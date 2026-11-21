import re
from difflib import SequenceMatcher
from typing import Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from querio_chatbot.config import (
    CONFIDENCE_THRESHOLD,
    DOMAINS,
    GUIDANCE_ONLY_SYSTEM_NOTE,
    HISTORY_TURN_LIMIT,
)
from querio_chatbot.llm.chat import invoke_with_fallback
from querio_chatbot.retrieval.retriever import _significant_tokens, retrieve

# Placed right before the question in the prompt, where models follow formatting rules most
# reliably; the chat UI renders markdown (bullets, ### headings, links).
ANSWER_FORMAT_RULES = """Formatting rules for your answer (markdown, read in a chat window):
- Start with one sentence that directly answers the question. Don't open with "Based on the provided context".
- List three or more items as bullets. Start each bullet with the item's name or label in **bold**, then its detail. Never bold a whole sentence.
- If the answer has more than 8 bullets or several distinct groups, put each group under a short ### heading.
- Use at most one level of sub-bullets.
- If the question asks for a specific number of items (e.g. "top 5"), list exactly that many.
- Stop when the information ends: no closing summary or extra advice."""

NO_ANSWER_MESSAGE = (
    "I don't have information to answer that yet. Please check with the relevant "
    "department office, or try rephrasing your question."
)

# What Querio covers, built from config.DOMAINS so it stays in step with the active domains.
TOPICS_MESSAGE = "I can answer questions about these topics, for example:\n\n" + "\n".join(
    f'- **{domain.name}**: "{domain.example_question}"' if domain.example_question else f"- **{domain.name}**"
    for domain in DOMAINS.values()
)

# For UNROUTED questions: off-topic requests, jokes, insults -- and the occasional misrouted real
# question, so it doesn't claim the topic is out of scope, only that it couldn't place it.
OUT_OF_SCOPE_MESSAGE = (
    "I couldn't match that to any of the topics I cover, so I can't answer it. "
    f"{TOPICS_MESSAGE}\n\n"
    "If your question is about one of these, try rephrasing it with a bit more detail. "
    "For anything else, please check with the relevant department office."
)

GREETING_REPLY = f"Hi! I'm Querio, your college assistant. {TOPICS_MESSAGE}\n\nWhat would you like to know?"
THANKS_REPLY = "You're welcome! If you have another question, just ask."
GOODBYE_REPLY = "Goodbye, and good luck! Come back any time you have a question."

TOO_SHORT_REPLY = f"Please type your question in a few words and I'll do my best to help. {TOPICS_MESSAGE}"
# Fewer letters/digits than this ("?", "a", "") can't be a question, so no model call is spent on it.
_MIN_QUERY_ALNUM_CHARS = 2

# Messages that are nothing but small talk get a fixed reply with no model call. The whole message
# must be made of these phrases (plus filler such as "ok" or "Querio"), so "hi, what are the fees?"
# still goes to the router. Checked in this order: "thanks, bye" is answered as thanks.
_SMALL_TALK = (
    (
        THANKS_REPLY,
        r"thanks?(?: you)?|thank u|thanku|thankyou|thx|ty|tysm|much appreciated"
        r"|for (?:the|your) (?:help|info|information|answer|reply|time)",
    ),
    (GOODBYE_REPLY, r"bye+(?: bye+)?|good ?bye|good night|see (?:you|ya)(?: later)?|cya|take care"),
    (
        GREETING_REPLY,
        r"hi+|hey+|hello+|helo|hola|namaste|namaskar|kem cho|greetings|good (?:morning|afternoon|evening)"
        r"|how are you(?: doing)?|whats up",
    ),
)
_SMALL_TALK_FILLER = r"ok|okay|great|cool|nice|awesome|there|querio|bot|dear|sir|maam|so much|very much|a lot|and"
_SMALL_TALK_WORD = "|".join([*(pattern for _, pattern in _SMALL_TALK), _SMALL_TALK_FILLER])
_SMALL_TALK_MESSAGE = re.compile(rf"(?:{_SMALL_TALK_WORD})(?: (?:{_SMALL_TALK_WORD}))*")
# Small talk is short; the cap also bounds regex backtracking on long repetitive input.
_SMALL_TALK_MAX_CHARS = 60

