# FIFO Engine v3 — Reference di sistema (stato corrente)

> **Scopo.** Descrizione ad alto livello, *completa e leggibile*, dell'intero sottosistema
> "analisi lotti FIFO" così com'è **oggi** (dopo i round di rifinitura 1–8 di luglio 2026):
> motore backend, strato di servizio, contratto DTO, formule matematiche, interfacce grafiche
> (con ASCII art) e modalità d'uso. Serve per **revisionare il lavoro**, decidere i prossimi
> passi e scrivere la documentazione utente aggiornata.
>
> **Come si colloca fra gli altri report v3** (stessa cartella):
> - [`highLevel-v3.md`](highLevel-v3.md) — la *specifica* originale (§1–18): cosa costruire.
> - [`implementation-log-v3.md`](implementation-log-v3.md) — il *diario* di implementazione (Wave 0–2).
> - [`final-report-v3.md`](final-report-v3.md) — il *report finale* del piano (diagnosi/decisioni/formule/test).
> - [`state-recap-v3.md`](state-recap-v3.md) — snapshot ultra-sintetico per il supervisore.
> - **Questo file** — la *reference di sistema*: la fotografia dello stato corrente, orientata
>   a chi deve capire "come funziona e come si usa", non "cosa è stato deciso passo-passo".
>
> Fonte di verità resta il **codice**. Se una formula qui diverge dal codice, vince il codice.

---

## 1. Architettura a colpo d'occhio

Un unico flusso, tre strati. Tutto il calcolo finanziario è nel backend; il frontend
seleziona/filtra/aggrega-visivamente/renderizza.

```text
  TRANSAZIONI (DB)                                       BROWSER
  ┌──────────────┐    ┌───────────────────────┐    ┌──────────────────────────┐
  │ transactions │    │  FifoLotEngine (puro)  │    │  LotsAnalysisPanel        │
  │ price_history│──▶ │  event-sourced:        │──▶ │  ├─ LotWacPriceChart      │
  │ fx rates     │    │  BUY/SELL/ADJ/TRANSFER │    │  ├─ LotGanttChart         │
  │ assets(qbq)  │    │  /SPLIT → lotti,       │    │  ├─ UnifiedLotsTable      │
  └──────────────┘    │  frammenti, closures   │    │  ├─ LotComparisonChart    │
                      └───────────┬───────────┘    │  └─ LotCustodyModal        │
                                  │                 └──────────────────────────┘
                      ┌───────────▼────────────┐              ▲
                      │  LotsAnalysisService    │   POST /portfolio/lots/analysis
                      │  - FX in target_ccy     │   (requested_analyses = sezioni)
                      │  - qbq scaling          │──────────────┘
                      │  - income allocation    │   LotsAnalysisResponse (DTO)
                      │  - estimated-at-cost     │
                      │  - continuità chiusura  │
                      │  - history builders     │
                      └─────────────────────────┘
```

- **Motore** (`backend/app/services/fifo_lot_engine.py`): matematica FIFO pura, senza I/O,
  senza valuta target, senza prezzi correnti. Produce lotti, frammenti di custodia, chiusure.
- **Servizio** (`backend/app/services/lots_analysis_service.py`): orchestrazione. Carica dati,
  esegue il motore, converte in `target_currency`, applica `quote_base_quantity`, alloca i
  proventi, gestisce il prezzo mancante ("estimated at cost"), costruisce tutte le history,
  serializza nel DTO. È il **punto in cui vivono le metriche di presentazione**.
- **Contratto** (`backend/app/schemas/portfolio.py`): `LotsAnalysisResponse`. Ogni sezione è
  `None` se non richiesta via `requested_analyses`.
- **Frontend** (`frontend/src/lib/components/brokers/lots/*`): il pannello e i suoi 5 figli.

Endpoint unico: `POST /portfolio/lots/analysis`. Il body richiede `asset_id`, opzionali
`broker_ids`, `date_range`, `target_currency`, `selected_lot_ids`, e la lista non vuota
`requested_analyses` (enum `LotAnalysisType`).

---

## 2. Il motore FIFO (event-sourced)

Il motore trasforma una sequenza di transazioni in **lotti** con FIFO cost-matching e in
**frammenti** che tracciano *dove* (broker/transito) vive ciascuna porzione di lotto nel tempo.

### 2.1 Entità

