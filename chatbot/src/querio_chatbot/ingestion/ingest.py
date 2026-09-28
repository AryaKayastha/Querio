"""Chunk and embed active-domain source documents into Chroma collections.

Supported formats are curated Markdown/text with frontmatter and raw PDFs.
Scanned PDFs without extractable text are skipped with a warning.

Usage: python -m querio_chatbot.ingestion.ingest [DOMAIN_CODE ...]
Each domain's chunks live in their own Chroma collection (see collection_name()), so
re-ingesting one domain never touches another's. With no arguments, every domain in
DOMAINS is ingested; pass explicit codes (e.g. "D4 D6") to limit it.

Ingestion syncs each collection with the documents on disk:
- chunks already in the collection (same source, section, and text) are skipped, so adding a
  file only embeds that file's chunks and re-runs never spend quota on unchanged documents;
- chunks the current documents no longer produce (edited/removed files, older chunking logic,
  duplicate copies) are deleted, which costs no embedding quota;
- a collection built with a different embedding model is refused, because mixing models
  silently breaks similarity search (same vector size, unrelated vector spaces).
An interrupted run can simply be re-run: it resumes from what was already embedded.
"""

import math
import sys
import time
from pathlib import Path

import pypdf
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from querio_chatbot.config import DOMAINS, GEMINI_EMBEDDING_MODEL, VECTORSTORE_DIR, Domain, collection_name
from querio_chatbot.llm.gemini_client import get_embeddings

FRONTMATTER_FIELDS = ("source_name", "source_type", "source_url", "last_updated", "owner_contact")
HEADER_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]
EMBED_BATCH_SIZE = 15
EMBED_BATCH_DELAY_SECONDS = 10
EMBED_BATCH_ATTEMPTS = 3
EMBED_RETRY_DELAY_SECONDS = 20
MODEL_METADATA_KEY = "embedding_model"
# Re-embedding a stored chunk with the model that built it gives cosine 1.0; a different
# model gives ~0 (measured 0.008 for gemini-embedding-001 vs gemini-embedding-2).
SAME_MODEL_MIN_COSINE = 0.98


class IngestionError(RuntimeError):
    pass


