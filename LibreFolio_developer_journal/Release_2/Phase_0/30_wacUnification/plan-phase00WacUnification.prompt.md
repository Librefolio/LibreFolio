# Piano — P: costo medio unico (issue #32)

> Workstream **P** di Release 2. Coordinator: sessione `c8328a01-f208-4ade-a352-0486d1f14de2`
> (project session `12a0954d-0fbe-42da-b687-979e798a50c6`).
> Analisi consegnata il 07/10 (sola lettura). **Implementazione autorizzata dal developer il 07/10**, inoltrata dal
> coordinator (testo e decisioni in [Decisioni prese e permessi](#decisioni-prese-e-permessi-0710-inoltrati-dal-coordinator)).
> Stato: **chiuso, FROZEN** (08/10). P0–P12 completati; commit `de252a38a`, merge dei treni 9 (`e0c40395c`) e 10
> (`e655003d3`), chiavi i18n aggiunte dopo O. Avanzamento passo per passo in §6.5, merge in §6.5bis.
>
> Percorso: `LibreFolio_developer_journal/Release_2/Phase_0/30_wacUnification/plan-phase00WacUnification.prompt.md`
> (non committato: i commit li fa il developer). L'analisi è stata scritta in plan mode nella cartella di sessione e
> copiata qui al passo 0.

| | |
|---|---|
| **Worktree** | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-miniature-telegram` |
| **Branch** | `e-alfy-p-costo-medio-unico-32` (rinominato via app da `e-alfy-miniature-telegram`, 07/10) |
| **Baseline** | HEAD `d07412899cdd7c6afb382d2f9ea193562ba5c890` = `dev_release2` locale (treni 6–8), dopo il fast-forward del developer del 07/10 12:57, verificato. L'analisi era stata fatta da `c9a602f74` (`origin/dev_release2`) leggendo la punta con `git show dev_release2:<path>`; le righe citate valgono sulla punta |
| **Lane** | `--test-port 6161 --data-dir /tmp/librefolio-r2-p`; server di review, se approvato, `6171` (porte libere, verificato 07/10). Preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6161 --data-dir /tmp/librefolio-r2-p …` |
| **Dati** | solo sintetici. Mai porta 6040/6041, mai `--force`, mai copie di prod |
| **Bootstrap** | `frontend/node_modules` **assente** (verificato) → `npm ci` solo con permesso del coordinator (serve per `component-unit`, `svelte-check`, `api sync`). `.env` assente: atteso. `graphify-out/graph.json` e `.graphify_python` assenti: atteso, wiki letto pagina per pagina |
| **Da non toccare** | N: `dashboard/+page.svelte`, `RiskLevelsPanel.svelte`, `risk-analysis.spec.ts`, `risk-lab.spec.ts`, `AssetSetRiskPanel.svelte`. O: rimozioni nei 4 cataloghi i18n (le mie chiavi arrivano dopo, solo aggiunte) |

Wiki letto: `decisions/wac-target-currency-last-acquisition`, `decisions/cost-basis-currency-object`, `features/F-097`,
`sources/r2-sp-a-cost-basis-wac`, `sources/r3-sp-d-formmodal-wac-fx-chain`, `concepts/inline-wac-computation`,
`entities/portfolio-engine`, `entities/portfolio-service`, `entities/lots-analysis-service`,
`problems/svelte-i18n-formatter-cache-ignores-locale` (punta). Nota: `problems/test-transaction-implied-constructor-mismatch`
è superata (il file di test non esiste più) → da sistemare col `wiki-file` finale.

---

## Riepilogo per il developer (IT)

### Cosa non va (verificato sul codice della punta)

1. **#32 confermato, causa esatta.** `_buy_unit_cost` (`portfolio_engine.py:1593-1643`) porta il costo nella valuta
   dell'asset A. Con P = T ≠ A legge `fx_rate_map[(EUR, EUR, d)]`, che `_preload_fx_rates` (`:2573-2668`) non carica
   mai (raccoglie solo `ccy != target`) → `None`. I chiamanti (`:793` pre-frame, `:958` frame) aggiungono allora le
   quote **al costo medio corrente**: pool vuoto → costo 0, nessuna traccia. Con la Dashboard in USD (A = T) il ramo
   `asset_ccy == target` usa `(EUR, USD, d)`, che c'è: per questo in USD è giusto.
2. **Gemelli dello stesso ramo, stessa causa:**
   - ADJUSTMENT-in / TRANSFER-in con `cost_basis_override` in T su un asset in A ≠ T (posizioni d'apertura con costo
     in euro su titoli in dollari): costo 0 **e** il capitale in natura non entra nel capitale versato, perché
     `_capital_flow_for_adjustment_in` (`:812`, `:981`) riceve `None` → il **P&L totale si gonfia** del valore della
     posizione.
   - CBO in una terza valuta: `(cbo_ccy, T, d)` è caricato solo se quella valuta compare altrove quel giorno → stesso
     ripiego silenzioso.
3. **Correzione al quadro del kickoff:** `:997` e `:1329` non sono protette: senza tasso usano l'importo nella valuta
   dell'asset **come se fosse in T** (`rate if rate else cb_local`, `rate if rate else ocb_local`): valore sbagliato,
   non zero, nessun segnale. `:1564` mette la coppia in `missing_fx`, ma `DailyPortfolioState.missing_fx_pairs` non
   ha lettori: non arriva né all'API né al banner. Lo ammette la docstring di `AcquisitionFundingSeries`
   (`schemas/portfolio.py:694-705`): il motore non ha un canale per le conversioni mancanti. Idem le valutazioni
   con tasso mancante: `market_value=None` ma `nav_complete` resta `True` (conta solo `MISSING`).
4. **Le implementazioni del costo sono quattro, non tre:**
   1. motore (pool in A, riconvertita al cambio del giorno);
   2. `compute_wac_iterative` + `compute_wac_from_txlist` (valuta dell'ultimo acquisto, cambio della data);
   3. lotti, `_build_wac_row` (`lots_analysis_service.py:870`, `:877`): senza tasso usa **il costo non convertito**;
   4. `TransactionService.get_cost_basis` (`transaction_service.py:480`) → `GET /brokers/{id}/summary`: somma gli
      importi dei BUY **in valute miste**, ignora vendite e trasferimenti. Il frontend non legge quei campi; i test sì.
5. **Altri punti silenziosi nel service:** il realizzato salta la vendita se manca il tasso (`:876`, `:1899`), usa
   il ricavo non convertito (`:891`, `:1912`), scarta le coppie mancanti (`_` a `:882`, `:1904`, `:1968`, `:1991`).
6. **Divergenza di semantica:** acquisto senza costo noto (TRANSFER/ADJUSTMENT-in senza CBO, oggi bloccato dalla
   validazione `COST_BASIS_REQUIRED`): motore = al costo medio corrente; `wac_utils` = costo zero. I rami `add_at_wac`
   e `is_pending` di `wac_utils` **non sono raggiungibili in produzione** (nessun chiamante passa `cost_basis_mode`
   o `is_pending`: `portfolio_service.py:172-218`).
7. **Pagina asset:** oggi non mostra né costo né PMC, e `POST /portfolio/wac` non ha chiamanti nel frontend (solo API
   esterna e test). La regola «valuta dell'ultimo acquisto» serve ad auto-CBO in validate/commit, a `POST
   /portfolio/wac` e alla PAC (che però passa T come override).
8. **Già allineati al nuovo modello:** la PAC (WAC in T con ogni acquisto convertito alla sua data) e la linea del
   costo medio dei lotti (in T alla data). Anche i lotti FIFO (`original_cost` alla data d'apertura): oggi il costo
   aperto del motore li **contraddice** per le posizioni in valuta, dopo no.

### Proposta in breve

Un modulo nuovo, `backend/app/services/average_cost.py`, con **una** funzione pubblica, `compute_average_costs(...)`:
riceve i movimenti in ordine e le valute (T del report, A dell'asset), converte da sé con `fx.convert_bulk` (una sola
chiamata a lotti per tutte le posizioni della richiesta, stessa valuta = 1 senza I/O) e restituisce per posizione
Q, C_T, C_A, costi unitari, la timeline per movimento e le conversioni mancanti con le date.
- Il **motore** la chiama una volta in `calculate()` e il builder consuma i risultati: spariscono `_buy_unit_cost`,
  i tassi incrociati e la riconversione giornaliera del costo.
- `compute_wac_iterative` resta come **facciata** (stessa firma, stesse query, stessa cache, stesso
  `WACPreviewResultItem`) → anteprima/auto-CBO, `POST /portfolio/wac` e PAC invariati.
- **Lotti** e **broker summary** passano alla stessa funzione.
- **Realizzato** e **costo d'inizio/fine periodo** leggono la timeline del motore: zero query WAC in più.
- Ogni conversione mancante risale con coppia e date fino a `summary.missing_fx_pairs` e al banner giallo.

### Decisioni da prendere (in grassetto la mia raccomandazione)

- **D1, dove vive la funzione:** **`backend/app/services/average_cost.py`** (fa I/O tramite il service FX). Il nucleo
  aritmetico è privato nello stesso modulo. `wac_utils.py` si elimina: `determine_target_currency` passa nel modulo
  nuovo (la usa solo la facciata), `WACInputTX`/`WACCalcResult`/`compute_wac_from_txlist` spariscono, insieme ai rami
  morti `add_at_wac`/`is_pending`.
- **D2, costo nella valuta dell'asset quando P ∉ {A, T}:** **via T, C_A = C_T / r(A→T, d)**: nessuna coppia nuova
  (servono già P/T e A/T), e l'effetto cambio è zero esatto il giorno dell'acquisto. Alternativa: conversione diretta
  P→A (serve la coppia P/A configurata; fonti diverse danno un piccolo effetto cambio spurio al giorno 0).
- **D3, tasso mancante per un acquisto (ramo T):** **quantità aggiunta, costo non aggiunto; posizione «costo
  incompleto»; `wac_per_unit` e `gain_loss` della riga a `None` (il contratto dice già «None if FX rate missing»);
  il costo aperto aggregato somma la parte nota; coppia e date al banner.** La facciata resta fail-safe come oggi
  (`wac=None` + `wac_missing_pairs`): un WAC parziale non si scrive mai in un CBO.
- **D4, acquisto senza costo noto (CBO assente):** **costo zero + diagnostica `unknown_cost`** (= semantica attuale di
  facciata e PAC: per loro non cambia nulla; cambia solo il motore, che oggi stima «al costo medio»). Risalita:
  **(a) un issue `MISSING_COST_BASIS` (warning, una chiave i18n in aggiunta), tagliabile** perché la validazione oggi
  impedisce questi dati; (b) solo diagnostica nel risultato e log.
- **D5, aritmetica:** **somme esatte** (C_T += importo convertito, riduzione proporzionale con conservazione esatta,
  WAC = C/Q): la #32 dà `Decimal("400")` esatto. Prezzo: rispetto alla formula iterativa di `wac_utils` i WAC con
  quozienti periodici possono differire **all'ultima cifra decimale** (~1e-26 relativo). Per la PAC è un valore
  diverso in `wac_contexts[].unit_cost`, schema invariato. Il test-author misura la differenza sulle fixture PAC.
  Alternativa: formula iterativa anche nel nucleo (bit-identico, ma C_T = WAC·Q = 399,999…9).
- **D6, costo dell'asset in transito:** **CBO × quantità convertito alla data d'arrivo (fisso)**, come lo convertirà la
  pool di destinazione. Oggi è riconvertito ogni giorno, e accanto al costo storico creerebbe un modello misto in
  `book_asset_like`. Alternativa: lasciarlo com'è (fuori perimetro dichiarato).
- **D7, canale «FX mancanti» del motore:** **tutte le conversioni del motore** (costo, cassa, flussi, ricavi, valutazione):
  chiude la limitazione scritta in `AcquisitionFundingSeries`. Le coppie dei movimenti valgono a ogni data, quelle
  della valutazione solo nel periodo. Effetto visibile: il banner può comparire dove oggi si perdono importi in
  silenzio. Alternativa: solo le conversioni del costo.
- **D8, fonte del realizzato:** **eventi di vendita esposti dal motore** (data, posizione, ricavo in T, costo storico in
  T): spariscono le chiamate `compute_wac_iterative` per ogni vendita. Alternativa: il service richiama la funzione
  per posizione.
- **D9, quarta implementazione (`GET /brokers/{id}/summary`):** **migrarla** (T = valuta dell'asset, raggruppando per
  valuta; elimina `get_cost_basis`). Alternativa: rinviarla.
- **D10, yield on cost:** **denominatore = WAC storico in T** (lo stesso della riga). Oggi è WAC_A × cambio di fine
  periodo; con l'input `(wac_report, T)` `yield_on_cost.py` non cambia codice (conversione identica), cambiano numeri e
  doc, e sparisce la riga di provenienza FX del WAC.
- **D11, scomposizione del non realizzato:** **in 1.2, come ultimi passi separabili (P8–P9)**: il «Δ non realizzato»
  da ora include il cambio, e senza tooltip l'utente lo vede cambiare senza spiegazione. Se si taglia, il CHANGELOG
  deve spiegarlo lo stesso.
- **D12, AI Export:** **(a) aggiornare `valuation_semantics` di `portfolio.provenance` e `broker.provenance`** («costo
  storico in T, ogni acquisto convertito alla sua data») **e alzarne la `version` d'implementazione**; (b) alzare
  anche i componenti che portano costo e P&L (elenco in §3.4). Passa da te.

### Permessi da chiedere al coordinator

- `backend/test_scripts/test_services/test_portfolio_allocation_source.py` (D): portare l'oracolo
  `test_canonical_runtime_wac_buy_sell_and_fresh_pool_sequence` (usa `compute_wac_from_txlist`) sulla funzione nuova.
  Nessuna modifica a `portfolio_allocation_source.py`.
- `backend/test_scripts/test_external/test_brim_providers.py` (area BRIM): una costruzione di `DailyStateBuilder`
  (`:1563`) da aggiornare.
- `scripts/test_runner/_backend_services.py` (condiviso): riallineare `financial-utils` al file di test nuovo.
- `backend/app/schemas/portfolio.py` (condiviso): campi nuovi, tutti opzionali.
- `frontend/src/lib/api/zodios-client.ts` via `api sync` (generato, condiviso).
- `KpiSection.svelte` / `KpiSection.test.ts` (area Dashboard; N lavora su `+page.svelte`, che non tocco).
- i18n: 3 chiavi (+1 se D4a) × 4 cataloghi, **dopo O**, solo aggiunte.
- componenti AI Export (se D12).
- `CHANGELOG.md` (lo scrivi tu o mi assegni).
- doc utente Dashboard (`kpi-cards`, `positions`) e teoria; traduzioni IT/FR/ES di quelle pagine (agente o Aphra).
- `npm ci`.

---

## Decisioni prese e permessi (07/10, inoltrati dal coordinator)

Autorizzazione del developer, testuale:

> «approvo tutto, ma a livello di struttura potrebbe avere senso creare un nuovo service layer per il calcolo
> matematico, e come prima funzione mettiamo questa, poi in futuro fattorizziamo le altre o le creiamo direttamente
> qui, ma è una questione di architettura del backend, sul piano sono d'accordo»

Valgono tutte le raccomandazioni, con queste precisazioni:

- **D1 → layer nuovo `backend/app/services/financial_math/`** (nome scelto dal coordinator, nessuna obiezione).
  - Primo modulo `financial_math/average_cost.py` con `compute_average_costs`.
  - La docstring di `financial_math/__init__.py` dice la regola del layer:
    - è la casa dei calcoli finanziari, che possono usare altri service (come l'FX);
    - i calcoli nuovi nascono qui;
    - quelli esistenti (`utils/financial/roi_utils.py`, `valuation_utils.py`, …) migreranno in futuro, **non ora**.
  - `wac_utils.py` si elimina.
  - Il layer va documentato nella doc sviluppatore (`docs-writer`) e come decisione nel wiki (`wiki-file` finale).
  - Ovunque questo piano dica `backend/app/services/average_cost.py` vale `backend/app/services/financial_math/average_cost.py`.
- **D4 = (a)**: issue `MISSING_COST_BASIS` al banner. Il developer l'aveva chiesto: «se la funzione non ritorna un
  costo, l'informazione risale e popola il banner».
- **D5**: misurare le differenze nella PAC e riportarle al coordinator prima del merge.
- **D12 = solo (a)**:
  - aggiornare `valuation_semantics` di `portfolio.provenance` e `broker.provenance` e alzare la versione di quei
    due componenti;
  - verificare che il renderer del frontend conosca le versioni nuove, altrimenti il componente ripiega su YAML;
  - nessun bump per gli altri componenti.

  Prima di toccarli leggere: skill `ai-export-probe-tuning`, `ai_export_composition.md`,
  `ai-development.instructions.md`, `frontend-ai-export.instructions.md`.
- **D2, D3, D6–D10, D11** come raccomandate. D11 va nella 1.2, con P8–P9 tagliabili.

**Permessi concessi:**
- `test_portfolio_allocation_source.py`, per l'oracolo della PAC.
- `test_brim_providers.py`: **solo** il blocco del `DailyStateBuilder` (~`:1563`). L lavora su DEGIRO in
  `test_brim_degiro.py`: niente riformattazioni del file intero.
- Il runner `scripts/test_runner/_backend_services.py`.
- `schemas/portfolio.py` + `api sync`: P è l'unico proprietario del client generato fino a nuovo avviso.
- `KpiSection.svelte` e `KpiSection.test.ts`.
- i18n: 3 + 1 chiavi, solo aggiunte, via `dev.py i18n`, **dopo** che O è integrato (avviso del coordinator).
- Componenti AI Export secondo D12(a).
- Doc: inglese, con `docs-writer`, le pagine del §6.1. **Niente traduzioni IT/FR/ES adesso**: si fanno
  nell'allineamento prima della 1.2. È debito di traduzione, quindi **niente stamp**.
- `npm ci` dal lock quando serve; mai `install`/`update`/`audit fix`.
- **CHANGELOG lo scrive il coordinator**: all'handoff gli si mandano le righe aggiornate.

**Regole di lavoro:**
- La coverage dello sprint gira nella corsia del coordinator: i rossi nella mia area si ignorano, non si inseguono.
- Test con `test-author`, rossi prima.
- Aggiornare il piano a ogni passo.
- Prima di proporre un commit: FROZEN + handoff al coordinator.

## 2bis. Contratto fissato prima di P1 (raffina §2)

Dettagli decisi rileggendo il codice prima di dare il lavoro al test-author. Dove differisce da §2, vale questo.

- **Movimento**: niente `Currency` Pydantic nel ciclo caldo; `CostMovement(movement_id, transaction_type, date,
  kind, quantity, cost_amount: Decimal | None = None, cost_currency: str | None = None)`.
  - `cost_amount=None` = costo sconosciuto;
  - `cost_amount=0` = costo zero, che non chiede conversioni;
  - `cost_currency` è obbligatorio quando `cost_amount` non è None.
- **Effetti** (`CostEffect`, StrEnum): `add`, `add_zero_cost`, `add_unknown_cost`, `add_missing_fx`, `reduce`,
  `split_rescale`.
- **Ordine**: `(date, 0 se quantity > 0 altrimenti 1, movement_id oppure 999_999_999)`, sort stabile. È lo stesso
  ordine del motore e di `wac_utils` di oggi; le righe di split seguono il segno della quantità.
- **Ramo asset (D2)**:
  - P = A → `c_A = importo`;
  - A = T → `c_A = c_T`;
  - altrimenti `c_A = c_T × r(T→A, d)`, con il tasso unitario chiesto nello **stesso** `convert_bulk`. È il percorso
    «via T» senza dividere per un tasso arrotondato.

  La coppia mancante del ramo asset si scrive `"A/T"`, come la valutazione.
- **Completezza per passo**:
  - `report_complete` / `asset_complete` del pool **dopo** il passo;
  - diventano False con un tasso mancante o con un costo sconosciuto;
  - tornano True quando il pool si svuota (Q = 0 azzera anche i costi).

  `AverageCost.missing` conserva **tutta** la storia: la facciata resta fail-safe su qualunque mancante del ramo T,
  come oggi.
- **Riduzioni**:
  - `q_out = min(|q|, Q)`; `removed = C × q_out / Q`, con `removed = C` esatto quando `q_out = Q`;
  - oltre la quantità: clamp a 0 + `oversold_movement_ids`.

  Il costo realizzato di una vendita oltre il pool è quello del pool, non più `WAC × |q|`. È un caso limite di dati
  incoerenti, annotato.
- **Costo aperto della posizione**:
  - in generale `C_T × q / Q`, dove `q` è la quantità cumulativa del motore;
  - con `q = Q` è **`C_T` esatto**: per la #32 dà 400, non 399,99…9.
- **Facciata**: mappa `add_unknown_cost` → `add_zero_cost` (vocabolario `effect` invariato per frontend e PAC);
  `add_missing_fx` non arriva mai all'uscita, perché scatta il fail-safe.
- **Il nucleo puro** è privato nello stesso modulo (`_conversion_requests`, `_fold_average_costs`). Lo usano solo
  l'helper di test del motore e i chiamanti del modulo. **L'unica funzione pubblica che converte** è
  `compute_average_costs`.

## 1. Stato verificato sulla punta

### 1.1 Il costo nel motore oggi

| Dove | Cosa fa | Problema |
|---|---|---|
| `DailyStateBuilder.__init__` `:574` | riceve `fx_rate_map` già caricata | il costo dipende dalle chiavi caricate da un altro metodo |
| `_buy_unit_cost` `:1593-1643` | BUY → `\|amount\|` in P; TRANSFER/ADJ con CBO → CBO × q in valuta CBO; senza CBO → `None`; converte P→A: se A = T usa `r(P→T)`, altrimenti `r(P→T)/r(A→T)` | nessuna identità P = T; `None` sia per «senza costo» sia per «tasso mancante» |
| pre-frame `:784-808`, frame `:955-985` | `None` → aggiunge al costo medio corrente | #32: pool vuota → 0, nessuna traccia |
| `_capital_flow_for_adjustment_in` `:1583` | capitale in natura = costo in A convertito a T alla data | con `None` il capitale non entra: P&L totale gonfiato |
| riduzione `:986-1027` | costo uscito = WAC_A × q × `r(A→T, oggi)`; senza tasso usa l'importo in A (`:998`) | realizzato/K/R al cambio della vendita; ripiego silenzioso |
| `_compute_open_cost_basis_inline` `:1532` | ogni giorno C_A × `r(A→T, t)` | il costo «galleggia» col cambio; `missing_fx` non letto da nessuno |
| `_build_position_state` `:1308` | `cost_basis = WAC_A × q × r`, senza tasso importo in A (`:1330`) | ripiego silenzioso |
| `_preload_fx_rates` `:2573` | carica `(ccy, T, d)` per importi, flussi, prezzi/asset ogni giorno, A alle date BUY (`:2629`) | mai `(T, T, d)`; mai `(cbo_ccy, T, d)` alle date dei movimenti |
| `EngineEndState` `:1720` | `wac_pool_qty`/`wac_pool_cost` | ripresa in avanti mai implementata (commento `:2440`) |

### 1.2 Gli altri costi medi

- **`compute_wac_iterative`** (`portfolio_service.py:114-367`): carica le righe `(broker, asset, date ≤ as_of, qty ≠ 0)`,
  rileva gli split, T = override o ultimo acquisto (`determine_target_currency`), una `convert_bulk` per gli acquisti
  con P ≠ T alla loro data, fail-safe (`wac=None` + coppie e date), cache `_wac_cache` con fingerprint delle righe,
  output `WACPreviewResultItem` (qualifying con `fx_info`, `original_*`, `fx_rate_used`, `effect`, `running_wac`).
  Chiamanti: `portfolio_api.py:125` (`/portfolio/wac`), `transaction_service.py:1012` (auto-CBO), PAC
  `portfolio_allocation_source.py:1024` (override T, `use_cache=False`), service `:868`, `:1891` (realizzato),
  `:1950`, `:1977` (WAC d'inizio/fine periodo).
- **`compute_wac_from_txlist`** (`wac_utils.py:65`): stato `(wac, qty)` iterativo; additions prima delle riduzioni nello
  stesso giorno; clamp a 0 sulle vendite oltre la quantità; split = rescale.
- **Lotti** (`lots_analysis_service.py:825-887`, `:1018-1039`): righe convertite in T con `_FxRateResolver`, ripiego
  sul costo non convertito; serie ricalcolata da capo per ogni data di storia (O(D×N)).
- **Broker summary** (`broker_service.py:359-451` + `transaction_service.py:480`): somma dei BUY.
- **Yield on cost** (`yield_on_cost.py:443-520`): converte WAC_A → T a fine periodo; quel valore diventa anche
  `PortfolioHolding.wac_per_unit` (`portfolio_service.py:944`).

### 1.3 Mappa dei consumatori

| Consumatore | Oggi | Fonte |
|---|---|---|
| KPI «Purchase Cost», storico «assets at cost», `book_value` | engine `open_cost_basis` (A × cambio del giorno) | `get_summary` `:1286`, `get_history` |
| Δ non realizzato del periodo | `MV − open_cost_basis` agli estremi | `_compute_period_summary_metrics` `:603` |
| Realizzato del periodo (KPI, contributi) | WAC_L × `r(L→T, data vendita)` | `:861-895`, `:1882-1917` |
| Costo d'inizio/fine periodo (tabella Performance) | WAC_L × `r(L→T, data)` | `:1949-2002` |
| Righe posizioni: `wac_per_unit`, `gain_loss`, `annualized_return` | YOC (WAC_A × r fine) e `ps.cost_basis` | `:903-1050` |
| Pool K/R (tooltip liquidità), capitale versato | costo uscito al cambio della vendita; capitale in natura | builder |
| Anteprima/auto-CBO, `/portfolio/wac`, PAC | `compute_wac_iterative` | facciata |
| Linea WAC dei lotti | `_build_wac_row` + `compute_wac_from_txlist` | lotti |
| `/brokers/{id}/summary` holdings | somma BUY | broker service |
| AI Export | holdings, summary, contributi, lotti FIFO | componenti portfolio/broker/asset |
| Current distribution PAC | solo `market_value` delle posizioni | invariato |

---

## 2. La funzione unica

### 2.1 Modulo e firma (identificatori in inglese)

```python
# backend/app/services/average_cost.py

class CostMovementKind(StrEnum):
    ACQUISITION = "acquisition"   # qty > 0, cost = total actually paid (>= 0) or None (unknown)
    REDUCTION = "reduction"       # qty < 0, exits at the current average on both legs
    SPLIT = "split"               # signed qty delta, total cost unchanged


@dataclass(frozen=True, slots=True)
class CostMovement:
    movement_id: int | None       # Transaction.id: same-day order key and step lookup key
    transaction_type: str         # BUY | SELL | TRANSFER | ADJUSTMENT (rows, diagnostics)
    date: date
    kind: CostMovementKind
    quantity: Decimal             # signed
    cost: Currency | None = None  # ACQUISITION only


@dataclass(frozen=True, slots=True)
class CostPosition:
    key: Hashable                 # caller key, e.g. (asset_id, broker_id)
    asset_currency: str           # A
    movements: tuple[CostMovement, ...]


def cost_movement_from_transaction(tx, *, asset_currency: str, split_linked: bool,
                                   share: Decimal = Decimal("1")) -> CostMovement | None: ...


async def compute_average_costs(
    session: AsyncSession,
    positions: Sequence[CostPosition],
    *,
    report_currency: str,         # T
    asset_leg: bool = True,       # also accumulate C_A
) -> dict[Hashable, AverageCost]: ...
```

Una sola funzione pubblica, a lotti: chi ha una posizione passa una lista di uno. L'adattatore
`cost_movement_from_transaction` è **l'unica regola** «transazione → movimento», usata da motore, facciata, lotti e
broker summary:
- BUY con importo → acquisto, costo `|amount|` in `tx.currency or A`;
- BUY con importo 0/None → acquisto a costo zero;
- TRANSFER/ADJUSTMENT con q > 0 e CBO → acquisto, costo `CBO × q` in `cbo_ccy or A`;
- TRANSFER/ADJUSTMENT con q > 0 senza CBO → acquisto con `cost=None` (D4);
- q < 0 → riduzione;
- riga legata a uno SPLIT → split.

`share` scala quantità e costo (proprietà del broker), come oggi `ctxn.share`.

### 2.2 Algoritmo (nucleo puro, privato)

- **Ordine:** `(date, acquisti prima delle riduzioni, movement_id)`, identico a motore e `wac_utils` di oggi.
- **Acquisto convertito:** `Q += q`, `C_T += c_T`, `C_A += c_A` (somme esatte degli importi convertiti, non
  `unitario × q`).
- **Costo zero:** `Q += q` (`add_zero_cost`). **Costo sconosciuto:** idem + `unknown_cost` (`add_unknown_cost`).
- **Tasso mancante sul ramo T:** `Q += q`, costo non aggiunto, `missing` + incompleto (`add_missing_fx`). Ramo A
  mancante: `C_A` diventa sconosciuto da quel passo (`asset_complete=False`), il ramo T resta valido.
- **Riduzione:** `q_out = min(|q|, Q)`; `removed_T = C_T · q_out / Q`; `C_T −= removed_T` (uscita totale → `C_T = 0`
  esatto); idem per A. **Conservazione esatta:** Σ acquisti_T = C_T residuo + Σ removed_T. Oltre la quantità: clamp
  a 0 (come oggi) + diagnostica `oversold`.
- **Split:** `Q += q` se il risultato è > 0, altrimenti tutto a zero; costo invariato.

### 2.3 Conversioni (service layer FX)

Raccoglie le richieste non identiche e fa **una** `convert_bulk(session, items, raise_on_error=False)`:
- ramo T: `(costo in P → T, d)` se P ≠ T; se P = T il costo entra tale e quale;
- ramo A (D2): se P = A, `C_A = costo`; altrimenti `(1 A → T, d)` → `r_A` e `C_A = C_T / r_A`.

Nessuna richiesta → nessuna chiamata (i test PAC lo verificano già con una sonda che esplode,
`test_portfolio_allocation_source.py`). Il backward-fill illimitato è quello del service FX: «mancante» vuol dire
nessun tasso **su o prima** della data, quindi coppia non configurata o data anteriore alla storia. Ogni conversione
riuscita porta la provenienza: `rate = convertito/originale`, `rate_date`, giorni indietro (servono a facciata e PAC).

### 2.4 Uscite

```python
@dataclass(frozen=True, slots=True)
class CostStep:
    movement: CostMovement
    effect: str                     # add | add_zero_cost | add_unknown_cost | add_missing_fx | reduce | split_rescale
    quantity: Decimal               # pool quantity after the movement
    cost_report: Decimal            # C_T after
    cost_asset: Decimal | None      # C_A after (None: leg off or incomplete)
    cost_report_change: Decimal     # + added / − removed, in T (reduction: realized cost basis)
    cost_asset_change: Decimal | None
    conversion: CostConversion | None   # T-leg provenance: original Currency, converted, rate, rate_date, days_back


@dataclass(frozen=True, slots=True)
class AverageCost:
    key: Hashable
    report_currency: str
    asset_currency: str
    quantity: Decimal
    cost_report: Decimal            # historical cost in T (known part)
    cost_asset: Decimal | None      # historical cost in A
    steps: tuple[CostStep, ...]
    missing: tuple[MissingConversion, ...]   # pair "FROM/TO", sorted unique dates, leg "report" | "asset"
    unknown_cost_movement_ids: tuple[int | None, ...]
    oversold_movement_ids: tuple[int | None, ...]
    # properties: report_complete, asset_complete, unit_cost_report (C_T/Q), unit_cost_asset
    def state_at(self, day: date) -> CostStep | None: ...   # last step dated <= day (bisect)
```

`MissingConversion.pair` usa il formato «FROM/TO» di `WACMissingPairInfo` di oggi, quindi passa senza traduzioni a
`summary.missing_fx_pairs`, a `build_data_quality_report` e a `WAC_FX_UNAVAILABLE`.

### 2.5 Come la usano i chiamanti

- **Motore** — `PortfolioCalculationEngine.calculate()`, dopo il preload FX:
  - costruisce le posizioni da `classification.classified` (stesso filtro del builder: `quantity ≠ 0` e `asset_id`) e
    chiama `compute_average_costs(..., report_currency=T, asset_leg=True)` **una volta**;
  - passa il risultato a `DailyStateBuilder(average_costs=...)`, parametro obbligatorio: nessun default che dia
    zeri silenziosi;
  - il builder legge il passo per `tx.id`: pool ← valori «after»; vendita → `−cost_report_change` per K/R e
    realizzato; capitale in natura ADJ-in/out ← `±cost_report_change`;
  - costo aperto del giorno = Σ C_T delle posizioni con q > 0, senza FX;
  - `DailyPositionState.wac` diventa il costo unitario **in T** (`wac_currency = T`), più `wac_asset` (A, opzionale)
    e `cost_complete`;
  - spariscono `_buy_unit_cost`, `_compute_open_cost_basis_inline`, la riga `:2629` del preload e i ripieghi `:998`
    e `:1330`;
  - `EngineEndState` porta `(Q, C_T, C_A)`;
  - il risultato espone `average_costs`, `realized_sales` (D8) e `missing_fx: dict[pair, set[date]]` (D7).
- **Facciata `compute_wac_iterative`** — firma, query, ordine delle query, cache e output invariati:
  - T = override, altrimenti `determine_target_currency` sulle stesse regole di oggi (compresa la stranezza: una
    riga di split con q > 0 conta come «ultimo acquisto»), con `asset_leg=False`;
  - mappa i passi su `WACQualifyingTX`: unitario = c_T/q; riduzione = WAC prima; split = WAC dopo;
    `running_wac = C_T/Q` (0 a pool vuota); `fx_info`/`original_*`/`fx_rate_used` dalla provenienza;
  - fail-safe: ramo T incompleto → `wac=None`, `qualifying=[]`, coppie e date;
  - nessuna riga → `wac = Currency(A, 0)`, come oggi.
- **Lotti** — `get_lots_analysis` (async) chiama la funzione una volta: una posizione per broker più `"__all__"`
  (tutti i broker insieme), con T del report e `asset_leg=False`. La serie si campiona con `state_at(data)`:
  O(D log N) invece di O(D×N). Le conversioni mancanti vanno in `data_quality.missing_fx_pairs` e in un issue
  `MISSING_FX_RATES` (da verificare che `LotDataQualityBanner` lo mostri; se no, piccola aggiunta).
- **Service:**
  - `get_summary`: realizzato = Σ `realized_sales` nel periodo; ricavo nullo = −costo, come oggi nel service;
    ricavo non convertibile → coppia al banner, mai il ricavo non convertito;
  - `get_summary`: YOC con `(wac_report, T)` (D10); unisce `engine_result.missing_fx` ad `all_missing_pairs`;
  - `get_positions_contribution`: realizzato e `per_cost_sold` dagli stessi eventi; costo d'inizio/fine =
    `state_at(date_from / effective_end)` × quantità. Spariscono 4 chiamate `compute_wac_iterative` e i `_` sulle
    coppie mancanti.
- **Broker summary (D9):** una chiamata per valuta d'asset con T = A; `total_cost = C_T`, medio `C_T/Q`, non
  realizzato in A.

### 2.6 Prestazioni

| Percorso | Oggi | Dopo |
|---|---|---|
| Motore | 1 `convert_bulk` (preload) | 2 `convert_bulk` (preload + costi, a lotti per tutte le posizioni); ciclo giornaliero senza FX sul costo |
| `get_summary` | per ogni vendita nel periodo: 1–2 query WAC + 1 `convert_bulk` WAC + 2 `_convert_to_base` | 0 (eventi del motore) |
| `get_positions_contribution` | (vendite + 2 × posizioni) × (query WAC + conversioni) | 0 per il costo (restano prezzi e cambi di valutazione) |
| Facciata (anteprima, `/wac`, PAC) | 1–2 query + ≤1 `convert_bulk` | identico |
| Linea WAC lotti | ricalcolo O(D×N) | una timeline + bisect |

Cache: la fingerprint FX del motore (`compute_portfolio_fx_cache_identity`) copre già le coppie P/T e A/T; blob e L2
sono in memoria, si svuotano al riavvio.

---

## 3. Migrazione per consumatore: cosa cambia nei numeri e perché

### 3.1 Quando cambia

Legenda: P = valuta pagata, A = valuta dell'asset, T = valuta del report, L = valuta dell'ultimo acquisto.

| Consumatore | P = A = T | P = A ≠ T | P = T ≠ A (#32) | P ≠ A = T | P ∉ {A, T} |
|---|---|---|---|---|---|
| Costo aperto, «assets at cost», costo/WAC/`gain_loss` di riga | = | **storico** (prima: C_A × cambio di oggi) | **corretto** (prima: 0) | = | storico (prima: incrociato, poi cambio di oggi) |
| Δ non realizzato del periodo | = | **include l'effetto cambio** (prima: in «Altro») | corretto | = | include l'effetto cambio |
| Capitale versato (ADJ in natura) | = | ADJ-out toglie C_T storico | ADJ-in **corretto** (prima: mancava) | = | — |
| K/R (tooltip liquidità) | = | vendita: K += C_T storico | corretto | = | — |
| Realizzato, costo d'inizio/fine periodo | = | cambia se L ≠ T: costo storico in T invece di WAC_L × cambio alla data | | | |
| YOC (D10) | = | denominatore storico | corretto | = | storico |
| Anteprima/auto-CBO, `/portfolio/wac`, PAC | = | = | = | = | = |
| Linea WAC lotti | = | = (già storico) | = | = | = |
| `/brokers/{id}/summary` (D9) | cambia se ci sono vendite/trasferimenti (prima: somma dei BUY) | | | | |

In tutti i casi «=», l'unica differenza possibile è l'ultima cifra decimale con quozienti periodici (D5). Due casi
limite: CBO = 0 in valuta estera non chiede più un tasso (prima un tasso mancante dava `wac=None`); il ramo
«senza costo» del motore passa da «al costo medio» a «zero + diagnostica» (D4).

### 3.2 La #32 in numeri

HYPE in USD, 3 BUY pagati 100 €, 150 €, 150 € alle date d1–d3, coppia USD/EUR sincronizzata.

| | Oggi | Dopo |
|---|---|---|
| Dashboard EUR, Purchase Cost HYPE | 0 | **400,00 € esatti** (`Decimal("400")`, somma senza conversione) |
| Dashboard EUR, non realizzato | MV (tutto il valore) | MV − 400 |
| Dashboard EUR, «Altro/residuo» del periodo | −400 (assorbe l'errore) | ≈ 0 |
| Dashboard EUR, WAC/unità | 0 | 400 / Q |
| Costo in USD (per la scomposizione) | — | C_A = 100/r1 + 150/r2 + 150/r3 |
| Dashboard USD | Σ EUR_i × r(EUR→USD, d_i) | **invariato** |

### 3.3 Un caso P = A ≠ T

10 quote a 100 USD, pagate in USD, con USD→EUR 0,909 all'acquisto e 0,833 oggi; prezzo fermo.

- **Oggi:** costo = 833 € (segue il cambio), non realizzato 0, i −76 € finiscono in «Altro».
- **Dopo:** costo = 909 € (quanto pagato in euro alla data), non realizzato −76 € = tutto effetto cambio (riga 💱 del
  tooltip), «Altro» ≈ 0.

### 3.4 PAC e AI Export

- **PAC (D):** passa da `compute_wac_iterative` con override T: contratto, campi, ordine delle righe qualifying e
  provenienza restano gli stessi. Differenze possibili:
  - l'ultima cifra di `unit_cost` (D5);
  - CBO = 0 in valuta estera: oggi la riga porta `fx_info` senza `fx_rate_used` e la PAC la segna
    `allocation.wac_fx_missing`; dopo la riga non ha conversione e viene saltata (falso positivo in meno).

  Non tocco `portfolio_allocation_source.py`; il test con l'oracolo `compute_wac_from_txlist` va portato.
- **AI Export:** cambiano i numeri (non gli schemi) per le posizioni in valuta in:
  - `portfolio.summary`, `.positions`, `.performance`, `.reconciliation` (il residuo si riduce);
  - `broker.summary`, `.positions`, `.performance`, `.reconciliation`;
  - `asset.positions_by_broker`, `.cost_value_pl`, `.performance`.

  Il testo `valuation_semantics` (`portfolio_financial.py:299`, `broker_financial.py:269`) oggi dice solo «Weighted
  Average Cost»: va precisato («in target currency, each acquisition converted at its own date: historical cost»).
  Dopo, costo medio e `fifo_lots.original_cost` usano la stessa base. Versioni: D12. Prima di toccarli: skill
  `ai-export-probe-tuning` e docs `ai_export_composition.md`.

---

## 4. Scomposizione del non realizzato (D11)

### 4.1 Formule

Per una posizione in A, con r(t) = cambio A→T, MV_T(t) = valore di mercato in T:

- **effetto asset**: `E_a(t) = MV_T(t) − C_A · r(t)` (= `(Q · prezzo_A(t) − C_A) · r(t)`)
- **effetto cambio**: `E_c(t) = C_A · r(t) − C_T`
- `E_a + E_c = MV_T − C_T = U(t)`, esatto. Per A = T: r = 1 e C_A = C_T → `E_c = 0` → **nessuna riga T→T**.

Il tooltip va sulla prima voce della prima card, «Unrealized change», che mostra un **delta di periodo**: le righe sono
`E(t1) − E(t0)` sugli stessi due stati usati da `_compute_period_summary_metrics` (stato ≤ `date_from`, stato a
`date_to`), quindi **Σ righe = `period_unrealized_gain_loss_delta`** per costruzione. Se per una valuta manca r o C_A
(ramo A incompleto), quella valuta dà una sola riga «non scomponibile» con il suo delta: la somma resta esatta.

### 4.2 Forma dei dati

- **Motore:** ogni `DailyPortfolioState` porta `unrealized_by_currency: dict[A, (asset, fx) | unsplit]`, accumulato
  nello stesso giro posizione per posizione che somma valore e costo (la valutazione con tasso mancante entra come
  oggi nell'aggregato). Le giornate ferme copiano il dizionario come fanno con `by_type`.
- **Schema:** `PortfolioSummary.period_unrealized_breakdown: list[UnrealizedBreakdownRow] = []` con
  `kind: asset | fx | unsplit`, `asset_currency: str`, `period_delta: Currency`. Opzionale con default, così la
  fixture reale della gallery (`frontend/e2e/dashboard-report.json`) resta valida.
- **Frontend** (`KpiSection.svelte`):
  - la prima `KpiMetricBar` riceve `tooltipHtml` costruito con `tooltipRows` come `cashTooltipHtml`; descrizione =
    chiave esistente `dashboard.unrealizedDeltaTooltip`; righe 📈 «Assets in USD» per ogni A, 💱 «USD → EUR rate»
    per ogni A ≠ T; senza righe, tooltip semplice come oggi;
  - chiavi nuove: `dashboard.unrealizedAssetEffect`, `dashboard.unrealizedFxEffect`, `dashboard.unrealizedUnsplit`.
    Argomenti semplici, niente ICU plural/number: il problema della cache dei formatter per locale non si applica;
  - importi con `formatMoney` come la liquidità (stesso mascheramento privacy).
- **Proposta:** in 1.2, passi P8–P9, dopo il resto e tagliabili senza toccarlo.

---

## 5. Test (rossi prima, scritti dal test-author)

Regole del prompt al test-author:
- solo questo worktree;
- `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`;
- corsia 6161 / `/tmp/librefolio-r2-p`;
- niente `./dev.py` nudo, venv, installazioni o `--force`;
- niente posizioni fisse, conteggi globali, attese a orologio o testi tradotti;
- dati propri, creati e cancellati dal test.

### 5.1 Rossi prima del codice (P1)

| # | File (selettore) | Caso | Perché è rosso oggi |
|---|---|---|---|
| U | `test_services/test_average_cost.py` nuovo (`services financial-utils`, riallineato) | U1 stessa valuta: acquisti, vendite, split, costo zero; nessuna `convert_bulk` (sonda); U2 #32: C_T = `Decimal("400")`, una chiamata, nessuna voce T→T; U3 P = A ≠ T; U4 P ∉ {A, T} via T, effetto cambio 0 al giorno d'acquisto; U5 tasso T mancante → coppia e date ordinate, quantità sì, costo no; U6 solo ramo A mancante; U7 conservazione esatta, uscita totale, oversold; U8 split avanti/indietro; U9 ordine nello stesso giorno; U10 costo sconosciuto; U11 più posizioni = una chiamata; U12 `state_at`; U13 adattatore (segno BUY, valuta None, CBO, share, split) | il modulo non esiste |
| S | `test_financial/test_portfolio_service.py` (`services roi-fifo-utils`, DB di test reale con `FxRate` inseriti) | S1 #32 EUR: `open_cost_basis == 400`, WAC riga 400/Q, non realizzato MV − 400; S2 USD invariato; S3 ADJ-in con CBO in EUR su asset USD: capitale versato corretto, P&L totale non gonfiato; S4 tasso anteriore alla storia: `missing_fx_pairs` con coppia e date, issue `MISSING_FX_RATES`, costo non a zero muto | oggi 0, nessun issue |
| A | `test_api/test_portfolio_api.py` (`api portfolio`, server della corsia) | `POST /portfolio/report` EUR → 400,00 e banner assente; USD → invariato; variante con tasso mancante → issue nel `data_quality` | oggi 0 |

### 5.2 Invarianti in una valuta sola (verdi prima e dopo)

Scritte in P1 sul codice di oggi; devono restare verdi, uguaglianza `Decimal` esatta con quozienti finiti:
- motore (DB di test): costo aperto e non realizzato per giorno, realizzato per vendita, WAC di riga;
- facciata: `WACPreviewResultItem` intero per acquisti, vendite, split, costo zero, uscita totale e nuova pool;
- `/portfolio/wac`: la serie;
- lotti: linee WAC per broker e cumulativa;
- realizzato e contributi del periodo.

### 5.3 Da adattare (dopo P2–P6)

- 13 costruzioni di `DailyStateBuilder` in 10 file di test (`test_portfolio_engine_vnext.py`, 8 file in
  `test_financial/test_portfolio_engine/`, `test_external/test_brim_providers.py:1563`): helper di test comune
  che costruisce `average_costs` dal nucleo puro con tassi forniti;
- `TestPrivateCostHelpers` (`test_daily_state_builder.py:636`), che fissa i tassi incrociati: sostituito dai test U;
- `test_financial_utils.py`: sostituito da `test_average_cost.py`;
- `test_lots_analysis_pure.py`: `WACInputTX` e `_compute_wac_series`;
- `test_portfolio_allocation_source.py`: oracolo (permesso D);
- `test_transaction_service.py::test_get_cost_basis` e `test_broker_service.py` `average_cost_per_unit` (se D9);
- frontend: `KpiSection.test.ts` (righe del tooltip, somma, niente riga T→T, privacy).

### 5.4 Selettori (uno alla volta nella corsia)

```bash
P="PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6161 --data-dir /tmp/librefolio-r2-p"
$P services financial-utils            # unità della funzione
$P services portfolio-engine           # test_portfolio_engine_vnext.py
$P services roi-fifo-utils             # test_financial/: motore, service, lotti, YOC
$P services lots-analysis-pure
$P services portfolio-allocation-source
$P services transaction ; $P services broker ; $P services ai-export
$P api portfolio ; $P api portfolio-wac ; $P api transactions-wac ; $P api pac-planner-tool
$P external brim-providers             # una costruzione del builder
$P front-utility component-unit        # KpiSection.test.ts (dopo npm ci)
```

Per chiudere: `services all` + `api all`. Coverage: non mi aspetta.

---

## 6. Doc, CHANGELOG, conflitti, rischi, passi, definizione di fatto

### 6.1 Documentazione

- **Sviluppatore (EN):** `developer/backend/transactions/wac.md` (riscrittura: funzione unica, facciata, motore,
  diagnostica), più la sezione costo nella pagina motore se c'è.
- **Teoria (EN + IT/FR/ES):**
  - `weighted-average-cost` (§ multi-currency, formula `CB`);
  - `portfolio-engine/book-value` (formula OCB: oggi dice cambio della data di valutazione);
  - `portfolio-engine/period-pnl` (Δ non realizzato con il cambio, residuo);
  - `portfolio-engine/yield-on-cost` (formula del denominatore, `:80-87`).
- **Utente (EN + IT/FR/ES):**
  - `user/dashboard/kpi-cards` (tooltip; correggere «± small residuals from FX rounding», `:55`);
  - `user/dashboard/positions` (WAC per unità);
  - eventualmente `user/ai-export/*`.
- **Sviluppatore frontend:** `developer/frontend/data-quality-banner.md`, se nascono fonti/issue nuovi.
- **Wiki** (`wiki-file` a fine lavoro): decisione nuova «costo storico in T, funzione unica»; aggiornare
  `concepts/inline-wac-computation`, `entities/portfolio-engine`, `entities/portfolio-service`, `features/F-097`;
  chiudere `problems/test-transaction-implied-constructor-mismatch`.

Inglese con `docs-writer`; validazione con build e link check (mai `mkdocs serve`).

### 6.2 CHANGELOG proposto (`[Unreleased]`, lo scrivi tu)

`### 🐛 Fixed` → `#### 💱 Exchange rates and the Dashboard`:
- **An asset bought in your display currency but quoted in another one no longer shows a zero purchase cost.** With
  the Dashboard in euro, a US-dollar asset bought with euro counted no cost at all, so its whole value appeared as
  unrealized gain; the purchase cost is now exactly what you paid. Opening positions and transfers whose cost is in
  the display currency are fixed the same way, and no longer inflate the total P&L
  ([#32](https://github.com/Librefolio/LibreFolio/issues/32)).
- **A missing exchange rate is no longer a silent zero.** When a rate needed for a purchase cost, a sale or a cash
  movement is missing, the yellow banner names the pair and the dates, and **Sync rates** downloads them.

`### 🔄 Changed`:
- **Purchase cost is what you paid, in the display currency.** Each purchase is converted at its own date's rate, so
  the purchase cost of an asset priced in another currency no longer moves with today's rate; sales are measured
  against that cost, and the average price per unit and the yield on cost follow it. Portfolios in a single currency
  show the same figures as before.
- *(D11)* **The unrealized change includes the exchange rate, and its tooltip splits it.** For assets priced in
  another currency, the Dashboard's *Unrealized change* now includes the effect of the exchange rate, which used to
  end up in the reconciliation residual; its tooltip shows the assets' own change for each currency and the
  exchange-rate effect for each pair.
- *(D9, riga API)* `GET /brokers/{id}/summary` reports each holding's cost from its purchases, sales and transfers,
  in the asset's currency.

### 6.3 Conflitti previsti

| File | Chi altro | Natura |
|---|---|---|
| `portfolio_engine.py`, `portfolio_service.py` | nessuno attivo noto (N ha lavorato sul frontend) | miei; molte righe |
| `schemas/portfolio.py`, `zodios-client.ts` | condivisi | solo aggiunte |
| `lots_analysis_service.py`, `broker_service.py`, `transaction_service.py` | — | piccoli |
| `KpiSection.svelte`, `KpiSection.test.ts` | area Dashboard (N su `+page.svelte`) | il tooltip non tocca `+page.svelte` |
| cataloghi i18n | O (rimozioni) | io dopo, solo aggiunte |
| `test_portfolio_allocation_source.py` | D | un test |
| `test_brim_providers.py` | BRIM | una costruzione |
| `_backend_services.py` (runner) | condiviso | una voce |
| `CHANGELOG.md`, doc Dashboard | condivisi (N ha toccato `dashboard/index.en.md`) | additivi |
| componenti AI Export | D12 | testo + versioni |

### 6.4 Complessità e rischi

**Complessità alta**: è il cuore del motore e cambia di proposito dei numeri visibili.

| Rischio | Mitigazione |
|---|---|
| Regressioni del motore (K/R, ECF, candele, funding, contributi per broker) | 40 test vnext + i file di `test_portfolio_engine/` adattati, invarianti in valuta unica, U7 conservazione |
| Numeri che cambiano per i portafogli in valuta | voluto; CHANGELOG, doc, tooltip (D11) |
| PAC: ultime cifre (D5) e caso CBO = 0 | misura sulle fixture, decisione tua prima del merge |
| AI Export: semantica e versioni (D12) | passa da te; la skill di probe guida i test |
| Banner nuovi dove oggi si perdono importi (D7) | è il comportamento giusto; da dire nel CHANGELOG |
| Fixture gallery | campi nuovi opzionali con default |
| `DailyStateBuilder` costruito in 10 file di test | parametro obbligatorio + helper comune: niente default silenziosi |
| Fuori perimetro, solo annotati | cassa estera a cambio storico nel motore (`:658`, mentre la KPI liquidità usa il cambio d'oggi); costo trasportato nei trasferimenti interni (oggi CBO all'arrivo, resta così) |

### 6.5 Passi in ordine

Ogni passo aggiorna questo piano con ✅ e data, `Note implementazione` e `Fuori pista`.

- **P0** ✅ (07/10) — Fast-forward del developer sulla punta; verificare HEAD = target; copiare il piano nel journal;
  corsia libera.
  > **Note implementazione**:
  > - HEAD = `dev_release2` = `d07412899cdd7c6afb382d2f9ea193562ba5c890`, worktree pulito (`git rev-parse`,
  >   `git status --short` vuoto);
  > - `lsof -nP -iTCP:6161/6171 -sTCP:LISTEN` vuoto: porte libere;
  > - piano copiato da `plan.md` di sessione;
  > - aggiunte le sezioni «Decisioni prese e permessi» e «2bis. Contratto fissato prima di P1».
  >
  > **⚠️ Fuori pista**:
  > - la prima verifica (12:3x) trovava ancora `c9a602f74`: mi sono fermato e l'ho segnalato al coordinator, che ha
  >   confermato il fast-forward alle 12:57;
  > - `frontend/node_modules` assente: `npm ci` (permesso dato) solo quando servirà il frontend (P8–P10).
- **P1** ✅ (07/10) — Test-author: rossi U/S/A e invarianti verdi (§5.1–5.2); registrazione nel runner (permesso).
  > **Note implementazione**:
  > - **Creati**:
  >   - `test_services/test_financial_math/{__init__,test_average_cost}.py`: 35 test U (U1–U15 più U5b, U9b,
  >     U12b e i casi limite di U15);
  >   - `test_services/test_financial/test_portfolio_cost_currency.py`: S1–S6 e I1–I7.
  > - **Aggiunto** in coda a `test_api/test_portfolio_api.py`: `TestIssue32PurchaseCostInReportCurrency`.
  > - **Runner**: nuovo selettore `services financial-math` (pure) in `_backend_services.py`; `financial-utils`
  >   resta fino a P3.
  > - **Esito**: 50 rossi, 10 verdi.
  >   - U: tutti rossi per `ModuleNotFoundError`.
  >   - S1, S3, S4, S4b, S5, S6 e A-EUR: rossi sui sintomi #32 (costo aperto 0 invece di 400/120/100, WAC 0 invece
  >     di None, nessun `MISSING_COST_BASIS`, nessuna data d'acquisto fra quelle delle coppie mancanti).
  >   - S2, I1–I7 e A-UZS: verdi.
  >   - `services roi-fifo-utils` completo: 514 passati e 6 falliti, cioè solo i rossi voluti.
  >   - `check-orphans` pulito.
  >
  > **⚠️ Fuori pista**:
  > - **Classe API.** Il backend condiviso non parte: `dev.py server --test` costruisce il frontend e
  >   `node_modules` manca. La classe ha girato con `--no-shared-server` (lo scheduler parte in processo per ~5 s).
  >   Il primo avvio fallito ha lasciato file ignorati da git: `frontend/src/lib/api/{generated.ts, openapi.json,
  >   tool-contracts.openapi.json}` e `frontend/static/fonts/`. Da rilanciare sul backend condiviso dopo `npm ci`.
  > - **Valute sostituite**:
  >   - BWP invece di BTN: `test_risk_asset_set.py` salva un tasso BTN/EUR;
  >   - UZS invece di ISK per l'API: `test_fx_core.py` cancella i tassi in ISK;
  >   - MNT e KGS per i «mancanti», con verifica preliminare che non esistano tassi né rotte.
- **P2** ✅ (07/10) — `average_cost.py`: dataclass, adattatore, nucleo, conversioni a lotti, diagnostica → U verdi.
  > **Note implementazione**:
  > - **Creati**: `backend/app/services/financial_math/__init__.py` (docstring con la regola del layer, nessun
  >   import) e `financial_math/average_cost.py`, secondo il contratto §2bis.
  > - **Interfaccia**:
  >   - funzione pubblica: `compute_average_costs`;
  >   - helper pubblici: `cost_movement_from_transaction`, `determine_target_currency`;
  >   - nucleo privato: `_conversion_requests`, `_fold_average_costs`.
  > - **Esito**: `services financial-math` → 35 passati; ruff e black puliti.
- **P3** ✅ (07/10) — Facciata `compute_wac_iterative` sopra la funzione; eliminare `wac_utils` internals ed export pigri
  (`utils/financial/__init__.py`) → `portfolio-wac`, `transactions-wac`, PAC, invarianti verdi.
  > **Note implementazione**:
  > - In `portfolio_service.py` restano query, rilevamento split, fingerprint e cache. Il resto del corpo diventa:
  >   - righe ordinate `(date, id)` → `cost_movement_from_transaction`;
  >   - valuta target = override oppure `determine_target_currency`;
  >   - una `compute_average_costs(asset_leg=False)`;
  >   - fail-safe su qualunque mancante del ramo T, poi `_wac_qualifying_txs`, che mappa i passi sul vocabolario
  >     `effect` di prima (`add_unknown_cost` → `add_zero_cost`).
  > - Tolto il `noqa: C901`.
  > - **Esito**:
  >   - invarianti I4–I6 verdi;
  >   - `services portfolio-allocation-source` 89/89;
  >   - `api portfolio-wac` 10/10 e `api transactions-wac` 14/14 sul backend condiviso;
  >   - ruff e black puliti; porta 6161 libera.
  >
  > **⚠️ Fuori pista**:
  > - L'eliminazione di `wac_utils.py` (e dei suoi export) slitta a **P6**: i lotti ne sono l'ultimo utente.
  > - `npm ci` (permesso) eseguito qui per avere il backend condiviso dei test API. npm 11 non ha lanciato lo
  >   script `postinstall` di esbuild («install-scripts»), ma il build del frontend nel runner funziona.
- **P4** ✅ (07/10) — Motore: `calculate()` → `compute_average_costs`; builder senza conversioni del costo;
  `wac`/`wac_asset`/`cost_complete`; `realized_sales`; `missing_fx` (D7); in transito (D6); `EngineEndState`; helper
  di test comune → engine e vnext verdi, S1–S3 verdi.
  > **Note implementazione** (`portfolio_engine.py`):
  > - **Costruzione**:
  >   - `build_cost_positions()` costruisce le posizioni `(asset_id, broker_id)` dalle transazioni classificate
  >     (share applicato, solo date ≤ `date_to`);
  >   - `calculate()` fa una sola `compute_average_costs` (ramo asset acceso) e la passa a `DailyStateBuilder`
  >     (`average_costs` obbligatorio).
  > - **Replay del builder**:
  >   - il builder segue i passi con un cursore per posizione (`_next_cost_step`, che fallisce se l'ordine non
  >     torna);
  >   - capitale in natura ADJ-in = `cost_report_change` del passo `add`; ADJ-out, vendite e K/R = costo storico
  >     tolto dal pool;
  >   - costo aperto = Σ `cost_report_for(q)`, senza FX;
  >   - `DailyPositionState.wac` in T (None se il costo è incompleto), più `asset_currency`, `wac_asset` e
  >     `cost_complete`; `unrealized_pnl` è None se il costo è incompleto.
  > - **Nuovi output**: `UnrealizedSplit` per valuta in `DailyPortfolioState.unrealized_by_currency` (D11, dato
  >   pronto); `RealizedSale` in `result.realized_sales` (D8); `result.missing_fx`, cioè i fallimenti dei movimenti
  >   (costo, cassa, flussi, costo in transito) più quelli della funzione (D7).
  > - **D6**: il costo in transito si converte alla data d'arrivo (`_convert_movement`), e il preload chiede
  >   `(cbo_ccy, arrivo)` invece di ogni giorno.
  > - **Rimossi**: `_buy_unit_cost`, `_compute_open_cost_basis_inline`, `_capital_flow_for_adjustment_in`,
  >   `_apply_split_rescale` e la richiesta dei tassi dell'asset alle date dei BUY.
  > - **Aggiunto** `load_configured_fx_pair_sets()`, condiviso con service e lotti.
  > - **Esito**: S1, S3 e S4 verdi; invarianti verdi.
  > - Test del motore (13 costruzioni, `TestPrivateCostHelpers`, transito, preload) affidati al test-author.
  > - **Adattamento dei test** (test-author):
  >   - nuovo helper `test_services/_engine_average_costs.py`, che costruisce `build_cost_positions` e risolve le
  >     richieste dalla stessa `fx_rate_map` del builder;
  >   - le 13 costruzioni ricevono `average_costs`;
  >   - `TestPrivateCostHelpers` sostituita da `TestCostConversionThroughAverageCosts`, compreso il caso #32 a
  >     livello di builder (500 € esatti);
  >   - due test nuovi sul transito: costo fisso alla data d'arrivo, e tasso d'arrivo mancante che finisce in
  >     `_missing_fx`;
  >   - preload: costo AUD solo alla data d'arrivo; nessun tasso JPY alla data di un BUY fuori intervallo.
  > - **Esito**: `services portfolio-engine` 42/42; `services roi-fifo-utils test_portfolio_engine` 188/188;
  >   `external brim-providers` (blocco Crédit Agricole) 1/1.
  >
  > **⚠️ Fuori pista**:
  > - **Valori attesi cambiati per scelta**:
  >   - `it_asset_cb` passa da 36 a 30 (D6: tasso d'arrivo 0,75 invece di quello del giorno, 0,9);
  >   - le chiavi AUD del preload passano da {01-01, 01-02} a {01-04}.
  > - **Vendita oltre la quantità** (`TestNegativeQuantityExcludedFromCandle`: vendute 15 su 10): il realizzato
  >   passa da 0 a 500 e la ripartizione K/R da 1500/0 a 1000/500. Il pool cede tutto il suo costo (1000), non più
  >   WAC × 15. È la regola di §2bis (clamp + segnalazione); il test non lo asserisce.
  > - **`test_brim_providers.py`**: l'import dell'helper sta dentro il test, con `noqa: PLC0415`, perché era
  >   permesso toccare solo il blocco ~`:1563`.
- **P5** ✅ (07/10) — Service: realizzato ed estremi dal motore (D8), YOC (D10), unione delle coppie
  mancanti, eliminare i ripieghi silenziosi → S4 e A verdi.
  > **Note implementazione**:
  > - **`get_summary`**:
  >   - realizzato = Σ `_period_realized_sales` (vendite nel periodo con ricavo convertito e costo completo):
  >     sparisce il ciclo `compute_wac_iterative` per ogni vendita;
  >   - le coppie mancanti del CBO in natura non si scartano più;
  >   - il rendimento annualizzato di riga richiede `cost_complete`;
  >   - `_engine_missing_fx_pairs` porta i movimenti a qualunque data e le valutazioni nei giorni del periodo;
  >   - `_missing_cost_basis_assets` alimenta l'issue nuovo `MISSING_COST_BASIS` (warning, `navigate_asset`,
  >     chiave `dataQuality.missingCostBasis`) in `build_data_quality_report`.
  > - **`get_positions_contribution`**: motore calcolato in testa; realizzato e `per_cost_sold` dagli eventi; costi
  >   d'inizio e fine periodo da `_boundary_cost` (`state_at`, None se il costo è incompleto). Anche qui spariscono
  >   le chiamate a `compute_wac_iterative`.
  > - **`get_report`**: anche il ramo senza summary riceve le coppie mancanti e `MISSING_COST_BASIS`.
  > - **YOC (D10)**: nessun cambio di codice; il WAC passa già in T (identità, nessuna riga di provenienza FX per
  >   il WAC).
  > - **Docstring** di `AcquisitionFundingSeries` aggiornata: il motore ha il canale dei movimenti.
  > - **Esito**:
  >   - `services roi-fifo-utils` 523/523, compresi S1–S6, I1–I7 e i 90 test di `test_portfolio_service.py`;
  >   - `services broker` 33/33;
  >   - rossi attesi, affidati al test-author: `services transaction` (`test_get_cost_basis`, metodo rimosso in P7),
  >     `lots-analysis-pure` e `portfolio-allocation-source` (raccolta fallita per l'import di `wac_utils`).
  > - **`api sync`** (07/10) eseguito dopo P8: rigenerati `generated.ts` e `openapi.json`, entrambi ignorati da
  >   git, con `MISSING_COST_BASIS` e `period_unrealized_breakdown`; nessun file tracciato del frontend cambia
  >   (lo schema zod sta solo in `generated.ts`).
- **P6** ✅ (07/10) — Lotti sulla funzione + FX mancanti nel `data_quality`.
  > **Test (test-author)**: `test_lots_analysis_pure.py` riscritto, con 9 test puri sulle linee e il buco fino allo
  > svuotamento della pool; `test_portfolio_cost_currency.py` L1 (USD comprato in EUR, nessuna `convert_bulk`), L2
  > (MGA senza tasso: coppia, issue, `DEGRADED`, nessun punto) e L3 (ADJUSTMENT-in senza costo: un solo
  > `MISSING_COST_BASIS`, `DEGRADED`, più un controllo con costo che resta `COMPLETE`). `services lots-analysis-pure`
  > 106/106, `services roi-fifo-utils` 531/531.
  > **Note implementazione**:
  > - **Linee WAC** (`lots_analysis_service.py`): `_compute_average_cost_lines` (una posizione per broker più
  >   `__all__`, una chiamata FX); i punti si campionano con `state_at`, e un giorno con costo incompleto non ha
  >   punto.
  > - **Buchi FX**: `_report_average_cost_fx_gaps` mette coppie e date in `data_quality.missing_fx_pairs`, più gli
  >   issue FX classificati come nel portafoglio; lo stato passa a `DEGRADED`.
  > - **Rimossi** `_build_wac_context`, `_build_wac_row`, `_compute_wac_series` e il blocco WAC di
  >   `_collect_fx_needs`.
  > - **`wac_utils.py` eliminato**, insieme agli export pigri di `utils/financial/__init__.py`; aggiornato il
  >   commento in `transaction_service.py`.
  >
  > **⚠️ Fuori pista**:
  > - un `git rm --cached` ha messo in stage la cancellazione di `wac_utils.py`: l'ho tolta subito dallo stage con
  >   `git restore --staged` (indice = HEAD, 0 file in stage); il file resta cancellato solo nel worktree;
  > - test da adattare al test-author: `test_financial_utils.py` (da eliminare insieme al selettore
  >   `financial-utils`), le sezioni WAC di `test_lots_analysis_pure.py`, l'oracolo PAC;
  > - (07/10, dopo la review del docs-writer) **buco silenzioso trovato e chiuso**: un acquisto senza costo noto
  >   svuotava la linea WAC dei lotti senza issue e senza `DEGRADED`. Ora `_report_average_cost_gaps` (rinominato da
  >   `_report_average_cost_fx_gaps`, riceve anche l'asset) emette `MISSING_COST_BASIS` per l'asset analizzato
  >   tramite `build_data_quality_report(missing_cost_basis_assets=...)`, e lo stato passa a `DEGRADED` anche per il
  >   costo sconosciuto. Il test l'ho chiesto al test-author, la doc al docs-writer. Ruff, black e import puliti.
- **P7** ✅ (07/10) — Broker summary (D9); eliminare `get_cost_basis`.
  > **Test (test-author)**: 6 test nuovi in `test_broker_service.py`, tutti verdi, e quello esistente 1700/30 passa
  > ancora. Casi: 2250 / 150 / P&L 450; EUR→MUR alla data d'acquisto; PYG senza tasso → None + coppia;
  > TRANSFER/ADJUSTMENT-in senza costo → None, controllo con costo 1650. `test_get_cost_basis` rimosso.
  > `services broker` 39/39, `api brokers` 29/29.
  > **Note implementazione**:
  > - **`BrokerService._holding_average_costs`**: righe `(broker, asset)` con quantità, ordinate `(date, id)`, più
  >   il rilevamento degli split; una `compute_average_costs` per valuta d'asset (T = A, ramo asset spento).
  > - **Schema**:
  >   - `BRAssetHolding.total_cost` = `cost_report_for(quantità)`;
  >   - `total_cost` e `average_cost_per_unit` diventano Optional (None se il costo è incompleto), e allora anche
  >     il non realizzato è None;
  >   - nuovo `BRSummary.missing_fx_pairs`.
  > - **Rimosso** `TransactionService.get_cost_basis`.
  > - Il frontend non legge questi campi (verificato).
  >
  > **⚠️ Fuori pista**: per P6 e P7 il codice è stato scritto prima dei test (mentre il test-author adattava il
  > motore), quindi i loro test nuovi nascono dopo l'implementazione. Rispetto al codice di prima, il motivo per
  > cui sarebbero rossi:
  > - lotti: oggi usano il costo non convertito, senza nessun issue;
  > - riepilogo broker: oggi somma i BUY, 3000 invece di 2250.
- **P8** ✅ (07/10) — scomposizione nel backend.
  > **Test (test-author)**, in `test_portfolio_cost_currency.py`, tutti verdi:
  > - B1: ISK asset 20 + fx 80 = 100;
  > - B2: dal 15/10, +20 / +105 = 125;
  > - B3: solo EUR, una riga asset di 250;
  > - B4: riga unsplit TJS −300, e le cinque righe sommano esattamente −175.
  > **Note implementazione**:
  > - **Motore**: per giorno e per valuta d'asset calcola `UnrealizedSplit(asset, fx, unsplit)`, nello stesso
  >   ciclo che somma valore e costo aperto (`_add_unrealized_part`).
  >   - Per A = T tutto finisce in `asset`.
  >   - È `unsplit` il caso senza MV, senza tasso o con un costo incompleto in una delle due valute.
  > - **Schema**: `UnrealizedBreakdownRow(kind, asset_currency, period_delta)` e
  >   `PortfolioSummary.period_unrealized_breakdown` (default lista vuota: la fixture della gallery resta valida).
  > - **Service**: `_unrealized_breakdown_rows` usa gli stessi stati estremi del Δ non realizzato.
  >   - Righe in ordine: asset, poi fx (solo per A ≠ T), poi unsplit se ≠ 0; dentro ogni gruppo T prima, poi
  >     alfabetico.
  >   - Somma esatta.
  > - I test (test-author) arrivano dopo il codice: stesso fuori pista di P6/P7.
- **P9** ✅ (07/10 codice, 08/10 chiavi i18n) — Tooltip in `KpiSection` + chiavi i18n (dopo O) + test di
  componente.
  > **Note implementazione**:
  > - **Rossi visti prima del codice**: il test-author ha scritto 6 test in `KpiSection.test.ts`: 4 rossi (righe e
  >   valori, ordine ricevuto, nessuna riga fx inventata, privacy) e 2 verdi (scomposizione vuota o assente: tooltip
  >   di testo come oggi). `front-utility component-unit`: 2831 passati, 4 falliti, solo questi.
  > - **`KpiSection.svelte`**:
  >   - `tooltipRows` accetta un `testid` facoltativo per riga (`<tr data-testid=…>`, con escape);
  >   - nuovo `unrealizedDeltaTooltipHtml`: righe nell'ordine del backend, 📈 asset / 💱 fx / ❔ unsplit, etichette con
  >     escape, importi con `formatMoney(..., {signed: true})`, cioè lo stesso formatter della liquidità e quindi la
  >     stessa privacy;
  >   - la prima `KpiMetricBar` riceve `tooltipHtml`; senza righe resta il tooltip di testo di prima.
  > - Il testo esistente `dashboard.unrealizedDeltaTooltip` («Change in unrealized gain/loss on positions still
  >   open.») resta valido anche con il cambio incluso: nessuna modifica alle chiavi esistenti.
  > - **In attesa**: le 3 chiavi `dashboard.unrealizedAssetEffect`, `dashboard.unrealizedFxEffect`,
  >   `dashboard.unrealizedUnsplit` (più `dataQuality.missingCostBasis`) entrano con `dev.py i18n add` solo quando il
  >   coordinator dice che O è integrato. Fino ad allora il tooltip mostra gli id delle chiavi.
  > - **Verifica (07/10)**: `front-utility component-unit` 2835/2835, quindi i 4 rossi di P9 sono verdi.
  >   `npm run check` (svelte-check): 0 errori, 0 warning. Prettier pulito.
  > - Il banner legge `issue.message_i18n_key`: finché `dataQuality.missingCostBasis` non c'è, `MISSING_COST_BASIS`
  >   mostra la chiave grezza. È atteso, e si chiude insieme alle altre chiavi dopo O.
  > - **Chiavi i18n (08/10)**, dopo il via del coordinator (O integrato nei treni 8 e 9):
  >   - aggiunte con `dev.py i18n add` (script `/tmp/libreFolio_p_i18n_add.sh`), testi approvati dal coordinator;
  >     l'IT di `dataQuality.missingCostBasis` usa il suo testo («{count} asset con un'acquisizione senza costo
  >     d'acquisto — conteggiata a zero finché non lo imposti»);
  >   - testi diversi in tutte e 4 le lingue, quindi nessun rischio con la cache ICU per testo; segnaposto verificati
  >     uguali ai parametri del codice (`currency`, `from`/`to`, `count`);
  >   - diff piccolo, +6/−2 per catalogo: le chiavi in coda ai namespace `dashboard` e `dataQuality`, più la virgola
  >     sulla chiave che prima era l'ultima.
  > - **Verifica (08/10)**:
  >   - `i18n audit` exit 0: 4156 chiavi complete (4152 + 4), 0 chiavi backend mancanti, 0 inutilizzate; le 3
  >     «not verified» e la famiglia PAC `tools.allocation.constraints.` sono le stesse di prima, preesistenti;
  >   - `api sync` OK; `front check` 0 errori, 0 warning; prettier pulito sui 4 cataloghi;
  >   - `utils gate-i18n-usage` 195; `front-utility core-unit` 116/116 file (3405 test); `component-unit` 2835.
- **P10** ✅ (07/10) — AI Export (D12(a)): testo e versioni.
  > **Note implementazione**:
  > - **Rossi visti prima del codice**: 4 backend (versione 2 su spec reale, segnaposto e registro; envelope v2
  >   schema 1) e 2 renderer (v2 schema 1 compatto e identico a v1). Le 4 guardie verdi del renderer: v3, v2 con
  >   schema 2 e `portfolio.summary` v2 restano in YAML.
  > - **Versioni**: `portfolio.provenance` e `broker.provenance` passano a `version=2`, sia nelle spec
  >   (`portfolio_financial.py`, `broker_financial.py`) sia nei segnaposto di `components/catalog.py`.
  >   `schema_version` resta 1: la forma del payload non cambia.
  > - **`valuation_semantics`** (stesso testo nei due builder):
  >   - `wac_per_unit` e `open_cost_basis` sono il costo medio storico nella valuta target: ogni acquisto è convertito
  >     al cambio della sua data, quindi il costo non si muove con i cambi successivi;
  >   - un acquisto senza costo aggiunge quantità a costo zero;
  >   - il realizzato confronta il ricavo, convertito alla data della vendita, con quel costo;
  >   - `original_cost`/`residual_cost_basis` dei lotti FIFO sono convertiti alla data d'apertura del lotto (prima il
  >     testo li chiamava, a torto, WAC);
  >   - il valore di mercato è al cambio della data di valutazione, quindi il non realizzato include l'effetto cambio.
  > - **Renderer** (`snapshotDataRenderer.ts`): mappa `COMPACT_COMPONENT_VERSIONS` (una `Map`, così un id ostile come
  >   `constructor` non legge il prototipo). Le due provenance sono compatte a v1 e v2 con schema 1; tutto il resto
  >   resta compatto solo a v1/schema 1.
  > - Ruff, black e prettier puliti. Probe reale non eseguita: il test funzionale del renderer dimostra che v2 rende
  >   byte per byte come v1, e cambia solo il testo della semantica. Se la vuoi, una probe mirata è da concordare.
  > - **Verifica (07/10)**: `services ai-export` 929/929 (i 4 rossi D12 ora verdi), `front-ai-export unit` 359/359
  >   (i 2 rossi del renderer ora verdi, le 4 guardie YAML ancora verdi). Nessun test fissava la versione 1 o il testo
  >   vecchio. Nelle pagine MkDocs dell'AI Export nessun riferimento a `valuation_semantics` o alle versioni dei
  >   componenti: niente da riallineare.
  >
  > **⚠️ Fuori pista**: 2 test di `test_ai_export_components_asset_fx_integration.py`, che non avevo previsto, sono
  > diventati rossi. La fixture (riga 536) scriveva in DB una SELL con quantità **positiva** (`"4"`), violando la
  > regola dei segni che l'API impone («SELL requires quantity < 0»). Il vecchio WAC la nascondeva aggiungendo quelle
  > quote a costo zero; il nuovo la tratta come un acquisto di costo sconosciuto (`MISSING_COST_BASIS`). Con il
  > permesso del coordinator il test-author ha cambiato solo il segno (`"-4"`): broker 1 con 6 quote a WAC 90,
  > valutazione completa, file verde.
- **P11** ✅ (07/10) — Doc EN (`docs-writer`); niente traduzioni IT/FR/ES né stamp (decisione del
  developer); righe CHANGELOG al coordinator all'handoff.
  > **Note implementazione**:
  > - Il docs-writer ha aggiornato 15 pagine inglesi: sviluppatore (`wac.md` riscritta con la regola del layer
  >   `financial_math`, `lots_analysis_service.md`, `service.md`, `data-quality-banner.md`, `architecture/overview.md`),
  >   teoria (costo medio, book value, P&L di periodo, yield on cost, indice del motore, indice delle metriche,
  >   capitale versato) e utente (`kpi-cards`, `positions`, indice Dashboard). Build strict OK.
  > - Ha segnalato tre punti, tutti chiusi: il buco dei lotti (vedi P6), le descrizioni rimaste vecchie
  >   (`WACQualifyingTX.effect` in `schemas/wac.py` ora cita anche `split_rescale`, `WACSeriesPoint.effect` in
  >   `schemas/portfolio.py` non cita più `add_at_wac`, il commento del motore dice `calculate()`), e
  >   `fifo_lot_engine.md:9`.
  > - `fifo_lot_engine.md:9`: la pagina è dell'area di Q. Il coordinator mi ha autorizzato a correggere **solo quel
  >   riferimento** nel mio ramo, perché diventa falso solo con il mio cambiamento. Ora cita
  >   `services/financial_math/average_cost.py`. Q rinomina `eligible_income_quantity` in un'altra sezione, quindi
  >   la fusione resta pulita.
  > - Follow-up chiesto al docs-writer: il `MISSING_COST_BASIS` dei lotti, l'eccezione «costo sconosciuto» dove una
  >   pagina dice che i portafogli in una sola valuta non cambiano, il vocabolario degli effetti.
  > - **Follow-up fatto (07/10)**:
  >   - `lots_analysis_service.md` (pipeline passo 7, `calculation_status`, sezione WAC Lines con
  >     `_report_average_cost_gaps`) e `data-quality-banner.md` (i due emettitori di `MISSING_COST_BASIS`: Dashboard
  >     e lotti) sono aggiornati; `wac.md` corregge la cella della diagnostica dei lotti;
  >   - nessuna pagina afferma «una valuta sola invariata»: l'eccezione va solo nel CHANGELOG;
  >   - il vocabolario degli effetti in `wac.md` era già allineato.
  > - **Verifica**: `dev.py mkdocs build` strict passa, nessun warning. `dev.py mkdocs check-links`: 89 validi, 3
  >   eccezioni note, più il rotto preesistente `user/assets/detail/chart/#rolling-return`.
- **P12** ✅ (07/10) — Lint/format (ruff + black; prettier + svelte-check), selettori §5.4, `services all` + `api all`,
  `git diff --check`, `wiki-file`, porta 6161 libera (`lsof`), handoff, FROZEN.
  > **Misura D5 (07/10)**: il vecchio `compute_wac_from_txlist` è stato ricostruito da `git show
  > HEAD:backend/app/utils/financial/wac_utils.py` in `/tmp/libreFolio_p_d5/`. Lo script
  > `/tmp/libreFolio_p_d5/measure_d5.py` (seed fisso) confronta le due aritmetiche su 2 × 2000 sequenze casuali in
  > una sola valuta (acquisti, vendite, split, uscite totali), il caso della PAC, e le confronta entrambe con il
  > risultato razionale esatto (`Fraction`). Log in `/tmp/libreFolio_p_d5/measure_d5.log`.
  >
  > | Dati | WAC corrente diverso | Diff. relativa max (corrente / finale) | Più vicino all'esatto |
  > |---|---|---|---|
  > | realistici (costi a 2 decimali, quantità fino a 6 decimali) | 32% dei passi | 9,2e-22 / 1,3e-22 | nuovo 569, vecchio 163, pari 1228 |
  > | quozienti periodici (caso peggiore) | 32,5% dei passi | 1,3e-25 / 3,1e-27 | nuovo 507, vecchio 293, pari 1184 |
  >
  > - Le differenze stanno oltre la 21ª cifra significativa: invisibili a qualunque arrotondamento di
  >   visualizzazione. Errore massimo rispetto all'esatto (dati realistici): vecchio 9,3e-23, nuovo 3,4e-23.
  > - I 41 passi con una pool «polvere» (< 1e-20 quote, prodotta da quantità periodiche sommate a 28 cifre) sono
  >   esclusi. Lì entrambe le aritmetiche danno un WAC senza senso, e con le quantità reali, a decimali finiti, la
  >   polvere non si forma (0 casi nei dati realistici).
  > - La suite PAC (89/89) passa con gli stessi valori attesi di prima: sulle fixture PAC non cambia nessuna cifra
  >   confrontata.
  >
  > **Gate (07/10)**, tutti nella corsia 6161 / `/tmp/librefolio-r2-p`, uno alla volta:
  > - `api sync` rilanciato dopo i ritocchi alle descrizioni degli schemi: cambiano solo file ignorati da git.
  > - Ruff pulito su tutti i 38 file Python toccati. Black pulito sulle nostre righe. `test_portfolio_api.py` e
  >   `test_portfolio_wac.py` falliscono black **già a HEAD**, solo su righe non nostre (hunk 1316–1802 e 43–236; le
  >   nostre sono da 2040 e a 367), quindi le lascio. `git diff --check` pulito, spazi in coda tolti dal piano.
  > - `services all`: la passata consolidata dà **5809 passati, 0 falliti**, ma il runner segna `financial-math` ✘
  >   («1 unit(s) produced no test case»). Vedi il fuori pista sotto.
  > - `api all`: **799 passati, 2 saltati**, exit 0, nessun ✘.
  > - La grep di §6.6 (`_buy_unit_cost`, `compute_wac_from_txlist`, `get_cost_basis`, `wac_utils`, `_build_wac_row`,
  >   `_compute_wac_series`, `if rate else`, `else cb_local`, `else ocb_local`) non trova nulla in `backend/app`.
  > - E2E non eseguiti: nessuno spec legge il tooltip della prima barra o le cifre di costo. `privacy-masking` e
  >   `dashboard-cache` leggono solo il valore principale della card 1.
  >
  > **⚠️ Fuori pista: difetto latente del runner.**
  > - **Causa** (riprodotta sul report junit reale):
  >   - `_consolidate_backend.py:260` ordina i percorsi delle unità, e `test_services/test_financial/` viene prima di
  >     `test_services/test_financial_math/` (`/` < `_`);
  >   - `_junit_results` (`:131`) attribuisce i casi alle unità-cartella con `dotted.startswith(d.rstrip("/"))`, senza
  >     confine;
  >   - così roi-fifo-utils si prende i 39 casi di financial-math, che risulta vuota.
  > - Il difetto c'era già. Lo espone il primo nome di cartella che ne estende un altro, `test_financial_math`.
  > - Il coordinator ha concesso la correzione (a): confine sul `/` più la cartella più specifica, con un test di
  >   regressione del test-author in `test_utilities/test_test_runner_cli.py` (selettore `utils test-runner-cli`),
  >   scritto rosso prima della correzione.
  > - **Rosso visto**: classe `TestJunitAttributionToDirectoryUnits`, 4 test e 14 casi.
  >   - 4 casi falliscono, tutti nell'ordine ordinato del runner: cartelle sorelle, attribuzione incrociata nei due
  >     versi, cartelle annidate.
  >   - 10 casi verdi: l'ordine inverso (prova che oggi il verdetto dipende dall'ordine) e la guardia «un'unità-file
  >     tiene i suoi casi».
  > - **Correzione** (`_consolidate_backend.py`, `_junit_results`): `dotted = "/".join(parts) + "/"`, poi
  >   `max((d for d in dirs if dotted.startswith(d)), key=len, default=None)`. La cartella deve combaciare su un
  >   confine `/` e vince la più profonda; il percorso esatto del file conserva la precedenza.
  > - **Verde**: `utils test-runner-cli` 36/36. Il replay sul report junit reale, nell'ordine ordinato, ora dà
  >   financial-math True e nessuna unità mancante.
  > - **Ruff**: gli 8 rilievi su `_consolidate_backend.py` (PLC0415 ×7, B007) esistono uguali a HEAD, perché ruff è
  >   configurato su `backend/`; il file di test è pulito.
  > - Solo `services` ha unità-cartella (`test_financial/`, `test_financial_math/`; utils, schemas, api ed e2e
  >   nessuna), quindi la correzione può cambiare solo quel gate.
  >
  > **Gate finali (07/10)**:
  > - `services all` rilanciato: **5809 passati**, exit 0, nessun ✘; `financial-math` ✓ e `roi-fifo-utils` ✓, ognuna
  >   con i suoi casi.
  > - `api all` 799 passati, 2 saltati (sopra).
  > - `external brim-providers` 626 passati, 1 saltato.
  > - Gli altri, già sopra: `front-utility component-unit` 2835/2835, `front-ai-export unit` 359/359,
  >   `utils test-runner-cli` 36/36, `check-orphans` pulito (test-author, dopo l'ultima registrazione).
  > - Porte: `lsof -nP -iTCP:6161 -sTCP:LISTEN` e `…:6171` non trovano nulla, e la 6171 non è mai stata usata.
  >   `git diff --check` pulito, niente in stage.
  >
  > **Wiki (`wiki-file`, project-historian, 07/10)**:
  > - **Nuove**: `decisions/financial-math-single-average-cost.md` e
  >   `problems/zero-purchase-cost-foreign-asset-paid-in-report-currency.md`.
  > - **Riallineate**: `concepts/inline-wac-computation`, `entities/portfolio-engine`, `entities/portfolio-service`,
  >   `entities/lots-analysis-service`, `features/F-097` (con `features/registry`),
  >   `decisions/wac-target-currency-last-acquisition` (nota di ambito per chiamante),
  >   `problems/test-transaction-implied-constructor-mismatch` (nota «Recurrence 2026-10-07»).
  > - **Corrette solo le frasi rese false da P**: `problems/wac-feedback-loop`, `concepts/3-pool-cash-model`,
  >   `concepts/pre-frame-frame-separation`, `features/F-058`.
  > - `index.md` e `log.md` aggiornati. L'aggiornamento del grafo è rinviato, perché graphify non c'è nel worktree.
  > - `check_source_paths.py`: 0 percorsi mancanti nelle pagine toccate, salvo la riga di `fifo_utils.py` in F-058,
  >   cancellato prima di P. Il controllo completo esce ancora 1 per derive altrove: 64 percorsi distinti, 88
  >   occorrenze, contro le 99 di prima.
  > - Derive più vecchie segnalate e lasciate: `domains/calculations.md`, `features/F-048.md`, le sezioni
  >   LAST_BUY_PRICE e TRANSACTION_IMPLIED.
  >
  > **Stato**: P0–P12 chiusi. Commit `de252a38a` (senza il footer BREAKING CHANGE, per decisione del developer: va
  > nel CHANGELOG sotto ⚠️ Breaking changes). Le chiavi i18n di P9 sono entrate l'08/10, dopo i merge (§6.5bis).

### 6.5bis Merge con `dev_release2` (07–08/10)

Il developer ha aperto i merge nel worktree; io ho risolto i conflitti e li ho messi in stage, senza commit.

- **Treno 9** (MERGE_HEAD `9ea2d519b`, merge commit `e0c40395c`). 165 file in stage, 3 conflitti attesi, tutti risolti
  in aggiunta (script `/tmp/libreFolio_p_resolve_merge.py`, con controlli sulla forma di ogni blocco):
  - `developer/architecture/overview.md`: tenute la voce «Financial Math Layer» e le 3 voci del treno 9 (Risk Engine,
    Tool Plugins, Onboarding Guides);
  - `LibreFolio_devWiki/index.md`: due righe vicine, ognuna cambiata da una parte sola (verificato sulla base
    `d07412899`), quindi la riga `ci-release-pipeline` del treno 9 e la riga `inline-wac-computation` di P;
  - `LibreFolio_devWiki/log.md`: in ordine di commit, prima O seconda passata (`6f728a541`, 14:36), poi le 4 voci
    di P (`de252a38a`, 16:33);
  - verificato per ciascun file: rispetto a HEAD restano solo i cambi del treno 9, rispetto a MERGE_HEAD solo
    quelli di P;
  - rivisti i file fusi in automatico che toccano P (`test_brim_providers.py`, `fifo_lot_engine.md`,
    `user/dashboard/index.en.md`): intatti e coerenti. Nessun manifest npm o pip cambiato.
- **Revisione combinata del treno 9**:
  - `api sync`, `front build --debug`, `front check` (0/0) OK; `services all` 5822; `utils all` 1169;
    `brim-providers` 626 + 1 saltato; `brim-degiro` 169; `component-unit` 2835; `front-ai-export unit` 359;
    `check-orphans` pulito; `mkdocs build` strict OK;
  - `api all`: 803 passati, 2 saltati, 1 fallito esterno. In `test_assets_provider.py::test_search_assets_basic`
    Yahoo dal vivo ha restituito 0 risultati per 'Apple' (16:04:18Z, senza errori, e le ricerche successive davano
    5 risultati); rilanciato da solo, `api assets-provider` è passato 24/24, con 'Apple' a 5 risultati alle 16:11:35Z;
  - `core-unit`: 1 file rosso, quello noto `optionFilter.test.ts › R13` (plugin DEGIRO di L), corretto nel treno 10;
  - `check-links`: 1 rotto, il preesistente `#rolling-return`;
  - `i18n audit`: mancava solo `dataQuality.missingCostBasis`. L'audit non vede le chiavi usate nel codice frontend
    e assenti dai cataloghi, per questo le 3 `dashboard.*` non comparivano.
- **Treno 10** (MERGE_HEAD `9d79c2dbe`, merge commit `e655003d3`). 32 file in stage, 1 conflitto, `log.md`, risolto
  in aggiunta: prima le 4 voci di P (16:33), poi «A slow language switch tore the whole app down» (`1c20b254f`,
  17:42), con lo script `/tmp/libreFolio_p_resolve_merge_t10.py`.
  - `index.md` si è fuso da solo con le righe di entrambi.
  - Il treno 10 non tocca codice di `backend/app`, manifest o i miei file del runner (solo `_backend_db.py`), e la
    correzione di `_junit_results` è intatta.
  - Convalida mirata: `front build --debug` e `front check` OK; `core-unit` 116/116; `component-unit` 2835;
    `front-ai-export unit` 359; `utils all` 1215; `check-orphans` pulito.
- Porte 6161 e 6171 libere dopo ogni giro.

### 6.6 Definizione di fatto

- **#32:** Dashboard EUR, costo di HYPE = `400` esatti; Dashboard USD invariata; gemelli ADJ/TRANSFER corretti,
  capitale versato compreso.
- **Una sola implementazione del costo medio**, usata da motore, facciata (anteprima, `/portfolio/wac`, PAC), lotti,
  service e broker summary. Nessuna traccia di `_buy_unit_cost`, `compute_wac_from_txlist`, `get_cost_basis` o dei
  ripieghi «importo non convertito» elencati in §1 (verifica con grep).
- **Ogni conversione mancante** del costo e del motore risale con coppia e date fino a `missing_fx_pairs` e al banner;
  nessuno zero muto.
- **Invarianti in valuta unica** verdi prima e dopo; suite di §5.4 verdi; `services all` + `api all` verdi.
- **D11:** righe del tooltip con somma esatta = Δ non realizzato, nessuna riga T→T.
- **PAC:** contratto invariato, differenze D5 approvate. **AI Export** secondo D12.
- **Chiusura:** doc e CHANGELOG pronti; piano aggiornato a ogni passo; porta 6161 libera; wiki aggiornato; FROZEN.

## 7. Seguito: lo staking del seed (08/10)

> Assegnato dal coordinator dopo la decisione del developer, presa nella chat di P. Scope: la correzione del seed;
> l'avviso `MISSING_COST_BASIS` resta; negli E2E non si provoca con transazioni; nessun test nuovo.

**Il problema.** Un E2E del treno 14 (`data-quality-banners.spec.ts:387`) contava un link in più. La causa era un
`MISSING_COST_BASIS` vero su Ethereum: il seed registrava lo staking ETH su Coinbase come `INTEREST` con +0,002 ETH e
+5 USD (`populate_mock_data.py`, «Day -7»).
- Una riga così l'app non può crearla, perché l'API vuole quantità 0 su INTEREST e DIVIDEND
  (`schemas/transactions.py:170-182`); il seed scrive direttamente nel DB.
- La ricompensa entrava due volte, come quote e come contanti.
- Prima del #32 il motore dava in silenzio a quelle quote il costo medio; dopo il #32 le segnala. Il conteggio di
  `:387` lo ha corretto N (treno 15).

**Analisi** (08/10):
- **Il WAC non è 2500 USD/ETH.** Il BUY del seed (0,8 ETH) è prezzato da `_derive_market_amount` sulla serie
  simulata, che dipende dalla data di generazione (`_stable_seed("price", asset.id, price_date)`), e non ha né
  commissione né cambio: asset, prezzi e BUY sono in USD. Nella run della corsia: BUY −890,50 USD, WAC 1113,125 USD/ETH.
  Un 2500 fisso sarebbe stato sbagliato di più del doppio: il costo va calcolato come fa la modalità Auto.
- **Chi dipende dalla riga.**
  - Nessun test backend, vitest o E2E cita lo staking, 0,802, il tag `long-term` o la cassa Coinbase.
  - I due «clone INTEREST» (`tx-clone.spec.ts:269`, `tx-paired-edit.spec.ts:73`) prendono il primo INTEREST in
    tabella, cioè quello di Recrowd (giorno −3, quantità 0). Il clone resta disponibile anche sui broker in sola
    lettura, dove lo spec controlla solo che edit e delete siano nascosti (`tx-clone.spec.ts:429-449`; il commento
    in testa allo spec che dice il contrario è vecchio): quindi non dipendono dallo staking.
  - Le coppie `delete-safe`/`delete-consume` vogliono 0,802 ETH su Coinbase, che resta.
  - La cassa USD di Coinbase resta positiva (circa 6000 USD).
  - `audit_transaction_signs.py` controlla solo i segni della cassa; `test_post_migration.py` usa dati suoi.
- **Gallery** (per M): la Dashboard usa lo snapshot statico, quindi non cambia. Cambiano un poco gli scatti del
  broker Coinbase (`gallery.spec.ts:2124-2195`) e della lista `/transactions`: lo staking appare come ADJUSTMENT, la
  cassa Coinbase ha 5 USD in meno, ed ETH su Coinbase ha WAC e P&L invece di «—». Nessuna asserzione su quei valori.

**Modifica** (`backend/test_scripts/test_db/populate_mock_data.py`):
- Lo staking diventa ciò che salverebbe l'import Coinbase: un `ADJUSTMENT` di +0,002 ETH, `amount` 0, nessuna cassa,
  `cost_basis_currency` USD, con `"cost_basis": "auto"`.
- Il ciclo dei movimenti passa `cost_basis_currency` e raccoglie le righe Auto. Dopo il `flush`, il nuovo
  `_seed_auto_cost_basis` scrive il costo: il WAC della posizione (broker, asset) alla data della riga, sulle righe
  fino a quella data esclusa la riga stessa, come fa l'app al commit. Funziona per date e non per ordine della lista,
  e si ferma con un errore su qualunque riga che non sia un BUY nella stessa valuta, invece di indovinare.
- Aggiornato il commento delle coppie `delete-safe` (0,802 ETH da BUY e ADJUSTMENT).

**Evidenze** (corsia 6161, `/tmp/librefolio-r2-p`):
- `db populate --force --clean` OK; il log dice «Auto cost basis for ADJUSTMENT #26: 1113.125 USD per unit».
- Nel DB, in sola lettura: la riga è un ADJUSTMENT 0,002, amount 0, CBO 1113,125 USD; nessun INTEREST o DIVIDEND con
  quantità; **nessuna riga** con quantità > 0, non BUY, senza CBO e non legata a uno split, quindi
  `MISSING_COST_BASIS` non può più scattare sul seed.
- `api portfolio` 51/51; `api brokers` 29/29; `front-transaction tx-clone` 6/6; `front-transaction tx-paired-edit`
  4/4. Ruff e black puliti.
- **Non eseguiti da me**: `front-portfolio dashboard` e `front-broker detail`. Il developer ha deciso di provarli
  insieme al resto, nella run complessiva del coordinator, invece di aspettare la fine della coverage sulla 6150. Ha
  anche approvato gli scatti della gallery che cambiano un poco.
