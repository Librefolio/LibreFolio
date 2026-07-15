# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Acquisto & Vendita ![](../../../static/icons/transactions/sell.png){: width="32" style="vertical-align: middle;" }

<div class="lf-screenshot-carousel" data-carousel="buy-sell" data-carousel-interval="4000" data-show-titles="true">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> ACQUISTO' alt="Acquisto">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENDITA' alt="Vendita">
</div>

I tipi di transazione più fondamentali: **l'acquisto** aumenta le tue partecipazioni e diminuisce la liquidità; **la vendita** fa l'opposto e realizza un profitto o una perdita.

---

## 🔑 Proprietà Chiave

| Proprietà | Acquisto | Vendita |
|-----------|----------|---------|
| **Codice** | `BUY` | `SELL` |
| **Effetto sulla liquidità** | ⬇️ Diminuisce | ⬆️ Aumenta |
| **Effetto sul patrimonio** | ⬆️ Aumenta le partecipazioni | ⬇️ Diminuisce le partecipazioni |
| **Evento fiscale** | No | Sì (realizza plusvalenza/minusvalenza) |

---

## 📊 Come Funziona

### 🛒 Acquisto

Quando acquisti un'attività, viene creato un **lotto** con:

- **Data**: Quando è avvenuto l'acquisto
- **Quantità**: Numero di azioni/unità acquistate
- **Prezzo unitario**: Prezzo per azione al momento dell'acquisto
- **Commissioni**: Eventuali commissioni di transazione (commissione, spread, ecc.)
- **Costo totale**: `quantità × prezzo_unitario + commissioni`

### 💰 Vendita

Quando vendi, LibreFolio abbina la vendita ai lotti esistenti utilizzando il metodo **FIFO** (First In, First Out) per determinare:

$$
\text{Plusvalenza}~\text{Minusvalenza} = (P_{vendita} \times Q) - (P_{acquisto} \times Q) - \text{Commissioni}
$$

<div id="fifo-matching"></div>

!!! info "Abbinamento FIFO"

    LibreFolio calcola l'abbinamento dei lotti a **runtime** — non viene salvato nel database. Ciò consente un'analisi flessibile di scenari "what-if" e un potenziale supporto futuro per altri metodi di abbinamento (LIFO, identificazione specifica).

---

## 🔗 Correlati

- 📊 **[Prezzo Medio di Carico (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Costo medio per unità su più acquisti
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Plusvalenze, metodi di abbinamento, riporto delle perdite
- 📈 **[Rendimenti](../../fundamentals/returns.md)** — Misurazione della performance degli investimenti
