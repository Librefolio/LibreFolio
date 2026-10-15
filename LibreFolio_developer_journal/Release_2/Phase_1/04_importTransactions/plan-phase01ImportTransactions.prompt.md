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
| W0 | Base e piano | questo piano; misure di base nella corsia | ✅ 14/10, `64e3d0a7d` |
| W1 | CP1, rinomina | `services/transactions/`, `services/brokers/`, via l'hub; import, runner, script, doc, `.github`, devWiki | ✅ 15/10, `9a44bdcec` |
| W2 | CP2, taglio | mixin per tema (C4); broker in CRUD, summary, accessi; stadi del batch per tema | ✅ 15/10, 🧊 al coordinatore |
| I1 | CP3, integrità | V-23, C-65b, L5, C-79/C-3 | ✅ 15/10, 🧊 al coordinatore |
| K1 | CP4, chiarezza | O-12, C-89, V-38, P-15 (W); I-10 S3 chiusa senza codice | ✅ 15/10, 🧊 al coordinatore |
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

   > **Note implementazione (coordinatore, 15/10 ~00:10)**: CP1 committato come `9a44bdcec` (codice, rinomine
   > R099–R100) e `64e3d0a7d` (journal); base aggiornata con il merge `2c89a7b24` (`dev_release2` a `4471d39b4`: T-1,
   > T-2, G, regole del piano). W1 entra in `dev_release2` dopo A1, insieme a W2.

### Revisione combinata `2c89a7b24` ✅ (2026-10-15)

- HEAD `2c89a7b24`, worktree pulito; nessuna modifica del backend fra `c9bb8f257` e `4471d39b4`
  (`git diff --stat c9bb8f257 4471d39b4 -- backend scripts/list_api_endpoints.py` vuoto), quindi lo schema di
  `4471d39b4` è quello esportato per la base.
- `api schema` di `2c89a7b24` identico alla base (escluso `info.version`), contratti dei Tool compresi.
- Nella corsia: `services transaction` 66, `broker` 39, `financial-math` 212 (con la guardia dello strato), verdi.

### W2 — CP2, taglio di transazioni e broker ✅ (2026-10-15) — 🧊 checkpoint inviato, FROZEN

**Via del coordinatore** (15/10 ~00:10): W2, I1 e K1, un checkpoint FROZEN ciascuno; non dipendono dalle decisioni
20–25 (solo E1). Forma: C4 (mixin per tema, la classe composta resta nel suo file col suo nome) e C1 (moduli nuovi
con nomi brevi per tema).

**Disegno** (verificato con `/tmp/libreFolio_w2_groups.py`: i 33 stadi in gruppi chiusi, nessuna chiamata fra gruppi;
i 29 membri di `TransactionService` e i 16 di `BrokerService` assegnati tutti, nessun doppione):

| Modulo | Contenuto |
|---|---|
| `transactions/transaction_service.py` | `TransactionService`, composta dai mixin qui sotto: `__init__`, `delete_by_broker`, `execute_batch` |
| `transactions/access.py` | `TransactionAccessMixin`: ruolo su un broker, controllo d'accesso del batch |
| `transactions/validation.py` | `TransactionValidationMixin`: collegamento a un evento, costo obbligatorio, regole delle coppie |
| `transactions/queries.py` | `TransactionQueryMixin`: `query`, partner delle coppie, `get_by_ids` |
| `transactions/balances.py` | `TransactionBalancesMixin`: replay dei saldi, saldi a una data, cassa e quantità |
| `transactions/event_suggestions.py` | `TransactionEventSuggestionsMixin`: `suggest_events_bulk` |
| `transactions/promotion.py` | `TransactionPromotionMixin` e `_PromoteCandidate`: promozione, mappe dei tipi di split e promozione, suggerimenti |
| `transactions/auto_cost.py` | `TransactionAutoCostMixin`: il costo Auto (WAC) delle righe del batch |
| `transactions/transaction_batch_stages.py` | gli stadi che aprono e chiudono il batch: parse, caricamento e accessi, replay dei saldi, risposta |
| `transactions/batch_edits.py` | cancellazioni, split, modifiche, controllo delle coppie modificate |
| `transactions/batch_creates.py` | creazioni (con il rifiuto degli `INDEX`), promozioni, collegamenti delle coppie nuove |
| `transactions/batch_costs.py` | WAC e cambi del batch, controllo del costo di carico |
| `brokers/broker_service.py` | `BrokerService`, composta dai due mixin: creazione, lettura, modifica, cancellazione |
| `brokers/access.py` | `BrokerAccessMixin`: ruoli, broker accessibili, gestione degli accessi, uscita e autoretrocessione |
| `brokers/summary.py` | `BrokerSummaryMixin`: `get_summary`, costo medio delle posizioni, ultimi prezzi |

- I corpi passano **alla lettera**; cambia solo `_find_promote_rule_match`, che chiamava
  `TransactionService._check_promote_constraints` e ora chiama il metodo sul mixin che lo definisce (stessa funzione).
- **Via le due riesportazioni** di `transaction_service.py` (`BalanceValidationError as BalanceValidationError`,
  `_parse_lenient as _parse_lenient`): chi le usa importa dal modulo che le definisce (C3, C4) —
  `brokers/broker_service.py` e `populate_mock_data.py` da `transaction_batch_context`, il test di `_parse_lenient` da
  `transaction_batch_stages`.
- **Patch dei test**: solo due, sugli attributi di classe (`BrokerService.delete_bulk`, `TransactionService.delete_by_broker`,
  `test_user_profile.py:544`, `:572`), che restano validi con i mixin; nessuna patch su globali dei moduli. Guardia C4:
  uno script AST in `/tmp`, prima e dopo.

1. ✅ **Il taglio** (15/10, 00:40), `/tmp/libreFolio_w2_cut.py`, senza comandi git: i corpi passano alla lettera dalle
   posizioni dell'AST, con i commenti attaccati e le intestazioni delle sezioni; ogni modulo nuovo parte dal blocco
   d'import originale, poi `ruff --fix --select F401,I001` e `black`. Righe dopo il taglio:
   `transaction_service.py` 137 (era 1 082), `transaction_batch_stages.py` 251 (era 1 108), `broker_service.py` 526
   (era 1 000); moduli nuovi da 63 (`access.py`) a 368 righe (`batch_creates.py`).
   - **Prova della copia alla lettera** (`/tmp/libreFolio_w2_verbatim.py`): gli 80 membri dei tre moduli d'origine
     (metodi, funzioni, `SPLIT_TYPE_MAP`, `_PromoteCandidate`, `BROKER_NAME_RECOVERY`) hanno ciascuno una copia con
     AST identico nel modulo nuovo; l'unica differenza è quella voluta, in `_find_promote_rule_match`.
   - **Le due riesportazioni tolte**; `populate_mock_data.py:81` prende `BalanceValidationError` da
     `transaction_batch_context`, `test_transaction_service.py:40` `_parse_lenient` da `transaction_batch_stages`.
   - Le docstring dei moduli e dei mixin dicono il tema e cosa si aspettano dalla classe composta (per esempio
     `promotion.py`: `session`, `execute_batch`, `_enforce_batch_access`, `_get_accessible_broker_ids`); quelle di
     `transactions/__init__.py` e `brokers/__init__.py` elencano i moduli.
   - MRO: `TransactionService` → 7 mixin → `object`; `BrokerService` → 2 mixin → `object`.
2. ✅ **Guardia contro le patch mute** (C4, `/tmp/libreFolio_w2_patch_guard.py`), prima e dopo: 2 patch sui due
   pacchetti, tutte e due sugli attributi di classe (`test_user_profile.py:544`, `:572`), efficaci; nessuna patch su
   globali di modulo; 0 problemi.
3. ✅ **Test del dominio** nella corsia, verdi: `services transaction` 66, `broker` 39, `user-profile` 36, `edge-cases`
   17, `brim-gap-fix` 99, `financial-math` 212, `brim-create-transaction` 14; `api transactions` 23,
   `transactions-validate` 11, `tx-balance-walk` 9, `events-suggest` 9, `batch-split-promote` 35, `transactions-wac` 20,
   `brokers` 29, `broker-access` 25 (+1 skipped), `account-deletion` 6, `broker-multiuser` 14.
4. ✅ **Statici**: `ruff` e `black` puliti sui 18 file dei due pacchetti e sui test toccati; vulture con gli stessi
   reperti di dopo W1 (8 senza riferimenti + 26 solo dai test, 581 di basso segnale); JSON di `api schema` identici
   alla base.
