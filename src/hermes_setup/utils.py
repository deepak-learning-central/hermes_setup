"""Utility functions for Hermes agent setup."""

import hashlib
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def is_docker_available() -> bool:
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def is_docker_compose_available() -> bool:
    """Check if Docker Compose is available."""
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_system_info() -> dict[str, str]:
    """Get system information for diagnostics."""
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version.split()[0],
        "hostname": socket.gethostname(),
    }


def validate_port(port: int) -> bool:
    """Validate that a port number is valid."""
    return 1 <= port <= 65535


def is_port_in_use(port: int, host: str = "localhost") -> bool:
    """Check if a port is already in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except OSError:
        return False


def find_available_port(start_port: int = 8000, max_attempts: int = 100) -> int | None:
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if validate_port(port) and not is_port_in_use(port):
            return port
    return None


def hash_file(filepath: Path, algorithm: str = "sha256") -> str | None:
    """Compute hash of a file."""
    try:
        hash_obj = hashlib.new(algorithm)
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except (FileNotFoundError, ValueError):
        return None


def read_env_file(filepath: Path) -> dict[str, str]:
    """Parse a .env file into a dictionary."""
    env_vars = {}
    if not filepath.exists():
        return env_vars

    with open(filepath, encoding="utf-8") as f:
        for _line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            # Remove quotes if present
            if (
                value.startswith('"')
                and value.endswith('"')
                or value.startswith("'")
                and value.endswith("'")
            ):
                value = value[1:-1]
            env_vars[key] = value
    return env_vars


def write_env_file(filepath: Path, env_vars: dict[str, str]) -> None:
    """Write environment variables to a .env file."""
    with open(filepath, "w", encoding="utf-8") as f:
        for key, value in sorted(env_vars.items()):
            f.write(f"{key}={value}\n")


def merge_env_files(*files: Path) -> dict[str, str]:
    """Merge multiple .env files (later files override earlier ones)."""
    merged: dict[str, str] = {}
    for file in files:
        if file.exists():
            merged.update(read_env_file(file))
    return merged


def validate_required_env(required: list[str], env: dict[str, str]) -> tuple[list[str], list[str]]:
    """Check for required environment variables."""
    present = [var for var in required if var in env and env[var]]
    missing = [var for var in required if var not in env or not env[var]]
    return present, missing


def truncate_string(text: str, max_length: int = 100) -> str:
    """Truncate string to max_length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def format_bytes(bytes_count: int) -> str:
    """Format byte count into human readable form."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"


def run_with_spinner(message: str, func) -> Any:
    """Run a function with a spinner message (for CLI feedback)."""
    import itertools
    import threading

    spinner = itertools.cycle(["-", "\\", "|", "/"])
    done = False
    result = [None]
    error = [None]

    def worker():
        try:
            result[0] = func()
        except Exception as e:
            error[0] = e
        finally:
            nonlocal done
            done = True

    thread = threading.Thread(target=worker)
    thread.start()

    while not done:
        sys.stdout.write(f"\r{message} {next(spinner)}")
        sys.stdout.flush()
        time.sleep(0.1)

    sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")
    sys.stdout.flush()

    if error[0]:
        raise error[0]
    return result[0]


def parse_bool(value: Any) -> bool:
    """Parse various truthy/falsy values to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_container_id_from_name(name: str) -> str | None:
    """Get container ID from container name."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-aqf", f"name={name}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")[0]
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def container_exists(name: str) -> bool:
    """Check if a container exists."""
    return get_container_id_from_name(name) is not None


def container_running(name: str) -> bool:
    """Check if a container is running."""
    container_id = get_container_id_from_name(name)
    if not container_id:
        return False
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format={{.State.Running}}", container_id],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except (subprocess.SubprocessError, FileNotFoundError):
        return False
