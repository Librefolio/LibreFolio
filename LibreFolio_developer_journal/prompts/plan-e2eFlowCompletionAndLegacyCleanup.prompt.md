# Plan: E2E Flow Completion & Legacy Code Cleanup

**Priorità**: 🔴 CRITICA  
**Complessità**: ⚡ ALTA (Currency class è breaking change significativo)  
**Tempo stimato**: 8-10 ore  
**Data creazione**: 2025-12-17  
**Stato**: 🚧 IN PROGRESS

---

## 🎯 Obiettivo Principale

Completare flusso End-to-End senza "buchi" + **ELIMINARE COMPLETAMENTE CODICE LEGACY**:

```
Search → Create Asset → Assign Provider → Refresh Metadata → Refresh Prices
```

**BREAKING CHANGES VOLUTI**: Nessuna retro-compatibilità. Pulizia totale del codice.

---

## 📋 TODO da Risolvere (da grep-todo_3.txt)

### 🔴 CRITICI - Bloccano E2E Flow

| # | File | Line | TODO | Stato |
|---|------|------|------|-------|
| 1 | `asset_source.py` | 330 | identifier_type in search | ✅ DONE |
| 2 | `provider.py` | FAProviderRefreshFieldsDetail | refreshed_fields con OldNew | ✅ DONE |
| 3 | `common.py` | Currency class | Currency class | ✅ DONE |
| 4 | `asset_source.py` | 530, 712 | hasattr checks | ✅ DONE |
| 5 | `fx.py` | 88 | hasattr check | ⏳ TODO |
| 6 | `geo_normalization.py` | 55 | multi-language + lista multipla | ✅ DONE (endpoint added) |
| 7 | `utilities.py` | 62 | region mapping | ⏳ TODO (advanced feature) |

### 🟡 MEDI - Migliorano UX

| # | File | Line | TODO | Stato |
|---|------|------|------|-------|
| 8 | `justetf.py` | search | identifier_type in search | ✅ DONE |
| 9 | `yahoo_finance.py` | search | identifier_type in search | ✅ DONE |
| 10 | `mockprov.py` | search | identifier_type in search | ✅ DONE |
| 11 | `css_scraper.py` | 110 | headers customization | ⏭️ SKIP (FUTURE) |

### 🟢 MINORI - Future Work

| # | File | Line | TODO | Stato |
|---|------|------|------|-------|
| 12 | `asset_source.py` | 435 | cache GC job | ⏭️ SKIP (FUTURE) |
| 13 | `test_*.py` | vari | test improvements | ⏭️ SKIP (SEPARATE TASK) |

---

## 🏗️ Nuove Classi da Creare

### 1. `Currency` - Oggetto Pydantic per valute con operazioni

**Location**: `backend/app/schemas/common.py`

**Features richieste**:
- ✅ Campo `code: str` (ISO 4217: USD, EUR, BTC, etc.)
- ✅ Campo `amount: Decimal` (può essere negativo)
- ✅ Validazione con `pycountry.currencies` + dizionario cripto
- ✅ Operazioni: `__add__`, `__sub__`, `__eq__`, `__ne__`, `__neg__`, `__abs__`
- ✅ Metodi: `to_dict()`, `__str__()`, `__repr__()`
- ✅ Validation: Solleva `ValueError` se currency invalida

**Implementazione**:
```python
from decimal import Decimal
from typing import Any
import pycountry
from pydantic import BaseModel, field_validator

# Cryptocurrencies not in pycountry
CRYPTO_CURRENCIES = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum", 
    "USDT": "Tether",
    "USDC": "USD Coin",
    "BNB": "Binance Coin",
    "XRP": "Ripple",
    "ADA": "Cardano",
    "SOL": "Solana",
    "DOT": "Polkadot",
    "DOGE": "Dogecoin",
    "MATIC": "Polygon",
    "AVAX": "Avalanche",
    # Add more as needed
}

class Currency(BaseModel):
    """
    Currency amount with validation and arithmetic operations.
    
    Validates currency codes against ISO 4217 (via pycountry) + crypto dict.
    Supports addition/subtraction only between same currencies.
    
    Examples:
        >>> usd = Currency(code="USD", amount=Decimal("100.50"))
        >>> fee = Currency(code="USD", amount=Decimal("2.50"))
        >>> total = usd + fee  # Currency(code="USD", amount=Decimal("103.00"))
        
        >>> eur = Currency(code="EUR", amount=Decimal("50"))
        >>> usd + eur  # ValueError: Cannot add USD and EUR
        
        >>> btc = Currency(code="BTC", amount=Decimal("0.5"))  # Valid crypto
    """
    code: str
    amount: Decimal
    
    @field_validator('code')
    @classmethod
    def validate_currency_code(cls, v: Any) -> str:
        """Validate and normalize currency code."""
        from backend.app.utils.validation_utils import normalize_currency_code
        
        code = normalize_currency_code(v)
        
        # Check ISO 4217 via pycountry
        try:
            pycountry.currencies.lookup(code)
            return code
        except LookupError:
            pass
        
        # Check crypto currencies
        if code in CRYPTO_CURRENCIES:
            return code
        
        # Invalid currency
        raise ValueError(
            f"Invalid currency code: {code}. "
            f"Must be ISO 4217 currency or supported crypto: {', '.join(CRYPTO_CURRENCIES.keys())}"
        )
    
    def __add__(self, other: 'Currency') -> 'Currency':
        """Add two Currency objects (same currency only)."""
        if not isinstance(other, Currency):
            raise TypeError(f"Cannot add Currency and {type(other)}")
        if self.code != other.code:
            raise ValueError(f"Cannot add {self.code} and {other.code}")
        return Currency(code=self.code, amount=self.amount + other.amount)
    
    def __sub__(self, other: 'Currency') -> 'Currency':
        """Subtract two Currency objects (same currency only)."""
        if not isinstance(other, Currency):
            raise TypeError(f"Cannot subtract {type(other)} from Currency")
        if self.code != other.code:
            raise ValueError(f"Cannot subtract {other.code} from {self.code}")
        return Currency(code=self.code, amount=self.amount - other.amount)
    
    def __neg__(self) -> 'Currency':
        """Negate currency amount."""
        return Currency(code=self.code, amount=-self.amount)
    
    def __abs__(self) -> 'Currency':
        """Absolute value of currency amount."""
        return Currency(code=self.code, amount=abs(self.amount))
    
    def __eq__(self, other: object) -> bool:
        """Check equality (same code and amount)."""
        if not isinstance(other, Currency):
            return False
        return self.code == other.code and self.amount == other.amount
    
    def __ne__(self, other: object) -> bool:
        """Check inequality."""
        return not self.__eq__(other)
    
    def __str__(self) -> str:
        """String representation: '100.50 USD'."""
        return f"{self.amount} {self.code}"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"Currency(code='{self.code}', amount=Decimal('{self.amount}'))"
    
    def to_dict(self) -> dict:
        """Serialize to dict for JSON responses."""
        return {
            "currency": self.code,
            "amount": str(self.amount)  # Decimal → string for JSON
        }
```

