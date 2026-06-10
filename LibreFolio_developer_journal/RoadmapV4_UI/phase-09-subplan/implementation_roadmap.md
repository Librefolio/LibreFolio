# Roadmap Implementativa: Riprogettazione Dashboard & Broker

Questa roadmap scompone la riprogettazione della Dashboard e della vista Dettaglio Broker in **Milestone Sequenziali Verificabili**. Ogni milestone produce un risultato visibile e testabile dal frontend, permettendo all'utente di validare l'estetica, la UX e la correttezza dei dati prima di procedere con la fase successiva.

---

## Milestone 1: Fondamenta Backend e API di Portafoglio (No-UI)
*Focus: Preparare i dati aggregati, le matematiche finanziarie e l'esposizione API senza toccare il frontend attuale.*

### Funzionalità Esistenti
* Backend boilerplate (FastAPI).
* `transaction_service.py` (CRUD base delle transazioni).

### Da Sviluppare
1. **Cartella Utils Finanziarie (`backend/app/utils/financial/`)** - *Vedi [plan_financial_algorithms.md](./plan_financial_algorithms.md) per i dettagli matematici*:
   * **Organizzazione WAC**: Spostamento della logica pura già esistente (`utils/financial_utils.py`) all'interno della nuova cartella. Riceverà array puliti di transazioni per calcolare il WAC, uniformandosi alla logica degli altri algoritmi. I test associati andranno mappati in `test_runner.py`.
   * **`roi_utils.py`**: Nuovo servizio unificato che espone due funzioni pure: calcolo del **TWRR** (rendimento pesato nel tempo) e **MWRR** (tasso interno di rendimento), oltre al ROI semplice.
2. **Orchestratore (`backend/app/services/portfolio_service.py`)**:
   * Nuovo orchestratore che interroga le transazioni, i prezzi correnti (FX), chiama i servizi finanziari specifici e applica la `share_percentage` dei broker.
3. **Nuovi Endpoint REST e KPI (`backend/app/api/v1/analytics.py`)**:
   * Sviluppo logica di aggregazione per le KPI cards della Dashboard (Net Worth totale, Liquidità, Gain/Loss totale, ROI percentuale).
   * `GET /api/v1/portfolio/summary`: Ritorna le KPI (NAV, Gain, TWRR, MWRR), aggregazioni di allocazione e **Breakdown per Broker** (necessario per la pagina Globale). *Supporta parametri filtro `broker_ids` e `date_range`.*
   * `GET /api/v1/portfolio/history`: Ritorna la serie temporale aggregata assoluta (Liquidità, Investito, NAV) e percentuale (`twrr`, `mwrr`, `roi`). *Supporta parametri filtro `broker_ids` e `date_range`.*
   * `GET /api/v1/portfolio/asset-history`: Ritorna lo storico del WAC vs Prezzo di mercato per il singolo asset, includendo le metriche percentuali `roi` e `twrr` per supportare la visualizzazione non diluita.

### Criterio di Verifica Utente
* Verifica tramite Swagger UI (o chiamate cURL) che gli endpoint restituiscano JSON corretti, che la matematica di TWRR/MWRR sia accurata e che le allocazioni sommino al 100%.

---

## Milestone 2: Dashboard Home (Sola Lettura & Aggregazione)
*Focus: Connettere i nuovi endpoint al frontend creando la vista aggregata principale.*

### Funzionalità Esistenti
* Componente `DateRangePicker`.
* Componente `<TransactionsTable>` (da riutilizzare in modalità minimale in fondo alla pagina).

### Da Sviluppare
1. **Nuova Pagina `/dashboard`**:
   * Layout a griglia come da `plan_ui_dashboard.md`.
2. **Componenti UI Nuovi**:
   * **Filtro Multi-Broker**: Componente popover per selezionare/deselezionare i broker da includere nel calcolo.
   * **KPI Cards**: Per visualizzare Net Worth, Gain/Loss totale e ROI (TWRR/MWRR).
   * **Grafico ECharts Growth [EUR | %]**: Collegato a `/api/v1/portfolio/history`, con toggle per passare dalle 3 linee assolute alle 3 percentuali.
   * **Grafici ECharts Allocazione**: Donut Chart per Tipo/Settore e **Mappa del Mondo** per la distribuzione geografica.
   * **Svelte Store (`portfolioStore.ts`)**: Integrare il caching a livello frontend (come da implementation plan) per evitare chiamate ridondanti.

### Criterio di Verifica Utente
* L'utente apre l'app sulla Dashboard, interagisce con il selettore date e i filtri broker, e vede tutti i grafici (Mappa inclusa) aggiornarsi fluidamente con i dati corretti. I KPI totali combaciano con le aspettative.

---

