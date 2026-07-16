# Verifica mirata — share, transito, split, short e banner FIFO

> **Metodo**: nessuna modifica al codice. Ogni claim è verificato leggendo il codice reale e, per i punti 1-3, **eseguendo dal vivo** il codice esistente (`ScopeAwareTransactionClassifier`, `DailyStateBuilder`, pool WAC) con lo stesso harness di mock-`Transaction` già usato dai test esistenti (`test_scope_classifier.py`, `test_daily_state_builder.py`) — non solo letture statiche. Gli script di verifica sono temporanei (`/tmp/libreFolio_*_verify.py`), non fanno parte della codebase e non hanno modificato nulla. I punti 4 e 5 sono stati verificati da due sotto-agenti dedicati con lo stesso standard di citazione file:riga, poi integrati e riformattati qui.
> **Documento di riferimento**: `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/high-level-plan_v1.md` e il relativo `high-level-plan_v1-feasibility-report.md` (stessa cartella), di cui questo documento risolve le domande residue aperte al §16.

---

## Executive Summary

Le verifiche dal vivo confermano — con numeri esatti, non solo con argomentazioni teoriche — tutte e 4 le "decisioni già mature" indicate dall'utente, e in un caso (§1) rivelano che la decisione presa **corregge un bug reale e attualmente in produzione**, non solo un problema di stile architetturale:

1. **Share**: la proposta "motore assoluto + proiezione utente" è confermata corretta. Ho riprodotto dal vivo un TRANSFER di 10 unità tra un broker al 30% e uno al 70%: la quantità totale visibile dall'utente passa da **3,00 → 7,00** (un +4 "fantasma" dal nulla), e il costo totale da **300 → 700** (stessa distorsione, +400 fantasma). Il meccanismo attuale (`ScopeAwareTransactionClassifier`, scale-at-source) produce questo risultato **oggi, in produzione**, e **nessun avviso viene mostrato** se le due gambe hanno la stessa data (il caso più comune). Ho anche trovato un campo DTO già esistente ma mai popolato (`share_mismatch_warnings`) — segno che il problema era già stato anticipato ma mai risolto.
2. **Transito**: la convenzione `[min,max)` proposta dal piano non solo è "diversa" da quella già in produzione (`InTransitInterval`), ma **corregge un gap di valore verificato empiricamente**: con la convenzione attuale, il valore dell'asset **sparisce per almeno un giorno** (il giorno stesso della gamba di partenza) da qualunque bucket (né a fine broker, né in transito). La convenzione del piano chiude esattamente questo buco. Cambio raccomandato, con impatto contenuto (2 costanti + 2 asserzioni di test da aggiornare consapevolmente).
3. **Split**: confermato al centesimo che `ADJUSTMENT +15` con `cost_basis_override=0` produce esattamente **30 quote @ WAC 50, costo totale 1.500 (invariato)** — la matematica del piano è corretta. Ma la modalità "auto" della UI **non** precompila 0: precompila il WAC corrente (100), producendo **30 quote @ WAC 100, costo totale 3.000 (raddoppiato)** — bug riconfermato con una quarta citazione indipendente nella serie di report. **Nuova scoperta**: il reverse split via `ADJUSTMENT` negativo è **anch'esso rotto**, in modo diverso — riduce il costo proporzionalmente (come una vendita), producendo 15 quote @ WAC 50 (costo 750) invece di 15 quote @ WAC 100 (costo 1.500 preservato).
4. **Short**: confermato un mismatch a tre livelli (validazione ammette lo short, FIFO va in eccezione non gestita, Portfolio Engine produce silenziosamente uno stato incoerente — pool WAC positivo con quantità cumulata negativa, poi escluso dal reporting). Raccomandazione confermata: v1 long-only con guardia esplicita.
5. **Banner**: il framework `DataQualityIssue`/`DataQualityReport` è pienamente riusabile per entrambi i nuovi casi (fallback prezzo ADJUSTMENT+ e prezzo assente); servono due nuovi `IssueCode` (`REFERENCE_PRICE_FALLBACK`, `REFERENCE_PRICE_UNAVAILABLE`), nessuna modifica al componente banner. Unico impatto reale: gli endpoint `/portfolio/lots` e `/portfolio/asset-history` oggi non trasportano `data_quality`.

---

## 1. Share percentage

### 1.1 Comportamento attuale verificato

`broker_shares` è costruito **per utente corrente**, non per broker in assoluto: `broker_shares = {a.broker_id: a.share_percentage or Decimal("1") for a in accesses}` dove `accesses` proviene da `BrokerUserAccess.user_id == user_id` (`backend/app/services/portfolio_engine.py:1698`, `1677-1679`). Questo dizionario alimenta `ScopeAwareTransactionClassifier`, che applica lo share **all'origine**, prima di qualunque aggregazione: `share = self.broker_shares.get(tx.broker_id, Decimal("1"))` (riga 212) e poi, nel `DailyStateBuilder`, `tx_qty = tx.quantity * ctxn.share` (riga 591) confluisce sia in `cumulative_qty[key] += tx_qty` (riga 620) sia nel pool WAC (`wac_pool_cost[key] += unit_cost_asset_ccy * tx_qty`, riga 599).

Ho riprodotto lo scenario richiesto (TRANSFER di 10 unità, broker A share utente 30%, broker B share utente 70%) istanziando direttamente `ScopeAwareTransactionClassifier` + `DailyStateBuilder` con lo stesso harness di `test_daily_state_builder.py` (mock `Transaction`, nessun DB):

```
BUY 10 @ 100 su broker A (2025-01-10)
TRANSFER -10 su broker A, TRANSFER +10 su broker B (2025-01-15, stesso giorno)
```

