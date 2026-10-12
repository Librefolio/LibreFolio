---
title: "A merge conflict in the test runner's catalogue cannot be solved by a line-by-line union: it would silently drop a new action"
category: problem
status: resolved
date: 2026-09-21
tags: [testing, test-runner, git, merge, conflict, workstreams, coordination]
related:
  - problems/fast-forward-blocked-by-a-dirty-file
  - concepts/test-isolation-classes
  - sources/phase00-risk-integration-2026-09
---

# Problem: the union that loses an action

## Symptom

Refreshing the Risk branch from `dev_release2` (merge `f829cd76b`, 2026-09-21), `scripts/test_runner/_frontend_utility.py`
conflicted for the fourth time. The first three times the recipe had been a line-by-line union of both sides; this time
that union would have made the incoming `onboarding-component-unit` action disappear without any error (register entry
R2-116).

## Root Cause

The runner's catalogue is structured — an action is a function plus its registration — so two sides that each add an
action can produce hunks whose plain union is syntactically fine and semantically wrong.

## Solution

Take the incoming structure and graft the branch's own additions onto it; then prove it by listing the actions
(`./dev.py test front-utility --help` shows all three), not by the absence of conflict markers.

## Prevention

After resolving a conflict in a registry-like file, check its behaviour — the list the command prints — rather than the
text. The coordinator's register keeps the recipe.

## Source files

| Role | Path |
|------|------|
| The runner's utility catalogue | `scripts/test_runner/_frontend_utility.py` |
| Journal (register, R2-116) | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/REGISTRO.md` |
