# 🇨🇭 SNB — Swiss National Bank

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

The Swiss National Bank provides exchange rates through their Data Portal API. The provider queries the `devkum` dataset for daily rates.

- **Quotation**: "X CHF = 1 (or 100) foreign currency units" — the provider **inverts** and normalizes automatically.
- **Multi-unit currencies**: JPY, SEK, NOK, DKK are quoted per **100 units** (e.g., 100 JPY = 1.5 CHF). The provider divides by 100 automatically.

### 💰 Supported Currencies

USD 🇺🇸, EUR 🇪🇺, GBP 🇬🇧, JPY 🇯🇵, CAD 🇨🇦, AUD 🇦🇺, SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, CNY 🇨🇳.

### 🔢 Multi-Unit Currency Handling

| Currency | SNB Quotation | LibreFolio Normalization |
|----------|---------------|--------------------------|
| USD 🇺🇸 | 0.88 CHF = 1 USD | 1 CHF = 1.136 USD |
| JPY 🇯🇵 | 1.50 CHF = **100** JPY | 1 CHF = 66.67 JPY |
| SEK 🇸🇪 | 8.50 CHF = **100** SEK | 1 CHF = 11.76 SEK |

### ⚠️ Limitations

- Smallest provider list (~10 currencies only).
- No data on Swiss holidays and weekends.
- Multi-unit quotation requires special handling (automated by the provider).
