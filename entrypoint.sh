#!/bin/sh
# =============================================================================
# LibreFolio — Docker Entrypoint
# =============================================================================
# WHY THIS EXISTS:
# Docker daemon creates bind-mount directories as root when they don't exist
# on the host. The 'user:' directive in compose only affects the process inside
# the container, NOT host directory creation. So we must:
#   1. Start as root (default Docker behavior)
#   2. Fix ownership of the data directory
#   3. Drop to non-root user via gosu (PID 1 replacement)
#
# This is the same pattern used by postgres, mysql, redis official images.
# =============================================================================

set -e

DATA_DIR="${LIBREFOLIO_DATA_DIR:-/app/backend/data/prod-docker}"
TARGET_USER="${LIBREFOLIO_USER:-librefolio}"

# If running as root, fix permissions and drop privileges
if [ "$(id -u)" = "0" ]; then
    # Ensure data dir exists and is owned by target user
    mkdir -p "$DATA_DIR"
    chown -R "$TARGET_USER:$TARGET_USER" "$DATA_DIR"
    # Drop to non-root and re-exec
    exec gosu "$TARGET_USER" "$@"
fi

# Already running as non-root (e.g. user: directive in compose) — just exec
exec "$@"