Nota utente:
chat, il normalize_currency_code fa solo uno strip e upper, quindi eliminalo e importa le 2 righe di codice dentro Currency direttamente.
anzi usa normalize_currency_code come chiave di ricerca per trovare le aree di codice dove probabilmente serve usare questo nuovo tipo.


**API Usage Pattern**:
```python
# API endpoint receives JSON
{"currency": "USD", "amount": "100.50"}

# Pydantic deserializer converts to Currency
price = Currency(code=data["currency"], amount=Decimal(data["amount"]))

# Internal operations use Currency
total = price + fee

# API response serializes back
response = total.to_dict()  # {"currency": "USD", "amount": "103.00"}
```

---

### 2. Add `OldNew[T]` in FAProviderRefreshFieldsDetail - Generic per field changes

Inside `backend/app/schemas/common.py` exist a class OldNew(BaseModel, Generic[CType])
Use it inside **FAProviderRefreshFieldsDetail**:
```python
class FAProviderRefreshFieldsDetail(BaseModel):
    """Field-level details for provider refresh operation."""
    
    refreshed_fields: List[OldNew[str|None]] = Field(
        ..., 
        description="Fields updated with old→new values"
    )
    missing_data_fields: List[str] = Field(
        ..., 
        description="Fields provider couldn't fetch (asset field names)"
    )
    ignored_fields: List[str] = Field(
        ..., 
        description="Fields not requested (asset field names)"
    )

# Example usage:
detail = FAProviderRefreshFieldsDetail(
    refreshed_fields=[
        OldNew(old="Technology", new="Industrials"),  # sector_area changed
        OldNew(old=None, new="Test Corp")  # short_description added
    ],
    missing_data_fields=["currency", "volume"],
    ignored_fields=[]
)
```

---

### 3. Country List Endpoint

**Endpoint**: `GET /api/v1/utilities/countries/list?lang=en`

**Response Schema** (`backend/app/schemas/utilities.py`):
```python
class CountryInfo(BaseModel):
    """Single country information."""
    code: str = Field(..., description="ISO 3166-1 alpha-3 code (USA, ITA, etc.)")
    name: str = Field(..., description="Country name in requested language")

class FACountryListResponse(BaseModel):
    """Response for country list endpoint."""
    countries: List[CountryInfo]
    language: str = Field(..., description="Language code used (e.g., 'en')")
    count: int = Field(..., description="Total number of countries")
```

**Implementation** (`backend/app/api/v1/utilities.py`):
```python
@router.get("/countries/list", response_model=FACountryListResponse)
async def list_countries(lang: str = Query("en", description="Language code (only 'en' supported for now)")):
    """
    List all countries with their ISO codes.
    
    Uses pycountry.countries database.
    """
    import pycountry
    
    if lang != "en":
        # For now, only English supported
        # Future: use pycountry translations
        logger.warning(f"Language '{lang}' not supported, using 'en'")
    
    countries = []
    for country in pycountry.countries:
        countries.append(CountryInfo(
            code=country.alpha_3,
            name=country.name
        ))
    
    # Sort by name
    countries.sort(key=lambda c: c.name)
    
    return FACountryListResponse(
        countries=countries,
        language="en",
        count=len(countries)
    )
```

---

## 🎯 FASE 1: Infrastruttura Base (2-3h)

### Step 1.1: Creare `Currency` class ⚡ BREAKING

