"""Hermes agent setup package.

A portable, credential-free setup for deploying the Hermes agent
(Nous Research personal assistant) using Docker and Python.
"""

__version__ = "0.1.0"

from .cli import main
from .config import HermesConfig
from .docker import DockerOrchestrator
from .secrets import SecretsManager
from .state import StateManager

__all__ = ["HermesConfig", "DockerOrchestrator", "SecretsManager", "StateManager", "main"]

# Web UI backend (imports optional — only loaded when the web command runs)
try:
    from .web.backend import app  # noqa: F401

    __all__.append("app")
except ImportError:
    pass
