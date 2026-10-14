# Recap corretto — Risk Analysis backend (G0-G5) + ripresa G6

**Data**: 28 Luglio 2026
**Ultima revisione G6**: 29 Luglio 2026
**Stato**: backend G0-G5 completato e auditato; IA G6 approvata, esecuzione
backend-first autorizzata.

## 1. Esito

La correzione richiesta è completa:

- nessun adapter production NumPy/SciPy;
- simulazione MC/QMC production con QuantLib 1.43;
- calcolo nativo in processi `spawn`, mai nel thread web;
- due pool separati, lazy, isolati e liberati dopo idle timeout;
- Riskfolio-Lib 7.0.1 adottata per P13;
- RQMC rimosso;
- test matematici basati su oracle motivati;
- benchmark dei pool production reali;
- service/API/client compatibili;
- nessuna migrazione DB;
- nessun lavoro frontend P13 avviato.

Le vecchie conclusioni «NumPy più veloce quindi production», «single
`asyncio.to_thread`» e «P13 respinto» sono superseded.

> **Fonte corrente G6.** Per placement, scope e scenari leggere prima
> [`plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md`](./plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md):
> quattro tab Assets Global, P13 solo Allocation, Dashboard/Broker condivisi,
> `portfolio.broker_ids`, catalogo YAML typed, replay con proxy manuali e shock
> `Other=100%`/`european_union`. Audit proxy, cache lazy, bucket UX e tag YAML
> opzionali sono espliciti. Le esclusioni replay usano residuo zero-return.

## 2. Documenti da leggere

