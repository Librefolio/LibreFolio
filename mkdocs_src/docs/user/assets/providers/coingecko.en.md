# <img src="https://www.coingecko.com/favicon.ico" alt=""> CoinGecko

CoinGecko prices cryptocurrencies: bitcoin, ether, stablecoins and thousands of tokens, in your own currency. It is also
a source of their [profile](#profile): what the coin is, its website, its market capitalisation. Both need one free
CoinGecko account and its API key, which an administrator sets once for the whole instance.

**[Powered by CoinGecko](https://www.coingecko.com/)**

## 🔍 What It Offers

- **Current price**: the coin's latest price, in the currency you chose for the asset. LibreFolio asks again every
  30 minutes by default.
- **History**: one closing price per day. Crypto trades all day long: each day's close is the price at midnight UTC.
- **Search**: by name or symbol («bitcoin», «BTC»), the biggest coins first.
- **Details**: the name, the type (Crypto), the logo and the symbol as ticker.
- **Profile**: the description, the website and the other data of the **Profile** tab ([below](#profile)).

## 🔑 What You Need

- **A free CoinGecko account** with a **Demo** API key ([how to get and set it](../../settings/coingecko-key.md)). It needs no credit card. The Demo plan allows 10 000 calls a
  month and 100 a minute ([CoinGecko's plans](https://www.coingecko.com/en/api/pricing)): plenty for a personal
  portfolio (see [Credits](#credits)).
- **An administrator** puts the key in **Settings › Plugins**, on the **CoinGecko** card under **Shared settings**:
  **API key**, and **Plan** «Demo (free)». The server's environment can set it instead
  (`LIBREFOLIO_PLUGIN_GROUP_COINGECKO_API_KEY`). The key is a [secret](../../settings/plugins.md#secrets): once saved,
  nobody can read it back.
- **A self-hosted LibreFolio.** CoinGecko is meant for instances you run yourself ([why](#self-hosted)); a hosted
  service may switch it off.

Until the key is set, CoinGecko is [to configure](../../settings/plugins.md#configured): its chip in **Search Online**
is switched off, you cannot assign it to an asset, and no profile is read from it.

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

## 👤 The Profile {: #profile }

CoinGecko is also an [enricher](../detail/profile.md#enrichers): a source that fills the **Profile** tab of the asset
page, **for cryptocurrencies only**. It reads:

| Item | What you get |
|---|---|
| **Description** | CoinGecko's own text, in English |
| **Website** | The coin's home page, as a link |
| **Inception date** | The coin's launch day: the day of its first block. Many tokens have none |
| **Market capitalisation** | In the currency you choose ([below](#market-cap-currency)), dated with CoinGecko's own day. It follows the weekly read, not the price. CoinGecko writes 0 when it does not know it: LibreFolio then shows nothing |
| **Categories** | CoinGecko's own words, all of them, as one text. They mix different things: kinds of coin, the ecosystems it lives in, the indices that hold it |

It never fills the **legal form** or the coin's supply: CoinGecko does not state the first, and the profile has no place
for the second. What CoinGecko does not give stays empty.

### 🔎 Bind It to a Coin

Open the **Enrichers** window from the asset form ([Choose the enrichers](../detail/profile.md#choose-enrichers)):

- **A coin already priced by CoinGecko** is recognised straight away, when the window opens. CoinGecko enters
  **Enrichers chosen** already bound, with the currency of its prices; on an asset that already has other enrichers it
  waits in **Not in the list**, with **+**.
- **Any other coin** (priced by another provider, or by hand): use **Search online** and type its name or its symbol. Many
  coins share a symbol: check the name before you add one.
- **By hand**: the identifier is the **CoinGecko ID**, the same as for the prices (`bitcoin`). **Test the binding** says
  which coin it finds.

Then **Use these enrichers** and save the asset. From there the profile is read once a week, and when you press
**[Refresh](../detail/profile.md#refresh)**.

### 💶 Market Capitalisation Currency {: #market-cap-currency }

Open the row of CoinGecko in the **Enrichers** window (✏️, **Change the binding**) and choose **Market capitalisation
currency**. It is EUR by default, or the currency of the prices when CoinGecko prices the coin. It changes the market
capitalisation only, never a price.

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
30 minutes, a month of prices costs about:

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

The [profile](#profile) spends the same credits, apart from the table:

- **The weekly read: one credit per coin**, about 4–5 a month for each coin bound to CoinGecko's profile. A read you ask
  for (**Refresh**, **Ask**) costs the same, unless the same data were already read in the last 30 minutes.
- **One credit each time LibreFolio asks CoinGecko who a coin is**: when the **Enrichers** window recognises it, for each
  search, and for each **Test the binding**.

Prices and profile count together in that **Calls** block. When a limit there is full, LibreFolio makes no more calls to
CoinGecko, neither for prices nor for the profile, until the limit's window starts again: searches and tests are refused
too, and you can try again later. What is already saved stays.

## 🏷️ Terms and Attribution {: #attribution }

The prices and the profile data are CoinGecko's, under [CoinGecko's API terms](https://www.coingecko.com/en/api_terms): whoever creates
the key accepts them. Read them. Among other things, they discourage keeping CoinGecko's data, while LibreFolio stores
every price it fetches and every profile value it reads, from any source. They also ask that the data be shown with
**«Powered by CoinGecko»** and a link to its site. LibreFolio shows it on CoinGecko's own pages: at the top of this page,
and on CoinGecko's card under **Prices** in **Settings › Plugins**. The asset's pages, its **Profile** tab included, do
not repeat it: a CoinGecko asset carries CoinGecko's icon, and its page links to the coin on coingecko.com.

### 🏠 Self-Hosted Instances {: #self-hosted }

CoinGecko's prices and profile are meant for self-hosted instances, the ones you run yourself. Nothing in LibreFolio's
code blocks them elsewhere. The administrator who turns CoinGecko on for a paid or hosted service, or who uses a paid
CoinGecko plan, is the one responsible for respecting CoinGecko's terms.

## ⚠️ Limits

- **One year of history** on the free plan ([above](#one-year)).
- **No volume**: CoinGecko's volume adds up every exchange, so LibreFolio does not use it.
- **Very small prices** keep 12 decimal places: a coin worth less than 0.000000000001 (1e-12) cannot be stored.
- **The profile is for crypto only**: CoinGecko is not offered as an enricher for any other asset type.
- **The key is the instance's**: every user's CoinGecko assets, prices and profile, spend the same account's credits.

## 🔗 Related

- 🔌 **[Asset Providers](index.md)** — Compare the providers
- 👤 **[Profile](../detail/profile.md)** — The Profile tab, its enrichers and when they read
- 🔑 **[Get and Set the CoinGecko Key](../../settings/coingecko-key.md)** — From no account to the first price
- 🧩 **[Plugin Settings](../../settings/plugins.md)** — The key, the plan and your preferred currency
- ✏️ **[Data Editor](../detail/data-editor.md)** — Import the older prices
- 🛠️ **For developers: [CoinGecko Provider](../../../developer/backend/assets/provider_coingecko.md)** — The SDK, the
  daily closes and the errors
- 🛠️ **For developers: [the CoinGecko enricher](../../../developer/architecture/patterns/enricher_plugin_guide.md#coingecko)** —
  The profile, on the same account
