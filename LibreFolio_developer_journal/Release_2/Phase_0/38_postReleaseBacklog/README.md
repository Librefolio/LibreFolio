# 38 · Backlog dopo la 1.2

> **Aperta il 2026-10-09** dal coordinatore della Release 2, nel treno dell'archivio (treno 25). Contiene:
>
> - i **residui delle cartelle archiviate il 09/10** in `Release_2/phases/` (voci N-, O-, L, K-, P-, I-). ID e titoli
>   sono quelli che i piani archiviati citano: non vanno rinominati;
> - il **backlog del coordinatore** (voci C-), raccolto dal 06/10 e riverificato il 09/10 sul codice del treno 25.
>
> Non contiene le voci aperte delle cartelle che restano in `Phase_0/` (02, 09, 13, 16, 21, 27, 32, 37): vivono
> lì. Il developer, il 09/10, sulle voci dopo la 1.2: «si a tutto, dopo».

## Regole

- Le righe di codice sono quelle del 09/10: le voci dei figli su `3cceb4f90`, le voci C- sull'albero del treno 25.
  Prima di lavorare una voce, si riverifica.
- Una voce non si cancella: si chiude con data, commit e una nota. Una voce che parte apre un piano in
  `Phase_0/<NN_area>/` e qui riceve il link.
- Peso: minimo, basso, medio-basso, medio, alto. «Decisione» vuol dire che serve una scelta del developer prima del
  codice.

## Indice

| Gruppo | Origine | Voci |
|---|---|---|
| N | `phases/28_fxDashboardSync/`, `phases/15_parallelRuntimeIsolation/` | N-1 … N-9 |
| O | `phases/29_i18nAudit/`, `phases/11_feedbackContractsRunes/` | O-1 … O-20 |
| L | `phases/26_brimDanskeBank/`, `18_brimTargeted/`, `33_e2eImportInfra/`, `34_accountAndIdReuse/` | L1 … L12 |
| K | `phases/25_taxonomySelect/` (step 23 e verifica d'archivio) | K-1 … K-26 |
| P | `phases/30_wacUnification/`, `phases/39_autoCostNoPosition/` | P-1 … P-11 |
| I | `phases/20_performanceCharts/`, `19_yieldOnCost/`, `24_privacyGlobal/` | I-01 … I-12 |
| C | backlog del coordinatore, riverificato il 09/10 | C-1 … C-42 |

In fondo: le voci del backlog del coordinatore **tracciate altrove** e quelle **chiuse alla verifica del 09/10**.

## N · Dashboard, FX, cache e runner

Origine: [28_fxDashboardSync](../../phases/28_fxDashboardSync/README.md) e
[15_parallelRuntimeIsolation](../../phases/15_parallelRuntimeIsolation/plan-phase00ParallelRuntimeIsolation.prompt.md).

- **N-1 · «Mostra il vecchio, aggiorna in background» fuori dal portafoglio** — medio, richiesta del developer.
  È la fase 2 del principio del developer del 06/10 22:21 («anche per gli asset e le forex, file, tutto»), mai
  avviata. Le pagine cancellano i dati e mostrano il caricamento: `frontend/src/lib/stores/core/TimeSeriesStore.ts:211-212`
  (`invalidateAll` cancella, niente `replaceRange`), `stores/core/entityStore.ts:180-191`,
  `routes/(app)/fx/+page.svelte:710`, `:944`, `files/+page.svelte:315`, `:779`, `transactions/+page.svelte:132`,
  `assets/+page.svelte:403-405`, `:1597`. La regola è scritta solo per gli store del portafoglio
  (`mkdocs_src/docs/developer/frontend/state/domain-state.md:22`), non in `.github/instructions/frontend.instructions.md`,
  e il contributo del broker nel dettaglio broker non la segue. Origine:
  [Step2PageCache](../../phases/28_fxDashboardSync/plan-phase00FxDashboardSyncStep2PageCache.prompt.md), §3.1-quater.
- **N-2 · Riepilogo generico quando fallisce solo il combine della coverage** — basso. Il runner scrive «Some tests
  failed, but coverage was still tracked» (`scripts/test_runner/_cli.py:1200`, `:1317`). Origine:
  [CoverageCombineRace](../../phases/28_fxDashboardSync/plan-phase00CoverageCombineRace.prompt.md).
- **N-3 · Una parte di coverage illeggibile rende rosse le passate successive** — basso. La parte resta in
  `parts/run-*`, e ogni passata rifà il combine su `RUN_PARTS_DIR` (`scripts/test_runner/_executor.py:232-271`,
  `:264-268`). Origine: CoverageCombineRace.
- **N-4 · SIGTERM durante il salvataggio della coverage** — basso, mitigato nel runner (`scripts/test_runner/_coverage.py:42`,
  `:66`). Le cause: `backend/app/services/risk/quant/spawn_worker.py:280-282` (`join(1.0)`, poi `terminate()`),
  `backend/app/services/tools/process_tree.py:196`, `:204` (`killpg(SIGTERM)`, poi `terminate()`) e, a monte,
  `_on_sigterm` di coverage 7.16.0 (`coverage/control.py:756`), che non è rientrante: da segnalare a monte. Origine:
  CoverageCombineRace, §4b.
- **N-5 · Commenti superati dalla cache della fase 1** — basso. Dicono che una mutazione scarta le risposte in volo:
  `frontend/e2e/portfolio/risk-lab.spec.ts:3319`, `:6969-6973`; `frontend/src/routes/(app)/assets/+page.svelte:418-419`.
  Origine: lotto 2 di N (07/10).
- **N-6 · Doc sviluppatore falsa sullo stato del frontend** — ✅ chiusa il 09/10 da Q (S23, treno 27). Era: basso. `mkdocs_src/docs/developer/frontend/state/registries.md:29`
  (WebSocket e SSE: nessun uso nel frontend) e `:55-56` (`getStore("AAPL")`; l'API è
  `getAssetPriceStore(assetId, currency)`, `assetPriceStoreRegistry.ts:39`); `developer/frontend/index.md:47` (il
  DateRange non è in `app/` ma in `stores/dateRangeStore.svelte.ts`) e `:54` (`registries/` non esiste). Origine:
  Step2PageCache, passo 9.
- **N-7 · `cli_tools.en.md:8`: i comandi del database «funzionano con `exec`»** — ✅ chiusa il 09/10 nel treno 25
  (M, lotto 8): la nota distingue `db current` e `db check`, che nel container funzionano, da `db upgrade` e
  `db downgrade`, che vogliono il server fermo. Le traduzioni restano in I-08. Origine:
  [DbPathArgument](../../phases/28_fxDashboardSync/plan-phase00DbPathArgument.prompt.md).
- **N-8 · Docker: un `PORT` in `.env` arriva nel container** — basso, letto nel codice e non provato.
  `docker-compose.yml:46` (`env_file`) porta `PORT` nel container, il server ascolta sempre su 6040 (`Dockerfile:158`)
  e `scripts/cli_base.py:80-82` legge `PORT`: con un `PORT` diverso da 6040, `db upgrade` via `exec` controlla la
  porta sbagliata. Origine: DbPathArgument.
- **N-9 · devWiki: il backward-fill FX illimitato** — ✅ chiusa il 09/10 (treno 26): pagina
  `LibreFolio_devWiki/wiki/problems/fx-backward-fill-unbounded-stale-rates.md`, scritta dall'historian e verificata sul
  codice. Era: basso, knowledge base. Trasforma i buchi interni in tassi
  stantii senza avviso (`backend/app/services/fx.py:1247`, `:1384`); la pagina promessa da D6 non è mai stata scritta.
  Va fatta con l'aggiornamento della knowledge base. Origine:
  [FxDashboardSync](../../phases/28_fxDashboardSync/plan-phase00FxDashboardSync.prompt.md), §11.

## O · i18n, contratti e Runes

Origine: [29_i18nAudit](../../phases/29_i18nAudit/plan-phase00I18nAudit.prompt.md) (O-1…O-18, §11) e
[11_feedbackContractsRunes](../../phases/11_feedbackContractsRunes/plan-phase00FeedbackContractsRunes.prompt.md)
(O-19, O-20).

- **O-1 · Famiglia i18n fantasma `tools.allocation.constraints.`** — basso. `backend/app/services/pac_allocator/evaluator.py:968`
  scrive una `explanation_key` che il frontend non legge mai, e il catalogo non ha chiavi; l'audit la elenca fra le
  famiglie del backend senza chiavi. Origine: 29, §2.4, decisione 7.
- **O-2 · File morti per knip: `onboardingTourSurfaces.svelte.ts` ed `EditBuffer.ts`** — basso.
  `frontend/src/lib/features/onboarding/onboardingTourSurfaces.svelte.ts` e `frontend/src/lib/stores/core/EditBuffer.ts`
  non hanno import fuori dai test. Con il primo vanno i flag `*TourPreview` delle pagine, mai veri
  (`assets/+page.svelte:149`, `fx/+page.svelte:119`, `brokers/+page.svelte:62`; Q, 07/10). Origine: 29, secondo turno.
- **O-3 · `ensure_started()` documentato ma inesistente** — ✅ chiusa il 09/10 da Q (S23, treno 27). Era: basso. `.github/instructions/backend-testing.instructions.md:109`,
  `.github/skills/devpy-tools/testing-backend/SKILL.md:107`, `LibreFolio_developer_journal/knowledge_base/06_testing_backend.md:138`;
  esiste solo `start_server()` (`backend/test_scripts/test_server_helper.py:294`). Origine: 29, S15.
- **O-4 · Descrizione vecchia dell'azione `api system` nel runner** — minimo. `scripts/test_runner/_backend_api.py:246`
  dice ancora «parse_pipfile, deps». Origine: 29, S15.
- **O-5 · `FixFlaggedStep` traduce le notice con una copia locale** — basso.
  `frontend/src/lib/components/transactions/import/FixFlaggedStep.svelte:134-138` chiama `$t(key)` senza i valori del
  `context`, mentre il risolutore condiviso `resolveBrimNotice.ts` li passa; i suoi test non coprono il testo.
  Origine: 29, S19.
- **O-6 · Dialogo di conferma del bulk senza agganci per i test** — basso. `TransactionBulkModal.svelte:3487-3502`
  non passa `testId` a `ConfirmModal`, e l'interruttore e le voci della lista non hanno agganci. In più
  `ConfirmModal.svelte:118` ha un ripiego inglese senza plurale, `` `${items.length} items` ``. Origine: 29, S19.
- **O-7 · `schemas/brim.py` descrive `message` come ripiego inglese** — minimo. `backend/app/schemas/brim.py:712`,
  ma i plugin scrivono nella lingua del file, anche in italiano. Origine: 29, S19.
- **O-8 · Stringhe fisse in inglese nell'editor dei dati degli asset** — medio-basso: in IT, FR ed ES si vede
  inglese. `frontend/src/lib/components/assets/AssetDataEditorSection.svelte:466-467` («Failed to save: …», «Save
  failed: …») e il prefisso «Asset data:» del toast a `:444` (K, 08/10); `dataEditor.saveFailed` esiste già.
  Origine: 29, S20.
- **O-9 · Parametri di justETF senza chiavi i18n** — basso. `backend/app/services/asset_source_providers/justetf.py:219-222`:
  non esiste `assets.providerParams.justetf.*`, quindi il form mostra le chiavi e il tooltip resta in inglese. Lo
  stesso vale per CSS Scraper: `frontend/src/lib/i18n/en.json:362-376` ha solo `borsa_italiana` (Q, 08/10).
  Origine: 29, S20.
- **O-10 · `provider-contracts` registrato senza classe d'isolamento** — minimo. `scripts/test_runner/_backend_services.py:1031`
  non ha `isolation=`, benché il test sia offline. Origine: 29, S20.
- **O-11 · Titolo di U1: "block Continue"** — minimo. `frontend/e2e/transactions/tx-import-report-set.spec.ts:2863`:
  il test controlla `import-wizard-parse`. Origine: 29, S20.
- **O-12 · `importWizard.assetsCount` senza plurale** — basso. `ImportWizardModal.svelte:4678` e il catalogo («{n}
  unique assets, {m} need resolution»). Origine: 29, S21.
- **O-13 · IWR-001 cerca il badge per classe CSS** — minimo. `frontend/e2e/transactions/tx-import-resolution.spec.ts:331`
  usa `[class*="amber"]`, mentre l'aggancio `import-wizard-unresolved-count` esiste. Origine: 29, S21.
- **O-14 · Riga booleana `scheduler_enabled` senza `data-testid`** — minimo.
  `frontend/src/lib/components/settings/tabs/GlobalSettingsTab.svelte:583`; le altre righe ce l'hanno (`:603`,
  `:626`). Origine: 29, S21.
