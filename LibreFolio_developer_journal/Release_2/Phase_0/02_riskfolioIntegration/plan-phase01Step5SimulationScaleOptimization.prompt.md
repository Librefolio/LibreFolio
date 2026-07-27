# Step 5 — Simulation, Scale & Optimization (P11-P13)

**Stato**: ⏳ NON INIZIATO.

← Step precedente:
[`plan-phase01Step4MultiAssetRiskBackend.prompt.md`](./plan-phase01Step4MultiAssetRiskBackend.prompt.md)

← Master:
[`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md)

→ Step successivo:
[`plan-phase01Step6RiskFrontendIntegration.prompt.md`](./plan-phase01Step6RiskFrontendIntegration.prompt.md)

## 1. Obiettivo

Implementare simulazione componibile, decisione di scala e frontiera condizionata,
senza esporre oggetti di libreria.

## 2. P11 — Adapter e simulazione

### 5.1 — Contratti

**Stato**: ⏳.

Separare:

- stochastic process;
- sampling MC/QMC/RQMC;
- config;
- portfolio aggregation;
- metrics;
- metadata;
- renderer-neutral result.

### 5.2 — Spike QuantLib vs NumPy/SciPy

**Stato**: ⏳.

Confrontare:

- single/multi-asset;
- MC/QMC/RQMC;
- seed;
- memoria/velocità;
- binding ergonomics;
- testabilità;
- manutenzione.

### 5.3 — Production adapter

**Stato**: ⏳.

GBM giornaliero correlato; output percentili e distribuzione. QuantLib principale
solo se G1 lo supporta; SciPy copre RQMC o intero adapter come fallback.

### 5.4 — Cache costosa

**Stato**: ⏳.

Chiave:

```text
scope + range + currency + tx/price/fx/split fingerprints
+ params + algo_version + seed
```

Nessuna invalidazione manuale.

## 3. Thread/process safety

Se QuantLib è production:

- worker `spawn` singolo già in P11 per isolamento;
- nessuna esecuzione QuantLib concorrente in thread;
- solo input/output serializzabili;
- oggetti QuantLib creati nel worker.

P12 decide soltanto il numero di worker.

## 4. P12 — Benchmark scale gate

### 5.5 — Benchmark matrix

**Stato**: ⏳.

- asset: 1/5/20/50;
- path: 1k/10k/100k;
- anni: 1/5/10;
- MC/QMC/RQMC;
- single vs multi spawn;
- tempo, memoria, IPC, startup, stabilità.

### 5.6 — Decisione pool

**Stato**: ⏳.

Attivare >1 worker solo con beneficio ripetibile e RAM accettabile. Altrimenti
chiudere P12 come `single-worker`.

## 5. P13 — Riskfolio-Lib

### 5.7 — Adapter frontier

**Stato**: 🚫 CHIUSO DAL GATE G1 — 27 Luglio 2026.

- min-risk;
- max-Sharpe stimato;
- risk parity;
- covariance shrinkage;
- vincoli pesi;
- sensibilità;
- timeout/cancellazione.

Nessuna raccomandazione assertiva.

> **Note implementazione**: il probe P0 ha validato le formule ma respinto
> l'adozione runtime: Riskfolio richiede NumPy `<2.5` e aggiunge circa 1 GiB
> all'immagine. P13 non produrrà adapter, endpoint, capability o UI in Release 2.
> Evidenza:
> [`spike-phase01QuantLibraries.md`](./spike-phase01QuantLibraries.md).

## 6. Test

- seed/reproducibility;
- shape/momenti/correlazioni;
- MC vs QMC/RQMC;
- convergence/stability;
- serialization;
- worker isolation;
- timeout/error propagation;
- cache key;
- single/multi equivalence;
- solver/frontier fixture.

## 7. Gate G5

- adapter unico e testato;
- decisione P12 misurata;
- decisione P13 misurata;
- capability catalog espone solo funzioni disponibili;
- backend pronto per rendering.

## 8. Rischi/fallback

- binding QuantLib incompleto → NumPy/SciPy;
- spawn overhead → single worker;
- Riskfolio respinta → nessuna frontier capability;
- estimation error → metadata/wording obbligatori.

## 9. Progress rule

Dopo ogni task aggiornare stato/data/note/fuori-pista qui e nel master.
