# Hermes Setup

Portable, credential-free setup for deploying the [Hermes agent](https://hermes-agent.nousresearch.com/) (Nous Research personal assistant) using Docker and Python.

![Hermes Setup Demo](docs/demo.gif)

## Features

- **Docker-based deployment** - Runs Hermes agent in isolated containers
- **Zero-credential repository** - No secrets in git history
- **Web-based UI configuration** - Browser-based setup with encrypted config storage
- **Zero-downtime updates** - Updates without service interruption
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

- **Configuration** — Set all Hermes agent values (image, ports, resource limits, model name, context size, temperature, etc.)
- **Encrypted persistence** — Configuration is saved to `.hermes-config.enc` on your local machine, encrypted with a passphrase you supply. This file is **never committed to the repository**
- **Docker control** — Start, stop, restart, and view container logs
- **State management** — Create and restore backups of persistent state
- **Project init** — Generate compose files, `.env.example`, `.gitignore`, and security hooks

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

Configuration is managed through environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `HERMES_DOCKER_IMAGE` | Docker image to use | `nousresearch/hermes:latest` |
| `HERMES_HOST_PORT` | Host port to bind | `8000` |
| `HERMES_CONTAINER_PORT` | Container port | `8000` |
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

## Persistent State

The Hermes agent maintains persistent state in:
- `./data` - Agent memory, conversation history, and configuration
- `./models` - Cached model files

These directories are mounted as Docker volumes and survive container updates.

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
│       │   ├── service.py  # Wraps Docker/State/Config
│       │   ├── tabs.py     # HTMX tab fragments
│       │   └── static/     # HTML, CSS, JS assets
│       │       └── index.html
│       ├── config.py       # Pydantic settings management
│       ├── docker.py       # Docker Compose orchestration
│       ├── secrets.py      # Secrets validation and injection helpers
│       ├── state.py        # Agent state persistence handling
│       └── utils.py        # Utility functions
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_docker.py
│   └── test_config_manager.py
├── docker/
│   ├── Dockerfile          # Hermes agent Docker image
│   ├── compose.yml         # Development Docker compose
│   └── compose.prod.yml    # Production Docker compose
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
