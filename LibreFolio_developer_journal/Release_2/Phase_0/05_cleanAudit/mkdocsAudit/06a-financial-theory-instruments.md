# 06A — Teoria: strumenti e fondamenti

> **Release 2 · Phase 0 · 05_cleanAudit · mkdocsAudit**
>
> Sola verifica. Nessuna correzione di codice, documentazione o dati di test fa
> parte di questo report. Baseline condivisa con [00_INDEX](00_INDEX.md):
> commit `09cbb7e28f4e4e4bba9f9d40748b98e1876f5103`, branch `dev_release2`,
> worktree dirty (elenco in `00_INDEX.md`), acquisita `2026-08-05T10:54:55+02:00`.

## Ambito di questo report

34 pagine EN pubblicate, esattamente:

- `financial-theory/fundamentals/**/*.en.md` (4)
- `financial-theory/instruments/**/*.en.md` (26, incluse le sotto-cartelle
  `asset-events/`, `asset-types/`, `transaction-types/`)
- `financial-theory/portfolio-theory/**/*.en.md` (3)
- `financial-theory/index.en.md` (1)

Esclusi da questo report (di competenza di 06B/06C o di altri report
dell'indice): `technical-analysis/**` (indicatori, benchmark sintetici,
performance metrics, FIFO engine, risk metrics), developer guide, traduzioni,
manuale utente, admin, AI Export, FX.

Confrontate solo le claim presentate come comportamento o terminologia
**implementati** in LibreFolio (nomi di enum, percorsi di file, formule
riprodotte da codice, regole di validazione, comportamento di provider/plugin
specifici). La teoria finanziaria generale senza legame con una feature di
LibreFolio è classificata `fuori standard di codice` e non trattata come
reperto.

## Copertura (34/34 pagine)

