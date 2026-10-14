# Piano — fase 01, 04: Import e transazioni (W)

> **Sessione**: «W - Import e transazioni», ramo `e-alfy-w-import-e-transazioni` (rinominato dall'app all'avvio, prima
> `e-alfy-fluffy-meme`). Coordinatore: «Release 1.3 planning» (`928ffa97-f0c3-4975-a442-3de0c2c20fc7`).
> **Corsia**: porta 6184, data-dir `/tmp/librefolio-r13-w`; preambolo
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6184 --data-dir /tmp/librefolio-r13-w …`.
> **Piano generale**: [`plan-phase01Release13.prompt.md`](../plan-phase01Release13.prompt.md) (§4 «W», §6 regole e forma
> comune C1–C7, §7 colori); decisioni: [`decisioni-analisi-20261014.md`](../decisioni-analisi-20261014.md) (punti 20–25).
> **Backlog**: sezione «W · Import e transazioni (fase 01)» di
> [`BACKLOG_POST_1.2.md`](../../Phase_0/BACKLOG_POST_1.2.md), scritta solo da questa sessione, ai checkpoint.

## 0. Mandato

### 0.1 Richiesta del developer (dal kickoff, testuale, parti rilevanti)

- «è imperativo nella prossima release rilasciare le feature che ci permettono di rilasciare librefolio cloud, è
  importante lavorare, con spirito critico, alle attività in backlog che ci siamo lasciati post 1.2 e se nel farlo
  riusciamo a tirarci dentro dei todo_futuri che vengono facili, non dispiace.»
- «proprio perchè dobbiamo avviare molti lavori in parallelo, prenderci del tempo iniziare per riodinare e fattorizzare
  credo sia prioritario» → scelta: «Tutto il riordino del piano 43, backend e frontend, compresi i file più grandi».
- Perimetro del backlog: errori che toccano numeri, sicurezza o dati, e chiarezza per utenti non esperti.

### 0.2 Via libera parziale al codice (coordinatore, 14/10 ~22:55, inoltrato alla lettera)

> Parole del developer, alla lettera (mentre legge il documento delle decisioni): «chat, sto leggendo
> LibreFolio_developer_journal/Release_2/Phase_1/decisioni-analisi-20261014.md — ho appena finito le prime 11 domande e
> sto iniziando piattaforma, ma ho già messo varie note dev, leggi intanto quelle, vedi se con quelle risposte devi
> aggiornare quello che viene dopo e poi vedi tu se aspettare che leggo tutto, o intanto grazie a queste riesci ad avviare
> qualche lavoro»
>
> Decisione del coordinatore su questa delega: parte SOLO il primo checkpoint, che è riordino puro e non dipende da
> decisioni di prodotto ancora aperte. W2, I1, K1 e il resto aspettano che il developer finisca di leggere.

- **Perimetro autorizzato adesso**: W0 (base e piano, nessun codice) e W1 = CP1 (rinomina di transazioni e broker,
  nessun cambio di comportamento).
- **Nomi** (C1, confermata dal coordinatore il 14/10 sera): un file che entra in un pacchetto di dominio tiene il suo
  nome → `services/transactions/{transaction_service,transaction_batch_stages,transaction_batch_context}.py`,
  `services/brokers/broker_service.py`. Nel taglio (W2, C4) la classe composta resta nel suo file, col suo nome
  (testo di C4 corretto dal coordinatore in `793395913`, che arriva col prossimo aggiornamento di base).
- **Base**: `c9bb8f257643c0b770788033789425b41ba16715` (fast-forward del coordinatore da `459131eb8`; solo journal,
  `scripts/visual_review/gallery_snapshot.sh`, `TODO_FUTURI.md`).

## 1. Stato reale (verificato sul codice, base `459131eb8`, invariato in `c9bb8f257`)

### 1.1 Backend

| Area | Fatti |
|---|---|
| `services/brim_provider.py` | 2 248 righe: contratto `BRIMProvider` 118–630; file e lock 632–1305; file combinati dei set 1306–1502; spostamenti e risultati 1503–1693; `parse_file` 1694–1773; candidati 1774–2058; duplicati 2059–2248. 41 importatori nell'app (33 plugin), 15 file di test, 2 script. Stato di modulo `_BROKER_LOCKS`, `_BROKER_LOCKS_GUARD`, `_BROKER_LOCK_STATE` (`:658-660`) + alias `broker_metadata_lock` usato dai report set. Importa lo shim `asset_source` (`:78`, PL6 di X) e `BRIMProviderRegistry` (`:79`, PL2 di X) |
| Patch dei test su `brim_provider` | 6 file patchano globali del modulo (`get_broker_reports_dir` ×5, `detection_signature`, `BRIMProviderRegistry.*`): nel taglio di PL5 i sotto-moduli le leggono per attributo del modulo, con una guardia (C4) |
| Satelliti BRIM | `brim_report_sets.py` 459, `brim_parse_pool.py` 144 (pool di processi: pickling per nome qualificato), `brim_gap_fix.py` 236 (importa `transaction_service`) |
| Transazioni | `transaction_service.py` 1 088, `transaction_batch_stages.py` 1 108, `transaction_batch_context.py` 94; `transaction_service` importa `portfolio_service.compute_wac_iterative` (J) |
| Broker | `broker_service.py` 1 000 (CRUD 81–362 e 568–794, summary 363–567, accessi 795–1000); importatori: `api/v1/brokers.py`, `services/user_service.py` (A), `services/__init__.py`. Copie di matematica già censite dal piano 43: V3 (`:549-562`, U5) e C2 (`:448-453`, U4), di J |
| `services/__init__.py` | hub pigro solo del dominio W (`BrokerService`, `TransactionService`, …), senza utilizzatori |
| Router | `api/v1/brokers.py` 1 193, due router (`/brokers`, `/brokers/import`); `operationId` FastAPI = nome funzione + percorso + metodo; l'ordine di registrazione delle rotte va tenuto (C2) |
| Schemi | `schemas/transactions.py` 1 370 (pacchetto di schemi, C3), `brokers.py` 407, `brim.py` 895 |
| Eventi | `api/v1/assets.py:1025-1130`, `asset_sources/price_store.py:629-1020`, `schemas/prices.py:284`: di X fino alla sua divisione in moduli propri, poi di W |
| Icone e campioni | `brim_providers/static/` solo `scalable/{broker,deposit}.png`; rotta `uploads.py:146-150` e `:495-553` (di H; anti-traversal con `startswith`); `sample_reports/` 62 voci + `malformed/` + README, citati da 15 file E2E/fixture, 10 test, `populate_mock_data.py`, 9 pagine doc |

### 1.2 Frontend

- `ImportWizardModal.svelte` 5 984, `TransactionBulkModal.svelte` 3 758, `TransactionFormModal.svelte` 2 270,
  `TransactionsTable.svelte` 1 213; barili `components/transactions/index.ts` e `shared/index.ts`.
- FE8b tocca righe d'import di file altrui (`FileSetBadges`, `FilesTable`, `CompactCashCell`, `ImportBrokerMismatchModal`,
  `AboutTab`, `ImportPluginSelect`, `brokerHelpers.ts`, rotte `dashboard` e `brokers/[id]`, `AssetDataEditorSection`);
  5 `vi.mock` su moduli che si spostano; il runner `_frontend_transaction.py` elenca 22 file Vitest.
- Chiavi i18n: `dataEditor.*`, `csvImport.*` in `base/`; `events.*` in `assets/` (X); di W `transactions/`,
  `importWizard/` e i frammenti dei plugin BRIM.

## 2. Voci assegnate: esito della verifica

| Voce | Esito |
|---|---|
| T-PL5 | confermata (§1.1); ordine PL2 → PL6 (X) → PL5 (W); registro BRIM in `services/brim/registry.py`, di X |
| U-B3 | confermata; rotta generica sulla `static/` del plugin, solo `serve_plugin_static` d'accordo con H; nessun alias dei vecchi URL (calcolati a runtime, `brokerHelpers.ts:61`) |
| U-B4 | confermata; `broker_<x>/sample_reports/`, `malformed/` e README alla radice della famiglia |
| U-B8 | entra nell'aggiornamento della guida in PL5 |
| U-B9 | a W, priorità bassa |
| C-79 + C-3 | stessa causa: `delete_files_for_brokers` (`:1258-1278`) lascia `<stato>/broker_<id>/`, `.locks/broker_<id>.lock` e la voce in `_BROKER_LOCKS` |
| C-65 | mancano la ricerca inversa `GET /transactions?asset_event_id=` e la modale; `provider_management.py:186-195` (X) scollega in silenzio le transazioni al cambio di provider |
| C-70 | (a) codici solo nei 2 plugin Scalable: DEGIRO (4 motivi) e Generic CSV (5) danno frasi inglesi; (b) 400 del parse inglese col codice del plugin e il nome salvato (chiude L6), `extractErrorMessage` legge già `detail.message`; (c) «L108» = anteprima di un Excel danneggiato (`file_preview.py:75`): W unico scrittore (D-W17 approvata), dopo il CP1 di H |
| C-89 | confermata (`TransactionFormModal.svelte:1649`, `:1697`) |
| P-13 | a Y |
| P-14 | a W, in una finestra concordata verso la fine (tutti gli `es.json`) |
| P-15 | parte W: `DataEditor.svelte:652`, `:661-668`, `DataImportModal.svelte:211`, `:220`; «Reset layout» e «max» a Y |
| V-22 | contratto oggi fissato da 2 test (`test_assets_events.py:932`, `:964`); decisione 20 in lettura |
| V-23 | confermata (`transaction_batch_stages.py:157-179`; `TransactionBulkModal.svelte:1611`) |
| V-37 | minimo e 1b chiusi nella 1.2; aperta V-37b |
| V-38 | confermata nel codice (`TransactionFormModal.svelte:971-972`); da vedere a schermo |
| I-09 | confermata (`schemas/prices.py:284`); decisione 23 in lettura |
| I-10 | S3 (`DataEditor.svelte:525-534`) e S4 (`EventCreateMiniModal.svelte:150-152`) confermati |
| I-11 | confermata (`CsvEditor.svelte:416-436`) |
| I-12 | confermata (`assets.py:1070-1092`, `price_store.py:954`); decisioni 21–22 |
| L5 | confermata (`brokers.py:695`, `:767`) |
| O-12 | basta l'ICU nei 4 `importWizard/*.json` |
| K-1 | chiusa senza codice (decisione 24, in lettura) |
| K-2, C-45, C-61, V-24, P-12 | da verificare con un rosso |
| K-3, K-4, P-2 | confermate |
| 🔗 eventi collegabili (`TODO_FUTURI`) | backend pronto: `POST /transactions/events/suggest`, 10 test; nessun chiamante frontend |

## 3. Superfici

- **Di W**: `services/{transactions,brokers,brim}/**` (dopo gli spostamenti), `brim_providers/**`, `api/v1/brokers/**`
  (dopo C2), `api/v1/transactions.py`, schemi delle transazioni, dei broker e di BRIM, `features/transactions/**`,
  `components/transactions/**`, `components/ui/data-editor/**` (classi convertite da T dei colori: righe funzionali W,
  classi T), eventi dopo la divisione di X, `services/__init__.py` (hub del dominio W).
- **Condivise, voci di W in aggiunta**: runner dei test (voci del dominio), cataloghi i18n (sorgenti dei sottosistemi
  di W e frammenti dei plugin), `.github/instructions/backend-providers-brim.instructions.md` e skill `brim-plugin`,
  doc per sviluppatori, tabelle «Source files» della devWiki (C6), `scripts/coverage_analysis.py` (voci di W).
- **Altrui, solo righe d'import nei lotti di rinomina**: `services/user_service.py` e `api/v1/auth.py` (A).

## 4. Dipendenze

1. X: PL2 (registri) prima di W3 e W4; PL6 (via lo shim) prima di W4; eventi in moduli propri prima di E1.
2. Coordinatore: un commit su `api/v1/brokers.py` prima di W3; uno su `api/v1/uploads.py` prima di W5.
3. H: CP1 prima della parte d'anteprima di C-70 (D-W17).
4. Colori: lo spostamento della cartella delle transazioni dopo il lotto A; FE8b dopo il lotto D; i tagli delle tre
   modali possono partire prima, con annuncio (§7 del piano generale) e senza toccare `transactions/import/`.
5. Developer: decisioni 20–25 prima di W2, I1, K1 e del resto.

## 5. Decisioni

### 5.1 Coordinamento (risposte del coordinatore, 14/10)

- **Q1** registro BRIM in `services/brim/registry.py` (X, PL2); ordine PL2 → PL6 → PL5; non riscrivere
  `brim_provider.py:78`: la riga la sistema chi arriva dopo, all'aggiornamento di base.
- **Q2** X mette gli eventi in moduli propri e li integra presto; da lì sono di W. Le righe in `AssetDataEditorSection`,
  `EventDataImportModal`, `AssetModal`, `provider_management.py` le scrive X.
- **Q3** `TransactionFormModal`, `TransactionBulkModal`, `transactions/events/**`, `ui/data-editor/**`,
  `signHintColor.ts` non sono in nessun lotto dei colori: I1 e K1 partono al via completo.
- **Q4** `api/v1/uploads.py` è di H; per U-B3 solo `serve_plugin_static`, d'accordo con H.
- **Q5** D-W17 approvata: W unico scrittore del messaggio «file Excel danneggiato» (`preview_unreadable_workbook`).
- **Q6** P-13 → Y; P-14 → W (finestra verso la fine); parti altrui di P-15 → Y; U-B9 → W, bassa.
- **Q7–Q10** forma comune C1–C7: nomi invariati dentro i pacchetti (C1); router in `api/v1/brokers/` con `crud.py`,
  `access.py`, `brim_files.py`, `brim_parse.py`, `brim_catalog.py` (C2); transazioni come pacchetto di schemi (C3);
  mixin per le classi grandi (C4); `npm ci` permesso dal lock (C5); devWiki aggiornata nello stesso lotto (C6);
  migrazioni dopo 005 (A) e 006 (X) (C7).

### 5.2 Di prodotto (in lettura dal developer: non servono a W0 e W1)

D-W1 (punto 20, V-22), D-W2 (21), D-W3 (22), D-W7 (23), D-W15 (24), e il punto 25 (chi modifica i dati condivisi
degli asset). Raccomandazione del coordinatore sul punto 20: il divieto vale per «+ Nuovo evento»; editor e CSV
continuano ad aggiornare per data e tipo, ma non toccano un evento collegato senza conferma.

## 6. Conflitti previsti

| Con | Superficie | Gestione |
|---|---|---|
| X | registro BRIM, `brim_provider.py:78-79`, import in `brokers.py`, eventi, contratto `BRIMProvider` (impostazioni dei plugin) | W3/W4 dopo PL2/PL6; PL5 prima delle impostazioni dei plugin |
| J | `transaction_service` → `portfolio_service`; summary dei broker (U4/U5) | W1/W2 presto; J sui percorsi nuovi |
| A | `user_service.py`, `auth.py` (righe d'import), `global_settings_service` in `brokers.py` | chi integra per secondo riscrive la riga |
| H | `file_preview` in `brokers.py`; `uploads.py` | idem; U-B3 e D-W17 col suo ok |
| Colori | lotti A, C, D; T su `ui/data-editor` | §7 del piano generale; tagli dichiarati |
| Condivisi | runner, `coverage_analysis.py`, `.github`, client generato, devWiki | voci di W in aggiunta; client solo con `api sync` |

## 7. Lotti e checkpoint

| # | Lotto | Contenuto | Stato |
|---|---|---|---|
| W0 | Base e piano | questo piano; misure di base nella corsia | ✅ 14/10 |
| W1 | CP1, rinomina | `services/transactions/`, `services/brokers/`, via l'hub; import, runner, script, doc, `.github`, devWiki | ✅ 15/10, 🧊 al coordinatore |
| W2 | CP2, taglio | mixin per tema (C4); broker in CRUD, summary, accessi | ⏳ via completo |
| I1 | CP3, integrità | V-23, C-65b, L5, C-79/C-3 | ⏳ via completo |
| K1 | CP4, chiarezza | O-12, C-89, V-38, P-15 (W), I-10 S3 | ⏳ via completo |
| W3 | CP5, router | `api/v1/brokers/` per risorsa | ⏳ dopo PL2 e il commit del coordinatore |
| W4 | CP6–CP7, PL5 | `services/brim/`, rinomina poi taglio con guardia; `applyTo`, skill, guida (U-B8) | ⏳ dopo PL2, PL6 |
| W5–W6 | CP8 | U-B3, U-B4 | ⏳ dopo W4 e il commit su `uploads.py` |
| K2 | CP9 | C-70 (a, b), e (c) dopo il CP1 di H | ⏳ |
| W7 | CP10 | schemi delle transazioni come pacchetto (C3) | ⏳ |
| E1 | CP11 | eventi: I-09, I-12, V-22, I-10, I-11 | ⏳ dopo X e le decisioni |
| FE8a | CP12–CP13 | tagli delle tre modali (annuncio §7), poi la cartella dopo il lotto A | ⏳ |
| K3 | CP14… | V-37b, eventi collegabili nel Bulk, C-65a, K-2..K-4; se c'è spazio C-45, C-61, V-24, P-2, P-12 | ⏳ |
| FE8b | finale | moduli usati fuori + `features/transactions/index.ts` (dopo il lotto D); P-14, U-B9 | ⏳ |

## 8. Definizione di fatto (ogni lotto di riordino)

- Vecchi percorsi a zero in `backend/`, `scripts/`, `.github/`, `mkdocs_src/docs/developer/` (e `frontend/` per FE8);
  rinomine ≥ 95 % in `git diff -M`; patch dei test sui percorsi nuovi; nessuno shim né barile nuovo.
- `all-backend` con gli stessi conteggi della base; `ruff` pulito; `black` senza file nuovi da riformattare;
  `lint --dead-code` senza reperti nuovi; JSON di `api schema` identici (escluso `info.version`).
- `mkdocs build` stretto e `check-links` verdi; `check_source_paths.py` non peggiora.
- Piano aggiornato a ogni passo; porta 6184 libera all'handoff.

## 9. Test e selettori

- **Backend**: `services transaction|broker|brim-*|static-uploads`; `api transactions|transactions-validate|tx-balance-walk|events-suggest|batch-split-promote|transactions-wac|brokers|brim|brim-scalable|broker-access|account-deletion|broker-multiuser|uploads|uploads-serve-file|assets-events|events-target-currency`;
  `external brim-providers|brim-danske-bank|brim-degiro|brim-scalable`; `schemas transactions|brokers`; `db brim|brim-bulk`;
  `utils gate-plugin-layout|gate-plugin-i18n-ownership|gate-i18n-usage|gate-i18n-catalog|gate-docs-links`; poi
  `all-backend`.
- **Frontend** (dai lotti frontend): `front-transaction tx-unit` e gli E2E del lotto; `front-transaction all` a 4 worker
  solo ai checkpoint di FE8, con avviso.
- **Senza corsia**: `lint`, `lint --dead-code`, `black --check`, `api schema`, `mkdocs build`, `mkdocs check-links`,
  `python3 LibreFolio_devWiki/check_source_paths.py`. Script della base statica: `/tmp/libreFolio_w_static_baseline.sh <tag>`.

## 10. Specialisti

- `test-author`: i rossi di ogni difetto, le guardie contro le patch mute (C4), il registro del runner.
- `docs-writer`: doc per sviluppatori (EN) di ogni lotto, guida BRIM (U-B8), `form.en.md` (C-89, V-37b).
- `project-historian`: solo su richiesta del coordinatore (C6: le tabelle della devWiki le aggiorna W nei suoi lotti).

## 11. Rischi

- Patch mute nei tagli (C4) e stato dei lock duplicato in PL5; pool di processi BRIM (pickling per nome qualificato).
- C-79: un lock tenuto da un altro processo; V-22 cambia un contratto usato da editor e CSV.
- Router: `operationId`, tag e ordine di registrazione delle rotte (C2).
- FE8: 45 spec E2E delle transazioni, un Vitest del wizard di 900 righe; tagli dichiarati col cricchetto dei colori.
- Sicurezza (segnalata, decisione 25): gli endpoint degli eventi chiedono solo il login.

## 12. Avanzamento

### W0 — Base e piano ✅ (2026-10-14)

1. ✅ **Base verificata** (14/10, 23:02): HEAD `c9bb8f257`, worktree pulito, ramo `e-alfy-w-import-e-transazioni`.
2. ✅ **`npm ci` dal lock** in `frontend/` (C5, richiesto dal coordinatore prima di ogni test): 433 pacchetti, nessun file
   tracciato cambiato. Log: `/tmp/libreFolio_w_npm_ci.log`.
   > **Note implementazione**: npm 11.20 avvisa che 5 pacchetti hanno script d'installazione non ancora approvati
   > (`esbuild`, `fsevents`, `es5-ext`): non li ho approvati né eseguiti a mano.
3. ✅ **Base statica** (14/10, 23:06–23:10), `/tmp/libreFolio_w_static_baseline.sh base`, log
   `/tmp/libreFolio_w_base_*.log`:
   - `dev.py lint` (ruff): pulito;
   - `black --check backend/ scripts/ dev.py`: **29 file** da riformattare, già prima di W (elenco in
     `/tmp/libreFolio_w_base_black_files.txt`; fra questi `scripts/test_runner/_frontend_transaction.py`);
   - `lint --dead-code --scope backend`: **10 senza riferimenti + 26 solo dai test**, 581 di basso segnale;
   - `api schema`: copie in `/tmp/libreFolio_w_base_openapi.json` e `/tmp/libreFolio_w_base_tool_contracts.json`;
   - `mkdocs build`: verde (112 s); `mkdocs check-links`: 95 link validi;
   - `check_source_paths.py`: **7 percorsi inesistenti (12 occorrenze) in 9 pagine** (erano 10/16/11 su `459131eb8`:
     il riordino del journal fra le due basi ne ha tolti 3).
4. ✅ **`test db populate --force --clean`** sul solo `/tmp/librefolio-r13-w` (23 s), verde.
5. ✅ **Build del frontend in modo debug** (14/10, 23:16–23:22): `dev.py front build --debug`, 329 s, verde; log
   `/tmp/libreFolio_w_front_build_debug.log`. Il sito MkDocs era già costruito alle 23:08 sullo stesso albero (passo 3).
   > **⚠️ Fuori pista**: la prima `all-backend` (partita alle 23:11) l'ho fermata io dopo 4 minuti, ancora nei passi del
   > DB, quando il coordinatore ha segnalato la seconda trappola della base, trovata da J: in un worktree nuovo il server
   > condiviso costruisce il frontend in debug (svelte-check e vite) e il sito MkDocs dentro il limite di avvio di 300 s
   > (`scripts/test_runner/_server.py:48`), e cade con «Shared backend did not answer within 300s». Da me la build è
   > durata 329 s: sarebbe caduta. Porta 6184 verificata libera dopo l'arresto, nessun processo rimasto. Log della run
   > interrotta: `/tmp/libreFolio_w_base_all_backend_aborted.log`.
6. ✅ **`all-backend`** (`--workers 2`, per il carico della macchina: load fra 40 e 68 su 10 core), 23:21–23:45
   (23 min 52 s), **7/7 categorie verdi**. Comando:
   `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test --test-port 6184 --data-dir /tmp/librefolio-r13-w --workers 2 all-backend`.
   - **Conteggi della base** (riassunti finali di pytest nei log per unità di `.testLog/`, copiati in
     `/tmp/libreFolio_w_base_testLog/`; per file in `/tmp/libreFolio_w_base_counts.txt`): **12 965 passed, 28 skipped,
     0 failed, 0 errori**, su 29 riassunti. Passate parallele: 6 251 (+1 skipped), 2 191, 1 705, 944 (+2 skipped);
     consolidate: api 68, e2e 7, services 185; unità di external e db: 1 614 (+25 skipped).
   - Script di conteggio: `/tmp/libreFolio_w_count.py`. Nel log principale ci sono solo le unità seriali e consolidate
     (1 874 + 25): le passate parallele scrivono solo nei log per worker.
   - Porta 6184 libera alla fine.

   > **Note implementazione**: W0 chiuso il 14/10 alle 23:46. Base `c9bb8f257`; nessun file del repo toccato salvo
   > questo piano (non tracciato fino al checkpoint).

### W1 — CP1, rinomina di transazioni e broker ✅ (2026-10-15) — 🧊 checkpoint inviato, FROZEN

1. ✅ **Spostamenti** (14/10, 23:47), con `mv` e nessun comando git (l'indice resta al coordinatore), nomi invariati
   (C1):
   - `backend/app/services/transaction_service.py` → `backend/app/services/transactions/transaction_service.py`;
   - `backend/app/services/transaction_batch_stages.py` → `backend/app/services/transactions/transaction_batch_stages.py`;
   - `backend/app/services/transaction_batch_context.py` → `backend/app/services/transactions/transaction_batch_context.py`;
   - `backend/app/services/broker_service.py` → `backend/app/services/brokers/broker_service.py`;
   - nuovi `transactions/__init__.py` e `brokers/__init__.py`, con la sola docstring.
2. ✅ **Via l'hub** di `backend/app/services/__init__.py`: ora è la sola docstring (niente `__getattr__`, `__dir__`,
   `_EXPORTS`, `_MODULES`); nessun utilizzatore nel repo, verificato prima (§1.1).
3. ✅ **Import e percorsi**, `/tmp/libreFolio_w1_rewrite.py`: 79 file, 121 sostituzioni (import puntati in app e test;
   percorsi in docstring dei test, runner `_backend_services.py:405`, `:427`, `coverage_analysis.py:57`, `:59`, 4 pagine
   della doc per sviluppatori, 53 pagine della devWiki, il commento di `tx-bulk-promote-cost-basis.spec.ts:5`).
   - Righe d'import in file altrui: `services/user_service.py:17` (A), `api/v1/brokers.py:88`, `api/v1/transactions.py:48`,
     `services/brim_gap_fix.py:44`.
   - **Guardia dello strato** (`test_layer_boundaries.py`): i prefissi vietati diventano i pacchetti
     `backend.app.services.brokers` e `backend.app.services.transactions`; i 3 esempi sintetici prendono i percorsi
     nuovi.
4. ✅ **Similarità** col file d'origine (righe cambiate su righe totali): `transaction_service.py` +5/−11 su 1 088,
   `transaction_batch_stages.py` 2/1 108, `transaction_batch_context.py` 0/94, `broker_service.py` 1/1 000: tutte
   oltre il 99 %.
5. ✅ **Controlli statici** (`/tmp/libreFolio_w_static_baseline.sh w1`, log `/tmp/libreFolio_w_w1_*.log`):
   - vecchi percorsi (puntati e con le barre) a **0** in `backend/`, `scripts/`, `dev.py`, `.github/`,
     `mkdocs_src/docs/developer/`, `frontend/src`, `frontend/e2e`, `LibreFolio_devWiki/wiki/`; restano solo i nomi dei
     moduli nella prosa, validi con C1;
   - `ruff` pulito sui 25 file Python toccati e su tutto (`dev.py lint`); `black --check`: gli stessi 29 file della
     base (fra questi `scripts/coverage_analysis.py`, già sporco prima: non lo riformatto);
   - `lint --dead-code`: **8 senza riferimenti + 26 solo dai test** (base 10 + 26): spariscono `__getattr__` e
     `__dir__` dell'hub, nessun reperto nuovo (dopo il passo 6);
   - JSON di `api schema` **identici** alla base (escluso `info.version`): 133 `operationId`, contratti dei Tool
     invariati;
   - `mkdocs build` verde (38 s), `check-links` verde;
   - `check_source_paths.py`: 5 percorsi inesistenti (8 occorrenze) in 5 pagine. Rispetto alla base mancano
     `frontend/build/` e `frontend/src/lib/api/generated.ts`, che ora esistono perché generati dalla build del passo 5
     di W0; le pagine toccate da W1 non aggiungono percorsi mancanti.
6. ✅ **`LinkedTransactionError` tolta** (`transaction_service.py`, 3 righe).
   > **⚠️ Fuori pista**: tolto l'hub, vulture ha segnalato come inutilizzata la classe `LinkedTransactionError`. Era
   > una classe d'eccezione vuota: nessuno la solleva né la cattura, nessuna doc o pagina della devWiki la nomina; la
   > teneva viva solo la riesportazione dell'hub. Codice già morto, che l'hub nascondeva; nessun cambio di
   > comportamento. Con lei è uscito dal blocco degli import a metà file `from dataclasses import dataclass`, che
   > `ruff --fix` (I001) ha portato fra gli import della libreria standard.
7. ✅ **Test del dominio** nella corsia, verdi: `services financial-math` 212 (con la guardia dello strato),
   `transaction` 66, `broker` 39, `user-profile` 36, `edge-cases` 17, `brim-gap-fix` 99. Import di
   `backend.app.main` e dei moduli spostati riuscito; il pacchetto `services` non espone più i nomi dell'hub.
8. ✅ **`all-backend`** con lo stesso comando della base (14/10, 23:52–00:05, 13 min 55 s; log
   `/tmp/libreFolio_w_w1_all_backend.log`, log per unità copiati in `/tmp/libreFolio_w_w1_testLog/`, conteggi per file
   in `/tmp/libreFolio_w_w1_counts.txt`): 6/7 categorie verdi, un rosso in `api fx`.
   - **Conteggi**: 12 964 passed, **1 failed**, 28 skipped. Sono gli stessi 12 993 test della base, e i totali di ogni
     passata coincidono (6 251, 2 191, 1 705; nella quarta 943 + 1 rosso contro 944); le unità seriali e consolidate
     sono identiche file per file. Cambia solo la ripartizione fra i due worker.
   - **Il rosso**: `test_api/test_fx_api.py::test_providers_include_target_currencies`, «Provider ECB should have at
     least one target currency». Rilanciato da solo (`api fx`): **21 passed**, ECB con 45 valute.
   - **Triage** (skill `test-triage`), verdetto **ambiente**. `GET /fx/providers` chiama dal vivo
     `get_supported_currencies()` di ECB (`fx_providers/ecb/plugin.py:94-150`), e su un errore di rete risponde con la
     lista vuota (`api/v1/fx.py:147-151`). Nella stessa run i test esterni dei cambi registrano la rete giù («No
     currencies returned», «No rate data returned»); subito dopo l'API di ECB risponde (HTTP 200 in 0,67 s). W1 non
     tocca il codice dei cambi. È un test API che raggiunge un terzo via rete, contro la regola 6 delle istruzioni dei
     test: lo segnalo al coordinatore per X (dominio dei cambi), non è di W.
   - Porta 6184 libera alla fine.

   > **Note implementazione**: W1 pronto per il checkpoint il 15/10 alle 00:10. Nessun cambio di comportamento.
7. ✅ **Inventario di W1** (sola lettura): 80 file, 129 sostituzioni (prova a vuoto di `/tmp/libreFolio_w1_rewrite.py`).
   - Import puntati e percorsi in `backend/` (app e test), `scripts/` (runner, `coverage_analysis.py`), 4 pagine della
     doc per sviluppatori (6 percorsi), 53 pagine della devWiki (61 righe di tabelle «Source files» e 10 di prosa, tutte
     posizioni attuali), un commento E2E (`tx-bulk-promote-cost-basis.spec.ts:5`).
   - Con C1 restano validi i nomi dei moduli nella prosa (`financial-math.instructions.md:33`, docstring di
     `financial_math/__init__.py`, `models.py:177`, nomi in `coverage_analysis.py:178-179`): non si toccano.
   - **La guardia dello strato** `test_layer_boundaries.py:52-53` vieta a `financial_math` i vecchi nomi come prefissi:
     dopo lo spostamento non vedrebbe più nulla, in silenzio. Diventano i prefissi dei pacchetti
     (`backend.app.services.brokers`, `backend.app.services.transactions`), che coprono anche i moduli del taglio di W2;
     i 3 esempi sintetici (`:144`, `:145`, `:160`) prendono i percorsi nuovi. `financial_math` non importa nessuno dei
     tre moduli del batch (verificato), quindi l'allargamento non fa rossi.
   - Nessun test o gate scansiona solo il primo livello di `services/`; i glob delle famiglie (`*_providers`,
     `*_plugins`) non vedono `transactions/` e `brokers/`.
