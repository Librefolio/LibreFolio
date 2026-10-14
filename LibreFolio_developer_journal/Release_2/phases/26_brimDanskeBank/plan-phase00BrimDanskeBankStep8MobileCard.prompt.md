# Piano — fase 00, Danske Bank, passo 8: la card del set su mobile (intestazione e timeline)

> **Stato**: ✅ chiuso e integrato nel treno 14 (merge `975950379`): `038109e91`, `f2f94c295` (verifica del 2026-10-09 su `3cceb4f90`).
> - Al checkpoint: ✅ pronta per il checkpoint (2026-10-08, §8.3). Via del coordinatore, con la decisione del developer (§0).
>
> - Viene da: [plan-phase00BrimDanskeBankStep7ButtonAndR6.prompt.md](plan-phase00BrimDanskeBankStep7ButtonAndR6.prompt.md), l'ultimo passo che ha toccato la card; la card nasce in [plan-phase00BrimDanskeBankStep4Implementation.prompt.md](plan-phase00BrimDanskeBankStep4Implementation.prompt.md).
> - Workstream L, issue #26. Base `ffa72cc2b` (`dev_release2` dopo il treno 12, col lotto 34 integrato).

## 0. Decisioni

- **Developer** (testuale, portato dal coordinatore il 2026-10-08): «L sistema la card su mobile». L'ha trovato M scattando la gallery del G3 (la prova è nel worktree di M e non la leggo: la riproduco nella mia corsia).
- **Coordinatore**:
  - i due difetti di `ReportSetCard.svelte` su mobile:
    1. l'intestazione: il toggle (chevron e «Set uploaded on …», `flex-1 min-w-0`) viene schiacciato a larghezza zero da checkbox, «Read as» e chip di stato; con «A file is missing» la card non si apre col tocco;
    2. la timeline: le date di inizio e fine si sovrappongono;
  - l'Esc su «Read as» lo fa K, perché è `SimpleSelect`;
  - prima i rossi, col test-author, anche sul progetto mobile di Playwright. Corsia 6156/6166;
  - **coordinamento con K**: K aggiunge `ReportSetCard.escape.test.ts`, che monta la card vera dentro `ModalBase`. I `data-testid` esistenti della card **non cambiano**, in particolare quelli di «Read as» e della sua lista; se ne possono aggiungere di nuovi; il layout cambia come serve.

## 1. Stato verificato (2026-10-08, sul codice a `ffa72cc2b`)

- **Il progetto mobile** di Playwright è un iPhone 14 Pro Max (430 px, `isMobile`, `hasTouch`) su Chromium (`playwright.config.ts:130-140`).
- **L'intestazione** (`ReportSetCard.svelte:323-357`) è una riga sola, `flex items-center gap-2`, senza a capo:
  - la checkbox (16 px);
  - il toggle `report-set-toggle`, `flex min-w-0 flex-1`, l'unico elemento che si restringe;
  - «Read as»: un gruppo `shrink-0` con l'etichetta (`hidden sm:inline`) e la `SimpleSelect` `max-w-52` (fino a 208 px);
  - la chip «Analysed», se c'è, e la chip di stato, tutte e due `shrink-0`.

  Su una card larga poco più di 350 px, gli elementi rigidi superano la riga: il toggle va a 0 px e il resto esce dalla card. Un tocco sul titolo trova la select o la chip.
- **La timeline** (`:467-520`) è una griglia `grid-cols-[fit-content(40%)_minmax(0,1fr)_max-content]`: etichetta, binario delle barre, e il periodo della riga (`rowSpan`, «gg/mm/aaaa → gg/mm/aaaa» a 10 px, ~125 px, `max-content`).
  - Le date dell'asse stanno in `col-start-2`, in un `flex justify-between` senza spazio fra loro.
  - Su mobile la colonna centrale resta di ~80 px: le due date (~2 × 55 px) non ci stanno, escono, e si toccano.
  - Il periodo della riga sta già anche nell'infobox di ogni barra (`barInfo`), e l'asse dà l'inizio e la fine.
- **I test**:
  - `ReportSetCard.test.ts` usa solo `data-testid`, mai il testo dell'asse o dei periodi; jsdom non ha layout.
  - `tx-import-report-set.spec.ts` gira solo su `desktop` (runner: `_run_playwright(..., project="desktop")` di default). H-E7 misura già le etichette della timeline (`scrollWidth ≤ clientWidth`) e salta tutto ciò che non è desktop.
  - Le esecuzioni consolidate (`_inventory.collect_launches`) raggruppano le spec per progetto e **ignorano** il `--grep`: una seconda voce del runner «solo mobile», filtrata per nome sulla stessa spec, farebbe girare l'intera spec su mobile.

