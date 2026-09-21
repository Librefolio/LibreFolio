# Phase 0 - Onboarding Round 5: progresso per-step e polish contestuale

← Previous:
[Onboarding Round 4 — geometry e milestone contestuali](plan-phase00OnboardingRound4-GeometryMilestones.prompt.md)

→ Follow-up:
[Onboarding Round 6 — final UX](plan-phase00OnboardingRound6-FinalUX.prompt.md)

## Confine e autorizzazione

**Baseline/base combinata:** `8f7acd610127d1ba24dcddfef5b9acf4552d4f51`.

**Target isolato:** `4949b2f4c04050e46f643de848894b6706349f34`.

**Branch:** `e-alfy-onboarding-foundation`.

**Lane:** porta 6158, data dir assoluta
`/tmp/librefolio-r2-j-onboarding`.

**Coordinator:** `c8328a01-f208-4ade-a352-0486d1f14de2`.

**Autorizzazione developer verbatim, 2026-09-12:**
`Plan approved! Exited plan mode.`

Il server review PID 14112 è stato arrestato prima di ogni edit e porta 6158 provata
libera. Nessun target merge, staging, commit/history, force, dato production o porta
6040.

## Feedback accettato

- Core: ordine/pointer/placement approvati; rimuovere solo l'action hint.
- Contestuali: mantenere l'hint e auto-avanzare al click reale sul target.
- Cursor subito semitrasparente.
- Message block circa 80% dopo 10 secondi; pieno su hover/focus/cambio step.
- Pulse sulle aree informative Transaction Form/Bulk/Asset e audit Broker/FX.
- Import Select più esplicito e con nota sugli step opzionali.
- Import/Bulk tornano a un flow ciascuno con progresso durevole per-step.
- X salta soltanto current step.
- Step opzionali non incontrati partono al primo incontro futuro.
- Nessun `waiting` flicker durante scroll/revalidation.
- Aggregazioni Asset Import aperte bloccano Continue.
- Toggle globale Asset Abs/% deve propagarsi alle card.

## Root cause

- Gli highlight mancanti sono metadata `highlight:none`, non z-index.
- Lo scroll globale catturato azzera `targetStable` anche se il target footer non si
  muove.
- Import Assets Continue non include `assetGroupOpenProposals > 0`.
- `globalViewMode` Asset non viene passato a `AssetCard`.

## Contratti invariati

- Source of truth backend.
- Nuova versione riapre step/flow terminali.
- Nessun click sintetico, route jump, modal open o financial write automatico.
- Chiusura host senza X/Finish lascia pending.
- Migrazione onboarding ancora unreleased: modificare soltanto `003`; nessuna `004`.

## API onboarding finale

- Un solo contratto GET con quindici flow e progresso per-step.
- Nessuna negoziazione di versione o shape legacy: onboarding non era incluso nella
  release 1.1.0.
- Il bootstrap conserva la gestione errore generica: può degradare soltanto quando
  esiste già uno stato Welcome terminale affidabile; senza stato valido resta
  bloccante.
- Logout block usa `Disconnettiti`.

## Persistenza per-step

Aggiungere nella sola migration `003`:

`user_onboarding_step_progress`

Campi:

- id, user_id, flow, step_id;
- status pending/completed/skipped;
- version;
- created/updated/completed/skipped timestamps;
- unique user+flow+step;
- FK user cascade.

Flow step-managed:

```text
import_guide:
upload → select → analyze → assets? → fix? → duplicates? → review → bulk

transaction_bulk_guide:
workspace → validation? → selection? → save?
```

Rimuovere i tre ID draft:

- `transaction_bulk_validation_guide`;
- `transaction_bulk_selection_guide`;
- `transaction_bulk_save_guide`.

Totale flow finale: 15.

Regole:

- unseen step pending;
- target click/Finish completed;
- X automatico skipped sul solo step;
- host close resta pending;
- aggregate flow pending finché uno step è pending/outdated;
- tutti terminali → skipped se tutti skipped, completed altrimenti;
- nuovo step richiede bump del flow.

