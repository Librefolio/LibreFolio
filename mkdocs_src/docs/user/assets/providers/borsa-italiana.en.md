# 🇮🇹 Borsa Italiana

**Borsa Italiana** is the Italian stock exchange, operated by Euronext. LibreFolio includes a dedicated **asset data provider** that fetches prices, historical series, and instrument metadata directly from the Borsa Italiana website.

---

## 🔍 What It Provides

| Data | Description |
|------|-------------|
| **Current price** | Last official market price |
| **Historical OHLCV** | Daily open/high/low/close/volume series |
| **Instrument metadata** | ISIN, market segment, currency |

Assets traded on Borsa Italiana include Italian stocks (MTA/MIL segment), ETFs (ETFplus), bonds (MOT), and funds.

---

## ⚙️ Configuration

No API key or registration is required — the provider scrapes public data from the Borsa Italiana website. Configuration is available per-asset in the **Provider Config** panel on the asset detail page.

1. Navigate to the asset you want to track.
2. Open the **⚙️ Provider Config** panel.
3. Select **Borsa Italiana** from the provider list.
4. Enter the **ISIN** or the Borsa Italiana ticker code.
5. Save — LibreFolio will fetch the first historical series on the next sync.

!!! tip "Finding the ISIN"

    You can look up the ISIN on [borsaitaliana.it](https://www.borsaitaliana.it) by searching for the instrument name. The ISIN is shown on every instrument detail page.

---

## 🔄 Synchronisation

The Borsa Italiana provider participates in the standard **asset sync** cycle. Trigger manually from the asset detail page with the **🔄 Sync** button, or let the scheduled background job run overnight.

!!! note "Rate limiting"

    The provider applies automatic throttling to avoid being blocked by Borsa Italiana. If you have many assets from this exchange, full sync may take a few minutes.

---

## 🔗 Developer Documentation

For implementation details (request format, HTML parsing strategy, field mapping), see:

→ [Developer Manual — Borsa Italiana Provider](../../../developer/backend/assets/provider_borsa_italiana.md)

---

## 🔗 Related

- 📋 **[Assets Overview](../index.md)** — Manage your asset library
- 🏦 **[Asset Providers](./index.md)** — Other data sources
- 📡 **[justETF](./justetf.md)** — Alternative source for ETF data
