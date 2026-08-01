# 🧠 AI Export

AI Export turns the current LibreFolio context into structured text that you can
paste into an AI assistant or keep as a portable snapshot.

!!! important "Clipboard export only"

    LibreFolio does **not** contact an AI service. It builds the financial and
    technical snapshot on your server, renders it in your browser, and copies it
    to the clipboard. You choose whether and where to paste it.

## 📋 What It Does

AI Export is available from:

- the Dashboard toolbar for Portfolio tasks;
- the Broker toolbar for Broker tasks;
- the Signals header on Asset and FX detail pages.

The backend supplies valuations, performance, allocations, FIFO facts, FX
exposure, and technical indicators. **Export Data** copies one selected dataset
without analysis instructions. **Request Analysis** combines the datasets
declared for that Analysis with an objective and response contract. Optional notes
and the requested response language apply only to analyses.

## 🚀 How to Use It

1. Open the relevant Portfolio, Broker, Asset, or FX page.
2. Select **AI Export** (:material-brain:).
3. Choose **Export Data** or **Request Analysis**, then select a dataset or
   Analysis.
4. Choose the AI period and detail level.
5. For an analysis, add optional notes when the Analysis supports them.
6. Select **Copy AI Export**, then paste the result into the tool of your choice.

## 🎛️ Export Options

| Option | Meaning |
|---|---|
| **Export type** | **Export Data** creates a factual dataset prompt. **Request Analysis** adds the Analysis objective, verification instructions, response contract, and relevant datasets. |
| **Dataset or analysis** | The available choices come from the current LibreFolio runtime catalog for the page/domain. |
| **AI period** | **3M**, **6M**, **1Y**, or Custom when offered. The period ends on the snapshot date. Partial source history remains explicit. |
| **Detail level** | **Compact**, **Standard**, and **Full** keep the same data universe but use progressively denser temporal buckets where supported (up to 30, 14, or 7 days). Synthetic snapshots can remain similar across levels; Full is not always necessary. |
| **Notes for the AI** | Available for supported analyses. Adds optional user context as a safely serialized data block. |

Draft export type, selection, detail, AI period, and notes are remembered per authenticated user and page
context. Closing the panel or navigating away does not discard them.

## 🗂️ Available Analyses

### 📊 Portfolio

| Task | Purpose |
|---|---|
| Recurring Investment Plan | Review portfolio structure, cash flows, and constraints for recurring investments. |
| Portfolio Rebalancing | Compare current allocation with diversification and target-allocation context. |
| Performance Attribution | Identify the main contributors to performance over the selected period. |
| Portfolio Income Review | Review dividends, interest, and other portfolio income. |
| Portfolio FIFO Lot Review | Review all open lots plus lots closed during the previous three months across the active Dashboard broker scope. |
| Technical Breadth | Summarize technical signal breadth across portfolio assets. |
| Portfolio Description | Produce a factual overview of composition, allocation, and recent activity. |

### 🏦 Broker

| Task | Purpose |
|---|---|
| Broker Review | Summarize holdings, cash, activity, performance, and data coverage for one broker. |
| Broker Cost Efficiency | Review fees, taxes, turnover, and cost patterns. |
| Broker Concentration Context | Review concentration by assets, currencies, and portfolio share. |
| FIFO Lot Review | Review all open lots plus lots closed during the previous three months for one broker. |

### 📈 Asset

| Task | Purpose |
|---|---|
| Asset Trend Analysis | Review price trends, normalized returns, drawdowns, and technical signals. |
| Position Review | Review size, cost basis, performance, income, and concentration context. |

### 💱 FX

| Task | Purpose |
|---|---|
| FX Trend Review | Review pair direction, returns, volatility, and technical context. |
| FX Conversion Timing Context | Review trend, volatility, and rate context for a possible conversion. |
| FX Exposure Impact | Review direct cash, trading-currency, and valuation-currency links to the pair. |

## 🧩 Partial History and Additional Data

LibreFolio can export the history that is actually available when it is shorter
than the requested AI period. The prompt shows requested/available dates, coverage,
warnings, and any Signal that is partial or omitted. It never uses future prices
or rates.

An Analysis can recommend **Additional LibreFolio Data** when another export would
materially improve the answer. The prompt gives the public export name, UI path,
recommended period/detail, reason, and whether it is required or optional.

## 🔗 Local References

The prompt uses local references to join compact tables:

- A# for Assets;
- B# for Brokers;
- F# for FX pairs;
- L# for FIFO lots.

The Entity Directory resolves those references. The receiving model should use
readable names in its answer; database IDs are not needed.

## 🔒 Scope and Privacy

- Portfolio exports follow the active broker filter, date range, and target
  currency.
- Broker exports contain only the selected broker and require access to it.
- Asset and FX exports use the current entity, selected range, target currency,
  and the user's accessible broker scope where portfolio context is needed.
- The clipboard text can contain sensitive financial data. Review it before
  sharing or pasting it into a third-party service.

## ⚠️ Availability and Safety

AI Export fails closed if the browser and server catalogs or response contracts
do not match. An option can also be unavailable when its facts do not apply—for
example, Position Review without an open position, FIFO Lot Review without
holdings, or Performance Attribution without period contributions.

The export provides factual context, not investment advice or automated trading
instructions.

## 🔗 Related Pages

- [Portfolio AI Export](portfolio.md)
- [Broker AI Export](broker.md)
- [Asset AI Export](asset.md)
- [FX AI Export](fx.md)
