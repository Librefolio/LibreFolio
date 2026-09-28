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
- [x] **9.3 C2** — ✅ 2026-09-25
  - Rosso prima: E3.
  - Codice: `carryResolverChoices`, `refreshDuplicateReport`, `handleImport`, i18n ×4.
  - Test: poi U5 ed E4.
  - DoD: U5, E3 ed E4 verdi, mutazioni rosse, E4-05 verde senza ritocchi.
  > **Note implementazione** (2026-09-24, rossi prima del codice, HEAD `78d324873`): test-author ha
  > scritto U5, E3 ed E4 contro il codice attuale.
  > - U5 (`importDuplicateResolver.test.ts`), 11 casi: **11 falliti, 33 passati**. Tutti falliscono con
  >   `TypeError: carryResolverChoices is not a function`; i test che c'erano già passano.
  > - `tx-import-duplicate-precedence`: **5 test, 3 ✓ e 2 ✘**, risultato identico su due run (log
  >   `/tmp/libreFolio_k_iw_c2_red.log` e `…_run1.log`).
  >   - E1, E2 ed E5 ✓.
  >   - E3 ✘ solo su «the wizard went back to the duplicates step». Nello screenshot lo step 5 ha
  >     «All auto-resolved»: la scelta «tieni entrambe» è sparita.
  >   - E4 ✘ solo sulle due asserzioni soft: nessun `toast-warning` e nessun evento
  >     `tx.import.duplicates.changed`. Il resto del percorso passa già oggi: ritorno, revisione, e una
  >     sola copia messa in stage.
  >
  > **Fuori pista**: leggendo `brim_provider.py:1480-1630` è emerso un caso che il piano non copriva.
  > - Il backend restringe il confronto col DB all'asset solo quando l'asset è risolto
  >   (`asset_id == reale OR NULL`); una riga non risolta si confronta con tutti gli asset.
  > - Quindi, se nella revisione l'utente lega di nuovo un gruppo a un altro asset, una copia unica
  >   può diventare un duplicato fermo del DB. Una scelta manuale riportata così com'è la farebbe
  >   importare.
  > - Regola aggiunta: un gruppo già deciso a mano, in cui una copia ha cambiato
  >   `hasFirmOutsideCollision` in un senso o nell'altro, conta come `changed`. Le sue scelte cadono e
  >   si torna allo step 5.
  > - I gruppi non toccati ricalcolano i default, e resta a guardia l'avviso «selezione cambiata».
  > - API: quarto argomento opzionale `{previousRows, nextRows}`, così U5 resta valido.
  > - Testo del toast: «new or changed duplicates».
  > - Da coprire con casi U5 in più e con E6: rilegatura nella revisione, toast ed evento.
  >
  > **Note implementazione** (2026-09-24 sera, codice C2):
  > - `importDuplicateResolver.ts`: `ResolverChoices`, `CarriedResolverChoices`, `carryResolverChoices`.
  >   È puro: firma dei membri ordinata, e la regola sui verdetti con il quarto argomento opzionale.
  > - `ImportWizardModal.svelte`:
  >   - `rebuildDuplicateGroups(txArr, assetMap, previous?)` riporta le scelte *prima* di
  >     `applyPendingDuplicateGroups`, che le legge, e restituisce i gruppi `changed`;
  >   - `refreshDuplicateReport` non azzera più le scelte: fotografa gruppi, righe e scelte, poi
  >     ricostruisce e restituisce `changed`, oppure `[]` se il ricontrollo non si completa;
  >   - `handleImport` torna allo step dei duplicati solo con `changed` non vuoto, e lo dice con
  >     `notify` (`tx.import.duplicates.changed`, detail `groups: [{key, memberIndices}]`) e un
  >     toast warning. Poi c'è la guardia «selezione cambiata», intatta.
  > - i18n: `importWizard.duplicatesChangedReview` ×4 con `dev.py i18n add`, +2 −1 per catalogo.
  > - Evidenze:
  >   - vitest su `utils/transactions`: 15 file, **308/308**;
  >   - `dev.py front build` exit 0; svelte-check dà 3 errori, gli stessi della baseline, in nessun
  >     file di K;
  >   - `tx-import-duplicate-precedence`: **5/5 ✓**, E3 ed E4 compresi (log
  >     `/tmp/libreFolio_k_iw_c2_green.log`).
  > - Documentazione (docs-writer, solo EN, nessuno stamp):
  >   - pagina developer `import-wizard.md`, solo le sezioni Duplicate detection, Batch Duplicate
  >     Resolver e N-way Compare Modal;
  >   - pagina utente `how-to.en.md`, solo la nota Duplicates e «Duplicates Against Your Database»;
  >   - riletta contro il codice finale: nomi, testo del toast e regola corrispondono. La sezione
  >     della guida di J non è toccata.
  >   - Debito di traduzione su `how-to` it/fr/es: la nota Duplicates (due punti) e una frase di
  >     «Duplicates Against Your Database».
  >
  > **Note implementazione** (2026-09-24 sera, test aggiunti dopo il codice e prove):
  > - Test-author ha aggiunto:
  >   - **U5b**, 10 casi sulla regola dei verdetti: `likely` che compare o sparisce, `pending_duplicate`,
  >     verdetti deboli, gruppo non toccato, senza `rows`, riga mancante, due gruppi. Con U5:
  >     **54/54**.
  >   - **E6**, la rilegatura nella revisione. T è legato a P al parse ed è unico, mentre il suo gemello
  >     è committato su Q. Allo step 5 si tengono entrambe le copie; nella revisione si rilega a Q e si
  >     risponde «skip» al prompt dell'identificativo. Importa: ritorno allo step 5 con toast ed evento,
  >     il default ora non tiene nessuna copia, e dopo Importa va in stage solo il DEPOSIT.
  >   - `tx-import-duplicate-precedence`: **6/6 ✓** (log `/tmp/libreFolio_k_iw_c2_e6.log`).
  > - **Mutazioni** (script `/tmp/libreFolio_k_iw_mutations_c2.py`, ogni file ripristinato identico e
  >   verificato con SHA-256): tutte e otto **rosse**.
  >   - M9, gruppi riconosciuti per chiave → 15 test U5 rossi;
  >   - M10, riportati anche i gruppi non toccati → 3;
  >   - M11, regola dei verdetti spenta → 4;
  >   - M12, gruppi nuovi non segnati come `changed` → 5;
  >   - M13, ritorno allo step 5 con un gruppo qualsiasi → E3;
  >   - M14, ricostruzione senza riporto → E4 ed E6. E3 sopravvive: la chiave del suo gruppo non
  >     cambia, quindi lo stato vecchio vale ancora per chiave. Per E3 fa fede il rosso su HEAD;
  >   - M15, regola dei verdetti non collegata nel componente → E6;
  >   - M16, evento rinominato → E4 ed E6.
  > - **Baseline** (`/tmp/libreFolio_k_iw_baseline_c2.sh`): i due file di prodotto riportati a HEAD
  >   `78d324873`, build, run, ripristino identico. Risultato: E1, E2 ed E5 ✓; E3 ✘ per il ritorno allo
  >   step 5; E4 ✘ su toast ed evento; E6 ✘ su «going back is announced with a warning toast».
  > - **Gate** nella lane 6155 (`/tmp/libreFolio_k_iw_gates_c2.sh`), **interrotti alle 18:40 dalla
  >   PAUSA** chiesta dal coordinator:
  >   - build exit 0; svelte-check 3 errori, gli stessi della baseline;
  >   - `tx-import-duplicate-precedence` 6/6 ✓;
  >   - `tx-import-matching` 6/6 ✓, E4-05 compreso, senza ritocchi;
  >   - `tx-import-resolution` 11/12, con IWR-006 ✘ già noto;
  >   - `tx-import-flow` 10/10 ✓;
  >   - `tx-brim-import` interrotto a metà.
  >
  > **Stato alla PAUSA** (2026-09-24 18:45):
  > - HEAD `78d324873`, stage vuoto, 11 percorsi modificati, nessun file nuovo.
  > - Porte 6155 e 6165 libere, nessun processo della lane acceso.
  > - Mancano, in ordine:
  >   1. i gate restanti, uno alla volta con `dev.py test --test-port 6155 --data-dir
  >      /tmp/librefolio-r2-k`: `front-transaction tx-brim-import`, `tx-ca-contract`,
  >      `tx-asset-identity`, `tx-import-asset-inspector`, poi `front-utility core-unit` e
  >      `front-transaction tx-unit`. Prima serve un `dev.py front build`, se il build non è più
  >      aggiornato;
  >   2. la validazione della documentazione: `dev.py mkdocs build` (strict), poi `git status` per
  >      vedere se `copy_docs_assets()` ha riscritto icone, favicon o `sw.js` tracciati (nel caso, esclusi
  >      e segnalati), poi `dev.py mkdocs check-links` e `dev.py mkdocs translate-validate`;
  >   3. gli statici: prettier sui file toccati e knip;
  >   4. il passo 9.4: nota finale del piano, messaggi di commit (codice, docs, journal) e **CHECKPOINT
  >      READY C2**. Il checkpoint porta il testo sostitutivo per il punto «duplicate-recheck bounce»
  >      nella sezione della guida (di J), la voce di CHANGELOG e la nota sulla galleria
  >      `import-wizard-duplicates-step`.
  > - Se nel frattempo il Mac si riavvia, `/tmp` si svuota: script e log spariscono, e anche la data-dir
  >   della lane. I numeri sono già scritti qui, e i comandi sopra bastano a rifare tutto.
  >
  > **In coda dopo C2**: **C3**, la raffica di `GET /api/v1/brokers/{id}` dalla pagina Transazioni
  > (40–60 richieste al secondo, anche in `v1.1.0`), assegnata dal coordinator. Prima analisi, poi codice.
  > Piano:
  > [`plan-phase00TaxonomySelectStep10BrokerRequestBurst.prompt.md`](plan-phase00TaxonomySelectStep10BrokerRequestBurst.prompt.md),
  > approvato dal developer il 25/09.
  >
  > **Note implementazione** (2026-09-25, ripresa dopo la PAUSA e il riavvio del Mac alle 08:58):
  > - `/tmp/librefolio-r2-k` era sparita: l'ha ricreata il runner. Non ho fatto nessuna copia di prod,
  >   per C2 non serve, quindi la correzione della snapshot delle 09:15 non mi riguarda.
  > - Gate restanti (`/tmp/libreFolio_k_iw_gates_c2b.sh`, lane 6155, uno alla volta):
  >
  >   | selettore | esito |
  >   |---|---|
  >   | build | exit 0; svelte-check 3 errori, gli stessi della baseline |
  >   | `tx-asset-identity` | 9/9 ✓ |
  >   | `front-utility core-unit` | 90 file, 2493 ✓ |
  >   | `front-transaction tx-unit` | 8 file, 369 ✓ |
  >   | `tx-brim-import` | T1 ✘ |
  >   | `tx-ca-contract` | 10/12, CAC-011 e CAC-012 ✘ |
  >   | `tx-import-asset-inspector` | 4/5, E2-001 ✘ |
  >
  > - Confronto con HEAD `78d324873` (`/tmp/libreFolio_k_iw_baseline_c2b.sh`): i due file di prodotto
  >   di C2 riportati a HEAD, build, run, ripristino identico verificato con SHA-256, poi di nuovo
  >   l'inspector sul codice C2.
  >   - **T1, CAC-011, CAC-012 ed E2-001 falliscono anche su HEAD, e negli stessi punti**:
  >     - T1: `tx-brim-import.spec.ts:113`, `import-wizard-step4` mai visibile;
  >     - CAC-011 e CAC-012: `tx-import-ca-contract.spec.ts:150`, idem;
  >     - E2-001: `tx-import-asset-inspector.spec.ts:476`, listbox della valuta.
  >   - E2-001 ✘ anche nel secondo run su C2. Il modo di fallire è quello già documentato in
  >     `B-esecuzione.md` (`optionsClosed()` soddisfatto da una tendina aperta ma vuota) e nel piano K,
  >     step 7.
  >   - Nessuno di questi rossi viene da C2. Non li correggo: li attribuisce il coordinator sul target.
  > - Documentazione:
  >   - `dev.py mkdocs build` (strict): exit 0, 0 righe `WARNING`; c'è solo il banner di Material su
  >     MkDocs 2.0;
  >   - `git status` identico prima e dopo la build: `copy_docs_assets()` non ha riscritto nessun
  >     file tracciato;
  >   - `dev.py mkdocs check-links`: 80 link validi ✅;
  >   - `dev.py mkdocs translate-validate`: exit 1 con 486 errori su tutto il sito, debito
  >     preesistente. Delta di K: su `how-to.en.md` i bullet passano da 28 a 29, mentre titoli (12) e
  >     link (7) non cambiano. Quindi il WARN `list-bullet-count` sale di uno per lingua; gli ERROR
  >     `heading-count` e `link-missing` (sezione Guided First Import) c'erano già. `import-wizard.md`
  >     è una pagina developer solo EN, senza traduzioni.
  > - Statici:
  >   - prettier pulito sugli 8 file frontend;
  >   - `npm run lint:dead` (knip, binario locale): nessun reperto nei file di K; restano solo reperti
  >     preesistenti in altri file.
  > - Gallery: `import-wizard-duplicates-step` arriva allo step dal flusso «Correzioni → Continua», non
  >   dal ritorno di Importa: C2 non ne rompe il percorso. Lo screenshot può cambiare per C1, se la sua
  >   fixture ha collisioni col DB.

