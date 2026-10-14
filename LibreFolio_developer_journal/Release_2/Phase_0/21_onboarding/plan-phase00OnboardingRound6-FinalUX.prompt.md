# Phase 0 - Onboarding Round 6: final UX

← Previous:
[Onboarding Round 5 — progresso per-step e polish contestuale](plan-phase00OnboardingRound5-StepProgressPolish.prompt.md)

→ Follow-up:
[Onboarding Round 7 — anchor stall](plan-phase00OnboardingRound7-AnchorStall.prompt.md)

## Confine e autorizzazione

**Base:** `8f7acd610127d1ba24dcddfef5b9acf4552d4f51`.

**Target isolato:** `4949b2f4c04050e46f643de848894b6706349f34`.

**Branch:** `e-alfy-onboarding-foundation`.

**Lane:** porta 6158, data dir `/tmp/librefolio-r2-j-onboarding`.

**Coordinator:** `c8328a01-f208-4ade-a352-0486d1f14de2`.

**Autorizzazione developer verbatim, 2026-09-14:**
`Plan approved! Exited plan mode.`

Server Round 5 PID 9655 arrestato prima di ogni edit; porta 6158 provata libera.
Nessun target merge, staging, commit/history, force, dato production o porta 6040.

## Contratti da preservare

- 15 flow finali.
- Import/Bulk step-managed nella sola migration 003.
- X current-step.
- Click contestuale auto-advance; Core escluso.
- No waiting flicker.
- Import aggregazioni bloccanti.
- Asset Abs/% globale e override locale.
- Desktop/mobile coerenti.

## Scope

1. Intro 8 secondi.
2. Broker informational step senza auto-scroll.
3. Transaction Form: tipo → obbligatori → opzionali → validazione contestuale.
4. Bulk checkpoint: niente progress/Back/Finish; CTA `Capito`.
5. Message block: fade dopo 3s; hover/focus pieno; leave/blur subito subdued.
6. Unifica asset: `Conferma tutte` solo sulle proposte aperte.

Il bootstrap generico resta automatic-test-only.

## Intro

- Default `durationMs=8_000`.
- Fasi 0/32%/64%; reduced motion invariato.
- Aggiornare hint localizzato a 8 secondi.

## Broker no-scroll

- `broker.page.views` e `broker.page.add`: `scrollPolicy:none`.
- Un target parzialmente visibile conta come visibile.
- `nearest-if-hidden` interviene soltanto se il target è interamente fuori bounds.
- Regression: step 3 non cambia `window.scrollY`; step 4 Add resta sotto header sticky.

## Transaction Form

1. **Tipo**: anchor sul vero `tx-form-type-wrap`.
2. **Obbligatori**: pulse sull'intero fieldset, copy dinamica per tipo.
3. **Opzionali**: pulse sul disclosure.
4. **Valida**: copy spiega che la bozza viene valutata con tutte le operazioni
   pending e che un errore può dipendere da altre righe/saldi; i messaggi indicano il
   contesto coinvolto.

## Bulk checkpoint

Metadata `navigationMode: sequence | checkpoint`.

Bulk:

- no progressLabel;
- no Back;
- CTA `onboarding.actions.gotIt`;
- niente ArrowRight;
- CTA completa solo current step;
- X salta current step.

Import conserva progress sequenziale.

## Fade

- Stato base `fresh/subdued`.
- Timer 3.000 ms per step.
- Hover/focus pieno.
- Dopo leave/blur, se base subdued, ritorno immediato subdued.
- Nessun nuovo delay post-hover.
- Cambio step/error reset fresh.
- Reduced motion senza transition.

## Conferma tutte

Semantica:

- tutte e sole le `state=proposed` aperte;
- signature suggerite invariate;
- nessuna modifica a primarie, partition, gruppi stabili o già decisi;
- una assegnazione `assetGroupConfirmed`;
- una sola `mergeAllTransactions()`.

UI:

- top-level button con `data-testid=asset-group-confirm-all`;
- visibile con almeno due proposte;
- label `Conferma tutte ({count})`;
- sparisce dopo click;
- Continue si abilita salvo busy.

