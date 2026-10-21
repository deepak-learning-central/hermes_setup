"""Deployment regressions; no Docker daemon or provider credentials required."""

import json
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from hermes_setup.config import HermesConfig
from hermes_setup.docker import DockerOrchestrator
from hermes_setup.web import backend
from hermes_setup.web.service import SetupService


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(backend.jobs, "manager", backend.jobs.JobManager())
    monkeypatch.setattr(backend, "session", backend.SetupSession(tmp_path / "config.enc"))
    return TestClient(backend.app)


def payload():
    return {
        "passphrase": "a long test passphrase",
        "config": {
            "api_provider": "openai",
            "openai_base_url": "https://example.com/v1",
            "openai_api_key": "test-provider-key",
            "model_name": "example-model",
            "api_port": 8642,
            "dashboard_port": 9119,
        },
    }


def test_setup_saves_private_config_and_runs_job(client):
    with patch.object(SetupService, "setup_streaming", return_value=True) as work:
        response = client.post("/setup", json=payload())
        assert response.status_code == 200
        assert response.json()["job_id"]
        assert len(backend.session.service.config.api_server_key) >= 16
        assert backend.session.service.config.docker_compose_file == ".hermes-runtime/compose.yml"
        assert backend.session.manager.filepath.stat().st_mode & 0o777 == 0o600
        assert "test-provider-key" not in backend.session.manager.filepath.read_text()
        # Wait for background invocation before the patch is removed.
        import time

        for _ in range(100):
            if work.called:
                break
            time.sleep(0.01)
        assert work.called


def test_invalid_setup_does_not_save(client):
    body = payload()
    body["config"]["api_port"] = 70000
    assert client.post("/setup", json=body).status_code == 422
    assert not backend.session.manager.exists()


def test_bad_origin_cannot_control_docker(client):
    assert (
        client.post("/docker/stop", headers={"Origin": "https://evil.example"}).status_code == 403
    )


def test_load_replaces_orchestrator_config(client):
    backend.session.set_passphrase("test")
    config = HermesConfig(api_port=9999)
    backend.session.manager.save(config)
    assert client.post("/config/load", json={"passphrase": "test"}).status_code == 200
    assert backend.session.service.orchestrator.config.api_port == 9999


def test_production_stop_preserves_volume(client):
    with patch.object(SetupService, "stop_streaming", return_value=True) as stop:
        response = client.post("/docker/stop", json={"production": True})
        job = backend.jobs.manager.get(response.json()["job_id"])
        import time

        for _ in range(100):
            if job.finished:
                break
            time.sleep(0.01)
        assert stop.call_args.kwargs["volumes"] is False


def test_linux_compose_has_reachable_loopback_dashboard():
    cfg = HermesConfig(api_port=8650, openai_api_key="test$VALUE\n# comment")
    with patch("hermes_setup.docker.platform.system", return_value="Linux"):
        content = DockerOrchestrator(cfg).generate_compose_file()
    assert "network_mode: host" in content
    assert "    ports:" not in content
    assert "API_SERVER_HOST=127.0.0.1" in content
    assert "http://localhost:8650/health" in content
    assert json.dumps("OPENAI_API_KEY=test$$VALUE\n# comment") in content
    assert ":stable" not in content


def test_apply_config_is_atomic():
    service = SetupService(HermesConfig(api_port=8642))
    with pytest.raises(ValueError):
        service.apply_config({"api_port": -1})
    assert service.config.api_port == 8642


def test_setup_stops_on_pull_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = SetupService(HermesConfig())
    with (
        patch("platform.system", return_value="Linux"),
        patch("platform.machine", return_value="aarch64"),
        patch.object(service.orchestrator, "check_docker", return_value=True),
        patch.object(service.orchestrator, "check_compose", return_value=True),
        patch.object(
            service.orchestrator, "stream_compose", return_value=(False, "pull failed")
        ) as run,
    ):
        assert service.setup_streaming(Mock()) is False
        assert run.call_count == 1


