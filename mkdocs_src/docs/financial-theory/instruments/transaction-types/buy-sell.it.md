# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Acquisto e Vendita

I tipi di transazione più fondamentali: l'**acquisto** aumenta le tue posizioni e diminuisce la liquidità; la **vendita** fa l'opposto e realizza un profitto o una perdita.

---

## 🔑 Proprietà Chiave

| Proprietà | Acquisto | Vendita |
|----------|-----|------|
| **Codice** | `BUY` | `SELL` |
| **Effetto liquidità** | ⬇️ Diminuisce | ⬆️ Aumenta |
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

Quando vendi, LibreFolio abbina la vendita ai lotti esistenti utilizzando il metodo **FIFO** (First In, First Out) per determinare:

$$
\text{Plusvalenza} = (P_{sell} \times Q) - (P_{buy} \times Q) - \text{Fees}
$$

!!! info "Abbinamento FIFO"

    LibreFolio calcola l'abbinamento dei lotti al **runtime** — non viene persistita nel database. Ciò consente analisi "what-if" flessibili e il potenziale supporto futuro per altri metodi di abbinamento (LIFO, identificazione specifica).

---

## 📐 Base di Costo

La base di costo delle tue posizioni è l'importo totale che hai pagato, incluse le commissioni:

$$
\text{Cost Basis} = \sum_{i} (Q_i \times P_i + F_i)
$$

Questo viene utilizzato per calcolare il P&L non realizzato in qualsiasi momento:

$$
\text{Unrealized P\\&L} = \text{Current Value} - \text{Cost Basis}
$$

---

## 🔗 Correlati

- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Plusvalenze, metodi di abbinamento, riporto delle perdite
- 📈 **[Rendimenti](../../fundamentals/returns.md)** — Misurazione delle performance dell'investimento
