#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""
LibreFolio Development CLI

Unified command-line interface for development tasks.
Supports autocompletion via argcomplete.

Usage:
    ./dev.py <command> [options]
    python dev.py <command> [options]

Autocompletion setup:
    # Add to ~/.bashrc or ~/.zshrc:
    eval "$(register-python-argcomplete dev.py)"
"""

import os
import sys
from pathlib import Path

try:
    import argcomplete
    HAS_ARGCOMPLETE = True
except ImportError:
    HAS_ARGCOMPLETE = False

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# Change to project root for consistent paths
os.chdir(PROJECT_ROOT)

from scripts.cli_base import (
    Colors,
    get_server_port,
    get_test_server_port,
    get_database_path,
    get_test_database_path,
    run_pipenv,
    run_command_live,
    print_header,
    print_success,
    print_error,
    print_warning,
    check_server_running,
)

from scripts.cli_tree_parser import TreeParser, format_help


# =============================================================================
# Backend Commands: Server
# =============================================================================

def cmd_server(args):
    """Start the development server."""
    test_mode = getattr(args, 'test', False)
    rebuild = getattr(args, 'rebuild', False)
    debug_mode = getattr(args, 'debug', False)

    if test_mode:
        port = get_test_server_port()
        db = get_test_database_path()
    else:
        port = get_server_port()
        db = get_database_path()

    # Handle frontend rebuild
    if rebuild:
        print(Colors.info("📦 Forcing frontend rebuild..."))
        # Create a mock args object with debug flag
        class BuildArgs:
            debug = debug_mode
        result = cmd_fe_build(BuildArgs())
        if result != 0:
            print_error("Frontend build failed. Server not started.")
            return result
    else:
        # Auto-build frontend if needed (respects debug mode)
        result = auto_build_frontend(debug=debug_mode)
        if result is not None and result != 0:
            print_error("Frontend build failed. Server not started.")
            return result

    auto_build_mkdocs()
    update_js_cache()

    if test_mode:
        print(Colors.success("Starting LibreFolio API server (TEST MODE)..."))
        print(Colors.warning(f"Database: {db}"))
        print(Colors.warning(f"Port: {port}"))
        print()
        print(f"{Colors.RED}{Colors.BOLD}⚠️  TEST MODE - Using test database!{Colors.NC}")
        print()
    else:
        mode_str = " (DEBUG MODE)" if debug_mode else ""
        print(Colors.success(f"Starting LibreFolio API server{mode_str}..."))
        print(Colors.warning(f"Database: {db}"))
        print(Colors.warning(f"Port: {port}"))
        if debug_mode:
            print(Colors.warning("Log Level: DEBUG"))
        print()
        print(f"{Colors.BLUE}{Colors.BOLD}Available endpoints:{Colors.NC}")
        print(f" ├── 🏠 {Colors.YELLOW}Frontend:  http://localhost:{port}/{Colors.NC}")
        print(f" ├── 💻 {Colors.YELLOW}API Redoc: http://localhost:{port}/api/v1/redoc{Colors.NC}")
        print(f" ├── 🚀 {Colors.YELLOW}API Docs:  http://localhost:{port}/api/v1/docs{Colors.NC}")
        print(f" └── 📚 {Colors.YELLOW}User Doc:  http://localhost:{port}/mkdocs/{Colors.NC}")
        print()

        if (PROJECT_ROOT / "frontend" / "build" / "index.html").exists():
            print_success("Frontend build found - UI available at /")
        else:
            print_warning("No frontend build - run './dev.py front build' to enable UI")
        print()

    env = os.environ.copy()
    if test_mode:
        env["LIBREFOLIO_TEST_MODE"] = "1"
    if debug_mode:
        env["LIBREFOLIO_LOG_LEVEL"] = "DEBUG"

    return run_command_live([
        "pipenv", "run", "uvicorn",
        "backend.app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", str(port)
    ], env=env)


# =============================================================================
# Backend Commands: Database
# =============================================================================

def cmd_db_check(args):
    """Verify CHECK constraints in database."""
    db_path = args.path or get_database_path()
    print(Colors.success(f"Checking database constraints: {db_path}"))
    return run_pipenv(["python", "backend/test_scripts/verify_db_check_constraints.py", db_path])


def cmd_db_current(args):
    """Show current database migration."""
    db_path = args.path or get_database_path()
    print(Colors.success(f"Current migration for: {db_path}"))

    env = {"DATABASE_URL": f"sqlite:///{PROJECT_ROOT / db_path}"} if db_path else {}
    return run_command_live(
        ["pipenv", "run", "alembic", "-c", "backend/alembic.ini", "current"],
        env=env
    )


def cmd_db_migrate(args):
    """Create a new migration."""
    if not check_server_running("creating migrations", strict=True):
        return 1

    db_path = args.path or get_database_path()
    message = args.message

    print(Colors.success(f"Creating migration: {message}"))

    env = {"DATABASE_URL": f"sqlite:///{PROJECT_ROOT / db_path}"} if db_path else {}
    return run_command_live(
        ["pipenv", "run", "alembic", "-c", "backend/alembic.ini", "revision", "--autogenerate", "-m", message],
        env=env
    )


def cmd_db_upgrade(args):
    """Apply pending migrations."""
    if not check_server_running("applying migrations", strict=True):
        return 1

    db_path = args.path or get_database_path()
    print(Colors.success(f"Upgrading database: {db_path}"))

    env = {"DATABASE_URL": f"sqlite:///{PROJECT_ROOT / db_path}"} if db_path else {}
    return run_command_live(
        ["pipenv", "run", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        env=env
    )


def cmd_db_downgrade(args):
    """Rollback one migration."""
    if not check_server_running("rolling back migrations", strict=True):
        return 1

    db_path = args.path or get_database_path()
    print(Colors.success(f"Downgrading database: {db_path}"))

    env = {"DATABASE_URL": f"sqlite:///{PROJECT_ROOT / db_path}"} if db_path else {}
    return run_command_live(
        ["pipenv", "run", "alembic", "-c", "backend/alembic.ini", "downgrade", "-1"],
        env=env
    )


def cmd_db_create_clean(args):
    """Delete database and recreate with latest migration."""
    if not check_server_running("recreating database", strict=True):
        return 1

    test_mode = getattr(args, 'test', False)
    if test_mode:
        db_path = Path(get_test_database_path())
    else:
        db_path = Path(get_database_path())

    full_path = PROJECT_ROOT / db_path

    # Delete existing database if exists
    if full_path.exists():
        print(Colors.warning(f"Deleting existing database: {db_path}"))
        full_path.unlink()
        print_success("Database deleted")
    else:
        print(Colors.info(f"Database does not exist: {db_path}"))

    # Create fresh database with migrations
    print(Colors.success(f"Creating fresh database: {db_path}"))

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{full_path}"
    if test_mode:
        env["LIBREFOLIO_TEST_MODE"] = "1"

    result = run_command_live(
        ["pipenv", "run", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        env=env
    )

    if result == 0:
        print_success(f"Database created successfully: {db_path}")
    else:
        print_error("Failed to create database")

    return result


# =============================================================================
# Frontend Commands
# =============================================================================

def cmd_fe_dev(args):
    """Start frontend development server."""
    print(Colors.success("Starting frontend development server..."))
    print(Colors.warning("URL: http://localhost:5173"))
    print()
    return run_command_live(["npm", "run", "dev"], cwd=PROJECT_ROOT / "frontend")


def cmd_fe_build(args):
    """Build frontend for production."""
    if args.debug:
        print(Colors.success("Building frontend in DEBUG mode (no minify, with sourcemaps)..."))
        result = run_command_live(["npm", "run", "build:debug"], cwd=PROJECT_ROOT / "frontend")
    else:
        print(Colors.success("Building frontend for production..."))
        result = run_command_live(["npm", "run", "build"], cwd=PROJECT_ROOT / "frontend")

    if result == 0:
        print_success("Frontend build complete!")
        print(Colors.warning("Output in: frontend/build/"))
    else:
        print_error("Frontend build failed")
    return result


def cmd_fe_check(args):
    """Run svelte-check for type errors."""
    print(Colors.success("Running svelte-check for type errors..."))
    return run_command_live(["npm", "run", "check"], cwd=PROJECT_ROOT / "frontend")


def cmd_fe_preview(args):
    """Preview production build."""
    print(Colors.success("Previewing production build..."))
    print(Colors.warning("URL: http://localhost:4173"))
    print()
    return run_command_live(["npm", "run", "preview"], cwd=PROJECT_ROOT / "frontend")


# =============================================================================
# API Schema Commands
# =============================================================================

def cmd_api_schema(args):
    """Export OpenAPI schema."""
    print(Colors.success("Exporting OpenAPI schema..."))
    return run_pipenv(["python", "backend/test_scripts/export_openapi.py"])


def cmd_api_client(args):
    """Generate TypeScript client from OpenAPI schema."""
    print(Colors.success("Generating TypeScript client..."))
    return run_command_live(
        ["npm", "run", "generate-api"],
        cwd=PROJECT_ROOT / "frontend"
    )


def cmd_api_sync(args):
    """Export schema and generate client."""
    result = cmd_api_schema(args)
    if result != 0:
        return result
    return cmd_api_client(args)



# =============================================================================
# Info Commands
# =============================================================================

def cmd_info_api(args):
    """List all API endpoints."""
    print(Colors.success("Listing all API endpoints..."))
    return run_pipenv(["python", "scripts/list_api_endpoints.py"])


# =============================================================================
# MkDocs Commands
# =============================================================================

def cmd_mkdocs_build(args):
    """Build MkDocs documentation."""
    print(Colors.success("Building MkDocs site..."))
    copy_docs_assets()
    return run_pipenv(["mkdocs", "build", "-f", "mkdocs_src/mkdocs.yml"])


def cmd_mkdocs_serve(args):
    """Serve MkDocs documentation locally."""
    print(Colors.success("Serving MkDocs site (http://127.0.0.1:8002)"))
    copy_docs_assets()
    return run_pipenv(["mkdocs", "serve", "-f", "mkdocs_src/mkdocs.yml", "-a", "127.0.0.1:8002"])


def cmd_mkdocs_clean(args):
    """Remove built site directory."""
    print(Colors.warning("Removing site directory..."))
    import shutil
    site_dir = PROJECT_ROOT / "mkdocs_src" / "site"
    if site_dir.exists():
        shutil.rmtree(site_dir)
    print_success("Site directory removed")
    return 0


def cmd_mkdocs_deploy(args):
    """Deploy MkDocs to GitHub Pages."""
    print(Colors.success("Deploying MkDocs site to GitHub Pages..."))
    copy_docs_assets()
    return run_pipenv(["mkdocs", "gh-deploy", "-f", "mkdocs_src/mkdocs.yml"])



# =============================================================================
# Format/Lint Commands
# =============================================================================

def cmd_format(args):
    """Format code with black."""
    print(Colors.success("Formatting code with black..."))
    return run_pipenv(["black", "backend/"])


def cmd_lint(args):
    """Lint code with ruff."""
    print(Colors.success("Linting code with ruff..."))
    return run_pipenv(["ruff", "check", "backend/"])


# =============================================================================
# Shell/Install Commands
# =============================================================================

def cmd_shell(args):
    """Open shell in virtualenv."""
    print(Colors.success("Opening shell in virtualenv..."))
    return run_command_live(["pipenv", "shell"])


def cmd_install(args):
    """Install all dependencies."""
    print_header("Installing LibreFolio Dependencies")
    print()

    print(Colors.info("[1/4] Installing Python backend dependencies..."))
    result = run_command_live(["pipenv", "install", "--dev"])
    if result != 0:
        print_error("Failed to install Python dependencies")
        return result
    print_success("Python dependencies installed")
    print()

    print(Colors.info("[2/4] Installing root project tools..."))
    result = run_command_live(["npm", "install"])
    if result != 0:
        print_error("Failed to install root npm dependencies")
        return result
    print_success("Root project tools installed")
    print()

    print(Colors.info("[3/4] Installing frontend dependencies..."))
    result = run_command_live(["npm", "install"], cwd=PROJECT_ROOT / "frontend")
    if result != 0:
        print_error("Failed to install frontend dependencies")
        return result
    print_success("Frontend dependencies installed")
    print()

    print(Colors.info("[4/4] Installing Playwright browsers..."))
    print(Colors.warning("   (This may take a while, ~500-700MB download)"))
    result = run_command_live(["npx", "playwright", "install"])
    if result != 0:
        print_warning("Playwright browser installation had issues (non-critical)")
    else:
        print_success("Playwright browsers installed")
    print()

    print_header("✅ All dependencies installed!")
    return 0


# =============================================================================
# Helper Functions
# =============================================================================

def auto_build_frontend(debug=False):
    """Auto-build frontend if needed."""
    build_dir = PROJECT_ROOT / "frontend" / "build"
    src_dir = PROJECT_ROOT / "frontend" / "src"

    needs_build = False

    if not build_dir.exists() or not (build_dir / "index.html").exists():
        print(Colors.info("📦 Frontend build missing, building..."))
        needs_build = True
    else:
        try:
            build_time = (build_dir / "index.html").stat().st_mtime
            for src_file in src_dir.rglob("*"):
                if src_file.is_file() and src_file.stat().st_mtime > build_time:
                    print(Colors.info("📦 Frontend sources changed, rebuilding..."))
                    needs_build = True
                    break
        except Exception:
            pass

    if needs_build:
        # Create args object for cmd_fe_build
        class BuildArgs:
            pass
        args = BuildArgs()
        args.debug = debug
        return cmd_fe_build(args)

    return None  # No build needed


def auto_build_mkdocs():
    """Auto-build mkdocs if needed."""
    site_dir = PROJECT_ROOT / "mkdocs_src" / "site"
    docs_dir = PROJECT_ROOT / "mkdocs_src" / "docs"

    if not site_dir.exists() or not (site_dir / "index.html").exists():
        print(Colors.info("📚 Documentation build missing, building..."))
        copy_docs_assets()
        run_pipenv(["mkdocs", "build", "-f", "mkdocs_src/mkdocs.yml"])
        return

    try:
        build_time = (site_dir / "index.html").stat().st_mtime
        for doc_file in docs_dir.rglob("*.md"):
            if doc_file.stat().st_mtime > build_time:
                print(Colors.info("📚 Documentation changed, rebuilding..."))
                copy_docs_assets()
                run_pipenv(["mkdocs", "build", "-f", "mkdocs_src/mkdocs.yml"])
                return
    except Exception:
        pass


def copy_docs_assets():
    """Copy logo and favicon to docs."""
    import shutil
    static_dir = PROJECT_ROOT / "mkdocs_src" / "docs" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    src_logo = PROJECT_ROOT / "frontend" / "static" / "logo.png"
    src_favicon = PROJECT_ROOT / "frontend" / "static" / "favicon.png"

    if src_logo.exists():
        shutil.copy(src_logo, static_dir / "logo.png")
    if src_favicon.exists():
        shutil.copy(src_favicon, static_dir / "favicon.png")


def update_js_cache():
    """Update JS library cache."""
    result = run_command_live(
        ["pipenv", "run", "python", "scripts/update_js_cache.py"],
        cwd=PROJECT_ROOT
    )
    if result == 0:
        print_success("JS libraries cached")
    else:
        print_warning("JS cache update failed (will use CDN fallback)")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = TreeParser(
        description="LibreFolio Development CLI",
        formatter_class=format_help,
        epilog="""
