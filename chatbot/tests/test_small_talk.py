"""QRO-15: greetings, thanks, chit-chat and abuse get a friendly reply naming the topics Querio covers,
not the cold "I don't have information to answer that yet"."""

import pytest

from querio_chatbot.config import DOMAINS
from querio_chatbot.router import router
from querio_chatbot.router.router import (
    GOODBYE_REPLY,
    GREETING_REPLY,
    NO_ANSWER_MESSAGE,
    OUT_OF_SCOPE_MESSAGE,
    THANKS_REPLY,
    Classification,
    _build_clarifying_message,
    _small_talk_reply,
    answer_query,
    generate_node,
)


def _assert_lists_every_topic(message):
    for domain in DOMAINS.values():
        assert domain.name in message


@pytest.fixture
def no_model(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("small talk must be answered without the graph or a model call")

    monkeypatch.setattr(router, "invoke_with_fallback", fail)
    monkeypatch.setattr(router, "get_graph", fail)


@pytest.mark.parametrize(
    "message", ["hi", "Hi!", "hello there", "Hey Querio 👋", "hiii", "Good morning sir", "namaste", "kem cho"]
)
def test_greetings_get_the_topic_list_without_a_model_call(no_model, message):
    result = answer_query(message)
    assert result["answer"] == GREETING_REPLY
    _assert_lists_every_topic(result["answer"])
    assert result["domain"] == "UNROUTED"
    assert result["documents"] == []
    assert result["guidance_only"] is False


@pytest.mark.parametrize(
    "message", ["thanks", "Thank you so much!", "ok thanks", "thx", "Thanks for the help", "thank you, bye"]
)
def test_thanks_get_a_friendly_reply_without_a_model_call(no_model, message):
    assert answer_query(message)["answer"] == THANKS_REPLY


@pytest.mark.parametrize("message", ["bye", "Goodbye!", "see you later", "ok bye bye"])
def test_goodbyes_get_a_friendly_reply_without_a_model_call(no_model, message):
    assert answer_query(message)["answer"] == GOODBYE_REPLY


@pytest.mark.parametrize(
    "message",
    [
        "hi, what are the fees for semester 3?",
        "hello can you tell me the dress code",
        "history of the college",  # starts with "hi" but is not a greeting
        "thanks but that answer is wrong",
        "Tell me a joke",
        "you are a stupid useless bot",
        "ok",  # filler alone is left to the router
    ],
)
def test_messages_with_anything_else_in_them_are_not_small_talk(message):
    assert _small_talk_reply(message) is None


def test_long_repetitive_input_is_not_matched():
    assert _small_talk_reply("bye " * 5000) is None


@pytest.mark.parametrize("confidence", [1.0, 0.4])
@pytest.mark.parametrize("message", ["Tell me a joke", "you are a stupid useless bot"])
def test_chit_chat_and_abuse_get_a_polite_redirect_listing_the_topics(monkeypatch, message, confidence):
    # The router sends these to UNROUTED; whether it's sure (1.0) or not (0.4), the reply must name the topics.
    monkeypatch.setattr(
        router,
        "invoke_with_fallback",
        lambda build, prompt: Classification(domain="UNROUTED", confidence=confidence),
    )
    answer = answer_query(message)["answer"]
    _assert_lists_every_topic(answer)
    assert NO_ANSWER_MESSAGE not in answer


def test_unrouted_question_gets_the_out_of_scope_message():
    state = {"query": "Who won the IPL last year?", "domain": "UNROUTED", "confidence": 0.95, "documents": []}
    assert generate_node(state)["answer"] == OUT_OF_SCOPE_MESSAGE


def test_domain_with_nothing_retrieved_still_says_no_information():
    state = {"query": "What is the fee?", "domain": "D5", "confidence": 0.9, "documents": []}
    assert generate_node(state)["answer"] == NO_ANSWER_MESSAGE


def test_generic_clarifying_question_lists_the_topics():
    message = _build_clarifying_message({"domain": "UNROUTED", "alternative_domain": None})
    assert "rephrase" in message.lower()
    _assert_lists_every_topic(message)


def test_every_active_domain_has_an_example_question():
    for domain in DOMAINS.values():
        assert domain.example_question.endswith("?"), domain.code
        assert f'"{domain.example_question}"' in GREETING_REPLY
