# <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" alt=""> Investimental

!!! warning "Beta — feedback benvenuto"

    Questo plugin è stato scritto basandosi sui **file di esempio** e attualmente è in **beta**. Siamo felici di ricevere qualsiasi segnalazione per migliorarlo o per aggiornare la documentazione su come ottenere l'export.

## 📥 Come Esportare

Esporta lo storico delle transazioni in formato **CSV** da Investimental e caricalo in LibreFolio. Per la procedura guidata passo-passo, consulta la **[Guida all'Importazione](how-to.md)**.

## 📝 Note

- Scritto sui file di esempio — alcuni casi limite potrebbero non essere ancora coperti.
- Un ordine eseguito in più parti diventa **una** transazione con tutta la quantità e tutto l'importo eseguiti, alla data dell'ultima parte; un avviso ti dice quando le parti cadono in giorni diversi o i loro numeri non tornano. Importato con una versione precedente, un ordine così teneva solo l'ultima parte: cancella quella transazione e reimporta il file.
- Un export che comincia con un ordine già avviato (senza le sue prime righe) non può dare la quantità intera di quell'ordine: l'ordine resta fuori, e un avviso mostra cosa c'è nel file (data, prezzo, la parte che mostra) perché tu lo inserisca a mano dall'estratto.
- Ogni ordine eseguito porta la sua **commissione**, come spesa collegata al suo trade. L'export dà la commissione ancora dovuta sulla parte aperta dell'ordine, quindi la commissione di ogni eseguito è quanto quel numero scende; il risultato viene dal registro degli ordini, al prezzo dell'ordine, e può differire di poco dall'estratto, perciò un avviso chiede di controllarla. Sulle vendite e sulle obbligazioni il file scrive 0, quindi non nasce nessuna commissione: se il broker le fa pagare, aggiungile a mano. Gli ordini importati con una versione precedente ricevono le commissioni come righe libere quando reimporti il file: collegale al loro trade dalla selezione.
- Hai trovato un problema o vuoi documentare i passaggi di export? [Apri una segnalazione](../../../community/contribute.md) — ogni contributo è benvenuto!
