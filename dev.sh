#!/usr/bin/env bash
# LibreFolio development helper script

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'  # No Color

function get_server_port() {
    # Get server port from system environment variable
    # Returns: port number (default: 8000)
    #
    # Note: The .env file is used by Docker/FastAPI at runtime, not by this script.
    # If you need a custom port for dev.sh checks, set it in your shell:
    #   export PORT=9000

    echo "${PORT:-8000}"
}

function get_test_server_port() {
    # Get test server port from environment variable
    # Returns: port number (default: 8001)
    echo "${TEST_PORT:-8001}"
}

function get_database_path() {
    # Get production database path from environment variable
    # Returns: relative path (default: backend/data/sqlite/app.db)
    local db_url="${DATABASE_URL:-sqlite:///./backend/data/sqlite/app.db}"
    # Extract path from URL (remove sqlite:///./  or sqlite:///)
    echo "$db_url" | sed 's|sqlite:///\./||' | sed 's|sqlite:///||'
}

function get_test_database_path() {
    # Get test database path from environment variable
    # Returns: relative path (default: backend/data/sqlite/test_app.db)
    local db_url="${TEST_DATABASE_URL:-sqlite:///./backend/data/sqlite/test_app.db}"
    # Extract path from URL
    echo "$db_url" | sed 's|sqlite:///\./||' | sed 's|sqlite:///||'
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
    local prod_port=$(get_server_port)
    local test_port=$(get_test_server_port)
    local prod_db=$(get_database_path)
    local test_db=$(get_test_database_path)

    echo "LibreFolio Development Helper"
    echo ""
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  install          Install all dependencies (Python + Node)"
    echo "  server           Start the FastAPI server (auto-builds frontend if needed)"
    echo "                   Port: $prod_port | Database: $prod_db"
    echo "  server:test      Start the FastAPI server in TEST MODE"
    echo "                   Port: $test_port | Database: $test_db"
    echo ""
    echo "Database Management:"
    echo "  db:check [path]      Verify CHECK constraints in database"
    echo "                       Optional: SQLite file path (default: $prod_db)"
    echo "                       Examples:"
    echo "                         ./dev.sh db:check"
    echo "                         ./dev.sh db:check $test_db"
    echo ""
    echo "  db:current [path]    Show current database migration"
    echo "                       Optional: SQLite file path (default: $prod_db)"
    echo "                       Examples:"
    echo "                         ./dev.sh db:current"
    echo "                         ./dev.sh db:current $test_db"
    echo ""
    echo "  db:migrate <msg> [path]  Create a new migration (provide message)"
    echo "                           Optional: SQLite file path (default: $prod_db)"
    echo "                           Note: Database must be at HEAD with all constraints present"
    echo "                           Examples:"
    echo "                             ./dev.sh db:migrate 'add users table'"
    echo "                             ./dev.sh db:migrate 'add feature' $test_db"
    echo ""
    echo "  db:upgrade [path]    Apply pending migrations"
    echo "                       Optional: SQLite file path (default: $prod_db)"
    echo "                       Examples:"
    echo "                         ./dev.sh db:upgrade"
    echo "                         ./dev.sh db:upgrade $test_db"
    echo ""
    echo "  db:downgrade [path]  Rollback one migration"
    echo "                       Optional: SQLite file path (default: $prod_db)"
    echo "                       Examples:"
    echo "                         ./dev.sh db:downgrade"
    echo "                         ./dev.sh db:downgrade $test_db"
    echo ""
    echo "Testing:"
    echo "  test [args]      Run tests via test_runner.py"
    echo "                   Examples:"
    echo "                     ./dev.sh test db validate"
    echo "                     ./dev.sh test db all"
    echo "                     ./dev.sh test --reset db all"
    echo "                     ./dev.sh test --help"
    echo ""
    echo "  test:coverage    Run all tests with code coverage tracking"
    echo "                   Generates HTML report in htmlcov/index.html"
    echo "                   Shows line-by-line coverage with missing lines"
    echo "                   Examples:"
    echo "                     ./dev.sh test:coverage"
    echo "                     open htmlcov/index.html  # View report"
    echo ""
    echo "Development:"
    echo "  format           Format code with black"
    echo "  lint             Lint code with ruff"
    echo "  shell            Open a shell in the virtualenv"
    echo ""
    echo "Frontend:"
    echo "  fe:dev           Start frontend dev server (Vite + SvelteKit)"
    echo "  fe:build         Build frontend for production"
    echo "  fe:check         Run svelte-check for type errors"
    echo "  fe:preview       Preview production build"
    echo ""
    echo "i18n (Translations):"
    echo "  i18n:audit       Audit translations, show missing keys (Markdown)"
    echo "  i18n:audit:md  Export translation audit to Markdown"
    echo "  i18n:audit:xlsx  Export translation audit to Excel"
    echo "  i18n:audit:both  Export both Markdown and Excel reports"
    echo ""
    echo "API Schema Generation:"
    echo "  api:schema       Export OpenAPI schema to frontend/src/lib/api/openapi.json"
    echo "  api:client       Generate TypeScript client from OpenAPI schema"
    echo "  api:sync         Run api:schema + api:client (full sync)"
    echo ""
    echo "User Management:"
    echo "  user:create      Create a new superuser"
    echo "                     Usage: ./dev.sh user:create <username> <email> <password>"
    echo "  user:reset       Reset user password"
    echo "                     Usage: ./dev.sh user:reset <username> <new_password>"
    echo "  user:list        List all users"
    echo "  user:activate    Activate a user account"
    echo "                     Usage: ./dev.sh user:activate <username>"
    echo "  user:deactivate  Deactivate a user account"
    echo "                     Usage: ./dev.sh user:deactivate <username>"
    echo ""
    echo "Information:"
    echo "  info:api         List all API endpoints with descriptions"
    echo "  info:mk [cmd]    MkDocs helper (cmd = build | serve | clean | help)"
    echo "                     Use: ./dev.sh info:mk help for details"
    echo ""
    echo "Help:"
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
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}       Installing LibreFolio Dependencies          ${NC}"
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""

    # 1. Backend Python dependencies
    echo -e "${BLUE}[1/4] ${NC}${BOLD}Installing Python backend dependencies...${NC}"
    pipenv install --dev
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install Python dependencies${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ Python dependencies installed${NC}"
    echo ""

    # 2. Root project tools (Playwright for E2E tests)
    echo -e "${BLUE}[2/4] ${NC}${BOLD}Installing root project tools...${NC}"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install root npm dependencies${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ Root project tools installed${NC}"
    echo ""

    # 3. Frontend dependencies (SvelteKit, TailwindCSS, etc.)
    echo -e "${BLUE}[3/4] ${NC}${BOLD}Installing frontend dependencies...${NC}"
    cd frontend && npm install && cd ..
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install frontend dependencies${NC}"
        return 1
    fi
    echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
    echo ""

    # 4. Playwright browsers for E2E testing
    echo -e "${BLUE}[4/4] ${NC}${BOLD}Installing Playwright browsers...${NC}"
    echo -e "${YELLOW}   (This may take a while, ~500-700MB download)${NC}"
    npx playwright install
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}⚠️  Playwright browser installation had issues (non-critical)${NC}"
    else
        echo -e "${GREEN}✅ Playwright browsers installed${NC}"
    fi
    echo ""

    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}       ✅ All dependencies installed!              ${NC}"
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Frontend Auto-Build Check
# ═══════════════════════════════════════════════════════════════════════════════

