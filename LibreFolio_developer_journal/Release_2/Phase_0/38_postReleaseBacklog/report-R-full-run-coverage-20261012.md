# Rapporto R — run completa con coverage (Release 2, treno 68)

> Sessione **R**, notte 12→13/10/2026. Solo misura, rilanci e classificazione: nessun file di codice, test o
> configurazione toccato. Corsia esclusiva `--test-port 6176 --data-dir /tmp/librefolio-r2-r-cov`.

## 0. In breve

| | |
|---|---|
| **Base** | `a5653f9efa8d56746e40e7a0a8662a10a7182956` (treno 68, con il CP1 di M-18), verificata con `git rev-parse HEAD`, albero pulito |
| **Comando** | `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc LIBREFOLIO_TEST_STARTUP_TIMEOUT=900 pipenv run python dev.py test --coverage --fresh-run --cov-clean-backend --cov-clean-backend-e2e --workers 2 --test-port 6176 --data-dir /tmp/librefolio-r2-r-cov all` |
| **Durata** | 19:40:55 → 00:02:03 = **4 h 21 min** (più 5 min del tentativo 1, morto prima dei test: §1.2) |
| **Carico** | load 1-min tra 9,6 e **151** (picchi 112 alle 20:28, 125 alle 23:05, 151 alle 23:13); media 1-min 37,9 sui campioni ogni 30 s 22:20→00:02 |
| **Esito** | **10/15 categorie verdi.** Rosse: Frontend Utility, FX, Asset, Transaction, AI Export |
| **Test** | pytest **12 627 ✓ / 0 ✗** (28 skip voluti) · vitest **10 760 ✓ / 0 ✗** · Playwright **1 163 ✓ / 29 ✗** (32 skip voluti) |
| **Rossi** | **29**, tutti E2E Playwright `desktop`; **zero rossi backend, zero rossi vitest** |
| **Coverage** | backend da test **91,51 %** (righe+archi; righe 93,53 %, rami 84,78 %) · backend da E2E 29,32 % · JS/Svelte **71,24 % statement**, 62,82 % rami |

**Rossi per classe** (dettaglio al §3):

