# 🔌 FX Providers (Developer)

This section provides the technical documentation for each Foreign Exchange (FX) rate provider implemented in the LibreFolio backend. For the end-user perspective, see the [User Manual — FX Providers](../../../../user/fx/providers/index.md).

## 🏛️ Providers at a Glance

| Provider | Code | Base Currency | Currencies | API Format | API Key | Test Level |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| [**European Central Bank**](ecb.md) | `ECB` | EUR | ~45 | JSON/XML | No | Stable |
| [**Federal Reserve**](fed.md) | `FED` | USD | ~20 | CSV | No | Beta |
| [**Bank of England**](boe.md) | `BOE` | GBP | ~15 | CSV/HTML | No | Beta |
| [**Swiss National Bank**](snb.md) | `SNB` | CHF | ~10 | CSV | No | Beta |

### 📝 General Notes

- **Base Currency**: The currency against which all other rates are quoted by the provider. LibreFolio automatically handles conversions between any pair, regardless of the provider's base currency.
- **Update Frequency**: Most central banks update their rates once per business day (weekdays only).
- **No API Keys**: All core providers use publicly accessible APIs — no registration or API keys required.

## 📚 Technical Details

- [🇪🇺 ECB (European Central Bank)](ecb.md)
- [🇺🇸 FED (Federal Reserve FRED)](fed.md)
- [🇬🇧 BOE (Bank of England)](boe.md)
- [🇨🇭 SNB (Swiss National Bank)](snb.md)

---

## 🔗 Related Documentation

- [💱 FX Configuration & Routing](../configuration.md) — Technical details on the routing algorithm and configuration.
- [💱 FX Architecture](../architecture.md) — Main backend service architecture.
