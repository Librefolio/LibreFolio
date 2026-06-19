# 🇺🇸 FED — Federal Reserve (FRED)

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

- **Series IDs**: Format `DEXXX` (e.g., `DEXUSEU` = USD per 1 EUR).
- **Quotation**: "USD per 1 foreign currency" — the provider **inverts** these automatically to get LibreFolio's standard format.
- **Multi-unit currencies**: None (FRED quotes all currencies per 1 unit).

### 💰 Supported Currencies

EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, CHF 🇨🇭, AUD 🇦🇺, INR 🇮🇳, BRL 🇧🇷, MXN 🇲🇽, ZAR 🇿🇦, SGD 🇸🇬, HKD 🇭🇰, KRW 🇰🇷, TWD 🇹🇼, NZD 🇳🇿, THB 🇹🇭, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, CNY 🇨🇳.

### 🗺️ Series ID Mapping

| Currency | FRED Series | Direction |
|----------|-------------|-----------|
| EUR 🇪🇺 | `DEXUSEU` | USD per 1 EUR |
| GBP 🇬🇧 | `DEXUSUK` | USD per 1 GBP |
| JPY 🇯🇵 | `DEXJPUS` | JPY per 1 USD |
| CHF 🇨🇭 | `DEXSZUS` | CHF per 1 USD |
| CAD 🇨🇦 | `DEXCAUS` | CAD per 1 USD |
| AUD 🇦🇺 | `DEXUSAL` | USD per 1 AUD |

### ⚠️ Limitations

- One HTTP request per currency (sequential fetching).
- No data on US holidays and weekends.
- Some series may have occasional gaps.
