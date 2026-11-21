"""The QRO-13 latency benchmark's pass/fail logic, with the HTTP calls faked."""

import itertools

import pytest

from querio_chatbot.eval import latency


def _fake_requests(monkeypatch, durations, status=200):
    sequence = itertools.cycle(durations)
    monkeypatch.setattr(latency, "_ask", lambda url, query, timeout: (next(sequence), status))


def test_passes_when_p90_and_max_are_under_target(monkeypatch, capsys):
    _fake_requests(monkeypatch, [2.0, 3.0, 4.0])
    assert latency.main([]) == 0
    assert "PASS" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("durations", "status"),
    [
        ([2.0] * 8 + [12.0, 12.0], 200),  # p90 over 8 s
        ([2.0] * 30 + [30.0], 200),  # one request over 25 s
        ([2.0], 500),  # failures
    ],
)
def test_fails_when_any_target_is_missed(monkeypatch, capsys, durations, status):
    _fake_requests(monkeypatch, durations, status)
    assert latency.main([]) == 1
    assert "FAIL" in capsys.readouterr().out