## 2. Il contratto

**Su mobile** (progetto `mobile`):
- **Intestazione**:
  - il toggle ha una larghezza vera (almeno metà della card);
  - checkbox, toggle, «Read as» e chip di stato stanno dentro la card e non si sovrappongono;
  - un tocco sul toggle apre la card, anche con «A file is missing».
- **Timeline**:
  - le date dell'asse sono tutte e due visibili, dentro la timeline, e non si sovrappongono;
  - il binario delle barre ha almeno metà della larghezza della timeline;
  - niente esce dalla timeline.

**Su desktop non cambia niente**: l'intestazione resta una riga sola, nello stesso ordine; la timeline tiene le tre colonne, col periodo accanto a ogni riga (H-E7 resta com'è).

**La cura proposta** (solo classi Tailwind e nuovi `data-testid`; nessun testid esistente cambia):
- **Intestazione**: `flex-wrap`.
  - Sotto `sm`, il toggle prende tutta la prima riga accanto alla checkbox: una `flex-basis` piena, che su `sm:` torna a 0, cioè all'attuale `flex-1`.
  - «Read as» e le chip vanno a capo nella seconda riga, allineate a destra (`ml-auto`).
  - Su desktop gli elementi stanno su una riga, come oggi.
- **Timeline**: sotto `sm`, due colonne (etichetta e binario).
  - Il periodo della riga e il segnaposto dell'asse nella terza colonna sono `hidden sm:block`; la legenda è `col-span-1 sm:col-span-2`.
  - Le date dell'asse hanno uno spazio fra loro e possono andare a capo (`flex-wrap gap-x-2`, la fine `ml-auto`): non si sovrappongono a nessuna larghezza.
  - Le etichette restano elementi della griglia, così la misura di H-E7 conserva il suo senso.
- **Testid nuovi**:
  - `report-set-status`, la chip di stato;
  - `report-set-timeline-start` e `report-set-timeline-end`, le date dell'asse;
  - `report-set-timeline-track` (`data-role`), il binario di ogni riga;
  - `report-set-timeline-span` (`data-role`), il periodo di ogni riga.

  Li aggiungo **prima** dei rossi, senza toccare il layout, così i rossi falliscono sulle asserzioni e non sui selettori.

## 3. I test, rossi prima (test-author)

In `tx-import-report-set.spec.ts`, dentro il describe che c'è già (helper e pulizie in comune):
- **Un test, un progetto**: un test col tag `@mobile` gira solo su `mobile`, ogni altro solo su `desktop`. La regola è nel `beforeEach`, prima del login e dopo l'azzeramento di `ownedBrokerId`, perché l'`afterEach` non cancelli il broker di un test precedente.
- **M1** (`@mobile`), l'intestazione, su un set incompleto: la custodia sola, quindi «A file is missing». Il contratto di §2.
- **M2** (`@mobile`), la timeline, su un set completo con la storia di LibreFolio (tre righe, come H-E7). Il contratto di §2.
- **D1** (desktop), la guardia:
  - l'intestazione è una riga: centri verticali allineati, ordine checkbox < toggle < «Read as» < chip;
  - la timeline mostra il periodo di ogni riga (`report-set-timeline-span`) accanto al suo binario.

  È verde oggi e deve restarlo.

**Runner** (la voce è mia): `tx-import-report-set` passa a `project=""`, cioè desktop e mobile. Su mobile ogni test senza tag salta; nelle esecuzioni consolidate la spec va nel gruppo «desktop + mobile». Aggiorno la descrizione della voce.

## 4. Superfici

| File | Cosa |
|---|---|
| `frontend/src/lib/components/transactions/import/ReportSetCard.svelte` | i testid nuovi, poi la cura (§2) |
| `frontend/e2e/transactions/tx-import-report-set.spec.ts` | la regola dei progetti, M1, M2, D1 (test-author) |
| `scripts/test_runner/_frontend_transaction.py` | la mia voce: `project=""`, la descrizione |
| questo piano, e il rimando in avanti in Step7 | — |

Niente i18n, niente API, niente doc utente: la pagina del wizard non descrive il layout. La gallery del G3 la riscatta M.

## 5. Rischi

