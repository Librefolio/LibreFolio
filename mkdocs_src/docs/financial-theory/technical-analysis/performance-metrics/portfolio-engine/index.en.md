# ⚙️ Portfolio Engine — Mathematical Model

## 💡 Overview

This page formally defines the mathematical model underlying LibreFolio's portfolio calculation engine. All other metric pages ([NAV](nav.md), [Book Value](book-value.md), [Period P&L](period-pnl.md), [Yield on Cost](yield-on-cost.md), [WAC](../weighted-average-cost.md), [Deposited Capital](deposited-capital.md)) reference this page for their precise computation rules.

---

## 📐 1. Notation and Sets

| Symbol | Meaning |
|--------|---------|
| $V(u)$ | All brokers visible to user $u$ |
| $S \subseteq V(u)$ | Selected (filtered) broker scope |
| $A$ | Set of assets with positions |
| $C^*$ | Target currency |
| $[t_0, t_1]$ | Requested evaluation frame |
| $q(a,b,t)$ | Quantity of asset $a$ at broker $b$ on date $t$ |
| $p(a,t)$ | Valuation price of asset $a$ on date $t$ |
| $\mathrm{fx}(c_1, c_2, t)$ | Exchange rate from currency $c_1$ to $c_2$ on date $t$ |

---

## 📐 2. Valuation Price {: #2-valuation-price }

$$
\operatorname{mark}(a,t)=
\begin{cases}
\text{MARKET}(a,t) & \text{same-day asset-system quote}\\
\operatorname{avg}(\text{TRADE}(a,t)) & \text{same-day BUY/SELL observations}\\
\text{last observation before }t & \text{carried forward (LOCF)}\\
\varnothing & \text{no observation on or before }t
\end{cases}
$$

- The unified resolver is the single valuation brain: `MARKET → TRADE_AVG → CARRIED → MISSING`.
- Only market quotes and BUY/SELL trades are observations. An ADJUSTMENT never is, incoming or outgoing, with or without a cost basis: its cost basis is a cost, not what the asset was worth that day.
- `CARRIED` is last-observation-carried-forward. It carries `days_back` staleness metadata.
- `estimated=True` means TRADE-origin. A stale carried MARKET quote is stale, not estimated.
- Marks stay in native currency; each consumer converts to $C^*$ at valuation date $t$.
- Cost-basis FX remains pinned to the transaction date.
- Cash stays in the currency it was recorded in, broker by broker, and is valued at the rate of $t$ (§5); each cash movement is still booked, and each external cash flow enters the capital, at the rate of its own date.
- WAC is **never** used as valuation price. A position whose asset has no mark at all ($\varnothing$) is counted at its cost basis instead, as a declared estimate, not a price (§3).

See [Price Resolution](price-resolution.md) for the resolver contract and data-quality semantics.

---

## 📐 3. Position State {: #3-position-state }

For each position $(a, b)$ with $q(a,b,t) > 0$:

$$
\mathrm{MV}(a,b,t) =
\begin{cases}
\dfrac{q(a,b,t)}{qbq(a)}\cdot \operatorname{mark}(a,t)\cdot \mathrm{fx}\bigl(\mathrm{ccy}_{mark}, C^*, t\bigr) & \operatorname{mark}(a,t) \neq \varnothing\\
\mathrm{CB}(a,b,t) & \operatorname{mark}(a,t) = \varnothing \text{ and the cost of } (a,b) \text{ is complete}
\end{cases}
$$

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \cdot w(a,b,t)
$$

$$
\mathrm{UGL}(a,b,t) = \mathrm{MV}(a,b,t) - \mathrm{CB}(a,b,t)
$$

Where $w(a,b,t)$ is the [Weighted Average Cost](../weighted-average-cost.md) for position $(a,b)$ at date $t$, kept in $C^*$ at historical rates (§4): the cost basis takes no exchange rate at $t$, so for a foreign asset the exchange-rate effect is part of $\mathrm{UGL}$.

The second case covers an asset with no observation yet — no quote, no BUY or SELL on or before $t$, as for a holding received through adjustments or transfers. The position is valued at its cost basis, valuation source `ESTIMATED_AT_COST`: a declared estimate, not a price. It reports no unit price, it does not move with exchange rates, and its $\mathrm{UGL}$ is zero, with neither a price effect nor an exchange-rate effect. The choice is made day by day, with no look-ahead: from the first observation on, the mark wins, even an old one carried forward. A position whose cost is incomplete (§4) has no market value on such a day (`MISSING`) and is left out of $\mathrm{MV}(t)$. The valuation sources therefore rank `MARKET_PRICE` > `LAST_TRADE_PRICE` > `ESTIMATED_AT_COST` > `MISSING` ([Price Resolution](price-resolution.md)).

