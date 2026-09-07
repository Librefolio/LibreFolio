Tutte le dimensioni sono `token-equivalenti stimati` (`caratteri renderizzati / 4`) sul prompt finale copiabile dalla UI, mai token esatti né JSON canonico grezzo. I conteggi finali derivano da `summary.md`/`metrics.json` del run autorevole, non da run intermedi.

# Report Phase 0 — AI Export Task Adequacy Review V1

**Data**: 1 agosto 2026
**Run autorevole finale**: `real_prompt_probe/20260801T035128.653789Z` — 348/348 prompt, 0 fallimenti, commit `0fcfaa759de310f5c1a706d72007a52dca7145f1` (worktree dirty)
**Run baseline (comparatore adeguatezza)**: `real_prompt_probe/20260731T165707.644762Z` — 285/285 prompt, 0 fallimenti
**Run FX parziali**: 3M `targeted_partial_fx_probe/20260801T015950.619928Z`, 6M `…/20260801T015950.794939Z`, 1Y `…/20260801T015951.265250Z` — ciascuno 24/24, 0 fallimenti
**Artefatti di adeguatezza persistiti nel run finale**: `task_adequacy_baseline_reviews.json`, `task_adequacy_final_reviews.json`, `task_adequacy_comparison.json`, `task_adequacy_tables.md`
**Report architetturale precedente**: `report-phase00AiExportSemanticCompositionV1.md`
**Profilo**: `tuning-v2` · **Utente rappresentativo**: `marco` · **Catalogo**: V2 in place — **64 componenti, 32 dataset, 16 Analysis**, quattro `*.all_data` con contesti derivati esclusi
**Ambito**: valutazione dell'adeguatezza del contenuto di ciascuna Analysis rispetto al suo task; commit/cleanup/wiki/release **fuori scope**

> **Addendum post-review del 1 agosto 2026.** La validazione mirata `report-phase00AiExportPacAndCostEfficiencyValidationV1.md`, run `real_prompt_probe/20260801T072616.671347Z`, corregge la rubrica per input disponibili soltanto dall'utente e prova Cost Efficiency su Directa con fee reali. `portfolio.pac_planning` e `broker.cost_efficiency` sono promossi a **OPTIMAL**. La classificazione pubblica corretta è quindi **96 OPTIMAL / 0 SUFFICIENT / 0 INSUFFICIENT**. Le tabelle V1 sottostanti restano la fotografia storica del run da 348 prompt e non vengono retroattivamente mescolate con il run mirato.

> **Superseded per il catalogo pubblico V3.** La review corrente è
> `report-phase00AiExportTaskAdequacyReviewV2.md`, basata sul run
> `real_prompt_probe/20260804T155305.988711Z` e sul catalogo 8 Export Data +
> 13 Analysis. Questa V1 resta la baseline storica V2.

---

## 1. Executive summary

La domanda a cui risponde questo report non è «il prompt è ben formattato o compatto?» (già chiuso da `report-phase00AiExportSemanticCompositionV1.md` e dall'hardening pubblico), ma **«ogni Analysis raccoglie abbastanza dati — e non troppi off-task — per completare il proprio compito?»**. La valutazione è stata prodotta da un revisore che legge i **prompt realmente renderizzati** (non il JSON) delle **96 varianti** di Analysis (16 Analysis × {3M,1Y} × {compact,standard,full}), con la stessa rubrica su baseline e finale, salvando gli esiti come artefatti persistenti dentro il run finale.

**Esito complessivo (96 varianti):**

| Corpus | OPTIMAL | SUFFICIENT | INSUFFICIENT |
|---|---:|---:|---:|
| Baseline `…165707` | 48 | 48 | 0 |
| Finale `…035128` | **84** | **12** | **0** |

**Transizioni**: 36 `SUFFICIENT→OPTIMAL`, 48 `OPTIMAL→OPTIMAL`, 12 `SUFFICIENT→SUFFICIENT`. Nessun regresso; **nessuna Analysis pubblica è INSUFFICIENT** né lo è mai stata nel corpus misurato.

Le sole 12 varianti ancora SUFFICIENT appartengono a **due sole Analysis**: una dipende soprattutto da input utente e da una scelta di densità prodotto (`portfolio.pac_planning`), l'altra da fee non registrate a monte (`broker.cost_efficiency`).

- `portfolio.pac_planning` (6 varianti, score 84): gli input utente (budget, orizzonte, allocazione target, tolleranza al rischio) sono **intenzionalmente assenti e segnalati come domande**, non un difetto dati; residua un contesto tecnico di audit ancora un po' abbondante e l'assenza (opzionale) del drawdown subordinato;
- `broker.cost_efficiency` (6 varianti, score 77–81): le fee/commissioni **registrate** sono genuinamente assenti nei dati rappresentativi e sono correttamente dichiarate `unavailable` (non zero, `reason_code=fees_unavailable`); il task resta completabile con prudenza su turnover, trade count e ownership share.

Il salto di qualità deriva da **7 nuovi dataset** e **8 nuovi componenti** che colmano lacune di task diagnosticate a baseline: contesto **drawdown** nativo (Portfolio/Broker TWRR, Asset PRICE_ONLY), **timeline reddito datata**, **dimensioni di concentrazione + comparatore** di portafoglio, **turnover/fee** di efficienza di costo, **contesto di timing FX** su range osservato. In corso di rating qualitativo è stato inoltre trovato e corretto — **prima** del run finale audited — un difetto di **doppia scala percentuale** (percentuale già in scala moltiplicata ×100) su campi SUMMARY di concentrazione; l'audit del probe ora verifica anche le percentuali SUMMARY e chiude a `violations = 0`.

Dimensioni del corpus finale (da `summary.md`/`metrics.json`): 348 prompt (252 dati + 96 Analysis), 27.924.328 caratteri renderizzati totali, mediana prompt dati 6.774 e prompt Analysis 25.310 caratteri; 281 Light / 47 Medium / 20 Heavy (281+47+20 = 348), di cui 18 Very-Heavy (sottoinsieme di Heavy); `public_output_violations = 0`, `percentage_violations = 0`, `hhi_violations = 0`, `weight_violations = 0`, `unit_price_violations = 0`, `renderer_equivalence_violations = 0`; secret scan `passed`, source DB read-only.

---

## 2. Metodo e rubrica

**Unità di analisi.** 96 varianti = 16 Analysis × 2 periodi ({3M, 1Y}) × 3 detail ({compact, standard, full}). Il caso rappresentativo è deterministico (`marco`; portafoglio intero; broker con più posizioni e storia più lunga; un Asset a storia più lunga; una coppia FX a storia più lunga). Le quattro `*.all_data` sono escluse dalla matrice di tuning.

**Rating.** Ogni variante riceve una delle tre etichette:

- **INSUFFICIENT** — il task **non è completabile**: manca evidenza critica non recuperabile dal prompt, oppure il segnale utile è sepolto da dati fuori-task al punto da compromettere il compito.
- **SUFFICIENT** — il task è **completabile con prudenza**: l'evidenza core è presente, ma restano lacune non critiche o eccesso off-task. L'assenza di input che soltanto l'utente può fornire, o di dati non registrati dalla sorgente, **non è di per sé una penalità** quando il prompt identifica soltanto i gap materiali, distingue indispensabile/opzionale, supporta scenari condizionali e rappresenta correttamente `unavailable` senza inventare valori.
- **OPTIMAL** — il task è **pienamente supportato**: evidenza deterministica completa, nessuna lacuna materiale, eccesso trascurabile, limiti/coperture dichiarati.

**Assi 0–100.** Lo score è la somma di sei assi pesati (massimi osservati fra parentesi, somma 100):

| Asse | Peso | Cosa misura |
|---|---:|---|
| `deterministic_completeness` | 25 | presenza dei fatti deterministici richiesti dal contratto del task |
| `task_relevance` | 25 | quanto i dati inclusi servono davvero l'obiettivo (penalizza l'off-task) |
| `semantic_clarity` (`…_units`) | 15 | unità, provenienza, riferimenti pubblici, semantica non ambigua |
| `coverage_limits` | 15 | copertura, staleness, `omission_reasons`, missing-not-zero dichiarati |
| `density_information` | 10 | densità informativa vs volume (penalizza ridondanza/verbosità) |
| `additional_data_usability` | 10 | qualità del suggerimento «Altri dati LibreFolio» (localizzato, pertinente) |

**Bande operative**: **OPTIMAL 85–100**, **SUFFICIENT 60–84**, **INSUFFICIENT 0–59**. Nel corpus osservato gli score finali vanno da 77 a 93. Ogni giudizio cita le righe del prompt reso (`evidence_citations`), così la rubrica è ancorata all'output copiabile, non a intuizioni.

**Comparabilità.** Baseline e finale usano rubrica, caso rappresentativo, profilo e matrice identici: cambia solo la composizione backend fra i due run. `task_adequacy_comparison.json` normalizza gli score/rating delle Analysis FX (schema revisore leggermente diverso) su tutte le 96 varianti. L'addendum PAC/Cost successivo usa invece un run mirato con DB production evoluto: le dimensioni before/after sono descrittive, mentre la promozione deriva dalla revisione semantica e dalle evidenze runtime.

---

## 3. Problemi del baseline e rating

Nel baseline `…165707` (già post-cutover V2, 25 dataset) le 96 varianti erano **48 OPTIMAL + 48 SUFFICIENT + 0 INSUFFICIENT**: la composizione era già corretta dimensionalmente (nessuna Analysis finanziaria dominata dal dataset tecnico completo), ma **restavano lacune di task specifiche** che tenevano metà del corpus a SUFFICIENT. Le principali, dagli `missing_evidence` baseline:

- **`asset.position_review`** (SUFFICIENT 80–84): il compact rendeva **0 righe di limited-history** benché §3 del contratto le promettesse (mismatch contratto/payload); il **Portfolio Role** era chiesto ma solo il broker scope era fornito (nessun peso/percentuale di concentrazione data-backed); il **drawdown** non era nativo (solo min/max grezzi).
- **`broker.concentration_context`** (SUFFICIENT 79): mancavano le **dimensioni di concentrazione** per asset-type/settore/geografia/valuta e il **comparatore vs intero portafoglio** che l'obiettivo chiede esplicitamente.
- **`broker.cost_efficiency`** (SUFFICIENT 68–72): assenti le **fee** (solo `period_fees=null`/`0`) e ogni **denominatore di turnover/trade-count**, quindi i ratio di costo del contratto non erano calcolabili né inquadrabili.
- **`portfolio.income_review`** (SUFFICIENT 79–80): nessuna **timeline datata** del reddito registrato (solo aggregato per contributore) e nessun puntatore «Altri dati LibreFolio»; cedole future, yield e accrual restavano intenzionalmente fuori scope.
- **`portfolio.technical_breadth`** (SUFFICIENT 70–78): a livello dati la copertura era completa, ma la variante riceveva **l'intero dataset tecnico** (quota tecnica >98%, fino a ~602k token-eq a 1Y/full): densità e task-relevance crollavano sotto il volume.
- **`portfolio.rebalancing`** (OPTIMAL 88) e **`broker.review`** (SUFFICIENT 83–84): adeguate ma prive di una dimensione **drawdown/recovery** deterministica e con contesto tecnico ancora ridondante.

Le varianti già OPTIMAL a baseline (`asset.trend_analysis`, `fx.trend_review`, `fx.exposure_impact`, `portfolio.description`, `portfolio.fifo_review`, `portfolio.performance_attribution`, `broker.fifo_review`) lo sono rimaste. Le lacune sopra sono esattamente il target dei 7 dataset / 8 componenti aggiunti fra baseline e finale (§11).

---

## 4. Latest event e implementazione delle categorie

I **latest_events** sono la sintesi «ultimo evento rilevante per categoria»: la selezione (`_latest_category_events`, `technical_context.py:501-530`) tiene **al più un evento per coppia `(entity_id, signal_category)`**. Le categorie sono **plugin-owned**: derivano da `SignalPluginRegistry.get_plugin(signal_code).category.value` (`technical_context.py:455-460`), non da liste hard-coded nel renderer. Le categorie ammesse sono l'enum del plugin: `trend`, `momentum`, `volatility`, `volume`, `risk` (`backend/app/schemas/signals.py:100-106`). Ogni riga porta il proprio `signal_category` (`TechnicalContextEvent.signal_category`, `technical_context.py:235-246`) impostato da `_context_event_from_discrete` (`:463-476`), e viene attaccata come tabella `latest_events` sulla `TechnicalMarketContextPayload` (`:248-256`).

**Distinzione dai baseline flat.** A baseline la scheda per-Asset esponeva quattro colonne piatte `latest_event_{date,direction,key,signal}` (un solo ultimo evento globale). In finale sono **sostituite dalla tabella `latest_events`** una-riga-per-categoria: si evita di privilegiare arbitrariamente una singola categoria e si dichiara esplicitamente che è un **sottoinsieme di sintesi** dei medesimi eventi già presenti nella tabella eventi (duplicazione minima e intenzionale, non doppio conteggio). Nel corpus finale i `latest_events` compaiono ad es. su `asset.position_review` (2 righe su 2 categorie: momentum+trend), `broker.review` (12), `portfolio.rebalancing` (24), `portfolio.pac_planning` (24); sono `None`/assenti dove il task non usa una scheda per-Asset (FX, FIFO puri). La policy latest è **distinta** da quelle detailed/context/digest (§7): stessa sorgente di eventi discreti, regole di selezione diverse e non sovrapposte.

---

## 5. Drawdown: stato, formula e serie di dominio

