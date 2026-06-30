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

## 📐 6. Three-Pool Cash Model $(K, R, W)$

Three accumulator pools track cash provenance:

| Pool | Meaning |
|------|---------|
| $K$ | Capital Pool — external capital still in system |
| $R$ | Returns Pool — generated returns still in system |
| $W$ | Withdrawn Returns — returns that left (hidden) |

### Update rules (per-transaction, chronological)

**DEPOSIT** $D > 0$:

$$
r = \min(D, W), \quad R \mathrel{+}= r, \quad W \mathrel{-}= r, \quad K \mathrel{+}= D - r
$$

**WITHDRAWAL** $X > 0$:

$$
k = \min(X, K), \quad K \mathrel{-}= k
$$

$$
\rho = \min(X - k,\ R), \quad R \mathrel{-}= \rho, \quad W \mathrel{+}= \rho
$$

**DIVIDEND / INTEREST** $I > 0$:

$$
R \mathrel{+}= I
$$

**FEE / TAX** $F > 0$:

$$
R \mathrel{-}= F, \quad \text{if } R < 0: \ K \mathrel{+}= R,\ R = 0
$$

**BUY** $B > 0$:

$$
\rho = \min(B, R), \quad R \mathrel{-}= \rho, \quad K \mathrel{-}= (B - \rho)
$$

**SELL** (proceeds $P$, cost basis $C = |q_{\text{sold}}| \cdot w_{\text{pre}}$):

!!! warning "Critical"

    $C$ must be computed **before** the WAC pool is reduced.

$$
G = P - C, \quad K \mathrel{+}= C, \quad R \mathrel{+}= G
$$

$$
\text{if } R < 0: \quad K \mathrel{+}= R, \quad R = 0
$$

### Reconciliation invariant

$$
\mathrm{Cash}_{\text{like}}(t) \approx K(t) + R(t)
$$

Proportional scaling applied if drift $> 0.01$ (from FX rounding or in-transit timing).

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
