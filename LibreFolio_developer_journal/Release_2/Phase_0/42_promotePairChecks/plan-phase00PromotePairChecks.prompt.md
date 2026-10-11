# Piano — 42: i controlli delle coppie promosse

> Workstream **P**, lotto per la 1.2. Coordinator: sessione `c8328a01-f208-4ade-a352-0486d1f14de2`.
>
> **Origine.** Reperti del test-author di S, tracciati nel codice ma non riprodotti; il coordinator ne aggiunge uno
> trovato da S e confermato dal suo E2E. Il mandato: prima i test rossi e un'analisi breve, poi la correzione dopo il
> via.
>
> **Base**: worktree a `fa109eaa7`, cioè `fbb57eb41` più l'archivio della 40, pulita. Nel frattempo `dev_release2` è
> andato a `e32f47133` (treno 29: traduzioni, pipeline e journal, nessun file mio). Corsia `--test-port 6161 --data-dir
> /tmp/librefolio-r2-p`, un comando alla volta.
>
> **Base aggiornata**: `f4a42bf4a` (treno 31, 10/10, coi file del passo 1 intatti), poi `01b967c56`, il commit di
> DistributionEditor (11/10). Al checkpoint `dev_release2` è a `b20eac991` (treno 32, che non tocca file del lotto).
>
> **Superfici.**
> - Mie: `transaction_service.py` (`_validate_linked_pair`), `transaction_batch_stages.py` (`apply_promotes`),
>   `frontend/src/lib/stores/transactions/transactionTypeStore.ts` e
>   `frontend/src/lib/utils/transactions/txPayloadHelpers.ts`.
> - Di S: `TransactionBulkModal.svelte` (S fa il filtro del banner «Unisci tutti») e i cataloghi i18n.
> - Di I: `portfolio_engine.py` (lotto 41).
>
> **Stato: Q0 (rossi e analisi) consegnato il 10/10. Via il 10/10, passo 1 in corso.**
>
> **Decisioni** (coordinator, 10/10, sulle raccomandazioni di P; il developer aveva già detto che un difetto confermato
> da un rosso entra nella 1.2):
> - **D1 = (a)**: solo TRANSFER, con `pairAssetMismatch` e `pairQuantityMismatch` (opposte esatte, in Decimal). Il
>   resto dei `pair_field_constraints` (CASH_TRANSFER, FX) va nel backlog 38 come C-42, e lo scrive il coordinator.
> - **D2 = rifiutare**: `eventTypeIncompatible` sull'operazione `promote` con `ref_id`; il promote non si applica e
>   `asset_event_id` non si azzera.
> - **Due tempi**, per non scrivere nei file di S prima che S sia dentro:
>   - **passo 1** (subito):
>     - 2.1 e 2.2 nel backend, che per ora manda il messaggio inglese;
>     - 2.3 in `transactionTypeStore.ts`, con il test nuovo `transactionTypeStore.test.ts`;
>     - 2.4 `fieldEq`;
>     - `routes/(app)/transactions/+page.svelte`, solo per `eventA`/`eventB`;
>   - **passo 2** (dopo il treno 30 e il merge del target nel ramo):
>     - `buildPromoteCtx` in `TransactionBulkModal.svelte`, solo `eventA`/`eventB`;
>     - la registrazione di `transactionTypeStore.test.ts` in `front_tx_unit`;
>     - le chiavi `pairQuantityMismatch` e `pairAssetMismatch` nelle 4 lingue, FR ed ES comprese;
>     - 2.5 (reperto di S): `cashAmountsCancel` (`promoteHelpers.ts:39-47`) usa `Number` con tolleranza 1e-9, e va
>       rifatto come `assetQuantitiesCancel` di S (`exactDecimalSign`/`exactDecimalEqual`).

## 1. Reperti verificati, con i rossi

Tutti i rossi sono scritti dal test-author. I log sono in `/tmp/libreFolio_p42_reds_*.log`.

### 1.1 Coppie TRANSFER con quantità che non si annullano, o con asset diversi — CONFERMATO (grave)
- `_validate_linked_pair` (`transaction_service.py:166-198`) controlla solo che il tipo sia lo stesso e, per TRANSFER e
  CASH_TRANSFER, che i broker siano diversi.
- Eppure i metadati del tipo dichiarano i vincoli della coppia: per TRANSFER asset uguale, broker diverso, quantità
  opposta (`schemas/transactions.py:1217-1221`). Nel backend li usa solo il promote (`_check_promote_constraints`,
  `transaction_service.py:748-779`).
- Quando l'editor promuove due righe **nuove**, lo fa in locale: dà a entrambe il tipo TRANSFER e un `link_uuid`
  comune. Il backend riceve quindi una coppia TRANSFER creata, e la accetta.
- **R42a** (`test_transactions_batch_split_promote.py:1141-1201`): −3 su A, +5 su B → committato. B guadagna 5 quote, A
  ne perde 3: 2 quote nascono dal nulla.
- **R42b** (`:1203-1259`): asset X in uscita da A, asset Y in entrata su B → committato.
- Lo stesso vale per una coppia TRANSFER creata via API.
- **G42** (`:1359-1426`, verde): per un promote di una riga salvata e di una nuova, il backend rifiuta già −3/+5 con
  `noPromoteRule`.
- **L'editor però lo propone**: `findPromoteMatch` (`transactionTypeStore.ts:352-357`) confronta solo i segni
  (`qA > 0 && qB < 0`). L'asset invece lo confronta già, quando ci sono entrambi.

### 1.2 Il promote lascia `asset_event_id` — CONFERMATO
- `apply_promotes` (`transaction_batch_stages.py:552-606`) cambia il tipo e collega le righe. Non tocca né valida
  `asset_event_id`, quindi un ADJUSTMENT legato a uno SPLIT diventa un TRANSFER legato a quello SPLIT.
- La regola 9 vieta proprio questo: `eventTypeIncompatible`, perché solo DIVIDEND, INTEREST e ADJUSTMENT si possono
  legare a un evento (`schemas/transactions.py:46-56`, `:150-162`).
- Il costo medio tratta una riga legata a uno SPLIT come un frazionamento
  (`cost_movement_from_transaction(split_linked=True)`).
- **R42c** (`:1261-1357`): promote di un ADJUSTMENT −10 salvato e di un ADJUSTMENT +10 legato a uno SPLIT, con costo
  manuale → committato. Risultato: un TRANSFER con `asset_event_id`.
- **Nota del test-author.** Con la riga dello SPLIT in Auto, oggi il promote è già rifiutato, ma **per caso**: Auto non
  scrive il costo su una riga di SPLIT, e il controllo dei promote del lotto 40 lo chiede (`costBasisRequired`). Con un
  costo manuale invece passa.

### 1.3 `fieldEq` confronta i costi per riferimento — CONFERMATO
- In `txPayloadHelpers.ts:204-205` il ramo di `cost_basis_override` fa `(a || '') === (b || '')` su oggetti
  `{code, amount}`, quindi due costi uguali risultano sempre diversi. Lo usano `buildUpdateDiff` (`:285-287`) e
  `diffDualItem` (`:339-343`). C'è dal `7f1a6ed39` (05/05).
- **Rossi unitari** (`txPayloadHelpers.test.ts`, `front-transaction tx-unit`): 8 su 14 nuovi.
  - `fieldEq` dà falso per uguali per valore (`'10'` e `'10.000000'`, o una copia), e per un importo vuoto o di spazi
    contro `null`.
  - `buildUpdateDiff` e `diffDualItem` mandano un `cost_basis_override` uguale.
- **E2E rosso WB11** (`tx-wac-bulk.spec.ts:666-856`): due righe salvate con costo manuale, Bulk aperto senza toccare
  nulla.
  - «Salva» (`tx-bulk-commit`) è **attivo**, e «Annulla tutto» (`tx-bulk-reset-all`) è visibile;
  - il validate manda 2 update che non cambiano nulla.
