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
