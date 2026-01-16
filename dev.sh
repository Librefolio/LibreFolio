#!/usr/bin/env bash
# LibreFolio Development CLI Wrapper
#
# This is a thin wrapper around dev.py for backward compatibility.
# All functionality is now in dev.py (Python).
#
# Usage:
#   ./dev.sh <command> [args...]
#
# For full help: ./dev.py --help
# For autocompletion, add to ~/.bashrc or ~/.zshrc:
#   eval "$(register-python-argcomplete dev.py)"

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Convert old colon-style commands to new space-separated format
# e.g., "fe:build" -> "front build", "db:upgrade" -> "db upgrade"
convert_args() {
    local args=()
    for arg in "$@"; do
        case "$arg" in
            # Legacy server:test -> server --test
            server:test) args+=("server" "--test") ;;
            # Legacy fe: -> front
            fe:*)
                local act="${arg#fe:}"
                args+=("front" "$act")
                ;;
            fe) args+=("front") ;;
            # Convert other category:action to category action
            *:*)
                local cat="${arg%%:*}"
                local act="${arg#*:}"
                args+=("$cat" "$act")
                ;;
            # Pass through as-is
            *) args+=("$arg") ;;
        esac
    done
    echo "${args[@]}"
}

# No arguments = show help
if [ $# -eq 0 ]; then
    exec pipenv run python dev.py --help
fi

# Convert and execute
converted=$(convert_args "$@")
# shellcheck disable=SC2086
exec pipenv run python dev.py $converted

