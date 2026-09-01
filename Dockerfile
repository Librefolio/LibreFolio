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

# --- Python builder stage ----------------------------------------------------
# pip builds some packages from source (gcc, libffi headers) and installs one
# dependency from a git URL (git). Those toolchain packages add ~200 MB and are
# useless at runtime, so the install happens here and only /install is copied
# into the final image.
FROM python:3.13-slim AS pybuilder
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements.txt ./
# --mount=type=cache persists downloaded wheels across builds on the host.
# Only packages with new versions are re-downloaded; unchanged ones are instant.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.txt && \
    pip install --prefix=/install uvicorn[standard]

FROM python:3.13-slim

# Non-root user (overridable at build time). Declared up here because every
# COPY into /app uses --chown=${UID}:${GID} (see the note at requirements.txt).
ARG UID=1000
ARG GID=1000

# System dependencies (runtime only — the pip toolchain lives in pybuilder):
#   - gosu: privilege drop in entrypoint (like postgres/mysql/redis images)
#   - sqlite3: CLI for manual DB inspection / ad-hoc one-off fixes on a prod
#     volume. Schema migrations are now applied automatically at startup — the
#     app runs `alembic upgrade head` in its lifespan (see backend/app/main.py::
#     ensure_database_exists), so upgrading the image over an existing data
#     volume no longer needs manual migration; sqlite3 stays for inspection only.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gosu sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies from the builder stage
COPY --from=pybuilder /install /usr/local

# Copy pre-generated requirements (created by ./dev.py docker build)
# NOTE: every COPY into /app carries --chown=${UID}:${GID} — a single
# `RUN chown -R /app` at the end would create a duplicate layer holding a
# second copy of every file (it added ~300 MB of docs alone, twice).
COPY --chown=${UID}:${GID} requirements.txt ./

# Copy application code
COPY --chown=${UID}:${GID} backend/ ./backend/
COPY --chown=${UID}:${GID} scripts/ ./scripts/
COPY --chown=${UID}:${GID} dev.py ./

# Copy manifests used by the "System Info" endpoint (backend/frontend dependency
# listing shown in Settings > About) — NOT node_modules, just the small source
# files. See dev.py::_docker_ensure_assets_built() for VERSION generation.
COPY --chown=${UID}:${GID} Pipfile ./
COPY --chown=${UID}:${GID} frontend/package.json ./frontend/package.json
COPY --chown=${UID}:${GID} VERSION ./

# Copy pre-built frontend (must run ./dev.py front build on host first)
COPY --chown=${UID}:${GID} frontend/build/ ./frontend/build/

# Copy pre-built docs (must run ./dev.py mkdocs build on host first).
# Comes from the DOCS_VARIANT-selected stage above: "light" has no doc images.
COPY --chown=${UID}:${GID} --from=docs /site/ ./mkdocs_src/site/

# Copy environment config
COPY --chown=${UID}:${GID} .env.example ./.env

# Copy license + third-party attributions. Required by the BSD/MIT/NCSA/Apache
# clauses of the bundled Python packages, which mandate that their copyright
# notices travel with any binary redistribution — this image is one.
COPY --chown=${UID}:${GID} LICENSE THIRD_PARTY_LICENSES.md ./

# Create the non-root user (files are already owned via COPY --chown).
# Best-effort named account for shell convenience; the entrypoint always works
# off the NUMERIC ids below, because host-provided UID/GID (dev.py passes the
# host user's, e.g. 501/20 on macOS) can collide with existing base-image
# groups and make the named groupadd fail.
RUN groupadd -g ${GID} librefolio 2>/dev/null || true && \
    useradd -u ${UID} -g ${GID} -m -s /bin/bash librefolio 2>/dev/null || true
ENV LIBREFOLIO_UID=${UID} \
    LIBREFOLIO_GID=${GID}

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

