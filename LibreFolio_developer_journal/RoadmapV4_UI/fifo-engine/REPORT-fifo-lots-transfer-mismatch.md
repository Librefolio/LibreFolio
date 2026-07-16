# Report — Disallineamenti tra Open Lots, Performance e Holdings quando un asset viene trasferito tra broker

> **Stato**: Analisi completata, nessuna modifica al codice applicata.
> **Data**: 2026-07-14
> **Origine**: sessione di debug interattivo su dati BTC nel DB di test, innescata da un'osservazione dell'utente su valori incoerenti tra "Open Lots", "Your Positions" e la lista holdings.
> **Ambito**: `backend/app/services/portfolio_service.py` (`get_lots`, `get_positions_contribution`), `frontend/src/lib/components/brokers/lots/*`, dati di test in `backend/test_scripts/test_db/populate_mock_data.py`.

---

## 1. Sommario esecutivo

Durante un test manuale (acquisto BTC + modifica prezzo su Coinbase, poi trasferimento parziale verso Interactive Brokers), sono emerse **6 osservazioni** di apparente incoerenza tra tre viste diverse dello stesso asset (Bitcoin). Dopo indagine approfondita nel codice backend e frontend, la situazione si riassume così:

| # | Osservazione | Verdetto | Gravità |
|---|---|---|---|
| 1 | "Open Lots" mostra solo Coinbase (0,15/0,15), nessuna bolla per Interactive Brokers | **Bug reale confermato** | Alta — dato visualizzato fuorviante |
| 2 | "Your Positions" (Performance) mostra solo Coinbase | **Comportamento voluto** (se osservato da pagina dettaglio broker) | — |
| 3 | Lista "Portfolio" mostra 0,03 e 0,015 invece di 0,10 e 0,05 | **Corretto** — è la quota di comproprietà (30%) applicata | — |
| 4 | Il grafico WAC/Market Price ha un salto il 30 giugno 2026 | **Causa esterna** — instabilità dei dati storici yfinance | Media (solo su dati di test/dev) |
| 5 | Nessuna bolla il 30 giugno nonostante il salto di prezzo | **Comportamento corretto** — le bolle sono eventi transazionali, non punti del grafico prezzi | — |
| 6 | Il parametro "giorni" mostra 345 vs 26 per lo stesso giorno (18/6) | **Ambiguità di etichetta** — sono due metriche diverse con lo stesso nome | Bassa — solo UX |

**L'unico problema realmente actionable è il punto 1**: la vista *Open Lots* (pannello FIFO) ignora completamente le transazioni di tipo `TRANSFER`, per cui un lotto resta attribuito per sempre al broker dell'acquisto originale, anche dopo un trasferimento reale verso un altro broker. Il broker che riceve l'asset via transfer non ottiene mai un proprio lotto/bolla, anche se detiene fisicamente parte della posizione.

Le sezioni 2-7 spiegano il contesto, i dati di test usati, l'evidenza per ciascun punto, e la sezione 8 propone soluzioni concrete per il punto 1, compatibili con l'architettura esistente.

---

## 2. Contesto: come è stata scoperta l'anomalia

La sessione è partita da un problema **diverso e già risolto** in questa stessa indagine, che vale la pena documentare perché ha lasciato traccia nel codice e nei test:

### 2.1 Bug collegato già corretto in questa sessione: mislabeling della fonte prezzo

Prima di arrivare al problema dei transfer, l'utente aveva segnalato un'incoerenza rosso/verde tra "Performance" e "Open Lots" su un BTC acquistato a 200$ manualmente. L'indagine ha portato a scoprire e correggere (**nella stessa sessione, prima di questo report**):

