"""Atlas CLI Entrypoint (Typer).

As specified in ARCHITECTURE.md §1:
- The CLI is a thin adapter over the same application use cases as the API.
- Full parity: Run creation, state machine execution, gate review, and quota inspection.
"""

import asyncio
import subprocess
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import typer
from atlas.adapters.container import Container
from atlas.adapters.persistence.database import get_session_manager, reset_session_manager
from atlas.adapters.persistence.repositories.execution_repository import ExecutionRepository
from atlas.adapters.persistence.repositories.focus_repository import FocusRepository
from atlas.application.usecases.approve_gate import ApproveGateUseCase
from atlas.application.usecases.create_channel import CreateChannelUseCase
from atlas.application.usecases.create_domain import CreateDomainUseCase
from atlas.application.usecases.create_run import CreateRunUseCase
from atlas.application.usecases.create_topic import CreateTopicUseCase
from atlas.application.usecases.get_run_status import (
    GetQuotaStatusUseCase,
    GetRunStatusUseCase,
    ListGatesUseCase,
    ListRunsUseCase,
)
from atlas.application.usecases.reject_gate import RejectGateUseCase
from atlas.domain.execution.models import RejectionAction, RejectionFeedback
from atlas.platform.config import get_settings
from rich.console import Console
from rich.table import Table
from sqlalchemy.ext.asyncio import AsyncSession

app = typer.Typer(
    name="atlas",
    help="Atlas: Knowledge-first autonomous documentary production system",
    no_args_is_help=True,
)
run_app = typer.Typer(name="run", help="Manage pipeline Runs", no_args_is_help=True)
gate_app = typer.Typer(
    name="gate", help="Manage suspension Gates and Approvals", no_args_is_help=True
)
quota_app = typer.Typer(name="quota", help="Inspect provider quota status", no_args_is_help=True)
domain_app = typer.Typer(name="domain", help="Manage research Domains", no_args_is_help=True)
topic_app = typer.Typer(name="topic", help="Manage Topics", no_args_is_help=True)
channel_app = typer.Typer(name="channel", help="Manage publishing Channels", no_args_is_help=True)

app.add_typer(run_app)
app.add_typer(gate_app)
app.add_typer(quota_app)
app.add_typer(domain_app)
app.add_typer(topic_app)
app.add_typer(channel_app)

console = Console()


def _build_container_and_repos(
    session: AsyncSession,
) -> tuple[Container, ExecutionRepository, FocusRepository]:
    """Build the container and the repositories a command needs on an active session.

    The pipeline runner is not built here: most commands only read state, and
    constructing the runner would demand provider credentials they never use.
    """
    container = Container(session)
    return (
        container,
        container.require_execution_repo(),
        container.require_focus_repo(),
    )


@asynccontextmanager
async def _managed_cli_context() -> AsyncGenerator[
    tuple[Container, ExecutionRepository, FocusRepository]
]:
    """Manage lifecycle of database session and engine cleanly within async CLI commands."""

    reset_session_manager()
    session_manager = get_session_manager()
    try:
        async with session_manager.session() as session:
            yield _build_container_and_repos(session)
    finally:
        await session_manager.close()
        reset_session_manager()


# =============================================================================
# Run Commands
# =============================================================================


@run_app.command("create")
def create_run_cmd(
    topic_id: str = typer.Argument(..., help="Unique Topic ID (e.g. topic_origin_of_chess)"),
    channel_id: str = typer.Option("origins", "--channel", "-c", help="Publishing channel"),
    actor_id: str = typer.Option("operator", "--actor", "-a", help="Actor initiating the run"),
    focus_id: str | None = typer.Option(None, "--focus-id", "-f", help="Optional Focus ID"),
) -> None:
    """Create a new pipeline Run and trigger execution."""

    async def _run() -> None:
        async with _managed_cli_context() as (container, exec_repo, focus_repo):
            runner = container.get_pipeline_runner()
            queue_broker = Container().queue_broker
            use_case = CreateRunUseCase(
                exec_repo,
                focus_repo,
                queue_broker,
                container.require_source_repo(),
                container.require_publishing_repo(),
            )

            run = await use_case.execute(
                topic_id=topic_id,
                channel_id=channel_id,
                actor_id=actor_id,
                focus_id=focus_id,
            )
            console.print(
                f"[green]✓ Run created:[/green] [bold]{run.id}[/bold] (Status: {run.status.value})"
            )

            # Execute stages
            with console.status(
                f"[bold cyan]Executing pipeline stages for {run.id}...[/bold cyan]"
            ):
                updated_run = await runner.run_pipeline(run.id)

            console.print(
                f"[blue]Run state after execution:[/blue] [bold]{updated_run.status.value}[/bold]"
            )
            if updated_run.status.value == "suspended":
                console.print(
                    "[yellow]⏸ Run suspended at a manual gate. Use 'atlas gate list' to inspect pending gates.[/yellow]"
                )

    asyncio.run(_run())


