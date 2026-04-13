# ![](../../../static/icons/asset-types/fund.png){: width="32" style="vertical-align: middle;" } Fondi Comuni di Investimento

Un **fondo comune di investimento** è un veicolo di investimento gestito professionalmente che raccoglie capitali da numerosi investitori per acquistare un portafoglio diversificato di azioni, obbligazioni o altri titoli.

---

## 🔑 Caratteristiche Principali

| Proprietà | Dettaglio |
|----------|--------|
| **Codice in LibreFolio** | `FUND` |
| **Determinazione del prezzo** | NAV (Net Asset Value) calcolato una volta al giorno, dopo la chiusura del mercato |
| **Valuta** | Denominato nella valuta di base del fondo |
| **Dividendi** | Può distribuire (fondi a distribuzione) o reinvestire (fondi ad accumulazione) |
| **Commissioni** | Commissione di gestione (TER), commissioni di ingresso/uscita |
| **Provider tipici** | Yahoo Finance, Manuale |

---

## 📊 Come Funzionano i Fondi Comuni

1. **Raccolta**: Gli investitori acquistano quote del fondo
2. **Gestione**: Un gestore professionale seleziona e gestisce i titoli sottostanti
3. **Prezzo NAV**: Il valore del fondo viene calcolato giornalmente come: (asset totali − passività) ÷ quote in circolazione
4. **Distribuzioni**: Il reddito (dividendi, interessi) può essere distribuito o reinvestito

---

## 📐 Calcolo del NAV

$$
\text{NAV} = \frac{\text{Asset Totali} - \text{Passività Totali}}{\text{Quote in Circolazione}}
$$

A differenza degli ETF, i fondi comuni vengono scambiati solo al NAV di fine giornata — non è possibile acquistare o vendere a prezzi intraday.

---

## 🔗 Correlati

- 📊 **[ETF](etfs.md)** — Alternativa scambiata in borsa con prezzi intraday
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Implicazioni fiscali tra distribuzione e accumulazione
- 📈 **[Rendimenti e Tassi di Crescita](../../fundamentals/returns.md)** — Misurare le performance del fondo
