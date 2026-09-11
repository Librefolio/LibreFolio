# 💸 Yield on Cost (YOC)

Yield on Cost (YOC) measures the **non-negative gross recorded income produced per current unit over the trailing 365 calendar dates**, relative to the open position's average purchase price per unit ([Weighted Average Cost, or WAC](../weighted-average-cost.md)).

LibreFolio computes it separately for every $(a,b)$ pair:

$$
(a,b) = (\text{asset},\ \text{broker})
$$

The same asset held at two brokers therefore has two independent YOC values.

!!! warning "Gross recorded income — not a tax-net return"

    YOC uses only non-negative cash amounts from asset-linked `DIVIDEND` and `INTEREST` transactions. Exact zero is accepted; negative income amounts are not supported. Separate `TAX` and `FEE` transactions are not subtracted, so the result must not be read as after-tax or net income performance.

---

## 🧭 Scope and trailing window

Let $T$ be the selected report end date. YOC always uses the inclusive window:

$$
\boxed{[T-364,\ T]}
$$

This window contains 365 calendar dates and is **independent of the report start date**. Moving the start of a dashboard report does not change YOC when $T$ remains unchanged.

Only non-negative, asset-linked entries from the personal transaction ledger qualify:

| Included | Excluded |
|---|---|
| Asset-linked `Transaction` rows of type `DIVIDEND` or `INTEREST`, with cash amount equal to or greater than zero | Separate `TAX`, `FEE`, and `ADJUSTMENT` transactions |
| The non-negative cash amount, currency, date, asset, and paying broker | Provider or manual `AssetEvent` income |
| Income assigned to the exact $(a,b)$ pair | Income without an asset |

The transaction schema accepts an exact-zero `DIVIDEND` or `INTEREST` cash amount but rejects a negative one. An `ADJUSTMENT` can affect replayed quantity, WAC, or linked-split inputs, but it never enters the YOC income numerator.

The calculation has no asset-class allowlist. It applies to every open long holding type represented by the portfolio engine, including crypto and manual assets, provided the required ledger, WAC, split, and FX inputs are valid.

---

## 🧮 Mathematical definition

For each qualifying income transaction $j$:

| Symbol | Meaning |
|---|---|
| $D_j$ | Transaction date |
| $I_j$ | Non-negative gross transaction cash amount in currency $c_j$, with $I_j\geq0$ |
| $C^*$ | Selected report currency |
| $q_j$ | Eligible long quantity at the paying broker at end of day $D_j-1$ |
| $s_j$ | Product of linked split ratios dated from $D_j$ through $T$, inclusive |
| $w_{a,b,T}$ | Average purchase price per unit (WAC) of pair $(a,b)$ at $T$ |

### 💱 Income conversion

Each income amount is converted to the report currency at its own transaction date:

$$
I_j^* =
I_j \cdot \mathrm{fx}(c_j,C^*,D_j)
$$

### 🧬 Current-unit normalization

Income per unit is first allocated over the eligible prior-day quantity, then normalized for every valid linked split on or after the income date:

$$
g_{a,b,T}
=
\sum_{\substack{j \in (a,b)\\T-364 \leq D_j \leq T}}
\frac{I_j^*}{q_j \cdot s_j}
$$

For a 2-for-1 split, $s_j=2$: historical income per old unit is divided by two so it is comparable with current units. A linked split dated on $D_j$ is included as well.

### 📊 Average-purchase-price denominator

The position's average purchase price per unit (WAC) is converted at the report end date:

$$
w_{a,b,T}^*
=
w_{a,b,T}
\cdot
\mathrm{fx}(c_w,C^*,T)
$$

LibreFolio then reports:

$$
\boxed{
\mathrm{YOC}_{a,b,T}
=
\frac{g_{a,b,T}}{w_{a,b,T}^*}
}
$$

The API value is a fraction, and the Holdings table renders it as a percentage. An available value may be positive or exactly zero.

---

## 🔁 Quantity, custody, transfer, and split rules

The eligible quantity $q_j$ is deliberately evaluated at **end of day before payment**:

- only `LONG` quantity counts;
- a same-day **BUY is excluded**;
- a same-day **SELL is included**, because those units existed at end of day $D_j-1$;
- broker custody is respected throughout transfer replay;
- an in-transit fragment still counts for its source broker, never for the destination before arrival.

Income remains attached to the broker that recorded it. Moving units from broker A to broker B does **not** automatically carry A's historical income into B's YOC. Later income recorded at B uses B's eligible prior-day quantity and B's average purchase price.

Subsequent and same-day linked splits rescale earlier per-unit income into the units that exist at $T$. LibreFolio uses explicit linked split rows; it does not infer an asset-wide restatement from a split recorded only at another broker. If a connected cross-broker replay contains a split but lacks a matching split row for the income/current broker, the normalization is ambiguous and YOC fails closed. An invalid, duplicated, mismatched, or non-positive linked split likewise makes the affected pair unavailable instead of producing an approximate result.

`ADJUSTMENT` transactions remain replay inputs only: they can change quantity or WAC and can carry a linked split, but their amounts never count as income.

