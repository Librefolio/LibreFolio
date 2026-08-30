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

3. **The unit is the line, not the statement.** The combined report merges two
   compilations of the same `.svelte` file (vitest for jsdom, the production
   build for E2E), and their statement positions do not coincide, so the merged
   denominator counts one file twice. Lines survive that far better. See
   `_statements_in_range` for the measurement and why it matters.
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
    """Count (total, covered) *lines* whose statements fall inside the range.

    Counted by line, not by statement, and that is a correction rather than a
    simplification. The combined report merges two measurements of the same
    ``.svelte`` file compiled twice — once by vitest for jsdom, once by the
    production build the E2E suite drives — and the Svelte compiler emits
    different code each time. Statement *positions* therefore do not line up:
    ``DataTableColumnFilter`` had 532 statements under vitest, 484 under E2E and
    791 in the merge, of which only 225 positions were shared. The merged
    denominator was the union of two maps of one file.

    That inflated 2 163 statements across 89 files, and it did so precisely on the
    files that have a component test — so adding one made a file's combined number
    look *worse*, and this analyser, which reads the combined report, sent us to
    write tests for code that was already covered by the other level.

    Lines survive the double compilation far better (356 of ~450 shared on that
    same file), so they are the stable unit here. A line counts as covered when any
    statement on it ran, which is what line coverage has always meant.
    """
    statement_map = file_data.get("statementMap", {})
    counters = file_data.get("s", {})
    by_line: dict[int, bool] = {}
    for sid, loc in statement_map.items():
        line = loc.get("start", {}).get("line")
        if line is None or line < start_line or line > end_line:
            continue
        by_line[line] = by_line.get(line, False) or counters.get(sid, 0) > 0
    return len(by_line), sum(1 for hit in by_line.values() if hit)


def _readable_name(raw_name: str, line: int) -> str:
    """Give anonymous closures a name a developer can act on."""
    if not raw_name or raw_name.startswith("(anonymous"):
        return f"block@{line}"
    return raw_name


def _branches_in_range(file_data: dict, start_line: int, end_line: int) -> tuple[int, int]:
    """Count (total, covered) branch arms whose branch starts inside the range.

    A branch is counted once per *arm*: an `if/else` contributes two, and each is
    covered only if that side actually ran. This is the measurement that says
    whether a decision was exercised, as opposed to merely reached — a line like
    ``if (err) log(err)`` in which ``err`` is always truthy is 100% covered by
    line and 50% by branch, and only the second number is telling the truth.

    The frontend's branch coverage sits 16 points below its statement coverage,
    against 10 on the backend, so this is where the real gap is.
    """
    branch_map = file_data.get("branchMap", {})
    counters = file_data.get("b", {})
    total = 0
    covered = 0
    for bid, meta in branch_map.items():
        loc = meta.get("loc") or {}
        line = loc.get("start", {}).get("line")
        if line is None:
            line = meta.get("line")
        if line is None or line < start_line or line > end_line:
            continue
        arms = counters.get(bid, [])
        total += len(arms)
        covered += sum(1 for hit in arms if hit > 0)
    return total, covered


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

            br_total, br_covered = _branches_in_range(file_data, start_line, end_line)

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
                    "num_branches": br_total,
                    "covered_branches": br_covered,
                    "missing_branches": br_total - br_covered,
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
