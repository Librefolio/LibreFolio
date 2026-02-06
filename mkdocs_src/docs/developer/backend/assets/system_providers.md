# System Providers (Assets)

LibreFolio includes two powerful "system" providers for asset pricing that do not rely on a specific external API. They provide flexibility for tracking a wide range of assets.

## CSS Scraper (`cssscraper`)

The CSS Scraper is a versatile provider that can extract a price from any public webpage using a CSS selector.

### How it Works

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

### Use Cases

- Tracking the price of an asset from a financial news website.
- Scraping data from a niche market data provider that doesn't have an API.
- Tracking the value of a collectible from an auction site.

### Limitations

- **No Historical Data**: It can only fetch the current value.
- **Fragile**: If the website's layout changes, the CSS selector may break.
- **Requires Public Access**: It cannot access pages that require a login.

## Scheduled Investment (`scheduled_investment`)

This is a synthetic provider that calculates the value of an asset based on a predefined interest schedule. It does not make any external calls.

### How it Works

1. **Configuration**: The asset's value is determined by its `interest_schedule` stored in the `provider_params`. This schedule defines:
    - Interest rate periods (start date, end date, annual rate).
    - **Compounding Type**: `SIMPLE` or `COMPOUND`.
    - **Day Count Convention**: `ACT/365`, `ACT/360`, `30/360`, etc.
    - **Late Interest**: A separate rate to apply after the scheduled maturity date.

2. **Calculation**:
    - The provider first calculates the current **principal** by summing up all `BUY` and `SELL` transactions for the asset.
    - It then calculates the **accrued interest** up to the requested date by applying the interest schedule to the principal.
    - The final value is `principal + accrued_interest`.

### Use Cases

- **P2P/Crowdfunding Loans**: Model a loan with a fixed interest rate.
- **Fixed-Rate Bonds**: Calculate the value of a bond including accrued interest.
- **Any asset with predictable cash flows**.

### Example

If you have a P2P loan of €1,000 with a 10% simple annual interest rate, the provider will calculate its value as:

- After 6 months: €1,000 (principal) + €50 (accrued interest) = €1,050.
- After 1 year: €1,000 (principal) + €100 (accrued interest) = €1,100.
