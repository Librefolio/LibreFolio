# ![](../../../static/icons/transactions/transfer.png){: width="32" style="vertical-align: middle;" } Transfer & FX Conversion

**Transfers** move assets between portfolios without a sale, while **FX Conversions** exchange one currency for another within a portfolio.

---

## 🔑 Key Properties

| Property | Transfer In | Transfer Out | FX Conversion |
|----------|------------|-------------|---------------|
| **Code** | `TRANSFER_IN` | `TRANSFER_OUT` | `FX_CONVERSION` |
| **Cash effect** | — | — | ⬆️⬇️ (swap) |
| **Asset effect** | ⬆️ Increases | ⬇️ Decreases | — |
| **Tax event** | Varies by jurisdiction | Varies | Varies |

---

## 🔄 Transfer In / Out

Transfers model the movement of assets between broker accounts or portfolios **without a sale**. Common scenarios:

- Moving shares from one broker to another
- Inheriting assets
- In-kind contributions to a different account type (e.g., ISA, 401k)

!!! info "Cost Basis Preservation"

    When transferring assets, the **original cost basis** should be preserved. The transfer itself is not a taxable event in most jurisdictions (though rules vary).

---

## 💱 FX Conversion

Currency exchanges within a portfolio:

$$
\text{Amount}_{target} = \text{Amount}_{source} \times \text{FX Rate} - \text{Fees}
$$

FX conversions may be:

- **Explicit**: User deliberately converts currencies (e.g., EUR → USD)
- **Implicit**: Broker auto-converts when buying a foreign-denominated asset

---

## 📊 Adjustment

The `ADJUSTMENT` transaction type is a catch-all for manual corrections to either cash or asset balances. Use cases:

- Correcting import errors
- Recording corporate actions not covered by standard types
- Initial balance setup

---

## 🔗 Related

- 🛒 **[Buy & Sell](buy-sell.md)** — Standard asset transactions
- 💵 **[Deposit & Withdrawal](deposit-withdrawal.md)** — Cash movements
- 💰 **[FX Rates](../../../user/fx/index.md)** — Exchange rate management
