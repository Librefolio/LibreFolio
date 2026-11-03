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
| 3 | **F-AI (b)** — code on the "FX on cash" effect (`portfolio_service.py`, `OtherPeriodEffect`), AI Export + `PerformanceChart.svelte` + `OtherPeriodEffectsTable.svelte` read the code, portfolio export shows it apart, broker by broker | ✅ 3/11/2026 (checkpoint 2, front check 0 errors) |
| 4 | **R11 + MF-A13** — export opened from a broker page: whole amounts (`apply_ownership_share=False`), a note with role and share; MF-A13 closure rounding declared if a dataset shows it | ✅ 3/11/2026 (checkpoint 3) |
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

### Step 3 — F-AI (b) done (3/11/2026, checkpoint 2)

> **Note implementazione**: `schemas/portfolio.py` — `OtherPeriodEffectCode` (`fx_on_cash`) and `OtherPeriodEffect.code` (optional, None for every other row).
> `portfolio_service.py` — the exchange-result row sets `code=OtherPeriodEffectCode.FX_ON_CASH` (the only line of that file; description "FX on cash" unchanged,
> figures unchanged). AI Export: `EffectRow.code`; `portfolio.flows_income` gets `fx_on_cash_effects` (rows filtered by code, one per broker, sorted by broker id).
> v2 of `portfolio.flows_income`, `portfolio.fees_taxes`, `broker.flows_income_costs` (all three carry `EffectRow`, which gained `code`); renderer map {1,2}.
> Frontend: `OtherPeriodEffectsTable.svelte` and `PerformanceChart.svelte` read `code === 'fx_on_cash'`, no longer the English description.
> Red first: service test (collection error: no `OtherPeriodEffectCode`), table tests (2 failed), chart test (red with the code check replaced by the description).
> **⚠️ Fuori pista**: `foreign-cash-real.spec.ts` (E2E) compares rows by description/category/amount/broker only, so it needs no change; not run (heavy).

### Step 4 — R11 + MF-A13 done (3/11/2026, checkpoint 3)

> **Note implementazione**: one rule, `payloads/portfolio_broker.counts_ownership_share(scope)` (False for a Broker scope, True otherwise);
> the share itself stays in `native_cash.broker_shares`. Hooks, from `ondata6/MF6-3-checkpoint.md` «Per AIX»:
> `load_portfolio_report` (new keyword `apply_ownership_share`, default = the scope's domain) — every `broker.*` component that reads the
> shared report is whole; `drawdown_context` (broker: `PortfolioRiskScope(..., apply_ownership_share=False)`);
> `broker_cost_efficiency._load_broker_ownership_share(..., apply_ownership_share)` now through `broker_shares` (the broker export: share 1, so
> `ownership_share_ratio` is 1 and the turnover is whole); `portfolio_income` reads the shares through `broker_shares` too (no number changes: the
> component is portfolio-only). `broker.concentration_comparison` loads the whole-portfolio report whole as well, so the broker's share of the
> portfolio is on one basis. Decided, no number change for the user: `asset_resources.py:249` and `fx_core.py:303` keep the owner's share
> (the asset and FX pages are not the broker page; the Dashboard counts the user's part).
> The note: `broker.provenance` gains `ownership` (`role`, `owner_stake_ratio`, `amounts_basis="whole_broker"`, `explanation`); the component is
> already at +1 over v1.2.1 (v3), so no further bump. MF-A13 declared in `asset.provenance.price_provenance_note` (already v2 over v1.2.1).
> No dataset bump: no dataset changes its composition. `build_currency_allocation` now uses `slice_percents({**covered_amounts, None: unknown_amount})`.
> **⚠️ Fuori pista**: the existing cost-efficiency test that asserted the owner's 0.25 share on the turnover was rewritten (R11 changes that expectation);
> the existing provenance version test now seeds the access row.
