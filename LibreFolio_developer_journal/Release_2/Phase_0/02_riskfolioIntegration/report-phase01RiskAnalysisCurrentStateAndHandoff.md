# Report di stato e handoff — Risk Analysis Fase 0.1

**Data snapshot**: 28 Luglio 2026, ore 16:15 CEST
**Destinatario**: agente di alto livello / revisore architetturale
**Scopo**: descrivere cosa era stato richiesto, cosa è stato realmente costruito,
la falsa pista iniziale sulle librerie quantitative, la correzione effettuata,
lo stato verificato attuale e le decisioni ancora da prendere.

> Questo documento è autosufficiente. Per approfondire formule, benchmark o singoli
> step, usare i riferimenti nella sezione finale.

---

## 1. Executive summary

Il lavoro backend della Risk Analysis è arrivato alla chiusura di **G0-G5**:

- piano P0-P13 materializzato in un master e sei sub-plan backend-first;
- serie canoniche, metadata e qualità dati condivisi;
- cinque metriche rolling asset-scoped nel framework `SignalPlugin`;
- sei analytics deterministici multi-asset nel framework `RiskAnalytic`;
- API bulk autenticata e client OpenAPI sincronizzato;
- Monte Carlo e Quasi-Monte Carlo production con **QuantLib 1.43**;
- ottimizzazione di portafoglio P13 con **Riskfolio-Lib 7.0.1**;
- QuantLib e Riskfolio eseguiti in **pool `spawn` separati, persistenti e isolati**;
- cache content-keyed, deduplicazione dei miss concorrenti e recovery da
  timeout/crash;
- test matematici, service/API, benchmark, lock e Docker verificati;
- nessuna migrazione DB.

Il lavoro non è ancora una chiusura completa della feature:

- **G6 frontend non è formalmente chiuso**;
- nella worktree esiste già una UI funzionale parziale, scritta prima della
  correzione finale G5, ma non è stata riallineata e ricertificata come gate G6;
- la UI non espone ancora P13 `portfolio_optimization`;
- la chiusura integrata GF non è stata eseguita;
- il runner backend globale si ferma su un test AI Export concorrente ed estraneo
  al dominio risk.

La più importante correzione architetturale è questa:

> La prima implementazione G5 aveva sostituito QuantLib con un adapter
> NumPy/SciPy, usato `asyncio.to_thread`, introdotto RQMC e respinto Riskfolio.
> Dopo la contestazione dell'utente, quella conclusione è stata riconosciuta come
> non sufficientemente dimostrata e interamente corretta. Oggi il production path
> usa QuantLib MC/QMC e Riskfolio, sempre fuori dal processo web.

---

## 2. Richieste ricevute e risposta effettiva

| Richiesta / vincolo | Stato | Risposta effettiva |
|---|---|---|
| Trasformare lo studio di alto livello in un piano implementativo | ✅ Fatto | Creati master G0-G6 e sei sub-plan con mapping P0-P13, gate, test, fallback e progress tracking. |
| Procedere dal backend verso la UI | ✅ Rispettato | G0-G5 backend chiusi prima della ripresa formale di G6. |
| Testare matematica e codice backend | ✅ Fatto | Oracle analitici, invarianti, service/API test, worker lifecycle, benchmark e Docker. |
| UI solo funzionale; niente fillings/design finale | 🟡 Parziale | Esiste wiring UI funzionale parziale e test mock; design/polish non affrontati. G6 non è chiuso. |
| Usare librerie quantitative mature, non reinventare la ruota | ✅ Corretto dopo falsa pista | QuantLib 1.43 per MC/QMC; Riskfolio-Lib 7.0.1 per P13; NumPy solo algebra/aggregazione/oracle. |
| Non usare `asyncio.to_thread` come confine dei calcoli pesanti | ✅ Corretto | Calcolo nativo in processi `spawn`; `to_thread` solo per IPC/join bloccanti o analytics leggere. |
| Scalabilità e isolamento più importanti del risparmio di RAM/disco | ✅ Recepite | Isolamento sempre attivo; numero worker configurabile; costo RAM misurato e documentato. |
| Preservare il `pipenv update` intenzionale dell'utente | ✅ Rispettato | Nessun rollback del lock; versioni finali verificate dopo l'update. |
| Fermarsi appena finito il backend | ✅ Rispettato | Nessuna nuova fase G6/P13 UI eseguita dopo la chiusura backend corretta. |

