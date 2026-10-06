---
title: PAC allocator
description: Plan the purchases that bring a new investment as close as possible to its target allocation, in whole or fractional units or in amounts, without placing orders.
---

# 🧮 PAC allocator

The **PAC allocator** answers one question:

> With the money available for this contribution cycle, which purchases bring
> my allocation as close as possible to its target?

Open **Tools** from the sidebar and click the PAC allocator card: it opens a
guided planner. You describe a scenario step by step, press **Calculate plan**,
and get a purchase plan to evaluate. It is a simulation: nothing is bought and
no order is sent to a Broker.

## 🗺️ Using the planner

The PAC allocator card shows the version pair `Backend/API 1.0.0 · UI 1.0.0`,
and the open planner repeats it in its header.

!!! note "About the UI version on the card"

    The `UI` number is the interface version this tool *expects*. It is
    published by the backend and does not prove that a matching interface is
    present in the frontend build you are running.

The planner guides you through these steps, in order. The **FX** step appears
only when the scenario needs exchange rates.

| Step | What you set |
|---|---|
| **Scenario** | A new investment, a "pure PAC": the calculation starts from an empty portfolio, so what you already hold is not counted, and it splits the cash you choose among the Assets, as close as possible to the target weights. You set the **Valuation currency**, in which amounts are compared and summarized (at first, the **Base Currency** of your preferences; money stays in its own currency, and every exchange needed appears in the plan), and the **Reference date**. |
| **Liquidity** | Where the money comes from; you can combine sources. **From your Brokers**: cash already on your Brokers in LibreFolio, of which you choose how much to use. **New contribution**: new money you add, such as the PAC instalment. **External account**: a balance on an account not registered in LibreFolio, for example at your bank; you declare how much is there and how much to use. Nothing is bought from an external account: its money is sent to a Broker. The Broker that receives a contribution or an external account's money is chosen in the **Brokers** step. Each amount stays in its own currency. |
| **Brokers** | Choose an existing Broker or add a **Manual Broker**: these are scenario data, and the Broker itself is never changed. For each currency you buy in, set the order mode, **By number of units** or **By amount**, and its **Increment**: every proposed order is a multiple of it (1 = whole units only, 0.001 = fractions down to three decimals; by amount, the smallest amount you can enter, such as 0.01). You can also set a purchase fee (a fixed part plus a percentage kept between a minimum and a maximum; it is paid from your liquidity and is not invested), narrow the **Usable liquidity** (the Broker's own cash plus the contributions and other accounts you allow: all of them at first, and you can exclude a source or cap how much of it is used there), and choose how currencies are converted: **You convert before buying** or **The Broker converts when you buy**, both at the rate of the **FX** step minus the spread. Fees and order modes are not recorded in LibreFolio, which is why you set them here. |
| **Assets** | Search the Assets registered in LibreFolio, add **Your Assets** (those with an open position today in your Brokers, added as rows only, without quantities), or add a **Manual Asset**. Each price is either **Auto** (the latest price stored in LibreFolio, read again just before the calculation; no data provider is called) or **Manual** (your own price, used as typed and never read again). A missing price stays in the draft: the calculation asks for it. The composition by country, sector, and type, copied from the Asset or typed, feeds only the exposure maps and bars of the result, not the calculation. |
| **Routing** | For each Broker, which Assets it may buy: **Allow all**, **Exclude all**, or click each one. Optional limits, measured like that Broker's orders (units or amount): **Minimum purchase** (if the plan buys there, at least this much), **Required purchase** (bought whatever happens; if resources are not enough, the plan becomes impossible), and **Maximum purchase**. **Priority** (0 = preferred) only breaks ties between plans equally close to the target. With a **Price margin**, each purchase is counted at price × (1 + margin), to cover a price that rises before the order; the difference is a reserve, not invested. Empty fields restrict nothing. |
| **Targets** | How to split the money you invest now among the Assets, in percent (decimals allowed). To calculate, the targets must add up to exactly 100%: **Balance all** rescales them, keeping their ratios. **Copy current distribution** reads how much each of these Assets weighs today in the Brokers you tick, counting only these Assets and not cash, and brings the ratios to 100%. These are weights only, a base to edit and not advice: you see them before using them, and a target you changed is not overwritten without your confirmation. |
| **FX** (only when needed) | One rate per currency pair in play, **Auto** (the latest rate stored in LibreFolio, read when the step opens and again just before the calculation; no data provider is called) or **Manual**, plus one **Conversion spread**: a percentage surcharge on every converted amount. Valuation uses the official rate without spread; conversions use the rate with the spread. When LibreFolio has no rate for a pair, the step offers **Add the pair** or **Download the rates**: each opens the matching window of the FX page, and nothing is added or downloaded until you confirm there. |
| **Strategy** | **Proportional**: purchases only, it sells nothing. Among all the purchase plans that respect your settings, it picks the best one with a cascade, each criterion deciding only among the plans still tied on the ones above: closeness to the targets (L2 distance), then uninvested money, then Broker and source priority, then explicit costs (fees, spread, margin), then number of orders. A fixed order of Assets and Brokers settles any final tie, so a search that completes always gives the same plan for the same data; a search stopped by a time or node limit can give a different plan on a slower or busier machine. |
| **Review** | A last check. It lists the complete copy that will be sent (the backend receives this copy, and only this), flags the fields still to complete, and offers **Calculate plan**. |

Not supported in this version: a tax regime, losses, and sell fees for a
Broker; a different exchange rate or spread per Broker; a safety margin on the
rate; a conversion fee on top of the spread; conversions in more than one step
(for example EUR → USD → CHF).

### 📋 Copied or typed values

The planner works without any registered Broker or Asset: everything can be
typed. When you would rather start from your LibreFolio data, you copy it with
an explicit action: **Choose existing Broker**, **From your Brokers**, the
Asset search or **Your Assets**, and **Copy current distribution**. In the
**FX** step, an **Auto** rate is read from LibreFolio as soon as the step opens.

Each value shows where it came from (**Copied**, **Manual**, or **Modified**),
and a copy also shows its date. A copy does not follow its source while you
edit, and a copy you modified can be restored.

When you press **Calculate plan**, the planner first reads again from
LibreFolio the prices, rates, and balances you copied and have not changed.
Values you typed or changed stay as they are. If that read fails, nothing is
calculated: you can **Try again**, or **Calculate with the copied data** to use
the earlier copies.

### ⏳ While it calculates

While the request is active, the planner shows **Calculation in progress** and
the configuration is locked. **Stop waiting** stops only the wait: the server
may finish anyway, and that answer is discarded.

If you change the draft after a result, a **Result not up to date** banner
appears: the previous values can still be consulted, but they no longer
describe the current draft.

## 📊 Reading the result {: #reading-the-result }

A calculation ends with one of these outcomes:

| Outcome | What it means |
|---|---|
| **Plan found** | A plan that respects every constraint. It is marked **Proven optimal** when the solver proved, within its small calculation margin (which grows with the amounts), that no better plan exists, objective by objective in the order of the **Strategy** step. It is marked **Optimality not proven** when the solver reached its time or node limit, or when its own numbers do not match the exact check of the plan: it is then the best plan found, but it is not proven to be the best. |
| **No operation** | No order, no exchange, and no funding is needed. |
| **Infeasible** | Proven: no combination meets every hard constraint together. The hard constraints involved are listed; the planner does not choose which one to relax, and no partial plan is shown as valid. |
| **No plan found** | Within its limits, the solver found no plan. This is not a proof that none exists. |
| **More data needed** | Something is missing. Your draft is intact, and no Asset is removed silently: add the missing fact or remove the Asset yourself. |
| **Input not valid** | Some of the data are not valid. |
| **Scenario not supported** | Not an error in your data: this version does not handle the case. |

Every plan shown has been checked again in exact decimal arithmetic,
independently of the solver: that is the **Verified in Decimal** badge. The
last three outcomes mean that the calculation could not start on your data:
nothing is calculated, and the problems found are listed.

Platform errors, such as a timeout, a full queue, or a crashed worker, are
different from all of the above: they are not financial conclusions. The
[Tools overview](../index.md) explains them.

A plan is laid out in these sections:

- **Key figures**: the plan in a few numbers, such as the cash chosen, the
  money not invested, the costs, and the number of orders.
- **Allocation per Asset**: each target next to the weight after the plan.
- **Assets**: the values of each Asset, in the valuation currency.
- **Exposures – ideal vs actual**: maps and bars by country, type, and sector,
  built from the compositions of the Assets.
- **Balances per Broker and currency**: how each cash balance moves, and what
  is left.
- **Operational plan**: numbered steps to follow in order. First the cash
  (available cash, transfers, deposits), then the currency exchanges, then the
  orders, each with the instruction to enter at the Broker.
- **Proof and solver**: how the outcome was established.

Every figure comes from the backend accounting; the interface adds nothing up.
With privacy mode on (see [User preferences](../../settings/preferences.md)),
amounts, quantities, and charged fees are hidden. Market prices, exchange rates,
percentages, and exposure weights stay visible, because they say nothing about
how much you own.

## 🧮 What the calculation engine does

The engine behind this tool plans **purchases**. Given a set of Assets with
their prices, the Brokers and buy routes that can be used to reach them, the
cash and contributions available, and one target weight per Asset, it searches
for the combination of purchases whose resulting allocation sits as close as
possible to those targets.

Three properties are worth knowing, because they shape what the planner can
promise:

- **It buys in each Broker's increments.** Whole units, fractions of a unit
  down to the step you set, or amounts: increments, fees, and the currencies
  involved are part of the problem it solves, not a rounding step applied
  afterwards.
- **Its published numbers come from exact arithmetic.** Every candidate plan is
  re-checked exactly before anything is shown. A plan that fails that check is
  never published.
- **It never passes off an unproven plan as optimal.** A plan stopped by a time
  or node limit is shown as the best one found and marked
  **Optimality not proven**. So is a plan whose exact check does not match the
  solver's own numbers, even when the search ended by itself. When no plan is
  found, it says so instead of guessing. With amounts of around ten billion
  units of a currency or more, the solver's calculations can lose precision: the
  tool may then stop with an error, or mark the plan **Optimality not proven**.

A completed calculation therefore reports one of the small set of honest
outcomes listed in [Reading the result](#reading-the-result).

The engine plans purchases only. It does not plan sales.

## 🎯 How its target is meant to be read

The PAC allocator distributes the liquidity available **now** — existing cash
plus new contributions. Its targets describe how that money should be
allocated; they do not describe the final mix of a portfolio you already hold.

The calculation does not take the positions you already hold as an input at
all, so changing them cannot change what this tool plans. **Copy current
distribution** only turns them into target weights for you to edit, and those
weights do not follow later changes.

## 🚫 What this tool never does

The planner and the calculation behind it stay within the Tools platform
contract:

- it does not place orders, execute trades, or contact a Broker;
- it does not write to your Assets, Brokers, or transactions;
- it does not read your portfolio by itself: the calculation receives only the
  scenario sent from **Review**, and the planner reads your LibreFolio data
  only when you copy something or open the **FX** step (for its **Auto**
  rates), then again just before a calculation for the copied values you have
  not changed;
- its result is a plan to evaluate, not advice and not an instruction.

## 🔒 Your financial data

The calculation runs on the scenario submitted with the request. It is not
handed a live portfolio, a database connection, or your signed-in session, and
it produces nothing that is stored.

Your draft lives only in the open page: it is saved neither on the server nor
in the browser. Leaving the planner, or reloading or closing the tab, with a
draft in progress asks you to confirm first. Signing out or switching account
discards the draft without asking.

As always, avoid pasting real portfolio values, Broker exports, or account
identifiers into examples or support messages.

## 🔗 Related

- [Tools overview](../index.md)
- [User preferences](../../settings/preferences.md), including privacy mode
