# mkdocs — admin, teoria, sito — verifica 2026-09-02

> Fonti: [00_INDEX](../../../phases/05_cleanAudit/mkdocsAudit/00_INDEX.md) ·
> [05 admin](../../../phases/05_cleanAudit/mkdocsAudit/05_admin-installation-operations.md) ·
> [06a strumenti](../../../phases/05_cleanAudit/mkdocsAudit/06a-financial-theory-instruments.md) ·
> [06b indicatori](../../../phases/05_cleanAudit/mkdocsAudit/06b-financial-theory-indicators.md) ·
> [06c performance/risk](../../../phases/05_cleanAudit/mkdocsAudit/06c-financial-theory-performance-risk.md) ·
> [07 sito/community/gallery](../../../phases/05_cleanAudit/mkdocsAudit/07_site-community-gallery.md) ·
> [08 tassonomia](../../../phases/05_cleanAudit/mkdocsAudit/08-functionality-gap-taxonomy.md)
>
> Metodo: analisi statica read-only; nessun test né `mkdocs serve` eseguito (run full in corso).
> Verificato contro il **working tree del 02/09** (modifiche beta non committate incluse: font
> fail-loud, drawdown `full_history`, broker sharing, `TransactionDeleteModal` rimosso).
> Baseline vecchio audit: commit `09cbb7e2`, 2026-08-05. Branch attuale: `dev_release2`.

## Sintesi esecutiva

- **35 voci vecchie riverificate** (05: 14, 06a: 7, 06b: 5, 06c: 4, 07: 5).
  Esito: **10 FATTO · 6 PARZIALE · 19 ANCORA VALIDE · 0 SUPERATE nel senso di non più applicabili**.
- Le 5 voci Blocco 1 eseguite il 2026-08-05 (S1–S3) **reggono tutte** nel codice attuale.
- La remediation documentale Block 3 del 2026-08-05 è **meno completa di quanto dichiarato**:
  4 voci segnate "✅ Aggiornato" nel mio scope sono in realtà parziali (05 A4, 05 A5, 05 B11,
  06A R-04) e 1 "✅ Già allineato" non regge (06A R-06).
- **6 nuove discrepanze** nate nell'ultimo mese (N1–N6), di cui 2 major: la nota "portfolio
  aggregation futura" di `sharing.en.md` smentita dal codice del 01/09 e l'omissione del
  self-leave con cascata distruttiva last-owner.
- Igiene sito: **0 link interni rotti su 526** controllati (96 pagine dello scope), **0 pagine
  orfane / 0 target nav mancanti** su 287 voci nav (`mkdocs.yml`). Coerenza screenshot
  docs↔`gallery.spec.ts`: **114/114 coppie** ancora generate (verificato sul worktree
  modificato).
- Peggior sorpresa: `docker_advanced.en.md:304-315` — il fix WAL del backup (B11) fu applicato
  a `filesystem.en.md` ma **non alla pagina dove il reperto era stato aperto**; lo snippet
  `cp …/app.db` a container attivo è ancora lì, immutato.

## A. Verifica voci vecchie

Stato 2026-08 = stato dichiarato nei report dopo le remediation Block 3 / Block 1 (S1–S3).
Stato oggi: **FATTO** (regge) · **PARZIALE** (fix incompleto o applicato altrove) ·
**ANCORA VALIDO** (mai toccato, discrepanza confermata oggi) · **SUPERATO**.

### Report 05 — Admin e operazioni (14 voci)

