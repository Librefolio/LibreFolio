# ⚙️ Portfolio Engine — Mathematical Model

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 Overview

This page formally defines the mathematical model underlying LibreFolio's portfolio calculation engine. All other metric pages ([NAV](nav.md), [Book Value](book-value.md), [Period P&L](period-pnl.md), [WAC](weighted-average-cost.md), [Deposited Capital](deposited-capital.md)) reference this page for their precise computation rules.

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

## 📐 2. Valuation Price

$$
p(a, t) = \begin{cases}
p_{\text{mkt}}(a, t) & \text{if PriceHistory} \leq t \text{ exists} \\
p_{\text{buy}}(a, t) & \text{if last BUY from } V(u) \text{ exists} \\
\varnothing & \text{otherwise (excluded from NAV)}
\end{cases}
$$

- $p_{\text{mkt}}$ = backward-fill from PriceHistory (latest close with date $\leq t$)
- $p_{\text{buy}}$ = unit price of most recent BUY of $a$ across all brokers in $V(u)$, with date $\leq t$
- WAC is **never** used as valuation price

---

## 📐 3. Position State

For each position $(a, b)$ with $q(a,b,t) > 0$:

$$
\mathrm{MV}(a,b,t) = q(a,b,t) \cdot p(a,t) \cdot \mathrm{fx}\bigl(\mathrm{ccy}_p, C^*, t\bigr)
$$

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \cdot w(a,b,t) \cdot \mathrm{fx}\bigl(\mathrm{ccy}_w, C^*, t\bigr)
$$

$$
\mathrm{UGL}(a,b,t) = \mathrm{MV}(a,b,t) - \mathrm{CB}(a,b,t)
$$

Where $w(a,b,t)$ is the [Weighted Average Cost](weighted-average-cost.md) for position $(a,b)$ at date $t$.

---

## 📐 4. WAC Iterative Update

Maintained per-position $(a,b)$ with pool state $(\hat{q}, \hat{c})$:

**Acquisition** (qty $> 0$, unit cost $u$):

$$
\hat{q}_{\text{new}} = \hat{q} + q_{\text{tx}}, \quad
\hat{c}_{\text{new}} = \hat{c} + u \cdot q_{\text{tx}}, \quad
w = \frac{\hat{c}_{\text{new}}}{\hat{q}_{\text{new}}}
$$

**Reduction** (qty $< 0$):

$$
w_{\text{pre}} = \frac{\hat{c}}{\hat{q}}, \quad
\hat{q}_{\text{new}} = \hat{q} - |q_{\text{tx}}|, \quad
\hat{c}_{\text{new}} = \hat{q}_{\text{new}} \cdot w_{\text{pre}}
$$

!!! info "Ordering"

    Within the same date: additions processed before reductions. Ensures SELL reads the correct WAC including same-day BUYs.

---

## 📐 5. Portfolio Aggregation

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

---

## 📐 6. Three-Pool Cash Model — Per-Broker $(K_b, R_b, W)$

Three accumulator pools track cash provenance. $K$ and $R$ are maintained **per-broker** $b$; $W$ is global (exits the system entirely).

| Pool | Scope | Meaning |
|------|-------|---------|
| $K_b$ | Per-broker | External capital still in broker $b$ as cash |
| $R_b$ | Per-broker | Generated returns still in broker $b$ as cash |
| $W$ | Global | Returns that left the system (hidden, restorable on re-deposit) |

!!! info "Key property"

    A BUY on broker $b_1$ can only consume $R_{b_1}$, never $R_{b_2}$. Cash does not teleport between brokers — only explicit transfers move pool balances.

### Update rules (per-transaction on broker $b$, chronological)

