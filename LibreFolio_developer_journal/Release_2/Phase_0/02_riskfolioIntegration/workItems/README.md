# Work items — Risk Analysis

Snapshot persistente del tracker operativo interno usato durante
l'implementazione della Risk Analysis.

**Data snapshot**: 29 Luglio 2026
**Totale**: 53 work item — 32 `done`, 21 `pending`

I testi inglesi di titolo e descrizione sono copiati senza riscrittura dal
tracker della sessione. Questi file documentano la scomposizione esecutiva; i
contratti e i piani nella cartella padre restano le fonti autoritative.

## Mappa P0-P13 → gate

| Gate | P-map | Work item | Stato |
|---|---|---:|---|
| [G0 — Piano](./g0-plan.md) | Materializzazione piano | 1 | ✅ |
| [G1 — Quant](./g1-quant-foundation.md) | P0 | 1 | ✅ |
| [G2 — Serie](./g2-canonical-series.md) | P1-P2 | 1 | ✅ |
| [G3 — Rolling](./g3-rolling-risk.md) | P3-P4 backend | 1 | ✅ |
| [G4 — Deterministico](./g4-deterministic-multiasset.md) | P5-P10 backend/API | 13 | ✅ |
| [G5 — Avanzato](./g5-stochastic-scale-optimization.md) | P11-P13 | 10 | ✅ |
| [G6 — Applicazione](./g6-frontend.md) | scope/scenari + UI P4/P6-P13 | 23 | ▶️ autorizzato |
| [GF — Finale](./gf-final-validation.md) | Validazione, knowledge, handoff | 3 | ✅ |

G1-G6 sono i sei gate di consegna. G0 materializza il piano prima
dell'esecuzione; GF raccoglie la chiusura trasversale.

## Semantica dello stato

- `done`: item chiuso nel tracker.
- `pending`: item G6 non ancora iniziato.
- `depends_on`: in G6 ogni item ha un solo predecessore; i gate umani sono item
  espliciti che bloccano la vista successiva.

## Riferimenti

- [Master implementativo](../plan-phase01RiskAnalysisImplementation.prompt.md)
- [Piano applicativo P0-P13](../plan-phase01RiskAnalysisApplication.prompt.md)
- [Step 6 corrente](../plan-phase01Step6RiskFrontendIntegration.prompt.md)
- [Information Architecture G6](../plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md)
- [Report corrente e handoff](../report-phase01RiskAnalysisCurrentStateAndHandoff.md)

> **Nota G6**: i sette item storici sono stati sostituiti dalla catena lineare
> approvata. Backend completo prima del frontend; poi sette viste funzionali,
> ciascuna seguita da review visuale umana.