| Entità | Cos'è |
|---|---|
| `FifoEvent` | Evento normalizzato: `BUY`, `SELL`, `ADJUSTMENT_IN/OUT`, `SPLIT`, `TRANSFER_DEPART/ARRIVE`. |
| `FifoLot` | Un lotto = un'apertura (BUY / ADJ+ / TRANSFER-in che origina il lotto). `lot_id == opening_transaction_id`. Tiene `original_quantity`, `opening_unit_price`, `original_cost`, `open_quantity`, `realized_quantity`, `realized_pnl`, `cumulative_proceeds`, `reference_unit_price`. |
| `FragmentInterval` | Una "corsia" di custodia: quantità omogenea di un lotto presso un broker (`BROKER`) o in trasferimento (`IN_TRANSIT`), con `start_date`/`end_date` (None = ancora attivo). È ciò che disegna il Gantt. |
| `LotClosure` | Una chiusura FIFO (SELL / ADJ− / eventuale BUY che chiude uno SHORT): quantità, `open_unit_price`, `close_unit_price`, `realized_pnl`, `proceeds`, `close_date`. |
| `FifoEngineResult` | Contenitore: lotti + frammenti + closures + issues + `calculation_status` (COMPLETE/DEGRADED). |

### 2.2 Regole di prezzo unitario e apertura

```text
_unit_price(amount, qty) = |amount| / |qty|
opening_unit_price       = original_cost / original_quantity        (per singola unità)
```

`opening_unit_price` e `original_cost` sono **per-unità-singola** (costo diviso quantità grezza).
Nota bene: **non** sono espressi per `quote_base_quantity`. Questo è il nodo della "convenzione a
due scale" (→ §5.7).

### 2.3 Custodia: frammenti, transito, transfer, split

- Un **BUY** apre un lotto e crea un frammento `BROKER` presso il broker d'acquisto.
- Un **TRANSFER** consuma frammenti dal broker sorgente in ordine FIFO, li mette `IN_TRANSIT`
  (`TRANSFER_DEPART`), poi li riapre come `BROKER` presso la destinazione (`TRANSFER_ARRIVE`).
  Il **costo del lotto non cambia**: un transfer non è una vendita, non realizza P&L.
- Uno **SPLIT** trasforma i frammenti in scope moltiplicando la quantità e dividendo il prezzo
  per il ratio, mantenendo invariato il costo (`q·p₀ = const`, con tolleranza `0.01` per il
  troncamento decimale su ratio non interi come 3:1).
- Un **ADJUSTMENT+** apre un lotto (o incrementa), un **ADJUSTMENT−** chiude in FIFO come una SELL
  ma senza incasso di mercato reale.
- Uno **stato lotto** (`get_lot_states`) è un insieme combinabile: `LONG`/`SHORT` + uno di
  `OPEN`/`PARTIALLY_CLOSED`/`CLOSED` + eventuali `IN_TRANSIT`, `DISTRIBUTED` (più custodie),
  `DEGRADED` (issue sul lotto).

### 2.4 Reference price (prezzo di riferimento del lotto)

Alla data di apertura, il motore cerca in `price_history` il prezzo di mercato "at-or-before"
(`_resolve_reference_price`) e lo salva in `lot.reference_unit_price` con
`reference_price_source ∈ {exact, fallback, unavailable}`. Serve al calcolo dell'**Open Return**
(→ §5.6). Se non esiste alcuna quotazione a quella data (es. **BTP comprato all'emissione**,
prima che iniziasse a trattare), `reference_unit_price = None` e il servizio ricadrà sul prezzo
d'acquisto del lotto (con lo scaling qbq, → §5.7).

### 2.5 Valutazione nel motore (senza qbq)

`value_for_lot(lot, market_price)` produce (LONG):
```text
open_value  = open_quantity · market_price
proceeds    = cumulative_proceeds
total_value = open_value + proceeds
pnl         = total_value − original_cost
```
⚠️ Questa valutazione "grezza" del motore **non applica** `quote_base_quantity`. Per i bond è
il **servizio** a rifare il calcolo con `compute_holding_value` (→ §5.2). Il metodo
`relative_return_for_lot` del motore esiste ma **non è usato in produzione**: la `relative_return`
la calcola il servizio (→ §5.6), che è l'unico posto dove qbq/FX sono corretti.

---

## 3. Lo strato di servizio (`LotsAnalysisService`)

