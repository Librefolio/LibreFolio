# Portfolio Analysis

This guide explains the portfolio analysis capabilities of LibreFolio, including runtime FIFO matching, time series generation, and key performance indicators (KPIs).

## 📈 Runtime Analysis Service

The core of the analysis engine is the `analysis.py` service. It provides on-demand calculations without persisting analysis data, ensuring that the results always reflect the most up-to-date transaction history.

### FIFO Matching
-   **First-In, First-Out (FIFO)**: The service matches SELL transactions with the earliest available BUY lots.
-   **Runtime Calculation**: FIFO matching is performed at runtime, meaning no "tax lots" are stored in the database. This provides maximum flexibility.
-   **Cost Basis**: Fees and taxes from BUY transactions are pro-rated into the unit cost of each lot.
-   **Realized P/L**: When a SELL is matched, the service calculates the realized profit or loss.

### Time Series Generation
The service can generate two fundamental time series for any asset over a given period:
1.  **Invested Capital**: A cumulative sum of cash outflows for `BUY` transactions, including fees and taxes. By default, it represents the total capital deployed into the asset.
2.  **Market Value**: The daily market value of the holdings. The valuation method depends on the asset's `valuation_model`:
    *   **`MARKET_PRICE`**: Uses daily closing prices from the `price_history` table, with forward-fill for missing days (e.g., weekends).
    *   **`SCHEDULED_YIELD`**: Calculates a synthetic daily value based on the asset's interest schedule (principal + accrued interest).

## 🔑 Key Performance Indicators (KPIs)

The analysis service computes several KPIs:

-   **Simple ROI (Return on Investment)**: A straightforward measure of profitability.
    `Simple ROI = (Market Value + Realized Cash - Total Invested) / Total Invested`
-   **Duration-Weighted ROI (DW-ROI)**: A more advanced metric that considers the time-weighted performance of each investment lot.

## 🤖 API Endpoint

The primary endpoint for asset analysis is:
`GET /api/v1/analysis/asset/{asset_id}`

### Query Parameters:
-   `broker_id` (optional): Filter analysis by a specific broker.
-   `start_date` & `end_date`: Define the time range for the analysis.
-   `use_cache` (optional, default: `false`): Whether to use a cached result if available.

### Response:
The endpoint returns a comprehensive JSON object containing:
- The `Invested` and `Market Value` time series.
- Calculated KPIs (Simple ROI, DW-ROI).
- An optional `matches` array showing the FIFO breakdown for transparency.

## 🕵️ How to get information about the portfolio analysis feature

To get information about the portfolio analysis feature an Agent can:

1.  Read this file.
2.  Read the original requirements in `LibreFolio_developer_journal/prompts/06_runtime_analysis_with_loans.txt`.
3.  Inspect the `backend/app/services/analysis.py` file for the core implementation.
4.  (Once implemented) Run the tests for the analysis service to see the calculations in action.
