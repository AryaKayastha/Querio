from querio_backend.router.router import _build_clarifying_message, _extract_text, generate_node, retrieve_node


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


def test_extract_text_handles_plain_string():
    assert _extract_text("hello") == "hello"


def test_extract_text_handles_content_block_list_with_opaque_parts():
    # Some Gemini models return content as [{"type": "text", ...}, <opaque non-text part>]
    content = [{"type": "text", "text": "hello "}, {"type": "thought_signature", "data": "xyz"}, {"type": "text", "text": "world"}]
    assert _extract_text(content) == "hello world"


def test_extract_text_handles_empty_list():
    assert _extract_text([]) == ""
