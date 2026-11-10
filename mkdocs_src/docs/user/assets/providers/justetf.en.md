# <img src="https://www.justetf.com/android-chrome-144x144.png?v2" alt=""> justETF

justETF prices European ETFs by their ISIN, in euros, US dollars, Swiss francs or British pounds.
It also brings each fund's description and its country and sector breakdowns.

## 🔍 What It Offers

- **Current price**: in EUR, the live price from the gettex exchange; when there is none — and
  always in USD, CHF and GBP — the latest daily price.
- **History**: daily closing prices in the currency you choose.
- **Dividends**: the distributions shown in the fund's chart become dividend events.
- **Search**: by name, ticker, WKN or ISIN, among the ETFs listed on justETF.
- **Details**: a description with the TER and the distribution policy, the country and sector
  breakdowns, the ISIN and the ticker.

## ✏️ Set It Up

**Search Online** sets it up for you. By hand, in **Provider Assignment**:

1. Choose **JustETF** as **Provider**.
2. Type the fund's **ISIN**, for example `IE00B4L5Y983` (iShares Core MSCI World).
3. In `currency`, pick `EUR` (the default), `USD`, `CHF` or `GBP`: every price of the asset is
   stored in that currency.

### 💱 Pick the Currency in Search {: #search-currency }

Each ETF appears four times in the results, once per currency: 🇪🇺 EUR, 🇺🇸 USD, 🇨🇭 CHF and
🇬🇧 GBP — unless you chose a [preferred currency](#preferred-currency). 👑 marks the fund's own
currency, the one its NAV is computed in — not necessarily the one you trade in. A line at the
bottom of the results says so whenever a result shows 👑.

justETF converts the USD, CHF and GBP prices with its own exchange rates. Is your reporting
currency another one? Pick any of the four: LibreFolio converts with its own
[exchange rates](../../fx/index.md).

### ⭐ Your Preferred Currency {: #preferred-currency }

Always pick the same currency? Choose it once as **Preferred currency**, under **JustETF** in
**Settings › Plugins**, or with **Configure** next to the provider in the asset dialog. Your
searches then show each ETF once, in that currency, with 👑 only on the funds computed in it.
**All currencies**, the default, shows all four.

It is a personal setting: it changes only your own searches, never a price or an asset you already
have. See [Plugin Settings](../../settings/plugins.md#search-preferences).

## ⚠️ Limits

- ISIN only: for a ticker, use [Yahoo Finance](yahoo-finance.md).
- Only the EUR price is live.
- LibreFolio reads justETF's website: a change on their side can stop the prices until LibreFolio
  is updated.

## 🔗 Related

- 🔌 **[Asset Providers](index.md)** — Compare the providers
- 🧩 **[Plugin Settings](../../settings/plugins.md)** — Your preferred currency in search
- 🛠️ **For developers: [JustETF Provider](../../../developer/backend/assets/provider_justetf.md)** — Live quotes, charts and caching
