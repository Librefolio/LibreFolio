# 📥 <img src="https://www.intesasanpaolo.com/favicon.ico" alt=""> Intesa Sanpaolo

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio, ma potrebbero esistere casi limite.

## 📥 Come esportare

LibreFolio legge le esportazioni Intesa Sanpaolo in **CSV** *oppure* **XLSX** — non è necessario
convertire il file, basta importarlo così come viene scaricato. Sono supportati due diversi rapporti
che coprono due situazioni diverse:

- **L'elenco movimenti** (*lista movimenti*) — l'attività del conto per un periodo.
- **Lo snapshot del portafoglio** (*patrimonio*) — le posizioni correnti con la loro
 base di costo fiscale e il saldo di cassa.

Dal tuo home banking Intesa Sanpaolo, scarica l'elenco movimenti per il periodo desiderato
e, se devi anche popolare le posizioni storiche, lo snapshot del portafoglio del tuo
*Deposito Amministrato*.

## 🧭 Quali file dovrei importare?

=== "Conto appena aperto"

 Se il conto è stato **aperto di recente** e ogni acquisto è all'interno del periodo
 esportato, è sufficiente importare solo l'**elenco movimenti** — non c'è una cronologia
 pregressa da ricostruire.

=== "Conto con storico (consigliato)"

 Intesa esporta solo circa **un anno** di movimenti e **non** include
 le transazioni di acquisto originali. Per rappresentare le posizioni acquistate in precedenza,
 importa prima lo **snapshot del portafoglio**: questo popola il conto con

 - un **deposito di contante** per la liquidità riportata (quando lo snapshot contiene un saldo di cassa diverso da zero), e
 - una **rettifica della base di costo per ogni posizione** (quantità dallo snapshot, con il
 costo fiscale memorizzato come una sostituzione della base di costo **per unità**),

 tutti datati alla data dello snapshot. Poi importa l'**elenco movimenti** per aggiungere
 cedole e commissioni recenti.

## 📝 Note

- **Elenco movimenti** — il parser associa le etichette delle operazioni tramite parole chiave: *Cedole* → interessi,
 *Dividend...* → dividendo, *Commission...* → commissione, e *Ritenut...* / *Imposta...* /
 *Bollo...* → imposta. Le operazioni correnti quotidiane che possono apparire nello stesso file esportato
 (bonifici, pagamenti con carta, stipendio, ecc.) **non sono riconosciute come attività su titoli e
 vengono saltate**, con un avviso — l'importazione non fallisce mai a causa di esse.
- **Nessun ISIN nell'elenco movimenti** — il titolo viene preso dal campo di testo libero *Dettagli*,
 quindi gli asset vengono abbinati **per nome**. Lo snapshot del portafoglio *invece* riporta l'ISIN.
 Poiché i due rapporti identificano lo stesso titolo in modo diverso (nome vs ISIN), LibreFolio
 non li unirà automaticamente — conferma l'asset nel **Passaggio 4** della procedura guidata.
- **Popolamento dello snapshot** — ogni rettifica memorizza `cost_basis_override` come costo fiscale **per unità**. Intesa riporta *Controvalore di carico fiscale €* come valore totale della posizione, quindi LibreFolio lo divide per la quantità della posizione prima di memorizzarlo. Il motore successivamente moltiplica il valore per unità per la quantità per ricostruire la base di costo totale. La data dello snapshot è la data dell'ultima quotazione nel rapporto.
- **Avvisi di scadenza** — se le righe Intesa analizzate contengono cenni di scadenza/rimborso, la finestra di creazione dell'asset potrebbe mostrare un avviso informativo ambra che avverte che il titolo potrebbe essere scaduto o delistato.
- **Gli importi vengono importati così come sono** in EUR, esattamente come appaiono nel rapporto. Non viene eseguita
 alcuna conversione valutaria.

## ⛔ Prima della data di apertura del broker

Quando il tuo broker ha una **data di apertura** impostata, i movimenti datati **strettamente prima** di tale data vengono contrassegnati nella procedura guidata come **"Prima dell'apertura"** e non possono essere importati (la loro casella di spunta è disabilitata). Il giorno di apertura stesso è valido: il controllo implementato è `txDate < info.openedAt`, non `<=`. Questo impedisce di duplicare le posizioni che sono già rappresentate dal popolamento dello snapshot. Se una riga viene contrassegnata in modo errato, utilizza l'azione in linea **Modifica data broker**, poi ricontrolla/aggiorna in modo che la procedura guidata valuti la data del broker aggiornata.

## 🔗 Riferimento per sviluppatori

→ [Provider BRIM — Dettagli Implementativi](../../../developer/backend/brim/providers_list.md)
