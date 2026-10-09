---
title: PAC allocator
description: Plan the purchases that bring a new investment as close as possible to its target allocation, in whole units or by amount, without placing orders.
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

The planner guides you through these steps, in order. The **FX** step appears
only when the scenario needs exchange rates.

### 🎬 Scenario

You plan a new investment, a "pure PAC": the calculation starts from an empty
portfolio, so what you already hold is not counted, and it splits the cash you
choose among the Assets, as close as possible to the target weights.

Here you set the **Valuation currency**, in which amounts are compared and
summarized. At first it is the **Default Currency** of your preferences. Money
stays in its own currency: every exchange needed appears in the plan.

The reference date is always today: the planner sets it again before every
copy from LibreFolio and before every calculation.

### 💰 Liquidity

Where does the money come from? You can combine several sources:

- **From your Brokers**: cash already on your Brokers in LibreFolio. You choose
  how much of it to use.
- **New contribution**: new money you add, such as the PAC instalment.
- **External account**: a balance on an account not registered in LibreFolio,
  for example at your bank. You declare how much is there and how much to use.
  Nothing is bought from an external account: its money is sent to a Broker.

The Broker that receives a contribution or an external account's money is
chosen in the **Brokers** step. Each amount stays in its own currency.

<!-- [Screenshot Placeholder: tools/pac-step-liquidity — the Liquidity step with cash copied From your Brokers, a New contribution and an External account, each amount in its own currency] -->

### 🏦 Brokers

Add the Brokers where the plan may buy: **Choose existing Broker** copies one
of yours, and **Manual Broker** adds one by hand. Either way they are scenario
data: the Broker itself is never changed. Fees and order modes are not
recorded in LibreFolio, which is why you set them here.

For each currency you buy in, set:

- The order mode: **By number of units** or **By amount**.
- The **Increment** $\Delta$: every proposed order is a whole multiple of it.
  With $q$ the size of an order, in units or as an amount:

    $$
    q = k\,\Delta, \qquad k = 0, 1, 2, \dots
    $$

    By number of units, $\Delta$ is a whole number: $\Delta = 1$ means whole
    units only. By amount, $\Delta$ is the smallest amount you can enter, such
    as $\Delta = 0.01$, and the units you get can be fractions of a unit.

- The **Purchase fee**: a **Fixed part** $f$ plus a **Percentage** $r$ of the
  order amount $A$, price margin included. The **Minimum** $f_{\min}$ and the
  **Maximum** $f_{\max}$ limit the percentage part only, and an empty
  **Maximum** sets no upper limit:

    $$
    \text{fee} = f + \min\big(\max(r\,A,\ f_{\min}),\ f_{\max}\big)
    $$

    The fee is charged on every order, and no order means no fee. It is paid
    from your liquidity and is not invested. For example, with $r = 0.19\%$,
    $f_{\min} = 1.50$, $f_{\max} = 18$ and no fixed part, an order of $500$
    pays $1.50$, one of $2{,}000$ pays $3.80$, and one of $20{,}000$ pays $18$.

Each Broker also has two settings of its own:

- **Usable liquidity**: the money the plan may use to buy there, that is the
  Broker's own cash plus the contributions and other accounts you allow. All
  of them are allowed at first: you can exclude a source, cap how much of it
  is used there, and give it a **Priority** ($0$ = preferred).
- **Currency conversion**: **You convert before buying** or
  **The Broker converts when you buy**. Both convert at the rate of the **FX**
  step minus the spread, so the calculation is the same either way: only the
  way the plan shows the conversion changes.

<!-- [Screenshot Placeholder: tools/pac-step-brokers — the Broker editor: order mode By number of units or By amount, Increment, purchase fee, and currency conversion mode] -->

Not supported yet: a tax regime, losses, and sell fees for a Broker.

### 💼 Assets

Add the Assets the plan may buy, in any mix:

- search the Assets registered in LibreFolio;
- add **Your Assets**: those with an open position today in your Brokers,
  added as rows only, without quantities;
- add a **Manual Asset**.

Each price is either:

- **Auto**: the latest price stored in LibreFolio, read again just before the
  calculation. No data provider is called.
- **Manual**: your own price, used as typed and never read again.

A missing price stays in the draft: the calculation asks for it.

The composition by country, sector, and type, copied from the Asset or typed,
feeds only the exposure maps and bars of the result, not the calculation.

<!-- [Screenshot Placeholder: tools/pac-step-assets — the Assets step with an Asset added from LibreFolio and a Manual Asset, each price Auto or Manual] -->

