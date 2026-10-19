"""Terminal User Interface for Hermes agent setup using Textual."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Log,
    Markdown,
    Static,
    TabbedContent,
    TabPane,
)

from .config import HermesConfig, load_config
from .docker import DockerOrchestrator
from .state import StateManager
from .utils import get_system_info, is_docker_available, is_docker_compose_available


class DockerStatus(Static):
    """Widget showing Docker status."""

    def compose(self) -> ComposeResult:
        yield Label("Docker Status", classes="section-title")
        yield Static(id="docker-status")


class SystemInfo(Static):
    """Widget showing system information."""

    def compose(self) -> ComposeResult:
        yield Label("System Information", classes="section-title")
        yield DataTable(id="system-info")


class ContainerStatus(Static):
    """Widget showing container status."""

    running = reactive(False)
    health = reactive("unknown")

    def compose(self) -> ComposeResult:
        yield Label("Container Status", classes="section-title")
        yield DataTable(id="container-status")


class LogViewer(Static):
    """Widget for viewing logs."""

    def compose(self) -> ComposeResult:
        yield Label("Container Logs", classes="section-title")
        yield Log(id="log-viewer", highlight=True, markup=True)


class SetupWizard(ModalScreen):
    """First-run setup wizard screen."""

    CSS = """
    SetupWizard {
        align: center middle;
    }
    #wizard-container {
        width: 80%;
        max-width: 100;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    #wizard-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    .wizard-step {
        margin: 1 0;
    }
    .wizard-buttons {
        height: auto;
        margin-top: 1;
    }
    """

    def __init__(self, config: HermesConfig) -> None:
        super().__init__()
        self.config = config
        self.orchestrator = DockerOrchestrator(config)
        self.step = 0
        self.steps = ["docker", "ports", "storage", "model", "secrets", "complete"]
        self.form_data = {}

    def compose(self) -> ComposeResult:
        with Container(id="wizard-container"):
            yield Label(
                f"[bold]Hermes Setup Wizard - Step {self.step + 1}/{len(self.steps)}[/bold]",
                id="wizard-title",
            )
            yield Vertical(id="wizard-content")
            yield Horizontal(classes="wizard-buttons")

    def on_mount(self) -> None:
        self.show_step()

    def show_step(self) -> None:
        content = self.query_one("#wizard-content")
        content.remove_children()

        step_name = self.steps[self.step]
        if step_name == "docker":
            self._show_docker_step(content)
        elif step_name == "ports":
            self._show_ports_step(content)
        elif step_name == "storage":
            self._show_storage_step(content)
        elif step_name == "model":
            self._show_model_step(content)
        elif step_name == "secrets":
            self._show_secrets_step(content)
        elif step_name == "complete":
            self._show_complete_step(content)

        buttons = self.query_one(".wizard-buttons")
        buttons.remove_children()
        if self.step > 0:
            buttons.mount(Button("Back", id="wizard-back", variant="default"))
        if self.step < len(self.steps) - 1:
            buttons.mount(Button("Next", id="wizard-next", variant="primary"))
        else:
            buttons.mount(Button("Finish", id="wizard-finish", variant="success"))

    def _show_docker_step(self, content: Vertical) -> None:
        docker_ok = is_docker_available()
        compose_ok = is_docker_compose_available()
        content.mount(Label(f"Docker: {'✓ Available' if docker_ok else '✗ Not available'}"))
        content.mount(
            Label(f"Docker Compose: {'✓ Available' if compose_ok else '✗ Not available'}")
        )
        if not docker_ok:
            content.mount(Label("[red]Please install Docker before continuing[/red]"))

    def _show_ports_step(self, content: Vertical) -> None:
        content.mount(Label("Port Configuration"))
        host_input = Input(
            value=str(self.config.host_port),
            placeholder="Host port (default: 8000)",
            id="host-port",
        )
        container_input = Input(
            value=str(self.config.container_port),
            placeholder="Container port (default: 8000)",
            id="container-port",
        )
        content.mount(Label("Host Port:"))
        content.mount(host_input)
        content.mount(Label("Container Port:"))
        content.mount(container_input)

    def _show_storage_step(self, content: Vertical) -> None:
        content.mount(Label("Persistent Storage"))
        data_input = Input(
            value=self.config.data_dir,
            placeholder="Data directory",
            id="data-dir",
        )
        models_input = Input(
            value=self.config.models_dir,
            placeholder="Models directory",
            id="models-dir",
        )
        content.mount(Label("Data Directory:"))
        content.mount(data_input)
        content.mount(Label("Models Directory:"))
        content.mount(models_input)

    def _show_model_step(self, content: Vertical) -> None:
        content.mount(Label("Model Configuration"))
        model_input = Input(
            value=self.config.model_name,
            placeholder="Model name",
            id="model-name",
        )
        content.mount(Label("Model Name:"))
        content.mount(model_input)

    def _show_secrets_step(self, content: Vertical) -> None:
        content.mount(Label("API Keys (optional)"))
        hf_input = Input(
            value=self.config.hf_token or "",
            placeholder="HuggingFace token (optional)",
            password=True,
            id="hf-token",
        )
        openai_input = Input(
            value=self.config.openai_api_key or "",
            placeholder="OpenAI API key (optional)",
            password=True,
            id="openai-key",
        )
        content.mount(Label("HuggingFace Token:"))
        content.mount(hf_input)
        content.mount(Label("OpenAI API Key:"))
        content.mount(openai_input)

    def _show_complete_step(self, content: Vertical) -> None:
        content.mount(Label("[green]Setup Complete![/green]"))
        content.mount(Label("Click Finish to save configuration and create project files."))

    @on(Button.Pressed, "#wizard-next")
    def next_step(self) -> None:
        self.save_current_step()
        self.step += 1
        self.query_one("#wizard-title").update(
            f"[bold]Hermes Setup Wizard - Step {self.step + 1}/{len(self.steps)}[/bold]"
        )
        self.show_step()

    @on(Button.Pressed, "#wizard-back")
    def back_step(self) -> None:
        self.step -= 1
        self.query_one("#wizard-title").update(
            f"[bold]Hermes Setup Wizard - Step {self.step + 1}/{len(self.steps)}[/bold]"
        )
        self.show_step()

    @on(Button.Pressed, "#wizard-finish")
    def finish_wizard(self) -> None:
        self.save_current_step()
        self.orchestrator.init_project()
        self.dismiss(True)

    def save_current_step(self) -> None:
        step_name = self.steps[self.step]
        content = self.query_one("#wizard-content")

        if step_name == "ports":
            host_port = content.query_one("#host-port", Input).value
            container_port = content.query_one("#container-port", Input).value
            if host_port.isdigit():
                self.config.host_port = int(host_port)
            if container_port.isdigit():
                self.config.container_port = int(container_port)
        elif step_name == "storage":
            self.config.data_dir = content.query_one("#data-dir", Input).value or "./data"
            self.config.models_dir = content.query_one("#models-dir", Input).value or "./models"
        elif step_name == "model":
            self.config.model_name = content.query_one("#model-name", Input).value
        elif step_name == "secrets":
            hf_token = content.query_one("#hf-token", Input).value
            openai_key = content.query_one("#openai-key", Input).value
            if hf_token:
                self.config.hf_token = hf_token
            if openai_key:
                self.config.openai_api_key = openai_key


class ConfigScreen(Screen):
    """Configuration management screen."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, config: HermesConfig) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("General", id="general"):
                yield VerticalScroll(id="general-config")
            with TabPane("Docker", id="docker"):
                yield VerticalScroll(id="docker-config")
            with TabPane("Agent", id="agent"):
                yield VerticalScroll(id="agent-config")
            with TabPane("Advanced", id="advanced"):
                yield VerticalScroll(id="advanced-config")
        yield Footer()

    def on_mount(self) -> None:
        self._populate_general()
        self._populate_docker()
        self._populate_agent()
        self._populate_advanced()

    def _populate_general(self) -> None:
        container = self.query_one("#general-config")
        fields = [
            ("host_port", "Host Port", str(self.config.host_port)),
            ("container_port", "Container Port", str(self.config.container_port)),
            ("data_dir", "Data Directory", self.config.data_dir),
            ("models_dir", "Models Directory", self.config.models_dir),
            ("log_level", "Log Level", self.config.log_level),
        ]
        for key, label, value in fields:
            container.mount(Label(label))
            input_widget = Input(value=value, id=f"config-{key}")
            container.mount(input_widget)

    def _populate_docker(self) -> None:
        container = self.query_one("#docker-config")
        fields = [
            ("docker_image", "Docker Image", self.config.docker_image),
            ("memory_limit", "Memory Limit", self.config.memory_limit),
            ("cpus_limit", "CPU Limit", str(self.config.cpus_limit)),
        ]
        for key, label, value in fields:
            container.mount(Label(label))
            input_widget = Input(value=value, id=f"config-{key}")
            container.mount(input_widget)

    def _populate_agent(self) -> None:
        container = self.query_one("#agent-config")
        fields = [
            ("model_name", "Model Name", self.config.model_name),
            ("context_size", "Context Size", str(self.config.context_size)),
            ("temperature", "Temperature", str(self.config.temperature)),
            ("top_p", "Top P", str(self.config.top_p)),
            ("max_tokens", "Max Tokens", str(self.config.max_tokens)),
        ]
        for key, label, value in fields:
            container.mount(Label(label))
            input_widget = Input(value=value, id=f"config-{key}")
            container.mount(input_widget)

    def _populate_advanced(self) -> None:
        container = self.query_one("#advanced-config")
        container.mount(Label("Advanced settings - modify with caution"))
        fields = [
            ("hf_token", "HuggingFace Token", self.config.hf_token or ""),
            ("openai_api_key", "OpenAI API Key", self.config.openai_api_key or ""),
        ]
        for key, label, value in fields:
            container.mount(Label(label))
            input_widget = Input(value=value, password=True, id=f"config-{key}")
            container.mount(input_widget)

        save_btn = Button("Save Configuration", id="save-config", variant="primary")
        container.mount(save_btn)

    @on(Button.Pressed, "#save-config")
    def save_config(self) -> None:
        # In a real implementation, this would persist to .env
        self.app.notify("Configuration saved (would write to .env in real implementation)")
        self.app.pop_screen()