---

## 3. Sequenza reale del lavoro

### 3.1 G0 — Materializzazione del piano

Lo studio originario P0-P13 è stato convertito in:

1. master implementativo G0-G6;
2. P0 Quant foundation;
3. P1-P2 serie canoniche e metadata;
4. P3-P4 rolling risk;
5. P5-P10 analytics deterministici multi-asset;
6. P11-P13 simulazione, scala e ottimizzazione;
7. G6 frontend funzionale.

Il piano ha mantenuto i vincoli fondativi:

- backend calcola, frontend presenta;
- rolling asset-scoped → `SignalPlugin`;
- multi-asset/portfolio → `RiskAnalytic`;
- frequenza matematica giornaliera;
- annualizzazione osservata;
- calendario congiunto;
- cache content-keyed;
- nessuna persistenza dei risultati risk.

### 3.2 G1-G4 — Fondamenta e analytics deterministici

Sono stati costruiti:

- utility canonica per preparazione serie;
- `AssetReturnSeries` con conversione prezzo prima del rendimento;
- metadata di esecuzione separati dalla qualità sorgente;
- supporto qualità per prezzi e FX carried-forward;
- cinque plugin rolling risk:
  - drawdown;
  - rolling volatility;
  - rolling return;
  - rolling Sharpe;
  - rolling beta contro asset reale;
- registry `RiskAnalytic`;
- service/API bulk;
- analytics:
  - portfolio KPI;
  - correlation;
  - risk contribution;
  - hypothetical stress;
  - comparison;
  - historical VaR/CVaR.

Questa parte non è stata invalidata dalla successiva correzione G5.

### 3.3 Primo G5 — La falsa pista

La prima chiusura G5 aveva scelto:

- adapter production NumPy/SciPy;
- SciPy Sobol e `ndtri`;
- MC/QMC/RQMC;
- esecuzione tramite `asyncio.to_thread`;
- lock in-process;
- nessun pool `spawn` production;
- Riskfolio/P13 respinto;
- QuantLib mantenuto soltanto come probe o confronto.

La conclusione presentata era, in sostanza:

```text
QuantLib QMC non supera il gate di correlazione ed è più lento
→ NumPy/SciPy è il production adapter.

Il pool spawn costa più del thread
→ il production path resta in-process con asyncio.to_thread.

Riskfolio confligge con NumPy e pesa troppo
→ P13 viene respinto.
```

L'utente ha correttamente bloccato il proseguimento e chiesto di riesaminare:

- equivalenza reale dei benchmark;
- validità statistica del gate;
- quantità di lavoro svolta da ciascun adapter;
- isolamento del processo web;
- origine del presunto vincolo Riskfolio/NumPy;
- costo effettivo del rollback.

### 3.4 Riapertura e correzione G5

La correzione ha:

- eliminato l'adapter production NumPy/SciPy;
- eliminato RQMC;
- sostituito i gate arbitrari con oracle GBM e standard error;
- reso QuantLib l'unico motore stochastic production;
- introdotto processi `spawn` persistenti;
- separato simulation e optimization in pool distinti;
- adottato Riskfolio-Lib 7.0.1;
- riscritto test, probe, benchmark e documentazione G5;
- aggiornato schema/API/client;
- mantenuto G0-G4 invariato.

---

## 4. Perché la prima conclusione era una falsa pista

### 4.1 Il confronto non era neutrale

Il confronto iniziale attribuiva a QuantLib e NumPy lo stesso lavoro, ma i percorsi
non erano equivalenti:

- QuantLib costruiva/evolveva path multi-step tramite binding SWIG;
- il costo includeva passaggio e copia dei path Python/native;
- NumPy poteva beneficiare di algebra vettoriale diretta e di un percorso più
  semplice;
