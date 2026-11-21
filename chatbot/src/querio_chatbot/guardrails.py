"""Output check for the guidance-only boundary (Project_Details/04_scope_and_guardrails.md §5).

An answer must never claim that the student's request was submitted, approved or otherwise acted on
("Your leave has been approved."). The check runs on every generated answer, so the boundary holds
even when a question tells the model what to write (QRO-01). It is phrased narrowly enough that
process explanations ("Medical leave is approved by the HOD", "Once your leave is approved, ...")
and denials ("I can't confirm whether your leave has been approved") pass.
"""

import re
from typing import Optional

_OUTCOME = (
    r"(?:approved|submitted|granted|accepted|processed|forwarded|registered|sanctioned|confirmed|cleared"
    r"|enrolled|marked\s+present)"
)
# Not a claim when the outcome is followed by who does it or a condition ("approved by the HOD",
# "accepted only if ...").
_NOT_A_CLAIM_AFTER = r"(?!\s+(?:only\s+)?(?:by|if|when|once|after|upon|before|unless)\b)"
_CLAIM = re.compile(
    rf"""
    \byour\s+(?:[\w'-]+\s+){{0,4}}(?:has|have|is|was|were)\s+(?:now\s+|already\s+|successfully\s+)?
      (?:been\s+)?(?:successfully\s+)?{_OUTCOME}\b{_NOT_A_CLAIM_AFTER}
    | \b(?:the|this)\s+(?:[\w'-]+\s+){{0,2}}(?:request|application|leave|noc|registration|form|submission)
      \s+(?:has|have|is|was)\s+(?:now\s+|already\s+|successfully\s+)?(?:been\s+)?{_OUTCOME}\b{_NOT_A_CLAIM_AFTER}
    | \bi(?:'ve|\s+have|\s+had)?\s+(?:now\s+|just\s+|already\s+|successfully\s+)?
      (?:submitted|approved|forwarded|registered|processed|sent|filed|applied|booked|cancelled|marked)\b
    | \b(?:you\s+are|you're|you\s+have\s+been|you've\s+been)\s+(?:now\s+|successfully\s+)?
      (?:registered|enrolled|marked\s+present|approved)\b
    | \bsuccessfully\s+(?:submitted|registered|approved|forwarded|processed)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Earlier in the same sentence, these mean the outcome is denied, hedged or conditional, not claimed.
_HEDGE = re.compile(
    r"\b(?:not|no|never|cannot|can't|couldn't|won't|unable|whether|if|once|when|after|until|unless|before)\b"
    r"|n't\b|\b(?:find\s+out|check|confirm|see|tell\s+you)\b",
    re.IGNORECASE,
)
_SENTENCE_END = re.compile(r"[.!?\n]")


def find_confirmation_claim(answer: str) -> Optional[str]:
    """The first sentence that claims an action was taken on the student's request, else None."""
    text = answer.replace("’", "'").replace("‘", "'")
    for match in _CLAIM.finditer(text):
        sentence_start = max((m.end() for m in _SENTENCE_END.finditer(text, 0, match.start())), default=0)
        if not _HEDGE.search(text, sentence_start, match.start()):
            sentence_end = _SENTENCE_END.search(text, match.end())
            return text[sentence_start : sentence_end.end() if sentence_end else len(text)].strip()
    return None


def drop_claim_sentences(answer: str) -> str:
    """The answer without any sentence that claims an action was taken."""
    while (claim := find_confirmation_claim(answer)) is not None:
        answer = answer.replace("’", "'").replace("‘", "'").replace(claim, "", 1)
    answer = re.sub(r"(?<=\S)[ \t]{2,}", " ", answer)  # gap left mid-line; leading indents stay
    return re.sub(r"\n{3,}", "\n\n", answer).strip()