- [x] **9.4 Gate e handoff** — ✅ 2026-09-25
  - Regressione `tx-import-*` e `front-utility core-unit`.
  - `dev.py front check`, lint e dead-code.
  - Nota sulla galleria `import-wizard-duplicates-step`.
  - **CHECKPOINT C2**.
  > **Note implementazione**:
  > - Gate e statici: sopra, in 9.2 e 9.3.
  > - Messaggi di commit per C2 in `/tmp/libreFolio_commits/`: `k-6-c2-recheck.txt` (codice),
  >   `k-7-docs-duplicates.txt` (docs, C1 + C2), `k-8-journal-c2.txt` (journal).
  > - Testo sostitutivo per il punto «The duplicate-recheck bounce» della sezione guida (di J) in
  >   `developer/frontend/components/features/import-wizard.md`: consegnato al coordinator. Lo applica
  >   all'integrazione chi fra J e K entra per secondo.
  > - CHANGELOG proposto (🐛 Fixed): due voci, una per C1 e una per C2, nel messaggio di handoff.
  > - Debito di traduzione dichiarato: `how-to` it/fr/es, cioè la nota Duplicates (due punti) e una
  >   frase di «Duplicates Against Your Database».
  > - **Aggiornamento del 2026-09-28**: il testo sostitutivo per J l'ha applicato K stesso, dopo
  >   l'allineamento a `dev_release2`, in un commit a parte (`759ba7748`).