**Files da creare/modificare**:
1. ✅ `backend/app/schemas/common.py` - Aggiungere classe Currency
2. ✅ `backend/app/utils/validation_utils.py` - RIMOSSO normalize_currency_code()

**Tasks**:
- [x] Definire classe `Currency(BaseModel)` con `code` e `amount`
- [x] Implementare validator con `pycountry.currencies` + `CRYPTO_CURRENCIES`
- [x] Implementare operazioni: `__add__`, `__sub__`, `__neg__`, `__abs__`, `__eq__`, `__ne__`
- [x] Implementare `to_dict()` per serializzazione API
- [x] Implementare `__str__()` e `__repr__()`
- [x] Aggiungere `Currency.validate_code()` metodo statico per validare solo codici
- [x] RIMOSSO `normalize_currency_code()` da validation_utils.py
- [x] Usare `Currency.validate_code()` in fx.py, prices.py
- [x] Unit tests completi: `test_currency.py`

**Breaking Change**: ⚠️ SÌ - Nuovo tipo, vecchi `Decimal` non compatibili perchè insufficienti

**Test cases minimi**:
```python
def test_currency_creation():
    usd = Currency(code="USD", amount=Decimal("100"))
    assert usd.code == "USD"
    assert usd.amount == Decimal("100")

def test_currency_addition():
    a = Currency(code="USD", amount=Decimal("100"))
    b = Currency(code="USD", amount=Decimal("50"))
    c = a + b
    assert c.amount == Decimal("150")

def test_currency_different_codes_error():
    usd = Currency(code="USD", amount=Decimal("100"))
    eur = Currency(code="EUR", amount=Decimal("50"))
    with pytest.raises(ValueError, match="Cannot add USD and EUR"):
        usd + eur

def test_invalid_currency():
    with pytest.raises(ValueError, match="Invalid currency code: XXX"):
        Currency(code="XXX", amount=Decimal("100"))

def test_crypto_currency():
    btc = Currency(code="BTC", amount=Decimal("0.5"))
    assert btc.code == "BTC"
```

---

### Step 1.3: Aggiornare `FAProviderRefreshFieldsDetail` ⚡ BREAKING

**Files**:
1. ✏️ `backend/app/schemas/provider.py` - Schema update

**Tasks**:
- [ ] Import `OldNew` da common
- [ ] Cambiare `refreshed_fields: List[str]` → `List[OldNew[str|None]]`
- [ ] Aggiornare docstring con esempi
- [ ] Verificare che tests esistenti siano aggiornati

**Breaking Change**: ⚠️ SÌ - Type change in response schema

**Before**:
```python
refreshed_fields: List[str] = ["sector_area", "geographic_area"]
```

**After**:
```python
refreshed_fields: List[OldNew[str|None]] = [
    OldNew(old="Technology", new="Industrials"),
    OldNew(old=None, new={"USA": 0.6, "EUR": 0.4})
]
```

---

## 🎯 FASE 2: E2E Critici (3-4h)

### Step 2.1: `identifier_type` in search ⚡ BREAKING

**Files**:
1. ✏️ `backend/app/schemas/provider.py` - Add field
2. ✏️ `backend/app/services/asset_source.py` - Update docstring
3. ✏️ `backend/app/services/asset_search.py` - Map field
4. ✏️ `backend/app/services/asset_source_providers/justetf.py` - Add to results
5. ✏️ `backend/app/services/asset_source_providers/yahoo_finance.py` - Add to results
6. ✏️ `backend/app/services/asset_source_providers/mockprov.py` - Add to results

**Tasks**:
- [ ] Aggiungere `identifier_type: IdentifierType` a `FAProviderSearchResultItem` (REQUIRED, no Optional)
- [ ] Aggiornare docstring `search()` in abstract class
- [ ] JustETF: Return `"identifier_type": IdentifierType.ISIN`
- [ ] YFinance: Return `"identifier_type": IdentifierType.TICKER`
- [ ] MockProv: Return appropriate type
- [ ] Aggiornare `AssetSearchService.search()` per mappare il campo
- [ ] Test E2E: search → create → assign senza DB lookup

**Breaking Change**: ⚠️ SÌ - Campo required in response

**TODO risolti**: ✅ `asset_source.py:330`

---

### Step 2.2: Field details in metadata refresh

**Files**:
1. ✏️ `backend/app/services/asset_source.py` - Populate fields_detail

**Tasks**:
- [ ] In `refresh_metadata_from_provider()`, tracciare old/new per ogni campo
- [ ] Confrontare asset before/after per determinare changes
- [ ] Popolare `refreshed_fields: List[OldNew[str]]` con old→new values
- [ ] Popolare `missing_data_fields` se provider non ha fornito dati
- [ ] Popolare `ignored_fields` se alcuni campi non richiesti
- [ ] Test con partial refresh (solo alcuni campi aggiornati)
- [ ] Test con complete refresh (tutti i campi)

**Implementation hint**:
```python
# Before refresh
old_sector = asset.classification_params.sector_area if asset.classification_params else None

# After refresh from provider
new_sector = patch_item.classification_params.sector_area if patch_item.classification_params else None

# Track change
if old_sector != new_sector:
    refreshed_fields.append(OldNew(old=str(old_sector), new=str(new_sector)))
```

