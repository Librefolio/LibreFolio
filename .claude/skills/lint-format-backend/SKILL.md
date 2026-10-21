---
name: lint-format
description: "Use this skill when running lint or format on the backend Python code, fixing ruff/black errors, understanding rule decisions, or applying lint+format to new/modified files."
---

# Backend Lint & Format Reference

## Tools & Config

| Tool | Purpose | Config |
|------|---------|--------|
| **ruff** | Linting (errors, style, imports, bugbear) | `pyproject.toml` → `[tool.ruff]` |
| **black** | Formatting (parentheses, spacing, blank lines) | `pyproject.toml` → `[tool.black]` |
| **vulture** | Dead code detection (unused functions, classes, methods) | `pyproject.toml` → `[tool.vulture]` |

Both configured with **line-length = 300** (dense lines, minimal wrapping) and **target = py313**.

## Commands

```bash
# Lint check (dry-run)
./dev.py lint

# Lint with statistics
./dev.py lint --statistics

# Lint auto-fix (safe fixes only)
./dev.py lint --fix

# Lint auto-fix (including unsafe fixes like C408 dict()→{})
./dev.py lint --fix --unsafe

# Format apply
./dev.py format

# Full pipeline: lint fix → format
./dev.py lint --fix && ./dev.py format

# === Direct commands (for single file or advanced use) ===

# Lint single file
python -m ruff check backend/app/services/some_file.py

# Format single file
python -m black backend/app/services/some_file.py
```

### Output to file (for large codebases)

Terminal output can be truncated. Always redirect to a file for full analysis:

```bash
python -m ruff check backend/ > /tmp/ruff_out.txt 2>&1; cat /tmp/ruff_out.txt
python -m ruff check backend/ --statistics > /tmp/ruff_stats.txt 2>&1; cat /tmp/ruff_stats.txt
```

## Enabled Rules

### Selected (`select`)

| Code | Plugin | What it catches |
|------|--------|-----------------|
| `E` | pycodestyle | Style errors (whitespace, indentation) |
| `W` | pycodestyle | Style warnings |
| `F` | pyflakes | Unused imports, undefined names, dead code |
| `I` | isort | Import sorting (stdlib → third-party → local) |
| `B` | flake8-bugbear | Common bug patterns, design issues |
| `C4` | flake8-comprehensions | Unnecessary list/dict/set calls |
| `UP` | pyupgrade | Python version upgrades |
| `PLC0415` | pylint | Imports inside functions (should be top-level) |

### Ignored (`ignore`) — with rationale

| Code | Rule | Why ignored |
|------|------|-------------|
| `E501` | Line too long | Handled by black (line-length=300) |
| `E402` | Import not at top | Intentional: `sys.path` manipulation, `warnings.filterwarnings` before imports |
| `B008` | Function call in defaults | FastAPI `Depends()` pattern |
| `UP006` | `List[X]` → `list[X]` | **Project style**: keep `List[X]` — more explicit |
| `UP007` | `Union[X,Y]` → `X\|Y` | **Project style**: keep `Union` — more explicit |
| `UP035` | Deprecated typing imports | **Project style**: keep `from typing import List, Dict, Optional` |
| `UP045` | `Optional[X]` → `X\|None` | **Project style**: keep `Optional[X]` — clearer with Pydantic models |

## Common Violations & How to Fix

### Auto-fixable (`--fix`)

| Code | What | Example fix |
|------|------|-------------|
| `I001` | Unsorted imports | Reorders import blocks |
| `F541` | f-string without `{}` | `f"hello"` → `"hello"` |
| `UP037` | Quoted annotation | `x: "MyClass"` → `x: MyClass` |
| `UP015` | Redundant open mode | `open(f, "r")` → `open(f)` |
| `UP017` | datetime.timezone.utc | → `datetime.UTC` |
| `UP041` | asyncio.TimeoutError | → `TimeoutError` |
| `UP024` | IOError alias | → `OSError` |
| `UP034` | Extraneous parentheses | `return (x)` → `return x` |
| `UP043` | Default type args | `AsyncGenerator[str, None]` → `AsyncGenerator[str]` |

### Manual fix required

| Code | What | How to fix |
|------|------|------------|
| `B904` | `raise` without `from` in except | `raise X` → `raise X from e` (or `from None`) |
| `B023` | Lambda captures loop variable | `lambda: f(x)` → `lambda _x=x: f(_x)` |
| `B015` | Pointless comparison | Usually a bug — add `assert` or fix. In tests: `# noqa: B015` |
| `F841` | Unused variable | Remove, or prefix with `_` if intentional |
| `F401` | Unused import | Remove import (use `--unsafe-fixes` for auto-fix) |
| `B007` | Unused loop variable | Rename to `_var` |
| `E722` | Bare `except:` | → `except Exception:` |
| `E712` | `== True` comparison | → `is True` or boolean test. **⚠️ Exception**: SQLAlchemy `.where(col == True)` is correct! |
| `B905` | `zip()` without `strict=` | Add `strict=True` if lists must be same length |
| `PLC0415` | Import inside function | Move to top-level. If circular import: add `# noqa: PLC0415 — avoid circular import` |

### Intentional suppressions (`# noqa`)

| Pattern | When to use |
|---------|-------------|
| `# noqa: PLC0415 — avoid circular import` | Import inside function to break circular dependency |
| `# noqa: B015 — intentional: testing raises` | Comparison in `pytest.raises` block |
| `# noqa: B027 — intentional no-op default` | Empty method in ABC that's a default, not abstract |