class LogScreen(Screen):
    """Log viewer screen."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, orchestrator: DockerOrchestrator, production: bool = False) -> None:
        super().__init__()
        self.orchestrator = orchestrator
        self.production = production
        self.follow = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield LogViewer()
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_logs()

    def action_refresh(self) -> None:
        self.refresh_logs()

    def refresh_logs(self) -> None:
        log_widget = self.query_one("#log-viewer", Log)
        log_widget.clear()
        logs = self.orchestrator.logs(production=self.production, follow=False, tail=200)
        log_widget.write(logs)


class ManagementScreen(Screen):
    """Management operations screen."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, config: HermesConfig, orchestrator: DockerOrchestrator) -> None:
        super().__init__()
        self.config = config
        self.orchestrator = orchestrator

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Label("Management Operations", classes="section-title")
            yield Container(id="management-buttons")
        yield Footer()

    def on_mount(self) -> None:
        container = self.query_one("#management-buttons")
        actions = [
            ("Create Backup", "backup", "primary"),
            ("Restore Backup", "restore", "default"),
            ("Cleanup (no volumes)", "cleanup", "warning"),
            ("Cleanup (with volumes)", "cleanup-volumes", "error"),
            ("View State Report", "state-report", "default"),
        ]
        for label, action, variant in actions:
            container.mount(Button(label, id=f"mgmt-{action}", variant=variant))

    @on(Button.Pressed, "#mgmt-backup")
    def do_backup(self) -> None:
        state_manager = StateManager(self.config)
        backup_path = state_manager.backup_state("manual")
        self.app.notify(f"Backup created: {backup_path}")

    @on(Button.Pressed, "#mgmt-restore")
    def do_restore(self) -> None:
        state_manager = StateManager(self.config)
        if state_manager.restore_backup():
            self.app.notify("Restored from latest backup")
        else:
            self.app.notify("No backups found", severity="error")

    @on(Button.Pressed, "#mgmt-cleanup")
    def do_cleanup(self) -> None:
        if self.orchestrator.cleanup(production=self.config is not None, volumes=False):
            self.app.notify("Cleanup complete")
        else:
            self.app.notify("Cleanup failed", severity="error")

    @on(Button.Pressed, "#mgmt-cleanup-volumes")
    def do_cleanup_volumes(self) -> None:
        if self.orchestrator.cleanup(production=self.config is not None, volumes=True):
            self.app.notify("Cleanup with volumes complete")
        else:
            self.app.notify("Cleanup failed", severity="error")

    @on(Button.Pressed, "#mgmt-state-report")
    def do_state_report(self) -> None:
        state_manager = StateManager(self.config)
        report = state_manager.generate_state_restore_report()
        self.app.notify(report, severity="info")


