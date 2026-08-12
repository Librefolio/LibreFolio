#!/usr/bin/env python3
"""
JS/Svelte coverage adapter for `coverage_analysis.py`.

`coverage_analysis.py` was written against the JSON produced by coverage.py:
a `files` mapping where every file carries a `functions` block with a ready-made
`summary`. Monocart writes the istanbul format instead — a flat mapping of files,
each with `statementMap`/`fnMap` and the raw hit counters `s`/`f`.

This module converts one into the other so a single analyser serves both
languages, and supplies the JS-specific classification rules (the Python ones
speak of providers and Pydantic schemas, which say nothing about a SvelteKit app).

Two properties of the input shape the whole design:

1. **`.svelte` files have no function names.** The Svelte compiler turns markup
   into closures, so every entry is `(anonymous_N)`. Names are therefore rebuilt
   from the source position (`block@142`), which is what a developer needs anyway
   to find the code. `.ts` files keep their real names.

2. **Statements are attributed by line range.** istanbul does not say which
   statement belongs to which function, so statements are matched against the
   function's `loc`. A nested closure is thus counted twice: once for itself and
   once for its parent. This is a ranking heuristic, not an exact metric — good
   enough to sort untested code by weight, not to be quoted as a percentage.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------


def is_istanbul(data: dict) -> bool:
    """True when the parsed JSON is an istanbul report rather than coverage.py."""
    if not isinstance(data, dict) or "files" in data:
        return False
    for value in data.values():
        if isinstance(value, dict) and "statementMap" in value and "fnMap" in value:
            return True
    return False


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def _statements_in_range(file_data: dict, start_line: int, end_line: int) -> tuple[int, int]:
    """Count (total, covered) statements whose start line falls inside the range."""
    statement_map = file_data.get("statementMap", {})
    counters = file_data.get("s", {})
    total = 0
    covered = 0
    for sid, loc in statement_map.items():
        line = loc.get("start", {}).get("line")
        if line is None or line < start_line or line > end_line:
            continue
        total += 1
        if counters.get(sid, 0) > 0:
            covered += 1
    return total, covered


def _readable_name(raw_name: str, line: int) -> str:
    """Give anonymous closures a name a developer can act on."""
    if not raw_name or raw_name.startswith("(anonymous"):
        return f"block@{line}"
    return raw_name


def istanbul_to_analysis(data: dict) -> dict:
    """Convert an istanbul report into the structure `coverage_analysis` expects."""
    files: dict[str, dict] = {}

    for filepath, file_data in data.items():
        if not isinstance(file_data, dict) or "fnMap" not in file_data:
            continue

        functions: dict[str, dict] = {}
        fn_counters = file_data.get("f", {})

        for fid, fn in file_data.get("fnMap", {}).items():
            loc = fn.get("loc") or fn.get("decl") or {}
            start_line = loc.get("start", {}).get("line", 0)
            end_line = loc.get("end", {}).get("line", start_line)
            hits = fn_counters.get(fid, 0)

            total, covered = _statements_in_range(file_data, start_line, end_line)
            if total == 0:
                # A one-expression arrow may own no statement of its own: fall
                # back to the function counter so it is still reported.
                total = 1
                covered = 1 if hits > 0 else 0

            name = _readable_name(fn.get("name", ""), start_line)
            # Distinct closures can start on the same line (chained callbacks):
            # keep the id as a tiebreaker so none is silently dropped.
            key = name if name not in functions else f"{name}#{fid}"

            functions[key] = {
                "start_line": start_line,
                "summary": {
                    "num_statements": total,
                    "covered_lines": covered,
                    "missing_lines": total - covered,
                    "percent_covered": (covered / total * 100.0) if total else 0.0,
                },
            }

        files[filepath] = {"functions": functions}

    return {"files": files}


# ---------------------------------------------------------------------------
# JS priority classification
# ---------------------------------------------------------------------------

JS_PRIORITY_MAP = {
    # HIGH — logic the user's money depends on, and the flows P3 showed to be fragile
    "src/lib/features/": "HIGH",
    "src/lib/stores/": "HIGH",
    "src/lib/services/": "HIGH",
    "src/lib/api/": "HIGH",
    "src/lib/utils/": "HIGH",
    "src/lib/risk/": "HIGH",
    # MEDIUM — presentation with real behaviour inside
    "src/lib/components/": "MEDIUM",
    "src/lib/charts/": "MEDIUM",
    "src/lib/actions/": "MEDIUM",
    "src/routes/": "MEDIUM",
    # LOW — mechanical or generated
    "src/lib/i18n/": "LOW",
    "src/lib/assets/": "LOW",
    # INFRA — not reachable from a page test
    "src/lib/workers/": "INFRA",
    "src/lib/types/": "INFRA",
    "src/lib/debug.ts": "INFRA",
    "src/service-worker": "INFRA",
}


def classify_priority_js(filepath: str) -> str:
    """Classify a frontend file path into a coarse priority bucket."""
    for prefix, priority in JS_PRIORITY_MAP.items():
        if filepath.startswith(prefix):
            return priority
    return "LOW"


# ---------------------------------------------------------------------------
# JS category classification
# ---------------------------------------------------------------------------

JS_CATEGORY_INFO = {
    "JS_FEATURE": ("🧩", "CRITICAL", "Feature logic (AI export, import wizard, …)"),
    "JS_STORE": ("🗃️", "HIGH", "Svelte stores — shared client state"),
    "JS_API": ("🔌", "HIGH", "API client wrappers"),
    "JS_UTILITY": ("🔨", "HIGH", "Pure frontend utilities (formatting, math, dates)"),
    "JS_CHART": ("📉", "MEDIUM", "Chart building and signal overlays"),
    "SVELTE_UI": ("🖼️", "MEDIUM", "Svelte component blocks (markup closures)"),
    "JS_ROUTE": ("🧭", "MEDIUM", "Route pages and layouts"),
    "JS_ACTION": ("👆", "MEDIUM", "Svelte actions (DOM behaviour)"),
    "JS_I18N": ("🌍", "LOW", "Translation plumbing"),
    "JS_INFRA": ("🔧", "SKIP", "Workers, types, debug helpers"),
    "JS_OTHER": ("❓", "LOW", "Other frontend code"),
}


def classify_category_js(filepath: str, func_name: str, stmts: int) -> str:
    """Classify a frontend function into a fine-grained category."""
    if filepath.startswith(("src/lib/workers/", "src/lib/types/")) or "debug" in filepath:
        return "JS_INFRA"
    if filepath.startswith("src/lib/features/"):
        return "JS_FEATURE"
    if filepath.startswith("src/lib/stores/"):
        return "JS_STORE"
    if filepath.startswith(("src/lib/api/", "src/lib/services/")):
        return "JS_API"
    if filepath.startswith("src/lib/charts/"):
        return "JS_CHART"
    if filepath.startswith("src/lib/actions/"):
        return "JS_ACTION"
    if filepath.startswith("src/lib/i18n/"):
        return "JS_I18N"
    if filepath.startswith("src/lib/utils/") or filepath.startswith("src/lib/risk/"):
        return "JS_UTILITY"
    if filepath.startswith("src/routes/"):
        return "JS_ROUTE"
    if filepath.endswith(".svelte"):
        return "SVELTE_UI"
    return "JS_OTHER"
