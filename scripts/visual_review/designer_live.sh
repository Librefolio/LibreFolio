#!/usr/bin/env bash
# Start a LibreFolio TEST server for a designer's live review, on its own lane (visual review).
#
# Usage: scripts/visual_review/designer_live.sh [--refresh] [--port N] [--data-dir PATH]
#                                               [--from PATH] [--from-port N]
#   First start (or --refresh): copies the data of the latest gallery run (default: the coordinator lane,
#   /tmp/librefolio-r2-main on port 6150) into --data-dir, so the live app shows the same data as the
#   screenshots. Later gallery runs wipe their own lane, not this one. The test server always serves the frontend
#   debug build (dev.py forces it with --test), so the hidden debug-only pages are available too.
#   The server listens on 0.0.0.0, so a designer on the same network can open http://<this-machine>:<port>.
#   Test data only — never production data. Stop with Ctrl+C.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/../.." && pwd)
SRC=/tmp/librefolio-r2-main
SRC_PORT=6150
DATA=/tmp/librefolio-color-review
PORT=6160
REFRESH=0
while [[ $# -gt 0 ]]; do
    case $1 in
        --refresh) REFRESH=1; shift ;;
        --port) PORT=$2; shift 2 ;;
        --data-dir) DATA=$2; shift 2 ;;
        --from) SRC=$2; shift 2 ;;
        --from-port) SRC_PORT=$2; shift 2 ;;
        *) echo "unknown argument: $1" >&2; sed -n '2,11p' "$0"; exit 2 ;;
    esac
done

busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

case "$DATA" in /tmp/*|/private/tmp/*) ;; *) echo "--data-dir must live under /tmp (it is wiped on --refresh): $DATA" >&2; exit 2 ;; esac
GIT_DIR=$(git -C "$REPO" rev-parse --path-format=absolute --git-dir)
GIT_COMMON=$(git -C "$REPO" rev-parse --path-format=absolute --git-common-dir)
if [[ "$GIT_DIR" != "$GIT_COMMON" && -z "${PIPENV_CUSTOM_VENV_NAME:-}" ]]; then
    echo "$REPO is a linked worktree: export PIPENV_CUSTOM_VENV_NAME=<main venv name> so pipenv reuses the main environment" >&2
    exit 2
fi
if busy "$PORT"; then
    echo "Port $PORT already has a listener — is the review server already running?" >&2
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
    exit 3
fi
if [[ $REFRESH -eq 1 || ! -d "$DATA/sqlite" ]]; then
    [[ -f "$SRC/sqlite/app.db" ]] || { echo "No gallery data in $SRC: capture a gallery snapshot first." >&2; exit 2; }
    busy "$SRC_PORT" && { echo "A gallery run is using $SRC right now (port $SRC_PORT): wait for it to finish." >&2; exit 3; }
    rm -rf "${DATA:?}"
    cp -R "$SRC" "$DATA"
    echo "Review data refreshed from $SRC"
fi

cat <<EOF

  LibreFolio — designer review server
  URL:    http://localhost:$PORT   (same network: http://<this-machine>:$PORT)
  Admin:  e2e_test_admin / E2eAdminPass123!   (the user of almost every gallery shot)
  User:   e2e_test_user  / E2eTestPass123!
  Data:   $DATA (copy of the gallery data; dates follow the day it was generated)
  Stop:   Ctrl+C

EOF
cd "$REPO"
exec pipenv run python dev.py server --test --port "$PORT" --data-dir "$DATA" --no-scheduler --no-reload