5. ✅ **Doc per sviluppatori** (solo EN, solo percorsi e la tabella dei moduli): `backend/transactions/service.md`
   (la tabella dei file diventa quella dei 13 moduli), `backend/transactions/wac.md:317`,
   `architecture/database/assets_pricing.md:88` (il rifiuto degli `INDEX` è in `batch_creates.py`),
   `architecture/patterns/brim_plugin_guide.md:696-698`, `lint_gates.md:57-58`, `frontend/data-quality-banner.md:176`,
   `architecture/access_control.md:87-93`.
   > **⚠️ Fuori pista**: in `access_control.md` l'elenco dei metodi sotto la frase che cambio nominava `add_access()`,
   > `update_access()` e `remove_access()`, che non esistono; ora elenca quelli veri del mixin (`list_accesses()`,
   > `bulk_update_access()`, più quelli che c'erano). L'elenco degli endpoint poco sotto è sbagliato allo stesso modo
   > (`POST` e `/access/{user_id}` invece di `PUT /access` e `/access/me`), ma non descrive il codice spostato: voce
   > W-B10 del backlog.
6. ✅ **devWiki** (C6, `/tmp/libreFolio_w2_wiki.py`): 31 righe in 26 pagine. Le righe che nominano una funzione spostata
   puntano al modulo nuovo; quelle che nominano il servizio in generale restano su `transaction_service.py` e
   `broker_service.py`, che contengono ancora le due classi. Restano com'erano le due righe di prosa di
   `decisions/auto-cost-basis-zero-without-position.md:24-26`, legate a un commit («Checked at `083ed26dc`») con i suoi
   numeri di riga. `check_source_paths.py`: 5 percorsi inesistenti (gli stessi di dopo W1), 3 853 citati.
7. ✅ **`scripts/coverage_analysis.py`**: la priorità HIGH e la classe dei servizi centrali passano dai due file ai due
   pacchetti (`backend/app/services/transactions/`, `backend/app/services/brokers/`), così i moduli nuovi non scendono
   a LOW.
8. ✅ **`all-backend`** con il comando della base (15/10, 00:35–00:48, 13 min 37 s; log
   `/tmp/libreFolio_w_w2_all_backend.log`, log per unità in `/tmp/libreFolio_w_w2_testLog/`, conteggi in
   `/tmp/libreFolio_w_w2_counts.txt`): **7/7 verdi, 12 965 passed, 28 skipped, 0 failed**, gli stessi conteggi della
   base; le unità seriali e consolidate sono identiche alla base file per file. Il rosso d'ambiente di W1 (ECB) non si
   è ripresentato. Porta 6184 libera alla fine.

   > **Note implementazione**: W2 pronto per il checkpoint il 15/10 alle 00:50. Nessun cambio di comportamento: corpi
   > alla lettera (prova AST), API identica, stessi conteggi.

   > **Note implementazione (coordinatore, 15/10 ~00:50)**: CP2 committato come `97aa874a6` (codice) e `d62c9c098`
   > (journal). Aggiornamento di base aperto dal coordinatore nel mio worktree: `git merge --no-ff --no-commit
   > 8250d92b3` (`dev_release2` con A1, `services/accounts/`, e H CP1, `services/platform/` e `services/files/`).

### Aggiornamento di base `8250d92b3` (A1, H CP1) ✅ (2026-10-15) — 🧊 FROZEN, merge commit al coordinatore

1. ✅ **Conflitti risolti** (00:52): 6, tutti di righe vicine, nessuno di logica. Tenuti i percorsi nuovi di tutti i
   lati: miei (`transactions/`, `brokers/`, i mixin), di A (`accounts/`) e di H (`platform/`, `files/`).
   - `backend/app/api/v1/brokers.py`: `brokers.broker_service` (W) accanto a `files.file_preview` (H);
   - `backend/app/services/accounts/user_service.py` (spostato da A): `accounts.auth_service` (A) e
     `brokers.broker_service` (W);
   - `backend/test_scripts/test_api/test_account_deletion_api.py`: `accounts.user_service` (A) e
     `brokers.broker_service` (W);
   - `backend/test_scripts/test_db/populate_mock_data.py`: i miei due import da `transactions/`; la riga vecchia di
     `static_uploads` cade, perché H l'ha già messa al suo posto come `files.static_uploads`;
   - `scripts/coverage_analysis.py`: `brokers/` e `transactions/` (W) con `accounts/user_service.py` (A), senza
     riformattare;
   - `LibreFolio_devWiki/wiki/problems/account-deletion-orphaned-brokers.md`: `accounts/user_service.py` (A) e
     `brokers/access.py` (W).
   - `ruff check --select I --fix` e `ruff check` puliti sui 5 file Python; nessun segno di conflitto rimasto. **Stage
     dei soli 6 file risolti** (richiesto dal coordinatore); nessun commit.
2. ✅ **Vecchi percorsi** di W, A e H (puntati, con le barre, e `from backend.app.services import <modulo spostato>`):
   **0** in `backend/`, `scripts/`, `dev.py`, `.github/`, `mkdocs_src/docs/developer/`; 0 di W ovunque. Fuori dal
   perimetro del cancello restano 26 citazioni di A e H: 24 nella prosa della devWiki e 2 commenti del frontend
   (`frontend/src/lib/stores/app/settings.test.ts:18`, `frontend/e2e/files-uploader.spec.ts:71`).
   `check_source_paths.py`: 5, come prima.
3. ✅ **Patch dei test sui moduli spostati** (`/tmp/libreFolio_merge_patch_guard.py`, la guardia di W2 allargata a
   `accounts`, `platform` e `files`): 44 patch, tutte efficaci. Lo script ne segnalava una,
   `test_static_uploads.py:431`, `monkeypatch.setattr(static_uploads, "magic", _FakeMagic, raising=False)`: è voluta,
   perché `magic` esiste solo con python-magic installato (`import magic` dentro un `try`, `static_uploads.py:39`) e il
   modulo lo legge (`:189`); la riga è identica a prima dello spostamento di H.
4. ✅ **`front build --debug`** (96 s), verde.
5. ✅ **`all-backend`** sulla revisione fusa (indice, non committata), stesso comando della base (00:54–01:07,
   13 min 18 s; log `/tmp/libreFolio_w_merge_all_backend.log`, conteggi in `/tmp/libreFolio_w_merge_counts.txt`):
   **7/7 verdi, 12 965 passed, 28 skipped, 0 failed**, uguale a W2 e alla base; le unità seriali e consolidate sono
   identiche a W2 file per file. Porta 6184 libera alla fine.
6. ✅ **`api schema`** della revisione fusa identico a quello di `8250d92b3` (escluso `info.version`), contratti dei
   Tool compresi; quello di riferimento l'ho esportato da un albero estratto con `git archive 8250d92b3` in
   `/tmp/libreFolio_w_ref_8250/`, senza toccare il worktree. `8250d92b3` ha lo stesso schema della mia base
   `c9bb8f257`.

   > **Note implementazione**: aggiornamento di base pronto per il merge commit il 15/10 alle 01:10. Questo piano ha le
   > note dell'aggiornamento non in stage (il coordinatore ha chiesto lo stage dei soli 6 file risolti).

   > **Note implementazione (coordinatore, 15/10 ~01:09)**: merge `17a644123` e nota `9198698c3`; W1 e W2 in
   > `dev_release2` con `998fd2701`; il mio ramo portato in avanzamento veloce a `998fd2701`, worktree pulito.

### I1 — CP3, integrità (V-23, C-65b, L5, C-79/C-3) ✅ (2026-10-15) — 🧊 checkpoint inviato, FROZEN

**Via del coordinatore** (15/10 ~01:09): «Via per I1 (integrità: V-23, C-65b, L5, C-79/C-3), poi K1, un checkpoint
FROZEN ciascuno. Ogni difetto con il rosso visto prima della cura. Nelle parti frontend, le regole di T-1. Dalle 09:00
c'è la finestra della galleria: niente `all-backend` né build pesanti. I tuoi lotti con frontend entrano prima delle
08:45 o dopo la chiusura.» Base: HEAD `998fd2701`, pulito (verificato alle 01:12).

**Disegno** (verificato sul codice di `998fd2701`):

- **V-23, backend**: `_append_access_issues` (`transaction_batch_stages.py:153-175`) mette ogni rifiuto d'accesso su
  `operation="create", index=0`. Cura: un rifiuto per ogni riga che tocca un broker senza EDITOR, sulle sue coordinate
  (`create`/indice della riga; `update`, `delete`, `split`, `promote` con l'indice e il `ref_id` della transazione
  salvata sul broker negato); una riga che tocca due volte lo stesso broker ne riceve uno solo; un `promote` per
  `link_uuid` non ne riceve, perché il rifiuto sta già sulla sua `create`. Il frontend non cambia: mappa già
  `operation:index` sulle righe (`lastOpsIndexMap`) e le etichette danno `1a` al mittente, `1b` al ricevente.
- **V-23, frontend**: in `TransactionBulkModal.svelte` la lista `brokers` (`:595`, solo i modificabili) serve solo a
  mostrare: risolutore dei messaggi (`:1452`), icone (`:1455`), `renderBrokerHtml` (`:1611`), etichette (`:2179`).
  Cura: quella lista diventa quella dei broker visibili (`getAccessibleBrokers()`); il broker di default di una riga
  nuova resta sui modificabili (`:199`). Prima del rosso, solo agganci di test sul bottone `tx-bulk-issue`
  (`data-code`, `data-row-label`), senza effetto sul comportamento.
- **C-65b**: `GET /transactions?asset_event_id=` (ricerca inversa evento → transazioni), un campo in `TXQueryParams`,
  un filtro in `queries.py`; resta dentro i broker che l'utente vede. Oggi il parametro è ignorato.
- **L5**: `get_brim_file_preview` (`brokers.py:695`) e `download_file` (`:767`) chiamano `brim_provider.get_file_path`
  sull'event loop; cura con `asyncio.to_thread`. Guardia AST (pura): nessuna chiamata diretta a una funzione sincrona
  di `brim_provider` dentro un `async def` di `api/v1/`; oggi trova esattamente quelle due.
- **C-79/C-3**: `delete_files_for_brokers` (`brim_provider.py:1258`) cancella i file ma lascia
  `<stato>/broker_<id>/` (creati tutti e tre da `save_uploaded_file`, `:820`) e `.locks/broker_<id>.lock`. Cura: dopo
  i file, sotto il lock del broker, `rmdir` delle tre cartelle se vuote (un contenuto sconosciuto resta, con un
  avviso nel log) e cancellazione del file di lock. La voce in `_BROKER_LOCKS` resta, per scelta: toglierla potrebbe
  dare due `RLock` alla stessa chiave mentre un'operazione è in volo.

**Passi**:

1. ✅ **Agganci di test** (15/10, 01:20): sui due bottoni `tx-bulk-issue` (banner d'errore e d'avviso) di
   `TransactionBulkModal.svelte`, `data-code={issue.code}` e `data-row-label={getVisualRowLabel(issue)}`. Nessun
   effetto sul comportamento, nessuna classe.
2. ✅ **Rossi** (15/10, 01:22–01:52; test-author `i1-reds`, solo file di test e il registro del runner). Tutti rossi
   per il difetto, con le premesse e i controlli già esistenti verdi nelle stesse run:
   - **C-79/C-3** `services brim-provider-base`: 3 nuovi in `test_brim_provider_base.py`
     (`test_delete_files_for_brokers_removes_the_broker_folders_and_lock`, `…_keeps_a_folder_holding_a_foreign_file`,
     `…_removes_the_empty_folders_of_a_broker_without_files`); rossi sull'ultima asserzione: le tre cartelle e
     `.locks/broker_42.lock` restano;
   - **V-23 E2E** `front-transaction tx-broker-access "V-23"`: `V-23 — clone of [Asym-c]: …`, tre controlli morbidi tutti
     rossi: cella `From: Interactive BrokersTo: —`, `data-row-label` `1a` invece di `1b`, messaggio «… for Broker #2»;
   - **V-23 API** `api broker-multiuser`: classe nuova `TestAccessRefusalPlacement` (TRANSFER verso un VIEWER, in
     `validate` e `commit`; un rifiuto per riga; update; delete; split di un CASH_TRANSFER) e un'asserzione in coda a
     `test_cross_broker_access_failure_is_atomic`: 8 rossi, tutti con l'unico `(create, 0, None)` di oggi;
   - **C-65b** `api transactions`: `test_get_transactions_filters_by_asset_event_id` (ottiene `[87, 88, 89]` invece di
     `[87]`) e `test_get_transactions_rejects_non_positive_asset_event_id[0|-1]` (200 invece di 422);
   - **L5** `utils gate-event-loop-io` (file nuovo `test_utilities/test_event_loop_brim_io_gate.py`, voce nuova
     `gate-event-loop-io` in `_backend_utils.py`, `isolation="pure"`): rosso con esattamente `brokers.py:695
     get_brim_file_preview` e `brokers.py:767 download_file`; 13 controlli del rilevatore verdi.
   - Log: `/tmp/libreFolio_w_i1_{A,B,C,D,E}_console.log`, `/tmp/libreFolio_w_i1_B_error-context.md`.

   > **⚠️ Fuori pista**: le azioni `services` ricreano vuoto il DB della corsia e `front-transaction` lo ripopola
   > (`db populate --force --with-reports`): test-author ha lanciato prima i servizi e poi il frontend, così la corsia
   > è rimasta col seme standard; in `broker_reports/` ci sono ora i report d'esempio.
3. ✅ **Cure** (15/10, 01:55–02:00):
   - **C-79/C-3** (`brim_provider.py`): `delete_files_for_brokers` chiama `_remove_broker_storage(broker_id)` dopo i
     file, nello stesso `try` del best-effort. Sotto il lock del broker: `rmdir` delle tre cartelle di stato (una non
     vuota resta, con un avviso nel log), poi `unlink` del file di lock mentre è tenuto. La voce di `_BROKER_LOCKS`
     resta, per scelta (docstring).
   - **L5** (`api/v1/brokers.py:695`, `:767`): `await asyncio.to_thread(brim_provider.get_file_path, file_id)`.
   - **C-65b**: `asset_event_id` (`Query(None, gt=0)`) in `query_transactions`, campo in `TXQueryParams`, filtro in
     `queries.py` (colonna già indicizzata, `idx_transactions_asset_event`); docstring dell'endpoint. Nei due test che
     chiamano `query_transactions` direttamente con tutte le chiavi, `asset_event_id=None` in più.
   - **V-23 backend** (`transaction_batch_stages.py`): `_denied_brokers` (i broker toccati senza EDITOR),
     `_rows_touching_brokers` (ogni riga con i broker che tocca: `create` col suo, `update`/`delete`/`split`/`promote`
     con quelli delle transazioni salvate che nomina, `ref_id` compreso), `_append_access_issues` (un rifiuto per riga
     e broker negato) e un ripiego a livello di broker (`index=-1`) per un broker negato che nessuna riga spiega: un
     rifiuto non può sparire. `preload_and_authorize` risponde `bool(denied)`.
   - **V-23 frontend** (`TransactionBulkModal.svelte`): la lista `brokers`, usata solo per mostrare (nomi, icone,
     messaggi, etichette), diventa `getAccessibleBrokers()`; il broker di default delle righe nuove resta sui
     modificabili.
4. ✅ **Verdi mirati** (15/10, 01:56–02:07), uno alla volta nella corsia:
   - `services brim-provider-base` 37 passed; `utils gate-event-loop-io` 14 passed; `api transactions` 26 passed;
     `api broker-multiuser` 20 passed; `front-transaction tx-broker-access` 5 passed (build di debug rifatta alle
     02:00 dal server condiviso: il bundle contiene la cura); `front-utility core-unit` 4 245 (cancelli T-1 e HTML
     compresi); `front-transaction tx-unit` 887; `front-utility component-unit` 3 162 (`ImportWizardModal.test.ts`, che
     monta il bulk, compreso).
   - `ruff` pulito e `black --check` pulito sugli 11 file Python toccati; Prettier pulito sui 2 file frontend.
   - `api schema` contro la revisione fusa (`/tmp/libreFolio_w_merge_openapi.json`, escluso `info.version`):
     **solo** il parametro `asset_event_id` di `GET /api/v1/transactions` e la sua descrizione; contratti dei Tool
     identici. `api sync` verde, nessun file tracciato toccato (il client generato è ignorato).
5. ✅ **`all-backend` ed E2E del lotto** (15/10):
   - `all-backend` (02:08–02:21, 13 min 12 s, `--workers 2`; log `/tmp/libreFolio_w_i1_all_backend.log`, unità in
     `/tmp/libreFolio_w_i1_testlog/`, conteggi in `/tmp/libreFolio_w_i1_counts.txt`): **7/7 verdi, 12 991 passed, 28
     skipped, 0 failed**, cioè la base (12 965) più i 26 test nuovi (3 servizi, 14 del cancello, 6 multiutente, 3 delle
     transazioni). Unità seriali e consolidate identiche alla run dell'aggiornamento di base file per file; cambia solo
     la distribuzione fra i due worker paralleli (11 091 → 11 117).
   - E2E in più, sul bulk e i broker di sola lettura: `front-transaction tx-bulk-operations` 10, `tx-clone` 8,
     `tx-paired-edit` 4, tutti verdi (02:22–02:25).
   - `lint` pulito; `lint --dead-code` senza reperti nuovi (gli stessi di W2, coi percorsi nuovi di A e H);
     `mkdocs build` stretto verde; `mkdocs check-links` 95 validi; `check_source_paths.py` 5, come prima;
     `git diff --check` pulito; porta 6184 libera.
6. ✅ **Doc, piano, backlog** (15/10, 02:10–02:27):
   - doc per sviluppatori (docs-writer `i1-docs`, nessuna build sua): `backend/transactions/service.md` («🔐 Access
     Control»: il contratto per riga, con tabella e ripiego), `backend/brim/architecture.md` («📂 File Lifecycle»: la
     pulizia alla cancellazione del broker; «⚡ Concurrency & off-loading»: riga **File reads** col cancello),
     `test-walkthrough/utils.md` (riga `gate-event-loop-io`). Nessuna pagina per sviluppatori elenca i filtri di
     `GET /transactions`: `asset_event_id` è documentato solo nell'OpenAPI.
   - devWiki: una riga nella tabella «Source files» di `problems/event-loop-blocking.md` (il cancello).
   - backlog, sezione W: W-B11 (`brokerName()` senza chiamanti nel bulk, via col taglio FE8a) e W-B12
     (`test_cross_broker_access_failure_is_atomic` lascia i suoi broker). Le chiusure di V-23 (sezione V), C-79
     (sezione R), C-65b (voce C-65), L5 e C-3 (backlog 38) le segno al coordinatore: non sono nella mia sezione.

   > **Note implementazione**: I1 pronto per il checkpoint il 15/10 alle 02:27. Per W4 (PL5): il cancello
   > `gate-event-loop-io` punta a `backend/app/services/brim_provider.py` e fallisce di proposito se il file sparisce;
   > lo spostamento in `services/brim/` aggiorna le sue due costanti (`BRIM_PROVIDER`, `BRIM_PROVIDER_MODULE`) e valuta
   > se estenderlo ai moduli tagliati.
   >
   > **Nota di prodotto**: un rifiuto per riga vuol dire N righe nel banner quando N righe toccano un broker di sola
   > lettura, come gli altri errori di riga. Nel form aperto dal bulk, che filtra per `operation` e `index`, un update
   > rifiutato compare ora sulla sua riga; prima finiva su `create:0` e lì non si vedeva.

   > **Note implementazione (coordinatore, 15/10 ~02:26)**: I1 committato come `5e96df752` (codice) e `c4d8efcdc`
   > (journal); base aggiornata con il merge `123c21efc` di `dev_release2` a `75a20ce29` (H CP2a, pacchetto `config/` e
   > guardia `services config-package`; X CP1 e CP2a, registri per famiglia, BRIM in `services/brim/registry.py`,
   > `services/assets/` senza shim). Unione automatica, worktree pulito.

### Revisione combinata `123c21efc` (I1 + H CP2a + X CP1/CP2a) ✅ (2026-10-15) — 🧊 FROZEN

Richiesta del coordinatore: `front build --debug`; `services config-package`; `utils gate-event-loop-io`, `services
brim-provider-base`, `api transactions`, `api broker-multiuser`; `all-backend`; `api schema` contro `75a20ce29` (deve
cambiare solo `asset_event_id`); E2E `tx-broker-access`, `tx-bulk-operations` e `core-unit`; poi handoff FROZEN, con
l'ingresso di I1 in `dev_release2` prima delle 08:45.

1. ✅ **Base** (02:27): HEAD `123c21efc` (genitori `c4d8efcdc` e `75a20ce29`), worktree pulito, porta 6184 libera. Il
   merge tocca 5 dei miei file solo con righe altrui: in `brokers.py` e `brim_provider.py` l'import di
   `BRIMProviderRegistry` da `services/brim/registry.py` e di `AssetCRUDService` da `services/assets/crud.py` (X); in
   `_backend_utils.py` e nella pagina `event-loop-blocking.md` il percorso `assets/core.py` (X); il backlog. Le mie
   righe di I1 ci sono tutte; la scansione L5 non trova più chiamate dirette a `brim_provider`.
2. ✅ **`front build --debug`** (02:27–02:29, 118 s): verde, svelte-check 0 errori e 0 avvisi.
3. ✅ **`services config-package`**: 472 passed. La guardia scandisce solo `backend/app/**`: i miei sei moduli toccati
   (`services/brim_provider.py`, `services/transactions/queries.py`, `services/transactions/transaction_batch_stages.py`,
   `api/v1/brokers.py`, `api/v1/transactions.py`, `schemas/transactions.py`) passano uno per uno. I quattro file di test
   di I1 non leggono variabili d'ambiente (grep di `os.environ`/`getenv` a zero), e nessuna riga aggiunta da I1 ne legge.
4. ✅ **Selettori di I1** (02:29–02:31): `utils gate-event-loop-io` 14, `services brim-provider-base` 37,
   `api transactions` 26, `api broker-multiuser` 20; gli stessi conteggi di prima del merge.
5. ✅ **`api schema`** contro `75a20ce29` (esportato da un albero `git archive 75a20ce29` in `/tmp/libreFolio_w_ref_75a2/`,
   escluso `info.version`): cambia **solo** `GET /api/v1/transactions`, col parametro `asset_event_id` e la descrizione
   dell'endpoint; contratti dei Tool identici. `openapi.json` e `generated.ts` sono esclusi dal controllo di freschezza
   della build (`_BUILD_GENERATED_SOURCES`, `scripts/cli_base.py:513`): l'esportazione non fa ricostruire il frontend.
6. ✅ **`all-backend`** (02:32–02:44, 11 min 55 s, `--workers 2`; log `/tmp/libreFolio_w_i1m_all_backend.log`, unità in
   `/tmp/libreFolio_w_i1m_testlog/`, conteggi in `/tmp/libreFolio_w_i1m_counts.txt`): **7/7 verdi, 13 458 passed, 28
   skipped, 0 failed**. Unità seriali e consolidate identiche alla run di I1 file per file; il gruppo parallelo passa da
   11 117 a 11 584 (+467), e il conteggio dei test raccolti (`pytest --collect-only` sui 66 file di test toccati dal
   merge, prima in un albero `git archive c4d8efcdc`, poi nel worktree) lo spiega tutto: `test_config_package.py` nuovo
   (+472, H) e `test_provider_core_cache.py` 33 → 28 (−5, X: tolto il test parametrizzato
   `test_legacy_and_canonical_public_symbols_share_identity`, quello dei simboli vecchi). Nessun altro file cambia
   numero.

   > **⚠️ Fuori pista**: 2 avvisi nuovi nel gruppo parallelo (worker 1), `PytestUnhandledThreadExceptionWarning` da
   > aiosqlite («Event loop is closed») in
   > `test_ai_export_components_portfolio_broker_financial.py::TestPerformanceBuckets::test_performance_path_uses_detail_owned_uniform_density[broker-broker.performance-components1-full-30]`:
   > un thread di connessione che finisce dopo la chiusura del loop. Non è un rosso; il file non è toccato né da I1 né
   > dal merge; da solo (`services ai-export test_performance_path_uses_detail_owned_uniform_density`) 6 passed e nessun
   > avviso, quindi dipende dai tempi sotto carico. Dominio AI Export, non W: segnalato al coordinatore. Dopo quel
   > rilancio il DB della corsia è vuoto (le azioni `services` lo ricreano); il prossimo E2E lo ripopola.
7. ✅ **E2E e Vitest** (02:50–02:53), sulla build di debug delle 02:29 («Frontend build is up to date»):
   `front-transaction tx-broker-access` 5 passed, `front-transaction tx-bulk-operations` 10 passed, `front-utility
   core-unit` 4 245 (130 file), gli stessi conteggi di prima del merge. Porta 6184 libera alla fine.

   > **Note implementazione**: revisione combinata `123c21efc` validata il 15/10 alle 02:56; pronta per l'ingresso di I1
   > in `dev_release2`. Per W4 (PL5): `services/brim/` esiste già, con `__init__.py` e `registry.py` di X;
   > `brim_provider.py:78-79` importa ora da `services/assets/crud.py` e `services/brim/registry.py`.

   > **Note implementazione (coordinatore, 15/10 ~03:06)**: I1 in `dev_release2` come `dc7e4e48e` (merge di `625e3dacc`
   > su `ae998da78`); record del coordinatore in `f39be79b7` (CHANGELOG, chiusure di V-23, C-79, C-65 ricerca inversa, L5,
   > C-3; W-B9 spostata a X; l'avviso di aiosqlite è C-93, a J). Il mio ramo è avanzato a `f39be79b7`, pulito.

### K1 — CP4, chiarezza (O-12, C-89, V-38, P-15 parte W, I-10 S3) ✅ (2026-10-15) — 🧊 checkpoint inviato, FROZEN

**Via del coordinatore** (15/10 ~03:06): «Via per K1. Regole per oggi: `ui/data-editor` è frontend, e T lo tiene in coda
finché K1 non entra. K1 entra prima delle 08:45 solo se è pronta e validata; altrimenti dopo la chiusura della finestra
della galleria. Dalle ~08:45, al mio avviso, niente `all-backend` né build pesanti fino all'avviso di fine.» Base: HEAD
`f39be79b7`, pulito, porta libera (03:06).

**Verifica sul codice** (`f39be79b7`):

- **O-12**: `importWizard.assetsCount` («{n} unique assets, {m} need resolution») senza plurale nelle 4 sorgenti
  `frontend/src/lib/i18n/importWizard/<lang>.json:45`; il chiamante (`ImportWizardModal.svelte:4845`) passa due numeri
  (`stats.uniqueAssets`, `stats.unresolvedCount`). Cura: solo l'ICU nelle 4 sorgenti, il componente non cambia.
- **P-15, parte W**: in `DataEditor.svelte` i contatori «{n} modified/deleted/new» (`:661-669`) e l'`aria-label` della
  levetta delle righe vecchie (`:652`, «Show/Hide N stale rows»); in `DataImportModal.svelte` gli `aria-label` «Help»
  (`:211`) e «Close» (`:220`), cioè W-B8. «Date» è già `common.date` (M-17/M-18), quindi consegnata; «Reset layout» sta
  in `components/table/ColumnVisibilityToggle.svelte:177` e va a Y con «max». Chiavi nuove: `dataEditor.counter.*` e
  `dataEditor.stale{Show,Hide}`, con plurale ICU dove la lingua accorda; «Help» e «Close» riusano `csvImport.helpTitle`
  (già il `title` del bottone) e `common.close`.
- **V-38**: il form divide i problemi per indice (`TransactionFormModal.svelte:971-972`); `balanceCashNegative` arriva
  con l'indice della riga, e finisce sotto il titolo dei problemi dei campi. La lista del saldo non ha un
  `data-testid`. Cura: la divisione per codice, come nel bulk (`isBulkBalanceIssue`), tenendo nel saldo anche
  l'indice negativo di oggi.
- **C-89**: le due date «Da» e «A» del pannello abbinato (`TransactionFormModal.svelte:1641-1700`), che FX e
  trasferimenti condividono (`pairLayout`). Cura: un suggerimento solo per `pairLayout === 'fx'` (chiave
  `transactions.form.fxDatesHint`, classi senza palette: `text-lf-muted`, T-1), e la stessa frase in
  `user/transactions/form.{en,it,fr,es}.md` dopo «Each side has its own date», scritta da me nelle 4 lingue (modifica
  piccola, regola di `mkdocs.instructions.md`) e poi `translate-stamp`.
- **I-10 S3**: ⚠️ **contraddetta dal contratto documentato**. Il tooltip `dataEditor.autoEvent.tooltip` e la guida
  (`user/assets/detail/data-editor.en.md:37`, `events.en.md:39`) dicono che un evento automatico si può cancellare e che
  il provider lo rimette; il menu della riga lo cancella già, e il backend lo elimina se non è collegato. Le righe
  `readonly` sono solo gli eventi automatici (`AssetDataEditorSection.svelte:162`). Domanda al coordinatore (needs_input,
  03:12): chiudere senza codice, o decisione di prodotto per saltarli nel bulk (con riga, tooltip e guida).
  - ✅ **Decisione del coordinatore** (15/10 ~03:20): «chiudila senza codice, come reperto non confermato. […] Vale la
    regola del developer per i reperti del piano 20: “verifiche prima, e la correzione solo dei reperti confermati”. S3
    era finita nel backlog per triage, non per una sua decisione di prodotto.» La chiusura nel README del 38 la segna il
    coordinatore all'ingresso di K1; S4 e il resto di I-10 restano per E1; il developer può ribaltarla.
  - **Prove**:
    - tooltip `dataEditor.autoEvent.tooltip` (`frontend/src/lib/i18n/base/en.json:171`): «Deleting is also temporary —
      the provider will recreate the event on next sync»;
    - guida: `mkdocs_src/docs/user/assets/detail/data-editor.en.md:37` («You can delete one, but the provider adds it
      back at its next sync») e `mkdocs_src/docs/user/assets/detail/events.en.md:39` (nello stesso senso);
    - menu ⋮ della riga: l'azione `delete` di `DataEditor.svelte:384-389` è visibile su ogni riga non cancellata,
      `readonly` comprese, e la cancella;
    - backend: `delete_events_bulk` (`backend/app/api/v1/assets.py:1067`, `services/assets/price_store.py:954`)
      elimina anche gli eventi automatici, e blocca solo quelli collegati a transazioni (`in_use`);
    - le righe `readonly` del DataEditor sono solo gli eventi automatici (`AssetDataEditorSection.svelte:162`,
      `readonly: ev.is_auto === true`; nessun altro chiamante imposta `readonly` su una riga).

**Passi**:

1. ✅ **Agganci di test** (03:11): `data-testid="tx-form-balance-issues"` (ul) e `tx-form-balance-issue` (li) sulla lista
   del saldo del form, nei due banner. Nessun effetto sul comportamento, nessuna classe.
2. ✅ **Rossi** (03:12–03:35; test-author `k1-reds`, solo test e registro del runner), tutti rossi per il difetto con le
   premesse verdi:
   - **O-12** `front-utility core-unit "O-12"`: file nuovo `frontend/src/lib/i18n/importWizardAssetsCount.test.ts`
     (registrato in `core-unit`, `_frontend_utility.py`); 5 rossi: per en/it/fr/es n=1 è il testo di n=2 col 2 cambiato
     in 1 («1 unique assets, 7 need resolution», «1 asset unici, …»), e l'inglese esatto riceve «1 unique assets, 1 need
     resolution»;
   - **P-15 / W-B8** in `DataEditor.test.ts` (aiuti della lingua-segnaposto portati a livello di modulo, invariati):
     i contatori leggono «2 modified», «1 deleted», «3 new»; la levetta «Hide/Show 2 stale rows»; `DataImportModal`
     `{help: 'Help', close: 'Close'}`; le cinque chiavi `dataEditor.*` mancano nei 4 cataloghi;
   - **C-89** in `TransactionFormModal.test.ts`: la chiave non esiste e l'elemento manca, con i due selettori di data del
     pannello abbinato presenti; il TRANSFER (controllo) è verde;
   - **V-38 a schermo** `front-transaction transactions-modals "V-38"` (`transactions-modals.spec.ts`, utente e broker
     propri, `allow_cash_overdraft: false`): `tx-form-balance-issue` 0 invece di 1, `tx-form-issue` 1 invece di 0; il
     server risponde `[{operation: 'create', index: 0, code: 'balanceCashNegative'}]`. Schermata
     `/tmp/libreFolio_w_k1_V38_form_after_validation.png`: la riga della cassa negativa sta sotto «With the other
     pending changes, this row causes the following issues», senza il titolo del saldo. Visto a schermo: la cura è
     quella del bulk.
   - Log: `/tmp/libreFolio_w_k1_component_unit.log`, `/tmp/libreFolio_w_k1_V38_run.log` e gli altri `/tmp/libreFolio_w_k1_*`.
3. ✅ **Cure** (03:37–03:38), con gli script `/tmp/libreFolio_w_k1_{i18n.sh,code.py,docs.py}`:
   - **O-12**: `dev.py i18n update importWizard.assetsCount`, ICU plurale su `n` in 4 lingue e su `m` in inglese
     («1 needs resolution»); il componente non cambia.
   - **P-15 / W-B8**: `dev.py i18n add` di `dataEditor.counter.{edited,deleted,appended}` (maschile, come
     `dataEditor.status.*` e `common.selected`) e `dataEditor.stale{Show,Hide}` (righe, come `dataEditor.staleTooltip`),
     tutte con il valore `n` e il plurale dove la lingua accorda; in `DataEditor.svelte` i contatori e l'`aria-label`
     della levetta leggono le chiavi (classi invariate); in `DataImportModal.svelte` gli `aria-label` diventano
     `csvImport.helpTitle` e `common.close`, con i `data-testid` `data-import-modal-help` e `data-import-modal-close`
     per non legare i test al testo.
   - **V-38**: `fieldIssues` = indice ≥ 0 e non di saldo, `balanceIssues` = indice < 0 o di saldo
     (`isBulkBalanceIssue`, lo stesso del bulk); la divisione serve solo a mostrare.
   - **C-89**: `transactions.form.fxDatesHint` in 4 lingue; `<p class="mt-2 text-xs text-lf-muted"
     data-testid="tx-form-fx-dates-hint">` sotto il pannello «Da»/«A» solo per `pairLayout === 'fx'`, nessuna classe di
     palette (T-1); in `user/transactions/form.{en,it,fr,es}.md` la stessa frase dopo «Each side has its own date…»,
     scritta da me nelle 4 lingue; `translate-stamp --file user/transactions/form.en.md` (la pagina era già allineata,
     «Already stamped» nel `--dry-run` di prima: lo stamp non nasconde debito; cambia solo la voce della pagina in
     `mkdocs_src/aphra-pipeline/.translate-hashes.json`, 8 righe).
4. ✅ **Verdi** (03:38–03:52), uno alla volta nella corsia:
   - `dev.py i18n check` stretto verde (4 366 chiavi); `i18n audit`: nessuna chiave morta né traduzione mancante, le
     chiavi nuove risultano usate;
   - `front-utility core-unit` 131 file, 4 250 test (+1 file, +5: O-12; cancelli `themeRoles`, `themeTokens` e
     `catalogIcuLocale` verdi); `front-utility component-unit` 118 file, 3 168 test (+6: P-15 e C-89);
     `front-transaction tx-unit` 887;
   - E2E: `front-transaction transactions-modals` 25 (V-38 compreso), sul bundle di debug ricostruito alle 03:42 dopo le
     cure (verificato: contiene `tx-form-fx-dates-hint` e `dataEditor.counter.edited`); `front-asset asset-data-editor`
     26, `front-fx fx-csv-import` 21, `front-fx fx-editor` 4;
   - `utils gate-i18n-catalog` 176, `gate-i18n-usage` 195, `gate-plugin-i18n-ownership` 45;
   - svelte-check (binario locale) 0 errori e 0 avvisi; Prettier pulito su 19 file frontend (sorgenti i18n comprese);
     ruff e black puliti su `_frontend_utility.py`;
   - `mkdocs build` stretto verde, `check-links` 95 validi, `translate-diff --issues-only` 642/642 puliti.
   - **`all-backend` non eseguito**: K1 non tocca codice backend; i cancelli che leggono il catalogo sono verdi. Da fare
     sulla revisione combinata, se il coordinatore la chiede.

   > **⚠️ Fuori pista**: `fx-csv-import.spec.ts:247` e `:276` (di X) prendono la ✕ della modale d'importazione per
   > `aria-label="Close"`. Con P-15 l'etichetta è tradotta: verdi in inglese, dove girano gli E2E; il `data-testid`
   > `data-import-modal-close` è pronto per sostituirlo (W-B13). Nota per T: `asset-data-editor.spec.ts:384` cerca il
   > contatore delle righe vecchie per classe (`span.text-amber-600, span.text-amber-400`), che la conversione dei colori
   > di `DataEditor` cambierà.
5. ✅ Piano, backlog (W-B13), CHANGELOG proposto, handoff FROZEN (03:55).

### Passaggio degli eventi da X (X CP2b, `92b42d796`, record `05c21b2b6`) — per E1

Comunicato dal coordinatore il 15/10 ~03:55; arriva nella mia base all'aggiornamento del checkpoint di K1.

- **Moduli che diventano di W**: `backend/app/api/v1/assets/events.py` (`event_router`: `upsert_events_bulk`,
  `delete_events_bulk`, `query_events_bulk`, `get_events_by_ids`); `backend/app/services/assets/event_store.py`
  (`EventStoreOperations`, 9 metodi, e `_EventKey`); `backend/app/schemas/assets/events.py` (11 classi, da
  `FAAssetEventPoint` a `FAEventQueryResponse`); test `test_api/test_assets_events.py` e
  `test_api/test_events_target_currency.py` interi, e in `test_services/test_asset_source_upsert_guards.py` (misto) i
  blocchi della valuta di destinazione (righe 411-490) e della modifica sul posto (782-925).
- **Contratti da tenere**: `refresh.py:557` (gli eventi dei fornitori passano da
  `EventStoreOperations._upsert_asset_events`); la composizione dei mixin in `services/assets/manager.py:20`;
  `PRICE_UPSERT_CHUNK_SIZE` importato da `price_store.py`; `FAAssetEventPoint`/`Out` dentro `schemas/prices.py:33`,
  prodotti dai plugin yahoo, justetf e scheduled_investment.
- **Righe sugli eventi che restano di X** (accordo attraverso il coordinatore): `services/assets/provider_management.py`
  17, 74-76, **164-204** (cancellazione simmetrica degli eventi di un fornitore parametrico, che scollega le transazioni:
  W-B2/C-65a), 228-236; `AssetDataEditorSection.svelte` 2-7, 24, 27, 42-43, 86-100, 106, 108, 110, 114, 147-176,
  196-215, 222, 266-267, **349-438** (il salvataggio), 475, 484-501, 524-528, 535-545, 557-564; `EventDataImportModal.svelte`
  intero; `AssetModal.svelte` 276, 1478-1486, 1503-1510, 1549-1553, 2434; `price_query.py:280-300,614`;
  `currency_change.py:86-135`; `crud.py:506-517` e `689-800` (il merge che migra gli eventi). C-65a (la modale al cambio di
  fornitore) chiede W e X insieme.

### Revisione combinata `1d1c7e67d` (K1 + A3, H CP3, X CP2b) ✅ (2026-10-15) — 🧊 FROZEN

K1 committato dal coordinatore come `532a1fd9c` (codice) e `05e738d18` (journal); base aggiornata col merge `1d1c7e67d`
di `dev_release2` a `05c21b2b6` (A3: frontend di Settings e login, cataloghi `auth`; H CP3; X CP2b: asset tagliati,
`api/v1/assets/` per risorsa, API identica). Unione automatica, worktree pulito. Validazione mirata richiesta entro le
08:20, senza `all-backend` (il backend lo copre la run di J sulla stessa combinazione).

1. ✅ **Base** (03:53): HEAD `1d1c7e67d` (genitori `05e738d18`, `05c21b2b6`), pulito, porta 6184 libera.
2. ✅ **`front build --debug`** (03:53–03:55, 83 s): verde, svelte-check 0 errori e 0 avvisi.
3. ✅ **`i18n check`** stretto verde, 4 371 chiavi; **`theme-roles.mjs --check`**: «Colour gates: clean»;
   **`check-orphans`**: 118 E2E, 367 Vitest e 269 file backend raggiungibili da un `all`.
4. ✅ **Vitest**: `front-utility core-unit` 132 file, 4 266 test; `front-utility component-unit` 119 file, 3 198 test;
   `front-transaction tx-unit` 887. Sono i conteggi attesi (A3 più K1).
5. ✅ **E2E** (03:57–04:03, sulla build delle 03:55, «Frontend build is up to date»): `front-transaction
   transactions-modals` 25, `front-asset asset-data-editor` 26 (sulle rotte degli eventi spostate da X), `front-fx
   fx-csv-import` 21, `front-fx fx-editor` 4.
6. ✅ **`mkdocs build`** stretto verde; `git diff --check` pulito; porta 6184 libera (04:04).

   > **Note implementazione (coordinatore, 15/10 ~04:06)**: K1 in `dev_release2` con l'avanzamento veloce a `d915c869f`;
   > record in `0229dbc6a` (CHANGELOG con le 4 righe; chiuse O-12, C-89, V-38, W-B8 e la parte W di P-15; I-10 S3 chiusa
   > senza codice nel README del 38; W-B13 spostata nella sezione X). Il mio ramo è avanzato a `0229dbc6a`, pulito.
   > `ui/data-editor` ora è di T (avvisato, con la nota su `asset-data-editor.spec.ts:384`).

### W4 — CP6–CP7, PL5: `services/brim/` ⏳ (2026-10-15) — CP6 🧊 checkpoint inviato, FROZEN

**Via del coordinatore** (15/10 ~04:06): «Via per W4 (`services/brim/`, PL5: rinomina, poi taglio con la guardia;
aggiorna le due costanti del cancello `gate-event-loop-io`; `applyTo`, skill, guida U-B8). W3 (`api/v1/brokers/`) e
W5–W6 (`uploads.py`) aspettano un commit del coordinatore su quei file, e git non segue il codice spostato. Se W4 finisce prima, passa a K2 o W7. Le run pesanti di W4 vanno chiuse prima delle
08:45, o fatte dopo l'avviso di fine della finestra della galleria.» Base: HEAD `0229dbc6a`, pulito, porta libera (04:06).

**Forma** (piano 43, P2.1; §6 del piano generale, C1 e «Regole di ogni lotto di riordino»): `brim_provider.py` è
rinominato **e** tagliato, quindi due checkpoint in fila.

- **CP6, rinomina**: `brim_provider.py`, `brim_report_sets.py`, `brim_parse_pool.py`, `brim_gap_fix.py` →
  `services/brim/`, stessi nomi (C1), accanto al `registry.py` di X; riferimenti di app, test, runner, script,
  `coverage_analysis` (prefisso del pacchetto, come per transazioni e broker), doc per sviluppatori, `.github` (`applyTo`
  `backend/app/services/brim/**`, skill `brim-plugin`), devWiki (C6), commenti di `frontend/src/lib/utils/brim/`; le due
  costanti del cancello `gate-event-loop-io`; U-B8 (il passo «Capacity table» della guida). Nessun cambio di
  comportamento; JSON di `api schema` identici.
  - Eccezione: la docstring dell'enum `IdentifierType` (`backend/app/db/models.py:127`) cita
    `backend/app/services/brim_provider.py` ed è pubblicata nell'OpenAPI; resta com'è per tenere lo schema identico,
    come X ha lasciato `asset_source.py` nella stessa docstring. Residuo nel backlog.
- **CP7, taglio**: `services/brim/brim_provider.py` per tema (piano 43: contratto, file e lock, report set, parsing,
  candidati, duplicati; moduli nuovi con nomi brevi, C1), con lo stato di modulo (`_BROKER_LOCKS`) in un modulo solo, le
  patch dei test sul modulo che definisce, e la guardia contro le patch mute (C4).

**Passi CP6**:

1. ✅ **Spostamento e riscrittura** (04:08–04:10): `mv` (non `git mv`: lo stage è del coordinatore) di
   `brim_provider.py`, `brim_report_sets.py`, `brim_parse_pool.py`, `brim_gap_fix.py` in `backend/app/services/brim/`;
   `/tmp/libreFolio_w4a_rename.py --apply`: 96 file, 146 riferimenti (forme puntata, con le barre, e `from
   backend.app.services import <moduli BRIM>`; nessuna riga d'import mescolava moduli BRIM e altri). Lo scarto fra il
   `grep` dei vecchi percorsi e la prova a secco era la sola `models.py`, esclusa apposta.

   > **⚠️ Fuori pista**: la regola dell'import non vede le sorgenti scritte dentro le stringhe (`\n` letterale dopo
   > l'import) né una docstring spezzata su due righe: nel cancello `gate-event-loop-io` 5 casi di controllo e la
   > docstring sono rimasti sulla forma vecchia, e i controlli sarebbero caduti (il modulo legato non era più quello
   > sorvegliato). Corretti a mano, con la forma relativa `from ...services.brim import brim_provider` e la costante
   > `BRIM_PROVIDER` (percorso per componenti).
2. ✅ **A mano**: `scripts/coverage_analysis.py` col prefisso di pacchetto `backend/app/services/brim/` (HIGH) e
   `services/brim/` fra i servizi del nucleo, come transazioni e broker (non tocca `brim_providers/`);
   `.github/instructions/backend-providers-brim.instructions.md`, `applyTo` →
   `backend/app/services/brim_providers/**,backend/app/services/brim/**`; la skill `brim-plugin` dice ora da dove vengono
   `BRIMProvider` e `BRIMProviderRegistry` (`services/brim/`: contratto in `brim_provider.py`, registro in
   `registry.py`; il contratto andrà in `base.py` col taglio); **U-B8**: tolto il passo 3 «Capacity table» della guida
   (`brim_plugin_guide.md`, la tabella «Importer Capabilities» non c'è più) e rinumerati i passi seguenti (3 Nav,
   4 Validate, 5 Developer providers overview); nessun altro riferimento a quella tabella in `mkdocs_src/docs`.
3. ✅ **Prove a secco e statiche** (04:10–04:16):
   - vecchi percorsi: 0 in `backend/` (salvo la docstring esclusa di `models.py:127`), `scripts/`, `dev.py`, `.github/`,
     `mkdocs_src/docs/developer/`, devWiki, `frontend/src/lib/utils/brim/`; `check_source_paths.py` 5, come prima;
   - import: `backend.app.main` e i 4 moduli si importano; il registro BRIM scopre 33 plugin;
   - patch dei test (`/tmp/libreFolio_merge_patch_guard.py backend.app.services.brim`): 7 siti, tutti efficaci;
   - somiglianza col file di base: `brim_provider.py` 100 % (nessuna riga cambiata), `brim_report_sets.py` 99,56 %,
     `brim_parse_pool.py` 99,31 %, `brim_gap_fix.py` 99,15 %;
   - `ruff check --select I --fix` sui 64 file Python toccati (46 blocchi d'import riordinati: il percorso nuovo cambia
     l'ordine, soprattutto nei plugin), poi `ruff` pulito; `black` invariato (la sola `coverage_analysis.py`, già fra i 29
     file sporchi della base); `lint --dead-code` senza reperti nuovi (i due di `brim_provider.py` col percorso nuovo; il
     resto delle differenze da I1 viene dagli spostamenti di X e H);
   - **`api schema` identico** a quello di `0229dbc6a` (OpenAPI e contratti dei Tool; riferimento esportato da un albero
     `git archive` in `/tmp/libreFolio_w_ref_0229/`).
4. ✅ **Selettori del dominio** (04:12–04:13): `services brim-provider-base` 37, `brim-parse-pool` 8, `brim-report-sets`
   259, `brim-gap-fix` 99; `utils gate-event-loop-io` 14, `gate-plugin-layout` 33, `gate-plugin-i18n-ownership` 45.
5. ✅ **`all-backend`** (04:13–04:27, `--workers 2`; log `/tmp/libreFolio_w4a_all_backend.log`, unità in
   `/tmp/libreFolio_w4a_testlog/`): **7/7 verdi, 13 749 passed, 28 skipped, 0 failed**. Non ho una run completa della
   base `0229dbc6a` (il coordinatore la fa coprire dalla run di J su `1d1c7e67d`, stesso codice): i conteggi li provo con
   la raccolta, file per file, dei 17 file di test toccati dalla rinomina, uguali alla base (1 876 test da tutte e due le
   parti, `pytest --collect-only` nell'albero `git archive 0229dbc6a` e nel worktree). La raccolta intera dell'albero di
   base non si fa in `/tmp`: alcuni test leggono file fuori da `backend/` e `scripts/` (doc, workflow).
6. ✅ **Doc**: `mkdocs build` stretto verde, `check-links` 95 validi; `git diff --check` pulito; porta 6184 libera
   (04:30). Prettier pulito sui due commenti di `frontend/src/lib/utils/brim/`.

   > **Note implementazione**: CP6 pronto il 15/10 alle 04:30: rinomina pura, schema identico, stessi test.
   >
   > **Disegno di CP7 (taglio)**, dalla mappa AST (`/tmp/libreFolio_w4b_map.txt`) e dai chiamanti
   > (`/tmp/libreFolio_w4b_callers.txt`). Con C1 e C4 (la classe resta nel suo file col suo nome),
   > `services/brim/brim_provider.py` tiene il contratto: `BRIMProvider`, `BRIMParseError`, `BRIMSetRequiredError`,
   > `TEXT_ENCODINGS`. Così i 38 plugin non cambiano. Escono per tema:
   > - `storage.py`: cartella e firma, lock e stato `_BROKER_LOCKS*`, sidecar, salvataggio, elenco, lettura, spostamenti,
   >   cancellazioni, `_update_metadata`, `_iter_metadata_paths`, `_unlink_report_set_references`;
   > - `combined_files.py`: i file combinati dei report set (`write_combined_csv`, `save_combined_file`,
   >   `find_reusable_combined`, `read_combine_summary`, `_members_key`). Nome breve diverso da `brim_report_sets.py`,
   >   per non avere due moduli «report_sets»;
   > - `parsing.py`: `parse_file`, `check_file_with_plugin`, `_check_path`, `_refusal_message`, `_relocated_path`;
   > - `candidates.py`: la ricerca degli asset, singola e in blocco;
   > - `duplicates.py`: `detect_tx_duplicates`.
   >
   > Dipendenze in un solo verso (storage ← combined_files, parsing; nessun ciclo). Le patch dei test
   > (`get_broker_reports_dir`, `detection_signature`) vanno su `storage`, e solo `storage` chiama
   > `get_broker_reports_dir` direttamente. Il cancello `gate-event-loop-io` sorveglia i moduli sincroni (storage,
   > combined_files, parsing).
   >
   > Volume: circa 18 righe in `api/v1/brokers.py`, 8 in `brim_report_sets.py`, 1 in `auth.py`, 1–2 in
   > `brim_parse_pool.py`, circa 150 riferimenti nei test.

### Revisione combinata `370189b3d` (W4 CP6 + H `web_link_finder`, J CP-1) ✅ (2026-10-15) — 🧊 FROZEN

CP6 committato dal coordinatore come `548a0688d` (98 file; git abbina le 4 rinomine al 98–100 %; il suo controllo AST:
56 file con soli import, negli altri 8 cambiano solo stringhe di percorso) e `7066176cf` (journal); base aggiornata col
merge `370189b3d` di `dev_release2` a `209e4a6f0`. Sul fuso il coordinatore ha già verificato: 0 import irrisolti, 0
patch mute (`patch_effect.py` di J), nessun percorso nuovo nelle guardie D-J18. Controllo leggero chiesto, senza
`all-backend`. **CP7 aspetta un commit del coordinatore su `brokers.py`** (lo stesso che aspetta W3): dopo l'ingresso
di CP6 si passa a **W7**, poi K2.

1. ✅ **Base** (04:34): HEAD `370189b3d` (genitori `7066176cf`, `209e4a6f0`), pulito, porta libera.
2. ✅ **`services config-package`**: 567 passed. Il conteggio è quello di `209e4a6f0`: 481 casi, uno per modulo di
   `backend/app` fuori da `config/`, più 86 test fissi. La rinomina sposta 4 moduli senza aggiungerne né toglierne; cambiano
   solo i 4 id dei parametri, da `services/brim_<x>.py` a `services/brim/brim_<x>.py`. I 6 id sotto `services/brim/` sono i
   miei 4 più `__init__.py` e `registry.py` di X.
3. ✅ `utils gate-event-loop-io` 14, `services brim-provider-base` 37.
4. ✅ **`pytest --collect-only`** contro `209e4a6f0` (albero `git archive` di `backend`, `scripts`, `pyproject.toml`,
   `dev.py` e `pytest.ini` in `/tmp/libreFolio_w_ref_209e/`): **13 881 test da tutte e due le parti, identici file per
   file (270 file)**.

   > **⚠️ Fuori pista**: senza `pytest.ini` l'albero estratto stampa la raccolta in un altro formato, e senza `dev.py`
   > `test_dev_port_check.py` non si raccoglie. Con i due file la raccolta è completa.
5. ✅ **`api schema`** contro `209e4a6f0`: OpenAPI e contratti dei Tool identici.
6. ✅ `git diff --check` pulito; porta 6184 libera (04:37).

   > **⚠️ Fuori pista (segnalato dal coordinatore)**: la riscrittura di CP6 ha cambiato anche un riferimento storico. La
   > docstring di `backend/test_scripts/test_services/test_brim_report_sets.py` dice `git show
   > v1.1.0:backend/app/services/brim/brim_provider.py`, ma nella v1.1.0 il file stava in `services/brim_provider.py`.
   > Lo correggo nel prossimo lotto (W7). Scansione delle righe aggiunte da `548a0688d` con un percorso nuovo accanto a
   > un'ancora storica (`git show`, versioni, SHA): è l'unico caso. L'altro riscontro, `architecture.md`, parla del
   > commit del database, non di git.

   > **Note implementazione (coordinatore, 15/10 ~04:38)**: CP6 in `dev_release2` con l'avanzamento veloce a `155d9b050`;
   > record in `0902524e5`; il mio ramo è avanzato lì, pulito.

### W7 — schemi delle transazioni come pacchetto (C3) ⏳ (2026-10-15) — W7a 🧊 checkpoint inviato, FROZEN

**Via del coordinatore** (15/10 ~04:38): «Via per W7 (schemi delle transazioni come pacchetto, C3), con la docstring di
`test_brim_report_sets.py`; poi K2. `schemas/transactions.py` è importato da altre sessioni: nell'handoff elenca gli
importatori fuori dal tuo dominio. Dalle ~08:45, al mio avviso, niente `all-backend` né build pesanti fino all'avviso di
fine.» Base: HEAD `0902524e5`, pulito, porta libera (04:38).

**Forma** (C3 e il precedente di X, `schemas/assets/`): `backend/app/schemas/transactions.py` (1 371 righe) diventa il
pacchetto `backend/app/schemas/transactions/`, con un `__init__.py` di sola docstring (nessun barile), il modulo
`transactions.py` per il nucleo (validatori, create, read, update con i gruppi di scambio, query, delete) e i moduli per
tema tagliati da lì: `batch.py` (batch unificato, codici e problemi di validazione, voci split/promote del batch),
`event_suggest.py`, `promotion.py` (promozione dei trasferimenti e promote-suggest), `type_metadata.py` (metadati dei tipi).
L'hub `schemas/__init__.py` resta e continua a esportare i nomi pubblici, dai moduli che li definiscono. Il nucleo è
circa il 48 % del file, sulla soglia di somiglianza di git: per non avere un file insieme rinominato e tagliato, **due
checkpoint**:

- **W7a, rinomina**: `schemas/transactions.py` → `schemas/transactions/transactions.py`, il pacchetto col suo
  `__init__.py`, l'hub (riga della docstring, import sotto `TYPE_CHECKING`, chiave `"transactions.transactions"` di
  `_EXPORT_GROUPS`, come `"assets.assets"`), gli importatori, la doc, la devWiki; in più la docstring storica di
  `test_brim_report_sets.py` (`git show v1.1.0:backend/app/services/brim_provider.py`).
- **W7b, taglio**: i moduli per tema, con la prova AST dei corpi alla lettera, gli importatori sul modulo che definisce e
  l'hub per modulo.

**Importatori**: tutti di W nell'app (48 file: router delle transazioni, servizi delle transazioni, BRIM, i 33 plugin,
`schemas/brim.py`, l'hub); nessuno passa dall'hub per i nomi TX; nei test 16 importazioni dirette in 13 file, tutte su
BRIM, transazioni e broker, salvo `test_schemas/test_schema_computed_fields.py` (comune ai domini degli schemi).

**Passi W7a**:

1. ✅ **Rinomina** (04:40): `mv` di `backend/app/schemas/transactions.py` in `backend/app/schemas/transactions/transactions.py`
   (somiglianza 100 %, nessuna riga cambiata); `backend/app/schemas/transactions/__init__.py` di sola docstring (elenco dei
   moduli, come `schemas/assets/__init__.py`); `/tmp/libreFolio_w7a_rename.py --apply`: 87 file, 99 riferimenti (forma
   puntata, idempotente, e percorso con le barre); l'hub `schemas/__init__.py` con la riga della docstring
   (`transactions/: … transactions.py (…)`), l'import sotto `TYPE_CHECKING` e la chiave `"transactions.transactions"`;
   la docstring storica di `test_brim_report_sets.py` torna a `git show v1.1.0:backend/app/services/brim_provider.py`.
   - Fuori dal mio dominio, una sola riga: il commento di `backend/app/services/files/static_uploads.py:65` (di H), che
     cita il percorso di `EVENT_COMPATIBLE_TYPES`.
2. ✅ **Prove statiche** (04:41–04:45):
   - `backend.app.main` si importa; l'hub esporta ancora i nomi TX in modo pigro (`from backend.app.schemas import
     TXCreateItem` è la classe del modulo nuovo); vecchi percorsi: 0 in `backend/`, `scripts/`, `dev.py`, `.github/`,
     `mkdocs_src/docs/developer/`, devWiki e `frontend/src/`; `check_source_paths.py` 5, come prima;
   - `ruff --select I --fix` senza cambi (il percorso nuovo non sposta l'ordine), `ruff` e `black` puliti sui 65 file Python
     toccati; `lint --dead-code` senza reperti nuovi (l'unica differenza da CP6 è lo spostamento di J,
     `pac_allocator/source/portfolio_allocation_source.py`); guardia delle patch su `backend.app.schemas.transactions`:
     0 siti;
   - **`api schema` identico** a `0902524e5` (OpenAPI e contratti dei Tool, riferimento da un albero `git archive` in
     `/tmp/libreFolio_w_ref_0902/`);
   - **`pytest --collect-only`** contro `0902524e5`: identico file per file su 270 file, salvo `test_config_package.py`
     567 → 568: la guardia ha un caso per modulo di `backend/app`, e il pacchetto aggiunge il suo `__init__.py` (l'id
     `schemas/transactions.py` diventa `schemas/transactions/__init__.py` e `schemas/transactions/transactions.py`).
3. ✅ **Selettori** (04:42–04:45): `schemas transactions` 75, `services config-package` 568, `services brim-report-sets` 259,
   `api transactions` 26, `utils gate-plugin-layout` 33.
4. ✅ **`all-backend`** (04:45–05:00, `--workers 2`; unità in `/tmp/libreFolio_w7a_testlog/`): **7/7 verdi, 13 871 passed,
   28 skipped, 0 failed**. Rispetto alla run di CP6 cambia solo quello che porta la base (`web_link_finder` di H, CP-1 di
   J) più il caso nuovo di `config-package`; la run conta 17 test in più della raccolta (unità ripetute), come in CP6.
   `mkdocs build` stretto verde, `check-links` 95; `git diff --check` pulito; porta libera (05:01).

   > **Note implementazione**: W7a pronto il 15/10 alle 05:01: rinomina pura, schema identico, raccolta identica salvo
   > il caso del nuovo `__init__.py`.

   > **Note implementazione (coordinatore, 15/10 ~05:03)**: W7a committato come `00a19bf72` (`R100` più l'`__init__`
   > nuovo; 59 file con soli import, negli altri 5 solo hub, docstring e una stampa) e `f71a77e03` (journal). Via per W7b
   > sopra W7a, **senza aggiornare la base adesso** (X CP3 e A4 chiudono le loro run sulla base `0902524e5`): W7a entra
   > insieme a W7b, in due commit separati; al checkpoint di W7b il coordinatore aggiorna la base e io valido una volta
   > sola la revisione combinata, con `all-backend`.

**Passi W7b** (taglio), sopra `f71a77e03`:

1. ✅ **Taglio** (05:05, `/tmp/libreFolio_w7b_cut.py`): ogni nodo di primo livello si porta dietro i commenti e i banner
   che lo precedono; i moduli nuovi hanno una docstring, il blocco d'import originale (poi `ruff --select F401,I --fix`: 64
   import inutili tolti) e gli import fra moduli; `black`.
   - `transactions.py` (661 righe) tiene 12 nodi: `EVENT_COMPATIBLE_TYPES`, `validate_tags_list`, `tags_to_csv`,
     `validate_transaction_business_rules`, `TXCreateItem`, `TXReadItem`, `SWAP_GROUPS`, `get_swap_group`,
     `_swap_group_codes`, `TXUpdateItem`, `TXQueryParams`, `TXDeleteItem`;
   - `batch.py` (192): il commento degli stati con `TXItemStatus` e `TXBatchOperation`, `TXDeleteResult`, `TXMixedBatch`,
     `TXBatchResultItem`, `TXBatchResponse`, `TXValidationCode`, `TXValidationCodeInfo`, `VALIDATION_CODE_METADATA`,
     `TXValidationIssue`, `TXSplitBatchItem`, `TXPromoteBatchItem`;
   - `event_suggest.py` (55): le tre classi di `POST /transactions/events/suggest`;
   - `promotion.py` (96): `TXTransferPromoteRequest`/`Response`, `TXPromoteSuggestInput`/`Candidate`/`Response`;
   - `type_metadata.py` (429): da `SignType` a `EVENT_TYPE_METADATA`, con `_swap_group_codes` dal nucleo e i codici di
     validazione da `batch`.
   - Dipendenze in un solo verso (`transactions` ← `batch` ← `type_metadata`; `event_suggest` e `promotion` da soli).
2. ✅ **Prova alla lettera** (`/tmp/libreFolio_w7b_verbatim.py`): 46 nodi di primo livello, 46 identici al testo
   originale (`ast.get_source_segment`), nessuno perso né in più.
3. ✅ **Importatori** (`/tmp/libreFolio_w7b_importers.py`): 12 file riscritti sul modulo che definisce ogni nome;
   a mano l'import con `# noqa: PLC0415` di `test_transaction_schemas.py` e l'hub, cioè l'import sotto `TYPE_CHECKING`
   e `_EXPORT_GROUPS` per modulo (`transactions.batch`, `transactions.transactions`, `transactions.type_metadata`), coi
   due commenti dell'elenco; docstring dell'hub e del pacchetto. I file altrui (`test_schema_computed_fields.py`, il
   commento di H in `static_uploads.py`) non cambiano: importano o citano solo nomi del nucleo.
4. ✅ **Doc**: 8 righe della devWiki (tabelle «Source files» e un elenco: F-097, F-046, `batch-only-split-promote`,
   `unified-batch-pipeline`, `server-driven-type-rules`, `static-metadata-export`, `promote-respects-asset-event-link`,
   `phase07-part4-round5-server-type-rules`) e il commento di `transactionTypeStore.test.ts` sul modulo che definisce;
   `check_source_paths.py` 5.
5. ✅ **Prove** (05:06–05:12):
   - `backend.app.main` si importa; i 21 nomi TX dell'hub vengono dal modulo che li definisce; gli schemi di
     `TXBatchResponse` e `TXTypesResponse` si generano; `TX_TYPE_METADATA` ha 12 tipi; nessun import da riscrivere;
   - `ruff` e `black` puliti sui 19 file Python toccati; codice morto uguale a W7a; guardia delle patch: 0 siti;
   - **`api schema` identico** a `0902524e5` (OpenAPI e contratti dei Tool);
   - **`pytest --collect-only`**: 13 886 test, identici a `0902524e5` file per file, salvo `test_config_package.py` 567 →
     572 (un caso per modulo: il `__init__.py` di W7a più i 4 moduli nuovi);
   - corsia: `schemas transactions` 75, `services config-package` 572, `services transaction` 66, `api transactions` 26,
     `transactions-validate` 11, `events-suggest` 9, `batch-split-promote` 35, `transfer-promotion` 3,
     `transactions-wac` 20, `tx-balance-walk` 9.
   - `all-backend` sulla revisione combinata, dopo l'aggiornamento della base del coordinatore.

   > **Note implementazione (coordinatore, 15/10 ~05:13)**: W7b committato come `e28aad42f` (28 file: 4 nuovi, 24
   > modificati; il suo controllo AST: 59/59 nomi identici fra il nucleo di prima e i 5 moduli) e `b60e91d83` (journal).

### Revisione combinata `304e6d176` (W7a + W7b + A4) ✅ (2026-10-15) — 🧊 FROZEN

Base aggiornata dal coordinatore col merge `304e6d176` di `dev_release2` a `be2ad6573` (A4: migrazione 005,
`account_tokens`, colonne nuove di `users`, `token_service`); merge pulito, senza file fusi in automatico. Sul fuso il
coordinatore ha verificato 0 import irrisolti e 0 patch mute. X CP3 è ancora in validazione: se entra prima di W7, un
secondo aggiornamento con un controllo leggero (cambi e schemi delle transazioni sono domini separati).

1. ✅ **Base** (05:17): HEAD `304e6d176` (genitori `b60e91d83`, `be2ad6573`), pulito, porta libera.
2. ✅ **Build**: `front build --debug` verde (svelte-check 0 errori, 0 avvisi); `mkdocs build` stretto verde (05:19).
3. ✅ **`api schema` contro `be2ad6573`** (albero `git archive` in `/tmp/libreFolio_w_ref_be2a/`): OpenAPI e contratti dei
   Tool identici.
4. ✅ **`pytest --collect-only` contro `be2ad6573`**: 13 971 → 13 976; identico su 272 file salvo `test_config_package.py`
   568 → 573, un caso per ciascuno dei 5 moduli nuovi del pacchetto (gli id `schemas/transactions.py` →
   `schemas/transactions/{__init__,batch,event_suggest,promotion,transactions,type_metadata}.py`).
5. ✅ **`all-backend`** (05:19–05:32, `--workers 2`; unità in `/tmp/libreFolio_w7m_testlog/`): **7/7 verdi, 13 965 passed,
   28 skipped, 0 failed**; la run conta 17 test in più della raccolta (le unità ripetute), come nelle run precedenti.
6. ✅ `git diff --check` pulito; porta 6184 libera (05:33).

   > **Preparazione di K2** (solo lettura, appunti fuori dal repo): la parte (a), i codici dei rifiuti di DEGIRO e del
   > Generic CSV, e L6 non toccano `brokers.py` né `uploads.py`; le parti (b), il 400 strutturato del parse, e (c), il
   > codice `preview_unreadable_workbook`, passano da `brokers.py:1010-1013`, `:717-719` e `uploads.py:292-295`, i file
   > che aspettano il commit del coordinatore. Proposta: K2a ora, K2b dopo quel commit.

   > **Note implementazione (coordinatore, 15/10 ~05:34)**: piano committato come `2afede53a`; X CP3 entrato alle 05:30
   > (cambi tagliati in `services/fx/` e `api/v1/fx/`, API identica). Ultimo aggiornamento di base: merge `f0b1ab58b` di
   > `dev_release2` a `5d21f2d85`, pulito. K2: divisione approvata (K2a subito dopo l'ingresso di W7; K2b dopo il commit
   > del coordinatore su `brokers.py` e `uploads.py`; per `file_preview.py` accordo con H attraverso il coordinatore).

### Controllo leggero di `f0b1ab58b` (W7 + X CP3) ✅ (2026-10-15) — 🧊 FROZEN

1. ✅ **Base** (05:34): HEAD `f0b1ab58b` (genitori `2afede53a`, `5d21f2d85`), pulito, porta libera.
2. ✅ **`api schema` contro `5d21f2d85`**: OpenAPI e contratti dei Tool identici.
3. ✅ **`pytest --collect-only` contro `5d21f2d85`**: 13 976 → 13 981; identico su 272 file salvo `test_config_package.py`
   573 → 578 (i 5 moduli nuovi del pacchetto, come nelle prove precedenti).
4. ✅ **`services config-package`**: 578 passed = 492 casi per modulo di `backend/app` fuori da `config/` (487 a
   `5d21f2d85`, più i 5 del pacchetto: 6 id sotto `schemas/transactions/` al posto di `schemas/transactions.py`) e 86
   test fissi. Porta libera.

   > **Note implementazione (coordinatore, 15/10 ~05:36)**: W7a e W7b in `dev_release2` con l'avanzamento veloce a
   > `1cd7300f3`; record in `58be885a9` (nessuna riga nel CHANGELOG: è un riordino); il mio ramo è avanzato lì, pulito.

### K2a — C-70 (a) e L6: i rifiuti dei plugin DEGIRO e Generic CSV, tradotti ✅ (2026-10-15) — 🧊 FROZEN

**Via del coordinatore** (15/10 ~05:36): «Via per K2a, con un checkpoint FROZEN. Le run pesanti vanno chiuse entro le
08:45, oppure dopo l'avviso di fine della finestra della galleria.» Divisione approvata alle 05:34: K2a ora; K2b (il 400
strutturato del parse e `preview_unreadable_workbook`) dopo il commit del coordinatore su `brokers.py` e `uploads.py`; per
`file_preview.py` accordo con H attraverso il coordinatore (D-W17). Base: HEAD `58be885a9`, pulito, porta libera (05:36).

**Disegno** (verificato sul codice di `58be885a9`):

- Il canale c'è: `BRIMRefusal(code, message, context)` (`schemas/brim.py:292`), da `BRIMProvider.cannot_parse_detail`;
  il frontend (`utils/brim/defaultPluginCheck.ts:86`, `resolveParseRefusalMessage`) traduce
  `importWizard.parseRefusal.<code>` coi parametri di `context` (`plugin_code` → `plugin_name`), e senza traduzione
  mostra la frase inglese. Oggi lo usano solo i due plugin Scalable (`_scalable.py:210-236`), con 4 chiavi condivise in
  `frontend/src/lib/i18n/importWizard/`.
- **Codici** (in `importWizard.parseRefusal`, il vocabolario condiviso del sottosistema di W, come quelli di Scalable;
  nessun cambio di codice nel frontend): generici `csv_only` (con `plugin_code`), `file_unreadable`, `no_header_row`,
  `missing_columns` (con `columns` e `count`, plurale ICU), `no_movement_rows`; di DEGIRO `degiro_csv_only` e
  `degiro_not_account_statement`.
- **Backend**: come chiede la guida (e come fa Scalable), Generic CSV (`broker_generic_csv/plugin.py:356-375`) e DEGIRO
  (`broker_degiro/plugin.py:669-685`, `_inspect`) costruiscono il `BRIMRefusal` una volta; `cannot_parse_reason`
  restituisce il suo `message`, identico a oggi (i testi inglesi sono fissati dai test di contratto,
  `test_brim_providers.py:906-913`).
- **L6**: il rifiuto del parse (`_refusal_message`, `services/brim/brim_provider.py:1183-1199`) dice oggi `Plugin
  '<codice>' cannot parse file '<nome salvato uuid>'`; nomina invece il plugin col suo `provider_name` e il file col nome
  originale (`get_file_info(file_id).filename`, `parse_file` ha il `file_id`). Il 400 resta inglese fino a K2b.
- **Dove stanno le chiavi**: nel sottosistema `importWizard`, non nel frammento del plugin come suggerisce la voce C-70.
  È la regola scritta (`mkdocs_src/docs/developer/backend/brim/architecture.md:312`: le parole del wizard per avvisi e
  rifiuti «belongs to no plugin»), e il cancello lo impone: R1 di `gate-plugin-i18n-ownership` vuole nel frammento di un
  plugin BRIM solo chiavi `brimPlugins.<code>.*`. Precedente: `importWizard.brimNotice.corporate_action`, del solo Generic
  CSV (`importWizard/en.json:195`). Cinque codici su sette sono vocabolario condiviso; i due `degiro_*` seguono Scalable.

**Passi**:

1. ✅ **Rossi** (test-author, 15/10 05:37–06:00; nessun file nuovo, runner invariato, ruff/black/prettier/svelte-check
   puliti). Preambolo `… --test-port 6184 --data-dir /tmp/librefolio-r13-w`:
   - Generic CSV, `external brim-providers TestGenericCSVRefusesWithACode TestPluginSaysWhyWithACode
     TestGenericCSVSaysWhyItRefuses`: **17 rossi**, 60 verdi. Oggi `(None, msg, {})` invece di
     `('csv_only', msg, {'plugin_code': 'broker_generic_csv'})`; sul corpus «58 of 86 answers miss the code of their
     cause».
   - DEGIRO, `external brim-degiro TestRefusalCodes TestRecognition`: **16 rossi**, 53 verdi (41 di `TestRecognition`);
     «78 of 92».
   - Frontend, `front-transaction tx-unit`: **16 rossi**, 887 verdi. Le 7 chiavi mancano in en/it/fr/es; gli altri
     mostrano la frase inglese di ripiego (una sentinella la distingue dalla traduzione); `csv_only` deve nominare il
     plugin in 4 lingue (anche DEGIRO, dal suo codice); `missing_columns` deve cambiare fra 1 e 2 oltre la cifra.
   - L6, `services brim-provider-base test_the_parse_refusal_names_the_plugin_and_the_file_as_uploaded`: **2 rossi**
     (`my_statement.txt`, `my_statement.csv`): oggi `Plugin 'broker_generic_csv' cannot parse file '300adede-….csv'`.
   - Ritoccato per tenerne l'intento: `TestPluginSaysWhyWithACode::test_the_default_wraps_the_reason_without_a_code`
     chiama `BRIMProvider.cannot_parse_detail(plugin, path)`, il default della base, perché il Generic CSV ora lo
     ridefinisce.

   > **⚠️ Fuori pista**: test-author segnala tre siti che fissano il difetto, fuori dai suoi file:
   > `test_brim_api.py` RS-G05 (`:2047`, il vecchio prefisso) e RS-PC03 (`:2650`, `code: null` del Generic CSV), e
   > `test_brim_parse_race.py:205-351` (6 test, 8 casi, sul nome salvato). I sostituti di plugin di quel file non
   > hanno `provider_name`: da qui il ripiego sul codice nella cura. Dopo K2a nessun plugin reale rifiuta senza
   > codice, e un test API non può piantare un sostituto nel server: RS-PC03 passa al rifiuto con codice del Generic
   > CSV, e il percorso senza codice resta coperto dal contratto e da Vitest. Ritocco affidato a test-author prima
   > della cura, per vederne il rosso.

   > **Note implementazione (ritocco dei siti che fissavano il difetto, 06:00–06:14)**: test-author, prima della cura.
   > `test_brim_parse_race.py` (+33 −17): `_plain_refusal(plugin_name, info)` costruisce il testo dal nome del plugin e
   > da `info.filename`; `_RefusingPlugin.provider_name = "Refusing stand-in"`; il ripiego sul codice di un plugin
   > senza `provider_name` è fissato una volta, in `test_a_plugin_without_the_method_keeps_the_plain_refusal`.
   > `test_brim_api.py` (+30 −19): RS-G05 confronta il `detail` intero (`Plugin 'Generic CSV' cannot parse file
   > 'no_date_….csv': required column 'date' …`) e l'`error_message` del file `failed`; RS-PC03 rinominato
   > `test_the_generic_csv_refuses_a_csv_without_date_with_its_code_and_context`, con `GENERIC_REFUSAL` = `missing_columns`,
   > `{"columns": "date", "count": 1}`; RS-PC07 (accesso) confronta codice del plugin, `can_parse` e messaggio inglese,
   > uguali prima e dopo (il rifiuto intero lo fissa RS-PC03): scelta accettata. Docstring di
   > `test_brim_providers.py:971` aggiornata. Rossi: `services brim-parse-race` **8 rossi**, 34 verdi (oggi
   > `Plugin 'broker_generic_csv' cannot parse file '<uuid>.csv'`); `api brim TestParseRefusalReason
   > TestPluginCheckEndpoint` **2 rossi** (RS-G05, RS-PC03 con `code: None`), 7 verdi. Nessuno su una premessa.
   > Il vecchio nome di RS-PC03 non è citato da altri file tracciati.

2. ✅ **Cure** (06:03–06:15).
   - Chiavi aggiunte (06:03) con `/tmp/libreFolio_w_k2a_i18n.sh`: 7 chiavi × 4 lingue in
     `frontend/src/lib/i18n/importWizard/{en,it,fr,es}.json` (+8 −1 righe ciascuno).
   - Backend (06:15) con `/tmp/libreFolio_w_k2a_backend.py` (8 sostituzioni, ognuna verificata unica prima a secco):
     - `broker_generic_csv/plugin.py`: `cannot_parse_detail` costruisce il `BRIMRefusal` (`csv_only` con
       `{"plugin_code": self.provider_code}`, `file_unreadable`, `no_header_row`, `missing_columns` con
       `{"columns": ", ".join(missing), "count": len(missing)}`); `cannot_parse_reason` ne restituisce il `message`,
       identico a prima.
     - `broker_degiro/plugin.py`: `_inspect` restituisce `(layout, Optional[BRIMRefusal])` (`degiro_csv_only`,
       `file_unreadable`, `no_movement_rows`, `degiro_not_account_statement`); `cannot_parse_detail` e
       `cannot_parse_reason` ne derivano. `_inspect` non ha altri chiamanti.
     - `services/brim/brim_provider.py`: `_refusal_message(plugin, plugin_code, file_name, checked_path)` nomina
       `getattr(plugin, "provider_name", None) or plugin_code`; `parse_file` passa `get_file_info(file_id).filename`,
       e il nome salvato solo se i metadati mancano.
     - `ruff check --select I --fix`, `ruff check`, `black --check` puliti sui 3 file.
3. ✅ Verdi, guida per sviluppatori, piano, CHANGELOG proposto, handoff FROZEN (06:36).
   - Guide aggiornate: `brim_plugin_guide.md` (frase del 400 a `:66` e «What the user reads», tabella del Generic CSV
     con codice e contesto, «Shared codes», esempio DEGIRO, dove stanno le traduzioni), `generic_csv.md:213-217`,
     `import-wizard.md:196-203`; devWiki `concepts/brim-texts-translated-by-code.md` (riga dei rifiuti).
     `mkdocs build` stretto verde (06:07, 0 avvisi), `mkdocs check-links` 95 validi.
   - Verdi, una invocazione alla volta (06:15–06:19):
     - `services brim-parse-race` 42 passed; `services brim-provider-base` 39 passed; `utils gate-event-loop-io` 14;
     - `external brim-providers` 733 passed, 1 skipped; `external brim-degiro` 197; `external brim-scalable` 151;
     - `api brim TestParseRefusalReason TestPluginCheckEndpoint` 9 passed;
     - `front-transaction tx-unit` 22 file, **903** passed (887 + 16);
     - `utils gate-i18n-catalog` 176, `gate-i18n-usage` 195, `gate-plugin-i18n-ownership` 45; `i18n check` stretto
       (4 378 chiavi); `i18n audit`: 0 inutilizzate, le 7 chiavi nuove «used» (i 4 «not verified» sono di prima);
     - `front-utility core-unit` 132 file, 4 266 passed (con `catalogIcuLocale.test.ts`);
     - `api schema` contro `58be885a9` (albero `git archive` in `/tmp/libreFolio_w_ref_58be/`): OpenAPI e contratti
       dei Tool identici.
     - `pytest --collect-only` contro `58be885a9`: 13 981 → **14 038** (+57): `test_brim_degiro.py` 169 → 197,
       `test_brim_providers.py` 707 → 734, `test_brim_provider_base.py` 37 → 39; identico sugli altri 269 file.
     - **`all-backend`** (06:19–06:31, `--workers 2`; unità in `/tmp/libreFolio_w_k2a_testlog/`): **7/7 verdi, 14 027
       passed, 28 skipped, 0 failed**; 14 027 + 28 = 14 038 + 17 (le unità ripetute), come nelle run precedenti.
     - `front build --debug` (06:32–06:34): svelte-check 0 errori, 0 avvisi.
     - E2E `front-transaction tx-import-broker-mismatch` 5 passed (il prompt del broker sbagliato, dove compare il
       rifiuto tradotto; i casi sono di Scalable) e `tx-import-degiro` 4 passed (06:34–06:35).
     - `git diff --check` pulito; porta 6184 libera (06:35).

   > **Note implementazione (coordinatore, 15/10 ~06:35)**: (1) W-B15 nella sezione W (`c81670354`):
   > `tx-bulk-operations.spec.ts:428` prende la chiusura per testo; nella stessa famiglia X-R9 chiede due `data-testid`
   > in `DataImportModal.svelte` (componente di W): il `ConfirmModal` di `:305` e il pulsante Annulla di `:287`, per
   > `fx-csv-import.spec.ts:250,261` (X li userà col FE4). Vanno nel primo lotto di W che tocca già quel file. (2)
   > `.github/instructions/backend-schemas.instructions.md`: l'albero aveva ancora `transactions.py`; sistemato in K2a
   > col pacchetto `schemas/transactions/` e i suoi 5 moduli. Restano fuori dal mio dominio, e li segnalo al
   > coordinatore: `assets.py` (ora `schemas/assets/`, di X) e i moduli assenti dall'albero (`ai_export_runtime`,
   > `pac_allocator/`, `portfolio`, `risk`, `risk_scenarios`, `signals`, `system`, `tools`, `wac`).

   > **CHANGELOG proposto** (`[Unreleased]`, al coordinatore): «🔄 Changed — Import wizard: when a broker's default
   > plugin, DEGIRO or the Generic CSV, cannot read an uploaded file, the wrong-broker prompt gives the reason in your
   > language: not a CSV, unreadable, no header row, missing `date`/`type` columns, no movement rows, not a DEGIRO Account
   > Statement.» e «🐛 Fixed — A parse that a plugin refuses names the plugin and the file as you know them (for example
   > «Generic CSV» and «export.csv»), not the plugin code and the stored file id.» Il 400 del parse resta in inglese
   > fino a K2b.

   ✅ **K2a completato** (06:36) — 🧊 FROZEN in attesa del checkpoint del coordinatore.

   > **Note implementazione (coordinatore, 15/10 ~06:38)**: K2a committato come `0eac8e1b6` (`fix(brim): coded
   > DEGIRO/Generic CSV refusals`, 18 file) e `4cb9fa5bf` (journal). Aggiornamento di base: merge `388a20f65` di
   > `dev_release2` a `786f3e216` (J C-93, H CP4 col router di sistema e l'area degli avvisi nel layout, J G-8, X CP4
   > con gli schemi degli asset per tema); `backend-schemas.instructions.md` fuso da solo, con `assets/` e
   > `transactions/`. X-R9 e W-B15 nel lotto E1; le altre righe superate di quel file restano al coordinatore, per una
   > passata unica a fine riordino.

### Controllo leggero di `388a20f65` (K2a + J C-93, H CP4, J G-8, X CP4) ✅ (2026-10-15) — 🧊 FROZEN

1. ✅ **Base** (06:38): HEAD `388a20f65` (genitori `4cb9fa5bf`, `786f3e216`), pulito, porta libera. Il merge non tocca
   nessun file di K2a salvo `backend-schemas.instructions.md`, con i due pacchetti presenti.
2. ✅ **Frontend**: `front build --debug` (06:38–06:40) con svelte-check 0 errori, 0 avvisi; `i18n check` stretto
   (4 392 chiavi, 18 sottosistemi); Vitest `tx-unit` 22 file, 903 passed; `core-unit` 134 file, 4 290 passed (le 2
   file in più sono i test di `features/instance/` di H CP4, registrati in `_frontend_utility.py`).
3. ✅ **E2E** col layout nuovo di H: `tx-import-broker-mismatch` 5 passed, `tx-import-degiro` 4 passed (06:41–06:43).
4. ✅ **Contro `786f3e216`** (albero `git archive` in `/tmp/libreFolio_w_ref_786f/`): `api schema` con OpenAPI e
   contratti dei Tool identici; `pytest --collect-only` 14 014 → 14 071 (+57: `test_brim_degiro.py` +28,
   `test_brim_providers.py` +27, `test_brim_provider_base.py` +2), identico sugli altri 269 file.
5. ✅ **Selettori di K2a** sul fuso (06:44–06:45): `services brim-parse-race` 42, `brim-provider-base` 39;
   `external brim-providers` 733 (1 skipped), `brim-degiro` 197; `api brim TestParseRefusalReason
   TestPluginCheckEndpoint` 9. `git diff --check` pulito; porta 6184 libera.

### Analisi di E1 (eventi) e via per E0 ✅ (2026-10-15)

> **Note implementazione (coordinatore, 15/10 ~06:46)**: K2a in `dev_release2` con l'avanzamento veloce a `62c964242`;
> record `e7cf1ae80` (CHANGELOG con le due righe; chiuse C-70 parte a e L6; C-95 nuova, l'albero delle istruzioni). Il
> mio ramo è avanzato lì, pulito.

**Analisi di E1, in sola lettura** (06:46–06:55, su `e7cf1ae80`; appunti fuori dal repo). In sintesi:

- I-09 confermata: `FAAssetEventPoint.type` è un `str` senza controllo (`schemas/assets/events.py:49`), la colonna è
  l'enum `AssetEventType` (`db/models.py:983`); i plugin di X emettono solo tipi maiuscoli, quindi un validatore sul punto
  condiviso non li rompe e l'OpenAPI non cambia.
- I-12 confermata: `DELETE /assets/events?ids=` non è limitato all'asset (`api/v1/assets/events.py:76-98`,
  `services/assets/event_store.py:471-537`); l'upsert fa un commit per elemento e, nel ramo senza id, uno per blocco di
  chiavi (`_upsert_asset_events`, condiviso col refresh dei fornitori, `refresh.py:557`).
- V-22 confermata, con una correzione alla premessa della decisione 20: senza id si toccano solo gli eventi **manuali**
  della stessa data e dello stesso tipo (`event_store.py:84-93`); l'evento del fornitore entra in gioco con S4.
- I-10 S4 confermata (`EventCreateMiniModal.svelte:135-152`); il resto di I-10 confermato nel salvataggio dell'editor,
  righe di X (`AssetDataEditorSection.svelte:349-438`, `:461-466`).
- I-11: (a) e (d) confermate; (b) in parte già chiusa; (c) tocca i numeri (il salvataggio mette la valuta dell'asset su
  ogni evento, `AssetDataEditorSection.svelte:365-378`); l'export degli eventi non porta gli id (`api/v1/backup.py:277-330`).

> **Note implementazione (coordinatore, 15/10 ~06:55)**: (1) decisioni 20–23 aggiornate nel file delle decisioni
> (`ee5d81a6f`), con la premessa corretta del 20, l'export senza id, la proposta precisata («Usa questo», «Crea
> comunque», «Annulla») e le strade A e B del 23; il developer non ha ancora risposto, E1a ed E1b aspettano. (2)
> Migrazione di E1a: la **008** (C7: 005 e 006 ad A, 007 a X); `down_revision` sulla testa trovata all'aggiornamento di
> base; se entro prima della 006 o della 007, il primo numero libero, da riallineare all'aggiornamento. (3) Le righe di X
> in `AssetDataEditorSection.svelte` le scrivo io in E1b, sul mio contratto. (4) **Via per E0**, che non dipende dalle
> decisioni: X-R9, W-B15, I-11a, I-11d; in `ui/data-editor` solo logica, niente classi né markup; E0 entra dopo la
> chiusura della finestra della galleria (build ed E2E prima delle 08:45 o dopo l'avviso di fine). (5) W-B16 (I-11b,
> `source`) nella mia sezione del backlog, con la proposta. Alle ~06:58: via anche per la riga di X in
> `EventDataImportModal.svelte` (`matchKey: true` sulla colonna `type`), da segnalare nell'handoff come file di X.