Endpoint:

```text
POST /settings/onboarding/{flow}/steps/{step_id}/complete
POST /settings/onboarding/{flow}/steps/{step_id}/skip
```

## Frontend controller

- Catalogo `completionMode: flow | steps`.
- Queue key `(flow, stepId)`.
- Import parte soltanto se current host step è due/replay.
- Bulk usa un flow e accoda milestone step.
- Finish/X step-managed chiamano endpoint step.
- Replay flow conserva set transient di step rimanenti.
- Settings mostra N/M e stato per-step.

## Click target

Metadata `advanceOnTarget` per tutte le azioni contestuali; Core escluso.

- Osservare il click reale in capture, mai generarlo.
- Flow lineare: next/finish.
- Flow step-managed: complete current step, host sceglie il prossimo.
- Guard snapshot active evita doppio advance.
- Errore transition resta esplicito e lo step resta due.

## Matrice visuale

- action reale → cursor semitrasparente;
- area informativa/overview → pulse;
- Core → backdrop+pulse+cursor, senza action hint.

Correggere:

- Transaction Form basics/amounts/details;
- Bulk workspace/validation/selection;
- Asset page overview/filters;
- Asset Add search/identity/provider;
- Asset detail header/chart;
- audit Broker/FX.

Form basics punta al wrapper tipo+broker, non al titolo.

## Geometry senza flicker

Stati:

```text
waiting → revalidating → stable
```

- Conservare ultimo rect valido durante revalidation.
- Aggiornare rect sullo scroll ancestor pertinente.
- Non ascoltare scroll di sibling irrilevanti.
- Busy label solo prima misura/anchor assente.
- Pointer/pulse/panel restano visibili.
- Pubblicare `data-geometry-state`.

## Opacità

- Cursor iniziale circa 70%.
- Message block pieno al cambio step.
- Dopo 10s background circa 80%.
- Hover/focus pieno; leave/blur riavvia timer.
- Reduced motion elimina transizione, non stato.

## Import

Select IT:

> Seleziona uno o più report salvati. Per ciascun file scegli il plugin di analisi
> adatto; quando tutte le selezioni sono complete, usa il pulsante a destra per
> continuare. In base al plugin e ai dati estratti potranno comparire passaggi
> opzionali per unificare asset, correggere righe o gestire duplicati.

Fix Assets Continue:

```text
disabled |= assetGroupOpenProposals > 0
```

Progress visibile resta dinamico.

## Asset global Abs/%

- Passare `globalViewMode` a ogni `AssetCard`.
- Pubblicare `data-view-mode`.
- Testid sui due toggle globali.
- Cambio globale azzera override locali tramite effect esistente.
- Toggle locale continua a cambiare una sola card.

## Superfici

Backend:

- models, schemas/settings, onboarding service, settings API, migration 003.

Frontend:

- onboarding types/API/catalog/controller/bootstrap;
- Coachmark/Overlay/Replay/BootstrapBlock;
- Transaction Form/Bulk/Import;
- Asset page/Card/Modal/detail;
- anchor Broker/FX.

Shared coordinator-owned:

- API sync;
- EN/IT/FR/ES;
- runner;
- changelog/backlog/master.

## Piano di esecuzione

### Step 1 - Piano durevole

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** server PID 14112 fermato, porta 6158 libera; creato e
> cross-linkato Round 5 preservando le parti Round 4 accettate.

### Step 2 - Schema e service per-step

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** aggiunta `user_onboarding_step_progress` nella sola
> migration `003`, con registry step Import/Bulk, ensure idempotente, transition
> complete/skip e aggregate flow. Rimossi dal registry backend e dal seed i tre flow
> Bulk draft; totale finale 15.

- nuova tabella nella sola 003;
- registry step;
- ensure/aggregate/transition;
- rimozione tre Bulk draft flow.

