# 14 — Backlog, esecuzione S1–S3 e feature perse — verifica 2026-09-02

> Fonti: [14](../../phases/05_cleanAudit/14_backlog_per_complessita.md) · [15](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md) · [16](../../phases/05_cleanAudit/16_feature_perse_nei_redesign.md)
> Metodo: analisi statica read-only (`grep`/`view`/`git log`/`git show`, `ruff check --select` e `npx knip` in sola lettura); nessun test eseguito (run full in corso).
> Stato del tree: branch `dev_release2`, 32 commit dal 2026-08-06 più modifiche beta non committate del 02/09 — considerate parte della realtà.

## Sintesi esecutiva

- **Interventi S1–S3 (report 15): 31 su 32 reggono. Uno è regredito**: la voce **2.6** — `S110` riportato a 0 il 2026-08-05 — è tornata a **1**: `try/except/pass` in `backend/app/utils/cache_utils.py:82`, introdotto dal commit `c8cd0fb2` (2026-08-13). Erosione collaterale minore: il traguardo «0 dipendenze npm inutilizzate» non regge più — knip oggi ne segnala **4** (`istanbul-*`, introdotte dal cantiere coverage di agosto).
- **Delle 42 voci residue (report 14): 3 chiuse** (4.10, 4.12, 5.1), **4 parzialmente avanzate** (3.8, 4.9, 5.11, 6.1), **35 ancora aperte**. La voce 4.6 è oggi risolvibile per via statica (confermata orfana). Nessuna delle 4 lasciate aperte il 2026-08-05 (1.5, 2.2, 3.8, 3.9) è stata chiusa.
- **Reperti del report 16**: A1 e A2 corretti e stabili; C1 corretto su entrambi i componenti; B2 superato; **A3, A4, A5, A6 ancora presenti** (asserzioni container-only); B1 attenuato ma non risolto; le chiavi i18n orfane sono **aumentate** (da 22 a 30 ID dataset); `suggest_events` resta mai collegato; `LiveTicker.svelte` resta rimosso.
- **Contromisure alle tre lezioni**: esistono a metà — knip è cablato in `dev.py`, il pattern canvas esiste in 2 suite ma non è un helper condiviso, e **nessuna regola di commit-discipline** è stata tradotta in istruzioni permanenti.

---

## A. Verifica dei 32 interventi S1–S3

Legenda: ✅ regge · ⚠️ regredito/parziale.