## Milestone 3: Dettaglio Broker - Shell & Tab Overview
*Focus: Ristrutturare la pagina del singolo broker, implementando la navigazione a Tab e riutilizzando il lavoro della Milestone 2.*

### Funzionalità Esistenti
* Modali e funzioni per Impostazioni & Condivisione (Share).
* Endpoint `/api/v1/brokers/{id}` per i metadati.

### Da Sviluppare
0. **Pre-Step: Pagina Global Brokers (`/brokers/+page.svelte`)**:
   * Aggiornare la UI della lista broker per includere una sezione "Altri broker" (quelli a cui l'utente non ha accesso, ovvero con `user_role === null` dal `GET /brokers` che ora fa LEFT JOIN).
   * Mostrare card minimali (solo icona e nome, nessun saldo).
   * Aggiungere il bottone "Condividi" su TUTTI i broker (propri e inaccessibili): apre la modale di sharing in `readOnly`, permettendo all'utente di vedere chi sono gli owner per richiedere l'accesso.
   * Impedire il click/accesso al dettaglio per i broker senza permessi.
1. **Ristrutturazione Layout Dettaglio (`/brokers/[id]/+page.svelte`)**:
   * Sostituire l'attuale visualizzazione fissa con un sistema a 3 Tab (Panoramica, Posizioni, Transazioni).
   * Spostare i controlli "Modifica" e "Condividi" nell'header (solo se l'utente ha permessi sufficienti).
2. **Implementazione Tab 1 (Panoramica)**:
   * Riutilizzare gli stessi componenti della Dashboard (KPI, Growth 3-Lines, Mappa Allocazione).
   * Alimentare i componenti richiamando gli endpoint di portafoglio passando il singolo `broker_id`.
   * Creare la card fissa con i "Metadati Broker" (Stato, Apertura, Plugin).

### Criterio di Verifica Utente
* L'utente entra in un broker, vede l'header rinnovato e il tab "Panoramica" perfettamente funzionante con i grafici specifici per quel broker (Mappa del mondo inclusa).

---

## Milestone 4: Dettaglio Broker - Posizioni e Modale Lotti FIFO
*Focus: Implementare la vista più complessa, l'analisi degli asset detenuti e le interazioni FIFO.*

### Funzionalità Esistenti
* `<DataTable>` (TanStack table base).

### Da Sviluppare
1. **Backend Lotti**:
   * `GET /api/v1/portfolio/lots`: Algoritmo che estrae acquisti non chiusi e vendite realizzate in rigoroso ordine FIFO (filtrato per `broker_id` e `asset_id`).
   * `GET /api/v1/portfolio/asset-history` (passando `broker_id` e `asset_id`): per ottenere la serie storica del WAC comparato col prezzo di mercato.
2. **Frontend Tab 2 (Posizioni)**:
   * Tabella delle holding del broker alimentata dal summary API.
3. **Frontend Modale Overlay**:
   * Grafico ECharts "WAC vs Valore Asset" in cima, con toggle **[EUR | %]** per mostrare TWRR e ROI.
   * Grafico ECharts "Bubble Timeline" con interazione "Goto & Pulse" attiva.
   * Tabelle separate per Lotti Aperti e Lotti Chiusi collegate agli endpoint FIFO.

### Criterio di Verifica Utente
* L'utente apre il tab Posizioni, clicca su una riga (es. AAPL), e l'overlay si apre mostrando la timeline a bolle. Cliccando una bolla, lo schermo scorre alla tabella dei lotti ed evidenzia la riga corretta. Il grafico WAC/Mercato si mostra chiaramente impilato in alto.

---

## Milestone 5: Dettaglio Broker - Transazioni & File Importati (Clean up)
*Focus: Completare le funzionalità rimanenti e deprecazione del codice obsoleto.*

### Funzionalità Esistenti
* `<TransactionsTable>` (completa).
* API transazioni e API/flusso importazione wizard BRIM.

### Da Sviluppare
1. **Backend Report Storici**:
   * Nessun nuovo endpoint da creare. Si utilizzerà l'endpoint esistente `GET /api/v1/brokers/import/files` passando il parametro `broker_id` per ottenere la lista dei file importati.
2. **Frontend Tab 3 (Transazioni)**:
   * Montare `<TransactionsTable>` fissando il filtro al broker corrente.
   * Creare una UI laterale o inferiore per l'elenco dei file importati con relativo stato.
   * Agganciare il bottone "Carica Nuovo File" all'import wizard esistente.
3. **Clean up**:
   * Rimozione dei vecchi endpoint di aggregazione placeholder (es. `/api/v1/brokers/{id}/summary` se sostituito).

### Criterio di Verifica Utente
* L'utente entra nel tab Transazioni, vede lo storico movimenti del broker e può visionare/attivare l'importazione di nuovi report CSV. Il sistema è completo e pulito.
