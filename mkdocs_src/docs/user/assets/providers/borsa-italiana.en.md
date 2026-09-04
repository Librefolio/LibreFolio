# 🇮🇹 Borsa Italiana

**Borsa Italiana** is the Italian stock exchange, operated by Euronext. LibreFolio includes a dedicated **asset data provider** that fetches prices, historical series, and instrument metadata directly from the Borsa Italiana website.

---

## 🔍 What It Provides

| Data | Description |
|------|-------------|
| **Current price** | Last official market price for listed instruments; fund NAV only when dated today |
| **Historical prices** | Daily OHLCV for listed instruments; one NAV point at the real NAV date for funds |
| **Instrument metadata** | ISIN, market segment, currency, and alternative identifiers when available |

Assets traded on Borsa Italiana include Italian stocks (MTA/MIL segment), ETFs (ETFplus), bonds (MOT), and mutual funds/SICAVs.

---

## ⚙️ Configuration

No API key or registration is required — the provider scrapes public data from the Borsa Italiana website. Configuration is available per-asset in the **Provider Config** panel on the asset detail page.

1. Navigate to the asset you want to track.
2. Open the **⚙️ Provider Config** panel.
3. Select **Borsa Italiana** from the provider list.
4. Enter the **ISIN** for listed instruments. For funds, use Smart Search so LibreFolio can capture the Borsa internal fund code automatically.
5. Save — LibreFolio will fetch the first historical series on the next sync.

!!! tip "Finding the ISIN"

    You can look up the ISIN on [borsaitaliana.it](https://www.borsaitaliana.it) by searching for the instrument name. The ISIN is shown on every instrument detail page.

!!! tip "Smart Search can use Borsa links"

    If normal search cannot find a fund, paste or search with the Borsa Italiana fund/detail page
    URL. LibreFolio's smart search can resolve supported Borsa pages, attach the right
    `provider_params`, and make the fund priceable by its internal code.

---

## 🔄 Synchronisation

The Borsa Italiana provider participates in the standard **asset sync** cycle. Trigger manually from the asset detail page with the **🔄 Sync** button, or let the scheduled background job run overnight.

!!! note "Rate limiting"

    The provider applies automatic throttling to avoid being blocked by Borsa Italiana. If you have many assets from this exchange, full sync may take a few minutes.

!!! note "Mutual funds (NAV)"

    Mutual funds and SICAVs are priced by their daily **NAV**, published once per day with a delay.
    LibreFolio prices each fund by its Borsa internal fund code, not by ISIN. Price history shows one
    NAV point at its real date, and current value is refreshed only when the published NAV is dated
    today (otherwise your most recent purchase price is used as the estimate).

!!! note "Alternative identifiers"

    Some imported or provider-discovered identifiers are stored as an editable list of alternative
    identifiers. For Borsa Italiana funds, this list can include the internal fund code while the
    real ISIN remains the main identifier when available.

---

## 🔗 Developer Documentation

For implementation details (request format, HTML parsing strategy, field mapping), see:

→ [Developer Manual — Borsa Italiana Provider](../../../developer/backend/assets/provider_borsa_italiana.md)

---

## 🔗 Related

- 📋 **[Assets Overview](../index.md)** — Manage your asset library
- 🏦 **[Asset Providers](./index.md)** — Other data sources
- 📡 **[justETF](./justetf.md)** — Alternative source for ETF data