**Risultato effettivo, eseguito dal vivo:**

| Momento | qty_A (share 30%) | qty_B (share 70%) | **TOTALE utente** | Atteso (reale) |
|---|---|---|---|---|
| Prima (12/01, solo BUY) | 3,00 | 0 | **3,00** | 3,00 (30% di 10) ✅ |
| Dopo (16/01, transfer completato) | 0,00 | 7,00 | **7,00** | dovrebbe restare 3,00 (nessun evento economico è avvenuto) ❌ |

**+4,00 unità apparse dal nulla**, puramente per effetto del cambio di broker con share differente. Lo stesso accade sul costo: costo_basis_A prima = 300 (30% di 1.000), costo_basis_B dopo = 700 (70% di 1.000) — **+400 di costo fantasma**, stessa magnitudine (4 unità × 100/unità).

**Controllo**: con share identico su entrambi i broker (50%/50%), lo stesso scenario produce `qty_B=5,00, TOTALE=5,00` — corretto, nessuna distorsione. **Il bug è specificamente causato dalla differenza di share tra i due broker del transfer, non da un difetto generico del TRANSFER.**

**Nessun avviso per l'utente nel caso "stesso giorno"**: `classifier.classify()` non emette alcun warning (`result.warnings == []`) quando le due gambe hanno la stessa data. Ho verificato che esiste effettivamente un controllo di "share mismatch" nel codice, ma è annidato dentro il branch che gestisce le date diverse: `if pair_key not in processed_pairs and tx.date != paired.date: ... paired_share = self.broker_shares.get(paired.broker_id, ...); if share != paired_share: warnings.append(...)` (`portfolio_engine.py:246-254`). Ripetendo lo stesso identico scenario con date diverse (OUT 15/01, IN 18/01), il warning **viene** emesso (`'Linked internal pair (2, 3): share mismatch broker 10=0.30 vs broker 20=0.70'`), ma la distorsione numerica su quantità/costo è **identica** in entrambi i casi. Il warning quindi copre solo un sottoinsieme dei casi in cui il bug si manifesta.