Commands by Category:

  🖥️  Backend
      server              Start development server (--test for test mode)
      db                  Database commands (check, upgrade, create-clean...)

  🎨  Frontend
      front               Frontend commands (dev, build, check, preview)

  🧪  Testing
      test                Run tests (api, db, external, schemas, services...)

  👤  Users
      user                User management (create, list, reset, promote...)

  📚  Documentation
      mkdocs              MkDocs commands (build, serve, clean, deploy)

  📦  Tools
      api                 API schema commands (schema, client, sync)
      i18n                Translation commands (audit)
      cache               Cache management (js)
      info                Information commands (api)
      format              Format code with black
      lint                Lint code with ruff

  🔧  Setup
      shell               Open pipenv shell
      install             Install all dependencies

Examples:
  ./dev.py server              Start development server
  ./dev.py server --test       Start in test mode (test database)
  ./dev.py server --debug      Start with DEBUG logging + debug frontend build
  ./dev.py server --rebuild    Force rebuild frontend before starting
  ./dev.py server -r -d        Rebuild frontend in debug mode + DEBUG logs
  ./dev.py test api auth       Run auth API tests
  ./dev.py db upgrade          Apply migrations
  ./dev.py db create-clean     Delete and recreate database
  ./dev.py front build         Build frontend
  ./dev.py mkdocs serve        Serve documentation locally
  ./dev.py user list           List all users
