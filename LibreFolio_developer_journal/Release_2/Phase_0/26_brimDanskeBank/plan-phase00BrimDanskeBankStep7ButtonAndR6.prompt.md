# Piano — fase 00, Danske Bank, passo 7: via il bottone «Escludi dall'import», e R6 (il set spuntato solo in parte)

> **Stato**: ✅ pronta per il checkpoint (2026-10-06, §8.5). Via del coordinatore, con la decisione del developer su R6 (§0).
>
> - Viene da: [plan-phase00BrimDanskeBankStep4Implementation.prompt.md](plan-phase00BrimDanskeBankStep4Implementation.prompt.md), §22 (le decisioni rimandate: il bottone e R6); [plan-phase00BrimDanskeBankStep6UploadRobustness.prompt.md](plan-phase00BrimDanskeBankStep6UploadRobustness.prompt.md) (F2, il passo prima).
> - Workstream L, issue #26. Ramo `e-alfy-l-danske-bank`, base `2a90c1395` (F2); al checkpoint lo script porta L su `dev_release2` = `c9a602f74` (il treno 5: `2a90c1395` più il commit del CHANGELOG), poi committa.

## 0. Decisioni

- **Il bottone** (developer, ask_user, testuale, Step4 §22): «Toglilo, e l'avviso dica di togliere la spunta al set (Consigliato)».
- **R6** (developer, ask_user, testuale, portato dal coordinatore il 2026-10-06): «Fermarsi con un avviso: spunta tutto il set o togli la spunta».
- **Coordinatore**, il via (testuale, in sintesi fedele):
  - opzione 1: `setBlocksAnalysis` vero per 'some'; l'avviso con una chiave nuova ×4; la casella del set risolve; nessuna spunta automatica;
  - il bottone se ne va come da §22;
  - perimetro: `ReportSetCard.svelte` + test, `ImportWizardModal.svelte`, `importReportSets.ts`, `tx-import-report-set.spec.ts`; i18n ×4 solo via `dev.py i18n` (via `importWizard.reportSet.exclude`, la coda di `incompleteBlocks`, la chiave di R6; l'elenco delle chiavi nel passaggio di consegne); doc EN col docs-writer: `import-wizard.md`, `danske-bank.en.md`, la guida del plugin se serve la regola di R6;
  - sovrapposizioni: nessun altro worktree tocca questi file, salvo i 4 cataloghi, aperti anche da D per R7 (la fusione la simula il coordinatore);
  - corsia: `--clean` concesso sulla 6156, solo in `/private/tmp/librefolio-r2-l`, per gli E2E; `front build --debug` prima degli E2E;
  - CHANGELOG: al checkpoint, la frase per la voce Danske, confermata sul codice; proposta «A set ticked only in part waits: tick it whole or untick it.»;
  - rossi prima, col test-author.

## 1. Stato verificato (2026-10-06, sul codice a `2a90c1395`)

- **Il bottone**: `ReportSetCard.svelte` — il commento d'intestazione («…or exclude the set from this import»), la prop `onExclude` (tipo e destrutturazione), `blocks` (`selection !== 'none' && status !== 'complete'`, usato solo dal bottone), il bottone `report-set-exclude`. `ImportWizardModal.svelte` — `excludeSet` e `onExclude={() => excludeSet(set)}`.
- **R6**:
  - `setSelectionState` dà 'all', 'some' o 'none'; con 'some' la casella mostra il trattino (`use:indeterminate`);
  - `setBlocksAnalysis`: 'none' non blocca; altrimenti blocca finché l'anteprima non è pronta e completa. Un set completo spuntato in parte **non** blocca;
  - `buildParseUnits` mette in un'unità i membri spuntati, ma `setRequest` lascia fuori solo i file che non sono membri, mai i membri senza spunta: anteprima e combine leggono il set **intero**;
  - ci si arriva, nei percorsi normali, solo quando un file rientra in un set scegliendo di nuovo il plugin del set: (a) un file spuntato in un set senza spunta, ~~(b) un file senza spunta in un set spuntato~~ (b non è raggiungibile dalla UI, §8.1). Non ci portano la casella del set (tutto o niente: da 'some' un clic toglie tutte le spunte), il caricamento del file mancante (segue la spunta del set) né la tabella dei file singoli.
- **L'avviso** sta nella barra del passo ②: `import-wizard-set-blocks`, col testo di `incompleteBlocks`, quando `blockingSets` non è vuoto; il bottone `import-wizard-parse` è disattivato (`step2CanParse`).
- **Il CHANGELOG** (voce Danske) promette: «None of these commands ticks or unticks a file» → nessuna spunta automatica.

## 2. Il contratto

- `setBlocksAnalysis(set, selectedIds, state)`: 'none' → `false`; **'some' → `true`, qualunque sia l'anteprima**; 'all' → come oggi.
- L'avviso resta uno, `import-wizard-set-blocks`, con un attributo nuovo `data-reason`:
  - `partly-selected` se almeno un set è spuntato in parte (ha la precedenza), col testo della chiave nuova `importWizard.reportSet.partlySelectedBlocks`;
  - `incomplete` altrimenti, col testo di `incompleteBlocks`.
- La casella del set risolve: da 'some' un clic toglie la spunta a tutto il set (com'è oggi), un secondo clic lo spunta intero.
- Nessuna spunta automatica; nessun cambiamento a `setRequest`, a `buildParseUnits` né all'API.
- Il bottone `report-set-exclude`, la prop `onExclude`, `blocks` ed `excludeSet` spariscono.

## 3. Le chiavi i18n (solo via `dev.py i18n`)

| Chiave | Azione | EN | IT | FR | ES |
|---|---|---|---|---|---|
| `importWizard.reportSet.exclude` | **tolta** | — | — | — | — |
| `importWizard.reportSet.incompleteBlocks` | **coda nuova** | …upload its missing file or deselect the set. | …carica il file mancante o togli la spunta al set. | …téléversez le fichier manquant ou désélectionnez le lot. | …sube el archivo que falta o deselecciona el conjunto. |
| `importWizard.reportSet.partlySelectedBlocks` | **nuova** | Continue is disabled while a set is only partly selected: select the whole set or deselect it. | Continua è disattivato finché un set è spuntato solo in parte: spunta tutto il set o togli la spunta. | Continuer est désactivé tant qu'un lot n'est sélectionné qu'en partie : sélectionnez tout le lot ou désélectionnez-le. | Continuar está desactivado mientras un conjunto esté seleccionado solo en parte: selecciona todo el conjunto o deselecciónalo. |

L'EN usa «select/deselect» come l'etichetta della casella («Select the whole set»); l'IT tiene le parole del developer.

## 4. I test, rossi prima (test-author)

- `importReportSets.test.ts` (`front-transaction tx-unit`; il test del file concesso): `setBlocksAnalysis` vero per 'some' anche con l'anteprima pronta e completa (rosso); guardie: 'none' falso, 'all' completo falso, 'all' incompleto o in caricamento vero.
- `ReportSetCard.test.ts` (`tx-unit`): un set selezionato e incompleto non ha `report-set-exclude` (rosso); il montaggio senza `onExclude`.
- `tx-import-report-set.spec.ts`:
  - i 4 clic su `report-set-exclude` passano alla casella del set, `report-set-select`, con lo stesso intento;
  - R6-E1 (rosso): coppia Danske completa e spuntata → «Togli dal set» per un membro (resta spuntato) → la casella del set toglie la spunta all'altro → il membro tolto torna nel set scegliendo di nuovo Danske → set 'some': `import-wizard-parse` disattivato, `import-wizard-set-blocks[data-reason="partly-selected"]` visibile; un clic sulla casella → l'avviso sparisce; un secondo clic → set intero, `import-wizard-parse` attivo.

## 5. Doc EN (docs-writer)

- `developer/frontend/components/features/import-wizard.md` (:289–290): niente bottone; l'avviso con `data-reason`; la regola di R6.
- `user/transactions/import/danske-bank.en.md` (:48): togliere la spunta al set al posto del bottone; il set spuntato solo in parte aspetta.
- La guida dei plugin, se la regola di R6 va accanto a quella di R5.

## 6. CHANGELOG

- La frase per la voce Danske, **confermata sul codice** il 2026-10-06 (`setBlocksAnalysis` vero per 'some' → `blockingSets` → `step2CanParse` falso → **Parse** disattivato; la casella da 'some' toglie la spunta a tutto il set, il secondo clic lo spunta intero): «A set ticked only in part waits: **Parse** stays disabled until you tick the whole set or untick it.» Rispetto alla proposta nomina il bottone che resta disattivato.
- Il bottone non è mai uscito in una versione e il CHANGELOG non lo nomina (verificato su `c9a602f74`): nessuna riga per toglierlo.

## 7. Gate e definizione di fatto

- I rossi rossi sul loro punto, poi verdi.
- `front check`; `front-transaction tx-unit`; `component-unit` (log conservato); `i18n audit` e parità delle chiavi nei 4 cataloghi; `front build --debug`; `--clean`; `tx-import-report-set` a 1 e a 4 worker, `-guide`, `tx-import-file-selection`, `tx-bulk-import-handoff`; `check-orphans`; `mkdocs build` e `check-links`; prettier sui file toccati; scanner di privacy; `git diff --check`; porta 6156 libera.

## 8. Avanzamento

### 8.0 ✅ L'analisi (2026-10-06)

- Mandata al coordinatore dopo la validazione di F2; la decisione del developer su R6 è arrivata col via (§0).

### 8.1 ✅ I rossi (test-author, 2026-10-06)

> **Note implementazione** (log nella sessione, `files/r6-reds/`):
> - `importReportSets.test.ts`:
>   - il vecchio test «…wholly or partly selected» diceva 'some' + completo → `false`, cioè il contrario del contratto: la riga è tolta e il test si chiama ora «lets a wholly selected complete set through»;
>   - rosso «R6 (step 7): blocks a set ticked only in part even when its preview is ready and complete»;
>   - guardia per 'some' senza anteprima, in caricamento, in errore;
>   - le altre guardie c'erano già.
> - `ReportSetCard.test.ts`:
>   - il montaggio senza `onExclude`, e `rerender`;
>   - rosso «…ticked (all/some): no «Exclude from the import» button», con la premessa che corpo e casella siano visibili;
>   - il test del caricamento del file mancante tiene la sua parte e perde il clic su «Exclude».
> - `tx-import-report-set.spec.ts`:
>   - un helper `untickSet` (la casella, poi `data-selected="none"`) al posto dei 4 clic, in R4, G-memory (alone), H-E6 e R5-E1 ×2;
>   - R3 controlla anche `data-reason="incomplete"`;
>   - **R6-E1**, nuovo;
>   - l'intestazione del file è aggiornata.
>
> | Comando (corsia 6156; build `--debug` del codice di prima; `--clean` fatto) | Esito |
> |---|---|
> | `front-transaction tx-import-report-set` | 26 verdi, 2 rossi: R3 (`data-reason` assente) e R6-E1 (`import-wizard-parse` attivo, «Parse (1)», col set `complete` e `some`). I 4 punti adattati sono verdi |
> | `front-transaction tx-unit` | 629 verdi, 4 rossi: `setBlocksAnalysis` per 'some'; il bottone presente (×2, `all` e `some`); la casella (sotto) |
>
> **⚠️ Fuori pista**:
> - **Un difetto in più, trovato dal test-author**: da un set spuntato in parte, il clic che toglie la spunta lasciava la casella **spuntata**. Svelte riscrive `checked` solo quando cambia il valore calcolato, e da 'some' a 'none' resta `false`, quindi il segno disegnato dal browser restava. È proprio il percorso con cui R6 chiede di risolvere, nel file di L: corretto in questo lotto, col suo rosso e una guardia.
> - **R6-E2 non è scritto**: un file senza spunta non può rientrare in un set spuntato dalla UI, perché solo un file singolo spuntato ha il suo menu di plugin. Corretto §1.
> - Non coperta da E2E la precedenza di `partly-selected` su `incomplete` con due set (servirebbe un secondo caricamento): è un ternario nel template.
> - ESLint non è installato nel worktree; prettier è pulito.

### 8.2 ✅ La cura (2026-10-06)

> **Note implementazione**:
> - `importReportSets.ts`: in `setBlocksAnalysis`, 'some' → `true`.
> - `ReportSetCard.svelte`:
>   - tolti il bottone, la prop `onExclude` e `blocks`;
>   - il commento d'intestazione dice come si lascia fuori un set, e la regola di R6;
>   - l'azione `indeterminate` diventa `selectionState`, che scrive `checked` e `indeterminate` a ogni cambio; via `checked={…}`. Prettier ha rimesso l'`<input>` su una riga.
> - `ImportWizardModal.svelte`: tolti `excludeSet` e la prop; aggiunto `partlySelectedSets`; l'avviso ha `data-reason` e il testo giusto.
> - i18n, solo via `dev.py i18n` (lo script è nella sessione, `files/r6-runs/i18n_changes.sh`): §3, 6 righe per lingua; parità a 4356 chiavi per lingua.

### 8.3 ✅ La documentazione (docs-writer, 2026-10-06)

> **Note implementazione**:
> - `import-wizard.md`: la riga di `setBlocksAnalysis` nella tabella delle funzioni; il passo `select`, con l'avviso e `data-reason`, la regola di R6, `selectionState` e il perché.
> - `danske-bank.en.md`: le righe 48 e **65**, dove la seconda menzione del bottone non era nell'elenco; un paragrafo nuovo su R6, a parole semplici.
> - `brim_plugin_guide.md`: un quarto punto in «How the user changes a set», accanto a R5.
> - `mkdocs build` (strict) ok; `check-links` mostra solo la D28.
> - Notata e non toccata: i due avvisi dicono «Continue is disabled» mentre il bottone dice «Parse (n)». È così da prima; va nel backlog.

### 8.4 ✅ I gate (2026-10-06)

> | Comando (corsia 6156, un comando per volta; log nella sessione, `files/r6-runs/`) | Esito |
> |---|---|
> | parità delle chiavi; `i18n audit` | 4356 ×4; completo, e nessuna delle 3 chiavi fra le inutilizzate |
> | `front check` | svelte-check: 0 errori, 0 avvisi |
> | prettier sui 10 file toccati (binario del lock) | pulito |
> | `front-transaction tx-unit` / `front-utility component-unit` | **633** / **2730 passed** |
> | `front build --debug`, poi `--clean` | ok |
> | `tx-import-report-set` a 1 e a 4 worker | **28** e **28 passed** |
> | `-guide` / `tx-import-file-selection` / `tx-bulk-import-handoff` | **2** / **2** / **2 passed** |
> | `check-orphans`; porta 6156 | pulito; libera |

### 8.5 ✅ Pronta per il checkpoint (2026-10-06)

- Delta:
  - 3 file di codice;
  - 4 cataloghi;
  - 3 file di test;
  - 3 pagine di doc EN;
  - il piano Step4 (un rimando in §22.1);
  - questo piano, nuovo.
- Le chiavi i18n per il passaggio di consegne sono in §3: `importWizard.reportSet.exclude` tolta; `importWizard.reportSet.incompleteBlocks` con la coda nuova; `importWizard.reportSet.partlySelectedBlocks` nuova. I cataloghi li apre anche D (R7): la fusione la simula il coordinatore.
- Fuori dal perimetro elencato, ma è il test del file concesso: `importReportSets.test.ts`.