Punto d'ingresso: `get_lots_analysis(user_id, asset_id, broker_ids, date_from, date_to,
target_currency, selected_lot_ids, requested_analyses)`. Responsabilità principali:

1. **Load** transazioni dell'asset (in scope broker), `price_history`, `quote_base_quantity`
   dell'asset. Carica **a parte** i DIVIDEND/INTEREST con `asset_id` (non entrano nel motore FIFO,
   che ignora le transazioni a quantità nulla).
2. **Esegue il motore** → lotti, frammenti, closures.
3. **FX**: `_FxRateResolver` converte ogni importo in `target_currency` alla data corretta
   (apertura, chiusura, data provento). I prezzi di `price_history` sono già in valuta asset e
   vengono convertiti dove serve.
4. **Range**: l'inizio calcolo è `min(tx.date)` dell'asset; `date_from` limita solo *quali punti
   history* vengono emessi, non lo stato iniziale.
5. **Costruisce** solo le sezioni richieste (`requested_analyses`) e serializza il DTO.

### 3.1 Allocazione dei proventi asset-linked (`_allocate_asset_income`)

DIVIDEND/INTEREST con `asset_id` vengono distribuiti **pro-rata sui lotti LONG aperti** alla data
del provento. Peso per lotto:
```text
w_i(t) = open_qty_i(t) / Σ_j open_qty_j(t)      (solo lotti LONG aperti a t)
Income_i = convert(I, ccy, t) · w_i(t)
```
La somma delle allocazioni è **esattamente** l'importo convertito (running-remainder: l'ultimo
lotto in ordine deterministico assorbe il residuo di divisione — nessun valore creato o perso). Se
nessun LONG è aperto a quella data, il provento è saltato qui (è un effetto broker-level gestito
dal Portfolio Engine). Ritorna: income cumulato per lotto, prefix cumulativo per-data (per le
history) e la lista `income_events` (un elemento per transazione allocata → marker "|" sui grafici).

### 3.2 Prezzo corrente mancante — "estimated at cost"

Se **non esiste** alcun prezzo di mercato per l'asset (`latest_market_price is None`) e il lotto è
LONG con quantità originale ≠ 0:
```text
value_source = ESTIMATED_AT_COST
open_value   = opening_value · open_quantity / original_quantity     (valore residuo al costo)
market_pnl   = 0                                                     (nessun P&L di prezzo)
```
Così crowdfunding/asset senza quotazione mostrano comunque valore residuo, proventi e
`total_return`. Altrimenti `value_source = MARKET_PRICE`.

### 3.3 Continuità dopo la chiusura completa (fix §1 del piano)

`_lot_history_end_date(..., extend_closed=True)` fa sì che le history di **valore** e **rendimento**
proseguano fino a `date_to` anche per lotti totalmente chiusi (prima troncavano alla data di
vendita). Nei giorni successivi alla chiusura, con `open_quantity == 0`, il punto è emesso **senza
prezzo di mercato**:
```text
open_value  = 0
proceeds    = cristallizzato (prefix alla data)
total_value = proceeds (+ income)
pnl         = total_value − original_cost      (cristallizzato)
total_return = (total_value + income)/original_cost − 1   (cristallizzato)
```
Risultato: la vendita completa azzera l'esposizione al mercato ma **non** il risultato economico,
che resta piatto fino a `date_to`. (La `price_history` per-lotto invece continua a troncare alla
chiusura: è corretto, dopo la chiusura non c'è più prezzo del lotto da mostrare.)

---

## 4. Formule (riepilogo unico)

Notazione: `t` = data; `L` = insieme dei lotti graficati; importi in `target_currency`.

### 4.1 Costo e apertura
```text
opening_unit_price = original_cost / original_quantity
opening_value      = original_cost                       (base per i "return")
```

### 4.2 Valore di mercato con quote_base_quantity  (chiave per i bond)
```text
compute_holding_value(qty, raw_price, qbq) = (qty / qbq) · raw_price
open_value(t) = (open_quantity(t) / qbq) · market_price(t)
```
`qbq` = `quote_base_quantity` dell'asset (es. 100 per un BTP quotato "per 100 nominale", 1 per
un'azione). `price_history.close` è quotato **per qbq**; le quantità sono nominali.

### 4.3 P&L (LONG)
```text
proceeds(t)     = Σ closure.proceeds  fino a t          (incassi da vendite, NO dividendi)
total_value(t)  = open_value(t) + proceeds(t)
pnl(t)          = total_value(t) − original_cost
market_pnl      = pnl − realized_pnl                    (= 0 se ESTIMATED_AT_COST)
realized_pnl    = Σ closure.realized_pnl
total_pnl       = market_pnl + realized_pnl + asset_income
```
(SHORT: `total_value = proceeds − open_value`, `pnl = total_value`.)

### 4.4 Proventi e rendimenti scalari (riga tabella / tooltip)
```text
asset_income = Σ_t Income_i(t)                           (dividendi+interessi allocati al lotto)
cash_yield   = asset_income / opening_value              (se opening_value > 0)
total_return = total_pnl / opening_value                 (se opening_value > 0)
```

### 4.5 Rendimento nelle history (per-lotto, per-data)
```text
total_return(t) = (total_value(t) + income(t)) / original_cost − 1
```

### 4.6 Open Return (`relative_return`) — rendimento vs prezzo di riferimento
```text
relative_return = market_price / reference_unit_price − 1
```
È il rendimento del **solo prezzo** rispetto alla quotazione di apertura del lotto. Due scenari
per `reference_unit_price` (→ §5.7 per la scala):
- **Scenario A** — alla data di apertura *esiste* una quotazione → reference = prezzo di mercato di
  apertura (già per-qbq). Nessuno scaling.
- **Scenario B** — apertura *precede* la prima quotazione (bond all'emissione) → reference =
  `opening_unit_price · qbq` (prezzo d'acquisto riportato sull'asse di mercato).

### 4.7 Rendimento aggregato (calcolato nel frontend, `LotComparisonChart`)
Non si sommano le percentuali. Per ogni data, sui lotti graficati aperti a `t`:
```text
AggregatePnL(t)          = Σ_i (pnl_i(t) + income_i(t))
AggregateOpeningValue(t) = Σ_i original_cost_i
AggregateReturn(t)       = AggregatePnL(t) / AggregateOpeningValue(t)      (se denom > 0)
```
Un lotto in perdita riduce correttamente l'aggregato. Se il denominatore ≤ 0 il punto è escluso.

---

## 5. Convenzioni critiche e "gotcha" (leggere prima di toccare il codice)

### 5.1 Tutto il calcolo è backend
Il frontend non calcola metriche finanziarie: normalizza per la vista (%), aggrega visualmente
(area aggregata) e disegna. Gli aggregati Valore/Rendimento sono somme di serie già pronte.

### 5.2 La convenzione a due scale (qbq) — causa storica di 3 bug
- `price_history.close` è **per qbq** (bond quotati per 100).
- `opening_unit_price` e `wac` sono **per-unità-singola** (`costo/quantità`).
- Per riconciliarli sull'asse di mercato si **moltiplica per qbq** il prezzo per-unità-singola.
- Valutazione: `open_value = (qty/qbq)·price` (`compute_holding_value`).

Questa convenzione ha morso tre volte: P&L >9000% (round-6, risolto), bolla ABS mal posizionata
(round-8, risolto invertendo ÷→×), `relative_return` a 9687% (risolto: scaling `×qbq` **solo** sul
ramo di fallback dello scenario B; un `×qbq` indiscriminato romperebbe lo scenario A).

### 5.3 Invarianza in modalità %
`toPercentSeries` normalizza ogni serie al suo primo valore ⇒ moltiplicare un'intera serie per una
costante (qbq) **si cancella**. Lo scaling qbq influisce solo sulla modalità ABS: corretto.

### 5.4 Reattività al refresh (F5)
`getAssetInfo()` è una funzione non reattiva allo store asset (che carica in modo asincrono). Al
F5, `activeAssetId` (dall'URL) arriva prima del caricamento dello store ⇒ titolo/valuta restavano
stale ("nome perso dopo il trattino"). Fix: derivare attraverso `$assetStoreVersion` per forzare il
ricalcolo quando la cache è pronta (dashboard con runes; pagina broker con `$:` legacy).

### 5.5 DTO backend ≠ vista frontend
Alcune sezioni DTO (es. `price_history`, `performance_history` ROI/TWRR) **restano nel contratto**
anche se una vista non le mostra più: potrebbero servire ad altre funzioni. Non rimuovere metriche
backend solo perché un grafico le ha tolte.

---

## 6. Il contratto DTO (`LotsAnalysisResponse`)

Sezioni (una per `LotAnalysisType`), tutte `None` se non richieste:

| Sezione (enum) | Campo response | Contenuto |
|---|---|---|
| `LOT_SUMMARY` | `lots[]` | Riga per lotto: metriche scalari (open/total value, pnl, market_pnl, realized_pnl, total_pnl, asset_income, cash_yield, total_return, relative_return, value_source, states, custody). |
| `GANTT_TOPOLOGY` | `gantt_segments[]` | Frammenti di custodia (lane del Gantt). |
| `CUSTODY_HISTORY` | `custody_history[]` | Timeline eventi di custodia (transfer). |
| `EVENT_HISTORY` | `lot_events[]` | Timeline eventi lotto (BUY/SELL/ADJ/SPLIT/TRANSFER). |
| `VALUE_HISTORY` | `value_history[]` | Punti per-lotto: open_value, proceeds, total_value, original_cost, pnl, income. |
| `RETURN_HISTORY` | `return_history[]` | Punti per-lotto: total_return, relative_return, income. |
| `PRICE_HISTORY` | `price_history[]` | Prezzo di mercato per-lotto (tronca a chiusura). |
| `BROKER_WAC_HISTORY` | `broker_wac_history[]` | WAC per broker nel tempo. |
| `CUMULATIVE_WAC_HISTORY` | `cumulative_wac_history[]` | WAC combinato (PMC). |
| `PERFORMANCE_HISTORY` | `performance_history[]` | ROI/TWRR asset-wide (ignora `selected_lot_ids`). |
| `INCOME_EVENTS` | `income_events[]` | DIVIDEND/INTEREST allocati → marker "\|". |

Campo top-level chiave: `quote_base_quantity` (default 1) — permette al frontend di riscalare i
prezzi per-unità sull'asse di mercato. Più `calculation_status`, `calculation_metadata` (range
calcolati/richiesti, selezione), `data_quality` (issue i18n).

**Nota — due richieste distinte**. Il pannello fa **due** POST allo stesso endpoint:
1. **Carico principale** (al cambio asset/range): `LOT_SUMMARY, GANTT_TOPOLOGY, EVENT_HISTORY,
   PRICE_HISTORY, BROKER_WAC_HISTORY, CUMULATIVE_WAC_HISTORY, INCOME_EVENTS`.
2. **Fetch di selezione** (al cambio della selezione effettiva): `VALUE_HISTORY, RETURN_HISTORY`
   *scoped* al set di lotti effettivo (selezione vuota ⇒ tutti i visibili) — alimenta il Blocco 3.

`PERFORMANCE_HISTORY` (ROI/TWRR) non è più richiesto dalla UI (rimosso dal 1° grafico) ma resta
disponibile nel backend.

---

## 7. Le interfacce grafiche (stato corrente)

Il pannello `LotsAnalysisPanel` rende, in quest'ordine: **banner data-quality → Blocco 1
(PMC/Prezzo) → Blocco 2 (Vita e custodia / Gantt) → Tabella lotti → Blocco 3 (Valore/Rendimento) →
Modale dettaglio**. Selezione condivisa fra tutti: **selezione vuota = "tutti i lotti visibili"**;
filtro **Aperti|Chiusi** a 3 vie (entrambi on o entrambi off = tutti).

### 7.1 Blocco 1 — `LotWacPriceChart` · "PMC / Prezzo di mercato"

Relazione prezzo ↔ PMC ↔ operazioni. Toggle in alto a destra: **[Auto | Da 0]** (solo in ABS) e
**[ABS | %]**.

```text
 PMC / Prezzo di mercato                              [Auto|Da 0]  [ABS | %]
 €                                             ● bolla performance lotto (centro = stato)
 102 ┤            ╱‾‾market price‾‾╲        ╱‾‾           colore = broker
 100 ┤      ▲BUY ╱      ┈┈┈PMC cumulato┈┈┈╱      ◆TRANSFER
  98 ┤────╱────────── WAC broker A ───────────────  ▼SELL
  96 ┤   │ (connettore tratteggiato costo→bolla)     │ marker provento (viola)
     └───┴───────────────────────────────────────────────────────▶ tempo
   marker eventi: ▲BUY  ▼SELL  ◆TRANSFER  +ADJ+  ×ADJ−  │SPLIT