- una misura di wall time non separava RNG, evoluzione, copia e aggregazione.

Dire «NumPy è più veloce» senza scomporre queste fasi non dimostrava che QuantLib
fosse inefficiente o matematicamente errata. Dimostrava soltanto che due pipeline
diverse avevano costi diversi.

Il benchmark corretto ha misurato separatamente:

- startup cold;
- warm execution;
- RNG;
- process evolution;
- path copy/aggregation;
- result aggregation;
- IPC;
- queue wait;
- RSS.

Nel caso QMC medio, il costo dominante è risultato il bridge SWIG/copia path,
non un errore matematico né un numero sconosciuto di calcoli aggiuntivi.

### 4.2 Il gate di correlazione non era statisticamente motivato

Il primo gate trattava una deviazione di correlazione sopra una soglia scelta come
prova che QuantLib fosse sbagliata.

Il problema:

- una simulazione MC ha errore campionario;
- la tolleranza deve dipendere da path, varianza e distribuzione;
- la correlazione richiede una misura appropriata, non un cutoff assoluto
  arbitrario;
- QMC va valutato anche per convergenza, non su un solo punto.

Il gate corretto usa:

- errore della media in standard error;
- errore della covarianza in standard error;
- correlazione tramite Fisher-z;
- convergenza QMC su 256/1.024/4.096 path.

Risultato MC a 8.192 path:

| Verifica | Errore massimo | Gate |
|---|---:|---:|
| Media | 0,935 SE | 4,5 SE |
| Covarianza | 1,695 SE | 4,5 SE |
| Correlazione Fisher-z | 1,523 SE | 4,5 SE |

QMC converge con slope negative:

- media `-0,648`;
- covarianza `-0,283`.

Quindi non esiste evidenza che il calcolo QuantLib fosse errato.

### 4.3 Il benchmark processi misurava il costo sbagliato

Il primo confronto penalizzava `spawn` soprattutto per:

- creazione processo;
- import librerie;
- startup runtime;
- comunicazione one-shot.

Questo non rappresentava il modello production richiesto. Il modello corretto è:

- worker lazy;
- worker persistente;
- richieste successive warm;
- pool separati;
- recycle solo su errore/timeout;
- cache parent prima dell'IPC.

Il benchmark production reale mostra:

| Dominio | 1 worker | 2 worker | Speedup warm | RSS 1→2 |
|---|---:|---:|---:|---:|
| Simulation | ~1,53 s | ~0,79 s | 1,938x | ~176→349 MB |
| Optimization | ~0,087 s | ~0,059 s | 1,477x | ~342→683 MB |

L'isolamento non è più un gate opzionale. P12 decide soltanto quanti worker usare.

### 4.4 Il problema Riskfolio era version-specifico

Il presunto vincolo era stato dedotto dalla closure di una versione più recente:

```text
Riskfolio 7.3
→ vectorbt
→ numba
→ vincolo incompatibile con NumPy 2.5.1
```

Questo non dimostrava che Riskfolio fosse inutilizzabile.

Riskfolio-Lib 7.0.1 è stata provata con:

- Python 3.13;
- NumPy 2.5.1;
- CVXPY;
- CLARABEL;
- SCS;
- nessun `vectorbt`;
- nessun `numba`.

Le capability richieste da P13 funzionano. Il problema è stato risolto scegliendo
la versione compatibile per capacità, non eliminando la libreria.

### 4.5 Costo del ritorno indietro

Il rollback non ha richiesto di rifare tutto il progetto risk.

**Rimasto valido**:

- G0-G4;
- contratti matematici;
- serie canoniche;
- rolling risk;
- analytics deterministici;
- registry/service/API bulk;
- metadata/qualità;
- cache content-keyed come principio.

**Rifatto o eliminato**:

- adapter simulation G5;
- RQMC;
- lock/thread execution;
- test simulation;
- probe adapter;
- benchmark P12;
- conclusioni P13;
- parte degli schema/client;
- documentazione G5.

