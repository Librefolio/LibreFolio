# Piano — K / step 9: duplicati dell'import wizard

> Nasce dallo step 8 di [`plan-phase00TaxonomySelect.prompt.md`](plan-phase00TaxonomySelect.prompt.md):
> la review del developer (24/09) ha fatto emergere due difetti **preesistenti** dell'import wizard.
> Il developer li ha assegnati a K in questo round. Il piano è approvato «così com'è» (coordinator,
> 24/09 15:00). **Niente hotfix**: la correzione va solo in Release 2. C1 e C2 restano comunque due
> commit separati.

| | |
|---|---|
| **Worktree** | `LibreFolio-worktrees/e-alfy-improved-memory`, branch `e-alfy-k-tassonomia-e-select` |
| **Baseline** | `dc575dc05` (su `f1047f766`) |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k` — l'unica usata qui |
| **Copia prod** | non serve e non si tocca; se servisse, va rinfrescata dallo snapshot |
| **File di K in esclusiva** | `ImportWizardModal.svelte` (senza ancore `guideAnchor`/`onboardingGuide` di J), `importDuplicateResolver.ts`, `importDedup.ts`, `importTypes.ts`, `importMerge.ts` |
| **Condivisi, solo in aggiunta** | cataloghi i18n (1 chiave ×4), `scripts/test_runner/_frontend_transaction.py` (1 registrazione) |
| **Spec di altri** | `tx-import-*` si eseguono e non si modificano; prima di toccare E4-05 o `tx-import-resolution` si avvisa il coordinator |

## I due difetti

**Reperto 2: il custode di un gruppo fra file è preselezionato anche quando collide col DB.**
- `applyPendingDuplicateGroups` sovrascrive la selezione calcolata dal verdetto DB con quella del
  resolver. Il resolver tiene di default il primario di ogni partizione e ignora le collisioni.
- Il primario conserva lo stato DB («⚠ Probabile dup»), ma `openBadgeCompare` apre per primo il
  confronto del gruppo, cioè file contro file.
- Lo stesso incrocio c'è con l'editor in sospeso: `markPendingBulkDuplicates` non azzera `dupGroupKey`.
- Origine: `62516170c` e `81853ae81` (agosto), presenti in `v1.1.0`.

**Reperto 1: dopo un cambio di risoluzione allo step 6, «Importa» riporta allo step 5.**
- `resolveAsset` segna il ricontrollo come da rifare. `handleImport` lo rifà, e `refreshDuplicateReport`
  azzera le scelte del resolver.
- Poi basta un qualunque gruppo fra file per tornare allo step 5, senza messaggio.
- Origine: `ef722b552` (09/09), non in `main`.

## Rimedio

**C1 — reperto 2**
- `MergedTx` riceve due campi opzionali che la logica di lotto non sovrascrive mai:
  - `dbDuplicateStatus`, scritto al parse (`importMerge`) e al ricontrollo;
  - `pendingMatchStatus`, calcolato **prima** di applicare i gruppi.
- Una collisione è **ferma** quando è DB `likely` o editor `pending_duplicate`:
  - il primario di una partizione è il membro a priorità più alta senza collisione ferma;
  - il custode di default è quel primario, ma solo se non collide; se collidono tutti, non c'è custode;
  - le scelte manuali restano come sono;
  - `possible` e `pending_possible` non bloccano, come oggi.
- `compareTargetFor(row)` è puro: il clic apre il confronto che il badge dichiara (DB, editor, lotto).

**C2 — reperto 1**
- `carryResolverChoices` è puro: riporta le scelte sui gruppi con **lo stesso insieme di membri**. La
  chiave non va bene, perché cambia quando un asset passa da ISIN estratto a id reale.
- Segnala anche i gruppi nuovi o cambiati.
- `handleImport` torna allo step 5 solo se ci sono gruppi nuovi o cambiati, e lo dice con un toast
  (`importWizard.duplicatesChangedReview`) e l'evento `tx.import.duplicates.changed`.
- La guardia «selezione cambiata» (E4-05) resta com'è.
- **Scartato**: il ricontrollo subito dopo la creazione dell'asset. E4-05 fissa il ricontrollo finale.

## Passi

- [x] **9.0 Piano nel journal** — ✅ 2026-09-24
  > **Note implementazione**: questo file, con il rimando dal piano principale (step 8, «Fuori
  > pista»). Scritto dopo il via del coordinator, che ha riportato l'approvazione del developer.
- [x] **9.1 Rossi prima della correzione** — ✅ 2026-09-24
  - Chi scrive: test-author scrive U1, U2 ed E1 sul codice attuale.
  - Esecuzione: U1 e U2 in vitest, E1 nella lane 6155.
  - DoD: tutti e tre rossi per la ragione giusta, cioè custode preselezionato e confronto del lotto.
  > **Note implementazione**: test-author ha esteso `importDuplicateResolver.test.ts` (U1, U2, U3), ha
  > creato `e2e/transactions/tx-import-duplicate-precedence.spec.ts` (E1, E2) e l'ha registrata in
  > `_frontend_transaction.py`, solo in aggiunta.
  > - `node_modules/.bin/vitest run src/lib/utils/transactions/importDuplicateResolver.test.ts`
  >   → **8 falliti, 25 passati** (log `/tmp/libreFolio_k_iw_unit_red.log`).
  >   - Rossi: U1 ×4 e U2 ×4. In ogni caso il custode è la copia che collide.
  >   - Verdi: U3 ×5, i due controlli di U2 sul primario di sola visualizzazione, e i 18 test che
  >     c'erano già.
  >   - U1 ha un quarto caso in più: dopo un riordino delle priorità il resolver deve leggere
  >     `dbDuplicateStatus` e `pendingMatchStatus`, non il `pending_duplicate` che il passo di lotto
  >     riscrive sui secondari.
  > - `dev.py test --test-port 6155 --data-dir /tmp/librefolio-r2-k front-transaction
  >   tx-import-duplicate-precedence` → **E1 ✘, E2 ✓** (log `/tmp/libreFolio_k_iw_e2e_red.log`).
  >   - E1 fallisce solo sulle due asserzioni bersaglio: `aria-pressed` atteso `"false"`, ricevuto
  >     `"true"`; e `import-wizard-compare-col-db-78` non trovato, perché si è aperto il confronto del
  >     lotto.
  >   - Il parse aveva segnato entrambe le copie `likely` contro la transazione #78. Lo step dei
  >     duplicati c'era, la copia A era visibile e la B nascosta.
  >   - Porta 6155 libera dopo il run.
  >
  > **Fuori pista**: il primo run E2E di test-author è caduto prima dei test.
  > - Modificare un file sotto `frontend/src`, anche un `*.test.ts`, rende il build frontend stale.
  > - Il runner avvia il backend prima del proprio build, così l'auto-build del backend supera i 120 s
  >   di avvio.
  > - Rimedio: prima di ogni run E2E, `dev.py front build`.
  >
  > **Fuori pista**: per non mostrare il coachmark di onboarding, la spec risponde con uno stato di
  > onboarding completato, solo per la pagina, come fa già `tx-import-flow.spec.ts`. Nessuna scrittura
  > su `TEST_USER`.
- [x] **9.2 C1** — ✅ 2026-09-24
  - Codice: i campi, `groupPartitions`/`defaultKeeperIndices`, `compareTargetFor`, e l'ordine
    pending → gruppi → override in `rebuildDuplicateGroups`.
  - Test: poi U3, U4 ed E2.
  - DoD: U1–U4 ed E1–E2 verdi; ogni correzione disattivata a mano torna rossa.
  - **CHECKPOINT C1**: le due correzioni condividono `ImportWizardModal.svelte`, quindi il commit C1
    va fatto prima di iniziare C2.
  > **Note implementazione** (in corso):
  > - `importTypes.ts`: `dbDuplicateStatus` e `pendingMatchStatus`, opzionali su `MergedTx`.
  > - `importMerge.ts`: una riga, il verdetto DB al parse.
  > - `importDedup.ts`: `hasFirmOutsideCollision` e `compareTargetFor`, puri. `unique` → nessun
  >   confronto.
  > - `importDuplicateResolver.ts`:
  >   - il primario è il membro a priorità più alta senza collisione ferma;
  >   - `defaultKeeperIndices` scarta il primario che collide, cioè quando collidono tutti.
  > - `ImportWizardModal.svelte`:
  >   - `refreshDuplicateReport` scrive `dbDuplicateStatus` e azzera `pendingMatchStatus`;
  >   - `rebuildDuplicateGroups` segue l'ordine rileva-editor → gruppi → override-editor;
  >   - `markPendingBulkDuplicates` è diviso in due: il nuovo `detectPendingBulkDuplicates` registra
  >     il verdetto, e `markPendingBulkDuplicates` resta l'override;
  >   - `openBadgeCompare` passa da `compareTargetFor`.
  > - Evidenze:
  >   - vitest su `src/lib/utils/transactions/`: **15 file, 276/276 verdi**, U1 e U2 compresi.
  >   - `dev.py front build`: exit 0. svelte-check dà 3 errori e 41 warning, gli stessi della
  >     baseline, in `TransactionFormModal.test.ts` e `ToolExecutionMetrics.svelte`: nessuno in un
  >     file di K.
  >   - E2E `tx-import-duplicate-precedence`: **E1 ✓, E2 ✓** (log `/tmp/libreFolio_k_iw_e2e_c1.log`).
  >   - prettier pulito sui cinque file.
  >
  > **Fuori pista**: la funzione nuova `detectPendingBulkDuplicates` è la prima metà di
  > `markPendingBulkDuplicates`, che era fra le sei funzioni dichiarate. Da segnalare nell'handoff.
  >
  > **Note implementazione** (completamento, 2026-09-24 pomeriggio):
  > - `markPendingBulkDuplicates`: dentro un gruppo fra file cambia solo il badge. Resta la struttura
  >   che il resolver ha scelto, quindi una copia è elencata e deselezionata, come nel caso DB.
  > - Test-author ha aggiunto:
  >   - U4, 12 test su `compareTargetFor` e `hasFirmOutsideCollision`, con il 100% dei rami di
  >     `importDedup.ts`;
  >   - U6, 2 test: `importMerge` scrive `dbDuplicateStatus`;
  >   - U7, 7 test su `rowAfterRecheck`;
  >   - E5, il percorso dell'editor in sospeso: al primo passaggio e dopo «ricalcola default» la copia
  >     A è elencata, deselezionata, e il badge apre il confronto con l'editor.
  > - `rowAfterRecheck` è estratto, puro, da `refreshDuplicateReport`. Pinna che un verdetto DB
  >   vecchio non sopravviva mai al ricontrollo.
  > - Mutazioni: script `/tmp/libreFolio_k_iw_mutations_c1.py`. Ogni file è stato ripristinato
  >   identico e verificato con SHA-256. Tutte e sette sono diventate **rosse**:
  >   - M1, il primario ignora le collisioni → U1 ×4;
  >   - M2, i custodi tengono i primari in collisione → U2 ×4;
  >   - M3, lotto prima del DB → U4 ×2;
  >   - M4, nessun verdetto DB al parse → U6 ×2;
  >   - M5, verdetto editor dopo il resolver → E5;
  >   - M6, l'override dell'editor nasconde le copie del gruppo → E5;
  >   - M8, il badge ignora `compareTargetFor` → E1 ed E5.
  >   - Test-author ha provato inoltre 19 mutanti di `rowAfterRecheck` su copie in `/tmp`: tutti rossi.
  > - Gate nella lane 6155, uno alla volta (log in `/tmp/libreFolio_k_iw_gates_c1/`):
  >
  >   | selettore | esito |
  >   |---|---|
  >   | `tx-import-duplicate-precedence` | 3/3 ✓ |
  >   | `tx-import-matching` (E4-05) | 6/6 ✓ |
  >   | `tx-import-flow` | 10/10 ✓ |
  >   | `tx-asset-identity` | 9/9 ✓ |
  >   | `tx-import-asset-inspector` | 5/5 ✓ |
  >   | `front-utility core-unit` | 90 file, 2472 ✓ |
  >   | `front-transaction tx-unit` | 8 file, 369 ✓ |
  >   | `tx-import-resolution` | 11/12, IWR-006 ✘ |
  >   | `tx-brim-import` | T1 ✘ |
  >   | `tx-ca-contract` | 10/12, CAC-011 e CAC-012 ✘; CAC-001 una volta ✘ |
  >
  > - I rossi sono **preesistenti**, provati con un controllo di baseline
  >   (`/tmp/libreFolio_k_iw_baseline_c1.sh`): i cinque file di C1 riportati a HEAD, build, run, e
  >   ripristino identico verificato.
  >   - IWR-006: il coachmark `import.review` intercetta i clic; lo corregge J nel suo C4.
  >   - T1 sceglie il file con `.first()`. Prende `schwab-export.csv`, lo step «Unifica asset» vuole
  >     2 conferme e Continue resta disabilitato. Verdetto: *assumption*. Rosso identico su baseline.
  >   - CAC-011 e CAC-012 si fermano allo step «Correzioni», con Continue disabilitato. Rossi identici
  >     su baseline.
  >   - CAC-001 ha preso un 500 dall'upload nel secondo run; è verde nel primo run e su baseline.
  > - Statici:
  >   - svelte-check: 3 errori, gli stessi della baseline;
  >   - prettier pulito sui nove file frontend;
  >   - knip: nessun reperto nei file di K, restano solo 4 devDependencies preesistenti;
  >   - ruff e black su `_frontend_transaction.py` segnalano solo cose preesistenti, identiche su HEAD
  >     e fuori dalle righe aggiunte.
  >
  > **Fuori pista**: il primo giro di gate ha usato nomi d'azione sbagliati (`tx-import-ca-contract`,
  > `tx-import-asset-identity`). I nomi del runner sono `tx-ca-contract` e `tx-asset-identity`; li ho
  > rilanciati.
- [ ] **9.3 C2**
  - Rosso prima: E3.
  - Codice: `carryResolverChoices`, `refreshDuplicateReport`, `handleImport`, i18n ×4.
  - Test: poi U5 ed E4.
  - DoD: U5, E3 ed E4 verdi, mutazioni rosse, E4-05 verde senza ritocchi.
- [ ] **9.4 Gate e handoff**
  - Regressione `tx-import-*` e `front-utility core-unit`.
  - `dev.py front check`, lint e dead-code.
  - Nota sulla galleria `import-wizard-duplicates-step`.
  - **CHECKPOINT C2**.

## Test list

| # | livello | cosa prova | rosso oggi |
|---|---|---|---|
| U1 | unit | due gemelli fra file, il prioritario collide col DB (`likely`): custode = l'altro | 🔴 |
| U2 | unit | collidono tutti (DB `likely` o editor `pending_duplicate`): nessun custode | 🔴 |
| U3 | unit, negativi | senza collisioni custode = prioritario; `possible`/`pending_possible` non bloccano; scelta manuale su una copia in collisione rispettata | — |
| U4 | unit | `compareTargetFor`: `likely`/`possible` → db; match editor → pending; secondario del lotto → lot; `unique` → nessuno | — |
| U5 | unit | `carryResolverChoices`: stessi membri con chiave diversa → scelta riportata; membri cambiati → scartata e segnalata; gruppo nuovo → segnalato | — |
| E1 | E2E | due CSV con la stessa riga, e la stessa transazione già nel DB: allo step 6 custode `aria-pressed=false`; clic sul badge → `import-wizard-compare-col-db-<id>` | 🔴 |
| E2 | E2E, negativo di E1 | senza la transazione nel DB: custode selezionato; una copia tenuta a mano apre il confronto del lotto | — |
| E3 | E2E | un gruppo fuori dal DB più una riga con asset ambiguo; allo step 5 «Tutte»; allo step 6 scelta a mano dell'asset; Importa → editor senza passare dallo step 5, con **entrambe** le copie nel payload | 🔴 |
| E4 | E2E, negativo di E3 | la risoluzione cambia i membri di un gruppo: Importa → step 5 con toast ed evento `tx.import.duplicates.changed` | 🔴 sull'avviso |
| R | regressione | `tx-import-matching` (E4-05), `tx-import-resolution`, `tx-import-flow`, `tx-brim-import`, `tx-import-ca-contract`, `tx-import-asset-identity`, `tx-import-asset-inspector`, `front-utility core-unit` | — |

- Gli E2E stanno in una spec **nuova**, `e2e/transactions/tx-import-duplicate-precedence.spec.ts`.
- È write-safe come le E4: broker, asset, file CSV Generic e transazioni sono tutti del test, e il test
  li cancella a fine run.
