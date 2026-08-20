"""remediate_p1_p2

Revision ID: 697d28e88cb7
Revises: 0002_remediate_p0
Create Date: 2026-08-20 13:44:04.252561+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "697d28e88cb7"
down_revision: str | None = "0002_remediate_p0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # B-01: Composite FKs to prevent cross-run execution records
    op.drop_constraint("approvals_gate_id_fkey", "approvals", type_="foreignkey")
    op.drop_constraint("approvals_run_id_fkey", "approvals", type_="foreignkey")
    op.drop_constraint("gates_run_id_fkey", "gates", type_="foreignkey")
    op.drop_constraint("gates_step_id_fkey", "gates", type_="foreignkey")
    op.drop_constraint("model_calls_run_id_fkey", "model_calls", type_="foreignkey")
    op.drop_constraint("model_calls_step_id_fkey", "model_calls", type_="foreignkey")

    op.create_unique_constraint("uq_step_run", "steps", ["id", "run_id"])
    op.create_foreign_key(
        "fk_gates_steps",
        "gates",
        "steps",
        ["step_id", "run_id"],
        ["id", "run_id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint("uq_gate_run", "gates", ["id", "run_id"])
    op.create_foreign_key(
        "fk_approvals_gates",
        "approvals",
        "gates",
        ["gate_id", "run_id"],
        ["id", "run_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_model_calls_steps",
        "model_calls",
        "steps",
        ["step_id", "run_id"],
        ["id", "run_id"],
        ondelete="SET NULL",
    )

    # B-02: Approval double-resolution defense-in-depth
    op.create_unique_constraint("uq_approval_gate", "approvals", ["gate_id"])

    # B-04: Idempotency uniqueness
    op.drop_index("ix_steps_idempotency", table_name="steps")
    op.create_index(
        "ix_steps_idempotency", "steps", ["run_id", "step_name", "input_hash"], unique=True
    )
    op.create_unique_constraint("uq_idempotency_step", "idempotency_keys", ["step_id"])

    # B-06: Entity scoping integrity
    op.drop_index("ix_entities_wikidata_qid", table_name="entities")
    op.create_index("ix_entities_wikidata_qid", "entities", ["wikidata_qid"], unique=True)
    op.create_foreign_key(
        "fk_focus_entities", "focus", "entities", ["entity_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_kov_entities",
        "knowledge_object_versions",
        "entities",
        ["entity_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_topics_domains", "topics", "domains", ["domain_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "fk_topics_entities", "topics", "entities", ["entity_id"], ["id"], ondelete="SET NULL"
    )

    # B-07: Snapshot storage_key check
    op.create_check_constraint(
        "snapshots_storage_key_check",
        "snapshots",
        "storage_key = 'sha256/' || substr(content_hash, 1, 2) || '/' || substr(content_hash, 3, 2) || '/' || content_hash",
    )

    # C-02: Numeric bounds & intervals parity check constraints
    op.create_check_constraint(
        "pub_windows_day_of_week_check",
        "publishing_windows",
        "day_of_week >= 0 AND day_of_week <= 6",
    )
    op.create_check_constraint(
        "pub_windows_time_interval_check",
        "publishing_windows",
        "local_start_time < local_end_time",
    )
    op.create_check_constraint(
        "pub_windows_rank_check",
        "publishing_windows",
        "rank >= 1",
    )
    op.create_check_constraint(
        "pub_windows_confidence_check",
        "publishing_windows",
        "confidence >= 0.0 AND confidence <= 1.0",
    )
    op.create_check_constraint(
        "blackout_time_interval_check",
        "blackout_rules",
        "earliest_allowed_time < latest_allowed_time",
    )
    op.create_check_constraint(
        "snapshots_byte_size_check",
        "snapshots",
        "byte_size >= 0",
    )
    op.create_check_constraint(
        "evidence_confidence_check",
        "evidence",
        "confidence >= 0.0 AND confidence <= 1.0",
    )
    op.create_check_constraint(
        "claims_confidence_check",
        "claims",
        "confidence >= 0.0 AND confidence <= 1.0",
    )
    op.create_check_constraint(
        "kov_confidence_check",
        "knowledge_object_versions",
        "confidence >= 0.0 AND confidence <= 1.0",
    )
    op.create_check_constraint(
        "kov_quality_score_check",
        "knowledge_object_versions",
        "quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 100.0)",
    )
    op.create_check_constraint(
        "model_calls_input_tokens_check",
        "model_calls",
        "input_tokens >= 0",
    )
    op.create_check_constraint(
        "model_calls_output_tokens_check",
        "model_calls",
        "output_tokens >= 0",
    )
    op.create_check_constraint(
        "model_calls_latency_ms_check",
        "model_calls",
        "latency_ms >= 0",
    )
    op.create_check_constraint(
        "model_calls_cost_usd_check",
        "model_calls",
        "cost_usd >= 0.0",
    )
    op.create_check_constraint(
        "quota_tokens_consumed_check",
        "quota_ledger",
        "tokens_consumed >= 0",
    )
    op.create_check_constraint(
        "quota_requests_consumed_check",
        "quota_ledger",
        "requests_consumed >= 0",
    )


def downgrade() -> None:
    # Drop C-02 numeric bounds & intervals
    op.drop_constraint("quota_requests_consumed_check", "quota_ledger", type_="check")
    op.drop_constraint("quota_tokens_consumed_check", "quota_ledger", type_="check")
    op.drop_constraint("model_calls_cost_usd_check", "model_calls", type_="check")
    op.drop_constraint("model_calls_latency_ms_check", "model_calls", type_="check")
    op.drop_constraint("model_calls_output_tokens_check", "model_calls", type_="check")
    op.drop_constraint("model_calls_input_tokens_check", "model_calls", type_="check")
    op.drop_constraint("kov_quality_score_check", "knowledge_object_versions", type_="check")
    op.drop_constraint("kov_confidence_check", "knowledge_object_versions", type_="check")
    op.drop_constraint("claims_confidence_check", "claims", type_="check")
    op.drop_constraint("evidence_confidence_check", "evidence", type_="check")
    op.drop_constraint("snapshots_byte_size_check", "snapshots", type_="check")
    op.drop_constraint("blackout_time_interval_check", "blackout_rules", type_="check")
    op.drop_constraint("pub_windows_confidence_check", "publishing_windows", type_="check")
    op.drop_constraint("pub_windows_rank_check", "publishing_windows", type_="check")
    op.drop_constraint("pub_windows_time_interval_check", "publishing_windows", type_="check")
    op.drop_constraint("pub_windows_day_of_week_check", "publishing_windows", type_="check")

    # Drop B-07 snapshot storage_key check
    op.drop_constraint("snapshots_storage_key_check", "snapshots", type_="check")

    # Drop B-06 FKs and entity index
    op.drop_constraint("fk_topics_entities", "topics", type_="foreignkey")
    op.drop_constraint("fk_topics_domains", "topics", type_="foreignkey")
    op.drop_constraint("fk_kov_entities", "knowledge_object_versions", type_="foreignkey")
    op.drop_constraint("fk_focus_entities", "focus", type_="foreignkey")
    op.drop_index("ix_entities_wikidata_qid", table_name="entities")
    op.create_index("ix_entities_wikidata_qid", "entities", ["wikidata_qid"], unique=False)

    # Drop B-04 idempotency uniqueness
    op.drop_constraint("uq_idempotency_step", "idempotency_keys", type_="unique")
    op.drop_index("ix_steps_idempotency", table_name="steps")
    op.create_index(
        "ix_steps_idempotency", "steps", ["run_id", "step_name", "input_hash"], unique=False
    )

    # Drop B-02 approval uniqueness
    op.drop_constraint("uq_approval_gate", "approvals", type_="unique")

    # Drop B-01 composite FKs and unique constraints
    op.drop_constraint("fk_model_calls_steps", "model_calls", type_="foreignkey")
    op.drop_constraint("fk_approvals_gates", "approvals", type_="foreignkey")
    op.drop_constraint("uq_gate_run", "gates", type_="unique")
    op.drop_constraint("fk_gates_steps", "gates", type_="foreignkey")
    op.drop_constraint("uq_step_run", "steps", type_="unique")

    # Recreate original single-column FKs
    op.create_foreign_key(
        "model_calls_step_id_fkey",
        "model_calls",
        "steps",
        ["step_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "model_calls_run_id_fkey",
        "model_calls",
        "runs",
        ["run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "gates_step_id_fkey",
        "gates",
        "steps",
        ["step_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "gates_run_id_fkey",
        "gates",
        "runs",
        ["run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "approvals_run_id_fkey",
        "approvals",
        "runs",
        ["run_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "approvals_gate_id_fkey",
        "approvals",
        "gates",
        ["gate_id"],
        ["id"],
        ondelete="CASCADE",
    )
