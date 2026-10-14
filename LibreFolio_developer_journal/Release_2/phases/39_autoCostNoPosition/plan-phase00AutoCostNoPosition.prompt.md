# Piano — P-1: costo Auto senza posizione

> Workstream **P**, lavoro per la 1.2. Coordinator: sessione `c8328a01-f208-4ade-a352-0486d1f14de2`. Voce **P-1** di
> [`38_postReleaseBacklog`](../../Phase_0/38_postReleaseBacklog/README.md) («Costo Auto senza posizione: costo 0
> salvato senza avviso»), nata dalla verifica d'archivio di [30_wacUnification](../../phases/30_wacUnification/plan-phase00WacUnification.prompt.md) (§9).
>
> **Stato: chiuso senza implementazione, per decisione del developer (09/10)**, vedi §10. Il codice resta com'è:
> Auto senza posizione salva 0 **per scelta**, e la correzione resta all'utente, sulla transazione. L'analisi di
> §1–§9 resta come motivazione. Archiviato in `Release_2/phases/39_autoCostNoPosition/` lo stesso giorno, senza
> passare dal repo in `Phase_0/`.
>
> Primo indirizzo del developer (09/10), testuale: «Si ma come avviene ora, se si entra e poi esce è da considerare
> che l'utente accetta lo 0». Lettura del coordinator: con la pool vuota Auto tratta il costo come **mancante**, con
> l'avviso che già esiste; se l'utente entra nel campo e ne esce senza scrivere, accetta lo 0 in modo esplicito; si
> riusa il flusso del costo mancante, senza inventarne uno nuovo. **Superato** dalla decisione finale di §10.
>
> Base: `dev_release2` @ `586a4f0ea` (treno 25), HEAD verificato uguale, worktree pulito. Corsia `--test-port 6161
> --data-dir /tmp/librefolio-r2-p`, mai usata: nessun test e nessun server. Cataloghi i18n, `ImportWizardModal` e
> `TransactionBulkModal` sono di **S**.

## 1. Stato verificato su `586a4f0ea`

Il treno 25 non tocca i file backend coinvolti. Le righe citate in P-1 valgono ancora.

### 1.1 Il difetto c'è ancora

- La facciata `compute_wac_iterative` dà un costo medio 0 quando non c'è posizione:
  - senza righe: `portfolio_service.py:185-190`, `Currency(asset_currency, 0)`;
  - con una pool svuotata dalle vendite: `CostStep.unit_cost_report` vale 0 se la quantità è 0
    (`financial_math/average_cost.py:155`).
- Auto lo scrive: `if wac_result.wac:` (`transaction_service.py:1012-1014`) è vero anche per un `Currency` di 0.
- La verifica del costo salta tutte le righe Auto (`transaction_batch_stages.py:889`, `:914`, `:935`).
- Uno 0 esplicito non accende `MISSING_COST_BASIS` (`ADD_ZERO_COST`, `average_cost.py:431-432`).
- **Auto è il default**:
  - nel form (`TransactionFormModal.svelte:340`, `:507`);
  - per le righe nuove del Bulk (`TransactionBulkModal.svelte:846`).

  Quindi un ADJUSTMENT in entrata con i valori di default, su un broker che non ha l'asset, si salva a costo 0. È il
  caso di una posizione d'apertura, di un regalo o della linea nuova di uno spin-off. La riga entra a costo zero e il
  suo valore diventa tutto guadagno.
- Per un TRANSFER la pool è quella del broker d'origine. Se è vuota, il controllo dei saldi rifiuta già la coppia, salvo
  quote d'origine a costo zero. Il caso tipico resta l'ADJUSTMENT.
- **v1.1.0**: identico. Verificato sul tag: la facciata (`portfolio_service.py:172-176`), la scrittura
  (`transaction_service.py:1673`) e Auto escluso dalla verifica (`:1461-1468`).

### 1.2 Il flusso del costo mancante, oggi

