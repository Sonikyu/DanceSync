# Two stages: Node builds web/dist, then a slim Python image with ffmpeg runs
# the API and serves that build from the same origin (server/web.py).

FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build


FROM python:3.11-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY dancesync/ dancesync/
COPY server/ server/
RUN pip install --no-cache-dir -e .
COPY --from=web /web/dist web/dist

# Uploads, catalog, and renders in /data; decoded audio and stretched
# features in /cache. Both are volumes so they survive a rebuild. Created
# here so a fresh named volume starts out owned by the app user.
RUN useradd --create-home dancesync \
    && mkdir -p /data /cache \
    && chown dancesync /data /cache
USER dancesync
ENV DANCESYNC_STORAGE_ROOT=/data \
    DANCESYNC_CACHE_DIR=/cache \
    PORT=8000
VOLUME ["/data", "/cache"]

EXPOSE 8000
# --forwarded-allow-ips: trust the reverse proxy's X-Forwarded-Proto, so the
# sign-in cookie is marked Secure behind HTTPS.
CMD ["sh", "-c", "exec uvicorn server.main:app --host 0.0.0.0 --port \"$PORT\" --forwarded-allow-ips '*'"]
