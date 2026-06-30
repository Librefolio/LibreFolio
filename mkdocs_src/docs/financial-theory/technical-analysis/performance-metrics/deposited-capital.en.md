# 💸 Deposited Capital, Total PnL and Cash Pools

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 Concept Overview

**Deposited Capital** = cumulative net external capital contributed since inception:

$$
\mathrm{DepCap}(t) = \sum_{\tau \leq t} D(\tau) - \sum_{\tau \leq t} W(\tau)
$$

**Total PnL** = all value generated above external contributions:

$$
\boxed{\mathrm{TotalPnL}(t) = \mathrm{NAV}(t) - \mathrm{DepCap}(t)}
$$

---

## 🎯 What Counts

| Transaction | Effect on DepCap |
|------------|-----------------|
| DEPOSIT / WITHDRAWAL (unlinked) | ✅ Yes |
| CASH\_TRANSFER linked-external | ✅ Yes |
| CASH\_TRANSFER linked-internal | ❌ No |
| BUY, SELL, DIVIDEND, INTEREST, FEE, TAX | ❌ No |

---

## 📊 Three-Pool Cash Model

The Growth Chart decomposes current cash into two visible pools $(K, R)$ plus a hidden tracker $(W)$:

$$
\mathrm{Cash}(t) \approx K(t) + R(t)
$$

| Pool | Meaning |
|------|---------|
| $K$ | Capital Pool — external capital still in system |
| $R$ | Returns Pool — generated returns still in system |
| $W$ | Withdrawn Returns — returns that left (hidden, for restore on re-deposit) |

!!! info "DepCap ≠ K"

    $\mathrm{DepCap}$ = historical sum of all flows (monotonic on deposits). $K$ = how much of current cash is external capital. They diverge after BUY/SELL.

🔗 Full update rules: **[Portfolio Engine — §6 Three-Pool Model](portfolio-engine.md#6-three-pool-cash-model-k-r-w)**

---

## 📝 Worked Examples

### A — Deposit → Buy → Sell in Gain

| Step | Tx | $K$ | $R$ | Cash |
|------|----|-----|-----|------|
| 1 | DEPOSIT €1,000 | 1,000 | 0 | 1,000 |
| 2 | BUY €1,000 | 0 | 0 | 0 |
| 3 | SELL P=€1,200, C=€1,000 | 1,000 | 200 | 1,200 |

TotalPnL = 1,200 − 1,000 = **+€200** ✓

### B — Dividend then Withdrawal

| Step | Tx | $K$ | $R$ | $W$ | Cash |
|------|----|-----|-----|-----|------|
| 1 | DEPOSIT €1,000 | 1,000 | 0 | 0 | 1,000 |
| 2 | DIVIDEND €50 | 1,000 | 50 | 0 | 1,050 |
| 3 | WITHDRAWAL €100 (K first) | 900 | 50 | 0 | 950 |
| 4 | WITHDRAWAL €950 (K=900→0, R=50→0, W+=50) | 0 | 0 | 50 | 0 |
| 5 | RE-DEPOSIT €30 (restore min(30,W=50)=30) | 0 | 30 | 20 | 30 |

After step 5: Cash=30, K=0, R=30 ✓ (returns restored from W)

### C — Full Sell Regression

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

🔗 See **[Portfolio Engine — §6](portfolio-engine.md#6-three-pool-cash-model-k-r-w)** for all formal rules.

---

## 🔗 Related

- 💼 [NAV](nav.md) — the other term in Total PnL
- 📊 [Period PnL](period-pnl.md) — windowed version
- ⚙️ [Portfolio Engine](portfolio-engine.md) — full mathematical model
