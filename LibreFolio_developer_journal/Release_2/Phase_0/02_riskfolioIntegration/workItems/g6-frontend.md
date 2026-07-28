# G6 — Frontend integration

← [Indice work item](./README.md)

**P-map**: UI P4/P6-P13
**Stato gate**: ⏸️ fermato su richiesta
**Work item**: 7 `blocked`

`blocked` registra lo stop esplicito dopo la chiusura backend. Store,
componenti, quattro route ed E2E mock erano già parzialmente materializzati, ma
non riallineati e ricertificati; la UI P13 è assente.

## `risk-frontend`

**Titolo**: Wiring functional risk UI
**Stato**: `blocked`
**Dipende da**: `risk-stochastic-backend`
**Creato**: 2026-07-27 09:58:43
**Aggiornato**: 2026-07-28 14:08:42

Execute frontend portions of P4/P6-P13 only after backend gates: API sync,
stores, tabs, heatmap, KPI/PCTR/stress/comparison/VaR/simulation/frontier
capability wiring, sync/quality states, i18n, and functional E2E. Deferred by
explicit user stop after backend completion; resume only on a new G6 request.

## `g6-risk-store`

**Titolo**: Creating risk client store
**Stato**: `blocked`
**Dipende da**: —
**Creato**: 2026-07-27 15:17:37
**Aggiornato**: 2026-07-28 14:08:42

Add typed catalog/query cache with stable request keys, capability checks,
session/mutation invalidation, and tests. Deferred by explicit user stop after
backend completion; resume only on a new G6 request.

## `g6-risk-components`

**Titolo**: Building shared risk panels
**Stato**: `blocked`
**Dipende da**: —
**Creato**: 2026-07-27 15:17:37
**Aggiornato**: 2026-07-28 14:08:42

Add correlation heatmap and shared functional risk output panel for KPI, PCTR,
stress, comparison, VaR/CVaR, simulation, quality, metadata, and PageSyncModal.
Deferred by explicit user stop after backend completion; resume only on a new
G6 request.

## `g6-route-wiring`

**Titolo**: Wiring four risk scopes
**Stato**: `blocked`
**Dipende da**: —
**Creato**: 2026-07-27 15:17:37
**Aggiornato**: 2026-07-28 14:08:42

Integrate Asset Global correlation, Dashboard Risk, Broker Risk, and Asset
Detail risk panel without frontend financial calculations. Deferred by
explicit user stop after backend completion; resume only on a new G6 request.

## `g6-i18n`

**Titolo**: Adding risk translations
**Stato**: `blocked`
**Dipende da**: —
**Creato**: 2026-07-27 15:17:37
**Aggiornato**: 2026-07-28 14:08:42

Add all UI-specific Risk keys in EN/IT/FR/ES and pass the i18n audit. Deferred
by explicit user stop after backend completion; resume only on a new G6
request.

## `g6-e2e`

**Titolo**: Adding functional risk E2E
**Stato**: `blocked`
**Dipende da**: —
**Creato**: 2026-07-27 15:17:37
**Aggiornato**: 2026-07-28 14:08:42

Add and register focused functional tests for risk tabs, selection, states,
sync, charts, simulation, and capability gating. Deferred by explicit user
stop after backend completion; resume only on a new G6 request.

## `g6-validation`

**Titolo**: Running G6 validation
**Stato**: `blocked`
**Dipende da**: —
**Creato**: 2026-07-27 15:17:37
**Aggiornato**: 2026-07-28 14:08:42

Run API sync, targeted backend/API regressions, frontend tests/check/build, E2E
risk, Docker validation, graph update, and update plans/wiki. Deferred by
explicit user stop after backend completion; resume only on a new G6 request.
