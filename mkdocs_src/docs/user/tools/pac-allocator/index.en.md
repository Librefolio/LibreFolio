---
title: PAC allocator
description: Build a periodic-investment scenario from your own assets, manual rows, or both, and inspect its exact initial allocation state.
---

# 🧮 PAC allocator

The **PAC allocator** is the implemented P1 pilot for a periodic investment
plan. Build one scenario — from your own owned assets, from manual rows, or a
mix of both — and LibreFolio evaluates its initial holdings, cash, target
weights, and allocation gaps.

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
- **zero rows** — nothing is pre-selected from your portfolio until you
  choose it.

## 🗂️ Your assets

The **Your assets** gallery lists each non-zero position held through a broker
where your access role is **OWNER**, read from your authenticated Portfolio
for the selected as-of date. It never writes anything back and never calls a
price, FX, or other data provider itself.

- Assets are grouped **canonically**: one card per underlying instrument,
  even if you hold it through several brokers.
- Selecting a card copies **every non-zero OWNER custody context** for that
  asset into the draft at once — one row per broker context — subject to the
  32-row cap below. Selecting it again deselects it and removes all of those
  rows instead of adding duplicates.
- A non-zero custody context with a **0% OWNER share** still appears and is
  still copyable. The copied quantity is always the **full custody quantity**
  held under that broker — it is never scaled down to your personal share.
  The ownership share is shown only as descriptive metadata next to the row.
- The card's price is the **latest saved native quote at or before the
  as-of date**. If no saved price exists on or before that date, the price
  is retained as missing (a "Price missing" badge) — it is never assumed to
  be zero or fetched live.
- Each copied row keeps its source metadata: the broker name, the portfolio
  snapshot date, and the quote's reference date and source plugin, when
  known. **Modified** and **Outdated** badges distinguish local edits from
  source facts that have changed.
- Use the search box to filter cards by asset name, ticker, asset type, or
  broker name. **Refresh** reloads the gallery for the current as-of date;
  **New manual asset** adds a blank manual row without using the gallery.

## ✍️ Add and edit rows

Besides picking assets from the gallery, use **New manual asset** to add a
blank row and fill it in yourself. Every row — copied or manual — uses the
same editable fields and LibreFolio's native searchable currency selector,
calendar date picker, and standard dropdown controls.

Numeric controls preserve values as **exact decimal strings**, rather than
converting them through browser floating-point numbers. You can type either
`10.125` or `10,125`; recognized locale grouping is normalized to the
canonical dot-decimal form when you leave the field or press **Enter**.
Scientific notation is not accepted. Blank and zero have different meanings:
blank is missing input, while `0` is a known exact zero.

| Field | Unit and meaning |
|---|---|
| **Instrument ID** / **Name** | Identity and display label. Copied rows prefill both; equal labels never join rows or establish identity by themselves. |
| **Custody context** | The row's opaque identity key. Two contexts for the same instrument remain two rows with separate targets and results. |
| **Initial quantity** | Exact custody quantity. For a copied row, this is the full custody quantity, not your personal share. Short inventory is outside P1. |
| **Currency** / **Native price** | The row's native quote currency and positive price for the selected quote base quantity. |
| **Quote base quantity** | Either `1` or `100`. Holding value is `initial quantity × native price ÷ quote base quantity`. |
| **Quote date** | Optional observation date for the native price. A cleared or omitted date is reported rather than silently replaced with today. |
| **Target (%)** | Percentage from `0` to `100` for that row. All row targets must total exactly `100`. |
| **Purchase grid** | Choose **Whole quantities** or **Fractional quantities**, then a positive quantity step (an integer for whole quantities). This governs only possible new purchases, never opening inventory. |

### ➕ Add, duplicate, remove, and clear

- **New manual asset** always appends one blank row with a new local identity.
  Gallery selection is deduplicated by canonical asset: while any linked row
  remains, selecting its card again means **deselect**, not "add another
  copy." Use **Duplicate** when you intentionally need another row.
- **Duplicate** clones every editable payload field — instrument identity,
  name, custody quantity, native quote, target, and purchase grid — but gives
  the copy a fresh row key. A duplicate of a copied row keeps that row's
  source link, so it still participates in staleness tracking and
  copied-facts refresh.
- **Remove** deletes a single row immediately, unless that row was copied
  from your assets **and** you have edited any of its fields — in that case,
  a confirmation dialog identifies the affected row before removing it.
- Deselecting an asset card removes **every** row copied from it, including
  any duplicates of those rows. If any of them were edited, a confirmation
  dialog lists the edited rows first.
- Clearing an optional quote/rate date or an exact decimal field leaves it
  missing; it does not turn it into today or zero. There is no separate
  "clear draft" action. To start over, use **Refresh** in the open tool's
  header and confirm the reset; this recreates the default empty draft.
- The draft holds at most **32 rows**. Adding a manual row or duplicating
  one stops with a warning once the draft is full. Adding an asset from the
  gallery is **all-or-nothing**: if its custody contexts would not all fit
  under the 32-row cap, nothing is copied and a warning explains why.

## 💶 Cash and contributions

Enter existing cash as one amount per currency. Enter new contributions in
the separate contribution list, also one amount per currency. The analyzer
reports both vectors separately and combines them only in the dedicated
cash total.

Each section has three distinct modes:

| Choice | Request meaning |
|---|---|
| **Not supplied** | Sends `null`: the vector is unknown, not zero, and is reported as missing (`needs_input` when it is the only blocking condition). |
| **Explicitly no existing cash / new contributions** | Sends an empty vector (`[]`): the known amount is zero. |
| **Enter amounts** | Sends the entered currency/amount rows. |