| Ordine | Documento | Ruolo |
|---:|---|---|
| 0 | [`plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md`](./plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md) | IA G6 corrente e fonte placement/scenari. |
| 1 | [`plan-phase01Step6RiskFrontendIntegration.prompt.md`](./plan-phase01Step6RiskFrontendIntegration.prompt.md) | Sequenza esecutiva G6 autorizzata e lineare. |
| 2 | [`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md) | Master G0-G6 e stato corrente. |
| 3 | [`contract-phase01RiskMetricsMathematical.md`](./contract-phase01RiskMetricsMathematical.md) | Contratto matematico/semantico, incluso stress. |
| 4 | [`analysis-phase01RiskModularityAndPlacement.md`](./analysis-phase01RiskModularityAndPlacement.md) | Placement e riuso. |
| 5 | [`plan-phase01RiskAnalysisApplication.prompt.md`](./plan-phase01RiskAnalysisApplication.prompt.md) | Piano P0-P13 aggiornato. |
| 6 | [`report-phase01RiskBackendAuditAndRemediation.md`](./report-phase01RiskBackendAuditAndRemediation.md) | Stato tecnico backend finale. |
| 7 | [`report-phase01RiskAnalysisCurrentStateAndHandoff.md`](./report-phase01RiskAnalysisCurrentStateAndHandoff.md) | Handoff storico e falsa pista. |
| 8 | [`plan-phase01Step5SimulationScaleOptimization.prompt.md`](./plan-phase01Step5SimulationScaleOptimization.prompt.md) | Implementazione P11-P13. |
| 9 | [`spike-phase01QuantLibraries.md`](./spike-phase01QuantLibraries.md) | Versioni, solver, lock, Docker arm64/amd64. |
| 10 | [`spike-phase01SimulationAdapters.md`](./spike-phase01SimulationAdapters.md) | Oracle MC/QMC QuantLib. |
| 11 | [`benchmark-phase01SimulationScale.md`](./benchmark-phase01SimulationScale.md) | Cold/warm, RSS, cache, concorrenza, recycle e idle reap. |

## 3. Architettura backend finale

### 3.1 Process boundary

`SpawnWorkerPool` implementa:

- start method `spawn`;
- lane create alla prima richiesta, persistenti durante attività;
- idle reap configurabile e restart lazy;
- coda bounded e backpressure;
- timeout hard per job;
- recycle della sola lane dopo timeout, crash o errore remoto;
- shutdown idempotente nel lifespan FastAPI;
- metriche PID, cold/warm, queue wait, execution, round trip e peak RSS;
- payload/result serializzabili.

Pool separati:

1. simulation → QuantLib;
2. optimization → Riskfolio/CVXPY.

Il request channel usa una `multiprocessing.Queue`; il response channel una pipe
one-way. La pipe elimina i semaphore leak osservati nei test di crash forzato.

La cache parent:

- è content-keyed;
- collassa miss concorrenti identici;
- protegge il future condiviso dalla cancellazione dei follower;
- cancella esplicitamente i follower se il leader viene cancellato;
- non lascia future irrisolti.

`asyncio.to_thread` resta solo per IPC/join bloccanti o analytics leggere. QuantLib
e Riskfolio calcolano esclusivamente nel child.

### 3.2 QuantLib P11

MC:

```text
UniformRandomGenerator
→ Gaussian sequence
→ GaussianMultiPathGenerator
→ StochasticProcessArray
```

QMC:

```text
SobolRsg.skipTo(sobol_start_index)
→ InvCumulativeSobolGaussianRsg
→ StochasticProcessArray.evolve
```

Regole:

- stato iniziale asset normalizzato a `1`;
- griglia giornaliera, `dt=1/365`;
- GBM correlato multi-asset;
- `random_seed` MC deterministico;
- `sobol_start_index` QMC = indice iniziale Sobol;
- path QMC in potenza di due;
- limite `asset × horizon_days <= 21.201`;
- NumPy solo per algebra, aggregazione e oracle;
- nessun fallback production.

### 3.3 Riskfolio P13

Nuovo analytic: `portfolio_optimization`.

Scope:

- `portfolio`;
- `asset_set`.

Il backend G5 conserva ancora lo scope `broker`; la foundation G6 lo migra a
`portfolio + broker_ids=[id]` e poi elimina `kind=broker`.

Strategie:

- minimum variance;
- maximum Sharpe;
- equal risk contribution/risk parity.

Covariance:

- historical;
- Ledoit-Wolf;
- OAS.

Vincoli:

- long-only;
- budget `1`;
- no leverage;
- `min_weight`/`max_weight` globali validati;
- infeasibilità → errore esplicito.

Solver allowlisted:

- CLARABEL;
- SCS.

Output:

- pesi ordinati;
- rendimento periodico/annuo;
- volatilità annua;
- Sharpe;
- contributi marginali/assoluti/percentuali;
- solver/status;
- constraint summary;
- frontiera e sensitivity opzionali;
- warning e metadata.

Il minimo production è 30 osservazioni allineate. Il DB fixture popolato dispone
di 13 osservazioni congiunte per alcuni scope e restituisce correttamente
`insufficient_history`; fixture sintetiche provano l'esecuzione completa.

## 4. Evidenza matematica

Per `Y_i = log(S_i(T)/S_i(0))`:

```text
E[Y_i] = (mu_i - 0,5 Sigma_ii) T
Cov(Y_i, Y_j) = Sigma_ij T
```

MC, 8.192 path:

| Verifica | Errore massimo | Gate |
|---|---:|---:|
| media | 0,935 SE | 4,5 SE |
| covarianza completa | 1,695 SE | 4,5 SE |
| correlazione Fisher-z | 1,523 SE | 4,5 SE |

QMC:

| Path | Errore media L2 | Errore covarianza Frobenius |
|---:|---:|---:|
| 256 | 6,592e-4 | 8,024e-3 |
| 1.024 | 1,597e-4 | 6,552e-3 |
| 4.096 | 4,933e-5 | 2,586e-3 |

Slope log2:

- media `-0,648`;
- covarianza `-0,283`.

Probe finale:

- `status=ok`;
- direct/spawn identici;
- covariance PSD, correlazione perfetta e volatilità zero coperte;
- percentile ordering, probability of loss, shape e seed coperti.

## 5. Prestazioni finali

### Simulation

| Caso | Cold | Warm | Peak RSS |
|---|---:|---:|---:|
| 1 asset · 1.024 · 30g MC | 1,286 s | 0,071 s | 171,3 MB |
| 1 asset · 1.024 · 30g QMC | 1,244 s | 0,133 s | 171,7 MB |
| 5 asset · 4.096 · 90g MC | 1,824 s | 0,766 s | 174,9 MB |
| 5 asset · 4.096 · 90g QMC | 3,404 s | 2,353 s | 175,3 MB |
| 1 asset · 2.048 · 365g MC | 1,437 s | 0,329 s | 184,0 MB |

QMC medio:

- RNG `0,089 s`;
- evolve `0,515 s`;
- copia/aggregazione path `1,256 s`;
- result aggregation `0,007 s`.

Il costo QMC è soprattutto nel bridge SWIG/copia path, non in calcoli matematici
aggiuntivi nascosti.

Cache simulation:

- first cold `1,523 s`;
- hit `0,000190 s`;
- nessun worker sul hit.

### Optimization

- cold `2,863 s`;
- warm `0,0159 s`;
- peak RSS ~340,6 MB.

### Concorrenza warm

| Dominio | 1 worker | 2 worker | Speedup mediano | RSS 1→2 |
|---|---:|---:|---:|---:|
| simulation | ~1,53 s | ~0,79 s | 1,938x | ~176→349 MB |
| optimization | ~0,087 s | ~0,059 s | 1,477x | ~342→683 MB |

Decisione:

- default `1` worker per pool;
- `>1` configurabile;
- process isolation sempre attivo.

Timeout:

- PID job bloccato terminato;
- lane ricreata con PID nuovo;
- richiesta successiva completata.

Idle:

- default `600 s` distinto per pool;
- simulation reap `0,416 s`, restart cold `1,197 s`;
- optimization reap `0,645 s`, restart cold `2,961 s`;
- nessun reap con job queued/in-flight;
- PID nuovo al restart.

Matrice P12:

- 72 celle;
- 32 accepted;
- 12 dimension limit;
- 28 resource limit.

## 6. Dipendenze e container

Versioni finali:

- Python 3.13.14;
- NumPy 2.5.1;
- QuantLib 1.43;
- Riskfolio-Lib 7.0.1;
- CVXPY 1.9.2;
- CLARABEL 0.11.1;
- SCS 3.2.11;
- `vectorbt` assente;
- `numba` assente.

`pipenv verify` è verde anche dopo l'update intenzionale del lock.

Probe:

- macOS arm64;
- Linux arm64;
- Linux amd64.

Immagine finale:

- tag `librefolio:risk-audit-remediation`;
- digest
  `sha256:98a2cea750af424ffabf7b9ed01beba0afe329fde445e9d85a240f2d492194ac`;
- dimensione non compressa `2.781.625.742` byte;
- smoke: QuantLib/NumPy/Riskfolio + import FastAPI app verdi.

## 7. Superfici modificate

Backend principale:

- `backend/app/services/risk/quant/spawn_worker.py`;
- `backend/app/services/risk/quant/workers.py`;
- `backend/app/services/risk/quant/quantlib_worker.py`;
- `backend/app/services/risk/quant/engine.py`;
- `backend/app/services/risk/quant/optimization_models.py`;
- `backend/app/services/risk/quant/optimization_engine.py`;
- `backend/app/services/risk/quant/riskfolio_worker.py`;
- `backend/app/services/risk_plugins/simulation.py`;
- `backend/app/services/risk_plugins/portfolio_optimization.py`;
- `backend/app/services/risk/base.py`;
- `backend/app/services/risk/service.py`;
- `backend/app/schemas/risk.py`;
- `backend/app/config.py`;
- `backend/app/main.py`.

Test:

- simulation QuantLib;
- optimization Riskfolio;
- worker lifecycle;
- analytic/service;
- API risk.

CLI test:

- `./dev.py test services risk-simulation`;
- `./dev.py test services risk-optimization`;
- `./dev.py test services risk-workers`;
- `./dev.py test services risk-all`.

Compatibilità:

- RQMC rimosso dal contratto e dal controllo frontend già esistente;
- client OpenAPI rigenerato e idempotente;
- nessuna UI P13 aggiunta.

## 8. Validazione

- risk service suite: **74 passed**;
- risk API: **7 passed**;
- risk schema: **21 passed**;
- worker lifecycle: **11 passed**, senza resource-tracker warning;
- oracle QuantLib: `status=ok`;
- benchmark pool: `status=ok`;
- Ruff/Black target: verdi;
- Pipenv lock/import smoke: verde;
- Docker build/smoke: verde;
- frontend check/build di compatibilità: verdi;
- API sync: idempotente.

Suite backend globale:

- external: verde;
- DB: verde;
- service action: 56/57 verdi;
- AI Export: 633 passed, 1 failure concorrente su
  `TargetCoverage.volume_analyzed`;
- il runner si ferma lì, quindi utils/schemas/API/E2E globali non vengono eseguiti
  in quella invocazione;
- il failure non appartiene al dominio risk e non è stato modificato.

## 9. Problemi imprevisti

1. Il primo confronto QuantLib/NumPy non era neutrale e usava un cutoff di
   correlazione arbitrario. Risolto con oracle analitici e standard error.
2. Il seed constructor Sobol QuantLib non sposta lo stream. Risolto con
   `SobolRsg.skipTo(sobol_start_index)` e campi MC/QMC distinti.
3. Riskfolio 7.3.0 portava `vectorbt → numba → numpy<2.5`; la capability richiesta
   funziona con Riskfolio 7.0.1 e NumPy 2.5.1.
4. Un primo lock aveva incluso upgrade wildcard non correlati. Ricostruita la
   closure minima; il successivo `pipenv update` utente è stato preservato.
5. La cancellazione di follower/leader cache poteva cancellare o lasciare sospeso
   il future condiviso. Aggiunti `shield` e gestione esplicita.
6. La response `multiprocessing.Queue` lasciava tre semaphore registrati dopo un
   crash forzato. Sostituita con pipe one-way.
7. Un backtick nel docstring provider rompeva il TypeScript generato. Corretto il
   testo documentale dello schema.
8. Il DB test è stato trovato vuoto durante una verifica concorrente; ripopolato
   con la fixture standard.
9. La suite globale resta bloccata da un singolo test AI Export concorrente,
   estraneo a G5.

## 10. Stato rispetto al piano originale

| Gate | Stato |
|---|---|
| G0 — piano implementativo | ✅ |
| G1 — Quant foundation | ✅ |
| G2 — serie/metadata | ✅ |
| G3 — rolling risk | ✅ |
| G4 — multi-asset deterministico | ✅ |
| G5 — simulazione/scala/ottimizzazione | ✅ corretto e auditato |
| G6 — applicazione | ▶️ IA approvata; correzione backend-first autorizzata |
| GF — chiusura integrata | 🟡 dipende da G6 e da worktree stabile |

P0-P13 backend:

- P0-P2: completati;
- P3-P4 backend: completati;
- P5-P10 backend/API: completati;
- P11 QuantLib MC/QMC: completato;
- P12 process isolation/benchmark: completato;
- P13 Riskfolio backend: completato.

## 11. Cosa resta

Nessun lavoro backend G5 rimasto.

Rispetto al piano originale:

1. migrare `portfolio.broker_ids`, auth/cache/metadata e rimuovere `kind=broker`;
2. costruire catalogo scenari typed/startup-loaded e contratti replay/shock;
3. estrarre shared state/componenti dal pannello monolitico;
4. implementare Asset Detail e attendere approvazione;
5. implementare Correlation, Scenarios e Allocation una alla volta, con gate;
6. migrare Broker Risk, Dashboard Risk e Home card una alla volta, con gate;
7. aggiungere test funzionali e smoke real-backend;
8. lasciare fillings/polish/design finale all'utente;
9. chiudere GF e archiviare la catena di piano.

## 12. Prompt di ripresa

```text
Contesto: LibreFolio Risk Analysis. Backend G0-G5 completato e corretto.
Leggi:
1. _RECAP-and-implementation-reading-guide.md
2. plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md
3. plan-phase01Step6RiskFrontendIntegration.prompt.md
4. plan-phase01RiskAnalysisImplementation.prompt.md

Vincoli:
- non riaprire QuantLib MC/QMC, spawn obbligatorio o Riskfolio 7.0.1;
- nessun adapter NumPy/SciPy production;
- RQMC resta rimosso;
- backend calcola, frontend presenta;
- Assets Global = Assets/Correlation/Scenarios/Allocation;
- P13 UI solo in Allocation;
- Dashboard/Broker = summary + pannelli condivisi lazy;
- scope = portfolio + broker_ids;
- catalogo scenario typed, replay proxy manuali, shock dimensione singola;
- niente redesign/polish salvo validazione utente;
- verificare il lavoro frontend già presente prima di aggiungere codice;
- la suite globale ha un failure AI Export concorrente estraneo al risk backend.

Obiettivo successivo: G6-11, migrazione scope portfolio.
```
