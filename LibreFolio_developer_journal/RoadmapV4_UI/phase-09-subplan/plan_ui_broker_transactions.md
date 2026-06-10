# Piano UI: Dettaglio Broker - Tab Transazioni & File

Questo documento descrive il wireframe ASCII per il tab dedicato allo storico transazioni e alla gestione dei report BRIM importati.

## Tab Transazioni

```text
+-------------------------------------------------------------------------------------------------+
|  <- Torna ai Broker                                                                             |
|  [Icon] DIRECTA  (Ruolo: OWNER | Quota: 100%)                              [Share] [Sincronizza] |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|   [ PANORAMICA ]   [ POSIZIONI ]   [* TRANSAZIONI *]                                            |
|                                                                                                 |
|   +-----------------------------------------------------------------------------------------+   |
|   |  TRANSAZIONI & FILE IMPORTATI                                                           |   |
|   |                                                                                         |   |
|   |  [ COMPONENTE <TransactionsTable> ]                                                     |   |
|   |  (Tabella completa con paginazione, ricerca, export già implementati)                   |   |
|   |                                                                                         |   |
|   |  FILE IMPORTATI (BRIM Report)                                                           |   |
|   |  +--------------------------+---------------------+------------+                        |   |
|   |  | Report_Directa_01.csv    | 2026-05-10 14:00    | ✅ Successo |                        |   |
|   |  | Report_Directa_02.csv    | 2026-06-01 09:30    | ✅ Successo |                        |   |
|   |  +--------------------------+---------------------+------------+                        |   |
|   |  [+ Carica Nuovo File]  <-- Apre l'import wizard esistente                              |   |
|   +-----------------------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------+
```

---

## Requisiti Dati Frontend

Per renderizzare questo tab, il frontend necessita delle seguenti funzionalità:

### Funzionalità Esistenti (da riutilizzare o integrare):
* **Componente `<TransactionsTable>`**: Esiste ed è completamente funzionale. Va montato nel tab passando il `broker_id` come filtro fisso.
* **API Transazioni (`GET /api/v1/transactions`)**: Esiste e supporta già i filtri e l'impaginazione.
* **Wizard di Importazione BRIM**: Esiste (il flusso in modale o pagina separata che permette il caricamento del CSV).
* **Storico File Importati (`GET /api/v1/brokers/import/files`)**: Esiste. L'endpoint restituisce la lista dei report caricati filtrabili per `broker_id`, completo di metadati e stato (es. PARSED, FAILED).

### Funzionalità da Sviluppare (Frontend):
* **UI Lista File**: Un piccolo componente per mostrare i file importati usando l'API esistente (tabella minimale) e il bottone per triggerare il wizard.
