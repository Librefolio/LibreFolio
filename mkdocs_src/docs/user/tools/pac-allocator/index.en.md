---
title: PAC Allocator P1
description: Split existing cash and new contributions across target Assets as exact theoretical reporting-currency amounts.
---

# 🧮 PAC Allocator P1

The **PAC Allocator** answers one question:

> How should the liquidity available for this contribution cycle be split across my target Assets?

Its investable budget is **existing cash plus new contributions**, valued in
your reporting currency. It applies each target percentage to that budget and
returns an exact theoretical monetary allocation for each Asset.

It does **not** inspect current holdings when calculating the split. If your
question is instead “How far is my invested portfolio from its desired final
allocation?”, use the
[Portfolio Rebalancer P1](../portfolio-rebalancer/index.md).

!!! warning "Planning amounts, not trade instructions"

    The result contains monetary shares of a budget. It never chooses units,
    creates orders, recommends purchases or sales, or proves that the native
    cash can fund a trade.

## 🎯 Choose the right allocation target

The two P1 allocation Tools deliberately use different totals:

| Tool | Target describes | Amount used in the calculation |
|---|---|---|
| **PAC Allocator** | How to distribute investable liquidity now | Existing cash + new contributions, valued in the reporting currency |
| **[Portfolio Rebalancer](../portfolio-rebalancer/index.md)** | The desired final mix of the currently invested portfolio | Current Asset value only; cash and contributions stay separate |

Changing holdings cannot change a PAC allocation because holdings are not part
of its calculation request. Conversely, a PAC percentage does not describe
your portfolio's current or final invested weight.

## 🚪 Open the Tool

Open **Tools** from the sidebar and choose the **PAC Allocator** card. Its Tool
code is `pac_allocator`, its route is `/tools/pac_allocator`, and its compiled
interface key is `pac-allocator`.

The PAC Allocator and Portfolio Rebalancer are separate catalogue entries and
separate interfaces, even though one packaged backend plugin serves both. The
PAC backend contract and implementation are version `1.0.0`; its independently
versioned UI is also `1.0.0`.

A new PAC draft starts with your account's base currency as the reporting
currency, today's local date as the analysis date, no selected Broker cash, no
contributions, and no Assets.

## 💶 Define the investable liquidity

The **Available funds** step keeps two native-currency vectors separate:

- **Existing cash** is money already available.
- **New contributions** are amounts you plan to add.

The backend values both vectors in the reporting currency with the explicit
rates in the draft, then adds the two reporting-currency totals. That sum is
the **investable budget**.

### 🏦 Copy existing cash or enter it manually

In **Broker reserves** mode, select any accessible OWNER Broker cards whose
cash should be included. LibreFolio asks the backend to aggregate the selected
native balances by currency and copies that aggregate into the calculation.
Each imported Broker balance is the **full, unscaled native reserve** for that
Broker and currency. `ownership_share_percent` is separate display metadata
only and does not multiply or scale the cash balance. The Broker card labels
the amount **Full native reserve** and shows the personal-share percentage
separately.

No Broker is selected by default, so the initial existing-cash vector is an
explicit empty list. Choose **Enter amounts** if you want a fully manual
scenario or no OWNER Broker is available. Broker-copy and manual cash are
alternative sources; they are not silently merged.

Existing cash allows **one row per currency**. Negative existing cash is
outside P1.

### ➕ Add one or more contributions

Choose **Add contribution** for each contribution event. Every row has:

- a native currency;
- a non-negative exact amount;
- a positive **monetary step** that must divide that amount exactly.

Several contribution rows may use the same currency. They remain visible as
separate inputs and are summed exactly by currency in the backend result.
Removing the last row restores the explicit empty contribution vector.

The contribution monetary step is metadata for that contribution. It is not
an Asset quantity step, and P1 does not use it to create an order.

## 🧺 Choose the Assets to fund

Select canonical Assets from the gallery or choose **New manual Asset**. A
manual draft needs no database Asset, saved quote, or existing position.

For PAC, selecting a catalog Asset copies its canonical identity and display
name into the draft. The gallery can show current quote and custody context as
source information, but neither prices nor holdings enter the PAC calculation.
For a selected source Asset, the card also shows the saved quote provider and
quote date when available. The calculation receives only the selected Asset
identities, their targets, and optional future purchase-grid metadata.

Each canonical Asset appears once in the PAC draft. Equal display names do not
establish identity, and manual Assets receive their own local identities.

For each Asset, **Future purchase constraints** can record:

