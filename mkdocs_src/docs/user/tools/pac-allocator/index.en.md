---
title: PAC allocator
description: Build a periodic-investment scenario from catalog Assets, OWNER custody and cash facts, or manual inputs, then inspect its exact initial allocation state.
---

# 🧮 PAC allocator

The **PAC allocator** is the implemented P1 pilot for a periodic investment
plan. Build one scenario from LibreFolio's Asset catalog, your OWNER custody
and broker-cash facts, manual inputs, or a mix. LibreFolio then evaluates its
initial holdings, cash, target weights, and allocation gaps.

!!! warning "Initial-state analysis only"

    This pilot does not propose purchases or sales, solve an allocation
    problem, route or execute orders, or decide whether trades are feasible.
    A `ready` result means only that the initial state could be evaluated.

## 🚪 Open the pilot

Open **Tools** from the sidebar and select the **PAC allocator** card (the
whole card opens it). See [Tools overview](../index.md) for the shared
Documentation/Refresh/Version controls in the tool header.

A freshly opened draft starts with:

- **Reporting currency** set to your account's base currency;
- **As-of date** set to today's date, in your device's local time zone —
  never inferred later or silently advanced;
- **Existing cash** and **New contributions** both set to **Not supplied**;
- **zero Asset rows** — nothing is selected until you choose a catalog card
  or add a manual Asset.

## 🗂️ Asset catalog and source scopes

The Asset gallery is a read-only source assembled from the backend-owned
global catalog for your authenticated account and selected as-of date. It is
**not limited to your current holdings**: it contains every active Asset, plus
an inactive Asset when you still have non-zero custody through an OWNER
Broker.

The three filters classify recorded use:

| Scope | Meaning |
|---|---|
| **Owned** | The Asset has recorded transaction use in at least one of your positive-share OWNER Brokers. This filter is on by default. |
| **Other users** | The Asset has recorded transaction use, but none in one of your positive-share OWNER Brokers. Only this scope classification is exposed — not another user's identity, Broker, transactions, quantity, or cash. |
| **Observed** | The Asset exists in the catalog but has no recorded transaction use. |

These are usage scopes, not promises about today's quantity. Toggle any
combination of scopes to broaden or narrow the gallery. Active cards appear
before inactive cards; an inactive card is included only while a current
OWNER custody context requires it. The counts beside the filters count Asset
cards, not transactions or users.

- Assets are grouped **canonically**: one card per Asset, even when you hold
  it through several Brokers.
- When a card has current custody, selecting it copies **every non-zero OWNER
  custody context** at once — one row per Broker context — subject to the
  32-row cap. A 0% OWNER economic share does not hide that context: the
  imported quantity is always the **full custody quantity**, while the share
  remains informational metadata.
- When a card has no current custody contexts, selecting it creates one
  zero-position catalog row with no invented Broker. Selecting **Other users**
  never copies another user's holdings.
- The quote is the **latest saved native quote at or before the as-of date**.
  A missing saved quote stays missing and is never treated as zero or fetched
  live.
- Imported rows show their available Broker, snapshot, quote-date, and source
  metadata. **Modified** marks changed target/grid inputs; **Outdated** marks
  a source snapshot that no longer matches the current source.
- Search matches the Asset name. **Refresh** reloads source facts for the
  current as-of date; **New manual asset** bypasses the source entirely.

## ✍️ Add and edit rows

Use **New manual asset** to add a blank, source-free row. Its visible scenario
facts are editable. A row imported from the catalog is deliberately split:
its source identity, name, opening custody, and saved quote facts are locked,
while its **Target** and **Purchase grid** remain editable.

Canonical Asset, instrument, context, and row identifiers stay hidden in the
interface. They keep Broker contexts distinct behind the scenes; equal display
names do not merge rows or establish identity.

Numeric controls preserve values as **exact decimal strings**, rather than
converting them through browser floating-point numbers. You can type either
`10.125` or `10,125`; recognized locale grouping is normalized to the
canonical dot-decimal form when you leave the field or press **Enter**.
Scientific notation is not accepted. Blank and zero have different meanings:
blank is missing input, while `0` is a known exact zero.

