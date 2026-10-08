# Piano — K / step 21: due difetti puri (l'avatar dopo una preferenza, il numero nei messaggi degli eventi)

> Lotto approvato dal developer (testuale, via coordinator, 08/10 17:39): «vai con i difetti puri». Li ha trovati Q
> confrontando doc e codice, e il coordinator li ha verificati. Viene dallo step 20
> ([`plan-phase00TaxonomySelectStep20SimpleSelectEscape.prompt.md`](plan-phase00TaxonomySelectStep20SimpleSelectEscape.prompt.md)).

| | |
|---|---|
| **Baseline** | `cf4248bd9` = `dev_release2` (treno 16), pulita; lo step 20 (`5f8e0b905`, `260a53ae4`) è in HEAD |
| **Lane suite** | `--test-port 6155 --data-dir /tmp/librefolio-r2-k`, preambolo `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` |
| **Ordine** | test rossi prima, via test-author, poi la cura, poi il checkpoint. Il CHANGELOG lo scrive il coordinator. |
| **Conflitti** | nessun ramo locale tocca dalla merge-base `PreferencesTab.svelte`/`.test.ts`, `settings.ts`, `AssetDataEditorSection.svelte`, `asset-event-delete.spec.ts` e `settings.spec.ts` (verificato il 08/10, 17:45) |

## Difetto 1: l'avatar sparisce dalla sidebar dopo il salvataggio di una preferenza

- `components/settings/tabs/PreferencesTab.svelte:172-178` (`syncPersistedPreferences`, chiamato a `:195` e `:247` dopo
  un salvataggio) fa `userSettings.setDirect({language, base_currency, theme})`.
- `stores/app/settings.ts:122-125`: `setDirect` fa `set(settings)` e **sostituisce** l'intero valore. `avatar_url`, come
  ogni altro campo, si perde finché le impostazioni non si ricaricano. La sidebar lo legge a `Sidebar.svelte:63`
  (`$userSettings?.avatar_url`).
- **Gli altri chiamanti di `setDirect`**:
  - `auth.ts:108`, dopo il login: l'oggetto completo della risposta. La sostituzione è giusta.
  - `welcome/+page.svelte:143`: l'oggetto completo del PUT. Il ramo `:145` unisce già da sé (`{...currentSettings, …}`).
  - `ProfileTab.svelte:239`: unisce già da sé (`{...currentSettings, avatar_url}`).
- **Cura scelta: nel chiamante**, con lo stesso schema di ProfileTab e welcome:
  `userSettings.setDirect({...userSettings.get(), language, base_currency, theme})`.
  - Il contratto di `setDirect` (sostituire) non cambia, perché a login e welcome serve così.
  - Con lo store ancora vuoto (`get()` nullo) il comportamento resta quello di oggi.

## Difetto 2: nei messaggi degli eventi il numero non compare

- `components/assets/AssetDataEditorSection.svelte:409` (`events.deleteSuccess`) e `:415-420` (`events.deleteBlocked`)
  passano `count`, ma i 4 cataloghi usano `{n}`.
- svelte-i18n non formatta un messaggio a cui manca un valore, quindi mostra il testo grezzo: «Asset data: {n}
  event(s) deleted».
- **Cura consigliata e scelta**: il codice passa `n`, così i 4 cataloghi restano com'erano.
- L'E2E `asset-event-delete.spec.ts` controllava solo la risposta dell'API e mai il toast: per questo il difetto non si
  vedeva.

## Trovati in più: approvati dal coordinator, entrano nel lotto

Una scansione in sola lettura dei `$t(…, {values: {…}})` contro i segnaposto del catalogo EN ha trovato altre **6
chiamate** della stessa classe (`count` contro `{n}`):
- `routes/(app)/fx/+page.svelte:864` (`fx.delete.resultDeleted`);
- `components/brokers/BrokerImportFilesModal.svelte:146` (`uploads.uploadBatchSucceeded`), `:191`
  (`uploads.deleteFailedSome`), `:194` (`uploads.deleteBatchSucceeded`), `:426` (`uploads.confirmBulkDelete.message`);
