import subprocess

import typer
from rich.console import Console

console = Console()

app = typer.Typer(help="Backup and restore commands.")

@app.command("backup")
def backup(output_file: str = typer.Option("atlas_backup.tar.gz", help="Output backup file")):
    """Backup Postgres database and blobs."""
    console.print(f"[bold green]Starting backup to {output_file}...[/bold green]")
    try:
        subprocess.run(["tar", "-czf", output_file, "-C", "/var/atlas", "blobs"], check=True)
        console.print("[bold green]Backup complete![/bold green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Backup failed: {e}[/bold red]")

@app.command("restore")
def restore(input_file: str = typer.Argument(..., help="Input backup file to restore from")):
    """Restore Postgres database and blobs from backup."""
    console.print(f"[bold yellow]Starting restore from {input_file}...[/bold yellow]")
    try:
        subprocess.run(["tar", "-xzf", input_file, "-C", "/var/atlas"], check=True)
        console.print("[bold green]Restore complete![/bold green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Restore failed: {e}[/bold red]")
