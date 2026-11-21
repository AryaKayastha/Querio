import pytest

from querio_chatbot.llm import chat


class FakeModel:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def invoke(self, prompt):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


@pytest.fixture(autouse=True)
def fresh_cooldowns():
    chat.reset_provider_cooldowns()
    yield
    chat.reset_provider_cooldowns()


@pytest.fixture
def providers(monkeypatch):
    def install(*pairs):
        monkeypatch.setattr(chat, "chat_providers", lambda: tuple(pairs))

    return install


def test_uses_first_provider_when_it_succeeds(providers):
    gemini, groq = FakeModel(result="gemini answer"), FakeModel(result="groq answer")
    providers(("gemini", gemini), ("groq", groq))

    assert chat.invoke_with_fallback(lambda model: model, "q") == "gemini answer"
    assert groq.calls == 0


def test_falls_back_when_first_provider_fails(providers):
    gemini = FakeModel(error=TimeoutError("504 DEADLINE_EXCEEDED"))
    groq = FakeModel(result="groq answer")
    providers(("gemini", gemini), ("groq", groq))

    assert chat.invoke_with_fallback(lambda model: model, "q") == "groq answer"


def test_empty_structured_result_counts_as_failure(providers):
    providers(("gemini", FakeModel(result=None)), ("groq", FakeModel(result="groq answer")))

    assert chat.invoke_with_fallback(lambda model: model, "q") == "groq answer"


def test_raises_last_error_when_every_provider_fails(providers):
    providers(("gemini", FakeModel(error=TimeoutError("gemini down"))), ("groq", FakeModel(error=RuntimeError("groq down"))))

    with pytest.raises(RuntimeError, match="groq down"):
        chat.invoke_with_fallback(lambda model: model, "q")


# QRO-13: a failing provider is benched for a while instead of being retried on every call.


def test_failed_provider_is_skipped_on_the_next_calls(providers):
    gemini = FakeModel(error=TimeoutError("504 DEADLINE_EXCEEDED"))
    groq = FakeModel(result="groq answer")
    providers(("gemini", gemini), ("groq", groq))

    for _ in range(3):
        assert chat.invoke_with_fallback(lambda model: model, "q") == "groq answer"
    assert gemini.calls == 1
    assert groq.calls == 3


def test_failed_provider_is_tried_again_after_the_cooldown(providers, monkeypatch):
    monkeypatch.setattr(chat, "PROVIDER_COOLDOWN_SECONDS", 0)
    gemini = FakeModel(error=TimeoutError("504 DEADLINE_EXCEEDED"))
    providers(("gemini", gemini), ("groq", FakeModel(result="groq answer")))

    chat.invoke_with_fallback(lambda model: model, "q")
    chat.invoke_with_fallback(lambda model: model, "q")
    assert gemini.calls == 2


def test_one_unusable_response_does_not_bench_the_provider(providers):
    gemini = FakeModel(result=None)  # empty structured result: a model quirk, not an outage
    providers(("gemini", gemini), ("groq", FakeModel(result="groq answer")))

    chat.invoke_with_fallback(lambda model: model, "q")
    chat.invoke_with_fallback(lambda model: model, "q")
    assert gemini.calls == 2


def test_last_provider_is_always_tried_even_after_failing(providers):
    groq = FakeModel(error=RuntimeError("groq down"))
    providers(("gemini", FakeModel(error=TimeoutError("gemini down"))), ("groq", groq))

    for _ in range(2):
        with pytest.raises(RuntimeError, match="groq down"):
            chat.invoke_with_fallback(lambda model: model, "q")
    assert groq.calls == 2


@pytest.fixture
def provider_config(monkeypatch):
    built = []

    def builder(name):
        def build(max_retries, timeout):
            built.append((name, max_retries, timeout))
            return f"{name}-model"

        return build

    def install(order, keys):
        monkeypatch.setattr(chat, "CHAT_PROVIDERS", order)
        monkeypatch.setattr(chat, "_PROVIDERS", {name: (keys.get(name, ""), builder(name)) for name in ("gemini", "groq")})
        chat.chat_providers.cache_clear()
        return built

    yield install
    chat.chat_providers.cache_clear()


def test_only_the_last_provider_retries_and_the_others_time_out_sooner(provider_config):
    built = provider_config(("gemini", "groq"), {"gemini": "k", "groq": "k"})

    assert [name for name, _ in chat.chat_providers()] == ["gemini", "groq"]
    assert built == [
        ("gemini", 0, chat.FALLBACK_TIMEOUT_SECONDS),
        ("groq", chat.LAST_PROVIDER_MAX_RETRIES, chat.CHAT_TIMEOUT_SECONDS),
    ]
    assert chat.FALLBACK_TIMEOUT_SECONDS < chat.CHAT_TIMEOUT_SECONDS


def test_no_timeout_is_below_geminis_minimum():
    # Gemini answers "400 INVALID_ARGUMENT: Minimum allowed deadline is 10s" to anything shorter,
    # which silently sent every call to the fallback provider.
    assert min(chat.FALLBACK_TIMEOUT_SECONDS, chat.CHAT_TIMEOUT_SECONDS) >= chat.GEMINI_MIN_TIMEOUT_SECONDS == 10


def test_providers_without_a_key_are_skipped(provider_config):
    built = provider_config(("gemini", "groq"), {"gemini": "k"})

    assert [name for name, _ in chat.chat_providers()] == ["gemini"]
    assert built == [("gemini", chat.LAST_PROVIDER_MAX_RETRIES, chat.CHAT_TIMEOUT_SECONDS)]


def test_provider_order_is_configurable(provider_config):
    provider_config(("groq", "gemini"), {"gemini": "k", "groq": "k"})

    assert [name for name, _ in chat.chat_providers()] == ["groq", "gemini"]


def test_unknown_provider_name_is_rejected(provider_config):
    provider_config(("gemini", "openai"), {"gemini": "k"})

    with pytest.raises(ValueError, match="openai"):
        chat.chat_providers()
