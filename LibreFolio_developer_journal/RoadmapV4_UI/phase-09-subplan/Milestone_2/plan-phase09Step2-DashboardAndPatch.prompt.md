# Piano Implementativo: Milestone 2 & Backend Patch

## Riferimenti UI e Documentali
* [Piano UI - Dashboard Home](file:///Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/plan_ui_dashboard.md)
* [Implementation Plan Generale](file:///Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/implementation_plan.md)
* [Roadmap Implementativa](file:///Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/implementation_roadmap.md)

## Obiettivo
Implementare la Milestone 2 della riprogettazione UI (Dashboard Home) e risolvere il gap evidenziato nella Milestone 1 relativo alle serie temporali percentuali (TWRR, MWRR, ROI) in modo da supportare i grafici di crescita con il toggle `[ EUR | % ]`.

Questo piano andrà seguito passo per passo. Ricordarsi di aggiornare questo file annotando "✅" e le "Note implementazione" alla fine di ogni step.

---

## Step 1: Backend Patch (Serie Storiche Percentuali)
**Target:** `backend/app/schemas/analytics.py`, `backend/app/services/portfolio_service.py`, `backend/app/api/v1/analytics.py`

1. **Modifica Schemi:** 
   In `backend/app/schemas/analytics.py`, estendere i modelli `PortfolioHistoryPoint` e `AssetHistoryPoint` aggiungendo i seguenti campi opzionali (default `None`):
   ```python
   twrr: SafeDecimal | None = None
   mwrr: SafeDecimal | None = None
   roi: SafeDecimal | None = None
   ```
2. **Aggiornamento Servizi (`portfolio_service.py`):**
   * Nei metodi `get_history` e `get_asset_history`, dopo aver generato le serie assolute di NAV e Investito, chiamare `calculate_twrr_series`, `calculate_simple_roi_series` e `calculate_mwrr_series` da `roi_utils.py` per popolare tutti i campi percentuali (`twrr`, `roi`, `mwrr`).
   * **Decisione Tecnica sul MWRR:** Il calcolo MWRR è computazionalmente pesante (Newton-Raphson), ma grazie all'ottimizzazione warm-start iterativa implementata in `roi_utils.py`, **abbiamo deciso di includerlo** nelle serie storiche. *Attenzione*: assicurarsi di avvolgere la chiamata a `calculate_mwrr_series` in `asyncio.to_thread(...)` per non bloccare l'event loop di FastAPI.
3. **Rigenerazione Client:**
   Eseguire il comando `./dev.py api sync` dal terminale per aggiornare il client Zodios Typescript con i nuovi schemi.

---

## Step 2: Frontend State Management (`portfolioStore.ts`)
**Target:** `frontend/src/lib/stores/portfolioStore.ts`

1. **Creazione Store Reattivo (Svelte 5 Runes):**
   Creare lo store per gestire la cache del portafoglio senza usare i vecchi `writable` store, ma usando lo state globale con Svelte 5.
   * Struttura della cache: dizionario (Map) in cui la chiave è determinata dai parametri della query (es. `broker_ids` e `date_range`) per `summary` e `history`.
2. **Metodi di Accesso e Aggiornamento:**
   * Esportare le funzioni `fetchSummary(brokerIds: number[] | null, force: boolean = false)` e `fetchHistory(...)` che ritornano i dati in cache se presenti (e validi) altrimenti eseguono la chiamata via API.
   * Aggiungere uno stato `isLoading` e `error` per gestire il feedback visivo.
3. **Metodo `invalidate()`:**
   * Aggiungere la funzione per svuotare la cache forzatamente. Da invocare quando si importano file o si alterano le transazioni, oppure premendo il pulsante "Sincronizza".

---

## Step 3: Sviluppo Componenti UI e Dashboard Home
**Target:** `frontend/src/routes/dashboard/+page.svelte` (e relative dipendenze UI)

1. **Nuova Pagina Dashboard (`/dashboard`):**
   * Creare la nuova route principale della dashboard (se la Home è altrove, decidere il routing di default per reindirizzare a `/dashboard`).
2. **Filtri e Controlli Globali (Header):**
   * Inserire un componente "Filtro Broker": un popover con checklist multipla (ispirato al selettore in `assets/`) per includere/escludere broker dal calcolo.
   * Collegare il pulsante `[↻ Sincronizza]` a `portfolioStore.invalidate()`.
   * Inserire il componente esistente `DateRangePicker`.
3. **KPI Cards:**
   * Implementare tre card in alto per mostrare i totali ricavati da `portfolioStore.summary`:
     - **Net Worth Complessivo** (ed eventuale cash/liquidità).
     - **Gain/Loss** (Assoluto in EUR e Percentuale Semplice).
     - **ROI Pesato** (TWRR e MWRR finali dal summary).
4. **Grafici di Allocazione (Donut e Map):**
   * Implementare un `Donut Chart` (ECharts) per mostrare `allocation_by_type` e `allocation_by_sector`.
   * Recuperare ed integrare il componente `GeographyMap.svelte` (mappa del mondo) per visualizzare la `allocation_by_geography`, mappando a parte la categoria "Unknown".
5. **Grafico di Crescita ECharts (Growth 3-Lines):**
   * Creare il grafico ECharts primario che riceve la `history` API.
   * Inserire un toggle UI `[ EUR | % ]`.
   * Modalità **EUR**: mostra linee per `Cash`, `Investito` e `Valore NAV`.
   * Modalità **%**: mostra le linee per `ROI Semplice`, `TWRR` e `MWRR`.
6. **Ultime Transazioni:**
   * Inserire in fondo alla pagina il componente `<TransactionsTable>` esistente.
   * Passare al componente flag per disattivare funzioni avanzate superflue e impostarlo per mostrare solo le ultime X righe recenti, agendo da activity log.

---

## Step 4: Verifica Finale e Debugging
**Target:** Manual testing da UI

1. Aprire l'applicazione sulla `/dashboard`.
2. Verificare che non si presentino errori nel calcolo dei campi API e che le carte KPI siano corrette e si aggiornino cambiando broker/date.
3. Testare il toggle del grafico Growth `[ EUR | % ]` per accertarsi che transizioni fluidamente.
4. Controllare che il tooltip e il rendering della Mappa Geografica gestisca correttamente la voce "Unknown" e colorizzi appropriatamente i pesi in base al Valore NAV di Mercato.
5. Verificare dal pannello Network che le chiamate di portafoglio vengano cachate (non richiamate 2 volte per gli stessi parametri) finché non si preme esplicitamente il pulsante Sincronizza.
