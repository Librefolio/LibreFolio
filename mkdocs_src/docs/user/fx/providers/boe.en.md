# <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" alt=""> Bank of England (BOE)

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
- **Licence**: the Bank of England publishes its database under the UK Open Government Licence, which allows free reuse with attribution.
- **Euro rates before LibreFolio 1.4**: the euro rate came from the wrong Bank of England series (euro against the US dollar instead of against sterling). If you used BOE for the euro, sync those pairs again over the whole period you hold (FX page, «All» period, «Sync All»).
- **Holidays**: The BOE does not publish rates on UK bank holidays or weekends.
