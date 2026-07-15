# Piano UI: Pagina Brokers & Dettaglio Broker

Questo documento descrive sia il wireframe della **Pagina Globale dei Broker** (lista di tutti i broker, inclusi quelli inaccessibili) sia il primo tab (Overview / Panoramica) della pagina di dettaglio del singolo broker.

## 1. Wireframe Pagina Globale Brokers (`/brokers`)

```text
+-------------------------------------------------------------------------------------------------+
|  I TUOI BROKER                                                                      [+ Nuovo]   |
|                                                                                                 |
|  +--------------------------+  +--------------------------+  +--------------------------+       |
|  | [Icon] DIRECTA           |  | [Icon] INTERACTIVE B.    |  | [Icon] TRADE REPUBLIC    |       |
|  | OWNER | Quota: 100%      |  | EDITOR | Quota: 50%      |  | OWNER | Quota: 100%      |       |
|  |--------------------------|  |--------------------------|  |--------------------------|       |
|  | NAV: EUR 48.200,00       |  | NAV: EUR 12.450,00       |  | NAV: EUR 5.000,00        |       |
|  | Gain: +EUR 3.120 (+6.9%) |  | Gain: -EUR 120 (-0.9%)   |  | Gain: +EUR 500 (+11.1%)  |       |
|  | Cassa: EUR 1.200,00      |  | Cassa: USD 2.500,00      |  | Cassa: EUR 500,00        |       |
|  |        USD 500,00        |  |        EUR 100,00        |  |                          |       |
|  |--------------------------|  |--------------------------|  |--------------------------|       |
|  | [Condividi]  [Vedi Dett.]|  | [Condividi]  [Vedi Dett.]|  | [Condividi]  [Vedi Dett.]|       |
|  +--------------------------+  +--------------------------+  +--------------------------+       |
|                                                                                                 |
|  ALTRI BROKER (Inaccessibili)                                                                   |
|                                                                                                 |
|  +--------------------------+  +--------------------------+                                     |
|  | [Icon] DEGIRO            |  | [Icon] FINECO            |                                     |
|  | Nessun Accesso           |  | Nessun Accesso           |                                     |
|  |                          |  |                          |                                     |
|  | [Richiedi Accesso]       |  | [Richiedi Accesso]       |  (Condividi in view-only)           |
|  +--------------------------+  +--------------------------+                                     |
+-------------------------------------------------------------------------------------------------+
```

---

## 2. Wireframe Dettaglio Broker - Tab Overview


```text
+-------------------------------------------------------------------------------------------------+
|  <- Torna ai Broker                                                                             |
|  [Icon] DIRECTA  (Ruolo: OWNER | Quota: 100%)                              [Share] [Sincronizza] |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|   [* PANORAMICA *]   [ POSIZIONI ]   [ TRANSAZIONI ]                                            |
|                                                                                                 |
|   +--------------------------+  +--------------------------+  +--------------------------+      |
|   | NAV BROKER               |  | GAIN/LOSS DEL BROKER     |  | ROI DEL BROKER           |      |
|   | EUR 48.200,00            |  | +EUR 3.120,00   (+6,9%)  |  | +7,45%                   |      |
|   +--------------------------+  +--------------------------+  +--------------------------+      |
|                                                                                                 |
|   +----------------------------------------------------+  +----------------------------------+  |
|   | GRAFICO DI CRESCITA                                |  | METADATI / INFO BROKER           |  |
|   | Range: [1W][1M][3M][6M][1Y][2Y][Custom]            |  | +------------------------------+ |  |
|   |                                                    |  | | Stato: Attivo                | |  |
|   |  EUR                                               |  | | Data Apertura: 2025-01-10    | |  |
|   |  60k +                                 ..*******   |  | | Leva Finanziaria: No         | |  |
|   |      |                             ..*******       |  | | Shorting Attivo: No          | |  |
|   |  40k |                         ..******* - - -     |  | | Plugin Import: directa_csv   | |  |
|   |      |                     ..*******               |  | +------------------------------+ |  |
|   |  20k |                 ..*******                   |  |                                  |  |
|   |      |............*****************................|  | +------------------------------+ |  |
|   |    0 +---*---*---*---*---*---*---*---*---*---*---> |  | | ALLOCAZIONE PATRIMONIALE     | |  |
|   |         Gen  Feb  Mar  Apr  May  Jun  Jul  Aug     |  | | [Tipo Asset] [Settore]       | |  |
|   |         [■] Valore Teorico Portafoglio             |  | |    ■ ETF     (80%)           | |  |
|   |         [- -] Capitale Investito (Titoli)          |  | |    ■ AZIONI  (20%)           | |  |
|   |         [....] Liquidità Libera (Cash)             |  | |                                | |  |
|   |                                                    |  | | ( ) MAPPA DEL MONDO          | |  |
|   |                                                    |  | | Mappa a calore basata sul    | |  |
|   |                                                    |  | | paese dell'asset (Unknown)   | |  |
|   +----------------------------------------------------+  +----------------------------------+  |
|                                                                                                 |
+-------------------------------------------------------------------------------------------------+
```

---

## Requisiti Dati Frontend

Per renderizzare questo tab, il frontend necessita delle seguenti funzionalità:

### Funzionalità Esistenti (da riutilizzare o integrare):
* **Componente ECharts per Grafici**: Esiste (usato in Dashboard e Assets), va parametrizzato per le 3 linee (Liquidità, Investito, NAV).
* **Modali Impostazioni e Condivisioni**: Esistono (apribili dai bottoni in alto).
* **`GET /api/v1/brokers/{id}`**: API esistente per reperire i metadati (Stato, Plugin, Data Apertura, ecc.).
* **`GET /api/v1/brokers/{id}/summary`**: API esistente per metriche parziali (verrà deprecata a favore dell'endpoint di portafoglio).

### Funzionalità da Sviluppare (Backend & API):
* **Riutilizzo `GET /api/v1/portfolio/summary`**: Il tab panoramica del singolo broker richiederà i dati chiamando l'endpoint di portafoglio passando l'ID del broker corrente. In questo modo si ottengono esattamente gli stessi dati (TWRR, MWRR, allocazioni, NAV) ricalcolati per il solo broker selezionato.
* **Riutilizzo `GET /api/v1/portfolio/history`**: Analogamente, il grafico storico a 3 linee verrà alimentato chiamando l'API `history` di portafoglio passando il parametro `broker_id`.
* **Componenti UI**: Si utilizzeranno gli stessi componenti creati per la Home Dashboard (KPI Cards, Growth 3-Lines, Mappe) renderizzandoli qui e passandogli in input il `broker_id`.
