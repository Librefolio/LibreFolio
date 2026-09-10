---
title: PAC allocator
description: Manually enter a periodic-investment scenario and inspect its exact initial allocation state.
---

# 🧮 PAC allocator

The **PAC allocator** is the implemented manual P1 pilot for a periodic
investment plan. You enter one complete scenario, and LibreFolio evaluates its
initial holdings, cash, target weights, and allocation gaps.

!!! warning "Initial-state analysis only"

    This pilot does not propose purchases, solve an allocation problem, route
    orders, or decide whether trades are feasible. A `ready` result means only
    that the initial state could be evaluated.

## 🎯 What the pilot calculates

For each asset and custody context, the backend analysis returns:

- the exact opening quantity;
- its value in the quote currency and report currency;
- its current weight among the invested rows;
- its target percentage and deviation in percentage points.

The current result table presents the reporting-currency value; the backend
contract also keeps the exact native-currency value as a separate fact.

It also reports the initial invested value, existing cash, new contributions,
cash plus contributions, the largest absolute allocation gap, and the sum of
squared gaps. Cash and contributions remain separate from the invested-value
denominator: the analyzer does not pretend that uninvested money is already
allocated.

All values come from the current form. You can edit them and run the analysis
again. The pilot does **not** read Asset, Broker, or Portfolio records, and it
does not call price, FX, or other data providers.

## ✍️ Enter a scenario

Use a dot (`.`) as the decimal separator, without thousands separators or
scientific notation. For example, enter `10.125`, not `10,125` or `1.0125e1`.
Blank and zero have different meanings: blank is missing input, while `0` is a
known exact zero.

| Input | Unit and meaning |
|---|---|
| **Reporting currency** | The three-letter currency used for reporting values and the invested-value denominator, for example `EUR`. |
| **As-of date** | Optional scenario date in `YYYY-MM-DD` form. A quote or valuation observation cannot be later than this date. No date is inferred from the clock. |
| **Asset and custody row** | Add one row for each asset × custody context. Two custody contexts for the same instrument remain two rows with separate targets and results. |
| **Opening quantity** | Exact, non-negative custody quantity. Short inventory is outside P1. |
| **Native price** | Positive price in the row's quote currency. It is the price for the selected quote base quantity. |
| **Quote base quantity** | Either `1` or `100`. Holding value is `opening quantity × native price ÷ quote base quantity`. |
| **Target** | Percentage from `0` to `100` for that row. All row targets must total exactly `100`. |
| **Purchase grid** | Choose **Whole quantities** or **Fractional quantities**, then enter a positive quantity step. A whole-quantity step must be an integer. This rule applies only to possible new purchases, not to opening inventory. |
| **Quote date** | Optional `YYYY-MM-DD` observation date for the native price. An omitted date is reported rather than silently replaced with today. |

The form assigns every row its own opaque row identity and maintains a canonical
instrument identity separately. Use **Same asset, another context** when two
rows represent the same underlying instrument: this preserves that instrument
identity across the custody contexts. The visible name is only a label; matching
names do not join rows or establish identity.

### 💶 Cash and contributions

Enter existing cash as one amount per currency. Enter new contributions in the
separate contribution list, also one amount per currency. The analyzer reports
both vectors separately and combines them only in the dedicated cash total.

Use **No existing cash** or **No new contributions** when the corresponding
vector is known to be empty. Leaving a vector as **Not supplied** does not mean
zero and produces `needs_input`. Duplicate currencies are invalid. Contributions
must be non-negative; an opening cash debt is outside the P1 domain.

### 💱 Valuation rates

Supply an explicit rate for every non-report currency used by a holding, cash
balance, or contribution:

> `1 native currency unit = rate_to_report report-currency units`

For example, `USD` with a rate of `0.9` in an `EUR` report means
`1 USD = 0.9 EUR`. The report currency has an identity rate of `1`.

Each rate can have an optional observation date. These rates value native
amounts for the report; they do not exchange, transfer, merge, or otherwise move
cash between currency pools.

## ▶️ Run and revise

1. Open **Tools**, then choose **PAC allocator**.
2. Enter every scenario value manually, including explicit empty cash or
   contribution vectors where appropriate.
3. Select **Check initial state**.
4. Review the domain state, backend findings, totals, row facts, and native cash
   pools.
5. After editing the draft, run the analysis again for the new revision.

