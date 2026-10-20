"""Background job tracking for long-running Docker operations.

Container operations such as ``docker compose up -d`` can take minutes (image
pull, image build).  The web UI starts them in the background so the HTTP
request returns immediately and the browser can poll for progress while the
operation runs.

Each job keeps a bounded tail of the command output so the UI can show live
progress without unbounded memory growth.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

#: Signature of the callable that performs the work.  It receives a
#: ``emit(line)`` callback used to stream output lines back to the UI.
JobWork = Callable[[Callable[[str], None]], bool]


@dataclass
class Job:
    """A single background operation and its observable state."""

    id: str
    action: str
    status: str = "pending"
    message: str = ""
    ok: bool | None = None
    output: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    @property
    def finished(self) -> bool:
        """Return True once the job has reached a terminal state."""
        return self.status in {"succeeded", "failed"}

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the job."""
        return {
            "id": self.id,
            "action": self.action,
            "status": self.status,
            "message": self.message,
            "ok": self.ok,
            "output": list(self.output),
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }


class JobManager:
    """Runs Docker operations on background threads and tracks their state."""

    def __init__(self, max_output_lines: int = 500) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._max_output_lines = max_output_lines

    def submit(self, action: str, work: JobWork) -> Job:
        """Start *work* on a background thread and return the created job."""
        job = Job(id=uuid.uuid4().hex[:12], action=action)
        with self._lock:
            self._jobs[job.id] = job
        thread = threading.Thread(target=self._run, args=(job, work), daemon=True)
        thread.start()
        return job

    def get(self, job_id: str) -> Job | None:
        """Return the job with *job_id*, or None if it is unknown."""
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        """Return all known jobs, newest first."""
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _run(self, job: Job, work: JobWork) -> None:
        """Execute *work*, capturing output and recording the outcome."""
        job.status = "running"
        job.message = f"Running {job.action}..."
        try:
            ok = work(self._emit(job))
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            job.status = "failed"
            job.ok = False
            job.message = f"{job.action} failed: {exc}"
            job.finished_at = time.time()
            return
        job.ok = ok
        job.status = "succeeded" if ok else "failed"
        job.message = f"{job.action} {'succeeded' if ok else 'failed'}"
        job.finished_at = time.time()

    def _emit(self, job: Job) -> Callable[[str], None]:
        """Return a callback that appends a line to the job's output tail."""

        def emit(line: str) -> None:
            with self._lock:
                job.output.append(line)
                excess = len(job.output) - self._max_output_lines
                if excess > 0:
                    del job.output[:excess]

        return emit


#: Shared manager used by the backend for all background operations.
manager = JobManager()
