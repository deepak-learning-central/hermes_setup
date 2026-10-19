"""Agent state persistence management for Hermes setup.

Handles persistent state across deployments, ensuring that
agent memory and configurations survive container updates.
"""

import datetime
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from hermes_setup.config import HermesConfig


class StateManager:
    """Manages persistent state for Hermes agent deployment."""

    def __init__(self, config: HermesConfig | None = None):
        self.config = config or HermesConfig()
        self.project_root = Path.cwd()
        self.data_dir = self.config.get_data_path()
        self.state_dir = self.data_dir / ".state"
        self.backup_dir = self.data_dir / "backups"
        self.history_file = self.state_dir / "deployment_history.json"

    def ensure_directories(self) -> None:
        """Ensure state directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def save_deployment(
        self,
        image: str,
        action: str,
        notes: str = "",
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Save a deployment record to history."""
        if timestamp is None:
            timestamp = datetime.datetime.now().isoformat()

        record = {
            "timestamp": timestamp,
            "image": image,
            "action": action,
            "notes": notes,
        }

        # Load existing history
        history: list[dict[str, Any]] = []
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    loaded = json.load(f)
                    if isinstance(loaded, list):
                        history = loaded
            except (OSError, json.JSONDecodeError):
                pass

        history.append(record)
        self.ensure_directories()
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)

        return record

    def get_deployment_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent deployment history."""
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file) as f:
                history = json.load(f)
                if isinstance(history, list):
                    return history[-limit:]
        except (OSError, json.JSONDecodeError):
            pass

        return []

    def backup_state(self, reason: str = "") -> Path:
        """Create a backup of current persistent data."""
        timestamp = _timestamp()
        backup_name = f"hermes-backup-{timestamp}"
        target_backup = self.backup_dir / backup_name

        # Copy non-model directories if they exist
        # Exclude backups dir itself to avoid path nesting issues
        excluded_dirs = {self.backup_dir, self.history_file.parent}
        for directory in [self.data_dir, self.config.get_models_path()]:
            if not directory.exists():
                continue
            dest = target_backup / directory.name
            for item in directory.iterdir():
                if item == self.backup_dir:
                    continue
                dest_item = dest / item.name
                if item.is_dir():
                    shutil.copytree(item, dest_item)
                elif item.is_file():
                    shutil.copy2(item, dest_item)

        # Copy state directory
        if self.state_dir.exists():
            shutil.copytree(self.state_dir, target_backup / "state")

        return target_backup

    def restore_backup(self, backup_path: Path | None = None) -> bool:
        """Restore from a backup directory."""
        if not backup_path:
            # Find latest backup
            backups = sorted(
                list(self.backup_dir.glob("hermes-backup-*")),
                reverse=True,
            )
            if not backups:
                return False
            backup_path = backups[0]

        for src_dir in backup_path.iterdir():
            if not src_dir.is_dir():
                continue
            dest_dir = Path.cwd() / src_dir.name
            if dest_dir.exists() and dest_dir != backup_path:
                shutil.rmtree(dest_dir)
            if src_dir.is_dir():
                shutil.copytree(src_dir, dest_dir)

        return True

    def snapshot_volume(self) -> Path | None:
        """Create Docker volume snapshot (requires Docker)."""
        try:
            result = _run_command(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{self.data_dir}:/data",
                    "-v",
                    f"{self.backup_dir}:/backup",
                    "alpine",
                    "tar",
                    "cfz",
                    "/backup/snapshot.tgz",
                    "/data",
                ]
            )
            if result.returncode == 0:
                snapshot = self.backup_dir / "volumesnap.tgz"
                return snapshot
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        return None

    def get_persistent_state_paths(self) -> dict[str, Path]:
        """Return all paths where persistent state is stored."""
        return {
            "data": self.data_dir,
            "state": self.state_dir,
            "backups": self.backup_dir,
            "history": self.history_file,
        }

    def remove_state(self) -> None:
        """Remove all persistent state (dangerous - use with caution)."""
        dirs_to_remove = [
            self.data_dir,
            self.state_dir,
            self.backup_dir,
        ]
        for d in dirs_to_remove:
            if d.exists():
                shutil.rmtree(d)
                d.mkdir(parents=True, exist_ok=True)

        # Reset history file
        if self.history_file.exists():
            self.history_file.unlink()

    @property
    def has_state(self) -> bool:
        """Check if there is any existing persistent state (files, not just empty dirs)."""
        for path in [self.state_dir, self.backup_dir, self.history_file]:
            if path.is_file():
                return True
            if path.is_dir() and any(path.iterdir()):
                return True
        return False

    def generate_state_restore_report(self) -> str:
        """Generate a report of current persistent state."""
        report_lines = ["=== Persistent State Report ==="]
        paths = self.get_persistent_state_paths()
        for name, path in paths.items():
            exists = path.exists()
            size = path.stat().st_size if exists else 0
            report_lines.append(f"{name}: {'EXISTS' if exists else 'NOT FOUND'} ({size} bytes)")
        return "\n".join(report_lines)


def _timestamp() -> str:
    """Generate a timestamp string."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def _run_command(cmd: list) -> subprocess.CompletedProcess:
    """Run a command and return result."""
    return subprocess.run(cmd, capture_output=True, text=True)
