# Piano — 40: costo dei transfer in Auto e dei promote

> **Stato: ✅ completato e integrato** nel **treno 28**: commit `d7c148564` (`fix(transactions): transfer auto cost
> and promote`), merge `2a5c15c3c`, `dev_release2` = `fbb57eb41`. Archiviato il 10/10 in
> `Release_2/phases/40_transferCostBasis/` (§7).
>
> Workstream **P**, lotto per la 1.2. Coordinator: sessione `c8328a01-f208-4ade-a352-0486d1f14de2`.
>
> **Origine.** Tre difetti del costo medio segnalati da Q, che li aveva letti nel codice senza provarli. Il 09/10 P li
> ha verificati con dei rossi; il rapporto è riassunto in §1.
>
> **Decisione del developer** (09/10), testuale. Prima domanda: «chat il punto 1 mi pareva che avvenisse già, gli
> altri 2 riguardano dati modificati dopo il salvataggio, quindi più che altro la ui deve ricordarlo e chiedere di
> metterlo, o sbaglio?». Dopo i chiarimenti, la scelta: **«Correggere 1 e 2 nel backend con una sola cura, e 3
> facendo chiedere il costo anche col promote (Consigliato)»**.
>
> Base: `dev_release2` @ `083ed26dc`, HEAD verificato uguale. Nel worktree ci sono solo i rossi della verifica (2 file
> di test, non committati). Corsia `--test-port 6161 --data-dir /tmp/librefolio-r2-p`, un comando alla volta.
>
> **Superfici.**
> - Mie: `transaction_service.py`, `transaction_batch_stages.py`, `transaction_batch_context.py` e `average_cost.py`.
> - Doc: `developer/backend/transactions/wac.md`, solo EN.
> - Di S, solo chiedendo prima: `TransactionBulkModal`, `ImportWizardModal` e i cataloghi.
> - `user/transactions/form.en.md` è di Q, e la sua modifica entra nel treno 27: se serve, si aspetta quel treno.

## 1. Stato verificato (rapporto del 09/10)

Sul codice di `083ed26dc`, tutti e tre i difetti esistevano già nella v1.1.0.

1. **Transfer in Auto di un'intera posizione: costo 0 sul broker che riceve.**
   - Per un ricevente creato insieme al suo partner, la fonte è il broker del partner e non si esclude nulla
     (`transaction_service.py:994`).
   - La facciata (`portfolio_service.py:122`) legge le righe del broker d'origine fino alla data, compresa la gamba in
     uscita dello stesso transfer. Quella riduzione svuota la pool, e il costo va a 0 (`average_cost.py:407-423`).
   - Il WAC 0 viene scritto (`:1012-1014`). Un transfer parziale invece dà il risultato giusto (P16).
   - Rossi: P30 (validate) e P31 (commit), che danno 0 invece di 100.
   - v1.1.0: il nucleo faceva `new_qty == 0 → wac = 0`, con la stessa esclusione (`:1655`).
2. **Un transfer esistente aggiornato in Auto fa la media sul broker che riceve.**
   - `TXUpdateItem` non ha `link_uuid` (`schemas/transactions.py:533-585`), quindi la fonte è il broker della riga
     stessa (`transaction_service.py:956-962`); `related_transaction_id` non è usato.
   - Rosso P32: fonte B, WAC 200 invece di 100.
   - **Stessa causa, seconda via**: il promote di una riga salvata con una riga nuova in Auto. Il `link_uuid` della
     riga nuova non ha partner fra le creazioni (`_resolve_source_broker_from_link`, `:1061-1078`). Rosso P33: fonte B,
     WAC 0 invece di 100.
   - v1.1.0: `:1617-1623`.
3. **Il promote salta il controllo del costo.**
   - `validate_cost_basis` salta le creazioni consumate da un promote (`transaction_batch_stages.py:845-866`) e non
     guarda mai le righe salvate che vengono promosse.
   - `_apply_promote_cost_basis` (`:701-729`) mette il costo del ricevente a None se `resolved_fields` porta un costo
     null.
   - Rossi:
     - R3a: due righe salvate e costo risolto null. Arriva solo dall'API: la modale di merge non manda costi dal 15/05.
     - R3b: una riga salvata −5 e una riga nuova +5 senza costo. Arriva dalla UI del Bulk.
   - Controllo C0 (verde): un ADJUSTMENT +5 da solo, senza costo, è rifiutato con `costBasisRequired`.
   - La doc `wac.md:423-424` dice il contrario.
   - v1.1.0: `:1471-1500`.

