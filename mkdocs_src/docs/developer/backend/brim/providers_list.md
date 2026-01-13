# BRIM Providers List

This page lists all the broker import plugins (BRIM Providers) currently available in LibreFolio.

| Provider Name | Code | Supported Formats | Test Level | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Generic CSV** | `broker_generic_csv` | CSV | Beta | Fallback provider, flexible but may require manual mapping. |
| **Interactive Brokers** | `broker_ibkr` | CSV | Beta | Parses standard IBKR activity reports. |
| **Degiro** | `broker_degiro` | CSV | Beta | Handles multi-language reports (Dutch, English, etc.). |
| **eToro** | `broker_etoro` | CSV | Beta | Supports stock and CFD transaction reports. |
| **Directa SIM** | `broker_directa` | CSV | Beta | For Italian broker Directa. Skips 9-line header. |
| **Charles Schwab** | `broker_schwab` | CSV | Beta | Parses US-formatted CSV exports. |
| **Revolut** | `broker_revolut` | CSV | Beta | Handles Revolut Trading CSVs with multi-currency amounts. |
| **Coinbase** | `broker_coinbase` | CSV | Beta | For crypto transactions from Coinbase. |
| **Freetrade** | `broker_freetrade` | CSV | Beta | For UK broker Freetrade. |
| **Finpension** | `broker_finpension` | CSV | Beta | For Swiss pension platform Finpension (uses semicolon delimiter). |
| **Trading212** | `broker_trading212` | CSV | Beta | Parses Trading212's standard CSV export. |

---

### Test Levels

-   **Alpha**: The plugin is in early development and may have significant bugs.
-   **Beta**: The plugin has been tested with sample files and is considered reasonably stable, but may have edge cases that are not handled.
-   **Stable**: The plugin is well-tested and considered reliable for its supported formats.