| # | Intervento | Stato | Evidenza (riga attuale) |
|---|---|:---:|---|
| 1.1 | Licenza AGPL-3.0 + versione 1.1.0 + Python ≥3.13 + Beta | ✅ | `pyproject.toml:7` (`version = "1.1.0"`), `:11` (`>=3.13`), `:16` (`Development Status :: 4 - Beta`), `:17` (classifier `GNU Affero General Public License v3`, senza "or later"); `frontend/package.json:4` `"version": "1.1.0"`. `git show be8394bb:pyproject.toml` conferma che la forma attuale è quella scritta dall'esecuzione |
| 1.3 | Docstring `get_provider_instance` | ✅ | `backend/app/services/fx_providers/__init__.py:8` — «use FXProviderRegistry.get_provider_instance(code)» |
| 1.4 | `_` sugli argomenti inutilizzati dei listener | ✅ | `db/models.py:1002` `receive_before_update(_mapper, _connection, target)`; `db/session.py:21` `set_sqlite_pragma(dbapi_conn, _connection_record)` |
| 2.1 | Riferimento al task di pre-warm | ✅ | `main.py:74` `_background_tasks: set[asyncio.Task] = set()`; `:263-265` `create_task` → `_background_tasks.add(...)` → `add_done_callback(_background_tasks.discard)` |
| 2.3 | `open()` → `asyncio.to_thread` in uploads | ✅ | `api/v1/uploads.py:377-384`: `open()` spostato dentro la closure sincrona `_read_text_preview`, invocata con `await asyncio.to_thread(_read_text_preview)` |
| 2.4 | `is_registration_enabled()` in `register()` | ✅ | `api/v1/auth.py:189-191`: 403 se registrazione disabilitata **e** non primo utente; bootstrap primo utente intatto (`:186-188`, `is_superuser=is_first_user` a :199) |
| 2.5 | Guardia `'"fast"'` ristretta a `params_schema` | ✅ | `test_signal_plugins_close_only.py:105-107`: serializza `params_schema` per plugin e asserisce `ignored not in serialized` per `"fast"`, `"slow"`, `rsi_length`, `mamode` |
| 2.6 | 11 `S110` → 0 | ⚠️ **REGREDITO** | `pipenv run ruff check --select S110 backend/app/` → **Found 1 error**: `utils/cache_utils.py:82` (`except Exception: pass`, con commento ma senza log). `git log -L` lo attribuisce a `c8cd0fb2` (2026-08-13, "perf(test-runner)"). Gli 11 originali restano convertiti; il totale non è più 0 |
| 2.7 | Alias `valuation_price*` / `signed_quantity_by_broker` rimossi | ✅ | `grep -rn "valuation_price\|signed_quantity_by_broker" backend/app/` → 0 hit |
| 2.8 | `unique_computation_count` rimossa | ✅ | 0 hit in `backend/app/` e `backend/test_scripts/` |
| 2.9 | `transitive_dependencies` / `summary_position_count` rimossi | ✅ | 0 hit |
| 2.10 | 3 helper di staleness AI Export rimossi | ✅ | `aiExportOptions.ts` ora 193 righe, nessun helper staleness; `PreparationContext` + `isPreparationContextCurrent()` in `AiExportMenu.svelte:38,146,159` |
| 2.11 | `AI_EXPORT_DOMAIN_ORDER` rimossa | ✅ | 0 hit in `frontend/src/` |
| 2.12 | `signalLabelToText` rimossa | ✅ | 0 hit |
| 2.13 | Ri-esportazione `SignalStyle` da `registry.ts` rimossa | ✅ | `charts/signals/registry.ts` importa e usa `SignalStyle` (`:6,151,177`) ma non lo ri-esporta; il barrel documentato `signals/index.ts:19` lo esporta da `ChartSignal` |
| 2.14 | `e2e/fixtures/db-helpers.ts` rimosso | ✅ | assente da `frontend/e2e/fixtures/` |
| 2.15 | `get_optional_user` rimosso | ✅ | 0 hit in `backend/app/` |
| 2.16 | 6 dipendenze npm rimosse, `katex` tenuto | ✅ (con erosione) | `katex` presente (`package.json:71`), `@types/katex` assente, nessun `@tanstack`. **Ma** knip 2026-09-02 segnala 4 nuove devDependencies inutilizzate: `istanbul-lib-coverage`, `istanbul-lib-report`, `istanbul-lib-source-maps`, `istanbul-reports` (`package.json:41-44`) — nuovo debito del cantiere coverage, non regressione delle 6 rimosse |
| 3.1 | 13 barrel morti rimossi | ✅ | `src/lib/index.ts` assente; nessuno dei 12 percorsi di report 09-I3 esiste (`components/assets|charts|fx|layout|settings/tabs|ui|ui/data-editor|ui/date|ui/display|ui/input|ui/modals`); `tanstack-table/` assente. I sopravvissuti (`charts/signals`, `types`, `components/ui/feedback|select|media`, `transactions/*`, `table`, `api`, `i18n`) sono i barrel documentati |
| 3.2 | Blocco pre-engine di `portfolio_service` rimosso | ✅ | `_HistoryTxRow`, `_HistoryQtyRow`, `_HistoryCalcPoint`, `_build_history_series`: 0 hit. `_daily_state_as_of` tenuto perché vivo fuori dal blocco (`portfolio_service.py:600`, usato a `:895,:989`); `get_history()` delega a `views.build_history()` (`:1595`) |
| 3.3 | `src/lib/tanstack-table/` + `@tanstack/table-core` rimossi | ✅ | directory assente; nessun `tanstack` in `package.json` |
| 3.4 | `HoldingsPanel.svelte` → `PositionsPanel.svelte` | ✅ | HoldingsPanel assente; `components/dashboard/PositionsPanel.svelte` presente |
| 3.5 | `BrokerImportFiles.svelte` → `BrokerImportFilesModal.svelte` | ✅ | solo il Modal esiste |
| 3.6 | `get_session_ttl` / `get_session_ttl_sync` rimossi | ✅ | 0 hit; sostituto vivo: `global_settings_service.py:75` `get_session_ttl_hours` |
| 3.7 | 9 bandiere `isXLoaded`/`isXLoading` rimosse | ✅ | delle 8 di report 08-H1 (`isAssetsLoaded`, `isBrokersLoaded`, `isCountriesLoaded/ing`, `isCurrenciesLoading`, `isFxRoutesLoaded/ing`, `isSectorsLoaded`) + `isLoggedIn`: 0 hit. `isCurrenciesLoaded` viva e tenuta (`currencyStore.ts:133`, usata da `currencyGraphStore.ts:69`). `getConfiguredCurrencies`: 0 hit |
| 4.5 | `FxProviderConfig.svelte` — assorbimento tracciato | ✅ | file assente; sostituto vivo: `FxPairAddModal.svelte` (editMode) → `components/ui/select/FxProviderSelect.svelte`, montato da `fx/[pair]/+page.svelte` e `fx/+page.svelte:19` |
| 5.6 | `LiveTicker.svelte` rimosso | ✅ | file assente, 0 riferimenti in `frontend/src/` |
| mkdocs 05 A3 | `max_file_upload_mb` applicato anche all'upload broker | ✅ | `global_settings_service.py:85` `get_max_upload_mb`; applicato in `api/v1/brokers.py:595` (upload broker) e `uploads.py:170` |
| mkdocs 05 B1 | `--workers` CPU-based in dev.py | ✅ | `dev.py:137-151` `_resolve_server_workers()`: `auto`/`0` → `max(1, 2*(cpu_count-1))` |
| mkdocs 03 F2 | Impostazioni grafico FX persistenti | ✅ | `stores/chartSettingsStore.svelte.ts` con `getSettingsForPair`/`setPairSettings`, usate in `fx/[pair]/+page.svelte:54`; test dedicati `chartSettingsStore.test.ts` + `chartSettingsStoreSsr.test.ts` |
| mkdocs 03 F3 | Import FX rifiuta header incompatibile | ✅ | `FxDataImportModal.svelte:59,100-102`: `headerMismatchError` con confronto header CSV vs `displayBase`/`displayQuote` |
| Regressione | Semi-donut: tracking contenuto + `renderGeneration` + dimensioni | ✅ | `SemiDonutChart.svelte:62` (`renderGeneration`), `:80` (`data.map((slice) => ({...slice}))`), `:85,163,168,198` (guardie di generazione/`isDisposed`/`isConnected`); test `broker-sharing.spec.ts:56-74` `expectOwnershipChartCanvas()` (canvas + `boundingBox()` non nullo), invocata a `:127,141,264` |

**Esito A: 31/32 reggono, 1 regredito (2.6).** Erosione collaterale su 2.16 (4 nuove devDeps inutilizzate) e miglioramento oltre il traguardo sui file orfani (knip «Unused files»: sezione assente oggi → 0; era 1 al 2026-08-05).

> ✅ **Aggiornamento 02–03/09**: la regressione **2.6 è stata chiusa** (P0-2: sito loggato
> con `logger.debug(..., exc_info=True)` + test) e il gate anti-ricaduta è stato creato
> (P0-3: `S110` nella `select` ruff di `pyproject.toml:81`). L'erosione 2.16 (istanbul) è
> un **falso positivo** knip documentato nel report 08 (le 4 devDep sono usate da
> `frontend/scripts/js-coverage-report.js`, fuori dagli entry pattern) — non rimuoverle.

---

## B. Le 42 voci residue: stato oggi

Metodo: `git --no-pager log --oneline --since=2026-08-06` (32 commit) più verifica diretta sui sorgenti. Chiuse **3**, parziali **4**, aperte **35**.

### B.1 — Banda S4 (11 voci residue dopo la chiusura fuori banda di 4.5)

