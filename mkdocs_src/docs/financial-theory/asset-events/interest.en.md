# 📈 Interest

An **interest** event represents a periodic interest payment from a debt instrument, fixed-income security, or lending arrangement.

---

## 📖 Definition

Interest is the cost of borrowing money, paid by the issuer (borrower) to the holder (lender). For investors, interest payments represent income earned from holding bonds, notes, term deposits, or peer-to-peer loans.

Unlike dividends (which depend on company profits), interest payments are **contractually obligated** — the issuer must pay the agreed rate regardless of financial performance.

**Common interest schedules:**

| Frequency | Typical Instruments |
|-----------|-------------------|
| Monthly | Savings accounts, P2P loans |
| Quarterly | Corporate bonds, some government bonds |
| Semi-annually | US Treasury bonds, many European government bonds |
| Annually | Some corporate bonds, term deposits |
| At maturity | Zero-coupon bonds, certificates of deposit |

---

## 📉 Impact on Market Price

For **coupon-bearing bonds**, interest payments cause a periodic reset of the **accrued interest** component:

1. Between coupon dates, the bond's "dirty price" (clean price + accrued interest) increases gradually
2. On the coupon payment date, the accrued interest resets to zero
3. The clean price may dip slightly around the ex-coupon date

!!! example "Example"

    A bond with face value €1,000 pays a 4% annual coupon semi-annually (€20 every 6 months).

    - **Day before coupon**: Clean price €980, Accrued interest €20 → Dirty price €1,000
    - **Coupon date**: Accrued interest resets to €0, investor receives €20 cash
    - **Day after coupon**: Clean price €980, Accrued interest ≈ €0.11 → Dirty price €980.11

For **Scheduled Investment** assets in LibreFolio, interest events directly modify the calculated price:

$$
\text{price}(d) = \text{initial{\_}value} + \text{accrued{\_}interest}(d) - \sum \text{INTEREST events}
$$

---

## 📊 Yield Metrics

### Current Yield

$$
\text{Current Yield} = \frac{\text{Annual Coupon}}{\text{Current Market Price}} \times 100\%
$$

### Yield to Maturity (YTM)

The total return anticipated if the bond is held until maturity, accounting for coupon payments, face value repayment, and the current market price.

---

## 🧮 How LibreFolio Handles Interest

In LibreFolio, an `INTEREST` event is recorded with:

- **Date**: The interest payment date
- **Amount**: The cash amount received
- **Currency**: The currency of payment

For **Scheduled Investment** provider assets, interest events are generated automatically from the configured interest schedule and directly affect the price calculation. For market-priced bonds, they serve as informational markers.

---

## 🔗 Related

- 📅 **[Asset Events Overview](../asset-events.md)** — All event types
- 📆 **[Day Count Conventions](../day-count.md)** — How interest accrual periods are calculated
- 🏁 **[Maturity Settlement](maturity-settlement.md)** — Final principal return at bond maturity