**Aggiunto**:

- worker abstraction;
- pool simulation;
- pool optimization;
- QuantLib engine;
- Riskfolio engine;
- lifecycle/recycle;
- cancellation-safe in-flight deduplication;
- test worker;
- test optimization;
- benchmark production.

Non sono servite migrazioni DB né conversioni di dati.

---

## 5. Architettura backend attuale

### 5.1 Due binari funzionali

```text
Rolling asset-scoped
→ SignalPlugin
→ renderer segnali

Portfolio / broker / asset-set / multi-asset
→ RiskAnalytic
→ service bulk
→ API risk
→ renderer/widget frontend
```

### 5.2 Process boundary quantitativo

Due pool indipendenti:

```text
Simulation pool
→ QuantLib MC/QMC

Optimization pool
→ Riskfolio/CVXPY
```

Proprietà:

- start method `spawn`;
- lazy startup;
- worker persistenti;
- queue bounded;
- timeout hard;
- recycle della singola lane;
- shutdown FastAPI idempotente;
- input/output serializzabili;
- nessun oggetto di libreria attraversa il boundary;
- nessun fallback silenzioso.

Il request channel usa una `multiprocessing.Queue`; il response channel una pipe
one-way.

### 5.3 Cache e concorrenza async

La cache:

- usa chiavi content-based;
- include scope, date, currency, fingerprint dati, parametri, algoritmo e seed;
- non richiede invalidazione manuale backend;
- collassa richieste identiche concorrenti;
- usa `asyncio.shield` per impedire a un follower cancellato di cancellare il
  future condiviso;
- risolve/cancella esplicitamente il future se il leader viene cancellato;
- memorizza solo risultati riusciti.

### 5.4 QuantLib P11

MC:

```text
UniformRandomGenerator
→ Gaussian sequence
→ GaussianMultiPathGenerator
→ StochasticProcessArray
```

QMC:

```text
SobolRsg.skipTo(seed)
→ InvCumulativeSobolGaussianRsg
→ StochasticProcessArray.evolve
```

Contratto:

- GBM correlato multi-asset;
- `dt=1/365`;
- stato iniziale normalizzato a `1`;
- seed deterministico;
- seed QMC = indice iniziale Sobol;
- path QMC in potenza di due;
- dimensione Sobol `asset × horizon_days <= 21.201`;
- output percentili, distribuzione e probability of loss.

### 5.5 Riskfolio P13

Nuovo analytic: `portfolio_optimization`.

Scope:

- portfolio;
- broker;
- asset-set.

Strategie:

- minimum variance;
- maximum Sharpe stimato nel campione;
- equal risk contribution/risk parity.

Estimatori:

- historical covariance;
- Ledoit-Wolf;
- OAS.

Vincoli:

- long-only;
- fully invested;
- no leverage;
- bound globali validati;
- errore esplicito se infeasible.

Output:

- pesi;
- rendimento e volatilità;
- Sharpe;
- contributi al rischio;
- solver/status;
- constraint summary;
- frontier opzionale;
- sensitivity opzionale;
- warning e metadata.

Minimo production: 30 osservazioni allineate.

---

## 6. Stato P0-P13

| Step | Obiettivo | Stato backend | Stato frontend |
|---|---|---|---|
| P0 | Probe/install QuantLib + Riskfolio | ✅ | N/A |
| P1 | Serie canoniche asset/portfolio | ✅ | Consumo indiretto |
| P2 | Data quality + metadata | ✅ | 🟡 Render parziale presente |
| P3 | Rolling risk plugins | ✅ | ✅ Integrati nel renderer segnali |
| P4 | Asset Detail rolling risk | ✅ backend | ✅ UI rolling esistente |
| P5 | Contratto `RiskAnalytic` | ✅ | Store/client presente |
| P6 | Correlation | ✅ | 🟡 Heatmap e route wiring presenti, non ricertificati G6 |
| P7 | KPI + PCTR | ✅ | 🟡 Componenti presenti, non ricertificati G6 |
| P8 | Stress | ✅ | 🟡 Controlli/output presenti, non ricertificati G6 |
| P9 | Comparison | ✅ | 🟡 Controlli/output presenti, non ricertificati G6 |
| P10 | VaR/CVaR | ✅ | 🟡 Render presente, non ricertificato G6 |
| P11 | MC/QMC QuantLib | ✅ | 🟡 Controlli MC/QMC presenti, non ricertificati dopo G5 |
| P12 | Spawn/scale benchmark | ✅ | Nessuna UI specifica |
| P13 | Riskfolio optimization/frontier | ✅ | ❌ Assente |