- **O-15 · Errori di rete al login in inglese** — basso. `auth.ts:143` mostra il messaggio di axios, mentre
  `auth.serverUnreachable` esiste già. Origine: 29, S21.
- **O-16 · Plurale scritto a mano nel tooltip del Gantt dei lotti** — basso. `LotGanttChart.svelte:701`. Origine: 29, §6.
- **O-17 · Debito Prettier in `DistributionDialog.svelte`** — minimo, dominio del PAC (D): `DistributionDialog.svelte:74-126`,
  già alla base; anche i piani della 13 lo citano. Origine: 29, §8.
- **O-18 · Segnalare a monte la cache di svelte-i18n** — basso, decisione del developer mai presa.
  `getMessageFormatter` (svelte-i18n 4.0.1, `runtime.js:383-392`, `:496-500`) tiene in cache i formattatori per testo
  e ignora la lingua: un messaggio identico in due cataloghi usa le regole di plurale della prima lingua che lo
  compila. Origine: 29, §4; pagina devWiki `svelte-i18n-formatter-cache-ignores-locale.md`.
- **O-19 · Catene FX: chiave `leg_rates` senza provider ed estremi invertiti** — da misurare.
  `backend/app/services/fx.py:820`, `:893`, `:680-716`: la chiave non ha il provider e gli estremi possono essere
  invertiti; serve un test di caratterizzazione. Origine: 11, §9.
- **O-20 · Doppia sync alla creazione di un asset dalla pagina Asset** — basso. `AssetModal.svelte:1451-1462` più
  `assets/+page.svelte:1828-1833`. Origine: 11, Round 1 §2.

## L · Import e upload

Origine: [26_brimDanskeBank](../../phases/26_brimDanskeBank/plan-phase00BrimDanskeBank.prompt.md), §12 (L1–L9),
[18_brimTargeted](../../phases/18_brimTargeted/plan-phase00BrimTargeted.prompt.md) (L10),
[33_e2eImportInfra](../../phases/33_e2eImportInfra/plan-phase00E2eImportInfra.prompt.md) (L11) e
[34_accountAndIdReuse](../../phases/34_accountAndIdReuse/plan-phase00AccountAndIdReuseStep2LastAdmin.prompt.md) (L12).

- **L1 · Un membro del set cancellato (A17)** — medio. `backend/app/services/brim_report_sets.py:228-244`, `:342-344`;
  `ReportSetCard.svelte:232`.
- **L2 · Le rettifiche negative e il capitale investito (A6)** — medio. `portfolio_engine.py:1641`,
  `fifo_lot_engine.py:529`. È la voce 8 del 06/10, «dopo la 1.2».
- **L3 · Crédit Agricole sui report set (§2.9, A10)** — medio, decisione di prodotto: il parser resta a file
  singolo o diventa un set.
- **L4 · Upload: il `.json` sovrascritto dal sidecar e le estensioni lunghe (F3, F4, F3-bis, F4-bis)** — medio; F3 è
  una perdita di dati. Un `.json` caricato ha lo stesso nome `{id}.json` dei propri metadati, che lo sovrascrivono
  (BRIM: `brim_provider.py:803-807`, `:835`; upload generici della pagina File: `static_uploads.py:15`); un'estensione
  di 300 caratteri dà un errore 500; l'`accept` dei selettori è statico; i `.json` già rotti vanno riconosciuti. Per
  gli upload BRIM il developer la vuole risolta «per un futuro in cui generalizziamo generic csv» (06/10 22:50).