def test_setup_checks_assistant_after_start(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = SetupService(HermesConfig())
    with (
        patch("platform.system", return_value="Linux"),
        patch("platform.machine", return_value="aarch64"),
        patch.object(service.orchestrator, "check_docker", return_value=True),
        patch.object(service.orchestrator, "check_compose", return_value=True),
        patch.object(service.orchestrator, "stream_compose", return_value=(True, "")) as run,
        patch.object(
            service, "agent_health", return_value={"ok": True, "dashboard": {"reachable": True}}
        ),
        patch("httpx.Client") as http,
    ):
        http.return_value.__enter__.return_value.post.return_value.json.return_value = {
            "choices": [{"message": {"content": "Ready"}}]
        }
        assert service.setup_streaming(Mock()) is True
        assert run.call_count == 3
        assert "HERMES_DASHBOARD=0" in run.call_args_list[1].args[0]
        http.return_value.__enter__.return_value.post.assert_called_once()


def test_running_job_blocks_configuration_changes(client):
    import threading

    release = threading.Event()
    job = backend.jobs.manager.submit("Hold deployment", lambda emit: release.wait(2))
    try:
        response = client.post("/setup", json=payload())
        assert response.status_code == 409
        assert not backend.session.manager.exists()
    finally:
        release.set()
        import time

        for _ in range(100):
            if job.finished:
                break
            time.sleep(0.01)


def test_setup_rejects_missing_credentials_and_short_passphrase(client):
    body = payload()
    body["config"]["openai_api_key"] = ""
    assert client.post("/setup", json=body).status_code == 422
    body = payload()
    body["passphrase"] = "short"
    assert client.post("/setup", json=body).status_code == 422
    assert not backend.session.manager.exists()


@pytest.mark.parametrize(
    "channel,values",
    [
        (
            "telegram",
            {
                "telegram_bot_token": "123456789:test-token",
                "telegram_allowed_users": "123456789,987654321",
            },
        ),
        (
            "discord",
            {
                "discord_bot_token": "test-discord-token",
                "discord_allowed_users": "123456789012345678",
            },
        ),
        (
            "slack",
            {
                "slack_bot_token": "xoxb-test-token",
                "slack_app_token": "xapp-test-token",
                "slack_allowed_users": "U012ABCDEF,W012ABCDEF",
            },
        ),
    ],
)
def test_channel_setup_roundtrip_and_compose(client, channel, values):
    body = payload()
    body["config"].update(values)
    with patch.object(SetupService, "setup_streaming", return_value=True):
        response = client.post("/setup", json=body)
        assert response.status_code == 200
        import time

        job = backend.jobs.manager.get(response.json()["job_id"])
        for _ in range(100):
            if job.finished:
                break
            time.sleep(0.01)
    restored = backend.session.manager.load()
    assert restored is not None
    compose = DockerOrchestrator(restored).generate_compose_file()
    for name, value in values.items():
        assert getattr(restored, name) == value
        assert f"{name.upper()}={value}" in compose
        assert value not in backend.session.manager.filepath.read_text()
    loaded = client.post("/config/load", json={"passphrase": body["passphrase"]})
    assert loaded.status_code == 200
    for name, value in values.items():
        assert loaded.json()["config"][name] == value


@pytest.mark.parametrize(
    "values",
    [
        {"slack_bot_token": "xoxb-test"},
        {"slack_app_token": "xapp-test"},
        {"telegram_bot_token": "123:test"},
        {"telegram_bot_token": "bad-format", "telegram_allowed_users": "123"},
        {"discord_bot_token": "test-token", "discord_allowed_users": "@username"},
        {
            "slack_bot_token": "xoxb-test",
            "slack_app_token": "xapp-test",
            "slack_allowed_users": "*",
        },
    ],
)
def test_invalid_channel_settings_are_rejected_before_save(client, values):
    body = payload()
    body["config"].update(values)
    assert client.post("/setup", json=body).status_code == 422
    assert not backend.session.manager.exists()


def test_channel_credentials_can_be_cleared():
    service = SetupService(
        HermesConfig(telegram_bot_token="123:test", telegram_allowed_users="123")
    )
    service.apply_config({"telegram_bot_token": "", "telegram_allowed_users": ""})
    service.config.validate_channels()
    assert service.config.telegram_bot_token is None
    assert service.config.telegram_allowed_users is None
    content = service.orchestrator.generate_compose_file()
    assert "123:test" not in content
    assert "TELEGRAM_BOT_TOKEN=" in content


def test_resetup_requires_unlocking_existing_config(client):
    backend.session.set_passphrase("saved-passphrase")
    backend.session.manager.save(HermesConfig(telegram_bot_token="123:saved-token"))
    before = backend.session.manager.filepath.read_bytes()
    backend.session.config_loaded = False
    response = client.post("/setup", json=payload())
    assert response.status_code == 409
    assert "Unlock" in response.json()["detail"]
    assert backend.session.manager.filepath.read_bytes() == before
