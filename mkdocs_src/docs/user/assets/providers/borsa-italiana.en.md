# 🇮🇹 Borsa Italiana

**Borsa Italiana** is the Milan stock exchange, run by Euronext. This provider reads prices, price
history and instrument details from its public website — no account or API key needed.

## 🔍 What It Offers

- **Current price**: the last market price. For a mutual fund, its NAV — only when it is dated
  today.
- **History**: daily open, high, low, close and volume. Mutual funds have no past series: each NAV
  is saved at its own date, so the history grows from the day you add the fund.
- **Search**: by name or ISIN. Each instrument appears twice, 🇮🇹 and 🇬🇧: the flag sets the
  language of its name and description. Indices are left out, as you cannot buy them. No result?
  LibreFolio also looks for a matching Borsa Italiana page on the web, unless your administrator
  has turned this off.
- **Details**: name, type, currency, a sector and a description (market, issuer, maturity, coupon);
  the ticker for stocks; for funds, the ISIN, the fund's features and its costs.

It covers what Borsa Italiana lists — Italian stocks, ETFs and ETCs (ETFplus), bonds (MOT,
ExtraMOT, EuroTLX) and closed-end funds (MIV) — plus mutual funds and SICAVs.

## 💱 Currency and Type

- **Currency** is the one Borsa Italiana quotes the prices in: EUR for ETFs and ETCs on ETFplus,
  even when the fund itself is denominated in USD; USD for a bond traded in dollars on EuroTLX. If
  LibreFolio cannot read it, it leaves your currency as it is — check it before saving.
- **Type**: ETFs, ETCs and ETNs all arrive as plain **ETF**. If you know what the fund holds,
  refine it (for example **Equity ETF** or **Commodity ETF**): a later
  [check against the provider's data](../create-edit.md#provider-data-comparison) keeps your choice.
- **Bonds** get the sector **Government Bonds** or **Corporate Bonds** (supranational issuers:
  **Financials**) and, when the issuer is recognised, its country — *United States of America*
  becomes **USA**.

## ✏️ Set It Up

**Search Online** fills in everything. To set the provider up by hand, open the asset with
**Edit** (✏️) — or **+ Add Asset** for a new one — and expand **Provider Assignment**:

1. Choose **Borsa Italiana** as **Provider**.
2. Type the instrument's **ISIN**, for example `IT0003128367` (ENEL). Every instrument page on
   [borsaitaliana.it](https://www.borsaitaliana.it) shows it.
3. Pick the **Language**: 🇬🇧 English or 🇮🇹 Italiano.
4. Click **Test Configuration**, then save.

**Search Online** also fills in the other three settings; set them by hand only in these cases.

??? note "🧾 Fund internal code — for a mutual fund or SICAV"

    Mutual funds are priced by Borsa Italiana's own fund code, not by the ISIN. Find the fund on
    [borsaitaliana.it](https://www.borsaitaliana.it/borsa/fondi/ricerca.html) and copy the code
    from its page address: in `…/borsa/fondi/dettaglio/2FADB602822.html` the code is
    `2FADB602822`. Leave the field empty for anything else.

??? note "🧭 Market MIC and Platform — when the instrument page does not open"

    Some markets must be named explicitly. Open the instrument on borsaitaliana.it: the code after
    the ISIN in the page address is the **Market MIC** — in `…/scheda/US912810TU25-ETLX.html` it is
    `ETLX`. **Platform** is needed only on EuroTLX, where it is `TLX`.

    | Market | Market MIC | Platform |
    |--------|:---:|:---:|
    | MTA (Italian stocks) | `MTAA` | — |
    | MOT (bonds) | `MOTX` | — |
    | ExtraMOT (bonds) | `XMOT` | — |
    | ETFplus (ETFs, ETCs) | `ETFP` | — |
    | MIV (closed-end funds) | `MIVX` | — |
    | EuroTLX (bonds) | `ETLX` | `TLX` |

    For example, the US Treasury bond `US912810TU25` on EuroTLX works once **Market MIC** is
    `ETLX` and **Platform** is `TLX`; its prices are in USD.

## 🧾 Mutual Funds and NAV

A fund's NAV is published once a day, with a delay. LibreFolio saves each NAV at the date it
refers to, never as today's price: until the next one arrives, the fund is valued at the latest
known price — that NAV, or your own trade if it is more recent.

The fund code is kept under **Other identifiers**; the real ISIN stays the main identifier when
the fund's page shows it.

## ⚠️ Limits

- LibreFolio spaces out its requests to the website, so syncing many Borsa Italiana assets can
  take a few minutes.
- A market LibreFolio cannot read yet gives an error asking you to report the ISIN on
  [GitHub](https://github.com/Librefolio/LibreFolio/issues).

## 🔗 Related

- 📋 **[Assets Overview](../index.md)** — Manage your asset library
- 🏦 **[Asset Providers](./index.md)** — Other data sources
- 📡 **[justETF](./justetf.md)** — Alternative source for ETF data
- 🛠️ **For developers: [Borsa Italiana Provider](../../../developer/backend/assets/provider_borsa_italiana.md)** — Requests, page parsing and field mapping
