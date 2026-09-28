"""initial schema

Revision ID: 4abab20ebafa
Revises:
Create Date: 2026-09-18 00:35:53.260130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB


# revision identifiers, used by Alembic.
revision: str = '4abab20ebafa'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DOMAIN_VALUES = ("D1", "D2", "D3", "D4", "D5", "D6", "UNROUTED")


def upgrade() -> None:
    ENUM(*DOMAIN_VALUES, name="domain_code").create(op.get_bind(), checkfirst=True)
    domain_code = ENUM(*DOMAIN_VALUES, name="domain_code", create_type=False)

    op.create_table(
        "query_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("matched_domain", domain_code, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("guidance_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("top_sources", JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="query_log_confidence_range"),
    )
    op.create_index("idx_query_log_matched_domain", "query_log", ["matched_domain"])
    op.create_index("idx_query_log_created_at", "query_log", ["created_at"])
    op.create_index(
        "idx_query_log_session_id",
        "query_log",
        ["session_id"],
        postgresql_where=sa.text("session_id IS NOT NULL"),
    )

    op.create_table(
        "document",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("domain", domain_code, nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("last_updated", sa.Date(), nullable=True),
        sa.Column("owner_contact", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("domain <> 'UNROUTED'", name="document_domain_not_unrouted"),
    )
    op.create_index("idx_document_domain", "document", ["domain"])
    op.create_index("idx_document_active", "document", ["active"])

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER document_set_updated_at
            BEFORE UPDATE ON document
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS document_set_updated_at ON document")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
    op.drop_index("idx_document_active", table_name="document")
    op.drop_index("idx_document_domain", table_name="document")
    op.drop_table("document")
    op.drop_index("idx_query_log_session_id", table_name="query_log")
    op.drop_index("idx_query_log_created_at", table_name="query_log")
    op.drop_index("idx_query_log_matched_domain", table_name="query_log")
    op.drop_table("query_log")
    ENUM(name="domain_code").drop(op.get_bind(), checkfirst=True)
