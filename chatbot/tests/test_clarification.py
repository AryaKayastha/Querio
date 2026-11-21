"""QRO-11: vague or context-less questions get a clarifying question instead of a guess or a
"no information" reply. Model faked unless noted."""

import os
from types import SimpleNamespace

import pytest

from querio_chatbot.router import router
from querio_chatbot.router.router import (
    ACTION_DECLINE,
    NO_EARLIER_MESSAGES_REPLY,
    Classification,
    answer_query,
    classify_node,
    generate_node,
)

ASK_PROGRAMME = "Which programme and year are you asking about?"
HISTORY = [
    {"role": "user", "content": "What are the benefits of joining NCC?"},
    {"role": "assistant", "content": "NCC cadets get certificates and camp training."},
]


def _fake_model(monkeypatch, classification):
    """Classifier calls get `classification`; answer calls get a fixed text. Returns all prompts."""
    prompts = []

    def fake_invoke(build, prompt):
        prompts.append(prompt)
        if prompt.startswith("You are a routing classifier"):
            return classification
        return SimpleNamespace(content="Generated answer.")

    monkeypatch.setattr(router, "invoke_with_fallback", fake_invoke)
    return prompts


def _no_model(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("must be answered without a model call")

    monkeypatch.setattr(router, "invoke_with_fallback", fail)


def _no_retrieval(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("a clarifying question needs no retrieval")

    monkeypatch.setattr(router, "retrieve", fail)


# --- Phrasings that can't mean anything without earlier messages: fixed reply, no model call ---


@pytest.mark.parametrize(
    "query",
    [
        "As I told you earlier, I'm in the AI branch, what is my fee?",  # QA repro 2
        "What about its fees?",  # QA repro 3
        "tell me more",  # QA repro 4
        "Like I said, what's the deadline?",
        "so what about that?",
        "Tell me more about it.",
    ],
)
def test_reference_to_earlier_messages_in_a_new_chat_asks_for_the_full_question(monkeypatch, query):
    _no_model(monkeypatch)
    result = answer_query(query)
    assert result["answer"] == NO_EARLIER_MESSAGES_REPLY
    assert result["documents"] == []


@pytest.mark.parametrize("query", ["tell me more", "What about its fees?"])
def test_with_earlier_messages_the_same_phrasing_goes_to_the_router(monkeypatch, query):
    _fake_model(monkeypatch, Classification(domain="D1", confidence=0.9))
    monkeypatch.setattr(router, "retrieve", lambda domain_code, query: [])
    assert answer_query(query, history=HISTORY)["answer"] != NO_EARLIER_MESSAGES_REPLY


@pytest.mark.parametrize(
    "query",
    [
        "Tell me more about the NCC camp",
        "What about the fees for semester 3?",
        "What is the fee for the AI branch?",
        "I told my HOD about my leave, what happens next?",
    ],
)
def test_self_contained_questions_are_not_intercepted(monkeypatch, query):
    _fake_model(monkeypatch, Classification(domain="D5", confidence=0.9))
    monkeypatch.setattr(router, "retrieve", lambda domain_code, query: [])
    assert answer_query(query)["answer"] != NO_EARLIER_MESSAGES_REPLY


# --- Vague questions flagged by the classifier ---


def test_bare_topic_gets_the_classifiers_clarifying_question(monkeypatch):
    # QA repro 1: "fees?" used to get a long fee dump.
    flagged = Classification(
        domain="D5", confidence=0.9, needs_clarification=True, clarifying_question=f"  {ASK_PROGRAMME} "
    )
    prompts = _fake_model(monkeypatch, flagged)
    _no_retrieval(monkeypatch)

    result = answer_query("fees?")

    assert result["answer"] == ASK_PROGRAMME
    assert result["documents"] == []
    assert len(prompts) == 1  # the classification only, no answer generated


def test_flag_without_a_question_is_ignored(monkeypatch):
    _fake_model(monkeypatch, Classification(domain="D5", confidence=0.9, needs_clarification=True))
    monkeypatch.setattr(router, "retrieve", lambda domain_code, query: [])
    assert classify_node({"query": "What is the fee for semester 3?"})["clarification"] is None


def test_classifier_is_told_when_there_is_no_earlier_conversation(monkeypatch):
    prompts = _fake_model(monkeypatch, Classification(domain="D5", confidence=0.9))
    classify_node({"query": "fees?"})
    classify_node({"query": "fees?", "history": HISTORY})
    assert "There is no earlier conversation" in prompts[0]
    assert "There is no earlier conversation" not in prompts[1]


def test_status_question_is_answered_rather_than_clarified():
    state = {"query": "Has it been approved?", "request_type": "status", "clarification": "Approved what?"}
    assert generate_node(state)["answer"].startswith("I can't see or track the status")


def test_action_request_is_still_declined_first():
    state = {"query": "Submit it for me", "domain": "D4", "request_type": "action",
             "clarification": "Submit what?", "low_confidence": True}
    assert generate_node(state)["answer"].startswith(ACTION_DECLINE)


# --- Live check against the real classifier (skipped without an API key) ---


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="requires a real GEMINI_API_KEY")
def test_live_bare_fee_question_is_clarified():
    result = answer_query("fees?")
    assert result["answer"].rstrip().endswith("?")
    assert result["documents"] == []
