# ![](../../../static/icons/transactions/buy.png){: width="32" style="vertical-align: middle;" } Acquisto & Vendita ![](../../../static/icons/transactions/sell.png){: width="32" style="vertical-align: middle;" }

<div class="lf-screenshot-carousel" data-carousel="buy-sell" data-carousel-interval="4000" data-show-titles="true">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> ACQUISTO' alt="Acquisto">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENDITA' alt="Vendita">
</div>

I tipi di transazione più fondamentali: **l'acquisto** aumenta le tue posizioni e riduce la liquidità; **la vendita** fa il contrario e realizza un profitto o una perdita.

---

## 🔑 Proprietà Chiave

| Proprietà | Acquisto | Vendita |
|-----------|----------|---------|
| **Codice** | `BUY` | `SELL` |
| **Effetto sulla liquidità** | ⬇️ Diminuisce | ⬆️ Aumenta |
| **Effetto sul patrimonio** | ⬆️ Aumenta le posizioni | ⬇️ Riduce le posizioni |
| **Evento fiscale** | No | Sì (realizza guadagno/perdita) |

---

## 📊 Come Funziona

### 🛒 Acquisto

Quando acquisti un asset, viene creato un **lotto** con:

- **Data**: Quando è avvenuto l'acquisto
- **Quantità**: Numero di azioni/unità acquistate
- **Prezzo unitario**: Prezzo per azione al momento dell'acquisto
- **Commissioni**: Eventuali commissioni di transazione (commissione, spread, ecc.)
- **Costo totale**: `quantità × prezzo_unitario + commissioni`

### 💰 Vendita

Quando vendi, LibreFolio abbina la vendita ai lotti esistenti utilizzando il metodo **FIFO** (First In, First Out) per determinare:

$$
\text{Plusvalenza} = (P_{vendita} \times Q) - (P_{acquisto} \times Q) - \text{Commissioni}
$$

<div id="fifo-matching"></div>

!!! info "Abbinamento FIFO"

    LibreFolio calcola l'abbinamento dei lotti **in fase di esecuzione** — non viene persistito nel database. Ciò consente un'analisi flessibile del tipo "what-if" e un potenziale supporto futuro per altri metodi di abbinamento (LIFO, identificazione specifica).

---

## 🔗 Correlati

- 📊 **[Prezzo Medio di Carico (PMC)](../../technical-analysis/performance-metrics/weighted-average-cost.md)** — Costo medio per unità su più acquisti
- 🔬 **[Analisi dei Lotti FIFO](../../technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)** — Analisi dettagliata per lotto dell'abbinamento FIFO introdotto sopra
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Plusvalenze, metodi di abbinamento, riporto delle perdite
- 📈 **[Rendimenti](../../fundamentals/returns.md)** — Misurazione della performance degli investimenti
