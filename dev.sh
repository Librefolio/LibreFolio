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

function get_server_port() {
    # Get server port from system environment variable
    # Returns: port number (default: 8000)
    #
    # Note: The .env file is used by Docker/FastAPI at runtime, not by this script.
    # If you need a custom port for dev.sh checks, set it in your shell:
    #   export PORT=9000

    echo "${PORT:-8000}"
}

function check_server_running() {
    # Check if server is running on configured port
    # Args:
    #   $1: action (e.g., "creating migrations", "applying migrations")
    #   $2: strictness ("strict" = exit immediately, "warn" = ask confirmation)
    # Returns: 0 if can continue, 1 if should abort

    local action="${1:-running migrations}"
    local strictness="${2:-strict}"
    local port=$(get_server_port)

    # Check if port is in use
    if ! lsof -ti:$port > /dev/null 2>&1; then
        # Port not in use - all good
        return 0
    fi

    # Port is in use - server is running
    if [ "$strictness" = "strict" ]; then
        # STRICT MODE: Hard stop, cannot continue
        echo -e "${YELLOW}⚠️  Important: Migrations should be run with the server OFFLINE${NC}"
        echo -e "${YELLOW}   Running migrations while the server is active can cause database locks.${NC}"
        echo ""
        echo -e "${RED}❌ Server is currently running on port $port${NC}"
        echo ""
        echo -e "${YELLOW}Please stop the server before $action:${NC}"
        echo -e "  1. Stop the server (Ctrl+C in server terminal)"
        echo -e "  2. Or kill the process: ${GREEN}lsof -ti:$port | xargs kill -9${NC}"
        echo ""
        echo -e "${YELLOW}Then run the command again.${NC}"
        echo ""
        return 1
    else
        # WARN MODE: Show warning and ask confirmation
        echo -e "${YELLOW}⚠️  Warning: Server is running on port $port${NC}"
        echo -e "${YELLOW}   ${action^} while server is active may cause database locks.${NC}"
        echo ""
        echo -e "${YELLOW}Recommended: Stop the server before running migrations.${NC}"
        echo -e "  Kill server: ${GREEN}lsof -ti:$port | xargs kill -9${NC}"
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Operation cancelled.${NC}"
            return 1
        fi
        echo ""
        return 0
    fi
}

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
    echo "  db:check [path]      Verify CHECK constraints in database"
    echo "                       Optional: SQLite file path (default: backend/data/sqlite/app.db)"
    echo "                       Examples:"
    echo "                         ./dev.sh db:check"
    echo "                         ./dev.sh db:check backend/data/sqlite/test_app.db"
    echo ""
    echo "  db:current [path]    Show current database migration"
    echo "                       Optional: SQLite file path (default: backend/data/sqlite/app.db)"
    echo "                       Examples:"
    echo "                         ./dev.sh db:current"
    echo "                         ./dev.sh db:current backend/data/sqlite/test_app.db"
    echo ""
    echo "  db:migrate <msg> [path]  Create a new migration (provide message)"
    echo "                           Optional: SQLite file path (default: backend/data/sqlite/app.db)"
    echo "                           Note: Database must be at HEAD with all constraints present"
    echo "                           Examples:"
    echo "                             ./dev.sh db:migrate 'add users table'"
    echo "                             ./dev.sh db:migrate 'add feature' backend/data/sqlite/test_app.db"
    echo ""
    echo "  db:upgrade [path]    Apply pending migrations"
    echo "                       Optional: SQLite file path (default: backend/data/sqlite/app.db)"
    echo "                       Examples:"
    echo "                         ./dev.sh db:upgrade"
    echo "                         ./dev.sh db:upgrade backend/data/sqlite/test_app.db"
    echo ""
    echo "  db:downgrade [path]  Rollback one migration"
    echo "                       Optional: SQLite file path (default: backend/data/sqlite/app.db)"
    echo "                       Examples:"
    echo "                         ./dev.sh db:downgrade"
    echo "                         ./dev.sh db:downgrade backend/data/sqlite/test_app.db"
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

