# Piano — K / step 20: l'Esc di SimpleSelect

> Lotto approvato dal developer (testuale, via coordinator, 08/10 12:13): «K estende l'Esc a SimpleSelect».
> Viene dallo step 18 (Esc in ContextMenu e SearchSelect) e dallo step 19 (Esc del trigger di SearchSelect).
> Precedente: [`plan-phase00TaxonomySelectStep19AppStartAuth.prompt.md`](plan-phase00TaxonomySelectStep19AppStartAuth.prompt.md).

| | |
|---|---|
| **Baseline** | `ffa72cc2b` = `dev_release2` (treno 12: lo step 19 di K, `93fd33702` `53a6b2213` `f6f2355cc` `04cd0dfdf`, merge `d4ca2b101`) |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`, preambolo `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc`; sonde sulla 6165 |
| **Coordinator** | «prima i rossi col test-author, dentro la modale e nel wizard dell'import, poi la cura» (08/10, 12:18) |

## Il difetto (trovato da M in `ReportSetCard`)

- `ui/select/SimpleSelect.svelte`:
  - `handleKeydown` sta sul trigger (`:297`), e il focus resta lì: è un combobox con `aria-activedescendant`;
  - con la lista aperta, l'Escape fa `preventDefault()` e `closeDropdown()` (`:267-269`), **senza
    `stopPropagation()`**;
  - con la lista chiusa, l'Escape non viene gestito (`:235-241`) e risale, che è giusto.
- Il wizard d'importazione è `ModalBase` con `onRequestClose={handleClose}` (`ImportWizardModal.svelte:4240`).
  `handleClose` apre la conferma di scarto (`:5431`). Un Esc sulla lista «Read as» di `ReportSetCard` (`:337`) chiude
  la lista e chiede di scartare l'import.
- È lo stesso schema dei due componenti dello step 18. La cura è la stessa: `stopPropagation()` sull'Esc consumato, a
  lista aperta.

## Effetto sui 18 consumatori (letti in sola lettura)

- **Dentro una modale** (`EventCreateMiniModal`, `DataTable` e le sue modali, `SchedulerLogModal`, il wizard con
  `ReportSetCard`): il primo Esc chiude la lista, il secondo la modale.
- **`ui/date/CompactDurationBadge.svelte`**: l'editor in linea si chiude su Escape (`:97-98`) e contiene una
  `SimpleSelect` per l'unità (`:112`).
  - Oggi un Esc a lista aperta chiude lista ed editor insieme.
  - Dopo la cura: il primo chiude la lista, il secondo l'editor. È la stessa regola «un Esc, uno strato», e la
    considero voluta.
- **`AiExportOptionsPanel`** (dentro `AiExportMenu`): il menu ascolta Escape su `document` **in cattura**, che passa
  prima del trigger. Il pannello si chiude comunque, come oggi. Il caso è fuori perimetro (non è una modale), già
  riferito allo step 18.
- **Gli altri** (risk, chart, pac-allocator, impostazioni, asset): non sono dentro un livello che chiuda su Escape.
  Nessun cambiamento visibile.

## Conflitti

- `SimpleSelect.svelte`, `ReportSetCard.svelte`/`.test.ts`, l'harness e `ModalBase.escapeLayers.test.ts`: nessun ramo
  locale li tocca dalla merge-base (verificato il 08/10, 12:20).

## Test (rossi prima, test-author)

1. **«Dentro la modale»**: `ModalBase.escapeLayers.test.ts`, con l'harness `ModalEscapeLayersHarness.svelte` più una
   `SimpleSelect`:
   - aperta col clic sul trigger, focus sul trigger → Escape → la lista si chiude e la modale resta; l'Escape dopo
     chiude la modale;
   - controllo: chiusa → Escape → la modale si chiude.
2. **«Nel wizard»**: la `ReportSetCard` vera dentro una `ModalBase` con `onRequestClose` spiato, cioè la struttura del
   wizard.
   - Escape sulla lista «Read as» aperta → `onRequestClose` NON chiamato (è la conferma di scarto) e la lista chiusa.
   - File nuovo di K: `transactions/import/ReportSetCard.escape.test.ts`, più l'harness. **Non** `ReportSetCard.test.ts`
     e **non** gli E2E dell'import, perché sono file di L e gli helper dei report set sono locali al suo spec.
   - Alternativa, se il coordinator vuole un E2E vero nel wizard: serve un accordo con L sugli helper.
3. Registrazioni in `component-unit` (file condiviso, solo aggiunte).

## Passi

- [x] 20.1 Base `ffa72cc2b`, pulita; i 4 commit dello step 19 sono in HEAD; il piano è nel repo. ✅ 2026-10-08.
  > I 4 cataloghi i18n differiscono dal manifesto 19 solo alla punta, per le modifiche del treno successive. Al commit
  > `93fd33702` i blob coincidono, e alla punta la chiave `auth.serverUnreachable` c'è.
- [x] 20.2 Rosso (test-author): i due test sopra. ✅ 2026-10-08.
  > **Note implementazione**:
  > - **Decisione del coordinator** (08/10 12:2x, testuale): «Va bene così: il test di componente
  >   `ReportSetCard.escape.test.ts` con la card vera dentro `ModalBase`, il caso in più in `ModalBase.escapeLayers.test.ts`,
  >   nessun E2E del wizard. Anche la regola «un Esc, uno strato» in `CompactDurationBadge` è giusta.»
  > - **Cautela del coordinator**: L sta cambiando l'intestazione di `ReportSetCard` per il mobile. Il test trova «Read as»
  >   solo con testid che esistono già (`report-set-card`, `report-set-read-as` con `-button`, `-dropdown` e
  >   `-option-*`); verificato, niente struttura né classi.
  > - **Esito**: 2 rossi e 55 verdi su 57. I 2 rossi sono:
  >   - escapeLayers, la SimpleSelect `esc-simple`;
  >   - la card «Read as» dentro `ModalBase`.
  >   Su entrambi `onRequestClose` viene chiamato dallo stesso Escape che chiude la lista; prima le premesse passano tutte
  >   (lista chiusa, focus sul trigger, `onReadAs` non chiamato).
  > - **Controlli verdi**: a lista chiusa, l'Escape chiude la modale.
  > - **Verifica di qualità**: il test-author ha simulato la cura con un config temporaneo in `/tmp` (57/57).
  > - **File nuovi**:
  >   - `ReportSetCard.escape.test.ts` e l'harness `ReportSetCardInModalHarness.svelte` (props della modale uguali a quelle
  >     del wizard);
  >   - nel test della card, uno stub di `localStorage`, perché lo store della lingua lo legge al caricamento.
  > - **Registrazione** in `component-unit`, perché `ReportSetCard.test.ts` è nel `tx-unit` di `_frontend_transaction.py`,
  >   fuori perimetro.
- [x] 20.3 Cura: `stopPropagation()` nel `case 'Escape'` di `SimpleSelect.handleKeydown`, con un commento. ✅ 2026-10-08.
  > Esito: vitest su escapeLayers, `ReportSetCard.escape`, `ReportSetCard.test` (di L) e `SimpleSelect.test`, 4 file e
  > 88/88; Prettier pulito.
- [x] 20.4 Verifica ✅ 2026-10-08, corsia 6155, un comando per volta (`/tmp/libreFolio_k20_gates.sh`, carico 12–27):
  > - `front build --debug` ok; `front check` 0/0; `check-orphans` ok;
  > - `component-unit`: 111 file, 2850/2850; `tx-unit`: 15 file, 676/676, con dentro la card di L; nessun errore non
  >   gestito;
  > - E2E `select` 17/17, `tx-import-report-set` 28/28 (spec di L, solo come regressione), `transactions-modals` 19/19.
- [x] 20.5 Handoff: CHECKPOINT READY e la frase di CHANGELOG, che probabilmente estende quella dell'Esc. ✅ 2026-10-08.
  > Due commit proposti, con i messaggi in `/tmp/libreFolio_commits/` e il manifesto `k-20-manifest.txt`.

## Seguito

- Lo step 21 cura due difetti puri: l'avatar dopo una preferenza e il numero nei messaggi degli eventi.
  [`plan-phase00TaxonomySelectStep21PureDefects.prompt.md`](plan-phase00TaxonomySelectStep21PureDefects.prompt.md).