- I test esistenti di `fieldEq` non confrontavano mai due costi.

### 1.4 Il 💡 propone le righe legate a un evento — CONFERMATO (11/10, trovato durante il passo 2)
- `promote_suggest_bulk` (`transaction_service.py:795-883`) ignora `asset_event_id` da tutti e due i lati:
  - **candidati**: una ADJUSTMENT salvata e legata a uno SPLIT si propone come l'altra metà di una ADJUSTMENT opposta
    su un altro broker;
  - **ingressi**: `TXPromoteSuggestInput` non ha il campo, e una riga legata riceve candidati.
- Il frontend mostra la risposta così com'è (`importableSuggestions`, `promoteSuggest.ts:74-83`). Il 💡 e il cancello
  del salvataggio (`tx-bulk-unseen-suggestions`) propongono una riga che, una volta importata, nessuno può unire: il
  banner e la selezione la rifiutano dal passo 2, il backend dal passo 1. Il vicolo cieco nasce con D2.
- **Rossi API** (`test_transactions_batch_split_promote.py`, B3), tutti col proprio asset, i propri broker e il
  proprio SPLIT:
  - **B3.8** (`:1711-1779`): il candidato legato si propone accanto al gemello non legato (`[143, 144]`);
  - **B3.9** (`:1780-1815`): un ingresso con `asset_event_id` → 422 `extra_forbidden`; il campo è il contratto nuovo;
  - **B3.10** (`:1816-1847`): `null` e `0` valgono come non legato (oggi 422).
- **Rossi E2E** (`tx-bulk-promote-cost-basis.spec.ts`):
  - **PC2b**: il ricevente legato sta fuori dall'editor → il 💡 conta 2 invece di 1;
  - **PC2c**: il ricevente legato sta dentro l'editor → l'editor non manda il legame, e il 💡 conta 2 invece di 1. È
    l'unica prova della riga del Bulk: resta rosso con la sola cura del backend.

## 2. Correzione proposta (dopo il via)

### 2.1 Backend: vincoli della coppia TRANSFER (`_validate_linked_pair`)
- Per una coppia TRANSFER: asset diverso → `pairAssetMismatch`; quantità non esattamente opposte (Decimal) →
  `pairQuantityMismatch`, con `qtyA` e `qtyB`.
- L'issue va sulla prima creazione della coppia, come gli altri errori di `resolve_create_links`.
- **D1, ambito**:
  - (a) solo TRANSFER, il caso grave;
  - (b) tutti i vincoli dichiarati in `pair_field_constraints`, anche CASH_TRANSFER (importo opposto, stessa valuta) e
    FX_CONVERSION (valute diverse, stesso broker).
  - I form e gli import li rispettano già: i form usano un solo campo condiviso, e solo DEGIRO crea coppie FX, sempre
    corrette. (b) toccherebbe solo i client API e porterebbe 2 o 3 chiavi in più.
  - **Consiglio (a)** ora, (b) nel backlog.

### 2.2 Backend: il promote valida le righe che produce (`apply_promotes`)
- Prima di applicare un promote, si validano le due righe nel loro stato finale con le stesse regole di business di
  create e update (`validate_transaction_business_rules`).
- Una riga legata a un evento dà quindi `eventTypeIncompatible`, sull'operazione `promote` con `ref_id`, e il promote
  non si applica. Chiave già esistente: «{type} cannot be linked to an asset event (only {allowed})».
- **D2**: rifiutare (consigliato) o azzerare `asset_event_id`?
  - Azzerarlo cancellerebbe in silenzio il legame con lo SPLIT: le quote del frazionamento passerebbero per un
    trasferimento.

### 2.3 Frontend: la regola dell'editor (`transactionTypeStore.ts`, `findPromoteMatch`)
- **Quantità**: «opposite» vuol dire `qA === -qB`, con entrambe diverse da zero. Così −3/+5 non viene più proposto,
  sia in locale (riga nuova + nuova) sia con le righe salvate.
- **Evento**: campi facoltativi `eventA`/`eventB` in `PromoteContext`. Se una riga è legata a un evento e il tipo di
  arrivo non lo ammette, non c'è match. Chi chiama deve passarli:
  - S in `buildPromoteCtx` (`TransactionBulkModal.svelte`), nelle sue superfici;
  - io in `routes/(app)/transactions/+page.svelte:356-364`, se me lo concedi.
- **Test**: per `findPromoteMatch` non c'è un test, e `tx-unit` esegue solo i file registrati. Serve un file nuovo,
  `frontend/src/lib/stores/transactions/transactionTypeStore.test.ts`, registrato in
  `scripts/test_runner/_frontend_transaction.py` (`front_tx_unit`, file condiviso). Chiedo il permesso; il rosso lo
  scrivo col via.

### 2.4 Frontend: `fieldEq` per valore (`txPayloadHelpers.ts`)
- Un ramo per `cost_basis_override`: un valore assente, o con importo vuoto o di spazi, vale «nessun costo»; altrimenti
  si confrontano il `code` e l'`amount` come decimale esatto (`exactDecimalEqual`, come per `cash`).
- `buildUpdateDiff` e `diffDualItem` non mandano più costi uguali. «Salva» resta spento e non partono update che non
  cambiano nulla.

### 2.5 Chiavi i18n nuove (cataloghi di S, 4 lingue) — solo per 2.1
- `transactions.errors.pairQuantityMismatch`:
  - EN «A transfer must move the same quantity out of one broker and into the other (found {qtyA} and {qtyB})»;
  - IT «Un trasferimento deve far uscire da un broker ed entrare nell'altro la stessa quantità (trovate {qtyA} e
    {qtyB})».
- `transactions.errors.pairAssetMismatch`:
  - EN «Both sides of a transfer must be the same asset»;
  - IT «I due lati di un trasferimento devono essere lo stesso asset».
- FR ed ES li scrive S. Senza le chiavi il messaggio uscirebbe in inglese, dal testo del backend.
  > **Superato** (coordinator, 10/10, «Via al passo 2»): D ha finito coi cataloghi, quindi le quattro lingue le
  > scrive P.

### 2.6 Il 💡 e le righe legate a un evento (`promote_suggest_bulk`) — approvato dal coordinator l'11/10
- **Schema**: `TXPromoteSuggestInput.asset_event_id`, facoltativo (`ge=0`); `None` o `0` vuol dire non legato. È
  additivo: un client che non lo manda si comporta come prima.
- **Servizio**: per un ingresso legato si saltano le regole il cui tipo d'arrivo non ammette il legame
  (`event_compatible` di `TX_TYPE_METADATA`), e oggi questo dà una lista vuota. Un candidato legato si scarta per le
  stesse regole. È la stessa regola di `findPromoteMatch` e di `_promoted_state_issues`.
- **Bulk**: il mapping degli input della ricerca manda `asset_event_id` di ogni riga (`TransactionBulkModal.svelte`,
  una riga, fuori da `buildPromoteCtx`). Poi `api sync`: il client generato è ignorato da git.
- **Doc** (coordinator, 11/10, «Via alla doc»):
  - in inglese, via docs-writer: `service.md`, `split_promote.md`, `brim_plugin_guide.md` e `transaction-draft.md`;
    l'ultima con anche `assetQuantitiesCancel` di S;
  - le due pagine utente (`adjustment`, `transfer`) solo in inglese, senza stamp: le traduzioni le fa M.

## 3. Effetto sui test esistenti

