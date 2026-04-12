# <img src="../../../static/icons/transactions/fee.png" width="32" style="vertical-align: middle;" /> Fee & Tax

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

Fees and taxes directly reduce your net return:

$$
R_{net} = R_{gross} - \frac{\text{Fees} + \text{Taxes}}{V_{start}}
$$

Over long periods, even small recurring fees compound significantly:

$$
V_{final} = V_0 \times (1 + r - f)^n
$$

where $f$ is the annual fee rate. A 1% annual fee on a 7% return over 30 years reduces the final value by **26%**.

---

## 🔗 Related

- 💰 **[Taxation](../../fundamentals/taxation.md)** — Comprehensive tax theory
- 🛒 **[Buy & Sell](buy-sell.md)** — Fees charged on transactions
