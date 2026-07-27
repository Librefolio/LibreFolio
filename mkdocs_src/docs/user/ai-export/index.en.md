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
exposure, and technical indicators. **Data Snapshot** copies those facts without
analysis instructions. Every analysis choice automatically adds its task
instructions and response contract, plus optional notes and safe YAML/Markdown
formatting. The requested response language always follows the current
LibreFolio interface language.

## 🚀 How to Use It

1. Open the relevant Portfolio, Broker, Asset, or FX page.
2. Select **AI Export** (:material-brain:).
3. Choose **Data Snapshot** or an analysis task, then choose the detail level.
4. For an analysis, add optional notes when the task supports them.
5. Select **Copy AI Export**, then paste the result into the tool of your choice.

## 🎛️ Export Options

| Option | Meaning |
|---|---|
| **Analysis type** | **Data Snapshot** is always first and copies factual data only. Every other choice is an analysis that automatically includes its task instructions and response contract. |
| **Detail level** | **Compact** uses latest values/aggregates only with no series and an explicit compact entity selection where applicable. **Standard** includes all applicable entities with up to 7 recent daily points plus 8 preceding weekly points. **Full** includes all applicable entities with 7 recent daily points plus weekly points across the full technical window. A task/profile may omit unavailable or non-applicable sections. |
| **Notes for the AI** | Available for supported analyses. Adds optional user context as a safely serialized data block. |

Draft task, detail, and notes are remembered per authenticated user and page
context. Closing the panel or navigating away does not discard them.

## 🗂️ Available Tasks

### 📊 Portfolio

| Task | Purpose |
|---|---|
| Recurring Investment Plan | Review portfolio structure, cash flows, and constraints for recurring investments. |
| Portfolio Rebalancing | Compare current allocation with diversification and target-allocation context. |
| Performance Attribution | Identify the main contributors to performance over the selected period. |
| Portfolio Income Review | Review dividends, interest, and other portfolio income. |
| Technical Breadth | Summarize technical signal breadth across portfolio assets. |
| Portfolio Description | Produce a factual overview of composition, allocation, and recent activity. |

### 🏦 Broker

| Task | Purpose |
|---|---|
| Broker Review | Summarize holdings, cash, activity, performance, and data coverage for one broker. |
| Broker Cost Efficiency | Review fees, taxes, turnover, and cost patterns. |
| Broker Concentration Context | Review concentration by assets, currencies, and portfolio share. |
| FIFO Lot Review | Summarize aggregate open/partial/closed FIFO counts, residual cost basis, age, and result components for one broker. |

### 📈 Asset

| Task | Purpose |
|---|---|
| Data Snapshot | Copy raw asset identity, valuation, position, performance, and available technical facts without interpretation. |
| Asset Trend Analysis | Review price trends, normalized returns, drawdowns, and technical signals. |
| Position Review | Review size, cost basis, performance, income, and concentration context. |
| Drawdown and Recovery | Analyze drawdown depth, duration, recovery progress, and related market context. |

### 💱 FX

| Task | Purpose |
|---|---|
| Data Snapshot | Copy raw pair, rate-history, provider, and technical facts without interpretation. |
| FX Trend Review | Review pair direction, returns, volatility, and technical context. |
| FX Conversion Timing Context | Review trend, volatility, and rate context for a possible conversion. |

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