1. **Il tempo del runner**: la spec viene raccolta anche su mobile. I test senza tag saltano prima del login, quindi costano poco; M1 e M2 costano due upload ciascuno.
2. **La `SimpleSelect` dentro una riga che va a capo**: la lista è `fixed`, calcolata dal rettangolo del bottone, quindi la posizione segue il bottone. K cura l'Esc e i testid restano.
3. **Testi più lunghi** in IT/FR/ES (le chip, i nomi dei ruoli): la seconda riga può andare a capo ancora, e va bene. Le etichette della timeline restano al massimo al 40%.

## 6. Gate e definizione di fatto

- `front build --debug`, poi, uno alla volta sulla 6156:
  - `tx-import-report-set` (desktop + mobile), compresi M1, M2, D1 e H-E7;
  - `tx-import-report-set-guide`, `tx-import-file-selection`, `tx-bulk-import-handoff`.
- `front check`; `component-unit` (con `ReportSetCard.test.ts`); `core-unit` se tocca le utility; `check-orphans`; prettier sui file cambiati; `git diff --check`; porte libere.
- Fatto quando:
  - M1 e M2 sono rossi prima e verdi dopo, D1 e H-E7 verdi prima e dopo;
  - nessun testid esistente è cambiato;
  - c'è la riga di CHANGELOG proposta.

## 7. CHANGELOG

Lo scrive il coordinatore. Al checkpoint propongo una riga 🐛 per la voce Danske, confermata sul codice.

## 8. Avanzamento

### 8.0 ✅ L'analisi (2026-10-08)

> **Note implementazione**: baseline `ffa72cc2b` verificata, pulita, porte libere. Letti la card, i suoi test, la spec E2E, la configurazione di Playwright e il modo in cui il runner sceglie i progetti, comprese le esecuzioni consolidate. Il contratto, la cura e i test sono in §2–§3.
>
> **⚠️ Fuori pista — dove mettere i test mobile**:
> - Una voce del runner «solo mobile» filtrata per `--grep` non va bene, perché il consolidato ignora il filtro e farebbe girare tutta la spec su mobile.
> - Una spec nuova non va bene nemmeno: gli helper sono locali al describe.
> - Quindi: la stessa spec, un test un progetto, la voce su tutti e due i progetti.

### 8.1 ✅ I testid, il runner, i rossi (2026-10-08)

> **Note implementazione**:
> - **Testid nuovi** nella card, senza cambiare il layout: `report-set-status`, `report-set-timeline-start` e `-end`, `report-set-timeline-track` e `-span` (con `data-role`). Nessun testid esistente cambia.
> - **Runner**: `tx-import-report-set` passa a `project=""`; descrizione e docstring aggiornate.
> - **I rossi** (test-author, solo `tx-import-report-set.spec.ts`, +375/−1):
>   - il `beforeEach` dà un progetto a ogni test: col tag `@mobile` solo mobile, senza tag solo desktop. Prima azzera `ownedBrokerId`, poi salta, poi fa il login;
>   - **M1** (`@mobile`): lo scenario di R3, la card chiusa con un click spedito. Tre misure (toggle ≥ 50% della card; le quattro parti dentro la card; nessuna sovrapposizione), poi `tap()` sul toggle;
>   - **M2** (`@mobile`): lo scenario di H-E7, cioè tre binari. Le date dell'asse visibili e dentro la timeline, staccate (≥ 4 px sulla stessa riga, o la fine a capo); ogni binario ≥ 50%; `scrollWidth ≤ clientWidth + 1`. M2 non guarda i periodi delle righe;
>   - **D1** (desktop, la guardia): l'intestazione su una riga e in ordine; il periodo di ogni riga visibile a destra del suo binario.
>   - Selezione: `-g "step 8"`.
> - `front build --debug` (stub compresi), poi `tx-import-report-set "step 8"` sulla 6156, desktop e mobile. Log: `files/next-batch/step8-red.log`.
>   - **M1 rosso**: «the toggle is 0.0 px wide: 0.0% of the card's 340.0 px».
>   - **M2 rosso**: «the axis dates share a line 0.0 px apart, under 4 px», con l'inizio a x 192.4–250.0 e la fine a x 250.0–307.7.
>   - **D1 verde**. 3 saltati: M1 e M2 su desktop, D1 su mobile.
>
> **⚠️ Fuori pista — la regola dell'asse**. Nella prima versione di M2 contava solo la sovrapposizione delle aree. Ma le date che si toccano non condividono area, e il difetto visto («01/07/201907/03/2020») sono proprio le date attaccate. La regola è diventata «staccate di almeno 4 px, o a capo».
>
> **⚠️ Fuori pista — l'intestazione della spec della guida**. `tx-import-report-set-guide.spec.ts:10` diceva che `tx-import-report-set` gira solo su desktop. Con la mia voce del runner non è più vero: frase corretta dal test-author, nient'altro.