### 🔀 Routing

For each Broker, choose which Assets it may buy: **Allow all**,
**Exclude all**, or click each one.

Then, only where you need them, set limits on each route. They are measured
like that Broker's orders, in units or as an amount. With $q$ the purchase of
the Asset on that Broker:

- **Minimum purchase** $q_{\min}$: if the plan buys there, it buys at least
  this much, so $q = 0$ or $q \ge q_{\min}$.
- **Required purchase** $q_{\text{req}}$: bought whatever happens,
  $q \ge q_{\text{req}}$. If the resources are not enough, the plan becomes
  impossible.
- **Maximum purchase** $q_{\max}$: the most the plan may buy there,
  $q \le q_{\max}$.

Two more settings shape how the plan buys there:

- **Priority** ($0$ = preferred): it only breaks ties between plans equally
  close to the target.
- **Price margin** $m$: each purchase is counted at $p\,(1 + m)$ instead of
  the price $p$ of one unit, to cover a price that rises before the order. A
  margin of $0.5\%$ on a price of $100$ counts $100.50$. The difference is a
  reserve, not invested. By amount, an order of $A$ buys
  $A / \big(p\,(1 + m)\big)$ units.

Empty fields restrict nothing.

<!-- [Screenshot Placeholder: tools/pac-step-routing — the Routing step: the Assets each Broker may buy, with Minimum purchase, Required purchase, Maximum purchase, Priority and Price margin] -->

### ⚖️ Targets

Here you split the money you invest now among the Assets: one target $w_i$
per Asset, in percent, decimals allowed. To calculate, the targets must add up
to exactly $100\%$:

$$
\sum_i w_i = 100\%
$$

Two actions help you get there:

- **Balance all** rescales every target, keeping their ratios:

    $$
    w_i' = \frac{w_i}{\sum_j w_j} \cdot 100\%
    $$

    If they are all $0$, every Asset gets an equal part. Rounding keeps the
    total at exactly $100\%$. To change only some rows, **Balance to 100%** on
    a row gives that Asset what is missing, or takes away the excess, and
    **Balance the selected rows to 100%** rescales only the rows you tick.

- **Copy current distribution** reads how much each of these Assets weighs
  today in the Brokers you tick, counting only these Assets and not cash.
  With $H_i$ the market value of Asset $i$ held there today:

    $$
    w_i = \frac{H_i}{\sum_j H_j} \cdot 100\%
    $$

    The weights are rounded to $0.01$ percentage points and still add up to
    exactly $100\%$, and an Asset you entered by hand gets $0$. These are
    weights only, a base to edit and not advice: you see them before using
    them, and a target you changed is not overwritten without your
    confirmation.

<!-- [Screenshot Placeholder: tools/pac-step-targets — the Targets step with target percentages adding up to 100% and the Balance all and Copy current distribution actions] -->

### 💱 FX (only when needed)

This step appears only when the scenario needs exchange rates. It holds one
rate $x$ per currency pair in play, each **Auto** or **Manual**:

- **Auto**: the latest rate stored in LibreFolio, read when the step opens and
  again just before the calculation. No data provider is called.
- **Manual**: your own rate.

It also holds one **Conversion spread** $s$: a percentage of every converted
amount, kept as a margin for a change in the official rate or for Broker
fees. Converting an amount $D$ at the rate $x$ (units received for each unit
converted) gives

$$
D \cdot x\,(1 - s)
$$

instead of $D \cdot x$. Valuation, which compares and sums amounts in the
valuation currency, uses the official rate $x$ without spread; conversions use
the rate with the spread, $x\,(1 - s)$.

The rates must also agree with each other, so that no conversion creates
value: with cash in CHF, an Asset in USD and valuation in EUR, for example,
one CHF converted into USD after the spread may not be worth more in EUR than
one CHF,

$$
x_{\text{CHF} \to \text{USD}}\,(1 - s)\,x_{\text{USD} \to \text{EUR}}
\le x_{\text{CHF} \to \text{EUR}}
$$