**TODO risolti**: ✅ `assets.py:691`

---

### Step 2.3: Currency in search/metadata (JustETF/YFinance)

**Files**:
1. ✏️ `backend/app/services/asset_source_providers/justetf.py`
2. ✏️ `backend/app/services/asset_source_providers/yahoo_finance.py`

**Tasks**:
- [ ] **JustETF**: Estrarre currency durante scraping (`get_etf_profile()` già la ha?)
  - Search: Aggiungere `"currency": extracted_currency` ai results
  - Metadata: Includere currency in `FAAssetPatchItem`
- [ ] **YFinance**: Estrarre currency da quote
  - Search: `quote.get('currency')` se disponibile
  - Metadata: Includere in patch
- [ ] Test che search ritorni currency quando disponibile
- [ ] Test che metadata fetch includa currency

**TODO risolti**: ✅ `justetf.py:304, 417`, `yahoo_finance.py:311`

---

## 🎯 FASE 3: Cleanup `hasattr()` (1h)

### Step 3.1: AssetSourceProvider properties

**Files**:
1. ✏️ `backend/app/services/asset_source.py` - Add property, remove hasattr
2. Providers (se serve override, ma default dovrebbe bastare)

**Tasks**:
- [ ] Aggiungere property in `AssetSourceProvider` base class:
  ```python
  @property
  def supports_metadata_fetch(self) -> bool:
      """Override to False if provider can't fetch metadata."""
      return True  # Default: supported
  ```
- [ ] Rimuovere **TUTTI** gli `hasattr(provider, 'fetch_asset_metadata')` checks
- [ ] Sostituire con `if provider.supports_metadata_fetch:`
- [ ] Test che funzioni con provider che fa override (es. CSS scraper → False)

**Locations to update**:
- `asset_source.py:530` ✅
- `asset_source.py:712` ✅
- `justetf.py:260` ✅ (se presente)

**Breaking**: ✅ NO - Internal refactor only

**TODO risolti**: ✅ `asset_source.py:530, 712`, `justetf.py:260`

---

### Step 3.2: FX Provider properties

**Files**:
1. ✏️ `backend/app/services/fx.py` - Add property to base class
2. ✏️ `backend/app/api/v1/fx.py` - Remove hasattr check

**Tasks**:
- [ ] In `FXRateProvider` base class, **verificare property già esiste** (sembra esserci a line 89)
- [ ] Se manca, aggiungere:
  ```python
  @property
  def base_currencies(self) -> list[str]:
      """List of supported base currencies."""
      return [self.base_currency]  # Default: single-base
  ```
- [ ] In `fx.py:88`, rimuovere:
  ```python
  if hasattr(instance, 'base_currencies') and instance.base_currencies:
      base_currencies = instance.base_currencies
  else:
      base_currencies = [instance.base_currency]
  ```
- [ ] Sostituire con:
  ```python
  base_currencies = instance.base_currencies
  ```
- [ ] Test endpoint `/fx/providers/list`

**Breaking**: ✅ NO - Internal refactor only

**TODO risolti**: ✅ `fx.py:88`

---

## 🎯 FASE 4: Utilities & UX (2-3h)

### Step 4.1: Multi-language country search (Best effort)

**Files**:
1. ✏️ `backend/app/utils/geo_normalization.py` - Fuzzy search
2. ✏️ `backend/app/api/v1/utilities.py` - Handle multiple matches
3. ✏️ `backend/app/schemas/utilities.py` - Response schema

**Tasks**:
- [ ] Tentare fuzzy search con `pycountry`:
  ```python
  import pycountry
  
  def search_country(query: str) -> list:
      results = []
      query_lower = query.lower()
      
      for country in pycountry.countries:
          # Exact match
          if country.alpha_3.lower() == query_lower:
              return [country.alpha_3]
          # Name match
          if query_lower in country.name.lower():
              results.append(country.alpha_3)
      
      return results
  ```
- [ ] Se `pycountry` non supporta lingue multiple, **fallback inglese OK**
- [ ] Aggiornare endpoint per ritornare lista se match multipli:
  ```python
  {
      "query": "Italia",
      "matches": [
          {"code": "ITA", "name": "Italy", "confidence": 1.0}
      ]
  }
  ```
- [ ] Se un solo match, comportamento come prima (singolo code)
- [ ] Test con vari input: "Italy", "Italia", "Deutschland", "Germany"

**TODO risolti**: ✅ `geo_normalization.py:55` (partial - best effort)

---

### Step 4.2: Country list endpoint

**Files**:
1. ✏️ `backend/app/api/v1/utilities.py` - New endpoint
2. ✏️ `backend/app/schemas/utilities.py` - Response schema (già mostrato sopra)

**Tasks**:
- [ ] Implementare endpoint `GET /utilities/countries/list?lang=en`
- [ ] Usare `pycountry.countries` per lista completa
- [ ] Parameter `lang` (solo "en" supportato per ora)
- [ ] Sort alfabetico per nome
- [ ] Test endpoint:
  - Verificare ~249 paesi ritornati
  - Verificare sorting corretto
  - Verificare USA, ITA, DEU presenti

**TODO risolti**: ✅ New feature (no existing TODO)

---

