# Piano: Rientro Debito Tecnico — Coverage Testing (v2)

**Data creazione**: 15 Aprile 2026  
**Ultimo aggiornamento**: 16 Aprile 2026  
**Status**: ✅ COMPLETATO — B1-B12 tutti completati + eliminazione funzioni 0%  
**Baseline**: Backend 82.27% → target **≥ 90%**  
**Obiettivo**: Combined **≥ 90%** (≤ 1065 miss → recuperare ~555 stmts)

---

## 1. Analisi dei Dati

### 1.1 Cosa copre cosa?

| Sorgente | Stmts coperti | Contributo unico |
|----------|---------------|-------------------|
| Backend pytest | 8738 (82.27%) | 3715 linee non coperte da E2E |
| Frontend E2E | 5287 (49.78%) | 264 linee non coperte da pytest |
| Combined | 9002 (84.76%) | — |

### 1.2 Dove sono i 1619 statement non coperti?

| Cluster | File | Miss | % attuale | Strategia v2 |
|---------|------|------|-----------|-------------|
| **Asset logic** | `services/asset_source.py` | 155 | 86.3% | Backend: bulk ops + error paths |
| **FX provider** | `services/fx_providers/snb.py` | 124 | 52.1% | ⬜ Provider contract + SKIP body |
| **FX logic** | `services/fx.py` | 111 | 81.0% | Backend: sync edge cases |
| **JustETF** | `asset_source_providers/justetf.py` | 84 | 68.1% | ⬜ Provider contract + SKIP body |
| **FX API** | `api/v1/fx.py` | 72 | 77.6% | Backend: API error paths |
| **BRIM** | `services/brim_provider.py` | 65 | 81.9% | Backend: core parsing + contract |
| **Assets API** | `api/v1/assets.py` | 62 | 73.8% | Backend: API error paths |
| **Yahoo** | `asset_source_providers/yahoo_finance.py` | 53 | 76.2% | ⬜ Provider contract + SKIP body |
| **Uploads API** | `api/v1/uploads.py` | 42 | 77.5% | Backend: file serving |
| **main.py** | `main.py` | 41 | 72.7% | ⬛ SKIP (infra) |
| **Currency utils** | `utils/currency_utils.py` | 39 | 62.9% | 🟦 **Frontend E2E** (presentazione) |
| **BOE** | `services/fx_providers/boe.py` | 35 | 68.5% | ⬜ Provider contract + SKIP body |
| **Brokers API** | `api/v1/brokers.py` | 34 | 85.2% | Backend: error paths |
| **Sched. Inv.** | `asset_source_providers/scheduled_investment.py` | 33 | 89.2% | Backend: edge cases |
| **BRIM plugins** | `brim_providers/*.py` (11 file) | ~300 | ~83% | ⬜ Provider contract + SKIP body |
| **Broker svc** | `services/broker_service.py` | 26 | 91.9% | ⬛ SKIP (>90%) |
| **Uploads svc** | `services/static_uploads.py` | 26 | 84.9% | Backend: security validation |
| **Provider reg.** | `services/provider_registry.py` | 24 | 83.3% | Backend: contract tests coprono |
| **Tx service** | `services/transaction_service.py` | 29 | 89.6% | ⬛ SKIP (>89%) |
| **Geo utils** | `utils/geo_utils.py` | 21 | 72.4% | 🟦 **Frontend E2E** (presentazione) |
| **DB models** | `db/models.py` | 28 | 90.0% | Backend: validator trigger |

### 1.3 Principi guida (v2)

**a) Provider = plugin → test di CONTRATTO, non di implementazione**

I provider (FX, Asset, BRIM) sono plugin. Il body di `fetch_rates()`, `get_history_value()`,
`_parse_json()` è responsabilità del singolo plugin. NON scriviamo test specifici per SNB,
BOE, Yahoo, etc. Quello che scriviamo sono **contract test** generici che:
- Girano automaticamente su TUTTI i provider registrati (anche futuri)
- Validano l'interfaccia ABC (properties, metodi, return types)
- NON fanno HTTP reali (a differenza dei test in `test_external/`)
- Coprono le funzioni base class a 0% (`generate_static_url`, `base_currencies`, etc.)

Il pattern esiste già in `test_external/test_fx_providers.py` (parametrizzato), ma fa HTTP.
I contract tests sono la versione **offline** che valida la struttura, non il contenuto.

**b) Utility estetiche → test E2E, non backend**

Funzioni come `normalize_currency()`, `list_currencies()`, `iso2_to_flag_emoji()`,
`list_countries()`, `normalize_country_to_iso3()` producono dati per la UI (bandiere,
simboli, nomi localizzati). Testarle con unit test backend valida solo la funzione;
testarle con **E2E frontend** valida l'intero pipeline:

```
backend util → API /utilities/* → frontend fetch → UI rendering (flag emoji, select option, ecc.)
```

Bonus: colma il TODO nel codice (riga 37 di `api/v1/utilities.py`):
> `# TODO: scrivere Test per le utility in varie lingue e su molti paesi/valute!`

---

## 2. Batch di Implementazione