- `components/ui/input/DistributionEditor.svelte:547` (`assets.distribution.deleteConfirmMessage`).
- Gli altri 23 risultati della scansione erano falsi positivi, controllati uno per uno.
- In più, il toast di `AssetDataEditorSection.svelte:438` ha il prefisso «Asset data:» scritto in inglese nel codice.
- **Decisioni del coordinator** (08/10, testuali in sintesi fedele):
  - «Via libera per i sei casi in più e per il test di guardia. Sono lo stesso difetto puro approvato dal developer.»
  - `routes/(app)/fx/+page.svelte` è di K per questo lotto; O lavora sulle stringhe FX scritte fisse, in
    `fx/[pair]/+page.svelte` e nei componenti FX.
  - Il test di guardia è rosso prima sui casi attuali, verde dopo. Sta in un file che un'unità esistente raccoglie già,
    oppure si registra nel runner dichiarandolo. Legge i cataloghi al momento in cui gira, perché O aggiungerà chiavi.
  - Il prefisso «Asset data:» va nel backlog: una chiave nuova toccherebbe i cataloghi in parallelo con O.
  - **Non si toccano**: `scripts/test_runner/_frontend_utility.py` e `_frontend_portfolio.py`, dove N registra i suoi
    test; `e2e/assets/asset-modal.spec.ts`, dove N corregge l'NR «Bug G».
- **Dove va la guardia**: un `describe` nuovo in `src/lib/i18n/catalogIcuLocale.test.ts`, già raccolto da `core-unit`
  (`_frontend_utility.py:131`), quindi nessuna riga nel runner. Nessun ramo tocca quel file.
  - Riusa i cataloghi del file (i quattro JSON, letti a ogni esecuzione) e il suo `parse()`, che è la classe del
    runtime (`getMessageFormatter`) con l'`ignoreTag` di svelte-i18n.
  - Le chiamate del codice si leggono con `svelte/compiler` (`parse`, AST moderno), non con espressioni regolari: la
    scansione a regex aveva 23 falsi positivi su 31.
  - Copre i `$t(...)` e `$_(...)` dei `.svelte` con chiave letterale e `values` letterale; quelli con spread o chiavi
    calcolate si saltano, dichiarandolo.

## Test (rossi prima, test-author)

1. **Difetto 1**: `PreferencesTab.test.ts`.
   - Il mock di `userSettings.get` diventa controllabile, nullo per default, così i test esistenti non cambiano.
   - Caso nuovo: lo store contiene già `avatar_url` e un campo in più; dopo il salvataggio di ciascuno dei tre campi,
     l'oggetto passato allo store conserva `avatar_url` e il campo in più, con il nuovo valore. Rosso oggi:
     `avatar_url` manca.
2. **Difetto 2**: `e2e/assets/asset-event-delete.spec.ts`.
   - Nei due test esistenti (cancellazione riuscita e cancellazione bloccata), il toast mostra il numero. Si controlla il
     **valore** interpolato e l'assenza del segnaposto `{n}`, mai il testo tradotto.
   - Rosso oggi: il toast contiene il letterale `{n}`.

## Passi

