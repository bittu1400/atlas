"""remediate_p0

Revision ID: 0002_remediate_p0
Revises: 0001_initial_schema
Create Date: 2026-08-20 18:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_remediate_p0"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add Check Constraints
    op.create_check_constraint(
        "approvals_decision_check", "approvals", "decision IN ('approved', 'rejected')"
    )
    op.create_check_constraint(
        "claim_evidence_stance_check", "claim_evidence", "stance IN ('supports', 'contradicts')"
    )
    op.create_check_constraint(
        "claims_assertion_type_check",
        "claims",
        "assertion_type IN ('fact', 'inference', 'opinion', 'contested')",
    )
    op.create_check_constraint(
        "claims_status_check",
        "claims",
        "status IN ('verified', 'unsupported', 'refuted', 'contested')",
    )
    op.create_check_constraint(
        "evidence_stance_check", "evidence", "stance IN ('supports', 'contradicts')"
    )
    op.create_check_constraint(
        "focus_scope_mode_check", "focus", "scope_mode IN ('hard', 'soft', 'exploratory')"
    )
    op.create_check_constraint(
        "gates_status_check", "gates", "status IN ('pending', 'approved', 'rejected')"
    )
    op.create_check_constraint(
        "gates_type_check", "gates", "gate_type IN ('automatic', 'manual', 'hybrid')"
    )
    op.create_check_constraint(
        "ko_status_check",
        "knowledge_object_versions",
        "status IN ('draft', 'verified', 'published', 'archived')",
    )
    op.create_check_constraint(
        "model_calls_outcome_check",
        "model_calls",
        "outcome IN ('success', 'error', 'rate_limited')",
    )
    op.create_check_constraint(
        "quota_window_type_check", "quota_ledger", "window_type IN ('minute', 'day')"
    )
    op.create_check_constraint(
        "runs_status_check",
        "runs",
        "status IN ('pending', 'running', 'suspended', 'reworking', 'completed', 'failed', 'abandoned')",
    )
    op.create_check_constraint(
        "sources_source_tier_check",
        "sources",
        "source_tier IN ('primary', 'peer_reviewed', 'institutional', 'reference', 'unvetted')",
    )
    op.create_check_constraint(
        "steps_status_check",
        "steps",
        "status IN ('pending', 'running', 'suspended', 'succeeded', 'failed', 'skipped')",
    )
    op.create_check_constraint(
        "topics_status_check",
        "topics",
        "status IN ('proposed', 'approved', 'researching', 'knowledge_ready', 'blocked', 'rejected', 'published')",
    )

    # A-04: Traceability constraint
    op.create_unique_constraint("uq_snapshot_source", "snapshots", ["id", "source_id"])
    op.drop_constraint("evidence_snapshot_id_fkey", "evidence", type_="foreignkey")
    op.create_foreign_key(
        "fk_evidence_snapshot",
        "evidence",
        "snapshots",
        ["snapshot_id", "source_id"],
        ["id", "source_id"],
        ondelete="RESTRICT",
    )

    # A-05: Triggers
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_delete() RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'Deletion from % is not allowed', TG_TABLE_NAME;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_update() RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'Updates to % are not allowed', TG_TABLE_NAME;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute(
        "CREATE TRIGGER trg_prevent_delete_topics BEFORE DELETE ON topics FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_delete_claims BEFORE DELETE ON claims FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_delete_domains BEFORE DELETE ON domains FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_delete_entities BEFORE DELETE ON entities FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_delete_channels BEFORE DELETE ON channels FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_delete_blackout_rules BEFORE DELETE ON blackout_rules FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_delete_sources BEFORE DELETE ON sources FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_delete_snapshots BEFORE DELETE ON snapshots FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_delete_evidence BEFORE DELETE ON evidence FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_delete_knowledge_object_versions BEFORE DELETE ON knowledge_object_versions FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_delete_claim_evidence BEFORE DELETE ON claim_evidence FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_delete_focus BEFORE DELETE ON focus FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_update_sources BEFORE UPDATE ON sources FOR EACH ROW EXECUTE FUNCTION prevent_update();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_update_snapshots BEFORE UPDATE ON snapshots FOR EACH ROW EXECUTE FUNCTION prevent_update();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_update_evidence BEFORE UPDATE ON evidence FOR EACH ROW EXECUTE FUNCTION prevent_update();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_update_knowledge_object_versions BEFORE UPDATE ON knowledge_object_versions FOR EACH ROW EXECUTE FUNCTION prevent_update();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_update_claim_evidence BEFORE UPDATE ON claim_evidence FOR EACH ROW EXECUTE FUNCTION prevent_update();"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_update_focus BEFORE UPDATE ON focus FOR EACH ROW EXECUTE FUNCTION prevent_update();"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_topics ON topics;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_claims ON claims;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_domains ON domains;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_entities ON entities;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_channels ON channels;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_blackout_rules ON blackout_rules;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_sources ON sources;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_snapshots ON snapshots;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_evidence ON evidence;")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_prevent_delete_knowledge_object_versions ON knowledge_object_versions;"
    )
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_claim_evidence ON claim_evidence;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_delete_focus ON focus;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_update_sources ON sources;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_update_snapshots ON snapshots;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_update_evidence ON evidence;")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_prevent_update_knowledge_object_versions ON knowledge_object_versions;"
    )
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_update_claim_evidence ON claim_evidence;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_update_focus ON focus;")

    op.execute("DROP FUNCTION IF EXISTS prevent_delete();")
    op.execute("DROP FUNCTION IF EXISTS prevent_update();")

    op.drop_constraint("fk_evidence_snapshot", "evidence", type_="foreignkey")
    op.create_foreign_key(
        "evidence_snapshot_id_fkey",
        "evidence",
        "snapshots",
        ["snapshot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("uq_snapshot_source", "snapshots", type_="unique")

    op.drop_constraint("topics_status_check", "topics", type_="check")
    op.drop_constraint("steps_status_check", "steps", type_="check")
    op.drop_constraint("sources_source_tier_check", "sources", type_="check")
    op.drop_constraint("runs_status_check", "runs", type_="check")
    op.drop_constraint("quota_window_type_check", "quota_ledger", type_="check")
    op.drop_constraint("model_calls_outcome_check", "model_calls", type_="check")
    op.drop_constraint("ko_status_check", "knowledge_object_versions", type_="check")
    op.drop_constraint("gates_type_check", "gates", type_="check")
    op.drop_constraint("gates_status_check", "gates", type_="check")
    op.drop_constraint("focus_scope_mode_check", "focus", type_="check")
    op.drop_constraint("evidence_stance_check", "evidence", type_="check")
    op.drop_constraint("claims_status_check", "claims", type_="check")
    op.drop_constraint("claims_assertion_type_check", "claims", type_="check")
    op.drop_constraint("claim_evidence_stance_check", "claim_evidence", type_="check")
    op.drop_constraint("approvals_decision_check", "approvals", type_="check")
