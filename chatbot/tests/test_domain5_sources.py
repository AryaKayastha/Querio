from pathlib import Path

from querio_chatbot.config import DOMAINS
from querio_chatbot.ingestion.ingest import _source_paths


EXPECTED_DOMAIN5_PDFS = {
    "FeesStructure.pdf",
    "Scholarship Details.docx.pdf",
    "Admission Counselling Booklet 2026.cdr.pdf",
}


def test_domain5_discovers_required_pdf_sources():
    paths = _source_paths(DOMAINS["D5"].data_dir)

    assert EXPECTED_DOMAIN5_PDFS <= {path.name for path in paths}
    assert all(path.suffix.lower() == ".pdf" for path in paths if path.suffix.lower() == ".pdf")


def test_source_discovery_ignores_directories_and_unsupported_files(tmp_path: Path):
    (tmp_path / "source.PDF").touch()
    (tmp_path / "notes.md").touch()
    (tmp_path / "ignore.docx").touch()
    (tmp_path / "nested").mkdir()

    assert [path.name for path in _source_paths(tmp_path)] == ["notes.md", "source.PDF"]