function frontend_needs_rebuild() {
    # Check if frontend build is needed
    # Returns 0 (true) if rebuild needed, 1 (false) otherwise

    local build_dir="frontend/build"
    local src_dir="frontend/src"

    # No build exists at all
    if [ ! -d "$build_dir" ]; then
        return 0
    fi

    # No index.html in build
    if [ ! -f "$build_dir/index.html" ]; then
        return 0
    fi

    # Check if any source file is newer than build
    # Find newest file in src directory
    local newest_src=$(find "$src_dir" -type f -newer "$build_dir/index.html" 2>/dev/null | head -1)
    if [ -n "$newest_src" ]; then
        return 0
    fi

    # Check package.json changes
    if [ "frontend/package.json" -nt "$build_dir/index.html" ]; then
        return 0
    fi

    # No rebuild needed
    return 1
}

function auto_build_frontend() {
    # Auto-build frontend if changes detected
    if frontend_needs_rebuild; then
        echo -e "${BLUE}🔄 Frontend changes detected, rebuilding...${NC}"
        cd frontend && npm run build && cd ..
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Frontend rebuilt successfully${NC}"
        else
            echo -e "${YELLOW}⚠️  Frontend build failed, continuing without frontend${NC}"
        fi
        echo ""
    fi
}

function start_server() {
    local port=$(get_server_port)
    local db=$(get_database_path)

    # Auto-build frontend if needed
    auto_build_frontend

    echo -e "${GREEN}Starting LibreFolio API server...${NC}"
    echo -e "${YELLOW}Database: $db${NC}"
    echo -e "${YELLOW}Port: $port${NC}"
    echo ""
    echo -e "${BLUE}${BOLD}Available endpoints:${NC}"
    echo -e " ├── 🏠 ${YELLOW}Frontend:  http://localhost:$port/${NC}"
    echo -e " ├── 💻 ${YELLOW}API Redoc: http://localhost:$port/api/v1/redoc${NC}"
    echo -e " ├── 🚀 ${YELLOW}API Docs:  http://localhost:$port/api/v1/docs${NC}"
    echo -e " └── 📚 ${YELLOW}User Doc:  http://localhost:$port/mkdocs/${NC}"
    echo ""

    # Check if frontend is available
    if [ -f "frontend/build/index.html" ]; then
        echo -e "${GREEN}✅ Frontend build found - UI available at /${NC}"
    else
        echo -e "${YELLOW}⚠️  No frontend build - run './dev.sh fe:build' to enable UI${NC}"
    fi
    echo ""

    pipenv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port $port
}

