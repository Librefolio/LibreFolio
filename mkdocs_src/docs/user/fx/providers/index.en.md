# 🔌 FX Providers

LibreFolio automatically synchronizes exchange rates using official central bank feeds. Each currency pair you configure can have a prioritized list of sources, creating a robust fallback system if one service goes down.

## 📊 Provider Comparison

| Provider | Base Currency | Supported Currencies | Update Frequency | API Key | Notes |
|:---|:---:|:---:|:---:|:---:|:---|
| <img src="https://www.ecb.europa.eu/favicon-32.png" style="height:18px; vertical-align:middle"> **ECB** (European Central Bank) | EUR 🇪🇺 | ~45 | Daily, ~16:00 CET | Not required | Primary provider for Euro-based pairs and major world currencies. |
| <img src="https://fred.stlouisfed.org/favicon.ico" style="height:18px; vertical-align:middle"> **FED** (Federal Reserve FRED) | USD 🇺🇸 | ~20 | Daily, US business days | Not required | Best fallback for US Dollar-based pairs. |
| <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" style="height:18px; vertical-align:middle"> **BOE** (Bank of England) | GBP 🇬🇧 | ~15 | Daily, UK business days | Not required | Good coverage for Sterling-based pairs. |
| <img src="https://data.snb.ch/favicon.ico" style="height:18px; vertical-align:middle"> **SNB** (Swiss National Bank) | CHF 🇨🇭 | ~10 | Daily, Swiss business days | Not required | Highly stable quotes for Swiss Franc pairs. |

## 🎯 How Routing & Fallback Works

LibreFolio doesn't restrict you to a single source. When managing exchange rates:

1. 🛤️ **Direct Routes**: If a direct rate exists (e.g., EUR/USD via ECB), LibreFolio fetches it.
2. 🔀 **Chain Routes**: If no direct provider supports your pair (e.g., EUR/RON), LibreFolio can convert it through a chain (e.g., EUR → USD → RON) automatically.
3. 🔄 **Auto Fallback**: If your primary provider fails during sync (e.g., network timeout), LibreFolio automatically tries the next configured provider.
4. ✍️ **Manual Sentinel**: For currency pairs that are not supported by any central bank, you can set the provider to `MANUAL` to input rates yourself.

## 📚 Provider Details

For details on each provider, see their specific guides:

- [🇪🇺 European Central Bank (ECB)](ecb.en.md)
- [🇺🇸 Federal Reserve (FED)](fed.en.md)
- [🇬🇧 Bank of England (BOE)](boe.en.md)
- [🇨🇭 Swiss National Bank (SNB)](snb.en.md)