| # | Pagina | Esito |
|---:|---|---|
| 1 | `financial-theory/index.en.md` | Pulita — indice concettuale, nessuna claim implementativa propria |
| 2 | `fundamentals/index.en.md` | Pulita — indice, nessuna claim implementativa propria |
| 3 | `fundamentals/day-count.en.md` | 🔴 **R-01** — percorso file errato |
| 4 | `fundamentals/returns.en.md` | Pulita — link e claim verificati |
| 5 | `fundamentals/taxation.en.md` | Pulita — claim FIFO verificate |
| 6 | `instruments/index.en.md` | Pulita — indice, nessuna claim implementativa propria |
| 7 | `instruments/asset-events/index.en.md` | 🟡 **R-06** (omissione minore) + nota su dedup (info) |
| 8 | `instruments/asset-events/dividend.en.md` | 🔴 **R-02** — claim Scheduled Investment errata |
| 9 | `instruments/asset-events/interest.en.md` | Pulita — tutte le claim verificate |
| 10 | `instruments/asset-events/maturity-settlement.en.md` | 🟡 **R-07** (omissione minore) |
| 11 | `instruments/asset-events/price-adjustment.en.md` | Pulita — formula verificata |
| 12 | `instruments/asset-events/split.en.md` | Pulita — direzione ratio verificata |
| 13 | `instruments/asset-types/index.en.md` | 🟡 **R-04** — omissione codice `INDEX` |
| 14 | `instruments/asset-types/bonds.en.md` | Pulita — parte descrittiva è teoria generale |
| 15 | `instruments/asset-types/commodities.en.md` | Pulita |
| 16 | `instruments/asset-types/crypto.en.md` | Pulita |
| 17 | `instruments/asset-types/etfs.en.md` | Pulita — provider verificati (justETF, CSS Scraper) |
| 18 | `instruments/asset-types/index-benchmark.en.md` | 🟡 **R-04** (stesso reperto di #13) |
| 19 | `instruments/asset-types/mutual-fund.en.md` | Pulita |
| 20 | `instruments/asset-types/other.en.md` | Pulita — provider verificati |
| 21 | `instruments/asset-types/real-estate.en.md` | Pulita — `CROWDFUND → SCHEDULED_YIELD` verificato |
| 22 | `instruments/asset-types/stocks.en.md` | Pulita |
| 23 | `instruments/transaction-types/index.en.md` | Pulita — enum `TransactionType` verificato 1:1 |
| 24 | `instruments/transaction-types/adjustment.en.md` | 🔴 **R-03** — claim "senza override" errata |
| 25 | `instruments/transaction-types/buy-sell.en.md` | Pulita — FIFO runtime e assenza LIFO verificate |
| 26 | `instruments/transaction-types/cash-transfer.en.md` | Pulita — vincoli promote verificati |
| 27 | `instruments/transaction-types/deposit-withdrawal.en.md` | 🔴 **R-05** — claim Crédit Agricole invertita |
| 28 | `instruments/transaction-types/dividend-interest.en.md` | Pulita |
| 29 | `instruments/transaction-types/fee.en.md` | Pulita — allocazione lotto/portfolio verificata |
| 30 | `instruments/transaction-types/fx-conversion.en.md` | Pulita — formule spread/implied rate verificate 1:1 |
| 31 | `instruments/transaction-types/transfer.en.md` | Pulita — vincoli promote e pattern successione verificati |
| 32 | `portfolio-theory/index.en.md` | Fuori standard di codice — MPT/frontiera efficiente, teoria pura |
| 33 | `portfolio-theory/asset-allocation.en.md` | Fuori standard di codice — teoria pura |
| 34 | `portfolio-theory/diversification.en.md` | Fuori standard di codice — teoria pura |

**Navigazione/link**: controllo automatico dei 184 link Markdown interni
presenti nelle 34 pagine (verso qualunque destinazione nel sito, non solo
verso lo scope) → **0 link rotti**.

---

## 🔴 Reperti

### R-01 — `day-count.en.md`: percorso file inesistente per `calculate_day_count_fraction()`

- **Pagina/riga**: `fundamentals/day-count.en.md:10`
- **Claim**: *"The function `calculate_day_count_fraction()` in
  `backend/app/utils/financial_math.py` implements all four conventions..."*
- **Controprova**: `backend/app/utils/financial_math.py` **non esiste** nel
  repository (verificato con `find`). La funzione è realmente definita in
  `backend/app/services/asset_source_providers/scheduled_investment.py:71`,
  sotto il commento di sezione `# FINANCIAL MATH — Day count conventions &
  simple interest` (riga 66). Non esiste alcun modulo `backend/app/utils/*`
  con quel nome o contenuto equivalente (elenco completo di
  `backend/app/utils/` verificato).
- **Classificazione**: Dettaglio obsoleto (riferimento a percorso file).
- **Gravità**: minor · **Confidenza**: alta.
- **Impatto / direzione di correzione**: un contributor che cerca il file
  indicato non lo trova. La parte restante della claim (provider Scheduled
  Investment, default ACT/365, firma e comportamento della funzione) è
  **corretta** — verificato codice `scheduled_investment.py:71-99` e default
  `DayCountConvention.ACT_365` in `backend/app/schemas/assets.py:301`. La
  correzione consiste nell'aggiornare solo il percorso file citato.

### R-02 — `dividend.en.md`: Scheduled Investment non genera mai eventi `DIVIDEND`

- **Pagina/riga**: `instruments/asset-events/dividend.en.md:80`
- **Claim**: *"For market-priced assets (Yahoo Finance, justETF), dividend
  events are informational... For **Scheduled Investment** assets, they are
  integral to the price model."*
- **Controprova**: `grep -n "DIVIDEND"
  backend/app/services/asset_source_providers/scheduled_investment.py`
  restituisce **zero occorrenze**. Il provider Scheduled Investment genera
  solo `INTEREST`, `PRICE_ADJUSTMENT` e `MATURITY_SETTLEMENT`
  (`scheduled_investment.py:345-373, 385-392, 500-505` e docstring di modulo
  riga 27: *"auto_events: list of FAAssetEventPoint auto-generated (INTEREST +
  MATURITY_SETTLEMENT)"*). L'enum `AssetEventType.DIVIDEND` in
  `backend/app/db/models.py:182-190` è descritto come "Cash distribution from
  equity/ETF" — coerente solo con asset a mercato, non con Scheduled
  Investment. La pagina gemella `interest.en.md` contiene la frase corretta
  ("For Scheduled Investment provider assets, interest events are generated
  automatically... and directly affect the price calculation"), il che
  suggerisce un copia-incolla tra le due pagine con lo scambio dei ruoli
  Dividend/Interest.
- **Classificazione**: Contraddizione.
- **Gravità**: major · **Confidenza**: alta.
- **Impatto / direzione di correzione**: la frase induce a pensare che asset
  Scheduled Investment (tipico per crowdfunding/P2P, vedi `real-estate.en.md`)
  possano avere eventi dividendo nativi nel motore di pricing — non è
  possibile. Correzione: sostituire l'ultima frase con un riferimento a
  `INTEREST`/`PRICE_ADJUSTMENT`/`MATURITY_SETTLEMENT` oppure rimuoverla,
  rispecchiando `interest.en.md`.

### R-03 — `adjustment.en.md`: "senza override" non produce un lotto a costo zero, blocca la transazione

- **Pagina/riga**: `instruments/transaction-types/adjustment.en.md:46-47`
- **Claim**: *"With override: the specified value is used as the per-unit
  acquisition cost... Without override: the lot is created with zero cost
  (free acquisition — e.g. gifts, airdrops)."*
- **Controprova**: `TransactionService._requires_cost_basis()`
  (`backend/app/services/transaction_service.py:233-241`) ritorna `True` per
  `ADJUSTMENT` con `quantity > 0`. Nella pipeline `execute_batch` (stesso
  file, blocco "6d", righe 1455-1531) ogni creazione/aggiornamento con
  `_requires_cost_basis(tx) == True` e `tx.cost_basis_override is None` genera
  un `TXValidationIssue` con codice `COST_BASIS_REQUIRED`
  (`"{type} with qty>0 requires cost_basis_override"`, righe 1492, 1511,
  1528). Al passo "8. Decision" (righe 1551-1558): `if issues: return
  TXBatchResponse(committed=False, ...)` — **qualunque issue blocca il
  commit**, non esiste un percorso che persista la transazione con costo
  implicito zero. L'unico modo per ottenere un costo diverso da un valore
  manuale esplicito è `cost_basis_mode="auto"/"auto-detail"`, che calcola il
  WAC (non "zero"), non un bypass silenzioso.
- **Classificazione**: Contraddizione.
- **Gravità**: major · **Confidenza**: alta (dimostrata a livello di codice
  end-to-end: metodo di validazione → issue → blocco del commit).
- **Impatto / direzione di correzione**: un utente che segue la pagina per
  registrare un regalo/airdrop senza specificare `cost_basis_override` si
  aspetta un lotto a costo zero, ma riceve un errore di validazione
  (`costBasisRequired`) e la transazione non viene salvata. Correzione:
  chiarire che `cost_basis_override` è **obbligatorio** per `ADJUSTMENT` con
  quantità positiva salvo `cost_basis_mode="auto"`; per un costo zero
  esplicito l'utente deve impostare l'override a `0`, non ometterlo.

### R-04 — `asset-types/index.en.md` + `index-benchmark.en.md`: omesso il vero `AssetType.INDEX`

- **Pagina/riga**: `instruments/asset-types/index.en.md:17` (colonna Code =
  `` ` — ` ``) e `instruments/asset-types/index-benchmark.en.md:11`
  (*"Tradeable? Not directly — but ETFs and futures track indexes"*).
- **Claim**: la riga della tabella presenta "Index & Benchmark" senza un
  codice proprio, e la pagina dedicata non menziona mai un asset type nativo
  — solo l'uso indiretto tramite ETF/futures o il segnale "Asset Comparison".
- **Controprova**: `AssetType` in `backend/app/db/models.py:145-178` include
  **`INDEX = "INDEX"`** come membro di prima classe, con docstring esplicita
  (riga 158): *"INDEX: Market indices and benchmarks (e.g., S&P 500, MSCI
  World) — no transactions allowed"* e valuation_model di default
  `MARKET_PRICE (read-only benchmark, no transactions)`. Il frontend espone
  `INDEX` come opzione selezionabile nel form di creazione asset:
  `frontend/src/lib/utils/assetTypes.ts:28` (`INDEX: 'index'` nella
  `PNG_MAP`) e `ASSET_TYPES = schemas.AssetType.options` (riga 17) che deriva
  le opzioni direttamente dall'enum backend via Zod — quindi l'utente **può**
  creare un asset di tipo `INDEX` dalla UI standard.
- **Classificazione**: Omissione.
- **Gravità**: minor · **Confidenza**: alta.
- **Impatto / direzione di correzione**: le due pagine descrivono
  correttamente il concetto finanziario di indice, ma non documentano una
  capacità reale e distinta di LibreFolio (un vero `AssetType.INDEX`,
  read-only, senza transazioni). Correzione: aggiungere `INDEX` alla tabella
  codici in `index.en.md` e una sezione in `index-benchmark.en.md` che
  spieghi il comportamento "read-only, nessuna transazione ammessa".

### R-05 — `deposit-withdrawal.en.md`: comportamento Crédit Agricole invertito

- **Pagina/riga**: `instruments/transaction-types/deposit-withdrawal.en.md:31`
- **Claim**: *"Crédit Agricole uses this model [DEPOSIT+BUY /
  SELL+WITHDRAWAL]; coupons and maturity premiums remain income and do not
  receive counter-entries."*
