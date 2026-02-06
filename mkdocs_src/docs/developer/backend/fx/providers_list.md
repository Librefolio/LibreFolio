# FX Providers List

This page lists the Foreign Exchange (FX) rate providers currently available in LibreFolio.

| Provider Name             | Code  | Base Currency | Test Level | Notes                                        |
|:--------------------------|:------|:--------------|:-----------|:---------------------------------------------|
| **European Central Bank** | `ECB` | EUR           | Stable     | Official rates from the ECB. Updated daily.  |
| **Federal Reserve**       | `FED` | USD           | Beta       | Official rates from the US Federal Reserve.  |
| **Bank of England**       | `BOE` | GBP           | Beta       | Official rates from the Bank of England.     |
| **Swiss National Bank**   | `SNB` | CHF           | Beta       | Official rates from the Swiss National Bank. |

---

### Notes

- **Base Currency**: The currency against which all other rates are quoted by the provider. LibreFolio automatically handles conversions between any pair, regardless of the
  provider's base currency.
- **Update Frequency**: Most central banks update their rates once per business day.
