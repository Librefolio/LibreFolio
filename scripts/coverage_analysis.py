#!/usr/bin/env python3
"""
Coverage Analysis Tool for LibreFolio.

Uses the native `functions` key from coverage JSON (same data as the HTML
web report) to find uncovered and partially-covered functions.

Previous versions used AST parsing to infer function coverage from line data.
This version reads function-level data directly from the JSON, which is both
simpler and more accurate — it shows the same information as the web report.

Usage:
    # Generate coverage JSON first:
    coverage json -o /tmp/cov_report.json

    # Then run analysis:
    python scripts/coverage_analysis.py                  # Full report
    python scripts/coverage_analysis.py --priority high  # Only HIGH priority
    python scripts/coverage_analysis.py --category critical  # Fine-grained
    python scripts/coverage_analysis.py --json           # Machine-readable
    python scripts/coverage_analysis.py --summary        # Summary counts only
    python scripts/coverage_analysis.py --threshold 50   # Functions below 50%

    # Or via dev.py:
    ./dev.py test coverage-report          # backend (Python)
    ./dev.py test coverage-report --lang js  # frontend (JS/Svelte)

The frontend report is the same analysis over the istanbul JSON written by
monocart: `coverage_js.py` converts the format and supplies frontend-specific
classification rules. The two languages share every filter and output mode.

Author: LibreFolio Contributors
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    from scripts import coverage_js
except ImportError:  # direct execution: python scripts/coverage_analysis.py
    import coverage_js

PROJECT_ROOT = Path(__file__).parent.parent.resolve()


# ---------------------------------------------------------------------------
# Priority classification rules (coarse: HIGH / MEDIUM / LOW / INFRA)
# ---------------------------------------------------------------------------

PRIORITY_MAP = {
    # HIGH — core business logic
    "backend/app/services/asset_source.py": "HIGH",
    "backend/app/services/fx.py": "HIGH",
    "backend/app/services/broker_service.py": "HIGH",
    "backend/app/services/user_service.py": "HIGH",
    "backend/app/services/transaction_service.py": "HIGH",
    "backend/app/services/brim_provider.py": "HIGH",
    # MEDIUM — API endpoints
    "backend/app/api/": "MEDIUM",
    # MEDIUM — providers
    "backend/app/services/fx_providers/": "MEDIUM",
    "backend/app/services/asset_source_providers/": "MEDIUM",
    "backend/app/services/brim_providers/": "MEDIUM",
    # LOW — utilities, infrastructure
    "backend/app/utils/": "LOW",
    "backend/app/services/global_settings_service.py": "LOW",
    "backend/app/services/settings_service.py": "LOW",
    "backend/app/services/static_uploads.py": "LOW",
    "backend/app/services/provider_registry.py": "LOW",
    "backend/app/schemas/": "LOW",
    # INFRA — not unit-testable
    "backend/app/main.py": "INFRA",
    "backend/app/logging_config.py": "INFRA",
    "backend/app/uploads.py": "INFRA",
    "backend/app/db/models.py": "INFRA",
}

# ---------------------------------------------------------------------------
# Fine-grained category rules (for --category filter)
# ---------------------------------------------------------------------------

# Provider metadata method names (1-liner, return constant)
_PROVIDER_META_NAMES = frozenset({
    "provider_code", "provider_name", "description", "supported_extensions",
    "detection_priority", "icon_url", "icon", "test_file_pattern",
    "test_search_query", "test_cases", "accepted_identifier_types",
    "supports_history", "supports_search", "provider_help_url",
    "get_icon", "get_asset_url", "base_currency", "docs_url",
    "description_i18n", "test_currencies", "warning_i18n",
    "base_currencies", "multi_unit_currencies", "params_schema",
    "validate_params", "to_plugin_info", "generate_static_url",
})

# Abstract base class prefixes
_ABSTRACT_PREFIXES = ("AssetSourceProvider.", "BRIMProvider.", "FXRateProvider.")


def classify_priority(filepath: str) -> str:
    """Classify a file path into a coarse priority bucket."""
    for prefix, priority in PRIORITY_MAP.items():
        if filepath.startswith(prefix):
            return priority
    return "LOW"


def classify_category(filepath: str, func_name: str, stmts: int) -> str:
    """
    Classify a function into a fine-grained category.

    Categories (in evaluation order):
      ABSTRACT       - interface methods on base classes (body=pass)
      PROVIDER_META  - 1-2 stmt metadata methods on providers
      SCHEMA_PROP    - 1 stmt computed properties on Pydantic schemas
      MODEL_VALID    - validators on DB models
      INFRA          - startup, logging, debug, lifecycle
      NOT_IMPL       - future features (backup)
      SCHEMA_VALID   - Pydantic schema validators
      BRIM_PROV      - broker import plugin code
      ASSET_PROV     - asset source provider code
      FX_PROV        - FX rate provider code
      CORE_SVC       - core business logic services
      API_ENDPOINT   - HTTP endpoint handlers
      UTILITY        - pure utility functions
      OTHER          - everything else
    """
    short = func_name.split(".")[-1] if "." in func_name else func_name

    # Abstract base methods
    if stmts == 1 and any(func_name.startswith(p) for p in _ABSTRACT_PREFIXES):
        return "ABSTRACT"

    # Provider metadata (1-2 stmt, return constant)
    if stmts <= 2 and short in _PROVIDER_META_NAMES:
        return "PROVIDER_META"

    # Schema computed properties
    if stmts <= 1 and "schemas/" in filepath:
        return "SCHEMA_PROP"

    # DB model validators
    if "models.py" in filepath and "validate" in func_name:
        return "MODEL_VALID"

    # Infrastructure
    if any(kw in filepath for kw in ["main.py", "logging_config.py"]):
        return "INFRA"
    if "_debug_" in func_name:
        return "INFRA"
    if short in ("shutdown_live_feeds", "get_session_ttl_sync",
                 "shutdown_all_providers", "_get_provider_folder"):
        return "INFRA"

    # Not implemented features
    if short in ("export_data", "restore_data", "backup_status"):
        return "NOT_IMPL"

    # Schema validators
    if "schemas/" in filepath:
        return "SCHEMA_VALID"

    # Broker import providers
    if "brim_providers/" in filepath:
        return "BRIM_PROV"

    # Asset source providers
    if "asset_source_providers/" in filepath:
        return "ASSET_PROV"

    # FX providers
    if "fx_providers/" in filepath:
        return "FX_PROV"

    # Core services
    if any(svc in filepath for svc in [
        "asset_source.py", "services/fx.py", "broker_service.py",
        "transaction_service.py", "user_service.py",
        "brim_provider.py", "settings_service.py",
    ]):
        return "CORE_SVC"

    # API endpoints
    if "api/v1/" in filepath:
        return "API_ENDPOINT"

    # Utilities
    if "utils/" in filepath:
        return "UTILITY"

    return "OTHER"


CATEGORY_INFO = {
    "ABSTRACT":      ("⬜", "SKIP",     "Abstract interfaces (body=pass)"),
    "PROVIDER_META": ("🏷️", "LOW",      "Provider metadata (1-liner constants)"),
    "SCHEMA_PROP":   ("📋", "LOW",      "Computed schema properties"),
    "MODEL_VALID":   ("🔐", "MEDIUM",   "DB model validators"),
    "INFRA":         ("🔧", "SKIP",     "Startup, logging, debug"),
    "NOT_IMPL":      ("⏳", "SKIP",     "Future features (not implemented)"),
    "SCHEMA_VALID":  ("📝", "MEDIUM",   "Pydantic schema validators"),
    "BRIM_PROV":     ("📊", "HIGH",     "Broker import plugins (CSV parsing)"),
    "ASSET_PROV":    ("📈", "HIGH",     "Asset source providers (JustETF/Yahoo/CSS)"),
    "FX_PROV":       ("💱", "HIGH",     "FX rate providers (ECB/BOE/FED/SNB)"),
    "CORE_SVC":      ("🔥", "CRITICAL", "Core business logic (CRUD/sync/bulk)"),
    "API_ENDPOINT":  ("🌐", "HIGH",     "HTTP endpoint handlers"),
    "UTILITY":       ("🔨", "MEDIUM",   "Pure utility functions"),
    "OTHER":         ("❓", "LOW",      "Other"),
    # Frontend categories live in the same table so filters, sorting and the
    # legend work identically whichever language is being analysed.
    **coverage_js.JS_CATEGORY_INFO,
}

CATEGORY_ORDER = list(CATEGORY_INFO.keys())


# ---------------------------------------------------------------------------
# Analysis using native JSON `functions` data
# ---------------------------------------------------------------------------

def find_uncovered_functions(cov_data: dict, threshold: float = 0.0,
                             priority_fn=None, category_fn=None) -> list[dict]:
    """
    Read function-level coverage from JSON and return functions below threshold.

    Uses the `functions` key in the coverage JSON — same data shown in the
    HTML web report. No AST parsing needed.

    Args:
        cov_data: Parsed coverage JSON
        threshold: Include functions with coverage <= this % (default 0 = only 0%)
        priority_fn: Path → priority bucket (defaults to the Python rules)
        category_fn: (path, name, stmts) → category (defaults to the Python rules)

    Returns:
        List of dicts with function info, sorted by category/priority.
    """
    priority_fn = priority_fn or classify_priority
    category_fn = category_fn or classify_category
    results = []

    for filepath, file_data in cov_data["files"].items():
        functions = file_data.get("functions", {})
        if not functions:
            continue

        for func_name, func_info in functions.items():
            summary = func_info.get("summary", {})
            pct = summary.get("percent_covered", 100.0)
            num_stmts = summary.get("num_statements", 0)
            covered = summary.get("covered_lines", 0)
            missing = summary.get("missing_lines", 0)

            if num_stmts == 0:
                continue
            if pct > threshold:
                continue

            category = category_fn(filepath, func_name, num_stmts)
            priority = priority_fn(filepath)

            results.append({
                "file": filepath,
                "func": func_name,
                "stmts": num_stmts,
                "covered": covered,
                "missing": missing,
                "pct": pct,
                "start_line": func_info.get("start_line", 0),
                "priority": priority,
                "category": category,
            })

    results.sort(key=lambda r: (
        CATEGORY_ORDER.index(r["category"]) if r["category"] in CATEGORY_ORDER else 99,
        r["file"],
        r["start_line"],
    ))

    return results


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def print_text_report(results: list[dict], priority_filter: str = None,
                      category_filter: str = None):
    """Print a human-readable report grouped by category."""
    if priority_filter:
        results = [r for r in results if r["priority"].upper() == priority_filter.upper()]
    if category_filter:
        results = [r for r in results
                   if r["category"].upper() == category_filter.upper()]

    # Summary table
    by_cat = Counter(r["category"] for r in results)
    stmts_by_cat = defaultdict(int)
    for r in results:
        stmts_by_cat[r["category"]] += r["stmts"]

    print(f"{'=' * 90}")
    print("COVERAGE ANALYSIS — Functions below threshold")
    print(f"{'=' * 90}")
    print(f"\n{'Category':<18} {'Funcs':>5} {'Stmts':>6}  {'Impact':<12} Description")
    print(f"{'─' * 90}")

    for cat in CATEGORY_ORDER:
        count = by_cat.get(cat, 0)
        if count == 0:
            continue
        emoji, impact, desc = CATEGORY_INFO[cat]
        stmts = stmts_by_cat[cat]
        print(f"{emoji} {cat:<16} {count:>5} {stmts:>6}  {impact:<12} {desc}")

    total = len(results)
    total_stmts = sum(r["stmts"] for r in results)
    print(f"{'─' * 90}")
    print(f"{'TOTAL':<18} {total:>5} {total_stmts:>6}")

    # Detailed list
    print(f"\n{'=' * 90}")
    print("DETAIL")
    print(f"{'=' * 90}")

    current_cat = None
    current_file = None

    for r in results:
        if r["category"] != current_cat:
            current_cat = r["category"]
            emoji, impact, desc = CATEGORY_INFO[current_cat]
            print(f"\n{'─' * 90}")
            print(f" {emoji} {current_cat} — {desc} [{impact}]")
            print(f"{'─' * 90}")
            current_file = None

        if r["file"] != current_file:
            current_file = r["file"]
            print(f"\n  📁 {current_file}")

        marker = "‼️" if r["stmts"] >= 20 else "  "
        pct_str = f"{r['pct']:.0f}%" if r["pct"] > 0 else "0%"
        print(f"   {marker} {r['func']:55s}  {r['stmts']:3d} stmts  {pct_str:>4s}")

    print(f"\n{'=' * 90}")
    print(f"TOTAL: {total} functions, {total_stmts} statements")
    if priority_filter:
        print(f"  (filtered: priority={priority_filter.upper()})")
    if category_filter:
        print(f"  (filtered: category={category_filter.upper()})")
    print(f"{'=' * 90}")


def print_json_report(results: list[dict]):
    """Print machine-readable JSON report."""
    by_cat = Counter(r["category"] for r in results)
    stmts_by_cat = defaultdict(int)
    for r in results:
        stmts_by_cat[r["category"]] += r["stmts"]

    print(json.dumps({
        "summary": {
            cat: {"functions": by_cat.get(cat, 0), "statements": stmts_by_cat.get(cat, 0)}
            for cat in CATEGORY_ORDER if by_cat.get(cat, 0) > 0
        },
        "functions": results,
        "total_functions": len(results),
        "total_statements": sum(r["stmts"] for r in results),
    }, indent=2))


def print_summary(results: list[dict]):
    """Print a short summary of counts by category."""
    by_cat = Counter(r["category"] for r in results)
    stmts_by_cat = defaultdict(int)
    for r in results:
        stmts_by_cat[r["category"]] += r["stmts"]

    print("\n📊 Coverage Analysis Summary")
    print(f"{'─' * 50}")
    for cat in CATEGORY_ORDER:
        count = by_cat.get(cat, 0)
        if count == 0:
            continue
        emoji, impact, _ = CATEGORY_INFO[cat]
        stmts = stmts_by_cat[cat]
        print(f"  {emoji} {cat:<16}  {count:>3} funcs  {stmts:>5} stmts  [{impact}]")
    print(f"{'─' * 50}")
    print(f"  TOTAL:  {len(results):>3} funcs  {sum(r['stmts'] for r in results):>5} stmts")

    # Action summary
    skip_cats = {"ABSTRACT", "PROVIDER_META", "SCHEMA_PROP", "INFRA", "NOT_IMPL", "JS_INFRA"}
    actionable = [r for r in results if r["category"] not in skip_cats]
    skip = [r for r in results if r["category"] in skip_cats]
    print(f"\n  ✅ Skip-safe:  {len(skip):>3} funcs  {sum(r['stmts'] for r in skip):>5} stmts")
    print(f"  🔴 Actionable: {len(actionable):>3} funcs  {sum(r['stmts'] for r in actionable):>5} stmts")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyse coverage using native function-level data from coverage JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 1. Generate coverage JSON (run tests with --coverage first)
  coverage json -o /tmp/cov_report.json

  # 2. Analyse
  python scripts/coverage_analysis.py                        # Full report (0%% only)
  python scripts/coverage_analysis.py --threshold 50         # Functions below 50%%
  python scripts/coverage_analysis.py --priority high        # Only HIGH priority
  python scripts/coverage_analysis.py --category core_svc    # Only core services
  python scripts/coverage_analysis.py --json                 # Machine-readable
  python scripts/coverage_analysis.py --summary              # Quick summary

  # 3. Same analysis on the frontend (istanbul JSON from monocart)
  python scripts/coverage_analysis.py --lang js --summary

Categories (Python):
  ABSTRACT, PROVIDER_META, SCHEMA_PROP, MODEL_VALID, INFRA, NOT_IMPL,
  SCHEMA_VALID, BRIM_PROV, ASSET_PROV, FX_PROV, CORE_SVC, API_ENDPOINT,
  UTILITY, OTHER

Categories (JS/Svelte):
  JS_FEATURE, JS_STORE, JS_API, JS_UTILITY, JS_CHART, SVELTE_UI, JS_ROUTE,
  JS_ACTION, JS_I18N, JS_INFRA, JS_OTHER
""",
    )
    parser.add_argument(
        "--input", "-i",
        default=None,
        help="Path to coverage JSON file (default: /tmp/cov_report.json, "
             "or the newest JS report when --lang js)",
    )
    parser.add_argument(
        "--lang", "-l",
        choices=["py", "js"],
        default=None,
        help="Which coverage to analyse (default: inferred from the file format)",
    )
    parser.add_argument(
        "--priority", "-p",
        choices=["high", "medium", "low", "infra"],
        default=None,
        help="Filter by coarse priority level",
    )
    parser.add_argument(
        "--category", "-c",
        choices=[c.lower() for c in CATEGORY_ORDER],
        default=None,
        help="Filter by fine-grained category",
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.0,
        help="Include functions with coverage <= this %% (default: 0 = only 0%%)",
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


JS_REPORT_CANDIDATES = (
    "frontend/coverage-js/combined/coverage-final.json",
    "frontend/coverage-js/e2e/coverage-final.json",
    "frontend/coverage-js/unit-combined/coverage-final.json",
)


def resolve_input(explicit: str | None, lang: str | None) -> Path | None:
    """Pick the coverage file to analyse, preferring the richest JS report available."""
    if explicit:
        return Path(explicit)
    if lang == "js":
        for candidate in JS_REPORT_CANDIDATES:
            path = PROJECT_ROOT / candidate
            if path.exists():
                return path
        return PROJECT_ROOT / JS_REPORT_CANDIDATES[0]
    return Path("/tmp/cov_report.json")


def run_analysis(args=None):
    """Run coverage analysis. Can be called programmatically or from CLI."""
    parser = create_parser()
    if args is None:
        args = parser.parse_args()
    elif isinstance(args, list):
        args = parser.parse_args(args)

    lang = getattr(args, "lang", None)

    # Load coverage data
    input_path = resolve_input(getattr(args, "input", None), lang)
    if not input_path.exists():
        print(f"❌ Coverage data not found: {input_path}", file=sys.stderr)
        if lang == "js":
            print("   Generate it first: ./dev.py test --coverage js front all", file=sys.stderr)
        else:
            print(f"   Generate it first: coverage json -o {input_path}", file=sys.stderr)
        return 1

    with open(input_path) as f:
        cov_data = json.load(f)

    # The two formats are told apart by shape, so `--lang` stays optional: it only
    # matters for choosing the default input path.
    priority_fn = category_fn = None
    if coverage_js.is_istanbul(cov_data):
        cov_data = coverage_js.istanbul_to_analysis(cov_data)
        priority_fn = coverage_js.classify_priority_js
        category_fn = coverage_js.classify_category_js
    elif lang == "js":
        print(f"❌ {input_path} is not an istanbul report.", file=sys.stderr)
        print("   Expected the JSON written by monocart (frontend/coverage-js/…).", file=sys.stderr)
        return 1

    # Check if functions data is available
    sample_file = next(iter(cov_data.get("files", {})), None)
    if sample_file and "functions" not in cov_data["files"][sample_file]:
        print("❌ Coverage JSON does not contain function-level data.", file=sys.stderr)
        print("   Regenerate with: coverage json -o /tmp/cov_report.json", file=sys.stderr)
        print("   (requires coverage.py >= 7.x)", file=sys.stderr)
        return 1

    # Analyse
    results = find_uncovered_functions(cov_data, threshold=args.threshold,
                                       priority_fn=priority_fn, category_fn=category_fn)

    # Apply category filter
    category_filter = args.category.upper() if args.category else None

    # Output
    if args.json:
        if category_filter:
            results = [r for r in results if r["category"] == category_filter]
        if args.priority:
            results = [r for r in results if r["priority"].upper() == args.priority.upper()]
        print_json_report(results)
    elif args.summary:
        if category_filter:
            results = [r for r in results if r["category"] == category_filter]
        if args.priority:
            results = [r for r in results if r["priority"].upper() == args.priority.upper()]
        print_summary(results)
    else:
        print_text_report(results, priority_filter=args.priority,
                          category_filter=category_filter)

    return 0


def register_subparser(subparsers):
    """Register as sub-command of test_runner (./dev.py test coverage-report)."""
    p = subparsers.add_parser(
        "coverage-report",
        help="Analyse coverage: find uncovered functions using native JSON data",
    )
    p.add_argument(
        "--input", "-i",
        default=None,
        help="Path to coverage JSON (default: /tmp/cov_report.json, "
             "or the newest JS report with --lang js)",
    )
    p.add_argument(
        "--lang", "-l",
        choices=["py", "js"],
        default=None,
        help="Which coverage to analyse (default: inferred from the file format)",
    )
    p.add_argument(
        "--priority", "-p",
        choices=["high", "medium", "low", "infra"],
        default=None,
        help="Filter by coarse priority",
    )
    p.add_argument(
        "--category", "-c",
        dest="cov_category",
        choices=[c.lower() for c in CATEGORY_ORDER],
        default=None,
        help="Filter by fine-grained category",
    )
    p.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.0,
        help="Include functions with coverage <= this %% (default: 0)",
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

