#!/usr/bin/env bash
# Capture a LibreFolio gallery run as an immutable snapshot (visual review safety net).
#
# Usage (from any directory):
#   scripts/visual_review/gallery_snapshot.sh <label> [--checkout PATH] [--port N] [--data-dir PATH]
#                                             [--work-dir PATH] [-- <extra `dev.py mkdocs gallery` args>]
# Examples:
#   scripts/visual_review/gallery_snapshot.sh ref-2026-10-20
#   scripts/visual_review/gallery_snapshot.sh dash-only -- -f "Dashboard" --desktop-only
#   scripts/visual_review/gallery_snapshot.sh cand-T --checkout ../LibreFolio-worktrees/t --port 6151 --data-dir /tmp/librefolio-r2-t
#
# Defaults: the checkout that contains this script; port 6150 + data dir /tmp/librefolio-r2-main (coordinator
# lane, Release 2 convention); work dir $LF_VISUAL_REVIEW_DIR, else <folder of the main checkout>/LibreFolio_subRepo/
# LibreFolio_visual_review when LibreFolio_subRepo exists, else ~/LibreFolio_visual_review — never inside a checkout.
# The gallery writes git-ignored PNGs into <checkout>/mkdocs_src/docs/gallery. Only the PNGs written by THIS run
# (newer than a start stamp) are copied to <work>/snapshots/<label>/png, so images left by failed or filtered
# tests never pollute a snapshot: they are listed in stale_not_regenerated.txt. A busy port stops the script
# (no --force, by policy). A linked worktree must reuse the main venv: export PIPENV_CUSTOM_VENV_NAME first.
# The app version is pinned, so that snapshots of different commits compare: the sidebar, the changelog and the
# About tab show LF_APP_VERSION (default v0.0.0-review) instead of `git describe`. When the checkout's frontend
# build is not a debug build carrying it, the script rebuilds it first (dev.py front build --debug, build.log).
# Every shot is also scanned for mixed elements (role and legacy colour classes on one element, the runtime twin of
# the colour gate G3): LF_GALLERY_MIXED_DIR=<snapshot>/mixed, merged into mixed_elements.json at the end; read it with
# `gallery_tool mixed <snapshot>`. Report only: it never fails the run.
set -euo pipefail

usage() { sed -n '2,24p' "$0"; exit 2; }
[[ $# -ge 1 && "$1" != -* ]] || usage
LABEL=$1; shift
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd -P)
CHECKOUT=$(cd "$(dirname "$0")/../.." && pwd)
PORT=6150
DATA_DIR=/tmp/librefolio-r2-main
WORK=${LF_VISUAL_REVIEW_DIR:-}
EXTRA=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --checkout) CHECKOUT=$2; shift 2 ;;
        --port) PORT=$2; shift 2 ;;
        --data-dir) DATA_DIR=$2; shift 2 ;;
        --work-dir) WORK=$2; shift 2 ;;
        --) shift; EXTRA=("$@"); break ;;
        *) echo "unknown argument: $1" >&2; usage ;;
    esac
done

CHECKOUT=$(cd "$CHECKOUT" && pwd -P)
if [[ -z "$WORK" ]]; then
    MAIN=$(dirname "$(git -C "$CHECKOUT" rev-parse --path-format=absolute --git-common-dir)")
    if [[ -d "$(dirname "$MAIN")/LibreFolio_subRepo" ]]; then WORK="$(dirname "$MAIN")/LibreFolio_subRepo/LibreFolio_visual_review"; else WORK="$HOME/LibreFolio_visual_review"; fi
