from langchain_core.documents import Document

from querio_chatbot.retrieval.retriever import (
    KEYWORD_WEIGHT_BY_DOMAIN,
    _bm25_candidates,
    _keyword_weight,
    _rerank,
    _tokenize,
    _weighted_rrf,
    retrieve,
)


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
