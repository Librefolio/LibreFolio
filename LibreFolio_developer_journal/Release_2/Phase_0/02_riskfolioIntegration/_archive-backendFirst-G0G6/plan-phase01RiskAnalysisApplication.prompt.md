# Piano Applicativo — Risk Analysis (Fase 0.1)

> **Stato dello studio:** approvato (review-1…4). Questo è il **piano applicativo
> incrementale e verificabile**, non codice. Nessuna feature/endpoint/componente è
> implementata qui. **Le dipendenze non vengono installate in questa fase
> documentale:** il piano descrive con precisione come `P0` le installerà
> definitivamente (manifest, lock, Docker, CI) durante l'implementazione.
>
> **Fonti:** documenti dello studio (`contract-`, `analysis-`, `brainstorm-`,
> `review-`, `README`); codice reale di LibreFolio (evidenza `file:linea`);
> decisioni definitive del prompt di revisione del piano (2026-07-27); ispezione
> API/doc ufficiali delle librerie con versioni verificate su PyPI.
>
> **Aggiornamento esecuzione — 28 Luglio 2026:** P0-P13 backend sono stati
> implementati. P11 usa esclusivamente QuantLib MC/QMC in worker `spawn`; RQMC è
> rimosso; P12 usa pool persistenti separati; P13 usa Riskfolio-Lib 7.0.1.
> Le note di esito sotto prevalgono sulle alternative originariamente pianificate.
>
> **Aggiornamento IA G6 — 29 Luglio 2026:** placement, scope e scenari sono
> approvati; audit proxy, lifecycle lazy/cache, bucket UX e tag YAML sono espliciti in
> [`plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md`](./plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md).
> L'implementazione è autorizzata con sequenza backend-first e gate visuale dopo
> ogni vista funzionale.

