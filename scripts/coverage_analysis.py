#!/usr/bin/env python3
"""
Coverage Analysis Tool for LibreFolio.

Finds functions where the `def` line is executed (covered) but the first
statement in the body is NOT covered — indicating the function was never
actually called during tests.

Usage:
    # Generate coverage JSON first:
    coverage json -o /tmp/cov_report.json

    # Then run analysis:
    python scripts/coverage_analysis.py                  # Full report
    python scripts/coverage_analysis.py --priority high  # Only HIGH priority
    python scripts/coverage_analysis.py --json           # Machine-readable output
    python scripts/coverage_analysis.py --summary        # Summary counts only

    # Or via dev.py:
    ./dev.py test coverage-report

Author: LibreFolio Contributors
"""

import argparse
import ast
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()


# ---------------------------------------------------------------------------
# Priority classification rules
# ---------------------------------------------------------------------------

PRIORITY_MAP = {
    # HIGH — core business logic
    "backend/app/services/asset_source.py": "HIGH",
    "backend/app/services/fx.py": "HIGH",
    "backend/app/services/broker_service.py": "HIGH",
    "backend/app/services/user_service.py": "HIGH",
    "backend/app/services/transaction_service.py": "HIGH",
    # MEDIUM — API endpoints
    "backend/app/api/": "MEDIUM",
    # MEDIUM — providers
    "backend/app/services/fx_providers/": "MEDIUM",
    "backend/app/services/asset_source_providers/": "MEDIUM",
    # LOW — utilities, infrastructure
    "backend/app/utils/": "LOW",
    "backend/app/services/global_settings_service.py": "LOW",
    "backend/app/services/settings_service.py": "LOW",
    "backend/app/services/static_uploads.py": "LOW",
    "backend/app/services/provider_registry.py": "LOW",
    # INFRA — not unit-testable
    "backend/app/main.py": "INFRA",
    "backend/app/logging_config.py": "INFRA",
    "backend/app/uploads.py": "INFRA",
    "backend/app/db/models.py": "INFRA",
}


def classify_priority(filepath: str) -> str:
    """Classify a file path into a priority bucket."""
    for prefix, priority in PRIORITY_MAP.items():
        if filepath.startswith(prefix):
            return priority
    return "LOW"


# ---------------------------------------------------------------------------
# AST analysis
# ---------------------------------------------------------------------------

