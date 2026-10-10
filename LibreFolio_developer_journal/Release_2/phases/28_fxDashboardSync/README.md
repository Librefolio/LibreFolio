# 28_fxDashboardSync — i lotti del workstream N (06/10 – 09/10)

> **Stato (09/10): FINITA, archiviata.** Ogni piano è fatto e integrato in `dev_release2`, verificato su
> `3cceb4f90` con `git merge-base --is-ancestor`. I residui ancora veri sul codice di oggi sono rinviati in
> `Phase_0/38_postReleaseBacklog/README.md`, voci N-1 … N-9 (elenco sotto). Il nome della cartella viene dal primo
> lotto; poi il workstream N ha raccolto qui tutti i lotti successivi, uno per piano.

| Piano | Data | Lotto | Stato | Commit | Treno |
|---|---|---|---|---|---|
| [`plan-phase00FxDashboardSync.prompt.md`](plan-phase00FxDashboardSync.prompt.md) | 06/10 | FX nella Dashboard: sync dal banner (date mancanti ±7 giorni), storia completa alla creazione della coppia, solo le valute capo delle rotte nel menu, segno del KPI giornaliero | ✅ | `5c1b52612`, `f7134bb7f`, `929887ad8`, `b4bddc411` | sul ramo il 06/10 alle 17:44, prima del treno 2 |
| [`plan-phase00FxDashboardSyncStep2PageCache.prompt.md`](plan-phase00FxDashboardSyncStep2PageCache.prompt.md) | 06/10 – 07/10 | Cache della Dashboard: stale-while-revalidate (fase 1); tab Rischio sui soli broker posseduti (lotto 2); i rossi della coverage del 07/10 (AI Export dopo i broker, test FX) | ✅ fase 1 e lotti; fase 2 rinviata (N-1) | `cd1d42fb6`, `a3d2fbc3c`, `8baf74f29`; `af154d84d`; `3a83ad9c7`, `49d4ec8e0`, `c958f857c`; `a1a0a0b87`, `6a6429db7`, `bc3dc7bdb`, `fdb877bcc`, `9d1af831c` | 8; 8; 9; 10 |
| [`plan-phase00CoverageCombineRace.prompt.md`](plan-phase00CoverageCombineRace.prompt.md) | 08/10 | Il combine della coverage riceve la cartella, una cartella per run, il combine fallito rende rossa la passata, le parti vuote | ✅ | `751f496b3`, `230b2695d`, `029e00906`, `fc76cefa1` | 13 |
| [`plan-phase00DataQualityBannersNavCount.prompt.md`](plan-phase00DataQualityBannersNavCount.prompt.md) | 08/10 | Rosso del banner: il conteggio dei link `navigate_asset` limitato alla sua riga | ✅ | `ce892dd7c`, `5157b6762` | 15 |
| [`plan-phase00DefaultDisplayCurrency.prompt.md`](plan-phase00DefaultDisplayCurrency.prompt.md) | 08/10 | Le pagine partono dalla Default Currency dell'utente, non da quella dell'istanza | ✅ | `51d1a64db`, `4c214bc16`, `9ca9078cc` | 18 |
| [`plan-phase00FxAddPairNavigationWait.prompt.md`](plan-phase00FxAddPairNavigationWait.prompt.md) | 08/10 | Rosso di `fx-add-pair`: l'attesa della pagina FX via `goToFxPage` | ✅ | `49d6f5324`, `55019a641` | 19 |
| [`plan-phase00DbPathArgument.prompt.md`](plan-phase00DbPathArgument.prompt.md) | 09/10 | `dev.py db … [path]` rispetta il path; `db check` funziona | ✅ | `964f3427d`, `7ef4ea287`, `faa2b2120`, `0c953f841` | 23 |

## Residui rinviati (`Phase_0/38_postReleaseBacklog/README.md`)

| Voce | Titolo | Peso | Da |
|---|---|---|---|
| N-1 | «Mostra il vecchio, aggiorna in background» fuori dal portafoglio (fase 2 del principio del 06/10) | medio | Step 2, §3.1-quater |
| N-2 | Il riepilogo della coverage resta generico quando fallisce solo il combine | basso | CoverageCombineRace, passo 6 |
| N-3 | Una parte illeggibile per sempre rende rosse tutte le passate successive della stessa run | basso | CoverageCombineRace, passo 6 |
| N-4 | Un SIGTERM durante il salvataggio della coverage svuota la parte del figlio (`spawn_worker.stop`, `ProcessTree._signal`, coverage.py a monte) | basso | CoverageCombineRace, §4b |
| N-5 | Commenti superati dalla cache della fase 1 (`risk-lab.spec.ts`, `assets/+page.svelte`) | basso | Step 2, passo 10 |
| N-6 | Doc sviluppatore del frontend con quattro affermazioni false (`registries.md`, `frontend/index.md`) | basso | Step 2, passo 9 |
| N-7 | `cli_tools.en.md:8`: «i comandi del database funzionano con `exec`», non `upgrade`/`downgrade` | basso | DbPathArgument, passo 6 |
| N-8 | In Docker un `PORT` in `.env` fa controllare la porta sbagliata a `db upgrade` via `exec` | basso | DbPathArgument, passo 6 |
| N-9 | devWiki: il backward-fill FX illimitato trasforma i buchi interni in tassi stantii silenziosi | basso | step 1, §4 D6 e §11 |

Non sono residui, e quindi non sono rinviati:
- l'opzione C di D6, non scelta;
- E7, superato da §3.1-ter;
- le attese predefinite dopo le navigazioni interne di `fx-add-pair`, mai rosse;
- `#rolling-return`, già nel backlog del coordinator come D28.
