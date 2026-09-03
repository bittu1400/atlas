import os

from alembic import command
from alembic.config import Config


def test_alembic_migrations_roundtrip() -> None:
    """Verify migrations apply upgrade head, downgrade base, and upgrade head without errors."""
    test_db_url = os.getenv(
        "ATLAS_TEST_DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5432/atlas_test"
    )
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url.replace("+asyncpg", "+psycopg"))

    # 1. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    # 2. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # 3. Downgrade to base again
    command.downgrade(alembic_cfg, "base")

    # 4. Final upgrade to head
    command.upgrade(alembic_cfg, "head")