The result contains facts about the supplied initial state only. The current
pilot performs no database writes, creates no transactions or orders, has no
broker routing, and runs no solver or optimization. Trade feasibility is
explicitly **not evaluated**.

## 🧭 Understand the result states

A successful Tool envelope can contain a PAC result that is not `ready`. The
four PAC domain states are:

| State | Meaning |
|---|---|
| `ready` | The initial state is evaluable within P1. Informational findings can still be present, and the current allocation does not have to match its targets. |
| `needs_input` | Required information is missing or incomplete, such as an unsupplied cash vector or a valuation rate for a foreign currency. |
| `invalid` | Supplied data is malformed or inconsistent, such as scientific decimal notation, duplicate currencies, an observation after the as-of date, or targets that do not total `100`. |
| `unsupported` | The input is understood but outside the P1 domain, such as quote base `3`, short inventory, opening cash debt, or a value beyond the supported numeric or currency bounds. |

Backend findings point to the affected field. Correct the draft and submit a new
revision; a non-ready state is still a valid analysis response, not a platform
failure.

Platform errors are separate. A queue or compatibility error, timeout, worker
failure, invalid output, transport failure, or stopped wait means that the
analysis did not deliver an accepted PAC result. In particular, a timeout is
**not** evidence that the scenario is infeasible. The interface preserves the
draft so you can review it or try again.

If you edit the draft while a request is running, that response is ignored
because it belongs to an older revision. A displayed result also becomes marked
as stale after a later edit. Re-run the analyzer rather than treating a stale
result as the answer to the current draft.

An invested value of exactly zero is a valid known total. However, weights,
deviations, and gap scores have no non-zero denominator, so they remain
unavailable. This does not mean “no trade needed” or “optimal.”

## 🔢 Exact and formatted views

Use **Exact** when reconciling a result. Financial decimals are authoritative
backend decimal strings, not browser floating-point numbers. Exact ratios are
returned with their numerator, denominator, and unit; percentage points (`pp`)
and squared percentage points (`pp²`) remain distinct.

Use **Formatted** for a shorter, easier-to-read presentation. It may shorten a
decimal or show the backend ratio approximation, but it does not replace or
change the exact result. The backend decimal strings and exact ratio
numerator/denominator remain authoritative in both cases. In a `ready` result,
**Normalized input and units** shows the canonical input returned by the
backend.

The purchase grid never rounds existing inventory. For example, an opening
quantity of `10.125` remains `10.125` even if that row uses a whole-quantity
purchase grid with step `1`; the backend reports an informational
`inventory_off_buy_grid` finding instead.

## 🧪 Synthetic manual example

Consider two custody contexts for the same synthetic instrument:

| Row | Opening quantity | Native quote | Target | Purchase grid |
|---|---:|---:|---:|---|
| `Alfa / X` | `10.125` | `10 EUR` per `1` unit | `50%` | Whole, step `1` |
| `Alfa / Y` | `0` | `10 EUR` per `1` unit | `50%` | Fractional, step `0.001` |

Use `EUR` as the report currency and `2026-09-08` as the as-of, quote, and rate
date. Enter existing cash of `0.005 EUR` and `10 USD`, a new contribution of
`5 EUR`, and the valuation rate `1 USD = 0.9 EUR`.

The analyzer reports:

- initial invested value: `101.25 EUR`;
- current weights: `100%` for `Alfa / X` and `0%` for `Alfa / Y`;
- target deviations: `+50 pp` and `-50 pp`;
- largest absolute gap: `50 pp`;
- sum of squared gaps: `5000 pp²`;
- existing cash value: `9.005 EUR`;
- new contributions: `5 EUR`;
- cash plus contributions: `14.005 EUR`.

The `10 USD` remains a native USD cash pool; `0.9` is used only to report its
value as `9 EUR`. The `10.125` opening quantity is retained exactly and receives
an off-grid information finding. No instruction is produced for spending the
`14.005 EUR`.

## 🔒 Privacy and safety

Treat names, quantities, prices, cash, and rates as financial data. The form
sends the scenario to your LibreFolio backend for this calculation, so use
synthetic labels when real names are unnecessary and protect any screenshots or
copied exact output.

The PAC calculation itself receives the submitted scenario, not access to your
Asset, Broker, or Portfolio records or data providers. It does not save the
draft back to those records. Its result is analysis, not investment advice or
authorization to trade.

## 🔗 Related

- [Tools overview](../index.md)
