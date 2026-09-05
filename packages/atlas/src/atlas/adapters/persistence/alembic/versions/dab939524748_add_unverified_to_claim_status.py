"""add unverified to claim status

Revision ID: dab939524748
Revises: 8b9f0a1c2d3e
Create Date: 2026-08-31 02:45:39.444035+00:00

A Claim is `unverified` between extraction and verification. Without this value
the extraction agent had to write a verification status it had not earned.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dab939524748"
down_revision: str | None = "8b9f0a1c2d3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("claims_status_check", "claims", type_="check")
    op.create_check_constraint(
        "claims_status_check",
        "claims",
        "status IN ('verified', 'unverified', 'unsupported', 'refuted', 'contested')",
    )


def downgrade() -> None:
    op.drop_constraint("claims_status_check", "claims", type_="check")
    op.create_check_constraint(
        "claims_status_check",
        "claims",
        "status IN ('verified', 'unsupported', 'refuted', 'contested')",
    )
