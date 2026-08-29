"""quarantine_incident_2026_08_29

Revision ID: 8b9f0a1c2d3e
Revises: 7a8e9f0b1c2d
Create Date: 2026-08-29 17:15:00.000000+00:00

ADR-0013: Quarantine fabricated data into incident_2026_08_29 schema.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b9f0a1c2d3e"
down_revision: str | None = "7a8e9f0b1c2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables to quarantine in dependency order (parent first, child last)
FORWARD_TABLES = [
    "topics",
    "runs",
    "quota_ledger",
    "model_calls",
    "idempotency_keys",
    "steps",
    "gates",
    "approvals",
    "sources",
    "snapshots",
    "evidence",
    "claims",
    "knowledge_object_versions",
    "knowledge_object_current",
    "knowledge_object_claims",
    "claim_evidence",
]

# Deletion order (child first, parent last)
DELETE_TABLES = list(reversed(FORWARD_TABLES))


def upgrade() -> None:
    # 1. Create quarantine schema
    op.execute("CREATE SCHEMA IF NOT EXISTS incident_2026_08_29;")

    # 2. Create tables in quarantine schema
    for table in FORWARD_TABLES:
        op.execute(
            f"CREATE TABLE IF NOT EXISTS incident_2026_08_29.{table} "
            f"(LIKE public.{table} INCLUDING DEFAULTS INCLUDING INDEXES);"
        )

    # 3. Copy rows from public to quarantine schema
    for table in FORWARD_TABLES:
        op.execute(f"INSERT INTO incident_2026_08_29.{table} SELECT * FROM public.{table};")

    # 4. Disable append-only triggers, delete rows from public, then re-enable triggers
    for table in DELETE_TABLES:
        op.execute(f"ALTER TABLE public.{table} DISABLE TRIGGER ALL;")
        op.execute(f"DELETE FROM public.{table};")
        op.execute(f"ALTER TABLE public.{table} ENABLE TRIGGER ALL;")


def downgrade() -> None:
    """Downgrade quarantine migration.

    ⚠️ CAUTION / RULE R11 WARNING:
    Running `alembic downgrade` re-inserts quarantined incident rows from `incident_2026_08_29`
    back into the `public` schema and drops the quarantine schema.
    This downgrade path exists for migration reversibility (ADR-0013), but in production,
    quarantined fabricated data must NEVER be treated as valid knowledge or production history.
    """
    # 1. Restore rows from quarantine schema back into public in forward FK order
    for table in FORWARD_TABLES:
        op.execute(
            f"INSERT INTO public.{table} "
            f"SELECT * FROM incident_2026_08_29.{table} "
            f"ON CONFLICT DO NOTHING;"
        )

    # 2. Drop the quarantine schema and its tables
    op.execute("DROP SCHEMA IF EXISTS incident_2026_08_29 CASCADE;")
