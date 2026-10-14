# Piano — fase 00, 48: la rifinitura UI (BrokerIcon, la modale del broker sbagliato, il pannello della sicurezza, M-20, V-19)

> **Stato**: ✅ chiuso il 2026-10-12, checkpoint al coordinatore (§8, passo 7). Fermo dalle 18:26 alle 19:24 (STOP del developer via coordinatore); ripreso al «riparti» del coordinatore, con la decisione (b) sul reperto di copy-and-go (§8, passo 4). **Seguito**: il lotto 49, la corsa dei contatori di `asset-detail.spec.ts` (§8, passo 5, «Fuori pista»; [piano della 49](../49_requestCountRace/plan-phase00RequestCountRace.prompt.md)).
>
> - **Mandato**: coordinatore di Release 2 (`c8328a01-…`). È la voce della coda di I dopo il piano 47. M-17 è passato a T, dentro M-18.
> - **Workstream I**. Ramo `e-alfy-performance-charts-plan`. Base `55304116f` (treno 60).
> - **Corsia**: `--test-port 6157 --data-dir /tmp/librefolio-r2-i-charts`, con `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; un comando alla volta. Mai le porte 6040 e 6041, mai la galleria.
> - **Origine**:
>   - BrokerIcon, la modale e il pannello: le segnalazioni del developer durante le verifiche sul server;
>   - M-20: la sezione M di `BACKLOG_POST_1.2.md`. La voce la chiude M quando la cura è nel target: questo lotto non tocca la sezione M.

## 0. Autorizzazione (2026-10-12)

- **Developer**, sull'analisi di I, testuale: «Via, così com'è».
- **Coordinatore**, «via all'implementazione»:
  - **BrokerIcon**: l'icona viene dal plugin, quindi H1 è confermata. La cura è in due parti: ogni evento va alla sua immagine, e lo stato del plugin parte sincrono dalla cache;
  - **il pannello**: il timer si ferma finché il puntatore o il fuoco sono dentro l'indicatore, e riparte da 30 s quando escono. Ritoccato il 12/10 con la scelta (b), vedi sotto;
  - **il pannello, scelta (b)**, coordinatore, 12/10: «Il puntatore ferma il timer dentro tutto l'indicatore, con gli eventi pointer; il fuoco lo ferma solo dentro i dettagli (motivo e link), non sul toggle; all'uscita riparte da 30 s. Resta nello spirito di quanto approvato dallo sviluppatore». Il motivo del ritocco:
    - Chrome, e Firefox su Windows e Linux, danno il fuoco al bottone cliccato. Con la regola di prima, chi apre il pannello col mouse lascia il fuoco sul toggle, e il timer resta fermo finché non clicca altrove: il pannello resterebbe aperto per sempre;
    - l'alternativa (a), il fuoco solo se `:focus-visible`, dipende dalle euristiche del browser, e jsdom non distingue la tastiera dal mouse;
    - la correzione sulla galleria (`parkPointer` prima dello scatto) la gira il coordinatore a M quando il lotto entra;
  - **M-20 (b): sì**. Prima la regola del rifiuto entra nell'helper, con un test in `clipboard.test.ts`; poi migrano FilesTable e FileGrid. Il lancio sincrono e la firma restano;
  - **M-17 passa a T**: `DateRangePicker.svelte`, `GlobalSettingsTab.svelte` e `DataEditor.svelte` non si toccano;
  - **H3 e H2** vanno nella sezione I del backlog, priorità bassa, scritte nel checkpoint;
    - **ritocco**, coordinatore, 12/10: su richiesta del developer le ha scritte lui nella sezione C del backlog (`bf831ef10`), come **C-56 (H3)** e **C-57 (H2)**. La sezione I non le riporta; questo piano le cita per ID;
  - **il piano qui**, col numero 48;
  - **i file del runner**:
    - `_frontend_broker.py` è di I;
    - `_frontend_utility.py` non è di I. Il 12/10 il coordinatore lo ha dato a T, per il CP1 di M-18: T aggiunge i suoi Vitest alle liste di `core-unit` e `component-unit`, la stessa lista del gate. Dopo il checkpoint di T il file va a I o a M, a chi è pronto per primo, e il coordinatore lo comunica. Intanto il file del gate si prepara, e si registra solo dopo l'avviso;
    - **l'avviso**, coordinatore, 12/10 sera: «Da adesso `scripts/test_runner/_frontend_utility.py` è tuo». Il lotto 28 di M (treno 70, `b063b16ca`) aggiunge `front_docs_offline_math` e il suo `add_test(… "docs-offline-math" …)` subito dopo `connection-security`; la base di I resta `55304116f` e il target arriva al checkpoint con un merge. Le aggiunte di I stanno lontane da quel blocco;
  - **i cataloghi** sono di I per questo lotto, solo via `dev.py i18n`. Si cambiano i valori di `importWizard.brokerMismatch.remove` e `.move` nelle 4 lingue e si aggiunge `assets.probe.copyErrorDetail`. Nel checkpoint va l'elenco di chiavi e valori, per U;
  - **ProviderAssignmentSection**: I tocca prima `:591-596`, poi T tocca le durate a `:585` e `:616` sopra la modifica di I;
  - **i siti di formattazione** nei file del lotto non si toccano: I li segnala al coordinatore (fatto il 12/10, per T);
  - **la consegna**:
    - un commit per voce, più un commit del journal;
    - la riga 🐛 di M-20 la scrive il coordinatore, col testo di I (§7);
    - la doc che cita i testi della modale e il rischio del timer per la galleria vanno a M, dopo;
    - si chiude con un checkpoint (manifest e messaggi), poi FROZEN con la 6157 libera.
- **V-19 entra nel lotto**, coordinatore, 12/10, sull'analisi di I: la ricalibrazione D5 delle due soglie `denseRow`, dashboard 950→990 e dettaglio dell'asset 850→890, in un commit a parte (C5) prima del journal. Niente riga di CHANGELOG: «Exportación IA» viene da `7c66234a7` e non è mai uscita (la 1.1 aveva «Exportar IA»). L'allineamento del padding del trigger di AiExportMenu ai vicini (`px-2.5 gap-1.5`) va in fondo alla sezione I del backlog, dopo la 1.2: da solo darebbe circa 12 px contro gli 11,8 px di sforamento (corretto al passo 5: lo sforamento peggiore è 18,8 px, quindi da solo non basterebbe). La nota devWiki va a W tramite il coordinatore. Dopo la cura, gli stessi selettori uno alla volta; col carico alto (80–190) uno sweep che va in timeout si rilancia prima di cercarne la causa.

## 1. I difetti

### 1.1 BrokerIcon: la valigetta al primo caricamento (regressione nata nella 1.2)

Parole del developer: «l'icona del broker, anche se impostata, la prima volta che la pagina lo apre mostra la valigetta, poi si fa f5 e l'icona compare, ma solo per l'icona grande… stesso difetto in broker global»; poi «Al primo caricamento mostra la valigetta fino a F5… la cura deve coprire anche questa superficie» (il selettore della Dashboard).

- Le superfici segnalate passano le props piene: la pagina del broker (`brokers/[id]/+page.svelte:469`), la BrokerCard (`:92`) e il selettore della Dashboard (`dashboard/+page.svelte:930`).
- **La causa (H1), una corsa fra due `<img>` nel `{#key}` di `BrokerIcon.svelte` (`:62-64`)**:
  - in `brokerIconChain.svelte.ts` lo stato del plugin (`pluginIconUrl`, `:52`) parte `null` anche con la cache calda, e lo imposta l'effetto `:56-76` dopo il primo render;
  - l'ordine dei candidati (`:82-102`, da `d5c649e9f`): `icon_url` → l'icona del plugin fatto per il broker (P) → `/favicon.ico` del portale → l'icona del plugin generico;
  - quindi il primo render mostra la favicon, poi arriva P e il `{#key}` crea una seconda `<img>`;
  - l'errore della favicon arriva dopo, dall'`<img>` staccata. Svelte 5.48.0 compila `onload` e `onerror` in `$.event(…)`, che toglie il listener solo da `body`, `window`, `document` e dagli elementi media (`svelte/src/internal/client/dom/elements/events.js:111-127`): quello dell'`<img>` resta;
  - `handleError()` (`:151-156`) marca il candidato **corrente**, cioè P, non l'URL che ha fallito. Torna la favicon, fallisce, non resta nessun candidato: la valigetta;
  - `failedUrls` si azzera solo quando cambiano le props (`:108-122`), quindi resta così fino a F5.
- Con una favicon valida il difetto è solo estetico: il `load` dell'`<img>` staccata (`handleLoad()`, `:147-149`) mette `imageLoaded = true` mentre P carica ancora.
- Nella 1.1.0 la favicon veniva prima del plugin, quindi niente scambio e niente corsa: nessuna riga 🐛.
- **Fuori dalla cura** (nel backlog, sezione C, priorità bassa: C-56 e C-57, scritte dal coordinatore in `bf831ef10`; §0):
  - **H3 (C-56), le props vuote**: nessuna superficie segnalata passa props vuote, e BrokerBadge riempie già i campi mancanti dallo store (`BrokerBadge.svelte:46-63`). Un chiamante che passasse a `BrokerIcon` il solo id partirebbe dalla valigetta. Se si fa, `settledIconFieldIds` resta (`brokerStoreIconHydration.test.ts`);
  - **H2 (C-57), la lista dei plugin che fallisce**: `ensurePluginIconsLoaded` (`brokerHelpers.ts:52`) mette una cache vuota e non riprova (`:66`), e le chiamate dopo (`brokerStore.ts:148`, `:156`) escono subito. È un'ipotesi sul sintomo: serve un rosso con la lista che fallisce una volta sola.

### 1.2 La modale del broker sbagliato: i bottoni vanno a capo (modale nuova nella 1.2)

Parole del developer: «i bottoni hanno i testi che vanno a capo e restano larghi, magari il rimuovi può essere accorciato, e anche lo sposta può diventare senza il nome del broker».

- `ImportBrokerMismatchModal.svelte`: il footer `:153-167`. `.modal-footer` (`:385`) è un flex senza `flex-wrap`, quindi i bottoni si stringono e il testo va a capo dentro il bottone; `.btn` a `:401`, senza `white-space`. `ModalBase` è `max-w-lg` (`:87`), cioè 32rem; sotto i 544 px la modale è larga quanto lo schermo meno 2rem (`ModalBase.svelte`, `.modal-backdrop` `padding: 1rem`, `.modal-content` `overflow: hidden`).
- Move mostra l'icona del broker scelto più «Sposta in {broker}» (`:164`).

### 1.3 Il pannello di ConnectionSecurityIndicator (funzione nuova nella 1.2)

Parole del developer: «un clic sul testo che spiega il livello chiude il pannello; il pannello si chiude da solo dopo 30 secondi».

- `ConnectionSecurityIndicator.svelte`: `detailsOpen` (`:47`), `toggle()` (`:58-65`), i dettagli (`:85`) col motivo `<p data-testid="connection-security-reason">` (`:87`). Nessun timer, nessun clic sul testo.

### 1.4 M-20 · I pulsanti «copia» senza il ripiego per l'HTTP (🐛, 1.1.0)

- Il browser non dà l'API degli appunti a una pagina `http://` fuori da `localhost`. `writeTextToClipboard` (`utils/clipboard.ts:14`) ha il ripiego `execCommand`, ma:
  - **cinque chiamate dirette** non lo usano: `AboutTab.svelte:242`, `UnifiedLotsTable.svelte:391`, `AskAdminModal.svelte:30`, `FilePreviewModal.svelte:377`, `ProviderAssignmentSection.svelte:595`;
  - **due copie private** del ripiego: `FilesTable.svelte:523-550` ripiega anche quando l'API sicura **rifiuta**, una regola che l'helper non ha; `FileGrid.svelte:96-118` è in linea e non controlla l'esito di `execCommand`.
- `aiExportClipboard.ts:155-176` resta com'è: ha già il ripiego, errori tipizzati e un writer iniettabile.
- In `ProviderAssignmentSection` ci sono anche due testi fissi in inglese: il toast `:596` e il `title="Copy error detail"` `:591`.

### 1.5 V-19 · «Exportación IA» esce dalla barra in spagnolo (nato nella 1.2)

- Trovato da V nel triage del piano 46 (`front-utility all` a 4 worker), ripetuto a 1 worker: deterministico. Backlog V-19, dato a I dal coordinatore il 12/10.
- Il rosso, riprodotto da I: `front-utility toolbar-width-sweep "es: 1700"`, 2 rossi e 3 verdi (`/tmp/libreFolio_i_v19_sweep_es_red.log`):
  - dashboard: in `denseRow`, barre di 957–967 px (vw 1320→1310) fuori misura, al massimo +11,0 px;
  - dettaglio dell'asset: barre di 857–867 px (vw 1220→1210, più 859 a vw 940), al massimo +11,8 px.
- **Corretto al passo 5**: +11,0 e +11,8 px sono solo i punti dove cade la griglia dello sweep, a passi di 10 px. Il gruppo delle azioni in `denseRow` chiede sempre 968 px sulla dashboard e 868,8 px sull'asset. Alle soglie vecchie il caso peggiore è la barra larga quanto la soglia, 950 e 850 px: +18,0 e +18,8 px. La griglia dipende dalla gutter della barra di scorrimento misurata al caricamento: 15 px in questa corsa, 0 nella successiva. A parità di vw la barra cambia di 15 px, il bisogno no.
- Il meccanismo: in `denseRow` la zona delle azioni è `grid grid-cols-2 *:w-full`, quindi ogni colonna è larga quanto l'etichetta più larga, «Exportación IA» (`px-3 gap-2`), e il gruppo esce dalla barra. Le soglie oggi: `denseRow: 950` (`dashboard/+page.svelte:829`, `oneRow` 1000) e `denseRow: 850` (`assets/[id]/+page.svelte:2773`).

## 2. La cura e la divisione in commit

- **C1, BrokerIcon**:
  - `handleLoad(event?)` e `handleError(event?)` leggono l'URL dall'`<img>` dell'evento (`currentTarget.getAttribute('src')`), con ripiego sul candidato corrente quando l'evento manca. Un errore marca quell'URL; `imageLoaded` cambia solo se l'URL è quello corrente;
  - lo stato del plugin parte dalla cache sincrona alla creazione della catena: con la cache calda il primo render mostra già P, senza scambio e senza la richiesta alla favicon di un terzo;
  - `settledIconFieldIds` resta: è il contratto contro il giro infinito (`brokerStoreIconHydration.test.ts`);
  - un `data-testid` sull'`<img>` e uno sulla valigetta, attributi additivi per il test del componente.
- **C2, la modale**:
  - i valori di `importWizard.brokerMismatch.remove` e `.move`, via `dev.py i18n` (tabella in §3). `move` perde `{broker}`, e la chiamata a `:164` non passa più `values`;
  - CSS: `white-space: nowrap` su `.btn`, quindi nessun testo va più a capo dentro un bottone. Il footer può andare a capo fra un bottone e l'altro (`flex-wrap: wrap`, allineato a destra). A 375 px la modale è larga 343 px e restano circa 267 px per i tre bottoni, mentre in it e fr ne servono circa 300 (stima, da misurare nell'E2E). Con un footer che non va a capo, Move verrebbe tagliato dall'`overflow: hidden`. L'analisi diceva «un footer che non va a capo»: vedi §8, passo 2. Move tiene l'icona del broker scelto, senza `title`.
