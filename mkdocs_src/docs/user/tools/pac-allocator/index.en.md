---
title: PAC allocator
description: Plan which purchases bring an allocation closest to its target. The calculation engine is installed; its interface is being rebuilt.
---

# 🧮 PAC allocator

The **PAC allocator** answers one question:

> With the money available for this contribution cycle, which purchases bring
> my allocation as close as possible to its target?

The tool is listed in the Tools catalogue and its calculation engine is
installed. **It currently has no interactive interface**, so there is no way to
enter a scenario and obtain a result from the application yet.

!!! warning "No interface yet — your installation is not broken"

    The earlier prototype interface was removed together with the prototype
    calculation it drove. The replacement engine is already in place, but its
    interface has not been rebuilt yet, so the tool cannot be opened.

    If you see the PAC allocator in the catalogue and it will not open, the
    application is behaving as expected. Nothing is missing from your
    installation, and no calculation is failing silently in the background.

## 👀 What you see today

In **Tools**, the PAC allocator still appears as a card showing its name,
description, documentation link, and the version pair
`Backend/API 2.0.0 · UI 2.0.0`. The card also carries this message:

> The backend tool is installed, but its interface is not included in this
> frontend build. No calculation has been started.

The card is **not clickable**. The arrow and the full-card link that open a
ready tool are not drawn while the interface is missing, and opening the tool's
address directly shows the same message instead of a form.

That last sentence is the one that matters: no scenario was submitted, no
calculation was started, and nothing in your portfolio was read, changed, or
saved.

!!! note "About the UI version on the card"

    The `UI` number is the interface version this tool *expects*. It is
    published by the backend and does not prove that a matching interface is
    present in the frontend build you are running.

## 🧮 What the calculation engine does

The engine behind this tool plans **purchases**. Given a set of Assets with
their prices, the Brokers and buy routes that can be used to reach them, the
cash and contributions available, and one target weight per Asset, it searches
for the combination of purchases whose resulting allocation sits as close as
possible to those targets.

Three properties are worth knowing, because they shape what a future interface
will be able to promise:

- **It buys whole units where whole units are required.** Purchase grids,
  quantity steps, fees, and the currencies involved are part of the problem it
  solves, not a rounding step applied afterwards.
- **Its published numbers come from exact arithmetic.** Every candidate plan is
  re-checked exactly before anything is shown. A plan that fails that check is
  never published.
- **It never presents an unverified plan as a result.** When it cannot
  establish one, it says so, rather than offering a best guess.

A completed calculation therefore reports one of a small set of honest
outcomes: the best plan it could prove, that nothing needs to be bought, that
the request cannot be satisfied at all, or that it could not establish a plan
within its budget. It can also report that a scenario is incomplete, internally
inconsistent, or outside the range it supports.

The engine plans purchases only. It does not plan sales.

## 🎯 How its target is meant to be read

The PAC allocator distributes the liquidity available **now** — existing cash
plus new contributions. Its targets describe how that money should be
allocated; they do not describe the final mix of a portfolio you already hold.

The calculation does not take your current holdings as an input at all, so
changing what you hold cannot change what this tool plans.

## 🚫 What this tool never does

Whatever its interface eventually looks like, the calculation is bound by the
Tools platform contract:

- it does not place orders, execute trades, or contact a Broker;
- it does not write to your Assets, Brokers, or transactions;
- it does not read your portfolio by itself — it receives only the scenario it
  is given;
- its result is a plan to evaluate, not advice and not an instruction.

## 🔒 Your financial data

The calculation runs on the scenario submitted with the request. It is not
handed a live portfolio, a database connection, or your signed-in session, and
it produces nothing that is stored.

While there is no interface, nothing is submitted at all.

As always, avoid pasting real portfolio values, Broker exports, or account
identifiers into examples or support messages.

## 🔗 Related

- [Tools overview](../index.md)
