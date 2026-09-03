# 99 — Task riesumati e backlog consolidato

> **Release 2 · Phase 0 · 08_newCleanAndDocumentation_audit** · 2026-09-02
> Deduplica dei task emersi da tutti i report di questa tornata (le stesse voci
> comparivano in 2-3 report ciascuna). Stima: **S** < 1 h · **M** < mezza giornata ·
> **L** ≥ 1 giorno / multi-sessione. Ogni voce rimanda al report d'area per
> l'evidenza `file:riga` completa.
>
> Conteggi: **P0 = 5 · P1 = 18 · P2 = 9 · P3 = 28 · P4 = 8** — 68 voci consolidate
> (da ~95 voci greffe nei report d'area).

---

## P0 — Bug vivi, rischio concreto (fare per primi)

> ✅ **TUTTI E 5 ESEGUITI IL 02/09** (stessa giornata dell'audit, branch `dev_release2`,
> working tree): P0-1 con decisione utente «per-utente, seeded dal default globale, EUR
> ultima spiaggia» → nuovo helper `settings_service.get_effective_base_currency()` + test
> della catena e del ramo `target_currency=None`; P0-2 `logger.debug` al posto del `pass`;
> P0-3 `S110` aggiunto alla select ruff (puntuale) + 8 swallow onesti convertiti a
> `contextlib.suppress`; P0-4 `_resize_image` sync dietro `asyncio.to_thread`; P0-5 preload
> unico + aggregati GROUP BY (20 patch senza valuta → **1 SELECT**; 3 con valuta → **4**,
> pinnato in test). Il wedge FX quadratico scoperto nel collaudo E1 è stato fixato nella
> stessa tornata (dedup O(1) + tetto 10). Run full seriale a fine giro: 14/15 (rossi =
> 3 ai-export contract pre-esistenti su HEAD). Restano da P0 i due N+1 verbatim secondari
> (`portfolio_api.py:49`, `fx.py:965,1014`) → tracciati nel piano P1.

| # | Task | Stima | Fonte | Stato 02/09 |
|---|---|---|---|---|
| P0-1 | **`portfolio_engine.py:1967` — chiamata rotta + chiave fantasma.** Sostituire con `get_setting_value(self.db, "default_currency", "EUR")` (fissare import `:42`), allineare gli altri 2 call site (`lots_analysis_service.py:581`, `portfolio_service.py:719`), aggiungere un test che chiama `calculate()` senza `target_currency`. Chiude insieme i reperti 🔴 2 e 4 del vecchio indice. Richiede la micro-decisione `default_currency` vs nuova chiave `base_currency` | **S** | [02](02_services_core.md) T1-T2 · [14](14_backlog_ed_esecuzione.md) #3 | ✅ Fatto — variante decisa: helper `get_effective_base_currency` (per-utente → globale → EUR) |
| P0-2 | **S110 regredito in `cache_utils.py:82`** (`except Exception: pass`, commit `c8cd0fb2`): loggare con `logger.debug(..., exc_info=True)`. 2 righe, riporta l'invariante a zero | **S** | [11](11_crosscutting.md) #1 · [04](04_providers.md) T1 | ✅ Fatto + test del log debug |
| P0-3 | **Gate anti-regressione per i livelli «zero»**: aggiungere `S110` (e valutare `TRY400`) alla `select` ruff in `pyproject.toml:72-81` o un check CI; senza gate, la bonifica del 05/08 si è riaperta in 8 giorni | **S** | [11](11_crosscutting.md) #2 · [14](14_backlog_ed_esecuzione.md) #2 | ✅ Fatto (solo S110; TRY400 resta al P1-3 che lo precede) |
| P0-4 | **Pillow bloccante in `serve_file`** (`uploads.py:423-440`, ramo anteprima immagini in handler async): `await asyncio.to_thread(...)`. Violazione Async I/O Rule presente dal 2026-01-20, **sfuggita al primo audit** | **S** | [01](01_api_layer.md) N1 | ✅ Fatto (helper sync `_resize_image` + `to_thread`; ramo `ratio>=1` invariato) + test spy |
| P0-5 | **N+1 nel bulk patch** (`asset_source.py:4191-4284`, ~7 query/elemento): preload `IN (...)`, conteggi `GROUP BY`, lookup in memoria. Miglior rapporto valore/costo dell'audit, intatto dopo un mese. Con lui i due N+1 verbatim `portfolio_api.py:49` e `fx.py:965,1014` | **S/M** | [03](03_services_pricing_fx.md) T1 · [01](01_api_layer.md) A3 | ✅ Fatto sul bulk patch; i due verbatim secondari → piano P1 |

---

## P1 — Quick win tecnici (S, nessuna decisione di prodotto)

| # | Task | Fonte |
|---|---|---|
| P1-1 | Chiudere gli ultimi **6 endpoint senza `response_model`** (`system.py` ×1, `settings.py` ×3, `uploads.py` ×2) cablando gli schemi già scritti, poi `./dev.py api sync` | [01](01_api_layer.md) A4 · [07](07_schemas_utils.md) T2 |
| P1-2 | **`max-complexity = 25` in `pyproject.toml`** (la voce 1.2 era nulla perché la config non esisteva: va *creata*). Rende C901 utilizzabile: 19 funzioni invece di 157 | [11](11_crosscutting.md) #4 · [12](12_test_coverage.md) #6 |
| P1-3 | Convertire i **55 `TRY400`** in `logger.exception` (erano 53: +2 in un mese) | [11](11_crosscutting.md) #5 · [01](01_api_layer.md) A8 |
| P1-4 | Pulizia orfani backend: `_price_on_date` (`portfolio_engine.py:1172`), `_bulk_load_asset_prices` + `_get_quote_base_map` (test-only), alias `ValuationResult.unit_price` (test-only), 4 `aggregate_*` mai usati, `cleanup_test_database()` | [12](12_test_coverage.md) #1-3 · [02](02_services_core.md) T4/T6/T7 · [17](17_stabilizzazione.md) #1 |
| P1-5 | Pulizia stringhe stale del test runner (`_backend_services.py:408,466,830,836` citano simboli rimossi in S1–S3) | [02](02_services_core.md) T9 |
| P1-6 | **`git rm utils/financial/fifo_utils.py`** (148 righe + 11 test) **dopo** mappatura casi limite su `FifoLotEngine`; aggiornare registration `_backend_services.py:463`. Resta l'unica rimozione a rischio medio | [02](02_services_core.md) T5 · [14](14_backlog_ed_esecuzione.md) #20 |
| P1-7 | Orfani frontend nuovi e vecchi: `uploadBrimFile`, `downloadFxBackup`, export default `zodios-client.ts:210`, nuovi orfani beta (`getResolvedStart/End`, `eventsSince/...`, `_debugStack`, `debugAssert`, `isReleaseVersion/isDirtyVersion`, ri-export date/time/number), alias `getTransactionTypeIconUrl` | [08](08_frontend_state_api.md) T5/T7/T9 · [14](14_backlog_ed_esecuzione.md) #4 |
| P1-8 | **96 voci i18n morte `importWizard.*` (24 chiavi × 4 lingue)** + `transactions.errors.cannotLinkEventNoAsset` ×4 + **30 chiavi `aiExport.dataset.*` orfane** (cresciute da 22) | [09](09_frontend_components.md) C3/C4 · [14](14_backlog_ed_esecuzione.md) #12 |
| P1-9 | 22 ri-esportazioni morte nei barrel vivi + ~30 tipi orfani componenti (24 nel barrel `table/`) + 43 tipi `lib/types/` da campionare contro `generated.ts` + 5 fixture e2e orfane | [09](09_frontend_components.md) C1/C2/C5 · [08](08_frontend_state_api.md) T8 |
| P1-10 | Mezza invalidazione grafo valute: completare il confronto di `cachedProvidersHash` **o** rimuovere campo + `invalidateCurrencyGraph` (`currencyGraphStore.ts:35-36,96,135-139`) | [08](08_frontend_state_api.md) T3 |
| P1-11 | Bump `implementation_version` drawdown a `1.1.0` (policy `signal_plugin_guide.md:586`) + decidere metadati componenti AI export drawdown (`version=1`/`WINDOWED` vs payload full-history) **prima del tag V1** | [05](05_signals_risk.md) T2 · [13](13_ai_export.md) #3 |
| P1-12 | Registrare la regola E2 («l'esclusione va alla reportistica, non alla raccolta riferimenti») nella skill di audit — la trappola si è ripetuta identica in questa tornata | [05](05_signals_risk.md) T1 |
| P1-13 | `COVERAGE_PROCESS_START` + `sitecustomize` per vedere `spawn_worker.py` nella copertura | [12](12_test_coverage.md) #5 · [14](14_backlog_ed_esecuzione.md) #7 |
| P1-14 | Generalizzare `expectChartCanvas()` in `e2e/fixtures/` e applicarlo a `brokers-detail.spec.ts`, `fx-detail.spec.ts:44-51`, `asset-data-editor.spec.ts:41`, `risk-analysis.spec.ts` — chiude i reperti A3-A6 (test container-only) del report 16 | [14](14_backlog_ed_esecuzione.md) #11 |
| P1-15 | Commento `# Intentionally unwired` su `ensure_rates_multi_source` (`fx.py:389`) + decisione `get_provider`/`list_plugin_classes` (rimozione o docstring corretta) | [03](03_services_pricing_fx.md) T4 · [04](04_providers.md) T3 |
| P1-16 | Prova della migrazione `002` (+ nuova `5b1333fa6b07`) su DB 1.0.1 reale popolato — prerequisito di release scoperto da un mese | [06](06_db_models.md) T3 · [14](14_backlog_ed_esecuzione.md) #24 |
| P1-17 | Igiene minore: RUF022 `__all__` (decidere regola o noqa), `get_version_info` (esporre o rimuovere), ramo morto `fallbackUrl` in `dashboard-check.js`, etichetta «LRU», `get_asset_provider` (adottare o rimuovere), convergenza 3 helper JSON-safe | [06](06_db_models.md) T4 · [07](07_schemas_utils.md) T5 · [03](03_services_pricing_fx.md) T4/T7 · mkdocs T17/T18 |
| P1-18 | Rieseguire la **suite completa** a run corrente conclusa e aggiornare il dato 90,66 % dichiarando le categorie (regola L1); alla stessa misura verificare chiusura `identifier_utils.py` ora che `merge_assets` lo esercita, e incrociare coverage JS × knip | [17](17_stabilizzazione.md) #2/#5 · [12](12_test_coverage.md) #7 · [14](14_backlog_ed_esecuzione.md) #25 |

---

## P2 — Decisioni di prodotto (bloccano i reperti; solo il proprietario decide)

| # | Decisione | Conseguenza | Fonte |
|---|---|---|---|
| P2-1 | `require_email_verification`: implementare la verifica email **o** rimuovere la chiave da schema/UI/i18n/docs. La UI promette ciò che il sistema non fa da oltre un mese | codice M / rimozione S | [01](01_api_layer.md) A2 · [mk2](mkdocs/02_admin_teoria_sito.md) T14 |
| P2-2 | `compute_wac_iterative_multi_broker` (`portfolio_service.py:347`): endpoint WAC cross-broker **o** rimozione funzione + 5 test | M | [02](02_services_core.md) T3 · [12](12_test_coverage.md) #4 |
| P2-3 | `AssetMetadataService` (`asset_source.py:4592`): cablare `compute_metadata_diff` come audit trail **o** rimuovere classe + test | S dopo decisione | [03](03_services_pricing_fx.md) T3 |
| P2-4 | `cache_utils`: endpoint admin `POST /admin/cache/clear` **o** rimozione delle 3 funzioni. Oggi l'unica invalidazione cache è il riavvio | M | [07](07_schemas_utils.md) T3 · [14](14_backlog_ed_esecuzione.md) #15 |
| P2-5 | Scorciatoia di cassa nella pagina broker (reperto B1 report 16): reintrodurre deposito/prelievo contestuale o confermare la via generica con `defaultBrokerId` | S dopo decisione | [14](14_backlog_ed_esecuzione.md) #21 |
| P2-6 | `suggest_events` (`transactions.py:257`): mai collegato dal 2026-07 (`c3faae19`) — cablare alla UI o rimuovere | S | [14](14_backlog_ed_esecuzione.md) #22 |
| P2-7 | Famiglia orfani frontend con logica di dominio: `txStoreGetPartner/Main` (gli altri 2 li ha adottati l'import wizard), helper `availableLanguages`/`currentLanguageFlag/Name` (DRY orfano: adottare nel `LanguageSelector`), helper coperti da test ma mai chiamati in produzione (`cleanUrlParams`, `hasActiveFilters`, 3× `imageCrop`) | S ciascuno | [08](08_frontend_state_api.md) T1/T4/T6 |
| P2-8 | **11 property orfane `*_cur`/conteggi** (`schemas/`): la raccomandazione è cambiata — l'adozione non è più economica (190 siti `Currency(code=` inline in 50 file). Rimuovere property + test dedicati. Eccezioni da valutare: `failed_count`, `total_cash_positions`, `total_asset_positions` | S | [07](07_schemas_utils.md) T1 |
| P2-9 | Consolidamento `settings_service` (221 righe) vs `global_settings_service` (102): un solo punto d'ingresso impostazioni | L | [07](07_schemas_utils.md) T4 |

---

## P3 — Debito documentale mkdocs (verificato voce per voce; dettaglio nei report mkdocs)

**Correzioni puntuali EN (tutte S)** — elenco compatto; evidenza doppia (docs+codice)
nei report [mk1](mkdocs/01_user_e_flussi.md) (D1-D19, N1-N9) e [mk2](mkdocs/02_admin_teoria_sito.md) (T1-T18):

| # | Task | Fonte |
|---|---|---|
| P3-1 | URL `custom_startup.sh` 404 (riprodotto con curl) in `service_exposure.*.md:416,420` | mk2 T1 |
| P3-2 | `./dev.py mkdocs --gallery` → `mkdocs gallery` in `docker_advanced.*:173` | mk2 T2 |
| P3-3 | **Backup Docker senza cautela WAL**: `docker_advanced.*:304-315` ancora `cp app.db` a container attivo (il fix del 05/08 toccò solo `filesystem.*:119`) | mk2 T3 |
| P3-4 | DocsLink WAC → 404 (`WacPreviewSection.svelte:447`, path pagina sbagliato) | mk2 T4 |
| P3-5 | Default benchmark segnali (linear 2, compound 8, sine 15/45) disallineati EN+IT/FR/ES | mk2 T5 |
| P3-6 | Settings: completare Categorie (A4/A5), riallineare `scheduler_history_sync_times`/`scheduler_timezone` alla semantica post-31/08 (lo «stored in UTC» è falso dal commit `c8bdbaea`) | mk2 T6/T7 |
| P3-7 | Asset types: codice `INDEX`; riga justETF in sorgenti DIVIDEND; nota late-interest in maturity | mk2 T8 |
| P3-8 | **Fail-loud font/JS Docker non documentato** in nessuna pagina admin (worktree 02/09) | mk2 T9 |
| P3-9 | **`sharing.en.md` da riscrivere**: aggregation non più «futura»; **self-leave e cascata last-owner (cancella broker+transazioni+report) mai documentati**; share solo OWNER | mk2 T10 (M) |
| P3-10 | Alt-text gallery «Delete Linked Pair Modal» (modale eliminata) + riga delete→bulk in transactions | mk2 T11 |
| P3-11 | Commento `user create` (sempre superuser via CLI); percorso `financial_math.py` → `scheduled_investment.py:71`; refuso DIVIDEND/Scheduled Investment | mk2 T12/T13 |
| P3-12 | `performance-metrics/index.*:164-170`: «link directly» → percorso a due passi via kpi-cards | mk2 T15 |
| P3-13 | KPI cards: due percentuali sbagliate (Card 1 denominatore, Card 3 = ROI since-inception) | mk1 D1 |
| P3-14 | Holdings 13 colonne reali; togliere riga «Date Format» da preferences; togliere «(backend + frontend)» da about | mk1 D2-D4 |
| P3-15 | **Generic CSV (critical)**: togliere `TRANSFER`/`FX_CONVERSION`/`CASH_TRANSFER` da `generic-csv.*.md` o implementarli (docs S / codice L) | mk1 D6 |
| P3-16 | Sharing: esempio Joint Account con due Owner (F4) | mk1 D7 |
| P3-17 | «PDF» da 4 superfici + eToro CSV-only + cella Directa CSV/XLSX + campi duplicati `import/index.*:282` | mk1 D8-D11 |
| P3-18 | **SNB (critical)**: `snb.*.md` dice daily, il provider produce medie **mensili** (~25 valute) | mk1 D12 |
| P3-19 | `fx/detail/signals.*:51-56` → 2 task reali; azioni menu FX; preset chart (1W–2Y+YTD+MAX + fill) | mk1 D13-D15 |
| P3-20 | AI Export: «thirteen»→«eleven», «Signals header»→«page toolbar», nota L# riga-embedded, nota drawdown full-history | mk1 D16-D19 |
| P3-21 | **`assets/detail/signals.*:55-62` promette 5 task AI Export Asset, 4 inesistenti nel catalogo** (verificato: solo `position_review` e `market_analysis` nel dominio ASSET) — pagina caduta nella fessura fra i report 01 e 04 del vecchio audit | mk1 N3 |
| P3-22 | `files.*.md`: togliere «Reprocess» (mai esistito), semantica Delete, «runs the guided Import Wizard» | mk1 N4 |
| P3-23 | `assets/index.*`: context menu (sync/refresh/merge/delete) + Live Ticker (Assets list/detail, non Dashboard) | mk1 N5 |
| P3-24 | Drag-and-drop «nella lista» da 3 pagine (resta vero nel wizard); label «Add Transaction»/«Add Broker» | mk1 N6/N7 |
| P3-25 | **Riallineare `brokers/import.*.md` al wizard a 7 step** (4 + 3 condizionali) — la pagina descrive il wizard pre-rework di agosto | mk1 N1 (M) |
| P3-26 | Riscrivere sezione Import di `getting-started.*.md` (6 passi → flusso attuale, togliere PDF) | mk1 N2 (M) |
| P3-27 | **Batch traduzioni IT/FR/ES**: rinviato dal 05/08, ora a **due generazioni** di debito (include rework wizard, cli_tools, settings, benchmark, sharing) | mk1 N8 · mk2 T16 (M/L) |
| P3-28 | Opzionale tooling: `check-links` vs template literal annidati (falso positivo `${lang`) | mk1 N9 |

---

## P4 — Strutturali (M/L; nessuna avviata in un mese, 4 peggiorate)

| # | Task | Stima | Fonte |
|---|---|---|---|
| P4-1 | **Scissione di `asset_source.py`** (ora 5 162 righe, +362 in un mese): provider management / prezzi / metadata / bulk ops. Più urgente di un mese fa | L | [03](03_services_pricing_fx.md) T8 · [14](14_backlog_ed_esecuzione.md) 6.13 |
| P4-2 | Scomposizione `execute_batch` (115, ~640 righe) in handler per verbo con dispatch tabellare | L | [02](02_services_core.md) T8 · [11](11_crosscutting.md) #7 |
| P4-3 | Estrazione helper condivisi BRIM **un provider alla volta**, da `broker_credit_agricole.py` (`_parse_account_movements` = 71); chiude i 35 C901 BRIM identici da un mese e abilita la copertura dei rami errore | L | [04](04_providers.md) T2 · [17](17_stabilizzazione.md) #4 |
| P4-4 | `get_history_value` Yahoo (complessità 31, invariata) — provider più usato e più instabile | M | [04](04_providers.md) T4 |
| P4-5 | Migrazione Runes di `BrokerSharingPanel.svelte` (24 `$:`, in crescita) + due tab settings (9+9) — costa di più a ogni mese che passa | M | [11](11_crosscutting.md) #6 · [10](10_frontend_charts.md) G3 |
| P4-6 | Matrice dichiarativa per `validate_status_matrix` (`schemas/signals.py:1069`, 32) — trigger: prossimo `SignalStatus` | M | [05](05_signals_risk.md) T4 |
| P4-7 | Misura crescita cache store (registry/pool mai rilasciati) + decisione ciclo di vita | M | [08](08_frontend_state_api.md) T2 · [14](14_backlog_ed_esecuzione.md) #9 |
| P4-8 | Voci S6 restanti del vecchio backlog (6.2, 6.3, 6.4, 6.7, 6.8, 6.11, 6.12; 6.14 resta ⛔ sconsigliata) + TRY003 congelata finché TRY non entra in `select` | varie | [14](14_backlog_ed_esecuzione.md) #23/#26 |

---

## Ordine suggerito di attacco

1. **P0-1 → P0-2 → P0-4** (tre fix da poche righe che chiudono un TypeError certo, una
   regressione e una violazione async) + **P0-3** (il gate: altrimenti tra un mese si
   riverifica tutto di nuovo).
2. **P1-1, P1-2, P1-3** (ripristino tipizzazione API + segnale complessità
   utilizzabile + log) — mezza giornata complessiva.
3. **P2-1…P2-6** in un'unica sessione di decisioni: sei «tenere o tagliare» che
   sbloccano una dozzina di voci P1.
4. **P3** in due passate: correzioni puntuali EN (P3-1…P3-24, quasi tutte S) poi le
   due riscritture (P3-25, P3-26) e il batch traduzioni (P3-27).
5. **P4** uno alla volta, mai in parallelo fra loro.

## Cross-reference

Fonte storica: [`../phases/05_cleanAudit/14_backlog_per_complessita.md`](../../phases/05_cleanAudit/14_backlog_per_complessita.md)
(70 residue → 42 al 2026-08-05 → **35 aperte oggi**, più 23 voci nuove di questa
tornata fra regressioni, ondate beta e docs). Indice: [00_INDEX.md](00_INDEX.md).