| # | Voce | Stato oggi | Evidenza |
|---|---|:---:|---|
| 4.1 | Eseguire `002_identifier_other_json_list.py` su DB 1.0.1 reale | ⏳ aperta | La migrazione esiste ancora (`backend/alembic/versions/002_identifier_other_json_list.py`); una terza migrazione è stata aggiunta (`5b1333fa6b07_scheduler_times_use_configured_timezone.py`, commit `c8bdbaea`). Nessun test di migrazione né evidenza di prova su DB 1.0.1 nei documenti beta di `Phase_0/06` |
| 4.2 | Verificare i casi limite FIFO sull'engine | ⏳ aperta | `git log --since=2026-08-06 -- test_fifo_lot_engine.py` → nessun commit. `test_fifo_lot_engine.py` oggi 1041 righe, `fifo_lot_engine.py` invariato nel perimetro |
| 4.3 | Misura crescita cache store per asset | ⏳ aperta | Le 3 funzioni esistono e restano **mai chiamate**: `assetPriceStoreRegistry.ts:64` `removeAssetPriceStore`, `currencyGraphStore.ts:135` `invalidateCurrencyGraph`, `priceProcessingPool.ts:97` `destroyPriceProcessingPool` — 0 chiamanti in `frontend/src/` |
| 4.4 | 38 candidati N+1, dal primo (`asset_source.py`) | ⏳ aperta | Il candidato 1 è **intatto**: `patch_assets_bulk` (`asset_source.py:4169`) ha ancora il loop `for patch in patches:` (:4190) con **7 `await session.execute` per elemento** (:4195, 4252, 4255, 4265, 4276, 4283, 4284) — la stessa forma delle «7 query per elemento» del report 03 |
| 4.6 | Tracciare `uploadBrimFile` e `downloadFxBackup` | 🔎 misura completabile oggi | Entrambi **confermati orfani**: `uploadBrimFile` (`utils/files/upload.ts:45`) — 0 chiamanti; il flusso reale usa `axiosInstance.post('/api/v1/brokers/import/upload...')` in `BrokerImportFilesModal.svelte:124`. `downloadFxBackup` (`api/backupDownload.ts:82`) — 0 chiamanti, confermato «Unused exports» da knip 2026-09-02. Resta la rimozione/decisione |
| 4.7 | Campionare i 43 tipi orfani vs `generated.ts` | ⏳ aperta | Non eseguito. knip 2026-09-02: **86 «Unused exported types»** totali (di cui 43 righe sotto `src/lib/types/`) |
| 4.8 | Campionare i 32 tipi orfani dei componenti | ⏳ aperta | Idem (inclusi nel conteggio knip sopra) |
| 4.9 | Copertura frontend post-merge × knip | 🟡 parziale | La macchina di coverage JS **è stata costruita** (piano `06/plan-phase00FrontendCoverage.prompt.md`: monocart-coverage, V8 sul build servito, vitest+Playwright; commit `d1622ee5`, `603099d2`, `c8cd0fb2`). L'**incrocio con knip** per il codice morto ad alta confidenza non risulta documentato |
| 4.10 | Inserimento FX idempotente in `test_lots_analysis_service.py` | ✅ **chiusa** | `test_financial/test_lots_analysis_service.py:28-46` `_own_fx_rate()`: `delete(FxRate)... + session.add(...)` con docstring sulla ownership del dato — il flaky order-dependent è eliminato per costruzione (commit `e2f488cf`) |
| 4.11 | `COVERAGE_PROCESS_START` per `spawn_worker.py` | ⏳ aperta | 0 hit per `COVERAGE_PROCESS_START` in `backend/`, `dev.py`, `scripts/`; il report 17 (:266) citava già il file come non seguito dalla coverage e nulla è cambiato |
| 4.12 | Test per `build_history_sync_entry`, `_infer_country_from_issuer`, `_infer_sector` | ✅ **chiusa** | `test_scheduler_joblog_builders.py:214,239` (`build_history_sync_entry`); `test_borsa_italiana_errors.py:85-90` (`_infer_country_from_issuer`) e `:93-95` (`_infer_sector`) |

> **Stato 03/09 (esecuzione P0/P1) sulla banda S4**:
> - **4.1** ✅ (P1-16, WS-H): prova migrazione eseguita davvero — immagine pubblicata 1.0.1
>   su volume popolato → nuova immagine, stesso volume: `002` (scalare→`["MIGRATION_MARKER"]`,
>   `''`→NULL, array intatto) e `5b1333fa6b07` (`12:00`→`14:00` Europe/Rome) corrette; boot
>   pulito, dashboard 200.
> - **4.2** ⏳ (P1-6): mappatura casi limite `fifo_utils` → `FifoLotEngine` **documentata**
>   nel piano (11 test testa a testa, 2 gap segnalati); rimozione differita a review utente.
> - **4.4** ✅ (P0-5): il candidato 1 (bulk patch) è fixato (02/09, preload + `GROUP BY`);
>   i due verbatim d'endpoint (03/09, Lane B). Gli altri candidati restano da verificare.
> - **4.6** ✅ (P1-7, Lane C): entrambi rimossi (`uploadBrimFile`, `downloadFxBackup`).
> - **4.7 + 4.8** ✅ (P1-9, Lane C): campionamento e pulizia eseguiti (tipi orfani rimossi;
>   scoperti 2 file orfani ulteriori — `BaseDropdown`, `TransactionTypeBadge` — decisione
>   utente nel piano).
> - **4.9** ✅ (P1-18): misura del 03/09 — backend test 91 %, backend-da-E2E 29 %, JS 72,3 %
>   statement. L'**incrocio coverage × knip** non risulta documentato a verbale (residuo).
> - **4.11** ✅ (P1-13): sitecustomize + `COVERAGE_PROCESS_START` sui 5 path di spawn;
>   `spawn_worker.py` ora all'87 % di copertura.

### B.2 — Banda S5 (13 voci residue dopo la chiusura fuori banda di 5.6)

