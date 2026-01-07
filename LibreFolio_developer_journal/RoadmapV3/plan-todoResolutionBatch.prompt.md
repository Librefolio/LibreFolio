# Plan: TODO Resolution & Enhancement Batch

Risoluzione di 11 TODO pendenti con cache centralizzata (cachetools), localizzazione multi-lingua (Babel), e miglioramenti ai test.

**Status: ✅ COMPLETATO - Tutti gli 11 step implementati**

---

## Steps Implementativi

### ✅ 1. **Aggiungere `cachetools` al Pipfile e creare cache utils**

- ✅ Aggiunto `cachetools = "*"` al Pipfile (pre-esistente)
- ✅ Creato [`backend/app/utils/cache_utils.py`](backend/app/utils/cache_utils.py) con wrapper `TTLCache`
- ✅ Funzione `get_ttl_cache(name: str, maxsize: int, ttl: int) -> TTLCache` per cache con auto-expire

### ✅ 2. **Refactoring cache nei provider asset**

- ✅ [yahoo_finance.py](backend/app/services/asset_source_providers/yahoo_finance.py): Sostituito `_search_cache` dict con `TTLCache`
- ✅ [justetf.py](backend/app/services/asset_source_providers/justetf.py): Sostituito `CachedData` class con `TTLCache`
- ✅ Rimosso TODO garbage collector in [`asset_source.py:436`](backend/app/services/asset_source.py)

### ✅ 3. **Fetch currency in Yahoo Finance search**

- ✅ In [`yahoo_finance.py:312`](backend/app/services/asset_source_providers/yahoo_finance.py): Per ogni risultato, fatto `yf.Ticker(symbol).fast_info.get('currency')`
- ✅ Usato TTLCache separata per evitare chiamate ripetute
- ✅ Fallback a `None` se timeout/errore

### ✅ 4. **Timezone handling - documentato comportamento UTC**

- ✅ In [`yahoo_finance.py:230`](backend/app/services/asset_source_providers/yahoo_finance.py): yfinance DatetimeIndex convertito a UTC
- ✅ Implementato: `idx.tz_convert('UTC').date()` con fallback
- ✅ Documentato: "All dates normalized to UTC for backend consistency; frontend handles local display"

### ✅ 5. **Localizzazione Paesi con Babel**

- ✅ Refactoring [`geo_utils.py`](backend/app/utils/geo_utils.py):
    - ✅ `list_countries(language: str) -> list[CountryInfo]`: Lista tutti i paesi con nome tradotto + flag emoji
    - ✅ `normalize_country_multilang(input: str, language: str) -> NormalizationResult`: Accetta nome in qualsiasi lingua → ritorna ISO3 o lista candidati
- ✅ Flag emoji: `chr(0x1F1E6 + ord(iso2[0]) - ord('A')) + chr(0x1F1E6 + ord(iso2[1]) - ord('A'))`
- ✅ Fallback a inglese se lingua non supportata
- ✅ Aggiornato [`utilities.py`](backend/app/api/v1/utilities.py) endpoint `/countries` con `flag_emoji`
- ✅ Gestione ambiguità con `match_type="multi-match"`

### ✅ 6. **Localizzazione Valute con Babel**

- ✅ Creato [`backend/app/utils/currency_utils.py`](backend/app/utils/currency_utils.py):
    - ✅ `normalize_currency(input: str, language: str) -> NormalizationResult`: Accetta ISO, simbolo (€/$), nome localizzato
    - ✅ `list_currencies(language: str) -> list[CurrencyInfo]`: Lista con nome tradotto, simbolo, ISO code
- ✅ Usato `babel.numbers.get_currency_symbol(code, locale)` e `babel.Locale(language).currencies`
- ✅ Simboli ambigui ($) → lista candidati con `match_type="multi-match"`
- ✅ Creato endpoint `/utilities/currencies` e `/utilities/currencies/normalize`
- ✅ Aggiunti schemi: `CurrencyListItem`, `CurrencyListResponse`, `CurrencyNormalizationResponse`

