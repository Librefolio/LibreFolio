# <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" alt=""> Yahoo Finance

Yahoo Finance covers stocks, ETFs, funds, indices and crypto from exchanges worldwide, and you can
search it by name or ticker.

## 🔍 What It Offers

- **Current price**: the latest price Yahoo reports for the ticker — on some exchanges it is
  delayed.
- **History**: daily open, high, low, close and volume, as far back as Yahoo goes. The closes are saved as
  the exchange gives them, without the adjustment for the dividends paid since (a split is already in
  Yahoo's closes, and is recorded as an event).
- **Dividends and splits**: recorded as asset events. For a London line quoted in pence, the dividend is
  saved in pounds (1.95 pence is 0.0195 GBP).
- **Search**: by name or ticker.
- **Details**: type, currency, description, sector, ticker and, when Yahoo has it, the ISIN.
- **Fund details**: for an ETF or a fund, the sector breakdown (a stock gets its single sector), the
  fund's own description when Yahoo has no business summary for it, and at the end of the description
  the expense ratio (`TER: 0.03%`) and the issuer (`Issuer: Vanguard`). Yahoo does not give every fund
  its expense ratio — Vanguard FTSE All-World (`VWCE.DE`) has none — and then that part is left out.
  The country breakdown comes only from [justETF](justetf.md).

## ✏️ Set It Up

**Search Online** sets it up for you. By hand, in **Provider Assignment**, choose
**Yahoo Finance**, set **Identifier Type** to **TICKER** and type the ticker as **Identifier**.
There is nothing else to fill in.

| Asset | Ticker |
|-------|--------|
| Apple Inc. | `AAPL` |
| Vanguard FTSE All-World (Xetra) | `VWCE.DE` |
| iShares Core S&P 500 (Milan) | `CSSPX.MI` |
| Bitcoin in US dollars | `BTC-USD` |

Outside the US, add the exchange suffix to the ticker: `.DE` for Xetra, `.MI` for Milan, `.AS` for
Amsterdam.

Many London lines (suffix `.L`) are quoted in pence, which Yahoo reports as the currency `GBp`.
LibreFolio stores the currency as `GBP` and the prices as Yahoo gives them, in pence, so such an
asset needs **Units per single price** at 100, or its value comes out 100 times too high. When
Yahoo reports `GBp`, picking the line in **Search Online** sets 100, with a note under the field,
and **Ask Provider** proposes it if the field says otherwise
([Check the provider's data](../create-edit.md#provider-data-comparison)).

## ⚠️ Limits

- **ISIN** also works as **Identifier Type**, but only when Yahoo can match it to a ticker: prefer
  the ticker.
- **Data saved before this behaviour stay as they were.** If you have a Yahoo asset whose closes were
  saved earlier, they still carry the dividend adjustment of the day they were read, and the dividends
  of a pence line are still in pence. Nothing rewrites them on its own: run the **full Sync** of the asset
  again (the dialog warns before it overwrites) and the history is read afresh. This does not change the
  split behaviour below.
- **Known limitation: splits.** After a stock split Yahoo rewrites the past closes (and dividends) to the
  new number of shares. For Apple's 4:1 split of 31 August 2020, the close of 28 August 2020 is given as
  124.81 instead of the 499 it really was. So the value of a position on the days before a split can come
  out divided by the split ratio (10 shares × 124.81 = 1,248 instead of 4,990), and the return jumps on
  the day of the split. A correction is planned after 1.3.
- Yahoo may throttle frequent requests: LibreFolio then pauses it for a while and keeps showing the
  last saved prices. Some tickers have missing days.

## 🔗 Related

- 🔌 **[Asset Providers](index.md)** — Compare the providers
- 🛠️ **For developers: [Yahoo Finance Provider](../../../developer/backend/assets/provider_yahoo_finance.md)** — Requests, caching and events