| Voce | Stato 2026-08 | Stato oggi | Evidenza verificata 2026-09-02 | Azione |
|---|---|---|---|---|
| A1 `enable_registration` inerte | ✅ Implementato (codice) | **FATTO** | `backend/app/api/v1/auth.py:186-191` — `register()` chiama `is_registration_enabled()` (accessor a `global_settings_service.py:95`), 403 con esenzione primo utente; doc claim `settings.en.md:39` ora vera | Nessuna |
| A2 `require_email_verification` decorativo | Aperto (Blocco 2) | **ANCORA VALIDO** | Doc: `settings.en.md:40` (tabella) e `:63` ("Email verification gate"). Codice: unica occorrenza `backend/app/schemas/settings.py:92` — `grep -rn "require_email_verification" backend/ --include="*.py"` → solo lo schema; nessun accessor, nessun gate | Decidere: implementare o rimuovere dalla UI/doc |
| A3 `max_file_upload_mb` non vale per broker | ✅ Implementato (codice) | **FATTO** | `backend/app/api/v1/brokers.py:82` import, `:595` `max_mb = await get_max_upload_mb(session)`; doc `settings.en.md:41` ora vera | Nessuna |
| A4 `default_theme` omesso | ✅ Aggiornato (Block 3) | **PARZIALE** | Tabella: `settings.en.md:50` ✅ presente. Ma la sezione Categorie `### 🌍 Defaults` (`settings.en.md:73-75`) elenca solo `default_currency`/`default_language` — la direzione di correzione chiedeva entrambe | Aggiungere la riga in Categorie |
| A5 `scheduler_timezone` omesso / "server local time" | ✅ Aggiornato (Block 3) | **PARZIALE + nuovo drift** | Tabella: `settings.en.md:47` ✅; Categorie "Sync & Uploads" (`:66-71`) senza `scheduler_timezone`. Inoltre la formulazione del 05/08 è già superata dal commit c8bdbaea (31/08) — vedi N2 | Completare Categorie + riallineare semantica (N2) |
| B1 `--workers` auto | ✅ Implementato + doc EN corretta | **FATTO** | `dev.py:137-152` `_resolve_server_workers` (`auto`/`0` → `max(1, 2×(CPU−1))`), parser `dev.py:2163` `metavar="N|auto"`; doc `cli_tools.en.md:24-29` allineata | Solo traduzioni (N6) |
| B2 commento `user create` | Aperto (editoriale) | **ANCORA VALIDO** | `cli_tools.en.md:46` ancora "# Create a user (first user becomes admin automatically)"; codice `scripts/user_cli.py:114` — `is_superuser=True` incondizionato | Correggere commento |
| B3 `./dev.py mkdocs --gallery` | Aperto (editoriale) | **ANCORA VALIDO** | `docker_advanced.en.md:173` invariato; parser `dev.py:2259` registra `gallery` come sottocomando (`mk_sub.add_parser("gallery")`), nessun flag `--gallery` su `mkdocs` (`dev.py:2244-2288`). Riproduzione diretta impossibile oggi (env senza pydantic fuori pipenv) ma la struttura argparse è prova statica sufficiente | Correggere in `mkdocs gallery` |
| B4 URL `custom_startup.sh` 404 | Aperto (editoriale) | **ANCORA VALIDO** | `service_exposure.en.md:416,420` invariati. Riprodotto oggi: `curl -s -o /dev/null -w "%{http_code}" …/main/docs/static/tailscale-guide/custom_startup.sh` → **404**; `…/main/mkdocs_src/docs/static/…` → **200**; file reale `mkdocs_src/docs/static/tailscale-guide/custom_startup.sh` esiste | Correggere entrambe le occorrenze |
| B7 prerequisito server per gallery | ✅ Aggiornato (Block 3) | **FATTO** | `cli_tools.en.md:93-94` — "uses Playwright; starts/controls a test server and populates test data unless `--no-populate`" | Nessuna |
| B9 GHCR/`docker-compose.prod.yml` non documentato | ✅ Aggiornato (Block 3) | **PARZIALE** | Risolto in `user/installation.en.md:74,84,97` (GHCR + `./LibreFolio-data`, commit 33dc94a8). Ma `docker_advanced.en.md` — la pagina del reperto — **ancora zero occorrenze** di `ghcr`/`prod`/pre-built e nessun rimando alla pagina installation (`grep -i "ghcr\|prod\|pre-built\|installation"` → vuoto) | Aggiungere rimando incrociato in docker_advanced |
| B11 backup Docker senza cautela WAL | ✅ Aggiornato (Block 3) | **PARZIALE (peggior sorpresa)** | Il fix del 05/08 (33dc94a8) fu applicato a `filesystem.en.md:119` ("stop the container first"). La sezione del reperto, `docker_advanced.en.md:304-315`, è **immutata**: ancora `cp ./LibreFolio-data/sqlite/app.db …` + "No `docker cp` needed", senza stop né `-wal`/`-shm`. WAL confermato attivo: `backend/app/db/session.py:53` `PRAGMA journal_mode=WAL` | Allineare docker_advanced alla cautela di filesystem |
| B12 `./dev.py install` 4 step | ✅ Aggiornato (Block 3) | **FATTO** | `host_installation.en.md:94-97` elenca i 4 step (pipenv, root npm, frontend `npm ci`, Playwright) | Nessuna |
| C1 "LRU" impreciso | Aperto (info) | **ANCORA VALIDO** | `configuration.en.md:25` ancora "LRU"; codice `uploads.py:54` commento "In-memory LRU cache", eviction per timestamp di scrittura `uploads.py:117-119` (`min(... key=[2])`, mai aggiornato da `get()`) | Ritoccare etichetta doc+commento |

> ⚠️ **Parziale 03/09** (P1-17): etichetta corretta nelle 5 superfici doc (4 lingue +
> `registries.md`); il commento sorgente in `uploads.py` (oggi `:63`) dice ancora «LRU».

Campioni "verificati corretti" del 2026-08 riconfermati a campione: rotazione log settimanale/gzip
(`logging_config.py:10`), healthcheck `GET /api/v1/system/health` 30s (`system.py:198`,
`docker-compose.yml:55-57`), sintassi `user create/list/reset/promote/demote/init-settings`
(`user_cli.py:326-356` ↔ `cli_tools.en.md:44-58`).

### Report 06a — Teoria: strumenti (7 voci)