| classe | n. | cosa | proprietario probabile |
|---|---|---|---|
| (a) carico | **27** | verdi da soli (11 azioni rilanciate da sole: 142/142 verdi), scaduti nella run: 15 teardown della coverage JS, 9 attese post-login, 2 dettaglio FX, 1 tabella transazioni | V (rinforzo delle attese e dell'harness) |
| (b) ambiente | 0 | — (il solo incidente d'ambiente è avvenuto prima dei test: §1.2) | — |
| (c) interferenza fra test | 0 | nessun rosso mostra dati o stato spostati da un vicino | — |
| (d) difetto del test | 0 come causa diretta | ma sotto i rossi (a) ci sono budget fissi su percorsi che dipendono dal carico (§3.2, §3.3) | V |
| (e) difetto del prodotto | **2** | `toolbar-width-sweep` in spagnolo: la barra di Asset Detail e della Dashboard sfora di 5–17 px | **M** (introdotto da `7c66234a7`), cura in UI (soglie) |

**I primi da guardare**

1. **(e) `toolbar-width-sweep` · es** — regressione vera e deterministica: rifallisce da sola, identica al pixel, anche
   a load 15. La causa è il cambio di termine «Exportar IA» → «Exportación IA» di `7c66234a7` (M, treno 40, 11/10
   22:27), arrivato dopo la calibrazione delle soglie (`3e5313d3e`, 30/09). §3.1.
2. **Il teardown di `jsCoverage`** — 15 rossi su 29 sono la raccolta della coverage JS che consuma il budget di 30 s
   del test: esistono solo con `--coverage js` e sotto carico. Il fixture non ha un timeout proprio. §3.2.
3. **`login()` ritorna prima che l'app sia partita** — 9 rossi (auth ×5, AI Export ×4) aspettano 3–5 s un URL o un
   controllo che sotto carico arriva dopo. È lo stesso schema che K ha corretto il 07/10 solo nello sweep. §3.3.
4. **Coverage JS**: il planner del PAC (`src/lib/features/tools/pac-allocator/planner/`, 7 008 statement, dal 25/09)
   è al **14 %**: da solo spiega il calo rispetto al 03/09. Senza `features/tools` il frontend è al 78,4 %. §4.2.

---

## 1. Esecuzione

### 1.1 Ambiente

- Worktree app-managed, `.env` assente (non copiato), venv condiviso `LibreFolio-SAUMUTtc`, mai `./dev.py` nudo.
- `npm ci` unico in `frontend/` dal lock: 433 pacchetti, lock intatto (`/tmp/libreFolio_R_npm_ci.log`). npm 11.20
  segnala 5 install script non approvati (esbuild, fsevents, es5-ext): ininfluenti, vite/esbuild/playwright/vitest
  partono.
- Una sola invocazione di test alla volta nella corsia 6176, sempre.

### 1.2 Tentativo 1: ambiente, prima dei test (19:33 → 19:38)

- `❌ Shared backend did not answer within 300s` → `❌ shared test backend failed to start`, rc=1, **nessun test
  eseguito** (`/tmp/libreFolio_R_full_run_attempt1.log`).
- Causa: in una worktree fresca il primo `dev.py server --test` ricostruisce il frontend (≈2,5 min) e poi MkDocs; con
  load 47–54 la somma ha superato `STARTUP_TIMEOUT` = 300 s (`scripts/test_runner/_server.py:48`). Il server è stato
  fermato a metà del build MkDocs, lasciando un sito parziale (243 MB contro 294).
- Rimedio, solo d'ambiente e nella mia corsia: sito MkDocs ricostruito a parte con lo stesso comando non-strict del
  server (`mkdocs build -f mkdocs_src/mkdocs.yml`, 34 s, exit 0); rilancio **da capo** con `--cov-clean-backend
  --cov-clean-backend-e2e` (via anche le parti `.coverage.*` del tentativo morto) e
  `LIBREFOLIO_TEST_STARTUP_TIMEOUT=900` (la manopola documentata in `_server.py:46-48` e `playwright.config.ts:76-84`;
  non tocca nessuna attesa dei test).
- Nota per chi prepara le corsie: in una worktree nuova conviene costruire frontend e MkDocs **prima** della run.

### 1.3 Andamento (tentativo 2)

| fase | esito |
|---|---|
| parallelo backend, 2 worker (services, utils, schemas, api…) | 10 760 ✓, 3 skip, 0 ✗ |
| consolidato backend | services 185 ✓ · api 68 ✓ · e2e 7 ✓ |
| consolidato frontend, 8 categorie (lotti da 8 spec con coverage JS) | Playwright 1 163 ✓ / 29 ✗ / 32 skip · vitest 10 760 ✓ |
| seriale: external, db | external FX 28 ✓ (21 skip voluti) · asset providers 33 ✓ (3 skip) · JustETF 11 ✓ · BRIM 705+324+169+145 ✓ · db 13/13 azioni ✓ |

Categorie: ✅ External, DB, Services, Utils, Schema, API, E2E, Broker, User, Portfolio · ❌ Utility, FX, Asset,
Transaction, AI Export.

Nessun rosso riconducibile a **T** (M-18 CP1, numeri e date nella lingua della UI) né a **I** (BrokerIcon, modale del
broker, pannello sicurezza: `front-broker` 51+2 ✓) né a **U** (vitest dei cataloghi tutti verdi).
`asset-detail.spec.ts:486` (nota del coordinatore, triato da I) in questa run è **verde**: nulla da classificare.

---

## 2. Tutti i rossi (29), per categoria e azione

Load = `uptime` 1/5/15 min. Per il primo giro è il campione più vicino all'ora del rosso (ora presa dall'mtime di
`error-context.md`; per AI Export gli artefatti sono andati persi, finestra 20:23–20:28). Rilancio = l'azione intera
da sola, `--workers 1`, stesso `--coverage` della run, nella corsia 6176.

| # | categoria · azione | test | errore nella run | primo giro: ora · load | rilancio da solo · load all'avvio | classe |
|---|---|---|---|---|---|---|
| 1 | front-ai-export · catalog | `ai-export/ai-export-catalog.spec.ts:83` «shows only FX V1 selections on FX Detail» | `setLanguage`: `language-selector-button` non trovato in 5 s (`fixtures/auth-helpers.ts:55`) | 20:23–20:28 · 112,5 / 92,3 / 79,6 | **4/4 ✓** · 14,7 / 17,4 / 21,1 | (a) |
| 2 | front-ai-export · contract | `ai-export/ai-export-contract.spec.ts:312` «the Dashboard enables AI Export only once the owned broker scope is known…» | idem | idem | **4/4 ✓** · 19,2 / 17,0 / 19,2 | (a) |
| 3 | front-ai-export · panel | `ai-export/ai-export-panel.spec.ts:106` «keeps outer trigger label stable while preparing» | idem | idem | **6/6 ✓** · 16,1 / 19,1 / 19,3 | (a) |
| 4 | front-ai-export · panel | `ai-export/ai-export-panel.spec.ts:266` «portals above Asset chart controls on desktop and mobile» | idem | idem | (stesso rilancio) | (a) |
| 5 | front-asset · asset-data-editor | `assets/asset-data-editor.spec.ts:92` «edit data button opens the editor panel» | `Tearing down "jsCoverage" exceeded the test timeout of 30000ms` (48,7 s) | 20:34:40 · ≈50–90 (20:28 112,5; 20:38 49,3 / 61,2 / 68,2) | **26/26 ✓** (`:92` in 15,2 s) · 15,8 / 24,1 / 24,3 | (a) |
| 6 | front-asset · asset-data-editor | `assets/asset-data-editor.spec.ts:100` «editor shows prices and events tabs» | teardown `jsCoverage` (47,4 s) | 20:34:39 · idem | (stesso rilancio; 13,0 s) | (a) |
| 7 | front-fx · fx-add-pair | `fx/fx-add-pair.spec.ts:40` «…early detail stale-error» | `expect(fx-detail-page).toBeVisible()` 3 s, elemento assente (spec `:219`) (20,1 s) | 21:01:55 · ≈55–63 (21:09 54,5 / 63,1 / 56,0) | **11/11 ✓** (14,1 s) · 24,4 / 29,8 / 27,7 | (a) |
| 8 | front-fx · fx-add-pair | `fx/fx-add-pair.spec.ts:40` «…early detail refresh-error» | idem (20,4 s) | 21:01:56 · idem | (stesso rilancio; 15,7 s) | (a) |
| 9 | front-fx · fx-add-pair | `fx/fx-add-pair.spec.ts:334` «can open add pair modal» | teardown `jsCoverage` (44,9 s) | 21:02:44 · idem | (stesso rilancio; 14,5 s) | (a) |
| 10 | front-fx · fx-add-pair | `fx/fx-add-pair.spec.ts:343` «modal has two currency selects» | teardown `jsCoverage` (45,2 s) | 21:02:44 · idem | (stesso rilancio; 12,0 s) | (a) |
| 11 | front-fx · fx-bulk | `fx/fx-bulk.spec.ts:51` «list view renders selectable rows and no toolbar until something is picked» | teardown `jsCoverage` (42,8 s) | 21:04:12 · idem | **7/7 ✓** (11,2 s) · 9,6 / 14,4 / 18,3 | (a) |
| 12 | front-fx · fx-bulk | `fx/fx-bulk.spec.ts:114` «clearing the selection from the toolbar hides it» | teardown `jsCoverage` (42,8 s) | 21:05:44 · idem | (stesso rilancio; 10,9 s) | (a) |
| 13 | front-fx · fx-bulk | `fx/fx-bulk.spec.ts:147` «the second filter narrows the pairs and clearing the first promotes the second» | teardown `jsCoverage` (46,3 s) | 21:06:08 · idem | (stesso rilancio; 11,4 s) | (a) |
| 14 | front-fx · fx-settings | `fx/fx-chart-settings.spec.ts:24` «can open global chart settings modal» | teardown `jsCoverage` (43,6 s) | 21:06:30 · idem | **3/3 ✓** (11,6 s) · 11,1 / 9,6 / 14,0 | (a) |
| 15 | front-fx · fx-settings | `fx/fx-chart-settings.spec.ts:62` «preview canvas is rendered with signals» | teardown `jsCoverage` (40,9 s) | 21:07:14 · idem | (stesso rilancio; 11,5 s) | (a) |
| 16 | front-fx · fx-csv-import | `fx/fx-csv-import.spec.ts:82` «initial header matches pair direction» | teardown `jsCoverage` (41,0 s) | 21:07:57 · idem | **21/21 ✓** (10,9 s) · 8,9 / 10,0 / 12,9 | (a) |
| 17 | front-fx · fx-csv-import | `fx/fx-csv-import.spec.ts:95` «swap button updates header and currencies without errors» | teardown `jsCoverage` (39,9 s) | 21:08:18 · idem | (stesso rilancio; 10,9 s) | (a) |
| 18 | front-transaction · tx-commit-all-types | `transactions/tx-commit-all-types.spec.ts:391` «DIVIDEND create → commit» | teardown `jsCoverage` (45,4 s) | 22:12:03 · ≈45–50 (22:09 44,9 / 34,1 / 37,1; 22:19 45,2 / 50,0 / 46,9) | **19/19 ✓** (13,2 s) · 11,1 / 11,4 / 12,6 | (a) |
| 19 | front-transaction · tx-commit-all-types | `…:395` «INTEREST create → commit» | teardown `jsCoverage` (45,7 s) | 22:12:03 · idem | (stesso rilancio; 11,9 s) | (a) |
| 20 | front-transaction · tx-commit-all-types | `…:399` «FEE create → commit» | teardown `jsCoverage` (45,2 s) | 22:12:50 · idem | (stesso rilancio; 18,7 s) | (a) |
| 21 | front-transaction · tx-commit-all-types | `…:403` «TAX create → commit» | teardown `jsCoverage` (44,8 s) | 22:12:50 · idem | (stesso rilancio; 19,2 s) | (a) |
| 22 | front-transaction · tx-ca-contract | `transactions/tx-import-ca-contract.spec.ts:192` «CAC-001: notices are rendered by severity, with their evidence readable» | `locator.waitFor`: `tx-table` non visibile in 10 s (`goToTransactions`, spec `:131`) (50,9 s) | 22:25:49 · 50,2 / 44,5 / 44,8 | **12/12 ✓** (18,7 s) · 21,3 / 19,2 / 22,7 | (a) |
| 23 | front-utility · auth | `auth.spec.ts:21` «successful login redirects to dashboard» | `toHaveURL(/dashboard/)` 3 s: ricevuto `http://localhost:6176/`, pagina «Loading...» | 23:09:32 · 44,6 / 56,0 / 48,1 (picco 125 alle 23:05) | **29/29 ✓** · 15,6 / 21,7 / 24,9 | (a) |
| 24 | front-utility · auth | `auth.spec.ts:44` «admin can login» | idem | 23:09:43 · idem | (stesso rilancio) | (a) |
| 25 | front-utility · auth | `auth.spec.ts:379` «1: canonical seeded user lands on the real shell and is never forced through welcome» | idem | 23:10:12 · 43,9 / 54,9 / 48,0 | (stesso rilancio) | (a) |
| 26 | front-utility · auth | `auth.spec.ts:427` «3a: completing welcome is one atomic request; refresh and next login do not re-force it» | `welcome-shell` non trovato in 3 s, pagina «Loading...» | 23:10:42 · 41,9 / 53,4 / 47,7 | (stesso rilancio) | (a) |
| 27 | front-utility · auth | `auth.spec.ts:501` «3b: permanently skipping welcome survives a refresh and the next login» | idem | 23:10:43 · idem | (stesso rilancio) | (a) |
| 28 | front-utility · toolbar-width-sweep | `layout/toolbar-width-sweep.spec.ts:873` «assetDetail › es: 1700 → 320 px…» | 4 larghezze in violazione: `denseRow`, barra 852–864 px, fino a **+16,8 px** a vw 1190 («Exportación IA Editar S…») | 23:22:06 · **18,2** / 32,1 / 44,1 | **✗ identico al pixel**, con coverage · 14,7 / 23,1 / 27,0; e **senza coverage** (build debug non strumentata) · 16,4 / 21,4 / 18,8 | **(e)** |
| 29 | front-utility · toolbar-width-sweep | `layout/toolbar-width-sweep.spec.ts:873` «dashboard › es: 1700 → 320 px…» | 3 larghezze: `denseRow`, barra 952–962 px, fino a **+16,0 px** a vw 1290 («Exportación IA Actualiz…») | 23:22:55 · **24,0** / 32,3 / 43,8 | **✗ identico al pixel**, in entrambi i rilanci | **(e)** |

---

## 3. Triage per gruppo, con le prove

Metodo: skill `test-triage` — prima i log e gli artefatti della run (copiati in `/tmp` prima che la categoria
successiva cancellasse `test-results/`), poi i rilanci da soli. Nessun rosso è stato rilanciato «alla cieca» né
chiamato flaky.

### 3.1 (e) Difetto del prodotto — `toolbar-width-sweep`, spagnolo, Asset Detail e Dashboard (2 rossi)

- **Deterministico**: rifallisce da solo a load 15 con **gli stessi numeri** della run (assetDetail: 1200/1190/930/920
  px, +6,8/+16,8/+4,8/+14,8; dashboard: 1300/1290/1020, +6,0/+16,0/+14,0). FR e IT verdi, così le altre barre in ES
  (`brokerDetail`…). Rifallisce identico anche **senza coverage**, sulla build debug non strumentata (0 chunk con
  `__coverage__`): la strumentazione non c'entra. Tre misure, stessi numeri: run 23:22 (load 18), rilancio con
  coverage 00:10 (load 15), rilancio senza 01:57 (load 16).
- **Era verde prima**: K lo ha chiuso **15/15** il 07/10 (step 18.7, corsia 6155), prima del cambio di termine.
- **Causa**: `7c66234a7` «fix(i18n): apply the developer's term choices» (M, 11/10 22:27, treno 40) porta
  `frontend/src/lib/i18n/es.json:65,1642,1955` da «Exportar IA» a **«Exportación IA»** (+3 caratteri). Le soglie della
  barra erano state calibrate prima, il 30/09 (`3e5313d3e` «fix(ui): recalibrate the five top toolbars»):
  - `frontend/src/routes/(app)/assets/[id]/+page.svelte:2773` → `denseRow: 850`, ma in `denseRow` il contenuto della
    barra misura **868,8 px** (barra + sforamento, costante su tutte e quattro le larghezze rosse);
  - `frontend/src/routes/(app)/dashboard/+page.svelte:829` → `denseRow: 950`, contenuto **968 px**.
- **Effetto utente**: in spagnolo, in quelle fasce di larghezza, il gruppo «Exportación IA / Editar S… / Actualiz…»
  esce dalla barra di 5–17 px.
- **Proprietario probabile**: **M** (il cambio di termine è suo); la cura è una ricalibrazione delle due soglie
  `denseRow` (lavoro di UI, eventualmente con **I**) oppure un'etichetta più corta: decisione del developer, perché il
  termine è una sua scelta.

### 3.2 (a) Carico — il teardown di `jsCoverage` consuma il budget del test (15 rossi)

- **Errore**: `Tearing down "jsCoverage" exceeded the test timeout of 30000ms`, durate 40–49 s, tutte sotto carico
  45–112. Rossi in finestre contigue (FX 21:02–21:08, transazioni 22:12), cioè durante picchi, non in un'area di
  prodotto.
- **Meccanismo** (`frontend/e2e/fixtures/playwright.ts:284-333`): il fixture è `{scope: 'test', auto: true}` **senza
  `timeout` proprio**, quindi la raccolta dopo il test sta dentro i 30 s del test (`playwright.config.ts:108`). Raccoglie
  `window.__coverage__` con `page.evaluate`, lo serializza e lo scrive: **≈17 MB di JSON per test** (17 GB di
  `coverage-js/e2e-raw` per 1 005 test). Sotto carico questo costa decine di secondi.
- **Rilancio**, con la stessa coverage della run (build strumentata ricostruita e raccolta JS attiva: «Generated
  frontend/coverage-js/e2e/ (N test)» con N = tutti i test di ogni azione): **tutti i 15 verdi**, in **11–19 s**
  ciascuno, teardown compreso, contro 40–49 s nella run. Anche i compagni verdi di spec erano lenti nella run
  (`asset-data-editor` fino a 36 s): era la macchina, non quei test.
- **Esiste solo con `--coverage js`**: senza coverage il fixture è un no-op.
- **Proprietario probabile**: **V** (harness E2E). Idea, non applicata: un `timeout` dedicato al fixture, così la
  raccolta non pesa sul budget del test e un test lento resta distinguibile da una raccolta lenta.

### 3.3 (a) Carico — `login()` ritorna prima che l'app sia partita (9 rossi: auth ×5, AI Export ×4)

- **Errori**: dopo `login()`, `toHaveURL(/dashboard/)` con il default di 3 s (`auth.spec.ts:23,46,381`),
  `welcome-shell` visibile in 3 s (`auth.spec.ts:431,505`), oppure `setLanguage` che aspetta il selettore della
  lingua 5 s (`fixtures/auth-helpers.ts:55`, chiamato da `ai-export/helpers.ts:37`).
- **Cosa vedeva il browser**: per auth, URL ancora `/` e pagina «Loading...» (snapshot dell'`error-context.md`): il
  bootstrap dopo il login non era finito. I 5 di auth cadono **nei primi due minuti del lotto** (test 1–23 di 139:
  avvio a freddo del browser sulla build strumentata), 4–5 min dopo un picco a 125.
- **Perché**: `login()` (`fixtures/auth-helpers.ts:7-39`) aspetta solo che il form sparisca e `domcontentloaded`
  (`:37-38`), non che l'app abbia redirezionato. Con il backend strumentato e il load 45–112, `GET /auth/me` e
  l'onboarding superano facilmente i 3–5 s (oltre i 5 s l'app mostra apposta il pannello «server lento»,
  `(app)/+layout.svelte:97`, K-19 `93fd33702`).
- **Precedente**: K, step 18.5 del 07/10 (`LibreFolio_developer_journal/Release_2/phases/25_taxonomySelect/plan-phase00TaxonomySelectStep18CoverageTriage.prompt.md`),
  ha diagnosticato lo stesso schema («`login()` ritorna prima del redirect… `setLanguage` aspetta il selettore solo
  5 s») e lo ha corretto **solo** in `toolbar-width-sweep.spec.ts`. L'helper condiviso è rimasto com'era.
- **Rilancio**: auth 29/29, catalog 4/4, contract 4/4, panel 6/6, tutti verdi a load 15–19.
- **Verdetto `test-triage`**: assunzione d'orologio (§2 della skill) sotto il rosso operativo (a).
  **Proprietario probabile: V**; la cura naturale è nell'helper (`login()` che aspetta la condizione vera: URL fuori da
  `/` e shell pronta), che rinforza 9 rossi in un colpo solo.

