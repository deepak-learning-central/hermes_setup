"""Secrets management for Hermes agent setup.

Provides secure handling and validation of environment variables
containing sensitive information.
"""

import re
from pathlib import Path
from typing import Any

from .config import HermesConfig


class SecretsManager:
    """Manages secrets for Hermes agent setup."""

    def __init__(self, config: HermesConfig | None = None):
        self.config = config or HermesConfig()
        self.project_root = Path.cwd()

    def validate_env_value(self, key: str, value: str) -> tuple[bool, str | None]:
        """Validate an environment variable value for secrets."""
        # Check for common secret patterns in values
        secret_patterns = [
            # Hardcoded API keys - very long strings
            (
                r".{200,}",
                f"Value for {key} is very long ({len(value)} chars), might contain embedded secrets",
            ),
            # Common placeholder values
            (r"^(sk_live|sk_test|pk_live|pk_test)", f"Testing/production API key detected in {key}"),
            # Base64 encoded values that look suspicious
            (r"^[A-Za-z0-9+/]{40,}={0,2}$", f"Base64-encoded value in {key}"),
        ]

        for pattern, message in secret_patterns:
            if re.match(pattern, value):
                return False, message

        # Check if value looks like a reasonable config value
        if value in {"placeholder", "TODO", "FILL_ME_IN", "CHANGE_ME", ""}:
            return False, f"Placeholder value detected in {key}"

        return True, None

    def detect_secrets(self, content: str) -> list[dict[str, Any]]:
        """Detect potential secrets in file content."""
        findings: list[dict[str, Any]] = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Skip known safe patterns
            if "=" in stripped:
                key, _, val = stripped.partition("=")
                key = key.strip()
                val = val.strip()

                # Skip common non-secret keys
                non_secret_keys = {
                    "HERMES_",
                    "MODEL_",
                    "CONTEXT_",
                    "TEMPERATURE_",
                    "TOP_P_",
                    "MAX_TOKENS_",
                    "LOG_",
                    "DATA_",
                    "MODELS_",
                    "PORT_",
                    "HOST_",
                    "CONTAINER_",
                    "NETWORK_",
                    "VOLUME_",
                    "SERVICE_",
                    "VERSION_",
                    "IMAGE_",
                    "RESTART_",
                    "HEALTHCHECK_",
                }

                if any(key.startswith(prefix) for prefix in non_secret_keys):
                    continue

                # Check for potential secrets (long strings, base64, etc.)
                if len(val) > 100:
                    findings.append(
                        {
                            "line": i,
                            "key": key,
                            "value_length": len(val),
                            "issue": f"Potential secret value (length {len(val)}) for {key}",
                        }
                    )

        return findings

    def scan_directory(self, directory: Path | None = None) -> list[dict[str, Any]]:
        """Scan a directory for potential secret leaks."""
        target = directory or self.project_root
        findings: list[dict[str, Any]] = []

        if not target.exists():
            return findings

        for filepath in target.rglob("*"):
            if not filepath.is_file():
                continue

            # Skip known excluded files/directories
            excluded_extensions = {".pyc", ".pyo", ".git"}
            excluded_names = {".env", ".git", ".github", ".cache"}

            if filepath.suffix in excluded_extensions:
                continue
            if any(part in excluded_names for part in filepath.parts):
                continue

            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                file_findings = self.detect_secrets(content)
                for f in file_findings:
                    f["file"] = str(filepath.relative_to(self.project_root))
                    findings.append(f)
            except (PermissionError, UnicodeDecodeError):
                continue

        return findings

    def generate_env_template(self, path: Path | None = None) -> str:
        """Generate .env.example with proper guidance."""
        config = self.config

        template = f"""# Hermes Agent Environment Configuration
# Copy to .env and fill in your values
# Never commit .env to version control!

# ==========================================
# Docker Settings
# ==========================================
HERMES_DOCKER_IMAGE={config.docker_image}
HERMES_DOCKER_COMPOSE_FILE={config.docker_compose_file}
HERMES_DOCKER_COMPOSE_PROD_FILE={config.docker_compose_prod_file}

# ==========================================
# Network Configuration
# ==========================================
# Port to expose Hermes agent on host
HERMES_HOST_PORT={config.host_port}
# Port inside the container
HERMES_CONTAINER_PORT={config.container_port}

# ==========================================
# Resource Limits
# ==========================================
# Memory limit for container (K/M/G)
HERMES_MEMORY_LIMIT={config.memory_limit}
# CPU cores to allocate
HERMES_CPUS_LIMIT={config.cpus_limit}

# ==========================================
# Persistent Storage
# ==========================================
# Host directory for agent data
HERMES_DATA_DIR={config.data_dir}
# Host directory for model files
HERMES_MODELS_DIR={config.models_dir}

# ==========================================
# Hermes Agent Settings
# ==========================================
# HuggingFace model name or path
HERMES_MODEL_NAME={config.model_name}
# Context window size (tokens)
HERMES_CONTEXT_SIZE={config.context_size}
# Sampling temperature (0.0 to 2.0)
HERMES_TEMPERATURE={config.temperature}
# Top-p sampling parameter
HERMES_TOP_P={config.top_p}
# Maximum tokens to generate
HERMES_MAX_TOKENS={config.max_tokens}

# ==========================================
# Optional API Keys
# ==========================================
# Uncomment and set if using private HuggingFace models
# HERMES_HF_TOKEN=your_hf_token_here

# Uncomment and set if using OpenAI models
# HERMES_OPENAI_API_KEY=your_openai_key_here

# ==========================================
# Logging Configuration
# ==========================================
HERMES_LOG_LEVEL={config.log_level}
# Optional: HERMES_LOG_FILE=./logs/hermes.log
"""

        if path:
            path.write_text(template)

        return template

    def generate_safe_env_example(self, path: Path | None = None) -> str:
        """Generate a .env.example with security warnings."""
        safe_example = """# !!! SECURITY WARNING !!!
# Never commit .env files containing real secrets to version control!
# This file is a template - replace placeholders with actual values only
# when running in a secure, isolated environment.

# Environment files must be listed in .gitignore
# Example: echo ".env" >> .gitignore

# ==========================================
# Configuration (OK to commit as template)
# ==========================================

# Docker image reference - safe to commit
HERMES_DOCKER_IMAGE=nousresearch/hermes:latest

# Port configuration - safe to commit
HERMES_HOST_PORT=8000
HERMES_CONTAINER_PORT=8000

# Resource limits - safe to commit
HERMES_MEMORY_LIMIT=4g
HERMES_CPUS_LIMIT=2.0

# Model name - safe to commit (public model)
HERMES_MODEL_NAME=NousResearch/Hermes-3-Llama-3.1-8B

# Agent settings - safe to commit
HERMES_CONTEXT_SIZE=8192
HERMES_TEMPERATURE=0.7
HERMES_TOP_P=0.9
HERMES_MAX_TOKENS=2048

# ==========================================
# Secrets - DO NOT fill in .env file!
# ==========================================
# These must be provided at runtime via:
# - Docker secrets (Swarm/Kubernetes)
# - GitHub Actions Secrets
# - 1Password/Doppler/SOPS at deployment time
# - Environment variable injection by orchestrator

# HERMES_HF_TOKEN=your_hf_token_here  # <-- DELETE or COMMENT OUT
# HERMES_OPENAI_API_KEY=your_openai_key_here  # <-- DELETE or COMMENT OUT

# ==========================================
# Logging
# ==========================================
HERMES_LOG_LEVEL=INFO

# ==========================================
# Generated: DO NOT EDIT directly
# Use: uv run hermes-setup generate:env-template
# ==========================================
"""

        if path:
            path.write_text(safe_example)

        return safe_example

    @staticmethod
    def create_baseline() -> dict[str, Any]:
        """Create a secrets baseline file for detect-secrets."""
        baseline: dict[str, Any] = {
            "version": 1,
            "default_excludes": True,
            "baseline": [],
        }
        return baseline