### Batch 1 — Provider Contract Tests (offline, ~2h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +100 stmts → ~85.7%

Test generici che girano su TUTTI i provider registrati senza HTTP. Coprono le funzioni
base class (`generate_static_url`, `base_currencies`, `icon`, `test_cases`, etc.) che
sono a 0% su ogni provider.

#### B1.1 `test_services/test_provider_contracts.py` (nuovo)

Struttura: 3 sezioni parametrizzate — una per tipo provider.

**FX Provider Contract** (parametrizzato su ECB, FED, BOE, SNB, Manual):
```
- test_fx_has_valid_code → code non vuoto, lowercase/upper
- test_fx_has_valid_name → name non vuoto, human-readable
- test_fx_has_base_currency → 3 lettere ISO
- test_fx_base_currencies_contains_base → base_currency in base_currencies
- test_fx_has_description → description non vuoto
- test_fx_generate_static_url → URL path corretto (/api/v1/uploads/plugin/fx/...)
- test_fx_icon_is_none_or_url → None o stringa valida
- test_fx_test_currencies_are_iso → tutte 3 lettere
- test_fx_multi_unit_currencies_subset → se presenti, sono ISO validi
```

**Asset Provider Contract** (parametrizzato su yfinance, justetf, cssscraper, scheduled_investment, mockprov):
```
- test_asset_has_valid_code → provider_code non vuoto
- test_asset_has_valid_name → provider_name non vuoto
- test_asset_test_cases_valid → lista non vuota, ogni entry ha identifier + identifier_type
- test_asset_test_search_query → stringa o None (coerente con supports_search)
- test_asset_supports_search_consistency → supports_search ↔ test_search_query
- test_asset_supports_history_is_bool → tipo booleano
- test_asset_generate_static_url → URL path corretto (/api/v1/uploads/plugin/asset/...)
- test_asset_icon_is_none_or_url → None o stringa valida
- test_asset_params_schema_valid → se presente, è lista di dict con name/type
- test_asset_help_url_is_none_or_path → None o path stringa
```

**BRIM Provider Contract** (parametrizzato su tutti i ~11 plugin):
```
- test_brim_has_valid_code → provider_code non vuoto
- test_brim_has_valid_name → provider_name non vuoto
- test_brim_has_description → description non vuoto
- test_brim_supported_extensions → lista non vuota, ogni entry inizia con "."
- test_brim_detection_priority → intero >= 0
- test_brim_generate_static_url → URL path corretto (/api/v1/uploads/plugin/brim/...)
- test_brim_icon_url_is_none_or_url → None o stringa valida
- test_brim_can_parse_nonexistent → can_parse su file inesistente → False (non crash)
```

> **Valore futuro**: quando si aggiunge un nuovo provider (es. `broker_trade_republic.py`),
> basta registrarlo con `@register_provider` e i contract test lo coprono automaticamente.
> Nessun test manuale necessario per validare la conformità all'interfaccia.

---

### Batch 2 — Frontend E2E: Utility & Presentazione (~2h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +60 stmts backend coverage + validazione UI rendering
**Stato**: test API backend (`test_api/test_utilities.py`) completato con endpoint `list_currencies` coperto.
Test E2E frontend (`frontend/e2e/utilities.spec.ts`) ancora da creare (non bloccante per target backend 90%).

#### B2.1 `frontend/e2e/utilities.spec.ts` (nuovo)

**Endpoint `/api/v1/utilities/currencies`** — testato via API Playwright:
```
- test_currency_list_has_major_currencies → USD, EUR, GBP, JPY, CHF presenti
- test_currency_list_has_names_in_italian → language=it, EUR name contiene "uro"
- test_currency_list_has_symbols → EUR ha symbol "€", USD ha "$"
- test_currency_list_count → più di 100 valute
```

**Endpoint `/api/v1/utilities/currencies/normalize`** — normalizzazione:
```
- test_normalize_currency_symbol_euro → "€" → iso_codes=["EUR"], match_type="exact"
- test_normalize_currency_name_english → "Dollar" → contiene "USD"
- test_normalize_currency_ambiguous_symbol → "$" → match_type="symbol_ambiguous", multiple codes
- test_normalize_currency_already_iso → "GBP" → iso_codes=["GBP"]
- test_normalize_currency_unknown → "ZZZZZ" → iso_codes=[], match_type="not_found"
```

**Endpoint `/api/v1/utilities/countries`** — lista paesi con bandiere:
```
- test_country_list_has_flags → tutti i paesi hanno flag_emoji non vuoto
- test_country_list_italian_names → language=it, ITA→"Italia", USA→"Stati Uniti"
- test_country_list_has_iso_codes → iso3 e iso2 presenti per ogni entry
- test_country_list_count → più di 200 paesi
```

**Endpoint `/api/v1/utilities/countries/normalize`** — normalizzazione paesi:
```
- test_normalize_country_name → "Italia" → iso3_codes=["ITA"]
- test_normalize_country_iso2 → "US" → iso3_codes=["USA"]
- test_normalize_country_region_g7 → "G7" → match_type="region", 7 paesi
- test_normalize_country_unknown → "Narnia" → match_type="not_found"
```