**Prova dei rossi** (09/10, corsia 6161):
- `api transactions-wac`: 14 passati, 4 falliti (P30–P33);
- `api batch-split-promote`: 23 passati, 2 falliti (R3a, R3b);
- i log sono in `/tmp/libreFolio_p_reds_wac_inline.log` e `/tmp/libreFolio_p_reds_promote.log`.

**Test che fissano il comportamento di oggi** (da adattare dopo la cura 3):
- `test_transactions_batch_split_promote.py::test_commit_promote_new_new` (B2.2) promuove un ADJUSTMENT nuovo +3
  **senza costo**, e si aspetta il commit. Con la cura il commit viene rifiutato. L'intento del test è il link senza
  riprocesso, e resta: al +3 si dà un costo.
- `test_transaction_service.py::test_resolve_source_broker_from_link_prefers_partner_then_self_fallback` (`:336`)
  copre l'helper che la cura 1+2 rende inutile.

## 2. Progetto

### 2.1 Cura unica per 1 e 2: la fonte è il partner, senza la sua gamba in uscita

In `_compute_wac_for_auto_items`, il ricevente di un TRANSFER, qualunque sia la sua strada, prende la fonte dal
partner:
- un partner creato nello stesso batch: `resolve_create_links` ha già scritto `related_transaction_id`;
- un transfer salvato e aggiornato: `related_transaction_id` è nel DB;
- una coppia del promote: `apply_promotes` ha già scritto `related_transaction_id`.

Lo stage dei link e quello dei promote girano **prima** del WAC (`execute_batch`: create → promote → link → WAC), quindi
un solo criterio basta: `related_transaction_id`.

- Fonte = il broker del partner.
- Escluse = la riga stessa e **la gamba in uscita del partner**. La media è quella della pool d'origine prima del
  transfer.
  - Un transfer parziale non cambia: una riduzione non muove il costo unitario (P16).
  - Un ADJUSTMENT senza partner resta com'è: il broker proprio, esclusa la riga stessa.
- `_resolve_source_broker_from_link` non serve più: si toglie, e con lui il suo test unitario.
- `average_cost.py` non cambia.

### 2.2 Cura per 3: il controllo del costo vale anche per i riceventi promossi

In `validate_cost_basis`:
- **Creazioni promosse**: non si saltano più. Una riga nuova che il promote fa diventare un TRANSFER in entrata, senza
  costo e non in Auto, riceve `costBasisRequired` sull'operazione `create`, con il suo indice. Così la UI del Bulk la
  mostra come oggi. `_check_linked_create_cost_basis` continua a saltare i `link_uuid` consumati, quindi l'issue non
  si ripete.
- **Righe salvate promosse**:
  - per ogni promote riuscito, ogni riga salvata della coppia (`context.existing_by_id`) che richiede un costo e non
    ce l'ha riceve `costBasisRequired`, sull'operazione `promote` con l'indice del promote e `ref_id` = la riga;
  - le righe già controllate come update si saltano.
- Stessa forma dell'issue di oggi (`_append_cost_basis_issue`). Nessuno schema nuovo e nessuna chiave i18n: il testo
  `transactions.errors.costBasisRequired` va bene così.

### 2.3 Nessun cambio a

- la facciata e i suoi altri chiamanti (`POST /portfolio/wac`, la PAC);
- Auto senza posizione, che resta 0 per la decisione P-1 (`phases/39_autoCostNoPosition/`);
- il frontend e i cataloghi.

## 3. Test (`test-author`, solo file già registrati)