- **Backend**: le coppie TRANSFER dei test sono tutte −q/+q sullo stesso asset (`create_transfer_pair`, i test WAC, i
  test API dei transfer); anche quelle del seed (`populate_mock_data.py`: −5/+5 Apple, −0,1/+0,1 BTC, −3/+3 Apple). I
  test di promote esistenti (cassa salvata+salvata, ADJUSTMENT nuova+nuova −3/+3, cassa salvata+nuova, vincoli, campi
  risolti, G1/G2/R3a/R3b del lotto 40) restano validi.
  - Atteso: verdi tutti, più R42a, R42b e R42c.
  - Da rieseguire: `api batch-split-promote`, `api transactions-wac`, `api transactions`, `api brokers`,
    `api transfer-promotion`, `services transaction`.
- **Frontend**:
  - `tx-unit`: nessun test esistente confrontava costi; gli 8 rossi diventano verdi;
  - E2E: WB11 diventa verde. Da rieseguire gli spec che aprono righe salvate nel Bulk o promuovono: `tx-wac-bulk`,
    `tx-wac-formmodal`, `tx-commit-all-types`, `tx-bulk-promote-exec`, `tx-split-promote`, `tx-delete`, `tx-clone`,
    `tx-paired-edit`.
  - Rischio: uno spec che apra righe con costo manuale e salvi senza modifiche aspettandosi un commit. Oggi passerebbe
    solo grazie al difetto; non ne ho trovati, e lo dirà la corsa.

## 4. Passi

- **Q0** ✅ (10/10): rossi e analisi.
  > **Note implementazione**:
  > - Backend: `api batch-split-promote` 28 passati e 3 falliti (R42a, R42b, R42c); G42 verde.
  > - `tx-unit`: 708 passati, 8 falliti (i nuovi rossi di `txPayloadHelpers.test.ts`).
  > - `tx-wac-bulk`: 10 passati, 1 fallito (WB11).
  > - Prima `front build --debug` sulla base.
  >
  > **⚠️ Fuori pista**:
  > - R42c ha dovuto usare un costo manuale: con Auto il rosso nasceva da `costBasisRequired` e non dal legame con
  >   l'evento (§1.2);
  > - WB11 usa due righe, perché con una sola si apre anche il form della riga, che fa un suo validate;
  > - gli unitari usano la regola finta `REQUIRED_POSITIVE` del mock esistente, che sta per ADJUSTMENT.
- **Q1** ✅ (10/10): **passo 1**, cioè 2.1–2.4 e `+page.svelte`, più il rosso di `transactionTypeStore.test.ts`.
  > **Note implementazione**:
  > - **Rosso prima del codice** (test-author): nuovo `transactionTypeStore.test.ts` (245 righe). F1–F4 sono rossi
  >   (−3/+5 nei due ordini; riga A o B legata a un evento → oggi esce un TRANSFER); G1–G7 sono verdi. Il file non è
  >   ancora registrato (passo 2): gira con il binario bloccato `frontend/node_modules/.bin/vitest`, e
  >   `check-orphans` lo segnalerà fino alla registrazione.
  > - **2.1** `_validate_linked_pair`: per una coppia TRANSFER, `pairAssetMismatch` se gli asset differiscono, e
  >   `pairQuantityMismatch` se le quantità non sono esattamente opposte (Decimal, con `qtyA`/`qtyB` come stringhe).
  >   Il messaggio per ora è inglese.
  > - **2.2** `apply_promotes`: nuovo `_promoted_state_issues`, che valida le due righe nello stato promosso con
  >   `validate_transaction_business_rules`, come per create e update.
  >   - Una riga legata a un evento dà `eventTypeIncompatible` sull'operazione `promote`, con `ref_id` solo per le
  >     righe salvate.
  >   - Il promote non si applica e `asset_event_id` non si tocca.
  > - **2.3** `findPromoteMatch`: «opposite» = `qA !== 0 && qA === -qB`. Il contesto ha i campi facoltativi
  >   `eventA`/`eventB`: nessun match se il tipo d'arrivo ha `event_compatible` falso. `+page.svelte` passa
  >   `asset_event_id` delle due righe.
  > - **2.4** `fieldEq`: nuovo ramo per `cost_basis_override` (`costBasisValue`). Un valore assente, o con importo
  >   vuoto o di spazi, vale «nessun costo»; altrimenti contano il `code` e `exactDecimalEqual(amount)`.
  >   `description` resta un confronto di stringhe.
  >
  > **Gate** (corsia 6161, uno alla volta; log in `/tmp/libreFolio_p42_s1_*.log`):
  > - Backend:
  >   - `api batch-split-promote` 31/31 (R42a/b/c e G42 compresi);
  >   - `api transactions-wac` 20/20, `api transactions` 23/23, `api brokers` 29/29;
  >   - `api transfer-promotion` 3/3, `services transaction` 66/66.
  > - Frontend:
  >   - unità: `transactionTypeStore.test.ts` 11/11; `tx-unit` 716/716 (gli 8 rossi di `fieldEq` compresi);
  >   - `front check`: 0 errori, 0 warning;
  >   - `front build --debug` OK;
  >   - E2E: `tx-wac-bulk` 11/11 (WB11 compreso), `tx-wac-formmodal` 10/10, `tx-commit-all-types` 19/19,
  >     `tx-bulk-promote-exec` 9/9, `tx-split-promote` 6/6, `tx-delete` 15/15, `tx-clone` 8/8, `tx-paired-edit` 4/4.
  > - Ruff, black e prettier puliti; `git diff --check` pulito; porta libera.
  >
  > **Nota per il backlog (non nel lotto)**: un update via API che cambia la quantità di una sola gamba di un
  > TRANSFER salvato non è controllato. `validate_updated_pairs` guarda solo descrizione e tag. Va con C-42, i vincoli
  > delle coppie.
  >
  > **Vincolo** (coordinator, 10/10): le due chiavi i18n del passo 2 si aggiungono solo dopo il suo via, quando D
  > (correzioni ai cataloghi it/fr del PAC) è dentro e il target è fuso nel ramo.
