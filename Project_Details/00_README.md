# Querio project documentation index

This folder contains the working reference set for Querio, a minor project for the Department of Computer Engineering. Querio is a conversational AI assistant that answers student questions across six mentor-approved domains of college life using retrieval-augmented generation over real institutional documents.

Team:

- Arya Kayastha (23CE055, Data and AI Engineer)
- Jahnavi Patel (23CE095, Software Developer)
- Nancy Vaghela (D24CE176, Software Developer)

Use these files as standing context when planning work, writing report sections, preparing a mentor review, or checking project scope.

## Repository structure

```text
Querio/
├── backend/
├── frontend/
├── data/
├── Project_Details/
└── README.md
```

## Documentation files

| File | Purpose |
|---|---|
| [`01_project_planning.md`](./01_project_planning.md) | Problem statement, objectives, timeline, team roles, and success criteria |
| [`02_architecture.md`](./02_architecture.md) | System design, component boundaries, and integration flow |
| [`03_data_requirements.md`](./03_data_requirements.md) | Source collection plan, document metadata, and database/schema guidance |
| [`04_scope_and_guardrails.md`](./04_scope_and_guardrails.md) | Scope limits, especially guidance-only behavior for Domains 4 and 6 |
| [`05_evaluation_and_testing.md`](./05_evaluation_and_testing.md) | Test strategy, evaluation datasets, and demo readiness criteria |

## Key project rule

Domains 4 (Career, Internship, Placement, and NOC) and 6 (Leave Management and Attendance) are guidance-only. Querio explains process and policy, but it never submits, approves, rejects, routes, or tracks requests. Any feature that reintroduces those actions for these domains is out of scope.

## Current implementation focus

- Backend service: `backend/src/querio_backend/`
- Frontend app: `frontend/src/`
- Source documents: `data/`
- Active domains: D5 (Formal Education) and D6 (Leave Management and Attendance)

## Notes

- The repository is intentionally split so the frontend and backend can evolve independently.
- Keep this index aligned with the actual folder layout whenever the codebase changes.
