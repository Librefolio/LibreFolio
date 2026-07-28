# Step 5 — Simulation, Scale & Optimization (P11-P13)

**Stato**: ✅ CORREZIONE COMPLETATA — 28 Luglio 2026. Stop prima di G6.

← Step precedente:
[`plan-phase01Step4MultiAssetRiskBackend.prompt.md`](./plan-phase01Step4MultiAssetRiskBackend.prompt.md)

← Master:
[`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md)

→ Step successivo:
[`plan-phase01Step6RiskFrontendIntegration.prompt.md`](./plan-phase01Step6RiskFrontendIntegration.prompt.md)

## 1. Obiettivo

Implementare simulazione componibile, decisione di scala e frontiera condizionata,
senza esporre oggetti di libreria.

> **⚠️ Riapertura 28 Luglio 2026**: le conclusioni NumPy/SciPy production,
> `asyncio.to_thread`, assenza pool e P13 respinto non sono più decisioni valide.
> Il confronto adapter non era neutrale e il gate correlazione QMC usava una
> soglia arbitraria. Nuovo vincolo: QuantLib MC/QMC in worker `spawn`; Riskfolio
> 7.0.1 in pool separato; NumPy solo algebra/oracle; RQMC rimosso. Le note
> storiche restano sotto per tracciabilità ma sono superseded fino alla nuova
> chiusura G5.

## 2. P11 — Adapter e simulazione

### 5.1 — Contratti

**Stato**: ✅ RIFATTO — 28 Luglio 2026.

Separare:

- stochastic process;
- sampling MC/QMC;
- config;
- portfolio aggregation;
- metrics;
- metadata;
- renderer-neutral result.

> **Note implementazione — 28 Luglio 2026**: contratti MC/QMC strict e
> serializzabili; RQMC rimosso. `seed` QMC = indice iniziale Sobol. Aggiunti DTO
> optimization, errori worker, metriche process boundary, output discriminato
> `optimization` e chiavi cache complete.

### 5.2 — Spike QuantLib vs NumPy/SciPy

**Stato**: ✅ RIFATTO — 28 Luglio 2026.

Confrontare:

- single/multi-asset;
- MC/QMC;
- seed;
- memoria/velocità;
- binding ergonomics;
- testabilità;
- manutenzione.

> **Note implementazione — 28 Luglio 2026**: eliminato il confronto di selezione
> non equivalente. Il nuovo probe verifica QuantLib contro gli oracle analitici
> GBM: MC entro 0,935 SE (media), 1,695 SE (covarianza), 1,523 SE (Fisher-z);
> QMC converge su 256/1.024/4.096 path con slope negative. Output direct/spawn
> identico. Evidenza:
> [`spike-phase01SimulationAdapters.md`](./spike-phase01SimulationAdapters.md).

### 5.3 — Production adapter

**Stato**: ✅ RIFATTO — QUANTLIB — 28 Luglio 2026.

GBM giornaliero correlato QuantLib; output percentili e distribuzione.

> **Note implementazione — 28 Luglio 2026**: MC usa RNG e
> `GaussianMultiPathGenerator` QuantLib. QMC usa `SobolRsg.skipTo(seed)`,
> `InvCumulativeSobolGaussianRsg` e `StochasticProcessArray.evolve`.
> `NumpyScipySimulationAdapter`, SciPy Sobol/`ndtri`, lock in-process e RQMC
> rimossi. NumPy resta solo dopo l'evoluzione per algebra/aggregazione.

### 5.4 — Cache costosa

**Stato**: ✅ COMPLETATO — 27 Luglio 2026.

Chiave:

```text
scope + range + currency + tx/price/fx/split fingerprints
+ params + algo_version + seed
```

Nessuna invalidazione manuale.

> **Note implementazione — 28 Luglio 2026**: cache TTL content-keyed di soli
> risultati engine e collasso async dei miss identici. Cache hit non avvia il
> worker (`0,201 ms` nel benchmark).

## 3. Thread/process safety

Se QuantLib è production:

- worker `spawn` singolo già in P11 per isolamento;
- nessuna esecuzione QuantLib concorrente in thread;
- solo input/output serializzabili;
- oggetti QuantLib creati nel worker.

P12 decide soltanto il numero di worker.

## 4. P12 — Benchmark scale gate

### 5.5 — Benchmark matrix

**Stato**: ✅ RIFATTO — 28 Luglio 2026.

- asset: 1/5/20/50;
- path: 1k/10k/100k;
- anni: 1/5/10;
- MC/QMC;
- single vs multi spawn;
- tempo, memoria, IPC, startup, stabilità.

> **Note implementazione — 28 Luglio 2026**: classificate 72 celle MC/QMC:
> 32 accettate, 12 `dimension_limit`, 28 `resource_limit`. Misurati pool
> persistenti reali: cold/warm, queue, IPC, stage engine, cache, RSS,
> concorrenza e timeout/recycle. Evidenza:
> [`benchmark-phase01SimulationScale.md`](./benchmark-phase01SimulationScale.md).

### 5.6 — Decisione pool

**Stato**: ✅ COMPLETATO — SPAWN PERSISTENTE — 28 Luglio 2026.

Attivare >1 worker solo con beneficio ripetibile e RAM accettabile. Altrimenti
chiudere P12 come `single-worker`.

> **Note implementazione — 28 Luglio 2026**: due pool separati, lazy e
> persistenti, con default configurabile 1 worker. Sul throughput warm, 2 worker
> danno `1,938x` simulation e `1,477x` optimization; RSS passa rispettivamente
> da ~176 a ~349 MB e da ~342 a ~683 MB. Process isolation resta sempre;
> `>1` è configurabile.

## 5. P13 — Riskfolio-Lib

### 5.7 — Adapter frontier

**Stato**: ✅ COMPLETATO — RISKFOLIO 7.0.1 — 28 Luglio 2026.

- min-risk;
- max-Sharpe stimato;
- risk parity;
- covariance shrinkage;
- vincoli pesi;
- sensibilità;
- timeout/cancellazione.

Nessuna raccomandazione assertiva.

> **Note implementazione — 28 Luglio 2026**: aggiunto analytic backend
> `portfolio_optimization` per portfolio/broker/asset-set: min-risk,
> max-Sharpe, risk parity, covariance historical/Ledoit-Wolf/OAS, bound globali,
> frontier e sensitivity opzionali, solver CLARABEL/SCS allowlisted.
> Riskfolio-Lib 7.0.1 funziona con NumPy 2.5.1 e senza vectorbt. Nessuna UI P13
> in questa correzione. Evidenza:
> [`spike-phase01QuantLibraries.md`](./spike-phase01QuantLibraries.md).

## 6. Test

- seed/reproducibility;
- shape/momenti/correlazioni;
- MC vs QMC;
- convergence/stability;
- serialization;
- worker isolation;
- timeout/error propagation;
- cache key;
- single/multi equivalence;
- solver/frontier fixture.

## 7. Gate G5

- [x] adapter unico e testato;
- [x] decisione P12 misurata;
- [x] decisione P13 misurata;
- [x] capability catalog espone solo funzioni disponibili;
- [x] backend pronto; P13 UI esplicitamente rinviata.

> **Note implementazione finale — 28 Luglio 2026**: 68 test service risk e 7
> test API verdi; probe matematico e benchmark `status=ok`; lock verificato;
> immagine finale arm64 costruita e import smoke verde. Il response channel
> worker usa una pipe one-way, eliminando i semaphore warning dopo crash forzato.
> La suite backend globale supera external+DB e tutti i service fino a un solo
> failure concorrente AI Export (`volume_analyzed`), non collegato a G5.

## 8. Rischi/fallback

- binding QuantLib incompleto → errore esplicito, nessun fallback silenzioso;
- spawn overhead → worker persistente lazy;
- Riskfolio/solver failure → risultato unavailable esplicito e lane riciclata;
- estimation error → metadata/wording obbligatori.

> **⚠️ Fuori pista — 28 Luglio 2026**: `./dev.py install` aveva rigenerato
> dipendenze wildcard non correlate. Il lock è stato ricostruito dal baseline,
> mantenendo solo la closure Riskfolio e NumPy 2.5.1. Inoltre `api sync` ha
> esposto un docstring provider con backtick non escapato dal generator: corretto
> il testo schema senza alterare il contratto.

## 9. Progress rule

Dopo ogni task aggiornare stato/data/note/fuori-pista qui e nel master.