### 3.4 (a) Carico — dettaglio FX dopo il clic sulla card (2 rossi)

- `fx/fx-add-pair.spec.ts:219`: dopo `click()` sulla card la spec aspetta `fx-detail-page` con il default di 3 s; la
  navigazione SPA sotto carico non ci sta.
- **Rilancio**: `fx-add-pair` 11/11 verde (le due varianti in 14,1 e 15,7 s, contro 20,1 e 20,4 s spesi nella run
  per arrivare al rosso). Stesso schema di §3.3: un budget di 3 s dopo una navigazione. **Proprietario probabile: V.**

### 3.5 (a) Carico — tabella delle transazioni oltre i 10 s (1 rosso)

- `transactions/tx-import-ca-contract.spec.ts:131` (`goToTransactions`): `tx-table` visibile in 10 s. Lo snapshot al
  momento del rosso mostra **la tabella già resa** (intestazioni, contatore «Transactions 91»): è arrivata appena dopo
  la scadenza.
- **Rilancio**: `tx-ca-contract` 12/12 verde, CAC-001 in 18,7 s (50,9 s nella run). **Proprietario probabile: V.**

### 3.6 Osservazioni sul runner (non sono rossi)

- **Worktree fresca + carico**: il primo avvio del backend condiviso costruisce frontend e MkDocs dentro i 300 s di
  `STARTUP_TIMEOUT` (§1.2). Costruirli prima della run evita il falso rosso d'ambiente.