### Step 3 - API finale

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** GET onboarding espone un solo contratto con 15
> flow/steps e gli endpoint step generici. Il block usa `Disconnettiti`.
>
> **⚠️ Deviazione developer post-OK:** rimosso integralmente l'esperimento di
> compatibilità multi-shape prima dell'integrazione: onboarding non è mai stato
> pubblicato in 1.1.0, quindi non esiste alcun client released da supportare.

- shape finale unica;
- endpoint step;
- error handling bootstrap generico.

### Step 4 - Controller step-managed

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** catalogo finale a 15 flow con Import/Bulk
> `completionMode:steps`; queue deduplicata su `(flow,step)`, due predicate,
> complete/skip current step, replay con `remainingStepIds` e Settings N/M con
> dettaglio step. Bulk usa nuovamente un solo flow e Import avvia soltanto lo step
> host ancora due/replay.

- queue flow+step;
- Import/Bulk grouped;
- X current step;
- replay step set;
- Settings N/M.

### Step 5 - Click auto-advance

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** Coachmark osserva in capture soltanto il click reale
> sugli step contestuali con cursor. Flow lineari eseguono next/finish; flow
> step-managed completano current step e lasciano il cambio host al wizard/modal.
> Core resta escluso e non mostra più l'action hint. La completion async non azzera
> una nuova guida già attivata dallo stesso click.

- listener click reale;
- sequential/step-managed;
- Core escluso;
- error/idempotency.

### Step 6 - Highlight/opacity/geometry

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** tutte le aree informative contestuali usano pulse,
> mentre le azioni mantengono cursor. Il cursor è semitrasparente; il panel passa a
> background 80% dopo 10s e torna pieno su hover/focus/step. Geometry distingue
> waiting/revalidating/stable, conserva l'ultimo rect e ascolta soltanto window o lo
> scroll root ancestor pertinente: nessun busy-text flicker su sibling scroll.

- pulse audit;
- cursor translucency;
- no Core hint;
- panel timer;
- revalidation senza flicker.

### Step 7 - Import/Asset fixes

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** Import Assets Continue include ora
> `assetGroupOpenProposals > 0`; la copy Select è pronta per il handoff i18n.
> `globalViewMode` viene passato a ogni `AssetCard`, i toggle globali hanno testid e
> la card pubblica `data-view-mode`, preservando l'override locale esistente.

- copy Select;
- aggregation gate;
- globalViewMode.

### Step 8 - Shared handoff

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** API sync canonico completo con enum finale 15 flow,
> schema step ed endpoint complete/skip; nessun generated tracked.
> I18n applicato solo via CLI: 6 add/move byte-identici, 1 update, 9 remove; parità
> onboarding EN/IT/FR/ES 3.040/3.040, 0 incomplete/backend missing e diff-check
> verde. Il successivo batch PAC coordinator-owned ha aggiunto 10 chiavi e portato i
> cataloghi condivisi a 3.050/3.050; chiavi PAC temporaneamente orfane preservate.

- API sync;
- i18n atomic;
- runner eventuale.

### Step 9 - Test-author

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** test-author ha riscritto i test Round 5; backend verde
> (services 28, API 40, DB 17, scheduler parallelo 3.708). I primi frontend hanno
> esposto blocker production senza indebolire i test: loop revalidation fermato sul
> flag usable invece che stable, geometry
> persa durante suspension ParseDetail e selector mancante sul toggle locale Asset.
> Applicati i fix production. Rerun finali verdi: onboarding component 338,
> controller/core 96, onboarding E2E 8 (4 desktop+4 mobile), Auth 24, Import 10,
> Asset Identity 8 e Asset List 26. Backend già verde: services 28, API 40, DB 17 e
> scheduler parallelo 3.708. `front check` 0 errori/41 warning legacy.
>
> **⚠️ Fuori pista test:** un probe delegato intermedio ha usato per errore porta
> 6487; risultato scartato. Tutti i rerun autoritativi hanno usato lane 6158 e
> entrambe le porte sono state poi provate libere.

- backend schema/API;
- controller/component;
- Import/Asset;
- desktop/mobile/account isolation.