Il drawdown è **implementato correttamente** e nativamente, delegato al Risk engine (nessuna matematica ricostruita nell'AI Export). La primitiva è il **peak-relative underwater**: `underwater_drawdown(values) = value / running_peak − 1.0` (`risk/metrics.py:200-205`). `drawdown_episodes` (`:259-379`) costruisce un wealth index dai rendimenti e ricava:

- **corrente**: `current_drawdown = min(0, underwater[last])`, `current_peak_date`, `current_drawdown_duration_days` (peak→ultima data se sott'acqua, altrimenti 0), `remaining_to_peak_ratio = max(0, −current/(1+current))`;
- **massimo (episodio più profondo)**: `maximum_drawdown = min(0, underwater[trough])`, `maximum_drawdown_peak_date`/`_trough_date`/`_recovery_date`, `maximum_drawdown_duration_days` (peak→recovery se recuperato, peak→ultima se aperto, 0 se assente), `maximum_drawdown_recovered_ratio = (wealth[ref]−trough)/(peak−trough)` clip [0,1];
- **stato di recovery**: `no_drawdown` / `recovered` / `open`; più `available_start/end`, `n_observations`, `coverage`.

**Serie per dominio** (`components/drawdown_context.py`, `risk/service.py`):

- **Asset** — nativo **PRICE_ONLY** (`calculation_basis=price_only_close`): `DrawdownPlugin` è ASSET-only e usa le sole chiusure (`signal_plugins/drawdown.py`), l'`AssetReturnSeries` ha `return_basis=PRICE_ONLY` di default (`schemas/risk.py`), e il componente Asset usa la **valuta nativa osservata** del prezzo (nessuna approssimazione in valuta target; `unavailable` se manca l'osservazione nativa).
- **Portfolio** — **TWRR** storico (`historical_twrr`): `PortfolioRiskScope(kind=PORTFOLIO, broker_ids=None)`, rendimenti da `_portfolio_twrr_returns`, **nessun percorso NAV grezzo**.
- **Broker** — **TWRR** storico ristretto ai **`broker_ids`** (`broker_ids=list(scope.broker_scope)`); stessa pipeline, nessun NAV grezzo.
- **FX** — **nessun drawdown FX pubblico**: non esiste dataset `fx.drawdown_context` (un tasso FX non è un valore di portafoglio); assenza verificata dal test di catalogo API.

**`asset.drawdown_recovery` resta differita**: esiste solo come *task contract* AI Export (`profiles/asset.py`: `task=AiExportTask.DRAWDOWN_RECOVERY`, `frontend_response_contract_id="asset.drawdown_recovery"`), **senza** pipeline di componente/dataset; il contesto canonico è `asset.drawdown_context`. È differita perché mancano episodi storici comparabili e un contratto di task dedicato implementato — quindi non è ancora esponibile in modo deterministico e anti-allucinazione.

**Output/plugin/file/copertura test** (Tabella D). Consumatori: `portfolio.rebalancing → portfolio.drawdown_context`, `broker.review → broker.drawdown_context`, `asset.position_review → asset.drawdown_context` (tutti optional). Nel corpus finale l'episodio Asset è, ad es., corrente `-3,2094%` / massimo `-4,1764%` (peak 2026/02/27, trough 2026/03/27), recovery `open`, recovered `23,1552%`, remaining `3,3158%`, coverage 100%, `n_obs` 253; su `broker.review` il drawdown è `status=partial` (warning `data_quality_degraded`: dati sorgente carried-forward), quindi provvisorio ma dichiarato.

### Tabella D — Implementazione drawdown (file / classe / funzione / input / output / semantica / copertura test)

| File | Classe/Funzione | Input | Output (campi) | Semantica | Copertura test |
|---|---|---|---|---|---|
| `services/risk/metrics.py` | `underwater_drawdown`, `drawdown_episodes`, `DrawdownEpisodeReport` | serie valori/rendimenti + `dates` + `baseline_date` | current/max drawdown, peak/trough/recovery date, durate, `recovered_ratio`, `remaining_to_peak_ratio`, `n_observations`, coverage | peak-relative `value/peak−1`; episodio più profondo; recovery `no_drawdown/recovered/open` | `test_services/test_risk_metrics.py` (6 test episodi) + `test_risk_signal_plugins.py` (vettore underwater) |
| `services/signal_plugins/drawdown.py` | `DrawdownPlugin`, `DrawdownParams` | prezzi `CLOSE` (`uses_prepared_asset_series`) | signal area `drawdown` in %, ASSET-only, ref `peak=0` | `underwater_drawdown(close)×100`, **price-only**, warmup ≥2 | `test_risk_signal_plugins.py` (`RISK_DRAWDOWN=-8.0`) |
| `services/risk_plugins/drawdown_summary.py` | `DrawdownSummaryAnalytic`, `DrawdownSummaryParams` | `require_primary_returns`, `baseline_date < dates[0]` | `RiskDrawdownOutput` (`calculation_basis`, `return_basis`) | delega a `drawdown_episodes`; basis `historical_twrr` se TWRR altrimenti `price_only_close` | `test_ai_export_components_drawdown_context.py` (pass-through TWRR) |
| `schemas/risk.py` | `RiskDrawdownOutput`, `RiskReturnBasis`, `RiskDrawdownRecoveryStatus` | campi episodio | 18 campi validati | `no_drawdown` vieta date/ratio; `recovered` esige recovery date; `open` la vieta; `AssetReturnSeries` default `price_only` | `test_schemas/test_risk_schemas.py` (4 test + assert `price_only`) |
| `services/ai_export/components/drawdown_context.py` | `DrawdownContextPayload`, `_build_portfolio/broker/asset_drawdown` | `RiskService.execute(…drawdown_summary)` | `status`/`reason_code` + ratio (current/max, peak/trough/recovery, durate, `recovered_ratio`, `remaining_to_peak_ratio`, `coverage_ratio`, `n_observations`) | ratio decimali interni; Portfolio `broker_ids=None`; Broker `broker_ids=scope`; Asset valuta nativa o `unavailable`; **no FX** | `test_ai_export_components_drawdown_context.py` (Portfolio/Broker/Asset) + `test_ai_export_dataset_analysis_catalogs.py` (wiring congelato) |
| `services/risk/service.py` | `RiskService.execute`, `_portfolio_twrr_returns` | scope inputs | `RiskExecutionContext.primary_return_basis` | `PORTFOLIO+HISTORICAL→TWRR` (no NAV); Broker filtrato per `broker_ids`; Asset PRICE_ONLY | `test_services/test_risk_analytics.py`, `test_api/test_risk_api.py` |

---
## 6. Semantica dei conteggi di universo

L'universo tecnico Portfolio/Broker distingue quattro conteggi, tutti dichiarati e non confondibili (`technical_shared.py`, `technical_payloads.py`):

- **`period_position_leg_count`** — leg di contribuzione `(broker_id, asset_id)` del periodo, **prima** dell'eligibilità, **inclusi i leg interamente venduti nel periodo**; non è un conteggio di asset unici (`technical_shared.py:434-445`).
- **`period_contributor_asset_count`** — asset unici attraverso tutti i leg pre-eligibilità, **broker-dedotti**, inclusi gli asset venduti nel periodo (`:448-460`).
- **`eligible_asset_count`** — asset unici **attualmente detenuti** a fine periodo con valore non nullo, broker-dedotti (`technical_payloads.py:510-529`).
- **`covered_asset_count`** — sottoinsieme eligible con **almeno un Signal incluso** / copertura tecnica classificabile (`:530-546`).

La **dedup multi-broker** avviene nell'universo eligible (`{position.asset_id}` sull'end-holding): un asset detenuto presso più broker conta **una volta** fra gli eligible, ma i suoi **leg per-broker contano più volte** nei conteggi di periodo. Ecco perché i conteggi di periodo (es. **20** leg / **18** contributor) possono **superare** l'unique-held all-time (**17**): i conteggi di periodo includono leg interamente venduti nel periodo e leg broker duplicati (`duplicate_asset_legs=2`), mentre eligible conta solo il posseduto corrente a valore non nullo.

Il `run_manifest.json` documenta la differenza fra etichette **all-time** e **runtime di periodo** e ammonisce a non confrontarle (`inventory_methods`). Per `marco`: all-time `position_legs=19`, `unique_held_assets=17`, `priced_assets=17`, `fifo_lot_count=47`; runtime di periodo `runtime_period_position_leg_count=20`, `runtime_period_contributor_asset_count=18`, `runtime_period_eligible_asset_count=17`, `runtime_period_covered_asset_count=12`. I conteggi runtime **dipendono dal periodo** (finestra 3M vs 1Y); i 5 asset eligible non coperti (17→12) sono dichiarati con `omission_reasons`/staleness.

---

## 7. Eventi detailed / context / latest / digest

Le quattro derivazioni di evento partono dalla **stessa** sorgente di eventi discreti (`signal_results_to_discrete_events`) ma applicano policy distinte e non sovrapposte:

- **DETAILED** (`full_technical_digest`, `*.states_events`): stream tecnico completo time-bucketed + `SELECTION` per-annotazione, con troncamento dichiarato. Usato dalle Analysis tecniche esplicite: `asset.trend_analysis` esporta **239** righe a 1Y e **105** a 3M (min-20/annotazione + cap 30 giorni recenti).
- **CONTEXT** (allowlist strutturale per-asset, con cap): `broker.review` (`context_latest_structural_per_asset_v1`, **44**), `portfolio.rebalancing` (`synthetic`, **48**), `asset.position_review` (`position_market_context`, **7**). Cap: universo ≤4/entità, `asset_position_context_v1` ≤12, `fx_market_context_v1` ≤8 (`technical_context.py`).
- **LATEST** (§4): ≤1 evento per `(entità, categoria)`; es. `asset.position_review` 2, `broker.review` 12, `portfolio.rebalancing`/`pac_planning` 24.
- **DIGEST** (`all_last_30d_else_latest_per_annotation_v1`): raggruppa per `(signal_code, key)` con «tutti gli eventi negli ultimi 30 giorni, altrimenti l'ultimo per annotazione»; `portfolio.description` e `portfolio.technical_breadth` rendono **7 gruppi** su **131** eventi sottostanti.

Le costanti di selezione sono `EVENT_SELECTION_RECENT_WINDOW_DAYS = 30` e `EVENT_SELECTION_MINIMUM_LATEST = 20` (`technical_shared.py:138-139`). Il probe misura ciascun tipo separatamente: `detailed_event_rows`, `context_event_rows`, `latest_event_rows`, `latest_event_category_count`, `event_digest_group_count`, `event_digest_underlying_event_count`, oltre a `detected_event_count`/`exported_event_count`. `fx.trend_review` e `fx.conversion_timing` usano gli eventi detailed del dataset completo `fx.market_technical`; `fx.exposure_impact` usa invece gli eventi context/latest di `fx.market_context`.

### Tabella F — Metriche evento per tipo (detail=full; 1Y / 3M)

| Analysis | Modalità evento | Detailed 1Y/3M | Context 1Y/3M | Latest 1Y/3M | Digest 1Y/3M |
|---|---|---:|---:|---:|---:|
| `asset.trend_analysis` | full_technical_digest | 239/105 | 0/0 | 0/0 | 0g·0u/0g·0u |
| `asset.position_review` | position_market_context + latest per categoria | 0/0 | 7/6 | 2/2 | 0g·0u/0g·0u |
| `broker.review` | context_latest_structural_per_asset_v1 | —/— | 44/44 | 12/12 | —/— |
| `portfolio.rebalancing` | synthetic (context+latest) | 0/0 | 48/48 | 24/24 | 0g·0u/0g·0u |
| `portfolio.pac_planning` | aggregated (latest) | 0/0 | 0/0 | 24/24 | 0g·0u/0g·0u |
| `portfolio.description` | digest | 0/0 | 0/0 | 0/0 | 7g·131u/7g·131u |
| `portfolio.technical_breadth` | digest | 0/0 | 0/0 | 0/0 | 7g·131u/7g·131u |
| `broker.concentration_context` | aggregate_breadth_only | —/— | 0/0 | —/— | —/— |
| `fx.trend_review`, `fx.conversion_timing` | eventi nel `fx.market_technical` completo (non nel contesto semantico) | ~227 (1Y, full technical) | — | — | — |
| `fx.exposure_impact` | `fx.market_context` + latest per categoria | 0/0 | 7/6 | 2/2 | 0g·0u/0g·0u |
| `broker.cost_efficiency`, `broker.fifo_review`, `portfolio.fifo_review`, `portfolio.income_review`, `portfolio.performance_attribution` | none/absent (task non-event) | — | — | — | — |

---

## 8. Copertura e pesi

Il denominatore dei pesi è **l'esposizione lorda assoluta**: `compute_nav_weights` somma `abs(position.end_value)` per asset e divide per il totale lordo (`technical_shared.py:462-480`). Da qui:

- **`eligible_portfolio_weight_ratio`** = somma dei pesi lordi assoluti degli asset eligible; **`covered_portfolio_weight_ratio`** = somma sui soli covered; **`covered_weight_ratio` = covered/eligible** (`technical_payloads.py:535-546`).
- **`portfolio_role.portfolio_weight_percent`** dell'Asset ha denominatore **`gross_absolute_open_position_value`**: «valore lordo assoluto della posizione aperta dell'asset unico / esposizione lorda eligible» (`asset_payloads.py`, `asset_core._build_portfolio_role`). Es. `asset.position_review` = **6,8811%**.
- **Conteggio ≠ peso**: il conteggio è di asset broker-dedotti; il peso è quota di esposizione lorda assoluta. Un asset piccolo e uno grande contano 1 ciascuno ma pesano diversamente; la quota di universo coperto (12/17 asset) e la quota di **peso** coperto sono due riconciliazioni distinte.
- Il **peso tecnico normalizzato per Signal** (`technical_normalized_weight_ratio`) è normalizzato **dentro l'insieme coperto di ciascun Signal**, non globalmente: due Signal con coperture diverse hanno denominatori diversi.

I riferimenti sono sempre **pubblici**: i nomi grezzi dei ratio (`portfolio_weight_ratio`, `covered_weight_ratio`, `eligible_portfolio_weight_ratio`, `coverage_ratio`, `return_*_ratio`, …) sono vietati nell'output reso e resi come percentuali; l'audit del probe finale conta **1.506 weight_checks con 0 violazioni**, **1.380 unit_price_checks / 0**, **54 hhi_checks / 0**.

---

## 9. Storia FX parziale 3M / 6M / 1Y

I tre probe FX parziali (24/24 ciascuno) usano una coppia la cui **storia sorgente inizia il 2026/04/30** (66 osservazioni reali fino al 2026/07/30 + 27 backward-fill, snapshot 2026/07/31). Il comportamento è **fail-open con warning**: la finestra osservata è la stessa nei tre casi, cambiano solo la copertura calendario e i flag di parzialità rispetto al periodo richiesto.

- **3M** (richiesta 93 gg, 2026/04/30→2026/07/31): coperta **100%**, `complete=true`, `is_partial_history=false`, `reason_code=null`; **success senza warning**.
- **6M** (richiesta 182 gg, 2026/01/31→2026/07/31): coperta **51,0989%** (93/182 gg), `complete=false`, `is_partial_history=true`, `reason_code=insufficient_source_history`, `partial_history_reason=source_history_starts_after_period_start`; **success con warning**.
- **1Y** (richiesta 366 gg, 2025/07/31→2026/07/31): coperta **25,4098%** (93/366 gg), stessi flag/ragioni del 6M; **success con warning**.

I **Signal** sono trattati per-istanza e sono **identici nei tre periodi** (la finestra disponibile non cambia): **10/12 inclusi come PARTIAL** (`incomplete_warmup`: bollinger_20_2, ema_20, ema_50, kama_20, macd_12_26_9, ppo_12_26_9, roc_20, rsi_14, sma_50, stoch_rsi_14_3) e **2/12 omessi** (`ema_200`, `sma_200`) con `insufficient_history` (minimo 200 punti > **93 input giornalieri utilizzabili**, 66 osservati + 27 backward-filled). L'invariante **no-future** è preservato (`missing_price_policy`: ultima osservazione on-or-before la data richiesta, mai un prezzo futuro).

La **posizione nel range osservato NON è un percentile**: `range_position_percent = 31,6279%` con `range_position_unavailable_reason = null`; min osservato 1,134 (2026/06/24), max 1,177 (2026/05/07); `distance_to_min_percent = 1,1993%`, `distance_to_max_percent = 2,5619%` (denominatori non ancora uniformati — v. §19). I ritorni/volatilità osservati sono presenti: `return_1m_percent = 0,817%`, `return_3m_percent = −2,3735%`, `return_period_percent = −1,9313%`, `daily_return_volatility_percent = 0,3218%`. Questi valori sono identici nei tre periodi perché calcolati sulla sola finestra osservata (i giorni richiesti antecedenti al 2026/04/30 non esistono, quindi non producono né rate né posizione fittizia).