- **Artefatti Playwright**: `test-results/` si svuota a ogni invocazione, quindi `error-context.md` e screenshot dei
  rossi di una categoria spariscono alla categoria successiva. Li ho salvati con una copia ogni 20 s; quelli di AI
  Export (la prima categoria) erano già persi.
- **Doppia build a ogni invocazione con coverage JS**: `dev.py server --test` forza `debug_mode = True`
  (`dev.py:197`, `:228`), quindi una build di produzione strumentata è per lui «del modo sbagliato» e la ricostruisce
  in debug, cancellando build e marker (output in DEVNULL, `_server.py:274`); poi `_ensure_frontend_build`
  (`_frontend_common.py:71-74`) ricostruisce la strumentata. Nella run completa non costa nulla (il server parte una
  volta, prima); nei rilanci di una singola azione costa una build in più per invocazione (parte dei 5–7 min di
  overhead che ho visto per azione). Prove: ogni rilancio con coverage stampa «Building the frontend instrumented»
  anche se il precedente aveva lasciato build e marker strumentati; dopo il rilancio senza coverage
  `frontend/build/.build-debug` = 1 alle 01:58 e il runner dice «Frontend build is up to date».

---

## 4. Coverage

### 4.1 Backend (Python, `branch = true`)

Categorie misurate: **tutte** (`all`: external, db, services, utils, schemas, api, e2e + backend toccato dai 21 lotti
Playwright). Dati della run congelati in `/tmp/libreFolio_R_cov_snapshot/`.

