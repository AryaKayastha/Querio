import functools

import pytest
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from querio_chatbot.config import DOMAINS
from querio_chatbot.ingestion.ingest import load_domain_chunks
from querio_chatbot.retrieval import retriever
from querio_chatbot.retrieval.retriever import (
    KEYWORD_WEIGHT_BY_DOMAIN,
    _bm25_candidates,
    _expand_query,
    _keyword_weight,
    _normalize_query,
    _rerank,
    _tokenize,
    _weighted_rrf,
    retrieve,
)


def test_normalize_query_rewrites_semester_abbreviations():
    assert _normalize_query("syllabus for 4th sem") == "syllabus for semester 4"
    assert _normalize_query("sem-3 subjects") == "semester 3 subjects"
    assert _normalize_query("electives in Sem 4") == "electives in semester 4"
    assert _normalize_query("fourth semester courses") == "semester 4 courses"
    assert _normalize_query("2nd semester") == "semester 2"


def test_normalize_query_leaves_non_semester_numbers_alone():
    assert _normalize_query("75% attendance rule") == "75% attendance rule"
    assert _normalize_query("what is semester 2") == "what is semester 2"


@pytest.mark.parametrize(
    "query",
    ["What is the dress code for placement drives?", "What should I wear for the Meditab drive?", "placement attire"],
)
def test_expand_query_adds_the_guidelines_wording_for_dress_questions(query):
    assert _expand_query("D4", query) == f"{query} formal attire shoes"


@pytest.mark.parametrize(
    ("domain_code", "query"),
    [
        ("D4", "What is the eligibility for on-campus placements?"),
        ("D1", "What is the NCC uniform?"),  # only D4 expands
        ("D1", "What should I wear for the NCC camp?"),
        ("D4", "Must I wear formal attire shoes?"),  # already in the document's words
    ],
)
def test_expand_query_leaves_other_questions_alone(domain_code, query):
    assert _expand_query(domain_code, query) == query


class _FakeCollection:
    def __init__(self, count):
        self._collection = type("Collection", (), {"count": staticmethod(lambda: count)})()


@functools.lru_cache
def _real_chunks(domain_code):
    return tuple(load_domain_chunks(DOMAINS[domain_code]))


def _retrieve_from_real_domain_by_keyword(monkeypatch, domain_code, query):
    """retrieve() over a domain's real documents with keyword search only (no embeddings needed)."""
    chunks = _real_chunks(domain_code)
    index = (BM25Okapi([_tokenize(chunk.page_content) for chunk in chunks]), chunks)
    monkeypatch.setattr(retriever, "_bm25_index", lambda code: index)
    monkeypatch.setattr(retriever, "_get_collection", lambda code: _FakeCollection(len(chunks)))
    monkeypatch.setattr(retriever, "_semantic_candidates", lambda code, query, k: [])
    return retrieve(domain_code, query)


def _retrieve_from_real_d4_by_keyword(monkeypatch, query):
    return _retrieve_from_real_domain_by_keyword(monkeypatch, "D4", query)


def test_bounced_cheque_question_retrieves_the_rs_300_penalty_once_routed_to_d5(monkeypatch):
    # QRO-04 was a routing miss (UNROUTED); within D5 the fee document's "Cheque rebounced invites a
    # penalty of Rs. 300/-" is found. This guards that half.
    results = _retrieve_from_real_domain_by_keyword(monkeypatch, "D5", "What is the penalty if my fee cheque bounces?")
    assert any("penalty of Rs. 300" in doc.page_content for doc in results[:3])


def test_dress_code_question_retrieves_the_formal_attire_rule(monkeypatch):
    # QRO-10: the rule never says "dress code", so keyword search used to rank it 12th behind the
    # penalty line.
    results = _retrieve_from_real_d4_by_keyword(monkeypatch, "What is the dress code for placement drives?")
    assert any("formal attire and shoes" in doc.page_content for doc in results[:3])


@pytest.mark.parametrize(
    "query", ["What documents do I need for an NOC?", "What is the NOC process for doing an internship?"]
)
def test_noc_questions_retrieve_the_noc_note(monkeypatch, query):
    # QRO-03: no D4 document covered NOC; NOC_Process.md now points students to their department's TPO.
    results = _retrieve_from_real_d4_by_keyword(monkeypatch, query)
    noc = [doc for doc in results[:3] if doc.metadata.get("source_name") == "NOC Process"]
    assert noc, [doc.metadata.get("source_name") for doc in results[:3]]
    assert "department's Training and Placement Officer (TPO)" in noc[0].page_content
    assert noc[0].metadata["source_section"] == "No Objection Certificate (NOC)"