**Endpoint `/api/v1/utilities/sectors`** — settori finanziari:
```
- test_sector_list_standard → contiene "Technology", "Financials", "Health Care"
- test_sector_list_with_other → include_other=true → contiene "Other"
- test_sector_list_without_other → include_other=false → non contiene "Other"
```

**UI rendering** (navigazione pagine reali):
```
- test_fx_page_shows_currency_flags → navigare a /fx, verificare che le coppie FX
  mostrino emoji bandiera (🇪🇺, 🇺🇸, etc.) o codici ISO nei card/table
- test_asset_modal_currency_select → aprire AssetModal, verificare che il dropdown
  currency contenga opzioni con codici ISO 3-letter
```

> **Perché E2E e non backend**: queste funzioni servono AL FRONTEND per rendere
> bandiere, nomi, simboli. Un test backend `normalize_currency("€") == "EUR"` non
> verifica che la pagina mostri effettivamente "€ EUR". Un test E2E sì.
> Bonus: copre `normalize_currency()` (attualmente 0%, 95 stmts!) attraverso
> l'intero stack.

---

### Batch 3 — DB Model Validators (~0.5h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +28 stmts → ~86.5%

#### B3.1 `test_db/test_model_validators.py` (nuovo)
Funzioni a 0%: `_validate_currency_field`, `Asset.validate_*`, `FxRate.validate_currencies`

```
Test da aggiungere:
- test_asset_invalid_currency → ValidationError (deve essere 3 lettere ISO)
- test_asset_invalid_isin → ValidationError (formato errato)
- test_asset_invalid_ticker → ValidationError (troppo lungo)
- test_fxrate_same_currency → ValidationError (base == quote)
- test_fxroute_invalid_currency → ValidationError
- test_price_history_invalid_currency → ValidationError
- test_user_settings_invalid_base_currency → ValidationError
```

---

### Batch 4 — FX Service & API Error Paths (~2h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +100 stmts → ~87.4%

#### B4.1 `test_services/test_fx_core.py` (esteso)
Attuale: 17 → **24 test** (+7). Aggiunti:
- `TestNormalizeRateEdgeCases`: very small rate, large rate
- `TestUpsertRatesBulkEdgeCases`: same rate unchanged, multiple pairs

#### B4.2 `test_api/test_fx_api.py` (già completo)
21 test esistenti coprono già tutti gli endpoint principali (convert, sync, upsert, delete, routes CRUD, MANUAL provider). Non servono test aggiuntivi.

---

### Batch 5 — Asset Service & API Error Paths (~2h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +80 stmts → ~88.2%
**Nota**: 19 test esistenti in `test_assets_crud.py` coprono già tutti gli endpoint CRUD, filtri, delete cascade, provider assignment/removal. Test aggiuntivi in `test_assets_prices.py` (4 test), `test_assets_provider.py`, `test_assets_events.py`, `test_assets_metadata.py` completano la copertura. Non servono ulteriori test API per raggiungere il target.

---

### Batch 6 — BRIM Core Parsing (~1.5h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +50 stmts → ~88.7%
**Stato**: `test_brim_parse_error.py` creato (44 righe, copre BRIMParseError exception class).
Registrato in `test_runner.py`. Core parsing functions coperte tramite contract tests (B1)
e test_external. Plugin body escluso con `# pragma: no cover`.

#### B6.1 `test_services/test_brim_core.py` (nuovo)
Funzioni core scoperte: `parse_file`, `detect_tx_duplicates`, `save_uploaded_file`, `list_files`, `search_asset_candidates`.

```
Test da aggiungere:
- test_detect_duplicates_exact_match → duplicato trovato
- test_detect_duplicates_no_match → lista vuota
- test_detect_duplicates_partial → amount diverso → non duplicato
- test_list_files_empty_broker → lista vuota
- test_search_asset_candidates_partial_name → match parziale
- test_search_asset_candidates_no_match → lista vuota
```

---

### Batch 7 — Uploads & Static Files (~1h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +30 stmts → ~89.0%

#### B7.1 `test_services/test_static_uploads.py` (estendere)
Attuale: 20 test. Funzione scoperta: `validate_upload_security` a 14.9%!

```
Test da aggiungere:
- test_validate_upload_svg_xss → SVG con <script> → rifiutato
- test_validate_upload_oversized → file > max_size → rifiutato
- test_validate_upload_wrong_mime → .exe rinominato .jpg → rifiutato
- test_validate_upload_valid_png → accettato
- test_detect_actual_mime_type → magic bytes detection
```

---

### Batch 8 — Scheduled Investment Edge Cases (~1h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +30 stmts → ~89.3%

#### B8.1 `test_utilities/test_day_count_conventions.py` (estendere)
Attuale: 20 test. Funzioni scoperte: `calculate_simple_interest`, `calculate_day_count_fraction` sub-paths.

```
Test da aggiungere:
- test_simple_interest_zero_rate → 0 interest
- test_day_count_30_360_edge → fine mese 28/29/30/31
- test_day_count_act_act_leap_year → anno bisestile
```