- **C3, il pannello**:
  - il motivo diventa un `<button type="button">` con l'aspetto del testo e lo stesso testid; un clic chiude il pannello. Solo il motivo: non il link, non l'avviso;
  - chiusura da sola dopo 30 s: un `$effect` con `setTimeout`, avviato all'apertura, cancellato alla chiusura e allo smontaggio;
  - il timer si ferma finché il puntatore è dentro l'intero indicatore (eventi pointer, così al tocco riparte quando si alza il dito) o il fuoco è dentro i dettagli, cioè sul motivo o sul link, non sul toggle. Quando escono, riparte da 30 s. Precedente: `Tooltip.svelte:81`. Scelta (b), §0.
- **C4, M-20**:
  - prima l'helper: `writeTextToClipboard` ripiega su `execCommand` anche quando l'API sicura rifiuta. Il lancio sincrono quando non c'è nessuna via (`clipboard.test.ts:91,105`; `SocialShareModal.svelte:94`) e la firma restano;
  - poi le sette chiamate passano dall'helper: le cinque dirette, FilesTable e FileGrid;
  - in `ProviderAssignmentSection` il toast diventa `common.copiedToClipboard` e il `title` la chiave nuova `assets.probe.copyErrorDetail`;
  - un gate nuovo, `src/clipboardSink.gate.test.ts`, sul modello di `htmlSink.gate.test.ts`: nessun `navigator.clipboard.writeText` fuori da `utils/clipboard.ts`, con l'eccezione rivista di `aiExportClipboard.ts`. Si registra in `_frontend_utility.py` solo dopo l'avviso del coordinatore (§0); l'avviso è arrivato il 12/10 sera, e il gate è in `core-unit` (§8 passo 4).
