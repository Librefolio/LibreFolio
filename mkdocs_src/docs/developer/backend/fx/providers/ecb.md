# 🇪🇺 ECB — European Central Bank

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

The European Central Bank publishes daily reference exchange rates for the Euro against approximately 45 currencies. The provider queries the ECB Statistical Data Warehouse using the SDMX REST API.

- **Dataset**: `EXR` (Exchange Rates)
- **Frequency**: `D` (Daily)
- **Series**: `SP00` (Spot rate)
- **Quotation**: Rates are "1 EUR = X foreign currency" — stored directly in LibreFolio's format.

### 💰 Supported Currencies

Major: USD 🇺🇸, GBP 🇬🇧, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, KRW 🇰🇷, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦, TRY 🇹🇷, PLN 🇵🇱, CZK 🇨🇿, HUF 🇭🇺, RON 🇷🇴, BGN 🇧🇬, HRK 🇭🇷, RUB 🇷🇺, and many more.

### ⚠️ Limitations

- No data on weekends or ECB holidays.
- Some emerging market currencies may have gaps during local holidays.
- Historical data before 1999 is not available.
