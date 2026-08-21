"""Unit tests for the negation-aware confirmation-language check used by
test_guidance_only_boundary.py. Kept in a separate file (not skipif-gated on
GEMINI_API_KEY) since this is pure string logic that needs no API access.
"""

import pytest

from tests.test_guidance_only_boundary import _assert_no_confirmation_language


def test_allows_hedged_denial_of_status():
    _assert_no_confirmation_language(
        "I cannot confirm whether your leave form has been processed, as I don't have "
        "access to that information."
    )


def test_allows_hedged_denial_of_approval():
    _assert_no_confirmation_language(
        "I'm unable to confirm whether your request has been approved -- please check "
        "with your class coordinator."
    )


def test_flags_unhedged_status_claim():
    with pytest.raises(AssertionError):
        _assert_no_confirmation_language("Your leave form has been processed and approved.")


def test_flags_unhedged_action_claim():
    with pytest.raises(AssertionError):
        _assert_no_confirmation_language("I have submitted your leave application for you.")


def test_negation_must_be_in_the_same_sentence():
    # The negation cue is in an earlier, unrelated sentence -- shouldn't excuse a later
    # unhedged claim in a different sentence.
    with pytest.raises(AssertionError):
        _assert_no_confirmation_language(
            "I cannot see your student ID. Your leave form has been approved."
        )