- **C5, V-19**: le due soglie `denseRow` sopra la barra più larga che non entra, con margine: dashboard 950→990 (sotto `oneRow` 1000), dettaglio dell'asset 850→890. Nessun test fissa 950 o 850; la barra dello spec `ai-export-panel` (circa 942 px) resta in `stackFilters`.
- **C6, il journal**: questo piano, che cita H3 e H2 come C-56 e C-57 (sezione C del backlog, del coordinatore). Nella sezione I di `BACKLOG_POST_1.2.md`, in fondo, solo le voci nuove nate dal lotto: il padding del trigger di AiExportMenu (§0, V-19).

I cataloghi cambiano in C2 e in C4. Per questo, dopo ogni commit verde, I salva lo stato dei suoi file nei file della sessione (`uipolish_commit_bundle/stage_C{n}/`), e il manifest del checkpoint dà un blob per stadio.

## 3. Superfici

| File | Cosa | Commit | Chi |
|---|---|---|---|
| `frontend/src/lib/utils/broker/brokerIconChain.svelte.ts` | l'evento attribuito alla sua immagine, lo stato sincrono | C1 | I |
| `frontend/src/lib/components/brokers/BrokerIcon.svelte` | i due `data-testid` | C1 | I |
| `frontend/src/lib/components/brokers/BrokerIcon.test.ts` (nuovo) | i rossi del componente | C1 | `test-author` |
| `frontend/src/lib/utils/broker/__tests__/brokerIconChain.test.ts` | il caso dell'errore di un URL non corrente | C1 | `test-author` |
| `scripts/test_runner/_frontend_broker.py` | la registrazione di `BrokerIcon.test.ts` | C1 | I |
| `frontend/src/lib/components/transactions/modals/ImportBrokerMismatchModal.svelte` | la chiamata a `move` e il CSS | C2 | I |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | i valori di `remove` e `move` (C2); la chiave `assets.probe.copyErrorDetail` (C4) | C2, C4 | I, via `dev.py i18n` |
| `ImportBrokerMismatchModal.test.ts`, `frontend/e2e/transactions/tx-import-broker-mismatch.spec.ts` | gli assert sul bottone Move | C2 | `test-author` |
| `frontend/src/lib/components/layout/ConnectionSecurityIndicator.svelte` | il motivo come bottone, il timer | C3 | I |
| `ConnectionSecurityIndicator.test.ts` | i rossi coi timer finti | C3 | `test-author` |
| `frontend/src/lib/utils/clipboard.ts`, `clipboard.test.ts` | il ripiego sul rifiuto e il suo test | C4 | I, `test-author` |
| `AboutTab.svelte`, `UnifiedLotsTable.svelte` (solo `:391`), `AskAdminModal.svelte`, `FilePreviewModal.svelte`, `ProviderAssignmentSection.svelte` (solo `:591-596`), `FilesTable.svelte`, `FileGrid.svelte` | le chiamate all'helper | C4 | I |
| `frontend/src/clipboardSink.gate.test.ts` (nuovo) | il gate | C4 | `test-author` |
| `AboutTab.test.ts`, `FilePreviewModal.test.ts`, `ProviderAssignmentSection.test.ts` | i rossi HTTP e lo stub di `isSecureContext` nel percorso sicuro | C4 | `test-author` |
| `frontend/e2e/support-copy-and-go.spec.ts` (aggiunto il 12/10, via del coordinatore) | il test del rifiuto con i due trasporti negati; il caso nuovo del limite noto: l'API sicura rifiuta dopo `window.open`, nessun ripiego | C4 | `test-author` |
| `scripts/test_runner/_frontend_utility.py` (di I dal 12/10 sera, §0) | il gate in `core-unit`; le descrizioni di `core-unit` e di `support-copy-and-go` | C4 | I |
| `frontend/src/routes/(app)/dashboard/+page.svelte` (solo `:829`), `frontend/src/routes/(app)/assets/[id]/+page.svelte` (solo `:2773`) | le soglie `denseRow` | C5 | I |
| questo piano; `BACKLOG_POST_1.2.md` (solo la sezione I, in fondo) | il journal | C6 | I |

