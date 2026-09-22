# G6 — Application integration

← [Indice work item](./README.md)

**P-map**: scope/scenario foundation + UI P4/P6-P13
**Stato gate**: ▶️ autorizzato
**Modello dipendenze**: catena unica; ogni item dipende soltanto dal precedente

> **Approvazione — 29 Luglio 2026.** IA e contratti G6 sono approvati. Il lavoro
> procede backend-first; ogni vista frontend è seguita da uno stop per review
> visuale umana. Il peso degli asset esclusi dal replay portfolio/broker resta
> residuo a rendimento zero, senza rinormalizzazione.

## Catena

| Ordine | Work item | Stato | Dipende da |
|---:|---|---|---|
| 0 | `g6-approval-sync` | ✅ | G6 IA |
| 1 | `g6-backend-scope` | ✅ | `g6-approval-sync` |
| 2 | `g6-backend-catalog` | ✅ | `g6-backend-scope` |
| 3 | `g6-backend-replay` | ✅ | `g6-backend-catalog` |
| 4 | `g6-backend-shock` | ✅ | `g6-backend-replay` |
| 5 | `g6-backend-close` | ✅ | `g6-backend-shock` |
| 6 | `g6-frontend-foundation` | ✅ | `g6-backend-close` |
| 7 | `g6-view-asset-detail` | 🔄 rifinitura H1 | `g6-frontend-foundation` |
| 8 | `g6-gate-asset-detail` | ⏳ review seriali | `g6-view-asset-detail` |
| 9 | `g6-view-assets-correlation` | ⏳ | `g6-gate-asset-detail` |
| 10 | `g6-gate-assets-correlation` | ⏳ | `g6-view-assets-correlation` |
| 11 | `g6-view-assets-scenarios` | ⏳ | `g6-gate-assets-correlation` |
| 12 | `g6-gate-assets-scenarios` | ⏳ | `g6-view-assets-scenarios` |
| 13 | `g6-view-assets-allocation` | ⏳ | `g6-gate-assets-scenarios` |
| 14 | `g6-gate-assets-allocation` | ⏳ | `g6-view-assets-allocation` |
| 15 | `g6-view-broker-risk` | ⏳ | `g6-gate-assets-allocation` |
| 16 | `g6-gate-broker-risk` | ⏳ | `g6-view-broker-risk` |
| 17 | `g6-view-dashboard-risk` | ⏳ | `g6-gate-broker-risk` |
| 18 | `g6-gate-dashboard-risk` | ⏳ | `g6-view-dashboard-risk` |
| 19 | `g6-view-home-risk-card` | ⏳ | `g6-gate-dashboard-risk` |
| 20 | `g6-gate-home-risk-card` | ⏳ | `g6-view-home-risk-card` |
| 21 | `g6-integrated-validation` | ⏳ | `g6-gate-home-risk-card` |
| 22 | `g6-close-handoff` | ⏳ | `g6-integrated-validation` |

## Backend

1. `g6-backend-scope`: `portfolio.broker_ids`, access control, metadata/cache,
   equivalenza subset singolo, eliminazione `kind=broker`.
2. `g6-backend-catalog`: YAML built-in/host typed, startup loader, localizzazione,
   tag, warning host, `european_union`, API read-only.
3. `g6-backend-replay`: rendimenti osservati, proxy manuali, esclusioni,
   zero-return residual, audit e qualità.
4. `g6-backend-shock`: dimensione singola, exposure canoniche, `Other=100%`,
   precedenza Paese > UE > Other e audit.
5. `g6-backend-close`: test, lint/format, OpenAPI/client sync. Completato con
   93 test Risk service, 10 API post-sync, Ruff mirato, sync idempotente,
   `front check`, build statico e smoke login `:6040` verdi.

## Frontend

La foundation è non visuale. Le viste vengono implementate e approvate in ordine:

1. Asset Detail — Risk & Scenarios;
2. Assets Global — Correlation;
3. Assets Global — Scenarios;
4. Assets Global — Allocation;
5. Broker Detail — Risk;
6. Dashboard — Risk;
7. Home Risk card.

Ogni gate:

- arriva dopo test logici/strutturali;
- accetta correzioni soltanto sulla vista corrente;
- richiede via libera esplicito prima dell'item successivo;
- non usa snapshot, pixel test o assertion estetiche.

### Asset Detail — consegna G6-20

`Overview | Risk & Scenarios` è implementato e validato funzionalmente.
Overview resta invariato; Risk & Scenarios riusa rolling SignalPlugin, query
asset-scoped, catalogo scenario typed, audit replay/shock e viste MC/QMC.
Nessuna Allocation è stata aggiunta.

Il gate corrente è la review visuale H1. `g6-view-assets-correlation` resta
bloccato fino al via libera esplicito dell'utente.

### Rifinitura H1 — catena attiva

```text
H1-R0 documenti ✅
-> H1-R1 historical_kpi asset ✅
-> H1-R2 test/API sync ✅
-> H1-R3 Abs/% dentro PriceChartFull Asset/FX ✅
-> H1-R4 AI Export nelle PageToolbar Asset/FX ✅
-> H1-G1 review shell ✅
-> H1-R5 rischio osservato automatico
-> H1-R6 downside automatico
-> H1-G2 review
-> H1-R7 confronto/beta guidati
-> H1-G3 review
-> H1-R8 scenari progressive disclosure
-> H1-G4 review finale
```

Ogni item ha un solo predecessore. Overview mantiene Signals personalizzabili;
Risk usa istanze automatiche non persistite. Nessun prompt Risk AI Export viene
aggiunto durante il solo riposizionamento del menu.

> **Note implementazione H1-R1/R2 — 30 Luglio 2026**:
> `historical_kpi@2.0.0` è ora scope-neutral per asset/portfolio e dichiara
> correttamente close-return vs TWRR nei metadata. Test Risk service/API verdi,
> consumer frontend migrati e generazione OpenAPI/client verificata idempotente.
>
> **Note implementazione H1-R3 — 30 Luglio 2026**: controllo `Abs/%`
> centralizzato nel grafico condiviso con callback al parent; copie topbar
> eliminate. Type-check e regressioni mirate Asset/FX verdi.
>
> **Note implementazione H1-R4 — 30 Luglio 2026**: AI Export spostato nelle
> `PageToolbar` Asset/FX e rimosso dagli header Signals; la toolbar Asset è
> condivisa fra Overview e Risk. Il Refresh page-level ricarica anche Risk senza
> duplicare azioni nel pannello. Build, type-check, i18n, risk-store e suite
> Playwright Asset/FX/Risk sono verdi.
>
> **Gate H1-G1 — APPROVATO 30 Luglio 2026**: shell condivisa approvata;
> H1-R5 è il prossimo e unico item eseguibile.
>
> **Correzione H1-G1 — 30 Luglio 2026**: rimossa la card `TabBar` autonoma da
> Asset Detail; `Overview | Risk & Scenarios` usa ora direttamente la zona tabs
> della `PageToolbar`, come Dashboard. Il banner qualità segue la toolbar.
> Regressioni Asset Detail/Risk verdi; correzione approvata visualmente.
