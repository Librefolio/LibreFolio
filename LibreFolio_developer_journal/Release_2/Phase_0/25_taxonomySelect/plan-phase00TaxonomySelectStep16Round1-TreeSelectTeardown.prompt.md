# Piano — K / step 16, round 1: TreeSelect annulla il lavoro differito quando viene distrutto

> Difetto trovato durante la validazione del treno (`998ce67d4`), nella `component-unit` dello step 16
> ([`plan-phase00TaxonomySelectStep16AssetDetailUx.prompt.md`](plan-phase00TaxonomySelectStep16AssetDetailUx.prompt.md)).
> È un checkpoint a sé, prima dello step 17.

| | |
|---|---|
| **Baseline** | `a7d0b37ec` (riallineamento del coordinator, 06/10), worktree pulito |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`, preambolo `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` |
| **Autorizzazione** | coordinator, 06/10: «Cura di `TreeSelect` approvata, ma DOPO il riallineamento: […] rosso col test-author in `TreeSelect.test.ts`, la cura in `TreeSelect.svelte` (handle annullati alla distruzione, elemento cercato nel contenitore del dropdown), `component-unit` ripetuta; un checkpoint a sé.» Poi: «riallineati […] K: la cura di `TreeSelect` (rosso, poi cura, poi `component-unit`), checkpoint a sé». |
| **Superfici** | `frontend/src/lib/components/ui/select/TreeSelect.svelte` e `TreeSelect.test.ts`. Nessun altro ramo li tocca. |
| **Fuori perimetro** | Messi dal coordinator nel backlog di fine round: i timer di SearchSelect (`:318` usa il `document` globale) e un controllo «nessun timer vivo a fine file» su tutta la suite. |

## Il difetto (triage con la skill test-triage)

- **Sintomo**: `front-utility component-unit` su `998ce67d4` passa 2276/2276 ma esce con codice 1, per un'eccezione
  non gestita.
  - L'eccezione è «ReferenceError: document is not defined», attribuita a `ChartSignalsSection.test.ts`.
  - È intermittente sotto carico: 0 casi su 5 col file da solo, 0 su 3 con la lista completa.
- **Diagnostica**, fuori dal repo: timer avvolti, stack di creazione, callback pendenti a fine file.
  - L'unico callback pendente che usa il `document` **globale** è di TreeSelect.
  - Catena: `open()` → `setTimeout(0)` → `setActiveIndex` → `scrollActiveEntryIntoView()` → `setTimeout(0)` →
    `document.getElementById(entry.id)` (`TreeSelect.svelte:150`).
- **I cinque `setTimeout` del componente** (`:150`, `:196`, `:319`, `:338`, `:352`) non vengono annullati quando il
  componente è distrutto.
  - Se l'ambiente di test rimuove `document` prima che partano, il callback lancia l'eccezione.
  - Nel browser è innocuo, perché `document` esiste sempre.
  - Lo stesso codice è identico su `dev_release2`, quindi il problema c'è anche lì.
- **Verdetto: difetto** del prodotto, introdotto da K in `4041ffa98` («two-level type select»).

## La cura

- **Handle dei timer** in una struttura normale, non `$state` (lezione dello step 14: un teardown legge `$state` com'era
  prima dell'ultima scrittura).
  - Un solo `defer()` gestisce i cinque differimenti e toglie l'handle quando il callback parte.
- **Teardown di distruzione** `$effect(() => () => …)` che annulla tutti gli handle ancora pendenti, come in
  `Tooltip.svelte`.
- **L'elemento attivo si cerca nel contenitore del dropdown** (il `div` con `id={treeId}`), non nel `document`
  globale.

## Passi

- [x] **R1.1 Rosso**: il test-author scrive in `TreeSelect.test.ts`; lo eseguo con vitest sul solo file. ✅ 2026-10-06.
  - Per ogni percorso che differisce (apertura con clic, apertura con tasto stampabile, digitazione, pulsante di
    cancellazione, frecce), lo smontaggio non lascia timer vivi.
  - Lo scorrimento all'elemento attivo agisce sull'elemento dentro il dropdown, senza ricerche nel `document` globale.
  > **Note implementazione**:
  > - comando: `cd frontend && node_modules/.bin/vitest run src/lib/components/ui/select/TreeSelect.test.ts`;
  > - esito sulla baseline: 28 test, 22 verdi, 6 rossi, nessuna eccezione non gestita;
  > - i 6 rossi sono quelli nuovi, e ognuno fallisce per la ragione attesa:
  >   - cinque righe di `it.each`: timer ancora pendenti dopo lo smontaggio, 1 (2 per il tasto stampabile) invece di 0;
  >     prima un controllo positivo verifica che il percorso abbia lavoro differito;
  >   - un test di scorrimento: la riga attiva viene cercata con `document.getElementById`; le asserzioni precedenti
  >     sono già verdi (riga dentro l'albero indicato da `aria-controls`, `scrollIntoView({block: 'nearest'})` sulla
  >     riga di `aria-activedescendant`).
  > - Il helper `mount()` del file ora restituisce anche `unmount`.
  > - Il test-author ha controllato anche Prettier e svelte-check sul file: 0/0.
  >
  > **⚠️ Fuori pista**: il test-author ha tolto una riga che aveva scritto, «smontare dopo che il passo di apertura è
  > partito».
  > - Quando il focus entra nella casella di ricerca, jsdom accoda un `selectionchange` sullo stesso `setTimeout` finto.
  > - Nessun teardown del componente può annullarlo, quindi la riga sarebbe rimasta rossa anche dopo la cura.
  > - Lo scorrimento resta coperto dalla riga delle frecce e dal test di scorrimento.
  > - Due vincoli emersi per la cura:
  >   - jsdom 30 non ha `CSS.escape`;
  >   - la ricerca non deve passare da nessun `getElementById`, neppure `ownerDocument.getElementById`, che chiama lo
  >     stesso metodo spiato.
- [x] **R1.2 Cura** in `TreeSelect.svelte`. ✅ 2026-10-06.
  > **Note implementazione**:
  > - **`defer(step)`** sostituisce i cinque `setTimeout(…, 0)`: apertura, tasto stampabile, `oninput`, pulsante di
  >   cancellazione, scorrimento.
  >   - Gli handle vivono in un `Set` normale (`pendingSteps`), e ogni callback toglie il proprio handle quando parte.
  >   - Il teardown di distruzione `$effect(() => () => …)` annulla quelli ancora pendenti.
  > - **La riga attiva** si trova con `entryElement(id)`, che cerca dentro `dropdownRef` (nuovo `bind:this` sul `div`
  >   con `id={treeId}`).
  >   - Confronta `element.id` su `querySelectorAll('[id]')`: niente `getElementById`, niente `CSS.escape`.
  > - Restano sul `document` globale solo i listener di `mousedown`, aggiunti e tolti dal loro effetto.
  > - Verifica: `node_modules/.bin/vitest run` su `TreeSelect.test.ts`, `SignalTreeSelect.test.ts`,
  >   `AssetTypeSelect.test.ts` e `ChartSignalsSection.test.ts`.
  >   - Esito: 4 file e 79 test verdi, exit 0, nessuna eccezione non gestita.
  >   - Prettier `--check` pulito sui due file.
- [x] **R1.3 Verifica** ✅ 2026-10-06, sulla corsia 6155, un comando per volta:
  - vitest sul file;
  - `front check`;
  - `component-unit` ripetuta;
  - la suite dei select e i test dei segnali, che passano da `SignalTreeSelect`.
  > **Note implementazione**:
  > - `front check`: svelte-check 0 errori e 0 avvisi (`/tmp/libreFolio_k_r1_front_check.log`).
  > - `front-utility component-unit`, ripetuta tre volte di seguito con carico 18–20: ogni corsa esce con 0, 2290/2290,
  >   e nessuna riga «Unhandled» o «document is not defined» (`/tmp/libreFolio_k_r1_component_unit_{1,2,3}.log`).
  > - `front build --debug`: build completa, svelte-check 0/0.
  > - E2E che guidano TreeSelect in Chromium:
  >   - `front-asset asset-modal`: 17/17 (il selettore del tipo, `asset-type-tree`);
  >   - `front-asset asset-detail`: 29/29 (il selettore dei segnali);
  >   - `front-utility select`: 17/17.
  > - Porte 6155 e 6165 libere al termine.
- [x] **R1.4 Handoff**: CHECKPOINT READY, FROZEN. ✅ 2026-10-06.
  > **Note implementazione**:
  > - Due commit proposti, con i messaggi in `/tmp/libreFolio_commits/` e il manifesto dei blob in
  >   `k-16r1-manifest.txt`:
  >   - `k-42-treeselect-teardown` per il codice e il test;
  >   - `k-43-journal-16r1` per il journal.
  > - Nessuna voce di CHANGELOG: nel browser il difetto non si vede (`document` esiste sempre). Il beneficio è l'exit
  >   code stabile della suite.

## Definizione di fatto

1. I test nuovi sono rossi sulla baseline e verdi dopo la cura; il resto del file resta verde.
2. `component-unit` ripetuta esce con codice 0 a ogni corsa, senza eccezioni non gestite attribuite a TreeSelect.
3. `front check` resta a 0/0.
4. Porte libere, nessun venv del worktree, nel worktree solo i file previsti.

## Seguito

- Lo step 17 riguarda le note del developer dai dispositivi:
  [`plan-phase00TaxonomySelectStep17DeviceNotes.prompt.md`](plan-phase00TaxonomySelectStep17DeviceNotes.prompt.md).
