#!/usr/bin/env python3
"""
LibreFolio Test Runner

Central test orchestrator for running backend and frontend tests.
Supports test execution in the correct order and environment reset.

Usage:
    python test_runner.py db validate          # Validate database schema
    python test_runner.py db populate          # Populate database with sample data
    python test_runner.py db all               # Run all database tests
    python test_runner.py --reset db all       # Reset environment and run all DB tests

Author: LibreFolio Contributors
"""

import argparse
import subprocess
import sys
from pathlib import Path


# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.NC}")
    print(f"{Colors.CYAN}{text:^70}{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}\n")


def print_section(text: str):
    """Print a section title."""
    print(f"\n{Colors.BLUE}{'▶' * 3} {text}{Colors.NC}")
    print(f"{Colors.BLUE}{'-' * 70}{Colors.NC}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.NC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.NC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.NC}")


def run_command(cmd: list[str], description: str) -> bool:
    """
    Run a command and return True if successful.

    Args:
        cmd: Command to run as list
        description: Description for logging

    Returns:
        bool: True if command succeeded
    """
    print(f"\n{Colors.BLUE}Running: {description}{Colors.NC}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=False,
            text=True,
        )

        if result.returncode == 0:
            print_success(f"{description} - PASSED")
            return True
        else:
            print_error(f"{description} - FAILED (exit code: {result.returncode})")
            return False

    except Exception as e:
        print_error(f"{description} - ERROR: {e}")
        return False


def reset_environment():
    """Reset the database environment."""
    print_section("Resetting Environment")

    db_path = Path(__file__).parent / "backend" / "data" / "sqlite" / "app.db"

    if db_path.exists():
        print_warning(f"Removing existing database: {db_path}")
        db_path.unlink()
        print_success("Database removed")
    else:
        print_warning("No database found, nothing to remove")

    # Run migrations
    print("\nApplying fresh migrations...")
    success = run_command(
        ["./dev.sh", "db:upgrade"],
        "Alembic migrations"
    )

    if success:
        print_success("Environment reset complete")
    else:
        print_error("Environment reset failed")

    return success


def run_db_validate() -> bool:
    """Run database schema validation."""
    print_section("Database Schema Validation")
    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_db.db_schema_validate"],
        "DB Schema Validation"
    )


def run_db_populate() -> bool:
    """Run database population script."""
    print_section("Database Population")
    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_db.populate_db"],
        "DB Population"
    )


def run_db_tests(reset: bool = False) -> bool:
    """
    Run all database tests in order.

    Args:
        reset: Whether to reset environment first

    Returns:
        bool: True if all tests passed
    """
    print_header("LibreFolio Database Tests")

    if reset:
        if not reset_environment():
            return False

    # Test order matters!
    tests = [
        ("Schema Validation", run_db_validate),
        ("Database Population", run_db_populate),
    ]

    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))

        if not success:
            print_error(f"Test failed: {test_name}")
            print_warning("Stopping test execution")
            break

    # Summary
    print_section("Test Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if success else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print_success("All database tests passed! 🎉")
        return True
    else:
        print_error(f"{total - passed} test(s) failed")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LibreFolio Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner.py db validate          # Validate database schema
  python test_runner.py db populate          # Populate database
  python test_runner.py db all               # Run all DB tests
  python test_runner.py --reset db all       # Reset env and run all DB tests
  
  # Future examples (when implemented):
  python test_runner.py api all              # Run all API tests
  python test_runner.py frontend all         # Run all frontend tests
  python test_runner.py --reset all          # Reset and run all tests
        """
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset environment (delete DB, rerun migrations) before tests"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )

    subparsers = parser.add_subparsers(dest="category", help="Test category")

    # Database tests
    db_parser = subparsers.add_parser("db", help="Database tests")
    db_parser.add_argument(
        "action",
        choices=["validate", "populate", "all"],
        help="Database test action"
    )

    # Future: API tests
    # api_parser = subparsers.add_parser("api", help="API tests")
    # api_parser.add_argument("action", choices=["endpoints", "all"])

    # Future: Frontend tests
    # frontend_parser = subparsers.add_parser("frontend", help="Frontend tests")
    # frontend_parser.add_argument("action", choices=["unit", "e2e", "all"])

    # Parse arguments
    args = parser.parse_args()

    if not args.category:
        parser.print_help()
        return 0

    # Route to appropriate test handler
    success = False

    if args.category == "db":
        if args.action == "validate":
            success = run_db_validate()
        elif args.action == "populate":
            success = run_db_populate()
        elif args.action == "all":
            success = run_db_tests(reset=args.reset)

    # Exit with appropriate code
    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Test execution interrupted by user{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

