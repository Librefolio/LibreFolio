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

   > **Note implementazione (coordinatore, 15/10 ~07:45–07:51)**: E0 validato e committato (`2326624c1`), poi entrato
   > in `dev_release2` con `d226bc69e` alle 07:51, prima della finestra, su richiesta del coordinatore colori. **Via per
   > FE8a** (annuncio nel §7 del piano generale, `2c699f85c`). Dal coordinatore colori: nessun loro annuncio aperto sui
   > tre file; T li converte nell'ondata W4, sui pezzi già tagliati; conteggi da ripartire: `ImportWizardModal` m1 595
   > più il letterale `#dc2626`, `TransactionBulkModal` 190, `TransactionFormModal` 218; comando `theme-roles.mjs --split
   > <vecchio>:<nuovi>`, poi `--check`; il `#dc2626` in uno dei pezzi, classi nuove solo sui ruoli `lf-*`. Regole: solo
   > tagli, niente `transactions/import/`, niente spostamento della cartella; la baseline del cricchetto nello stesso
   > commit del taglio; W-B11 si chiude qui. Dalle 09:00, per circa 2 ore, la finestra della galleria: solo codice.

### FE8a — i tagli delle tre modali ⏳ (2026-10-15)

**Analisi** (07:45–07:50, su `2326624c1`):

- Il peso sta negli script (righe di script / template): Form 1 378 / 790, Bulk 3 143 / 460, Wizard 4 414 / ~1 500.
  Quasi tutte le funzioni chiudono sullo stato del componente (nel Form 2 pure su 39, script
  `/tmp/libreFolio_w_fe8/purity.mjs`): accorciare gli script vorrebbe lo stato in una classe `.svelte.ts`, come
  `features/tools/pac-allocator/planner/draft.svelte.ts`, cioè un ridisegno.
- **Disegno, approvato dal coordinatore (07:51)**: si taglia il **template** per sezione (Form, Bulk) o per passo
  (Wizard) in componenti figli con props esplicite; `bind:` solo dove il template già scriveva lo stato; stato, `$effect`
  e handler restano nel padre; i tipi condivisi in un `.ts`. Il ridisegno dello stato non rientra nella 1.3. Cartelle
  `components/transactions/form/`, `bulk/`, `wizard/` (`wizard/` confluisce in `import/` con FE8b). Tre
  sotto-checkpoint, ognuno FROZEN e validato a parte; ogni taglio chiude con `--split` e `--check`. Dopo la finestra
  entrano prima R e L dei colori, poi i lotti della 1.3.
- **Strumenti** (fuori dal repo, `/tmp/libreFolio_w_fe8/`): `refs.mjs` legge l'AST di Svelte e dà, per un intervallo di
  righe del template, i nomi dello script che usa (con chi è scritto: `bind:`, assegnazione), i componenti, le direttive
  `use:` e gli store `$x`, e le righe d'import ridotte a quei nomi; `gen_form.py` genera i figli (import, `Props` con un
  tipo per ogni nome, markup copiato alla lettera) e sostituisce le sezioni nel padre con la chiamata. svelte-check
  verifica tutto il cablaggio.

#### FE8a-1 — il Form ✅ (2026-10-15) — 🧊 FROZEN

1. ✅ **Taglio** (07:52): `TransactionFormModal.svelte` 2 275 → 1 616 righe; in `components/transactions/form/`:
   `TxFormBanners.svelte` (righe 1464-1542 del padre, 12 props, legati `commitFailed`, `formError`, `issuesDismissed`),
   `TxFormPairSection.svelte` (1548-1817, 46 props, legati `costBasisMode`, `createAssetOpen`, `createBrokerOpen`,
   `draft`), `TxFormSingleSection.svelte` (1823-2035, 40 props, gli stessi legati), `TxFormOptionalSection.svelte`
   (2066-2131, 8 props, legati `createEventOpen`, `draft`, `optionalOpen`); `txFormTypes.ts` con `ValidationIssue`,
   `FormDraft`, `DualDraftTo` (spostati dal padre) e `TxFormWacResult` (il tipo che il padre scriveva due volte in
   linea). Restano nel padre header, footer, piè di pagina in sola lettura, il blocco del costo di un TRANSFER e le
   modali impilate. Il DOM non cambia (un componente non aggiunge elementi); gli stili del padre sono tutti `:global`.
2. ✅ **Cricchetto**: `theme-roles.mjs --split` del Form nei quattro pezzi; m1 218 = 35 (padre) + 6 + 96 + 56 + 25; riga
   `~split` nella baseline; `--check` pulito.
