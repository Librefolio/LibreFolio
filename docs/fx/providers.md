# Available FX Providers

Complete reference for all supported FX rate providers.

---

## 📊 Provider Overview

| Provider | Code | Base | Currencies | Multi-Unit | API Key |
|----------|------|------|------------|------------|---------|
| European Central Bank | `ECB` | EUR | 45+ | No | ✅ **Not required** |
| Federal Reserve | `FED` | USD | 20+ | No | ✅ **Not required** |
| Bank of England | `BOE` | GBP | 15+ | No | ✅ **Not required** |
| Swiss National Bank | `SNB` | CHF | 10+ | Yes | ✅ **Not required** |

> 🎉 **Great news!** All current providers are **public APIs** that don't require API keys. This means:
> - ✅ No registration needed
> - ✅ No configuration required
> - ✅ No rate limits to worry about (within reasonable use)
> - ✅ Works out of the box

---

## 🇪🇺 ECB - European Central Bank

### Overview

**Provider Code**: `ECB`  
**Base Currency**: `EUR`  
**API**: https://data.ecb.europa.eu/help/api/overview  
**Coverage**: 45+ currencies  
**Multi-Unit**: No  
**API Key**: ✅ **Not required** (public API, no registration needed)

**File**: `backend/app/services/fx_providers/ecb.py`

### Features

- ✅ **Dynamic currency list** - Fetched from API
- ✅ **JSON response format** - Easy parsing
- ✅ **Comprehensive coverage** - Major and emerging market currencies
- ✅ **Well-documented API** - SDMX 2.1 RESTful standard
- ✅ **Historical data** - Years of historical rates

### Supported Currencies

**Major**: USD, GBP, JPY, CHF, CAD, AUD  
**European**: BGN, CZK, DKK, HUF, PLN, RON, SEK, NOK, ISK  
**Asian**: CNY, HKD, INR, IDR, KRW, MYR, PHP, SGD, THB, TWD  
**Other**: ARS, BRL, CLP, COP, ILS, MXN, NZD, PEN, RUB, TRY, ZAR

**Total**: 45+ currencies

### API Details

**Base URL**: `https://data-api.ecb.europa.eu/service/data`  
**Dataset**: `EXR` (Exchange Rates)  
**Frequency**: Daily (`D`)

**Example API Call**:
```
GET https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A
  ?format=jsondata
  &startPeriod=2025-01-01
  &endPeriod=2025-01-31
```

**Response Format**:
```json
{
  "dataSets": [{
    "series": {
      "0:0:0:0:0": {
        "observations": {
          "0": [1.0850],  // 2025-01-01: 1 EUR = 1.0850 USD
          "1": [1.0875]   // 2025-01-02: 1 EUR = 1.0875 USD
        }
      }
    }
  }]
}
```

### Rate Semantics

**ECB provides**: `1 EUR = X foreign currency`

**Examples**:
- 1 EUR = 1.08 USD
- 1 EUR = 0.85 GBP
- 1 EUR = 165.5 JPY

### Usage

```python
provider = FXProviderFactory.get_provider('ECB')

# Get supported currencies
currencies = await provider.get_supported_currencies()

# Fetch rates
rates = await provider.fetch_rates(
    date_range=(date(2025, 1, 1), date(2025, 1, 31)),
    currencies=['USD', 'GBP', 'JPY']
)
```

---
**Multi-Unit**: No (all per 1 unit, including JPY)  
**API Key**: ✅ **Not required** (public CSV download, no authentication)

**File**: `backend/app/services/fx_providers/fed.py`

**Provider Code**: `FED`  
**Base Currency**: `USD`  
**API**: FRED (Federal Reserve Economic Data)  
**Coverage**: 20+ major currencies  
- ✅ **Major currencies** - Focus on most traded
- ✅ **Historical data** - Extensive history

**Multi-Unit Support**: No (all per 1 unit, including JPY)  
**API Key**: ❌ Not required (uses public CSV)
### Features

- ✅ **H.10 Release** - Official foreign exchange rates
- ✅ **CSV format** - Simple parsing
**File**: `backend/app/services/fx_providers/fed.py`

- ✅ **No API key** - Public CSV download

### Supported Currencies

**Major**: EUR, GBP, JPY, CHF, CAD, AUD, NZD  
**Asian**: CNY, HKD, INR, KRW, MYR, SGD, TWD, THB  
**Other**: BRL, MXN, SEK, DKK, NOK, ZAR

**Total**: 20+ currencies

### API Details

**Base URL**: `https://www.federalreserve.gov/datadownload/Output.aspx`  
**Series**: `H10` (Foreign Exchange Rates)