### Step 4.3: Region expansion

**Files**:
1. ✏️ `backend/app/utils/geo_normalization.py` - Region mapping dict
2. ✏️ `backend/app/api/v1/utilities.py` - Use mapping

**Tasks**:
- [ ] Creare `REGION_MAPPING` dict con massima copertura:
  ```python
  REGION_MAPPING = {
      # Europe
      "EUR": ["DEU", "FRA", "ITA", "ESP", "NLD", "AUT", "BEL", "FIN", "GRC", "IRL", "LVA", "LTU", "LUX", "MLT", "PRT", "SVK", "SVN", "CYP", "EST"],  # Eurozone 20
      "EU": ["DEU", "FRA", "ITA", "ESP", "NLD", "AUT", "BEL", "FIN", "GRC", "IRL", "LVA", "LTU", "LUX", "MLT", "PRT", "SVK", "SVN", "CYP", "EST", "POL", "CZE", "HUN", "SWE", "DNK", "BGR", "HRV", "ROU"],  # EU27
      "NORDIC": ["SWE", "DNK", "NOR", "FIN", "ISL"],
      
      # Americas
      "LATAM": ["BRA", "MEX", "ARG", "CHL", "COL", "PER", "VEN", "ECU", "BOL", "PRY", "URY", "CRI", "PAN", "GTM", "HND", "SLV", "NIC", "DOM", "CUB"],
      "NAFTA": ["USA", "CAN", "MEX"],
      
      # Asia
      "ASIA": ["CHN", "JPN", "IND", "KOR", "SGP", "THA", "VNM", "IDN", "MYS", "PHL", "TWN", "HKG", "PAK", "BGD", "LKA", "MMR", "KHM", "LAO", "MNG", "NPL"],
      "ASEAN": ["SGP", "THA", "VNM", "IDN", "MYS", "PHL", "KHM", "LAO", "MMR", "BRN"],
      
      # Middle East & Africa
      "MENA": ["ARE", "SAU", "QAT", "KWT", "OMN", "BHR", "JOR", "LBN", "EGY", "MAR", "TUN", "DZA", "IRQ", "YEM"],
      "AFRICA": ["ZAF", "EGY", "NGA", "KEN", "ETH", "GHA", "TZA", "UGA", "DZA", "MAR", "TUN", "MOZ", "AGO", "SEN", "CIV", "CMR", "ZWE", "RWA", "BEN"],
      
      # Oceania
      "OCEANIA": ["AUS", "NZL", "FJI", "PNG", "NCL", "PYF", "GUM", "SLB", "VUT"],
      
      # Others
      "G7": ["USA", "CAN", "GBR", "DEU", "FRA", "ITA", "JPN"],
      "G20": ["USA", "CAN", "GBR", "DEU", "FRA", "ITA", "JPN", "CHN", "IND", "BRA", "MEX", "RUS", "ZAF", "SAU", "TUR", "KOR", "IDN", "AUS", "ARG"],
      "BRICS": ["BRA", "RUS", "IND", "CHN", "ZAF"],
  }
  ```
- [ ] Aggiornare `normalize_country_to_iso3()` per espandere regioni
- [ ] Endpoint già supporta `List[str]` in response
- [ ] Test con ogni regione:
  - `EUR` → 19 paesi
  - `ASIA` → ~20 paesi
  - `G7` → 7 paesi

**TODO risolti**: ✅ `utilities.py:62`

---

## 🎯 FASE 5: Currency Refactoring Completo ⚡ BREAKING (3-4h)

### Step 5.1: Identificare usage di currency/amount nel codice

**Search patterns**:
```bash
# Trova tutti i posti dove si manipolano valute e importi
grep -r "Decimal.*amount" backend/app/
grep -r "\.upper().*currency" backend/app/
grep -r "from_currency.*to_currency" backend/app/
grep -r "value.*currency" backend/app/schemas/
```

**Files probabilmente da aggiornare**:
- `backend/app/services/fx.py` - **`convert()` e `convert_bulk()`** ⚡
- `backend/app/api/v1/fx.py` - FX conversion endpoints
- `backend/app/api/v1/assets.py` - Price operations
- `backend/app/schemas/prices.py` - Price models
- `backend/app/schemas/fx.py` - FX rate schemas
- `backend/app/services/asset_source.py` - Current value handling
- Provider implementations che ritornano `FACurrentValue`

**Task**:
- [ ] Creare lista completa di file da modificare
- [ ] Prioritize by: Services → Schemas → APIs → Providers

---

### Step 5.2: Aggiornare FX Service per ritornare `Currency` ⚡ BREAKING

**Files**:
1. ✏️ `backend/app/services/fx.py` - `convert()` e `convert_bulk()`

**Signature BEFORE**:
```python
async def convert(
    session,
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    as_of_date: date,
    return_rate_info: bool = False
) -> Decimal | tuple[Decimal, date, bool]:
    ...
```

