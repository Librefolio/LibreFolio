# 📦 BRIM Providers List

This page lists all the broker import plugins (BRIM Providers) currently available in LibreFolio.

| Provider | Code | Formats | Status | Notes |
|:---------|:-----|:--------|:-------|:------|
| <img src="https://www.interactivebrokers.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Interactive Brokers**](../../../user/transactions/import/ibkr.md) | `broker_ibkr` | CSV | 🧪 Beta | Parses standard IBKR activity reports. |
| <img src="https://www.degiro.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Degiro**](../../../user/transactions/import/degiro.md) | `broker_degiro` | CSV | 🧪 Beta | Handles multi-language reports (Dutch, English, etc.). |
| <img src="https://www.etoro.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**eToro**](../../../user/transactions/import/etoro.md) | `broker_etoro` | CSV | 🧪 Beta | Supports stock and CFD transaction reports. |
| <img src="https://www.directa.it/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Directa SIM**](../../../user/transactions/import/directa.md) | `broker_directa` | CSV | ✅ Stable | Italian broker Directa. |
| <img src="https://www.schwab.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Charles Schwab**](../../../user/transactions/import/schwab.md) | `broker_schwab` | CSV | 🧪 Beta | Parses US-formatted CSV exports. |
| <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Revolut**](../../../user/transactions/import/revolut.md) | `broker_revolut` | CSV | 🧪 Beta | Handles Revolut Trading CSVs with multi-currency amounts. |
| <img src="https://www.coinbase.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Coinbase**](../../../user/transactions/import/coinbase.md) | `broker_coinbase` | CSV | 🧪 Beta | For crypto transactions from Coinbase. |
| <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Freetrade**](../../../user/transactions/import/freetrade.md) | `broker_freetrade` | CSV | 🧪 Beta | For UK broker Freetrade. |
| <img src="https://www.finpension.ch/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Finpension**](../../../user/transactions/import/finpension.md) | `broker_finpension` | CSV | 🧪 Beta | Swiss pension platform. |
| <img src="https://www.trading212.com/favicon.ico" alt="" style="width:16px;vertical-align:middle;margin-right:6px"> [**Trading212**](../../../user/transactions/import/trading212.md) | `broker_trading212` | CSV | 🧪 Beta | Parses Trading212's standard CSV export. |
| <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style="width:16px;vertical-align:middle;margin-right:6px"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> [**Generic CSV**](../../../user/transactions/import/generic-csv.md) | `broker_generic_csv` | CSV | ✅ Stable | Fallback provider. Accepts any CSV matching the [Generic CSV spec](generic_csv.md). |

---

### 🧪 Status Levels

| Level | Meaning |
|-------|---------|
| 🔬 **Alpha** | Early development — may have significant bugs |
| 🧪 **Beta** | Tested with sample files — edge cases may exist |
| ✅ **Stable** | Well-tested and reliable for supported formats |