**Example API Call**:
```
GET https://www.federalreserve.gov/datadownload/Output.aspx
  ?rel=H10
  &series=DEXUSEU  # EUR/USD
  &lastobs=
  &from=01/01/2025
  &to=01/31/2025
  &filetype=csv
```

**Response Format** (CSV):
```
Date,DEXUSEU
2025-01-01,1.0850
2025-01-02,1.0875
```

### Rate Semantics

**FED provides**: `1 foreign currency = X USD`

**Provider inverts to**: `1 USD = X foreign currency`

**Examples** (after inversion):
- 1 USD = 0.92 EUR
- 1 USD = 1.27 GBP
- 1 USD = 149.5 JPY

### FRED Series Mapping

```python
CURRENCY_SERIES = {
    'EUR': 'DEXUSEU',  # Euro
    'GBP': 'DEXUSUK',  # British Pound
    'JPY': 'DEXJPUS',  # Japanese Yen
    'CHF': 'DEXSZUS',  # Swiss Franc
    'CAD': 'DEXCAUS',  # Canadian Dollar
    # ... etc
}
```

### Usage

```python
provider = FXProviderFactory.get_provider('FED')

# Fetch rates
rates = await provider.fetch_rates(
## 🇬🇧 BOE - Bank of England

### Overview

)
```

---
**Multi-Unit**: No  
**API Key**: ✅ **Not required** (public API, no registration needed)

**Multi-Unit**: No  
**API Key**: ✅ **Not required** (public API, no registration needed)
**Provider Code**: `BOE`  
**Base Currency**: `GBP`  
**API**: Bank of England Statistical Interactive Database  
**Coverage**: 15+ currencies  
**Multi-Unit Support**: No  
**API Key**: ❌ Not required

**File**: `backend/app/services/fx_providers/boe.py`

### Features

- ✅ **Official UK rates** - From Bank of England
- ✅ **Major currencies** - Focus on key trading partners
- ✅ **CSV-like format** - Simple parsing
- ✅ **UK business days** - Aligns with UK calendar

### Supported Currencies

**Major**: USD, EUR, JPY, CHF, CAD, AUD, NZD  
**Asian**: CNY, HKD, INR, SGD  
**European**: SEK, NOK, DKK  
**Other**: ZAR

**Total**: 15+ currencies

### API Details

**Base URL**: `https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp`

**Example API Call**:
```
GET https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp
  ?Datefrom=01/Jan/2025
  &Dateto=31/Jan/2025
  &SeriesCodes=XUDLUSS  # USD/GBP series
  &CSVF=TN
  &UsingCodes=Y
  &VPD=Y
```

**Response Format** (CSV):
```
DATE,XUDLUSS
01 Jan 2025,1.2750
02 Jan 2025,1.2760
```

**Note**: Requires proper `User-Agent` header

### Rate Semantics

**BOE provides**: `1 GBP = X foreign currency`

**Examples**:
- 1 GBP = 1.27 USD
- 1 GBP = 1.16 EUR
- 1 GBP = 193.5 JPY

### Series Codes

```python
CURRENCY_SERIES = {
    'USD': 'XUDLUSS',  # US Dollar
    'EUR': 'XUDLERS',  # Euro
    'JPY': 'XUDLJYS',  # Japanese Yen
    'CHF': 'XUDLSFS',  # Swiss Franc
    # ... etc
}
```

### Usage

```python
provider = FXProviderFactory.get_provider('BOE')

# Fetch rates
rates = await provider.fetch_rates(
    date_range=(date(2025, 1, 1), date(2025, 1, 31)),
    currencies=['USD', 'EUR', 'JPY']
)
```

---

## 🇨🇭 SNB - Swiss National Bank

### Overview

**Provider Code**: `SNB`  
**Base Currency**: `CHF`  
**API**: https://data.snb.ch/en/topics/uvo  
**Coverage**: 10+ currencies  
**Multi-Unit**: ✅ Yes (JPY, SEK, NOK, DKK per 100 units)  
**API Key**: ✅ **Not required** (public API, no registration needed)

**File**: `backend/app/services/fx_providers/snb.py`

### Features

- ✅ **Multi-unit handling** - Correct JPY, SEK, NOK, DKK rates
- ✅ **Clean API** - Well-designed REST API
- ✅ **CSV format** - Easy parsing
- ✅ **Swiss business days** - Aligns with Swiss calendar

### Supported Currencies

**Major**: USD, EUR, GBP, JPY, CAD, AUD  
**Nordic**: SEK, NOK, DKK  
**Asian**: CNY