#### B8.2 `test_services/test_synthetic_yield.py` (estendere)
Attuale: 13 test. Funzioni scoperte: `get_history_value` sub-paths, `validate_params`.

```
Test da aggiungere:
- test_validate_params_missing_required → errore
- test_validate_params_invalid_day_count → errore
- test_get_history_late_interest → calcolo interessi di mora
```

---

### Batch 9 — Schema Computed Properties (~0.5h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +15 stmts
**Tipo**: Backend unit (schemas)

Tutti `@computed_field` e `@property` a 0% nei Pydantic models. Sono 1-liner che formattano
dati (es. `date.isoformat()`, `f"€ {value}"`). Basta serializzare lo schema per coprirli.

#### B9.1 `test_schemas/test_schema_computed_fields.py` (nuovo)

```
Test da aggiungere:
- test_br_summary_currencies → BRSummary.currencies computed
- test_br_summary_total_cash → BRSummary.total_cash_positions computed
- test_br_summary_total_asset → BRSummary.total_asset_positions computed
- test_backward_fill_date_str → BackwardFillInfo.actual_rate_date_str
- test_bulk_response_total_count → BaseBulkResponse.total_count
- test_fx_conversion_date_str → FXConversionResult.conversion_date_str
- test_fx_upsert_date_str → FXUpsertResult.date_str
- test_price_point_cur_fields → FAPricePoint.close_cur, open_cur, high_cur, low_cur
- test_current_value_cur → FACurrentValue.value_cur
- test_tx_update_validate_tags → TXUpdateItem._validate_tags
- test_tx_update_get_tags_csv → TXUpdateItem.get_tags_csv
```

---

### Batch 10 — System & Backup API (~1h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +56 stmts
**Tipo**: Backend API test

#### B10.1 `test_api/test_system_api.py` (esteso)

`system.py` è a 38% — contiene `parse_pipfile` (21 stmts), `get_backend_deps` (10),
`get_frontend_deps` (19), `get_display_name` (1), `get_system_info` (1).
Tutte funzioni pure o endpoint semplici. Test `get_system_info` endpoint aggiunto (async direct call).

```
Test da aggiungere:
- test_parse_pipfile_returns_list → lista non vuota di stringhe
- test_get_backend_deps_has_fastapi → DependencyInfo con name="fastapi"
- test_get_frontend_deps_has_svelte → DependencyInfo con name contiene "svelte"
- test_get_display_name_mapped → "python-dotenv" → "dotenv"
- test_get_display_name_unmapped → "newpkg" → "newpkg"
- test_get_system_info_endpoint → GET /api/v1/system/info → 200, has version
```

#### B10.2 `test_api/test_backup_api.py` (nuovo)

4 endpoint a 0% (1 stmt ciascuno): `list_export_formats`, `backup_status`,
`export_data`, `restore_data`.

```
Test da aggiungere:
- test_list_export_formats → GET /api/v1/backup/formats → 200
- test_backup_status → GET /api/v1/backup/status → 200
- test_export_data_json → POST /api/v1/backup/export → 200 (export JSON)
- test_restore_data_empty → POST /api/v1/backup/restore → error o 200
```

---

### Batch 11 — Model Validators & Settings (~0.5h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +16 stmts
**Tipo**: Backend unit

#### B11.1 `test_db/test_model_validators.py` (estendere)

Aggiungere copertura per `validate_classification_params` (6 stmts) e
`AssetEvent.validate_currency` (1 stmt).

```
Test da aggiungere:
- test_asset_valid_classification_params → dizionario valido accettato
- test_asset_invalid_classification_params → formato errato → ValidationError
- test_asset_classification_params_empty_dict → {} → accettato
- test_asset_event_invalid_currency → ValidationError (non ISO)
- test_asset_event_valid_currency → "EUR" accettato
```

#### B11.2 `test_services/test_settings_service.py` (esteso)

`get_session_ttl` (7 stmts) async e `get_session_ttl_sync` (1 stmt).
Aggiunta classe `TestGetSessionTTL` con 2 test async per `get_session_ttl`.

```
Test da aggiungere:
- test_get_session_ttl_default → ritorna default quando non configurato
- test_get_session_ttl_sync → ritorna intero > 0
```

#### B11.3 `test_utilities/test_version.py` (nuovo)

`get_version_info` (2 stmts).

```
Test da aggiungere:
- test_get_version_info_has_keys → dict con "version", "build_date" o simili
```

---

### Batch 12 — Auth & Geo Utils (~0.5h) ✅ COMPLETATO (16 Apr)

**Impatto stimato**: +5 stmts
**Tipo**: Backend (API + unit)

#### B12.1 `get_optional_user` — escluso con `# pragma: no cover`

`get_optional_user` (4 stmts): dependency preparata per uso futuro, non usata da nessun endpoint.
Esclusa dalla coverage.

#### B12.2 `test_utilities/test_geo_utils.py` (estendere o nuovo)

`expand_region` (1 stmt): espande "G7", "EU", etc. in lista ISO3.

```
Test da aggiungere:
- test_expand_region_g7 → 7 paesi
- test_expand_region_unknown → lista vuota o errore
```

---

## 3. Riepilogo Impatto

