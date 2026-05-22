# ![](../../../static/icons/asset-types/etf.png){: width="32" style="vertical-align: middle;" } ETF (Fondi Negoziabili in Borsa)

Un **ETF** è un paniere di titoli (azioni, obbligazioni, materie prime o una combinazione) che viene scambiato in borsa come un singolo titolo azionario. Gli ETF combinano la diversificazione dei fondi comuni di investimento con la flessibilità di negoziazione in tempo reale delle azioni.

---

## 🔑 Caratteristiche Principali

| Proprietà | Dettaglio |
|-----------|-----------|
| **Codice in LibreFolio** | `ETF` |
| **Prezzo** | Prezzi di borsa in tempo reale, come le azioni |
| **Valuta** | Denominato nella valuta dell'exchange di quotazione |
| **Dividendi** | Possono distribuire (Dist) o reinvestire internamente (Acc) |
| **TER** | Total Expense Ratio — commissione di gestione annuale detratta dal NAV |
| **Provider tipici** | Yahoo Finance, justETF, CSS Scraper |

---

## 📊 Accumulazione vs Distribuzione

| Caratteristica | Ad Accumulazione (Acc) | A Distribuzione (Dist) |
|----------------|------------------------|------------------------|
| **Dividendi** | Reinvestiti internamente | Pagati ai detentori |
| **Evento fiscale** | Solo in caso di vendita | Ad ogni distribuzione |
| **Capitalizzazione composta** | Crescita composta piena | Ridotta dal carico fiscale |
| **Ideale per** | Crescita a lungo termine | Esigenze di reddito |

Il [vantaggio del differimento fiscale](../../fundamentals/taxation.md#tax-deferral-advantage) degli ETF ad accumulazione può essere significativo su orizzonti temporali lunghi.

---

## 📈 NAV vs Prezzo di Mercato

- **NAV** (Net Asset Value): Il valore reale delle posizioni sottostanti ÷ azioni in circolazione. Calcolato giornalmente.
- **Prezzo di Mercato**: Il prezzo a cui l'ETF viene effettivamente scambiato in borsa. Può discostarsi leggermente dal NAV.
- **Premio/Sconto**: Quando il prezzo di mercato > NAV, l'ETF viene scambiato a premio; quando < NAV, a sconto.

---

## 🔍 Tracciamento dell'Indice

La maggior parte degli ETF replica un indice di riferimento (es. S&P 500, MSCI World). Il **tracking error** misura quanto il rendimento dell'ETF si discosta dall'indice:

$$
TE = \sigma(R_{ETF} - R_{index})
$$

Un tracking error più basso = migliore replicazione dell'indice.

---

## 🔗 Correlati

- 💰 **[Eventi di Dividendo](../asset-events/dividend.md)** — Distribuzioni dalle posizioni dell'ETF
- 📈 **[Indice e Benchmark](index-benchmark.md)** — Come funzionano gli indici di riferimento
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Implicazioni fiscali Acc vs Dist
