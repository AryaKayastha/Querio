"""Chunk + embed each active domain's source documents into its Chroma collection.

Document format expected in ../data/<domain>/*.md (see data/README.md):

    ---
    source_name: Attendance Policy 2025-26
    source_type: policy_document
    last_updated: 2026-01-15
    owner_contact: Office of Academic Affairs
    ---

    # Heading
    ... content ...
"""

from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from querio_chatbot.config import DOMAINS, VECTORSTORE_DIR, Domain
from querio_chatbot.llm.gemini_client import get_embeddings

FRONTMATTER_FIELDS = ("source_name", "source_type", "last_updated", "owner_contact")
HEADER_SPLIT_ON = [("#", "h1"), ("##", "h2"), ("###", "h3")]


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


def load_domain_chunks(domain: Domain) -> list:
    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADER_SPLIT_ON)
    chunk_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    documents = []
    source_files = sorted(domain.data_dir.glob("*.md")) + sorted(domain.data_dir.glob("*.txt"))
    for path in source_files:
        raw_text = path.read_text(encoding="utf-8")
        doc_metadata, body = _parse_frontmatter(raw_text)
        if not body:
            continue

        sections = header_splitter.split_text(body)
        for section in sections:
            for chunk in chunk_splitter.split_documents([section]):
                chunk.metadata.update(doc_metadata)
                chunk.metadata["domain"] = domain.code
                chunk.metadata["source_section"] = _section_heading(chunk.metadata) or path.stem
                chunk.metadata.setdefault("source_name", path.stem)
                documents.append(chunk)
    return documents


def ingest_domain(domain: Domain) -> int:
    chunks = load_domain_chunks(domain)
    if not chunks:
        print(f"[{domain.code}] no documents found in {domain.data_dir} -- skipping")
        return 0

    Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        collection_name=domain.code,
        persist_directory=str(VECTORSTORE_DIR),
    )
    print(f"[{domain.code}] ingested {len(chunks)} chunks from {len(list(domain.data_dir.glob('*')))} files")
    return len(chunks)


def main() -> None:
    for domain in DOMAINS.values():
        ingest_domain(domain)


if __name__ == "__main__":
    main()
