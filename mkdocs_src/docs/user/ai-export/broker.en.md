# 🧠 Broker AI Export

Broker AI Export prepares a clipboard snapshot or analysis prompt limited to one
accessible broker. LibreFolio never sends it to an AI service.

## 📍 Location

Open a Broker detail page and select **AI Export** in the top toolbar. Your draft
is remembered separately for this user and broker.

## 🎯 Broker Tasks

| Task | Focus |
|---|---|
| **Broker Review** | Holdings, cash, activity, performance, and data coverage. |
| **Broker Cost Efficiency** | Fees, taxes, turnover, and cost patterns. |
| **Broker Concentration Context** | Asset, currency, and portfolio-share concentration. |
| **FIFO Lot Review** | Aggregate open/partial/closed counts, residual cost basis, age, and realized/unrealized components. |

## 🗂️ Scope and Data

The export is limited to the selected broker and current date range and target
currency. Depending on the task, it can include cash balances, positions,
transactions, performance, costs, allocation, concentration, income, and an
aggregate FIFO summary. Server-side access checks prevent exporting a broker the
current user cannot read.

!!! important "FIFO Review is aggregate"

    The current snapshot does not contain one row per lot and does not export
    custody history, lot events, value/return history, or price history. It reports
    counts and totals only, so the prompt must not imply fragment-level or
    per-lot evolution.

## 📸 Snapshot and Analyses

- **Data Snapshot** copies factual structured broker data only.
- An **analysis task** adds task-specific instructions and a response contract.
  The requested response language follows the current LibreFolio interface
  language.
- Optional notes are included only when supported by the selected task.

## 📏 Detail and Sampling

| Detail | Exact sampling |
|---|---|
| **Compact** | Latest values and aggregates only; no time series. Where applicable, the task profile uses an explicit compact selection of broker entities, such as relevant positions or lots. |
| **Standard** | All applicable entities; up to **7 recent daily points** plus **8 preceding weekly points**. |
| **Full** | All applicable entities; **7 recent daily points** plus weekly points across the **full technical window**. |

A task/profile may omit sections whose data is unavailable or not applicable.

## 🔒 Applicability, Errors, and Privacy

Tasks can be unavailable when required facts do not exist—for example, FIFO Lot
Review without holdings. Choices also fail closed on catalog or contract
mismatch. Typed errors report access, applicability, source, or contract
problems.

The clipboard can contain sensitive account and transaction data. Review it
before sharing. See the [AI Export overview](index.md) for the
cross-domain workflow and safety model.
