# Report di fattibilità tecnica — "FIFO Lot Engine v1" (high-level-plan_v1.md)

> **Documento analizzato**: `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/high-level-plan_v1.md` (1541 righe, 15 sezioni + Appendice A a 20 sotto-sezioni)
> **Metodo**: lettura integrale del piano, poi verifica riga-per-riga di ogni claim contro il codice reale del repository (nessuna assunzione). Nessuna modifica al codice è stata effettuata. Nessuna nuova soluzione è stata implementata.
> **Documenti correlati** (stessa serie, già scritti in questa sessione): `REPORT-fifo-lots-transfer-mismatch.md`, `fifo-engine-current-state.md`, `fifo-segment-model-analysis.md`, `portfolio-engine-cache-analysis.md`. Questo report li presuppone e vi fa riferimento incrociato dove utile, ma è leggibile autonomamente.

---

## 1. Executive Summary

Il piano `high-level-plan_v1.md` propone un **secondo motore** (`FifoLotEngine`), puro ed event-sourced, indipendente dal Portfolio Engine aggregato esistente, per ricostruire lotti FIFO puntuali, frammenti di custodia per broker/transito, e alimentare una nuova UI a 4 viste sincronizzate (WAC/Prezzo, Gantt, Tabella unificata, Confronto lotti).

**Giudizio complessivo: il modello matematico è solido, internamente coerente, e — punto più importante — è quasi ovunque allineato con convenzioni già presenti nel codice reale** (ordinamento `(date, id)`, "mai fondere BUY same-day", pattern di richiesta bulk con flag `include_*`/`requested_analyses`, separazione FIFO/WAC già raccomandata nel Report 3 di questa stessa serie, riuso del linking `asset_event_id` per identificare gli SPLIT). Non ho trovato **contraddizioni matematiche interne** al piano.

Ho però trovato **3 gap critici che il piano lascia completamente impliciti o del tutto silenti**, e che devono essere risolti con una decisione esplicita **prima** di scrivere una riga di `FifoLotEngine`, perché condizionano lo schema dati di ogni DTO a valle:

1. **Identità dei frammenti non definita** — lo schema d'esempio del piano stesso (§A.5.2, transfer di ritorno) genera due segmenti Coinbase distinti per lo stesso lotto; una chiave naive `lot_id:broker_id` collide.
2. **`share_percentage` non è mai menzionato nel piano** (verificato per grep, zero occorrenze) — il Portfolio Engine esistente scala le quantità **all'origine** (`tx_qty = tx.quantity * ctxn.share`), non a valle; il nuovo motore deve scegliere la stessa politica o le due viste (aggregata vs lotti) mostreranno numeri incompatibili per gli utenti che condividono un broker.
3. **Convenzione dei confini di data del transito diversa da quella già in produzione**: il piano usa `[min(d_out,d_in), max(d_out,d_in))`; il meccanismo già esistente e testato `InTransitInterval` usa `[departure+1, arrival-1]`. Se non riconciliate esplicitamente, l'invariante di riconciliazione §2.4 del piano (`Q_{a,b}(t) = Σ frammenti`) può divergere dall'Engine per 1-2 giorni intorno a ogni transfer.

A questi si aggiunge un **bug preesistente e indipendente** (già documentato nel Report 3, qui riconfermato con una terza citazione di codice indipendente): un `ADJUSTMENT` positivo collegato a uno SPLIT richiede oggi obbligatoriamente un `cost_basis_override` (`_requires_cost_basis`, `transaction_service.py:238-241`), e se questo non viene calcolato preservando il costo totale, il fallback "auto" (`_buy_unit_cost`, `portfolio_engine.py:1234-1257`) **raddoppia il costo** nel dominio WAC. Il nuovo piano lascia il dominio WAC intonso (per design, §7) — quindi il nuovo Gantt mostrerebbe uno split matematicamente corretto (costo preservato) mentre il grafico WAC accanto (invariato) continuerebbe a mostrare il costo raddoppiato: una contraddizione visiva tra le due viste che il piano stesso dichiara "separate ma coerenti".

**Raccomandazione: GO CON MODIFICHE.** Il piano è implementabile e i componenti di base (DataTable con selezione multipla, ECharts 6 con custom series già usate altrove, pattern di richiesta bulk `include_*`, funzioni di fingerprint riusabili) esistono già e riducono il rischio. Ma le 3 decisioni fondanti sopra elencate vanno prese esplicitamente (raccomandazioni concrete nella sezione 16), e il bug SPLIT/WAC va marcato come dipendenza o debito tecnico dichiarato, non ignorato.

---

## 2. Comprensione del piano — sintesi di verifica

Confermo di aver compreso, e riassumo per verifica incrociata, i punti chiave richiesti:

| Concetto | Sintesi come inteso | Confermato coerente? |
|---|---|---|
| **Lotto** `L_i=(id_i,a_i,t_i^0,q_i^0,p_i^0,c_i,o_i)` | Una quantità generata da UNA transazione di origine; niente fusione anche a parità di data/prezzo | Sì — più conservativo dell'ipotesi 2 già validata nel Report 3 (che ammetteva fusione a parità di prezzo); il codice attuale (`fifo_utils.py:98-99`) già non fonde mai, quindi il piano è addirittura già "gratis" rispetto al codice esistente |
| **Frammento** `F_{i,j}=(L_i,b_{i,j},q_{i,j},[t^{start},t^{end}),s_{i,j})` | Suddivisione di un lotto per broker/transito nel tempo, senza perdere l'identità del lotto | Concetto nuovo, non esiste analogo a grana di lotto oggi (solo a grana di pool aggregato, vedi §4.1) |
| **Classificazione eventi** BUY/SELL/ADJUSTMENT_IN/OUT/TRANSFER/SPLIT | Pre-elaborazione delle transazioni in eventi di dominio prima delle regole FIFO | Coerente con `TransactionType`/`AssetEventType` reali (§4.4 sotto) |
| **BUY**: `p^0=|A|/q` | Prezzo FIFO = costo totale / quantità | Identico alla formula già usata in `get_lots()` (`portfolio_service.py:2382`) e nel piano stesso (§2.3) |
| **SELL**: consumo FIFO sul broker della vendita, `p_s=A_s/q_s`, P&L=`q(p_s-p^0)` | FIFO per-broker, non cross-broker | **Già il comportamento reale di `get_lots()` oggi** (broker-loop indipendente, vedi §4.2) |
| **ADJUSTMENT+**: `p^0=0`, riferimento per rendimento % = prezzo di mercato alla data | Nessun costo cash, costo storico nullo; % calcolata a parte | Scelta di design deliberata — **diverge** dall'uso attuale di `cost_basis_override` come costo FIFO (vedi Criticità §7.1) ma è coerente con la separazione FIFO/WAC raccomandata nel Report 3 |
| **ADJUSTMENT−**: consumo FIFO, ricavo nullo, P&L negativo pieno | Rimozione senza incasso | Coerente — oggi `ADJUSTMENT` ha sempre `amount=0` per costruzione (`models.py`, commento riga 586) |
| **TRANSFER**: preserva lotto/data/prezzo, può biforcare, `[min,max)` in transito, non usa `cost_basis_override` in vista FIFO | Trasferimento = fork di frammento, non nuova origine | Parzialmente in tensione con la convenzione già in uso (`InTransitInterval`, vedi Criticità §7.3) |
| **SPLIT**: `q'=rq, p0'=p0/r`, costo totale invariato | Trasformazione di tutti i lotti aperti coinvolti | Il meccanismo di collegamento (`asset_event_id` + `AssetEventType.SPLIT`) esiste già e permette di IDENTIFICARE quali ADJUSTMENT sono split (§4.4); il fallback di costo esistente però NON preserva il costo (bug preesistente, vedi Criticità §7.1) |
| **Separazione FIFO/WAC** | Due domini indipendenti, WAC continua a usare `cost_basis_override` | Coerente con la raccomandazione esplicita del Report 3 (naming `original_unit_price` vs costo fiscale) |
| **Gantt, tabella unica, modale, grafico comparativo** | 4 viste sincronizzate su asse temporale/selezione | Primitive di base esistono (DataTable selezione multipla, ECharts custom series, dataZoom sync) — dettaglio in §5 |
| **Endpoint bulk `POST /portfolio/lots/analysis`** con `requested_analyses` | Un'unica richiesta condivide query/prezzi/FX/WAC per più analisi | **Pattern architetturale già in produzione** — `POST /portfolio/report` con flag `include_*` (`schemas/portfolio.py:521-536`, `portfolio_service.py:1975-2203`) fa esattamente questo per il Portfolio Engine |

La mia comprensione del piano è confermata corretta su tutti i punti richiesti dal compito. Procedo con il gap analysis.

---

## 3. Gap analysis matematica e tecnica

### 3.1 Punti corretti (verificati)