| Field | Unit and meaning |
|---|---|
| **Name** | Editable display label on a manual row; locked to the catalog name on an imported row. Names are not identity keys. |
| **Initial quantity** | Exact opening quantity. An imported custody row uses the full Broker custody quantity, not your economic share; a zero-position catalog row starts at `0`. Short inventory is outside P1. |
| **Currency** / **Native price** | The native quote currency and positive saved or manual price. Imported values are locked; manual values are editable. |
| **Quote base quantity** | Any positive integer number of units represented by the native price. Holding value is `initial quantity × native price ÷ quote base quantity`. |
| **Quote date** | Optional observation date for the native price. A missing date is reported rather than silently replaced with today. |
| **Target (%)** | Percentage from `0` to `100` for that row. All row targets must total exactly `100`. |
| **Purchase grid** | Choose **Whole quantities** or **Fractional quantities**, then a positive quantity step. Whole mode requires an integer step. This governs only possible new purchases, never opening inventory. |

If an imported row has a missing quote, or you need to replace another locked
source fact for the scenario, choose **Duplicate** to create an independent
manual copy, edit that copy, and remove the source-linked row if it is no
longer wanted.

### ➕ Add, duplicate, remove, and clear

- **New manual asset** always appends one blank row with a new local identity.
  Gallery selection is deduplicated by canonical asset: while any linked row
  remains, selecting its card again means **deselect**, not "add another
  copy." Use **Duplicate** when you intentionally need another row.
- **Duplicate** copies the scenario values into a row with a fresh row key,
  retains the hidden instrument key, removes the portfolio/catalog source
  link, and makes the visible source facts editable. This independent manual
  copy does not participate in copied-facts refresh or keep its source card
  selected.
- **Remove** deletes a single row immediately, unless that row was copied
  from the catalog **and** you have edited any of its fields — in that case,
  a confirmation dialog identifies the affected row before removing it.
- Deselecting an Asset card removes every row still linked to that card.
  Independent manual duplicates remain. If a linked row was edited, a
  confirmation dialog lists it first.
- Clearing an optional quote/rate date or an exact decimal field leaves it
  missing; it does not turn it into today or zero. There is no separate
  "clear draft" action. To start over, use **Refresh** in the open tool's
  header and confirm the reset; this recreates the default empty draft.
- The draft holds at most **32 rows**. Adding a manual row or duplicating
  one stops with a warning once the draft is full. Adding an asset from the
  gallery is **all-or-nothing**: if its custody contexts would not all fit
  under the 32-row cap, nothing is copied and a warning explains why.

## 💶 Funding first: cash and contributions

Available funds appear before Asset selection. Existing cash and new
contributions are separate vectors: the analyzer reports them separately and
combines them only in the dedicated **Cash + contributions** total.

Existing cash has four modes:

| Cash mode | Request meaning |
|---|---|
| **Not supplied** | Sends `null`: existing cash is unknown, not zero, and can produce `needs_input`. |
| **No existing cash** | Sends an empty vector (`[]`): existing cash is known to be zero. |
| **From brokers** | Select OWNER Brokers. The backend calculates their full-custody native balances at the as-of date and returns the selected total per currency; no selection produces a known empty vector. |
| **Manual** | Sends the entered currency/amount rows. |

In **From brokers**, ownership share is informational: balances are not
share-scaled. The selected aggregate is calculated by the backend and copied
unchanged into the PAC request. The frontend performs no Broker-balance sum
and no currency conversion. If no OWNER Broker is available, or the source
read fails, switch to **Manual** and enter the scenario cash directly.

Contributions use their own three modes: **Not supplied** (`null`), **No new
contributions** (`[]`), and **Enter amounts**. Every entered contribution has
a currency, a non-negative amount, and a separate positive **Monetary step**;
the amount must be an exact multiple of that step. Existing cash has no
`monetary_step` field.

Switching modes keeps draft rows available if you switch back, but inactive
rows are not sent. Duplicate currencies are invalid, and opening cash debt is
outside P1.

## 💱 Valuation rates

Supply an explicit rate for every non-report currency used by a holding,
cash balance, or contribution:

> `1 native currency unit = rate_to_report report-currency units`

For example, `USD` with a rate of `0.9` in an `EUR` report means
`1 USD = 0.9 EUR`. The report currency has an identity rate of `1`.

