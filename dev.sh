#!/usr/bin/env bash
# LibreFolio development helper script

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function print_help() {
    echo "LibreFolio Development Helper"
    echo ""
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  install          Install all dependencies"
    echo "  server           Start the FastAPI development server"
    echo ""
    echo "Database Management:"
    echo "  db:current [url]     Show current database migration"
    echo "                       Optional: Pass database URL for test DB"
    echo "  db:migrate <msg>     Create a new migration (provide message)"
    echo "  db:upgrade [url]     Apply pending migrations"
    echo "                       Optional: Pass database URL for test DB"
    echo "  db:downgrade [url]   Rollback one migration"
    echo "                       Optional: Pass database URL for test DB"
    echo ""
    echo "Testing:"
    echo "  test [args]      Run tests via test_runner.py"
    echo "                   Examples:"
    echo "                     ./dev.sh test db validate"
    echo "                     ./dev.sh test db all"
    echo "                     ./dev.sh test --reset db all"
    echo "                     ./dev.sh test --help"
    echo ""
    echo "Development:"
    echo "  format           Format code with black"
    echo "  lint             Lint code with ruff"
    echo "  shell            Open a shell in the virtualenv"
    echo "  help             Show this help message"
    echo ""
}

function install_deps() {
    echo -e "${GREEN}Installing dependencies...${NC}"
    pipenv install --dev
}

function start_server() {
    echo -e "${GREEN}Starting LibreFolio API server...${NC}"
    echo -e "${YELLOW}API docs available at: http://localhost:8000/api/v1/docs${NC}"
    pipenv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
}

function db_current() {
    echo -e "${GREEN}Current database migration:${NC}"

    # Accept optional database URL as first parameter
    local db_url="${1:-}"

    if [ -n "$db_url" ]; then
        echo -e "${YELLOW}Using database: $db_url${NC}"
        pipenv run alembic -c backend/alembic.ini -x sqlalchemy.url="$db_url" current
    else
        pipenv run alembic -c backend/alembic.ini current
    fi
}

function db_migrate() {
    if [ -z "$1" ]; then
        echo -e "${RED}Error: Migration message required${NC}"
        echo "Usage: ./dev.sh db:migrate 'your migration message'"
        exit 1
    fi
    echo -e "${GREEN}Creating new migration: $1${NC}"
    pipenv run alembic -c backend/alembic.ini revision --autogenerate -m "$1"

    # Automatically verify CHECK constraints after migration
    echo ""
    echo -e "${YELLOW}Verifying CHECK constraints...${NC}"
    if pipenv run python -m backend.alembic.check_constraints_hook --quiet; then
        echo -e "${GREEN}✅ All CHECK constraints present${NC}"
    else
        echo -e "${RED}⚠️  WARNING: Some CHECK constraints are missing!${NC}"
        echo -e "${YELLOW}Run this for details:${NC}"
        echo -e "  pipenv run python -m backend.alembic.check_constraints_hook"
        echo ""
        echo -e "${YELLOW}SQLite limitation: Alembic autogenerate doesn't detect CHECK constraints.${NC}"
        echo -e "${YELLOW}You may need to manually add them to the generated migration.${NC}"
        echo -e "See: docs/alembic-guide.md (SQLite Limitation: CHECK Constraints section)"
    fi
}