- **Formula prezzo FIFO BUY** (`p^0=|A|/q`, §2.3): identica a quella già implementata in `get_lots()` — `price_per_unit = abs(tx.amount) / qty` (`portfolio_service.py:2382`). Nessuna novità matematica, solo un nuovo consumatore.
- **Ordinamento deterministico same-day per `(date, id)`** (§4, "A parità di data, l'ordinamento deve essere deterministico tramite identificatore transazione"): è **esattamente** la convenzione già usata in tre punti indipendenti del codice: `fifo_utils.calculate_fifo_lots()` (`.sort(key=lambda t: (t.date, t.id))`, riga 89), `_get_transactions()` (`portfolio_service.py:770`, `order_by(Transaction.date, Transaction.id)`), e la classificazione dell'Engine. `Transaction.id` è una PK autoincrementante mai riusata (SQLModel/SQLite standard) — quindi il piano può contare su questa proprietà senza introdurre nulla di nuovo.
- **Non fondere mai due BUY same-day** (§2.2): il codice attuale (`fifo_utils.py:98-99`, ogni `BUY` diventa una entry separata nella deque indipendentemente da data/prezzo) è **già più conservativo** della regola del piano (che almeno menzionava un possibile confronto di prezzo). Nessun lavoro di migrazione dati necessario su questo fronte.
- **Split invariante di costo** (`q'p0'=qp0`, §4.6): matematicamente corretto e verificabile in isolamento (pura algebra). Il problema non è la formula ma la sua **applicazione pratica** oggi (vedi Criticità §7.1).
- **Pattern richiesta bulk con flag di analisi multiple**: `PortfolioReportQuery` (`schemas/portfolio.py:521-536`) con `include_summary/include_history/include_allocation_history/include_breakdown/include_positions_contribution`, orchestrato da `get_report()` che esegue l'Engine **una sola volta** e costruisce condizionalmente le viste richieste riusando `engine_result` (`portfolio_service.py:2042-2074`), è precedente diretto e collaudato per `requested_analyses` (§9 del piano). Ottimo segnale: il pattern non è solo "auspicabile", è già shippato e testato.
- **Identificazione SPLIT via `asset_event_id`** (§4.6, §3): la mappatura `TransactionType.ADJUSTMENT → {AssetEventType.PRICE_ADJUSTMENT, AssetEventType.SPLIT}` esiste già (`transaction_service.py:572`) ed è usata da `suggest_events_bulk()`. Il nuovo motore può identificare "questo ADJUSTMENT rappresenta uno split" con un semplice join `Transaction.asset_event_id → AssetEvent.type == SPLIT`, senza inferenza euristica.
- **TRANSFER con date delle due gambe diverse (fuori ordine)**: confermato che **nessuna validazione richiede oggi che le due gambe di un TRANSFER condividano la stessa data** (`_validate_linked_pair`, `transaction_service.py:244-276`, controlla solo tipo e broker distinti). Il piano ha ragione a trattare questo come scenario reale da gestire, non ipotetico.
- **In-transito escluso da entrambi i broker aggregati**: il Portfolio Engine esistente già NON attribuisce la quantità in transito a nessun broker specifico durante la finestra di transito (il valore in transito è isolato in bucket `in_transit_*` separati, `portfolio_engine.py:872-934`), il che è concettualmente identico allo stato `IN_TRANSIT` del piano (non attribuito a `b_{i,j}` di nessun broker). Buona corroborazione strutturale.

### 3.2 Contraddizioni interne al piano

**Nessuna contraddizione matematica interna trovata.** Il documento è internamente coerente: le formule di §2-§7 non si contraddicono a vicenda, e l'Appendice A (specifica visuale) è coerente con il modello matematico del corpo principale.

### 3.3 Ambiguità