```

- **Serie**: linee WAC per broker, WAC cumulato (PMC), linea prezzo di mercato, marker evento
  (BUY/SELL/TRANSFER/ADJ±/SPLIT), **bolle performance** per lotto con puntino di stato al centro
  (colore = stato aperto/parziale/chiuso), connettori tratteggiati costo→bolla, marker proventi "|".
- **Scaling qbq**: `scaleUnitPrice(v) = v·qbq` applicato a WAC broker, WAC cumulato, `opening_unit_price`
  e baseY della bolla, così tutte le serie di prezzo condividono l'asse di mercato (par ~100 per i
  bond; no-op per qbq=1). In % la costante si cancella.
- **% mode**: ogni serie normalizzata al primo valore; **asse 0% evidenziato**; la bolla usa
  `total_return×100`. I connettori bolla sono esclusi dalla legenda.
- **Tooltip bolla**: data/valore apertura, P&L complessivo, rendimento totale, proventi, stato,
  avviso "⚠ Stimato al costo" se applicabile. **Tooltip marker**: specifico per evento (BUY:
  quantità/prezzo/valore apertura/broker; SELL: quantità venduta/residua/prezzo/incasso/P&L
  realizzato; TRANSFER: da→a/quantità/intervallo; SPLIT: quantità e prezzo prima/dopo, costo
  invariato; ADJ: tipo/quantità/effetto).
- **Rimosso** in v3: ROI e TWRR (affollavano la modalità %).

### 7.2 Blocco 2 — `LotGanttChart` · "Vita e custodia dei lotti"

Topologia di custodia nel tempo: ogni lotto è una barra; i transfer generano lane figlie.

```text
 Vita e custodia dei lotti                                    [Aperti | Chiusi]
 Lotto #1 (Directa) ▲■■■■■■■■■■■■■■■■■■■■■■■■■■▼           barra = vita del lotto
 Lotto #2 (Directa) ▲■■■■■■■■┐                              spessore ∝ quantità
                            └─L→ ■■■■■■■■ (IBKR)            L/elbow = transfer → lane figlia
 ├────────────────────── asse tempo sticky ──────────────────────▶
