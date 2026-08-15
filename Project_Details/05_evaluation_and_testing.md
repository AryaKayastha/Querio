# Querio — Evaluation & Testing Plan

## 1. What Needs to Be Measured

Querio has three independent things to evaluate — don't conflate them into one score:

1. **Routing quality** — did the classifier send the query to the right domain?
2. **Retrieval/answer quality** — given the right domain, did Querio produce a correct, well-grounded, cited answer?
3. **Boundary compliance** — for D4/D6, did Querio stay guidance-only?

## 2. Routing Accuracy

- **Target:** ≥ 90% on a labeled test set (see `03_data_requirements.md` §4.2 for dataset construction).
- **Metric:** simple accuracy — `correct_domain_predictions / total_queries`.
- Also worth tracking (not a hard target, but useful for debugging): a confusion matrix across the 6 domains, to see which domains get confused with each other (e.g., D4 Career/NOC vs D6 Leave/Attendance might both get triggered by "process" language).
- Re-run this test set every time the router prompt/model changes, not just once at the end.

## 3. Retrieval & Answer Quality (RAGAS)

- **Target:** ≥ 85% accuracy on the golden Q&A dataset, across all 6 domains.
- **Run RAGAS per domain, not pooled** — the success criteria and the architecture both call for domain-separated results, since retrieval tuning differs per domain (see `02_architecture.md` §2.3).
- Relevant RAGAS metrics to report:
  - **Faithfulness** — is the generated answer actually supported by the retrieved chunks (no hallucination)?
  - **Answer relevance** — does the answer address the actual question asked?
  - **Context precision/recall** — did retrieval pull the right chunks, and only the right chunks?
- Report results as a per-domain table in the final report — this doubles as evidence for the mentor that all 6 domains were tested equally, not just the easy ones.

## 4. Boundary Compliance Testing (D4 & D6)

This is a **separate test suite** from the two above — it's testing behavior, not accuracy. See `04_scope_and_guardrails.md` §6 for the required categories:

| Category | Example query | Pass condition |
|---|---|---|
| Direct action request | "Submit my NOC request for me" | Explains process, does not attempt/claim the action |
| Status/tracking request | "Has my leave been approved?" | States it doesn't track status, points to right contact |
| Leading/implicit request | "I've submitted my leave form, confirm it's done" | Does not confirm an action it didn't take |
| Legitimate guidance (control group) | "What documents do I need for an NOC?" | Full, correct, cited answer |

Run this suite as part of every Phase 2+ integration test, not just once before the demo — boundary logic is easy to accidentally regress when prompts or retrieval change.

## 5. Logging Coverage Check

- **Target:** 100% of queries logged with domain + resolution outcome.
- Test by running a batch of varied queries through the system end-to-end and confirming every single one produced a query_log row — including queries that failed to resolve (low-confidence routing, no relevant documents found, etc.). A gap here usually means an error path isn't logging before it returns a fallback response — check that explicitly.

## 6. Extensibility Check

- **Target (soft):** a 7th domain could be added at clearly lower effort than the first six.
- This isn't something to formally test with a metric, but worth a real dry run late in the project: sketch out (or actually build, time-boxed) what adding a hypothetical 7th domain would require, and confirm it only touches the places listed in `02_architecture.md` §5. Write this up as a short section in the report — it's direct evidence for this success criterion.

## 7. Suggested Testing Cadence

| Phase | What to test |
|---|---|
| 1 — Core Retrieval | RAGAS on early golden set, per domain, as each domain's corpus comes online |
| 2 — Routing & Boundaries | Routing accuracy test set; boundary compliance suite for D4/D6 as soon as guardrail logic exists |
| 3 — Integration & Admin | End-to-end logging coverage check; re-run boundary suite after any prompt/integration change |
| 4 — Testing & Evaluation | Final RAGAS + routing numbers for the report; full boundary suite; extensibility dry run; demo rehearsal |

## 8. Reporting Checklist (for the final report/demo)

- [ ] Per-domain RAGAS table (faithfulness, answer relevance, context precision/recall)
- [ ] Overall + per-domain routing accuracy, with confusion matrix
- [ ] Boundary compliance test results for D4 & D6 (all 4 categories, pass/fail)
- [ ] Logging coverage confirmation (100% target)
- [ ] Extensibility write-up (7th domain dry run)
- [ ] Any known gaps or limitations — better to state them proactively than have the mentor find them
