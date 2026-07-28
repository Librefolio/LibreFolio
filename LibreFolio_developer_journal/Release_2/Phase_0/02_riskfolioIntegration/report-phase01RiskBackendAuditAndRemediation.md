# Audit backend e piano di rimedio — Risk Analysis G0-G5

> **Data audit:** 2026-07-28
> **Stato:** ✅ remediation implementata e verificata; G6 solo ripianificato
> **Ambito:** backend G0-G5, compatibilità frontend strettamente necessaria, replan G6
> **Fuori ambito:** redesign UI, implementazione completa G6, chiusura GF

---

## 1. Esito sintetico

Il backend Risk Analysis realizzato finora è sostanzialmente corretto:

- G0-G4 non richiedono riscritture;
- G5 usa realmente QuantLib e Riskfolio-Lib in processi `spawn`;
- gli oracle matematici e i test Risk mirati sono verdi;
- non esiste un adapter production NumPy/SciPy concorrente;
- non esiste RQMC nel runtime;
- la cache è content-keyed e separata per simulation/optimization.

L'audit ha però trovato due debiti reali e circoscritti:

1. `seed` ha due significati diversi:
   - MC: seed pseudo-casuale;
   - QMC: indice iniziale della sequenza Sobol passato a `skipTo`.
2. I worker sono lazy ma, dopo il primo job, restano residenti fino allo shutdown
   FastAPI. Manca un idle timeout distinto per simulation e optimization.

La remediation approvata non cambia motori, matematica o architettura:

- contratto esplicito `sampling_method`, `path_count`, `random_seed`,
  `sobol_start_index`;
- compatibilità temporanea in input per `sampling`, `paths`, `seed`;
- metadata e cache key normalizzati sui nuovi campi;
- idle reap sicuro dei processi, seguito da restart lazy;
- test di lifecycle, concorrenza, cancellazione e cleanup;
- nessun upgrade a Riskfolio-Lib 7.3.0;
- nessun refactor delle pipeline matematiche già corrette.

---

## 2. Baseline verificata

| Verifica | Esito |
|---|---:|
| `./dev.py test services risk-all` | 68 passed |
| `./dev.py test api risk` dopo popolamento DB test | 7 passed |
| QuantLib production | confermato |
| Riskfolio-Lib production | confermato, versione 7.0.1 |
| Process isolation | confermato, start method `spawn` |
| Pool separati | confermato, simulation e optimization |
| Cache separate | confermato |
| RQMC runtime | assente |

Il primo run API aveva 2 failure perché il DB test non era popolato. Dopo
`./dev.py test db populate --force`, la stessa suite è passata integralmente.
Non era un difetto del backend Risk.

---

## 3. Classificazione G0-G5

| Gate | Stato audit | Decisione |
|---|---|---|
| G0 — dipendenze quantitative | **confermato con pin** | mantenere QuantLib 1.43 e Riskfolio-Lib 7.0.1 |
| G1 — fondazione quant | **confermato** | nessuna modifica matematica |
| G2 — serie canoniche | **confermato** | nessuna fusione con la pipeline Signal |
| G3 — rolling risk | **confermato** | nessun fix richiesto |
| G4 — multi-asset deterministico | **confermato** | nessun fix richiesto |
| G5 — stochastic/scale/optimization | **corretto con debito lifecycle/contract** | fix naming QMC + idle timeout |

G5 non viene riaperto per cambiare engine. Viene riaperto solo per eliminare
ambiguità di contratto e processi residenti senza limite temporale.

---

## 4. QuantLib simulation: evidenza e decisione

### 4.1 Stato reale

Il runtime production:

- importa QuantLib solo nel child worker;
- usa generatori QuantLib per MC e Sobol QMC;
- evolve il processo GBM tramite primitive QuantLib;
- usa NumPy solo per algebra, aggregazione e statistiche successive;
- non esegue il calcolo nativo nel processo web;
- non possiede più un adapter NumPy/SciPy alternativo.

### 4.2 Matematica

I test confrontano i log-return terminali con:

```text
E[Y_i] = (mu_i - 0.5 * Sigma_ii) * T
Cov(Y_i, Y_j) = Sigma_ij * T
```

Le tolleranze MC derivano da standard error e Fisher transform; QMC viene
controllato su potenze di due e convergenza normalizzata. Non resta il vecchio
gate arbitrario usato nella falsa pista iniziale.

### 4.3 Problema residuo

Il campo `seed` è semanticamente sovraccarico:

