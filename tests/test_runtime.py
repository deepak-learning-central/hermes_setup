"""Exercise the actual container bootstrap without Docker or real credentials."""

import json
import sys
from types import SimpleNamespace

from hermes_setup.web.runtime import BOOTSTRAP_SCRIPT, CHANNEL_ENV_KEYS


def bootstrap(tmp_path, monkeypatch, token):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    for key in CHANNEL_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "123456789" if token else "")
    # JSON is valid YAML. Substitute the codec, executing the same filesystem
    # and environment logic sent to the upstream image.
    monkeypatch.setitem(
        sys.modules, "hermes_yaml", SimpleNamespace(safe_load=json.loads, safe_dump=json.dumps)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bootstrap",
            json.dumps({"model": {"default": "test-model"}}),
            json.dumps(CHANNEL_ENV_KEYS),
        ],
    )
    exec(BOOTSTRAP_SCRIPT, {})


def read_profile(path):
    return {
        key: json.loads(value)
        for line in path.read_text().splitlines()
        if "=" in line and not line.startswith("#")
        for key, value in [line.split("=", 1)]
    }


def test_credentials_survive_process_environment_loss(tmp_path, monkeypatch, capsys):
    token = "123456789:test-token"
    bootstrap(tmp_path, monkeypatch, token)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    monkeypatch.delenv("TELEGRAM_ALLOWED_USERS")
    # A new process/profile can load these without the launch environment.
    saved = read_profile(tmp_path / ".env")
    assert saved["TELEGRAM_BOT_TOKEN"] == token
    assert saved["TELEGRAM_ALLOWED_USERS"] == "123456789"
    assert (tmp_path / ".env").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "config.yaml").stat().st_mode & 0o777 == 0o600
    assert token not in capsys.readouterr().out
    assert token not in BOOTSTRAP_SCRIPT


def test_reconfiguration_preserves_unrelated_settings_and_replaces_tokens(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        '# Keep this comment\nOTHER_API_KEY="keep-me"\nexport TELEGRAM_BOT_TOKEN="old"\nTELEGRAM_BOT_TOKEN="duplicate"\n'
    )
    (tmp_path / "config.yaml").write_text(json.dumps({"custom": {"preserved": True}}))
    bootstrap(tmp_path, monkeypatch, "123:new-token")
    text = (tmp_path / ".env").read_text()
    assert text.count("TELEGRAM_BOT_TOKEN=") == 1
    assert "# Keep this comment" in text
    assert read_profile(tmp_path / ".env")["OTHER_API_KEY"] == "keep-me"
    assert json.loads((tmp_path / "config.yaml").read_text())["custom"]["preserved"] is True
    bootstrap(tmp_path, monkeypatch, "")
    assert read_profile(tmp_path / ".env")["TELEGRAM_BOT_TOKEN"] == ""
    assert "123:new-token" not in (tmp_path / ".env").read_text()