function db_upgrade() {
    # Accept optional database URL as first parameter
    local db_url="${1:-}"

    # Check for missing CHECK constraints BEFORE upgrade (only for production DB)
    if [ -z "$db_url" ]; then
        echo -e "${YELLOW}Pre-flight check: Verifying CHECK constraints...${NC}"
        if ! pipenv run python -m backend.alembic.check_constraints_hook --quiet; then
            echo -e "${RED}❌ BLOCKED: Cannot upgrade - CHECK constraints are missing!${NC}"
            echo ""
            echo -e "${YELLOW}Your database is missing CHECK constraints defined in models.${NC}"
            echo -e "${YELLOW}This usually happens when Alembic autogenerate creates empty migrations.${NC}"
            echo ""
            echo -e "${YELLOW}Run this for details on what's missing:${NC}"
            echo -e "  pipenv run python -m backend.alembic.check_constraints_hook"
            echo ""
            echo -e "${YELLOW}To fix:${NC}"
            echo -e "  1. Find the migration that should have added the constraint"
            echo -e "     (usually the most recent one in backend/alembic/versions/)"
            echo -e "  2. Edit the migration file and add CHECK constraints manually"
            echo -e "     (use batch operations for SQLite)"
            echo -e "  3. If migration already applied: downgrade first, fix, then upgrade"
            echo -e "     ./dev.sh db:downgrade"
            echo -e "     # Edit migration file"
            echo -e "     ./dev.sh db:upgrade"
            echo ""
            echo -e "${YELLOW}See: docs/alembic-guide.md (SQLite Limitation: CHECK Constraints)${NC}"
            echo ""
            exit 1
        fi
        echo -e "${GREEN}✅ Pre-flight check passed${NC}"
        echo ""
    fi

    echo -e "${GREEN}Applying database migrations...${NC}"

    if [ -n "$db_url" ]; then
        echo -e "${YELLOW}Using database: $db_url${NC}"
        # Pass database URL to Alembic via -x sqlalchemy.url
        pipenv run alembic -c backend/alembic.ini -x sqlalchemy.url="$db_url" upgrade head
    else
        # Use default from config/env
        pipenv run alembic -c backend/alembic.ini upgrade head
    fi

    # Verify CHECK constraints after upgrade (only for production DB, not test)
    if [ -z "$db_url" ]; then
        echo ""
        echo -e "${YELLOW}Post-upgrade verification: Checking CHECK constraints...${NC}"
        if pipenv run python -m backend.alembic.check_constraints_hook --quiet; then
            echo -e "${GREEN}✅ All CHECK constraints present${NC}"
        else
            echo -e "${RED}❌ ERROR: Migration applied but CHECK constraints are still missing!${NC}"
            echo -e "${RED}The migration file may need manual correction.${NC}"
            echo ""
            echo -e "${YELLOW}Run this for details:${NC}"
            echo -e "  pipenv run python -m backend.alembic.check_constraints_hook"
            echo ""
            exit 1
        fi
    fi
}

function db_downgrade() {
    echo -e "${YELLOW}Rolling back one migration...${NC}"

    # Accept optional database URL as first parameter
    local db_url="${1:-}"

    if [ -n "$db_url" ]; then
        echo -e "${YELLOW}Using database: $db_url${NC}"
        pipenv run alembic -c backend/alembic.ini -x sqlalchemy.url="$db_url" downgrade -1
    else
        pipenv run alembic -c backend/alembic.ini downgrade -1
    fi
}

function run_tests() {
    # Delegate all test execution to test_runner.py
    # This passes all arguments from dev.sh to test_runner.py
    if [ $# -eq 0 ]; then
        # No arguments: show test_runner help
        python test_runner.py --help
    else
        # Pass all arguments to test_runner
        python test_runner.py "$@"
    fi
}

function format_code() {
    echo -e "${GREEN}Formatting code with black...${NC}"
    pipenv run black backend/
}

function lint_code() {
    echo -e "${GREEN}Linting code with ruff...${NC}"
    pipenv run ruff check backend/
}

function open_shell() {
    echo -e "${GREEN}Opening pipenv shell...${NC}"
    pipenv shell
}

# Main command dispatcher
case "${1:-help}" in
    install)
        install_deps
        ;;
    server)
        start_server
        ;;
    db:current)
        db_current "$2"
        ;;
    db:migrate)
        db_migrate "$2"
        ;;
    db:upgrade)
        db_upgrade "$2"
        ;;
    db:downgrade)
        db_downgrade "$2"
        ;;
    test)
        # Pass all arguments after 'test' to test_runner.py
        shift
        run_tests "$@"
        ;;
    format)
        format_code
        ;;
    lint)
        lint_code
        ;;
    shell)
        open_shell
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        print_help
        exit 1
        ;;
esac

