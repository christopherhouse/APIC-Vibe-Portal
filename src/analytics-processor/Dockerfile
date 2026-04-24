# ============================================================================
# Analytics Processor Dockerfile — Azure Functions on Container Apps
#
# Build context MUST be src/analytics-processor:
#   docker build -t analytics-processor src/analytics-processor
# ============================================================================

# Build stage
FROM mcr.microsoft.com/azure-functions/python:4-python3.14 AS builder

WORKDIR /home/site/wwwroot

# Install UV
RUN pip install --no-cache-dir uv

# Copy dependency files first (cache layer)
COPY pyproject.toml ./
# Install uv.lock if it exists; otherwise generate it
COPY uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project 2>/dev/null || uv sync --no-dev --no-install-project

# Copy source code
COPY function_app.py host.json ./
COPY analytics_processor/ analytics_processor/

# Install the project itself
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

# Compile Python files
RUN .venv/bin/python -m compileall -b .

# Production stage
FROM mcr.microsoft.com/azure-functions/python:4-python3.14 AS production

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

WORKDIR /home/site/wwwroot

# Copy virtual environment and compiled code from builder
COPY --from=builder /home/site/wwwroot/.venv /home/site/wwwroot/.venv
COPY --from=builder /home/site/wwwroot/function_app.py /home/site/wwwroot/function_app.py
COPY --from=builder /home/site/wwwroot/host.json /home/site/wwwroot/host.json
COPY --from=builder /home/site/wwwroot/analytics_processor /home/site/wwwroot/analytics_processor

# Set the virtual environment as the Python path
ENV PATH="/home/site/wwwroot/.venv/bin:$PATH"

# Run as non-root (the Azure Functions base image provides UID 1000)
USER 1000
