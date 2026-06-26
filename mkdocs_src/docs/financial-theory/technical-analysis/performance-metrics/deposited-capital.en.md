# 💸 Deposited Capital & Total P&L

*[⬅️ Back to Performance Metrics Overview](index.md)*

## 💡 Concept overview

**Deposited Capital** (also called *Capital Baseline* internally) is the net external capital you have contributed to your portfolio scope over time — your deposits minus your withdrawals. It is the anchor point for computing **Total P&L**.

$$
\text{Deposited Capital}(t) = \sum_{\tau \leq t} \text{Deposits}(\tau) - \sum_{\tau \leq t} \text{Withdrawals}(\tau)
$$

**Total P&L** is then the difference between what your portfolio is worth today and how much external capital you put in:

$$
\text{Total P}\&\text{L}(t) = \text{NAV}(t) - \text{Deposited Capital}(t)
$$

This is the most complete measure of *all the value your portfolio generated* — unrealized gains, realized gains, interest, dividends, minus all fees and taxes, since inception.

---

## 🔄 Relationship with Period P&L

[Period P&L](period-pnl.md) isolates the gain generated during a *selected window*:

$$
\text{Period P}\&\text{L} = \text{NAV}_{\text{end}} - \text{NAV}_{\text{start}} - \text{Net External Flows in period}
$$

**Total P&L** is the cumulative version — it starts from the very first transaction. In the Growth Chart tooltip, the **period delta** of Total P&L equals the Period P&L:

$$
\text{Period Delta} = \text{Total P}\&\text{L}(t_{\text{end}}) - \text{Total P}\&\text{L}(t_{\text{start}})
$$

---

## 🎯 What counts as Deposited Capital

Deposited Capital includes **only external flows** — money entering or leaving the selected portfolio scope from outside. Internal transfers between brokers within the same scope do not affect it.

| Transaction | Effect on Deposited Capital |
|------------|----------------------------|
| `DEPOSIT` (unlinked) | ✅ Increases |
| `WITHDRAWAL` (unlinked) | ✅ Decreases |
| `CASH_TRANSFER` linked-external (paired leg outside scope) | ✅ Increases/Decreases |
| `CASH_TRANSFER` linked-internal (both legs inside scope) | ❌ No effect |
| `BUY`, `SELL` | ❌ No effect |
| `INTEREST`, `DIVIDEND` | ❌ No effect — these are *returns*, not deposits |
| `FEE`, `TAX` | ❌ No effect |
| `FX_CONVERSION` linked-internal | ❌ No effect |

!!! example "Key insight"

    If you earn €100 in interest and then reinvest it, Deposited Capital stays flat. The interest shows up as an increase in Total P&L (+€100), because the portfolio is worth €100 more than what you put in.

    If you then **withdraw** that €100 as profit, Deposited Capital **decreases by €100** — but Total P&L stays the same (+€100), because the portfolio earned it before you took it out.

---

## 🧮 Deposited Capital vs. Net Deposited Capital (Card 1)

!!! warning "Two related but different values"

    The **dashboard Card 1** shows **Net Deposited Capital**, which is period-scoped (counts only deposits and withdrawals between `date_from` and `date_to`) and counts only pure `DEPOSIT`/`WITHDRAWAL` transactions.

    The **Growth Chart** shows **Deposited Capital** (capital_baseline), which is inception-to-date and also includes `CASH_TRANSFER` linked-external flows.

    The two values differ when:

    1. The selected period does not start at inception (older deposits are excluded from the card).
    2. The portfolio has linked cash transfers from outside the selected scope.

---

## 📊 Cash Decomposition

The Growth Chart's stacked areas break down the **current liquidity** into two components, answering the question: *"Is the cash I hold today from my deposits or from portfolio returns?"*

### The two pools

LibreFolio maintains two running accumulators per day — not persisted to the database, recalculated from the transaction log each time:

```
capital_cash_pool   — cash attributable to undeployed external capital
returns_cash_pool   — cash from portfolio returns (interest, dividends, realized gains)
```

### The delta-based algorithm

The key insight is that the **daily change in `book_asset_like`** (`open_cost_basis + in_transit_asset_cost_basis`) tells us exactly how much capital moved between cash and assets that day, without needing to inspect individual transactions:

- When `book_asset_like` **grows** → assets were purchased; cash was consumed
- When `book_asset_like` **shrinks** → assets were sold; the cost basis was returned to cash as principal

Each day, the pools update in this exact order:

**Step 1 — External cash flows** → `capital_cash_pool`

Any `DEPOSIT`, `WITHDRAWAL`, or `CASH_TRANSFER` linked to a broker outside the current scope updates `capital_cash_pool` directly:

```
capital_cash_pool += ecf_today
```

**Step 2 — Asset cost basis change** (`delta_assets = book_asset_like_today − book_asset_like_yesterday`)

```python
if delta_assets > 0:                    # Assets grew (BUY)
    from_returns = min(delta_assets, max(returns_cash_pool, 0))
    returns_cash_pool -= from_returns   # returns consumed first
    capital_cash_pool -= (delta_assets - from_returns)  # capital consumed second

elif delta_assets < 0:                  # Assets shrank (SELL)
    capital_cash_pool += abs(delta_assets)  # principal returns to capital
```

This implements the **"returns consumed first"** convention: when you buy an asset, portfolio income is assumed reinvested before external capital is touched.

**Step 3 — Residual cash delta** → `returns_cash_pool`

After accounting for external flows and asset movements, the remaining cash change on that day must come from portfolio activity (interest, dividends, fees, taxes, realized gain/loss on top of cost basis):

```
returns_delta = total_cash_delta_today − ecf_today + delta_assets
returns_cash_pool += returns_delta
```