class HermesSetupApp(App):
    """Main Hermes Setup TUI Application."""

    CSS = """
    .section-title {
        text-style: bold;
        color: $primary;
        margin: 1 0;
    }
    DataTable {
        height: 12;
    }
    #main-container {
        padding: 1;
    }
    #sidebar {
        width: 30;
        border-right: solid $primary;
        padding: 1;
    }
    #content {
        padding: 1;
    }
    #action-buttons {
        height: auto;
        margin: 1 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "push_screen('status')", "Status"),
        Binding("c", "push_screen('config')", "Config"),
        Binding("l", "push_screen('logs')", "Logs"),
        Binding("m", "push_screen('management')", "Manage"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = load_config()
        self.orchestrator = DockerOrchestrator(self.config)
        self.state_manager = StateManager(self.config)
        self.first_run = not (Path.cwd() / ".env").exists()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-container"):
            with Vertical(id="sidebar"):
                yield Label("[bold]Hermes Setup[/bold]", classes="section-title")
                yield DockerStatus()
                yield SystemInfo()
                yield ContainerStatus()
                with Horizontal(id="action-buttons"):
                    yield Button("Start", id="btn-start", variant="success")
                    yield Button("Stop", id="btn-stop", variant="error")
                    yield Button("Restart", id="btn-restart", variant="primary")
            with Vertical(id="content"):
                yield TabbedContent(
                    TabPane("Dashboard", Markdown(id="dashboard-content")),
                    TabPane("Logs", Log(id="main-log-viewer")),
                )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_status()
        if self.first_run:
            self.push_screen(SetupWizard(self.config), self.on_wizard_done)

    def on_wizard_done(self, result: bool) -> None:
        if result:
            self.refresh_status()
            self.first_run = False

    def refresh_status(self) -> None:
        """Refresh all status widgets."""
        # Docker status
        docker_status = self.query_one("#docker-status", Static)
        docker_ok = is_docker_available()
        compose_ok = is_docker_compose_available()
        docker_status.update(
            f"Docker: {'[green]●[/green] Running' if docker_ok else '[red]○[/red] Not running'}\n"
            f"Compose: {'[green]●[/green] Available' if compose_ok else '[red]○[/red] Not available'}"
        )

        # System info
        sys_info = self.query_one("#system-info", DataTable)
        sys_info.clear(columns=True)
        sys_info.add_columns("Property", "Value")
        info = get_system_info()
        for key, value in info.items():
            sys_info.add_row(key.replace("_", " ").title(), value)

        # Container status
        container_status = self.query_one("#container-status", DataTable)
        container_status.clear(columns=True)
        container_status.add_columns("Container", "Status", "Health")
        status = self.orchestrator.status()
        for container in status["containers"]:
            running = container.get("State") == "running"
            health = container.get("Health", "unknown")
            container_status.add_row(
                container.get("Service", "unknown"),
                "[green]Running[/green]" if running else "[red]Stopped[/red]",
                f"[green]{health}[/green]" if health == "healthy" else f"[yellow]{health}[/yellow]",
            )

        # Dashboard
        dashboard = self.query_one("#dashboard-content", Markdown)
        status_emoji = "🟢" if status["running"] else "🔴"
        dashboard.update(f"""
