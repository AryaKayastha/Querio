-- Querio backend — PostgreSQL schema
-- Covers the two tables scoped to this lane (see Project_Details/03_data_requirements.md §5):
--   1. query_log  — analytics-only record of every chat query and its outcome
--   2. document   — metadata driving the admin document-management panel
--
-- Guardrail (Project_Details/04_scope_and_guardrails.md): query_log must never carry
-- workflow-state fields (e.g. status: pending/approved/rejected). `resolved` is the only
-- outcome field, and it describes the query's own resolution, not a request's lifecycle.

CREATE TYPE domain_code AS ENUM ('D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'UNROUTED');

-- 1. query_log
-- One row per POST /chat call. Powers "what do students ask about most" analytics only.
CREATE TABLE query_log (
    id             BIGSERIAL PRIMARY KEY,
    session_id     TEXT,                    -- correlates turns from the same chat session; nullable, never a join key into a workflow table
    question       TEXT NOT NULL,
    matched_domain domain_code NOT NULL,
    confidence     REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    resolved       BOOLEAN NOT NULL,         -- true iff confidence cleared the router's threshold and a grounded answer was returned
    guidance_only  BOOLEAN NOT NULL DEFAULT FALSE,  -- mirrors the chatbot response flag, for D4/D6 usage analytics
    top_sources    JSONB NOT NULL DEFAULT '[]',     -- snapshot of the sources array returned to the client: [{source_name, source_section, source_url}]
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_query_log_matched_domain ON query_log (matched_domain);
CREATE INDEX idx_query_log_created_at ON query_log (created_at);
CREATE INDEX idx_query_log_session_id ON query_log (session_id) WHERE session_id IS NOT NULL;

-- 2. document
-- Metadata the admin panel reads/writes to manage per-domain source documents without
-- an engineer touching code or the vector store directly.
CREATE TABLE document (
    id            SERIAL PRIMARY KEY,
    domain        domain_code NOT NULL CHECK (domain <> 'UNROUTED'),  -- UNROUTED is a routing outcome, not a real domain with owned documents
    source_name   TEXT NOT NULL,
    source_type   TEXT NOT NULL,
    version       TEXT,
    last_updated  DATE,
    owner_contact TEXT,
    active        BOOLEAN NOT NULL DEFAULT TRUE,  -- lets admin retire a doc without deleting history
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_document_domain ON document (domain);
CREATE INDEX idx_document_active ON document (active);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER document_set_updated_at
    BEFORE UPDATE ON document
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