- **Backend**:
  - TRANSFER e ADJUSTMENT con quantità > 0 vogliono `cost_basis_override` (`transaction_service.py:157-165`);
  - senza, scatta `COST_BASIS_REQUIRED` (`transaction_batch_stages.py:878-946`). La forma è stabile
    (`_append_cost_basis_issue`, `:948-966`): codice `costBasisRequired`, campo `cost_basis_override`, params
    `{type}`;
  - qualunque issue blocca: `committed=False` (`finalize_response`, `:1013-1029`);
  - la regola esiste dal `0c4ff3e4e` (02/06). Due test lo dicono nei commenti (`test_tx_balance_walk.py:286`,
    `tx-delete.spec.ts:340`), ma **nessun test verifica il codice `costBasisRequired`**.
- **Form**:
  - con ADJUSTMENT in Manuale e il campo vuoto compare un avviso ambra sotto il campo:
    `transactions.costBasisOverride.warningAdjustment` (`TransactionFormModal.svelte:1947-1950`);
  - l'errore del backend compare nel banner (`:1418-1450`), con il testo di `transactions.errors.costBasisRequired`
    (`resolveValidationMessage.ts:222`): «❌ … requires a cost basis. Use **Auto** mode (WAC) or enter a **manual**
    value».
- **Bulk**:
  - la cella del costo è di sola lettura (`TransactionBulkModal.svelte:1797-1850`); in Auto senza valore mostra
    «💡 —»;
  - l'errore va nel banner della griglia.
- **Import**:
  - i plugin BRIM aprono un todo *blocker* sul costo. Esempi: `broker_generic_csv.py:443-457`, la linea nuova di una
    scissione in `broker_danske_bank.py:1566-1575`, e Crédit Agricole;
  - il todo si chiude con un valore **o con Auto** (`bulkTodos.ts:19-25`); finché è aperto, Save è disabilitato
    (`TransactionBulkModal.svelte:2176`, `:2189`).
  - Oggi è anche una via del difetto: Auto chiude il todo e, senza posizione, salva 0.

### 1.3 «Entrare nel campo e uscire» oggi non dà mai uno 0

- **Manuale**:
  - un blur sul campo vuoto emette `null` o `{amount: '', code}` (`CompactCashCell.svelte:89-103`);
  - il form lo normalizza a `null` (`TransactionFormModal.svelte:1008-1011`);
  - risultato: `costBasisRequired` e salvataggio rifiutato.
- **Auto**:
  - un blur senza modifiche lascia Auto e il valore (`WacPreviewSection.svelte:284-297`);
  - lo fissa l'E2E **W9** (`tx-wac-mode.spec.ts:119-151`).
  - Con la pool vuota quel valore è proprio lo 0: l'unico «entra ed esci = 0» che esiste oggi è il difetto stesso.
- **Lo 0 esplicito oggi**: Manuale, si scrive 0. La riga si salva, senza avvisi né `MISSING_COST_BASIS`.

### 1.4 Tre testi descrivono il comportamento di prima di giugno

Dicono «lotto a costo zero, con un avviso», ma dal `0c4ff3e4e` il codice rifiuta la riga:
- la chiave `warningAdjustment`: «No cost basis set — lot will be created with zero cost…». È nata il 15/05
  (`5e552ad9e`), prima della regola;
- la doc utente `user/transactions/form.en.md:39`: «An Adjustment without a cost basis creates its lot at zero cost,
  and the form warns you». È stata riscritta l'08/10 (`1c2f88d67`);
- la doc developer `developer/frontend/components/features/transaction-form.md:198-199`.

Probabilmente è da qui che viene il «come avviene ora» della decisione.

Rinviato: `Phase_0/38_postReleaseBacklog/README.md`, voce P-11 «Tre testi promettono un lotto a costo zero col costo
vuoto».

### 1.5 Altri chiamanti della facciata

- `POST /portfolio/wac` (`portfolio_api.py:125`). `test_portfolio_wac.py::test_a1_empty_pool` (`:130`) fissa la pool
  vuota = WAC 0.
- La PAC (`portfolio_allocation_source.py:1024`) legge `wac`, `wac_missing_pairs` e le righe qualificanti (`:1118`,
  `:1160-1163`).
- Il seed: `_seed_auto_cost_basis` rifiuta già Auto senza posizione (`populate_mock_data.py:185`).

### 1.6 Correzione a una mia affermazione dell'08/10