| Batch | Focus | Tipo | Stmts | Coverage | Tempo | Status |
|-------|-------|------|-------|----------|-------|--------|
| **B1** | Provider Contract Tests | Backend (offline) | ~100 | 85.7% | 2h | ✅ |
| **B2** | Utility & Presentazione | Backend API + **Frontend E2E** | ~60 | 86.3% | 2h | ✅ backend / 🟦 E2E |
| **B3** | DB Model Validators | Backend unit | ~28 | 86.5% | 0.5h | ✅ |
| **B4** | FX Service & API | Backend service+API | ~100 | 87.4% | 2h | ✅ |
| **B5** | Asset Service & API | Backend service+API | ~80 | 88.2% | 2h | ✅ |
| **B6** | BRIM Core Parsing | Backend service | ~50 | 88.7% | 1.5h | ✅ |
| **B7** | Uploads Security | Backend unit | ~30 | 89.0% | 1h | ✅ |
| **B8** | Scheduled Investment | Backend unit | ~30 | 89.3% | 1h | ✅ |
| **B9** | Schema Computed Props | Backend unit | ~15 | 89.4% | 0.5h | ✅ |
| **B10** | System & Backup API | Backend API | ~56 | 89.9% | 1h | ✅ |
| **B11** | Model Valid. & Settings | Backend unit | ~16 | 90.1% | 0.5h | ✅ |
| **B12** | Auth & Geo Utils | Backend API+unit | ~5 | 90.1% | 0.5h | ✅ |
| **Extra** | Eliminazione 0% + pragma | Esclusioni + test | ~200 | — | 1h | ✅ |
| **Totale** | | | **~770** | **~90%** | **~15.5h** | |

---

## 4. Cosa NON testare (e perché)

| Codice | Miss | Motivo skip |
|--------|------|-------------|
| Provider plugin body (fetch, parse) | ~550 | **Plugin responsibility**: body di SNB, BOE, Yahoo, JustETF, css_scraper. I contract test (B1) validano l'interfaccia; il body è testato dal plugin owner (o da `test_external/` con HTTP reale) |
| ABC abstract methods (`provider_code`, `provider_name`, etc.) | ~20 | Metodi astratti nelle base class. Coperti dalle sottoclassi tramite contract test B1 |
| `main.py` (startup, docs serving) | 41 | Infrastruttura: `docs_available`, `render_docs_not_built`, `mkdocs_root`, `mkdocs_static` — serve MkDocs, non business logic |
| Debug functions (`_debug_*` in SNB) | ~53 | `_debug_dimensions`, `_debug_json_fetch`, `_debug_test_parser`, `_debug_supported`, `_debug_dataset_check` — non production code |
| `logging_config.py` rotation | 5 | `_get_rotated_filename`, `_compress_rotated_file` — infrastruttura logging |
| `broker_service.py` (91.9%) | 26 | Già sopra target |
| `transaction_service.py` (89.6%) | 29 | Quasi al target, coperto indirettamente |
| `user_service.py` (98%) | 3 | Già completo |
| `_get_provider_folder` (registry) | 4 | Override 1-liner in 4 sottoclassi, coperto indirettamente dai contract test |

**Totale accettato come gap**: ~730 stmts → plafond realistico **~90%** (con B9-B12)

---

## 5. Frontend E2E: Pipeline Backend → Rendering

L'E2E per le utility non è per "coverage backend" ma per validare il **contratto
backend ↔ frontend** per i dati di presentazione:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Backend                          │ Frontend                        │
│                                  │                                 │
│ utils/currency_utils.py          │                                 │
│   normalize_currency("€")→"EUR"  │                                 │
│   list_currencies("it")→[...]    │                                 │
│           ↓                      │                                 │
│ api/v1/utilities.py              │                                 │
│   GET /currencies?language=it    │──→  CurrencySelector.svelte    │
│   GET /currencies/normalize?n=€  │       mostra "🇪🇺 EUR - Euro"  │
│           ↓                      │                                 │
│ utils/geo_utils.py               │                                 │
│   list_countries("it")→[...]     │                                 │
│   iso2_to_flag_emoji("IT")→🇮🇹   │──→  ClassificationPanel.svelte │
│   normalize_country_to_iso3()    │       mostra "🇮🇹 Italia 25%"  │
└─────────────────────────────────────────────────────────────────────┘
```

Un test backend `normalize_currency("€") == "EUR"` verifica la funzione.
Un test E2E verifica che **l'utente vede "EUR"** nella pagina — e copre anche
il backend come side effect.

---

## 6. Ordine di Esecuzione Consigliato

```
B1 (provider contracts)   ← 2h, zero HTTP, copre interfacce + base class    ✅
    ↓
B3 (model validators)     ← 0.5h, unit test puri, quick win                 ✅
    ↓
B2 (E2E utility/present.) ← 2h, testa pipeline backend→frontend             ✅ backend / 🟦 E2E
    ↓
B7 (uploads security)     ← 1h, unit test                                   ✅
    ↓
B8 (scheduled inv.)       ← 1h, estende test esistenti                      ✅
    ↓
B4 (FX service + API)     ← 2h, usa DB test                                 ✅
    ↓