```

- **Lane** come custom series ECharts; lane figlia nasce solo alla biforcazione (transfer),
  connessa da un **connettore a L (elbow)** genitore→figlia. Asse tempo **sticky** in fondo
  (condivide range/zoom col grafico sopra).
- **Marker eventi** sulla vita di ogni lotto; lo spessore cambia dopo l'evento.
- **Tooltip sintetico** (varianti aperto/chiuso): data apertura, broker, direzione, stato,
  quote aperte/originarie, valore corrente, proventi, P&L complessivo, rendimento totale; valore
  stimato mostra "⚠ Stimato al costo" in ambra. Il dettaglio completo è nella modale.
- **Mobile**: il tap mostra il tooltip e seleziona; il re-render della selezione riafferma il
  tooltip.
- **Infobox** ("Vita e custodia dei lotti"): P&L e rendita colorati **verde se positivi / rosso se
  negativi**; su mobile il box è centrato sul dito e traslato in alto.

### 7.3 Tabella — `UnifiedLotsTable`

`DataTable` con colonna azioni a **kebab (⋮)** (default del progetto per le tabelle con azioni).

```text
 ┌ Data ap. ┬ P&L tot ┬ Rend.tot ┬ Proventi ┬ Val.corr ┬ Q.aperta ┬ Custodia ┬ Stato ┬ ⋮ ┐
 │ 17/02/25 │ +15,50  │ +13,74%  │  +4,20   │  64,40   │    2     │ Directa  │ Aperto│ ⋮ │
 ├──────────┼─────────┼──────────┼──────────┼──────────┼──────────┴──────────┴───────┴───┤
 │  Totali  │  Σ P&L  │  media⌀  │  Σ prov  │  Σ valore│  Σ quantità  (footer aggregato)  │
 └──────────┴─────────┴──────────┴──────────┴──────────┴──────────────────────────────────┘