- **Q2** ✅ (11/10): **passo 2**, dopo il treno 30 e il merge del target, col via del coordinator:
  - `buildPromoteCtx` (`eventA`/`eventB`);
  - la registrazione di `transactionTypeStore.test.ts` in `front_tx_unit`;
  - le due chiavi nelle 4 lingue;
  - 2.5 `cashAmountsCancel` esatto, riusando `assetQuantitiesCancel` di S.
  Poi i gate.
  > **Note implementazione** (10/10, base `f4a42bf4a`, treno 31, coi 10 file del passo 1 intatti):
  > - **2.5, rosso prima del codice** (test-author): in `promoteHelpers.test.ts` un blocco nuovo
  >   «exact at large magnitudes» (righe 138–189). 4 rossi: un centesimo a 10 milioni, a 123 milioni e a 1,2 trilioni,
  >   più il caso normalizzato (CASH_OUT 10000000.00 da DB, CASH_IN 10000000.01). 4 controlli verdi: importi uguali, zeri
  >   di sola rappresentazione, e il caso normalizzato uguale. `tx-unit` col rosso: 866 passati, 4 falliti
  >   (`expected true to be false`).
  > - **2.5, cura**: `cashAmountsCancel` firma i due importi con la regola del tipo (`buildSignedCash`, la stessa
  >   canonicalizzazione di `signedCashAmount`), chiede segni opposti e diversi da zero (`exactDecimalSign`) e
  >   confronta i moduli con `exactDecimalEqual`. Niente più `Number` né tolleranza: è lo schema di
  >   `assetQuantitiesCancel`. `signedCashAmount` resta, con i suoi test, perché è un'API numerica esportata.
  > - `buildPromoteCtx` in `TransactionBulkModal.svelte`: solo `eventA`/`eventB` (`asset_event_id ?? null`).
  > - `transactionTypeStore.test.ts` registrato in `front_tx_unit` (`scripts/test_runner/_frontend_transaction.py`,
  >   l'unico elenco che lo nomina).
  > - **Gate parziali**: `tx-unit` 881/881 su 22 file (870 + gli 11 dello store); `front check` 0/0; prettier e
  >   `git diff --check` puliti.
  > - **In attesa**: le due chiavi nei cataloghi. Il checkpoint separato di `DistributionEditor` tocca gli stessi
  >   quattro file, quindi le chiavi entrano solo dopo il suo commit, per non mescolare i due commit.
  > - **E2E** (`front build --debug`, poi uno alla volta; log `/tmp/libreFolio_p42_s2_<spec>.log`):
  >   `tx-bulk-suggest-ux` 8/8, `tx-bulk-promote-exec` 9/9, `tx-split-promote` 6/6, `tx-import-scalable-transfers`
  >   4/4, `tx-selection-after-bulk` 10/10; `tx-bulk-promote-cost-basis` 3/4. Porta libera.
  >
  > **⚠️ Fuori pista**: `tx-bulk-promote-cost-basis.spec.ts` (di S, `1a4fe32a4`, treno 30) PC2 promuove un
  > ADJUSTMENT salvato legato a uno SPLIT, che la sua intestazione chiama l'unica strada pubblica verso un ricevente
  > salvato senza costo. Con D2 quel promote è impossibile per scelta: il banner non lo propone più (`buildPromoteCtx`
  > passa gli eventi) e il backend lo rifiuterebbe con `eventTypeIncompatible`. Il test si ferma a `:569`
  > (`expectBannerOffers(page, 1)`). Premessa superata da D2, non una regressione. Nessun altro spec combina un evento
  > collegato e un promote. Proposta al coordinator (10/10): il test-author riscrive PC2 come lato UI di D2 (il banner
  > e la selezione non offrono il promote di un ricevente legato a uno SPLIT); in attesa del permesso, perché il file
  > è di S.
  >
  > **PC2 riscritto** (coordinator, 11/10: approvato; S è archiviata e lo spec passa a P):
  > - il test-author l'ha riscritto come lato UI di D2. È lo stesso setup, col ricevente salvato e legato allo SPLIT
  >   dentro l'editor, più un −5 nuovo; il banner resta nascosto, prima e dopo la riga nuova; la selezione delle due
  >   righe non mostra `promote-toolbar-confirm`, con le checkbox `checked` come ancora; le righe restano due, senza
  >   partner; il ledger è intatto;
  > - nell'intestazione, la sezione su PC2 dice che il controllo del costo sul promote di una riga salvata
  >   (`_check_promoted_saved_cost_basis`) resta raggiungibile solo dall'API, coperto da
  >   `test_promote_saved_saved_clearing_cost_basis_is_rejected`; tolta `BALANCE_CODES`, che era rimasta senza uso;
  > - `tx-bulk-promote-cost-basis` 4/4, prettier pulito, porta libera (log `/tmp/libreFolio_p42_pc2.log`);
  > - resta da fare: la `desc` del catalogo del runner (`_frontend_transaction.py:628`) descrive ancora il vecchio
  >   PC2, e la aggiorno io.
  >
  > **⚠️ Fuori pista, un reperto nuovo: il 💡 propone le righe legate a un evento.**
  > - `promote_suggest_bulk` (`transaction_service.py:795-883`) ignora `asset_event_id`, sia nei candidati sia negli
  >   ingressi: `TXPromoteSuggestInput` non ha il campo. `importableSuggestions` (`promoteSuggest.ts:74-83`) toglie
  >   solo le righe già nell'editor.
  > - Il risultato è un vicolo cieco nato con D2: il 💡 e il cancello del salvataggio propongono una riga che, una
  >   volta importata, nessuno può unire.
  > - Decisione del coordinator (11/10): **nel lotto 42**. Sono permessi il campo facoltativo `asset_event_id` in
  >   `TXPromoteSuggestInput`, la riga del mapping degli input nel Bulk e `api sync`.
  > - L'ordine: prima i rossi (API su `/promote-suggest` per candidati e ingressi; E2E PC2b col ricevente fuori
  >   dall'editor; PC2c, l'unica prova della riga del Bulk), poi la cura.
  >
  > **Il 💡, la chiusura** (11/10; i dettagli in §1.4 e §2.6):
  > - **Rossi** (test-author, corsia 6161): `api batch-split-promote` 3 falliti e 31 passati (B3.8, B3.9, B3.10);
  >   `tx-bulk-promote-cost-basis` 4 passati e 2 falliti (PC2b, PC2c), tutti per il motivo dichiarato. Log in
  >   `/tmp/libreFolio_p42_suggest_{api,e2e}_red.log`.
  > - **Cura**: lo schema, `promote_suggest_bulk`, la riga del Bulk e `api sync`, che non tocca file tracciati. Il router
  >   non è toccato: la descrizione del campo basta per l'OpenAPI.
  > - **Chiavi**: `transactions.errors.pairQuantityMismatch` e `pairAssetMismatch` nelle 4 lingue, con
  >   `dev.py i18n add`, dopo il commit `01b967c56` di DistributionEditor. Nessun markup nei valori, quindi
  >   `htmlInterpolation.gate` non vuole voci nuove.
  > - La `desc` del catalogo del runner per `tx-bulk-promote-cost-basis` ora descrive PC2, PC2b e PC2c.
  >
  > **⚠️ Fuori pista**: il test-author ha dovuto cambiare `openEditorOn` per aprire l'editor su una sola riga. Con una
  > riga sola si apre il form di modifica (`autoForm: 'edit'`), e l'helper ora lo annulla senza toccarlo. PC1–PC4 non
  > passano da quel ramo.
  >
  > **Gate finali** (corsia 6161, uno alla volta; base `01b967c56`):
  > - Backend:
  >   - `api batch-split-promote` 34/34;
  >   - `api transactions` 23/23, `api transfer-promotion` 3/3, `api transactions-wac` 20/20, `api brokers` 29/29,
  >     `api brim-scalable` 2/2;
  >   - `services transaction` 66/66, `schemas transactions` 75/75;
  >   - ruff e black puliti.
  > - Frontend:
  >   - `tx-unit` 881/881, `core-unit` 3676/3676 (con `htmlInterpolation.gate`), `front check` 0/0;
  >   - `front build --debug` OK;
  >   - E2E: `tx-bulk-promote-cost-basis` 6/6, `tx-bulk-suggest-ux` 8/8, `tx-bulk-promote-exec` 9/9,
  >     `tx-crud-full` 7/7, `tx-fx-implied-rate` 3/3, `tx-import-scalable-transfers` 4/4, `tx-split-promote` 6/6,
  >     `tx-selection-after-bulk` 10/10, `tx-ca-contract` 12/12, `tx-wac-bulk` 11/11.
  > - i18n: `i18n audit` 4339 chiavi complete e 0 inutilizzate; `utils gate-i18n-usage` 195/195.
  > - `check-orphans` pulito; porta libera.
  > - Log: `/tmp/libreFolio_p42_final_*.log` e `/tmp/libreFolio_p42_s2b_*.log`.
  >
  > **Doc** (docs-writer, solo inglese, nessuno stamp né `translate`):
  > - le pagine:
  >   - `service.md:152-160`: le regole TRANSFER di `_validate_linked_pair()`;
  >   - `split_promote.md`: il passo 3 di `apply_promotes()`, un paragrafo sul legame con l'evento, la clausola su
  >     `findPromoteMatch()` della pagina Transazioni, e la riga `eventTypeIncompatible` nella tabella dei codici;
  >   - `brim_plugin_guide.md:677-684`: `pairSameBroker`, l'asset unico e le quantità opposte;
  >   - `transaction-draft.md`: il banner, con il legame, le quantità, `cashAmountsCancel` e `assetQuantitiesCancel`
  >     di S, e la barra della selezione; il 💡, con `asset_event_id`;
  >   - `adjustment.en.md:37` e `transfer.en.md:50`: nessuna delle due righe legata a un evento.
  > - `mkdocs build` strict OK (30,75 s); `check-links` 95 validi più 8 risolti a runtime; `translate-validate` sulle
  >   due pagine utente: 0 errori. Il debito è una frase per pagina, per il giro di M.
  > - Il docs-writer ha trovato e lasciato stare, perché fuori dal lotto:
  >   - `transaction-draft.md`, il punto «Merge all»: *N* è `mergeAllPairs.length`, non il numero dei suggerimenti;
  >   - `transfer.en.md:44`: un Transfer non è fatto di due Adjustment;
  >   - `adjustment.en.md`, «Impact on Cost Basis»: «senza override, costo zero» vale solo per i lotti FIFO;
  >   - un possibile difetto di codice, non verificato: lo slider *Max Δ days* ammette 0, ma `/promote-suggest` vuole
  >     `tolerance_days ≥ 1`.
  >   Vanno al coordinator, per il 38.
  >
  > **Residuo, segnalato al coordinator**: per un TRANSFER, la barra della selezione (`selectedForPromote`) usa solo
  > `findPromoteMatch`, che confronta le quantità come numeri JS (`qA === -qB`), e non chiama `assetQuantitiesCancel`
  > come fa il banner. Oltre circa 15 cifre significative due quantità diverse possono sembrare opposte. Il salvataggio
  > le rifiuta comunque (`noPromoteRule`, oppure `pairQuantityMismatch` per due righe nuove), quindi nessun dato è
  > sbagliato. La cura sarebbe una riga nel Bulk, come quella di `cashAmountsCancel` lì accanto.
