# <img src="../../../../static/cssscraper.png" alt=""> CSS Scraper

The CSS Scraper reads an asset's price from any public web page, using a CSS selector that points
at the number. Use it when no other provider covers the instrument. In the **Provider** list it is
called **CSS Web Scraper**.

## 🔍 What It Offers

- ✅ **Current price**: read from the page at every sync, in the currency you choose.
- ❌ **History**: none. Each sync saves the day's price, so the history grows from the day you
  start.
- ❌ **Search** and **details**: none — you enter the page address and the settings yourself.

## 🧩 Set It Up

### 1️⃣ Copy the Price's CSS Selector

The selector tells LibreFolio which element of the page holds the price.

=== "Chrome"

    1. Open the page and right-click the price.
    2. Choose **Inspect** (or press `F12`): DevTools highlights the price element.
    3. Right-click the highlighted element, then **Copy** → **Copy selector**.

=== "Firefox"

    1. Open the page and right-click the price.
    2. Choose **Inspect** (or press `F12`): the Inspector highlights the price element.
    3. Right-click the highlighted element, then **Copy** → **CSS Selector**.

### 2️⃣ Fill In the Provider Settings

In **Provider Assignment**, choose **CSS Web Scraper** and paste the page address into **URL**. The
settings appear under their technical names:

| Setting | Required | What to enter |
|---|:---:|---|
| `current_css_selector` | ✅ | The selector you copied, e.g. `.summary-value strong` |
| `currency` | ✅ | The currency of the price, e.g. `EUR` |
| `decimal_format` | — | `us` for `1,234.56` (the default) or `eu` for `1.234,56` |
| `timeout` | — | Seconds to wait for the page (default `30`) |
| `user_agent` | — | How LibreFolio introduces itself to the site (default `LibreFolio/1.0`) |

### 3️⃣ Test It

Click **Test Configuration**: **Current Price** must show the number you see on the page. The ⚠️ on
**History** is expected, as this provider has none.

!!! example "A BTP on Borsa Italiana"

    - **URL**: `https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en`
    - `current_css_selector`: `.summary-value strong`
    - `currency`: `EUR`
    - `decimal_format`: `us` — the English page shows `100.39`. The Italian page (`lang=it`)
      shows `100,39`, so there use `eu`.

    For instruments listed on Borsa Italiana, the [Borsa Italiana](borsa-italiana.md) provider
    also brings their history.

## 🛠️ Troubleshooting

| What you see | What to do |
|---|---|
| **Price element not found** | The page layout may have changed: copy the selector again. |
| **Failed to parse price** | Check `decimal_format`. The element must hold just the number: spaces, €, $, £, ¥ and % are ignored, letters such as `EUR` are not. |
| **HTTP error** or **Request failed** | Check the URL; raise `timeout` for a slow site. Error 403 means the site refuses automated visits. |
| A wrong number | The selector matches another element (LibreFolio uses the first match): make it more specific. |

## ⚠️ Limits

- LibreFolio reads the page as the site sends it, without running its scripts: a price filled in
  by JavaScript cannot be read, nor can pages behind a login.
- When the site changes its layout, the selector may stop matching: test again and copy a new one.

## 🔗 Related

- ✏️ **[Data Editor](../detail/data-editor.md)** — Enter or correct prices by hand
- 🛠️ **For developers: [CSS Scraper Provider](../../../developer/backend/assets/provider_cssscraper.md)** — Request, parsing and error codes

