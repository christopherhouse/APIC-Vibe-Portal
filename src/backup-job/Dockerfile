# ============================================================================
# Backup Job Dockerfile — Azure Container Job for API Center backups
#
# Build context MUST be the repository root so that the shared
# ``src/apic_client`` package is accessible.
#   docker build -t backup-job -f src/backup-job/Dockerfile .
# ============================================================================

# Build stage
FROM python:3.14-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY src/apic_client /apic_client

COPY src/backup-job/pyproject.toml src/backup-job/uv.lock* ./

RUN uv sync --frozen --no-dev --no-install-project || uv sync --no-dev --no-install-project

COPY src/backup-job/ .

RUN uv sync --frozen --no-dev || uv sync --no-dev

RUN .venv/bin/python -m compileall -b .

# Production stage
FROM python:3.14-slim AS production

WORKDIR /app

RUN apt-get update && \
    apt-get upgrade -y && \
    pip uninstall -y pip setuptools 2>/dev/null && \
    rm -rf /usr/local/lib/python*/site-packages/pip* \
           /usr/local/lib/python*/site-packages/setuptools* \
           /usr/local/bin/pip* && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1001 -s /bin/bash appuser && \
    chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /apic_client /apic_client
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

USER appuser

CMD ["python", "main.py"]
