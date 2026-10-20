"""Configuration management for Hermes agent setup using Pydantic Settings."""

from pathlib import Path

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
        default="nousresearch/hermes-agent:latest",
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
    hf_token: str | None = Field(
        default=None,
        description="HuggingFace token for private models or HF Inference API",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key (if using OpenAI-compatible API)",
    )
    openai_base_url: str | None = Field(
        default=None,
        description=("Optional OpenAI-compatible base URL (e.g. custom endpoint)"),
    )
    ollama_host: str | None = Field(
        default=None,
        description=("Ollama server host (e.g. http://host.docker.internal:11434)"),
    )
    api_provider: str = Field(
        default="huggingface",
        description="API provider: huggingface | openai | ollama",
    )

    # Channel integrations
    telegram_bot_token: str | None = Field(
        default=None,
        description="Telegram bot token (from @BotFather)",
    )
    discord_bot_token: str | None = Field(
        default=None,
        description="Discord bot token (from Discord Developer Portal)",
    )
    slack_bot_token: str | None = Field(
        default=None,
        description="Slack bot token (xoxb-...)",
    )
    slack_app_token: str | None = Field(
        default=None,
        description="Slack app token (xapp-1-...)",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR)",
    )
    log_file: str | None = Field(
        default=None,
        description="Optional log file path",
    )

    @staticmethod
    def get_default_env_template() -> str:
        """Generate default .env.example template content."""
        return """# Hermes Agent Configuration
# Copy this file to .env and fill in your values
# NEVER commit .env to version control!

# ==========================================
# MODE: Local Model vs API Provider
# ==========================================
# By default, runs a local HuggingFace model (requires model download).
# For API mode (no local model, uses remote provider), set API_PROVIDER
# and provide the corresponding API key below.
#
# API_PROVIDER options:
#   - huggingface  (default, uses HF Inference API or local model)
#   - openai       (uses OpenAI-compatible API)
#   - ollama       (local Ollama server)

API_PROVIDER=huggingface

# ==========================================
# Docker Settings
# ==========================================
HERMES_DOCKER_IMAGE=nousresearch/hermes-agent:latest
HERMES_DOCKER_COMPOSE_FILE=docker/compose.yml
HERMES_DOCKER_COMPOSE_PROD_FILE=docker/compose.prod.yml

# ==========================================
# Network Settings
# ==========================================
HERMES_HOST_PORT=8000
HERMES_CONTAINER_PORT=8000

# ==========================================
# Resource Limits
# ==========================================
HERMES_MEMORY_LIMIT=4g
HERMES_CPUS_LIMIT=2.0

# ==========================================
# Persistent Storage (will be created automatically)
# ==========================================
HERMES_DATA_DIR=./data
HERMES_MODELS_DIR=./models

# ==========================================
# Hermes Agent Settings
# ==========================================
# For LOCAL model mode (downloads model):
HERMES_MODEL_NAME=NousResearch/Hermes-3-Llama-3.1-8B
HERMES_CONTEXT_SIZE=8192
HERMES_TEMPERATURE=0.7
HERMES_TOP_P=0.9
HERMES_MAX_TOKENS=2048

# ==========================================
# Optional API Keys - REQUIRED for API mode
# ==========================================
# Uncomment and set ONE of these based on API_PROVIDER:
#
# For HuggingFace Inference API (API_PROVIDER=huggingface):
# HERMES_HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxx
#
# For OpenAI-compatible API (API_PROVIDER=openai):
# HERMES_OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
# HERMES_OPENAI_BASE_URL=https://api.openai.com/v1  # optional, for custom endpoints

# For Ollama (API_PROVIDER=ollama):
# HERMES_OLLAMA_HOST=http://host.docker.internal:11434  # default

# ==========================================
# Channel Integrations (uncomment and set if needed)
# ==========================================
# Get tokens from:
#   Telegram: @BotFather → /newbot
#   Discord:  https://discord.com/developers/applications → Bot
#   Slack:    https://api.slack.com/apps → Bot
#
# TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
# DISCORD_BOT_TOKEN=your_discord_bot_token_here
# SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
# SLACK_APP_TOKEN=xapp-1-your-slack-app-token

# ==========================================
# Logging
# ==========================================
HERMES_LOG_LEVEL=INFO
# HERMES_LOG_FILE=./logs/hermes.log
"""

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