??? example "Same-day trades and a later split"

    Assume a €20 dividend is recorded on June 30. The paying broker held 100 eligible long units at end of day June 29. A buy or sell on June 30 does not change that denominator.

    A linked 2-for-1 split occurs between June 30 and $T$, so:

    $$
    g = \frac{20}{100 \times 2} = 0.10\ \mathrm{EUR}
    $$

    If the average purchase price (WAC) at $T$ is €4.00 per current unit:

    $$
    \mathrm{YOC} =
    \frac{0.10\ \mathrm{EUR}}{4.00\ \mathrm{EUR}}
    = 2.50\%
    $$

---

## 🌍 FX resolution and provenance

YOC uses the portfolio's current historical FX policy:

- income requests FX for $D_j$;
- average purchase price (WAC) requests FX for $T$;
- when the exact date is absent, the latest stored rate on or before that date is used;
- no forward rate is substituted.

Provenance preserves both the **requested date** and the **actual rate date**, plus the currency pair and days carried backward. The Holdings tooltip can therefore show, for example, that a June 30 income conversion used the most recent June 28 rate.

If any required income or average-purchase-price conversion cannot be resolved, the whole pair is unavailable. LibreFolio does not silently omit the affected transaction or reuse an unrelated value.

---

## 🚦 Availability and fail-closed behavior

YOC distinguishes a valid absence of income from a calculation that cannot be trusted.

| State | Meaning | Holdings cell |
|---|---|---|
| **Available** | At least one qualifying income transaction exists and every required input is valid. The result is positive when any qualifying amount is positive; it is exactly zero when one or more qualifying rows are recorded at amount zero and none has a positive amount. Provenance marks that exact-zero case with `net_zero=true`. No minimum pair age applies. | Percentage with two decimals: for example, `2.50%` or `0.00%`. |
| **No income** | No qualifying income row exists in the window, and the pair has a full 365-date ledger history. The API value is zero, but this state is distinct from an available zero. | `-` with explanatory tooltip and no warning icon. |
| **Unavailable** | The no-income pair is too young, or a required ledger/calculation input failed validation. Its value is `null` and its reason identifies the failure. | `-` with an info icon and custom reason tooltip. |

The outer `yield_on_cost` field is required and non-null for every holding. An unavailable result is therefore represented by the result object's `unavailable` status and null `value`, not by a missing or null outer field.

Let $F_{a,b}$ be the first-ever asset-linked transaction date for the pair. A no-income result becomes valid only when:

$$
(T-F_{a,b})+1 \geq 365
$$

Equivalently, $F_{a,b} \leq T-364$. Closing and later reopening the position does **not** reset this age: the original first pair transaction remains the anchor.

This one-year gate is evaluated **only when the trailing window contains no qualifying income transactions**. It is not an annualization rule: a younger pair with valid recorded income can have an available YOC because the metric simply sums the income observed inside $[T-364,T]$.

The calculation fails closed for any of these conditions:

- income has no eligible long quantity at end of day $D_j-1$;
- transaction or transfer replay is inconsistent;
- linked split data is invalid or inconsistent;
- required historical FX is missing;
- average purchase price (WAC) is missing or non-positive.

One bad required input makes the entire pair unavailable. There is no partial sum, asset-event substitute, provider-income fallback, or current-quantity approximation.

---

## 🖥️ Reading YOC in LibreFolio

YOC appears in the shared **Holdings** table used by both the Dashboard Positions tab and each broker's Positions tab:

- visible by default immediately beside **Annualized**;
- available values, including exact zero, are fixed to two decimal places;
- positive values have no leading `+`;
- an available zero appears as `0.00%` and has `net_zero=true` in its provenance;
- a normal no-income dash has no warning icon;
- an unavailable dash has an info icon whose tooltip explains the specific reason and available provenance;
- show/hide choices are shared between Dashboard and broker views and persist across sessions.

Each row remains broker-specific. In the Dashboard's multi-broker scope, two rows for the same asset can therefore show different values. See [Positions & Analysis](../../../../user/dashboard/positions.md) for the user-facing table guide.

---

## ⚖️ What YOC is not

| Metric | Denominator and horizon | Why it differs from LibreFolio YOC |
|---|---|---|
| [**Market dividend yield**](../../../instruments/asset-events/dividend.md) | Annual dividend per share divided by current market price | Market/provider measure; YOC uses only recorded personal income and average purchase price (WAC). |
| **Cumulative cash yield** | Lifetime total income divided by current total cost basis | YOC uses only $[T-364,T]$, reconstructs income per eligible historical unit, and does not divide lifetime cash by today's aggregate basis. |
| [**Net annualized return / CAGR**](net-annualized-return.md) | Compounded net total return over the holding window | Includes market performance, income, fees, and taxes; YOC isolates gross recorded income and is not annualized from a cumulative return. |
| [**Bond current yield**](../../../instruments/asset-events/interest.md) | Annual coupon divided by current bond price | Security-level coupon/price measure; YOC uses the investor's recorded broker ledger and WAC. |
| [**Yield to maturity (YTM)**](../../../instruments/asset-events/interest.md) | Discount rate equating a bond's future coupons and redemption value to price | Forward-looking bond IRR; YOC is trailing, transaction-based, and applies to every holding type. |

---

## 🔗 Related

- 📊 [Weighted Average Cost](../weighted-average-cost.md) — average-purchase-price denominator
- 🖥️ [Dashboard Positions](../../../../user/dashboard/positions.md) — column states, formatting, and shared preference
- 💰 [Dividend & Interest Transactions](../../../instruments/transaction-types/dividend-interest.md) — qualifying personal ledger entries
- ⚙️ [Portfolio Engine](index.md) — position state and metric layer