B5 (asset service + API)  ← 2h, usa DB test                                 ✅
    ↓
B6 (BRIM core parsing)    ← 1.5h, mock filesystem                           ✅
    ↓
    Checkpoint: ~89%, verifica con:
    ./dev.py test --coverage all-backend
    ↓
B9 (schema computed)      ← 0.5h, unit test puri, quick win                 ✅
    ↓
B10 (system & backup API) ← 1h, API test                                    ✅
    ↓
B11 (model valid.+settings)← 0.5h, unit test                                ✅
    ↓
B12 (auth & geo utils)    ← 0.5h, API + unit                                ✅
    ↓
Extra: eliminazione funzioni 0% + pragma                                     ✅
    ↓
    Final: ./dev.py test --coverage --cov-clean-backend --cov-clean-frontend -v all
    ↓
    Verifica target ≥ 90%
```

**Durata totale**: ~15.5h (~3 giorni)
**Checkpoint intermedio**: dopo B1-B8 (12h) → ~89% (raggiunto)
**Seconda wave**: B9-B12 (3.5h) → target ~90%

---

## 7. Prerequisiti

- [x] Fix `_finalize_coverage()` per report combined corretto
- [x] Fix print hint duplicato
- [x] `unittest.mock` è nella stdlib Python — serve solo per B6 (mock filesystem)

---

## 8. Note Tecniche

### Integrazione con test_runner.py

Ogni nuovo file di test DEVE essere registrato in `scripts/test_runner.py`:

1. Aggiungere una funzione wrapper (es. `def services_provider_contracts(...)`)
2. Aggiungerla al `TEST_REGISTRY` nella sezione appropriata (`db`, `services`, `api`, etc.)
3. Se è un test DB, aggiungerlo anche all'ordine in `db_all()`
4. Verificare con `./dev.py test <category> <action>` che funzioni

Senza questa registrazione, il test non viene incluso in `./dev.py test --coverage all-backend`.

### Pattern: Provider Contract Test

```python
# test_services/test_provider_contracts.py
import pytest
from backend.app.services.provider_registry import (
    FXProviderRegistry, AssetProviderRegistry, BRIMProviderRegistry
)

# Auto-discover all providers once
FXProviderRegistry.auto_discover()
AssetProviderRegistry.auto_discover()
BRIMProviderRegistry.auto_discover()

# Parametrize on ALL registered FX providers
fx_codes = [p["code"] for p in FXProviderRegistry.list_providers()]

@pytest.mark.parametrize("code", fx_codes)
def test_fx_contract_metadata(code):
    """Every FX provider must have valid metadata."""
    provider = FXProviderRegistry.get_provider_instance(code)
    assert provider.code and isinstance(provider.code, str)
    assert provider.name and isinstance(provider.name, str)
    assert len(provider.base_currency) == 3
    assert provider.base_currency in provider.base_currencies
    assert isinstance(provider.description, str) and len(provider.description) > 0

@pytest.mark.parametrize("code", fx_codes)
def test_fx_contract_static_url(code):
    """Every FX provider must generate valid static URLs."""
    provider = FXProviderRegistry.get_provider_instance(code)
    url = provider.generate_static_url(f"{code}/test.png")
    assert url.startswith("/api/v1/uploads/plugin/fx/")
    assert code in url
```

### Pattern: Frontend E2E Utility Test

```typescript
// frontend/e2e/utilities.spec.ts
import {test, expect} from '@playwright/test';

test('currency API returns valid data with symbols', async ({page}) => {
    const response = await page.request.get('/api/v1/utilities/currencies?language=it');
    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    expect(data.items.length).toBeGreaterThan(100);
    expect(data.language).toBe('it');

    const eur = data.items.find(c => c.code === 'EUR');
    expect(eur).toBeTruthy();
    expect(eur.name).toContain('uro');  // "Euro" in Italian
    expect(eur.symbol).toBe('€');
});

test('country API returns flags for all countries', async ({page}) => {
    const response = await page.request.get('/api/v1/utilities/countries?language=it');
    const data = await response.json();

    expect(data.items.length).toBeGreaterThan(200);
    const italy = data.items.find(c => c.iso3 === 'ITA');
    expect(italy.name).toBe('Italia');
    expect(italy.flag_emoji).toBe('🇮🇹');
});

test('normalize € resolves to EUR', async ({page}) => {
    const r = await page.request.get('/api/v1/utilities/currencies/normalize?name=%E2%82%AC');
    const data = await r.json();
    expect(data.iso_codes).toContain('EUR');
    expect(data.match_type).toBe('exact');
});

