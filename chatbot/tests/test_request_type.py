"""Guidance-only boundary, request side (Project_Details/04_scope_and_guardrails.md §6), with the model
faked so no network is needed. QRO-08: status/tracking questions."""

from types import SimpleNamespace

import pytest

from querio_chatbot.config import DOMAINS
from querio_chatbot.router import router
from querio_chatbot.router.router import (
    DEFAULT_CONTACT,
    Classification,
    _request_type,
    answer_query,
    classify_node,
    generate_node,
    retrieve_node,
)

GENERATED = "Generated answer."


def _fake_model(monkeypatch, domain, request_type="information", confidence=0.9):
    """Classifier calls get `domain`; answer calls get GENERATED. Returns the answer prompts."""
    prompts = []

    def fake_invoke(build, prompt):
        if prompt.startswith("You are a routing classifier"):
            return Classification(domain=domain, confidence=confidence, request_type=request_type)
        prompts.append(prompt)
        return SimpleNamespace(content=GENERATED)

    monkeypatch.setattr(router, "invoke_with_fallback", fake_invoke)
    return prompts


def _no_retrieval(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("status questions must not trigger retrieval")

    monkeypatch.setattr(router, "retrieve", fail)


# --- QRO-08: status and tracking questions --------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "Has my leave been approved?",
        "What's the status of my NOC application?",
        "Confirm that my placement registration is completed",
        "I've submitted my leave form, confirm it's done",
        "has my medical leave request been approved yet",
        "Did my NOC get approved?",
        "Can you track my leave request?",
        "Is my placement registration complete?",
    ],
)
def test_status_wording_is_recognised_whatever_the_classifier_says(query):
    assert _request_type(query, "information") == "status"


@pytest.mark.parametrize(
    "query",
    [
        "How do I apply for leave?",
        "What documents do I need for an NOC?",
        "How do I confirm my registration for the placement drive?",
        "Is my NOC required to be submitted before the internship starts?",
        "Is my leave granted if I have a medical certificate?",
        "What happens if my leave is rejected?",
        "How long does it take for leave to be approved?",
    ],
)
def test_ordinary_questions_keep_the_classifiers_request_type(query):
    assert _request_type(query, "information") == "information"


def test_classifier_can_still_flag_a_status_question_the_wording_check_misses(monkeypatch):
    _fake_model(monkeypatch, "D6", request_type="status")
    assert classify_node({"query": "Did the HOD sign off on my leave?"})["request_type"] == "status"


@pytest.mark.parametrize(
    ("query", "domain", "contact_word"),
    [
        ("Has my leave been approved?", "D6", "HOD"),
        ("What's the status of my NOC application?", "D4", "CDPC"),
        ("Confirm that my placement registration is completed", "D4", "CDPC"),
    ],
)
def test_status_questions_say_querio_cannot_track_and_name_the_contact(monkeypatch, query, domain, contact_word):
    prompts = _fake_model(monkeypatch, domain)
    _no_retrieval(monkeypatch)

    result = answer_query(query)

    assert result["answer"].startswith("I can't see or track the status of your requests")
    assert contact_word in result["answer"]
    assert DOMAINS[domain].contact in result["answer"]
    assert result["documents"] == []  # no sources shown
    assert prompts == []  # no answer generated


def test_status_question_with_unclear_topic_uses_the_generic_contact():
    state = {"query": "Has it been approved?", "domain": "D6", "low_confidence": True, "request_type": "status"}
    answer = generate_node(state)["answer"]
    assert DEFAULT_CONTACT in answer
    assert "not fully sure" not in answer  # no clarifying question needed to say Querio can't track


def test_status_question_outside_every_domain_uses_the_generic_contact():
    state = {"query": "Has my hostel room been approved?", "domain": "UNROUTED", "request_type": "status"}
    assert DEFAULT_CONTACT in generate_node(state)["answer"]


def test_retrieval_is_skipped_for_status_questions(monkeypatch):
    _no_retrieval(monkeypatch)
    assert retrieve_node({"query": "Has my leave been approved?", "domain": "D6", "request_type": "status"}) == {
        "documents": []
    }


def test_every_domain_names_a_contact():
    for domain in DOMAINS.values():
        assert domain.contact, domain.code
