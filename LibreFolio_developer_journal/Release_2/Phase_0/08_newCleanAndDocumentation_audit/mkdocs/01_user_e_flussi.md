# mkdocs — area utente e flussi — verifica 2026-09-02

> Fonti: [baseline](../../../phases/05_cleanAudit/mkdocsAudit/00_BASELINE.md) ·
> [01_user-core](../../../phases/05_cleanAudit/mkdocsAudit/01_user-core.md) ·
> [02_transactions-brokers-import](../../../phases/05_cleanAudit/mkdocsAudit/02_transactions-brokers-import.md) ·
> [03_fx-market-data](../../../phases/05_cleanAudit/mkdocsAudit/03_fx-market-data.md) ·
> [04_ai-export](../../../phases/05_cleanAudit/mkdocsAudit/04_ai-export.md) ·
> contesto: [00_INDEX](../../../phases/05_cleanAudit/mkdocsAudit/00_INDEX.md) e
> [08_tassonomia](../../../phases/05_cleanAudit/mkdocsAudit/08-functionality-gap-taxonomy.md)
>
> Metodo: analisi statica read-only del worktree `dev_release2` (HEAD `f4698da7`,
> 2026-09-02) **incluse le modifiche beta non committate del 02/09**. Nessun test
> eseguito, nessun server avviato (`mkdocs build/serve` inclusi), nessuna scrittura
> fuori da questo file. Ogni citazione `file:riga` è stata riletta oggi sui sorgenti
> correnti; i numeri sono riprodotti con il comando mostrato.

## Sintesi esecutiva

