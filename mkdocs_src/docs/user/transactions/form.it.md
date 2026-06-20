# 📝 Modulo Transazioni

Il Modulo Transazioni si apre ogni volta che si **crea** o si **modifica** una transazione. Si adatta dinamicamente al tipo di transazione selezionato, mostrando solo i campi pertinenti a quell'operazione.

---

## 🏷️ Tipi di Transazione

Per una definizione concettuale approfondita di ogni operazione, fare riferimento alla [guida alla Teoria Finanziaria](../../financial-theory/instruments/transaction-types/index.md).

<div class="lf-screenshot-carousel" data-carousel="transactions" data-carousel-interval="3000" data-show-titles="true">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="form-modal" data-title='<img src="/LibreFolio/static/icons/transactions/buy.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> ACQUISTO' alt="Acquisto">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-sell" data-title='<img src="/LibreFolio/static/icons/transactions/sell.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VENDITA' alt="Vendita">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-dividend" data-title='<img src="/LibreFolio/static/icons/transactions/dividend.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> DIVIDENDO' alt="Dividendo">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-deposit" data-title='<img src="/LibreFolio/static/icons/transactions/deposit.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> VERSAMENTO' alt="Versamento">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-adjustment" data-title='<img src="/LibreFolio/static/icons/transactions/adjustment.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> REGOLAZIONE' alt="Regolazione">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRASFERIMENTO' alt="Trasferimento Asset">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-fxconversion" data-title='<img src="/LibreFolio/static/icons/transactions/fx-conversion.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> CONVERSIONE VALUTARIA' alt="Conversione FX">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="transactions" data-name="form-modal-cash-transfer" data-title='<img src="/LibreFolio/static/icons/transactions/cash-transfer.png" style="width:24px; vertical-align:-5px; margin-right:6px;"> TRASFERIMENTO CONTANTE' alt="Trasferimento Contante">
</div>

### Transazioni Singole

Queste operano indipendentemente su un singolo conto broker.

| Tipo | Descrizione | Guida Teorica |
|------|-------------|--------------|
| ![](../../static/icons/transactions/buy.png){: width="24" style="vertical-align: middle;" } **ACQUISTO / VENDITA** ![](../../static/icons/transactions/sell.png){: width="24" style="vertical-align: middle;" } | Acquisto o vendita di un asset | [📖 Leggi](../../financial-theory/instruments/transaction-types/buy-sell.md) |
| ![](../../static/icons/transactions/deposit.png){: width="24" style="vertical-align: middle;" } **VERSAMENTO / PRELIEVO** ![](../../static/icons/transactions/withdrawal.png){: width="24" style="vertical-align: middle;" } | Versamento o prelievo di liquidità da un conto broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/deposit-withdrawal.md) |
| ![](../../static/icons/transactions/dividend.png){: width="24" style="vertical-align: middle;" } **DIVIDENDO / INTERESSE** ![](../../static/icons/transactions/interest.png){: width="24" style="vertical-align: middle;" } | Rendimento da asset azionari o a reddito fisso | [📖 Leggi](../../financial-theory/instruments/transaction-types/dividend-interest.md) |
| ![](../../static/icons/transactions/fee.png){: width="24" style="vertical-align: middle;" } **COMMISSIONE / TASSA** ![](../../static/icons/transactions/tax.png){: width="24" style="vertical-align: middle;" } | Costi come commissioni del broker o tasse | [📖 Leggi](../../financial-theory/instruments/transaction-types/fee.md) |
| ![](../../static/icons/transactions/adjustment.png){: width="24" style="vertical-align: middle;" } **REGOLAZIONE** | Correzione manuale dei saldi | [📖 Leggi](../../financial-theory/instruments/transaction-types/adjustment.md) |

### Transazioni Composite

Queste rappresentano movimenti **tra** conti o valute. Producono due voci collegate che si compensano a vicenda.

| Tipo | Descrizione | Guida Teorica |
|------|-------------|--------------|
| ![](../../static/icons/transactions/transfer.png){: width="24" style="vertical-align: middle;" } **TRASFERIMENTO** | Asset spostato tra due dei tuoi broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/transfer.md) |
| ![](../../static/icons/transactions/cash-transfer.png){: width="24" style="vertical-align: middle;" } **TRASFERIMENTO CONTANTE** | Bonifico tra broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/cash-transfer.md) |
| ![](../../static/icons/transactions/fx-conversion.png){: width="24" style="vertical-align: middle;" } **CONVERSIONE VALUTARIA** | Cambio valuta all'interno di un broker | [📖 Leggi](../../financial-theory/instruments/transaction-types/fx-conversion.md) |

---

## 📋 L'Interfaccia del Modulo

Il modulo è progettato per essere intuitivo e dinamico. Quando si seleziona un **Tipo di Transazione**, il modulo si aggiorna automaticamente per mostrare solo i campi pertinenti.

- **Dettagli Base:** Data, Tipo, Valuta e Importo.
- **Specifiche dell'Asset:** Se la transazione coinvolge un asset (come ACQUISTO o VENDITA), appariranno i campi per selezionare l'asset, inserire la quantità e impostare il prezzo unitario.
- **Pannello di Anteprima (WAC):** Per le operazioni che influenzano il portafoglio, in basso appare un'anteprima in tempo reale. Questa mostra il costo di carico attuale, il nuovo costo di carico previsto e qualsiasi guadagno/perdita realizzato.

> **💡 Note:** Il sistema gestisce automaticamente i calcoli standard per te (come la moltiplicazione della quantità per il prezzo unitario), evitando così di dover effettuare i calcoli manualmente.

---

## 🔄 Transazioni Composite

**TRASFERIMENTO** e **CONVERSIONE VALUTARIA** sono *composite* — collegano due gambe:

- **TRASFERIMENTO**: specifica un **broker di origine** e un **broker di destinazione**, oltre all'asset e alla quantità. LibreFolio registra entrambe le gambe in modo atomico.
- **CONVERSIONE VALUTARIA**: specifica l'**importo della valuta di origine** e l'**importo della valuta di destinazione** all'interno dello stesso broker.

Per dividere una transazione composta in due transazioni indipendenti, utilizza l'operazione [frazionamento](index.md) nella tabella delle transazioni.

---

## 🔗 Correlati

- 📋 **[Tabella Transazioni](index.md)** — Vista elenco, filtraggio, operazioni massive
- 📥 **[Importazione da Broker](import/index.md)** — Salta l'inserimento manuale con l'importazione BRIM