- MC: inizializza il generatore pseudo-random;
- QMC: viene passato a `SobolRsg.skipTo`, quindi identifica il primo punto Sobol.

Il calcolo è corretto, ma il nome induce un contratto falso.

### 4.4 Contratto corretto

Nuovi nomi canonici:

| Campo | Significato |
|---|---|
| `sampling_method` | `mc` oppure `qmc` |
| `path_count` | numero di traiettorie |
| `random_seed` | seed MC; valido solo per `mc` |
| `sobol_start_index` | primo indice Sobol; valido solo per `qmc` |

Regole:

- MC rifiuta `sobol_start_index`;
- QMC rifiuta `random_seed`;
- QMC mantiene il vincolo power-of-two su `path_count`;
- QMC mantiene `asset_count * horizon_days <= 21_201`;
- nessun fallback automatico da QMC a MC;
- cache key e metadata usano solo i campi canonici.

### 4.5 Compatibilità

Poiché Risk Analysis non è ancora una superficie rilasciata, output e metadata
vengono migrati direttamente ai nomi corretti. Per non rompere richieste già
scritte durante lo sviluppo, il backend accetta temporaneamente:

```text
sampling -> sampling_method
paths    -> path_count
seed     -> random_seed (MC)
seed     -> sobol_start_index (QMC)
```

Le chiavi legacy:

- non vengono riemesse;
- non entrano nella cache key;
- non vengono pubblicizzate nel catalogo;
- saranno documentate come deprecate e rimovibili prima del rilascio.

### 4.6 Non sovrapposizione Sobol

Oggi una simulazione è un singolo job assegnato a una sola lane: non esiste
chunking del medesimo campione tra worker. Di conseguenza:

- l'intervallo usato è
  `[sobol_start_index, sobol_start_index + path_count)`;
- non può esserci overlap interno tra chunk, perché non esistono chunk;
- due richieste identiche condividono cache/dedup;
- due richieste esplicitamente impostate sullo stesso indice producono
  intenzionalmente la stessa sequenza deterministica.

Se in futuro una simulazione verrà partizionata, ogni chunk dovrà ricevere un
offset disgiunto calcolato dal parent; non è corretto farlo implicitamente oggi.

---

## 5. Worker lifecycle

### 5.1 Classificazione corrente

Il lifecycle attuale è **B — lazy persistent until application shutdown**:

1. nessun processo all'avvio;
2. la prima richiesta avvia la lane;
3. richieste successive riusano il processo warm;
4. timeout, crash ed errore remoto riciclano la lane coinvolta;
5. lo shutdown FastAPI chiude entrambi i pool;
6. in assenza di errori, una lane inattiva resta residente indefinitamente.

### 5.2 Proprietà già corrette

- `spawn`, non `fork`;
- code bounded e backpressure;
- timeout hard;
- cancellazione senza riuso prematuro della lane;
- isolamento dei failure domain;
- shutdown idempotente;
- pool simulation e optimization distinti.

### 5.3 Fix approvato

Aggiungere:

```text
RISK_SIMULATION_IDLE_TIMEOUT_SECONDS
RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS
```

Default iniziale: **600 secondi per entrambi**, configurabili separatamente.

Il valore è conservativo: i benchmark mostrano cold start significativo,
soprattutto per Riskfolio, quindi non conviene distruggere processi tra richieste
ravvicinate. Il benchmark aggiornato misurerà nuovamente:

- cold request;
- warm reuse;
- RSS prima/dopo idle reap;
- restart dopo idle;
- cicli reap/restart ripetuti.

Il default potrà essere separato in seguito sulla base delle nuove misure senza
cambiare il contratto.

### 5.4 Invarianti di sicurezza

Il reaper:

- parte solo quando `_pending == 0`;
- viene invalidato appena una richiesta viene accettata;
- non chiude lane con job queued o in-flight;
- non marca il pool come definitivamente chiuso;
- usa lo stesso `lane.stop()` già testato per timeout/shutdown;
- consente alla richiesta successiva di riavviare lazy la lane;
- non altera timeout, queue capacity o worker count.

Test obbligatori:

1. idle reap dopo ultimo job;
2. nessun reap con job in-flight;
3. restart lazy con PID nuovo;
4. worker count >1;
5. cicli ripetuti senza processi orfani;
6. shutdown durante timer idle;
7. cancellazione e timeout invariati.

---

## 6. Riskfolio-Lib 7.0.1 vs 7.3.0

