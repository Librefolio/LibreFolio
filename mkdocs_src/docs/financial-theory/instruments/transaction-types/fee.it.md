# ![](../../../static/icons/transactions/fee.png){: width="32" style="vertical-align: middle;" } Commissioni e Tasse

Le **commissioni** e le **tasse** rappresentano costi che riducono il valore del tuo portafoglio. Sono tipi di transazione separati per distinguere tra i costi addebitati dal broker e gli obblighi imposti dallo Stato.

---

## 🔑 Proprietà Chiave

| Proprietà | Commissione | Tassa |
|----------|-----|-----|
| **Codice** | `FEE` | `TAX` |
| **Effetto cassa** | ⬇️ Diminuisce il saldo | ⬇️ Diminuisce il saldo |
| **Effetto asset** | — | — |
| **Esempi** | Commissione, costo di custodia, spread | Imposta sulle plusvalenze, ritenuta d'acconto, stamp duty |

---

## 📊 Tipi di Commissioni

| Tipo di Commissione | Descrizione | Frequenza |
|----------|-------------|-----------|
| **Commissione di trading** | Costo per singola operazione addebitato dal broker | Per transazione |
| **Costo di custodia** | Canone di mantenimento del conto | Mensile/Trimestrale |
| **Spread** | Differenza tra prezzo bid e ask | Implicito per transazione |
| **Commissione di conversione FX** | Costo di conversione valutaria | Per conversione |
| **Commissione di gestione (TER)** | Spesa annuale di ETF/Fondo | Dedotta dal NAV |

---

## 💰 Tipi di Tasse

| Tipo di Tassa | Descrizione | Quando viene addebitata |
|----------|-------------|-------------|
| **Imposta sulle plusvalenze** | Tassa sul profitto realizzato dalla vendita | Alla vendita |
| **Ritenuta d'acconto** | Tassa detratta alla fonte (dividendi, interessi) | Al pagamento |
| **Stamp duty** | Tassa di transazione (es. UK stamp duty) | All'acquisto |
| **Tassa sulle transazioni finanziarie** | Tassa sulle operazioni (es. Tobin tax italiana) | All'operazione |

---

## 📐 Impatto sui Rendimenti

Le commissioni e le tasse riducono direttamente il tuo rendimento netto:

$$
R_{net} = R_{gross} - \frac{\text{Commissioni} + \text{Tasse}}{V_{start}}
$$

Su periodi lunghi, anche piccole commissioni ricorrenti si accumulano significativamente:

$$
V_{final} = V_0 \times (1 + r - f)^n
$$

dove $f$ è il tasso di commissione annuale. Una commissione annuale dell'1% su un rendimento del 7% in 30 anni riduce il valore finale del **26%**.

---

## 🔗 Correlati

- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Teoria completa sulla tassazione
- 🛒 **[Acquisto e Vendita](buy-sell.md)** — Commissioni addebitate sulle transazioni