**I valori i18n** (per U):

| Chiave | en | it | fr | es | Commit |
|---|---|---|---|---|---|
| `importWizard.brokerMismatch.remove` (valore) | Remove | Rimuovi | Retirer | Quitar | C2 |
| `importWizard.brokerMismatch.move` (valore, senza `{broker}`) | Move | Sposta | Déplacer | Mover | C2 |
| `assets.probe.copyErrorDetail` (nuova) | Copy error detail | Copia il dettaglio dell'errore | Copier le détail de l'erreur | Copiar el detalle del error | C4 |

- **Fuori**: `DateRangePicker.svelte`, `GlobalSettingsTab.svelte` e `DataEditor.svelte` (M-17, di T); i siti di formattazione dei file del lotto (M-18, di T); `gallery.spec.ts` (di M); la doc che cita i testi della modale (`user/transactions/import/how-to.*.md`, `developer/frontend/components/features/import-wizard.md:162`), che va a M; `aiExportClipboard.ts`; la sezione M del backlog.

## 4. I test

Tutti via `test-author`, rossi prima della cura, un giro per voce.

- **C1**:
  - `BrokerIcon.test.ts` (jsdom): con la cache calda e le props piene, la prima `<img>` mostra già P; con la cache fredda, dopo lo scambio un `error` sull'`<img>` staccata della favicon lascia P a schermo, e un suo `load` non toglie la valigetta finché P non carica;
  - `brokerIconChain.test.ts`: un errore attribuito a un URL non corrente lascia il corrente com'è.
- **C2**:
  - gli assert che cercano il nome del broker nel bottone Move (unit `ImportBrokerMismatchModal.test.ts`, E2E `tx-import-broker-mismatch.spec.ts`);
  - un caso E2E sul layout, in it e fr, su desktop e a 375 px: ogni bottone è alto una riga e sta tutto dentro la modale. Nell'analisi era facoltativo; ora serve, perché il CSS dipende dalla larghezza (§2).
- **C3**, con `vi.useFakeTimers`: il clic sul motivo chiude; a 30 s si chiude; il puntatore dentro l'indicatore ferma il timer, e all'uscita riparte da 30 s; il fuoco dentro i dettagli lo ferma, quello sul toggle no (§0, scelta b); la chiusura a mano cancella il timer.
- **C4**:
  - `clipboard.test.ts`: l'API sicura rifiuta, il ripiego copia; il lancio sincrono resta;
  - il gate;
  - i rossi HTTP (`isSecureContext = false` più uno stub di `execCommand`) negli host esistenti: `AboutTab.test.ts`, `FilePreviewModal.test.ts`, `ProviderAssignmentSection.test.ts`. AskAdminModal e UnifiedLotsTable non hanno un host: li copre il gate;
  - jsdom 30.0.1 non ha `isSecureContext` né `execCommand`: i test che stubbano solo `navigator.clipboard` stubbano anche `isSecureContext = true`;
  - E2E `support-copy-and-go.spec.ts` (aggiunto il 12/10, §8 passo 4): il test del rifiuto nega anche `execCommand` e verifica che il ripiego sia stato tentato una volta; un caso nuovo fissa il comportamento noto (scelta b, §8 passo 4): l'API sicura rifiuta subito, dentro il task del clic e dopo `window.open`; il vero `execCommand` di Chromium risponde `false`, la modale va in errore, chiude la scheda e lascia gli appunti veri come erano. La premessa è asserita: al rifiuto `navigator.userActivation.isActive` vale `false`.

## 5. Selettori

Sulla corsia, uno alla volta:

1. `front-broker broker-unit`;
2. `front-transaction tx-unit`, `front-transaction tx-import-broker-mismatch`, `front-transaction tx-import-scalable-transfers`;
3. `front-utility component-unit`, `front-utility core-unit`, `front-utility connection-security`, `front-utility support-copy-and-go` (aggiunto il 12/10, §8 passo 4);
4. V-19: `front-utility toolbar-width-sweep` (intero), `front-ai-export panel`, `front-portfolio broker-filter-label`, `front-portfolio dashboard`, `front-asset asset-detail`;
5. statici: `dev.py front check` e `prettier --check` sui file toccati; `git diff --check`.

La galleria non si lancia.

## 6. Definizione di fatto

- Ogni rosso visto rosso prima della cura, poi verde.
- I selettori di §5 verdi, `front check` a 0 errori.
- Il piano aggiornato dopo ogni passo.
- H3 e H2 sono nel backlog come C-56 e C-57 (le ha scritte il coordinatore); le voci nuove del lotto, se ce ne sono, in fondo alla sezione I.
- Il checkpoint ha manifest, partizione in C1–C6, istantanee per stadio, messaggi e l'elenco i18n per U. La porta 6157 è libera.

## 7. CHANGELOG (lo scrive il coordinatore)

- M-20, 🐛: «Copy buttons also work on plain HTTP addresses, such as a LAN IP or Tailscale.»
- BrokerIcon, la modale e il pannello: nessuna riga, sono nati nella 1.2.

## 8. Avanzamento

