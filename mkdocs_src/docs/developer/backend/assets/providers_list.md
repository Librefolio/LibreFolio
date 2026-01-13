# Asset Providers List

This page lists the asset pricing providers currently available in LibreFolio.

| Provider Name | Code | Features | Test Level | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Yahoo Finance** | `yfinance` | History, Search, Metadata | Beta | Uses `yfinance` library. Supports Stocks, ETFs, Crypto. |
| **JustETF** | `justetf` | History, Search, Metadata | Beta | Scrapes JustETF.com. Excellent for European ETFs. |
| **CSS Scraper** | `cssscraper` | Current Value | Beta | Scrapes any URL using CSS selectors. No history. |
| **Scheduled Investment** | `scheduled_investment` | History (Calc) | Beta | Synthetic provider for bonds/loans. Calculates value based on interest schedule. |
| **Mock Provider** | `mock_provider` | History, Search | Alpha | For testing purposes only. |

---

### Feature Key

-   **History**: Can fetch historical OHLC data.
-   **Search**: Supports searching for assets by name/ticker.
-   **Metadata**: Can fetch asset details (sector, description, etc.).
-   **Current Value**: Can fetch the latest real-time price.