---

## 📐 4. WAC Iterative Update

Maintained per-position $(a,b)$ with pool state $(\hat{q}, \hat{c})$, the cost $\hat{c}$ kept in $C^*$:

**Acquisition** (qty $> 0$, amount $P$ paid in currency $c$ on date $d$):

$$
\hat{q}_{\text{new}} = \hat{q} + q_{\text{tx}}, \quad
\hat{c}_{\text{new}} = \hat{c} + P \cdot \mathrm{fx}(c, C^*, d), \quad
w = \frac{\hat{c}_{\text{new}}}{\hat{q}_{\text{new}}}
$$

$P$ is the cash paid for a BUY, or the per-unit cost basis override times $q_{\text{tx}}$ for a TRANSFER or ADJUSTMENT; $\mathrm{fx}(C^*, C^*, d) = 1$. When no rate exists on or before $d$, or the acquisition has no cost basis, the quantity enters and the cost does not: the position's cost is flagged incomplete instead of counting zero.

**Reduction** (qty $< 0$):

$$
w_{\text{pre}} = \frac{\hat{c}}{\hat{q}}, \quad
\hat{q}_{\text{new}} = \hat{q} - |q_{\text{tx}}|, \quad
\hat{c}_{\text{new}} = \hat{q}_{\text{new}} \cdot w_{\text{pre}}
$$

**Split** (linked to a split event): $\hat{q}$ changes, $\hat{c}$ does not.

!!! info "Ordering"

    Within the same date: additions processed before reductions. Ensures SELL reads the correct WAC including same-day BUYs.

---

## 📐 5. Portfolio Aggregation {: #5-portfolio-aggregation }

$$
\mathrm{MV}(t) = \sum_{(a,b) \in S} \mathrm{MV}(a,b,t)
$$

$$
\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)
$$

$$
\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)
$$

$$
\mathrm{UGL}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

$\mathrm{Cash}(t)$ is each broker's cash, kept in the currencies it was recorded in and valued at the rate of $t$:

$$
\mathrm{Cash}(t) = \sum_{b \in S} \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t)
$$

where $N_{b,c}(t)$ is the balance of broker $b$ in currency $c$ after its movements dated on or before $t$, scaled by the broker's [ownership share](../../../../user/brokers/sharing.md), and $\mathrm{fx}(c, C^*, t)$ is the latest rate on or before $t$ ($1$ for $c = C^*$). The same term is in NAV and in Book, so the exchange-rate effect on cash cancels in UGL: it is booked as an exchange result (§6) and belongs to the Total P&L.

### 🔀 Two Unrealized Figures {: #two-unrealized-figures }

$\mathrm{InTransit}(t)$ and $\mathrm{InTransitBook}(t)$ hold the same cash in transit, and the securities travelling between two brokers of $S$ at market value, $\mathrm{MV}^{\mathrm{tr}}(t)$, in the first and at historical cost, $\mathrm{CB}^{\mathrm{tr}}(t)$, in the second. Cash cancels, so with $\mathrm{OCB}(t)$ the cost basis of the positions held (§3):

$$
\mathrm{UGL}(t) = \bigl[\mathrm{MV}(t) - \mathrm{OCB}(t)\bigr] + \bigl[\mathrm{MV}^{\mathrm{tr}}(t) - \mathrm{CB}^{\mathrm{tr}}(t)\bigr]
$$

The engine reports two unrealized figures:

| Figure | Definition | Where it shows |
|--------|-----------|----------------|
| Portfolio unrealized | $\mathrm{UGL}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)$, securities in transit included | `unrealized_gain_loss` of the portfolio report's summary and history points (`POST /portfolio/report`) and of the AI Export portfolio and broker summaries; [Book Value — Unrealized](book-value.md) |
| Period unrealized | $\mathrm{MV}(t) - \mathrm{OCB}(t)$ at each period boundary, positions held only | `period_unrealized_gain_loss_start`, `_end`, `_delta` and their split by currency; the Dashboard's **Unrealized change**; the $\Delta\mathrm{UGL}$ of [Period P&L](period-pnl.md) and the per-position rows of §7 |

