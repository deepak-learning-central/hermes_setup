"""Tests for the background job runner and the web API surface."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from hermes_setup.web.backend import app
from hermes_setup.web.jobs import JobManager


class TestJobManager:
    """Test the background job manager."""

    def test_submit_returns_pending_job(self):
        """A submitted job should be retrievable straight away."""
        manager = JobManager()
        job = manager.submit("Test", lambda emit: True)
        assert manager.get(job.id) is not None
        assert job.action == "Test"

    def test_job_completes_successfully(self):
        """A job whose work returns True should report success."""
        manager = JobManager()
        job = manager.submit("Test", lambda emit: True)

        for _ in range(100):
            if job.finished:
                break
            time.sleep(0.01)

        assert job.status == "succeeded"
        assert job.ok is True
        assert job.finished_at is not None

    def test_job_failure_is_recorded(self):
        """A job whose work raises should report failure, not crash."""
        manager = JobManager()

        def boom(emit):
            raise RuntimeError("kaboom")

        job = manager.submit("Test", boom)

        for _ in range(100):
            if job.finished:
                break
            time.sleep(0.01)

        assert job.status == "failed"
        assert job.ok is False
        assert "kaboom" in job.message

    def test_output_lines_are_captured(self):
        """Lines emitted by the work function should be captured."""
        manager = JobManager()

        def work(emit):
            emit("first")
            emit("second")
            return True

        job = manager.submit("Test", work)

        for _ in range(100):
            if job.finished:
                break
            time.sleep(0.01)

        assert job.output == ["first", "second"]

    def test_output_is_truncated_to_max_lines(self):
        """The output tail should be bounded so memory does not grow forever."""
        manager = JobManager(max_output_lines=5)

        def work(emit):
            for i in range(50):
                emit(f"line {i}")
            return True

        job = manager.submit("Test", work)

        for _ in range(200):
            if job.finished:
                break
            time.sleep(0.01)

        assert len(job.output) == 5
        assert job.output[-1] == "line 49"


@pytest.fixture
def client() -> TestClient:
    """Return a test client for the web API."""
    return TestClient(app)


class TestHealthEndpoint:
    """The frontend polls /health with HEAD as well as GET."""

    def test_get_health(self, client: TestClient):
        """GET /health should report healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_head_health(self, client: TestClient):
        """HEAD /health should not 405 — the browser polls with HEAD."""
        response = client.head("/health")
        assert response.status_code == 200


class TestDockerActionEndpoints:
    """The Docker endpoints are triggered from plain buttons, with no body."""

    def test_start_accepts_empty_body(self, client: TestClient):
        """POST /docker/start with no JSON body should not 422."""
        response = client.post("/docker/start")
        assert response.status_code == 200
        assert "job_id" in response.json()

    def test_stop_accepts_empty_body(self, client: TestClient):
        """POST /docker/stop with no JSON body should not 422."""
        response = client.post("/docker/stop")
        assert response.status_code == 200
        assert "job_id" in response.json()

    def test_restart_accepts_empty_body(self, client: TestClient):
        """POST /docker/restart with no JSON body should not 422."""
        response = client.post("/docker/restart")
        assert response.status_code == 200
        assert "job_id" in response.json()

    def test_start_accepts_production_flag(self, client: TestClient):
        """A JSON body with production=true should still be accepted."""
        response = client.post("/docker/start", json={"production": True})
        assert response.status_code == 200
        assert "job_id" in response.json()

    def test_unknown_job_returns_404(self, client: TestClient):
        """Polling an unknown job id should return 404."""
        response = client.get("/jobs/does-not-exist")
        assert response.status_code == 404

    def test_job_status_is_retrievable(self, client: TestClient):
        """A submitted job should be pollable through /jobs/{id}."""
        job_id = client.post("/docker/start").json()["job_id"]
        response = client.get(f"/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["id"] == job_id


class TestTabFragments:
    """Each tab renders an HTML fragment."""

    @pytest.mark.parametrize("tab", ["dashboard", "config", "docker", "state", "system"])
    def test_tab_renders(self, client: TestClient, tab: str):
        """Every known tab should return HTML."""
        response = client.get(f"/tab/{tab}")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_unknown_tab_returns_message(self, client: TestClient):
        """An unknown tab name should render a message rather than 500."""
        response = client.get("/tab/nope")
        assert response.status_code == 200
        assert "Unknown tab" in response.text

    def test_dashboard_has_progress_panel(self, client: TestClient):
        """The dashboard must contain a panel for showing progress."""
        body = client.get("/tab/dashboard").text
        assert 'id="job-panel"' in body
        assert 'data-docker-action="start"' in body

    def test_config_has_api_server_key_field(self, client: TestClient):
        """The config tab must expose the API server key field."""
        body = client.get("/tab/config").text
        assert 'id="api_server_key"' in body
        assert 'id="api_port"' in body
