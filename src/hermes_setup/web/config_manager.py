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
        self.filepath = Path(filepath) if filepath else Path.cwd() / self.DEFAULT_FILENAME
        self.passphrase = passphrase
        self._fernet: Fernet | None = None
        self._config_cache: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------

    def set_passphrase(self, passphrase: str) -> None:
        """Set the passphrase and drop any cached cipher.

        The Fernet instance is built from the passphrase, so it has to be
        rebuilt whenever the passphrase changes — otherwise a stale cipher
        would keep decrypting with the *previous* passphrase.
        """
        self.passphrase = passphrase
        self._fernet = None

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
        """Flatten a HermesConfig into a plain dict keyed by field name.

        The web UI form identifies its inputs by field name (``api_port``),
        so the API contract uses field names too.  The encrypted file still
        stores canonical env var names via :meth:`config_to_env_dict`.
        """
        data: dict[str, Any] = {}
        for field_name in type(config).model_fields:
            value = getattr(config, field_name)
            if value is None:
                continue
            data[field_name] = value
        return data

    @staticmethod
    def config_to_env_dict(config: HermesConfig) -> dict[str, Any]:
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
        """Rebuild a HermesConfig from a flat dict.

        Keys may be config field names (``api_port``) or canonical env var
        names (``HERMES_API_PORT``) — the encrypted file uses the latter.
        """
        from ..config import field_name_for_env

        kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key in HermesConfig.model_fields:
                kwargs[key] = value
                continue
            field_name = field_name_for_env(key)
            if field_name is not None:
                kwargs[field_name] = value
        # Build the model directly so the values from the encrypted file are
        # used verbatim, without the process environment or a stray .env
        # file overriding them.
        config = HermesConfig.model_construct(**kwargs)
        return HermesConfig.model_validate(config.model_dump())

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, config: HermesConfig) -> None:
        """Write the configuration to the encrypted file.

        The file stores canonical env var names so it stays portable between
        the web UI, the CLI, and a plain ``.env`` file.
        """
        payload = json.dumps(self.config_to_env_dict(config), indent=2)
        token = self.fernet.encrypt(payload.encode("utf-8"))
        self.filepath.write_text(token.decode("utf-8"), encoding="utf-8")
        self._config_cache = None

    def load(self) -> HermesConfig | None:
        """Load configuration from the encrypted file, or return None.

        Returns None when the file is missing, unreadable, or when no
        passphrase has been supplied yet — the file is encrypted, so it
        cannot be opened before the user provides the passphrase.
        """
        if not self.filepath.exists():
            return None
        if not self.passphrase:
            # Without the passphrase the file cannot be decrypted at all.
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
