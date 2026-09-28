# Piano — K / step 11: ordine di creazione nel comparatore del Bulk (C4)

> Difetto trovato da J (FM7 intermittente). Assegnato a K dal developer il 25/09: «Sì: ordine di creazione
> nel comparatore e test per contenuto, a K dopo C3». Viene dopo lo step 10
> ([`plan-phase00TaxonomySelectStep10BrokerRequestBurst.prompt.md`](plan-phase00TaxonomySelectStep10BrokerRequestBurst.prompt.md)).

| | |
|---|---|
| **Baseline** | `d318311df` (C3 committato: `7000f8d02`, `d318311df`) |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k` |
| **File di K in esclusiva** | `utils/transactions/bulkDisplay.ts` (+ test), `TransactionBulkModal.svelte` (solo per questo), `e2e/transactions/tx-wac-bulk.spec.ts`, `e2e/transactions/tx-wac-formmodal.spec.ts` |
| **Condivisi, solo in aggiunta** | `scripts/test_runner/_frontend_transaction.py` (registrazione dell'eventuale spec nuova) |

## Il difetto

- `createBulkDateComparator` (`bulkDisplay.ts:62-80`, da `ef722b552`) ordina i gruppi visibili per data
  minima, poi per data massima, poi per `txId`, e infine per `compareText(a.tempId, b.tempId)`.
- Una riga nuova non ha `txId` (vale `MAX_SAFE_INTEGER`), e il suo `tempId` è un UUID casuale
  (`generateUUID()`). Quindi due righe nuove della stessa data escono in ordine casuale.
- `visibleOps` (`TransactionBulkModal.svelte:280`) applica il comparatore alle sole righe visibili. In
  ordine discendente lo nega per intero.
- Per l'utente: se aggiunge due righe dello stesso giorno, a volte la seconda finisce sopra la prima.
- Per i test: FM7 (`tx-wac-formmodal.spec.ts:377`) apre `rows.nth(lastIdx)` convinto che sia il
  TRANSFER, e una volta su due apre il BUY. WB2 (`tx-wac-bulk.spec.ts:253`), WB3 (`:304`, `:320`) e WB8,
  WB9 e WB10 hanno la stessa firma.

## Analisi: dove nasce una riga

`ops` è il registro nell'ordine di arrivo: il payload lo segue, la vista no. Ogni `PendingOp` nasce in
uno di questi punti:

| punto | riga | tipo |
|---|---|---|
| `createOpEmpty()` | `:209` | create vuota: aggiunta, `addRowFromForm`, split, dual |
| `editOpFromTx()` | `:254` | edit di una riga del DB: intent edit/delete, picker, suggerimento, reset |
| `createOpFromClone()` | `:260` | create clonata da una riga: intent clone |
| `collapsePairedOps()` | `:684`, `:701` | partner nascosti (segnaposto inaccessibile, edit del partner) |
| `cloneRow()` | `:867`, `:876` | clone e partner clonato |
| `txCreateItemToPendingOp()` | `:2237` | righe dal file (`onImportBatch`), nell'ordine del wizard |

- **Righe da file**: arrivano in lotto, nell'ordine di `buildFinalTxList`, cioè quello del file.
  `linkPairedImportOps` rende nascosta la seconda di ogni coppia con lo stesso `link_uuid`. La riga
  visibile è la prima in ordine di file.
- **Righe modificate**:
  - un edit si ordina per `txId`, unico e stabile, e resta com'è;
  - una create modificata tiene la sua posizione di creazione; cambiare un campo, anche la data, non
    la fa rinascere;
  - `resetRow` e `resetAll` rigenerano gli edit con `editOpFromTx`, ma per un edit decide il `txId`,
    quindi la sequenza nuova è irrilevante.
- **Coppie**: il comparatore raggruppa per `pairedWith ?? tempId` per calcolare le date del gruppo, e
  confronta solo righe visibili. Una coppia si colloca con la data minima e massima dei due capi, poi con
  il `txId` o la sequenza della riga visibile. Il partner nascosto non entra mai nel confronto.
  Invariati sono l'orientamento From/To e l'etichetta 1a/1b (`buildBulkRowLabels`).
- **`serializeOps`** (`:536`) esclude `tempId` perché rimettere nel draft le stesse righe, o un
  `resetAll`, non deve contare come modifica. Deve escludere anche la sequenza nuova: dopo un reset la
  riga ne ha una diversa, e la guardia di chiusura vedrebbe modifiche che non ci sono.

## Cura approvata

1. **`bulkDisplay.ts`**: `BulkDisplayRow` riceve un campo opzionale `createdSeq?: number`. Il comparatore
   ha un nuovo spareggio **dopo il `txId` e prima del `tempId`**: `(a.createdSeq ?? MAX) - (b.createdSeq ??
   MAX)`. Il `tempId` resta l'ultima risorsa per le righe senza sequenza; il test che c'è già non cambia.
2. **`TransactionBulkModal.svelte`**:
   - un contatore del componente, `nextCreatedSeq()`;
   - `createdSeq` diventa **obbligatorio** su `PendingOp`, così svelte-check segnala ogni punto di
     nascita dimenticato, e viene assegnato negli 8 punti della tabella;
   - `serializeOps` lo esclude, come il `tempId`.
3. **E2E**: FM7 e i WB scelgono la riga **per contenuto**, non per posizione.

## Passi

- [x] **11.0 Analisi e piano** — ✅ 2026-09-25, questo file, con il rimando dallo step 10.
- [x] **11.1 Test** (test-author) — ✅ 2026-09-25: rosso prima il comparatore; FM7 e i WB per contenuto; una
  verifica del cablaggio nella UI.
  > **Note implementazione** (HEAD `d318311df`, prodotto intatto):
  > - `bulkDisplay.test.ts`: U1 ✘ «expected ['a-second','z-first'] to deeply equal
  >   ['z-first','a-second']»; U2a–e verdi; il test che c'era già è intatto. In tutto 1 rosso e 14 verdi.
  > - `tx-bulk-row-order.spec.ts` (nuova, registrata in `_frontend_transaction.py`):
  >   - **E-order ✘**: ordine osservato `[r5, r1, r4, r2, r3]`, e al primo run `[r1, r4, r2, r3, r5]`,
  >     cioè ordine alfabetico degli id casuali;
  >   - **E-reset ✓** (modifica → Reset all → chiudi, senza conferma) ed **E-reset senza modifica ✓**.
  >     Sono i controlli di `serializeOps`. La prova che il controllo diventa rosso quando la conferma
  >     compare è stata fatta con una variante temporanea su una coppia FX_CONVERSION, poi tolta; la spec
  >     è tornata identica byte per byte.
  > - FM7 e WB2, WB3, WB8, WB9, WB10 scelgono la riga per una descrizione unica scritta sul TRANSFER. È
  >   condivisa dai due capi e resta attraverso le riedizioni, con `toHaveCount(1)` prima del doppio
  >   clic. Sul prodotto attuale `tx-wac-formmodal` e `tx-wac-bulk` passano 10/10 ciascuna.
  >
  > **Fuori pista (preesistente, non C4)**: dopo un Reset, su una **coppia** già salvata la chiusura
  > mostra un falso «scartare le modifiche?», anche prima di C4. Le cause, tutte in `serializeOps` e
  > `collapsePairedOps`, sono tre:
  > - `collapsePairedOps` dà alla coppia un `link_uuid` nuovo;
  > - il partner nascosto porta in `pairedWith` il `tempId` rigenerato della riga principale;
  > - il partner viene ricostruito con un ordine di chiavi diverso.
  >
  > Confermato da test-author con la variante temporanea. Da segnalare al coordinator come voce a parte.

- [x] **11.2 Cura** (`bulkDisplay.ts`, `TransactionBulkModal.svelte`) — ✅ 2026-09-25
  > **Note implementazione**:
  > - `bulkDisplay.ts`: `BulkDisplayRow.createdSeq?`, e nel comparatore lo spareggio dopo il `txId` e
  >   prima del `tempId`.
  > - `TransactionBulkModal.svelte`:
  >   - `createdSeq` obbligatorio su `PendingOp`;
  >   - il contatore `nextCreatedSeq()`;
  >   - il timbro negli 8 punti di nascita: 8 occorrenze, pari agli 8 `tempId: generateUUID()`;
  >   - `serializeOps` esclude `createdSeq` come il `tempId`.
  > - Evidenze:
  >   - vitest `bulkDisplay.test.ts` **15/15**;
  >   - `dev.py front build` exit 0; svelte-check dà i 3 errori della baseline e nessun errore di tipo
  >     nuovo, cioè nessun punto di nascita senza timbro;
  >   - `tx-bulk-row-order` **3/3** (E-order ✓, E-reset ×2 ✓);
  >   - prettier pulito (lo spareggio sta su una riga, come vuole lo stile del progetto).
- [x] **11.3 Determinismo**: `tx-wac-formmodal` e `tx-wac-bulk` 5 volte di fila, prima e dopo la cura
  del prodotto (i test per contenuto non devono dipendere dall'ordine), più le mutazioni.
  > **Note implementazione** (2026-09-25, parziale: fermato dalla PAUSA del coordinator alle ~13:05):
  > - **5 volte di fila, prima della cura del prodotto** (`/tmp/libreFolio_k_c4_repeat.sh before 5`,
  >   con i test nuovi): `tx-wac-formmodal` 5 su 5 (10 test ciascuno) e `tx-wac-bulk` 5 su 5. I test per
  >   contenuto non dipendono più dall'ordine.
  > - **5 volte di fila, dopo la cura**: `tx-wac-formmodal` 5 su 5, `tx-wac-bulk` 5 su 5 e
  >   `tx-bulk-row-order` 5 su 5 (3 test ciascuno).
  > - **Mutanti** (`/tmp/libreFolio_k_c4_mutations.py`, file ripristinati identici con SHA-256):
  >   - M1, il comparatore ignora `createdSeq` → U1 ✘ ed E-order ✘ ✓;
  >   - M3, `serializeOps` tiene `createdSeq` → E-reset (con modifica) ✘ ✓, la guardia scatta;
  >   - **M2, il modale timbra una costante → NON CONCLUSO.** Due volte di fila «Shared backend did not
  >     answer within 120s», prima di qualunque test: è un guasto d'ambiente, non un rosso.
  >
  > **Fuori pista (triage di M2, in corso)**:
  > - Il log dell'app nella lane mostra l'avvio e lo spegnimento nello stesso secondo, alla scadenza dei
  >   120 s, quindi il tempo va via prima che l'app parta.
  > - Il backend condiviso ha l'output su DEVNULL (`verbose=False` scritto in `_cli.py:599`).
  > - Ipotesi «build stantio» **smentita**: subito dopo il build di M2, `check_frontend_needs_build()`
  >   risponde `False` e nessun file di `frontend/src` è più recente di `build/index.html`.
  > - Prossima ipotesi da verificare: cosa fa `dev.py server --test` prima dell'avvio (cache delle
  >   risorse statiche, rete), e perché solo con M2.
  >
  > **⚠️ Stato del build alla pausa**: `frontend/build` contiene il **mutante M2**, dal build della
  > diagnosi. I sorgenti sono giusti (SHA-256 verificati), ma prima di qualunque E2E o misura va rifatto
  > `dev.py front build`.
  >
  > **Alla ripartenza**, in ordine:
  > 1. `dev.py front build`;
  > 2. chiudere M2, rilanciandolo o con un altro percorso;
  > 3. i gate 11.4: `tx-unit`, `tx-bulk-operations`, `transactions-modals`, `tx-split-promote`,
  >    `tx-clone`, `tx-import-duplicate-precedence`, poi gli statici;
  > 4. CHECKPOINT READY.
  >
  > **Note implementazione** (2026-09-28, ripresa dopo il riavvio; passo 11.3 chiuso):
  > - **Causa del «Shared backend did not answer within 120s»**, trovata da F e verificata nel codice:
  >   - `dev.py server --test` forza `debug_mode = True` (`dev.py:185`);
  >   - `auto_build_frontend` (`dev.py:2013`) ricompila se il marcatore `frontend/build/.build-debug` non
  >     corrisponde;
  >   - il mio script dei mutanti faceva `dev.py front build` in produzione (marcatore 0), quindi il
  >     server di test ricompilava in debug dentro i suoi 120 s di avvio.
  >   - Non era né un rosso né un build stantio. Con M1 e M3 la ricompilazione era rientrata nei tempi.
  > - Rimedio: build **`dev.py front build --debug`** (marcatore 1). Ha tolto anche il mutante M2 da
  >   `frontend/build`: nel bundle c'è `createdSeqCounter++`. Gli script in `/tmp` ora compilano con
  >   `--debug`.
  > - **M2, il modale timbra una costante → E-order ✘ ✓** («Shared backend ready», 1 fallito e 2 passati).
  >   File ripristinato identico (SHA-256).
  > - **Mutanti 3 su 3 rossi**: M1 (U1 ed E-order), M2 (E-order), M3 (E-reset).
  >
  > **Fuori pista**: lo script dei mutanti lascia in `frontend/build` l'ultimo mutante compilato,
  > perché ripristina i sorgenti ma non ricompila. Prima dei gate va rifatta la build debug.
- [x] **11.4 Gate e handoff** — ✅ 2026-09-28: `tx-unit`, `core-unit`, statici, **CHECKPOINT READY** con la
  voce di CHANGELOG.
  > **Note implementazione**:
  > - Gate nella lane 6155 (`/tmp/libreFolio_k_c4_gates.sh`), dopo `dev.py front build --debug`
  >   (marcatore 1, nel bundle il contatore vero):
  >
  >   | selettore | esito |
  >   |---|---|
  >   | `tx-unit` | 8 file, 375 ✓ (comprende `bulkDisplay.test.ts`) |
  >   | `tx-bulk-operations` | 10/10 ✓ |
  >   | `transactions-modals` | 19/19 ✓ |
  >   | `tx-split-promote` | 6/6 ✓ |
  >   | `tx-clone` | 6/6 ✓ |
  >   | `tx-import-duplicate-precedence` | 6/6 ✓ |
  >   | `tx-bulk-row-order` | 3/3 ✓ |
  >
  > - Statici:
  >   - svelte-check: 3 errori, gli stessi della baseline (`TransactionFormModal.test.ts`,
  >     `ToolExecutionMetrics.svelte`);
  >   - prettier pulito sui 6 file frontend;
  >   - knip: nessun reperto nei file di K;
  >   - ruff e black sul runner: niente sulle righe aggiunte; i 4 errori ruff ci sono identici su HEAD.
  > - `core-unit` non è stato rilanciato: C4 non tocca nessun file della sua lista, mentre
  >   `bulkDisplay.test.ts` sta in `tx-unit`.
  > - Messaggi di commit: `/tmp/libreFolio_commits/k-11-c4-bulk-order.txt` (codice e test) e
  >   `k-12-journal-c4.txt` (journal).
  >
  > **Fuori pista (principio del developer del 25/09)**: nel modale ogni riga ha ora una sequenza
  > unica, quindi lì lo spareggio finale per `tempId` non si raggiunge più. Resta nel contratto della
  > funzione pura, per righe senza sequenza, come da piano approvato, ed è coperto da U2b e dal test che
  > c'era già. Nessun test vecchio da togliere: FM7 e i WB sono stati riscritti per contenuto, non
  > aggiunti accanto.

## Test list

| # | livello | cosa prova | rosso oggi |
|---|---|---|---|
| U1 | unit (`bulkDisplay.test.ts`, `tx-unit`) | due righe nuove della stessa data, `createdSeq` 0 e 1, con `tempId` in ordine lessicografico inverso: restano nell'ordine di creazione | 🔴 |
| U2 | unit, controlli | `txId` prima di `createdSeq` (gli edit prima delle create nello stesso giorno); una coppia usa la sequenza della riga visibile; senza sequenza decide il `tempId`; l'input non viene mutato | — |
| E-order | E2E (spec nuova `tx-bulk-row-order.spec.ts`) | 5 righe nuove della stessa data, riconoscibili per descrizione, compaiono nell'ordine di creazione | 🔴, con probabilità 119/120 |
| FM7, WB2, WB3, WB8, WB9, WB10 | E2E | la riga si sceglie per contenuto: stessi passi e stesse asserzioni di prima | — (erano rossi a intermittenza) |

**CHANGELOG proposto** (🐛 Fixed): «Bulk editor: new rows on the same date now keep the order in which
you added them, instead of occasionally swapping places.»
