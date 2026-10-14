---
title: "Shared brokers: the portfolio caches ignored role and share, so a changed ownership % showed old figures for up to 24 hours; the first share fix zeroed every editor and viewer (F2)"
category: problem
status: resolved
date: 2026-09-01
tags: [backend, portfolio, cache, sharing, roles, ownership, dashboard, beta-feedback, release-1.1]
related:
  - entities/portfolio-engine
  - decisions/native-cash-daily-revaluation
  - decisions/broker-last-owner-guard
  - sources/beta-testing-2026-08-05
---

# Problem: the numbers depended on the role and the share, the cache keys did not

## Symptom

Beta feedback F2 (31/08/2026) asked the Dashboard to show only the brokers a user owns, scaled by the ownership
percentage, with 0 % a valid share. Two defects came out of the work:

1. the first version of the fix emptied the figures of every **editor** and **viewer** of a shared broker;
2. after the fix, a broker card stayed at zero, and editing a share had **no visible effect** for up to a day.

## Root Cause

1. **The naive share rule.** The old code scaled by `share_percentage or Decimal("1")`, so a 0 % share counted as 100 %. The
   first fix read the share whenever it was not `None` — but editors and viewers always carry share 0 by schema rule,
   so their data was multiplied by zero. Two risk API tests went red, and the existing suite caught it before it
   shipped.
2. **The cache keys.** Both portfolio caches were keyed on the scope and on fingerprints of transactions, prices and
   FX, none of which moves when a role or a share changes, although every scaled number does: the engine's blob
   cache (24-hour TTL) and the report cache above it (30 minutes).

## Solution

Two commits of 01/09/2026, both titled «fix: consolidate beta user feedback (F1–F17)» and both shipped in 1.1.0:

- **role-aware scaling** (`3e3f9c41f`): an owner's share scales the broker's contribution (0 % contributes nothing);
  an editor or a viewer always scales by 1. Today the rule has one home, `effective_share()` in
  `financial_math/native_cash.py` (see [[decisions/native-cash-daily-revaluation]]);
- an **access fingerprint** (`f32e460ca`), the sorted `(broker_id, role, share)` of every access in scope, enters **both** cache
  keys, so a changed share or role misses the cache by itself, without any explicit invalidation. The role is read as
  `getattr(role, "value", role)`, because a model built in the session may carry it as a plain string.

`TestAccessFingerprintCacheBust` edits a share and a role and expects new numbers; with the fingerprint removed from
the key it turns red.

## Prevention

- A cache key must contain **everything the cached value depends on**, including permissions and ownership: a
  fingerprint of the data rows does not move when only the reader changes.
- «0 is valid» and «0 means not applicable» cannot share one field without the role that tells them apart.

## Source files

| Role | Path |
|------|------|
| Engine blob cache key | `backend/app/services/financial_math/portfolio/engine.py` |
| Report cache key | `backend/app/services/portfolio_service.py` |
| Share rule | `backend/app/services/financial_math/native_cash.py` (`effective_share`) |
| Regression test | `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` (`TestAccessFingerprintCacheBust`) |
| Feedback classification | `LibreFolio_developer_journal/Release_2/phases/06_betaTestingReportAndFixing/03_feedback_utenti_F1-F17_classificazione_e_fix.md` |
