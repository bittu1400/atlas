"""Initial database schema and seeded priors for Phase 2.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-30 00:00:00.000000

"""

from collections.abc import Sequence
from datetime import UTC

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    # 1. Domains
    op.create_table(
        "domains",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("research_profile", json_type, nullable=False),
    )

    # 2. Entities
    op.create_table(
        "entities",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("wikidata_qid", sa.String(32), nullable=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "domain_id",
            sa.String(64),
            sa.ForeignKey("domains.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("aliases", json_type, nullable=False),
    )
    op.create_index("ix_entities_wikidata_qid", "entities", ["wikidata_qid"])
    op.create_index("ix_entities_domain_id", "entities", ["domain_id"])

    # 3. Focus
    op.create_table(
        "focus",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("scope_mode", sa.String(32), nullable=False, server_default="soft"),
        sa.Column("facets", json_type, nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. Active Focus Pointer
    op.create_table(
        "active_focus",
        sa.Column("id", sa.String(32), primary_key=True, server_default="default"),
        sa.Column(
            "focus_id",
            sa.String(64),
            sa.ForeignKey("focus.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=False),
    )

    # 5. Topics
    op.create_table(
        "topics",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("domain_id", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_topics_domain_id", "topics", ["domain_id"])
    op.create_index("ix_topics_entity_id", "topics", ["entity_id"])

    # 6. Sources
    op.create_table(
        "sources",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("author", sa.String(256), nullable=True),
        sa.Column("published_date", sa.String(64), nullable=True),
        sa.Column("source_tier", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sources_url", "sources", ["url"])
    op.create_index("ix_sources_source_tier", "sources", ["source_tier"])

    # 7. Snapshots
    op.create_table(
        "snapshots",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(64),
            sa.ForeignKey("sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False, server_default="text/html"),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_snapshots_source_id", "snapshots", ["source_id"])
    op.create_index("ix_snapshots_content_hash", "snapshots", ["content_hash"])
    op.create_index("ix_snapshots_source_hash", "snapshots", ["source_id", "content_hash"])

    # 8. Evidence
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(64),
            sa.ForeignKey("sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            sa.String(64),
            sa.ForeignKey("snapshots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("locator", sa.String(256), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("stance", sa.String(32), nullable=False, server_default="supports"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_source_id", "evidence", ["source_id"])
    op.create_index("ix_evidence_snapshot_id", "evidence", ["snapshot_id"])

    # 9. Claims
    op.create_table(
        "claims",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("assertion_type", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="unsupported"),
        sa.Column("inferred_from_claim_ids", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_claims_assertion_type", "claims", ["assertion_type"])
    op.create_index("ix_claims_status", "claims", ["status"])

    # 10. Claim-Evidence link
    op.create_table(
        "claim_evidence",
        sa.Column(
            "claim_id",
            sa.String(64),
            sa.ForeignKey("claims.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "evidence_id",
            sa.String(64),
            sa.ForeignKey("evidence.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("stance", sa.String(32), nullable=False, server_default="supports"),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    # 11. Knowledge Object Versions (row-per-version)
    op.create_table(
        "knowledge_object_versions",
        sa.Column("ko_id", sa.String(64), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column(
            "topic_id",
            sa.String(64),
            sa.ForeignKey("topics.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ko_versions_topic_id", "knowledge_object_versions", ["topic_id"])
    op.create_index("ix_ko_versions_entity_id", "knowledge_object_versions", ["entity_id"])

    # 12. Knowledge Object Current Pointer
    op.create_table(
        "knowledge_object_current",
        sa.Column("ko_id", sa.String(64), primary_key=True),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ko_id", "current_version"],
            ["knowledge_object_versions.ko_id", "knowledge_object_versions.version"],
            ondelete="RESTRICT",
        ),
    )

    # 13. Knowledge Object Claims
    op.create_table(
        "knowledge_object_claims",
        sa.Column("ko_id", sa.String(64), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column(
            "claim_id",
            sa.String(64),
            sa.ForeignKey("claims.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.ForeignKeyConstraint(
            ["ko_id", "version"],
            ["knowledge_object_versions.ko_id", "knowledge_object_versions.version"],
            ondelete="CASCADE",
        ),
    )

    # 14. Claim Usages (Impact Index)
    op.create_table(
        "claim_usages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "claim_id",
            sa.String(64),
            sa.ForeignKey("claims.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("render_id", sa.String(64), nullable=False),
        sa.Column("beat_id", sa.String(64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_claim_usages_claim_id", "claim_usages", ["claim_id"])
    op.create_index("ix_claim_usages_render_id", "claim_usages", ["render_id"])

    # 15. Channels
    op.create_table(
        "channels",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column(
            "audience_timezone", sa.String(64), nullable=False, server_default="America/New_York"
        ),
        sa.Column("style_profile", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 16. Publishing Windows
    op.create_table(
        "publishing_windows",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "channel_id",
            sa.String(64),
            sa.ForeignKey("channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(64), nullable=False),
        sa.Column("format", sa.String(64), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("local_start_time", sa.Time(), nullable=False),
        sa.Column("local_end_time", sa.Time(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(256), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
    )
    op.create_index(
        "ix_pub_windows_lookup",
        "publishing_windows",
        ["channel_id", "platform", "format", "day_of_week"],
    )

    # 17. Blackout Rules
    op.create_table(
        "blackout_rules",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("local_start_time", sa.Time(), nullable=False),
        sa.Column("local_end_time", sa.Time(), nullable=False),
        sa.Column("is_enforced", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # 18. Runs
    op.create_table(
        "runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "topic_id",
            sa.String(64),
            sa.ForeignKey("topics.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "channel_id",
            sa.String(64),
            sa.ForeignKey("channels.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("captured_focus", json_type, nullable=False),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_runs_topic_id", "runs", ["topic_id"])
    op.create_index("ix_runs_channel_id", "runs", ["channel_id"])
    op.create_index("ix_runs_status", "runs", ["status"])
    op.create_index("ix_runs_trace_id", "runs", ["trace_id"])

    # 19. Steps
    op.create_table(
        "steps",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id", sa.String(64), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("step_name", sa.String(64), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("output_artifact_ref", sa.String(512), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_steps_run_id", "steps", ["run_id"])
    op.create_index("ix_steps_idempotency", "steps", ["run_id", "step_name", "input_hash"])

    # 20. Gates
    op.create_table(
        "gates",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id", sa.String(64), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "step_id", sa.String(64), sa.ForeignKey("steps.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("gate_type", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_gates_run_id", "gates", ["run_id"])
    op.create_index("ix_gates_step_id", "gates", ["step_id"])
    op.create_index("ix_gates_status", "gates", ["status"])

    # 21. Approvals
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "gate_id", sa.String(64), sa.ForeignKey("gates.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "run_id", sa.String(64), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("feedback", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_approvals_gate_id", "approvals", ["gate_id"])
    op.create_index("ix_approvals_run_id", "approvals", ["run_id"])

    # 22. Resource Locks
    op.create_table(
        "resource_locks",
        sa.Column("resource_name", sa.String(64), primary_key=True),
        sa.Column("holder_id", sa.String(128), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_resource_locks_expires_at", "resource_locks", ["expires_at"])

    # 23. Idempotency Keys
    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(256), primary_key=True),
        sa.Column(
            "step_id", sa.String(64), sa.ForeignKey("steps.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 24. Model Calls Audit
    op.create_table(
        "model_calls",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "run_id", sa.String(64), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "step_id", sa.String(64), sa.ForeignKey("steps.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(128), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("outcome", sa.String(32), nullable=False, server_default="success"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_calls_run_id", "model_calls", ["run_id"])
    op.create_index("ix_model_calls_created_at", "model_calls", ["created_at"])

    # 25. Quota Ledger
    op.create_table(
        "quota_ledger",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("window_type", sa.String(32), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tokens_consumed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requests_consumed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "run_id", sa.String(64), sa.ForeignKey("runs.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quota_window", "quota_ledger", ["provider", "window_type", "window_start"])

    # Seed Default Data (Blackout rules, initial channel, initial domains)
    _seed_initial_data()


def _seed_initial_data() -> None:
    """Seed initial defaults for Channel ORIGINS, default domains, and blackout rule."""
    from datetime import datetime, time

    now = datetime(2026, 7, 30, 0, 0, 0, tzinfo=UTC)

    # Seed Blackout Rule (06:00 - 22:00)
    op.bulk_insert(
        sa.table(
            "blackout_rules",
            sa.column("id", sa.String),
            sa.column("local_start_time", sa.Time),
            sa.column("local_end_time", sa.Time),
            sa.column("is_enforced", sa.Boolean),
        ),
        [
            {
                "id": "blk_default",
                "local_start_time": time(6, 0),
                "local_end_time": time(22, 0),
                "is_enforced": True,
            }
        ],
    )

    # Seed Channel ORIGINS (ADR-0007, D4)
    op.bulk_insert(
        sa.table(
            "channels",
            sa.column("id", sa.String),
            sa.column("name", sa.String),
            sa.column("audience_timezone", sa.String),
            sa.column("style_profile", json_type),
            sa.column("created_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": "origins",
                "name": "ORIGINS",
                "audience_timezone": "America/New_York",
                "style_profile": {
                    "display_font": "Playfair Display",
                    "body_font": "Inter",
                    "target_duration_seconds": 60,
                    "color_palette": ["#0F172A", "#F8FAFC", "#E2E8F0"],
                    "motion_style": "slow_pan_zoom",
                    "sound_profile": "tactile_keystroke_ambient",
                },
                "created_at": now,
            }
        ],
    )

    # Seed Default Domains (Animal, History, Technology, Science)
    op.bulk_insert(
        sa.table(
            "domains",
            sa.column("id", sa.String),
            sa.column("name", sa.String),
            sa.column("description", sa.Text),
            sa.column("research_profile", json_type),
        ),
        [
            {
                "id": "dom_animal",
                "name": "Animal",
                "description": "Zoology, animal behavior, biology, and conservation",
                "research_profile": {
                    "preferred_apis": ["openalex", "crossref", "wikidata"],
                    "source_allowlist": [
                        "*.nature.com",
                        "*.sciencemag.org",
                        "*.iucnredlist.org",
                        "*.si.edu",
                    ],
                    "source_tier_floor": "peer_reviewed",
                    "vocabulary": ["species", "habitat", "behavior", "evolution", "diet"],
                    "disambiguation_hints": ["taxonomic classification", "genus", "wildlife"],
                },
            },
            {
                "id": "dom_history",
                "name": "History",
                "description": "Historical events, documents, archives, and archaeology",
                "research_profile": {
                    "preferred_apis": ["loc", "archive_org", "europeana", "smithsonian"],
                    "source_allowlist": [
                        "*.loc.gov",
                        "*.archives.gov",
                        "*.si.edu",
                        "*.rijksmuseum.nl",
                        "*.metmuseum.org",
                    ],
                    "source_tier_floor": "primary",
                    "vocabulary": ["manuscript", "treaty", "chronicle", "archaeology", "era"],
                    "disambiguation_hints": ["historical era", "century", "historical figure"],
                },
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("quota_ledger")
    op.drop_table("model_calls")
    op.drop_table("idempotency_keys")
    op.drop_table("resource_locks")
    op.drop_table("approvals")
    op.drop_table("gates")
    op.drop_table("steps")
    op.drop_table("runs")
    op.drop_table("blackout_rules")
    op.drop_table("publishing_windows")
    op.drop_table("channels")
    op.drop_table("claim_usages")
    op.drop_table("knowledge_object_claims")
    op.drop_table("knowledge_object_current")
    op.drop_table("knowledge_object_versions")
    op.drop_table("claim_evidence")
    op.drop_table("claims")
    op.drop_table("evidence")
    op.drop_table("snapshots")
    op.drop_table("sources")
    op.drop_table("topics")
    op.drop_table("active_focus")
    op.drop_table("focus")
    op.drop_table("entities")
    op.drop_table("domains")
