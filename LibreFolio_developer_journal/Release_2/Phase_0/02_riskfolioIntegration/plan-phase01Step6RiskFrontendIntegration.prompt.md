# Step 6 — Risk Frontend Integration (UI P4/P6-P13)

**Stato**: ⏳ NON INIZIATO.

← Step precedente:
[`plan-phase01Step5SimulationScaleOptimization.prompt.md`](./plan-phase01Step5SimulationScaleOptimization.prompt.md)

← Master:
[`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md)

## 1. Obiettivo

Collegare backend già verificato alle quattro superfici UI. Scope limitato a
funzionalità, render e i18n; design finale resta all'utente.

## 2. Vincoli

- zero formule/calcoli finanziari TypeScript;
- riuso componenti LibreFolio prima di nuovi;
- EN/IT/FR/ES;
- `data-testid`;
- loading/refreshing/empty/partial/insufficient/error;
- desktop/mobile smoke;
- niente gallery/pixel test/screenshot/polish.

## 3. Task

### 6.1 — Client/store

**Stato**: ⏳.

- `./dev.py api sync`;
- transport/runtime mapping;
- request-keyed risk store;
- capability gating;
- invalidazione `onsynced`.

### 6.2 — Rolling risk Asset Detail

**Stato**: ⏳.

Riusare catalogo/renderer segnali. Aggiungere picker comparison asset
metadata-driven con `AssetSearchAutocomplete`.

### 6.3 — Asset Global Correlation

**Stato**: ⏳.

- tab Assets/Correlation;
- broker filter → asset set, nessun peso;
- add/remove asset;
- nuova heatmap ECharts minimale;
- quality/sync.

### 6.4 — Dashboard/Broker Risk

**Stato**: ⏳.

- tab Risk;
- KPI;
- correlation;
- PCTR barre divergenti;
- stress;
- VaR/CVaR;
- broker label "rischio interno".

### 6.5 — Comparison/Scenarios Asset Detail

**Stato**: ⏳.

Pannello risk-free vs comparison asset, cumulative/relative metrics, stress e
metadata.

### 6.6 — Simulation/Frontier

**Stato**: ⏳.

- percentile bands via `LineChart`;
- label "simulato";
- frontier solo se capability backend;
- nessun controllo morto.

### 6.7 — Data quality/sync

**Stato**: ⏳.

Riusare `DataQualityBanner` e `PageSyncModal`; prezzi+FX preselezionati; utente
avvia; pagina ricarica a `onsynced`.

### 6.8 — Functional E2E

**Stato**: ⏳.

Creare suite risk mirata e registrarla nel test runner.

## 4. Componenti da riusare

- `PageToolbar`, `TabBar`;
- `DataQualityBanner`, `PageSyncModal`;
- `KpiCard`;
- `LineChart` band;
- renderer segnali;
- `PerformanceChart`/bar helper;
- `AssetSearchAutocomplete`;
- select/tooltip/state components.

Nuovo solo se necessario:

- heatmap correlation;
- thin risk result containers.

## 5. Test funzionali

- tab/render;
- plugin config/comparison picker;
- broker -> asset set;
- add/remove asset;
- heatmap/KPI/PCTR;
- warnings/partial/error;
- sync modal/onsynced;
- simulation label/bands;
- frontier capability gate;
- desktop/mobile.

## 6. Gate G6

- quattro scope funzionanti;
- nessun calcolo FE;
- i18n audit verde;
- build/check verde;
- E2E risk verde;
- nessun lavoro di design finale anticipato.

## 7. Chiusura finale

1. test aggregati backend/frontend;
2. Docker build;
3. aggiornare master/sub-plan/recap;
4. aggiornare docs architetturali direttamente coinvolte;
5. file devWiki con decisioni/problemi non ovvi;
6. `./dev.py graph update`.

## 8. Progress rule

Dopo ogni task aggiornare stato/data/note/fuori-pista qui e nel master.