@run_app.command("status")
def get_run_status_cmd(
    run_id: str = typer.Argument(..., help="Run ID to inspect"),
) -> None:
    """Inspect current status, steps, and gates of a Run."""

    async def _run() -> None:
        async with _managed_cli_context() as (_container, exec_repo, _):
            use_case = GetRunStatusUseCase(exec_repo)
            run = await use_case.execute(run_id)

            console.print(f"[bold]Run ID:[/bold] {run.id}")
            console.print(f"[bold]Topic ID:[/bold] {run.topic_id}")
            console.print(f"[bold]Channel:[/bold] {run.channel_id}")
            console.print(f"[bold]Status:[/bold] [cyan]{run.status.value}[/cyan]")
            console.print(f"[bold]Trace ID:[/bold] {run.trace_id}")
            console.print(f"[bold]Actor:[/bold] {run.actor_id}")

            steps = await exec_repo.list_steps_for_run(run_id)
            if steps:
                table = Table(title=f"Steps for {run_id}")
                table.add_column("Index", style="dim")
                table.add_column("Stage Name", style="bold")
                table.add_column("Status")
                table.add_column("Artifact Ref")
                for s in steps:
                    color = (
                        "green"
                        if s.status.value == "succeeded"
                        else "yellow"
                        if s.status.value == "suspended"
                        else "white"
                    )
                    table.add_row(
                        str(s.step_index),
                        s.step_name,
                        f"[{color}]{s.status.value}[/{color}]",
                        s.output_artifact_ref or "-",
                    )
                console.print(table)

    asyncio.run(_run())


@run_app.command("list")
def list_runs_cmd(
    limit: int = typer.Option(50, "--limit", "-l", help="Max number of runs to show"),
) -> None:
    """List recent pipeline Runs."""

    async def _run() -> None:
        async with _managed_cli_context() as (_container, exec_repo, _):
            use_case = ListRunsUseCase(exec_repo)
            runs = await use_case.execute(limit=limit)

            if not runs:
                console.print("[dim]No runs found.[/dim]")
                return

            table = Table(title="Pipeline Runs")
            table.add_column("Run ID", style="bold")
            table.add_column("Topic ID")
            table.add_column("Channel")
            table.add_column("Status")
            table.add_column("Created At")
            for r in runs:
                table.add_row(
                    r.id,
                    r.topic_id,
                    r.channel_id,
                    r.status.value,
                    r.created_at.strftime("%Y-%m-%d %H:%M UTC"),
                )
            console.print(table)

    asyncio.run(_run())


# =============================================================================
# Gate Commands
# =============================================================================


@gate_app.command("list")
def list_gates_cmd() -> None:
    """List all pending Gates awaiting operator review."""

    async def _run() -> None:
        async with _managed_cli_context() as (_container, exec_repo, _):
            use_case = ListGatesUseCase(exec_repo)
            gates = await use_case.execute(pending_only=True)

            if not gates:
                console.print("[green]✓ No pending gates. Pipeline queue is clear.[/green]")
                return

            table = Table(title="Pending Gates Awaiting Review")
            table.add_column("Gate ID", style="bold")
            table.add_column("Run ID")
            table.add_column("Step ID")
            table.add_column("Gate Type")
            table.add_column("Requested At")
            for g in gates:
                table.add_row(
                    g.id,
                    g.run_id,
                    g.step_id,
                    g.gate_type.value,
                    g.requested_at.strftime("%Y-%m-%d %H:%M UTC"),
                )
            console.print(table)

    asyncio.run(_run())


