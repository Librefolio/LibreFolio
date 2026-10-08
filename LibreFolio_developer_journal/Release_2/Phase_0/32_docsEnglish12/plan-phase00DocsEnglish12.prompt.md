# Phase 0 — 32 · Doc inglese 1.2: allineamento EN ai cambiamenti dalla 1.1

> **Stato: Q1 COMMITTATO (`dfcbc0003`), Q2 COMMITTATO (`7b06e9f9f`), entrambi nel treno 9 (base `9ea2d519b`). S12 (ancora `#risk-tab`) COMPLETATO, FROZEN (2026-10-07), in attesa del commit.** L'analisi (§1-§2, §4) è stata scritta il
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