- **L5 · `get_file_path` sull'event loop** — basso. `backend/app/api/v1/brokers.py:693`, `:765`: solo `:863` usa
  `asyncio.to_thread`.
- **L6 · Il nome salvato nel rifiuto del plugin** — basso. `brim_provider.py:1169` mostra il nome salvato, non
  quello originale.
- **L7 · Un plugin di set scelto a mano per un file che non legge** — basso. `importReportSets.ts:131-139` contro
  `brim_report_sets.py:134`.
- **L8 · Il ripiego `auto` → CSV generico** — basso. `brokers.py:861-875`. La doc dice ora che il Generic CSV non è
  un ripiego universale (`brim/architecture.md:46`), ma non descrive questo ripiego.
- **L9 · `clean_data_dirs` che conta «(0 files)»** — basso. `populate_mock_data.py:3317`.
- **L10 · Commento obsoleto nel parser CA** — basso. `broker_credit_agricole.py:1313`: `noqa: C901 —
  TODO(P2-refactor) … nested trade-resolution closures`, ma le closure non ci sono più.
- **L11 · Qualità degli spec d'import** — medio. IWR-005/006/010, le sonde `formClose`, i `waitForTimeout` di
  CAC-009/010, T1–T8, CAC-001/006/007/011/012, `tx-brim-import` seriale: il dettaglio è nel §7 del piano 33.
- **L12 · Gli utenti E2E alice…eve creati amministratori** — basso. `scripts/test_runner/_frontend_common.py:192` li
  crea con `create-superuser`; dovrebbero essere utenti normali, salvo `e2e_test_admin`.

## K · Bulk delle transazioni

Origine: [25_taxonomySelect](../../phases/25_taxonomySelect/README.md), archiviata il 09/10 (treno 26). K-1…K-4 vengono
dallo [step 23](../../phases/25_taxonomySelect/plan-phase00TaxonomySelectStep23BulkCloneAndDiscardGuard.prompt.md),
K-5…K-26 dalla verifica d'archivio di K su `586a4f0ea`; i percorsi senza prefisso sono sotto `frontend/src`.

- **K-1 · Riparazione delle coppie di tipi non di coppia** — basso, solo se servisse. Il Bulk mostrava due cloni
  dello stesso tipo come una coppia, ma il payload scarta il `link_uuid` dei tipi non di coppia
  (`txPayloadHelpers.ts:256`), e la copia del DB del developer ha 0 coppie sbagliate. Un'altra installazione potrebbe
  averne, e lo Split non le ripara (`TYPE_CANNOT_SPLIT`): servirebbe una riparazione dedicata, con la query di
  rilevamento scritta nel piano.
- **K-2 · Nel percorso lento, form o wizard aperti da soli si riaprono** — basso. Se l'utente chiude il form o il
  wizard prima che il caricamento finisca, il Bulk lo riapre a caricamento finito; i test B6 aspettano la fine.
- **K-3 · Il crash di *Reset all* su una coppia con un capo inaccessibile** — basso, oggi non raggiungibile dalla UI.
  `resetAll` arriva a `txStoreGet(...)!` → `fieldsFromTx(undefined)` sul segnaposto `inaccessible`; la guardia c'è
  solo in `resetRow`.
- **K-4 · Bulk: l'`$effect` d'apertura legge `$currentLanguage` fuori da `untrack`** — basso.
  `TransactionBulkModal.svelte:513-514`: un cambio di lingua col Bulk aperto ricostruirebbe le righe.

- **K-5 · Registrazione aperta senza utenti anche se l'admin l'ha chiusa** — minimo, decisione (un endpoint, oppure va
  bene così). `backend/app/api/v1/auth.py:214`, `:217`: `is_first_user` vince su `enable_registration`, e il frontend,
  che non conosce il numero di utenti, nasconde il link. Dal prodotto non si raggiunge: l'ultimo admin attivo non si
  cancella né si declassa (piano 34, step 2). Origine: step 22, punto 7.
- **K-6 · iPhone: nessuna immagine d'avvio** — medio-basso. `app.html:8`, `:11` ha solo `apple-touch-icon` e
  `theme-color`, nessun `apple-touch-startup-image`: iOS mostra uno schermo vuoto fino al primo paint. Servono le
  immagini dal generatore per ogni formato. Origine: step 17, voce 13.
- **K-7 · Android: quadrato nero sull'icona della PWA** — basso; prima servono le prove del developer sul dispositivo.
  Icone opache e `background_color` `#f5f4ef` (`frontend/static/manifest.json:9-10`); manifest e icone escono senza
  `Cache-Control`, solo l'HTML rivalida (`backend/app/main.py:398-400`, `:505-511`). Ipotesi: icona vecchia in cache o
  nella WebAPK, splash di Android 12+ in tema scuro, splash interno. Origine: step 17, voce 12.
- **K-8 · E2E `tx-split-promote` C3: commit di uno split mai ripristinato** — medio-basso.
  `frontend/e2e/transactions/tx-split-promote.spec.ts:305`, commit a `:363-371`, nessun `afterEach`: divide la coppia
  condivisa «delete-safe», quindi in una run in cui C3 viene prima FE-SP-C1 diventa rosso. Origine: step 18 (18.4) e
  step 19, §7.
- **K-9 · E2E `multi-user`: nomi con `Date.now()` e due broker mai cancellati** — minimo.
  `frontend/e2e/brokers/multi-user.spec.ts:53`, `:70`. Origine: step 18 (18.2).
- **K-10 · `test_update_js_cache.py` esegue l'aggiornamento reale** — medio-basso.
  `backend/test_scripts/test_utilities/test_update_js_cache.py:190-195` chiama `run_from_args`, che esegue
  `update_all_libraries` (`scripts/update_js_cache.py:528`) con la rete, sulle cartelle vere di `frontend/static`; il
  fixture autouse (`:39-44`) svuota solo le failure. Origine: step 12 (12.3).
- **K-11 · `entityStore.merge` alza la versione anche a dati identici** — medio-basso. `lib/stores/core/entityStore.ts:163-177`:
  per una voce già presente imposta `changed = true` senza confrontare, quindi chi dipende dalla versione ridisegna.
  N-1 cita lo stesso file per un altro motivo. Origine: step 10.
