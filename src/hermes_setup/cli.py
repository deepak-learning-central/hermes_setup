"""Command-line interface for Hermes agent setup using Typer."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import load_config
from .docker import DockerOrchestrator
from .state import StateManager

app = typer.Typer(
    name="hermes-setup",
    help="CLI for managing Hermes agent setup",
    rich_markup_mode="markdown",
)

console = Console()


@app.command()
def init(
    config_file: Path | None = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Initialize Hermes agent setup project."""
    orchestrator = DockerOrchestrator()
    orchestrator.init_project()
    config = load_config()
    config.ensure_directories()

    console.print(Panel("[green]Initialization complete![/green]", title="Hermes Setup"))
    console.print("\nGenerated files:")
    console.print("  - docker/compose.yml")
    console.print("  - docker/compose.prod.yml")
    console.print("  - .env.example")
    console.print("  - .gitignore")
    console.print("  - .pre-commit-config.yaml")
    console.print("  - .gitleaks.toml")
    console.print("\nNext steps:")
    console.print("  Option A (Web UI - recommended):")
    console.print("    1. Run: hermes-setup web")
    console.print("    2. Open http://127.0.0.1:8765 in your browser")
    console.print("    3. Configure and save — encrypted config stored in .hermes-config.enc")
    console.print("  Option B (CLI only):")
    console.print("    1. Copy .env.example to .env and fill in your values")
    console.print("    2. Run: hermes-setup up")


@app.command()
def up(
    production: bool = typer.Option(
        False, "--production", "-p", help="Deploy to production environment"
    ),
    pull: bool = typer.Option(True, "--pull/--no-pull", help="Pull latest image"),
) -> None:
    """Start Hermes agent containers."""
    config = load_config()
    orchestrator = DockerOrchestrator(config)

    issues = orchestrator.validate_environment()
    if issues:
        console.print("[red]Environment validation failed:[/red]")
        for issue in issues:
            console.print(f"  • {issue}")
        raise typer.Exit(1)

    if pull:
        console.print("[yellow]Pulling latest image...[/yellow]")
        if not orchestrator.pull_image():
            console.print("[red]Failed to pull Docker image[/red]")
            raise typer.Exit(1)

    console.print("[yellow]Starting Hermes agent...[/yellow]")
    if orchestrator.start(production=production):
        console.print("[green]Hermes agent started successfully![/green]")
    else:
        console.print("[red]Failed to start Hermes agent[/red]")
        raise typer.Exit(1)


@app.command()
def down(
    production: bool = typer.Option(False, "--production", "-p", help="Stop production containers"),
    volumes: bool = typer.Option(False, "--volumes", "-v", help="Remove volumes"),
) -> None:
    """Stop Hermes agent containers."""
    config = load_config()
    orchestrator = DockerOrchestrator(config)

    console.print("[yellow]Stopping Hermes agent...[/yellow]")
    if orchestrator.stop(production=production, volumes=volumes):
        console.print("[green]Hermes agent stopped successfully![/green]")
    else:
        console.print("[red]Failed to stop Hermes agent[/red]")
        raise typer.Exit(1)