- **Controprova**: il docstring di modulo di
  `backend/app/services/brim_providers/broker_credit_agricole.py:52-56`
  afferma l'esatto contrario: *"the plugin adds same-day cash counter-entries
  so the broker cash nets to zero: DEPOSIT before every cash BUY, WITHDRAWAL
  after every SELL, **and a balancing WITHDRAWAL after every coupon (CEDOLA)
  and maturity-premium INTEREST leg**. Succession transfers carry no
  counter-entry (a cashless ADJUSTMENT)."* Il comportamento è implementato,
  non solo documentato: righe 536-542 dello stesso file, commento *"A coupon
  (CEDOLA -> INTEREST) is income with no bank-cash counterpart in this
  securities-only export; balance it with a WITHDRAWAL..."* seguito dalla
  chiamata `add_cash_counter_entry(..., tx_type=TransactionType.WITHDRAWAL,
  ...)`. La stessa funzione è usata per il premio di scadenza bond (righe
  515-528, causale `TITOLI SCADUTI`). Solo le righe di successione
  (`GIRO ALTRO DOSSIER` / `VERS.TITOLI`) sono davvero prive di
  contropartita, come correttamente descritto in `transfer.en.md`.
- **Classificazione**: Contraddizione.
- **Gravità**: major · **Confidenza**: alta (docstring + implementazione
  concordi, entrambi opposti alla pagina).