### 6.1 Versione production confermata

`riskfolio-lib==7.0.1` è stata verificata con:

- Python 3.13.14;
- NumPy 2.5.1;
- assenza di vectorbt e Numba;
- solver open-source;
- minimum risk;
- maximum Sharpe;
- risk parity;
- covariance historical/Ledoit-Wolf/OAS;
- frontiera;
- vincoli e infeasible handling;
- Docker arm64 e amd64.

Il worker possiede già una runtime guard sulla versione.

### 6.2 Probe pulito 7.3.0

Con NumPy 2.5.1, Riskfolio-Lib 7.3.0 non è compatibile nel grafo corrente:

```text
riskfolio-lib 7.3.0
  -> vectorbt >= 0.28.0
  -> numba >= 0.66
  -> numpy < 2.5
```

Esiti del probe:

| Probe | Esito |
|---|---:|
| pip con NumPy 2.5.1 pin | fallito |
| Pipenv lock con NumPy 2.5.1 | fallito |
| Docker Python 3.13 con NumPy 2.5.1 | fallito |
| installazione senza pin NumPy | possibile solo degradando a NumPy 2.4.6 |

7.3.0 aggiunge inoltre vectorbt, relativo peso transitivo e licenza Commons
Clause. Non è stata modificata la dependency production.

### 6.3 Decisione

Mantenere il pin esatto:

```text
riskfolio-lib==7.0.1
```

Non è un risparmio di spazio: è la versione più recente che soddisfa
contemporaneamente i requisiti reali del prodotto senza downgrade NumPy né nuova
dipendenza vectorbt.

Nuovo confronto richiesto prima di:

- cambiare Riskfolio;
- degradare NumPy;
- accettare vectorbt/Numba;
- cambiare solver o vincoli P13.

Artefatti del probe:

- `/tmp/libreFolio_riskfolio730_pinned_install_20260728.log`
- `/tmp/libreFolio_riskfolio730_pipenv_lock_20260728.log`
- `/tmp/libreFolio_riskfolio730_docker_build_20260728.log`
- `/tmp/libreFolio_riskfolio730_probe_result_20260728.txt`

---

## 7. Audit anti-duplicazione

Nessuna duplicazione urgente giustifica un refactor.

### 7.1 Series preparation

Risk e Signal condividono primitive, ma hanno orchestrazioni e contratti diversi.
Fonderle ora aumenterebbe il coupling e il rischio di regressione senza eliminare
un'unica fonte di verità matematica.

### 7.2 Matematica

Le formule Risk sono già centralizzate in `risk/metrics.py`. I punti delicati sono
coperti meglio con test di confine che con una nuova astrazione.

### 7.3 Cache

Simulation e optimization hanno cache analoghe ma intenzionalmente separate:

- payload diversi;
- failure domain diversi;
- dipendenze native diverse;
- invalidazione/versionamento diversi.

Non vengono unificate.

---

## 8. Frontend G6: stato rilevato, non implementato

| Capability | Stato reale |
|---|---|
| Asset Global correlation | presente e montata correttamente |
| Dashboard Risk | presente |
| Broker Risk | presente |
| KPI/PCTR/stress/comparison/VaR/MC-QMC | presenti |
| Asset Detail | presente ma montato fuori dalla tab approvata |
| Optimization P13 UI | assente |
| Selector comparison condiviso | già corretto |
| Fallback `#assetId` | ancora presenti |

In questa remediation il frontend cambia solo quanto necessario per compilare e
inviare il nuovo contratto simulation. Non vengono implementati:

- tab Asset Detail “Risk & Scenarios”;
- renderer optimization/frontier;
- rifiniture visuali;
- rimozione completa dei fallback ID.

Questi elementi restano nel replan G6.

---

## 9. RQMC

RQMC non è presente nel runtime, nell'OpenAPI o nel selettore frontend.

Resta una possibile estensione futura a priorità bassa, subordinata a:

- definizione esplicita dello scrambling;
- seed separato dallo start index Sobol;
- repliche indipendenti;
- oracle e benchmark dedicati;
- supporto verificato del binding QuantLib o adapter approvato.

La voce è stata aggiunta a `Release_2/todo_futuri.md`; nessun codice RQMC è stato
reintrodotto.

---

## 10. Fix approvati

1. Rinominare il contratto simulation:
   `sampling_method`, `path_count`, `random_seed`, `sobol_start_index`.
