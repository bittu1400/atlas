"""remediate_p3_1

Revision ID: 7a8e9f0b1c2d
Revises: 697d28e88cb7
Create Date: 2026-08-21 00:00:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a8e9f0b1c2d"
down_revision: str | None = "697d28e88cb7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # P2-09: Drop time interval constraints preventing overnight windows (e.g. 22:00-06:00)
    op.drop_constraint("pub_windows_time_interval_check", "publishing_windows", type_="check")
    op.drop_constraint("blackout_time_interval_check", "blackout_rules", type_="check")

    # P2-10: Update fk_model_calls_steps from SET NULL to RESTRICT
    op.drop_constraint("fk_model_calls_steps", "model_calls", type_="foreignkey")
    op.create_foreign_key(
        "fk_model_calls_steps",
        "model_calls",
        "steps",
        ["step_id", "run_id"],
        ["id", "run_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Revert fk_model_calls_steps to SET NULL
    op.drop_constraint("fk_model_calls_steps", "model_calls", type_="foreignkey")
    op.create_foreign_key(
        "fk_model_calls_steps",
        "model_calls",
        "steps",
        ["step_id", "run_id"],
        ["id", "run_id"],
        ondelete="SET NULL",
    )

    # Re-add time interval checks
    op.create_check_constraint(
        "blackout_time_interval_check",
        "blackout_rules",
        "earliest_allowed_time < latest_allowed_time",
    )
    op.create_check_constraint(
        "pub_windows_time_interval_check",
        "publishing_windows",
        "local_start_time < local_end_time",
    )
