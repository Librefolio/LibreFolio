---
title: "coverage-report --category silently overwrote the parent subcommand dest (argparse collision)"
category: problem
status: resolved
date: 2026-07-14
tags: [testing, coverage, cli, argparse, python, infra]
related: []
---

# Problem: `./dev.py test coverage-report --category X` Broke Subcommand Dispatch

## Summary

`./dev.py test coverage-report --priority high` worked, but as soon as a `--category`/`-c`
filter was combined with it (e.g. to scope the report to `core_svc` or exclude
`asset_prov`/`fx_prov`), the CLI dispatcher crashed / misrouted: `args.category` no longer held
the subcommand name (`"coverage-report"`) that `dispatch_to_category()` in `scripts/
test_runner/_cli.py` expects, because it had been silently overwritten by the unrelated
`--category` filter flag defined on the `coverage-report` subparser itself.

## Root Cause (argparse `dest` collision across parser levels)

The top-level subparsers object is created with `dest="category"` so that
`args.category` holds whichever subcommand name was chosen (`"api"`, `"services"`,
`"check-orphans"`, `"coverage-report"`, ...) — this is how `_cli.py`'s
`dispatch_to_category()` routes execution. Independently, `scripts/coverage_analysis.py`'s
`register_subparser()` added the `coverage-report` subcommand's own fine-grained filter
argument as `--category`/`-c`, and left its `dest` at the argparse default, which is derived
from the flag name: also `"category"`.

```python
# scripts/test_runner/_cli.py (top level)
subparsers = parser.add_subparsers(dest="category")   # holds "coverage-report", "api", ...

# scripts/coverage_analysis.py (register_subparser, BEFORE fix)
cov_parser.add_argument("--category", "-c", help="Filter by category (e.g. core_svc)")
# no explicit dest= → argparse defaults dest to "category" → COLLIDES with the parent's dest
```

Because both live on the same final `args` namespace, parsing `coverage-report --category
core_svc` overwrote `args.category` from `"coverage-report"` to `"core_svc"` — the dispatcher
then had no way to tell it was supposed to run the `coverage-report` handler at all whenever
the filter flag was actually used (the bug was invisible/dormant when `--category` was omitted,
which is why it wasn't caught by the earlier orphan-registration or `--priority`-only testing).

## Solution

Renamed the inner argument's `dest` to something namespaced and non-colliding:
`cov_parser.add_argument("--category", "-c", dest="cov_category", ...)` in
`scripts/coverage_analysis.py`, and updated the one read site in
`_cli.py::dispatch_to_category()` from `args.category` to `args.cov_category` for this
subcommand's filter value. The flag text (`--category`/`-c`) is unchanged for the user; only
the internal attribute name changed.

## Prevention

Any subcommand-level `add_argument` that reuses the **same flag name** as an ancestor
`add_subparsers(dest=...)` (or any other already-claimed `dest`) is at risk of this exact
silent overwrite — argparse does not warn on `dest` collisions across parser levels. When
adding a new subcommand-local flag, prefer an explicit, namespaced `dest=` whenever the flag
name is generic enough to plausibly collide (`--category`, `--type`, `--mode`, `--format`,
etc.), especially in a CLI with nested subparsers like `dev.py test <category> <subcommand>`.

## Verification

Reproduced the crash before the fix (`args.category` became the filter value instead of the
subcommand name), applied the rename, then confirmed `./dev.py test coverage-report --category
core_svc --threshold 80` and `./dev.py test coverage-report --priority high --summary` both
dispatch correctly and produce the expected filtered function-level report.

## Source files

| Role | Path |
|------|------|
| Parent dest definition | `scripts/test_runner/_cli.py` (`add_subparsers(dest="category")`) |
| Colliding argument (fixed) | `scripts/coverage_analysis.py` (`register_subparser()`, `--category`/`-c` → `dest="cov_category"`) |
| Read site (fixed) | `scripts/test_runner/_cli.py` (`dispatch_to_category()`, reads `args.cov_category`) |
