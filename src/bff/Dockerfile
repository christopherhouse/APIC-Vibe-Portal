# ============================================================================
# BFF Dockerfile - Multi-stage build for Python FastAPI application
# ============================================================================

# Build stage
FROM python:3.14-slim AS builder

WORKDIR /app

# Install UV
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies only (creates .venv, skip project install since source isn't copied yet)
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY . .

# Install the project itself now that source is available
RUN uv sync --frozen --no-dev

# Compile Python files
RUN python -m compileall -b .

# Production stage
FROM python:3.14-slim AS production

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1001 -s /bin/bash appuser && \
    chown -R appuser:appuser /app

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