### E0 — X-R9, W-B15, I-11a, I-11d ✅ (2026-10-15) — 🧊 FROZEN

**Disegno** (verificato sul codice di `e7cf1ae80`):

- **I-11a** — `CsvEditor.svelte:416-437` scarta come doppioni tutte le righe con la stessa data, qualunque sia il tipo:
  un dividendo e uno split dello stesso giorno non entrano (la guida lo dice come limite, `data-editor.en.md:70`). Cura:
  un flag `matchKey?: boolean` in `CsvColumnDef` (mio); due righe sono doppioni solo con la stessa data (o identità) e gli
  stessi valori delle colonne marcate. `EventDataImportModal.svelte:38` (file di X, riga concessa) marca `type`. Prezzi,
  cambi e distribuzioni non marcano nulla: restano come oggi (anche la colonna `currency` dei prezzi è una stringa
  obbligatoria, quindi una regola implicita sbaglierebbe).
- **I-11d** — il selettore della data di una riga nuova disabilita tutti i giorni che hanno una riga
  (`DataEditor.svelte:141`, `:160-170`). Cura: con `importMatchKeys` (gli eventi passano `['type']`) disabilita solo i
  giorni delle altre righe con gli stessi valori di quelle chiavi; senza chiavi, come oggi. Solo logica.
