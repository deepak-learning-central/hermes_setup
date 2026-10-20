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

# ---------------------------------------------------------------------------
# TODO: SSH-based production deployment
# ---------------------------------------------------------------------------
# The current CD pipeline only builds and verifies the image on GitHub's
# ephemeral runner — it never deploys to a real server. To make it a true
# production deployment, add an SSH deploy step to .github/workflows/cd.yml:
#
#   - name: Deploy to production host
#     uses: appleboy/ssh-action@v1
#     with:
#       host: ${{ secrets.PROD_HOST }}
#       username: ${{ secrets.PROD_USER }}
#       key: ${{ secrets.PROD_SSH_KEY }}
#       script: |
#         docker pull ghcr.io/${{ github.actor }}/hermes-setup:latest
#         docker compose -f docker/compose.prod.yml up -d
#
# This would pull the freshly-published image onto your actual server and
# restart the container there. Requires PROD_HOST, PROD_USER, and PROD_SSH_KEY
# secrets, plus SSH key access on the target host.
# ---------------------------------------------------------------------------
