# 🔌 Providers

LibreFolio supports multiple pricing providers to automatically fetch current prices and historical data for your assets.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="yahoo-finance/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Yahoo Finance favicon">
            <span class="card-title" style="margin: 0;">Yahoo Finance</span>
        </div>
        <span class="card-desc">Default provider for global stocks, ETFs, and mutual funds.</span>
    </a>
    <a href="justetf/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="justETF favicon">
            <span class="card-title" style="margin: 0;">justETF</span>
        </div>
        <span class="card-desc">European ETFs comparison, prices, and asset structures.</span>
    </a>
    <a href="borsa-italiana/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Borsa Italiana favicon">
            <span class="card-title" style="margin: 0;">Borsa Italiana</span>
        </div>
        <span class="card-desc">Italian stock exchange integration for Euronext instruments.</span>
    </a>
    <a href="css-scraper/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="/LibreFolio/static/icons/cssscraper.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="CSS Scraper icon">
            <span class="card-title" style="margin: 0;">CSS Scraper</span>
        </div>
        <span class="card-desc">Web page selector scraper for custom bond prices or exotics.</span>
    </a>
    <a href="scheduled-investment/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="/LibreFolio/static/icons/scheduled_investment.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Scheduled Investment icon">
            <span class="card-title" style="margin: 0;">Scheduled Investment</span>
        </div>
        <span class="card-desc">Fixed-income assets calculating value via interest rate schedules.</span>
    </a>
</div>

## 📊 Provider Comparison

| Provider | Current Price | History | Search | Identifier | Notes |
|----------|:---:|:---:|:---:|---|---|
| <img src="https://s.yimg.com/cv/apiv2/myc/finance/Finance_icon_0919_250x252.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Yahoo Finance** | ✅ | ✅ | ✅ | Ticker (e.g., `AAPL`, `VWCE.DE`) | Best for stocks, ETFs, mutual funds |
| <img src="https://www.justetf.com/android-chrome-144x144.png?v2" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **justETF** | ✅ (EUR) | ✅ | ✅ | ISIN (e.g., `IE00BK5BQT80`) | European ETFs, multi-currency |
| <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Borsa Italiana** | ✅ | ✅ | ✅ | ISIN or alpha code | Italian stocks, bonds, and ETFs |
| <img src="/LibreFolio/static/icons/cssscraper.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **CSS Scraper** | ✅ | ❌ | ❌ | URL | Scrape any web page for price data |
| <img src="/LibreFolio/static/icons/scheduled_investment.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **Scheduled Investment** | ✅ | ✅ | ❌ | Auto-generated | Fixed-income instruments with interest schedules |

## 🎯 Choosing a Provider

- **Stocks & ETFs**: Use **Yahoo Finance** — widest coverage, supports search
- **European ETFs**: Use **justETF** for more detailed European ETF data
- **Borsa Italiana**: Use Borsa Italiana directly for Euronext Milano listings
- **Bonds on Borsa Italiana**: Use **CSS Scraper** to scrape prices directly from the web
- **Savings accounts / Fixed deposits**: Use **Scheduled Investment** with interest rate schedules
