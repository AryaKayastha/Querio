# Querio — Complete Project Context
*Use this as background context in any AI conversation about this project — it's self-contained, no extra explanation needed.*

---

## 1. What This Project Is

**Querio** is a minor project (9 credits, B.Tech Computer Engineering, 7th Semester) — a conversational AI agent that answers student questions across **six mentor-approved domains of college life**, pulling accurate, cited answers from real institutional documents instead of students having to search or ask around.

It is **inspired by, but independent of**, an internal AI platform ("Project INT") being built at a company where one team member interns. Only the underlying *pattern* (RAG-based knowledge assistant, human-guided boundaries) was borrowed — no code, infrastructure, or proprietary content was reused.

**Team:**
- **Arya Kayastha** (23CE055) — Data & AI Engineer
- **Jahnavi Patel** (23CE095) — Software Developer
- **Nancy Vaghela** (D24CE176) — Software Developer

---

## 2. The Six Knowledge Domains (mentor-defined, approved)

| # | Domain | Covers | Type |
|---|---|---|---|
| 1 | Co-curricular Activities & Clubs | Club list, joining process, event participation rules | Pure Q&A |
| 2 | Certifications | Available certifications, eligibility, enrollment/credit process | Pure Q&A |
| 3 | Extra-Curricular Activities & Sports | NCC/NSS enrollment, sports trials, cultural events | Pure Q&A |
| 4 | Career / Internship / Placement (incl. NOC) | Placement process, eligibility, **NOC guidance** (how to apply, required documents, timelines) | **Guidance-only** |
| 5 | Formal Education | Subject/syllabus queries, electives, teaching-learning process | Pure Q&A |
| 6 | Leave Management & Attendance | Leave policy, attendance shortage/condoning rules, how the process works | **Guidance-only** |

---

## 3. Critical Scope Boundary (do not violate this in any design/feature discussion)

Domains 4 and 6 are **guidance-only, never transactional**. This was an explicit mentor correction — the project originally planned a full approval workflow (submit → route → approve → track) for NOC and Leave requests; that was **removed entirely**.

**Querio DOES, for Domains 4 & 6:**
- Explain the process step by step
- Clarify eligibility and policy (e.g., attendance shortage rules)
- List required documents and typical timelines
- Direct the student to the right contact/procedure for the actual request

**Querio NEVER does, for Domains 4 & 6 (or anywhere else):**
- Submit a leave or NOC request on the student's behalf
- Approve, reject, or route a request to anyone
- Track or store request/approval status
- Claim an action has been taken when it hasn't

Any future feature idea that reintroduces submission/approval/tracking for these two domains is **out of scope** and contradicts approved project direction.

---

## 4. Problem Statement

Students repeatedly ask the same questions across all six areas of college life, with no single reliable source of truth. Faculty/department staff answer the same informal queries repeatedly, with no visibility into which topics cause the most confusion. Querio solves this with one conversational agent, without building or maintaining any approval/workflow system.

---

## 5. Architecture

```
                    Chat Interface (Telegram / Web Chat)
                                   │
                    Domain Classifier / Router (1 of 6)
                                   │
        ┌──────┬──────┬──────┬──────┬──────┬──────┐
        D1    D2     D3     D4     D5     D6
      (Clubs)(Certs)(Sports)(Career/(Formal(Leave/
                              NOC)   Edu)  Attend.)
        └──────┴──────┴──────┴──────┴──────┘
                          │
              Shared Retrieval Engine
           (hybrid search + re-ranking + LLM)
                          │
              ┌───────────┴────────────┐
        Vector Store              Query Log DB
     (per-domain corpora,       (question, matched
      Chroma/FAISS)             domain, resolved Y/N)
```

**Key design points:**
- One shared retrieval pipeline serves all 6 domains; each domain has its own curated document corpus.
- The domain classifier/router decides which of the 6 domains a query belongs to *before* retrieval runs — this keeps retrieval precise per domain instead of searching one undifferentiated corpus.
- There is **no approval workflow anywhere in the system**. Every path terminates in either an answer or a logged query — never a pending/tracked request.
- Every query (regardless of domain) is logged: the question, the matched domain, and whether it was successfully resolved. This is for **department analytics only** (what students are asking about most) — not a workflow/audit trail for decisions.

---

## 6. Core Features

