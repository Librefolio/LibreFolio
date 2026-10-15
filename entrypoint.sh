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
# Numeric ids, not names: the build's UID/GID can collide with existing
# base-image groups, so a named user/group is not guaranteed to exist.
TARGET_IDS="${LIBREFOLIO_UID:-1000}:${LIBREFOLIO_GID:-1000}"

# Shutdown budget (LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS: 8 s by default, 0 = no
# limit, otherwise 2-600): uvicorn may spend 3/8 of it draining the requests in
# flight, the server the rest (backend/app/config/sleep_wake.py makes the same
# sum). A value set by hand in UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN wins; one the
# server cannot use counts as the default, and the server logs it. Values are
# trimmed of spaces at both ends, as the server does.
shutdown_trim() { printf '%s' "$1" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//'; }
if [ -z "$(shutdown_trim "${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN:-}")" ]; then
    shutdown_budget=$(shutdown_trim "${LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS:-}")
    case "$shutdown_budget" in
        "" | *[!0-9]*) shutdown_budget=8 ;;
    esac
    while [ "${shutdown_budget#0}" != "$shutdown_budget" ]; do
        shutdown_budget="${shutdown_budget#0}"
    done
    case "$shutdown_budget" in
        "") shutdown_budget=0 ;;
        ????*) shutdown_budget=8 ;;
    esac
    if [ "$shutdown_budget" -ne 0 ] && { [ "$shutdown_budget" -lt 2 ] || [ "$shutdown_budget" -gt 600 ]; }; then
        shutdown_budget=8
    fi
    if [ "$shutdown_budget" -gt 0 ]; then
        shutdown_drain=$((shutdown_budget * 3 / 8))
        [ "$shutdown_drain" -ge 1 ] || shutdown_drain=1
        export UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN="$shutdown_drain"
    fi
fi

# If running as root, fix permissions and drop privileges
if [ "$(id -u)" = "0" ]; then
    # Ensure data dir exists and is owned by target user
    mkdir -p "$DATA_DIR"
    chown -R "$TARGET_IDS" "$DATA_DIR"
    # Drop to non-root and re-exec
    exec gosu "$TARGET_IDS" "$@"
fi

# Already running as non-root (e.g. user: directive in compose) — just exec
exec "$@"