For row \(i\), let \(q_i\) be its opening quantity, \(p_i\) its native price,
\(b_i\) its positive-integer quote base, \(c_i\) its native currency, \(R\)
the report currency, and \(r_{c_i\to R}\) the explicit valuation rate:

$$
V_{i,R} =
\begin{cases}
\dfrac{q_i p_i}{b_i}, & c_i = R \\
\dfrac{q_i p_i}{b_i}\,r_{c_i\to R}, & c_i \ne R
\end{cases}
$$

Cash and contribution amounts use the same conditional rule: keep the native
amount when its currency is \(R\); otherwise multiply it by the supplied
`rate_to_report`.

Each rate can have an optional observation date. Foreign currencies produce a
hint, but rates are never fetched or filled automatically: enable manual rates
and add each one explicitly. These rates value native amounts for the report.
Native cash pools stay separate by currency: the tool does not exchange,
transfer, merge, spend, or execute them, and it provides no automatic FX
funding.

## 🔄 Keeping copied facts current

Changing the **as-of date** re-fetches source facts for that date and marks
linked rows and Broker-copied cash stale. Refreshing can also discover changed
facts for the same date. Neither action silently overwrites selected Asset
rows: source facts are copied when you select an Asset, reselect it after
removal, or choose **Refresh copied facts**.

When copied rows are outdated, a **Refresh copied facts** action appears.
It replaces only the locked identity, custody, and quote facts with the fresh
snapshot; your **target percentage and purchase grid are always preserved**.
If a custody context no longer exists, its row is retained and stays marked
**Outdated**. Selecting or reselecting an Asset always uses the accepted
current snapshot.

Broker-copied cash has a stricter guard: while its source is loading, failed,
or stale for the current date/selection, **Check initial state** is disabled
and the previous aggregate is not submitted. Retry the source read or switch
to **Manual**.

Source requests are tied to their date, Broker selection, request sequence,
and signed-in account generation. Late or superseded responses are ignored;
an account change stops the old account's request.

## ▶️ Run and revise

1. Open **Tools**, choose **PAC allocator**, then confirm the reporting
   currency and as-of date.
2. Define existing cash first: leave it unknown, declare none, copy selected
   OWNER Brokers, or enter it manually. Define new contributions separately,
   including each contribution's monetary step.
3. Select catalog Assets from the needed usage scopes, add manual rows, or
   use both. Set every row's target and purchase grid.
4. Add an explicit valuation rate for every non-report currency.
5. Select **Check initial state**.
6. Review the domain state, findings, four totals, row values and gaps, and
   native cash pools. After any edit, run the analysis again.

The result contains facts about the supplied initial state only. The browser
prepares the draft and presents the response. The backend performs the
normalize → evaluate → report pipeline: validation, valuation, weights, gaps,
totals, findings, and normalized values. It also owns the selected Broker-cash
aggregate; the browser does not recompute it.

Read the totals separately. **Initial invested** is the sum of reporting-value
Asset rows and is the only denominator for current weights and target gaps.
**Existing cash**, **Contributions**, and **Cash + contributions** are reported
beside it but do not enter that denominator. Adding cash or a contribution
therefore does not change P1 Asset weights or allocate that money.

## 🚫 Outside P1

P1 only normalizes, evaluates, and reports the initial state. Its output says
`optimization = "not_run"` and `trade_feasibility = "not_evaluated"`.

The pilot has no solver, order or recommendation generation, purchase or sale
plan, order execution, Broker routing, or implicit FX. It does not support
short inventory, leverage/opening debt, or automatic funding transfers. It
does not invoke or change FIFO, WAC, tax, or Riskfolio analytics. Quantity and
monetary steps are validated input facts — including contribution-step
alignment — but P1 does not use them to recommend an amount or quantity.

## 🧭 Understand the result states

A successful Tool envelope can contain a PAC result that is not `ready`. The
four PAC domain states are:

| State | Meaning |
|---|---|
| `ready` | The initial state is evaluable within P1. Informational findings can still be present, and the current allocation does not have to match its targets. |
| `needs_input` | Required information is missing or incomplete, such as an unsupplied cash vector or a valuation rate for a foreign currency. |
| `invalid` | Supplied data is malformed or inconsistent, such as scientific decimal notation, duplicate currencies, an observation after the as-of date, or targets that do not total `100`. |
| `unsupported` | The input is understood but outside the P1 domain, such as short inventory, opening cash debt, or a value beyond the supported numeric or currency bounds. |

