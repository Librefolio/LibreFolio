# G — Gallery deterministica (56) · analisi e piano

> Stato: **FROZEN** (solo analisi). Si implementa solo con l'autorizzazione del developer riportata dal coordinatore
> (`aec04834-1532-4d86-9e3f-f942e82aca89`). Piano nel repo, al via:
> `LibreFolio_developer_journal/Release_2/Phase_0/56_galleryDeterminism/plan-phase00GalleryDeterminism.prompt.md`.

## Baseline

- Worktree `e-alfy-laughing-spoon`, branch `e-alfy-g-gallery-deterministica`, HEAD `b631308d5` = target `dev_release2`
  (fast-forward fatto dal coordinatore), worktree pulito.
- Corsia 6153 + `/tmp/librefolio-r2-g` (porta libera). `node_modules` assente → `npm ci` pre-approvato una volta.
- Grafo wiki assente (atteso): lette le pagine `gallery-is-a-release-gate-with-real-data`,
  `playwright-probes-ignore-timeout`, `login-returns-before-the-app-has-started`, `load-only-red-is-a-product-defect`.

## Problema e approccio

Le 27 instabili stanno quasi tutte nei test «vecchi» della spec (attese a tempo, `appears()` brevi, `isVisible()`
istantanei, scroll senza verifica). I test recenti (Risk, PAC, Files, onboarding-replay) assestano già bene e sono stabili.
`screenshot()` (132 chiamate) assesta solo networkidle + 200 ms.

Approccio: un solo assestamento dentro `screenshot()` (nuova fixture `fixtures/galleryShot.ts`) + correzioni puntuali
dove la causa è nel percorso del test (sonde, inquadratura, scelta per posizione). Nessuna modifica all'app.

## Cause G-1 (verificate nel codice)

| Classe | Meccanismo | Scatti |
|---|---|---|
| A fase animazioni infinite | `freezeAnimations()` mette `paused` + `animation-delay:-0.1s` dopo il load → fase = tempo trascorso + 0,1 s; annulla i ritardi 0/4/8 s delle linee di `AnimatedBackground` (solo CSS, ignora reduced-motion) | auth/01, 02, 03 |
| B inquadratura | `LotsAnalysisPanel` (slide 200 ms) fa da sé uno scroll smooth a rect fermo; spec: scroll istantaneo + 800 ms; scroll troncato mentre la pagina cresce; `scrollIntoViewIfNeeded`/`center` su blocchi che crescono; header sticky che si nasconde dopo 8 px | fifo-lots-panel/wac ×2, positions-holdings-table, detail-classification, -signals, -editor, -rolling-return |
| C sonde che decidono | preset data `appears(btn, 500)`; prefs `isVisible()` istantaneo su `/settings` (default «profile»); catene `appears(…,1–3 s)`; `isVisible({timeout})` nel FIFO dashboard | positions, signals, fifo, user-preferences, asset-picker, classification |
| D grafici/numeri in corsa | ECharts anima sempre 600/800 ms; `data-chart-ready` resta true nei ridisegni; `TweenedValue` 900 ms su broker detail | brokers/detail, detail-chart(-candlestick), signals-tree, fifo comparison-return (16/16) |
| E transizioni modali | `ModalBase` fade 150 + scale 200 (WAAPI), scatto 300–500 ms dopo visibile | import-modal, sharing, edit-modal, asset-picker |
| F immagini | anteprime e icone con attese fisse | asset-picker, broker list/detail/info |
| G stato vivo condiviso | CachePanel: `current_size` per processo uvicorn; wizard carica file su IB durante il run | cache-panel, global-settings (altezza), wizard/import (da confermare) |
| H ora dell'esecuzione | FileGrid `formatDateTime(uploaded_at)` seminato al populate; «Aggiornato» impostazioni globali; ultima esecuzione scheduler | static-grid, static-tab, brim-*, asset-picker, global-settings |
| I puntatore/altezze/posizione | hover residuo; fit del dialogo prima che il form sia completo; `.first()` sulle card broker | edit-modal (3 altezze), import-modal, asset-picker |

## G-2 / G-3 (ipotesi, nessun verdetto)

- G-3: H1 `SimpleSelect` `onmouseenter` + puntatore fermo sulla tendina + `stepSelectable` senza giro → solo-↓ non arriva;
  H2 `$effect` che resetta l'evidenziazione quando `options` ($derived) cambia. Prova: messaggio con la sequenza,
  riproduzione deterministica (puntatore sull'ultima opzione), 5 run desktop a 10 worker.
- G-2 auth-loading: `appBootstrap.load()` (3 letture parallele) + `goto` dei chunk; ipotesi: ambiente all'avvio /
  lentezza o difetto sotto carico. Prove: log r1, registratore delle richieste in volo, riproduzione del primo blocco.
- G-2 r2 (update modal, lista/picker/promote-merge): forma della risposta (prima riga, prime 4 righe, salto silenzioso),
  orologio (timeout 3–8 s), stato condiviso. Servono i messaggi d'errore.

## Decisioni chieste

D1 istante t* (o `animations:'disabled'`); D2 ora del seed (maschere / normalizzazione / populate); D3 CachePanel e
upload del wizard; D4 M-15 assorbita da G; D5 riferimenti di R dopo il merge di G; D6 run complete e a 10 worker;
D7 dove sono baseline-r1/r2 e il diff noise.

## Conflitti

R: nessun file comune; contratto `data-chart-ready`/`data-chart-renders`/`data-busy`; sequenza dei riferimenti.
L: nessun file comune. M-15 (sezione M). C-82 per G-2.

## Note

- Opt-out del parcheggio puntatore: Security (1677), delete-pair (3039), event popover (5452/5472).
- Statica: `frontend/node_modules/.bin/tsc -p frontend/tsconfig.e2e.json`, `prettier --check` sui file toccati.
- Le modifiche ai test le scrive `test-author`; le run le lancio io, una per volta, in corsia.
