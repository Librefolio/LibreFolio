---
title: Portfolio Rebalancer P1
description: Compare the current invested value of canonical Assets with a desired final allocation, without creating trades.
---

# ⚖️ Portfolio Rebalancer P1

The **Portfolio Rebalancer** answers one question:

> How far is my currently invested portfolio from a desired final allocation?

It values the selected holdings, aggregates custody contexts that share the
same canonical Asset identity, and compares each Asset's current value with
its target value. The result shows current value, current weight, target
value, and a signed value gap.

Cash and planned contributions are useful context, but they do not enlarge the
portfolio denominator. If your question is instead “How should my available
liquidity be split for this contribution cycle?”, use
[PAC Allocator P1](../pac-allocator/index.md).

!!! warning "A gap is not a trade"

    Positive and negative gaps describe the difference between target value
    and current value. They are not buy or sell instructions, quantities,
    orders, or proof that a trade is feasible.

## 🎯 Choose the right allocation target

The two P1 allocation Tools deliberately use different totals:

| Tool | Target describes | Amount used in the calculation |
|---|---|---|
| **[PAC Allocator](../pac-allocator/index.md)** | How to distribute investable liquidity now | Existing cash + new contributions, valued in the reporting currency |
| **Portfolio Rebalancer** | The desired final mix of the currently invested portfolio | Current Asset value only; cash and contributions stay separate |

Adding cash or a contribution cannot change the Rebalancer's current weights
or target values. It only changes the separately reported liquidity context.

## 🚪 Open the Tool

Open **Tools** from the sidebar and choose the **Portfolio Rebalancer** card.
Its Tool code is `portfolio_rebalancer`, its route is
`/tools/portfolio_rebalancer`, and its compiled interface key is
`portfolio-rebalancer`.

The Rebalancer and PAC Allocator are separate catalogue entries and separate
interfaces, even though one packaged backend plugin serves both. The
Rebalancer backend contract and implementation are version `1.0.0`; its
independently versioned UI is also `1.0.0`.

A new Rebalancer draft starts with your account's base currency as the
reporting currency, today's local date as the analysis date, no holdings, no
selected Broker cash, and no contributions.

## 🧺 Build the invested portfolio

Use the Asset gallery to choose canonical Assets from the current source, or
choose **New manual Asset** to work without any database Asset.

Selecting a source Asset copies all of its non-zero OWNER custody contexts
that fit in the 32-row limit. Each context remains visible as a separate
holding with its Broker context, quantity, native quote, quote basis, and
quote date.

Imported quantities are the **full custody quantities** for their Broker
contexts. `ownership_share_percent` is separate display metadata only and does
not multiply or scale a holding quantity.

Behind the interface, every copied context carries:

- a unique custody-row key, so two Broker contexts remain distinct; and
- the canonical `instrument_key`, so contexts for the same Asset are combined
  for the target comparison.

This means one Asset held through two Brokers still has **one target row** and
one aggregated result row. Display names never decide whether holdings belong
together.

When an Asset has no current custody context, selecting it creates a
zero-quantity candidate without inventing a Broker. Use a manual holding to
enter a source-free name, quantity, native price, quote basis, currency, and
optional quote date.

Source-linked quantity and quote facts are copied into the draft rather than
kept as a live portfolio query. The source-linked card shows the copied
values and dates. It labels the amount **Full custody quantity**, shows the
personal-share percentage separately, and displays the **Portfolio snapshot**
date plus the quote provider and quote date when available. Choose
**Duplicate** to copy those facts into a second, independent manual holding;
there you can edit the quantity, currency, price, quote basis, or quote date.
The duplicate no longer follows the catalog or Broker source.

### 🧩 Record future purchase-grid metadata

Every holding can carry optional future purchase constraints:

- **Whole quantities** with a positive whole-number quantity step; or
- **Fractional quantities** with a positive decimal quantity step.

The grid applies only to possible future purchases. Existing custody is kept
exactly as supplied, even when it does not fit the grid, and P1 never turns the
grid into an order quantity.

## 📊 Set the final target

The **Final target allocation** DataTable contains one row per canonical
Asset, not one row per Broker custody. Enter a percentage for each Asset and
use the colored distribution bar to inspect the final mix.

Targets must each be between `0` and `100` and must total **exactly `100`**.
The interface computes the displayed total with exact decimal arithmetic, and
the backend validates it again.

After a successful analysis, **Use current distribution** can copy the
reported current weights into the target fields. The copied percentages stay
editable, and the final row is adjusted exactly so that the displayed total
closes at `100%`.

## 🧮 Understand the invested denominator

For each holding, LibreFolio calculates its native value from exact quantity,
native price, and quote basis, then values it in the reporting currency with
the draft's explicit rate.

The **current invested value** is the sum of those reporting-currency holding
values. It is the only denominator used for current weights and target values:

- current weight = aggregated current Asset value divided by current invested
  value;
- target value = current invested value multiplied by the target percentage
  and divided by 100;
- signed value gap = target value minus aggregated current Asset value.

