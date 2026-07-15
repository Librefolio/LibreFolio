# Piano UI v2: Tab Transazioni & File Importati (Milestone_3 — Fase 3)

> **Supersede**: [`../plan_ui_broker_transactions.md`](../plan_ui_broker_transactions.md) (disegno originale).
> **Fasi correlate**: ← [`plan_ui_broker_overview.md`](./plan_ui_broker_overview.md) (Fase 1, shell tab) ·
> ← [`plan_ui_broker_holdings.md`](./plan_ui_broker_holdings.md) (Fase 2).

## Perché un v2

Questa è la fase con meno divario rispetto al disegno originale: tutti i pezzi previsti allora
(`<TransactionsTable>`, API transazioni con filtro broker, wizard import, storico file) esistevano già e
**restano validi oggi**. L'unico aggiornamento reale è di collocazione (questo contenuto finisce sotto il
terzo tab della shell introdotta in Fase 1, sostituendo la sezione "Transazioni recenti" + bottone Import
File che oggi vivono nella colonna destra della pagina piatta) e una nota tecnica sul modo migliore di
recuperare i dati filtrati per broker (vedi sotto).

---

## Wireframe Tab Transazioni

```text
+-------------------------------------------------------------------------------------------------+
|  <- Torna ai Broker                                                                             |
|  [Icon] DIRECTA  (♛ Owner · Quota: 100%)                                    [Share] [↻ Refresh] |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|   [ PANORAMICA ]   [ POSIZIONI ]   [* TRANSAZIONI *]                                            |
|                                                                                                 |
|   +-----------------------------------------------------------------------------------------+   |
|   |  TRANSAZIONI                                                          [+ Nuova Tx]      |   |
|   |                                                                                         |   |
|   |  [ <TransactionsTable> — stessa tabella di /transactions, con filtro broker fisso ]     |   |
|   |  (paginazione, ricerca, ordinamento, filtri colonna, azioni riga: già tutto esistente)  |   |
|   |                                                                                         |   |
|   |-----------------------------------------------------------------------------------------|  |
|   |                                                                                         |   |
|   |  FILE IMPORTATI (BRIM Report)                                                           |   |
|   |  +--------------------------+---------------------+------------+                        |   |
|   |  | Report_Directa_01.csv    | 2026-05-10 14:00    | ✅ Successo |                        |   |
|   |  | Report_Directa_02.csv    | 2026-06-01 09:30    | ✅ Successo |                        |   |
|   |  +--------------------------+---------------------+------------+                        |   |
|   |  [+ Carica Nuovo File]  <-- apre lo stesso wizard import esistente                      |   |
|   +-----------------------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------+
```

Note sul disegno:
- Rispetto all'originale non cambia nulla nel disegno visivo — cambia solo la collocazione (era già
  presente nella pagina piatta come "Transazioni recenti" + bottone Import File nella colonna destra, ora
  diventa il contenuto pieno del terzo tab, con la tabella completa invece della sola lista recente).