### ✅ 7. **Refactor `_classify_asset_identifier` → oggetto tipizzato**

- ✅ In [`brim.py`](backend/app/schemas/brim.py): Creato `BRIMExtractedAssetInfo(BaseModel)` con `extracted_symbol`, `extracted_isin`, `extracted_name`
- ✅ In [`broker_generic_csv.py:567`](backend/app/services/brim_providers/broker_generic_csv.py): Ritorna `BRIMExtractedAssetInfo` invece di dict

### ✅ 8. **CSS scraper: header custom da provider_params**

- ✅ In [`css_scraper.py:110`](backend/app/services/asset_source_providers/css_scraper.py):
    - ✅ Legge `provider_params.get('headers', {})`
    - ✅ Usa `mergedeep` invece di dict unpacking: `merge({}, default_headers, custom_headers)`

### ✅ 9. **Implementare test `test_patch_icon_url_clear`**

- ✅ In [`test_assets_patch_fields.py:268`](backend/test_scripts/test_api/test_assets_patch_fields.py):
    - ✅ Crea asset con `icon_url="http://example.com/icon.png"`
    - ✅ PATCH con `icon_url=None`
    - ✅ Verifica `icon_url` è `None` nel DB

### ✅ 10. **Completare test `test_list_active_filter`**

- ✅ In [`test_assets_crud.py:296`](backend/test_scripts/test_api/test_assets_crud.py):
    - ✅ Crea 2 asset: uno `active=True`, uno `active=False` (via PATCH)
    - ✅ Testa `?active=true` ritorna solo l'attivo
    - ✅ Testa `?active=false` ritorna solo l'inattivo

### ✅ 11. **Aggiungere `expected_symbol` ai provider test_cases**

- ✅ Aggiornato `test_cases` in tutti i provider:
    - ✅ [yahoo_finance.py](backend/app/services/asset_source_providers/yahoo_finance.py): `{'identifier': 'AAPL', 'expected_symbol': 'AAPL', ...}`
    - ✅ [justetf.py](backend/app/services/asset_source_providers/justetf.py): `{'identifier': 'IE00B4L5Y983', 'expected_symbol': 'IE00B4L5Y983', ...}` (ISIN)
    - ✅ [mockprov.py](backend/app/services/asset_source_providers/mockprov.py): `{'identifier': 'MOCK', 'expected_symbol': 'MOCK', ...}`
    - ✅ [css_scraper.py](backend/app/services/asset_source_providers/css_scraper.py): `{'expected_symbol': '<URL>', ...}` (identifier stesso)

---

## 🆕 Refactoring Aggiuntivi (Post-Review)

### ✅ **Creato `translation_utils.py` per funzioni comuni**

- ✅ Creato [`backend/app/utils/translation_utils.py`](backend/app/utils/translation_utils.py)
- ✅ Centralizzata funzione `get_babel_locale(language: str) -> Locale`
- ✅ Eliminata duplicazione in `currency_utils.py` e `geo_utils.py`
- ✅ Fallback automatico a inglese se lingua non supportata

### ✅ **Usato `mergedeep` invece di dict unpacking**

- ✅ In `css_scraper.py`: Sostituito `{**default_headers, **custom_headers}` con `merge({}, default_headers, custom_headers)`
- ✅ Più robusto per merge ricorsivi e consistente con altri usi di mergetools nel progetto

---

## Steps Implementativi

### 1. **Aggiungere `cachetools` al Pipfile e creare cache utils**

- Aggiungere `cachetools = "*"` al Pipfile
- Creare [`backend/app/utils/cache_utils.py`](backend/app/utils/cache_utils.py) con wrapper `TTLCache`
- Funzione `get_ttl_cache(name: str, maxsize: int, ttl: int) -> TTLCache` per cache con auto-expire

### 2. **Refactoring cache nei provider asset**