| # | Voce | Stato oggi | Evidenza |
|---|---|:---:|---|
| 5.1 | `merge_other_identifiers` — requisito reale? | ✅ **chiusa (cablata)** | Ora chiamata in produzione da `merge_assets`: `asset_source.py:4475-4477` (`merged_other = merge_other_identifiers(target.identifier_other, [...])`), import a `:130`. Commit `571bcde0` (2026-08-08, "feat(import): asset identity…"). La semantica additiva è applicata; i suoi test coprono ora codice vivo |
| 5.2 | `base_currency` vs `default_currency` | ⏳ aperta | Identica a 2.2 (stessa riga): `portfolio_engine.py:1967` contiene ancora `get_global_setting(self.db, "base_currency", "EUR")` — argomenti invertiti + positional di troppo contro la firma `get_global_setting(key, session)` (`settings_service.py:128`). `lots_analysis_service.py:581` usa l'ordine corretto ma la stessa chiave inesistente |
| 5.3 | `compute_wac_iterative_multi_broker` — cablare o rimuovere | ⏳ aperta | Definita a `portfolio_service.py:347`; unici chiamanti: i test (`test_portfolio_service.py:136,191,269,289`) |
| 5.4 | `AssetMetadataService` — cablare o rimuovere | ⏳ aperta | Classe presente (`asset_source.py:4592`); 0 riferimenti in `backend/app/api/` |
| 5.5 | `cache_utils` — endpoint admin o rimuovere | ⏳ aperta | Il modulo è cresciuto (`NamedCache` + `clear_cache`, `clear_all_caches`, `close_all_caches`, `get_cache_stats`, `list_caches` — `cache_utils.py:136,145,154,177,185`) ma **nessun endpoint admin** li espone. Effetto collaterale: qui vive il nuovo S110 di 2.6 |
| 5.7 | `require_email_verification` — implementare o togliere dalla UI | ⏳ aperta | Chiave ancora nello schema (`schemas/settings.py:92`) e nella UI (`GlobalSettingsTab.svelte:29,50`); nessuna lettura in `auth.py` |
| 5.8 | `ensure_rates_multi_source` — documentare come estensione | 🟡 parziale | Commento-pipeline presente (`fx.py:143-147` la cita come «explicit base_currency routing»); chiamanti: solo test (`test_fx_rates_persistence.py:44,68,108,…`). La documentazione c'è, la decisione di tenere/rimuovere non è registrata |
| 5.9 | `get_provider` / `list_plugin_classes` — rimuovere o documentare | ⏳ aperta | `provider_registry.py:89` (`list_plugin_classes`) e `:233` (`get_provider`): 0 chiamanti di produzione |
| 5.10 | `get_version_info` — esporre con la 1.1.0? | ⏳ aperta | `utils/version.py:60`; 0 riferimenti in `backend/app/api/` → la decisione di release non è stata presa (o è stata «no» non registrata) |
| 5.11 | `txStoreGet*` (4 accessori) | 🟡 parziale | `txStoreGet` e `txStoreGetAll` **adottati** (ImportWizardModal, TransactionPickerModal, TransactionBulkModal); `txStoreGetPartner` (`txStore.svelte.ts:49`) e `txStoreGetMain` (`:62`) restano a 0 chiamanti |
| 5.12 | Le 3 funzioni di ciclo di vita degli store | ⏳ aperta | Dipende da 4.3 (mai misurata); le funzioni restano mai chiamate (v. 4.3) |
| 5.13 | Le 11 property `*_cur` — adottare o rimuovere | ⏳ aperta | Presenti (`schemas/prices.py:168-183,280`); 0 chiamanti (`.close_cur` ecc.: 0 hit); le costruzioni inline `Currency(code=…)` persistono (`schemas/transactions.py:473,483`) — il *DRY orfano* è intatto |
| 5.14 | `availableLanguages`, `currentLanguageFlag`, `currentLanguageName` | ⏳ aperta | Ancora esportate (`language.ts:105,110,116`); knip 2026-09-02 le elenca tutte e tre fra gli «Unused exports» |

> **Stato 03/09 (esecuzione P0/P1) sulla banda S5**:
> - **5.2** ✅ (P0-1, 02/09): chiusa con la variante decisa dall'utente — helper
>   `get_effective_base_currency()` (per-utente → `default_currency` globale → EUR);
>   `portfolio_engine.py`, `lots_analysis_service.py:582`, `portfolio_service.py:719`
>   allineati + test. La chiave fantasma `base_currency` non è più letta.
> - **5.8** ✅ (P1-15, 03/09): commento `# Intentionally unwired` applicato a `fx.py:389` —
>   la decisione «tenere come punto di estensione» è ora registrata nel codice.
> - **5.9** ✅ (P1-15, 03/09): decisione = **rimozione** — `list_plugin_classes` e l'alias
>   `get_provider` tolti da `provider_registry.py`; test esterni migrati a
>   `get_provider_instance`.
> - **5.10** ✅ (P1-17, 03/09) — **terza via**: `get_version_info` **tenuta** (né esposta né
>   rimossa) perché `dev.py:642` è un caller di produzione.

### B.3 — Banda S6 (14 voci)

