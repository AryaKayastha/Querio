# Querio — System Architecture

## 1. High-Level Diagram

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
- One shared retrieval pipeline serves all 6 domains; each domain has its own curated document corpus (own namespace/collection, not one undifferentiated corpus).
- The domain classifier/router decides which of the 6 domains a query belongs to **before** retrieval runs — this keeps retrieval precise per domain.
- **There is no approval workflow anywhere in the system.** Every path terminates in either an answer or a logged query — never a pending/tracked request. This is a structural constraint, not just a policy — don't build a table, endpoint, or state machine that implies a request has a lifecycle beyond "logged."
- Every query is logged regardless of domain: the question, the matched domain, and whether it was resolved. This is for **department analytics only**, not an audit trail for decisions.

## 2. Components

### 2.1 Chat Interface
- Telegram bot or web chat widget. Either is fine — pick based on what's easiest to test with real classmates in Phase 3.
- Responsibilities: receive raw user message, display response (with citations), maintain conversation session/context if multi-turn is supported, forward message to the backend API.
- Does **not** do any domain logic itself — it's a thin client.

### 2.2 Domain Classifier / Router
- Input: raw student query (+ optional short conversation history for follow-ups).
- Output: one of the 6 domain labels (D1–D6), plus a confidence score.
- Approach options: a small fine-tuned/prompted classifier, or an LLM-based zero-shot classifier with the 6 domain descriptions in the prompt. Start with LLM-prompted classification in Phase 1/2 (fast to build, good enough baseline) and only invest in a trained classifier if routing accuracy on the labeled test set falls short of the 90% target.
- **Low-confidence / ambiguous queries:** define a fallback behavior early (e.g., ask a clarifying question, or present the top-2 candidate domains) — don't leave this undefined until the demo.
- Owner: Arya (Data & AI Engineer).

### 2.3 Shared Retrieval Engine
- One engine, reused across all 6 domains, parameterized by which domain's corpus to hit.
- Hybrid retrieval = semantic (embedding) search + keyword (BM25/sparse) search, combined and re-ranked.
- Per-domain tuning of the semantic/keyword weighting:
  - **Leave/Attendance (D6) and Career/NOC (D4):** policy-exact — weight keyword search higher, since exact terms ("condoning," "75% attendance," "NOC") matter more than paraphrase similarity.
  - **Clubs (D1), Certifications (D2), Sports/ECA (D3):** exploratory — weight semantic search higher, since students phrase these questions more loosely.
  - Formal Education (D5) is likely closer to policy-exact for syllabus/electives queries but exploratory for "which elective should I pick"-style questions — decide case by case during Phase 1 tuning.
- After retrieval + re-ranking, the top-k chunks are passed to the LLM with the query, to generate a grounded answer with citations.
- Owner: Arya (retrieval tuning), Jahnavi/Nancy (integration into backend).

### 2.4 Guidance-Only Boundary Logic (D4 & D6)
- This is not just a prompt instruction — treat it as a first-class architectural component, since it's the single most mentor-scrutinized part of the system.
- Concretely: for any query routed to D4 or D6, the answer-generation step must:
  1. Only draw from process/policy documents (never generate or simulate a submission/approval action).
  2. Include a fallback pointer to the real procedure/contact when the query implies the student wants an action taken (e.g., "submit my NOC request" → explain how to submit it, and where, not attempt to do it).
  3. Be explicitly testable — see `05_evaluation_and_testing.md` for the required test cases.
- See `04_scope_and_guardrails.md` for the full rule set.

### 2.5 Vector Store
- Chroma or FAISS, self-hosted.
- One namespace/collection per domain (6 total) — keeps retrieval scoped and makes per-domain re-indexing/document updates independent of the other domains.
- Stores document chunks + metadata (source document, section, domain, last-updated date) for citation generation.

### 2.6 Query Log DB (PostgreSQL)
- Logs every query regardless of domain or outcome: question text, matched domain, timestamp, resolved (Y/N), and optionally the top retrieved sources.
- **Analytics only** — never a workflow/state table. No status field beyond "resolved" for the query itself; no linkage to any external request system.
- Powers a lightweight department-facing view of "what students ask about most" (a simple aggregate query/dashboard is enough — this doesn't need its own service).

### 2.7 Admin Document Management
- Lets a non-engineer admin add/update/remove documents per domain without code changes.
- Minimum viable version: an admin panel or even a structured folder + re-index script, as long as it doesn't require an engineer to touch code for routine updates (e.g., updating the attendance policy PDF each semester).
- Owner: Jahnavi (Software Developer).

### 2.8 Backend (FastAPI)
- Exposes the API the chat interface calls; orchestrates: receive query → classify domain → retrieve → generate answer → log query → return response.
- Clean separation between: routing service, retrieval service, logging service, admin service — keeps the team's parallel work (Arya on routing/retrieval, Jahnavi on backend/logging/admin, Nancy on chat/deployment) from stepping on each other.

## 3. Data Flow (per query)

1. Student sends a message via chat interface.
2. Backend receives it, calls the domain classifier → domain label + confidence.
3. If confidence is high enough, backend calls the shared retrieval engine against that domain's vector store namespace.
4. Retrieval engine returns top-k ranked chunks with source metadata.
5. LLM generates an answer grounded in those chunks, with citations. For D4/D6, guidance-only boundary logic constrains the generation.
6. Backend logs the query (question, matched domain, resolved Y/N) to the Query Log DB.
7. Response (with citations) returned to the chat interface and shown to the student.

## 4. Technology Stack

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

**Explicitly rejected (and why):** multi-cloud/enterprise infrastructure, managed vector DBs, Teams/Kantata-style integrations, any RBAC/approval-state system — these are the inspiration platform's org-scale solutions to org-scale problems, not needed at this project's scope.

## 5. Extensibility Check (Success Criterion #5)

The architecture should make a 7th domain "clearly lower effort" than the first six. Concretely, adding a domain should only require:
1. A new document corpus + vector store namespace.
2. One new entry in the classifier's domain list (with a short description for the router prompt).
3. If it's guidance-only like D4/D6, wiring it through the same guardrail logic — not building new guardrail logic.

If adding a domain ever requires touching the retrieval engine's core logic or the chat interface, that's a signal the abstraction has leaked and is worth revisiting before the demo.
