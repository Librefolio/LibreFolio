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