- **Whole quantities** with a positive whole-number quantity step; or
- **Fractional quantities** with a positive decimal quantity step.

These fields describe a possible future purchase grid. P1 does not convert its
monetary allocation into quantities or round it to that grid.

## 📊 Set one exact target distribution

The **Liquidity distribution** DataTable has one row per selected canonical
Asset. Enter the target percentage in the table and use the colored
distribution bar to review the shape of the split.

Targets must each be between `0` and `100` and must total **exactly `100`**.
The interface computes the displayed total with exact decimal arithmetic, and
the backend validates the exact total again. A rounded-looking total is not
silently accepted.

## 💱 Value currencies explicitly

The valuation-rate section appears when active cash or contribution facts use
a currency different from the reporting currency. Enter one positive rate per
foreign currency:

> 1 native currency unit = the entered number of reporting-currency units

The reporting currency uses an identity rate of `1`. Other missing rates never
default to `1`, and duplicate valuation-rate rows for one currency are
invalid.

You can enter a rate and optional source date manually, or choose **Copy rate**
to copy the saved rate available for the analysis date. A copied value and its
actual source date are placed in ordinary editable fields, so you can review or
replace them before analysis. A missing date is reported for review; a source
date after the analysis date is invalid.

Rates are for valuation only. Native pools remain distinct, and LibreFolio
does not exchange or transfer cash.

## ▶️ Analyze the allocation

1. Confirm the reporting currency and analysis date.
2. Select OWNER Broker reserves or enter existing cash manually.
3. Add any contributions, including their monetary steps.
4. Select catalog Assets, add manual Assets, or mix both.
5. Enter one target per Asset and make the total exactly `100%`.
6. Resolve each displayed currency-rate requirement.
7. Choose **Analyze PAC allocation**.

The result presents human-readable diagnostics followed by:

- exact reporting-currency totals for existing cash, contributions, and the
  combined investable budget;
- a DataTable with each Asset's target percentage and exact theoretical
  monetary allocation;
- native cash pools that preserve the distinction between existing cash and
  contributions.

The allocation for each target is the exact investable budget multiplied by
that target percentage and divided by 100. Decimal strings remain
authoritative even when the interface shortens them for display.

## 🧭 Understand diagnostics

A successful Tool request can still report one of four domain states:

| State | Meaning |
|---|---|
| `ready` | Every dependency needed for this P1 calculation is available. Informational findings can still be present. |
| `needs_input` | A required value is missing, such as an Asset target or foreign-currency valuation rate. |
| `invalid` | A supplied value or relationship is inconsistent, such as a target total other than exactly `100`. |
| `unsupported` | The draft is understood but outside P1, such as negative existing cash or a value outside the supported exact numeric domain. |

The interface translates backend issue codes into friendly messages and keeps
technical details available in a disclosure. Platform failures such as a
timeout, unavailable Tool, or incompatible version are separate from these
financial-domain states.

## 🔄 Keep copied facts and results current

Changing the analysis date or refreshing the source can mark a selected
catalog Asset as **Outdated** rather than silently replacing a customized
draft. Copied Broker cash is not submitted while its source request is still
loading.

Source and calculation requests are guarded by request sequence, draft
revision, selected date, Broker selection, and signed-in account generation.
Late or superseded responses are ignored. After you edit an analyzed draft,
the displayed result receives an amber stale warning until you run it again.

Removing a source-linked Asset after changing its target or purchase-grid
settings opens an amber confirmation warning so that customization is not
discarded unnoticed.

## 🚫 P1 boundaries

PAC Allocator P1 has:

- no solver, optimization, or optimality claim;
- no operative quantities, purchases, sales, or orders;
- no Broker routing or native-cash feasibility check;
- no automatic FX transfer or execution;
- no tax recommendation;
- no short positions, leverage, or opening cash debt.

The P1 output schema cannot represent solver, optimization, optimality, or
operational-feasibility concepts; it does not emit `not_run` or
`not_evaluated` fields for them.

## 🔒 Protect private financial data

The optional source read is limited to catalog metadata plus your OWNER
custody and Broker-cash context. The calculation receives only the scenario
currently visible in the draft; it does not receive a live portfolio or
database handle and does not write back to Assets, Brokers, or transactions.

Avoid putting personal portfolio values, Broker exports, account identifiers,
or screenshots of real holdings into examples or support messages.

## 🔗 Related

- [Portfolio Rebalancer P1](../portfolio-rebalancer/index.md)
- [Tools overview](../index.md)
