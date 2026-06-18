# ![](../../../static/icons/transactions/fee.png){: width="32" style="vertical-align: middle;" } Fee & Tax ![](../../../static/icons/transactions/tax.png){: width="32" style="vertical-align: middle;" }

**Fees** and **taxes** represent costs that reduce your portfolio value. They are separate transaction types to distinguish between broker-charged costs and government-imposed obligations.

---

## 🔑 Key Properties

| Property | Fee | Tax |
|----------|-----|-----|
| **Code** | `FEE` | `TAX` |
| **Cash effect** | ⬇️ Decreases balance | ⬇️ Decreases balance |
| **Asset effect** | — | — |
| **Examples** | Commission, custody fee, spread | Capital gains tax, withholding tax, stamp duty |

---

## 📊 Fee Types

| Fee Type | Description | Frequency |
|----------|-------------|-----------|
| **Trading commission** | Per-trade cost charged by broker | Per transaction |
| **Custody fee** | Account maintenance charge | Monthly/Quarterly |
| **Spread** | Difference between bid and ask price | Implicit per trade |
| **FX conversion fee** | Cost of currency exchange | Per conversion |
| **Management fee (TER)** | ETF/Fund annual expense | Deducted from NAV |

---

## 💰 Tax Types

| Tax Type | Description | When Charged |
|----------|-------------|-------------|
| **Capital gains tax** | Tax on realized profit from selling | On sale |
| **Withholding tax** | Tax deducted at source (dividends, interest) | On payment |
| **Stamp duty** | Transaction tax (e.g., UK stamp duty) | On purchase |
| **Financial transaction tax** | Tax on trades (e.g., Italian Tobin tax) | On trade |

---

## 📐 Impact on Returns

Fees and taxes directly reduce your net return. The relationship between gross and net performance:

$$
R_{net} = R_{gross} - \frac{\text{Fees} + \text{Taxes}}{V_{start}}
$$

Where:

- $R_{gross}$ = return before costs (what the market gave you)
- $R_{net}$ = return after costs (what you actually keep)
- $V_{start}$ = portfolio value at the start of the period

### 📉 Compounding Effect of Fees

Over long holding periods, even small recurring fees erode returns significantly due to **compounding drag**:

$$
V_{final} = V_0 \times (1 + r - f)^n
$$

Where:

- $V_0$ = initial investment
- $r$ = annual gross return rate (e.g., 0.07 for 7%)
- $f$ = annual fee rate (e.g., 0.01 for 1%)
- $n$ = number of years

!!! example "The 1% drag over 30 years"

    With $10,000 invested at 7% gross return:

    - **Without fees**: $10,000 × $(1.07)^{30}$ = **$76,123**
    - **With 1% fee**: $10,000 × $(1.06)^{30}$ = **$57,435**

    The 1% annual fee costs you **$18,688** — a 26% reduction in final value.

---

## 🔗 Related

- 📈 **[Returns & Growth Rates](../../fundamentals/returns.md)** — How returns are measured (gross vs net)
- 💰 **[Taxation](../../fundamentals/taxation.md)** — Comprehensive tax theory and tax efficiency
- 🛒 **[Buy & Sell](buy-sell.md)** — Trading commissions attached to transactions
- 💱 **[FX Conversion](fx-conversion.md)** — Hidden FX spreads as implicit fees
