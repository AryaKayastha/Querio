"""ORM models mirroring db/schema.sql — see that file for the authoritative DDL and rationale.

Kept intentionally free of workflow-state fields (see Project_Details/04_scope_and_guardrails.md):
`resolved` describes the query's own outcome, never a request's lifecycle.
"""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

DOMAIN_VALUES = ("D1", "D2", "D3", "D4", "D5", "D6", "UNROUTED")


class Base(DeclarativeBase):
    pass


domain_code = Enum(*DOMAIN_VALUES, name="domain_code")


class QueryLog(Base):
    __tablename__ = "query_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str | None] = mapped_column(index=True)
    question: Mapped[str]
    matched_domain: Mapped[str] = mapped_column(domain_code)
    confidence: Mapped[float]
    resolved: Mapped[bool]
    guidance_only: Mapped[bool] = mapped_column(default=False)
    top_sources: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="query_log_confidence_range"),
        Index("idx_query_log_matched_domain", "matched_domain"),
        Index("idx_query_log_created_at", "created_at"),
    )


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain: Mapped[str] = mapped_column(domain_code)
    source_name: Mapped[str]
    source_type: Mapped[str]
    version: Mapped[str | None]
    last_updated: Mapped[date | None]
    owner_contact: Mapped[str | None]
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("domain <> 'UNROUTED'", name="document_domain_not_unrouted"),
        Index("idx_document_domain", "domain"),
        Index("idx_document_active", "active"),
    )
