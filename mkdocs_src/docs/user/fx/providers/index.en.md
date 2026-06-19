# 🔌 FX Providers

LibreFolio automatically synchronizes exchange rates using official central bank feeds. Each currency pair you configure can have a prioritized list of sources, creating a robust fallback system if one service goes down.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ecb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.ecb.europa.eu/favicon-32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="ECB favicon">
            <span class="card-title" style="margin: 0;">European Central Bank (ECB)</span>
        </div>
        <span class="card-desc">Daily reference exchange rates from the ECB, base currency EUR.</span>
    </a>
    <a href="fed/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://fred.stlouisfed.org/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="FED favicon">
            <span class="card-title" style="margin: 0;">Federal Reserve (FED)</span>
        </div>
        <span class="card-desc">FRED database exchange rates, base currency USD.</span>
    </a>
    <a href="boe/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="BOE favicon">
            <span class="card-title" style="margin: 0;">Bank of England (BOE)</span>
        </div>
        <span class="card-desc">Daily reference rates from the BOE, base currency GBP.</span>
    </a>
    <a href="snb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://data.snb.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="SNB favicon">
            <span class="card-title" style="margin: 0;">Swiss National Bank (SNB)</span>
        </div>
        <span class="card-desc">Stable daily Swiss Franc rates from the SNB, base currency CHF.</span>
    </a>
</div>

## 📊 Provider Comparison

| <span style="min-width: 320px;">Provider</span> | Base Currency | Supported Currencies | <span style="min-width: 220px;">Update Frequency</span> | API Key | Notes |
|:---|:---:|:---:|:---:|:---:|:---|
| <img src="https://www.ecb.europa.eu/favicon-32.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **ECB** (European Central Bank) | EUR 🇪🇺 | ~45 | Daily, ~16:00 CET | Not required | Primary provider for Euro-based pairs and major world currencies. |
| <img src="https://fred.stlouisfed.org/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **FED** (Federal Reserve FRED) | USD 🇺🇸 | ~20 | Daily, US business days | Not required | Best fallback for US Dollar-based pairs. |
| <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BOE** (Bank of England) | GBP 🇬🇧 | ~15 | Daily, UK business days | Not required | Good coverage for Sterling-based pairs. |
| <img src="https://data.snb.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **SNB** (Swiss National Bank) | CHF 🇨🇭 | ~10 | Daily, Swiss business days | Not required | Highly stable quotes for Swiss Franc pairs. |

## 🎯 How Routing & Fallback Works

LibreFolio doesn't restrict you to a single source. When managing exchange rates:

1. 🛤️ **Direct Routes**: If a direct rate exists (e.g., EUR/USD via ECB), LibreFolio fetches it.
2. 🔀 **Chain Routes**: If no direct provider supports your pair (e.g., EUR/RON), LibreFolio can convert it through a chain (e.g., EUR → USD → RON) automatically.
3. 🔄 **Auto Fallback**: If your primary provider fails during sync (e.g., network timeout), LibreFolio automatically tries the next configured provider.
4. ✍️ **Manual Sentinel**: For currency pairs that are not supported by any central bank, you can set the provider to `MANUAL` to input rates yourself.