| # | Voce | Stato oggi | Evidenza |
|---|---|:---:|---|
| 6.1 | `response_model` sui 17 endpoint mancanti | 🟡 parziale | Conteggio riprodotto (python, decoratori multilinea): **35 endpoint totali, 6 senza `response_model`** — `system.py` ×1 (`/health`), `settings.py` ×3, `uploads.py` ×2. Erano 17: 11 cablati nel frattempo (commit `571bcde0`, `6ab295d8`, `29ac61a2` toccano `response_model` in `api/v1/`) |
| 6.2 | `is_chain` via API; `providers_used` chiarito | ⏳ aperta | `is_chain`: 0 hit in `backend/app/api/` e `schemas/`; `providers_used` ancora calcolato inline in `fx.py:990,1098`; il frontend ricostruisce la catena da `chain_steps` (`fx/+page.svelte:310-315`) |
| 6.3 | `build_data_quality_report()` deve usare i 4 `aggregate_*` | ⏳ aperta | Gli `aggregate_*` (`portfolio_engine.py:1678-1699`) sono chiamati **solo dai test** (`test_daily_state_builder.py:783-786`); i due call site reali (`portfolio_service.py:1499,2337`) passano DTO costruiti a mano |
| 6.4 | Estrarre le 3 fasi di `bulk_refresh_prices` | ⏳ aperta | `asset_source.py:2697`: nessun metodo privato estratto nel corpo |
| 6.5 | Far usare `get_asset_provider` ai chiamanti inline | ⏳ aperta (peggiorata) | `asset_source.py:1336`: **0 chiamanti** oltre la definizione — da «sotto-usata» a «del tutto orfana» |
| 6.6 | Ridurre `get_history_value` (complessità 31) | ⏳ aperta | `yahoo_finance.py:284-~488`: ~205 righe, nessuna estrazione |
| 6.7 | Matrice di `validate_status_matrix` dichiarativa | ⏳ aperta | `schemas/signals.py:1069`: ancora catena imperativa `if/elif` per stato |
| 6.8 | Scomposizione di `execute_batch` (complessità 112) | ⏳ aperta | `transaction_service.py:937-~1578`: ~640 righe |
| 6.9 | 53 `TRY400` → `logger.exception` | ⏳ aperta (peggiorata) | `ruff check --select TRY400 backend/app/` → **55 errori** (era 53) |
| 6.10 | `BrokerSharingPanel.svelte` alle Runes | ⏳ aperta (peggiorata) | 24 occorrenze `$:` (erano 20) e `export let` a `:43-45` — ancora legacy mode |
| 6.11 | 17 `assert` strutturali AI Export → `if…raise` | ⏳ aperta | 52 `assert` in `backend/app/services/ai_export/` (conteggio grezzo, include asserzioni non strutturali; nessuna campagna fatta) |
| 6.12 | Consolidare i due `*settings_service` | ⏳ aperta | `settings_service.py` e `global_settings_service.py` coesistono |
| 6.13 | Scindere `asset_source.py` (4 800 righe) | ⏳ aperta (peggiorata) | Oggi **5 162 righe** (`wc -l`) — cresciuto di ~360 righe |
| 6.14 | Helper condivisi dai `parse` BRIM (⛔ sconsigliata) | ⏳ aperta | Nessun helper condiviso nuovo (`_brim_io.py` preesiste al ciclo) |

> **Stato 03/09 (esecuzione P0/P1) sulla banda S6**:
> - **6.1** ✅ (P1-1, Lane A): gli ultimi 6 endpoint cablati (13 schemi nuovi; 2 binari →
>   `response_class`; `api sync` + fix discriminatore `SchedulerLog`).
> - **6.5** ✅ (P1-4/P1-17, 03/09): decisione presa — `get_asset_provider` **tenuto** (è API
>   pubblica del manager, usata da 3 test); non più «orfana da decidere».
> - **6.9** ✅ (P1-3, Lane B2): i 55 `TRY400` convertiti in `logger.exception`, 0 residui.
>   ⚠️ `TRY400` **non** è entrato nel `select` ruff — senza gate la voce può ricrescere.
> - Le altre S6 (6.2, 6.3, 6.4, 6.6, 6.7, 6.8, 6.10, 6.11, 6.12, 6.13, 6.14) restano aperte
>   come da P4-8.

### B.4 — Le 4 lasciate aperte il 2026-08-05

| # | Voce | Stato oggi | Evidenza |
|---|---|:---:|---|
| 1.5 | `TRY003` in `ignore` se si adotta `TRY` | ⏳ aperta (condizione non verificata) | `pyproject.toml` `[tool.ruff.lint] select` = `E,W,F,I,B,C4,UP,PLC0415` — `TRY` non adottato, quindi la voce resta correttamente in sospeso |
| 2.2 | `get_global_setting(self.db, "base_currency", "EUR")` | ⏳ aperta | `portfolio_engine.py:1967` — identica, solo spostata di riga |
| 3.8 | Rimuovere i test orfani col codice che coprono | 🟡 parziale | Il sotto-caso `merge_other_identifiers` è uscito dalla categoria (cablato, v. 5.1). Restano solo-test `compute_wac_iterative_multi_broker` e `AssetMetadataService`. Il runner ora «reports every test red» (commit `0c319f14`), ma una ripetizione completa dell'incrocio «42 simboli» non risulta documentata |
| 3.9 | `git rm fifo_utils.py` (bloccata su 4.2) | ⏳ aperta | `backend/app/utils/financial/fifo_utils.py` presente (148 righe) con i suoi test; 4.2 non fatta → blocco invariato |

> **Stato 03/09 (esecuzione P0/P1) sulle 4 lasciate aperte**:
> - **2.2** ✅ (P0-1, 02/09): vedi nota S5 sopra — helper `get_effective_base_currency()`,
>   chiamata rotta eliminata.
> - **3.9** ⏳ (P1-6, 03/09): il blocco 4.2 è sciolto **sulla carta** — mappatura completa
>   documentata nel piano (11 test testa a testa + equivalenze + gap #7 «P&L negativo» da
>   coprire prima); la **rimozione è differita** a dopo la review utente. File ancora
>   presente, registration runner già corretta.

---

## C. Reperti feature-perse (report 16): stato oggi

