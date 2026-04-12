# <img src="../../../static/icons/asset-types/bond.png" width="32" style="vertical-align: middle;" /> Bonds

A **bond** is a fixed-income security representing a loan from an investor to a borrower (government or corporation). The borrower pays periodic interest (**coupons**) and returns the principal (**face value**) at maturity.

---

## 🔑 Key Characteristics

| Property | Detail |
|----------|--------|
| **Code in LibreFolio** | `BOND` |
| **Pricing** | Quoted as percentage of face value (e.g., 98.50 = 98.5% of par) |
| **Currency** | Denominated in the issuance currency |
| **Coupons** | Fixed or floating rate, paid semi-annually or annually |
| **Maturity** | Fixed date when principal is returned |
| **Typical providers** | Yahoo Finance, Scheduled Investment, Manual |

---

## 📊 Bond Pricing Concepts

### 💵 Face Value (Par)

The amount the issuer will pay back at maturity — typically $1,000 or €1,000 per bond.

### 📈 Coupon Rate

The annual interest rate paid on the face value:

$$
\text{Annual Coupon} = \text{Face Value} \times \text{Coupon Rate}
$$

### 📊 Yield to Maturity (YTM)

The total expected return if the bond is held until maturity, accounting for the purchase price, coupon payments, and face value at maturity. The YTM formula is a widely used **mathematical approximation** of how the market prices bonds in response to changes in interest rates, and serves as the foundation for many other fixed-income metrics:

$$
P = \sum_{t=1}^{n} \frac{C}{(1 + y)^t} + \frac{F}{(1 + y)^n}
$$

where $P$ = price, $C$ = coupon, $F$ = face value, $y$ = YTM, $n$ = periods.

### 📉 Dirty vs Clean Price

- **Clean Price**: The quoted price, excluding accrued interest
- **Dirty Price**: Clean price + accrued interest (what you actually pay)

$$
\text{Dirty Price} = \text{Clean Price} + \text{Accrued Interest}
$$

Accrued interest depends on the [Day Count Convention](../../fundamentals/day-count.md).

---

## 📈 Price–Yield Relationship

Bond prices move **inversely** to yields:

- When interest rates rise → bond prices fall
- When interest rates fall → bond prices rise

This is because existing bonds with lower coupons become less attractive compared to new bonds issued at higher rates.

---

## 🔗 Related

- 📈 **[Interest Events](../asset-events/interest.md)** — Coupon payments and accrual
- 🏁 **[Maturity Settlement](../asset-events/maturity-settlement.md)** — End-of-life capital return
- 📊 **[Price Adjustment](../asset-events/price-adjustment.md)** — Mark-to-market and write-downs
- 📅 **[Day Count Conventions](../../fundamentals/day-count.md)** — How accrued interest is calculated