| Voce | Stato 2026-08 | Stato oggi | Evidenza verificata 2026-09-02 | Azione |
|---|---|---|---|---|
| R-01 percorso `financial_math.py` | Aperto (editoriale) | **ANCORA VALIDO** | `fundamentals/day-count.en.md:10` cita ancora `backend/app/utils/financial_math.py` — file inesistente (`ls` → absent); funzione reale a `asset_source_providers/scheduled_investment.py:71` | Correggere il percorso |
| R-02 DIVIDEND su Scheduled Investment | Aperto (ambiguo) | **ANCORA VALIDO** | `asset-events/dividend.en.md:80` invariata ("For Scheduled Investment assets, they are integral to the price model"); `grep -c "DIVIDEND" scheduled_investment.py` → **0** | Decidere refuso vs requisito, poi correggere |
| R-03 ADJUSTMENT "zero cost" | Aperto (Blocco 1, S5) | **ANCORA VALIDO** | `transaction-types/adjustment.en.md:47` invariata; codice blocca: `transaction_service.py:233-241` (`_requires_cost_basis`), issue `COST_BASIS_REQUIRED` a `:1492,1511,1528` | Voce di prodotto, in attesa |
| R-04 `AssetType.INDEX` omesso | ✅ Aggiornato (Block 3) | **PARZIALE** | Pagina dedicata `asset-types/index-benchmark.en.md:13` ✅ ("Read-only benchmark reference… transactions are not allowed", 33dc94a8). Ma la tabella riepilogativa `asset-types/index.en.md:17` mostra ancora Code `—` invece di `INDEX` — l'enum esiste (`backend/app/db/models.py:178`) | Aggiungere codice `INDEX` in tabella |
| R-05 Crédit Agricole invertito | ✅ Aggiornato (Block 3) | **FATTO** | `transaction-types/deposit-withdrawal.en.md:31` riscritta: contropartite solo nella "Securities Account Activity List", cedole/premi con WITHDRAWAL di bilanciamento — concorde con `broker_credit_agricole.py:66` (docstring) | Nessuna |
| R-06 justETF tra le fonti DIVIDEND | ✅ "Già allineato" (Block 3) | **ANCORA VALIDO** (la chiusura non regge) | La lista specifica del reperto, `asset-events/index.en.md:38-39`, elenca ancora solo "Yahoo Finance: may produce DIVIDEND events"; `justetf.py:419,425` genera eventi `DIVIDEND` da chart data. Il "già allineato" si basava sulla citazione justETF in altra pagina, ma la riga suggerita ("justETF: produces DIVIDEND events from chart data") non fu mai aggiunta | Aggiungere la riga (info) |
| R-07 late interest post-maturità | ✅ Aggiornato (Block 3) | **PARZIALE** | Documentato nella pagina **user** `user/assets/providers/scheduled-investment.en.md:37-39,59` (grace period, late interest, `generate_interest`). La pagina **teorica** del reperto, `asset-events/maturity-settlement.en.md:67-70,83-85`, resta assoluta: "price series ends at the maturity date", "no further accrual occurs after maturity" | Nota cross-link nella pagina teorica |

### Report 06b — Teoria: indicatori e benchmark (5 voci)

| Voce | Stato 2026-08 | Stato oggi | Evidenza verificata 2026-09-02 | Azione |
|---|---|---|---|---|
| B0 benchmark client-side non dichiarato | ✅ Aggiornato (Block 3) | **FATTO** | `synthetic-benchmarks/index.en.md:3` — "generated mathematically, **computed locally in the browser**" | Nessuna |
| B1 frequenze capitalizzazione "backend" | Aperto (Blocco 1, S6) | **ANCORA VALIDO** | `synthetic-benchmarks/compound.en.md:31` invariata ("LibreFolio's backend supports the following compounding frequencies"); codice: solo frontend `registry.ts:123` `source: 'local'`; `CompoundSignal.ts:30-46` — unici parametri `annualRate`/`offset`, nessuna frequenza | Voce di prodotto, in attesa |
| B2 default `annualRate` linear (5 vs 2) | Aperto (editoriale) | **ANCORA VALIDO** | `linear.en.md:45` → `5`; `LinearSignal.ts:29` → `default: 2`. Ereditato dalle traduzioni (`linear.it.md:45` → `5`) | Allineare tabella |
| B3 default `annualRate` compound (7 vs 8) | Aperto (editoriale) | **ANCORA VALIDO** | `compound.en.md:68` → `7`; `CompoundSignal.ts:35` → `default: 8` (IT: `compound.it.md:67` → `7`) | Allineare tabella |
| B4 default sine (10/365 vs 15/45) | Aperto (editoriale) | **ANCORA VALIDO** | `sine-wave.en.md:36-37` → `10`/`365`; `SineSignal.ts:37,48` → `default: 15`/`45` (IT: `sine-wave.it.md:36-37` → `10`/`365`) | Allineare tabella |

Nessuna regressione sul gruppo indicatori: i `docs_path` dei plugin puntano ancora a file
esistenti (a campione `adx.py:78`, `bollinger.py:79`, `donchian.py:68`).

### Report 06c — Teoria: performance e rischio (4 voci)