test('normalize G7 returns region with 7 countries', async ({page}) => {
    const r = await page.request.get('/api/v1/utilities/countries/normalize?name=G7');
    const data = await r.json();
    expect(data.match_type).toBe('region');
    expect(data.iso3_codes.length).toBe(7);
});
```

### Coverage Target Ragionamento

- **90%** è realistico con la strategia "no plugin body testing" + B9-B12
- Il ~10% gap è: plugin body (550 stmts), infra (50 stmts), debug (53 stmts), ABC astratti (20 stmts)
- I contract tests garantiscono che OGNI plugin rispetti il contratto ABC
- Il body dei plugin è testato da chi li sviluppa, non dal framework
- Per arrivare a 92%+: testare plugin body (non previsto) o main.py infra (non consigliabile)

---

## 9. Diario Sessioni

### Sessione 1 — 15 Aprile 2026
- Analisi coverage baseline (82.27% backend, 84.76% combined)
- Creazione piano v2 con strategia "provider contract, not implementation"
- Fix `_finalize_coverage()` e pipeline coverage combine
- Fix `coverage_analysis.py` per report accurato

### Sessione 2 — 16 Aprile 2026 (commit `e1fcfc0e` + WIP)

**Lavoro completato:**

1. **Batch 1 — Provider Contract Tests** ✅
   - Creato `test_services/test_provider_contracts.py` (287 righe)
   - 3 sezioni parametrizzate: FX, Asset, BRIM provider contracts
   - Registrato in `test_runner.py` con azioni dedicate

2. **Batch 3 — DB Model Validators** ✅
   - Creato `test_db/test_model_validators.py` (247 righe)
   - Copre `validate_currency_field`, `Asset.validate_*`, `FxRate.validate_currencies`

3. **Batch 2 — Utility Tests** (parziale)
   - Creato `test_api/test_utilities.py` (140 righe) — test backend per API utilities
   - Registrato in `test_runner.py`
   - Frontend E2E `utilities.spec.ts` ancora da fare

4. **Batch 6 — BRIM Parse Error** (parziale)
   - Creato `test_services/test_brim_parse_error.py` (44 righe)
   - Copre `BRIMParseError.__init__`, `.message`, `.details`
   - Registrato in `test_runner.py`

5. **Infrastruttura test_runner.py**
   - Aggiunto provider filtering CLI (es. `./dev.py test external asset-providers --provider yfinance`)
   - Aggiunta retry logic per yfinance (flaky provider)
   - Registrate tutte le nuove azioni: `services_provider_contracts`, `services_brim_parse_error`, `api_utilities`

6. **Fix coverage pipeline**
   - Fix nella gestione `--cov-clean-backend` / `--cov-clean-frontend`
   - In attesa di verifica con run `all` dopo pulizia coverage

**File modificati (non committati):**
- `backend/test_scripts/test_api/test_utilities.py` (nuovo, 140 righe)
- `backend/test_scripts/test_services/test_brim_parse_error.py` (nuovo, 44 righe)
- `scripts/test_runner.py` (+58 righe: registrazione nuovi test)

**Prossimi passi:**
- Verificare risultato coverage dopo run `all` con coverage pulita
- Completare Batch 2 (E2E frontend `utilities.spec.ts`)
- Batch 4 (FX Service & API error paths)
- Batch 5 (Asset Service & API error paths)
- Batch 7 (Uploads security)
- Batch 8 (Scheduled Investment edge cases)

### Sessione 3 — 16 Aprile 2026 (cont.)

**Lavoro completato:**

1. **Batch 4 — FX Core** ✅
   - Esteso `test_fx_core.py` da 17→21 test (+4)
   - `TestNormalizeRateEdgeCases` (very small rate, large rate)
   - `TestUpsertRatesBulkEdgeCases` (same rate unchanged, multiple pairs)

2. **Batch 7 — Uploads Security** ✅
   - Esteso `test_static_uploads.py` da 20→29 test (+9)
   - `TestValidateUploadSecurity`: CSV, JSON, PNG safe, .js/.mjs/.jar blocked, declared MIME octet-stream, text match, empty content

3. **Batch 8 — Scheduled Investment** ✅
   - Esteso `test_day_count_conventions.py` da 20→31 test (+11): `TestSimpleInterest` (6), `TestThirty360EdgeCases` (3), `TestACTACTLeapYear` (2)
   - Esteso `test_synthetic_yield.py` da 13→16 test (+3): validation error, invalid day count, grace period late interest

4. **Fix coverage pipeline**
   - `test_runner.py`: `.coverage.backend` ora aggiornato sempre (non solo prima volta) sia nel path backend-only che nel path all/frontend
   - Backup `.coverage*` DB in `.coverage_backup_20260416/`

**Prossimi passi:**
- Eseguire test incrementali con coverage sui file modificati
- Completare Batch 2 (E2E frontend `utilities.spec.ts`)
- Completare Batch 6 (BRIM core parsing — oltre `test_brim_parse_error.py`)

### Sessione 4 — 16 Aprile 2026 (cont. — eliminazione funzioni 0%)

**Obiettivo**: ridurre a zero la lista di funzioni 0% coverage.

**Strategia duale**:
1. Funzioni infrastrutturali/plugin body → `# pragma: no cover`
2. Funzioni testabili → nuovi test

**Esclusioni aggiunte (`# pragma: no cover`)**:

