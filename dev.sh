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
    echo "  server           Start the FastAPI development server (python backend app)"
    echo "  db:current       Show current database migration"
    echo "  db:migrate       Create a new migration (provide message)"
    echo "  db:upgrade       Apply pending migrations"
    echo "  db:downgrade     Rollback one migration"
    echo "  test             Run tests"
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
    pipenv run alembic -c backend/alembic.ini current
}

function db_migrate() {
    if [ -z "$1" ]; then
        echo -e "${RED}Error: Migration message required${NC}"
        echo "Usage: ./dev.sh db:migrate 'your migration message'"
        exit 1
    fi
    echo -e "${GREEN}Creating new migration: $1${NC}"
    pipenv run alembic -c backend/alembic.ini revision --autogenerate -m "$1"
}

function db_upgrade() {
    echo -e "${GREEN}Applying database migrations...${NC}"
    pipenv run alembic -c backend/alembic.ini upgrade head
}

function db_downgrade() {
    echo -e "${YELLOW}Rolling back one migration...${NC}"
    pipenv run alembic -c backend/alembic.ini downgrade -1
}

function run_tests() {
    echo -e "${GREEN}Running tests...${NC}"
    pipenv run pytest
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
        db_current
        ;;
    db:migrate)
        db_migrate "$2"
        ;;
    db:upgrade)
        db_upgrade
        ;;
    db:downgrade)
        db_downgrade
        ;;
    test)
        run_tests
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

