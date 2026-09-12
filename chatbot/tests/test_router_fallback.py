from querio_chatbot.router.router import (
    _build_clarifying_message,
    _extract_text,
    _format_history,
    generate_node,
    retrieve_node,
)


def test_retrieve_node_skips_retrieval_when_low_confidence():
    state = {"query": "something ambiguous", "domain": "D5", "low_confidence": True}
    assert retrieve_node(state) == {"documents": []}


def test_generate_node_asks_clarifying_question_naming_both_candidates():
    state = {
        "query": "something ambiguous",
        "domain": "D5",
        "alternative_domain": "D6",
        "low_confidence": True,
    }
    answer = generate_node(state)["answer"]
    assert "Formal Education" in answer
    assert "Leave Management" in answer


def test_generate_node_falls_back_to_generic_message_without_alternative():
    state = {"query": "something ambiguous", "domain": "D5", "low_confidence": True}
    answer = generate_node(state)["answer"]
    assert "rephrase" in answer.lower()


def test_build_clarifying_message_ignores_alternative_equal_to_primary_domain():
    message = _build_clarifying_message({"domain": "D5", "alternative_domain": "D5"})
    assert "rephrase" in message.lower()


def test_build_clarifying_message_never_names_unrouted_as_a_domain_option():
    # Regression test: when the classifier's primary guess is itself UNROUTED (with a real
    # domain as the alternative), the message used to leak "UNROUTED" verbatim, e.g.
    # "...whether your question is about UNROUTED or Formal Education."
    message = _build_clarifying_message({"domain": "UNROUTED", "alternative_domain": "D5"})
    assert "UNROUTED" not in message
    assert "rephrase" in message.lower()


def test_extract_text_handles_plain_string():
    assert _extract_text("hello") == "hello"


def test_extract_text_handles_content_block_list_with_opaque_parts():
    # Some Gemini models return content as [{"type": "text", ...}, <opaque non-text part>]
    content = [{"type": "text", "text": "hello "}, {"type": "thought_signature", "data": "xyz"}, {"type": "text", "text": "world"}]
    assert _extract_text(content) == "hello world"


def test_extract_text_handles_empty_list():
    assert _extract_text([]) == ""


def test_format_history_returns_empty_string_for_no_history():
    assert _format_history(None) == ""
    assert _format_history([]) == ""


def test_format_history_renders_student_and_assistant_lines():
    history = [
        {"role": "user", "content": "How much are the fees?"},
        {"role": "assistant", "content": "Grounded answer"},
    ]
    assert _format_history(history) == "Student: How much are the fees?\nAssistant: Grounded answer"


def test_format_history_truncates_to_the_last_turn_pairs():
    history = [{"role": "user", "content": f"question {i}"} for i in range(10)]
    formatted = _format_history(history, limit=2)
    assert formatted == "Student: question 6\nStudent: question 7\nStudent: question 8\nStudent: question 9"
