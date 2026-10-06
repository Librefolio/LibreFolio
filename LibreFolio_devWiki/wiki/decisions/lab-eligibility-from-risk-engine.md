---
title: "Asset Global: eligibility comes from Risk's engine, and an ineligible asset is parked, not dropped"
category: decision
status: resolved
date: 2026-09-25
tags: [frontend, risk, asset-global, eligibility, i18n, selection]
related: [asset-global-page-shows-no-money, discarded-risk-answer-read-as-empty]
---

# Decision: eligibility comes from Risk's engine, and an ineligible asset is parked, not dropped

## Context
The developer's review of the laboratory's "+" picker (24/09): four crowdfunding assets were offered as selectable
although they had **0 prices recorded**. "The point is not the crowdfunding type, it is the zero prices", and it
"should reconnect to the asset eligibility engine". Risk's backend (`POST /api/v1/risk/eligibility`, time ② of its
redesign) arrived in the lab's branch with the Risk → F merge `2c02ff070`.

## Options Considered
1. **A frontend rule** (e.g. "no prices loaded → disabled") — rejected: whether an asset has enough prices in a period
   is a calculation, and calculations live in the backend.
2. **Drop ineligible assets from the selection** — simple, but a change of period brings them back as eligible and the
   user has to find them again.
3. **Park them** — keep them in the selection as greyed chips with the engine's reason, and leave them out of the
   requests.

## Decision
- **The lab never computes eligibility.** It asks the engine once for the whole page catalogue (at most 500 ids per
  request, never with an empty list), again when the catalogue, the period or the currency changes, with a 300 ms
  debounce, and drops a superseded answer.
- **No verdict means selectable.** A failed call shows `risk-eligibility-failed` and locks nothing: the engine can make
  the lab stricter, never emptier.
- **Option 3, parking.** `analysedIds` = the selection minus `ineligible`; only those reach the three sections. The
  sync still covers the parked ones, because an asset without prices is sometimes an asset that was never synced.
  The developer: "read-only but struck through in the presets, while the + cannot add it — it is clear and coherent".
- **The quick actions act on the eligible catalogue**, not on a filter: the type and currency filters moved into the
  "+", where they narrow a list rather than a button. `none` empties everything, parked chips included; `invert` leaves
  the parked ones in place.
- **The "+" lists ineligible assets read-only**, in a section of their own, with the engine's reasons; `warning`
  assets stay selectable with the warning.
- **Wording**: `reasonText` is an exhaustive `switch` over the generated `RiskEligibilityReason`, with every key
  written out in full inside `t(...)`, so the i18n audit sees it and a reason the engine adds later fails `front
  check`. A missing translation falls back to the level's label, never to a raw key. Thresholds (`min_quotes`,
  `stale_days`) come from the response, never hard-coded.

## Consequences
- "My assets" has two meanings, kept apart by their labels:
  - **"All mine"** (holdings command and opening seed) = open positions on the period's **last day**, read from the
    portfolio report's holdings (the light report, without history).
  - **`held_by_me` / `held_by_others`** on the asset list = held **now**. They drive the grid's three usage panels
    (`assetScope`), since 24/09, instead of `tx_count_own`.
  - The two coincide only when the period ends today.
- `risk.eligibility.*` belongs to F until the F → Risk merge; Risk adds `no_price_history` in its checkpoint C.

## Source files
| Role | Path |
|------|------|
| Verdicts, wording, batching | `frontend/src/lib/components/risk/eligibility.ts` |
| Tests | `frontend/src/lib/components/risk/eligibility.test.ts` |
| Panel: request, parking, holdings | `frontend/src/lib/components/risk/AssetSetRiskPanel.svelte` |
| The "+" picker | `frontend/src/lib/components/risk/LabAssetPicker.svelte` |
| Ladder and quick actions | `frontend/src/lib/components/risk/assetSetSelection.ts` |
| Usage panels (`assetScope`) | `frontend/src/routes/(app)/assets/+page.svelte` |
| Engine | `backend/app/services/risk/eligibility.py` |

## Links
- [[decisions/asset-global-page-shows-no-money]]
- Source: `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation_2/progress/F-laboratorio-postmerge.md`
