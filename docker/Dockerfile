# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Copy application source (required for uv to build the local package)
COPY src/ ./src/

# Copy README for uv_build
COPY README.md ./

# Copy Docker Compose files
COPY docker/ ./docker/

# Copy config
COPY docker/hermes/ ./config/

# Build stage
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r hermes -g 1000 \
    && useradd -r -g hermes -u 1000 -m -d /app hermes

# Copy uv from builder
COPY --from=builder /uv /uvx /bin/

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/ ./src/
COPY docker/hermes/ ./config/

# Set ownership
RUN chown -R hermes:hermes /app

# Switch to non-root user
USER hermes

# Environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -f http://localhost:8000/health || exit 1

# Entry point
ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["python", "-m", "hermes_setup.tui"]