- [x] **0. Analisi** (2026-10-12): approvata dal developer e dal coordinatore (§0). Il rapporto sui siti di formattazione per M-18 è andato al coordinatore il 12/10.
- [x] **1. C1, BrokerIcon** (2026-10-12): i rossi, la cura, i selettori, l'istantanea.
  > **Note implementazione**:
  > - **I rossi** (`test-author`): `BrokerIcon.test.ts` nuovo, 3 casi (con la cache calda la prima e unica `<img>` è P; un `error` tardivo dell'`<img>` staccata della favicon lascia P; un suo `load` tardivo non toglie la valigetta), più un caso in `brokerIconChain.test.ts` (l'errore attribuito alla favicon, non a P). Visti rossi da I: `Tests 4 failed | 5 passed (9)` (`/tmp/libreFolio_i_ui_c1_red_verify.log`), ciascuno sull'assert per cui è scritto.
  > - **La cura** (`brokerIconChain.svelte.ts`): `eventUrl(event)` legge `currentTarget.getAttribute('src')`, con ripiego sull'URL corrente quando l'evento manca (i casi della catena che chiamano `handleError()` senza evento restano uguali). `handleError` marca quell'URL e azzera `imageLoaded` solo se è il corrente; `handleLoad` mette `imageLoaded` solo per il corrente. Lo stato del plugin parte da `getPluginIconUrl`/`isFallbackPluginCode`, sincroni; l'effetto resta per i cambi di props e per la cache fredda. L'interfaccia dichiara `(event?: Event) => void`.
  > - **Verde**: i due file `9 passed` (`/tmp/libreFolio_i_ui_c1_green.log`); `front-broker broker-unit` sulla 6157 `5 files, 57 passed` (`/tmp/libreFolio_i_ui_c1_broker_unit.log`); `BrokerBadge.test.ts` e `brokerStoreIconHydration.test.ts`, lanciati a parte, `15 passed`. Prettier invariato.
  > - **Il runner**: `BrokerIcon.test.ts` registrato in `front_broker_unit` (`_frontend_broker.py`), con la docstring e la descrizione del catalogo.
  >
  > **⚠️ Fuori pista**:
  > - `BrokerIcon.svelte` non cambia gli handler: Svelte passa l'evento a `onload={chain.handleLoad}`, e per un evento lanciato sull'`<img>` stessa il suo involucro non tocca `currentTarget` (in `handle_event_propagation` il bersaglio coincide con l'elemento ed esce subito). Nel componente restano solo i due testid.
  > - `test-author` ha sostituito `lucide-svelte` con un `Briefcase` inerte: con i moduli rifatti a ogni caso il barile delle icone (circa 1.900 moduli) mandava ogni caso oltre i 5 s. Per lo stesso motivo è sostituito lo store dei broker, che lo ritira dentro coi role helper; il test verifica che BrokerIcon non lo chiami mai, con le props piene.
  > - Il caso della catena tiene anche `walkChain(...) = [P]`: la favicon resta fallita fino al cambio delle props, quindi niente seconda richiesta a un URL che fallisce.
- [x] **2. C2, la modale** (2026-10-12): i rossi, i valori i18n, il CSS, i selettori, l'istantanea.
  > **Note implementazione**:
  > - **I rossi** (`test-author`), visti rossi da I:
  >   - unit: `Tests 3 failed | 14 passed (17)` (`/tmp/libreFolio_i_ui_c2_red_unit_verify.log`), i tre casi che cercavano il nome del broker nel bottone Move;
  >   - E2E: M4 e M5 rossi, M1–M3 verdi (`/tmp/libreFolio_i_ui_c2_red_e2e.log`). M5, con le etichette di prima: a 1280 px in it Remove, Keep e Move vanno a capo su 2, 2 e 3 righe, in fr su 3, 3 e 3; a 375 px Move va su 6 righe ed esce dal footer `[16, 344]`, `[236.1, 386.3]` in it e `[227.9, 378.1]` in fr.
  > - **I valori**: `dev.py i18n update` sulle due chiavi (`/tmp/libreFolio_i_ui_c2_i18n.log`), tabella di §3. I quattro cataloghi cambiano di 2 righe ciascuno e le chiavi restano allineate.
  > - **La cura** (`ImportBrokerMismatchModal.svelte`):
  >   - `:164` chiama `move` senza `values`;
  >   - il testid `import-broker-mismatch-footer` sul footer;
  >   - `.modal-footer` va a capo fra un bottone e l'altro, allineato a destra (`flex-wrap: wrap; justify-content: flex-end`, con un commento);
  >   - `.btn` ha `white-space: nowrap`.
  > - **Verde**:
  >   - il file unit, `17 passed` (`/tmp/libreFolio_i_ui_c2_unit.log`);
  >   - sulla 6157, uno alla volta:
  >     - `front-transaction tx-unit`, `22 files, 881 passed` (`/tmp/libreFolio_i_ui_c2_txunit.log`);
  >     - `tx-import-broker-mismatch`, `5 passed` (`…_c2_e2e_mismatch.log`);
  >     - `tx-import-scalable-transfers`, `4 passed` (`…_c2_e2e_scalable.log`);
  >   - `prettier --check` pulito sui file del passo e sui quattro cataloghi.
  > - **La misura**, dalle geometrie che M5 allega (`/tmp/libreFolio_i_ui_c2_m5_geometry.txt`):
  >
  >   | Lingua, larghezza | Remove | Keep | Move | Footer |
  >   |---|---|---|---|---|
  >   | it, 1280 px | [396.5, 482.8] | [648.8, 750.5] | [762.5, 868.5] | [376.5, 888.5], una riga |
  >   | it, 375 px | [36, 122.3] | [222.3, 324] | [218.0, 324] | [16, 344], Move sulla seconda riga |
  >   | fr, 1280 px | [396.5, 474.8] | [621.9, 737.3] | [749.3, 868.5] | [376.5, 888.5], una riga |
  >   | fr, 375 px | [36, 114.3] | [208.7, 324] | [204.8, 324] | [16, 344], Move sulla seconda riga |
  >
  >   Ogni bottone sta su una riga.
  >
  > **⚠️ Fuori pista**:
  > - **Il footer che va a capo serve davvero.**
  >   - L'analisi diceva «un footer che non va a capo»; §2 aveva già messo la deviazione come stima.
  >   - A 375 px restano 288 px di contenuto (da 36 a 324), mentre una riga sola chiede circa 318 px in it e 337 in fr (bottoni più due spazi da 12).
  >   - Move passa sulla seconda riga, allineato a destra (bordo destro 324, come Keep). A 1280 px tutto resta su una riga.
  > - **M5 rilanciato da solo** (`"M5"`, `1 passed`, `/tmp/libreFolio_i_ui_c2_e2e_m5_geometry.log`). Il reporter `list` non stampa gli allegati, e il rapporto HTML della corsa piena era già stato sovrascritto dal selettore seguente. Le geometrie vengono dal rapporto HTML della corsa singola.
  > - **Il guasto di `node`** dopo il `brew upgrade` (17:17–17:26): i verdi del passo sono partiti dopo il via del coordinatore. Nessun comando di I è fallito per l'ambiente.
  > - **Per il coordinatore, nel checkpoint**:
  >   - la descrizione del selettore `tx-import-broker-mismatch` (`_frontend_transaction.py:670-675`, non è un file di I) potrebbe nominare M4 («Move non nomina il broker») e M5 (una riga dentro il footer, it e fr, 1280 e 375 px);
  >   - la doc che cita i testi vecchi della modale va a M (how-to nelle 4 lingue, `import-wizard.md:162`).
- [x] **3. C3, il pannello** (2026-10-12): i rossi, la cura, i selettori, l'istantanea.
  > **Note implementazione**:
  > - **I rossi** (`test-author`, 20 casi nuovi in `ConnectionSecurityIndicator.test.ts`, coi timer finti su `setTimeout`/`clearTimeout` soli): visti rossi da I sul componente intatto, `Tests 20 failed | 14 passed (34)` (`/tmp/libreFolio_i_ui_c3_red_verify.log`). I 14 verdi sono i casi di prima (livelli, link, collassato).
  > - **La cura** (`ConnectionSecurityIndicator.svelte`):
  >   - il motivo è un `<button type="button">` con l'aspetto del testo (`block w-full cursor-pointer text-left`, il preflight azzera padding e bordo ed eredita font e colore) e lo stesso testid. Un clic chiude; se il motivo aveva il fuoco, il fuoco torna al toggle (`toggleEl`, `bind:this`);
  >   - `pointerInside` (`onpointerenter`/`onpointerleave` sulla radice) e `focusInDetails` (`onfocusin`/`onfocusout` sui dettagli; un `focusout` verso un elemento dei dettagli non conta) sono `$state`;
  >   - un `$effect` arma `setTimeout(closeDetails, 30_000)` quando i dettagli sono aperti e niente li tiene, e il teardown lo cancella. Ogni cambio di uno dei tre stati rifà il giro, quindi il conto riparte sempre da 30 s; lo smontaggio lo cancella;
  >   - `closeDetails` azzera anche `focusInDetails`: i dettagli escono dalla pagina col fuoco che avevano, e jsdom (come alcuni browser) non lancia il `focusout`;
  >   - `title={$_('common.close')}` sul motivo, chiave esistente: dice, al passaggio e ai lettori di schermo, che il clic chiude.
  > - **Verde**:
  >   - il file, `34 passed` (`/tmp/libreFolio_i_ui_c3_green.log`); prettier riscrive solo il componente (`/tmp/libreFolio_i_ui_c3_prettier.log`);
  >   - sulla 6157, `front-utility connection-security`, `8 passed` (`/tmp/libreFolio_i_ui_c3_e2e_connsec.log`); porta libera dopo.
  >   - `front-utility component-unit` raccoglie anche `clipboard.test.ts` e `AboutTab.test.ts`, rossi di C4 per costruzione: si lancia al passo 4, a C4 curato.
  >
  > **⚠️ Fuori pista**:
  > - **Niente handle del timer in una variabile.** §2 diceva «un `$effect` con `setTimeout`», il precedente `Tooltip.svelte:81` tiene l'handle in una variabile semplice. Qui l'handle è una costante nella closure dell'effetto: il teardown cancella il timer che il suo giro ha armato, e non legge nessuno `$state` (la nota devWiki `svelte5-teardown-reads-stale-state-timers`, il caso «unmounted after the pointer restarted the countdown» del test).
  > - **Per il coordinatore** (UX): il `title` sul motivo è una scelta di I, non chiesta dal developer; si toglie con una riga se non piace. La galleria apre il pannello: il rischio dei 30 s (`parkPointer`) va a M, come da §0.
- [x] **4. C4, M-20** (2026-10-12): l'helper, il gate, i rossi HTTP, le sette chiamate, la chiave nuova, i selettori, l'istantanea.
  > **In corso** (2026-10-12), nota provvisoria:
  > - rossi (`test-author`) visti rossi da I prima della cura: `5 failed (5)`, `Tests 8 failed | 117 passed (125)` (`/tmp/libreFolio_i_ui_c4_red.log`); il gate elenca 11 trasporti diretti;
  > - cura fatta (helper, 7 siti, chiave via `dev.py i18n add`); i 5 file `125 passed` (`/tmp/libreFolio_i_ui_c4_green.log`); `front-utility component-unit` `112 files, 3022 passed` (`/tmp/libreFolio_i_ui_c4_component_unit.log`);
  > - `front-utility support-copy-and-go` rosso `12 passed, 2 failed` (`/tmp/libreFolio_i_ui_c4_e2e_copygo.log`): lo spec entra in C4 col via del coordinatore, lavoro di `test-author` in corso.
  > - Da fare: rosso dei casi nuovi contro l'helper di base, spec verde, `core-unit`, istantanea.
  >
  > **⏸️ STOP** (2026-10-12 18:26, ordine del developer via coordinatore):
  > - **fatto**: C1–C3 con istantanee e messaggi (bundle di sessione `uipolish_commit_bundle/`); di C4 la cura intera (helper, gate, 7 siti, chiave), i 5 file verdi, `component-unit` verde, il messaggio `messages/C4.txt`.
  > - **a metà**: `support-copy-and-go.spec.ts`, affidato a `test-author` (agente `6553e02c…`). L'agente ha chiuso la corsa che aveva in volo allo STOP e poi non ha lanciato altro. Ha cambiato solo lo spec (+117 −1):
  >   - l'harness ha una spia su `execCommand('copy')` e `denyLegacyCopy()`;
  >   - il test del rifiuto nega i due trasporti;
  >   - il test nuovo è `'goes ahead to the social destination through the legacy copy when the secure clipboard refuses the write'`;
  >   - `16 passed (42.3s)` secondo l'agente (`/tmp/libreFolio_i_ui_c4_ta_full.log`). **Il rosso contro l'helper di base non l'ho ancora visto io.**
  > - **⚠️ Fuori pista, reperto di `test-author`, da decidere al «riparti»**: in un Chromium vero il ripiego sul rifiuto non riesce in copy-and-go.
  >   - `reserveShareTab()` (`window.open`, `SocialShareModal.svelte:96`) consuma il gesto del clic in circa 10 ms. Il rifiuto dell'API sicura arriva dopo (`clipboard.ts:26-28`), quindi `execCommand('copy')` torna `false` e la modale finisce in `copy.failed`.
  >   - Il test nuovo passa solo perché Playwright esegue `page.evaluate` con `userGesture: true`, cioè ridà il gesto quando il test rifiuta la scrittura.
  >   - L'HTTP semplice (M-20) non è toccato: `clipboard.ts:35` copia in modo sincrono dentro il clic, prima di `:96`.
  >   - Non è una regressione: prima di C4 anche un rifiuto finiva in `copy.failed`.
  >   - Opzioni:
  >     - (a) tenere il test, col commento che ne dice il limite;
  >     - (b) riscriverlo perché provi il limite vero: rifiuto da un timer della pagina, senza gesto, quindi `error`;
  >     - (c) cambiare il prodotto in copy-and-go, cioè l'ordine fra copia e scheda, col rischio del blocco dei popup di Safari.
  >   - Le altre copie, che non aprono schede, non sono state misurate.
  >   - `messages/C4.txt`: l'ultima voce («a new case proves the legacy copy in a real browser») è falsa. Va riscritta dopo la decisione.
  > - **non iniziato**: il rosso dei casi dello spec contro l'helper di base, `core-unit`, l'istantanea C4; poi C5 (V-19), C6 (journal), statici, checkpoint.
  > - **worktree**: HEAD `55304116f`, 29 file sporchi (26 modificati, 3 non tracciati), niente in stage. Nessun processo di corsia, 6157 libera (`lsof` exit 1).
  > - **al «riparti»**: prima la decisione sul reperto. Poi il rosso contro l'helper di base: copia di riserva della cura in `/tmp`, `git show HEAD:…`, ripristino verificato con shasum. Poi lo spec intero verde, `core-unit`, l'istantanea.
  >
  > **▶️ Riparti** (2026-10-12 19:24, coordinatore): scelta **(b)**.
  > - Le parole del coordinatore: «riscrivi il test perché provi il limite vero. Il rifiuto arriva da un timer della pagina, senza gesto, quindi `execCommand` fallisce e la modale va nello stato d'errore, con l'asserzione su quello stato. Il prodotto non cambia, e (c) è scartata per il rischio del blocco dei popup in Safari». Nessuna riga nel CHANGELOG.
  > - **Comportamento noto**: in un contesto sicuro, dopo `window.open`, un rifiuto dell'API sicura non può ripiegare sulla copia legacy. La scheda riservata consuma l'attivazione del clic, e senza attivazione Chromium risponde `false` a `execCommand('copy')`: copy-and-go finisce in `copy.failed`, chiude la scheda e mostra l'errore, come prima di C4. Le copie che non aprono schede ripiegano, e l'HTTP semplice (M-20) copia in modo sincrono dentro il clic, prima di `window.open`.
  > - **Perché un timer, e niente `page.evaluate` dopo il clic**: Playwright 1.61 manda ogni `evaluate`, ogni locator e ogni `expect` come `Runtime.callFunctionOn` con `userGesture: true` (`node_modules/playwright-core/lib/coreBundle.js:35169-35180`), cioè ridà l'attivazione alla pagina. Il clic senza `force` fa anche lui un `evaluate` dopo l'azione, lo `stop()` del controllo sul bersaglio (`coreBundle.js:19546-19549`). Le istantanee della traccia usano `Runtime.evaluate` senza gesto (`:35150`).
  > - Corsa del rifacimento affidata a `test-author`, stesso agente.
  >
  > **Note implementazione** (chiusura, 2026-10-12 sera):
  > - **Lo spec** (`test-author`, +143 −1 su HEAD): l'harness registra il rifiuto immediato (`refuseClipboardImmediately`) e l'attivazione al momento del rifiuto (`activationAtRefusal`); il test del rifiuto (`:459`) nega i due trasporti; il caso nuovo (`:508`) è `'fails explicitly when the secure clipboard refuses after the share tab opened, since the legacy copy has no user activation left'`, con la premessa asserita (`[false]`), un ripiego refuso dal browser vero, lo stato `error`, la scheda chiusa e gli appunti veri intatti (sentinella).
  > - **Il rosso, visto da I contro l'helper di base**: copia di riserva della cura (`shasum` `9b8b1e1d…`), `git show HEAD:frontend/src/lib/utils/clipboard.ts`, poi `front-utility support-copy-and-go "clipboard write is denied" "legacy copy"`: `4 failed` (2 test × 2 progetti), dove previsto. Il test del rifiuto cade a `:486`, il caso nuovo a `:536`, entrambi con Received `[]`: nessun ripiego. La premessa (`:534`, `[false]`) e la scrittura sicura (`:535`) passano: il caso nuovo non cade sulla premessa (`/tmp/libreFolio_i_ui_c4_b_red_base2.log`).
  > - **Il verde**: cura ripristinata e verificata con `shasum -c`; `front-utility support-copy-and-go` `16 passed (1.8m)` (`/tmp/libreFolio_i_ui_c4_b_green_full.log`). Le corse di `test-author` sulla variante immediata: tre filtrate `2 passed` ciascuna, una intera `16 passed (1.9m)` (`/tmp/libreFolio_i_ui_c4_ta_b_imm{1,2,3}.log`, `…_imm_full.log`); la premessa ha tenuto in tutte e 8.
  > - **Il runner** (`_frontend_utility.py`, di I dall'avviso, §0): il gate entra in `core-unit` subito dopo `htmlSink.gate.test.ts`; la descrizione di `core-unit` nomina il gate; la docstring e la descrizione di `support-copy-and-go` nominano il limite noto. La chiamata `add_test` di `support-copy-and-go` supera i 300 caratteri: ha la forma di `black`, su più righe, come le voci vicine. I quattro blocchi cambiati (`:110`, `:398`, `:584`, `:622-629`, numeri della worktree) stanno lontani dal blocco `connection-security` (`:461-470`, `:659-667`) che il merge di M allunga. `ruff check` e `black --check` puliti; `dev.py test front-utility --help` carica il registro.
  > - **L'intestazione del gate**: «To be registered … until then `vitest run` reaches it by path» diventa «Registered in `front_utility_unit` (…, action `core-unit`)», come negli altri due gate. È una riga di commento, non logica di test.
  > - `front-utility core-unit`: `122 files, 3777 passed` (`/tmp/libreFolio_i_ui_c4_core_unit.log`); le voci della lista sono 122, quindi il gate c'è. `prettier --check` pulito su gate, spec e helper.
  > - `messages/C4.txt`: l'ultima voce dice il limite noto e il gate registrato in `core-unit`.
  >
  > **⚠️ Fuori pista**:
  > - **Il timer è diventato un rifiuto immediato**, una deviazione dalla lettera del coordinatore. La variante col timer della pagina (`setTimeout`, clic con `force`, attesa dal lato Node) ha passato tre corse filtrate, ma nella corsa intera è caduta una volta su 8, sul progetto mobile e col carico alto: `1 failed, 15 passed`, premessa Received `[true]` (`/tmp/libreFolio_i_ui_c4_ta_b_full.log`). La pagina aveva di nuovo l'attivazione, la copia legacy è passata e la modale è andata avanti. La causa non è nota; il sospetto è una valutazione di Playwright, che porta `userGesture: true`, arrivata prima del timer. `test-author` è passato al punto 6 del mandato: lo stub rifiuta subito, con `Promise.reject`. Il rifiuto, il ripiego e l'errore girano nel checkpoint dei microtask del task del clic, dopo `window.open`, dove nessun comando CDP si può inserire; quindi la variante è deterministica per costruzione. La sostanza di (b) resta: nessun gesto, il vero `execCommand` risponde `false`, lo stato d'errore è asserito. E prova di più: neanche il rifiuto più precoce possibile riesce a ripiegare. Il commento sopra il test (`:499-507`) racconta il tentativo col timer. Va detto al coordinatore nel checkpoint.
  > - **Infrastruttura**: il primo rosso contro la base è caduto prima della raccolta. Il backend condiviso non ha risposto entro 300 s (carico 61–73 su 10 core, con la corsa completa con coverage sulla 6176), e non ha scritto niente nel log della corsia, il cui ultimo record era lo spegnimento pulito delle 20:08. DB non toccato, 6157 libera dopo. Rilanciato da solo, come da istruzione del coordinatore, è partito al primo colpo (`/tmp/libreFolio_i_ui_c4_b_red_base.log`, poi `…_base2.log`).
  > - **Il perimetro del runner**: `_frontend_utility.py` è passato a I a metà passo (§0). Il gate, che il piano voleva registrare «solo dopo l'avviso», entra quindi in C4 e non in un commit a parte.
- [x] **5. C5, V-19** (aggiunto e chiuso il 2026-10-12, §1.5): le due soglie, i selettori, l'istantanea.
  > **Note implementazione**:
  > - **Il rosso contro la base**, sull'albero senza cura (soglie 950 e 850): `front-utility toolbar-width-sweep "es: 1700"` dà `2 failed, 3 passed (1.6m)` (`/tmp/libreFolio_i_ui_c5_red_pre.log`). Cadono le due pagine previste, dashboard e dettaglio dell'asset.
  > - **La cura**: `denseRow: 990` (`dashboard/+page.svelte:829`, sotto `oneRow` 1000) e `denseRow: 890` (`assets/[id]/+page.svelte:2773`). Nient'altro nei due file.
  > - **Il bisogno e il margine**, dalle righe del log (`red_pre.log:53-60,89-95`):
  >   - dashboard: 968 px (vw 1300→barra 962, +6; 1290→952, +16; 1020→954, +14);
  >   - asset: 868,8 px (1200→862, +6,8; 1190→852, +16,8; 930→864, +4,8; 920→854, +14,8);
  >   - il bisogno non dipende dalla vw, perché le soglie confrontano la larghezza della barra;
  >   - alle soglie nuove il margine è di 22 px sulla dashboard e di 21,2 px sull'asset. Una barra sotto soglia scende al livello inferiore e guadagna spazio, quindi lì non c'è un rischio nuovo.
  > - **La calibrazione chiesta dal coordinatore**, per il CP2 di T (M-18), che cambia la larghezza di `DateRangePicker`:
  >   - lo sweep di T su CP2 coincide al pixel col mio su una base senza CP2, quindi CP2 non sposta il bisogno: i rossi di T sono il V-19 preesistente, che C5 cura;
  >   - V vedeva le vw 1320/1310 e 1220/1210/940: è la stessa barra con la gutter misurata a 15 px. La mia prima riproduzione dice «gutter 15» (`/tmp/libreFolio_i_v19_sweep_es_red.log:49,84`), il rosso contro la base «gutter 0» (`red_pre.log:48,84`). A parità di vw la barra è più stretta di 15 px, il bisogno è lo stesso;
  >   - con 990 e 890 i margini restano 22 e 21,2 px in tutti e tre i casi. A vw 1020 la barra della dashboard (954 px) è sotto soglia, nel livello inferiore, verde;
  >   - la risposta al coordinatore: nessun ritocco; chi integra per secondo rilancia lo sweep sulla revisione combinata.
  > - **I selettori**, uno alla volta sulla 6157 (`/tmp/libreFolio_i_ui_c5_{sweep_full,aiexport_panel,broker_filter_label,dashboard,asset_detail,asset_detail_cal1}.log`):
  >   - `front-utility toolbar-width-sweep`: `15 passed (4.2m)`;
  >   - `front-ai-export panel`: `6 passed (19.6s)`;
  >   - `front-portfolio broker-filter-label`: `2 passed (19.1s)`;
  >   - `front-portfolio dashboard`: `27 passed (2.2m)`;
  >   - `front-asset asset-detail`: `1 failed, 31 passed (2.5m)`, poi il test caduto, rilanciato da solo: `1 passed (2.0m)` (sotto).
  > - Il frontend servito contiene `denseRow: 990` e `890`, verificato nel bundle prima delle corse.
  > - L'istantanea è `stage_C5`, il messaggio `messages/C5.txt`.
  >
  > **⚠️ Fuori pista**:
  > - **Il rosso di `asset-detail` è un'assunzione del test, non C5.**
  >   - Il test è `'calendar-return primary mode queries exact windows and restores price controls'` (`asset-detail.spec.ts:486`). Cade su un conteggio a `:5435`: Expected 51, Received 50. Rilanciato da solo, passa.
  >   - Il triage (skill `test-triage`) esclude la forma, perché il contatore è locale alla rotta della pagina. Il test aspetta la condizione sbagliata.
  >   - Il meccanismo, in Playwright 1.61 (`node_modules/playwright-core/lib/coreBundle.js`):
  >     - il server emette l'evento `request` prima di avviare la `route` (`:22399-22401`);
  >     - il client in-process consegna ogni messaggio in un suo `setImmediate` (`:62310`);
  >     - `calendarRequestCount` cresce nell'handler di `page.route` (spec `:1934-1951`), mentre l'asserzione è sincrona, subito dopo `waitForCalendarRequestForRange` (`page.waitForRequest`, `:1491-1492`);
  >     - il conto torna solo se la richiesta parte mentre il test è ancora fermo nel `click()`. Col carico arriva dopo, e il contatore si legge prima che l'handler giri.
  >   - La scansione dello spec (`/tmp/libreFolio_i_ui_race_scan.log`) conta 42 asserzioni di conteggio dopo un'attesa di richiesta, nel solo `asset-detail.spec.ts`.
  >   - C5 non c'entra: lo spec non è nel lotto e le soglie non toccano il calendario.
  > - **La decisione del coordinatore** (12/10): «(a), ma come lotto 49 separato, subito dopo il checkpoint del lotto 48».
  >   - La cura, via `test-author`: gli helper `waitFor…Request…` risolvono solo dopo che l'handler ha contato la richiesta, con un registro locale; i 42 siti restano invariati.
  >   - Le prove sulla 6157, compreso un rilancio sotto carico della spec intera.
  >   - Una scansione in sola lettura delle altre spec con lo stesso schema, cioè un contatore incrementato da `page.route` e asserito subito dopo `waitForRequest`, con file:riga e proprietario. Quelle non mie non si correggono: decide il coordinatore.
  >   - Quindi nessuna voce di backlog.
  > - **Il timeout d'infrastruttura del passo 4, la causa più probabile**: l'avvio del server condiviso ricostruisce prima un frontend non aggiornato (`scripts/test_runner/_server.py:43-48`, `STARTUP_TIMEOUT` 300 s). Con la cura appena scritta il frontend era vecchio, e la ricostruzione, col carico a 61–73, può aver superato i 300 s prima che il backend partisse. Questo spiega anche il log della corsia vuoto.
  > - **La mia risposta sul CP2 va corretta in un punto**: avevo attribuito i 15 px fra V e T a un cambio della cornice. Sono invece la gutter misurata al caricamento, come sopra. La conclusione non cambia.
- [x] **6. Il journal** (2026-10-12): questo piano, con H3 e H2 citate come C-56 e C-57; le voci nuove del lotto nella sezione I (il padding del trigger di AiExportMenu, §1.5).
  > **Note implementazione**:
  > - **Il piano**: H3 e H2 sono citate come C-56 e C-57 (§0, §1.1); il passo 5 riporta il reperto di `asset-detail` e la decisione sul lotto 49.
  > - **La sezione I del backlog**, in fondo, ha una voce sola, **48-1**: il padding del trigger di AiExportMenu, coi numeri corretti del passo 5. La corsa di `asset-detail` non entra nel backlog, perché è il lotto 49.
  > - **C-56 e C-57 non sono nella base.** Le ha scritte il coordinatore in `bf831ef10`, che è nel target ma non in `55304116f`; la sezione C della worktree non le ha ancora, e non la tocco. Fra la base e il target (`b1c8f22df`) il backlog cambia alle righe 43, 51, 82, 99, 301, 418, 434-435, 593 e 614 della base, nessuna dentro la sezione I (101-187): non mi aspetto conflitti.
- [x] **7. Statici e checkpoint** (2026-10-12).
  > **Note implementazione**:
  > - `dev.py front check`: `svelte-check found 0 errors and 0 warnings` (`/tmp/libreFolio_i_ui_front_check.log`).
  > - `prettier --check` sui 29 file del frontend toccati, cataloghi compresi: «All matched files use Prettier code style!» (`/tmp/libreFolio_i_ui_prettier_final.log`).
  > - `git diff --check` pulito; nessuno spazio in coda nei 3 file nuovi.
  > - `ruff check` e `black --check` sui due file del runner: `_frontend_utility.py` pulito. `_frontend_broker.py` ha 5 errori ruff (E701 a `:44-45`, `:52-53`; PLC0415 a `:96`) e black lo riformatterebbe, ma la base ha gli stessi 5 errori e lo stesso riformato, e le righe di C1 non sono nei pezzi di black. È debito preesistente, fuori dal lotto.
  > - La privacy: 2.305 righe aggiunte, nessun percorso di casa, email, IBAN, segreto, token o IP privato.
  > - Le istantanee `stage_C1`…`stage_C6` e i messaggi `C1`…`C6` sono nel bundle della sessione; il manifest va al coordinatore col checkpoint. Porta 6157 libera.