### Tabella E — FX storia parziale (artefatti reali, nessun numero inventato)

| Voce | 3M `…619928Z` | 6M `…794939Z` | 1Y `…265250Z` |
|---|---|---|---|
| Periodo richiesto | 2026/04/30→2026/07/31 (93 gg) | 2026/01/31→2026/07/31 (182 gg) | 2025/07/31→2026/07/31 (366 gg) |
| Periodo disponibile | 2026/04/30→2026/07/31 | 2026/04/30→2026/07/31 | 2026/04/30→2026/07/31 |
| Coverage | **100%** (`complete=true`) | **51,0989%** (`complete=false`) | **25,4098%** (`complete=false`) |
| Osservate / backfilled | 66 / 27 | 66 / 27 | 66 / 27 |
| Signal inclusi (PARTIAL) | 10/12 (`incomplete_warmup`) | 10/12 (`incomplete_warmup`) | 10/12 (`incomplete_warmup`) |
| Signal omessi | 2/12 (`ema_200`,`sma_200`) | 2/12 (`ema_200`,`sma_200`) | 2/12 (`ema_200`,`sma_200`) |
| Ragione omissione | `insufficient_history` (min 200 > 93 input utilizzabili) | idem | idem |
| `is_partial_history` / reason | false / `null` | true / `source_history_starts_after_period_start` | true / `source_history_starts_after_period_start` |
| Stato / warning | success, nessun warning | success, warning `insufficient_source_history` | success, warning `insufficient_source_history` |
| No-future | rispettato | rispettato | rispettato |

---
## 10. Additional Data e localizzazione

Ogni `AnalysisSpec` dichiara una lista esplicita di `AdditionalExportSuggestion` (anche vuota). Il frontend rende, per ogni suggerimento non già incluso: **label pubblica localizzata**, contenuto, motivo, **percorso UI localizzato**, label Export Data, **periodo/detail consigliati** e necessità (tutte `optional` in V2), con il dataset ID **solo tra parentesi** come riferimento tecnico. I testi sono in **EN/IT/FR/ES** (`frontend/src/lib/i18n/{en,it,fr,es}.json`, chiavi `aiExport.additionalData.*` e `aiExport.dataset.*`). Il **technical completo resta selezionabile**: le Analysis che ne hanno bisogno lo indicano come approfondimento opzionale, non lo ricevono inline.

Miglioramenti rispetto al baseline:

- **`portfolio.income_review`**: da «nessun suggerimento» a un puntatore **`portfolio.fifo` (1Y, Standard)** — esattamente la lacuna baseline (`additional_data_usability` → `good`).
- **`portfolio.technical_breadth`** (`excellent`): la **Technical Breadth** ora fornisce inline il **riepilogo aggregato** (`technical_summary`: coverage + breadth pesata/non pesata + digest categorizzato) e offre come Additional Data **`portfolio.technical` (Full)** + `portfolio.performance_flows`. La profondità tecnica **non è ridotta globalmente**: è spostata dietro un'escalation esplicita e localizzata.
- **`portfolio.description`** (`excellent`): `portfolio.technical` (3M Standard) + `portfolio.fifo`.
- **`broker.cost_efficiency`**: offre `broker.fifo`; non offre un export di fee itemizzate perché **le fee non esistono a monte** (non è un dataset del catalogo).

La **Technical Breadth** è dunque il caso paradigmatico della strategia: *summary aggregato inline + technical completo come Additional Data*, che porta la variante da SUFFICIENT (dominata dal volume) a OPTIMAL senza perdere accesso ai dati grezzi.

---

## 11. Componenti/dataset nuovi e riusati, dati aggiunti e rimossi

Fra baseline (`…165707`: 56 componenti / 25 dataset) e finale (`…035128`: **64 componenti / 32 dataset**) sono stati aggiunti **8 componenti** e **7 dataset**, tutti mirati alle lacune di task del §3. Nessun ricalcolo: i componenti drawdown delegano a `RiskService.execute`, i componenti di contesto riusano i resource bundle memoizzati.

**Dati aggiunti** (per Analysis): episodio drawdown deterministico (`asset.position_review`, `portfolio.rebalancing`, `broker.review`); **dimensioni di concentrazione** (type/settore/geografia/valuta) + **comparatore** vs intero portafoglio (`broker.concentration_context`, `broker.review`); **turnover/trade-count/ownership share** e stato fee missing-not-zero (`broker.cost_efficiency`); **timeline reddito datata** (`portfolio.income_review`); **range osservato/ritorni/volatilità** FX e storia parziale (`fx.conversion_timing`); `portfolio_role.portfolio_weight_percent` data-backed; `latest_events` per categoria e `signal_category` sugli eventi; limited-history compact 0→3 righe.

**Dati rimossi/superati**: le colonne piatte `latest_event_{date,direction,key,signal}` (sostituite dalla tabella `latest_events`); il conteggio ambiguo `considered_*` è stato separato in leg/contributor/eligible/covered per Portfolio/Broker e selected/eligible/covered per Asset/FX; per `portfolio.technical_breadth` la **history tecnica per-asset grezza** (4.752–12.306 righe) e gli **eventi detailed** (1.308–2.844 righe) sono usciti dal percorso inline, portando ~602k → **4.490** token-eq e spostando il technical completo su Additional Data. Le quattro `*.all_data` mantengono soltanto i propri `source_specs` completi e **escludono tutti i contesti derivati**: Portfolio esclude summary/snapshot/comparison/drawdown/income; Broker summary/comparison/drawdown/concentration/cost; Asset position/drawdown; FX market/timing. Il manifest finale li elenca tutti in `excluded_semantic_projections` (14 dataset derivati, 126 prompt nella coorte nuova).

### Tabella G — Mattoncini nuovi e riusati

| Mattoncino | Tipo | Stato | Ruolo | Consumatori |
|---|---|---|---|---|
| `portfolio.drawdown_summary` | componente | **nuovo** | drawdown TWRR di portafoglio (via Risk) | `portfolio.drawdown_context` |
| `broker.drawdown_summary` | componente | **nuovo** | drawdown TWRR broker (`broker_ids`) | `broker.drawdown_context` |
| `asset.drawdown_summary` | componente | **nuovo** | drawdown Asset PRICE_ONLY nativo | `asset.drawdown_context` |
| `broker.concentration_context` | componente | **nuovo** | HHI + allocazioni per type/settore/geo/valuta | `broker.concentration_evidence` |
| `broker.concentration_comparison` | componente | **nuovo** | comparatore broker vs intero portafoglio | `broker.concentration_evidence` |
| `broker.cost_efficiency` | componente | **nuovo** | turnover/trade-count/ownership + fee missing-not-zero | `broker.cost_efficiency_evidence` |
| `portfolio.income_timeline` | componente | **nuovo** | timeline reddito datata registrata | `portfolio.income_evidence` |
| `fx.timing_context` | componente | **nuovo** | range osservato/ritorni/volatilità + storia parziale | `fx.conversion_timing_context` |
| `asset/broker/portfolio.drawdown_context` | dataset | **nuovo** (3) | esposizione contesto drawdown | `position_review`, `broker.review`, `rebalancing` |
| `broker.concentration_evidence` | dataset | **nuovo** | evidenza di concentrazione | `broker.concentration_context` |
| `broker.cost_efficiency_evidence` | dataset | **nuovo** | evidenza efficienza di costo | `broker.cost_efficiency` |
| `portfolio.income_evidence` | dataset | **nuovo** | evidenza reddito datata | `portfolio.income_review` |
| `fx.conversion_timing_context` | dataset | **nuovo** | contesto timing FX | `fx.conversion_timing` |
| `*.technical_coverage`, `*.asset_market_context`, `*.context_events`, `*.event_digest`, `*.position_market_context`, `*.market_summary`, `*.technical_breadth` | componenti | riusati (V1) | contesto/copertura tecnica semantica | dataset semantici V1 |
| `*.overview`, `*.performance_flows`, `*.fifo`, `*.direct_exposure` | componenti | riusati invariati | fatti finanziari/FIFO/esposizione | Analysis finanziarie |
| `TechnicalUniverseBundle`, `PriceResultsResource`, `FxTechnicalBundle`, `FxRateSeriesResource`, metadata `SignalPlugin`, `signal_results_to_discrete_events`, `RiskService.execute` | risorse/engine | riusati (no ricalcolo) | universo/prezzi/Signal/eventi/rischio memoizzati | tutti i nuovi componenti |

---
## 12. Valutazione delle 16 Analysis

Ogni paragrafo risponde in forma sintetica alle domande di adeguatezza (evidenza deterministica, rilevanza al task, eccesso off-task, drawdown, coverage/limiti, Additional Data), evitando di ripetere le domande verbatim; il dettaglio numerico è in Tabella B (aggregato) e Tabella A (per variante).

**Portfolio**

- **`portfolio.description`** — OPTIMAL (med 90). `overview + performance_flows + technical_summary` coprono composizione, cassa, capitale, performance, concentrazione e breadth categorizzata (digest 7g/131u). Eccesso lieve: la matrice per-signal è più ricca del necessario per un task «conciso». Additional Data: technical Full + FIFO. Nessuna lacuna materiale.
- **`portfolio.performance_attribution`** — OPTIMAL (88,5). Contributori e allocazioni completi; manca solo il dettaglio lotto realizzato, correttamente offerto come `portfolio.fifo` opzionale. Nessuna tecnica; stabile.
- **`portfolio.income_review`** — OPTIMAL (86,5; era SUFFICIENT). La **timeline reddito datata** (`income_evidence`) chiude la lacuna baseline e rende derivabili timing e totali per Asset; lo yield non è direttamente fornito e richiede una semantica di denominatore esplicita. Residuo: serie NAV-bucket e schema contributor larghi, per lo più off-task. Additional Data: FIFO.
- **`portfolio.fifo_review`** — OPTIMAL (86,5). `overview + fifo` coprono lotti aperti/parziali/chiusi/custody; manca un rollup aggregato realizzato/non-realizzato (derivabile). `detail_level` è **no-op** (compact==full byte-identici).
- **`portfolio.pac_planning`** — **SUFFICIENT** (84). Gli input utente (budget/orizzonte/target/tolleranza) sono assenti per contratto (non difetto); resta tecnica di audit abbondante (~27–35%) e manca il drawdown subordinato. È l'unica leva verso OPTIMAL (§15).
- **`portfolio.rebalancing`** — OPTIMAL (90,5). Gap di allocazione + contesto per-asset + **drawdown/recovery** ora presenti; residuo NAV-bucket tangenziale e boilerplate `semantic_description` ripetuto. VaR/CVaR forward assenti (fuori scope deterministico).
- **`portfolio.technical_breadth`** — OPTIMAL (**93**, massimo del corpus; era SUFFICIENT 74,5). Summary aggregato + digest categorizzato; il volume crolla (~602k→4,5k token-eq) senza perdere il deliverable di breadth; 5/17 asset non coperti dichiarati; `detail_level` no-op. Technical completo come Additional Data.

**Broker**

- **`broker.review`** — OPTIMAL (86,5; era SUFFICIENT). Holdings/performance/costi/FIFO + **drawdown** + concentrazione; il drawdown è `status=partial` (dati carried-forward) quindi provvisorio; tecnica secondaria ancora ~31–38%.
- **`broker.concentration_context`** — OPTIMAL (88; era SUFFICIENT). **Dimensioni** (type/settore/geo/valuta) + **comparatore** vs intero portafoglio risolvono la lacuna baseline; residuo bucket «Unknown» dichiarati (geo 4,25% / settore 4,14%). Il defect x100 su `concentration_comparison` è **corretto** e verificato dall'audit.
- **`broker.cost_efficiency`** — **SUFFICIENT** (77–81). Turnover/trade-count/ownership share presenti; le **fee registrate sono genuinamente assenti** (`fees.status=unavailable`, `reason_code=fees_unavailable`), quindi i ratio sono null ma **missing-not-zero**; la serie NAV-bucket resta inclusa come denominatore di `fees_to_average_nav` (però null). Task completabile con prudenza (§15).
- **`broker.fifo_review`** — OPTIMAL (85,5). Lotti completi; i 5 gruppi economic-duplicate e gli stati DEGRADED non sono evidenziati come nota di qualità; `detail_level` identico.

**Asset**

- **`asset.position_review`** — OPTIMAL (91; era SUFFICIENT). Posizione/P&L/FIFO + **`portfolio_role`=6,8811%** + tecnica mirata + **drawdown PRICE_ONLY** + limited-history compact 0→3: tutte le 5 lacune baseline chiuse; residuo atr_14/bollinger point-only nel summary (la trajectory `natr_14_percent` è presente).
- **`asset.trend_analysis`** — OPTIMAL (89,5; invariato). Tecnica completa (239 eventi a 1Y, Signal e history completi); residuo: nessuna materiality-tiering sugli eventi micro (delegata al modello) e `portfolio_role` presente ma non usato dall'obiettivo trend.

**FX**

- **`fx.exposure_impact`** — OPTIMAL (**92**, top FX). L'esposizione netta base/quote è ora sintetizzata (finding ~zero-USD esplicito); residuo: tabella 21-leg + directory 17 asset ridondanti rispetto al netto.
- **`fx.conversion_timing`** — OPTIMAL (90; era SUFFICIENT). Range osservato/ritorni/volatilità (`timing_context`) + tecnica; residuo: doppia copertura `market_technical`+`timing_context` e denominatori di range da uniformare (§19).
- **`fx.trend_review`** — OPTIMAL (90; invariato). Signal/history/eventi completi; residuo: volume full (~40,9k token-eq) e 227 eventi oltre le «transizioni materiali».

### Tabella B — Aggregato per Analysis (16 righe)

