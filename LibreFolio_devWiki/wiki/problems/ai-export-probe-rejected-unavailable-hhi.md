---
title: "The AI Export probe rejected the unavailable HHI of a broker with no positions"
category: problem
status: resolved
date: 2026-10-12
tags: [ai-export, probe, diagnostics, concentration, hhi, contracts, testing, workstream-t]
related:
  - decisions/ai-export-version-bump-once-per-release
  - problems/ai-export-reconciled-false-on-rounding-dust
  - entities/ai-export-snapshot-service
  - sources/phase00-financial-math-home-2026-10
---

# Problem: the probe rejected an unavailable HHI

## Symptom

The real-prompt probe of AI Export marked «invalid HHI points» on `broker.allocation_concentration` and
`broker.concentration_context` for the synthetic broker with no positions, although the export answered HTTP 200.
Found by T's probe run for C-53, recorded as backlog C-55. On the 24-case matrix of the synthetic data (the portfolio
and its 7 brokers, 3M / 6M / 1Y), 21 cases were measured and 3 failed — all the empty broker, one per period — so a
full matrix exited with code 1 and could hide real reds behind this one.

## Root Cause

The defect was in the probe, not in the product. `audit_snapshot_semantics` (in
`ai_export_real_prompt_probe.py`) flagged every `herfindahl_index_points` that was `None`, below 0 or above 10 000,
and had no case for an empty set. **The payload's contract is the intended one**: the HHI and the largest position
weight come from the same list of weights, and are **`null` together** when no position has a weight. An HHI of 0
would say "perfectly diversified", which is false; the risk engine makes the same choice for a fully liquid scope,
and an existing test pins `None` on the empty broker. The prompt prints `null`, which its preamble defines as
«explicitly unavailable»; the AI also receives `position_count 0` and a comparison message saying the broker has no
valued positions. The user saw no defect.

## Solution

Commit `9e495c305` ("fix(ai-export): probe accepts an unavailable HHI", train 56), approved by the developer for 1.2
(«Sì, nella 1.2: la cura della sonda più i test rossi»):

- a raw `None` HHI is accepted only when the same record carries `largest_position_weight_percent`, also `None`; it is
  then counted in a new `hhi.unavailable` counter (and `hhi_unavailable` in the quality summary), so empty cases are
  visible instead of vanishing;
- everything else stays a violation: `None` next to a valued weight (a builder regression), `None` without the sibling
  field (a new component must decide on purpose), a non-numeric value, `< 0`, `> 10 000`, the HHI printed as a
  percentage;
- red tests first, by test-author: 16 new tests in `test_ai_export_real_prompt_probe.py` (5 red before the fix, the
  guards green before and after); `utils ai-export-probe-helpers` 73 passed;
- the real matrix: **24 of 24 measured, 0 failures**, `hhi_unavailable` 6 (the empty broker, 2 components × 3
  periods), and the 24 prompts byte-identical, by SHA-256, before and after.

**No version bump and no changelog line**: neither a builder, nor a payload, nor the renderer changed
([[decisions/ai-export-version-bump-once-per-release]]). Rejected: an HHI of 0 for an empty set (false), and a status
field in the three components (a v2 on three components that would restate what `position_count 0` and the legend
already say).

## Prevention

A validator of a payload must follow the payload's declared contract — here, two fields `null` together — and count
the legitimate exceptions, rather than drop them or let them fail the run.

## Left for later (backlog section T)

- **T-U7**: the HHI is computed twice in AI Export (`broker_financial.py` and `broker_concentration_context.py`); its
  home is `financial_math`, after 1.2. In the same item, a NAV ≤ 0 makes the service use 1 as the weight denominator,
  which would push the HHI above 10 000 — the probe would flag it, rightly.
- **T-U9**: the comparison's `reason_code` reads `broker_summary_unavailable` also when the summary exists but has no
  holdings; changing it changes the contract, so a v2.

## Source files

| Role | Path |
|------|------|
| The probe (`audit_snapshot_semantics`, `build_quality_summary`) | `backend/test_scripts/diagnostics/ai_export_real_prompt_probe.py` |
| The probe's tests | `backend/test_scripts/test_utilities/test_ai_export_real_prompt_probe.py` |
| The two components that emit the HHI | `backend/app/services/ai_export/components/broker_financial.py`, `backend/app/services/ai_export/components/broker_concentration_context.py` |
| The renderer's `null` legend | `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts` |
| C-55 analysis, decision and implementation | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
| Backlog C-55 | `LibreFolio_developer_journal/Release_2/Phase_0/38_postReleaseBacklog/README.md` |