- **Impatto / direzione di correzione**: un lettore che usa questa pagina
  per capire come un broker-import mantiene la cassa a zero conclude
  l'opposto della realtà per cedole e premi di scadenza. Correzione:
  invertire la frase — "coupons and maturity premiums **do** receive a
  balancing WITHDRAWAL counter-entry; only succession transfers (in-kind,
  cashless ADJUSTMENT) do not."

---

## 🟡 Reperti minori / informativi

### R-06 — `asset-events/index.en.md`: justETF non menzionato tra le fonti di eventi `DIVIDEND`

- **Pagina/riga**: `instruments/asset-events/index.en.md:38-39` (sezione
  "Sources of Events → Provider-generated"), elenca solo *"Yahoo Finance: may
  produce DIVIDEND events from historical data"*.
- **Controprova**: `backend/app/services/asset_source_providers/justetf.py:408-425`
  genera eventi `DIVIDEND` a partire dalla colonna `dividends` del chart
  data (`type="DIVIDEND"`, riga 419; log `"Parsed {len(events)} DIVIDEND
  events for {identifier} from chart data"`, riga 425).
- **Classificazione**: Omissione · **Gravità**: info · **Confidenza**: alta.
- **Impatto**: elenco incompleto ma non fuorviante (justETF è comunque citato
  altrove, es. `dividend.en.md:80`, come fonte "market-priced" informativa).
  Correzione: aggiungere una riga *"justETF: produces DIVIDEND events from
  chart data"*.

