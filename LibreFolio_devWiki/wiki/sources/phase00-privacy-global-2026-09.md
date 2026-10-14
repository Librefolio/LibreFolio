---
title: "Phase 0 / 24 — global privacy, «hide values» (U2, SP15), rounds 1 and 2"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/24_privacyGlobal/
tags: [phase0, release2, privacy, frontend, formatters, gates, workstream-j]
related:
  - decisions/privacy-mask-at-the-formatter
  - features/F-101
  - concepts/premise-gate-keyed-by-content
  - decisions/asset-global-page-shows-no-money
---

# Source: Phase 0 / 24 — global privacy

## Summary

An analysis (~1 100 lines) and two plans, archived on 2026-10-09. Round 1 (masking core, 2026-09-22,
`b66e93003` + the gate `9a6dd2015`) put a "hide values" switch in the header and the masking in the currency
formatters. The usage review of 2026-09-22 found it hid too much — the currency symbol, the risk sign, lots, the
broker view, every quantity — because values were classified by formatter; Round 2 (2026-09-24, `176f19707`
"keep currency and sign under the mask") moved to a classification by context.

## Key takeaways

- Decisions D1–D8 (device-scoped, plain key, off by default, no protection against DevTools/API/exports, money
  only, percentages visible, inputs out of scope, **sign visible**) and the round-2 rules ("wealth is what reveals
  what you own; a market price is not wealth"; "privacy hides the number, not the currency"):
  [[decisions/privacy-mask-at-the-formatter]].
- Mask where the number becomes a string, not in each component; the planned `SensitiveValue` component was
  suspended by a measured decision.
- Default to hiding: an unclassified amount is `personal`.
- The anti-regression gate tests a premise and is keyed by content: [[concepts/premise-gate-keyed-by-content]].
- The repair of the risk formatter on 2026-09-24 made a stale claim of
  [[decisions/asset-global-page-shows-no-money]] (annotated today).

## Residuals (backlog 38)

I-05 — gate precision on `PerformanceChart` (the two `shortMoney` branches and `axisTickAmount` are outside what the
source scan sees).

## Wiki pages updated

- [[decisions/privacy-mask-at-the-formatter]], [[features/F-101]], [[concepts/premise-gate-keyed-by-content]] — new.
- [[decisions/asset-global-page-shows-no-money]] — update note (the formatter it waited for was repaired).

## Source files

| Role | Path |
|------|------|
| README | `LibreFolio_developer_journal/Release_2/phases/24_privacyGlobal/README.md` |
| Analysis (§0 decisions, §1.8 gate) | `LibreFolio_developer_journal/Release_2/phases/24_privacyGlobal/analysis-phase00PrivacyGlobal.md` |
| Round 1 — masking core | `LibreFolio_developer_journal/Release_2/phases/24_privacyGlobal/plan-phase00PrivacyGlobalRound1-MaskingCore.prompt.md` |
| Round 2 — post review | `LibreFolio_developer_journal/Release_2/phases/24_privacyGlobal/plan-phase00PrivacyGlobalRound2-PostReview.prompt.md` |
| Masking primitives | `frontend/src/lib/utils/privacy/maskable.ts` |
| Gate | `frontend/src/lib/utils/privacy/moneyRenderSites.test.ts` |
| Risk formatter (repaired 2026-09-24) | `frontend/src/lib/components/risk/riskAnalysisHelpers.ts` |
