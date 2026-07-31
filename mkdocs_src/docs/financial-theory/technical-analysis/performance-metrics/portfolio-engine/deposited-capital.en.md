# 💸 Deposited Capital, Total PnL and Cash Pools

*[⬅️ Back to Performance Metrics Overview](../index.md)*

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

`InKindCapital` covers priced ADJUSTMENT / TRANSFER rows carrying `cost_basis_override` with no `asset_event_id` (not split rows). These rows inject book value without cash, so they must increase invested capital.

---

## 🎯 What Counts

| Transaction | Effect on capital baseline |
|------------|-----------------|
| DEPOSIT / WITHDRAWAL (unlinked) | ✅ Yes |
| CASH\_TRANSFER linked-external | ✅ Yes |
| CASH\_TRANSFER linked-internal | ❌ No |
| ADJUSTMENT / TRANSFER with `cost_basis_override`, no `asset_event_id` | ✅ Yes, in-kind capital |
| SPLIT-linked ADJUSTMENT | ❌ No, quantity rescale only |
| BUY, SELL, DIVIDEND, INTEREST, FEE, TAX | ❌ No |

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
    - Cash transfers between brokers move $R$ and $K$ from source to destination without touching $W$.

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

---

## ⚙️ Implementation

The 3-pool model runs in a **single per-transaction loop** (event-driven, not daily-delta):

1. Read WAC before pool mutation
2. Update K/R/W per transaction type rules
3. Then reduce WAC pool (for SELLs)

The ROI/TWRR/MWRR input series is derived from day-over-day changes in `cumulative_external_cash_flow`, the capital baseline. It is not derived from the cash-only `external_cash_flow` field.

🔗 See **[Portfolio Engine — §6](index.md#6-three-pool-cash-model-per-broker-k_b-r_b-w)** for all formal rules.

---

## 🔗 Related

- 💼 [NAV](nav.md) — the other term in Total PnL
- 📊 [Period PnL](period-pnl.md) — windowed version
- ⚙️ [Portfolio Engine](index.md) — full mathematical model