### 8.2 ✅ La cura (2026-10-08)

> **Note implementazione** (`ReportSetCard.svelte`; solo classi, e un commento per blocco):
> - **Intestazione**:
>   - il contenitore diventa `flex flex-wrap … gap-x-2 gap-y-1.5`, e la checkbox `shrink-0`;
>   - il toggle passa da `flex-1` a `grow basis-[calc(100%_-_2rem)] sm:basis-0`. Su mobile riempie la prima riga accanto alla checkbox (16 px + 8 px di gap, con 8 px di margine contro gli arrotondamenti); da `sm` in su è `flex: 1 1 0`, come prima;
>   - il gruppo «Read as» prende `ml-auto`: su mobile la seconda riga sta a destra; su desktop non conta, perché lo spazio libero lo prende il toggle.
> - **Timeline**:
>   - la griglia ha due colonne sotto `sm` e tre da `sm` in su;
>   - il segnaposto dell'asse e i periodi delle righe (`report-set-timeline-span`) sono `hidden sm:block`;
>   - la legenda è `col-start-2 sm:col-span-2`: con `col-span-2` su due colonne avrebbe creato una colonna implicita;
>   - l'asse è `flex-wrap … gap-x-2`, con la fine `ml-auto`: le date restano staccate a qualunque larghezza, e se vanno a capo la fine resta a destra;
>   - le etichette restano elementi della griglia, così la misura di H-E7 conserva il suo senso.
> - Prettier pulito su card e spec. `front build --debug` verde.
> - `tx-import-report-set "step 8"` sulla 6156: **3 passed** (M1 e M2 su mobile, D1 su desktop), 3 saltati. Log: `files/next-batch/step8-green.log`.
>
> **⚠️ Fuori pista — la verifica visiva**. Playwright salva lo screenshot solo quando un test fallisce (`playwright.config.ts:114`), e la configurazione non si tocca. La forma la provano le misure di M1, M2 e D1; l'occhio la avrà la gallery del G3, che rifà M.

### 8.3 ✅ I gate (2026-10-08)

> | Gate (corsia 6156, un comando alla volta; log `files/next-batch/`) | Esito |
> |---|---|
> | `front check` | 0 errori, 0 avvisi |
> | `front-utility component-unit` (con `ReportSetCard.test.ts`) | 2846/2846, exit 0 |
> | `tx-import-report-set`, intera, desktop e mobile | **31 passed, 31 skipped**: ognuno dei 31 test gira su un progetto solo. Desktop: 29, compresi H-E7 e D1. Mobile: M1 e M2 |
> | `tx-import-report-set-guide` / `tx-import-file-selection` / `tx-bulk-import-handoff` | 2 / 2 / 2 |
> | `check-orphans` | pulito |
> | prettier (card, le due spec), `git diff --check` | puliti |
> | porte 6156 e 6166 | libere |
>
> **⚠️ Fuori pista — ruff e black sul runner**. `_frontend_transaction.py` ha 4 PLC0415 e black lo riformatterebbe. Ma è identico sul file a `HEAD`: è preesistente, non è mio, e non lo tocco.
>
> **Voce CHANGELOG proposta** (🐛, voce Danske): «On a phone, a report set's card keeps its title tappable — «Read as» and the status move to a second row — and its timeline no longer runs the start and end dates together.»

### 8.4 ✅ Integrato (2026-10-08)

> **Note implementazione**:
> - I commit: `038109e91` fix(import): set card header, timeline on phones; `f2f94c295` docs(journal): plan 26 step 8, mobile set card. Tutti e due sopra `ffa72cc2b`.
> - Merge `975950379` nel treno 14; `dev_release2` = `9eb01c756`.
> - Il coordinatore ha rifatto i controlli sulla revisione unita: component 2850, compreso l'Esc di K sulla card; `tx-import-report-set` 31 passati e 31 saltati; guida 2; selezione file 2.
> - CHANGELOG: nessuna riga, perché i report set sono nuovi nella 1.2.0.
> - Segue: [plan-phase00BrimDanskeBankStep9StaleFrontend.prompt.md](plan-phase00BrimDanskeBankStep9StaleFrontend.prompt.md).