- **K-12 · Handle di timer tenuti in `$state`** — basso. `lib/components/table/DataTable.svelte:249` (`touchTimerId`) e
  `routes/(app)/dashboard/+page.svelte:161` (`reloadTimer`): la regola dello step 14 (un teardown di Svelte 5 legge lo
  `$state` di prima dell'ultima scrittura) chiede variabili normali. Origine: step 14 (14.6).
- **K-13 · Bandiere nei grafici ECharts (D-b1)** — medio. Nessuna `fontFamily` con `'LF Flags'` nei 15 componenti con
  `echarts.init`: su Windows le bandiere delle legende dei segnali, della mappa geografica e dello storico
  dell'allocazione restano lettere. Pista: `textStyle.fontFamily` globale più `document.fonts.load` prima del disegno.
  Origine: step 12.
- **K-14 · Bandiere: pile scritte a mano e nome del file (D-b3)** — basso. `frontend/static/lf-flags.css:23` punta a
  `noto-color-emoji.0.woff2`, un nome generato; pile monospace senza `'LF Flags'` in `CompactCashCell.svelte:166`,
  `DataTable.svelte:2309`, `FilePreviewModal.svelte:1152`, `:1270`, `ImageEditModal.svelte`, `FileEditModal.svelte`.
  Origine: step 12.
- **K-15 · Formatter dei tooltip ECharts senza un `sanitizeHtml` finale né un gate** — basso, difesa in profondità. I
  sink corretti usano `escapeHtml` (per esempio `GrowthChart.svelte:2245`), ma nessuno dei 21 file con un `formatter`
  sotto `components/charts`, `charts`, `dashboard`, `risk` e `brokers/lots` chiama `sanitizeHtml`. Origine: step 13.
- **K-16 · Borsa Italiana: ETC/ETN classificati come `ETF` generico** — basso. `borsa_italiana.py:82`
  (`"etc/etn": AssetType.ETF`), benché esista `ETF_COMMODITY`; per gli ETN serve una scelta. La verifica sul server con
  l'ETC sull'oro `IE00B579F325` (17.7) non è stata fatta. Origine: step 13 e step 17.
- **K-17 · `PasswordInput`: pulsante «occhio» con `title` inglese fisso e `tabindex="-1"`** — basso.
  `lib/components/ui/input/PasswordInput.svelte:47` («Hide password», «Show password»): servono due chiavi di
  catalogo, e il pulsante è fuori dall'ordine di tabulazione. Origine: step 13.
- **K-18 · Dashboard: nei 2 s di debounce il filtro nomina già il broker** — basso. `routes/(app)/dashboard/+page.svelte:686-691`
  (`scheduleReload`): la pagina mostra ancora i totali di tutti i broker, e niente dice che un ricaricamento è in arrivo.
  Origine: step 15 (15.5).
- **K-19 · Lista degli asset: i filtri non si ritrovano al ritorno dal dettaglio (2b)** — medio-basso. Nessuno snapshot
  della lista. Decisione del developer del 06/10: «Sì, ma dopo che Risk ha integrato la sua lista: per ora va nel
  backlog». Origine: step 16.
- **K-20 · Dettaglio dell'asset: il cambio di tab rimette le date vecchie** — medio-basso.
  `routes/(app)/assets/[id]/+page.svelte:2670` ricostruisce l'URL da `$page.url`, ma il periodo è scritto con
  `history.replaceState` (`lib/utils/url/dateRangeUrl.ts:13`), che SvelteKit non vede; la stessa cura c'è già in
  `AssetBrowseNav.svelte:91` (`window.location.search`). Origine: step 16.
- **K-21 · AssetModal (wizard): il prompt di riuso può aprirsi sopra il confronto** — basso. Alla scelta di un risultato
  partono insieme il confronto dei metadati e la ricerca del riuso (`lib/components/assets/AssetModal.svelte:841`,
  `:845`); il trattenimento copre solo i prompt già aperti (`:397-403`). Preesistente. Origine: piano madre, passo 2.
- **K-22 · AssetModal: una lettura del catalogo dei provider sprecata alla riapertura** — minimo. Il corpo si ridisegna
  con lo stato vecchio e monta per un istante `ProviderAssignmentSection`; il test la chiama «wasted read»
  (`AssetModal.providerLifecycle.test.ts:1594-1599`). Origine: piano madre, passo 2.
- **K-23 · `TreeSelect`: dopo l'Esc il focus cade su `<body>`** — basso. `close()` (`lib/components/ui/select/TreeSelect.svelte:230-234`)
  non riporta il focus al trigger, e il campo di ricerca che l'aveva sparisce (`:355`); ereditato da `SignalTreeSelect`.
  Origine: piano madre, passo 4.
- **K-24 · Doc della qualità dei dati** — ✅ chiusa il 09/10 da Q (S23, treno 27). Era: basso. In `developer/frontend/data-quality-banner.md`
  mancano `TRANSACTION_IMPLIED` e `MWRR_SERIES_UNRELIABLE` (`backend/app/schemas/portfolio.py:167`, `:174`) e i test
  dicono «all 5 codes» (`:232-234`) contro 9 codici; `user/dashboard/index.en.md:93` dice «valued at purchase cost», ma
  il motore usa l'ultimo prezzo di transazione. Origine: step 13 (13.4).
- **K-25 · devWiki: quattro pagine mai scritte** — ✅ chiusa il 09/10 dal secondo giro dell'historian (treno 27):
  `problems/svelte5-teardown-reads-stale-state-timers`, `decisions/html-escape-at-the-source` (con `F-047` corretta),
  `problems/stale-price-banner-never-emitted`, `concepts/responsive-4mode-layout` riscritta. Era: minimo, knowledge base. Il teardown
  di Svelte 5 e i timer (step 14); le regole di escape con i due gate (step 13); `valuation_stale` anche per i prezzi di
  transazione; la taratura delle soglie delle barre. Origine: step 13 e 14.
- **K-26 · Intestazione superata in `catalogIcuLocale.test.ts`** — minimo. `lib/i18n/catalogIcuLocale.test.ts:26` dice
  «Red today with three keys», ma il suo gate è verde. Origine: step 21 (21.2).

## P · Costo medio e impostazioni

Origine: [30_wacUnification](../../phases/30_wacUnification/plan-phase00WacUnification.prompt.md), §9,
[SettingsBulkValidation](../../phases/30_wacUnification/plan-phase00SettingsBulkValidation.prompt.md) (P-4) e
[39_autoCostNoPosition](../../phases/39_autoCostNoPosition/plan-phase00AutoCostNoPosition.prompt.md) (P-1, P-10, P-11).

- **P-1 · Costo Auto senza posizione: costo 0 salvato senza avviso** — ✅ chiusa senza codice il 09/10, per decisione
  del developer: «no chat, non facciamolo e segnamo la decisione, se i dati mancano lo 0 come fallback per auto è
  corretto. se bisogna cambiare sarà l'utente ad andare su quella transazione e correggere.» L'analisi di P, che ne è la
  motivazione, è in [39_autoCostNoPosition](../../phases/39_autoCostNoPosition/plan-phase00AutoCostNoPosition.prompt.md).
  In Auto, senza quote nel pool d'origine (`portfolio_service.py:185-190`, `average_cost.py:155`), il costo resta 0 per
  scelta; il test P27 (`test_wac_inline.py:497`) fissa ora il comportamento voluto.
- **P-2 · Anteprima WAC: etichetta sbagliata per le righe di split e ramo `add_at_wac` morto** — basso.
  `WacPreviewSection.svelte:571-585` riconosce solo `add`, `reduce` e `add_at_wac`: una riga `split_rescale`
  (`portfolio_service.py:230-236`) mostra «Diluizione», e `add_at_wac` non esiste più dal #32.
- **P-3 · Contributo per posizione: dividendi e costi senza cambio esclusi senza segnale** — basso.
  `portfolio_service.py:1794-1805` salta il movimento senza registrare la coppia, e `PositionsContribution`
  (`schemas/portfolio.py:443-450`) non ha un canale per dirlo.
- **P-4 · Fuso orario: verificare il database IANA nell'immagine Docker** — basso. `_check_timezone`
  (`schemas/settings.py:426-432`) controlla il fuso solo se il server ha il database IANA, e `tzdata` non è nel
  `Pipfile` (`Dockerfile:72`, `:86-88`).
- **P-5 · Layer `financial_math`: migrare `roi_utils` e `valuation_utils`** — basso, refactor. È la decisione D1 del
  developer («poi in futuro fattorizziamo le altre»), scritta in `financial_math/__init__.py:8-10`.
- **P-6 · Grafo del wiki: aggiornamento rinviato dal #32** — knowledge base; **rinviata a dopo la 1.2** dal developer il
  09/10: «Rimandare a dopo la 1.2: le pagine bastano, P-6 e C-29 restano nel backlog». Le pagine devWiki nuove di P12 vanno nel grafo, e con loro le 47 scritte dall'historian il 09/10: misura del
  09/10, 289 pagine della wiki da rielaborare (714 file con i sotto-corpus). Vedi anche C-29.
- **P-7 · Chiudere la issue #32 al rilascio** — amministrativa. Il commit cita `(#32)` senza parola di chiusura, e la
  issue è aperta. Lo stesso vale per la [#35](https://github.com/Librefolio/LibreFolio/issues/35) (DEGIRO, piano 31):
  aperta, risolta nella 1.2.
- **P-8 · `tx-clone.spec.ts`: commento di testa superato** — minimo. La riga `:10` dice che sui broker in sola
  lettura il clone è nascosto; il test (`:429-448`) controlla solo edit e delete.
- **P-9 · Black: riformattare due file di test API** — minimo. `black --check` fallisce su
  `backend/test_scripts/test_api/test_portfolio_api.py` e `test_portfolio_wac.py`; le righe da riformattare non sono
  di P.
- **P-10 · `MISSING_COST_BASIS` raggiungibile dall'app riclassificando uno SPLIT** — basso, decisione (il cambio di tipo
  chiede il costo, oppure basta l'avviso). Un ADJUSTMENT +q legato a uno SPLIT, in Auto, si salva senza costo
  (`transaction_service.py:969-990`); se l'evento passa a PRICE_ADJUSTMENT la riga non è più legata allo split e diventa
  un'acquisizione di costo sconosciuto (`financial_math/average_cost.py:265`, `:290`, `:428`), e l'avviso esce sulla
  Dashboard (`portfolio_engine.py:2072-2077`, via `portfolio_service.py:561`) e nei lotti
  (`lots_analysis_service.py:855`). Lo fissa `test_portfolio_wac.py:521-588`. Origine: 39, §1.6.
- **P-11 · Tre testi promettono un lotto a costo zero col costo vuoto** — doc EN chiusa da Q (S23, treno 27); la chiave e
  il ripiego inline li ha corretti S (checkpoint 2 e 3); ✅ **chiusa nel treno 30**, con l'ingresso di S. Le versioni IT/FR/ES di `form` le ha portate il lotto 11 di M (treno 29). La chiave `transactions.costBasisOverride.warningAdjustment` («No cost basis set — lot will
  be created with zero cost…», `TransactionFormModal.svelte:1947-1950`), la doc utente `user/transactions/form.en.md:39`
  (più IT, FR, ES) e `developer/frontend/components/features/transaction-form.md:198-199`; il backend invece, in Manuale
  col campo vuoto, rifiuta la riga con `COST_BASIS_REQUIRED` (`transaction_service.py:157-165`,
  `transaction_batch_stages.py:878-946`). Origine: 39, §1.4.

## I · Grafici, eventi degli asset e traduzioni

Origine: [20_performanceCharts](../../phases/20_performanceCharts/README.md),
[19_yieldOnCost](../../phases/19_yieldOnCost/README.md) e [24_privacyGlobal](../../phases/24_privacyGlobal/README.md).

- **I-01 · DBT-A** — basso-medio. `aggregateSumSeries` propaga `missing` su un bucket che ha una somma vera
  (`timeSeriesAggregation.ts:200`).
- **I-02 · DBT-B** — basso. `aggregateEnvelope` è esportata ma non ha chiamanti (`timeSeriesAggregation.ts:268`).
- **I-03 · `%` premuto ma disabilitato** — basso-medio. Nella Crescita il pulsante `%` resta premuto e disabilitato
  su un intervallo senza dati in percentuale: `GrowthChart.svelte:772` (`hasPctData`), il ripiego a `:779-781`, il
  bottone a `:2444-2449`, il banner a `:2573`.
- **I-04 · risoluzione delle candele in `PriceChartFull`** — basso-medio. La risoluzione delle candele si decide nel
  ramo della linea (`PriceChartFull.svelte:1118-1119`, `:92-93`, `:409-423`).
- **I-05 · precisione del gate privacy su PerformanceChart** — basso. Due rami `maskable` sulla stessa riga e
  `axisTickAmount` non visto (`PerformanceChart.svelte:180`, `:183-189`). Da fondere con P4-11
  ([00_backlog_strutturale_P4.md](../09_feedbackJobs/00_backlog_strutturale_P4.md)).
- **I-06 · `npx` nel runner** — basso. `scripts/test_runner/_frontend_asset.py:14`, `:66`, contro la regola del
  progetto: mai `npx` per gli strumenti del frontend.
- **I-07 · `tsc` degli E2E, 2 errori** — basso. `tsc -p tsconfig.e2e.json` segnala `onboarding-tour.spec.ts:863` e
  `types/files.ts:9` (mancano i `paths`).
- **I-08 · debito di traduzione MkDocs** — medio, giro Aphra: «quando arriva il momento lo faremo» (developer,
  09/10). Il conto esatto lo dà `./dev.py mkdocs translate-validate`. Le pagine note il 09/10:
  - di I: `yield-on-cost.en.md` senza it/fr/es; `user/dashboard/charts`, `user/dashboard/index`,
    `user/assets/detail/chart`;
  - l'àncora `#rolling-return`, che c'è solo in inglese (D28; l'allineamento è nella 27);
  - dal treno 25: `admin/cli_tools` (N-7), `user/files/index` (anteprima PDF), `user/connection-security`, la gallery
    e il suo indice con la sezione Security (M, lotto 8); Sharpe e Sortino, la cui formula del tasso privo di rischio
    esiste solo in inglese (Q);
  - dal treno 27: `user/tools/index` e `user/tools/pac-allocator/index`, nel nav ma solo EN (D); `user/transactions/form`
    e `user/dashboard/index` (Q, S23); `developer/dev_workflow` (N);
  - dal treno 26: le otto pagine EN riscritte da K senza IT/FR/ES (`financial-theory/instruments/asset-types/{index,etfs,real-estate}`,
    `user/assets/{create-edit,index,detail/index}`, `user/dashboard/index`, `user/transactions/import/how-to`);
  - `admin/docker_advanced` in FR, IT ed ES mostra ancora `docker exec … db upgrade` e gli esempi `server --test` e
    `test db populate`, che nel container non girano;
  - la pagina `profile`, segnalata urgente da L l'08/10: l'inglese dice un'altra cosa.
- **I-09 · tipo di evento non validato → 500** — medio. `backend/app/schemas/prices.py:283`: un tipo in minuscolo o
  sconosciuto (un CSV scritto a mano) viene salvato, poi ogni lettura ORM della riga va in 500 (`LookupError`).
  Proposta: un validatore che porta in maiuscolo e rifiuta il resto con 422. Origine:
  [AssetEvents](../../phases/20_performanceCharts/plan-phase00PerformanceChartsBugfix-AssetEvents.prompt.md).
- **I-10 · robustezza dell'editor degli eventi (S3/S4)** — basso-medio. S3: `handleBulkDelete` non salta gli eventi
  automatici in sola lettura. S4: la mini-modale ritrova l'evento appena creato per (tipo, data) e può prendere quello
  automatico (`EventCreateMiniModal.svelte:150`). Poi: una riga nuova senza id si fonde in silenzio con un evento
  salvato (`DataEditor.svelte:521-530`); le modifiche partono prima delle cancellazioni, quindi spostare un evento
  sulla chiave di uno appena eliminato dà `EVENT_KEY_CONFLICT` (`price_store.py:277`); il toast d'errore mostra il
  messaggio generico di axios (`AssetDataEditorSection.svelte:463-467`). Origine: AssetEvents.
- **I-11 · limiti del round-trip CSV degli eventi** — basso. `CsvEditor.svelte:416-436` scarta le righe con una data
  ripetuta; l'import ignora `source` (le righe dei provider tornano manuali e poi raddoppiano) e `currency` (un
  backup preso prima di un cambio di valuta torna rietichettato); il selettore della data disabilita le date già
  usate (`DataEditor.svelte:151-161`). Origine: AssetEvents.
- **I-12 · guardie server degli eventi** — basso-medio. `DELETE /assets/events?ids=…` non è limitato all'asset
  (`backend/app/api/v1/assets.py:1070-1072`, `price_store.py:954`); `bulk_upsert_events` salva un elemento alla volta
  (`price_store.py:629`). Origine: AssetEvents.

## C · Backlog del coordinatore

Raccolto dal 06/10 nei controlli dei treni e nei messaggi dei figli; riverificato il 09/10 sull'albero del treno 25.

- **C-1 · Spec E2E a contratto di rete chiuso e chiamate globali nuove** — basso, strumento. Le spec che chiudono la
  rete (`route('**/*')` più il rifiuto delle API non dichiarate) vanno ricontrollate ogni volta che il frontend
  aggiunge una chiamata globale. Il caso del 09/10: `GET /api/v1/system/connection` ha rotto `files-uploader` e
  `layout/header-scroll`, curate da L nel treno 25. Proposta: un test del runner che elenchi le chiamate globali
  dell'app (Sidebar, Header, layout) e verifichi che ogni spec a contratto chiuso le dichiari.
- **C-2 · Licenza del campione DEGIRO** — basso, legale. `backend/app/services/brim_providers/sample_reports/degiro-export.csv`
  coincide col campione pubblico misto del progetto `dickwolff/Export-To-Ghostfolio` (L, 07/10). Lo usano
  `test_brim_degiro.py:76` e `populate_mock_data.py:3534`, e `sample_reports/README.md` non ne dice la provenienza.
  Verificarne la licenza o sostituirlo con un campione sintetico.
- **C-3 · Cartelle `broker_<id>` vuote dopo la cancellazione di un broker** — minimo. `delete_files_for_brokers`
  (`brim_provider.py:1203-1222`) cancella i file ma lascia le cartelle in uploaded, parsed e failed; con
  `AUTOINCREMENT` gli id non tornano, quindi le cartelle vuote si accumulano, innocue (I, 08/10).
- **C-4 · Stato dei plugin BRIM (Stable/Beta/Alpha) solo nella doc** — basso. Sta in `providers_list.md` (per esempio
  `:9`, `:29`), nelle card dell'indice e nell'avviso della pagina utente; nessun attributo nel codice lo tiene
  allineato (Q, 08/10).
- **C-5 · Crédit Agricole: `TITOLI SCADUTI` senza posizione né prezzo** — basso, da provare con un export reale. Con
  nominale 0 o senza controvalore la riga diventa un SELL con quantità 0 (`broker_credit_agricole.py:1039-1062`;
  Q, 08/10).
- **C-6 · eToro: dividendi `KER/EUR` etichettati EUR** — basso, serve un export reale. L'importo è nella valuta del
  conto, mentre la valuta viene dal ticker `SYMBOL/CURRENCY` (`broker_etoro.py:143`; Q, 08/10). La voce eToro di
  [04_brim_import.md](../09_feedbackJobs/04_brim_import.md) chiede lo stesso export.
- **C-7 · Doc BRIM da allineare** — fatta da S il 09/10 (checkpoint 2, `94271713b`); ✅ **chiusa nel treno 30**, con l'ingresso di
  S in `dev_release2`. Era: basso. `brim_plugin_guide.md:435-436` dice «Fineco (Italian)», ma gli avvisi di
  Fineco sono in inglese (`broker_fineco.py:279-297`), e sbaglia anche la docstring del modulo (`:7-8`); la riga eToro
  di `providers_list.md:9` è da precisare (Q, 08/10).
- **C-8 · Docstring e commenti superati** — basso.
  - `broker_coinbase.py:16-19`: staking come INTEREST, send e receive come WITHDRAWAL e DEPOSIT; il codice fa
    ADJUSTMENT (`:68-70`) e salta send e receive (`:76-77`).
  - `backend/app/schemas/assets.py:341`, `:359`, `:541-542`: tolleranza ±1e-6; il codice usa `Decimal("0.01")`
    (`:399`).
  - `backend/app/api/v1/brokers.py:414-416` («Any user with access to the broker can view the access list») e
    `broker_service.py:281`, `:340`, `:370` (`as_user_id="all"` «For superuser»): per decisione del developer ogni
    utente autenticato vede l'elenco degli accessi di qualsiasi broker, e-mail comprese, e `brokers.py:422` usa
    `"all"` per tutti.
  - `.github/instructions/frontend-ai-export.instructions.md:65-72` descrive `ClipboardItem`; il codice usa
    `writeText` (`aiExportClipboard.ts:156-158`).
  - Non riverificati il 09/10 (Q, 08/10): la docstring di Intesa, l'intestazione di `PositionsPanel` (clic e doppio
    clic), lo zoom di `ImageCropper`, la gomma degli eventi (`ErasableNumberCell`), `AssetSetRiskReturnSection.svelte`
    («there is no picker here», ma il picker del benchmark c'è), la coda delle immagini in `files/+page.svelte:355`.
- **C-9 · Doc admin di Docker** — ✅ chiusa il 09/10 (treno 27): `docker_advanced.en.md` e `.env.example` da Q (S23),
  il commento di `docker-compose.yml` e gli esempi di `dev.py` da N. Era: basso. `.env.example:77-81` dice che UID e GID valgono anche a runtime, ma
  l'entrypoint legge `LIBREFOLIO_UID` e `LIBREFOLIO_GID` (`entrypoint.sh:21`) e compose passa `UID` solo come
  argomento di build (`docker-compose.yml:32`). `docker_advanced.en.md` non dice che `server --test` e
  `test db populate` non girano nel container (niente Node né `test_scripts`): lo dice solo il manuale dev (Q, 08/10).
- **C-10 · Date nella lingua del browser invece che in quella dell'app** — medio-basso (K, 09/10).
  `dataTableLogic.ts:326-344` (cella data e ora della DataTable), `importReportSets.ts:287`,
  `ImportWizardModal.svelte:3604`, `TransactionBulkModal.svelte:1873-1874`, `GlobalSettingsTab.svelte:726` (con
  «Last updated:» scritto fisso) e `:755`, `SchedulerLogModal.svelte:222`, `FileGrid.svelte:73`,
  `brokers/[id]/+page.svelte:442`, `assets/[id]/+page.svelte:3515`. Gli eventi degli asset non sono riverificati.
- **C-11 · `formatBytes` senza la lingua dell'app** — basso (K, 09/10). `FileUploader.svelte:241`,
  `FileEditModal.svelte:165`, `ImportWizardModal.svelte:3301`, `DataTable.svelte:1265`,
  `DataTableColumnFilter.svelte:913-917`, `FilePreviewModal.svelte:123`; la vista a lista dei file segue già la lingua.
- **C-12 · AiExportMenu: un Esc dentro il pannello lo chiude** — basso (K, 07/10), dopo la 1.2 per decisione del
  developer. `AiExportMenu.svelte:255-259` ascolta `keydown` su `document` in cattura, senza `stopPropagation`: un Esc
  che chiude una SimpleSelect aperta dentro il pannello chiude anche il pannello.
- **C-13 · Timer che sopravvivono allo smontaggio** — basso (K, 06/10). `SearchSelect.svelte:306-318` (un
  `setTimeout` che legge il `document` globale; altri a `:238`, `:345`, `:400`) e `ProfileTab.svelte:138`, `:190`,
  `:256` (timer di 5 s); gli helper della clipboard non sono riverificati. Proposta: un controllo dei timer vivi su
  tutta la suite di unità.
- **C-14 · Anteprima PDF: residui** — basso (M, 09/10).
  - `frontend/package.json:61` dichiara solo `@embedpdf/snippet`, ma `pdfViewerAssets.ts:22-25` importa direttamente
    `@embedpdf/models` e i `fonts-*`: manutenzione, per il developer.
  - Da riverificare a runtime: Ctrl/⌘+C su un testo fuori dal PDF inghiottito dal visore; il riquadro della password
    del proprietario, che rimanda a Security (ora spento) e dopo lo sblocco dice «full access» coprendo la pagina; lo
    stato `error` mentre si chiede la password, che per distinguersi vuole un quarto stato (decisione d'interfaccia).
- **C-15 · Gate dell'interpolazione HTML: residui della decisione (c)** — basso (I, 09/10). Restano i due
  `title="${$t(…)}"` (`ImportWizardModal.svelte:2310`, `TransactionBulkModal.svelte:1786`), che contano solo se una
  traduzione contenesse `"`; il ripiego di `translateOr` (`translateOr.ts:25`); `LABEL_BUNDLE` riconosciuto per nome
  (`htmlInterpolation.gate.test.ts:204`). Non riverificata (K, 08/10): la guardia ICU non leggerebbe le chiamate
  `get(t)(…)` né i moduli `.ts`.
- **C-16 · E2E della Dashboard sui provider veri** — basso-medio. `frontend/e2e/portfolio/dashboard.spec.ts` non
  instrada prezzi e provider (c'è solo `fx/providers/routes`, `:2108`): partono i feed live di JustETF e la cache di
  `scheduled_investment`, e il polling dei prezzi non è trattenuto. `asset-list.spec.ts:58-75` invece instrada le sue
  chiamate.
- **C-17 · E2E che intercettano `/portfolio/report` prima che la Dashboard d'atterraggio sia ferma** — basso, da
  verificare (N, 07/10). `dashboard.spec.ts:282`, `:416`, `data-quality-banners.spec.ts:107` e `risk-lab.spec.ts`
  registrano la route senza attendere: è la corsa curata in `brokers-detail.spec.ts`.
- **C-18 · Test di unità che leggono i sorgenti di altri rami** — basso, processo. `optionFilter.test.ts:120`, `:219`
  legge i plugin BRIM con `readFileSync`, quindi un plugin nuovo può romperlo solo dopo l'integrazione (DEGIRO,
  07/10). Regola dei treni: `core-unit` gira sulla simulazione, non solo dopo.
- **C-19 · Prezzi seed per gli asset senza prezzo** — basso (M, 08/10). `populate_mock_data.py:2345-2362`
  (`price_configs`) valorizza solo azioni, crypto e prestiti crowdfunding: ETF, BTP e oro restano senza prezzo
  finché non gira il polling live, e la gallery risponde con prezzi fissi (G5). Da fare dopo un'analisi dell'impatto
  su E2E e laboratorio di rischio.
- **C-20 · Diagnostica dei plugin senza i plugin di rischio** — basso (Q, 07/10). `backend/app/api/v1/system.py:201-207`
  copre i registri di asset, FX, BRIM e segnali; mancano `RiskAnalyticRegistry` e i Tool.
- **C-21 · Simulazione: numero di percorsi fisso** — decisione di prodotto, dopo la 1.2 (developer, 07/10); dominio
  della 02. `path_count` è un parametro fisso (`risk_plugins/simulation.py:108`): non si adatta alla dimensione del
  portafoglio e il risultato non lo dice. Oggi uno scope troppo grande è rifiutato con `RESOURCE_LIMIT` e un rimedio
  (`:53-89`).
- **C-22 · Istogramma: Freedman–Diaconis con un IQR appena sopra zero** — basso, decisione; dominio della 02.
  `backend/app/services/risk/metrics.py:22`, `:832-846`: tetto di 200 barre e Sturges solo con IQR = 0 (D380); con un
  IQR minimo si arriva a 198 barre (campione di stress dell'oracolo). Il pavimento `max(fd, sqrt/2)` di NumPy 2 è da
  decidere.
- **C-23 · Laboratorio di rischio** — basso; dominio della 02 (F).
  - Il ricarico usa `invalidateRisk()` (`AssetSetRiskPanel.svelte:205`, `:225`): passare a `markRiskStale()`, nello
    stile di E4, è una scelta da fare.
  - Da verificare a runtime: la doppia richiesta all'apertura; in italiano, l'ultima colonna della tabella delle
    perdite, «Risalita al massimo», tagliata a destra (M, 08/10).
  - Ipotesi da provare: il backend che ignora SIGTERM dopo i feed live di JustETF (`justetf.py:123-130`,
    `shutdown_live_feeds` con 3 s di timeout).
- **C-24 · `BenchmarkSelect` e gli id spariti** — basso (L, 08/10). Da quando gli id non si riusano (piano 34),
  `BenchmarkSelect` può tornare a togliere dalla selezione gli id spariti: non rischia più di colpire un asset nuovo
  con lo stesso id. Oggi filtra solo le opzioni (`BenchmarkSelect.svelte:8`, `:96`).
- **C-25 · `/welcome`: possibile ciclo se si alza la versione del Welcome** — basso, da verificare a runtime (Q,
  07/10); dominio della 21. Il gate passa da `appBootstrap.svelte.ts:43`, `:97` (`hasReplay('welcome', version)`).
- **C-26 · Registry: un tag `test` rimasto** — minimo, amministrativa (Q, 08/10): da cancellare dal registry delle
  immagini.
- **C-27 · `populate_mock_data` imposta `brim_plugin_key`, che il modello del broker non ha** — basso (S, 09/10). Il
  valore non arriva mai al broker; correggerlo farebbe aprire la modale del broker sbagliato nella gallery (l'upload
  Crédit Agricole sul broker Interactive Brokers del seed), quindi va fatto insieme agli scatti di M.
- **C-28 · Registro degli ingest della devWiki: hash che non esistono più** — basso, knowledge base (historian, 09/10).
  158 delle 181 righe vecchie di `LibreFolio_devWiki/raw/ingest-registry.md` citano commit fuori dalla storia del repo,
  quindi il controllo di deriva non funziona; 64 righe puntano a percorsi spostati. È annotato in testa al registro; va
  ri-baselinato solo con una rilettura vera delle fonti.
- **C-29 · Il controllo «il grafo è aggiornato?» di `SCHEMA.md` non vede nulla** — basso (historian, 09/10).
  `detect_incremental(Path('corpus/'))`, con il graphify installato, scansiona 0 file, perché i symlink del corpus si
  risolvono fuori dalla radice: risponde sempre «aggiornato». Collegata a P-6.
- **C-30 · Docstring di `patch_assets_bulk`: `exclude_none` invece di `exclude_unset`** — minimo (historian, 09/10).
  `backend/app/services/asset_sources/crud.py:489-490`.
- **C-31 · Il formato black non ha un gate** — basso, processo (D, 09/10). `dev.py lint` lancia solo `ruff check backend/`
  (`dev.py:1811-1823`), così il debito di black entra senza rossi (vedi P-9). Proposta di D: `black --check` sui file
  toccati nella checklist dei checkpoint.
- **C-32 · Commenti e docstring superati** — minimo (Q, S23). `portfolio_engine.py:1990`, `:2034`;
  `portfolio_service.py:1139-1146`, `:1184-1191`; `schemas/portfolio.py:165`; `test_data_quality_report.py:3`; nel runner
  `_archive.py:7`, `_run_cache.py:7-10`, `_cli.py:470`, `:568-572`, `__init__.py:15-31`, `_consolidate.py:69-71`,
  `_frontend_ai_export.py:69-71`; `EditBuffer.ts:10`.
- **C-33 · Costo medio dei trasferimenti e del promote: tre possibili difetti** — **confermati da P il 09/10** con test
  rossi, tutti già nella v1.1.0; ✅ **corretti il 09/10 (treno 28)** per decisione del developer («Correggere 1 e 2 nel
  backend con una sola cura, e 3 facendo chiedere il costo anche col promote»; data d'uscita: «Alla data in cui le quote
  escono dal broker d'origine»), piano `phases/40_transferCostBasis/`. Erano, letti da Q: (1) un transfer in Auto di un'intera posizione riceverebbe costo 0, perché la gamba in uscita
  svuota il pool prima della media (`transaction_service.py:976`, `average_cost.py:407-423`); (2) un transfer esistente
  modificato in Auto farebbe la media sul broker che riceve (gli update non hanno `link_uuid`,
  `schemas/transactions.py:533-585`); (3) il promote salta il controllo del costo (`transaction_batch_stages.py:845-866`,
  `:701-729`), contro `developer/backend/transactions/wac.md:423-424`.
- **C-34 · `escapeHtml` definita tre volte, una copia più debole** — basso, difesa in profondità (historian, 09/10). La
  copia locale di `CorrelationHeatmap.svelte` sfugge solo `& < >`, e il gate XSS accetta qualunque funzione con quel nome;
  oggi è sicuro perché ogni uso è testo. Vedi K-15.
- **C-35 · `test_settings_api.py` salta cinque controlli se l'endpoint risponde 404** — minimo (historian, 09/10). Gli
  endpoint esistono, quindi i controlli girano; ma una rotta rinominata li farebbe saltare invece di fallire.
- **C-36 · Docstring di `AssetType`: i sottotipi «confluiscono» nel tipo base** — minimo (historian, 09/10).
  `backend/app/db/models.py` (~`:178`); `allocation_by_type` del backend usa i valori grezzi, e i grafici raggruppano per
  famiglia.
- **C-37 · `docker-compose.yml` pubblica la 6041 su cui nel container non ascolta niente** — basso, configurazione,
  decisione del developer (N, 09/10, letto nel codice). `docker-compose.yml:47` mappa `${TEST_PORT:-6041}:6041`, ma
  l'immagine non sa fare il test mode; con lo stack attivo, `./dev.py server --test` sul host rifiuta la porta occupata
  (`dev.py:238`, `:256-260`), e l'aiuto suggerisce `kill -9` o `--force`, che ucciderebbero l'inoltro di Docker. Proposta:
  togliere la mappatura. La pagina `developer/dev_workflow` lo dice dal treno 27.
- **C-38 · `DataTable` su mobile: l'intestazione «Actions» resta fissa, il ⋮ scorre via** — medio-basso, letto nel
  codice (D, 09/10, dagli scatti PAC del lotto 9 di M). Sotto i 768 px la media query rende statiche le celle delle
  azioni, ma `thead.sticky-header th` è più specifica di `.th-actions`, quindi l'intestazione resta sticky a `right: 0`
  mentre il ⋮ delle righe esce dallo schermo. Riguarda ogni tabella con azioni; nel PAC spiega F e la tabella Targets
  (backlog della 13). Componente condiviso: la cura va concordata con chi lo possiede.
- **C-39 · Cataloghi i18n divisi per namespace** — dopo la 1.2, per decisione del developer (09/10, su proposta di
  S): «Chiavi brimPlugins ora per tutti i 33 plugin, divisione dopo la 1.2.0 (Consigliato)». I quattro cataloghi
  `frontend/src/lib/i18n/{en,it,fr,es}.json` hanno oltre 4.200 chiavi ciascuno, testi dei plugin (`brimPlugins.*`)
  compresi: dividerli per namespace, cominciando da `brimPlugins`, riduce i conflitti fra flussi paralleli e ciò che
  ogni pagina carica.
- **C-40 · Un parametro per scegliere l'icona del broker** — dopo la 1.2, idea del developer (10/10): «in futuro
  potremmo pensare di aggiungere un parametro selettore». Per la 1.2 l'ordine è personalizzata → plugin dedicato →
  favicon del portale → plugin di ripiego → valigetta; i plugin di ripiego sono quelli con `detection_priority` sotto
  `FALLBACK_PLUGIN_PRIORITY_LIMIT` (50, `frontend/src/lib/utils/brim/pluginKind.ts`, workstream S). Un selettore,
  sul plugin o sul broker, sostituirebbe la soglia.
- **C-41 · Gli scatti dell'AI Export** — dopo la 1.2, per decisione del developer (10/10): «sull'ai export mettiamolo
  nel backlog i suoi scatti, ora non è una priorità». Le 5 pagine `user/ai-export/*` non hanno scatti, e
  `frontend/e2e/gallery.spec.ts` non ne prevede: servono la spec (desktop e mobile), le immagini nelle pagine utente e
  le voci delle due gallery, con le traduzioni.
- **C-42 · I vincoli delle coppie anche per contante e cambio** — dopo la 1.2 (decisione D1 del coordinatore sul lotto 42 di
  P, 10/10). Il lotto 42 fa controllare a `_validate_linked_pair` asset e quantità delle coppie TRANSFER; gli altri
  `pair_field_constraints` dei metadati (importo e valuta del CASH_TRANSFER, valute e broker dell'FX_CONVERSION,
  `backend/app/schemas/transactions.py:1217-1221`) li rispettano il modulo e l'import, ma un client dell'API può ancora
  salvare una coppia sbilanciata.

## Tracciate altrove

Voci del backlog del coordinatore che una cartella attiva tiene già: non sono duplicate qui.

- Le immagini solo amd64: [ReleaseGallery](../27_releaseImages/plan-phase00ReleaseGallery.prompt.md), riga 209.
- La doc developer precedente alla 1.1 (l'esempio JSON di `api/overview`, `-v` in `external.md`, «11 categories»,
  le opzioni del runner e i moduli mancanti): [DocsEnglish12](../32_docsEnglish12/plan-phase00DocsEnglish12.prompt.md),
  S9. Alcune voci di quell'elenco sono chiuse: vedi sotto.
- La fase 3 di Risk, i buchi B1–B6 e le questioni aperte: [README della 02](../02_riskfolioIntegration/README.md).

## Chiuse alla verifica del 09/10

Voci del backlog del coordinatore che il codice del treno 25 ha già chiuso.

| Voce | Chiusa da |
|---|---|
| Id dei broker riusati e file BRIM ereditati da un broker nuovo (⚠️ del 07/10) | `AUTOINCREMENT` (`db/models.py:535`) e `delete_files_for_brokers` (`brim_provider.py:1203-1222`), piano 34 |
| `portfolio_optimization` oltre 100 titoli risponde `invalid_parameters` | `RESOURCE_LIMIT` (`portfolio_optimization.py:189-196`) |
| Docstring di `AssetType` e del budget in `pac_allocator` | `db/models.py:147-184`; `planner.py:145-160` e `solver.py:99-111` coerenti |
| `mkdocs gallery --no-populate` che ripopola a ogni giro | `dev.py:1074`, `global-setup.ts:34` |
| `ai_export_snapshot.md` senza il 422 `selection_not_applicable` | `ai_export_snapshot.md:121` |
| `CashBalanceCard`, `CashTransactionModal` e «Live Ticker» nella doc | nessuna occorrenza in `mkdocs_src/docs` |
| `registry_pattern.md` (`get_provider()`, la base, i registri mancanti) | `get_provider_instance`, `AbstractPluginRegistry`, `RiskAnalyticRegistry` e `ToolPluginRegistry` |
| `release-pipeline.md` vecchia | riscritta da M |
| Passo 2 di `brim/architecture.md`: il Generic CSV come ripiego | `brim/architecture.md:46`; il ripiego `auto` resta in L8 |
| La traduzione rompe la prosa con liste annidate | `translate_docs.py:360` e il test `nested-list-items` |
| Plurale con `Number(…)` in `modeText.ts` | ICU con `plannerPlainDecimalCount` |
| `desc` di `risk-asset-detail` nel runner | `_frontend_portfolio.py:371` |
| Sezione «Adding and Removing Assets» della guida | non esiste più |
| Marquee della gallery e `freezeAnimations()` | `reducedMotion: 'reduce'` (`gallery.spec.ts:326-332`) |
| `settings.spec.ts:540`, attesa di 3 s | `timeout: 5_000` |
| Timer di `currencyStore` e di `ImageCropper` | nessun intervallo; `onDestroy` con `clearTimeout` |
| Avvisi dei set «Continue is disabled» | treno 19 |
| `fx-add-pair.spec.ts`, attese di 3 s | piano `FxAddPairNavigationWait` della 28 |
| Riga Total Value della tab Info degli asset | la riga non esiste più; il campo è solo dei broker |
| 34 `assert` nelle richieste dell'AI Export | nessuno nei 7 file (09, nota S6 6.11) |
| `docker_advanced.en.md`: `docker exec … db upgrade` | `:207` lo sconsiglia; le traduzioni restano in I-08 |
| Immagini 1.1.0 full e light identiche | la full contiene gli screenshot (M, CHANGELOG 1.2.0) |
| Coverage: combine fallito su due passate parallele | piano CoverageCombineRace della 28; residui N-2…N-4 |
| Issue #32 (costo 0 in valuta del report), #35 e #33 (DEGIRO) | piani 30 e 31; restano da chiudere #32 e #35 (P-7) |
