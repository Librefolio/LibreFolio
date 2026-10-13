---
title: "One asset quoted from mid-crisis moved the replay's joint baseline: every other asset replayed only half the crisis, unsaid"
category: problem
status: resolved
date: 2026-09-24
tags: [risk, replay, stress, eligibility, calendar, coverage, backend, release-1.2]
related:
  - features/F-110
  - decisions/lab-eligibility-from-risk-engine
  - sources/phase00-risk-integration-2026-09
---

# Problem: a late starter shortened everyone's crisis

## Symptom

The historical-crisis replay builds one joint series for the selection. When one asset began quoting in the middle of
the crisis, the common baseline moved to its first date, and the replay of every other asset covered only the second
half of the crisis; the only hint was the generic `short_history` warning (review R5 of folder 02).

## Root Cause

A buy-and-hold replay compares the value at the start with the value at the end; the joint calendar silently took the
latest start among the assets as everyone's start.

## Solution

`a766a9d5d` («feat(risk): eligibility and replay auto-exclusion»), `services/risk/eligibility.py`: one set of facts per
asset and window, read two ways — analysis eligibility for a period the user chooses (an asset that starts late may be
selected, with a warning: the developer's decision of 24/09) and replay coverage for a crisis window, where an asset not
priced at both ends is **excluded automatically** instead of blocking the replay or moving the baseline. On the
portfolio its weight is treated as cash; in the Lab it is left out.

## Prevention

A joint window must never be narrowed by one member without saying so: exclude the member, name it, keep the window.

## Source files

| Role | Path |
|------|------|
| Eligibility and replay coverage | `backend/app/services/risk/eligibility.py` |
| Journal (R5) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/R5-post-merge-e-review.md` |