The formula works because `total_cash_delta` = all signed amounts in the day; subtracting `ecf_today` removes the capital part; adding back `delta_assets` removes the asset-purchase/sale part (which was handled in Step 2). What remains is the pure return component.

**Step 4 — Clamp and reconcile**

Both pools are clamped to ≥ 0. If they drift from actual `cash_like` by more than €0.01 (e.g., due to FX rounding or in-transit cash), they are proportionally scaled back to match reality.

### Why delta_assets instead of per-transaction tracking

Using `delta_assets` has a key advantage: for a SELL transaction, the cost basis reduction in `book_asset_like` automatically equals `WAC × quantity_sold` — the exact principal being returned. There is no need to look up the WAC per transaction; it falls out naturally from the accounting.

### Convention properties

| Scenario | Result |
|----------|--------|
| Deposit + partial buy | Residual sits as **Capital** (undeployed deposit) |
| Interest received | Shows as **Returns** until reinvested |
| Sell in gain (e.g. bought @100, sold @120) | Principal @100 → Capital; gain @20 → Returns |
| Sell in loss (e.g. bought @100, sold @80) | Partial principal @80 → Capital; loss reduces Returns |
| Interest withdrawn | Deposited Capital decreases; Total P&L preserved |

### Worked examples

#### A — Deposit + Buy (fully deployed)

```
Day 1:
  ECF: +1,000 → capital_pool = 1,000
  delta_assets = +1,000 (BUY)
    from_returns = min(1,000, 0) = 0
    capital_pool -= 1,000  → capital_pool = 0
  returns_delta = 0 (no other cash)

Result: Capital = 0,  Returns = 0,  P&L = 0
```

#### B — Deposit + Buy + Interest (same day)

```
Day 1:
  ECF: +1,000 → capital_pool = 1,000
  delta_assets = +1,000 (BUY)
    capital_pool -= 1,000  → capital_pool = 0
  returns_delta = total_cash_delta(0) - ecf(1,000) + delta_assets(1,000) = 0

Day 2:
  ECF: 0
  delta_assets = 0
  returns_delta = 100 (INTEREST received)
    returns_pool += 100

Result: Capital = 0,  Returns = 100,  P&L = 100
```

#### C — Sell in Gain

```
State after buy: capital_pool = 0, returns_pool = 0, book_asset_like = 1,000

Day of SELL (1 unit, bought @100, sold @120):
  ECF: 0
  delta_assets = -100  (book_asset_like drops from 1,000 to 900)
    capital_pool += 100   → capital_pool = 100  (principal returned)
  returns_delta = 120 - 0 + (-100) = +20  (gain on top of cost basis)
    returns_pool += 20

Result: Capital = 100,  Returns = 20,  P&L = 20
```

#### D — Sell in Loss

```
State after buy: capital_pool = 0, returns_pool = 0, book_asset_like = 1,000

Day of SELL (1 unit, bought @100, sold @80):
  delta_assets = -100  → capital_pool += 100
  returns_delta = 80 - 0 + (-100) = -20  (loss)
    returns_pool += -20  → clamped to max(0) = 0

Result: Capital = 80,  Returns = 0,  P&L = -20
```

#### E — P2P Repayment + Interest

```
State: capital_pool = 0, book_asset_like = 1,000 (loan)

REPAYMENT 100 (SELL at cost @100) + INTEREST 10:
  delta_assets = -100  → capital_pool += 100
  returns_delta = (100 + 10) - 0 + (-100) = +10
    returns_pool += 10

Result: Capital = 100,  Returns = 10,  P&L = 10
```

#### F — Withdraw Earned Interest

```
DEPOSIT 1,000  BUY 1,000  INTEREST 100  WITHDRAWAL 100

ECF_net = 1,000 − 100 = 900 → capital_pool net +900
delta_assets = +1,000 (BUY): capital_pool 900 → -100, clamped to 0
returns_delta = (1,000 − 1,000 + 100 − 100) − 900 + 1,000 = 0

Result: Capital = 0,  Returns = 0,  cash = 0
NAV = 1,000 (assets at cost),  P&L = 1,000 − 900 = +100 ✓
```

!!! note "Key insight from Example F"

    Even though all cash is gone, Total P&L = +100 because the Deposited Capital baseline dropped to 900 when you withdrew the earned interest. The profit is locked into the asset cost — visible as NAV exceeding Deposited Capital.

---

## ⚠️ Limitations

!!! warning "Approximation via delta, not per-transaction provenance"

    The cash decomposition uses the **daily change in cost basis** (`delta_assets`) as a proxy for capital/returns flow. This means it cannot track the exact order of multiple transactions on the same day — only their net daily effect on cost basis and cash.

    In particular, when `book_asset_like > Deposited Capital` (portfolio returns have been reinvested into assets), any residual cash is attributed to returns. If you made a fresh deposit on that same day, the deposit increases `capital_cash_pool` — but part of it may be immediately consumed by a BUY also on that day, since Step 2 processes all BUYs as a single delta.

    For most practical use cases the attribution is intuitive and correct. The result is fully deterministic and recalculable from the transaction log.

- **Asset transfers from external brokers** (`TRANSFER` with `amount=0`) are not counted in Deposited Capital. If you transferred positions in from an outside broker, Total P&L may be slightly overstated relative to the true external capital contributed.

---

## 🔗 Related

- 💼 **[NAV / Net Worth](nav.md)** — the other term in the P&L formula
- 📊 **[Period P&L](period-pnl.md)** — the period-windowed version
- 📚 **[Book Value](book-value.md)** — the cost basis used in cash decomposition
- ⏱️ **[Timing Effect](timing-effect.md)** — how cash flow timing affects returns