- **29 voci vecchie riverificate** (11 da 01, 9 da 02, 6 da 03, 3 da 04, più il falso
  positivo noto di check-links): **9 reggono** (fix Block 3/S1–S3 ancora corretti),
  **15 mai toccate e ancora valide** (01: R-02, R-03, R-11, R-12 · 02: F3 critical,
  F4, F5, F6 · 03: F1 critical, F4, F5, F6 · 04: R-01, R-02, R-03), **3 parziali**
  (01-R-05 Holdings; 02-F7 e F8 lato `index.en.md`), **1 superata in peggio** (02-F1/F2:
  `brokers/import.en.md` fu riallineata il 05/08 al wizard a 4 step, ma il rework di
  agosto l'ha resa di nuovo obsoleta).
- **12 nuove discrepanze** trovate (sezione B), di cui le peggiori: la pagina
  `assets/detail/signals.en.md` dichiara **5 task AI Export Asset inesistenti**
  (mai auditata — era "fuori standard" per 01 e fuori scope per 04); `files/index.en.md`
  documenta un'azione **"Reprocess" che non è mai esistita** e un delete che
  "rimuove le transazioni dal ledger" mentre cancella solo il file; il flusso import di
  `getting-started.en.md` descrive il wizard pre-rework.
- **Blocco 1 (mio scope: 03-F2, 03-F3): regge entrambe**, test E2E del caso negativo FX
  presente (`fx-csv-import.spec.ts:227-233`).
- **i18n**: il batch multi-lingua rinviato è ora indietro di **due generazioni** sul
  wizard (IT/FR/ES dicono ancora "5 passi operativi", testo pre-remediation).

## A. Verifica voci vecchie

Legenda stato oggi: **FATTO** (fix regge) · **PARZIALE** · **MAI FATTO** (claim ancora
falsa/vera come allora) · **SUPERATO** (il fix o la pagina sono stati resi obsoleti da
onde successive) · **ANNULLATA** (la claim o il codice non esistono più).

| Voce | Stato 2026-08 | Stato oggi | Evidenza 2026-09-02 (docs ↔ codice) | Azione |
|---|---|---|---|---|
| 01 R-02 (Card 1 % = "yesterday's Period P&L") | aperta | **MAI FATTO — ANCORA VALIDO** | `kpi-cards.en.md:32` invariato ("share of **yesterday's** Period P&L"); codice `KpiSection.svelte:113-118`: `pnlDeltaDay / prevHistoryPoint.total_pnl.amount` (Total P&L di ieri). Il diff working-tree di `kpi-cards.*.md` aggiunge solo la nota "Net Worth includes cash" (righe 105-107), non tocca R-02 | Task D1 |
| 01 R-03 (Card 3 % = "day-over-day") | aperta | **MAI FATTO — ANCORA VALIDO, codice cambiato** | `kpi-cards.en.md:113` invariato; ma la Card 3 ora renderizza `absRoiPct = total_gain_loss_percent * 100` (`KpiSection.svelte:121-126`, render `:339-341`; commento `:119-120` sposta `simple_roi_percent` alla Card 2). Backend: `total_gl_pct = total_gl / total_invested` (`portfolio_service.py:1409-1412`) → ROI since-inception, non delta giornaliero (all'audit era `simple_roi_percent`: la docs resta sbagliata in entrambe le versioni) | Task D1 |
| 01 R-04 (Positions Performance: 4 colonne errate) | ✅ Aggiornato | **FATTO — regge** | `positions.en.md:34-36` non elenca più la tabella errata; le colonne reali restano `ContributionTable.svelte:244-428` (14 header) | — |
| 01 R-05 (Holdings: 8 colonne omesse + label "PMC") | ✅ Aggiornato | **PARZIALE** | La tabella Holdings a 5 metriche è **rimasta identica** (`positions.en.md:26-32`); `ExposureTable.svelte` ha 13 header (`:160,182,210,224,238,251,265,279,292,305,318,332,347`), label UI "PMC" (`:332`) vs docs "Average Price (WAC)" (`:31`). Né colonne aggiunte né nota "sottoinsieme non esaustivo" | Task D2 |
| 01 R-06 (Time Delta 1D/YTD/ALL) | ✅ Aggiornato | **FATTO — regge** | `assets/index.en.md:29` elenca `1W,1M,3M,6M,1Y,2Y,3Y,5Y` = `DELTA_PERIODS` (`assetPriceDerived.ts:104-113`) 1:1 | — |
| 01 R-08 (CSV anche con `,`) | ✅ Aggiornato | **FATTO — regge** | `data-editor.en.md:41` ("both `;` and `,` … auto-detects"); `CsvEditor.svelte:145-160` `detectSeparator()` invariato | — |
| 01 R-09 (justETF fallback non-EUR) | ✅ Aggiornato | **FATTO — regge** | `justetf.en.md:35-37` (gettex EUR + fallback `latestQuote`); codice `justetf.py` `get_current_value()`: strategia a due passi con fallback `load_raw_chart` invariata | — |
| 01 R-10 (Settings "tre aree") | ✅ Aggiornato | **FATTO — regge** | `settings/index.en.md:5-10` ora "split into four tabs" con Profile separato; `settings/+page.svelte:5-8,50-56` monta Profile/Preferences/About/GlobalSettings | — |
| 01 R-11 (campo "Date Format" inesistente) | in attesa (S4) | **MAI FATTO — ANCORA VALIDO** | `preferences.en.md:14` ha ancora la riga; `grep -rn "dateFormat\|date_format" frontend/src/lib/components/settings/ backend/app/schemas/settings.py backend/app/schemas/users.py` → 0 risultati; `PreferencesTab.svelte:35-37,81-83` espone solo language/default_currency/theme | Task D3 |
| 01 R-12 ("backend + frontend" version) | aperta (editoriale) | **MAI FATTO — ANCORA VALIDO** | `about.en.md:9` invariato; un solo `app_version`: `AboutTab.svelte:25,220,293`, `system.py:20` | Task D4 |
| 01 R-13 (preset Asset Icon) | ✅ Aggiornato | **FATTO — regge** | `image-crop.en.md:29` (riga Asset Icon 256×256); `imageCrop.ts:47,70` preset `'asset-icon'` | — |
| 01 check-links `${lang` (falso positivo parser) | falso positivo noto | **ANCORA VALIDO come falso positivo** | `AboutTab.svelte:145` (template literal annidato) e parser `dev.py:1066` (regex) + `:1072` (cleanup `\$\{[^}]+\}`) invariati → la segnalazione si riprodurrebbe identica. Non riverificabile by-run per vincolo no-serve | (tooling, opzionale) |
| 02 F1 (n° step wizard) | ✅ Aggiornato (4 step) | **SUPERATO (in parte)** | `how-to.en.md` riscritta nel rework (commit `c0814ee4`): `:38-51` "four steps you always see and three that appear only when needed" — **corrisponde al wizard attuale** (`ImportWizardModal.svelte:120-132` STEP_DEFS a 7 id: upload/select/analyze/assets/fix/duplicates/review; visibilità condizionale `:2576-2595` coerente con la tabella docs). `brokers/import.en.md` **non** fu ritoccata dal rework → ancora 6 stadi vecchio modello (`:43-54`) | Task D5 (solo brokers/import) |
| 02 F2 (parser ereditato dal broker) | ✅ Aggiornato | **FATTO con deriva minore** | Meccanismo invariato: `models.py:405` `default_import_plugin`, `BrokerForm.svelte:225-231` (label i18n "Default Import Plugin"), override per file nel wizard (`ImportWizardModal.svelte:3045-3048` `ImportPluginSelect` con `compatiblePlugins`). `how-to.en.md:72` lo documenta. In `brokers/import.en.md:46` lo stadio si chiama ancora "Select Parser" mentre lo step reale è "Select Files" (i18n `step2Title`, `en.json:393`) | Task D5 |
| 02 F3 (Generic CSV: TRANSFER/FX_CONVERSION/CASH_TRANSFER documentati ma rifiutati) | in attesa (S6) | **MAI FATTO — ANCORA VALIDO (critical)** | Docs `generic-csv.en.md:42,43,45,50` invariati. Codice: `broker_generic_csv.py:534-536` (`TYPE_MAPPINGS.get` → `raise "Unknown transaction type"`), `:597` (TRANSFER → raise), `:602` (FX_CONVERSION → raise); verifica riprodotta: `python3 -c` su TYPE_MAPPINGS → `'cash_transfer' in keys == False`, `'fx_conversion' in keys == False` (presenti solo `transfer/transfer_in/transfer_out`, tutti rifiutati dopo) | Task D6 |
| 02 F4 (share % a Editor) | in attesa (S5) | **MAI FATTO — ANCORA VALIDO** | `sharing.en.md:52-59` (Joint Account Owner 50% / Editor 50%) e `:76` invariati; validatore `brokers.py:379-384` (`share_percentage must be 0 for role …`) invariato; guardie UI `BrokerSharingPanel.svelte:195,284,331` | Task D7 |
| 02 F5 (PDF accettato) | blocco 2 | **MAI FATTO — ANCORA VALIDO ed ESTESO** | Superfici note: `how-to.en.md:64`, `import/index.en.md:54` (card) e `:242` (tabella). Nuove superfici trovate oggi: `transactions/index.en.md:18` ("upload CSV or PDF exports"), `getting-started.en.md:53` ("CSV or PDF"). Codice: `accept=".csv,.xlsx,.xls"` (`ImportWizardModal.svelte:3577`); `broker_revolut.py:284-285` solo `.csv`; `grep -rln '\.pdf' backend/app/services/brim_providers/broker_*.py | wc -l` → **0** | Task D8 |
| 02 F6 (eToro XLSX) | in attesa (S4) | **MAI FATTO — ANCORA VALIDO** | `etoro.en.md:15,25`; `import/index.en.md:33` (card) e `:239` (tabella); codice `broker_etoro.py:182-183` solo `[".csv"]` | Task D9 |
| 02 F7 (Directa: tabella omette XLSX) | ✅ "Già allineato" | **PARZIALE — la chiusura non rispondeva al reperto** | Il reperto era sulla **tabella indice**: `import/index.en.md:240` dice ancora solo `CSV` (e la card `:40` "CSV files"). La pagina dedicata `directa.en.md:9,28` è corretta (CSV+XLSX) e il codice `broker_directa.py:179-180` restituisce `[".csv", ".xlsx"]` | Task D10 |
| 02 F8 (campi dedup incoerenti) | ✅ Aggiornato | **PARZIALE** | `how-to.en.md:253` allineata al modello (`type, date, amount, quantity and description` cfr. `brim.py:91-108`); `import/index.en.md:282` **invariata** ("date, type, asset, quantity, and amount" — asset come criterio-base, description omessa) | Task D11 |
| 02 F9 (Schwab "auto-skip" footer) | ✅ Aggiornato | **FATTO — regge** | `schwab.en.md:24-26` riformulato ("ignores rows that do not map … may emit warnings"); codice `broker_schwab.py:264` (`invalid date, skipping` + warning) invariato | — |
| 03 F1 (SNB "daily") | blocco 2 (critical) | **MAI FATTO — ANCORA VALIDO** | `snb.en.md:3,7,8,14` dicono ancora "daily" ×3 + "Daily on Swiss business days"; lista valute ferma a 10 (`:19`). Codice: `snb.py:5-8` ("monthly average … no daily dataset"), invariato | Task D12 |
| 03 F2 (chart settings localStorage) | ✅ Implementato | **FATTO — regge** (sezione C) | `chartSettingsStore.svelte.ts:6,9` docblock aggiornato, `:146,168` get/set `localStorage`; `chart-settings.en.md:65-67` ora vera | — |
| 03 F3 (header CSV FX → corruzione silenziosa) | ✅ Implementato | **FATTO — regge** (sezione C) | `FxDataImportModal.svelte:28-32` messaggio "Header currencies don't match" (4 lingue), `:59,163-165,177-179,187-191` gate `isPairDirectionAllowed`, `:131` blocco import; test negativo `fx-csv-import.spec.ts:227-233`; docs `fx/detail/data-editor.en.md:125-140` invariata e ora vera | — |
| 03 F4 (3 task AI Export FX) | in attesa (S5) | **MAI FATTO — ANCORA VALIDO** | `fx/detail/signals.en.md:51-56` elenca ancora FX Trend Review / FX Exposure Impact / FX Conversion Timing Context; catalogo pubblico: solo `fx.pair_analysis` + `fx.exposure_impact` (`shared.ts:200-215`; nomi display `en.json:2621-2628`) | Task D13 |
| 03 F5 (menu contestuale FX) | aperta (editoriale) | **MAI FATTO — ANCORA VALIDO** | `fx/index.en.md:23` "(Edit, Sync, Delete)"; codice `FxTable.svelte:288-326`: swap/sync/refresh/delete | Task D14 |
| 03 F6 (preset FX chart) | aperta (editoriale) | **MAI FATTO — AMPLIATO** | `fx/detail/chart.en.md:31,54` elenca 1W–2Y+Custom; `DateRangePicker.svelte:211-220` core ora include YTD+MAX **e** `:228-238` aggiunge i "jolly fill" 3Y/5Y/10Y/MTD/QTD/WTD (nuovi dal rework del picker) | Task D15 |
| 04 R-01 ("thirteen Analyses") | aperta (editoriale) | **MAI FATTO — ANCORA VALIDO** | `ai-export/index.en.md:21-22` "thirteen"; `analyses/catalog.py:26-27,241` `EXPECTED_ANALYSIS_COUNT = 11` (+ assert); le tabelle della pagina stessa elencano 11 voci; traduzioni portano lo stesso errore: `index.it.md:22` "tredici", `index.fr.md:23` "treize", `index.es.md:22` "trece" | Task D16 |
| 04 R-02 ("Signals header" per Asset/FX) | aperta (major) | **MAI FATTO — ANCORA VALIDO** | Docs: `ai-export/index.en.md:18`, `asset.en.md:8`, `fx.en.md:9` (IT uguale: `asset.it.md:8`). Codice: `assets/[id]/+page.svelte:1855` — `<AiExportMenu>` dentro lo snippet `actions` di `<PageToolbar>` (`:1814`); `fx/[pair]/+page.svelte:199` commento "AI export (page toolbar)" | Task D17 |
| 04 R-03 (Entity Directory non copre L#) | aperta (minor) | **MAI FATTO — ANCORA VALIDO** | `ai-export/index.en.md:117-126` invariato; `AiExportEntityDirectory` (`ai_export_runtime.py:361-368`) ha solo `assets/brokers/fx_pairs`; `lot_ref=f"L{index}"` resta riga-embedded (`asset_core.py:551`) | Task D18 |
| 04 claim positive campionate (sampling 8/16/30, 6/12/24; indicatori 5/10/∞; bucket 30/14/7gg; draft 10 min sessionStorage; catalogo 8+11) | verificate | **FATTO — reggono** | `technical_context.py:58-66` (6/12/24, 8/16/30), `policy.py:44-48` (30/14/7), `:84-88` (5/10/None), `aiExportMemory.ts:11` (TTL 10 min) + `:90-93` (default sessionStorage), `datasets/catalog.py:44,867` (8 pubblici), `shared.ts` = 19 entry (`grep -c "id: '"` → 19) | — |
| Drawdown full_history (beta 02/09) | — (post-audit) | **nessuna contraddizione** | `drawdown_context.py` ora ignora lo start richiesto (diff working tree: "computed over the FULL available history", start = `Date.min` per ASSET / prima transazione per PORTFOLIO). Le pagine AI Export citano Drawdown solo come contenuto ("historical context only", `portfolio.en.md:83-85`; `asset.en.md:17,40,42`; `index.en.md:92`) senza claim sulla finestra → nessuna pagina smentita; semmai omissione info: la semantica full-history non è documentata | Task D19 (info) |

Conteggio riprodotto pagine: `find mkdocs_src/docs -name "*.en.md" -not -path "*/developer/*" | wc -l` → **182** (immutato rispetto alla baseline). Le 103 pagine developer EN-only della baseline esistono ora come `.md` senza suffisso (`find mkdocs_src/docs/developer -name "*.en.md"` → 1; `-name "*.md"` → 105): rinormalizzazione i18n della guida developer, fuori scope ma da sapere per i futuri audit developer.

## B. Nuove discrepanze docs↔codice

| # | Discrepanza | Evidenza docs | Evidenza codice | Gravità |
|---|---|---|---|---|
| B1 | **`brokers/import.en.md` descrive il wizard pre-rework**: 6 stadi (Upload Files → Select Parser → Operation Analysis → Asset Resolution → Opening-Date Gate → Bulk Staging & Commit); mancano del tutto Unify assets, Corrections, Duplicates; la carousel screenshot (`:35-40`) titola ancora "Step 2: Parser Config", "Step 4: Asset Resolution" | `brokers/import.en.md:43-54` | `ImportWizardModal.svelte:120-132` (7 STEP_DEFS), step opzionali `:2576-2587`, render `:3564-4102`; gate opening-date spostato nel Review (`:581,608-612,830`) | major |
| B2 | **`getting-started.en.md` sezione "3. Import Your First Statement" sul wizard pre-rework**: 6 passi con "Parser Configuration" come passo 2, "Broker & Asset Resolution" passo 4, "Duplicate Detection" passo 5, "Staging & Final Review" passo 6; più "(CSV or PDF)" | `getting-started.en.md:41-100` (PDF a `:53`) | stesso codice di B1 | major |
| B3 | **Context menu Assets**: docs "(Edit, Delete, Sync)" — Edit non esiste, mancano Refresh e **Merge** (azione aggiunta col rework import, commit `571bcde0`) | `assets/index.en.md:31` | `AssetTable.svelte:303-351` (sync/refresh/merge/delete) | minor |
| B4 | **"Live Ticker" su Dashboard**: docs "live price badges on the **Dashboard** and Asset Detail pages … polls every 30 seconds" — il componente `LiveTicker.svelte` è stato eliminato nel ciclo S1–S3 (`be8394bb`); il polling 30s oggi è inline in **Assets list** e **Asset Detail**; sul Dashboard non c'è alcun polling né badge live | `assets/index.en.md:51-57` | `assets/+page.svelte:399` (`setInterval(fetchLivePrices, 30_000)`), `assets/[id]/+page.svelte:957`; `grep -rn "setInterval" frontend/src/lib/components/dashboard/ routes/(app)/dashboard/+page.svelte` → 0 risultati | minor |
| B5 | **Preset Asset Detail chart**: "1W, 1M, 3M, 6M, 1Y, ALL" — mancavano 2Y/YTD già all'audit (pagina data per pulita), oggi mancano anche i fill preset 3Y/5Y/10Y/MTD/QTD/WTD | `assets/detail/chart.en.md:19` | `DateRangePicker.svelte:211-220,228-238` | minor |
| B6 | **AI Export Asset: "five Asset tasks" inesistenti** — Asset Snapshot, Asset Trend Analysis, Position Review, Recurring Investment Timing, Drawdown and Recovery. Il menu reale offre 4 voci: dataset "Position & Market History (full)" e "Market History Only (no holdings)", analysis "Position Review" e "Asset Market Analysis". Mai auditata: il box era "fuori standard" per 01 e la pagina non era in scope per 04 | `assets/detail/signals.en.md:55-62` | `shared.ts:97-110,185-199`; display names `en.json:2610-2616` (`aiExport.analysis.asset.*`), `:2769-2776` (`aiExport.dataset.asset.*`) | **major** |
| B7 | **Files → Broker Reports: azione "🔄 Reprocess" inesistente** — il context menu reale ha solo Preview / Download / Delete (+ Copy Link per static). `grep -rn -i "reprocess" frontend/src backend/app` → 0 risultati; mai esistita in `git log -S "reprocess"`. Conseguenza: anche il tip "re-process from the Files & Uploads page" (`getting-started.en.md:63-65`) e "re-import them" (`how-to.en.md:30-32`) puntano a un'azione che non c'è; il percorso reale è lo step 2 "Select Files" del wizard, che elenca i report già caricati | `files/index.en.md:76-79`; `getting-started.en.md:63-65`; `how-to.en.md:30-32` | `FilesTable.svelte:346-403` (row actions), `files/+page.svelte:739-760` (solo onDelete/onPreview), wizard `ImportWizardModal.svelte:3667+` (brokerFilesMap) | **major** |
| B8 | **Delete di un report "rimuove statement e transazioni dal ledger"** — falso: `delete_upload` cancella file + metadata, nessuna cascata sulle transazioni | `files/index.en.md:79-81` | `static_uploads.py:430-459`, `api/v1/uploads.py:291-322` | major (aspettativa dati errata) |
| B9 | **Upload da Files "runs the guided Import Wizard"** — falso: l'upload dalla pagina Files salva il file con associazione broker e ricarica la lista; nessun wizard viene lanciato (mai esistito: `git log -S "ImportWizard" -- files/+page.svelte` → vuoto) | `files/index.en.md:69-72` | `files/+page.svelte:436-463` (`confirmBrimUpload` = solo POST upload + reload) | major |
| B10 | **Drag-and-drop "nella lista transazioni"** — la pagina Transactions non ha drop zone (`grep -rn "ondrop\|dragover" routes/(app)/transactions/` → 0); il drag&drop esiste solo **dentro** lo step 1 del wizard (`FileUploader.svelte:201-202`). Il claim within-wizard (`how-to.en.md:64`) è invece corretto | `how-to.en.md:11`; `getting-started.en.md:53`; `transactions/index.en.md:29` | vedi comandi; nessun handler nella pagina | minor |
| B11 | Label bottoni: docs "**+ New Transaction**" vs UI "Add Transaction"; docs "**New Broker**" vs UI "Add Broker" (preesistenti, non colti dall'audit) | `transactions/index.en.md:28`; `brokers/index.en.md:15` | `en.json` `transactions.addTransaction`="Add Transaction" (`transactions/+page.svelte:742-743`); `brokers.addBroker`="Add Broker" (`brokers/+page.svelte:353`) | info |
| B12 | **i18n a due generazioni indietro sul wizard**: how-to IT/FR/ES dicono "5 passi operativi" (testo pre-remediation: mai ricevuto né il fix a 4 step né il rework a 7). Stessa classe: `positions.it/fr/es.md:42` (vecchia tabella Performance), `etoro.it.md:25` + `index.it.md:33,239` (XLSX), `how-to.it.md:42` (PDF), `ai-export/index.it/fr/es` ("tredici/treize/trece") | `how-to.it.md:38`, `how-to.fr.md:38`, `how-to.es.md:38` (`wc -l`: EN 272 righe vs IT/FR/ES 137) | wizard attuale `ImportWizardModal.svelte:120-132` | major (batch) |

Note di non-discrepanza verificate (richieste dal mandato):

- **TransactionDeleteModal eliminato**: `grep -rn "TransactionDeleteModal" frontend/src mkdocs_src/docs` → 0 risultati. Nessuna pagina descriveva il vecchio modale di conferma; il delete singolo oggi apre il workspace bulk pre-marcatо (`transactions/+page.svelte:654-665`) e la frase docs "click the trash icon to delete, or check multiple rows to perform bulk deletions" (`transactions/index.en.md:31`) resta valida. Nessuna azione.
- **Fix decimali/stepper nei form** (`TransactionFormModal`: quantity iniziale vuota, duplicate preserva la data; `CompactCashCell`): nessuna pagina utente descrive quei dettagli → nessuna deriva.
- **Tooltip con delay 500ms** (`Tooltip.svelte` diff: `showDelayMs = 500`): i docs citano solo tooltip dei grafici ECharts, non il componente → nessuna deriva.
- **Nota "Net Worth includes cash" (working tree, kpi-cards.*.md 4 lingue)**: verificata contro il codice — `portfolio_engine.py:1003-1005` `nav = broker_nav + in_transit_mv` con `broker_nav = market_value + cumulative_cash`; la nota e il tooltip i18n `dashboard.netWorthTooltip` (presente in en/it/fr/es) corrispondono. ✅
- **Reorder route FX** (`provider.en.md:36` drag&drop/frecce): regge, ma il percorso codice è cambiato — `FxProviderConfig.svelte` eliminato; ora `FxPairAddModal` in `editMode` (`fx/[pair]/+page.svelte:1321`) + `FxProviderSelect.svelte:27,488` (`OrderableList` con `onReorder`).
- **Tab Risk (beta)** su Dashboard e Broker: le docs dicono "three primary tabs" (`dashboard/index.en.md:13`) e "four primary tabs" (`brokers/index.en.md:31`) mentre il codice ne monta 4/5 (`dashboard/+page.svelte:212-215`, `brokers/[id]/+page.svelte:198-203`). Esclusione deliberata per la regola "superfici beta Risk Analysis non sono reperti", coerente con l'audit originale.
- **Chiavi i18n citate nei docs**: nessuna pagina `user/**.en.md` cita chiavi i18n (`grep -rn "importWizard\.\|transactions\.table\." mkdocs_src/docs/user --include="*.en.md"` → 0). Le chiavi rimosse nel working tree (blocco `deleteModal.*`, ecc.) non rompono alcuna pagina.

## C. Voci Blocco 1 eseguite il 2026-08-05: reggono?

Nel perimetro di QUESTO report (01–04) le voci Blocco 1 implementate sono **2**; la
tassonomia ne registra 5 in totale — `05 A1`, `05 A3`, `05 B1` appartengono al report
admin (altro ambito di verifica; incidentalmente `api/v1/auth.py:190` mostra oggi
`if not registration_enabled and not is_first_user`, coerente con la chiusura di A1).

| Voce | Esito 2026-09-02 | Evidenza |
|---|---|---|
| 03 F2 — persistenza `localStorage` Chart Settings FX | **REGGE** | `chartSettingsStore.svelte.ts:9` ("settings live in user-scoped localStorage and survive refresh"), `:146` `localStorage.getItem(storageKey)`, `:168` `localStorage.setItem(...)`; la pagina `chart-settings.en.md:65-67` promette ora il vero |
| 03 F3 — rifiuto header CSV FX con valute estranee (corruzione silenziosa dati) | **REGGE** | `FxDataImportModal.svelte:28-32` (messaggio localizzato "Header currencies don't match", identico alla tabella errori docs `fx/detail/data-editor.en.md:140`), `:130-133` (`handleImport` esce se `headerMismatchError`), `:159-169` (gate su direzione `<`), `:172-184` (gate su `>`), `:187-191` (`isPairDirectionAllowed` contro `displayBase`/`displayQuote`); test E2E negativo dedicato `frontend/e2e/fx/fx-csv-import.spec.ts:227-233` ("rejects CSV header currencies that do not match page pair", riempie `date;GBP>JPY` e asserisce il testo d'errore) |

Entrambe le direzioni di remediation (documentazione non toccata perché già corretta,
codice esteso fino alla promessa) restano valide a un mese di distanza; il gate F3
sopravvive invariato anche nel diff working-tree del 02/09.

## Task riesumati + nuovi task docs

Riesumati (dai report sorgente, ancora aperti):

| # | Task | Evidenza | Stima |
|---|---|---|---|
| D1 | Riscrivere le due percentuali in `kpi-cards.*.md`: Card 1 → denominatore = Total P&L di ieri (R-02); Card 3 → è il ROI since-inception (`total_gain_loss_percent`), non un delta giornaliero (R-03, formulazione cambiata rispetto all'audit perché il codice è cambiato) | A: R-02/R-03 | S |
| D2 | Completare R-05: tabella Holdings → 13 colonne reali o nota "sottoinsieme", label "PMC" | A: R-05 | S |
| D3 | R-11: rimuovere la riga "Date Format" da `preferences.*.md` (o implementare la feature — tier S4) | A: R-11 | S |
| D4 | R-12: togliere "(backend + frontend)" da `about.*.md` | A: R-12 | S |
| D6 | 02-F3 (critical): rimuovere TRANSFER/FX_CONVERSION/CASH_TRANSFER da `generic-csv.*.md` (`:42,43,45,50`) o implementarli (tier S6) | A: F3 | S (docs) / L (codice) |
| D7 | 02-F4: riscrivere esempio Joint Account e riga Spouse in `sharing.*.md` con due Owner | A: F4 | S |
| D8 | 02-F5: togliere "PDF" da 4 superfici (`how-to:64`, `import/index:54,242`, `transactions/index:18`, `getting-started:53`) o decidere il parser PDF (blocco 2) | A: F5 | S (docs) / L (codice) |
| D9 | 02-F6: correggere eToro a CSV-only in `etoro.*.md` + card/tabella indice | A: F6 | S |
| D10 | 02-F7: aggiornare cella Format Directa in `import/index.*.md` (`:240` + card `:40`) a CSV/XLSX | A: F7 | S |
| D11 | 02-F8: allineare `import/index.en.md:282` ai campi reali (type/date/quantity/amount + description per LIKELY; asset come qualificatore `_WITH_ASSET`) | A: F8 | S |
| D12 | 03-F1 (critical): riscrivere `snb.*.md` a "monthly" + lista ~25 valute, o nuova sorgente daily (blocco 2) | A: F1(03) | S (docs) / L (codice) |
| D13 | 03-F4: allineare `fx/detail/signals.*.md:51-56` ai 2 task reali | A: F4(03) | S |
| D14 | 03-F5: elenco azioni menu FX → "Swap, Sync, Refresh, Delete" | A: F5(03) | S |
| D15 | 03-F6 + B5: aggiornare preset in `fx/detail/chart.*.md:31,54` e `assets/detail/chart.*.md:19` (core 1W–2Y+YTD+MAX + fill 3Y/5Y/10Y/MTD/QTD/WTD) | A: F6(03), B: B5 | S |
| D16 | 04-R-01: "thirteen" → "eleven" in `ai-export/index.*.md` (4 lingue) | A: R-01 | S |
| D17 | 04-R-02: "Signals header" → "page toolbar" in `ai-export/index|asset|fx.*.md` (4 lingue) | A: R-02 | S |
| D18 | 04-R-03: precisare che L# è riga-embedded, non risolto dall'Entity Directory | A: R-03 | S |
| D19 | (info) Documentare che il Drawdown AI Export è sempre full-history | A: drawdown | S |

Nuovi (nati o scoperti in questo giro):

| # | Task | Evidenza | Stima |
|---|---|---|---|
| N1 | Riallineare `brokers/import.*.md` al wizard a 7 step (4 sempre + 3 condizionali), specchio di `how-to.en.md` | B1 | M |
| N2 | Riscrivere la sezione Import di `getting-started.*.md` (6 passi → flusso attuale, togliere PDF) | B2 | M |
| N3 | Correggere B6: `assets/detail/signals.*.md` — 5 task → le 4 voci reali del catalogo | B6 | S |
| N4 | Correggere B7+B8+B9 su `files.*.md`: togliere "Reprocess", correggere la semantica del Delete (solo file), correggere "runs the guided Import Wizard"; citare come percorso di riesame lo step 2 del wizard | B7-B9 | S |
| N5 | Allineare `assets/index.*.md`: context menu (sync/refresh/merge/delete) e sezione Live Ticker (Assets list + Asset detail, non Dashboard) | B3, B4 | S |
| N6 | Togliere il drag-and-drop "nella lista" da 3 pagine (resta vero dentro il wizard) | B10 | S |
| N7 | Label bottoni: "Add Transaction" / "Add Broker" | B11 | S |
| N8 | Batch traduzioni multi-lingua (rinviato dal 05/08): ora include anche il rework wizard (how-to/brokers-import/getting-started) — due generazioni di debito | B12 | L |
| N9 | (tooling, opzionale) insegnare a `dev.py check-links` i template literal annidati per estinguere il falso positivo `${lang` | A: check-links | S |

## Cross-reference

- Voci fuori perimetro assegnato ma correlate: Blocco 1 `05 A1/A3/B1` (report admin),
  `06A R-03`, `06B B1`, `06C F1` (teoria) — da riverificare nei report fratelli di
  questa tornata.
- Il debt i18n (N8) è trasversale: riguarda anche le voci dei report 05/06/07.
- [16_feature_perse_nei_redesign.md](../../../phases/05_cleanAudit/16_feature_perse_nei_redesign.md)
  documenta capacità perse nei redesign — B4 (Live Ticker) è un'istanza ulteriore lato docs.
- Il manifest baseline (182 pagine EN) è riprodotto e immutato; la guida developer è
  passata da `.en.md` a `.md` plain (105 file) — la futura ripresa dell'audit developer
  deve usare i nuovi path.

---

### Riepilogo finale

1. Voci decadute (fix fatti ma non più veri): **1** — 02-F1/F2 su `brokers/import.en.md` (riallineata il 05/08, superata dal rework wizard dell'08–12/08).
2. Voci ancora valide mai corrette: **15** (01: R-02, R-03, R-11, R-12; 02: F3, F4, F5, F6; 03: F1, F4, F5, F6; 04: R-01, R-02, R-03) + **3 parziali** (01-R-05; 02-F7, F8: la metà su `index.en.md` non fu mai toccata).
3. Nuove discrepanze trovate: **12** (B1–B12), di cui 4 major (B1, B2, B6, B7-B9 cluster Files).
4. Peggior sorpresa: **B6** — `assets/detail/signals.en.md` promette 5 task AI Export Asset di cui 4 inesistenti ("Asset Snapshot", "Asset Trend Analysis", "Recurring Investment Timing", "Drawdown and Recovery"): mai auditata perché cadeva nella fessura fra il report 01 (box escluso) e il report 04 (solo pagine ai-export/*). Subito dopo, **B7**: il "Reprocess" dei report broker documentato in `files/index.en.md` non è mai esistito nel codice.
5. Blocco 1 in-scope (03-F2, 03-F3): **regge tutto**, incluso il test E2E del caso negativo FX.
6. i18n: il batch rinviato è ora a due generazioni di debito sul wizard (IT/FR/ES a "5 passi").
