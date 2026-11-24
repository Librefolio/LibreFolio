# <img src="https://www.coingecko.com/favicon.ico" alt=""> CoinGecko

CoinGecko prices cryptocurrencies: bitcoin, ether, stablecoins and thousands of tokens, in your own currency. It needs
a free CoinGecko account and its API key, which an administrator sets once for the whole instance.

**[Powered by CoinGecko](https://www.coingecko.com/)**

## 🔍 What It Offers

- **Current price**: the coin's latest price, in the currency you chose for the asset. LibreFolio asks again every
  30 minutes by default.
- **History**: one closing price per day. Crypto trades all day long: each day's close is the price at midnight UTC.
- **Search**: by name or symbol («bitcoin», «BTC»), the biggest coins first.
- **Details**: the name, the type (Crypto), the logo and the symbol as ticker.

## 🔑 What You Need

- **A free CoinGecko account** with a **Demo** API key ([how to get and set it](../../settings/coingecko-key.md)). It needs no credit card. The Demo plan allows 10 000 calls a
  month and 100 a minute ([CoinGecko's plans](https://www.coingecko.com/en/api/pricing)): plenty for a personal
  portfolio (see [Credits](#credits)).
- **An administrator** puts the key in **Settings › Plugins**, on the **CoinGecko** card under **Shared settings**:
  **API key**, and **Plan** «Demo (free)». The server's environment can set it instead
  (`LIBREFOLIO_PLUGIN_GROUP_COINGECKO_API_KEY`). The key is a [secret](../../settings/plugins.md#secrets): once saved,
  nobody can read it back.
- **A self-hosted LibreFolio.** CoinGecko is offered on instances you run yourself; a hosted service may switch it off.

Until the key is set, CoinGecko is [to configure](../../settings/plugins.md#configured): its chip in **Search Online**
is switched off, and you cannot assign it to an asset.

## ✏️ Set It Up

**Search Online** sets it up for you: search «bitcoin» and pick the CoinGecko result. LibreFolio fills in the name,
the type and the currency, and the coin's symbol as ticker. The CoinGecko id (`coingecko:bitcoin`) joins the asset's
other identifiers.

By hand, in **Provider Assignment**:

1. Choose **CoinGecko** as **Provider**.
2. Type the coin's **CoinGecko ID**: CoinGecko's own name for it, such as `bitcoin`, `ethereum` or `usd-coin`. It is the
   last part of the coin's address on coingecko.com (`coingecko.com/en/coins/bitcoin`).
3. In **Price currency**, pick the asset's own currency (EUR by default). It must be the currency of the asset: a
   price in another one is not stored.

### ⭐ Your Preferred Currency {: #preferred-currency }

The search shows each coin in one currency. Choose it as **Preferred currency** on the **CoinGecko** card under
**Prices** in **Settings › Plugins**, or with **Configure** next to the provider in the asset dialog (EUR by default). It is a
personal setting: it changes only your own searches, never a price or an asset you already have.

## 📅 One Year of History {: #one-year }

The free Demo plan gives the **last 365 days** of prices, no more. When you ask for an older start (a new asset asks
for its whole history), LibreFolio stores the year it gets and the sync result says from which day the prices start.

The prices LibreFolio saves stay: the history grows by one day every day. For the years before:

1. Find the old daily prices elsewhere, for example on an exchange's site or in a spreadsheet you keep.
2. Open the asset, then the [Data Editor](../detail/data-editor.md).
3. Load them with **Import CSV** ([how](../detail/data-editor.md#import-from-csv)).

A paid CoinGecko plan gives more history: two years on Basic, back to 2013 from Analyst up. Set its key and choose
the plan «Pro (paid)».

## 🪙 Credits {: #credits }

Every call to CoinGecko spends one credit of the account. LibreFolio asks for the current price of **all your
CoinGecko assets in one call**, so the cost depends little on how many you hold. With the default refresh of
30 minutes, a month costs about:

| CoinGecko assets | 5 | 20 | 50 | the most the Demo plan holds |
|---|---|---|---|---|
| Credits a month | ~1 800 | ~2 700 | ~4 400 | ~150 coins |

To spend fewer, an administrator can set a longer **Price refresh** (60, 120 or 240 minutes) on the **CoinGecko**
card under **Prices** in **Settings › Plugins**. CoinGecko's [Developer Dashboard](https://www.coingecko.com/en/developers/dashboard) shows
the account's exact usage.

LibreFolio keeps its own count: the **Calls** block of the **CoinGecko** card under **Shared settings** shows the calls
of this instance, and an administrator can cap each window, for example the month below the plan's credits
(see **Calls and Their Limits** in [Plugin Settings](../../settings/plugins.md)). CoinGecko's month may start again on another day than
LibreFolio's, so the two counts can differ.

## 🏷️ Terms and Attribution {: #attribution }

The prices are CoinGecko's, under [CoinGecko's API terms](https://www.coingecko.com/en/api_terms): whoever creates
the key accepts them. Read them. Among other things, they discourage keeping CoinGecko's data, while LibreFolio stores
every price it fetches, from any source. They also ask that the data be shown with **«Powered by CoinGecko»** and a
link to its site. LibreFolio shows it on CoinGecko's own pages: at the top of this page, and on CoinGecko's card in
**Settings › Plugins**. A CoinGecko asset carries CoinGecko's icon, and its page links to the coin on coingecko.com.

## ⚠️ Limits

- **One year of history** on the free plan ([above](#one-year)).
- **No volume**: CoinGecko's volume adds up every exchange, so LibreFolio does not use it.
- **Very small prices** keep 12 decimal places: a coin worth less than 0.000000000001 (1e-12) cannot be stored.
- **The key is the instance's**: every user's CoinGecko assets spend the same account's credits.

## 🔗 Related

- 🔌 **[Asset Providers](index.md)** — Compare the providers
- 🔑 **[Get and Set the CoinGecko Key](../../settings/coingecko-key.md)** — From no account to the first price
- 🧩 **[Plugin Settings](../../settings/plugins.md)** — The key, the plan and your preferred currency
- ✏️ **[Data Editor](../detail/data-editor.md)** — Import the older prices
- 🛠️ **For developers: [CoinGecko Provider](../../../developer/backend/assets/provider_coingecko.md)** — The SDK, the
  daily closes and the errors
