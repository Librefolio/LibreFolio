# 💼 Valore Patrimoniale Netto (NAV) / Patrimonio Netto

*[⬅️ Torna alla Panoramica delle Metriche di Performance](index.md)*

## 💡 Cos'è il NAV?

Il **Valore Patrimoniale Netto (NAV)** è la valutazione complessiva di mercato del tuo portafoglio in un istante $t$. Risponde alla domanda: *"Quanto vale il portafoglio in questo momento?"*

---

## 🧮 Formula

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Dove $\mathrm{MV}(t) = \sum_{(a,b) \in S} q(a,b,t) \cdot p(a,t) \cdot \mathrm{fx}(\mathrm{ccy}_p, C^*, t)$

🔗 Vedi **[Portfolio Engine — §5 Aggregation](portfolio-engine.md#5-portfolio-aggregation)** per la derivazione completa.

---

## 🔗 Catena del Prezzo di Valutazione {: #valuation-price-chain }

Il prezzo $p(a,t)$ segue una priorità rigorosa:

1. **Prezzo di mercato** — riempimento all'indietro di PriceHistory (ultimo $\leq t$)
2. **Ultimo prezzo di acquisto** — prezzo unitario BUY più recente da $V(u)$ (tutti i broker visibili)
3. **Mancante** — posizione esclusa dal NAV

Il **PMC** non viene mai utilizzato per la valutazione. Vedi **[Portfolio Engine — §2](portfolio-engine.md#2-valuation-price)**.

---

## 📝 Esempio

| Componente | Importo |
|------------|---------|
| Valore di Mercato delle Attività | €32.759 |
| Saldo di Cassa | €631 |
| In Transito | €0 |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinzioni Chiave

- **NAV vs [Valore Contabile](book-value.md)**: NAV = valore di mercato; Valore Contabile = costo di acquisizione. La differenza = plusvalenze non realizzate.
- **NAV vs [PnL Periodico](period-pnl.md)**: NAV = istantanea; PnL Periodico = variazione corretta per i flussi nel tempo.

---

## ⚠️ Qualità dei Dati

| Fonte di Valutazione | Affidabilità |
|----------------------|--------------|
| `MARKET_PRICE` | Piena — PriceHistory disponibile |
| `LAST_BUY_PRICE` | Parziale — utilizza il prezzo di transazione |
| `MISSING` | Nessuna — escluso dal NAV |
