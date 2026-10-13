#!/bin/sh
# Warn, never fail, when the checkout no longer matches its commit.
#
# usage: warn_if_tree_changed.sh <what-just-ran>
#
# The release workflow freezes the version right after the checkout (VERSION for the backend,
# LF_APP_VERSION for the frontend). A build that read `git describe --dirty` later would otherwise
# carry `-dirty` as soon as a step before it rewrote a tracked file - as every 1.1 screenshot did.
# This check names the step: it prints `git status --porcelain` and, when the output is not empty,
# a GitHub Actions warning naming <what-just-ran>. It always exits 0: it diagnoses, it does not gate.
set -u

after="${1:?usage: warn_if_tree_changed.sh <what-just-ran>}"

if ! changes="$(git status --porcelain 2>&1)"; then
    echo "::warning title=Checkout check failed after ${after}::git status failed: ${changes}"
    exit 0
fi
if [ -z "${changes}" ]; then
    echo "Checkout unchanged after ${after}."
    exit 0
fi

printf '%s\n' "${changes}"
tracked="$(printf '%s\n' "${changes}" | grep -vc '^??' || true)"
untracked="$(printf '%s\n' "${changes}" | grep -c '^??' || true)"
if [ "${tracked}" -gt 0 ]; then
    echo "::warning title=Checkout changed after ${after}::${tracked} tracked path(s) changed and ${untracked} untracked (listed in this step's log). git describe --dirty now reads -dirty: only LF_APP_VERSION keeps it off the app."
else
    echo "::warning title=Checkout changed after ${after}::${untracked} untracked path(s) not ignored by Git (listed in this step's log)."
fi
exit 0