---

## 7. Stato reale del frontend

### 7.1 Discrepanza piano vs worktree

Il sub-plan Step 6 è ancora marcato **“NON INIZIATO”**, ma questo non descrive
correttamente la worktree.

Esistono:

- `riskStore.svelte.ts`;
- `RiskAnalysisPanel.svelte`;
- `RiskResultFrame.svelte`;
- `CorrelationHeatmap.svelte`;
- `AssetSetRiskPanel.svelte`;
- `riskTypes.ts`;
- test unit del risk store;
- E2E funzionale `portfolio/risk-analysis.spec.ts`;
- wiring su:
  - Asset list / Asset Global;
  - Asset Detail;
  - Broker Detail;
  - Dashboard.

Questi file sono stati materializzati prima della correzione finale del backend.
Non sono stati rimossi perché contengono lavoro utile e il contratto MC/QMC finale
è compatibile con gran parte del wiring.

### 7.2 Cosa supporta già

Il pannello corrente contiene capability gating per:

- KPI;
- correlation;
- risk contribution;
- historical VaR/CVaR;
- comparison;
- stress;
- simulation MC/QMC;
- quality summary;
- `DataQualityBanner`;
- `PageSyncModal`;
- refresh e invalidazione store;
- quattro scope.

Il risk store:

- usa request key canoniche;
- separa cache per client-session user;
- deduplica richieste in-flight;
- invalida su reset sessione e mutazioni portfolio.

L'E2E:

- è registrato nel test runner;
- usa risposte API mock;
- verifica superfici e stati funzionali;
- non prova la matematica, correttamente delegata al backend.

### 7.3 Cosa manca o va ricontrollato

- nessun supporto UI per `portfolio_optimization`;
- nessuna frontier/sensitivity UI;
- catalog mock E2E non include P13;
- G6 non è stato ricertificato contro l'OpenAPI finale corretto;
- non è stata eseguita una chiusura integrata reale con QuantLib/Riskfolio worker;
- il sub-plan Step 6 e i file reali sono fuori sync;
- design, layout finale, fillings e polish restano intenzionalmente all'utente.

Quindi lo stato corretto non è “G6 mai toccato”, ma:

> **G6 parzialmente materializzato, non formalmente riallineato, verificato e
> chiuso dopo la correzione G5.**

---

## 8. Evidenze e validazione attuali

### 8.1 Test

- risk service suite: **68 passed**;
- risk API: **7 passed**;
- worker lifecycle: **6 passed**;
- nessun resource-tracker warning dopo la correzione pipe;
- probe QuantLib: `status=ok`;
- benchmark pool: `status=ok`;
- Ruff/Black target: verdi;
- `pipenv verify`: verde;
- API sync: idempotente;
- frontend check/build di compatibilità: verdi;
- Docker build/smoke: verde.

### 8.2 Suite globale

Il runner backend globale ha:

- superato external;
- superato DB;
- superato 56/57 service action;
- eseguito 633 test AI Export prima di un solo failure su
  `TargetCoverage.volume_analyzed`.

Il failure:

- è concorrente;
- è estraneo al risk backend;
- non è stato modificato in questa attività;
- impedisce a quella specifica invocazione di proseguire verso tutte le categorie
  successive.

### 8.3 Docker

- immagine: `librefolio:g5-quantlib-riskfolio-final`;
- digest:
  `sha256:fd8d79d6584dd7cf8087f54508f8c73cc66bbcacebe5a206bf46821117bd7999`;
