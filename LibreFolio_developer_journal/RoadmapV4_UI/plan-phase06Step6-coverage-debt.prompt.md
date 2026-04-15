# Piano: Rientro Debito Tecnico — Coverage Testing (v2)

**Data creazione**: 15 Aprile 2026  
**Status**: 📋 PIANIFICATO  
**Baseline**: Backend 82.27% | Frontend E2E 49.78% | Combined **84.76%** (1619/10621 stmts uncovered)  
**Obiettivo**: Combined **≥ 89%** (≤ 1168 miss → recuperare ~451 stmts)

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

### Batch 1 — Provider Contract Tests (offline, ~2h) 🟢 NUOVO

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

### Batch 2 — Frontend E2E: Utility & Presentazione (~2h) 🟦 NUOVO

**Impatto stimato**: +60 stmts backend coverage + validazione UI rendering

Questi test chiamano gli endpoint `/api/v1/utilities/*` ATTRAVERSO il frontend,
validando che la UI mostra correttamente bandiere, valute, paesi, settori.

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

### Batch 3 — DB Model Validators (~0.5h) 🟢 FACILE

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

### Batch 4 — FX Service & API Error Paths (~2h) 🟡 MEDIO

**Impatto stimato**: +100 stmts → ~87.4%

#### B4.1 `test_services/test_fx_core.py` (estendere)
Attuale: 17 test. Funzioni scoperte: `sync_pairs_bulk` inner paths, `convert_bulk` errors, `delete_rates_bulk` edges.

```
Test da aggiungere:
- test_sync_pairs_bulk_partial_failure → un provider fallisce, altri ok
- test_sync_pairs_bulk_no_providers → errore appropriato
- test_convert_bulk_chain_rate → conversione con triangolazione
- test_convert_bulk_missing_rate → errore per coppia senza route
- test_delete_rates_bulk_nonexistent → silenzioso o warning
- test_normalize_rate_for_storage → rate con unit currency (JPY/100)
- test_count_actual_changes → inseriti/aggiornati/invariati
```

#### B4.2 `test_api/test_fx_api.py` (estendere)
Attuale: 21 test. Funzioni scoperte: `delete_rates_endpoint`, `create_routes_bulk`, `convert_currency_bulk`.

```
Test da aggiungere:
- test_delete_rates_nonexistent → 404 o empty
- test_create_routes_bulk_invalid_currency → 422
- test_create_routes_bulk_duplicate → 409 o handled
- test_convert_bulk_empty_list → 200 empty
- test_convert_bulk_same_currency → amount unchanged
- test_sync_rates_no_route → 404
- test_list_providers_with_details → response ha campi attesi
```

---

### Batch 5 — Asset Service & API Error Paths (~2h) 🟡 MEDIO

**Impatto stimato**: +80 stmts → ~88.2%

#### B5.1 `test_services/test_asset_source.py` (estendere)
Attuale: 23 test. Funzioni scoperte: `bulk_refresh_prices` sub-paths, `refresh_assets_from_provider`, `probe_provider_config`.

```
Test da aggiungere:
- test_bulk_refresh_prices_no_provider → skip senza errore
- test_refresh_from_provider_timeout → gestisce timeout
- test_probe_provider_config_invalid → errore chiaro
- test_bulk_assign_providers_duplicate → idempotente
- test_create_assets_bulk_validation → campi obbligatori
```

#### B5.2 `test_api/test_assets_crud.py` (estendere)
Attuale: 19 test. Funzioni scoperte: `read_assets_bulk`, `refresh_assets_from_provider`, `search_assets_via_providers`.

```
Test da aggiungere:
- test_read_assets_bulk_empty_ids → 200 empty
- test_read_assets_bulk_nonexistent → gestisce gracefully
- test_search_via_providers_no_results → 200 empty list
- test_create_bulk_missing_fields → 422
- test_patch_bulk_invalid_id → 404
- test_delete_bulk_with_transactions → 409 (o cascade policy)
```

---

### Batch 6 — BRIM Core Parsing (~1.5h) 🟡 MEDIO

**Impatto stimato**: +50 stmts → ~88.7%

> **Nota**: NON testiamo i singoli plugin (Degiro, IBKR, etc.) — quelli sono coperti
> dai contract tests (B1) per interfaccia e dai `test_external/test_brim_providers.py`
> per parsing con sample files reali. Qui testiamo solo il CORE di `brim_provider.py`
> (funzioni orchestranti, non i plugin).

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

