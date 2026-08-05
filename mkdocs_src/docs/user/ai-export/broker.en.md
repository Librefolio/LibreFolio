# 🧠 Broker AI Export

Broker AI Export prepares a clipboard snapshot or analysis prompt limited to one
accessible broker. LibreFolio never sends it to an AI service.

## 📍 Location

Open a Broker detail page and select **AI Export** in the top toolbar. The draft
remains available for 10 minutes in the current login session and resets after
logout or a new login.

## 🎯 Broker Analyses

| Task                                    | Focus                                                                                                                                     |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Broker Review**                       | Holdings, cash, activity, performance, and data coverage.                                                                                 |
| **Broker Performance & Market Drivers** | Performance reconciliation plus dated research for every Asset held through the Broker.                                                   |
| **Capital-Loss Offset Strategies**      | Conditional ways to use available or expiring tax losses against potentially eligible gains using selected-Broker economic FIFO evidence. |

## 🗂️ Scope and Data

The export is limited to the selected broker and current date range and target
currency. Depending on the selection, it can include cash balances, positions,
transactions, performance, costs, allocation, concentration, income, and FIFO
lot summaries. Server-side access checks prevent exporting a broker the
current user cannot read.

!!! important "Allocated and unallocated costs stay distinct"

    FIFO rows contain only fees and taxes deterministically allocated to lots.
    Broker-level unallocated costs remain in the general financial evidence and
    are never presented as zero lot costs.

## 📤 Export Data and Request Analysis

- **Export Data** copies one factual Broker dataset only.
- **Request Analysis** adds task-specific instructions, a response contract, and
  the datasets declared for the Analysis.
  The requested response language follows the current LibreFolio interface
  language.
- Optional notes are included only when supported by the selected Analysis.

Two public data exports are available:

- **Broker Overview & History** — selected-Broker holdings, cash, concentration,
  performance path, flows, costs, ratios, economic FIFO summary, compact per-Asset
  history, Drawdown, coverage, and provenance;
- **Broker Asset History** — Broker-scoped observed-close price buckets,
  indicators, states, events, breadth, and explicit reasons for current Assets
  excluded from technical eligibility.

## 🧾 Capital-Loss Offset Strategies

The prompt uses selected-Broker economic FIFO lots to identify conditional gain
and loss candidates, but never treats them as legally eligible automatically. It
first asks for tax residence, regime, account type, official tax-loss inventory,
amounts by legal category, origin and expiry dates, already-used balances, offset
rules, and whether balances across Brokers/accounts may be combined.

It can then compare no-action, eligible-gain realization before expiry, staged
realization aligned with rebalancing, and loss harvesting when relevant. Every
path shows costs, exposure changes, liquidity, concentration, timing, and legal
uncertainty; no trade is recommended solely for tax reasons.

## 📏 Detail and Sampling

| Detail       | Exact sampling                                                                   |
| ------------ | -------------------------------------------------------------------------------- |
| **Compact**  | Same data universe with the sparsest supported temporal buckets (up to 30 days). |
| **Standard** | Same data universe with temporal buckets up to 14 days.                          |
| **Full**     | Same data universe with temporal buckets up to 7 days.                           |

The general export uses 8/16/30 Broker path points and up to 6/12/24 compact
history points per eligible Asset. The detailed export keeps the full technical
sampling policy and can be large.

A dataset or Analysis can omit unavailable or non-applicable optional sections.
The **AI period** ends on the snapshot date. Partial history and coverage remain
explicit.

## 🔒 Applicability, Errors, and Privacy

Analyses can be unavailable when required facts do not exist. Choices also fail
closed on catalog or contract mismatch. Typed errors report access,
applicability, source, or contract problems.

The clipboard can contain sensitive account and transaction data. Review it
before sharing. See the [AI Export overview](index.md) for the
cross-domain workflow and safety model.
