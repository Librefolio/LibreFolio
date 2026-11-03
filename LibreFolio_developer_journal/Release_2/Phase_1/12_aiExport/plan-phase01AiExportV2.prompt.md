# AI Export v2 — wave 6 · AIX

> Session AIX, wave 6 (3/11/2026). Base `898bc9d15` (`dev_release2`). Lane: port 6207, `/tmp/librefolio-r13-o6-aix`.
> Kickoff: `salvataggi-worktrees-20261021/ondata6/kickoff-AIX.md`. Related: [11_financialMath plan](../11_financialMath/plan-phase01FinancialMath.prompt.md)
> (MF writes that file; this one is AIX's own, so nobody shares a writer).

## Ondata 6 · AIX

One v2 bump for everything below (rule: a component is bumped at most +1 over the last released version).

| Step | Lot | State |
|---|---|---|
| 1 | **T-U9** — the two hand-made percentages in `broker_concentration_context.py` (`:212`, `:407`) go through `weights.percent_of`; `reason_code` of `broker.concentration_comparison` says the truth (no summary vs summary without positions) | ✅ 3/11/2026 |
| 2 | **MF-C2, contract side** — `AllocationItem.value` nullable already reaches `AllocationSlice.percent`; the components that carry slices are bumped to v2, the renderer shows an empty percent honestly | ✅ 3/11/2026 |
| 3 | **F-AI (b)** — code on the "FX on cash" effect (`portfolio_service.py`, `OtherPeriodEffect`), AI Export + `PerformanceChart.svelte` + `OtherPeriodEffectsTable.svelte` read the code, portfolio export shows it apart, broker by broker | ⏳ |
| 4 | **R11 + MF-A13** — export opened from a broker page: whole amounts (`apply_ownership_share=False`), a note with role and share; MF-A13 closure rounding declared if a dataset shows it | ⏳ |
| 5 | Probe (skill `ai-export-probe-tuning`), test data only | ⏳ |

Checkpoints: (1+2), (3) alone, (4+5), then the probe.

### Analysis (3/11/2026)

- T-U9 sites: `broker_concentration_context.py:212` (`_percent` in `build_currency_allocation`: `value / valued_total * 100`, None when the
  total is 0) and `:407` (`broker_share`, None when the portfolio value is 0). `percent_of(part, total)` returns None for total ≤ 0,
  so a negative total now gives None instead of a negative share: declared as a behaviour change in the checkpoint.
- `reason_code`: `REASON_BROKER_EMPTY = "broker_summary_unavailable"` is raised for `summary is None or not summary.holdings`.
  The message is exact, the code is not when the summary exists but has no positions. Same split for the portfolio side.
- MF-C2: `AllocationSlice.percent` is already `SafeDecimal | None` (MF + Y2). What is left for the contract is the version of the
  components that expose slices and the wording of the renderer for a null percent.

### Steps 1+2 — done (3/11/2026)

> **Note implementazione**: `broker_concentration_context.py` — `_percent` of the currency allocation and `broker_share` now call
> `weights.percent_of` (no local `* 100`). New reason codes `broker_has_no_positions` / `portfolio_has_no_positions` for a summary
> that exists without positions; `broker_summary_unavailable` / `portfolio_summary_unavailable` stay for a missing summary.
> Bumped to v2 (real spec + placeholder in `catalog.py` + `COMPACT_COMPONENT_VERSIONS`): `portfolio.allocations_cash`,
> `broker.concentration_context`, `broker.concentration_comparison`. Red first: 2 reason tests failed on the missing constants
> (`AIX-tu9-red.log`); green 175 passed (`AIX-tu9-green.log`); renderer test red 3 failed with the map entries removed, green 7 passed.
> **⚠️ Fuori pista**: (1) `broker.allocation_concentration` carries no slice → stays v1 (I had bumped it first and reverted).
> (2) The first background `npm ci` chain was started twice by mistake: the second ran while `api sync` of the first, which failed
> (exit 1); `api sync` rerun alone, exit 0 (`AIX-apisync2.log`). (3) Docs (`ai_export_composition.md`) deferred to the last
> docs pass of the wave, one writer.
