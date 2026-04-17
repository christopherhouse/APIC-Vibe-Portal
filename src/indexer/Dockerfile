# ============================================================================
# Indexer Dockerfile — Azure Container Job for AI Search reindexing
#
# Build context MUST be the repository root so that the shared
# ``src/apic_client`` package is accessible.
#   docker build -t indexer -f src/indexer/Dockerfile .
# ============================================================================

# Build stage
FROM python:3.14-slim AS builder

WORKDIR /app

# Install UV
RUN pip install --no-cache-dir uv

# Copy the shared apic_client package first (rarely changes → caches well)
COPY src/apic_client /apic_client

# Copy indexer dependency files
COPY src/indexer/pyproject.toml src/indexer/uv.lock ./

# Install locked runtime dependencies into a virtual environment.
# --no-install-project: skip installing the project itself (source not yet
#   copied); this layer is cached as long as the lockfile is unchanged.
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY src/indexer/ .

# Install the project itself now that source is available
RUN uv sync --frozen --no-dev

# Compile Python files
RUN .venv/bin/python -m compileall -b .

# Production stage
FROM python:3.14-slim AS production

WORKDIR /app

# Upgrade OS packages and remove pip to reduce attack surface
RUN apt-get update && \
    apt-get upgrade -y && \
    pip uninstall -y pip setuptools 2>/dev/null && \
    rm -rf /usr/local/lib/python*/site-packages/pip* \
           /usr/local/lib/python*/site-packages/setuptools* \
           /usr/local/bin/pip* && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1001 -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# Copy the shared apic_client source (editable install references /apic_client)
COPY --from=builder --chown=appuser:appuser /apic_client /apic_client

# Copy virtual environment and compiled code from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app /app

# Runtime environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

USER appuser

# Container jobs run to completion — no HEALTHCHECK needed
CMD ["python", "main.py"]
