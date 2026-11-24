# 🔑 Get and Set the CoinGecko Key

[CoinGecko](../assets/providers/coingecko.md) prices your crypto, and it needs an API key: a free one is enough. This
page takes you from no account to the first price, in five steps. Setting the key needs an **administrator** of your
LibreFolio.

## 💶 What It Costs {: #cost }

Nothing. A CoinGecko account is free and asks for **no credit card**. Its **Demo** plan allows 10 000 calls a month and
100 a minute ([CoinGecko's plans](https://www.coingecko.com/en/api/pricing)). With a usual portfolio and the default
settings, LibreFolio uses about 2 700 a month: see the [credits table](../assets/providers/coingecko.md#credits).

## 1️⃣ Create the Account {: #account }

1. Open [CoinGecko's API plans](https://www.coingecko.com/en/api/pricing).
2. Under **Demo**, choose **Start for Free** and sign up.

CoinGecko's own guide, [Setting Up Your API Key](https://docs.coingecko.com/docs/setting-up-your-api-key), shows its
screens step by step.

## 2️⃣ Create the Key {: #key }

1. Open the [Developer Dashboard](https://www.coingecko.com/en/developers/dashboard) of your account.
2. Choose **+ Add New Key**.
3. Copy the key. Keep it to yourself: it is the password of your CoinGecko account's API.

## 3️⃣ Put It in LibreFolio {: #set }

As an administrator:

1. Open **Settings › Plugins**.
2. Under **Shared settings**, find the **CoinGecko** card: it is the CoinGecko account every CoinGecko plugin uses.
3. Paste the key into **API key**, keep **Plan** on «Demo (free)», and **Save**.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="plugin-group-coingecko" alt="The CoinGecko card under Shared settings, before the key"
         style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

The card's badge turns from **To configure** to **Configured**, and the key shows as **Set**. The key is a
[secret](plugins.md#secrets): once saved, nobody can read it back, not even an administrator. To change it, paste a
new one.

!!! tip "On the server instead"

    Whoever runs the server can set the key in the environment, `LIBREFOLIO_PLUGIN_GROUP_COINGECKO_API_KEY` (and
    `LIBREFOLIO_PLUGIN_GROUP_COINGECKO_PLAN`, `demo` or `pro`). The field then cannot be changed from the page
    ([Set by the Server](plugins.md#set-by-the-server)).

## 4️⃣ Try It {: #try }

1. Open **Assets** and create a new asset.
2. In **Search Online**, type «bitcoin»: the CoinGecko chip is now on, and its results are among the others.
3. Pick **Bitcoin**. LibreFolio fills in the name, the type and the currency, then runs **Test Configuration**:
   a price and a few days of history mean the key works.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="coingecko-search" alt="Search Online with CoinGecko results for bitcoin"
         style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

When you create the asset, LibreFolio loads its history: the last year on the Demo plan
([why](../assets/providers/coingecko.md#one-year)).

## 5️⃣ Keep an Eye on the Credits {: #credits }

- CoinGecko's [Developer Dashboard](https://www.coingecko.com/en/developers/dashboard) shows how many calls the key
  has used this month.
- LibreFolio counts them too: the **Calls** block of the **CoinGecko** card under **Shared settings**, in **Settings ›
  Plugins**, shows this instance's calls this minute, hour, day, week and month, and an administrator can set a limit
  on each (see **Calls and Their Limits** in [Plugin Settings](plugins.md)). CoinGecko's month may start again on another day than
  LibreFolio's (the 1st, UTC): the two counts can differ, and CoinGecko's Dashboard has the account's own.
- Running short? An administrator can set a longer **Price refresh** (60, 120 or 240 minutes) on the CoinGecko card
  under **Prices** in **Settings › Plugins**: the prices update less often, and the credits last longer.

## ⚠️ Good to Know {: #limits }

- **One year of history** on the free plan: load the older prices with **Import CSV** in the asset's
  [Data Editor](../assets/detail/data-editor.md#import-from-csv).
- **Self-hosted only**: CoinGecko is offered on instances you run yourself; a hosted service may switch it off.
- **The data are CoinGecko's**, under [its API terms](https://www.coingecko.com/en/api_terms): whoever creates the key
  accepts them. LibreFolio credits CoinGecko with «Powered by CoinGecko», as the terms ask
  ([where](../assets/providers/coingecko.md#attribution)).
- **One key for the whole instance**: every user's CoinGecko assets spend the same account's credits.

## 🔗 Related

- 🦎 **[CoinGecko](../assets/providers/coingecko.md)** — What the provider offers, the year of history, the credits
- 🧩 **[Plugin Settings](plugins.md)** — Secrets, settings set by the server, «to configure»
