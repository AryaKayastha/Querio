from querio_backend.session_store import InMemorySessionStore


def test_get_recent_returns_empty_list_for_unknown_session():
    store = InMemorySessionStore()
    assert store.get_recent("unknown") == []


def test_append_then_get_recent_preserves_order():
    store = InMemorySessionStore()
    store.append("s1", "user", "How much are the fees?")
    store.append("s1", "assistant", "Grounded answer")

    assert store.get_recent("s1") == [
        {"role": "user", "content": "How much are the fees?"},
        {"role": "assistant", "content": "Grounded answer"},
    ]


def test_history_is_truncated_to_turn_limit():
    store = InMemorySessionStore(turn_limit=1)
    store.append("s1", "user", "first question")
    store.append("s1", "assistant", "first answer")
    store.append("s1", "user", "second question")
    store.append("s1", "assistant", "second answer")

    assert store.get_recent("s1") == [
        {"role": "user", "content": "second question"},
        {"role": "assistant", "content": "second answer"},
    ]


def test_sessions_are_isolated_from_each_other():
    store = InMemorySessionStore()
    store.append("s1", "user", "session one question")
    store.append("s2", "user", "session two question")

    assert store.get_recent("s1") == [{"role": "user", "content": "session one question"}]
    assert store.get_recent("s2") == [{"role": "user", "content": "session two question"}]


def test_oldest_session_is_evicted_once_capacity_is_exceeded():
    store = InMemorySessionStore(max_sessions=2)
    store.append("s1", "user", "q1")
    store.append("s2", "user", "q2")
    store.append("s3", "user", "q3")

    assert store.get_recent("s1") == []
    assert store.get_recent("s2") == [{"role": "user", "content": "q2"}]
    assert store.get_recent("s3") == [{"role": "user", "content": "q3"}]