Switching away from **Enter amounts** keeps those draft rows available if you
switch back, but inactive rows are not sent. Duplicate currencies are invalid.
Contributions must be non-negative; an opening cash debt is outside the P1
domain.

## 💱 Valuation rates

Supply an explicit rate for every non-report currency used by a holding,
cash balance, or contribution:

> `1 native currency unit = rate_to_report report-currency units`

For example, `USD` with a rate of `0.9` in an `EUR` report means
`1 USD = 0.9 EUR`. The report currency has an identity rate of `1`.

Each rate can have an optional observation date. Foreign currencies produce a
hint, but rates are never fetched or filled automatically: enable manual rates
and add each one explicitly. These rates value native amounts for the report;
they do not exchange, transfer, merge, or otherwise move cash between currency
pools — there is no automatic FX funding.

## 🔄 Keeping copied facts current

Changing the **as-of date** re-fetches the gallery for that date and marks any
copied row whose source no longer matches as referring to another snapshot.
Refreshing the gallery can also discover changed facts for the same date.
Neither action overwrites the draft: source facts are copied only when you
select an asset, reselect it after removal, or choose **Refresh copied facts**.

When copied rows are outdated, a **Refresh copied facts** action appears.
It replaces only the copied identity, custody, and quote fields with the
fresh snapshot; your **target percentage and purchase grid are always
preserved**. If you had edited one of those copied fields yourself, refresh
asks you to confirm overwriting your edits first, listing every affected
row and field. If a custody context no longer exists in the refreshed source,
its editable row is retained and stays marked **Outdated**. Selecting or
reselecting an asset from the gallery always uses the current snapshot.

## ▶️ Run and revise

1. Open **Tools**, then choose **PAC allocator**.
2. Pick assets from **Your assets**, add manual rows, or both, then fill in
   any remaining fields, including explicit empty cash or contribution
   vectors where appropriate.
3. Select **Check initial state**.
4. Review the domain state, backend findings, totals, row facts, and native
   cash pools.
5. After editing the draft, run the analysis again for the new revision.

The result contains facts about the supplied initial state only. The pilot
performs no database writes, creates no transactions or orders, has no
broker routing, and runs no solver or optimization. Trade feasibility is
explicitly **not evaluated**.

The browser prepares and submits the exact draft. Validation, valuation,
weights, gaps, totals, findings, and normalized values are calculated by the
backend.

## 🚫 Outside P1

The current pilot has no optimization or historical optimizer, trade proposal,
purchase or sale plan, order execution, or broker routing. It does not support
short inventory, leverage/opening debt, or automatic FX funding. The purchase
grid is an input fact for possible future purchase logic; P1 does not use it to
recommend a quantity.

## 🧭 Understand the result states

A successful Tool envelope can contain a PAC result that is not `ready`. The
four PAC domain states are:

| State | Meaning |
|---|---|
| `ready` | The initial state is evaluable within P1. Informational findings can still be present, and the current allocation does not have to match its targets. |
| `needs_input` | Required information is missing or incomplete, such as an unsupplied cash vector or a valuation rate for a foreign currency. |
| `invalid` | Supplied data is malformed or inconsistent, such as scientific decimal notation, duplicate currencies, an observation after the as-of date, or targets that do not total `100`. |
| `unsupported` | The input is understood but outside the P1 domain, such as quote base `3`, short inventory, opening cash debt, or a value beyond the supported numeric or currency bounds. |

Backend findings point to the affected field. Correct the draft and submit a
new revision; a non-ready state is still a valid analysis response, not a
platform failure.

Platform errors are separate. A queue or compatibility error, timeout,
worker failure, invalid output, transport failure, or stopped wait means
that the analysis did not deliver an accepted PAC result. In particular, a
timeout is **not** evidence that the scenario is infeasible. The interface
preserves the draft so you can review it or try again.

If you edit the draft while a request is running, that response is ignored
because it belongs to an older revision. A displayed result also becomes
marked as stale after a later edit. Re-run the analyzer rather than
treating a stale result as the answer to the current draft.

An invested value of exactly zero is a valid known total. However, weights,
deviations, and gap scores have no non-zero denominator, so they remain
unavailable. This does not mean "no trade needed" or "optimal."

## 🔢 Exact and formatted views

Use **Exact** (the default) when reconciling a result. Financial decimals
are authoritative backend decimal strings, not browser floating-point
numbers. Exact ratios are returned with their numerator, denominator, and
unit; percentage points (`pp`) and squared percentage points (`pp²`) remain
distinct.

Use **Formatted** for a shorter, easier-to-read presentation. It may
shorten a decimal or show the backend ratio approximation, but it does not
replace or change the exact result, run any solver, or certify feasibility
— it only changes how the same backend-computed facts are displayed. The
backend decimal strings and exact ratio numerator/denominator remain
authoritative in both views. In a `ready` result, **Normalized input and
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
contribution of `5 EUR`, and the valuation rate `1 USD = 0.9 EUR`.

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

Treat names, quantities, prices, cash, and rates as financial data. Two
different reads happen behind this pilot, and it helps to keep them apart:

- The **Your assets** gallery reads your own OWNER custody positions from
  your authenticated Portfolio, read-only, to offer them for copying. It
  never writes back to your Asset, Broker, or Transaction records.
- The **PAC calculation** itself receives only the scenario values present
  in your draft — whether copied or typed — never a live link to your
  Asset, Broker, or Portfolio records, and it does not call price, FX, or
  other data providers.

Use synthetic labels for manual rows when real names are unnecessary, and
protect any screenshots or copied exact output. The result is analysis, not
investment advice or authorization to trade.

## 🔗 Related

- [Tools overview](../index.md)
