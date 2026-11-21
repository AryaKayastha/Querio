"""QRO-12: citations show the few documents the answer draws on, and none on "not found" answers."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from querio_chatbot import app as app_module
from querio_chatbot.router import router
from querio_chatbot.router.router import MAX_SOURCES, _select_sources, generate_node


def _doc(text, name, section="Page 1"):
    return Document(page_content=text, metadata={"source_name": name, "source_section": section})


SEM5 = _doc("Semester 5 electives: Machine Learning, Cloud Computing, Cyber Security.", "Semester_5_Courses")
NEP = _doc("5th Sem NEP scheme. Professional electives: Machine Learning, Cloud Computing.", "5th SemNEP", "Page 3")
FY = _doc("First year booklet: semester credits, examination scheme and grading.", "FY_Booklet", "Page 5")
SY = _doc("Second year booklet: semester 3 and 4 credit structure.", "SY_Booklet", "Page 2")
ELECTIVES_ANSWER = "The electives offered in semester 5 are Machine Learning, Cloud Computing and Cyber Security."


def _names(docs):
    return [doc.metadata["source_name"] for doc in docs]


def test_only_documents_the_answer_draws_on_are_cited():
    # QA case: "Which electives are available in semester 5?" cited FY Booklet p5 and SY Booklet p2.
    assert _names(_select_sources(ELECTIVES_ANSWER, [FY, SEM5, SY, NEP])) == ["Semester_5_Courses", "5th SemNEP"]


def test_at_most_three_sources_are_cited():
    docs = [_doc(f"Machine Learning Cloud Computing Cyber Security {i}", f"Doc{i}") for i in range(8)]
    assert len(_select_sources(ELECTIVES_ANSWER, docs)) == MAX_SOURCES


def test_each_source_section_is_cited_once():
    twin = _doc("More on Machine Learning and Cloud Computing electives.", "Semester_5_Courses")
    assert _names(_select_sources(ELECTIVES_ANSWER, [SEM5, twin])) == ["Semester_5_Courses"]


@pytest.mark.parametrize(
    "answer",
    [
        "The information I have does not mention how to apply for condonation. Please check with your department office.",
        "I couldn't find that in the college documents. Please check with the relevant office.",
        "I don’t have information about a quantum computing club.",
        "Condonation is not mentioned in the attendance policy.",
    ],
)
def test_not_found_answers_cite_nothing(answer):
    # QA case: "How do I apply for condonation..." said "no information" but listed 8 sources.
    assert _select_sources(answer, [FY, SEM5, SY, NEP] * 2) == []


def test_partial_answer_that_opens_with_a_gap_still_cites_its_sources():
    answer = (
        "The guidelines don't specify a deadline for semester 5 elective selection, but they do list the "
        "options. " + ELECTIVES_ANSWER + " Each elective carries the same credits, and you choose one in "
        "the elective selection round announced by your department before the semester begins, so keep "
        "an eye on department notices for the exact date."
    )
    assert len(answer) > 400
    assert "Semester_5_Courses" in _names(_select_sources(answer, [FY, SEM5, SY, NEP]))


def test_generate_node_returns_the_cited_sources_and_keeps_all_documents_for_the_model(monkeypatch):
    prompts = []

    def fake_invoke(build, prompt):
        prompts.append(prompt)
        return SimpleNamespace(content=ELECTIVES_ANSWER)

    monkeypatch.setattr(router, "invoke_with_fallback", fake_invoke)
    result = generate_node({"query": "Which electives are in semester 5?", "domain": "D5", "documents": [FY, SEM5, SY, NEP]})

    assert _names(result["sources"]) == ["Semester_5_Courses", "5th SemNEP"]
    assert "First year booklet" in prompts[0]  # the model still sees everything retrieved


def test_chat_api_lists_only_the_cited_sources(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "answer_query",
        lambda query, history: {
            "answer": ELECTIVES_ANSWER,
            "domain": "D5",
            "confidence": 0.9,
            "documents": [FY, SEM5, SY, NEP],
            "sources": [SEM5],
        },
    )
    body = TestClient(app_module.app).post("/chat", json={"query": "Which electives are in semester 5?"}).json()
    assert [source["source_name"] for source in body["sources"]] == ["Semester_5_Courses"]