Avevo detto al developer che `MISSING_COST_BASIS` dall'app non può scattare. Una via c'è:
- si crea l'ADJUSTMENT +q legato a uno SPLIT, in Auto e quindi senza costo;
- poi si riclassifica l'evento da SPLIT a PRICE_ADJUSTMENT;
- la riga diventa un'acquisizione di costo sconosciuto. Lo fissa `test_portfolio_wac.py:521-588`.

Non è P-1 e non lo tocco. Rinviato: `Phase_0/38_postReleaseBacklog/README.md`, voce P-10 «`MISSING_COST_BASIS`
raggiungibile dall'app riclassificando uno SPLIT».

## 2. Progetto

> **Non eseguito**: il developer ha deciso di non farlo (§10). Resta come motivazione, con le opzioni che sono state
> valutate.

### 2.1 Lettura della decisione

- Auto senza posizione diventa un **costo mancante**, con lo stesso codice e lo stesso blocco di un costo vuoto.
- L'utente accetta lo 0 solo in modo esplicito: la riga salva `cost_basis_override` = 0, quindi `ADD_ZERO_COST`, e
  `MISSING_COST_BASIS` non scatta.
- **D1, da confermare**:
  - (a) la riga **resta bloccata** finché l'utente non dà un costo (0 compreso), come oggi nel codice;
  - (b) si salva a 0 con un avviso, come dicono i testi di §1.4.
  - **Consiglio (a)**: (b) è lo zero muto di oggi con una riga di testo in più, e contraddice la regola «mai più zeri
    silenziosi» del #32.

### 2.2 Backend (stessa forma dell'issue di oggi, nessuno schema nuovo, nessun `api sync`)

- **B1. Facciata**: `compute_wac_iterative(..., empty_pool_as_missing: bool = False)`.
  - Con `True` e la pool vuota alla data (nessuna riga, oppure quantità 0) rende `wac=None` senza coppie mancanti, e
    tiene le righe qualificanti.
  - Il controllo viene **prima** del fail-safe FX: senza posizione, una coppia mancante su acquisti già venduti
    sarebbe un falso allarme.
  - Il flag entra nella chiave di cache (`:176`).
  - Il default `False` lascia identici `POST /portfolio/wac` e la PAC: contratto e fingerprint di D non cambiano.
- **B2. Auto** (`_compute_wac_for_auto_items`):
  - passa `True`;
  - senza posizione toglie il costo dalla riga in stage, sia per le creazioni sia per gli aggiornamenti, così un
    aggiornamento non tiene un costo vecchio;
  - registra la riga (operazione, indice, `ref_id`, transazione) in un campo nuovo del contesto,
    `auto_rows_without_cost`.
  - Lo SPLIT (`:969-990`) e l'FX mancante (`WAC_FX_UNAVAILABLE`) restano come sono.
- **B3. Verifica del costo** (`validate_cost_basis`):
  - per quelle righe chiama `_append_cost_basis_issue`, con lo stesso codice, campo e `params.type`;
  - aggiunge `params.reason = "noPosition"`; per le issue di oggi il parametro resta assente;
  - le altre righe Auto restano escluse come oggi.
  - Il WAC gira solo senza altre issue (`:803`), come oggi per l'FX: l'avviso arriva al primo giro pulito.

### 2.3 Frontend

- **F0, nessun cambio necessario per la correttezza.**
  - Form e Bulk mostrano già `costBasisRequired` sulla riga, e il salvataggio è rifiutato.
  - L'utente passa a Manuale e scrive il costo, anche 0.
- **F1, il gesto: entrare nel campo vuoto e uscirne = 0 esplicito.** Oggi non esiste (§1.3): è codice nuovo.
  - `WacPreviewSection.svelte` riceve una prop nuova.
  - Il form (`TransactionFormModal.svelte`) gliela passa, alle 3 istanze, quando la riga ha `costBasisRequired`.
  - All'uscita dal campo importo, se è vuoto e il fuoco non va al selettore della valuta, il componente imposta
    Manuale con importo `0`.
  - Nello stato segnalato il form mostra il campo vuoto, non un WAC vecchio (`displayedCostBasis`).
  - **W9 resta valido**: il gesto agisce solo con il campo vuoto e la riga segnalata.
  - **D2, ambito**:
    - (a) Auto senza posizione **e** Manuale vuoto: una regola sola, e il «come oggi» della decisione diventa vero;
    - (b) solo Auto senza posizione;
    - (c) nessun gesto: lo 0 si scrive.
    - **Consiglio (a)**.
    - Rischio, da accettare in modo esplicito: col tasto Tab attraverso il campo l'utente accetta lo 0 senza
      accorgersene.