- **Q3** ✅ (11/10): CHECKPOINT READY inviato al coordinator con il manifest (26 percorsi), le righe del CHANGELOG e il
  messaggio di commit (`/tmp/libreFolio_commit_p42.txt`); poi FROZEN.
  > **Aggiunta, solo doc in inglese** (coordinator, 11/10; serve a non far tradurre a M due volte le stesse pagine). Il
  > docs-writer ha corretto i tre testi falsi che aveva trovato:
  > - `transfer.en.md:43`: un Transfer sono due righe `TRANSFER`, una per broker, legate da `related_transaction_id`;
  >   lo split le rende due `ADJUSTMENT` e il promote fa il contrario;
  > - `adjustment.en.md:46-49`, «Impact on Cost Basis»:
  >   - senza override il lotto FIFO apre a costo zero, ma per il costo medio il costo è sconosciuto e non zero: la
  >     posizione resta incompleta finché non si chiude, e c'è `MISSING_COST_BASIS`;
  >   - c'è la regola del salvataggio, con Auto che vale 0 a posizione vuota (la decisione P-1);
  >   - fanno eccezione le righe legate a uno split e quelle salvate prima che la regola esistesse;
  > - `transaction-draft.md:151-162`: per «Merge all» *N* è `mergeAllPairs.length`, il bottone compare quando i pair
  >   sono più di uno, e `mergeAllSuggestions` percorre `mergeAllPairs`.
  >
  > **Gate**: `mkdocs build` strict OK; `check-links` OK (95 validi più 8 risolti a runtime).
  >
  > **`translate-validate`** sulle due pagine utente: 3 errori e 12 warning, il debito per il giro di M.
  > - Gli errori sono il link nuovo di `adjustment` verso «Cost Basis Override», che manca in it, fr ed es.
  > - I warning:
  >   - 9 su `transfer`, per il codice inline nuovo;
  >   - 3 su `adjustment`, per il numero dei link.
  > - Su tutto il sito gli errori sono 93: 90 c'erano già, su `user/transactions/import/how-to`, `transactions/index` e
  >   `import/index`.
  > - `release.yml` fa fallire `translate-validate` nelle corse di release (nella nightly di `dev` no), quindi il giro
  >   di M deve chiuderli tutti prima della 1.2. Il link resta: per il giro è un debito normale.
  >
  > **⚠️ Fuori pista**: il docs-writer segnala la stringa `transactions.costBasisOverride.warningAdjustment` («If these
  > shares cost nothing (a stock split or a gift), enter 0»). Per un regalo il costo è quello del donatore, come dice
  > la tabella della pagina. È fuori dal lotto: va al coordinator, per il 38, con P-11.

## 5. Definizione di fatto

- Nessuna coppia TRANSFER si salva con quantità che non si annullano o con asset diversi.
- Nessun promote produce una riga legata a un evento che il suo tipo non ammette.
- L'editor non propone coppie che il backend rifiuterebbe.
- Aprire il Bulk su righe con costo manuale non le segna come modificate.
- Rossi verdi, regressioni verdi, porta libera, FROZEN.

## 6. Compito a lato: DistributionEditor

Fuori dal lotto 42, con un checkpoint e un commit propri (coordinator, 10/10).
- **Il reperto è di M**, visto negli scatti della gallery:
  [`27_releaseImages/plan-phase00ReleaseGallery.prompt.md`](../27_releaseImages/plan-phase00ReleaseGallery.prompt.md),
  passo 26, «Fuori pista». I difetti erano tre:
  - `DistributionEditor.svelte:377`: l'intestazione `'Weight %'` era un letterale;
  - `:527`, `:532` e `:534`: i totali `toFixed(2)}%` non erano localizzati;
  - `es.json:338`: «Agregar pais» era senza accento.
- **La cura**:
  - la chiave `assets.distribution.weightPercent` nelle 4 lingue;
  - l'opzione `locale` in `formatPercent`, usata dall'editor per il totale, l'eccesso, la parte mancante e la cella
    in sola lettura;
  - «Agregar país»;
  - in più, il fr `excess` in «excès».
- **Rossi prima** (test-author): 6 in `formatPercent.test.ts` e 1 E2E in `asset-classification.spec.ts`, con la UI in
  francese.
- **Gate**: `core-unit` 3676/3676, `front check` 0/0; E2E `asset-classification` 4/4, `asset-modal` 17/17,
  `tx-import-asset-inspector` 5/5; `i18n audit` completo.
- **Checkpoint**: 8 percorsi, verificato dal coordinator (10/10). Commit `01b967c56`
  («fix(assets): localize distribution editor labels»), fuso nel target come `e26b1b7f2` (treno 32, 11/10).

## 7. Seguito: C-46, C-47, C-48 (11/10)

Il lotto 42 è nel target come `7f8233c47`, fuso come `8ca0d5535` (treno 34, `dev_release2` = `f6a5a2fcc`). Il
coordinator chiede, per il developer, di chiudere prima della 1.2 le tre voci del 38 nate da questo lotto, ognuna col
suo rosso prima. Base: worktree a `f6a5a2fcc`, pulita. Corsia 6161.