### Step 10 - Gate e manual review

**Stato:** ✅ completato (2026-09-12).

> **Note implementazione:** backend verde (services 28, API 40, DB 17, scheduler
> parallelo 3.708); frontend verde (component 338, core/controller 96, onboarding
> desktop/mobile 8, Auth 24, Import 10, Asset Identity 8, Asset List 26). Format,
> `front check` 0 errori/41 warning legacy, build, Ruff/Black, i18n 3.050/3.050 e
> check-orphans 206 backend/79 E2E/206 unit verdi. Lane fresh/migrata riaperta senza
> force su `http://localhost:6158`, PID 9655, root HTTP 200.

- reset lane per nuova table draft;
- gate mirati;
- server 6158;
- runbook developer.

## Runbook review manuale Round 5

Credenziali lane:
`e2e_test_user` / `E2eTestPass123!`.

1. `/settings` → Preferenze → Primo utilizzo: verificare 15 flow; Import e Bulk
   mostrano N/M step e non quattro righe Bulk separate.
2. Core: nessun sottotesto `Esplora il controllo indicato`; ordine/pointer/placement
   Round 4 invariati.
3. Transaction Form: basics, amounts e details mostrano pulse sull'area; Save conserva
   cursor.
4. Click su Add/Import/Sync/tab/CTA contestuale: la guida avanza senza premere il
   proprio Avanti; Core non auto-avanza.
5. Dopo 10 secondi il panel diventa semitrasparente; hover/focus/nuovo step lo rende
   pieno. Cursor semitrasparente fin dall'inizio.
6. Scrollare contenuto Import/Asset: nessun flash `In attesa`; geometry resta
   anchored/revalidating e torna stable.
7. Import Select: copy file→plugin→continua + nota step opzionali. Un flow già
   completato nei base step deve mostrare in una futura importazione soltanto un
   optional step mai incontrato.
8. Import Unifica asset: con proposte aperte Continue è disabilitato; dopo conferma
   diventa disponibile.
9. `/assets` grid: toggle globale Abs/% aggiorna tutte le card; toggle locale cambia
    una sola card; il successivo cambio globale riallinea tutte.

### Step 11 - Post-OK

**Stato:** bloccato fino a OK developer.

- docs-writer;
- full campaign;
- read-only review;
- shared finali.

## Test obbligatori

Tutti nuovi/riparati via test-author.

Backend:

- entrambe le table in upgrade/downgrade;
- ensure idempotente;
- step complete/skip e aggregate;
- GET finale con quindici flow e steps.

Frontend:

- optional Import futuro senza repeat dei completati;
- Bulk grouped;
- X current step;
- target click contextual; Core no;
- pulse matrix;
- no waiting flicker;
- opacity timer/hover/focus;
- degraded bootstrap.

Import/Asset:

- aggregazioni bloccano;
- global Abs/% tutte card;
- local override una card.

Playwright:

- desktop/mobile highlight;
- scroll senza flicker;
- auto-advance click;
- optional trigger futuro;
- account isolation.

## Rischi

- Lane ha 003 vecchia: reset clean obbligatorio prima review.
- Aggregate pending lungo: Settings N/M esplicito.
- Click/unmount race: snapshot/idempotenza.
- Flow rollback Bulk: rimuovere tre ID/test/i18n atomicamente.

## Definition of Done

- Core senza hint.
- Aree informative evidenziate.
- Cursor semitrasparente.
- Nessun waiting flicker.
- Panel attenuato dopo 10s.
- Import/Bulk flow unici step-managed.
- Optional futuri al primo incontro.
- X current step.
- Click target avanza.
- Aggregazioni bloccano Continue.
- Asset Abs/% globale funziona.
- Nessuna 004; test desktop/mobile verdi.

La review developer ha accettato step progress, auto-advance, no-flicker, Import
aggregation e Asset Abs/%. Round 6 rifinisce esclusivamente timing, Broker scroll,
narrativa Form, checkpoint Bulk, fade e conferma massiva Asset.
