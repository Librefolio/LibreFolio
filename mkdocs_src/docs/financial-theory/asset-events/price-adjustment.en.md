# 📊 Price Adjustment

A **price adjustment** event represents a non-cash change to an asset's fair value — such as a write-down, mark-to-market correction, haircut, or re-rating.

---

## 📖 Definition

Price adjustments capture value changes that are **not caused by market trading** and **do not involve cash flow** to the investor. They are algebraic modifications (positive or negative) to the asset's calculated fair value.

These events are most relevant for assets that don't have continuous market pricing — such as private debt, illiquid instruments, or assets tracked via the Scheduled Investment provider.

### Common Scenarios

| Scenario | Amount | Description |
|----------|--------|-------------|
| **Write-down** | Negative | Reduction in book value due to impairment |
| **Mark-to-market** | +/− | Periodic revaluation to reflect current fair value |
| **Haircut** | Negative | Forced reduction (e.g., during debt restructuring) |
| **Re-rating** | Positive | Upward revision of fair value after positive events |
| **NAV adjustment** | +/− | Net Asset Value correction for closed-end funds |

---

## 📉 Impact on Market Price

For **market-priced assets** (stocks, ETFs), price adjustments are rare and typically informational — the market price already reflects the event.

For **model-priced assets** (Scheduled Investment, manual), the adjustment directly modifies the calculated price:

$$
\text{price}(d) = \text{base{\_}value}(d) + \sum_{i : d_i \leq d} \text{PRICE{\_}ADJUSTMENT}_i
$$

!!! example "Example: Bond Write-down"

    A corporate bond originally valued at €1,000 is partially written down after the issuer reports financial difficulties.

    - **Before adjustment**: Calculated value = €1,000
    - **Price adjustment event**: amount = −200
    - **After adjustment**: Calculated value = €800

    This is not a market transaction — it's a correction to the fair value model.

!!! example "Example: P2P Loan Haircut"

    A peer-to-peer loan of €5,000 has a 20% haircut applied during debt restructuring.

    - **Price adjustment event**: amount = −1,000
    - **New fair value**: €4,000

---

## 📊 When to Use Price Adjustments

Use `PRICE_ADJUSTMENT` when:

- ✅ The asset's fair value changes without a market transaction
- ✅ You need to record a write-down or impairment
- ✅ The asset is model-priced (Scheduled Investment) and needs a manual correction
- ✅ A debt restructuring affects the principal value

Do **not** use for:

- ❌ Regular market price changes (those are captured by price data points)
- ❌ Cash payments (use `DIVIDEND` or `INTEREST` instead)
- ❌ Share quantity changes (use `SPLIT` instead)

---

## 🧮 How LibreFolio Handles Price Adjustments

In LibreFolio, a `PRICE_ADJUSTMENT` event is recorded with:

- **Date**: The effective date of the adjustment
- **Amount**: The algebraic change (positive for increases, negative for decreases)
- **Currency**: The currency of the adjustment
- **Notes**: Description of the reason (e.g., "Partial write-down due to issuer default")

For the **Scheduled Investment** provider, price adjustments are part of the core formula:

$$
\text{price}(d) = \text{initial{\_}value} + \text{accrued{\_}interest}(d) - \sum \text{INTEREST} + \sum \text{PRICE{\_}ADJUSTMENT}
$$

---

## 🔗 Related

- 📅 **[Asset Events Overview](../asset-events.md)** — All event types
- 📈 **[Interest](interest.md)** — Periodic interest payments
- 🏁 **[Maturity Settlement](maturity-settlement.md)** — Final capital return



