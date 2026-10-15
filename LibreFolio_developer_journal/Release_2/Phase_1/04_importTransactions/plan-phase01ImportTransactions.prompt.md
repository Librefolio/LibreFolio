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
