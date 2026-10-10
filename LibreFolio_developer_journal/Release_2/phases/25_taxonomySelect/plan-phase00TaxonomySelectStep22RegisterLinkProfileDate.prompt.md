# Piano — K / step 22: «Register here» a registrazione chiusa, la data del profilo nella lingua dell'app

> Lotto approvato dal developer (testuale, via coordinator, 09/10 09:41): «anche 5 se si può è meglio, idem per 6 e 7»
> e «14 pure se si puù migliorare è meglio.» A K vanno il 7 e il 14. Viene dallo step 21
> ([`plan-phase00TaxonomySelectStep21PureDefects.prompt.md`](plan-phase00TaxonomySelectStep21PureDefects.prompt.md)).

| | |
|---|---|
| **Baseline** | `9b2acdd5d` = `dev_release2` (treno 21), pulita; lo step 21 (`be4283e5f`, `65c1e40e6`, `59e3f4bc6`) è in HEAD |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`, preambolo `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` |
| **Ordine** | test rossi prima, via test-author, solo in file già registrati; poi la cura; poi gate e checkpoint. Il CHANGELOG lo scrive il coordinator. |
| **Vincoli** | niente cataloghi: una chiave nuova si chiede a O tramite il coordinator. `scripts/test_runner/_frontend_utility.py` è aperto da M: non si tocca. |
| **Conflitti** | nessuno dei 17 rami locali tocca, dalla merge-base, i file del lotto (verificato il 09/10, 09:55 e 11:00, FileGrid compreso). **Eccezione**, segnalata dal coordinator alle 11:14: il checkpoint S21 di O (treno 22) cambia anche `LoginCard.svelte` e `LoginCard.test.ts` (errori di login `{key}\|{message}`, `AuthError`, `AuthErrorKey`). Merge simulato dal coordinator: `LoginCard.svelte` si fonde da solo; `LoginCard.test.ts` ha due conflitti additivi (intestazione con gli import, e i `describe` in fondo). Alla fusione del target in K si tengono entrambe le parti, poi si rilanciano `LoginCard.test.ts` e `auth.spec.ts`. K non tocca la parte errori di `LoginCard`. |

## Punto 7: «Register here» resta visibile a registrazione chiusa

- **Stato verificato sul codice**:
  - `LoginCard.svelte:102-108`: il blocco con «auth.noAccount» e il pulsante `goto-register` si disegna sempre.
  - `backend/app/api/v1/auth.py:190-192`: `if not registration_enabled and not is_first_user` → 403 «New user
    registration is disabled». Il rifiuto arriva solo dopo l'invio di `RegisterCard`.
  - **Già in v1.1.0**: sul tag, `LoginCard.svelte:92` e `auth.py:189-191` sono uguali.
- **Dove il frontend conosce già lo stato**: nessun endpoint nuovo serve.
  - `GET /api/v1/settings/global` è pubblico (`settings.py:293-303`, «Public read access»), e lo era già in v1.1.0.
  - Lo legge lo store `stores/app/globalSettings.ts` (`load()`), con una cache in localStorage (`global_settings`).
    Lo usano già `appBootstrap`, `settings.ts`, la pagina dei file e `GlobalSettingsTab`.
  - Il tipo `GlobalSettings` oggi non elenca `enable_registration`; il ciclo di `load()` copia le chiavi che non conosce
    come stringhe grezze.
  - Le righe dei global settings si creano all'avvio con i default (`main.py:293`, `initialize_global_settings`):
    `enable_registration` = `'true'`, tipo `bool`.
- **Cura**:
  1. `globalSettings.ts`: `enable_registration: boolean` nel tipo, default `true` come `GLOBAL_SETTINGS_DEFAULTS`.
     `load()` lo legge come il backend (`_convert_value`, tipo `bool`): vero se `value.toLowerCase()` è uno di
     `true`, `1`, `yes`, `on`.
  2. `LoginCard.svelte`: al mount chiede `globalSettings.load()` (pubblico; se fallisce restano i valori della cache o i
     default). Il blocco del link si disegna solo con `$globalSettings.enable_registration`.
  - **Si apre in caso di dubbio**: il link sparisce solo se il server ha detto «chiusa», ora o nell'ultima risposta in
    cache. Un errore o una chiave assente lasciano il link: il backend rifiuta comunque, come oggi.
- **Limite dichiarato, nessun endpoint**: il backend accetta la registrazione anche a registrazione chiusa se non c'è
  nessun utente (`is_first_user`). Il frontend non può sapere quanti utenti ci sono senza un endpoint nuovo. Dal prodotto
  il caso non si raggiunge: si chiude solo da amministratore, e l'ultimo amministratore non può cancellare il proprio
  account (`auth.py:300`).
- **Non toccati**: `GlobalSettingsTab.syncGlobalSettingsStore` (passa un `Partial`, e la pagina di login ricarica al
  mount), `RegisterCard` (il rifiuto del backend resta), la root `+page.svelte`.

## Punto 14: la data di creazione del profilo segue la lingua del browser

- **Stato verificato sul codice**: `ProfileTab.svelte:18-26`, `formatDate` usa `toLocaleDateString(undefined,
  {year: 'numeric', month: 'long', day: 'numeric'})`; il template, `:478`, chiama `formatDate($currentUser?.created_at)`.
  **Già in v1.1.0** (`ProfileTab.svelte:17-24` sul tag).
- **Come il resto dell'interfaccia**: la lingua dell'app è `currentLanguage` (`stores/app/language.ts:100`), allineata al
  `locale` di svelte-i18n. `LotCustodyModal.svelte:67` formatta la stessa data lunga con
  `toLocaleDateString($currentLanguage || undefined, …)`; `LotComparisonChart` e `AllocationHistoryChart` fanno lo stesso.
- **Cura**: `formatDate(dateStr, lang)` con `toLocaleDateString(lang || undefined, …)`, e il template passa
  `$currentLanguage`.
  - La lingua entra nell'espressione del template, quindi la data segue un cambio di lingua senza ricaricare. Il
    componente è in modalità legacy: uno store letto dentro il corpo della funzione non verrebbe tracciato.
- **Fuori perimetro, da riferire al checkpoint**: altre date formattate nella lingua del browser, stessa classe. Lista
  completa dalla scansione in sola lettura del 09/10 (`/tmp/libreFolio_k22_browser_locale_scan.txt`, numeri esclusi):
  - `components/table/dataTableLogic.ts:326`, `:328`, `:342`, `:344`: la cella data/ora generica delle DataTable;
  - `utils/transactions/importReportSets.ts:287` e `ImportWizardModal.svelte:3604`;
  - `TransactionBulkModal.svelte:1870-1871`, `AssetEventPicker.svelte:188`, `EventCreateMiniModal.svelte:155`;
  - `GlobalSettingsTab.svelte:726` (anche «Last updated:» scritto fisso) e `:755`, `SchedulerLogModal.svelte:222`;
  - `FileGrid.svelte:73` e `files/+page.svelte:685` (`formatDateTime` senza lingua, scelta dichiarata nel suo commento);
  - `brokers/[id]/+page.svelte:442`, `assets/[id]/+page.svelte:3515`.

## Aggiunta: le dimensioni dei file nella griglia (FileGrid)

> Approvata dal developer (testuale, via coordinator, 09/10 10:53): «si a entrambe le cose». L'ha trovata M: nella
> griglia delle risorse statiche le dimensioni (B/KB; in francese o/Ko) non seguono il cambio di lingua. È lo stesso
> tipo del punto 14: devono seguire la lingua dell'app, in modo reattivo.

- **Stato verificato sul codice**:
  - `FileGrid.svelte:177` disegna `{formatBytes(file.size_bytes)}`. Il componente è in modalità runes.
  - `formatBytes` (`utils/files/upload.ts:45-57`) legge il traduttore con `get(_)`: una lettura una tantum, che nessun
    effetto traccia. L'espressione si ricalcola solo quando cambia il file, mai quando cambia la lingua.
  - Le unità cambiano solo in francese: `o`, `Ko`, `Mo`, `Go` contro `B`, `KB`, `MB`, `GB` in EN/IT/ES (`common.bytes` …
    `common.gigabytes`). Nessuna chiave nuova.
- **Cura**: `formatBytes(bytes, translate = get(_))`, con il traduttore come secondo parametro facoltativo; FileGrid passa
  `$t` dal template: `{formatBytes(file.size_bytes, $t)}`. Letto lì, lo store è tracciato. Gli altri chiamanti non
  cambiano.
- **Preparazione neutra, prima del rosso**: la dimensione è avvolta in uno
  `<span data-testid="file-grid-size-<id>">`. Così il test la trova con un `data-testid` e fallisce sull'unità, non sulla
  ricerca dell'elemento. Il testo non cambia.
- **Stesso schema, fuori perimetro, da riferire**: `formatBytes` senza traduttore tracciato in `FileUploader.svelte:241`,
  `FileEditModal.svelte:165`, `ImportWizardModal.svelte:3301`, `DataTableColumnFilter.svelte:913-917`, `FilePreviewModal.svelte:113` e `files/+page.svelte:916`. La data della stessa
  griglia (`FileGrid.svelte:73`, `formatDateTime` senza lingua) è già nella lista del punto 14.
  - `DataTable.svelte:1265`, la vista a lista dei file, segue già il cambio di lingua (misurato dal test-author):
    `FilesTable` ricalcola le colonne, e con loro `formatBytes`.

## Test (rossi prima, test-author; solo file già registrati)

1. **Punto 7, componente**: `src/lib/components/auth/LoginCard.test.ts` (`component-unit`, `_frontend_utility.py:246`).
   - Lo store `globalSettings` è finto: uno store scrivibile e una spia su `load`.
   - Casi: chiusa → nessun `goto-register`; aperta → presente; chiave assente (una cache vecchia) → presente; `load`
     chiamato al mount.
   - Rosso oggi: a registrazione chiusa il link c'è, e `load` non viene chiamato.
2. **Punto 7, E2E**: `e2e/auth.spec.ts` (`front-utility auth`).
   - La pagina di login riceve la risposta vera di `GET /api/v1/settings/global`, modificata con `page.route` e
     `route.fetch()` così che `enable_registration` valga `'false'`: `goto-register` non c'è. Senza modifica (default
     aperta) c'è.
   - Non tocca il global setting condiviso dalla corsia: nessuna scrittura.
3. **Punto 14, componente**: `src/lib/components/settings/tabs/ProfileTab.test.ts` (`component-unit`, `:277`).
   - `$lib/stores/app/language` è finto, con uno store scrivibile.
   - Per ognuna delle 4 lingue dell'app, la data di creazione è quella di `toLocaleDateString(lingua, …)`; e dopo il
     mount un cambio di lingua la ridisegna.
   - Rosso oggi su ogni lingua il cui formato differisce da quello dell'ambiente: almeno 3 su 4. Un controllo prova che
     il test discrimina sull'ambiente in cui gira.
4. **FileGrid, E2E**: `e2e/files-uploader.spec.ts` (`front-utility files-uploader`, API sintetiche, desktop e mobile).
   - Nella vista a griglia, la lingua passa da EN a FR dal selettore dell'header, che cambia solo lo stato client
     (`currentLanguage.set`, nessuna scrittura). `file-grid-size-<id>` passa da `128 B` a `128 o`, con le unità lette dai
     cataloghi quando il test gira.
   - Rosso oggi: resta `128 B`.
5. **Lo store**: `src/lib/stores/app/settings.test.ts` (`core-unit`). `globalSettings.load()` legge
   `enable_registration` come il backend legge un `bool`; una risposta senza la riga vale «aperta»; un caricamento
   fallito tiene il valore.

## Passi

- [x] 22.1 Base `9b2acdd5d` verificata pulita; codice letto; v1.1.0 verificato; piano nel repo. ✅ 2026-10-09.
- [x] 22.2 Rossi (test-author), nei tre file sopra, più lo store e FileGrid. ✅ 2026-10-09.
  > **Note implementazione** (punto 7, test-author):
  > - `LoginCard.test.ts`: un `describe` nuovo con 5 casi; lo store `globalSettings` è finto (uno store scrivibile e una
  >   spia `load`) e resta inerte finché il componente non lo importa.
  >   - Comando: `node_modules/.bin/vitest run src/lib/components/auth/LoginCard.test.ts`: 3 rossi, 10 verdi; gli 8
  >     esistenti restano verdi (`/tmp/libreFolio_k22_red_login_unit.log`).
  >   - Rossi: chiusa → il link e «auth.noAccount» ci sono; aperta → chiusa dopo il mount → il link resta; `load`
  >     chiamato 0 volte invece di 1.
  >   - Verdi oggi, com'è giusto: aperta → il link c'è; chiave assente (una cache vecchia) → il link c'è.
  > - `e2e/auth.spec.ts`: un `describe` nuovo con 1 test. Su questa pagina soltanto, la risposta vera di
  >   `GET /api/v1/settings/global` arriva con il solo `enable_registration` a `'false'`. Nessuna scrittura sul setting
  >   condiviso dalla corsia.
  >   - Comando: `dev.py test --workers 2 --test-port 6155 --data-dir /tmp/librefolio-r2-k front-utility auth`: 28 verdi e
  >     1 rosso, il nuovo (`/tmp/libreFolio_k22_red_auth_e2e.log`).
  >   - Il rosso: «The login page never read GET /api/v1/settings/global» (0 letture in 10 s, asserzione soft), poi
  >     `goto-register` atteso 0, trovato 1.
  >   - Il filtro dell'azione `auth` raccoglie anche i 3 test di `layout/app-start-auth.spec.ts`, solo sul progetto
  >     desktop.
  > - **Decisioni** (K, 09/10):
  >   - La condizione è `!== false`, non «vero»: una chiave assente lascia il link. Con «vero» il caso 3 diventava rosso
  >     (prova del test-author su una copia in `/tmp`).
  >   - Le cache scritte prima della cura hanno `enable_registration` come stringa (`load()` copiava grezze le chiavi che
  >     non conosceva). Con una stringa `'false'` il link si vede fino alla prima `load()` riuscita. Si apre in caso di
  >     dubbio: accettato, senza test.
  >   - `front check` sulla base, con `svelte-kit sync`: 0/0. I 2 errori pac-allocator visti dal test-author venivano da
  >     svelte-check lanciato senza sync.
  > - **Lo store** (`settings.test.ts`, chiesto dopo, allo stesso test-author): un `describe` nuovo per
  >   `globalSettings.load()`.
  >   - Comando: `node_modules/.bin/vitest run src/lib/stores/app/settings.test.ts`: 14 rossi e 6 verdi
  >     (`/tmp/libreFolio_k22_red_store_unit.log`). I 5 test esistenti e la guardia sul caricamento fallito sono verdi:
  >     il `catch` di oggi tiene già i valori.
  >   - I rossi: `'true'`, `'True'`, `'TRUE'`, `'1'`, `'yes'`, `'On'` attesi `true`; `'false'`, `'FALSE'`, `'0'`, `'no'`,
  >     `'off'`, `''`, `'enabled'` attesi `false`. Oggi arriva la stringa grezza. In più, la risposta senza la riga:
  >     atteso `true`, ricevuto `undefined`.
  >   - `'enabled'` non è in nessuna delle due liste: prova che vale «vero» solo per i quattro valori del backend.
  >   - Ogni caso controlla prima che lo store abbia preso la sua risposta (un `default_currency` testimone), così un
  >     `load()` fallito in silenzio non fa passare a vuoto i casi «vero».
  >   - Stesso esito, 14 e 6, con due ordini casuali.
  > **⚠️ Fuori pista**: la sessione si è fermata per un errore dopo i due rossi (segnalato dal coordinator alle 10:38).
  > Nessun comando bloccato: i due test-author avevano finito, e le porte 6155 e 6165 erano libere. Ripreso dallo stato del
  > worktree.
  > **Note implementazione** (punto 14, test-author):
  > - `ProfileTab.test.ts`: un `describe` nuovo con 6 test, in fondo al file.
  >   - Comando: `node_modules/.bin/vitest run src/lib/components/settings/tabs/ProfileTab.test.ts`: 4 rossi e 47 verdi;
  >     i 45 test esistenti restano verdi (`/tmp/libreFolio_k22_red_profile_unit.log`).
  > - Ambiente: `en-US` (`LANG=C.UTF-8`, TZ Europe/Rome, Node 26.8.2, ICU 78.3).
  > - I rossi:
  >   - `it`: atteso «5 marzo 2024», ricevuto «March 5, 2024»;
  >   - `fr`: atteso «5 mars 2024»;
  >   - `es`: atteso «5 de marzo de 2024»;
  >   - il cambio di lingua dopo il mount: la riga resta «March 5, 2024».
  > - `en` è verde oggi perché `en-US` scrive la data come `en`. Il controllo prova che 3 lingue su 4 discriminano su
  >   questa macchina, e ne riporta il locale nel titolo.
  > - Provato anche con `LANG=it_IT.UTF-8`: rossi `en`, `fr`, `es` e il cambio di lingua. Su qualunque macchina restano
  >   almeno 3 rossi su 4, più il cambio.
  > - La cura simulata in memoria (una config vitest scratch in `/tmp/k22_sim`, che riscrive il componente al caricamento
  >   senza toccare il file):
  >   - la cura del piano porta 51/51 verdi;
  >   - una cura incompleta, che legge lo store dentro `formatDate` e lascia il template com'è, lascia rosso solo il cambio
  >     di lingua. Conferma che in un componente legacy uno store si traccia solo se il template lo legge.
  > - Il mock di `$lib/stores/app/language` è uno store intero, senza `importOriginal`: lo store vero accetta solo le
  >   lingue del mock di `$lib/i18n` (`en`, `it`) e porterebbe `fr` ed `es` a `en`.
  > - La riga si trova come nel test già esistente: per la chiave `settings.accountCreated` e la sua `.setting-row`.
  >   Nessun `data-testid` nuovo.
  > **Note implementazione** (FileGrid, un terzo test-author):
  > - `e2e/files-uploader.spec.ts`: un test nuovo, sulle API sintetiche della fixture `uploaderPage`, desktop e mobile.
  >   - Comando: `dev.py test --workers 2 --test-port 6155 --data-dir /tmp/librefolio-r2-k front-utility files-uploader`:
  >     8 test, 6 verdi e 2 rossi, cioè il nuovo sui due progetti (`/tmp/libreFolio_k22_red_filegrid_e2e.log`).
  >   - Il rosso: `file-grid-size-<id>` atteso «128 o», ricevuto «128 B» dopo il passaggio a FR.
  >   - Il cambio di lingua è avvenuto davvero: `<html lang="fr">`, e il `title` del pulsante di anteprima della stessa
  >     scheda passa da «Preview» ad «Aperçu». FileGrid ridisegna in francese; solo la dimensione resta inglese.
  >   - Il cambio è lato client (`setLanguage()`, il selettore dell'header): nessuna richiesta rifiutata dalla fixture,
  >     nessuna riga aggiunta alla sua tabella.
  >   - L'ultima asserzione vuole lo stesso nodo di prima: ridisegnato al suo posto, senza ricaricare né rimontare.
  > - Sonda in sola lettura, poi tolta: la vista a lista (`FilesTable` su DataTable) segue già il cambio di lingua, da
  >   «128 B» a «128 o». Una griglia aperta dopo il cambio legge la lingua nuova. Il difetto c'è solo con la griglia già
  >   a schermo. Per questo `DataTable.svelte:1265` esce dalla lista dei fuori perimetro.
- [x] 22.3 Cura: `globalSettings.ts`, `LoginCard.svelte`, `ProfileTab.svelte`; poi `upload.ts` e `FileGrid.svelte`. ✅ 2026-10-09.
  > **Note implementazione** (parziale, 09/10):
  > - `LoginCard.svelte`:
  >   - `onMount(() => void globalSettings.load())`;
  >   - il blocco «auth.noAccount» con `goto-register` dentro `{#if $globalSettings.enable_registration !== false}`.
  > - `ProfileTab.svelte`: importa `currentLanguage`; `formatDate(dateStr, lang)` con `toLocaleDateString(lang ||
  >   undefined, …)`; il template passa `$currentLanguage`.
  > - `globalSettings.ts`:
  >   - `enable_registration: boolean` nel tipo, default `true`;
  >   - `load()` lo legge con `BACKEND_TRUE_VALUES.has(value.toLowerCase())`, cioè `true`, `1`, `yes` e `on`, come
  >     `_convert_value`.
  > - Verifica:
  >   - `vitest run LoginCard.test.ts ProfileTab.test.ts`: 64/64 (`/tmp/libreFolio_k22_green_components.log`);
  >   - `vitest run settings.test.ts LoginCard.test.ts`: 33/33 (`/tmp/libreFolio_k22_green_store.log`).
  > - FileGrid, preparazione neutra prima del rosso: `<span data-testid="file-grid-size-<id>">` attorno alla dimensione.
  > - FileGrid, dopo il rosso:
  >   - `formatBytes(bytes, translate = get(_))`: il traduttore è un parametro facoltativo, e il commento spiega che
  >     `get()` non è tracciato;
  >   - FileGrid passa `$t`: `{formatBytes(file.size_bytes, $t)}`. Gli altri chiamanti non cambiano.
  > - Prettier: nessuna modifica sui 10 file del lotto; `git diff --check` pulito.
- [x] 22.4 Gate, corsia 6155, in sequenza: ✅ 2026-10-09.
  - `front build --debug`, `front check`;
  - `front-utility core-unit` (`settings.test.ts` importa `globalSettings`) e `component-unit`;
  - E2E `front-utility auth`, `settings`, `app-start-auth`, `files-uploader`, `image-crop` (FileGrid compatta nel
    selettore di immagini); `check-orphans`.
  > **Note implementazione**:
  > - Comando: `/tmp/libreFolio_k22_gates.sh`, log `/tmp/libreFolio_k22_gates.log`; E2E con `--workers 2`.
  > - Risultati:
  >   - build ok, svelte-check 0/0; `front check` 0/0;
  >   - `core-unit`: 118 file, 3467 verdi; `component-unit`: 111 file, 2910 verdi;
  >   - `auth` 29/29: il test nuovo della registrazione chiusa e i 3 di `app-start-auth`;
  >   - `app-start-auth` 3/3; `files-uploader` 8/8: il test nuovo, desktop e mobile; `image-crop` 42/42;
  >   - `check-orphans` ok; a fine corsa nessun ascoltatore su 6155.
  > - **`settings`: 44 verdi e 1 rosso**, `settings.spec.ts:540`, «About Tab › installed signals section lists the
  >   signals the backend reports»: `about-installed-signals` non trovato in 3 s. Triage:
  >   - il test e `AboutTab.svelte` non sono toccati dal lotto, e non cambiano da settembre;
  >   - AboutTab non importa nessun modulo cambiato;
  >   - la sezione sta dentro `{#if !isLoading}`, che si chiude solo quando tutte e 5 le richieste del `Promise.all` hanno
  >     risposto (`system/info`, provider, plugin, i due cataloghi di segnali);
  >   - l'expect ha il budget globale di 3 s (`playwright.config.ts:109`), e la macchina era a carico 33-44;
  >   - le prove: allo step 21 lo stesso test passava in 4,7 s, e qui è fallito a 7,7 s. Rilanciata l'unità `settings`,
  >     45/45, con `:540` in 3,0 s (`/tmp/libreFolio_k22_g_settings_rerun.log`).
  >   - **Verdetto: lentezza, non un difetto del lotto.** Va nel backlog: o la scheda mostra le sezioni man mano che
  >     arrivano, o espone il suo stato di caricamento e il test lo attende.
  > **⚠️ Fuori pista**: il rosso di `settings` e il suo rilancio. Le prove di Playwright (`test-results/`) erano già state
  > cancellate dall'esecuzione successiva dello script: il triage si è fatto sul log.
- [x] 22.5 Handoff: CHECKPOINT READY al coordinator con le frasi per il CHANGELOG, poi FROZEN. ✅ 2026-10-09.
  > **Note implementazione**:
  > - Quattro commit proposti in `/tmp/libreFolio_commits/`, manifesto `k-22-manifest.txt`:
  >   - `k-61-auth-register-link.txt`;
  >   - `k-62-profile-date-language.txt`;
  >   - `k-63-files-grid-sizes.txt`;
  >   - `k-64-journal-22.txt`.
  > - Verificati sul tag v1.1.0, e quindi «Fixed» per una versione rilasciata: tutti e tre i difetti.
  >   - Il link: `LoginCard.svelte:92`, con il rifiuto in `auth.py:189-191`.
  >   - La data: `ProfileTab.svelte:17-24`.
  >   - Le dimensioni: `FileGrid.svelte:177` con `formatBytes` e `get(_)`; in francese `o`/`Ko`.
  > - Alla fusione del target con S21 di O: conflitti additivi in `LoginCard.test.ts`, come da tabella iniziale.

## Definizione di fatto

1. Ogni test nuovo è rosso sulla base, per la ragione attesa, e verde dopo la cura.
2. I gate sono verdi e `front check` resta a 0/0.
3. Nessun catalogo, nessun file del runner; porte libere, nessun venv del worktree, nel worktree solo i file previsti.

## Seguito

- Lo step 23 corregge il Bulk: il clone di righe singole dello stesso tipo, che diventavano una coppia, e il falso
  «Scartare le modifiche?» dopo Reset su una coppia salvata o con la cache dei tipi ancora vuota.
  [`plan-phase00TaxonomySelectStep23BulkCloneAndDiscardGuard.prompt.md`](plan-phase00TaxonomySelectStep23BulkCloneAndDiscardGuard.prompt.md).
