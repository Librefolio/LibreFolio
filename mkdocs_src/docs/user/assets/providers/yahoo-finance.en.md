# <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" alt=""> Yahoo Finance

Yahoo Finance covers stocks, ETFs, funds, indices and crypto from exchanges worldwide, and you can
search it by name or ticker.

## 🔍 What It Offers

- **Current price**: the latest price Yahoo reports for the ticker — on some exchanges it is
  delayed.
- **History**: daily open, high, low, close and volume, as far back as Yahoo goes.
- **Dividends and splits**: recorded as asset events.
- **Search**: by name or ticker.
- **Details**: type, currency, description, sector, ticker and, when Yahoo has it, the ISIN.

!!! note "Dates on the exchange's own day"

    Prices, dividends and splits are dated on the exchange's own day. Versions before 1.3 stored
    them a day early for exchanges ahead of UTC, such as Milan and Tokyo, or London in summer.
    After you upgrade, LibreFolio checks each Yahoo asset once, at its next sync, and moves those
    dates to their day. That sync reads the asset's whole history, so it may take a little
    longer. If Yahoo cannot answer then, the sync saves nothing for that asset, and the next sync
    tries again.

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

## ⚠️ Limits

- **ISIN** also works as **Identifier Type**, but only when Yahoo can match it to a ticker: prefer
  the ticker.
- Yahoo may throttle frequent requests: LibreFolio then pauses it for a while and keeps showing the
  last saved prices. Some tickers have missing days.
- Yahoo quotes many London shares in pence (GBp). The Dashboard's
  [Data Quality Banner](../../dashboard/index.md#data-quality-banner) names each one you hold: set
  its **Units per single price** to 100. Do not change a London share the banner does not name:
  some are quoted in pounds.

## 🔗 Related

- 🔌 **[Asset Providers](index.md)** — Compare the providers
- 🛠️ **For developers: [Yahoo Finance Provider](../../../developer/backend/assets/provider_yahoo_finance.md)** — Requests, caching and events
