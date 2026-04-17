# ============================================================================
# BFF Dockerfile - Multi-stage build for Python FastAPI application
#
# Build context MUST be the repository root so that the shared
# ``src/apic_client`` package is accessible.
#   docker build -t bff -f src/bff/Dockerfile .
# ============================================================================

# Build stage
FROM python:3.14-slim AS builder

WORKDIR /app

# Install UV
RUN pip install --no-cache-dir uv

# Copy the shared apic_client package first (rarely changes → caches well)
COPY src/apic_client /apic_client

# Copy BFF dependency files
COPY src/bff/pyproject.toml src/bff/uv.lock ./

# Install the shared package into the venv, then BFF deps.
# --no-install-project because source isn't copied yet.
RUN uv sync --frozen --no-dev --no-install-project

# Copy BFF source code
COPY src/bff/ .

# Install the project itself now that source is available
RUN uv sync --frozen --no-dev

# Compile Python files
RUN python -m compileall -b .

# Production stage
FROM python:3.14-slim AS production

WORKDIR /app

# Upgrade OS packages to pick up any available security patches, then
# remove pip (not needed at runtime) to reduce attack surface.
RUN apt-get update && \
    apt-get upgrade -y && \
    pip uninstall -y pip setuptools 2>/dev/null; \
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

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

# Set user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "apic_vibe_portal_bff.main:app", "--host", "0.0.0.0", "--port", "8000"]