| Analysis | Worst | Median | Min | Max | Insuf. | Suff. | Optim. | Dato mancante principale | Eccesso principale | Raccomandazione finale |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|
| `asset.position_review` | OPTIMAL | 91 | 89 | 91 | 0 | 0 | 6 | atr_14/bollinger point-only nel summary (natr trajectory presente) | latest_events (2) sottoinsieme per-categoria degli eventi | Ship as-is; opz.: atr/bollinger in history; nota su latest_events |
| `asset.trend_analysis` | OPTIMAL | 89.5 | 89 | 90 | 0 | 0 | 6 | nessuna materiality-tiering sugli eventi micro | portfolio_role presente ma non usato dall obiettivo trend | Ship as-is; opz.: tiering eventi; rimuovere portfolio_role dal trend |
| `broker.concentration_context` | OPTIMAL | 88 | 88 | 88 | 0 | 0 | 6 | nessuno stream eventi/history per-asset (by design) | matrice per-signal (20) + per-entita (12) verbosa | Ridurre bucket Unknown; collassare i 3 detail; defect x100 corretto |
| `broker.cost_efficiency` | SUFFICIENT | 79 | 77 | 81 | 0 | 6 | 0 | fee/tax registrate non disponibili a monte; nessun benchmark peer | serie NAV-bucket settimanale (29-75 righe) con ratio null | Mantenere missing-not-zero; downsample NAV quando fee n/d |
| `broker.fifo_review` | OPTIMAL | 85.5 | 85 | 86 | 0 | 0 | 6 | nessun rollup aggregato realizzato/non-realizzato | allocation_concentration duplica lievemente le holdings | Aggiungere rollup; evidenziare 5 duplicati economici/DEGRADED; detail no-op |
| `broker.review` | OPTIMAL | 86.5 | 86 | 87 | 0 | 0 | 6 | drawdown status=partial (carried-forward), provvisorio | coverage/breadth tecnica (~31-38%) secondaria | Risolvere drawdown partial; trim tecnica secondaria a compact |
| `fx.conversion_timing` | OPTIMAL | 90 | 89 | 90 | 0 | 0 | 6 | nessuna task-critical; lieve ridondanza market_technical/timing_context | doppia copertura range/ritorni; full ~42,7k token-eq | Uniformare denominatori di range; ridurre volume market_technical |
| `fx.exposure_impact` | OPTIMAL | 92 | 91 | 92 | 0 | 0 | 6 | nessuna task-critical | tabella 21-leg ridondante col netto | Opz.: condensare la tabella 21-leg; localizzare i flag |
| `fx.trend_review` | OPTIMAL | 90 | 87 | 91 | 0 | 0 | 6 | nessuna task-critical | 12 indicator histories + 227 eventi (1Y); full ~40,9k token-eq | Opz.: cap eventi a transizioni materiali; ridurre ridondanza full |
| `portfolio.description` | OPTIMAL | 90 | 89 | 91 | 0 | 0 | 6 | 5/17 asset non coperti (dichiarati) | matrice per-signal ricca per un task conciso | Demote matrice 20-signal; mantenere per-entita + digest |
| `portfolio.fifo_review` | OPTIMAL | 86.5 | 86 | 87 | 0 | 0 | 6 | nessun contesto performance (offerto come Additional Data) | detail_level no-op (compact==full); .code valuta ripetuto | Rendere detail_level significativo; collassare .code valuta |
| `portfolio.income_review` | OPTIMAL | 86.5 | 86 | 87 | 0 | 0 | 6 | yield per-asset non fornito (derivabile dalla timeline) | serie NAV-bucket e schema contributor larghi | Togliere NAV-bucket; opz. colonna yield per-asset |
| `portfolio.pac_planning` | SUFFICIENT | 84 | 84 | 84 | 0 | 6 | 0 | nessuna dimensione drawdown/rischio subordinata | latest_events (24) + NAV-bucket + matrice coverage (~27-35% tec.) | Demote coverage matrix; estendere drawdown subordinato -> OPTIMAL |
| `portfolio.performance_attribution` | OPTIMAL | 88.5 | 88 | 89 | 0 | 0 | 6 | dettaglio lotto realizzato via portfolio.fifo opzionale | bucket con colonne null (innocue); cash loosely tied | Nessuna modifica richiesta |
| `portfolio.rebalancing` | OPTIMAL | 90.5 | 90 | 91 | 0 | 0 | 6 | VaR/CVaR forward assenti (drawdown gap risolto) | NAV-bucket tangenziale; boilerplate semantic_description; matrice coverage | Collassare semantic_description; demote coverage matrix; opz. VaR/CVaR |
| `portfolio.technical_breadth` | OPTIMAL | 93 | 93 | 93 | 0 | 0 | 6 | 5/17 asset non coperti (dichiarati) | matrice per-signal (20) + per-entita (17) granulari; detail no-op | Rendere detail_level significativo o nasconderlo; allineare wording §8 |

---

## 13. Valutazione di tutte le 96 varianti

La Tabella A elenca tutte e 96 le varianti. Le colonne **numeriche** (Token-eq, Quota tecnica, History, Ev.dett., Digest, Score, Rating) sono **per-variante** ed esatte dagli artefatti; le colonne **qualitative** (Obiettivo task, Coverage, Evidenza mancante/eccesso, Modifica raccomandata) sono in **compattazione a livello di Analysis** (pressoche identiche fra i 6 detail/periodo di ogni Analysis) — aggregazione dichiarata per leggibilita. Token-eq = `token-equivalenti stimati` arrotondati; le quote e le percentuali usano la virgola decimale.

### Tabella A — Per variante (96 righe)