- **F2, il messaggio.** Il testo di `costBasisRequired` dice «Use **Auto** mode (WAC)», che qui è proprio ciò che non
  funziona.
  - **D3**:
    - (a) tenere il testo di oggi: zero chiavi;
    - (b) una chiave nuova di S, `transactions.errors.costBasisNoPosition`, scelta da `resolveValidationMessage.ts`
      quando `params.reason = "noPosition"`. Va anche registrata nel gate `htmlInterpolation.gate.test.ts:933`.
  - **Consiglio (b)**, non bloccante: la correzione funziona anche con (a).
  - Bozza EN: «❌ <b>{type}</b>: there is no position to take the average cost from, so <b>Auto</b> cannot set it.
    Enter a <b>manual</b> cost — 0 if the units cost nothing.»
  - Bozza IT: «❌ <b>{type}</b>: non c'è una posizione da cui prendere il costo medio, quindi <b>Auto</b> non può
    impostarlo. Inserisci un costo <b>manuale</b> — 0 se le quote non sono costate nulla.»
  - FR e ES li scrive S.
  - Facoltativo, per S: riformulare `warningAdjustment`, che oggi promette un lotto a costo zero.
- **Non servono** `TransactionBulkModal` e `ImportWizardModal`.
  - Solo se un E2E lo mostra: nella cella del Bulk, un valore Auto vecchio resta visibile quando una validazione
    successiva non dà WAC. Il caso esiste già oggi con l'FX mancante; se emerge, lo chiedo a S.

### 2.4 Documentazione (`docs-writer`, solo EN)

- `developer/backend/transactions/wac.md`, §Inline Batch Auto Modes (`:428-460`): pool vuota → nessun costo e
  `costBasisRequired`; il flag della facciata. Il passo 4 della facciata (`:366-367`, WAC 0) resta vero per
  `/portfolio/wac`.
- `developer/frontend/components/features/transaction-form.md:198-199` e `user/transactions/form.en.md:39`:
  allineare la frase superata al comportamento vero, col gesto se D2 ≠ (c).
- Le pagine utente hanno traduzioni. Lascio il debito senza stamp, salvo che il developer chieda la correzione diretta
  delle 4 lingue, che è piccola.

## 3. Superfici