function start_server_test() {
    local port=$(get_test_server_port)
    local db=$(get_test_database_path)

    # Auto-build frontend if needed
    auto_build_frontend

    echo -e "${GREEN}Starting LibreFolio API server (TEST MODE)...${NC}"
    echo -e "${YELLOW}Database: $db${NC}"
    echo -e "${YELLOW}Port: $port${NC}"
    echo ""
    echo -e "${BLUE}${BOLD}Available endpoints:${NC}"
    echo -e " ├── 🏠 ${YELLOW}Frontend:  http://localhost:$port/${NC}"
    echo -e " ├── 💻 ${YELLOW}API Redoc: http://localhost:$port/api/v1/redoc${NC}"
    echo -e " ├── 🚀 ${YELLOW}API Docs:  http://localhost:$port/api/v1/docs${NC}"
    echo -e " └── 📚 ${YELLOW}User Doc:  http://localhost:$port/mkdocs/${NC}"
    echo ""
    echo -e "${RED}${BOLD}⚠️  TEST MODE - Using test database!${NC}"
    echo ""

    LIBREFOLIO_TEST_MODE=1 pipenv run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port $port
}

# ═══════════════════════════════════════════════════════════════════════════════
# Frontend Commands
# ═══════════════════════════════════════════════════════════════════════════════

function frontend_dev() {
    echo -e "${GREEN}Starting frontend development server...${NC}"
    echo -e "${YELLOW}URL: http://localhost:5173${NC}"
    echo ""
    cd frontend && npm run dev
}

function frontend_build() {
    echo -e "${GREEN}Building frontend for production...${NC}"
    cd frontend && npm run build
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Frontend build complete!${NC}"
        echo -e "${YELLOW}Output in: frontend/build/${NC}"
    else
        echo -e "${RED}❌ Frontend build failed${NC}"
        return 1
    fi
}

function frontend_check() {
    echo -e "${GREEN}Running svelte-check for type errors...${NC}"
    cd frontend && npm run check
}

function frontend_preview() {
    echo -e "${GREEN}Previewing production build...${NC}"
    echo -e "${YELLOW}URL: http://localhost:4173${NC}"
    echo ""
    cd frontend && npm run preview
}

# ═══════════════════════════════════════════════════════════════════════════════
# API Schema Generation
# ═══════════════════════════════════════════════════════════════════════════════

