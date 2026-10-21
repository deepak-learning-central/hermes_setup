"""High-level service that wraps the existing Docker orchestrator and config.

This module isolates the web backend from direct imports of legacy modules
while reusing 100% of the existing functionality (Docker, config, state).
"""

from __future__ import annotations

import json
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
        self.config = config or HermesConfig(
            docker_compose_file=".hermes-runtime/compose.yml",
            docker_compose_prod_file=".hermes-runtime/compose.prod.yml",
        )
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
        from .config_manager import EncryptedConfigManager

        merged = EncryptedConfigManager.config_to_dict(self.config)
        for field_name in type(self.config).model_fields:
            env_key = env_field_name(field_name)
            if field_name in values or env_key in values:
                merged[field_name] = values.get(field_name, values.get(env_key))
        # Validate a complete candidate before replacing the live configuration.
        self.config = EncryptedConfigManager.dict_to_config(merged)
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

    def setup_streaming(self, on_line: Callable[[str], None]) -> bool:
        """Deploy on a Linux Pi, then verify HTTP readiness and model access."""
        import platform
        import time

        import httpx

        if platform.system() != "Linux" or platform.machine() not in {
            "aarch64",
            "arm64",
            "x86_64",
            "AMD64",
        }:
            raise ValueError("Run setup on 64-bit Linux on the target Pi (not this computer).")
        cfg = self.config
        if cfg.dashboard_port != 9119:
            raise ValueError("The Pi dashboard uses port 9119. Keep the default dashboard port.")
        if not self.orchestrator.check_docker() or not self.orchestrator.check_compose():
            raise ValueError(
                "Docker Engine and the Compose plugin must be installed and accessible to your user. See README.md."
            )
        on_line("1/5 Writing deployment configuration")
        self.orchestrator.write_compose_files()
        on_line(
            "2/5 Pulling Hermes image for this machine (first download can take several minutes)"
        )
        ok, _ = self.orchestrator.stream_compose(["pull"], on_line=on_line)
        if not ok:
            return False
        on_line("3/5 Configuring the model and messaging channel environment")
        runtime = {
            "model": {
                "default": cfg.model_name,
                "provider": "custom",
                "base_url": cfg.openai_base_url,
            },
            "terminal": {"backend": "local"},
        }
        # Update only the keys this wizard owns; preserve other Hermes settings.
        script = (
            "import json,pathlib; import hermes_yaml as yaml; "
            "p=pathlib.Path('/opt/data/config.yaml'); "
            "c=yaml.safe_load(p.read_text()) if p.exists() else {}; c=c or {}; "
            f"v=json.loads({json.dumps(json.dumps(runtime))}); "
            "c.update(v); p.write_text(yaml.safe_dump(c)); "
            "p.chmod(0o600)"
        )
        ok, _ = self.orchestrator.stream_compose(
            [
                "run",
                "--rm",
                "--no-deps",
                "-e",
                "HERMES_DASHBOARD=0",
                "hermes",
                "python",
                "-c",
                script,
            ],
            on_line=on_line,
        )
        if not ok:
            return False
        on_line("4/5 Starting Hermes and waiting for its API and dashboard")
        ok, _ = self.orchestrator.stream_compose(["up", "-d", "--force-recreate"], on_line=on_line)
        if not ok:
            return False
        for _ in range(90):
            health = self.agent_health()
            if health["ok"] and (not cfg.enable_dashboard or health["dashboard"]["reachable"]):
                break
            time.sleep(2)
        else:
            on_line("Hermes did not become ready. Inspect container logs, then retry setup.")
            return False
        on_line("5/5 Checking a real assistant response (uses a small number of provider tokens)")
        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(
                    f"http://127.0.0.1:{cfg.api_port}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {cfg.api_server_key}"},
                    json={
                        "model": cfg.model_name,
                        "messages": [{"role": "user", "content": "Reply only with: Ready"}],
                        "max_tokens": 16,
                    },
                )
                response.raise_for_status()
                if not response.json().get("choices"):
                    raise ValueError("No assistant response returned")
        except (httpx.HTTPError, ValueError):
            on_line(
                "Model check failed. Verify the provider URL, model name, API key and account balance, then retry."
            )
            return False
        on_line(
            "Hermes is ready. Open the assistant dashboard at http://localhost:9119 through your SSH tunnel."
        )
        return True

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
    # Agent health (probes running endpoints from the host)
    # ------------------------------------------------------------------

    @staticmethod
    def _probe(host: str, port: int, path: str = "/", timeout: float = 3.0) -> dict[str, Any]:
        """Probe one endpoint on ``host:port`` and report reachability + status."""
        import urllib.error
        import urllib.request

        url = f"http://{host}:{port}{path}"
        info: dict[str, Any] = {"url": url, "reachable": False, "status": None, "body": ""}
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                info["reachable"] = True
                info["status"] = resp.getcode()
                info["body"] = resp.read().decode("utf-8", errors="replace")[:512]
        except urllib.error.HTTPError as exc:
            info["reachable"] = True
            info["status"] = exc.code
        except (urllib.error.URLError, ConnectionError, OSError):
            info["reachable"] = False
        except Exception:
            info["reachable"] = False
        return info

    def agent_health(self) -> dict[str, Any]:
        """Report whether the agent, its API server and dashboard are up.

        This is the definitive answer for the question "is Hermes running?".
        The container state comes straight from docker compose; the two HTTP
        probes confirm that the published ports actually respond.
        """
        cfg = self.config
        try:
            container = self.orchestrator.status()
        except Exception:
            container = {"running": False, "health": None, "containers": []}

        api_state = self._probe("127.0.0.1", cfg.api_port, path="/health", timeout=3.0)
        dashboard_state = self._probe("127.0.0.1", cfg.dashboard_port, path="/", timeout=3.0)

        version = None
        if api_state.get("reachable") and api_state.get("body"):
            try:
                version = json.loads(api_state["body"]).get("version")
            except (ValueError, AttributeError):
                version = None

        return {
            "ok": bool(
                container.get("running")
                and api_state.get("reachable")
                and api_state.get("status") == 200
            ),
            "container": {
                "running": container.get("running"),
                "health": container.get("health"),
                "status": container.get("Status"),
            },
            "api": {**api_state, "version": version},
            "dashboard": dashboard_state,
            "api_server_key_configured": bool(cfg.api_server_key),
        }

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
