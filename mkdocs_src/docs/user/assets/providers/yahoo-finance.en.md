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
- Yahoo may throttle frequent requests, and some tickers have missing days.

## 🔗 Related

- 🔌 **[Asset Providers](index.md)** — Compare the providers
- 🛠️ **For developers: [Yahoo Finance Provider](../../../developer/backend/assets/provider_yahoo_finance.md)** — Requests, caching and events
