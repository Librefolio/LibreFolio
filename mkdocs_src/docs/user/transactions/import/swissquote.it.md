# <img src="https://www.swissquote.com/favicon.ico" alt=""> Swissquote

!!! warning "Beta — il feedback della community è benvenuto"

    Questo plugin è stato sviluppato a partire da **file di export di esempio** ed è attualmente in **beta**. Siamo felici di ricevere qualsiasi segnalazione per migliorarlo o per aggiornare la documentazione su come ottenere l'export.

## 📥 Come esportare

Esporta la cronologia delle tue transazioni in formato **CSV** da Swissquote e caricala in LibreFolio. Per la procedura di importazione passo passo, consulta la **[Guida all'importazione](how-to.md)**.

## 🔄 Cosa viene importato

| Nell'export (**Transaction**) | Importato come |
|:--------------------------------|:------------|
| Buy | **Acquisto** |
| Sell | **Vendita** |
| Dividend | **Dividendo** |
| Interest, Interests | **Interesse** |
| Tax, Withholding | **Imposta** |
| Custody fee, any other fee | **Commissione** |
| Debit | **Prelievo** |
| Credit | **Deposito** |
| Forex credit + Forex debit, same **Order #** | Una coppia di **Cambio valuta** collegata |

**Conversioni di valuta.** Le due gambe di una stessa conversione, un **Forex credit** e un **Forex debit**
con lo stesso **Order #**, diventano due transazioni **Cambio valuta** collegate tra loro: il denaro in uscita in una
valuta e il denaro in entrata nell'altra. Ogni gamba mantiene la propria data e il proprio **Net Amount**.

## 📝 Note

- Sviluppato a partire da export di esempio — alcuni casi limite potrebbero non essere ancora coperti.
- I costi e gli interessi maturati di un'operazione sono riportati nella sua descrizione, non importati come transazioni separate.
- Le righe che LibreFolio non conosce sono elencate in un avviso ambra, con un link per aprire una segnalazione su GitHub; un secondo avviso elenca le righe che LibreFolio non riesce a leggere.
- Hai trovato un problema o vuoi documentare i passaggi dell'export? [Apri una segnalazione](../../../community/contribute.md) — i contributi sono benvenuti!

## 🚧 Limitazioni note

- **Viene importata solo una coppia pulita di gambe forex.** Una gamba forex viene esclusa e inserita nell'avviso ambra con il link per aprire una segnalazione (aggiungi quella conversione manualmente) quando:
    - manca la sua controparte (nessun'altra gamba con lo stesso **Order #**);
    - l'ordine ha più di due gambe;
    - una gamba riporta dei **Costs** (il file non indica se il costo sia incluso o escluso dal suo **Net Amount**);
    - le due gambe sono nella stessa valuta, oppure sono entrambe in accredito o entrambe in addebito.
- **Qualcosa non torna?** [Apri una segnalazione](../../../community/contribute.md), allegando un file di esempio anonimizzato.