**Nota informativa (non reperto)** sulla stessa pagina, riga 40: la frase
*"deduplication on asset_id + date + type"* è corretta ma incompleta — la
query di cancellazione in
`backend/app/services/asset_source.py:1544-1552`
(`_upsert_asset_events`) filtra **anche** su `provider_assignment_id`, quindi
il dedup è realmente scoped per-provider: eventi generati da provider diversi
sullo stesso `(asset_id, date, type)` possono coesistere. Non altera la
sostanza della claim per il caso comune (singolo provider, sync ripetuti).

### R-07 — `maturity-settlement.en.md`: comportamento "late interest" post-maturità non documentato

- **Pagina/riga**: `instruments/asset-events/maturity-settlement.en.md:13,
  68, 70` — *"The instrument ceases to exist — no further pricing or
  trading"*, *"The asset's price series ends at the maturity date"*, *"won't
  receive new price data"*.
- **Controprova**: `scheduled_investment.py` implementa un meccanismo di
  *late interest* (config `FALateInterestConfig`) che **continua ad
  accumulare valore dopo `maturity_date`** durante un periodo di grazia e
  oltre, con eventi `MATURITY_SETTLEMENT` posticipati (righe 533-621,
  744-761, 817-877: `_compute_late_interest_value`, `grace_end`,
  `late_start`, generazione di nuovi `FAPricePoint`/`MATURITY_SETTLEMENT`
  dopo la data di scadenza originale).
- **Classificazione**: Omissione · **Gravità**: minor · **Confidenza**:
  media-alta (funzionalità reale ma di nicchia — pagamenti in ritardo su
  asset Scheduled Investment).
- **Impatto**: la formula piecewise mostrata in pagina
  (`price(d) = settlement_amount if d ≥ maturity`) è corretta per il caso
  standard, ma tace il caso "pagamento in ritardo" in cui il prezzo continua
  a essere calcolato oltre la data di scadenza formale. Correzione:
  aggiungere una nota su "late interest / grace period" con link incrociato,
  se ritenuto rilevante per il pubblico di questa pagina teorica.

---

## ✅ Claim verificate e correttamente implementate

Elenco delle claim più significative controllate positivamente (codice
coerente con la pagina), a beneficio di eventuale futura manutenzione:

