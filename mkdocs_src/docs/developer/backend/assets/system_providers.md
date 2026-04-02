# 🔌 System Providers (Assets)

LibreFolio includes two powerful "system" providers for asset pricing that do not rely on a specific external API. They provide flexibility for tracking a wide range of assets.

## 🌐 CSS Scraper (`cssscraper`)

The CSS Scraper is a versatile provider that can extract a price from any public webpage using a CSS selector.

### ⚙️ How it Works

1. **Configuration**: When assigning this provider to an asset, you must provide:
    - `identifier`: The URL of the webpage to scrape.
    - `provider_params`:
        - `current_css_selector`: The CSS selector to locate the price element on the page (e.g., `.price-value`, `#stock-price`).
        - `currency`: The currency of the price.
        - `decimal_format`: `us` (e.g., `1,234.56`) or `eu` (e.g., `1.234,56`).

2. **Execution**:
    - It fetches the HTML of the specified URL.
    - It uses **BeautifulSoup** to parse the HTML and find the element matching the CSS selector.
    - It extracts the text content of the element and parses it into a `Decimal` value, handling different number formats.

### 📋 Use Cases

- Tracking the price of an asset from a financial news website.
- Scraping data from a niche market data provider that doesn't have an API.
- Tracking the value of a collectible from an auction site.

### ⚠️ Limitations

- **No Historical Data**: It can only fetch the current value.
- **Fragile**: If the website's layout changes, the CSS selector may break.
- **Requires Public Access**: It cannot access pages that require a login.

## 📅 Scheduled Investment (`scheduled_investment`)

This is a synthetic provider that calculates the value of an asset based on a predefined interest schedule. It does not make any external calls.

### ⚙️ How it Works

1. **Configuration**: The asset's value is determined entirely by `provider_params`, which include:
    - `initial_value`: The principal / face value of the asset (required, > 0).
    - `currency`: The asset's currency (ISO 4217).
    - `schedule`: Interest rate periods (start date, end date, annual rate).
    - **Compounding Type**: `SIMPLE` or `COMPOUND`.
    - **Day Count Convention**: `ACT/365`, `ACT/360`, `30/360`, etc.
    - **Late Interest**: A separate rate to apply after the scheduled maturity date.
    - `asset_events`: Planned events (INTEREST payouts, PRICE_ADJUSTMENT write-downs).

2. **Calculation** (pure deterministic — no DB access, no transaction dependency):
    - Starts with `initial_value` as the base principal.
    - Calculates **accrued interest** up to the requested date using the schedule periods.
    - Applies **asset events**: INTEREST events subtract from price (ex-date drop), PRICE_ADJUSTMENT events modify value algebraically.
    - `price(d) = initial_value + accrued_interest - Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)`
    - Interest is always calculated on `initial_value`, not the running value.

3. **Events**: This provider sets `supports_events = True` and returns events filtered to the requested date range via `FAHistoricalData.events`.

### 📋 Use Cases

- **P2P/Crowdfunding Loans**: Model a loan with a fixed interest rate and periodic interest payouts.
- **Fixed-Rate Bonds**: Calculate the value of a bond including accrued interest and coupon payments.
- **Any asset with predictable cash flows**.

### 📐 Example

If you have a P2P loan of €10,000 with a 5% simple annual interest rate and an INTEREST event of €250 on July 1:

- Before July 1: value = €10,000 + accrued interest (e.g., after 6 months: €10,250)
- After July 1 (ex-date): value drops by €250 (interest paid out) → continues accruing from €10,000 base
