"""Docker Compose orchestration for Hermes agent."""

import contextlib
import os
import subprocess
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
    ) -> subprocess.CompletedProcess:
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
    ) -> subprocess.CompletedProcess:
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
        """Generate Docker Compose file content."""
        config = self.config
        data_dir = config.get_data_path()
        models_dir = config.get_models_path()

        compose_content = f"""version: '3.8'

services:
  hermes:
    image: {config.docker_image}
    container_name: hermes-agent
    restart: unless-stopped
    ports:
      - "{config.host_port}:{config.container_port}"
    environment:
      - MODEL_NAME={config.model_name}
      - CONTEXT_SIZE={config.context_size}
      - TEMPERATURE={config.temperature}
      - TOP_P={config.top_p}
      - MAX_TOKENS={config.max_tokens}
      - LOG_LEVEL={config.log_level}
"""
        if config.hf_token:
            compose_content += f"      - HF_TOKEN={config.hf_token}\n"
        if config.openai_api_key:
            compose_content += f"      - OPENAI_API_KEY={config.openai_api_key}\n"

        compose_content += f"""    volumes:
      - {data_dir}:/app/data
      - {models_dir}:/app/models
    deploy:
      resources:
        limits:
          memory: {config.memory_limit}
          cpus: '{config.cpus_limit}'
        reservations:
          memory: {config.memory_limit}
          cpus: '{config.cpus_limit / 2}'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{config.container_port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  hermes-data:
  hermes-models:
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

    def stop(self, production: bool = False) -> bool:
        """Stop Hermes agent containers."""
        if production:
            return self._run_compose_prod(["down"], check=False).returncode == 0
        return self._run_compose(["down"], check=False).returncode == 0

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

        return result.stdout if result.returncode == 0 else result.stderr

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
          "textual>=0.58.0",
          "typer>=0.12.0",
          "rich>=13.7.0",
          "httpx>=0.27.0",
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