@app.command(name="restart")
def restart_cmd(
    production: bool = typer.Option(
        False, "--production", "-p", help="Restart production containers"
    ),
) -> None:
    """Restart Hermes agent containers."""
    config = load_config()
    orchestrator = DockerOrchestrator(config)

    console.print("[yellow]Restarting Hermes agent...[/yellow]")
    if orchestrator.restart(production=production):
        console.print("[green]Hermes agent restarted successfully![/green]")
    else:
        console.print("[red]Failed to restart Hermes agent[/red]")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show Hermes agent status."""
    config = load_config()
    orchestrator = DockerOrchestrator(config)

    status = orchestrator.status()

    table = Table(title="Hermes Agent Status")
    table.add_column("State", style="bold")
    table.add_column("Status", style="bold")
    table.add_column("Value", style="cyan")

    running_icon = "[green]●[/green]" if status["running"] else "[red]○[/red]"
    table.add_row("Container", "Status", running_icon)

    state_manager = StateManager(config)
    paths = state_manager.get_persistent_state_paths()

    for name, path in paths.items():
        exists = "exists" if path.exists() else "missing"
        table.add_row("State", name, exists)

    console.print(table)


@app.command()
def logs(
    lines: int = typer.Option(100, "--lines", "-n", help="Number of lines"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
) -> None:
    """View Hermes agent logs."""
    config = load_config()
    orchestrator = DockerOrchestrator(config)

    console.print(f"[yellow]Fetching last {lines} log lines...[/yellow]")
    log_output = orchestrator.logs(follow=follow, tail=lines)
    console.print(log_output)


@app.command()
def update(
    production: bool = typer.Option(
        False, "--production", "-p", help="Update production deployment"
    ),
) -> None:
    """Update Hermes agent to latest image."""
    config = load_config()
    orchestrator = DockerOrchestrator(config)

    console.print("[yellow]Updating Hermes agent...[/yellow]")
    if orchestrator.pull_image():
        if orchestrator.zero_downtime_deploy(production=production):
            console.print("[green]Hermes agent updated successfully![/green]")
        else:
            console.print("[red]Update failed - attempting rollback[/red]")
            orchestrator.rollback(production=production)
            raise typer.Exit(1)
    else:
        console.print("[red]Failed to pull latest image[/red]")
        raise typer.Exit(1)


@app.command()
def config(
    name: str | None = typer.Option(None, "--name", "-n", help="Config variable to read"),
) -> None:
    """Show or edit configuration."""
    config = load_config()

    if name:
        if hasattr(config, name):
            value = getattr(config, name)
            console.print(f"{name}: {value}")
        else:
            console.print(f"[red]Unknown configuration variable: {name}[/red]")
    else:
        table = Table(title="Hermes Configuration")
        table.add_column("Variable", style="bold")
        table.add_column("Value")
        for field_name, _field_info in config.model_fields.items():
            value = getattr(config, field_name)
            table.add_row(field_name, str(value))
        console.print(table)


@app.command()
def backup(reason: str = typer.Option("manual", "--reason", "-r", help="Backup reason")) -> None:
    """Create state backup."""
    config = load_config()
    state_manager = StateManager(config)
    state_manager.ensure_directories()

    backup_path = state_manager.backup_state(reason)
    console.print(f"[green]Backup created at: {backup_path}[/green]")


@app.command()
def restore(
    backup_path: Path | None = typer.Option(None, "--path", "-p", help="Backup path"),
) -> None:
    """Restore from backup."""
    config = load_config()
    state_manager = StateManager(config)

    if state_manager.restore_backup(backup_path):
        console.print("[green]Restored from backup successfully![/green]")
    else:
        console.print("[red]Failed to restore from backup[/red]")
        raise typer.Exit(1)


@app.command()
def diagnose() -> None:
    """Run diagnostics."""
    from .utils import get_system_info, is_docker_available, is_docker_compose_available

    console.print(Panel.fit("[bold blue]Hermes Setup Diagnostics[/bold]"))

    sys_info = get_system_info()
    for key, value in sys_info.items():
        console.print(f"  {key}: {value}")

    table = Table(title="Tool Availability")
    table.add_column("Tool", style="bold")
    table.add_column("Status")
    table.add_row("Docker", "✓ Available" if is_docker_available() else "✗ Not available")
    table.add_row(
        "Docker Compose", "✓ Available" if is_docker_compose_available() else "✗ Not available"
    )
    console.print(table)


@app.command("generate:env-template")
def generate_env_template(
    path: Path | None = typer.Option(None, "--path", "-p", help="Output path"),
) -> None:
    """Generate .env.example template."""
    orchestrator = DockerOrchestrator()
    orchestrator.generate_env_example(path)
    if path:
        console.print(f"[green]Generated: {path}[/green]")
    else:
        console.print("[green]Generated: .env.example[/green]")


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(8765, "--port", "-p", help="Port to bind"),
) -> None:
    """Launch the web-based setup server."""
    try:
        from .web.backend import run

        run(host=host, port=port)
    except ImportError as e:
        console.print(f"[red]Web backend not available: {e}[/red]")
        console.print("[yellow]Install required dependencies:[/yellow]")
        console.print("  uv sync")
        raise typer.Exit(1)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