| Voce | Stato 2026-08 | Stato oggi | Evidenza verificata 2026-09-02 | Azione |
|---|---|---|---|---|
| F1 CASH_TRANSFER arrivo 100% a K | Aperto (Blocco 1, S6) | **ANCORA VALIDO** | Doc: `portfolio-engine/index.en.md:142` — "Arrival Leg: $K_d += \kappa$, $R_d += \rho$". Codice: `portfolio_engine.py:674-677` e `:965-968` — arrival leg interamente in `K[bid]`, commento "can't track exact split without buffering" presente in entrambe le fasi | Voce di prodotto, in attesa |
| F2 WAC "valuta più frequente" | ✅ Aggiornato (Block 3) | **FATTO** | `weighted-average-cost.en.md:139` — "latest acquisition currency (deterministic), falling back to the asset currency"; codice `wac_utils.py:52-59` (`max(acquisitions, key=date)`) concorde | Nessuna |
| F4 link aiuto WAC 404 | Aperto (editoriale) | **ANCORA VALIDO** | `WacPreviewSection.svelte:447` — `DocsLink path="financial-theory/portfolio-theory/weighted-average-cost/"`; quella cartella contiene solo `index/asset-allocation/diversification` (`ls mkdocs_src/docs/financial-theory/portfolio-theory/`); pagina reale `technical-analysis/performance-metrics/weighted-average-cost.en.md` esiste | Correggere il `path` |
| F5 "link directly" KPI | Aperto (editoriale) | **ANCORA VALIDO** | `performance-metrics/index.en.md:164-170` ancora "link directly to"; `KpiSection.svelte:239,290,327` (file modificato nel worktree beta, target invariati) → tutte a `user/dashboard/kpi-cards/#card-N-…` (percorso a due passi) | Riformulare "directly" |

Campioni riconfermati: grace 14 giorni (`portfolio_engine.py:420`), soglia annualizzazione 30
giorni (`roi_utils.py:90`).

### Report 07 — Sito, community, gallery (5 voci)

| Voce | Stato 2026-08 | Stato oggi | Evidenza verificata 2026-09-02 | Azione |
|---|---|---|---|---|
| R1 badge "SELF-HOSTED OR CLOUD" | Aperto (Blocco 2) | **ANCORA VALIDO** | `index.en.md:47` invariato; controparti ancora "futuro": `faq.en.md:15` ("Coming soon: hosted platform"), `contribute.en.md:89-93` ("we're planning") | Decidere wording badge |
| R2 FAQ crypto "Coming soon" | ✅ Aggiornato (Block 3) | **FATTO** | `faq.en.md:31` — "Crypto assets — Tracked as portfolio assets in the UI; not Forex…" | Nessuna |
| R3 fallback `alfystar.github.io` | Aperto (editoriale) | **FATTO** (fix separato, c0814ee4 del 12/08) | `gallery-img-loader.js:29-31` — base iniettata da `config.site_url` via `overrides/main.html:19` (`window.LF_GALLERY_FALLBACK_BASE`), fallback letterale `https://librefolio.github.io/LibreFolio` = `site_url` (`mkdocs.yml:2`) | Nessuna |
| R4 `fallbackUrl` obsoleto (codice morto) | Aperto (editoriale) | **ANCORA VALIDO** | `dashboard-check.js:15` ancora `'getting-started/installation/'` (`:78` assegnazione); nav reale `mkdocs.yml:621-622` (`user/getting-started.md`, `user/installation.md`); nessun `id="dashboard-link"` in `mkdocs_src/docs/` → ramo morto, impatto nullo latente | Aggiornare o rimuovere il ramo |

> ✅ **Risolto 03/09** (P1-17): ramo morto rimosso (strada «rimozione»).
| R5 "community-driven" | Aperto (info) | **ANCORA VALIDO** (info) | Framing invariato (`index.en.md:290,320`); `git log --format='%an'` su `brim_providers/` e `asset_source_providers/` → solo `Alfystar` | Nessuna (nota interpretativa) |

Igiene sito riverificata (task C): **nav intatta** — script inline su `mkdocs.yml`: 287 voci
`.md`, 0 target mancanti, 0 `.en.md` orfane; **link interni** — 526 link relativi Markdown su
96 pagine dello scope (admin, financial-theory, community, gallery, index) → 0 rotti;
**screenshot** — 114 coppie `data-category`/`data-name` delle 3 pagine EN tutte riconducibili a
`gallery.spec.ts` (76 chiamate letterali + 38 via array dinamici: `POSITIONS_SCREENSHOT_VARIANTS`
:310, `LOTS_SCREENSHOT_VARIANTS` :377, `TX_FORM_VARIANT_TYPES` :1063, `previewTypes` :977,
chiamate per categoria `dashboard` :578,653 e `brokers` :1522,1550, `menu-open` :494).

## B. Nuove discrepanze docs↔codice (ultimo mese)

### N1 — Build Docker/frontend ora fallisce "loud" sui font: nessuna pagina lo documenta 🟢 minor (omissione)

- **Codice (worktree 02/09, non committato)**: `dev.py:539` (`cmd_fe_build`) e
  `dev.py:1388` (`_docker_ensure_assets_built`) chiamano `update_js_cache(strict=True)` e
  abortiscono la build; `dev.py:2074-2094` — strict solo nei path di build, il dev-server resta
  non bloccante; `scripts/update_js_cache.py:40-46` (`_HARD_FAILURES`), `:442-446` (exit code
  non zero), `:205,219,240-246` (subset font mancante = hard fail). Motivazione nel codice:
  "the Docker image shipped with a 404 on the emoji font for months".
