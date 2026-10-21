"""FastAPI backend for the Hermes web setup UI.

The backend owns a single :class:`SetupSession` which holds the encryption
passphrase, the encrypted config file location, and the
:class:`SetupService` that wraps the existing Docker orchestration.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError

from . import jobs
from .config_manager import EncryptedConfigManager
from .service import SetupService, find_available_port, is_port_in_use
from .tabs import render_tab

FRONTEND_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Hermes Setup API",
    version="0.1.0",
    description="Web-based configuration and Docker orchestration for the Hermes agent",
)


operation_lock = threading.Lock()


@app.middleware("http")
async def local_browser_only(request: Request, call_next: Any) -> Any:
    """Reject cross-origin browser requests to this local administration tool."""
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        return JSONResponse({"detail": "Cross-origin requests are not allowed"}, status_code=403)
    host = request.headers.get("host", "").split(":")[0]
    if host not in {"localhost", "127.0.0.1", "[", "testserver"}:
        return JSONResponse({"detail": "Use localhost through an SSH tunnel"}, status_code=403)
    mutations = {
        "/setup",
        "/config/save",
        "/config/load",
        "/init",
        "/docker/start",
        "/docker/stop",
        "/docker/restart",
    }
    if request.method == "POST" and request.url.path in mutations:
        if not operation_lock.acquire(blocking=False):
            return JSONResponse(
                {"detail": "Another configuration operation is in progress"}, status_code=409
            )
        try:
            if any(not job.finished for job in jobs.manager.list()):
                return JSONResponse(
                    {"detail": "Wait for the current operation to finish"}, status_code=409
                )
            response = await call_next(request)
        finally:
            operation_lock.release()
    else:
        response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ConfigSaveRequest(BaseModel):
    """Payload for saving the configuration."""

    passphrase: str = Field(min_length=1, description="Encryption passphrase")
    config: dict[str, Any] = Field(default_factory=dict, description="Flat env-var config")


class ConfigLoadRequest(BaseModel):
    """Payload for loading the configuration."""

    passphrase: str = Field(min_length=1, description="Encryption passphrase")


class DockerActionRequest(BaseModel):
    """Payload for Docker lifecycle actions."""

    production: bool = False


class BackupRequest(BaseModel):
    """Payload for creating a state backup."""

    reason: str = "manual"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


class SetupSession:
    """Holds state shared across requests for the lifetime of the server."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.manager = EncryptedConfigManager(config_path)
        self.service = SetupService()
        self.passphrase: str | None = None
        #: True once a config has actually been decrypted (or saved) in this
        #: session.  A failed load attempt must not count — otherwise the
        #: frontend would restore a config that was never opened.
        self.config_loaded = False

    def set_passphrase(self, passphrase: str) -> None:
        """Store the passphrase and attach it to the config manager."""
        self.passphrase = passphrase
        self.manager.set_passphrase(passphrase)

    def refresh_service(self) -> None:
        """Reload config from disk into the service."""
        loaded = self.manager.load()
        if loaded is not None:
            self.service.config = loaded
            self.service.orchestrator = type(self.service.orchestrator)(loaded)
            self.config_loaded = True


session = SetupSession()


@app.on_event("startup")
async def _startup() -> None:
    """Best-effort load of an existing config on startup.

    The encrypted file cannot be read without the user's passphrase, so this
    normally finds nothing.  It must not raise — the server has to come up
    so the user can be prompted for the passphrase.
    """
    loaded = session.manager.load()
    if loaded is not None:
        session.service.config = loaded
        session.config_loaded = True


# ---------------------------------------------------------------------------
# Routes: config persistence
# ---------------------------------------------------------------------------


@app.post("/config/save")
async def config_save(request: ConfigSaveRequest) -> JSONResponse:
    """Persist the configuration to an encrypted file on this machine."""
    session.set_passphrase(request.passphrase)
    try:
        session.service.apply_config(request.config)
    except (ValidationError, ValueError):
        raise HTTPException(
            status_code=422, detail="Invalid configuration. Check ports, model and resource values."
        )
    session.manager.save(session.service.config)
    session.config_loaded = True
    # Regenerate compose files so docker compose up uses the saved values
    session.service.orchestrator.write_compose_files()
    return JSONResponse({"ok": True, "path": str(session.manager.filepath), "exists": True})


