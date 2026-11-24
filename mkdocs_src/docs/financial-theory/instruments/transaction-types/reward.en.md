# 🎁 ![](../../../static/icons/transactions/reward.png){: width="32" style="vertical-align: middle;" } Reward

A **Reward** records units of an asset you receive as a payment in kind: crypto staking, an airdrop, a free share from a
platform. No cash moves. The units arrive, and their value on the day they arrive is **income**.

---

## 🔑 Key Properties

| Property | Value |
|----------|-------|
| **Code** | `REWARD` |
| **Cash effect** | None: a reward moves no cash |
| **Asset effect** | Required, a positive quantity: the units received |
| **Value on receipt** | Required: the value of **one** unit on the day it was received, in the currency you choose |
| **Income** | Yes: quantity × value on receipt |

---

## 📊 When to Use

Use a Reward when units of an asset reach you without you paying for them:

- **Staking rewards**: a proof-of-stake network or an exchange pays you new tokens for the ones you stake.
- **Airdrops**: a project sends tokens to your wallet.
- **Promotional shares**: a broker gives you a free share when you open an account.
- **Card cashback paid in a token**: the cashback arrives as units, not as cash.

A payment in **cash** for an asset you hold is a [Dividend or Interest](dividend-interest.md), not a Reward. Units that
arrive with no value of their own — a stock split, a transfer from another broker — are an
[Adjustment](adjustment.md) or an [Asset Transfer](transfer.md).

---

## 💰 What a Reward Means

A Reward of $q$ units valued $v$ per unit is read as **two things happening on the same day**: a dividend of value
$V$, immediately reinvested in a purchase of the same units at the same value.

$$
V = q \times v
$$

| Effect | Value |
|--------|-------|
| **Income** | $+V$, like a dividend: it counts in the period's income and return |
| **New lot** | $q$ units at a cost of $V$, dated on the day of the reward |
| **Cash** | Unchanged: the «dividend» and the «purchase» cancel out |
| **Capital invested** | Unchanged: you did not put new money in |

So a reward raises the value of your portfolio **by its income**, not by a deposit: the return of the period includes it.
When you sell the units later, the gain or loss is measured against $v$, the value on receipt, which becomes their cost.

!!! note "Income is a measure of return, not a tax figure"

    LibreFolio books the value on receipt as income because it is what the reward earned you. Whether and how it is
    taxed depends on your country: in some, a reward is taxed when it is received; in others only when the units are
    sold, or with a cost of zero. Check the rules that apply to you.

---

## 🧾 The Value on Receipt

The value is per **single unit**, not the total: LibreFolio multiplies it by the quantity.

- **In the transaction form**, LibreFolio suggests it from the asset's stored price history: the close of the reward's
  own day, per unit, in the price's currency. It is never the close of another day. You can change it whenever the
  platform shows another value.
- **From an import**, the value comes from the file when the platform writes it (for example Coinbase's `Subtotal`,
  Crypto.com's `Native Amount`, Freetrade's price per share). When the file has no value (Bitvavo, CoinTracking, the
  Generic CSV), each reward waits for one: in the bulk workspace, **Fill from price history** writes the close of that
  very day for all of them at once, and a day with no stored price is left for you.

A value of `0` is a value: an airdrop with no market yet is received at zero, and its later sale is all gain.

---

## 🔬 Rewards in the Lots Analysis

By default each reward opens **its own lot**, dated on the day of the reward, at its value on receipt. The income is
attributed to the lots you already held the day before, like a dividend's.

The lots panel also offers a second view, **Rewards in lots** (in the selector **Rewards apart** / **Rewards in lots**, shown when the scope holds a Reward). It answers a different question: «how much did
the units I bought really cost me, counting the rewards they produced?»

- The units of each reward **join the lots the broker held at the close of the day before**, in proportion to their size,
  at no cost and with no date of their own.
- Each lot grows and its average cost per unit falls; nothing is booked as income.
- When the broker held no lot of that asset the day before (an airdrop of a new token), the reward keeps a lot of its own
  at a cost of zero, and an information note says so.

The two views never change your transactions: the selector only changes how the panel reads them, and it goes back to
the first view when you open another asset or change the brokers.

---

## 🔗 Related

- 💰 **[Dividend & Interest](dividend-interest.md)** — Income received in cash
- 🧮 **[Adjustment](adjustment.md)** — Units added or removed with no income
- 🪙 **[Crypto](../asset-types/crypto.md)** — The asset type where staking rewards are most common
- 💰 **[Taxation](../../fundamentals/taxation.md)** — Tax implications of transactions
