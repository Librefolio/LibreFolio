# =============================================================================
# LibreFolio — Runtime-only Docker Image
# =============================================================================
# Build frontend and docs on host BEFORE building the Docker image:
#   ./dev.py front build
#   ./dev.py mkdocs build
#   docker build -t librefolio .
# =============================================================================

FROM python:3.13-slim

# System dependencies
#   - gcc, libffi-dev: build native Python extensions
#   - git: needed for justetf-scraping pip dependency
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev git \
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

# Copy pre-built frontend (must run ./dev.py front build on host first)
COPY frontend/build/ ./frontend/build/

# Copy pre-built docs (must run ./dev.py mkdocs build on host first)
COPY mkdocs_src/site/ ./mkdocs_src/site/

# Copy environment config
COPY .env.example ./.env

# Create non-root user (default UID/GID 1000:1000).
# Override at build time: docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) .
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} librefolio 2>/dev/null || true && \
    useradd -u ${UID} -g ${GID} -m -s /bin/bash librefolio 2>/dev/null || true && \
    chown -R ${UID}:${GID} /app

# Run as non-root user
USER librefolio

# Default environment
ENV HOST=0.0.0.0 \
    PORT=8000 \
    LIBREFOLIO_DATA_DIR=/app/backend/data/prod \
    LOG_LEVEL=INFO \
    PORTFOLIO_BASE_CURRENCY=EUR

EXPOSE 8000 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/v1/system/health')" || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