| Icon & Type | Update Formulas | Logic & Description |
|:---:|---|---|
| ![](../../../static/icons/transactions/deposit.png){: width="24" }<br>**DEPOSIT**<br>$D > 0$ | $r = \min(D,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= D - r$ | Restores previously withdrawn returns from the global tracker $W$ first, then adds the remainder to capital $K_b$. |
| ![](../../../static/icons/transactions/withdrawal.png){: width="24" }<br>**WITHDRAWAL**<br>$X > 0$ | $k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$<br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Consumes capital $K_b$ first, then moves remaining returns $\rho$ to the global tracker $W$. |
| ![](../../../static/icons/transactions/dividend.png){: width="24" } ![](../../../static/icons/transactions/interest.png){: width="24" }<br>**DIVIDEND / INTEREST**<br>$I > 0$ | $R_b \mathrel{+}= I$ | Yields directly increase the returns pool $R_b$. |
| ![](../../../static/icons/transactions/fee.png){: width="24" } ![](../../../static/icons/transactions/tax.png){: width="24" }<br>**FEE / TAX**<br>$F > 0$ | $R_b \mathrel{-}= F$<br>$\text{if } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0$ | Consumes returns $R_b$ first; if $R_b$ becomes negative, it drains from capital $K_b$. |
| ![](../../../static/icons/transactions/buy.png){: width="24" }<br>**BUY**<br>$B > 0$ | $\rho = \min(B,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$K_b \mathrel{-}= (B - \rho)$ | Consumes returns $R_b$ first, then drains the rest from capital $K_b$. |
| ![](../../../static/icons/transactions/sell.png){: width="24" }<br>**SELL** | $G = P - C$<br>$K_b \mathrel{+}= C$<br>$R_b \mathrel{+}= G$<br>$\text{if } R_b < 0\text{: } K_b \mathrel{+}= R_b, \quad R_b = 0$ | Cost basis $C = |q_s| \cdot w_{\text{pre}}$ returns to capital $K_b$; gain $G$ goes to returns $R_b$ (if $G < 0$, it behaves like a fee).<br><br>!!! warning "Critical ordering"<br><br>    $C$ must be computed **before** the WAC pool is reduced (full-sell would give $C = 0$ otherwise). |
| ![](../../../static/icons/transactions/cash-transfer.png){: width="24" }<br>**CASH TRANSFER**<br>(Internal, $s \to d$, $X > 0$) | **Departure Leg ($s$):**<br>$\rho = \min(X,\, R_s)$<br>$R_s \mathrel{-}= \rho$<br>$\kappa = X - \rho$<br>$K_s \mathrel{-}= \kappa$<br><br>**Arrival Leg ($d$):**<br>$K_d \mathrel{+}= \kappa$<br>$R_d \mathrel{+}= \rho$ | Internal cash transfers move pool allocations ($R_s \to R_d$, $K_s \to K_d$) proportional to the departure balance.<br>The global tracker $W$ is **never** touched (capital remains inside the system). |

If departure and arrival dates differ, the transfer is in-transit: subtracted from $s$ at departure day, added to $d$ at arrival day. Between those dates, $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$ by the in-transit amount — handled by proportional reconciliation.

### Aggregation for output

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t)
$$

$$
\mathrm{CashFromReturns}(t) = \sum_{b \in S} R_b(t)
$$

### Reconciliation invariant

$$
\mathrm{Cash}_{\text{like}}(t) \approx \sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)
$$

Proportional per-broker scaling applied if drift $> 0.01$ (from FX rounding or in-transit timing).

---

## 📐 7. Period Contribution

For period $[t_0, t_1]$, per-position $(a,b)$:

$$
\Delta\mathrm{UGL}(a,b) = \mathrm{UGL}(a,b,t_1) - \mathrm{UGL}(a,b,t_0)
$$

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{Fees}(a,b)
$$

Contribution position set:

$$
\mathcal{P} = \mathcal{P}(t_0) \cup \mathcal{P}(t_1) \cup \mathrm{keys}(\text{Realized}) \cup \mathrm{keys}(\text{Income}) \cup \mathrm{keys}(\text{Fees})
$$

Unallocated (fees/income without `asset_id`) grouped per broker.

---

## 📐 8. Realized Gain/Loss

On SELL of $|q_s|$ units from position $(a,b)$:

$$
C = |q_s| \cdot w_{\text{pre}}(a,b) \cdot \mathrm{fx}(\mathrm{ccy}_w, C^*, t)
$$

$$
\mathrm{Realized} = P_{\text{sell}} - C
$$

Where $w_{\text{pre}}$ is the WAC **before** the pool reduction (same value used by 3-pool SELL rule above).

---

## 📐 9. Pre-Frame / Frame Architecture

| Phase | Date range | Computes |
|-------|-----------|----------|
| Pre-frame | $[t_{\mathrm{first}},\ t_0)$ | Cash, qty, WAC, pools — no market evaluation |
| Frame | $[t_0,\ t_1]$ | Full daily: prices, FX, position states, portfolio states |

Pre-frame transactions update accumulators (cash ledger, WAC pools, 3-pool K/R/W) without consuming price or FX data. This enables efficient range-based caching.

---

## 📐 10. Performance Metrics (Layer 2)

Computed **after** daily states, as a separate pass:

| Metric | Formula | Reference |
|--------|---------|-----------|
| Total PnL | $\mathrm{NAV}(t) - \text{DepositedCapital}(t)$ | [Deposited Capital](deposited-capital.md) |
| Period PnL | $\mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \text{ECF}_{[t_0,t_1]}$ | [Period P&L](period-pnl.md) |
| TWRR | $\prod_i (1 + r_i) - 1$ (sub-period chain) | [TWRR](twrr.md) |
| MWRR | XIRR solving $\sum \frac{CF_i}{(1+r)^{d_i/365}} = 0$ | [MWRR](mwrr.md) |
| Simple ROI | $(\mathrm{NAV} - \text{NetInvested}) / \text{NetInvested}$ | [ROI](roi.md) |
| Timing Effect | $\text{MWRR}_{\text{cum}} - \text{TWRR}_{\text{cum}}$ | [Timing Effect](timing-effect.md) |

---

## 🔗 Related

- 💼 [NAV](nav.md) — snapshot valuation
- 📖 [Book Value](book-value.md) — cost basis aggregate
- 📊 [Period P&L](period-pnl.md) — windowed gain/loss with contribution
- 💸 [Deposited Capital](deposited-capital.md) — 3-pool details and worked examples
- 📈 [WAC](weighted-average-cost.md) — iterative cost method