| Claim | Pagina | Verificata in |
|---|---|---|
| `AssetType` = STOCK/ETF/BOND/CRYPTO/FUND/CROWDFUND/HOLD/OTHER | `asset-types/index.en.md` | `backend/app/db/models.py:170-178` |
| `AssetEventType` = DIVIDEND/INTEREST/PRICE_ADJUSTMENT/SPLIT/MATURITY_SETTLEMENT | `asset-events/index.en.md` | `backend/app/db/models.py:182-190` |
| `TransactionType` (12 codici, incl. sign rules) | `transaction-types/index.en.md` | `backend/app/db/models.py:266-278`, `backend/app/schemas/transactions.py:114-197` |
| DIVIDEND: `quantity=0`, asset **obbligatorio** | `dividend.en.md`, `interest.en.md` | `backend/app/schemas/transactions.py:114-123, 190` (Rule 5, Rule 11) |
| INTEREST: `quantity=0`, asset **opzionale** | `interest.en.md` | `backend/app/schemas/transactions.py:125` (Rule 6) |
| FIFO calcolato a runtime, non persistito (nessuna tabella "lots") | `buy-sell.en.md`, `taxation.en.md` | `backend/app/services/fifo_lot_engine.py` (nessun `class *Lot*(table=True)` in `models.py`) |
| LIFO/specific-id non ancora implementati ("potential future") | `buy-sell.en.md` | `grep -rl LIFO backend/app frontend/src` → nessun risultato |
| Direzione ratio SPLIT: `quantity × ratio`, `unit_price / ratio` | `split.en.md` | `backend/app/services/fifo_lot_engine.py:757-758` |
| Formula `price(d) = base_value(d) + Σ PRICE_ADJUSTMENT` | `price-adjustment.en.md` | `scheduled_investment.py:500-505` |
| Scheduled Investment genera `INTEREST` + `PRICE_ADJUSTMENT` (+ `MATURITY_SETTLEMENT`) | `asset-events/index.en.md` | `scheduled_investment.py:245-251, 345-392` |
| Yahoo Finance genera eventi `DIVIDEND` | `asset-events/index.en.md`, `dividend.en.md` | `yahoo_finance.py:441-447` |
| Default day-count `ACT/365` | `day-count.en.md` | `backend/app/schemas/assets.py:301` |
| `calculate_day_count_fraction()` implementa le 4 convenzioni | `day-count.en.md` | `scheduled_investment.py:71-99` (percorso file errato, vedi R-01) |
| WAC auto-computation su TRANSFER/ADJUSTMENT ricevente | `adjustment.en.md` | `backend/app/services/transaction_service.py:1428-1466, 1566+`; `backend/app/utils/financial/wac_utils.py` |
| Cost basis override = per-unit, moltiplicato per quantità | `adjustment.en.md` | `backend/app/schemas/transactions.py:265-271` |
| Promote ADJUSTMENT+ADJUSTMENT → TRANSFER (stesso asset, broker diversi, quantità opposte) | `adjustment.en.md`, `transfer.en.md` | `backend/app/schemas/transactions.py:1238-1247` |
| Promote WITHDRAWAL+DEPOSIT → CASH_TRANSFER (stessa valuta, broker diversi, importi opposti) | `cash-transfer.en.md` | `backend/app/schemas/transactions.py:1298-1311` |
| Promote WITHDRAWAL+DEPOSIT → FX_CONVERSION (valute diverse, stesso broker) | `fx-conversion.en.md` | `backend/app/schemas/transactions.py:1276-1286` |
| Formula implied rate `= |target|/|source|` e spread `= implied − market` | `fx-conversion.en.md` | `frontend/src/lib/utils/currency/fxConversionHelper.ts:44-58` |
| Intesa Sanpaolo `patrimonio` → `ADJUSTMENT` + `cost_basis_override` per-unit | `adjustment.en.md` | `backend/app/services/brim_providers/broker_intesa.py:277-393` |
| Crédit Agricole `GIRO ALTRO DOSSIER`/`VERS.TITOLI` → `ADJUSTMENT` cashless (successione) | `adjustment.en.md`, `transfer.en.md` | `backend/app/services/brim_providers/broker_credit_agricole.py:34-40, 89` |
| Crédit Agricole `DEPOSIT + BUY` / `SELL + WITHDRAWAL` come contropartita cassa | `deposit-withdrawal.en.md` | `broker_credit_agricole.py:25-26, 392-460` (ma vedi R-05 per la parte cedole/premi) |
| Doppio click su marker evento → scroll nel Data Editor | `asset-events/index.en.md` | `frontend/src/lib/components/charts/PriceChartFull.svelte:120,711`; `AssetDataEditorSection.svelte:470` |
| Segnale "Asset Comparison" esiste come overlay | `index-benchmark.en.md` | `frontend/src/lib/charts/signals/AssetComparisonSignal.ts`, `registry.ts:27` |
| Provider css_scraper.py, justetf.py, yahoo_finance.py esistono | `etfs.en.md`, `other.en.md`, `stocks.en.md` | `ls backend/app/services/asset_source_providers/` |
| CROWDFUND → default valuation model `SCHEDULED_YIELD` | `real-estate.en.md` | `backend/app/db/models.py:163-165` |
| FEE/TAX con `asset_id=None` esclusi dall'allocazione per-lotto (gestione a livello portfolio) | `fee.en.md` | `backend/app/services/lots_analysis_service.py:1058, 1094` |

