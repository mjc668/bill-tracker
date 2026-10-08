# syntax=docker/dockerfile:1

# --- Frontend build ---------------------------------------------------------
FROM docker.io/library/node:22-bookworm-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG NEXT_PUBLIC_APP_VERSION=dev
ARG NEXT_PUBLIC_SESSION_HEARTBEAT_SECONDS=180
ENV NEXT_PUBLIC_APP_VERSION=$NEXT_PUBLIC_APP_VERSION \
    NEXT_PUBLIC_SESSION_HEARTBEAT_SECONDS=$NEXT_PUBLIC_SESSION_HEARTBEAT_SECONDS
RUN npm run build

# --- Backend build ----------------------------------------------------------
FROM docker.io/library/python:3.13-slim AS backend-build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --frozen
COPY backend/ ./

# --- Runtime ----------------------------------------------------------------
FROM docker.io/library/python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    API_PREFIX=/api

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libstdc++6 tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "supervisor==4.2.5" "setuptools<81"

COPY --from=docker.io/library/node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node

WORKDIR /
COPY --from=backend-build /backend /backend
COPY --from=frontend-build /frontend/.next/standalone /frontend
COPY --from=frontend-build /frontend/.next/static /frontend/.next/static
COPY --from=frontend-build /frontend/public /frontend/public
# Demo seeder runs from the same image (compose `demo` profile).
COPY demo /app/demo
COPY docker/entrypoint.sh /entrypoint.sh

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /backend /frontend /app /data \
    && chmod +x /entrypoint.sh

EXPOSE 3010
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:3010/', timeout=4).status < 500 else 1)"

ENTRYPOINT ["/entrypoint.sh"]
