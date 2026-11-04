---
title: "E2E waits chained past the test budget: «Test timeout» instead of the step's name"
category: problem
status: resolved
date: 2026-10-17
tags: [e2e, playwright, load, timeouts, risk, triage]
related: [problems/jscoverage-teardown-spends-the-test-budget, problems/login-returns-before-the-app-has-started, concepts/page-busy-refresh-button]
---

# Problem: E2E waits chained past the test budget

## Symptom

Under a busy machine (load 57 → 115, several lanes plus the colour gallery), `front-portfolio risk` went red in tests
that had passed for days:
- D378 (`:3993`) and the shared-benchmark picker (`:4456`) both said only «Test timeout of 30000ms exceeded»;
- the snapshot showed the click had worked (the period had moved and the report was loading): only the budget had run
  out.

A first fix (Y-21) gave L4 (D377) real deadlines on its `expect.poll` (`L4_OFFER_DEADLINE_MS`, 10 s: the default 3 s
poll had failed «waiting on the predicate», because the page's main thread was busy). The rerun turned up two more,
of a different kind:
- an L3 tooltip that did not open within `hoverUntilHelpOpens`' 10 s;
- a benchmark option whose click waited «visible, enabled and stable» until the end of the budget.

## Root Cause

- **The budget.** These tests chain their own waits: a 20 s settle barrier, a picker of 10 + 10 s, polls of 10 + 15 s.
  Together they add up to more than the config's 30 s test timeout.
  - On a slow machine the test timeout fires first, so the red loses the name of the step that was slow.
  - The run itself was 2–3× slower than earlier runs in its middle block, while its first tests ran at their usual
    speed: contention, not a growing DB (1.3 MB).
- **The tooltip.** Each retry of `hoverUntilHelpOpens` moves the pointer to the corner first, and that disarms the
  delay the previous attempt left pending (`handlePointerLeave` in the Tooltip).
  - So a delay run late must fit in **one** rest of `HELP_REST_MS`.
  - A longer deadline alone buys more attempts, not a longer one.
- **The click.** Not reproduced: alone, ×4, `--trace on`, at load 55, the option was actionable at once
  (0.04–0.29 s from «waiting» to «click done»).
  - Verdict: environment, a starved renderer at load 94–115.

## Solution

- `test.describe.configure({timeout: 90_000})` at the top of «Risk analysis functional integration». It is **a
  budget, not a wait**: room for each step's own deadline to run out first, so a red names its step. D377's own
  `setTimeout` was removed as redundant.
- `HELP_OPEN_DEADLINE_MS` 10 → 20 s and `HELP_REST_MS` 2 → 3 s, with the reason in the comments.
- The click: left as it is. If it comes back, a trace of the red case is needed. The config traces only
  `on-first-retry`, and local runs do not retry.

## Prevention

- When a test chains waits, check their sum against the test budget, and give the block a budget that covers them.
- Give an `expect.poll` an explicit deadline: the default 3 s fails silently on a busy main thread.
- Triage a timeout with `test-triage` before raising anything. Compare per-test durations across runs: a block-wide
  slowdown is the machine, one slow test is the test.
- Trade-off accepted: with no `actionTimeout`, a click on a control that never becomes clickable now fails at 90 s
  instead of 30.

## Impact

Three E2E reruns, about 45 slot-minutes, and two backlog items, Y-21 and Y-22, both closed on 17/10.

## Source files

| Role | Path |
|------|------|
| The block budget, `L4_OFFER_DEADLINE_MS`, `hoverUntilHelpOpens` | `frontend/e2e/portfolio/risk-analysis.spec.ts` |
| The Tooltip's pending delay and `handlePointerLeave` | `frontend/src/lib/components/ui/feedback/Tooltip.svelte` |
| The test timeout and the trace setting | `frontend/playwright.config.ts` |
| History (Y-21, Y-22) | `LibreFolio_developer_journal/Release_2/Phase_0/BACKLOG_POST_1.2.md` |
