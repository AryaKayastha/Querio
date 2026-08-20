# Domain document corpora

This folder stores the raw source documents that are later chunked and embedded by the backend ingestion pipeline.

See [`Project_Details/03_data_requirements.md`](../Project_Details/03_data_requirements.md) for collection guidance and metadata expectations.

## Folder structure

```text
data/
├── README.md
├── D1_clubs/
├── D2_certifications/
├── D3_eca_sports/
├── D4_career_noc/
├── D5_formal_education/
└── D6_leave_attendance/
```

## File format

Store each source document as `.md` or `.txt` inside the appropriate domain folder.

Each file should begin with a small metadata block so the ingestion pipeline can create citations correctly:

```text
---
source_name: Attendance Policy 2025-26
source_type: policy_document
last_updated: 2026-01-15
owner_contact: Office of Academic Affairs
---

# Actual document content starts here.
## Section heading
...
```

The backend ingestion code at `backend/src/querio_backend/ingestion/ingest.py` uses this metadata when building document chunks.

## Domain folders

| Folder | Domain | Status |
|---|---|---|
| `D1_clubs/` | Co-curricular activities and clubs | needs data |
| `D2_certifications/` | Certifications | needs data |
| `D3_eca_sports/` | Extra-curricular activities and sports | needs data |
| `D4_career_noc/` | Career, internship, placement, and NOC | needs data |
| `D5_formal_education/` | Formal education | current target |
| `D6_leave_attendance/` | Leave management and attendance | current target |

## Notes

- Keep document titles and section headings clear and stable.
- Prefer one topic per file when possible.
- Do not commit generated vector store files; they are rebuilt from this source corpus.