2. Accettare temporaneamente input legacy e normalizzarlo prima di cache/metadata.
3. Migrare output, metadata, test, benchmark, client e UI minima ai nuovi nomi.
4. Aggiungere idle timeout distinti per i due pool.
5. Aggiungere test lifecycle/resource cleanup.
6. Estendere benchmark con reap/restart.
7. Integrare nel journal il probe Riskfolio 7.3.0.
8. Aggiornare Step 5 e riscrivere Step 6 secondo lo stato reale.
9. Aggiungere RQMC ai todo futuri.

---

## 11. Fix respinti o rimandati

| Proposta | Decisione | Motivo |
|---|---|---|
| Upgrade Riskfolio 7.3.0 | respinto | incompatibile con NumPy 2.5.1 |
| Downgrade NumPy | respinto | nessun beneficio che giustifichi la regressione |
| Reintroduzione NumPy/SciPy production | respinta | QuantLib production è corretto |
| Chunking QMC automatico | rimandato | oggi ogni simulazione è un job indivisibile |
| Worker sizing automatico CPU/RAM | rimandato | nessun modello affidabile per job eterogenei |
| Fusione cache simulation/optimization | respinta | failure domain distinti |
| Fusione pipeline Risk/Signal | respinta | semantiche diverse |
| Implementazione G6/P13 UI | fuori ambito | richiede fase frontend dedicata |
| Chiusura GF | vietata ora | mancano G6, smoke reali e suite globale stabile |

---

## 12. Ordine di implementazione

```text
decision report
  -> simulation contract + metadata + cache
  -> idle timeout + lifecycle tests
  -> backend/API tests
  -> API sync + frontend compatibility
  -> benchmark idle/restart
  -> dependency/Docker checks
  -> journal + Step 6 replan
  -> handoff finale
```

---

## 13. Rollback

La remediation non tocca DB, dati o migrazioni.

Rollback contract:

- ripristinare i vecchi nomi nei DTO/plugin/frontend;
- nessuna cache persistente da migrare;
- nessun dato utente da convertire.

Rollback lifecycle:

- impostare idle timeout a `0` per disabilitare il reap;
- oppure rimuovere il timer mantenendo invariati lane/pool esistenti.

Rollback dependency:

- nessun cambio production previsto;
- Pipfile e lock devono restare su Riskfolio 7.0.1 e QuantLib 1.43.

---

## 14. Criteri di uscita

La remediation è completa solo se:

- MC espone solo `random_seed`;
- QMC espone solo `sobol_start_index`;
- output e metadata dichiarano `sampling_method` e `path_count`;
- input legacy viene accettato e normalizzato;
- cache equivalenti legacy/canoniche producono la stessa key;
- idle reap non può interrompere job queued/in-flight;
- restart lazy usa PID nuovo;
- nessun processo resta dopo shutdown;
- test Risk service/API/schema sono verdi;
- client OpenAPI e frontend compilano;
- benchmark registra cold/warm/reap/restart/RSS;
- Riskfolio resta 7.0.1 con NumPy 2.5.1;
- Step 6 descrive il gap reale senza dichiarare G6 completato;
- GF resta aperta.

---

## 15. Esito implementativo finale

### 15.1 Contratto simulation

La remediation è stata applicata integralmente:

- `SimulationEngineRequest` usa `sampling_method`, `path_count`, `random_seed`,
  `sobol_start_index`;
- MC richiede solo `random_seed`;
- QMC richiede solo `sobol_start_index`;
- `sobol_start_index` viene passato a `QuantLib.SobolRsg.skipTo`;
- il plugin accetta temporaneamente `sampling`, `paths`, `seed` solo in ingresso;
- cache key, metadata, output e OpenAPI usano esclusivamente i nomi canonici;
- algorithm version simulation: `2.1.0-quantlib-1.43`;
- richieste identiche condividono cache/dedup;
- non esiste chunking interno: un job QMC consuma
  `[sobol_start_index, sobol_start_index + path_count)`.

File principali:

- `backend/app/services/risk/quant/models.py`
- `backend/app/services/risk/quant/quantlib_worker.py`
- `backend/app/services/risk_plugins/simulation.py`
- `backend/app/schemas/risk.py`
- `backend/app/services/risk/service.py`

### 15.2 Lifecycle worker

Configurazione aggiunta:

```text
RISK_SIMULATION_IDLE_TIMEOUT_SECONDS=600
RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS=600
```

Il reaper:

