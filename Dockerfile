# =============================================================================
# ACR-QA Multi-Stage Dockerfile
# Stage 1 (builder)  — install Python deps into a venv, no build tools in final image
# Stage 2 (go-tools) — compile gosec + staticcheck from source
# Stage 3 (runtime)  — lean runtime image, non-root user, no build artifacts
# =============================================================================

# ── Stage 1: Python dependency builder ───────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Build-only system deps (gcc / libpq-dev needed to compile psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create venv — everything lives here, easy to copy to runtime stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    # Static analysis tools pinned to same versions as requirements.txt
    && pip install --no-cache-dir \
        ruff==0.6.0 \
        semgrep==1.45.0 \
        vulture==2.10 \
        radon==6.0.1 \
        bandit==1.7.5 \
        alembic==1.13.1

# ── Stage 2: Go security tools ────────────────────────────────────────────────
FROM golang:1.22-alpine AS go-tools

RUN go install github.com/securego/gosec/v2/cmd/gosec@v2.18.2 \
    && go install honnef.co/go/tools/cmd/staticcheck@v0.4.3

# ── Stage 3: Runtime image ────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="ACR-QA" \
      org.opencontainers.image.description="Automated Code Review & Quality Assurance" \
      org.opencontainers.image.version="3.2.4" \
      org.opencontainers.image.source="https://github.com/ahmed-145/ACR-QA"

# Runtime-only system deps — NO gcc, NO python3-dev
# libpq5   → psycopg2 shared library
# nodejs   → ESLint (JS/TS analysis)
# npm      → ESLint plugin installation
# git      → --diff-only mode (changed-files detection)
# curl     → HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    nodejs \
    npm \
    git \
    curl \
    && npm install -g eslint eslint-plugin-security --prefix /usr/local \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /root/.npm

# Copy Python venv from builder (contains all pip packages + analysis tools)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy Go binaries from go-tools stage
COPY --from=go-tools /go/bin/gosec /usr/local/bin/gosec
COPY --from=go-tools /go/bin/staticcheck /usr/local/bin/staticcheck

# Create non-root user — runs with minimal privileges
RUN groupadd -r acrqa && useradd -r -g acrqa -d /app -s /sbin/nologin acrqa

WORKDIR /app

# Copy application source
COPY . .

# Create runtime data directories and fix ownership in one layer
RUN mkdir -p DATA/outputs DATA/provenance DATA/reports \
    && chmod +x TOOLS/*.sh 2>/dev/null || true \
    && chown -R acrqa:acrqa /app

# Drop to non-root
USER acrqa

EXPOSE 5000

# Health check — verifies Flask API is alive
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:5000/api/health || exit 1

# Default: run the Flask dashboard
# Override with: docker run ... python3 CORE/main.py --target-dir /repo
CMD ["python3", "FRONTEND/app.py"]
