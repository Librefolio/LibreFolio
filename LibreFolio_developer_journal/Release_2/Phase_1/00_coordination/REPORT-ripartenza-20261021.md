# LibreFolio: censimento attività pending e ripartenza (stato al 20/10/2026 ~14:36 CEST)

Fonti: `copilot-enel/session-store.db`, `data.db`, `session-state/928ffa97…/files/`, `git` su `./LibreFolio`.
**Nota importante:** il lavoro non si è fermato al 19/10. Dopo la pausa generale (19/10 18:12) il coordinatore ha ripreso il 20/10 alle 08:44 e le sessioni hanno girato fino alle 12:36 UTC (14:36 locali). Gli ultimi checkpoint strutturati (tabella `checkpoints`) sono più vecchi dei turni: per lo stato reale valgono gli ultimi turni.

## A. Sessioni

### Release 1.3 planning (coordinatore, `928ffa97…`, 3519 turni, 17 checkpoint)
Regole in vigore: ogni decisione di prodotto è una domanda al developer; ogni lotto parte con un'analisi e si implementa solo dopo un GO; massimo 2 slot pesanti; prove leggere solo con load < 50. I figli non fanno git: committa e fa merge solo il coordinatore ("treni" di integrazione, oggi arrivati al treno 4).
Documenti chiave: `RESUME-pausa-20261019.md`, `risposte-resoconto-20261019.md` (decisioni §36–§51), `litestream-domande-20261019.md`, `issue26-danske-messaggio-20261019.md`, `nightly-fix-dentro-container.md`, `backup-architettura-cloud-20261020.md`, `l3-litestream-ricerca-20261020.md`.
Decisioni del developer aperte: Litestream (a) in 1.3 o (b) dopo (raccomandato b); frasi del prompt E-AI503 e E-23; D-W85-1/2/4; N78-1; MF-P1b (2.496 punti None→valore); E-25 approvata, E-26 e traduzioni `getting-started` da portare al developer; domande N64; D-P4 (MF, campionamento storico lungo); TC-23.