## Dead Code Detection (vulture)

`ruff`'s `F` rules catch unused *imports and locals*, but never unused module-level
functions, classes or methods. That gap is covered by **vulture**.

```bash
# Backend only, high-signal findings
./dev.py lint --dead-code --scope backend

# Include low-signal findings (Enum members, Pydantic fields — mostly noise)
./dev.py lint --dead-code --scope backend --all

# Skip a subtree (repeatable)
./dev.py lint --dead-code --scope backend --exclude "*/ai_export/*"
```

### The two result buckets

| Bucket | Meaning |
|--------|---------|
| **Unreferenced** | No reference from production code (`backend/app`, `scripts/`, `dev.py`) nor from `backend/test_scripts` |
| **Referenced only by tests** | Zero references from production code, N from `backend/test_scripts` — code kept alive artificially by its own tests |

The second bucket comes from a differential scan: vulture runs twice, once over
production code alone and once with `backend/test_scripts` added. Symbols that vanish
from the report when tests enter scope are used *only* by tests.

> **Production ≠ `backend/app`.** `scripts/` and `dev.py` are deliberately in scope:
> the `./dev.py user` CLI imports `user_service` directly, so scanning `backend/app` in
> isolation would report every CLI-only service function as dead.

### ⚠️ Before deleting anything

Dead code is a **question, not a verdict**. For each finding, first establish where its
logic went:

- **Logic absorbed elsewhere** (superseded by a newer implementation) → safe to remove,
  along with its now-pointless tests.
- **Logic exists nowhere else** → do NOT delete. It is either an unwired feature or a
  regression waiting to happen. Stop and discuss with the maintainer.

### False positives already handled

Vulture is purely static and cannot see decorators, registries or `getattr()`. The
`[tool.vulture]` config in `pyproject.toml` already suppresses:

| Pattern | Why it looks dead |
|---------|-------------------|
| `@router.get` / `@*.post` / … | FastAPI handlers are invoked by the framework. Router variables have inconsistent names (`router`, `tx_router`, `brim_router`, `router_currencies`), hence the glob |
| `@field_validator`, `@model_validator` | Resolved by the Pydantic metaclass |
| `@event.listens_for` | SQLAlchemy ORM hooks |
| `@register_provider`, `@register_plugin` | LibreFolio provider auto-discovery |
| `test_cases`, `test_currencies`, `test_file_patterns` | Provider plugin self-test contract — abstract properties consumed by the test harness **by design** |
| `mapper`, `connection`, `connection_record` | Positional params required by SQLAlchemy event signatures |

If a new framework pattern produces noise, extend `ignore_decorators` / `ignore_names`
in `[tool.vulture]` rather than sprinkling `# noqa` in the code.

### Why `--all` is off by default

At `min_confidence = 60` vulture reports ~460 items, but ~380 are `variable` and
`attribute` findings dominated by **Enum members** (consumed by value, not by name) and
**Pydantic model fields** (serialized reflectively). Filtering to
`function / method / class / property` cuts that to ~60 genuinely actionable items.


1. **Run ruff on the file**: `python -m ruff check backend/path/file.py > /tmp/ruff_out.txt 2>&1`
2. **Read output**: check error codes and counts
3. **Auto-fix safe rules**: `python -m ruff check backend/path/file.py --fix`
4. **Fix manual issues**: B904, B023, F841, PLC0415, etc.
5. **Run black**: `python -m black backend/path/file.py`
6. **Re-verify ruff** (black can reformat lines that re-trigger): `python -m ruff check backend/path/file.py`
7. **Verify syntax**: `python -c "import ast; ast.parse(open('backend/path/file.py').read()); print('OK')"`

## Workflow: Full Codebase Lint+Format

```bash
# Step 1: Auto-fix safe rules
python -m ruff check backend/ --fix

# Step 2: Format
python -m black backend/

# Step 3: Check remaining manual issues
python -m ruff check backend/ --statistics > /tmp/ruff_stats.txt 2>&1
cat /tmp/ruff_stats.txt

# Step 4: Fix remaining issues file by file
```

## ⚠️ Known Pitfalls

1. **ruff I001 + PyCharm closing parens**: ruff import sorting can corrupt files if imports use PyCharm-style indented closing `)`. Always run **black after ruff** to normalize parentheses first, or apply I001 per-file with verification.

2. **ruff --fix on large files**: Always redirect output and verify syntax after auto-fix. The I001 rule in particular can scramble multi-line import blocks.

3. **E712 false positives**: `col == True` in SQLAlchemy `where()` clauses is correct SQL — do NOT change to `col is True`. Add `# noqa: E712` if flagged.

4. **B023 in async loops**: Lambda inside `async for` with `await` right after is usually safe (lambda executes before next iteration), but still best to bind variables for clarity.

5. **black line-length 300**: With this setting, black almost never wraps lines. Its main effect is **normalizing closing parenthesis indentation** (PyCharm `    )` → PEP8 `)`) and **enforcing blank lines** between functions/classes.

6. **Black vs PyCharm closing parens**: Black uses dedented `)` everywhere (PEP 8 style). PyCharm uses continuation indent (`)` aligned with args). **Decision: use Black style** — it's the industry standard and better for team collaboration. Do NOT reformat with PyCharm after Black.