class EmbeddingModelMismatch(IngestionError):
    pass


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
            # Dense, table-heavy pages (course/credit scheme tables) often don't repeat
            # identifying context like "Semester 5" on every page -- only a divider page
            # elsewhere in the same PDF does. Prepending the document name measurably
            # improves semantic match for queries like "semester 5 subjects" (confirmed:
            # cosine similarity to that query rose from 0.63 to 0.71 on a real table page
            # that otherwise didn't make the top-12 candidates at all).
            chunks.append(
                Document(
                    page_content=f"{source_name}\n\n{piece}",
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


def _chunk_key(text: str, metadata: dict) -> tuple[str, str, str]:
    return (str(metadata.get("source_name", "")), str(metadata.get("source_section", "")), text)


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def _mismatch_message(domain: Domain, built_with: str) -> str:
    return (
        f"[{domain.code}] collection {collection_name(domain.code)} was built with {built_with}, but "
        f"GEMINI_EMBEDDING_MODEL is {GEMINI_EMBEDDING_MODEL}. Mixing models silently breaks search. "
        f"Delete {VECTORSTORE_DIR} and re-run ingestion to rebuild with the current model."
    )


def _ensure_same_embedding_model(store: Chroma, domain: Domain) -> None:
    """Refuse to add to a collection built with another model; stamp the model otherwise."""
    collection = store._collection
    metadata = collection.metadata or {}
    built_with = metadata.get(MODEL_METADATA_KEY)
    if built_with is not None:
        if built_with != GEMINI_EMBEDDING_MODEL:
            raise EmbeddingModelMismatch(_mismatch_message(domain, built_with))
        return

    if collection.count() > 0:
        # Collections created before the model was recorded: identify the model by re-embedding
        # one stored chunk (costs a single embedding call, once per collection).
        sample = collection.get(limit=1, include=["documents", "embeddings"])
        fresh = _with_retry(
            lambda: get_embeddings().embed_documents([sample["documents"][0]])[0],
            domain,
            "embedding-model check",
        )
        if _cosine(list(sample["embeddings"][0]), fresh) < SAME_MODEL_MIN_COSINE:
            raise EmbeddingModelMismatch(_mismatch_message(domain, "a different embedding model"))
    collection.modify(metadata={**metadata, MODEL_METADATA_KEY: GEMINI_EMBEDDING_MODEL})


def _prune_stale(
    store: Chroma, domain: Domain, current_keys: set[tuple[str, str, str]]
) -> set[tuple[str, str, str]]:
    """Delete chunks the current documents no longer produce, plus duplicate copies.

    Returns the keys still present in the collection afterwards.
    """
    existing = store.get(include=["documents", "metadatas"])
    kept: set[tuple[str, str, str]] = set()
    stale_ids = []
    for chunk_id, text, metadata in zip(existing["ids"], existing["documents"], existing["metadatas"]):
        key = _chunk_key(text or "", metadata or {})
        if key in current_keys and key not in kept:
            kept.add(key)
        else:
            stale_ids.append(chunk_id)
    if stale_ids:
        store.delete(ids=stale_ids)
        print(f"[{domain.code}] removed {len(stale_ids)} stale or duplicate chunks")
    return kept


def _with_retry(call, domain: Domain, what: str):
    """Run an embedding-API call, retrying transient failures (timeouts, overload)."""
    for attempt in range(1, EMBED_BATCH_ATTEMPTS + 1):
        try:
            return call()
        except Exception as exc:
            if attempt == EMBED_BATCH_ATTEMPTS:
                raise IngestionError(
                    f"[{domain.code}] {what} failed {EMBED_BATCH_ATTEMPTS} times ({exc}). Progress so far "
                    "is saved -- re-run ingestion to resume."
                ) from exc
            print(f"[{domain.code}] {what} failed ({exc}); retrying in {EMBED_RETRY_DELAY_SECONDS}s")
            time.sleep(EMBED_RETRY_DELAY_SECONDS)


def ingest_domain(domain: Domain) -> int:
    all_chunks = load_domain_chunks(domain)
    if not all_chunks:
        print(f"[{domain.code}] no ingestible documents found in {domain.data_dir} -- skipping")
        return 0

    unique_chunks = {_chunk_key(chunk.page_content, chunk.metadata): chunk for chunk in all_chunks}

    store = Chroma(
        collection_name=collection_name(domain.code),
        embedding_function=get_embeddings(),
        persist_directory=str(VECTORSTORE_DIR),
    )
    _ensure_same_embedding_model(store, domain)
    already_embedded = _prune_stale(store, domain, set(unique_chunks))

    chunks = [chunk for key, chunk in unique_chunks.items() if key not in already_embedded]
    if not chunks:
        print(f"[{domain.code}] all {len(unique_chunks)} chunks already embedded -- nothing to do")
        return 0
    if already_embedded:
        print(f"[{domain.code}] skipping {len(already_embedded)} already-embedded chunks, embedding {len(chunks)} new")

    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        _with_retry(lambda: store.add_documents(batch), domain, "embedding batch")
        done = min(start + EMBED_BATCH_SIZE, len(chunks))
        print(f"[{domain.code}] embedded {done}/{len(chunks)} chunks")
        if done < len(chunks):
            time.sleep(EMBED_BATCH_DELAY_SECONDS)

    print(f"[{domain.code}] ingested {len(chunks)} chunks from {len(_source_paths(domain.data_dir))} files")
    return len(chunks)


def main() -> None:
    requested_codes = sys.argv[1:]
    if not requested_codes:
        domains = list(DOMAINS.values())
    else:
        unknown = [code for code in requested_codes if code not in DOMAINS]
        if unknown:
            raise SystemExit(f"Unknown domain code(s): {', '.join(unknown)} (known: {', '.join(DOMAINS)})")
        domains = [DOMAINS[code] for code in requested_codes]

    for domain in domains:
        try:
            ingest_domain(domain)
        except IngestionError as exc:
            raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