function path_to_url() {
    # Convert SQLite file path to database URL
    # If no path provided, returns empty (use default from .env)
    local db_path="$1"

    if [ -z "$db_path" ]; then
        echo ""
        return
    fi

    # Convert relative path to absolute if needed
    if [[ ! "$db_path" = /* ]]; then
        db_path="$PROJECT_ROOT/$db_path"
    fi

    echo "sqlite:///$db_path"
}

function install_deps() {
    echo -e "${GREEN}Installing dependencies...${NC}"
    pipenv install --dev
}

function start_server() {
    echo -e "${GREEN}Starting LibreFolio API server...${NC}"
    echo -e "${YELLOW}API Redoc available at: http://localhost:8000/api/v1/redoc${NC}  # Render with Redoc"
    echo -e "${YELLOW}API docs available at: http://localhost:8000/api/v1/docs${NC}    # Render with Swagger"
    pipenv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
}

function has_pending_migrations() {
    # Check if there are pending migrations
    # Returns 0 (success) if there ARE pending migrations
    # Returns 1 (failure) if there are NO pending migrations (already at HEAD)

    local db_path="$1"
    local db_url=$(path_to_url "$db_path")

    local current_output
    if [ -n "$db_url" ]; then
        current_output=$(pipenv run alembic -c backend/alembic.ini -x sqlalchemy.url="$db_url" current 2>/dev/null | grep -v "Loading" | grep -v "Courtesy" | grep -v "Pipenv" | grep -v "PIPENV" | tail -1)
    else
        current_output=$(pipenv run alembic -c backend/alembic.ini current 2>/dev/null | grep -v "Loading" | grep -v "Courtesy" | grep -v "Pipenv" | grep -v "PIPENV" | tail -1)
    fi

    # If output contains "(head)", we're already at the latest version
    if echo "$current_output" | grep -q "(head)"; then
        return 1  # No pending migrations
    else
        return 0  # Has pending migrations
    fi
}

function db_check() {
    # Accept optional SQLite file path as first parameter
    local db_path="${1:-backend/data/sqlite/app.db}"
    local db_url=$(path_to_url "$db_path")

    if [ -n "$db_url" ]; then
        echo -e "${GREEN}Verifying CHECK constraints in: ${YELLOW}$db_path${NC}"
        echo ""
        # Use ALEMBIC_DATABASE_URL to avoid being overridden by .env loading
        ALEMBIC_DATABASE_URL="$db_url" pipenv run python -m backend.alembic.check_constraints_hook
    else
        echo -e "${GREEN}Verifying CHECK constraints in default database${NC}"
        echo ""
        pipenv run python -m backend.alembic.check_constraints_hook
    fi
}

function db_current() {
    echo -e "${GREEN}Checking current database migration...${NC}"

    # Accept optional SQLite file path as first parameter
    local db_path="$1"
    local db_url=$(path_to_url "$db_path")

    if [ -n "$db_url" ]; then
        echo -e "${YELLOW}Database: $db_path${NC}"
    else
        echo -e "${YELLOW}Database: backend/data/sqlite/app.db (default)${NC}"
    fi
    echo ""

    if [ -n "$db_url" ]; then
        pipenv run alembic -c backend/alembic.ini -x sqlalchemy.url="$db_url" current
    else
        pipenv run alembic -c backend/alembic.ini current
    fi

    local exit_code=$?
    echo ""
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ The current 'Migration status code was retrieved' successfully${NC}"
    else
        echo -e "${RED}❌ Failed to retrieve migration status${NC}"
        return $exit_code
    fi
}

function db_migrate() {
    if [ -z "$1" ]; then
        echo -e "${RED}Error: Migration message required${NC}"
        echo "Usage: ./dev.sh db:migrate 'your migration message' [db_path]"
        exit 1
    fi

    # Accept optional database path as second parameter
    local db_path="$2"
    local db_url=$(path_to_url "$db_path")

    echo -e "${GREEN}Checking database state before creating migration...${NC}"
    echo ""

    # STEP 0: Check if server is running (avoid database locks)
    if ! check_server_running "creating migrations" "strict"; then
        exit 1
    fi

    local port=$(get_server_port)
    echo -e "${GREEN}✅ Server is offline (port $port not in use)${NC}"
    echo ""

    # STEP 1: Check if we're at HEAD
    if has_pending_migrations "$db_path"; then
        echo -e "${RED}❌ Cannot create migration: you have pending migrations${NC}"
        echo ""
        echo -e "${YELLOW}Apply them first:${NC}"
        if [ -n "$db_path" ]; then
            echo -e "  ./dev.sh db:upgrade $db_path"
        else
            echo -e "  ./dev.sh db:upgrade"
        fi
        echo ""
        exit 1
    fi

    echo -e "${GREEN}✅ Database is at HEAD${NC}"

    # STEP 2: Check constraints
    echo -e "${YELLOW}Verifying CHECK constraints...${NC}"

    local check_result
    if [ -n "$db_url" ]; then
        ALEMBIC_DATABASE_URL="$db_url" pipenv run python -m backend.alembic.check_constraints_hook --quiet
        check_result=$?
    else
        pipenv run python -m backend.alembic.check_constraints_hook --quiet
        check_result=$?
    fi

    if [ $check_result -ne 0 ]; then
        echo -e "${RED}❌ Cannot create migration: database has missing CHECK constraints${NC}"
        echo ""
        echo -e "${YELLOW}Run for details:${NC}"
        if [ -n "$db_path" ]; then
            echo -e "  ./dev.sh db:check $db_path"
        else
            echo -e "  ./dev.sh db:check"
        fi
        echo ""
        echo -e "${YELLOW}Fix the database first (see: docs/alembic-guide.md - SQLite CHECK Constraints)${NC}"
        echo ""
        exit 1
    fi

    echo -e "${GREEN}✅ All CHECK constraints present${NC}"
    echo ""

    # STEP 3: Create migration
    echo -e "${GREEN}Database is ready - creating migration: $1${NC}"

    if [ -n "$db_url" ]; then
        pipenv run alembic -c backend/alembic.ini -x sqlalchemy.url="$db_url" revision --autogenerate -m "$1"
    else
        pipenv run alembic -c backend/alembic.ini revision --autogenerate -m "$1"
    fi

    echo ""
    echo -e "${YELLOW}⚠️  Remember to check the generated migration file for CHECK constraints${NC}"
    echo -e "${YELLOW}SQLite limitation: Alembic autogenerate doesn't detect CHECK constraints.${NC}"
    echo -e "${YELLOW}See: docs/alembic-guide.md (SQLite Limitation: CHECK Constraints)${NC}"
}

function db_upgrade() {
    # Accept optional SQLite file path as first parameter
    local db_path="$1"
    local db_url=$(path_to_url "$db_path")

    echo -e "${GREEN}Applying database migrations...${NC}"

    if [ -n "$db_url" ]; then
        echo -e "${YELLOW}Database: $db_path${NC}"
    fi
    echo ""

    # Check if server is running (avoid database locks)
    if ! check_server_running "applying migrations" "warn"; then
        exit 1
    fi

    # Apply migrations (NO pre-flight blocking check)
    if [ -n "$db_url" ]; then
        pipenv run alembic -c backend/alembic.ini -x sqlalchemy.url="$db_url" upgrade head
    else
        pipenv run alembic -c backend/alembic.ini upgrade head
    fi

    local upgrade_exit_code=$?

    if [ $upgrade_exit_code -ne 0 ]; then
        echo ""
        echo -e "${RED}❌ Migration upgrade failed${NC}"
        return $upgrade_exit_code
    fi

    echo ""
    echo -e "${GREEN}✅ Migrations applied successfully${NC}"

    # Post-flight check (WARNING ONLY - does not block or exit)
    echo ""
    echo -e "${YELLOW}Post-upgrade verification: Checking CHECK constraints...${NC}"

    local check_result
    if [ -n "$db_url" ]; then
        ALEMBIC_DATABASE_URL="$db_url" pipenv run python -m backend.alembic.check_constraints_hook --quiet
        check_result=$?
    else
        pipenv run python -m backend.alembic.check_constraints_hook --quiet
        check_result=$?
    fi

    if [ $check_result -ne 0 ]; then
        echo -e "${YELLOW}⚠️  WARNING: Migration completed but CHECK constraints are missing!${NC}"
        echo ""
        echo -e "${YELLOW}Run this for details on what's missing:${NC}"
        if [ -n "$db_path" ]; then
            echo -e "  ./dev.sh db:check $db_path"
        else
            echo -e "  ./dev.sh db:check"
        fi
        echo ""

        echo ""
        echo -e "${YELLOW}This is a known SQLite limitation - batch operations sometimes fail to add${NC}"
        echo -e "${YELLOW}CHECK constraints. You need to fix the migration file and re-apply it.${NC}"
        echo ""
        echo -e "${YELLOW}🔧 HOW TO FIX:${NC}"
        echo ""
        echo -e "${GREEN}STEP 1: Rollback the migration${NC}"
        if [ -n "$db_path" ]; then
            echo -e "  \$ ./dev.sh db:downgrade $db_path"
        else
            echo -e "  \$ ./dev.sh db:downgrade"
        fi
        echo ""
        echo -e "${GREEN}STEP 2: Edit the migration file${NC}"
        echo -e "  Look in: backend/alembic/versions/"
        echo ""
        echo -e "  ${YELLOW}Add to upgrade() function:${NC}"
        echo -e "    with op.batch_alter_table('table_name', schema=None) as batch_op:"
        echo -e "        batch_op.create_check_constraint("
        echo -e "            'constraint_name',"
        echo -e "            'sql_expression'"
        echo -e "        )"
        echo ""
        echo -e "  ${YELLOW}Add to downgrade() function:${NC}"
        echo -e "    try:"
        echo -e "        with op.batch_alter_table('table_name', schema=None) as batch_op:"
        echo -e "            batch_op.drop_constraint('constraint_name', type_='check')"
        echo -e "    except ValueError:"
        echo -e "        pass  # Constraint may not exist if migration failed"
        echo ""
        echo -e "${GREEN}STEP 3: Re-apply the migration${NC}"
        if [ -n "$db_path" ]; then
            echo -e "  \$ ./dev.sh db:upgrade $db_path"
        else
            echo -e "  \$ ./dev.sh db:upgrade"
        fi
        echo ""
        echo -e "${YELLOW}📚 Full documentation: docs/alembic-guide.md${NC}"
        echo -e "${YELLOW}   See section: SQLite Limitation - CHECK Constraints${NC}"
        echo ""
        # NOTE: NO exit 1 here - just warning
    else
        echo -e "${GREEN}✅ All CHECK constraints present${NC}"
    fi
}

function db_downgrade() {
    echo -e "${YELLOW}Rolling back one migration...${NC}"

    # Accept optional SQLite file path as first parameter
    local db_path="$1"
    local db_url=$(path_to_url "$db_path")

    if [ -n "$db_url" ]; then
        echo -e "${YELLOW}Database: $db_path${NC}"
    else
        echo -e "${YELLOW}Database: backend/data/sqlite/app.db (default)${NC}"
    fi
    echo ""

    # Check if server is running (avoid database locks)
    if ! check_server_running "rolling back migrations" "warn"; then
        exit 1
    fi

    if [ -n "$db_url" ]; then
        pipenv run alembic -c backend/alembic.ini -x sqlalchemy.url="$db_url" downgrade -1
    else
        pipenv run alembic -c backend/alembic.ini downgrade -1
    fi

    local exit_code=$?
    echo ""
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ Migration rolled back successfully${NC}"
    else
        echo -e "${RED}❌ Migration rollback failed${NC}"
        return $exit_code
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
    db:check)
        db_check "$2"
        ;;
    db:current)
        db_current "$2"
        ;;
    db:migrate)
        db_migrate "$2" "$3"
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