- **Docs**: `docker_advanced.en.md:19` cita **solo** `.env` come causa di rifiuto della build;
  `:28` descrive la build come automatica ("handles this automatically"); nessuna pagina
  admin/installation menziona che la build scarica font/JS da Google Fonts/CDN né che ora può
  fallire senza rete o senza cache calda (`grep -ri "cdn\|font\|offline" mkdocs_src/docs/admin/
  mkdocs_src/docs/user/installation.en.md` → nessun riferimento pertinente).
- **Impatto**: admin offline/air-gapped o con CDN bloccato ottiene un rifiuto di build non
  previsto dal manuale. Il messaggio d'errore è auto-esplicativo → gravità minor, ma la
  dipendenza di rete in fase di build andrebbe dichiarata (prerequisito).

### N2 — `scheduler_history_sync_times`: "stored in UTC" non è più vero dal 31/08 🟢 minor (dettaglio obsoleto)

- **Docs**: `settings.en.md:45` — "saved times are **stored in UTC** and first-boot defaults are
  converted from the configured timezone"; `:47` — `scheduler_timezone` "used to convert
  first-boot scheduler defaults and display scheduler state".
- **Codice** (commit c8bdbaea, 2026-08-31, "scheduler runs in its configured zone"):
  `backend/app/schemas/settings.py:117` — "Comma-separated HH:MM **local times** for history
  sync in scheduler_timezone"; `:132` — "IANA timezone used to **store and evaluate** scheduler
  history-sync days and times"; migrazione `alembic/versions/5b1333fa6b07_scheduler_times_use_configured_timezone.py`;
  `SchedulerConfigModal.svelte:5-6` — "Times and days are stored in the configured scheduler
  timezone. The backend converts local slots to UTC only when deciding if a job is due."
- **Nota**: la formulazione corrente della doc è quella scritta dalla remediation Block 3 del
  05/08 — corretta per 26 giorni, poi superata dal cambio di storage. La sostanza operativa per
  l'admin (gli orari inseriti sono nel fuso scelto) resta vera; è la frase sullo storage interno
  a essere diventata falsa.

### N3 — `sharing.en.md` superata dal giro broker-sharing del 01/09 🟡 major (contraddizione + omissione)