def find_uncovered_functions(cov_data: dict) -> tuple[list[dict], dict]:
    """
    Analyse coverage JSON data and return:
      - list of functions with covered def but uncovered body
      - dict of skip counts by reason
    """
    skip_counts = {"abstract": 0, "property": 0, "validator": 0}
    uncovered = []

    for filepath, file_data in cov_data["files"].items():
        executed = set(file_data["executed_lines"])
        missing = set(file_data["missing_lines"])

        if not missing:
            continue

        full_path = PROJECT_ROOT / filepath
        if not full_path.exists():
            continue

        try:
            source = full_path.read_text()
            source_lines = source.splitlines()
            tree = ast.parse(source)
        except Exception:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            def_line = node.lineno
            body = node.body
            if not body:
                continue

            # Skip past docstring
            first_stmt = body[0]
            if (isinstance(first_stmt, ast.Expr)
                    and isinstance(first_stmt.value, ast.Constant)
                    and isinstance(first_stmt.value.value, str)):
                if len(body) > 1:
                    first_stmt = body[1]
                else:
                    continue

            first_body_line = first_stmt.lineno

            # Core condition: def covered, first body line NOT
            if not (def_line in executed and first_body_line in missing):
                continue

            # --- Determine class context ---
            class_name = None
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    for child in ast.walk(parent):
                        if child is node:
                            class_name = parent.name
                            break

            qualified = f"{class_name}.{node.name}" if class_name else node.name

            # --- Filter: abstract (body = pass) ---
            real_body = [s for s in body if not (
                    isinstance(s, ast.Expr)
                    and isinstance(s.value, ast.Constant)
            )]
            if len(real_body) == 1 and isinstance(real_body[0], ast.Pass):
                skip_counts["abstract"] += 1
                continue

            # --- Filter: simple @property (single return) ---
            has_property = any(
                (isinstance(d, ast.Name) and d.id == "property")
                or (isinstance(d, ast.Attribute) and d.attr == "property")
                for d in node.decorator_list
            )
            if has_property and len(real_body) == 1 and isinstance(real_body[0], ast.Return):
                skip_counts["property"] += 1
                continue

            # --- Filter: model validators ---
            is_validator = any(
                (isinstance(d, ast.Name) and d.id in ("field_validator", "model_validator", "validator"))
                or (isinstance(d, ast.Attribute) and d.attr in ("field_validator", "model_validator", "validator"))
                for d in node.decorator_list
            )
            if is_validator:
                skip_counts["validator"] += 1
                continue

            # --- Collect info ---
            func_end = node.end_lineno or def_line
            func_missing = len([ln for ln in range(def_line, func_end + 1) if ln in missing])
            func_total = len([ln for ln in range(def_line, func_end + 1) if ln in (executed | missing)])
            first_body_text = source_lines[first_body_line - 1].strip() if first_body_line <= len(source_lines) else "?"

            uncovered.append({
                "file": filepath,
                "func": qualified,
                "func_type": "async def" if isinstance(node, ast.AsyncFunctionDef) else "def",
                "def_line": def_line,
                "first_body_line": first_body_line,
                "first_body_text": first_body_text,
                "missing_lines": func_missing,
                "total_lines": func_total,
                "priority": classify_priority(filepath),
            })

    uncovered.sort(key=lambda r: (
        {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFRA": 3}[r["priority"]],
        r["file"],
        r["def_line"],
    ))

    return uncovered, skip_counts


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def print_text_report(uncovered: list[dict], skip_counts: dict, priority_filter: str = None):
    """Print a human-readable report grouped by priority."""
    print(f"{'=' * 80}")
    print(f"SKIPPED: Abstract methods (body = pass): {skip_counts['abstract']}")
    print(f"SKIPPED: Simple properties (return only): {skip_counts['property']}")
    print(f"SKIPPED: Model validators: {skip_counts['validator']}")
    print(f"{'=' * 80}")

    if priority_filter:
        uncovered = [r for r in uncovered if r["priority"].upper() == priority_filter.upper()]

    current_priority = None
    current_file = None

    for r in uncovered:
        if r["priority"] != current_priority:
            current_priority = r["priority"]
            emoji = {"HIGH": "🔥", "MEDIUM": "⚠️ ", "LOW": "📐", "INFRA": "ℹ️ "}
            print(f"\n{'─' * 80}")
            print(f" {emoji.get(current_priority, '•')} Priority: {current_priority}")
            print(f"{'─' * 80}")
            current_file = None

        if r["file"] != current_file:
            current_file = r["file"]
            print(f"\n  📁 {current_file}")

        print(f"    L{r['def_line']:4d}  {r['func_type']} {r['func']}()")
        print(f"           ↳ {r['missing_lines']}/{r['total_lines']} lines uncovered")

    total = len(uncovered)
    print(f"\n{'=' * 80}")
    print(f"🔴 UNCOVERED FUNCTIONS: {total}")
    if priority_filter:
        print(f"   (filtered: {priority_filter.upper()} only)")
    print(f"{'=' * 80}")


def print_json_report(uncovered: list[dict], skip_counts: dict):
    """Print machine-readable JSON report."""
    print(json.dumps({
        "skipped": skip_counts,
        "uncovered": uncovered,
        "total": len(uncovered),
    }, indent=2))


def print_summary(uncovered: list[dict], skip_counts: dict):
    """Print a short summary of counts by priority."""
    from collections import Counter
    by_priority = Counter(r["priority"] for r in uncovered)

    print(f"\n📊 Coverage Analysis Summary")
    print(f"{'─' * 40}")
    print(f"  Skipped (abstract):   {skip_counts['abstract']}")
    print(f"  Skipped (property):   {skip_counts['property']}")
    print(f"  Skipped (validator):  {skip_counts['validator']}")
    print(f"{'─' * 40}")
    for p in ("HIGH", "MEDIUM", "LOW", "INFRA"):
        count = by_priority.get(p, 0)
        emoji = {"HIGH": "🔥", "MEDIUM": "⚠️ ", "LOW": "📐", "INFRA": "ℹ️ "}.get(p, "•")
        print(f"  {emoji} {p:8s}  {count:3d} functions")
    print(f"{'─' * 40}")
    print(f"  TOTAL:         {len(uncovered)} functions")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyse backend coverage: find functions with covered def but uncovered body.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 1. Generate coverage JSON (run tests with --coverage first)
  coverage json -o /tmp/cov_report.json

  # 2. Analyse
  python scripts/coverage_analysis.py                  # Full report
  python scripts/coverage_analysis.py --priority high  # Only HIGH priority
  python scripts/coverage_analysis.py --json           # Machine-readable
  python scripts/coverage_analysis.py --summary        # Quick summary
""",
    )
    parser.add_argument(
        "--input", "-i",
        default="/tmp/cov_report.json",
        help="Path to coverage JSON file (default: /tmp/cov_report.json)",
    )
    parser.add_argument(
        "--priority", "-p",
        choices=["high", "medium", "low", "infra"],
        default=None,
        help="Filter by priority level",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print summary counts only",
    )
    return parser


def run_analysis(args=None):
    """Run coverage analysis. Can be called programmatically or from CLI."""
    parser = create_parser()
    if args is None:
        args = parser.parse_args()
    elif isinstance(args, list):
        args = parser.parse_args(args)

    # Load coverage data
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Coverage data not found: {input_path}", file=sys.stderr)
        print(f"   Generate it first: coverage json -o {input_path}", file=sys.stderr)
        return 1

    with open(input_path) as f:
        cov_data = json.load(f)

    # Analyse
    uncovered, skip_counts = find_uncovered_functions(cov_data)

    # Output
    if args.json:
        print_json_report(uncovered, skip_counts)
    elif args.summary:
        print_summary(uncovered, skip_counts)
    else:
        print_text_report(uncovered, skip_counts, priority_filter=args.priority)

    return 0


def register_subparser(subparsers):
    """Register as sub-command of test_runner (./dev.py test coverage-report)."""
    p = subparsers.add_parser(
        "coverage-report",
        help="Analyse coverage: find functions with covered def but uncovered body",
    )
    p.add_argument(
        "--input", "-i",
        default="/tmp/cov_report.json",
        help="Path to coverage JSON (default: /tmp/cov_report.json)",
    )
    p.add_argument(
        "--priority", "-p",
        choices=["high", "medium", "low", "infra"],
        default=None,
        help="Filter by priority",
    )
    p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON",
    )
    p.add_argument(
        "--summary",
        action="store_true",
        help="Summary counts only",
    )
    return p


if __name__ == "__main__":
    sys.exit(run_analysis())