## Piano

### Step 1 - Piano durevole

**Stato:** ✅ completato (2026-09-14).

> **Note implementazione:** server fermato, porta libera, piano creato e Round 5
> cross-linkato.

### Step 2 - Intro e Broker scroll

**Stato:** ✅ completato (2026-09-14).

> **Note implementazione:** Intro default portato a 8s mantenendo proporzioni e
> reduced motion. Broker views/Add usano no-scroll; il visibility check considera
> hidden soltanto un target interamente fuori bounds, evitando il ricentramento del
> grid parzialmente visibile.

### Step 3 - Transaction Form narrative

**Stato:** ✅ completato (2026-09-14).

> **Note implementazione:** basics ancorato al solo wrapper tipo in entrambi i layout;
> amounts resta sull'intero fieldset obbligatori e details sul disclosure opzionale.
> Copy coordinator-owned nello Step 7.

### Step 4 - Bulk checkpoint UI

**Stato:** ✅ completato (2026-09-14).

> **Note implementazione:** catalogo Bulk usa `navigationMode:checkpoint`.
> Overlay nasconde progress/Back, usa CTA `Capito` senza freccia e conserva
> complete/skip sul solo current step. Import resta sequence.

### Step 5 - Fade 3s

**Stato:** ✅ completato (2026-09-14).

> **Note implementazione:** fade base dopo 3s; hover/focus agiscono solo sul visual,
> senza riavviare timer. Al termine dell'interazione un panel già subdued torna
> immediatamente semitrasparente.

### Step 6 - Conferma tutte

**Stato:** ✅ completato (2026-09-14).

> **Note implementazione:** `AssetGroupStep` espone CTA top-level con almeno due
> proposte. Il parent aggiunge in una sola assegnazione soltanto le signature
> `state=proposed` e richiama una sola ricomputazione; primarie, partition e gruppi
> già decisi restano invariati.

### Step 7 - Shared i18n

**Stato:** ✅ completato (2026-09-14).

> **Note implementazione:** coordinator ha applicato esclusivamente via
> `dev.py i18n` 2 add + 9 update; parità EN/IT/FR/ES 3.052/3.052, 0
> incomplete/backend missing, diff-check verde. PAC/unrelated preservati; nessun API
> sync necessario.

### Step 8 - Test-author

**Stato:** ✅ completato (2026-09-14).

> **Note implementazione:** test-author ha aggiornato solo test. Recheck ampi:
> Coachmark/Overlay/Popup 142, AssetGroup/ImportWizard 16, Form 4, Intro 11.
> Playwright Broker desktop/mobile 2 e Confirm All desktop 1 verdi. `front check` 0
> errori/41 warning legacy, Prettier/diff/orphans verdi, porta 6158 libera.
>
> **⚠️ Fuori pista test:** il primo E2E Broker imponeva overlap zero anche al target
> grid viewport-scale/no-scroll. Verdict test-author: assumption; eccezione limitata
> esclusivamente a quello step, mantenendo tutti gli altri invarianti geometry.

### Step 9 - Gate e review 6158

**Stato:** ✅ completato il 2026-09-14 — review feedback chiusa dall'OK verbatim del developer dello stesso giorno; il lavoro post-OK è tracciato nello Step 10. Riga chiusa a posteriori nel Round 7 Step 1.

