"""Chunk and embed active-domain source documents into Chroma collections.

Supported formats are curated Markdown/text with frontmatter and raw PDFs.
Scanned PDFs without extractable text are skipped with a warning.
"""

import time
from pathlib import Path

import pypdf
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from querio_chatbot.config import DOMAINS, VECTORSTORE_DIR, Domain, collection_name
from querio_chatbot.llm.gemini_client import get_embeddings

FRONTMATTER_FIELDS = ("source_name", "source_type", "source_url", "last_updated", "owner_contact")
HEADER_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]
EMBED_BATCH_SIZE = 15
EMBED_BATCH_DELAY_SECONDS = 10


def _parse_frontmatter(raw_text: str) -> tuple[dict, str]:
    if not raw_text.startswith("---"):
        return {}, raw_text
    parts = raw_text.split("---", 2)
    if len(parts) < 3:
        return {}, raw_text

    _, frontmatter_block, body = parts
    metadata = {}
    for line in frontmatter_block.strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if key in FRONTMATTER_FIELDS:
            metadata[key] = value.strip()
    return metadata, body.strip()


def _section_heading(section_metadata: dict) -> str:
    return section_metadata.get("h3") or section_metadata.get("h2") or section_metadata.get("h1") or ""


def _clean_source_name(path: Path) -> str:
    stem = path.stem
    if stem.lower().endswith(".docx"):
        stem = stem[: -len(".docx")]
    return " ".join(stem.replace("_", " ").split())


def _load_markdown_chunks(path: Path, header_splitter, chunk_splitter) -> list[Document]:
    raw_text = path.read_text(encoding="utf-8")
    doc_metadata, body = _parse_frontmatter(raw_text)
    if not body:
        return []

    chunks = []
    for section in header_splitter.split_text(body):
        for chunk in chunk_splitter.split_documents([section]):
            chunk.metadata.update(doc_metadata)
            chunk.metadata["source_section"] = _section_heading(chunk.metadata) or path.stem
            chunk.metadata.setdefault("source_name", path.stem)
            chunks.append(chunk)
    return chunks


def _load_pdf_chunks(path: Path, chunk_splitter) -> list[Document]:
    reader = pypdf.PdfReader(path, strict=False)
    source_name = _clean_source_name(path)
    chunks = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue
        for piece in chunk_splitter.split_text(page_text):
            chunks.append(
                Document(
                    page_content=piece,
                    metadata={
                        "source_name": source_name,
                        "source_type": "pdf",
                        "source_section": f"Page {page_number}",
                    },
                )
            )

    if not chunks:
        sidecar = path.parent / f"{path.stem}.ocr.md"
        if sidecar.exists():
            print(f"  [i] {path.name} has no extractable text, but an OCR sidecar exists -- using that instead")
        else:
            print(f"  [!] {path.name} has no extractable text -- likely a scanned image, run ingestion.ocr first")
    return chunks


def _source_paths(data_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in data_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".pdf"}
    )


def load_domain_chunks(domain: Domain) -> list[Document]:
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADER_SPLIT_ON)
    chunk_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    documents = []

    for path in _source_paths(domain.data_dir):
        try:
            if path.suffix.lower() == ".pdf":
                documents.extend(_load_pdf_chunks(path, chunk_splitter))
            else:
                documents.extend(_load_markdown_chunks(path, header_splitter, chunk_splitter))
        except Exception as exc:
            print(f"  [!] Could not ingest {path.name}: {exc}")

    for chunk in documents:
        chunk.metadata["domain"] = domain.code
    return documents


def ingest_domain(domain: Domain) -> int:
    chunks = load_domain_chunks(domain)
    if not chunks:
        print(f"[{domain.code}] no ingestible documents found in {domain.data_dir} -- skipping")
        return 0

    store = Chroma(
        collection_name=collection_name(domain.code),
        embedding_function=get_embeddings(),
        persist_directory=str(VECTORSTORE_DIR),
    )
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        store.add_documents(batch)
        done = min(start + EMBED_BATCH_SIZE, len(chunks))
        print(f"[{domain.code}] embedded {done}/{len(chunks)} chunks")
        if done < len(chunks):
            time.sleep(EMBED_BATCH_DELAY_SECONDS)

    print(f"[{domain.code}] ingested {len(chunks)} chunks from {len(_source_paths(domain.data_dir))} files")
    return len(chunks)


def main() -> None:
    for domain in DOMAINS.values():
        ingest_domain(domain)


if __name__ == "__main__":
    main()
