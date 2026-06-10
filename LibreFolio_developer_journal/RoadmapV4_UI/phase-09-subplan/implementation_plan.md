# Piano Creativo di Riprogettazione — Dashboard & Broker

Questo documento definisce l'interfaccia utente (UI), i layout e le funzionalità analitiche avanzate per la Dashboard Home e la pagina dei Dettagli del Broker, con l'obiettivo di renderle visivamente eccezionali e coerenti.

---

## Struttura e Navigazione del Dettaglio Broker

La pagina di dettaglio del broker viene riorganizzata in un'interfaccia a **tre Tab** principali, mantenendo le attuali modali tramite pulsanti in alto a destra per gestire "Impostazioni" e "Accessi/Condivisione", evitando di disperdere queste funzionalità in tab aggiuntive:

1. **Overview (Panoramica)**:
   * KPI rapidi (NAV, P&L, ROI pesato, Cash) ereditati dallo stesso componente della Dashboard principale (filtrati per questo singolo broker).
   * Grafico di crescita a tre linee (Liquidità + Investito vs Valore Teorico complessivo).
   * Allocazione Patrimoniale (Donut per tipo, settore, nazione + Mappa del mondo per distribuzione geografica).
   * Scheda informativa fissa con i metadati del broker (regime, stato attivo, data di creazione, plugin di import).
2. **Holdings (Posizioni)**:
   * Tabella interattiva basata su `DataTable` (TanStack Table) con ordinamento e ricerca.
   * Cliccando su una riga (asset) si apre una modale overlay con il **dettaglio lotti FIFO**.
3. **Transactions (Transazioni & File)**:
   * Tabella paginata di tutte le transazioni del broker (riutilizzando integralmente il componente `<TransactionsTable>`).
   * Pannello dei **File Importati**: lista dei report BRIM caricati per questo broker, con stato (importato/fallito) e la possibilità di caricare nuovi file triggerando l'attuale workflow di importazione in transazioni.

---

## Wireframe dell'Interfaccia (ASCII Art)

Per mantenere questo piano conciso, i wireframe dettagliati con le ASCII art sono stati separati in documenti specifici per ogni tab. Puoi consultarli cliccando sui seguenti link:

