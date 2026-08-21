from __future__ import annotations

import re
from collections import defaultdict
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from querio_chatbot.config import VECTORSTORE_DIR, collection_name
from querio_chatbot.llm.gemini_client import get_embeddings

# Candidate pool size before fusion / re-rank. Final answer uses top-k from retrieve().
CANDIDATE_K = 12
RRF_K = 60

# Keyword weight in [0, 1]. Remainder goes to semantic. Tuned per 02_architecture.md §2.3.
KEYWORD_WEIGHT_BY_DOMAIN: dict[str, float] = {
    "D1": 0.30,  # exploratory → semantic-heavy
    "D2": 0.30,
    "D3": 0.30,
    "D4": 0.65,  # policy-exact → keyword-heavy
    "D5": 0.45,  # mixed
    "D6": 0.65,  # policy-exact → keyword-heavy
}

_TOKEN_RE = re.compile(r"[a-z0-9%]+(?:'[a-z]+)?", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text or "")]


def _keyword_weight(domain_code: str) -> float:
    return KEYWORD_WEIGHT_BY_DOMAIN.get(domain_code, 0.40)


@lru_cache
def _get_collection(domain_code: str) -> Chroma:
    return Chroma(
        collection_name=collection_name(domain_code),
        embedding_function=get_embeddings(),
        persist_directory=str(VECTORSTORE_DIR),
    )


@lru_cache
def _bm25_index(domain_code: str) -> tuple[BM25Okapi, tuple[Document, ...]] | None:
    """Build an in-memory BM25 index over all chunks in the domain collection."""
    collection = _get_collection(domain_code)
    raw = collection.get(include=["documents", "metadatas"])
    texts = raw.get("documents") or []
    metadatas = raw.get("metadatas") or []
    if not texts:
        return None

    documents = [
        Document(page_content=text or "", metadata=metadata or {})
        for text, metadata in zip(texts, metadatas, strict=False)
    ]
    tokenized_corpus = [_tokenize(doc.page_content) for doc in documents]
    if not any(tokenized_corpus):
        return None
    return BM25Okapi(tokenized_corpus), tuple(documents)


def _doc_key(doc: Document) -> str:
    meta = doc.metadata or {}
    return "|".join(
        [
            str(meta.get("source_name", "")),
            str(meta.get("source_section", "")),
            str(meta.get("page", "")),
            doc.page_content[:120],
        ]
    )


def _semantic_candidates(domain_code: str, query: str, k: int) -> list[Document]:
    collection = _get_collection(domain_code)
    return collection.similarity_search(query, k=k)


def _bm25_candidates(domain_code: str, query: str, k: int) -> list[Document]:
    indexed = _bm25_index(domain_code)
    if indexed is None:
        return []
    bm25, documents = indexed
    tokens = _tokenize(query)
    if not tokens:
        return []
    scores = bm25.get_scores(tokens)
    ranked = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)
    return [documents[idx] for idx in ranked[:k] if scores[idx] > 0]


def _weighted_rrf(
    semantic_docs: list[Document],
    keyword_docs: list[Document],
    keyword_weight: float,
) -> list[tuple[Document, float]]:
    """Reciprocal Rank Fusion with domain-specific semantic/keyword weights."""
    semantic_weight = 1.0 - keyword_weight
    fused: dict[str, float] = defaultdict(float)
    by_key: dict[str, Document] = {}

    for rank, doc in enumerate(semantic_docs, start=1):
        key = _doc_key(doc)
        by_key[key] = doc
        fused[key] += semantic_weight * (1.0 / (RRF_K + rank))

    for rank, doc in enumerate(keyword_docs, start=1):
        key = _doc_key(doc)
        by_key.setdefault(key, doc)
        fused[key] += keyword_weight * (1.0 / (RRF_K + rank))

    return sorted(
        ((by_key[key], score) for key, score in fused.items()),
        key=lambda item: item[1],
        reverse=True,
    )


def _rerank(query: str, ranked: list[tuple[Document, float]]) -> list[Document]:
    """Light second-stage re-rank: boost chunks that share more query tokens."""
    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return [doc for doc, _ in ranked]

    rescored: list[tuple[Document, float]] = []
    for doc, base_score in ranked:
        doc_tokens = set(_tokenize(doc.page_content))
        overlap = len(query_tokens & doc_tokens) / max(len(query_tokens), 1)
        # Small additive boost so RRF order still dominates unless overlap is strong.
        rescored.append((doc, base_score + 0.15 * overlap))

    rescored.sort(key=lambda item: item[1], reverse=True)
    return [doc for doc, _ in rescored]


def clear_retrieval_caches() -> None:
    """Drop cached Chroma/BM25 handles (call after re-ingestion in the same process)."""
    _get_collection.cache_clear()
    _bm25_index.cache_clear()


def retrieve(domain_code: str, query: str, k: int = 4) -> list[Document]:
    """Hybrid retrieve: semantic + BM25, fused with weighted RRF, then light re-rank."""
    collection = _get_collection(domain_code)
    if collection._collection.count() == 0:
        return []

    candidate_k = max(k, min(CANDIDATE_K, collection._collection.count()))
    keyword_weight = _keyword_weight(domain_code)

    semantic_docs = _semantic_candidates(domain_code, query, candidate_k)
    keyword_docs = _bm25_candidates(domain_code, query, candidate_k)

    if not semantic_docs and not keyword_docs:
        return []
    if not keyword_docs:
        return semantic_docs[:k]
    if not semantic_docs:
        return keyword_docs[:k]

    fused = _weighted_rrf(semantic_docs, keyword_docs, keyword_weight)
    return _rerank(query, fused)[:k]
