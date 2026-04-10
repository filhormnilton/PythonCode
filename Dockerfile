# ── Business Multi-Agent — Docker image ──────────────────────────────────────
# Multi-stage build to keep the final image lean.
#
# Build:
#   docker build -t business-multiagent .
#
# Run (REST API mode — for Azure App Service / Container Apps):
#   docker run --env-file .env -p 8000:8000 business-multiagent
#
# Run (Teams bot mode):
#   docker run --env-file .env -p 3978:3978 business-multiagent \
#       python business_main.py --mode teams
#
# Run (CLI mode):
#   docker run --env-file .env -it business-multiagent \
#       python business_main.py --mode cli
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools only in the builder stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY Business/ ./Business/
COPY business_main.py .
COPY api_server.py .

# Create output directory and assign ownership
RUN mkdir -p /app/business_output && chown -R appuser:appuser /app

USER appuser

# Expose REST API port
EXPOSE 8000

# Default: run as REST API server (Azure App Service / Container Apps)
# Override CMD to run in other modes.
ENTRYPOINT ["python", "api_server.py"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
