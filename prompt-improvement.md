# Improved Prompt: Docker-Based Hermes Agent Setup Project

---

## Role
You are a senior DevOps engineer and Python developer specializing in containerized agent deployments, CI/CD pipelines, and secrets management.

## Context
I want to create a **portable, credential-free project** that sets up a Docker-based "Hermes agent" (the personal assistant from Nous Research) on any machine. The project itself lives in a GitHub repository and uses Python (managed with `uv`) for its setup/automation scripts.

**Reference:** 
- Official documentation: https://hermes-agent.nousresearch.com/docs
- Docker installation guide: https://hermes-agent.nousresearch.com/docs/user-guide/docker

**Additional requirement:** Include a friendly Terminal User Interface (TUI) for interacting with the Hermes agent setup and management.

## Requirements

### Core Functionality
1. **Repository Initialization**
   - Transform the current folder into a GitHub-ready Python project using `uv`
   - Include: `pyproject.toml`, `README.md`, `.gitignore`, `uv.lock`, CI/CD workflow files
   - Scripts should be modular, typed, and tested

2. **CI/CD Pipeline with Zero-Downtime Deployments**
   - Pipeline stages: lint → test → build image → deploy
   - **Critical constraint:** Deployments must **not affect existing agent memory, schedulers, or persistent state**
   - Deployment target: (specify — e.g., local Docker, Docker Swarm, Kubernetes, remote VM via SSH, Portainer, etc.)
   - Rollback strategy required

3. **Terminal User Interface (TUI)**
   - Build a friendly TUI for setup, configuration, and management of the Hermes agent
   - Commands: install, start, stop, restart, status, config, logs, update
   - Should guide non-technical users through initial setup interactively
   - Framework: Textual (preferred) or Rich + prompt_toolkit

4. **Zero-Credential Repository**
   - No secrets, API keys, or credentials in git history
   - Use `.env.example` + `.gitignore` pattern
   - Document secrets injection method (GitHub Actions secrets, 1Password, Doppler, SOPS, etc.)
   - Pre-commit hooks to prevent credential leaks (e.g., `gitleaks`, `detect-secrets`)

### Enhancements (Phase 2)
4. **n8n Integration**
   - Define: webhook triggers? workflow automation? credential sync?
   - n8n runs in Docker alongside Hermes? Separate instance?

5. **Obsidian "Second Brain" Integration**
   - Define: sync markdown files? bidirectional? read-only index?
   - Obsidian vault location: local mount? remote (Syncthing, iCloud, Git)?

## Constraints & Guardrails
- **Python ≥ 3.11**, managed exclusively via `uv`
- **Docker Compose** for local orchestration (production target TBD)
- **No credentials in repo** — enforce via pre-commit + CI checks
- **Idempotent setup scripts** — safe to re-run
- **Cross-platform** (Linux/macOS/WSL2)
- **TUI framework**: Use `textual` (preferred) or `rich` + `prompt_toolkit` for the terminal interface
- **Keep it under ~2500 lines of Python** for maintainability (includes TUI)
- Output: a **complete implementation plan** (not code yet) with:
  - Project structure tree
  - CI/CD workflow diagram (text-based)
  - Secrets management strategy
  - Phase 1 vs Phase 2 scope split
  - Open questions for me to answer before implementation

## Output Format
Return a **single Markdown file** named `IMPLEMENTATION_PLAN.md` with:
1. Executive summary (3–5 lines)
2. Project structure (tree)
3. CI/CD pipeline design (mermaid or ASCII)
4. Secrets management approach
5. TUI design overview (components, screens, workflow)
6. Phase 1 (core) vs Phase 2 (enhancements) breakdown
7. Open questions (numbered, for my answers)
8. Risks & mitigations table

---

## Example Output Snippet (for structure reference)

```markdown
## Project Structure
hermes-setup/
├── .github/workflows/
│   ├── ci.yml          # lint, test, build
│   └── cd.yml          # deploy with zero-downtime
├── src/hermes_setup/
│   ├── __init__.py
│   ├── cli.py          # typer/click entrypoint for setup
│   ├── tui.py          # Textual-based terminal interface
│   ├── config.py       # pydantic-settings, env-driven
│   ├── docker.py       # compose generation, deployment
│   └── secrets.py      # validation, injection helpers
├── tests/
├── docker/
│   ├── Dockerfile
│   ├── compose.yml
│   └── compose.prod.yml
├── .env.example
├── .pre-commit-config.yaml
├── pyproject.toml
└── README.md
```

---

## Key Improvements Made

| Original Gap | Improvement |
|--------------|-------------|
| "Hermes agent" undefined | Replaced with explicit reference to Nous Research Hermes personal assistant + documentation URLs |
| "Pipeline like flow" too vague | Specified stages (lint → test → build → deploy), zero-downtime requirement, deployment target question |
| "Free of credentials" open-ended | Added `.env.example` + `.gitignore` pattern, pre-commit scanning (`gitleaks`/`detect-secrets`), and CI secret-check requirements |
| n8n / Obsidian underspecified | Added targeted questions about what each integration should actually do (webhooks, sync direction, vault location) |
| No project structure guidance | Included sample file tree with purposes for each module |
| No output format specified | Defined exact deliverable: `IMPLEMENTATION_PLAN.md` with sections |
| No constraints on Python/Docker versions | Pinned Python ≥ 3.11, `uv`, Docker Compose |
| No phase boundary | Explicit Phase 1 (core repo/CI/secrets/TUI) vs Phase 2 (n8n/Obsidian enhancements) |
| No risk analysis | Added risks & mitigations table requirement |
| No TUI requirement | Added dedicated TUI requirement with command list and Textual framework preference |