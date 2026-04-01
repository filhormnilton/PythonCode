# ── Business Multi-Agent — Docker image ──────────────────────────────────────
# Multi-stage build to keep the final image lean.
#
# Build:
#   docker build -t business-multiagent .
#
# Run (Teams bot mode):
#   docker run --env-file .env -p 3978:3978 business-multiagent
#
# Run (CLI mode):
#   docker run --env-file .env -it business-multiagent --mode cli
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
COPY business/ ./business/
COPY business_main.py .

# Create output directory and assign ownership
RUN mkdir -p /app/business_output && chown -R appuser:appuser /app

USER appuser

# Expose Teams bot port
EXPOSE 3978

# Default: run as Teams bot server
# Override ENTRYPOINT args to run in other modes:
#   docker run ... --mode cli
#   docker run ... --mode once --request "..."
ENTRYPOINT ["python", "business_main.py"]
CMD ["--mode", "teams"]