# Hermes Agent Dashboard

**Status:** {status_emoji} {"Running" if status["running"] else "Stopped"}

**Quick Actions:**
- Start/Stop/Restart using buttons on the left
- Press `c` for Configuration
- Press `l` for Logs
- Press `m` for Management

**Persistent State:**
""")
        paths = self.state_manager.get_persistent_state_paths()
        for name, path in paths.items():
            exists = "✅" if path.exists() else "❌"
            dashboard.update(dashboard.text + f"\n- {name}: {exists}")

    @on(Button.Pressed, "#btn-start")
    async def start_container(self) -> None:
        self.notify("Starting Hermes agent...", timeout=3)
        success = await asyncio.to_thread(self.orchestrator.start)
        if success:
            self.notify("Hermes agent started!")
        else:
            self.notify("Failed to start Hermes agent", severity="error")
        self.refresh_status()

    @on(Button.Pressed, "#btn-stop")
    async def stop_container(self) -> None:
        self.notify("Stopping Hermes agent...", timeout=3)
        success = await asyncio.to_thread(self.orchestrator.stop)
        if success:
            self.notify("Hermes agent stopped!")
        else:
            self.notify("Failed to stop Hermes agent", severity="error")
        self.refresh_status()

    @on(Button.Pressed, "#btn-restart")
    async def restart_container(self) -> None:
        self.notify("Restarting Hermes agent...", timeout=5)
        success = await asyncio.to_thread(self.orchestrator.restart)
        if success:
            self.notify("Hermes agent restarted!")
        else:
            self.notify("Failed to restart Hermes agent", severity="error")
        self.refresh_status()

    def action_refresh(self) -> None:
        self.refresh_status()

    def action_push_screen(self, screen_name: str) -> None:
        """Push a screen by name."""
        screens = {
            "status": None,  # Dashboard is main screen
            "config": ConfigScreen(self.config),
            "logs": LogScreen(self.orchestrator),
            "management": ManagementScreen(self.config, self.orchestrator),
        }
        if screen_name in screens and screens[screen_name]:
            self.push_screen(screens[screen_name])


def launch_tui() -> None:
    """Launch the TUI application."""
    app = HermesSetupApp()
    app.run()