**Signature AFTER** ⚡:
```python
async def convert(
    session,
    amount: Currency,  # ⚡ Era Decimal
    to_currency: str,  # ⚡ from_currency è in amount.code
    as_of_date: date,
    return_rate_info: bool = False
) -> Currency | tuple[Currency, date, bool]:  # ⚡ Era Decimal
    """
    Convert a Currency object to another currency.
    
    Args:
        session: Database session
        amount: Currency object to convert (contains code + amount)
        to_currency: Target currency code
        as_of_date: Date for FX rate
        return_rate_info: If True, return (converted, rate_date, backward_fill)
    
    Returns:
        Currency object in target currency, or tuple if return_rate_info=True
    """
    # Extract from_currency from amount object
    from_currency = amount.code
    amount_value = amount.amount
    
    # ... rest of logic ...
    
    # Return Currency object instead of Decimal
    converted = Currency(code=to_currency, amount=converted_amount)
    
    if return_rate_info:
        return converted, rate_date, backward_fill_applied
    return converted
```

**Tasks**:
- [ ] Aggiornare signature di `convert()`
- [ ] Aggiornare signature di `convert_bulk()` (simile)
- [ ] Aggiornare internal logic per usare `Currency`
- [ ] **Trovare TUTTI i call sites** e aggiornarli
- [ ] Test completi per conversioni

**Breaking Change**: ⚠️ SÌ - Signature change, tutti i caller vanno aggiornati

**TODO risolti**: ✅ `fx.py:637` + richiesta user su convert forex

---

### Step 5.3: Aggiornare Asset Service per usare `Currency`

**Files**:
1. ✏️ `backend/app/services/asset_source.py` - Métodi che gestiscono prezzi
2. ✏️ Provider implementations - `FACurrentValue` return

**Tasks**:
- [ ] Dove si crea `FACurrentValue(value=Decimal(...), currency="USD")`:
  - Cambiare in `FACurrentValue(value=Currency(code="USD", amount=Decimal(...)))`
- [ ] Aggiornare schema `FACurrentValue` per accettare `Currency`:
  ```python
  class FACurrentValue(BaseModel):
      value: Currency  # Era Decimal + separato currency: str
      as_of_date: date
      source: str
  ```
- [ ] Oppure mantenere retrocompat temporanea e convertire internamente
- [ ] Decidere strategia: **Breaking subito** o **graduale migration**?

**Recommendation**: Breaking subito, progetto embrionale.
Utente: confermo breaking subito
---

### Step 5.4: Aggiornare API endpoints per Currency

**Files**:
1. ✅ `backend/app/api/v1/fx.py` - Conversion endpoints
2. ✏️ `backend/app/api/v1/assets.py` - Price endpoints
3. ✅ `backend/app/schemas/fx.py` - FXConversionRequest/Result updated

**Strategy**:
Dove prendo già solo valuta e quantità, uso direttamente currency.
Dove ho più valute (ad esempio forex), per quella di partenza uso currecy, per quella di arrivo, metto una stringa con il codice valuta, e la classe pydantic valida che sia una valuta valida con le funzioni di currency.

**COMPLETATO**:
- [x] `FXConversionRequest`: `amount+from_currency` → `from_amount: Currency`
- [x] `FXConversionResult`: `amount+from_currency` → `from_amount: Currency`, `converted_amount+to_currency` → `to_amount: Currency`
- [x] `convert_currency_bulk()` in `fx.py` API aggiornato
- [x] Test files aggiornati: `test_fx_sync.py`, `test_fx_api.py`
- [x] RIMOSSO `normalize_currency_code` da validation_utils.py
- [x] Tutti i validator in `fx.py` usano ora `Currency.validate_code()`

---

### Step 5.5: Aggiornare Schemas per Currency

**Files**:
1. ✏️ `backend/app/schemas/prices.py` - `FAPricePoint`, etc.
2. ✏️ `backend/app/schemas/fx.py` - FX rate schemas
3. ✏️ `backend/app/schemas/assets.py` - Asset schemas con currency

**Decision needed**:

**Option B - Backward Compat** (Not recommended):
```python
class FAPricePoint(BaseModel):
    date: date
    close: Decimal  # Keep API contract
    currency: str   # Keep API contract
    
    @property
    def close_cur(self) -> Currency:
        """Internal use: Currency object."""
        return Currency(code=self.currency, amount=self.close)
```

**User choice**: Option B con validazione della currecy e un metodo property per ogni campo valore che fa questa conversione just in time

**Tasks**:
- [ ] Update ALL schemas che hanno currency/amount pairs
- [ ] Ensure serialization/deserialization works
- [ ] Update tests

---

### Step 5.6: Aggiornare Provider Implementations

**Files**: Tutti i provider in `backend/app/services/asset_source_providers/`

**Tasks**:
- [ ] `justetf.py` - Return Currency objects
- [ ] `yahoo_finance.py` - Return Currency objects  
- [ ] `css_scraper.py` - Return Currency objects
- [ ] `scheduled_investment.py` - Use Currency for calculations
- [ ] `mockprov.py` - Return Currency objects
- [ ] Test each provider

---

## 🎯 FASE 6: Test & Verification (2h)

### Step 6.1: Creare E2E test completo

**File**: `backend/test_scripts/test_e2e/test_search_to_prices.py`

