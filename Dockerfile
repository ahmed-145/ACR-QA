# =============================================================================
# ACR-QA Multi-Stage Dockerfile  v3.8.0
# Stage 1 (node-builder)  — build React dashboard with Vite
# Stage 2 (py-builder)    — install Python deps into a venv
# Stage 3 (go-tools)      — pre-built gosec + staticcheck binaries (no Go compile)
# Stage 4 (runtime)       — lean runtime image, non-root user
# =============================================================================

# ── Stage 1: Dashboard build ──────────────────────────────────────────────────
FROM node:20-slim AS node-builder

WORKDIR /build/dashboard

COPY dashboard/package*.json ./
RUN npm ci --prefer-offline 2>/dev/null || npm ci

COPY dashboard/ .
# outDir is ../FRONTEND/static/dashboard (relative to /build/dashboard)
RUN npm run build

# ── Stage 2: Python dependency builder ───────────────────────────────────────
FROM python:3.11-slim AS py-builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
        ruff==0.6.0 \
        semgrep==1.45.0 \
        vulture==2.10 \
        radon==6.0.1 \
        bandit==1.7.5 \
        alembic==1.13.1

# ── Stage 3: Go security tools (pre-built binaries — no Go compilation) ───────
FROM alpine:3.19 AS go-tools

RUN apk add --no-cache curl tar

RUN curl -sSL \
    https://github.com/securego/gosec/releases/download/v2.18.2/gosec_2.18.2_linux_amd64.tar.gz \
    | tar -xz -C /usr/local/bin gosec

RUN curl -sSL \
    https://github.com/dominikh/go-tools/releases/download/2023.1.3/staticcheck_linux_amd64.tar.gz \
    | tar -xz --strip-components=1 -C /usr/local/bin

# ── Stage 4: Runtime image ────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="ACR-QA" \
      org.opencontainers.image.description="Automated Code Review & Quality Assurance" \
      org.opencontainers.image.version="3.8.0" \
      org.opencontainers.image.source="https://github.com/ahmed-145/ACR-QA"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    nodejs \
    npm \
    git \
    curl \
    && npm install -g eslint eslint-plugin-security --prefix /usr/local \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /root/.npm

COPY --from=py-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=go-tools /usr/local/bin/gosec /usr/local/bin/gosec
COPY --from=go-tools /usr/local/bin/staticcheck /usr/local/bin/staticcheck

RUN groupadd -r acrqa && useradd -r -g acrqa -d /app -s /sbin/nologin acrqa

WORKDIR /app

COPY . .

# Copy pre-built dashboard from node-builder stage
COPY --from=node-builder /build/FRONTEND/static/dashboard /app/FRONTEND/static/dashboard

RUN mkdir -p DATA/outputs DATA/provenance DATA/reports \
    && chmod +x TOOLS/*.sh 2>/dev/null || true \
    && chown -R acrqa:acrqa /app

USER acrqa

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD ["uvicorn", "FRONTEND.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