@gate_app.command("approve")
def approve_gate_cmd(
    gate_id: str = typer.Argument(..., help="Gate ID to approve"),
    actor_id: str = typer.Option("operator", "--actor", "-a", help="Actor granting approval"),
) -> None:
    """Approve a pending Gate and resume pipeline execution."""

    async def _run() -> None:
        async with _managed_cli_context() as (container, exec_repo, _):
            runner = container.get_pipeline_runner()
            queue_broker = Container().queue_broker
            use_case = ApproveGateUseCase(exec_repo, queue_broker)

            updated_gate, approval = await use_case.execute(gate_id=gate_id, actor_id=actor_id)
            console.print(f"[green]✓ Gate {gate_id} approved by {actor_id}[/green]")

            with console.status(
                f"[bold cyan]Resuming pipeline execution for {updated_gate.run_id}...[/bold cyan]"
            ):
                updated_run = await runner.run_pipeline(updated_gate.run_id)

            console.print(
                f"[blue]Run state after resumption:[/blue] [bold]{updated_run.status.value}[/bold]"
            )

    asyncio.run(_run())


@gate_app.command("reject")
def reject_gate_cmd(
    gate_id: str = typer.Argument(..., help="Gate ID to reject"),
    target_ref: str = typer.Option(
        ..., "--target-ref", "-t", help="Target reference (Beat ID, Asset ID)"
    ),
    rubric_dimension: str = typer.Option(..., "--rubric-dimension", "-d", help="Rubric dimension"),
    reason: str = typer.Option(..., "--reason", "-r", help="Structured rationale for rejection"),
    action: str = typer.Option(
        "regenerate", "--action", help="Action: regenerate, branch, or abandon"
    ),
    actor_id: str = typer.Option("operator", "--actor", "-a", help="Actor rejecting the gate"),
) -> None:
    """Reject a Gate with mandatory structured feedback (SPEC §7)."""

    async def _run() -> None:
        async with _managed_cli_context() as (container, exec_repo, _):
            runner = container.get_pipeline_runner()
            queue_broker = Container().queue_broker
            use_case = RejectGateUseCase(exec_repo, queue_broker)

            feedback = RejectionFeedback(
                target_ref=target_ref,
                rubric_dimension=rubric_dimension,
                reason=reason,
                action=RejectionAction(action),
            )

            updated_gate, approval = await use_case.execute(
                gate_id=gate_id, feedback=feedback, actor_id=actor_id
            )
            console.print(f"[yellow]✗ Gate {gate_id} rejected with action '{action}'[/yellow]")

            if action != "abandon":
                with console.status(
                    f"[bold cyan]Advancing rework cycle for {updated_gate.run_id}...[/bold cyan]"
                ):
                    updated_run = await runner.run_pipeline(updated_gate.run_id)
                console.print(
                    f"[blue]Run state after rework advance:[/blue] [bold]{updated_run.status.value}[/bold]"
                )

    asyncio.run(_run())


# =============================================================================
# Catalogue Commands — the rows a Run needs before it can exist
#
# Defect V-15: `save_domain`, `save_topic` and `save_channel` had no production
# caller at all, so a Run could only be created against a database some test had
# seeded. These are the operator's way in.
# =============================================================================


@domain_app.command("create")
def create_domain_cmd(
    domain_id: str = typer.Argument(..., help="Unique Domain ID (e.g. dom_history)"),
    name: str = typer.Option(..., "--name", "-n", help="Display name (e.g. History)"),
    description: str = typer.Option(..., "--description", "-d", help="Coverage description"),
) -> None:
    """Register a research Domain."""

    async def _run() -> None:
        async with _managed_cli_context() as (_container, _exec_repo, focus_repo):
            domain = await CreateDomainUseCase(focus_repo).execute(
                domain_id=domain_id, name=name, description=description
            )
            console.print(f"[green]\u2713 Domain created:[/green] [bold]{domain.id}[/bold]")

    asyncio.run(_run())


@topic_app.command("create")
def create_topic_cmd(
    topic_id: str = typer.Argument(..., help="Unique Topic ID (e.g. topic_origin_of_chess)"),
    title: str = typer.Option(..., "--title", "-t", help="Human-readable Topic title"),
    domain_id: str = typer.Option(..., "--domain", "-D", help="Existing Domain ID"),
    entity_id: str | None = typer.Option(None, "--entity", "-e", help="Wikidata QID, if known"),
) -> None:
    """Register a Topic against an existing Domain."""

    async def _run() -> None:
        async with _managed_cli_context() as (container, _exec_repo, focus_repo):
            topic = await CreateTopicUseCase(container.require_source_repo(), focus_repo).execute(
                topic_id=topic_id, title=title, domain_id=domain_id, entity_id=entity_id
            )
            console.print(
                f"[green]\u2713 Topic created:[/green] [bold]{topic.id}[/bold] "
                f"(Status: {topic.status.value})"
            )

    asyncio.run(_run())


