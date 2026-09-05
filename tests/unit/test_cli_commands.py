"""Unit and CLI Command Tests using Typer CliRunner."""

from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


def test_cli_help() -> None:
    """Verify top-level CLI help returns 0."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Atlas: Knowledge-first autonomous documentary production system" in result.output
    assert "run" in result.output
    assert "gate" in result.output
    assert "quota" in result.output


def test_cli_run_help() -> None:
    """Verify `atlas run --help`."""
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "create" in result.output
    assert "status" in result.output
    assert "list" in result.output


def test_cli_gate_help() -> None:
    """Verify `atlas gate --help`."""
    result = runner.invoke(app, ["gate", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "approve" in result.output
    assert "reject" in result.output


def test_cli_quota_help() -> None:
    """Verify `atlas quota --help`."""
    result = runner.invoke(app, ["quota", "--help"])
    assert result.exit_code == 0
    assert "status" in result.output


def test_cli_quota_status(db_session: object) -> None:  # noqa: ARG001
    """Verify `atlas quota status` execution."""
    result = runner.invoke(app, ["quota", "status"])
    assert result.exit_code == 0
    assert "System Status" in result.output
    assert "Provider Quota Status" in result.output


def test_cli_exposes_the_catalogue_commands_a_run_depends_on() -> None:
    """Defect V-15: a Run needs a Domain, a Topic and a Channel, and nothing could create one."""
    top_level = runner.invoke(app, ["--help"])
    assert top_level.exit_code == 0
    for group in ("domain", "topic", "channel"):
        assert group in top_level.output
        group_help = runner.invoke(app, [group, "--help"])
        assert group_help.exit_code == 0
        assert "create" in group_help.output
