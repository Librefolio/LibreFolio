# <img src="https://traderepublic.com/favicon.ico" alt=""> Trade Republic

!!! warning "Beta — i feedback della community sono benvenuti"

    Questo plugin è stato creato a partire da **file di esportazione di esempio** ed è attualmente in **beta**. Siamo felici di ricevere qualsiasi segnalazione per migliorarlo o per aggiornare la documentazione su come ottenere l'esportazione.

## 📥 Come esportare

Esporta la cronologia delle tue transazioni in **CSV** da Trade Republic e caricala in LibreFolio. Per il flusso di importazione passo passo, consulta la **[Guida all'importazione](how-to.md)**.

## 📝 Note

- Creato a partire da esportazioni di esempio — alcuni casi limite potrebbero non essere ancora coperti.
- **Le colonne delle commissioni e delle imposte (*Kosten*, *Belasting*) non vengono ancora importate**: la riga stessa viene importata, e un avviso ambra elenca le righe che hanno una commissione o un'imposta, con un link per aprire una issue su GitHub. Aggiungi la commissione o l'imposta a mano. Lo stesso avviso elenca le righe che LibreFolio non conosce o non riesce a leggere.
- **Non sei sicuro che il valore netto sia davvero netto**: vedi [Verifica l'importo netto](#check-the-net-amount) qui sotto.
- Hai trovato un problema o vuoi documentare i passaggi dell'esportazione? [Apri una segnalazione](../../../community/contribute.md) — i contributi sono benvenuti!

## 🔍 Verifica l'importo netto {: #check-the-net-amount }

!!! warning "Non sappiamo se il valore netto include già la commissione e l'imposta"

    LibreFolio importa ogni Acquisto o Vendita usando la colonna **`Waarde (netto)`** ("valore netto") come
    liquidità. **Non sappiamo** se quel valore contenga già la commissione (**`Kosten`**) e l'imposta
    (**`Belasting`**) della riga: lo sviluppatore non dispone di un'esportazione recente e sicura da Trade Republic
    con cui fare un confronto.

    Un semplice esempio: acquisti azioni e Trade Republic ti addebita una commissione di 1,00 EUR.

    - **Se il valore netto include già la commissione** (per esempio 101,00 EUR, di cui 1,00 è la commissione),
      l'Acquisto è già corretto. Aggiungere a mano la commissione di 1,00 EUR, come suggerisce l'avviso ambra,
      la conterebbe **due volte**.
    - **Se il valore netto non include la commissione** (mostra 100,00 EUR), la liquidità dell'Acquisto è inferiore
      di 1,00 EUR, e la commissione va aggiunta a mano.

    Lo stesso ragionamento vale per una Vendita e per l'imposta.

**Cosa verificare, prima di aggiungere qualsiasi cosa:**

1. Scegli un Acquisto o una Vendita che abbia una commissione o un'imposta (l'avviso ambra elenca queste righe).
2. Confrontalo con il tuo **estratto del conto** o con il totale mostrato dall'app Trade Republic:
   la liquidità uscita dal tuo conto (o entrata, per una vendita) corrisponde a quella che LibreFolio mostra per
   quella riga?
3. Se i due valori **corrispondono**, la commissione è già inclusa: **non** aggiungerla. Se LibreFolio mostra **meno**
   del reale movimento di liquidità, aggiungi **Kosten** e **Belasting** a mano come transazioni separate di tipo
   Commissione e Imposta.

Un **file di esempio reale e anonimizzato** risolverebbe definitivamente la questione. Se puoi condividerne uno,
[apri una issue](https://github.com/Librefolio/LibreFolio/issues): correggeremo l'importatore e
questa pagina.
