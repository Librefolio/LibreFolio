# Plan W2 · Il form delle transazioni (ondata 5, 1.3.0)

Link: piano di W [`plan-phase01ImportTransactions.prompt.md`](plan-phase01ImportTransactions.prompt.md) (non lo tocco: un solo scrittore per file).
Riferimenti: `PROSSIMI_LAVORI.md:129-143` (V-37b), `:567-580` (#47); backlog V-37b ~2104; analisi K3 punto 7 nel piano di W.

- **Worktree**: `/home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio-worktrees/e-alfy-w2-form`
- **Ramo**: `e-alfy-w2-form-transazioni` (da `dev_release2`)
- **HEAD di partenza**: `1fd80c481d2e2bd0c0b5e07cf27984681a88e839` (= `dev_release2`, verificato 23/10/2026)
- **Corsia**: porta `6194`, dati `/tmp/librefolio-r13-w2`. Sessione coordinatore: sotto-agente del coordinatore di release.
- Treni: V-37b → 11a; #47 → 11b (dopo il commit di V-37b).

## Analisi V-37b (stato reale, 23/10/2026)

- Il pulsante ⚡ è `disabled={!isFormComplete}` (`TransactionFormModal.svelte:1594`). `validateNow` (`:1131`) salta il server
  solo se `hasLocalErrors` (errori di formato: segno, cifre, data digitata rifiutata, stessa valuta/broker) e porta il fuoco al
  primo errore con `focusFirstLocalError` (`:1117`, lista di selettori fissa).
- I campi obbligatori mancanti (`isFormComplete`: data, broker, asset se richiesto, cassa se richiesta e ≠ 0, quantità ≠ 0,
  lato «To» della coppia, due importi FX ≠ 0) **non hanno alcun segno rosso**: il pulsante resta spento e basta.
- Formato: la quantità, la data digitata e le cifre della cassa sono già rosse da sole (ognuna col suo componente); mancano il
  segno rosso sui campi obbligatori vuoti e un solo punto che dica «quali celle» in ordine di schermo.
- Tre asserzioni E2E di `tx-fx-completeness.spec.ts` (`:267`, `:367`, `:393`) dicono «⚡ disabilitato»: cambiano.
- Nessun componente condiviso va toccato: il rosso dei campi obbligatori vuoti è un anello sul contenitore della cella
  (`ring-lf-danger`, solo ruoli), non una proprietà nuova di `SingleDatePicker`/`SearchSelect`.

### Disegno
1. **Helper puro** `form/txFormChecks.ts` → `computeTxFormChecks(input): TxFormCheck[]` (fase 1 obbligatori, fase 2 formato; una
   voce per cella, l'obbligatorio vince). Celle: `date, dateTo, quantity, cash, cashTo, asset, broker, brokerTo`.
2. `TransactionFormModal.svelte`: `checksArmed` (si arma al clic su ⚡, si spegne all'apertura e al reset); ⚡ sempre
   cliccabile (non in sola lettura); `validateNow`: arma, se ci sono voci → fuoco alla prima **in ordine di schermo** (DOM:
   `[data-cell-invalid]`), nessuna chiamata; altrimenti `scheduler.trigger('manual')`. `hasLocalErrors` = voci di formato
   dell'helper (stessa semantica di oggi). Il rosso sparisce da solo man mano che il campo si corregge.
3. Sezioni (`TxFormSingleSection`, `TxFormPairSection`): ogni cella con `data-cell` + `data-cell-invalid`.
4. i18n: `transactions.validate.checkSummary`, `transactions.validate.requiredHint`.
5. Doc `user/transactions/form.en.md`; spec E2E.

### Scelta da confermare (non blocca)
«Fuoco sulla prima»: scelgo la prima **in ordine di schermo** (come V-37 oggi), non «prima gli obbligatori». Esempio: Qty vuota +
data «abc» → fuoco sulla data (sta sopra la quantità). Se il developer vuole gli obbligatori per primi, è un cambio di una riga.

## Passi

### V-37b

- ✅ **1. Rossi** (23/10/2026, `test-author`, Sonnet). Stub dell'helper (`[]`), poi: `txFormChecks.test.ts` (73 test, 61 rossi sul motivo giusto),
  `TransactionFormModal.checks.test.ts` (7 test, 7 rossi), `tx-fx-completeness.spec.ts` (3 asserzioni «⚡ disabilitato» → abilitato +
  marcature, 1 test nuovo «single form (V-37b)»: quantità vuota + data «abc», nessuna richiesta a `/transactions/validate`; non girato, serve slot).
  > **Note implementazione**: log in `salvataggi-worktrees-20261021/ondata5/W2-checks-*.log`. L'autore ha provato i 73 contro un'implementazione
  > di riferimento usa-e-getta (73/73) e l'ha cancellata.
- ✅ **2. Cura** (23/10/2026). `form/txFormChecks.ts` (helper puro), `form/TxCellMark.svelte` (contenitore di cella: `data-cell`,
  `data-cell-invalid`, anello `ring-lf-danger` solo per «required»), `TransactionFormModal.svelte` (`formChecks`, `checksArmed`,
  `markedCells`, contatore `tx-form-check-summary`, ⚡ senza `disabled`, `focusFirstMarkedCell` al posto di `focusFirstLocalError`;
  `hasLocalErrors` ora = voci «format» dell'helper; tolti `cashSignResult`, `hasSignViolation`, `cashOverSignificant`…, ora dentro l'helper),
  `TxFormSingleSection.svelte`/`TxFormPairSection.svelte` (celle avvolte, nuova prop `markedCells`), i18n `transactions.validate.checkSummary` (4 lingue).
  > **Note implementazione**: `isFormComplete` NON toccato (gate del salvataggio e del validatore automatico); l'equivalenza «nessun required ⇔
  > isDraftReadyForValidation» è fissata da un test dell'helper. Vitest `form/`: 7 file, 186 verdi. i18n check 0. Gate colori 101 verdi.
- ✅ **3. Doc** (23/10/2026, `docs-writer`): `form.en.md`, nuova sezione «⚡ Validate now» + punto «Checks as you go». Traduzioni it/fr/es = debito.
- ✅ **4. Prove** (23/10/2026): `front check` (flock) 0 errori 0 avvisi (`W2-front-check.log`); prettier pulito; `git diff --check` pulito.
  Vitest `form/`: 186 verdi (73 helper + 7 componente + 106 preesistenti). **Non fatti, serve slot**: E2E `front-transaction form`/`modals` e
  `tx-fx-completeness.spec.ts` (scritto, mai girato), `mkdocs build` + `check-links`.
  > **⚠️ Fuori pista**: il primo `front check` ha atteso ~10 min il lucchetto pesante (altre sessioni).
- ✅ **5. E2E, doc build** (23/10/2026, sotto `flock`, corsia 6194): `tx-fx-completeness` 5/5, `tx-wac-fx`, `tx-wac-mode` verdi, `mkdocs build` rc=0, `check-links` rc=0.
  `transactions-modals`: 23 verdi e **2 rossi** (`a refused typed date blocks the form`, futura e «non è una data»): dopo ⚡ il fuoco non era nel campo data.
  > **⚠️ Fuori pista**: causa = `focusFirstMarkedCell` prendeva il primo controllo della cella, che nel date picker è il pulsante del calendario, prima del campo
  > di testo. Cura: prima `input`/`combobox`, il pulsante solo se non c'è altro. Rilanciati `transactions-modals` e `tx-fx-completeness`: rc=0 entrambi.
  > Anche nello spec `transactions-modals` due messaggi di asserzione («disabled only by an incomplete form») aggiornati: ⚡ ora è sempre abilitato.

## #47 · Importo totale / Prezzo unitario (11b) — analisi (23/10/2026, base `479f57872` = commit di V-37b)

**Dove si applica.** Solo BUY e SELL hanno quantità **e** cassa obbligatorie (`schemas/transactions/type_metadata.py:177-193`). ADJUSTMENT/TRANSFER hanno la cassa vietata, FX e i trasferimenti di cassa non hanno quantità, dividendo/interesse/spese non hanno quantità. Quindi la **coppia non è interessata**: il selettore vive solo nella sezione singola di BUY/SELL (`TxFormSingleSection.svelte`, il ramo «quantità + cassa»).

**Il calcolo esiste in `financial_math/`? No, non per questo uso.**
- `valuation.compute_holding_value(qty, raw_price, quote_base_quantity)` = `(qty / base) × raw_price`, `Decimal`, senza arrotondamento: è il valore di mercato di una posizione (il lato «prezzo → importo» ci somiglia, ma non c'è il lato inverso né l'arrotondamento alle colonne).
- Nessuna funzione per «importo ÷ quantità → prezzo». `average_cost.movement_unit_costs` è il costo medio di un movimento, altra cosa.
- Il frontend **non** ha `quote_base_quantity` dell'asset (non è nell'`assetStore`) e non può calcolare (regola 6 di `financial-math.instructions.md`).
- `financial_math/**` è di MF e `api/v1/transactions.py` non ha un endpoint di conversione.

**Regola dei decimali già in uso (W-B64/N63, `db/precision.py`)**: importo ≤ 6 decimali, ≤ 15 cifre significative, ≤ 15 intere; quantità ≤ 10 decimali; prezzo ≤ 12 decimali. È un **limite di ingresso, mai un arrotondamento** (`decimal_limit_issue`). `Transaction` non ha il prezzo: salva solo `quantity` e `amount`. Il prezzo unitario è quindi solo un modo di digitare; l'importo è ciò che si salva.

**Decisioni chieste (bloccano il calcolo, non il resto)** — vedi il messaggio al coordinatore: D1 dove vive il calcolo; D2 `quote_base_quantity`; D3 arrotondamento del valore calcolato; D4 selettore nella modifica multipla.

### #47 — decisioni del coordinatore (23/10/2026, «decise da lui», il developer può cambiarle)
- **D1** endpoint backend: funzione pura in **file nuovo** `financial_math/trade_amount.py` (MF la rivede), riga nelle mappe, test unitari; poi schema, rotta in `api/v1/transactions.py` (due modi), `api sync`. Il form la interroga con un breve ritardo e non calcola mai.
- **D2** convenzione dell'app `qty / quote_base_quantity × prezzo`, letta dall'asset nel backend; `compute_holding_value` riusato per prezzo→importo.
- **D3** half-even alle scale delle colonne: importo 6 decimali, prezzo 12; oltre i limiti d'ingresso resta rosso come oggi.
- **D4** niente selettore nel Bulk (di W): voce di backlog.

### #47 — disegno (mio)
- Solo BUY/SELL singola (`quantityMode≠forbidden`, `cashField≠forbidden`, asset non vietato, niente coppia).
- Backend: `POST /api/v1/transactions/trade-amount` body `{asset_id, quantity, mode: price_to_amount|amount_to_price, value}`; risposta `{mode, result, quote_base_quantity}`, `result` = decimale piano, senza esponente né zeri finali. 404 asset ignoto, 422 quantità zero o valori oltre i limiti d'ingresso.
- Frontend: selettore a badge `tx-form-entry-mode` (due bottoni, `aria-pressed`); campo prezzo `tx-form-unit-price`; il prezzo calcolato in modalità importo `tx-form-unit-price-computed`; `driver` = ultimo valore scritto (`txTradeAmount.ts`), l'altro si calcola dal backend (`txTradeAmountApi.ts`), mai a mano. Il prezzo è nella valuta della cassa (il backend ignora la valuta).

### #47 — passi
- ✅ **1. Rossi** (23/10/2026, due `test-author`): backend `test_trade_amount.py` (54 test, rossi per `NotImplementedError`), 32 test API in `test_transactions_api.py` (rossi per 405: rotta assente), frontend `txTradeAmount.test.ts` (62; 14 rossi), `TransactionFormModal.entryMode.test.ts` (25; 22 rossi), un E2E in `transactions-modals.spec.ts` (non girato).
- ✅ **2. Cura backend** (23/10/2026): `financial_math/trade_amount.py` (`amount_from_unit_price`, `unit_price_from_amount`; `compute_holding_value` riusato, half-even in `localcontext` a 80 cifre), `schemas/transactions/trade_amount.py` (richiesta con limiti d'ingresso `decimal_limit_issue`, quantità ≠ 0), `services/transactions/trade_amount.py` (legge `quote_base_quantity` dell'asset, scale 6 e 12 dalle colonne), rotta `POST /transactions/trade-amount` (404 asset ignoto), mappe in `financial_math/__init__.py`, `financial-math.instructions.md`, `backend.instructions.md`, `developer/backend/financial_math.md`. Unit 54/54 (pytest diretto, funzione pura). `ruff` e `black` puliti.
- ✅ **3. `api sync`** (generated.ts ignorato da git): alias `trade_amount_api_v1_transactions_trade_amount_post`.
- ✅ **4. Cura frontend** (23/10/2026): `txTradeAmount.ts` (driver e piano della richiesta), `txTradeAmountApi.ts` (trySave, mai eccezioni, `null` su rifiuto), `TxTradePriceRow.svelte` (badge `tx-form-entry-mode`, prezzo digitato o calcolato), stato nel form (`tradeEntryMode`, `tradeDriver`, `unitPrice`, effetto con attesa di 250 ms e numero di sequenza contro le risposte vecchie), i18n 4 chiavi (`transactions.form.entryModeAmount|entryModeUnitPrice|unitPriceCalculated|unitPriceHint`). Vitest `form/` + gate colori: 374/374.
  > **Note implementazione**: il badge segue il driver (un importo digitato in modalità prezzo riporta il badge su «Importo totale»); la valuta del prezzo è quella della cassa (il backend ignora la valuta). `unitPrice` non entra nel payload. Il robustezza: `convertTradeAmount` risponde `null` se la risposta non ha `result` (prima un test vecchio con `zodiosApi` finto dava un'eccezione non gestita).
- ✅ **5. Doc** (`docs-writer`): `form.en.md`, regola «Amounts are totals» e sezione «🧮 Total amount or unit price». Traduzioni = debito.
- ✅ **6. Backlog**: nuova sezione «W2» in `BACKLOG_POST_1.2.md` con W2-1 (selettore nel Bulk, D4).
- ✅ **7. Prove finali #47** (23/10/2026, sotto `flock`, corsia 6194): unit 54/54, API `trade_amount` 32/32, `services financial-math` 2545/2545, Vitest `form/` + gate colori 374/374, Vitest `email/` + `plugin-settings/pluginSettingsApi` 1005/1005, E2E `transactions-modals` 26/26, `tx-fx-completeness` 5/5, `tx-wac-fx` 9/9, `tx-wac-mode` 5/5, `tx-wac-formmodal` 10/10, `front check` 0/0, `i18n check` ok, `mkdocs build` rc=0, `check-links` 97 validi.
  > **⚠️ Fuori pista (1)**: il primo E2E di `transactions-modals` è andato rosso (importo 0): `ExactDecimalInput.onchange` passa il testo grezzo (`83,40`), non quello normalizzato; il piano della richiesta si aspettava un decimale canonico. Cura: `normalizeDecimalInput(unitPrice)` nel calcolo della richiesta, il campo mostra ciò che l'utente scrive.
  > **⚠️ Fuori pista (2)**: `front check` rosso fuori dal mio perimetro: «Type instantiation is excessively deep» in `email/emailApi.test.ts` (poi `forgotPasswordApi.test.ts`…). Causa: con un endpoint in più il tipo del client Zodios supera la profondità di TS e l'errore cade sul primo `vi.spyOn(zodiosApi, …)` controllato, poi si sposta sul successivo. Cura: helper `src/__tests__/spyOnApi.ts` (vista a una chiave del client) e 5 file di test dell'email/plugin-settings passati a `spyOnApi` (modifica meccanica, solo tipi). Resta valida per ogni futuro endpoint.