They differ only by the securities in transit: on a day when none is travelling, they are equal. A security in transit on a period boundary is in NAV, so in the period P&L, but in no position's state: its part of the result is in the residual of §7, not in $\Delta\mathrm{UGL}$.

---

## 📐 6. Three-Pool Cash Model — Per-Broker $(K_b, R_b, W)$ {: #6-three-pool-cash-model-per-broker-k_b-r_b-w }

Three accumulator pools track cash provenance. $K$ and $R$ are maintained **per-broker** $b$; $W$ is global (exits the system entirely).

| Pool | Scope | Meaning |
|------|-------|---------|
| $K_b$ | Per-broker | External capital still in broker $b$ as cash |
| $R_b$ | Per-broker | Generated returns still in broker $b$ as cash |
| $W$ | Global | Returns that left the system (hidden, restorable on re-deposit) |

!!! info "Key property"

    A BUY on broker $b_1$ can only consume $R_{b_1}$, never $R_{b_2}$. Cash does not teleport between brokers — only explicit transfers move pool balances.

### 🔁 Update rules (per-transaction on broker $b$, chronological)

| Icon & Type | Update Formulas | Logic & Description |
|:---:|---|---|
| ![](../../../../static/icons/transactions/deposit.png){: width="24" }<br>**DEPOSIT**<br>$D > 0$ | $r = \min(D,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= D - r$ | Restores previously withdrawn returns from the global tracker $W$ first, then adds the remainder to capital $K_b$. |
| ![](../../../../static/icons/transactions/withdrawal.png){: width="24" }<br>**WITHDRAWAL**<br>$X > 0$ | $k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$<br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Consumes capital $K_b$ first, then moves remaining returns $\rho$ to the global tracker $W$. |
| ![](../../../../static/icons/transactions/dividend.png){: width="24" } ![](../../../../static/icons/transactions/interest.png){: width="24" }<br>**DIVIDEND / INTEREST**<br>$I > 0$ | $R_b \mathrel{+}= I$ | Yields directly increase the returns pool $R_b$. |
| ![](../../../../static/icons/transactions/fee.png){: width="24" } ![](../../../../static/icons/transactions/tax.png){: width="24" }<br>**FEE / TAX**<br>$F > 0$ | $R_b \mathrel{-}= F$<br>$\text{if } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0$ | Consumes returns $R_b$ first; if $R_b$ becomes negative, it drains from capital $K_b$. |
| ![](../../../../static/icons/transactions/buy.png){: width="24" }<br>**BUY**<br>$B > 0$ | $\rho = \min(B,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$K_b \mathrel{-}= (B - \rho)$ | Consumes returns $R_b$ first, then drains the rest from capital $K_b$. |
| ![](../../../../static/icons/transactions/sell.png){: width="24" }<br>**SELL** | $G = P - C$<br>$K_b \mathrel{+}= C$<br>$R_b \mathrel{+}= G$<br>$\text{if } R_b < 0\text{: } K_b \mathrel{+}= R_b, \quad R_b = 0$ | Cost basis $C = |q_s| \cdot w_{\text{pre}}$ returns to capital $K_b$; gain $G$ goes to returns $R_b$ (if $G < 0$, it behaves like a fee).<br><br>!!! warning "Critical ordering"<br><br>    $C$ must be computed **before** the WAC pool is reduced (full-sell would give $C = 0$ otherwise). |
| ![](../../../../static/icons/transactions/cash-transfer.png){: width="24" } ![](../../../../static/icons/transactions/fx-conversion.png){: width="24" }<br>**CASH TRANSFER / FX CONVERSION**<br>(Internal, $s \to d$, $X > 0$ leaves, $Y > 0$ arrives) | **Departure Leg ($s$):**<br>$\rho = \min(X,\, R_s)$<br>$R_s \mathrel{-}= \rho$<br>$\kappa = X - \rho$<br>$K_s \mathrel{-}= \kappa$<br><br>**Arrival Leg ($d$):**<br>$K_d \mathrel{+}= \kappa$<br>$R_d \mathrel{+}= \rho + (Y - X)$<br>$\text{if } R_d < 0\text{: } K_d \mathrel{+}= R_d,\; R_d = 0$ | The departure takes returns $R_s$ first, then capital $K_s$. The arrival brings back what the departure took from each pool. $X$ and $Y$ are in $C^*$ at the rate of each leg's own date, each weighted by its broker's ownership share, so they can differ: a conversion's spread against the reference rate, the rate move while the cash travels, two brokers owned at different shares. Neither leg is an external flow, so the capital baseline does not move and Total P&L already counts the gap $Y - X$: it is a **result**, booked like the [exchange result on cash at rest](#exchange-result-on-foreign-cash) — a gain to the returns, a loss out of the returns first and then of the capital, as a FEE. With $Y = X$: $K_d \mathrel{+}= \kappa$, $R_d \mathrel{+}= \rho$.<br>An FX CONVERSION has both legs at the same broker ($s = d$), in two currencies.<br>The global tracker $W$ is **never** touched (capital remains inside the system). |

For example, with $C^* = \mathrm{EUR}$, a broker with $K = 1000$, $R = 300$ converts 650 EUR into 715 USD at a reference rate of 0.92 EUR per USD ($Y = 657.80$): afterwards $K = 1000$ and $R = 307.80$ — the capital still equals what was deposited, and the 7.80 spread is a result. Between brokers owned at different shares, $A$ at 100 % sending 400 to $B$ at 50 % gives $X = 400$, $Y = 200$: a loss of 200, out of the returns first.

Each departure records its split $(\rho, X)$ until its arrival takes it up, once. An arrival whose departure is unknown — no recorded split, or $X = 0$ — goes entirely to $K_d$. When both legs fall on the same day, the arrival is applied after that day's other movements, whatever their transaction ids, so it always finds its departure's split. A transfer or conversion whose other leg is outside $S$ is not internal and does not follow this rule.

If departure and arrival dates differ, the transfer is in-transit: subtracted from $s$ at departure day, added to $d$ at arrival day. Between those dates, $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$ by the in-transit amount — the reconciliation below reads that cash with the pools' current mix until the arrival brings back the departure's split.

### 💱 Exchange Result on Foreign Cash {: #exchange-result-on-foreign-cash }

Each cash movement enters the broker's cash, and its pools, at the rate of its own date; the balance held afterwards follows the rate (§5). On every day $t$ on which the rate of a foreign currency held as cash in $S$ changes — its first known rate included — after that day's cash movements and before that day's transactions update the pools, each broker $b$ holding foreign cash is revalued:

$$
\varepsilon_b(t) = \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t) - \mathrm{Cash}^{\text{replay}}_b(t)
$$

$$
\mathrm{Cash}^{\text{replay}}_b \mathrel{+}= \varepsilon_b, \qquad
R_b \mathrel{+}= \varepsilon_b, \qquad
\text{if } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0
$$

$\mathrm{Cash}^{\text{replay}}_b(t)$ is the cash the replay carries for $b$: its value at the previous revaluation plus every later movement at the rate of its own date. A gain goes to the returns; a loss consumes them first and then the capital, exactly like a FEE. The capital baseline does not move: an exchange result is a result, not a contribution, so it is in NAV, Total P&L, ROI, TWRR and MWRR, never in the deposited capital.

### 🧮 Aggregation for output

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t)
$$