> **Note implementazione:** component recheck verdi (Coachmark/Overlay 142,
> AssetGroup/Import 16, Form 4, Intro 11), E2E Broker desktop/mobile 2 e Confirm All
> 1. Finali: format, `front check` 0 errori/41 warning legacy, build, Ruff/Black,
> i18n 3.052/3.052 e orphans 206 backend/79 E2E/206 unit verdi. Server riaperto senza
> force su `http://localhost:6158`, PID 89279, HTTP 200.
>
> **Feedback intermedio:** rimosso del tutto l'hint testuale del countdown Welcome.
> Broker step 3 resta no-scroll; step 4 Add usa ora un controllo sticky-header-aware
> che corregge soltanto l'occlusione reale. Il checkpoint Bulk viene riconosciuto
> esplicitamente dal flow ID oltre al catalogo, per impedire progress/Back/Finish
> anche in caso di reattività intermedia. Server fermato prima del patch.
> Coordinator ha rimosso la chiave ormai obsoleta esclusivamente via `dev.py i18n`;
> parità finale 3.051/3.051, 0 incomplete/backend missing e locale diff-check verde.
> Test-author feedback rerun verde: component 7 e Broker desktop/mobile 2. Final
> format/check/build/i18n/orphans/diff verdi. Server review riaperto senza force su
> `http://localhost:6158`, PID 98836, HTTP 200.
>
> **Handoff shared Tool:** `ToolsHub` e `ToolHost` mostrano ora soltanto le versioni
> di compatibilità `Backend/API <contract_version> · UI <ui.version>`.
> `implementation_version` resta disponibile esclusivamente nei pannelli diagnostici.
> Coordinator ha aggiunto `tools.backendVersion`/`tools.uiVersion`; cataloghi
> 3.053/3.053.
> Test-author: ToolsHub 2 e ToolHost 2 pass con versioni fixture distinte e
> implementation assente dal blocco pubblico; `ToolHost.test.ts` nuovo attende
> registrazione coordinator-owned.
> Coordinator ha registrato ToolHost e applicato il batch Tool Round 4, portando i
> cataloghi a 3.167/3.167. Cleanup semantico successivo: fixture Hub/Host e rendering
> usano `ui.version='1.0.0'`; selector registrato verde 4/4. Il fallback numerico
> resta transitorio e read-only finché D non integra il nuovo descriptor.
>
> **Review read-only post-OK:** corretti finding ad alta confidenza:
> 1. Import Bulk handoff dipende da un flag di successo settato solo da
>    `onImportBatch`, non dall'intent iniziale/nested modal.
> 2. Replay session state conserva esplicitamente `mode`; i pending step armati
>    restano replay e consumano una sola entry.
> 3. Operation token impedisce a callback complete/skip tardive di contaminare la
>    guida modal successiva.
> 4. Geometry ascolta il nearest scrollable ancestor reale; il Form body pubblica
>    inoltre lo scroll root esplicito.
>
> **Re-review finale:** due race residue corrette prima del checkpoint:
> - durante replay esplicito, i pending step già consumati restano soppressi fino a
>   esaurimento di `remainingStepIds`;
> - ogni attivazione ha una generation; success callback tardive possono pulire
>   replay/active soltanto se possiedono ancora flow/version/step/generation correnti.
>
> **Review release finale:** corretti ulteriori edge case:
> - step endpoint usa DTO senza `welcome_settings`;
> - token automatici non possono riaprire flow/step terminali;
> - request sequencing separato per flow conserva risultati concorrenti indipendenti;
> - target sopra viewport usa offset header-safe prima del fallback scroll.
>
> I regressioni successivi hanno completato il contratto controller:
> - token automatici Intro/Import terminali vengono rimossi;
> - una load più recente invalida transition precedenti, senza reintrodurre
>   invalidazione tra flow indipendenti;
> - `transitioningFlow` appartiene a un ticket preciso e viene pulito anche dopo
>   cambio account, senza cancellare una transition più nuova.
>
> **⚠️ Fuori pista review finale:** la review read-only ha individuato una queue
> `transaction_create_guide` che poteva sopravvivere alla chiusura/distruzione del
> Form e riaprirsi senza anchor. Il Form ora rilascia active host e queue come una
> singola operazione lifecycle; regressione component dedicata richiesta al
> test-author.
>
> **Correzione developer:** eliminato interamente il compatibility scaffolding
> onboarding prima dell'integrazione. Onboarding non era pubblicato in 1.1.0; il
> prodotto espone una sola shape finale a 15 flow con step progress.
> Test-author ha riallineato i regressioni: API 8, services 14, controller/bootstrap
> 10, component Import/replay/scroll 9, full core 2.075, onboarding E2E 10,
> Import 2 e Asset Identity 1, tutti verdi.

