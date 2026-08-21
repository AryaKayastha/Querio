from querio_chatbot.config import DOMAINS
from querio_chatbot.ingestion.ocr import _needs_ocr, _sidecar_path, find_scanned_pdfs

FEES_STRUCTURE_PDF = DOMAINS["D5"].data_dir / "FeesStructure.pdf"
FY_BOOKLET_PDF = DOMAINS["D5"].data_dir / "FY_Booklet.pdf"


def test_needs_ocr_true_for_known_scanned_pdf():
    assert _needs_ocr(FEES_STRUCTURE_PDF) is True


def test_needs_ocr_false_for_text_extractable_pdf():
    assert _needs_ocr(FY_BOOKLET_PDF) is False


def test_sidecar_path_naming():
    assert _sidecar_path(FEES_STRUCTURE_PDF).name == "FeesStructure.ocr.md"


def test_find_scanned_pdfs_includes_fees_structure_when_no_sidecar_yet():
    sidecar = _sidecar_path(FEES_STRUCTURE_PDF)
    if sidecar.exists():
        # Already OCR'd in a prior run -- nothing left to find for this file.
        assert FEES_STRUCTURE_PDF not in find_scanned_pdfs()
    else:
        assert FEES_STRUCTURE_PDF in find_scanned_pdfs()
