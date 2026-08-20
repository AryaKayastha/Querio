# Querio — Project Planning

## 1. One-line pitch

One conversational guide across every part of student life on campus — a RAG-based AI agent that answers student questions across six mentor-approved domains, with cited answers pulled from real institutional documents.

## 2. Problem Statement

Students repeatedly ask the same questions across six recurring areas of college life (clubs, certifications, sports/ECA, career & NOC, academics, leave/attendance), with no single reliable source of truth. Faculty and department staff end up answering the same informal queries again and again, with no visibility into which topics cause the most confusion.

**Querio solves this** with one conversational agent that:
- Gives accurate, cited answers grounded in real documents — not the LLM's general knowledge.
- Routes every query to the correct domain before retrieving an answer.
- Gives the department visibility into what students actually ask, via lightweight logging — without building or maintaining any approval/workflow system.

## 3. Objectives

| Objective | Measured by |
|---|---|
| Give students one trusted place for accurate, cited answers across all 6 domains | Golden Q&A test-set accuracy ≥ 85% |
| Route every query to the right knowledge domain before retrieval | Domain routing accuracy ≥ 90% on a labeled test set |
| Prove retrieval quality quantitatively | RAGAS metrics, run separately per domain |
| Give the department useful visibility into student needs | 100% of queries logged (question + domain + resolution outcome) |

## 4. Scope

**In scope:** the student's own university, six mentor-approved domains, guidance-only handling for NOC and Leave, document-grounded Q&A, domain routing, query logging/analytics, admin document management, an evaluation harness.

**Out of scope (explicitly rejected):**
- Any approval/routing/tracking workflow for requests (NOC, Leave, or otherwise).
- Multi-cloud/enterprise infrastructure, managed vector DBs, Teams/Kantata-style integrations, RBAC/approval-state systems — these are the inspiration platform's org-scale solutions to org-scale problems and don't fit this project's scope.
- Domains beyond the fixed six, without mentor sign-off.

See `04_scope_and_guardrails.md` for the full detail on why this boundary exists and how to keep to it.

## 5. Team & Role Split

| Member | ID | Role | Primary responsibilities |
|---|---|---|---|
| Arya Kayastha | 23CE055 | Data & AI Engineer | Domain classifier/router, per-domain retrieval tuning, RAGAS + routing evaluation harness, document curation strategy across all 6 domains (`chatbot/`) |
| Jahnavi Patel | 23CE095 | Software Developer | Chat UI / web widget, frontend delivery (`frontend/`) |
| Nancy Vaghela | D24CE176 | Software Developer | Backend API bridge, query logging pipeline, admin document-management panel, database schema (`backend/`) |

## 6. Phased Timeline (Semester-Paced)

| Phase | Duration | Deliverables |
|---|---|---|
| **0 — Foundation** | 2–3 weeks | Requirements, architecture doc, document collection for all 6 domains, stack setup |
| **1 — Core Retrieval** | 4–5 weeks | RAG pipeline, hybrid retrieval + re-ranking, working across all 6 domains |
| **2 — Routing & Boundaries** | 3–4 weeks | Domain classifier, guidance-only boundary logic for D4 & D6, query logging pipeline |
| **3 — Integration & Admin** | 2–3 weeks | Unified chat interface, admin document panel, deployment |
| **4 — Testing & Evaluation** | 2 weeks | RAGAS + routing accuracy results, test cases, report, demo prep |

**Total:** ~13–17 weeks, matching a semester's pace. Use this as your sprint boundary — don't start Phase 2's routing logic before Phase 1's retrieval is working across all six domains; the classifier is only useful once there's something correct to route into.

## 7. Success Criteria (Definition of Done)

- [ ] Domain routing accuracy ≥ 90% on a labeled test set.
- [ ] Golden Q&A test-set answer accuracy ≥ 85%, across all 6 domains.
- [ ] 100% of queries logged with domain + resolution outcome.
- [ ] Domains 4 & 6 verified via explicit test cases to **never** submit/approve/track a request.
- [ ] A 7th domain could be added at clearly lower effort than the first six — proving the architecture generalizes, not just a one-off build.

## 8. Decision Log

Keep this updated as decisions are made — it exists so nobody re-litigates settled scope in week 10.

| Decision | Status |
|---|---|
| Two-pillar design (Knowledge + Workflow Agent) | **Superseded** — replaced with single multi-domain pillar |
| NOC/Leave approval workflow | **Removed** — guidance-only per mentor instruction |
| Request status tracking DB | **Removed** — replaced with lightweight query logging (analytics only, not workflow state) |
| Project name | **Querio** (finalized) |
| Number of knowledge domains | **6**, fixed by mentor's handwritten note — do not add/remove domains without mentor sign-off |

## 9. Relationship to "Project INT"

Querio is **inspired by, but independent of**, an internal AI platform ("Project INT") being built at a company where one team member interns. Only the underlying *pattern* — RAG-based knowledge assistant with human-guided boundaries — was borrowed. No code, infrastructure, or proprietary content was reused. Keep this framing consistent in the report and any mentor conversation: Querio is a from-scratch academic build at university scale, not a port of a company product.

## 10. Glossary

| Term | Meaning |
|---|---|
| RAG | Retrieval-Augmented Generation |
| RAGAS | Evaluation framework for RAG systems (faithfulness, relevance, precision/recall) |
| Domain Router | Classifier assigning an incoming query to 1 of 6 knowledge domains |
| Guidance-only | System explains process/policy but never performs the transactional action itself |
| Golden Dataset | Hand-curated question-answer pairs used to measure quality objectively |
| HITL | Human-in-the-loop — not used in the current design, since there is no approval workflow left; retained here only because early drafts referenced it |
