# Piano UI: Dashboard Home

Questo documento contiene il wireframe ASCII per la vista generale della Dashboard Home, che aggrega i dati di più broker e mostra l'andamento complessivo del portafoglio.

## Wireframe Generale

Consente di filtrare per uno o più broker tramite un pannello a comparsa (popover a checklist, identico ai filtri della pagina Assets) e scegliere il range temporale desiderato.

```text
+-------------------------------------------------------------------------------------------------+
|  LibreFolio                                                                  [Avatar] Username  |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|   DASHBOARD HOME                                                                                |
|   [ Range: 1W | 1M | ... | Custom ]  [ Filtra Broker (3) v ]                   [↻ Sincronizza]  |
|                                                                                                 |
|   +--------------------------+  +--------------------------+  +--------------------------+      |
|   | NET WORTH COMPLESSIVO    |  | GAIN/LOSS DI PORTAFOGLIO |  | ROI PESATO (PMC/WAC)     |      |
|   | EUR 124.500,00           |  | +EUR 14.250,32  (+12,9%) |  | +11,45%                  |      |
|   | [Dettaglio per valuta]   |  | [Dettaglio per broker]   |  | TWRR: 12,1%  | MWRR: 11,2% |      |
|   +--------------------------+  +--------------------------+  +--------------------------+      |
|                                                                                                 |
|   +------------------------------------------------+  +--------------------------------------+  |
|   | ANDAMENTO DEL PORTAFOGLIO (GROWTH)  [EUR | % ] |  | ALLOCAZIONE PATRIMONIALE             |  |
|   |                                                |  | [Tipo Asset] [Settore] [Geografica]  |  |
|   |  EUR (o Percentuale se vista %)                |  |                                      |  |
|   |  150k +                                 ..**   |  |         _.._   [■] ETF     (45%)     |  |
|   |       |                             ..**       |  |       .'    '. [■] AZIONI  (30%)     |  |
|   |  100k |                         ..** - - -     |  |      /  (•)   \ [■] CRYPTO  (15%)     |  |
|   |       |                     ..**               |  |     |   NAV   | [■] LIQUID. (10%)     |  |
|   |   50k |                 ..**                   |  |      \       /                       |  |
|   |       |             ..**                       |  |       '.__..'                        |  |
|   |     0 +---*---*---*---*---*---*---*---*---*--->|  |  ( ) MAPPA DEL MONDO                 |  |
|   |         Gen Feb Mar Apr Mag Giu Lug Ago Set    |  |  Mappa a calore basata sul paese     |  |
|   |         [■] Valore NAV / MWRR                  |  |  dell'asset, con 'Unknown' separato  |  |
|   |         [- -] Capitale Invest. / TWRR          |  |                                      |  |
|   |         [....] Liquidità / ROI Semplice        |  |                                      |  |
|   +------------------------------------------------+  +--------------------------------------+  |
|                                                                                                 |
|   +-----------------------------------------+  +---------------------------------------------+  |
|   | LE TUE POSIZIONI (ASSET)                |  | ULTIME TRANSAZIONI                          |  |
|   | Asset         Prezzo   Valore     Gain  |  | Data  Tipo   Asset   Broker   Importo       |  |
|   | [Ic] AAPL     $291     $1.200     +67%  |  | 09-06 BUY    AAPL    IBKR     € -250,00     |  |
|   | [Ic] VWCE     €114     €5.400     +12%  |  |                               +1 AAPL       |  |
|   |                                         |  | 08-06 DEP    --      Directa  € +1.000,00   |  |
|   | Vedi Tutti ->                           |  | Vedi Tutte ->                               |  |
|   +-----------------------------------------+  +---------------------------------------------+  |
|   *In modalità Mobile, il blocco "Transazioni" scivolerà automaticamente sotto agli "Asset"*    |
+-------------------------------------------------------------------------------------------------+
```

---

## Requisiti Dati Frontend

Per renderizzare questa schermata, il frontend necessita delle seguenti funzionalità:

### Funzionalità Esistenti (da riutilizzare o integrare):
* **Componente `DateRangePicker`**: Esiste (usato in `assets/` e `forex/`).
* **Filtro Multi-selettore Broker**: Esiste concettualmente (popover a checklist simile a quello degli asset), va applicato al contesto Broker.
* **Componente `<TransactionsTable>`**: Esiste ed è completo, va montato in fondo alla pagina passando la prop per nascondere paginazione/filtri avanzati (solo modalità "Ultime righe").

### Funzionalità da Sviluppare (Frontend State Management):
* **`portfolioStore.ts`**: Store globale di caching (Svelte Store) che trattiene l'ultimo JSON di `summary` e `history` per evitare che la navigazione tra le pagine della dashboard e dei broker continui a innescare il ricalcolo backend. Include metodi per invalidare la cache (su CRUD transazioni) e il refresh forzato tramite il pulsante `[↻ Sincronizza]`.

### Funzionalità da Sviluppare (Backend & API):
* **`GET /api/v1/portfolio/summary`**: Endpoint che restituisce (filtrando per `broker_id` opzionali):
  * KPI totali: `net_worth`, `total_gain_loss` (assoluto e %), `cash_total`.
  * Metriche ROI: `twrr_percent` e `mwrr_percent`.
  * Dati aggregati per le 3 allocazioni: `allocation_by_type`, `allocation_by_sector`, `allocation_by_geography`.
  * **Breakdown per Broker (Opzionale)**: Supporta il query parameter `?include_breakdown=true` (default `false`). Se attivo, include un array `by_broker: [{broker_id, net_worth, ...}]` per fornire agilmente i saldi alla pagina "Global Brokers" senza fare chiamate multiple, eseguendo i calcoli N+1 in memoria (super-veloce) dopo un solo fetch I/O.
* **`GET /api/v1/portfolio/history`**: Endpoint che restituisce (filtrando per `broker_id` opzionali e `date_range`):
  * Serie storica aggregata giornaliera: `date`, `cash_value`, `invested_value`, `nav_value` (per la vista EUR).
  * Serie storica percentuale: `twrr`, `mwrr`, `roi` (per la vista % attivabile dal toggle `[EUR | %]`).

*Nota*: le formule matematiche core (TWRR, MWRR) dovranno essere calcolate in backend (all'interno di `roi_utils.py` orchestrato da `portfolio_service.py`) per garantire consistenza dei dati.
