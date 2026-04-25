# ============================================================================
# Analytics Processor Dockerfile — Azure Functions on Container Apps
#
# Build context MUST be the repository root:
#   docker build -t analytics-processor -f src/analytics-processor/Dockerfile .
# ============================================================================

# Build stage
FROM mcr.microsoft.com/azure-functions/python:4-python3.14 AS builder

WORKDIR /home/site/wwwroot

# Install UV (copy standalone binary from official image)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (cache layer)
COPY src/analytics-processor/pyproject.toml ./
# Install uv.lock if it exists; otherwise generate it
COPY src/analytics-processor/uv.lock* ./

# Install dependencies into the path the Azure Functions host expects.
# The base image sets PYTHONPATH to .python_packages/lib/site-packages and
# the worker uses /opt/python/3/bin/python3, so packages MUST go here
# (NOT into a .venv which the host cannot see).
RUN uv export --frozen --no-dev --no-emit-project 2>/dev/null > /tmp/requirements.txt || \
    uv export --no-dev --no-emit-project > /tmp/requirements.txt && \
    uv pip install --no-cache --target .python_packages/lib/site-packages -r /tmp/requirements.txt

# Copy source code
COPY src/analytics-processor/function_app.py src/analytics-processor/host.json ./
COPY src/analytics-processor/analytics_processor/ analytics_processor/

# Install the project itself into the same target
RUN uv pip install --no-cache --no-deps --target .python_packages/lib/site-packages .

# Compile Python files
RUN /opt/python/3/bin/python3 -m compileall -b .

# Production stage
FROM mcr.microsoft.com/azure-functions/python:4-python3.14 AS production

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

WORKDIR /home/site/wwwroot

# Copy installed packages and code from builder
COPY --from=builder /home/site/wwwroot/.python_packages /home/site/wwwroot/.python_packages
COPY --from=builder /home/site/wwwroot/function_app.py /home/site/wwwroot/function_app.py
COPY --from=builder /home/site/wwwroot/host.json /home/site/wwwroot/host.json
COPY --from=builder /home/site/wwwroot/analytics_processor /home/site/wwwroot/analytics_processor

# Run as non-root (the Azure Functions base image provides UID 1000)
USER 1000
