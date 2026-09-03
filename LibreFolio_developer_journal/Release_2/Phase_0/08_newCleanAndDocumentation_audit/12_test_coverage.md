# 12 — Test & copertura — verifica 2026-09-02

> Fonte: [report archiviato](../../phases/05_cleanAudit/12_test_coverage.md) (audit 2026-08-07)
> Metodo: analisi statica read-only; NESSUN test eseguito (run full in corso, DB condiviso).
> I numeri di copertura (90,48 %, 42 funzioni, 155 statement) non sono riproducibili
> staticamente: verificata la STRUTTURA (registrazione test, esistenza file, guardie,
> selettori, chiamanti). Working tree beta del 02/09 incluso nella verifica.

---

## Sintesi esecutiva

Il report 12 **regge un mese dopo, e i suoi 8 interventi raccomandati sono stati
eseguiti per 5/8 in pieno, 1/8 in forma evoluta, 2/8 mai fatti** (entrambi di
configurazione, entrambi con mitigazione documentale parziale).

I tre reperti operativi principali sono tutti **chiusi**:

- **L2.1** (guardia `'"fast"'` troppo larga): **FATTO** — ristretta a `params_schema`
  esattamente come prescritto (`test_signal_plugins_close_only.py:105-107`, commit
  `be8394bb` della banda S1–S3). Il file esiste ancora, il test anche.
- **L2.2** (insert FX non idempotente, flaky order-dependent): **FATTO** — helper
  `_own_fx_rate` delete-then-insert con razionale documentato
  (`test_financial/test_lots_analysis_service.py:28-47`).
- **L4** (`build_history_sync_entry`, 29 stmt allo 0 %): **FATTO** — due test dedicati
  in `test_scheduler_joblog_builders.py:239,291` (commit `603099d2`, 2026-08-27).