"""
    )

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    # =========================================================================
    # 🖥️ Backend Commands Group
    # =========================================================================

    # Server (unified with --test flag)
    p = subparsers.add_parser("server", help="🖥️  Start development server")
    p.add_argument("--test", "-t", action="store_true", help="Use test database (port 8001)")
    p.add_argument("--rebuild", "-r", action="store_true", help="Force rebuild frontend before starting")
    p.add_argument("--debug", "-d", action="store_true", help="Debug mode: verbose logging + frontend debug build")
    p.set_defaults(func=cmd_server)

    # Database
    p = subparsers.add_parser("db", help="🖥️  Database commands")
    db_sub = p.add_subparsers(dest="db_cmd", metavar="action")

    db_p = db_sub.add_parser("check", help="Verify CHECK constraints")
    db_p.add_argument("path", nargs="?", help="Database path (default: app.db)")
    db_p.set_defaults(func=cmd_db_check)

    db_p = db_sub.add_parser("current", help="Show current migration")
    db_p.add_argument("path", nargs="?", help="Database path")
    db_p.set_defaults(func=cmd_db_current)

    db_p = db_sub.add_parser("migrate", help="Create new migration")
    db_p.add_argument("message", help="Migration message")
    db_p.add_argument("path", nargs="?", help="Database path")
    db_p.set_defaults(func=cmd_db_migrate)

    db_p = db_sub.add_parser("upgrade", help="Apply pending migrations")
    db_p.add_argument("path", nargs="?", help="Database path")
    db_p.set_defaults(func=cmd_db_upgrade)

    db_p = db_sub.add_parser("downgrade", help="Rollback one migration")
    db_p.add_argument("path", nargs="?", help="Database path")
    db_p.set_defaults(func=cmd_db_downgrade)

    db_p = db_sub.add_parser("create-clean", help="Delete DB and recreate with latest migration")
    db_p.add_argument("--test", "-t", action="store_true", help="Use test database")
    db_p.set_defaults(func=cmd_db_create_clean)

    # =========================================================================
    # 🎨 Frontend Commands Group
    # =========================================================================

    p = subparsers.add_parser("front", help="🎨 Frontend commands")
    fe_sub = p.add_subparsers(dest="fe_cmd", metavar="action")

    fe_p = fe_sub.add_parser("dev", help="Start dev server with HMR")
    fe_p.set_defaults(func=cmd_fe_dev)

    fe_p = fe_sub.add_parser("build", help="Build for production")
    fe_p.add_argument("--debug", "-d", action="store_true", help="Build in debug mode (no minify, with sourcemaps)")
    fe_p.set_defaults(func=cmd_fe_build)

    fe_p = fe_sub.add_parser("check", help="Type check with svelte-check")
    fe_p.set_defaults(func=cmd_fe_check)

    fe_p = fe_sub.add_parser("preview", help="Preview production build")
    fe_p.set_defaults(func=cmd_fe_preview)

    # =========================================================================
    # 🧪 Testing Commands - Import from test_runner
    # =========================================================================

    from scripts.test_runner import register_subparser as register_test_parser
    register_test_parser(subparsers)

    # =========================================================================
    # 👤 User Commands - Import from user_cli
    # =========================================================================

    from scripts.user_cli import register_subparser as register_user_parser
    register_user_parser(subparsers)

    # =========================================================================
    # 📚 Documentation Commands
    # =========================================================================

    p = subparsers.add_parser("mkdocs", help="📚 MkDocs documentation commands")
    mk_sub = p.add_subparsers(dest="mk_cmd", metavar="action")

    mk_p = mk_sub.add_parser("build", help="Build documentation site")
    mk_p.set_defaults(func=cmd_mkdocs_build)

    mk_p = mk_sub.add_parser("serve", help="Serve documentation locally (port 8002)")
    mk_p.set_defaults(func=cmd_mkdocs_serve)

    mk_p = mk_sub.add_parser("clean", help="Remove built site/ directory")
    mk_p.set_defaults(func=cmd_mkdocs_clean)

    mk_p = mk_sub.add_parser("deploy", help="Deploy to GitHub Pages")
    mk_p.set_defaults(func=cmd_mkdocs_deploy)

    # =========================================================================
    # 📦 Tools Commands Group
    # =========================================================================

    # API
    p = subparsers.add_parser("api", help="📦 API schema commands")
    api_sub = p.add_subparsers(dest="api_cmd", metavar="action")

    api_p = api_sub.add_parser("schema", help="Export OpenAPI schema")
    api_p.set_defaults(func=cmd_api_schema)

    api_p = api_sub.add_parser("client", help="Generate TypeScript client")
    api_p.set_defaults(func=cmd_api_client)

    api_p = api_sub.add_parser("sync", help="Export schema + generate client")
    api_p.set_defaults(func=cmd_api_sync)

    # i18n - Import from frontend/scripts/i18n-audit.py
    sys.path.insert(0, str(PROJECT_ROOT / "frontend" / "scripts"))
    from importlib import import_module
    i18n_module = import_module("i18n-audit")
    i18n_module.register_subparser(subparsers)

    # Cache - Import from scripts/update_js_cache.py
    from scripts.update_js_cache import register_subparser as register_cache_parser
    register_cache_parser(subparsers)

    # Info
    p = subparsers.add_parser("info", help="📦 Information commands")
    info_sub = p.add_subparsers(dest="info_cmd", metavar="action")

    info_p = info_sub.add_parser("api", help="List all API endpoints")
    info_p.set_defaults(func=cmd_info_api)

    # Format & Lint
    p = subparsers.add_parser("format", help="📦 Format code with black")
    p.set_defaults(func=cmd_format)

    p = subparsers.add_parser("lint", help="📦 Lint code with ruff")
    p.set_defaults(func=cmd_lint)

    # =========================================================================
    # 🔧 Setup Commands Group
    # =========================================================================

    p = subparsers.add_parser("shell", help="🔧 Open pipenv shell")
    p.set_defaults(func=cmd_shell)

    p = subparsers.add_parser("install", help="🔧 Install all dependencies")
    p.set_defaults(func=cmd_install)

    # =========================================================================
    # Enable autocompletion and parse
    # =========================================================================

    if HAS_ARGCOMPLETE:
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    if hasattr(args, 'func'):
        return args.func(args) or 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())

