"""Run RAGAS answer-quality evaluation against the golden Q&A set.

Usage:
    python -m querio_chatbot.eval.answer_quality

This requires a configured GEMINI_API_KEY, an ingested vector store, and the
optional RAGAS dependencies from requirements.txt. Scores are printed per domain
so D5 and D6 are not hidden by a pooled average.
"""

import sys
import types
from collections import defaultdict

from querio_chatbot.eval.golden_qa import GOLDEN_QA_SET, validate_golden_qa
from querio_chatbot.llm.gemini_client import get_chat_model, get_embeddings
from querio_chatbot.router.router import answer_query


class _VertexAIUnavailable:
    """Placeholder for a VertexAI integration this project never uses."""

    def __init__(self, *args, **kwargs) -> None:
        raise RuntimeError(
            "VertexAI is not available -- this project evaluates with Gemini only."
        )


def _patch_ragas_vertexai_import() -> None:
    """ragas 0.4.x unconditionally imports langchain_community's VertexAI integration
    (ragas/llms/base.py). langchain_community is being sunset upstream and no longer
    ships that integration at all, so the plain `import ragas` fails before we ever
    get a chance to use it -- even though we only ever evaluate with Gemini. Since we
    never construct a VertexAI model, a harmless placeholder is enough to satisfy the
    import; nothing about our actual evaluation path touches these symbols.
    """
    module_name = "langchain_community.chat_models.vertexai"
    if module_name not in sys.modules:
        try:
            __import__(module_name)
        except ModuleNotFoundError:
            shim = types.ModuleType(module_name)
            shim.ChatVertexAI = _VertexAIUnavailable
            sys.modules[module_name] = shim

    import langchain_community.llms as community_llms

    if not hasattr(community_llms, "VertexAI"):
        community_llms.VertexAI = _VertexAIUnavailable


def _build_rows() -> list[dict]:
    rows = []
    for case in GOLDEN_QA_SET:
        result = answer_query(case["question"])
        documents = result.get("documents", [])
        rows.append(
            {
                "id": case["id"],
                "domain": case["domain"],
                "question": case["question"],
                "answer": result.get("answer", ""),
                "contexts": [document.page_content for document in documents],
                "ground_truth": case["reference_answer"],
                "expected_domain": case["domain"],
                "actual_domain": result.get("domain"),
            }
        )
    return rows


def run() -> dict[str, dict[str, float]]:
    """Evaluate and print faithfulness, relevance, and context metrics by domain."""
    validate_golden_qa()
    try:
        _patch_ragas_vertexai_import()
        from datasets import Dataset
        from ragas import evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError as exc:
        raise RuntimeError(
            "RAGAS dependencies are not installed. Install chatbot/requirements.txt first."
        ) from exc

    rows = _build_rows()
    evaluator_llm = LangchainLLMWrapper(get_chat_model())
    evaluator_embeddings = LangchainEmbeddingsWrapper(get_embeddings())
    scores_by_domain: dict[str, dict[str, float]] = defaultdict(dict)
    for domain in sorted({row["domain"] for row in rows}):
        domain_rows = [row for row in rows if row["domain"] == domain]
        result = evaluate(
            Dataset.from_list(domain_rows),
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )
        scores = result.to_pandas().mean(numeric_only=True).to_dict()
        scores_by_domain[domain] = {name: float(value) for name, value in scores.items()}
        print(f"{domain}: " + ", ".join(f"{name}={value:.3f}" for name, value in scores_by_domain[domain].items()))

    all_scores = [score for score in scores_by_domain.values()]
    overall = {
        name: sum(score[name] for score in all_scores) / len(all_scores)
        for name in all_scores[0]
    } if all_scores else {}
    if overall:
        print("Overall: " + ", ".join(f"{name}={value:.3f}" for name, value in overall.items()))
    return dict(scores_by_domain)


if __name__ == "__main__":
    run()
