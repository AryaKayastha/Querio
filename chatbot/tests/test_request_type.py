"""Guidance-only boundary, request side (Project_Details/04_scope_and_guardrails.md §6), with the model
faked so no network is needed. QRO-08: status/tracking questions. QRO-09: direct action requests."""

from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from querio_chatbot.config import DOMAINS
from querio_chatbot.router import router
from querio_chatbot.router.router import (
    ACTION_DECLINE,
    DEFAULT_CONTACT,
    TOPICS_MESSAGE,
    Classification,
    _request_type,
    answer_query,
    classify_node,
    generate_node,
    retrieve_node,
)

GENERATED = "Generated answer."
DOCS = [Document(page_content="Register for each drive on the CDPC portal.", metadata={"source_name": "Guidelines"})]


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


# --- QRO-09: direct action requests ---------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "Register me for the Meditab placement drive",
        "Forward my NOC request to the HOD",
        "Mark me present for yesterday's lecture",
        "Submit my NOC request for me",
        "Apply for leave on my behalf",
        "Please submit my leave application",
        "Can you register me for the NSS camp?",
        "Sign me up for the hackathon",
    ],
)
def test_action_wording_is_recognised_whatever_the_classifier_says(query):
    assert _request_type(query, "information") == "action"


@pytest.mark.parametrize(
    "query",
    [
        "How do I register for the Meditab drive?",
        "apply leave process",
        "Send me the syllabus for semester 5",
        "Can my parents submit the undertaking on my behalf?",
        "What is the process to forward an NOC request to the HOD?",
        "Register for placements: what is the eligibility?",
    ],
)
def test_questions_that_only_mention_an_action_are_not_action_requests(query):
    assert _request_type(query, "information") == "information"


def test_classifier_can_still_flag_an_action_request_the_wording_check_misses(monkeypatch):
    _fake_model(monkeypatch, "D4", request_type="action")
    assert classify_node({"query": "I want to join the Meditab drive, do it for me"})["request_type"] == "action"


@pytest.mark.parametrize(
    ("query", "domain"),
    [
        ("Register me for the Meditab placement drive", "D4"),
        ("Forward my NOC request to the HOD", "D4"),
        ("Mark me present for yesterday's lecture", "D6"),
    ],
)
def test_action_requests_start_with_a_decline_then_explain_the_process(monkeypatch, query, domain):
    prompts = _fake_model(monkeypatch, domain)
    monkeypatch.setattr(router, "retrieve", lambda domain_code, query: DOCS)

    answer = answer_query(query)["answer"]

    assert answer.startswith(ACTION_DECLINE)
    assert answer == f"{ACTION_DECLINE}\n\n{GENERATED}"
    # The model is told to stick to how the student can do it, naming the domain's contact.
    assert "Explain only how they can do it themselves" in prompts[0]
    assert DOMAINS[domain].contact in prompts[0]


def test_action_request_outside_every_domain_is_declined_with_the_topic_list(monkeypatch):
    prompts = _fake_model(monkeypatch, "UNROUTED")
    answer = answer_query("Book me a cab to the airport")["answer"]
    assert answer == f"{ACTION_DECLINE}\n\n{TOPICS_MESSAGE}"
    assert prompts == []


def test_action_request_with_unclear_topic_is_still_declined_first():
    state = {"query": "Submit it for me", "domain": "D4", "low_confidence": True, "request_type": "action"}
    assert generate_node(state)["answer"].startswith(ACTION_DECLINE)


def test_information_requests_get_no_decline(monkeypatch):
    prompts = _fake_model(monkeypatch, "D4")
    monkeypatch.setattr(router, "retrieve", lambda domain_code, query: DOCS)
    answer = answer_query("How do I register for the Meditab drive?")["answer"]
    assert answer == GENERATED
    assert "Explain only how they can do it themselves" not in prompts[0]
