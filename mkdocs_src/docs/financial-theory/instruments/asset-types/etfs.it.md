# ![](../../../static/icons/asset-types/etf.png){: width="32" style="vertical-align: middle;" } ETF (Exchange Traded Funds)

Un **ETF** è un paniere di titoli (azioni, obbligazioni, materie prime o un mix) che viene scambiato in borsa come se fosse una singola azione. Gli ETF combinano la diversificazione dei fondi comuni di investimento con la flessibilità di negoziazione in tempo reale delle azioni.

---

## 🔑 Caratteristiche Principali

| Proprietà | Dettaglio |
|----------|--------|
| **Codice in LibreFolio** | `ETF` |
| **Prezzo** | Prezzi di borsa in tempo reale, come le azioni |
| **Valuta** | Denominato nella valuta della borsa di quotazione |
| **Dividendi** | Possono distribuire (Dist) o reinvestire internamente (Acc) |
| **TER** | Total Expense Ratio — commissione di gestione annuale dedotta dal NAV |
| **Provider tipici** | Yahoo Finance, justETF, CSS Scraper |

---

## 📊 Accumulazione vs Distribuzione

| Caratteristica | Accumulazione (Acc) | Distribuzione (Dist) |
|---------|-------------------|-------------------|
| **Dividendi** | Reinvestiti internamente | Pagati ai detentori |
| **Evento fiscale** | Solo alla vendita | Ad ogni distribuzione |
| **Capitalizzazione** | Crescita composta completa | Ridotta dal carico fiscale |
| **Ideale per** | Crescita a lungo termine | Esigenze di reddito |

Il [vantaggio del differimento fiscale](../../fundamentals/taxation.md#tax-deferral-advantage) degli ETF ad accumulazione può essere significativo su orizzonti temporali lunghi.

---

## 📈 NAV vs Prezzo di Mercato

- **NAV** (Net Asset Value): Il valore reale delle attività sottostanti ÷ quote in circolazione. Calcolato giornalmente.
- **Prezzo di Mercato**: Il prezzo al quale l'ETF viene effettivamente scambiato in borsa. Può deviare leggermente dal NAV.
- **Premio/Sconto**: Quando il prezzo di mercato > NAV, l'ETF viene scambiato a premio; quando < NAV, a sconto.

---

## 🔍 Tracking dell'Indice

La maggior parte degli ETF segue un indice di riferimento (ad es., S&P 500, MSCI World). Il **tracking error** misura quanto il rendimento dell'ETF devia da quello dell'indice:

$$
TE = \sigma(R_{ETF} - R_{index})
$$

Un tracking error più basso = una migliore replicazione dell'indice.

---

## 🔗 Correlati

- 💰 **[Eventi Dividendi](../asset-events/dividend.md)** — Distribuzioni dalle posizioni dell'ETF
- 📈 **[Indice e Benchmark](index-benchmark.md)** — Come funzionano i benchmark
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Implicazioni fiscali Acc vs Dist
