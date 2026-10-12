# Piano — fase 00, 44: il wizard di import aspetta i broker (M-16)

> **Stato**: ✅ consegnato il 2026-10-12 col checkpoint (§7, S7), in attesa dell'integrazione. Avanzamento in §7.
>
> - **Mandato**: coordinatore di Release 2 (`c8328a01-…`), voce M-16 di `BACKLOG_POST_1.2.md`. La voce sta nella sezione M e la chiude M quando la cura è nel target: questo lotto non tocca la sezione M.
> - **Workstream I**. Ramo `e-alfy-performance-charts-plan`. Base `378338fed` (`dev_release2`).
> - **Corsia**: `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; un comando alla volta. Mai le porte 6040 e 6041.
> - **Origine**: M, lotto 19, passi 10.0–10.3 (la galleria).

## 0. Autorizzazione (2026-10-12)

- **Developer**, testuale: «si nella 1.2 e ok I, ma fai che disabilitiamo il pulsante finchè il pacchetto non arriva».
- **Coordinatore**, dal kickoff:
  - la cura: il pulsante di avanzamento del passo 1 resta disabilitato finché la lista dei broker non è arrivata, senza ricalcolare i pannelli;
  - un test rosso prima, poi la cura, con `test-author`; va bene un E2E che rallenta la risposta e verifica il pulsante disabilitato, poi abilitato;
  - chiavi i18n solo se servono davvero;
  - la riga 🐛 del CHANGELOG la propongo io, la scrive lui.
- **Coordinatore** (10:01), sull'analisi di I:
  1. **B sì**: il contatore copre anche l'aggiornamento dopo la creazione di un broker, che è lo stesso difetto. È coerente con la decisione del developer;
  2. **lo spinner sì**: quello che il pulsante usa già per l'upload, senza chiavi i18n;
  3. **niente E2**: V1, V2 ed E1 coprono il blocco, e il blocco chiude anche la seconda faccia, cioè l'avviso del broker sbagliato;
  4. il piano qui, col numero 44;
  5. nello stesso checkpoint, il piano 41 (la nota del treno 43 e la decisione F-AI (a)) e la voce F-AI (b) nella sezione I del backlog;
  6. la sezione M non si tocca.
  - La riga del CHANGELOG va bene così (§8).

## 1. Il difetto

In `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` (righe della base):

- l'apertura (l'`$effect` di `:2522-2530`) lancia `loadBrokers()` (`:2611-2616`). Questa attende i broker, i tipi e i plugin, e solo dopo scrive `brokers`;
- il pulsante «Avanti: Seleziona File» (`import-wizard-next`, `:5374-5389`) guarda solo `step1CanProceed`, `uploading` e `step1Continuing`. Quindi si può premere prima che `brokers` sia arrivato;
- `goNext()` carica i file e chiama `loadBrokerFiles()` (`:3510-3557`). Questa legge `brokers.map(...)` (`:3512`) da una lista vuota, e così tutti i pannelli del passo 2 (`{#each brokers}`, `:4622`) si aprono chiusi e il file caricato non compare;
- **la seconda faccia**: anche `reviewDefaultPluginMismatches` (`:3323`) legge `brokers`, per l'avviso del broker sbagliato;
- **lo stesso difetto dopo la creazione di un broker** dal passo 1: l'`oncreated` di BrokerModal (`:5921-5935`) aggiorna `brokers` con `refreshAllBrokers().then(...)`, senza nessun segnale;
- **un difetto vicino**: `loadBrokers` non ha `try/finally`. Se `ensureTypesLoaded` rifiuta, `data-busy` resta `true` per sempre e il rifiuto non è gestito.

## 2. La cura (A+B)

- **A**: finché i broker non sono arrivati, `brokersLoading` disabilita «Avanti» e mostra lo spinner dell'upload. Lo usa anche `goNext()` come guardia, come fa già con `step1Continuing`.
- **B**: un contatore dei caricamenti in corso. L'apertura e l'aggiornamento dopo `oncreated` lo incrementano, e `brokersLoading` torna falso solo quando sono finiti tutti.
- `loadBrokers` usa `Promise.allSettled` e un `finally`. Un errore dei tipi non blocca il pulsante, perché lo store lo registra già.
- Niente chiavi i18n, niente ricalcolo dei pannelli, niente backend.

> **⚠️ Fuori pista** (2026-10-12, preparazione, prima del codice): l'analisi proponeva un contatore `$state` e un `$derived(brokerLoads > 0)`. Non va: `loadBrokers()` gira dentro l'`$effect` d'apertura, e `brokerLoads += 1` legge e scrive lo stesso segnale. L'effetto ne diventerebbe dipendente e ripartirebbe a ogni caricamento, cioè un ricaricamento senza fine o `effect_update_depth_exceeded`. Il file documenta già lo stesso rischio per `importPluginsRequest` (`:3713-3716`). Quindi il contatore è una variabile semplice, non reattiva, e il segnale resta il `brokersLoading` che c'è già. Il comportamento visibile non cambia.

## 3. Superfici

| File | Cosa | Chi |
|---|---|---|
| `frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte` | la cura (§2) | I |
| `frontend/src/lib/components/transactions/modals/ImportWizardModal.test.ts` | V1–V4b e le 3 riparazioni (§4) | `test-author` |
| `frontend/e2e/transactions/tx-import-upload.spec.ts` | E1 (§4) | `test-author` |
| questo piano; `BACKLOG_POST_1.2.md` (solo la sezione I); il piano 41 | il journal | I |

- **Nessun file del runner**: i test sono già registrati in `front-utility component-unit`, `front-utility onboarding-component-unit` e `front-transaction tx-import-upload`.
- **Fuori**: le chiavi i18n, la sezione M del backlog, `refreshEditableBrokers()` (`:1951`) e `openBrokerOpeningEditById` (`:1929`), che sono dei passi successivi.

## 4. I test

**Vitest**, in `ImportWizardModal.test.ts`, con i mock che ci sono già:

- **V1**: con `ensureBrokersLoaded` in sospeso, «Avanti» è disabilitato e il passo 1 ha `data-busy="true"`. Quando la promessa si risolve, il pulsante si abilita. Oggi è rosso;
- **V2**: un click durante il caricamento non lascia il passo 1 e non chiede la lista dei file. Oggi è rosso;
- **V3**: se `ensureTypesLoaded` rifiuta, `data-busy` torna `false` e il pulsante si abilita. Oggi è rosso;
- **V4**: dopo un `oncreated`, con `refreshAllBrokers` in sospeso, «Avanti» resta disabilitato finché l'aggiornamento non finisce. Oggi è rosso;
- **V4b**: l'aggiornamento finisce prima del caricamento iniziale, che è ancora in sospeso. Il pulsante resta disabilitato finché non finiscono entrambi. È la ragione del contatore;
- **le 3 riparazioni** (`:497`, `:531`, `:546`): oggi premono «Avanti» subito dopo il mount. Prima del click devono aspettare `data-busy="false"`, come fa già `:340`.

**E2E**: E1, in `tx-import-upload.spec.ts`, in un `describe` suo. Trattiene le richieste dei plugin dell'import, apre il wizard e verifica che, mentre il passo 1 è occupato, «Avanti» sia disabilitato. Poi rilascia le richieste: il pulsante si abilita, e il click porta al passo 2. Nessuna scrittura nel backend.

## 5. Selettori

Sulla corsia, uno alla volta:

1. `front-utility onboarding-component-unit` (prima coi filtri per nome, poi intero);
2. `front-utility component-unit`;
3. `front-transaction`: `tx-import-upload`, `tx-import-flow`, `tx-brim-import`, `tx-import-broker-mismatch`, `tx-import-file-selection`, `tx-bulk-import-handoff`, `tx-import-report-set-guide`;
4. `front-utility onboarding-tour`, `front-broker detail`;
5. Prettier e `svelte-check` sui file toccati.

## 6. Definition of done

- I rossi di V1–V4b ed E1 sono registrati prima della cura, e falliscono per la ragione giusta.
- Dopo la cura, i selettori di §5 sono verdi, e lo sono anche Prettier e `svelte-check`.
- Niente chiavi i18n, nessun file del runner, la sezione M intatta.
- Il journal è aggiornato: questo piano, la sezione I del backlog e il piano 41.
- Il checkpoint ha il manifest e i messaggi di commit; la porta 6157 è libera; poi FROZEN.

## 7. Avanzamento

### S0 — La base ✅ 2026-10-12

> **Note implementazione**: HEAD = `dev_release2` = `378338fed`, worktree pulita, il file dell'agente tracciato, la porta 6157 libera, la cartella della corsia presente, i binari del frontend in `frontend/node_modules/.bin`. Le righe di §1 sono verificate sulla base.

### S1 — I rossi, via `test-author` ✅ 2026-10-12

> **Note implementazione**: `test-author` ha scritto i test senza toccare il componente.
>
> - **Vitest**, in `ImportWizardModal.test.ts` (+220/−1):
>   - un probe di BrokerModal, che registra le props e rende comunque il componente vero, come il wrapper di ImportWizardModal;
>   - il `describe` «ImportWizardModal — step 1 waits for the broker list», con V1–V4b;
>   - le 3 riparazioni, che prima di premere «Avanti» aspettano `data-busy="false"`. In più aspettano anche il contenuto del passo 2 (`import-wizard-step2`), perché `data-step-id` è fisso sul nodo dello stepper e non prova che il passo sia cambiato.
> - **E2E**: E1, in `tx-import-upload.spec.ts` (+55), in un `describe` suo. Trattiene `**/api/v1/brokers/import/plugins*` e lo rilascia anche in un `finally`.
> - **Comandi**, uno alla volta, tutti con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`:
>   1. `front-utility onboarding-component-unit "step 1 waits for the broker list" "onboarding guide integration"`: 5 rossi, 10 verdi (tutto il `describe` della guida, riparazioni comprese), 1 errore (`/tmp/libreFolio_i_m16_vitest_red.log`);
>   2. lo stesso senza filtri: 15 file, 1 rosso; 5 test rossi e 429 verdi su 434, 1 errore (`/tmp/libreFolio_i_m16_vitest_full.log`). I rossi sono solo V1–V4b;
>   3. `front-transaction tx-import-upload "E1 "`: 1 rosso (`/tmp/libreFolio_i_m16_e2e_red.log`). Il runner ha ripopolato il DB della corsia.
> - **Le ragioni dei rossi**, tutte quelle giuste:
>   - V1, V4 e V4b falliscono su `toBeDisabled()`: «Avanti» è abilitato mentre il caricamento è trattenuto. Le precondizioni (il loader chiamato, `data-busy="true"`) passano;
>   - V2: il click dato durante il caricamento porta al passo 2;
>   - V3: `data-busy` resta `"true"`. In più Vitest segnala un «Unhandled Rejection» (`Errors 1 error`), che basta da solo a far uscire il runner con 1: lo toglie solo una cura che gestisce il rifiuto;
>   - E1 fallisce a `:262` («Avanti» abilitato per 5 s col passo 1 occupato), dopo che entrambe le precondizioni sono passate.
> - **Statici**: Prettier e `svelte-check` (0/0) passano sui due file. `tsc -p tsconfig.e2e.json` non segnala errori nei file toccati; ne segnala 2 in file che il lotto non tocca, `e2e/onboarding-tour.spec.ts:863` e `src/lib/types/files.ts:9`.
> - La porta 6157 è libera alla fine (`lsof` vuoto).

### S2 — La cura ✅ 2026-10-12

> **Note implementazione**: 5 punti in `ImportWizardModal.svelte`, nessuna chiave i18n e nessun ricalcolo dei pannelli.
>
> 1. **Il contatore**: `brokerLoadsInFlight`, una variabile semplice accanto a `brokersLoading` (`:669-675`).
> 2. **`trackBrokerLoad(load)`** (`:2617-2631`):
>    - incrementa il contatore e accende `brokersLoading`;
>    - nel `finally` lo decrementa e ricalcola `brokersLoading = brokerLoadsInFlight > 0`. Se un caricamento fallisce, il passo 1 non resta occupato.
> 3. **`loadBrokers()`** passa da `trackBrokerLoad` e usa `Promise.allSettled` (`:2633-2640`).
>    - Prima c'era `Promise.all`: un rifiuto (di fatto solo `ensureTypesLoaded`, che rilancia) lasciava `brokersLoading` a `true` per sempre e produceva l'«Unhandled Rejection» di V3.
>    - Ogni loader registra già il proprio errore nel log, quindi `allSettled` non ne perde nessuno.
> 4. **`goNext`** (`:3147`) esce anche con `brokersLoading`, oltre che con `step1Continuing`. Serve perché Svelte 5 con la delega degli eventi può chiamare il gestore anche su un pulsante disabilitato (`svelte/src/internal/client/dom/elements/events.js:252-262`).
> 5. **«Avanti»** (`:5403-5407`) aggiunge `brokersLoading` sia a `disabled` sia alla condizione dello spinner. È lo stesso `LoadingSpinner` dell'upload.
> 6. **`oncreated` di BrokerModal** (`:5955-5958`): il ricaricamento dopo la creazione (B) passa da `trackBrokerLoad`. Legge sempre `getEditableBrokers()` dopo `refreshAllBrokers()`.
>
> Restano come sono:
> - `data-busy={brokersLoading || uploading}` (`:4495`), che ora segue il contatore;
> - `resetState()`, che non azzera il contatore: un caricamento ancora in volo lo decrementerebbe poi sotto zero.
>
> Il commento sul rischio dell'effetto a `:3738-3740` resta esatto, perché `loadBrokers()` gira ancora dentro l'effetto d'apertura.

### S3 — I verdi Vitest ✅ 2026-10-12

> **Note implementazione**: tre comandi, uno alla volta, con lo stesso prefisso di S1. Tutti hanno dato exit 0, senza «Unhandled Rejection».
>
> 1. `front-utility onboarding-component-unit "step 1 waits for the broker list" "onboarding guide integration"`: 15 verdi, 419 saltati (`/tmp/libreFolio_i_m16_vitest_green_filtered.log`);
> 2. `front-utility onboarding-component-unit`: 15 file, 434/434 verdi (`/tmp/libreFolio_i_m16_vitest_green_full.log`);
> 3. `front-utility component-unit`: 112 file, 2983/2983 verdi (`/tmp/libreFolio_i_m16_component_unit.log`).
>
> V1–V4b passano a verde con la cura e le 3 riparazioni restano verdi. L'errore di V3 non c'è più: il rifiuto ora lo gestisce `allSettled`.

### S4 — Gli E2E ✅ 2026-10-12

> **Note implementazione**: 9 selettori, uno alla volta sulla 6157, con lo stesso prefisso di S1. Tutti exit 0, nessun rosso e nessun flaky.
>
> | Selettore | Esito | Log (`/tmp/libreFolio_i_m16_…`) |
> |---|---|---|
> | `front-transaction tx-import-upload` (intero, E1 compreso) | 10 verdi | `e2e_upload.log` |
> | `front-transaction tx-import-flow` | 10 verdi | `e2e_flow.log` |
> | `front-transaction tx-brim-import` | 8 verdi | `e2e_brim.log` |
> | `front-transaction tx-import-broker-mismatch` | 4 verdi | `e2e_mismatch.log` |
> | `front-transaction tx-import-file-selection` | 2 verdi | `e2e_filesel.log` |
> | `front-transaction tx-bulk-import-handoff` | 3 verdi | `e2e_handoff.log` |
> | `front-transaction tx-import-report-set-guide` | 2 verdi | `e2e_setguide.log` |
> | `front-utility onboarding-tour` | 10 verdi | `e2e_tour.log` |
> | `front-broker detail` | 37 verdi | `e2e_brokerdetail.log` |
>
> - **La build era quella con la cura.** Il primo comando ha ricostruito il frontend all'avvio del backend condiviso: `build/index.html` è delle 10:48:59, la modifica del componente delle 10:44:02, e il chunk servito contiene `trackBrokerLoad`. Per questo il runner ha poi scritto «Frontend build is up to date».
> - **I click su «Avanti» negli altri spec restano compatibili.** `click()` di Playwright aspetta che il pulsante sia abilitato, e non c'è un `actionTimeout` nel config.

> **⚠️ Fuori pista — la galleria**: la galleria non l'ho lanciata, perché riscriverebbe gli screenshot tracciati. L'ho letta.
>
> - **Compatibili**:
>   - i preludi a `gallery.spec.ts:3274`, `:3345`, `:5607` e `galleryReportSets.ts:815` aspettano già il `data-busy` del passo 1;
>   - lo scatto del passo 2 (`:3234`) preme «Avanti» senza `waitForSettled`, cioè proprio il caso del difetto. Ora il click aspetta il pulsante abilitato, quindi il passo 2 apre i pannelli giusti.
> - **Una gara sul clock**: lo scatto «import wizard step 1» (`:3186-3203`) aspetta solo il passo 1 visibile più 300 ms. Se il caricamento dei plugin supera quei 300 ms, «Avanti» compare con lo spinner. La riga che manca è `await waitForSettled(page.getByTestId('import-wizard-step1'));` prima dello scatto.
> - **La riga va a M.** Decisione del coordinatore (2026-10-12): M sta già modificando `gallery.spec.ts` per M-14, quindi la mette lì e la verifica con la galleria completa. M-16 si chiude senza.

### S5 — Prettier e `svelte-check` ✅ 2026-10-12

> **Note implementazione**:
> - `frontend/node_modules/.bin/prettier --check` sui 3 file toccati: «All matched files use Prettier code style!» (`/tmp/libreFolio_i_m16_prettier.log`);
> - `npm run check`, cioè `svelte-kit sync && svelte-check`: 0 errori e 0 avvisi (`/tmp/libreFolio_i_m16_svelte_check_post.log`).

### S6 — Il journal: la sezione I del backlog e il piano 41 ✅ 2026-10-12

> **Note implementazione**: solo documenti, nessun test.
>
> - **`BACKLOG_POST_1.2.md`, solo la sezione I**:
>   - l'introduzione porta la decisione del developer su F-AI: la (a) nella 1.2, cioè niente; la (b) dopo, «con un codice tipizzato»;
>   - la voce **F-AI (b)**, dopo la ✅ F e prima di B1. È il testo pronto del piano 41 (§15, «F-AI»), con il codice tipizzato su `OtherPeriodEffect` al posto della costante condivisa; per questo la stima sale a ¾ g più la sonda;
>   - le righe citate sono verificate su `378338fed`.
>
>   La sezione M (M-16) non è toccata.
> - **Il piano 41**:
>   - la testa: F-C3 e il treno 43 fra le consegne nel target, la decisione su F-AI al posto di «Aperto», la base;
>   - in §9, le righe F-AI, T8 e F-C3;
>   - in §15, il titolo di «F-AI» a ✅ con la decisione, e la nota nuova «Treno 43 e F-AI».
> - `git diff --check` pulito.
>
> **⚠️ Fuori pista**:
> - **Il letterale «FX on cash» è scivolato** da `portfolio_service.py:2001` (`5d62658bb`) a `:1978`, con i riordini di T (`1cc9cd8f5`, `a57a43fbd`). Nel backlog c'è la riga nuova.
> - **Il secondo confronto nel frontend** (`PerformanceChart.svelte:291`) l'ho cercato con `git log -S`: viene dal mio stesso F-W (`9a0d9280c`), come quello di `OtherPeriodEffectsTable.svelte:75`. Quindi non è codice nuovo di altri. La voce li cita tutti e due, perché il codice tipizzato li sostituisce entrambi.

### S7 — Il checkpoint ✅ 2026-10-12

> **Note implementazione**:
> - **6 percorsi**, niente in stage: 5 modificati e 1 nuovo, questo piano.
> - **Due commit proposti.** I messaggi sono in ASCII in `/tmp/libreFolio_commit_i_m16_msg_C{1,2}.txt`; accanto ci sono i percorsi e i blob (`…_paths_*`, `…_blobs_*`):
>   1. C1 `fix(import): gate wizard Next on broker load`: il componente, il test Vitest e lo spec E2E;
>   2. C2 `docs(journal): plan 44, F-AI (b) in backlog I`: questo piano, la sezione I del backlog e il piano 41.
> - **Controlli**:
>   - `git diff --check` pulito, anche sul file nuovo;
>   - la scansione privacy delle righe aggiunte è pulita.
> - **Esclusi**, perché ignorati o di runtime:
>   - `frontend/build`, `.svelte-kit`, `test-results`, `playwright-report`, `.testLog`;
>   - i log `/tmp/libreFolio_i_m16_*`.
>
>   Il `backend/data/test/sqlite/app.db` della worktree è di settembre, non di questo lotto.
> - La porta 6157 è libera (`lsof` vuoto). Poi FROZEN.

## 8. CHANGELOG (proposta, la scrive il coordinatore)

- 🐛 Fixed: «The import wizard keeps Next disabled until your brokers have loaded, so a quick click no longer opens file selection with the uploaded files hidden».