| Analysis | Variante | Obiettivo task | Ev. rich. | Dataset correnti | Comp. | Token-eq | Quota tec. | History | Ev.dett. | Digest g/u | Coverage | Evidenza mancante | Evidenza in eccesso | Drawdown | Additional | Score | Rating | Modifica raccomandata |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---:|---|---|
| `asset.position_review` | 3M/compact | Rivedere posizione singolo Asset: qty/valore/costo/P&L/FIFO/ruolo, tecnica mirata, drawdown, limiti | 8 | overview+position_performance+position_context+drawdown_context | 11 | 3892 | 25,7% | 3 | 0 | 0/0 | 1 Asset (BTP); 18/20 Signal ok (MFI/OBV n/d); FIFO+P&L completi; drawdown PRICE_ONLY -3,21%/max -4,18% | atr_14/bollinger point-only nel summary (natr trajectory presente) | latest_events (2) sottoinsieme per-categoria degli eventi | alto | buono | 89 | OPTIMAL | Ship as-is; opz.: atr/bollinger in history; nota su latest_events |
| `asset.position_review` | 3M/standard | Rivedere posizione singolo Asset: qty/valore/costo/P&L/FIFO/ruolo, tecnica mirata, drawdown, limiti | 8 | overview+position_performance+position_context+drawdown_context | 11 | 3947 | 26,7% | 6 | 0 | 0/0 | 1 Asset (BTP); 18/20 Signal ok (MFI/OBV n/d); FIFO+P&L completi; drawdown PRICE_ONLY -3,21%/max -4,18% | atr_14/bollinger point-only nel summary (natr trajectory presente) | latest_events (2) sottoinsieme per-categoria degli eventi | alto | buono | 91 | OPTIMAL | Ship as-is; opz.: atr/bollinger in history; nota su latest_events |
| `asset.position_review` | 3M/full | Rivedere posizione singolo Asset: qty/valore/costo/P&L/FIFO/ruolo, tecnica mirata, drawdown, limiti | 8 | overview+position_performance+position_context+drawdown_context | 11 | 4054 | 28,7% | 12 | 0 | 0/0 | 1 Asset (BTP); 18/20 Signal ok (MFI/OBV n/d); FIFO+P&L completi; drawdown PRICE_ONLY -3,21%/max -4,18% | atr_14/bollinger point-only nel summary (natr trajectory presente) | latest_events (2) sottoinsieme per-categoria degli eventi | alto | buono | 91 | OPTIMAL | Ship as-is; opz.: atr/bollinger in history; nota su latest_events |
| `asset.position_review` | 1Y/compact | Rivedere posizione singolo Asset: qty/valore/costo/P&L/FIFO/ruolo, tecnica mirata, drawdown, limiti | 8 | overview+position_performance+position_context+drawdown_context | 11 | 3948 | 26,6% | 3 | 0 | 0/0 | 1 Asset (BTP); 18/20 Signal ok (MFI/OBV n/d); FIFO+P&L completi; drawdown PRICE_ONLY -3,21%/max -4,18% | atr_14/bollinger point-only nel summary (natr trajectory presente) | latest_events (2) sottoinsieme per-categoria degli eventi | alto | buono | 89 | OPTIMAL | Ship as-is; opz.: atr/bollinger in history; nota su latest_events |
| `asset.position_review` | 1Y/standard | Rivedere posizione singolo Asset: qty/valore/costo/P&L/FIFO/ruolo, tecnica mirata, drawdown, limiti | 8 | overview+position_performance+position_context+drawdown_context | 11 | 4002 | 27,5% | 6 | 0 | 0/0 | 1 Asset (BTP); 18/20 Signal ok (MFI/OBV n/d); FIFO+P&L completi; drawdown PRICE_ONLY -3,21%/max -4,18% | atr_14/bollinger point-only nel summary (natr trajectory presente) | latest_events (2) sottoinsieme per-categoria degli eventi | alto | buono | 91 | OPTIMAL | Ship as-is; opz.: atr/bollinger in history; nota su latest_events |
| `asset.position_review` | 1Y/full | Rivedere posizione singolo Asset: qty/valore/costo/P&L/FIFO/ruolo, tecnica mirata, drawdown, limiti | 8 | overview+position_performance+position_context+drawdown_context | 11 | 4110 | 29,5% | 12 | 0 | 0/0 | 1 Asset (BTP); 18/20 Signal ok (MFI/OBV n/d); FIFO+P&L completi; drawdown PRICE_ONLY -3,21%/max -4,18% | atr_14/bollinger point-only nel summary (natr trajectory presente) | latest_events (2) sottoinsieme per-categoria degli eventi | alto | buono | 91 | OPTIMAL | Ship as-is; opz.: atr/bollinger in history; nota su latest_events |
| `asset.trend_analysis` | 3M/compact | Analisi tecnica completa del trend Asset (Signal/history/eventi materiali) | 5 | overview+market_technical | 8 | 18604 | 88,5% | 20 | 105 | 0/0 | 1 Asset; Signal/history/eventi completi; 239 di 451 eventi (1Y), troncamento dichiarato | nessuna materiality-tiering sugli eventi micro | portfolio_role presente ma non usato dall obiettivo trend | basso | buono | 89 | OPTIMAL | Ship as-is; opz.: tiering eventi; rimuovere portfolio_role dal trend |
| `asset.trend_analysis` | 3M/standard | Analisi tecnica completa del trend Asset (Signal/history/eventi materiali) | 5 | overview+market_technical | 8 | 21896 | 90,3% | 26 | 105 | 0/0 | 1 Asset; Signal/history/eventi completi; 239 di 451 eventi (1Y), troncamento dichiarato | nessuna materiality-tiering sugli eventi micro | portfolio_role presente ma non usato dall obiettivo trend | basso | buono | 89 | OPTIMAL | Ship as-is; opz.: tiering eventi; rimuovere portfolio_role dal trend |
| `asset.trend_analysis` | 3M/full | Analisi tecnica completa del trend Asset (Signal/history/eventi materiali) | 5 | overview+market_technical | 8 | 26862 | 92,1% | 36 | 105 | 0/0 | 1 Asset; Signal/history/eventi completi; 239 di 451 eventi (1Y), troncamento dichiarato | nessuna materiality-tiering sugli eventi micro | portfolio_role presente ma non usato dall obiettivo trend | basso | buono | 89 | OPTIMAL | Ship as-is; opz.: tiering eventi; rimuovere portfolio_role dal trend |
| `asset.trend_analysis` | 1Y/compact | Analisi tecnica completa del trend Asset (Signal/history/eventi materiali) | 5 | overview+market_technical | 8 | 28043 | 92,4% | 29 | 239 | 0/0 | 1 Asset; Signal/history/eventi completi; 239 di 451 eventi (1Y), troncamento dichiarato | nessuna materiality-tiering sugli eventi micro | portfolio_role presente ma non usato dall obiettivo trend | basso | buono | 90 | OPTIMAL | Ship as-is; opz.: tiering eventi; rimuovere portfolio_role dal trend |
| `asset.trend_analysis` | 1Y/standard | Analisi tecnica completa del trend Asset (Signal/history/eventi materiali) | 5 | overview+market_technical | 8 | 38902 | 94,5% | 46 | 239 | 0/0 | 1 Asset; Signal/history/eventi completi; 239 di 451 eventi (1Y), troncamento dichiarato | nessuna materiality-tiering sugli eventi micro | portfolio_role presente ma non usato dall obiettivo trend | basso | buono | 90 | OPTIMAL | Ship as-is; opz.: tiering eventi; rimuovere portfolio_role dal trend |
| `asset.trend_analysis` | 1Y/full | Analisi tecnica completa del trend Asset (Signal/history/eventi materiali) | 5 | overview+market_technical | 8 | 56072 | 96,2% | 75 | 239 | 0/0 | 1 Asset; Signal/history/eventi completi; 239 di 451 eventi (1Y), troncamento dichiarato | nessuna materiality-tiering sugli eventi micro | portfolio_role presente ma non usato dall obiettivo trend | basso | buono | 90 | OPTIMAL | Ship as-is; opz.: tiering eventi; rimuovere portfolio_role dal trend |
| `broker.concentration_context` | 3M/compact | Concentrazione Broker per dimensioni + comparatore vs intero portafoglio | 2 | overview+concentration_evidence+technical_summary | 8 | 4064 | 23,2% | 0 | — | — | aggregate breadth; HHI + allocazioni type/settore/geo/valuta + comparatore portafoglio | nessuno stream eventi/history per-asset (by design) | matrice per-signal (20) + per-entita (12) verbosa | nessuno | adeguato | 88 | OPTIMAL | Ridurre bucket Unknown; collassare i 3 detail; defect x100 corretto |
| `broker.concentration_context` | 3M/standard | Concentrazione Broker per dimensioni + comparatore vs intero portafoglio | 2 | overview+concentration_evidence+technical_summary | 8 | 4065 | 23,2% | 0 | — | — | aggregate breadth; HHI + allocazioni type/settore/geo/valuta + comparatore portafoglio | nessuno stream eventi/history per-asset (by design) | matrice per-signal (20) + per-entita (12) verbosa | nessuno | adeguato | 88 | OPTIMAL | Ridurre bucket Unknown; collassare i 3 detail; defect x100 corretto |
| `broker.concentration_context` | 3M/full | Concentrazione Broker per dimensioni + comparatore vs intero portafoglio | 2 | overview+concentration_evidence+technical_summary | 8 | 4064 | 23,2% | 0 | — | — | aggregate breadth; HHI + allocazioni type/settore/geo/valuta + comparatore portafoglio | nessuno stream eventi/history per-asset (by design) | matrice per-signal (20) + per-entita (12) verbosa | nessuno | adeguato | 88 | OPTIMAL | Ridurre bucket Unknown; collassare i 3 detail; defect x100 corretto |
| `broker.concentration_context` | 1Y/compact | Concentrazione Broker per dimensioni + comparatore vs intero portafoglio | 2 | overview+concentration_evidence+technical_summary | 8 | 4071 | 23,1% | 0 | — | — | aggregate breadth; HHI + allocazioni type/settore/geo/valuta + comparatore portafoglio | nessuno stream eventi/history per-asset (by design) | matrice per-signal (20) + per-entita (12) verbosa | nessuno | adeguato | 88 | OPTIMAL | Ridurre bucket Unknown; collassare i 3 detail; defect x100 corretto |
| `broker.concentration_context` | 1Y/standard | Concentrazione Broker per dimensioni + comparatore vs intero portafoglio | 2 | overview+concentration_evidence+technical_summary | 8 | 4072 | 23,1% | 0 | — | — | aggregate breadth; HHI + allocazioni type/settore/geo/valuta + comparatore portafoglio | nessuno stream eventi/history per-asset (by design) | matrice per-signal (20) + per-entita (12) verbosa | nessuno | adeguato | 88 | OPTIMAL | Ridurre bucket Unknown; collassare i 3 detail; defect x100 corretto |
| `broker.concentration_context` | 1Y/full | Concentrazione Broker per dimensioni + comparatore vs intero portafoglio | 2 | overview+concentration_evidence+technical_summary | 8 | 4070 | 23,1% | 0 | — | — | aggregate breadth; HHI + allocazioni type/settore/geo/valuta + comparatore portafoglio | nessuno stream eventi/history per-asset (by design) | matrice per-signal (20) + per-entita (12) verbosa | nessuno | adeguato | 88 | OPTIMAL | Ridurre bucket Unknown; collassare i 3 detail; defect x100 corretto |
| `broker.cost_efficiency` | 3M/compact | Efficienza di costo Broker (fee/turnover/ratio; missing-not-zero) | 3 | overview+performance_flows+cost_efficiency_evidence | 8 | 4544 | 0,0% | — | — | — | turnover/trade-count/ownership; fee registrate assenti (unavailable, non zero) | fee/tax registrate non disponibili a monte; nessun benchmark peer | serie NAV-bucket settimanale (29-75 righe) con ratio null | basso | adeguato | 81 | SUFFICIENT | Mantenere missing-not-zero; downsample NAV quando fee n/d |
| `broker.cost_efficiency` | 3M/standard | Efficienza di costo Broker (fee/turnover/ratio; missing-not-zero) | 3 | overview+performance_flows+cost_efficiency_evidence | 8 | 4796 | 0,0% | — | — | — | turnover/trade-count/ownership; fee registrate assenti (unavailable, non zero) | fee/tax registrate non disponibili a monte; nessun benchmark peer | serie NAV-bucket settimanale (29-75 righe) con ratio null | basso | adeguato | 80 | SUFFICIENT | Mantenere missing-not-zero; downsample NAV quando fee n/d |
| `broker.cost_efficiency` | 3M/full | Efficienza di costo Broker (fee/turnover/ratio; missing-not-zero) | 3 | overview+performance_flows+cost_efficiency_evidence | 8 | 5215 | 0,0% | — | — | — | turnover/trade-count/ownership; fee registrate assenti (unavailable, non zero) | fee/tax registrate non disponibili a monte; nessun benchmark peer | serie NAV-bucket settimanale (29-75 righe) con ratio null | basso | adeguato | 78 | SUFFICIENT | Mantenere missing-not-zero; downsample NAV quando fee n/d |
| `broker.cost_efficiency` | 1Y/compact | Efficienza di costo Broker (fee/turnover/ratio; missing-not-zero) | 3 | overview+performance_flows+cost_efficiency_evidence | 8 | 5042 | 0,0% | — | — | — | turnover/trade-count/ownership; fee registrate assenti (unavailable, non zero) | fee/tax registrate non disponibili a monte; nessun benchmark peer | serie NAV-bucket settimanale (29-75 righe) con ratio null | basso | adeguato | 80 | SUFFICIENT | Mantenere missing-not-zero; downsample NAV quando fee n/d |
| `broker.cost_efficiency` | 1Y/standard | Efficienza di costo Broker (fee/turnover/ratio; missing-not-zero) | 3 | overview+performance_flows+cost_efficiency_evidence | 8 | 5773 | 0,0% | — | — | — | turnover/trade-count/ownership; fee registrate assenti (unavailable, non zero) | fee/tax registrate non disponibili a monte; nessun benchmark peer | serie NAV-bucket settimanale (29-75 righe) con ratio null | basso | adeguato | 78 | SUFFICIENT | Mantenere missing-not-zero; downsample NAV quando fee n/d |
| `broker.cost_efficiency` | 1Y/full | Efficienza di costo Broker (fee/turnover/ratio; missing-not-zero) | 3 | overview+performance_flows+cost_efficiency_evidence | 8 | 7020 | 0,0% | — | — | — | turnover/trade-count/ownership; fee registrate assenti (unavailable, non zero) | fee/tax registrate non disponibili a monte; nessun benchmark peer | serie NAV-bucket settimanale (29-75 righe) con ratio null | basso | adeguato | 77 | SUFFICIENT | Mantenere missing-not-zero; downsample NAV quando fee n/d |
| `broker.fifo_review` | 3M/compact | Revisione lotti FIFO Broker (aperti/parziali/chiusi, custody) | 2 | overview+fifo | 5 | 4983 | 0,0% | — | — | — | lotti aperti/parziali/chiusi + custody completi | nessun rollup aggregato realizzato/non-realizzato | allocation_concentration duplica lievemente le holdings | nessuno | buono | 85 | OPTIMAL | Aggiungere rollup; evidenziare 5 duplicati economici/DEGRADED; detail no-op |
| `broker.fifo_review` | 3M/standard | Revisione lotti FIFO Broker (aperti/parziali/chiusi, custody) | 2 | overview+fifo | 5 | 4983 | 0,0% | — | — | — | lotti aperti/parziali/chiusi + custody completi | nessun rollup aggregato realizzato/non-realizzato | allocation_concentration duplica lievemente le holdings | nessuno | buono | 85 | OPTIMAL | Aggiungere rollup; evidenziare 5 duplicati economici/DEGRADED; detail no-op |
| `broker.fifo_review` | 3M/full | Revisione lotti FIFO Broker (aperti/parziali/chiusi, custody) | 2 | overview+fifo | 5 | 4982 | 0,0% | — | — | — | lotti aperti/parziali/chiusi + custody completi | nessun rollup aggregato realizzato/non-realizzato | allocation_concentration duplica lievemente le holdings | nessuno | buono | 85 | OPTIMAL | Aggiungere rollup; evidenziare 5 duplicati economici/DEGRADED; detail no-op |
| `broker.fifo_review` | 1Y/compact | Revisione lotti FIFO Broker (aperti/parziali/chiusi, custody) | 2 | overview+fifo | 5 | 5204 | 0,0% | — | — | — | lotti aperti/parziali/chiusi + custody completi | nessun rollup aggregato realizzato/non-realizzato | allocation_concentration duplica lievemente le holdings | nessuno | buono | 86 | OPTIMAL | Aggiungere rollup; evidenziare 5 duplicati economici/DEGRADED; detail no-op |
| `broker.fifo_review` | 1Y/standard | Revisione lotti FIFO Broker (aperti/parziali/chiusi, custody) | 2 | overview+fifo | 5 | 5204 | 0,0% | — | — | — | lotti aperti/parziali/chiusi + custody completi | nessun rollup aggregato realizzato/non-realizzato | allocation_concentration duplica lievemente le holdings | nessuno | buono | 86 | OPTIMAL | Aggiungere rollup; evidenziare 5 duplicati economici/DEGRADED; detail no-op |
| `broker.fifo_review` | 1Y/full | Revisione lotti FIFO Broker (aperti/parziali/chiusi, custody) | 2 | overview+fifo | 5 | 5203 | 0,0% | — | — | — | lotti aperti/parziali/chiusi + custody completi | nessun rollup aggregato realizzato/non-realizzato | allocation_concentration duplica lievemente le holdings | nessuno | buono | 86 | OPTIMAL | Aggiungere rollup; evidenziare 5 duplicati economici/DEGRADED; detail no-op |
| `broker.review` | 3M/compact | Revisione neutra Broker (holdings/perf/costi/FIFO + tecnica subordinata + drawdown) | 2 | overview+performance_flows+asset_comparison+fifo+drawdown_context+concentration_evidence | 15 | 12314 | 37,9% | 0 | — | — | holdings/performance/costi/FIFO + drawdown (partial) + concentrazione | drawdown status=partial (carried-forward), provvisorio | coverage/breadth tecnica (~31-38%) secondaria | alto | buono | 86 | OPTIMAL | Risolvere drawdown partial; trim tecnica secondaria a compact |
| `broker.review` | 3M/standard | Revisione neutra Broker (holdings/perf/costi/FIFO + tecnica subordinata + drawdown) | 2 | overview+performance_flows+asset_comparison+fifo+drawdown_context+concentration_evidence | 15 | 12566 | 37,1% | 0 | — | — | holdings/performance/costi/FIFO + drawdown (partial) + concentrazione | drawdown status=partial (carried-forward), provvisorio | coverage/breadth tecnica (~31-38%) secondaria | alto | buono | 86 | OPTIMAL | Risolvere drawdown partial; trim tecnica secondaria a compact |
| `broker.review` | 3M/full | Revisione neutra Broker (holdings/perf/costi/FIFO + tecnica subordinata + drawdown) | 2 | overview+performance_flows+asset_comparison+fifo+drawdown_context+concentration_evidence | 15 | 12984 | 35,9% | 0 | — | — | holdings/performance/costi/FIFO + drawdown (partial) + concentrazione | drawdown status=partial (carried-forward), provvisorio | coverage/breadth tecnica (~31-38%) secondaria | alto | buono | 86 | OPTIMAL | Risolvere drawdown partial; trim tecnica secondaria a compact |
| `broker.review` | 1Y/compact | Revisione neutra Broker (holdings/perf/costi/FIFO + tecnica subordinata + drawdown) | 2 | overview+performance_flows+asset_comparison+fifo+drawdown_context+concentration_evidence | 15 | 13002 | 35,9% | 0 | — | — | holdings/performance/costi/FIFO + drawdown (partial) + concentrazione | drawdown status=partial (carried-forward), provvisorio | coverage/breadth tecnica (~31-38%) secondaria | alto | buono | 87 | OPTIMAL | Risolvere drawdown partial; trim tecnica secondaria a compact |
| `broker.review` | 1Y/standard | Revisione neutra Broker (holdings/perf/costi/FIFO + tecnica subordinata + drawdown) | 2 | overview+performance_flows+asset_comparison+fifo+drawdown_context+concentration_evidence | 15 | 13734 | 34,0% | 0 | — | — | holdings/performance/costi/FIFO + drawdown (partial) + concentrazione | drawdown status=partial (carried-forward), provvisorio | coverage/breadth tecnica (~31-38%) secondaria | alto | buono | 87 | OPTIMAL | Risolvere drawdown partial; trim tecnica secondaria a compact |
| `broker.review` | 1Y/full | Revisione neutra Broker (holdings/perf/costi/FIFO + tecnica subordinata + drawdown) | 2 | overview+performance_flows+asset_comparison+fifo+drawdown_context+concentration_evidence | 15 | 14980 | 31,1% | 0 | — | — | holdings/performance/costi/FIFO + drawdown (partial) + concentrazione | drawdown status=partial (carried-forward), provvisorio | coverage/breadth tecnica (~31-38%) secondaria | alto | buono | 87 | OPTIMAL | Risolvere drawdown partial; trim tecnica secondaria a compact |
| `fx.conversion_timing` | 3M/compact | Timing conversione FX (range osservato/ritorni/volatilita + tecnica) | 2 | overview+market_technical+conversion_timing_context+direct_exposure | 11 | 16542 | 79,7% | pb20/ind12 | — | — | range osservato/ritorni/volatilita (timing_context) + tecnica completa | nessuna task-critical; lieve ridondanza market_technical/timing_context | doppia copertura range/ritorni; full ~42,7k token-eq | n.d. | nessuno | 90 | OPTIMAL | Uniformare denominatori di range; ridurre volume market_technical |
| `fx.conversion_timing` | 3M/standard | Timing conversione FX (range osservato/ritorni/volatilita + tecnica) | 2 | overview+market_technical+conversion_timing_context+direct_exposure | 11 | 18846 | 82,1% | pb26/ind12 | — | — | range osservato/ritorni/volatilita (timing_context) + tecnica completa | nessuna task-critical; lieve ridondanza market_technical/timing_context | doppia copertura range/ritorni; full ~42,7k token-eq | n.d. | nessuno | 90 | OPTIMAL | Uniformare denominatori di range; ridurre volume market_technical |
| `fx.conversion_timing` | 3M/full | Timing conversione FX (range osservato/ritorni/volatilita + tecnica) | 2 | overview+market_technical+conversion_timing_context+direct_exposure | 11 | 22294 | 84,9% | pb36/ind12 | — | — | range osservato/ritorni/volatilita (timing_context) + tecnica completa | nessuna task-critical; lieve ridondanza market_technical/timing_context | doppia copertura range/ritorni; full ~42,7k token-eq | n.d. | nessuno | 89 | OPTIMAL | Uniformare denominatori di range; ridurre volume market_technical |
| `fx.conversion_timing` | 1Y/compact | Timing conversione FX (range osservato/ritorni/volatilita + tecnica) | 2 | overview+market_technical+conversion_timing_context+direct_exposure | 11 | 23222 | 85,5% | pb29/ind12 | — | — | range osservato/ritorni/volatilita (timing_context) + tecnica completa | nessuna task-critical; lieve ridondanza market_technical/timing_context | doppia copertura range/ritorni; full ~42,7k token-eq | n.d. | nessuno | 90 | OPTIMAL | Uniformare denominatori di range; ridurre volume market_technical |
| `fx.conversion_timing` | 1Y/standard | Timing conversione FX (range osservato/ritorni/volatilita + tecnica) | 2 | overview+market_technical+conversion_timing_context+direct_exposure | 11 | 30782 | 89,1% | pb46/ind12 | — | — | range osservato/ritorni/volatilita (timing_context) + tecnica completa | nessuna task-critical; lieve ridondanza market_technical/timing_context | doppia copertura range/ritorni; full ~42,7k token-eq | n.d. | nessuno | 90 | OPTIMAL | Uniformare denominatori di range; ridurre volume market_technical |
| `fx.conversion_timing` | 1Y/full | Timing conversione FX (range osservato/ritorni/volatilita + tecnica) | 2 | overview+market_technical+conversion_timing_context+direct_exposure | 11 | 42678 | 92,1% | pb75/ind12 | — | — | range osservato/ritorni/volatilita (timing_context) + tecnica completa | nessuna task-critical; lieve ridondanza market_technical/timing_context | doppia copertura range/ritorni; full ~42,7k token-eq | n.d. | nessuno | 89 | OPTIMAL | Uniformare denominatori di range; ridurre volume market_technical |
| `fx.exposure_impact` | 3M/compact | Impatto esposizione FX diretta (esposizione netta base/quote) | 2 | overview+direct_exposure+market_context | 7 | 3764 | 21,5% | pb0/ind0 | — | — | esposizione netta base/quote (finding ~zero-USD); 21 leg + directory 17 asset | nessuna task-critical | tabella 21-leg ridondante col netto | n.d. | presente | 91 | OPTIMAL | Opz.: condensare la tabella 21-leg; localizzare i flag |
| `fx.exposure_impact` | 3M/standard | Impatto esposizione FX diretta (esposizione netta base/quote) | 2 | overview+direct_exposure+market_context | 7 | 3847 | 23,1% | pb0/ind0 | — | — | esposizione netta base/quote (finding ~zero-USD); 21 leg + directory 17 asset | nessuna task-critical | tabella 21-leg ridondante col netto | n.d. | presente | 92 | OPTIMAL | Opz.: condensare la tabella 21-leg; localizzare i flag |
| `fx.exposure_impact` | 3M/full | Impatto esposizione FX diretta (esposizione netta base/quote) | 2 | overview+direct_exposure+market_context | 7 | 3906 | 24,3% | pb0/ind0 | — | — | esposizione netta base/quote (finding ~zero-USD); 21 leg + directory 17 asset | nessuna task-critical | tabella 21-leg ridondante col netto | n.d. | presente | 92 | OPTIMAL | Opz.: condensare la tabella 21-leg; localizzare i flag |
| `fx.exposure_impact` | 1Y/compact | Impatto esposizione FX diretta (esposizione netta base/quote) | 2 | overview+direct_exposure+market_context | 7 | 3845 | 23,1% | pb0/ind0 | — | — | esposizione netta base/quote (finding ~zero-USD); 21 leg + directory 17 asset | nessuna task-critical | tabella 21-leg ridondante col netto | n.d. | presente | 91 | OPTIMAL | Opz.: condensare la tabella 21-leg; localizzare i flag |
| `fx.exposure_impact` | 1Y/standard | Impatto esposizione FX diretta (esposizione netta base/quote) | 2 | overview+direct_exposure+market_context | 7 | 3927 | 24,7% | pb0/ind0 | — | — | esposizione netta base/quote (finding ~zero-USD); 21 leg + directory 17 asset | nessuna task-critical | tabella 21-leg ridondante col netto | n.d. | presente | 92 | OPTIMAL | Opz.: condensare la tabella 21-leg; localizzare i flag |
| `fx.exposure_impact` | 1Y/full | Impatto esposizione FX diretta (esposizione netta base/quote) | 2 | overview+direct_exposure+market_context | 7 | 3987 | 25,8% | pb0/ind0 | — | — | esposizione netta base/quote (finding ~zero-USD); 21 leg + directory 17 asset | nessuna task-critical | tabella 21-leg ridondante col netto | n.d. | presente | 92 | OPTIMAL | Opz.: condensare la tabella 21-leg; localizzare i flag |
| `fx.trend_review` | 3M/compact | Revisione trend FX (Signal/history/eventi materiali) | 2 | overview+market_technical | 8 | 14780 | 89,1% | pb20/ind12 | — | — | Signal/history/eventi FX completi; warm-up per-signal dichiarato | nessuna task-critical | 12 indicator histories + 227 eventi (1Y); full ~40,9k token-eq | n.d. | presente | 91 | OPTIMAL | Opz.: cap eventi a transizioni materiali; ridurre ridondanza full |
| `fx.trend_review` | 3M/standard | Revisione trend FX (Signal/history/eventi materiali) | 2 | overview+market_technical | 8 | 17085 | 90,6% | pb26/ind12 | — | — | Signal/history/eventi FX completi; warm-up per-signal dichiarato | nessuna task-critical | 12 indicator histories + 227 eventi (1Y); full ~40,9k token-eq | n.d. | presente | 90 | OPTIMAL | Opz.: cap eventi a transizioni materiali; ridurre ridondanza full |
| `fx.trend_review` | 3M/full | Revisione trend FX (Signal/history/eventi materiali) | 2 | overview+market_technical | 8 | 20532 | 92,2% | pb36/ind12 | — | — | Signal/history/eventi FX completi; warm-up per-signal dichiarato | nessuna task-critical | 12 indicator histories + 227 eventi (1Y); full ~40,9k token-eq | n.d. | presente | 87 | OPTIMAL | Opz.: cap eventi a transizioni materiali; ridurre ridondanza full |
| `fx.trend_review` | 1Y/compact | Revisione trend FX (Signal/history/eventi materiali) | 2 | overview+market_technical | 8 | 21460 | 92,5% | pb29/ind12 | — | — | Signal/history/eventi FX completi; warm-up per-signal dichiarato | nessuna task-critical | 12 indicator histories + 227 eventi (1Y); full ~40,9k token-eq | n.d. | presente | 91 | OPTIMAL | Opz.: cap eventi a transizioni materiali; ridurre ridondanza full |
| `fx.trend_review` | 1Y/standard | Revisione trend FX (Signal/history/eventi materiali) | 2 | overview+market_technical | 8 | 29020 | 94,5% | pb46/ind12 | — | — | Signal/history/eventi FX completi; warm-up per-signal dichiarato | nessuna task-critical | 12 indicator histories + 227 eventi (1Y); full ~40,9k token-eq | n.d. | presente | 90 | OPTIMAL | Opz.: cap eventi a transizioni materiali; ridurre ridondanza full |
| `fx.trend_review` | 1Y/full | Revisione trend FX (Signal/history/eventi materiali) | 2 | overview+market_technical | 8 | 40916 | 96,1% | pb75/ind12 | — | — | Signal/history/eventi FX completi; warm-up per-signal dichiarato | nessuna task-critical | 12 indicator histories + 227 eventi (1Y); full ~40,9k token-eq | n.d. | presente | 87 | OPTIMAL | Opz.: cap eventi a transizioni materiali; ridurre ridondanza full |
| `portfolio.description` | 3M/compact | Descrizione concisa portafoglio (composizione/cassa/capitale/perf/breadth aggregata) | 5 | overview+performance_flows+technical_summary | 11 | 6212 | 18,9% | 0 | 0 | 7/131 | composizione/cassa/capitale/performance/concentrazione + breadth (digest 7g/131u) | 5/17 asset non coperti (dichiarati) | matrice per-signal ricca per un task conciso | medio-basso | ottimo | 91 | OPTIMAL | Demote matrice 20-signal; mantenere per-entita + digest |
| `portfolio.description` | 3M/standard | Descrizione concisa portafoglio (composizione/cassa/capitale/perf/breadth aggregata) | 5 | overview+performance_flows+technical_summary | 11 | 6464 | 18,2% | 0 | 0 | 7/131 | composizione/cassa/capitale/performance/concentrazione + breadth (digest 7g/131u) | 5/17 asset non coperti (dichiarati) | matrice per-signal ricca per un task conciso | medio-basso | ottimo | 90 | OPTIMAL | Demote matrice 20-signal; mantenere per-entita + digest |
| `portfolio.description` | 3M/full | Descrizione concisa portafoglio (composizione/cassa/capitale/perf/breadth aggregata) | 5 | overview+performance_flows+technical_summary | 11 | 6882 | 17,1% | 0 | 0 | 7/131 | composizione/cassa/capitale/performance/concentrazione + breadth (digest 7g/131u) | 5/17 asset non coperti (dichiarati) | matrice per-signal ricca per un task conciso | medio-basso | ottimo | 89 | OPTIMAL | Demote matrice 20-signal; mantenere per-entita + digest |
| `portfolio.description` | 1Y/compact | Descrizione concisa portafoglio (composizione/cassa/capitale/perf/breadth aggregata) | 5 | overview+performance_flows+technical_summary | 11 | 6705 | 18,4% | 0 | 0 | 7/131 | composizione/cassa/capitale/performance/concentrazione + breadth (digest 7g/131u) | 5/17 asset non coperti (dichiarati) | matrice per-signal ricca per un task conciso | medio-basso | ottimo | 91 | OPTIMAL | Demote matrice 20-signal; mantenere per-entita + digest |
| `portfolio.description` | 1Y/standard | Descrizione concisa portafoglio (composizione/cassa/capitale/perf/breadth aggregata) | 5 | overview+performance_flows+technical_summary | 11 | 7436 | 16,6% | 0 | 0 | 7/131 | composizione/cassa/capitale/performance/concentrazione + breadth (digest 7g/131u) | 5/17 asset non coperti (dichiarati) | matrice per-signal ricca per un task conciso | medio-basso | ottimo | 90 | OPTIMAL | Demote matrice 20-signal; mantenere per-entita + digest |
| `portfolio.description` | 1Y/full | Descrizione concisa portafoglio (composizione/cassa/capitale/perf/breadth aggregata) | 5 | overview+performance_flows+technical_summary | 11 | 8683 | 14,2% | 0 | 0 | 7/131 | composizione/cassa/capitale/performance/concentrazione + breadth (digest 7g/131u) | 5/17 asset non coperti (dichiarati) | matrice per-signal ricca per un task conciso | medio-basso | ottimo | 89 | OPTIMAL | Demote matrice 20-signal; mantenere per-entita + digest |
| `portfolio.fifo_review` | 3M/compact | Revisione lotti FIFO portafoglio (aperti/parziali/chiusi) | 6 | overview+fifo | 6 | 6231 | 0,0% | 0 | 0 | — | lotti aperti/parziali/chiusi completi | nessun contesto performance (offerto come Additional Data) | detail_level no-op (compact==full); .code valuta ripetuto | basso | buono | 86 | OPTIMAL | Rendere detail_level significativo; collassare .code valuta |
| `portfolio.fifo_review` | 3M/standard | Revisione lotti FIFO portafoglio (aperti/parziali/chiusi) | 6 | overview+fifo | 6 | 6231 | 0,0% | 0 | 0 | — | lotti aperti/parziali/chiusi completi | nessun contesto performance (offerto come Additional Data) | detail_level no-op (compact==full); .code valuta ripetuto | basso | buono | 86 | OPTIMAL | Rendere detail_level significativo; collassare .code valuta |
| `portfolio.fifo_review` | 3M/full | Revisione lotti FIFO portafoglio (aperti/parziali/chiusi) | 6 | overview+fifo | 6 | 6230 | 0,0% | 0 | 0 | — | lotti aperti/parziali/chiusi completi | nessun contesto performance (offerto come Additional Data) | detail_level no-op (compact==full); .code valuta ripetuto | basso | buono | 86 | OPTIMAL | Rendere detail_level significativo; collassare .code valuta |
| `portfolio.fifo_review` | 1Y/compact | Revisione lotti FIFO portafoglio (aperti/parziali/chiusi) | 6 | overview+fifo | 6 | 6425 | 0,0% | 0 | 0 | — | lotti aperti/parziali/chiusi completi | nessun contesto performance (offerto come Additional Data) | detail_level no-op (compact==full); .code valuta ripetuto | basso | buono | 87 | OPTIMAL | Rendere detail_level significativo; collassare .code valuta |
| `portfolio.fifo_review` | 1Y/standard | Revisione lotti FIFO portafoglio (aperti/parziali/chiusi) | 6 | overview+fifo | 6 | 6425 | 0,0% | 0 | 0 | — | lotti aperti/parziali/chiusi completi | nessun contesto performance (offerto come Additional Data) | detail_level no-op (compact==full); .code valuta ripetuto | basso | buono | 87 | OPTIMAL | Rendere detail_level significativo; collassare .code valuta |
| `portfolio.fifo_review` | 1Y/full | Revisione lotti FIFO portafoglio (aperti/parziali/chiusi) | 6 | overview+fifo | 6 | 6424 | 0,0% | 0 | 0 | — | lotti aperti/parziali/chiusi completi | nessun contesto performance (offerto come Additional Data) | detail_level no-op (compact==full); .code valuta ripetuto | basso | buono | 87 | OPTIMAL | Rendere detail_level significativo; collassare .code valuta |
| `portfolio.income_review` | 3M/compact | Revisione reddito portafoglio (timeline datata registrata, no forecast) | 3 | overview+performance_flows+income_evidence | 9 | 5188 | 0,0% | 0 | 0 | 0/0 | timeline reddito datata per contributore; converted/unconverted dichiarati | yield per-asset non fornito (derivabile dalla timeline) | serie NAV-bucket e schema contributor larghi | nessuno | buono | 86 | OPTIMAL | Togliere NAV-bucket; opz. colonna yield per-asset |
| `portfolio.income_review` | 3M/standard | Revisione reddito portafoglio (timeline datata registrata, no forecast) | 3 | overview+performance_flows+income_evidence | 9 | 5496 | 0,0% | 0 | 0 | 0/0 | timeline reddito datata per contributore; converted/unconverted dichiarati | yield per-asset non fornito (derivabile dalla timeline) | serie NAV-bucket e schema contributor larghi | nessuno | buono | 86 | OPTIMAL | Togliere NAV-bucket; opz. colonna yield per-asset |
| `portfolio.income_review` | 3M/full | Revisione reddito portafoglio (timeline datata registrata, no forecast) | 3 | overview+performance_flows+income_evidence | 9 | 5913 | 0,0% | 0 | 0 | 0/0 | timeline reddito datata per contributore; converted/unconverted dichiarati | yield per-asset non fornito (derivabile dalla timeline) | serie NAV-bucket e schema contributor larghi | nessuno | buono | 86 | OPTIMAL | Togliere NAV-bucket; opz. colonna yield per-asset |
| `portfolio.income_review` | 1Y/compact | Revisione reddito portafoglio (timeline datata registrata, no forecast) | 3 | overview+performance_flows+income_evidence | 9 | 6032 | 0,0% | 0 | 0 | 0/0 | timeline reddito datata per contributore; converted/unconverted dichiarati | yield per-asset non fornito (derivabile dalla timeline) | serie NAV-bucket e schema contributor larghi | nessuno | buono | 87 | OPTIMAL | Togliere NAV-bucket; opz. colonna yield per-asset |
| `portfolio.income_review` | 1Y/standard | Revisione reddito portafoglio (timeline datata registrata, no forecast) | 3 | overview+performance_flows+income_evidence | 9 | 6934 | 0,0% | 0 | 0 | 0/0 | timeline reddito datata per contributore; converted/unconverted dichiarati | yield per-asset non fornito (derivabile dalla timeline) | serie NAV-bucket e schema contributor larghi | nessuno | buono | 87 | OPTIMAL | Togliere NAV-bucket; opz. colonna yield per-asset |
| `portfolio.income_review` | 1Y/full | Revisione reddito portafoglio (timeline datata registrata, no forecast) | 3 | overview+performance_flows+income_evidence | 9 | 8180 | 0,0% | 0 | 0 | 0/0 | timeline reddito datata per contributore; converted/unconverted dichiarati | yield per-asset non fornito (derivabile dalla timeline) | serie NAV-bucket e schema contributor larghi | nessuno | buono | 87 | OPTIMAL | Togliere NAV-bucket; opz. colonna yield per-asset |
| `portfolio.pac_planning` | 3M/compact | Pianificazione PAC (input utente mancanti per contratto) | 2 | overview+performance_flows+asset_snapshot | 10 | 7661 | 35,0% | 0 | 0 | 0/0 | overview+flows+asset_snapshot; input utente assenti/segnalati | nessuna dimensione drawdown/rischio subordinata | latest_events (24) + NAV-bucket + matrice coverage (~27-35% tec.) | medio | buono | 84 | SUFFICIENT | Demote coverage matrix; estendere drawdown subordinato -> OPTIMAL |
| `portfolio.pac_planning` | 3M/standard | Pianificazione PAC (input utente mancanti per contratto) | 2 | overview+performance_flows+asset_snapshot | 10 | 7914 | 33,9% | 0 | 0 | 0/0 | overview+flows+asset_snapshot; input utente assenti/segnalati | nessuna dimensione drawdown/rischio subordinata | latest_events (24) + NAV-bucket + matrice coverage (~27-35% tec.) | medio | buono | 84 | SUFFICIENT | Demote coverage matrix; estendere drawdown subordinato -> OPTIMAL |
| `portfolio.pac_planning` | 3M/full | Pianificazione PAC (input utente mancanti per contratto) | 2 | overview+performance_flows+asset_snapshot | 10 | 8332 | 32,2% | 0 | 0 | 0/0 | overview+flows+asset_snapshot; input utente assenti/segnalati | nessuna dimensione drawdown/rischio subordinata | latest_events (24) + NAV-bucket + matrice coverage (~27-35% tec.) | medio | buono | 84 | SUFFICIENT | Demote coverage matrix; estendere drawdown subordinato -> OPTIMAL |
| `portfolio.pac_planning` | 1Y/compact | Pianificazione PAC (input utente mancanti per contratto) | 2 | overview+performance_flows+asset_snapshot | 10 | 8157 | 33,6% | 0 | 0 | 0/0 | overview+flows+asset_snapshot; input utente assenti/segnalati | nessuna dimensione drawdown/rischio subordinata | latest_events (24) + NAV-bucket + matrice coverage (~27-35% tec.) | medio | buono | 84 | SUFFICIENT | Demote coverage matrix; estendere drawdown subordinato -> OPTIMAL |
| `portfolio.pac_planning` | 1Y/standard | Pianificazione PAC (input utente mancanti per contratto) | 2 | overview+performance_flows+asset_snapshot | 10 | 8889 | 30,8% | 0 | 0 | 0/0 | overview+flows+asset_snapshot; input utente assenti/segnalati | nessuna dimensione drawdown/rischio subordinata | latest_events (24) + NAV-bucket + matrice coverage (~27-35% tec.) | medio | buono | 84 | SUFFICIENT | Demote coverage matrix; estendere drawdown subordinato -> OPTIMAL |
| `portfolio.pac_planning` | 1Y/full | Pianificazione PAC (input utente mancanti per contratto) | 2 | overview+performance_flows+asset_snapshot | 10 | 10135 | 27,0% | 0 | 0 | 0/0 | overview+flows+asset_snapshot; input utente assenti/segnalati | nessuna dimensione drawdown/rischio subordinata | latest_events (24) + NAV-bucket + matrice coverage (~27-35% tec.) | medio | buono | 84 | SUFFICIENT | Demote coverage matrix; estendere drawdown subordinato -> OPTIMAL |
| `portfolio.performance_attribution` | 3M/compact | Attribuzione performance (contributori/allocazioni) | 2 | overview+performance_flows | 8 | 4842 | 0,0% | 0 | 0 | 0/0 | contributori + allocazioni completi | dettaglio lotto realizzato via portfolio.fifo opzionale | bucket con colonne null (innocue); cash loosely tied | basso | buono | 88 | OPTIMAL | Nessuna modifica richiesta |
| `portfolio.performance_attribution` | 3M/standard | Attribuzione performance (contributori/allocazioni) | 2 | overview+performance_flows | 8 | 5094 | 0,0% | 0 | 0 | 0/0 | contributori + allocazioni completi | dettaglio lotto realizzato via portfolio.fifo opzionale | bucket con colonne null (innocue); cash loosely tied | basso | buono | 88 | OPTIMAL | Nessuna modifica richiesta |
| `portfolio.performance_attribution` | 3M/full | Attribuzione performance (contributori/allocazioni) | 2 | overview+performance_flows | 8 | 5513 | 0,0% | 0 | 0 | 0/0 | contributori + allocazioni completi | dettaglio lotto realizzato via portfolio.fifo opzionale | bucket con colonne null (innocue); cash loosely tied | basso | buono | 88 | OPTIMAL | Nessuna modifica richiesta |
| `portfolio.performance_attribution` | 1Y/compact | Attribuzione performance (contributori/allocazioni) | 2 | overview+performance_flows | 8 | 5279 | 0,0% | 0 | 0 | 0/0 | contributori + allocazioni completi | dettaglio lotto realizzato via portfolio.fifo opzionale | bucket con colonne null (innocue); cash loosely tied | basso | buono | 89 | OPTIMAL | Nessuna modifica richiesta |
| `portfolio.performance_attribution` | 1Y/standard | Attribuzione performance (contributori/allocazioni) | 2 | overview+performance_flows | 8 | 6011 | 0,0% | 0 | 0 | 0/0 | contributori + allocazioni completi | dettaglio lotto realizzato via portfolio.fifo opzionale | bucket con colonne null (innocue); cash loosely tied | basso | buono | 89 | OPTIMAL | Nessuna modifica richiesta |
| `portfolio.performance_attribution` | 1Y/full | Attribuzione performance (contributori/allocazioni) | 2 | overview+performance_flows | 8 | 7257 | 0,0% | 0 | 0 | 0/0 | contributori + allocazioni completi | dettaglio lotto realizzato via portfolio.fifo opzionale | bucket con colonne null (innocue); cash loosely tied | basso | buono | 89 | OPTIMAL | Nessuna modifica richiesta |
| `portfolio.rebalancing` | 3M/compact | Ribilanciamento (gap allocazione + tecnica + drawdown/recovery) | 2 | overview+performance_flows+asset_comparison+drawdown_context | 13 | 10667 | 49,0% | 0 | 0 | 0/0 | gap allocazione + contesto per-asset + drawdown/recovery | VaR/CVaR forward assenti (drawdown gap risolto) | NAV-bucket tangenziale; boilerplate semantic_description; matrice coverage | alto | buono | 90 | OPTIMAL | Collassare semantic_description; demote coverage matrix; opz. VaR/CVaR |
| `portfolio.rebalancing` | 3M/standard | Ribilanciamento (gap allocazione + tecnica + drawdown/recovery) | 2 | overview+performance_flows+asset_comparison+drawdown_context | 13 | 10920 | 47,8% | 0 | 0 | 0/0 | gap allocazione + contesto per-asset + drawdown/recovery | VaR/CVaR forward assenti (drawdown gap risolto) | NAV-bucket tangenziale; boilerplate semantic_description; matrice coverage | alto | buono | 90 | OPTIMAL | Collassare semantic_description; demote coverage matrix; opz. VaR/CVaR |
| `portfolio.rebalancing` | 3M/full | Ribilanciamento (gap allocazione + tecnica + drawdown/recovery) | 2 | overview+performance_flows+asset_comparison+drawdown_context | 13 | 11338 | 46,1% | 0 | 0 | 0/0 | gap allocazione + contesto per-asset + drawdown/recovery | VaR/CVaR forward assenti (drawdown gap risolto) | NAV-bucket tangenziale; boilerplate semantic_description; matrice coverage | alto | buono | 90 | OPTIMAL | Collassare semantic_description; demote coverage matrix; opz. VaR/CVaR |
| `portfolio.rebalancing` | 1Y/compact | Ribilanciamento (gap allocazione + tecnica + drawdown/recovery) | 2 | overview+performance_flows+asset_comparison+drawdown_context | 13 | 11164 | 47,3% | 0 | 0 | 0/0 | gap allocazione + contesto per-asset + drawdown/recovery | VaR/CVaR forward assenti (drawdown gap risolto) | NAV-bucket tangenziale; boilerplate semantic_description; matrice coverage | alto | buono | 91 | OPTIMAL | Collassare semantic_description; demote coverage matrix; opz. VaR/CVaR |
| `portfolio.rebalancing` | 1Y/standard | Ribilanciamento (gap allocazione + tecnica + drawdown/recovery) | 2 | overview+performance_flows+asset_comparison+drawdown_context | 13 | 11896 | 44,4% | 0 | 0 | 0/0 | gap allocazione + contesto per-asset + drawdown/recovery | VaR/CVaR forward assenti (drawdown gap risolto) | NAV-bucket tangenziale; boilerplate semantic_description; matrice coverage | alto | buono | 91 | OPTIMAL | Collassare semantic_description; demote coverage matrix; opz. VaR/CVaR |
| `portfolio.rebalancing` | 1Y/full | Ribilanciamento (gap allocazione + tecnica + drawdown/recovery) | 2 | overview+performance_flows+asset_comparison+drawdown_context | 13 | 13142 | 40,2% | 0 | 0 | 0/0 | gap allocazione + contesto per-asset + drawdown/recovery | VaR/CVaR forward assenti (drawdown gap risolto) | NAV-bucket tangenziale; boilerplate semantic_description; matrice coverage | alto | buono | 91 | OPTIMAL | Collassare semantic_description; demote coverage matrix; opz. VaR/CVaR |
| `portfolio.technical_breadth` | 3M/compact | Ampiezza tecnica universo (coverage/breadth pesata/digest categorizzato) | 4 | overview+technical_summary | 7 | 4434 | 26,5% | 0 | 0 | 7/131 | coverage + breadth pesata/non-pesata + digest categorizzato (7g/131u); 12/17 coperti | 5/17 asset non coperti (dichiarati) | matrice per-signal (20) + per-entita (17) granulari; detail no-op | medio-basso | ottimo | 93 | OPTIMAL | Rendere detail_level significativo o nasconderlo; allineare wording §8 |
| `portfolio.technical_breadth` | 3M/standard | Ampiezza tecnica universo (coverage/breadth pesata/digest categorizzato) | 4 | overview+technical_summary | 7 | 4435 | 26,5% | 0 | 0 | 7/131 | coverage + breadth pesata/non-pesata + digest categorizzato (7g/131u); 12/17 coperti | 5/17 asset non coperti (dichiarati) | matrice per-signal (20) + per-entita (17) granulari; detail no-op | medio-basso | ottimo | 93 | OPTIMAL | Rendere detail_level significativo o nasconderlo; allineare wording §8 |
| `portfolio.technical_breadth` | 3M/full | Ampiezza tecnica universo (coverage/breadth pesata/digest categorizzato) | 4 | overview+technical_summary | 7 | 4434 | 26,5% | 0 | 0 | 7/131 | coverage + breadth pesata/non-pesata + digest categorizzato (7g/131u); 12/17 coperti | 5/17 asset non coperti (dichiarati) | matrice per-signal (20) + per-entita (17) granulari; detail no-op | medio-basso | ottimo | 93 | OPTIMAL | Rendere detail_level significativo o nasconderlo; allineare wording §8 |
| `portfolio.technical_breadth` | 1Y/compact | Ampiezza tecnica universo (coverage/breadth pesata/digest categorizzato) | 4 | overview+technical_summary | 7 | 4491 | 27,4% | 0 | 0 | 7/131 | coverage + breadth pesata/non-pesata + digest categorizzato (7g/131u); 12/17 coperti | 5/17 asset non coperti (dichiarati) | matrice per-signal (20) + per-entita (17) granulari; detail no-op | medio-basso | ottimo | 93 | OPTIMAL | Rendere detail_level significativo o nasconderlo; allineare wording §8 |
| `portfolio.technical_breadth` | 1Y/standard | Ampiezza tecnica universo (coverage/breadth pesata/digest categorizzato) | 4 | overview+technical_summary | 7 | 4491 | 27,4% | 0 | 0 | 7/131 | coverage + breadth pesata/non-pesata + digest categorizzato (7g/131u); 12/17 coperti | 5/17 asset non coperti (dichiarati) | matrice per-signal (20) + per-entita (17) granulari; detail no-op | medio-basso | ottimo | 93 | OPTIMAL | Rendere detail_level significativo o nasconderlo; allineare wording §8 |
| `portfolio.technical_breadth` | 1Y/full | Ampiezza tecnica universo (coverage/breadth pesata/digest categorizzato) | 4 | overview+technical_summary | 7 | 4490 | 27,4% | 0 | 0 | 7/131 | coverage + breadth pesata/non-pesata + digest categorizzato (7g/131u); 12/17 coperti | 5/17 asset non coperti (dichiarati) | matrice per-signal (20) + per-entita (17) granulari; detail no-op | medio-basso | ottimo | 93 | OPTIMAL | Rendere detail_level significativo o nasconderlo; allineare wording §8 |

