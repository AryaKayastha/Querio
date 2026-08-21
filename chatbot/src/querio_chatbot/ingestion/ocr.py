"""OCR fallback for scanned PDFs with no extractable text (e.g. FeesStructure.pdf).

Renders each page to an image via PyMuPDF and asks Gemini's vision model to
transcribe it verbatim, then writes the result as a markdown sidecar file next
to the original PDF (FeesStructure.pdf -> FeesStructure.ocr.md) with frontmatter.
The sidecar flows through the normal curated-markdown path on the next
`ingest` run -- no special-casing needed there.

This is a separate, explicit step (not run automatically during ingestion)
because each page costs a real Gemini vision call against the same rate-limited
free-tier quota used for chat -- run it once per scanned document, not on
every ingest.

Usage: python -m querio_chatbot.ingestion.ocr
"""

import base64
import time
from pathlib import Path

import fitz  # PyMuPDF
import pypdf
from langchain_core.messages import HumanMessage
from langchain_core.messages.content import create_image_block, create_text_block

from querio_chatbot.config import DATA_ROOT
from querio_chatbot.llm.gemini_client import get_chat_model
from querio_chatbot.router.router import _extract_text

OCR_PAGE_DELAY_SECONDS = 5
# Cap rendered pages by pixel dimension rather than a fixed DPI -- some scanned PDFs declare
# unusually large physical page sizes, and dpi=200 on those renders 100+ MB images that vision
# APIs reject outright. Capping the longest side keeps every page a similar, API-safe size.
MAX_RENDER_DIMENSION = 2000
DEFAULT_DPI = 200
BLANK_PAGE_MARKER = "[BLANK PAGE]"
TRANSCRIBE_PROMPT = (
    "Transcribe all readable text from this document page verbatim, preserving structure "
    "(headings, bullet points, tables as markdown tables). Do not summarize, translate, or "
    f"add commentary -- output only the transcribed text. If the page is blank or unreadable, "
    f"output exactly: {BLANK_PAGE_MARKER}"
)


def _needs_ocr(pdf_path: Path) -> bool:
    reader = pypdf.PdfReader(pdf_path)
    return not any((page.extract_text() or "").strip() for page in reader.pages)


def _sidecar_path(pdf_path: Path) -> Path:
    return pdf_path.parent / f"{pdf_path.stem}.ocr.md"


def _render_page_png(page: "fitz.Page") -> bytes:
    """Render a page at DEFAULT_DPI, capped at MAX_RENDER_DIMENSION on its longest side."""
    longest_side_points = max(page.rect.width, page.rect.height)
    dpi_scale = DEFAULT_DPI / 72
    scale = min(dpi_scale, MAX_RENDER_DIMENSION / longest_side_points)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    return pixmap.tobytes("png")


def _transcribe_page(png_bytes: bytes) -> str:
    b64 = base64.b64encode(png_bytes).decode("ascii")
    message = HumanMessage(
        content=[
            create_text_block(TRANSCRIBE_PROMPT),
            create_image_block(base64=b64, mime_type="image/png"),
        ]
    )
    response = get_chat_model().invoke([message])
    return _extract_text(response.content).strip()


def ocr_pdf(pdf_path: Path) -> Path:
    """OCR a scanned PDF page-by-page and write a markdown sidecar. Returns its path.

    A page that fails to transcribe (e.g. a rejected image) is skipped, not fatal --
    the rest of the document still gets OCR'd.
    """
    doc = fitz.open(pdf_path)
    page_texts = []
    for page_number, page in enumerate(doc, start=1):
        try:
            text = _transcribe_page(_render_page_png(page))
        except Exception as exc:
            print(f"  [!] {pdf_path.name}: page {page_number}/{len(doc)} failed, skipped ({exc})")
            text = ""
        else:
            if text and text != BLANK_PAGE_MARKER:
                page_texts.append((page_number, text))
            print(f"  [ocr] {pdf_path.name}: page {page_number}/{len(doc)} transcribed ({len(text)} chars)")
        if page_number < len(doc):
            time.sleep(OCR_PAGE_DELAY_SECONDS)

    body = "\n\n".join(f"## Page {number}\n\n{text}" for number, text in page_texts)
    frontmatter = (
        "---\n"
        f"source_name: {pdf_path.stem}\n"
        "source_type: ocr_scanned_pdf\n"
        "owner_contact: unknown -- OCR'd automatically, verify with the source department\n"
        "---\n\n"
    )

    sidecar_path = _sidecar_path(pdf_path)
    sidecar_path.write_text(frontmatter + body, encoding="utf-8")
    return sidecar_path


def find_scanned_pdfs() -> list[Path]:
    """PDFs across all domain folders (active or not) with no extractable text and no sidecar yet."""
    candidates = []
    for domain_dir in sorted(p for p in DATA_ROOT.iterdir() if p.is_dir()):
        for pdf_path in sorted(domain_dir.glob("*.pdf")):
            if _sidecar_path(pdf_path).exists():
                continue
            if _needs_ocr(pdf_path):
                candidates.append(pdf_path)
    return candidates


def main() -> None:
    candidates = find_scanned_pdfs()
    if not candidates:
        print("No scanned PDFs need OCR (or all already have .ocr.md sidecars).")
        return

    for pdf_path in candidates:
        print(f"[ocr] Starting {pdf_path.relative_to(DATA_ROOT)} ...")
        try:
            sidecar_path = ocr_pdf(pdf_path)
        except Exception as exc:
            print(f"[!] {pdf_path.name}: OCR failed entirely, skipped ({exc})")
            continue
        print(f"[ocr] Wrote {sidecar_path.relative_to(DATA_ROOT)}")


if __name__ == "__main__":
    main()
