# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Acquisto e Vendita

I tipi di transazione più fondamentali: l'**acquisto** aumenta le tue posizioni e diminuisce la liquidità; la **vendita** fa l'opposto e realizza un profitto o una perdita.

---

## 🔑 Proprietà Chiave

| Proprietà | Acquisto | Vendita |
|----------|-----|------|
| **Codice** | `BUY` | `SELL` |
| **Effetto cassa** | ⬇️ Diminuisce | ⬆️ Aumenta |
| **Effetto asset** | ⬆️ Aumenta le posizioni | ⬇️ Diminuisce le posizioni |
| **Evento fiscale** | No | Sì (realizza plusvalenza/minusvalenza) |

---

## 📊 Come Funziona

### 🛒 Acquisto

Quando acquisti un asset, viene creato un **lotto** con:

- **Data**: Quando è avvenuto l'acquisto
- **Quantità**: Numero di azioni/unità acquistate
- **Prezzo unitario**: Prezzo per azione al momento dell'acquisto
- **Commissioni**: Eventuali costi di transazione (commissioni, spread, ecc.)
- **Costo totale**: `quantity × unit_price + fees`

### 💰 Vendita

Quando vendi, LibreFolio associa la vendita ai lotti esistenti utilizzando il metodo **FIFO** (First In, First Out) per determinare:

$$
\text{Plusvalenza} = (P_{sell} \times Q) - (P_{buy} \times Q) - \text{Fees}
$$

!!! info "Associazione FIFO"

    LibreFolio calcola l'associazione dei lotti al **runtime** — non viene persistita nel database. Ciò consente analisi ipotetiche flessibili e il potenziale supporto futuro per altri metodi di associazione (LIFO, identificazione specifica).

---

## 🔗 Correlati

- 📊 **[Costo Medio Ponderato (WAC)](../../portfolio-theory/weighted-average-cost.md)** — Costo medio per unità su più acquisti
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Plusvalenze, metodi di associazione, riporto delle perdite
- 📈 **[Rendimenti](../../fundamentals/returns.md)** — Misurazione delle performance dell'investimento
