# Piano — K / step 23: il Bulk, clone di righe singole (5) e falso «Scartare le modifiche?» (6)

> Lotto deciso dal developer (testuale, via coordinator, 09/10 11:36): «Sì: la 10 a I subito, la 5 e la 6 a K dopo il
> lotto attuale». Analisi approvata dal coordinator alle 11:59. Decisioni:
> - più di 2 righe con coppie dentro: sì, nello stesso lotto (stessa riga, stessa causa, voce 5);
> - la query sui dati con la procedura autorizzata della copia di prod; con coppie sbagliate ci si ferma;
> - la nota sull'`$effect` che legge `$currentLanguage` va nel backlog del coordinator.
>
> Viene dallo step 22
> ([`plan-phase00TaxonomySelectStep22RegisterLinkProfileDate.prompt.md`](plan-phase00TaxonomySelectStep22RegisterLinkProfileDate.prompt.md)).

| | |
|---|---|
| **Baseline** | `1ead733f2` = `dev_release2` (treno 23), pulita: contiene lo step 22 e il merge `cad759f9e`, entrato con `200b572b3`. Il treno 23 non tocca i file dello step. |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`, preambolo `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` |
| **Copia di prod** | 6165, `/tmp/librefolio-r2-k-prodcopy`: solo letture, mai un `dev.py test` |
| **Ordine** | spostamento neutro di `serializeOps`; rossi via test-author, solo file già registrati; cura; gate; checkpoint con il CHANGELOG sotto 🐛 Fixed |
| **Conflitti** | nessuno dei 17 rami locali tocca `TransactionBulkModal.svelte`, `bulkDisplay.ts`/`.test.ts`, `tx-clone.spec.ts`, `tx-bulk-row-order.spec.ts` e `brokers-detail.spec.ts` (09/10, 11:5x). Ultima modifica al modale: `a312797bf` (08/10) |

## Dati (voce 5)

- Copia di prod creata il 09/10 con la procedura autorizzata, poi rinfrescata alle 12:53 dalla base `1ead733f2`:
  `004_release_1_2_0_schema`; prod spento, niente WAL, niente marcatore. La copia precedente è
  `/tmp/librefolio-r2-k-prodcopy.prev-20261009-125338`.
- Solo conteggi:
  - 216 transazioni e 0 con `related_transaction_id`;
  - nessun tipo di coppia (TRANSFER, FX_CONVERSION, CASH_TRANSFER);
  - 0 coppie di tipo non di coppia, 0 collegamenti tra tipi diversi, 0 collegamenti a senso unico.
- **I dati del developer non hanno coppie sbagliate: nessuna riparazione da decidere.** Il difetto c'è dalla v1.1.0,
  quindi altre installazioni potrebbero averne; la query di rilevamento è sotto, per il backlog.
  ```sql
  SELECT a.type, COUNT(*) FROM transactions a JOIN transactions b ON a.related_transaction_id = b.id
  WHERE a.id < b.id AND a.type NOT IN ('TRANSFER','FX_CONVERSION','CASH_TRANSFER') GROUP BY a.type;
  ```
- **Lo Split non ripara una coppia di tipo non di coppia** (verificato nel codice, per il backlog): `apply_splits`
  (`transaction_batch_stages.py:240`) rifiuta con `TYPE_CANNOT_SPLIT` ogni tipo assente da `SPLIT_TYPE_MAP`
  (`transaction_service.py:704-708`: solo CASH_TRANSFER, TRANSFER e FX_CONVERSION). Un'installazione con coppie
  sbagliate avrebbe bisogno di una riparazione dedicata: azzerare il `related_transaction_id` dei due capi. Qui non
  serve: 0 coppie.

## Voce 5: due righe singole clonate dello stesso tipo diventano una coppia

- **Stato verificato sul codice**: `TransactionBulkModal.svelte:414`, nel ramo clone di `resolveInitialRows`:
  `sharedLinkUuid = resolved.length === 2 && resolved[0].type === resolved[1].type ? generateUUID() : null`.
  - Basta lo stesso tipo perché due righe ricevano lo stesso `link_uuid`. Il Pass 3 di `collapsePairedOps` (`:724-760`)
    le fonde in una riga accoppiata.
  - Al salvataggio `resolve_create_links` (`transaction_batch_stages.py:737-777`) scrive il `related_transaction_id`
    reciproco.
  - `_validate_linked_pair` (`transaction_service.py:168`) controlla lo stesso tipo, i broker diversi per
    TRANSFER/CASH_TRANSFER, e descrizione e tag identici. Non controlla che il tipo sia di coppia.
  - ~~Effetto: con descrizione e tag uguali, anche vuoti, due righe indipendenti finiscono collegate nel DB.~~
    **Corretto dal rosso C5a**: il payload non porta il `link_uuid` per i tipi che non sono di coppia
    (`buildCreatePayload`, `txPayloadHelpers.ts:256`: `if (fields.link_uuid && rule.requiresPair)`). Il DB quindi
    non si sporca, coerente con i conteggi a 0. Il difetto si vede nella griglia: due righe indipendenti appaiono come
    una coppia Da:/A:, e il form della coppia ne scrive i campi come se lo fossero.
- **Stessa riga, stessa causa**: con più di 2 righe nessun clone riceve il link. I due capi di una coppia arrivano
  scollegati, e il backend li rifiuta con `linkUuidRequired`. Il `link_uuid` non si salva: una riga letta non lo porta.
- **Già in v1.1.0**: `:376` sul tag.
- **Cura**: un `link_uuid` nuovo per ogni coppia del DB (`r` e `r.related_transaction_id`, entrambi nella selezione);
  le righe singole restano `null`. Vale per 2 righe come per N.

## Voce 6a: falso «Scartare le modifiche?» dopo Reset all o Reset riga su una coppia salvata

- **Stato verificato sul codice**: le tre cause del 25/09 (step 11, nota 11.1).
  - `resetAll` (`:910-921`) e `resetRow` (`:900-908`) rigenerano le righe modificate con `editOpFromTx`, cioè con
    `tempId` nuovi. Poi `collapsePairedOps`:
    1. dà un `link_uuid` nuovo ai due capi (`:672-675`, e nel Pass 2 `:705`/`:719`);
    2. mette nel `pairedWith` del partner il `tempId` nuovo della riga principale (`:671`);
    3. ricostruisce il partner del Pass 2 con un altro ordine di chiavi.
  - `serializeOps` (`:547-555`) toglie `tempId` e `createdSeq` solo al primo livello e usa `JSON.stringify` semplice.
- **Già in v1.1.0**: `serializeOps` a `:503`; `link_uuid` rigenerati a `:630`, `:648`, `:665`.
- **Cura**: un confronto canonico, che tocca solo la guardia di chiusura, non le righe né il payload.
  - `pairedWith` diventa `tx:<id>` per una riga modificata, `new:<tempId>` per una nuova (il reset non tocca le nuove).
  - `link_uuid` diventa l'etichetta dei suoi membri, ordinati.
  - Le chiavi si ordinano a ogni livello.
  - Prima uno spostamento neutro: `serializeOps` passa tale e quale in `utils/transactions/bulkDisplay.ts` (file di K
    dallo step 11; `bulkDisplay.test.ts` è registrato in `tx-unit`, `_frontend_transaction.py:20`). `stableJson`
    esiste, ma è privato in `charts/signals/requestBuilder.ts`, dominio di altri: non si tocca.

## Voce 6b: falso «Scartare le modifiche?» se il Bulk si apre prima della cache dei tipi

- **Stato verificato sul codice**: il percorso lento dell'apertura (`:480-497`) mette `ops = []` e `initialOpsKey = ''`,
  ma `serializeOps([])` dà `'[]'`.
  - Con righe (edit, clone, delete) la chiave si ricalcola dopo il caricamento (`:504-514`): il falso avviso c'è solo se
    si chiude prima.
  - Senza righe (create, import) non si ricalcola mai: ogni chiusura chiede conferma.
  - L'ha introdotto DD-BF3/F6 (Round6, bugfix1), che correggeva la prima apertura del Bulk.
- **Dove succede**: la pagina transazioni carica i tipi al mount (`transactions/+page.svelte:170`); la pagina di un
  broker no (`brokers/[id]/+page.svelte:104`/`:109`, create e import). Su una pagina broker aperta da zero, Aggiungi o
  Importa, poi chiudi: falso avviso, ogni volta finché un'altra pagina non carica i tipi.
- **Già in v1.1.0**: `:440` sul tag; la pagina broker apre già create e import (`:76`/`:81`).
- **Cura**: `initialOpsKey = serializeOps(ops)` anche nel percorso lento.

## Test (rossi prima, test-author; solo file già registrati)

1. **Voce 5**, `e2e/transactions/tx-clone.spec.ts` (`front-transaction tx-clone`):
   - due BUY singole create dal test, con la stessa descrizione → Clone (`toolbar-action-clone`) → nel Bulk restano 2
     righe indipendenti → dopo il salvataggio, via API, entrambe senza `related_transaction_id`;
   - una selezione mista, una coppia più una singola → la coppia clonata resta collegata e la singola no.
2. **Voce 6a**:
   - unità in `bulkDisplay.test.ts`, sulla funzione spostata: identità rigenerate → stessa chiave; modifiche vere (un
     campo, uno split, `markedDelete`, una riga aggiunta) → chiave diversa;
   - E2E in `tx-bulk-row-order.spec.ts`: una coppia FX_CONVERSION salvata, creata dal test. Reset all e Reset riga, con e
     senza modifica → chiusura senza conferma, con l'helper già presente (`:206-219`).
3. **Voce 6b**, E2E in `e2e/brokers/brokers-detail.spec.ts` (`front-broker detail`): un broker creato dal test, pagina
   aperta da zero → `broker-new-transaction` → si chiude il form aperto da solo → si chiude il Bulk: nessuna conferma.
   Lo stesso con `broker-import-transactions`. Deterministico: la cache dei tipi è del modulo, e a ogni caricamento
   parte vuota.

## Passi

- [x] 23.1 Base `1ead733f2` verificata pulita; copia di prod rinfrescata e conteggi; piano nel repo; il rimando dallo
  step 22. ✅ 2026-10-09.
- [x] 23.2 Spostamento neutro di `serializeOps` in `bulkDisplay.ts`; `tx-unit` e `front check` verdi. ✅ 2026-10-09.
  > **Note implementazione**:
  > - `bulkDisplay.ts`: `export function serializeOps(rows: readonly {tempId: string; createdSeq: number}[])`, corpo
  >   identico. Il tipo è generico, perché `PendingOp` è locale al componente.
  > - `TransactionBulkModal.svelte`: la funzione locale tolta; `serializeOps` importato con gli altri helper di
  >   `bulkDisplay`. Le tre chiamate (`:479`, `:514`, `:546`) non cambiano.
  > - Evidenze: `front check` 0/0 (`/tmp/libreFolio_k23_move_check.log`); `front-transaction tx-unit` 15 file e 685 test
  >   verdi (`/tmp/libreFolio_k23_move_txunit.log`). Prettier: nessuna modifica.
- [x] 23.3 Rossi (test-author). ✅ 2026-10-09.
  > **Note implementazione** (6a, test-author):
  > - `bulkDisplay.test.ts`: un `describe` nuovo con 17 test.
  >   - Comando: `node_modules/.bin/vitest run src/lib/utils/transactions/bulkDisplay.test.ts`: 5 rossi e 27 verdi; i 15
  >     test esistenti restano verdi (`/tmp/libreFolio_k23_red_6a_unit.log`).
  >   - I rossi isolano una causa ciascuno: (1) tempId e createdSeq rigenerati, con il partner che punta alla riga nuova;
  >     (2) un `link_uuid` nuovo su entrambi i capi; (3) il partner ricostruito nell'ordine di chiavi del Pass 2; (3b)
  >     le chiavi in un altro ordine a ogni profondità; (1+2+3) tutte insieme, come le restituisce Reset all.
  >   - I controlli, verdi oggi e dopo: una riga salvata non in coppia rigenerata, che dà la stessa chiave; poi, con
  >     chiave diversa: un campo cambiato (anche sul partner nascosto), l'ordine dei tag, `markedDelete`, una riga
  >     aggiunta o tolta, la coppia divisa, il partner accoppiato a un'altra riga, i link scambiati fra due coppie (9b),
  >     una coppia nuova ricollegata (9c). In più: `serializeOps` non modifica il suo input.
  >   - Verifica in `/tmp`, poi cancellata: un'implementazione di riferimento del contratto porta 32/32. Tre cure
  >     sbagliate (togliere i dati di coppia, ridurli a booleani, ordinare gli array) diventano rosse su almeno un
  >     controllo.
  > - `tx-bulk-row-order.spec.ts`: 3 test nuovi nel `describe` della guardia, ciascuno con il suo broker, un DEPOSIT e
  >   una coppia FX_CONVERSION salvata (EUR −400 / USD +440, in una sola richiesta con `link_uuid` condiviso).
  >   - Comando: `dev.py test --workers 2 --test-port 6155 --data-dir /tmp/librefolio-r2-k front-transaction
  >     tx-bulk-row-order`: 6 test, 4 verdi e 2 rossi (`/tmp/libreFolio_k23_red_6a_e2e.log`).
  >   - Rossi: E-reset-pair-all (modifica, Reset all, chiusura) ed E-reset-pair-row (segna da eliminare, Reset della riga
  >     dal menu `row-actions-<tempId>` → `context-menu-action-reset`, chiusura): `Expected "closed", Received "guard"`.
  >   - Verde, il controllo E-reset-pair-untouched: è il Reset che fa scattare la guardia, non la coppia.
  >   - `closeEditorWithoutGuard` ora dice cosa è successo (`closed`, `guard` od `open`): prima non distingueva «la
  >     guardia è scattata» da «il clic non ha fatto nulla». Gli helper del file sono stati generalizzati, e i 3 test
  >     esistenti restano verdi.
  >   - A fine corsa, nel DB della corsia, 0 broker `E-reset%` e 0 transazioni del test.
  > **Note implementazione** (5 e 6b, un secondo test-author):
  > - `tx-clone.spec.ts`: C5a e C5b, con broker, sorgenti e cloni propri, ripuliti dal tracker e per id.
  >   - Comando: `dev.py test --workers 2 --test-port 6155 --data-dir /tmp/librefolio-r2-k front-transaction tx-clone`:
  >     8 test; i 6 esistenti verdi, C5a e C5b rossi (`/tmp/libreFolio_k23_red_clone_e2e.log`).
  >   - C5a, due DEPOSIT singoli con la stessa descrizione: la griglia mostra una coppia, con le date dei partner
  >     `['2023-05-17']` invece di `['', '']`. Il salvataggio riesce, e i due cloni nel DB non sono collegati: il
  >     controllo sul DB resta come guardia.
  >   - C5b, una coppia FX_CONVERSION più un DEPOSIT: la griglia mostra 3 righe sciolte; il salvataggio è rifiutato,
  >     `committed: false`, con due `linkUuidRequired` («FX_CONVERSION requires link_uuid for pairing»).
  > - `brokers-detail.spec.ts`: B6a (Nuova transazione) e B6b (Importa), su una pagina broker caricata da zero e un broker
  >   del test.
  >   - Comando: `dev.py test … front-broker detail`: 35 test; i 33 esistenti verdi, B6a e B6b rossi
  >     (`/tmp/libreFolio_k23_red_6b_e2e.log`).
  >   - Il rosso: alla chiusura del Bulk vuoto, `Expected "closed", Received "discard guard"`.
  >   - La premessa è vera e controllata: la pagina broker non chiede i tipi prima del clic (0 richieste); il Bulk li
  >     chiede da sé dopo l'apertura.
  > - Trovato dal test-author, per il backlog: nel percorso lento, a caricamento finito, il Bulk riapre il form o il
  >   wizard aperto da solo, se l'utente l'ha già chiuso (`if (!formOpen) scheduleAutoOpen(…)`). I test B6 aspettano la
  >   fine del caricamento prima di chiudere.
  > **⚠️ Fuori pista** (trovato dal test-author, riferito al coordinator alle 13:3x):
  > - `resetRow` rigenera solo la riga visibile di una coppia salvata. Una modifica fatta con il form della coppia resta
  >   sul capo nascosto: dopo il Reset della riga la validazione invia ancora `updates:[{id:<capo nascosto>, …}]`, e la
  >   conferma di chiusura è vera. Proposta: includerlo come 6c. Per questo E-reset-pair-row usa «segna da eliminare»,
  >   che tocca solo la riga visibile e isola la 6a.
  > - Un crash latente letto nel codice: `resetAll` passa il segnaposto `inaccessible` della W4b a `editOpFromTx`, che
  >   fa `txStoreGet(...)!` → `fieldsFromTx(undefined)`. Proposto per il backlog.
  > **Note implementazione** (rosso 6c, lo stesso test-author della 6a):
  > - `tx-bulk-row-order.spec.ts`: E-reset-pair-row-edited ed E-reset-pair-selected-edited. Con il form della coppia si
  >   modifica la descrizione, poi si fa il Reset della riga, dal menu nel primo test e con `tx-bulk-reset-selected` nel
  >   secondo.
  >   - Comando: `dev.py test … front-transaction tx-bulk-row-order`: 8 test, 6 verdi e 2 rossi
  >     (`/tmp/libreFolio_k23_red_6c_e2e.log`). E-reset-pair-all ed E-reset-pair-row sono già verdi con la cura 6a.
  >   - I rossi:
  >     - (a) l'ultima validazione dopo il Reset è `updates: [{id: <capo nascosto>, description: "… changed …"}]`;
  >     - (b) `tx-bulk-reset-all` resta visibile, ed è un segnale affidabile: il pulsante c'è solo finché una riga
  >       differisce dal registro;
  >     - (c) alla chiusura `Received "guard"`.
  >   - La validazione si legge senza attese a tempo: si registrano le richieste da prima del Reset, si attende che salga
  >     il contatore `data-validate-runs` e che l'editor sia fermo.
  >   - La riga visibile mostra di nuovo la descrizione salvata: il rosso riguarda solo il capo nascosto.
  > - Avvertenza del test-author, seguita nella cura: la chiave 6a tiene l'ordine delle righe, quindi il capo nascosto si
  >   rigenera al suo posto, non in fondo.
- [x] 23.4 Cura: il clone per coppie del DB; `serializeOps` canonica; `initialOpsKey` nel percorso lento; `resetRow` sulle coppie. ✅ 2026-10-09.
  > **Note implementazione** (6a):
  > - `bulkDisplay.ts`: `serializeOps(rows: readonly GuardKeyRow[])` canonica:
  >   - toglie `tempId` e `createdSeq`;
  >   - `pairedWith` diventa `tx:<txId>` o `new:<tempId>`;
  >   - `link_uuid` diventa la lista ordinata dei riferimenti dei membri, o `null`;
  >   - le chiavi sono ordinate a ogni profondità (`sortedKeys`), l'ordine degli array resta.
  > - Il componente non cambia: le righe e il payload non sono toccati, cambia solo la chiave della guardia.
  > - `vitest bulkDisplay.test.ts`: 32/32 (`/tmp/libreFolio_k23_green_6a_unit.log`).
  > **Note implementazione** (5 e 6b):
  > - 5, `resolveInitialRows` (clone): al posto della regola «2 righe dello stesso tipo», `cloneLinks` dà un
  >   `link_uuid` nuovo a ogni coppia del DB con entrambi i capi selezionati (`r.related_transaction_id` presente
  >   nella selezione); le righe singole non ne hanno. Vale per 2 righe come per N.
  > - 6b, il percorso lento dell'apertura: `initialOpsKey = serializeOps(ops)` con `ops = []`, invece di `''`.
  > **⚠️ Decisione del coordinator** (13:26): la 6c entra nel lotto, con un rosso E2E che copre anche «Reset selected» e
  > la guardia `inaccessible` in `resetRow`. Il crash di `resetAll` entra solo se esiste già un modo ragionevole per
  > ottenere un rosso; altrimenti va nel backlog.
  > - Verifica nel codice: nessun ingresso della UI apre nel Bulk una coppia con un capo inaccessibile. Le azioni di
  >   riga Edit e Delete richiedono `rowAccessLevel === 'full'` (`TransactionsTable.svelte:906-940`); l'Edit della
  >   toolbar filtra con `txStoreCanEdit`, che vuole entrambi i broker modificabili (`txStore.svelte.ts:63-73`); il
  >   picker disabilita entrambi i capi (`TransactionPickerModal.svelte:52-73`). La coppia di prova dei mock
  >   («[Asym-d]», IB ↔ Hidden Admin Broker) è proprio «locked».
  > - Quindi il rosso non è ragionevole: il crash di `resetAll` va nel backlog.
  > **Note implementazione** (cura 6c): `resetRow` rigenera, al suo posto (`ops.map`), anche il partner nascosto della
  > riga (`getPartnerOp(tempId)`), saltando i segnaposto `inaccessible`, poi rifà il collasso. «Reset selected» chiama
  > `resetRow` riga per riga, quindi la stessa cura copre entrambi.
- [x] 23.5 Gate, corsia 6155, in sequenza: ✅ 2026-10-09.
  - `front build --debug`, `front check`;
  - `front-transaction tx-unit`, `front-utility core-unit` e `component-unit`;
  - E2E `tx-clone`, `tx-wac-bulk`, `tx-bulk-row-order`, `tx-bulk-operations`, `tx-split-promote`, `tx-bulk-suggest-ux`,
    `tx-bulk-promote-exec`, `transactions-modals`, `front-broker detail`; `check-orphans`.
  > **Note implementazione**:
  > - Comando: `/tmp/libreFolio_k23_gates.sh`, log `/tmp/libreFolio_k23_gates.log`; E2E con `--workers 2`.
  > - Risultati:
  >   - build ok, svelte-check 0/0; `front check` 0/0;
  >   - `tx-unit` 15 file, 702 verdi; `core-unit` 119 file, 3494; `component-unit` 111 file, 2927;
  >   - `tx-clone` 8/8, con C5a e C5b; `tx-wac-bulk` 10/10, compreso «clone link_uuid»;
  >   - `tx-bulk-row-order` 8/8, con la 6a e la 6c; `tx-bulk-operations` 10/10; `tx-split-promote` 6/6;
  >   - `tx-bulk-suggest-ux` 8/8; `tx-bulk-promote-exec` 9/9; `transactions-modals` 19/19;
  >   - `front-broker detail` 35/35, con B6a e B6b;
  >   - `check-orphans` ok; a fine corsa nessun ascoltatore su 6155.
  > - Nessun rosso e nessun rilancio.
- [x] 23.6 Handoff: CHECKPOINT READY con le righe del CHANGELOG sotto 🐛 Fixed, poi FROZEN. ✅ 2026-10-09.
  > **Note implementazione**:
  > - Due commit proposti in `/tmp/libreFolio_commits/`, manifesto `k-23-manifest.txt`:
  >   - `k-65-bulk-clone-reset-guard.txt`;
  >   - `k-66-journal-23.txt`.
  > - Lo spostamento neutro e le quattro cure stanno negli stessi due file, `TransactionBulkModal.svelte` e
  >   `bulkDisplay.ts`: dividerli richiederebbe uno stage per blocchi, quindi un solo commit `fix`.
  > - Verificate sul tag v1.1.0 tutte e quattro: il clone a `:376`, `serializeOps` a `:503`, il percorso lento a `:440`,
  >   `resetRow` a `:855-863`. Nella v1.1.0 il payload scartava già il `link_uuid` dei tipi non di coppia (`:204`).
  > - Backlog, da riferire:
  >   - il crash latente di `resetAll` sul segnaposto `inaccessible`, oggi irraggiungibile dalla UI;
  >   - nel percorso lento il form o il wizard aperti da soli si riaprono, se l'utente li chiude prima della fine del
  >     caricamento;
  >   - una riparazione dedicata per le coppie di tipo non di coppia, se un'altra installazione ne avesse: lo Split non
  >     le accetta (`TYPE_CANNOT_SPLIT`).

## Definizione di fatto

1. Ogni test nuovo è rosso sulla base, per la ragione attesa, e verde dopo la cura.
2. I gate sono verdi e `front check` resta a 0/0.
3. Nessun catalogo, nessun file del runner; porte libere, nel worktree solo i file previsti.