---

## 14. Esiti INSUFFICIENT (nessuno — spiegazione)

**Nessuna Analysis pubblica è INSUFFICIENT**, né nel baseline né nel finale: 0/96 varianti. Lo score minimo assoluto del corpus finale è **77** (`broker.cost_efficiency` 1Y/full), ben sopra la banda INSUFFICIENT (0–59); a baseline il minimo era 68. Una variante sarebbe INSUFFICIENT solo se il task **non fosse completabile** — evidenza core mancante e non recuperabile, o segnale utile sepolto dall'off-task. Non è il caso: anche le 12 varianti SUFFICIENT contengono l'evidenza deterministica core del proprio task (holdings, P&L, FIFO, overview, o turnover/ownership), e le lacune residue sono o **di priorità media** (drawdown subordinato PAC) o **strutturalmente non colmabili oggi** (fee non registrate a monte, input utente per contratto). Questo è un esito **confermato** dagli artefatti, non una stima.

---

## 15. Esiti SUFFICIENT storici (PAC, Broker Cost Efficiency) — superati dall'addendum

Le uniche 12 varianti SUFFICIENT appartengono a due Analysis.

### `portfolio.pac_planning` (6 varianti, score 84)

- **Finding confermato**: gli input utente (budget mensile, orizzonte, allocazione target, tolleranza al rischio) sono **correttamente assenti e segnalati come domande** — non un difetto dati ma la natura del task PAC deterministico; inoltre il contesto tecnico di audit (matrice coverage per-signal + `latest_events` 24 + NAV-bucket) è ancora un po' abbondante per un task che subordina esplicitamente la tecnica (quota ~27–35%).
- **Finding residuo potenziale**: PAC **non** ha ricevuto il `portfolio.drawdown_context` che `rebalancing` ha ottenuto; è la dimensione di rischio subordinata di valore medio ancora assente. È **la modifica più probabile** per portare PAC in OPTIMAL, insieme al demote della matrice coverage a una riga per-entità.
- **Decisione di prodotto futura**: se e come far ingerire a PAC gli input utente (fuori dallo scope dell'export deterministico attuale) — è una scelta di prodotto, non un bug.

### `broker.cost_efficiency` (6 varianti, score 77–81)

- **Finding confermato**: le fee/commissioni **registrate** sono genuinamente assenti nei dati rappresentativi; il componente le dichiara `fees.status=unavailable` con `reason_code=fees_unavailable`, quindi i ratio (`fees_to_turnover`, `fees_to_average_nav`, `fees_to_invested`) sono null ma **correttamente missing-not-zero**, non falsati a zero. Il task resta completabile con prudenza su turnover, trade-count e ownership share.
- **Finding residuo potenziale**: la serie NAV-bucket settimanale (29–75 righe) resta inclusa come denominatore di `fees_to_average_nav`, che però è null perché le fee mancano: da downsampling/rimozione quando le fee non sono disponibili.
- **Decisione di prodotto futura**: esporre le fee reali quando i provider di import a monte le forniranno (dipende dalla pipeline BRIM/broker, non dall'export).

**Risoluzione post-review**:

- PAC riceve ora checklist condizionale completa, distinzione indispensabile/opzionale, scenari condizionali, `portfolio.drawdown_context` e confronto Drawdown per Asset senza history: 4 varianti mirate, score 92–94, **OPTIMAL**.
- Cost Efficiency è stato provato su Directa con fee/tasse registrate: cinque ratio completi con formula, operandi, unità e coverage. Il caso senza fee è correttamente `unavailable`, non zero, e non viene più penalizzato: score 93–96, **OPTIMAL**.
- Report e artefatti: `report-phase00AiExportPacAndCostEfficiencyValidationV1.md`, `real_prompt_probe/20260801T072616.671347Z/`.

---

## 16. Esiti OPTIMAL

**84/96 varianti OPTIMAL nel run storico `…035128`** (era 48). Le 36 promozioni `SUFFICIENT→OPTIMAL` sono guidate — **finding confermati** — dai nuovi dataset/componenti mirati alle lacune §3. L'addendum mirato successivo porta la classificazione corretta a **96/96 OPTIMAL**:

| Analysis | Δ mediana | Driver principale |
|---|---:|---|
| `portfolio.technical_breadth` | 74,5 → 93 (**+18,5**) | summary aggregato + digest; volume ~602k→4,5k token-eq |
| `broker.concentration_context` | 79 → 88 (+9) | dimensioni type/settore/geo/valuta + comparatore; fix x100 |
| `fx.conversion_timing` | 83 → 90 (+7) | `timing_context`: range osservato/ritorni/volatilità |
| `asset.position_review` | 83,5 → 91 (+7,5) | drawdown PRICE_ONLY + portfolio_role + latest per categoria + compact history |
| `portfolio.income_review` | 79,5 → 86,5 (+7) | timeline reddito datata + puntatore FIFO |
| `broker.review` | 83,5 → 86,5 (+3) | drawdown TWRR + concentrazione |
| `portfolio.rebalancing` | 88 → 90,5 (+2,5) | drawdown/recovery TWRR |

Le 48 varianti già OPTIMAL a baseline (`asset.trend_analysis`, `fx.trend_review`, `fx.exposure_impact`, `portfolio.description`, `portfolio.fifo_review`, `portfolio.performance_attribution`, `broker.fifo_review`, e parte di `rebalancing`) **restano OPTIMAL**. I loro residui sono **finding residui potenziali non bloccanti**: `detail_level` no-op su FIFO/breadth, matrici coverage per-signal verbose, denominatori di range FX da uniformare, boilerplate `semantic_description` — tutti «optional polish», nessun blocker.

---
## 17. Prima/dopo: dimensioni, quota tecnica, history, eventi

Fra baseline e finale il corpus complessivo passa da 285 a 348 prompt (25→32 dataset) per l'aggiunta dei 7 dataset di evidenza; sulle **96 varianti di Analysis** il quadro è:

- **Rating**: 48 OPTIMAL / 48 SUFFICIENT → **84 / 12**; nessun regresso.
- **Quota tecnica**: già ridotta a baseline sulle Analysis finanziarie, resta bassa; l'unico movimento rilevante è il crollo di `portfolio.technical_breadth` (98,8% → **27,4%**) dovuto allo spostamento del technical completo dietro l'Additional Data. Le Analysis tecniche esplicite (`asset.trend_analysis`, `fx.trend_review`, `fx.conversion_timing`) mantengono quota alta (85–96%) per contratto.
- **History/eventi**: `portfolio.technical_breadth` sposta fuori dal prompt inline la history per-asset (4.752–12.306 righe → **0**) e gli eventi detailed (1.308–2.844 → **0**), mantenendo il risultato aggregato come digest categorizzato (7 gruppi / 131 eventi) e il full technical come Additional Data. Al contempo **si aggiungono** eventi di contesto/latest dove il task li richiede: `portfolio.rebalancing` (context 48 / latest 24), `broker.review` (context 44 / latest 12), `asset.position_review` (context 7 / latest 2).
- **Token-eq mediano per variante**: sostanzialmente stabile o in lieve aumento sulle Analysis leggere (per l'evidenza aggiunta: drawdown, income timeline, concentrazione), e in forte calo dove il volume era il problema (breadth). L'obiettivo non era ridurre i token ma **massimizzare l'adeguatezza al task**.

La Tabella C aggrega per Analysis (mediana di token-eq e score sulle 6 varianti; **worst rating** se le varianti divergono — qui mai, ogni Analysis ha rating omogeneo).

### Tabella C — Prima/dopo per Analysis (16 righe, aggregazione: mediana + worst rating)

| Analysis | Rating base | Rating fin. | Score base | Score fin. | Token-eq base | Token-eq fin. | Info aggiunta | Info rimossa | Giustificazione qualita |
|---|---|---|---:|---:|---:|---:|---|---|---|
| `asset.position_review` | SUFFICIENT | OPTIMAL | 83.5 | 91 | 3392 | 3975 | drawdown PRICE_ONLY + portfolio_role 6,88% + latest per categoria + compact 0->3 | colonne latest_event piatte; considered_entity_count rinominato | 5 lacune baseline chiuse |
| `asset.trend_analysis` | OPTIMAL | OPTIMAL | 89.5 | 89.5 | 27324 | 27453 | nessuna (tecnica gia completa) | — | invariato: tecnica esplicita completa |
| `broker.concentration_context` | SUFFICIENT | OPTIMAL | 79 | 88 | 3391 | 4068 | dimensioni type/settore/geo/valuta + comparatore portafoglio; fix x100 | — | lacuna dimensioni/comparatore chiusa |
| `broker.cost_efficiency` | SUFFICIENT | SUFFICIENT | 70 | 79 | 4774 | 5128 | turnover/trade-count/ownership + stato fee unavailable | — | ratio non calcolabili: fee assenti a monte |
| `broker.fifo_review` | OPTIMAL | OPTIMAL | 85.5 | 85.5 | 5093 | 5093 | — | — | invariato |
| `broker.review` | SUFFICIENT | OPTIMAL | 83.5 | 86.5 | 11093 | 12993 | drawdown broker TWRR + concentrazione + asset_comparison | — | holdings/perf/costi/FIFO + rischio (drawdown partial) |
| `fx.conversion_timing` | SUFFICIENT | OPTIMAL | 83 | 90 | 22046 | 22758 | timing_context: range osservato/ritorni/volatilita + storia parziale | — | range/ritorni deterministici aggiunti |
| `fx.exposure_impact` | OPTIMAL | OPTIMAL | 88 | 92 | 3547 | 3877 | sintesi esposizione netta base/quote | — | finding ~zero-USD esplicito |
| `fx.trend_review` | OPTIMAL | OPTIMAL | 89.5 | 90 | 20973 | 20996 | warm-up per-signal dichiarato | — | invariato |
| `portfolio.description` | OPTIMAL | OPTIMAL | 89 | 90 | 6654 | 6794 | technical_summary: digest categorizzato + universe semantics | history tecnica per-asset inline | descrizione concisa completa |
| `portfolio.fifo_review` | OPTIMAL | OPTIMAL | 86.5 | 86.5 | 6328 | 6328 | — | — | invariato; detail_level no-op |
| `portfolio.income_review` | SUFFICIENT | OPTIMAL | 79.5 | 86.5 | 5226 | 5973 | timeline reddito datata + puntatore FIFO | — | timeline datata chiude la lacuna |
| `portfolio.pac_planning` | SUFFICIENT | SUFFICIENT | 84 | 84 | 7191 | 8245 | asset_snapshot per-asset subordinato | — | input utente assenti per contratto |
| `portfolio.performance_attribution` | OPTIMAL | OPTIMAL | 88.5 | 88.5 | 5396 | 5396 | — | — | invariato |
| `portfolio.rebalancing` | OPTIMAL | OPTIMAL | 88 | 90.5 | 9762 | 11251 | drawdown/recovery TWRR + asset_comparison | — | gap drawdown risolto (score+) |
| `portfolio.technical_breadth` | SUFFICIENT | OPTIMAL | 74.5 | 93 | 260358 | 4462 | technical_summary aggregato + digest categorizzato | history tecnica per-asset grezza (602k->4,5k) | volume tagliato senza perdere il deliverable |

---

## 18. Prompt migliorati / invariati con motivazioni

| Categoria | Analysis | Motivo |
|---|---|---|
| **Rating migliorato** `SUFFICIENT→OPTIMAL` (36 varianti) | `asset.position_review`, `broker.concentration_context`, `portfolio.income_review`, `fx.conversion_timing`, `broker.review`, `portfolio.technical_breadth` | nuovi dataset di evidenza mirati alle lacune baseline (drawdown, concentrazione+comparatore, timeline reddito, timing FX, summary aggregato) |
| **Score migliorato, rating già OPTIMAL** | `portfolio.rebalancing` (88→90,5), `fx.exposure_impact` (88→92), `portfolio.description` (89→90) | evidenza aggiunta senza cambiare il verdetto: drawdown/recovery, sintesi esposizione netta, digest categorizzato |
| **Invariato OPTIMAL (byte-stabile a meno di metadata)** | `asset.trend_analysis`, `fx.trend_review`, `portfolio.fifo_review`, `portfolio.performance_attribution`, `broker.fifo_review` | già completi per il proprio task; nessun dataset ne modifica la composizione |
| **Invariato SUFFICIENT** | `portfolio.pac_planning` (84→84), `broker.cost_efficiency` (rating stabile, score +9) | lacune strutturali non colmabili oggi (input utente per contratto; fee non registrate a monte) |

Le motivazioni sono **causali e verificabili**: ogni miglioramento di rating corrisponde a un dataset/componente aggiunto in §11; ogni invarianza corrisponde o a completezza già raggiunta o a un limite strutturale dichiarato.

---

## 19. Problemi aperti

**Finding residui potenziali (non bloccanti, polish):**

- **Denominatori di range FX non uniformi**: `distance_to_min_percent` è calcolato sul minimo, `distance_to_max_percent` sul tasso corrente — usare un riferimento unico.
- **`detail_level` no-op** su `portfolio.fifo_review`, `broker.fifo_review`, `portfolio.technical_breadth` (compact/standard/full byte-identici, diff verificato): renderlo significativo o nasconderlo.
- **Matrici coverage per-signal verbose** su `description`/`pac_planning`/`rebalancing`: demote a riga per-entità.
- **`broker.review` drawdown `status=partial`** (`data_quality_degraded`: sorgente carried-forward): rendere la max drawdown pienamente autoritativa.
- **Bucket «Unknown»** in `broker.concentration_context` (geo 4,25% / settore 4,14%): migliorare la classificazione.
- **Ridondanza full-detail FX** (~40–42k token-eq) fra `market_technical` e `timing_context`.
- **Serie NAV-bucket off-task** in `income_review` e `broker.cost_efficiency` (quest'ultima con `fees_to_average_nav` null).
- **Duplicati economici FIFO / stati DEGRADED** non evidenziati come nota di qualità (aggregato: 159 gruppi / 318 righe nel corpus).

**Decisioni di prodotto futura (fuori dallo scope di questo export):**

- Ingestione opzionale degli input utente in PAC (budget/orizzonte/target/tolleranza): miglioramento UX futuro, non requisito di adeguatezza del prompt.
- Ampliare la copertura fee dei provider/import che non le registrano: l'assenza per uno specifico Broker non è un difetto dell'AI Export.
- VaR/CVaR/stress **deterministici** quando esisterà un calcolatore affidabile.
- `asset.drawdown_recovery`: implementare il contratto di task dedicato + episodi storici comparabili (oggi differita); l'assenza del **drawdown FX pubblico** è invece una scelta intenzionale da confermare.

---

## 20. Test

I risultati del gate sono riportati **separatamente**, senza somma aggregata:

- **Backend**: gate seriale a **1.315 test** verdi; comprende **1.059 servizi AI Export**, **112 schema AI Export** e **15 API AI Export**, oltre ai gate Risk/registry. Il rerun dei tre file toccati dal lint aggiunge **172 test verdi** ma è sovrapposto, quindi non va sommato al totale.
- **Frontend**: **419 test**, di cui **117 AI Export**.
- **Typecheck**: **0 errori**.
- **i18n**: **2.277 chiavi × 4 lingue** (EN/IT/FR/ES) coerenti.
- **Probe**: **35 test** di utility/diagnostica dopo l'audit rafforzato (percentuali SUMMARY, ref grezzi, scope).
- **MkDocs**: build OK + **18 link** cross-boundary verificati.
- **API**: sync client TypeScript / discriminator OK.
- **Addendum PAC/Cost**: backend mirato 215 (195 + 20 composer), probe utility 38, frontend AI Export/Signal 198, typecheck 0; probe reale 10/10, UI/probe equivalence 10/10, source production invariata.

**Qualità del probe finale** (`metrics.json`): `public_output_violations = 0`, `percentage_violations = 0`, `hhi_violations = 0` (54 check), `weight_violations = 0` (1.506 check), `unit_price_violations = 0` (1.380 check), `renderer_equivalence_violations = 0`, `duplicate_header/empty_column = 0`; secret scan `passed`, source DB read-only. Il difetto di **doppia scala percentuale** su campi SUMMARY di concentrazione è stato trovato in fase di rating qualitativo e **corretto prima** del run audited; l'audit ora verifica i campi percentuali SUMMARY (`bounded_summary_percent_fields`, range [−100,100]) e chiude a 0.

---

## 21. Decisioni richieste alla review

1. **Residui SUFFICIENT**: accettarli come by-design (PAC = input utente per contratto; `cost_efficiency` = fee assenti a monte, missing-not-zero) oppure schedulare le due leve (estendere `portfolio.drawdown_context` a PAC; sorgente fee a monte)?
2. **Strategia a volume**: approvare «summary aggregato inline + technical completo come Additional Data» (caso `technical_breadth`, 74,5→93) come standard per le Analysis dominate dal volume?
3. **Polish non bloccanti**: autorizzare `detail_level` significativo-o-nascosto, uniformare i denominatori di range FX, demote delle matrici coverage per-signal, collasso del boilerplate `semantic_description`?
4. **Drawdown**: confermare `asset.drawdown_recovery` differita finché non esistono episodi storici comparabili + contratto dedicato, e confermare l'assenza volontaria del **drawdown FX pubblico**?
5. **`broker.review` drawdown partial**: prioritizzare la risoluzione di `data_quality_degraded` (dati carried-forward) per rendere la max drawdown autoritativa?

---

> **Validazione del report**: 21 sezioni (1–21) presenti; tabelle A (96 righe), B (16), C (16), D (6), E (3 periodi), F (per-tipo evento), G (mattoncini). Percorsi run verificati: finale `real_prompt_probe/20260801T035128.653789Z` (348/348), baseline `real_prompt_probe/20260731T165707.644762Z` (285/285), FX parziali `targeted_partial_fx_probe/20260801T015950.619928Z` (3M), `…794939Z` (6M), `…265250Z` (1Y). Tutte le dimensioni sono `token-equivalenti stimati` (caratteri/4), mai token esatti. **Caveat**: (a) le colonne qualitative di Tabella A sono compattazioni a livello di Analysis (i numeri restano per-variante); (b) i conteggi test in §20 provengono dal gate di validazione, riportati senza somma aggregata (AI Export ⊂ backend); (c) i probe FX parziali usano una coppia a storia sorgente corta per esercitare il ramo parziale, non la coppia del run principale.