- **File**: `backend/app/services/asset_source.py`, funzione `bulk_upsert_prices()` (linea ~1207)
- **Bug**: la funzione forzava sempre `source_plugin_key="MANUAL"` su ogni riga scritta, anche quando i dati arrivavano dallo scheduler tramite provider reale (yfinance). Questo:
  1. Rendeva impossibile distinguere dati sincronizzati automaticamente da dati inseriti manualmente.
  2. Lasciava `fetched_at=None` sempre, disattivando silenziosamente `_compute_price_fingerprint()` (`portfolio_engine.py:1868-1891`), il proxy `COUNT + MAX(fetched_at)` usato per invalidare la cache del motore di calcolo portfolio.
  3. Permetteva a righe OHLC internamente incoerenti (es. `close=63560.94` con `high=8692.20`, matematicamente impossibile) di essere persistite senza alcun controllo.
- **Fix applicato**:
  - `bulk_upsert_prices()` ora accetta un parametro opzionale `source_plugin_key` (default `"MANUAL"`, invariato per l'endpoint manuale in `api/v1/assets.py`); lo scheduler (`_persist_single` in `asset_source.py`) passa ora il vero `provider_code`.
  - `fetched_at` viene settato correttamente per i write da provider.
  - Aggiunta una guardia di integrità: se dopo il merge F.4 (sentinel `-1`/`None`/valore) il `close` finale cade fuori da `[low, high]`, quella singola data viene **scartata** (non l'intero batch) con un messaggio di errore esplicito, invece di essere persistita silenziosamente.
- **Verifica**: 71 suite di test backend (30 services + 41 API) tutte verdi dopo il fix, inclusa una regressione scoperta e corretta in `test_prices_sync_delta.py` (il test simulava un cambio prezzo scrivendo solo `close` e lasciando `open/high/low` non coerenti — esattamente il pattern del bug reale, ora giustamente bloccato dalla nuova guardia).

Questo fix **resta valido e indipendente** dal problema descritto in questo report. Viene menzionato perché fa parte della stessa catena investigativa e perché ha involontariamente "resettato" i dati di test manuali dell'utente (ogni run di `./dev.py test` o `./dev.py mkdocs gallery` esegue `db populate --force`, sovrascrivendo il DB condiviso).

### 2.2 Setup di test che ha rivelato il problema dei transfer

Dopo il fix di cui sopra, l'utente ha ricreato il DB (`./dev.py db create-clean` + populate) e ha osservato Bitcoin nella sua configurazione di dati mock standard, che include un trasferimento parziale tra broker. Il ledger completo delle transazioni BTC nel DB di test al momento dell'analisi:

```
id  type      date        quantity  amount    currency  broker            related_transaction_id
22  BUY       2026-06-18   0.15     -1130.38   USD       Coinbase          —
29  TRANSFER  2026-07-06  -0.1      0          USD       Coinbase          30
30  TRANSFER  2026-07-06   0.1      0          USD       Interactive Brokers  29
37  TRANSFER  2026-07-10  -0.05     0          USD       Interactive Brokers  38
38  TRANSFER  2026-07-10   0.05     0          USD       Coinbase          37
```

Fonte: `backend/test_scripts/test_db/populate_mock_data.py`, righe ~1256-1266 (BUY) e sezione "TRANSFER pair" (~1397-1461).

**Bilancio netto per broker** (quantità attualmente detenuta, calcolata a mano dal ledger):
- Coinbase: `0.15 − 0.10 + 0.05 = 0.10 BTC`
- Interactive Brokers: `0.10 − 0.05 = 0.05 BTC`
- Totale: `0.15 BTC` (invariato, corretto — i transfer non creano né distruggono quantità)

**Nota su `amount=-1130.38`** (non `-6450.00` come scritto nel codice a riga 1262): `populate_mock_data.py` contiene una funzione `_derive_market_amount()` (righe 122-145) che **sovrascrive** l'importo fisso nel dizionario di seed con il prodotto `quantità × prezzo_storico_simulato_a_quella_data`, quando la valuta coincide. L'importo fisso nel codice è quindi solo un *fallback* usato se non c'è storico prezzi compatibile — nella pratica, per BTC, viene quasi sempre sostituito dal prezzo simulato realistico del giorno.

### 2.3 Anomalia nei dati prezzo storici (contesto per il punto 4)

Durante l'indagine è stata osservata un'**instabilità reale della fonte dati esterna** (yfinance), verificata con una chiamata live durante la sessione:

```python
import yfinance as yf
yf.Ticker('BTC-USD').history(period='5d')
# 2026-07-13: Open=63757.17  Close=62239.12   (valore ottenuto ORA, in diretta)
```

Ma nel DB, la riga per `2026-07-13` mostra `close=8606.14`. **Interrogazioni live diverse a yfinance, per la stessa data storica, restituiscono valori radicalmente diversi.** Il sistema ha un clock reale impostato al 2026-07-14 (confermato con `date; python3 -c "from datetime import date; print(date.today())"`), quindi le chiamate a yfinance sono chiamate di rete reali, non simulate — ma la sorgente esterna stessa è incoerente nel tempo per questo ticker in questo ambiente (rate limiting HTTP 429 osservato su `query1.finance.yahoo.com`, con retry/fallback che a volte restituiscono dati di regimi di prezzo differenti).

L'intera cronologia prezzi BTC nel DB mostra un pattern a "regimi" ben distinti e internamente coerenti, ma con salti bruschi ai confini:

```
2026-06-24 → 2026-06-29   ~7.7K–8.3K USD   (coerente internamente)
2026-06-30 → 2026-07-12   ~58K–64K USD     (coerente internamente, salto di regime)
2026-07-13 → 2026-07-14   ~8.6K–9.1K USD   (coerente internamente, altro salto)
```

Ogni singola riga **rispetta** l'invariante `low ≤ close ≤ high` (verificato con una query SQL dedicata) — quindi il fix del punto 2.1 sta funzionando: non ci sono più righe internamente corrotte. Il salto **tra** giorni adiacenti è invece un problema di affidabilità della fonte dati esterna nel tempo, non del nostro merge/persistenza. Non è stata implementata alcuna guardia anti-salto-di-prezzo (richiederebbe una decisione di soglia/policy, es. "rifiuta variazioni giornaliere superiori a X%" — proposta ma non implementata, vedi sezione 8.4).

---

## 3. Analisi punto per punto

### 3.1 Punto 1 — Open Lots ignora i TRANSFER (BUG CONFERMATO)

**Componente coinvolto**: `backend/app/services/portfolio_service.py`, metodo `get_lots()` (righe 2331-2430+), usato da `GET /portfolio/lots`, a sua volta chiamato da `frontend/src/lib/components/brokers/lots/FIFOLotsPanel.svelte`.

**Causa esatta**:
```python
# backend/app/services/portfolio_service.py:698
_HOLDING_TYPES = {TransactionType.BUY, TransactionType.SELL}
```
`get_lots()` itera sui broker accessibili e, per ciascuno, richiama:
```python
txns = await self._get_transactions(broker_id, tx_types=_HOLDING_TYPES, date_to=as_of_date)
asset_txns = [t for t in txns if t.asset_id == asset_id]
if not asset_txns:
    continue  # <-- Interactive Brokers finisce qui: zero BUY/SELL per BTC
```
Poi passa `asset_txns` (solo BUY/SELL) a `calculate_fifo_lots()` (`backend/app/utils/financial/fifo_utils.py:66`), che è **deliberatamente e correttamente** una funzione pura che non conosce i TRANSFER (per design — il suo docstring dice esplicitamente "the caller is responsible for filtering out other transaction types").

**Conseguenza osservata**:
- Coinbase: 1 BUY di 0.15 BTC → FIFO calcola un lotto aperto 0.15/0.15 — **come se il TRANSFER out non fosse mai avvenuto**. Il lotto resta "pieno" per sempre nel calcolo, anche se in realtà solo 0.10 BTC risiede fisicamente su Coinbase.
- Interactive Brokers: 0 transazioni BUY/SELL per BTC → `asset_txns` è vuoto → `continue` → **nessun lotto prodotto**, quindi nessuna bolla in `BubbleLotTimeline.svelte`, nonostante IB detenga realmente 0.05 BTC.

**Impatto**: la vista "Open Lots"/FIFO Lots Panel produce un quadro contabilmente scorretto quando un asset viene trasferito tra broker propri — mostra il 100% del lotto originale ancora attaccato al broker di acquisto, e zero visibilità sul broker che ha effettivamente ricevuto quota dell'asset via transfer.

**Da notare**: questo NON è un problema di calcolo P&L complessivo (il costo base totale e la quantità totale restano giusti se aggregati su tutti i broker), ma di **attribuzione per broker** — esattamente il tipo di errore che genera le bolle mancanti osservate dall'utente.

### 3.2 Punto 2 — "Your Positions" mostra solo Coinbase (comportamento voluto, verosimilmente)

**Componente coinvolto**: `frontend/src/routes/(app)/brokers/[id]/+page.svelte`, riga 563 (broker detail) vs `frontend/src/routes/(app)/dashboard/+page.svelte`, riga 709 (dashboard).

Se l'utente stava visualizzando la pagina di dettaglio del broker Coinbase, il comportamento è **intenzionale**:
```svelte
<!-- brokers/[id]/+page.svelte:563 -->
<FIFOLotsPanel ... brokerIds={[broker.id]} ... />
```
contro
```svelte
<!-- dashboard/+page.svelte:709 -->
<FIFOLotsPanel ... brokerIds={activeBrokerIds ?? allBrokers.map((b) => b.id)} ... />
```
La pagina dettaglio broker filtra **deliberatamente** su un solo broker (ha senso: è la pagina "Coinbase", non "tutti i miei asset"). Il dashboard invece, senza filtro attivo, passa tutti i broker.

Questo punto **condivide la stessa causa radice del punto 1**: anche sul dashboard (tutti i broker passati), se il calcolo FIFO per-broker ignora i TRANSFER, il broker Coinbase mostrerebbe comunque l'intero lotto e Interactive Brokers zero, semplicemente perché nessuna riga verrebbe mai generata per IB indipendentemente dal filtro broker applicato a monte. Il filtro per singolo broker nella pagina di dettaglio *aggrava* la percezione del problema ma non ne è la causa.

### 3.3 Punto 3 — Le quantità 0,03 e 0,015 sono corrette (comproprietà)

**Verificato direttamente sul DB**:
```sql
SELECT user_id, username, broker_name, share_percentage FROM broker_user_access ...
-- e2e_test_user | Coinbase             | 0.3
-- e2e_test_user | Interactive Brokers  | 0.3
```
`e2e_test_user` possiede il 30% di quota su entrambi i broker. Applicando la quota alle quantità nette reali:
```
Coinbase:  0.10 × 0.3 = 0.03   ✓ combacia esattamente
IB:        0.05 × 0.3 = 0.015  ✓ combacia esattamente
```
Questa vista (probabilmente la tabella Holdings/Positions in modalità "Portfolio" — non ContributionTable, che non ha colonna quantità) **calcola correttamente sia i transfer sia la quota di comproprietà**, a differenza di `get_lots()`. È la controprova che il resto del sistema (holdings/posizioni) gestisce già i TRANSFER correttamente — solo il pannello FIFO Lots ne è rimasto escluso.

### 3.4 Punto 4 e 5 — Salto di prezzo e bolla assente il 30 giugno (causa esterna, comportamento corretto)

Vedi sezione 2.3 per l'evidenza sul salto di prezzo (fonte dati esterna instabile, non un bug interno). L'assenza di bolla il 30 giugno è **corretta**: `BubbleLotTimeline.svelte` disegna una bolla per ogni evento di acquisto/vendita (transazione), non un punto per ogni giorno del calendario. Il 30 giugno non è una data di transazione per questo asset — solo una data in cui il *grafico prezzi* (serie continua, non eventi) mostra un salto. Il WAC stesso non cambia realmente quel giorno (nessuna nuova transazione); l'impressione di un "salto anche nel WAC" è quasi certamente un effetto del riscalamento automatico dell'asse Y del grafico (ECharts) quando la serie "Market Price" cambia bruscamente ordine di grandezza — la linea WAC, pur restando a valore costante, appare visivamente spostata perché la scala del grafico è cambiata.

### 3.5 Punto 6 — "Days" 345 vs 26: due metriche distinte, stessa etichetta (ambiguità UX)

| Componente | Calcolo | File/riga | Valore per il 18/6 |
|---|---|---|---|
| Bolla acquisto (`BubbleLotTimeline`) | `holdingDaysBetween(buy_date, oggi)` — giorni di possesso | `BubbleLotTimeline.svelte:167,237` | 26 (18 giu → 14 lug) |
| Tooltip grafico WAC (`AssetWacPriceChart`) | `elapsedDaysBetween(chartStartDate, punto)` — giorni dall'inizio dello storico caricato nel grafico | `AssetWacPriceChart.svelte:178,328,471` | 345 (~7 lug 2025 → 18 giu 2026) |

`chartStartDate` è calcolato come la data minima tra tutti i punti dati caricati nel grafico (`AssetWacPriceChart.svelte:328-334`), che coincide con l'inizio dello storico prezzi simulato (`~2025-07-07`, confermato via query SQL). Non è un bug di dati: sono semplicemente due metriche diverse — "giorni di possesso della posizione" contro "posizione del punto lungo l'asse temporale del grafico" — che condividono l'etichetta generica "Days" nell'interfaccia, generando confusione legittima.

---

## 4. Riferimenti di codice (riepilogo)

| File | Righe | Ruolo |
|---|---|---|
| `backend/app/services/portfolio_service.py` | 698 | Definizione `_HOLDING_TYPES = {BUY, SELL}` — causa del punto 1 |
| `backend/app/services/portfolio_service.py` | 2331-2430 | `get_lots()` — ciclo per-broker che ignora TRANSFER |
| `backend/app/utils/financial/fifo_utils.py` | 17-90 | `calculate_fifo_lots()` — funzione pura, per design non gestisce TRANSFER (comportamento corretto per questa funzione) |
| `backend/app/schemas/portfolio.py` | 455-488 | `OpenLotSchema`, `ClosedLotSchema`, `FIFOLotsResponse` |
| `frontend/src/lib/components/brokers/lots/FIFOLotsPanel.svelte` | 42-186 | Riceve `brokerIds` come prop, non decide da solo lo scope broker |
| `frontend/src/lib/components/brokers/lots/BubbleLotTimeline.svelte` | 167,237,432,438 | Calcolo "holding days" per bolla |
| `frontend/src/lib/components/brokers/lots/AssetWacPriceChart.svelte` | 178,328,471 | Calcolo "elapsed days" per tooltip grafico |
| `frontend/src/routes/(app)/brokers/[id]/+page.svelte` | 563 | `brokerIds={[broker.id]}` — scope singolo broker, per design |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | 709 | `brokerIds={activeBrokerIds ?? allBrokers...}` — scope multi-broker |
| `backend/test_scripts/test_db/populate_mock_data.py` | 122-145, 1256-1266, 1397-1461 | `_derive_market_amount()`, seed BUY BTC, seed TRANSFER pair |
| `backend/app/services/asset_source.py` | ~1207-1391, ~2645-2665 | Fix già applicato in questa sessione (§2.1) |

---

## 5. Cosa NON è stato modificato

Su esplicita richiesta dell'utente, **nessuna modifica al codice è stata applicata** per i punti descritti in questo report (a differenza del bug OHLC/source_plugin_key del §2.1, corretto in una fase precedente della stessa sessione con relativa suite di test verificata). Questo documento è puramente analitico; le proposte della sezione 8 richiedono approvazione prima dell'implementazione.

---

## 6. Rischi di non intervenire

- **Fiducia nei dati**: un utente che trasferisce asset tra broker propri (operazione comune, es. consolidamento su un broker più economico) vedrà la propria cronologia FIFO "sparire" dal broker di destinazione, con rischio di interpretare erroneamente la propria posizione fiscale/di costo storico.
- **Inconsistenza tra viste**: la lista Holdings/Positions (corretta) e il pannello Open Lots (non corretto) raccontano storie diverse per lo stesso asset — mina la percezione di affidabilità dell'intera sezione "Positions".
- **Superficie di test**: qualsiasi test E2E futuro su asset trasferiti tra broker (es. `tx-paired-edit.spec.ts` o simili) rischia di non intercettare questo gap se non verifica esplicitamente il pannello FIFO Lots dopo un transfer.

---

## 7. Cosa funziona già bene (da non toccare)

- Il calcolo di holdings/quantità corrente per broker (usato da Positions/Holdings table) **già gestisce correttamente** sia i TRANSFER sia la quota di comproprietà (`share_percentage`) — vedi §3.3. Qualsiasi soluzione dovrebbe riusare questa logica come riferimento di correttezza, non reinventarla.
- `calculate_fifo_lots()` come funzione pura è ben progettata, testata e usata in più punti (WAC, positions_contribution) — le proposte in sezione 8 **non modificano questa funzione**, solo il modo in cui viene chiamata/i risultati vengono ricomposti in `get_lots()`.
- Il fix del §2.1 (guardia di integrità OHLC + tracciamento provenienza) resta valido e non necessita ulteriori interventi legati a questo report.

---

## 8. Proposte di modifica alla visualizzazione (compatibili col sistema attuale)

Tutte le opzioni seguenti sono pensate per **non modificare** `calculate_fifo_lots()` (funzione pura, condivisa, ben testata) e per riusare i dati già disponibili (`related_transaction_id` collega già ogni coppia di TRANSFER nel DB — non serve nuovo schema).

### 8.1 Opzione A — Redistribuzione post-calcolo dei lotti tra broker (raccomandata)

**Idea**: lasciare `get_lots()` calcolare i lotti per-broker come oggi (solo BUY/SELL), poi aggiungere un **passo di redistribuzione** che sposta quota dei lotti aperti dal broker mittente al broker destinatario in base ai TRANSFER effettivamente avvenuti, preservando `buy_date`/`buy_price` originali (il costo storico non cambia mai con un transfer).

**Come**:
1. Dopo il ciclo esistente per-broker in `get_lots()`, raccogliere tutte le transazioni `TRANSFER` per l'asset (già disponibili da `_get_transactions`, basta non filtrarle via `_HOLDING_TYPES` in una query separata), accoppiate via `related_transaction_id`, ordinate per data.
2. Per ogni transfer netto (broker A → broker B, quantità Q, data D): consumare FIFO gli `open_lot_schemas` **già calcolati per il broker A** fino a Q (stesso algoritmo "consuma dalla testa" già presente in `calculate_fifo_lots`, riusabile o replicabile in poche righe), e aggiungere/aumentare corrispondenti voci in `open_lot_schemas` per il broker B con lo stesso `buy_date`/`buy_price` del lotto consumato (eventualmente split se il transfer non coincide esattamente con un lotto intero).
3. Il risultato finale (`open_lot_schemas`) riflette la **posizione fisica corrente per broker**, non solo l'acquisto originale.

**Pro**: non tocca il motore FIFO condiviso; isolato in un unico metodo; compatibile con `OpenLotSchema` esistente (nessuna modifica di schema necessaria); riusa `related_transaction_id` già presente.
**Contro**: richiede scrivere una piccola funzione di "redistribuzione FIFO" ad-hoc (non enorme, ma nuova logica da testare con cura, specialmente sui casi limite di split parziale di un lotto tra più broker).

### 8.2 Opzione B — FIFO combinato cross-broker con broker "corrente" mutabile

**Idea**: invece di lanciare `calculate_fifo_lots()` una volta per broker, lanciarlo **una sola volta** per l'intero asset con tutte le transazioni BUY/SELL di tutti i broker accessibili insieme, poi aggiungere manualmente la logica di "spostamento" broker sui lotti risultanti in base ai TRANSFER, sempre ordinati per data.

**Pro**: concettualmente più vicino a "un lotto = un'entità che può cambiare broker nel tempo", più intuitivo da spiegare.
**Contro**: cambia il modo in cui `get_lots()` interroga le transazioni (da per-broker a globale-poi-filtrato), tocca più codice del necessario, maggiore rischio di regressione su casi con più utenti/permessi diversi per broker (dato che oggi il ciclo è già scoped per `access` con `share_percentage` per broker).

**Verdetto**: l'Opzione A è preferibile perché isola il cambiamento e riusa la struttura esistente per-broker (inclusa la gestione già presente della quota di comproprietà per broker).

### 8.3 Opzione C — Fix minimo solo di visualizzazione (nessun cambiamento backend)

**Idea**: senza tocca il backend, il frontend potrebbe mostrare un badge/tooltip su un lotto quando la sua quantità rimanente supera la quantità netta attualmente detenuta su quel broker (dato già disponibile lato frontend dalle Holdings), con un messaggio tipo *"Parte di questo lotto è stata trasferita ad altri broker"*.

**Pro**: zero rischio, implementabile in un pomeriggio, nessun test backend da riscrivere.
**Contro**: **non risolve il problema di fondo** — il broker destinatario (IB) continuerebbe a non avere alcuna bolla/riga propria. È un cerotto di trasparenza, non una correzione.

**Verdetto**: adatta solo come soluzione-ponte a bassissimo costo se l'Opzione A richiede più tempo di quanto disponibile a breve termine; da NON considerare come soluzione definitiva.

### 8.4 Nota collaterale — guardia anti-salto di prezzo (dal punto 4)

Non direttamente collegata ai TRANSFER, ma emersa dalla stessa indagine (§2.3): si potrebbe aggiungere una guardia opzionale in `bulk_upsert_prices()` (stesso punto del fix §2.1) che segnala (senza necessariamente rifiutare) variazioni giorno-su-giorno superiori a una soglia configurabile (es. 40-50%) per asset volatili come crypto, loggando un warning invece di un rifiuto silenzioso. Richiede una decisione di prodotto sulla soglia (diversa per asset class) — **non proposta come implementazione immediata**, solo come possibile lavoro futuro se le anomalie di fonte dati esterna (yfinance) si rivelano frequenti anche in produzione, non solo in questo ambiente di test.

---

## 9. Prossimi passi suggeriti

1. Decidere se procedere con l'Opzione A (raccomandata) per il fix del punto 1.
2. Se approvata, scrivere prima un test di regressione mirato (`backend/test_scripts/test_services/` o `test_api/`) che riproduca esattamente lo scenario di questo report (BUY su broker A, TRANSFER parziale verso B, verifica che `get_lots()` ritorni lotti coerenti su **entrambi** i broker con quantità che sommano al totale corretto) — così da avere un contratto chiaro prima di toccare `get_lots()`.
3. Estendere la copertura E2E frontend (`frontend/e2e/transactions/tx-paired-edit.spec.ts` o un nuovo file dedicato) per verificare che il pannello FIFO Lots mostri una bolla per ciascun broker coinvolto in un transfer.
4. Valutare separatamente (non urgente) la nota §8.4 sulla guardia anti-salto prezzo, solo se il problema si ripresenta fuori da questo ambiente di test.
