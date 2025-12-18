"""
LibreFolio Test Utilities Library

Common utilities for all test scripts to avoid code duplication.
Provides standardized output formatting, test helpers, and common functions.
"""
import sys
import time


# ============================================================================
# ANSI COLOR CODES
# ============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


# ============================================================================
# OUTPUT FORMATTING FUNCTIONS
# ============================================================================

def print_header(text: str):
    """Print a formatted header (large, centered)."""
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.NC}")
    print(f"{Colors.CYAN}{text:^70}{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}\n")


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n{'-' * 60}")
    print(f"  {title}")
    print('-' * 60)


def print_success(message: str):
    """Print a success message with green checkmark."""
    print(f"{Colors.GREEN}✅ {message}{Colors.NC}")


def print_error(message: str):
    """Print an error message with red X."""
    print(f"{Colors.RED}❌ {message}{Colors.NC}")


def print_warning(message: str):
    """Print a warning message with yellow warning symbol."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")


def print_info(message: str):
    """Print an info message with blue info symbol."""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.NC}")


def print_prerequisite(message: str):
    """Print a prerequisite message with magenta symbol."""
    print(f"{Colors.MAGENTA}📋 Prerequisite: {message}{Colors.NC}")


def print_step(step_num: int, message: str):
    """Print a test step with number."""
    print(f"{Colors.CYAN}[Step {step_num}] {message}{Colors.NC}")


def print_bold(message: str):
    """Print a bold message."""
    print(f"{Colors.BOLD}{message}{Colors.NC}")


# ============================================================================
# TEST SUMMARY FUNCTIONS
# ============================================================================

def print_test_summary(results: dict[str, bool], suite_name: str = "Test Suite"):
    """
    Print a formatted test summary.

    Args:
        results: Dictionary mapping test name to pass/fail boolean
        suite_name: Name of the test suite
    """
    print_section(f"{suite_name} Summary")

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if result else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status}: {test_name}")

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed}/{total} tests passed")
    print('=' * 60)

    if passed == total:
        print_success(f"All {suite_name.lower()} passed! 🎉")
    else:
        print_error(f"{total - passed} test(s) failed")

    return passed == total


# ============================================================================
# TEST HEADER FUNCTION
# ============================================================================

def print_test_header(title: str, description: str = None, prerequisites: list[str] = None):
    """
    Print a standardized test header.

    Args:
        title: Test suite title
        description: Optional description of what tests verify
        prerequisites: Optional list of prerequisites
    """
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

    if description:
        print(f"\n{description}")

    if prerequisites:
        print(f"\n{Colors.MAGENTA}📋 Prerequisites:{Colors.NC}")
        for prereq in prerequisites:
            print(f"   • {prereq}")
        print()


# ============================================================================
# EXIT HELPERS
# ============================================================================

def exit_success():
    """Exit with success code."""
    sys.exit(0)


def exit_failure():
    """Exit with failure code."""
    sys.exit(1)


def exit_with_result(success: bool):
    """Exit with appropriate code based on result."""
    sys.exit(0 if success else 1)

# ============================================================================
# RECORDS HELPER
# ============================================================================

# Helper to generate unique identifiers
_counter = 0

def unique_id(prefix: str = "TEST") -> str:
    """Generate unique identifier for test data."""
    global _counter
    _counter += 1
    return f"{prefix}_{int(time.time() * 1000)}_{_counter}"
