"""Configuration management for Hermes agent setup using Pydantic Settings."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class HermesConfig(BaseSettings):
    """Configuration for Hermes agent deployment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Docker settings
    docker_image: str = Field(
        default="nousresearch/hermes:latest",
        description="Docker image for Hermes agent",
    )
    docker_compose_file: str = Field(
        default="docker/compose.yml",
        description="Path to Docker Compose file",
    )
    docker_compose_prod_file: str = Field(
        default="docker/compose.prod.yml",
        description="Path to production Docker Compose file",
    )

    # Network settings
    host_port: int = Field(
        default=8000,
        description="Host port to bind Hermes agent",
        ge=1,
        le=65535,
    )
    container_port: int = Field(
        default=8000,
        description="Container port for Hermes agent",
        ge=1,
        le=65535,
    )

    # Resource limits
    memory_limit: str = Field(
        default="4g",
        description="Memory limit for container (e.g., '4g', '2048m')",
    )
    cpus_limit: float = Field(
        default=2.0,
        description="CPU limit for container",
        gt=0,
        le=128,
    )

    # Persistent storage
    data_dir: str = Field(
        default="./data",
        description="Host directory for persistent data",
    )
    models_dir: str = Field(
        default="./models",
        description="Host directory for model files",
    )

    # Hermes agent settings
    model_name: str = Field(
        default="NousResearch/Hermes-3-Llama-3.1-8B",
        description="HuggingFace model name or path",
    )
    context_size: int = Field(
        default=8192,
        description="Context window size",
        ge=512,
        le=32768,
    )
    temperature: float = Field(
        default=0.7,
        description="Sampling temperature",
        ge=0.0,
        le=2.0,
    )
    top_p: float = Field(
        default=0.9,
        description="Top-p sampling parameter",
        ge=0.0,
        le=1.0,
    )
    max_tokens: int = Field(
        default=2048,
        description="Maximum tokens to generate",
        ge=1,
        le=8192,
    )

    # Optional API keys (loaded from environment)
    hf_token: Optional[str] = Field(
        default=None,
        description="HuggingFace token for private models",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key (if using OpenAI models)",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR)",
    )
    log_file: Optional[str] = Field(
        default=None,
        description="Optional log file path",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper

    @field_validator("data_dir", "models_dir")
    @classmethod
    def expand_paths(cls, v: str) -> str:
        return str(Path(v).expanduser().resolve())

    def get_data_path(self) -> Path:
        """Get resolved data directory path."""
        return Path(self.data_dir).expanduser().resolve()

    def get_models_path(self) -> Path:
        """Get resolved models directory path."""
        return Path(self.models_dir).expanduser().resolve()

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.get_data_path().mkdir(parents=True, exist_ok=True)
        self.get_models_path().mkdir(parents=True, exist_ok=True)


def load_config() -> HermesConfig:
    """Load configuration from environment and .env file."""
    return HermesConfig()


def get_default_env_template() -> str:
    """Generate default .env.example template content."""
    return """# Hermes Agent Configuration
# Copy this file to .env and fill in your values
# NEVER commit .env to version control!

# Docker Settings
HERMES_DOCKER_IMAGE=nousresearch/hermes:latest
HERMES_DOCKER_COMPOSE_FILE=docker/compose.yml
HERMES_DOCKER_COMPOSE_PROD_FILE=docker/compose.prod.yml

# Network Settings
HERMES_HOST_PORT=8000
HERMES_CONTAINER_PORT=8000

# Resource Limits
HERMES_MEMORY_LIMIT=4g
HERMES_CPUS_LIMIT=2.0

# Persistent Storage (will be created automatically)
HERMES_DATA_DIR=./data
HERMES_MODELS_DIR=./models

# Hermes Agent Settings
HERMES_MODEL_NAME=NousResearch/Hermes-3-Llama-3.1-8B
HERMES_CONTEXT_SIZE=8192
HERMES_TEMPERATURE=0.7
HERMES_TOP_P=0.9
HERMES_MAX_TOKENS=2048

# Optional: API Keys (uncomment and set if needed)
# HERMES_HF_TOKEN=your_huggingface_token_here
# HERMES_OPENAI_API_KEY=your_openai_key_here

# Logging
HERMES_LOG_LEVEL=INFO
# HERMES_LOG_FILE=./logs/hermes.log
"""