| Reperto | Stato 2026-09-02 | Evidenza |
|---|:---:|---|
| A1 — asserzione tautologica `brokers.spec.ts:61` | ✅ corretto | `brokers.spec.ts:64-66`: card filtrata sul nome univoco `Test Broker ${Date.now()}`, `toHaveCount(1)` — fallisce davvero se la creazione non va a buon fine |
| A2 — grafico dettaglio asset container-only | ✅ corretto | `asset-detail.spec.ts:49` `expectAssetDetailChartCanvas()` (modellata su `expectOwnershipChartCanvas`, volutamente duplicata in locale), invocata a `:82` e `:369` |
| A3 — suite `brokers-detail.spec.ts` | ⚠️ ancora presente (in gran parte) | `lot-wac-price-chart`: 4 asserzioni `toBeVisible()` sul contenitore (`:321-327`); `lot-comparison-echart`: 4 `toBeVisible()` (`:550-566`). Unico miglioramento: `lot-gantt` ora verifica i segmenti `lot-gantt-segment-*` (`:341-347`) — contenuto, non contenitore. Un solo `canvas` in tutto il file |
| A4 — `fx-detail.spec.ts` canvas senza contenuto | ⚠️ ancora presente | `:44-51`: canvas visibile, nessuna verifica di dimensioni/pixel |
| A5 — `asset-data-editor.spec.ts` canvas come gate | ⚠️ ancora presente | `:41` `page.waitForSelector('canvas')` non scopato (segue `waitForChart`, che attende ma non asserisce dimensioni) |
| A6 — suite rischio container-only | ⚠️ ancora presente | `portfolio/risk-analysis.spec.ts`: 0 occorrenze `canvas`, 49 `toBeVisible` |
| A7 — `asset-list.spec.ts` | ✅ superato | era già parzialmente protetto; nessuna azione richiesta |
| C1 — `AllocationPieChart` / `GeographyMap` stessa forma del semi-donut | ✅ corretto | `AllocationPieChart.svelte:~113-115`: «Read every element synchronously so this effect tracks the CONTENT…»; `GeographyMap.svelte:118-123`: `for (const key of Object.keys(data)) void data[key];` — esattamente la distinzione array/Record descritta dalla remediation. Nessuna regressione |
| B1 — scorciatoia di cassa sparita (`c14117bb`) | 🟡 attenuato, non risolto | La scorciatoia **specifica** (deposito/prelievo di cassa in 2 click) non è mai tornata. Però oggi la pagina broker ha «Add transaction» contestuale: `brokers/[id]/+page.svelte:639` (`broker-new-transaction`) → `TransactionBulkModal` con `defaultBrokerId={broker.id}` (`:760`) — la comodità contestuale generica è coperta, quella di cassa no. Decisione di prodotto ancora da registrare |
| B2 — pannello transazioni recenti dashboard (ipotesi debole) | ✅ superato | La dashboard ha un tab dedicato: `dashboard/+page.svelte:743` `dashboard-transactions-tab` con `TransactionsTable` completa — la capacità esiste in forma più ricca |
| 22 chiavi i18n orfane `aiExport.dataset.*` | ⚠️ ancora presente, **cresciuto** | Conteggio riprodotto (python su `en.json` + grep dei letterali): **40 ID dataset distinti, 10 referenziati** (dal catalogo `shared.ts:69-…`, 19 entry `displayI18nKey`), **30 orfani** — erano 22 su 28. Nessun uso dinamico delle chiavi rilevato |
| Endpoint `suggest_events` mai collegato | ⚠️ ancora presente | `transactions.py:257-258` (`POST /events/suggest`); client generato (`generated.ts:16718-16719`); 0 chiamanti in componenti/store frontend |
| `LiveTicker.svelte` | ✅ risolto (rimosso) | File assente, 0 riferimenti; capacità viva inline in `assets/+page.svelte` e `assets/[id]/+page.svelte` via `livePriceService.ts` (scelta dell'utente: non ripristinare la striscia in dashboard) |

> **Stato 03/09 (esecuzione P1) sui reperti del report 16**:
> - **A3, A4, A5, A6** ✅ (P1-14, Lane D): helper condiviso `expectChartCanvas()` creato in
>   `e2e/fixtures/charts.ts:25` e applicato a `brokers-detail.spec.ts`, `fx-detail.spec.ts`,
>   `asset-data-editor.spec.ts`, `risk-analysis.spec.ts`. Unica eccezione documentata:
>   `risk-contribution-bars` saltato (è HTML, non canvas).
> - **«30 chiavi i18n orfane `aiExport.dataset.*`»** ⚠️ **REPERETO RITIRATO** (P1-8, Lane C):
>   le ~30 chiavi **non erano orfane** — sono risolte dinamicamente dal catalogo backend
>   (`displayI18nKey`); verificato in sede di rimozione e **tenute**. Rimosse invece le 24
>   chiavi `importWizard.*` + `cannotLinkEventNoAsset` (25 × 4 lingue).

---

## D. Lezioni trasversali: le contromisure esistono ancora?

### Lezione 1 — Le misure di codice morto dipendono dall'ordine

**Contromisura: esiste, ma non viene rieseguita.** Lo strumento è cablato: `./dev.py lint --dead-code` esegue vulture (backend) + knip (frontend) con reporter JSON e path-filtering (`dev.py:1694-1793`, `_run_knip` a `:1792`). Però la riesecuzione non è periodica: il knip di oggi mostra riaccumulo — 60 «Unused exports», 86 «Unused exported types», 4 «Unused devDependencies», 2 «Duplicate exports». La regola operativa («ricalcolare da zero dopo ogni rimozione strutturale») vive solo nei report 14/15/16: nessuna istruzione permanente la codifica.

### Lezione 2 — Test sul contenitore, non sul contenuto

**Contromisura: parziale.** Il pattern di riferimento esiste e regge (`expectOwnershipChartCanvas`, `broker-sharing.spec.ts:56-74`) ed è stato replicato una volta (`expectAssetDetailChartCanvas`, `asset-detail.spec.ts:49`) — ma **non** è stato promosso a helper condiviso in `e2e/fixtures/` (la directory non contiene alcun helper chart/canvas). La generalizzazione proposta dal report 16 non è avvenuta: A3/A4/A5/A6 restano scoperti. Prova che il rischio è vivo: la voce 2.6 (S110=0) è regredita un mese dopo su `cache_utils.py:82` — senza gate automatico, i livelli «zero» non si tengono.

### Lezione 3 — Capacità che spariscono nei redesign

**Contromisura: assente sul piano strutturale.** Nessuna regola «dichiara le rimozioni nel commit message» è stata tradotta nelle istruzioni permanenti (`.github/instructions/*.md`, istruzioni Copilot): la ricerca di vincoli su «Removed:»/rimozione-nei-commit non trova nulla. Resta disciplina orale. Il contro-esempio positivo (`54a15b42`, breaking dichiarato) resta isolato.

### Correzioni ai reperti (tabella INDEX.md «Aggiornamento»)

Verificate tutte e quattro, più la quinta ritirata:

| Correzione | Regge? | Evidenza |
|---|:---:|---|
| 1.2 voce nulla (nessun `max-complexity`/`C901`/mccabe) | ✅ | `pyproject.toml` `[tool.ruff.lint]` non contiene alcuna voce di complessità; nessun `ruff.toml`/`setup.cfg` nel repo |
| 3.1 — 13 barrel (12 previsti + `tanstack-table/index.ts`) | ✅ | v. tabella A |
| 3.7 — 9 bandiere vere, non 8 | ✅ | v. tabella A; `isCurrenciesLoaded` viva e tenuta |
| 03 F3 riclassificato a corruzione silenziosa | ✅ | fix presente e robusto (`FxDataImportModal.svelte:59-102`) |
| «Quinta correzione ritirata» (attribuzione S110 a `api/v1/version.py` mai esistito) | ✅ | coerente: gli S110 erano in `utils/version.py`, e il S110 attuale è altrove (`cache_utils.py:82`) |

---

## Task riesumati

Ordinati per valore/urgenza. Stima: S < 1 h · M < mezza giornata · L ≥ 1 giorno / multi-sessione.

1. **[S] Regressione S110 in `cache_utils.py:82`** — `except Exception: pass` (commit `c8cd0fb2`). Convertire in log (come gli 11 del 2026-08-05) o motivare con `noqa`. Evidenza: `ruff check --select S110 backend/app/` → 1 errore.
   > ✅ **Fatto 02/09** (P0-2): convertito in `logger.debug(..., exc_info=True)` + test.
2. **[S] Gate anti-regressione per i livelli «zero»** — S110 era a 0 e non c'è più; le dipendenze npm inutilizzate erano a 0 e sono 4 (`istanbul-*`, `package.json:41-44`). Aggiungere S110 alla `select` di ruff o un check in CI; rimuovere o cablare le 4 istanbul.
   > ✅ **Fatto 02/09** (P0-3): `S110` aggiunto alla `select` ruff (`pyproject.toml:81`) + 8
   > swallow onesti → `contextlib.suppress`. `TRY400` lasciato fuori gate (P1-3 ha fatto la
   > conversione, non il gate). Le 4 istanbul: **falso positivo** knip (report 08 N1) —
   > nessuna rimozione.
3. **[S codice, decisione M] 2.2/5.2 — `portfolio_engine.py:1967`** — argomenti invertiti + chiave inesistente; allineare anche `lots_analysis_service.py:581`. Richiede la decisione `base_currency` vs `default_currency` (`schemas/settings.py:135` vs `db/models.py:351` colonna per-utente).
   > ✅ **Fatto 02/09** (P0-1) — variante decisa dall'utente: helper
   > `get_effective_base_currency()` (per-utente → globale → EUR), 3 call site allineati +
   > test della catena e del ramo `target_currency=None`.
4. **[S] 4.6 — rimuovere `uploadBrimFile` e `downloadFxBackup`** — orfani confermati oggi (0 chiamanti; knip conferma). La misura è fatta: resta la cancellazione.
   > ✅ **Fatto 03/09** (P1-7, Lane C): entrambi rimossi (0 occorrenze residue).
5. **[S] 5.14 — adottare o rimuovere i 3 helper lingua** (`language.ts:105,110,116`) — knip li conferma orfani; il selettore lingua ricalcola per conto proprio. *DRY orfano*: la risposta giusta è quasi certamente adottare.
6. **[S] 5.11 — completare `txStoreGetPartner` / `txStoreGetMain`** (`txStore.svelte.ts:49,62`) — gli altri due accessori sono stati adottati dall'import wizard; decidere per questi due.
7. **[S] 4.11 — `COVERAGE_PROCESS_START` per `spawn_worker.py`** — il file resta fuori dalla coverage (report 17:266, invariato).
   > ✅ **Fatto 03/09** (P1-13, Lane D + fix coordinatore): sitecustomize
   > (`backend/test_scripts/_coverage_sitecustomize/`) + `COVERAGE_PROCESS_START` sui 5 path
   > di spawn; risolto in corsa il conflitto con lo sitecustomize Homebrew (chain-exec).
   > `spawn_worker.py` ora misurato: 87 %.
8. **[M] 4.4 — N+1 nel bulk patch** (`asset_source.py:4190-4284`, 7 query/elemento) — miglior rapporto valore/costo dell'audit, intatto dopo un mese.
   > ✅ **Fatto 02/09** (P0-5): preload unico + conteggi `GROUP BY` (20 patch senza valuta →
   > 1 SELECT; 3 con valuta → 4, pinnato in test). I due verbatim d'endpoint fixati il 03/09.
9. **[M] 4.3 + 5.12 — misura crescita cache store** e decisione sulle 3 funzioni di ciclo di vita (mai chiamate).
10. **[M] 4.7 + 4.8 — campionamento degli 86 «Unused exported types»** (knip 2026-09-02) contro `generated.ts` — può cancellare decine di voci o promuoverle a S6.
    > ✅ **Fatto 03/09** (P1-9, Lane C): campionamento + pulizia eseguiti (22 re-export morti,
    > tipi orfani componenti, fixture e2e; +2 file orfani scoperti → decisione utente).
11. **[M] A3+A4+A5+A6 — generalizzare il pattern canvas** — promuovere un helper condiviso `expectChartCanvas()` in `e2e/fixtures/` e applicarlo a `brokers-detail.spec.ts` (`:321-327,550-566`), `fx-detail.spec.ts:44-51`, `asset-data-editor.spec.ts:41`, `portfolio/risk-analysis.spec.ts`. Include l'azione A3 residua.
    > ✅ **Fatto 03/09** (P1-14, Lane D): `expectChartCanvas()` creato in
    > `e2e/fixtures/charts.ts:25` e applicato alle 4 spec; `risk-contribution-bars` saltato
    > perché HTML, non canvas (documentato).
12. **[S] 30 chiavi i18n orfane `aiExport.dataset.*`** — pulizia dei 4 file lingua (cresciute da 22 a 30 ID: il catalogo V3 va tenuto sincronizzato con le traduzioni).
    > ⚠️ **Fatto 03/09 con esito opposto** (P1-8, Lane C): in sede di rimozione si è scoperto
    > che le ~30 chiavi `aiExport.dataset.*` **NON erano orfane** (risoluzione dinamica
    > backend-driven via `displayI18nKey`) → **tenute**. La pulizia ha rimosso invece 25
    > chiavi realmente morte (`importWizard.*` ×24 + `cannotLinkEventNoAsset`) × 4 lingue
    > (2 523 → 2 498).
13. **[M, decisione] 5.3 — `compute_wac_iterative_multi_broker`** (`portfolio_service.py:347`): completa, testata, cablata a nulla.
14. **[M, decisione] 5.4 — `AssetMetadataService`** (`asset_source.py:4592`): diff campo-per-campo mai esposto.
15. **[M, decisione] 5.5 — endpoint admin per `cache_utils`** — il modulo è cresciuto (stats/clear/close) ma resta senza superficie; unico modo di invalidare: riavvio.
16. **[S, decisione] 5.7 — `require_email_verification`**: implementare o togliere dalla UI (`GlobalSettingsTab.svelte:50` promette ciò che il sistema non fa).
17. **[S, decisione] 5.10 — `get_version_info`** (`utils/version.py:60`): esporre o rimuovere; la 1.1.0 è uscita senza deciderlo.
    > ✅ **Fatto 03/09** (P1-17) — **terza via**: tenuta com'è (né esposta né rimossa) perché
    > `dev.py:642` è un caller di produzione; il reperto «solo test» era incompleto.
18. **[S] 5.8/5.9 — punti di estensione**: la documentazione di `ensure_rates_multi_source` è a metà (commento `fx.py:143-147`, ma solo test la chiamano); `get_provider`/`list_plugin_classes` (`provider_registry.py:89,233`) restano indecise.
    > ✅ **Fatto 03/09** (P1-15, Lane B): commento `# Intentionally unwired` su `fx.py:389`;
    > `get_provider` e `list_plugin_classes` **rimossi** (test esterni migrati a
    > `get_provider_instance`).
19. **[M] 6.1 — chiudere gli ultimi 6 endpoint senza `response_model`** (`system.py` ×1, `settings.py` ×3, `uploads.py` ×2), poi `./dev.py api sync`.
    > ✅ **Fatto 03/09** (P1-1, Lane A): 6 endpoint cablati, 13 schemi creati; 2 binari →
    > `response_class`; `api sync` + fix discriminatore `SchedulerLog` (enum +
    > post-processor). Nota: le 8 classi orfane pre-scritte (report 01 A5 / 07 G2) **non**
    > sono state riusate — restano da decidere.
20. **[M] 4.2 + 3.9 — casi limite FIFO sull'engine, poi `git rm utils/financial/fifo_utils.py`** (148 righe + test dedicati). Ancora l'unica rimozione a rischio medio.
    > ⏳ **Parziale 03/09** (P1-6, Lane B): mappatura completa documentata nel piano (11 test
    > testa a testa + equivalenze; gap: test di P&L negativo da aggiungere prima). Rimozione
    > **differita** a dopo review utente — il file resta.
21. **[M, decisione] B1 — scorciatoia di cassa broker**: registrare la decisione (reintrodurre deposito/prelievo contestuale o confermare la via generica con `defaultBrokerId`).
22. **[S, decisione] `suggest_events`** (`transactions.py:257`): cablare alla UI o rimuovere; mai collegato da `c3faae19`.
23. **[L] S6 strutturali invariati**: 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9 (55 TRY400), 6.10 (24 `$:`), 6.11, 6.12, 6.13 (`asset_source.py` ora 5 162 righe), 6.14 (⛔ resta sconsigliata). Nessuna avviata; 6.5, 6.9, 6.10, 6.13 **peggiorate** nel mese.
    > ⚠️ **Aggiornamento 03/09**: la **6.9 non è più in questo elenco** — chiusa con P1-3
    > (55/55 TRY400 convertiti). Anche la 6.5 è decisa (`get_asset_provider` tenuto, P1-4/17).
    > Restano aperte: 6.2, 6.3, 6.4, 6.6, 6.7, 6.8, 6.10, 6.11, 6.12, 6.13, 6.14.
24. **[M] 4.1 — prova della migrazione `002` su DB 1.0.1 reale** — prerequisito di release ancora scoperto; nel frattempo è arrivata una terza migrazione (`5b1333fa6b07`).
    > ✅ **Fatto 03/09** (P1-16, WS-H): prova superata con marker esatti — immagine 1.0.1
    > pubblicata → nuova immagine su stesso volume popolato: `002` (scalare→`["MIGRATION_MARKER"]`,
    > `''`→NULL, array intatto) e `5b` (`12:00` UTC→`14:00` Europe/Rome) corrette; boot pulito,
    > dashboard 200.
25. **[S] 4.9 — chiudere l'incrocio coverage × knip** — la coverage JS esiste; manca il confronto documentato con gli orfani knip.
    > ⚠️ **Parziale 03/09** (P1-18): la misura di coverage c'è (backend test 91 %, E2E 29 %,
    > JS 72,3 % statement) ma il **confronto documentato coverage × knip** non risulta nel
    > verbale di chiusura — residuo aperto se lo si ritiene ancora utile dopo la pulizia P1-9.
