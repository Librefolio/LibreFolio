# Phase 0 - Onboarding Round 8: correzioni dalla review d'uso e prosecuzione concordata

← Previous:
[Onboarding Round 7 — anchor stall](plan-phase00OnboardingRound7-AnchorStall.prompt.md)

Piano gemello, stesso round di review:
[Privacy Round 2 — correzioni dalla review d'uso](../24_privacyGlobal/plan-phase00PrivacyGlobalRound2-PostReview.prompt.md)

Fonti:
[review d'uso 22/09](../09_feedbackJobs/08_review_visiva_20260922.md) (R3, R4, R19) ·
[dossier di review onboarding](onboarding-review-dossier.md) §6

## Confine e autorizzazione

**Baseline:** `f1047f766`, verificata 2026-09-23 10:33, albero pulito.

**Branch:** `e-alfy-onboarding-foundation`.

**Lane copia prod:** porta `6168`, `/tmp/librefolio-r2-j-onboarding-prodcopy`, solo dalla snapshot
`/tmp/librefolio-r2-prod-snapshot`. **Lane suite:** porta `6158`, `/tmp/librefolio-r2-j-onboarding`,
solo `dev.py test …`.

**Coordinator:** `c8328a01-f208-4ade-a352-0486d1f14de2`.

**Autorizzazione developer verbatim, 2026-09-23:** `Plan approved! Exited plan mode.`

**Schema:** la migrazione `003_user_onboarding_progress` non esiste più; il suo contenuto vive in
`004_release_1_2_0_schema`. Questo round **non crea migrazioni**: se un'opzione ne richiedesse,
stop e domanda al coordinator, che aggiorna la 004.

## Premesse corrette prima di scrivere

- **«Il Round 4 resta valido e va cucito»** — il Round 4 è chiuso dal 2026-09-11, e il suo split
  Bulk in quattro flow persistiti è stato **rovesciato dal Round 5** (*«Import/Bulk tornano a un
  flow ciascuno»*, 2026-09-12). Cucirlo reintrodurrebbe una decisione annullata. Il coordinator
  ha registrato l'errore in 08 §10.
- **La prosecuzione concordata** è la sequenza R7 → R8 → R9 confermata dal developer il
  2026-09-21 nel Round 7. Qui si chiamano **OB-8** e **OB-9**, perché R8 e R9 della review sono
  le candele e la frase di I.
- **R3 «z-index»** — la lettura del codice dà un meccanismo diverso (sotto). Il coordinator l'ha
  registrata.

## Inventario

| # | difetto | causa | file |
|---|---|---|---|
| R3 | la modale «nuova versione» compare dopo, o sotto, il changelog | percorso **admin**: `ChangelogModal:242` → `updateAvailable.show()` → `DeferredAppPopups:41` la **rinvia** finché `modalDepth > 0`. Il percorso non-admin (`AskAdminModal` annidata, `:325`) risponde subito. Il rinvio è giusto per i popup non chiesti e sbagliato per un controllo che l'utente ha chiesto | `DeferredAppPopups.svelte` (mio, `8a8e686f0`), `ChangelogModal.svelte`, `updateCheckStore.svelte.ts`, `UpdateAvailableModal.svelte` |
| R4 | nessun «sei aggiornato» | con R2 attiva la versione era `v1.0.1-97-…` → esito `update-available` → nessun toast «aggiornato» era dovuto. E lo stato `'newer'` **non ha resa inline** | `ChangelogModal.svelte` |
| R19 | frase «Importa ha una guida» | `onboarding.tour.steps.transactionsNav.description`, usata da `OnboardingOverlayHost.svelte:74` | cataloghi i18n ×4 |
| OB-8 | il replay vive in `sessionStorage` e non sopravvive a scheda chiusa o cambio dispositivo | `onboarding.svelte.ts:22` | store onboarding, `OnboardingReplaySection.svelte` |
| OB-9 | uscire dalla route a metà guida riparte dallo step 1; 9 flow su 15 senza E2E | `OnboardingOverlayHost.svelte:641`, `ImportWizardModal:178` (`restartAtFirst`) | host, `onboardingRouteSettlement.ts` (co-autore `e38a521f0`) |

**R3/R4 — osservazione che separa rinvio da impilamento.** Con il changelog aperto, dopo il
check: `[data-testid=deferred-app-popups]` con `data-active-popup="none"` e `data-modal-depth="1"`
è il rinvio; `data-active-popup="update"` è una modale montata ma coperta (il changelog vive
**dentro** la `<nav class="fixed z-50 transform … overflow-hidden">` della Sidebar, senza portal).
R2 è riparata (`v1.1.0-228-gf1047f766`): R4 va ri-verificata in quello stato prima di ripararla.
Il caso `update-available` non è più riproducibile dal vivo: si prova con un test di componente.

## Decisioni — default approvati con il piano

| Q | decisione |
|---|---|
| Q2 | esito «nuova versione» di un check **manuale**: la modale compare **subito sopra** il changelog (richiesta marcata nello store, `DeferredAppPopups` salta il rinvio solo per quella, zIndex sopra 50) + riga di stato inline per **ogni** esito |
| Q5 | OB-8: `localStorage` per utente (la chiave `lf_{userId}_…` è già per utente), cancellato a logout e cambio account, con la nota «vale su questo dispositivo». Nessuno schema |
| Q6 | OB-9: uscire dalla route a metà guida riprende dallo step lasciato, non dallo step 1 |

## Passi

Ogni passo aggiorna questo file dopo il completamento: stato con data, `Note implementazione`,
`Fuori pista`, comando ed evidenza.

### Step 1 — Piano durevole — **Stato: ✅ completato il 2026-09-23.**

Questo file, il gemello privacy, cross-link `→ Follow-up` dal Round 7.

> **Note implementazione:** scritti questo piano e il gemello privacy Round 2; `→ Follow-up` in
> testa al Round 7 e nel §5 del Round 1 privacy. Ogni link relativo risolve, 0 rotti.

### Step 2 — R4, ri-verifica — **Stato: ⏳**

Sulla copia prod, versione `v1.1.0-228-gf1047f766`: Sidebar → versione → «Verifica
aggiornamenti». Registrare: toast visibile o no, stato di `deferred-app-popups`. Solo dopo, il fix.

### Step 3 — R3/R4, fix — **Stato: ⏳**

Per Q2: `updateCheckStore` distingue la richiesta manuale; `DeferredAppPopups` continua a
rinviare i popup non chiesti (contratto invariato) e mostra subito quella chiesta;
`UpdateAvailableModal` sopra il changelog; `ChangelogModal` con una riga di stato inline per
`up-to-date`, `no-release`, `image-pending`, `error`, `newer`. Toast e `notify` invariati: sono il
contratto su cui asseriscono i test.

### Step 4 — R19 — **Stato: ⏳**

`dev.py i18n update onboarding.tour.steps.transactionsNav.description` nelle quattro lingue:
cade solo la seconda frase. La chiave resta (nessuna chiave si dichiara morta prima della fine
del round).

### Step 5 — OB-8 — **Stato: ⏳**

Replay in `localStorage` per Q5, cancellato da `registerClientSessionReset` a logout e cambio
account; il bump di versione continua a invalidarlo; nota in `OnboardingReplaySection`.

### Step 6 — OB-9 — **Stato: ⏳**

Ripresa dallo step lasciato per Q6. E2E dei 9 flow mai provati (modale e dettaglio Broker, FX,
Asset), desktop e mobile, lane 6158, via `test-author`.

### Step 7 — Review manuale e FROZEN — **Stato: ⏳**

## Previsione conflitti

| file | owner | nota |
|---|---|---|
| `DeferredAppPopups.svelte` | J | nessun conflitto |
| `ChangelogModal`, `UpdateAvailableModal`, `updateCheckStore` | nessun owner attivo | ultimo tocco 2026-09-09 |
| cataloghi i18n | condivisi | un valore, via `dev.py`, elencato nell'handoff |
| `ImportWizardModal`, `TransactionBulkModal` | K | vincolo girato dal coordinator: 7 ancore `import.action.*` (`:4586–4770`), 5 del Bulk, step-sync `:164–178` e `:1279`. Secondo K, R18 si ripara in `AssetModal`; rieseguire l'E2E onboarding dopo il merge di K |
| `onboardingRouteSettlement.ts` | co-autore `e38a521f0` | toccato solo se OB-9 lo richiede |
| `features/tools/ToolsHub.svelte` | **D** (assegnato dal coordinator, 2026-09-24) | contiene l'àncora `use:guideAnchor={'tools.hub'}` a `:146`, fissata da `ToolsHub.test.ts:99`: D la preserva. Misurato: **nessuna guida la consuma** (controllo positivo: `nav.tools` consumata a `OnboardingOverlayHost.svelte:109`). Candidata naturale per una guida Strumenti quando esisterà la UI del PAC v2 |

## Test list — approvata con il piano

| # | livello | asserzione |
|---|---|---|
| T8 | componente | `DeferredAppPopups`: i popup automatici restano rinviati con `modalDepth > 0`; la richiesta manuale si mostra subito |
| T9 | componente | `ChangelogModal`: stato inline per ogni esito; percorso non-admin invariato |
| T10 | componente | OB-8: il replay sopravvive a una nuova scheda; cancellato a logout e cambio account; il bump di versione lo invalida |
| T11 | E2E | OB-9: 9 flow, desktop e mobile |

R19 non ha test automatico: niente asserzioni su testo tradotto. Review manuale.

## Runbook review manuale — copia prod `6168`

| dove | cosa | difetto se |
|---|---|---|
| Sidebar → versione → «Verifica aggiornamenti» | stato inline e toast | nessun riscontro visibile |
| tour intro, passo Transazioni | testo | cita ancora la guida di import |
| guida qualunque, cambio di pagina a metà e ritorno | step | riparte dallo step 1 |
| replay da Impostazioni, poi scheda nuova | guida | il replay è perso |

## Definition of done

- Check manuale: riscontro visibile per ogni esito; «nuova versione» subito sopra il changelog;
  popup non chiesti ancora rinviati.
- R19: frase tolta in quattro lingue, chiave conservata.
- OB-8 e OB-9 per Q5 e Q6; E2E dei 9 flow verde desktop e mobile.
- Nessuna migrazione, nessuna chiave rimossa, porte 6158/6168 provate libere al FROZEN.

## CHANGELOG proposto — lo scrive il coordinator

- 🐛 Aggiornamenti: il controllo manuale mostra sempre l'esito, e la nuova versione compare subito.
- 🐛 Onboarding: rimosso dal tour un rimando superfluo alla guida di importazione.
- ✨ Onboarding: il replay di una guida sopravvive alla chiusura della scheda; una guida
  interrotta cambiando pagina riprende da dove era rimasta.
