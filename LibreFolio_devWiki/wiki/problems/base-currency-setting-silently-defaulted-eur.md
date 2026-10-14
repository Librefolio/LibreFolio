---
title: "The portfolio ignored the user's base currency: a settings lookup with swapped arguments and a non-existent key fell back to EUR without a sound"
category: problem
status: resolved
date: 2026-09-02
tags: [backend, settings, currency, portfolio, fallback, silent-error, audit]
related:
  - features/F-092
  - sources/phase00-clean-audit-2026-08
---

# Problem: every portfolio in euros

## Symptom

The second clean audit (2026-09-02, folder `08_newCleanAndDocumentation_audit`) rated it P0: the portfolio, the lots
analysis and the portfolio service computed in EUR whatever base currency the user had chosen — and nothing failed,
because EUR was the fallback.

## Root Cause

The portfolio engine called `get_global_setting(self.db, "base_currency", "EUR")`: the arguments were inverted and one
too many (the signature is `(key, session)`), and the key `base_currency` does not exist — the global default is
`default_currency`. The same wrong key was read in the lots analysis and in the portfolio service. Each lookup missed,
and the default answered for all of them.

## Solution

`08b99c3ac` (2026-09-03, «fix: beta wave 2 collaudo + clean-audit P0/P1 backlog»), in the variant the developer chose:
one helper, `get_effective_base_currency()` in `settings_service.py`, which resolves per-user → global → EUR, used by
the portfolio engine (`financial_math/portfolio/engine.py` today), the lots analysis and the portfolio service, with tests on the chain and on the `target_currency=None` branch.

## Prevention

A setting is read through one helper that knows its chain; a lookup by a free string key with a default hides both a
wrong key and a wrong signature.

## Source files

| Role | Path |
|------|------|
| `get_effective_base_currency()` | `backend/app/services/accounts/settings_service.py` |
| A caller | `backend/app/services/lots_analysis_service.py` |
| Journal (P0-1) | `LibreFolio_developer_journal/Release_2/phases/08_newCleanAndDocumentation_audit/14_backlog_ed_esecuzione.md` |
