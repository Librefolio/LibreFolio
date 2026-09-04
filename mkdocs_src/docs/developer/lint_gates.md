# 🚦 Lint Gates & Code Policy

LibreFolio's Python hygiene rules are **enforced by gates**, not by convention documents: everything
listed here lives in `[tool.ruff.lint]` in the repo-root `pyproject.toml` and runs on every
`./dev.py lint` invocation. The audit lesson behind this setup (audit 08, P1-2): *"level zero" cleanups
do not hold without a gate that fails the build when the level regresses.*

```bash
./dev.py lint            # ruff check --fix (auto-fixes what is safe)
./dev.py format          # black, line-length 300
./dev.py lint --dead-code  # vulture dead-code scan (config in pyproject.toml)
```

## 🧱 The gate list

| Gate | Rule family | Why it is on |
|------|-------------|--------------|
| `E` / `W` | pycodestyle errors / warnings | Baseline style (`E501` line-length stays **off** — black owns it) |
| `F` | pyflakes | Unused imports, undefined names |
| `I` | isort | Import ordering |
| `B` | flake8-bugbear | Real-bug patterns (`B008` stays **off** — FastAPI `Depends()` needs call defaults) |
| `C4` | flake8-comprehensions | Unnecessary comprehension/list/dict calls |
| `UP` | pyupgrade | Modern syntax — with `UP006`/`UP007`/`UP035`/`UP045` **off** by choice: `List[X]`, `Union[X, Y]`, `Optional[X]` and `typing` imports are kept because they read more explicitly next to Pydantic |
| `PLC0415` | import-outside-toplevel | Imports belong at module top; the few legitimate function-local imports carry a justified `# noqa: PLC0415` |
| `S110` | try-except-pass | No silent `except: pass` swallows — audit 08/P0-3 fixed the instances, the gate keeps them from coming back |
| `C901` | cyclomatic complexity | Gated at **10** (`[tool.ruff.lint.mccabe] max-complexity = 10`) — see the policy below |
| `RUF022` | sorted `__all__` | Barrel modules keep `__all__` sorted — with 5 deliberate exceptions, see below |

`ruff check backend/` is green under these gates; a regression is a lint failure, not a discussion.

## 📏 The C901 policy: flat packers vs real complexity

McCabe counts **every** decision point — including ternaries and boolean operators — so a flat
"unpack-and-repack" data mapper with 12 ternaries scores 13 while being perfectly linear code.
Cognitive complexity would be the honest metric for that shape, but ruff does not implement it.
The threshold was therefore set low (10) and the resulting triage distinguishes two kinds of
over-threshold function:

1. **Flat data shuffling** (packers, CSV parsers, per-rule validators, bulk loops with early
   returns) → keeps a **per-function justified noqa** that says *why* it is flat:

   ```python
   def validate_chain_steps(  # noqa: C901 — flat numbered rule-chain validation
   ```

2. **Genuinely nested logic** (orchestrators, state machines, nested closures) → marked
   `TODO(P2-refactor)` in the same comment and tracked in the audit backlog for real
   decomposition:

   ```python
   async def execute_batch(  # noqa: C901 — TODO(P2-refactor): 8-stage batch pipeline, split per-operation stages
   ```

As of 2026-09-03 the tree carries **198** `# noqa: C901` sites: **173 flat-justified** and **25**
`TODO(P2-refactor)` markers (the original 26th, `compute_wac_iterative_multi_broker`, was deleted
with the legacy valuation engine). Check the current split with:

```bash
grep -rn "noqa: C901" backend/ scripts/ --include="*.py" | wc -l
grep -rn "TODO(P2-refactor)" backend/ scripts/ --include="*.py" | wc -l
```

!!! warning "Writing a new `# noqa: C901`"

    Read the whole function first. If its branches are flat format/error handling, write the noqa
    with the flat-shape justification. If you found real nesting, mark it `TODO(P2-refactor)` —
    or better, extract a helper and drop the noqa entirely.

## 🛢️ The 5 RUF022 exceptions

`__all__` is kept sorted everywhere **except** five barrel modules that group their exports by
domain with section comments — sorting would scatter related names away from their group:

- `backend/app/db/__init__.py`
- `backend/app/db/base.py`
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/assets.py`
- `backend/app/utils/financial/__init__.py`

Each carries `# noqa: RUF022 — grouped by domain with section comments; sorting would scatter related names`.

## 🪵 Logging inside `except` (TRY400 convention)

Inside an exception handler, use `logger.exception(...)` — never `logger.error(...)`: the former
attaches the active traceback, the latter silently drops it. Audit 08 converted all 55
`logger.error`-in-`except` sites (03/09) and the codebase is TRY400-clean today
(`ruff check --select TRY400` passes), although the rule is not yet part of the select list —
treat it as mandatory style regardless.

## 🧪 Beyond the linter: JSON validator vs sanitizer

Two JSON-safety helpers coexist with **opposite** error policies, and they must not be merged
(audit 08, report 03 §N-03-A):

- **`ensure_json_safe`** (`backend/app/utils/json_utils.py`) — the **validator**: recursively
  checks a value is natively JSON-serializable and raises `ValueError` otherwise. Used by Pydantic
  `field_validator`s on contract boundaries (signals, AI Export payloads), where a non-JSON value
  means the *producer* is broken and must be rejected.
- **`_json_safe_details`** (local to `backend/app/services/asset_source.py`) — the **sanitizer**:
  stringifies anything non-primitive and never raises. It exists for one field
  (`AssetSourceError.details` in provider diagnostics), preserves `None`/empty as "omit the field",
  and sanitizes one list level deep — exactly what provider-error localization needs.

Rejecting and stringifying are opposite answers to the same input. If a boundary needs validation,
call the validator; if a diagnostic field needs to survive arbitrary provider data, call the
sanitizer. Never let one grow the other's behavior.
