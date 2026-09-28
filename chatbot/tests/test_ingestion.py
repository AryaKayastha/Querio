from pathlib import Path

import pytest

from querio_chatbot.config import GEMINI_EMBEDDING_MODEL, Domain
from querio_chatbot.ingestion import ingest
from querio_chatbot.ingestion.ingest import EmbeddingModelMismatch, _parse_frontmatter, load_domain_chunks

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_DOMAIN = Domain(
    code="TEST", name="Test", description="Test fixture domain", data_dir=FIXTURES_DIR, guidance_only=False
)
STORED_VECTOR = [1.0, 0.0]


class FakeCollection:
    def __init__(self, store, metadata):
        self.store = store
        self.metadata = metadata

    def count(self):
        return len(self.store.rows)

    def get(self, limit, include):
        rows = self.store.rows[:limit]
        return {"documents": [text for _, text, _ in rows], "embeddings": [STORED_VECTOR for _ in rows]}

    def modify(self, metadata):
        self.metadata = metadata


class FakeStore:
    """In-memory stand-in for a langchain Chroma store: rows are (id, text, metadata)."""

    def __init__(self, rows=(), model=GEMINI_EMBEDDING_MODEL, failures_before_success=0):
        self.rows = list(rows)
        self.added = []
        self.deleted = []
        self.failures_left = failures_before_success
        self._collection = FakeCollection(self, {ingest.MODEL_METADATA_KEY: model} if model else None)

    def get(self, include):
        return {
            "ids": [row_id for row_id, _, _ in self.rows],
            "documents": [text for _, text, _ in self.rows],
            "metadatas": [metadata for _, _, metadata in self.rows],
        }

    def delete(self, ids):
        self.deleted.extend(ids)
        self.rows = [row for row in self.rows if row[0] not in ids]

    def add_documents(self, batch):
        if self.failures_left:
            self.failures_left -= 1
            raise ConnectionError("simulated embedding timeout")
        self.added.extend(batch)


class FakeEmbeddings:
    def __init__(self, vector):
        self.vector = vector

    def embed_documents(self, texts):
        return [self.vector for _ in texts]


def _row(chunk, row_id):
    return (row_id, chunk.page_content, dict(chunk.metadata))


@pytest.fixture
def use_store(monkeypatch):
    monkeypatch.setattr(ingest.time, "sleep", lambda _: None)
    monkeypatch.setattr(ingest, "get_embeddings", lambda: FakeEmbeddings(STORED_VECTOR))

    def install(store):
        monkeypatch.setattr(ingest, "Chroma", lambda **_: store)
        return store

    return install


def test_ingest_embeds_only_chunks_not_already_in_collection(use_store):
    chunks = load_domain_chunks(FIXTURE_DOMAIN)
    store = use_store(FakeStore(rows=[_row(chunks[0], "a")]))

    assert ingest.ingest_domain(FIXTURE_DOMAIN) == len(chunks) - 1
    assert chunks[0].page_content not in [doc.page_content for doc in store.added]
    assert store.deleted == []


def test_ingest_removes_stale_and_duplicate_chunks(use_store):
    chunks = load_domain_chunks(FIXTURE_DOMAIN)
    stale = ("old", "text from a document that was since edited", {"source_name": "Gone", "source_section": "x"})
    store = use_store(FakeStore(rows=[_row(chunks[0], "a"), _row(chunks[0], "a-copy"), stale]))

    ingest.ingest_domain(FIXTURE_DOMAIN)

    assert sorted(store.deleted) == ["a-copy", "old"]
    assert chunks[0].page_content not in [doc.page_content for doc in store.added]


def test_ingest_refuses_collection_stamped_with_another_model(use_store):
    chunks = load_domain_chunks(FIXTURE_DOMAIN)
    store = use_store(FakeStore(rows=[_row(chunks[0], "a")], model="models/some-older-model"))

    with pytest.raises(EmbeddingModelMismatch, match="some-older-model"):
        ingest.ingest_domain(FIXTURE_DOMAIN)
    assert store.added == [] and store.deleted == []


def test_ingest_detects_unstamped_collection_built_with_another_model(use_store, monkeypatch):
    chunks = load_domain_chunks(FIXTURE_DOMAIN)
    store = use_store(FakeStore(rows=[_row(chunks[0], "a")], model=None))
    monkeypatch.setattr(ingest, "get_embeddings", lambda: FakeEmbeddings([0.0, 1.0]))

    with pytest.raises(EmbeddingModelMismatch):
        ingest.ingest_domain(FIXTURE_DOMAIN)
    assert store.added == [] and store.deleted == []


def test_ingest_stamps_unstamped_collection_built_with_the_current_model(use_store):
    chunks = load_domain_chunks(FIXTURE_DOMAIN)
    store = use_store(FakeStore(rows=[_row(chunks[0], "a")], model=None))

    ingest.ingest_domain(FIXTURE_DOMAIN)

    assert store._collection.metadata[ingest.MODEL_METADATA_KEY] == GEMINI_EMBEDDING_MODEL


def test_ingest_retries_a_failed_embedding_batch(use_store):
    chunks = load_domain_chunks(FIXTURE_DOMAIN)
    store = use_store(FakeStore(failures_before_success=1))

    assert ingest.ingest_domain(FIXTURE_DOMAIN) == len(chunks)
    assert len(store.added) == len(chunks)


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
    chunks = load_domain_chunks(FIXTURE_DOMAIN)

    assert len(chunks) >= 2
    assert all(c.metadata["source_name"] == "Fixture Policy Doc" for c in chunks)
    assert all(c.metadata["domain"] == "TEST" for c in chunks)
    section_headings = {c.metadata["source_section"] for c in chunks}
    assert "Fixture Section One" in section_headings
    assert "Fixture Subsection" in section_headings
