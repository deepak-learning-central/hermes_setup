"""Tests for the encrypted config manager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_setup.config import HermesConfig
from hermes_setup.web.config_manager import EncryptedConfigManager


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    return tmp_path / ".hermes-config.enc"


def test_save_and_load_roundtrip(config_file: Path) -> None:
    """A saved config should load back with identical values."""
    manager = EncryptedConfigManager(config_file, passphrase="correct horse battery")
    config = HermesConfig(host_port=9001, model_name="test/model", temperature=0.42)
    manager.save(config)

    assert config_file.exists()
    assert manager.exists()

    loaded = manager.load()
    assert loaded is not None
    assert loaded.host_port == 9001
    assert loaded.model_name == "test/model"
    assert loaded.temperature == pytest.approx(0.42)


def test_file_contents_are_not_plaintext(config_file: Path) -> None:
    """Secrets must not appear in the raw file contents."""
    manager = EncryptedConfigManager(config_file, passphrase="hunter2")
    config = HermesConfig(openai_api_key="sk-super-secret-value")
    manager.save(config)

    raw = config_file.read_text()
    assert "sk-super-secret-value" not in raw
    assert "openai_api_key" not in raw


def test_wrong_passphrase_fails_to_load(config_file: Path) -> None:
    """Decrypting with the wrong passphrase should not raise."""
    EncryptedConfigManager(config_file, passphrase="right").save(HermesConfig())

    wrong = EncryptedConfigManager(config_file, passphrase="wrong")
    assert wrong.load() is None


def test_missing_file_returns_none(tmp_path: Path) -> None:
    """Loading a nonexistent file should return None rather than raise."""
    manager = EncryptedConfigManager(tmp_path / "absent.enc", passphrase="x")
    assert manager.load() is None
    assert manager.exists() is False


def test_config_to_dict_uses_env_var_names(config_file: Path) -> None:
    """Exported keys should be env var names, not field names."""
    manager = EncryptedConfigManager(config_file, passphrase="x")
    data = manager.config_to_dict(HermesConfig(host_port=1234))
    assert data["HERMES_HOST_PORT"] == 1234
    assert "host_port" not in data


def test_dict_to_config_roundtrip(config_file: Path) -> None:
    """A flat env dict should rebuild an equivalent config."""
    manager = EncryptedConfigManager(config_file, passphrase="x")
    original = HermesConfig(host_port=7000, log_level="DEBUG")
    restored = manager.dict_to_config(manager.config_to_dict(original))

    assert restored.host_port == 7000
    assert restored.log_level == "DEBUG"


def test_payload_is_valid_json_when_decrypted(config_file: Path) -> None:
    """The decrypted payload should be readable JSON."""
    manager = EncryptedConfigManager(config_file, passphrase="pw")
    manager.save(HermesConfig(host_port=8080))

    from cryptography.fernet import Fernet

    key = Fernet(manager._derive_key("pw"))
    payload = key.decrypt(config_file.read_bytes()).decode()
    assert json.loads(payload)["HERMES_HOST_PORT"] == 8080


def test_remove_deletes_file(config_file: Path) -> None:
    """remove() should delete the encrypted file."""
    manager = EncryptedConfigManager(config_file, passphrase="x")
    manager.save(HermesConfig())
    assert config_file.exists()

    manager.remove()
    assert not config_file.exists()
