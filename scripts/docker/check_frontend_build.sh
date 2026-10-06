#!/bin/sh
# Fail the Docker image build unless the frontend build is a production build.
#
# usage: check_frontend_build.sh <frontend-build-dir>
#
# `./dev.py front build` records the build mode in <dir>/.build-debug ("0" = production).
# Any `./dev.py server --test` - the docs gallery in CI runs one - rebuilds the frontend
# in debug mode (no minification, sourcemaps, ~2.7x the size), and the JS-coverage test
# runs leave an instrumented build. Neither may ship in an image.
set -eu

dir="${1:?usage: check_frontend_build.sh <frontend-build-dir>}"

fail() {
    echo "ERROR: ${dir} is not a production frontend build: $1" >&2
    echo "Rebuild it with './dev.py front build', then build the image again." >&2
    exit 1
}

[ -f "${dir}/index.html" ] || fail "index.html is missing"
[ -f "${dir}/200.html" ] || fail "200.html (the SPA fallback) is missing"

if [ -f "${dir}/.build-debug" ] && [ "$(tr -d '[:space:]' < "${dir}/.build-debug")" = "1" ]; then
    fail "it is a debug build (.build-debug = 1)"
fi
[ ! -e "${dir}/.coverage-instrumented" ] || fail "it is instrumented for coverage (.coverage-instrumented)"

map="$(find "${dir}" -type f -name '*.map' | head -n 1)"
[ -z "${map}" ] || fail "it contains sourcemaps (${map#"${dir}"/})"

[ -f "${dir}/.build-debug" ] || echo "WARNING: ${dir}/.build-debug is missing: build mode unknown, but no sourcemaps found." >&2
echo "Frontend build OK: production."
