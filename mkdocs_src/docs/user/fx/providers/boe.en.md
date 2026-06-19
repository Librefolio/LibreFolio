# 🇬🇧 Bank of England (BOE)

The **Bank of England (BOE)** provider offers daily reference exchange rates quoted against the British Pound Sterling (GBP). It serves as an excellent reference for Sterling-denominated portfolios.

## 📊 Capabilities

- ✅ **Current Price**: Reference rate updated daily
- ✅ **History**: Deep historical coverage
- ❌ **Search**: No asset search (FX rates only)

## 🔧 Specifications

- **Base Currency**: GBP 🇬🇧
- **Update Frequency**: Daily on UK business days
- **API Key**: Not required (retrieved from the BOE Statistical Database)

## 💰 Supported Currencies

The Bank of England supports approximately 15 major currencies, including:

- **Major**: USD 🇺🇸, EUR 🇪🇺, JPY 🇯🇵, CHF 🇨🇭, CAD 🇨🇦, AUD 🇦🇺, NZD 🇳🇿
- **Other**: SEK 🇸🇪, NOK 🇳🇴, DKK 🇩🇰, CNY 🇨🇳, HKD 🇭🇰, SGD 🇸🇬, ZAR 🇿🇦, INR 🇮🇳

## 📝 Important Notes

- **Quotes format**: Rates are expressed as the amount of foreign currency per 1 GBP (e.g., 1 GBP = 1.25 USD). LibreFolio automatically normalizes this representation behind the scenes.
- **Holidays**: The BOE does not publish rates on UK bank holidays or weekends.
