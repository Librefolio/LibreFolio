# 📊 Asset Types

Instruments differ in the real world — how they are priced, whether they pay income, how they are
taxed — and the detail pages below cover those differences. Inside LibreFolio every asset carries
exactly one **asset type**, and the type is a **classification** read in three places: it chooses the
icon and the label you see, it decides where the asset is counted in the
[allocation](../../portfolio-theory/asset-allocation.md) charts, and it names the bucket the asset
falls into when a [stress scenario](../../technical-analysis/risk-metrics/hypothetical-shock.md)
shocks the portfolio by asset class. `INDEX` is, in addition, the one type that accepts no
transactions.

The taxonomy has **two levels**. Most types stand on their own; two of them — **ETF** and
**Crowdfunding** — are **families**, whose members also state what the instrument *contains*.

---

## 📋 Base Types {: #base-types }

| | Type | Code | Description | |
|:---:|:---|:---|---|:---:|
| ![](../../../static/icons/asset-types/stock.png){: width="32" } | **Stock** | `STOCK` | Equity shares in a single company. Prices are typically fetched from public exchanges. | [📖](stocks.md) |
| ![](../../../static/icons/asset-types/etf.png){: width="32" } | **ETF** | `ETF` | Exchange Traded Fund of mixed or unstated content (balanced, multi-asset) — the generic member of the [ETF family](#etf-family). | [📖](etfs.md) |
| ![](../../../static/icons/asset-types/bond.png){: width="32" } | **Bond** | `BOND` | Fixed-income securities representing a loan to a borrower (government or corporate). | [📖](bonds.md) |
| ![](../../../static/icons/asset-types/crypto.png){: width="32" } | **Crypto** | `CRYPTO` | Digital currencies and tokens (Bitcoin, Ethereum, etc.). | [📖](crypto.md) |
| ![](../../../static/icons/asset-types/fund.png){: width="32" } | **Fund** | `FUND` | Mutual funds and other professionally managed investment funds. | [📖](mutual-fund.md) |
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | **Crowdfund** | `CROWDFUND` | Peer-to-peer and business crowdfunding loans, often valued via scheduled interest payments — the generic member of the [Crowdfunding family](#crowdfunding-family). | [📖](real-estate.md) |
| ![](../../../static/icons/asset-types/hold.png){: width="32" } | **Held asset** | `HOLD` | Assets without automatic market pricing: art, collectibles, shares of unlisted companies. | — |
| ![](../../../static/icons/asset-types/commodity.png){: width="32" } | **Commodity** | `COMMODITY` | Physical goods and their direct exposures: gold, oil, agricultural products. | [📖](commodities.md) |
| ![](../../../static/icons/asset-types/real-estate.png){: width="32" } | **Real estate** | `REAL_ESTATE` | Property exposure: REITs and other listed real-estate vehicles. | [📖](real-estate.md#three-ways-to-hold-property) |
| ![](../../../static/icons/asset-types/index.png){: width="32" } | **Index** | `INDEX` | Market indexes (S&amp;P 500, MSCI World) used as reference benchmarks — not directly tradeable, so no transactions are allowed. | [📖](index-benchmark.md) |
| ![](../../../static/icons/asset-types/other.png){: width="32" } | **Other** | `OTHER` | Any asset the types above do not describe. | [📖](other.md) |

A type is **one label per asset**: a balanced ETF is counted whole under `ETF`, never split into its
equity and bond parts. Looking *through* an instrument is the job of its sector and geographic
distributions, not of its type.

---

## 🧬 Families and Subtypes {: #families-and-subtypes }

A subtype answers a single question: **which base type does this instrument contain?** The second
level is therefore not a parallel taxonomy — it *is* the set of base types, seen through a wrapper.
The generic member of each family (`ETF`, `CROWDFUND`) remains a valid choice in its own right: it
is the residual for mixed or unstated content, and the type menu lists it first in its family, with
a hint that says so.

A subtype's icon is its family's icon with a small disc in the corner — a **pastille** — showing its
content: the container says what the instrument *is*, the pastille what it *holds*. The pastille is
the icon of the base type the subtype contains; the money market ETF, which contains no base type,
borrows the liquidity icon. Wherever LibreFolio draws the type icon, a subtype shows its composite —
an asset with a custom icon keeps its own.

### 📦 ETF Family {: #etf-family }

| | Type | Code | Contains | Rolls up to |
|:---:|:---|:---|:---|:---|
| ![](../../../static/icons/asset-types/etf.png){: width="32" } | **ETF** | `ETF` | Mixed or unstated content — the generic member | `ETF` (itself) |
| ![](../../../static/icons/asset-types/etf-stock.png){: width="32" } | **Equity ETF** | `ETF_STOCK` | Stocks | `STOCK` |
| ![](../../../static/icons/asset-types/etf-bond.png){: width="32" } | **Bond ETF** | `ETF_BOND` | Bonds | `BOND` |
| ![](../../../static/icons/asset-types/etf-commodity.png){: width="32" } | **Commodity ETF** | `ETF_COMMODITY` | Commodities | `COMMODITY` |
| ![](../../../static/icons/asset-types/etf-real-estate.png){: width="32" } | **Real estate ETF** | `ETF_REAL_ESTATE` | Real estate | `REAL_ESTATE` |
| ![](../../../static/icons/asset-types/etf-crypto.png){: width="32" } | **Crypto ETF** | `ETF_CRYPTO` | Crypto assets | `CRYPTO` |
| ![](../../../static/icons/asset-types/etf-liquidity.png){: width="32" } | **Money market ETF** | `ETF_MONETARY` | Money-market instruments | `ETF_MONETARY` (itself — see [below](#two-views-of-one-instrument)) |

The instrument itself is described on the [ETFs](etfs.md) page.

### 🤝 Crowdfunding Family {: #crowdfunding-family }

| | Type | Code | Contains | Rolls up to |
|:---:|:---|:---|:---|:---|
| ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" } | **Crowdfund** | `CROWDFUND` | P2P and business lending — the generic member | `CROWDFUND` (itself) |
| ![](../../../static/icons/asset-types/crowdfunding-real-estate.png){: width="32" } | **Real estate crowdfunding** | `CROWDFUND_REAL_ESTATE` | Loans backed by property projects | `REAL_ESTATE` |

Both are described on the [P2P / Crowdfunding](real-estate.md) page.

---

## ⚖️ Two Views of One Instrument {: #two-views-of-one-instrument }

The two levels answer two different questions, and LibreFolio keeps them apart.

- **The container view** — *what kind of instrument is it?* — is the family. The type menu groups by
  family, the icon keeps the family's shape, and the label says *Equity ETF*: that is the instrument
  you actually own.
- **The content view** — *what am I exposed to?* — is the roll-up: a subtype belongs with the base
  type it contains. An equity ETF and a share are both equity exposure, and to the question *am I as
  diversified as I think?* the wrapper says nothing.

Formally, let $c$ send every subtype to the base type it contains, and every other type — the
generic members and `ETF_MONETARY` included — to itself. The weight of a content class $k$ is then

$$
W_k = \sum_{i \,:\, c(\tau_i) = k} w_i
$$

where $\tau_i$ is the type of holding $i$ and $w_i$ its weight in the portfolio. The same sum taken
over the family map instead of $c$ — every ETF subtype to `ETF`, `CROWDFUND_REAL_ESTATE` to
`CROWDFUND`, every other type to itself — gives the weight of each family, the container view's
counterpart.
The type badge follows the content: an *Equity ETF* badge is blue, like a *Stock* badge. How the
dashboard presents allocation by type is described in the
[Allocation Panel](../../../user/dashboard/charts.md#allocation-panel).

Two exceptions deserve a sentence each:

- **`ETF_MONETARY` rolls up to itself.** A money market fund has no base type to roll up to: cash is
  an account balance, not an asset that is bought, so it is not an asset type. `ETF` would bury the
  fund among mixed funds, and *Liquidity* is not an asset type at all — it is the allocation bucket
  in which LibreFolio counts your cash balance, separately. In the content view the money market ETF
  is therefore a class of its own, and its badge has a colour of its own.
- **`CROWDFUND_REAL_ESTATE` has two answers.** In the content view it contains real estate and
  belongs to the Real estate class; in stress scenarios it is shocked as the loan it is.

---

## 🌪️ Types in Stress Scenarios {: #types-in-stress-scenarios }

A stress scenario that shocks the portfolio by asset class treats every code as its **own bucket** —
there, a subtype is never folded into its content class. In the defaults of the two built-in
asset-class scenarios, *Equity crash* and *Global risk-off*, each ETF subtype carries exactly the
shock of the base type it holds, while the generic `ETF` keeps a blended shock of its own, because
its content is unstated; `ETF_MONETARY` is not shocked.

The one deliberate departure is `CROWDFUND_REAL_ESTATE`, which moves like `CROWDFUND` rather than
like `REAL_ESTATE`: a crowdfunding loan is illiquid and not marked to market, and its risk is a
default that arrives late. The reasoning, and its known limit, are on the
[P2P / Crowdfunding](real-estate.md#in-stress-scenarios) page.

Every bucket shock of those scenarios is editable, and a bucket left unconfigured is shocked by
zero — see [Hypothetical Shock](../../technical-analysis/risk-metrics/hypothetical-shock.md#what-you-did-not-configure).

---

## 🔗 Related

- 💸 **[Transaction Types](../transaction-types/index.md)** — Operations that affect your portfolio
- 📅 **[Asset Events](../asset-events/index.md)** — Corporate actions affecting asset prices
- 💰 **[Taxation](../../fundamentals/taxation.md)** — Tax implications by asset class
- 🧭 **[Asset Allocation](../../portfolio-theory/asset-allocation.md)** — Distributing capital across asset classes
- ⚡ **[Hypothetical Shock](../../technical-analysis/risk-metrics/hypothetical-shock.md)** — How asset-class buckets are shocked

