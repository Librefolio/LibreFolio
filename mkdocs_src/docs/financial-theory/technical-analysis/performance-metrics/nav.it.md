# 💼 Net Asset Value (NAV) / Patrimonio Netto

*[⬅️ Torna a Panoramica Metriche di Performance](index.md)*

## 💡 Cos'è il NAV?

Il **Net Asset Value (NAV)** è la valutazione totale di mercato del tuo portafoglio in un dato momento $t$. Risponde alla domanda: *"Quanto vale il portafoglio in questo momento?"*

---

## 🧮 Formula

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Dove $\mathrm{MV}(t) = \sum_{(a,b) \in S} q(a,b,t) \cdot p(a,t) \cdot \mathrm{fx}(\mathrm{ccy}_p, C^*, t)$

🔗 Vedi **[Portfolio Engine — §5 Aggregazione del Portafoglio](portfolio-engine.md#5-portfolio-aggregation)** per la derivazione completa.

---

## 🔗 Catena dei Prezzi di Valutazione {: #valuation-price-chain }

Il prezzo $p(a,t)$ segue una priorità rigorosa:

1. **Prezzo di mercato** — backward-fill di PriceHistory (ultimo $\leq t$)
2. **Ultimo prezzo di acquisto** — prezzo unitario dell'ultimo acquisto (ACQUISTO) da $V(u)$ (tutti i broker visibili)
3. **Mancante** — la posizione è esclusa dal NAV

Il PMC **non** viene mai utilizzato per la valutazione. Vedi **[Portfolio Engine — §2](portfolio-engine.md#2-valuation-price)**.

---

## 📝 Esempio

| Componente | Importo |
|-----------|--------|
| Valore di Mercato degli Asset | €32,759 |
| Saldo Cassa | €631 |
| In Transito | €0 |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinzioni Chiave

- **NAV vs [Book Value](book-value.md)**: NAV = valore di mercato; Book = costo di acquisizione. Differenza = plusvalenze non realizzate.
- **NAV vs [Period PnL](period-pnl.md)**: NAV = snapshot; Period PnL = variazione rettificata per i flussi nel tempo.

---

## ⚠️ Qualità dei Dati

| Fonte di Valutazione | Affidabilità |
|-----------------|------------|
| `MARKET_PRICE` | Completa — PriceHistory disponibile |
| `LAST_BUY_PRICE` | Parziale — utilizza il prezzo di transazione |
| `MISSING` | Nulla — la posizione è esclusa dal NAV |