### Batch 7 — Uploads & Static Files (~1h) 🟢 FACILE

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

### Batch 8 — Scheduled Investment Edge Cases (~1h) 🟢 FACILE

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

## 3. Riepilogo Impatto

| Batch | Focus | Tipo | Stmts | Coverage | Tempo |
|-------|-------|------|-------|----------|-------|
| **B1** | Provider Contract Tests | Backend (offline) | ~100 | 85.7% | 2h |
| **B2** | Utility & Presentazione | **Frontend E2E** | ~60 | 86.3% | 2h |
| **B3** | DB Model Validators | Backend unit | ~28 | 86.5% | 0.5h |
| **B4** | FX Service & API | Backend service+API | ~100 | 87.4% | 2h |
| **B5** | Asset Service & API | Backend service+API | ~80 | 88.2% | 2h |
| **B6** | BRIM Core Parsing | Backend service | ~50 | 88.7% | 1.5h |
| **B7** | Uploads Security | Backend unit | ~30 | 89.0% | 1h |
| **B8** | Scheduled Investment | Backend unit | ~30 | 89.3% | 1h |
| **Totale** | | | **~478** | **~89%** | **~12h** |

---

## 4. Cosa NON testare (e perché)

| Codice | Miss | Motivo skip |
|--------|------|-------------|
| Provider plugin body (fetch, parse) | ~550 | **Plugin responsibility**: body di SNB, BOE, Yahoo, JustETF, etc. è codice del plugin, non del framework. I contract test (B1) validano l'interfaccia; il body è testato dal plugin owner (o da `test_external/` con HTTP reale) |
| `main.py` (startup, DB init) | 41 | Infrastruttura: richiede setup complesso, fragile |
| `broker_service.py` (91.9%) | 26 | Già sopra target |
| `transaction_service.py` (89.6%) | 29 | Quasi al target, coperto indirettamente |
| `user_service.py` (98%) | 3 | Già completo |
| Debug functions (`_debug_*`) | ~50 | Funzioni debug in SNB, non production code |
| `api/v1/system.py` (93%) | 6 | Già sopra target |
| `logging_config.py` | 6 | Infrastruttura |

**Totale accettato come gap**: ~720 stmts → plafond realistico **~89%**

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
B1 (provider contracts)   ← 2h, zero HTTP, copre interfacce + base class
    ↓
B3 (model validators)     ← 0.5h, unit test puri, quick win
    ↓
B2 (E2E utility/present.) ← 2h, testa pipeline backend→frontend
    ↓
B7 (uploads security)     ← 1h, unit test
    ↓
B8 (scheduled inv.)       ← 1h, estende test esistenti
    ↓
    Checkpoint: ~87%, verifica con:
    ./dev.py test --coverage --cov-clean-backend --cov-clean-frontend -v all
    ↓
B4 (FX service + API)     ← 2h, usa DB test
    ↓
B5 (asset service + API)  ← 2h, usa DB test
    ↓
B6 (BRIM core parsing)    ← 1.5h, mock filesystem
    ↓
    Final: ./dev.py test --coverage --cov-clean-backend --cov-clean-frontend -v all
    ↓
    Verifica target ≥ 89%
```

**Durata totale**: ~12h (~2 giorni)  
**Checkpoint intermedio**: dopo B1+B3+B2+B7+B8 (6.5h) → dovrebbe essere ~87%

---

## 7. Prerequisiti

- [x] Fix `_finalize_coverage()` per report combined corretto
- [x] Fix print hint duplicato  
- [ ] `unittest.mock` è nella stdlib Python — serve solo per B6 (mock filesystem)

> **Nota**: il progetto attualmente NON usa `unittest.mock`. Il pattern principale è:
> - Test via TestClient HTTP (per API)
> - Test via service diretto con DB test (per services)
> - Provider reale `mockprov` (per provider logic)
> - Test parametrizzato su tutti i provider (per `test_external/`)
>
> I contract tests (B1) seguono lo stesso pattern parametrizzato di `test_external/`
> ma senza HTTP: istanziano il provider e validano l'interfaccia.

---

## 8. Note Tecniche

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

- **89%** è realistico con la strategia "no plugin body testing"
- Il ~11% gap è: plugin body (550 stmts), infra (100 stmts), debug (50 stmts)
- I contract tests garantiscono che OGNI plugin rispetti il contratto ABC
- Il body dei plugin è testato da chi li sviluppa, non dal framework
- Per arrivare a 90%+: testare plugin body (non previsto) o main.py infra (non consigliabile)