- **Da far diventare verdi**: P30–P33 (`api transactions-wac`); C0 resta verde; R3a e R3b (`api batch-split-promote`).
- **Da aggiungere**:
  - **P34**: update in Auto del ricevente di un transfer che ha spostato **tutta** la posizione → fonte A, WAC 100.
    Copre esclusione e update insieme. Rosso oggi.
  - **P35** (aggiunto dopo il codice, vedi T2): transfer «in viaggio» con un BUY sul broker d'origine fra le due
    date → WAC 100, cioè la pool quando le quote escono.
  - **Controlli verdi**:
    - un promote di due ADJUSTMENT salvati in cui il ricevente tiene il suo costo → commit;
    - un promote di una riga salvata e di una nuova con costo → commit.
- **Da adattare**:
  - B2.2: al +3 si dà un costo;
  - il test unitario dell'helper tolto: va tolto o sostituito.
- **Regressioni**:
  - API: `api transactions-wac`, `api batch-split-promote`, `api portfolio-wac`, `api transactions`, `api brokers`,
    `api transfer-promotion`;
  - servizi: `services financial-math`, `services transaction`;
  - E2E: `front-transaction tx-wac-mode`, `tx-bulk-promote-exec`, `tx-split-promote`, dopo `front build --debug`.

## 4. Passi

- **T0** ✅ (09/10): base verificata, piano.
  > **Note implementazione**: HEAD = `dev_release2` = `083ed26dc`; nel worktree ci sono solo i 2 file di test con i
  > rossi della verifica; porta 6161 libera. Gli E2E del promote (`tx-bulk-promote-exec`, `tx-split-promote`) usano
  > solo coppie di cassa (CASH_TRANSFER): la cura 3 non li tocca.
- **T1** ✅ (09/10): test-author. Aggiunte P34 e i controlli; adattati B2.2 e il test dell'helper; rosso visto.
  > **Note implementazione**:
  > - Nuovi test:
  >   - P34 `test_wacp34_update_full_position_transfer_receiver_auto_uses_source_wac` (`test_wac_inline.py:786-838`);
  >   - G1 `test_promote_saved_saved_adjustments_keep_receiver_cost` (`test_transactions_batch_split_promote.py:960-1024`);
  >   - G2 `test_promote_saved_new_with_cost_basis_commits` (`:1026-1097`).
  > - Adattati:
  >   - B2.2: il +3 ha un costo USD 50, e un commento dice perché;
  >   - tolto il test unitario di `_resolve_source_broker_from_link`.
  > - **Rosso visto prima del codice**:
  >   - `api transactions-wac`: 14 passati, 5 falliti (P30–P34; P34 dà fonte B e 200 invece di A e 100);
  >   - `api batch-split-promote`: 25 passati, 2 falliti (R3a, R3b; C0, G1, G2 e B2.2 verdi);
  >   - `services transaction`: 66 su 66.
  > - Ruff e black puliti. Log in `/tmp/libreFolio_p40_t1_*.log`.