1. **Multi-Domain Document-Grounded Q&A** — answers sourced from real curated documents per domain, not the LLM's general knowledge.
2. **Domain Classifier / Router** — routes each query to the correct one of 6 domains before retrieval.
3. **Source Citation** — every answer references the document/section it came from.
4. **Hybrid Retrieval + Re-ranking** — combines semantic + keyword search, tuned per domain (e.g., Leave/Attendance is policy-exact and benefits from keyword weighting; Clubs/Certifications are more exploratory and benefit from semantic search).
5. **Guidance-Only Boundaries for NOC & Leave** — explicit system-level rule (see Section 3) with fallback messaging directing students to the real procedure.
6. **Query Logging & Department Analytics** — logs question + domain + resolution outcome for department visibility.
7. **Evaluation Harness** — RAGAS metrics run per domain, plus a separate routing-accuracy test set.
8. **Admin Document Management** — admin can add/update/remove documents per domain without engineering involvement.

---

## 7. Technology Stack

| Layer | Choice | Why |
|---|---|---|
| Agent Framework | Google ADK or LangGraph | Free; clean support for routing logic |
| LLM | Gemini (free tier) or Groq (Llama) | No cost for a student project |
| Vector Store | Chroma or FAISS (self-hosted, one namespace per domain) | Free; deeper learning than a managed API |
| Backend | FastAPI | Clean service separation across the team |
| Database | PostgreSQL | Query logs, domain document metadata |
| Delivery | Telegram bot or web chat widget | Real and testable with classmates |
| Evaluation | RAGAS + golden dataset (all 6 domains) + routing-accuracy test set | Quantifies both retrieval and routing quality |
| Deployment | Docker container on a free-tier cloud VM | Real deployment, not "runs on a laptop" |

**Explicitly rejected (and why):** multi-cloud/enterprise infrastructure, managed vector DBs, Teams/Kantata-style integrations, any RBAC/approval-state system — all were the company's org-scale solutions to org-scale problems, not needed at this project's scope.

---

## 8. Team Role Split

- **Arya Kayastha (Data & AI Engineer):** domain classifier/router, per-domain retrieval tuning, RAGAS + routing evaluation harness, document curation strategy across all 6 domains.
- **Jahnavi Patel (Software Developer):** backend/API, query logging pipeline, admin document-management panel, database schema.
- **Nancy Vaghela (Software Developer):** chat/bot interface, deployment, integration between the router and retrieval engine.

---

## 9. Phased Timeline (Semester-Paced)

| Phase | Duration | Deliverables |
|---|---|---|
| 0 — Foundation | 2–3 weeks | Requirements, architecture doc, document collection for all 6 domains, stack setup |
| 1 — Core Retrieval | 4–5 weeks | RAG pipeline, hybrid retrieval + re-ranking, working across all 6 domains |
| 2 — Routing & Boundaries | 3–4 weeks | Domain classifier, guidance-only boundary logic for D4 & D6, query logging pipeline |
| 3 — Integration & Admin | 2–3 weeks | Unified chat interface, admin document panel, deployment |
| 4 — Testing & Evaluation | 2 weeks | RAGAS + routing accuracy results, test cases, report, demo prep |

---

## 10. Success Criteria

- Domain routing accuracy ≥ 90% on a labeled test set.
- Golden Q&A test-set answer accuracy ≥ 85%, across all 6 domains.
- 100% of queries logged with domain + resolution outcome.
- Domains 4 & 6 verified via explicit test cases to **never** submit/approve/track a request.
- A 7th domain could be added at clearly lower effort than the first six — proving the architecture generalizes, not just a one-off build.

---

## 11. Decision Log (so nobody re-litigates settled scope)

| Decision | Status |
|---|---|
| Two-pillar design (Knowledge + Workflow Agent) | **Superseded** — replaced with single multi-domain pillar |
| NOC/Leave approval workflow | **Removed** — guidance-only per mentor instruction |
| Request status tracking DB | **Removed** — replaced with lightweight query logging (analytics only, not workflow state) |
| Project name | **Querio** (finalized) |
| Number of knowledge domains | **6**, fixed by mentor's handwritten note — do not add/remove domains without mentor sign-off |

---

## 12. Glossary

| Term | Meaning |
|---|---|
| RAG | Retrieval-Augmented Generation |
| RAGAS | Evaluation framework for RAG systems (faithfulness, relevance, precision/recall) |
| Domain Router | Classifier assigning an incoming query to 1 of 6 knowledge domains |
| Guidance-only | System explains process/policy but never performs the transactional action itself |
| Golden Dataset | Hand-curated question-answer pairs used to measure quality objectively |
| HITL | Human-in-the-loop — not used in the current design, since there is no approval workflow left; retained here only because early drafts referenced it |
