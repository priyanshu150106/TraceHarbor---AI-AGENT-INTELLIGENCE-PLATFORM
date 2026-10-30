"""
Phase B3 — Alembic Migration Chain Verification

Validates the full migration chain (001 -> 002 -> 003 -> 004 -> 005) for consistency,
and verifies schema upgrades against real PostgreSQL when available.
"""

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.tests.integration.conftest import POSTGRES_TEST_URL


def test_alembic_migration_chain_integrity() -> None:
    """
    Statically inspect all Alembic migration scripts to verify:
    1. Single head revision exists
    2. No broken or cyclic revision references
    3. Revisions 001 through 005 form a contiguous linear chain
    """
    api_root = Path(__file__).resolve().parents[3]
    alembic_ini_path = api_root / "alembic.ini"
    config = Config(str(alembic_ini_path))
    config.set_main_option("script_location", str(api_root / "alembic"))
    script = ScriptDirectory.from_config(config)

    # Verify single head
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly one Alembic head, found {heads}"
    assert heads[0] == "005_failure_intelligence"

    # Verify migration chain links
    revisions: list[str] = []
    rev = script.get_revision(heads[0])
    while rev is not None:
        revisions.append(rev.revision)
        if rev.down_revision is None:
            break
        rev = script.get_revision(rev.down_revision)

    expected_chain = [
        "005_failure_intelligence",
        "004_safety_module",
        "003_analytics_and_alerts",
        "002_evaluation_engine",
        "001_initial_schema",
    ]
    assert revisions == expected_chain, f"Migration chain mismatch: {revisions}"


@pytest.mark.integration
def test_alembic_upgrade_head_on_postgres(require_postgres: None) -> None:
    """
    Apply all migrations up to head against real PostgreSQL and verify success.
    Requires running PostgreSQL container.
    """
    from alembic import command

    api_root = Path(__file__).resolve().parents[3]
    alembic_ini_path = api_root / "alembic.ini"
    config = Config(str(alembic_ini_path))
    config.set_main_option("script_location", str(api_root / "alembic"))
    # Override database URL with integration test database
    config.set_main_option("sqlalchemy.url", POSTGRES_TEST_URL.replace("+asyncpg", ""))

    # Upgrade to head
    command.upgrade(config, "head")

    # Downgrade one step and re-upgrade to verify reversible schema changes
    command.downgrade(config, "004_safety_module")
    command.upgrade(config, "head")
