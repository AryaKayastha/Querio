"""In-memory short-term conversation memory, keyed by client-supplied session_id.

This is the intended seam for the database work planned in Project_Details/03_data_requirements.md
(the query-log Postgres schema): swap InMemorySessionStore for a Postgres/Redis-backed
implementation of the same get_recent/append methods and nothing in bridge.py, the chatbot
service, or the frontend needs to change.
"""

from collections import OrderedDict
from typing import Literal, TypedDict

HISTORY_TURN_LIMIT = 3
MAX_TRACKED_SESSIONS = 500


class Turn(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class InMemorySessionStore:
    def __init__(self, turn_limit: int = HISTORY_TURN_LIMIT, max_sessions: int = MAX_TRACKED_SESSIONS):
        self._turn_limit = turn_limit
        self._max_sessions = max_sessions
        self._sessions: "OrderedDict[str, list[Turn]]" = OrderedDict()

    def get_recent(self, session_id: str) -> list[Turn]:
        return list(self._sessions.get(session_id, []))

    def append(self, session_id: str, role: Literal["user", "assistant"], content: str) -> None:
        turns = self._sessions.setdefault(session_id, [])
        turns.append({"role": role, "content": content})
        max_entries = 2 * self._turn_limit
        if len(turns) > max_entries:
            del turns[:-max_entries]
        self._sessions.move_to_end(session_id)
        while len(self._sessions) > self._max_sessions:
            self._sessions.popitem(last=False)


session_store = InMemorySessionStore()
