from pathlib import Path

from querio_chatbot.config import Domain
from querio_chatbot.ingestion.ingest import _parse_frontmatter, load_domain_chunks

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_frontmatter_extracts_known_fields():
    raw = (
        "---\n"
        "source_name: Attendance Policy 2025-26\n"
        "source_type: policy_document\n"
        "last_updated: 2026-01-15\n"
        "owner_contact: Office of Academic Affairs\n"
        "---\n\n"
        "# Heading\ncontent"
    )
    metadata, body = _parse_frontmatter(raw)
    assert metadata["source_name"] == "Attendance Policy 2025-26"
    assert metadata["owner_contact"] == "Office of Academic Affairs"
    assert body.startswith("# Heading")


def test_parse_frontmatter_missing_block_returns_full_text():
    raw = "# Heading\ncontent, no frontmatter"
    metadata, body = _parse_frontmatter(raw)
    assert metadata == {}
    assert body == raw


def test_load_domain_chunks_extracts_metadata_and_sections():
    fixture_domain = Domain(code="TEST", name="Test", data_dir=FIXTURES_DIR, guidance_only=False)
    chunks = load_domain_chunks(fixture_domain)

    assert len(chunks) >= 2
    assert all(c.metadata["source_name"] == "Fixture Policy Doc" for c in chunks)
    assert all(c.metadata["domain"] == "TEST" for c in chunks)
    section_headings = {c.metadata["source_section"] for c in chunks}
    assert "Fixture Section One" in section_headings
    assert "Fixture Subsection" in section_headings