1. **§10.2 vs A.16 — resa visiva di un lotto parzialmente fuori range**: §10.2 dichiara "fuori dal range → non renderizzato", mentre A.16 mostra un lotto nato prima del range ma ancora aperto, reso con una freccia di troncamento a sinistra. Le due frasi non si contraddicono a un secondo livello di lettura (il primo caso è "lotto interamente fuori range", il secondo "lotto parzialmente in range"), ma andrebbero esplicitamente distinte nella specifica finale per evitare ambiguità in fase di implementazione UI.
2. **Prezzo di riferimento per ADJUSTMENT+ quando manca un prezzo esatto alla data di origine** (§4.3, §A.13.2: `p_i^{ref}=MarketPrice_a(t_i^0)`): il piano non specifica il comportamento quando `PriceHistory` non ha un punto esatto in quella data (weekend, festivi, gap di feed). Il Portfolio Engine esistente ha già una convenzione di fallback per questo caso (uso dell'ultimo prezzo noto — dedotto dalla struttura `price_map` documentata nel Report 4); il nuovo motore dovrebbe **riusare la stessa convenzione**, ma il piano non lo dichiara esplicitamente.
3. **Fusione implicita di frammenti contigui sullo stesso broker**: l'esempio "Transfer di ritorno" (§A.5.2) mostra Coinbase con **due segmenti separati** (0,05 poi 0,10) invece di un unico segmento fuso da 0,15 dopo il rientro. È probabilmente intenzionale (preserva la traccia delle transazioni), ma non è mai dichiarato come regola esplicita ("i frammenti adiacenti sullo stesso broker non vengono mai fusi automaticamente, anche se contigui").
4. **Limite di selezione multipla** (§A.11: "non viene imposto un limite al numero di lotti selezionabili"): assenza di limite è una scelta di prodotto valida, ma va accoppiata a una strategia esplicita per il caso limite (centinaia di lotti selezionati → centinaia di serie storiche giornaliere da calcolare/renderizzare); il piano non lo affronta (vedi Criticità §7.7).

### 3.4 Edge case non coperti dal piano

- **Catene lunghe di transfer avanti-indietro** (>2 hop): il piano tratta esplicitamente 1 biforcazione e 1 rientro (§A.5.1, §A.5.2), ma non un caso a N hop con N>2 broker coinvolti in sequenza. Il modello matematico (§2.4) generalizza correttamente (è ricorsivo per costruzione: ogni frammento può essere ulteriormente suddiviso), ma la resa Gantt con molti segmenti sottili non è discussa (rischio di leggibilità, non di correttezza matematica).
- **Lotti multi-valuta**: il piano assegna una singola `c_i` (valuta originaria) per lotto, ma un frammento trasferito con `cost_basis_override` in valuta diversa da `c_i` (scenario reale e già gestito dall'Engine odierno, `_buy_unit_cost()`, righe 1238-1257, con conversione FX incrociata) non è discusso esplicitamente — il nuovo motore dovrebbe riusare la stessa logica di conversione a due tassi (`cost_ccy→target`, `asset_ccy→target`) già presente.
- **Transazione di partner mancante/cancellata**: se la gamba collegata (`related_transaction_id`) di un TRANSFER viene cancellata lasciando un riferimento pendente, il piano non specifica il comportamento. Esiste già un pattern difensivo riusabile: `ScopeAwareTransactionClassifier.classify()` tratta esplicitamente il caso "paired is None" trattando la transazione come normale e generando un warning (`portfolio_engine.py:227-235`) invece di sollevare un'eccezione — raccomando lo stesso trattamento per il nuovo motore.
- **`share_percentage`**: assente dal piano (vedi Criticità §7.2) — è l'edge case più importante non coperto, perché riguarda TUTTI i lotti su un broker condiviso, non un caso limite raro.

### 3.5 Decisioni di prodotto ancora necessarie

Enumerate esaustivamente nella sezione 16 ("Domande residue"). In sintesi: schema id frammento, politica `share_percentage`, confine giorno transito, comportamento su oversell/dato incoerente, fallback prezzo di riferimento ADJUSTMENT+, limite pratico di selezione multipla.

---

## 4. Confronto con il repository reale, componente per componente

### 4.1 Portfolio Engine e DailyStateBuilder

**Struttura dati centrale**: `DailyPositionState` (`portfolio_engine.py:352-370`) mantiene **un solo record per `(date, broker_id, asset_id)`**, con pool WAC aggregato a due soli numeri cumulativi (`wac_pool_qty`, `wac_pool_cost`). Confermato (già documentato nel Report 4, qui riverificato): quando due BUY si fondono nel pool, l'informazione su prezzo/data del singolo acquisto è **irreversibilmente persa** (`wac_pool_cost[key] = old_cost + unit_cost_asset_ccy * tx_qty`, riga 599).

**Conseguenza diretta per questo piano**: il Portfolio Engine, per costruzione, non può MAI fornire dati a grana di lotto. Il piano lo sa e infatti non lo tocca (§11: "Portfolio Engine esistente → invariato"). Questa è la scelta corretta — **concordo pienamente**, coerente con la raccomandazione già data nel Report 4 di non estendere `DailyStateBuilder` (rischio alto di regressione su NAV/MWRR/3-pool, già stabilizzato con test).

**Meccanismo riutilizzabile scoperto in questa analisi — `ScopeAwareTransactionClassifier`/`InTransitInterval`** (`portfolio_engine.py:100-336`, letto integralmente): è un meccanismo **già esistente, testato (`test_scope_classifier.py`), e concettualmente molto vicino** a ciò che il piano chiede per il transito:
- Determina direzione/ordine delle due gambe indipendentemente da quale sia "OUT" o "IN", solo dalle date (`tx_a.date <= tx_b.date: departure, arrival = tx_a, tx_b`, righe 299-302) — **stesso approccio del piano** (§4.5: "la direzione dipende dal segno delle quantità, non dall'ordine cronologico delle date" — concettualmente equivalente, entrambi calcolano min/max indipendentemente dall'ordine di inserimento).
- Estrae il costo dalla gamba di partenza con fallback sulla gamba di arrivo (`cbo = departure.cost_basis_override or arrival.cost_basis_override`, riga 315).
- Gestisce già il caso "paired non trovato" in modo difensivo (righe 227-235).

**Ma attenzione — convenzione dei confini diversa** (Criticità §7.3): `start_date = departure.date + 1`, `end_date = arrival.date - 1` (righe 304-305, **esclude entrambe le date di regolamento**) contro la formula del piano `[min(d_out,d_in), max(d_out,d_in))` (**include** la data di partenza). Su un transfer con gambe a 2+ giorni di distanza, i due motori assegnerebbero l'ultimo/primo giorno a broker diversi.

**Trattamento quantità durante il transito**: `cumulative_qty[key] += tx_qty` (riga 620) applica il delta pieno alla data della gamba stessa, indipendentemente dalla finestra di transito — cioè la quantità aggregata per broker cala/sale esattamente alle date di regolamento, e solo il **valore monetario** (cash/market value/cost basis) resta nel bucket `in_transit_*` per i giorni intermedi. Questo è concettualmente compatibile con l'idea di frammento `IN_TRANSIT` non attribuito a nessun broker specifico, ma la quantità stessa non è mai "sospesa" nel motore attuale — è la sola dimensione monetaria a esserlo. Il nuovo `FifoLotEngine`, se vuole realmente sospendere anche la *quantità* visibile per broker durante il transito (come suggerisce la resa grafica del Gantt, §A.4.1: il segmento "Transito" è visivamente distinto sia da Coinbase che da IBKR), introduce un concetto più fine di quanto l'Engine aggregato rappresenti oggi — non un problema, ma un punto da tenere presente per la riconciliazione (l'invariante §2.4 riguarda la quantità, non il valore, quindi la divergenza di confine giorno è più rilevante qui che nel resto dell'Engine).

**Funzioni riusabili as-is** (pure, module-level, nessuna modifica necessaria):
- `_compute_tx_fingerprint(transactions)` (`portfolio_engine.py:1633-1642`) — hash MD5 su `id:updated_at`.
- `_compute_price_fingerprint(held_asset_ids, date_to)` (`portfolio_engine.py:1868` ss.) — COUNT+MAX(fetched_at).

Entrambe già raccomandate nel Report 4 per le nuove cache dedicate (`_lots_gantt_cache`, `_lot_history_cache`) — qui confermo che sono funzioni generiche riusabili senza modifica.

**`allow_asset_shorting`/`allow_cash_overdraft`** (`models.py:406-407`): flag broker già esistenti, usati in `_validate_broker_balances` (`transaction_service.py:419-510`) con un **loop giorno-per-giorno** dalla prima transazione all'ultima (non O(transazioni) ma O(giorni civili)) per verificare che nessun saldo scenda sotto zero, a meno che il flag lo permetta esplicitamente. Il piano rimanda correttamente lo short selling (§12: "eventuali funzionalità da rinviare, in particolare short selling") — scelta corretta, perché anche la funzione pura `calculate_fifo_lots()` oggi **solleva `ValueError`** se una SELL eccede la quantità disponibile (`fifo_utils.py:104`), quindi non esiste alcuna rappresentazione di lotto negativo da cui partire.

**Classificazione ESISTE/MODIFICARE/CREARE**: Portfolio Engine → **ESISTE, invariato per design** (corretto). `ScopeAwareTransactionClassifier`/`InTransitInterval` → **ESISTE, pattern riutilizzabile con adattamento** (non riutilizzabile letteralmente per fragment-per-lotto, ma il metodo/l'approccio sì).

### 4.2 FIFO/WAC utilities

**`fifo_utils.calculate_fifo_lots()`** (148 righe, letto integralmente): unico codice con vera granularità di lotto. Accetta **solo BUY/SELL** (`FIFOTransactionInput.type: str # "BUY" | "SELL"`, righe 17-28), ordina per `(date, id)`, non fonde mai BUY, solleva `ValueError` su oversell. **Non gestisce**: TRANSFER, ADJUSTMENT, valute, FX, broker multipli in un'unica chiamata, custodia/transito. È l'esatto punto di partenza matematico (loop FIFO via deque) ma non la struttura dati — il piano lo sostituisce correttamente (§11: "sostituito progressivamente dal nuovo motore").

**`get_lots()`** (`portfolio_service.py:2331-2434`, letto integralmente): orchestratore attuale. Punto cruciale verificato qui per la prima volta in modo esplicito — **il codice attuale già esegue FIFO indipendentemente per ciascun broker** (loop `for access in accesses: ... calculate_fifo_lots(fifo_inputs)`, righe 2360-2427). Questo conferma che la scelta del piano "SELL consuma FIFO i frammenti presenti sul broker della vendita" (§4.2) **non è una restrizione nuova ma la formalizzazione di un comportamento già esistente**. Il difetto attuale non è l'ambito per-broker del FIFO, ma il filtro `_HOLDING_TYPES = {BUY, SELL}` (`portfolio_service.py:698`) che esclude TRANSFER — motivo per cui, come riscontrato dall'utente all'inizio di questa serie di analisi, un broker che ha ricevuto quantità solo via TRANSFER-IN mostra **zero lotti aperti** oggi ("non vedo la bolla per l'altro broker che possiede bitcoin" — bug reale, causa ora completamente spiegata a livello di codice: `asset_txns` non contiene mai transazioni TRANSFER, quindi `fifo_inputs` è vuoto per quel broker).

**`get_asset_history()`** (`portfolio_service.py:2205-2329`, letto integralmente): chiama `compute_wac_iterative()` **una volta per ogni punto prezzo, per ogni broker** (righe 2277-2301), più un'ulteriore passata combinata se i broker sono ≥2 (righe 2303-2327). `compute_wac_iterative()` (righe 97-157) esegue **una query DB non condizionale** ad ogni chiamata (`db_rows = list((await session.execute(stmt)).scalars().all())`, riga 124) **prima** di controllare la cache (`_wac_cache`, popolata da un fingerprint calcolato sulle righe appena interrogate). Quindi: per un asset con 2 broker e ~1000 punti prezzo (3 anni di storico giornaliero), questo endpoint esegue **~2000 query DB separate per singola richiesta**, e la cache (`maxsize=200`) evita solo la **ricomputazione matematica**, non la query. Questo è il dato quantitativo più severo di questa analisi. Il piano ha pienamente ragione a dire "`get_asset_history()` attuale → da riesaminare, non da usare come modello" (§11) — qui ne fornisco la prova numerica.

**Classificazione**: `calculate_fifo_lots()` → **DA RIMUOVERE** (dopo migrazione, uso limitato e noto: solo `get_lots()`). `get_lots()` → **DA RIMUOVERE** (sostituito dal nuovo bulk endpoint). `get_asset_history()` → **DA RIMUOVERE o RISCRIVERE integralmente**, mai da estendere.

### 4.3 PortfolioService e API

**Pattern bulk già in produzione**: `get_report()` (righe 1975-2203) calcola due fingerprint leggeri (`tx_fp` via query aggregata, `price_fp` via `COUNT`+`MAX(fetched_at)`, non hash per-riga) per la chiave di cache L2, poi esegue l'Engine **una volta sola** con `date_from=None` (sempre dall'inception), e costruisce le viste incluse riusando `engine_result`. `PortfolioReportQuery` (`schemas/portfolio.py:521-536`) è il precedente diretto per `requested_analyses`.

**Endpoint reali oggi** (`portfolio_api.py`, 200 righe, confermato in Report 4): solo 4 — `/wac`, `/report`, `/asset-history`, `/lots`. Il piano ne propone un quinto (`/lots/analysis`) che consoliderebbe/sostituirebbe `/asset-history` e `/lots`.

**Helper riusabili per il nuovo loader bulk**:
- `_get_user_broker_access(user_id, broker_ids)` (righe 734-744) — query singola, già filtrata per accesso.
- `_get_transactions(broker_id, tx_types, date_from, date_to)` (righe 756-772) — **ambito singolo broker**; il nuovo loader dovrà generalizzarla a `broker_id IN (...)` per evitare N query (oggi `get_lots()` la chiama una volta per broker in un loop, righe 2364-2368 — pattern N+1 noto ma limitato, dato che il numero di broker per utente è tipicamente piccolo, a differenza del N+1 di `get_asset_history()` che scala con il numero di *punti prezzo*).
- `_get_latest_price(asset_id)` (riga 774) — query singola per asset.

**Classificazione**: pattern `get_report()`/`PortfolioReportQuery` → **ESISTE, riutilizzabile come modello architetturale diretto** (non come codice, ma come schema di orchestrazione). `_get_user_broker_access` → **ESISTE E RIUTILIZZABILE as-is**. `_get_transactions` → **DA MODIFICARE** (estensione a multi-broker per il nuovo loader bulk).

### 4.4 Prezzi, FX, share_percentage e transazioni collegate

- **Prezzi**: `PriceHistory` con vincolo `UniqueConstraint(asset_id, date)` — un punto al giorno, nessun dato intraday. Compatibile senza modifiche con `PRICE_HISTORY` (§9 del piano).
- **FX**: non riletto in dettaglio in questa sessione (già mappato nel Report 4 — `fx_rate_map` bulk-caricato dall'Engine); la conversione a due tassi incrociati (`cost_ccy→target`, `asset_ccy→target`) usata da `_buy_unit_cost()` (righe 1238-1257) è il pattern di riferimento da riusare per convertire i valori dei frammenti nella `target_currency` richiesta.
- **`share_percentage`** (`BrokerUserAccess.share_percentage`, `models.py`, vincolo `0.00 ≤ x ≤ 1.00`, somma per broker ≤ 1.00): **il piano non lo menziona mai** (verificato per grep sull'intero documento, zero occorrenze). Il Portfolio Engine esistente applica lo scaling **all'origine**, prima di ogni aggregazione: `tx_qty = tx.quantity * ctxn.share` (`portfolio_engine.py:591`, ripetuto identicamente alle righe 481, 543, 717, 1149, 1160, 1168 per cash/asset/in-transit). Questo è un fatto strutturale importante: se il nuovo `FifoLotEngine` non applica la stessa scalatura nello stesso punto (alla creazione del frammento dalla transazione di origine), l'invariante di riconciliazione §2.4 (`Q_{a,b}(t) = Σ frammenti`) **non regge** per un broker condiviso tra utenti con quote diverse. Raccomando esplicitamente di seguire la stessa politica "scale-at-source" per coerenza (dettaglio in Criticità §7.2).
- **Transazioni collegate**: `related_transaction_id` è una FK **DEFERRABLE INITIALLY DEFERRED** (`models.py`), che permette di creare entrambe le gambe nella stessa transazione DB senza violare il vincolo FK — nessun problema strutturale. Il caso "gamba collegata fuori dallo scope broker caricato" è già risolto concettualmente da `ScopeAwareTransactionClassifier.get_needed_paired_ids()` (righe 173-183: restituisce gli ID delle transazioni collegate non ancora caricate, da recuperare con una query mirata) — pattern riusabile 1:1 per il loader bulk del nuovo endpoint.

**Classificazione**: `share_percentage` handling → **DA CREARE** (nessuna logica equivalente esiste oggi a grana di lotto; la politica di scaling va decisa e implementata ex novo, sia pure riusando il pattern "scale-at-source"). `get_needed_paired_ids()` → **ESISTE E RIUTILIZZABILE as-is** per il loader bulk.

### 4.5 Cache e store frontend

Già mappato in dettaglio nel Report 4 (`portfolio-engine-cache-analysis.md`, §4 e Appendice frontend). Confermo qui solo la parte rilevante per QUESTO piano: **non esiste alcuno store "LotsAnalysisStore"** oggi, né un pattern di history-per-lotto lazy. `FIFOLotsPanel.svelte` non usa nessuna cache (rifetcha ad ogni apertura/cambio asset, riconfermato dall'esplorazione di questa sessione). Il pattern più vicino riutilizzabile è `TimeSeriesStore.ts` (gap-detection per delta-fetch), utile come **modello** per una futura history-per-lotto on-demand, ma non riusabile letteralmente (i dati non sono una serie temporale singola ma multi-lotto/multi-serie).

**Classificazione**: store frontend dedicato → **DA CREARE**, con pattern di riferimento esistente (`TimeSeriesStore`) da adattare, non riusare direttamente.

### 4.6 DataTable

Componente generico: `frontend/src/lib/components/table/DataTable.svelte`. Verificato con lettura diretta (oltre alla mappatura del sub-agente):

```
enableSelection?: boolean;
selectionMode?: 'multi' | 'single' | 'none';
onSelectionChange?: (selectedIds: string[]) => void;
onRowClick?: (row: T) => void;
onRowDoubleClick?: (row: T) => void;
```
(`DataTable.svelte:33-41, 115-122, 695-768`)

Tutte le primitive richieste dal piano esistono già come prop pubbliche: selezione multipla (§10.3), doppio click distinto da click singolo (§10.3, §A.9.2), e un tipo di cella custom cliccabile (`CellContent.type === 'custom'`, `types.ts:66-72,134-153`) utilizzabile per la colonna "Custodia" che deve aprire la modale **senza** attivare la selezione di riga (§A.10.1: "La selezione della riga e l'apertura della modale sono azioni distinte" — esattamente supportato, dato che il click sulla cella custom e il click sulla riga sono già gestori separati).

Non trovato: nessuna tabella esistente nell'app che already colleghi selezione multipla a un grafico di confronto aggiornato dinamicamente — questa parte di "glue logic" (selectedIds → props del grafico comparativo) è lavoro nuovo ma di integrazione, non di componente.

Il componente **non** è basato su TanStack Table (esiste un adapter TanStack separato, `frontend/src/lib/tanstack-table/`, non usato da `DataTable.svelte`) — nessun impatto pratico sul piano, la superficie di prop necessaria è comunque presente.

**Classificazione**: `DataTable.svelte` → **ESISTE E RIUTILIZZABILE as-is** per selezione, click, doppio click e cella custom. Glue logic selezione→grafico → **DA CREARE** (piccolo).

### 4.7 Componenti ECharts esistenti

- **ECharts versione**: `^6.0.0` (`frontend/package.json:62`) — confermato.
- **Custom series (`type: 'custom'`)** già usata in `PerformanceChart.svelte` (righe 528-565, 690-754) e `AllocationHistoryChart.svelte` (righe 520-565, 690-760). Questo è un fatto tecnico importante: il team ha già competenza ed esempi in-house per il rendering custom via `renderItem`, la tecnica esatta necessaria per il Gantt (ogni lane = valore su asse a categorie, ogni segmento = rettangolo disegnato manualmente con spessore/colore/opacità variabili, §A.4.2-A.4.3 del piano). **Non serve introdurre una nuova libreria o un nuovo paradigma di rendering.**
- **Stacked bar** già usato in tre componenti (`PerformanceChart`, `GrowthChart`, `AllocationHistoryChart`) — pattern alternativo disponibile se il Gantt venisse semplificato a barre impilate invece di renderItem custom (opzione più economica ma meno flessibile per spessore variabile continuo).
- **`buildDataZoom` + `echartsDataZoomSync.ts`** (`chartCoreHelpers.ts:260-307`, `echartsDataZoomSync.ts:1-62`): helper condivisi già usati da `AssetWacPriceChart` per sincronizzare zoom/pan con `BubbleLotTimeline` dentro `FIFOLotsPanel.svelte` (righe 105-114, 275-285) — **precedente diretto e collaudato** per la sincronizzazione richiesta dal piano tra WAC-chart, Gantt e grafico di confronto (§10.2, §A.9, §A.15).

**Classificazione**: paradigma custom-series ECharts → **ESISTE E RIUTILIZZABILE** (pattern, non componente specifico). Helper dataZoom sync → **ESISTE E RIUTILIZZABILE as-is**. Componente Gantt vero e proprio → **DA CREARE** (nessun componente Gantt esiste oggi, ma con tutti gli ingredienti tecnici già presenti nel codebase).

### 4.8 Open/Closed Lots, Bubble Timeline e Asset WAC/Price Chart

- **`AssetWacPriceChart.svelte`**: legge `GET /portfolio/asset-history`, mostra WAC per broker (line) + WAC combinato (line tratteggiata) + prezzo di mercato (line) in modalità assoluta, oppure ROI/TWRR in modalità percentuale; ha già dataZoom e sync bidirezionale con `xAxisRange` (righe 21-48, 73-87, 532-568, 671-706). **Classificazione: DA MODIFICARE** — mantiene la responsabilità aggregata (coerente con §11 del piano: "mantenuto ed evoluto per la sincronizzazione col Gantt"), ma deve: (a) cambiare sorgente dati una volta riscritto `get_asset_history()`, (b) aggiungere i marker di evento discreti richiesti da §A.3.2.
- **`BubbleLotTimeline.svelte`**: ECharts `scatter` + `effectScatter` (pulse) + linea connettore — **non è un Gantt** (nessun segmento orizzontale multi-tratto per lane). Il piano lo dichiara esplicitamente sostituito (§11: "BubbleLotTimeline → sostituita dal Gantt") — **confermo che è la scelta tecnica corretta**, non è evolvibile incrementalmente in un Gantt: il tipo di serie è strutturalmente diverso (punti vs segmenti). **Classificazione: DA RIMUOVERE** dopo la migrazione.
- **`OpenLotsTable.svelte` / `ClosedLotsTable.svelte`**: entrambi thin wrapper di `DataTable` con `selectionMode="none"` (righe 251-271 e 232-252 rispettivamente) — la conversione a tabella unica con selezione multipla è un flip di configurazione + fusione delle colonne, non una riscrittura da zero. **Classificazione: DA RIMUOVERE come componenti separati, MA il loro contenuto (colonne, `BrokerBadge`) è riusabile nella nuova tabella unificata.**
- **`FIFOLotsPanel.svelte`**: orchestratore attuale, chiama `/portfolio/lots`, gestisce `sharedXAxisRange` e la sincronizzazione bidirezionale bubble↔riga. Il lavoro di sincronizzazione zoom già fatto qui è il precedente diretto per la sincronizzazione Gantt↔WAC-chart richiesta dal piano. **Classificazione: DA MODIFICARE profondamente** (cambia sorgente dati e sostituisce uno dei due grafici, ma l'infrastruttura di sync resta).

### 4.9 i18n e `./dev.py i18n audit`

Confermato: `./dev.py i18n audit` esiste, chiama `frontend/scripts/i18n-audit.py`, e fa più della semplice verifica di coerenza chiavi (rileva anche duplicati, esporta in Markdown/Excel). Struttura a namespace per feature in JSON annidati (`frontend/src/lib/i18n/{en,it,fr,es}.json`), appiattiti in dot-notation dallo script. Le 4 traduzioni esplicite richieste dal piano per "Market Price" (IT/EN/FR/ES, §10.1, §A.3.1) sono banalmente aggiungibili con questo tooling esistente, così come tutte le nuove chiavi per Gantt/modale/tabella unificata.

**Classificazione**: tooling i18n → **ESISTE E RIUTILIZZABILE as-is**, nessuna modifica necessaria allo strumento, solo nuove chiavi da aggiungere seguendo la convenzione a namespace esistente.

---

## 5. Matrice riepilogativa ESISTE / MODIFICARE / CREARE / RIMUOVERE

| Componente | Stato | Note |
|---|---|---|
| Portfolio Engine / `DailyStateBuilder` | **ESISTE — invariato** | Corretto per design, nessuna estensione richiesta né consigliata |
| `ScopeAwareTransactionClassifier` / `InTransitInterval` | **ESISTE — pattern riutilizzabile con adattamento** | Riusare l'approccio (classificazione linked pair, gestione partner mancante), non la struttura dati (è a grana di coppia, non di lotto); riconciliare la convenzione dei confini di data (Criticità §7.3) |
| `_compute_tx_fingerprint` / `_compute_price_fingerprint` | **ESISTE E RIUTILIZZABILE as-is** | Funzioni pure module-level, nessuna modifica |
| `fifo_utils.calculate_fifo_lots()` | **DA RIMUOVERE** (dopo migrazione) | Uso limitato e noto (solo `get_lots()`); logica di ordinamento/non-fusione già corretta e riusabile come riferimento/test-vector |
| `get_lots()` | **DA RIMUOVERE** | Sostituito dal nuovo bulk endpoint; comportamento per-broker già corretto da preservare concettualmente |
| `get_asset_history()` | **DA RIMUOVERE o RISCRIVERE integralmente** | O(broker × punti prezzo) query DB confermato — non estendere mai |
| `compute_wac_iterative` / `_wac_cache` | **DA MANTENERE TEMPORANEAMENTE** | Ancora usato da `/portfolio/wac` (fuori scope di questo piano); non toccare, ma non riusare per il nuovo motore |
| `PortfolioReportQuery` / `get_report()` (pattern) | **ESISTE — riutilizzabile come modello architetturale** | Precedente diretto per `requested_analyses` / bulk endpoint |
| `_get_user_broker_access` | **ESISTE E RIUTILIZZABILE as-is** | — |
| `_get_transactions` | **DA MODIFICARE** | Estendere a multi-broker per il loader bulk |
| `get_needed_paired_ids()` | **ESISTE E RIUTILIZZABILE as-is** | Per risolvere gambe TRANSFER fuori scope broker |
| `share_percentage` handling a grana lotto | **DA CREARE** | Nessuna logica esiste oggi; politica da decidere (raccomandazione: scale-at-source, §7.2) |
| Nuovo `FifoLotEngine` | **DA CREARE** | Puro, no I/O, stesso stile di `fifo_utils.py`/classifier |
| Nuovo endpoint `POST /portfolio/lots/analysis` | **DA CREARE** | — |
| Nuovi DTO (lots[], custody_segments[], lot_events[], histories[], wac_series[]) | **DA CREARE**, parzialmente **DA MODIFICARE** | `AssetHistoryPoint` (già esiste) è riusabile per `wac_series[]` con modifiche; gli altri sono nuovi |
| `DataTable.svelte` | **ESISTE E RIUTILIZZABILE as-is** | Selezione multipla, click/doppio click, cella custom già presenti |
| `OpenLotsTable.svelte` / `ClosedLotsTable.svelte` | **DA RIMUOVERE come componenti**, contenuto riusabile | Fondere in tabella unica |
| `BubbleLotTimeline.svelte` | **DA RIMUOVERE** | Non evolvibile incrementalmente in Gantt (tipo di serie strutturalmente diverso) |
| `AssetWacPriceChart.svelte` | **DA MODIFICARE** | Cambio sorgente dati + marker eventi; struttura chart mantenuta |
| `FIFOLotsPanel.svelte` | **DA MODIFICARE profondamente** | Sostituisce un grafico, aggiunge tabella unica e modale, mantiene l'infrastruttura di sync zoom |
| Nuovo componente Gantt | **DA CREARE** | Tecnica (custom series ECharts) già padroneggiata dal team su altri chart |
| Nuova modale Custodia | **DA CREARE** | — |
| `buildDataZoom` / `echartsDataZoomSync.ts` | **ESISTE E RIUTILIZZABILE as-is** | — |
| Store frontend dedicato (`LotsAnalysisStore`) | **DA CREARE** | Pattern di riferimento: `TimeSeriesStore` (da adattare, non riusare 1:1) |
| `./dev.py i18n audit` e struttura namespace i18n | **ESISTE E RIUTILIZZABILE as-is** | Solo nuove chiavi da aggiungere |
| Cache dedicata lotti/history (`_lots_gantt_cache`, `_lot_history_cache`) | **DA CREARE** | Già proposta nel Report 4; non riusare `_wac_cache` (rischio thrashing noto) né `_portfolio_blob_cache` (formato incompatibile) |

---

## 6. Criticità ordinate per severità

### 🔴 CRITICA

**7.1 — Bug preesistente SPLIT/WAC-doubling non risolto dal piano, ma reso visivamente contraddittorio da esso.**
`_requires_cost_basis()` (`transaction_service.py:233-242`) impone `cost_basis_override` obbligatorio per **qualunque** `ADJUSTMENT` con `quantity>0`, incluso uno collegato a un evento SPLIT — non esiste eccezione nel codice attuale. Se questo valore viene calcolato dal fallback "auto" (`transaction_service.py:1591-1603`, che invoca `compute_wac_iterative` e scrive il risultato come `cost_basis_override`), e questo confluisce nel pool WAC via `_buy_unit_cost()` (`portfolio_engine.py:1230-1233`: `total_cost = tx.cost_basis_override * qty`, sommato al pool esistente riga 599), il costo totale della posizione **raddoppia** invece di restare invariato — esattamente il bug già trovato indipendentemente nel Report 3 (`fifo-segment-model-analysis.md`), qui **riconfermato con una terza citazione di codice indipendente**. Il piano lascia il dominio WAC "invariato" (§7, per design corretto), quindi il nuovo Gantt mostrerebbe uno split matematicamente pulito (`q'p0'=qp0` preservato) mentre il grafico WAC accanto (stesso asset, stesso evento) continuerebbe a mostrare il costo raddoppiato. Le due viste che il piano vuole "separate ma coerenti" diventerebbero visibilmente incoerenti per l'utente finale nel caso d'uso più comune per uno SPLIT.
→ **Raccomandazione**: trattare la correzione di questo bug come **dipendenza esplicita** del piano (fix minimo: quando `asset_event.type == SPLIT`, calcolare `cost_basis_override = old_total_cost / new_qty` invece di usare il fallback WAC-corrente), da fare prima o in parallelo, non come "fuori scope silenzioso".

**7.2 — `share_percentage` completamente assente dal piano.**
Verificato per grep: zero occorrenze nell'intero documento di 1541 righe. Il Portfolio Engine applica lo scaling **all'origine** (`tx_qty = tx.quantity * ctxn.share`, sei citazioni indipendenti in `portfolio_engine.py`). Se il nuovo `FifoLotEngine` non applica la stessa politica nello stesso punto (creazione frammento dalla transazione), l'invariante di riconciliazione §2.4 del piano stesso (`Q_{a,b}(t) = Σ frammenti`) si rompe per ogni broker condiviso tra più utenti con quote diverse — e i broker condivisi sono una feature di prima classe del sistema (vincolo di somma quote ≤ 1.00 già presente nello schema DB).
→ **Raccomandazione**: applicare `share_percentage` "scale-at-source", cioè scalare `q_i^0` (e conseguentemente ogni `q_{i,j}`) al momento della creazione del lotto/frammento dalla transazione di origine, usando lo stesso fattore `share` già caricato da `BrokerUserAccess` — **non** scalare a valle/display. Questo garantisce che "lotto" abbia lo stesso significato quantitativo nelle due viste (aggregata ed a grana di lotto) per lo stesso utente.

**7.3 — Convenzione dei confini di data del transito diversa da quella già in produzione.**
Piano: `t_start=min(d_out,d_in)`, `t_end=max(d_out,d_in)`, finestra `[t_start,t_end)` — include la data di partenza. Codice esistente e testato (`InTransitInterval`, `portfolio_engine.py:304-305`): `start=departure+1`, `end=arrival-1` — esclude **entrambe** le date di regolamento. Su un TRANSFER con gambe distanti ≥2 giorni, i due motori disegnerebbero confini diversi per lo stesso evento, e l'invariante di riconciliazione §2.4 potrebbe silenziosamente mostrare un disallineamento di 1-2 giorni tra il Gantt (nuovo motore) e i bucket `in_transit_*` del dashboard aggregato (motore esistente) per quei giorni specifici.
→ **Raccomandazione**: decidere esplicitamente se allineare il nuovo motore alla convenzione esistente (preferibile per coerenza cross-engine, anche se il confine "esclusivo su entrambi i lati" è meno intuitivo da spiegare in UI) oppure documentare e testare esplicitamente la divergenza attesa (con un invariante di test dedicato, non un'assunzione implicita).

**7.4 — Schema di identità dei frammenti non definito, con collisione dimostrabile nell'esempio del piano stesso.**
Il piano definisce `id_i` come "identificatore stabile del lotto" (naturalmente = id della transazione di origine, dato che ogni lotto = una transazione di origine, non fusa mai) ma **non definisce alcun identificatore per il frammento** `F_{i,j}`. L'esempio "Transfer di ritorno" del piano stesso (§A.5.2: Coinbase→IBKR 0,10, poi IBKR→Coinbase 0,05) produce **due segmenti Coinbase distinti** per lo stesso lotto (prima e dopo il rientro) — una chiave naive `f"{lot_id}:{broker_id}"` li farebbe collidere. Questo impatta direttamente anche §A.17 ("la selezione viene mantenuta quando gli stessi lot_id sono ancora presenti nella nuova risposta"), che presuppone un id stabile e univoco end-to-end.
→ **Raccomandazione**: id frammento = `f"{lot_id}:{sequence_index}"`, dove `sequence_index` è l'ordine cronologico di creazione del frammento (deterministico, derivabile dall'ordinamento `(date, transaction_id)` già usato ovunque nel sistema).

### 🟠 ALTA

**7.5 — `get_asset_history()`'s N+1 query pattern non deve essere replicato nel nuovo endpoint bulk.**
Confermato quantitativamente (§4.2): ~2000 query DB per una singola richiesta con 2 broker e 3 anni di storico. Il piano evita correttamente di modellarsi su questo codice (§11), ma non fornisce una guardia esplicita contro la reintroduzione dello stesso pattern nelle nuove analisi `PRICE_HISTORY`/`BROKER_WAC_HISTORY`/`CUMULATIVE_WAC_HISTORY` (§9).
→ **Raccomandazione**: aggiungere un invariante di test esplicito ("il numero di query DB per una richiesta bulk non deve scalare con il numero di giorni/punti richiesti") — dettaglio in §12.

**7.6 — Nessun "wizard" o calcolo assistito per SPLIT nella UI attuale.**
Verificato: nessun componente frontend dedicato alla gestione di uno stock split esiste oggi (cercato per pattern "split" tra i componenti — solo falsi positivi come `SplitPane`/date picker). L'utente dovrebbe oggi calcolare manualmente `cost_basis_override = costo_totale_precedente / nuova_quantità` per evitare il bug §7.1 — nessuna assistenza UI lo fa per lui.
→ **Raccomandazione**: considerare, come parte del lavoro (o come dipendenza dichiarata), un piccolo affinamento UI che precompili `cost_basis_override` in modo cost-preserving quando l'utente collega un ADJUSTMENT a un evento SPLIT — chiude il bug alla fonte invece di richiedere disciplina manuale.

**7.7 — Comportamento su "SELL/oversell impossibile" da definire esplicitamente, non ereditare il crash attuale.**
`calculate_fifo_lots()` solleva `ValueError` non gestita se una SELL eccede la quantità disponibile (`fifo_utils.py:104`) — oggi questo si traduce probabilmente in un errore 500 per l'intera richiesta. Il piano rimanda correttamente lo short-selling (§12), ma un caso più comune e non legato allo short selling — un TRANSFER-IN storico mai registrato che fa apparire una SELL "impossibile" sul FIFO per-broker — potrebbe scatenare lo stesso crash su dati reali imperfetti (esattamente il tipo di incongruenza dati che ha originato l'intera serie di analisi di questa sessione).
→ **Raccomandazione**: il nuovo motore deve intercettare questo caso e restituire un lotto/asset con un flag esplicito (es. `data_inconsistent: true`) invece di un'eccezione non gestita, permettendo comunque il rendering parziale della UI.

### 🟡 MEDIA

**7.8 — Nessun limite dichiarato per la selezione multipla di lotti (§A.11), rischio di performance non affrontato.**
Centinaia di lotti selezionati implicano centinaia di serie storiche giornaliere da calcolare e renderizzare nel grafico di confronto. Non bloccante per il design ma da affrontare con una soglia soft (warning UI) o un degrado controllato lato backend.

**7.9 — Fallback prezzo di riferimento per ADJUSTMENT+ non specificato quando manca un prezzo esatto alla data di origine.**
Il piano assume `MarketPrice_a(t_i^0)` sempre disponibile; la realtà (weekend, festivi, gap di feed) richiede un fallback esplicito — raccomando di riusare la stessa convenzione già presente nella struttura `price_map` dell'Engine (ultimo prezzo noto).

**7.10 — Nessuna store frontend dedicata esiste, servirà lavoro di progettazione ex novo (non solo implementazione).**
Confermato dall'esplorazione frontend: il pattern più vicino (`TimeSeriesStore`) è un buon riferimento ma non riusabile 1:1 per dati multi-lotto/multi-serie.

### 🟢 BASSA

**7.11 — `OpenLotsTable`/`ClosedLotsTable` richiedono solo un cambio di configurazione (`selectionMode="none"` → `"multi"`) più fusione colonne — rischio basso.**

**7.12 — 4 nuove traduzioni "Market Price" (IT/EN/FR/ES) esplicitamente fornite dal piano — banale con il tooling i18n esistente.**

---

## 7. Fattibilità dei punti specifici richiesti

| Aspetto | Fattibilità | Note |
|---|---|---|
| Nuovo `FifoLotEngine` puro | **Alta** | Stile identico a `fifo_utils.py`/`ScopeAwareTransactionClassifier` (pure, no I/O) già presente e testato nel repository; nessun ostacolo tecnico, solo le 3 decisioni fondanti (§7.1-7.4 sopra) da prendere prima |
| Intervalli di custodia e transito | **Alta, con riconciliazione da fare** | Il concetto esiste già a livello aggregato (`InTransitInterval`); serve solo estenderlo a grana di frammento e allineare la convenzione dei confini (Criticità §7.3) |
| Transfer con date fuori ordine | **Alta** | Già supportato dal modello dati (nessun vincolo di uguaglianza data tra le gambe) e già gestito concettualmente da `ScopeAwareTransactionClassifier` (ordinamento min/max indipendente dalla direzione) |
| Selezione multipla | **Alta** | `DataTable.svelte` supporta nativamente `selectionMode="multi"` e `onSelectionChange` |
| Modale Custodia | **Alta** | Nessun ostacolo tecnico; componente nuovo ma di complessità UI standard (nessun pattern esotico richiesto) |
| Sincronizzazione temporale WAC/Gantt | **Alta** | `buildDataZoom` + `echartsDataZoomSync.ts` già usati per la stessa sincronizzazione tra `AssetWacPriceChart` e `BubbleLotTimeline` oggi |
| POST bulk con più analisi e caricamenti DB raggruppati | **Alta come pattern, media come implementazione** | Pattern architetturale (`get_report()`/`PortfolioReportQuery`) già collaudato; l'implementazione del loader multi-broker/multi-analisi è comunque lavoro nuovo non banale (deve evitare l'N+1 di `get_asset_history()`) |
| Prezzi e conversioni FX nello stesso endpoint | **Alta** | Il Portfolio Engine già bulk-carica prezzi/FX con query `IN(...)` (documentato nel Report 4); stesso pattern riusabile per il nuovo loader |

---

## 8. Identità lotti, ordinamento same-day, range, complessità, query, riconciliazione

- **Identità lotto**: `id_i = origin_transaction_id` è naturale, stabile, già garantito dal DB (PK autoincrementante mai riusata) — **nessun problema**. **Identità frammento**: da definire esplicitamente, raccomandazione `f"{lot_id}:{sequence_index}"` (Criticità §7.4).
- **Ordinamento same-day**: `(date, id)` — convenzione già usata in 3+ punti indipendenti del codice reale, il piano la eredita correttamente senza introdurre nulla di nuovo.
- **Range di calcolo vs visualizzazione**: il piano è esplicito e corretto (§A.16: "il calcolo viene effettuato dall'inizio della storia; il range limita esclusivamente il materiale visualizzato") — identico alla filosofia già in uso da `get_report()` (`date_from=None` sempre). Punto di attenzione non esplicitato dal piano: le analisi **VALUE_HISTORY/RETURN_HISTORY/PRICE_HISTORY** (serie giornaliere per i lotti selezionati) hanno una complessità diversa dalla ricostruzione lotti/frammenti — la ricostruzione FIFO deve sempre avvenire O(transazioni) dall'inception, ma la proiezione giornaliera per il grafico di confronto può essere limitata alla finestra di visualizzazione richiesta (`date_from`/`date_to`), **a condizione che** lo stato del lotto all'inizio della finestra sia già noto dal passaggio O(transazioni). Il piano non separa esplicitamente queste due classi di complessità — raccomando di farlo nella specifica implementativa per evitare che, per inerzia, anche le history vengano generate sempre dall'inception (con costo O(giorni totali × lotti selezionati) invece di O(giorni visualizzati × lotti selezionati)).
- **Complessità computazionale**: il nuovo motore, essendo event-sourced (itera sulle transazioni, non sui giorni), è **asintoticamente più leggero** del `DailyStateBuilder` esistente (che itera O(giorni civili)) — un beneficio collaterale positivo del design proposto, non esplicitamente rivendicato dal piano ma verificabile.
- **Numero di query**: oggi `get_lots()` = O(1+B) query (B=numero broker); `get_asset_history()` = O(1+1+B×P) query (P=punti prezzo, confermato ~2000 per caso realistico). Il nuovo endpoint bulk, se implementato secondo il pattern di `get_report()`, può realisticamente restare O(1) round-trip DB per tipo di dato (1 query transazioni multi-broker, 1 query prezzi bulk, 1 query FX bulk) — **ma questo richiede scrivere un nuovo loader**, non è gratuito: `_get_transactions()` esistente è a singolo broker e andrebbe generalizzata (Criticità/Matrice §5).
- **Strategia di riconciliazione col Portfolio Engine**: l'invariante `Σ_{i,j: b_{i,j}=b} q_{i,j}(t) = Q_{a,b}(t)` (dal `DailyPositionState.cumulative_qty` esistente) è testabile direttamente e dovrebbe essere un **test di non regressione permanente**, eseguito su ogni combinazione asset/broker/data nei dataset di test esistenti — condizionato alla risoluzione della Criticità §7.2 (`share_percentage`) e §7.3 (confini transito), altrimenti il test fallirebbe per ragioni note e non per bug reali.

---

## 9. Suggerimenti migliorativi

1. Adottare `id_i = origin_transaction_id` e `fragment_id = f"{lot_id}:{sequence_index}"` come schema di identità stabile (Criticità §7.4).
2. Applicare `share_percentage` "scale-at-source", nello stesso punto in cui l'Engine esistente lo fa (`tx_qty = tx.quantity * ctxn.share`), per coerenza cross-engine (Criticità §7.2).
3. Decidere esplicitamente la convenzione dei confini di data del transito, riallineandola a `InTransitInterval` oppure documentando/testando la divergenza (Criticità §7.3).
4. Trattare la correzione del bug SPLIT/WAC-doubling come dipendenza dichiarata di questo piano, non come debito tecnico silenzioso (Criticità §7.1) — eventualmente accompagnata da un piccolo affinamento UI che precompili `cost_basis_override` in modo cost-preserving per gli ADJUSTMENT collegati a SPLIT (§7.6).
5. Aggiungere un flag esplicito tipo `data_inconsistent`/`degraded` alla risposta per il caso "SELL eccede i lotti disponibili sul broker" invece di propagare un'eccezione non gestita (Criticità §7.7).
6. Riusare `_compute_tx_fingerprint`/`_compute_price_fingerprint` (già generiche e module-level) per le nuove cache dedicate, invece di scrivere nuova logica di fingerprint.
7. Riusare `ScopeAwareTransactionClassifier.get_needed_paired_ids()` per risolvere le gambe TRANSFER il cui partner è fuori dallo scope broker caricato.
8. Separare esplicitamente, nella specifica implementativa, la complessità O(transazioni, sempre dall'inception) della ricostruzione lotti/frammenti dalla complessità O(giorni visualizzati × lotti selezionati) delle history di confronto (§8), per non ereditare per inerzia il pattern "tutto dall'inception" anche dove non serve.
9. Introdurre una soglia soft (warning UI, non blocco) per selezioni molto ampie di lotti nel grafico di confronto (§A.11).
10. Definire un fallback esplicito e testato per il prezzo di riferimento ADJUSTMENT+ quando manca un punto prezzo esatto alla data di origine, riusando la convenzione già presente nell'Engine.

---

## 10. Dipendenze e prerequisiti

- **Bloccanti (da decidere prima di scrivere codice)**: schema id lotto/frammento (§7.4), politica `share_percentage` (§7.2), convenzione confini transito (§7.3).
- **Fortemente raccomandato in parallelo, non bloccante ma ad alto rischio di contraddizione visiva se rimandato**: fix del bug SPLIT/WAC-doubling (§7.1).
- **Nessuna dipendenza da modifiche al Portfolio Engine** — punto di forza del piano, confermato: zero rischio di regressione sul motore aggregato.
- **Dipendenza tecnica**: generalizzazione di `_get_transactions()` a multi-broker (o nuova funzione dedicata) per evitare N+1 nel loader bulk.
- **Dipendenza organizzativa**: aggiornamento della E2E gallery (`frontend/e2e/gallery.spec.ts`, ristrutturata in questa stessa sessione) una volta rimossi `BubbleLotTimeline`/`OpenLotsTable`/`ClosedLotsTable` e introdotti i nuovi componenti — gli screenshot di riferimento in `mkdocs_src/docs/gallery/*.md` andranno rigenerati.

---

## 11. Strategia di migrazione incrementale

Coerente con la raccomandazione già data nel Report 4 (Opzione B: nuovo `FifoLotEngine` puro isolato + drill-down lazy):

1. **Fase 0 — Fondamenta decisionali**: fissare le 3 policy critiche (§7.2, §7.3, §7.4) e decidere il trattamento del bug SPLIT/WAC (§7.1). Nessun codice.
2. **Fase 1 — `FifoLotEngine` puro**: nessun I/O, input = `list[Transaction]` già caricata (stesso stile di `fifo_utils.py`), output = lotti+frammenti. Test esaustivi contro gli invarianti (§12) prima di qualunque integrazione DB.
3. **Fase 2 — Loader dati + DTO + endpoint**: nuova funzione di caricamento multi-broker/bulk-prezzi/bulk-FX (generalizzando `_get_transactions`), nuovi DTO (§5), `POST /portfolio/lots/analysis` ricalcando l'orchestrazione di `get_report()`.
4. **Fase 3 — Frontend**: tabella unificata (estensione `DataTable` con `selectionMode="multi"`), nuovo componente Gantt (custom series ECharts, pattern già padroneggiato), modale Custodia, grafico di confronto (variante di `AssetWacPriceChart` o nuovo componente), store `LotsAnalysisStore` (ispirato a `TimeSeriesStore`).
5. **Fase 4 — Switch-over e pulizia**: deprecare `get_lots()`/`calculate_fifo_lots()` come via pubblica (il modulo può restare come riferimento/test-vector matematico), rimuovere `OpenLotsTable`/`ClosedLotsTable`/`BubbleLotTimeline`, aggiornare i18n (nuove chiavi via `./dev.py i18n audit`), rigenerare screenshot E2E gallery.

Ogni fase corredata da test di non regressione numerica contro l'Engine aggregato esistente (invariante di riconciliazione, §8).

---

## 12. Test e invarianti necessari

1. **Riconciliazione quantità**: `Σ_{i,j: b_{i,j}=b} q_{i,j}(t) == Q_{a,b}(t)` (da `DailyPositionState.cumulative_qty`) per ogni combinazione asset/broker/data nei dataset di test — condizionato alla risoluzione di §7.2/§7.3.
2. **Conservazione costo split**: `q'·p0' == q·p0` per rapporti 2:1, 3:1, 1:2 (reverse split), e rapporti non interi.
3. **Transfer parziale/multiplo/di ritorno/in catena**: replica esatta degli esempi §A.5.1/§A.5.2 del piano — quantità finali per branch, custodia corretta, `lot_id` invariato attraverso i fork.
4. **Determinismo same-day**: due BUY (o un BUY+TRANSFER) nello stesso giorno, stesso asset, broker diversi — l'ordine di elaborazione deve essere stabile e riproducibile per `(date, id)`.
5. **Oversell/dato incoerente**: verificare esplicitamente il comportamento scelto (flag degradato vs eccezione, §7.7) — non lasciare il comportamento di default ereditato da `calculate_fifo_lots()`.
6. **`share_percentage`**: due utenti con quote 0.3/0.7 sullo stesso broker devono vedere quantità di lotto coerenti con la politica scelta (scale-at-source raccomandato).
7. **Complessità query**: asserzione automatica sul numero di query DB eseguite per una richiesta bulk — deve restare costante al crescere del numero di giorni/punti richiesti (guardia esplicita contro la regressione N+1 di `get_asset_history()`, §7.5).
8. **Cache invalidation**: fingerprint invalidato correttamente su insert/update/delete di transazioni collegate (incluse entrambe le gambe di un TRANSFER), su nuovi prezzi, su nuovi FX, su modifica di `share_percentage` — questi ultimi due sono gap di invalidazione già segnalati (non risolti) nel Report 4 ed ereditati qui.
9. **Partner mancante/cancellato**: una gamba TRANSFER con `related_transaction_id` pendente non deve produrre un crash, ma un trattamento difensivo esplicito (riuso del pattern già in `ScopeAwareTransactionClassifier.classify()`).

---

## 13. Rischi di regressione

- **Portfolio Engine (NAV/MWRR/3-pool)**: il piano lo lascia invariato (§11) — scelta corretta, **zero rischio** se rispettata. Base di test esistente sostanziale da preservare: `test_fifo_utils.py` (11 test), `test_portfolio_engine_vnext.py` (24 test), `test_portfolio_wac.py` (9 test), `test_wac_inline.py` (15 test), più la directory `test_portfolio_engine/` (`test_cash_decomposition.py`, `test_daily_state_builder.py`, `test_data_quality_report.py`, `test_scope_classifier.py`).
- **`calculate_fifo_lots()`**: uso confermato limitato a `get_lots()` — blast radius noto e contenuto in caso di rimozione.
- **E2E gallery**: la rimozione di `BubbleLotTimeline`/`OpenLotsTable`/`ClosedLotsTable` impatta gli screenshot regression già presenti in `frontend/e2e/gallery.spec.ts` (ristrutturato in questa stessa sessione) e i riferimenti in `mkdocs_src/docs/gallery/desktop.en.md`/`mobile.en.md` — da aggiornare in Fase 4, non dimenticare.
- **Bug SPLIT/WAC-doubling**: se non affrontato, resta un rischio di regressione *percepita* (contraddizione visiva tra le due viste) anche se il codice del nuovo motore è corretto.

---

## 14. Note sulla cache (indicazioni, non design definitivo)

Come richiesto, nessun design di cache definitivo. Riprendo e confermo le indicazioni già proposte nel Report 4, applicate a questo piano specifico:

- **Dove servirebbe**: (a) risultato della ricostruzione lotti/frammenti per asset+scope broker (cache dedicata nuova, es. `_lots_gantt_cache`); (b) history giornaliera per lotto/selezione (cache dedicata nuova, es. `_lot_history_cache`, TTL più breve data la natura on-demand).
- **Cosa NON riusare**: `_wac_cache` (rischio di thrashing già documentato, chiave troppo granulare per punto-prezzo), `_portfolio_blob_cache` (formato risultato incompatibile, pensato per lo stato aggregato giorno-per-giorno).
- **Misure da raccogliere per l'invalidazione**: fingerprint transazioni rilevanti per l'asset (riusando `_compute_tx_fingerprint`, ma ristretto alle transazioni BUY/SELL/TRANSFER/ADJUSTMENT dell'asset, non tutto il broker), fingerprint prezzi (riusando `_compute_price_fingerprint` esistente), fingerprint FX (**gap**: non esiste oggi in nessuna cache del sistema, ereditato dal Report 4), fingerprint `share_percentage` (**gap**: non esiste oggi in nessuna cache, ereditato dal Report 4).
- **Eventi di invalidazione necessari**: CRUD transazioni sull'asset (in qualunque broker collegato via TRANSFER), CRUD prezzi, CRUD FX, modifica `share_percentage`, modifica/cancellazione di un `AssetEvent` di tipo SPLIT collegato a un ADJUSTMENT già lottizzato.

---

## 15. Raccomandazione finale

### **GO CON MODIFICHE**

Il modello matematico proposto è solido, autoconsistente, e in larga parte già allineato con le convenzioni reali del codebase (ordinamento, non-fusione same-day, separazione FIFO/WAC, pattern di richiesta bulk). I componenti di base necessari — DataTable con selezione multipla, ECharts 6 con custom series già in uso altrove, helper di sincronizzazione zoom, tooling i18n — esistono già e riducono sostanzialmente il rischio di esecuzione. Nessuna modifica al Portfolio Engine aggregato è richiesta, eliminando il rischio più pericoloso (regressione su NAV/MWRR/3-pool, protetto da ~60 test esistenti).

Le condizioni per procedere in sicurezza sono:

1. Risolvere esplicitamente, **prima** di scrivere il `FifoLotEngine`, le 3 decisioni fondanti: schema identità frammento (§7.4), politica `share_percentage` (§7.2), convenzione confini transito (§7.3).
2. Dichiarare esplicitamente il trattamento del bug SPLIT/WAC-doubling preesistente (§7.1) come dipendenza del piano, non come debito tecnico ignorato — altrimenti il piano produrrà una contraddizione visiva garantita nel caso d'uso "stock split", che è comune, non raro.
3. Progettare il loader bulk evitando esplicitamente (con un test di guardia dedicato) il pattern N+1 già presente in `get_asset_history()`.

Con queste 3 condizioni soddisfatte, il piano è implementabile con rischio contenuto, riusando una quota significativa di infrastruttura già collaudata.

---

## 16. Domande residue che richiedono una decisione dell'utente

1. **Schema identità frammento**: si conferma `f"{lot_id}:{sequence_index}"` (proposta §7.4/§9) o si preferisce un'altra convenzione (es. UUID deterministico)?
2. **`share_percentage`**: si conferma la politica "scale-at-source" (stessa dell'Engine aggregato, proposta §7.2), oppure si preferisce mostrare la quantità piena del broker con la quota applicata solo a valore/P&L?
3. **Confine giorno del transito**: allineare il nuovo motore alla convenzione già in produzione (`InTransitInterval`: `[departure+1, arrival-1]`) per garantire riconciliazione esatta con l'Engine aggregato, oppure mantenere la convenzione più pulita del piano (`[min,max)`) accettando un disallineamento noto e documentato di 1-2 giorni?
4. **Bug SPLIT/WAC-doubling**: risolverlo come parte di questo stesso lavoro (raccomandato, per evitare la contraddizione visiva descritta in §7.1), oppure trattarlo esplicitamente come debito tecnico separato con un piano dedicato? Se separato, con quale priorità rispetto al FifoLotEngine?
5. **Comportamento su oversell/dato incoerente**: errore bloccante come oggi (`ValueError` non gestita), oppure vista degradata con flag esplicito (raccomandato, §7.7)?
6. **Sequenza di lavoro**: procedere prima con l'engine puro isolato e i suoi test (Fase 1, raccomandato anche nel Report 4), oppure parallelizzare da subito anche API e frontend?
7. **Timeline per lo short selling**: il piano lo rimanda esplicitamente (§12) — quando riprenderlo, e con quale relazione rispetto ai flag `allow_asset_shorting` già esistenti a livello broker?
8. **Limite pratico di selezione multipla** (§A.11): si accetta l'assenza di limite dichiarata dal piano con un semplice warning UI per selezioni molto ampie, o si preferisce un cap tecnico esplicito?

---

*Fine report. Nessuna modifica al codice sorgente né al documento di piano originale è stata effettuata durante questa analisi.*