26. **[S] 1.5 — TRY003**: resta correttamente congelata finché `TRY` non entra in `select`; da non dimenticare quando/if si adotta.

---

## Cross-reference

- Report fratelli di questa tornata: `02_services_core.md`, `03_services_pricing_fx.md`, `06_db_models.md`, `07_schemas_utils.md`, `08_frontend_state_api.md`, `09_frontend_components.md`, `10_frontend_charts.md`, `12_test_coverage.md`, `13_ai_export.md`, `17_stabilizzazione.md`, `mkdocs/` (stessa directory).
- I task riesumati alimentano `99_task_riesumati.md`.
- Tornata precedente: [`05_cleanAudit/14`](../../phases/05_cleanAudit/14_backlog_per_complessita.md) · [`15`](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md) · [`16`](../../phases/05_cleanAudit/16_feature_perse_nei_redesign.md) · [`INDEX.md`](../../phases/05_cleanAudit/INDEX.md) (sezione «Aggiornamento — esecuzione S1–S3»).
- Lavoro beta che ha prodotto le chiusure/parziali: `phases/06_betaTestingReportAndFixing/` (archiviata 03/09) (piani `…AssetIdentity…`, `…FrontendCoverage…`, `03_feedback_utenti_F1-F17…`).

---

*Report 14 della tornata 08_newCleanAndDocumentation_audit — verifica read-only del 2026-09-02.*
