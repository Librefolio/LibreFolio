---
title: "The stress editor listed 9 of the 17 asset types by hand: a missing bucket got a silent 0 % shock"
category: problem
status: resolved
date: 2026-09-24
tags: [risk, stress, asset-types, frontend, silent-error, release-1.2]
related:
  - features/F-113
  - features/F-110
  - sources/phase00-risk-integration-2026-09
---

# Problem: a shock that never reached half the asset types

## Symptom

In the risk panel's stress editor, a «uniform» stress by asset class left COMMODITY, REAL_ESTATE, the ETF subtypes
and five more types untouched: the editor listed 9 of the 17 `AssetType` values by hand. Found in the post-merge review
R5 of folder 02.

## Root Cause

The backend accepts any `AssetType` as a bucket and shocks a missing one by 0, with no error (`stress.py`): the number
is simply wrong. The hand-written list sat one layer above the backend's gate, where no check could see the omission.

## Solution

`5f50a2a21` («fix(risk): derive the stress buckets from the AssetType enum»): every bucket an `asset_class` shock can
name now comes from the backend enum itself, pinned by `stressBuckets.test.ts`.

**2026-11-17 (RN-17 c)**: the list, its uniform shock and their test left with the legacy Asset Detail panel, their
only reader. The levels' shock on one asset offers no type shock (Q16-4); the presets come from the backend's scenario
catalogue, which `test_risk_scenario_catalog.py` checks against the enum in both directions.

## Prevention

A list that mirrors a backend enum is derived from it, never typed again — the enum is the contract.

## Source files

| Role | Path |
|------|------|
| Accepts any `AssetType` bucket, shocks a missing one by 0 | `backend/app/services/risk_plugins/stress/plugin.py` |
| The scenario catalogue checked against the enum | `backend/test_scripts/test_services/test_risk_scenario_catalog.py` |
| Journal (R5) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/R5-post-merge-e-review.md` |