| base dati | statement | mancanti | rami | parziali | % coverage.py (righe+archi) | % righe | % rami |
|---|---:|---:|---:|---:|---:|---:|---:|
| backend da test (`.coverage_data/backend`) | 53 896 | 3 486 | 16 252 | 2 299 | **91,50 %** | 93,53 % | 84,77 % |
| backend da E2E (`.coverage_data/frontend`) | 53 896 | 33 921 | 16 252 | 378 | 29,32 % | 37,06 % | 3,63 % |
| combinata (`.coverage`, `htmlcov/`) | 53 896 | 3 485 | 16 252 | 2 298 | **91,51 %** | 93,53 % | 84,78 % |

- Sentinella del cablaggio dei figli: `services/risk/quant/spawn_worker.py` all'**87,64 %** (non 0 %): il combine e i
  processi `spawn` sono misurati.

**Confronto** (le cifre vecchie non sono sempre della stessa formula: vedi
`LibreFolio_devWiki/wiki/problems/coverage-percent-mixed-lines-and-branches.md`):

| misura | quando | backend | E2E→backend | fonte |
|---|---|---|---|---|
| questa run | 12–13/10 | **91,51 %** (righe 93,53, rami 84,78) su 53 896 stmt | 29,32 % | qui |
| run del 07/10 (K) | 07/10 | 36,8 % — **non confrontabile**: falsata dalla corsa del `coverage combine`, corretta l'08/10 (`751f496b3`) | — | `phases/28_fxDashboardSync/plan-phase00CoverageCombineRace.prompt.md:25` |
| P1-18 | 03/09 | 91 % | 29 % | `phases/08_newCleanAndDocumentation_audit/17_stabilizzazione.md:151-153` |
| wiki | 31/08 | righe 92,39 %, rami 82,64 % | — | `wiki/concepts/coverage-rate-vs-volume.md:74` |
| skill testing-backend | inizio 09 | 91,36 % su 37 336 stmt | — | `testing-backend/SKILL.md` |