**Test flow**:
```python
@pytest.mark.asyncio
async def test_complete_e2e_flow():
    """Test complete E2E flow without DB/web access."""
    
    # 1. Search asset
    response = await client.get("/api/v1/assets/provider/search?q=Apple")
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) > 0
    
    # Extract from search result (no DB lookup needed!)
    result = results[0]
    identifier = result["identifier"]
    identifier_type = result["identifier_type"]  # ✅ Now available
    provider_code = result["provider_code"]
    currency = result.get("currency")  # ✅ May be available
    
    # 2. Create asset
    asset_data = {
        "display_name": result["display_name"],
        "currency": currency or "USD",
        "asset_type": result.get("asset_type", "STOCK")
    }
    response = await client.post("/api/v1/assets", json=[asset_data])
    asset_id = response.json()["results"][0]["asset_id"]
    
    # 3. Assign provider (using data from search!)
    assignment = {
        "asset_id": asset_id,
        "provider_code": provider_code,
        "identifier": identifier,
        "identifier_type": identifier_type,  # ✅ No guessing!
        "provider_params": None
    }
    response = await client.post("/api/v1/assets/provider", json=[assignment])
    assert response.status_code == 200
    
    # 4. Refresh metadata
    response = await client.post(f"/api/v1/assets/provider/refresh?asset_ids={asset_id}")
    assert response.status_code == 200
    
    # Verify field details ✅
    result = response.json()["results"][0]
    fields_detail = result.get("fields_detail")
    assert fields_detail is not None
    assert "refreshed_fields" in fields_detail
    # Check OldNew format
    for change in fields_detail["refreshed_fields"]:
        assert "old" in change
        assert "new" in change
    
    # 5. Refresh prices
    response = await client.post("/api/v1/assets/prices/refresh", json=[{
        "asset_id": asset_id,
        "date_range": {
            "start": "2025-01-01",
            "end": "2025-01-10"
        }
    }])
    assert response.status_code == 200
    
    # 6. Get prices
    response = await client.get(f"/api/v1/assets/prices/{asset_id}")
    assert response.status_code == 200
    prices = response.json()["prices"]
    assert len(prices) > 0
    
    # ✅ Complete flow without ever accessing DB or external sites!
```

---

### Step 6.2: Currency Unit Tests

**File**: `backend/test_scripts/test_utilities/test_currency.py`

**Test coverage**:
- Creation (valid/invalid codes)
- Arithmetic operations (+, -, neg, abs)
- Error handling (different currencies)
- Crypto currencies
- Serialization (to_dict)
- String representation

---

### Step 6.3: Aggiornare Test Esistenti

**Files da aggiornare**:
- `test_assets_provider.py` - Search with identifier_type
- `test_external/test_asset_providers.py` - identifier_type check
- `test_api/test_fx.py` - Currency operations
- `test_services/test_fx.py` - FX service with Currency
- Tutti i test che usano Decimal per importi

---

## 📊 Impact Summary

| Categoria | Files | Tests | Breaking | Sforzo |
|-----------|-------|-------|----------|---------|
| Currency class | 15-20 | 10+ | ⚠️ SÌ | 🔴 Alto |
| identifier_type | 6 | 4 | ⚠️ SÌ | 🟡 Medio |
| OldNew + fields | 3 | 3 | ⚠️ SÌ | 🟢 Basso |
| hasattr cleanup | 4 | 0 | ✅ NO | 🟢 Basso |
| Utilities | 4 | 4 | ✅ NO | 🟡 Medio |
| **TOTALE** | **32-37** | **21+** | **3 Breaking** | **8-10h** |

---

## ⚠️ Breaking Changes Summary

### 1. `Currency` class - MAGGIORE
**Impact**: Tutti i file che manipolano importi e valute

**Migration path**: Nessuna - Cleanup completo
- Vecchio: `amount: Decimal, currency: str`
- Nuovo: `amount: Currency`

**Files impattati**: ~15-20

---

### 2. `identifier_type` required in search
**Impact**: Client che consumano search API

**Migration path**: Nessuna - Campo obbligatorio
- Vecchio: `{"identifier": "AAPL", "display_name": "Apple"}`
- Nuovo: `{"identifier": "AAPL", "identifier_type": "TICKER", "display_name": "Apple"}`

**Files impattati**: ~6

---

### 3. `refreshed_fields` type change
**Impact**: Client che leggono metadata refresh response

**Migration path**: Nessuna - Nuovo formato
- Vecchio: `["sector_area", "geographic_area"]`
- Nuovo: `[{"old": "Tech", "new": "Finance"}, {"old": null, "new": {...}}]`

**Files impattati**: ~3

---

## ✅ Definition of Done

### Funzionalità:
- [ ] ✅ E2E flow completo funziona via API (test passa)
- [ ] ✅ Search ritorna `identifier_type` required
- [ ] ✅ Metadata refresh ritorna `OldNew` details
- [ ] ✅ `Currency` class implementata, testata, usata ovunque
- [ ] ✅ FX `convert()` ritorna `Currency` objects
- [ ] ✅ Zero `hasattr()` nel codice
- [ ] ✅ Country list endpoint funzionante
- [ ] ✅ Region expansion implementata (max coverage)
- [ ] ✅ Multi-language country search (best effort)

### Qualità:
- [ ] ✅ Tutti i test passano (inclusi E2E)
- [ ] ✅ Code coverage ≥ 80% per nuovo codice
- [ ] ✅ Nessun codice legacy rimasto
- [ ] ✅ Nessuna retro-compatibilità (cleanup totale)
- [ ] ✅ Docstrings aggiornate
- [ ] ✅ TODO obsoleti rimossi
- [ ] ✅ VERIFICATION_REPORT.md creato

