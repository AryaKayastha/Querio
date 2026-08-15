# Querio — Project Documentation Index

This folder is the working reference set for **Querio**, a minor project (9 credits, B.Tech Computer Engineering, 7th Semester, Department of Computer Engineering) — a conversational AI agent that answers student questions across six mentor-approved domains of college life, using retrieval-augmented generation (RAG) over real institutional documents.

**Team:** Arya Kayastha (23CE055, Data & AI Engineer) · Jahnavi Patel (23CE095, Software Developer) · Nancy Vaghela (D24CE176, Software Developer)

Use these files as standing context whenever you're stuck, planning a sprint, writing the report, or prepping for a mentor review. They're written to be self-contained — no extra explanation should be needed to make sense of them.

## Files in this set

| File | Use it when you need to... |
|---|---|
| [`01_project_planning.md`](./01_project_planning.md) | Recall the problem statement, objectives, phased timeline, role split, or success criteria — or write report sections. |
| [`02_architecture.md`](./02_architecture.md) | Design or explain a component, decide where new logic belongs, or draw the system diagram. |
| [`03_data_requirements.md`](./03_data_requirements.md) | Plan document collection, design DB schemas, or build the golden/evaluation datasets. |
| [`04_scope_and_guardrails.md`](./04_scope_and_guardrails.md) | Check whether a feature idea is in-scope, especially anything touching NOC or Leave (Domains 4 & 6). |
| [`05_evaluation_and_testing.md`](./05_evaluation_and_testing.md) | Design test cases, set up RAGAS, or check against success criteria before a demo. |

## The one rule that overrides every other doc

**Domains 4 (Career/Internship/Placement incl. NOC) and 6 (Leave Management & Attendance) are guidance-only, never transactional.** Querio explains processes and policy; it never submits, approves, rejects, routes, or tracks a request. This was an explicit mentor correction after an earlier design (a full approval workflow) was rejected. Any feature idea that reintroduces submission/approval/tracking for these two domains is out of scope — see `04_scope_and_guardrails.md` before building anything that touches them.

## Quick facts

- **6 fixed domains** (mentor-approved, do not add/remove without mentor sign-off): Clubs & Co-curricular, Certifications, Extra-Curricular & Sports, Career/Internship/Placement (incl. NOC), Formal Education, Leave Management & Attendance.
- **Scope:** the student's own university only, for this project.
- **Inspiration:** loosely inspired by an internal company platform ("Project INT") one team member has seen via an internship — only the RAG + human-guided-boundaries *pattern* was borrowed, no code/infrastructure/proprietary content.
- **Stack (all free/self-hosted, deliberately not enterprise-scale):** Google ADK or LangGraph, Gemini free tier or Groq (Llama), Chroma or FAISS, FastAPI, PostgreSQL, Telegram bot or web chat widget, RAGAS for evaluation, Docker on a free-tier VM.
