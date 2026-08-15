# Domain Document Corpora

Raw source documents per domain, before chunking/embedding. See [`Project_Details/03_data_requirements.md`](../Project_Details/03_data_requirements.md) for what to collect and how to describe each document.

## Format

Drop each source document as a `.md` or `.txt` file inside its domain folder. At the top of each file, include a small metadata header so the ingestion pipeline (`chatbot/src/querio_chatbot/ingestion/ingest.py`) can populate citations correctly:

```
---
source_name: Attendance Policy 2025-26
source_type: policy_document
last_updated: 2026-01-15
owner_contact: Office of Academic Affairs
---

# Actual document content starts here, in sections with headings.
## Section heading
...
```

The `source_name` + the nearest heading above a chunk become that chunk's citation.

## Folders

| Folder | Domain | Status |
|---|---|---|
| `D1_clubs/` | Co-curricular Activities & Clubs | needs data |
| `D2_certifications/` | Certifications | needs data |
| `D3_eca_sports/` | Extra-Curricular Activities & Sports | needs data |
| `D4_career_noc/` | Career/Internship/Placement (incl. NOC) | needs data |
| `D5_formal_education/` | Formal Education | **has data — current target** |
| `D6_leave_attendance/` | Leave Management & Attendance | **has data — current target** |