- opera solo con `_pending == 0`;
- non interrompe job queued/in-flight;
- usa un generation token per invalidare timer obsoleti;
- chiude tutte le lane del pool;
- non marca il pool come definitivamente chiuso;
- permette restart lazy con PID nuovo;
- viene disabilitato con timeout `0`;
- viene cancellato dallo shutdown idempotente.

Copertura aggiunta:

- idle reap/restart;
- queue e in-flight safety;
- tre cicli reap/restart;
- shutdown durante timer;
- pool a due lane;
- timeout/crash/cancellation invariati.

### 15.3 Frontend minimo, senza avvio G6

Sono state fatte soltanto le modifiche necessarie alla compatibilità:

- payload simulation canonico;
- controlli distinti Random seed MC / Sobol start index QMC;
- metadata/output aggiornati;
- traduzioni EN/IT/FR/ES;
- mock E2E aggiornato;
- client OpenAPI rigenerato.

Non sono stati implementati placement Asset Detail, rimozione completa fallback id,
P13 UI o smoke reali. Queste attività sono ora dettagliate in
[`plan-phase01Step6RiskFrontendIntegration.prompt.md`](./plan-phase01Step6RiskFrontendIntegration.prompt.md).

### 15.4 Evidenze

| Gate | Esito |
|---|---:|
| Risk service suite | **74 passed** |
| Risk API | **7 passed** |
| Risk schema subset | **21 passed** |
| Ruff/Black mirati | verde |
| frontend format/check/build | verde, 0 errori/warning |
| Risk E2E desktop mocked | **5 passed** |
| QuantLib oracle probe | `status=ok` |
| worker benchmark | `status=ok` |
| `pipenv verify` | lock up-to-date |
| runtime host | NumPy 2.5.1 / QuantLib 1.43 / Riskfolio 7.0.1 |
| dependency graph | vectorbt e Numba assenti |
| Docker finale arm64 | build + import smoke verdi |

Immagine finale:

- tag: `librefolio:risk-audit-remediation`;
- digest:
  `sha256:98a2cea750af424ffabf7b9ed01beba0afe329fde445e9d85a240f2d492194ac`;
- architettura: arm64;
- dimensione: `2.781.625.742 B`;
- import smoke: NumPy 2.5.1, QuantLib 1.43, Riskfolio 7.0.1.

### 15.5 Benchmark remediation

| Pool | Cold | Warm | RSS | Reap | Restart cold |
|---|---:|---:|---:|---:|---:|
| Simulation | `1,067 s` | `0,002722 s` | `171,3 MB` | `0,416 s` | `1,197 s` |
| Optimization | `3,075 s` | `0,016835 s` | `340,4 MB` | `0,645 s` | `2,961 s` |

Entrambi i restart usano PID nuovi. Il run remediation a una ripetizione misura
speedup 2-worker `2,144x` simulation e `2,471x` optimization; il run principale a
due ripetizioni resta la base più robusta per mantenere default un worker per pool.

### 15.6 Problemi inattesi

1. Il primo rerun Risk API ha fallito due test perché il DB test era stato modificato
   da lavoro concorrente. Dopo `./dev.py test db populate --force`, gli stessi sette
   test sono passati.
2. Il probe pulito Riskfolio 7.3.0 ha confermato l'incompatibilità reale
   `vectorbt -> Numba -> numpy<2.5`; nessun downgrade o cambio lock è stato fatto.
3. Il worktree contiene ampio lavoro concorrente AI Export/provider/frontend. La
   remediation non lo ha ripristinato né incluso nei gate Risk.

### 15.7 Stato rispetto al piano originale

| Gate | Stato |
|---|---|
| G0 piano | ✅ chiuso |
| G1 fondazione quant | ✅ chiuso |
| G2 serie/metadata | ✅ chiuso |
| G3 rolling risk | ✅ chiuso |
| G4 multi-asset deterministico | ✅ chiuso |
| G5 simulation/scale/P13 backend | ✅ chiuso e auditato |
| G6 frontend | ⏸️ capability parziali presenti; piano riconciliato, non eseguito |
| GF finale | ⏳ aperto |

Lavoro restante:

1. eseguire il nuovo Step 6;
2. aggiungere UI P13 minima e smoke real-backend;
3. chiudere GF con suite globale su worktree stabile;
4. aggiornare knowledge graph/devWiki a chiusura della fase frontend.

Nessuna migrazione DB e nessun cambio `Pipfile`/`Pipfile.lock` appartengono a questa
remediation.