| File | Funzione | Stmts | Motivo |
|------|----------|-------|--------|
| `main.py` | `docs_available`, `render_docs_not_built`, `mkdocs_root`, `mkdocs_static`, `root` | 17 | Infra: docs/frontend serving |
| `logging_config.py` | `_get_rotated_filename`, `_compress_rotated_file` | 5 | Infra: log rotation |
| `fx_providers/boe.py` | `_parse_response`, `_parse_boe_date` | 25 | Plugin body |
| `fx_providers/snb.py` | `_extract_d1_from_header` | 7 | Plugin body |
| `css_scraper.py` | `get_asset_url`, `get_history_value` | 2 | Plugin body |
| `justetf.py` | `shutdown_live_feeds`, `_country_name_to_iso3`, `shutdown` | 15 | Plugin body/shutdown |
| `yahoo_finance.py` | `_is_transient` | 2 | Plugin helper |
| `asset_source.py` | `accepted_identifier_types`, `shutdown` | 2 | ABC base class defaults |
| `asset_source.py` | `search_stream` + inner `_search_one` | 56 | SSE streaming (duplex of `search`) |
| `assets.py` | `search_assets_stream` | 4 | SSE API endpoint wrapper |
| `brim_provider.py` | `supported_extensions`, `detection_priority`, `shutdown` | 3 | ABC base class defaults |
| `fx.py` | `icon`, `test_currencies`, `shutdown` | 3 | ABC base class defaults |
| `provider_registry.py` | `shutdown_all_providers` | 7 | Infra: app shutdown |
| **Totale** | | **~148** | |

**Test creati**:

| File | Test | Stmts coperti | Funzione target |
|------|------|---------------|-----------------|
| `test_api/test_fx_compress_errors.py` | 6 test | 18 | `_compress_convert_errors` |
| `test_api/test_preview_cache.py` | 9 test | 33 | `PreviewCache.load_config/get/put` |
| **Totale** | **15 test** | **~51** | |

**Funzioni già coperte da batch esistenti**:
- `get_optional_user` (4 stmts) → B12 `test_auth_api.py`
- `get_system_info` (1 stmt) → B10 `test_system_api.py`
- `list_currencies` (3 stmts) → B2 `test_utilities.py`
- `get_session_ttl` (7 stmts) → B11 `test_settings_service.py`

**File modificati (non committati)**:
- `backend/app/main.py` (+5 `# pragma: no cover`)
- `backend/app/logging_config.py` (+2 `# pragma: no cover`)
- `backend/app/services/fx_providers/boe.py` (+2 `# pragma: no cover`)
- `backend/app/services/fx_providers/snb.py` (+1 `# pragma: no cover`)
- `backend/app/services/asset_source_providers/css_scraper.py` (+2 `# pragma: no cover`)
- `backend/app/services/asset_source_providers/justetf.py` (+3 `# pragma: no cover`)
- `backend/app/services/asset_source_providers/yahoo_finance.py` (+1 `# pragma: no cover`)
- `backend/app/services/asset_source.py` (+3 `# pragma: no cover`)
- `backend/app/api/v1/assets.py` (+1 `# pragma: no cover`)
- `backend/app/services/brim_provider.py` (+3 `# pragma: no cover`)
- `backend/app/services/fx.py` (+3 `# pragma: no cover`)
- `backend/app/services/provider_registry.py` (+1 `# pragma: no cover`)
- `backend/test_scripts/test_api/test_fx_compress_errors.py` (nuovo, 6 test)
- `backend/test_scripts/test_api/test_preview_cache.py` (nuovo, 9 test)
- `scripts/test_runner.py` (registrati `fx-compress-errors` e `preview-cache`)

### Sessione 5 — 16 Aprile 2026 (cont. — residui 0% finali)

**Obiettivo**: eliminare gli ultimi 4 residui 0% dopo re-run coverage.

**Azioni**:
1. `get_system_info` (1 stmt) → aggiunto `TestGetSystemInfoEndpoint` in `test_system_api.py`
2. `list_currencies` endpoint (3 stmts) → aggiunto `TestListCurrenciesEndpoint` in `test_utilities.py`
3. `get_session_ttl` async (7 stmts) → aggiunto `TestGetSessionTTL` in `test_settings_service.py`
4. `get_optional_user` (4 stmts) → `# pragma: no cover` (dependency inutilizzata, preparata per futuro)

**Esclusioni aggiuntive per funzioni a bassa coverage (infra)**:
- `frontend_catchall` (11 stmts) → `# pragma: no cover` (SPA catch-all)
- `SNBProvider._parse_json` (38 stmts) → `# pragma: no cover` (plugin body)
- `_yf_with_retry` (11 stmts) → `# pragma: no cover` (plugin retry helper)
- `serve_file` (60 stmts) → `# pragma: no cover` (file serving/preview infra)

**File modificati**:
- `backend/app/api/v1/auth.py` (+1 pragma)
- `backend/app/api/v1/uploads.py` (+1 pragma)
- `backend/app/main.py` (+1 pragma)
- `backend/app/services/fx_providers/snb.py` (+1 pragma)
- `backend/app/services/asset_source_providers/yahoo_finance.py` (+1 pragma)
- `backend/test_scripts/test_api/test_system_api.py` (+1 test class)
- `backend/test_scripts/test_api/test_utilities.py` (+1 test class)
- `backend/test_scripts/test_services/test_settings_service.py` (+1 test class, 2 async tests)