### I 10 figli (stato dagli ultimi turni del 20/10)
| WS | Fatto / entrato | In corso o in attesa |
|---|---|---|
| **A** account | N69a/N69b, A-61, H-61 `admin_setup_status` (checkpoint `64b8b9fa3`,`bdb083782`,`50d1f29c6`, ancora **fuori da dev**) | A-62 (tooltip menu tradotto, rossi in scrittura), poi A-CL1 (analisi bug changelog), N69c/d; segnale `data-security-checks`. Bloccato su: D1–D11 per N69, politica CSP di H |
| **B** backup | B-8, B-50, B-53/54/55 (`1fd559a26`, sulla sua branch, già in dev secondo l'ultimo checkpoint del coordinatore) | FROZEN, albero pulito. Restano B7 Litestream (D1–D10), B9 arm64, BZ parte 2, B5b galleria, B-33, B-56 (dopo 1.3) |
| **E** email | E-AI503, N62, E-20 (in lavorazione), gallery settings/email | Branch ahead 2 (`b02611402`, `a7c7de18d`); traduzione voce X in it/fr/es + `translate-stamp` **sporca nel worktree (9 file)**; E-25 GO (rossi prima), E-26, E-24, E-7, E-23 |
| **H** piattaforma | H-60 (review), N70 | H-61 pannello hosting: CP1 pronto (R1 da applicare da `dry/`), CP2 (ticket Ed25519 L2) dopo; aggiungere `platform.hosting_panel` a `frontend/e2e/fixtures/gallerySecurity.ts` (18ª voce, permesso di G). Branch ahead 5. 3 test CP2 non tracciati |
| **J** numeri | J-57 (cure v1/v2), H-60 analisi | J-57 v3 con `files/j/j57c/slot_part2.sh`; L1b con base aggiornata (GO, rossi sulla parità di L1a); Gantt §29, TC-23, R1 dipende da X-Q1; CP-8/9b/9c in finestra tranquilla |
| **MF** | P1b, P2, P3 (`e71012c67`, in dev treno 4) | **P4** (segmenti del motore): analisi inviata, aspetta GO + risposta D-P4; poi E2/P3, N78 |
| **W** import | B-52 (Fineco ok), W-B88, W-B89, **B-51 fatto** (CHECKPOINT READY in attesa di commit) | Danske cure, B-87/W-B90/91, Q-N78-1, K3a/b/c |
| **X** plugin | X-R45b-ui, N61-form (cura pronta, non applicata `files/checks/n61form_code.py`) | Aspetta commit di X-R45b-ui; N64 (aspetta risposte developer), P3 step function per MF, Q1–Q3/S1, X-R48b sospesa (N68). Branch pulita a `6011a9ff0` ma 1 file sporco (piano 03) |
| **Y** cruscotto | Y-N65, Z-29d-0, Y-38 | **Y-39a** codice fatto e verde (375/375 + 1044/1044), serve ok righe runner + slot E2E ~25 min poi CHECKPOINT; Y-39b (DV: LineChart `colorByBaseline`, non toccare `chartInitOptions`), Y-40, Y-41/42. **Worktree con 11 file sporchi: è il lavoro più a rischio** |
| **Z** sospensione | Z-29a-f (`5bbadda95`), Z-32d, Z-39 | Z-29s-a (campionamento backend): GO dato, rossi in scrittura (6 file sporchi tra cui `signal_sampling_cases.v1.json`); Z-29b aspetta Y-39 |

Dipendenze: **X ↔ Y**: modulo condiviso `lib/charts/chartSignalRendering.ts` (di Y, adottato da X; gate `signalRendering.gate.test.ts` con lista che può solo accorciarsi; le due pagine di dettaglio di X sono copie note, Y-42). **E ↔ G**: stampa delle traduzioni della gallery; voce di X in it/fr/es tradotta da E. **A ↔ H ↔ G**: la fixture `gallerySecurity.ts` (17 check `ok`, H-61 aggiunge `platform.hosting_panel`; A ha verificato le 17 voci). **MF ↔ X ↔ J**: step function FX per P3, L1a/L1b.

### UI color analysis (`aec04834…`, 1223 turni, 9 checkpoint)
- **T**: T2 entrato (`ccc2a4141`), R3-c/TC-20 chiuso; fermo, branch pulita. Resta TC-23 (→1.3), `data-group-key`/`aria-busy` come voci TC.
- **DV**: DV-14 (DPR, `chartInitOptions`) entrato `1cb7097d1`; fermo. Prossimo: DV-11 (Lab e `chartCategories` su ruoli `--lf-cat-*`) oppure serie `chartTheme` su ruoli; condizioni F-2 per `LineChart` date a Y.
- **G**: **G-28 fatto** (`gallerySecurity.ts` fixture 17 check ok, commit `a288a181f`, entrato come `b844f83f2` = HEAD di dev); fermo. Ha anche catturato `settings/email` nelle 3 gallerie.
- Aperto: il coordinatore colori aspetta la decisione del developer su interruttori (109 classi → `bg-lf-checked`) e serie grafici (145 letterali), o risposte della designer (Liquidity verde, flussi neutri, serie di crescita, posizione pallino). Poi: DV-11, 2 `#a855f7` residui, TC-21, G-22..G-27, B6 (rimuovere remap legacy `app.css`/`--theme-*` quando le 590 classi sono sparite), fine programma (docs, CHANGELOG unico, skill, archivio piani).
- Sessioni L, R, TR, BK, IW, AF, IM: archiviate il 15–17/10, nessun pending.

> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_

## B. Artifact di riferimento
- Piani per workstream: `LibreFolio/LibreFolio_developer_journal/Release_2/Phase_1/{01_platform,02_accounts,03_pluginsAssets,04_importTransactions,05_numbersAnalysis,06_sleepWake,07_backupDocker,08_email,09_dashboardCharts,10_colorSystem,11_financialMath}/plan-*.prompt.md` e `Phase_0/BACKLOG_POST_1.2.md` (il backlog per sezione di workstream; è dove i figli segnano lotti e decisioni). Nei worktree molti sono **sporchi** (aggiornamenti non committati): vedi sezione C.
- Coordinatore: `copilot-enel/session-state/928ffa97-…/files/` (RESUME, risposte-resoconto §36–§51 con il `▶ RIPARTI DA QUI`, scripts `gate_*.sh`, `v4_on_copy.sh`, squash SQL, `PROSSIMI_LAVORI.md` nel repo).
- Cartelle `files/` dei figli (patch e script pronti non applicati): H `dry/`, `dry2/`; J `files/j/j57c/slot_part2.sh`; X `files/checks/n61form_code.py`; W `files/scripts/b52_cure.py`; B `files/b50-wip/`; Y `files/scripts/y39a_vitest_batch.sh`, `y39a_e2e.sh`; Z `files/z29s-draft/`.
- Screenshot di riferimento: gallery 18/10 (trio prima/dopo in `LibreFolio_subRepo/LibreFolio_visual_review/sheets/r3-2026-10-18/`), `session-state/<uuid>/files/transcript-images/` per i mock del programma colori.

## C. Git
- `./LibreFolio`: `dev_release2` = `b844f83f2` (20/10 14:15), pulito (solo `.claude/` non tracciato), **allineato con `origin/dev_release2`** secondo il tracking locale (il remote è `git@github.com:Librefolio/LibreFolio.git`; non ho fatto fetch).
- Ultimi 5: `b844f83f2` merge G-28 · `a288a181f` test(gallery) fixture · `a820bd4dd` merge G N69 · `e32b53473` docs journal G · `15fa228ef` changelog train 4.
- 32 branch locali. **Con commit non in dev**: `e-alfy-a-account-e-accessi` +3 (`50d1f29c6`, 189 indietro), `e-alfy-e-email` +2 (`a7c7de18d`, 52 indietro), `e-alfy-h-piattaforma` +5 (`f9f417bfa`, 179 indietro), `e-alfy-j-numeri-e-analisi` +2 (`7321c8b9b`, 24 indietro), `preview-colori-1015` +2 (obsoleto, 2615 indietro). Tutti gli altri `e-alfy-*` sono ahead 0 (già in dev o solo indietro): MF (22 indietro), Z (102), B (199), X (192), Y (200), W (187), T (175), DV (147), G (0).
- Worktree: i 14 `.git` puntano a `/Users/ea_enel/...`, ma `LibreFolio/.git/worktrees/<nome>` esiste per tutti, quindi **`git worktree repair` basta** (nessuna perdita).
- **Lavoro non committato nei worktree** (conteggio file sporchi): Y-39a 11 (codice vero: `chartSignalRendering.ts`, `ChartSettingsModal.svelte`, pagine assets/fx…), E 9 (traduzioni gallery + stamp), Z 6 (rossi Z-29s-a), H 3 (test pannello), J 2, X 1, T 1, A 1, MF 1 (solo piani/journal). I worktree W, B, G, DV sono puliti.

## D. Roadmap di ripartenza
1. **Salvare subito**
   - Copiare/backup di `copilot-enel/` e dei 14 worktree sporchi (soprattutto Y-39a, Z-29s-a, E gallery) prima di qualsiasi operazione.
> _(parte del servizio gestito: nel repo privato `librefolio-cloud`)_
2. **Ripristinare i worktree su Linux**
   ```bash
   cd LibreFolio && git worktree repair ../LibreFolio-worktrees/*
   ```
   - Verifica `git worktree list` (niente più "prunable"). I path dei figli sono di `/Users/ea_enel/...` nei loro prompt e script: serve un `sed` o una variabile `WORKTREES`. Ricreare le corsie in `/tmp/librefolio-r13-*` con `db populate --force --clean` (le corsie sono sparite al riavvio), porte 6182–6189. Verificare `pipenv` (venv `LibreFolio-SAUMUTtc`) e `npm ci` per il frontend.
3. **Consolidare dev (ordine del coordinatore)**: committare i checkpoint pronti: Y-39a (dopo ok righe runner + slot E2E 25 min), B-51 di W, H-61 CP1, E-25/gallery traduzioni, A-62, J-57 v3. Poi merge reviewed: Z-29a, L1a/L1b, E-AI503, X-R45b-ui + N61-form, H-60, treno 4 già in dev (N69b, E-23, P3, J-67, E2b).
4. **Verifica ambiente** (dopo il repair): `./dev.py test all-backend --fresh-run` su HEAD, poi E2E mirati: front-transaction, front-asset, front-fx, front-utility settings, backup; `gate_b8.sh` (pronto, mai eseguito). Light checks solo con load < 50.
5. **Risposte del developer da raccogliere** (sbloccano molti lotti): Litestream a/b, E-AI503/E-23, D-W85, N78-1, MF-P1b, D-P4, N64 ×2, D1–D11 di N69, E-26, D-24, interruttori/serie grafici.
6. Rispondere al coordinatore cloud (ultimo messaggio del developer senza risposta) e sbloccare il ramo H-61 → API pannello → contratto per il coordinatore.
