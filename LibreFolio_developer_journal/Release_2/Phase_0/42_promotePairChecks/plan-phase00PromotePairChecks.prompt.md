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