- **C-46** ✅ (11/10): la barra della selezione (`selectedForPromote`) usa per un TRANSFER il confronto esatto del banner
  (`assetQuantitiesCancel`), con una riga accanto a quella di `cashAmountsCancel`.
  > **Rosso** (test-author, 11/10): **PC5** in `tx-bulk-promote-cost-basis.spec.ts` (`:889-947`), con la sezione
  > nell'intestazione (`:97-117`) e l'helper `unselectBulkRows`.
  > - La coppia sono due righe nuove scritte nel form: `-123456789012.123456` su A e `+123456789012.123457` su B, cioè
  >   12 cifre intere e 6 decimali, il massimo di `Numeric(18, 6)`. Come double sono lo stesso numero (provato in Node,
  >   gli stessi bit IEEE), come decimali no.
  > - Nello stesso test c'è il controllo positivo: la coppia esatta `±123456789012.123456`, che banner e barra offrono.
  > - Il form conserva tutte le cifre, quindi il difetto si raggiunge dalla UI.
  > - Esito: PC1–PC4, PC2b e PC2c verdi; PC5 rosso, con `promote-toolbar-confirm` visibile (atteso 0, trovato 1).
  >   Log in `/tmp/libreFolio_c46_red.log`.
  >
  > **Cura**: in `selectedForPromote` c'è ora `if (match.targetType === 'TRANSFER' && !assetQuantitiesCancel(...))
  > return null;`, accanto alla riga di `cashAmountsCancel`, con il commento.
  >
  > **⚠️ Fuori pista** (dal test-author): la cella della quantità nella griglia mostra `parseFloat(qty)`, quindi le due
  > righe della coppia appaiono uguali (`±123456789012.12346`) e l'utente non vede perché non si uniscono. È fuori da
  > C-46: va segnalato al coordinator.
- **C-47**: lo slider *Max Δ days* arriva a 0, ma `/promote-suggest` vuole `tolerance_days ≥ 1`. Prima la verifica,
  poi la cura che rompe meno, da proporre al coordinator prima di farla. ✅ (11/10)
  > **Verifica nel codice** (11/10):
  > - lo slider `promote-suggest-delta-input` va da 0 a 14 (`TransactionBulkModal.svelte:3470`, valore in
  >   `sessionStorage`);
  > - la ricerca del 💡 manda `tolerance_days: maxDeltaDays` (`:2787`) all'endpoint, che vuole
  >   `Query(7, ge=1, le=30)` (`api/v1/transactions.py:283`): a 0 risponde 422, che finisce in un `console.warn`;
  > - il 💡 resta vuoto, o mostra la risposta vecchia, mentre il banner locale propone le coppie dello stesso giorno.
  >
  > **⚠️ Fuori pista**: spostare lo slider non rilancia la ricerca del 💡. La chiave della richiesta sono solo gli input,
  > e `maxDeltaDays` si legge nel timer, fuori dal tracciamento dell'effetto.
  >
  > Proposta al coordinator: (b), il backend accetta 0 (`ge=0`, come `events/suggest`), più la finestra nella chiave
  > della ricerca. L'alternativa (a) è lo slider da 1, con il clamp del valore salvato.
  >
  > **Decisione** (coordinator, 11/10): **(b)**. `ge=0` in `api/v1/transactions.py:283`, file in cui oggi non scrive
  > nessun altro; poi `api sync`; e la finestra entra nella chiave della ricerca del 💡. Prima i rossi: l'API a 0 dà
  > 200 con i soli candidati dello stesso giorno; nell'E2E lo slider va a 0, e uno spostamento fa partire una ricerca
  > nuova.
  >
  > **Rossi** (test-author, 11/10):
  > - **B3.11** `test_suggest_tolerance_zero_is_the_same_day_only` (`test_transactions_batch_split_promote.py:1848-1887`).
  >   Il controllo a `tolerance_days=1` passa e restituisce le due righe; a 0 la risposta è 422 (`greater_than_equal`).
  >   `api batch-split-promote` dà 34 passati e 1 fallito.
  > - **PC6** in `tx-bulk-promote-cost-basis.spec.ts` (`:1015-1063`, con la sezione nell'intestazione a `:122-142`).
  >   - Ci sono i mittenti −5 di oggi e di ieri, fuori dall'editor. Lo slider va a 0, poi si aggiunge un +5 nuovo:
  >     oggi la richiesta a 0 riceve 422 e il 💡 non compare.
  >   - Lo slider passa a 1: oggi entro 5 s non parte nessuna richiesta.
  >   - La riga nuova è in Manual senza costo, perché le riscritture di Auto rilanciano la ricerca e il rosso
  >     dipenderebbe dai tempi.
  > - Nella stessa corsa PC1–PC5 sono verdi: **PC5 verde è la prova di C-46**.
  > - Il test-author ha anche aggiornato i commenti invecchiati dell'intestazione: PC2b e PC2c sono ora regressioni,
  >   PC5 è al passato, e PC3 descrive il confronto della barra.
  >
  > **Cura**:
  > - `api/v1/transactions.py:283`: `Query(7, ge=0, le=30)`. `api sync` aggiorna il client generato
  >   (`gte(0).lte(30)`), che git ignora: nessun file tracciato cambia;
  > - nell'effetto del 💡 in `TransactionBulkModal.svelte`, `toleranceDays = maxDeltaDays` si legge nella parte
  >   tracciata ed entra nella chiave (`JSON.stringify({inputs, toleranceDays})`); la richiesta usa quel valore. Uno
  >   spostamento dello slider fa partire una ricerca nuova, con il debounce di 500 ms;
  > - doc, via docs-writer: in `transaction-draft.md` il punto del 💡 dice che la ricerca usa la finestra del banner,
  >   che 0 è lo stesso giorno e che lo slider rilancia la ricerca. In più la clausola sulla barra della selezione
  >   ora cita anche `assetQuantitiesCancel` (C-46).
- **C-48**: il testo `transactions.costBasisOverride.warningAdjustment` nelle 4 lingue. Per un regalo il costo è
  quello del donatore, non 0. ✅ (11/10)
  > Proposta al coordinator:
  > - niente rosso: è un testo, e le regole dei test vietano di asserire il testo tradotto;
  > - la verifica è `i18n audit` più la lettura delle 4 stringhe;
  > - segnalato anche `user/transactions/form.en.md:39`, che dà lo stesso consiglio.
  >
  > **Decisione** (coordinator, 11/10):
  > - niente rosso. Le verifiche sono `i18n audit`, la lettura delle 4 stringhe riportata nel checkpoint e
  >   `gate-i18n-usage`;
  > - il testo inglese va bene; in IT, FR ed ES si usano i termini del glossario;
  > - `form.en.md:39` lo correggo io in inglese, via docs-writer, senza stamp. M lo traduce nella parte B del suo giro,
  >   con `adjustment` e `transfer`.
  >
  > Il glossario (`aphra-pipeline/glossaries/glossary.json`): cost basis è «costo di carico», «coût de base», «coste
  > base»; uno split è «split», «division», «desdoblamiento». Le etichette del campo nella UI sono «Costo di carico
  > manuale», «Coût de base manuel» e «Coste base manual». L'IT oggi dice «costo base» e «frazionamento», il FR
  > «fractionnement»: tutti e due vanno allineati.
  >
  > **Fatto** (11/10):
  > - `dev.py i18n update transactions.costBasisOverride.warningAdjustment`, una riga per catalogo. I testi:
  >   - EN «The manual cost basis is empty: the transaction cannot be saved without it. Enter what these shares cost:
  >     0 for a stock split, the donor's original cost for a gift.»
  >   - IT «Il costo di carico manuale è vuoto: senza, la transazione non si può salvare. Scrivi quanto sono costate
  >     queste quote: 0 per uno split, il costo di carico originale del donante per un regalo.»
  >   - FR «Le coût de base manuel est vide : sans lui, la transaction ne peut pas être enregistrée. Saisissez ce que
  >     ces parts ont coûté : 0 pour une division d’actions, le coût de base d’origine du donateur pour un don.»
  >   - ES «El coste base manual está vacío: sin él, la transacción no se puede guardar. Escribe lo que costaron estas
  >     participaciones: 0 para un desdoblamiento, el coste base original del donante para un regalo.»
  > - `form.en.md:39`, via docs-writer: «Type 0 only for units that really cost nothing, such as the new shares of a
  >   stock split; for a gift, type the donor's original cost.» Il resto della riga e l'admonition restano com'erano,
  >   e sulla pagina non c'è altro consiglio sui regali.

**Gate del seguito** (11/10, corsia 6161, uno alla volta, base `f6a5a2fcc`; log in `/tmp/libreFolio_c4x_*.log`):
- `front build --debug` OK; `front check` 0/0; ruff, black e prettier puliti; `api sync` senza file tracciati cambiati.
- E2E, tutti verdi:
  - `tx-bulk-promote-cost-basis` 8/8, con PC5 e PC6;
  - `tx-bulk-suggest-ux` 8/8, `tx-bulk-promote-exec` 9/9, `tx-crud-full` 7/7, `tx-fx-implied-rate` 3/3;
  - `tx-import-scalable-transfers` 4/4, `tx-selection-after-bulk` 10/10, `tx-split-promote` 6/6;
  - `tx-ca-contract` 12/12, `tx-wac-bulk` 11/11, `tx-wac-formmodal` 10/10, `tx-wac-mode` 5/5.
- API: `api batch-split-promote` 35/35 (con B3.11), `api transactions` 23/23.
- Unità: `tx-unit` 881/881, `core-unit` 3676/3676, che comprende `htmlInterpolation.gate`.
- i18n: `i18n audit` 4339 chiavi complete e 0 inutilizzate; `utils gate-i18n-usage` 195/195.
- `check-orphans` pulito; porta libera.
- Doc:
  - `mkdocs build` strict OK; `check-links` 95 validi;
  - `translate-validate`: su `form` nessun problema strutturale, perché la frase nuova è testo semplice, ma it, fr ed
    es portano ancora la frase vecchia, per la parte B di M;
  - sul sito restano 39 errori: 30 in `deposited-capital`, 6 in `dashboard/charts`, e i 3 noti di `adjustment` dal
    lotto 42.

## 8. Mini-lotto dai reperti dell'audit di M (11/10)

- Decisione del coordinator (11/10): il developer è fuori e gli ha delegato le cose ragionevoli.
- Base: `41ddc61cb` (treno 37), pulita. Corsia 6161.
- I cataloghi i18n sono di P per queste voci, fino al checkpoint.

**Integrazione del seguito (§7):** C-46…C-48 sono entrati come `bdec709d2`, con il merge `b5a71de01` (treno 37). Nel 38
sono ✅; le righe del CHANGELOG sono scritte dal coordinator.

- **8.1 `BrokerCard`, la percentuale** ✅ (11/10). Oggi è `toFixed(2)%`, quindi «0.00%» in tutte le lingue. Va curata come il
  `DistributionEditor` (treno 32): `formatPercent` con `locale: $currentLanguage`.
  > **Il perimetro, cioè «la card o la pagina del broker»**. I siti sono 8:
  > - `BrokerCard.svelte:157`: il P/L in percentuale fra parentesi;
  > - `routes/(app)/brokers/[id]/+page.svelte:457` e `:481`: il badge della propria quota, `broker-quota-badge`;
  > - `BrokerSharingPanel.svelte`, che è nella pagina del broker: assegnato `:516`, disponibile `:519`, le quote delle
  >   righe `:572`, `:608` e `:644`, e il suggerimento «max» `:832`.
  >
  > Restano **fuori**, e li segnalo al coordinator:
  > - i componenti della Dashboard che la pagina del broker riusa (`KpiSection`: 7 siti senza `locale`), perché sono
  >   condivisi con la Dashboard;
  > - gli assi dei grafici (`LotWacPriceChart:1604`), che di proposito tengono la forma fissa (vedi il commento di
  >   `formatPercent`).
  >
  > Nella v1.1.0 c'erano già tutti e 8.
  >
  > **Rossi** (test-author): 11 test, di cui 9 rossi e 2 controlli in inglese verdi, nei soli file registrati.
  > - `BrokerCard.test.ts`: il controllo inglese, il francese al montaggio, e il cambio en → fr → en sul posto.
  > - `BrokerSharingPanel.test.ts`: il controllo inglese di tutti i siti; assegnato/disponibile; le colonne owners,
  >   editors e viewers; il suggerimento «max».
  > - `e2e/brokers/brokers-detail.spec.ts` (`front-broker detail`): la pagina aperta in francese, e il cambio en → fr
  >   sul posto, con un broker proprio al 45,67 %.
  > - Il valore atteso si calcola sempre con `Intl` nello stesso ambiente. Chromium e Node scrivono tutti e due U+00A0.
  >   Atteso «12,34 %», trovato «12.34%».
  >
  > **⚠️ Fuori pista** (dal test-author): la card e la pagina sono componenti legacy, e una lettura di
  > `$currentLanguage` dentro un helper chiamato dal template compila in `$.untrack`, quindi non si aggiorna al cambio
  > di lingua. Per questo la cura scrive `$currentLanguage` nell'espressione del template; `formatSharePercentage`
  > riceve la lingua come parametro.
  >
  > **Cura**:
  > - `BrokerCard`: `formatPercent(…, {scale: 100, signed: false, locale: $currentLanguage})`;
  > - `BrokerSharingPanel` (6 siti) e il badge della pagina: `formatPercent(<il valore arrotondato come prima>,
  >   {signed: false, digits: 1, locale: $currentLanguage})`. Le cifre e gli arrotondamenti non cambiano, e in inglese
  >   il testo è identico.
  >
  > **Gate** (corsia 6161):
  > - `front build --debug` OK, `front check` 0/0, prettier pulito;
  > - `component-unit` 2966/2966;
  > - E2E: `front-broker detail` 37/37, `front-broker list` 9/9, `front-user broker-sharing` 17/17,
  >   `front-portfolio privacy-masking` 18/18;
  > - `front-broker broker-unit` 53/53, `core-unit` 3676/3676, `gate-i18n-usage` 195/195;
  > - `i18n audit` 4339 chiavi complete; `check-orphans` pulito; porte 6161 e 6171 libere.
  >
  > **A margine**: il suggerimento `% (max …)` di `BrokerSharingPanel:832` ha «max» scritto nel codice, quindi in
  > spagnolo non diventa «máx.». Fuori dal perimetro: lo segnalo.
- **8.2 es `pairQuantityMismatch`** ✅ (11/10): «un broker» diventa «un bróker», con `dev.py i18n update` (una riga di
  `es.json`). Niente rosso: è testo. La chiave è nata nel lotto 42, nella 1.2, quindi non serve una riga di CHANGELOG.
  > **A margine**: in `es.json` «broker» senza accento resta in 47 chiavi (39 al singolare, 9 al plurale), contro 175
  > «bróker» e 48 «brókeres». Alcune sono nomi propri, come Interactive Brokers. Fuori dal perimetro: lo segnalo.
- **8.3 es «Tasa(s)» dove il glossario dice «tipo de cambio»** ✅ (11/10). La lista è arrivata dal coordinator: il file
  dei revisori di M, fuori dal repo (`release-pipeline/runs/b15/b15_catalog_vs_glossary.tsv`).

**Il lotto cresce** (coordinator, 11/10, sui difetti dei revisori di M). Sono **fuori**, e li decide il developer, gli
altri conflitti di terminologia della lista e «Exportar IA» / «Export AI»: non si toccano. Se il lotto si allunga, prima
1, 2 e 8.

Il glossario (`aphra-pipeline/glossaries/glossary.json`) dice: exchange rate = es «tipo de cambio»; broker = es
«bróker»; broker report = es «informe del bróker». Per upload, merge e combine non ha voci.

Fatti l'11/10, solo cataloghi, con `dev.py i18n update` (script `/tmp/libreFolio_items3to7.py`, che rilegge ogni valore
dopo l'aggiornamento). Niente rossi, perché sono testi:
- **3, es «tipo de cambio»**:
  - `fx.rate`: «Tasa» → «Tipo de cambio»;
  - `fxDetail.editRates`: «Editar tasas» → «Editar tipos de cambio»;
  - `common.syncFxRates` e `transactions.errors.wacFxUnavailableSyncLink`: «Sincronizar tasas FX» → «Sincronizar tipos de
    cambio».
- **4, es «bróker»**:
  - `uploads.assignBrokers`: «Asignar Brokers» → «Asignar brókeres»;
  - `uploads.brokerReports`: «Informes de Broker» → «Informes del bróker», come dice il glossario;
  - `importWizard.globalBroker`: «Broker para subidas» → «Bróker para subidas».
- **5, accenti** in `assets.comparison.title`: fr «Comparaison des donnees du fournisseur» → «… données …»; es
  «Comparacion de datos del proveedor» → «Comparación …».
- **6, fr upload → «téléverser»**: il glossario non ha un termine per upload. Ho cambiato le 8 chiavi in cui l'inglese
  dice *upload*, e il download resta «télécharger»:
  - `brokers.showImportHistory`: «Rapports téléversés»;
  - `brokers.uploadHint`: «Téléversez des rapports…»;
  - `fileStatus.uploaded`: «Téléversé»;
  - `settings.avatarHint`: «Cliquez pour téléverser…»;
  - `uploads.editAvatar`: «Téléverser l'avatar»;
  - `uploads.cropAndUpload`: «Recadrer et téléverser»;
  - `uploads.renameAndUpload`: «Renommer et téléverser»;
  - `uploads.editIcon`: «Téléverser l'icône».
- **7, es Merge ≠ Combine**: `transactions.promoteSuggest.merge` «Combinar» → «Unir», come già il resto della famiglia
  Merge («Unir todos ({n})», «Unir {n} pares»). `mergeAllCombine` resta «Combinar».
- **8, etichette inglesi scritte nel codice** ✅ (11/10): i badge di stato di `DataEditor.svelte`, «Auto/Min/Max» di
  `ChartAestheticsSection.svelte`, i preset di `DateRangePicker.svelte`. Il rosso è dal test-author; la cura riusa
  `common.status`, `common.min` e `common.max` e aggiunge `dataEditor.status.*`, `chartSettings.yAxisAuto` e
  `datePicker.presets.{weeks,months,years}` con `{n}`.
  > **Rossi** (test-author, 11/10): 9 rossi, 3 per componente, nei soli file registrati.
  > - `DataEditor.test.ts` (`:799-921`), `ChartSignalsSection.test.ts` (`:555-648`, che ha già un blocco
  >   `ChartAestheticsSection`) e `DateRangePicker.test.ts` (`:1032-1194`).
  > - Il metodo non asserisce testo tradotto: si monta in una lingua finta, `qaa`, in cui ogni chiave appare come
  >   marcatore (`⟦key⟧`, oppure `⟦key n={n}⟧`). Un'etichetta presa dal catalogo mostra il suo marcatore; un letterale
  >   scritto nel codice mostra se stesso.
  > - Un test per file controlla che le chiavi esistano nei 4 cataloghi.
  > - Le etichette che già usavano il catalogo fanno da controlli; i testid e le chiavi dei preset non cambiano.
  >
  > **Cura**:
  > - `DataEditor`: l'intestazione è `$t('common.status')`; opzioni del filtro e badge usano la stessa mappa statica
  >   `STATUS_LABEL_KEYS` → `dataEditor.status.{original,edited,deleted,appended}`.
  > - `ChartAestheticsSection`: `chartSettings.yAxisAuto`, `common.min` e `common.max`.
  > - `DateRangePicker`: `datePicker.presets.{weeks,months,years}` con `{n}`. Le tre liste dei preset sono ora
  >   `$derived`, quindi seguono il cambio di lingua sul posto, YTD e MAX compresi.
  >
  > **Chiavi nuove** (`dev.py i18n add`), in en / it / fr / es:
  > - `dataEditor.status.original`: Original / Originale / Original / Original;
  > - `dataEditor.status.edited`: Edited / Modificato / Modifié / Modificado;
  > - `dataEditor.status.deleted`: Deleted / Eliminato / Supprimé / Eliminado;
  > - `dataEditor.status.appended`: New / Nuovo / Nouveau / Nuevo;
  > - `chartSettings.yAxisAuto`: Auto in tutte e 4;
  > - `datePicker.presets.weeks`: `{n}W` / `{n}S` / `{n}S` / `{n}S`;
  > - `datePicker.presets.months`: `{n}M` in tutte e 4;
  > - `datePicker.presets.years`: `{n}Y` / `{n}A` / `{n}A` / `{n}A`.
  >
  > Le lettere coincidono con quelle di «Personalizzato» (`datePicker.granularity.*Short`: W/M/Y in inglese, S/M/A in
  > it/fr/es), come chiede il coordinator.
  >
  > **Gate** (corsia 6161):
  > - `component-unit` 2975/2975, `core-unit` 3676/3676;
  > - E2E: `toolbar-width-sweep` 15/15, `dashboard` 27/27, `fx-list` 12/12, `fx-editor` 4/4, `fx-settings` 3/3,
  >   `asset-detail` 31/31, `asset-data-editor` 26/26, `front-broker detail` 37/37;
  > - `gate-i18n-usage` 195/195; `i18n audit` 4347 chiavi complete e 0 inutilizzate; `check-orphans` pulito; porte
  >   libere.
  >
  > **⚠️ Fuori pista** (coordinator, 11/10, dalla preparazione di M): c'è un terzo punto,
  > `charts/calendarReturnWindow.ts`, con `1W 1M 3M 1Y`, la «Finestra» del rendimento mobile nella pagina dell'asset.
  > Va localizzato con gli stessi tasti.
  > - **Rossi** (test-author):
  >   - 3 unitari in `priceChartHelpers.test.ts` (`core-unit`, `:390-440`): manca `count` o `unit`, oppure manca
  >     `CALENDAR_RETURN_UNIT_LABEL_KEYS`;
  >   - 1 E2E in `asset-detail.spec.ts` (`:7914-7969`): in italiano atteso `["1S","1M","3M","1A"]`, ricevuto
  >     `["1W","1M","3M","1Y"]`. Il valore atteso viene da `it.json`; c'è anche il controllo in inglese.
  > - **Cura**:
  >   - i preset hanno `count` e `unit` al posto di `label`;
  >   - il modulo esporta la mappa statica `CALENDAR_RETURN_UNIT_LABEL_KEYS` → `datePicker.presets.{weeks,months,years}`;
  >   - la pagina dell'asset scrive `$t(CALENDAR_RETURN_UNIT_LABEL_KEYS[preset.unit], {values: {n: preset.count}})`;
  >   - chiavi, `windowDays` e testid restano gli stessi. Prettier ha solo spezzato l'import, che si era allungato.
  > - **Gate**: `front check` 0/0; `core-unit` 3679/3679; `component-unit` 2975/2975; `asset-detail` 32/32;
  >   `i18n audit` 4347; `check-orphans` pulito; porte libere.
  > - Nella v1.1.0 questo modulo non c'era.
  >
  > ✅ (11/10) per tutti e tre i punti.
  >
  > **A margine** (dal test-author): restano in inglese altre etichette di `DataEditor`, fuori dalla lista del
  > coordinator. Sono l'intestazione «Date», i contatori «modified/deleted/new», un `aria-label` e «Reset layout».
  > Le segnalo.

**Chiusura del mini-lotto** (11/10). I punti 1–8 sono fatti: CHECKPOINT READY al coordinator, poi FROZEN.
- **CHANGELOG** (proposte, verificate sul tag v1.1.0):
  - 8.1 c'era già nella v1.1.0;
  - i punti 3–6 c'erano già nella v1.1.0, tranne `fx.rate`, nata nella 1.2;
  - per il punto 7 il conflitto è nato nella 1.2, con l'opzione Combine;
  - il punto 8 c'era già nella v1.1.0, tranne `calendarReturnWindow`, nato nella 1.2;
  - per il punto 2 non serve una riga.
- **Lasciato a dopo la 1.2**, con le righe proposte per la sezione P dell'indice:
  - P-13: le percentuali dei componenti condivisi della Dashboard (`KpiSection`: 7 siti senza `locale`);
  - P-14: «broker» senza accento in altre 46 chiavi di `es.json`, nomi propri esclusi;
  - P-15: altre etichette inglesi scritte nel codice, cioè in `DataEditor` «Date», i contatori, un `aria-label` e
    «Reset layout», e in `BrokerSharingPanel` «max».