L'incrocio copertura-zero ↔ codice morto (§ L5) mostra **movimento nei due sensi**:
gli alias `valuation_price*` sono stati rimossi come prescritto, ma — reperto del mese —
**`merge_other_identifiers` è uscito dall'elenco dei morti perché è diventato codice di
produzione**: la semantica additiva mai applicata è ora il cuore del merge asset
(`asset_source.py:4475`, commit `571bcde0`, 2026-08-08, un giorno dopo l'audit). Il
reperto ⚠️ più delicato del report 07 si è risolto come *funzionalità implementata*,
non come codice cancellato. In senso opposto, `_price_on_date`, `list_plugin_classes`
e i tre simboli test-only ⚠️ sono **ancora esattamente dove erano**.

La suite è cresciuta: **196 file `test_*.py` backend** (erano 171) e **68 spec E2E** —
confronto riprodotto con `find` (comandi in § Dettaglio). La registrazione nel runner
resta completa: controllo orfani riprodotto staticamente → **0 orfani reali**, e tutti
i nuovi file delle ondate beta (incluso il non-tracciato `test_update_js_cache.py` del
working tree) sono già registrati.

---

## Tabella di verifica

| Voce vecchia | Stato 2026-08 | Stato verificato oggi | Evidenza | Azione |
|---|---|---|---|---|
| Copertura 90,48 % / 42 funzioni / 155 stmt | misura | **NON VERIFICABILE STATICAMENTE** | vincolo no-test (run full in corso, DB condiviso); nessuna fonte statica | — |
| L1: trappola misurazione parziale (75,65 % falso) | 🔴 reperto di metodo | **ANCORA VALIDO come rischio; prevenzione FATTA** | la sequenza completa e la tabella unit-only vs completa sono ora in `.github/skills/devpy-tools/testing-backend/SKILL.md:183-208` («A partial coverage measurement is worthless — and it lies LOW») | — |
| L2: `check-orphans` pulito, tutti i test registrati | ✅ | **ANCORA VALIDO — riprodotto staticamente** | 196 file su disco vs 183 path letterali in `scripts/test_runner/*.py`; i 15 scarti sono tutti spiegati: 13 file di `test_financial/` registrati via directory (`_backend_services.py:470`), 3 helper esclusi dal meccanismo stesso (`_inventory.py:270`); i 2 "fantasmi" sono `test_foo.py` in un commento (`_cli.py:178`) e `db_schema_validate.py` (esiste, non matcha il glob `test_*`) | — |
| L2: conteggi per categoria (schemas 8, utils 12, db 5, services 90, api 50, external 4; totale 171) | misura | **SUPERATO (crescita)** | oggi: `test_schemas` 8, `test_db` 7, `test_services` 106, `test_api` 52, `test_external` 4, `test_utilities` 14 (la categoria `utils` vive oggi nella directory `test_utilities/`; `test_utils.py` radice è un helper escluso dal runner, `_inventory.py:270`) — totale 196 | — |
| L2.1: guardia `'"fast"'` sul catalogo intero, 1 failed riproducibile | 🟡 segnalato, non corretto (territorio altro agente) | **FATTO** | `test_signal_plugins_close_only.py:105` serializza solo `{code: definitions[code].params_schema …}`; assert a `:107`; `git blame` → `be8394bb` (2026-08-05, banda S1–S3) | — |
| L2.2: `UNIQUE constraint failed: fx_rates` order-dependent | 🟡 flaky da irrobustire | **FATTO** | `_own_fx_rate` a `test_financial/test_lots_analysis_service.py:28-47`: `delete(FxRate).where(...)` prima dell'insert, stessa transazione con rollback della fixture; docstring che spiega entrambe le trappole. Il file si è spostato in `test_financial/` | — |
| L4: `build_history_sync_entry` (`joblog.py:129`, 29 stmt, 0 %), viva e non testata | 🔴 prioritaria | **FATTO (test aggiunto)** | funzione ancora a `joblog.py:129`, chiamata da `jobs.py:168` (era `:163`); nuovi `test_build_history_sync_entry_shape` (`test_scheduler_joblog_builders.py:239`) e `..._without_icons_or_results` (`:291`), commit `603099d2` 2026-08-27 | — |
| L4: provider 68–79 % falso allarme (rami errore) | 🟢 giudizio | **SUPERATO in meglio** | le ondate beta hanno aggiunto test dedicati ai rami di errore: `test_snb_errors.py` (8 test: HTTP failure `:160,:254`, non-CHF `:175`, valuta non supportata `:192`), `test_justetf_errors.py:73,91,102`, `test_yahoo_finance_errors.py`, `test_borsa_italiana_errors.py` — commit `c1755d19` 2026-08-28 | — |
| L5: `merge_other_identifiers` 0 % + 0 rif. da `app/` | 🔴 conferma incrociata, da discutere come funzionalità mancante | **SUPERATO — ora in produzione** | `identifier_utils.py:51` chiamata da `asset_source.py:130,4475` (merge asset: identificatori demoted confluiscono in `identifier_other`); introdotto da `571bcde0` (2026-08-08); i vecchi riferimenti test-only sono spariti (`grep -l merge_other_identifiers test_scripts/` → solo via merge API) | verificare copertura rami al prossimo giro di misura |
| L5: `DailyPositionState.valuation_price` / `valuation_price_ccy` rimovibili | 🟡 rimozione proposta | **FATTO** | `grep -rn "valuation_price" backend/app --include="*.py"` → 0 occorrenze | — |
| L5: `DailyStateBuilder._price_on_date` (8 stmt) residuo vecchia pipeline | 🟡 report 02 riassorbito | **ANCORA VALIDO — ancora morto** | `portfolio_engine.py:1172`; unica occorrenza testuale in `backend/app/` è il `def` (zero chiamanti) | Task 1 (S) |
| L5: `provider_registry.py` ×4 (`list_plugin_classes`, `_get_plugin_code_attr`, `_reject_duplicate_codes`, `_fail_on_discovery_errors`) | 🟡 report 04 | **ANCORA VALIDO** | presenti a `provider_registry.py:89,190,194,198` (+ override `:222`); `list_plugin_classes` ancora **zero chiamanti ovunque** (`grep` exit 1) | Task 2 (S) |
| L5: `_empty_response` / `_adjustment_cash_flow_cost` | 🟡 report 02 | **ANCORA VALIDO** | `lots_analysis_service.py:671` (chiamata `:192,:207`) e `:1982` (chiamata `:952`) | — |
| L5: `_geography_group_members` | 🟡 report 05 | **ANCORA VALIDO** | `risk/service.py:454`, chiamata condizionata a `:183` | — |
| L5: cecità coverage su `spawn_worker` (`_worker_main` 22, `_resolve_handler` 8, `_peak_rss_bytes` 2) | 🔴 trappola documentata | **ANCORA VALIDO (simboli vivi, strumento cieco); mitigazione documentale** | simboli a `spawn_worker.py:67,72,87`, `Process(target=_worker_main)` a `:167`; `COVERAGE_PROCESS_START` mai configurato (0 occorrenze); ma la cecità è ora regola scritta in `SKILL.md:220-222` | Task 5 (M) |
| L5: `OptimizationResourceLimitError.__init__` 0 % | 🟡 nel gruppo sottoprocesso | **ANCORA VALIDO** | classe a `risk/quant/optimization_engine.py:35` (spostata da dove la citava il report) | — |
| L5: `ApiKeyEngine` stub dichiarato, da lasciare com'è | 🟢 conservare | **ANCORA VALIDO** | `web_link_finder.py:106-113`, docstring-seam intatto parola per parola | — |
| L6: `get_portfolio_wac` coperto solo con `api portfolio-wac` | 🟡 verificare che resti in `api all` | **ANCORA VALIDO (struttura)** | endpoint a `portfolio_api.py:37`; gruppo registrato: `_backend_api.py:558` | — |
| L6: `_infer_country_from_issuer` / `_infer_sector` (Borsa Italiana) | 🟡 euristiche mai testate | **FATTO** | funzioni a `borsa_italiana.py:155,188` (chiamate `:846,:855`); test a `test_borsa_italiana_errors.py:85-90,93+` (`c1755d19`) | — |
| L6: `validate_requested_analyses` / `validate_identifier_other` / `get_plugin_diagnostics` / `get_risk_scenario_catalog` / `get_asset_candidates` | 🟡/🟢 residui | **ANCORA VALIDO** | `schemas/portfolio.py:522`, `db/models.py:551`, `api/v1/system.py:186`, `api/v1/risk.py:33`, `api/v1/brokers.py:1024` — tutti presenti | — |
| L7: 42 simboli referenziati solo da `test_scripts/`; i test dei ⚠️ sono specifiche da conservare | regola + elenco | **ANCORA VALIDO sul campione** | `compute_wac_iterative_multi_broker` (`portfolio_service.py:347`): zero chiamanti in `app/`, test in `test_financial/test_portfolio_service.py`; `AssetMetadataService` (`asset_source.py:4592`): solo docstring, test in `test_asset_metadata.py`; `ensure_rates_multi_source` (`fx.py:389`): citata solo in un commento, test in `test_db/test_fx_rates_persistence.py`. Eccezione: `merge_other_identifiers` uscito dall'elenco (vedi sopra) | Task 4 (M, decisione) |
| L8: frontend non misurato; misurare dopo merge AI Export | raccomandazione | **SUPERATO — la copertura JS/Svelte esiste** | `@vitest/coverage-istanbul ^4.1.11` (`frontend/package.json:38`), `vite-plugin-istanbul ^9.0.1` (`:56`), `vitest.config.ts:19` (provider istanbul, `COVERAGE_JS=1`), `vite.config.ts:67` (`coverageInstrumentation`, guardia `.coverage-instrumented`), report condivisi in `frontend/coverage-js/`; commit `d1622ee5` 2026-08-30. Vedi report 17 della presente tornata | — |
| Intervento 1: restringere guardia `'"fast"'` | 10 min | **FATTO** | vedi L2.1 | — |
| Intervento 2: FX idempotente in `test_lots_analysis_service.py` | 20 min | **FATTO** | vedi L2.2 | — |
| Intervento 3: test per `build_history_sync_entry` | 30 min | **FATTO** | vedi L4 | — |
| Intervento 4: documentare sequenza copertura valida in SKILL.md | 15 min | **FATTO** | `testing-backend/SKILL.md:183-222` (sequenza completa, regola dello scope dichiarato, divieto di timeout corti su `api all`, nota spawn-worker) | — |
| Intervento 5: test inferenze Borsa Italiana | 30 min | **FATTO** | vedi L6 | — |
| Intervento 6: `COVERAGE_PROCESS_START` per `spawn_worker.py` | 45 min | **MAI FATTO** | 0 occorrenze di `COVERAGE_PROCESS_START` in repo; mitigato solo dalla regola scritta in SKILL.md | Task 5 (M) |
| Intervento 7: `max-complexity` 25 + attacco ai `parse` BRIM | — | **MAI FATTO** | `pyproject.toml:72-80`: `C901` non è nel `select`, nessun `max-complexity` impostato. Riprodotto oggi: `pipenv run ruff check app/services/brim_providers --select C901` → **35 errori, identici all'audit** | Task 6 (M, decisione di policy) |

> ✅ **Aggiornamento 03/09**: intervento 6 **fatto** (P1-13 — sitecustomize +
> `COVERAGE_PROCESS_START` sui 5 path di spawn; `spawn_worker.py` ora misurato all'87 %);
> intervento 7 **fatto nella metà config** (P1-2 — `C901` in select con soglia 10; i parse
> BRIM marcati `noqa`/`TODO(P2-refactor)`, l'attacco ai 35 resta P4-3).
| Intervento 8: misurare copertura frontend + incrocio con knip | 1 h | **FATTO (misura); incrocio con knip non documentato** | infrastruttura istanbul operativa (`d1622ee5`); nessun report di incrocio trovato nel journal | — |

---

## Dettaglio

### Comandi di riproduzione strutturale

```bash
# Conteggi file di test (riprodotti il 2026-09-02)
find backend/test_scripts -name "test_*.py" -not -path "*__pycache__*" | wc -l   # 196
find frontend/e2e -name "*.spec.ts" | wc -l                                        # 68
for d in test_schemas test_db test_services test_api test_external test_utilities; do
  find backend/test_scripts/$d -name 'test_*.py' -not -path '*__pycache__*' | wc -l
done   # 8 / 7 / 106 / 52 / 4 / 14

# Controllo orfani statico (equivalente read-only di `test check-orphans`):
# confronto fra file su disco e path letterali in scripts/test_runner/*.py →
# 0 orfani reali (15 scarti spiegati: 13 via directory test_financial/,
# 2 helper-radice esclusi da _inventory.py:270)
```

### Nota su L2.1

La correzione è attribuita da `git blame` a `be8394bb` (2026-08-05), cioè alla banda
S1–S3 documentata dal report 15 — coerente con la cronologia: il report 12 segnalava il
difetto, la banda di remediation lo ha corretto nella forma esatta proposta
(serializzare solo `params_schema`). Il test oggi non è più «l'unico rosso»: è tornato
una guardia anti-leak valida.

### Nota su L5 / `merge_other_identifiers`

Il report 12 lo dava come «da discutere come funzionalità mancante, non codice morto».
Un giorno dopo l'audit (`571bcde0`, 2026-08-08, *feat(import): asset identity, CA
trades and import wizard rework*) la semantica additiva è stata applicata nel **merge
asset**: gli identificatori primari degradati del sorgente confluisco in
`identifier_other` del target (`asset_source.py:4469-4482`), con guardia anti-ombra
(`:4480-4481`). Il rischio funzionale segnalato (reimport da secondo broker che
sovrascrive gli identificatori del primo) va considerato **chiuso nel percorso merge**;
resta da verificare alla prossima misura se i rami della funzione sono coperti (nessun
test la nomina direttamente: la copertura, se c'è, è indiretta via
`test_asset_merge_api.py`).

---

## Task riesumati

| # | Task | Evidenza | Stima |
|---|---|---|---|
| 1 | Rimuovere `DailyStateBuilder._price_on_date` (o trovare il chiamante mancante) | `portfolio_engine.py:1172`, zero chiamanti testuali in `backend/app/` | **S** |
| 2 | Decidere `list_plugin_classes` + `_get_plugin_code_attr`/`_reject_duplicate_codes`/`_fail_on_discovery_errors`: rimozione o whitelist vulture motivata | `provider_registry.py:89,190,194,198`; `list_plugin_classes` zero riferimenti ovunque | **S** |
| 3 | Rimuovere o usare `cleanup_test_database()` | `test_db_config.py:51`, zero chiamanti (reperto ⚪ del report 17, confermato) | **S** |
| 4 | Decidere i tre ⚠️ test-only: `compute_wac_iterative_multi_broker`, `AssetMetadataService`, `ensure_rates_multi_source` — promuovere a feature o rimuovere *con* i test (regola L7: i test sono specifiche di comportamenti che il prodotto non offre) | `portfolio_service.py:347`, `asset_source.py:4592`, `fx.py:389` | **M** (decisione di prodotto, non di codice) |
| 5 | Configurare `COVERAGE_PROCESS_START` + `sitecustomize` per vedere `spawn_worker.py` (intervento 6, mai fatto) | 0 occorrenze; SKILL.md:220-222 documenta solo la cecità | **M** |
| 6 | Policy complessità: o si abilita `C901` nel `select` con `max-complexity` (intervento 7, mai fatto) o si dichiara esplicitamente rinunciato — oggi la regola è solo on-demand e i 35 errori BRIM sono identici a un mese fa | `pyproject.toml:72-80`; `ruff check --select C901` su `brim_providers` → 35 | **M** (più L se si attaccano i parse) |
| 7 | Alla prossima misura di copertura: verificare che `merge_other_identifiers` (ora in produzione) e `identifier_utils.py` intero escano dallo 0 % | `identifier_utils.py:51`, `asset_source.py:4475` | **S** (verifica, non scrittura) |

> **Stato 03/09 (esecuzione P0/P1)**:
> - **#1** ✅ (P1-4, Lane B): `DailyStateBuilder._price_on_date` rimosso (0 chiamanti
>   confermati alla rimozione).
> - **#2** ✅ (P1-15, Lane B) — risolto per **rimozione**: `list_plugin_classes` e l'alias
>   `get_provider` tolti dal registry (test esterni migrati a `get_provider_instance`);
>   `_get_plugin_code_attr`/`_reject_duplicate_codes`/`_fail_on_discovery_errors` restano
>   (usate internamente dal discovery).
> - **#3** ✅ (P1-4, Lane B): `cleanup_test_database()` rimossa (0 chiamanti).
> - **#4** ⏳ **Terzo su tre chiuso a metà**: `ensure_rates_multi_source` ha ricevuto il
>   commento `# Intentionally unwired` (P1-15, `fx.py:389`); le due decisioni di prodotto
>   (`compute_wac_iterative_multi_broker` → P2-2, `AssetMetadataService` → P2-3) restano
>   **aperte**.
> - **#5** ✅ (P1-13, Lane D + fix coordinatore): `sitecustomize`
>   (`backend/test_scripts/_coverage_sitecustomize/`) + `COVERAGE_PROCESS_START` cablati sui
>   5 path di spawn (`scripts/test_runner/_common.py:37`, `_server.py:159`, …). Fuori pista
>   risolto in corsa: conflitto con lo sitecustomize di Homebrew → chain-exec. Risultato
>   misurato: `spawn_worker.py` ora coperto all'**87 %** (prima invisibile).
> - **#6** ✅ (P1-2) — **risolto diversamente**: `C901` abilitato con `max-complexity = 10`
>   (non 25; decisione utente), 199 siti triagiati (173 noqa giustificati, 26
>   `TODO(P2-refactor)`). I 35 C901 BRIM sono fra i marcati — la riduzione resta aperta
>   (P4-3), il gate ora impedisce il peggioramento.
> - **#7** ✅ (P1-18, 03/09): misura rieseguita — `identifier_utils.py` all'**80 %**
>   (esercitato da `merge_assets` via `test_asset_merge_api.py`, chiusura indiretta
>   confermata); copertura backend test **91 %** complessiva.

---

## Nuovi rilievi

1. **Nessun nuovo rilievo di gravità.** La crescita della suite (+25 file backend,
   +spec E2E) è avvenuta mantenendo la disciplina di registrazione: tutti i nuovi file
   delle ondate beta — `test_borsa_italiana_errors.py`, `test_justetf_errors.py`,
   `test_snb_errors.py`, `test_yahoo_finance_errors.py` (`_backend_services.py:62-65`),
   `test_brim_parse_race.py` (`:403`), `test_scheduler_joblog_builders.py` (`:637`),
   `test_coverage_js_adapter.py` (`_backend_utils.py:67`) e perfino il non-tracciato
   `test_update_js_cache.py` del working tree (`_backend_utils.py:139` +
   `add_test("js-cache-fail-loud", …, isolation="pure")` nel diff non committato) —
   sono registrati nel runner.
2. **I test aggiunti nel working tree beta sono di qualità alta**: campionati tutti i
   diff (`test_transactions_api.py`, `test_tx_balance_walk.py`,
   `test_ai_export_components_drawdown_context.py`, `test_portfolio_service.py`,
   `test_risk_signal_plugins.py`): solo asserzioni a valori esatti
   (`Decimal("1200")`, `pytest.approx([-45.0, …])`, codici errore specifici
   `balanceAsset`/`pairDeleteIncomplete`) con messaggi diagnostici. Nessuna asserzione
   tautologica.
3. **`_lastrun_lots.log`** (27/07, il fallimento FX originale di L2.2) è ancora in
   `backend/test_scripts/` ma è **gitignored** (`git check-ignore` conferma): nessuna
   azione.

---

## Cross-reference

- Report 17 della presente tornata: [17_stabilizzazione.md](17_stabilizzazione.md) (B1/B2/B3, buco copertura frontend — chiuso).
- Fonte: [12_test_coverage.md](../../phases/05_cleanAudit/12_test_coverage.md); esecuzione S1–S3: [15_esecuzione_s1_s3.md](../../phases/05_cleanAudit/15_esecuzione_s1_s3.md).
- Codice morto: report 02/03/04/07 dell'audit originario; complessità: report 11 (§ K5); test walk E2E: report 16.
- Skill aggiornate: `.github/skills/devpy-tools/testing-backend/SKILL.md` (§ Coverage, :157-229), `testing-frontend` (copertura JS).
- Verifica gemella su AI Export: [13_ai_export.md](13_ai_export.md) (stessa tornata).
