# 🔌 Providers

LibreFolio supports multiple pricing providers to automatically fetch current prices and historical data for your assets.

## 📊 Provider Comparison

| Provider | Current Price | History | Search | Identifier | Notes |
|----------|:---:|:---:|:---:|---|---|
| **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (e.g., `AAPL`, `VWCE.DE`) | Best for stocks, ETFs, mutual funds |
| **justETF** | ✅ | ✅ | ❌ | ISIN (e.g., `IE00BK5BQT80`) | European ETFs with detailed data |
| **CSS Scraper** | ✅ | ❌ | ❌ | URL | Scrape any web page for price data |
| **Scheduled Investment** | ✅ | ✅ | ❌ | Auto-generated | Fixed-income instruments with interest schedules |

## 🎯 Choosing a Provider

- **Stocks & ETFs**: Use **Yahoo Finance** — widest coverage, supports search
- **European ETFs**: Use **justETF** for more detailed European ETF data
- **Bonds on Borsa Italiana**: Use **CSS Scraper** to scrape prices directly
- **Savings accounts / Fixed deposits**: Use **Scheduled Investment** with interest rate schedules

## 📚 Provider Details

- [📈 Yahoo Finance](yahoo-finance.en.md)
- [📊 justETF](justetf.en.md)
- [🔍 CSS Scraper](css-scraper.en.md) — detailed guide for web scraping
- [🧮 Scheduled Investment](scheduled-investment.en.md)
