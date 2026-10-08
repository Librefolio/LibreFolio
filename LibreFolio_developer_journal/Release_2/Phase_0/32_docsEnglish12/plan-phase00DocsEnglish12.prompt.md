# Phase 0 — 32 · Doc inglese 1.2: allineamento EN ai cambiamenti dalla 1.1

> **Stato: Q1 (`dfcbc0003`), Q2 (`7b06e9f9f`), S12 (`a09220321`), S13 (`dc9209b3e`) e l'onda 1 del feedback (`eee56b42a`, fuso con il treno 14 in `cbfce2475`) sono committati. L'onda 2 (S17, base `cbfce2475`) è stata approvata dal developer il 2026-10-08 alle 17:26: checkpoint pronto e FROZEN. Poi l'onda 3 (admin), dopo la fusione del treno 15.** L'analisi (§1-§2, §4) è stata scritta il
> 2026-10-07 in plan mode su `c9a602f74`, leggendo la punta `d07412899` con `git show`. Poi il
> developer ha fatto il fast-forward del ramo: HEAD = `d07412899`, verificato. Le evidenze grezze
> sono nella sessione Q (`files/`: `audit_brief.md`, `img_refs_report.txt`,
> `translation_debt_baseline.txt`, `app_doc_links.tsv`, i report dei 9 audit).
>
> **Autorizzazione del developer**, inoltrata dal coordinatore (07/10): «Piano approvato dal developer,
> in modalità interattiva». Il piano è stato approvato anche in questa sessione (exit plan mode,
> modalità interattiva).
>
> **Decisioni** (coordinatore, 07/10):
> - **D1, tag Docker.** Il developer: «Correggere il workflow: latest = light».
>   - `release.yml` lo corregge M.
>   - Guida di installazione e CHANGELOG sono già giusti: **non si toccano**.
>   - `developer/docs/release-pipeline.md` passa a **M**.
> - **D2.** Il piano è questo file.
> - **D3.**
>   - **Q1, subito:** utente, admin, teoria e inventario degli screenshot.
>   - **Q2, dopo Q1:** manuale developer, cioè:
>     - la deriva della 1.2;
>     - i due errori precedenti alla 1.1 (LiveTicker, posizione dei toast);
>     - le due pagine nuove (onboarding, sottosistema rischio).
>   - Q2 si può tagliare per la 1.2: **va tenuto separabile**.
> - **D4, screenshot.** Il developer: «organizzati che q scrive delle note placeholder che poi quando
>   abbiamo gli screen vengono sostituite dal codice giusto».
>   - Formato del segnaposto: `<!-- [Screenshot Placeholder: <nome-immagine> — <cosa mostra>] -->`.
>   - I nomi si concordano con M tramite il coordinatore.
>   - La fixture nuova della Dashboard la fornisce il developer, da una build recente. **Nessun dato
>     inventato**: gli shot che ne dipendono restano segnaposto.
> - **D5, N.**
>   - Sì alla riga sulla tab Rischio in `user/brokers/index`, con link alla sezione di N; l'ancora la
>     fornisce il coordinatore.
>   - N non tocca `risk-metrics/*`.
>   - `user/assets/correlation.en.md` è libera.
> - **D6, P.** Sì alla rinomina di `eligible_income_quantity` in `fifo_lot_engine.md`, fuori dalla
>   sezione sul costo (Q2).
> - **L** non tocca `import/index.en.md` né `import/how-to.en.md`.
> - **Richiesta di M, approvata.** Ancore esplicite sui due titoli EN di
>   `user/assets/providers/scheduled-investment`: `#how-value-is-calculated` e
>   `#interest-schedule-editor`, con lo slug attuale.
> - **CHANGELOG.** I 4 cambiamenti mancanti (§1.4) li aggiunge il coordinatore.
>
> **Esclusioni**
> - **P:**
>   - `developer/backend/transactions/wac.md`;
>   - la sezione sul costo della pagina del motore;
>   - `financial-theory` WAC, `book-value`, `period-pnl`, `yield-on-cost`;
>   - `user/dashboard/kpi-cards` e `user/dashboard/positions`;
>   - `user/ai-export/*`;
>   - `developer/frontend/data-quality-banner.md`.
> - **L:** `degiro.en.md`, `brim_plugin_guide.md`, `developer/backend/brim/providers_list.md`.
> - **N:**
>   - la sezione Rischio di `user/dashboard/index.en.md` (prima di toccare la pagina, chiedere al
>     coordinatore);
>   - la frase di `user/brokers/sharing.en.md` intorno a `:76`;
>   - il paragrafo Rischio di `developer/frontend/state/domain-state.md`.
> - **M:** `developer/docs/release-pipeline.md`.
> - **Sempre:** le traduzioni `.it/.fr/.es`, `gallery.spec.ts` e le immagini, `CHANGELOG.md`, il
>   codice applicativo.
>
> **Regole**
> - Le pagine le scrive l'agente `docs-writer`, solo in inglese, **nessuno stamp** delle traduzioni.
> - Gate `mkdocs build` (strict) e `mkdocs check-links` **a ogni lotto**, sempre con
>   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …`.
> - Nessun server: la corsia 6162 / `/tmp/librefolio-r2-q` non serve.
> - Prima del commit: FROZEN e handoff al coordinatore.

## 0. Contesto e baseline

| Voce | Valore |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-ideal-garbanzo` |
| Ramo | `e-alfy-q-doc-inglese-1-2` (rinominato dall'app) |
| HEAD | `d07412899` = `dev_release2` (treno 8), worktree pulito |
| Confronto | `v1.1.0` = `c44aa4053` (2026-09-07); 809 commit; 205 file in `mkdocs_src/docs` |
| Coordinatore | `c8328a01-f208-4ade-a352-0486d1f14de2` |
| Ambiente | `.env`, `node_modules` e `graphify-out/graph.json` assenti, come previsto. La wiki è stata letta pagina per pagina (`sources/mkdocs-audit-2026-08-05`, `sources/kb-03-documentation`) |

**Debito di traduzione già presente prima di Q:**
- 58 pagine EN stale rispetto a `.translate-hashes.json`;
- 22 pagine EN nuove mai tradotte: le nuove `risk-metrics`, tools, correlation, danske-bank, YoC.

Q non lo riduce e non fa stamp: alla fine riporta il debito.

**Link e ancore chiamati dall'app** (54, `app_doc_links.tsv` della sessione). Da non rompere:
- `user/assets/detail/chart/#rolling-return`
- `risk-metrics/benchmark-selection/#the-risk-return-line`
- `risk-metrics/data-quality/#excluded-weight`
- `user/dashboard/kpi-cards/#card-*` (P)
- `user/tools/pac-allocator/`
- `fundamentals/returns/`
- le pagine `risk-metrics/*` e `indicators/*`

Il cancello è `check-links`.

## 1. Analisi (sintesi verificata contro il codice)

Metodo:
- 9 audit read-only per dominio, sulla punta, con prova `doc:riga ↔ codice:riga`.
- Legenda: ✅ corretta · 🟡 incompleta · ❌ sbagliata · ⛔ mancante · n.d. = nessuna doc necessaria.

### 1.1 Errori (❌) — utente e teoria (Q1)

| Pagina | Errore | Prova |
|---|---|---|
| `user/transactions/import/generic-csv:15-18` e `import/how-to:84` | Descrivono una «mappatura manuale delle colonne» che non esiste: le colonne si riconoscono da intestazioni e alias | `broker_generic_csv.py:344-374,476` |
| `user/assets/correlation` | Fasce di ρ sbagliate. Quelle vere: >0,7 alta · 0,3–0,7 · −0,3–0,3 bassa · ≤−0,3 inversa. Le liste tengono solo ρ > 0,7 e ρ ≤ −0,3 | `correlationHelpers.ts:69-84,281-284` |
| `user/assets/correlation` | Il contatore dice «3 selected of 42» | `risk.assetSet.selectedCount` = «{selected} in the analysis, of {total} that can be analysed» |
| `user/assets/correlation` | Rimanda al pannello **+** «descritto sopra», ma non lo descrive mai | `LabAssetPicker.svelte:65` |
| `risk-metrics/correlation:35` | «LibreFolio deliberately does not slice that range into named bands» | `correlationBand()`, `correlationHelpers.ts:78` |
| `user/tools/pac-allocator` | Etichette degli esiti: la pagina dice «Plan found», «Infeasible», «No plan found». La UI dice **Plan available**, **Infeasible with these constraints** (con il badge **Infeasibility proven**), **No plan within the limits** | `en.json` `tools.pacAllocator…result.*` |
| `user/tools/pac-allocator` | Cita una sezione «Assets» che non esiste. L'ordine vero è Key figures → Allocation per Asset → Operational plan → Exposures – ideal vs actual → Balances per Broker and currency → Proof and solver | `result/ResultView.svelte:122-158` |
| `user/assets/detail/index:11-13` | Dice che è in beta tutto il sottosistema Rischio. Oggi lo è solo questa vista | `AssetRiskScenariosView.svelte:62`; CHANGELOG «Risk Analysis leaves beta» |
| `user/assets/detail/signals:44` | I link di teoria non coincidono con quelli dei pulsanti guida, che aprono current-drawdown, beta-active-return, sharpe, volatility, returns | `drawdown.py:71`, `rolling_beta.py:83`, `rolling_sharpe.py:85`, `rolling_volatility.py:68`, `rolling_return.py:68` |
| `user/brokers/index:34` | «four primary tabs»: le schede sono 5, c'è anche Rischio (già nella 1.1) | `brokers/[id]/+page.svelte:226-230` |

### 1.2 Mancanze (⛔) e incompletezze (🟡) — utente, admin, teoria (Q1)

| Pagina | Da aggiungere | Prova |
|---|---|---|
| `user/assets/index` ⛔ | I pannelli *Your assets*, *Other users' assets* e *Watched*: li decide ciò che è detenuto **ora**. La riga dei provider (`:68`) non cita Borsa Italiana | `en.json` 355-359 |
| `user/assets/create-edit` ⛔🟡 | Il confronto con i dati del provider: aspetta la scelta dell'ISIN, mostra icona e nome del tipo, non declassa un sottotipo ETF. La precompilazione del nome da ISIN/ticker. La spiegazione della prima creazione. Il tooltip della valuta. L'inclusione di `assets/distribution-editor-{sector,geographic}`, generati ma mai usati | CHANGELOG e codice di creazione |
| `user/assets/detail/index:21` 🟡 | I modi Prices e Rolling Return | — |
| `user/assets/providers/borsa-italiana` 🟡 | ETF, ETC e risposte senza valuta prendono EUR | `borsa_italiana.py:281-291,562,654` |
| `user/assets/providers/scheduled-investment` | Ancore esplicite `#how-value-is-calculated` e `#interest-schedule-editor` (richiesta di M) | — |
| `user/assets/detail/signals:114` 🟡 | L'avviso di copertura parziale non conta weekend e festivi. Le finestre sono in sessioni | `signal_service.py:761-763,854` |
| `financial-theory/fundamentals/returns` ⛔ | Sezione «Rolling return»: finestra in sessioni e finestra di N giorni di calendario, solo prezzo. Il pulsante 📖 di due segnali apre questa pagina | `calendar_rolling_return.py:125`, `rolling_return.py:68` |
| `risk-metrics/simulation-modes` ⛔🟡 | Perché la simulazione è in beta (finestra rispetto all'orizzonte). Le modalità *Reshuffled history*, *Calm market* e *Prolonged crisis*. La lunghezza del blocco. I due limiti e i loro messaggi | `L4WhatIf.svelte:158`, `risk_plugins/simulation.py:32,150-170` |
| `risk-metrics/data-quality:141` 🟡 | Lo stato *calculation failed* | CHANGELOG «A failure inside a risk calculation…» |
| `user/assets/correlation` 🟡 | Il tono dell'avviso unico (info o ambra) e i badge. Il ritentativo, fino a 3 volte. Il periodo comune a livello di scheda (da verificare) | `riskPanelController` (punta) |
| `risk-metrics/historical-replay`, `hypothetical-shock` 🟡? | Le colonne della tabella (da verificare) | `L4WhatIf` |
| `bollinger-bands`, `donchian-channels` 🟡 (facoltativo) | Il riempimento della banda tra una sessione e l'altra | commit `840bdbc0d` |
| `user/settings/about` ⛔🟡 | Una sezione «Support LibreFolio»: caffè, social, Copy and go, hashtag, nulla pubblicato in automatico. Le *Tool diagnostics* dentro *Plugin diagnostics*. Nel controllo degli aggiornamenti, il rimando alla regola dell'immagine sul registry | `AboutTab.svelte:313,554-581`, `ToolAboutPanel.svelte:339`, `DonationPopupModal.svelte:71` |
| `community/contribute` 🟡 | Le azioni di supporto nell'app e il popup | idem |
| `index.en.md` (home) e `user/index` ⛔ | Tools e PAC allocator. L'header che si nasconde durante lo scorrimento | `Sidebar.svelte:41`, `Header.svelte:33-50` |
| `user/tools/pac-allocator` 🟡 | La privacy mode, da verificare campo per campo. Expand/Collapse all e il dettaglio dell'ordine | `format.ts` |
| `user/settings/preferences` 🟡 | Il menu delle valute mostra solo quelle convertibili | `CurrencySearchSelect.svelte` |
| `admin/settings` e `user/getting-started` 🟡 | Gli utenti già esistenti non passano dall'onboarding. Welcome precompila i default dell'admin | `onboarding_service.py` |
| `user/pwa` 🟡 | L'icona maskable da 512 e lo splash | `frontend/static/icons/` |
| `user/fx/sync` 🟡 | Per le coppie aggiunte prima: scegliere **All** e lanciare **Sync All** una volta | CHANGELOG, sezione FX |
| `user/files/index` ⛔ | La colonna *Uploaded by*, il filtro per avatar o nome, la chiave `?uploader=` | `FilesTable.svelte:61-222`, `files/+page.svelte:57,229` |
| `user/transactions/index` ⛔ | I banner dei todo portano alla riga. La selezione si svuota dopo save, clone, delete, import e link. La diagnostica dei saldi | `TransactionBulkModal.svelte` |
| `user/transactions/import/index` ⛔ | Gli encoding Windows-1252 e Latin-1, con rimando a `brim_plugin_guide` | `_brim_io.py:12` |
| `user/transactions/import/how-to` 🟡 | *Read as* e il set spuntato solo in parte. Tabelle paginate da 5 righe, espansi solo i broker interessati. Il rimbalzo su Review. Danske nella tabella del passo correzioni (`:169-172`). Il match unico selezionato in automatico | `ImportWizardModal.svelte` (punta) |
| `user/transactions/import/generic-csv` 🟡 | Un file per broker, non uno per valuta | — |
| `user/dashboard/charts` 🟡 | Gli anelli del donut *Now*: famiglie dentro, sottotipi fuori (`:246`). La lista dei tipi è incompleta (`:240`) | `allocationRings.ts:11-15` |
| `user/brokers/index` 🟡 | Nella scheda Overview: vista P&L, **Refresh** e page cache. Una riga sulla tab Rischio, con link a N | `brokers/[id]/+page.svelte` |

Corretti, nessuna azione:
- installazione: tag, full e light (dopo D1);
- Tailscale e gzip;
- Danske Bank e report set;
- onboarding lato utente e privacy;
- Growth P&L (testo), Rolling Return (`chart`), frecce tra asset;
- page cache, banner qualità dati, Sync rates;
- indicatori;
- `benchmark-selection`, `data-quality` (calendari, 7 giorni, 30 giorni), `historical-replay`.

### 1.3 Manuale developer (Q2, separabile)

**Errori (❌)**
- `patterns/tool_plugins`: i budget (`schemas/tools.py:79-87`).
- `features/settings`: 3 flow invece di 15 (`onboarding_service.py:27-43`).
- `brim/architecture`: fallback su Generic CSV e mappatura manuale. Mancano report set, combine, gapFix e la nuova rilevazione dei plugin.
- `state/transaction-draft:151-152,198`.
- `core-ui/modals`: le props di ModalBase, il focus trap opzionale, la variante di ConfirmModal.

**Errori precedenti alla 1.1**
- `features/live-ticker`: componente rimosso il 05/08.
- `core-ui/feedback`: posizione dei toast.

**Mancanze e incompletezze della 1.2 (⛔/🟡)**
- Pagine DB: tabelle dell'onboarding, `is_benchmark`, `AssetType`, VARCHAR(32), migrazione 004.
- `styling`: LF Flags.
- `components/index`, `core-ui/index`, `atoms`.
- `brokers/{modals,forms}`.
- `features/transaction-form`: le due gambe di una conversione FX.
- `state/reference-state`.
- `transactions/price_resolver`: OHLC, finestra FX (#30).
- `fifo_lot_engine`: `eligible_income_quantity`.
- `components/charts`, `core-ui/data-table`, `features/import-wizard`.
- `frontend/pages/index`: manca `/tools`; `assets/detail` e `fx/detail` non sono mai generati.
- Indici developer: Tools e registry.
- `features/auth`: autocomplete.
- `pwa`.
- `architecture/security`: escaping.
- AI Export: errori tipizzati.
- `signal_plugin_guide`: matrice degli stati.
- `test-walkthrough`: `--test-port`, `--data-dir`, unità.
- `test-walkthrough/runner_architecture.md:730-739`: 10 link `file:///Users/ea_enel/...` pubblicati nel sito, segnalati da M il 07/10. Vanno sostituiti con percorsi relativi al repo o con link GitHub. Il resto dei `file:///` sta in `release-pipeline.md:3,131`, che è di M. Sweep del 07/10: nessun altro file in `mkdocs_src/docs`.
- `api/overview`: gzip.

**Pagine nuove**
- `developer/frontend/onboarding.md`.
- Sottosistema rischio.
- Le voci di nav corrispondenti.

### 1.4 Note per altri workstream (inoltrate dal coordinatore)

- **P**
  - La fixture `dashboard-report.json` non ha `yield_on_cost`.
  - `fifo_lot_engine.md:329-331`: lo cambia Q in Q2, autorizzato.
- **N**
  - In `dashboard/index:17` la tab Rischio occupa una sola riga.
  - Nessuna pagina descrive la tab Rischio del broker: Q aggiunge una riga in `brokers/index`.
- **L:** il fallback cp1252 è documentato solo nella `brim_plugin_guide`.
- **M:** in `release-pipeline.md` ci sono il tag `vX.Y.Z`, una cache della gallery che non esiste, `--workers 8` e il link `file:///Users/ea_enel/...`.
- **CHANGELOG** (coordinatore), quattro voci mancanti:
  - Tool diagnostics;
  - «Cannot be combined»;
  - «N already in LibreFolio (hidden)»;
  - gli avvisi sulle card dei set.

## 2. Screenshot

### 2.1 Segnaposto: formato e nomi (proposti, da confermare con M tramite il coordinatore)

`<!-- [Screenshot Placeholder: <categoria/nome> — <cosa mostra>] -->`

Quando M produce l'immagine, il segnaposto si sostituisce con il blocco standard
`<div class="screenshot-container">…<img class="gallery-img" data-category="…" data-name="…">`, oppure
con una voce di carosello.

| Nome | Cosa mostra | Pagina | Dipendenze |
|---|---|---|---|
| `tools/hub` | Catalogo Tools con la card PAC: coppia di versioni, Documentation, Refresh | `user/tools/index` | — |
| `tools/pac-step-liquidity` | Passo Liquidity: un contributo nuovo e un conto esterno | `pac-allocator` | dati manuali |
| `tools/pac-step-brokers` | Editor del broker: modo d'ordine, incremento, commissioni, modo di conversione | `pac-allocator` | dati manuali |
| `tools/pac-step-assets` | Passo Assets: prezzo Auto o Manual, badge Copied e Manual | `pac-allocator` | asset seminati |
| `tools/pac-step-routing` | Passo Routing: Allow/Exclude, Minimum/Required/Maximum, Priority, margine | `pac-allocator` | — |
| `tools/pac-step-targets` | Passo Targets: pesi obiettivo, **Balance all** | `pac-allocator` | — |
| `tools/pac-step-review` | Passo Review e **Calculate plan** | `pac-allocator` | — |
| `tools/pac-result` | Esito (Proven optimal, Verified in Decimal), Key figures, Allocation per Asset | `pac-allocator` | calcolo reale |
| `tools/pac-result-plan` | Operational plan: ordini per broker e per rotta, con commissioni | `pac-allocator` | calcolo reale |
| `tools/pac-result-proof` | Pannello Proof and solver | `pac-allocator` | calcolo reale |
| `risk/lab-correlation` | Scheda Correlation: matrice e le due liste di coppie (almeno 4 asset) | `user/assets/correlation` | prezzi seminati |
| `risk/lab-asset-picker` | Pannello **+** aperto: filtri per tipo e valuta, sezione «not analysable» | `correlation` | un asset senza prezzi |
| `risk/lab-hurt-table` | «How much did each of these hurt?» | `correlation` | — |
| `risk/lab-risk-return` | «What did each of these pay for its risk?»: tabella con la riga del benchmark, grafico con il diamante e la linea tratteggiata | `correlation`, `benchmark-selection` | benchmark scelto |
| `risk/lab-benchmark-picker` | *Compared with* aperto, asset non misurabili in una sezione a parte | `correlation` | un asset senza prezzi |
| `risk/lab-notice` | Avviso sopra le sezioni e banner di livello | `correlation`, `data-quality` | asset stale o escluso |
| `risk/lab-replay` | Replay: righe, badge degli asset esclusi, pulsante del periodo comune | `correlation`, `historical-replay` | finestra che taglia un asset |
| `risk/whatif-simulation` | Passo della simulazione con l'avviso beta | `simulation-modes` | **dopo N** |
| `dashboard/growth-pnl-line` | Growth in vista P&L, *Line* | `user/dashboard/charts` | **fixture nuova** |
| `dashboard/growth-pnl-candles` | *Candles* con il selettore dell'ampiezza | `charts` | **fixture nuova** |
| `dashboard/growth-pnl-income` | *Income*, barre mensili | `charts` | **fixture nuova** |
| `dashboard/privacy-masked` | Dashboard con la privacy attiva: occhio nell'header, importi `•••` | `settings/preferences`, `charts` | **fixture nuova** |
| `assets/type-picker-open` | Selettore del tipo aperto, famiglia ETF espansa, icone composte | `user/assets/create-edit` | — |
| `assets/create-provider-compare` | Confronto con i dati del provider dopo la scelta dell'ISIN | `create-edit` | rete → mock |
| `assets/detail-chart-rolling-return` | Modo Rolling Return, finestra 1Y, un asset di confronto | `user/assets/detail/chart` | — |
| `brokers/import-report-set-card` | Card del set Danske: tabelle per ruolo, timeline, *Read as* | `import/danske-bank` | sample `danske_bank-*` |
| `brokers/import-report-set-missing` | Export mancante: suggerimento al passo 1 e avviso sulla card | `danske-bank` | solo `-cash.csv` |
| `brokers/import-report-set-read-as` | Menu *Read as* aperto, più il menu del file (*Remove from the set*) | `danske-bank`, `how-to` | — |
| `brokers/import-report-set-pairing` | Dettaglio dell'analisi: abbinamento titoli ↔ cassa | `danske-bank` | — |
| `brokers/import-wizard-gapfix-step` | Passo *Align with the bank*: card e tabella `gap_fix` | `danske-bank`, `how-to` | trio `gap-*` |
| `files/brim-report-sets` | Pagina File: badge dei set e filtro *Uploaded by* | `user/files/index` | set caricato |
| `transactions/bulk-todo-banner` | Banner dei todo con la riga evidenziata | `user/transactions/index` | consegna dall'import con todo |
| `onboarding/welcome-setup` | Pagina /welcome | `user/getting-started` | utente usa e getta |
| `onboarding/core-tour-step` | Un passo del Core tour | `getting-started` | utente usa e getta |
| `onboarding/contextual-guide` | Una guida contestuale (pagina FX) | `getting-started` | utente usa e getta |
| `settings/onboarding-replay` | Preferences: categoria Onboarding con Replay | `settings/preferences` | — |
| `settings/about-tool-diagnostics` | About → Plugin diagnostics, con *Tool diagnostics* aperto | `settings/about` | — |
| `support/donation-popup` | Popup delle donazioni con le azioni di supporto | `settings/about`, `community/contribute` | utente idoneo al popup |
| `support/social-share-modal` | Modale di condivisione: testo, hashtag, Copy and go | `settings/about` | — |

Non serve un segnaposto per i nomi già presenti nello spec:
- quelli che si aggiornano da soli: `assets/list`, `create-modal`, `detail-chart`, `files/*`, `settings/about`, `brokers/detail`;
- quelli che falliscono online e che ripara M.

`dashboard/data-quality-sync-rates` (pagina `dashboard/index`) aspetta che N abbia chiuso.

### 2.2 Riferimenti rotti (Q2)

`developer/frontend/pages/index.md:102,122` → `assets/detail-chart`, `fx/detail-chart`.

## 3. Passi

I lotti da S1 a S6 lavorano su file disgiunti: i `docs-writer` possono girare in parallelo, ma **i
gate li esegue solo Q**, uno alla volta (un solo comando nella corsia). Dopo ogni lotto:
- `mkdocs build` strict, con il log letto per intero: zero WARNING/ERROR nuovi;
- `mkdocs check-links`.

### Q1

- **S0** ✅ 2026-10-07 — Piano nel journal, HEAD `d07412899` verificato, nomi degli screenshot inviati al coordinatore.
  > **Note implementazione**:
  > - Mandati al coordinatore i 39 nomi di §2.1.
  > - Baseline dei gate, presa prima di ogni modifica alla doc:
  >   - `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build`: exit 0, 0 righe WARNING/ERROR, build in circa 36 s (log in `/tmp/libreFolio_q_build_baseline.log`); il build scrive solo in `mkdocs_src/site/`, che è ignorato da git.
  > - I lotti A–E sono stati lanciati in parallelo su file disgiunti, uno `docs-writer` per lotto, con l'istruzione di non eseguire comandi `dev.py`.
  > - Ancora di N per `user/brokers/index`: il link resta senza ancora, con `<!-- TODO(anchor): #risk-tab, after N -->`. L'ancora si aggiunge all'integrazione di N, su segnale del coordinatore.
  >
  > **⚠️ Fuori pista**:
  > - `… dev.py mkdocs check-links` è **già rosso alla baseline** (exit 1), con 1 link rotto: `user/assets/detail/chart/#rolling-return` esiste in EN, ma manca in IT/FR/ES.
  > - La causa è il debito di traduzione della Rolling Return: le pagine tradotte non hanno quella sezione. La chiama l'app, da `frontend/src/routes/(app)/assets/[id]/+page.svelte:3010`.
  > - La lista delle eccezioni `MKDOCS_ANCHOR_EXCEPTIONS` (in `dev.py`, «deve solo restringersi») e le traduzioni non sono di Q.
  > - Criterio del gate per Q: **nessun link rotto nuovo rispetto alla baseline**. L'ho segnalato al coordinatore; si risolve con il giro di traduzione.
- **S1** ✅ 2026-10-07 — Lotto A, import, transazioni e file:
  - `generic-csv`, `how-to`, `import/index`, `transactions/index`, `files/index`;
  - segnaposto in `danske-bank`.
  > **Note implementazione** (`docs-writer`, verificato da Q):
  > - **generic-csv.** Riscritta la sezione «How It Works»: le colonne si riconoscono da intestazioni e alias (`broker_generic_csv.py:55-123, 336-374, 476-499`). Aggiunto il consiglio «One file per broker — not one file per currency». Ancora `#column-reference`. Corretta anche la riga della valuta: EUR vale solo se manca la colonna; con la cella vuota la riga si salta (`common.py:193-205`).
  > - **how-to.** Corretto il «manually map»; aggiunte le tabelle a 5 file per pagina con solo i broker interessati aperti (`ImportWizardModal.svelte:3333-3338, 4516-4520`), *Read as* e set spuntato in parte (link `danske-bank.md#how-the-set-is-read`), la riga Danske nel passo correzioni, il match unico selezionato da solo, la Review che resta aperta con l'avviso.
  > - **import/index.** Suggerimento su encoding e separatori (`brim_provider.py:86, 206-266, 591-605`). Corretti i due «manual column mapping».
  > - **transactions/index.** Banner dei todo → riga, diagnostica dei saldi, selezione svuotata.
  > - **files/index.** Sezione `#uploaded-by`.
  > - **Segnaposto (9):** `how-to:94,367`; `danske-bank:40,42,54,69,151`; `transactions/index:42`; `files/index:59`.
  >
  > **⚠️ Fuori pista**: il `docs-writer` ha corretto 4 errori fuori dall'audit, ognuno con la prova:
  > - etichette **Keep as recorded** / **Restore** (`en.json:661-697`);
  > - l'avviso «Blocking rows»: **Continue** resta disattivato finché ogni riga non ha una risposta (`ImportWizardModal.svelte:2602, 5304`);
  > - la riga «Composite & Promotion», uscita dalla tabella;
  > - in `transactions/index`: il doppio clic apre la vista in sola lettura e **Edit** sta nel menu contestuale (`TransactionsTable.svelte:898-909, 1024`).
- **S2** ✅ 2026-10-07 — Lotto B, rischio e teoria:
  - `assets/correlation`;
  - `risk-metrics/{correlation,simulation-modes,data-quality,benchmark-selection,historical-replay,hypothetical-shock}`;
  - `fundamentals/returns`, `assets/detail/signals`;
  - facoltativi: `bollinger-bands`, `donchian-channels`.
  > **Note implementazione** (`docs-writer`, verificato da Q):
  > - **user/assets/correlation:**
  >   - «Building the Selection» riscritto: contatore vero, apertura sulle posizioni dell'ultimo giorno, nuove sezioni `#what-can-be-analysed` e `#common-period` (il periodo comune c'è anche a livello di tab), pannello **+** descritto (limite 100: `assetSetSelection.ts:31`);
  >   - fasce di ρ corrette (>0,7 · 0,3–0,7 · −0,3–0,3 · ≤−0,3) e soglie delle liste;
  >   - cinque ordinamenti della matrice;
  >   - avviso con le cause prima, poi i badge delle misure, poi il tono;
  >   - ritentativo fino a 3;
  >   - 7 segnaposto.
  > - **risk-metrics/correlation:** le fasce come aiuto alla lettura; ordinamento per somiglianza (d = 1 − |ρ|).
  > - **simulation-modes**, riscrittura maggiore:
  >   - cinque modalità;
  >   - motivo della beta;
  >   - block bootstrap, con blocco = round(n^⅓) e minimo 2 (`resampling.py:81`);
  >   - regimi prescritti;
  >   - limiti: almeno 30 osservazioni (`simulation.py:193`), Sobol 21 201 (`quant/models.py:21`, 5 posizioni sì e 6 no a 3 650 giorni); numeri ricontrollati da Q;
  >   - l'ancora `#the-process` resta;
  >   - segnaposto `whatif-simulation`.
  > - **data-quality:** stato `failed` = errore non dichiarato («Calculation failed»), distinto da «undefined».
  > - **historical-replay:** colonne (Weight, Return, Contribution, Impact, Effect); segnaposto `lab-replay`.
  > - **hypothetical-shock:** sezione `#what-the-result-shows`; l'audit esiste solo sulla tab dell'asset.
  > - **benchmark-selection:** segnaposto dentro `#the-risk-return-line`, ancora invariata.
  > - **fundamentals/returns:** sezione `#rolling-return`, con sotto-ancore e LaTeX.
  > - **detail/signals:** link 📖 corretti secondo il `docs_path` dei plugin; sessioni; conteggio dei punti esclusi.
  > - **bollinger/donchian:** riempimento tra i giorni di chiusura (`lineChartHelpers.ts`).
  > - **Ancore:** nessun link nuovo da pagine solo-EN verso ancore di pagine tradotte.
  >
  > **⚠️ Fuori pista** (contraddizioni codice ↔ CHANGELOG, inoltrate al coordinatore; Q ha scritto ciò che fa il codice):
  > - «excluded assets as badges» nell'avviso: le cause sono frasi (`RiskPartialNotice.svelte:91`); i badge sono delle misure (`:107`) e, per gli asset, solo nel riquadro del replay. **Verificato da Q.**
  > - «Two simulation settings now explain themselves»: a schermo compaiono solo i messaggi generici `risk.errors.invalid_parameters` / `resource_limit`; la lunghezza del blocco non è un input della UI (solo provenance) ma un parametro dell'API. **Verificato da Q.**
  > - Il pulsante guida del calendar rolling return non apre `returns`: il plugin è nascosto dal catalogo e la modalità del grafico rimanda a `chart#rolling-return`.
  >
  > **Possibili bug trovati leggendo il codice** (non documentati, per i proprietari):
  > - colonna **Weight** della tabella dello shock in Dashboard = somma non pesata delle esposizioni (può superare 100%) → N;
  > - una simulazione oltre il budget viene riportata come «invalid parameters» e non «too large»; ai default (365 giorni, 8 192 percorsi) sono rifiutate 67+ posizioni;
  > - una finestra bootstrap oltre 5 000 osservazioni finirebbe probabilmente in «calculation failed» (solo lettura statica).
- **S3** ✅ 2026-10-07 — Lotto C, asset:
  - `assets/index`, `create-edit`, `detail/index`;
  - `detail/chart` (segnaposto);
  - `providers/borsa-italiana`, `providers/scheduled-investment` (ancore).
  > **Note implementazione** (`docs-writer`, verificato da Q):
  > - **assets/index.** Sezione dei tre pannelli (`assets/+page.svelte:340-363, 1659-1745`; `asset_sources/crud.py:268-284`); Borsa Italiana aggiunta tra i provider.
  > - **create-edit.** Sezione `#provider-data-comparison` (`ProviderComparisonModal.svelte`, `providerComparisonQueue.ts`, `AssetModal.svelte:304-403, 791-841, 1033-1217`), precompilazione del nome da ISIN/ticker (`AssetModal.svelte:719`), aiuto sulla valuta. Carosello **reale** con `assets/distribution-editor-{sector,geographic}`, immagini già generate; tolta la nota «screenshots planned». Ancora `#one-instrument-several-codes`.
  > - **detail/index.** Avviso beta riscritto: resta beta solo questa vista (`AssetRiskScenariosView.svelte:62`). Aggiunti i modi Prices e Rolling Return.
  > - **detail/chart.** Segnaposto sotto l'ancora congelata; affermazioni esistenti verificate, nessuna era sbagliata.
  > - **borsa-italiana.** Sezione «ETFs and ETCs: Currency and Type» (`borsa_italiana.py:276-291, 735, 914-917, 1079-1088`).
  > - **scheduled-investment.** Ancore `#interest-schedule-editor` e `#how-value-is-calculated`, con lo slug invariato (richiesta di M).
  > - **Segnaposto:** `create-edit:103` (`type-picker-open`), il confronto col provider, `chart:24`.
  >
  > **⚠️ Fuori pista**: corretti fuori dall'audit, con la prova:
  > - la ricerca della lista cerca solo nel nome (`+page.svelte:301-303`);
  > - filtro valuta e interruttori Active/Inactive;
  > - etichette **Add Asset**, **Create Asset**, **Create new asset**;
  > - «Provider Config panel» esiste solo per l'FX: per gli asset si passa da **Edit** → **Provider Assignment** (`AssetModal.svelte:2114`).
  >
  > Restano due titoli senza emoji, non toccati perché il loro slug è usato: `create-edit:286`, `scheduled-investment:18`.
- **S4** ✅ 2026-10-07 — Lotto D, Tools e impostazioni:
  - `tools/index`, `tools/pac-allocator`;
  - `settings/about`, `community/contribute`;
  - `index.en.md`, `user/index`;
  - `settings/preferences`, `admin/settings`, `getting-started`;
  - `user/pwa`, `fx/sync`.
  > **Note implementazione** (`docs-writer`, verificato da Q):
  > - **pac-allocator:**
  >   - etichette degli esiti allineate a `en.json` (`result.badges.planAvailable`, `states.infeasible.title`, `badges.infeasibilityProven`, `states.noIncumbent.title`; ricontrollate da Q);
  >   - sezione «How a plan is laid out» nell'ordine vero (`ResultView.svelte:53-60,113-158`), con Expand/Collapse all e **Show provenance**;
  >   - privacy precisata: anche i limiti di rotta e la distanza L2 restano mascherati (`format.ts`, `result/text.ts`);
  >   - tolto il campo «Reference date», che non esiste: la data è sempre oggi (`draft.svelte.ts:365-369`);
  >   - 9 segnaposto.
  > - **tools/index:**
  >   - il pulsante è **Reload** (`ToolsHub.svelte:158-162`);
  >   - la versione di implementazione non compare mai nella UI; la coppia di versioni sta solo sulla card e nell'header dello strumento;
  >   - segnaposto `tools/hub`.
  > - **settings/about:**
  >   - sezioni `#support-librefolio` e `#donation-popup` (fonte `donation_popup_service.py`; lo switch d'ambiente nascosto **non** è documentato, come chiede il codice);
  >   - `#tool-diagnostics`;
  >   - controllo aggiornamenti riscritto, con **Remind me later**;
  >   - 3 segnaposto.
  > - **contribute:** rimando alle azioni di supporto.
  > - **index.en.md:** nuovo blocco «Planning Tools», a **colonna singola centrata** finché manca l'immagine, perché la griglia a 2 colonne `home-custom.css:512-531` avrebbe lasciato mezzo blocco vuoto. Il segnaposto `tools/hub` spiega di tornare al layout `deep-dive reverse` quando arriva l'immagine.
  > - **user/index:** voce Tools e header che si nasconde (`Header.svelte:24-128`).
  > - **preferences:**
  >   - «Base Currency» → **Default Currency**;
  >   - segnaposto `onboarding-replay` e `privacy-masked`.
  > - **admin/settings:** i nuovi utenti partono dai default; gli account precedenti alla 1.2 sono esentati dall'onboarding (`004_release_1_2_0_schema.py:84-93,164-195`).
  > - **getting-started:**
  >   - etichette di Welcome e nota «Already using LibreFolio?»;
  >   - «Customize settings» puntava alle Global Settings dell'admin, ora punta alle Preferences;
  >   - 3 segnaposto.
  > - **pwa:** icone maskable 192/512 e apple-touch 180, verificate sui PNG.
  > - **fx/sync:** consiglio per le coppie precedenti alla 1.2 (`fxCreationSync.ts:111-171`).
  > - **admin/index** (autorizzato in corso d'opera): sezione update-available con le etichette di `en.json` (**New version available**, **Remind me later**, **Skip this version**, **Update available — contact an administrator**); il blocco immagine è rimasto identico.
  >
  > **⚠️ Fuori pista**:
  > - **Valute.** Il menu delle valute in Preferences elenca tutte le valute: la restrizione alle valute convertibili vale solo per i menu della Dashboard e della pagina asset (`dashboard/+page.svelte:851-856`, `AssetPriceSummary.svelte:134`), non per Preferences né per i broker. La mia analisi §1.2 diceva il contrario, e anche `CHANGELOG.md:116` generalizza troppo: segnalato al coordinatore.
  > - **Link dalle pagine solo-EN.** Il build strict valida le ancore anche nelle build tradotte: una pagina solo-EN (es. Tools) che linka un'ancora assente nelle traduzioni (es. `preferences#privacy-mode`) rompe il build. I link dalle pagine Tools restano quindi senza ancora.
- **S5** ✅ 2026-10-07 — Lotto E, dashboard e broker:
  - `dashboard/charts`;
  - `brokers/index` (riga sulla tab Rischio con l'ancora di N).
  > **Note implementazione** (`docs-writer`, verificato da Q):
  > - **charts.** Riga Type riscritta, con il link alle famiglie. Sezione `#allocation-type-rings`: anello interno per le famiglie, esterno per i membri, sfumature, ↳ nel tooltip, legenda (`allocationRings.ts`, `AllocationPieChart.svelte`, `allocationHierarchy.ts`). Il bullet *Now* dice che Geography è una mappa (`AllocationPanel.svelte:143-161`). Segnaposto `privacy-masked:36` (descrizione allineata a quella concordata con M), `growth-pnl-line:113`, `-candles:131`, `-income:169`.
  > - **brokers/index.** Cinque tab; riga Rischio con link `../dashboard/index.md` e `<!-- TODO(anchor): #risk-tab, after N -->` indentato dentro la voce 3, perché un commento a colonna 0 riavvierebbe la numerazione. Growth con Abs/%/P&L. Paragrafo sul ritorno alla pagina e su **Refresh**, con link a `dashboard/index.md#coming-back-and-refreshing`, ancora esplicita già nella punta.
  >
  > **⚠️ Fuori pista**: corretti fuori dall'audit, verificati da Q nel codice:
  > - la riga Geography diceva «primary listing», ma il motore usa la distribuzione geografica (`portfolio_engine.py:1697-1711`);
  > - AI Export non è nella tab Info ma nella toolbar della pagina (`brokers/[id]/+page.svelte:604`).
  >
  > Da comunicare a N: tenere `#coming-back-and-refreshing`.
- **S6** ✅ 2026-10-07 — Lotto F, gallery:
  - `gallery/{index,desktop,mobile}.en.md`;
  - segnaposto per sezione e Features Highlighted.
  > **Note implementazione** (`docs-writer`):
  > - **Segnaposto.** 81 commenti invisibili: 40 in desktop, 40 in mobile, stesso ordine, più 1 in `gallery/index` dopo l'admonition. Nessun contenuto visibile è cambiato (102 righe aggiunte, 0 tolte).
  > - **Sezioni nuove** (titoli e descrizioni dentro i commenti): Onboarding dopo Authentication, Risk Analysis dopo Assets, Tools in fondo; 3 voci P&L per il carosello Portfolio Growth.
  > - **Per chi sostituisce:**
  >   - aggiungere `---` dopo l'ultima voce Onboarding, dopo l'ultima Risk Analysis e prima di `## 🧰 Tools`;
  >   - quando arrivano le immagini P&L, aggiornare la frase del carosello Growth.
  > - **Descrizioni corrette contro il codice:**
  >   - il pulsante dell'hub è **Reload** (`ToolsHub.svelte:158-162`);
  >   - Tool diagnostics mostra una sola versione (`ToolDiagnosticsPanel.svelte:163`);
  >   - c'è un solo link Buy Me a Coffee;
  >   - Welcome imposta lingua, valuta e avatar;
  >   - «PAC — Routing».
  >
  > **⚠️ Fuori pista**:
  > - In `mobile.en.md` 15 voci non hanno la classe `mobile`: sono tutte precedenti alla 1.1 (ultima 2026-09-04), quindi non le tocco; proposta al coordinatore.
  > - Separatori `---` incoerenti, anch'essi precedenti alla 1.1.
  > - Q2: `tool_plugins.en.md:291-294` dice che la versione di implementazione compare in Plugin diagnostics, e non è vero.
  > - `user/tools/index:34,54-56`: girato al lotto D.
  >
  > **Gate intermedio** `interim1` (`/tmp/libreFolio_q_gate.sh interim1`), su A, C, E, F, con B e D ancora in scrittura:
  > - build strict: exit 0, 0 WARNING/ERROR;
  > - check-links: rotto solo il link della baseline, nessuno nuovo;
  > - scope ok, stile ok;
  > - `git diff --check` pulito.
- **S7** ✅ 2026-10-07 — Verifica finale di Q1:
  - build e check-links;
  - `translate-validate --hide-localized` e `translate --dry-run`, solo per il report;
  - `git diff --check`;
  - etichette ricontrollate contro l'`en.json` della punta;
  - handoff, FROZEN.
  > **Note implementazione**:
  > - **Gate finale** `final1`: `/tmp/libreFolio_q_gate.sh final1`, cioè `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build` seguito da `… mkdocs check-links` e dal controllo `q_gate.py`.
  >   - build strict: exit 0, **0 righe WARNING/ERROR** su EN, IT, FR ed ES; le ancore sono validate (`validation.anchors: warn` + `--strict`);
  >   - check-links: exit 1 per il **solo** link rotto già alla baseline (`chart/#rolling-return` in IT/FR/ES), **nessun link rotto nuovo**;
  >   - scope: 40 `.en.md` più questo piano, tutti nel perimetro, nessuna traduzione toccata;
  >   - segnaposto: tutti i 39 nomi nelle pagine attese, più quello di `gallery/index`, formato corretto;
  >   - stile ok: emoji nei titoli H1-H3 nuovi, riga vuota dopo le admonition;
  >   - `git diff --check` pulito.
  > - **Etichette:** verificate dai `docs-writer` sull'`en.json` della punta `d07412899`, che contiene già l'audit i18n di O (treno 8). Q le ha ricontrollate a campione: PAC, privacy, update check.
  > - **Debito di traduzione** (`… mkdocs translate --dry-run`, senza scritture): 93 pagine × 3 lingue = 279 lavori, circa 8,6 M token.
  >   - (A) 13 pagine allineate prima di Q e ora stale. Di queste, `gallery/{desktop,mobile,index}` hanno solo commenti e `scheduled-investment` solo ancore.
  >   - (B) 27 pagine già stale o mai tradotte prima di Q.
  >   - (C) 53 pagine di debito precedente, non toccate da Q.
  >   - Nessuno stamp.
  >   - **Ordine consigliato** per il giro di traduzione:
  >     - tradurre insieme `returns`, `signals` e `chart` (ancora `#rolling-return`), che chiude anche il link rotto della baseline;
  >     - aggiungere le ancore esplicite di `scheduled-investment`, `create-edit` (`#provider-data-comparison`, `#one-instrument-several-codes`), `files/index#uploaded-by` e `dashboard/charts#allocation-type-rings` anche in IT/FR/ES;
  >     - tradurre la gallery solo dopo le immagini di M.
  >   - `translate-validate` non l'ho lanciato: il dry-run basta per misurare il debito, e il giro strutturale si fa dopo la pipeline.
  > - **Corsia e server:** HEAD = `dev_release2` = `d07412899`, la punta non si è mossa. Nessun server avviato: `lsof -nP -iTCP:6162 -sTCP:LISTEN` → exit 1, nessun listener. `site/` è ignorato da git.

### Q2 (dopo Q1, solo con il via libera)

> **Via a Q2** (coordinatore, 07/10 15:09, approvato dal developer): Q1 committato in `dfcbc0003`, albero verificato, worktree pulito.
>
> **Decisioni** (07/10, 15:08 e 15:09):
> - **Stamp:** nessuno, nemmeno per le pagine che cambiano solo per commenti o ancore. Le ancore di `scheduled-investment` arriveranno in IT, FR ed ES con l'allineamento delle traduzioni.
> - **Gallery `mobile.en.md`:** si corregge **all'inizio di Q2**, non in Q1, perché il checkpoint Q1 resti quello verificato.
> - **CHANGELOG:** le 3 frasi che non coincidono col codice e i 4 cambiamenti mancanti li corregge il coordinatore nel treno 9.
> - **Possibili bug** (pesi dello shock, limiti della simulazione): passati al proprietario del rischio.
> - **`#coming-back-and-refreshing`:** esiste anche nella versione di N (`:80`), quindi il link regge.
>
> **Nuova esclusione:** `developer/backend/transactions/fifo_lot_engine.md:9`, il riferimento a `wac_utils.py`, lo corregge P insieme al codice. In quella pagina Q fa **solo** la rinomina di `eligible_income_quantity`.
>
> **Restano escluse:** le pagine dev di P (`wac.md`, sezione costo del motore, `data-quality-banner.md`), di L (`brim_plugin_guide.md`, `providers_list.md`) e di M (`release-pipeline.md`). Resta escluso anche il paragrafo Rischio di `domain-state.md` (N, già nel suo commit).
>
> **Regole:** come in Q1, poi checkpoint, FROZEN e handoff.
>
> **Nav:** i titoli della nav developer non hanno traduzioni (`nav_translations` non contiene nessuna voce developer), quindi le pagine nuove richiedono solo la voce EN in `mkdocs.yml`.
>
> **Lotti Q2** (file disgiunti; `mkdocs.yml` lo tocca un solo lotto):
> - **G, gallery:**
>   - `gallery/mobile.en.md`: classe `mobile` sulle 15 voci;
>   - `gallery/{desktop,mobile}.en.md`: separatori `---`.
> - **H, core UI e componenti:**
>   - `core-ui/{index,atoms,modals,feedback,data-table}.md`;
>   - `components/index.md`, `components/charts.md`, `styling.md`;
>   - `features/{live-ticker,auth}.md`;
>   - `frontend/pwa.md`.
> - **I, feature, stato e pagine:**
>   - `features/{settings,import-wizard,transaction-form}.md`;
>   - `features/brokers/{modals,forms}.md`;
>   - `state/{transaction-draft,reference-state}.md`;
>   - `frontend/pages/index.md`: `/tools` e i riferimenti rotti `assets/detail` e `fx/detail`.
> - **J1, backend e DB:**
>   - `database/{index,users_access,assets_pricing,brokers_transactions}.md`;
>   - `transactions/price_resolver.md`;
>   - `transactions/fifo_lot_engine.md` (solo la rinomina);
>   - `brim/architecture.md`;
>   - `fx/architecture.md`;
>   - `architecture/settings_cache.md`.
> - **J2, pattern, sicurezza, API e test:**
>   - `patterns/{tool_plugins.en,registry_pattern,signal_plugin_guide,ai_export_composition}.md`;
>   - `architecture/security.md`;
>   - `api/overview.md`;
>   - `test-walkthrough/{index,utils,runner_architecture}.md`.
> - **K, pagine nuove e indici:**
>   - `developer/frontend/onboarding.md` (nuova);
>   - `developer/backend/risk/architecture.md` (nuova);
>   - `mkdocs.yml` (solo le voci di nav nuove);
>   - `developer/index.md`, `architecture/overview.md`, `frontend/index.md`.

- **S8a** ✅ 2026-10-07 — Lotto G, gallery.
  > **Note implementazione** (`docs-writer`, verificato da Q):
  > - In `mobile.en.md` le 15 voci senza classe `mobile` ora ce l'hanno: 58 container su 58, nessun altro mancava. Le immagini non cambiano: la classe aggiunge solo la cornice di 400 px. Desktop non toccato (0 modifiche ai container).
  > - Separatori in entrambe le pagine: tolto lo `---` spurio prima di `### 📥 Import`, aggiunto quello prima di `## ⚙️ Settings`.
  > - Segnaposto identici byte per byte a HEAD.
  >
  > **⚠️ Fuori pista**:
  > - Tolto anche un terzo `---`, quello prima del blocco `<style>`: si vedeva come riga orizzontale dentro FX Rates, tra due `###`. Viene dal riordino della v0.9.0 (`3622c2c03`).
  > - Ora ogni `##` ha esattamente un `---` davanti e nessun `###` ne ha uno.
  > - Gli stessi difetti restano nelle traduzioni IT/FR/ES della gallery: 15 container senza `mobile` per ogni mobile tradotta e 3 separatori per pagina. È debito di traduzione meccanico, non toccato.
- **S8** ✅ 2026-10-07 — Errori nella doc developer, compresi quelli precedenti alla 1.1 (§1.3), nei lotti H, I, J1, J2.
  > **Note implementazione** (`docs-writer`, verificato da Q):
  > - **H — core UI:**
  >   - `modals.md`: prop di ModalBase (`trapFocus`/`restoreFocus` opt-in), varianti di ConfirmModal (primary, danger, warning ambra), `results[].action`, flussi di scarto bozza; tolti `DeleteBrokerDialog` come utente di ConfirmModal e `TransactionModal`, che non esiste;
  >   - `feedback.md`: toast in alto al centro, `sanitizeHtml`, link senza swipe (errore precedente alla 1.1);
  >   - `data-table.md`: prop complete (`stickyActions`, `pageSizeOptions`, `alwaysShowPagination`), `navigateToRowId`, avviso che le celle `html` non sono sanificate;
  >   - `live-ticker.md` riscritta come «Live Prices» intorno a `livePriceService` (errore precedente alla 1.1): liste a 30 s, intestazione del grafico a 60 s via client generato, la Dashboard non legge prezzi live;
  >   - `charts.md`: H1 rotto riparato, `needsFullInit`, sottomodi P&L, torta a due anelli;
  >   - `styling.md`: font **LF Flags**, utility, dark mode con varianti `dark:`, non con variabili `--theme-*`;
  >   - `auth.md`: contratto per i password manager; la sezione onboarding ridotta a un rimando a `onboarding.md`; tenuta l'ancora `#post-login-onboarding-gate`;
  >   - `pwa.md`: icone opache, colori di splash e tema, endpoint di condivisione corretto.
  > - **I — feature, stato e pagine:**
  >   - `settings.md`: i 15 flow nei 6 gruppi, **Replay at next trigger** / **Cancel activation**;
  >   - `import-wizard.md`: paginazione a 5 e broker espansi; endpoint per step;
  >   - `transaction-form.md` largamente riscritta, sezione FX con ancore `#fx-conversion` e seguenti;
  >   - `brokers/modals.md`: `BrokerSharingPanel` con Save/Reset (non esiste un pulsante «Undo»);
  >   - `brokers/forms.md`: nomi duplicati e toast;
  >   - `transaction-draft.md`: consegna dall'import validata una volta, **Save All**, banner, `#transactions-selection`;
  >   - `reference-state.md`: `fxRoutesStore`, `#broker-icon-hydration`;
  >   - `pages/index.md`: `/tools`, `/tools/[tool_code]`, `/welcome`; immagini corrette in `detail-chart`; `/fx/[pair]`.
  > - **J1 — backend e DB:**
  >   - pagine DB: tabelle dell'onboarding, `#migrations`, `#enum-column-length`, `is_benchmark`, `#asset-types` (18 valori, raggruppamento per famiglia solo nel frontend);
  >   - `price_resolver.md`: OHLC opzionali;
  >   - `fifo_lot_engine.md`: **solo** la rinomina `eligible_income_quantity`;
  >   - `brim/architecture.md`: Generic CSV, `#report-sets`, sidecar, gapFix, lock;
  >   - `fx/architecture.md`: `#convert-bulk-window` (PR #30), `#portfolio-cache-invalidation`;
  >   - `settings_cache.md`: invalidazioni FX.
  > - **J2 — pattern, sicurezza, API e test:**
  >   - `tool_plugins`: budget veri (`schemas/tools.py:63-108`) e versione mostrata;
  >   - `registry_pattern`: `RiskAnalyticRegistry`, `ToolPluginRegistry`, link al Risk Engine;
  >   - `signal_plugin_guide`: matrice degli stati;
  >   - `ai_export_composition`: «Validation Errors» (niente `assert`, quindi valgono anche con `-O`);
  >   - `security`: «Output Escaping», «Container Image Check», endpoint privati della 1.2 (Risk, Tools, onboarding); `plugin-diagnostics` **autenticato**, per decisione del developer (fix di O nel treno 9); `/ai-export/catalog` pubblico per progetto (verificato con `test_ai_export_api.py:164,197-210`);
  >   - `api/overview`: gzip;
  >   - `api/index`: `/tools`, `/risk` senza «(beta)» generica, ReDoc `/api/v1/redoc`;
  >   - `test-walkthrough`: `#isolated-runtime-lanes`, unità `gate-i18n-usage` e `runtime-isolation`; i 10 `file:///` di `runner_architecture` diventati percorsi inline.
  > - **L — riferimenti a LiveTicker:** `frontend/index`, `scheduler`, `api/overview`, `backend/assets/architecture`; titolo nav «Live Prices».
  >
  > **⚠️ Fuori pista**:
  > - **Molte correzioni fuori audit**, tutte con prova: endpoint, prop, colonne DB, nomi di componenti inesistenti (`Button`, `CashBalanceCard` nel catalogo, `TransactionModal`, `CashTransactionModal` in `brokers/modals`).
  > - **Divergenze AI Export** (riportate, non cambiate, come chiede `ai-development.instructions.md`):
  >   - 34 `assert` restano nel codice delle richieste;
  >   - `ai_export_snapshot.md` non cita il 422 `selection_not_applicable` per un livello di dettaglio non supportato.
- **S9** ✅ 2026-10-07 — Mancanze e incompletezze della 1.2 nella doc developer (§1.3), più la rinomina in `fifo_lot_engine` (D6) e i riferimenti rotti (§2.2).
  > **Note implementazione**: coperte nei lotti H, I, J1, J2 e L (vedi S8). I riferimenti rotti `assets/detail` e `fx/detail` sono stati corretti in `detail-chart` (lotto I).
  >
  > **Backlog precedente alla 1.1**, segnalato e **non** corretto, perché fuori dal perimetro Q2:
  > - `CashBalanceCard` in `features/brokers/{index,cards}.md`;
  > - `CashTransactionModal` in `core-ui/datePickers.md:12,45` e `features/brokers/index.md:29`;
  > - l'esempio JSON di `api/overview.md:157-171` (`as_of_date`, formato `source`, `success_count`/`errors`);
  > - `scheduler.md:69-71` (il job chiama `get_current_prices_bulk`, non `bulk_refresh_prices`);
  > - `external.md` usa `-v`, che non esiste;
  > - `test-walkthrough/index.md` dice «11 categories»;
  > - opzioni del runner non documentate (`--resume`, `--fresh-run`, `--run-status`, `--log-file`, `--no-shared-server`, `--assume-scoped`);
  > - nella mappa di `runner_architecture` mancano 6 moduli;
  > - lato utente: `user/assets/index.en.md` usa ancora «Live Ticker» (titolo con traduzioni).
- **S10** ✅ 2026-10-07 — Pagine nuove, onboarding e rischio, con le loro voci di nav in `mkdocs.yml`.
  > **Note implementazione** (`docs-writer`, verificato da Q):
  > - **K1 — `developer/frontend/onboarding.md`** (nuova, 484 righe):
  >   - contenuto: regole, i 15 flow (tutti alla versione 1), architettura con Mermaid, layout gate, Welcome e intro tour (8 s, `OnboardingIntroScene.svelte:18`), guide contestuali e step-managed, ancore e stall, mobile, regola «due», posizioni nel browser, replay, popup differiti, endpoint, account precedenti alla 1.2 (`004_release_1_2_0_schema.py:171,198`), checklist e test;
  >   - una riga di link aggiunta in `frontend/index.md`.
  >   - La sincronizzazione tra schede passa dall'evento `storage` di `localStorage`: non esiste un `BroadcastChannel`.
  >   - I test e la gallery partono già con l'onboarding completato grazie a `populate_mock_data._grandfather_onboarding_for_test_users`, non grazie alla fixture e2e.
  > - **K2 — `developer/backend/risk/architecture.md`** (nuova, 787 righe):
  >   - contenuto: i cinque chiamanti, mappa dei sorgenti, flusso con Mermaid ELK (`service.py:143-447`), stati del risultato (`schemas/risk.py:90-96`; l'eccezione non dichiarata diventa `execution_failed` loggata senza `str(exc)`, `service.py:291-336`), contratto dei plugin e registry, tabella dei 15 analytic, qualità dati, idoneità e calendario, simulazione e worker (`MAX_SOBOL_DIMENSION`, link a `simulation-modes#limits` invece di ripetere la matematica), API, localizzazione dei warning, contratto frontend (`RISK_DISCARD_ATTEMPTS` = 3), checklist «Adding a Risk Analytic»;
  >   - dei componenti della tab Rischio della Dashboard, che N sta cambiando, solo il minimo.
  > - **Nav** (`mkdocs.yml`):
  >   - `:1015` `"📉 Risk Engine"`, dopo Scheduler;
  >   - `:1062` `"🧭 Onboarding Guides"`, dopo Data Quality Banner;
  >   - solo EN, perché i titoli della nav developer non hanno traduzioni.
  > - **Indici**: `developer/index.md` (Tool Plugins, Risk Engine, Onboarding Guides) e `architecture/overview.md` (nodi Risk Analytics e Tool Plugins nel diagramma, tre punti nei sottosistemi).
  > - **Skill** `.github/skills/onboarding-tools/onboarding-guide/SKILL.md`, concessa dal coordinatore e scritta da Q:
  >   - primo puntatore `developer/frontend/onboarding.md`;
  >   - poi `import-wizard.md#import-guide-wiring` e `#guide-anchor-stall`, e `settings.md` per l'interfaccia del replay;
  >   - tolto `auth.md`;
  >   - lo step 7 punta alla checklist.
  >
  > **⚠️ Fuori pista** (reperti inoltrati al coordinatore):
  > - La migrazione 004 non semina `import.gapFix` per gli account precedenti alla 1.2. Decisione: **resta così**, perché lo step è nuovo anche per loro.
  > - `onboardingTourSurfaces.svelte.ts` e i flag `*TourPreview`, sempre false, sono codice non collegato: vanno nel backlog per knip.
  > - Una finestra bootstrap oltre 5 000 osservazioni (`quant/models.py:70`, con `_build_bootstrap_request` fuori dal `try`) finirebbe in `execution_failed`. L'hanno trovato in modo indipendente i lotti B e K2: passato al proprietario del rischio.
- **S11** ✅ 2026-10-07 — Verifica e handoff di Q2.
  > **Note implementazione**:
  > - **Gate finale** `q2final`: `Q_GATE_ARGS=--q2 /tmp/libreFolio_q_gate.sh q2final`, cioè `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build`, poi `… mkdocs check-links`, poi `q_gate.py --q2`.
  >   - build strict su EN/IT/FR/ES: **0 righe WARNING/ERROR**; l'unico avviso è il banner upstream di Material su MkDocs 2.0, che non è nostro;
  >   - check-links: rotto **solo** il link della baseline (`chart/#rolling-return` in IT/FR/ES), nessuno nuovo;
  >   - scope Q2 pulito: 48 file tracciati più 2 pagine nuove, tutti nel perimetro, compresa la skill concessa;
  >   - stile ok: il controllo delle emoji ora ignora i blocchi di codice;
  >   - `git diff --check` pulito;
  >   - nessun `file:///` rimasto, tranne in `release-pipeline.md` (M).
  > - **Diff**: +2530/−742 su 48 file, più `developer/backend/risk/architecture.md` (787 righe) e `developer/frontend/onboarding.md` (484 righe). Nav: Risk Engine, Onboarding Guides, «Live Ticker» → «Live Prices».
  > - **Base**: HEAD `dfcbc0003` (Q1), `dev_release2` = `d07412899` invariata. Nessun server avviato: porta 6162 libera (`lsof` exit 1).
  > - **Debito di traduzione Q2**:
  >   - nessuno per le pagine developer, che sono solo EN e senza titoli tradotti nella nav;
  >   - la gallery EN cambia ancora, ed era già stale da Q1; le traduzioni della gallery hanno gli stessi 15 container senza `mobile` e gli stessi 3 separatori, un debito meccanico.
  > - **Reperti di codice per i proprietari** (nell'handoff):
  >   - possibile loop di redirect su `/welcome` se si alza la versione di Welcome;
  >   - `BrokerModal` in modifica prende un PATCH `success:false` per un successo;
  >   - docstring superate in `models.py` (`AssetType`) e in `pac_allocator.py` (budget);
  >   - 34 `assert` nell'AI Export.

### Dopo il treno 9

- **S12** ✅ 2026-10-07 — Ancora `#risk-tab` in `user/brokers/index.en.md` (base `9ea2d519b`, che contiene il treno 9 con N).
  > **Note implementazione**:
  > - Il link della voce Risk (`:38`) ora punta a `../dashboard/index.md#risk-tab`, testo «Dashboard Risk Tab». Tolto il commento `<!-- TODO(anchor): #risk-tab, after N -->`.
  > - L'ancora c'è nella pagina EN di N (`user/dashboard/index.en.md:41`, `## 🛡️ Risk Tab {: #risk-tab }`). Non c'è ancora nelle IT/FR/ES, ma il link sta solo nella pagina EN dei broker, le cui traduzioni non lo contengono: le build tradotte non lo validano.
  > - **Frase verificata**: «limited to this broker's holdings» resta vera. La pagina broker monta `RiskLevelsPanel` con `scope={{kind: 'portfolio', broker_ids: [broker.id]}}` (`brokers/[id]/+page.svelte:680-681`), mentre la tab della Dashboard copre tutto il portafoglio (testo di N, `:45`).
  > - **Altre voci che aspettavano il treno 9**: nessuna eseguibile.
  >   - I 40 segnaposto aspettano gli scenari di M: oggi 0/40 nomi sono in `gallery.spec.ts`.
  >   - `#coming-back-and-refreshing` c'è ancora (`dashboard/index.en.md:80`).
  >   - Le pagine solo-EN (`developer/backend/risk/architecture.md`, `user/assets/correlation.en.md`) restano senza `#risk-tab`: lì l'ancora romperebbe le build IT/FR/ES finché le traduzioni della Dashboard non la contengono.
  > - **Riferimenti alle immagini** ricontrollati dopo `c80508be8` (riparazione degli scenari di M): tutti prodotti. I 6 `dashboard/allocation-*` risultano «mancanti» per il mio script solo perché lo spec li costruisce con un template (`${shot}-now`, `${shot}-history`, `gallery.spec.ts:691-699`).
  > - **Gate** `/tmp/libreFolio_q_gate.sh q3anchor`:
  >   - `mkdocs build` strict: exit 0, 0 WARNING/ERROR; l'ancora è validata (`validation.anchors: warn` + `--strict`);
  >   - `check-links`: solo il link rotto della baseline (`chart/#rolling-return` IT/FR/ES);
  >   - scope: 1 pagina, più questo piano;
  >   - `git diff --check` pulito.
  >   - Nessun server: `build` e `check-links` sono statici, non serve la porta 6162.

- **S13** ✅ 2026-10-07 — Limiti della simulazione allineati a `resource_limit` con rimedio (base `9d79c2dbe`, treno 10; entra nel treno 11 con Risk).
  > **Fonti**:
  > - backend nella base: `b72d22ab1` (`_REMEDY_BY_METRIC`, `_resource_limit`, `_refuse_oversized_scope`, `MAX_SIMULATION_ASSETS = 100`);
  > - frasi EN dal ramo di Risk, lette con `git show 3fd9fed9a:frontend/src/lib/i18n/en.json` (`risk.errors.resource_limit_*`) e `…/errorDisplayCode.ts`, senza aprire il suo worktree.
  >
  > **Note implementazione** (`docs-writer`, verificato da Q):
  > - **`simulation-modes.en.md` `#limits`:**
  >   - i righi «Sequence too large» e «Size» sono diventati una riga per rimedio: Path budgets → `paths_or_horizon`, Sequence too large (Sobol) → `horizon_or_sampling`, History too long (bootstrap: più di 5 000 osservazioni o osservazioni × titoli oltre 250 000) → `period`, Too many holdings (oltre 100) → `positions`;
  >   - ogni frase «On screen» è identica byte per byte alla chiave di `3fd9fed9a`;
  >   - invariati, e riverificati: Too little history, Block longer than the history (`invalid_parameters`, `simulation.py:446-457`) e Path count (`invalid_parameters`);
  >   - il paragrafo dei codici dice che ogni limite di dimensione risponde `resource_limit`, che il rimedio sceglie la frase, e che la frase generica resta per un rimedio ignoto;
  >   - il paragrafo delle dimensioni ha conti ricontrollati da Q: 8 192 × 2 442 = 20 004 864; 8 192 × 365 × 67 = 200 335 360 (66 titoli = 197 345 280); 250 000 / 50 = 5 000, / 100 = 2 500; 58 × 365 = 21 170;
  >   - aggiunto che oltre 100 titoli non serve nessuna impostazione, che i titoli esclusi non contano (`data-quality.md#exclusions`) e che i limiti si incontrano uno alla volta.
  > - **`developer/backend/risk/architecture.md`: TOLTA DAL CHECKPOINT** (coordinatore, 08/10 10:17). Alle 17:55 del 07/10 la pagina era stata assegnata a Risk, che l'ha già aggiornata sul suo ramo (`9590a3763`, treno 11): due versioni delle stesse righe avrebbero creato un conflitto certo.
  >   - Ripristino: file riscritto da `git show HEAD:<path>`, senza `git checkout --`; `git diff -- <path>` vuoto.
  >   - La mia versione resta per confronto in `files/risk_architecture.q4mine.md` della sessione.
  >   - Rispetto alla mia, alla versione di Risk mancano cinque cose minori, inviate al coordinatore e non corrette:
  >     - l'ordine dei controlli (rifiuto al primo limite superato; builder prima della richiesta, `validate_resource_budget()` all'inizio di `run_simulation()`);
  >     - che il tetto dei 100 titoli conta solo quelli con una serie di rendimenti utilizzabile, cioè gli esclusi non contano, come dice la pagina utente;
  >     - il passaggio `SimulationResourceLimitError` → `_resource_limit()`;
  >     - che il `resource_limit` dell'ottimizzazione porta solo `actual` e `limit`;
  >     - che la Sobol la controlla il builder GBM e non genericamente «the plugin».
  >
  > **⚠️ Fuori pista**:
  > - **Conto sbagliato nel brief di Q** (8 192 × 365 × 67 indicato come 200 343 040): il writer ha scritto quello giusto, 200 335 360.
  > - **Pagina developer non prevista:** il writer ha trovato superata la pagina developer del rischio. Corretta e poi **tolta** dal checkpoint, perché era già stata assegnata a Risk (vedi sopra).
  > - **Frasi in anticipo:** `simulation-modes.en.md` descrive frasi del ramo di Risk che arrivano col treno 11; fino ad allora il frontend della base mostra solo la frase generica.
  >
  > **Gate** `Q_GATE_ARGS=--q4 /tmp/libreFolio_q_gate.sh q4limits2`, rilanciato dopo aver tolto la pagina developer:
  > - build strict: exit 0, 0 WARNING/ERROR; le ancore `#limits` e `data-quality.md#exclusions` sono validate;
  > - `check-links`: solo il link rotto della baseline;
  > - scope: `simulation-modes.en.md`, più questo piano; `git diff -- developer/backend/risk/architecture.md` è vuoto;
  > - `git diff --check` pulito;
  > - nessun server.

### Feedback del developer

- **S14** ✅ 2026-10-08 — Primo giro di feedback diretto del developer, su base `ffa72cc2b` (treno 12).
  > **Feedback** (developer, 08/10 12:22): «riguardo a mkdocs serve, sei l'unica quindi la puoi usare»; «tools: fino a opening tool come capitolo va bene quello che viene dopo è da manuale dev se fosse, qui è la sezione utente, deve essere semplice, e la parte del documentation and language mi pare errata, visto che quando poi avviamo la traduzione ci saranno le guide in tutte le linghe»; «riguardo a pac, non farei una tabella con gli step, ma per ogni step una sezione, così compare anche nella tabella dei contenuti, e per formule e numeri cercherei di usare latex». Il coordinatore ha confermato la precedenza (12:25).
  >
  > **Note implementazione** (2 `docs-writer`, verificato da Q):
  > - **Server**: anteprima statica sulla 6162 spenta; `dev.py mkdocs serve` sulla 6042 (`http://127.0.0.1:6042/LibreFolio/`), con live reload, autorizzato dal developer.
  > - **`user/tools/index.en.md`**:
  >   - resta tutto fino a «🖱️ Opening a tool»;
  >   - via le otto sezioni tecniche, sostituite da «ℹ️ Good to know», 3 punti semplici: un tool non cambia il portafoglio; server occupato o tempo scaduto non dicono nulla sui tuoi numeri; se un tool manca, Plugin diagnostics;
  >   - tolta «Documentation and language», che era sbagliata.
  > - **`developer/architecture/patterns/tool_plugins.en.md`**: ha ricevuto solo i fatti che mancavano, ciascuno nella sua sezione esistente:
  >   - lettura esplicita dei dati prima del calcolo;
  >   - 401 per un account disabilitato;
  >   - `version_mismatch` prima della coda;
  >   - ammissione per batch;
  >   - codici `retryable`;
  >   - contatori da zero per processo;
  >   - semantica di `execution_ms` e `server_processing_ms`;
  >   - tabella dei motivi di indisponibilità;
  >   - link alla documentazione nella lingua dell'app.
  > - **`user/settings/about.en.md`** (~:104): non rimanda più alla spiegazione dei contatori, che non c'è più; ora spiega in una frase che **Completed jobs** comprende già i **Failed jobs**.
  > - **`user/tools/pac-allocator/index.en.md`**:
  >   - la tabella degli step diventa **una sezione H3 per step**, che compare nell'indice: 🎬 Scenario, 💰 Liquidity, 🏦 Brokers, 💼 Assets, 🔀 Routing, ⚖️ Targets, 💱 FX, 🧠 Strategy, ✅ Review;
  >   - LaTeX verificato nel codice: incremento $q = k\,\Delta$; commissione $f + \min(\max(r A, f_{\min}), f_{\max})$ (`numeric.py:265-289`); margine $p(1+m)$; conversione $D\,x(1-s)$ (`numeric.py:292-322`); target e **Balance all**; **Copy current distribution**; distanza $D = \sum_i (V_i - w_i R)^2$, **senza radice**, in denaro al quadrato (`evaluator.py:3484-3487`, `objectives.py:118-140`);
  >   - i 6 segnaposto degli step, identici byte per byte, stanno nelle sezioni giuste, come M ha chiesto per il G6;
  >   - l'ancora `#reading-the-result` resta;
  >   - frase sugli errori di piattaforma resa semplice.
  > - **`index.en.md`** (home, Planning Tools): «in whole units, fractions, or amounts» → «in whole units or by amount, where an amount can buy a fraction of a unit».
  >
  > **⚠️ Fuori pista** (reperto di codice, inoltrato):
  > - L'aiuto `tools.pacAllocator.planner.brokers.incrementHelp` dice «By number of units: … 0.001 = fractions down to three decimals». Ma il codice rifiuta un incremento non intero in modalità a unità: `request.ts:190` «Whole-unit mode: the step must be a whole number of units», più `schemas/pac_allocator.py:48,233-236,386` ed `evaluator.py:326-331`.
  > - La doc segue il codice: unità intere; le frazioni solo per importo.
  > - Anche `CHANGELOG.md:18` («in whole or fractional units, or in amounts») è da riformulare, o va cambiato il codice: decide il developer.
  >
  > **Gate** `Q_GATE_ARGS=--fb /tmp/libreFolio_q_gate.sh fb1`:
  > - build strict: exit 0, 0 WARNING/ERROR;
  > - `check-links`: solo il link rotto della baseline;
  > - scope: 5 pagine più questo piano;
  > - stile ok (il controllo ora riconosce `ℹ️`);
  > - `git diff --check` pulito.
  >
  > Checkpoint e porta 6042 libera rinviati a fine giro di review, perché il developer sta ancora guardando l'anteprima.
  >
  > **Seguito** (developer, 08/10 12:58): «tool ok, riguardo pack allocator togli il riferimento alla versione, non serve».
  > - Via la coppia di versioni, la nota sulla versione della UI e la menzione `Backend/API`.
  > - Le tre frasi «this version» diventano «yet».
  > - Elenco delle pagine cambiate dalla 1.1 rimandato in chat, con gli URL della 6042. I treni 11-12 hanno aggiunto `admin/cli_tools`, `admin/docker_advanced` e `user/settings/profile`.

- **S15** ✅ 2026-10-08 — Correlation e Rischio della Dashboard: una pagina per blocchi, con la stessa struttura.
  > **Feedback** (developer, 08/10 13:04): «in correlation il problema è che fai un unica pagina per tutto, dovrebbe essere invece una pagina che spiega i vari blocchi, mettendoci magari anche uno screen e dice quali strumenti vi sono riportati, e per gli strumenti un link a delle pagine dedicate in teoria matematica, una struttura comune anche in rischio dashboard».
  >
  > **Via libera del coordinatore** (13:10):
  > - Q scrive la pagina nuova `user/dashboard/risk.en.md`.
  > - Riduce `## 🛡️ Risk Tab {: #risk-tab }` di `user/dashboard/index.en.md` a un sommario, **tenendo l'ancora**: la linkano `:17` e `brokers/index.en.md:38`.
  > - Aggiunge la voce di nav e l'etichetta «Risk» nei blocchi `nav_translations` it/fr/es.
  > - Nomi delle schermate confermati: `dashboard/risk-hurt`, `dashboard/risk-diversification`, `dashboard/risk-paid`, `dashboard/risk-whatif`, oltre a `risk/whatif-simulation`.
  > - N e Risk sono parcheggiati, senza lavoro aperto.
  >
  > In corso: un `docs-writer` su `user/assets/correlation.en.md`, che deve conservare `#correlation`, `#what-did-each-pay`, `#what-if` e i 7 segnaposto `risk/lab-*`; un altro su `dashboard/risk.en.md`, `dashboard/index.en.md#risk-tab` e `mkdocs.yml`.
  >
  > **Note implementazione, correlation, primo passaggio** (13:30):
  > - **Struttura.** La pagina è riscritta per blocchi: Selezione, Correlazione, «Hurt», «Pay», «What if», Avvisi. Ogni blocco ha lo stesso schema: cosa risponde, segnaposto, **Tools shown** con i link alla teoria verificati nel codice, **How to read it**.
  > - **Segnaposto.** I 7 segnaposto sono identici byte per byte e nello stesso ordine.
  > - **Ancore.** Restano `#correlation`, `#what-did-each-pay` e `#what-if`. Le 11 ancore tolte non sono linkate da nessuna parte: verificato con grep su tutte le lingue, su `frontend/src` e su `backend/app`.
  > - **Lunghezza.** Da 7303 a 5273 parole: ancora un muro di testo, rispetto alla direttiva delle 13:08 (S16).
  >
  > **⚠️ Fuori pista: secondo passaggio.**
  > - **Correlation.** Obiettivo circa 1500-2000 parole. Le regole e i meccanismi vanno in una pagina dev **nuova**, `developer/frontend/components/features/risk-lab.md`; la voce di nav la aggiunge Q. Non duplica `developer/backend/risk/architecture.md`, che è di Risk e non si tocca: ci rimanda. I due link alla Dashboard puntano ora a `../dashboard/risk.md`.
  > - **Dashboard Risk.** Al writer ho mandato gli stessi criteri. Non tocca `risk-lab.md`: elenca i fatti spostati, e la sezione «Dashboard Risk tab» si aggiunge dopo.
  >
  > **Reperto di codice**, da passare al coordinatore: la docstring di `AssetSetRiskReturnSection.svelte` dice ancora «there is no picker here», ma il picker del benchmark ora è disegnato in quella sezione.
  >
  > **Note implementazione, Dashboard Risk** (13:45):
  > - **`user/dashboard/risk.en.md`**, pagina nuova: 1349 parole visibili (1766 con `wc -w`, dopo un primo passaggio da 2722). Ha lo stesso schema per blocchi di correlation: Hurt, Diversification, Being Paid, What If, Notices, poi Good to Know e Related.
  >   - Ci sono i 4 segnaposto `dashboard/risk-*` più `risk/whatif-simulation`, e una sola admonition, il beta della simulazione.
  >   - Ancore: `#how-much-can-it-hurt`, `#diversification`, `#being-paid`, `#what-if`, `#notices`, `#good-to-know`, `#related`.
  > - **`user/dashboard/index.en.md`**: `## 🛡️ Risk Tab {: #risk-tab }` diventa un sommario di 3 frasi con il link a `risk.md`, e l'ancora resta.
  > - **`mkdocs.yml`**: la voce `Risk: user/dashboard/risk.md` nel gruppo Dashboard, più `Risk:` nei blocchi `nav_translations`: Rischio, Risque, Riesgo.
  > - **Fatti spostati.** Il writer ne ha elencati 32, con file:riga, per la sezione «Dashboard Risk tab» di `risk-lab.md`. Si aggiungono dopo che il writer di correlation ha creato il file.
  >
  > **Note implementazione, correlation, secondo passaggio** (13:55):
  > - **`user/assets/correlation.en.md`**: da 5273 a 1999 parole, di cui 1706 di prosa più i 7 segnaposto, identici byte per byte.
  >   - Una sola admonition: il rendimento medio annuo non è il rendimento vissuto.
  >   - L'H3 `#what-can-be-analysed` confluisce nel blocco della selezione: nessuno lo linka.
  >   - I link alla Dashboard puntano a `../dashboard/risk.md`.
  >   - In Related, una riga «Technical details».
  > - **`developer/frontend/components/features/risk-lab.md`**, nuova, 2336 parole, con le citazioni file:riga controllate da script. Sezioni: selezione all'apertura; azioni di massa (rimanda a `core-ui/select.md`); idoneità nel lab; richieste e finestra condivisa; correlazione (soglie 0.7, −0.3, 0.9 e −0.7, limiti di 5 o 8 coppie); tabella delle perdite; rischio e rendimento (regola dei sette giorni); replay; avvisi e cornici.
  >   - Per il backend rimanda ad `architecture.md` di Risk, senza duplicarlo.
  > - **Fatti da Q:**
  >   - nav `- Risk UI: …/features/risk-lab.md` dopo «Lots Analysis», e `- Danske Bank Importer: developer/backend/brim/danske_bank.md` dopo «Generic CSV Provider»;
  >   - una riga «Risk UI» nella tabella delle feature di `developer/frontend/components/index.md`;
  >   - `core-ui/select.md:424`: `BenchmarkSelect` **usa già** `AssetPickerPanel mode="single"` (`BenchmarkSelect.svelte:197`); resta in programma solo il segnale Asset Comparison.
  > - **In corso:** il writer della Dashboard Risk aggiunge `## 🛡️ Dashboard Risk Tab {: #dashboard-risk-tab }` a `risk-lab.md`, con rimandi e non duplicati, e cambia l'H1 in «Risk UI: Correlation and Dashboard Risk Tabs».

- **S16** 🟡 2026-10-08 (onda 1 ✅; onde 2-3 da fare) — Semplificazione di tutta la doc utente: il tecnico va nel manuale dev.
  > **Feedback** (developer, 08/10 13:08): «in danske bank il titolo va a capo, ma vedo che lo fa con anche le altre banche, Poi è un muro di testo, troppi dettagli tecnici, e te lo dico, vale per tutto, non solo per questa pagina, quindi riguarda anche le altre e cerca di semplificare e scorporare, mettere in dev manual le cose tecniche e qui le info utili».
  >
  > **Note implementazione**:
  > - **Titolo a capo.** In `mkdocs_src/docs/static/extra.css`, sotto i 76.1875em, il media query metteva l'H1 flex in `flex-direction: column`, quindi emoji, favicon e nome finivano su tre righe. Ora è `row` con `flex-wrap: wrap`. Verificato nel browser a 1280 px: una riga.
  >   - Il file è condiviso, ma nessuno lo ha aperto: il coordinatore lo assegna a Q fino al checkpoint (13:14). Va **dichiarato** nel checkpoint.
  > - **Misura della densità tecnica** delle pagine utente e admin (parole, code span, nomi interni): sessione Q, `files/user_density.txt`.
  > - **Brief comune** per i writer: sessione Q, `files/simplify_brief.md`.
  >   - La pagina utente dice cosa vedi, cosa fai, cosa controllare, con le etichette esatte della UI.
  >   - Il tecnico verificato nel codice va nella pagina dev giusta, aggiungendo solo i fatti mancanti.
  >   - Restano ancore, schermate, segnaposto e admonition utili.
  > - **Onda 1**, 4 `docs-writer` su file disgiunti:
  >   - `import/danske-bank`, più la pagina dev **nuova** `developer/backend/brim/danske_bank.md`, la cui voce di nav la aggiunge Q;
  >   - `import/how-to`, `import/index` e `import/generic-csv`, verso `import-wizard.md` e `brim/generic_csv.md`;
  >   - `dashboard/charts`, verso il `charts.md` del frontend;
  >   - `assets/create-edit`, verso `asset-identity.md` e `backend/assets/architecture.md`.
  >   - Nel checkpoint dell'onda 1 entrano anche S14, S15, about, home e CSS.
  > - **Onda 2**: preferences, about, getting-started, asset (index, detail/chart, detail/signals), provider asset e FX, files, transactions, credit_agricole, installation e home. In più le pagine di P (`dashboard/kpi-cards`, `dashboard/positions`, `ai-export/*`) e di L (`import/degiro`), che il coordinatore assegna a Q per questa semplificazione (13:14).
  >   - Per `ai-export/**` e per le pagine dev `ai_export_*.md` i writer leggono prima `.github/instructions/ai-development.instructions.md`.
  >   - `brim_plugin_guide` e `providers_list` restano esclusi: O ci ha appena committato, per il treno 14.
  > - **Onda 3**: le pagine admin. Restano i comandi; gli interni vanno nelle pagine dev.
  >
  > **⚠️ Fuori pista: treno 13** (`374381e27`, 13:14, non ancora nella base `ffa72cc2b`). Ha cambiato 5 pagine di Q:
  > - `danske-bank`: 5 segnaposto diventano immagini; «a **Deposit** or a **Withdrawal**»;
  > - `how-to`: 3 immagini, tra cui `brokers/import-report-set-file-menu`, che è nuova;
  > - `files/index` e `transactions/index`: 1 immagine ciascuna (M, G3);
  > - `dashboard/charts`: il punto «How the periods are labelled» di I.
  > - Anche il codice dei grafici è cambiato (`GrowthChart.svelte`, `growthLadderAxis.ts`): etichette dell'asse per periodo, e i dividendi nelle barre Income ora sono **oro** (erano ciano). Nessuna pagina EN nomina quel colore.
  >
  > Per regola del coordinatore, i writer partono dalla versione del treno 13 (`git show 374381e27:<percorso>`) e la portano nelle riscritture. Il punto di I va nel manuale dev, con i fatti intatti.
  >
  > Conflitti attesi quando il target sarà fuso nel ramo di Q, dopo il checkpoint: `danske-bank.en.md`, `how-to.en.md` e `charts.en.md`. Risoluzione semantica: tenere la versione di Q, che contiene già il treno 13, e verificarlo.
  >
  > **Checkpoint per onda** (proposta del coordinatore, 13:14): il checkpoint dell'onda 1 si chiude quando il developer la approva; poi il target viene fuso nel ramo di Q e si parte con l'onda 2. Se il developer preferisce un checkpoint unico, va detto al coordinatore.
  >
  > **Note implementazione, onda 1**:
  > - **`user/assets/create-edit.en.md`**: da 3082 a 1822 parole, organizzata per compiti: crea, scegli il tipo, collega un provider, controlla i dati del provider, modifica, identificatori, distribuzioni, unisci duplicati.
  >   - Le 6 ancore esplicite restano. Le 4 tolte sono automatiche e nessuno le linka.
  >   - Via i due diagrammi Mermaid; le admonition passano da 9 a 2.
  >   - **Fatti nuovi**, verificati anche da Q:
  >     - **Units per single price**, con 100 proposto per i bond (`AssetModal.svelte:909-918`);
  >     - **Name** unico;
  >     - togliere la spunta a **No Provider** prima di impostare un provider a mano;
  >     - cambiare la **Currency** cancella prezzi ed eventi, con il dialogo **Delete & Change Currency** (`en.json:43`).
  > - **`developer/frontend/components/features/asset-identity.md`**: le regole delle righe di confronto (`isFamilyOnlyProposal()`), la regola dell'avviso di fusione dei duplicati, e una precisazione sulla fusione dei codici.
  > - **`developer/backend/assets/architecture.md`**:
  >   - **errore corretto**: la prova della storia scarica **7** giorni, non 30 (`provider_management.py:379`);
  >   - le operazioni usate da **Test Configuration** e da **Ask Provider**, e i fallimenti morbidi.
  > - **`developer/architecture/database/assets_pricing.md`** (Q): ospita l'unico fatto rimasto orfano, cioè le distribuzioni salvate come frazioni.
  >   - La UI lavora in percento, con tolleranza 0.005 punti, e divide per 100 (`DistributionEditor.svelte:132,192`, `DistributionDataImportModal.svelte:35,42`).
  >   - Il backend rifiuta uno scarto oltre 0.01, poi rinormalizza, quantizza a 4 decimali e mette il residuo sul peso minore (`schemas/assets.py:352-431`).
  >
  > **Reperto di codice**, da passare al coordinatore: la docstring di `BaseDistribution` (`schemas/assets.py:341,359`) dice tolleranza 1e-6, ma il codice usa `Decimal("0.01")` (`:398`).
  >
  > - **`user/dashboard/charts.en.md`**: da 4850 parole (versione del treno 13) a 2268, a blocchi.
  >   - Le 8 ancore esplicite restano. Le automatiche tolte non le linka nessuno, e l'app non linka la pagina.
  >   - Admonition da 8 a 2: «Highs and lows are hypothetical» e «purchase bars ≠ KPI».
  >   - Carousel e segnaposto sono identici byte per byte.
  >   - **Correzioni dal codice:** le etichette delle tab sono **By Type**, **By Sector** e **Geographic**; **Now** e **History** sono pulsanti a icona; via «All series start at 0%», perché il ROI non parte forzato da 0; il banner si chiama **MWRR chart unavailable**.
  >   - Del punto di I resta una frase («Axis labels»).
  > - **`developer/frontend/components/charts.md`**: da 1414 a 2576 parole, solo fatti nuovi.
  >   - Il punto di I c'è per intero: etichette dei periodi, rotazione tutto o niente, diradamento contato dall'ultima, chiavi `dashboard.pnlAxisQuarter` e `dashboard.pnlAxisWithYear`. È verificato su `git show 374381e27:` di `growthLadderAxis.ts` e `GrowthChart.svelte`.
  >   - Anche: le regole delle larghezze e delle candele su più giorni, la legenda e le fonti di Income, i dettagli delle torte, il ridisegno in privacy.
  >   - Corretta una riga superata: anche l'ultimo periodo può essere sbiadito, non solo il primo.
  >   - Il colore dei dividendi non è nominato in nessuna delle due pagine.
  > - **`user/transactions/import/danske-bank.en.md`**: da 3753 parole (versione del treno 13) a 1865, di cui 1471 di prosa.
  >   - Indice: export, upload, file mancante, come si legge il set, import annuale, cosa si importa, commissioni, scissioni, primo import, controllo di fine periodo, gap, limiti.
  >   - Le 5 immagini del treno 13 sono identiche byte per byte; «a **Deposit** or a **Withdrawal**».
  >   - Le ancore linkate da altre pagine (`#how-the-set-is-read`, `#first-import-align-with-the-bank`) restano, insieme a `#gaps`, `#demergers` e `#limits`.
  > - **`developer/backend/brim/danske_bank.md`**, nuova, 3634 parole: accoppiamento titoli e cassa, file combinato, punti di partenza e gap, correzioni `gap_fix` (`DEPOSIT` o `WITHDRAWAL`), controllo di fine periodo, stima delle commissioni, scissioni. Voce di nav aggiunta da Q.
  > - **`user/transactions/import/how-to.en.md`**: da 3890 parole leggibili a 1714. Ogni step dice cosa vedi, cosa decidi e cosa fare se qualcosa va storto.
  >   - Le 3 immagini del treno 13 sono identiche byte per byte, tra cui `brokers/import-report-set-file-menu`, che è nuova.
  >   - Le admonition sono 0.
  >   - **Correzioni dal codice:** i nomi dello stepper sono Upload / Select Files / Parse / Review; le colonne della review non includono Price, Net Amount né Fees; i badge reali dicono **⚠ Likely dup**; ci sono **Set opening to ‹date›** e **Recalculate by priority**; la pagina Files non ha un'azione di re-import; il flusso nelle impostazioni si chiama **Import guide**.
  >   - Ancore: `#guided-first-import` resta; nuove le esplicite `#review`, `#duplicates` e `#opening-date`, per i link dell'index.
  > - **`user/transactions/import/index.en.md`**: da 1511 parole leggibili a 730.
  >   - Via la tabella «Importer Capabilities», che aveva celle **sbagliate**: IBKR non legge dividendi né depositi, Coinbase salta send e receive.
  >   - Le card mostrano stato ed export da fare; Degiro chiede l'Account Statement.
  >   - Le ancore `#asset-mapping`, `#duplicate-detection` e `#before-opening` restano.
  > - **`user/transactions/import/generic-csv.en.md`**: da 956 a 753 parole.
  >   - La tabella `#column-reference` è identica byte per byte.
  >   - Nuova la nota che le righe ADJUSTMENT chiedono il costo di una unità.
  > - **Pagine dev, solo fatti nuovi:**
  >   - `import-wizard.md`: la regola `pickBestPlugin`, cosa fanno Confirm e Confirm all, quali righe vanno nelle Corrections;
  >   - `brim/generic_csv.md`: rilevamento delle colonne (maiuscole e spazi ignorati, vince la colonna più a sinistra, rifiuto HTTP 400) e un paragrafo sugli errori di riga.
  >
  > **Gate `fb2`** (`Q_GATE_ARGS=--fb /tmp/libreFolio_q_gate.sh fb2`):
  > - scope ok (27 percorsi), segnaposto ok, stile ok, `check-links` con solo il link rotto della baseline, `git diff --check` pulito;
  > - build strict: exit 1, con 2 WARNING.
  >   - `risk-lab.md#dashboard-risk-tab`: la sezione la sta ancora scrivendo il writer della Dashboard Risk.
  >   - **⚠️ Fuori pista:** `danske-bank.en.md` linkava `files/index.md#report-sets`, che manca in IT/FR/ES (la pagina EN-only si costruisce anche lì). Riportato a `#broker-reports`, che esiste in tutte le lingue e che usava il treno 13.
  >
  > **Reperti per altri** (inoltrati al coordinatore):
  > - `providers_list.md:7` (L) dice che IBKR legge «standard IBKR activity reports», ma il parser richiede le colonne Flex Query `Buy/Sell`, `TradeDate`, `ISIN` e `IBCommission` (`broker_ibkr.py:131`).
  > - La docstring di `broker_coinbase.py:16-19` è superata: staking e rewards sono ADJUSTMENT (`:68-70`), send e receive vengono saltati (`:76-77`).
  > - La schermata `brokers/import-report-set-file-menu` (M, G3) mostra **Read alone with Generic CSV** su un file di cassa Danske, preparato apposta per il test. Ma la pagina Danske dice che un export reale non lo offre mai.
  > - Per l'onda 2, pagine di Q: `directa` dice Beta, mentre l'index e `providers_list` dicono Stable; `ibkr` parte dall'Activity Statement; `preferences` dice «Import Wizard», ma l'etichetta è «Import guide».
  >
  > **Seguito** (14:10-14:20):
  > - **Smistamento del coordinatore.** La riga IBKR di `providers_list.md` passa a Q: L è parcheggiato, il file non è cambiato dopo la base, e il resto delle pagine dev BRIM resta di L. Lo stato di Directa lo decide il developer. Le docstring vanno nel backlog del coordinatore.
  > - **Developer** (ask_user): «Directa = **Stable**».
  >   - `directa.en.md`: tolta l'admonition «Beta». Le pagine Stable, come Crédit Agricole, non ne hanno.
  >   - La card dell'index e `providers_list.md:10` dicevano già Stable.
  >   - Le traduzioni dicono ancora Beta: è debito di traduzione.
  > - **IBKR**:
  >   - `providers_list.md:7`: Activity Flex Query in CSV, con le intestazioni quotate `Buy/Sell`, `TradeDate`, `ISIN` e `IBCommission` sulla prima riga (`can_parse`, `broker_ibkr.py:131`). Legge acquisti e vendite con ISIN e commissioni come `FEE`; salta le righe senza ISIN; niente dividendi, tasse né movimenti di cassa.
  >   - **⚠️ Fuori pista:** corretta anche la pagina utente `ibkr.en.md`, per lo stesso reperto e perché il rischio per l'utente è alto. Diceva di esportare l'Activity Statement, che il parser non legge, e prometteva dividendi, tasse e depositi.
  >   - Ora la pagina chiede una Flex Query con la sola sezione Trades e le 8 colonne del parser, in CSV con data `yyyyMMdd`. Dice cosa si importa: BUY e SELL; la FEE sullo stesso asset, in `IBCommissionCurrency`; USD se `CurrencyPrimary` è vuota.
  >   - Tolti il vecchio segnaposto del portale, superato, e l'avvertenza sulla lingua. Nessun link punta alle ancore tolte.
  > - **M** (14:15) rifà `brokers/import-report-set-file-menu` con l'export di cassa Danske reale: Preview, Remove from the set, Delete, senza «Read alone». Q ha aggiunto il segnaposto con lo stesso nome in `danske-bank.en.md#how-the-set-is-read`, dopo `-read-as`, come M ha proposto.
  > - **Reperto per Risk:** la tabella «Who Calls It» di `developer/backend/risk/architecture.md` dice che la Dashboard manda tutti i broker accessibili. Il codice manda solo quelli posseduti con quota sopra 0 (`dashboard/+page.svelte:1041`, `getOwnedBrokers()` in `brokerStore.ts:262-267`). Inoltrato al coordinatore.
  >
  > **Gate `fb3`**: build strict exit 0 e 0 WARNING; il resto verde (27 percorsi). **Gate `fb4`**, dopo IBKR, Directa e il segnaposto: build exit 0 e 0 WARNING, `check-links` con solo la baseline, scope (30 percorsi), segnaposto, stile e `git diff --check` tutti verdi.
  >
  > **Seguito** (coordinatore, 14:25): «Risk, Who Calls It: correggila tu in questo checkpoint». Risk è parcheggiato e il file non è cambiato dopo la base. Le voci CHANGELOG della doc (IBKR, Directa, semplificazione) le scrive il coordinatore all'integrazione.
  > - **`developer/backend/risk/architecture.md`**:
  >   - **Riga «Dashboard, Risk tab»** di `#callers`. Prima diceva «every broker the user can access». Ora dice `{kind: "portfolio", broker_ids}` con i broker **posseduti** a quota positiva, dove una quota mai impostata conta 100% per il proprietario (`getOwnedBrokers()`, `stores/reference/brokerStore.ts:262`). Vale qualunque sia il filtro dei broker. Il pannello si monta solo quando i broker sono noti, perché senza `broker_ids` il backend allargherebbe la richiesta a tutti i broker visibili (`dashboard/+page.svelte:1032-1041`).
  >   - **Puntatori** (intro e «Related»): ora vanno a `user/dashboard/risk.md` e alla nuova `Risk UI`, legati alle pagine nuove di S15.
  > - **Gate `fb5`**: build exit 0 e 0 WARNING, `check-links` con solo la baseline, scope 31 percorsi, segnaposto, stile e `git diff --check` verdi.
  >
  > **Review del developer** (14:20-14:30): «quelle che vedo per ora mi piacciono»; «nella forma e nei contenuti, mi pare corretto fin ora», fino ai Grafici; «le pagine developer sono giustamente ricche… mi fido che siano corrette».
  > - **⚠️ Fuori pista: anteprima senza schermate.** Con `mkdocs serve`, MkDocs riscrive `config.site_url` in `http://127.0.0.1:6042/LibreFolio/`.
  >   - `overrides/main.html` ricava da lì `LF_GALLERY_FALLBACK_BASE`, quindi il fallback di `gallery-img-loader.js` verso GitHub Pages interroga di nuovo il server locale. I PNG sono gitignorati e nel worktree non ci sono, perciò nessuna immagine viene caricata.
  >   - Verificato nel browser: fallback = `http://127.0.0.1:6042/LibreFolio/`, mentre github.io risponde (1280 px).
  >   - Con la build statica, dove `site_url` resta canonico, il fallback funziona: 8/8 immagini su `charts`.
  >   - Le schermate della 1.1 sono pubblicate (200). Quelle nuove della 1.2 di M (`tools/hub`, set Danske, `files/brim-report-sets`, `transactions/bulk-todo-banner`, `assets/type-picker-open`) non lo sono ancora (404): arrivano con la gallery di M.
  >   - È un difetto dell'infrastruttura, non delle pagine. `overrides/main.html` non è di Q: va segnalato.
  > - **Anteprima** (developer: «meglio cambiare porta»; anche il serve diventava inusabile durante le ricompilazioni):
  >   - spento `dev.py mkdocs serve` sulla 6042 (PID 19591 e figlio 21346). Era stato riavviato alle 13:44 da un agente di questa sessione, padre l'app Copilot (PID 730), senza shell utente; `stop_bash` non lo tracciava più. Fermato con `kill <PID>` e verificato che la porta 6042 è libera;
  >   - anteprima statica sulla corsia **6162**: `http://127.0.0.1:6162/LibreFolio/`, `python3 -m http.server` detached (shellId `q-preview-6162`) su `/tmp/librefolio-r2-q/preview`, con il symlink `LibreFolio` che punta a `site`;
  >   - aggiornamento con `/tmp/libreFolio_q_preview_rebuild.sh`: build con `dev.py`, copia e scambio atomico solo se la build riesce. Con `--no-build` riusa la build del gate.
  > - **Modifiche chieste** (14:25):
  >   - **elenco broker** (`import/index.en.md`): badge solo per Alpha e Beta, via «✅ Stable ·» dalle card di Directa, Crédit Agricole e Generic CSV. La legenda ora dice che gli importer senza etichetta sono quelli stabili;
  >   - **home** (`index.en.md`): «Planning Tools», legata al PAC, diventa la sezione «Tools»: un tool per ogni funzione utile, che legge i dati senza cambiarli, e un catalogo che crescerà. Resta solo «Explore tools →»; via il pulsante del PAC.
  >   - Nessun'altra pagina utente usa il badge «✅ Stable».
  > - **Gate `fb6`**: build exit 0 e 0 WARNING, `check-links` con solo la baseline, scope 31 percorsi, segnaposto, stile e `git diff --check` verdi. Anteprima aggiornata alle 14:31.
  >
  > **Review del developer, seguito** (14:41):
  > - **Home, frase dei Tools.** Il developer: «non è accattivante; l'inizio va bene […] deve finire con qualcosa del tipo: da ora fare calcoli e prendere decisioni sarà un gioco da ragazzi!». Nuova frase: «LibreFolio comes with a set of tools, one for each useful job! Each one starts from your real portfolio, shows you the numbers before you act, and never changes a thing. From now on, crunching numbers and making decisions is child's play!»
  > - **Home, «A Modular Ecosystem».** Il developer: «aggiungere un'altra voce proprio per i tools». Quinta voce **Tools**, con l'icona `Wrench` della sidebar dell'app (`Sidebar.svelte:41`) e link a `user/tools/`.
  >   - **Layout:** la variante nuova `plugin-radial-hub--five` dispone le 5 voci a pentagono. Le posizioni `node-penta-1…5` stanno sul cerchio a 0°, 72°, 144°, 216° e 288°, con le linee SVG in `viewBox 0 0 720 720`.
  >   - **Geometria in `stylesheets/home-custom.css`**, file condiviso e mai aperto da altri, da **dichiarare**:
  >     - **da 1240 px in su**: orbita di 760 px (raggio 380), schede da 360 px, hub alto 760 px;
  >     - **sotto 1240 px**: le 5 schede si impilano come su mobile, solo nella variante five;
  >     - **la sezione** ha `overflow-x: clip`, con la nuova classe `deep-dive--ecosystem` solo nella home EN.
  >   - La variante `--four` delle home IT/FR/ES non cambia.
  >   - **⚠️ Fuori pista: misure** nel browser della 6162, campionando l'orbita ogni 3°:
  >     - **prima versione** (raggio 360, da 769 px): le schede si toccavano a 40° (−1 px, schede alte 189 px), e la pagina scorreva in orizzontale tra 1100 e 900 px;
  >     - **senza clip:** durante la rotazione la pagina scorreva di 135-198 px in orizzontale. Nessuna scheda usciva dallo schermo, ma la traccia ruotata calcola l'overflow dai box non trasformati delle schede. `html {overflow-x: hidden}` blocca solo lo scroll manuale. Il clip sull'hub tagliava le schede agli angoli estremi (10 px), per questo è passato alla sezione;
  >     - **finale:** a 1240 e 1366 px il distacco minimo è +13 px, senza overflow e senza tagli; sotto 1240 px le schede sono impilate, senza overflow;
  >     - **a 1920 px** c'è una sovrapposizione transitoria di −7 px, perché Material ingrandisce il font radice da 1600 px. L'hub a quattro attuale fa −31 px alla stessa larghezza, quindi la variante nuova è migliore dell'esistente.
  >   - Durante le misure, aprire `/it/` aveva salvato `gallery-lang` = `it` per l'origine 6162, e la home veniva reindirizzata in italiano. Riportato a `en` dopo ogni misura.
  > - **Degiro = Stable** (developer: «abbiamo avuto degli export veri, direi che è uscito dalla fase beta»):
  >   - `degiro.en.md`: tolta l'admonition Beta;
  >   - card dell'index senza badge;
  >   - `providers_list.md`: «✅ Stable». Il file era già aperto per IBKR; da comunicare al coordinatore.
  > - **Immagini mancanti nell'anteprima:** `type-picker-open`, le 5 Danske, read-as e file-menu di how-to. Sono schermate nuove della 1.2, non ancora pubblicate.
  >   - M ha depositato **102 PNG** in `/tmp/librefolio-q-gallery-drop/desktop/en/{light,dark}`. Lo script dell'anteprima le sovrappone al solo sito servito.
  >   - Verificato: home 12/12, create-edit 5/5 (3 dalla copia), Danske 5/5 (5), how-to 20/20 (9).
  >   - Le schermate pubblicate `assets/distribution-editor-*` erano della 1.1, senza **Import CSV**. M le ha rigenerate con lo scenario esistente; alla release la gallery completa le riprodurrà.
  >   - `brokers/import-report-set-file-menu` nella copia è ancora la versione con «Read alone with Generic CSV»: lo scatto con l'export reale arriva dopo l'onda 1.
  > - **About:** la frase da guardare è in `#tool-diagnostics`: «Its job counters cover … **Completed jobs** already includes the **Failed jobs**: do not add the two together.» Prima rimandava alla spiegazione dei contatori nella pagina Tools, spostata nel manuale dev.
  > - **Gate `fb7`-`fb9`**: build exit 0 e 0 WARNING, `check-links` con solo la baseline, scope 33 percorsi, segnaposto, stile e `git diff --check` verdi. Anteprima pulita alle 14:58, con la copia di M.
  >
  > **Review del developer, seguito** (15:07):
  > - **«Modular ecosystem non compare» in Chrome.**
  >   - In Chrome 155 headless (profilo temporaneo, `/tmp/q-chrome-profile`), a 1600, 1280 e 1100 px, l'hub si vedeva: non riprodotto.
  >   - I tab del developer sono il browser integrato dell'app, cioè WebKit.
  >   - L'unico costrutto nuovo rispetto all'hub a quattro, che funziona, era `overflow-x: clip` sulla sezione, sopra schede animate con `backdrop-filter`. Rimosso, e con lui la classe `deep-dive--ecosystem`.
  >   - **⚠️ Fuori pista: causa vera dell'overflow.** Misurando su 360°, l'hub a quattro non va mai oltre il bordo (0 angoli su 60), quello a cinque senza clip sì (fino a 134 px a 1366, 38 angoli su 60). Ruotare la traccia e controruotare ogni scheda annida due rotazioni, e ognuna gonfia il box di overflow; con l'orbita più larga quel box esce dalla pagina.
  >   - **Correzione**, solo nella variante five: ogni scheda si muove con un transform suo, `@keyframes penta-orbit` = `rotate(a) translateY(-380px) rotate(-a)`, che è una traslazione pura. Ritardi da −12 s a −48 s; traccia ferma, ruota solo lo SVG delle linee (`orbit 60s`); pausa all'hover anche per lo SVG. Tolte le posizioni statiche `node-penta-*`.
  >   - **Misure WebKit su 360°:** overflow 0 e nessuna scheda fuori vista a 1240, 1366, 1600 e 1920 px. Distacco minimo +13 px fino a 1366; da 1600 px −3 px, per il font radice di Material (l'hub a quattro fa −31).
  >   - **Chrome headless:** l'hub si vede e gira; a 2 s e a 9 s le posizioni sono diverse.
  >   - **Anteprima:** il server ora è `/tmp/libreFolio_q_preview_server.py` (shellId `q-preview-6162b`), con `Cache-Control: no-store`, così il browser non tiene copie vecchie fra una build e l'altra.
  > - **Home:** tolto «and never changes a thing» dalla frase dei Tools e «never change it» dalla scheda: «with tool plugins, one for each job, **starting from your own portfolio**».
  > - **How-to:** i tre step facoltativi tornano **pannelli espandibili**, come a HEAD: `??? abstract` Unify assets, `??? warning` Corrections, `??? note` Duplicates.
  >   - Stanno sotto un H3 breve, `### 🧩 Steps that appear only when needed {: #only-when-needed }`.
  >   - Il link dell'elenco broker passa da `#duplicates` a `#only-when-needed`: era l'unico link a quell'ancora.
  > - **About:**
  >   - **popup delle donazioni:** restano la frase «Every now and then … reminds you» e la schermata. Via Esc, soglie e frequenza;
  >   - **Tool diagnostics:** via anche la frase sui contatori dei job, che il manuale dev copre già (`tool_plugins.en.md:192`).
  >   - Le regole del popup vanno in `developer/frontend/onboarding.md#deferred-popups`: 60 giorni, oppure 10 accessi più 7 giorni; niente Esc né backdrop; si chiude solo con Buy Me a Coffee o Maybe later (`donation_popup_service.py`, `auth.py:112,146`, `DonationPopupModal.svelte:50`).
  >   - L'interruttore nascosto della docstring **non** è documentato, come la docstring richiede.
  > - **Gate `fb10`**: build exit 0 e 0 WARNING, `check-links` con solo la baseline, scope 34 percorsi, segnaposto, stile e `git diff --check` verdi. Anteprima alle 15:17.
  >
  > **Review del developer, seguito** (15:21): «about ora è perfetto»; «le frasi vanno bene».
  > - **Home, hub senza orbita:** dove c'è spazio, le schede vanno su due colonne.
  >   - Da 900 a 1239 px, griglia `repeat(2, minmax(0, 400px))` centrata; la quinta scheda, Tools, occupa entrambe le colonne. Le schede della stessa riga hanno la stessa altezza.
  >   - Sotto 900 px resta la colonna singola.
  >   - Misure WebKit: a 1239, 1000 e 900 px, 2 colonne e 3 righe (161/161 e 189/189 px), Tools centrata, overflow 0; a 899 e 700 px una colonna, overflow 0.
  > - **How-to:** anche «⚖️ Align with the bank» diventa un pannello `??? info`, «after Review, only for a report set such as Danske Bank», in fondo alla Review. Nessun link puntava alla sua ancora automatica.
  > - **Gate `fb11`**: build exit 0 e 0 WARNING, `check-links` con solo la baseline, scope 34 percorsi, segnaposto, stile e `git diff --check` verdi. Anteprima alle 15:23, con 4 pannelli `<details>` in how-to.
  >
  > **Onda 1 approvata** (developer, 15:25): «mi piacciono entrambi, direi che questa onda è completata».
  > - **Verifica del formato** (domanda del developer: «gli script di verifica del formato danno errore nelle pagine inglesi?»):
  >   - `dev.py mkdocs translate-validate` controlla solo le **traduzioni** contro l'EN: i suoi errori sono debito di traduzione. Sono 1128; il parser per pagina ne attribuisce 237 alle 10 pagine tradotte di questa onda e 606 alle 45 pagine con debito precedente della 1.2. Log: `/tmp/libreFolio_q_tv_fb.log`.
  >   - **Auto-validazione EN** (`/tmp/libreFolio_q_selfcheck.py`): `validate_file(en, en)` con gli stessi 15 controlli del progetto (admonition, code block, liste, HTML, LaTeX, front matter…). Su 221 pagine EN e dev: **0 errori**, e 3 WARN `artifact-glossary-marker` già presenti a HEAD. Sono falsi positivi su codice (`"broker_ids": [3]`, `groupIsins[0]`) in pagine dev non tradotte.
  > - **Privacy:** sulle 2589 righe aggiunte, nessun IBAN, email, numero lungo né segreto.
  > - **Chiusura della corsia:** anteprima spenta, porte 6162 e 6042 libere. Rimossi il profilo Chrome temporaneo, le PNG di M (`/tmp/librefolio-q-gallery-drop`) e il sito copiato. Gli script `/tmp/libreFolio_q_preview_rebuild.sh` e `/tmp/libreFolio_q_preview_server.py` restano per l'onda 2.
  > - **Checkpoint:** 31 file tracciati modificati e 3 nuovi; nessuna traduzione toccata; `git diff --check` pulito. Messaggio proposto in `/tmp/libreFolio_commit_fb.txt`. Stato FROZEN.
  > - **Commit del developer:** `eee56b42a` («docs: simplify user pages, move internals to dev»), 34 file, sopra `ffa72cc2b`.
  >   - Il coordinatore ha verificato l'albero e la risoluzione dei 3 conflitti col treno 13: vale la versione di Q.
  >   - Poi il developer ha fuso il treno 14 nel ramo di Q: `cbfce2475` (genitori `eee56b42a` e `9eb01c756`). La base ora contiene i treni 13 e 14.
  >   - L'onda 1 entra in `dev_release2` col treno 15, dopo la coverage.

- **S17** ✅ 2026-10-08 — Onda 2 della semplificazione, su base `cbfce2475`.
  > **Via libera del coordinatore** (15:48), nella stessa sessione col developer:
  > - le pagine di P e di L sono comprese; per `user/ai-export/**` vale `ai-development.instructions.md`;
  > - `mkdocs.yml`, `static/extra.css` e `home-custom.css` restano di Q;
  > - **riservate a M**, che ci mette le immagini dopo il treno 15: `user/assets/correlation`, `user/dashboard/index`, `user/dashboard/risk`, `user/tools/pac-allocator/index`, `user/transactions/import/danske-bank` e le tre pagine `risk-metrics/` (`benchmark-selection`, `historical-replay`, `simulation-modes`).
  >
  > **Brief** (sessione Q, `files/simplify_brief.md`, «wave 2 edition»), aggiornato con le correzioni del developer nell'onda 1:
  > - pannelli espandibili per ciò che compare solo a volte;
  > - un H3 per step;
  > - LaTeX per le formule;
  > - niente versioni;
  > - badge solo per Alpha e Beta;
  > - frequenze e regole interne nel manuale dev;
  > - blocchi per le superfici di analisi.
  >
  > Il brief elenca anche le pagine vietate: quelle riservate a M, le pagine dev di P, `brim_plugin_guide.md` e `providers_list.md`. Niente anteprima live: la build strict la fa Q dopo i writer.
  >
  > **Gruppi** (8 `docs-writer`, file disgiunti; parole sulla base `cbfce2475`):
  > - **A, dashboard di P:** `kpi-cards` (1784) e `positions` (2164).
  > - **B, AI Export di P:** `ai-export/{index,portfolio,broker,fx,asset}` (3591).
  > - **C, onboarding e impostazioni:** `getting-started` (1555), `settings/preferences` (1880), `pwa` (694), `misc/image-crop` (498).
  > - **D, dettaglio asset:** `assets/index` e `assets/detail/{index,chart,signals,data-editor,measures,events}` (6300). Si conserva l'ancora `#rolling-return`.
  > - **E, FX:** `fx/{index,add-pair,sync,chart-settings}` e `fx/detail/{index,chart,data-editor,signals,measures}` (5151).
  > - **F, provider:** `assets/providers/{index,borsa-italiana,css-scraper,justetf,yahoo-finance,scheduled-investment}`, `fx/providers/index` e `fx/detail/provider` (4330).
  > - **G1, broker, transazioni e Files:** `brokers/{index,import,info}`, `transactions/{index,form}` e `files/index` (4165). `brokers/sharing` resta fuori finché il coordinatore non chiarisce l'esclusione del Q1 alla riga `:76`.
  > - **G2, importer:** `import/{credit_agricole,degiro,intesa,etoro,fineco}` (3229).
  > - Fuori dall'onda 2: le admin (onda 3), `community/contribute` (pagina per contributori) e la home, già rivista dal developer.
  >
  > **Risposte del coordinatore** (15:53):
  > - **Pagine dev e di teoria di P** (`wac.md`, sezione sul costo di `fifo_lot_engine.md`, `data-quality-banner.md`, teoria): **restano di P**, che sta discutendo col developer la regola `MISSING_COST_BASIS` (#32). I writer elencano nel report i fatti che spetterebbero lì, e il coordinatore li gira a P.
  > - **`user/brokers/sharing.en.md` è libera.** La riga `:76` era stata concessa a N il 07/10 per la tab Rischio sui broker posseduti, lavoro entrato con `49d4ec8e0`. Aggiunta al gruppo G1, con un messaggio al writer, e allo scope `--w2` del gate.
  >
  > **M** (16:00): ha rimesso in `/tmp/librefolio-q-gallery-drop/desktop/en/{light,dark}` le stesse 102 PNG del primo deposito: assets 5, dashboard 17, brokers 12, files 3, settings 1, transactions 1; per fx, onboarding e ai-export nessuno scatto, quindi ricade sulle Pages. Il prossimo deposito arriva dopo le 17 con la verifica del G5: gli scatti `onboarding/*` e la guardia offline della gallery su assets, fx e brokers.
  >
  > **Note implementazione, onda 2, gruppo B (AI Export)** (16:15):
  > - **Lunghezze:** `index` da 1211 a 963 parole, `portfolio` da 872 a 480, `broker` da 604 a 358, `fx` da 459 a 277, `asset` da 445 a 247.
  > - **Struttura dell'index:** un H3 per step (da Step 1, tipo di export, a Step 6, copia); il prompt lungo sta in un pannello espandibile; sezioni «Paste», «Privacy» e «When Something Goes Wrong».
  > - **Pagine di scope:** «Export Data» e «Analyses», con i casi particolari in pannelli: domande del PAC, fatti fiscali delle minusvalenze.
  > - **Ancore:** nessuna esplicita e nessuna linkata. Le pagine non hanno schermate.
  > - **Errori corretti nel testo utente:**
  >   - «drawdown always full-history» era falso: il drawdown per asset del PAC usa solo il periodo dell'AI;
  >   - «unavailable tasks stay disabled» era falso: le analisi sono tutte elencate e rifiutate al momento della copia.
  > - **Pagine dev, solo aggiunte:**
  >   - `ai_export_composition.md`: drawdown, binding delle analisi, timing del PAC, riferimenti A#/B#/F#/L#, confine del clipboard con le soglie 20 000 / 60 000 e il draft di 10 minuti in `sessionStorage`;
  >   - `ai_export_snapshot.md`: `cost_allocation_semantics` e `zero_semantics`;
  >   - `ai_export_sampling.md`: i rendimenti FX a 30 e 91 giorni.
  > - **Seguiti:**
  >   - al writer: correggere in `ai_export_probe_workflow.md` la frase sulle L# fuori dalla directory, e in `ai_export_snapshot.md` la frase sullo schema V1;
  >   - al writer G1: `brokers/index.en.md:~79` dice «exact sampling», che non vale più.
  >   - ✅ (16:25) Fatti:
  >     - `ai_export_probe_workflow.md:134-138`: la directory risolve A#, B# e F#, mentre L# è il `lot_ref` del backend, letto sul posto (`ai_export_runtime.py:342-345`, `payloads/portfolio_broker.py:444-447,721-735`, `asset_core.py:533-551`);
  >     - `ai_export_snapshot.md:72-76`: il runtime precedente è stato rimosso prima del rilascio, e lo schema V1 è il primo rilasciato (`AI_EXPORT_SCHEMA_VERSION = 1`, `ai_export_runtime.py:25-29`; storia git `2544a3e36` → `7992471b6`).
  >
  > **Note implementazione, gruppo F (provider)** (16:30):
  > - **Lunghezze:** `providers/index` da 649 a 765 parole (le card restano identiche), `borsa-italiana` da 1125 a 771, `css-scraper` da 484 a 564, `justetf` da 344 a 320, `yahoo-finance` da 145 a 247, `scheduled-investment` da 524 a 768 (con il LaTeX e un esempio in pannello), `fx/providers/index` da 655 a 717, `fx/detail/provider` da 404 a 412. Le pagine corte crescono perché mancavano «What It Offers» e «Limits».
  > - **Errori corretti dal codice:**
  >   - justETF: USD, CHF e GBP hanno un prezzo corrente, l'ultimo giornaliero;
  >   - Borsa: nessun fallback sull'ultimo acquisto, e nessuna ricerca da URL;
  >   - CSS Scraper: il tipo è salvato come OTHER, e il parser ignora solo spazi e `€ $ £ ¥ %`;
  >   - Scheduled Investment: Interest Type e Day Count valgono per tutto il piano; «Frequency» include Weekly; **Generate Coupon**; interessi nei giorni di grazia;
  >   - FX: EUR/RON è una coppia diretta ECB, quindi l'esempio di catena diventa RON/USD via EUR; una coppia senza provider diventa manuale da sola; le etichette **Providers** ed **Edit Pair Providers**;
  >   - card: Yahoo non è «default», e Borsa non ha «smart URL search».
  >   - Tolti i fatti non verificabili: `SEDX`, «3000+ ETFs», «15-minute delay», i conteggi delle valute.
  > - **Ancore:** restano `#interest-schedule-editor` e `#how-value-is-calculated`, linkate dall'app; `#late-interest` diventa esplicita (la linka `maturity-settlement` in 4 lingue).
  > - **Dev:**
  >   - `provider_borsa_italiana.md`, `provider_cssscraper.md`, `provider_justetf.md`, `provider_scheduled_investment.md`, `system_providers.md`, `asset_plugin_guide.md`;
  >   - `fx/providers/snb.md`, che era **sbagliato** da cima a fondo: SNB dà medie mensili datate al 1°, via API JSON, per circa 25 valute;
  >   - la riga SNB di `fx/providers/index.md`.
  > - **Inoltrati:** a D due fatti per `assets/architecture.md` (il prezzo del sync diventa il punto del giorno; nessun fallback sull'ultimo acquisto, `price_resolver`); a E la regola delle catene per `fx/configuration.md` e l'esempio RON/USD.
  >
  > **Note implementazione, gruppo G2 (importer)** (16:30):
  > - **Lunghezze:** Crédit Agricole da 1219 a 1071 parole (la parte sempre visibile cresce: il saldo iniziale diventa un passo principale); DEGIRO da 717 a 624, Stable e senza badge; Intesa da 586 a 581; eToro da 345 a 410; Fineco da 362 a 331.
  > - **Errori corretti dal codice:**
  >   - Fineco: gli avvisi sono in inglese;
  >   - Intesa: la lista movimenti non crea acquisti né vendite;
  >   - eToro: niente CSV, si scarica un XLS da cui si salva il foglio **Account Activity**; la valuta viene da **Details**; overnight fee e SDRT vengono scartati senza avviso;
  >   - Crédit Agricole: il passo del saldo iniziale non è facoltativo.
  > - **Altro:**
  >   - Intesa usa le due schermate di `static/` che nessuna pagina referenziava;
  >   - DEGIRO, eToro e Fineco hanno l'H1 con 📥.
  > - **Dev:**
  >   - nuova `developer/backend/brim/credit_agricole.md`, 2037 parole; nav aggiunta da Q dopo «Danske Bank Importer»;
  >   - `brim/architecture.md`: sezione «🗒️ Plugin notes» con `#plugin-degiro`, `#plugin-intesa`, `#plugin-etoro` e `#plugin-fineco`.
  >   - Nessuna ancora linkata dalle pagine utente.
  > - I reperti per altri e sul codice sono raccolti in sessione Q, `files/w2_findings.md`, da mandare al coordinatore a fine onda.
  >
  > **Note implementazione, gruppo C (onboarding e impostazioni)** (16:40):
  > - **Lunghezze:** `getting-started` da 1555 a 1403 parole, `settings/preferences` da 1880 a 1519, `pwa` da 694 a 566, `misc/image-crop` da 498 a 550 (cinque affermazioni sbagliate corrette, aggiunte l'icona dell'asset e la pagina Files).
  > - **Pannelli espandibili:** account più vecchi, setup che non si carica, step extra dell'import, guide con step, dove si salva un replay.
  > - **Via:** le temporizzazioni 8 s / 3 s e la versione «1.2.0».
  > - **Errori corretti dal codice:**
  >   - qualità −/+, non uno slider; anteprima tonda attivabile; il preset dell'icona dell'asset da 256×256;
  >   - lingua e tema si applicano al salvataggio;
  >   - la promozione di un utente si fa solo da CLI;
  >   - Safari non serve più su iOS;
  >   - il banner di installazione del browser è soppresso.
  > - **Ancore:** restano `#welcome-setup`, `#onboarding-and-guides` e `#privacy-mode`; le schermate sono identiche a HEAD.
  > - **Dev:** `onboarding.md`, `features/settings.md` (con la lettura della Default Currency) e `pwa.md`.
  > - **Seguito:** correggere la riga «Auto-install banner ✅» di `pwa.md`, la lista «Logic» sotto AboutTab in `settings.md`, e in `state/app-state.md` il salvataggio delle impostazioni e la riga Chart Settings (fatto di E). `app-state.md` è aggiunto allo scope `--w2`.
  > - ✅ (16:50-17:05) Fatti:
  >   - `pwa.md:186,292-293`: il banner automatico del browser è soppresso da `preventDefault()`, e il dialog nativo si apre da **Install App**;
  >   - `settings.md`: la lista «Logic» spostata sotto PreferencesTab;
  >   - `app-state.md`:
  >     - riga Chart Settings: per utente in `localStorage`, scope `fx` e `assets`, periodo in `sessionStorage`;
  >     - riga Date Range: Dashboard, broker, asset e FX, in `sessionStorage`, e l'URL vince;
  >     - diagramma: le scritture passano dai componenti («write first»); il bootstrap è `appBootstrap.load()` in parallelo; nessun listener su lingua e tema;
  >     - flusso: punto 5 nuovo, sul reload che legge `librefolio-locale` e `librefolio-theme`.
  > - **Reperto di codice:** la Dashboard parte dalla valuta di default dell'istanza, non da quella dell'utente; vedi `w2_findings.md`.
  >
  > **Note implementazione, gruppo E (FX)** (16:40): 9 pagine, in tutto da 4996 a 4522 parole.
  > - **Lunghezze:** `index` da 305 a 444 (mancavano le azioni della pagina), `add-pair` da 549 a 566, `sync` da 542 a 502, `chart-settings` da 1042 a 634, `detail/index` da 216 a 288, `detail/chart` da 413 a 425, `detail/data-editor` da 856 a 769, `detail/signals` da 745 a 540, `detail/measures` da 328 a 363.
  > - **Errori corretti dal codice:**
  >   - le card non mostrano il provider, e il mini-grafico segue il periodo;
  >   - niente candlestick FX, e il doppio clic non resetta lo zoom;
  >   - il tooltip mostra la variazione dall'inizio del periodo;
  >   - data editor: nessuna colonna Source, modifica inline, Undo invece della conferma, salvataggio con **Save (N)**;
  >   - le misure si accumulano;
  >   - il pulsante è **Save Configuration**;
  >   - l'inversione 1/0.9053 ≈ 1.1046.
  > - **LaTeX:** il prodotto della catena e il tasso annuo $(P_{end}/P_{start})^{365/d}-1$.
  > - **Esempio di catena:** RON/USD via EUR, allineato ai provider.
  > - **Dev:** `fx/architecture.md` (sync di una coppia nuova, colore dell'esito, Timeout ininfluente a 120 s), `fx/configuration.md` (nuova H3 «Chain Dates, Writes and Counters», data stretta, scheduler a 14 giorni), `fx-chain-algorithm.md` (picker, salvataggio delle rotte, priorità 999 del manuale).
  > - **Inoltrati a D:** i fatti per `charts.md`, `core-ui/data-editor.md` e `signal_plugin_guide.md`.
  >
  > **Note implementazione, gruppo A (dashboard di P)** (16:50):
  > - **`kpi-cards`:** da 1784 a 1540 parole. Un blocco per card: domanda, schermata, **Metrics shown** con link alla teoria, **How to read it**. Le righe di variazione del giorno e l'esempio dell'ETF USA stanno in pannelli; LaTeX solo per Period P&L, Timing effect, Total P&L e la variazione del giorno.
  > - **`positions`:** da 2164 a 2190 parole.
  >   - Non scende perché lo schema a blocchi copre ora 3 viste e 5 blocchi FIFO, e prima la vista Performance non aveva una guida alla lettura.
  >   - Tolti il muro di regole sul YOC, i nomi interni e la storia «v3». Pannelli per celle vuote, YOC non disponibile, Hide amounts e avvisi.
  >   - Altri tagli possibili, se il developer li vuole: «Choosing a view» e le colonne nascoste.
  > - **Errori corretti dal codice:**
  >   - la Dashboard conta solo i broker posseduti con quota sopra 0;
  >   - il Total P&L include il capitale entrato con titoli a costo;
  >   - l'etichetta è **Deposited Capital (Period)**;
  >   - il pannello dei lotti si apre con **Analyze Lots** (⋮ o tasto destro), non con un clic;
  >   - i toggle si chiamano **Portfolio / Period**;
  >   - il filtro Status esiste solo come colonna nascosta;
  >   - la dimensione delle bolle dipende da **Abs / %**;
  >   - il weight include la cassa;
  >   - il pannello dei lotti ignora la quota di proprietà.
  > - **Ancore:** restano `#card-1-period-pl`, `#card-2-returns` e `#card-3-net-worth` (linkate dall'app), `#unrealized-change-by-currency`, `#fifo-lots-analysis` e `#yield-on-cost-yoc`. Nuove `#holdings` e `#performance`, più `#dashboard` sulla pagina dev.
  > - **Dev:** `pages/index.md` (sezione Dashboard: riga KPI, soglie del Timing effect, tab Posizioni) e `lots_analysis_service.md` (scope dei broker per tutti i ruoli, nessuna quota applicata). Gli interni del YOC sono già nella teoria.
  > - **Seguiti:**
  >   - ad A: il punto Broker Detail di `pages/index.md` e 3 fatti in `features/lots-analysis.md`, aggiunta allo scope;
  >   - a G1: il «click to open» di `brokers/index`.
  >   - ✅ (16:58) Fatti da A:
  >     - `pages/index.md:143-145`: **Analyze Lots**, da ⋮ o tasto destro (`ExposureTable.svelte:437-448`, `ContributionTable.svelte:219-232`);
  >     - `lots-analysis.md:128-131`: la linea Combined richiede 2 o più broker (`LotWacPriceChart.svelte:720-722`); l'etichetta è «Abs» (`en.json:1557`); la dimensione delle bolle dipende dalla quantità o dal valore, su scala a radice da 7 a 22 px (`lotWacPriceChartHelpers.ts:273-292`).
  >   - I reperti di codice (`KpiSection`, `PositionsPanel`) sono in `w2_findings.md`.
  >
  > **Note implementazione, gruppo G1 (broker, transazioni e Files)** (17:00):
  > - **Testo visibile, prima e dopo:** `brokers/index` da 727 a 656 parole; `brokers/import` da 461 a 365; `brokers/info` da 324 a 344 (con la regola del saldo di fine giornata in LaTeX, in un pannello); `brokers/sharing` da 786 a circa 780 (682 sempre visibili); `transactions/index` da 691 a 675; `transactions/form` da 442 a 580, con la tabella dei 12 tipi e i link alla teoria; `files/index` da 937 a 842.
  > - **10 affermazioni sbagliate corrette dal codice:**
  >   - non esiste una **Base currency** del broker;
  >   - le etichette sono **Allow Leveraged Buying** e **Allow Short Selling**;
  >   - i broker inattivi sono solo attenuati sulla card;
  >   - si condivide per username, non per e-mail;
  >   - **Add Transaction** apre il bulk workspace;
  >   - il form non ha un campo prezzo e chiede l'importo totale;
  >   - il cost basis vale solo per Adjustment e Asset Transfer, e non c'è un'anteprima del guadagno;
  >   - non c'è una barra di ricerca ma i filtri di colonna;
  >   - il ritaglio si apre solo da ✏️ **Edit**;
  >   - il controllo del contenuto dei file vale solo con libmagic.
  > - **Sharing:**
  >   - è un campo numerico, non uno slider;
  >   - **Save Configuration**, e **Share Broker** sta nella toolbar;
  >   - la frase sulla tab Rischio della Dashboard (solo broker posseduti con quota sopra 0) linka `#risk-tab`.
  > - **Seguiti fatti:**
  >   - via «exact sampling» da `brokers/index`;
  >   - il ritaglio con ✏️ in `files/index` e in `core-ui/file-upload.md`, che ha avuto tutti i fatti del ritaglio;
  >   - **Analyze Lots** in `brokers/index`.
  > - **Ancore:** restano `#broker-reports` (ora esplicita in EN), `#report-sets`, `#uploaded-by`, `#composite-transactions` e il link a `#risk-tab`. Nuove `#trading-options`, `#bulk-workspace` e `#link-pairs`.
  > - **Dev:**
  >   - componenti broker: `forms.md`, `cards.md` e `modals.md`, con i motivi per cui il server rifiuta il salvataggio della condivisione;
  >   - `transaction-form.md`, `file-upload.md`, `balance_validation.md`, `split_promote.md` e `users_and_brokers.md`.
  > - **⚠️ Fuori pista: sicurezza.** `GET /brokers/{id}/access` restituisce username **ed e-mail** a qualunque utente autenticato, per qualunque broker. Verificato da Q: `as_user_id="all"` salta il controllo (`broker_service.py:347`) e `list_accesses` non filtra (`:795-825`). Segnalato subito al coordinatore (16:58), senza toccare il codice.
  > - **Seguito:** correggere `brokers/cards.md` e `brokers/index.md` dev, che documentano componenti inesistenti (`CashBalanceCard`, `CashTransactionModal`).
  >   - ✅ (17:10) Fatti. `brokers/index.md` dev: card `BrokerCard` e `BrokerDiscoveryCard`; modali `BrokerModal`, `BrokerSharingModal`, `BrokerSharingPanel`, `BrokerImportFilesModal` e `DeleteBrokerDialog`; una riga `lots/`. `cards.md`: le props reali (`broker`, `summary`, `assetCount`, `targetCurrency`) e gli eventi `edit`, `delete` e `share`; via la «base currency» e `CashBalanceCard`; aggiunta `BrokerDiscoveryCard`.
  >   - Altro seguito: `core-ui/datePickers.md` (L12, L45) citava ancora `CashTransactionModal` fra gli utenti di `SingleDatePicker`. È aggiunto allo scope `--w2`.
  >
  > **Coordinatore** (16:48):
  > - **L'onda 1 è in `dev_release2`:** treno 15 `23b839fb2`, con il merge di Q `ceeb31a2c`. Il worktree di Q non viene avanzato mentre l'onda 2 è in corso; il treno 15 sarà fuso nel ramo di Q al checkpoint dell'onda 2.
  > - **Elenco degli accessi:** reperto verificato (`brokers.py:422` è l'unico `as_user_id="all"`). Lo porta il coordinatore al developer. Le frasi «share button shows who has access» di `brokers/index` e `brokers/sharing` restano come sono finché il developer non decide.
  >   - **Decisione del developer** (17:05, via il coordinatore): «mi pare che fosse una cosa voluta, serve per permettere, quando si condivide il broker di vedere a chi condividerlo, e nel caso scrivergli. poi le persone che condividono un istanza tra loro non sono estranee, basta che almeno siano autenticate». Il codice non cambia. La docstring e il commento «For superuser» vanno nel backlog del coordinatore, e Q non li tocca.
  >   - **Doc aggiornata da Q:** `brokers/index.en.md:43` e `brokers/sharing.en.md:81` dicono che ogni utente autenticato dell'istanza vede chi ha accesso a qualunque broker. Niente «e-mail» nelle pagine utente: la UI mostra username e avatar, non le e-mail (nessun `.email` in `components/brokers`). `users_and_brokers.md:67-74`: scelta voluta, e l'API restituisce anche l'e-mail.
  > - Le pagine riservate restano a M, che ora ci mette le immagini.
  >
  > **Note implementazione, gruppo D (asset)** (17:20):
  > - **Lunghezze:** `assets/index` da 1214 a 1057 parole; `detail/index` da 590 a 543; `detail/chart` da 1220 a 911 (finestra del rolling return in LaTeX); `detail/signals` da 1703 a 1058 (un H3 per famiglia, una riga per indicatore con link alla teoria); `detail/data-editor` da 656 a 669; `detail/measures` da 475 a 368; `detail/events` da 442 a 558.
  > - **Errori corretti dal codice:**
  >   - non c'è un «time delta selector»; le voci sono **Reload** e **Merge with…**;
  >   - i marker degli eventi si distinguono per forma, non per colore;
  >   - il menu valuta elenca le valute raggiungibili dalle coppie FX;
  >   - l'icona della documentazione è **?**, e l'errore è un ⚠ rosso;
  >   - nel data editor non c'è una colonna Currency; i vecchi esempi CSV non si importavano (serve `date;currency;close`); si cancella con **Undo**;
  >   - eventi: Scheduled Investment genera Interest e Maturity; Yahoo porta anche gli split; mancava justETF; gli eventi si aggiungono dal data editor, da **Linked Event** e da **Add Event** del piano.
  >   - Data editor ed eventi crescono per queste correzioni.
  > - **Ancore:** restano esplicite `chart.md#rolling-return` e `#primary-modes` (la linka `indicators/index`). Nuove `signals.md#data-comparison`, `#drawdown-full-history`, `#technical-indicators` e `data-editor.md#import-from-csv`. Le automatiche tolte non le linka nessuno.
  > - **Dev:**
  >   - `charts.md`: modi Prices / Rolling Return; nuove sezioni «Chart Settings and Axis Scales» e «Responsive Date Axis», con i fatti di E;
  >   - `core-ui/data-editor.md`: parsing CSV, tabella degli errori, regole di salvataggio FX e asset, refresh trattenuto; corretti conferma e separatore tab;
  >   - `signal_plugin_guide.md`: `catalog_visible`, 23/22/9 plugin, risultati mai salvati, tabella delle icone di `signalProblem.ts`;
  >   - `events.md`: corretto il dedup (sostituisce solo stessa data, tipo e provider);
  >   - `assets/architecture.md`: politica di conversione FX, endpoint, i due fatti di F. Il prezzo del sync diventa il punto del giorno. Il fallback sull'ultima operazione esiste dentro il `price_resolver` (`LAST_TRADE_PRICE`), non come regola a parte.
  > - **Reperti di codice:** 5 sugli eventi (`{n}` contro `count`, cambio di tipo che duplica, FK `RESTRICT`, CSV `value` contro `amount`, commento della gomma), in `w2_findings.md`.
  >
  > **Chiusura della scrittura dell'onda 2** (17:00):
  > - **G1, ultimi seguiti su `core-ui/datePickers.md`:**
  >   - `SingleDatePicker` ha 6 utenti reali (DataEditor, BrokerForm, TransactionFormModal, EventCreateMiniModal, ScheduledInvestmentEditor e BoundaryDateModal), non `CashTransactionModal`;
  >   - `DateRangePicker` ha 10 utenti reali (i 6 toolbar di pagina, `MeasurePanel`, `DataTableColumnFilter`, `CellDateRange`, `L4Replay` → `risk-lab.md#replay`).
  >   - Q ha corretto la riga dei preset: 1W, 1M, 3M, 6M, 1Y, 2Y, YTD, MAX e la finestra personalizzata; 3Y, 5Y, 10Y, MTD, QTD e WTD solo se c'è spazio (`DateRangePicker.svelte:36,216-251`).
  > - **Gate `w2b`** (`Q_GATE_ARGS=--w2 /tmp/libreFolio_q_gate.sh w2b`): build strict exit 0 e 0 WARNING; `check-links` con solo la baseline (`#rolling-return`); scope 88 percorsi, 48 pagine utente e 39 dev più il piano; segnaposto, stile e `git diff --check` verdi. Nel gate intermedio `w2a` c'era 1 WARNING su `charts.md#where-settings-live`, a scrittura in corso: risolto.
  > - **Anteprima:** sulla 6162 alle 16:58 (`q-preview-6162c`, no-store), con le 102 PNG di M sovrapposte.
  >
  > **Onda 2 approvata** (developer, 17:26): «kpi e posizioni vanno alla grande! anche ai export ora è come me la immaginavo in tutte le pagine. […] le altre dopo mi paiono tutte corrette, le approvo».
  > - **Immagine `fx/detail-chart` «mancante» nella tab del developer:** non è un errore.
  >   - Il nome è lo stesso di HEAD, lo scenario esiste (`gallery.spec.ts:3482`), e la copia pubblicata della 1.1 esiste (200, 1280×720, EUR→USD).
  >   - Nel WebKit dell'app si carica (697×392). Nella tab del developer la richiesta a GitHub Pages era fallita in quel momento.
  >   - M non ha ancora scatti FX: alla release la gallery completa la rigenera.
  > - **⚠️ Fuori pista: LaTeX.** L'auto-validazione EN (`/tmp/libreFolio_q_selfcheck.py`) ha trovato in `kpi-cards.en.md` 3 formule con `\text{Total P&L}`. È l'errore `latex-syntax-ampersand` del validatore del progetto: `&` dentro `\text{}`.
  >   - MathJax lo renderizzava comunque, ma la regola del progetto vale anche per le traduzioni.
  >   - Corretto in `\text{Total P}\&\text{L}` (6 occorrenze). MathJax: 5 container, 0 errori.
  > - **Auto-validazione EN dopo la correzione:** 247 pagine, 0 errori, e 2 WARN `artifact-glossary-marker` già presenti a HEAD, falsi positivi su codice.
  > - **Privacy:** sulle 3750 righe aggiunte, nessun IBAN, email, numero lungo né segreto.
  > - **Gate `w2d`:** build exit 0 e 0 WARNING, `check-links` con solo la baseline, scope 88 percorsi, segnaposto, stile e `git diff --check` verdi.
  > - **Chiusura della corsia:** anteprima spenta, porte 6162 e 6042 libere. Rimosse le PNG di M (`/tmp/librefolio-q-gallery-drop`), il sito copiato e i file temporanei.
  > - **Checkpoint:** 87 file tracciati modificati e 1 nuovo (`developer/backend/brim/credit_agricole.md`); nessuna traduzione toccata. Messaggio proposto in `/tmp/libreFolio_commit_w2.txt`. Stato FROZEN.
  > - **Reperti per il coordinatore:**
  >   - i tooltip dei livelli di dettaglio in `en.json` («buckets up to 30/14/7 days») valgono solo per i prezzi; gli indicatori arrivano a 84/28/14;
  >   - `.github/instructions/frontend-ai-export.instructions.md` descrive un flusso `ClipboardItem`, ma il codice usa `writeText` con un fallback.

## 4. Conflitti, rischi, definizione di fatto

### Conflitti

- **N:** su `brokers/index` solo la riga della tab Rischio, con l'ancora fornita dal coordinatore. `dashboard/index` non si tocca.
- **P:** `fifo_lot_engine` in Q2, fuori dalla sezione sul costo.
- **L:** nessuno.
- **M:** nomi degli screenshot; `release-pipeline`.
- **O:** etichette della UI, ricontrollo finale.

### Rischi

- **Debito di traduzione in crescita:** niente stamp.
- **Ancore chiamate dall'app** (§0): si rompono se cambiano i titoli.
- **Segnaposto invisibili:** la pagina deve capirsi anche senza l'immagine.
- **La punta si muove.**
- **Voci «non verificate» negli audit:** il `docs-writer` le verifica prima di scrivere.

### Definizione di fatto (Q1)

- Risolti tutti i ❌ e i ⛔ di §1.1-§1.2, completati i 🟡; ognuno verificato contro il codice.
- Un segnaposto per ogni nome di §2.1, nella pagina indicata.
- Build strict senza WARNING/ERROR nuovi; check-links verde.
- Debito di traduzione riportato.
- Nessuna modifica ai file esclusi.
- Questo piano aggiornato a ogni passo.
- Handoff FROZEN prima del commit.