$$
\mathrm{CashFromReturns}(t) = \sum_{b \in S} R_b(t)
$$

### ⚖️ Reconciliation invariant

$$
\mathrm{Cash}_{\text{like}}(t) \approx \sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)
$$

Both pools are first clamped at zero per broker. If the pools are not empty and the drift still exceeds $0.01$, the **summed** pools are scaled to $\mathrm{Cash}_{\text{like}}$, the cash plus the cash in transit — an aggregate scaling, not a per-broker one, each result floored at zero:

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t) \cdot \frac{\mathrm{Cash}_{\text{like}}(t)}{\sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)}, \qquad
\mathrm{CashFromReturns}(t) = \mathrm{Cash}_{\text{like}}(t) - \mathrm{CashFromCapital}(t)
$$

Otherwise $\mathrm{CashFromCapital}(t) = \min\bigl(\sum_b K_b(t),\, \mathrm{Cash}_{\text{like}}(t)\bigr)$ and $\mathrm{CashFromReturns}$ is the rest, floored at zero. The exchange results on cash at rest are booked into the pools (above); the scaling absorbs two drifts:

- **Cash in transit.** The departure has left the pools, while $\mathrm{Cash}_{\text{like}}$ still counts the cash in transit — and the move of its exchange rate while it travels — so $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$. Until the arrival, the scale reads that cash with the pools' current mix. A broker with $K = 1000$, $R = 300$ sends $650$ in $C^*$ to an empty broker of $S$: it keeps $K = 650$, $R = 0$, the scale is $1300 / 650 = 2$, so $\mathrm{CashFromCapital} = 1300$ and $\mathrm{CashFromReturns} = 0$ during the transit. On arrival the split comes back: $1000$ and $300$.
- **Negative cash (overdraft).** Both pools are clamped at zero per broker, so a broker whose cash goes below zero leaves pools that no longer sum to its cash — also on the following days, since the clamped values are kept.

