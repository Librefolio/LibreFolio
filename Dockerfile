# =============================================================================
# LibreFolio — Runtime-only Docker Image
# =============================================================================
# Build frontend and docs on host BEFORE building the Docker image:
#   ./dev.py front build
#   ./dev.py mkdocs build
#   docker build -t librefolio .
#
# Prefer `./dev.py docker build` — it also regenerates requirements.txt and
# VERSION (used below) automatically, on top of the above.
#
# Variants (build-arg DOCS_VARIANT=full|light, default: full):
#   full  — complete image, documentation images included (docs work offline)
#   light — documentation text pages only; doc images (gallery screenshots,
#           hundreds of MB) are excluded and loaded on demand from the online
#           docs site → viewing them requires an internet connection.
# =============================================================================

# Declared before the first FROM so it can select the docs stage below.
ARG DOCS_VARIANT=full

# --- Documentation stages ---------------------------------------------------
# The pre-built docs site is COPYed into an intermediate stage so the "light"
# variant can prune the image files BEFORE they reach the final image: a
# `RUN rm` after a COPY in the final stage would NOT shrink the image, because
# the files would still exist in the earlier layer.
FROM python:3.13-slim AS docs-full
COPY mkdocs_src/site/ /site/

FROM python:3.13-slim AS docs-light
COPY mkdocs_src/site/ /site/
# Strip documentation images — the weight is in the gallery screenshots.
# Text pages are kept; missing images fall back to the online docs site
# (mkdocs_src/docs/javascripts/gallery-img-loader.js → GitHub Pages).
RUN find /site/gallery -type f \( \
        -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \
        -o -iname '*.gif' -o -iname '*.webp' -o -iname '*.svg' \
        -o -iname '*.mp4' \
    \) -delete

FROM docs-${DOCS_VARIANT} AS docs

FROM python:3.13-slim

# System dependencies
#   - gcc, libffi-dev: build native Python extensions
#   - git: needed for justetf-scraping pip dependency
#   - gosu: privilege drop in entrypoint (like postgres/mysql/redis images)
#   - sqlite3: CLI for manual DB inspection / ad-hoc one-off fixes on a prod
#     volume. Schema migrations are now applied automatically at startup — the
#     app runs `alembic upgrade head` in its lifespan (see backend/app/main.py::
#     ensure_database_exists), so upgrading the image over an existing data
#     volume no longer needs manual migration; sqlite3 stays for inspection only.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev git gosu sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy pre-generated requirements (created by ./dev.py docker build)
COPY requirements.txt ./

# Install Python dependencies (system-wide, no virtualenv in Docker)
# --mount=type=cache persists downloaded wheels across builds on the host.
# Only packages with new versions are re-downloaded; unchanged ones are instant.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt && \
    pip install uvicorn[standard]

# Copy application code
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY dev.py ./

# Copy manifests used by the "System Info" endpoint (backend/frontend dependency
# listing shown in Settings > About) — NOT node_modules, just the small source
# files. See dev.py::_docker_ensure_assets_built() for VERSION generation.
COPY Pipfile ./
COPY frontend/package.json ./frontend/package.json
COPY VERSION ./

# Copy pre-built frontend (must run ./dev.py front build on host first)
COPY frontend/build/ ./frontend/build/

# Copy pre-built docs (must run ./dev.py mkdocs build on host first).
# Comes from the DOCS_VARIANT-selected stage above: "light" has no doc images.
COPY --from=docs /site/ ./mkdocs_src/site/

# Copy environment config
COPY .env.example ./.env

# Copy license + third-party attributions. Required by the BSD/MIT/NCSA/Apache
# clauses of the bundled Python packages, which mandate that their copyright
# notices travel with any binary redistribution — this image is one.
COPY LICENSE THIRD_PARTY_LICENSES.md ./

# Create non-root user (default UID/GID 1000:1000).
# Override at build time: docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) .
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} librefolio 2>/dev/null || true && \
    useradd -u ${UID} -g ${GID} -m -s /bin/bash librefolio 2>/dev/null || true && \
    chown -R ${UID}:${GID} /app

# Entrypoint: fix bind-mount permissions then drop to non-root via gosu
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default environment
ENV HOST=0.0.0.0 \
    PORT=6040 \
    LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker \
    LOG_LEVEL=INFO \
    PORTFOLIO_BASE_CURRENCY=EUR

EXPOSE 6040 6041

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/v1/system/health')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "6040"]