## 🔵 Fuori standard di codice / non verificabile

- **`portfolio-theory/index.en.md`, `asset-allocation.en.md`,
  `diversification.en.md`**: interamente Modern Portfolio Theory
  (Markowitz, frontiera efficiente, CAPM, correlazione, glide path,
  rebalancing bonus) — nessuna claim del tipo "LibreFolio calcola/implementa
  X". L'unico rimando a una feature reale è il link a `../../user/fx/index.md`
  per il rischio di cambio, verificato risolvere correttamente.
- **`fundamentals/returns.en.md`**: le formule di rendimento
  semplice/logaritmico/CAGR sono teoria standard; l'unica claim
  implementativa ("This is what LibreFolio's Measures tool displays")
  è verificata (`mkdocs_src/docs/user/fx/detail/measures.en.md:35` conferma
  l'uso di CAGR).
- **`fundamentals/taxation.en.md`**: le sezioni su loss carry-forward,
  aliquote per giurisdizione, wash-sale, ecc. sono teoria generale
  esplicitamente dichiarata non normativa dalla pagina stessa ("not
  jurisdiction-specific advice").
- **Contenuto descrittivo di `bonds.en.md`, `commodities.en.md`,
  `crypto.en.md`, `mutual-fund.en.md`, `stocks.en.md`**: le righe
  "Pricing"/"Why hold"/"How it works" sono convenzioni di mercato generiche
  (es. "Bonds quoted as % of face value") non legate a un campo o comportamento
  specifico di LibreFolio (nessun campo `face_value`/`par_value` nel modello
  dati — verificato assenza in `backend/app/schemas/assets.py` e
  `backend/app/db/models.py`); non trattate come reperto perché la pagina non
  afferma che LibreFolio implementi quella convenzione.
- **Non verificabile in locale**: nessuna riga individuata in queste 34
  pagine richiede accesso a servizi esterni o stato runtime non disponibile
  nel repository; tutte le claim controllabili sono state verificate contro
  il codice sorgente.

---

## Sintesi e conteggi

| Metrica | Valore |
|---|---:|
| Pagine in scope | 34/34 |
| Pagine con almeno un reperto | 7 |
| Pagine verificate pulite (incl. teoria pura) | 27 |
| Reperti totali | 7 |
| — Contraddizione | 3 (R-02, R-03, R-05) |
| — Dettaglio obsoleto | 1 (R-01) |
| — Omissione | 3 (R-04, R-06, R-07) |
| — Navigazione/link | 0 (184/184 link interni risolvono) |
| Gravità major | 3 (R-02, R-03, R-05) |
| Gravità minor | 3 (R-01, R-04, R-07) |
| Gravità info | 1 (R-06) |
| Claim verificate correttamente implementate (tabella dedicata) | 23 |
| Link Markdown interni controllati | 184 (0 rotti) |

I tre reperti `major` condividono un pattern: pagine gemelle o simmetriche
(dividend/interest, adjustment "with/without override", deposit-withdrawal
broker-nuance) dove una delle due metà dell'affermazione è stata invertita o
lasciata non aggiornata rispetto al comportamento reale — utile indizio per
chi correggerà i reperti, poiché la pagina "corretta" di riferimento esiste
già nello stesso set (`interest.en.md`, `transfer.en.md`, docstring del
plugin) e può essere usata come base per la riscrittura.
