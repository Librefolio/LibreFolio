# FIFO segments — prezzi, adjustment, transfer e short positions

> **Stato**: Analisi tecnica critica. Nessuna modifica al codice applicata. Nessuna proposta di UI.
> **Data**: 2026-07-15
> **Documenti collegati** (stessa cartella): `REPORT-fifo-lots-transfer-mismatch.md` (sintomi osservati in UI), `fifo-engine-current-state.md` (motore FIFO/WAC, cost_basis_override, opzioni di redesign per i TRANSFER). Questo documento **estende** l'analisi a: modello di segmento/lotto, ADJUSTMENT (positivo e negativo), eventi asset, shorting/leva. Dove i due documenti si sovrappongono (es. semantica di `cost_basis_override`), qui si cita il risultato già verificato senza ripeterne la dimostrazione completa.
>
> **Nota sul percorso**: la richiesta originale indicava `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/Milestone_3/fifo-engine/`, ma quella cartella non esiste più — è stata effettivamente *spostata* (non copiata) in `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/` (= `LibreFolio_devWiki/corpus/roadmap/fifo-engine/` via symlink), dove risiedono già gli altri due report. Questo documento è stato salvato lì per non frammentare la documentazione tra due cartelle.

---

## Indice

0. [Mappa dello stato attuale (sommario)](#0-mappa-dello-stato-attuale-sommario)
1. [Ipotesi 1 — Campi identificativi di un lotto/segmento](#ipotesi-1--campi-identificativi-di-un-lottosegmento)
2. [Ipotesi 2 — Fusione di BUY nello stesso giorno](#ipotesi-2--fusione-di-buy-nello-stesso-giorno)
3. [Ipotesi 3-4 — original_unit_price vs costo fiscale, e cost_basis_override come secondo campo](#ipotesi-3-4--original_unit_price-vs-costo-fiscale-e-cost_basis_override-come-secondo-campo)
4. [Ipotesi 5 — Quale prezzo deve usare FIFO/P&L realizzato](#ipotesi-5--quale-prezzo-deve-usare-fifop38l-realizzato)
5. [Ipotesi 6 — Il ruolo reale del WAC](#ipotesi-6--il-ruolo-reale-del-wac)
6. [Ipotesi 7 — BUY e ADJUSTMENT positivi](#ipotesi-7--buy-e-adjustment-positivi)
7. [Ipotesi 8 — TRANSFER](#ipotesi-8--transfer)
8. [Ipotesi 9 — ADJUSTMENT negativo](#ipotesi-9--adjustment-negativo)
9. [Ipotesi 10 — Eventi asset collegati](#ipotesi-10--eventi-asset-collegati)
10. [Ipotesi 11 — Shorting/leva](#ipotesi-11--shortingleva)
11. [Ambiguità semantiche (elenco consolidato)](#11-ambiguità-semantiche-elenco-consolidato)
12. [Modello di segmento consigliato (long e short)](#12-modello-di-segmento-consigliato-long-e-short)
13. [Naming consigliato](#13-naming-consigliato)
14. [Invarianti e test necessari](#14-invarianti-e-test-necessari)

---

## 0. Mappa dello stato attuale (sommario)

| Sottosistema | File | Filtra per tipo transazione? | Gestisce TRANSFER? | Gestisce ADJUSTMENT? | Gestisce short (qty<0 su pool vuoto)? |
|---|---|---|---|---|---|
| `calculate_fifo_lots()` (motore puro) | `fifo_utils.py` | Sì, solo BUY/SELL (hardcoded) | No | No | **No — lancia eccezione** |
| `get_lots()` (Open Lots / FIFO panel) | `portfolio_service.py:2331` | Sì (`_HOLDING_TYPES={BUY,SELL}`) | **No** | **No** | **No — eccezione non catturata, probabile 500** |
| `compute_wac_from_txlist()` (motore WAC puro) | `wac_utils.py` | No | Sì | Sì | Clamp silenzioso a zero (nessuna eccezione, nessun pool negativo) |
| `compute_wac_iterative()` | `portfolio_service.py:97` | No | Sì | Sì | Eredita il clamp del motore puro |
| `PortfolioEngine`/`DailyStateBuilder` | `portfolio_engine.py` | No | Sì | Sì | Da verificare punto per punto (§10) — usa `max(qty, 0)` in più punti |
| `get_positions_contribution()` | `portfolio_service.py:1593` | Sì (`_QTY_TYPES={BUY,SELL}`) | No (già segnalato nel report precedente, §7.4) | **No (nuovo finding)** | N/A |
| Balance-walk (validazione business) | `transaction_service.py:440` | No | Sì | Sì | **Blocca esplicitamente** se `allow_asset_shorting=False`, altrimenti permette |

**Sintesi**: il motore FIFO puro e `get_lots()` sono gli **unici due componenti** che (a) filtrano rigidamente su BUY/SELL escludendo sia TRANSFER **sia ADJUSTMENT**, e (b) non hanno alcuna gestione esplicita di quantità negative/shorting (l'eccezione non è mai catturata a questo livello). Tutti gli altri sottosistemi già gestiscono TRANSFER e ADJUSTMENT in modo omogeneo (nessun filtro di tipo), confermando che il problema è isolato architettonicamente, non diffuso.

---

## Ipotesi 1 — Campi identificativi di un lotto/segmento

> *"Un lotto/segmento raggruppa quantità dello stesso asset con: stessa data di origine; stesso prezzo unitario originario. Valutare se servano anche broker, valuta, transazione origine e tipo origine."*

**Verifica sullo schema attuale** (`OpenLotSchema`, `backend/app/schemas/portfolio.py:455-464`):
```python
class OpenLotSchema(BaseModel):
    buy_transaction_id: int    # transazione di origine — GIÀ PRESENTE
    broker_id: int              # broker — GIÀ PRESENTE (ma oggi = "broker del BUY", mai aggiornato da transfer)
    buy_date: date_type          # data di origine — GIÀ PRESENTE
    buy_price: SafeDecimal        # prezzo unitario originario — GIÀ PRESENTE
    original_quantity: SafeDecimal
    remaining_quantity: SafeDecimal
    unrealized_pnl: Optional[SafeDecimal]
```
**Non presenti**: `currency` (valuta del prezzo unitario — implicita, non esposta nello schema; il motore puro `FIFOTransactionInput.price` è un `Decimal` senza valuta associata, la valuta è gestita SOLO a monte, nel layer di preparazione WAC, non nel motore FIFO), `origin_type` (tipo della transazione di origine — oggi implicito, dato che `get_lots()` alimenta il motore solo con BUY, quindi il "tipo" è sempre "BUY" per costruzione; se si estende a TRANSFER/ADJUSTMENT come proposto nel report precedente, distinguere il tipo di origine diventa necessario per interpretare correttamente `buy_price` — es. un prezzo "ereditato" da `cost_basis_override` ha una natura diversa da un prezzo derivato da `amount/quantity`).

**Verdetto**: **ipotesi confermata come necessaria, con un campo aggiuntivo da aggiungere esplicitamente**. Broker è già presente (ma semanticamente sbagliato, vedi report precedente); valuta e tipo-origine **non sono oggi rappresentati esplicitamente nel lotto** e andrebbero aggiunti in un redesign, per i motivi seguenti:
- **Valuta**: un lotto comprato in EUR e uno in USD per lo stesso asset (possibile con conti multi-valuta) non sono direttamente comparabili senza sapere la valuta del prezzo — oggi questa informazione esiste a monte (sulla riga `Transaction.currency`) ma si perde nel passaggio a `FIFOTransactionInput.price` (un `Decimal` puro).
- **Tipo origine**: necessario per sapere se `buy_price` è un prezzo di mercato reale (BUY) o un valore "congelato"/derivato (`cost_basis_override` da TRANSFER, o da ADJUSTMENT con `cost_basis_mode=auto`) — la distinzione è rilevante per la trasparenza verso l'utente e per capire se un lotto "eredita" un costo da un'altra transazione piuttosto che averlo determinato autonomamente.

---

## Ipotesi 2 — Fusione di BUY nello stesso giorno

> *"Più BUY dello stesso giorno si fondono solo se il prezzo unitario è identico; altrimenti restano lotti separati."*

**Verifica su codice reale** (`fifo_utils.py:97-99`):
```python
for tx in sorted_txs:
    if tx.type == "BUY":
        buy_queue.append([tx, tx.quantity])   # SEMPRE un nuovo elemento, nessun controllo di fusione
```
**Nessuna logica di fusione esiste oggi, a nessuna condizione.** Due BUY nello stesso giorno, anche a **prezzo identico**, generano **due elementi separati** nella coda (`open_lots` conterrà due righe con `buy_date` e `buy_price` identici ma `buy_transaction_id` diversi).

**Verdetto: ipotesi SMENTITA come descrizione del comportamento attuale.** Non è vero che "si fondono se il prezzo è identico" — oggi **non si fondono mai**, indipendentemente dal prezzo.

**Conseguenze pratiche della non-fusione** (per valutare se la fusione proposta sia desiderabile):
- **FIFO order**: `sorted_txs = sorted(..., key=lambda t: (t.date, t.id))` — a parità di data, l'ordine è per `id` crescente. Se due BUY hanno prezzo diverso, l'ordine di consumo FIFO **dipende dall'ordine di inserimento in DB**, non da un criterio esplicito (es. ora del giorno, se disponibile) — punto di attenzione se si vuole un ordinamento deterministico "intra-day" più preciso.
- **Se fossero fuse** (stesso giorno, stesso prezzo): il risultato del consumo FIFO sarebbe **matematicamente identico** in termini di quantità totale consumata e P&L realizzato aggregato (la fusione di due lotti adiacenti con lo stesso prezzo non altera l'ordine né il costo di alcuna vendita successiva). **Cambierebbe solo**: (a) il numero di righe visualizzate in "Open Lots" (1 invece di 2), (b) la tracciabilità per singola transazione di origine (un lotto fuso non potrebbe più puntare a un singolo `buy_transaction_id` — servirebbe una lista, o si perderebbe la granularità).
- **Se il prezzo è diverso**: la fusione **non deve avvenire** (l'ipotesi lo riconosce correttamente) — fondere prezzi diversi produrrebbe un lotto con un prezzo "medio" che non è più un vero prezzo di acquisto storico, snaturando il modello FIFO (che per definizione richiede lotti a prezzo puro, non mediato — la media è compito del WAC, un concetto distinto).

---

## Ipotesi 3-4 — `original_unit_price` vs costo fiscale, e `cost_basis_override` come secondo campo

> *"Distinguere nel lotto: `original_unit_price` (costo storico effettivo di acquisizione); `tax_unit_cost` o altro nome (costo fiscalmente riconosciuto dopo transfer, successione, step-up o override). Verificare se il DB possiede già dati sufficienti e se `cost_basis_override` può rappresentare il secondo campo."*

**Verifica**: il DB **possiede già, per ogni transazione**, sia il dato per ricostruire il "costo storico effettivo" (`amount`/`quantity` per un BUY) sia un campo dedicato esplicitamente al "costo congelato" (`cost_basis_override`, `cost_basis_currency` — vedi `fifo-engine-current-state.md` §5-6 per la dimostrazione triplice che è un valore **per-unità**). **Nessuna migrazione DB è necessaria per rappresentare il secondo campo — esiste già.**

**Ma attenzione a una distinzione cruciale che l'ipotesi rischia di appiattire**: `cost_basis_override` oggi **non è un "costo fiscale" in senso stretto** — è descritto nel modello come "Frozen cost basis for TRANSFER_IN" con scopo dichiarato *anche* di rappresentare basi imponibili diverse dal costo storico (l'esempio esplicito nel codice è "Exit Tax, inheritances use market value" — `models.py:653`), ma la sua **implementazione attuale lo tratta sempre come "il prezzo/costo da usare per questo lotto da questo momento in poi"**, senza distinguere se il motivo è:
(a) **puramente tecnico** (snapshot del WAC sorgente per evitare di interrogare a ritroso — non è un evento fiscale, è solo un'ottimizzazione/architettura di persistenza), oppure
(b) **genuinamente fiscale** (l'utente ha scelto un valore diverso dal WAC per motivi di step-up/successione).

**Oggi il sistema non distingue questi due casi con un flag o un campo separato** — entrambi finiscono nello stesso `cost_basis_override`. Questo significa che, se in futuro si volesse calcolare **sia** una performance economica (basata sul costo storico reale) **sia** una plusvalenza fiscale (basata sul valore riconosciuto ai fini fiscali, che può differire), **un solo campo non è sufficiente per distinguere i due casi con certezza**: non si può oggi rispondere in automatico alla domanda "questo `cost_basis_override` è uguale al costo storico per puro caso (transfer semplice, nessun evento fiscale) o è deliberatamente diverso per uno step-up?" — bisognerebbe confrontare il valore con il WAC storico "ricostruito" per inferirlo indirettamente, oppure aggiungere un flag esplicito.

**Verdetto**:
- **`original_unit_price`** (costo storico effettivo): **non esiste come campo dedicato oggi** — è sempre *derivato al volo* da `amount/quantity` per un BUY, o *perso* per un TRANSFER (l'unica cosa che sopravvive è `cost_basis_override`, che PUÒ coincidere col costo storico originale della catena di trasferimenti, ma nel DB attuale non c'è modo di risalire al valore originario "puro" senza attraversare a ritroso l'intera catena di transfer fino al BUY radice — operazione oggi possibile solo interrogando manualmente `related_transaction_id` a ritroso più volte, non automatizzata).
- **`cost_basis_override` può rappresentare il secondo campo** (costo fiscale/riconosciuto) **con una riserva importante**: oggi fa da **contenitore unico** sia per il caso "tecnico" (snapshot transfer semplice) sia per il caso "fiscale" (override manuale) — se si vuole distinguerli con certezza in un redesign, servirebbe un **flag booleano aggiuntivo** (es. "è un valore fiscale intenzionalmente diverso dal costo storico, o è solo la propagazione tecnica del WAC?"), non necessariamente un terzo campo Decimal — un bit di metadato può bastare. Il campo `cost_basis_mode` (`"auto" | "manual" | "auto-detail"`) già esistente è un **buon punto di partenza concettuale** (distingue "calcolato automaticamente" da "impostato manualmente dall'utente"), ma **oggi si applica solo al momento della creazione della transazione, non è persistito come metadato permanente sul valore finale salvato in `cost_basis_override`** — una volta scritto il valore nel DB, la distinzione `auto`/`manual` che l'ha generato **non è conservata da nessuna parte** (verificato: `cost_basis_mode` non è una colonna del modello `Transaction`, è solo un campo dello schema di INPUT usato al momento della creazione/update).

---

## Ipotesi 5 — Quale prezzo deve usare FIFO/P&L realizzato

> *"Verificare se FIFO e P&L realizzato debbano usare il prezzo originario oppure il costo fiscalmente riconosciuto. Non assumere che il prezzo originario sia corretto: distinguere performance economica e plus/minusvalenza fiscale."*

**Cosa fa oggi il codice, verificato**:
- `calculate_fifo_lots()` — il motore puro usa **un solo prezzo per lotto** (`buy_price`), qualunque esso sia stato al momento della costruzione dell'input. Non esiste alcuna distinzione tra "prezzo economico" e "prezzo fiscale" — il motore è **agnostico**: usa ciecamente il valore che gli viene passato.
- `get_positions_contribution()` (P&L realizzato in produzione, §7.4 del report precedente + qui) — usa **il WAC** (calcolato da `compute_wac_iterative`, che a sua volta usa `cost_basis_override` quando presente) per calcolare `realized_pnl = sell_proceeds - (sell_qty × wac_at_sell)`. **Questo è, oggi, il "costo riconosciuto" (che coincide con `cost_basis_override` se il lotto proviene da un transfer), non necessariamente il costo storico originario della catena.**

**Conseguenza pratica, con esempio numerico**: se un asset è stato comprato a 100, trasferito (con `cost_basis_override` "manuale" impostato a 150 per un motivo fiscale — es. valore di mercato al momento di una successione), e poi venduto a 200:
```
P&L "economico" (se si usasse il costo storico originario, 100): (200 - 100) × qty = 100 × qty
P&L "fiscale" (usando cost_basis_override = 150, come fa OGGI il sistema): (200 - 150) × qty = 50 × qty
```
**Oggi il sistema calcola SEMPRE la seconda cifra (50×qty), mai la prima, e non conserva l'informazione per calcolare la prima a posteriori se il costo storico originario non è più direttamente osservabile** (nell'esempio, si perderebbe la traccia del "100" originale una volta che `cost_basis_override=150` sostituisce il calcolo automatico — a meno di risalire manualmente la catena `related_transaction_id` fino al BUY radice, cosa che nessuna funzione esistente fa automaticamente).

**Verdetto**: l'ipotesi è **fondata e la sua premessa è verificata come vera nel codice attuale — il sistema oggi calcola SOLO una delle due cifre (quella "fiscale"/riconosciuta) e non conserva l'altra in modo interrogabile**. Se si vuole distinguere "performance economica" da "plusvalenza fiscale" come due concetti paralleli e sempre disponibili, è necessario **conservare esplicitamente sia il costo storico originario (risalendo la catena di transfer una sola volta, alla creazione, non ricalcolandolo ad ogni query) sia il costo riconosciuto**, esattamente come proposto nell'ipotesi 3.

---

## Ipotesi 6 — Il ruolo reale del WAC

> *"Verificare il ruolo reale del WAC: book value; WAC del broker; realized gain/loss; fiscalità; transfer; eventuali usi ulteriori."*

Verifica sistematica di ogni singolo uso di `compute_wac_iterative`/`compute_wac_from_txlist`/pool-WAC nel codice:

| Uso | Confermato? | Dove |
|---|---|---|
| **Book value / cost basis della posizione aperta** | ✅ Sì | `PortfolioEngine._build_position_state()`: `cost_basis = wac_val * qty` (`portfolio_engine.py:1006`) — usato per calcolare `unrealized_pnl = mv - cost_basis` |
| **WAC "del broker" (per-broker, non aggregato)** | ✅ Sì | Sia `compute_wac_iterative(broker_id=...)` sia il pool `wac_pool_qty/cost` in `PortfolioEngine` sono sempre chiavati per `(asset_id, broker_id)` — non esiste un "WAC globale cross-broker" calcolato direttamente; se serve, va aggregato a posteriori pesando per quantità |
| **Realized gain/loss** | ✅ Sì | `get_positions_contribution()`: `cost_sold = sell_qty * wac_at_sell_base; realized += sell_proceeds - cost_sold` (righe ~1698-1712) — usa il WAC **alla data della vendita**, escludendo la vendita stessa dal calcolo (`excluded_tx_ids=[tx.id]`) |
| **Fiscalità (in senso di calcolo dell'imposta)** | ⚠️ **Indirettamente, non esplicitamente** | Il sistema non ha un concetto di "plusvalenza fiscale" distinto da "plusvalenza economica" (vedi Ipotesi 5) — il WAC calcolato è usato **come se fosse** anche il valore fiscale, ma non c'è una funzione o un report dedicato a "calcolo imposte" che lo consumi con logica fiscale specifica (es. aliquote, esenzioni, compensazione minus/plus). Il termine "fiscalità" nell'ipotesi originale sembra riferirsi più alla *plausibilità* che il WAC venga *usato* a fini fiscali dall'utente finale (per compilare la propria dichiarazione), non a una funzionalità di calcolo fiscale nel software |
| **Transfer (snapshot alla creazione)** | ✅ Sì | `_compute_wac_for_auto_items()`: calcola il WAC del broker sorgente e lo scrive in `cost_basis_override` della gamba IN (`transaction_service.py:1591-1604`) — vedi `fifo-engine-current-state.md` §5.3 |
| **Preview interattivo per l'utente (WAC "in diretta" mentre si compila un form)** | ✅ Sì, uso ulteriore non elencato nell'ipotesi | `WACPreviewResultItem` (schema dedicato) e l'intera famiglia "auto"/"auto-detail" di `cost_basis_mode` servono a mostrare all'utente, **prima del salvataggio**, quale sarebbe il WAC risultante — usato nel form di creazione TRANSFER/ADJUSTMENT lato frontend |
| **Cache del motore Portfolio** (uso tecnico, non di business) | ✅ Sì, uso ulteriore | `_compute_price_fingerprint()` (`portfolio_engine.py:1868`) usa indirettamente la presenza di aggiornamenti WAC/prezzo come proxy di invalidazione cache — non è un "ruolo" del WAC in senso finanziario, ma un suo effetto collaterale architetturale |

**Verdetto**: il WAC ha **almeno 6 ruoli distinti e verificati** nel codice, di cui l'ipotesi ne elencava 4 correttamente (book value, WAC broker, realized G/L, transfer) più uno assunto ma non verificabile come funzionalità dedicata ("fiscalità" — presente solo indirettamente/implicitamente, l'utente dovrebbe fare da sé i calcoli fiscali a partire dai numeri che il sistema fornisce) più due usi aggiuntivi non menzionati nell'ipotesi (preview interattivo, invalidazione cache).

---

## Ipotesi 7 — BUY e ADJUSTMENT positivi

> *"Derivazione del prezzo unitario da `abs(amount)/quantity`; fallback/override tramite WAC o `cost_basis_override`; comportamento con quantità frazionarie."*

**Verificato** (`PortfolioEngine._buy_unit_cost()`, `portfolio_engine.py:1207-1257`, già citato in `fifo-engine-current-state.md` §6):
```python
if tx.type == TransactionType.BUY:
    total_cost = abs(tx.amount)
    cost_ccy = tx.currency or asset_ccy
elif tx.cost_basis_override is not None:
    total_cost = tx.cost_basis_override * qty       # ADJUSTMENT positivo con override esplicito
    cost_ccy = tx.cost_basis_currency or asset_ccy
else:
    return None    # → trattato dal chiamante come "add at current WAC" (fallback)
unit_cost = total_cost / qty   # (dopo eventuale conversione FX)
```
**Confermato**: `unit_cost = abs(amount)/qty` per BUY; per ADJUSTMENT positivo, se presente `cost_basis_override` (per-unità) lo usa direttamente, altrimenti **fallback silenzioso a "aggiungi al WAC corrente del pool"** (nessun costo esplicito → l'aggiunta non altera il WAC per-unità, ma **aumenta il costo totale proporzionalmente alla quantità aggiunta**, vedi discussione critica sotto).

**Quantità frazionarie**: nessuna gestione speciale — la divisione `total_cost/qty` funziona identicamente per `qty=0.15` o `qty=15.0` (aritmetica `Decimal` standard, 6 decimali di precisione DB). **Nessun problema di arrotondamento sistemico riscontrato nel codice per quantità frazionarie in sé** — l'unico rischio di arrotondamento è quello generico di qualunque divisione (residui su Decimal), già mitigato da `truncate_priceHistory`-style helper altrove nel codice per i prezzi storici (non per i lotti/WAC, dove si usa `Decimal` a piena precisione senza troncamento esplicito, verificato assente in `wac_utils.py`/`fifo_utils.py`).

**Ambiguità critica scoperta durante questa verifica (non esplicitamente richiesta dall'ipotesi, ma emersa naturalmente)**: il fallback "add at current WAC" (`cost_basis_mode="auto"` senza override, o ADJUSTMENT senza `cost_basis_override`) è **corretto per un TRANSFER** (dove si vuole che l'arrivo di quantità non alteri il WAC-per-unità, dato che il costo TOTALE trasferito è già "giusto" per definizione — si sposta valore, non se ne crea), **ma è POTENZIALMENTE SCORRETTO se usato per rappresentare uno SPLIT tramite ADJUSTMENT positivo**:

**Esempio numerico — perché "add at current WAC" è sbagliato per uno split 2:1**:
```
Posizione preesistente: 15 azioni, WAC=100, costo totale=1500
Split 2:1 → utente crea ADJUSTMENT +15 (per arrivare a 30 azioni totali)

Se cost_basis_mode="auto" (add at current WAC=100):
  nuova_qty = 15 + 15 = 30
  wac = (100×15 + 100×15) / 30 = 3000/30 = 100        ← WAC-per-unità INVARIATO (sbagliato per uno split!)
  costo totale implicito = 100 × 30 = 3000             ← RADDOPPIATO (sbagliato: un split non crea valore!)

Comportamento CORRETTO per un vero split 2:1 (dimezzare il prezzo, raddoppiare la quantità, costo totale invariato):
  nuova_qty = 30
  wac_corretto = 1500 / 30 = 50                         ← dimezzato, come deve essere
  costo totale = 50 × 30 = 1500                          ← invariato, corretto
```
**Il fallback "auto" del sistema, se usato ingenuamente per un ADJUSTMENT che rappresenta uno split, produce un costo totale raddoppiato (o comunque gonfiato in proporzione al rapporto di split) invece di rimanere invariato.** Per ottenere il comportamento corretto, l'utente dovrebbe usare `cost_basis_mode="manual"` e impostare esplicitamente `cost_basis_override = WAC_precedente / rapporto_di_split` (nell'esempio: 100/2=50) — **un calcolo che il sistema non suggerisce né automatizza in alcun modo** (coerente con quanto verificato in Ipotesi 10: gli AssetEvent di tipo SPLIT sono solo "candidati suggeriti" per data, il valore/rapporto numerico non viene mai tradotto automaticamente in un `cost_basis_override` corretto).

---

## Ipotesi 8 — TRANSFER

> *"Consuma FIFO sul broker sorgente; trasferisce quantità senza realizzo; preserva prezzo/data originari; l'override aggiorna esclusivamente il costo fiscale/contabile."*

**Punto per punto, verificato**:

1. **"Consuma FIFO sul broker sorgente"** — ❌ **Non verificato come comportamento attuale in `get_lots()`** (che non processa affatto i TRANSFER, vedi report precedente). ✅ **Verificato come comportamento del pool WAC** (`compute_wac_from_txlist`/`PortfolioEngine`): un TRANSFER OUT riduce il pool "a coda" nel senso di "esce al costo medio corrente", ma **non è un vero consumo FIFO lotto-per-lotto** — è un consumo *a pool aggregato* (media, non identità di lotto). La differenza è sostanziale se il pool sorgente ha più lotti a prezzi diversi (vedi discussione multi-lotto in `fifo-engine-current-state.md` §9.3): oggi **nessun componente esistente traccia "quale lotto specifico" viene consumato da un TRANSFER**, perché nessun componente traccia lotti multipli per broker fuori da `get_lots()` (che a sua volta non vede i transfer).
2. **"Trasferisce quantità senza realizzo"** — ✅ **Confermato**: `amount=0` sempre per TRANSFER (vincolo di modello), e la riduzione nel pool WAC esce "al WAC corrente" (nessun P&L generato all'interno di `compute_wac_from_txlist`). Il realizzo, dove calcolato (`get_positions_contribution`), è **filtrato esplicitamente solo per `TransactionType.SELL`** (`if tx.type != TransactionType.SELL: continue`) — un TRANSFER non genera mai una riga di realized P&L in quel flusso.
3. **"Preserva prezzo/data originari"** — ⚠️ **Parzialmente verificato, con una sottigliezza importante**: il **prezzo** (`cost_basis_override`) è preservato SE calcolato in modalità "auto" al momento della creazione (snapshot del WAC sorgente) — ma la **data** usata per quello snapshot è `db_tx.date` (**la data del transfer**, non la data del BUY originario) — verificato in `_compute_wac_for_auto_items`: `as_of_date=db_tx.date`. Questo significa: **il valore del prezzo può essere "quello giusto" (eredita correttamente il WAC storico), ma nessun campo persiste esplicitamente "la data di acquisto originaria"** — quella informazione, oggi, **esiste solo implicitamente** risalendo `related_transaction_id` fino al BUY radice (operazione manuale, non automatizzata da nessuna funzione esistente).
4. **"L'override aggiorna esclusivamente il costo fiscale/contabile"** — ✅ **Confermato nella sua accezione tecnica**: modificare `cost_basis_override` non altera in alcun modo la quantità (`quantity` resta quella originaria del TRANSFER) né alcun altro campo — è isolato al costo. Ma vedi Ipotesi 3-4 per la riserva sulla distinzione "fiscale" vs "tecnico".

---

## Ipotesi 9 — ADJUSTMENT negativo

> *"Verificare campi e validazioni disponibili; può avere WAC/override? Oggi genera cash o no? Deve consumare FIFO senza realizzo, essere trattato come vendita a ricavo zero, o dipendere dall'evento asset? Mostrare le conseguenze matematiche di ogni scelta."*

**Campi e validazioni**:
- `amount = 0` sempre (vincolo di modello — **non genera mai cash**, identico a TRANSFER, confermato dalla docstring `TransactionType` righe 221-224: *"ADJUSTMENT: ... amount = 0"*).
- `_requires_cost_basis()` (`transaction_service.py:234-242`) richiede `cost_basis_override` **solo per `quantity > 0`** — un ADJUSTMENT **negativo non richiede né supporta esplicitamente `cost_basis_override`** nella validazione attuale (nessun controllo lo impedisce a livello di schema, ma la logica di business non lo richiede né lo popola mai automaticamente per una riduzione).
- **WAC**: sì, un ADJUSTMENT negativo **è già incluso** nelle query di `compute_wac_iterative()`/`PortfolioEngine` (nessun filtro di tipo, come verificato per i TRANSFER) — viene trattato come una **riduzione generica**, esce al WAC corrente, nessun P&L calcolato all'interno del motore WAC.
- **`get_lots()`**: come TRANSFER, un ADJUSTMENT (positivo o negativo) è **invisibile** perché `_HOLDING_TYPES={BUY,SELL}` lo esclude — questo è un finding aggiuntivo rispetto al report precedente: **il bug di `get_lots()` non è "specifico dei transfer", è "specifico di qualunque tipo diverso da BUY/SELL"**, ADJUSTMENT incluso.

**Le tre opzioni e le loro conseguenze matematiche** (con lo stesso esempio: posizione 15 unità @ WAC=100, ADJUSTMENT −5, prezzo di mercato corrente al momento dell'evento = 120):

| Opzione | Quantità residua | WAC dopo | Realized P&L generato | Cost basis residuo |
|---|---|---|---|---|
| **(a) Consuma FIFO senza realizzo** (come TRANSFER OUT — comportamento GIÀ ATTUALE nel motore WAC/PortfolioEngine, verificato) | 10 | 100 (invariato) | **0** | 1000 (10×100) |
| **(b) Vendita a ricavo zero** (pseudo-SELL con prezzo=0) | 10 | 100 (invariato, il WAC non cambia mai per una riduzione) | **−500** (perdita piena: (0−100)×5) | 1000 |
| **(c) Dipende dall'evento asset collegato** (es. se `asset_event_id` punta a un `PRICE_ADJUSTMENT` con `value` = nuovo prezzo di mercato, si potrebbe voler registrare un realizzo "nozionale" pari a `(value − wac) × qty_rimossa`) | 10 | 100 (invariato) | **variabile**: es. con `value=120`, `(120−100)×5=+100` di plusvalenza nozionale | 1000 |

**Osservazione critica**: le tre opzioni producono **P&L realizzato radicalmente diverso** (0 vs −500 vs +100 nell'esempio) **dallo stesso identico evento economico** — la scelta non è affatto neutra e ha impatto diretto su qualunque report di performance o (indirettamente) su una dichiarazione fiscale basata su questi numeri. **Il comportamento oggi effettivamente implementato nel motore WAC è l'opzione (a)** (per costruzione, essendo trattato come una generica riduzione) — ma **questo non è mai stato scelto esplicitamente per il caso ADJUSTMENT negativo**, è semplicemente l'effetto collaterale di non avere alcun filtro di tipo nel motore WAC. **Nessuna decisione di design esplicita risulta documentata nel codice per questo caso specifico.**

---

## Ipotesi 10 — Eventi asset collegati

> *"Dividendo, interesse, split, adeguamento prezzo e liquidazione. Spiegare come devono trasformare segmenti, quantità, prezzi e costi."*

**Finding principale, verificato nella docstring del modello** (`AssetEvent`, `models.py:743-745`):
> *"Events are NOT transactions — they describe what happens to the asset globally, not what happens in a user's portfolio. The portfolio reads these events for display, smart assistant suggestions, and ex-date price adjustments."*

**Nessun AssetEvent trasforma automaticamente segmenti/quantità/prezzi/costi di alcuna transazione utente.** La trasformazione, quando avviene, è sempre mediata da una transazione creata **manualmente dall'utente** (eventualmente assistito da un meccanismo di "suggerimento" per data — non di calcolo automatico del valore).

Verificato `suggest_events_bulk()` (`transaction_service.py:555-621`) e la mappa `EVENT_COMPATIBLE_TYPES` (`transactions.py:48-54`):

| Tipo di evento asset | Transazione utente compatibile | Il sistema calcola AUTOMATICAMENTE quantità/prezzo dall'evento? |
|---|---|---|
| `DIVIDEND` | `DIVIDEND` | Suggerisce solo la **data candidata**; l'importo (`value`) è mostrato ma l'utente deve confermare/inserire l'importo netto nella propria transazione (può differire per ritenute fiscali) |
| `INTEREST` | `INTEREST` | Idem — solo suggerimento di data/candidato |
| `PRICE_ADJUSTMENT` | `ADJUSTMENT` | Suggerisce solo la data; **nessuna traduzione automatica** del `value` dell'evento in una quantità o un `cost_basis_override` per la transazione ADJUSTMENT dell'utente |
| `SPLIT` | `ADJUSTMENT` | Idem — **il rapporto di split (es. 2:1) non viene mai automaticamente tradotto in "raddoppia la quantità, dimezza il costo unitario"** — vedi il rischio concreto dimostrato in Ipotesi 7 se l'utente usa il fallback "auto" invece di calcolare manualmente il `cost_basis_override` corretto |
| `MATURITY_SETTLEMENT` | **Nessuna** (non in `EVENT_COMPATIBLE_TYPES`) | Non suggerito ad alcuna transazione — è un evento puramente informativo/di prezzo, specifico del provider `scheduled_investment` (asset P2P/crowdfunding), che marca "fine dei punti prezzo generati" (`scheduled_investment.py:385-392`). L'utente deve registrare manualmente l'eventuale SELL/rimborso finale senza alcun collegamento automatico |

**Come DOVREBBERO trasformare segmenti/quantità/prezzi/costi** (ragionamento, non implementazione):
- **DIVIDEND/INTEREST**: non toccano MAI quantità o lotti (sono `quantity=0` per definizione di tipo) — impattano solo cassa. Nessuna trasformazione di segmento necessaria o corretta.
- **SPLIT**: dovrebbe, se automatizzato, **moltiplicare la quantità di OGNI lotto aperto per il rapporto di split e dividere il `buy_price` di ciascuno per lo stesso rapporto** (mantenendo il costo totale invariato per lotto) — **oggi nessuna funzione fa questo**: l'utente crea UN SOLO ADJUSTMENT aggregato (non uno per lotto), che il motore FIFO (se lo vedesse) tratterebbe come UN NUOVO LOTTO SEPARATO con un proprio prezzo (da calcolare manualmente), **non** come una trasformazione IN-PLACE dei lotti preesistenti. Questa è una differenza semantica profonda: "split come nuovo lotto a prezzo calcolato" vs "split come ridimensionamento di tutti i lotti esistenti" producono la stessa quantità/costo totale finale ma **rappresentazioni interne diverse** (numero di lotti, tracciabilità storica per singolo lotto pre-split).
- **PRICE_ADJUSTMENT** (svalutazione/rivalutazione non-cash): per definizione (`models.py:187`, "Non-cash value change") non dovrebbe generare né consumare quantità — semanticamente più vicino a un cambiamento del PREZZO DI MERCATO dell'asset (che vive in `PriceHistory`, non nei lotti) che a una modifica del COSTO DI ACQUISTO di un lotto. Se un utente lo registra come ADJUSTMENT (quantity-affecting), sta probabilmente confondendo due concetti distinti: valore di mercato (non tocca i lotti) vs costo fiscale riconosciuto (tocca `cost_basis_override`, non la quantità).
- **MATURITY_SETTLEMENT** ("liquidazione"): concettualmente è una SELL "forzata dall'esterno" (l'emittente rimborsa/liquida) — semanticamente dovrebbe generare un realizzo (P&L = valore di liquidazione − costo del lotto), esattamente come una SELL. Il fatto che oggi non sia nemmeno suggerita come candidato per nessun tipo di transazione (a differenza di SPLIT/PRICE_ADJUSTMENT/DIVIDEND/INTEREST) è una lacuna di UX più che di modello dati — l'utente deve sapere autonomamente di dover registrare una SELL a fronte di un evento di questo tipo.

---

## Ipotesi 11 — Shorting/leva

> *"Verificare i flag broker esistenti per cash e quantità negative; comportamento attuale di validation, WAC, FIFO e Portfolio Engine; definire cosa accade quando SELL/ADJUSTMENT OUT supera i lotti disponibili; valutare se una posizione short richieda lotti negativi separati."*

### 11.1 Flag broker esistenti — confermati

```python
# backend/app/db/models.py:399-400
allow_cash_overdraft: bool = Field(default=False, description="Allow leveraged buying (negative cash balance)")
allow_asset_shorting: bool = Field(default=False, description="Allow short selling (negative asset quantities)")
```
Entrambi **esistono già nel modello Broker**, con default `False` (comportamento conservativo: niente scoperto, niente short, di default).

### 11.2 Comportamento per componente, verificato

| Componente | Comportamento con quantità che andrebbe negativa |
|---|---|
| **Balance-walk validation** (`transaction_service.py:494-508`) | Se `allow_asset_shorting=False`: **rifiuta l'intero batch** con `BalanceValidationError` (codice `BALANCE_ASSET_NEGATIVE`) se il saldo cumulato giorno-per-giorno scende sotto zero. Se `allow_asset_shorting=True`: **nessun controllo, il saldo negativo è permesso senza ulteriori verifiche** — questo è l'**unico punto del sistema che rispetta esplicitamente il flag** |
| **`calculate_fifo_lots()`** (motore puro) | **Non riceve il flag broker come parametro — non ha modo di saperlo.** Se `sell_qty_remaining > 0` e la coda è vuota, **lancia sempre `ValueError`**, indipendentemente da `allow_asset_shorting`. Un broker con shorting abilitato che genera una vendita "in eccesso" (posizione short legittima) **causerebbe comunque un'eccezione qui** |
| **`get_lots()`** | **Non cattura l'eccezione di cui sopra** (verificato: nessun `try/except` attorno alla chiamata a `calculate_fifo_lots` in `portfolio_service.py:2394`) — si propagherebbe come errore non gestito (probabile HTTP 500) quando l'utente tenta di visualizzare "Open Lots" per un asset in posizione short legittima su un broker con `allow_asset_shorting=True` |
| **`compute_wac_from_txlist()`** | **Clamp silenzioso**: se la riduzione porta `new_qty < 0`, imposta `wac=0, qty_pool=0` (righe 130-135) — **non genera un pool "negativo"**, semplicemente azzera tutto. Questo significa: **il motore WAC non rappresenta affatto una posizione short** — un pool azzerato non distingue "sono a zero perché ho venduto esattamente tutto" da "sono andato short e il sistema ha silenziosamente clampato" |
| **`PortfolioEngine`** | Verificato uso di `max(new_qty, zero)`/`max(old_qty + tx_qty, zero)` in più punti (es. righe 610, 615, 747, 764) — **stesso pattern di clamp-a-zero**, non di rappresentazione esplicita di quantità negative |

### 11.3 Cosa succede oggi, in pratica, con una vendita/adjustment-out che eccede i lotti disponibili

**Scenario concreto**: Broker con `allow_asset_shorting=True`, utente vende (SELL) più unità di quante ne possiede (short legittimo voluto).
- **Balance-walk validation**: passa (il flag lo permette) → la transazione viene salvata nel DB senza errori.
- **WAC** (`compute_wac_iterative`/`PortfolioEngine`): il pool si azzera silenziosamente (clamp), **non riflette la posizione short reale** — mostrerebbe "quantità 0, WAC 0" invece di, ad esempio, "quantità −5, prezzo di apertura short = X".
- **`get_lots()`/Open Lots panel**: **lancia un'eccezione non gestita** — l'utente probabilmente vede un errore generico o una pagina bianca invece dei propri lotti.

**Conclusione verificata**: **il sistema oggi PERMETTE (a livello di validazione business) la creazione di posizioni short quando il broker lo consente, ma NESSUN motore di calcolo a valle (WAC, FIFO, PortfolioEngine) è stato progettato per RAPPRESENTARE correttamente una posizione short una volta creata.** È una funzionalità "abilitata a metà": il cancello d'ingresso (validazione) è aperto, ma le sale successive (calcolo/visualizzazione) non sono equipaggiate per gestire ciò che entra.

### 11.4 I lotti short richiedono una rappresentazione separata?

**Sì, quasi certamente, per un motivo strutturale non aggirabile**: il modello FIFO attuale (`OpenLot` con `remaining_quantity` sempre `>= 0`, una coda che si "riempie" con BUY e si "vuota" con SELL) **non ha un concetto nativo di "quantità negativa in coda"**. Rappresentare uno short richiede una delle due strade:
1. **Coda parallela per posizioni short**: un `OpenShortLot` con semantica invertita (`SELL` apre un lotto short, un successivo `BUY` di "riacquisto" lo chiude, calcolando P&L con il segno invertito rispetto al caso long: `realized_pnl = (sell_price_apertura − buy_price_chiusura) × qty`, non `(sell−buy)` come nel caso long).
2. **Segno esplicito su un unico modello di lotto**: un campo `direction: "LONG"|"SHORT"` sul lotto, con formule di P&L condizionali al segno.

Entrambe le strade richiedono **modifiche non banali al motore FIFO puro** (che oggi assume implicitamente "solo long" in tutta la sua logica di coda) — non è un semplice "permettere numeri negativi" nello stesso algoritmo, perché il **significato economico di FIFO si inverte** per una posizione short (si "compra per chiudere", non "si vende per chiudere").

---

## 11. Ambiguità semantiche (elenco consolidato)

1. **`cost_basis_override` come contenitore unico** per due motivazioni concettualmente diverse (snapshot tecnico di transfer vs override fiscale intenzionale) — nessun flag distingue i due casi una volta salvato il valore (Ipotesi 3-4).
2. **Il fallback "auto" (add-at-current-WAC)** è corretto per TRANSFER ma **matematicamente scorretto se usato per rappresentare uno SPLIT** tramite ADJUSTMENT positivo (Ipotesi 7) — nessun avviso o guardia impedisce all'utente di commettere questo errore.
3. **Nessuna decisione esplicita documentata** per il trattamento di un ADJUSTMENT negativo (Ipotesi 9) — il comportamento osservato (opzione "a", consuma senza realizzo) è un effetto collaterale dell'assenza di filtri di tipo nel motore WAC, non una scelta di design dichiarata.
4. **PRICE_ADJUSTMENT come evento asset** si sovrappone concettualmente a due modelli distinti (variazione di prezzo di mercato vs variazione di costo fiscale riconosciuto) senza che il sistema forzi o chiarisca quale dei due l'utente stia effettivamente registrando quando crea una transazione ADJUSTMENT collegata (Ipotesi 10).
5. **Nessuna rappresentazione della "data di acquisto originaria"** sopravvive esplicitamente attraverso una catena di transfer — solo il prezzo (`cost_basis_override`) è preservato per costruzione, la data richiede una risalita manuale di `related_transaction_id` (Ipotesi 8).
6. **Shorting "abilitato a metà"** (Ipotesi 11): il flag di validazione esiste e viene rispettato, ma nessun motore di calcolo a valle rappresenta correttamente il risultato — un'incoerenza architetturale tra "cosa è permesso salvare" e "cosa il sistema sa poi mostrare/calcolare".
7. **Filosofie diverse di fronte a un oversell**: `calculate_fifo_lots()` fallisce rumorosamente (eccezione), `compute_wac_from_txlist()` clampa silenziosamente a zero — nessuna delle due gestisce esplicitamente un vero short, ed entrambe le filosofie sono in conflitto tra loro se applicate allo stesso identico evento.

---

## 12. Modello di segmento consigliato (long e short)

*(Presentato come sintesi ragionata delle verifiche sopra — non un'implementazione, come richiesto. Nessuna proposta di interfaccia utente.)*

Un segmento (lotto), per rappresentare correttamente tutti i casi analizzati, dovrebbe portare con sé, come minimo:

```
Segment {
    origin_transaction_id       # transazione che ha creato il segmento (BUY, TRANSFER_IN, ADJUSTMENT positivo)
    origin_type                  # "BUY" | "TRANSFER_IN" | "ADJUSTMENT_SPLIT" | "ADJUSTMENT_OTHER" | ...
    origin_date                  # data del BUY radice — preservata attraverso QUALUNQUE catena di transfer
    origin_unit_price             # prezzo storico effettivo, in origin_currency — MAI sovrascritto
    origin_currency
    recognized_unit_cost          # = cost_basis_override quando presente, altrimenti = origin_unit_price
                                    # (nome provvisorio, vedi §13 — rappresenta "il costo da usare per WAC/P&L oggi")
    recognized_cost_is_override   # flag: true se recognized_unit_cost != origin_unit_price per scelta esplicita
                                    # (risolve l'ambiguità 1 sopra)
    current_broker_id             # AGGIORNATO ad ogni transfer — risolve il bug principale già documentato
    current_quantity               # quantità residua SU QUESTO broker (>=0 per segmenti long)
    direction                     # "LONG" | "SHORT" — risolve Ipotesi 11.4
}
```

**Per i segmenti short**, la stessa struttura si applica con semantica invertita: `origin_transaction_id` punta alla SELL/ADJUSTMENT-OUT che ha "aperto" la posizione short (non un BUY), `origin_unit_price` è il prezzo di apertura dello short, e la chiusura (P&L) avviene con un BUY di riacquisto usando la formula invertita (`P&L = prezzo_apertura_short − prezzo_chiusura`, non il contrario). **Un segmento non dovrebbe mai cambiare `direction` durante la sua vita** — se una posizione passa da long a short (o viceversa) attraversando lo zero in una singola transazione, quella transazione dovrebbe essere trattata come DUE eventi distinti (chiusura del segmento long esistente fino a zero, poi apertura di un nuovo segmento short per l'eccedenza) — analogo concettualmente a come un TRANSFER che eccede un lotto ne consuma il residuo e "spilla" nel lotto successivo.

Questo modello **non richiede modificare il motore FIFO puro esistente per i soli casi long** (che continuerebbe a funzionare come oggi, con l'aggiunta dei campi extra) — richiede invece un **motore parallelo o esteso** per i segmenti short, dato che (Ipotesi 11.4) la semantica di apertura/chiusura si inverte e non può essere ottenuta semplicemente "permettendo numeri negativi" nella coda FIFO esistente.

---

## 13. Naming consigliato

| Concetto | Nome proposto | Alternative scartate e perché |
|---|---|---|
| Costo storico effettivo di acquisizione, mai modificato | **`origin_unit_price`** | `original_unit_price` (usato nell'ipotesi originale, valido ma leggermente più lungo); `historical_cost` (ambiguo, potrebbe suggerire un valore aggregato non per-unità) |
| Costo riconosciuto oggi per WAC/P&L (= `cost_basis_override` se presente, altrimenti = `origin_unit_price`) | **`recognized_unit_cost`** | `tax_unit_cost` (proposto nell'ipotesi originale — **scartato** perché, come dimostrato in Ipotesi 3-4, il valore non è sempre di natura fiscale: può essere un semplice snapshot tecnico di transfer senza alcun evento fiscale coinvolto; usare "tax" nel nome imporrebbe una semantica fiscale anche ai casi puramente tecnici, fuorviante); `effective_unit_cost` (valida alternativa, meno esplicita su "riconosciuto da chi/cosa") |
| Flag che distingue le due motivazioni di `recognized_unit_cost` diverso da `origin_unit_price` | **`cost_override_reason`** (enum: `"transfer_snapshot"` \| `"manual_fiscal_override"` \| `"none"`) | Un semplice booleano perderebbe la distinzione tra "perché è diverso" — un enum a 3 stati è più espressivo e risolve l'ambiguità 1 del §11 in modo esplicito, non solo binario |
| Il campo esistente `cost_basis_override` (DB) | **Nessuna rinomina raccomandata nel breve termine** | Rinominare un campo DB già in uso comporta migrazione e impatto su tutto il codice che lo referenzia (verificato in almeno 3 file distinti in questa e nella precedente analisi) — il nome attuale, seppur non perfettamente allineato alla sua natura per-unità (§6 di `fifo-engine-current-state.md`), è **funzionalmente corretto e ben documentato inline**; una rinomina avrebbe senso solo come parte di un redesign più ampio che tocchi comunque lo schema, non come intervento isolato |

---

## 14. Invarianti e test necessari

### 14.1 Invarianti aggiuntive rispetto a quelle già elencate in `fifo-engine-current-state.md` §12.1

1. **Un segmento non cambia mai `origin_unit_price` o `origin_date` durante la sua vita**, indipendentemente da quanti TRANSFER/redistribuzioni subisce — solo `current_broker_id` e `current_quantity` sono mutabili.
2. **`recognized_unit_cost` può differire da `origin_unit_price` solo per una ragione esplicita e tracciata** (`cost_override_reason != "none"`) — mai per un effetto collaterale non intenzionale di un fallback silenzioso (risolve il rischio dimostrato in Ipotesi 7 per gli split).
3. **Un ADJUSTMENT positivo che rappresenta uno split deve preservare il costo totale della posizione** (`Σ costo_totale_prima == Σ costo_totale_dopo`) — qualunque implementazione futura deve verificare questa invariante esplicitamente con un test dedicato, dato che il fallback attuale la viola (Ipotesi 7).
4. **Il P&L realizzato di un ADJUSTMENT negativo deve essere il risultato di una scelta esplicita e documentata** (una delle tre opzioni di Ipotesi 9, o una quarta se ne emerge una migliore) — non un effetto collaterale implicito del motore WAC.
5. **Una posizione short, una volta creata, deve essere interrogabile e visualizzabile senza eccezioni non gestite** — oggi (Ipotesi 11.3) non lo è.
6. **Il flag `allow_asset_shorting` deve essere rispettato in modo coerente da TUTTI i componenti a valle della validazione**, non solo dal balance-walk — oggi c'è un disallineamento netto tra "cosa la validazione permette" e "cosa il motore FIFO/WAC sa rappresentare" (Ipotesi 11.3).

### 14.2 Test da scrivere (contratto, prima di qualunque implementazione)

1. **Same-day BUY, stesso prezzo**: verificare che il totale consumato/P&L aggregato sia identico sia con lotti separati (comportamento attuale, confermato in Ipotesi 2) sia con eventuale fusione futura — nessuna differenza nel risultato aggregato, solo nel numero di righe visualizzate.
2. **Same-day BUY, prezzo diverso**: verificare che NON vengano mai fusi, in nessuna implementazione futura.
3. **Split via ADJUSTMENT con `cost_basis_mode="auto"`**: test che DIMOSTRI il comportamento attuale (costo totale raddoppiato/gonfiato, Ipotesi 7) come **regressione da correggere**, non come comportamento accettabile — utile anche solo come test di "characterization" per documentare lo stato attuale prima di un eventuale fix.
4. **ADJUSTMENT negativo, le tre varianti**: tre test paralleli che verificano i tre possibili P&L (0, -500, +100 nell'esempio di Ipotesi 9) per la STESSA transazione di input, a seconda dell'opzione scelta — da usare come specifica eseguibile una volta presa la decisione di design.
5. **Catena di transfer A→B→C** con un acquisto aggiuntivo su B nel mezzo (ambiguità già segnalata in `fifo-engine-current-state.md` §8.4): un test che documenti quale comportamento il sistema produce OGGI (probabilmente "il pool WAC di B si mescola, C eredita un valore medio, non più il valore puro di A") — utile per decidere se questo è accettabile o va vincolato diversamente.
6. **Short position end-to-end**: creare un broker con `allow_asset_shorting=True`, generare una SELL che eccede la quantità posseduta, verificare (a) che la validazione la accetti, (b) cosa succede ESATTAMENTE in `get_lots()` oggi (documentare l'eccezione/errore attuale come test di caratterizzazione), (c) cosa succede in WAC/PortfolioEngine (documentare il clamp-a-zero attuale).
7. **`get_positions_contribution()` con ADJUSTMENT** (oltre al TRANSFER già segnalato in `fifo-engine-current-state.md` §7.4): verificare se `_QTY_TYPES={BUY,SELL}` esclude anche gli ADJUSTMENT da quella vista, con lo stesso tipo di scenario multi-broker/dashboard usato per il finding sui transfer.

---

*Fine documento. Nessuna modifica al codice è stata applicata. Nessuna proposta di interfaccia utente è stata formulata, come richiesto.*