# Derived from config.DOMAINS so newly activated domains are automatically valid structured-
# output values -- a hardcoded Literal here previously caused Gemini's structured output to
# silently coerce a correct classification into UNROUTED whenever the true domain wasn't listed.
# UNROUTED means the query didn't clearly match any active domain.
DomainCode = Literal[tuple(DOMAINS) + ("UNROUTED",)]


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
    request_type: Literal["information", "status", "action"] = Field(
        default="information",
        description=(
            "'status' if the student asks about the state of their OWN request, application, "
            "registration or record (e.g. 'Has my leave been approved?', 'What is the status of my "
            "NOC application?', 'Confirm that my registration is complete'). 'action' if they ask "
            "the assistant to do something for them (e.g. 'Register me for the placement drive', "
            "'Forward my NOC request to the HOD', 'Mark me present'). Otherwise 'information': they "
            "want to know a rule, process, eligibility, document or contact (e.g. 'How do I apply "
            "for leave?')."
        ),
    )


class ChatState(TypedDict, total=False):
    query: str
    history: list[dict]
    domain: str
    confidence: float
    alternative_domain: Optional[str]
    low_confidence: bool
    # "status": where their own request stands, which Querio can't know. "action": do something for
    # them, which Querio can't do. Both are declined (04_scope_and_guardrails.md §3).
    request_type: str
    # Everything retrieved, as given to the model (and to evaluation).
    documents: list
    answer: str
    # The few documents the answer draws on, shown to the student as citations.
    sources: list
    guidance_only: bool


