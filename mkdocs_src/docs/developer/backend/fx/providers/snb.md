# 🇨🇭 SNB — Swiss National Bank

| Property | Value |
|----------|-------|
| **Code** | `SNB` |
| **Base Currency** | CHF |
| **API Endpoint** | `https://data.snb.ch/api/cube` |
| **API Format** | JSON — `/devkum/dimensions/en` (currency list), `/devkum/data/json/en` (rates) |
| **API Key** | Not required |
| **Currencies** | ~25, read from the dataset's dimensions at first use (e.g. USD, EUR, GBP, JPY, CNY, AUD, CAD, …) |
| **Dataset** | `devkum` — monthly averages (`M0`); month-end values (`M1`) are not used |
| **Update Frequency** | Monthly, published around the 2nd business day of the following month |
| **API Docs** | [SNB Data Portal — devkum](https://data.snb.ch/en/topics/ziredev/cube/devkum) |

### ⚙️ How It Works

The Swiss National Bank provides exchange rates through their Data Portal API. The SNB offers **no daily-rate API**: the `devkum` dataset holds monthly averages, and the provider stores each one on the **1st of its month** to fit the daily-rate storage model.

- **Currency map**: loaded once per process from the `dimensions` endpoint (class-level cache). Forward rates (`USD3M`, `USD6M`) and the SDR (`XDR1`) are skipped. If the call fails, the provider raises `FXServiceError` ("Cannot load SNB currency list").
- **Request**: the filtered JSON endpoint with `dimSel=D0(M0),D1(…)` — only monthly averages, only the requested currencies — and `fromDate`/`toDate` in `YYYY-MM`.
- **Quotation**: "X CHF per 1 (or 100) units of the foreign currency". The provider divides by the unit count and returns CHF per 1 unit; the FX service normalizes the direction for storage.

### 🔢 Multi-Unit Currency Handling

Each series id carries its unit count: `EUR1` is CHF per 1 EUR, `CNY100` is CHF per 100 CNY. The provider parses it (`CNY100` → `CNY`, 100) and divides the value by it, so a `CNY100` value of 12.5 becomes 0.125 CHF per CNY.

### ⚠️ Limitations

- One value per month, dated the 1st: no daily movement.
- In chain routes, `compute_chain_rate` needs a rate on the exact same date for every leg, so a chain through SNB yields rates only on the 1st of each month. The provider's `warning_i18n` surfaces this as ⚠️ on such routes.
- Multi-unit quotation requires special handling (automated by the provider).