and the same holds for every conversion the plan may need between two
currencies other than the valuation currency. Otherwise the calculation does
not start and the outcome is **Input not valid** (see
[Reading the result](#reading-the-result)): the cause can be a **Manual** rate
or **Auto** rates from different days or sources, so align the rates or set a
**Conversion spread** that covers the difference.

Like order amounts and fees, the amount received from a conversion is
rounded half up to the smallest unit of its currency, and the **Rounding**
column of **Balances per Broker and currency** shows how much of each row
comes from rounding: ≈ marks a figure shown rounded, as when the exact
difference has no finite decimal form (for example after converting USD → EUR
at $1/1.085$), and a difference below the smallest unit keeps the digits it
needs, such as ≈ −0.0022 rather than ≈ −0.00.

When LibreFolio has no rate for a pair, the step offers **Add the pair** or
**Download the rates**: each opens the matching window of the FX page, and
nothing is added or downloaded until you confirm there.

Not supported yet: a different exchange rate or spread per Broker, a safety
margin on the rate, a conversion fee on top of the spread, and conversions in
more than one step (for example EUR → USD → CHF).

### 🧠 Strategy

The strategy is **Proportional**: purchases only, it sells nothing.

Among all the purchase plans that respect your settings, it picks the best one
with a cascade of criteria, each deciding only among the plans still tied on
the ones above it:

1.  **Closeness to the targets (L2 distance)**: the smallest distance

    $$
    D = \sum_i \big(V_i - w_i\,R\big)^2
    $$

    where $V_i$ is the value of Asset $i$ after the plan, $w_i$ its target,
    and $R$ the **Base of the targets**: the cash you chose that can reach a
    Broker where it can buy (in a PAC nothing is already invested). So
    $w_i\,R$ is the ideal value of Asset $i$. Values are in the valuation
    currency, at the quote price, without fees or price margin. Squaring makes
    big gaps weigh more, and $D$ is measured in squared money, for example
    EUR².

2.  **Uninvested money**: the least money left out of the Assets,
    $R - \sum_i V_i$.

3.  **Broker and source priority**: the smallest sum of the **Priority**
    numbers of the orders and cash sources the plan uses.

4.  **Explicit costs (fees, spread, margin)**: the lowest total of fees,
    conversion spread, and price margin, in the valuation currency.

5.  **Number of orders**: the fewest orders.

A fixed order of Assets and Brokers settles any final tie, so a search that
completes always gives the same plan for the same data; a search stopped by a
time or node limit can give a different plan on a slower or busier machine.

### ✅ Review

A last check before the calculation. It lists the complete copy that will be
sent (the backend receives this copy, and only this), flags the fields still
to complete, and offers **Calculate plan**.

<!-- [Screenshot Placeholder: tools/pac-step-review — the Review step with the calculation data, the fields still to complete and the Calculate plan button] -->

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
describe the current draft. From the banner, **Back to Review** returns to the
last step, and **Discard the previous result** removes the old result and takes
you there too.

## 📊 Reading the result {: #reading-the-result }

A calculated plan opens with a header: the scenario date, the valuation
currency, and the draft revision, then a row of badges. Each badge explains
itself when you point at it, tap it, or focus it. A plan also shows its
**L2 distance** from the targets (the $D$ of the **Strategy** step), how much
is **Not invested**, and how many notes the calculation left; the notes are
listed just below, under **Notes on the calculation**. **Edit configuration**
takes you back to the **Review** step, and **Calculate new plan** runs the
calculation again.

<!-- [Screenshot Placeholder: tools/pac-result — a calculated plan: the outcome badges, the Key figures and the Allocation per Asset table] -->

A calculation ends with one of these outcomes:

| Outcome | What it means |
|---|---|
| **Plan available** | A plan that respects every constraint. A second badge says what it is worth. **Proven optimal**: the solver proved, within its small calculation margin (which grows with the amounts), that no better plan exists, objective by objective in the order of the **Strategy** step, and the exact check of the plan matches its numbers. **Optimality not proven**: the solver reached its time or node limit, or its own numbers do not match the exact check of the plan; it is then the best plan found, but it is not proven to be the best. |
| **No operation** | With the cash you chose, no purchase meets the constraints: the plan is to do nothing. No order, no currency exchange, and no funding. |
| **Infeasible with these constraints** | Marked **Infeasibility proven**: no combination meets every hard constraint together. The constraints involved are listed (each **Required purchase**, and the liquidity that can reach the Brokers), each with a link to the step where you can change it. The planner does not choose which one to relax, and no partial plan is shown as valid. |
| **No plan within the limits** | The solver found no plan before reaching its limit. This is not a proof that none exists. A lighter search helps: fewer Assets or routes, a lower **Maximum purchase**, or a larger **Increment**. |
| **More data needed** | Something is missing. Your draft is intact, and no Asset is removed silently: add the missing fact or remove the Asset yourself. |
| **Input not valid** | Some of the data are not valid. |
| **Scenario not supported** | Not an error in your data: the tool does not handle this case yet. |

Every plan shown has been checked again in exact decimal arithmetic,
independently of the solver: that is the **Verified in Decimal** badge. A last
badge tells how the search ended: **Completed** (the solver ended its search by
itself), **Time limit**, or **Node limit**. When a plan was found but the search
stopped at a limit, a notice adds that a better plan may exist; the result
stays complete and can be consulted. If rounding to the smallest unit of a
currency leaves a Broker slightly short, a notice says how much more cash that
Broker needs to execute the plan.

The last three outcomes mean that the calculation could not start on your
data: nothing is calculated, and the problems found are listed, with a link to
the step concerned when there is one. **Details** adds the backend code of each
problem.

Platform errors, such as a timeout, a full queue, or a crashed worker, are not
financial conclusions about your scenario: your draft stays intact, so try
again later. If the tool is unavailable, see
[Settings → About → Plugin diagnostics](../../settings/about.md).

### 🗂️ How a plan is laid out

Below the outcome, a plan is laid out in this order:

1. **Key figures**: the plan in a few numbers, **Base of the targets**,
   **Invested after**, **Not invested**, **Cash chosen**, **Costs**, and
   **Orders**, each with a **?** that explains it and, below the value, the
   parts it is made of. Beside them, the **Calculation** box shows how long the
   optimizer worked, the time it was allowed for each objective, and how many
   objectives it closed.
2. **Allocation per Asset**: for each Asset, its target share next to its share
   after the plan, with its ideal value $w_i\,R$, its value after the plan
   $V_i$, the gap from the ideal $V_i - w_i\,R$, and the value bought.
3. **Operational plan**: the steps to follow, in order. First the cash
   (**Available cash**, **Transfer**, **Deposit**), then the currency exchanges
   you make yourself, then one table of orders per Broker, with the
   **Instruction** to enter at the Broker, the **Price**, the **Order amount**,
   and the **Fee**. A conversion that the Broker makes by itself when you buy
   has no number: it appears above that Broker's orders as an
   **Automatic conversion**. This section is shown only when the plan has
   something to do.
4. **Exposures – ideal vs actual**: maps and bars by country, type, and sector,
   built from the compositions of the Assets. The charts do not change the
   plan.
5. **Balances per Broker and currency**: how each cash balance moves, and what
   is left.
6. **Proof and solver**: how the outcome was established. The outcome, proof,
   and stop badges, the exact value of each objective, the solver stages, and
   the backend timings.

**Allocation per Asset** and **Operational plan** start open; the other
sections open on request, and **Expand all** / **Collapse all** opens or closes
them together. Without a plan (**Infeasible with these constraints** or
**No plan within the limits**), **Proof and solver** is the only section, and
the key figures show only the **Calculation** box.

<!-- [Screenshot Placeholder: tools/pac-result-plan — the Operational plan: numbered cash and currency exchange steps, then the orders table of a Broker] -->

Click an order, or its **Detail** button, to open its detail: the instruction,
the economic quantity, the prices used (source price, mid price, and charge
price with the price margin), the cash debit and the fee, the conversions that
pay for it, and the priority, limit, and minimums of its route.
**Show provenance** lists where each value came from, **Copied** or **Manual**,
with the date and time of the copy or of your entry.

**Proof and timings**, at the top of the result, opens **Proof and solver** and
scrolls to it.

<!-- [Screenshot Placeholder: tools/pac-result-proof — the Proof and solver section: outcome, proof and stop badges, exact objective values, solver stages and backend timings] -->

Every figure comes from the backend accounting; the interface adds nothing up.
With privacy mode on (see [User preferences](../../settings/preferences.md)),
the result hides what would tell how much you own: every amount (key figures,
values, balances, order amounts, fees and costs, and the objective and solver
values measured in money, the **L2 distance** included), every quantity, and
the purchase limits of a route (**Minimum purchase**, **Required purchase**,
**Maximum purchase**). The amounts in the problems listed when a calculation
could not start are hidden too. Market prices, exchange rates, percentages
(targets, shares, exposure weights, spreads, and margins), increments,
priorities, counts, and dates stay visible, because they say nothing about how
much you own.

## 🧮 What the calculation engine does

The engine behind this tool plans **purchases**. Given a set of Assets with
their prices, the Brokers and buy routes that can be used to reach them, the
cash and contributions available, and one target weight per Asset, it searches
for the combination of purchases whose resulting allocation sits as close as
possible to those targets.

Three properties are worth knowing, because they shape what the planner can
promise:

- **It buys in each Broker's increments.** Whole units or amounts, always in
  multiples of the increment you set: increments, fees, and the currencies
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