Backend findings point to the affected field. Correct the draft and submit a
new revision; a non-ready state is still a valid analysis response, not a
platform failure.

Platform errors are separate. A queue or compatibility error, timeout,
worker failure, invalid output, transport failure, or stopped wait means
that the analysis did not deliver an accepted PAC result. In particular, a
timeout is **not** evidence that the scenario is infeasible. The interface
preserves the draft so you can review it or try again.

If you edit the draft while a request is running, that response is ignored
because it belongs to an older revision. The same protection rejects a
response after the Tool descriptor becomes incompatible or the signed-in
account changes; sign-out or account switching also stops account-bound
requests. A displayed result becomes marked as stale after a later edit.
Re-run the analyzer rather than treating a stale result as the answer to the
current draft.

An invested value of exactly zero is a valid known total. However, weights,
deviations, and gap scores have no non-zero denominator, so they remain
unavailable. This does not mean "no trade needed" or "optimal."

## 🔢 Exact and formatted views

Use **Formatted** (the default) for a shorter, easier-to-read presentation. It
may shorten a decimal or show the backend ratio approximation, but it does not
replace or change the exact result, run any solver, or certify feasibility
— it only changes how the same backend-computed facts are displayed. The
backend decimal strings remain authoritative.

Use **Exact** when reconciling a result. Exact ratios show their backend
numerator and denominator; percentage points (`pp`) and squared percentage
points (`pp²`) remain distinct. In a `ready` result, **Normalized input and
units** shows the canonical input returned by the backend.

The purchase grid never rounds existing inventory. For example, an opening
quantity of `10.125` remains `10.125` even if that row uses a whole-quantity
purchase grid with step `1`; the backend reports an informational
`inventory_off_buy_grid` finding instead.

## 🧪 Synthetic manual example

Consider two custody contexts for the same synthetic instrument, entered
manually:

| Row | Opening quantity | Native quote | Target | Purchase grid |
|---|---:|---:|---:|---|
| `Alfa / X` | `10.125` | `10 EUR` per `1` unit | `50%` | Whole, step `1` |
| `Alfa / Y` | `0` | `10 EUR` per `1` unit | `50%` | Fractional, step `0.001` |

Use `EUR` as the report currency and `2026-09-08` as the as-of, quote, and
rate date. Enter existing cash of `0.005 EUR` and `10 USD`, a new
contribution of `5 EUR` with monetary step `0.01 EUR`, and the valuation rate
`1 USD = 0.9 EUR`.

The analyzer reports:

- initial invested value: `101.25 EUR`;
- current weights: `100%` for `Alfa / X` and `0%` for `Alfa / Y`;
- target deviations: `+50 pp` and `-50 pp`;
- largest absolute gap: `50 pp`;
- sum of squared gaps: `5000 pp²`;
- existing cash value: `9.005 EUR`;
- new contributions: `5 EUR`;
- cash plus contributions: `14.005 EUR`.

The `10 USD` remains a native USD cash pool; `0.9` is used only to report
its value as `9 EUR`. The `10.125` opening quantity is retained exactly and
receives an off-grid information finding. No instruction is produced for
spending the `14.005 EUR`.

## 🔒 Privacy and safety

Treat names, quantities, prices, cash, and rates as financial data. Keep two
read boundaries apart:

- The **allocation source** reads global Asset metadata and saved quotes, then
  adds only your OWNER custody contexts and OWNER Broker native-cash facts.
  The **Other users** scope exposes only shared catalog metadata plus a usage
  class; it does not expose another user's identity, Broker, transaction
  details, position, or cash. The source is read-only and never writes back to
  Asset, Broker, or Transaction records.
- The **PAC calculation** receives only scenario values present in the draft
  — copied or typed — never a live link to Asset, Broker, Portfolio, FIFO,
  WAC, tax, or Riskfolio data. It does not call price, FX, or other providers.

Use synthetic labels for manual rows when real names are unnecessary, and
protect any screenshots or copied exact output. The result is analysis, not
investment advice or authorization to trade.

## 🔗 Related

- [Tools overview](../index.md)