- [x] **9.5 C6 — due campi morti del custode** — ✅ 2026-09-28 (via del coordinator per il principio
  del developer del 25/09: il codice di prodotto senza uso, dentro il perimetro, si toglie)
  > **Attribuzione, dalla storia di git e senza nessun test rosso di mezzo**:
  > - `MergedTx.dupKeeperIndex` e `dupKeeperFileName` li leggeva il «salta al custode» (`canJump`,
  >   `jumpToDuplicateKeeper`, il tooltip `pendingDuplicateJump`).
  > - `81853ae81` (03/08, «N-way dedup») l'ha sostituito con il confronto N-way (`openBadgeCompare`) e
  >   ha lasciato le scritture: 8 scritture, 0 letture. La chiave i18n era già sparita.
  > - È l'avanzo di una funzione tolta, non un difetto.
  >
  > **Note implementazione**:
  > - Tolti i due campi da `importTypes.ts` e le scritture da `ImportWizardModal.svelte`. Da
  >   `applyPendingDuplicateGroups` sono sparite anche la mappa `primaryOf` e la variabile
  >   `keeperIndex`, che servivano solo a quei campi. Tolte anche le scritture in `rowAfterRecheck`
  >   (`importDedup.ts`).
  > - Test, via test-author, solo le fixture: U4 in `importDedup.test.ts:300`, i marcatori e la fixture
  >   di U7, e le due fixture di U1-riordino. Nessun test aggiunto o tolto. Prima della modifica U7
  >   falliva come previsto: il campo passava attraverso `...m`.
  > - Comportamento invariato. Nessuna chiave i18n, nessun file del runner.
  > - Gate nella lane 6155, dopo `front build --debug` (`/tmp/libreFolio_k_c6_gates.sh`):
  >   - svelte-check: 3 errori, gli stessi della baseline, nessuno nei file di C6;
  >   - `core-unit` 98 file, **2646 ✓**; `tx-unit` 8 file, **375 ✓**;
  >   - `tx-import-duplicate-precedence` **6/6 ✓**; `tx-import-flow` **10/10 ✓**;
  >   - knip: nessun reperto nei file di K;
  >   - nessun riferimento ai due campi in `frontend/src` o `frontend/e2e`.

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
| U5b | unit, in corso d'opera | regola dei verdetti di `carryResolverChoices`: un gruppo toccato che guadagna o perde una collisione ferma è `changed`; verdetti deboli, gruppo non toccato, senza `rows`, riga mancante → riportato o ignorato | — |
| U6 | unit, in corso d'opera | `buildMergedTransactions` scrive `dbDuplicateStatus` (`likely`/`possible`/nessuno, anche con match tutti da cancellare) | — |
| U7 | unit, in corso d'opera | `rowAfterRecheck`: il verdetto DB vecchio non sopravvive, i marcatori di lotto ed editor si azzerano, la selezione si ricalcola | — |
| E5 | E2E, in corso d'opera | reimport dall'editor in sospeso: nessuna copia tenuta né preselezionata; la copia mostrata è elencata e deselezionata, il badge apre il confronto con l'editor, anche dopo «ricalcola default» | — |
| E6 | E2E, in corso d'opera | rilegatura nella revisione a un asset che ha il gemello nel DB: Importa → step 5 con toast ed evento, il default non tiene nessuna copia, va in stage solo il DEPOSIT | 🔴 su HEAD, su toast ed evento |

- Gli E2E stanno in una spec **nuova**, `e2e/transactions/tx-import-duplicate-precedence.spec.ts`.
- È write-safe come le E4: broker, asset, file CSV Generic e transazioni sono tutti del test, e il test
  li cancella a fine run.