# Querio never tracks requests (Project_Details/04_scope_and_guardrails.md), so phrasings that are
# unmistakably about the student's own request are recognised here rather than left to the
# classifier alone. Anything subtler is still caught by Classification.request_type.
_STATUS_REQUEST = re.compile(
    r"""
    \b(?:status|progress)\ of\ (?:my|our)\b                       # "the status of my NOC application"
    | \btrack\ (?:my|our)\b                                         # "track my leave request"
    | \b(?:has|have|is|was|were|did)\ (?:my|our)\ (?:[\w'-]+\ ){0,3}(?:been\ |got\ |get\ |gone\ )?
      (?:approved|accepted|rejected|processed|sanctioned|granted|forwarded|cleared|completed?|done
        |received|submitted|verified|confirmed|issued)
      (?:\ yet|\ already|\ or\ not)?\s*(?:[?.!]|$)                  # "has my leave been approved?",
                                                                    # not "is my leave granted if ..."
    | (?:^|[.!?,;]\s*|\b(?:please|pls|kindly|can\ you|could\ you)\ )
      confirm\ (?:that\ |whether\ |if\ )?(?:my|our|it|it's|its|this)\b  # "confirm my registration is done"
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Requests that open with an instruction to act on the student's own thing ("Forward my NOC request",
# "Register me for the drive", "Apply for leave on my behalf"). Kept narrow so questions phrased
# as commands ("Send me the syllabus") or about someone else acting ("Can my parents submit it on
# my behalf?") stay information requests.
_ACTION_REQUEST = re.compile(
    r"""
    ^(?:(?:please|pls|kindly|can\ you|could\ you|would\ you|will\ you|can\ u|i\ want\ you\ to|i\ need\ you\ to)\ )*
    (?:
      (?:submit|register|enrol|enroll|apply|forward|send|mark|approve|cancel|book|pay|update|fill|sign|file|raise|withdraw)
      (?:\ (?:my|our)\b|\b.*\b(?:for\ me|on\ my\ behalf)\b)       # "submit my ...", "apply ... on my behalf"
    | (?:register|enrol|enroll|sign|mark|book|add|put)\ (?:me|us)\b  # "register me ...", "mark me present"
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

DEFAULT_CONTACT = "the relevant department office"

ACTION_DECLINE = (
    "I can't do that for you: I can explain the process, but I can't submit, register, forward, approve "
    "or record anything on your behalf."
)

# Added to the answer prompt for an action request; the decline above is put in front of the answer.
ACTION_INSTRUCTION = (
    "The student asked you to do something for them, which you cannot do. That has already been "
    "said, so don't apologise or say it again. Explain only how they can do it themselves, as the "
    "context describes it: the steps, documents and who to contact. Leave out rules about anything "
    "else. If the context doesn't describe how to do it, say so in one sentence and suggest checking "
    "with {contact}."
)


def _request_type(query: str, classified: str) -> str:
    """The classifier's request type, unless the wording itself makes it a status or action request."""
    text = " ".join(query.replace("’", "'").split())
    if _STATUS_REQUEST.search(text):
        return "status"
    if _ACTION_REQUEST.search(text):
        return "action"
    return classified


def _status_reply(state: ChatState) -> str:
    """Fixed reply to "has my request been approved?": Querio can't know, so say who can."""
    domain = None if state.get("low_confidence") else DOMAINS.get(state.get("domain"))
    contact = domain.contact if domain and domain.contact else DEFAULT_CONTACT
    return (
        "I can't see or track the status of your requests, applications or records. I can only "
        f"explain the college's rules and processes, so to find out where yours stands, please check with {contact}."
    )


def _extract_text(content) -> str:
    """Some Gemini models return response.content as a list of content blocks
    (text parts plus opaque non-text parts like thought signatures) instead of
    a plain string -- pull just the text parts out."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "".join(parts)
    return str(content)


def _domain_name(code: Optional[str]) -> str:
    return DOMAINS[code].name if code in DOMAINS else str(code)


def _build_clarifying_message(state: ChatState) -> str:
    alternative = state.get("alternative_domain")
    domain = state["domain"]
    # Both sides must be real, known domains -- "UNROUTED" (the primary guess or the
    # alternative) has no friendly name and would otherwise leak into the message
    # verbatim, e.g. "...whether your question is about UNROUTED or Formal Education".
    if alternative and alternative != domain and alternative in DOMAINS and domain in DOMAINS:
        return (
            f"I'm not fully sure whether your question is about {_domain_name(domain)} "
            f"or {_domain_name(alternative)}. Could you clarify which one you mean?"
        )
    return (
        "I'm not fully sure which topic your question is about. Could you rephrase it with a bit more "
        f"detail? {TOPICS_MESSAGE}"
    )


def _small_talk_reply(query: str) -> Optional[str]:
    """The fixed reply if the message is only a greeting, thanks or goodbye, otherwise None."""
    text = " ".join(re.sub(r"[^\w\s]|_", " ", re.sub(r"['’]", "", query.lower())).split())
    if not text or len(text) > _SMALL_TALK_MAX_CHARS or not _SMALL_TALK_MESSAGE.fullmatch(text):
        return None
    for reply, pattern in _SMALL_TALK:
        if re.search(rf"\b(?:{pattern})\b", text):
            return reply
    return None  # Only filler ("ok", "cool"): let the router handle it.


def _format_history(history: Optional[list[dict]], limit: int = HISTORY_TURN_LIMIT) -> str:
    """Render the last `limit` user+assistant turn pairs as plain dialogue lines for
    prompt context. Returns "" for empty/missing history so prompts are byte-for-byte
    unchanged when no history is provided (single-turn behavior stays untouched)."""
    if not history:
        return ""
    recent = history[-(2 * limit):]
    lines = []
    for turn in recent:
        speaker = "Assistant" if turn.get("role") == "assistant" else "Student"
        lines.append(f"{speaker}: {turn.get('content', '')}")
    return "\n".join(lines)


def classify_node(state: ChatState) -> ChatState:
    domain_descriptions = "\n".join(f"- {code}: {d.name} — {d.description}" for code, d in DOMAINS.items())
    history_block = _format_history(state.get("history"))
    history_section = (
        f"\nRecent conversation (context only -- use it just to resolve what a follow-up "
        f"question or a reply to your own earlier clarifying question refers to, not to "
        f"override what's actually being asked now):\n{history_block}\n"
        if history_block
        else ""
    )
    prompt = (
        "You are a routing classifier for a college assistant. The assistant currently only "
        f"handles these domains:\n{domain_descriptions}\n\n"
        "If the question is about anything outside the domains listed above, respond UNROUTED. "
        "Do not force a question into a domain just because it's the closest available option.\n"
        f"{history_section}\n"
        f"Question: {state['query']}"
    )
    result = invoke_with_fallback(lambda model: model.with_structured_output(Classification), prompt)
    return {
        "domain": result.domain,
        "confidence": result.confidence,
        "alternative_domain": result.alternative_domain,
        "low_confidence": result.confidence < CONFIDENCE_THRESHOLD,
        "request_type": _request_type(state["query"], result.request_type),
    }


def retrieve_node(state: ChatState) -> ChatState:
    if state.get("low_confidence") or state.get("request_type") == "status":
        # A status question gets a fixed reply, so there is nothing to look up (and no sources to show).
        return {"documents": []}
    domain_code = state["domain"]
    if domain_code not in DOMAINS:
        return {"documents": []}
    documents = retrieve(domain_code, state["query"])
    return {"documents": documents, "guidance_only": DOMAINS[domain_code].guidance_only}


def generate_node(state: ChatState) -> ChatState:
    if state.get("request_type") == "status":
        # Before the clarifying question: "has my request been approved?" needs no topic to answer.
        return {"answer": _status_reply(state)}

    action = state.get("request_type") == "action"
    domain = DOMAINS.get(state.get("domain"))
    if action and (state.get("low_confidence") or domain is None):
        # No topic to explain a process from: decline, then say what Querio does cover.
        return {"answer": f"{ACTION_DECLINE}\n\n{TOPICS_MESSAGE}"}

    if state.get("low_confidence"):
        return {"answer": _build_clarifying_message(state)}

    documents = state.get("documents", [])
    if not documents:
        if state.get("domain") not in DOMAINS:
            # UNROUTED: tell the student what Querio does cover instead of a bare "no information".
            return {"answer": OUT_OF_SCOPE_MESSAGE}
        return {"answer": f"{ACTION_DECLINE}\n\n{NO_ANSWER_MESSAGE}" if action else NO_ANSWER_MESSAGE}

    context = "\n\n".join(
        f"[{doc.metadata.get('source_name', 'unknown')} — {doc.metadata.get('source_section', '')}]\n{doc.page_content}"
        for doc in documents
    )
    system_instructions = [
        "Answer the student's question using ONLY the provided context.",
        "The context may state a policy or requirement in general/administrative language rather "
        "than phrasing it as a direct answer -- if it clearly implies the answer, state that answer "
        "plainly instead of treating the difference in phrasing as missing information. Only say "
        "you don't have the information if the context truly doesn't address the question -- "
        "never invent a fact the context doesn't state.",
        "Do not cite sources, page numbers, or section names within your answer, and do not add a "
        "closing sentence summarizing what you cited -- the student sees the source documents "
        "separately, so inline citations only clutter the answer.",
        "Talk to the student directly and never mention 'the context' or 'the provided context' -- "
        "the student doesn't know what that is. If the context doesn't answer the question, say you "
        "couldn't find that in the college documents and suggest checking with the relevant office "
        "(name a specific person or office only if the context gives one).",
    ]
    if state.get("guidance_only"):
        system_instructions.append(GUIDANCE_ONLY_SYSTEM_NOTE)
    if domain and domain.answer_instructions:
        system_instructions.append(domain.answer_instructions)
    if action:
        system_instructions.append(ACTION_INSTRUCTION.format(contact=domain.contact or DEFAULT_CONTACT))

    history_block = _format_history(state.get("history"))
    if history_block:
        system_instructions.append(
            "Recent conversation is provided below for conversational continuity only -- "
            "treat it purely as context, never as a newly established fact, and continue to "
            "answer strictly from the Context documents."
        )

    history_section = f"\n\nRecent conversation:\n{history_block}" if history_block else ""
    prompt = (
        "\n".join(system_instructions)
        + history_section
        + f"\n\nContext:\n{context}\n\n{ANSWER_FORMAT_RULES}\n\nQuestion: {state['query']}\n\nAnswer:"
    )
    response = invoke_with_fallback(lambda model: model, prompt)
    answer = _student_facing(_extract_text(response.content))
    sources = _select_sources(answer, documents)
    if action:
        # Fixed text, so the decline can't be dropped or reworded by the model.
        answer = f"{ACTION_DECLINE}\n\n{answer}"
    if domain and domain.answer_disclaimer:
        answer = _append_disclaimer(answer, domain.answer_disclaimer)
    return {"answer": answer, "sources": sources}


MAX_SOURCES = 3
# A document is cited if it shares at least this share of the answer words that the best-matching
# document shares -- so pages retrieved for a stray word (e.g. "semester") are left out.
SOURCE_MIN_SHARE = 0.5
# An answer whose first sentence says the documents don't cover the question, and that is no longer
# than this, has nothing to cite.
_NOT_FOUND_MAX_CHARS = 400
_NOT_FOUND_ANSWER = re.compile(
    r"^[^.!?\n]*\b(?:"
    r"couldn't find|could not find|can't find|cannot find|no information"
    r"|(?:don't|do not) have (?:any |the )?information"
    r"|(?:does not|doesn't|do not|don't) (?:mention|specify|say|cover|contain|include|state)"
    r"|(?:is|are) not (?:mentioned|specified|covered|stated|listed)"
    r")\b",
    re.IGNORECASE,
)


def _select_sources(answer: str, documents: list) -> list:
    """The few retrieved documents the answer draws on, most-used first, one per source section.
    None when the answer only says the documents don't cover the question."""
    answer = answer.replace("’", "'")
    if not documents or (len(answer) <= _NOT_FOUND_MAX_CHARS and _NOT_FOUND_ANSWER.search(answer)):
        return []
    answer_tokens = _significant_tokens(answer)
    scored = [
        (len(answer_tokens & _significant_tokens(doc.page_content)), rank, doc)
        for rank, doc in enumerate(documents)
    ]
    best = max(score for score, _, _ in scored)
    if best == 0:
        return documents[:1]  # answer shares no words with anything: fall back to the top retrieved
    picked, seen = [], set()
    for score, _, doc in sorted(scored, key=lambda item: (-item[0], item[1])):
        key = (doc.metadata.get("source_name"), doc.metadata.get("source_section"))
        if score < SOURCE_MIN_SHARE * best or key in seen:
            continue
        seen.add(key)
        picked.append(doc)
        if len(picked) == MAX_SOURCES:
            break
    return picked


# Prompt wording the model sometimes echoes to the student ("The provided context does not mention...").
# "the context of ..." is ordinary English and left alone.
_CONTEXT_PHRASE = re.compile(
    r"\bthe\s+(?:(?:provided|given|supplied|available|retrieved)\s+)?context"
    r"(?:\s+(?:provided|given|supplied)\b)?(?!\s+of\b)\b",
    re.IGNORECASE,
)


def _student_facing(answer: str) -> str:
    """Replace leaked prompt wording with plain language. The replacement is singular like "context",
    so the verb that follows still agrees ("The information I have does not mention...")."""
    return _CONTEXT_PHRASE.sub(
        lambda match: "The information I have" if match.group(0)[0].isupper() else "the information I have",
        answer,
    )


def _plain(text: str) -> str:
    return " ".join(re.sub(r"[*_`>]", " ", text).lower().split())


def _append_disclaimer(answer: str, disclaimer: str) -> str:
    """Append the domain disclaimer exactly once.

    Earlier answers in the conversation end with the disclaimer, and the model imitates them, so its
    own (sometimes reworded) copy is dropped before the official one is appended.
    """
    target = _plain(disclaimer)
    kept = [
        line for line in answer.splitlines()
        if not line.strip() or SequenceMatcher(None, _plain(line), target).ratio() < 0.8
    ]
    body = "\n".join(kept).rstrip()
    return f"{body}\n\n{disclaimer}"


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


def _fixed_reply(query: str, history: Optional[list[dict]], answer: str, confidence: float) -> ChatState:
    """A complete result for a message answered without routing, retrieval or a model call."""
    return {
        "query": query,
        "history": history or [],
        "domain": "UNROUTED",
        "confidence": confidence,
        "documents": [],
        "answer": answer,
        "guidance_only": False,
    }


def answer_query(query: str, history: Optional[list[dict]] = None) -> ChatState:
    if len(re.findall(r"[^\W_]", query)) < _MIN_QUERY_ALNUM_CHARS:
        return _fixed_reply(query, history, TOO_SHORT_REPLY, confidence=0.0)
    small_talk = _small_talk_reply(query)
    if small_talk is not None:
        return _fixed_reply(query, history, small_talk, confidence=1.0)
    return get_graph().invoke({"query": query, "history": history or []})
