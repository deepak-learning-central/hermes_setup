# Hermes Setup

Portable, credential-free setup for deploying the [Hermes agent](https://hermes-agent.nousresearch.com/) (Nous Research personal assistant) using Docker and Python.

![Hermes Setup Demo](docs/demo.gif)

## Features

- **Docker-based deployment** - Runs Hermes agent in isolated containers
- **Zero-credential repository** - No secrets in git history
- **Terminal User Interface (TUI)** - Easy management via text-based interface
- **CI/CD pipeline** - Automated testing, building, and deployment
- **Zero-downtime updates** - Updates without service interruption
- **State persistence** - Agent memory and configuration survive updates
- **Cross-platform** - Works on Linux, macOS, and WSL2
- **Secure by design** - Pre-commit hooks and CI scans prevent secret leaks

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

# Copy template and configure
cp .env.example .env
# Edit .env to set your preferences

# Start Hermes agent
hermes-setup up
```

## Usage

### CLI Commands

```bash
# Start the agent
hermes-setup up

# Stop the agent
hermes-setup down

# Restart the agent
hermes-setup restart

# View logs
hermes-setup logs --follow

# Update to latest version
hermes-setup update

# Launch the TUI
hermes-setup tui
```

### TUI Interface

The TUI provides an interactive interface for managing your Hermes agent:

- **Dashboard**: Real-time status and quick actions
- **Configuration**: Modify agent settings
- **Logs**: View container logs
- **Management**: Backups, cleanup, and diagnostics

Launch with: `hermes-setup tui`

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

## CI/CD Pipeline

The project includes GitHub Actions workflows for continuous integration and deployment:

- **CI Workflow** (`.github/workflows/ci.yml`): Linting, testing, security scans
- **CD Workflow** (`.github/workflows/cd.yml`): Zero-downtime deployment with rollback

## Security

- **No secrets in repository**: All sensitive values must be in `.env` (gitignored)
- **Pre-commit hooks**: Prevent accidental secret commits
- **CI secret scanning**: Fails builds if secrets are detected
- **Environment isolation**: Secrets loaded only at runtime

## Development

### Running Tests

```bash
# Run test suite
uv run pytest

# Run with coverage
uv run pytest --cov=src.hermes_setup

# Run specific test file
uv run pytest tests/test_tui.py
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
├── .github/
│   └── workflows/
│       ├── ci.yml          # Lint, test, security scans
│       └── cd.yml          # Zero-downtime deployment
├── src/
│   └── hermes_setup/
│       ├── __init__.py
│       ├── __main__.py     # CLI entrypoint
│       ├── cli.py          # Typer-based CLI
│       ├── tui.py          # Textual-based terminal interface
│       ├── config.py       # Pydantic settings management
│       ├── docker.py       # Docker Compose orchestration
│       ├── secrets.py      # Secrets validation and injection helpers
│       ├── state.py        # Agent state persistence handling
│       └── utils.py        # Utility functions
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_docker.py
│   └── test_tui.py
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
- [Textual](https://textual.textualize.io/) - Awesome TUI framework
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer
- [Pydantic](https://docs.pydantic.dev/) - Data validation and settings management