3. ✅ **Prove** (07:52–08:12, corsia 6184): `prettier --write` sui file toccati; `svelte-check` 0 errori, 0 avvisi su
   5 667 file; Vitest `tx-unit` 903, `core-unit` 4 290 (con le guardie dell'HTML e dei colori), `component-unit` 3 225
   (con `TransactionFormModal.test.ts`, i cui `vi.mock` sono su moduli condivisi); E2E `front-transaction all
   --workers 4` (07:56–08:06; avviso al coordinatore): 46/46 azioni verdi, 337 + 34 (mobile) passed, 32 skipped del
   progetto mobile; fuori dalle transazioni `front-broker detail` 37, `front-utility onboarding-tour` 10,
   `front-utility tooltip` 9. Doc: `features/transaction-form.md` (i quattro componenti; `FormDraft` in
   `txFormTypes.ts`); devWiki `problems/browser-autofill-numeric-fields.md` (la riga del Form punta anche ai pezzi; le
   altre righe che citano la modale restano vere, la logica è nel padre); `check_source_paths.py` invariato (5 path di
   prima); `mkdocs build` stretto con 0 avvisi; `check-links` verde.

   > **Note implementazione (coordinatore, 15/10 ~08:18)**: FE8a-1 committato come `8a62cea7f` (`refactor(tx-form): cut
   > form modal by section`, 9 file; baseline 218 = 35 + 6 + 96 + 56 + 25, `--check` pulito anche dal coordinatore) e
   > `04a3b2691` (journal). Orari dal coordinatore colori: dalle 08:45 alle ~10:15 `dev_release2` è fermo (gallerie r1 e
   > r2); dalle 08:45 alla fine della finestra (~12:30) niente run pesanti nella corsia (E2E delle transazioni, build).
   > FE8a-1 entra dopo la finestra, dopo R e L, con il controllo leggero sul fuso.

#### FE8a-2 — il Bulk ✅ (2026-10-15) — 🧊 FROZEN

1. ✅ **Taglio** (08:18, `/tmp/libreFolio_w_fe8/gen_cut.py`, la versione generica di `gen_form.py`, con
   `bulk_cfg.py`): `TransactionBulkModal.svelte` 3 760 → 3 332 righe; in `components/transactions/bulk/`:
   `TxBulkBanners.svelte` (righe 3194-3454 del padre: errori, problemi di validazione, cose da sistemare, proposte di
   unione; 36 props, legati `commitFailed`, `formError`, `issuesDismissed`, `promoteAllOpen`, `promoteBannerSeen`,
   `todoBlockersExpanded`, `todoWarningsExpanded`), `TxBulkToolbar.svelte` (3462-3566: cerca e aggiungi, filtro dei
   giorni, selezione e azioni; 17 props, legati `bulkTableSelectedRows`, `importWizardOpen`, `maxDeltaDays`);
   `txBulkTypes.ts` con `DraftFields`, `PendingOp`, `WacResultEntry`, `SuggestEntry`, spostati alla lettera dal padre.
   **W-B11 chiusa**: `brokerName()` (`:1597`) non aveva chiamanti ed è tolta. Header, tabella, footer e modali
   impilate restano nel padre; restano anche le funzioni pure (i renderer delle celle), fuori dal disegno approvato.

   > **⚠️ Fuori pista**: la prima prova ha dato 2 rossi in `core-unit` e 3 in `component-unit`.
   > (1) `htmlSink.gate.test.ts`: la voce rivista di `formatCurrencyCodeHtml(…)` (`REVIEWED_SINKS`, `:69`) puntava a
   > `TransactionBulkModal.svelte`; ora il `{@html}` sta in `TxBulkBanners.svelte`, e la voce segue il codice (stesso
   > motivo, `CURRENCY_HTML`). (2) `ImportWizardModal.test.ts`, «Import success-only handoff»: `tx-bulk-import` non
   > c'era. La sezione della barra cominciava **dentro** il commento HTML di più righe che la precede: nel padre il
   > `<!--` restava aperto e inghiottiva la chiamata `<TxBulkToolbar/>` fino al `-->` successivo, e il figlio cominciava
   > con il resto del commento. svelte-check non lo vede (è markup valido). Cura: il commento torna intero nel padre, la
   > riga spuria esce dal figlio; il generatore ora rifiuta una sezione che comincia dentro un commento o che apre o chiude
   > un commento che non contiene. Le sezioni del Form (FE8a-1) erano giuste: il loro commento era tutto dentro, e
   > `front-transaction all` lo aveva provato.
2. ✅ **Cricchetto**: `--split` del Bulk nei due pezzi; m1 190 = 88 (padre) + 54 + 48; riga `~split`; `--check`
   pulito.
3. ✅ **Prove** (08:19–08:43, corsia 6184): svelte-check 0 errori, 0 avvisi su 5 670 file; Vitest `tx-unit` 903,
   `core-unit` 4 290, `component-unit` 3 225; `ImportWizardModal.test.ts` 26/26; E2E `front-transaction all --workers 4`
   (08:29–08:39, avviso al coordinatore): 46/46 azioni verdi, 337 + 34 (mobile) passed, 32 skipped del progetto mobile;
   fuori dalle transazioni `front-utility onboarding-tour` 10 (l'àncora `transaction.bulk.add_import` è ora nella
   barra) e `front-broker detail` 37. Doc: `developer/frontend/state/transaction-draft.md` (dove sono dichiarati
   `PendingOp` e `DraftFields`; i due componenti). devWiki: `concepts/import-todo-signals.md` e
   `decisions/transfer-pair-same-asset-opposite-quantity.md` (le righe che descrivono i banner e la barra puntano anche
   ai pezzi); `check_source_paths.py` invariato. `mkdocs build` stretto con 0 avvisi; `check-links` verde (08:43,
   prima della finestra).

   > **Note implementazione (coordinatore, 15/10 ~08:45)**: FE8a-2 committato come `464350cc7` (`refactor(tx-bulk): cut
   > bulk modal banners, toolbar`, 9 file; 190 = 88 + 54 + 48, `--check` pulito anche dal coordinatore) e `ba9819ec0`
   > (journal, W-B11 chiusa). Via per il Wizard, solo codice. svelte-check concesso durante la finestra: al massimo 3
   > volte, una alla volta, con `nice -n 15`, niente Vitest, E2E né build; le righe-sonda fuori dal commit.

#### FE8a-3 — il Wizard ⏳ (2026-10-15) — codice scritto, prove dopo la finestra

1. ✅ **Tipi** (08:45–08:51): dei 123 nomi del padre usati dai cinque passi grandi, 93 hanno un tipo scritto nella
   dichiarazione (generico di `$state`/`$derived`, annotazione, letterale, parametri tipati, `void` per le funzioni
   senza `return` di un valore; `/tmp/libreFolio_w_fe8/autotypes.mjs`); i 30 `$derived` inferiti li ha stampati
   svelte-check, con righe-sonda temporanee (`const __p_x: __Probe = x;`) e `noErrorTruncation` acceso solo per quella
   corsa (svelte-check 1/3, 08:47); padre e `tsconfig.json` rimessi com'erano subito dopo. Lo stesso per i 12 della barra
   in fondo (svelte-check 2/3, 08:50, insieme al primo controllo dei pezzi).
2. ✅ **Taglio** (08:49–08:52, `gen_cut.py`): `ImportWizardModal.svelte` 5 984 → 5 053 righe; in
   `components/transactions/wizard/`: `UploadStep.svelte` (20 props), `SelectFilesStep.svelte` (32), `AnalyzeStep.svelte`
   (17), `DuplicatesStep.svelte` (24), `ReviewStep.svelte` (36), `WizardFooter.svelte` (i pulsanti di ogni passo, 39);
   `wizardTypes.ts` con `StepId`, `PendingFileEntry`, `Step1SetWarning`, `FileSelection`, `SetPreviewEntry`,
   `ParsedFileResult`, `ParsedSetInfo`, `BrokerOpeningIssue`, spostati alla lettera. I passi `assets`, `fix` e `gapFix`
   erano già componenti in `components/transactions/import/` (non toccata). Restano nel padre la macchina a stati, gli
   handler, le modali impilate e l'unico `{@html}` (con `sanitizeHtml`); il padre non ha `<style>`.

   > **⚠️ Fuori pista**: (1) la prima configurazione della barra usava righe contate prima di `prettier`, e prendeva
   > blocchi di altri passi: il generatore si è fermato sui tipi mancanti, e l'intervallo è stato ricalcolato sul file.
   > (2) svelte-check 3/3 (08:52): 3 errori, tutti import di tipo mancanti in `WizardFooter.svelte`
   > (`PendingFileEntry`, `FileSelection`, `ParseUnit`), più un `BrimFile` doppio in `SelectFilesStep.svelte` corretto
   > prima: aggiunti; un controllo statico conferma che ogni nome di tipo nei `Props` dei sei pezzi è importato. Il
   > generatore ora fonde anche nelle righe `import type {…}`. La conferma con svelte-check arriva dopo la finestra.
3. ✅ **Cricchetto**: `--split` del Wizard nei sei pezzi; m1 595 = 222 (padre) + 20 + 22 + 67 + 77 + 86 + 101; il
   letterale `#dc2626` (`dotColor` nello script) resta nella riga del padre; `--check` pulito.
4. ✅ **Doc**: `developer/frontend/components/features/import-wizard.md` (i componenti dei passi e `wizardTypes.ts`).
   devWiki: `decisions/brim-broker-scoped.md`, `problems/playwright-probes-ignore-timeout.md`,
   `entities/import-wizard-modal.md` (le righe su ciò che ora sta nei passi); `check_source_paths.py` invariato. Nessun
   pezzo muta in loco una prop ricevuta senza `bind:` (controllo statico).
5. ✅ **Prove dopo l'avviso di fine finestra** (slot pesante 2, 15:28–15:58, revisione combinata `06459c1b3` + E1a):
   svelte-check, Vitest `tx-unit`, `core-unit`, `component-unit`
   (`ImportWizardModal.test.ts`), E2E `front-transaction all --workers 4`, `front-utility onboarding-tour` (la guida
   dell'import ancora le sue àncore ai passi), `mkdocs build` e `check-links`; poi l'handoff FROZEN.
   > **Note implementazione** (15:58): svelte-check 0/0 (nella `front build --debug`); `tx-unit` 903, `core-unit` 4 537,
   > `component-unit` 3 240; `front-transaction all --workers 4` 337/337 desktop, 34 mobile; `onboarding-tour` 10. I
   > dettagli e la doc nella sezione E1, passo 2. `mkdocs build` stretto (0 avvisi) e `check-links` (95) ✅ alle 16:05.

   > **Note implementazione (coordinatore, 15/10 ~09:05)**: FE8a-3 committato come checkpoint prima delle prove,
   > `b92e655d9` (`refactor(import-wizard): cut wizard steps and footer`, 13 file; 595 = 222 + 20 + 22 + 67 + 77 + 86 +
   > 101, `#dc2626` nel padre, `--check` pulito) e `063e5b7cf` (journal). Le prove della lista dopo la finestra, prima
   > dell'ingresso.

### N1 — numeri e dati: la cassa della pagina broker (W-B5) e il TRANSFER orfano (V-3) ⏳ (2026-10-15)

**Via del coordinatore** (15/10 ~09:05), con le risposte: (Q1) «oggi» ~~è la data del server~~ — **corretta alle ~09:12**
dopo la verifica di J: è il giorno dell'utente, come nella Dashboard: l'endpoint accetta `as_of` facoltativo (senza,
`date.today()`) e la pagina del broker passa `todayIso()`; (Q2) una CASH_TRANSFER orfana diventa
DEPOSIT o WITHDRAWAL secondo il segno (decisione del coordinatore nello spirito di quella del developer del 13/10 sul
TRANSFER; il developer può correggerla); (Q3) gli orfani già nei DB con una migrazione dei dati e il log di ogni riga
(D-J4, 14/10), numero 006, il primo libero sulla mia base (C7: rinominata se entra prima la 006 di A). I rossi su lotti e
Dashboard li scrive il mio test-author (J ha C-94 aperto); **J rivede i numeri attesi prima della cura** (sessione
`4c677a01-…`, gli scrivo io). Alle ~09:08: **N1b in due**: N1b-1 (la cancellazione converte la metà rimasta) entra
quando è pronto; N1b-2 (la migrazione) in un commit a parte, **solo con l'ok esplicito del developer** (punto 46 delle
decisioni). Durante la finestra: codice e singoli file pytest senza server, uno alla volta, con `nice -n 15`; `api`,
`all-backend` ed E2E dopo l'avviso di fine.

**Disegno** (verificato sul codice di `063e5b7cf`):

- **N1a · W-B5 (B15, D-J16)**: `BrokerSummaryOperations.get_summary` (`services/brokers/summary.py:74,78,86`) legge
  `TransactionService.get_cash_balances` e `get_asset_holdings` (`services/transactions/balances.py:153-163`), due somme
  SQL di ogni transazione del broker senza data, e `_holding_average_costs` (`summary.py:200-229`), che legge anche gli
  acquisti futuri. Cura: un solo «oggi», `as_of` (il giorno dell'utente; `date.today()` se assente), per la cassa, le
  quantità e il costo medio. La cassa da
  `financial_math/native_cash.py` (la casa unica: «Cash per broker and currency»), che ha già `balances(as_of)`; le due
  somme di `balances.py` sono una copia di quel calcolo e non hanno altri chiamanti. Le quantità: nessuna casa nella
  tabella di `backend.instructions.md` (la segnalo); restano la somma per asset, con la data.
- **N1b-1 · V-3 (D-J4)**: `TransactionService.delete_by_broker` (`services/transactions/transaction_service.py:60-79`),
  chiamata da `broker_service.py:494` (anche dalla cancellazione dell'account), oggi toglie solo
  `related_transaction_id` alla metà rimasta sull'altro broker. Cura: la metà rimasta di un TRANSFER diventa un
  ADJUSTMENT con la stessa quantità e lo stesso `cost_basis_override`; quella di una CASH_TRANSFER un DEPOSIT o un
  WITHDRAWAL secondo il segno dell'importo; in tutti e due i casi senza `related_transaction_id` né `link_uuid`.
- **N1b-2 · gli orfani già nei DB**: ~~migrazione dei dati `006`~~ → **correzione post-migrazione**
  (`db/post_migration/orphan_pair_halves.py`, decisione del coordinatore ~09:58), con una riga di log per ogni
  transazione convertita; commit a parte, in attesa del punto 46.

**Passi**:

1. ✅ Rossi (test-author), 2026-10-15: N1a in `services broker`; N1b-1 in `services transaction` / `services broker`; lotti e
   Dashboard dopo la cancellazione in `test_services/test_financial/`, numeri attesi rivisti da J.
   > **Note implementazione** (prima tornata, 09:30, rossi visti prima della cura): `test_broker_service.py`
   > (`TestGetSummaryAsOf` BR-U-090…093; `TestDeleteBulkCrossBrokerPair` BR-U-073…076) → `services broker` 13 rossi /
   > 48 verdi; nuovo `test_financial/test_orphan_transfer_after_broker_delete.py` con l'azione `services
   > orphan-transfer-numbers` (`in_all=False`; il file è anche dentro `roi-fifo-utils`) → 4 rossi / 2 controlli verdi.
   > **API** (seconda tornata, 10:15, scritti senza eseguirli per la finestra; `py_compile`, `ruff`, `black` puliti):
   > `test_brokers_api.py` `TestBrokerSummaryAsOf` BR-A-070…073 (verdi attesi: la cura di N1a c'è già; con una linea
   > USD a zero contro «nessuna linea», e un controllo di mezzanotte su BR-A-070) e, rossi fino a N1b-1, BR-A-032C (la
   > gamba in arrivo diventa ADJUSTMENT, quantità e costo invariati) e BR-A-032D nuovo (CASH_TRANSFER: la metà del
   > mittente diventa WITHDRAWAL −300); `test_account_deletion_api.py` ACCDEL-001 (`[new]` sul tipo ADJUSTMENT), con
   > docstring allineate al punto 47. I test nuovi puliscono i propri broker e asset (righe future nel DB condiviso).
   > **Terza tornata, in corso**: opzione b (BR-U-077 costo Auto 25 con taglio alla data; BR-U-079 pool vuoto = P-1),
   > caso speculare con i valori di oggi (BR-U-078 guardia; Dashboard 100/+80, lotti FAILED, posizione 6/20/180/60), i
   > perni di J (data del lotto, prezzo di riferimento, valuta del costo) e le due serie della cassa (finanziamento degli
   > acquisti, punto dei depositi) segnalate da J alle ~10:20.
2. Cure:
   - **N1a, backend** ✅ (2026-10-15 09:40). Q1 corretta dal coordinatore alle ~09:12, dopo la verifica di J: «oggi» è
     il **giorno dell'utente**, come nella Dashboard. Ok del coordinatore (~09:18, opzione A) per le sole 3 righe di
     `get_broker_summary` in `api/v1/brokers.py`; il resto del file aspetta il suo commit (W3, K2b, CP7).
     > **Note implementazione**: `GET /brokers/{id}/summary` accetta `as_of` facoltativo (aggiunta, nessun campo
     > tolto); `BrokerSummaryMixin.get_summary(..., as_of=None)` usa `as_of or date.today()` per cassa, quantità e costo
     > medio (`_holding_average_costs` filtra `date <= as_of`). `get_cash_balances(broker_id, as_of=None)` ora legge
     > la cassa dal layer: `native_balances(movements, as_of)`, funzione di modulo estratta da `NativeCash.balances`
     > (che le delega, stesso risultato), sui movimenti di `cash_movement_from_transaction` — stesse righe della somma
     > SQL di prima (valuta e importo presenti; la linea a zero resta). `get_asset_holdings(broker_id, as_of=None)`
     > resta una somma SQL con la data (nessuna casa delle quantità nella tabella di `backend.instructions.md`: lo
     > segnalo nell'handoff). Estrazione nel layer di J: approvazione chiesta a J, in attesa.
     > Prove (`nice -n 15`, senza server): `ruff --select I`, `ruff`, `black --check` puliti sui 4 file;
     > `services broker` 53 passed / 8 failed — verdi i 6 di `TestGetSummaryAsOf` (BR-U-090…093), rossi solo gli 8
     > di N1b-1 (BR-U-073 ×4, BR-U-076 ×4); `services financial-math` 212 passed (guardie del layer).
     > Resta per N1a: la riga di `routes/(app)/brokers/[id]/+page.svelte:281` (`as_of: todayIso()`), `api sync`, e un
     > rosso/verde API del parametro, dopo l'avviso di fine finestra.
   - ⏳ **N1b-1**, dopo l'ok di J sui numeri.
     > **Esito di J** (15/10 ~09:50, letto nel codice): numeri giusti (investito 80, P&L 40); il cambio per il
     > co-proprietario (100/20 → 80/40) accettato ma **da dichiarare** (conferma di cancellazione, doc, CHANGELOG);
     > **caso 2 = opzione b** per le cancellazioni nuove: il costo **Auto** già esistente (`_auto_cost_source` +
     > `compute_wac_iterative`), calcolato prima che spariscano le righe del mittente, override e valuta insieme
     > (eredita P-1); i tre perni da fissare nei test: (a) il lotto riparte alla data del trasferimento, (b) prezzo di
     > riferimento del giorno d'apertura (rendimento relativo +20 %, P&L % +50 %), (c) valuta del costo con l'override.
     > Ok sul diff di `native_cash.py` (golden `test_native_cash_guard.py` byte-identico: `services roi-fifo-utils`
     > 657 verdi, i 4 rossi sono i miei). J-9 e J-10 (fuori N1) li registra J.
     > **⚠️ Fuori pista** (J, ~10:10): il caso speculare — cancellato il **destinatario**, resta la gamba in uscita del
     > mittente — convertito alla lettera (ADJUSTMENT −4 senza costo: una gamba in uscita non può portarlo) farebbe
     > leggere le unità spostate come distrutte (P&L di A da +80 a −20, lotti −20). Decisione chiesta da J al
     > coordinatore; **intanto**: si convertono solo le metà **in arrivo** di un TRANSFER; quella in uscita perde solo il
     > link, come oggi; CASH_TRANSFER e FX_CONVERSION per segno. Il caso speculare entra nei test coi valori di oggi.
     > Lo split (`batch_edits.py:126-139`) produce già ADJUSTMENT in uscita senza costo: J lo porta al coordinatore.
     > **Confermato dal coordinatore** (~10:12): in N1b-1 e N1b-2 solo le gambe in arrivo di un TRANSFER e quelle di
     > cassa; le gambe in uscita restano come oggi fino alla risposta del developer al **punto 47**; il dry run le conta a parte.
   - **N1b-1, cura** ✅ (2026-10-15 10:25; riordino «prima i costi» 10:51). `/tmp/libreFolio_w_n1b1_final.py --apply`, poi
     `/tmp/libreFolio_w_n1b1_atomic.py --apply` (`_auto_cost()` calcola, `_write_auto_cost()` scrive; BR-U-080 verde).
     > **Note implementazione**: `batch_edits.py`: `pair_sides()` (la regola del lato: quantità per un TRANSFER, importo
     > per la cassa) e `make_standalone()` (tipo, link via, asset via se non è un ADJUSTMENT, `updated_at` adesso)
     > estratti da `apply_splits()`, che li usa: stesso comportamento. `auto_cost.py`: `_write_auto_cost()` estratto da
     > `_compute_wac_for_auto_items()` (asset, `compute_wac_iterative`, override e valuta insieme); nessun nuovo punto
     > d'import di `compute_wac_iterative` (per il CP-8 di J). `transaction_service.delete_by_broker()`: carica le metà
     > rimaste sugli altri broker (`related_transaction_id IN` le righe del broker), scrive il costo Auto sulle gambe in
     > arrivo senza costo finché le righe del mittente ci sono, scollega le coppie interne del broker, poi converte in
     > place con `SPLIT_TYPE_MAP` — salvo la gamba in uscita di un TRANSFER (punto 47) e un link ignoto allo split
     > (ADJUSTMENT), che perdono solo il link (con `updated_at`) — e infine cancella. La FK `DEFERRABLE INITIALLY
     > DEFERRED` regge l'ordine.
     > Prove (`nice -n 15`, senza server): `services broker` **64/64** (prima 9 rossi), `services orphan-transfer-numbers`
     > **16/16** (prima 6 rossi), `services transaction` 66/66 (copre `apply_splits`), `services roi-fifo-utils` 671/671
     > (golden di J byte-identico). `ruff`, `black` puliti.
     > **⚠️ Fuori pista** (docs-writer, 10:20): `DELETE /brokers` fa commit quando `response.errors` è vuoto
     > (`api/v1/brokers.py:389`) e `delete_bulk` non lo riempie mai (cattura per broker): un errore a metà di
     > `delete_by_broker` lascerebbe nel commit il costo Auto già scritto su una prima gamba. Un SAVEPOINT per broker non è
     > sicuro qui: senza il listener `begin` di SQLAlchemy, pysqlite non apre la transazione prima del primo DML, e il
     > RELEASE del savepoint più esterno farebbe commit (romperebbe l'atomicità della cancellazione dell'account di A).
     > Cura scelta: **prima tutti i costi Auto, poi le modifiche** (`_auto_cost()` calcola, `_write_auto_cost()` scrive),
     > con il rosso BR-U-080 prima (test-author, in corso). Il resto del difetto generale (nessuna atomicità per broker in
     > `delete_bulk`) va nella sezione W del backlog.
     > **Revisione di J delle serie di cassa** ✅ (~10:45, a mano sul ramo del frame, `daily_state.py:451-570`): C1 oggi
     > 300/0 → dopo 100/200, depositi {1/10: 1000} → {1/10: 1000, 5/10: 300}; C2 oggi 400/200 → dopo 500/100; capitale e
     > P&L fermi (C1 100/300/200, C2 400/600/200); giuste le correzioni del test-author (seconda vendita in C2, utili
     > ritirati prima in C1, citazioni `:505-570`); W globale = semantica esistente. Perni (a), (b), (c), BR-U-077,
     > BR-U-079 e speculare: ok. La lista dei lotti sotto FAILED la prende J (J-12); W-B19: copia per la metà di cassa.
     > Provato (10:33) su un SQLite in `/tmp` con `aiosqlite` e un `AsyncSession` come quelli dell'app: SELECT, poi
     > `begin_nested()` con un INSERT, poi il rollback esterno → la riga **resta** (il RELEASE ha fatto commit); con un
     > DML prima del savepoint → nessuna riga. ~~Lo stesso vale per `assets/crud.py:392` (X), dove ogni asset cancellato
     > in blocco entra subito nel commit: lo segnalo al coordinatore.~~ W-B19 e W-B20 nella sezione W del backlog.
     > **Correzione** (11:19, reperti di X girati dal coordinatore): avevo letto solo la riga 392. `delete_assets_bulk` è
     > già atomico: un `UPDATE` vuoto prima del primo savepoint (`assets/crud.py:349-351`, da `e50d66408`) fa emettere
     > `BEGIN`, e lo fissa `test_asset_source.py::test_delete_assets_bulk_commit_failure_propagates_and_rolls_back_tentative_deletes`.
     > Il listener `begin` generale è scartato (X: lettura, commit di un altro scrittore, poi scrittura → subito
     > `SQLITE_BUSY_SNAPSHOT`, che `busy_timeout` non aspetta). Cura decisa per W-B20: un aiuto in `db/session.py` che apre
     > la transazione prima del primo savepoint (lo stesso `UPDATE` vuoto, o `BEGIN IMMEDIATE`), usato da `delete_bulk`
     > per broker, con un rosso prima: lotto piccolo di W dopo l'ingresso di N1.
     > **Superfici concesse dal coordinatore** (~10:05): testo `brokers.confirmDeleteWithTransactions` (4 lingue, `i18n
     > update`, nessun markup); frase in `user/brokers/index.{en,it,fr,es}.md:49` + `translate-stamp`; riga del
     > CHANGELOG proposta nell'handoff. Fatte (10:03): il testo EN approvato, precisato dopo la restrizione di J (solo
     > gli asset **trasferiti da** questo broker diventano posizioni d'apertura); `translate-stamp` sul file EN.
     > Cura pronta in `/tmp/libreFolio_w_n1b1_final.py` (helper `pair_sides`/`make_standalone` estratti da
     > `apply_splits`; `_write_auto_cost` estratto da `_compute_wac_for_auto_items`; nessun nuovo punto d'import di
     > `compute_wac_iterative`), da applicare dopo i rossi aggiornati (test-author, opzione b e caso speculare).
3. ✅ N1b-2 (scritta e provata, 11:00; entra solo con l'ok del developer sul **punto 46**) — **correzione post-migrazione**, non Alembic (coordinatore, ~09:58: il log di una migrazione Alembic si
   perde all'avvio, `main.py:202-209` con `capture_output=True`, anche in Docker). `post_migration/orphan_pair_halves.py`
   è mio; la voce in `FIXES` di `post_migration/__init__.py` concessa, solo in aggiunta. Commit a parte, entra solo con
   l'ok del developer sul punto 46.
   > **Punto 46 deciso** (developer, 15/10 16:00, alla lettera): «Sì: la correzione entra, e una metà senza costo resta
   > «costo mancante» con l'avviso». N1b-2 ed N1b-3 entrano con il resto del ramo, così come sono: la metà senza costo
   > diventa una rettifica senza costo, con l'avviso `MISSING_COST_BASIS`. Il punto 47 (la gamba in uscita) resta aperto,
   > e la gamba resta com'è oggi.
   > **Domanda del developer sul 46** (coordinatore, 16:15, corretta alle 16:25): quando nasce una metà ricevuta senza
   > costo? Nei metadati dei tipi il lato ricevente di `TRANSFER` ha `cost_basis_pair: ["forbidden",
   > "required_qty_pos"]` (`schemas/transactions/type_metadata.py:286`): il modulo e il Bulk, dove passano anche gli
   > import, obbligano a scegliere un costo (manuale o Auto). Una metà ricevuta senza costo nasce solo dall'API chiamata
   > direttamente, o da dati più vecchi della 1.0. Per N1b-2 non cambia nulla: il caso «senza costo» resta una rete di
   > sicurezza. Nessuna voce di backlog: quella scritta alle 16:15 su una lettura sbagliata è ritirata dal coordinatore e
   > tolta (il suo id, W-B25, entrato in `d7c7dcab7`, non si riusa).
   > **Note implementazione** (10:00): `OrphanPairHalfFix` (`fix_id` `orphan_pair_halves`): `detect` trova le righe
   > TRANSFER/CASH_TRANSFER/FX_CONVERSION senza la metà (link NULL o verso una riga assente) e logga un **warning** con
   > le conversioni per tipo, le righe che resteranno senza costo, quelle lasciate come sono (gamba in uscita di un
   > TRANSFER, in attesa della decisione; segno illeggibile) — visibile anche nel dry run della CLI, che mostra solo
   > WARNING+; `apply` converte (tipo, link NULL, asset NULL per la cassa, `updated_at` adesso); `verify` richiede zero
   > convertibili rimasti e il tipo atteso su ognuna; `finish` logga una riga per transazione convertita **solo dopo
   > il commit**. Le righe senza costo restano senza (opzione a: il mittente non c'è più → `MISSING_COST_BASIS`).
   > Prova a mano su un SQLite in `/tmp` (9 righe, ogni classe): conversioni giuste, coppia collegata intatta,
   > seconda esecuzione `clean`. I test veri con test-author dopo i rossi di N1b-1. `ruff`/`black` puliti.
   > **Ritocchi** (10:16): una metà **non** convertita (gamba in uscita di un TRANSFER, punto 47; segno illeggibile) il
   > cui link nomina una riga che non c'è più perde solo il link, come la lascia la cancellazione: altrimenti il
   > `foreign_key_check` del quadro farebbe fallire la correzione, e a ogni avvio resterebbe una copia del DB in più.
   > Il warning della rilevazione esce **a ogni avvio** finché esistono gambe in uscita lasciate (il dry run deve
   > contarle comunque, e la CLI mostra solo WARNING+), con un messaggio distinto quando non c'è nulla da convertire.
   > Seconda prova attraverso il vero `run_post_migration_fixes` (FK dichiarata, una gamba in uscita con link
   > pendente): dry run `would_apply`; poi `applied`, copia cancellata, `foreign_key_check` vuoto, una riga di log per
   > ogni riga cambiata, seconda esecuzione `clean`. Nella CLI le righe INFO per riga non si vedono (il `__main__` non
   > configura il livello INFO): si vede il warning con gli id per conversione; nel log del server (anche in Docker) ci
   > sono tutte.
   > **Test** (test-author, 10:48): `test_db/test_post_migration_orphan_pairs.py`, 42 test (un DB alla testa con
   > alembic `-x sqlalchemy.url=`, copiato per test, data dir in sandbox con canarino come `test_post_migration.py`):
   > registrazione dopo `autoincrement`; DB pulito; 16 conversioni (6 tipi × link NULL/pendente, più l'arrivo con e
   > senza costo); 15 righe lasciate (gambe in uscita, segno illeggibile, coppie intere, altri tipi) e 3 che perdono solo
   > il link pendente; esito `applied` con FK pulite e conteggi invariati; seconda esecuzione `clean`; dry run; il
   > warning; una riga INFO per riga cambiata; verifica fallita → DB com'era, copia tenuta. Azione nuova `db
   > post-migration-orphan-pairs` in `scripts/test_runner/_backend_db.py` (solo aggiunta, anche in `db_order`).
   > **Rosso visto** (10:52): tolta la registrazione da `FIXES` → **42 rossi**; rimessa → `git diff` di `__init__.py`
   > uguale a prima (import più la voce). Con la registrazione: **42/42** (due volte).
   > **⚠️ Fuori pista** (test-author): una riga di un altro tipo (un ADJUSTMENT può portare un link) con il link
   > pendente farebbe fallire il `foreign_key_check` del quadro a ogni avvio, con una copia del DB in più ogni volta.
   > Cura: anche lei perde solo il link, come fa la cancellazione per «un link che lo split non conosce». Rossi prima
   > (test-author), poi `/tmp/libreFolio_w_n1b2_otherlinks.py`.
   > Fatto (10:58): 2 rossi visti (`failed` con la copia tenuta; `clean` con la violazione rimasta), poi l'estensione
   > → **45/45**; un link verso una riga che esiste non si tocca (guardia verde).
4. Verdi senza server durante la finestra ✅ (11:00); `api`, `all-backend` ed E2E dopo l'avviso di fine ✅ (slot pesante
   2, 15:58); handoff FROZEN per N1a+N1b-1, e N1b-2 separato.
   > **Prove dopo la finestra** (slot pesante 2, revisione combinata `06459c1b3` + E1a): `api sync` (il parametro
   > `as_of` c'è nel client generato); `all-backend` 7/7 (comprende `api brokers`, `api account-deletion`, `api
   > batch-split-promote`, `services broker`, `db post-migration-orphan-pairs` 47); `front check` dentro la `front build
   > --debug` (0/0); E2E `front-broker detail` 37, `front-broker list` 9, `front-user account-deletion` 1. Dettagli
   > nella sezione E1, passo 2.
   > **Note implementazione** (11:00, tutto con `nice -n 15`, senza server): `services broker` 65/65 (con BR-U-080 dopo
   > il riordino «prima i costi»: rosso visto alle 10:48), `services orphan-transfer-numbers` 19/19 (con il controllo
   > dell'opzione a: un ADJUSTMENT +4 senza costo → lotti DEGRADED, Dashboard investito 0 / P&L 120 / MISSING_COST_BASIS),
   > `services transaction` 66/66, `services roi-fifo-utils` 671/671, `services financial-math` 212/212,
   > `db post-migration-orphan-pairs` 45/45 (rossi visti: 42 senza la registrazione, poi 2 per gli altri tipi con link
   > pendente prima dell'estensione), `db post-migration` 37/37 (piano 34, invariato); `ruff`/`black` puliti sui 15
   > file Python; `git diff --check` pulito; `i18n check` stretto pulito (4 392 chiavi); `check_source_paths` invariato
   > (5 percorsi inesistenti, 8 occorrenze, nessuno mio). devWiki: `decisions/orphan-transfer-becomes-an-adjustment.md`,
   > stato aggiornato (la correzione post-migrazione solo in prosa: il suo file entra con il commit a parte).
   > **Dopo la finestra**, nell'ordine: `api sync` (atteso: solo il parametro `as_of`); `test db populate --force
   > --clean` sulla mia data-dir; `api brokers` (BR-A-070…073 verdi, BR-A-032C/D), `api account-deletion` (ACCDEL-001),
   > `api batch-split-promote` (il riordino di `apply_splits`); `all-backend`; `front check`; E2E `front-broker
   > detail`, `front-broker list` (testo della conferma), `front-user account-deletion`; `mkdocs build` stretto e
   > `check-links`. Prima di tutto questo, le prove di FE8a-3 già in fila.
   > **Checkpoint** (coordinatore, 11:04): `6be11ecf3` fix(brokers): user-day summary, orphan pair halves (26 file);
   > `0737055e0` docs(journal): W N1 checkpoint, W-B17..W-B20; `5e19c6018` fix(db): post-migration fix for orphan pair
   > halves (4 file), **per ultimo**: senza l'ok sul 46 prima dell'ingresso il ramo entra fino a `0737055e0`. Risposte:
   > doc di N1b-2 solo in inglese (`developer/architecture/database/index.md`, `admin/cli_tools.en.md`), in un commit
   > sopra N1b-2, senza IT/FR/ES né stamp (il debito di `cli_tools` sta in A-10: W-B21 nella mia sezione, A-10 non è
   > ancora nel mio ramo); W-B20 da decidere, non ora (poi, alle 11:19, cura decisa: vedi la correzione sopra);
   > CHANGELOG all'ingresso, con le mie righe.
5. ✅ Doc di N1b-2 (docs-writer, EN, 11:20), sopra `5e19c6018`; poi le prove dopo la finestra (punto 4).
   > **Note implementazione**: `developer/architecture/database/index.md` (la seconda correzione: perché, cosa rileva,
   > converte e lascia, i controlli, i log, il comando del test) e `admin/cli_tools.en.md` (tre punti per
   > l'amministratore, e nel riquadro il dry run **prima del primo avvio della nuova versione**: dopo, la correzione è
   > già passata). Solo EN, niente stamp (W-B21). Il docs-writer ha provato lo script su DB di prova in `/tmp`, poi
   > cancellati. Corretta la docstring del contratto 8 del mio test (diceva ancora «RED until»).
   > **⚠️ Fuori pista** (docs-writer): (1) una violazione di FK già nel DB fa fallire `autoincrement` e ferma il giro
   > prima di `orphan_pair_halves`, a ogni avvio con una copia in più (quadro del piano 34, già prima di N1b-2): W-B22;
   > (2) lo script a mano non configura il log, quindi niente righe INFO per transazione: W-B23. Tutte e due da
   > assegnare: file del quadro.
   > **Docs committate** (coordinatore, 11:19): `3f42dda9d` sopra `5e19c6018`. W-B22 e W-B23 **assegnate a me** come
   > lotto **N1b-3**, sopra il commit delle docs (W-B22 è legata a N1b-2: un DB che chiede ancora `autoincrement` e ha
   > un link pendente non arriva mai a `orphan_pair_halves`). Rossi prima; durante la finestra solo prove leggere.

### N1b-3 — il quadro delle correzioni post-migrazione: violazioni di FK preesistenti (W-B22) e log dello script (W-B23) ✅ (2026-10-15)

**Via del coordinatore** (15/10 ~11:25, base `eb3bb0529`): W-B22 e W-B23 assegnate a me, lotto sopra il commit delle docs
di N1b-2 (W-B22 è legata a N1b-2: un DB che chiede ancora `autoincrement` e ha un link pendente non arriva mai a
`orphan_pair_halves`). Rossi prima; durante la finestra solo prove leggere (`nice`, senza server).

**Disegno** (verificato su `eb3bb0529`):

- **W-B22**: `_apply_one` (`backend/app/db/post_migration/__init__.py`) aggiunge ai controlli della correzione
  `_common_problems`, che vuole `PRAGMA foreign_key_check` **vuoto** sull'intero DB. Una violazione già presente fa
  fallire qualunque correzione, a ogni avvio, con una copia `.bak` in più; e `_apply_pending` si ferma alla prima che
  fallisce. Cura: come per i conteggi delle righe, si confronta con lo stato di prima: è un problema solo una violazione
  **nuova** (l'insieme `(tabella, rowid, padre, fkid)` letto subito prima della correzione). Le violazioni già presenti
  si dicono in un warning, una volta per giro, e restano. `autoincrement` ricopia le righe con gli stessi id e lo stesso
  DDL più `AUTOINCREMENT`, quindi le tuple restano uguali; `orphan_pair_halves` poi toglie i link pendenti delle
  transazioni.
- **W-B23**: `python -m backend.app.db.post_migration` non configura il log: le righe INFO (una per transazione
  cambiata, «applied and verified» con i secondi) si perdono, e il warning esce come testo su stderr (lastResort). Cura:
  `configure_logging(LOG_LEVEL, enable_file_logging=False)` **solo nel blocco `if __name__ == "__main__"`**: la console
  (stdout, righe JSON come il server) e nessuna scrittura nella data-dir, che i test del piano 34 proteggono con il
  canarino; `main()` chiamato in-process (test, figlio della prova di concorrenza) non riconfigura nulla.

**Passi**:

1. ✅ Rossi (test-author, 11:32): W-B22 (DB 1.1 alla testa con un link pendente → oggi `autoincrement` `failed` e
   `orphan_pair_halves` mai eseguita; una violazione in un'altra tabella → oggi `failed` a ogni avvio; guardia: una
   correzione che **aggiunge** una violazione fallisce ancora); W-B23 (lo script stampa una riga per transazione e la
   chiusura con i secondi; il dry run solo il warning; nessun file nella data-dir configurata).
   > **Note implementazione**: `test_post_migration.py` (piano 34, **solo aggiunte**: 154 righe, nessuna asserzione
   > toccata) contratto 14 — pin 1 `test_a_broken_link_already_there_no_longer_blocks_the_fixes` (rosso:
   > `['failed', 'would_apply']`, errore `foreign_key_check: ('transactions', 12, 'transactions', 1)`, copia tenuta), pin 2
   > `test_a_broken_link_in_another_table_is_left_as_it_is_and_reported` (rosso: una riga di `price_history` di un asset
   > cancellato, `failed` due volte), pin 3 `test_a_fix_that_breaks_a_link_itself_still_fails` (guardia verde: un UPDATE
   > che rompe un riferimento, non una DELETE, che fallirebbe già sui conteggi) — e contratto 15, la guardia `nessun
   > file nella data-dir` (verde). `test_post_migration_orphan_pairs.py` contratto 9 — pin 4 (rosso: nessuna riga JSON
   > per riga cambiata) e pin 5 (rosso: il warning del dry run solo come testo su stderr), con `LIBREFOLIO_LOG_LEVEL=INFO`
   > forzato nel figlio. Prove: `db post-migration` 39/41, `db post-migration-orphan-pairs` 45/47, rossi solo i quattro.
   > **⚠️ Fuori pista** (test-author): il nome della copia è al secondo, quindi due giri falliti nello stesso secondo
   > lasciano una copia sola (la seconda sovrascrive la prima); fra secondi diversi le copie si accumulano. Solo nota.
2. ✅ Cure (11:33), `/tmp/libreFolio_w_n1b3_fix.py --apply`.
   > **Note implementazione**: `post_migration/__init__.py`: `_fk_violations()`; `_apply_one` legge le violazioni subito
   > prima della correzione e `_common_problems` segnala solo quelle nuove (ordinate); `_apply_pending`, dopo la copia,
   > logga una volta il WARNING «Foreign key violations already in the database, left as they are» (`count`, fino a 20
   > righe). `__main__.py`: `configure_logging(get_settings().LOG_LEVEL, enable_file_logging=False)` nel solo blocco
   > `if __name__ == "__main__"`. Prove (`nice -n 15`, senza server): `db post-migration` **41/41**,
   > `db post-migration-orphan-pairs` **47/47**; `ruff`/`black` puliti.
3. ✅ Doc EN (11:36), a mano (correzioni puntuali): `developer/architecture/database/index.md` (il passo 5 con la regola
   delle violazioni nuove e il warning; lo script logga sulla console; tolta la frase delle righe INFO perse) e
   `admin/cli_tools.en.md` (un punto per il warning delle violazioni già presenti; nel riquadro, lo script stampa il
   log e non scrive file). Solo EN (W-B21). `mkdocs build` e `check-links` dopo la finestra.
4. ✅ Handoff FROZEN (committati dal coordinatore: `0e4bd9790` fix(db), `05f2cb106` journal). `mkdocs build` stretto e
   `check-links` sulla revisione combinata ✅ (16:05, sezione E1, passo 2).

### E1 — eventi: decisioni 20–23 del developer (V-22, I-09, I-10 S4 e resto, I-11c, I-12) ⏳ (2026-10-15)

**Via del coordinatore** (15/10 12:44, base `05f2cb106`), con le decisioni del developer (file delle decisioni e chat
del 15/10 12:30–12:44):

- **20**: «+ Nuovo evento» non sovrascrive mai. Se esiste un evento con la stessa data e lo stesso tipo, manuale o del
  fornitore, arriva un errore: la finestra mostra l'evento esistente e offre «Modifica questo», «Usa questo» e
  «Annulla». **Niente «Crea comunque»** (developer: due eventi dello stesso tipo nello stesso giorno non capitano).
  L'editor degli eventi e il CSV continuano ad aggiornare per data e tipo, come oggi.
- **21**: la cancellazione degli eventi indica l'asset.
- **22**: tutto o niente, e se fallisce dice dove.
- **23**: il tipo in maiuscolo all'ingresso e, se ancora non va, salvataggio rifiutato; quelli già salvati male si
  cancellano tutti; per quelli collegati a transazioni la proposta è mia (per esempio scollegare e poi cancellare, con
  il log dei due passi); **prima il conteggio sulla copia del DB**.
- **24**: K-1 chiusa senza codice. **25**: resta così; una voce nel backlog per un modello futuro.
- Dipendenza: B0 (`api/v1/backup.py` → pacchetto `api/v1/backup/`) non è ancora in `dev_release2`; E1 non tocca
  l'export degli eventi. Fino all'avviso di fine della finestra della galleria (~13:00) solo prove leggere.

**Disegno** (verificato su `05f2cb106`; appunti dell'analisi del mattino in `files/e1-prep.md` della sessione):

- **E1a, backend** (moduli miei da X CP2b: `api/v1/assets/events.py`, `services/assets/event_store.py`,
  `schemas/assets/events.py`):
  - **D23 / I-09**: validatore `before` su `FAAssetEventPoint.type` (spazi tolti, maiuscolo; fuori da
    `AssetEventType` → errore di validazione, 422). Il tipo resta `str` nell'OpenAPI. Vale per API, editor, CSV,
    pianificazioni dei parametri e uscite dei plugin (tutti già in maiuscolo).
  - **D22 / I-12b**: `bulk_upsert_events` in **una transazione**: gli elementi in ordine, con flush e nessun commit fino
    alla fine; ogni errore → rollback, niente scritto. Un asset inesistente → `EVENT_ASSET_NOT_FOUND` invece di «0
    salvati». Gli errori dicono **dove** (elemento, asset, evento: indice, data, tipo) in un dettaglio strutturato
    `{error_code, message, params}`, come gli altri errori di `api/v1/assets/`. `_upsert_asset_events(..., commit=True)`:
    il percorso manuale passa `False`; il refresh dei fornitori (`refresh.py:557`, X) resta a blocchi.
  - **D21 / I-12a**: `DELETE /assets/events?asset_id=&ids=` con `asset_id` obbligatorio; gli id di un altro asset
    tornano `not_found`.
  - **D20 / V-22**: `FAEventUpsert.mode`: `"upsert"` (oggi, predefinito) o `"create"`. In `create` solo eventi senza
    id; se un evento con la stessa data e lo stesso tipo esiste già (manuale o del fornitore) → 409 `EVENT_EXISTS` con
    gli eventi esistenti (id, data, tipo, valore, note, `is_auto`, transazioni collegate) e nulla scritto.
  - **I-10 S4**: `FAEventUpsertResult.event_ids`, gli id scritti in ordine (aggiunta).
- **E1b, frontend**:
  - `EventCreateMiniModal.svelte` manda `mode: "create"`. Su `EVENT_EXISTS` un componente nuovo,
    `EventExistsPanel.svelte` (solo ruoli `lf-*`), mostra l'evento o gli eventi esistenti: «Usa questo» (lo collega),
    «Modifica questo» (solo manuale: il form passa a quell'evento, con i suoi valori, e salva per id), «Annulla» (torna
    al form). Un evento del fornitore non si modifica (`EVENT_NOT_EDITABLE`): una nota e solo «Usa questo». Il
    collegamento usa l'id restituito (S4).
  - `AssetDataEditorSection.svelte` (righe di X concesse): la cancellazione con `asset_id` (D21); prima le
    cancellazioni, poi le modifiche (I-10: spostarsi sulla chiave di un evento appena cancellato); l'errore del server
    tradotto con la riga (D22, D23); la valuta della riga, se c'è (I-11c: un evento in un'altra valuta viene rifiutato
    con la sua riga, invece di essere rietichettato in silenzio).
  - i18n nelle 4 lingue; doc utente.
- **E1c, dati (D23)**: una correzione post-migrazione `event_types` (come N1b-2: il dry run fa da conteggio, ogni riga
  il suo log) che porta in maiuscolo i tipi correggibili e cancella gli sconosciuti, scollegando prima le transazioni
  (log dei due passi). Il quadro vuole i conteggi delle righe invariati: serve una sua estensione (delta dichiarati
  dalla correzione, controllati esatti).

**Risposte del coordinatore** (15/10 ~12:58), disegno approvato:

1. **Niente conteggio sulla copia del developer**: i dati di produzione non si toccano, la copia in `/tmp` non c'è più,
   e il developer ha già deciso («l'unica è cancellarli»). Sui DB veri il conteggio è il dry run della correzione.
   Lo script di conteggio (provato solo su un DB sintetico) è stato cancellato senza lanciarlo su dati veri.
2. **E1c = correzione post-migrazione `event_types`** al posto della 008: prima il maiuscolo, poi scollegare e
   cancellare i tipi sconosciuti, ogni riga con il suo log; l'estensione del quadro (delta dichiarati dalla
   correzione, controllati esatti) con un rosso prima; commit a parte. **E1 staccato il più possibile da N1b-2**: se il
   developer dice no al 46, E1 deve poter entrare senza N1b-2; `post_migration/__init__.py` solo per l'estensione (e la
   registrazione), dichiarato nell'handoff.
3. **«Modifica questo»** come proposto: il form passa all'evento esistente con i suoi valori e salva per id; per un
   evento del fornitore la nota e solo «Usa questo»; «Annulla» torna al form.
4. Colori: il coordinatore chiede al coordinatore colori dei due file; intanto E1a.
5. W-B24 nella mia sezione. 6. K-1 la chiude il coordinatore nel README del 38.
- Nell'handoff: la voce «⚠️ Breaking changes» del CHANGELOG per il 21 (`asset_id` obbligatorio).

**Passi**:

1. ✅ Rossi E1a (test-author): servizio 13:38, API 14:44 (slot pesante 2).
   > **Rossi del servizio visti** (13:38, `nice -n 10`, dopo la pausa delle dipendenze; `cryptography 50.0.2` e
   > `pycparser 3.11` nell'ambiente condiviso, `dc9a5d232` su `dev_release2`): nuovo
   > `test_services/test_asset_event_store.py` con l'azione `services asset-event-store` (`write-global`): **40 test, 34
   > rossi, 6 guardie verdi** — tipi non normalizzati (`'dividend' == 'DIVIDEND'`, `DID NOT RAISE`, riga grezza
   > `'dividend'`), elementi già salvati prima del rifiuto, asset mancante «0 salvati», `details == {}`, `mode`/`event_ids`
   > campi sconosciuti, `delete_events_bulk()` senza `asset_id`. `services asset-source-guards` 29/29. `ruff`/`black`
   > puliti. Le due azioni dei servizi ricreano vuoto il DB della corsia (comportamento normale).
   > `test_api/test_assets_events.py`: 37 test, 18 rossi attesi (10 nuovi, `test_upsert_nonexistent_asset` e
   > `_assert_rejected` ritarati sul contratto nuovo, i 5 test di cancellazione con `asset_id`). Nessun altro test del
   > backend chiama `DELETE /assets/events`; gli E2E che lo fanno: `tx-bulk-promote-cost-basis.spec.ts:353`,
   > `asset-event-delete.spec.ts:176,204,252`, `asset-data-editor.spec.ts:472,613`.
   > **⚠️ Fuori pista** (13:41–13:46): `db populate --force --clean` (`nice -n 15`) verde; poi `api assets-events`
   > (via del coordinatore, «con le due build dentro», `nice -n 15`): **il backend condiviso non ha risposto in 300 s**
   > — la build del frontend (vecchia: 08:30) non è finita dentro `LIBREFOLIO_TEST_STARTUP_TIMEOUT`, con il carico della
   > macchina a 77. Nessun test eseguito, nulla rimasto acceso, porta libera. Riferito al coordinatore con due strade:
   > ripetere con `LIBREFOLIO_TEST_STARTUP_TIMEOUT=1200` a carico basso, o i rossi API nello slot dopo il merge.
   > **Preparato, non applicato** (13:05–13:20): `/tmp/libreFolio_w_e1a_fix.py` (dry run: ancore trovate, i 3 file
   > compilano) e `/tmp/libreFolio_w_e1c_fix.py` (dry run ok). E1a: `_upsert_asset_events` delega a
   > `_write_asset_events`, che dà gli id scritti nell'ordine (letti dopo il flush, prima di un commit);
   > `bulk_upsert_events` = `_write_manual_item` per elemento + un commit, rollback su qualunque errore, e i dettagli
   > completati con `asset_id` e `item_index`; `_reject_currency_mismatches`, `_reject_existing_events` (409
   > `EVENT_EXISTS` con gli esistenti e i collegamenti); `delete_events_bulk(asset_id, …)`; il validatore del tipo; il
   > dettaglio HTTP `{error_code, message, params}`. E1c: `PostMigrationFix.row_count_changes()` in `base.py`; in
   > `__init__.py` `_expected_counts()`, `_common_problems(conn, counts_expected, …)` con il messaggio «row counts not
   > as expected: tabella (expected N, found M)», la registrazione; `post_migration/event_types.py` (`EventTypesFix`).
   > I ruoli dei colori per `EventExistsPanel`: `tokens.css` e `app.css` uguali fra HEAD e `dev_release2`.
   > **Via libera dei colori** (coordinatore colori, 13:00): nessun annuncio aperto sui due file; T li converte più
   > avanti (ondata W4). Vincoli: in `AssetDataEditorSection.svelte` non spostare né togliere il letterale `#a855f7`
   > della linea d'anteprima (eccezione R-6, `frontend/scripts/theme/theme-roles.mjs:73`); m1 17 lì e 42 in
   > `EventCreateMiniModal`: nessuna classe nuova; `EventExistsPanel.svelte` solo con i ruoli già in `tokens.css`.
   > **E1a porta anche il frontend che la rottura del 21 richiede**: la riga della cancellazione nell'editor
   > (`queries: {asset_id: assetId, ids}`) e gli E2E che chiamano `DELETE /assets/events` senza `asset_id`
   > (`tx-bulk-promote-cost-basis.spec.ts:353`, `asset-event-delete.spec.ts:204`, `asset-data-editor.spec.ts`): se E1a
   > entrasse da solo, l'editor non cancellerebbe più (422).
   > **Pausa delle dipendenze** (13:20, `cryptography` nell'ambiente condiviso): nessun comando Python; nella mia corsia
   > non girava nulla («fermo» al coordinatore). ⚠️ Mia svista: un `python --version` (nessun import, nulla scritto).
   > Intanto, solo codice: le bozze di E1b in `/tmp/libreFolio_w_e1b/` (`EventExistsPanel.svelte`, solo ruoli;
   > `eventSaveError.ts`, puro) e `/tmp/libreFolio_w_e1b_fix.py` (mini-modale: `mode`, `event_ids`, pannello, «Modifica
   > questo» con i valori dell'evento e i decimali conservati sul blur; editor: prima le cancellazioni, `asset_id`, la
   > valuta della riga importata, l'errore tradotto con la riga), e le chiavi i18n in `/tmp/libreFolio_w_e1b_i18n.sh`.
   > La riga registrata del toast della mini-modale (`moneyRenderSites.test.ts`) resta identica; il pannello mostra
   > importo e valuta in due espressioni di markup (asset events = pubblici).
2. ✅ Cura E1a; `api sync` (slot pesante 2, 14:41–14:51).
   > **Checkpoint e merge** (coordinatore, 14:38–14:40): `c658119af` (rossi E1a), `313dde70e` (E1c), `87a034a89`
   > (journal); merge di `dev_release2` a `ec0dc7ebd` (H CP6, X FE5b, `cryptography`, la 1.2.1) committato come
   > `06459c1b3`. Conflitti risolti da me e messi in stage: `themeRoles.baseline.tsv` (`--resolve`; poi `--check` rosso
   > sul caso R-8, `themeStore.ts` `#166534`; `--accept` con la ragione D3 autorizzata dal coordinatore colori; poi
   > pulito, `~accept` una sola volta; unione esatta dei due lati) e il backlog (la nota di chiusura di W-B15 più le mie
   > W-B17…W-B24). Uniti da soli e controllati: `api/v1/brokers.py` (i tipi dei report in linea; le righe `as_of`
   > lontane), `.translate-hashes.json` (il JSON si legge, nessuna chiave cambiata dai due lati, lo stamp di N1 c'è),
   > `_backend_services.py` (compila; `orphan-transfer-numbers`, `asset-event-store` e la `fx-catalog` di X).
   > **Slot pesante 2** (`nice -n 10`, una cosa alla volta; `LIBREFOLIO_TEST_STARTUP_TIMEOUT=1200` sui comandi con il
   > server): `db populate --force --clean` verde; **`api assets-events` sui rossi: 18 rossi, 19 verdi** (14:44, la build
   > dentro l'avvio), ognuno per la ragione voluta (dettaglio stringa, 200 al posto di 400/422, il 500 di I-09 alla
   > rilettura, `mode` campo sconosciuto, niente `event_ids`, cancellazione non limitata all'asset). **Cura** (14:44,
   > `/tmp/libreFolio_w_e1a_fix.py` e `/tmp/libreFolio_w_e1a_fe.py`, la riga della cancellazione nell'editor): `ruff`
   > (un C416 corretto: `dict(...)`), `black` puliti; `services asset-event-store` **40/40**, `services
   > asset-source-guards` **29/29**; `api sync`: l'OpenAPI cambia solo nelle descrizioni del tipo, `FAEventUpsert.mode`,
   > `FAEventUpsertResult.event_ids` e `asset_id` **obbligatorio** sulla `DELETE` (la sola rottura); `front build
   > --debug` verde, **svelte-check 0 errori e 0 avvisi** (verifica anche gli import di tipo di `WizardFooter` di
   > FE8a-3); `api assets-events` **37/37**. In corso: `all-backend` (14:51); gli E2E che chiamano la `DELETE` degli
   > eventi senza `asset_id` li aggiusta il test-author (solo modifiche).
   > **E2E per la rottura del 21** (test-author, 14:55, solo modifiche; poi rivisti da me): `asset_id` aggiunto alle tre
   > chiamate `DELETE` dei test — `tx-bulk-promote-cost-basis.spec.ts` (gli eventi posseduti ora con il loro asset,
   > `events: [{id, assetId}]`; l'asserzione `deleted` uguale), le pulizie di `asset-event-delete.spec.ts:203–205` e di
   > `asset-data-editor.spec.ts:472`; due commenti di `asset-data-editor.spec.ts` (S1, :584–587 e :608–610) riallineati.
   > Invariati, perché la `DELETE` dell'editor la osservano soltanto: `asset-event-delete.spec.ts:176,253` (il predicato
   > sull'URL combacia anche con `?asset_id=…&ids=…`; lo `status === 200` ora prende anche un editor che dimenticasse
   > `asset_id`) e `asset-data-editor.spec.ts:614`. Nessun'altra `DELETE` degli eventi nei test del frontend; nessun test
   > fissa il `detail` stringa dell'upsert (`portfolioMutation.test.ts:16` classifica solo il percorso). `prettier
   > --check` pulito sui file toccati.
   > **⚠️ Fuori pista — la mini-modale con il `detail` oggetto** (segnalato dal test-author): `EventCreateMiniModal.svelte`
   > mostrava `err.response.data.detail` così com'era, e dopo E1a un rifiuto avrebbe scritto «[object Object]» nel
   > banner. Correzione ponte, accoppiata alla mia rottura: il banner legge `detail.message` (o la stringa, se il
   > `detail` è ancora una stringa), cioè lo stesso testo inglese di prima senza il codice davanti. E1b la sostituisce
   > con l'errore tradotto: l'ancora di `/tmp/libreFolio_w_e1b_fix.py` riallineata, dry run ok. L'editor non cambia: legge
   > solo `e.message` di Axios, come prima.
   > **Prove dello slot 2, revisione combinata** (HEAD `06459c1b3` + E1a e i ritocchi sopra, `nice -n 10`, una alla volta):
   > `all-backend` **7/7 gruppi verdi** (14:51–15:27; 14 609 passati, 28 saltati, 0 rossi: servizi 7 627, utilità 2 369,
   > schemi 1 705 con 6 avvisi preesistenti di `test_pac_planner_schemas.py`, API 1 120, db 16/16 compresi
   > `post-migration-event-types`, `post-migration` 41 e `post-migration-orphan-pairs` 47); Vitest `front-utility
   > core-unit` **4 537/4 537** (144 file, con i cancelli dei colori e quello del denaro), `component-unit` **3 240/3 240**
   > (con `ImportWizardModal.test.ts` di FE8a-3), `front-transaction tx-unit` **903/903**; `test db populate --force
   > --clean`; `front build --debug` (dopo il ritocco della mini-modale) con **svelte-check 0 errori e 0 avvisi**;
   > `front-transaction all --workers 4` **337/337** su desktop (43 spec, compresi FE8a, `tx-event-picker` e
   > `tx-bulk-promote-cost-basis` con `asset_id`) e 34 su mobile (32 saltati per disegno), 15:36–15:51.
   > E2E con `--workers 2` (15:51–15:58): `front-asset asset-data-editor` **26**, `front-asset asset-event-delete` **4**,
   > `front-broker detail` **37**, `front-broker list` **9**, `front-user account-deletion` **1**, `front-utility
   > onboarding-tour` **10**; nessun rosso né flaky. Porta 6184 libera; slot pesante restituito al coordinatore (15:58).
   > **Doc di E1a** (docs-writer, solo EN, pagine sviluppatore senza traduzioni): `developer/backend/assets/events.md`
   > (§ Manual Events: tutto o niente, `mode`, `event_ids`, i rifiuti con stato e `params`, il tipo, la `DELETE` con
   > `asset_id`), `developer/backend/assets/architecture.md` (tabella degli endpoint), `developer/frontend/components/
   > core-ui/data-editor.md` (la `DELETE`). Le pagine utente aspettano E1b.
   > **Fatto** (16:00–16:05): la doc come sopra (rivista da me; il docs-writer non ha lanciato nulla). Dai suoi reperti:
   > tre descrizioni dello schema che finiscono nell'OpenAPI erano rimaste al contratto vecchio — `FAEventUpsertPoint`
   > (docstring e `id`: senza id si confronta su data e tipo solo in un elemento `upsert`; in un `create` si aggiunge),
   > `FAEventDeleteItemResult` (`not_found`: anche un evento di un altro asset, che resta) e
   > `FAEventBulkDeleteResponse.not_found_count` — corrette; `ruff`/`black` puliti; `api sync` di nuovo: nel client
   > generato cambiano solo quelle tre descrizioni. `mkdocs build` stretto verde, nessun avviso (47 s; 3 028 URL
   > relativi risolti), `mkdocs check-links` 95 validi. `git diff --check` pulito; porta 6184 libera.
   > Restano fuori, annotati dal docs-writer: «+ Nuovo evento» non usa ancora `create` (E1b); il caso limite di un
   > `create` rifiutato da un evento scritto da un elemento precedente della stessa richiesta (gli `existing` mostrano
   > un id che il rollback toglie: solo detto nella pagina); `assets_pricing.md:119` incompleta (non nomina `create`) e
   > la frase vecchia «sync replaces» di `architecture.md`, non mia: nella doc di E1b.
3. ✅ Rossi e cura E1b (2026-10-15, 16:40–17:59; dettagli sotto).
   > **Rossi scritti in staging, non eseguiti** (test-author, ~16:00; il worktree resta fermo per l'ingresso di E1a):
   > `/tmp/libreFolio_w_e1b_tests/` con `frontend/e2e/transactions/tx-event-create-exists.spec.ts` (8 test, la
   > mini-modale), `frontend/e2e/assets/asset-event-editor-save.spec.ts` (3: prima le cancellazioni, la valuta della
   > riga, il rifiuto con il toast — quest'ultimo guardia verde oggi), `eventSaveError.test.ts` (42, Vitest node),
   > `EventExistsPanel.test.ts` (7, jsdom), e le copie con le registrazioni (solo aggiunte) di `_frontend_transaction.py`
   > (`tx-event-create-exists`), `_frontend_asset.py` (`asset-event-editor-save`), `_frontend_utility.py` (i due Vitest
   > in `core-unit` e `component-unit`). Un evento del fornitore su un asset proprio, senza stato condiviso:
   > `scheduled_investment` con un DIVIDEND pianificato e `POST /assets/prices/sync` (calcolato in locale).
   > **Reperti da sistemare nella cura**: (1) bozza: «Modifica questo» porta `1.500000` a `1.5`, non `1.50` — usare la
   > stessa funzione del pannello (`amountText`) anche nel form; (2) I-10 fissato con un cambio di tipo, perché l'editor
   > non cambia la data di una riga salvata (`DataEditor.svelte:163-179`); (3) **prima le cancellazioni** = un salvataggio
   > che cancella e ha un upsert rifiutato lascia le cancellazioni fatte (due richieste): da dichiarare al coordinatore
   > (il 22 parla della richiesta bulk), lo stato resta coerente col DB; (4) codici sconosciuti: frase generica col
   > messaggio inglese; (5) il picker tiene in cache la lista per asset/data/intervallo: dopo «Modifica questo» che
   > cambia note o importo potrebbe mostrare i valori vecchi — da verificare in `AssetEventPicker.svelte`
   > (`fetchEvents`, :115); (6) l'editor E2E semina due chiusure per asset (senza prezzi il pulsante non ha test id);
   > (7) le chiavi i18n nuove (`/tmp/libreFolio_w_e1b_i18n.sh`).
   > **Decisione sul salvataggio dell'editor** (coordinatore, 16:20, sulla mia domanda): **no** alle due richieste. La
   > decisione 22 del developer è «tutto o niente e se fallisce ti dice dove», e cancellazioni fatte con un upsert
   > rifiutato la rompono per l'utente. L'API degli eventi cambia già nella 1.3 (`asset_id`), quindi **`delete_ids` nella
   > richiesta di upsert**: prima le cancellazioni, poi gli upsert, in una sola transazione con un solo commit (I-10
   > continua a funzionare, il salvataggio è atomico). La `DELETE` separata resta per l'eliminazione semplice. In E1b,
   > con i rossi prima: da decidere nel disegno come si dice un evento cancellato in uso (oggi `in_use` per riga, non un
   > errore) dentro un salvataggio tutto o niente.
   > **Disegno di E1b aggiornato** (16:50):
   > - **Backend, `delete_ids`** (`FAEventUpsert`, per elemento, cioè per asset): solo in `mode: "upsert"` (in un
   >   `create` → 422); un id sia in `delete_ids` sia fra gli eventi dell'elemento → 422; un elemento con soli
   >   `delete_ids` è valido (`events` può essere vuoto se ci sono cancellazioni; né l'uno né l'altro → 422). In
   >   `_write_manual_item`, **prima** dei controlli sugli eventi: ogni id deve essere un evento **manuale di quell'asset**,
   >   altrimenti 400 `EVENT_NOT_DELETABLE` (`params.ids`; come `EVENT_NOT_EDITABLE` per le modifiche: un id che non c'è più
   >   non si ignora); un evento collegato a transazioni → 409 `EVENT_IN_USE` (`params.events`: `id`, `date`, `type`,
   >   `linked_transactions` — solo il conteggio, nessun id di transazioni di altri utenti); poi la cancellazione e il
   >   flush, così i controlli di chiave e il `create` vedono le chiavi liberate (I-10 dentro una richiesta). Il risultato
   >   aggiunge `deleted_ids`. La `DELETE` separata resta com'è (eliminazione semplice, `in_use` per riga).
   > - **Editor**: un'unica `POST` con `delete_ids` ed eventi; niente più `DELETE` nel salvataggio; alla riuscita toglie
   >   le righe cancellate; al rifiuto nessuna modifica, e il messaggio tradotto nomina la riga (anche l'evento in uso).
   >   Cambia per l'utente: prima un evento in uso veniva saltato con un avviso e il resto salvato; ora il salvataggio non
   >   parte e dice quale evento è in uso (decisione 22).
   > - **Mini-modale**: come la bozza, più il reperto (1): `existingAmountText()` in `eventSaveError.ts`, usata dal
   >   pannello e da «Modifica questo».
   > - **Picker** (reperto 5, verificato: `fetchEvents` esce se `fetchKey` non cambia, `AssetEventPicker.svelte:115-118`;
   >   un evento nuovo arriva come `pinnedEvent`, ma dopo «Modifica questo» il picker trova la copia vecchia in `events`):
   >   il picker si registra sul bus `registerPortfolioMutationListener` (`portfolioMutation.ts`, già notificato
   >   dall'interceptor per ogni `POST`/`DELETE` su `/assets/events`) e rilegge la lista; chiave per istanza, tolta
   >   all'uscita.
   > - i18n (sorgente `assets`, condivisa: solo aggiunte): `events.saveError.inUse`, `events.saveError.notDeletable` oltre
   >   alle chiavi della bozza.
   > **Rossi, seconda tornata** (test-author, 16:40; i file della prima copiati dallo staging: i 4 nuovi tali e quali,
   > `_frontend_transaction.py` intero perché solo aggiunte, le aggiunte di `_frontend_asset.py` e `_frontend_utility.py` a
   > mano, perché le copie in staging erano di prima del merge e avrebbero tolto le registrazioni di Z1 e A5b):
   > `test_asset_event_store.py` +19 casi, `test_assets_events.py` +8, `asset-event-editor-save.spec.ts` riscritto (4: una
   > sola `POST` con `delete_ids`; la riga EUR; l'evento in uso con un'altra modifica → 409 e nulla salvato; il conflitto,
   > guardia), ritarati `asset-event-delete.spec.ts` (scenario 1: la `POST` con `delete_ids`; scenario 2: l'evento in uso
   > rifiuta il salvataggio) e `asset-data-editor.spec.ts` S1 (nessuna `DELETE` né `delete_ids`; guardia), il picker con le
   > note nuove dopo «Modifica questo» in `tx-event-create-exists.spec.ts`, i Vitest (`EVENT_IN_USE`, `EVENT_NOT_DELETABLE`,
   > `existingAmountText`). **Visti** (16:43, `nice -n 10`, senza server): `services asset-event-store` **17 rossi / 42
   > verdi**, tutti per il campo `delete_ids` sconosciuto o per `events` vuoto rifiutato; i due Vitest rossi al caricamento
   > (moduli assenti). API ed E2E sui rossi: slot chiesto al coordinatore (16:45). Cura pronta, non applicata:
   > `/tmp/libreFolio_w_e1b_backend_fix.py`, `/tmp/libreFolio_w_e1b_fix.py` (editor con una sola `POST`),
   > `/tmp/libreFolio_w_e1b_picker_fix.py`, `/tmp/libreFolio_w_e1b_i18n.sh`; tutti in dry run ok.
   > Non fissati (test-author): id ripetuti in `delete_ids` (la cura: 422), quale codice vince fra non cancellabile e in
   > uso (la cura: prima `EVENT_NOT_DELETABLE`), l'ordine di `params.ids` (la cura: ordinati). Rischio noto lasciato com'è:
   > lo scenario 1 di `asset-event-delete` scrive su Apple condivisa a una data fissa (desktop e mobile insieme potrebbero
   > sovrascriversi).
   > **Rossi API ed E2E visti** (slot pesante 2, 16:47–17:06, `nice -n 10`, `--workers 2` per le E2E): `api
   > assets-events` **8 rossi / 37 verdi** (422 per `delete_ids` sconosciuto o `events` mancante); `front-asset
   > asset-event-editor-save` **3 rossi + 1 guardia verde** (nessun `delete_ids` nella richiesta; la riga EUR mandata in
   > USD; l'evento in uso: 200); `asset-event-delete` **2 rossi** (i due scenari ritarati: nessuna `POST` entro 10 s) **+ 2
   > verdi** (non toccati); `asset-data-editor` **26 verdi** (S1 guardia); `front-transaction tx-event-create-exists` **8
   > rossi**. **⚠️ Fuori pista**: il test dell'evento del fornitore era rosso nella **precondizione** (la sync non scriveva
   > il DIVIDEND pianificato: `events_fetched 0`). Causa (test-author): una sync non scrive mai un evento del fornitore con
   > la data di oggi — la storia si ferma a ieri (`refresh.py:227`, `history_end`) e il punto di oggi viene da
   > `get_current_value`, senza eventi. Il test ora data l'evento e il form a ieri (helper `setFormDate`); rilanciato da
   > solo (17:04–17:06): **rosso al punto voluto** (il pannello non compare, `:476`). Il comportamento del prodotto (un
   > evento pianificato con la data di oggi arriva solo il giorno dopo) è di `services/assets/` (X): segnalato al
   > coordinatore, non mio.
   > **Cura applicata** (17:06–17:10): `/tmp/libreFolio_w_e1b_backend_fix.py`, `/tmp/libreFolio_w_e1b_fix.py`,
   > `/tmp/libreFolio_w_e1b_picker_fix.py` (`--apply`), le 18 chiavi i18n (`/tmp/libreFolio_w_e1b_i18n.sh`: 16 in
   > `assets`, `transactions.form.eventEditTitle`; nelle 4 lingue, solo aggiunte), `api sync` (il client cambia in
   > `delete_ids`, `deleted_ids`, `events` facoltativo e la docstring), `ruff`/`black` puliti, `prettier --write` sui due
   > componenti (solo rientri del blocco `{#if existing}`). **Verdi** (17:10–17:29, `nice -n 10`): `theme-roles --check`
   > pulito; `services asset-event-store` **59/59**, `asset-source-guards` **29/29**; Vitest `eventSaveError` **57/57**;
   > `front build --debug` con svelte-check **0/0**; `api assets-events` **45/45**; E2E `asset-event-delete` **4/4**,
   > `asset-data-editor` **26**, `tx-event-create-exists` **8/8** (il fornitore e il picker dopo «Modifica questo»
   > compresi), `tx-event-picker` **5/5**; `front-utility core-unit` **4 680/4 680** (151 file, con `eventSaveError` e i
   > cancelli di colori, denaro e ICU), `component-unit` **3 395/3 395**; `i18n check` stretto pulito (4 435 chiavi).
   > **⚠️ Fuori pista** (2): (1) `EventExistsPanel.test.ts` 8/8 rosso dopo la cura per un errore del test (`events` è
   > anche un'opzione di montaggio di Svelte: le props vanno sotto `props`): corretto dal test-author, poi **8/8**. (2)
   > `asset-event-editor-save` **3/4**: il test 3 (evento in uso più un'altra modifica) fallisce **sempre** al cambio di
   > tipo, prima e dopo la cura e anche da solo (17:29–17:31): l'opzione `SPLIT` della tendina è coperta dall'intestazione
   > fissa della tabella (`thead.sticky-header … intercepts pointer events`). Quindi il suo rosso «prima» non era quello
   > voluto (avevo letto male il riepilogo: il comportamento rosso dell'evento in uso è visto all'API, 409 contro 422, e
   > nello scenario 2 di `asset-event-delete`). Causa, un difetto del prodotto fuori da E1b: la tendina di `SimpleSelect`
   > è `fixed z-[9999]` ma non portata nel `body`, e dentro la tabella resta sotto la `th` fissa (`z-index: 15`,
   > `DataTable.svelte:1621`) quando si apre verso l'alto vicino all'intestazione → **W-B26** nel backlog. Il test 3 cambia
   > l'importo invece del tipo (test-author), poi lo rilancio.
   > **Rilanciato** (17:34–17:35): `asset-event-editor-save` **4/4**. Il test 3 non ha avuto il suo rosso E2E per la
   > ragione voluta; il comportamento resta visto rosso all'API e nello scenario 2. `prettier --check` pulito su specs,
   > test e componenti; `ruff`/`black` puliti sui test; `git diff --check` pulito. **Slot pesante 2 restituito** (17:36),
   > porta libera. Resta: doc di E1b (docs-writer), `mkdocs build` e `check-links` (chiesti), handoff.
   > **⚠️ Fuori pista — una regressione mia, trovata dal docs-writer** (17:50): l'editor offre ancora «Elimina» sulle righe
   > del fornitore (sola lettura) e ne mette l'id in `delete_ids`; la mia cura rifiutava gli id del fornitore
   > (`EVENT_NOT_DELETABLE`), quindi l'intero salvataggio falliva con un messaggio fuorviante («…non esiste più… ricarica»).
   > Nella 1.2 quella cancellazione riusciva (l'evento torna con la sync successiva, e la doc utente lo diceva); la `DELETE`
   > la permette ancora. **Correzione nel mio perimetro, da dichiarare nell'handoff**: `delete_ids` accetta ogni evento
   > dell'asset, manuale o del fornitore; `EVENT_NOT_DELETABLE` solo per id ignoti, spariti o di un altro asset;
   > `EVENT_IN_USE` per ogni evento collegato. Rossi prima (test-author), poi `/tmp/libreFolio_w_e1b_provider_fix.py`
   > (dry run ok); doc riallineata dal docs-writer. Annotati per l'handoff, non curati: il prefisso inglese «Save failed» e
   > le date ISO dell'editor (righe di X), il tipo in minuscolo nel CSV (l'editor confronta con le maiuscole; il server poi
   > normalizza), le chiavi `events.deleteBlocked`/`deleteNotFound` non più usate, tre pagine sviluppatore da aggiornare
   > (`transaction-form.md`, `domain-state.md`, la frase dei range nel `data-editor.md`).
   > **Correzione fatta** (17:52–17:55): rossi (test-author: un test del fornitore cancellato come un manuale, uno del
   > fornitore in uso → `EVENT_IN_USE`; il test dei non cancellabili senza il fornitore) **visti: 2 rossi / 59 verdi**
   > (17:54); poi `/tmp/libreFolio_w_e1b_provider_fix.py --apply` (`_delete_item_events`, il filtro sul fornitore tolto,
   > messaggi e docstring) → `services asset-event-store` **61/61**, `asset-source-guards` **29/29**, `ruff`/`black`
   > puliti, `api sync` (solo descrizioni), `api assets-events` **45/45** (17:59). Il frontend non cambia: l'editor mandava
   > già quegli id.
4. ✅ E1c (14:35): rossi visti → cura → verdi; commit a parte.
   > **Rossi scritti, non eseguiti** (test-author, 14:10, carico alto): nuovo
   > `test_db/test_post_migration_event_types.py` (20 funzioni, 35 casi: 33 rossi attesi, 2 guardie), nessun import dai
   > test di N1b-2, `FIXES` controllato solo per `fix_id`; azione `db post-migration-event-types` in `_backend_db.py`,
   > su righe proprie lontane da quelle di N1b-2 (anche in `db_order`, come prima riga). Più un perno chiesto dopo:
   > un `row_count_changes` che solleva → `failed`, non un'eccezione.
   > **Correzioni alla cura** dalla revisione del test-author: `FIXES` riconosciuto per forma (con o senza N1b-2);
   > `row_count_changes()` chiesto dentro il `try` di `_apply_one`; la docstring del modulo `__init__.py` (punto 4: era
   > ferma a «foreign_key_check vuoto», già superata da N1b-3); docstring in inglese; raggruppamento in un passaggio.
   > Resta, dichiarato: l'import di `event_types` confina con quello di N1b-2 (conflitto banale se N1b-2 non entra); la
   > parte della cura su `_common_problems` sta sulle righe di N1b-3.
   > **Rossi visti** (14:33, `nice -n 10`, un file, senza server): `db post-migration-event-types` **34 rossi, 2 guardie
   > verdi**, ognuno sull'asserzione prevista (A.1 `row counts changed`; A.2 solo sulle parole; A.4 nessun `boom`;
   > registrazione assente; `event_types` senza esito). **Cura** (14:34, `/tmp/libreFolio_w_e1c_fix.py --apply`):
   > `base.py` `row_count_changes()`; `__init__.py` `_expected_counts()`, i conteggi attesi chiesti dentro il `try`, il
   > messaggio «row counts not as expected: tabella (expected N, found M)», la docstring del modulo, la registrazione;
   > nuovo `event_types.py`. **Verdi**: `db post-migration-event-types` **36/36**; regressione `db post-migration` 41/41,
   > `db post-migration-orphan-pairs` 47/47. Doc (solo EN, `/tmp/libreFolio_w_e1c_docs.py --apply`):
   > `developer/architecture/database/index.md` (passo 5, paragrafo di `event_types`) e `admin/cli_tools.en.md` (due
   > punti per l'amministratore); debito di traduzione in W-B21. `ruff`/`black` puliti.
   > **Via (b) per i rossi API di E1a** (14:29, carico 32,8 alla scadenza): nello slot pesante dopo il merge. La cura E1a
   > resta in `/tmp` fino ad allora; nel worktree ci sono i soli rossi di E1a.
5. ✅ Doc; handoff FROZEN (E1a+E1b; E1c a parte) — E1a ed E1c entrati; E1b handoff alle 18:05.
   > **Doc di E1b** (docs-writer, solo EN, senza stamp, rivista da me): utente `user/assets/detail/data-editor.en.md`,
   > `events.en.md` (nuovo H3 `#new-event`), `user/transactions/form.en.md` («Missing event?»); sviluppatore
   > `developer/backend/assets/events.md`, `architecture.md`, `developer/frontend/components/core-ui/data-editor.md`,
   > `developer/frontend/state/domain-state.md` (il picker sul bus), `developer/frontend/components/features/
   > transaction-form.md`, `developer/architecture/database/assets_pricing.md`. Debito di traduzione → W-B28. **devWiki**
   > (historian): nuove `decisions/asset-event-saves-all-or-nothing.md`, `problems/provider-event-dated-today-not-synced.md`,
   > `problems/select-list-under-the-sticky-table-header.md`, `problems/testing-library-events-prop-read-as-mount-option.md`;
   > aggiornate F-031, F-090, `problems/asset-event-edit-delete-reinsert.md`, `problems/sqlite-savepoint-without-write-
   > begins-as-transaction.md` (W-B20), `domains/assets.md`, `features/registry.md`, `index.md`, `log.md`;
   > `check_source_paths.py` invariato (5). **Prove** (18:00, `nice -n 15`): `mkdocs build` stretto, 0 avvisi (42 s, 3 036
   > URL), `check-links` 95 validi. Porta 6184 libera.
   > **E1a entra da solo** (coordinatore, 16:00, dopo il punto 46): doc sviluppatore di E1a ✅ (passo 2), handoff
   > FROZEN d'ingresso con il CHANGELOG di FE8a, N1, N1b-2/3, E1a ed E1c (16:10). Le pagine utente, la devWiki e il resto
   > con E1b.
   > **Committati** (coordinatore): `a2fb6936f` `fix(events)!: all-or-nothing upsert, scoped delete` (con `BREAKING
   > CHANGE`) e `d7c7dcab7` (journal); il cambio di `detail` in oggetto va sotto ⚠️ Breaking changes, come proposto; il
   > CHANGELOG lo scrive il coordinatore. **Secondo merge di base** (`MERGE_HEAD` `243c8c9ff`: E1, Y1, A5, H C-96 e G-10,
   > Z1, G-9, colori), committato come `15a8355cc`. Conflitti risolti da me e messi in stage: `themeRoles.baseline.tsv`
   > (`--resolve`, `--check` pulito senza ripetere l'`--accept` D3; vince il lato più stretto: 222, 88, 35 per i miei
   > split, GrowthChart 86 uguale) e `_backend_db.py` (in `db_order` sia `post-migration-orphan-pairs` sia
   > `migration-006`; 18 azioni senza doppioni). Rivisti gli uniti da git sui due lati: `test_post_migration.py`,
   > `_backend_services.py`, `cli_tools.en.md`, `database/index.md`, `.translate-hashes.json`, il backlog (`T-B4` doppio
   > già sui due lati, non mio: lo sistema il coordinatore).
   > **Prove sulla revisione combinata `15a8355cc`** (16:12–16:18, `nice -n 10`, una alla volta, lista del coordinatore):
   > `api sync` (393 righe del client cambiate, tutte di account e accessi arrivati col merge: utenti, inviti, token;
   > nessuna mia); `front check` svelte-check **0/0**; `theme-roles --check` pulito; `db post-migration` **41**,
   > `post-migration-orphan-pairs` **47**, `post-migration-event-types` **36**; `db populate --force --clean`; `api brokers`
   > **34**, `api account-deletion` **6**, `api assets-events` **37**; `services broker` **65**, `services config-package`
   > **642**. Porta 6184 libera. Pronto all'ingresso.

### N2 — il costo obbligatorio anche nell'API: TRANSFER ricevuto e ADJUSTMENT in entrata ✅ (2026-10-15) — 🧊 FROZEN

**Richiesta** (coordinatore, 15/10 ~16:30, dopo il punto 46). Il developer, in chat alle 16:12, alla lettera: «sarei
daccordo a metterci una protezione in caso di chiamate dirette dalle api, ma non certo metterci a fare bonifiche o
altro». Lotto piccolo dopo l'ingresso (o dentro E1b):

- il backend applica la regola dei metadati dei tipi, che oggi controlla solo il frontend: `cost_basis_pair`
  `required_qty_pos` per il lato che riceve un `TRANSFER`, `cost_basis_mode` `required_qty_pos` per un `ADJUSTMENT` con
  quantità > 0 (`schemas/transactions/type_metadata.py:286`, `:331`);
- senza modalità di costo la richiesta è rifiutata (422) con un codice chiaro, e il messaggio dice quale riga;
- la regola si legge dai metadati, non si riscrive a mano;
- prima i rossi; i test e le fixture che creano queste righe dall'API senza costo li sistema il test-author;
- **nessuna bonifica**: le righe già salvate restano come sono (`orphan_pair_halves` non cambia);
- una riga del CHANGELOG sotto 🔄 Changed: l'API rifiuta un trasferimento ricevuto o una rettifica in entrata senza
  modalità di costo, come già fa l'app.

**Prima lettura** (da completare nell'analisi): il posto naturale è `validate_transaction_business_rules`
(`schemas/transactions/transactions.py:83`), la funzione pura delle regole 5–12 condivisa da creazione
(`TXCreateItem`) e modifica (il ciclo di `TransactionService`); la regola 12 controlla già dove `cost_basis_mode` è
ammesso. «Un costo» = `cost_basis_override` presente oppure `cost_basis_mode` `auto`/`auto-detail`; oggi la funzione
non riceve `cost_basis_override`. **Da decidere nell'analisi**: la modifica di una riga già salvata senza costo (dati
vecchi, o una metà convertita da `orphan_pair_halves`): rifiutarla finché non ha un costo bloccherebbe anche la
modifica delle sole note via API; il disegno proposto la applica alla creazione e alla modifica che **tocca** tipo,
quantità o costo, e lo verifico contro quello che fanno il modulo e il Bulk.

**Passi**: 1. ✅ analisi e disegno al coordinatore (16:40); 2. ✅ rossi (test-author, 18:43–19:15); 3. ✅ cura (18:52, più il
collegamento all'evento alle 19:16); 4. ✅ prove; 5. ✅ doc; CHANGELOG proposto nell'handoff (19:30).
> **Via a N2** (coordinatore, 18:15, dopo l'ingresso di E1b: `dev_release2` = `fecf88c1a`, CHANGELOG `f0d2c77e2`; il mio
> ramo in pari per avanzamento veloce, HEAD `f0d2c77e2`, pulito). Rossi chiesti a un test-author nuovo (18:16: (a) la
> modifica delle sole note e dei soli tag di un TRANSFER ricevuto e di un'ADJUSTMENT +qty salvati senza costo, (b) i
> metadati come fonte con `TX_TYPE_METADATA` modificato nel test; le guardie). **Cura pronta, non applicata**
> (`/tmp/libreFolio_w_n2_fix.py`, dry run ok): `cost_basis_required(type, quantity)` in `type_metadata.py`, usata da
> `_requires_cost_basis`; `stored_cost_fields` nel contesto del batch, fotografato al caricamento delle righe
> (`_load_existing_transactions`) con `cost_fields(tx)` = tipo, quantità, costo e valuta; `_check_update_cost_basis`
> controlla solo se la modifica cambia quei valori o nomina una `cost_basis_mode`.
> **Rossi visti** (test-author, poi io, 18:43–18:51): nuovo `test_services/test_transaction_cost_basis_rule.py` (azione
> `services transaction-cost-basis-rule`, registrata dopo `transaction`): **10 rossi / 51 verdi** — (a) le modifiche di
> sole note (`description`), soli tag e sola data di un TRANSFER ricevuto e di un'ADJUSTMENT +qty salvati senza costo
> (oggi `costBasisRequired`), (b) `_requires_cost_basis` con un campo dei metadati cambiato nel test (ADJUSTMENT e
> TRANSFER ricevuto resi `optional`, BUY reso `required_qty_pos`) e la creazione senza costo quando i metadati la rendono
> facoltativa; guardie: creazioni rifiutate sulla loro riga, quantità −5→+5 e unità in più senza costo, `manual` senza
> costo, cambio di tipo (con `SWAP_GROUPS` modificato nel test: nessun gruppo reale porta a un tipo che chiede il costo),
> note su una riga con costo, Auto con media (100 EUR), una promozione con modifica delle note nello stesso batch (resta
> rifiutata), parametrico tipo × segno (−, 0, +) uguale ai metadati. API (`test_transactions_batch_split_promote.py`,
> B4.1, dati vecchi scritti con `legacy_cost_rows.main()`): **rossa** (modifica delle sole note rifiutata con
> `costBasisRequired`, update 1 e 2). **Cura applicata** (18:52, `/tmp/libreFolio_w_n2_fix.py --apply`, `ruff`/`black`
> puliti). Reperti del test-author: (1) togliere il costo con una modifica non si può esprimere (`cost_basis_override:
> null` vale «invariato»): il modulo che svuota un costo manuale manda `null` e il backend tiene il vecchio → W-B30; (2)
> la regola 12 di `validate_transaction_business_rules` (`costBasisModeIncompatible`) è una seconda copia scritta a mano
> (TRANSFER e ADJUSTMENT con quantità > 0); leggerla dai metadati porterebbe un import circolare
> (`type_metadata` importa `transactions`) → W-B31.
> **Verdi** (18:52–18:59, `nice -n 10`, una alla volta): `services transaction-cost-basis-rule` **61/61**, `services
> transaction` **66**, `services broker` **65**, `services orphan-transfer-numbers` **19**; `db populate --force --clean`;
> `api batch-split-promote` **36** (B4.1 compresa), `api transactions` **26**, `api transactions-validate` **11**, `api
> transactions-wac` **20**; `test check-orphans` pulito; `git diff --check` pulito; porta libera. Nessuno schema cambiato:
> niente `api sync`, nessun file del frontend toccato. Doc sviluppatore in corso (docs-writer).
> **⚠️ Fuori pista — un buco della mia cura, trovato dal docs-writer** (19:15): `cost_fields()` non contava il
> collegamento all'evento. Un'ADJUSTMENT +qty legata a uno SPLIT e salvata in Auto resta senza costo per disegno
> (`auto_cost.py:70-90`): prima di N2 ogni sua modifica non Auto era rifiutata, dopo la cura una modifica che la
> **scollega** soltanto (`asset_event_id: 0`, quello che manda `buildUpdateDiff`) passava e lasciava un acquisto di costo
> ignoto. Cura: `asset_event_id` dentro `cost_fields()` (cambiare o togliere il collegamento conta come toccare il costo),
> con il rosso prima (test-author); `/tmp/libreFolio_w_n2_link_fix.py` (dry run ok), che toglie anche dalla docstring di
> `cost_basis_required` la frase «l'app e l'API applicano una sola regola» (il modulo sceglie dove mostrare il costo dal
> nome del tipo, `TransactionFormModal.svelte:744`, `TxFormSingleSection.svelte:294,316`). Residui annotati per
> l'handoff, non curati: il testo `warningAdjustment` («non si può salvare senza») e il controllo lato client restano più
> severi dell'API per le righe vecchie; `fieldsFromTx()` del Bulk sceglie il lato dal collegamento e non dal segno.
> **Fatto** (19:15–19:27): test-author, nuova classe `TestSplitLinkedAdjustment` (6 test: la riga legata a uno SPLIT
> costruita come fa l'app, in Auto; scollegarla o legarla a un PRICE_ADJUSTMENT senza costo → rifiutato; note e tag →
> committati; cambio di collegamento con un costo → committato); **rossi visti: 2 / 65 verdi** (scollega, ricollega);
> `/tmp/libreFolio_w_n2_link_fix.py --apply` (`asset_event_id` in `cost_fields`, le docstring); **verdi**:
> `services transaction-cost-basis-rule` **67/67**, `transaction` **66**, `broker` **65**; `api batch-split-promote`
> **36**, `transactions` **26**, `transactions-validate` **11**, `transactions-wac` **20**; `ruff`/`black` puliti; porta
> libera. **Doc** (docs-writer, solo sviluppatore EN, niente stamp): `developer/frontend/data-quality-banner.md:176`,
> `developer/frontend/components/features/transaction-form.md:227-240` (anche due frasi già sbagliate prima di N2: «salta
> solo le creazioni consumate da una promozione», da `d7c148564`; «costo zero», da `bdec709d2`),
> `developer/backend/transactions/wac.md:528-550` e `:655-657`, `split_promote.md:211-212`. **Prove della doc** (19:28,
> `nice -n 15`, carico 36): `mkdocs build` stretto, 0 avvisi (43 s, 3 036 URL), `check-links` 95 validi. `git diff
> --check` pulito. Handoff FROZEN di N2 (19:30).
Ordine dei lotti (coordinatore, 16:30): **E1b, poi N2, poi W-B20**; FE8b sul suo binario. Ogni prova pesante: slot dal
coordinatore. Scopo delle modifiche (coordinatore, 16:30): la regola vale alla creazione e per le modifiche che toccano
tipo, quantità, segno o costo; note, tag e descrizione di una riga vecchia senza costo restano modificabili.

**Analisi** (16:40, letta sul codice di `4a303b50b`) — **la premessa va corretta**: il backend la regola **la controlla
già**, per ogni percorso dell'API.
- `TransactionService.execute_batch` (`transaction_service.py:113-161`) è l'unico percorso di creazione e modifica:
  `POST /transactions/validate`, `/transactions/commit` e `promote-transfer` (`promotion.py:167`, che gli passa
  `creates_raw`). Dopo il WAC gira sempre `validate_cost_basis` (`batch_costs.py:64-215`): creazioni (singole e in
  coppia), modifiche e promozioni senza `cost_basis_override` → issue `costBasisRequired` con `index`, `ref_id`,
  `field: cost_basis_override` e `params.type`; il batch non committa (HTTP 200, `committed: false`, come ogni altro
  rifiuto del batch; la chiave `transactions.errors.costBasisRequired` è già nelle 4 lingue).
- La regola però è **scritta a mano**: `TransactionService._requires_cost_basis` (`validation.py:33-41`, TRANSFER e
  ADJUSTMENT con quantità > 0), oggi uguale ai metadati ma non letta da lì.
- **Le modifiche oggi sono più strette di quanto deciso**: `_check_update_cost_basis` rifiuta **qualunque** modifica di
  una riga che vuole un costo e non l'ha, anche delle sole note. Con N1b-2 queste righe esisteranno (metà convertite
  senza costo): oggi non se ne potrebbero toccare nemmeno le note, né dall'app né dall'API.
- Le righe senza costo nascono, oltre che dai dati vecchi e dalle due conversioni di N1: dalla modalità **Auto** quando
  la media non esiste (pool vuoto, P-1: `_write_auto_cost` non scrive nulla e il controllo salta le righe Auto;
  `auto_cost.py:143-148`) e dalle ADJUSTMENT legate a uno SPLIT (per disegno: il costo viene dal rapporto dello split,
  `auto_cost.py:70-90`). Non dall'API «senza modalità».

**Disegno proposto**:
1. Un'unica funzione che legge i metadati: `cost_basis_required(type, quantity)` vicino a `TX_TYPE_METADATA`
   (`type_metadata.py`): per un tipo in coppia `cost_basis_pair[1 if quantity > 0 else 0]`, altrimenti
   `cost_basis_mode`; `required_qty_pos` con quantità > 0 → richiesto. `_requires_cost_basis` la chiama (stesse
   risposte di oggi su ogni tipo: perno parametrico su tutti i `TransactionType` × segno).
2. `_check_update_cost_basis` controlla solo le modifiche che **cambiano** tipo, quantità (segno compreso) o costo
   (`cost_basis_override`, la sua valuta, `cost_basis_mode`) rispetto alla riga salvata: confronto dei valori, non dei
   campi presenti, così vale sia per il diff dell'app (`buildUpdateDiff`) sia per un client che manda la riga intera.
   Serve lo stato salvato prima della modifica (da prendere in `apply_updates` o nel contesto).
3. Fuori da N2: l'Auto senza media (P-1) e lo split, come oggi.

**Rossi previsti** (test-author, `services transaction`/`api` del batch): (a) la modifica delle sole note (e dei soli
tag) di un TRANSFER ricevuto e di un'ADJUSTMENT +qty salvati senza costo → oggi `costBasisRequired`, dopo committata;
(b) i metadati come fonte: con `TX_TYPE_METADATA` modificato nel test (ADJUSTMENT `optional`) la creazione senza costo
passa → oggi rossa (regola a mano). Guardie verdi oggi: creazione senza costo rifiutata con `index`; modifica che porta
la quantità di un'ADJUSTMENT da −5 a +5, o cambia il tipo, senza costo → rifiutata; modifica che toglie il costo →
rifiutata; Auto con media → committata; parametrico tipo × segno = metadati.

**CHANGELOG** (riga corretta, la tua presupponeva un'API che accetta): 🐛 Fixed — «Editing only the notes, tags or
description of a transfer received or of an incoming adjustment saved without a cost basis is no longer refused; a
change to its type, quantity or cost still needs one.»

### Coda dei lotti dopo E1b (coordinatore, 15/10 16:30 e 18:02)

- **E1b committato** (coordinatore, 18:05): `af4408608` feat(events), `0ffaa9127` docs(events), `a62d36062` docs(wiki),
  `5749cef7d` docs(journal); base aggiornata con `dev_release2` `a718e5281` (J, A6a, H, Z7a, il banner del Lab) senza
  conflitti → HEAD `949ab6bea`. **Prove sulla revisione combinata** (18:03–18:11, `nice -n 10`, una alla volta): `api sync`
  (157 righe del client, tutte di A6a e H: anteprima di cancellazione dell'account, sonda dell'indirizzo; nessuna mia);
  `front check` svelte-check **0/0**; `services asset-event-store` **61/61**; `db populate --force --clean`; `api
  assets-events` **45/45**; Vitest `eventSaveError` **57/57**, `EventExistsPanel` **8/8**; E2E `asset-event-editor-save`
  **4/4**, `tx-event-create-exists` **8/8**; `i18n check` stretto pulito (4 440 chiavi); `theme-roles --check` pulito;
  `test check-orphans` pulito. Porta 6184 libera. Pronto all'ingresso.
- Ordine: **N2** (dopo l'ingresso, non prima) → **W-B20** (l'aiuto in `db/session.py` per `delete_bulk`) → **A-14** (da A:
  in `mkdocs_src/docs/developer/architecture/access_control.md` la frase «The last OWNER cannot remove themselves»
  contraddice la sezione «Self-Management» e `leave_broker`: correggerla secondo il codice). FE8b sul suo binario.
- Il rischio di Apple condivisa a data fissa in `asset-event-delete` → **W-B29** nel backlog W.
- **Coda aggiornata** (coordinatore, 18:15): N2 → **i file dei broker visibili solo a chi ha la vista sul broker**
  (decisione 36, `Phase_1/decisioni-analisi-20261014.md` § 36: «File dei broker (report, estratti): lista, anteprima e
  scarico solo a chi ha almeno la vista su quel broker»; i file comuni e personali sono di Piattaforma, registrazione e
  impostazioni di Account e accessi) → W-B20 → A-14. W-B26 lo assegna il coordinatore.
  > **Prima lettura per la decisione 36** (18:59, solo lettura): le rotte BRIM dei file (`api/v1/brokers.py:653-870`:
  > lista, info, anteprima, scarico, ultimo parse, controllo del plugin, parse, cancellazione) controllano già l'accesso
  > al broker con `_get_brim_file_with_access` (`:120-140`) e la lista filtra per broker accessibili. **Ma** il controllo
  > c'è solo `if file_info.target_broker_id and not current_user.is_superuser`: un file **senza** `target_broker_id` è
  > aperto a ogni utente con il login, anche la cancellazione (il `min_role=EDITOR` salta) — W-B3 confermata. Da
  > chiarire nell'analisi: quando nasce un file senza broker, chi l'ha caricato (se è registrato), e cosa fa la lista.

### F36 — i file dei broker solo a chi ha la vista sul broker (decisione 36, W-B3) ✅ (2026-10-15) — 🧊 FROZEN

**Richiesta** (coordinatore, 19:28 e 19:31; decisione 36 del developer, approvata il 15/10): «**File dei broker**
(report, estratti): lista, anteprima e scarico solo a chi ha almeno la vista su quel broker». I nomi dei broker restano
visibili a tutti. I file comuni e personali sono di H: accordarsi sull'elenco e sullo scarico. Lotto dopo N2, prima di
W-B20. `backend/app/main.py` congelato fino al CP2b di H (questo lotto non lo tocca).

**Analisi** (19:40, letta sul codice di `f8e0a9b35`):
- Le rotte dei report sono `brim_router` in `backend/app/api/v1/brokers.py` (`/api/v1/brokers/import/…`). Il caricamento vuole un
  broker con EDITOR (`:577-601`); la lista (`:653-684`) filtra per broker accessibili; info, anteprima, scarico, ultimo
  parse, controllo del plugin (VIEWER+) e parse, cancellazione (EDITOR) passano da `_get_brim_file_with_access`
  (`:120-140`). I set (`/sets/preview`, `/sets/combine`), `/gap-fix` e `/duplicates` vogliono EDITOR sul broker e leggono
  solo i file di quel broker (`brim_report_sets.py:128`, `target_broker_id == broker_id`).
- **Il buco (W-B3, confermata)**: i file **senza broker** (cartella radice di ogni stato in `broker_reports/`, «backward
  compatibility»: caricati da versioni vecchie) li vede e li tocca chiunque abbia il login.
  `_get_brim_file_with_access` controlla solo `if file_info.target_broker_id and not current_user.is_superuser`, quindi
  per loro salta tutto, anche la cancellazione e il parse (EDITOR); `brim_provider.list_files` (`:1068-1070`) li aggiunge
  a ogni lista filtrata per broker («files without broker_id (legacy)»).
- `BRIMFileInfo` registra `uploaded_by_user_id`: per i file senza broker si sa chi li ha caricati.

**Accordo con H** (19:45): H tocca la pagina File (`routes/(app)/files/+page.svelte`), `FilesTable` e
`FilePreviewModal` per lo scopo dei suoi file; **io nessun file del frontend**. Stessa regola dei suoi file personali per i
miei report senza broker: **chi li ha caricati e l'admin**. H propone `can_delete: bool` per voce dell'elenco (lo mette su
`/uploads`; la tabella nasconde «elimina» quando è falso): lo aggiungo all'elenco BRIM. Codici: `/uploads` risponderà
404 a chi non può vedere; i report restano a **403**, come oggi e come fissano i test (`test_brim_api.py:809,948`, RS-006,
GF-007): H lo scrive così nella doc. `services/files/file_preview.py` resta condiviso e puro; il controllo resta nelle rotte.

**Disegno proposto**:
1. `_get_brim_file_with_access`: per chi non è admin, un file con broker come oggi (ruolo ≥ `min_role` sul broker, altrimenti
   403); un file **senza** broker solo a chi l'ha caricato (`uploaded_by_user_id`), altrimenti 403, anche per anteprima,
   scarico, ultimo parse, controllo del plugin, parse e cancellazione.
2. Lista: per chi non è admin, i file dei broker con almeno la vista e quelli senza broker caricati da lui; per l'admin
   come oggi. `list_files` del provider non cambia: il filtro sul caricatore lo fa la rotta.
3. `can_delete` sulle voci dell'elenco (`BRIMFileListItem(BRIMFileInfo)`, solo nella risposta, non nel file di metadati):
   admin; EDITOR/OWNER sul broker (`get_accessible_broker_ids(min_role=EDITOR)`); il caricatore per un file senza broker.
   `api sync` (campo aggiunto).
4. Facoltativo, da W-B4 (stessa superficie): rifiutare con 404 un `file_id` che non è un UUID, prima di cercarlo.
5. Nessuna bonifica: i file senza broker restano dove sono; chi li ha caricati e l'admin li vedono ancora.

**Rossi previsti** (API, `test_brim_api.py`, con un file senza broker scritto nella cartella radice della corsia come una
versione vecchia, `uploaded_by_user_id` = U): per V (né U né admin) lista senza il file, info/anteprima/scarico/ultimo
parse/controllo del plugin/parse → 403, cancellazione → 403 e il file resta (oggi 200 e cancellato); `can_delete` assente
oggi. **Guardie**: U e l'admin vedono e cancellano il file senza broker; sui file con broker VIEWER vede ma non cancella
né fa il parse, chi non ha accesso riceve 403, EDITOR/OWNER cancella; `can_delete` falso per VIEWER, vero per
EDITOR/OWNER, caricatore e admin.

**Per l'utente**: chi condivideva un'istanza smette di vedere i report caricati da altri senza broker (versioni vecchie);
li vedono chi li ha caricati e l'admin. CHANGELOG all'ingresso.

**Passi**: 1. ✅ analisi al coordinatore (19:46; **via** alle 19:40: disegno approvato, i file senza broker solo al
caricatore e all'admin, `can_delete` nel modello di risposta con `api sync` dichiarato, **W-B4 dentro**, nessuna bonifica;
prove mirate una alla volta, `all-backend` nello slot da chiedere, `front check` dopo `api sync`); 2. ⏳ rossi
(test-author, 19:48); 3. cura (pronta, non applicata: `/tmp/libreFolio_w_f36_fix.py`, dry run ok: `BRIMFileListItem`,
`_is_brim_file_id`, `_get_brim_file_with_access` e la lista); 4. prove; 5. doc (`developer/…` sui file BRIM, `user/…` se
dice chi vede i report) e handoff.
> **Rossi visti** (test-author, Categoria 18 di `test_api/test_brim_api.py`, righe 2770–3371; azione `api brim` con
> `TestReportsWithoutBroker TestReportsOfABroker TestListCanDelete TestFileIdsAreUuids`; 20:12–20:14, dopo `db populate`
> perché i test dell'admin entrano con `e2e_test_admin`): **14 rossi / 10 verdi**, come previsto — il file senza broker
> (nella radice di `uploaded/`, scritto come una versione vecchia, con il lock `.locks/broker_none.lock`) nella lista di un
> altro utente (3 casi), 200 su info/anteprima/scarico/ultimo parse/controllo del plugin/parse/cancellazione per un altro
> utente (7), il file senza broker e senza caricatore aperto a tutti, `can_delete` assente, un id di 300 caratteri → **500**
> su tutte le rotte (pathlib «file name too long»), un file chiamato `<uuid>-1` servito con 200; guardie: caricatore e
> admin vedono e cancellano, VIEWER legge ma né parse né cancellazione, chi non ha accesso 403, EDITOR cancella, id non UUID
> semplici già 404.
> **⚠️ Fuori pista — `/parse` e il broker del corpo** (test-author, 20:05; incluso dal coordinatore alle 20:15): `POST
> /files/{id}/parse` non controlla il `broker_id` del corpo, contro cui confronta duplicati e storia dei set: un EDITOR del
> broker del file poteva lavorare su un broker che non vede. Cura: `_require_broker_editor(request.broker_id, …)`, come
> `/duplicates`; rosso prima (test-author). Aggiunta a `/tmp/libreFolio_w_f36_fix.py` (dry run ok).
> **Rossi di `/parse`** (`TestParseTargetBroker`, 20:20–20:21): **2 rossi / 2 verdi** (EDITOR di A che fa il parse nel
> broker B dove è VIEWER o senza ruolo: oggi 200, la risposta e la cache con B; guardie: il parse in A, l'admin in B).
> **Cura applicata** (20:21): `/tmp/libreFolio_w_f36_fix.py --apply`; `ruff`/`black` puliti; `api sync` (nuovo
> `BRIMFileListItem` con `can_delete` obbligatorio; `GET /files` lo usa). **Verdi**: `api brim` **115/115** (20:22–20:31,
> le 28 della Categoria 18 comprese). `front check`: **1 errore**, un mock di `ImportWizardModal.test.ts:307` senza
> `can_delete` (il client valida le risposte con Zod, `validate: 'response'`; nessuna E2E finge la lista): riparazione al
> test-author.
> **Riparato** (test-author: `can_delete: true` sull'unica voce finta della lista in `ImportWizardModal.test.ts:315`; gli
> altri mock di quel file non hanno voci; `defaultPluginCheck.test.ts`, `ParseDetailModal.test.ts` e `FilesTable.test.ts`
> non fingono la lista) → `front check` svelte-check **0/0**, Vitest `ImportWizardModal.test.ts` **26/26** (20:44).
> **Pausa delle prove** (coordinatore, ~20:45, carico 89, galleria di DV): nulla in esecuzione, «fermo». Restano dopo la
> ripresa: le E2E mirate sulla lista dei report (`tx-import-file-selection`, `files`), la doc (docs-writer in corso),
> `mkdocs build` e `check-links`, poi `all-backend` nello slot del coordinatore.
> **Doc** (docs-writer, 20:58; solo EN, senza stamp): `developer/backend/brim/architecture.md` (riga dei campi del
> sidecar e nuova sezione «🔐 Who reaches a report file» `{: #file-access }`, citata da 4 link),
> `developer/architecture/access_control.md` (solo le righe BRIM e una frase), `developer/architecture/patterns/
> brim_plugin_guide.md` (controllo del plugin, quali rotte vogliono EDITOR, `BRIMFileListItem`), `developer/api/
> overview.md` (prefisso), `developer/api/curl-testing.md` (`broker_id` come campo del form: con la query era 422);
> utente `user/files/index.en.md` (l'admin vede e cancella ogni report: debito di traduzione di una frase).
> **⚠️ Fuori pista** (dai reperti del docs-writer): (1) `_is_brim_file_id` confrontava con `file_id.lower()`, quindi un UUID
> **maiuscolo** passava e su un disco che non distingue maiuscole (macOS) il file veniva servito → controllo stretto,
> rosso prima (test-author); (2) un file senza broker «vero» (prima di `f0b7aad8d`, 24/01/2026) non ha nemmeno il
> caricatore: è solo dell'admin (la doc lo dice); (3) docstring delle rotte e di `BRIMFileListItem` (finisce nell'OpenAPI)
> col prefisso sbagliato o senza la regola nuova → `/tmp/libreFolio_w_f36_tweaks.py` (dry run ok, anche `is not None`
> per «ha un broker»); (4) `broker_ids` non toglie i file senza broker → **W-B32**. Corretta da me la frase della doc sul
> maiuscolo (`architecture.md:155-158`). Da fare: la riga 72 di `LibreFolio_devWiki/wiki/decisions/brim-broker-scoped.md`
> («Legacy metadata without `target_broker_id` is still discoverable») e il controllo del parse nel suo elenco;
> `developer/architecture/access_control.md` «API Endpoints» resta con A-14 (stessa pagina, W-B10).
> **Maiuscolo** (test-author F36-15, `api brim upper_cased`; 20:54–21:03): **rosso visto** (macOS: 200 su tutte e sette le
> rotte con l'id in maiuscolo). **Ritocchi applicati** (21:03, `/tmp/libreFolio_w_f36_tweaks.py --apply`: confronto stretto
> in `_is_brim_file_id`, `is not None`, docstring di `get_file`/`delete_file`/`download_file`/`parse_file` e di
> `BRIMFileListItem`); `ruff`/`black` puliti. Wiki: `decisions/brim-broker-scoped.md` (il contratto: `can_delete`, il parse
> sul broker del corpo, W-B4, i file senza broker solo al caricatore e all'admin); `check_source_paths.py` invariato (5).
> **Seconda pausa** (21:00–21:25, G): dopo la ripresa `api sync`, `front check`, `api brim` intero, le E2E della lista
> (`front-utility files`, `files-uploader`, `front-transaction tx-import-file-selection`, `front-broker detail`),
> `mkdocs build`, `check-links`; `all-backend` da chiedere.
> **Prove dopo la ripresa** (21:09–21:27, `nice`, una alla volta, in attesa quando il carico superava 70): `api sync`
> (12 righe: le descrizioni); `front check` **0/0**; `api brim` **116/116**; E2E `front-utility files` **28**,
> `front-transaction tx-import-file-selection` **2**, `front-broker detail` **37**; `mkdocs build` stretto, 0 avvisi
> (3 044 URL), `check-links` **96**. **⚠️ Fuori pista**: `front-utility files-uploader` **2 rossi / 6** (desktop e mobile di
> «BRIM URL keeps an unknown numeric uploader distinct from an absent owner»): lo spec **finge** la lista dei report
> (`files-uploader.spec.ts:188`, una tabella di rotte, sfuggita alla ricerca di `route(` del test-author) con voci senza
> `can_delete`, e la validazione Zod delle risposte rompe la scheda: riparazione al test-author (un campo per voce).
> **Riparato** (test-author: `can_delete: true` sulle tre voci di `REPORTS`, l'utente della pagina è OWNER del broker; una
> ricerca più larga non trova altri mock con voci: `files-destructive.spec.ts:232` risponde con una lista vuota,
> `galleryReportSets.ts` filtra la risposta vera) → `front-utility files-uploader` **8/8** (21:31–21:33). Restano:
> `all-backend` nello slot (chiesto), poi l'handoff.
> **`all-backend --workers 2`** (slot pesante 2, 21:50–22:15, `nice -n 10`): **7/7 gruppi**, 14 803 passati, 4 saltati, 0
> rossi. Porta libera, slot restituito. Backlog: **W-B3** e **W-B4** chiuse (✅ F36). Handoff FROZEN (22:17).
> **Ingresso di F36** (coordinatore 22:17: committato `3907eed36`, `258407d4d`, `4213b175a`, `c65421690`; base aggiornata con
> `dev_release2` `2415faf33` senza conflitti → HEAD `d3afcf779`). Prove sulla revisione combinata (22:17–22:30, `nice`):
> `api sync` (602 righe, tutte d'altri: impostazioni dei plugin, lavori del backup), `front check` **0/0**, `api brim`
> **116/116**, Vitest `ImportWizardModal` **26/26**, `check-orphans` pulito; l'E2E `files-uploader` dopo la pausa di T
> (22:28, 10 minuti senza E2E): **8/8** (22:32–22:34). Pronto all'ingresso.

### W-B20 — la cancellazione dei broker atomica per broker ✅ FROZEN (2026-10-15)

**Cura decisa** (coordinatore, 15/10 11:19, con i reperti di X): un aiuto in `db/session.py` che apre la transazione
prima del primo savepoint di un percorso di scrittura (lo stesso `UPDATE` vuoto di `assets/crud.py:349-351`, o `BEGIN
IMMEDIATE`), usato da `delete_bulk` per broker; il rosso prima. Il listener `begin` generale resta scartato
(`SQLITE_BUSY_SNAPSHOT`). Ordine (coordinatore, 22:17): W-B20, poi la 47 quando J ha CP-16, poi A-14 con W-B10 e le
chiavi di W-B27.

**Analisi** (22:30, codice di `d3afcf779`): `BrokerService.delete_bulk`
(`backend/app/services/brokers/broker_service.py:424-520`) **non ha nessun savepoint**: per ogni broker un `try` che, su
un'eccezione, aggiunge un risultato fallito e passa al successivo. Quello che `delete_by_broker` (N1b-1: costi Auto,
conversioni delle metà rimaste, cancellazioni) aveva già scritto resta nella sessione, e `DELETE /brokers` fa commit
perché `response.errors` resta vuoto (`api/v1/brokers.py`). Cioè: un errore a metà della cancellazione di un broker lascia
scritto metà del lavoro. La cura vuole **un savepoint per broker** (`session.begin_nested()`), e prima del primo savepoint
l'aiuto che fa emettere `BEGIN` a pysqlite (che lo rimanda fino alla prima scrittura: un savepoint aperto dopo sole
letture sarebbe il più esterno, e il suo RELEASE farebbe commit).

**Disegno**:
1. `db/session.py`: `begin_writes(session, table)`, un `UPDATE` di `table` che non tocca righe (`WHERE false`, sulla
   chiave primaria), con la docstring del perché; nessun effetto se una transazione è già aperta.
2. `delete_bulk`: `begin_writes(self.session, Broker)` prima del ciclo; il corpo di ogni broker dentro
   `async with self.session.begin_nested()`; su un'eccezione il savepoint torna indietro e il risultato dice l'errore.
   La cancellazione dell'account (che chiama la stessa strada) resta atomica per intero: i savepoint stanno dentro la sua
   transazione.
3. X potrà sostituire il trucco locale di `crud.py` con l'aiuto (non in questo lotto).

**Rossi previsti** (servizi, `services broker`): due broker in una richiesta, il secondo fallisce a metà di
`delete_by_broker` (un errore provocato dopo una prima scrittura) → oggi la scrittura parziale del secondo resta dopo il
commit; dopo la cura il primo è cancellato e il secondo è com'era. Guardie: la cancellazione normale; l'atomicità della
cancellazione dell'account; nessun commit prima della fine della richiesta.

**Passi**: 1. ✅ rossi (test-author); 2. ✅ cura; 3. ✅ prove; 4. ✅ doc e handoff (sotto, con il dettaglio).
> **F36 entrato** (coordinatore 22:35: treno 63, merge `434af2925`, registri `e05eaf17d`; CHANGELOG sotto una nuova «🔒
> Security» di `[Unreleased]`). **Via a W-B20** come disegnato (savepoint per broker con `_delete_one` e il `flush` dentro);
> `begin_writes` in `db/session.py` è un file condiviso: funzione piccola, documentata, solo in aggiunta, dichiarata
> nell'handoff. Cura pronta: `/tmp/libreFolio_w_wb20_fix.py` (dry run ok; l'import di `begin_writes` dopo `db.models`).
> Verifiche di lettura (22:40): nessun servizio delle transazioni o dei broker fa `commit`/`rollback` dentro;
> `leave_broker` (F4) e la cancellazione dell'account passano da `delete_bulk` e restano atomiche per intero (il loro
> `rollback` esterno disfa anche i savepoint rilasciati). Doc: aggiornare la pagina devWiki
> `problems/sqlite-savepoint-without-write-begins-as-transaction.md` («Seen again», oggi «not built»).
> **Finestra tranquilla** (coordinatore 22:53, corretta alle 22:55): **00:00–01:15** (G-13 dei colori, schermate con la
> data del 16/10); fino a mezzanotte lavoro normale, poi niente E2E né run pesanti finché non scrive «galleria finita».

1. ✅ **Rossi** (2026-10-15 22:58). test-author ha aggiunto la sezione 4.10 `TestDeleteBulkOneSavepointPerBroker` a
   `backend/test_scripts/test_services/test_broker_service.py` (azione `services broker`, nessuna registrazione nuova):
   BR-U-081 e BR-U-082 rossi, BR-U-083/084/085 guardie. Il fallimento è provocato sostituendo `make_standalone` nello
   spazio di nomi di `transaction_service` (dopo le due scritture di `delete_by_broker`: il costo Auto sulla metà
   ricevente, lo scollegamento dell'FX_CONVERSION del mittente); ogni caso fa commit come il router, legge da una
   sessione propria e pulisce con la fixture `committed`. Nessun caso nuovo per la cancellazione dell'account: il test
   esistente `test_delete_user_is_all_or_nothing_when_a_broker_deletion_reports_failure` (`services user-profile`) fallisce
   con una cura senza `begin_writes`; lo giro dopo la cura.
   > **Note implementazione**: `nice -n 10 … dev.py test --fresh-run --test-port 6184 --data-dir /tmp/librefolio-r13-w
   > services broker TestDeleteBulkOneSavepointPerBroker` → **2 failed, 3 passed** (2,5 s), per il motivo atteso: in
   > BR-U-081 il commit tiene `sender's FX_CONVERSION -100/110` senza `related_transaction_id` e la metà ricevente con il
   > costo Auto, mentre il mittente esiste ancora; in BR-U-082 le stesse scritture dentro la transazione della richiesta
   > (dopo il rollback del chiamante tutto torna com'era). Log `/tmp/libreFolio_w_wb20_red1.log`.
2. ✅ **Cura** (2026-10-15 23:05). `/tmp/libreFolio_w_wb20_fix.py --apply`:
   - `backend/app/db/session.py` (**file condiviso, solo in aggiunta**): `false, update` nell'import di `sqlalchemy` e la
     funzione `begin_writes(session, table)` in fondo al file (un `UPDATE` di `table` con `WHERE false`, chiave primaria
     su sé stessa, `synchronize_session=False`; la docstring dice perché, e perché non un listener `begin`);
   - `backend/app/services/brokers/broker_service.py`: `delete_bulk` chiama `begin_writes(self.session, Broker)` prima del
     ciclo e cancella ogni broker in `async with self.session.begin_nested()`; il corpo è passato tale e quale in
     `_delete_one(item, user_id, as_user_id) -> BRDeleteResult`, con un `flush` dopo `session.delete(broker)` dentro il
     savepoint (un errore di scrittura emerge prima del RELEASE e il broker risulta fallito); su un'eccezione il savepoint
     torna indietro e il risultato porta il messaggio. Messaggi e conteggi invariati.
   > **Note implementazione**: `black` invariato, `ruff check` pulito (anche sul file di test). Verdi: `services broker
   > TestDeleteBulkOneSavepointPerBroker` **5/5**; `services user-profile test_delete_user_is_all_or_nothing` **2/2**.
   > **Prova di mutazione** (`/tmp/libreFolio_w_wb20_mutation.sh`: tolta solo la chiamata a `begin_writes`, file
   > ripristinato all'uscita e verificato): BR-U-082 **rosso** (1 failed, 4 passed) e i due test dell'account **rossi**
   > («A technical failure half-way must commit nothing (D6)»: il primo broker resta cancellato dopo il rollback, perché
   > il RELEASE del suo savepoint, il più esterno, ha fatto commit). Cioè l'aiuto serve, e i test lo custodiscono.
   > **⚠️ Fuori pista** (23:08–23:15): ho lanciato `dev.py test --workers 2 … services broker` con il carico a 79 (sopra
   > 70: ho concatenato il controllo invece di aspettare). Con `--workers N` il runner **ignora l'azione**: la passata
   > parallela (`_run_parallel_prepass` → `_parallel_for_scope(args, category, …)`, `scripts/test_runner/_cli.py:906-949`)
   > copre tutta la categoria, e sono partiti i pytest di `test_ai_export_*`, cioè un run pesante senza slot. Fermato dopo
   > ~7 minuti (`stop_bash`), nessun processo rimasto, porta 6184 libera; la base della corsia era solo il DB vuoto dei
   > servizi. Segnalato al coordinatore. Da ora: mai `--workers` con un'azione singola, e il carico si controlla prima, in
   > un comando a parte.
3. ✅ **Prove** (2026-10-15 23:10–23:21, `nice -n 10`, una alla volta, carico controllato prima in un comando a parte):
   `services broker` **70/70**; `services user-profile` **36/36**; `services orphan-transfer-numbers` **19/19**;
   `services account-deletion-preview` **15/15**; `db populate --force --clean`; `api brokers` **34/34**; `api
   broker-access` **25 passed, 1 skipped** (ACCESS-050, salto previsto dal test: il primo utente non è superuser in un DB
   popolato); `api account-deletion` **9/9**; `api users-admin` **64/64** (`DELETE /users/{id}` passa da `delete_user`);
   `check-orphans` pulito (326 backend, 429 frontend). `services transaction` non serve: il suo `delete_bulk` è l'aiuto
   delle transazioni (`_tx_test_helpers.py`), non quello dei broker. Porta 6184 libera dopo ogni prova API.
4. ✅ **Doc e handoff** (2026-10-15 23:25–23:40).
   - **docs-writer**: `mkdocs_src/docs/developer/backend/transactions/service.md`, «🗑️ Broker Deletion», un blocco nuovo
     «One savepoint per broker» (33 righe aggiunte, nessuna tolta): il savepoint per broker, chi fa commit (`DELETE
     /brokers`, `leave_broker`, `delete_user` tutto o niente), perché `begin_writes()` e quando chiamarla, i test. Il
     Developer Manual è solo in inglese: nessun debito di traduzione. `mkdocs build` stretto (`nice -n 15`): 0 avvisi,
     0 errori; nessun link nuovo, quindi niente `check-links`.
   - **devWiki** (skill `wiki-file`, pagina esistente aggiornata, nessun duplicato):
     `problems/sqlite-savepoint-without-write-begins-as-transaction.md` («Fixed (2026-10-15, W-B20)», la lezione sui
     test, Prevention con `begin_writes`, fonti), la riga in `index.md`, una voce in fondo a `log.md`.
     `check_source_paths.py`: 5 mancanti (8 occorrenze) prima e dopo, tutti preesistenti. Grafo non aggiornato
     (graphify assente nel worktree).
   - **Backlog**: W-B20 ✅; **W-B33** nuova (tre imprecisioni di testo nella stessa sezione, trovate da docs-writer: le
     metto nel lotto di doc A-14 / W-B10).
   > **Note implementazione**: nessun file nuovo; delta di 9 file tracciati. Non girati: `all-backend` (lo chiedo nello
   > slot se il coordinatore lo vuole), E2E (nessun cambiamento del frontend né dell'API), `api sync` (nessuno schema
   > toccato).
> **Ingresso di W-B20** (coordinatore 23:33: committato `d6b457849` fix, `357f2cd72` docs, `81bf8204f` wiki, `d4c034936`
> giornale; base aggiornata con `dev_release2` `4ef2fc199`, merge pulito, solo il backlog fuso da sé → HEAD `70f7ab9bc`;
> `all-backend` **non richiesto**: `begin_writes` è nuovo e lo chiama solo `delete_bulk`, bastano mirate e mutazione).
> Prove sulla revisione combinata (23:34–23:41, `nice -n 10`, carico sotto 70 controllato prima): `services broker`
> **70/70**; `db populate --force --clean`; `api brokers` **34/34**; `api users-admin` **64/64** (atteso il calo del
> carico da 71). Porta 6184 libera. Pronto all'ingresso.

**Regola della notte** (coordinatore 23:33; il developer dorme fino a domattina): una decisione del developer (prodotto,
sicurezza, comportamento visibile fuori dal piano approvato) non si aspetta: al coordinatore in 3-4 righe con la proposta
per prima, quel punto in pausa e si passa al successivo; una scelta tecnica nel perimetro la decido io e la annoto come
«Decisione notturna, da rivedere»; slot pesanti, una prova alla volta con `nice` e checkpoint FROZEN invariati; senza
lavoro, lo dico subito.

### Lotto di doc A-14 · W-B10 · W-B27 (chiavi) · W-B33 ✅ FROZEN (2026-10-15/16; build da girare dopo la finestra)

Ordine del coordinatore (23:33): finché J non ha CP-16, il lotto di doc A-14 con W-B10, più le chiavi di W-B27 e W-B33;
le chiavi i18n vogliono `core-unit` prima dell'handoff; dalle 00:00 alle 01:15 niente E2E.

**Analisi** (23:45, codice di `70f7ab9bc`):
- **A-14** — `mkdocs_src/docs/developer/architecture/access_control.md`, «🔒 The "Last Owner" Rule»: dice che l'ultimo OWNER
  «cannot remove themselves» e che per andarsene deve promuovere un altro OWNER o cancellare il broker. Il codice (F4):
  `leave_broker()` (`services/brokers/access.py`) lascia andare l'ultimo OWNER e **cancella il broker** (`delete_bulk` con
  `force`); `update_own_role()` gli rifiuta la retrocessione («The last OWNER cannot demote themselves — promote another
  user first»); `bulk_update_access()` (`PUT …/access`) rifiuta ogni configurazione senza OWNER («At least one OWNER is
  required»). La sezione «🔧 Self-Management» della stessa pagina è già giusta. Cura: riscrivere la regola come «un
  broker ha sempre almeno un OWNER: nessuno lo toglie o lo retrocede; se se ne va, il broker se ne va con lui».
- **W-B10** — stessa pagina, «🌐 API Endpoints»: elenca `POST …/access` e `PATCH`/`DELETE …/access/{user_id}`, che non
  esistono. Le rotte vere (`backend/app/api/v1/brokers.py:446`, `:478`, `:531`, `:557`): `GET` e `PUT
  /brokers/{broker_id}/access` (la configurazione intera: aggiunte, ruoli, quote e rimozioni in un colpo; OWNER o admin;
  403, 400, 422 con la lista vuota), `PATCH /brokers/{broker_id}/access/me` (retrocessione di sé), `DELETE
  /brokers/{broker_id}/access/me` (andarsene; `broker_deleted` nella risposta).
- **W-B27, le chiavi** — `events.deleteBlocked` ed `events.deleteNotFound` (sorgente `assets`, prefisso `events`):
  nessun lettore nei sorgenti del prodotto, nei test, nelle E2E, nel backend, negli script né nella doc; nessuna
  chiave `events.${…}` costruita a runtime (le sole occorrenze di `deleteBlocked` sono `brokers.deleteBlocked*` e una
  variabile locale di `routes/(app)/brokers/+page.svelte`). Si tolgono con `dev.py i18n remove`. Il resto di W-B27 (il
  prefisso «Save failed:» e le date ISO in `AssetDataEditorSection.svelte`) è di X e resta fuori.
- **W-B33** — `mkdocs_src/docs/developer/backend/transactions/service.md`, «🗑️ Broker Deletion»: (1) «One is required
  since (`costBasisRequired`)» — `costBasisRequired` è il codice d'errore del batch (`schemas/transactions/batch.py:122`)
  che la regola `cost_basis_required()` (`schemas/transactions/type_metadata.py:378`) solleva; (2) «both helpers» → i tre
  aiuti, che `_compute_wac_for_auto_items()` (`services/transactions/auto_cost.py:31`) usa tutti; (3) la riga di
  `delete_bulk()` nella tabella dei chiamanti tace l'admin: `as_user_id="all"` salta il controllo, `as_user_id=<id>`
  controlla quell'utente (solo per l'admin, 403 per gli altri: `api/v1/brokers.py`).
- La riga di `developer/api/overview.md:82` segnalata dal coordinatore (`/brim/files/…/download`) è **già giusta**
  (`/brokers/import/files/…/download`): niente da fare.

**Superfici**: `access_control.md` è condivisa con A (le sezioni d'account): tocco solo «Last Owner» e «API Endpoints»;
`service.md` è di W; i sorgenti i18n `frontend/src/lib/i18n/assets/{en,it,fr,es}.json` (due chiavi in meno, il catalogo
generato è ignorato).

**Passi**: 1. ✅ doc (docs-writer: A-14, W-B10, W-B33, più tre sviste della stessa pagina); 2. ✅ chiavi (`i18n
remove`); 3. ✅ prove (`i18n check`, `utils gate-i18n-catalog`, `utils gate-i18n-usage`, `front-utility core-unit`;
`mkdocs build` stretto e `check-links` del secondo giro **dopo la finestra**); 4. ✅ handoff (sotto).

2. ✅ **Chiavi di W-B27** (2026-10-15 23:46). `dev.py i18n remove "events.deleteBlocked" -f` e `… "events.deleteNotFound"
   -f`: tolte in EN, IT, FR ed ES dalla sorgente `frontend/src/lib/i18n/assets/` (4 file, 8 righe tolte, nient'altro; il
   catalogo generato si rifà da sé ed è ignorato).
   > **Note implementazione**: prove, `nice -n 10`, una alla volta col carico controllato prima: `i18n check` stretto
   > (**4 633 chiavi**, sorgenti base 1, plugin 71, sottosistemi 21); `utils gate-i18n-catalog` **176/176**; `utils
   > gate-i18n-usage` **195/195**; `front-utility core-unit` **166 file, 5 491 test** verdi (23:48–23:5x, prima della
   > finestra delle 00:00).
1. ✅ **Doc** (docs-writer, 23:50–00:05).
   - **Primo giro** (A-14, W-B10, W-B33): `access_control.md` +28 / −11, `service.md` +12 / −10; `mkdocs build` stretto
     0 avvisi, `check-links` 96 validi (link nuovi: `#self-management`, `wac.md#persisted-cost-basis`). Due scarti dal
     mio brief, scritti come fa il codice:
     - l'elenco degli accessi (`GET …/access`) lo legge **qualsiasi utente con il login, di qualsiasi broker, e-mail
       comprese** (`get_by_id(…, as_user_id="all")`, nessun controllo in `list_accesses()`): decisione del developer per
       l'istanza di famiglia (C-8 della 38), fissata da ACCESS-002/003;
     - W-B33 (1): «refused with `costBasisRequired`» vale per un batch che **crea** quella metà senza costo; un'edit di
       sole note, tag o data su una riga vecchia passa (`batch_costs.py:152-176`, N2).
     Riformulata anche la frase «orphaned … inaccessible by anyone with admin rights» (l'admin raggiunge comunque un
     broker senza OWNER).
   - **Secondo giro** (stessa pagina, sezioni dei broker, trovate dal primo): L56 «OWNER defaults to 1.00» (vale per chi
     crea il broker; un OWNER aggiunto col `PUT` senza quota ha 0), L92 «cascade over transactions» (non è una cascata
     del DB: `delete_by_broker()`, link a `service.md#broker-deletion`), L106 `bulk_update_access()` «OWNER only» (anche
     l'admin). Senza build: dalle 00:00 è finestra tranquilla; build e `check-links` li giro io dopo «galleria finita».
     Applicata da me la sua quarta segnalazione, L101 «Promotions stay on the OWNER-only path» → «Promotions go through
     the `PUT`, OWNER or administrator only». Totale: `access_control.md` +40 / −17, `service.md` +12 / −10.
   > **⚠️ Fuori pista** — **W-B34**, decisione per il developer (inviata al coordinatore alle 23:57 secondo la regola della
   > notte, con la proposta per prima): `GET /brokers/{broker_id}/access` solo a chi ha un ruolo sul broker e all'admin,
   > 404 agli altri. In pausa; il lotto va avanti e la doc descrive la regola di oggi. **W-B35** nel backlog: docstring
   > e commenti superati (`access.py:98`, `:141`, `brokers.py:455`, `:496`, `transaction_service.py:84`; le docstring
   > delle rotte vanno nell'OpenAPI, quindi `api sync` dopo). A-14 sta nella sezione di A del backlog: la chiusura la
   > segna il coordinatore.
4. ✅ **Handoff FROZEN** (2026-10-16 00:1x). Delta: `mkdocs_src/docs/developer/architecture/access_control.md` (solo
   le sezioni dei broker: «Ownership share», «Last Owner», «Self-Management», «Implementation Details», «API
   Endpoints»; le sezioni d'account di A intatte), `mkdocs_src/docs/developer/backend/transactions/service.md`,
   `frontend/src/lib/i18n/assets/{en,it,fr,es}.json`, backlog e piano. Nessun file nuovo, nessun codice.
   > **Note implementazione**: non girati, per la finestra G-13 (00:00–01:15): `mkdocs build` stretto e `check-links`
   > del secondo giro (il primo giro: 0 avvisi, 96 link validi); li giro dopo «galleria finita», o li gira il
   > coordinatore al treno. W-B34 attende il developer.

> **Lotto di doc salvato** (coordinatore 00:02: `bf66d4fe7`, `f062418e4`, `865bccb9d`, `32f8f659c`; worktree pulito). Dopo
> le 01:15: `mkdocs build` stretto e `check-links`, poi l'ingresso. A-14 nella sezione di A la chiude il coordinatore.
> **W-B20 entrato** (treno 69, merge `23ff56b95`, riga 🐛 nel CHANGELOG). **W-B30** alla lista di domattina: proposta
> inviata alle 00:10 (un `null` esplicito toglie il costo manuale, la regola di N2 risponde `costBasisRequired` dove serve).

### W-B31 — la regola 12 del costo letta dai metadati ⏳ (2026-10-16)

Via del coordinatore (00:02): prove leggere; l'import circolare lo risolvo come preferisco, annotando la scelta.

**Analisi** (00:15, codice di `32f8f659c`):
- La regola 12 di `validate_transaction_business_rules` (`backend/app/schemas/transactions/transactions.py:190-205`)
  ammette `cost_basis_mode` solo per TRANSFER e ADJUSTMENT con quantità > 0, scritto a mano. I metadati
  (`type_metadata.py`) dicono lo stesso oggi: TRANSFER `cost_basis_pair = [forbidden, required_qty_pos]`, ADJUSTMENT
  `cost_basis_mode = required_qty_pos`, tutti gli altri `forbidden`, nessun tipo `optional`. È una copia che deriva al
  primo cambio della tabella; il frontend legge già la tabella (`getCostBasisRule` → `cbAllowed`,
  `frontend/src/lib/utils/transactions/txPayloadHelpers.ts`). Nessun test del backend copre la regola 12 (solo l'E2E
  FM9 di `tx-wac-formmodal.spec.ts`: un BUY senza `costBasisModeIncompatible`).
- Il ciclo: `type_metadata.py:18` importa `_swap_group_codes` da `transactions.py` (per riempire `swap_group`), e
  `transactions.py` dovrebbe importare la regola da `type_metadata.py`.

**Decisione notturna, da rivedere** — il ciclo si scioglie spostando i gruppi di scambio (`SWAP_GROUPS`,
`get_swap_group`, `_swap_group_codes`, tali e quali) da `transactions.py` a `type_metadata.py`, che diventa la casa
foglia delle regole per tipo; `transactions.py` importa da lì in testa, `services/transactions/batch_edits.py` prende
`get_swap_group` da lì, il test di N2 (`test_transaction_cost_basis_rule.py:590-591`) patcha `type_metadata.SWAP_GROUPS`
(regole P2: niente shim, `patch` sul percorso nuovo, grep dei vecchi a zero). Scartato l'import tardivo dentro il
validatore: lascia la dipendenza al contrario, e le regole 5–11, anch'esse copie a mano dei metadati (`asset_mode`,
`cash_mode`, `quantity_sign`, `cash_sign`, `event_compatible`), vorrebbero lo stesso trucco.

**Disegno**:
1. `type_metadata.py`: i gruppi di scambio spostati; `cost_basis_allowed(tx_type, quantity)` accanto a
   `cost_basis_required()`, con la scelta del lato in comune (`_cost_basis_rule`): ammesso quando la regola del lato non è
   `forbidden` e non è `required_qty_pos` con quantità ≤ 0 (lo stesso `cbAllowed` del frontend).
2. Regola 12: `if cost_basis_mode is not None and not cost_basis_allowed(tx_type, quantity)`; il messaggio inglese
   perde l'elenco scritto a mano; codice e parametri invariati.
3. `schemas/transactions/__init__.py`: la docstring dice dove stanno ora i gruppi di scambio.
4. Rossi (test-author, `schemas transactions`): la parità su ogni tipo × segno (verde oggi), e due rossi che provano la
   lettura dei metadati (un BUY reso `optional` deve ammettere `cost_basis_mode`; un ADJUSTMENT reso `forbidden` deve
   rifiutarlo).
5. Prove: `schemas transactions`, `services transaction-cost-basis-rule`, `services transaction`; dopo le 01:15 `api
   transactions-types` e `api sync` senza differenze.

**Passi**: 1. ⏳ rossi; 2. cura; 3. prove; 4. doc e handoff.

1. ✅ **Rossi** (2026-10-16 00:19). test-author: sezione 1.10 `TestCostBasisModeRule12` in
   `backend/test_scripts/test_schemas/test_transaction_schemas.py` (azione `schemas transactions`, nessuna registrazione
   nuova): TX-S-090 la parità su 12 tipi × quantità −1/0/1 (verde), TX-S-091 senza `cost_basis_mode` mai il codice
   (verde), **TX-S-092** un BUY reso `optional` deve ammettere `cost_basis_mode` (rosso), **TX-S-093** un ADJUSTMENT reso
   `forbidden` deve rifiutarlo (rosso), TX-S-094 il percorso di creazione: un BUY con `cost_basis_mode` riceve
   esattamente `costBasisModeIncompatible` con `{type, qty}` (verde, guardia di codice e parametri).
   > **Note implementazione**: `nice -n 10 … schemas transactions TestCostBasisModeRule12` → **2 failed, 3 passed**,
   > per il motivo atteso («still the hand-written copy»: 092 rifiutato, 093 ammesso). Log
   > `/tmp/libreFolio_w_wb31_red1.log`.
2. ✅ **Cura** (2026-10-16 00:22). `/tmp/libreFolio_w_wb31_fix.py --apply` (dry run prima):
   - `backend/app/schemas/transactions/type_metadata.py`: arrivano `SWAP_GROUPS`, `get_swap_group`, `_swap_group_codes`
     tali e quali (prima di `_build_tx_type_metadata`), via l'import da `transactions.py`; nuovo `_cost_basis_rule()` (la
     scelta del lato, ora in comune), `cost_basis_required()` lo usa, nuovo `cost_basis_allowed()`; docstring del modulo.
   - `backend/app/schemas/transactions/transactions.py`: importa `cost_basis_allowed` in testa; la regola 12 diventa
     `if cost_basis_mode is not None and not cost_basis_allowed(tx_type, quantity)`, il messaggio inglese senza l'elenco
     a mano (codice e parametri invariati); tolto il blocco dei gruppi di scambio.
   - `backend/app/services/transactions/batch_edits.py`: `get_swap_group` da `type_metadata`.
   - `backend/app/schemas/transactions/__init__.py`: la docstring dice dove stanno i gruppi di scambio e le regole.
   - `backend/test_scripts/test_services/test_transaction_cost_basis_rule.py`: il modulo patchato è `type_metadata`
     (`SWAP_GROUPS`), percorso nuovo come vuole P2.
   > **Note implementazione**: `black` (1 file riformattato), `ruff check` pulito; grep dei vecchi percorsi a zero
   > (`transactions.transactions` con `get_swap_group`/`_swap_group_codes`/`SWAP_GROUPS`, `transaction_schemas.`). Import
   > freschi in ogni ordine (`transactions`, `type_metadata`, `backend.app.schemas`, `batch_edits`, `backend.app.main`):
   > nessun ciclo. `cost_basis_allowed` su 12 tipi × −1/0/1 ammette solo ADJUSTMENT +1 e TRANSFER +1, come prima; i
   > gruppi di scambio invariati (BUY ↔ SELL, `swap_group` di BUY = `['SELL']`).
   > Nota (test-author): a quantità 0 su un tipo appaiato il frontend legge il lato `self` (`cost_basis_mode`), il backend
   > `cost_basis_pair[0]`; oggi tutti e due «forbidden». Divergerebbero solo con un primo lato `optional` e un modo
   > diverso: nessuna azione.
3. ✅ **Prove** (00:23–00:26, `nice -n 10`, una alla volta col carico controllato prima): `schemas transactions`
   **80/80** (i 5 nuovi compresi); `services transaction-cost-basis-rule` **67/67** (con lo scambio BUY → ADJUSTMENT,
   che fallisce se la patch di `SWAP_GROUPS` non viene letta); `services transaction` **66/66**. Dopo le 01:15: `api
   transactions-types` e `api sync` (atteso senza differenze: OpenAPI e metadati invariati), con la build del lotto di
   doc.
4. ⏳ **Doc e handoff**. docs-writer (00:28–00:34, senza build per la finestra):
   `mkdocs_src/docs/developer/backend/transactions/wac.md` +13 / −1, un paragrafo nuovo dopo quello di
   `cost_basis_required()` (la regola 12 legge la stessa tabella con `cost_basis_allowed()`, il lato scelto da
   `_cost_basis_rule()`, lo stesso `cbAllowed` del frontend; con la tabella di oggi ammette esattamente le righe che
   vogliono un costo) e un rimando a `#persisted-cost-basis` nella frase della riga ~602. Nessuna traduzione. Notato e
   non toccato: la descrizione di `cost_basis_pair` (`type_metadata.py:135`) dice «qty<0» per l'indice 0 (è ≤ 0) e usa
   le etichette italiane «Da»/«A» in un testo dell'API (finisce nell'OpenAPI: semmai con W-B36). Backlog: W-B31 ✅,
   **W-B36** nuova (le regole 5–11, copie a mano dei metadati).
   > Restano per dopo le 01:15, in serie: `mkdocs build` stretto e `check-links` (anche per il lotto di doc), `db
   > populate`, `api transactions` (copre `GET /transactions/types`), `api transactions-validate`, `api
   > transactions-wac`, `api sync` (atteso senza differenze).

> **W-B31 committato come checkpoint** (coordinatore 00:35: `b29f41e51` refactor, `d01ce77f7` giornale; worktree
> pulito). Le prove API di W-B31 e la build del lotto di doc dopo «galleria finita», su `d01ce77f7` o oltre.

### W-B36 — le regole 5–11 lette dai metadati, la parte che coincide ⏳ (2026-10-16)

Via del coordinatore (00:33): la parte che coincide, dopo il commit di W-B31, con i quattro casi che non coincidono come
eccezioni esplicite che rimandano alla decisione **P6** (lista del developer di domattina); prove leggere.

**Analisi** (00:40–00:50, sola lettura, codice di `b29f41e51`), tipo per tipo contro `TX_TYPE_METADATA`:

| Regola | A mano | Tabella | Esito |
|---|---|---|---|
| 5 asset obbligatorio | BUY, SELL, DIVIDEND, TRANSFER, ADJUSTMENT | `asset_mode == required`: gli stessi | coincide |
| 6 asset facoltativo | nessun controllo | INTEREST, FEE, TAX `optional` | coincide |
| asset vietato | non c'è nelle 5–11 | DEPOSIT, WITHDRAWAL, FX_CONVERSION, CASH_TRANSFER `forbidden` | in creazione le regole 3, 3b, 4; un aggiornamento non può aggiungere un asset (`TXUpdateItem` non ha `asset_id`): nessun caso raggiungibile |
| 7 cassa obbligatoria | 10 tipi | `cash_mode == required`: gli stessi | coincide |
| 8 cassa vietata | solo ADJUSTMENT | ADJUSTMENT **e TRANSFER** | **P6 caso 1** (TRANSFER) |
| 9 eventi | `EVENT_COMPATIBLE_TYPES` = DIVIDEND, INTEREST, ADJUSTMENT | `event_compatible`: gli stessi | coincide (il frozenset è una seconda copia) |
| 10 segno della quantità | BUY > 0, SELL < 0, sette tipi = 0, ADJUSTMENT ≠ 0 | `quantity_sign`: anche **FX_CONVERSION zero** e **TRANSFER nonzero** | **P6 casi 2 e 3** |
| 11 segno della cassa | negativo BUY, WITHDRAWAL, FEE, TAX; positivo SELL, DIVIDEND, INTEREST, DEPOSIT | `cash_sign`: gli stessi; più **nonzero** per FX_CONVERSION e CASH_TRANSFER | **P6 caso 4** |

I quattro casi P6 sono tutti nell'aggiornamento: la creazione li rifiuta già (regole 2, 3, 3b), l'aggiornamento
(`batch_edits._validate_updated_final_state`) fa girare solo le 5–12. Via API passano un TRANSFER con cassa ≠ 0 (sposta il
saldo di cassa), un FX_CONVERSION con quantità ≠ 0, un TRANSFER a quantità 0, un FX_CONVERSION o CASH_TRANSFER a cassa 0;
Form e Bulk no (nascondono i campi vietati). Proposta al developer (P6): la tabella anche in aggiornamento, solo quando il
campo cambia (come N2), dopo un controllo dei dati.

**Disegno**: le regole 5, 7, 8, 9, 10, 11 leggono `TX_TYPE_METADATA` al momento della chiamata (accessori in
`type_metadata.py`); i casi P6 restano com'è oggi con insiemi d'eccezione espliciti e nominati in `transactions.py`
(commento che rimanda a P6); `EVENT_COMPATIBLE_TYPES` tolto o derivato; codici, parametri e testi resi dei messaggi
invariati. Rossi (test-author, `schemas transactions`): la parità su tipi × asset × cassa × quantità × evento (verde oggi),
un rosso per regola che prova la lettura della tabella, le guardie dei casi P6 (verdi oggi e dopo).

**Passi**: 1. ⏳ rossi; 2. cura; 3. prove; 4. doc e handoff.
> **Pausa delle prove** (coordinatore 00:56): da subito fino a verso l'01:40 niente prove né build di nessun tipo (la
> galleria dei colori ha avuto rossi per il carico); leggere e scrivere file va bene. Le prove spostate all'01:15 (build
> e `check-links` del lotto di doc, API di W-B31) e i rossi di W-B36 slittano a dopo il suo via. Cura di W-B36 pronta:
> `/tmp/libreFolio_w_wb36_fix.py` (dry run ok).
1. ⏳ **Rossi** (test-author, 00:40–01:10, nessuna prova lanciata). Sezione 1.11 di
   `backend/test_scripts/test_schemas/test_transaction_schemas.py`: TX-S-095 la parità su 576 celle (12 tipi × asset
   × 4 casse × 3 quantità × evento) con i casi P6 a parte (verde: senza le eccezioni differirebbero 64 celle, tutte dei
   casi 1–3; il caso 4 non tocca nessuna cella, lo vede solo la sua guardia); TX-S-096…103 un rosso per regola (5, 7, 8,
   9 aperta e chiusa, 10 positivo/negativo e zero/nonzero, 11); TX-S-104…107 le guardie dei quattro casi P6 (verdi oggi e
   dopo); TX-S-108 codice, testo reso e parametri di 11 codici (verde). Attesi oggi 8 rossi e 16 verdi su 24 elementi.
   I rossi si girano dopo il via del coordinatore (pausa delle prove).

**Decisioni notturne, da rivedere** (00:58–01:10, dai reperti di test-author):
- **`EVENT_COMPATIBLE_TYPES` tolto** (era la seconda copia scritta a mano di `event_compatible`): un aiuto
  `event_compatible(tx_type)` in `type_metadata.py`, letto al momento della chiamata, lo usano la regola 9 e
  `services/transactions/event_suggestions.py` (`skipped_reason="type_not_event_compatible"`); il test 1.9
  `test_tx_type_metadata_event_compatible_flags` riscritto senza quel nome (test-author). Il commento di
  `backend/app/services/files/static_uploads.py:80` (file di H) cita `EVENT_COMPATIBLE_TYPES` come esempio di frozenset:
  lo segnalo, non lo tocco; `developer/backend/transactions/split_promote.md:120` va riallineata nella doc del lotto.
  Resta fuori la mappa `type_map` di `event_suggestions.py` (quali tipi d'evento per tipo di transazione): un'altra
  copia, ma di un'informazione che la tabella non ha.
- **Testi dei messaggi invariati**: con due o più violazioni `multipleBusinessRuleErrors` impacchetta il *template*,
  non il testo reso; i quattro messaggi che erano letterali (`qtyPositive`, `qtyNegative`, `qtyNonzero`, `cashForbidden`)
  restano letterali per tipo (f-string), gli altri restano template. La fuga di `{type}` di oggi nei testi impacchettati
  va nel backlog come **W-B38**.
   > Seguito di test-author (01:10–01:25, solo ruff/black): il test 1.9 `test_tx_type_metadata_event_compatible_flags`
   > riscritto senza `EVENT_COMPATIBLE_TYPES` (i flag della tabella, e il parametro `allowed` della regola 9 su un DEPOSIT
   > collegato a un evento; `set(TX_TYPE_METADATA) == set(TransactionType)` al posto del conteggio); le docstring della 1.10
   > al passato; TX-S-108 fissa anche `message_template` degli 11 codici; nuovo **TX-S-109** (un BUY senza asset e con
   > quantità 0 in creazione: `multipleBusinessRuleErrors` con esattamente le voci `assetRequired` «{type} requires
   > asset_id» e `qtyPositive` «BUY requires quantity > 0»). Attesi sul file intero 105 elementi: 8 rossi (TX-S-096…103),
   > 97 verdi.
   > **Dopo il via**, in serie: `mkdocs build` stretto e `check-links` (lotto di doc e W-B31) → ingresso del lotto di doc;
   > rossi di W-B36 (`schemas transactions`); cura; `schemas transactions`, `services transaction`, `services
   > transaction-cost-basis-rule`; `db populate`; `api transactions`, `api transactions-validate`, `api transactions-wac`,
   > `api events-suggest`; `api sync`; doc di W-B36 (`split_promote.md:120`) e build; handoff di W-B31 e W-B36.
> **File tenuti dai colori stanotte** (coordinatore 01:07): `frontend/src/lib/components/transactions/modals/
> TransactionFormModal.test.ts` (righe 791–792, 834–838: `border-red-400` → `border-lf-danger`), `frontend/src/lib/utils/
> currency/fxConversionHelper.ts:118–131` e `frontend/src/lib/components/transactions/wac/WacPreviewSection.svelte:321–322`
> (Q10, tooltip sul fondo invertito). Prima di toccarli (la 47 compresa), avvisare il coordinatore.

### Decisione 47 — la gamba che cede convertita al costo: analisi ⏳ (2026-10-16)

Sblocco (coordinatore 01:07): J CP-16 in `dev_release2` (`240675ad1`, commit `335fb89cf`: un ADJUSTMENT negativo con
`cost_basis_override` chiude ogni lotto FIFO che consuma a quel costo per unità, il valore come incasso; senza, resta una
correzione a prezzo zero). Firma di J: la gamba convertita è un ADJUSTMENT −q con il costo Auto **del suo broker**
(`compute_wac_iterative(broker della riga, data della riga, esclusa la riga)`); per un TRANSFER ancora legato
`_auto_cost_source` sceglie il broker del partner; un promote che la riporta a TRANSFER toglie il costo dal lato che
cede; J-17 è nella lista del developer. Analisi in sola lettura fino al via (i servizi delle transazioni di
`dev_release2` sono identici ai miei).

**Analisi** (01:10–01:35):
1. **Cancellazione del broker** (`TransactionService.delete_by_broker`, `services/transactions/transaction_service.py`):
   oggi la gamba che cede perde solo il link. Con la 47: `make_standalone(gamba, ADJUSTMENT)` e il costo Auto scritto con
   `_write_auto_cost`, calcolato **prima di ogni modifica** (come quello delle gambe in entrata) con
   `_auto_cost(gamba, (gamba.broker_id, [gamba.id], gamba.date))`, non con `_auto_cost_source`. Senza un cambio il costo
   non si scrive: proposta tecnica, la gamba resta come oggi (TRANSFER senza link, lotti `TRANSFER_PAIR_MISSING`) invece di
   un ADJUSTMENT −q senza costo, che leggerebbe le unità come distrutte.
2. **«Dividi la coppia»** (`apply_splits`, `batch_edits.py`): la gamba from diventa ADJUSTMENT −q; il suo costo Auto
   (stesso broker, data, esclusa la riga) va calcolato nello stadio WAC del batch (dopo update, create e promote dello
   stesso batch), così vede lo stato finale, e `/validate` lo mostra.
3. **Promote** (`apply_promotes`, `batch_creates.py`): oggi non tocca il costo; con la 47 lo toglie
   (`cost_basis_override` e `cost_basis_currency`) dal lato in cui il tipo d'arrivo non lo ammette (`cost_basis_allowed`,
   W-B31): copre il TRANSFER che cede.
4. **`orphan_pair_halves`, il nodo**: la correzione (`backend/app/db/post_migration/orphan_pair_halves.py`) gira su una
   connessione `sqlite3` sincrona dentro il framework post-migrazione (lock, backup, controlli FK e conteggi), passo
   `post-migration-fixes` di `services/platform/app_lifespan.py` in un thread. Il costo Auto vuole `compute_wac_iterative`
   (async, cambi, split): rifarlo lì sarebbe una seconda copia della matematica finanziaria. Proposta: un passo async
   d'avvio subito dopo `post-migration-fixes` (una riga in `app_lifespan.py`, file di H) che chiama una funzione mia, lo
   stesso codice della cancellazione; idempotente, mai bloccante, serializzato fra i worker con `begin_writes`; la
   correzione sincrona continua a contarle nel dry run. Alternativa: lasciare le gambe vecchie come sono.
5. **J-17 sì**: ogni gamba convertita (cancellazione, orfani, split) diventa un ADJUSTMENT in uscita col costo, che
   `build_asset_price_series` (`financial_math/price_marks.py:307-309`) legge come osservazione TRADE: su un asset quotato
   di rado il prezzo per tutti i broker diventa il costo medio di quel giorno, dove il TRANSFER non segnava nulla.
6. **Metadati e moduli**: per l'ADJUSTMENT con quantità < 0 il costo resta non ammesso (`required_qty_pos`): Form e Bulk
   non lo mostrano né lo mandano, un'edit lo lascia scritto, lo scrive solo il sistema. Nessun file del frontend toccato
   (né `WacPreviewSection.svelte`, tenuto dai colori).
7. **Testo V-3 per A**: una frase in più sulle unità mandate da un broker che resta a quello cancellato.
8. **Rossi previsti**: BR-U-073 (oggi fissa la gamba che cede come TRANSFER) e i numeri di `services
   orphan-transfer-numbers` cambiano; nuovi per lo split, il promote e il passo d'avvio.

**Risposte del coordinatore** (01:12):
- Punti 1–3: **via**. **Decisione notturna, da rivedere**: senza un cambio la gamba che cede resta un TRANSFER senza link
  (com'è oggi), non un ADJUSTMENT −q senza costo.
- Punto 4: **via al passo d'avvio async** subito dopo `post-migration-fixes`: una riga in
  `backend/app/services/platform/app_lifespan.py`, dichiarata (con H lo schema concordato: un passo per riga), la funzione
  nel codice di W. **Decisione notturna, da rivedere**: cambia i dati all'aggiornamento, quindi il CHANGELOG lo dice, e il
  dry run (`python -m backend.app.db.post_migration --dry-run`) deve mostrare le gambe e il costo che prenderanno.
- Punto 5: J-17 è P2 nella lista del developer; **la 47 non entra senza J-17**: preparo tutto, l'ingresso aspetta la sua
  risposta di domattina (se la approva, J la fa subito e la 47 entra dopo).
- L'ordine al via resta il mio: build e `check-links` del lotto di doc → W-B36 (rossi, cura, prove) → API di W-B31/W-B36 →
  la 47 (rossi dei punti 1–4, cura, prove).

**Cura della 47 preparata** (01:15–01:20, `/tmp/libreFolio_w_dec47_fix.py`, dry run ok su 10 file; si applica dopo i rossi):
- `services/transactions/auto_cost.py`: `_handover_cost(db_tx)` = `_auto_cost(db_tx, (db_tx.broker_id, [db_tx.id],
  db_tx.date))`, l'aiuto comune ai quattro punti.
- Punto 1, `transaction_service.py` (`delete_by_broker`): i costi delle gambe che cedono calcolati con quelli delle gambe
  in entrata, prima di ogni modifica; con il costo `make_standalone(…, ADJUSTMENT)` e `_write_auto_cost`, senza solo il
  link (decisione notturna); docstring aggiornata e il commento «one is required since» corretto (una voce di W-B35).
- Punto 2, `batch_edits.py` (`apply_splits` annota la gamba che cede di un TRANSFER in `context.handover_rows`,
  campo nuovo di `transaction_batch_context.py`) e `batch_costs.py` (`compute_wac_and_fx_issues` la prezza dopo le voci
  Auto). **Decisione notturna, da rivedere**: senza un cambio lo split è rifiutato con `WAC_FX_UNAVAILABLE` (come una
  riga Auto), invece di lasciare un ADJUSTMENT −q senza costo; l'issue esce da un aiuto comune `_wac_fx_unavailable`,
  identico per le voci Auto.
- Punto 3, `batch_creates.py` (`apply_promotes`): via costo e valuta dal lato in cui il tipo d'arrivo non li ammette
  (`cost_basis_allowed`).
- Punto 4: nuovo `services/transactions/lone_transfer_legs.py` (`convert_lone_giving_legs(session, dry_run)`,
  `convert_lone_giving_legs_at_startup()` che non solleva mai, `run_lone_giving_legs(db_path, dry_run)` per la riga di
  comando, `LoneLeg.describe`); una riga in `services/platform/app_lifespan.py` (passo `lone-transfer-legs` dopo
  `post-migration-fixes`, **file di H, dichiarata**); `db/post_migration/__main__.py` lo fa girare dopo le correzioni e
  stampa ogni gamba col costo (anche a secco); la docstring di `orphan_pair_halves.py`.

> **Ripresa delle prove** (coordinatore 01:33). **Lotto di doc verde**: `mkdocs build` stretto (uscita 0, 0 avvisi, 81 s)
> e `check-links` (96 validi), su HEAD `d01ce77f7`; segnalato pronto all'ingresso (01:37).
> **W-B36, passo 1 ✅** (01:40): `schemas transactions` → **8 failed, 97 passed**, per il motivo atteso (TX-S-096…103:
> «still the hand-written copy»; la parità TX-S-095, le guardie P6, i messaggi e il test 1.9 riscritto verdi). Log
> `/tmp/libreFolio_w_wb36_red1.log`.
> **W-B36, passo 2 ✅** (01:42): `/tmp/libreFolio_w_wb36_fix.py --apply` su `transactions.py` (regole 5–11 dalla tabella
> con `get_tx_type_metadata()`; insiemi d'eccezione P6 nominati; `EVENT_COMPATIBLE_TYPES` tolto; messaggi letterali per
> tipo dove lo erano), `type_metadata.py` (`get_tx_type_metadata`, `event_compatible`, `event_compatible_types`; commenti e
> docstring), `__init__.py` (docstring), `services/transactions/event_suggestions.py` (`event_compatible(req.type)`).
> `black` invariato, `ruff` pulito. Unico riferimento rimasto a `EVENT_COMPATIBLE_TYPES`: il commento di
> `backend/app/services/files/static_uploads.py:80` (file di H, da segnalare).
> **W-B36, passo 3 ✅** (01:43–02:00, `nice -n 10`, carico controllato prima di ogni lancio): `schemas transactions`
> **105/105**; `services transaction` **66/66**; `services transaction-cost-basis-rule` **67/67**; `db populate`; `api
> transactions` **26/26**, `api transactions-validate` **11/11**, `api transactions-wac` **20/20**, `api events-suggest`
> **9/9** (valgono anche come prove API di W-B31); `api sync` senza differenze tracciate. Porta 6184 libera.
> Passo 4 in corso: doc (docs-writer: `service.md` § regole per tipo, `split_promote.md:120`), docstring della 1.11
> (test-author).
> **W-B36, passo 4 ✅** (02:00–02:15). docs-writer: `service.md` nuova sottosezione «📏 Per-type rules»
> (`#per-type-rules`, 25 righe: i chiamanti, la tabella regola → campo letto → codici, i quattro punti P6) e
> `split_promote.md` (~120: i tipi che la tabella marca `event_compatible`, con il rimando); `mkdocs build` stretto 0
> avvisi, `check-links` 96 validi. test-author: le docstring e i messaggi della 1.11 al passato («red before W-B36, now
> its guard»), nessuna asserzione toccata; `schemas transactions` di nuovo **105/105**. Reperti di docs-writer: il caso 4
> di P6 si raggiunge anche con un promote (WITHDRAWAL e DEPOSIT a importo zero promossi); la descrizione di
> `TXCreateItem.asset_event_id` è un'altra copia a mano nell'API (con quella di `cost_basis_pair`: residuo di W-B36 nel
> backlog). Handoff FROZEN di W-B31 e W-B36 (02:15).

> **Lotto di doc entrato** (treno 72, merge `6fa3f8936`, solo `32f8f659c`); A-14 chiusa dal coordinatore nella sezione di A.
> **W-B36 committato** (`dcb33859f` codice e test, `ad346751b` doc, `a92dc76ec` giornale); base aggiornata con
> `dev_release2` `bbfba9169` (dentro CP-16, CP-15, X CP11a, Z3/Z4, E4a, Y7) → HEAD `3b3ede3ed`. Prove d'ingresso di
> W-B31 + W-B36 sulla revisione combinata (02:00–02:10, `nice`, carico sotto 70): `schemas transactions` **105/105**,
> `services transaction` **66/66**, `db populate`, `api transactions` **26/26**, `api transactions-validate` **11/11**.
> Porta 6184 libera. Pronti all'ingresso. Le note: il commento di `static_uploads.py:80` lo gira il coordinatore a H, il
> caso del promote va in P6, il residuo dei testi dell'API resta nel backlog.

**Decisione 47 — passi** (dopo il via del coordinatore, 02:10): 1. ⏳ rossi; 2. cura; 3. prove; 4. doc e handoff (l'ingresso
aspetta J-17).

1. ⏳ **Rossi** (test-author, 02:12–03:05; nessuna prova lanciata da lui). File: `test_broker_service.py` (BR-U-073 e
   BR-U-076 sul caso `transfer-receiver-deleted`, BR-U-078 riscritto ×2, nuovi BR-U-086 ×2, BR-U-087 guardia del cambio
   mancante con un vero PYG/EUR assente, BR-U-088 il calcolo che fallisce), `test_transaction_cost_basis_rule.py`
   (`TestDecision47TheGivingLegOfATransfer`: costo della gamba dello split, prezzata dopo il resto del batch, split
   rifiutato con `WAC_FX_UNAVAILABLE` in commit e validate, promote ×2), `test_orphan_transfer_after_broker_delete.py`
   (`TestOrphanOutgoingTransfer` su due libri: un controllo con l'ADJUSTMENT −4 a 20 EUR scritto direttamente e il resto
   della cancellazione), nuovo `test_lone_transfer_legs.py` (15 test, import tardivo) con l'azione nuova `services
   lone-transfer-legs` in `scripts/test_runner/_backend_services.py` (condiviso, solo in aggiunta).
   Reperti di test-author e mie **decisioni notturne, da rivedere** (nella cura preparata): una gamba il cui costo
   solleva un errore resta un TRANSFER (con il motivo) e le altre vanno avanti, senza che il passo sollevi (la sezione 9 di
   `test_post_migration_orphan_pairs.py` mette quantità `'n/a'` sullo stesso broker); le gambe si scelgono in SQL con
   `quantity < 0`; il dry run conta anche una gamba il cui link nomina una riga sparita; la riga di comando salta il passo
   se il controllo d'integrità fallisce; un costo dato alla gamba dello split da un update dello stesso batch resta.
   > Rossi visti (02:15–02:25, `nice`, carico sotto 70): `services broker TestDeleteBulkCrossBrokerPair` → **7 failed,
   > 19 passed** (i sette attesi; BR-U-087 verde); `services orphan-transfer-numbers TestOrphanOutgoingTransfer` → **2
   > failed, 2 passed** (i controlli verdi confermano i numeri derivati da test-author sul motore di CP-16).
   > Seguito di test-author (03:05–03:15): `test_lone_transfer_legs.py` a 18 elementi (la gamba il cui costo solleva un
   > errore resta con il motivo e le altre si convertono; il dry run elenca la gamba col link verso una riga sparita; le
   > prove della riga di comando con quattro gambe; una guardia: nessun passo dopo una correzione fallita);
   > `test_transaction_cost_basis_rule.py` una guardia (il costo dato dall'update dello stesso batch resta);
   > `test_account_deletion_api.py:17` docstring; sezione 9 di `test_post_migration_orphan_pairs.py` invariata.
   > Rossi visti (03:15–03:18): `services transaction-cost-basis-rule TestDecision47TheGivingLegOfATransfer` → **6
   > failed, 1 passed** (la guardia); `services lone-transfer-legs` → **17 failed, 1 passed** (la guardia della correzione
   > fallita); `check-orphans` pulito (341 file del backend raggiungibili).
2. ✅ **Cura** (03:20): `/tmp/libreFolio_w_dec47_fix.py --apply` (i 10 file della cura preparata, con le decisioni notturne
   sopra); `black` invariato, `ruff` pulito; import freschi senza cicli (`lone_transfer_legs`, `app_lifespan`,
   `post_migration.__main__`, `backend.app.main`).
3. ✅ **Prove** (03:20–03:45, `nice -n 10`, una alla volta, carico controllato prima di ogni lancio): `services broker`
   **76/76**; `services transaction-cost-basis-rule` **74/74**; `services lone-transfer-legs` **18/18**; `services
   orphan-transfer-numbers` **21/21**; `services transaction` **66/66**; `services app-lifecycle` **42/42**; `services
   roi-fifo-utils` **708/708**; `services user-profile` **36/36**; `services account-deletion-preview` **15/15**; `db
   post-migration` **41/41**; `db post-migration-orphan-pairs` **47/47**; `db populate`; `api batch-split-promote`
   **36/36** (il server di prova parte col passo nuovo); `api brokers` **34/34**; `api account-deletion` **9/9**; `api
   transactions-wac` **20/20**. Porta 6184 libera. Non girati: E2E (lo split dal frontend: chiederò lo slot prima
   dell'ingresso), `all-backend` (slot del coordinatore).
4. ⏳ **Doc e handoff** (03:45–).
   - **devWiki**: `decisions/orphan-transfer-becomes-an-adjustment.md` aggiornata (la gamba che cede al costo Auto del suo
     broker, lo split e il promote, le gambe sole e il passo d'avvio, l'intreccio con J-17; via le righe superate «not in
     the code yet» e «waits for point 46/47»), la riga di `index.md`, una voce in fondo a `log.md`; `check_source_paths.py`
     5 mancanti, preesistenti.
   - **docs-writer** (primo giro): 15 pagine inglesi — sviluppatore `service.md`, `split_promote.md` (nuova sezione
     `#transfer-giving-leg`), `architecture/database/index.md` (nuova sezione `#lone-transfer-legs`), `overview.md`,
     `users_and_brokers.md`, `brokers_transactions.md`, `wac.md`, `price_resolver.md` (J-17); amministratore
     `cli_tools.en.md`, `docker_advanced.en.md`, `users.en.md`; utente `brokers/index.en.md`, `settings/profile.en.md`,
     `dashboard/charts.en.md`, `transactions/index.en.md`. Build stretto 0 avvisi, `check-links` 96, `translate-validate`
     solo il debito nuovo delle sei pagine tradotte toccate (non timbrate).
   - **Testo dell'eliminazione del broker** (`brokers.confirmDeleteWithTransactions`, EN/IT/FR/ES con `dev.py i18n
     update`): una frase in più, «Assets other brokers transferred to this one leave them at their average cost»; `i18n
     check` stretto (4 687 chiavi). Il testo V-3 di A (`settings` `…unpaired`) è pronto in quattro lingue, va ad A col
     coordinatore insieme alla 47.
   - **Decisione notturna, da rivedere**: il passo d'avvio non tocca un DB danneggiato. Se c'è qualcosa da convertire,
     prima `PRAGMA quick_check` (`_database_is_sound`); senza niente da convertire nessun controllo (una query). La riga di
     comando già lo salta se il controllo d'integrità delle correzioni fallisce. `services lone-transfer-legs` di nuovo
     **18/18**.
   - Reperti di docs-writer, nel backlog: **W-B39** (uno split rifiutato non dice niente all'utente: `confirmSplit()` lo
     scrive solo in console) e **W-B40** (lo split di una coppia non ancora salvata nel Bulk salva l'ADJUSTMENT in uscita
     senza costo); due pagine della teoria finanziaria e una frase di `access_control.md` nel secondo giro di docs-writer.
   - **Secondo giro di docs-writer** (04:00–04:20): `architecture/database/index.md` e `overview.md` (il controllo
     `quick_check` all'avvio; resta una differenza documentata: dopo una correzione fallita su un DB sano il passo d'avvio
     gira, la riga di comando no), `admin/cli_tools.en.md` (la riga di log nuova), `financial-theory/.../deposited-capital.en.md`
     e `.../transfer.en.md` (lo split e il promote col costo), `access_control.md` (la gamba che resta TRANSFER senza
     cambio). Build stretto 0 avvisi, `check-links` 96, `translate-validate` 429 errori e 1 140 avvisi (da 426 e 1 134: il
     link nuovo di `transfer.en.md` e la riga di log di `cli_tools.en.md`, non timbrati).
   - test-author: due guardie del passo d'avvio (DB che non passa il controllo: niente scritto, un avviso; niente da
     convertire: nessun controllo); `services lone-transfer-legs` **20/20**.
   > **Handoff FROZEN** (04:25): delta di 41 file tracciati e 2 nuovi (`lone_transfer_legs.py`,
   > `test_lone_transfer_legs.py`); l'ingresso aspetta J-17. File condivisi dichiarati: `services/platform/app_lifespan.py`
   > (di H: un import e una riga di passo col commento), `scripts/test_runner/_backend_services.py` (azione nuova, in
   > aggiunta), `db/post_migration/__main__.py` (il passo dopo le correzioni), pagine d'account di A
   > (`user/settings/profile.en.md`, `admin/users.en.md`, `architecture/users_and_brokers.md`: solo la frase sulla gamba
   > che cede). Non girati: E2E (lo split e la finestra del broker dal frontend: chiedo lo slot prima dell'ingresso),
   > `all-backend` (slot del coordinatore).

> **Decisione 47 committata come checkpoint** (coordinatore 04:05: `a66bbc1a4`, `8b3e6b766`, `7d28466be`, `cb247a696`);
> base aggiornata (merge di `dev_release2` `2c485d3d4`, dentro H CP-U2; un conflitto di sola aggiunta in
> `LibreFolio_devWiki/log.md` risolto dal coordinatore tenendo tutte le voci) → HEAD `817a2d37c`. L'ingresso della 47
> aspetta J-17. W-B31 + W-B36 entrati (treno 78, merge `4e69b5271`). Il testo V-3 per A lo gira il coordinatore.
> **Coda della notte** (coordinatore 04:05), ciascuno in commit separati dalla 47 (entrano con un cherry-pick): 1. W-B37;
> 2. la riga dell'escaper in `TransactionBulkModal.svelte:1879` (C-34 di Y) e la voce da togliere dalla sua guardia;
> 3. W-B35 (docstring, `api sync`, `front check`); 4. W-B12. W-B29 dopo le 06:45 (slot E2E).

### W-B37 — il modale dei report salta i file non cancellabili ✅ (2026-10-16) — 🧊 FROZEN

**Analisi** (04:10, codice di `817a2d37c`): `handleDeleteMultiple(fileIds)` di
`frontend/src/lib/components/brokers/BrokerImportFilesModal.svelte` manda un DELETE per ogni file selezionato e riporta i
403 come errore; dopo CP-U2 di H `FilesTable` nasconde «elimina» sulle righe con `can_delete: false`, e la pagina File
(`frontend/src/routes/(app)/files/+page.svelte`, `deletableSelection` e `handleBulkDeleteFiles`) salta quei file con
`notify({name: 'file.delete.skipped', detail: {count, isBrim}, toast: {variant: 'warning', message: uploads.deleteSkipped}})`.
`files` nel modale è tipato `BrimFile[]` (`schemas.BRIMFileInfo`, senza `can_delete`), ma la lista arriva da
`BRIMFileListItem`, che lo porta: si legge come fa H, `(file as {can_delete?: boolean}).can_delete === false`.
**Disegno**: in `handleDeleteMultiple` i file non cancellabili si tolgono prima del ciclo, con lo stesso avviso e lo stesso
evento della pagina File; se non resta niente, nient'altro; il conteggio del toast di successo è quello dei cancellati.
Nessun cambio di classi (il file non è tenuto dai colori). Rosso prima (Vitest, test-author).

**Rosso** ✅ (04:25): test-author, `frontend/src/lib/components/brokers/BrokerImportFilesModal.test.ts` (nuovo, 4 test:
selezione mista, selezione tutta bloccata, selezione tutta cancellabile, controllo del client generato), registrato in
`front_component_unit` (`scripts/test_runner/_frontend_utility.py`, una riga dopo `BrokerCard.test.ts`; file condiviso,
aggiunta sola). `vitest run` del file: **2 failed, 2 passed**, per il motivo atteso: i DELETE partono anche per i file
bloccati (`expected [deletable-1, …(2)] to deeply equal [deletable-1, …(1)]`; `expected [locked-1, locked-2] to deeply
equal []`). Log `/tmp/libreFolio_w_wb37_red.log`.

**Cura** ✅ (04:32): `BrokerImportFilesModal.svelte`, in `handleDeleteMultiple`: l'insieme dei file con
`can_delete === false` (chiave `file_id`), la selezione filtrata, l'avviso `uploads.deleteSkipped` con l'evento
`file.delete.skipped` (`detail: {count, isBrim: true}`, come la pagina File) se qualcosa resta fuori, ritorno subito se
non resta niente (`confirmBulkDelete` toglie comunque la selezione dopo), il ciclo e il toast di successo sui soli
cancellabili; import di `notify`. Nessuna classe toccata, nessuna chiave i18n nuova.
**Prove** (`nice`, carico < 60): `vitest run` del file **4/4**; `prettier --check` pulito; `front check` **0 errori,
0 avvisi** (copre anche C-34 e il client rigenerato di W-B35); `check-orphans` (459 file Vitest raggiungibili, compreso
il nuovo); gate dei colori pulito. Porta 6184 libera.

### C-34 (di Y) — l'escaper in linea del Bulk ✅ codice (2026-10-16)

`frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` (~1879), la cella `html` della descrizione
escapava a mano `& < >`; ora `escapeHtml(row.fields.description)` da `$lib/utils/core/escapeHtml` (già importato nel
file), che escapa anche `"` e `'`. Classi invariate (gate dei colori pulito, `prettier` ok). Le sole copie rimaste sono
quella canonica e `inlineMath.ts` (voluta, per KaTeX). **La guardia di Y** che ammette questo file per nome non è ancora
in `dev_release2` né nella mia base: la voce va tolta da chi entra per secondo (Y, se il mio commit entra prima).
Prove: `front check` insieme a W-B37 ✅ (0 errori, 0 avvisi).

### W-B35 — docstring superate dell'accesso ai broker ✅ codice (2026-10-16)

`backend/app/services/brokers/access.py`: `list_accesses` dice che non controlla niente (decide la rotta) e che
`user_id`/`is_superuser` non si leggono (tenuti per un controllo che la rotta potrà aggiungere, P4); i campi restituiti
veri (con `share_percentage` e `avatar_url`). `bulk_update_access`: la regola «Cannot remove the calling user as last
OWNER» assorbita in «At least one OWNER must remain: nobody, the caller included, can remove or downgrade the last
one». `backend/app/api/v1/brokers.py`: la docstring di `list_broker_access` dice ciò che fa il codice (qualsiasi utente
autenticato legge l'elenco di qualsiasi broker esistente, e-mail comprese; 404 per un broker che non esiste) e quella del
`PUT …/access` la stessa regola dell'ultimo OWNER. `black` invariato, `ruff` pulito; `api sync` rigenera il client (ignorato
da git: nessuna differenza tracciata). La riga «one is required since» di `transaction_service.py:84` è già nella 47.
Restano fuori: il `PUT …/access` su un broker che non esiste (403 all'utente, 400 all'admin), comportamento e non testo.
Prove: `api broker-access` **25 passed, 1 skipped** (docstring soltanto); `front check` con W-B37 ✅ (0 errori, 0 avvisi).

### W-B12 — MULTI-008d pulisce i suoi broker ✅ (2026-10-16)

test-author: `backend/test_scripts/test_api/test_broker_multiuser_api.py`, MULTI-008d (`test_cross_broker_access_failure_
is_atomic`) crea i due broker con gli aiuti dei test V-23 (`_Owned`, `_new_broker`, nomi `M008dEditable`/`M008dRestricted`)
e li cancella in un `finally` (con `force`: transazioni e accessi con loro); un errore di pulizia non copre l'errore del
test e, a test verde, lo fa fallire con l'elenco dei rimasti. Asserzioni originali intatte (9 su 9). Prove (`nice`): `db
populate`; `api broker-multiuser test_cross_broker_access_failure_is_atomic` **2/2**, poi nessun broker `M008d%` nel DB
della corsia; `api broker-multiuser` intero **20/20**. Porta libera. Reperto: anche `TestMultiUserRoles`,
`TestEditorRestrictions` e MULTI-007/008b/008c lasciano broker o transazioni → **W-B41**.

> **Coda della notte entrata** (treno 89 in `dev_release2`: `7bed1bdce` W-B37, `60917185c` C-34, `d35e3c8f3` W-B35,
> `8129f8176` W-B12, `0fc27a8b8` journal del coordinatore). Nel mio ramo gli stessi lotti sono `c8da45fc4`, `5d6965b79`,
> `91ae33e34`, `232524cb1`, `7923ae8d4` (HEAD, verificato alle 04:40; worktree pulito). C-34 di Y9, arrivata dopo: già
> fatta; la guardia di Y non è né in `dev_release2` né nella mia base → la voce di `TransactionBulkModal` la toglie Y nel
> suo lotto (detto al coordinatore). Prossimi, come proposto nell'handoff: W-B41, poi W-B38.

### W-B41 — gli altri test di `test_broker_multiuser_api.py` puliscono i loro broker ✅ (2026-10-16) — 🧊 FROZEN

**Analisi** (04:42, codice di `7923ae8d4`): in `backend/test_scripts/test_api/test_broker_multiuser_api.py` 11 test
creano il broker con `create_broker` e non lo cancellano: MULTI-001…005, 007, 008, 008b, 008c (`TestMultiUserRoles`),
009 e 010 (`TestEditorRestrictions`); 007, 008b e 008c lasciano anche un DEPOSIT. MULTI-006 cancella da sé il suo broker
(è il test della cancellazione) e resta com'è: registrarlo farebbe riportare a `drop()` un broker già cancellato.
MULTI-008d (W-B12) e i test V-23 sono già puliti.
**Prima della cura** (prova in corsia, `nice`, carico 40): DB della corsia 41 broker (max id 64), 3 transazioni su broker
`Broker_%`; `api broker-multiuser` **20/20**; dopo: 52 broker (+11, id 65…80, tutti `Broker_<hex>`), 6 transazioni su
`Broker_%` (+3). Letture con `sqlite3 "file:…/app.db?immutable=1"` a server spento (nessun `-wal`). Log
`/tmp/libreFolio_w_wb41_before.log`. Il giro ha anche ricostruito la build debug del frontend (sorgenti cambiati dopo il
treno 89).
**Disegno** (decisione notturna, da rivedere): un context manager asincrono `_owning(label)` accanto a `_new_broker`, con
il contratto del `try/finally` di MULTI-008d e dei V-23 (pulizia anche dopo un rosso, il rosso passa intatto, i rimasti
stampati, un verde con rimasti fallisce), messo per ultimo nell'`async with` (esce a client aperti). Negli 11 test cambiano
solo la riga dell'`async with` e `create_broker(...)` → `_new_broker(<client dell'OWNER>, owned, "MULTI00x")` (nomi
`MULTI00x_<hex>`, riconoscibili): niente rientri, asserzioni intatte. MULTI-008d e V-23 restano col loro `try/finally`.
test-author in corso (04:52), senza corsia.
**Fatto** ✅ (04:56): test-author, solo `backend/test_scripts/test_api/test_broker_multiuser_api.py` (+42 −21): `import
contextlib`; `_owning(label)` fra `_Owned` e `_new_broker`; negli 11 test la riga dell'`async with` (`_owning` per ultimo) e
`_new_broker(<client dell'OWNER>, owned, "MULTI00x")`, anche in MULTI-003 e 009 (dove l'EDITOR tenta la cancellazione).
`create_broker` resta solo per MULTI-006. Il test-author ha provato la semantica del context manager in un frammento a sé
(solo stdlib, niente repo): pulizia prima della chiusura dei client, rosso intatto, verde con rimasti → fallisce, verde
pulito → passa. Effetto collaterale voluto: `_new_broker` verifica 200 e `success` alla creazione. `black` e `ruff` puliti.
**Prova** (05:03, `nice`, carico 55; il DB della corsia era stato ripopolato dal runner E2E di W-B29): prima 8 broker (max
id 8) e 76 transazioni; `api broker-multiuser` **20/20**; dopo 8 broker (max id 8), 76 transazioni, zero broker
`MULTI0%`/`M008d%`/`V23%` (prima della cura: +11 broker, +3 transazioni). Log `/tmp/libreFolio_w_wb41_after.log`.

### W-B29 — `asset-event-delete.spec.ts` su asset propri ✅ (2026-10-16) — 🧊 FROZEN

Slot E2E 2 dato dal coordinatore alle 04:48, **stop duro alle 05:25** (05:30–06:45 macchina ferma: nessuna prova). Build
debug fresca (04:47, ricostruita dal runner su `7923ae8d4`). **Analisi**: lo scenario 1 trova Apple per testo della card e
le scrive un DIVIDEND a oggi − 230 giorni (stessa chiave per desktop e mobile nello stesso giorno → il secondo upsert
sovrascrive il primo); lo scenario 2 usa il DIVIDEND di Apple realizzato da una transazione del mock e marca le righe con
una sonda `isVisible().catch` (un rosso cancellerebbe eventi condivisi). Il modello giusto è
`asset-event-editor-save.spec.ts` (`createOwnedAsset`, `linkDividend`, `deleteOwned`, `afterEach`). Il rosso «prima» non si
mostra senza far girare i due progetti insieme: la prova è statica (lo spec nomina Apple e scrive su di lei). test-author in
corso (04:52): scenari 1 e 2 su un asset proprio, aiuti comuni in un modulo nuovo `e2e/assets/asset-events-owned.ts`, nessun
tocco a `assets-helpers.ts` (di X); poi un solo E2E del file in corsia.
**Fatto** ✅ (04:57): test-author.
- Nuovo `frontend/e2e/assets/asset-events-owned.ts` (non è uno spec): gli aiuti di `asset-event-editor-save.spec.ts` spostati
  tali e quali con `export` (`EVENTS_PATH`, `Owned`, `OwnedAsset`, `StoredEvent`, `jsonFrom`, `createOwnedAsset`,
  `linkDividend`, `deleteOwned`, `seedEvents`, `storedEvents`, `snapshot`, `openEventsEditor`, `eventRow`, `markDeleted`);
  importa solo `API_BASE` da `assets-helpers.ts`, che non cambia. In `asset-event-editor-save.spec.ts` gli aiuti tolti e
  importati; i test non cambiano.
- `asset-event-delete.spec.ts`: `afterEach` con `deleteOwned` (broker con `force`, poi l'asset), titoli invariati. Scenario
  1: asset proprio con un DIVIDEND non collegato a oggi − 20 giorni (marcatore `uniqueSuffix()`), pagina aperta per id, riga
  segnata per id; le asserzioni di prima più «l'evento non è più salvato» letto dall'API. Scenario 2: asset proprio con due
  DIVIDEND, uno realizzato da una transazione su un broker proprio (`linkDividend`) e uno libero, segnati per id (via la
  sonda `isVisible().catch`); le asserzioni di prima (409, `EVENT_IN_USE`, toast d'errore per `data-testid`) più: tutti e
  due in `delete_ids`, in uso esattamente quello collegato, nulla cancellato (istantanee identiche). Scenari 3 e 4 restano:
  leggono soltanto (il 3 apre il menu della card ma non cancella; ha ancora sonde `isVisible().catch` e un filtro per testo
  → residuo, sotto). `prettier` pulito.
**Prove** (slot 2, `nice`, carico 36–55): `front-asset asset-event-delete` **4/4** (39 s, 04:57–05:00, progetto desktop come
fa il runner); `front-asset asset-event-editor-save` **4/4** (05:00–05:02: lo spostamento degli aiuti); `front check` **0
errori, 0 avvisi** (05:13: il tsconfig comprende `e2e/**`, Playwright non controlla i tipi). Build debug del frontend fresca
(nessuna build nello slot). Stop dello slot rispettato (05:20).
**Residuo** → backlog: lo scenario 3 (`delete asset with events shows appropriate warning`) ha sonde `isVisible().catch`, un
`.first()` senza filtro, un filtro per testo `/delete|elimina/i` e può passare senza asserire nulla; lo scenario 4 dipende
dai collegamenti del mock (`.first()` sui pallini degli eventi). Sola lettura: nessun dato condiviso a rischio.

### W-B38 — gli errori multipli della creazione arrivano renderizzati ✅ (2026-10-16) — 🧊 FROZEN

**Analisi** (04:58, codice di `7923ae8d4`): `TXCreateItem.validate_transaction_rules`
(`backend/app/schemas/transactions/transactions.py`), con due o più violazioni, impacchetta in `multipleBusinessRuleErrors`
per ciascuna `e.message_template`: «{type} requires asset_id» arriva così in `TXValidationIssue.error` (batch, spacchettato
in `transactions/transaction_batch_stages.py:45`) e in `BRIMValidationIssue.message` (import, `brim/brim_provider.py:564`).
La UI traduce per codice (`transactions.errors.<code>`, `resolveValidationMessage.ts`) e mostra il testo grezzo solo come
ripiego: la fuga si vede nelle risposte dell'API. Le regole (TX-S-108) non cambiano.
**Rossi** ✅ (test-author; corsia, `nice`, 05:04–05:05): TX-S-109 rovesciato e rinominato `test_packed_messages_rendered`
(i testi impacchettati renderizzati, `ctx` invariato, nessuna `{`; docstring della classe e commento di
`VISIBLE_RULE_MESSAGES` aggiornati) → `schemas transactions` **1 failed** («the user would read ['{type} requires
asset_id']»); nuovo G.3.13 `test_validate_create_multiple_rule_errors_rendered` in `test_transactions_validate.py` (un BUY
senza asset e con quantità 0 su un broker proprio, cancellato in un `finally`; codici e parametri invariati, ogni `error` senza
`{` e col tipo) → `api transactions-validate` **1 failed**, stesso motivo; `test_multiple_errors_produce_multiple_issues` in
`test_brim_create_transaction.py` (+2 righe: ogni `message` senza `{` e col tipo SELL) → `services brim-create-transaction`
**1 failed** («['{type} requires cash.amount > 0']»).
**Cura** ✅ (05:06): `"msg": e.message()` al posto di `e.message_template`; il commento del blocco dice che ogni voce porta il
testo renderizzato con i parametri in `ctx` (W-B38), e quello della regola 10 perde la parentesi «packs the template».
`black` e `ruff` puliti. Nessuna pagina di doc nomina l'impacchettamento.
**Verdi** (`nice`, carico < 64): `schemas transactions` **105/105** (TX-S-108 invariato); `services brim-create-transaction`
**14/14**; `db populate --force --clean` (i `services` svuotano il DB della corsia); `api transactions-validate` **12/12**
(05:12; il runner ha ricostruito la build debug all'avvio). Porta 6184 libera.

> **Prenotazioni ricevute** (coordinatore, 05:13–05:15): T (colori) ha un lotto di sole classi verso le 07:30 sui 4 file di
> `ui/data-editor` (`DataEditor`, `CsvEditor`, `DataImportModal`, `ErasableNumberCell`) e su tre righe di spec
> (`e2e/assets/asset-data-editor.spec.ts:287`, `e2e/fx/fx-csv-import.spec.ts:53,56`): non toccarli finché non entra. Y applica
> Y5/Y6 (`components/brokers/*` → `features/brokers/`, compreso `BrokerImportFilesModal`; `components/lots/*` →
> `features/brokers/lots/`; `BrokerIcon` → `components/ui/display/`; `components/files/*` → `features/files/`; in
> `ImportWizardModal` cambia solo una riga d'import): non toccarli fino al suo ingresso (dopo le 06:45). Nessuno dei due
> tocca il delta di W-B41, W-B29, W-B38. 05:30–06:45 macchina ferma: nessuna prova.

> **Lotti committati** (coordinatore, 05:20): `f2b6c0983` W-B41, `f9969056e` W-B29, `52387e2c0` W-B38, `238ff0381` journal →
> HEAD `238ff0381` (verificato, worktree pulito). I tre cherry-pick su `dev_release2` simulano puliti ed entrano dopo il
> blocco dei colori (destinazione ferma fino alle ~06:45); il journal entra con la 47. Prenotazione nuova: lotto «input» dei
> colori (mattino) su `transactions/form/TxFormSingleSection.svelte`, `TxFormPairSection.svelte`, righe di
> `TransactionFormModal.test.ts` e di `e2e/transactions/transactions-modals.spec.ts`. Durante la sosta (05:30–06:45): le
> analisi in sola lettura di W-B39 e W-B42 (via del coordinatore); `routes/(app)/transactions/+page.svelte` è libero (Y5
> cambia al più la riga d'import di `BrokerIcon`, già sul suo ramo `6f7ac70ce`). Il codice dopo l'aggiornamento della base.

### W-B39 — uno split o una promozione rifiutati lo dicono ✅ (2026-10-16) — 🧊 FROZEN

**Stato reale** (codice di `238ff0381`, sola lettura):
- `frontend/src/routes/(app)/transactions/+page.svelte`: `confirmSplit()` (~437) e `onPromoteMergeConfirm()` (~408, anche
  per `confirmPromote`) chiamano `commitTransactions` (`utils/transactions/txCommitApi.ts`), che ha `toast: false` di
  serie; su `committed=false` scrivono solo `console.error`, la modale (`TransactionActionModal` per lo split,
  `ConfirmModal`/`PromoteMergeModal` per la promozione) resta aperta senza un perché. Anche un errore di rete tace. Sono i
  due soli chiamanti diretti della pagina; il Form e il Bulk mostrano i problemi nei loro riquadri.
- **La promozione ha lo stesso difetto**: la includo (stessa funzione, stessa pagina).
- I problemi si traducono già con `resolveIssueMessage` (`utils/transactions/resolveValidationMessage.ts`), con le chiavi
  `transactions.errors.*` di ogni codice di split e promozione (`typeCannotSplit`, `splitIdsMismatch`, `alreadyPaired`,
  `noPromoteRule`, `promoteRefNotFound`, `accessDenied`, `balanceAssetNegative`, `costBasisRequired`, `wacFxUnavailable`…);
  i toast accettano HTML (icone e bandiere, come i riquadri). Il contesto (`brokers`, `getAllAssets`, icone) si costruisce
  come in `TransactionBulkModal.svelte:1400`; la pagina ha già `brokers` e l'archivio degli asset.
- **Il caso della 47**: `wacFxUnavailable` si traduce «❌ WAC calculation failed.» (il Form aggiunge il link per sincronizzare
  i cambi e «or switch to manual mode», che per uno split non vale): da solo, per uno split, non dice niente. Il problema
  porta `params.pairs` (`services/transactions/batch_costs.py:62-82`).
- Doc utente (`user/transactions/index.en.md:50`, della 47): «If that cost needs an exchange rate LibreFolio does not have,
  the pair stays linked» — non dice come lo si scopre.
**Disegno proposto** (decisione notturna, da rivedere: toast d'errore come le altre azioni della pagina, non un riquadro
nella modale):
1. Sulla pagina, a `committed=false`: un toast d'errore con il titolo che c'è già (`transactions.split.failed`,
   `transactions.promote.failed`) e i problemi tradotti (`resolveIssueMessage`), senza doppioni; su un errore di rete il suo
   messaggio. La modale resta aperta (com'è oggi: si annulla). La composizione in una funzione pura in
   `utils/transactions/` (es. `commitRefusalMessage`), con il suo Vitest.
2. In `resolveIssueMessage`, additivo: `ResolvableIssue.operation?`; per `wacFxUnavailable` su `operation === 'split'` la
   chiave nuova `transactions.errors.wacFxUnavailableSplit` (4 lingue, `dev.py i18n add`), con `{pairs}`: «le unità che
   escono prendono il costo medio, che chiede il cambio {pairs}: sincronizza i cambi, poi riprova». Vale anche nel Bulk.
   Prima dell'ingresso della 47 il ramo non si raggiunge, ma non dipende dal suo codice: il commit entra da solo.
3. Test (test-author): Vitest in `resolveValidationMessage.test.ts` (lo split prende il testo nuovo coi `pairs`, una
   creazione tiene quello di oggi) e della funzione nuova; un E2E nuovo `e2e/transactions/tx-split-refusal.spec.ts` (non
   `transactions-modals.spec.ts`, prenotato dai colori): coppia TRANSFER propria via API, split dal menu della riga
   (`context-menu-action-split`, `tx-action-modal-confirm`), il commit intercettato con `route.fulfill` (`committed:false`,
   un problema `wacFxUnavailable` sullo split: niente 47 e niente dati sui cambi) → `toast-error` visibile, nessuna `{`, la
   coppia (`USD`, parametro, non testo tradotto), la modale aperta; lo stesso per la promozione di due righe proprie.
   Pulizia in `afterEach`. Precedenti di `route.fulfill`: `tx-selection-after-bulk.spec.ts`, `tx-broker-icon-hydration.spec.ts`.
4. Doc (docs-writer, EN): una frase vicino alla riga 79 di `user/transactions/index.en.md` («If a Promote pair or a Split pair
   is refused, nothing changes and an error message says why.»), lontana dalle righe della 47 (cherry-pick pulito); IT/FR/ES
   a mano e `translate-stamp`, come C-89.
5. CHANGELOG 🐛: «A refused Split pair or Promote pair now says why: until now the confirmation stayed open with no message.»
**Prove previste**: Vitest dei due file, `front check`, `i18n check`, gate dei colori, E2E del file nuovo (slot), `mkdocs
build` e `check-links`.

**Via del coordinatore** (05:21) al disegno proposto: funzione pura in `utils/transactions/` + Vitest,
`wacFxUnavailableSplit` con `i18n add`, `tx-split-refusal.spec.ts` con coppia propria e `route.fulfill`, frase vicino alla
riga 79; il toast invece del riquadro va nella lista come decisione notturna. Codice da scrivere dopo il suo commit di merge,
anche durante la sosta; Vitest, `mkdocs build` ed E2E dopo le 06:45.
**Base aggiornata** (05:22–05:24): merge di `dev_release2` (`72e66d1a6`) aperto dal coordinatore su `238ff0381`; un conflitto
in `mkdocs_src/docs/developer/architecture/overview.md`, l'elenco degli `STARTUP_STEPS`: tenuti tutti e due, nell'ordine del
codice fuso (`app_lifespan.py:207-215`): 11 `lone-transfer-legs` (47), 12–15 invariati, 16 `idle-monitor` (Z). Rivisti i
file fusi da soli cambiati da tutte e due le parti: rispetto a `dev_release2` restano solo le aggiunte della 47 (5 file; le
righe tolte sono testi della merge-base riscritti dalla 47); gli altri identici; ogni voce W del backlog una volta sola.
Messo in stage solo `overview.md`; commit di merge del coordinatore `b8dd7bdc4` (genitori `238ff0381` + `72e66d1a6`),
verificato. `mkdocs build` dopo le 06:45.
**Cura pronta, non applicata** (05:27): `/tmp/libreFolio_w_wb39_cure.py` (dry run pulito, 3 file, ogni modifica trovata una
volta): nuovo `frontend/src/lib/utils/transactions/commitRefusal.ts` (`commitRefusalMessage`: titolo scappato, poi una riga
«• motivo» per ogni motivo distinto, da `resolveIssueMessage`; senza problemi l'errore di rete; il toast rende HTML
sanificato con `whitespace-pre-line`); `resolveValidationMessage.ts` (`ResolvableIssue.operation?`; `wacFxUnavailable` su uno
`split` prova `transactions.errors.wacFxUnavailableSplit`, poi la chiave generica); la pagina (`issueContext()` come il
contesto del Bulk, toast d'errore al posto dei due `console.error`; la modale resta aperta); con `--apply`, `dev.py i18n add`
della chiave nelle 4 lingue (lessico dei cataloghi: IT «Scollega coppia», «tassi FX»; FR «Séparer la paire»; ES «Separar
par»). Si applica dopo i rossi delle 06:45.
**In corso** (05:28): test-author (rossi: Vitest del risolutore, Vitest nuovo della funzione, E2E nuovo con `route.fulfill`,
registrazione nel runner; nessun comando che carichi la macchina, niente file prenotati); docs-writer (la frase EN in fondo
alla riga 79 di `user/transactions/index.en.md`; IT/FR/ES a mano da me, `translate-stamp` dopo le 06:45).
**Doc** ✅ (05:33): docs-writer, `user/transactions/index.en.md:79`, in fondo allo stesso paragrafo: «If a **Promote pair**
or a **Split pair** is refused, nothing changes: an error message says why, and the confirmation stays open.» (la pagina non
ha una riga di data); IT, FR, ES a mano sulla stessa riga 79 (lessico delle pagine: «Promuovi coppia»/«Scollega coppia»,
«Promouvoir la paire»/«Séparer la paire», «Promover par»/«Separar par»); solo la riga 79 in tutte e quattro, la riga 50 della
47 intatta. Doc per sviluppatori: nessuna pagina descrive come la pagina riporta un commit; il solo posto adatto alla riga
«`wacFxUnavailable` su `split` prova prima `wacFxUnavailableSplit`» è `developer/backend/transactions/split_promote.md:90-94`,
che viene dal commit della 47 (`8b3e6b766`) → quella riga entra con la 47 (residuo annotato qui). `translate-stamp` della
pagina dopo le 06:45.
**Rossi scritti** (05:48, test-author, niente eseguito: macchina ferma):
- `frontend/src/lib/utils/transactions/resolveValidationMessage.test.ts`: un `describe` W-B39. (a) rosso: `wacFxUnavailable`
  su `split` col testo dello split e i `pairs` (oggi il generico); (b) e (c) guardie verdi (su `create` il generico; split
  senza chiave dello split → il generico).
- Nuovo `frontend/src/lib/utils/transactions/commitRefusal.test.ts` (10 casi del contratto, compreso «un errore di rete
  uguale al titolo non aggiunge niente», chiesto da me dopo il dubbio 2 del test-author: la pagina passa come ripiego il
  titolo stesso → nella cura `networkError !== title`): oggi non si carica (modulo assente, codice nuovo).
- Nuovo `frontend/e2e/transactions/tx-split-refusal.spec.ts`: S1 (split della coppia TRANSFER finanziata di
  `fixtures/owned-pair.ts`, `openAccountWithPair`, rifiuto `wacFxUnavailable` servito da `page.route` su `POST
  /transactions/commit` con un `TXBatchResponse` valido per lo schema: il client valida le risposte, `validate:
  'response'`) e P1 (promozione di un WITHDRAWAL e un DEPOSIT gemelli su due broker propri, rifiuto `accessDenied` col
  broker); conto usa e getta, `afterEach` con broker `force` e conto; rossi attesi a `toast-error` visibile (5 s).
  `data-testid` della promozione: `dt-row-checkbox-tx-{id}`, `toolbar-action-promote`, `confirm-modal-confirm/cancel`.
- Runner: `scripts/test_runner/_frontend_transaction.py` (azione `tx-split-refusal`), `_frontend_utility.py` (una riga
  in `core-unit`, dopo `resolveValidationMessage.test.ts`): righe aggiunte soltanto.
- Lacune di `data-testid` viste (non mie da chiudere ora): `ConfirmModal` senza prop `testId`; `promote-merge-modal`
  su due elementi, il suo «Annulla» senza testid.
**Alle 06:45, in ordine** (carico < 70, una prova alla volta): Vitest dei due file (rossi); E2E `front-transaction
tx-split-refusal` (rossi); `python3 /tmp/libreFolio_w_wb39_cure.py --apply` (file + `i18n add`); Vitest (verdi);
`prettier`; `front check`; `i18n check`; gate dei colori; E2E (verdi); `check-orphans`; `mkdocs build`, `check-links`;
`translate-stamp --file user/transactions/index.en.md`.
**Ordine rivisto** (coordinatore, 05:50: gli E2E solo nel suo slot 2, col suo via, ~10–15 minuti, perché ricostruiscono
il frontend; prima le prove leggere, subito dopo il «blocco finito» dei colori; uno script con un orario di taglio). Per
tenere il rosso prima della cura anche nell'E2E, la cura è divisa in due (`--part A|B`, dry run puliti):
- **A** (livello unità: la funzione, il risolutore, la chiave) nella fase leggera: `/tmp/libreFolio_w_light.sh` → Vitest
  rossi, A applicata, Vitest verdi, `prettier`, `front check`, `i18n check`, gate dei colori, `check-orphans`, `mkdocs
  build`, `check-links`;
- **B** (il cablaggio della pagina, ciò che vede l'E2E) nello slot: `/tmp/libreFolio_w_slot.py --until HH:MM
  [--with-wb42]` → E2E rosso (B si applica solo se il rosso è quello del toast W-B39), B, E2E verde, E2E di W-B42,
  `front check` se resta tempo; prima di ogni passo il tempo stimato e il carico; al taglio SIGINT al gruppo del passo.
**Niente `translate-stamp`** (decisione notturna, da rivedere): la cache di Aphra tiene un hash per pagina EN; la pagina ha
il debito della 47 (riga 50, solo EN): uno stamp lo nasconderebbe. La pagina resta in debito; le frasi IT/FR/ES a mano
restano.
**Eseguito** (via del coordinatore 06:48, «blocco finito»; slot 2 fino alle 07:10, poi slot 1 fino alle 07:20):
- **Rossi Vitest** ✅ (06:50, carico 51): `vitest run` dei due file → 1 fallito per il motivo atteso («expected 'WAC
  calculation failed.' to contain 'Average cost of the units that leave …'»), `commitRefusal.test.ts` non si carica («Cannot
  find module './commitRefusal'»); le guardie (b) e (c) verdi, 52 passati. Log `/tmp/libreFolio_w_wb39_vitest_red.log`.
- **Parte A** ✅ (06:51): `commitRefusal.ts`, `resolveValidationMessage.ts`, `dev.py i18n add` della chiave (una riga in
  ciascuna delle 4 sorgenti `frontend/src/lib/i18n/transactions/*.json`). **Verdi**: `vitest run` dei due file **63/63**;
  `prettier --write` (riformattati `commitRefusal.test.ts` e i due spec, che i test-author non potevano formattare durante la
  sosta), poi `--check` pulito.
- **E2E rosso** ✅ (slot 2, 06:51:55–07:05:34, 820 s): `front-transaction tx-split-refusal` **2 falliti su 2 al punto
  atteso**: S1 (split) e P1 (promozione), «W-B39: a refused split/promote raises an error toast», `toast-error` non visibile
  in 5 s, nessun retry; le asserzioni sul payload passate prima. Il tempo: due build debug di vite (2m14s e 3m25s) e la doc
  (173 s, stantia per le frasi della riga 79), col carico a 48–73. Log `/tmp/libreFolio_w_slot_e2e-red.log`.
- **Parte B** ✅ (07:05:34): il cablaggio della pagina (`issueContext()`, i due toast d'errore). L'E2E verde saltato dallo
  script per il taglio delle 07:10 (263 s rimasti < 360 stimati).
- `front check` ✅ (07:06–07:08, fuori slot, con B dentro): **0 errori, 0 avvisi**.
- **E2E verdi** ✅ (slot 1, 07:08:45–07:19): `tx-split-refusal` **2/2** (437 s, con la ricostruzione); `front-asset
  asset-event-delete` **4/4** (182 s) per W-B42.
- **Prove leggere** ✅ (07:20–07:24, una alla volta, `nice`, carico < 70; `/tmp/libreFolio_w_light2.sh`): `prettier --check`
  sugli 11 file del frontend pulito; `i18n check` (4751 chiavi, strict); gate dei colori pulito; `check-orphans` (461 file
  Vitest e 132 spec E2E raggiungibili); `mkdocs build` strict (137 s); `check-links` (97 validi); `git diff --check` pulito;
  porta libera. `black`/`ruff` sui due file del runner: `_frontend_utility.py` pulito; in `_frontend_transaction.py` i
  rilievi ci sono già in HEAD (black riformatterebbe le stesse 50 righe della vecchia lista di `front_tx_unit`; ruff 4
  PLC0415, import locali di `db_populate`), le righe nuove sono pulite: il file condiviso non si riformatta.
**Cherry-pick**: i file di W-B39 sono identici fra HEAD e `dev_release2`, tranne `user/transactions/index.en.md`, che
differisce per la riga 50 della 47; la frase nuova è alla riga 79, il contesto coincide. La pagina non importa `BrokerIcon`
(Y5 non la tocca).
**Residui**: la riga per sviluppatori in `developer/backend/transactions/split_promote.md` entra con la 47 (sopra); i
`data-testid` mancanti di `PromoteMergeModal` → **W-B44**; `ConfirmModal` senza prop `testId` (UI condivisa) → al
coordinatore.

### W-B42 — gli scenari 3 e 4 di `asset-event-delete.spec.ts` ✅ (2026-10-16) — 🧊 FROZEN

- Scenario 3 (`delete asset with events shows appropriate warning`): ogni passo è dentro un `if` su una sonda
  `isVisible().catch(() => false)`, con `.first()` senza filtro e un filtro per testo `/delete|elimina/i`: passa sempre, anche
  se non trova niente; non verifica l'avviso del titolo. **Proposta**: asset proprio con un evento (e una transazione
  collegata, `linkDividend`), card cercata per id (`asset-card-{id}`), menu della card → «elimina» per `data-testid`
  (`context-menu-action-delete` o quello della card), l'avviso della conferma visibile per `data-testid`, annulla, l'asset
  ancora presente (API). L'interfaccia della cancellazione degli asset è di X: solo il test cambia.
- Scenario 4 (`event badge reflects current link state`): verifica soltanto che il primo pallino abbia un `data-testid` ben
  formato, sui collegamenti del mock. Il pallino porta l'id della transazione (`TransactionsTable.svelte:716`,
  `tx-event-dot-${tx.id}`). **Proposta**: un DIVIDEND proprio collegato a un evento proprio (`linkDividend`) →
  `tx-event-dot-{txId}` visibile; scollegato via API (`asset_event_id: null`) e ricaricata la pagina → il pallino sparisce:
  lo «stato del collegamento» del titolo.
- Nessuno dei due scrive su dati condivisi oggi: è un debito di qualità, non un rischio. Peso: minimo; dopo W-B39.

**Riscritti** (06:07, test-author, niente eseguito: macchina ferma; via del coordinatore alle 05:21, «poi W-B42»): solo
`frontend/e2e/assets/asset-event-delete.spec.ts` (+156 −50), titoli invariati, scenari 1 e 2 e `asset-events-owned.ts`
intatti.
- Scenario 3: asset proprio con un DIVIDEND (verificato), card `asset-card-<id>` visibile; la cancellazione parte dalla riga
  della vista a elenco (`view-mode-list`, ricerca `assets-search-input` col nome unico, `row-actions-<id>` →
  `context-menu-action-delete`: stesso gestore della card, il cui cestino non ha `data-testid`); la conferma
  (`confirm-modal-message`) col nome dell'asset e nessuna `{`; annulla; asset ed evento ancora salvati (API).
- Scenario 4: DIVIDEND proprio collegato (`linkDividend`), `/transactions?broker_id=<proprio>`, `tx-event-dot-<txId>`
  visibile; scollegato con un commit `{updates: [{id, asset_event_id: 0}]}` (**`null` in un update vuol dire «non
  cambiare»**: lo `0` scollega, come fa l'editor), riletto; ricaricata la pagina, il pallino ha conteggio 0, la riga c'è,
  l'evento resta.
- **Comportamento trovato** (UI degli asset, di X; solo lettura): la conferma della cancellazione di un asset non nomina gli
  eventi (testo fisso «Provider assignments and price history will be removed»), che spariscono in cascata senza avviso;
  una transazione blocca la cancellazione solo dopo la conferma; l'etichetta «N assets» della conferma multipla è inglese
  scritta a mano; cestino della card e conferma singola senza `data-testid` → al coordinatore per la sezione di X.
Prova: E2E `front-asset asset-event-delete` nello slot. ✅ (slot 1, 07:16–07:19): **4/4** (182 s; scenario 3 19,0 s,
scenario 4 8,7 s), al primo giro; `prettier` pulito (riformattato alle 06:51), `front check` 0/0.
