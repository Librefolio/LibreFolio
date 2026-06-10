# Piano UI: Dettaglio Broker - Tab Posizioni (Holdings)

Questo documento descrive il wireframe ASCII per il tab "Posizioni", che include la tabella degli asset e l'overlay (modale) dei lotti FIFO.

## Tab Posizioni

```text
+-------------------------------------------------------------------------------------------------+
|  <- Torna ai Broker                                                                             |
|  [Icon] DIRECTA  (Ruolo: OWNER | Quota: 100%)                              [Share] [Sincronizza] |
+-------------------------------------------------------------------------------------------------+
|                                                                                                 |
|   [ PANORAMICA ]   [* POSIZIONI *]   [ TRANSAZIONI ]                                            |
|                                                                                                 |
|   +-----------------------------------------------------------------------------------------+   |
|   |  TABELLA POSIZIONI (DataTable)                                  [Cerca...] [Filtri v]   |   |
|   |  +------------+----------+-----------+---------------+-----------------+--------------+ |   |
|   |  | Asset      | Quantità | Costo Med.| Valore Att.   | P&L Non Realiz. | Allocazione  | |   |
|   |  +------------+----------+-----------+---------------+-----------------+--------------+ |   |
|   |  | (Icon) AAPL| 50       | USD 165,00| USD 5.463,00  | +USD 513 (+10%) | 15%          | |   |
|   |  | (Icon) VWCE| 120      | EUR 98,00 | EUR 14.500,00 | +EUR 450 (+4%)  | 45%          | |   |
|   |  +------------+----------+-----------+---------------+-----------------+--------------+ |   |
|   |                                                                                         |   |
|   |  ( Cliccando una riga si apre l'overlay dei Lotti FIFO sottostante )                    |   |
|   +-----------------------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------+
```

## Modale Overlay (Dettaglio Lotti FIFO)

All'apertura della modale viene mostrato un grafico a bolle per visualizzare visivamente lo stato dei lotti residui (Aperti), con interazione ("Goto & Pulse") per evidenziare le righe sottostanti corrispondenti.

```text
+-----------------------------------------------------------------------------+
|  DETTAGLIO TRANCHE / LOTTI (FIFO) — Apple (AAPL)                       [X]  |
+-----------------------------------------------------------------------------+
|                                                                             |
|   ANDAMENTO WAC E VALORE ASSET  [EUR | %]                                   |
|                                                                             |
|    EUR (o % se attivato)                                                    |
|    200 |                                            ****  <- Val. Mercato / TWRR %|
|        |                                        ****                        |
|    150 |       ---------------------------------          <- PMC / ROI %    |
|        |      /                                                             |
|    100 +-----+---------------------------------------------------------->   |
|         Gen   Feb   Mar   Apr   Mag   Giu   Lug   Ago                       |
|                                                                             |
|   +---------------------------------------------------------------------+   |
|                                                                             |
|   RENDIMENTO PER LOTTO DI ACQUISTO (Bubble Timeline)                        |
|                                                                             |
|    Gain (%)                                                                 |
|     +20% |             ( ) Lotto 1 (2026-01-10) — 30 / 100 quote residue    |
|          |            :   : (Il cerchio tratteggiato indica l'orig. 100)    |
|     +10% |                           ( ) Lotto 2 (2026-03-15) — 20 / 20     |
|       0% +------------------------------------------------------------->    |
|     -10% |                                                                  |
|                                                                             |
|   (Interazione: Cliccando una bolla la modale scorre giù alla tabella e fa  |
|    "pulse" sulla riga corrispondente).                                      |
|                                                                             |
|   +---------------------------------------------------------------------+   |
|   | LOTTI APERTI RESIDUI (FIFO)                                         |   |
|   +------------+----------+-----------+---------------+-----------------+   |
|   | Data Acq.  | Quantità | Prezzo    | Valore Att.   | P&L Non Realiz. |   |
|   +------------+----------+-----------+---------------+-----------------+   |
|   | 2026-01-10 | 30 / 100 | USD 165,00| USD 5.463,00  | +USD 513 (+10%) |   |
|   | 2026-03-15 | 20 / 20  | USD 180,00| USD 3.642,00  | +USD 42  (+1,1%)|   |
|   +------------+----------+-----------+---------------+-----------------+   |
|                                                                             |
|   +---------------------------------------------------------------------+   |
|   | LOTTI CHIUSI / VENDITE REALIZZATE (FIFO)                            |   |
|   +------------+------------+----------+--------------+-----------------+   |
|   | Data Acq.  | Data Vend. | Quantità | Prezzo Vend. | P&L Realizzato  |   |
|   +------------+------------+----------+--------------+-----------------+   |
|   | 2026-01-10 | 2026-05-20 | 70       | USD 175,00   | +USD 700,00     |   |
|   +------------+------------+----------+--------------+-----------------+   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## Requisiti Dati Frontend

Per renderizzare questo tab, il frontend necessita delle seguenti funzionalità:

### Funzionalità Esistenti (da riutilizzare o integrare):
* **Componente `<DataTable>` (TanStack Table)**: Esiste, supporta l'ordinamento e il filtering. Va solo configurato con le colonne specifiche per questo tab.
* **Modale Overlay / Slide-over**: Il wrapper dell'interfaccia modale esiste.

### Funzionalità da Sviluppare (Backend & API):
* **Lotti FIFO (`GET /api/v1/portfolio/lots`)**: Il backend deve restituire, filtrando per `broker_id` e `asset_id`, i dati FIFO:
  * `open_lots`: Array di acquisti non completamente venduti (con `original_qty`, `remaining_qty`, data, prezzo di carico e P&L % attuale).
  * `closed_lots`: Array di transazioni di vendita collegate agli acquisti originali (data acq., data vend., qty, prezzo vend., P&L realizzato).
* **Serie Storica WAC vs Prezzo (`GET /api/v1/portfolio/asset-history`)**: Serve una serie storica che affianchi il WAC dell'utente in ogni data al prezzo di chiusura di mercato. **(Audit Fix)**: Per evitare di fare l'overload dello schema di `GET /api/v1/portfolio/history` (che ritorna Liquidità/Investito/NAV), useremo un endpoint dedicato `asset-history`. Passando in input il `broker_id` e l'`asset_id`, questo nuovo endpoint restituirà `date`, `wac_value`, `market_price` e le metriche percentuali `roi` e `twrr`, per supportare lo switch `[EUR | %]`.
* **Componenti UI Nuovi**:
  * Grafico "Bubble Timeline" con interazione.
  * Grafico "Stacked Line" per WAC e Prezzo.
  * Logica "Goto & Pulse" tra i grafici ECharts e le righe della tabella.
