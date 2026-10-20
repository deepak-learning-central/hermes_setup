"""High-level service that wraps the existing Docker orchestrator and config.

This module isolates the web backend from direct imports of legacy modules
while reusing 100% of the existing functionality (Docker, config, state).
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Any

from ..config import HermesConfig, env_field_name
from ..docker import DockerOrchestrator
from ..state import StateManager
from ..utils import get_system_info, is_docker_available, is_docker_compose_available


class SetupService:
    """Operations used by the web UI.

    The service holds a mutable :class:`HermesConfig` instance that reflects
    the latest values loaded from (or saved to) the encrypted config file.
    """

    def __init__(self, config: HermesConfig | None = None) -> None:
        self.config = config or HermesConfig()
        self.orchestrator = DockerOrchestrator(self.config)

    # ------------------------------------------------------------------
    # Config passthrough
    # ------------------------------------------------------------------

    def apply_config(self, values: dict[str, Any]) -> None:
        """Apply a flat dict of values onto the current config.

        Keys may be either config field names (``docker_image``) or the
        canonical env var names (``HERMES_DOCKER_IMAGE``) — the web UI uses
        field names, the CLI and .env use env var names.
        """
        for field_name in self.config.model_fields:
            env_key = env_field_name(field_name)
            if field_name in values:
                raw = values[field_name]
            elif env_key in values:
                raw = values[env_key]
            else:
                continue
            setattr(self.config, field_name, self._coerce(field_name, raw))

        # Recreate orchestrator with updated config
        self.orchestrator = DockerOrchestrator(self.config)

    @staticmethod
    def _coerce(field_name: str, raw: Any) -> Any:
        """Coerce a raw form value to the type the config field expects."""
        field = HermesConfig.model_fields[field_name]
        annotation = field.annotation

        if raw is None or raw == "":
            return None

        if annotation is bool:
            if isinstance(raw, bool):
                return raw
            return str(raw).strip().lower() in {"1", "true", "yes", "on"}

        if annotation is int:
            return int(str(raw).strip())

        if annotation is float:
            return float(str(raw).strip())

        return raw

    def config_to_dict(self) -> dict[str, Any]:
        """Export the current config as a flat dict keyed by env var."""
        from .config_manager import EncryptedConfigManager

        return EncryptedConfigManager.config_to_dict(self.config)

    # ------------------------------------------------------------------
    # System / environment
    # ------------------------------------------------------------------

    def docker_status(self) -> dict[str, Any]:
        """Return Docker daemon and compose availability."""
        return {
            "available": is_docker_available(),
            "compose_available": is_docker_compose_available(),
            "issues": self.orchestrator.validate_environment(),
        }

    def system_info(self) -> dict[str, Any]:
        """Return basic system information."""
        return get_system_info()

    # ------------------------------------------------------------------
    # Project scaffolding
    # ------------------------------------------------------------------

    def init_project(self) -> dict[str, Any]:
        """Generate all scaffold files (compose, templates, hooks, etc.)."""
        self.orchestrator.init_project()
        self.config.ensure_directories()
        return {
            "ok": True,
            "generated": [
                str(self.orchestrator.compose_file),
                str(self.orchestrator.compose_prod_file),
                ".env.example",
                ".gitignore",
                ".pre-commit-config.yaml",
                ".gitleaks.toml",
            ],
        }

    # ------------------------------------------------------------------
    # Docker lifecycle
    # ------------------------------------------------------------------

    def start(self, production: bool = False) -> dict[str, Any]:
        ok = self.orchestrator.start(production=production)
        return {"ok": ok, "message": "Started" if ok else "Start failed"}

    def stop(self, production: bool = False, volumes: bool = False) -> dict[str, Any]:
        ok = self.orchestrator.stop(production=production, volumes=volumes)
        return {"ok": ok, "message": "Stopped" if ok else "Stop failed"}

    def restart(self, production: bool = False) -> dict[str, Any]:
        ok = self.orchestrator.restart(production=production)
        return {"ok": ok, "message": "Restarted" if ok else "Restart failed"}

    # ------------------------------------------------------------------
    # Streaming variants (used by background jobs)
    # ------------------------------------------------------------------

    def start_streaming(
        self, production: bool = False, on_line: Callable[[str], None] | None = None
    ) -> bool:
        """Start the containers, streaming compose output to *on_line*."""
        self.ensure_compose_files(on_line)
        ok, _ = self.orchestrator.stream_compose(
            ["up", "-d"], production=production, on_line=on_line
        )
        return ok

    def ensure_compose_files(self, on_line: Callable[[str], None] | None = None) -> None:
        """Write the compose files if they are missing or out of date.

        The web UI is the only supported setup path, so starting the agent
        must not fail just because the user has not run ``init`` yet.
        """
        compose_file = self.orchestrator.compose_file
        prod_file = self.orchestrator.compose_prod_file
        if compose_file.exists() and prod_file.exists():
            return

        if on_line:
            on_line("Compose files missing — generating them from the current config...")
        self.orchestrator.write_compose_files()
        if on_line:
            on_line(f"Wrote {compose_file}")

    def stop_streaming(
        self,
        production: bool = False,
        volumes: bool = False,
        on_line: Callable[[str], None] | None = None,
    ) -> bool:
        """Stop the containers, streaming compose output to *on_line*."""
        args = ["down"]
        if volumes:
            args.append("-v")
        ok, _ = self.orchestrator.stream_compose(args, production=production, on_line=on_line)
        return ok

    def restart_streaming(
        self, production: bool = False, on_line: Callable[[str], None] | None = None
    ) -> bool:
        """Restart the containers, streaming compose output to *on_line*."""
        self.stop_streaming(production=production, on_line=on_line)
        return self.start_streaming(production=production, on_line=on_line)

    def status(self) -> dict[str, Any]:
        return self.orchestrator.status()

    def logs(self, production: bool = False, tail: int = 200) -> str:
        return self.orchestrator.logs(production=production, follow=False, tail=tail)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def backup_state(self, reason: str = "manual") -> dict[str, Any]:
        sm = StateManager(self.config)
        path = sm.backup_state(reason)
        return {"ok": True, "path": str(path)}

    def restore_backup(self) -> dict[str, Any]:
        sm = StateManager(self.config)
        ok = sm.restore_backup()
        return {"ok": ok, "message": "Restored" if ok else "No backup found"}

    def state_report(self) -> str:
        sm = StateManager(self.config)
        return sm.generate_state_restore_report()

    def persistent_paths(self) -> dict[str, str]:
        sm = StateManager(self.config)
        return {k: str(v) for k, v in sm.get_persistent_state_paths().items()}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------


# Small utility functions kept local to avoid circular imports
def is_port_in_use(port: int, host: str = "localhost") -> bool:
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            return sock.connect_ex((host, port)) == 0
    except OSError:
        return False


def find_available_port(start_port: int = 8000) -> int | None:
    for port in range(start_port, start_port + 100):
        if not is_port_in_use(port):
            return port
    return None


def run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True)
