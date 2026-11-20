# 🔌 FX Providers (Developer)

This section provides the technical documentation for each Foreign Exchange (FX) rate provider implemented in the LibreFolio backend. For the end-user perspective, see the [User Manual — FX Providers](../../../../user/fx/providers/index.md).

## 🏛️ Providers at a Glance

| Provider | Code | Base Currency | Currencies | API Format | API Key | Test Level |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| [**European Central Bank**](ecb.md) | `ECB` | EUR | ~45 | JSON/XML | No | Stable |
| [**Federal Reserve**](fed.md) | `FED` | USD | 23 | CSV | No | Beta |
| [**Bank of England**](boe.md) | `BOE` | GBP | 15 | CSV | No | Beta |
| [**Swiss National Bank**](snb.md) | `SNB` | CHF | ~25 | JSON | No | Beta |
| [**Banca d'Italia**](bdi.md) | `BDI` | EUR | ~149 | JSON | No | Beta |
| [**Banco Central do Brasil**](bcb.md) | `BCB` | USD | 152 + BRL | CSV | No | Beta |
| [**Norges Bank**](norges.md) | `NORGES` | NOK | ~35 | CSV (SDMX) | No | Beta |
| [**National Bank of Ukraine**](nbu.md) | `NBU` | UAH | ~40 | JSON | No | Beta |
| [**Bank of Canada**](boc.md) | `BOC` | CAD | ~24 | JSON | No | Beta |
| [**Banco de México**](banxico.md) | `BANXICO` | MXN | 6 | JSON (SIE) | Yes (free token) | Beta |
| [**Czech National Bank**](cnb.md) | `CNB` | CZK | 30 | Text (one file per year) | No | Beta |
| [**South African Reserve Bank**](sarb.md) | `SARB` | ZAR | 25 | JSON | No | Beta |
| [**Bank of Korea**](bok.md) | `BOK` | KRW | 43 | JSON (ECOS) | Yes (free key) | Beta |

### 📝 General Notes

- **Base Currency**: The currency against which all other rates are quoted by the provider. LibreFolio automatically handles conversions between any pair, regardless of the provider's base currency.
- **Update Frequency**: ECB, BOE, BDI, BCB, NORGES and BOC publish one rate per business day of their country (weekdays only); NBU has a row for every day, weekends included, each valid from the day after it is set ([NBU](nbu.md)). FED holds one rate per US business day too, but FRED releases them once a week, on Mondays ([FED](fed.md#release-schedule)). The SNB publishes monthly averages only, stored on the 1st of each month.
- **API Keys**: BANXICO and BOK need a free key from their bank (a secret `PluginSettingField`, set by an administrator in the plugin settings or with `LIBREFOLIO_PLUGIN_FX_<CODE>_<FIELD>`); without it they are «to configure» and the sync does not call them. The other providers use public APIs, with no registration.

## 📚 Technical Details

- [🇪🇺 ECB (European Central Bank)](ecb.md)
- [🇺🇸 FED (Federal Reserve FRED)](fed.md)
- [🇬🇧 BOE (Bank of England)](boe.md)
- [🇨🇭 SNB (Swiss National Bank)](snb.md)
- [🇮🇹 BDI (Banca d'Italia)](bdi.md)
- [🇧🇷 BCB (Banco Central do Brasil)](bcb.md)
- [🇳🇴 NORGES (Norges Bank)](norges.md)
- [🇺🇦 NBU (National Bank of Ukraine)](nbu.md)
- [🇨🇦 BOC (Bank of Canada)](boc.md)
- [🇲🇽 BANXICO (Banco de México)](banxico.md)
- [🇨🇿 CNB (Czech National Bank)](cnb.md)
- [🇿🇦 SARB (South African Reserve Bank)](sarb.md)
- [🇰🇷 BOK (Bank of Korea)](bok.md)

---

## 🔗 Related Documentation

- [💱 FX Configuration & Routing](../configuration.md) — Technical details on the routing algorithm and configuration.
- [💱 FX Architecture](../architecture.md) — Main backend service architecture.