- **T2** ✅ (09/10): cura 1+2 (`transaction_service.py`).
  > **Note implementazione**:
  > - Nuovo `_auto_cost_source(db_tx)`, che dà broker, righe escluse e data della media:
  >   - per un ricevente TRANSFER con `related_transaction_id`: il broker del partner, escluse la riga e la gamba in
  >     uscita del partner, **fino alla data del partner**;
  >   - per tutte le altre righe: il broker proprio, esclusa la riga, fino alla sua data.
  > - Tolto `_resolve_source_broker_from_link`; aggiornata la docstring di `_compute_wac_for_auto_items`.
  > - La soppressione C901 resta: la complessità scende ma resta 13, sopra la soglia di 10.
  >
  > **⚠️ Fuori pista: la data.** Oltre al partner e all'esclusione della sua gamba, la media si prende alla **data del
  > partner**, cioè quando le quote escono, e non alla data del ricevente.
  > - Con le due date uguali, il caso comune, non cambia nulla.
  > - Cambia per un transfer «in viaggio» con altri movimenti sul broker d'origine fra le due date. Esempio: BUY 10 a
  >   100, uscita il 01/04, BUY 5 a 300 il 03/04, ricevente il 05/04.
  >   - Oggi il ricevente prende 200.
  >   - Escludendo solo la gamba prenderebbe 166,67.
  >   - Con la data del partner prende 100, il costo vero delle quote spostate.
  > - È nello spirito della cura («la media della pool d'origine prima del transfer»), ma va detto al coordinator.
  >   La copre P35, scritto dopo il codice; il rosso di prima è dimostrato con il calcolo qui sopra.
- **T3** ✅ (09/10): cura 3 (`transaction_batch_stages.py`).
  > **Note implementazione**:
  > - `validate_cost_basis` non salta più le creazioni promosse: `_check_result_create_cost_basis` le controlla come
  >   le altre creazioni, e restano escluse solo quelle in Auto.
  > - Nuovo `_check_promoted_saved_cost_basis`: per ogni promote riuscito controlla le righe salvate della coppia
  >   (`existing_by_id`), escluse quelle già controllate come update. L'issue è sull'operazione `promote`, con
  >   l'indice del promote e `ref_id` = la riga.
  > - Stessa forma dell'issue (`_append_cost_basis_issue`); nessuno schema e nessuna chiave nuova.
  > - Ruff e black puliti sui due file di prodotto.
  > - **Verde**: `api transactions-wac` 19/19 (P30–P34 compresi); `api batch-split-promote` 27/27 (R3a, R3b, C0, G1,
  >   G2 e B2.2 compresi).
- **T4** ✅ (09/10): doc `wac.md` (`docs-writer`, EN), poi `mkdocs build` e `check-links`.
  > **Note implementazione**:
  > - `developer/backend/transactions/wac.md` (+50/−11):
  >   - nella tabella dei chiamanti della facciata, la data per il ricevente di un TRANSFER;
  >   - il paragrafo del costo richiesto, ora vero anche per i promote, con l'elenco delle vie che restano per un
  >     costo sconosciuto (dati scritti fuori dal batch o da versioni vecchie, e lo SPLIT riclassificato, P-10);
  >   - la regola di `_auto_cost_source()` al posto dei due punti su `link_uuid`;
  >   - il controllo dei promote nel «Promote boundary»;
  >   - due ancore esplicite, con gli stessi id di prima.
  > - Verifiche: `mkdocs build` strict passa; `check-links` ha 90 link validi, 3 eccezioni note e 1 link rotto
  >   preesistente (`user/assets/detail/chart/#rolling-return`); `git diff --check` pulito.
  >
  > **⚠️ Fuori pista**: il docs-writer ha trovato altre tre pagine che descrivono il comportamento vecchio. Non le ho
  > toccate perché sono fuori dalle mie superfici; le porto al coordinator col testo proposto:
  > - `developer/architecture/database/brokers_transactions.md:154-155`, che è falsa: dice ancora `link_uuid_map`
  >   e il broker proprio;
  > - `developer/backend/transactions/split_promote.md:175-181`, che non è falsa ma è incompleta;
  > - `financial-theory/.../weighted-average-cost.en.md:114`, con traduzioni IT/FR/ES (servirebbero le 4 lingue e
  >   lo stamp).
  > - C'è poi un errore più vecchio, che non tocco: `brokers_transactions.md:156-157` dice che è
  >   `compute_wac_iterative()` a scrivere il costo.
  >
  > **Seguito (09/10, dopo il via del coordinator).** Il developer conferma la data: «Alla data in cui le quote
  > escono dal broker d'origine (Consigliato)». La scelta di T2 resta, con P35. Il coordinator approva le bozze del
  > docs-writer, che le applica in inglese, senza aggiunte facoltative e senza stamp:
  > - `brokers_transactions.md:154-161`: la regola di `_auto_cost_source()` e l'errore più vecchio corretto. Il costo
  >   lo scrive `_compute_wac_for_auto_items()`, mentre `compute_wac_iterative()` lo legge e lo restituisce;
  > - `split_promote.md`, «Cost basis boundary»: senza la chiave il ricevente tiene il suo costo; un ricevente in Auto
  >   di un promote prende la media del partner; `validate_cost_basis()` controlla il lato che riceve;
  > - `weighted-average-cost.en.md:114`: per un transfer, la pool d'origine quando le quote escono, prima della gamba in
  >   uscita. Le traduzioni IT/FR/ES restano debito per il giro I-08.
  > - Verifiche: `mkdocs build` strict passa; `check-links` ha solo il rotto preesistente `#rolling-return`;
  >   `git diff --check` pulito.
- **T5** ✅ (09/10): gate, lint e format, `git diff --check`, porta libera.
  > **Note implementazione** (corsia 6161, un comando alla volta; log in `/tmp/libreFolio_p40_t5_*.log`):
  > - Backend:
  >   - `api transactions-wac` 20/20, con P35 scritto dopo il codice (T2, fuori pista);
  >   - `api batch-split-promote` 27/27; `api portfolio-wac` 12/12 (A1 e SPLIT invariati);
  >   - `services financial-math` 39/39; `services transaction` 66/66;
  >   - `api transactions` 23/23; `api brokers` 29/29; `api transfer-promotion` 3/3.
  > - `front build --debug` OK.
  > - E2E `front-transaction`:
  >   - `tx-wac-mode` 5/5, `tx-bulk-promote-exec` 9/9, `tx-split-promote` 6/6;
  >   - in più, perché la cura cambia la fonte del WAC: `tx-wac` 7/7, `tx-wac-bulk` 10/10, `tx-wac-formmodal` 10/10.
  > - Ruff e black puliti su prodotto e test; porta 6161 libera dopo ogni giro.
- **T6** ✅ (09/10): CHECKPOINT READY con le righe del CHANGELOG (§5), poi FROZEN.
  > **Note implementazione**: checkpoint mandato al coordinator, con il manifesto e il messaggio di commit
  > (`/tmp/libreFolio_commit_p40.txt`). I due punti aperti sono chiusi lo stesso giorno: il developer ha confermato
  > la data, e le tre pagine di doc sono applicate (T4, «Seguito»). Il CHANGELOG lo scrive il coordinator nel treno
  > 28. Il checkpoint è stato mandato di nuovo con il manifesto aggiornato.

## 5. CHANGELOG proposto (`[1.2.0]`, 🐛 Fixed → «📥 Imports and transaction editing»)

C'era già nella v1.1.0.

> - **An asset transfer in *Auto* keeps the cost of the shares it moves.** Moving a whole position to another broker
>   with the cost basis in *Auto* gave the receiving broker a cost of 0, so the shares' whole value counted as gain;
>   switching an existing transfer, or a pair made with **🔗 Promote pair**, to *Auto* averaged the receiving broker
>   instead of the one the shares came from. The receiving side now takes the sending broker's average cost at the
>   moment the shares left; partial transfers keep the value they had.
> - **Promoting two rows into a transfer asks for the cost basis.** A promoted pair whose receiving side had no cost
>   basis was saved anyway and then counted at zero; it is now refused with the usual message asking for a cost
>   basis, like any other transaction.

## 6. Definizione di fatto

- Ogni ricevente di un TRANSFER in Auto prende la media del broker d'origine prima del transfer. Vale per la coppia
  nuova, per il transfer salvato e aggiornato, e per il promote. Il transfer intero dà il costo vero; il parziale non
  cambia.
- Un promote che lascia senza costo un TRANSFER in entrata riceve `costBasisRequired` e non si salva.
- Rossi verdi; regressioni verdi; doc allineata; righe del CHANGELOG pronte; porta 6161 libera; FROZEN.

## 7. Integrazione e archivio (10/10)

- **Integrazione**: il checkpoint (manifest di 10 percorsi) è entrato nel treno 28 come commit `d7c148564`, merge
  `2a5c15c3c`; la punta di `dev_release2` è `fbb57eb41`. Il CHANGELOG `[1.2.0]` l'ha scritto il coordinator nel treno.
- **Debito di traduzione** (unico residuo): `financial-theory/technical-analysis/performance-metrics/weighted-average-cost`
  è cambiata solo in inglese (riga 114: per un transfer, la data d'uscita prima della gamba in uscita), senza stamp.
  Le versioni IT/FR/ES vanno aggiornate nel **lotto 11 di M** (le traduzioni).
- **Esito**: FINITA, archiviata intera in `Release_2/phases/40_transferCostBasis/`. I due link in ingresso
  (`Phase_0/38_postReleaseBacklog/README.md:506` e `phases/00-index.md:48`) sono del coordinator.
