# ![](../../../static/icons/transactions/deposit.png){: width="32" style="vertical-align: middle;" } Deposit & Withdrawal ![](../../../static/icons/transactions/withdrawal.png){: width="32" style="vertical-align: middle;" }

<div class="screenshot-container">
    <img class="gallery-img" data-category="transactions" data-name="form-modal-deposit" alt="Transaction Form — DEPOSIT">
</div>

**Deposits** and **withdrawals** track the movement of cash into and out of a broker account. They do not involve any asset — only the cash balance changes.

---

## 🔑 Key Properties

| Property | Deposit | Withdrawal |
|----------|---------|------------|
| **Code** | `DEPOSIT` | `WITHDRAWAL` |
| **Cash effect** | ⬆️ Increases balance | ⬇️ Decreases balance |
| **Asset effect** | — | — |
| **Tax event** | No | No |

---

## 💡 Why They Matter

Deposits and withdrawals don't change your portfolio's market value, but they are critical for **performance measurement**:

- **Money-Weighted Return (MWR)**: accounts for timing and size of cash flows — directly affected by deposits/withdrawals
- **Time-Weighted Return (TWR)**: eliminates the effect of cash flows to measure "pure" portfolio performance

Without accurate deposit/withdrawal tracking, it's impossible to distinguish between returns *generated* by the portfolio and returns *caused* by adding/removing cash.

!!! tip "Learn more"

    See **[📈 Returns & Growth Rates](../../fundamentals/returns.md)** for the formulas and methodology.

---

## 🔗 Related

- 📈 **[Returns & Growth Rates](../../fundamentals/returns.md)** — TWR vs MWR calculation
- 🛒 **[Buy & Sell](buy-sell.md)** — Transactions that use deposited cash
