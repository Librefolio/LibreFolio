# Piano — fase 01, 05: J · Numeri e analisi (1.3.0)

> **Stato**: 🧊 J-0 consegnato (2026-10-14), FROZEN fino al commit del coordinatore; poi CP-1. Via libera
> **parziale**: solo J-0 e CP-1 (§0.2). Il resto aspetta le risposte del developer alle decisioni di prodotto (§3) e il
> via del coordinatore.
>
> - **Workstream J** · worktree `LibreFolio-worktrees/e-alfy-crispy-goggles` · ramo `e-alfy-j-numeri-e-analisi`
>   (rinominato dall'app all'avvio; prima `e-alfy-crispy-goggles`).
> - **Base**: `c9bb8f257643c0b770788033789425b41ba16715`. Il worktree è nato a `459131eb8` (piano della fase); il
>   coordinatore l'ha portato in fast-forward a `c9bb8f257` prima del via. In mezzo solo journal,
>   `scripts/visual_review/gallery_snapshot.sh` e `TODO_FUTURI.md`: nessun file del codice.
> - **Corsia**: `--test-port 6185 --data-dir /tmp/librefolio-r13-j`, con
>   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test …`; un comando alla volta; mai 6040 né
>   6041. Finestra della galleria del programma colori il 15/10 dalle 09:00 (~2 h, inizio e fine dal coordinatore):
>   in quelle ore niente `all-backend` né build pesanti nella corsia.
> - **Coordinatore**: «Release 1.3 planning», `928ffa97-f0c3-4975-a442-3de0c2c20fc7`.
> - **Fonti**:
>   - il [piano generale della fase](../plan-phase01Release13.prompt.md): §3, §4 «J», §6 (Git, «Forma comune del
>     riordino» C1–C7, superfici condivise, regole di ogni lotto, «Taglio dichiarato»), §7, §9, §10 n. 14;
>   - le [decisioni delle analisi](../decisioni-analisi-20261014.md), punti 26–30 (le mie);
>   - il [piano 43](../../Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md): §2, §3, §4, §5,
>     §7.1–7.5, §8, P2;
>   - il [piano 53](../../Phase_0/53_pacTests/plan-phase00PacTests.prompt.md), §5 (D1–D4); il
>     [README della 13](../../Phase_0/13_pacAllocator/implementation/README.md), «Gate del PAC»;
>   - il [backlog dopo la 1.2](../../Phase_0/BACKLOG_POST_1.2.md), sezioni C, I, P, T, V, e il
>     [backlog 38](../../Phase_0/38_postReleaseBacklog/README.md) (P-10, C-33).
> - **Wiki**: grafo assente nella worktree (atteso). Lette direttamente:
>   `decisions/orphan-transfer-becomes-an-adjustment`, `problems/dirty-days-ignore-fx-only-moves`,
>   `decisions/signal-label-unification`, `decisions/pac-fx-one-rate-map-direct-conversions`,
>   `decisions/risk-library-versus-own-maths`, `decisions/ai-export-version-bump-once-per-release`.
> - **Verifica**: 3 sottoagenti `explore` in sola lettura (inventario delle U, bug assegnati, superfici del riordino)
>   più letture mie, su `459131eb8`; il codice è identico in `c9bb8f257`. Le righe citate si riverificano quando un
>   lotto le tocca.

## 0. Mandato e autorizzazioni

### 0.1 Mandato (kickoff del coordinatore, 14/10)

Parole del developer, alla lettera, riportate nel kickoff:

- «è imperativo nella prossima release rilasciare le feature che ci permettono di rilasciare librefolio cloud, è
  importante lavorare, con spirito critico, alle attività in backlog che ci siamo lasciati post 1.2 e se nel farlo
  riusciamo a tirarci dentro dei todo_futuri che vengono facili, non dispiace.»
- «proprio perchè dobbiamo avviare molti lavori in parallelo, prenderci del tempo iniziare per riodinare e
  fattorizzare credo sia prioritario» → scelta: «Tutto il riordino del piano 43, backend e frontend, compresi i file
  più grandi».
- Perimetro del backlog: errori che toccano numeri, sicurezza o dati, e chiarezza per utenti non esperti. Regola 10:
  ogni calcolo finanziario ha una casa sola, `backend/app/services/financial_math/`.

Voci assegnate a J: T-PL1, T-P2.2 (per i miei file), T-U1…T-U10 (U8 solo backend), T-B4…T-B9, T-D9, B8, B11, B15,
V-3, V-11, P-10, C-33 (da verificare), C-71, C-73, C-74, C-75, C-76.

### 0.2 Via libera parziale (coordinatore, 14/10 ~22:55)

- **Chi**: l'approvazione del piano in questa sessione l'ha data il coordinatore della 1.3, alle 22:55 del 14/10, su
  delega esplicita del developer. Non è un'approvazione diretta del developer.
- **Parole del developer**, alla lettera, mentre legge il documento delle decisioni: «chat, sto leggendo
  LibreFolio_developer_journal/Release_2/Phase_1/decisioni-analisi-20261014.md — ho appena finito le prime 11 domande
  e sto iniziando piattaforma, ma ho già messo varie note dev, leggi intanto quelle, vedi se con quelle risposte devi
  aggiornare quello che viene dopo e poi vedi tu se aspettare che leggo tutto, o intanto grazie a queste riesci ad
  avviare qualche lavoro»
- **Decisione del coordinatore**: parte solo il primo checkpoint, riordino puro senza decisioni di prodotto aperte:
  **J-0 e CP-1**. Il resto aspetta che il developer finisca di leggere; il via lo dà il coordinatore, con le sue
  risposte.
- **Ordine dei checkpoint**: approvato (§4), con le correzioni delle 19:35. Handoff FROZEN dopo J-0; CP-1 dopo il
  commit di J-0.

## 1. Stato reale (verificato su `459131eb8`, codice identico in `c9bb8f257`)

### 1.1 Riordino

| File | Righe | Importatori app / test | Note |
|---|---|---|---|
| `services/pac_allocator/evaluator.py` | 3 754 | 6 / 9 (alias `EV`, 23 letture di nomi privati) | cuciture al §4, CP-1 |
| `services/portfolio_allocation_source.py` | 1 621 | 1 (`api/v1/portfolio_api.py:36`) / 3 | ~25 patch sull'alias `source`; `source_ref` di contratto a `:301`, `:312` |
| `schemas/pac_allocator.py` | 2 522 | 6 / 9 | 138 classi; nessun nome doppio |
| `services/portfolio_service.py` | 2 358 | 7 (2 pigri) / 20 file | `transaction_service.py:50` (W) importa `compute_wac_iterative` |
| `services/risk/service.py` | 1 456 | 2 / 7 | patch su `risk_service_module.*`; T-R1 a `:440` |
| `services/signal_service.py` (+ `signal_runtime` 45, `signal_annotations` 441, `signal_series_preparation` 479) | 1 315 | 5 / 11 | `main.py:59` (H) importa `signal_runtime` |
| `services/series_preparation.py` | 457 | 4 (uno è `asset_sources/price_query.py:48`, X) / 2 | puro; contiene R6 e R10 |
| `services/lots_analysis_service.py` | 1 172 | 3 / 8 | `requires_lots_analysis_service` è contratto |
| `schemas/risk.py`, `portfolio.py`, `signals.py` | 1 829, 1 637, 1 372 | 44 / 61 / 76 file | C3 |

- **Ciclo rischio↔segnali**: `risk/signal_helpers.py:26` → `signal_plugins.base`; `rolling_beta`, `rolling_sharpe`,
  `rolling_volatility`, `rolling_return` e `drawdown` → `risk.signal_helpers` (`drawdown` anche `risk.metrics`).
- **Ri-esportazioni**: `signal_plugins/__init__.py:3`; basi pigre in `provider_registry.py:20-26` (file di X).
- **Patch dei test**: nessuna per stringa, tutte su alias di modulo. Le stringhe dei vecchi percorsi stanno in
  `test_layer_boundaries.py:51-59`, `:143-159`.
- **Contratti che contengono nomi di modulo** (non si toccano): `source_ref="portfolio_service.compute_wac_iterative"`
  e `"portfolio_engine.PortfolioCalculationEngine"` (`portfolio_allocation_source.py:301`, `:312`);
  `requires_lots_analysis_service` e `requires_signal_plugins` (`ai_export/datasets/catalog.py`); il namespace
  `"signal_plugins"` (`provider_registry.py:390`).
- **Impronta degli schemi dei Tool**: per nome di classe (`tools/schema.py:178`, `:227-229`), quindi invariata se i
  nomi restano.
- **Nessuna guardia** vieta oggi il DB dentro `pac_allocator/`: il worker dei Tool importa solo la catena del planner.

### 1.2 Unificazioni

- **Già fatte**: O1 e O2 (`effective_share`, `native_cash.py:56`); X2 (B3a); X5 sui movimenti (F); R16 lato FX
  (`displayFxDelta`); P5 nel grafico (B3b); V5 solo in `pac_allocator/numeric.py`.
- **Cambiata**: R1, i due rami ora sono identici: codice doppio, non divergente.
- **Da fare**:
  - U1: X1 (`portfolio/engine.py:348,455`, `daily_state.py:909-922`), X3 (`yield_on_cost.py:439-545`), X9
    (`evaluator.py:192-206`, `normalize.py:615-631`), `series_preparation.py:184`; X6–X8 e `fx.py:717` nei file di X
    dopo il suo PL4, con X informato (D-J17);
  - U2: S1–S3 (S3 senza validazione, `lots_analysis_service.py:563-569`);
  - U3: O3 (`portfolio_income.py:350-379` con `abs`; `broker_cost_efficiency.py:152-158,353`), O4
    (`portfolio_allocation_source.py:487,544-545,597-598`: quota senza ruolo, oggi innocua);
  - U4: R1 (`portfolio_service.py:970-1028`, `:1245-1268`), R2 (`:2145-2191`), R3 (`:876-883` e
    `lots/histories.py:513-516`), R5 (`:1040`) e `:824`, R6 in tre copie (`series_preparation.py:66-81`,
    `risk/service.py:1154`, `risk_plugins/comparison/plugin.py:236`, diverse a 0 giorni), R7–R11, C1 (`:239-272`),
    C2 (`broker_service.py:420-453`, W), P1 (`:585-650`);
  - U5: V1 (`lots/prices.py:26-49`), V2/P2 (`:525-531`, `:828-848`), V3 (W), V4 (c), V5 (`evaluator.py:481,673,2085`,
    `normalize.py:869`), V10 (X), R4/B8 (`:1766-1858`);
  - U6: L1 (`:396-420`), L2 (`:435-457`); U7: W1 (`:958-964`), W5 (`risk/service.py:542-559`);
  - U9: R12–R14, C3, C4, V7 (`payloads/portfolio_broker.py:664`), V8, W2–W4, Q1, Q2, P3; U10: I1, I2 (plugin SI).
- **Copie nuove**, fuori dall'inventario del 43: 365 in `risk/metrics.py:741`, `risk/quant/resampling.py:235`,
  `risk/quant/quantlib_worker.py:116,195`, `CompoundSignal.ts:69`; rendimenti in `fx_timing_context.py:361-362`;
  `levelHelpers.ts:359` (Y).

### 1.3 Bug assegnati

| Voce | Stato | Dove oggi |
|---|---|---|
| T-B4 | ✔ | L1 `portfolio_service.py:396-420`; il FIFO tiene `lot.opening_date` (`fifo/engine.py:658`); nessun test |
| T-B5 | ✔, più largo | `fifo/engine.py:602-638`, e `lots/histories.py:160-182` converte proventi e P&L con la valuta del lotto alla data di chiusura (§3, D-J1) |
| T-B6 | ✔ | `lots_analysis_service.py:732-733,814`; la regola giusta c'è già a `lots/histories.py:300` |
| T-B7 | ✔ | `snapshotDataRenderer.ts:306-315`: solo un contatore globale |
| T-B8 | ✔ | `payloads/portfolio_broker.py:532-622` |
| T-B9 | ✔ | `snapshotDataRenderer.ts:256-273`; `reconciled` è `< 1e-9` stretto |
| T-D9 | ✔ | `MeasureSignal.ts:103,133`; soglia della casa `returns.py:81,127` |
| B8 | ✔ in parte | `portfolio_service.py:1766-1858`; la parte TRANSFER si prova col rosso |
| B11 | ✔ | `native_cash.py:181,271-279`; golden `fixtures/native_cash_guard/eur_only_golden.json` |
| B15 | ✔ | tre regole diverse; la pagina broker conta le transazioni future (D-J16, a W) |
| V-3 | ✔ | `transaction_service.py:347` (W); il test della Dashboard S7 c'è, quello dei lotti no |
| V-11 | ✔ | `price_marks.py:178-224`; grazia dal primo BUY/SELL, `portfolio_service.py:1087` |
| P-10 | ✔ | cambio di tipo in `asset_sources/price_store.py:745-783`; la cancellazione è impedita dal DB (`ondelete=RESTRICT`) |
| C-33 | ✅ già fatta | treno 28 (chiusa dal coordinatore) |
| C-71 | ✔ | chiavi solo in `i18n/charts`; la pagina asset le usa a mano (file di X) |
| C-73…C-76 | ✔ | `planner/format.ts:223-236`; `pacAllocator/en.json:454-455`; `planner_report.py:1086-1091`; `planner/request.ts:155-176`, `normalize.py:449-450` |

Contraddetta: **B12** (sezione I), i tre chiamanti di `_get_transactions` passano `date_to` (`:753`, `:1466`,
`:1698`): la confermo nel lotto dei contributi (CP-3), come chiede il coordinatore.

## 2. Regole comuni applicate (piano generale, §6)

- **C1 — nomi.** Un file che entra in un pacchetto tiene il suo nome; i moduli nati dal taglio hanno nomi brevi per
  tema. Quindi:
  - `portfolio_allocation_source.py` → `pac_allocator/source/portfolio_allocation_source.py`;
  - `pac_allocator/evaluator.py` → `pac_allocator/evaluation/evaluator.py`;
  - `schemas/pac_allocator.py` → `schemas/pac_allocator/pac_allocator.py`;
  - più avanti `portfolio_service.py` e `lots_analysis_service.py` → `services/portfolio/`; `signal_service.py`,
    `signal_runtime.py`, `signal_annotations.py`, `signal_series_preparation.py`, `risk/signal_helpers.py` →
    `services/signals/` coi loro nomi.
  - `series_preparation.py` tiene nome e posto: lo usano rischio, segnali e prezzi, e un pacchetto di dominio creerebbe
    una dipendenza fra loro. Esce solo la sua matematica (U4a). Questo sostituisce `market_series.py` (D-J7).
- **C3 — schemi.** `schemas/<dominio>/` con moduli per tema e `__init__.py` con la sola docstring; l'hub
  `schemas/__init__.py` resta; chi importa una classe la prende dal modulo che la definisce; nomi di classe invariati.
- **C4 — classi grandi.** Mixin per tema composti nella classe del modulo di servizio; metodi pubblici e patch sui
  metodi invariati. Le funzioni di modulo vanno nei moduli per tema.
  - **Le patch** puntano al modulo nel cui spazio dei nomi la chiamata legge il nome (§1.3 e §4.3 del 43): una
    funzione definita in `loaders.py` e chiamata da un altro modulo che l'ha importata va patchata lì, altrimenti la
    patch è muta.
  - Guardia: uno script AST usa e getta in `/tmp` controlla che ogni coppia (modulo, nome) patchata dai test sia letta
    da quel modulo.
- **C5 — `npm ci`.** Permesso, solo dal lock e nel mio worktree, quando serve a un controllo. Per i lotti di solo
  riordino del backend bastano i JSON di `dev.py api schema`.
- **C6 — devWiki.** Le righe «Source files» dei file che sposto le aggiorno io, nello stesso lotto;
  `check_source_paths.py` non peggiora.
- **Regole di ogni lotto di riordino**: rinomina e taglio in due commit (il coordinatore committa la rinomina da sola);
  niente shim né barili; grep dei vecchi percorsi a zero in `backend/`, `scripts/`, `.github/`,
  `mkdocs_src/docs/developer/`; stessi conteggi della base; ruff, black, dead code senza reperti nuovi; generati
  dell'API identici; `mkdocs build` stretto e `check-links`; rinomine ≥ 95 % in `git diff -M`; `applyTo` aggiornati.
- **Programma colori**: nessun file dei lotti di R prima del loro ingresso; nessun taglio di file Svelte nei miei lotti
  (il «taglio dichiarato» non mi tocca); `MeasureSignal.ts` (T-D9) dopo il lotto B.

## 3. Decisioni

| # | Domanda | Proposta | Stato |
|---|---|---|---|
| D-J1 | T-B5: P&L dei lotti in valuta estera | **B**: ogni gamba nella sua valuta alla sua data (proventi dalla valuta della chiusura alla data di chiusura, costo dalla valuta del lotto alla data d'apertura; `LotClosure` porta la valuta della chiusura) | al developer (punto 26) |
| D-J2 | P-10: lo SPLIT riclassificato | **A**: rifiutare il cambio di tipo di uno SPLIT con rettifiche legate senza costo, con un messaggio tradotto | al developer (punto 27) |
| D-J3 | B11: i giorni di solo cambio dei titoli | curarla in un lotto proprio; valori dichiarati, golden rigenerato | al developer (punto 28) |
| D-J4 | V-3: chi scrive | W scrive il percorso e la migrazione dei dati; J i rossi su lotti e Dashboard | ✅ coordinatore |
| D-J5 | Il renderer dell'AI Export | `features/ai-export/**` a J; la sola sezione legale di `promptRenderer.ts` la scrive A, in un lotto concordato | ✅ coordinatore |
| D-J6 | C-71: due «Rolling Return» | chiavi distinte, nessun ritiro; il testo «(calendar days)» nel catalogo `charts` lo scrive J | scrittura ✅ coordinatore; scelta al developer (punto 29) |
| D-J7 | Nomi dei moduli | C1 (§2); `series_preparation.py` resta | ✅ coordinatore |
| D-J8 | `signal_plugins/base.py` e le basi pigre | li sposta X nel PL2 | ✅ (analisi di X) |
| D-J9 | Schemi | C3 (§2) | ✅ coordinatore |
| D-J10 | `lots_analysis_service.py` | in `services/portfolio/`, col suo nome (C1) | ✅ coordinatore |
| D-J11 | T-D9 | dopo il lotto B dei colori, lo fa J | ✅ coordinatore |
| D-J12 | U10 | il file del plugin SI è di J per quel lotto, X informato | ✅ coordinatore |
| D-J13 | `npm ci` | regola C5 | ✅ coordinatore |
| D-J14 | Versioni dell'AI Export | regola già scritta («Versions» di `ai-development.instructions.md`): +1 al massimo su `v1.2.0`, mappa compatta nello stesso cambio | regola |
| D-J15 | V-11 | curare la regola: la grazia parte dall'ultima quotazione di mercato; senza quotazioni dal primo BUY/SELL, come oggi | al developer (punto 30) |
| D-J16 | La cassa della pagina broker | a W | ✅ coordinatore |
| D-J17 | X6, X7, X8, `fx.py:717` | restano a J, scritti nei file di X dopo il suo PL4, con X informato | ✅ coordinatore |
| D-J18 | Guardia del motore del PAC | test `ast` (test-author): i moduli del motore non importano `pac_allocator.source`, `sqlalchemy` né `db.models` | ✅ coordinatore |

**D-J1, i valori.** La sintesi del lotto calcola `pnl = total_value − opening_value` e `market_pnl = pnl − realized`
(`lots_analysis_service.py:728-770`).
- **Una sola valuta estera.** Esempio: 100 USD comprati quando 1 USD = 1,00 €, venduti a 110 USD quando 1 USD = 0,90 €.
  - Oggi: realizzato +9 €, «di mercato» −10 € su un lotto chiuso, totale −1 €.
  - Con B: realizzato −1 €, di mercato 0, totale −1 €, come il realizzato WAC della Dashboard.
  - Il totale non cambia: cambia solo la ripartizione.
- **Valute miste.** Esempio: aperto a 100 €, trasferito, venduto a 110 USD quando 1 USD = 0,90 €.
  - Oggi: proventi «110 €» (gli USD letti come EUR), totale +10 €.
  - Con B: proventi 99 €, realizzato −1 €, totale −1 €.
  - Cambiano proventi e totale, che oggi sono sbagliati.

## 4. Lotti e checkpoint

Ordine: prima i lotti indipendenti; il portafoglio si sposta solo dopo che la sua matematica è uscita (§P2.2 del 43);
rischio e segnali dopo il PL2 di X; i numeri sbagliati per gli utenti prima dei consolidamenti. Se una decisione tarda,
il suo lotto scivola senza fermare gli altri. **Ora autorizzati: J-0 e CP-1.**

| CP | Contenuto | Dipende da | Peso |
|---|---|---|---|
| J-0 | piano nel repo, sezione J del backlog, base (`all-backend`, statici, generati dell'API, mkdocs, devWiki) | — | — |
| CP-1 | PAC: sorgente, evaluator e schemi in pacchetti (C1, C3, C4); guardia D-J18 | J-0 | medio |
| CP-2 | PAC: C-75 (backend), C-76, C-73, C-74 | via | basso |
| CP-3 | U5a: B8 + V2/P2 + R4 (+ B19), conferma di B12 | via | medio |
| CP-4 | U4b (R1/R2, R3, R5 e `:824`, P1, C1) + V-11 | via, D-J15 | medio |
| CP-5 | U2 + U6 + T-B4 | CP-3, CP-4 | medio |
| CP-6 | B11 | D-J3 | medio-basso |
| CP-7 | Lotti: T-B5, T-B6, V1 | D-J1 | medio |
| CP-8 | `services/portfolio/` (+ `lots_analysis_service`) + schemi del portafoglio | CP-3, CP-4, CP-5 | medio |
| CP-9 | rischio diviso + T-R1 + schemi del rischio | PL2 di X | medio-basso |
| CP-10 | PL1 + U4a + schemi dei segnali + C-71 | PL2 di X, CP-9, D-J6 | medio |
| CP-11 | U1 (X1, X3, X9, `:184`; X6–X8 e `fx.py:717` dopo il PL4) + U3 + U7 + B15 lato PAC | CP-8 | medio |
| CP-12 | AI Export: U9, parti AI di U3/U7, T-B7, T-B8, T-B9, T-U9; sonde | CP-7, CP-11 | medio |
| CP-13 | U8 lato backend per Y | CP-3, CP-4 | medio-alto |
| CP-14 | U10, T-D9, i rossi di V-3, P-10 | D-J2, D-J11, D-J12 | basso |

### J-0 — il piano e la base

1. Questo piano; la sezione J del backlog (righe nuove al checkpoint).
2. Base sulla corsia: `all-backend` coi conteggi; ruff, black, dead code; hash dei 5 file generati dell'API (ignorati
   da git: `generated.ts`, `generated-tools.ts`, `openapi.json`, `tool-contract-map.generated.ts`,
   `tool-contracts.openapi.json`) e del JSON di `openapi.json` senza `info.version`; `mkdocs build` stretto e
   `check-links`; `check_source_paths.py`.
3. Handoff FROZEN; CP-1 dopo il commit.

### CP-1 — il PAC in pacchetti

Nessun cambio di comportamento. Due commit: A (rinomina) committato da solo dal coordinatore, poi B (taglio).

- **A — rinomina** (`mv` dei file interi, più gli import):
  - `services/portfolio_allocation_source.py` → `services/pac_allocator/source/portfolio_allocation_source.py`;
  - `services/pac_allocator/evaluator.py` → `services/pac_allocator/evaluation/evaluator.py`;
  - `schemas/pac_allocator.py` → `schemas/pac_allocator/pac_allocator.py`;
  - `source/__init__.py`, `evaluation/__init__.py`, `schemas/pac_allocator/__init__.py` con la sola docstring;
  - import riscritti in app, test e runner; patch sui nuovi moduli; le stringhe di `test_layer_boundaries.py`.
- **B — taglio**, lungo le cuciture (nomi definitivi dopo la lettura completa, grafo senza cicli):
  - sorgente: caricamenti (`:46-138`), provenienza e chiavi (`:141-318`), entità (asset, broker, posizioni, cassa,
    prezzi; `:320-700`), classificazioni (`:702-882`), cambi e WAC (`:884-1280`), distribuzione (`:1282-1436`);
    l'ingresso `build_portfolio_planner_source` resta in `portfolio_allocation_source.py`;
  - evaluator: errori e identità (`:99-180`), scenario e valorizzazione (`:181-494`), raggiungibilità (`:495-663`),
    limiti (`:664-945`), riferimenti di vincoli e obiettivi (`:946-1550`), stato economico (`:1551-2335`), fatti
    (`:2336-2865`), politica (`:2866-3553`); `evaluate_exact_candidate` e `rounding_top_ups` restano in
    `evaluator.py`;
  - schemi: base e numeri, ingressi dello scenario, uscite (scalari, issue, evidenze, risultati), Rebalancer;
  - **grafo delle cuciture** (script AST in `/tmp/libreFolio_j/`, sola lettura, su `c9bb8f257`): la sorgente non ha
    cicli. L'evaluator ne ha due, da rompere ritoccando le cuciture del 43:
    - scenario ↔ raggiungibilità, per due aiuti di chiave (`_fx_pair_key`, `_source_currency`): le chiavi e i quanti
      (`_*_key`, `_entity_refs`, `_floor_units`, `_is_quantum_multiple`) vanno in un modulo comune;
    - politica ↔ evaluator: `build_exact_policy_view` chiama `evaluate_exact_candidate`, che valida con
      `_validate_policy_view`, `_candidate_contract_conflicts` e `_objective_value_map`. La validazione di vista e
      candidato va in un modulo suo: politica → evaluator → validazione;
  - i nomi letti fra moduli diventano pubblici (precedente di T-1); le patch dei test sul modulo che legge il nome;
    script AST per le patch mute;
  - guardia D-J18 (test-author), registrata nella voce del PAC del runner.
- **Doc e testo**: pagine dev che citano i percorsi; `.github` (`devpy-i18n` cita `pac_allocator/evaluator.py:968`);
  righe «Source files» della devWiki (C6); `TODO_FUTURI.md:2203` (riga da assegnare dal coordinatore).
- **Cancelli**: `services pac-planner-{core,evaluator,oracle,policies,proof,report,service,solver,wire-numbers}`,
  `services portfolio-allocation-source`, `services tools-registry`, `schemas pac-planner`, `api pac-planner-tool`,
  `api tools`, `api portfolio`; poi `all-backend` con gli stessi conteggi; generati dell'API identici; ruff, black,
  dead code; grep dei vecchi percorsi a zero; `mkdocs build` e `check-links`; `check_source_paths.py`.

### Gli altri lotti (in attesa del via)

- **CP-2**: rossi C-75 (un limite −0.0 → «0»), C-76 (`localProblems` a tabella per segno e zero, chiavi nuove nei 4
  cataloghi di `pacAllocator`; il percorso giusto in `normalize.py:449-450`), C-73 (percentuali con `roundDecimal`, con
  i pareggi), C-74 (i due testi d'aiuto nei 4 cataloghi); gate del PAC e Prettier del planner.
- **CP-3**: contributi e variazione a 1 giorno dai prezzi del motore (ripiego, split, conversioni), TRANSFER, ordine
  degli unallocati; valori dichiarati prima.
- **CP-4**: un ribasamento solo nella casa; via la riprova MWRR solo con la parità provata; R3, R5, `:824`, P1, C1 dalla
  casa; V-11 secondo D-J15.
- **CP-5**: `financial_math/splits.py`; finestre di detenzione dal FIFO (data d'origine, D-7); soglia della polvere nel
  FIFO; annualizzati che cambiano elencati prima.
- **CP-6**: giorni «dirty» anche per le valute dei titoli; golden rigenerato col suo comando.
- **CP-7**: T-B5 secondo D-J1; T-B6; prezzi dei lotti dalla regola della casa; sonda mirata su un Asset coi lotti
  esteri (DB copiato della corsia).
- **CP-8…CP-14**: come nella tabella; i dettagli si scrivono qui quando arriva il via.

## 5. Conflitti

- **X**: il PL2 tocca tutti i plugin di rischio e segnali e `risk/service.py:62`, `signal_service.py:56` (CP-9 e CP-10
  dopo); il PL4 cambia una riga d'import di `convert_bulk` per file nella casa; `price_store` (P-10, V10);
  `price_query` e i router di asset e cambi importano `series_preparation` e `signal_service`; la pagina asset (C-71);
  il PL7 dopo CP-10. CP-1 non tocca file di X.
- **H**: `main.py:59` (CP-10); `data_quality_thresholds` → `platform/` cambia gli import nella casa, nel PAC (anche
  nella sorgente di CP-1) e nella guardia.
- **A**: `settings_service` → `accounts/` cambia l'import in `portfolio/engine.py` e nella guardia.
- **W**: `transaction_service.py:50` (CP-8); `broker_service` (V3, C2, B15); `delete_by_broker` (V-3); gli eventi (P-10).
- **Z**: nessuno. **Y**: consuma CP-13; T-D9. **Colori**: nessun file dei lotti di R nei CP-1…12.
- **Condivisi**: catalogo del runner (le mie righe), i18n (`pacAllocator`, cartelle dei plugin dei segnali; `charts`
  per C-71), generati dell'API, CHANGELOG e navigazione (testo nell'handoff).
- **Conflitti modify/delete** sui file spostati: si portano le modifiche nel modulo nuovo, mai tenendo il vecchio file.

## 6. Rischi

- Patch mute dopo i tagli: script AST in `/tmp` (C4) e la suite.
- Identificatori di contratto rinominati per errore: elencati al §1.1, esclusi dalle sostituzioni.
- Riferimenti in avanti degli schemi Pydantic divisi: ogni modulo importa ciò che usa, senza cicli; i generati
  dell'API devono restare identici.
- Il server di test costruisce il frontend se manca: in un worktree nuovo serve prima `npm ci` (Fuori pista di J-0).
- `all-backend` ~20–25 min per giro, uno per corsia; mai nella finestra della galleria.

## 7. Definizione di fatto

- **Riordino**: vecchi moduli spariti; grep a zero; suite del dominio e `all-backend` con gli stessi conteggi della
  base; ruff, black, dead code senza reperti nuovi; i 5 generati dell'API identici (`openapi.json` senza
  `info.version`); `mkdocs build` stretto e `check-links`; `check_source_paths.py` non peggiora; rinomine ≥ 95 %; patch
  sui moduli che leggono; `applyTo` aggiornati; righe della devWiki.
- **Numeri**: rosso prima (test-author) visto fallire per il motivo giusto; valori che cambiano dichiarati prima;
  verde; doc EN (docs-writer); riga di CHANGELOG proposta; sonde per l'AI Export.
- **Sempre**: porta 6185 libera; piano aggiornato a ogni passo; handoff FROZEN.

## 8. Test e selettori

Preambolo: `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6185 --data-dir
/tmp/librefolio-r13-j <CATEGORIA> <AZIONE>`, uno alla volta.

- **PAC**: `services pac-planner-{core,evaluator,oracle,policies,proof,report,service,solver,wire-numbers}`,
  `services portfolio-allocation-source`, `schemas pac-planner`, `api pac-planner-tool`, `api tools`,
  `services tools-registry`; frontend `front-utility core-unit`, `component-unit`.
- **Rischio**: `services risk-all`, `risk-asset-set`, `risk-oracle`, `schemas risk`, `api risk`.
- **Segnali**: `services signal-{registry,runtime,contracts,service,annotations,plugins-core,plugins-close-only,plugins-ohlc,plugins-volume,plugin-matrix}`,
  `services asset-signals`, `services series-preparation`, `schemas signals`, `api signal-catalogs`,
  `api asset-signals`, `api fx-signals`, `api signal-request-validation`, `api signal-preview`.
- **Numeri**: `services financial-math`, `roi-fifo-utils`, `portfolio-engine`, `lots-analysis-pure`, `utils roi-utils`,
  `api portfolio`, `api portfolio-wac`, `api transactions-wac`.
- **AI Export**: `services ai-export`, `ai-export-pure`, `schemas ai-export`, `api ai-export`,
  `utils ai-export-probe-helpers`.
- A ogni checkpoint di riordino: `all-backend`.

## 9. Specialisti

`test-author` (ogni rosso, la guardia D-J18, la riscrittura di alias e patch), `docs-writer` (pagine dev, EN),
`project-historian` se servono le righe della devWiki; skill `ai-export-probe-tuning` (CP-7, CP-12), `test-triage` per
i rossi non ovvi. Ogni prompt agli specialisti porta il preambolo della corsia e i divieti (niente installazioni,
niente `./dev.py` nudo, niente `server --force`, niente altri checkout).

## 10. Avanzamento

### Analisi ✅ (2026-10-14)

> **Note implementazione**: analisi consegnata al coordinatore il 14/10 (prima versione e correzioni delle 19:35), poi
> FROZEN. Nessun file del repo toccato, nessun comando sulla corsia.
>
> **⚠️ Fuori pista**: dopo l'approvazione del piano nell'app ho scritto al coordinatore che l'aveva data il developer
> verso le 19:30. Era del coordinatore, alle 22:55, su delega del developer (§0.2): corretto qui.

### J-0 — il piano e la base ✅ (2026-10-14)

#### Statici della base ✅ (2026-10-14)

> **Note implementazione** (backend, log in `/tmp/libreFolio_j_base_*.log`):
> - `dev.py lint`: ruff pulito («All checks passed!»).
> - `black --check backend/`: 4 file da riformattare, preesistenti: `alembic/versions/004_release_1_2_0_schema.py`,
>   `test_api/test_portfolio_wac.py`, `test_api/test_portfolio_api.py`, `test_utilities/test_i18n_usage_gate.py` (i
>   due di portafoglio sono P-9).
> - `dev.py lint --dead-code --scope backend`: 36 reperti (10 senza riferimenti, 26 usati solo dai test).
> - I comandi sono girati a ridosso del fast-forward a `c9bb8f257`: il codice del backend è lo stesso, quindi i numeri
>   valgono per entrambe le basi.

#### Generati dell'API ✅ (2026-10-14)

> **Note implementazione**: `dev.py front build` (sotto) ha rigenerato l'API (`api sync`) su `c9bb8f257`. I generati
> sono ignorati da git, quindi la base sono gli hash (`/tmp/libreFolio_j_base_api_hashes.txt`):
> - `generated-tools.ts` `4630bb93…`, `generated.ts` `723f3992…`, `openapi.json` `13025306…`,
>   `tool-contract-map.generated.ts` `62798d0c…`, `tool-contracts.openapi.json` `202402e5…`;
> - `openapi.json` senza `info.version` (`v1.2.0-40-gc9bb8f257`, da `git describe`): `1da07e60…`.
> - **Determinismo provato**: la build di debug fatta dal server di test (23:06) ha rigenerato i 5 file sulla stessa
>   HEAD con hash identici (`/tmp/libreFolio_j_base_api_hashes_after_debug.txt`).

#### `all-backend` — la base ✅ (2026-10-14)

> **Note implementazione**: terzo giro, `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6185 --data-dir /tmp/librefolio-r13-j all-backend`, 23:13–23:48 su `c9bb8f257`:
> - **7/7 categorie, «ALL BACKEND TESTS PASSED»**; 23 invocazioni pytest, **12 965 passed, 28 skipped, 0 failed**
>   (35 min 04 s; il carico delle altre corsie allunga i tempi). Conteggi per invocazione in
>   `/tmp/libreFolio_j_base_allbackend_summary.txt`, log completo in `/tmp/libreFolio_j_base_allbackend.log`.
> - Le righe «❌ Resource cache incomplete» del log sono l'uscita attesa di test che passano
>   (`test_update_js_cache.py`).
> - Porta 6185 libera alla fine; istantanea del DB del runner in `.testLog/00_archive/` (ignorata).
> - `dev.py mkdocs check-links`: 95 link validi, «All cross-boundary links are valid!».

### Checkpoint J-0 🧊 (2026-10-14) — FROZEN, in attesa del commit del coordinatore

- Delta: questo piano (nuovo) e la sezione J di `Phase_0/BACKLOG_POST_1.2.md` (J-1, J-2, J-3). Nessun file di codice.
- Messaggio proposto: `docs(journal): plan J numbers and analysis, base`.
- CP-1 parte dopo il commit, con lo SHA dal coordinatore.

> **⚠️ Fuori pista**: il primo giro (`… dev.py test --test-port 6185 --data-dir /tmp/librefolio-r13-j all-backend`)
> è caduto prima di pytest: «Shared backend exited during startup (code 1)» dopo 14 s.
> - **Causa**, letta nel codice senza riprodurla: il server di test costruisce il frontend se manca
>   (`dev.py` `cmd_server` → `auto_build_frontend` → `cmd_fe_build`, che chiama `npx svelte-check` e `npm run build`),
>   e il worktree nuovo non aveva `node_modules`. Lo stdout del server va in `DEVNULL` (`_server.py:274-275`).
> - **Toccati**: il DB della corsia, creato dalle migrazioni (`/tmp/librefolio-r13-j/sqlite/app.db`), e un'istantanea in
>   `.testLog/00_archive/` (ignorata). Nessun file tracciato, nessun server rimasto, porta libera. Nella cache di `npx`
>   nessuna voce nuova: l'unica voce recente (`openapi-zod-client`, del 08/09) è stata toccata alle 23:01:16, dopo la
>   fine del giro (23:00:25).
> - **Cura**, regola C5 del coordinatore: `npm ci` dal lock in `frontend/` (exit 0, worktree pulito), poi
>   `dev.py front build` (exit 0, 23:04–23:06; `api sync`, svelte-check, build di produzione in `frontend/build`,
>   ignorata). `npm run generate-api` usa `openapi-zod-client` del lock (devDependency, `node_modules/.bin`).
> - Il coordinatore ha poi scritto la regola per tutti (`793395913`: `npm ci` prima della base, perché il server
>   condiviso costruisce il frontend; era successo anche a H).
>
> **⚠️ Fuori pista (secondo giro)**: con `node_modules` il giro è caduto per «Shared backend did not answer within
> 300s» (23:06–23:11).
> - **Causa**: prima di uvicorn il server fa, dentro gli stessi 300 s di `STARTUP_TIMEOUT` (`_server.py:48`),
>   `auto_build_frontend(debug=True)` (svelte-check e vite in modalità debug, ~4 min: la build di produzione non
>   serve, il segnale della modalità non coincide) e `auto_build_mkdocs()` (il sito mancava).
> - La build di debug è finita prima del tempo massimo (`frontend/build/.build-debug`, 23:10); il runner ha chiuso il
>   suo server, porta libera.
> - **Cura**: `dev.py mkdocs build` (sotto), poi il terzo giro: «Shared backend ready on port 6185» subito.
> - Segnalato al coordinatore per le altre sessioni: prima della base, `front build --debug` e `mkdocs build`.

#### MkDocs e devWiki ✅ (2026-10-14)

> **Note implementazione**:
> - `dev.py mkdocs build` (`--strict`, `dev.py:865`): exit 0, 0 avvisi, 61 s; «All 3012 relative asset URL(s) in
>   the built site resolve». Log `/tmp/libreFolio_j_base_mkdocs_build.log`.
> - `check_source_paths.py`: **5 percorsi inesistenti (8 occorrenze) in 5 pagine**, su 3 844 citati; tutti cartelle
>   generate (`htmlcov-*`, `frontend/coverage-js/`, una cartella di sonda). Il cancello è «resta a 5».
> - `mkdocs check-links`: dopo `all-backend`, per non toccare il sito mentre il server di test gira.
