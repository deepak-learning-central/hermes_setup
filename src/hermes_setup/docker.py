"""Docker Compose orchestration for Hermes agent."""

import contextlib
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .config import HermesConfig, get_default_env_template


class DockerOrchestrator:
    """Manages Docker Compose operations for Hermes agent."""

    def __init__(self, config: HermesConfig | None = None):
        self.config = config or HermesConfig()
        self.project_root = Path.cwd()
        self.compose_file = self.project_root / self.config.docker_compose_file
        self.compose_prod_file = self.project_root / self.config.docker_compose_prod_file

    def _run_compose(
        self,
        args: list[str],
        env: dict[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run docker compose command with proper environment."""
        cmd = ["docker", "compose", "-f", str(self.compose_file)] + args
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(cmd, env=merged_env, check=check, capture_output=True, text=True)

    def _run_compose_prod(
        self,
        args: list[str],
        env: dict[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run docker compose with production file."""
        cmd = ["docker", "compose", "-f", str(self.compose_prod_file)] + args
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(cmd, env=merged_env, check=check, capture_output=True, text=True)

    def check_docker(self) -> bool:
        """Check if Docker is available and running."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def check_compose(self) -> bool:
        """Check if Docker Compose is available."""
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def validate_environment(self) -> list[str]:
        """Validate Docker environment and return list of issues."""
        issues = []
        if not self.check_docker():
            issues.append("Docker is not running or not installed")
        if not self.check_compose():
            issues.append("Docker Compose is not available")
        if not self.compose_file.exists():
            issues.append(f"Compose file not found: {self.compose_file}")
        return issues

    def generate_compose_file(self, production: bool = False) -> str:
        """Generate Docker Compose file content.

        The compose file runs the official ``nousresearch/hermes-agent`` image
        in gateway mode.  The agent keeps all of its state in ``/opt/data``,
        backed by a named volume so SQLite's WAL mode stays coherent.
        """
        config = self.config
        image = config.docker_image
        if production and image.endswith(":latest"):
            image = image.replace(":latest", ":stable")
        dashboard = "1" if config.enable_dashboard else "0"

        api_key = config.api_server_key or ""
        if production and not api_key:
            # Fail fast rather than silently serving an unauthenticated API.
            api_key = "${API_SERVER_KEY:?API_SERVER_KEY is required in production}"

        compose_content = f"""services:
  hermes:
    image: {image}
    container_name: hermes
    restart: unless-stopped
    command: ["gateway", "run"]
    ports:
      - "{config.api_port}:8642"
      - "{config.dashboard_port}:9119"
    environment:
      - HERMES_UID=${{HERMES_UID:-1000}}
      - HERMES_GID=${{HERMES_GID:-1000}}
      - API_PROVIDER={config.api_provider}
      - HERMES_MODEL={config.model_name}
      - HF_TOKEN={config.hf_token or ""}
      - OPENAI_API_KEY={config.openai_api_key or ""}
      - OPENAI_BASE_URL={config.openai_base_url or ""}
      - OLLAMA_BASE_URL={config.ollama_host or ""}
      - TELEGRAM_BOT_TOKEN={config.telegram_bot_token or ""}
      - DISCORD_BOT_TOKEN={config.discord_bot_token or ""}
      - SLACK_BOT_TOKEN={config.slack_bot_token or ""}
      - SLACK_APP_TOKEN={config.slack_app_token or ""}
      - API_SERVER_ENABLED=true
      - API_SERVER_HOST=0.0.0.0
      - API_SERVER_KEY={api_key}
      - HERMES_DASHBOARD={dashboard}
      - HERMES_DASHBOARD_HOST=127.0.0.1
    volumes:
      - hermes-data:/opt/data
    deploy:
      resources:
        limits:
          memory: {config.memory_limit}
          cpus: '{config.cpus_limit}'
        reservations:
          memory: 1g
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8642/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s

volumes:
  hermes-data:
"""
        if production:
            compose_content += """
networks:
  default:
    name: hermes-network
    external: false
"""
        return compose_content

    def write_compose_files(self) -> None:
        """Write both development and production compose files."""
        self.compose_file.parent.mkdir(parents=True, exist_ok=True)

        dev_content = self.generate_compose_file(production=False)
        self.compose_file.write_text(dev_content)

        prod_content = self.generate_compose_file(production=True)
        self.compose_prod_file.write_text(prod_content)

    def pull_image(self) -> bool:
        """Pull the latest Hermes Docker image."""
        try:
            result = subprocess.run(
                ["docker", "pull", self.config.docker_image],
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False

    def start(self, production: bool = False, detach: bool = True) -> bool:
        """Start Hermes agent containers."""
        args = ["up"]
        if detach:
            args.append("-d")
        if production:
            return self._run_compose_prod(args, check=False).returncode == 0
        return self._run_compose(args, check=False).returncode == 0

    def stream_compose(
        self,
        args: list[str],
        production: bool = False,
        on_line: Callable[[str], None] | None = None,
        timeout: float | None = 1800,
    ) -> tuple[bool, str]:
        """Run a compose command, streaming its output line by line.

        Returns a ``(ok, output)`` tuple.  *on_line* is called for each line of
        combined stdout/stderr so the caller can surface live progress.
        """
        cmd = [
            "docker",
            "compose",
            "-f",
            str(self.compose_file if not production else self.compose_prod_file),
        ]
        cmd += args
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=os.environ.copy(),
            )
        except (OSError, FileNotFoundError) as exc:
            message = f"Failed to launch docker compose: {exc}"
            if on_line:
                on_line(message)
            return False, message

        lines: list[str] = []
        assert proc.stdout is not None
        try:
            for raw in proc.stdout:
                line = raw.rstrip("\n")
                lines.append(line)
                if on_line:
                    on_line(line)
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            message = "docker compose timed out"
            lines.append(message)
            if on_line:
                on_line(message)
            return False, "\n".join(lines)
        except Exception:
            proc.kill()
            raise

        return proc.returncode == 0, "\n".join(lines)

    def stop(self, production: bool = False, volumes: bool = False) -> bool:
        """Stop Hermes agent containers."""
        args = ["down"]
        if volumes:
            args.append("-v")
        if production:
            return self._run_compose_prod(args, check=False).returncode == 0
        return self._run_compose(args, check=False).returncode == 0

    def restart(self, production: bool = False) -> bool:
        """Restart Hermes agent containers."""
        self.stop(production)
        return self.start(production)

    def status(self, production: bool = False) -> dict[str, Any]:
        """Get container status."""
        args = ["ps", "--format", "json"]
        if production:
            result = self._run_compose_prod(args, check=False)
        else:
            result = self._run_compose(args, check=False)

        if result.returncode != 0:
            return {"running": False, "containers": []}

        import json

        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                with contextlib.suppress(json.JSONDecodeError):
                    containers.append(json.loads(line))

        running = any(c.get("State") == "running" for c in containers)
        return {"running": running, "containers": containers}

    def logs(self, production: bool = False, follow: bool = False, tail: int = 100) -> str:
        """Get container logs."""
        args = ["logs", "--tail", str(tail)]
        if follow:
            args.append("-f")
        if production:
            result = self._run_compose_prod(args, check=False)
        else:
            result = self._run_compose(args, check=False)

        return result.stdout or "" if result.returncode == 0 else result.stderr or ""

    def update(self, production: bool = False) -> bool:
        """Update Hermes agent to latest image."""
        if not self.pull_image():
            return False
        return self.restart(production)

    def zero_downtime_deploy(self, production: bool = False) -> bool:
        """Perform zero-downtime deployment using rolling update strategy."""
        if not self.pull_image():
            return False

        # For Docker Compose, we use the built-in rolling update
        # This requires the service to have healthcheck configured
        args = ["up", "-d", "--force-recreate", "--no-deps"]
        if production:
            result = self._run_compose_prod(args, check=False)
        else:
            result = self._run_compose(args, check=False)

        if result.returncode != 0:
            return False

        # Wait for health check to pass
        import time

        for _ in range(30):
            status = self.status(production)
            if status["running"]:
                all_healthy = all(
                    c.get("Health") == "healthy"
                    for c in status["containers"]
                    if c.get("Service") == "hermes"
                )
                if all_healthy:
                    return True
            time.sleep(2)

        return False

    def rollback(self, production: bool = False) -> bool:
        """Rollback to previous image (requires image tagging strategy)."""
        # This is a simplified rollback - in production you'd tag images
        # and revert to previous tag
        args = ["up", "-d", "--force-recreate", "--no-deps"]
        if production:
            result = self._run_compose_prod(args, check=False)
        else:
            result = self._run_compose(args, check=False)
        return result.returncode == 0

    def cleanup(self, production: bool = False, volumes: bool = False) -> bool:
        """Clean up containers and optionally volumes."""
        args = ["down", "--remove-orphans"]
        if volumes:
            args.append("-v")
        if production:
            return self._run_compose_prod(args, check=False).returncode == 0
        return self._run_compose(args, check=False).returncode == 0

    def generate_env_example(self, path: Path | None = None) -> None:
        """Generate .env.example file."""
        target = path or (self.project_root / ".env.example")
        target.write_text(get_default_env_template())

    def generate_gitignore(self, path: Path | None = None) -> None:
        """Generate .gitignore file."""
        target = path or (self.project_root / ".gitignore")
        content = """# Hermes Setup - Git Ignore Rules

# Environment files - NEVER commit these!
.env
.env.*
*.env
*.env.local
*.env.production

# Secrets and credentials
*secret*
*credential*
*password*
*token*
*key*.pem
*key*.key

# Data directories
data/
models/
logs/
*.log

# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/
uv.lock

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
.docker/

# Backup files
*.bak
*.backup
*~
"""
        target.write_text(content)

    def generate_pre_commit_config(self, path: Path | None = None) -> None:
        """Generate .pre-commit-config.yaml for secret detection."""
        target = path or (self.project_root / ".pre-commit-config.yaml")
        content = """# Pre-commit hooks for Hermes Setup
# Install with: pre-commit install
# Run manually: pre-commit run --all-files

repos:
  # Basic file checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-merge-conflict
      - id: debug-logger
      - id: detect-private-key
      - id: check-added-large-files
        args: ["--maxkb=500"]

  # Secret detection - Gitleaks
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
        args: ["--verbose", "--config=.gitleaks.toml"]

  # Secret detection - Detect-Secrets
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]
        exclude: "^.secrets.baseline$"

  # Python formatting - Ruff
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format

  # Type checking - MyPy
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        additional_dependencies: [
          "pydantic>=2.6.0",
          "pydantic-settings>=2.2.0",
          "typer>=0.12.0",
          "rich>=13.7.0",
          "httpx>=0.27.0",
          "fastapi>=0.150.0",
          "cryptography>=50.0.2",
        ]

  # Security - Bandit
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.9
    hooks:
      - id: bandit
        args: ["-r", "src", "-ll", "-f", "json", "-o", "bandit-report.json"]

  # Dependency checking - Safety
  - repo: https://github.com/pyupio/safety
    rev: 3.1.0
    hooks:
      - id: safety
        args: ["--json", "--output", "safety-report.json"]
        verbose: true
"""
        target.write_text(content)

    def generate_gitleaks_config(self, path: Path | None = None) -> None:
        """Generate .gitleaks.toml configuration."""
        target = path or (self.project_root / ".gitleaks.toml")
        content = """# Gitleaks configuration for Hermes Setup
# https://github.com/gitleaks/gitleaks

[allowlist]
description = "Allowlisted patterns for Hermes Setup"
paths = [
    "(?i).*\\.example$",
    "(?i).*\\.template$",
    "(?i)README\\.md$",
    "(?i)CHANGELOG\\.md$",
    "(?i)LICENSE$",
    "(?i)\\.gitleaks\\.toml$",
    "(?i)\\.secrets\\.baseline$",
    "(?i)test.*\\.py$",
]

# Common patterns that are false positives
regexes = [
    # UUIDs that look like API keys but aren't
    "example_[a-f0-9]{32}",
    "test_[a-f0-9]{32}",
    "dummy_[a-f0-9]{32}",
    "placeholder_[a-f0-9]{32}",
]
"""
        target.write_text(content)

    def init_project(self) -> None:
        """Initialize project with all generated files."""
        self.write_compose_files()
        self.generate_env_example()
        self.generate_gitignore()
        self.generate_pre_commit_config()
        self.generate_gitleaks_config()
        self.config.ensure_directories()