- dimensione non compressa: `2.756.004.428` byte;
- import smoke: FastAPI + QuantLib + NumPy + Riskfolio verdi.

---

## 9. Cosa è stato completato

### Backend

- P0-P13 backend;
- contratti matematici e serializzabili;
- serie, qualità e metadata;
- rolling risk;
- analytics deterministici;
- simulation QuantLib;
- optimization Riskfolio;
- worker architecture;
- cache e cancellation safety;
- API/client;
- test e benchmark;
- lock e Docker;
- documentazione operativa;
- recap;
- devWiki e knowledge graph.

### Frontend già presente

- rolling risk Asset Detail;
- risk store;
- componenti shared;
- correlation heatmap;
- quattro route collegate;
- render KPI/PCTR/stress/comparison/VaR/simulation;
- quality/sync;
- test unit store;
- E2E funzionale mock.

Quest'ultimo blocco non equivale a G6 chiuso.

---

## 10. Cosa non è stato completato

1. Chiusura formale G6.
2. Riallineamento del sub-plan Step 6 allo stato reale.
3. UI P13 `portfolio_optimization`.
4. Frontier e sensitivity UI.
5. E2E funzionale P13.
6. Test integrato UI ↔ worker reale QuantLib/Riskfolio.
7. Chiusura GF completa.
8. Riesecuzione dell'intero runner backend oltre il failure AI Export concorrente.
9. Review visuale finale desktop/mobile.
10. Fillings, polish, gallery e design finale.

---

## 11. Cosa è stato rimandato intenzionalmente

| Elemento | Motivo |
|---|---|
| G6 finale | L'utente ha chiesto stop alla chiusura backend. |
| UI P13/frontiera | Backend prima; richiede decisione UX separata. |
| Worker default >1 | Speedup esiste, ma il costo RAM è quasi lineare; resta configurabile. |
| Tuning bridge SWIG/path copy | Non blocca correttezza o adozione; ottimizzazione futura misurabile. |
| Factor shock | Manca un factor-exposure model. |
| Total-return per asset | Le serie correnti sono price-only; va progettato separatamente. |
| Design/fillings | Esplicitamente riservati all'utente. |
| Full-suite finale | Bloccata dal failure AI Export concorrente. |

---

## 12. Cosa non serve più o è stato eliminato

### Eliminato dal production path

- `NumpyScipySimulationAdapter`;
- SciPy Sobol/`ndtri` come engine production;
- RQMC;
- lock QuantLib in-process;
- `asyncio.to_thread` come boundary quantitativo;
- fallback silenzioso QuantLib → NumPy;
- conclusione “Riskfolio respinto”.

### Riconosciuto come non necessario

- nuovo sistema di invalidazione cache;
- persistenza DB dei risultati risk;
- migrazione DB;
- fattore fisso 252 o 365;
- forward-fill dei rendimenti;
- benchmark sintetico per il beta;
- processo nuovo per ogni richiesta;
- pool unico condiviso fra simulation e optimization;
- QMCPy;
- risparmio di spazio come criterio per respingere una dipendenza necessaria;
- P12 come scelta “processo sì/no”: decide solo il numero di worker.

---

## 13. Problemi inattesi affrontati

