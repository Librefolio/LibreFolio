---
title: Portfolio rebalancer
description: Bring an already invested portfolio towards its targets, estimating fees and taxes, without placing orders.
---

# ⚖️ Portfolio rebalancer

The **Portfolio rebalancer** answers one question:

> Given what I already hold and the cash I add, which operations bring my
> portfolio closest to its targets, and what do they cost?

Where the [PAC allocator](../pac-allocator/index.md) splits new money starting
from an empty portfolio, the rebalancer starts from your current holdings. It is
a simulation: nothing is bought and no order is sent to a Broker.

!!! info "Work in progress"

    The rebalancer's planning engine is in place; its guided page in **Tools**
    arrives in a later version of 1.4, and this page will then describe it step
    by step. For now the rebalancer plans **Invest only**: it buys with the cash
    and the contributions you select, and sells nothing.

## 🎯 What it optimises

The rebalancer weighs two things against each other:

- **How far the portfolio ends from its targets.** Every Asset and every cash
  item with a target counts, on the whole wealth the plan starts from (your
  holdings plus the cash and the contributions you select); what is left neither
  in an Asset nor in a cash item with a target counts as off-target too.
- **The money the plan loses**: fees, the spread of currency conversions,
  execution margins and rounding.

How much a step closer to the target is worth in money is the **target
fidelity** you choose: **Cost aware** (spend little to get closer),
**Balanced**, **Faithful** (get close even when it costs more), a custom value,
or **Target first**, which reaches the closest possible portfolio first and only
then spends as little as possible. Among plans that are equally good it prefers
fewer operations, then your preferred routes.

## 📋 What the plan shows

- Every Asset and cash item **before** the plan, at its **target** and
  **after**, as an amount and as a share of the starting wealth, with the cash
  left uninvested.
- The steps in the order you execute them: deposits of your contributions,
  transfers between your Brokers, manual currency conversions, then the orders.
- The plan's accounts: the wealth before and after, and the money lost, item by
  item.
- The largest distance of any item from its target, before and after the plan.