- [yahoo_finance.py](backend/app/services/asset_source_providers/yahoo_finance.py): Sostituire `_search_cache` dict con `TTLCache`
- [justetf.py](backend/app/services/asset_source_providers/justetf.py): Sostituire `CachedData` class con `TTLCache`
- Rimuovere TODO garbage collector in [`asset_source.py:436`](backend/app/services/asset_source.py) (non più necessario con TTLCache)

### 3. **Fetch currency in Yahoo Finance search**

- In [`yahoo_finance.py:312`](backend/app/services/asset_source_providers/yahoo_finance.py): Per ogni risultato, fare `yf.Ticker(symbol).fast_info.get('currency')`
- Usare TTLCache per evitare chiamate ripetute
- Fallback a `None` se timeout/errore

### 4. **Timezone handling - documentare comportamento UTC**

- In [`yahoo_finance.py:230`](backend/app/services/asset_source_providers/yahoo_finance.py): yfinance ritorna DatetimeIndex con timezone del mercato
- Convertire esplicitamente a UTC prima di estrarre `.date()`: `idx.tz_convert('UTC').date()`
- Documentare: "All dates normalized to UTC for backend consistency; frontend handles local display"

### 5. **Localizzazione Paesi con Babel**

- Refactoring [`geo_utils.py`](backend/app/utils/geo_utils.py):
    - `list_countries(language: str) -> list[CountryInfo]`: Lista tutti i paesi con nome tradotto + flag emoji
    - `normalize_country_multilang(input: str, language: str) -> NormalizationResult`: Accetta nome in qualsiasi lingua → ritorna ISO3 o lista candidati se ambiguo
- Flag emoji formula: `chr(0x1F1E6 + ord(iso2[0]) - ord('A')) + chr(0x1F1E6 + ord(iso2[1]) - ord('A'))`
- Fallback a inglese se lingua non supportata da Babel
- Aggiornare [`utilities.py`](backend/app/api/v1/utilities.py) endpoint `/countries` con `flag_emoji`
- Se ambiguo → ritorna lista candidati con `match_type="multi-match"`

### 6. **Localizzazione Valute con Babel**

- Creare [`backend/app/utils/currency_utils.py`](backend/app/utils/currency_utils.py):
    - `normalize_currency(input: str, language: str) -> NormalizationResult`: Accetta ISO, simbolo (€/$), nome localizzato
    - `list_currencies(language: str) -> list[CurrencyInfo]`: Lista con nome tradotto, simbolo, ISO code
- Usare `babel.numbers.get_currency_symbol(code, locale)` e `babel.Locale(language).currencies`
- Se simbolo ambiguo ($) → ritorna lista candidati (USD, CAD, AUD, etc.) con `match_type="multi-match"`
- Creare endpoint `/utilities/currencies` e `/utilities/currencies/normalize`
- Aggiungere schemi: `CurrencyListItem`, `CurrencyListResponse`, `CurrencyNormalizationResponse`

### 7. **Refactor `_classify_asset_identifier` → oggetto tipizzato**

- In [`brim.py`](backend/app/schemas/brim.py): Creare `BRIMExtractedAssetInfo(BaseModel)` con `extracted_symbol`, `extracted_isin`, `extracted_name`
- In [`broker_generic_csv.py:567`](backend/app/services/brim_providers/broker_generic_csv.py): Ritornare `BRIMExtractedAssetInfo` invece di dict

### 8. **CSS scraper: header custom da provider_params**

- In [`css_scraper.py:110`](backend/app/services/asset_source_providers/css_scraper.py):
    - Leggere `provider_params.get('headers', {})`
    - Merge: `default_headers | custom_headers` (custom vince su default)

### 9. **Implementare test `test_patch_icon_url_clear`**

- In [`test_assets_patch_fields.py:268`](backend/test_scripts/test_api/test_assets_patch_fields.py):
    - Create asset con `icon_url="http://example.com/icon.png"`
    - PATCH con `icon_url=None`
    - Verify `icon_url` è `None` nel DB

### 10. **Completare test `test_list_active_filter`**

