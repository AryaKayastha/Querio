from typing import Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from querio_chatbot.config import CONFIDENCE_THRESHOLD, DOMAINS, GUIDANCE_ONLY_SYSTEM_NOTE
from querio_chatbot.llm.gemini_client import get_chat_model
from querio_chatbot.retrieval.retriever import retrieve

NO_ANSWER_MESSAGE = (
    "I don't have information to answer that yet. Please check with the relevant "
    "department office, or try rephrasing your question."
)

# NOTE: keep this Literal in sync with the active keys in config.DOMAINS as domains
# are brought online (currently D5, D6). UNROUTED means the query didn't clearly
# match any active domain.
DomainCode = Literal["D5", "D6", "UNROUTED"]


class Classification(BaseModel):
    domain: DomainCode = Field(description="The single best matching domain, or UNROUTED if none fit")
    confidence: float = Field(ge=0, le=1, description="How confident you are in this domain, from 0 to 1")
    alternative_domain: Optional[DomainCode] = Field(
        default=None,
        description=(
            "The second-most-likely domain if the query could plausibly belong to more "
            "than one, otherwise null"
        ),
    )


class ChatState(TypedDict, total=False):
    query: str
    domain: str
    confidence: float
    alternative_domain: Optional[str]
    low_confidence: bool
    documents: list
    answer: str
    guidance_only: bool


def _domain_name(code: Optional[str]) -> str:
    return DOMAINS[code].name if code in DOMAINS else str(code)


def _build_clarifying_message(state: ChatState) -> str:
    alternative = state.get("alternative_domain")
    if alternative and alternative != state["domain"] and alternative in DOMAINS:
        return (
            f"I'm not fully sure whether your question is about {_domain_name(state['domain'])} "
            f"or {_domain_name(alternative)}. Could you clarify which one you mean?"
        )
    return "I'm not fully sure which topic your question is about. Could you rephrase it with a bit more detail?"


def classify_node(state: ChatState) -> ChatState:
    domain_descriptions = "\n".join(f"- {code}: {d.name}" for code, d in DOMAINS.items())
    prompt = (
        "You are a routing classifier for a college assistant. Given the student's "
        f"question, choose the single best matching domain from:\n{domain_descriptions}\n"
        "If the question doesn't clearly match any of these, respond UNROUTED.\n\n"
        f"Question: {state['query']}"
    )
    structured_llm = get_chat_model().with_structured_output(Classification)
    result = structured_llm.invoke(prompt)
    return {
        "domain": result.domain,
        "confidence": result.confidence,
        "alternative_domain": result.alternative_domain,
        "low_confidence": result.confidence < CONFIDENCE_THRESHOLD,
    }


def retrieve_node(state: ChatState) -> ChatState:
    if state.get("low_confidence"):
        return {"documents": []}
    domain_code = state["domain"]
    if domain_code not in DOMAINS:
        return {"documents": []}
    documents = retrieve(domain_code, state["query"])
    return {"documents": documents, "guidance_only": DOMAINS[domain_code].guidance_only}


def generate_node(state: ChatState) -> ChatState:
    if state.get("low_confidence"):
        return {"answer": _build_clarifying_message(state)}

    documents = state.get("documents", [])
    if not documents:
        return {"answer": NO_ANSWER_MESSAGE}

    context = "\n\n".join(
        f"[{doc.metadata.get('source_name', 'unknown')} — {doc.metadata.get('source_section', '')}]\n{doc.page_content}"
        for doc in documents
    )
    system_instructions = [
        "Answer the student's question using ONLY the provided context.",
        "Cite the source document name for any facts you use.",
        "If the context doesn't contain the answer, say you don't have that information -- do not guess.",
    ]
    if state.get("guidance_only"):
        system_instructions.append(GUIDANCE_ONLY_SYSTEM_NOTE)

    prompt = (
        "\n".join(system_instructions)
        + f"\n\nContext:\n{context}\n\nQuestion: {state['query']}\n\nAnswer:"
    )
    response = get_chat_model().invoke(prompt)
    return {"answer": response.content}


def build_graph():
    graph = StateGraph(ChatState)
    graph.add_node("classify", classify_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def answer_query(query: str) -> ChatState:
    return get_graph().invoke({"query": query})