def test_tokenize_lowercases_and_keeps_percent_terms():
    assert _tokenize("75% Attendance Condoning") == ["75%", "attendance", "condoning"]


def test_keyword_weight_is_higher_for_policy_domains():
    assert _keyword_weight("D6") > _keyword_weight("D1")
    assert _keyword_weight("D6") == KEYWORD_WEIGHT_BY_DOMAIN["D6"]
    assert _keyword_weight("D5") == KEYWORD_WEIGHT_BY_DOMAIN["D5"]


def test_weighted_rrf_prefers_keyword_hits_when_keyword_weight_is_high():
    semantic = [
        Document(page_content="semantic only about electives", metadata={"source_name": "A"}),
        Document(page_content="shared policy note", metadata={"source_name": "Shared"}),
    ]
    keyword = [
        Document(page_content="shared policy note", metadata={"source_name": "Shared"}),
        Document(page_content="condoning attendance shortage", metadata={"source_name": "B"}),
    ]

    fused = _weighted_rrf(semantic, keyword, keyword_weight=0.8)
    assert fused[0][0].metadata["source_name"] == "Shared"


def test_rerank_does_not_let_stopword_overlap_beat_a_better_ranked_doc():
    """Regression test: a query like "What is syllabus of first year" shares three
    stopwords ("what", "is", "of") plus "syllabus" with ANY page that happens to say
    "the syllabus is ... for your review", even if that page has nothing to do with
    "first year" specifically. A flat additive rerank boost (the old behavior) let
    that raw overlap alone flip a poorly-fused, off-topic page ahead of a well-fused,
    on-topic one. Filtering stopwords from the overlap calc and scaling the boost by
    each doc's own base score (instead of adding a fixed amount) fixes this.
    """
    ranked = [
        (
            Document(
                page_content="first year formal education programme",
                metadata={"source_name": "on-topic"},
            ),
            0.0090,
        ),
        (
            Document(
                page_content="what is the syllabus of the course for your review",
                metadata={"source_name": "off-topic-stopword-match"},
            ),
            0.0070,
        ),
    ]

    reranked = _rerank("What is syllabus of first year", ranked)
    assert reranked[0].metadata["source_name"] == "on-topic"


def test_rerank_boosts_strong_term_overlap():
    ranked = [
        (
            Document(page_content="general campus introduction", metadata={"source_name": "weak"}),
            0.10,
        ),
        (
            Document(page_content="attendance shortage and condoning rules", metadata={"source_name": "strong"}),
            0.09,
        ),
    ]

    reranked = _rerank("attendance shortage condoning", ranked)
    assert reranked[0].metadata["source_name"] == "strong"


def test_bm25_candidates_return_empty_for_unknown_domain(monkeypatch):
    monkeypatch.setattr(
        "querio_chatbot.retrieval.retriever._bm25_index",
        lambda domain_code: None,
    )
    assert _bm25_candidates("DX", "attendance", k=4) == []


def test_retrieve_fuses_semantic_and_keyword_candidates(monkeypatch):
    semantic_doc = Document(page_content="semantic attendance guidance", metadata={"source_name": "semantic"})
    keyword_doc = Document(page_content="75% attendance condoning", metadata={"source_name": "keyword"})

    class FakeCollection:
        class Collection:
            @staticmethod
            def count():
                return 10

        _collection = Collection()

    monkeypatch.setattr(
        "querio_chatbot.retrieval.retriever._get_collection",
        lambda domain_code: FakeCollection(),
    )
    monkeypatch.setattr(
        "querio_chatbot.retrieval.retriever._semantic_candidates",
        lambda domain_code, query, k: [semantic_doc],
    )
    monkeypatch.setattr(
        "querio_chatbot.retrieval.retriever._bm25_candidates",
        lambda domain_code, query, k: [keyword_doc],
    )

    results = retrieve("D6", "75% attendance condoning")

    assert {doc.metadata["source_name"] for doc in results} == {"semantic", "keyword"}


def test_retrieve_returns_empty_for_empty_collection(monkeypatch):
    class FakeCollection:
        class Collection:
            @staticmethod
            def count():
                return 0

        _collection = Collection()

    monkeypatch.setattr(
        "querio_chatbot.retrieval.retriever._get_collection",
        lambda domain_code: FakeCollection(),
    )

    assert retrieve("D6", "attendance") == []