**Un campo DTO già esiste per questo, ma non è mai popolato**: `DataQualityReport.share_mismatch_warnings: List[str]` (`backend/app/schemas/portfolio.py:226`) — verificato per grep che è l'**unica** occorrenza nell'intero backend: nessun servizio scrive mai in questo campo. Inoltre `classification.warnings` (il risultato di `classifier.classify()`, che include il messaggio di mismatch) viene assegnato a una variabile locale (`classification = classifier.classify(external_paired)`, riga 1724) e **mai più letto** in tutto il file (verificato per grep, zero occorrenze di `classification.warnings` o `.warnings` dopo l'assegnazione). Il meccanismo di segnalazione esiste a metà, è stato costruito ma mai collegato: un segnale che il problema era già stato anticipato da chi ha scritto questo codice, ma la correzione/segnalazione non è mai stata completata.

### 1.2 Valutazione della proposta

Confronto diretto, con evidenza numerica:

| | **Scale-at-source** (comportamento oggi) | **Assoluto + proiezione** (proposta) |
|---|---|---|
| Dove si applica lo share | Ad ogni transazione, prima di ogni aggregazione | Solo alla fine, in una vista per-utente |
| Comportamento su TRANSFER con share diversi | **Bug confermato**: quantità/costo totale cambiano senza eventi economici | Nessuna distorsione possibile: l'Engine lavora su quantità reali (10 unità, sempre 10), la proiezione utente è un moltiplicatore applicato in sola lettura |
| Cache/riuso tra utenti che condividono un broker | **Impossibile**: la cache blob è già chiavata per `user_id` (Report 4, confermato), quindi il calcolo va ripetuto per ogni utente anche se il 70%+ dei dati sottostanti (transazioni, prezzi, FX) è identico | **Possibile**: il motore assoluto può essere calcolato una sola volta per broker/asset indipendentemente da chi guarda, con benefici di cache diretti (coerente con le cache dedicate proposte nel Report 4) |
| Identità stabile del lotto (`lot_id = origin_transaction_id`) | **Compromessa**: due utenti con share diverso vedrebbero quantità diverse per "lo stesso" `lot_id`, complicando cache/confronto/test | **Preservata**: `lot_id` e le quantità assolute sono oggettivi, indipendenti dall'osservatore; solo la proiezione finale (moltiplicazione) dipende dall'utente |

**Le evidenze non solo non contraddicono la decisione già presa, la rafforzano**: non è solo una questione di pulizia architetturale, è la correzione di un bug quantitativamente dimostrato.

### 1.3 Una domanda di prodotto non ancora esplicita, emersa da questa verifica

Nello spostare lo scaling a valle, emerge una domanda che il modello "assoluto + proiezione" da solo non risolve automaticamente: **a quale broker "appartiene" economicamente un'unità dopo un transfer, quando i due broker hanno share diversi per lo stesso utente?**

Due politiche possibili, entrambe compatibili con l'architettura "assoluto + proiezione" a livello di codice, ma con risultati numerici diversi:

- **Politica A — "la custodia attuale governa"**: la quota dell'utente su una unità è sempre quella del broker che la detiene *ora*. Conseguenza: spostando l'unità da un broker al 30% a uno al 70%, la quota dell'utente su quella specifica unità *cambia realmente* (da 30% a 70%) — non è un bug ma un evento economico reale (es. un trasferimento tra conti cointestati con quote diverse può legittimamente cambiare la titolarità effettiva). Il "+4 fantasma" osservato in §1.1 sarebbe quindi corretto in questo scenario, purché visualizzato come un evento esplicito (non silenzioso).
- **Politica B — "la quota viaggia con il lotto, fissata all'origine"**: la quota dell'utente su un lotto è quella in vigore quando il lotto è stato acquisito, e **non cambia** per effetto di trasferimenti puramente custodiali. Il transfer è amministrativo, non ridistribuisce la titolarità economica.

Il piano `high-level-plan_v1.md` non discute questo caso (share non è mai menzionato, come già rilevato nel report di fattibilità), quindi non prende posizione. La proposta "assoluto + proiezione" risolve *dove* si applica lo scaling, ma non *quale* scaling applicare in questo scenario specifico. **Raccomando la Politica B** (coerente con il principio già stabilito nella serie di report — "il transfer preserva lotto/data/prezzo originari", §4.5 del piano — la quota di comproprietà è un attributo dell'origine del lotto, non della custodia corrente), ma segnalo che è una decisione di prodotto, non deducibile dal solo codice.

### 1.4 Soluzione raccomandata

- `FifoLotEngine` ricostruisce quantità/costi assoluti per broker (nessuno scaling interno).
- La proiezione per l'utente corrente avviene in un livello a parte (`LotsAnalysisService` o superficie equivalente), applicando lo `share_percentage` **per fragment**, usando la quota **fissata all'origine del lotto** (Politica B) salvo diversa decisione di prodotto.
- Da correggere/collegare, indipendentemente da questo piano (bug preesistente, fuori scope ma da segnalare): il campo `share_mismatch_warnings` mai popolato e `classification.warnings` mai letto — oggi il Portfolio Engine aggregato soffre dello stesso bug quantitativo mostrato in §1.1, senza alcuna segnalazione even nel caso con date diverse coperto dal warning esistente.

### 1.5 Impatto sul piano v1

Il piano non menziona `share_percentage` in nessuna delle sue 1541 righe. Senza questa sezione, l'invariante di riconciliazione §2.4 del piano (`Q_{a,b}(t) = Σ frammenti`) non è definibile in modo univoco per broker condivisi.

### 1.6 Modifica testuale da inserire nel piano

> **Nuova sezione proposta, dopo §2.4 ("Frammento di custodia")**:
> "2.4bis Comproprietà e `share_percentage`. Il `FifoLotEngine` opera esclusivamente su quantità e costi assoluti per broker, indipendenti dall'utente osservatore. La quota di comproprietà (`share_percentage`) viene applicata esclusivamente in fase di proiezione per l'utente corrente, utilizzando la quota in vigore alla data di origine del lotto (`t_i^0`), non quella corrente del broker che lo custodisce al momento dell'osservazione. Un trasferimento tra broker con quote diverse per lo stesso utente non altera la quota di comproprietà già assegnata al lotto."

---

## 2. Confini del transito

### 2.1 Comportamento attuale verificato

`InTransitInterval` (`portfolio_engine.py:110-131`) usa oggi `start_date = departure.date + 1`, `end_date = arrival.date - 1` (`_build_in_transit_interval`, righe 304-305) — **esclude entrambe le date di regolamento**. `_compute_in_transit()` include l'intervallo con un controllo inclusivo su entrambi gli estremi: `if not (interval.start_date <= dt <= interval.end_date): continue` (riga 1140).

### 2.2 Blast radius, punto per punto

- **Quantità per broker** (`cumulative_qty`): **non è influenzata affatto dalla finestra di transito**. Il delta pieno viene applicato alla data della singola gamba, indipendentemente dall'intervallo (`cumulative_qty[key] += tx_qty`, riga 620, eseguito nel loop giornaliero standard, non nel blocco `_compute_in_transit`). Cambiare la convenzione dei confini **non tocca in alcun modo** questo calcolo.
- **`in_transit` quantity/value/book**: qui sì l'impatto è diretto e ho verificato empiricamente la differenza. Riproducendo BUY 10 @ 100 su A (10/01) + TRANSFER 10 (OUT 15/01, IN 18/01):

  | Data | Convenzione attuale (`dep+1..arr-1`) | Convenzione piano (`[min,max)` ≈ `dep..arr-1`) |
  |---|---|---|
  | 15/01 (giorno della gamba OUT) | `qty_A=0`, `in_transit_mv=0` → **valore sparito per un giorno intero** | `qty_A=0`, `in_transit_mv=1.000` → valore correttamente contato come "in transito" |
  | 18/01 (giorno della gamba IN) | `qty_B=10`, `in_transit_mv=0` (corretto) | `qty_B=10`, `in_transit_mv=0` (identico, corretto) |

  **La convenzione attuale ha un buco di valore verificato di almeno un giorno** (il giorno stesso della partenza): l'asset non risulta né sul broker di origine (già a zero) né nel bucket "in transito" (che parte solo dal giorno dopo). Ripetendo con gambe **adiacenti** (OUT 01/06, IN 02/06): la convenzione attuale produce **zero giorni di intervallo di transito** (`start=02/06 > end=01/06` → intervallo vuoto, confermato dal test esistente `test_adjacent_days_no_transit`), quindi il giorno 01/06 non ha né quantità né valore in transito da nessuna parte — lo stesso buco, e per un caso probabilmente frequente (bonifici che regolano il giorno successivo). La convenzione del piano (`[dep, arr)`) coprirebbe correttamente questo giorno.
- **NAV e Book Value**: `in_transit_market_value`/`in_transit_book_value` confluiscono direttamente in `nav_value` e `book_value` di `DailyPortfolioState` (`portfolio_engine.py:381-390`, `881-884`). Il buco di valore descritto sopra si traduce quindi in un **NAV/Book Value sottostimato per almeno un giorno** ad ogni transfer con gambe non identiche o adiacenti.
- **History e GrowthChart**: `PortfolioHistoryPoint` espone gli stessi campi `in_transit_market_value`/`in_transit_book_value` per ogni giorno della serie storica (`schemas/portfolio.py:419-426`), che alimentano `GrowthChart.svelte` — il buco descritto sopra è quindi visibile anche nel grafico di crescita del dashboard, non solo in un valore puntuale.
- **`ScopeAwareTransactionClassifier`**: la modifica richiesta è **chirurgica**: una sola riga (`start = departure.date + timedelta(days=1)` → `start = departure.date`), lasciando invariato `end = arrival.date - timedelta(days=1)`. Nessun'altra logica del classificatore dipende da questo dettaglio.
- **Test esistenti**: la modifica rompe consapevolmente **2 asserzioni dirette** — `test_cash_transfer_different_dates` (si aspetta `start_date == date(2025,3,2)` = `dep+1`, diventerebbe `date(2025,3,1)` = `dep`) e `test_asset_transfer_different_dates` (stesso pattern, `dep+1`→`dep`) — e **1 test di comportamento** (`test_adjacent_days_no_transit`, che oggi asserisce "0 intervalli" per gambe adiacenti; con la nuova convenzione diventerebbe "1 intervallo di 1 giorno", quindi il test andrebbe riscritto per riflettere il comportamento corretto, non solo aggiornato nei numeri). Nessun altro test file referenzia `in_transit` con asserzioni sui confini esatti (verificato per grep in `test_portfolio_engine_vnext.py` e `test_daily_state_builder.py` — usano `InTransitInterval` costruito a mano con date esplicite, non derivato da `_build_in_transit_interval`, quindi non sono impattati dal cambio di formula).
- **Casi con date uguali o invertite**: date uguali → nessun intervallo creato in nessuna delle due convenzioni (comportamento identico, corretto). Date invertite (la gamba con quantità negativa/OUT ha una data **successiva** alla gamba con quantità positiva/IN) → **non è un caso ipotetico**, il codice lo gestisce già oggi tramite puro ordinamento cronologico (`if tx_a.date <= tx_b.date: departure, arrival = tx_a, tx_b else: ...`, righe 299-302), indipendente dal segno della quantità. L'ho verificato dal vivo costruendo un TRANSFER con OUT datato 05/05 e IN datato 05/01: il codice non va in errore, produce un intervallo `[05/02, 05/04]` corretto, ma **etichetta semanticamente "departure_leg" la transazione IN (id=61, quantità positiva)** perché è quella con la data più antica — un'inversione di naming interna, confusa da leggere in debug ma **non un bug funzionale**: l'estrazione del `cost_basis_override` (che controlla entrambe le gambe con fallback, riga 315) continua a funzionare correttamente anche in questo caso.

### 2.3 Il Portfolio Engine può essere uniformato senza double-count o perdita di valore?

Sì, con evidenza diretta: **cambiare a `[min,max)` non introduce doppio conteggio** (verificato: sul giorno di arrivo, entrambe le convenzioni producono `in_transit_mv=0`, nessuna sovrapposizione con la quantità già assegnata al broker destinatario) e **elimina un buco di valore già esistente e verificato** sul giorno di partenza. È quindi una correzione, non un semplice cambio di stile — a differenza di quanto ipotizzato con più cautela nel report di fattibilità precedente (che segnalava solo "convenzioni diverse da riconciliare" senza aver ancora eseguito questa verifica quantitativa).

### 2.4 Soluzione raccomandata

Adottare `[min(d_out,d_in), max(d_out,d_in))` sia nel nuovo `FifoLotEngine` sia, per coerenza ed eliminazione del bug, **anche in `InTransitInterval`** (modifica di una riga, `_build_in_transit_interval`, `portfolio_engine.py:304`), aggiornando consapevolmente le 2+1 asserzioni di test elencate in §2.2. Questo è tecnicamente fuori dallo scope stretto del piano FIFO (tocca il Portfolio Engine, che il piano dichiara invariato) — **lo segnalo come correzione raccomandata ma separata**, da valutare a parte con l'utente prima di procedere, coerentemente con la preferenza di non correggere silenziosamente bug fuori scope in un task non correlato.

### 2.5 Impatto sul piano v1 / modifica testuale

> **Modifica proposta alla sezione 4.5 ("TRANSFER") del piano, dopo la formula di `t_start`/`t_end`**:
> "Nota di implementazione: questa convenzione `[min,max)` differisce da quella già in uso in `InTransitInterval` (`portfolio_engine.py`), che esclude entrambe le date di regolamento. Una verifica empirica ha mostrato che la convenzione qui proposta **corregge** un buco di valore già presente nel motore aggregato (il valore risulta non contabilizzato per almeno un giorno sulla gamba di partenza). Si raccomanda di allineare anche `InTransitInterval` alla stessa convenzione, come correzione dichiarata e separata dal lavoro sul nuovo `FifoLotEngine`."

---

## 3. Split e reverse split

### 3.1 Percorso reale form → schema → validation → DB → WAC

- **Form**: `TransactionFormModal.svelte` gestisce uno stato locale `costBasisMode: 'auto' | 'manual'` (riga 322). In modalità `'auto'`, il payload inviato al backend include `cost_basis_mode: 'auto'` (riga 1006) e un placeholder `cost_basis_override` con importo `'0'` (riga 995: `costBasisMode === 'auto' ? {code: wacCurrencyHint, amount: '0'} : cbo`) — **questo `'0'` è solo un valore transitorio lato client**, sovrascritto dal backend prima del commit (vedi sotto).
- **Schema**: `cost_basis_mode: Literal["auto", "auto-detail", "manual"] | None` (`backend/app/schemas/transactions.py:149-152`), con la regola "valido solo per TRANSFER ricevente (qty>0) o ADJUSTMENT (qty>0)" (righe 301-314).
- **Validation**: `_requires_cost_basis()` impone che ADJUSTMENT con `quantity>0` abbia sempre un `cost_basis_override` non nullo, **senza eccezioni per collegamento a un evento SPLIT** (`transaction_service.py:233-242`).
- **DB → WAC (modalità `auto`)**: se `cost_basis_mode == 'auto'`, il backend **ignora** il placeholder del form e calcola da sé: `wac_result = await compute_wac_iterative(...)` seguito da `db_tx.cost_basis_override = wac_result.wac.amount` (`transaction_service.py:1591-1603`) — cioè scrive nel DB il **WAC corrente per unità**, non zero.

### 3.2 Verifica numerica split diretto (eseguita dal vivo)

Partendo da **15 quote @ WAC 100 (costo totale 1.500)**, ho eseguito realmente `ScopeAwareTransactionClassifier` + `DailyStateBuilder` per un `ADJUSTMENT +15` con due valori diversi di `cost_basis_override`:

| `cost_basis_override` usato | Risultato effettivo (eseguito) | Corretto? |
|---|---|---|
| `0` (valore proposto dall'utente, matematicamente corretto per uno split) | **30 quote @ WAC 50, costo totale = 1.500** | ✅ Esattamente come atteso dal piano (§4.6: `q'p0'=qp0`) |
| `100` (= WAC corrente, quello che la modalità **auto** scrive davvero) | **30 quote @ WAC 100, costo totale = 3.000** | ❌ Costo raddoppiato |

**Conferma diretta e quantitativa**: la matematica del piano è corretta *se* si usa `cost_basis_override=0`; ma la modalità "auto" della UI **non produce mai 0** per questo caso — produce il WAC pre-split, causando esattamente il raddoppio già segnalato nel Report 3 e ri-confermato nel report di fattibilità precedente (qui con una quarta citazione di codice indipendente: `transaction_service.py:1601-1603`).

### 3.3 Reverse split via ADJUSTMENT negativo — bug distinto, non ancora segnalato nei report precedenti

Partendo da **30 quote @ WAC 50 (costo 1.500)**, ho eseguito dal vivo un `ADJUSTMENT -15` (dimezzamento quantità, tipico di un reverse split 2:1 — nessun `cost_basis_override` è richiesto/possibile per un ADJUSTMENT a quantità negativa, `_requires_cost_basis()` si applica solo a `quantity>0`):

- **Risultato effettivo**: `wac_pool_qty=15`, `wac_pool_cost=750`, **WAC=50/unità (invariato)**.
- **Atteso per un reverse split 2:1 corretto**: 15 quote @ WAC **100**/unità, costo totale **preservato a 1.500**.

Il ramo di riduzione del pool (`portfolio_engine.py`, righe ~611-619) tratta **qualunque** riduzione di quantità come una vendita/rimozione pro-quota al WAC corrente (`wac_pool_cost[key] = wac_pool_qty[key] * current_wac`), dimezzando quantità **e** costo nella stessa proporzione — comportamento corretto per una vendita o un `ADJUSTMENT` di rimozione reale, ma **sbagliato per un reverse split**, che dovrebbe preservare il costo totale raddoppiando il WAC per unità. **Il costo totale viene ridotto erroneamente** (dimezzato, coerentemente con la quantità rimossa), non conservato. Non esiste oggi alcun meccanismo (override o altro) per correggere questo caso, perché la via del `cost_basis_override` è riservata esclusivamente alle transazioni a quantità **positiva**.

### 3.4 Soluzione raccomandata

- Il nuovo `FifoLotEngine`, quando riconosce (via `asset_event_id` → `AssetEventType.SPLIT`) che un `ADJUSTMENT` rappresenta uno split, deve applicare direttamente la trasformazione matematica del piano (`q'=rq, p0'=p0/r`) **senza passare da `cost_basis_override`**, sia per split diretti (ADJUSTMENT positivo) sia per reverse split (ADJUSTMENT negativo) — il piano già lo prevede per il caso diretto (§4.6), ma andrebbe esteso esplicitamente al caso di riduzione.
- Per il dominio WAC (fuori scope di questo piano, ma da segnalare): la modalità "auto" dovrebbe riconoscere il collegamento a un evento SPLIT e, in quel caso, non precompilare il WAC corrente ma calcolare il valore che preserva il costo totale (per lo split diretto: 0 aggiuntivo; per il reverse split: nessun meccanismo esiste oggi — richiederebbe un nuovo campo o una nuova via di calcolo, poiché `cost_basis_override` non è applicabile a transazioni con quantità negativa).

### 3.5 Impatto sul piano v1 / modifica testuale

> **Aggiunta proposta alla sezione 4.6 ("SPLIT") del piano**:
> "Verifica empirica: la trasformazione `q'=rq, p0'=p0/r` è stata confermata numericamente corretta nel dominio FIFO quando applicata direttamente (15@100 → ADJUSTMENT +15 con costo aggiuntivo nullo → 30@50, costo 1.500 preservato). Per rapporti r<1 (reverse split, tramite `ADJUSTMENT` a quantità negativa), la stessa proprietà di conservazione del costo deve essere applicata esplicitamente nel `FifoLotEngine`: oggi il dominio WAC (Portfolio Engine) **non** la garantisce — un `ADJUSTMENT` negativo riduce il costo proporzionalmente alla quantità rimossa, come una cessione, non come uno split inverso. Questa è una limitazione nota del dominio WAC esistente, indipendente dal nuovo motore FIFO, ma da tenere presente per evitare che le due viste (FIFO corretto, WAC non corretto) divergano visibilmente anche per i reverse split, non solo per gli split diretti già segnalati."

---

## 4. Short positions

*(Sezione prodotta da verifica dedicata con lo stesso standard di citazione file:riga, integrata qui.)*

### 4.1 Comportamento attuale verificato

`Broker.allow_asset_shorting` esiste, default `False` (`backend/app/db/models.py:406-407`). `_validate_broker_balances()` ritorna subito solo se **entrambi** i flag (`allow_cash_overdraft` e `allow_asset_shorting`) sono `True`; altrimenti accumula i saldi firmati giorno per giorno e lancia errore su quantità negative solo dentro `if not broker.allow_asset_shorting:` (`transaction_service.py:431-508`). Con il flag attivo, una SELL che porta la posizione sotto zero **non è bloccata**. Confermato dai test esistenti `TX-U-024` (`DEPOSIT + BUY 10 + SELL 20` va a buon fine con shorting abilitato) e `BR-U-053` (disabilitare il flag con una holding già negativa fallisce) — `backend/test_scripts/test_services/test_transaction_service.py:687-719`, `test_broker_service.py:797-831`.

Il FIFO puro è invece rigidamente long-only: `get_lots()` usa solo BUY/SELL, passa `abs(tx.quantity)`/`abs(tx.amount)/qty` a `calculate_fifo_lots()` (`portfolio_service.py:2363-2395`) **senza try/except**; `calculate_fifo_lots()` solleva `ValueError` se una SELL eccede la coda dei BUY aperti (`fifo_utils.py:87-148`, coperto dal test `test_oversell_raises_error`). L'endpoint `/portfolio/lots` non intercetta questa eccezione (`portfolio_api.py:158-178`).

Il Portfolio Engine, diversamente, **non va in crash ma produce uno stato incoerente**: `cumulative_qty` viene sempre aggiornato con il delta firmato e può diventare negativo, mentre `wac_pool_qty`/`wac_pool_cost` sono sempre clampati a zero quando una riduzione eccede il pool (`max(old_qty + tx_qty, zero)`, o reset esplicito). Tutti i loop di valutazione/snapshot saltano `qty <= 0` (`DailyPositionState` è documentato come snapshot valido solo per `qty > 0`, righe 352-357, 506-508, 583-620, 708-779, 853-855, 911-915, 956-960, 1186-1193). Risultato: lo short sparisce dal reporting mentre il pool WAC resta positivo e incoerente con la quantità cumulata negativa.

Lato UI: nessun campo `direction`/segno esiste negli schema attuali (`OpenLotSchema`/`ClosedLotSchema`, `schemas/portfolio.py:455-487`), che sono costruiti attorno a `buy_transaction_id`/`buy_date`/`buy_price`. `FIFOLotsPanel.svelte` cattura genericamente l'errore di fetch e mostra un messaggio generico, nascondendo bubble timeline e tabelle (righe 118-141, 212-224, 288-303). Nessun test end-to-end (validazione → `/portfolio/lots` → Portfolio Engine) esercita oggi uno scenario short.

### 4.2 Esempio numerico (BUY 5 @ 100, SELL 8 @ 120, BUY 2 @ 90)

- **Validazione saldi**: saldo asset `+5 → -3 → -1`, sempre accettato con `allow_asset_shorting=True` (`transaction_service.py:466-508`).
- **`calculate_fifo_lots()`**: abbina 5 unità del BUY iniziale contro la SELL (`ClosedLot` da 5, `realized_pnl=(120-100)*5=100`), poi la coda si svuota con 3 unità ancora da vendere → **`ValueError`** immediato; il BUY successivo di 2 non viene mai processato (`fifo_utils.py:97-128`).
- **Portfolio Engine**: dopo BUY 5@100 → `wac_pool_qty=5, cost=500`; dopo SELL 8@120 → pool clampato a `qty=0, cost=0`, `cumulative_qty=-3`, realizzato attribuito ai pool K/R (`960-800=160`); dopo BUY 2@90 → il pool riparte come un nuovo long (`qty=2, cost=180`), ma `cumulative_qty` passa da `-3` a `-1`. **Pool WAC positivo (2@90) convive con quantità cumulata negativa (-1)** — incoerenza interna silenziosa, l'asset viene poi escluso da valutazione/snapshot (`qty<=0`).

### 4.3 Valutazione del modello "SELL chiude FIFO + apre SHORT"

Applicato all'esempio: BUY 5@100 apre `L1` long da 5; SELL 8@120 chiude `L1` (P&L +100) e apre `S1` short da 3 @ 120; BUY 2@90 chiude 2 unità di `S1` (P&L short `+(120-90)*2=+60`), lasciando `S1` aperto per 1 unità. **P&L totale realizzato = +160, 1 lotto short aperto da 1 unità.**

Un semplice flag `direction` non basta: gli schema/UI attuali sono costruiti su `buy_*`/`sell_*` come identità primaria; servirebbero campi neutri (`open_transaction_id/date/price`, `close_transaction_id/date/price`) o DTO distinti per long/short. Invarianti da testare: direzione di un lotto immutabile fino a chiusura completa a zero; un attraversamento dello zero va scisso in chiusura-direzione-corrente + apertura-direzione-opposta; polarità P&L invertita per gli short (`entry - cover`, non `sell - buy`); posizione netta = Σlong aperti − Σshort aperti. Algoritmicamente, la singola `deque` FIFO attuale andrebbe estesa a due code (long aperti, short aperti) — più leggibile e testabile di una struttura unica a segno misto.

### 4.4 Impatto sul piano v1

Il piano rimanda esplicitamente lo short (§12, corretto). Da notare per iscritto nel piano: oggi il sistema ha già un mismatch a tre livelli (validazione ammette, FIFO va in eccezione, Engine produce stato incoerente silenzioso) — senza una nota esplicita di scope, si rischia di consegnare una v1 che sembra "supportare" gli short (perché il broker li accetta) ma li tratta in modo incoerente tra i tre livelli.

### 4.5 Raccomandazione

**Confermato: rimandare il supporto short**, mantenendo la v1 long-only **con una guardia esplicita** sui casi in cui la quantità netta diventerebbe negativa (errore dichiarato, non uno stato silenziosamente incoerente come oggi nel Portfolio Engine). La frequenza d'uso reale dello short non è verificabile dal codice — è una priorità di prodotto, non tecnica.

> **Modifica testuale proposta per il piano, §12**: "Lo short selling resta esplicitamente fuori scope per questa v1. Il `FifoLotEngine` deve però rilevare esplicitamente il caso di quantità netta negativa su un broker (oggi gestito in modo incoerente: ammesso dalla validazione, causa eccezione non gestita nel FIFO attuale, produce stato silenzioso incoerente nel Portfolio Engine) e restituire un errore/flag dichiarato invece di propagare un'eccezione o un dato silenziosamente sbagliato."

---

## 5. Banner / Data Quality

*(Sezione prodotta da verifica dedicata con lo stesso standard di citazione file:riga, integrata qui.)*

### 5.1 Sistema esistente — mappa completa

Schema: `MissingPriceAsset` (`asset_id, symbol, name, broker_id, broker_name, first_position_date, quantity, open_cost_basis, currency`), `StalePriceAsset` (`asset_id, name, last_price_date, stale_days`), `DataQualityIssue` (`domain, code, severity, message_i18n_key, message_params, count`, liste asset/FX, CTA opzionale, `group_key`), `DataQualityReport` (`issues, missing_price_assets, missing_fx_pairs, stale_prices, incomplete_nav_dates, incomplete_book_value_dates, incomplete_allocation_dates, in_transit_cost_basis_warnings, share_mismatch_warnings, warnings`) — `schemas/portfolio.py:116-227`.

Enum attuali: `IssueSeverity` = `error|warning|info` (148-153); `IssueDomain` = `portfolio|asset|forex` (156-161); `IssueCode` portfolio = `MISSING_PRICE, TRANSACTION_IMPLIED, STALE_PRICE, MISSING_FX_MARKET, NAV_INCOMPLETE, MWRR_NOT_CALCULABLE, MWRR_SERIES_UNRELIABLE` (171-178); detail-page = `ASSET_ARCHIVED, RANGE_BEFORE_FIRST_DATA, FX_PAIR_MISSING, FX_PAIR_NO_DATA, FX_PAIR_PARTIAL_GAP` (180-185).

Popolamento: `DerivedViewsBuilder.build_data_quality_report()` (`portfolio_engine.py:1491-1625`) produce una issue per tipologia con severity fissa (`MISSING_PRICE`→error, `TRANSACTION_IMPLIED`/`STALE_PRICE`/`MISSING_FX_MARKET`→warning, `NAV_INCOMPLETE`/`MWRR_NOT_CALCULABLE`→info). Esposizione: non un endpoint dedicato, ma `PortfolioSummary.data_quality` e `PortfolioReportResponse.data_quality` (`schemas/portfolio.py:399-409, 539-553`), letti dal dashboard (`frontend/.../dashboard/+page.svelte:166`). **`GET /portfolio/lots` e `GET /portfolio/asset-history` non trasportano `data_quality`** (`portfolio_api.py:137-178`) — nessun caso FIFO è oggi veicolato da questi endpoint.

Deduplicazione: già a 3 livelli — set intra-day su `DailyPortfolioState` (righe 405-410, 848-851, 946-949), aggregazione cross-day via `aggregate_*_ids()` basata su `set.update()` (1463-1489), e infine **una sola** `DataQualityIssue` per tipologia con `count` e `group_key` stabile (1512-1615).

### 5.2 Localizzazione

Ogni issue porta un `message_i18n_key` esplicito (non una mappa automatica codice→testo), impostato dal backend (`dataQuality.missingPrice`, `stalePrice`, `missingFx`, `navIncomplete`, `mwrrNotAvailable`, `mwrrSeriesUnreliable`) o dal frontend nelle pagine detail (`archivedAsset`, `rangeBeforeData`, `fxPair*`). Il banner renderizza genericamente `$_(issue.message_i18n_key, {values: issue.message_params})` (`DataQualityBanner.svelte:158-162,213-218`). Stringhe presenti in EN/IT/FR/ES (`frontend/src/lib/i18n/{en,it,fr,es}.json:938-960`).

### 5.3 Visualizzazione frontend

`DataQualityBanner.svelte`: modalità `grouped` (dashboard) e `flat` (detail page); severity `error`/`warning` → palette amber, `info` → palette sky, icone `AlertCircle`/`AlertTriangle`/`Info` (righe 67-83). **Persistente, non dismissibile** (nessun bottone "close", solo expand/collapse) — confermato dal contrasto con un banner runtime-error separato e dismissibile presente nelle stesse pagine. Il resto della UI continua a renderizzare subito dopo il banner in tutti i punti verificati (dashboard, asset detail, FX detail).

### 5.4-5.5 Nuovi casi — riuso vs nuovo codice

Per entrambi i casi richiesti (fallback ultimo prezzo per ADJUSTMENT+ senza prezzo esatto; nessun prezzo precedente disponibile), **il framework esistente è pienamente sufficiente as-is**: `IssueDomain.ASSET`, severity `info`/`warning`, `DataQualityIssue` con `message_i18n_key`+`message_params`, banner code-agnostico (non fa switch sul codice). Nessun codice esistente è semanticamente corretto da riusare direttamente: `STALE_PRICE` significa "ultimo prezzo più vecchio di una soglia", non "fallback puntuale per un lotto"; `MISSING_PRICE` oggi indica esclusione dal NAV, semanticamente troppo forte per un caso in cui il P&L assoluto resta disponibile; `RANGE_BEFORE_FIRST_DATA` è vicino solo concettualmente ma è già legato al range della detail page, non al prezzo di riferimento di un lotto.

**Proposta**: due nuovi `IssueCode`, coerenti con lo stile UPPER_SNAKE_CASE esistente:
- `REFERENCE_PRICE_FALLBACK` (dominio `ASSET`, severity `info`) — chiave i18n `dataQuality.referencePriceFallback`, parametri `tx_date`/`fallback_date` (o `count` se aggregato).
- `REFERENCE_PRICE_UNAVAILABLE` (dominio `ASSET`, severity `warning`) — chiave i18n `dataQuality.referencePriceUnavailable`, messaggio esplicito "rendimento % non disponibile, P&L assoluto disponibile".

Dedup: stessa strategia già in uso — raccolta a insieme di asset/lotti colpiti, poi una sola issue con `count` e `group_key` dedicato (`reference_price_fallback`/`reference_price_unavailable`). Il banner esistente supporta già la nozione di "non bloccante" (nessun fail-fast, resto della pagina renderizza comunque).

### 5.6 Raccomandazione

Riusare il framework, non i codici esistenti. Impatto sul piano v1: **basso sul componente banner** (già code-agnostico), **medio sul plumbing API**, perché oggi `/portfolio/lots` e `/portfolio/asset-history` non trasportano `data_quality` — se questi due nuovi casi nascono nel flusso FIFO/asset-detail, il nuovo endpoint `POST /portfolio/lots/analysis` proposto dal piano dovrà includere un campo `data_quality` nella risposta, cosa che il piano attuale non prevede esplicitamente tra i campi di `§9 Risposta concettuale`.

> **Modifica testuale proposta, §9 del piano ("Risposta concettuale")**: aggiungere `data_quality: DataQualityIssue[]` come campo di primo livello della risposta di `POST /portfolio/lots/analysis`, riusando lo schema `DataQualityIssue` esistente e i due nuovi codici `REFERENCE_PRICE_FALLBACK`/`REFERENCE_PRICE_UNAVAILABLE` proposti in questo documento.

---

## 6. Sintesi — decisioni già mature: confermate o da rivedere?

| Decisione | Esito verifica | Note |
|---|---|---|
| Share: motore assoluto + proiezione user-scoped | **Confermata, con evidenza a favore più forte del previsto** | Corregge un bug quantitativo reale (§1.1), non solo un problema di stile. Resta aperta la scelta di *politica* (custodia-attuale vs origine-lotto, §1.3) |
| Transito: `[min,max)` | **Confermata, con evidenza a favore più forte del previsto** | Corregge un buco di valore di ≥1 giorno già presente e verificato empiricamente (§2.2-2.3), non solo una convenzione diversa |
| Split: ADJUSTMENT+ a costo zero è corretto | **Confermata al 100% con verifica numerica** | Il bug è nella modalità "auto" della UI (precompila WAC corrente, non zero), non nella formula. **Nuovo**: reverse split via ADJUSTMENT negativo ha un bug distinto e non preserva il costo (§3.3) |
| Short: lotti distinti ma fase successiva | **Confermata** | Mismatch a tre livelli verificato (validazione/FIFO/Engine); raccomandata guardia esplicita invece di silenzio incoerente |
| Prezzo ADJUSTMENT+: exact → last known → unavailable + banner | **Framework già pronto** | Nessun nuovo componente necessario, solo due nuovi `IssueCode` e un campo `data_quality` nel nuovo endpoint |

---

## 7. Bug scoperti durante questa verifica, fuori dallo scope specifico richiesto

Come da preferenza already nota, questi non sono stati corretti — solo segnalati, da valutare a parte con un piano dedicato se ritenuto utile:

1. **Phantom quantity/cost su TRANSFER tra broker con `share_percentage` diversi** (§1.1) — bug attivo oggi nel Portfolio Engine aggregato (Holdings, dashboard), non solo un problema teorico per il nuovo piano FIFO.
2. **`DataQualityReport.share_mismatch_warnings` mai popolato; `classification.warnings` calcolato e mai letto** (§1.1) — plumbing a metà, mai completato.
3. **`InTransitInterval.share` sempre hardcoded a `1` nonostante il commento "Will be overridden by caller"** (`portfolio_engine.py:324`) — verificato per grep (zero assegnazioni successive nel file) e dal vivo (`interval.share == 1` sempre, indipendentemente dagli share reali dei broker coinvolti). Distinto dal bug #1: qui il valore monetario in transito (`in_transit_asset_market_value`/`in_transit_asset_cost_basis`) usa sempre il 100% del valore della gamba di partenza, mai la quota utente.
4. **Buco di valore di ≥1 giorno nella convenzione attuale di `InTransitInterval`** (§2.2-2.3) — indipendente dal nuovo piano FIFO, corregge un difetto già presente nel dashboard/GrowthChart oggi.
5. **Reverse split via `ADJUSTMENT` negativo riduce il costo totale invece di preservarlo** (§3.3) — bug distinto dal già noto bug dello split diretto, mai segnalato nei report precedenti di questa serie.

---

*Fine report. Nessuna modifica al codice sorgente, al piano originale o al report di fattibilità è stata effettuata durante questa analisi. Gli script di verifica temporanei usati (`/tmp/libreFolio_*_verify.py`) non sono parte della codebase.*
