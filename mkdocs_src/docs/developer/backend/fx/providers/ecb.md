# 🇪🇺 ECB — European Central Bank

| Property | Value |
|----------|-------|
| **Code** | `ECB` |
| **Base Currency** | EUR |
| **API Endpoint** | `https://data-api.ecb.europa.eu/service/data/EXR/` |
| **API Format** | JSON (SDMX) |
| **API Key** | Not required |
| **Currencies** | Discovered at runtime by `get_supported_currencies()`: on 2026-10-08, 29 published daily and 44 plus EUR in the history |
| **Update Frequency** | Daily, ~16:00 CET on ECB business days |
| **Historical Data** | Available from 1999 |
| **API Docs** | [ECB Data Portal API](https://data.ecb.europa.eu/help/api/overview) |

### ⚙️ How It Works

The European Central Bank publishes daily reference exchange rates for the Euro against about 30 currencies. The provider queries the ECB Statistical Data Warehouse using the SDMX REST API; `get_supported_currencies()` (`backend/app/services/fx_providers/ecb.py`) reads the currency list from the same API, so it also returns the discontinued currencies that are still in the history.

- **Dataset**: `EXR` (Exchange Rates)
- **Frequency**: `D` (Daily)
- **Series**: `SP00` (Spot rate)
- **Quotation**: Rates are "1 EUR = X foreign currency" — stored directly in LibreFolio's format.

### 💰 Supported Currencies

Published daily (29 on 2026-10-08, from the ECB's `eurofxref-daily.xml`): AUD, BRL, CAD, CHF, CNY, CZK, DKK, GBP, HKD, HUF, IDR, ILS, INR, ISK, JPY, KRW, MXN, MYR, NOK, NZD, PHP, PLN, RON, SEK, SGD, THB, TRY, USD, ZAR.

History only: discontinued currencies such as BGN (last rate 2025-12-31, before Bulgaria adopted the euro), HRK and RUB. `fetch_rates()` gets their past observations from the same `EXR` series and nothing after the last one.

### ⚠️ Limitations

- No data on weekends or ECB holidays.
- Some emerging market currencies may have gaps during local holidays.
- Historical data before 1999 is not available.