## Indice
- [0. Principi vincolanti](#0-principi-vincolanti)
- [1. Decisioni consolidate](#1-decisioni-consolidate)
- [2. Librerie quantitative](#2-librerie-quantitative)
- [3. Matrice capability → libreria](#3-matrice-capability--libreria)
- [4. Invalidazione post-sync: classificazione con evidenza](#4-invalidazione-post-sync-classificazione-con-evidenza)
- [5. Piano a step P0–P13](#5-piano-a-step-p0p13)
- [6. Test obbligatori](#6-test-obbligatori)
- [7. Attività, dipendenze, critical path](#7-attività-dipendenze-critical-path)
- [8. Questioni aperte residue](#8-questioni-aperte-residue)
- [Tracciabilità R0–R9 ↔ P0–P13](#tracciabilità-r0r9--p0p13)

---

## 0. Principi vincolanti

1. **Riuso prima di nuove astrazioni** (ordine obbligatorio): riuso diretto →
   estensione compatibile → composizione di contratti esistenti → estrazione di una
   primitive → libreria già adottata → nuovo elemento solo per gap dimostrato.
   Ogni nuovo schema/service/utility/componente/dipendenza deve dichiarare: *gap
   reale · elementi esistenti valutati · perché non bastano · impatto sui consumer ·
   test di non regressione · strategia di migrazione*.
2. **Matematica nel backend** (service layer o plugin). Il frontend configura /
   invoca / presenta / spiega / mostra warning+metadata; **non** ricalcola, riallinea
   serie, converte valute, interpreta formule, ricostruisce risultati.
3. **Componenti UI custom prima di HTML/ad-hoc**: `PageToolbar`, `TabBar`, selettore
   temporale condiviso, select custom, tooltip custom, `PageSyncModal`,
   `DataQualityBanner`, `KpiCard`, `AssetSearchAutocomplete`, chart-wrapper/ECharts
   helper, renderer segnali, formattatori, stati loading/skeleton/empty/error,
   pattern responsive e light/dark.
4. **Adapter contro API reali, mai contro mock.** Le librerie confermate in P0 entrano
   subito nel manifest/lock/Docker/CI e gli step successivi le usano tramite le loro
   API effettive.
5. I nomi dello studio (`AssetReturnSeries`, `RiskResultMetadata`) sono **capability
   semantiche**, non nomi di classe obbligatori.

---

## 1. Decisioni consolidate

Confermate esplicitamente e vincolanti per tutti gli step:

| # | Decisione |
|---|-----------|
| D1 | **`SignalCategory.RISK`** nuovo valore di enum (**non** riuso di `VOLATILITY`) |
| D2 | Metriche rolling asset-scoped (drawdown underwater, rolling volatility, rolling return, rolling Sharpe, rolling beta) come **`SignalPlugin`** |
| D3 | **Rolling Sharpe**: `risk_free_annual_rate` param del plugin (default 0); conversione al giornaliero nel service layer; **nessun** provider/curva/seconda serie/sottosistema in 1ª impl. |
| D4 | **Rolling beta solo con asset reale**: parametro **`comparison_asset_id`** (dominio/UI: `comparison_asset`); **nessun benchmark sintetico, nessuna seconda serie sintetica, nessun risk-free come benchmark del beta** |
| D5 | **Utility comune di preparazione serie** nel service layer (estratta/estesa dal preflight di `SignalService`), unico punto per SignalPlugin/RiskAnalytic/correlazione/PCTR/confronto/stress/VaR-CVaR/simulazione/ottimizzazione |
| D6 | **Estendere `DataQualityReport`** in via prioritaria per ogni campo che descrive la qualità della sorgente; separare da `RiskResultMetadata` (contesto d'esecuzione) |
| D7 | **`PageSyncModal`** con prezzi **e** FX preselezionati, avvio esplicito utente; banner **non** avvia il sync direttamente |
| D8 | **Assets Global ha quattro tab**: `Assets | Correlation | Scenarios | Allocation`. Correlazione primaria in `Correlation`; un solo contratto riusato in Dashboard/Broker/Asset Detail; broker seed = solo SET di asset |
| D9 | **Stress differenziato per scope**, una sola definizione di scenario (Asset Detail % · Assets Global/Scenarios % multi · Dashboard/Broker sulla composizione corrente) |
| D10 | **QuantLib** = motore quantitativo/simulazione principale (dietro adapter); **Riskfolio-Lib** = frontiera/ottimizzazione (ruolo separato). **Entrambe verificate e, se confermate, installate definitivamente in `P0`.** |
| D11 | Production espone **MC / QMC QuantLib**. RQMC è rimosso; NumPy/SciPy restano algebra/oracle, non adapter alternativo. QMCPy è fuori piano. |
| D12 | Calcoli QuantLib/Riskfolio **sempre** in processi `spawn` persistenti e separati. P12 decide il numero di worker, non l'isolamento. |
| D13 | Scope patrimoniale unico: `kind=portfolio` + `broker_ids` opzionale; Broker Detail usa una lista di cardinalità uno; `kind=broker` viene eliminato |
| D14 | UI P13 solo in `Assets Global → Allocation`; non è holdings-aware e non compare integralmente in Dashboard/Broker |
| D15 | Catalogo scenari statico, typed, versionato, caricato all'avvio: built-in + directory host; frontend servito da API, mai lettura YAML diretta |
| D16 | Nomi/descrizioni degli scenari localizzati negli YAML; built-in EN/IT/FR/ES obbligatorie; host con fallback deterministico |
| D17 | Historical replay usa rendimenti osservati; asset senza storia → proxy manuale o esclusione; nessuna sostituzione automatica |
| D18 | Hypothetical shock usa una dimensione; missing sector/geography → `Other=100%`; `european_union`, precedenza Paese > UE > Other |
| D19 | Dashboard/Broker riusano summary + pannelli espandibili lazy; nessuna sub-tab Risk e nessuno stato URL/localStorage iniziale |
| D20 | Replay auditabile: response/metadata espongono contatori, mapping original→proxy, esclusioni e policy effettive; qualità separata in `DataQualityReport` |
| D21 | Lazy semantics: accordion close/open non invalida dati; request identity e data-generation governano stale/cache/refetch |
| D22 | Editor shock: bucket presenti nello scope di default + toggle `Mostra tutti`; `Other` sempre visibile per sector/geography |
| D23 | YAML `tags` opzionali, slug aperti e senza semantica finanziaria; nessuna ricerca/filtro UI/API avanzato in G6 |
| D24 | Replay portfolio/broker: il peso di un asset escluso diventa residuo a rendimento zero; nessuna rinormalizzazione |

> **Esito corretto P0/G5 — 28 Luglio 2026**: QuantLib 1.43 e Riskfolio-Lib
> 7.0.1 sono `ADOPTED` con NumPy 2.5.1; `vectorbt`/`numba` assenti. Host e
> Linux arm64/amd64 superano i probe. RQMC è escluso dal prodotto. Evidenza:
> [`spike-phase01QuantLibraries.md`](./spike-phase01QuantLibraries.md).

---

## 2. Librerie quantitative

> Versioni/licenze **verificate su PyPI** (`pypi.org/pypi/<pkg>/json`) il 2026-07-27.
> **La compatibilità concreta (wheel, binding, container, CI) e le capability API sono
> da confermare con probe reale in `P0`.** La sola assenza di un vincolo
> `requires_python` **non** dimostra compatibilità con Python 3.13.

### 2.1 QuantLib (binding Python, SWIG) — motore principale
- **Versione:** `1.43` (PyPI). **Licenza:** **BSD-3-Clause** (OSI, non-copyleft).
- **Compatibilità Python 3.13:** **non ancora confermata → da verificare concretamente
  in P0** (disponibilità wheel, assenza di compilazione nativa imprevista, import del
  binding SWIG, comportamento nel container, CI). `requires_python`: non dichiarato su
  PyPI — irrilevante ai fini della prova di compatibilità.
- **Fonti:** <https://pypi.org/project/QuantLib/>, <https://www.quantlib.org/>, <https://quantlib-python-docs.readthedocs.io/>.
- **Capability rilevanti (da confermare nel binding installato, P0):**
  - **Processi stocastici:** `GeneralizedBlackScholesProcess` (GBM), `BlackScholesMertonProcess`, `HestonProcess`, `Merton76Process` (jump-diffusion), `VarianceGammaProcess`, processi sui tassi (Vasicek, Hull-White, CIR).
  - **Generatori:** `MersenneTwisterUniformRng` (pseudo), **`SobolRsg`** (low-discrepancy), `InverseCumulativeRsg` (gaussianizzazione).
  - **Path generator:** `GaussianPathGenerator` (single), **`GaussianMultiPathGenerator` / `MultiPathGenerator`** (multi-asset correlato via matrice/Cholesky).
  - **QMC:** Sobol esposto; production usa `skipTo` come indice iniziale deterministico.
    Le API Burley/RQMC non fanno parte del contratto prodotto.
  - **Infrastruttura quant:** `Calendar` (calendari di mercato), `DayCounter` (Actual/Actual, 30/360…), curve tassi (`YieldTermStructure`, `FlatForward`, bootstrap), **obbligazioni** (`FixedRateBond`, `ZeroCouponBond`), **duration/convexity** (`BondFunctions.duration/convexity`), pricing Black-Scholes/analitico.
- **⚠️ Thread-safety (decisione D12):** QuantLib **non è thread-safe** — stato globale (evaluation date non thread-local), lazy-eval/caching → **non** condividere oggetti tra thread. Modello «un thread / un contesto di mercato»; per il parallelismo usare **process `spawn`** con oggetti locali al worker.
- **Differenza API Python vs C++:** alcuni template C++ (scrambled Sobol, alcuni engine MC) potrebbero **non** essere wrappati in SWIG → assunzione da confermare con probe (P0).

> **Esito P0**: wheel ABI3 e capability verificate su Python 3.13/macOS arm64 e
> Linux arm64/amd64. Dipendenza pinata a 1.43. Le sequenze Burley sono esposte;
> il path-generator Burley specializzato non lo è.

### 2.2 Riskfolio-Lib — frontiera / ottimizzazione
- **Versione adottata:** `7.0.1`. **Licenza:** **BSD-3-Clause** (OSI).
- **Fonti:** <https://pypi.org/project/riskfolio-lib/>, <https://riskfolio-lib.readthedocs.io/>.
- **Dipendenze pesanti:** `cvxpy (≥1.7)`, `clarabel`, `SCS`, `scikit-learn`, `statsmodels`, `arch`, `xlsxwriter`, `networkx`, `astropy`, `pybind11`, oltre a numpy/scipy/pandas/matplotlib. → **impatto Docker single-image, durata build, conflitti NumPy/SciPy/pandas, solver disponibili** da misurare **in P0**.
- **Ruolo (separato da QuantLib):** frontiera efficiente, ottimizzazione (min-risk, max-Sharpe **stimato**, max-utility, risk-parity), 22+ misure di rischio convesse. **Non** fa simulazione forward: MC/QMC restano QuantLib.
- **Installazione:** **verificata e installata in P0 se confermata**, anche se l'uso applicativo principale è nello step finale della frontiera (P13).
- **Solver:** via CVXPY (ECOS/SCS/Clarabel default; MOSEK/Gurobi opzionali). Nessun solver commerciale richiesto.

> **Esito corretto P0/G5**: adottata 7.0.1 con NumPy 2.5.1. CLARABEL completa
> min-risk, max-Sharpe, risk parity, frontiera, bound, covariance
> historical/Ledoit-Wolf/OAS e infeasible detection. Delta oltre QuantLib:
> 644,4 MiB arm64 / 672,9 MiB amd64.

### 2.3 NumPy / SciPy — algebra e oracle (già presenti)
- **Presenti** nell'ambiente: numpy 2.5, scipy 1.18, pandas 3.0.
- **Ruolo:** algebra matriciale, aggregazione, primitive statistiche e oracle
  indipendenti. Nessun sampling/evoluzione production e nessun fallback silenzioso.

### 2.4 QMCPy — non pianificata (nota fallback futuro)
- **Non** candidata all'installazione in P0, **non** nel critical path, **non** nei
  benchmark obbligatori, **non** dipendenza pianificata. La licenza QMCPy **non** è una
  questione aperta di questo piano.
- Rivalutabile **solo in futuro** e solo se emerge un gap concreto: *QuantLib non espone
  la capability necessaria* **AND** *SciPy richiede logica custom significativa* **AND**
  *QMCPy risolve direttamente e meglio quel requisito* (in quel caso andrà verificata la
  licenza reale del repo).

---

## 3. Matrice capability → libreria

Scelta **per capability**, non per libreria. `⇒` = decisione finale.

| Capability | LibreFolio esistente | QuantLib | Riskfolio-Lib | NumPy/SciPy | ⇒ Scelta | Motivo |
|---|---|---|---|---|---|---|
| Vol/Sharpe/Sortino/MaxDD/CAGR scalari | `numpy` (già) | ✓ | ✓ | ✓ | **NumPy/pandas** | poche righe, zero peso |
| Serie rolling | `pandas.rolling` | — | — | ✓ | **pandas** | già dipendenza |
| Correlazione/covarianza | `pandas.corr` | ✓ | ✓ (stimatori) | ✓ | **pandas/NumPy** (shrinkage: Riskfolio se serve) | leggero |
| PCTR (MCTR/CCTR/PCTR) | — | — | ✓ | ✓ | **NumPy** (formula chiusa) | contratto §6.7 |
| VaR/CVaR historical/param | — | ✓ | ✓ | ✓ | **NumPy/SciPy** | `CVaR≥VaR≥0`, controllo pieno |
| GBM single-asset simulato | — | ✓ | — | ✓ | **QuantLib** | processo/RNG/evoluzione production |
| Multi-asset correlato (path) | — | ✓ (`StochasticProcessArray`) | — | ✓ (Cholesky) | **QuantLib** | correlazione nativa |
| QMC (Sobol) | — | ✓ (`SobolRsg`) | — | ✓ | **QuantLib** | `skipTo` + evoluzione QuantLib |
| RQMC (Sobol scrambled + seed) | — | parziale | — | ✓ | **non esposto** | rimosso dal contratto |
| Calendari/day-count/curve tassi | parziale | ✓ **robusto** | — | — | **QuantLib** (adapter) | standard di settore |
| Bond duration/convexity, stress tassi | limitato | ✓ | — | — | **QuantLib** (evoluzione) | BTP/obbligazioni |
| Frontiera efficiente / ottimizzazione / risk-parity | — | — | ✓ **specializzato** | (QP manuale) | **Riskfolio-Lib** (R9/P13) | evita QP a mano |

---

## 4. Invalidazione post-sync: classificazione con evidenza

**Domanda:** l'invalidazione cache dopo sync è refuso / già coperta / estensione FE /
gap backend?

**Evidenza dal codice:**
- **Cache portfolio content-keyed → auto-invalidante.** `_portfolio_blob_cache` (TTL
  24h, `portfolio_engine.py:50`) usa una chiave che include un **`price_fingerprint`**
  (`portfolio_engine.py:2124,2139`). La funzione `_compute_price_fingerprint`
  (`portfolio_engine.py:2243-2265`) restituisce `COUNT(PriceHistory.id) +
  MAX(PriceHistory.fetched_at)`; il docstring dichiara esplicitamente: *«any price
  insert/update changes at least one of these, invalidating the cache key»*. → dopo un
  refresh prezzi, `fetched_at` cambia → **nuova chiave → cache miss → ricalcolo**.
  Nessuna `.delete()` sul blob cache esiste (né serve).
- **Cache prezzi asset** invalidata esplicitamente sui refresh/wipe
  (`asset_source.py:948-949,1696-1697`); **FX cache** è solo TTL 300s
  (`fx.py:31-34`) → si auto-risana.
- **Frontend:** l'handler `onsynced` invalida già gli store
  (`invalidateAfterMutation`, `invalidateAssetPriceStore`, `invalidateFxRoutes`,
  `signalCatalogStore.invalidate`, ricarica prezzi/FX) — pattern in
  `assets/+page.svelte` e affini.

**Classificazione:**
- **A (wording generico) + B (già coperto)** per portfolio/FX/frontend: la chiave
  content-derived e gli store frontend gestiscono già il refresh.
- **C (piccola estensione)** *solo* se la Risk Analysis introdurrà una **cache
  propria**: dovrà adottare lo **stesso pattern content-keyed** (chiave che include
  `price_fingerprint`/fingerprint FX + parametri canonici + `algo_version`, incluso
  `random_seed` MC oppure `sobol_start_index` QMC), così da auto-invalidarsi come il
  blob. **Nessun D (gap backend), nessun nuovo sistema di invalidazione.**

---

## 5. Piano a step P0–P13

> Ogni step riporta: **Obiettivo · Stato attuale · Gap · File/componenti · Contratto
> backend · Schema dati · Service layer · Frontend · Dipendenze · Test · Migrazione ·
> Compatibilità · Criteri di completamento · Rischi · Fallback · Parallelizzabile ·
> Bloccante.** «Nessuno» dove non applicabile.

### P0 — Probe e installazione definitiva delle librerie

- **Stato esecuzione:** ✅ completato e rivalutato: QuantLib 1.43 e Riskfolio
  7.0.1 `ADOPTED`; RQMC rimosso.
- **Obiettivo:** verificare nell'ambiente **reale** di LibreFolio le capability, la
  licenza e la compatibilità di **QuantLib** e **Riskfolio-Lib** e, se confermate,
  **installarle definitivamente** (manifest + lock + Docker + CI). Non è un semplice
  probe temporaneo con installazione rinviata.
- **Sequenza:**

  ```text
  P0.a — Probe nell'ambiente reale di LibreFolio (Python + Docker)
  P0.b — Verifica API, licenza e compatibilità Python 3.13
  P0.c — Decisione di adozione (registrata con evidenza riproducibile)
  P0.d — Installazione definitiva delle librerie confermate
  P0.e — Aggiornamento manifest e lock file
  P0.f — Aggiornamento build Docker
  P0.g — Smoke test e CI
  P0.h — Misurazione dell'impatto sull'immagine
  ```

- **Esito:** Python 3.13, host, Linux arm64/amd64, wheel, solver, lock e costo
  immagine verificati; immagine finale arm64 importabile.
- **File/componenti:** manifest dipendenze (`Pipfile`/`requirements.txt`/`pyproject.toml`),
  lock file, `Dockerfile`/build, pipeline CI, script di probe/smoke-test.
- **Contratto/Schema/Service/Frontend:** nessuno.
- **Dipendenze:** **QuantLib** e **Riskfolio-Lib** installate **realmente** se superano
  il probe (regola: superato → manifest + lock + Docker + CI; non superato → fallback
  dichiarato + decisione documentata).
- **Verifiche obbligatorie QuantLib (stesso ambiente Python+Docker):** wheel compatibile ·
  install senza compilazioni impreviste · import binding · versione · licenza ·
  costruzione processo stocastico · path single · multi-path · generatori pseudo ·
  `SobolRsg` · API QMC · esclusione RQMC documentata · calendari ·
  day-counter · curve · obbligazioni · duration/convexity · build Docker · CI.
- **Verifiche obbligatorie Riskfolio-Lib:** install reale · versione · licenza ·
  compatibilità Python · dipendenze transitive · solver disponibili · import ·
  ottimizzazione minima su fixture · impatto lock · incremento immagine · durata build ·
  CI · conflitti con NumPy/SciPy/pandas.
- **Test:** smoke-test d'import + capability minima per ciascuna libreria confermata;
  suite CI verde; misura MB immagine e durata build.
- **Migrazione:** nessuna (schema/DB invariati). **Compatibilità:** provare su Python
  3.13 nel container di progetto.
- **Output obbligatori:** versione+licenza QuantLib confermate · compatibilità 3.13
  provata o respinta · wheel/build strategy · API Python disponibili · MC/QMC
  disponibili · RQMC escluso · multi-path · processi utili · adapter boundary
  confermato · Riskfolio installabile · solver · impatto Docker misurato · lock
  aggiornato · CI verde · decisione definitiva registrata.
- **Criteri di completamento:** le librerie confermate risultano **nel manifest, nel
  lock, nell'immagine, importabili, coperte da smoke test, compatibili con la CI**. Non
  basta un test locale temporaneo.
- **Rischi verificati:** costo binding QMC, RAM/cold import Riskfolio e peso immagine;
  wheel Python 3.13 e solver sono confermati.
- **Fallback:** nessuno nel path production. Fallimento QuantLib/Riskfolio chiude il
  gate con errore esplicito.
- **Parallelizzabile:** ✅ (parte subito con P1, P2). **Bloccante per:** P11, P13.

### P1 — Utility comune di preparazione delle serie (D5)
- **Obiettivo:** un unico punto service-layer che prepara le serie per tutti i consumer.
- **Stato attuale:** il preflight vive in `SignalService` (`prepare_plan()`
  `signal_service.py:118-261`, `_build_coverage()` `:793-871`,
  `_select_computation_points()` `:923-974`, `_availability_state()` `:986-1026`); i
  plugin ricevono punti già selezionati (`:553-558`); `convert_bulk`
  (`fx.py:1225-1411`) fa già conversione FX batch + backward-fill + provenienza.
- **Gap:** la preparazione non è estratta/riusabile fuori dai segnali; manca calendario
  congiunto multi-serie + carried-forward + fattore osservato + `comparison_asset` +
  serie multiple; manca una `AssetReturnSeries` canonica (oggi il per-asset è
  lotto/posizione-based in `lots_analysis_service`).
- **File/componenti:** nuovo modulo service (es. `services/risk/series_preparation.py`)
  **estraendo** la logica comune da `signal_service.py`; riuso `fx.convert_bulk`,
  price layer, coverage.
- **Contratto backend:** funzione `prepare_series(scope, primary, comparison_asset?, target_currency,
  window, policy) -> PreparedSeriesResult` con: serie valorizzata, serie rendimenti,
  `annualization_factor` osservato (contratto §2.1), calendario congiunto (§2.2),
  provenienza/coverage/warning/data-quality.
- **Schema dati:** `AssetReturnSeries` come **risultato tipizzato della utility**
  (DTO/projection), *non* tabella DB (nessuna migrazione). Riuso `FAPricePoint`/
  `SignalPricePoint` dove possibile.
- **Service layer:** estrae dal `SignalService` la parte «prepara input», lasciando nel
  `SignalService` orchestrazione plan/warmup/status; condivide la utility con
  `RiskAnalytic` e con lo step di confronto (P9).
- **Frontend:** nessuno.
- **Dipendenze:** nessuna nuova libreria.
- **Test:** calendario congiunto; carried-forward prezzi; backward-filled FX;
  target-currency; annualization factor; neutralità ai flussi (TWRR); coverage/provenance;
  **non-regressione dei segnali esistenti** (i plugin attuali devono dare identico output).
- **Migrazione:** nessuna. **Compatibilità:** i 17 plugin esistenti non cambiano output.
- **Criteri:** utility usata dai plugin esistenti senza differenze; copertura test.
- **Rischi:** regressione sottile nella selezione punti dei segnali.
- **Fallback:** mantenere la logica nel `SignalService` e **condividere via import** se
  l'estrazione risultasse rischiosa.
- **Parallelizzabile:** parte subito. **Bloccante per:** P3, P4, P5, P9.

### P2 — Estensione `DataQualityReport` e metadata comuni (D6)
- **Obiettivo:** rappresentare la qualità estesa (prezzi + FX) e separare i metadata
  d'esecuzione.
- **Stato attuale:** `DataQualityReport` (`portfolio.py:224-239`) ha
  `missing_price_assets`/`missing_fx_pairs`/`stale_prices`/`incomplete_*`; **mancano**
  `data_quality_status`/`excluded_assets`/`carried_forward_*`. `SignalStatus`/
  `SignalWarningCode`/`SignalWarmupMetadata` esistono (`signals.py:171-300`).
- **Gap:** nessun campo sintetico di stato; nessun conteggio carried-forward; nessuna
  distinzione asset esclusi per qualità vs per requisito-metrica.
- **File/componenti:** `schemas/portfolio.py` (estensione), eventuale
  `schemas/risk.py` (nuovo `RiskResultMetadata`).
- **Contratto backend:** estendere `DataQualityReport` con `data_quality_status`
  (`ok|carried_forward|partial`), `carried_forward_price_points`,
  `carried_forward_fx_points`, `excluded_assets` (privi di dati valorizzabili).
  `RiskResultMetadata` (nuovo) = contesto esecuzione: periodo, metodo, parametri,
  valuta, annualization factor, mode/composition policy, risk-free, comparison_asset,
  `algo_version`, `sampling_method`, `path_count`, `random_seed` MC oppure
  `sobol_start_index` QMC, timestamp. **Asset esclusi per requisito-metrica** → nei
  metadata del risultato, **non** in `DataQualityReport` (separazione semantica).
- **Schema dati:** solo Pydantic (nessuna tabella).
- **Service/Frontend:** i producer popolano i nuovi campi; il FE li mostra (banner/modale).
- **Dipendenze:** nessuna. **Migrazione:** nessuna (schemi, non DB).
- **Compatibilità:** campi **additivi/opzionali** → consumer attuali invariati.
- **Test:** serializzazione; nessun campo duplicato; mapping carried-forward/excluded.
- **Criteri:** nuovi campi presenti e valorizzati dai producer; consumer legacy verdi.
- **Rischi:** duplicazione con campi esistenti → mitigato dalla review dei nomi.
- **Fallback:** usare solo `RiskResultMetadata` se estendere il report crea attrito.
- **Parallelizzabile:** parte subito. **Bloccante per:** P4, P5, P6, P9.

### P3 — `SignalCategory.RISK` + `comparison_asset` (D1, D4)
- **Obiettivo:** abilitare la categoria RISK e la dipendenza da un **asset di confronto reale**.
- **Stato attuale:** `SignalCategory=TREND|MOMENTUM|VOLATILITY|VOLUME`
  (`signals.py:98-103`); nessuno slot di serie di confronto in `SignalInputRequirements`
  (`:303-318`) né in `SignalExecutionContext` (`:260-273`); `params_model` supporta
  scalari (`base.py:43`).
- **Gap:** categoria RISK assente; nessuna orchestrazione del `comparison_asset`.
- **File/componenti:** `schemas/signals.py`, `services/signal_service.py`,
  catalogo FE (Zodios/OpenAPI dopo `./dev.py api sync`).
- **Contratto backend:** aggiungere `SignalCategory.RISK`; il concetto di dominio/UI è
  **`comparison_asset`** con parametro **`comparison_asset_id`**. `SignalService`
  risolve `comparison_asset_id`, converte entrambe le serie nella target currency,
  costruisce il calendario congiunto, propaga qualità, immette
  **`comparison_asset_series`** nell'`SignalExecutionContext` e passa **due serie pronte**
  al plugin (il plugin non carica/allinea/converte/sincronizza). Un'astrazione interna
  «series dependency» generica è ammessa **solo se** riduce duplicazione, resta semplice,
  non rende ambiguo il catalogo e non anticipa casi non necessari; in ogni caso
  **UI/dominio espongono `comparison_asset`**, non `secondary_series`.
- **Flusso:**

  ```text
  Utente seleziona comparison_asset
          ↓
  comparison_asset_id nei parametri
          ↓
  SignalService risolve le due serie
          ↓
  utility comune (P1) applica valuta, calendario, qualità
          ↓
  comparison_asset_series entra nell'execution context
          ↓
  RollingBetaPlugin calcola il risultato
  ```

- **Schema dati:** param `comparison_asset_id: int` nello schema param del plugin beta.
- **Service layer:** estende il preflight (P1) per il caso a 2 serie.
- **Frontend:** `comparison_asset` picker via **`AssetSearchAutocomplete`** (riuso);
  catalogo aggiornato con la categoria RISK.
- **Dipendenze:** nessuna. **Migrazione:** nessuna. **Compatibilità:** campo
  `comparison_asset` **opzionale** → plugin esistenti invariati.
- **Test:** risoluzione comparison_asset; conversione entrambe le serie; calendario
  congiunto a 2 serie; catalogo espone RISK; `./dev.py api sync` rigenera il client.
- **Criteri:** un plugin beta riceve `comparison_asset_series` pronta; nessun accesso DB
  dal plugin.
- **Rischi:** infrastruttura «series dependency» troppo generica → mantenere il concetto
  UI `comparison_asset`.
- **Fallback:** implementare la serie di confronto in modo specifico per il beta senza
  slot generico, se l'astrazione risultasse ambigua nel catalogo.
- **Parallelizzabile:** dopo P1. **Bloccante per:** P4 (beta), P9.

### P4 — Rolling risk come `SignalPlugin` (D2, D3, D4)
- **Obiettivo:** 5 plugin rolling di **Asset Detail**: drawdown underwater, rolling
  volatility, rolling return, rolling Sharpe, rolling beta.
- **Stato attuale:** sistema segnali completo (discovery/catalogo/param/context/status/
  warmup/renderer/tooltip/legenda/serie); plugin esistenti come `ema.py`/`rsi.py`.
- **Gap:** i 5 plugin non esistono.
- **File/componenti:** `services/signal_plugins/{drawdown,rolling_volatility,rolling_return,
  rolling_sharpe,rolling_beta}.py`; renderer FE segnali (riuso `backendRenderer.ts`,
  `LineChart`).
- **Contratto backend (per plugin):** input richiesti · parametri · warmup · output ·
  asse/rendering · metadata · errori di dominio. Sharpe: `risk_free_annual_rate`
  (default 0), conversione giornaliera `(1+rf)^(1/365)-1` nel service layer. Beta:
  **solo `comparison_asset_id`** (asset reale), `comparison_asset_series` preparata (P3),
  `β=cov/var`; **rifiuto** di benchmark a varianza nulla (contratto §6.5); **nessun
  benchmark sintetico né risk-free come benchmark**.
- **Schema dati:** param model per plugin (finestra, ecc.).
- **Service layer:** riuso P1 per preparazione; annualizzazione osservata dai metadata.
- **Frontend:** configurazione via UI segnali esistente; verifiche di rendering/tooltip/
  legenda; `comparison_asset` picker (P3).
- **Dipendenze:** solo NumPy/pandas. **Migrazione:** nessuna. **Compatibilità:** nuovi
  plugin, additivi.
- **Test:** unit per formula (drawdown/vol/return/Sharpe/beta); warmup; output/asse;
  errori di dominio (insufficienza dati → status PARTIAL/UNAVAILABLE); integrazione
  catalogo→esecuzione; verifiche FE.
- **Criteri:** i 5 plugin nel catalogo, renderizzati, con metadata/warning corretti.
- **Rischi:** semantica warmup del beta (2 serie). **Fallback:** consegnare prima i 3
  price-only, poi Sharpe, poi beta.
- **Parallelizzabile:** i 3 price-only in parallelo; Sharpe dopo D3; beta dopo P3.
  **Bloccante per:** UI Asset Detail rolling.

### P5 — `RiskAnalytic` multi-asset (scope portafoglio/subset)
- **Obiettivo:** contratto plugin per correlazione, PCTR, (poi VaR/CVaR, stress, MC).
- **Stato attuale:** nessun contratto multi-asset; serie di portafoglio esistono
  (`PortfolioHistoryPoint.twrr`, `DailyPortfolioState` già in valuta target,
  `portfolio_engine.py:560-568,1049-1121`).
- **Gap:** nessun `RiskAnalytic`; dipende da `AssetReturnSeries` (P1) e metadata (P2).
- **File/componenti:** `services/risk_plugins/base.py` (`RiskAnalytic` ABC:
  `output_kind`, `scopes`, `modes`, `params_model`, `compute(series, weights, params,
  ctx)`), `correlation.py`, `risk_contribution.py`.
- **Contratto backend:** `mode` (`historical` disponibile subito; `current_composition`
  = `current_buy_and_hold`) obbligatorio nei metadata; correlazione = un contratto
  riusato (D8); PCTR = MCTR/CCTR/PCTR (contratto §6.7), output barre divergenti.
- **Schema dati:** `RiskResultMetadata` (P2).
- **Service layer:** riuso P1 per serie multiple + calendario congiunto unico
  (covarianza/correlazione/PCTR sullo stesso calendario).
- **Frontend:** consumato in P6/P7.
- **Dipendenze:** NumPy/pandas. **Migrazione:** nessuna.
- **Test:** correlazione post-conversione valuta; celle insufficienti; PCTR (somma
  100%, contributi negativi, cash vol-nulla=0); calendario congiunto multi-asset.
- **Criteri:** correlazione e PCTR calcolati con metadata/qualità.
- **Rischi:** costo di `AssetReturnSeries`. **Fallback:** correlazione prima, PCTR dopo.
- **Parallelizzabile:** dopo P1/P2. **Bloccante per:** P6, P7, P8, P9, P10.

### P6 — Asset Global: tab `Correlation` (D8)
- **Obiettivo:** casa primaria della correlazione, vista asset-centrica.
- **Stato riconciliato G6:** route/tab, store e `CorrelationHeatmap.svelte` sono
  parzialmente presenti; richiedono audit e composizione secondo l'IA finale.
- **IA:** `Assets | Correlation | Scenarios | Allocation`; un unico asset universe
  route-level alimenta le tre tab analitiche.
- **Correlation:** switch manuale `[Heatmap] [Asset centrale]`; default UI iniziale
  heatmap su desktop con ≤20 asset, asset-centric su mobile o set più grandi.
  La soglia è euristica visuale, non vincolo finanziario.
- **File/componenti:** `routes/(app)/assets/+page.svelte`,
  `CorrelationHeatmap.svelte`, selector asset-set condiviso,
  `PageSyncModal`/`DataQualityBanner`.
- **Contratto backend:** endpoint correlazione (contratto unico D8), consuma P5.
- **Frontend:** broker → **solo SET**; add/remove manuale; heatmap/lista; warning,
  coverage, osservazioni, esclusi; apertura `PageSyncModal`.
- **Dipendenze:** ECharts (già presente) per heatmap. **Migrazione:** nessuna.
- **Compatibilità:** vista Asset Global attuale invariata nella tab `Assets`.
- **Test FE:** broker→set asset; add/remove manuale; render heatmap; warning; sync modal;
  switch manuale; responsive default; build+check.
- **Criteri:** heatmap funzionante con SET costruito senza pesi.
- **Vincolo placement:** stress multi-asset vive nella tab `Scenarios`, non in
  `Correlation`.
- **Parallelizzabile:** dopo P5. **Bloccante per:** nessuno (feature UI).

### P7 — Dashboard Risk e Broker Risk
- **Obiettivo:** stesso componente condiviso in Dashboard e Broker Detail,
  configurato con scope differenti.
- **Scope:** Dashboard = `portfolio + broker_ids` toolbar oppure omesso; Broker =
  `portfolio + broker_ids=[current]`. Migrare e poi eliminare `kind=broker`.
- **IA:** summary sempre visibile + pannelli espandibili `Rischio osservato`,
  `Struttura del rischio`, `Confronto`, `Scenari`; nessuna sub-tab.
- **Lifecycle:** query lazy al primo open; same-key close/reopen riusa
  in-flight/result/error. Cambio date/scope/currency/params crea una nuova request
  identity: pannello aperto ricarica, pannello chiuso aspetta la riapertura. Sync e
  mutazioni invalidano dati senza cambiare lo stato accordion. Retention garantita
  nel mount; cache cross-mount solo ottimizzazione `riskStore`.
- **File/componenti:** dashboard/broker `+page.svelte`, componenti Risk condivisi,
  `KpiCard`, heatmap, barre divergenti, banner/modale.
- **Contratto backend:** consuma P5 (KPI storici, drawdown/vol su TWRR, correlazione,
  PCTR); `mode:historical` subito.
- **Frontend:** KPI + drawdown/VaR + PCTR/peso economico/correlation +
  confronto/scenari. Broker con label «Rischio interno a: {broker}».
- **Vincolo P13:** nessun pannello Allocation completo in Dashboard/Broker.
- **Dipendenze:** nessuna nuova. **Migrazione:** contratto scope/API
  `portfolio.broker_ids`; nessuna migrazione DB.
- **Test FE:** scope/payload broker, lazy first-open, retention, KPI, heatmap, PCTR,
  responsive defaults, label subset.
- **Criteri:** contratto e componenti identici fra Dashboard/Broker, salvo scope/label.
- **Parallelizzabile:** dopo P5/P6. **Bloccante per:** P8/P9/P10 (host UI).

### P8 — Stress test per scope (D9)
- **Obiettivo:** catalogo scenario typed + un engine/proiezione riusato per scope.
- **Catalogo:** YAML statico/versionato, built-in + host, validato Pydantic e caricato
  all'avvio; frontend tramite API. Nomi/descrizioni localizzati nel YAML. `tags`
  opzionali come slug machine-readable aperti/inerti, senza UI/search G6.
- **Historical replay:** prezzi+FX storici → rendimenti osservati;
  `current_buy_and_hold` per portfolio/broker; asset senza storia → proxy scelto
  manualmente o esclusione. Nessun proxy automatico. Response/metadata espongono
  contatori, mapping original→proxy, esclusioni/motivi e policy effettive; mapping
  ed esclusioni entrano nella request identity. Il peso escluso resta residuo a
  rendimento zero e non viene redistribuito.
- **Hypothetical:** una dimensione (`asset_class`, `sector` o `geography`);
  sector/geography come distribuzioni; missing metadata → `Other=100%`;
  `european_union` con precedenza Paese > UE > Other, senza sommare. UI: bucket
  presenti nello scope di default + `Mostra tutti`; `Other` sempre visibile.
- **Factor shock:** rimandato; richiede factor exposure model.
- **Frontend:** `HistoricalReplayEditor` e `HypotheticalShockEditor` noti e typed;
  YAML non è un form engine. Parametri iniziali modificabili prima del submit.
- **Placement:** Asset Detail %, Assets Global → `Scenarios` % multi,
  Dashboard/Broker sulla composizione corrente.
- **Dipendenze:** NumPy. **Migrazione:** nessuna.
- **Test:** loader built-in/host; localizzazione; duplicate ID; optional tags;
  replay/proxy/audit trail; shock weighted; bucket visibility; Other; EU
  precedence; parametri effettivi; output coerente per scope.
- **Criteri:** un catalogo, editor typed, formule backend, audit per asset/bucket.
- **Non-obiettivi:** CRUD, DB, persistence, hot reload, salvataggio preset.
- **Parallelizzabile:** dopo P5/P7.

### P9 — Confronto risk-free / comparison asset (R7)
- **Obiettivo:** realizzare il **confronto completo** (risk-free **oppure**
  comparison_asset reale) come funzionalità multi-scope, **componendo** i contratti
  esistenti — **non** un nuovo `ComparisonEngine`. Distinto da P4 (che espone solo i
  plugin rolling di Asset Detail): questo step realizza la vista comparativa /
  «Relative Performance» per Asset Detail, Dashboard Risk e Broker Risk.
- **Stato attuale:** rolling Sharpe/beta esistono come plugin (P4); mancano metriche di
  confronto aggregate (active return, tracking error, Information Ratio, drawdown
  comparato) e la UI comparativa multi-scope.
- **Gap:** solo le metriche/contratti comparativi mancanti; **niente** duplicazione di
  serie, Sharpe, beta, correlazione, drawdown già disponibili.
- **File/componenti:** `services/risk/comparison.py` (composizione), UI pannello
  comparativo riusabile in Asset Detail / Dashboard / Broker.
- **Contratto backend — Modalità A (Risk-free, nessun asset reale):**
  input `risk_free_annual_rate` (default 0) + `currency`; output rendimento eccedente,
  Sharpe, serie cumulata primaria vs baseline deterministica, metadata, data quality.
- **Contratto backend — Modalità B (Comparison asset reale):** input
  `comparison_asset_id` + `target_currency` + `analyzed_range` + `scope`; output minimo:
  rendimento cumulato comparato, **active return**, **tracking error**,
  **Information Ratio**, correlazione, beta, drawdown comparato, differenziale di
  rendimento, metadata, data quality. **Non** trattare l'asset reale come risk-free.
- **Composizione (riuso, non duplicazione):** utility serie (P1) · TWRR portafoglio ·
  serie price-only asset · `comparison_asset_id` · funzioni Sharpe · funzioni beta ·
  correlazione · drawdown · `DataQualityReport` · `RiskResultMetadata`.
- **Schema dati:** `RiskResultMetadata` (P2); nessuna tabella.
- **Frontend (pannello riusabile):**

  ```text
  CONFRONTA CON

  (●) Risk-free
      Tasso annuo: [0,00%]

  ( ) Asset reale
      comparison_asset: [Cerca asset...]

  Risultati:
  - andamento cumulato
  - rendimento relativo
  - tracking error
  - Information Ratio
  - correlazione
  - beta
  - drawdown comparato
  ```

  Componenti **obbligatori (riuso)**: radio/select custom · `AssetSearchAutocomplete` ·
  chart wrapper esistente · renderer temporale · `KpiCard` · tooltip custom ·
  `DataQualityBanner` · `PageSyncModal` · formattatori condivisi · stati
  empty/loading/error esistenti.
- **Scope:** Asset Detail (asset corrente vs risk-free|comparison_asset) · Dashboard Risk
  (portafoglio storico o composizione dichiarata vs …) · Broker Risk (subset del broker
  vs …, con etichetta «rischio e performance relativa interni al sottoinsieme»).
- **Dipendenze:** NumPy/pandas. **Migrazione:** nessuna. **Compatibilità:** additivo.
- **Test:** risk-free default 0; conversione tasso annuale; confronto cumulato; active
  return; tracking error; Information Ratio; correlazione; beta; drawdown comparato;
  target currency comune; calendario congiunto; dati price-only; confronto obbligazionario
  con warning cedole; insufficient data; comparison_asset uguale all'asset primario;
  comparison_asset a varianza nulla; warning qualità prezzi e FX; apertura modale sync;
  Asset Detail; Dashboard; Broker; build/check/frontend test.
- **Criteri:** entrambe le modalità funzionanti nei tre scope, con metadata/qualità.
- **Rischi:** confusione risk-free vs asset reale → separazione esplicita in UI e dominio.
- **Fallback:** consegnare prima la Modalità A (risk-free), poi la Modalità B.
- **Parallelizzabile:** dopo P1/P2/P3 e componenti host (P4/P7). **Bloccante per:** nessuno.

### P10 — VaR / CVaR
- **Obiettivo:** VaR/CVaR historical simulation (default), magnitudini positive.
- **Stato attuale:** assente.
- **Gap:** formule + convenzione segno.
- **File/componenti:** `services/risk_plugins/var_cvar.py`; UI KPI card.
- **Contratto backend:** `CVaR ≥ VaR ≥ 0` (contratto §6.8); metodo dichiarato nei
  metadata; UI formatta come negativo senza cambiare il dominio.
- **Frontend:** `KpiCard` + tooltip metodologico.
- **Dipendenze:** NumPy/SciPy. **Migrazione:** nessuna.
- **Test:** `CVaR≥VaR≥0` a parità di confidence/orizzonte/metodo/campione; casi noti.
- **Criteri:** VaR/CVaR con metodo e metadata.
- **Rischi:** interpretazione utente. **Fallback:** solo historical simulation.
- **Parallelizzabile:** dopo P5.

### P11 — Motore di simulazione stocastica MC/QMC (D10, D11, D12)
- **Stato esecuzione:** ✅ completato con QuantLib 1.43.
- **Obiettivo:** motore stocastico componibile dietro boundary serializzabile.
- **Gap:** processo/sampling/config/aggregazione/metriche/metadata/rendering separati.
- **File/componenti:** `services/risk/quant/`:
  `Contratti LibreFolio → worker QuantLib → risultati serializzabili`; nessun
  oggetto QuantLib esposto a dominio/API.
- **Contratto backend:** separare `StochasticProcess` · `SamplingStrategy`
  (MC IID / QMC Sobol) · `SimulationConfig` · `PortfolioAggregation`
  · `RiskMetrics` · `ResultMetadata` · `Rendering` (il grafico a bande/percentili è
  **soltanto uno** dei renderer).
- **Implementazione:** MC usa generator multi-path QuantLib; QMC usa
  `SobolRsg.skipTo(sobol_start_index)`, gaussianizzazione QuantLib e
  `StochasticProcessArray.evolve`. NumPy aggrega soltanto dopo l'evoluzione.
- **Frontend:** cono percentili su band `LineChart` (riuso Bollinger), label «simulato».
- **Dipendenze:** QuantLib (BSD-3, installata in P0) + NumPy/SciPy. **Migrazione:** nessuna.
- **Test:** `random_seed`/`sobol_start_index` e riproducibilità; MC vs QMC su casi
  noti; dimensioni/correlazioni; adapter; convergenza/stabilità;
  serialize/deserialize input.
- **Criteri:** adapter unico, controllo di sequenza deterministico e non ambiguo,
  metriche corrette.
- **Rischi:** costo SWIG/copia path QMC. **Fallback:** nessuno silenzioso.
- **Parallelizzabile:** spike sì; integrazione dopo P5. **Bloccante per:** P12.

### P12 — Isolamento e scala `spawn` (D12)
- **Stato esecuzione:** ✅ completato.
- **Obiettivo:** process isolation obbligatorio; benchmark per scegliere il numero
  di worker.
- **File/componenti:** due pool `spawn` custom separati, lazy, bounded, persistenti
  durante attività e chiusi dopo idle timeout configurabile.
- **Contratto backend:** ogni subprocess importa QuantLib autonomamente, crea localmente
  processi/curve/generatori/handle e configurazioni, riceve **solo input serializzabili**
  (Pydantic/dataclass), restituisce output serializzabili, **non** condivide oggetti
  QuantLib, **non** riceve connessioni/sessioni/service, **non** dipende da
  PID/scheduling per il controllo di sequenza. Granularità corrente:
  1 job/worker → 1 scenario/config per worker → nessun chunk interno. Se in futuro
  viene introdotto chunking QMC, il parent deve assegnare intervalli
  `sobol_start_index` disgiunti e aggregare esplicitamente
  distribuzioni/percentili/VaR/CVaR — mai media dei quantili.
- **Operatività:** max worker (default conservativo self-hosted), coda, timeout,
  idle reap/restart lazy, cancellazione, error handling, shutdown ordinato,
  protezione RAM, dedup richieste,
  metriche tempo/memoria; nessun fallback in-process.
- **Dipendenze:** stdlib. **Migrazione:** nessuna.
- **Test:** spawn isolation; serialize/deserialize; timeout/error propagation;
  riproducibilità cross-worker; pool vs single.
- **Esito benchmark:** default 1 worker/pool; `>1` configurabile. Due worker:
  `1,938x` simulation, `1,477x` optimization, circa doppio RSS.
- **Rischi:** cold import e RAM. **Mitigazione:** persistenza, cache, limiti e
  configurazione separata.
- **Parallelizzabile:** no (dipende da P11 + benchmark). **Bloccante:** nessuno.

### P13 — Frontiera e ottimizzazione con Riskfolio-Lib (opzionale, R9)
- **Stato esecuzione:** ✅ backend completato — 28 Luglio 2026.
- **Decisione:** `portfolio_optimization` usa Riskfolio-Lib 7.0.1 in worker
  separato. Il backend G5 supporta portfolio/broker/asset-set; G6 migra lo scope
  broker a `portfolio + broker_ids`.
- **Capability:** min-risk, max-Sharpe, risk parity; historical/Ledoit-Wolf/OAS;
  bound globali; CLARABEL/SCS; frontiera e sensitivity opzionali.
- **Output:** pesi, rendimento/volatilità/Sharpe, contributi di rischio, vincoli,
  solver/status, frontier/sensitivity e metadata. Nessuna raccomandazione.
- **Semantica:** seleziona un universo di asset e costruisce una composizione
  ipotetica; non usa quantità/pesi posseduti e non è holdings-aware.
- **Frontend G6:** unica casa `Assets Global → Allocation`, con asset universe
  condiviso da Correlation/Scenarios. Main controls: strategy, covariance,
  min/max weight, run. `Advanced`: risk-free, solver, frontier, sensitivity,
  vincoli e metadata. Solver effettivo sempre visibile.
- **Escluso:** pannello P13 completo in Dashboard/Broker e qualunque wording di
  ribilanciamento/raccomandazione.

---

## 6. Test obbligatori

**Backend:** unit per ogni formula; calendario congiunto; target currency;
carried-forward prezzi; backward-filled FX; annualization factor; neutralità flussi
TWRR; `DataQualityReport`; comparison_asset; rolling beta con asset reale; active return;
tracking error; Information Ratio; drawdown comparato; comparison_asset uguale al primario;
comparison_asset a varianza nulla; insufficienza dati; controllo di sequenza/
riproducibilità; MC vs QMC su
casi noti; dimensioni/correlazioni; adapter QuantLib; serialize/deserialize input
subprocess; spawn isolation; timeout/error propagation; convergenza/stabilità; VaR/CVaR
(`CVaR≥VaR≥0`); PCTR; integration endpoint/service; smoke-test import librerie (P0).

**Frontend:** build+check; test componenti; broker→set asset; aggiunta manuale asset;
configurazione plugin; comparison_asset picker; pannello confronto (risk-free/asset);
apertura `PageSyncModal`; preselezione prezzi+FX; `onsynced`; loading; partial result;
warning; insufficient data; empty/error; responsive; dark/light; tooltip metodologici;
accessibilità; checklist manuale UI/UX.

**Benchmark:** single asset e portafoglio; 5/20/50 asset; 1k/10k/100k percorsi;
orizzonte 1/5/10 anni; MC/QMC QuantLib; tempo; memoria;
riproducibilità; convergenza; stabilità dei percentili; VaR/CVaR; costo IPC; spawn
startup; pool vs singolo.

---

## 7. Attività, dipendenze, critical path

Il piano distingue **due percorsi** che possono avanzare in parallelo.

**Percorso funzionale principale:**
`P1 (utility serie) → P5 (RiskAnalytic + AssetReturnSeries) → P6/P7 (UI) → P8/P9/P10`.

**Percorso librerie quantitative:**
`P0 (probe+installazione) → P11 (motore MC/QMC) → P12 (spawn) → P13 (frontiera)`.

**Parte subito (parallelo):** P0 (probe+install), P1 (utility), P2 (metadata) — indipendenti.

**Parallelizzabili:** i 3 plugin price-only di P4; lo spike simulazione (P11); P13 (dopo P5);
i test.

**Bloccanti:** P1 blocca P3/P4/P5/P9; P5 blocca P6/P7/P8/P9/P10; P0 blocca P11/P13;
P11 blocca P12.

**Dipendenze di P9 (confronto):** utility serie (P1) + metadata (P2) + `comparison_asset`
(P3) + funzioni comparative (Sharpe/beta/correlazione/drawdown da P4/P5) + componenti host
Asset/Dashboard/Broker (P7). Nessuna dipendenza artificiale.

**Spike obbligatori:** (1) probe API + installazione librerie in P0; (2) oracle
analitici QuantLib in P11; (3) benchmark worker count in P12.

**Rischi principali verificati:** costo SWIG/copia QMC; cold import Riskfolio;
RAM per worker; limiti Sobol/risorse. Compatibilità Python/container e solver sono
chiusi dai probe.

---

## 8. Questioni aperte residue

- tuning operativo del numero worker per installazione self-hosted;
- forma visuale finale di chart, frontier scatter, densità e responsive: validazione
  manuale utente durante G6;
- dettaglio DTO/file-path built-in del catalogo scenario, da congelare nella shared
  foundation entro i vincoli IA già approvati;
- suite backend globale da rilanciare dopo la chiusura del lavoro concorrente sul
  provider Borsa Italiana.

> QMCPy resta fuori dal piano; non è un fallback production.
>
> Placement P13 non è più aperto: `Assets Global → Allocation` è l'unica casa G6.

---

## Tracciabilità R0–R9 ↔ P0–P13

| Studio (analisi §8) | Piano |
|---|---|
| R0 contratto + `RiskResultMetadata` | P2 (+ contratto già scritto) |
| R1 `AssetReturnSeries` FX | P1 |
| R2 drawdown + rolling vol | P4 |
| R3 KPI storici scalari | P4 + P7 |
| R4 correlazione | P5 + P6 |
| R5 PCTR barre divergenti | P5 + P7 |
| R6 stress (hypothetical→historical) | P8 |
| R7 confronto risk-free / asset | **P9** (step dedicato al confronto completo) |
| R8 VaR/CVaR + Monte Carlo | P10 + P11 |
| R9 efficient frontier | P13 |
| (nuovo) probe + installazione librerie | P0 |
| (nuovo) parallelismo spawn | P12 |

---

## Riferimenti incrociati
- Contratto matematico: [`contract-phase01RiskMetricsMathematical.md`](./contract-phase01RiskMetricsMathematical.md)
- Analisi architetturale: [`analysis-phase01RiskModularityAndPlacement.md`](./analysis-phase01RiskModularityAndPlacement.md)
- Brainstorming UI: [`brainstorm-phase01RiskUiConcepts.md`](./brainstorm-phase01RiskUiConcepts.md)
- Review (Capitolo 4): [`review-risk-analysis-feedback.md`](./review-risk-analysis-feedback.md)
- Indice: [`README.md`](./README.md)

→ Piano implementativo:
[`plan-phase01RiskAnalysisImplementation.prompt.md`](./plan-phase01RiskAnalysisImplementation.prompt.md)