| Problema | Impatto | Soluzione |
|---|---|---|
| Benchmark QuantLib/NumPy non equivalente | Scelta production errata | Oracle analitici e stage timing. |
| Gate correlazione arbitrario | QuantLib giudicata erroneamente | Standard error + Fisher-z + convergenza QMC. |
| Seed constructor Sobol non spostava lo stream come richiesto | Semantica seed ambigua | `SobolRsg.skipTo(seed)`. |
| Riskfolio 7.3 trascinava vectorbt/numba | Falso conflitto globale | Riskfolio-Lib 7.0.1 capability-tested. |
| Primo lock includeva upgrade wildcard non correlati | Diff dipendenze troppo ampio | Ricostruita closure minima; successivo update utente preservato. |
| Follower cancellato poteva cancellare il future condiviso | Richieste concorrenti fragili | `asyncio.shield`. |
| Leader cancellato poteva lasciare follower sospesi | Deadlock logico | Cancellazione/risoluzione esplicita del future. |
| Response `multiprocessing.Queue` lasciava semaphore dopo crash | Resource warning | Pipe one-way per la risposta. |
| Docstring con backtick rompeva il TypeScript generato | `api sync` non compilabile | Testo schema corretto senza cambiare contratto. |
| DB test trovato vuoto durante attività concorrente | Verifica reale impossibile | Ripopolamento con fixture standard. |
| Fixture reale P13 con sole 13 osservazioni | Optimization unavailable | Risposta corretta `insufficient_history`; successo provato con fixture sintetica ≥30. |
| Limite dimensione Sobol | Alcune matrici P12 non eseguibili | Classificazione esplicita `dimension_limit`. |
| Celle benchmark oltre budget risorse | Rischio OOM/tempi eccessivi | Classificazione `resource_limit`, non fallback. |
| Failure AI Export nella suite globale | GF non chiudibile | Registrato come estraneo; nessuna modifica fuori scope. |
| Worktree condivisa con modifiche concorrenti | Rischio rollback involontario | Nessun revert ampio; modifiche utente preservate. |
| Piano G6 fuori sync con file reali | Handoff ambiguo | Evidenziato in questo report; va riconciliato prima di proseguire. |

---

## 14. Decisioni ormai consolidate

Queste decisioni non dovrebbero essere riaperte senza nuova evidenza tecnica:

1. Backend calcola; frontend presenta.
2. Rolling risk → `SignalPlugin`.
3. Multi-asset risk → `RiskAnalytic`.
4. QuantLib è l'engine production MC/QMC.
5. Riskfolio-Lib 7.0.1 è l'engine production P13.
6. Process isolation `spawn` sempre attivo.
7. Simulation e optimization hanno pool separati.
8. Nessun fallback silenzioso.
9. NumPy resta algebra/aggregazione/oracle.
10. RQMC resta rimosso.
11. QMC seed = Sobol start index tramite `skipTo`.
12. Calcolo giornaliero e annualizzazione osservata.
13. Cache content-keyed, nessuna invalidazione backend manuale.
14. Nessuna persistenza DB dei risultati.
15. Nessun calcolo finanziario TypeScript.

---

## 15. Decisioni ancora aperte per l'agente di alto livello

### Priorità 1 — Come trattare G6 già parzialmente scritto

Scegliere fra:

1. **Reconciliation-first** — audit dei file esistenti, aggiornamento Step 6,
   rimozione drift, poi completamento.
2. **Hard reset logico** — mantenere solo primitive valide e ricostruire il wiring
   G6 secondo il piano finale.
3. **Minimal close** — verificare il wiring presente, aggiungere solo P13 e test
   mancanti.

Raccomandazione: **reconciliation-first**. Il lavoro esistente è sostanziale e
coerente con i contratti backend, ma non va dichiarato completato senza audit.

### Priorità 2 — Scope UI P13

Decidere se G6 deve includere:

- solo pesi ottimali + summary;
- anche risk contribution;
- anche frontier;
- anche sensitivity;
- selezione strategia/estimator/solver;
- oppure P13 UI in una fase separata.

### Priorità 3 — Tipo di test integrato

Decidere se è sufficiente:

- E2E mock per comportamento UI;
- più un singolo smoke reale con backend worker;
- oppure un E2E completo su fixture ≥30 osservazioni.

### Priorità 4 — Profilo worker production

Il codice supporta più worker, ma il default è 1 per pool.

Da decidere:

- lasciare solo configurazione manuale;
- introdurre preset per RAM disponibile;
- documentare sizing per deployment;
- rinviare tuning fino a workload reali.

### Priorità 5 — Chiusura GF e failure concorrente

Decidere se:

- attendere la stabilizzazione AI Export;
- correggere prima quel failure in task separato;
- eseguire GF con eccezione documentata;
- ripetere il runner globale su una worktree non concorrente.

---

## 16. Proposta di prossimo incarico

