---
title: "normalize_currency accepted unknown garbage codes (babel echo bug)"
category: problem
status: resolved
date: 2026-04-25
tags: [backend, currency, fx, babel, pycountry, hidden-bug]
related:
  - sources/phase07-part3-closure2
  - decisions/price-currency-hard-reject
  - features/F-019
  - features/F-020
---

# Problem: `normalize_currency` echoed unknown input back as a valid ISO code

## Symptom

`backend/app/utils/currency_utils.py::normalize_currency("ZZZZZZ")` returned
`"ZZZZZZ"` as if it were a valid currency. Any random string was accepted as
a currency code by the helper, defeating its entire purpose. The downstream
hard-400 rejection in `upsert_prices_bulk` (Blocco I.2 — see
[[decisions/price-currency-hard-reject]]) could therefore be bypassed by
sending a typo like `"USDX"`: the typo was echoed through `normalize_currency`
and silently treated as a brand-new currency.

## Root Cause

The implementation used `babel.numbers.get_currency_symbol(code)` to test
whether a code was known. That function has the **undocumented behaviour of
echoing its input** when the code is unknown (instead of raising or returning
`None`). So the "is this code valid?" branch was never `False` for any
arbitrary string of letters.

```python
# old (buggy) — get_currency_symbol("ZZZZZZ") → "ZZZZZZ"
sym = get_currency_symbol(code, locale=...)
if sym != code:  # ← almost always True for ISO codes, almost always False for garbage
    return code  # ← but the early-exit path also accepted garbage
```

The bug had been latent since the helper was first written; nothing had ever
forced the function to deal with truly unknown input until G-batch7 unit tests
were added.

## Solution

Replace `babel`-based guess with a **strict `pycountry.currencies.get(alpha_3=...)`**
lookup, plus an explicit `None` return when the lookup misses. Symbol-based
resolution (e.g. `€` → `EUR`) still uses the curated `SYMBOL_TO_ISO` map +
fuzzy name search, but every path now returns either a real ISO 4217 code
from `pycountry` or `None`.

Commit: `a61b0dfa` (G-batch7, 2026-04-25).

## Prevention

- **Never trust an external helper to validate input** — always cross-check
  against an authoritative dataset (`pycountry`). Babel is for formatting,
  not validation.
- **Unit tests for utility functions** with explicit garbage cases. The
  G-batch7 audit promoted `normalize_currency` from 20% to ~95% coverage
  precisely because "20% on a deterministic utility is dramatic
  underexposure" (BlockG audit, 2026-04-25).

## Impact

- Production impact: low in practice (the UI only feeds `normalize_currency`
  with codes from a controlled dropdown), but the helper is also called from
  CSV-import paths where user-supplied strings can reach it. Any garbage
  there would have been persisted as a "currency".
- Discovered by `test_currency_utils.py::TestNormalizeCurrency::test_unknown_garbage_returns_none`.
- Sister bug to [[problems/assets-wipe-error-attr-mismatch]] — both were
  surfaced by the BlockG coverage push that took backend coverage from
  ~57% to **87.06%** in 2 days.

## Source files

| Role | Path |
|------|------|
| Bug & fix | `backend/app/utils/currency_utils.py` (`normalize_currency`) |
| Symbol map | `backend/app/utils/currency_utils.py` (`SYMBOL_TO_ISO`) |
| Test that caught it | `backend/test_scripts/test_utils/test_currency_utils.py::TestNormalizeCurrency` |

