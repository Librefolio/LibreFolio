# 🌐 CSS Scraper Provider (`css_scraper`)

The CSS Scraper is a versatile provider that can extract a price from any public webpage using a CSS selector. It is one of the [Asset Providers](system_providers.md) — it does not rely on a specific financial data API.

📖 **User Guide**: [CSS Scraper — User Manual](../../../user/assets/providers/css-scraper.md)

---

## ⚙️ How it Works

1. **Configuration**: When assigning this provider to an asset, you must provide:
    - `identifier`: The URL of the webpage to scrape.
    - `identifier_type`: `URL` — the form's input type; it is stored as `IdentifierType.OTHER` (`map_input_type_to_identifier_type`), which is why `test_cases` use `OTHER`.
    - `provider_params`:
        - `current_css_selector` (**required**): The CSS selector to locate the price element on the page (e.g., `#sp-last`, `.price-value`).
        - `currency` (**required**): The currency of the price (ISO 4217).
        - `decimal_format` (optional): `us` (e.g., `1,234.56`) or `eu` (e.g., `1.234,56`). Default: `us`.
        - `timeout` (optional): HTTP request timeout in seconds. Default: `30`.
        - `user_agent` (optional): Custom User-Agent header. Default: `LibreFolio/1.0`.
        - `headers` (optional, not in `params_schema`, so not in the form): a dict of extra HTTP headers merged over the defaults (`User-Agent`, `Accept`, `Accept-Language: en-US,en;q=0.5`) with `mergedeep`.

2. **Execution**:
    - Fetches the HTML of the specified URL via `httpx` — a fresh `httpx.AsyncClient(timeout=…)` per call, `follow_redirects=True`, then `raise_for_status()`.
    - Uses **BeautifulSoup** (`html.parser`) and `select_one()` — the **first** element matching the selector. No JavaScript runs, so a price rendered client-side is invisible to the scraper.
    - Extracts the text content and parses it into a `Decimal` value, handling different number formats based on `decimal_format`.
    - `as_of_date` is always today. During a refresh the core stores that value as the day's price point, so a history builds up one sync at a time.

3. **`get_asset_url()`**: Returns the `identifier` URL itself (the page being scraped).

4. **`params_schema`**: Exposes all 5 configuration fields for dynamic form generation in the frontend. The fields declare no `label`, so the form shows the raw keys as captions, with each `description` as tooltip.

Error codes raised by `get_current_value()` (history always raises `NOT_IMPLEMENTED`):

| Code | When | Message starts with |
|---|---|---|
| `MISSING_PARAMS` | No params, or `current_css_selector` / `currency` missing | `CSS scraper requires provider_params` / `Missing required params` |
| `INVALID_PARAMS` | `decimal_format` other than `us` / `eu` | `decimal_format must be 'us' or 'eu'` |
| `NOT_FOUND` | The selector matches nothing | `Price element not found with selector` |
| `PARSE_ERROR` | Empty or non-numeric text | `Empty price text` / `Failed to parse price` |
| `HTTP_ERROR` | Non-2xx response | `HTTP error {status}: {reason}` |
| `REQUEST_ERROR` | Network error or timeout (`httpx.RequestError`) | `Request failed` |
| `SCRAPE_ERROR` | Anything else | `Scraping failed` |
| `NOT_AVAILABLE` | `httpx` / `beautifulsoup4` not installed | `httpx and beautifulsoup4 not available` |

---

## 🔢 Decimal Format Remapping

The `decimal_format` parameter controls how the scraped text is parsed into a number:

| Format | Input Example | Parsed Value |
|---|---|---|
| `us` (default) | `1,234.56` | `1234.56` |
| `eu` | `1.234,56` | `1234.56` |

The parser first removes whitespace and the symbols `€ $ £ ¥ %`. It then drops the group separator (`,` for US; `.` for EU, where `,` also becomes `.`) and converts to `Decimal`. Any other character — e.g. a currency code such as `EUR` next to the number — makes the conversion fail with `PARSE_ERROR`.

---

## ⚡ Caching & Performance

- **No response caching**: Each `get_current_value()` call performs a fresh HTTP request. This is intentional — scraped data may change frequently and the provider cannot predict staleness.
- **No connection pooling across calls**: each `get_current_value()` opens and closes its own `httpx.AsyncClient`.
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
- **Requires Public Access**: It cannot access pages that require a login, nor read prices that JavaScript adds after the page loads.
- **Rate limits**: No built-in rate limiting. High-frequency sync may trigger the target site's anti-bot protection.

---

## 🔗 Related Documentation

- 📖 [CSS Scraper — User Guide](../../../user/assets/providers/css-scraper.md) — End-user configuration guide
- 📦 [Providers Overview](system_providers.md) — All available providers
- 💰 [Asset Architecture](architecture.md) — Sync pipeline and price queries
- 📈 [Asset Plugin Guide](../../architecture/patterns/asset_plugin_guide.md) — How to create a new provider

