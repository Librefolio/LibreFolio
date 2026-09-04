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
- the page toolbar on Asset and FX detail pages.

The backend supplies valuations, performance, allocations, economic FIFO facts,
FX exposure, and technical indicators. The public catalog intentionally exposes
only **eight autonomous Export Data choices** and **eleven task-oriented
Analyses**. Smaller backend datasets remain internal composition blocks.

**Export Data** copies one selected factual snapshot without analysis
instructions. **Request Analysis** adds an objective and response contract to an
autonomous snapshot, plus a complementary public export suggestion when useful.
Optional notes and the requested response language apply only to analyses.

## 🚀 How to Use It

1. Open the relevant Portfolio, Broker, Asset, or FX page.
2. Select **AI Export** (:material-brain:).
3. Choose **Export Data** or **Request Analysis**, then select a dataset or
   Analysis.
4. Choose the AI period and detail level.
5. For an analysis, add optional notes when the Analysis supports them.
6. Select **Copy AI Export**, then paste the result into the tool of your choice.

## 🎛️ Export Options

| Option                  | Meaning                                                                                                                                                                                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Export type**         | **Export Data** creates a factual dataset prompt. **Request Analysis** adds the Analysis objective, verification instructions, response contract, and relevant datasets.                                                                                     |
| **Dataset or analysis** | The available choices come from the current LibreFolio runtime catalog for the page/domain.                                                                                                                                                                  |
| **AI period**           | **3M**, **6M**, **1Y**, or Custom when offered. The period ends on the snapshot date. Partial source history remains explicit.                                                                                                                               |
| **Detail level**        | **Compact**, **Standard**, and **Full** keep the same entity universe. General snapshots use progressively denser uniform mini-histories; detailed market exports use the complete technical sampling policy. Full can be large and is not always necessary. |
| **Notes for the AI**    | Available for supported analyses. Adds optional user context as a safely serialized data block.                                                                                                                                                              |

Draft export type, selection, detail, AI period, and notes remain in browser
memory for 10 minutes per page context. Closing the panel or navigating away
preserves them within that window. Expiry, logout, or any new login resets every
AI Export panel to its defaults; drafts are not persisted in `localStorage`.

## 📤 Available Export Data

| Page      | General snapshot                     | Detailed market history               |
| --------- | ------------------------------------ | ------------------------------------- |
| Dashboard | **Portfolio Overview & History**     | **Portfolio Asset History**           |
| Broker    | **Broker Overview & History**        | **Broker Asset History**              |
| Asset     | **Position & Market History (full)** | **Market History Only (no holdings)** |
| FX        | **FX Market & Exposure**             | **FX Market History**                 |

General snapshots combine current economic facts with a compact historical path
and focused market context. Detailed market histories contain denser observed
prices or rates, indicators, states, events, and coverage.

## 🗂️ Available Analyses

### 📊 Portfolio

| Task                                   | Purpose                                                                                                                                            |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Recurring Investment Plan              | Review portfolio structure, cash flows, and constraints for recurring investments.                                                                 |
| Portfolio Rebalancing                  | Compare current allocation with diversification and target-allocation context.                                                                     |
| Portfolio Performance & Market Drivers | Reconcile performance, then research dated short- and long-horizon drivers for every held Asset without overstating causality.                     |
| Capital-Loss Offset Strategies         | Explore how available or expiring tax losses might offset eligible gains using economic FIFO evidence and an explicit official tax-loss inventory. |

### 🏦 Broker

| Task                                | Purpose                                                                                                                |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Broker Review                       | Summarize holdings, cash, activity, performance, and data coverage for one broker.                                     |
| Broker Performance & Market Drivers | Reconcile selected-Broker performance and research dated drivers for every held Asset.                                 |
| Capital-Loss Offset Strategies      | Explore tax-loss offset paths using selected-Broker economic FIFO evidence and the user's official tax-loss inventory. |

### 📈 Asset

| Task                  | Purpose                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------ |
| Position Review       | Review size, cost basis, performance, income, and concentration context.                                     |
| Asset Market Analysis | Review observed-close history, returns, trend, momentum, volatility, Drawdown, states, events, and coverage. |

### 💱 FX

| Task               | Purpose                                                                                            |
| ------------------ | -------------------------------------------------------------------------------------------------- |
| FX Pair Analysis   | Review pair direction, returns, volatility, technical evidence, coverage, and dated macro context. |
| FX Exposure Impact | Review direct cash, trading-currency, and valuation-currency links to the pair.                    |

Analyses that compare future paths use a **Scenario Thesis**: supplied evidence,
assumptions, horizon, trade-offs, trigger conditions, invalidation conditions, and
missing user decisions. It is mandatory for PAC, rebalancing, and capital-loss
offset scenarios.

## 🧩 Partial History and Additional Data

LibreFolio can export the history that is actually available when it is shorter
than the requested AI period. The prompt shows requested/available dates, coverage,
warnings, and any Signal that is partial or omitted. It never uses future prices
or rates.

An Analysis can recommend **Additional LibreFolio Data** when another export would
materially improve the answer. The prompt gives the public export name, UI path,
recommended period/detail, reason, and whether it is required or optional.

!!! info "Drawdown is always full-history"

    Wherever a Drawdown section appears in an export, it is computed over the
    **full available history** — from the first stored price for an Asset, or
    from the first transaction for a Portfolio or Broker — never relative to
    the selected AI period. A short export window still carries the true
    historical peak-to-trough.

## 🔗 Local References

The prompt uses local references to join compact tables:

- A# for Assets;
- B# for Brokers;
- F# for FX pairs;
- L# for FIFO lots.

The Entity Directory resolves the A#, B#, and F# references. L# lots are
different: they are **embedded rows** inside the FIFO tables of the export
itself, not directory entries — the model reads them in place. The receiving
model should use readable names in its answer; database IDs are not needed.

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
example, Position Review without an open position or FX Exposure Impact without
direct linked exposure.

The export provides factual context, not investment advice or automated trading
instructions.

## 🔗 Related Pages

- [Portfolio AI Export](portfolio.md)
- [Broker AI Export](broker.md)
- [Asset AI Export](asset.md)
- [FX AI Export](fx.md)