Lettura: il denominatore è cresciuto del **44 %** (37 336 → 53 896 statement) e la copertura è salita
(+0,5 pp sulla cifra P1-18; righe +1,1 pp e rami +2,1 pp sulla misura del 31/08). Questa è la **prima misura completa
valida dopo la correzione del combine**.

**Moduli più scoperti** (combinata):

| mancanti | % | file |
|---:|---:|---|
| 97 / 1 542 | 90,08 | `backend/app/schemas/pac_allocator.py` |
| 95 / 950 | 84,22 | `backend/app/services/pac_allocator/models.py` |
| 88 / 1 047 | 86,80 | `backend/app/schemas/risk.py` |
| 73 / 286 | **75,00** | `backend/app/api/v1/assets.py` (73,9 % nel report 17, `08_…/17_stabilizzazione.md`: praticamente fermo) |
| 54 / 801 | 91,76 | `backend/app/services/brim_provider.py` |
| 54 / 1 232 | 93,68 | `backend/app/services/pac_allocator/evaluator.py` |
| 53 / 714 | 90,13 | `backend/app/services/pac_allocator/normalize.py` |
| 50 / 597 | 90,18 | `backend/app/services/fx.py` |
| 49 / 214 | 74,45 | `backend/app/services/brim_providers/broker_cointracking/plugin.py` |
| 47 / 394 | 88,80 | `backend/app/api/v1/fx.py` |