- **X-R9** — `DataImportModal.svelte:287` (Annulla, senza testid) → `data-testid="data-import-cancel"`; `:305`
  (`ConfirmModal`, prop `testId` già esistente) → `testId="data-import-discard-confirm"`. Le userà X in
  `fx-csv-import.spec.ts:250,261` (FE4).
- **W-B15** — il pulsante Annulla di `TransactionPickerModal.svelte:180-186` ha **già** `data-testid="tx-picker-cancel"`:
  resta da usarlo in `tx-bulk-operations.spec.ts:428` al posto del testo (e chiudere il picker senza condizioni). Nessun
  difetto di prodotto, quindi nessun rosso di prodotto.
- **Guida**: `data-editor.en.md:70` («One event per date») passa a «one event per date and type», nelle 4 lingue, poi
  `translate-stamp`.

**Passi**:

1. ✅ **Rossi** (test-author, 07:00–07:22; nessun file nuovo, runner invariato, prettier pulito). `DataEditor.test.ts`
   +296 −17 (blocchi I-11d a `:680`, I-11a a `:839`, X-R9 a `:1296`; `eventImportModal()`/`importedRows()` spostati,
   invariati, a livello di modulo; `parsedCsv` con un terzo argomento facoltativo); `tx-bulk-operations.spec.ts` +4 −5.
   Preambolo `… --test-port 6184 --data-dir /tmp/librefolio-r13-w`:
   - `front-utility component-unit`: **9 rossi**, 3 216 verdi (3 225). X-R9: `data-import-cancel` non trovato (2) e
     `data-import-discard-confirm` assente sulla conferma (1); I-11a: dividendo e split dello stesso giorno danno
     `data-valid-rows="0"` (1), e a livello di `CsvEditor` con una colonna `matchKey` tutte e due le righe finiscono nei
     doppioni (3); I-11d: il giorno di un evento d'altro tipo è disabilitato (1) e lo spostamento non arriva al padre (1).
   - 7 guardie verdi: stessa data e stesso tipo restano doppioni; nei prezzi la `currency` diversa resta un doppione;
     senza `importMatchKeys` il selettore e lo spostamento restano come oggi; il giorno di un evento dello stesso tipo
     resta rifiutato.
   - `front-transaction tx-bulk-operations` col nuovo selettore: 10 passed (W-B15 non ha un difetto di prodotto).
   - `svelte-check`: 3 errori attesi (`matchKey` sconosciuto nei test) fino alla cura; il selettore reale del calendario
     gira in jsdom, senza `vi.mock`.
