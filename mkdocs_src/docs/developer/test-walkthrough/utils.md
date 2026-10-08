# 🔧 Utility Module Tests (`utils`)

These tests verify the helper functions and utility modules used throughout the application.

## 🎯 Purpose

To ensure that low-level utilities are robust and handle edge cases correctly.

## 🔑 Key Tests

- **Financial Math**: Tests interest calculations, day count conventions, and compounding formulas.
- **Datetime Utils**: Tests timezone handling and date parsing.
- **Decimal Utils**: Tests precision handling for financial amounts.

## 🧩 Gate and Runner Units

The two units below test the project's own tooling rather than application helpers. Both are
PURE: no database, no server, no network.

| Sub-command | What It Tests |
|-------------|---------------|
| `gate-i18n-usage` | The three-verdict i18n key classifier in `scripts/i18n_usage.py`, which `./dev.py i18n audit` uses to report unused keys: *used* (proven), *dead* (proven absent), or *not verified* (the key's family exists but its last segment is produced at runtime). It checks typed-union expansion, constant namespaces, both branches of a ternary or of a conditional prefix, backend literals as the vocabulary of dynamic segments, and that test sources never count as evidence. Each case asserts what must be condemned **and** what must survive (`backend/test_scripts/test_utilities/test_i18n_usage_gate.py`). |
| `runtime-isolation` | The [runtime lane](index.md#isolated-runtime-lanes) contract: test-port and data-directory resolution with its production guards, propagation of the lane to child processes and nested Pipenv runs, the lane-identity readiness probe, and ownership of the shared test server, which never reuses or signals a process it did not start (`backend/test_scripts/test_utilities/test_runtime_isolation.py`). |

List every unit of the category with `./dev.py test utils --list`.

## 🚀 Running

```bash
./dev.py test utils
```
