# <img src="https://www.justetf.com/android-chrome-144x144.png?v2" alt=""> justETF

justETF provides detailed data for European ETFs, including current prices and historical data with multi-currency support.

## 📊 Capabilities

- ✅ **Current Price**: Real-time gettex quotes (EUR only)
- ✅ **History**: Historical price data in EUR, USD, CHF, or GBP
- ✅ **Search**: Full-text search across 3000+ European ETFs

## 💱 Currency Selection

justETF supports fetching prices in **4 currencies**: EUR, USD, CHF, GBP.

When you search for an ETF, results appear with currency flags:

| Flag | Meaning |
|------|---------|
| 🇪🇺 | Euro prices |
| 🇺🇸 | US Dollar prices |
| 🇨🇭 | Swiss Franc prices |
| 🇬🇧 | British Pound prices |
| 👑 | Fund's native NAV currency (shown alongside the flag) |

!!! note "Currency Conversion"

    JustETF performs the conversion server-side using their own FX rates.
    For currencies not in the supported list (JPY, SEK, etc.), use LibreFolio's built-in FX conversion system.

## ⚠️ Limitations

!!! warning "Current Price: EUR Only"

    Real-time prices (current value) are only available in **EUR** because they come from the **gettex** exchange WebSocket, which is a European exchange quoting in EUR.

    For non-EUR currencies (USD, CHF, GBP):

    - ✅ Historical data is available (converted by JustETF)
    - ❌ Real-time price is **not** available — the asset sync will show "current value unavailable"

    **Recommendation**: If you need real-time prices, use EUR. For portfolio tracking where daily closing prices suffice, any currency works.

## 🔧 Configuration

- **Identifier**: ISIN code (e.g., `IE00BK5BQT80`)
- **Identifier Type**: `ISIN`
- **Parameters**:
    - `currency`: Price currency — EUR (default), USD, CHF, or GBP

## 💡 Examples

| Asset | ISIN | Suggested Currency |
|-------|------|--------------------|
| Vanguard FTSE All-World | `IE00BK5BQT80` | EUR or USD 👑 |
| iShares Core MSCI World | `IE00B4L5Y983` | EUR or USD 👑 |
| Xtrackers MSCI Emerging Markets | `IE00BTJRMP35` | EUR or USD 👑 |

## 📝 Notes

- Best suited for European-domiciled ETFs listed on justETF
- Uses the ISIN as the primary identifier
- The 👑 in search results indicates the fund's native NAV denomination — this is the currency the fund manager uses internally, not necessarily the currency you trade in
