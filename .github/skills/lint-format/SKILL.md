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

Both configured with **line-length = 300** (dense lines, minimal wrapping) and **target = py313**.

## Commands

```bash
# Lint check (dry-run)
./dev.py lint
python -m ruff check backend/

# Lint single file
python -m ruff check backend/app/services/some_file.py

# Lint auto-fix (safe fixes only)
python -m ruff check backend/ --fix

# Lint with statistics
python -m ruff check backend/ --statistics

# Format check (dry-run)
python -m black backend/ --diff

# Format apply
./dev.py format
python -m black backend/

# Full pipeline: lint fix → format
python -m ruff check backend/ --fix && python -m black backend/
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

## Workflow: Applying Lint+Format to a File

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