- [x] 21.1 Base `cf4248bd9` verificata pulita; codice letto; piano nel repo. ✅ 2026-10-08.
- [x] 21.2 Rosso: il difetto 1 (vitest) e il difetto 2 (E2E, corsia 6155); poi la guardia. ✅ 2026-10-08.
  > **Note implementazione** (test-author):
  > - **E2E** `front-asset asset-event-delete`, 2 rossi e 2 verdi.
  >   - Riuscita: il toast dice «Asset data: {n} event(s) deleted».
  >   - Bloccata: «Cannot delete: {n} event(s) … ({accessible} …, {hidden} …)». Anche `{accessible}` e `{hidden}` restano
  >     grezzi, perché fallisce la formattazione dell'intero messaggio.
  >   - Il toast giusto si individua chiudendo, prima del salvataggio, quelli della stessa variante.
  >   - Si controllano il numero e l'assenza di `{`, mai le parole.
  > - **vitest** `PreferencesTab.test.ts`, 4 rossi e 54 verdi.
  >   - I rossi: un `it.each` su tema, lingua e valuta, più il salva-tutto (il chiamante `:247`). In tutti l'oggetto dato
  >     allo store non ha più `avatar_url`.
  >   - Il mock `get` ora è controllabile e nullo per default; i 54 test esistenti restano verdi.
  > - **Guardia** in `catalogIcuLocale.test.ts`: un `describe` nuovo con 7 test, 6 controlli e il gate.
  >   - Il file resta in `core-unit`: nessuna riga nel runner.
  >   - Rosso per la ragione attesa: esattamente gli 8 casi, ciascuno nelle 4 lingue. Lo stesso elenco in tre esecuzioni.
  >     Comando: `node_modules/.bin/vitest run src/lib/i18n/catalogIcuLocale.test.ts`, 1 rosso e 16 verdi
  >     (`/tmp/libreFolio_k21_red_guard.log`).
  >   - Misure sull'albero reale:
  >     - 328 componenti letti, più 16 harness di `src/__tests__/` esclusi; 0 rifiutati dal compilatore;
  >     - 4213 chiamate `$t`/`$_` in tutto;
  >     - 347 registrate (136 negli script, 211 nel markup), 0 saltate;
  >     - 447 con chiave template literal, quindi dinamiche e non registrate.
  >   - Controlli sintetici, passati per lo stesso parse e lo stesso controllo:
  >     - segnalati: `{count}` per `{n}`, un nome che serve solo dentro i rami di un plurale, un `select` che manca in una
  >       sola lingua;
  >     - passano: nomi esatti, nomi in più, un plurale con il suo argomento, la forma abbreviata `{values: {n}}`, una
  >       chiamata su più righe con template literal e chiamate annidate;
  >     - spread e chiavi calcolate (anche nelle opzioni attorno a `values`) si saltano e si contano.
  >   - Non vacuo: soglia ≥ 250 chiamate registrate, presenti sia in `src/lib` sia in `src/routes`, più una chiamata nota
  >     e buona (`risk.levels.l4.replaySuggested` in `L4Replay.svelte`, trovata per file e chiave, mai per riga).
  >   - Il gate, i controlli e il latch già presenti nel file restano invariati e verdi (10/10 prima, 10/10 dopo).
  >   - Tempo: il file passa da circa 1,0 s a circa 4,2 s. Il primo test sull'albero reale analizza 328 componenti;
  >     l'analisi è condivisa, quindi il gate in sé richiede circa 20 ms. I due test sull'albero hanno un tetto di 60 s.
  >   - Fuori dalla guardia, dichiarato nell'intestazione: le chiamate `get(t)(…)`/`get(_)(…)` (10 nei `.svelte`;
  >     le 3 con `values` letterale oggi sono giuste) e i moduli `.ts`.
  > **⚠️ Fuori pista**: nessuno. L'intestazione esistente del file dice ancora «Red today with three keys», ma il suo
  > gate è verde: è un testo del lotto precedente, fuori perimetro, e l'ho lasciato com'è.
