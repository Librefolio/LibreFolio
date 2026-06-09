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

## 🧮 Interest Formulas

??? example "📏 Simple Interest"

    Interest calculated only on the original principal — no compounding:

    $$
    I = P \times r \times t
    $$

    Where:

    - $P$ = principal (initial investment)
    - $r$ = annual interest rate (e.g., 0.04 for 4%)
    - $t$ = time in years

    Used for: short-term loans, some savings accounts, treasury bills.

??? example "📈 Compound Interest"

    Interest calculated on principal **plus** previously accumulated interest:

    $$
    A = P \times \left(1 + \frac{r}{n}\right)^{n \times t}
    $$

    Where:

    - $A$ = final amount (principal + interest)
    - $P$ = principal
    - $r$ = annual interest rate
    - $n$ = compounding frequency per year (12 = monthly, 4 = quarterly, 1 = annual)
    - $t$ = time in years

    The interest earned is: $I = A - P$

    Used for: most bonds, savings accounts with reinvestment, P2P platforms.

---

## 📉 Impact on Market Price

For **coupon-bearing bonds**, interest payments cause a periodic reset of the **accrued interest** component:

1. Between coupon dates, the bond's "dirty price" (clean price + accrued interest) increases gradually
2. On the coupon payment date, the accrued interest resets to zero
3. The clean price may dip slightly around the ex-coupon date

??? example "Bond coupon cycle"

    A bond with face value €1,000 pays a 4% annual coupon semi-annually (€20 every 6 months).

    - **Day before coupon**: Clean price €980, Accrued interest €20 → Dirty price €1,000
    - **Coupon date**: Accrued interest resets to €0, investor receives €20 cash
    - **Day after coupon**: Clean price €980, Accrued interest ≈ €0.11 → Dirty price €980.11

For **Scheduled Investment** assets in LibreFolio, interest events directly modify the calculated price:

$$
\text{price}(d) = V_0 + I_{accrued}(d) - \sum_{k} C_k
$$

Where:

- $V_0$ = initial investment value
- $I_{accrued}(d)$ = interest accrued up to date $d$
- $\sum_k C_k$ = sum of all interest payments (coupons) already distributed

---

## 📊 Yield Metrics

??? example "📐 Current Yield"

    The simplest yield measure — annual income relative to current price:

    $$
    \text{Current Yield} = \frac{\text{Annual Coupon}}{\text{Current Market Price}} \times 100
    $$

    Where:

    - **Annual Coupon** = total coupon payments per year (e.g., €40 for a 4% bond with €1,000 face value)
    - **Current Market Price** = what you'd pay to buy the bond today

    Limitation: ignores capital gain/loss if held to maturity.

??? example "📐 Yield to Maturity (YTM)"

    The total return anticipated if the bond is held until maturity, accounting for **all** cash flows: coupon payments, face value repayment, and the difference between purchase price and par value.

    YTM is the rate $y$ that satisfies:

    $$
    P = \sum_{t=1}^{T} \frac{C}{(1+y)^t} + \frac{F}{(1+y)^T}
    $$

    Where:

    - $P$ = current market price
    - $C$ = coupon payment per period
    - $F$ = face value (returned at maturity)
    - $T$ = number of periods to maturity
    - $y$ = yield to maturity (per period)

    YTM must be solved numerically (no closed-form solution).

---

## 🧮 How LibreFolio Handles Interest

In LibreFolio, an `INTEREST` event (and the corresponding portfolio transaction) is recorded with:

- **Date**: The interest payment date
- **Amount**: The cash amount received
- **Currency**: The currency of payment

### The Accounting Difference: Interest vs. Dividend
It is crucial to distinguish between an **Interest** and a **Dividend** transaction at the database level:

1. **Interest (Debt/Yield-based)**: An interest payment represents yield on debt or cash deposits (e.g., bank savings accounts, P2P loans, or bond coupons). In double-entry portfolio tracking, these represent cash inflows (`cash.amount > 0`) where the underlying asset is optional. The database transaction requires `quantity = 0` because no units of the asset are transacted during a cash interest payment.
2. **Dividend (Equity-based)**: A dividend is an utility distribution paid to shareholders. It strictly requires an underlying equity asset to exist (the asset is mandatory), and the payout depends directly on the number of shares owned at the ex-date. Just like interests, dividends are pure cash movements (`quantity = 0`).

For **Scheduled Investment** provider assets, interest events are generated automatically from the configured interest schedule and directly affect the price calculation. For market-priced bonds, they serve as informational markers.

---

## 🔗 Related

- 📅 **[Asset Events Overview](index.md)** — All event types
- 📆 **[Day Count Conventions](../../fundamentals/day-count.md)** — How interest accrual periods are calculated
- 🏁 **[Maturity Settlement](maturity-settlement.md)** — Final principal return at bond maturity
- 📈 **[Returns & Growth Rates](../../fundamentals/returns.md)** — Measuring total return