```

- **Colonne default**: data apertura, P&L totale, rendimento totale, proventi (income), valore
  corrente, quantità aperta, custodia, stato. **Nascoste di default**: prezzo/valore d'apertura,
  quantità originaria, **Open Return** (`relative_return`), direzione.
- **Footer aggregato**: somme (P&L, income, valore, quantità) e medie ponderate (prezzo apertura,
  open return) su selezionate se presenti, altrimenti visibili.
- **Azioni riga** (kebab): dettaglio, vai al Gantt, vai alla transazione di apertura, copia lot id.
- **Selezione** sincronizzata con tutti i grafici e potata alle righe visibili.

### 7.4 Blocco 3 — `LotComparisonChart` · "Valore / Rendimento dei lotti"

Toggle sempre presente **[Valore | Rendimento]** (a destra). In **Valore** compare anche
**[Auto | Da 0]** per l'asse Y.

**Modalità Valore** — *solo aggregato* (nessuna linea per-lotto, nessun toggle Aggregato/Per-lotto):
```text
 Valore dei lotti selezionati            [Auto|Da 0]  [Valore | Rendimento]
 € ┤                                   ╭──── Valore complessivo (linea, sopra tutto)
   ┤                         ░░░░░░░░░╯     Proventi cumulati
   ┤                   █████████████████    Incassi da vendite (solo proceeds, NO dividendi)
   ┤             ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓        Valore residuo (stimato al costo se senza prezzo)
   ┼──────── Valore di apertura ───────────────────────────────
 0 ┼─────────────────────────────────────────────────────────▶ tempo