- **Nota tecnica sul fetch dati** (l'unico punto non banale di questa fase): la pagina `/transactions`
  attuale carica *tutte* le transazioni dell'utente in un colpo solo
  (`query_transactions_api_v1_transactions_get({} as never)`, nessun filtro passato all'API) e poi applica i
  filtri — incluso l'eventuale `broker_id` — **lato client** tramite le colonne filtrabili della
  `<DataTable>`. Per il tab broker-scoped conviene invece sfruttare il filtro `broker_id` **lato server**
  già supportato da `GET /transactions` (`backend/app/api/v1/transactions.py:193`), per non scaricare
  l'intero storico utente quando serve solo quello di un broker. Va however considerato che
  `<TransactionsTable>` distingue `mainRows` (righe che passano il filtro) da `partnerRows` (righe "ghost"
  per il lato non filtrato di una transazione collegata, es. un TRANSFER verso un altro broker): filtrando
  lato server per un solo `broker_id`, la gamba collegata su un broker diverso non rientra nella risposta e
  andrebbe recuperata con una query supplementare se si vuole preservare il rendering "ghost row" delle
  transazioni collegate cross-broker. Decisione da prendere in implementazione, non blocca il disegno UI.

---

## Requisiti Dati Frontend

### Funzionalità Esistenti (da riutilizzare così come sono)

* **`<TransactionsTable>`** (`frontend/src/lib/components/transactions/TransactionsTable.svelte`) — esiste
  ed è completamente funzionale (ordinamento, filtri colonna con sync URL, paginazione "pair-never-split",
  azioni riga, modalità `compact`). Va montata passandole `mainRows`/`partnerRows` già filtrati per il
  broker corrente.
* **`GET /transactions`** (`query_transactions`, `backend/app/api/v1/transactions.py:192-193`) — supporta
  già `broker_id` come query param opzionale lato server.
* **`BrokerImportFiles.svelte`** e **`BrokerImportFilesModal.svelte`**
  (`frontend/src/lib/components/brokers/`) — già accettano una prop `brokerId`, già interrogano
  `broker_ids: [brokerId]` per lo storico file e già postano su
  `/api/v1/brokers/import/upload?broker_id=...` per il wizard di caricamento. Nessuna modifica necessaria,
  solo montaggio nel nuovo tab.
* **Wizard di Importazione BRIM**: invariato, si apre dal bottone "Carica Nuovo File" come oggi.

### Funzionalità da Sviluppare (Backend & API)

* Nessun gap identificato per questa fase.

### Funzionalità da Sviluppare (Frontend)

* **Cablaggio del fetch scoped-per-broker**: nuova funzione di caricamento dati per il tab (analoga a
  quella di `/transactions` ma con `broker_id` passato server-side, vedi nota tecnica sopra) — riuso della
  UI esistente, solo la query cambia.
* **Riposizionamento** dei blocchi "Transazioni recenti" e "Import File" dalla colonna destra della pagina
  piatta attuale al nuovo tab dedicato — puro refactor di collocazione, nessuna nuova logica.

---

## Recap implementazione (post Fase 1 + 3, questo aggiornamento)

Confrontando con l'implementazione reale nella pagina broker detail:

### ✅ Realizzato come pianificato

- `<TransactionsTable>` montata nel tab, con `broker_id` filtrato **lato server** (non client-side come
  `/transactions`) — esattamente la nota tecnica di questo piano.
- Gestione righe "ghost"/partner (gamba collegata su un broker diverso, es. TRANSFER) tramite una query
  supplementare — esattamente come anticipato, **nessuna sorpresa in implementazione**.
- Paginazione, ordinamento, filtri colonna — ereditati gratis da `<TransactionsTable>`/`DataTablePagination`.
- "+ Carica Nuovo File" → apre `BrokerImportFilesModal` esistente, invariato.

### 🆕 Aggiunto, non previsto dal piano

- **`loadPartnerRows`/`loadEventTooltipMap` estratte in un modulo condiviso**
  (`frontend/src/lib/components/transactions/shared/loadTransactionRows.ts`) — il piano anticipava solo
  il *bisogno* della query supplementare per il tab broker-scoped; in pratica la stessa logica era
  duplicata anche in `/transactions/+page.svelte`, quindi è stata generalizzata e ora la usano entrambe le
  pagine (miglioramento non richiesto dal piano, ma diretta conseguenza del principio "riusa i componenti
  già scritti").
- **`hideActions={true}`** — scelta deliberata (non specificata nel wireframe) di rendere il tab Transazioni
  di Broker Detail **sola lettura** (niente edit/delete/clone/split inline, solo "view" su doppio click) —
  coerente con un feedback esplicito dell'utente in un altro punto della sessione ("depositi/prelievi sono
  transazioni, si fanno da lì", riferito alla Cassa — la logica è stata estesa: le transazioni si
  gestiscono dalla vista Transazioni dedicata, non da altri punti della UI).
  * ⚠️ Il wireframe di questo piano mostra ancora `[+ Nuova Tx]` nell'header del tab (riga 29) —
    **contraddizione da risolvere**: o si aggiunge il bottone (rompendo la scelta "sola lettura" fatta
    altrove), o si aggiorna il wireframe per rimuoverlo (confermando la linea "sola lettura, CRUD solo da
    /transactions o dal wizard import").
- Caricamento lazy (solo al primo accesso al tab, non al mount della pagina) — dettaglio di efficienza non
  specificato nel piano.
- La stessa Dashboard Home (fuori scope di questo documento, ma stesso pattern) ha ricevuto un tab
  "Transazioni" identico — la scelta "sola lettura" + paginazione completa + filtro broker/periodo è stata
  replicata lì.

### ❌ Mancante rispetto al piano — risolto (2026-07-08)

- **Lista "FILE IMPORTATI" (storico import)**: il componente `BrokerImportFiles.svelte`
  (`frontend/src/lib/components/brokers/BrokerImportFiles.svelte`) **esiste già** (accetta `brokerId`,
  interroga lo storico file) ma **non è montato da nessuna parte** nel tab Transazioni attuale — oggi c'è
  solo il bottone "+ Carica Nuovo File" che apre il wizard, nessuna tabella con lo storico
  Report_Directa_01.csv / stato PARSED-FAILED come da wireframe.
  > ✅ **Risolto**: bottone rinominato "Report Caricati" (`brokers.showImportHistory`,
  > `data-testid="broker-show-import-history"`) → continua ad aprire `BrokerImportFilesModal` invariata
  > (che mostra già lo storico file con stato) invece di montare `BrokerImportFiles.svelte` inline — stessa
  > necessità coperta, meccanismo diverso da quello immaginato nel wireframe. **Accettato così**, vedi Todo
  > 5/6 sotto.
- **`[+ Nuova Tx]`**: non implementato (vedi sopra, decisione da confermare/wireframe da aggiornare).
  > ✅ **Risolto**: bottone "Nuova Tx" (`data-testid="broker-new-transaction"`) → `TransactionBulkModal` con
  > `intent: {action: 'create'}` + `defaultBrokerId={broker.id}`. Wireframe riga 29 confermato, nessuna
  > contraddizione residua.

## Decisioni prese (aggiornamento post-recap)

1. **Holdings Fase 2** (fuori scope di questo file, vedi `plan_ui_broker_holdings.md` §1bis): confermata
   Opzione A (modale Lotti FIFO resta dentro Broker Detail).
2. **"File Importati" → "Report Caricati"**: da tabella-con-bottone-import a vista **meno invasiva**,
   sola visualizzazione + eventuale aggiunta, spostando l'azione di import primaria altrove (punto 3).
3. **Nuovo bottone "Importa Transazioni" in cima alla pagina** (non più dentro un blocco dedicato) che
   apre — **non un wizard separato**, ma esattamente lo stesso flusso già usato da `/transactions` — vedi
   dettaglio tecnico sotto.
4. **Nuovo bottone "Nuova Tx"**, 3° bottone accanto a "Report Caricati" e "Importa", stessa riga —
   estetica da decidere in fase di implementazione (mockup libero).
5. Entrambi i bottoni (Importa / Nuova Tx) devono **pre-popolare il broker della pagina corrente** nel
   modale che aprono, ma **senza saltare uno step** — il campo broker resta visibile/editabile, solo il
   valore iniziale cambia.

### Scoperta tecnica chiave: "l'import wizard di /transactions" non è `BrokerImportFilesModal`

Investigando il bottone "Importa" di `/transactions/+page.svelte` (`onImportFromBroker()`, riga 199-202):
apre **`TransactionBulkModal`** con `intent: {action: 'import'}` — lo **stesso** componente usato per
"Nuova Transazione" (`intent: {action: 'create'}`), non un modale separato. `TransactionBulkModal`, al suo
interno, apre poi **`ImportWizardModal.svelte`** (righe 62, 1968, 3158) per lo step di
selezione/upload/parsing file, i cui risultati confluiscono nella stessa griglia bulk per la validazione —
è un flusso **unificato**: import e creazione manuale condividono lo stesso motore di validazione/commit
bulk. Questo è ciò che l'utente intende per "wizard presente in transactions/" — **non**
`BrokerImportFilesModal` (componente più vecchio e più semplice, oggi montato in Broker Detail).

### Hook di pre-popolazione broker — già quasi pronto

- `TransactionBulkModal.svelte::defaultFields()` (righe 152-156) ha già un concetto di `defaultBroker`,
  oggi calcolato solo come "se l'utente ha un solo broker totale, usa quello" (`brokers.length === 1 ?
  brokers[0].id : 0`). **Estensione minima**: aggiungere una prop opzionale `defaultBrokerId?: number` a
  `TransactionBulkModal`, usata in `defaultFields()` con priorità sulla euristica attuale.
- `ImportWizardModal.svelte` ha un proprio stato `globalBrokerId` (riga 97, oggi sempre `null` all'apertura)
  che si applica a tutti i file non ancora assegnati singolarmente (`onGlobalBrokerChange`, righe
  1014-1019). **Stessa estensione**: prop opzionale `defaultBrokerId?: number | null`, passata da
  `TransactionBulkModal` (che la riceve dal chiamante) fino a `ImportWizardModal`, per inizializzare
  `globalBrokerId` invece di `null`. Il campo resta comunque cambiabile per-file o globalmente.
- **`broker.default_import_plugin` è GIÀ usato correttamente**: `ImportWizardModal::pickBestPlugin()`
  (righe 1168-1183) già preferisce `broker.default_import_plugin` quando compatibile con i plugin
  supportati dal file — **nessun lavoro necessario**, il sospetto dell'utente era corretto.
- **Il picker "collega a transazione esistente" è già globale**: `TransactionPickerModal` (usato per
  linking, es. TRANSFER/FX_CONVERSION) non riceve alcun filtro broker oggi — cerca già su tutte le
  transazioni indipendentemente da dove si apre il bulk modal. **Nessuna modifica necessaria**, il
  comportamento desiderato dall'utente è già quello attuale.

### Impatto su `BrokerImportFilesModal`/`BrokerImportFiles.svelte`

Questi due componenti (più vecchi, upload semplice senza il motore di validazione bulk) diventano
**ridondanti** come punto di INGRESSO per l'import (sostituiti dal bottone "Importa Transazioni" →
`TransactionBulkModal`+`ImportWizardModal`). `BrokerImportFiles.svelte` resta utile come **vista di sola
lettura "Report Caricati"** (storico file + stato parsing) — va verificato se la sua UI attuale può essere
semplificata (rimuovendo la sua logica di upload propria, ormai duplicata) o se conviene scriverne una
versione più snella.

### Todo di implementazione — stato finale (aggiornato 2026-07-08)

1. ✅ **Fatto** — `defaultBrokerId?: number` su `TransactionBulkModal`.
2. ✅ **Fatto** — `defaultBrokerId?: number | null` su `ImportWizardModal`, inizializza `globalBrokerId` da
   essa.
3. ✅ **Fatto** — bottone "Importa Transazioni" (`data-testid="broker-import-transactions"`) →
   `TransactionBulkModal` con `intent: {action: 'import'}` + `defaultBrokerId={broker.id}`.
4. ✅ **Fatto** — bottone "Nuova Tx" (`data-testid="broker-new-transaction"`) → `TransactionBulkModal` con
   `intent: {action: 'create'}` + `defaultBrokerId={broker.id}`.
5. ❌ **Non si fa** (deciso 2026-07-08 dall'utente): nessuna ulteriore semplificazione oltre al rinominare
   il bottone in "Report Caricati" — `BrokerImportFilesModal` resta con la sua UI di upload invariata.
6. ❌ **Non si fa** (deciso 2026-07-08 dall'utente): `BrokerImportFilesModal` **non viene ritirata/ritagliata**
   — resta un secondo punto di ingresso import ridondante ma innocuo accanto a "Importa Transazioni". Stato
   attuale accettato così com'è.

**Fase 3 (Tab Transazioni) considerata chiusa con questo aggiornamento** — nessun altro todo aperto su
questo file. Codice presente in working tree (non ancora committato al momento di questa nota).
