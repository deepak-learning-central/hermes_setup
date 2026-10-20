# Hermes Setup

Portable, credential-free setup for deploying the [Hermes agent](https://hermes-agent.nousresearch.com/) (Nous Research personal assistant) using Docker and Python.

![Hermes Setup Demo](docs/demo.gif)

## Features

- **Docker-based deployment** - Runs the official `nousresearch/hermes-agent` image
- **Zero-credential repository** - No secrets in git history
- **Web-based UI configuration** - Browser-based setup with encrypted config storage
- **Live progress feedback** - Container operations run as background jobs with streaming output
- **State persistence** - Agent memory and configuration survive updates
- **Cross-platform** - Works on Linux, macOS, and WSL2

## Quick Start

### Prerequisites

- Docker Engine and Docker Compose
- Python 3.11+ with [uv](https://docs.astral.sh/uv/)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/hermes-setup.git
cd hermes-setup

# Install dependencies
uv sync

# Initialize project (creates config files)
hermes-setup init

# Launch the web setup UI
hermes-setup web
```

## Usage

### Web Setup UI

The web UI runs a local FastAPI backend on `http://127.0.0.1:8765` and serves a browser-based configuration page.

```bash
# Start the web server
hermes-setup web

# Custom host/port
hermes-setup web --host 0.0.0.0 --port 8765
```

**Capabilities:**

- **Configuration** — Set all Hermes agent values (image, API/dashboard ports, resource limits, model name, provider keys, channel tokens)
- **Encrypted persistence** — Configuration is saved to `.hermes-config.enc` on your local machine, encrypted with a passphrase you supply. This file is **never committed to the repository**
- **Docker control** — Start, stop, and restart the agent with live progress output; the operation runs as a background job so the browser stays responsive and you can see exactly what `docker compose` is doing
- **State management** — Create and restore backups of persistent state
- **Project init** — Generate compose files, `.env.example`, `.gitignore`, and security hooks

### What gets deployed

The compose files run the official upstream image, `nousresearch/hermes-agent`, in
gateway mode:

| Surface | Default port | Notes |
|---------|--------------|-------|
| OpenAI-compatible API server | `8642` | Requires an `API_SERVER_KEY` of at least 16 characters |
| Web dashboard | `9119` | Bound to loopback inside the container |

All agent state lives in a single Docker volume mounted at `/opt/data`. A named
volume (rather than a host bind mount) is used deliberately: SQLite's WAL mode
is not safe across a macOS/Windows Docker Desktop VM boundary and silently
corrupts the database.

> **Note on the API server key.** The agent refuses to expose its API server
> without a key of at least 16 characters. Generate one with
> `openssl rand -hex 32` and enter it in the Configuration tab. If you leave it
> blank, the agent generates a loopback-only key at first boot.

### CLI Commands

The CLI provides additional management commands for advanced users:

```bash
# Start the agent (requires .env file)
hermes-setup up

# Stop the agent
hermes-setup down

# Restart the agent
hermes-setup restart

# View logs
hermes-setup logs --follow

# Update to latest version
hermes-setup update

# Show configuration
hermes-setup config

# Create state backup
hermes-setup backup

# Restore from backup
hermes-setup restore

# Run diagnostics
hermes-setup diagnose

# Generate .env.example template
hermes-setup generate:env-template
```

## Configuration

Configuration is managed through the web UI and persisted to an encrypted file
on this machine. The values map to these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `HERMES_DOCKER_IMAGE` | Docker image to use | `nousresearch/hermes-agent:latest` |
| `HERMES_API_PORT` | Host port for the agent's API server | `8642` |
| `HERMES_DASHBOARD_PORT` | Host port for the agent's web dashboard | `9119` |
| `HERMES_DASHBOARD` | Run the web dashboard alongside the gateway | `true` |
| `API_SERVER_KEY` | API server auth key (16+ chars) | *(generated)* |
| `HERMES_MEMORY_LIMIT` | Memory limit | `4g` |
| `HERMES_CPUS_LIMIT` | CPU limit | `2.0` |
| `HERMES_DATA_DIR` | Data directory | `./data` |
| `HERMES_MODELS_DIR` | Models directory | `./models` |
| `HERMES_MODEL_NAME` | HuggingFace model | `NousResearch/Hermes-3-Llama-3.1-8B` |
| `HERMES_CONTEXT_SIZE` | Context window | `8192` |
| `HERMES_TEMPERATURE` | Sampling temperature | `0.7` |
| `HERMES_TOP_P` | Top-p parameter | `0.9` |
| `HERMES_MAX_TOKENS` | Max tokens | `2048` |
| `HERMES_LOG_LEVEL` | Log level | `INFO` |
| `API_PROVIDER` | `huggingface`, `openai`, or `ollama` | `huggingface` |
| `HERMES_HF_TOKEN` | HuggingFace token | — |
| `HERMES_OPENAI_API_KEY` | OpenAI API key | — |
| `HERMES_OPENAI_BASE_URL` | OpenAI-compatible base URL | — |
| `HERMES_OLLAMA_HOST` | Ollama server URL | — |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | — |
| `DISCORD_BOT_TOKEN` | Discord bot token | — |
| `SLACK_BOT_TOKEN` | Slack bot token | — |
| `SLACK_APP_TOKEN` | Slack app token | — |

## Persistent State

The Hermes agent keeps all of its state — configuration, API keys, sessions,
skills, and memories — in a single directory mounted at `/opt/data`. This setup
uses a named Docker volume (`hermes-data`) rather than a host bind mount,
because SQLite's WAL mode silently corrupts databases that live across a
macOS or Windows Docker Desktop VM boundary.

The volume survives container updates, so agent memory and configuration are
preserved across restarts and image changes.

## Security

- **No secrets in repository**: All sensitive values must be in `.env` (gitignored)
- **Encrypted UI config**: `.hermes-config.enc` holds web UI configuration, encrypted with your passphrase — never committed
- **Pre-commit hooks**: Prevent accidental secret commits
- **Environment isolation**: Secrets loaded only at runtime

## Development

### Running Tests

```bash
# Run test suite
uv run pytest

# Run with coverage
uv run pytest --cov=src.hermes_setup

# Run specific test file
uv run pytest tests/test_config_manager.py
```

### Code Quality

```bash
# Run linting
uv run ruff check src tests

# Run type checking
uv run mypy src

# Format code
uv run ruff check --fix src tests
uv run ruff format src tests
```

## Project Structure

```
hermes-setup/
├── src/
│   └── hermes_setup/
│       ├── __init__.py
│       ├── __main__.py     # CLI entrypoint
│       ├── cli.py          # Typer-based CLI
│       ├── web/            # Web-based UI (FastAPI + HTMX)
│       │   ├── __init__.py
│       │   ├── backend.py  # FastAPI server + REST endpoints
│       │   ├── config_manager.py  # Encrypted config persistence
│       │   ├── jobs.py     # Background job tracking for Docker ops
│       │   ├── service.py  # Wraps Docker/State/Config
│       │   ├── tabs.py     # HTMX tab fragments
│       │   └── static/     # HTML, CSS, JS assets
│       │       ├── app.js
│       │       └── index.html
│       ├── config.py       # Pydantic settings management
│       ├── docker.py       # Docker Compose orchestration
│       ├── secrets.py      # Secrets validation and injection helpers
│       ├── state.py        # Agent state persistence handling
│       └── utils.py        # Utility functions
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_config_manager.py
│   ├── test_docker.py
│   └── test_web.py
├── docker/
│   ├── compose.yml         # Development Docker compose
│   ├── compose.prod.yml    # Production Docker compose
│   └── hermes/config.yaml  # Agent runtime config template
├── .env.example            # Template for environment variables
├── .gitignore              # Git ignore rules
├── .pre-commit-config.yaml # Pre-commit hooks
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Disclaimer

This project is not affiliated with Nous Research or the Hermes agent. It is a community-created tool for easier deployment and management.

## Acknowledgments

- [Nous Research Hermes](https://hermes-agent.nousresearch.com/) - The amazing personal assistant
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer
- [Pydantic](https://docs.pydantic.dev/) - Data validation and settings management