---

## 📐 7. Period Contribution {: #7-period-contribution }

For period $[t_0, t_1]$, per-position $(a,b)$:

$$
\Delta\mathrm{UGL}(a,b) = \mathrm{UGL}(a,b,t_1) - \mathrm{UGL}(a,b,t_0) + T(a,b)
$$

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

Contribution position set:

$$
\mathcal{P} = \text{positions with BUY/SELL/ADJUSTMENT/TRANSFER activity or boundary quantity}
$$

$\mathrm{UGL}(a,b,t)$ is the position state of §3 at the end of day $t$, the one the portfolio aggregates (§5): the mark of §2 — a trade-derived mark restated through any later split —, the cost basis when the asset has no mark at all, the exchange rate of $t$ itself. A position not held on $t$ counts 0. A position held on $t$ whose $\mathrm{UGL}(a,b,t)$ is unknown — no rate, an incomplete cost — makes $\Delta\mathrm{UGL}(a,b)$ unknown, never the known side minus zero. When every row is known, the rows add up to the portfolio's change, that of the positions held — the period unrealized of [§5](#two-unrealized-figures), securities in transit left out:

$$
\sum_{(a,b) \in \mathcal{P}} \Delta\mathrm{UGL}(a,b) = \Delta\mathrm{UGL} = \bigl[\mathrm{MV}(t_1) - \mathrm{OCB}(t_1)\bigr] - \bigl[\mathrm{MV}(t_0) - \mathrm{OCB}(t_0)\bigr]
$$

Dust aside: a row counts a position holding $10^{-5}$ units or fewer as not held — no value, no unrealized of its own —, while the portfolio state of §3 values every quantity above zero. The unrealized change of such a residual is in $\Delta\mathrm{UGL}$ and in no row (MF-A6).

**Internal transfers.** $T(a,b)$ splits the result of a security moved between two brokers of $S$: each broker answers for its own stretch. For each linked TRANSFER of $a$ from broker $s$ to broker $d$ that departs after $t_0$ and arrives on or before $t_1$, with $V$ the value of the moved units on the arrival day (§3) and $C$ the historical cost the sender's pool gave up for them (§4):

$$
T(a,s) \mathrel{+}= V - C, \qquad T(a,d) \mathrel{-}= V - C
$$

The sender answers for the units until they arrive, transit included, the receiver from their arrival; the terms cancel, so the total is unchanged. A transfer already in transit at $t_0$, still in transit at $t_1$, or with $V$ or $C$ unknown adds nothing: the boundary values stand.

??? example "Example: 10 units moved from broker A to broker B"

    A holds 10 units bought at 80 ($C = 800$). The price is 100 at $t_0$, 120 on the day they move to B ($V = 1{,}200$), 150 at $t_1$:

    $$
    \Delta\mathrm{UGL}(a,A) = 0 - (1{,}000 - 800) + (1{,}200 - 800) = +200
    $$

    $$
    \Delta\mathrm{UGL}(a,B) = (1{,}500 - 800) - 0 - (1{,}200 - 800) = +300
    $$

    A answers for 100 → 120, B for 120 → 150: +500 in all, the portfolio's $\Delta\mathrm{UGL}$ ($700 - 200$). Without $T$, A would show −200 and B +700.

Portfolio-level period P&L also exposes a residual:

$$
\mathrm{Other} =
\mathrm{PnL}_{period} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Since UGL cannot contain the exchange result on cash (§5), Other splits into each broker's exchange result over the period and what remains:

$$
\mathrm{Other} = \sum_{b \in S} \mathrm{FXonCash}_b + \mathrm{Residual}
$$