- In [`test_assets_crud.py:296`](backend/test_scripts/test_api/test_assets_crud.py):
    - Creare 2 asset: uno `active=True`, uno `active=False` (via PATCH)
    - Testare `?active=true` ritorna solo l'attivo
    - Testare `?active=false` ritorna solo l'inattivo

### 11. **Aggiungere `expected_symbol` ai provider test_cases**

- Aggiornare `test_cases` in tutti i provider:
    - [yahoo_finance.py](backend/app/services/asset_source_providers/yahoo_finance.py): `{'identifier': 'AAPL', 'expected_symbol': 'AAPL', ...}`
    - [justetf.py](backend/app/services/asset_source_providers/justetf.py): `{'identifier': 'IE00B4L5Y983', 'expected_symbol': 'SWDA', ...}`
    - [mockprov.py](backend/app/services/asset_source_providers/mockprov.py): `{'identifier': 'MOCK', 'expected_symbol': 'MOCK', ...}`
    - [css_scraper.py](backend/app/services/asset_source_providers/css_scraper.py): Da verificare quali test case ha
- Aggiornare test per verificare match su `expected_symbol`

---

## Nuovi Schemi da Creare

```python
# In backend/app/schemas/utilities.py

class CountryListItem:
    iso3: str  # "USA"
    iso2: str  # "US"
    name: str  # "United States" (nella lingua richiesta)
    flag_emoji: str  # "🇺🇸"


class CurrencyListItem:
    code: str  # "USD"
    name: str  # "Dollaro statunitense" (nella lingua richiesta)
    symbol: str  # "$"


class CurrencyNormalizationResponse:
    query: str
    iso_codes: list[str]  # ["USD"] o ["USD", "CAD", "AUD"] se ambiguo
    match_type: str  # "exact", "multi-match", "not_found"
    error: str | None
```

---

## Ordine di Implementazione Suggerito

1. **Step 1-2**: Cache centralizzata (foundation per altri step)
2. **Step 5-6**: Localizzazione Babel (paesi + valute)
3. **Step 3-4**: Yahoo Finance improvements (usano nuova cache)
4. **Step 7-8**: Refactor minori (BRIM, CSS scraper)
5. **Step 9-11**: Test (validano tutto il resto)

---

## Test Aggiuntivi

- Test per `/utilities/currencies` endpoint
- Test per `/utilities/currencies/normalize` endpoint
- Test per simboli ambigui ($) → lista candidati
- Test per nomi paese in lingue diverse (IT, FR, ES, EN)
- Test per fallback lingua inglese se locale non supportato

---

## Files Modificati

| File                                                           | Modifica                         |
|----------------------------------------------------------------|----------------------------------|
| `Pipfile`                                                      | +cachetools                      |
| `backend/app/utils/cache_utils.py`                             | NUOVO - TTLCache wrapper         |
| `backend/app/utils/currency_utils.py`                          | NUOVO - localizzazione valute    |
| `backend/app/utils/geo_utils.py`                               | +Babel, +flag emoji, +multi-lang |
| `backend/app/schemas/utilities.py`                             | +CurrencyListItem, +flag_emoji   |
| `backend/app/schemas/brim.py`                                  | +BRIMExtractedAssetInfo          |
| `backend/app/api/v1/utilities.py`                              | +currencies endpoints            |
| `backend/app/services/asset_source.py`                         | -TODO garbage collector          |
| `backend/app/services/asset_source_providers/yahoo_finance.py` | +TTLCache, +currency fetch, +UTC |
| `backend/app/services/asset_source_providers/justetf.py`       | +TTLCache                        |
| `backend/app/services/asset_source_providers/css_scraper.py`   | +custom headers                  |
| `backend/app/services/brim_providers/broker_generic_csv.py`    | +BRIMExtractedAssetInfo          |
| `backend/test_scripts/test_api/test_assets_patch_fields.py`    | +test icon_url clear             |
| `backend/test_scripts/test_api/test_assets_crud.py`            | +test active filter              |
| `backend/test_scripts/test_external/test_asset_providers.py`   | +expected_symbol validation      |

