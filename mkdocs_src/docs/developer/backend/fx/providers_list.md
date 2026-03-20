# 🏦 FX Providers List

This page lists the Foreign Exchange (FX) rate providers currently available in LibreFolio, followed by detailed documentation for each.

## 📋 Summary Table

| | Provider Name             | Code  | Base Currency | Currencies | API Format | API Key | Test Level |
|:-:|:--------------------------|:------|:--------------|:-----------|:-----------|:--------|:-----------|
| <img src="https://www.ecb.europa.eu/favicon-32.png" style="height:18px"> | [**European Central Bank**](#ecb) | `ECB` | EUR           | ~45        | JSON/XML   | No      | Stable     |
| <img src="https://fred.stlouisfed.org/favicon.ico" style="height:18px"> | [**Federal Reserve**](#fed) | `FED` | USD           | ~20        | CSV        | No      | Beta       |
| <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" style="height:18px"> | [**Bank of England**](#boe) | `BOE` | GBP           | ~15        | CSV/HTML   | No      | Beta       |
| <img src="https://data.snb.ch/favicon.ico" style="height:18px"> | [**Swiss National Bank**](#snb) | `SNB` | CHF           | ~10        | CSV        | No      | Beta       |

### 📝 General Notes

- **Base Currency**: The currency against which all other rates are quoted by the provider. LibreFolio automatically handles conversions between any pair, regardless of the provider's base currency.
- **Update Frequency**: Most central banks update their rates once per business day (weekdays only).
- **No API Keys**: All core providers use publicly accessible APIs — no registration or API keys required.

---

## <img src="https://www.ecb.europa.eu/favicon-32.png" style="height:24px;vertical-align:middle"> ECB — European Central Bank { #ecb }

| Property | Value |
|----------|-------|
| **Code** | `ECB` |
| **Base Currency** | EUR |
| **API Endpoint** | `https://data-api.ecb.europa.eu/service/data/EXR/` |
| **API Format** | JSON (SDMX) |
| **API Key** | Not required |
| **Currencies** | ~45 (all major + many emerging markets) |
| **Update Frequency** | Daily, ~16:00 CET on ECB business days |
| **Historical Data** | Available from 1999 |
| **API Docs** | [ECB Data Portal API](https://data.ecb.europa.eu/help/api/overview) |

### ⚙️ How It Works

ECB publishes daily reference exchange rates for the Euro against ~45 currencies. The provider queries the ECB Statistical Data Warehouse using the SDMX REST API.

- **Dataset**: `EXR` (Exchange Rates)
- **Frequency**: `D` (Daily)
- **Series**: `SP00` (Spot rate)
- **Quotation**: Rates are "1 EUR = X foreign currency" — stored directly in LibreFolio's format

### 💰 Supported Currencies

Major: USD, GBP, JPY, CHF, CAD, AUD, NZD, SEK, NOK, DKK, CNY, HKD, SGD, KRW, INR, BRL, MXN, ZAR, TRY, PLN, CZK, HUF, RON, BGN, HRK, RUB, and many more.

### ⚠️ Limitations

- No data on weekends or ECB holidays
- Some emerging market currencies may have gaps during local holidays
- Historical data before 1999 is not available

---

## <img src="https://fred.stlouisfed.org/favicon.ico" style="height:24px;vertical-align:middle"> FED — Federal Reserve (FRED) { #fed }

| Property | Value |
|----------|-------|
| **Code** | `FED` |
| **Base Currency** | USD |
| **API Endpoint** | `https://fred.stlouisfed.org/graph/fredgraph.csv` |
| **API Format** | CSV (public download, no API key) |
| **API Key** | Not required |
| **Currencies** | ~20 major currencies |
| **Update Frequency** | Daily, US business days |
| **API Docs** | [FRED Economic Data](https://fred.stlouisfed.org/) |

### ⚙️ How It Works

The Federal Reserve provides exchange rate data through FRED (Federal Reserve Economic Data). The provider downloads CSV files for each currency series.

- **Series IDs**: Format `DEXXX` (e.g., `DEXUSEU` = USD per 1 EUR)
- **Quotation**: "USD per 1 foreign currency" — the provider **inverts** these automatically to get LibreFolio's standard format
- **Multi-unit currencies**: None (FRED quotes all currencies per 1 unit)

### 💰 Supported Currencies

EUR, GBP, JPY, CAD, CHF, AUD, INR, BRL, MXN, ZAR, SGD, HKD, KRW, TWD, NZD, THB, SEK, NOK, DKK, CNY.

### 🗺️ Series ID Mapping

| Currency | FRED Series | Direction |
|----------|-------------|-----------|
| EUR | `DEXUSEU` | USD per 1 EUR |
| GBP | `DEXUSUK` | USD per 1 GBP |
| JPY | `DEXJPUS` | JPY per 1 USD |
| CHF | `DEXSZUS` | CHF per 1 USD |
| CAD | `DEXCAUS` | CAD per 1 USD |
| AUD | `DEXUSAL` | USD per 1 AUD |

### ⚠️ Limitations

- One HTTP request per currency (sequential fetching)
- No data on US holidays and weekends
- Some series may have occasional gaps

---

## <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" style="height:24px;vertical-align:middle"> BOE — Bank of England { #boe }

| Property | Value |
|----------|-------|
| **Code** | `BOE` |
| **Base Currency** | GBP |
| **API Endpoint** | `https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp` |
| **API Format** | CSV (HTML response with embedded data) |
| **API Key** | Not required |
| **Currencies** | ~15 major currencies |
| **Update Frequency** | Daily, UK business days |
| **Historical Data** | Deep historical coverage (decades for major currencies) |
| **API Docs** | [BOE Statistical Interactive Database](https://www.bankofengland.co.uk/boeapps/database/) |

### ⚙️ How It Works

BOE provides exchange rates through their Statistical Interactive Database (IADB). Each currency has a unique series code.

- **Series codes**: Format `XUDL{XXX}` where `XXX` varies by currency (e.g., `XUDLUSS` for USD)
- **Quotation**: "Foreign currency per 1 GBP" — the provider normalizes these automatically

### 💰 Supported Currencies

USD, EUR, JPY, CHF, CAD, AUD, NZD, SEK, NOK, DKK, CNY, HKD, SGD, ZAR, INR.

### ⚠️ Limitations

- API returns HTML with embedded CSV data — parsing is more complex than pure JSON/CSV APIs
- One request per currency (sequential)
- Some currencies have limited historical coverage

---

## <img src="https://data.snb.ch/favicon.ico" style="height:24px;vertical-align:middle"> SNB — Swiss National Bank { #snb }

| Property | Value |
|----------|-------|
| **Code** | `SNB` |
| **Base Currency** | CHF |
| **API Endpoint** | `https://data.snb.ch/api/cube` |
| **API Format** | CSV |
| **API Key** | Not required |
| **Currencies** | ~10 major currencies |
| **Dataset** | `devkum` (Daily exchange rates) |
| **Update Frequency** | Daily, Swiss business days |
| **API Docs** | [SNB Data Portal](https://data.snb.ch/en/topics/uvo#!/doc/explanations) |

### ⚙️ How It Works

SNB provides exchange rates through their Data Portal API. The provider queries the `devkum` dataset for daily rates.

- **Quotation**: "X CHF = 1 (or 100) foreign currency units" — the provider **inverts** and normalizes automatically
- **Multi-unit currencies**: JPY, SEK, NOK, DKK are quoted per **100 units** (e.g., 100 JPY = 1.5 CHF). The provider divides by 100 automatically.

### 💰 Supported Currencies

USD, EUR, GBP, JPY, CAD, AUD, SEK, NOK, DKK, CNY.

### 🔢 Multi-Unit Currency Handling

| Currency | SNB Quotation | LibreFolio Normalization |
|----------|---------------|--------------------------|
| USD | 0.88 CHF = 1 USD | 1 CHF = 1.136 USD |
| JPY | 1.50 CHF = **100** JPY | 1 CHF = 66.67 JPY |
| SEK | 8.50 CHF = **100** SEK | 1 CHF = 11.76 SEK |

### ⚠️ Limitations

- Smallest provider list (~10 currencies only)
- No data on Swiss holidays and weekends
- Multi-unit quotation requires special handling (automated by the provider)