Unallocated fees/income without `asset_id` are grouped per broker as other period effects, and so is $\mathrm{FXonCash}_b$: one row per broker holding foreign cash, shown when its result is not zero. See [Period P&L — FX on Cash](period-pnl.md#fx-on-cash).

When every row is known, the rows and the other period effects together close $\mathrm{PnL}_{period}$. Since the rows are valued as the portfolio is, the residual holds no valuation difference between them, only what no position holds: what travels between two brokers, the cost of a currency exchange, a disposal left out of Realized.

---

## 📐 8. Realized Gain/Loss {: #8-realized-gain-loss }

On a disposal of $|q_s|$ units from position $(a,b)$ on date $t$ — a SELL, or an outgoing ADJUSTMENT with a cost basis:

$$
C = |q_s| \cdot w_{\text{pre}}(a,b)
$$

$$
\mathrm{Realized} = P \cdot \mathrm{fx}(c_P, C^*, t) - C
$$

$P$ is what the units leave for, in its currency $c_P$: a SELL's proceeds, in the currency of its cash; an outgoing ADJUSTMENT's value handed over, $|q_s| \cdot k$ for its per-unit cost basis $k$, in the cost basis's currency, or the asset's when the row has none. $w_{\text{pre}}$ is the WAC in $C^*$ **before** the pool reduction (same value used by 3-pool SELL rule above): the units leave at their historical cost, with no conversion at $t$, while $P$ converts at $t$. A disposal whose $P$ cannot be converted, or drawn from a position whose cost is incomplete, is left out of Realized.

An outgoing ADJUSTMENT moves no cash, so no pool of §6 changes: its value $P \cdot \mathrm{fx}(c_P, C^*, t)$ leaves the capital baseline instead, or $C$ when that value cannot be converted ([Deposited Capital — Outgoing Adjustments](deposited-capital.md#outgoing-adjustments)).

---

## 📐 9. One Daily Replay

| Range | Date range | Role |
|-------|-----------|------|
| Replay | $[\min(t_{\mathrm{first}},\ t_0),\ t_1]$ | Every day, with the same rules: cash, qty, WAC, pools, prices, FX, position and portfolio states |
| Frame | $[t_0,\ t_1]$ | The days whose states are returned |

There is one replay, from the first movement $t_{\mathrm{first}}$ (or $t_0$, when earlier) to $t_1$. A movement dated before $t_0$ follows the same rules as any other: it is converted at the rate of its own date and moves the WAC pools and the 3-pool K/R/W, and on every day the rate of a held foreign currency changes the cash is revalued and the exchange result enters the pools (§6). The states are returned from $t_0$, so a day's state does not depend on the frame it is read in. A day on which no term of the model changes — no movement, rate, quote, split, transit boundary or price turning stale — carries the previous day's state.

---

## 📐 10. Performance Metrics (Layer 2)

Computed **after** daily states, as a separate pass:

| Metric | Formula | Reference |
|--------|---------|-----------|
| Total PnL | $\mathrm{NAV}(t) - \text{CapitalBaseline}(t)$ | [Deposited Capital](deposited-capital.md) |
| Period PnL | $\mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \text{ECF}_{[t_0,t_1]}$ | [Period P&L](period-pnl.md) |
| TWRR | $\prod_i (1 + r_i) - 1$ (sub-period chain) | [TWRR](twrr.md) |
| MWRR | XIRR solving $\sum \frac{CF_i}{(1+r)^{d_i/365}} = 0$ | [MWRR](mwrr.md) |
| Simple ROI | $(\mathrm{NAV} - \text{NetInvested}) / \text{NetInvested}$ | [ROI](roi.md) |
| Net annualized return | $(1+r_{\mathrm{net}})^{365/d}-1$, suppressed below 30 days | [Net Annualized Return](net-annualized-return.md) |
| Yield on Cost | Trailing-365-day gross transaction income per eligible historical unit, divided by residual unit WAC at $t_1$ | [Yield on Cost](yield-on-cost.md) |
| Timing Effect | $\text{MWRR}_{\text{cum}} - \text{TWRR}_{\text{cum}}$ | [Timing Effect](timing-effect.md) |

---

## 🔗 Related

- 💼 [NAV](nav.md) — snapshot valuation
- 🧭 [Price Resolution](price-resolution.md) — unified valuation resolver
- 📈 [Net Annualized Return](net-annualized-return.md) — holdings, period, and FIFO CAGR definitions
- 💸 [Yield on Cost](yield-on-cost.md) — trailing gross recorded income relative to residual unit WAC
- 📖 [Book Value](book-value.md) — cost basis aggregate
- 📊 [Period P&L](period-pnl.md) — windowed gain/loss with contribution
- 💸 [Deposited Capital](deposited-capital.md) — 3-pool details and worked examples
- 📈 [WAC](../weighted-average-cost.md) — iterative cost method
- 📈 [Performance Metrics Overview](../index.md) — all performance metrics at a glance
