"""append-only claim versions and persisted production artifacts

Revision ID: b1c4d7e90a25
Revises: dab939524748
Create Date: 2026-08-31 13:10:00.000000+00:00

ADR-0015: `claims` becomes an immutable identity row and every mutable field
moves to the append-only `claim_versions` table (Invariant 4).

ADR-0016: Scripts, timing plans, storyboards and render artifacts are persisted
so that stages 10-18 read the artifact the operator approved instead of
regenerating a new one (Invariant 7).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "b1c4d7e90a25"
down_revision: str | None = "dab939524748"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = JSONB().with_variant(sa.JSON(), "sqlite")

CLAIM_STATE_COLUMNS = (
    "text",
    "assertion_type",
    "confidence",
    "status",
    "inferred_from_claim_ids",
)


def upgrade() -> None:
    op.create_table(
        "claim_versions",
        sa.Column(
            "claim_id",
            sa.String(64),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("assertion_type", sa.String(32), nullable=False, index=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="unsupported"),
        sa.Column("inferred_from_claim_ids", json_type, nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "assertion_type IN ('fact', 'inference', 'opinion', 'contested')",
            name="claim_versions_assertion_type_check",
        ),
        sa.CheckConstraint(
            "status IN ('verified', 'unverified', 'unsupported', 'refuted', 'contested')",
            name="claim_versions_status_check",
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0", name="claim_versions_confidence_check"
        ),
        sa.CheckConstraint("version >= 1", name="claim_versions_version_check"),
    )
    op.create_index("ix_claim_versions_claim_version", "claim_versions", ["claim_id", "version"])
    op.create_index("ix_claim_versions_status", "claim_versions", ["status"])

    # Existing rows become version 1; nothing is destroyed (rule R11).
    op.execute(
        """
        INSERT INTO claim_versions (
            claim_id, version, text, assertion_type, confidence, status,
            inferred_from_claim_ids, actor_id, reason, created_at
        )
        SELECT id, 1, text, assertion_type, confidence, status,
               inferred_from_claim_ids, 'migration.b1c4d7e90a25',
               'Backfilled from the pre-versioning claims row', created_at
        FROM claims
        """
    )

    op.drop_constraint("claims_assertion_type_check", "claims", type_="check")
    op.drop_constraint("claims_status_check", "claims", type_="check")
    op.drop_constraint("claims_confidence_check", "claims", type_="check")
    for column in CLAIM_STATE_COLUMNS:
        op.drop_column("claims", column)

    op.create_table(
        "scripts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("topic_id", sa.String(64), nullable=False, index=True),
        sa.Column("knowledge_object_id", sa.String(64), nullable=False),
        sa.Column("ko_version", sa.Integer(), nullable=False),
        sa.Column("story_angle", sa.Text(), nullable=False),
        sa.Column("target_duration_seconds", sa.Float(), nullable=False, server_default="60.0"),
        sa.Column("beats", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ko_version >= 1", name="scripts_ko_version_check"),
        sa.CheckConstraint("target_duration_seconds > 0", name="scripts_target_duration_check"),
    )

    op.create_table(
        "timing_plans",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "script_id",
            sa.String(64),
            sa.ForeignKey("scripts.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("total_duration_seconds", sa.Float(), nullable=False),
        sa.Column("beat_timings", json_type, nullable=False),
        sa.Column("caption_cues", json_type, nullable=False),
        sa.Column("meta", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("total_duration_seconds > 0", name="timing_plans_total_duration_check"),
    )

    op.create_table(
        "storyboards",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "script_id",
            sa.String(64),
            sa.ForeignKey("scripts.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "timing_plan_id",
            sa.String(64),
            sa.ForeignKey("timing_plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("scenes", json_type, nullable=False),
        sa.Column("render_targets", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "render_artifacts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(64),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "storyboard_id",
            sa.String(64),
            sa.ForeignKey("storyboards.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("render_target", sa.String(32), nullable=False),
        sa.Column("video_storage_key", sa.String(512), nullable=False),
        sa.Column("captions_storage_key", sa.String(512), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("meta", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "render_target IN ('vertical', 'horizontal')", name="render_artifacts_target_check"
        ),
        sa.CheckConstraint("duration_seconds > 0", name="render_artifacts_duration_check"),
        sa.CheckConstraint("file_size_bytes >= 0", name="render_artifacts_size_check"),
        sa.UniqueConstraint(
            "run_id", "storyboard_id", "render_target", name="uq_render_artifact_target"
        ),
    )


def downgrade() -> None:
    op.drop_table("render_artifacts")
    op.drop_table("storyboards")
    op.drop_table("timing_plans")
    op.drop_table("scripts")

    op.add_column("claims", sa.Column("text", sa.Text(), nullable=True))
    op.add_column("claims", sa.Column("assertion_type", sa.String(32), nullable=True))
    op.add_column(
        "claims", sa.Column("confidence", sa.Float(), nullable=True, server_default="1.0")
    )
    op.add_column(
        "claims",
        sa.Column("status", sa.String(32), nullable=True, server_default="unsupported"),
    )
    op.add_column("claims", sa.Column("inferred_from_claim_ids", json_type, nullable=True))

    # Collapse the append-only history back onto the latest version per claim.
    op.execute(
        """
        UPDATE claims c
        SET text = v.text,
            assertion_type = v.assertion_type,
            confidence = v.confidence,
            status = v.status,
            inferred_from_claim_ids = v.inferred_from_claim_ids
        FROM (
            SELECT DISTINCT ON (claim_id)
                   claim_id, text, assertion_type, confidence, status, inferred_from_claim_ids
            FROM claim_versions
            ORDER BY claim_id, version DESC
        ) v
        WHERE c.id = v.claim_id
        """
    )

    op.alter_column("claims", "text", nullable=False)
    op.alter_column("claims", "assertion_type", nullable=False)
    op.alter_column("claims", "confidence", nullable=False)
    op.alter_column("claims", "status", nullable=False)
    op.alter_column("claims", "inferred_from_claim_ids", nullable=False)

    op.create_check_constraint(
        "claims_assertion_type_check",
        "claims",
        "assertion_type IN ('fact', 'inference', 'opinion', 'contested')",
    )
    op.create_check_constraint(
        "claims_status_check",
        "claims",
        "status IN ('verified', 'unverified', 'unsupported', 'refuted', 'contested')",
    )
    op.create_check_constraint(
        "claims_confidence_check", "claims", "confidence >= 0.0 AND confidence <= 1.0"
    )

    op.drop_index("ix_claim_versions_status", table_name="claim_versions")
    op.drop_index("ix_claim_versions_claim_version", table_name="claim_versions")
    op.drop_table("claim_versions")
