# 🇬🇧 BOE — Bank of England

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

The Bank of England provides exchange rates through their Statistical Interactive Database (IADB). Each currency has a unique series code.

- **Series codes**: Format `XUDL{XXX}` where `XXX` varies by currency (e.g., `XUDLUSS` for USD).
- **Quotation**: "Foreign currency per 1 GBP" — the provider normalizes these automatically.

### 💰 Supported Currencies

USD 🇺🇸, EUR 🇪🇺, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, ZAR 🇿🇦, INR 🇮🇳.

### ⚠️ Limitations

- The API returns HTML with embedded CSV data — parsing is more complex than pure JSON/CSV APIs.
- One request per currency (sequential).
- Some currencies have limited historical coverage.