2. ✅ **Cure** (07:22, `/tmp/libreFolio_w_e0_fix.py`, 7 sostituzioni verificate prima a secco):
   - `CsvEditor.svelte`: `CsvColumnDef.matchKey?: boolean`; i doppioni si cercano sulla data (o l'identità) più i valori
     delle colonne `matchKey`; il messaggio dice `Duplicate date · type: <data> · <tipo>`.
   - `EventDataImportModal.svelte:38` (**file di X**, riga concessa): `matchKey: true` sulla colonna `type`.
   - `DataEditor.svelte`: `takenDates(row)` sostituisce il `$derived` `existingDates`; vale per il selettore e per
     `handleDateChange`.
   - `DataImportModal.svelte`: `data-testid="data-import-cancel"` e `testId="data-import-discard-confirm"`.
   - Solo logica e due attributi di test: nessuna classe né struttura cambiata (`ui/data-editor` è anche di T).
3. ✅ **Verdi, guida, W-B16** (07:22–07:32):
   - `prettier --check` sui 6 file toccati: pulito.
   - `front-utility component-unit`: 120 file, **3 225 passed**.
   - `front build --debug`: svelte-check 0 errori, 0 avvisi.
   - E2E: `front-asset asset-data-editor` 26, `front-fx fx-csv-import` 21, `front-fx fx-editor` 4,
     `front-transaction tx-bulk-operations` 10 (07:27–07:31).
   - Guida utente `data-editor.{en,it,fr,es}.md:70`: «One event per date and type» (ES «desdoblamiento», come il resto
     della pagina); `translate-stamp` sulla pagina (solo le sue voci in `.translate-hashes.json`); `translate-validate`
     non ha errori su `data-editor` (i 69 sono di altre pagine). Pagina per sviluppatori
     `frontend/components/core-ui/data-editor.md`: selettore della data, `matchKey`, il modale degli eventi, la tabella
     dei messaggi. `mkdocs build` stretto con 0 avvisi; `check-links` 95 validi.
   - W-B16 (I-11b, `source`) nella mia sezione del backlog, con la proposta.
   - `git diff --check` pulito; porta 6184 libera.

   ✅ **E0 completato** (07:33) — 🧊 FROZEN; entra dopo la chiusura della finestra della galleria.

   > **Note implementazione (coordinatore, 15/10 ~07:34)**: E0 committato come `692fbae39` (`fix(data-editor): events
   > keyed by date and type`, 12 file) e `f901eb6fb` (journal). Aggiornamento di base: merge `2bf015afa` di
   > `dev_release2` a `c3047aa17` (J C-93, H CP4, J G-8, X CP4, A4b, X J-5, H CP5a, la versione fissata nelle gallerie),
   > pulito; `.translate-hashes.json` fuso come testo. E0 entra dopo la finestra della galleria; le chiusure di I-11a,
   > I-11d, X-R9 e W-B15 e la riga del CHANGELOG le scrive il coordinatore.

### Revisione combinata `2bf015afa` (E0 + A4b, X J-5, H CP5a…) ✅ (2026-10-15) — 🧊 FROZEN

1. ✅ **Base** (07:35): HEAD `2bf015afa` (genitori `f901eb6fb`, `c3047aa17`), pulito, porta libera;
   `.translate-hashes.json` si legge (251 voci) e tiene l'md5 di `data-editor.en.md` timbrato in E0. Dei file di E0 il
   merge tocca solo il backlog e `.translate-hashes.json`, con righe aggiunte.
2. ✅ **`front build --debug`** (07:35–07:36, client rifatto per l'API di H CP5a): svelte-check 0 errori, 0 avvisi.
3. ✅ **Vitest**: `front-utility core-unit` 134 file, 4 290 passed (con `themeRoles.gate.test.ts`, la guardia dei
   colori di T: E0 non aggiunge classi); `component-unit` 120 file, 3 225 passed (07:36–07:39).
4. ✅ **E2E** (07:39–07:44): `front-asset asset-data-editor` 26, `front-fx fx-csv-import` 21, `front-fx fx-editor` 4,
   `front-transaction tx-bulk-operations` 10.
5. ✅ **Doc**: `mkdocs build` stretto con 0 avvisi; `check-links` 95 validi. `git diff --check` pulito; porta 6184 libera
   (07:44).
