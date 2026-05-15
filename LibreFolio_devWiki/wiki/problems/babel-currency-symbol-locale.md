---
title: "Babel Currency Symbol Returns Code Instead of Symbol in Non-English Locale"
category: problem
tags: [backend, python, babel, currency, locale, i18n]
severity: high
resolved: true
date: 2026-04-28
related:
  - features/F-047
  - sources/phase07-part4-round1
---

# Problem: Babel Currency Symbol Returns Code in Non-English Locale

## Symptom

On a system with Italian locale (or when user has Italian as preferred language), currency symbols show as their ISO code instead of the correct symbol:

| Expected | Actual (Italian locale) |
|----------|------------------------|
| `$` | `USD` |
| `£` | `GBP` |
| `¥` | `JPY` |
| `CHF` | `CHF` (accidentally correct) |
| `€` | `€` (accidentally correct, both work) |

## Root Cause

Babel's `get_currency_symbol(currency, locale=user_locale)` uses the **CLDR data for the given locale**. In Italian (and many European locales), CLDR provides the ISO code string (e.g. `'USD'`) as the "symbol" because Italians write amounts as `USD 100,00` not `$100`. Only the `en` locale reliably returns the symbolic glyph `'$'` for all common currencies.

## Fix

In `backend/app/utils/currency_utils.py`, a hardcoded English `Babel Locale` object is used for symbol lookup only; the user's locale is still used for the currency name:

```python
def list_currencies(language: str = "en") -> list[CurrencyInfo]:
    ...
    en_locale = get_babel_locale("en")                          # ← Locale object, not string
    symbol = get_currency_symbol(code, locale=en_locale) or code  # ← always 'en' for symbol
    name = get_currency_name(code, locale=babel_locale)           # ← user locale for name
```

The key detail: `locale=en_locale` must receive a `babel.Locale` object (from `get_babel_locale("en")`), **not** the plain string `'en'`.

## Affected File

- `backend/app/utils/currency_utils.py` (W77/C22, Round 1)

## Source

W77/C22 documented in:
`LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md`, sub-round 1.13.