@app.post("/config/load")
async def config_load(request: ConfigLoadRequest) -> JSONResponse:
    """Load the encrypted configuration and return it to the client."""
    session.set_passphrase(request.passphrase)
    loaded = session.manager.load()
    if loaded is None:
        # The passphrase did not open the file — leave the session marked as
        # "not loaded" so the form is not repopulated with stale defaults.
        session.config_loaded = False
        raise HTTPException(
            status_code=404, detail="No readable encrypted config found (wrong passphrase?)"
        )
    session.service = SetupService(loaded)
    session.config_loaded = True
    return JSONResponse({"ok": True, "config": session.manager.config_to_dict(loaded)})


@app.get("/config/current")
async def config_current() -> JSONResponse:
    """Return the config the server currently holds in memory.

    Used to restore the form after the passphrase has been entered once in
    this session, so the fields show the saved values rather than defaults.
    """
    if not session.config_loaded:
        raise HTTPException(status_code=404, detail="No config loaded in this session")
    return JSONResponse(
        {"ok": True, "config": session.manager.config_to_dict(session.service.config)}
    )


@app.get("/config/status")
async def config_status() -> JSONResponse:
    """Report whether the encrypted config file exists (without decrypting it).

    Also reports whether a config has already been opened in this session, so
    the frontend can restore the form right away instead of leaving it at
    its defaults.
    """
    return JSONResponse(
        {
            "ok": True,
            "exists": session.manager.exists(),
            "path": str(session.manager.filepath),
            "alreadyLoaded": session.config_loaded,
        }
    )


# ---------------------------------------------------------------------------
# Routes: project initialization
# ---------------------------------------------------------------------------


@app.post("/init")
async def init_project() -> JSONResponse:
    """Generate all project files (compose, .env.example, .gitignore, etc.)."""
    try:
        result = session.service.init_project()
        return JSONResponse({"ok": True, "generated": result["generated"]})
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Routes: Docker / container lifecycle
# ---------------------------------------------------------------------------


@app.get("/docker/status")
async def docker_status() -> JSONResponse:
    """Return Docker availability information."""
    return JSONResponse({"ok": True, **session.service.docker_status()})


@app.post("/setup")
def setup_hermes(request: ConfigSaveRequest) -> JSONResponse:
    """Save settings and run the complete deployment as one background job."""
    if any(not job.finished for job in jobs.manager.list()):
        raise HTTPException(status_code=409, detail="An operation is already running")
    if session.manager.exists() and not session.config_loaded:
        raise HTTPException(
            status_code=409,
            detail="Unlock your saved settings before running setup again so channel credentials are preserved.",
        )
    candidate = SetupService()
    try:
        if len(request.passphrase) < 12:
            raise ValueError("Choose a passphrase of at least 12 characters.")
        candidate.apply_config(request.config)
        cfg = candidate.config
        cfg.validate_channels()
        if cfg.api_provider != "openai":
            raise ValueError("Choose an OpenAI-compatible provider for this setup wizard.")
        if not cfg.openai_api_key or not cfg.openai_base_url or not cfg.model_name.strip():
            raise ValueError("Provider URL, model name and API key are required.")
        from urllib.parse import urlparse

        if urlparse(cfg.openai_base_url).scheme not in {"http", "https"}:
            raise ValueError("Provider URL must start with http:// or https://")
        if cfg.api_port in {8765, cfg.dashboard_port}:
            raise ValueError("API, dashboard and setup ports must be different.")
        if not cfg.api_server_key:
            import secrets

            cfg.api_server_key = secrets.token_hex(32)
        if len(cfg.api_server_key) < 16:
            raise ValueError("API server key must contain at least 16 characters.")
    except ValidationError:
        raise HTTPException(status_code=422, detail="Invalid configuration values")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    cfg.docker_compose_file = ".hermes-runtime/compose.yml"
    cfg.docker_compose_prod_file = ".hermes-runtime/compose.prod.yml"
    session.set_passphrase(request.passphrase)
    session.manager.save(cfg)
    session.service = candidate
    session.config_loaded = True
    job = jobs.manager.submit("Set up Hermes", candidate.setup_streaming)
    return JSONResponse({"ok": True, "job_id": job.id})


@app.get("/agent/health")
def agent_health() -> JSONResponse:
    return JSONResponse(session.service.agent_health())


@app.post("/docker/start")
async def docker_start(request: DockerActionRequest | None = None) -> JSONResponse:
    """Start the Hermes agent containers (as a background job)."""
    production = request.production if request else False
    job = jobs.manager.submit(
        "Starting Hermes",
        lambda emit: session.service.start_streaming(production=production, on_line=emit),
    )
    return JSONResponse({"ok": True, "job_id": job.id, "action": job.action})


