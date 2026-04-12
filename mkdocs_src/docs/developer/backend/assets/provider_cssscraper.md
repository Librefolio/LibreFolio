# 🌐 CSS Scraper Provider (`css_scraper`)

The CSS Scraper is a versatile provider that can extract a price from any public webpage using a CSS selector. It is one of the [Asset Providers](system_providers.md) — it does not rely on a specific financial data API.

📖 **User Guide**: [CSS Scraper — User Manual](../../../user/assets/providers/css-scraper.md)

---

## ⚙️ How it Works

1. **Configuration**: When assigning this provider to an asset, you must provide:
    - `identifier`: The URL of the webpage to scrape.
    - `identifier_type`: `URL`
    - `provider_params`:
        - `current_css_selector` (**required**): The CSS selector to locate the price element on the page (e.g., `#sp-last`, `.price-value`).
        - `currency` (**required**): The currency of the price (ISO 4217).
        - `decimal_format` (optional): `us` (e.g., `1,234.56`) or `eu` (e.g., `1.234,56`). Default: `us`.
        - `timeout` (optional): HTTP request timeout in seconds. Default: `30`.
        - `user_agent` (optional): Custom User-Agent header. Default: `LibreFolio/1.0`.

2. **Execution**:
    - Fetches the HTML of the specified URL via `httpx` (async HTTP client).
    - Uses **BeautifulSoup** to parse the HTML and find the element matching the CSS selector.
    - Extracts the text content and parses it into a `Decimal` value, handling different number formats based on `decimal_format`.

3. **`get_asset_url()`**: Returns the `identifier` URL itself (the page being scraped).

4. **`params_schema`**: Exposes all 5 configuration fields for dynamic form generation in the frontend.

---

## 🔢 Decimal Format Remapping

The `decimal_format` parameter controls how the scraped text is parsed into a number:

| Format | Input Example | Parsed Value |
|---|---|---|
| `us` (default) | `1,234.56` | `1234.56` |
| `eu` | `1.234,56` | `1234.56` |

The parser strips all non-numeric characters except the decimal separator, then converts to `Decimal`. Group separators (`,` for US, `.` for EU) are removed first.

---

## ⚡ Caching & Performance

- **No response caching**: Each `get_current_value()` call performs a fresh HTTP request. This is intentional — scraped data may change frequently and the provider cannot predict staleness.
- **Connection pooling**: Uses `httpx.AsyncClient` with connection reuse across requests.
- **Timeout handling**: Configurable per-asset via `timeout` parameter. Default 30s prevents blocking on slow sites.

---

## 📋 Use Cases

- Tracking the price of an asset from a financial news website.
- Scraping data from a niche market data provider that doesn't have an API.
- Tracking the value of a collectible from an auction site.

---

## ⚠️ Limitations

- **No Historical Data**: `supports_history = False`. It can only fetch the current value.
- **Fragile**: If the website's layout changes, the CSS selector may break. Use the **probe** endpoint to test before saving.
- **Requires Public Access**: It cannot access pages that require a login.
- **Rate limits**: No built-in rate limiting. High-frequency sync may trigger the target site's anti-bot protection.

---

## 🔗 Related Documentation

- 📖 [CSS Scraper — User Guide](../../../user/assets/providers/css-scraper.md) — End-user configuration guide
- 📦 [Providers Overview](system_providers.md) — All available providers
- 💰 [Asset Architecture](architecture.md) — Sync pipeline and price queries
- 📈 [Asset Plugin Guide](../../architecture/patterns/asset_plugin_guide.md) — How to create a new provider