fi
refuse_inside() { case "$1/" in "$CHECKOUT/"*) echo "work dir $1 is inside the checkout $CHECKOUT: choose a path outside it" >&2; exit 2 ;; esac; }
case "$WORK" in /*) ;; *) WORK="$PWD/$WORK" ;; esac
refuse_inside "$WORK"
mkdir -p "$WORK"
WORK=$(cd "$WORK" && pwd -P)
refuse_inside "$WORK"
GIT_DIR=$(git -C "$CHECKOUT" rev-parse --path-format=absolute --git-dir)
GIT_COMMON=$(git -C "$CHECKOUT" rev-parse --path-format=absolute --git-common-dir)
if [[ "$GIT_DIR" != "$GIT_COMMON" && -z "${PIPENV_CUSTOM_VENV_NAME:-}" ]]; then
    echo "$CHECKOUT is a linked worktree: export PIPENV_CUSTOM_VENV_NAME=<main venv name> so pipenv reuses the main environment" >&2
    exit 2
fi
# Read by vite.config.ts (the bundle) and by the backend (the About tab): one version for every snapshot.
APP_VERSION=${LF_APP_VERSION:-v0.0.0-review}
export LF_APP_VERSION=$APP_VERSION

DEST="$WORK/snapshots/$LABEL"
GAL="$CHECKOUT/mkdocs_src/docs/gallery"
[[ -e "$DEST" ]] && { echo "snapshot already exists: $DEST" >&2; exit 2; }
[[ -d "$GAL" ]] || { echo "gallery dir not found: $GAL" >&2; exit 2; }
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "port $PORT is busy — refusing to start (no --force by policy)" >&2
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
    exit 3
fi

mkdir -p "$DEST/png"
# The gallery's mixed-element records, one file per Playwright worker (frontend/e2e/fixtures/galleryMixed.ts).
MIXED_PARTS="$DEST/mixed"
mkdir -p "$MIXED_PARTS"
BUILD="$CHECKOUT/frontend/build"
if [[ "$(cat "$BUILD/.build-debug" 2>/dev/null)" != "1" ]] || ! grep -rqF --include='*.js' -- "$APP_VERSION" "$BUILD" 2>/dev/null; then
    echo "the frontend build is not a debug build showing $APP_VERSION: rebuilding it (log: $DEST/build.log)"
    set +e
    (cd "$CHECKOUT" && pipenv run python dev.py front build --debug) > "$DEST/build.log" 2>&1
    BUILD_RC=$?
    set -e
    [[ $BUILD_RC -eq 0 ]] || { echo "frontend build failed (rc=$BUILD_RC): see $DEST/build.log" >&2; exit 4; }
fi
STAMP="$DEST/.start-stamp"
touch "$STAMP"
SHA=$(git -C "$CHECKOUT" rev-parse HEAD)
DIRTY=$(git -C "$CHECKOUT" status --porcelain | wc -l | tr -d ' ')
START_ISO=$(date '+%Y-%m-%dT%H:%M:%S%z')
START_S=$(date +%s)
echo "snapshot=$LABEL sha=$SHA dirty_files=$DIRTY app_version=$APP_VERSION port=$PORT data_dir=$DATA_DIR work=$WORK extra=${EXTRA[*]:-}"

set +e
(
    cd "$CHECKOUT" &&
    LF_GALLERY_MIXED_DIR="$MIXED_PARTS" LIBREFOLIO_TEST_DATA_DIR="$DATA_DIR" pipenv run python dev.py mkdocs gallery --test-port "$PORT" ${EXTRA[@]+"${EXTRA[@]}"}
) 2>&1 | tee "$DEST/gallery.log"
RC=${PIPESTATUS[0]}
set -e
END_S=$(date +%s)

(cd "$GAL" && find . -name '*.png' -newer "$STAMP" -print0 | rsync -a --from0 --files-from=- ./ "$DEST/png/")
(cd "$GAL" && find . -name '*.png' ! -newer "$STAMP" | sed 's|^\./||' | sort) > "$DEST/stale_not_regenerated.txt"
NEW=$(find "$DEST/png" -name '*.png' | wc -l | tr -d ' ')
# Keep Playwright's failure evidence (screenshots, error-context.md) with the snapshot when the run failed.
if [[ $RC -ne 0 && -d "$CHECKOUT/frontend/test-results" ]]; then cp -R "$CHECKOUT/frontend/test-results" "$DEST/test-results"; fi
STALE=$(wc -l < "$DEST/stale_not_regenerated.txt" | tr -d ' ')
sed 's/\x1b\[[0-9;]*m//g' "$DEST/gallery.log" | grep -E '^\s+\[(desktop|mobile)\] ›|^\s+[0-9]+ (failed|passed|skipped)' > "$DEST/failures.txt" || true

# Written by Python so that every value is JSON-escaped (a filter such as `-g 'a\(b'` used to break the file).
(
    cd "$CHECKOUT" &&
    LF_META_PATH="$DEST/meta.json" LF_META_LABEL="$LABEL" LF_META_CHECKOUT="$CHECKOUT" LF_META_COMMIT="$SHA" \
    LF_META_DIRTY="$DIRTY" LF_META_STARTED="$START_ISO" LF_META_DURATION="$((END_S - START_S))" LF_META_RC="$RC" \
    LF_META_PORT="$PORT" LF_META_DATA_DIR="$DATA_DIR" LF_META_EXTRA="${EXTRA[*]:-}" LF_META_NEW="$NEW" \
    LF_META_STALE="$STALE" LF_META_APP_VERSION="$APP_VERSION" pipenv run python -c '
import json, os
e = os.environ
meta = {
    "label": e["LF_META_LABEL"],
    "checkout": e["LF_META_CHECKOUT"],
    "commit": e["LF_META_COMMIT"],
    "dirty_files": int(e["LF_META_DIRTY"]),
    "app_version": e["LF_META_APP_VERSION"],
    "started": e["LF_META_STARTED"],
    "duration_s": int(e["LF_META_DURATION"]),
    "exit_code": int(e["LF_META_RC"]),
    "port": int(e["LF_META_PORT"]),
    "data_dir": e["LF_META_DATA_DIR"],
    "extra_args": e["LF_META_EXTRA"],
    "png_captured": int(e["LF_META_NEW"]),
    "png_stale_not_regenerated": int(e["LF_META_STALE"]),
}
with open(e["LF_META_PATH"], "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)
    f.write("\n")
'
)
# After meta.json, which gives the table its commit. A failed merge leaves the records in place and the run's result alone.
if ! (cd "$CHECKOUT" && pipenv run python "$SCRIPT_DIR/gallery_tool.py" mixed "$DEST" --collect); then
    echo "WARNING: the mixed-element records could not be merged: they stay in $MIXED_PARTS" >&2
fi
rm -f "$STAMP"
echo "---"
cat "$DEST/meta.json"
echo "failed/passed summary: $DEST/failures.txt"
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "WARNING: port $PORT still has a listener after the run" >&2
fi
exit "$RC"