## Runbook review manuale Round 6

1. Welcome: verificare che il tour parta automaticamente dopo 8 secondi.
2. Broker pagina: step 3 non sposta la pagina; step 4 Add resta visibile sotto
   l'header sticky.
3. Add Transaction:
   - Tipo evidenzia solo il controllo tipo;
   - Obbligatori evidenzia il fieldset;
   - Opzionali evidenzia il disclosure;
   - Valida spiega il contesto dell'intero workspace.
4. Bulk: ogni milestone non mostra numero né Back; CTA `Capito`, senza freccia o
   `Termina guida`.
5. Message block: semitrasparente dopo 3s; pieno in hover/focus; subito
   semitrasparente al leave/blur.
6. Import Unifica asset: con almeno due proposte compare `Conferma tutte (N)`;
   click accetta solo le proposte e abilita Continue.
7. Smoke desktop/mobile: Import progress, X-current-step, no-flicker e Asset Abs/%
   restano invariati.

### Step 10 - Post-OK

**Stato:** ✅ completato (2026-09-14).

> **Note implementazione:** developer ha approvato UX Round 6. Docs-writer ha
> riallineato 7 pagine EN; strict MkDocs e link-check verdi. La correzione developer
> ha poi rimosso ogni claim v1/v2/legacy e chiarito il bootstrap generico nelle pagine
> Getting Started/Preferences.
>
> Gate finale, tutti con
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py` e lane
> `--test-port 6158 --data-dir /tmp/librefolio-r2-j-onboarding`:
>
> - `services settings`: 23 pass; `api settings`: 39 pass;
> - `db validate`: 17 pass; `db referential-integrity`: 15 pass;
> - `front-utility core-unit --workers 4`: 2.085 pass;
> - `front-utility onboarding-component-unit`: 361 pass;
> - Tool Hub/Host selector: 4 pass;
> - Auth: 24 pass; onboarding E2E: 10 pass (5 desktop + 5 mobile);
> - Import Flow: 10 pass; Asset Identity: 9 pass; Asset List: 26 pass;
> - dopo il finding lifecycle finale, `front-utility component-unit --workers 4`:
>   1.811 pass in 68 file, incluse 3 regressioni Form close/destroy.
>
> Statici finali: Prettier verde; `front check` 0 errori/41 warning legacy in 2
> file; build production verde; Ruff verde; Black verde su tutti i file backend
> modificati; i18n 3.167/3.167 EN/IT/FR/ES, 0 incomplete/backend missing; MkDocs
> strict e 12/12 link verdi; inventory 206 backend/79 E2E/207 unit registrati e
> raggiungibili; `git diff --check` verde. Il check Black sull'intero `backend/`
> conserva 7 drift preesistenti in file non modificati da J, esclusi correttamente
> dallo scope.
>
> Il canonical API sync coordinator-owned è byte-identico pre/post e conferma un
> solo contratto onboarding finale, senza DTO/query legacy; i request body step
> contengono soltanto `expected_version`. Il build finale non ha introdotto delta
> generated tracked.
>
> La review read-only finale ha trovato un solo finding medio: queue Form
> sopravvissuta a close/destroy. Fix e regressioni sono verdi. Nessun altro finding
> ad alta confidenza. Developer manual review già approvata; porta 6158 libera,
> nessun server/staging/history.

## Test

Tutti nuovi/riparati via test-author.

- Intro 8s.
- Broker no-scroll desktop/mobile.
- Form anchor/copy sequence.
- Bulk checkpoint chrome/transition.
- Fade 3s + hover/focus/leave.
- Confirm All proposal-only/single recompute.
- bootstrap error-handling smoke automatico.

## Definition of Done

- Welcome 8s.
- Broker 3→4 senza scroll/header overlap.
- Form narrativa approvata.
- Bulk usa `Capito`, senza numerazione/Back/Finish.
- Fade 3s corretto.
- Conferma tutte non distruttiva.
- Targeted desktop/mobile verdi.
