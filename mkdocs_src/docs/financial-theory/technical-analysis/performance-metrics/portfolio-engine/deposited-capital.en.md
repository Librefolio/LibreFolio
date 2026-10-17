# 💸 Deposited Capital, Total PnL and Cash Pools

## 💡 Concept Overview

**Capital Baseline** = cumulative economic capital contributed since inception:

$$
\mathrm{CapitalBaseline}(t)=
\sum_{\tau \leq t}\mathrm{ExternalCashFlow}(\tau)
+ \sum_{\tau \leq t}\mathrm{InKindCapital}(\tau)
$$

**Total PnL** = all value generated above external contributions:

$$
\boxed{\mathrm{TotalPnL}(t) = \mathrm{NAV}(t) - \mathrm{CapitalBaseline}(t)}
$$

`InKindCapital` covers the securities that enter or leave the scope without cash:

- ADJUSTMENT rows carrying a cost basis (`cost_basis_override`, not linked to a split): an incoming row **at cost**, the cost it adds to the position; an outgoing row **at the value it hands over**, its quantity times its cost basis, converted at the rate of its own date ([Outgoing Adjustments](#outgoing-adjustments));
- TRANSFER legs whose other leg is not in the scope — it sits at a broker outside the view, is missing, or was never linked — **at market value** on their own date: $+$ for securities received, $-$ for securities sent. A security with no price at all on that date — no quote, no BUY or SELL on or before it — counts **at cost** instead: the cost the leg moves in its position, the cost a received leg adds or the average cost a sent leg removes. An unknown cost counts as zero, as in the position's own cost. While the position's cost is complete, the NAV values the holding at that same cost and the leg is neutral; with part of the cost unknown, the holding has no value in the NAV, yet the leg still moves its known cost, so nothing is left in the capital once the units are gone. Nothing counts if the security cannot be valued that day: it has a price, but the exchange rate is missing.

These rows move value without cash: they are capital, not profit or loss. An outgoing ADJUSTMENT also realizes the difference between the value it hands over and the average cost its position gives up, as a sale does.

---

## 🎯 What Counts

| Transaction | Effect on capital baseline |
|------------|-----------------|
| DEPOSIT / WITHDRAWAL (unlinked) | ✅ Yes |
| CASH\_TRANSFER / FX\_CONVERSION whose other leg is outside the view, missing, or never linked (orphan) | ✅ Yes, at its amount, like a deposit or a withdrawal |
| CASH\_TRANSFER / FX\_CONVERSION / TRANSFER with both legs in the view (internal pair) | ❌ No. Per broker, a pair across two brokers moves capital from the sender to the receiver on the arrival day, summing to zero ([Internal Transfers](#internal-transfers-broker-lines)) |
| TRANSFER of securities whose other leg is outside the view, missing, or never linked (orphan) | ✅ Yes, in-kind capital at market value on its date, or at cost for a security with no price at all |
| ADJUSTMENT with `cost_basis_override`, not split-linked | ✅ Yes, in-kind capital: incoming at cost, outgoing at the value it hands over ([below](#outgoing-adjustments)) |
| SPLIT-linked ADJUSTMENT | ❌ No, quantity rescale only |
| BUY, SELL, DIVIDEND, INTEREST, FEE, TAX | ❌ No |
| Exchange-rate move on cash held in another currency (no transaction) | ❌ No: a result, part of TotalPnL; the capital flows (deposits, withdrawals, orphan cash legs) entered the baseline at the rate of their own dates |

---

## 📤 Outgoing Adjustments {: #outgoing-adjustments }

An ADJUSTMENT that removes $|q|$ units of asset $a$ from broker $b$ on date $d$ with a per-unit cost basis $k$ — units given away, or moved to a broker LibreFolio does not track — hands them over at that cost, converted at the rate of its own date:

$$
D = s_b \cdot |q| \cdot k \cdot \mathrm{fx}(c_k, C^*, d)
$$

$c_k$ is the currency of the cost basis, the asset's currency when the row has none, and $s_b$ the broker's [ownership share](../../../../user/brokers/sharing.md). The position gives up the historical cost of those units, at its [average cost](../weighted-average-cost.md) before the adjustment, each purchase at the rate of its own date:

$$
C = s_b \cdot |q| \cdot w_{\text{pre}}(a,b)
$$

The adjustment is booked as a sale whose proceeds are $D$:

$$
\Delta\mathrm{CapitalBaseline}(d) = -D, \qquad \mathrm{Realized} = D - C
$$

- **Capital.** $D$ leaves the capital baseline, and the capital of broker $b$'s line: the mirror of an incoming ADJUSTMENT, which adds the cost it brings in. No cash moves, so the [cash pools](#three-pool-cash-model) do not change.
- **Realized.** $D - C$ counts in the period's realized gain or loss and in the position's contribution ([Period P&L](period-pnl.md)), and is left out, as a sale is, when the position's cost is incomplete. In a single currency, with a cost basis equal to the average cost, it is zero.
- **Returns.** TWRR and MWRR take their flows from the changes of the capital baseline, so the adjustment is a flow of $-D$ on $d$. When $D$ equals the units' market value that day — a cost basis at the day's market price — the adjustment leaves that day's return untouched; otherwise the difference between their market value and $D$ counts in it.
- **No rate on or before $d$.** $D$ is unknown: the adjustment is left out of Realized, the missing pair is reported with its date, and the capital drops by $C$ instead.

An outgoing ADJUSTMENT **without** a cost basis moves no capital and realizes nothing: its units leave the NAV, and their value comes off the TotalPnL.

!!! example "Dollar units handed over after the dollar fell"

    Report currency EUR. On a day when 1 USD = 0.90 EUR, a deposit of 1,000 USD — capital €900 — buys 10 units at 100 USD: $C = 900$. Later the price is still 100 USD but the rate is 0.80, so the units are worth €800. An ADJUSTMENT of −10 units with a cost basis of 100 USD hands them over at $D = 10 \times 100 \times 0.80 = 800$.

    | Moment | NAV | CapitalBaseline | TotalPnL | Realized |
    |--------|-----|-----------------|----------|----------|
    | Before the adjustment | 800 | 900 | −100 | 0 |
    | After the adjustment | 0 | 100 | −100 | −100 |

    The €100 that the dollar's fall took from the position while it was held is now realized, and TotalPnL does not move. The day's flow is −800, the value that left: with the price and the rate unchanged since the day before, the TWRR shows no return that day. Taken out at their average cost instead, €900, the units would leave a capital of 0: TotalPnL would jump to 0, and the TWRR would read +12.5% that day, the loss erased by the handover.

---

## 🔀 Internal Transfers in the Broker Lines {: #internal-transfers-broker-lines }

With two or more brokers in scope, the [P&L chart](../../../../user/dashboard/charts.md#pnl-line) draws one line per broker. Each broker $b \in S$ has its own NAV, capital and PnL:

$$
\mathrm{PnL}_b(t) = \mathrm{NAV}_b(t) - C_b(t)
$$

$$
\mathrm{NAV}_b(t) = \mathrm{MV}_b(t) + \mathrm{Cash}_b(t) + \mathrm{InTransit}_b(t)
$$

$$
C_b(t) = \sum_{\tau \leq t}\mathrm{ExternalCashFlow}_b(\tau) + \sum_{\tau \leq t}\mathrm{InKindCapital}_b(\tau) + \sum_{\tau \leq t}\mathrm{Internal}_b(\tau)
$$

$\mathrm{InTransit}_b$ is the value in transit that left $b$, and $\mathrm{Internal}_b$ is $b$'s side of the internal transfers described below. Since $\sum_b \mathrm{NAV}_b = \mathrm{NAV}$ and the internal flows cancel out every day, the lines add up to the scope figures:

$$
\sum_{b \in S}\mathrm{Internal}_b(t) = 0
\quad\Rightarrow\quad
\sum_{b \in S} C_b(t) = \mathrm{CapitalBaseline}(t),
\qquad
\sum_{b \in S}\mathrm{PnL}_b(t) = \mathrm{TotalPnL}(t)
$$

A broker's line is therefore the PnL earned while the value was at that broker, or travelling from it. It is not the unrealized gain of the positions the broker holds.

### 📐 The Internal Flow

An **internal pair** is a linked CASH\_TRANSFER, FX\_CONVERSION or TRANSFER whose two legs are both in $S$, on two different brokers: the sender $A$ (the leg going out) and the receiver $B$ (the leg coming in). It produces one flow, on the **arrival day** $t_{arr}$, the date of the later leg:

$$
\mathrm{Internal}_A(t_{arr}) = -X,
\qquad
\mathrm{Internal}_B(t_{arr}) = +X,
\qquad
X = s_A \cdot V(t_{arr})
$$

$s_A$ is the sender's [ownership share](../../../../user/brokers/sharing.md) and $V(t_{arr})$ the full value the arrival brings to $B$ that day, valued exactly as the NAV values it:

| Pair | $V(t_{arr})$ |
|------|--------------|
| CASH\_TRANSFER | The amount received, converted at $\mathrm{fx}(c, C^*, t_{arr})$ |
| FX\_CONVERSION across brokers | The received leg, converted the same way: $-1{,}000$ USD at $A$ → $+900$ EUR at $B$ gives $V = 900$ EUR, and the conversion cost stays in $A$'s line |
| TRANSFER of securities | $\mathrm{MV}$ of the quantity received at the [valuation price](index.md#2-valuation-price) of $t_{arr}$, the last known price carried forward if there is none that day. With no price at all on or before $t_{arr}$, the cost basis the units add to $B$'s position — the cost recorded on $B$'s leg, converted at that leg's date —, since the NAV values a holding with no price at its cost ([§3](index.md#3-position-state)) |

With equal shares, $X$ is exactly what the arrival adds to $\mathrm{NAV}_B$, so neither line jumps. The scope's $\mathrm{CapitalBaseline}$ is untouched, because an internal move is not external capital: NAV, CapitalBaseline, TotalPnL and its candles, ROI, TWRR, MWRR and cash are the same as without the flow. Only the split of the baseline among the brokers changes.

### ✈️ Value in Transit

When the legs fall on different days, the value travels from the departure day $t_{dep}$ to the day before $t_{arr}$. Meanwhile it is part of $\mathrm{InTransit}_A$, at the sender's share $s_A$, valued every day: cash at that day's exchange rate, securities at that day's valuation price (at the cost recorded on the transfer if the security has no price at all). No flow happens while the value travels, so its price and exchange-rate moves stay in $A$'s line, the arrival day's own move included; $B$'s line starts from the value received.

For example, $A$ receives a deposit of 1,000 USD on day 0 at 0.90 EUR per USD ($C_A = 900$) and sends the dollars on day 1; $B$ receives them on day 4. With the rate at 0.90, 0.91, 0.92, 0.93 on days 1–4, $A$'s line reads 0, +10, +20, +30 and $B$'s stays at 0. On day 4, $X = 930$ and $C_A = 900 - 930 = -30$. Once arrived, the dollars are $B$'s cash, revalued every day, so from day 5 $B$'s line moves with the rate: at 0.94, it reads +10.

### 🧩 Special Cases

- **Different ownership shares.** $X$ uses $s_A$, like the value in transit, while the arrival adds $s_B \cdot V(t_{arr})$ to $\mathrm{NAV}_B$. $B$'s line keeps a residual step of $(s_B - s_A)\,V(t_{arr})$ on the arrival day, and TotalPnL shows the same step, with or without the flow.
- **Value unknown on the arrival day.** If $V(t_{arr})$ cannot be computed — an exchange rate is missing, or the security has no observation on or before $t_{arr}$ ($\operatorname{mark} = \varnothing$) and the cost on $B$'s leg is unknown (no cost basis, or one with no exchange rate), so that the arrival adds nothing to $B$'s position cost — then $X = 0$. Nothing is guessed: the jump stays, and the security's value appears in the line of the broker holding it from its first price.
- **No price at all.** A security with no observation on or before $t_{arr}$ moves at the cost its arrival adds to $B$'s position — the cost recorded on $B$'s leg, the sender's average cost when the transfer is saved with an automatic cost basis — whether or not $B$'s cost is complete. With $B$'s cost complete, that is the value $\mathrm{NAV}_B$ takes the units at, so with equal shares $B$'s line does not jump. The cost need not equal the value the units had at $A$ before leaving, $A$'s own cost basis or nothing when that cost was incomplete; the difference ends up in $A$'s line, and TotalPnL shows it too. With $B$'s cost incomplete — $B$ already held units of unknown cost — $B$'s holding has no value in the NAV, which is incomplete: $B$'s line takes the gap, its own unknown cost, and $A$'s line is the same as with a complete cost at $B$.
- **Fees.** They are not part of $X$. A FEE row of 5 recorded at the sender, or the same 5 as a gap between the legs ($-1{,}000$ sent, $+995$ received, so $X = 995$), stays in $A$'s line as a loss of 5.
- **Same-broker pairs.** Two legs on the same broker, such as a currency conversion inside one account, need no flow: the value never leaves the line.
- **ADJUSTMENT pairs.** They are not internal pairs: each leg stays in-kind capital (see the table above). The sender's capital drops by the value its leg hands over, the receiver's rises by the cost its leg adds, and the sender realizes the difference between that value and its average cost ([Outgoing Adjustments](#outgoing-adjustments)). With the setup of the example below and both legs on day 2 at a cost of 10, $A$'s average cost, $A$ realizes nothing and the receiving line takes over the gain accrued at the sender: the lines read $A = 0$, $B = +20$. At a cost of 12, the day's price, $A$ realizes $+20$ and the lines read as for a TRANSFER pair: $A = +20$, $B = 0$.

### 🔍 Filtered Views

In a view with only some brokers, a TRANSFER leg whose other leg is outside $S$ — or missing, or never linked — cannot form an internal pair. It is in-kind capital at market value on its own date: $+\mathrm{MV}$ for securities received, $-\mathrm{MV}$ for securities sent, at that broker's share — at cost for a security with no price at all, as above — and nothing if the security cannot be valued that day. Unlike an internal flow, it moves the view's CapitalBaseline, so the view's TotalPnL, ROI, TWRR and MWRR treat it as capital, like an in-kind ADJUSTMENT. A CASH\_TRANSFER or FX\_CONVERSION leg in the same position is external cash at its amount, like a deposit or a withdrawal.

When the broker holding the other leg is deleted, the remaining leg becomes what a split of the pair leaves, and the legs older versions left are converted the same way at startup: securities become an ADJUSTMENT — in-kind capital at cost when it carries a cost basis (table above), no longer at market value — and cash a DEPOSIT or a WITHDRAWAL. A leg that sent securities stays a TRANSFER without its link when its average cost at its broker cannot be computed, for instance for a missing exchange rate. Such an orphan follows the same rules in every view, the full one included.

Comparing a broker's own view with the combined view:

- **The receiver alone matches its combined line.** In $B$'s own view the received securities are capital at their market value on $t_{arr}$, which is the $X$ of the combined view. This holds with equal shares and a price that both views can see: a price that comes only from trades at $A$ is not visible in $B$'s own view.
- **The sender alone loses the moves in transit.** In $A$'s own view its capital drops on the departure day by $s_A \cdot V(t_{dep})$, while in the combined view the value stays with $A$ until it arrives.

Writing $\mathrm{PnL}_A^{(S)}$ for $A$'s line in the view of scope $S$, from the departure day on:

$$
\mathrm{PnL}_A^{(A)}(t) = \mathrm{PnL}_A^{(A,B)}(t) - s_A\bigl[V(\min(t, t_{arr})) - V(t_{dep})\bigr]
$$

### 📦 Example — Securities in Transit

All amounts in EUR, shares 100%. $A$ receives a deposit of 100 and buys 10 units at 10 on day 0. The price is 10, 11, 12, 13, 14, 15 on days 0–5. $A$ sends the 10 units on day 1, and $B$ receives them on day 3.

**Combined view** (both brokers in $S$):

| Day | Price | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | TotalPnL |
|-----|-------|------------------|-------|------------------|------------------|-------|------------------|----------|
| 0 | 10 | 100 | 100 | 0 | 0 | 0 | 0 | 0 |
| 1 | 11 | 110 (in transit) | 100 | +10 | 0 | 0 | 0 | +10 |
| 2 | 12 | 120 (in transit) | 100 | +20 | 0 | 0 | 0 | +20 |
| 3 | 13 | 0 | −30 | +30 | 130 | 130 | 0 | +30 |
| 4 | 14 | 0 | −30 | +30 | 140 | 130 | +10 | +40 |
| 5 | 15 | 0 | −30 | +30 | 150 | 130 | +20 | +50 |

On day 3 the flow $X = 10 \times 13 = 130$ moves capital from $A$ to $B$. $A$ keeps the +30 earned while the units were at $A$ or travelling (10 → 13), and $B$ earns from 13 on. $C_A$ turns negative because $A$ passed on more value (130) than the capital it took in (100): the difference is its gain. TotalPnL is the same with or without the flow; without it, on day 3 $A$'s line would drop to $0 - 100 = -100$ and $B$'s would jump to $130 - 0 = +130$.

**Single-broker views**:

| Day | $B$ alone: $C_B$ | $B$ alone: $\mathrm{PnL}_B$ | $A$ alone: $C_A$ | $A$ alone: $\mathrm{PnL}_A$ |
|-----|------------------|-----------------------------|------------------|-----------------------------|
| 0 | — | — | 100 | 0 |
| 1 | — | — | −10 | +10 |
| 2 | — | — | −10 | +10 |
| 3 | 130 | 0 | −10 | +10 |
| 4 | 130 | +10 | −10 | +10 |
| 5 | 130 | +20 | −10 | +10 |

$B$'s own view starts at its first transaction and matches $B$ in the combined view. In $A$'s own view the units leave on day 1 at $10 \times 11 = 110$, so $C_A = 100 - 110 = -10$ and the line stays at +10: the move from 11 to 13 while travelling is not in it, and $+30 - (130 - 110) = +10$. Counted as a gain or a loss instead of capital, the same transfer would put $A$ alone at −100 from day 1 and $B$ alone at +130 on day 3.

### 💶 Example — Cash Between Two Brokers

$A$ receives a deposit of 5,000. Later, $A$ sends 1,000 to $B$, both legs on the same day.

| Case | $\mathrm{NAV}_A$ | $C_A$ | $\mathrm{PnL}_A$ | $\mathrm{NAV}_B$ | $C_B$ | $\mathrm{PnL}_B$ | TotalPnL |
|------|------------------|-------|------------------|------------------|-------|------------------|----------|
| After the deposit | 5,000 | 5,000 | 0 | 0 | 0 | 0 | 0 |
| After the transfer | 4,000 | 4,000 | 0 | 1,000 | 1,000 | 0 | 0 |
| $B$ receives 995 (fee 5) | 4,000 | 4,005 | −5 | 995 | 995 | 0 | −5 |
| $B$ owned at 50% | 4,000 | 4,000 | 0 | 500 | 1,000 | −500 | −500 |
| Without the flow | 4,000 | 5,000 | −1,000 | 1,000 | 0 | +1,000 | 0 |

The last row is the same transfer read without the internal flow: the move looks like a loss for $A$ and a gain for $B$. With $B$ owned at 50%, the step of −500 is the residual $(s_B - s_A)\,V = (0.5 - 1) \times 1{,}000$, and TotalPnL shows it too.

---

## 📊 Three-Pool Cash Model {: #three-pool-cash-model }

The Growth Chart decomposes current cash into two visible aggregates plus a hidden global tracker:

$$
\mathrm{Cash}(t) \approx \sum_b K_b(t) + \sum_b R_b(t)
$$

| Pool | Scope | Meaning |
|------|-------|---------|
| $K_b$ | Per-broker | External capital still at broker $b$ |
| $R_b$ | Per-broker | Generated returns still at broker $b$ |
| $W$ | Global | Returns that left the system (restorable on re-deposit) |

!!! info "Key properties"

    - $\mathrm{CapitalBaseline}$ = historical sum of cash and in-kind capital flows. $\sum K_b$ = how much current cash is external capital. They diverge after BUY/SELL.
    - A BUY on broker $b_1$ only consumes $R_{b_1}$, never $R_{b_2}$.
    - Cash transfers between brokers and currency conversions move $R$ and $K$ from source to destination without touching $W$: the departure leaves returns first, and the arrival brings back what it took from capital and returns; any gap between the two legs — another currency, another day's rate, another ownership share — is a result.
    - An exchange result on cash a broker holds in another currency goes to $R_b$; a loss larger than $R_b$ comes out of $K_b$, as a FEE does. $\mathrm{CapitalBaseline}$ does not move ([Portfolio Engine — §6](index.md#exchange-result-on-foreign-cash)).

🔗 Full per-broker update rules: **[Portfolio Engine — §6 Three-Pool Model](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)**

---

## 📝 Worked Examples

### 🧾 A — Deposit → Buy → Sell in Gain

| Step | Tx | $K$ | $R$ | Cash |
|------|----|-----|-----|------|
| 1 | DEPOSIT €1,000 | 1,000 | 0 | 1,000 |
| 2 | BUY €1,000 | 0 | 0 | 0 |
| 3 | SELL P=€1,200, C=€1,000 | 1,000 | 200 | 1,200 |

TotalPnL = 1,200 − 1,000 = **+€200** ✓

### 💸 B — Dividend then Withdrawal

| Step | Tx | $K$ | $R$ | $W$ | Cash |
|------|----|-----|-----|-----|------|
| 1 | DEPOSIT €1,000 | 1,000 | 0 | 0 | 1,000 |
| 2 | DIVIDEND €50 | 1,000 | 50 | 0 | 1,050 |
| 3 | WITHDRAWAL €100 (K first) | 900 | 50 | 0 | 950 |
| 4 | WITHDRAWAL €950 (K=900→0, R=50→0, W+=50) | 0 | 0 | 50 | 0 |
| 5 | RE-DEPOSIT €30 (restore min(30,W=50)=30) | 0 | 30 | 20 | 30 |

After step 5: Cash=30, K=0, R=30 ✓ (returns restored from W)

### 🧪 C — Full Sell Regression

| Step | Tx | $K$ | $R$ | Cash |
|------|----|-----|-----|------|
| 1 | DEPOSIT €1,000, BUY 1@€1,000 | 0 | 0 | 0 |
| 2 | SELL 1@€1,005 (C=1000, G=5) | 1,000 | 5 | 1,005 |

Capital correctly returns to $K$; only €5 gain to $R$. **Not** all €1,005 to $R$.

### 💱 D — Dollars Held While the Rate Moves

One broker, report currency EUR, rates in EUR per USD; $\varepsilon$ is the [exchange result on cash](index.md#exchange-result-on-foreign-cash).

| Step | Event | $\varepsilon$ | $K$ | $R$ | Cash | TotalPnL |
|------|-------|---------------|-----|-----|------|----------|
| 1 | DEPOSIT 1,000 USD at 0.90 | — | 900 | 0 | 900 | 0 |
| 2 | Rate rises to 0.95 | +50 | 900 | 50 | 950 | +50 |
| 3 | Rate falls to 0.85 ($R$ = 50 − 100, $K$ absorbs −50) | −100 | 850 | 0 | 850 | −50 |
| 4 | BUY for 1,000 USD at 0.85 (€850) | — | 0 | 0 | 0 | MV − 900 |

The CapitalBaseline stays €900 throughout: the exchange results are profit and loss, not capital. After step 4, TotalPnL is the security's market value MV less the €900 deposited — −50 on the purchase day if MV equals the €850 paid.

---

## ⚙️ Implementation

The 3-pool model runs in a **single per-transaction loop** (event-driven, not daily-delta):

1. Take the transaction's step of its position's average-cost pool, computed before the replay — for a SELL, the cost it removes ($C$ = pre-sale WAC × quantity sold, at historical rates)
2. Update K/R/W per transaction type rules, with that $C$ for a SELL

On each day the exchange rate of a foreign currency held as cash changes, each broker's exchange result on that cash is also booked into its pools, after the day's cash movements and before the day's transactions ([§6](index.md#exchange-result-on-foreign-cash)).

The ROI/TWRR/MWRR input series is derived from day-over-day changes in `cumulative_external_cash_flow`, the capital baseline. It is not derived from the cash-only `external_cash_flow` field.

🔗 See **[Portfolio Engine — §6](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)** for all formal rules.

---

## 🔗 Related

- 💼 [NAV](nav.md) — the other term in Total PnL
- 📊 [Period PnL](period-pnl.md) — windowed version
- ⚙️ [Portfolio Engine](index.md) — full mathematical model
- 📈 [Performance Metrics Overview](../index.md) — all performance metrics at a glance