OPENAPI_OUTPUT="frontend/src/lib/api/openapi.json"
TS_CLIENT_OUTPUT="frontend/src/lib/api/generated.ts"

function api_export_schema() {
    echo -e "${GREEN}Exporting OpenAPI schema from FastAPI...${NC}"

    # Ensure output directory exists
    mkdir -p "$(dirname "$OPENAPI_OUTPUT")"

    # Export OpenAPI schema using the enhanced script
    pipenv run python backend/test_scripts/list_api_endpoints.py --openapi-file "$OPENAPI_OUTPUT"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ OpenAPI schema exported to: $OPENAPI_OUTPUT${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to export OpenAPI schema${NC}"
        return 1
    fi
}

function api_generate_client() {
    echo -e "${GREEN}Generating TypeScript client from OpenAPI schema...${NC}"

    # Check if openapi.json exists
    if [ ! -f "$OPENAPI_OUTPUT" ]; then
        echo -e "${YELLOW}⚠️  OpenAPI schema not found. Running api:schema first...${NC}"
        api_export_schema || return 1
    fi

    # Check if openapi-zod-client is installed
    if ! command -v npx &> /dev/null; then
        echo -e "${RED}❌ npx not found. Please install Node.js${NC}"
        return 1
    fi

    # Generate TypeScript client with Zod schemas
    cd frontend && npx openapi-zod-client "../$OPENAPI_OUTPUT" \
        --output "src/lib/api/generated.ts" \
        --with-alias \
        --export-schemas

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ TypeScript client generated: $TS_CLIENT_OUTPUT${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to generate TypeScript client${NC}"
        echo -e "${YELLOW}💡 Tip: Run 'cd frontend && npm install openapi-zod-client zod' to install dependencies${NC}"
        return 1
    fi
}

function api_sync() {
    echo -e "${BLUE}${BOLD}Syncing API schema and TypeScript client...${NC}"
    echo ""

    # Step 1: Export OpenAPI schema
    api_export_schema || return 1
    echo ""

    # Step 2: Generate TypeScript client
    api_generate_client || return 1
    echo ""

    echo -e "${GREEN}${BOLD}✅ API sync complete!${NC}"
    echo -e "${YELLOW}Files updated:${NC}"
    echo -e "  📄 $OPENAPI_OUTPUT"
    echo -e "  📄 $TS_CLIENT_OUTPUT"
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
    local db_path="${1:-$(get_database_path)}"
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
        echo -e "${YELLOW}Database: $(get_database_path) (default)${NC}"
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
        ALEMBIC_DATABASE_URL="$db_url" pipenv run python -m backend.alembic.check_constraints_hook --log-level info
        check_result=$?
    else
        pipenv run python -m backend.alembic.check_constraints_hook --log-level info
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
        ALEMBIC_DATABASE_URL="$db_url" pipenv run python -m backend.alembic.check_constraints_hook --log-level debug
        check_result=$?
    else
        pipenv run python -m backend.alembic.check_constraints_hook --log-level debug
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
        echo -e "${YELLOW}Database: $(get_database_path) (default)${NC}"
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
    echo -e "${GREEN}Opening shell in virtualenv...${NC}"
    pipenv shell
}

function list_api_endpoints() {
    echo -e "${GREEN}Listing all API endpoints...${NC}"
    echo ""
    pipenv run python backend/test_scripts/list_api_endpoints.py
}

# Main command dispatcher
COMMAND="${1:-help}"

case "$COMMAND" in
    install)
        install_deps
        ;;
    server)
        start_server
        ;;
    server:test)
        start_server_test
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
    info:api)
        list_api_endpoints
        ;;
    fe:dev)
        frontend_dev
        ;;
    fe:build)
        frontend_build
        ;;
    fe:check)
        frontend_check
        ;;
    fe:preview)
        frontend_preview
        ;;
    i18n:audit)
        echo -e "${GREEN}Running i18n translation audit...${NC}"
        cd frontend && npm run i18n:audit
        ;;
    i18n:audit:md)
        echo -e "${GREEN}Exporting i18n audit Markdown ...${NC}"
        cd frontend && npm run i18n:audit:md
        ;;
    i18n:audit:xlsx)
        echo -e "${GREEN}Exporting i18n audit to Excel...${NC}"
        cd frontend && npm run i18n:audit:xlsx
        ;;
    i18n:audit:both)
        echo -e "${GREEN}Exporting i18n audit (Markdown + Excel)...${NC}"
        cd frontend && npm run i18n:audit:both
        ;;
    api:schema)
        api_export_schema
        ;;
    api:client)
        api_generate_client
        ;;
    api:sync)
        api_sync
        ;;
    user:create)
        shift
        if [ $# -lt 3 ]; then
            echo -e "${RED}Usage: ./dev.sh user:create <username> <email> <password>${NC}"
            exit 1
        fi
        echo -e "${GREEN}Creating superuser...${NC}"
        pipenv run python user_cli.py create-superuser "$1" "$2" "$3"
        ;;
    user:reset)
        shift
        if [ $# -lt 2 ]; then
            echo -e "${RED}Usage: ./dev.sh user:reset <username> <new_password>${NC}"
            exit 1
        fi
        echo -e "${GREEN}Resetting password...${NC}"
        pipenv run python user_cli.py reset-password "$1" "$2"
        ;;
    user:list)
        echo -e "${GREEN}Listing users...${NC}"
        pipenv run python user_cli.py list-users
        ;;
    user:activate)
        shift
        if [ $# -lt 1 ]; then
            echo -e "${RED}Usage: ./dev.sh user:activate <username>${NC}"
            exit 1
        fi
        echo -e "${GREEN}Activating user...${NC}"
        pipenv run python user_cli.py activate "$1"
        ;;
    user:deactivate)
        shift
        if [ $# -lt 1 ]; then
            echo -e "${RED}Usage: ./dev.sh user:deactivate <username>${NC}"
            exit 1
        fi
        echo -e "${GREEN}Deactivating user...${NC}"
        pipenv run python user_cli.py deactivate "$1"
        ;;
    test:coverage)
        echo -e "${GREEN}Running all tests with coverage tracking...${NC}"
        echo ""
        ./test_runner.py --coverage all
        ;;
    info:mk)
        shift
        subcommand="${1:-help}"
        if [ "$subcommand" = "help" ]; then
            echo -e "${GREEN}MkDocs Helper Commands:${NC}"
            echo "  build    Build documentation (mkdocs build)"
            echo "  serve    Serve documentation locally (mkdocs serve)"
            echo "  clean    Remove built site/ directory"
            echo "  help     Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./dev.sh info:mk build"
            echo "  ./dev.sh info:mk serve"
            echo ""
            exit 0
        fi
        case "$subcommand" in
            build)
                echo -e "${GREEN}Building MkDocs site...${NC}"
                pipenv run mkdocs build -f mkdocs_src/mkdocs.yml
                ;;
            serve)
                echo -e "${GREEN}Serving MkDocs site (http://127.0.0.1:8002)${NC}"
                pipenv run mkdocs serve -f mkdocs_src/mkdocs.yml -a 127.0.0.1:8002
                ;;
            clean)
                echo -e "${YELLOW}Removing site directory...${NC}"
                rm -rf site
                ;;
            *)
                echo -e "${RED}Unknown mkdocs info subcommand${NC}"
                exit 1
                ;;
        esac
        exit 0
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

# TODO: IDEA: in futuro potrebbe servire inviare il DB privatamente quando c'è un problema, c'è ovviamente un problema di privacy in ciò, ma necessario per risolvere eventuali problemi complessi.
# Potrebbe essere una funzione tipo ./dev.sh db:export-for-support <path-to-export> <scale> che moltiplica o divide tutti gli importi per un fattore di scala (es. 0.01 per ridurre 100x gli importi) e rimuove tutti i dati personali (nomi, email, note, descrizioni, ecc.) lasciando solo i dati essenziali per riprodurre il problema e numeri in propozione uguali, ma in concreto casuali, a patto che l'utente non mette un fattore di scala banale.
# Non sono sicuro basti, forse servirà poter inviare anche altro, ma è un inizio.