| File | Cambio | Proprietario |
|---|---|---|
| `backend/app/services/portfolio_service.py` | flag `empty_pool_as_missing`, chiave di cache | P (#32) |
| `backend/app/services/transaction_service.py` | `_compute_wac_for_auto_items` (B2) | ex L (SP16, chiuso): conferma del coordinator |
| `backend/app/services/transaction_batch_context.py` | campo `auto_rows_without_cost` | idem |
| `backend/app/services/transaction_batch_stages.py` | B3; `reason` facoltativo in `_append_cost_basis_issue` | idem |
| `frontend/src/lib/components/transactions/wac/WacPreviewSection.svelte` | F1 | da confermare |
| `frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte` | F1: flag e campo vuoto | da confermare |
| `frontend/src/lib/utils/transactions/resolveValidationMessage.ts` | F2, solo con D3 = (b) | da confermare |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | 1 chiave (D3 = (b)); `warningAdjustment` facoltativa | **S** |
| doc §2.4 | allineamento | `docs-writer` |
| test §4 | rossi e adattamenti | `test-author` |

## 4. Test (rossi prima, `test-author`, solo file registrati)

> **Non scritti**: decisione del 09/10 (§10). In particolare P27 (`test_wac_inline.py:497-519`, «empty pool → WAC 0»)
> resta com'è: ora fissa il comportamento voluto, non un difetto.

- **`api transactions-wac`** (`test_wac_inline.py`):
  - **NP1**: validate di un ADJUSTMENT +5 Auto, broker senza posizione → `wac` null, nessuna coppia, un
    `costBasisRequired` (create, indice, campo `cost_basis_override`, `reason` `noPosition`). Rosso oggi: WAC 0,
    nessuna issue.
  - **NP2**: commit dello stesso → `committed` false, niente salvato. Rosso oggi: salvato a 0.
  - **NP3**: pool svuotata da una SELL totale prima della data → come NP1. Rosso oggi.
  - **NP4**: update di un ADJUSTMENT esistente in Auto senza posizione → issue, e il costo salvato non cambia.
    Rosso oggi.
  - **NP5**: 0 manuale esplicito su pool vuota → commit OK, costo 0, nessuna issue. Verde prima e dopo.
  - **P27** (`:497-519`) oggi fissa il difetto («empty pool → WAC 0»): va riscritto. Ricevente Auto con la pool
    d'origine vuota → `wac` null e `costBasisRequired` sul ricevente.
- **Invarianti verdi prima e dopo**:
  - `api portfolio-wac` A1, la pool vuota = 0 per l'API;
  - lo SPLIT in Auto (`test_portfolio_wac.py:438-588`, `api batch-split-promote`);
  - P16–P29;
  - la suite PAC.
- **Frontend**, solo con F1:
  - `WacPreviewSection.test.ts` (`front-utility component-unit`):
    - G1: riga segnalata + Auto + campo vuoto, blur → `onModeChange('manual')` + `{code, amount: '0'}`;
    - G2: riga non segnalata + Auto con valore, blur → nulla (W9 in unità);
    - G3: riga segnalata, l'utente scrive un valore → Manuale con quel valore;
    - G4: Manuale vuoto segnalato, blur → `0`, solo con D2 = (a);
    - G5: fuoco verso il selettore della valuta → nessuno 0.
  - E2E `tx-wac-mode.spec.ts`, **W12**, write-safe:
    - broker e asset propri, creati via API;
    - ADJUSTMENT +q Auto → l'issue compare → entra ed esci dal campo → Manuale 0 → commit → costo 0 → pulizia.
    - Rosso oggi: nessuna issue.
    - **W9** deve restare verde.
- **Da adattare se diventano rossi**: `tx-commit-all-types.spec.ts:407`. L'ADJUSTMENT usa il primo broker e il primo
  asset del seed, in Auto: se quel broker non ha l'asset, dopo la correzione è bloccato. Lo verifico con un giro prima
  della correzione.

## 5. Gate (corsia 6161, un comando alla volta)

> **Non eseguiti**: nessun codice cambia (§10).

- **Backend**:
  - `api transactions-wac`, `api portfolio-wac`, `api batch-split-promote`, `api transactions`, `api brokers`,
    `api tx-balance-walk`;
  - `services transaction`, `services portfolio-allocation-source`.
- **Frontend**:
  - `front check`, `front-utility component-unit`;
  - E2E `front-transaction`: `tx-wac-mode`, `tx-wac-formmodal`, `tx-wac`, `tx-wac-bulk`, `tx-commit-all-types`,
    `tx-bulk-import-handoff`.
- **Doc**: `mkdocs build`, `check-links`.
- **Chiusura**: ruff e black, prettier, `git diff --check`, porta libera.

## 6. Rischi

1. **API**: `cost_basis_mode: auto` senza posizione ora è rifiutato. Prima passava a 0, quindi gli script che ci
   contavano ricevono `costBasisRequired`. Va nel CHANGELOG.
2. **E2E che dipendono dal seed**: §4, `tx-commit-all-types:407`.
3. **Tab** attraverso il campo = 0 accettato (F1): è nella decisione, va solo saputo.
4. **W9**: protetto dalla condizione «campo vuoto e riga segnalata».
5. **Valore Auto vecchio nella cella del Bulk**: caso marginale che esiste già, file di S (§2.3).
6. **Import**: Auto «risponde» ancora al todo del costo (`bulkTodos.ts:22`), ma ora il salvataggio è bloccato
   dall'issue e il banner spiega perché. Nessun cambio proposto.
7. **Pool con costi sconosciuti** (scritti nel DB, oppure lo SPLIT riclassificato di §1.6): Auto dà un WAC che conta
   quei costi a zero. Fuori dallo scope; si estende allo stesso modo se il developer vuole.
8. **Stessa richiesta**: il costo tolto a una riga senza posizione cambia l'anteprima delle righe Auto successive nella
   stessa richiesta. Il batch è comunque rifiutato.

## 7. CHANGELOG (`[1.2.0]`, 🐛 Fixed → «📥 Imports and transaction editing»; c'era già nella v1.1.0)

> **Nessuna riga**: il comportamento non cambia (§10). La bozza sotto resta solo come traccia di ciò che era stato
> proposto.

> - **Auto cost basis no longer saves 0 when there is nothing to average.** An adjustment or transfer that adds shares
>   in *Auto* mode, on a broker that held none of that asset on that date, was saved at a cost of 0 without a word, so
>   its whole value counted as gain. It now counts as a missing cost basis, like an empty field: the transaction asks
>   for a cost before it can be saved, and clicking into the empty field and leaving it records 0 on purpose. Through
>   the API, such a row now returns the `costBasisRequired` issue.

Con D2 = (c), l'ultima frase diventa: «enter 0 for a gift or a split».

## 8. Passi

- **Q0** ✅ (09/10): analisi e questo piano, mandati al coordinator. FROZEN.
- **Q1–Q6**: non eseguiti. Il 09/10 il developer ha deciso di non farlo (§10). Nessun test, nessun server, nessun
  codice.
- **Q7** ✅ (09/10): chiusura per decisione.
  > **Note implementazione**:
  > - la decisione testuale è in §10; i punti superati sono segnati in §2, §4, §5, §7 e §9;
  > - i due reperti dell'analisi passano al 38 come P-10 e P-11, con i rimandi in §1.4 e §1.6;
  > - la nota per il wiki va al coordinator, che la registra;
  > - la cartella è passata intera da `Phase_0/39_autoCostNoPosition/` a `phases/39_autoCostNoPosition/`. Il file non
  >   era mai stato committato, quindi nel repo nasce direttamente lì; il link al 38 è stato riscritto per la nuova
  >   profondità.

## 9. Definizione di fatto

> **Superata** dalla decisione di §10. Vale invece: il codice non cambia; la decisione è scritta con la data; i
> reperti sono nel 38; la cartella è archiviata intera.

- Auto senza posizione non scrive mai 0: validate e commit danno `costBasisRequired` sulla riga, e nulla si salva.
- Lo 0 esplicito (scritto, o col gesto se approvato) salva costo 0, senza `MISSING_COST_BASIS`.
- Restano come prima:
  - Auto con posizione, lo SPLIT e l'FX mancante;
  - `POST /portfolio/wac` e la PAC (A1 e suite PAC verdi);
  - W9.
- Rossi visti rossi, poi verdi; gate verdi; doc allineata; riga del CHANGELOG pronta; porta 6161 libera; FROZEN.

## 10. Decisione e chiusura (09/10)

**Decisione del developer** (09/10), inoltrata dal coordinator, testuale:

> «no chat, non facciamolo e segnamo la decisione, se i dati mancano lo 0 come fallback per auto è corretto. se
> bisogna cambiare sarà l'utente ad andare su quella transazione e correggere.»

Cosa vuol dire:
- **Nessuna implementazione.** In Auto, se la pool d'origine è vuota alla data della riga, il costo per unità è 0
  **per scelta**: è il ripiego corretto quando mancano i dati.
- Se il costo vero è diverso, l'utente apre quella transazione e lo corregge (Manuale). Il rimedio è suo, non
  dell'app.
- Restano come oggi, senza cambi:
  - la facciata (`portfolio_service.py:185-190`) e la scrittura di Auto (`transaction_service.py:1012-1014`);
  - la verifica del costo, che salta le righe Auto (`transaction_batch_stages.py:889`, `:914`, `:935`);
  - `test_wac_inline.py::test_wacp27_empty_pool_wac_zero`, che ora fissa il comportamento voluto.
- Le decisioni D1–D3 di §2 e la bozza del CHANGELOG di §7 decadono.

**Residui**, passati al 38:
- rinviato: `Phase_0/38_postReleaseBacklog/README.md`, voce P-10 «`MISSING_COST_BASIS` raggiungibile dall'app
  riclassificando uno SPLIT»;
- rinviato: `Phase_0/38_postReleaseBacklog/README.md`, voce P-11 «Tre testi promettono un lotto a costo zero col costo
  vuoto».

La voce P-1 del 38 la chiude il coordinator, per decisione. Anche la nota nel wiki la registra lui.

**Esito**: FINITA per decisione, archiviata intera in `Release_2/phases/39_autoCostNoPosition/`.