@app.post("/docker/stop")
async def docker_stop(request: DockerActionRequest | None = None) -> JSONResponse:
    """Stop the Hermes agent containers (as a background job)."""
    production = request.production if request else False
    job = jobs.manager.submit(
        "Stopping Hermes",
        lambda emit: session.service.stop_streaming(
            production=production, volumes=False, on_line=emit
        ),
    )
    return JSONResponse({"ok": True, "job_id": job.id, "action": job.action})


@app.post("/docker/restart")
async def docker_restart(request: DockerActionRequest | None = None) -> JSONResponse:
    """Restart the Hermes agent containers (as a background job)."""
    production = request.production if request else False
    job = jobs.manager.submit(
        "Restarting Hermes",
        lambda emit: session.service.restart_streaming(production=production, on_line=emit),
    )
    return JSONResponse({"ok": True, "job_id": job.id, "action": job.action})


@app.get("/jobs/{job_id}")
async def job_status(job_id: str) -> JSONResponse:
    """Return the state of a background Docker operation."""
    job = jobs.manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job id")
    return JSONResponse({"ok": True, **job.to_dict()})


@app.get("/docker/status-full")
async def docker_status_full() -> JSONResponse:
    """Full container status plus recent logs."""
    return JSONResponse({"ok": True, **session.service.status(), "logs": session.service.logs()})


@app.get("/docker/logs")
async def docker_logs(tail: int = 200) -> JSONResponse:
    """Recent container logs as plain text."""
    return JSONResponse({"ok": True, "logs": session.service.logs(tail=tail)})


# ---------------------------------------------------------------------------
# Routes: state management
# ---------------------------------------------------------------------------


@app.post("/state/backup")
async def state_backup(request: BackupRequest) -> JSONResponse:
    """Create a backup of persistent state."""
    return JSONResponse({"ok": True, **session.service.backup_state(reason=request.reason)})


@app.post("/state/restore")
async def state_restore() -> JSONResponse:
    """Restore from the most recent backup."""
    return JSONResponse({"ok": True, **session.service.restore_backup()})


@app.get("/state/report")
async def state_report() -> JSONResponse:
    """Return a human-readable state report."""
    return JSONResponse({"ok": True, "report": session.service.state_report()})


@app.get("/state/paths")
async def state_paths() -> JSONResponse:
    """Return persistent state paths."""
    return JSONResponse({"ok": True, **session.service.persistent_paths()})


# ---------------------------------------------------------------------------
# Routes: port / network helpers
# ---------------------------------------------------------------------------


@app.get("/port/available/{start_port}")
async def port_available(start_port: int) -> JSONResponse:
    """Return an available port starting from *start_port*."""
    port = find_available_port(start_port)
    if port is None:
        raise HTTPException(status_code=500, detail="No available port in range")
    return JSONResponse({"ok": True, "port": port})


@app.post("/port/check")
async def port_check(port: int) -> JSONResponse:
    """Check whether a port is already in use."""
    return JSONResponse({"ok": True, "in_use": is_port_in_use(port)})


@app.get("/system/info")
async def system_info() -> JSONResponse:
    """Return basic system information for the diagnostics panel."""
    return JSONResponse({"ok": True, **session.service.system_info()})


# ---------------------------------------------------------------------------
# Routes: HTMX tab fragments
# ---------------------------------------------------------------------------


@app.get("/tab/{tab_name}", response_class=HTMLResponse)
async def tab(tab_name: str) -> HTMLResponse:
    """Return the HTML fragment for a settings tab."""
    return HTMLResponse(render_tab(tab_name))


@app.api_route("/health", methods=["GET", "HEAD"])
async def health() -> JSONResponse:
    """Liveness probe used by the frontend connection indicator.

    ``HEAD`` is accepted as well so the browser can poll it cheaply.
    """
    return JSONResponse({"ok": True, "status": "healthy"})


# ---------------------------------------------------------------------------
# Static file serving: the HTML UI
# ---------------------------------------------------------------------------


@app.get("/")
async def root() -> FileResponse:
    """Serve the HTML setup page."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{path:path}")
async def static_files(path: str) -> FileResponse:
    """Serve static assets (CSS, JS) from the frontend directory."""
    file_path = (FRONTEND_DIR / path).resolve()
    if not file_path.is_relative_to(FRONTEND_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Forbidden")
    if file_path.is_file():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Not found")


def run(host: str = "127.0.0.1", port: int = 8765, reload: bool = False) -> None:
    """Run the web setup server."""
    import uvicorn

    uvicorn.run("hermes_setup.web.backend:app", host=host, port=port, reload=reload)
