"""High-level service that wraps the existing Docker orchestrator and config.

This module isolates the web backend from direct imports of legacy modules
while reusing 100% of the existing functionality (Docker, config, state).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
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
        """Apply a flat dict of env-var values onto the current config."""
        for field_name in self.config.model_fields:
            env_key = env_field_name(field_name)
            if env_key in values:
                setattr(self.config, field_name, values[env_key])
        # Recreate orchestrator with updated config
        self.orchestrator = DockerOrchestrator(self.config)

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