Il prossimo incarico più sicuro è:

```text
Eseguire un audit di riconciliazione G6 senza redesign:

1. confrontare Step 6 con i file frontend risk già presenti;
2. aggiornare lo stato del piano task-per-task;
3. verificare il client contro l'OpenAPI finale G5;
4. mantenere solo MC/QMC;
5. progettare esplicitamente la UI P13 oppure rinviarla;
6. eseguire test unit, check/build ed E2E funzionali;
7. non modificare fillings/design oltre il minimo funzionale;
8. fermarsi prima del polish e produrre un nuovo report di chiusura G6.
```

---

## 17. File chiave

### Stato e piani

- `_RECAP-and-implementation-reading-guide.md`;
- `plan-phase01RiskAnalysisImplementation.prompt.md`;
- `plan-phase01Step5SimulationScaleOptimization.prompt.md`;
- `plan-phase01Step6RiskFrontendIntegration.prompt.md`;
- `benchmark-phase01SimulationScale.md`;
- `spike-phase01SimulationAdapters.md`;
- `spike-phase01QuantLibraries.md`.

### Backend

- `backend/app/services/risk/`;
- `backend/app/services/risk/quant/spawn_worker.py`;
- `backend/app/services/risk/quant/quantlib_worker.py`;
- `backend/app/services/risk/quant/riskfolio_worker.py`;
- `backend/app/services/risk/quant/engine.py`;
- `backend/app/services/risk/quant/optimization_engine.py`;
- `backend/app/services/risk_plugins/simulation.py`;
- `backend/app/services/risk_plugins/portfolio_optimization.py`;
- `backend/app/schemas/risk.py`;
- `backend/app/api/v1/risk.py`.

### Frontend già presente

- `frontend/src/lib/stores/risk/riskStore.svelte.ts`;
- `frontend/src/lib/components/risk/RiskAnalysisPanel.svelte`;
- `frontend/src/lib/components/risk/AssetSetRiskPanel.svelte`;
- `frontend/src/lib/components/risk/CorrelationHeatmap.svelte`;
- `frontend/src/lib/components/risk/RiskResultFrame.svelte`;
- `frontend/src/lib/risk/riskTypes.ts`;
- `frontend/e2e/portfolio/risk-analysis.spec.ts`.

### Test backend

- `backend/test_scripts/test_services/test_risk_analytics.py`;
- `backend/test_scripts/test_services/test_risk_simulation.py`;
- `backend/test_scripts/test_services/test_risk_optimization.py`;
- `backend/test_scripts/test_services/test_risk_spawn_worker.py`;
- `backend/test_scripts/test_api/test_risk_api.py`.

---

## 18. Prompt copiabile per l'agente di alto livello

```text
Analizza lo stato della Risk Analysis LibreFolio usando come fonte primaria:
report-phase01RiskAnalysisCurrentStateAndHandoff.md.

Obiettivo: decidere il prossimo incarico senza riaprire le decisioni backend già
corrette.

Punti da valutare:
1. il backend G0-G5 è chiuso con QuantLib MC/QMC e Riskfolio 7.0.1 in pool spawn;
2. la prima pista NumPy/thread/Riskfolio-respinto è superseded;
3. G6 è marcato non iniziato, ma la worktree contiene un wiring UI sostanziale;
4. la UI non include P13 optimization/frontier;
5. serve scegliere fra reconciliation-first, minimal close o ricostruzione G6;
6. design/fillings restano fuori scope;
7. la suite globale ha un failure AI Export concorrente estraneo al risk.

Produci:
- valutazione delle scelte attuali;
- rischi tecnici residui;
- cosa tenere/rifare/rimuovere nel frontend;
- scope preciso del prossimo task;
- criteri di accettazione e ordine di esecuzione.
```

---

## 19. Stato finale in una frase

> **Backend risk completo e corretto; falsa pista NumPy/thread rimossa; QuantLib e
> Riskfolio operative in processi isolati; frontend già parzialmente materializzato
> ma non riallineato né chiuso, P13 UI assente, GF ancora da eseguire.**