Percentuali più basse (≥ 30 stmt): `services/scheduler/scheduler.py` 60,18 %, `brim_providers/broker_cryptocom` 69,86 %,
`fx_providers/fed/plugin.py` 70,80 %, `broker_cointracking` 74,45 %, `api/v1/assets.py` 75,00 %, `services/tools/resources.py`
75,50 %. Per pacchetto, i più bassi: `fx_providers` 88,1 % righe / 73,8 % rami, `brim_providers` 88,4 % / 79,7 %
(907 righe mancanti su 7 809: la quota più grossa), `api/v1` 89,6 % / 83,5 %, `services/tools` 90,2 % / 81,5 %.

### 4.2 Frontend (JS/Svelte, istanbul, build strumentata)

| livello | file | statement | rami | funzioni | righe* |
|---|---:|---:|---:|---:|---:|
| unit (vitest) | 641 | 57,15 % (33 706 / 58 977) | 49,76 % | 59,73 % | 58,81 % |
| E2E (Playwright, 1 005 test raccolti) | 609 | 63,10 % (35 595 / 56 408) | 49,90 % | 62,10 % | 65,83 % |
| **combinata** | 641 | **71,24 %** (47 522 / 66 711) | **62,82 %** (27 082 / 43 113) | 72,88 % | 78,32 % |

\* righe con almeno uno statement istanbul (stessa regola di `istanbul-lib-coverage`).