### Documentazione:
- [ ] ✅ `Currency` class documented in code + docstring
- [ ] ✅ Breaking changes documented
- [ ] ✅ Migration examples provided (anche se non servono per progetto embrionale)

---

## 📝 Ordine Esecuzione (SEQUENZIALE - No Overlap)

```
FASE 1: Infrastruttura
  └─ 1.1 Currency class
  └─ 1.2 OldNew generic  
  └─ 1.3 FAProviderRefreshFieldsDetail update
  └─ Test FASE 1

FASE 2: E2E Critici
  └─ 2.1 identifier_type in search
  └─ 2.2 Field details in metadata refresh
  └─ 2.3 Currency in search/metadata
  └─ Test FASE 2

FASE 3: Cleanup hasattr()
  └─ 3.1 AssetSourceProvider properties
  └─ 3.2 FX Provider properties
  └─ Test FASE 3

FASE 4: Utilities & UX
  └─ 4.1 Multi-language country search
  └─ 4.2 Country list endpoint
  └─ 4.3 Region expansion
  └─ Test FASE 4

FASE 5: Currency Refactoring Completo
  └─ 5.1 Identify usage
  └─ 5.2 FX Service
  └─ 5.3 Asset Service
  └─ 5.4 API endpoints
  └─ 5.5 Schemas
  └─ 5.6 Providers
  └─ Test FASE 5

FASE 6: Test & Verification
  └─ 6.1 E2E test completo
  └─ 6.2 Currency unit tests
  └─ 6.3 Update existing tests
  └─ Verification report
```

**Nessuna sovrapposizione tra fasi** ✅

---

## 🎯 Checkpoint Points

Dopo ogni FASE, verificare:

1. ✅ Tutti i test della fase passano
2. ✅ Nessun breaking change non documentato
3. ✅ Code coverage mantenuto/aumentato
4. ✅ Docstrings aggiornate
5. ✅ Commit con messaggio descrittivo

**Commit message format**:
```
feat(phase-N): [description]

- Implemented X
- Updated Y
- Removed Z

Breaking: [if applicable]
```

---

## 📌 Note Implementative

### Currency class - Design decisions:
- **Immutable**: Operations return new instance
- **Type safe**: Cannot mix currencies in operations
- **Validation eager**: Exception on invalid currency at creation
- **Crypto support**: Extensible dict for new cryptos

### OldNew generic - Usage:
- Use `OldNew[str]` when new is always defined
- Use `OldNew[str | None]` when new can be None (field cleared)
- `old` is always Optional (first time set → old=None)

### hasattr() removal - Rationale:
- Explicit better than implicit (Zen of Python)
- Base class defines contract
- Easier to discover provider capabilities
- Better IDE support

### Breaking changes - Philosophy:
- Progetto embrionale → cleanup completo OK
- No backward compatibility burden
- Cleaner architecture long-term
- Document everything

---

## 🚨 Rischi & Mitigazioni

### Rischio 1: Currency refactor troppo invasivo
**Probabilità**: Media  
**Impatto**: Alto  
**Mitigazione**: 
- Procedere fase per fase
- Test completi dopo ogni modifica
- Rollback facile per commit granulari

### Rischio 2: pycountry limiti multi-lingua
**Probabilità**: Alta  
**Impatto**: Basso  
**Mitigazione**:
- Fallback a inglese accettabile
- Country list endpoint come workaround
- Future: custom translation dict se serve

### Rischio 3: Test coverage drop
**Probabilità**: Media  
**Impatto**: Medio  
**Mitigazione**:
- Test dopo ogni fase
- Coverage report automatico
- Definition of Done richiede ≥80%

---

## ❓ Decisions Confirmed

✅ **Q1**: identifier_type REQUIRED  
✅ **Q2**: OldNew format with generics, new can be Optional in type  
✅ **Q3**: Max region expansion coverage  
✅ **Q4**: Currency Pydantic class with operations  
✅ **Q5**: Sequential execution, no overlap  
✅ **Q6**: Breaking changes OK, no legacy code  
✅ **Q7**: FX convert() returns Currency  

**All decisions confirmed** ✅ - READY TO IMPLEMENT

---

## 🎯 Next Steps

1. ✅ **Plan saved** in: `LibreFolio_developer_journal/prompts/plan-e2eFlowCompletionAndLegacyCleanup.prompt.md`

2. **Start with FASE 1.1**: Create Currency class
   - Most critical
   - Foundation for everything else
   - Can be tested in isolation

3. **After each phase**: Run tests, commit, verify

4. **Final verification**: E2E test passes, no legacy code remains

---

**Piano completato**: 2025-12-17  
**Approvato da**: User  
**Ready to implement**: ✅ YES

---

## 📎 Related Files

- `/VERIFICATION_REPORT.md` - Previous plan verification
- `/TODO_CLEANUP_REPORT.md` - TODO cleanup from previous phase
- `grep-todo_3.txt` - TODO source file
- `backend/app/utils/validation_utils.py` - Currency validation foundation

---

**END OF PLAN**

