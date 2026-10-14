# <img src="../../../../static/scheduled_investment.png" alt=""> Scheduled Investment

The Scheduled Investment provider calculates an asset's value from its interest schedule instead
of reading a market price. Use it for savings accounts, term deposits, P2P or crowdfunding loans,
and bonds you follow by their accrued interest. In the **Provider** list it is called
**Scheduled Investment Calculator**.

## 🔍 What It Offers

- ✅ **Current price** and **history**, calculated from your schedule: no website is queried, and
  the same schedule always gives the same values.
- ✅ **Events**: with **Generate Coupon**, interest payouts and a final maturity settlement, plus
  the events you add yourself.
- ❌ **Search** and **details**: not applicable. There is no identifier to type either: LibreFolio
  creates one for you.

## 📋 Interest Schedule Editor {: #interest-schedule-editor }

Choosing the provider in **Provider Assignment** opens the **Interest Schedule** editor. Start with
the settings for the whole schedule:

- **Initial Value** and **Currency**: the amount invested, or the face value — e.g. 10,000 EUR.
- **Interest Type**: **Simple** or **Compound** — see
  [How the value is calculated](#how-value-is-calculated).
- **Day Count**: how the days of a year are counted — **ACT/365**, **ACT/360**, **ACT/ACT** or
  **30/360**. See [Day count conventions](../../../financial-theory/fundamentals/day-count.md).

Then add the periods with **Add First Period**, and **Add Period** for the next ones:

| Column | What to enter |
|---|---|
| **Period** | Start and end date, both included |
| **Rate %** | The annual rate as a percentage: `5.00` means 5% a year |
| **Frequency** | How often interest matures: Daily, Weekly, Monthly, Quarterly, Semiannual or Annual |
| **Generate Coupon** | Tick it to pay the accrued interest out at each maturity date |

Periods must follow one another, with no gaps or overlaps. **Split** cuts a period in two; select
neighbouring periods and click **Merge** to join them.

### ⚡ Late Interest {: #late-interest }

For a loan repaid late, turn on **⚡ Late Interest** below the periods: the asset keeps growing
after the last period ends. A late row appears with its own **Rate %**, **Frequency** and
**Generate Coupon**. Click its period to set the grace days, and choose **Simple** or
**Compound** (the default) next to the switch.

- During the grace days, interest keeps accruing at the last period's rate.
- After them, the late rate applies.

### 📅 Asset Events

Add one-off events with **Add Event**: a **Date**, a **Type**, a **Value** and optional **Notes**.
Each event counts from its date onwards.

| Type | Effect on the value |
|---|---|
| **Interest** | An interest payout you received: the value drops by that amount |
| **Price Adjustment** | A write-down (negative) or a write-up (positive) |

## 🧮 How the Value Is Calculated {: #how-value-is-calculated }

LibreFolio walks the schedule day by day. On day $d$ the value is

$$
V(d) = V_0 + I(d) - \sum \text{Interest events} + \sum \text{Price adjustments}
$$

where $V_0$ is the **Initial Value**, $I(d)$ the interest accrued so far, and the sums cover the
events up to day $d$. Each day adds interest at the period's annual rate $r$ over $\Delta t$, one
day's share of the year under the **Day Count** (for example $1/365$ with ACT/365):

- **Simple** — interest on the initial value only: $\Delta I = V_0 \, r \, \Delta t$
- **Compound** — interest on the interest already accrued too: $\Delta I = (V_0 + I) \, r \, \Delta t$

With **Generate Coupon**, at each maturity date the gain $V(d) - V_0$, when positive, is paid out
as an interest event: the value starts again from $V_0$, and $I$ and the sums restart from zero.

- **Before the first period**, the value is the Initial Value.
- **After the last period**, it stays at its final amount, unless late interest is on. With
  **Generate Coupon** on the last period and no late interest, a maturity settlement event closes
  the asset at that amount.
- **The chart** gets a point on each **Frequency** date: choose **Daily** for a smooth line.

??? example "🧮 A €10,000 loan at 5%, with a coupon every month"

    Simple interest, ACT/365, one period starting on 1 January, **Frequency** Monthly,
    **Generate Coupon** ticked. The first maturity date is 1 February, 31 days later: the loan has
    earned about €42.47 ($10\,000 \times 0.05 \times 31/365$). That amount is paid out as an
    interest event, and the value goes back to €10,000 to grow again in February.

## 🔗 Related

- 📅 **[Asset Events](../detail/events.md)** — How events show on the asset's chart
- 🛠️ **For developers: [Scheduled Investment Provider](../../../developer/backend/assets/provider_scheduled_investment.md)** — Engine, events and caching