- **(a) Contraddizione**: `user/brokers/sharing.en.md:83` — "The share percentage is designed
  for **future** portfolio aggregation features. When these are implemented…". La feature è
  **implementata** dal commit 6ab295d8 (2026-09-01, F2): dashboard owned-brokers-only con
  scaling role-aware — `portfolio_service.py:1027-1029` e `:1760-1762` ("OWNER share scales
  (0% is valid…); EDITOR/VIEWER … scale 1").
- **(b) Omissione**: self-service leave — `PATCH`/`DELETE /brokers/{id}/access/me`
  (`backend/app/api/v1/brokers.py:502,528`): EDITOR/VIEWER sempre, OWNER solo se resta un altro
  OWNER; **l'ultimo OWNER che esce cancella broker + transazioni + report BRIM in cascata**
  (docstring `:536-542`). Nessuna pagina user documenta né il leave né la cascata distruttiva.
- **(c) Dettaglio collaterale** (si sovrappone al vecchio 02 F4, tier S5): l'esempio
  "Spouse (Editor): 50%" (`sharing.en.md:56-59`) è invalido per la regola schema
  `backend/app/schemas/brokers.py:380-384` ("only OWNERs can have share_percentage > 0") e per
  la UI (`BrokerSharingPanel.svelte:195` — slider share solo per OWNER); lo step 6
  (`sharing.en.md:18`) non distingue i ruoli.
- Regola "somma ≤ 100%" ancora vera: `broker_service.py:821-823`.

### N4 — Gallery: lo screenshot "Delete Linked Pair Modal" non ritrae più una modale dedicata 🟢 minor (dettaglio obsoleto)

- **Codice (worktree 02/09)**: `TransactionDeleteModal.svelte` **eliminato** (`git status` →
  ` D`); `gallery.spec.ts:1338-1367` — il delete di riga singola apre il **bulk workspace** con
  la coppia collassata in una riga marcata + banner split-hint; screenshot generato con lo
  stesso nome/categoria (`transactions`, `bulk-delete-pair-modal`).
- **Docs**: alt text "Delete Linked Pair Modal" a `gallery/desktop.en.md:175` e
  `gallery/mobile.en.md:179` (+ gemelli IT/FR/ES alle stesse righe) descrive una modale che non
  esiste più; il testo di `user/transactions/index.en.md:31` ("click the trash icon to delete,
  or check multiple rows to perform bulk deletions") resta accettabile ma non racconta la
  convergenza delete→bulk.
- Coerenza categoria/nome preservata → il check 114/114 tiene; è il contenuto atteso
  dell'immagine a essere cambiato.

### N5 — Drawdown `full_history`: parametro user-visible non documentato; teoria ora coerente col default ⚪ info

- **Codice (worktree 02/09)**: `signal_plugins/drawdown.py:36-53` — nuovo parametro
  `full_history` default `True` con chiavi i18n (`en.json:1131` "Full history", `:2347`
  tooltip "highest peak of the entire available history, not just the visible window");
  `schemas/signals.py:372-377` — `SignalWarmupRequirement.full_history`; fetch path
  `signal_service.py:129,274,316` + `asset_source.py:2200` (`if plan.requires_full_history:`);
  AI Export sempre full-history: `ai_export/components/drawdown_context.py:14-18,307-318`.
  Decisione registrata in `LibreFolio_devWiki/wiki/decisions/drawdown-full-history-warmup.md`.
- **Docs**: nessuna pagina user documenta il parametro (i segnali di rischio sono beta → per la
  convenzione dell'audit **non è un reperto formale**). La pagina teorica
  `risk-metrics/max-drawdown.en.md` è teoria pura e la formula ($\max_{\tau\le t}$) descrive
  proprio la semantica full-history: **il codice si è allineato alla teoria**, non viceversa.
  Le pagine ai-export (`asset.en.md:17,40`, `portfolio.en.md:83-85`) citano il Drawdown senza
  specificare finestre → nessuna contraddizione.
- **Da sorvegliare**: se i risk signals escono dal beta, documentare il toggle `full_history`.

### N6 — Drift i18n confermato e allargato; il "batch multilingua" non è mai partito 🟡 major (processo)

- Il 05/08 le correzioni EN furono rimandate a un batch traduzioni: a un mese di distanza le
  pagine IT/FR/ES restano al testo pre-fix. Verifiche puntuali:
  - `cli_tools.it.md:24-25`, `.fr.md:24-25`, `.es.md:24-25` — ancora "# With auto-calculated
    workers (2 × (CPU-1))" / `--workers N` (testo inglese perfino nelle pagine tradotte), mentre
    EN (`:24-29`) descrive `auto`/`0`;
  - `settings.it/fr/es.md` — zero occorrenze di `default_theme`/`scheduler_timezone` (EN li ha
    a `:47,:50`);
  - le tabelle default errate di 06b sono identiche nelle traduzioni (`linear.it.md:45` → 5,
    `compound.it.md:67` → 7, `sine-wave.it.md:36-37` → 10/365): errore EN ereditato, correggere
    prima l'inglese poi propagare;
  - i fix B3/B4/B2/C1/F4/F5 (mai applicati) riguardano pagine con gemelli tradotti: la
    correzione dovrà essere 4-lingue.
- **Contro-esempio positivo nel worktree**: la nota "Net Worth includes cash" di
  `kpi-cards.*.md` è stata applicata a tutte e 4 le lingue (+3 righe ciascuna) — prassi corretta
  da replicare.

## C. Functionality-gap-taxonomy: stato voci

### Blocco 1 — 13 voci: le 5 eseguite il 05/08 reggono; le 8 in attesa sono ancora valide

| Voce | Stato tassonomia | Oggi | Evidenza |
|---|---|---|---|
| 05 A1 | ✅ Implementato | **Regge** | `auth.py:186-191` |
| 05 A3 | ✅ Implementato | **Regge** | `brokers.py:82,595` |
| 05 B1 | ✅ Implementato | **Regge** | `dev.py:137-152`, parser `:2163` |
| 03 F2 (persistenza chart FX) | ✅ Implementato | **Regge** | `chartSettingsStore.svelte.ts:6-9,123,146` (localStorage user-scoped) |
| 03 F3 (rifiuto header FX) | ✅ Implementato | **Regge** | `FxDataImportModal.svelte:27-28` (`HEADER_MISMATCH_MESSAGES`), E2E `fx-csv-import.spec.ts:80-95` |
| 01 R-11 (Date Format) | In attesa (S4) | Ancora valido | nessuna preferenza `date_format` in `schemas/settings.py` né nei tab Settings |
| 02 F3 (Generic CSV TRANSFER/FX_CONVERSION/CASH_TRANSFER) | In attesa (S6) | Ancora valido | `broker_generic_csv.py:596-600` — rifiuto esplicito TRANSFER/FX_CONVERSION |
| 02 F4 (quota % per Editor) | In attesa (S5) | Ancora valido — anzi rafforzato | `schemas/brokers.py:380-384` invariato; il giro 01/09 (F2) ha reso la share owner-only anche nel calcolo dashboard |
| 02 F6 (eToro XLSX) | In attesa (S4) | Ancora valido | `broker_etoro.py:182-183,196` — solo `.csv` |
| 03 F4 (3 task FX AI Export) | In attesa (S5) | Ancora valido | doc `user/fx/detail/signals.en.md:51-56` — ancora 3 task (FX Trend Review / FX Exposure Impact / FX Conversion Timing Context); catalogo reale 2 (`analyses/catalog.py:210-238`: `pair_analysis`, `exposure_impact`) |
| 06A R-03 | In attesa (S5) | Ancora valido | vedi tabella 06a |
| 06B B1 | In attesa (S6) | Ancora valido | vedi tabella 06b |
| 06C F1 | In attesa (S6) | Ancora valido | vedi tabella 06c |

### Blocco 2 — 4 voci: tutte ancora valide

| Voce | Oggi | Evidenza |
|---|---|---|
| 02 F5 (PDF in BRIM) | Ancora valido | `grep -ri "pdf" backend/app/services/brim_providers/*.py` → 0 risultati |
| 03 F1 (SNB "daily") | Ancora valido | codice mensile (`fx_providers/snb.py:5-8` "monthly average… no daily dataset available"); docs ancora daily (`user/fx/providers/snb.en.md:3`, `providers/index.en.md:32,50`) — l'alternativa "a costo nullo" (correggere la pagina in monthly) non fu mai presa |
| 05 A2 (email verification) | Ancora valido | vedi tabella 05 |
| 07 R1 (Cloud) | Ancora valido | vedi tabella 07 |

### Blocco 3 — nel mio scope (13 delle 25 voci)

FATTO: 06A R-05, 06B B0, 06C F2, 05 B7, 05 B12, 07 R2 (6). PARZIALE: 05 A4, 05 A5, 05 B9,
05 B11, 06A R-04, 06A R-07 (6). NON REGGE la chiusura: 06A R-06 ("già allineato" — la lista di
`asset-events/index.en.md:38-39` non fu mai corretta). Le 12 voci dei report 01/02 sono scope
degli altri auditor di questa tornata.

### Voci editoriali nel mio scope (11 delle 21)

Ancora aperte: 05 B2, 05 B3, 05 B4, 05 C1, 06A R-01, 06B B2, 06B B3, 06B B4, 06C F4, 06C F5,
07 R4 (11). Chiuse fuori remediation: 07 R3 (fix 12/08). 07 R5 resta info/interpretativa.
Attenzione: B3, B4, F4 sono **quick win a una riga** aperti da un mese nonostante gravità
critical (B3, B4) e major (F4) nell'audit originale.

## Task riesumati + nuovi task docs

Riepilogo operativo, in ordine di priorità (S = <1h, M = mezza giornata, L = >1 giorno).
Nessuna modifica applicata da questo audit (sola verifica).

| # | Task | Evidenza | Stima |
|---|---|---|---|
| T1 | Correggere l'URL `custom_startup.sh` (2 occorrenze, tutte le lingue) | `service_exposure.en.md:416,420`; 404 riprodotto (`curl` → 404 vs 200 su path con `mkdocs_src/`) | S |
| T2 | Correggere `./dev.py mkdocs --gallery` → `./dev.py mkdocs gallery` | `docker_advanced.en.md:173`; parser `dev.py:2259` | S |
| T3 | Allineare backup Docker a cautela WAL (stop container / includere `-wal`/`-shm` / checkpoint) | `docker_advanced.en.md:304-315`; modello già in `filesystem.en.md:119`; WAL `db/session.py:53` | S |
| T4 | Correggere `path` del DocsLink WAC | `WacPreviewSection.svelte:447` → `financial-theory/technical-analysis/performance-metrics/weighted-average-cost/` | S |
| T5 | Allineare default benchmark (linear 2, compound 8, sine 15/45) EN + IT/FR/ES | `linear.en.md:45`, `compound.en.md:68`, `sine-wave.en.md:36-37` vs `LinearSignal.ts:29`, `CompoundSignal.ts:35`, `SineSignal.ts:37,48` | S |
| T6 | Completare A4/A5: aggiungere `default_theme` e `scheduler_timezone` alle Categorie | `settings.en.md:73-75` (Defaults), `:66-71` (Sync & Uploads) | S |
| T7 | N2: riallineare `scheduler_history_sync_times`/`scheduler_timezone` alla semantica post-31/08 (storage nel fuso configurato) | `settings.en.md:45,47` vs `schemas/settings.py:117,132`, `SchedulerConfigModal.svelte:5-6` | S |
| T8 | Aggiungere codice `INDEX` nella tabella asset-types; riga justETF in sources DIVIDEND; nota late-interest nella pagina teorica maturity | `asset-types/index.en.md:17`; `asset-events/index.en.md:38-39`; `maturity-settlement.en.md:67-85` | S |
| T9 | N1: documentare il fail-loud font/JS e il prerequisito di rete in build (docker_advanced + host_installation) | `docker_advanced.en.md:19,28` vs `dev.py:539,1388,2074-2094`, `scripts/update_js_cache.py:40-46,442-446` | S |
| T10 | N3: riscrivere `sharing.en.md` — aggregation non più "futura", self-leave + cascata last-owner, share solo OWNER (4 lingue) | `sharing.en.md:18,50-59,83` vs `portfolio_service.py:1027-1029`, `brokers.py:502,528`, `schemas/brokers.py:380-384` | M |
| T11 | N4: ritoccare alt text gallery delete-pair e una riga su delete→bulk in transactions | `gallery/desktop.*.md:175`, `gallery/mobile.*.md:179`; `user/transactions/index.en.md:31` | S |
| T12 | 05 B2: correggere il commento `user create` (sempre superuser via CLI) | `cli_tools.en.md:46` vs `scripts/user_cli.py:114` | S |
| T13 | 06a R-01/R-02: percorso `financial_math.py` → `scheduled_investment.py:71`; decidere refuso DIVIDEND/Scheduled Investment e correggere | `day-count.en.md:10`; `dividend.en.md:80` vs `scheduled_investment.py` (0 DIVIDEND) | S |
| T14 | 05 A2: decidere il destino di `require_email_verification` (implementare o togliere da UI+doc) | `settings.en.md:40,63` vs solo `schemas/settings.py:92` | M (decisione) / L (implementazione) |
| T15 | 06c F5: "link directly" → percorso a due passi via kpi-cards | `performance-metrics/index.en.md:164-170` vs `KpiSection.svelte:239,290,327` | S |
| T16 | N6: eseguire il batch traduzioni accumulato (cli_tools, settings, benchmark defaults, sharing, e tutte le correzioni T1-T15) | drift verificato su `cli_tools.it/fr/es:24-25`, `settings.it/fr/es`, `linear/compound/sine-wave.it` | M |
| T17 | 07 R4: aggiornare o rimuovere il ramo morto `fallbackUrl` in `dashboard-check.js` | `dashboard-check.js:15,78`; nessun `#dashboard-link` nel sito | S |
| T18 | 05 C1 (info): ritoccare etichetta "LRU" in doc e commento sorgente | `configuration.en.md:25`, `uploads.py:54,117-119` | S |

> **Stato 03/09 (esecuzione P1-17)**:
> - **T17** ✅: ramo morto `fallbackUrl` **rimosso** (verificato: 0 occorrenze in
>   `mkdocs_src/docs/` e `mkdocs_src/overrides/`).
> - **T18** ⚠️ **Parziale**: etichetta «LRU» corretta nelle **5 superfici documentali** (4
>   lingue di `configuration.*.md` + `registries.md`) — verificato: 0 occorrenze «LRU» nei
>   docs. Il **commento sorgente** in `uploads.py` (oggi `:63`) recita ancora «In-memory
>   LRU cache» (con nota TTL): residuo da ritoccare.
> - T14 resta **aperto**: decisione di prodotto P2-1 (`require_email_verification`).

Restano fuori come voci di prodotto (Blocco 1/2, tier S4-S6): 01 R-11, 02 F3, 02 F4, 02 F5,
02 F6, 03 F1, 03 F4, 06A R-03, 06B B1, 06C F1, 07 R1 — tutte riconfermate valide oggi
(sezione C).

## Cross-reference

- Indice e metodo dell'audit originale: [00_INDEX](../../../phases/05_cleanAudit/mkdocsAudit/00_INDEX.md);
  baseline: [00_BASELINE](../../../phases/05_cleanAudit/mkdocsAudit/00_BASELINE.md).
- Esecuzione S1–S3 (05/08): [15_esecuzione_s1_s3](../../../phases/05_cleanAudit/15_esecuzione_s1_s3.md);
  feature perse nei redesign: [16_feature_perse_nei_redesign](../../../phases/05_cleanAudit/16_feature_perse_nei_redesign.md).
- Report di questa tornata dagli altri ambiti (01–04: user core, transactions, FX, AI Export) —
  stessa cartella `08_newCleanAndDocumentation_audit/`.
- Decisione drawdown full-history (02/09): `LibreFolio_devWiki/wiki/decisions/drawdown-full-history-warmup.md`.
- Commit chiave citati: `33dc94a8` (05/08, remediation docs Block 3), `be8394bb` (05/08,
  remediation codice S1–S3), `c0814ee4` (12/08, fix R3 gallery fallback), `c8bdbaea` (31/08,
  scheduler timezone — causa N2), `6ab295d8` (01/09, beta F1–F17 — causa N3).

---

## Riepilogo finale

- Voci vecchie: 35 riverificate → **10 FATTO, 6 PARZIALE, 19 ANCORA VALIDE**; nessuna superata.
- Le 5 implementazioni S1–S3 del 05/08 reggono tutte nel codice attuale.
- La remediation Block 3 fu sovrastimata: 4 "✅" parziali (A4, A5, B11, R-04) e 1 "già allineato"
  che non regge (R-06); B11 è il caso peggiore — fixato `filesystem.en.md`, lasciato immutato
  lo snippet insicuro in `docker_advanced.en.md:304-315` dove il reperto era nato.
- Nuove discrepanze: **6** (N1 font fail-loud non documentato · N2 scheduler "stored in UTC"
  falso dal 31/08 · N3 sharing.en.md superata dal giro 01/09, major · N4 alt text gallery
  delete-pair · N5 parametro drawdown `full_history`, info · N6 batch traduzioni mai partito).
- Quick win critical/major aperti da un mese: B3 (`mkdocs --gallery`), B4 (URL 404 riprodotto
  oggi), F4 (link WAC → 404).
- Igiene sito eccellente: 0/526 link rotti, 0 orfane su 287 voci nav, 114/114 screenshot coerenti.
- Peggior sorpresa: N3(b) — l'ultimo owner che lascia un broker **cancella broker+transazioni
  +report** e nessuna pagina utente lo dice.
