"""QRO-17: student-facing answers must not echo prompt wording such as "the provided context"."""

from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from querio_chatbot.router import router
from querio_chatbot.router.router import _student_facing, generate_node

DOC = [Document(page_content="Clubs at CSPIT: AI/ML Club, Robotics Club", metadata={"source_name": "Clubs"})]


@pytest.mark.parametrize(
    ("model_answer", "expected"),
    [
        (
            "The provided context does not mention a quantum computing club.",
            "The information I have does not mention a quantum computing club.",
        ),
        ("Based on the given context, the penalty is Rs. 300.", "Based on the information I have, the penalty is Rs. 300."),
        ("The context provided doesn't say.", "The information I have doesn't say."),
        ("This isn't covered in the context.", "This isn't covered in the information I have."),
        ("THE PROVIDED CONTEXT is silent on this.", "The information I have is silent on this."),
    ],
)
def test_prompt_wording_is_rewritten(model_answer, expected):
    assert _student_facing(model_answer) == expected


@pytest.mark.parametrize(
    "answer",
    [
        "In the context of placements, a pool campus drive is open to several colleges.",
        "Your attendance is counted per subject.",
    ],
)
def test_ordinary_text_is_left_alone(answer):
    assert _student_facing(answer) == answer


def test_generated_answer_never_says_provided_context(monkeypatch):
    prompts = []

    def fake_invoke(build, prompt):
        prompts.append(prompt)
        return SimpleNamespace(content="The provided context does not mention a quantum computing club.")

    monkeypatch.setattr(router, "invoke_with_fallback", fake_invoke)
    state = {"query": "Does CSPIT have a quantum computing club?", "domain": "D1", "documents": DOC}
    answer = generate_node(state)["answer"]

    assert "provided context" not in answer.lower()
    assert "college documents" in prompts[0]  # the prompt asks for the student-friendly phrasing
