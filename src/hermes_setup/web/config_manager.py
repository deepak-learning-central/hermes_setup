"""Encrypted configuration file persistence for the web setup UI.

All configuration values are persisted to an encrypted file on the target
machine.  The file is never committed to the repository — it lives next to
the setup project (or in a user-chosen location) and can be re-opened later
for modifications.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from ..config import HermesConfig, env_field_name


class EncryptedConfigManager:
    """Save and load Hermes configuration in an encrypted local file.

    The encryption key is derived from a user-supplied passphrase so that
    secrets (API keys, channel tokens) never sit in plain text on disk.
    """

    DEFAULT_FILENAME = ".hermes-config.enc"

    def __init__(
        self,
        filepath: Path | None = None,
        passphrase: str | None = None,
    ) -> None:
        self.filepath = filepath or Path.cwd() / self.DEFAULT_FILENAME
        self.passphrase = passphrase
        self._fernet: Fernet | None = None
        self._config_cache: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------

    def _derive_key(self, passphrase: str) -> bytes:
        """Derive a Fernet-compatible key from a passphrase."""
        digest = hashlib.sha256(passphrase.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    @property
    def fernet(self) -> Fernet:
        """Lazily build the Fernet instance from the passphrase."""
        if self._fernet is None:
            if not self.passphrase:
                raise ValueError("Passphrase is required to use encrypted config")
            self._fernet = Fernet(self._derive_key(self.passphrase))
        return self._fernet

    # ------------------------------------------------------------------
    # Config <-> dict helpers
    # ------------------------------------------------------------------

    @staticmethod
    def config_to_dict(config: HermesConfig) -> dict[str, Any]:
        """Flatten a HermesConfig into a plain dict keyed by env var name."""
        data: dict[str, Any] = {}
        for field_name in type(config).model_fields:
            value = getattr(config, field_name)
            if value is None:
                continue
            data[env_field_name(field_name)] = value
        return data

    @staticmethod
    def dict_to_config(data: dict[str, Any]) -> HermesConfig:
        """Rebuild a HermesConfig from a flat dict of env var values."""
        from ..config import field_name_for_env

        kwargs = {}
        for env_key, value in data.items():
            field_name = field_name_for_env(env_key)
            if field_name is not None:
                kwargs[field_name] = value
        return HermesConfig(_env_file=None, **kwargs)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, config: HermesConfig) -> None:
        """Write the configuration to the encrypted file."""
        payload = json.dumps(self.config_to_dict(config), indent=2)
        token = self.fernet.encrypt(payload.encode("utf-8"))
        self.filepath.write_text(token.decode("utf-8"), encoding="utf-8")
        self._config_cache = None

    def load(self) -> HermesConfig | None:
        """Load configuration from the encrypted file, or return None if missing."""
        if not self.filepath.exists():
            return None
        try:
            token = self.filepath.read_text(encoding="utf-8")
            payload = self.fernet.decrypt(token.encode("utf-8"))
            data = json.loads(payload.decode("utf-8"))
            return self.dict_to_config(data)
        except (InvalidToken, json.JSONDecodeError, OSError):
            return None

    def exists(self) -> bool:
        """Return True if an encrypted config file already exists."""
        return self.filepath.exists()

    def remove(self) -> None:
        """Delete the encrypted config file if present."""
        if self.filepath.exists():
            self.filepath.unlink()