- **Home Dashboard**: [Piano UI - Dashboard Home](file:///Users/ea_enel/.gemini/antigravity/brain/eefade00-c698-4d32-b4f8-2e20273f92d7/plan_ui_dashboard.md)
- **Broker (Panoramica)**: [Piano UI - Broker Overview](file:///Users/ea_enel/.gemini/antigravity/brain/eefade00-c698-4d32-b4f8-2e20273f92d7/plan_ui_broker_overview.md)
- **Broker (Posizioni e Lotti)**: [Piano UI - Broker Holdings](file:///Users/ea_enel/.gemini/antigravity/brain/eefade00-c698-4d32-b4f8-2e20273f92d7/plan_ui_broker_holdings.md)
- **Broker (Transazioni)**: [Piano UI - Broker Transactions](file:///Users/ea_enel/.gemini/antigravity/brain/eefade00-c698-4d32-b4f8-2e20273f92d7/plan_ui_broker_transactions.md)

---

## Logica dei Grafici e delle Analisi

### 1. Il Grafico di Crescita (Cash, Investito, Valore Teorico)
Il grafico ECharts della crescita utilizzerà tre serie sovrapposte per spiegare dove si trova la ricchezza del portafoglio:
- **Linea 1: Liquidità Disponibile (Cash)**: L'ammontare liquido non investito detenuto sul broker nelle varie valute (convertito in valuta base).
- **Linea 2: Capitale Investito (Costo di Carico)**: Il valore cumulato degli acquisti di asset effettuati (quando si acquista, la liquidità scende e l'investito sale).
- **Linea 3: Valore Teorico Complessivo (NAV)**: Ottenuto sommando la Liquidità al valore di mercato attuale delle posizioni in titoli (calcolato tramite i prezzi storici dei provider). La differenza tra Linea 3 e (Linea 1 + Linea 2) rappresenta il guadagno/perdita non realizzato.

### 2. Metriche ROI: TWRR e MWRR
* **TWRR (Time-Weighted Rate of Return)**: Misura le performance della selezione dei titoli, eliminando il rumore dei depositi/prelievi inseriti nel tempo.
* **MWRR (Money-Weighted Rate of Return)**: Corrisponde al Tasso Interno di Rendimento (IRR) ed evidenzia l'impatto reale che il timing dei movimenti di capitale dell'utente ha avuto sul rendimento effettivo.
* Queste logiche matematiche (TWRR, MWRR) verranno sviluppate all'interno di un unico file `roi_utils.py` all'interno di una nuova cartella `backend/app/utils/financial/`. Anche l'esistente logica pura del WAC (attualmente in `utils/financial_utils.py`) verrà spostata e organizzata in questa cartella. In questo modo tutte le funzionalità finanziarie matematiche saranno pure funzioni slegate dal DB.
* Questi servizi puri (WAC, ROI) verranno orchestrati da `portfolio_service.py` ed esposti tramite nuovi endpoint definiti in `backend/app/api/v1/analytics.py`. I risultati verranno mostrati a livello di KPI cards sia per il singolo broker sia in modalità aggregata sulla Dashboard.
* **Documentazione**: Sarà redatto un documento esplicativo dei calcoli teorici di TWRR e MWRR all'interno della sezione teorica della documentazione del progetto in `mkdocs_src/docs/financial-theory/`.

### 3. Allocazioni Patrimoniali Pestate (Sector, Geography, Asset Type)
Le allocazioni mostrate nella Dashboard e nei Broker saranno pesate in base al **Valore Teorico di mercato attuale** (prezzi correnti + tassi di cambio aggiornati).
* Se per un asset i metadati relativi al settore o all'area geografica sono assenti o incompleti, questi verranno raggruppati in una categoria esplicita denominata **"Unknown" (Ignoto)**, per distinguerla chiaramente da "Other" (Altro, che contiene invece settori noti ma di peso percentuale trascurabile).

---

## Gap Analysis: Attuale vs Desiderato

### 1. Backend: Dati e API
* **Situazione Attuale**: `broker_service.py` ha il metodo `get_summary` che calcola dinamicamente le holding (`BRAssetHolding`) interpellando il `transaction_service`. Non c'è alcun raggruppamento multi-broker, né una vista aggregata del portafoglio (`NAV`, `MWRR`, `TWRR`). Manca il calcolo dei lotti FIFO.
* **Cosa Manca**:
  * **`portfolio_service.py`**: Un nuovo servizio dedicato ad aggregare saldi, posizioni e transazioni, applicando il filtro `share_percentage` dell'utente per le quote in comproprietà. Gestirà sia i calcoli globali che quelli del singolo broker.
  * **Nuovi Endpoint Unificati (Famiglia `/portfolio`)**:
    * `GET /api/v1/portfolio/summary`: per la vista aggregata (Cash, NAV, Holdings aggregati). Accetta `broker_id` opzionali per restringere il calcolo a uno o più broker.
    * `GET /api/v1/portfolio/history`: per ottenere la serie storica a tre linee (Liquidità, Investito, Valore Teorico) necessaria al Grafico di Crescita. Se viene passato un `asset_id`, l'endpoint cambia natura per restituire lo storico del WAC vs Prezzo di mercato.
    * `GET /api/v1/portfolio/lots`: logica core FIFO per separare lotti aperti/chiusi e calcolare il realized/unrealized P&L specifico per lotto.
    * **NOTA SULLA DEPRECAZIONE**: Gli endpoint esistenti (`/api/v1/brokers/{id}/summary` e altri vecchi placeholder) verranno rimossi poiché le loro funzioni saranno interamente assorbite da questi nuovi endpoint unificati.
  * **Calcoli ROI e Financial Utils (`backend/app/utils/financial/`)**: Implementazione delle formule matematiche TWRR (valutazione periodale in base ai flussi) e MWRR (IRR sui flussi di cassa) in moduli dedicati, trattandoli come componenti di dominio matematico-finanziario isolati e riutilizzabili.
  * **Endpoint API (`backend/app/api/v1/analytics.py`)**: Conterrà l'esposizione web degli endpoint di portfolio/analytics.

### 1.1. Backend Patch: Serie Temporali Percentuali (TWRR, MWRR, ROI)
* **Situazione Attuale**: L'implementazione base della Milestone 1 ha correttamente erogato TWRR/MWRR come snapshot finale nel `summary`. Le serie storiche (`/history` e `/asset-history`) attualmente restituiscono i valori assoluti (EUR) in piena conformità con il piano originale.
* **Intervento Richiesto**:
  * Poiché abbiamo recentemente deciso di implementare un toggle `[EUR | %]`, dobbiamo aggiornare l'API per erogare anche le versioni "in serie".
  * Modificare i modelli Pydantic `PortfolioHistoryPoint` e `AssetHistoryPoint` in `schemas/analytics.py` per accogliere i nuovi campi opzionali `twrr`, `mwrr` e `roi`.
  * Aggiornare `portfolio_service.py` affinché invochi le funzioni `calculate_twrr_series` e `calculate_mwrr_series` (già scritte e pronte in `roi_utils.py`) per popolare questi nuovi campi nei payload di output.
  * *Open Question per te:* Dato che il MWRR rolling iterativo è computazionalmente pesante (deve rifare il root-finding di Newton per ogni giorno del grafico), vogliamo provarci comunque o vogliamo escludere l'MWRR dalle serie storiche (lasciandolo solo nel summary), limitandoci a inviare TWRR e ROI per i grafici?

### 3. Frontend State Management & Caching (Store)
* Per evitare il ricalcolo continuo del portafoglio durante la normale navigazione, verrà implementato un sistema di **caching lato frontend** tramite uno Svelte Store dedicato (es. `portfolioStore.ts`).
* **Single Source of Truth Trasversale**: Questo store sarà l'unica fonte di verità e deve essere riutilizzato in tutte le viste:
  - **Dashboard (Home)**: per memorizzare la vista aggregata globale.
  - **Global Brokers Page (`/brokers`)**: per estrarre l'array `by_broker` senza rifare chiamate di rete.
  - **Broker Detail (`/brokers/[id]`)**: lo store dovrà gestire la cache parametrizzata (es. salvare in cache le chiavi specifiche per il broker `summary?broker_ids=X`).
  - **Analisi Storiche e di Dettaglio**: Lo store manterrà in memoria anche le risposte degli endpoint `history` e `asset-history`, azzerando i tempi di caricamento tra i vari tab interni del broker.
* **Funzionamento**:
  1. Il frontend interroga prima lo Store locale passandogli gli argomenti (es. `broker_ids`). Se i dati sono già presenti, la pagina renderizza istantaneamente.
  2. Se i dati sono assenti, lo Store lancia la fetch verso l'API corrispondente e ne salva il risultato associato a quella chiave.
* **Invalidazione (Smart Cache)**: Lo store verrà svuotato (invalidato) in automatico ogni qualvolta l'utente esegue un'operazione CRUD sulle transazioni (creazione, modifica, eliminazione) o importa un nuovo file CSV, garantendo così dati sempre freschi al caricamento successivo.
* **Refresh Manuale**: Verrà inserito un pulsante di "Sincronizzazione/Refresh" [↻] nelle UI (Dashboard e Dettaglio Broker) per permettere all'utente di bypassare la cache e forzare il ricalcolo.

### 4. Frontend: Componenti e Layout
* **Situazione Attuale**: La pagina del Broker (`/brokers/[id]/+page.svelte`) è una struttura basica a tre colonne fisse. Le transazioni sono visualizzate tramite l'ottimo e completo `<TransactionsTable.svelte>`, che offre già ricerca, tag, navigazione e view modale.
* **Cosa Manca**:
  * **Ristrutturazione Pagina Broker**: Implementare i 3 tab (Panoramica, Posizioni, Transazioni & File), mantenendo gli attuali pulsanti `Modifica` e `Condividi` in header.
  * **Riutilizzo `TransactionsTable`**: Integrarlo nel tab Transazioni, passandogli i filtri adeguati (`broker_id` e range temporale `DateRangePicker`).
  * **Nuovi Componenti UI**:
    * Componente grafico "Growth 3-Lines" con ECharts.
    * Mappa Mondiale geografica (ECharts Map) per l'allocazione patrimoniale.
    * Modale "Dettaglio Lotti FIFO" con componente "Bubble Timeline" customizzato.
    * Integrazione del componente popover di selezione multipla (simile a quanto presente in `assets/`) per la selezione e deselezione rapida dei broker.