@channel_app.command("create")
def create_channel_cmd(
    channel_id: str = typer.Argument(..., help="Unique Channel ID (e.g. origins)"),
    name: str = typer.Option(..., "--name", "-n", help="Display name"),
    audience_timezone: str = typer.Option(
        "America/New_York", "--timezone", "-z", help="IANA timezone of the Channel's audience"
    ),
) -> None:
    """Register a publishing Channel."""

    async def _run() -> None:
        async with _managed_cli_context() as (container, _exec_repo, _focus_repo):
            channel = await CreateChannelUseCase(container.require_publishing_repo()).execute(
                channel_id=channel_id, name=name, audience_timezone=audience_timezone
            )
            console.print(
                f"[green]\u2713 Channel created:[/green] [bold]{channel.id}[/bold] "
                f"({channel.audience_timezone})"
            )

    asyncio.run(_run())


# =============================================================================
# Quota Commands
# =============================================================================


@quota_app.command("status")
def quota_status_cmd() -> None:
    """Inspect current quota availability across providers."""

    async def _run() -> None:
        async with _managed_cli_context() as (_container, exec_repo, _):
            use_case = GetQuotaStatusUseCase(exec_repo)
            status_data = await use_case.execute()

            console.print(f"[bold]System Status:[/bold] [green]{status_data['status']}[/green]")
            table = Table(title="Provider Quota Status")
            table.add_column("Provider", style="bold")
            table.add_column("RPM Remaining")
            table.add_column("RPD Remaining")
            table.add_column("Status")
            for prov, info in status_data["providers"].items():
                table.add_row(
                    prov,
                    str(info.get("rpm_remaining", "-")),
                    str(info.get("rpd_remaining", "-")),
                    info.get("status", "active"),
                )
            console.print(table)

    asyncio.run(_run())


# =============================================================================
# Deployment Commands
# =============================================================================


@app.command("backup")
def backup_cmd(
    output_file: str = typer.Option("atlas_backup.tar.gz", help="Output backup file"),
) -> None:
    """Backup Postgres database and blobs."""
    console.print(f"[bold green]Starting backup to {output_file}...[/bold green]")
    try:
        settings = get_settings()
        sync_db_url = settings.database_sync_url.replace("+psycopg", "").replace("+asyncpg", "")
        subprocess.run(["pg_dump", sync_db_url, "-F", "c", "-f", "/tmp/db_dump.custom"], check=True)

        # Tar blobs + DB dump
        storage_path = Path(settings.storage_root).resolve()
        parent_dir = str(storage_path.parent)
        folder_name = storage_path.name

        cmd = ["tar", "-czf", str(Path(output_file).resolve()), "-C", "/tmp", "db_dump.custom"]
        if storage_path.exists():
            cmd.extend(["-C", parent_dir, folder_name])

        subprocess.run(cmd, check=True)
        console.print("[bold green]Backup complete![/bold green]")
    except (subprocess.CalledProcessError, OSError) as e:
        console.print(f"[bold red]Backup failed: {e}[/bold red]")
        raise typer.Exit(code=1) from e


@app.command("restore")
def restore_cmd(
    input_file: str = typer.Argument(..., help="Input backup file to restore from"),
) -> None:
    """Restore Postgres database and blobs from backup."""
    console.print(f"[bold yellow]Starting restore from {input_file}...[/bold yellow]")
    try:
        settings = get_settings()
        # Untar
        subprocess.run(["tar", "-xzf", input_file, "-C", "/tmp"], check=True)
        if Path("/tmp/blobs").exists():
            Path(settings.storage_root).parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["cp", "-r", "/tmp/blobs", str(Path(settings.storage_root).parent)], check=True
            )
        # Restore DB
        sync_db_url = settings.database_sync_url.replace("+psycopg", "").replace("+asyncpg", "")
        subprocess.run(["pg_restore", "-d", sync_db_url, "-1", "/tmp/db_dump.custom"], check=True)
        console.print("[bold green]Restore complete![/bold green]")
    except (subprocess.CalledProcessError, OSError) as e:
        console.print(f"[bold red]Restore failed: {e}[/bold red]")
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
