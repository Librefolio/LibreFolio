# 📝 Modulo Transazione

Il modulo transazione aggiunge o modifica una transazione — o una coppia collegata — nel [workspace bulk](index.md#bulk-workspace). Mostra inoltre una transazione in sola lettura quando fai doppio clic su di essa in un elenco. Appaiono solo i campi richiesti dal tipo scelto.

<div class="lf-screenshot-carousel" data-carousel="transactions" data-carousel-interval="3000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> BUY' alt="Buy">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> SELL' alt="Sell">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-dividend" data-title='<img src="/LibreFolio/static/icons/transactions/dividend.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DIVIDEND' alt="Dividend">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-deposit" data-title='<img src="/LibreFolio/static/icons/transactions/deposit.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DEPOSIT' alt="Deposit">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-adjustment" data-title='<img src="/LibreFolio/static/icons/transactions/adjustment.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> ADJUSTMENT' alt="Adjustment">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRANSFER' alt="Trasferimento asset">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fxconversion" data-title='<img src="/LibreFolio/static/icons/transactions/fx-conversion.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> FX CONVERSION' alt="Conversione FX">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-cash-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/cash-transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> CASH TRANSFER' alt="Giroconto">
</div>

---

## ✍️ Compila il modulo

1. Scegli il **Tipo**, poi il **Broker** se non è già impostato.
2. Compila la sezione **Obbligatori**: la **Data**, l'**Asset** e la sua quantità quando il tipo ne prevede una, e l'importo in contanti.
3. Apri **Opzionali** per **Tag**, una **Descrizione** o, su dividendi, interessi e rettifiche, un **Evento collegato**.
4. Fai clic su **Applica** per inserire la riga nel workspace bulk; **Salva tutto** nel workspace bulk la salva definitivamente.

Alcune regole rendono l'inserimento rapido:

- **Gli importi sono totali** — digita il totale pagato o ricevuto, non il prezzo per azione (*Importo totale, non per azione*).
- **Digita numeri positivi** — il modulo aggiunge il segno meno dove escono denaro o unità: il pagamento di un acquisto, le unità di una vendita, un prelievo, una commissione, un'imposta. Solo la quantità di una **Rettifica** porta un segno: positivo aggiunge unità, negativo le rimuove.
- **Controlli mentre procedi** — una volta compilati i campi obbligatori, il modulo verifica la voce rispetto al tuo registro e alle altre righe del workspace bulk, ed elenca eventuali problemi in alto. **⚡ Valida ora** esegue subito il controllo.
- **Broker o asset mancante?** — **Crea nuovo** nell'elenco dei broker, o **Nuovo asset** nell'elenco degli asset, lo crea senza uscire dal modulo.

??? info "💰 Costo di carico delle unità in entrata — per Rettifiche e Trasferimenti asset"

    Quando una **Rettifica** aggiunge unità, o sul lato ricevente di un **Trasferimento asset**, il modulo chiede quanto sono costate quelle unità:

    - **Auto** — LibreFolio lo calcola come [prezzo medio di carico (PMC)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md); premi **⚡ Valida ora** per vederlo.
    - **Manuale** — lo digiti tu.

    In **Auto**, la media viene presa sul broker mittente di un trasferimento, o sul broker della rettifica stessa. Se quel broker non ha altre transazioni sull'asset fino alla data in cui entrano le unità, non c'è nulla da mediare e il costo è 0 per scelta di progetto: se quelle unità sono costate qualcosa, apri la transazione in seguito e digita il loro costo in **Manuale**. In **Manuale**, il campo non può restare vuoto: LibreFolio segnala la riga e non salva nulla finché non lo compili o non passi a **Auto**. Per unità che non sono costate nulla, come un regalo, digita 0. Se manca un tasso di cambio, il link **Sincronizza tassi FX** lo recupera.

---

## 🏷️ Tipi di transazione

La [Guida alla teoria finanziaria](../../financial-theory/instruments/transaction-types/index.md) spiega in dettaglio ogni tipo.

### 🧾 Transazioni singole

| Tipo | Cosa registra | Teoria |
|------|-----------------|--------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **Acquisto** | Unità di un asset acquistate e il totale pagato | [📖 Leggi](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } **Vendita** | Unità di un asset vendute e il totale incassato | [📖 Leggi](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **Dividendo** | Denaro pagato da un asset che possiedi | [📖 Leggi](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } **Interesse** | Interessi ricevuti, con o senza un asset | [📖 Leggi](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **Deposito** | Denaro che versi nel broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } **Prelievo** | Denaro che prelevi dal broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **Commissione** | Una commissione o un altro costo, facoltativamente legato a un asset | [📖 Leggi](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } **Imposta** | Un'imposta pagata, facoltativamente legata a un asset | [📖 Leggi](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **Rettifica** | Unità aggiunte o rimosse senza movimenti di denaro: uno split, un regalo, una posizione aperta altrove | [📖 Leggi](../../financial-theory/instruments/transaction-types/adjustment.md) |

### 🔗 Transazioni abbinate {: #composite-transactions }

Un'operazione abbinata viene registrata come due transazioni collegate, che il modulo mostra come una sola, con un lato **Da** e un lato **A**. Ogni lato ha la propria data, e la freccia **Inverti lati** capovolge la direzione.

| Tipo | Cosa registra | Teoria |
|------|-----------------|--------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **Trasferimento asset** | Unità di un asset spostate tra due tuoi broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **Giroconto** | Liquidità spostata tra due tuoi broker, in una sola valuta | [📖 Leggi](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **Cambio valuta** | Una valuta convertita in un'altra, all'interno di un solo broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

Un trasferimento richiede due broker diversi, un cambio valuta due valute diverse. Due righe singole possono anche essere collegate in una coppia in un secondo momento, e una coppia può essere separata di nuovo — vedi [Collega o scollega una coppia](index.md#link-pairs).

---

## 🔗 Correlati

- 📋 **[Transazioni](index.md)** — l'elenco, i filtri e il workspace bulk
- 📥 **[Importa dal broker](import/index.md)** — salta l'inserimento manuale con un'importazione BRIM