A positive gap means the current value is below the target value; a negative
gap means it is above. Neither sign tells you to trade.

When current invested value is exactly zero, that zero remains a known value,
but weights and gap ratios have no non-zero denominator and remain
unavailable.

## 💶 Add optional liquidity context

Open **Optional liquidity context** when you also want the result to show
existing cash and planned contributions. These controls are shared with PAC
Allocator:

- Select accessible OWNER Broker cards to copy the backend's aggregate native
  cash by currency, or choose **Enter amounts** for a fully manual cash
  vector.
- Add zero or more contribution rows, each with its own non-negative exact
  amount and positive monetary step.
- Use explicit valuation rates for currencies that differ from the reporting
  currency.

Every imported Broker balance is a **full, unscaled native reserve**.
`ownership_share_percent` remains separate display metadata and does not
multiply or scale the cash. The Broker card labels the balance **Full native
reserve** and shows the personal-share percentage separately.

Several contribution rows may use the same currency. The backend sums them
exactly by currency while preserving them as distinct normalized inputs.
Existing cash and valuation rates instead allow only **one row per currency**.

The Rebalancer reports existing cash, contributions, and their combined
reporting value separately. It does not add them to current invested value,
change target values because of them, or infer executable trades from them.

## 💱 Review rates and source dates

Enter one positive valuation rate per foreign currency:

> 1 native currency unit = the entered number of reporting-currency units

The reporting currency uses an identity rate of `1`; another missing rate is
never assumed to be `1`. Rates value holdings and liquidity for comparison
only. They do not exchange or transfer native cash.

Choose **Copy rate** to copy a saved rate for the analysis date. LibreFolio
places the value and the actual source date—including an earlier
backward-filled date—into ordinary editable fields. You may replace either
before analysis. Missing source dates produce reviewable information;
observations after the analysis date are invalid.

Source-linked holdings retain their copied quote dates. Changing the analysis
date or refreshing the source can mark a customized holding **Outdated**
instead of silently replacing its draft values.

## ▶️ Analyze target gaps

1. Confirm the reporting currency and analysis date.
2. Select source Assets, add manual holdings, or use both.
3. Review each custody quantity, quote, source date, and future purchase grid.
4. Set one final target per canonical Asset and make the total exactly `100%`.
5. Optionally add cash and contributions as separate context.
6. Resolve every displayed foreign-currency rate requirement.
7. Choose **Analyze target gaps**.

The result first presents human-readable diagnostics, then:

- the total current invested value;
- cash plus contributions as a separate context total;
- a result DataTable with custody count, current value, current weight, target
  percentage, target value, and signed value gap for each canonical Asset.

The backend also returns each individual holding's current native and
reporting value. The main table intentionally summarizes by canonical Asset
so that the target comparison is not split by Broker.

## 🧭 Understand diagnostics

A successful Tool request can still report one of four domain states:

| State | Meaning |
|---|---|
| `ready` | Every dependency needed for this P1 comparison is available. Informational findings can still be present. |
| `needs_input` | A required fact is missing, such as a holding quote, target, or foreign-currency valuation rate. |
| `invalid` | A supplied value or relationship is inconsistent, such as duplicate cash currencies or targets that do not total exactly `100`. |
| `unsupported` | The draft is understood but outside P1, such as short inventory, negative existing cash, or a value outside the supported exact numeric domain. |

The interface turns backend issue codes into friendly messages and keeps
technical details available in a disclosure. Missing dates, stale copied
source facts, and stale calculation results remain visible rather than being
silently replaced or treated as current.

Platform failures such as a timeout, unavailable Tool, or incompatible
version are separate from these financial-domain states.

## 🔄 Keep the draft safe

Source requests are tied to the requested date, Broker selection, request
sequence, and signed-in account generation. Calculation responses are also
tied to the submitted draft revision. Late, superseded, or wrong-account
responses are ignored.

After you edit an analyzed draft, the result receives an amber stale warning
until you run the analysis again. Removing a source-linked Asset after
customizing one of its custody rows or its target opens an amber confirmation
warning before those settings are discarded.

## 🚫 P1 boundaries

Portfolio Rebalancer P1 has:

- no solver, optimization, or optimality claim;
- no operative quantities, purchases, sales, or orders;
- no Broker routing or native-cash feasibility check;
- no automatic FX transfer or execution;
- no tax recommendation;
- no short positions, leverage, or opening cash debt.

The P1 output schema cannot represent solver, optimization, optimality, or
operational-feasibility concepts; it does not emit `not_run` or
`not_evaluated` fields for them. A target gap is descriptive only.

## 🔒 Protect private financial data

The optional source read uses catalog metadata plus your OWNER custody and
Broker-cash context. The calculation receives only the scenario currently
visible in the draft; it does not receive a live portfolio or database handle
and does not write back to Assets, Brokers, or transactions.

Avoid putting personal portfolio values, Broker exports, account identifiers,
or screenshots of real holdings into examples or support messages.

## 🔗 Related

- [PAC Allocator P1](../pac-allocator/index.md)
- [Tools overview](../index.md)