- **Senza `src/lib/features/tools`**: 78,42 % statement, 67,64 % rami.
- **Il planner del PAC** (`src/lib/features/tools/pac-allocator/planner/`, nato il 25/09 con `0210f9848`): 7 008
  statement al **14,01 %** (unit 16,97 %, E2E 5,78 %); 47 dei 56 file allo 0 % sono suoi. Nessuna spec E2E lo
  esercita: `layout/document-title.spec.ts` apre la pagina di un tool solo per il titolo, e `gallery.spec.ts`
  (`e2e/fixtures/galleryPac.ts`), l'unica che lo percorre, è esclusa dalla suite per scelta
  (`scripts/test_runner/_inventory.py:54-55`). Lacuna di test, **proprietario probabile V**.
  Fuori dal planner, allo 0 %:
  `features/tools/ToolDiagnosticsPanel.svelte` (185), `features/tools/components/ToolExecutionMetrics.svelte` (44),
  `routes/+error.svelte` (37), `components/risk/levels/SimulationProvenance.svelte` (29),
  `components/files/FileSetBadges.svelte` (20), `components/assets/assetEditData.ts` (14), `hooks.server.ts` (14).
- **File con più statement scoperti**: `ImportWizardModal.svelte` 1 241 (54,9 %), `routes/(app)/assets/[id]/+page.svelte`
  549 (68,5 %), `TransactionBulkModal.svelte` 407 (74,5 %), `TransactionFormModal.svelte` 327 (69,7 %),
  `RiskAnalysisPanel.svelte` 284 (67,4 %, rami 39,8 %), `routes/(app)/assets/+page.svelte` 284 (61,0 %),
  `LotComparisonChart.svelte` 277 (46,8 %), `routes/(app)/fx/[pair]/+page.svelte` 252 (69,2 %).
- **Per area**: `features/tools` 6 637 scoperti (22,5 %), `components/transactions` 3 101 (66,4 %),
  `routes/(app)` 2 051 (66,3 %), `components/brokers` 1 176 (74,4 %), `components/ui` 1 108 (81,8 %).

**Confronto**: 03/09 (P1-18) JS **72,3 %** statement → oggi **71,24 %** (−1,1 pp) con il denominatore cresciuto; la
differenza è tutta nel planner del PAC, nato dopo. Il 31/08 (wiki) era 69,84 % statement / 53,75 % rami, ma con V8 +
monocart, che non vedeva i rami dei template Svelte: i rami di oggi (62,82 %) non sono confrontabili con quelli.

---

## 5. Prove, stato finale, pulizia

| cosa | dove |
|---|---|
| log completo della run | `/tmp/libreFolio_R_full_run.log` (tentativo 1: `/tmp/libreFolio_R_full_run_attempt1.log`) |
| log per unità della run | `/tmp/libreFolio_R_testLog_fullrun/` (copia di `.testLog`) |
| artefatti Playwright dei rossi (error-context, screenshot) | `/tmp/libreFolio_R_test_results/` (persi solo quelli di AI Export, cancellati dalla categoria successiva prima che partisse la copia) |
| load ogni 30 s (22:20 → 00:02) | `/tmp/libreFolio_R_load.log` |
| rilanci (log, artefatti, riepilogo) | `/tmp/libreFolio_R_rerun/` (`summary.txt`) |
| coverage della run, congelata | `/tmp/libreFolio_R_cov_snapshot/` (+ JSON: `/tmp/libreFolio_R_cov_{backend,e2e,combined}.json`; sintesi `/tmp/libreFolio_R_covsum_py.txt`, `/tmp/libreFolio_R_covsum_js.txt`) |

**Stato finale** (13/10, 02:08):

- nessun server acceso, **porta 6176 libera**, nessun processo della corsia;
- worktree su `a5653f9ef`, **nessun file tracciato modificato** (`git status` vuoto);
- nella worktree restano solo artefatti ignorati: `node_modules` (dal `npm ci`), la build del frontend in modalità
  **debug non strumentata** (nessuna build strumentata lasciata in giro), il sito MkDocs, `.testLog/` della run e i
  report di coverage **della run completa**, ripristinati dalla copia congelata dopo i rilanci (che li avevano
  sovrascritti): `./dev.py test coverage show combined` e `show js` mostrano le cifre di questo rapporto;
- disco: la run aveva prodotto 17 GB di `frontend/coverage-js/e2e-raw` con il disco al 97 %; i rilanci con coverage
  li hanno cancellati come da progetto e non ne restano: liberi 18 GiB al termine.

**Rilanci**: 12 azioni, una alla volta, 00:09 → 01:56, `--workers 1`, `--coverage` come la run
(`/tmp/libreFolio_R_rerun.sh`), più lo sweep senza coverage (01:57 → 02:03).
