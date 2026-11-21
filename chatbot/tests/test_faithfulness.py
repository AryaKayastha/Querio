"""QRO-06 / QRO-07: answers stick to what the documents say -- no inferred yes/no for cases they
don't cover, no added steps, contacts or padding bullets. The prompt rules are checked offline; the
model's behaviour is checked live (skipped without an API key)."""

import os
import re
from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from querio_chatbot.router import router
from querio_chatbot.router.router import (
    ANSWER_FORMAT_RULES,
    ANSWER_ONLY_COVERED_CASES,
    STATE_ONLY_WHAT_THE_CONTEXT_SAYS,
    _select_sources,
    answer_query,
    generate_node,
)

DOCS = [
    Document(
        page_content="Leave is granted only for major medical cases or external/university-level academic events.",
        metadata={"source_name": "Attendance Policy", "source_section": "Page 1"},
    )
]


def _answer_prompt(monkeypatch):
    prompts = []

    def fake_invoke(build, prompt):
        prompts.append(prompt)
        return SimpleNamespace(content="The college documents don't cover leave for the NCC camp.")

    monkeypatch.setattr(router, "invoke_with_fallback", fake_invoke)
    generate_node({"query": "Do I get leave for the NCC camp?", "domain": "D6", "documents": DOCS})
    return prompts[0]


def test_yes_or_no_only_for_cases_the_documents_cover(monkeypatch):
    # QRO-06: the old instruction told the model to "state plainly" answers the context merely implied.
    prompt = _answer_prompt(monkeypatch)
    assert ANSWER_ONLY_COVERED_CASES in prompt
    assert "state that answer plainly instead of treating" not in prompt


def test_no_added_facts_contacts_or_padding_bullets(monkeypatch):
    # QRO-07: answers invented "Documentation"/"Approval"/"Implication" bullets and office names.
    prompt = _answer_prompt(monkeypatch)
    assert STATE_ONLY_WHAT_THE_CONTEXT_SAYS in prompt
    assert "Never add bullets to fill out an answer." in ANSWER_FORMAT_RULES


@pytest.mark.parametrize(
    "answer", ["That value isn't listed.", "The NRI fee for 3rd-year ME is not listed in the fee structure."]
)
def test_answers_saying_a_value_is_not_listed_cite_nothing(answer):
    assert _select_sources(answer, DOCS) == []


live = pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="requires a real GEMINI_API_KEY")


@live
@pytest.mark.parametrize("query", ["Is attendance given for placement drives?", "Do I get leave for the NCC camp?"])
def test_live_uncovered_cases_get_no_inferred_yes_or_no(query):
    answer = answer_query(query)["answer"]
    assert not re.match(r"\W*(?:yes|no)\b", answer, re.IGNORECASE), answer


@live
def test_live_blank_fee_cell_is_not_filled_in():
    answer = answer_query("What is the fee for 3rd year mechanical NRI?")["answer"]
    assert not re.search(r"\d{1,2},\d{2},\d{3}", answer), answer  # no fee amount invented for a "-" cell