```
Serie: Valore residuo / Incassi da vendite / Proventi cumulati / Valore complessivo / Valore di
apertura. La linea blu "Valore complessivo" è disegnata **sopra** le aree (evita sovrapposizioni
quando gli incassi sono 0). Marker provento "|" sulla linea complessiva.

**Modalità Rendimento** — *solo ABS*, linee individuali + **area aggregata**:
```text
 Rendimento dei lotti                                 [Valore | Rendimento]
 +30% ┤                           ───── Lotto A 2025
 +20% ┤                  ────────────── Lotto C 2025
 +15% ┤             ╭█████████████████  Rendimento aggregato (area + bordo)
   0% ┼─────────────┴──────────────────────────────  (0 evidenziato)
 -10% ┤       ───── Lotto negativo
```
- **≥2 lotti**: linee individuali + area aggregata semitrasparente con bordo.
- **1 solo lotto**: mostra **l'area aggregata** (non la linea nuda), così si vede l'area e si
  evidenzia lo 0 (richiesta round-8). Nomi lotto includono **l'anno** (es. "Lotto A 2025").
- **Rimosso** in v3: modalità Prezzo, ROI/TWRR, e la versione % del Rendimento (il rendimento
  aggregato in % non era la somma delle componenti → si è tenuto solo l'ABS).

### 7.5 Modale — `LotCustodyModal`

Dettaglio completo per lotto (più ricca del tooltip Gantt): direzione, quantità
originaria/aperta, prezzo/valore apertura, valore corrente (con nota "estimated at cost"),
proventi cumulati, asset income, market P&L, FIFO (realized) P&L, total P&L, Open Return, total
return, cash yield, stati; più la **timeline cronologica** cliccabile (prezzo apertura/chiusura,
proceeds, realized P&L, ratio split, sorgente/destinazione transfer) con "vai alla transazione".

---

## 8. Come si usa (percorsi utente)

1. **Aprire il pannello**: dashboard `?tab=posizioni&asset=<id>` (o pagina broker) → il pannello
   carica l'analisi dell'asset.
2. **Filtrare i lotti**: bottoni **Aperti|Chiusi** (3 vie). Nessuna selezione esplicita ⇒ tutti i
   visibili sono graficati.
3. **Selezionare lotti**: click nella tabella / sulle barre Gantt / sulle bolle → la selezione
   restringe il Blocco 3 (Valore/Rendimento) e resta sincronizzata ovunque.
4. **Blocco 1** — leggere prezzo vs PMC, gli eventi (marker) e le bolle di performance; alternare
   **ABS/%** e, in ABS, **Auto/Da 0** per l'asse.
5. **Blocco 2** — capire *dove* vive ogni lotto (broker, transito, transfer con lane figlie) e la
   sua vita; hover/tap per il tooltip sintetico; kebab per il dettaglio.
6. **Blocco 3** — **Valore** per il valore economico aggregato (residuo + incassi + proventi);
   **Rendimento** per il confronto dei rendimenti con l'aggregato ponderato.
7. **Modale** — dettaglio completo del lotto + timeline; "vai alla transazione" apre la transazione
   di apertura in vista.

---

## 9. Stato qualità del codice (per la revisione)

### 9.1 Punti solidi
- **Separazione netta** motore puro / servizio / DTO / frontend: il motore FIFO non conosce FX,
  qbq, prezzi correnti — testabile in isolamento.
- **Conservazione del valore** nell'allocazione proventi (running-remainder) e nell'invariante di
  costo dello split (con tolleranza motivata).
- **Metriche di presentazione centralizzate** nel servizio: un solo posto dove FX+qbq sono
  applicati correttamente (il `relative_return_for_lot` del motore, non-usato, evita di essere una
  seconda sorgente di verità sbagliata).
- **Regressioni coperte**: test dedicati per qbq (scenario A con prezzo all'apertura, scenario B
  bond all'emissione), continuità post-chiusura, cristallizzazione incassi/proventi.

### 9.2 Duplicazioni fattorizzabili (candidati a refactor)
- **`_build_value_history` e `_build_return_history`** condividono ~l'80% della logica (stesso loop
  date, stesso ramo `market_price is None` con `open_qty==0` / estimated, stesso `_value_snapshot_on_date`).
  Fattorizzabile in un unico builder che produce entrambe le serie (o un helper che emette
  `(open_value, proceeds, total_value, pnl, income)` per data, consumato da entrambi).
- **Rami LONG/SHORT ripetuti** (`total_value`/`pnl`) compaiono in `value_for_lot`,
  `_value_snapshot_on_date` e nei due builder history. Un unico helper `lot_pnl(direction, open_value,
  proceeds, cost)` toglierebbe la ripetizione.
- **Aggregazione frontend**: `aggregatedValuePoints` e `aggregateReturnPoints` iterano entrambe le
  history per data con la stessa struttura Map<date,…>; un solo pass potrebbe produrre entrambe.
- **Marker "|" proventi**: logica quasi identica in `LotWacPriceChart` e `LotComparisonChart`
  (`buildIncomeMarkerData`, colori per tipo, esclusione dalla legenda). Estraibile in un helper
  condiviso `lots/incomeMarkers.ts`.
- **Tooltip builders**: pattern ripetuto (`buildTooltipRow/Header/Divider`, tema) fra i tre grafici;
  già parzialmente condiviso, ma le righe specifiche per evento potrebbero vivere in un modulo unico.

### 9.3 Bug latenti / rischi da verificare
- **Doppia sorgente di valutazione**: il motore `value_for_lot` valuta **senza** qbq; il servizio
  rivaluta **con** qbq. Se un futuro consumer usasse per errore `value_for_lot`/`aggregate_value`
  direttamente su un asset con qbq≠1 otterrebbe valori sbagliati. Rischio latente → valutare se far
  accettare qbq anche al motore o marcare quei metodi come "internal, qbq-unaware".
- **`relative_return` non definita in modalità estimated**: se non c'è `latest_market_price`,
  `relative_return` resta `None` (corretto), ma alcune viste potrebbero aspettarsi un valore →
  verificare i fallback dei tooltip.
- **Scenario B (reference = opening_unit_price·qbq)**: usa il prezzo *d'acquisto*, non un prezzo di
  mercato reale, come base dell'Open Return. È una scelta consapevole (meglio che 9687%), ma va
  documentata all'utente come "riferimento = costo" quando la fonte è fallback/exact-da-costo.
- **Bolla del bond con prezzo assente il giorno d'apertura**: la posizione temporale della bolla usa
  la data d'apertura; se in quel giorno non c'è prezzo, la baseY usa `opening_unit_price·qbq`.
  Coerente, ma resta il tema (segnalato dall'utente) di dove **ancorare orizzontalmente** la bolla
  quando la prima quotazione è successiva — oggi resta all'apertura. Da decidere come prodotto.
- **`performance_history` (ROI/TWRR) orfano**: calcolato ancora nel backend ma non più richiesto
  dalla UI. Non è un bug, ma è codice non esercitato dal percorso principale → tenerlo coperto da
  test o marcarlo esplicitamente "solo API".

### 9.4 Limitazioni residue note
- SHORT: transfer/adjustment su SHORT non pienamente supportati (issue dedicate
  `SHORT_TRANSFER_NOT_SUPPORTED`, `SHORT_ADJUSTMENT_NOT_SUPPORTED`).
- Nessun test automatico sull'aspetto dei grafici (scelta di piano): la verifica è manuale.
- FEE/TAX asset-linked **non** riducono ancora il cost basis dei lotti (task B separato, non in
  questo scope): oggi restano costi broker-level nel Portfolio Engine.

---

## 10. Glossario rapido

| Termine | Significato |
|---|---|
| **qbq** | `quote_base_quantity`: unità per cui è quotato il prezzo (100 per bond, 1 per azioni). |
| **WAC / PMC** | Weighted Average Cost / Prezzo Medio di Carico (WAC cumulato). |
| **Frammento** | Porzione omogenea di un lotto presso una custodia (broker o transito) in un intervallo. |
| **Closure** | Chiusura FIFO (SELL/ADJ−): quantità, prezzi, realized P&L, proceeds. |
| **Open Return** | `relative_return`: rendimento del solo prezzo vs prezzo di riferimento del lotto. |
| **Total Return** | `(total_value + income)/original_cost − 1`: rendimento economico completo. |
| **Estimated at cost** | Valore residuo stimato al costo quando manca il prezzo di mercato (market P&L = 0). |
| **Cristallizzazione** | Dopo la chiusura, i risultati economici (proceeds/pnl/return) restano piatti fino a `date_to`. |

---

*Snapshot @ 2026-07-19. Riflette i round di rifinitura 1–8 (working tree, non committato al momento
della stesura). Aggiornare se il contratto DTO o le formule cambiano.*
