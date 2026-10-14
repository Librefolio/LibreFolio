---
title: "The gallery's fixture normalizer chose what to scale by key name, and scaled ratios too — allocation shares, Yield on Cost, the one-day change: the allocation-history stacks stopped short of 100 % in the shots since v1.1.0 (I-M30)"
category: problem
status: resolved
date: 2026-10-14
tags: [gallery, fixtures, normalization, privacy, allocation, yield-on-cost, screenshots, workstream-i, release-1.2]
related:
  - decisions/gallery-is-a-release-gate-with-real-data
  - concepts/ci-release-pipeline
---

# Problem: a scale applied to numbers that are not amounts

## Symptom

In the gallery's dashboard shots, the 100 % stacks of the allocation history — by type, sector and geography — did
not reach the top. The app was never affected, only the screenshots, which read a committed fixture; so the
CHANGELOG has no line. M noted it after the final gallery of 2026-10-13 (backlog M-30); workstream I took it as I-M30,
plan 54.

## Root Cause

The dashboard shots read `frontend/e2e/dashboard-report.json`, a real capture normalized by
`scripts/normalize_dashboard_fixture.py` ([[concepts/ci-release-pipeline]]). The script chose what to scale by the
key's name. Amounts and per-unit prices are meant to be scaled; the same rule also caught the allocation **shares**,
Yield on Cost and `price_change_1d`, which are ratios and must keep their value. The script came with `17adbe0f4`
(2026-09-04) and the first normalized fixture with `3e33372c6`, both in v1.1.0: the 1.1 gallery was already wrong.

## Solution

- `a26051686`: the committed fixture's shares, Yield on Cost and one-day changes are recomputed, deterministically,
  from data already in the fixture; its Vitest guard follows.
- `a08e208b4`: the script never scales those keys, whatever their name. Before writing, it checks invariants — the
  shares sum to 100, Yield on Cost and the one-day change agree with their inputs — and on a failure it exits with an
  error and writes nothing; its messages carry no values. A test file and a runner entry,
  `utils normalize-dashboard-fixture`, come with it.

## The privacy question

A uniform scale leaves recoverable ratios. The developer decided on 2026-10-14 — option (a) — that the fixture is
published as it is. M's shots of the allocation and positions groups, taken again after the cure, show the stacks at
100 % (2026-10-14, 10 of 10); the journal and the backlog carry no figure of the fixture.

## Prevention

A normalizer that rescales real data decides by meaning, with an exception per path, and checks invariants before it
writes: a rule on key names turns a ratio into a wrong figure without a sound.

## Source files

| Role | Path |
|------|------|
| The normalizer | `scripts/normalize_dashboard_fixture.py` |
| Its tests | `backend/test_scripts/test_utilities/test_normalize_dashboard_fixture.py` |
| Runner entry | `scripts/test_runner/_backend_utils.py` |
| The fixture and its guard | `frontend/e2e/dashboard-report.json`, `frontend/src/lib/api/dashboardReportFixture.test.ts` |
| Plan 54 | `LibreFolio_developer_journal/Release_2/Phase_0/54_galleryFixtureShares/plan-phase00GalleryFixtureShares.prompt.md` |