**Total**: 10+ currencies

### Multi-Unit Currencies

The following currencies are quoted **per 100 units**:

- **JPY** - Japanese Yen
- **SEK** - Swedish Krona
- **NOK** - Norwegian Krone
- **DKK** - Danish Krone

**Why?** These currencies have small unit values, so quoting per 100 makes rates more readable.

**Example**:
- API returns: `100 JPY = 0.67 CHF`
- Provider adjusts: `1 JPY = 0.0067 CHF`

### API Details

**Base URL**: `https://data.snb.ch/api/cube`  
**Dataset**: `devkum` (Exchange Rates)

**Example API Call**:
```
GET https://data.snb.ch/api/cube/devkum/data/csv/en
  ?from=2025-01-01
  &to=2025-01-31
  &series=D.M.USD  # Daily, Monthly average, USD
```

**Response Format** (CSV):
```
Date,Value
2025-01-01,0.9250
2025-01-02,0.9260
```

### Rate Semantics

**SNB provides**: `X CHF = 1 foreign currency` (or 100 for multi-unit)

**Provider inverts to**: `1 CHF = X foreign currency`

**Examples** (after inversion + multi-unit adjustment):
- 1 CHF = 1.08 USD
- 1 CHF = 0.95 EUR
- 1 CHF = 149.25 JPY (adjusted from per-100)

### Currency Codes

```python
CURRENCY_CODES = {
    'USD': 'USD',
    'EUR': 'EUR',
    'GBP': 'GBP',
    'JPY': 'JPY',  # Multi-unit
    'SEK': 'SEK',  # Multi-unit
    'NOK': 'NOK',  # Multi-unit
    'DKK': 'DKK',  # Multi-unit
    # ... etc
}
```

### Usage

```python
provider = FXProviderFactory.get_provider('SNB')

# Multi-unit currencies automatically handled
rates = await provider.fetch_rates(
    date_range=(date(2025, 1, 1), date(2025, 1, 31)),
    currencies=['USD', 'EUR', 'JPY']  # JPY auto-adjusted
)
```

---

## 🆚 Provider Comparison

### Coverage Comparison

| Currency | ECB | FED | BOE | SNB |
|----------|-----|-----|-----|-----|
| USD | ✅ | ✅ | ✅ | ✅ |
| EUR | ✅ | ✅ | ✅ | ✅ |
| GBP | ✅ | ✅ | ✅ | ✅ |
| JPY | ✅ | ✅ | ✅ | ✅ (multi) |
| CHF | ✅ | ✅ | ✅ | ✅ |
| CAD | ✅ | ✅ | ✅ | ✅ |
| AUD | ✅ | ✅ | ✅ | ✅ |
| CNY | ✅ | ✅ | ✅ | ✅ |
| INR | ✅ | ✅ | ✅ | ❌ |
| BRL | ✅ | ✅ | ❌ | ❌ |
| **API Key** | ✅ Not needed | ✅ Not needed | ✅ Not needed | ✅ Not needed |
| NOK | ✅ | ✅ | ✅ | ✅ (multi) |
| DKK | ✅ | ✅ | ✅ | ✅ (multi) |

### Feature Comparison

| Feature | ECB | FED | BOE | SNB |
|---------|-----|-----|-----|-----|
| **API Format** | JSON | CSV | CSV | CSV |
- ✅ You want dynamic currency discovery
| **Dynamic List** | ✅ Yes | ❌ Static | ❌ Static | ❌ Static |
| **Multi-Unit** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **API Key** | ❌ No | ❌ No | ❌ No | ❌ No |
| **Total Currencies** | 45+ | 20+ | 15+ | 10+ |
| **Update Frequency** | Daily | Daily | Daily | Daily |
| **API Key** | ✅ Not needed | ✅ Not needed | ✅ Not needed | ✅ Not needed |
### When to Use Each Provider

**Use ECB when**:
- ✅ You need EUR as base
- ✅ You need maximum currency coverage


**Use FED when**:
- ✅ You need USD as base
- ✅ You focus on major currencies
- ✅ You want official US rates

**Use BOE when**:
- ✅ You need GBP as base
- ✅ You focus on UK trading partners
- ✅ You want official UK rates

**Use SNB when**:
- ✅ You need CHF as base
- ✅ You need correct multi-unit handling (JPY, SEK, NOK, DKK)
- ✅ You want official Swiss rates

---

## 🔗 Related Documentation

- **[Provider Development Guide](./provider-development.md)** - How to add new providers
- **[Architecture](./architecture.md)** - System architecture
- **[API Reference](./api-reference.md)** - REST API endpoints