- [x] 21.3 Cura: `PreferencesTab.syncPersistedPreferences` unisce; gli 8 punti passano `n`. ✅ 2026-10-08.
  > **Note implementazione**:
  > - `PreferencesTab.svelte`: `setDirect({...userSettings.get(), language, base_currency, theme})`.
  >   - `setDirect` mantiene il suo contratto di sostituzione, perché login (`auth.ts`) e welcome passano oggetti
  >     completi. È lo stesso schema di `ProfileTab.svelte:237-242`.
  >   - Con `get()` nullo il risultato non cambia: il test esistente che si aspetta esattamente i tre campi resta verde.
  > - `count`→`n` in `AssetDataEditorSection.svelte:409` e `:416`, `fx/+page.svelte:864`, `BrokerImportFilesModal.svelte`
  >   `:146`, `:191`, `:194` e `:426`, e `DistributionEditor.svelte:547`. Nessun catalogo toccato.
  > - L'intestazione della guardia passa al passato: «It was written red with eight calls … green since».
  > - Prettier: nessuna modifica. Comando: `node_modules/.bin/vitest run src/lib/i18n/catalogIcuLocale.test.ts
  >   src/lib/components/settings/tabs/PreferencesTab.test.ts`, 75/75 verdi (`/tmp/libreFolio_k21_green_unit.log`).
- [x] 21.4 Verifica: ✅ 2026-10-08.
  - i test nuovi, `core-unit` (dove sta la guardia) e `component-unit` (dove sta `PreferencesTab.test.ts`);
  - gli E2E delle preferenze e della sidebar: `front-utility settings`, più `image-crop`, che controlla
    `sidebar-user-avatar`;
  - gli E2E dell'editor degli eventi: `front-asset asset-event-delete` e `asset-data-editor`;
  - per i sei casi in più: `front-broker detail` (`BrokerImportFilesModal`) e `front-fx fx-bulk` (eliminazione delle
    coppie);
  - `front check`.
  > **Note implementazione**:
  > - Un solo script, sequenziale, nella corsia 6155 (`/tmp/librefolio-r2-k`), E2E con `--workers 2`: comando
  >   `/tmp/libreFolio_k21_gates.sh`, log `/tmp/libreFolio_k21_gates.log`.
  > - Risultati:
  >   - `front build --debug`: ok, svelte-check 0/0; `front check`: 0/0;
  >   - `front-utility core-unit`: 117 file, 3442 test verdi; la guardia è in `front_utility_unit`
  >     (`_frontend_utility.py:131`);
  >   - `front-utility component-unit`: 111 file, 2854 verdi;
  >   - `front-utility settings` 45/45; `image-crop` 42/42;
  >   - `front-asset asset-event-delete` 4/4 (i 2 rossi ora verdi); `asset-data-editor` 23/23;
  >   - `front-broker detail` 33/33; `front-fx fx-bulk` 7/7;
  >   - `check-orphans` ok. A fine corsa nessun ascoltatore su 6155; 6165 non usata in questo step.
  > - Carico della macchina alto (loadavg fino a 108, altre corsie attive): nessun rosso, nessun ritentativo.
  > - Nessuna sovrapposizione prevista: tra `cf4248bd9` e `dev_release2` (`108a2adf5`, treno 17, Q) nessun file del
  >   lotto cambia, e nessuno dei 17 rami locali li tocca. La guardia legge però a ogni esecuzione tutti i `.svelte` e i
  >   cataloghi, quindi una chiamata nuova con il nome sbagliato, di qualunque ramo, la fa diventare rossa alla fusione.
  >   È voluto.
- [x] 21.5 Handoff: CHECKPOINT READY al coordinator, poi FROZEN. ✅ 2026-10-08.
  > **Note implementazione**:
  > - Tre commit proposti in `/tmp/libreFolio_commits/`, manifesto `k-21-manifest.txt`:
  >   - `k-58-settings-avatar.txt`;
  >   - `k-59-i18n-count-values.txt`;
  >   - `k-60-journal-21.txt`.
  > - Backlog: il prefisso «Asset data:» scritto fisso (`AssetDataEditorSection.svelte:438`) e, solo da segnalare, le
  >   chiamate `get(t)(…)` fuori dalla guardia.

## Definizione di fatto

1. Ogni test nuovo è rosso sulla base, per la ragione attesa, e verde dopo la cura.
2. I gate sono verdi e `front check` resta a 0/0.
3. Porte libere, nessun venv del worktree, nel worktree solo i file previsti.
