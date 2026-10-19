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

Rimessa in pari il 19/10 (riconciliazione della ripartenza, base `3d5678283`): lo stato di ogni lotto letto nei commit di
`dev_release2`, con la prova. Le voci del backlog hanno i loro ✅ nella sezione W di `BACKLOG_POST_1.2.md`.

| # | Lotto | Contenuto | Stato |
|---|---|---|---|
| W0 | Base e piano | questo piano; misure di base nella corsia | ✅ 14/10, `64e3d0a7d` |
| W1 | CP1, rinomina | `services/transactions/`, `services/brokers/`, via l'hub; import, runner, script, doc, `.github`, devWiki | ✅ 15/10, `9a44bdcec` |
| W2 | CP2, taglio | mixin per tema (C4); broker in CRUD, summary, accessi; stadi del batch per tema | ✅ 15/10, in dev prima di `d036d4896` |
| I1 | CP3, integrità | V-23, C-65b, L5, C-79/C-3 | ✅ 15/10, dev `dc7e4e48e` |
| K1 | CP4, chiarezza | O-12, C-89, V-38, P-15 (W); I-10 S3 chiusa senza codice | ✅ 15/10, `532a1fd9c`, registro `0229dbc6a` |
| W3 | CP5, router | `api/v1/brokers/` per risorsa | ❌ **non fatto**: aspettava un commit del coordinatore su `brokers.py` che non è venuto, poi la coda dei difetti l'ha superato. `api/v1/brokers.py` è ancora un file solo |
| W4 | CP6–CP7, PL5 | `services/brim/`, rinomina poi taglio con guardia; `applyTo`, skill, guida (U-B8) | 🟡 CP6 (la rinomina) ✅ 15/10, registro `0902524e5`; **CP7 (il taglio di `brim_provider.py` per tema) non fatto**: aspettava lo stesso commit di W3 |
| W5–W6 | CP8 | U-B3, U-B4 | ❌ **non fatto**: `brim_providers/static/` e `brim_providers/sample_reports/` sono ancora alla radice della famiglia (verificato il 19/10); aspettava il commit su `uploads.py` |
| K2 | CP9 | C-70 (a, b), e (c) dopo il CP1 di H | 🟡 K2a ✅ 15/10 (`0eac8e1b6`, registro `e7cf1ae80`); **K2b** (il 400 strutturato del parse e `preview_unreadable_workbook`) e **K2c** non fatti: aspettavano il commit su `brokers.py` e `uploads.py` |
| W7 | CP10 | schemi delle transazioni come pacchetto (C3) | ✅ 15/10, registro `58be885a9` |
| E1 | CP11 | eventi: I-09, I-12, V-22, I-10, I-11 | ✅ 15/10: E0 dev `d226bc69e`, E1a ed E1c dev `14d58cc61`, E1b dev `fecf88c1a` |
| FE8a | CP12–CP13 | tagli delle tre modali (annuncio §7), poi la cartella dopo il lotto A | ✅ 15/10, dev `14d58cc61` |
| K3 | CP14… | V-37b, eventi collegabili nel Bulk, C-65a, K-2..K-4; se c'è spazio C-45, C-61, V-24, P-2, P-12 | ⏸️ **parcheggiato il 19/10** (N91): K3a in patch nella cartella di sessione, K3b e K3c dopo la lettura del developer; C-65a con X dopo |
| FE8b | finale | moduli usati fuori + `features/transactions/index.ts` (dopo il lotto D); P-14, U-B9 | ✅ 16/10 lo spostamento, dev `31335fe26` (`index.ts` superato da D-P4); **P-14 e U-B9**, lotti piccoli a parte, aperti |

**Lotti aggiunti durante la 1.3** (dalla coda del coordinatore; prove dei singoli treni nel backlog):

| Lotto | Contenuto | Stato |
|---|---|---|
| N1 + N1b | cassa della pagina broker (W-B5), TRANSFER orfano (V-3), correzioni post-migrazione (W-B6, W-B22, W-B23) | ✅ 15/10, dev `14d58cc61` |
| N2 | il costo obbligatorio anche nell'API | ✅ 15/10, dev `f421e418a` |
| F36 | i file dei broker solo a chi vede il broker (W-B3, W-B4) | ✅ 15/10, dev `434af2925` |
| W-B20 | la cancellazione dei broker atomica per broker | ✅ 15/10, dev `23ff56b95` |
| Doc A-14 | W-B10, W-B27 (le chiavi), W-B33, W-B35 | ✅ 16/10, dev `6fa3f8936` |
| W-B31 + W-B36 | le regole 5–12 lette dai metadati dei tipi | ✅ 16/10, dev `4e69b5271` |
| Treni piccoli del 16/10 | W-B12, W-B17, W-B29, W-B30, W-B32, W-B37, W-B38, W-B39, W-B41, W-B42, W-B44, W-B45, W-B53 | ✅ 16/10, treni 98–111 |
| Decisione 47 | la gamba che cede convertita al costo | ✅ 16/10, dev `ea72346b7` |
| C-97a | quantità a 10 e prezzi a 12 decimali; il costo Auto | ✅ 16/10, dev `c91bd41b2` |
| C-97b | i decimali in input | ✅ 17/10, dev `b2462042d` |
| C-97c-1…3 | prezzi e quantità, lotti, asset e grafici | ✅ 17/10, dev `f1bfa1e31`, `016fe7af9`, `e19f7c7e6` |
| W-B58 + W-B59 | la revisione R13-SEC2 | ✅ 17/10, dev `4e9d1815f` |
| W-B60 | importi e valori degli eventi letti esatti | ✅ 17/10, dev `484c71afb` |
| W-B69 | il costo Auto su un pool illeggibile; la metà del batch | ✅ 17/10, dev `c61a2db4d`, `eee5dad17` |
| R13-SEC7-3 | i limiti d'ingresso, il giro dei giorni, le date | ✅ 17/10, dev `e609082ab` |
| W-B71 | le finestre di date ai bordi del calendario | ✅ 17/10, dev `1431e20df` |
| W-B74 | i saldi su righe illeggibili | ✅ 17/10, dev `80cee9c2d` |
| W-B72 | N78: un costo dove il tipo non lo prende | ✅ 17/10, dev `7bc66c7ca`, `5603a23a7` |
| W-B67 | il costo Auto sulla riga giusta (N84) | ✅ 17/10, dev `ac92e6fae` |
| W-B66 | gli esponenti incollati | ✅ 17/10, dev `e820279e1` |
| W-B68 | i valori degli eventi del fornitore troncati alla colonna | ✅ 17/10, dev `06e9d2c20` |
| W-B70 (+ W-B73, W-B77) | i parametri degli errori, il limite dell'unione | ✅ 17/10, dev `41335f1e1` |
| W-B48 + W-B51 | i testid negli spec; i doppioni BRIM delle crypto | ✅ 17/10, dev `4bc6b2ab1` |
| W-B81 | i doppioni del wizard con la regola di W-B51 | ✅ 17/10, dev `5890d512c` |

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

> **W-B39 e W-B42 committati** (coordinatore, 07:27): `df898b445` W-B39, `3564129b5` W-B42, `e7e03b19a` journal → HEAD
> `e7e03b19a` (verificato, worktree pulito); in `dev_release2` per cherry-pick `c881237a9`, `9df17ef20` (treno 98), CHANGELOG
> con la riga proposta; il journal entra con la 47. Le 4 note sulla UI degli asset vanno a X, il `testId` di `ConfirmModal` alla
> sezione C. Via a: W-B44, analisi di W-B32, W-B43 dopo W1-g di T.

### W-B44 — `PromoteMergeModal`: un solo `promote-merge-modal`, e Annulla col suo `data-testid` ✅ (2026-10-16) — 🧊 FROZEN

**Analisi** (07:30, codice di `e7e03b19a`): `frontend/src/lib/components/transactions/modals/PromoteMergeModal.svelte` mette
`promote-merge-modal` su `ModalBase` (`testId`, reso sul `role="dialog"`, `ModalBase.svelte:237`) e sul `div` interno (riga
105): due elementi. Il pulsante Annulla (~259) non ha `data-testid`. Chi lo usa: `e2e/gallery.spec.ts:3378`
(`[data-testid="promote-merge-modal"][role="dialog"]`: il `ModalBase`), `tx-selection-after-bulk.spec.ts:492` e
`tx-split-refusal.spec.ts:294` (`toHaveCount(0)` a modale chiusa), `tx-bulk-promote-exec.spec.ts:357` (un commento che
spiega il giro attorno al doppione). Il file non è tenuto dai colori (coordinatore).
**Disegno**: il `div` interno diventa `promote-merge-modal-content` (come `tx-action-modal-content`), il `ModalBase` tiene
`promote-merge-modal` (la galleria continua a funzionare), Annulla prende `promote-merge-cancel`; il commento di
`tx-bulk-promote-exec.spec.ts` si aggiorna. Nessuna classe toccata. Cura pronta in `/tmp/libreFolio_w_wb44_cure.py` (dry run
pulito, 2 file). Rosso: un Vitest nuovo `PromoteMergeModal.test.ts` (test-author, in corso), registrato in `front_tx_unit`.
**Rosso** ✅ (07:38, carico 34): test-author, `frontend/src/lib/components/transactions/modals/PromoteMergeModal.test.ts`
(nuovo, 4 test, registrato in `front_tx_unit` di `scripts/test_runner/_frontend_transaction.py`, una riga dopo
`PromoteAllModal.test.ts`): `vitest run` **3 falliti, 1 passato** per i motivi attesi: «elements carrying
data-testid="promote-merge-modal": expected 2 to be 1», «…promote-merge-modal-content: expected +0 to be 1»,
«…promote-merge-cancel: expected +0 to be 1»; la guardia di Conferma (d) verde (`onConfirm` una volta con
`{description: 'Savings out\nSavings in', tags: ['savings', 'monthly', 'transfer']}`, `onCancel` mai).
**Cura** ✅ (07:39): `/tmp/libreFolio_w_wb44_cure.py --apply` (il `div` interno → `promote-merge-modal-content`, Annulla →
`promote-merge-cancel`, il commento di `tx-bulk-promote-exec.spec.ts:357`). **Verdi**: `vitest run` **4/4**; `prettier`
pulito sui 3 file; `front check` 0 errori, 0 avvisi; gate dei colori pulito; `check-orphans` (462 file Vitest
raggiungibili); `git diff --check` pulito. `black`/`ruff` su `_frontend_transaction.py`: nessun rilievo nuovo (ruff 4 = HEAD;
black +2 righe di diff = l'elemento in più dentro la vecchia lista non formattata da black, che black riformatterebbe già in
HEAD). E2E non girati: nessun selettore usa l'id del `div` interno (grep), la galleria legge il `ModalBase` (invariato), gli
altri spec `toHaveCount(0)` a modale chiusa o `promote-merge-confirm` (invariato). I file sono identici in `dev_release2`:
cherry-pick pulito.

### W-B32 — i report senza broker nella lista di ogni broker ✅ (2026-10-16) — 🧊 FROZEN

**Stato reale** (codice di `e7e03b19a`, sola lettura):
- `brim_provider.list_files(broker_ids=…)` (`backend/app/services/brim/brim_provider.py:1068-1071`) tiene i file del filtro **e**
  quelli senza broker («legacy»). Tre chiamanti passano `broker_ids`: `delete_files_for_brokers` (:1277) e
  `brim_report_sets.collect_members` (:128) filtrano già per uguaglianza su `target_broker_id`; la rotta `GET
  /brokers/import/files` (`backend/app/api/v1/brokers.py:676-714`) no.
- La rotta, per chi non è admin, passa **sempre** una lista (i broker accessibili, o la loro intersezione col filtro), anche
  senza filtro nella richiesta; poi tiene i file senza broker solo se caricati dall'utente (decisione 36). Quindi togliere i
  file senza broker dentro `list_files` quando c'è `broker_ids` li nasconderebbe anche nella pagina File, a chi li ha
  caricati: rottura della decisione 36. La correzione va nella rotta.
- Frontend: il wizard d'import (`ImportWizardModal.svelte:3475` e `:3778`) li scarta già sul client; la pagina File
  (`routes/(app)/files/+page.svelte:335`) chiama senza filtro; **solo** «Uploaded Reports» del broker
  (`BrokerImportFilesModal.svelte:95`, `broker_ids: [brokerId]`) li mostra, sotto **ogni** broker (i propri per l'utente,
  tutti per l'admin), e la sua cancellazione multipla può cancellare un file che non è di quel broker.
- Test: le guardie F36-04/05 (`test_brim_api.py:3165`, `:3191`) leggono la lista senza filtro → invariate; F36-01 (gli altri
  utenti non li vedono, con e senza filtro) invariata. Diventano superati due commenti: l'aiuto di `test_brim_api.py:1170`
  («the list also returns legacy files…») e `ImportWizardModal.svelte:3774` (FE8; Y5 cambia un import nello stesso file).
**Proposta** (comportamento visibile → decisione del developer o del coordinatore se la ritiene dentro la decisione 36):
nella rotta, con un `broker_ids` esplicito nella richiesta, i file senza broker restano fuori (una riga, prima del ramo
dell'admin); senza filtro tutto com'è (la pagina File: i propri per l'utente, tutti per l'admin). `list_files` invariata.
Rosso prima (test-author, nella classe F36 col `planter`): il caricatore e l'admin, con `broker_ids` del proprio broker, non
vedono il file senza broker; senza filtro sì (guardie esistenti). Doc: docs-writer (dove la doc descrive la lista dei report
di un broker). CHANGELOG 🐛: «A broker's report list no longer shows the reports an older version stored without a broker:
they stay on the Files page.» Peso: minimo.
**Approvata** (coordinatore, 07:32): dentro la decisione 36, **«Decisione notturna, da rivedere»**: con `broker_ids`
esplicito i report senza broker fuori, senza filtro invariato, `list_files` intatta; rosso prima nella classe F36, guardie
F36-01/04/05 invariate, doc con docs-writer; dopo W-B44, commit separati. Cura pronta in `/tmp/libreFolio_w_wb32_cure.py`
(dry run pulito: la docstring della rotta e il filtro di tre righe prima del ramo dell'admin). Rosso: test-author in corso
(07:34), senza corsia.
**W-B44 committato** (coordinatore, 07:43): `911252a85` sul ramo (HEAD, verificato), cherry-pick `df6e2df10` in
`dev_release2` (treno 99). Le righe del journal di W-B44 restano col prossimo commit del journal.
**W-B32, preparazione dello slot** (slot 2 verso le 08:30, dopo J ed E5b, chiamato dal coordinatore):
- Rosso scritto ✅ (07:41, test-author, niente eseguito): F36-16
  `TestReportsWithoutBroker::test_the_list_of_a_broker_leaves_out_a_file_with_no_broker` in
  `backend/test_scripts/test_api/test_brim_api.py`, parametrizzato su `uploader`/`administrator`: U possiede B con un report
  caricato; un file senza broker di U piantato (`planter`); barriere: chi legge rilegge il file e lo vede senza filtro
  (F36-04), il report di B è nella lista filtrata; il rosso: `legacy.file_id not in listed` con `broker_ids` = B; poi ogni
  voce della lista è di B; pulizia in `finally` (report e broker; il file piantato lo spazza il `planter`). In più: la
  docstring dell'aiuto `_files_on` (~1170) resa vera prima e dopo la cura; W-B32 nel titolo della «Category 18» e nella
  docstring del modulo. `black`/`ruff` puliti.
- Il server di test ricostruisce la build debug quando è stantia a ogni avvio (`dev.py server --test --build-only`,
  `scripts/test_runner/_server.py:179`), e W-B44 ha cambiato `src/`: anche il rosso di `api brim` la ricostruisce → slot. La
  doc si ricostruisce se un `.md` è più recente di `mkdocs_src/site/index.html` (`dev.py:2299`): la `mkdocs build` strict
  fuori slot, dopo la doc di W-B32, la rende fresca e toglie ~2,5 minuti allo slot.
- Script `/tmp/libreFolio_w_slot_wb32.py --until HH:MM` (dry run pulito): rosso F36-16 (`api brim list_of_a_broker`; la
  cura solo se fallisce l'asserzione di F36-16 e solo i suoi 2 casi) → cura → `api brim` intero (116 test, ~3 minuti di
  pytest l'ultima volta), o solo la classe F36 se l'intero non ci sta; carico < 70 prima di ogni passo; SIGINT al taglio.
- **Doc** ✅ (07:51, docs-writer, niente eseguito): `developer/backend/brim/architecture.md` (169–173, «The list.»: la frase che
  dava il vecchio comportamento come voluto è riscritta, con una nota «Before 1.3 … (W-B32)» come le altre della pagina);
  `user/brokers/import.en.md:58` (un paragrafo in fondo a «🗂️ Uploaded reports»: i report che una versione precedente ha
  salvato senza broker non sono in questa lista, chi li ha caricati e gli admin li trovano nella pagina File);
  `user/files/index.en.md:69` (una frase: compaiono solo lì). Controllate e lasciate: `access_control.md:39-41`,
  `frontend/components/features/brokers/modals.md:155-173` (diventa vera), e altre 12 pagine. Reperto: l'upload chiede un
  broker da `f0b7aad8d` (24/01), lo stesso commit che registra chi carica: nessun file senza broker ha un caricatore
  registrato, quindi in pratica li vedono solo gli admin (il test F36-16 pianta un file con caricatore: copre il ramo).
- IT/FR/ES a mano (07:52) sulle due pagine utente, col lessico di ciascuna: `user/brokers/import.{it,fr,es}.md` (paragrafo
  dopo la riga 56) e `user/files/index.{it,fr,es}.md` (fine della riga 44). Cache di Aphra: `import.en.md` senza altro debito
  (md5 di HEAD = cache, 3 lingue fatte) → `translate-stamp --file user/brokers/import.en.md`, solo dopo un `--dry-run` che
  nomina quella pagina sola (senza `--file` lo stamp prende tutte le pagine del nav); `files/index.en.md` ha già debito
  (`14819e3b0`, la sezione «Shared or personal») → niente stamp.
- `/tmp/libreFolio_w_docs_gate.sh 08:25` in corso (07:52): `mkdocs build` strict, `check-links`, il dry run e lo stamp, ognuno
  col carico < 50 (regola delle 07:48) e attese di 60 s; si arrende alle 08:25 per non toccare lo slot.
- Prove della doc ✅ (07:53–07:55, carico 27–35): `mkdocs build` strict (68 s), `check-links` puliti; dry run dello stamp: «1
  file(s) would be stamped … user/brokers/import.en.md (MD5 2fb763ba→6327ae7e)» per it, fr, es (la mia guardia nello script
  cercava il percorso a inizio riga, la riga comincia con «🔍»: lo stamp vero l'ho lanciato a mano, col carico a 35) →
  «Stamped 1 file(s)»: in `mkdocs_src/aphra-pipeline/.translate-hashes.json` (tracciato e condiviso) cambia solo la voce di
  quella pagina (md5 e `stamped_at` per lingua). `git diff --check` pulito. La doc è fresca per lo slot (la build segue le
  modifiche delle traduzioni).
- **Slot 2** ✅ (08:02–08:13, taglio 08:18; `/tmp/libreFolio_w_slot_wb32.py --until 08:18`): **rosso** F36-16 `api brim
  list_of_a_broker` → **2 falliti su 2** (caricatore e admin) sull'asserzione attesa («a report with no broker shows in the list
  of broker 11 … as the uploader reads it», «… broker 12 … as the administrator reads it»), 116 deselezionati, 361 s con la
  ricostruzione della build debug; **cura** (`/tmp/libreFolio_w_wb32_cure.py --apply`: la docstring della rotta e il filtro di
  tre righe); **verde**: `api brim` intero **118/118** (250 s; F36-16 e le guardie F36-01/04/05 dentro, la sola classe non
  serviva). Log `/tmp/libreFolio_w_slot_red-f36-16.log`, `/tmp/libreFolio_w_slot_green-api-brim.log`.
- Prove leggere ✅ (08:13–08:16, carico < 50): `black`/`ruff` puliti su `brokers.py` e `test_brim_api.py`; `api sync` (nessuna
  differenza tracciata: client e `openapi.json` ignorati); `front check` 0 errori, 0 avvisi; `git diff --check` pulito; porta
  libera. I file di W-B32 sono identici fra HEAD e `dev_release2`: cherry-pick pulito.

> **W-B32 committato** (coordinatore, 08:18): `77fbc8687` sul ramo, cherry-pick `84d24ed03` in `dev_release2` (treno 101),
> journal `a4f682261`. **Base aggiornata**: merge di `dev_release2` (`c94254695`) senza conflitti → HEAD `647167f46`
> (verificato, worktree pulito). Via a W-B43 (TC-13) e W-B45 (T13), commit separati, prove leggere col carico < 50.

### W-B45 — T13 di `transactions-modals.spec.ts` col tempo dei vicini ✅ (2026-10-16) — 🧊 FROZEN

**Analisi** (08:19, codice di `647167f46`): T13 (`invalid TX in BulkModal shows issues banner with clickable error`,
`frontend/e2e/transactions/transactions-modals.spec.ts:1211`) passa da `openCreateFlow`, il form, lo spazio di lavoro e la
risposta di `validate` col tempo di serie (30 s); gli altri test del file con `test.setTimeout(60_000)` (399, 431, 485, 585,
628, 707) lo hanno per il giro di benvenuto di un conto nuovo. Col carico a 43–49 T13 è scaduto prima di ogni controllo; da
solo, col carico a 30, passa in 3,5 s (T, 08:01). **Cura** (08:20): `test.setTimeout(60_000)` in testa a T13, con un commento
nello stile del file. Nessun rosso possibile (dipende dal carico). **Prove**: `prettier` pulito; `front check` 0 errori, 0
avvisi (il tsconfig comprende `e2e/`); `git diff --check` pulito. E2E non girato: cambia solo il tempo concesso, un test verde
non può diventare rosso (e ogni avvio del server ricostruirebbe la build debug, stantia dopo il lotto di T). Il file è identico
in `dev_release2`: cherry-pick pulito.

### W-B43 — tre debolezze in `asset-data-editor.spec.ts` e `fx-csv-import.spec.ts`: analisi ✅, codice ⛔ (2026-10-16)

**Stato reale** (codice di `647167f46`): il lotto W1-g di T è entrato (`fx-csv-import.spec.ts:289` usa
`getByTestId('info-banner-info')`), ma **il lotto di T sui quattro file di `ui/data-editor`** (riservato dalle 05:13: `DataEditor`,
`CsvEditor`, `DataImportModal`, `ErasableNumberCell`, più `asset-data-editor.spec.ts:287` e `fx-csv-import.spec.ts:53,56`, dove un
attributo di stato sostituisce `.text-red-500`) **non è né nella mia base né in `dev_release2`**: le righe 53 e 56 di
`fx-csv-import.spec.ts` (`assertNoErrors`) e 286–287 di `asset-data-editor.spec.ts` usano ancora `.text-red-500`, e nessun
componente di `ui/data-editor` ha un `data-state`. Le tre debolezze di TC-13:
- `asset-data-editor.spec.ts:376` (test 21, «stale toggle is visible in toolbar»): tutto dentro `if (await
  staleToggle.isVisible({timeout: 3000}).catch(() => false))`, che non aspetta e fa passare il test senza asserire nulla; il
  contatore si cerca per classe (`span.text-amber-600, span.text-amber-400`), classi che il lotto di T sostituirà; il toggle è
  `data-editor-stale-toggle` in `DataEditor.svelte:647` (file di T). Cura: un asset proprio con righe stantie (dato deterministico),
  il toggle atteso visibile, il contatore per `data-testid` o `data-state` del lotto di T, col numero atteso.
- nessun controllo positivo della ✗: `assertNoErrors` (`fx-csv-import.spec.ts:51-58`) prova solo l'assenza di
  `.text-red-500:has-text("✗")`; dopo il passaggio ai ruoli quel selettore non troverebbe più nulla e il controllo passerebbe a
  vuoto. Cura: un controllo positivo (una riga sbagliata → l'indicatore c'è, per l'attributo di stato di T) accanto a quello
  negativo.
- `fx-csv-import.spec.ts:56` dipende dalla parola «error» (testo tradotto). Cura: lo stato o il conteggio per `data-testid`.
**Blocco**: le tre cure usano l'attributo o i `data-testid` che porta il lotto di T, e le righe sono riservate a T: W-B43 aspetta
quel lotto (detto al coordinatore). Poi: test-author, E2E dei due spec in uno slot.

> **W-B45 committato** (coordinatore, 08:25): `7ab9add9e` sul ramo (HEAD, verificato), cherry-pick `72ac088fc` (treno 102).
> Via: il triage delle voci di sicurezza e dati aperte (W-B1, W-B3, W-B4, W-B5, W-B17), poi la prima ancora aperta per
> gravità, rosso prima, lotto piccolo; W-B19 (copia della convalida del saldo) è matematica finanziaria di J: avvisare prima.

### Triage di W-B1, W-B3, W-B4, W-B5, W-B17 ✅ (2026-10-16)

Sul codice di `7ab9add9e`, sola lettura:
- **W-B1** (icona dei plugin con `startswith`): **già chiusa** da `6e8251014` (14/10, in `v1.2.1`: `git tag --contains`),
  «fix(server): keep served file paths inside their folder»: `serve_plugin_static` (`backend/app/api/v1/uploads.py:545`) usa
  `confined_path` (`backend/app/utils/runtime/paths.py`: `resolve()` della radice e del candidato, poi `is_relative_to`);
  CHANGELOG 1.2.1 «The server keeps every file it serves inside the folder it belongs to». Chiusa nel backlog col riferimento.
- **W-B3** e **W-B4**: già ✅ (F36, `3907eed36`); le righe del CHANGELOG («Broker reports uploaded by older versions are no
  longer open to every user», «Report file ids are checked first») sono in [Unreleased], non in 1.2.1 (il commit non è in
  nessun tag): aggiunti i riferimenti.
- **W-B5**: già ✅ (`6be11ecf3`, N1a); il resto è W-B19 (di J, non lo tocco).
- **W-B17**: **aperta** → il lotto seguente.

### W-B17 — una FX_CONVERSION su due broker rifiutata dall'API ✅ (2026-10-16) — 🧊 FROZEN

**Stato reale**: `_validate_linked_pair` (`backend/app/services/transactions/validation.py:39-87`) rifiuta TRANSFER e
CASH_TRANSFER sullo stesso broker, un TRANSFER con asset diversi o quantità non opposte, ma nessuna regola per FX_CONVERSION;
la docstring dice «FX_CONVERSION intra-broker is allowed». I metadati (`type_metadata.py`, blocco FX_CONVERSION:
`pair_field_constraints` e `promote_from`) vogliono `broker_id: equal` (e `cash_currency: different`); form, promozione e
import scrivono sempre le due metà sullo stesso broker. Chiamante unico: `resolve_create_links`
(`batch_creates.py:321`), solo per le creazioni con `link_uuid`: le coppie già salvate non si riconvalidano negli update
(nessun dato esistente diventa intoccabile). I codici sono letterali (nessun enum); il frontend traduce
`transactions.errors.<code>`. Test vicini: `test_transaction_service.py:1696` (TRANSFER sullo stesso broker, rifiutato) e
`:1737` (FX_CONVERSION sullo stesso broker, ammessa).
**Disegno** (dentro il backlog approvato: «Cura: `pairBrokerMismatch` per una FX_CONVERSION su due broker, con il rosso»):
- una regola in `_validate_linked_pair`, nello stile delle altre: FX_CONVERSION con `a.broker_id != b.broker_id` →
  `("FX_CONVERSION requires both legs on one broker (got brokers A and B)", "pairBrokerMismatch", {"brokerA", "brokerB"})`
  (parametri A/B come `typeA/typeB`, `assetA/assetB`); la docstring corretta;
- la chiave `transactions.errors.pairBrokerMismatch` con `dev.py i18n add` nelle 4 lingue, sul modello di
  `pairAssetMismatch` (EN «Both sides of a currency exchange must be on the same broker»);
- rosso prima (test-author, servizi: nessun server, nessuna ricostruzione), accanto ai due test vicini;
- doc per sviluppatori (docs-writer) dove si elencano le regole delle coppie.
Fuori: leggere tutte le `pair_field_constraints` dalla tabella (come W-B31/W-B36 per le regole 5–12) e la regola
`cash_currency: different` → residuo, se non già coperta altrove. Le coppie su due broker già nel DB (solo via API) restano:
la cancellazione di un broker ne converte la metà per segno (N1b-1).
**Rosso** ✅ (08:36, test-author; carico 41): `TestLinkedPairValidation::test_pairing_rejects_fx_conversion_cross_broker` in
`backend/test_scripts/test_services/test_transaction_service.py`, subito dopo la guardia
`test_pairing_allows_fx_conversion_same_broker` (invariata): EUR −500 su `test_broker` (finanziato il giorno prima) e USD +540 su
`test_broker_overdraft`, `link_uuid` comune; `services transaction <nome>` → **1 fallito**: «W-B17: /transactions/commit saves an
exchange split across broker 1 (EUR) and 2 (USD) with no error … got committed=True, issues []». Scelta del test-author (da
rivedere se serve): `execute_batch` non fa commit né rollback (lo fa il chiamante), quindi il batch è avvolto in un savepoint
(`session.begin_nested()`) chiuso come fa la rotta (commit se `committed`, rollback altrimenti), così la rilettura «niente
scritto» (per descrizione, `service.query` sui due broker, dopo una barriera sul deposito di setup) ha senso; tutto resta nella
transazione del fixture `session`, annullata alla fine (DB della corsia verificato vuoto). Nessun id TX-U (la classe non li usa;
TX-U-122 è già prenotato nella checklist di RoadmapV3).
**Cura** ✅ (08:38): `/tmp/libreFolio_w_wb17_cure.py --apply`: in `_validate_linked_pair` la regola FX_CONVERSION con broker
diversi → `pairBrokerMismatch` (`brokerA`, `brokerB`), la docstring corretta; `dev.py i18n add
transactions.errors.pairBrokerMismatch` (EN «Both sides of a currency exchange must be on the same broker», IT, FR, ES, sul
modello di `pairAssetMismatch`). **Verdi**: `services transaction` **67/67** (08:39).
**Prove** (08:47, carico 40): `black`/`ruff` puliti; `i18n check` strict (4770 chiavi); `prettier` pulito sui 4 JSON; `git diff
--check` pulito; i file sono identici in `dev_release2`.
> **⏸ STOP del developer** (coordinatore, ~08:50): nessuna prova in corso, porta libera, worktree lasciato com'era. **Ripresa**
> alle 10:32: HEAD ancora `7ab9add9e`, delta di W-B17 intatto. Notizie: il lotto di T su `ui/data-editor` è entrato alle 10:19
> (`eb4040cd1`) → W-B43 sbloccata, base da aggiornare al prossimo checkpoint; **P2 decisa dal developer** («una rettifica non è
> mai un prezzo»): la 47 entra dopo il lotto J-17 di J.
**Dopo la ripresa** (10:33–10:36, carico 11–32):
- Portata della regola: `TXUpdateItem` non ha `broker_id` (un update non sposta una gamba); i tipi in coppia non hanno
  scambi di tipo (`SWAP_GROUPS`, `type_metadata.py:143`); la promozione legge già `broker_id: equal` dalla tabella
  (`_check_promote_constraints`, `promotion.py:243`): la creazione con `link_uuid` era l'unica via, ed è chiusa.
- Suite che costruiscono coppie FX col batch, senza server: `services broker` **76/76**, `services
  transaction-cost-basis-rule` **74/74**, `db brim` **28/28**; nessun test, dato del mock o spec E2E crea una FX_CONVERSION su
  due broker (grep: `tx-clone`, `tx-bulk-row-order` e gli altri usano un broker solo; il mock la scrive con l'ORM, su IB).
  API ed E2E non girati: ogni avvio del server ricostruirebbe la build debug (la base e le sorgenti i18n sono cambiate), e
  la regola è nel servizio, provato direttamente; il frontend traduce il codice nuovo.
- Doc: docs-writer (10:37) su `developer/backend/transactions/service.md:210-212` e
  `developer/architecture/patterns/brim_plugin_guide.md:749-752`, pagine solo EN, che dicevano che una FX_CONVERSION può stare
  su due broker.
- **Residuo → W-B46**: le regole delle coppie restano scritte a mano; la tabella vuole anche `cash_currency: different` per
  FX_CONVERSION, che nessuna regola di creazione controlla (solo la promozione, `promotion.py:252`): una FX_CONVERSION nella
  stessa valuta passa ancora dall'API.
- **Doc** ✅ (10:41, docs-writer): `developer/backend/transactions/service.md:210-213` («… and one broker for both legs of an
  `FX_CONVERSION` (`pairBrokerMismatch`, params `brokerA`/`brokerB`)», al posto di «allows an intra-broker `FX_CONVERSION`») e
  `developer/architecture/patterns/brim_plugin_guide.md:749-752` («an `FX_CONVERSION` must stay on **one**
  (`pairBrokerMismatch`) … while an `FX_CONVERSION` pair saved the same way passes it», vero per DEGIRO: `_fx_pair` crea le due
  gambe sul broker di `parse()`); grep di `developer/`: i codici delle coppie solo in queste due pagine, nient'altro di falso
  (`service.md:183`, `:249` e `database/index.md:151` restano veri). Pagine solo EN: nessun debito di traduzione.
- `mkdocs build` strict ✅ (110 s) e `check-links` ✅ (97 validi), 10:42–10:47, carico 40–42; `git diff --check` pulito; porta
  libera.
- **Cherry-pick**: i file di W-B17 sono identici in `dev_release2`, tranne `service.md`, che differisce solo per gli hunk della
  47 (`8b3e6b766`, righe 71–101 e 252–355; `dev_release2` non l'ha cambiata dopo la merge-base); simulato con `git merge-file`
  (base = HEAD, nostra = `dev_release2`, loro = il worktree): 0 conflitti, la riga nuova al suo posto.
> **⚠️ Fuori pista**: il riavvio delle 10:03 ha svuotato `/tmp`: gli script e i log di prima (`/tmp/libreFolio_w_*`, citati nelle
> sezioni W-B39, W-B42, W-B44, W-B32, W-B17) non ci sono più; le prove restano trascritte qui. Regola nuova (coordinatore,
> 10:47): ciò che serve di nuovo (patch, lavoro parcheggiato, script, log) va nella cartella della sessione; i log di W-B17 sono
> copiati lì (`files/logs/`). Regola nuova anche per i colori: prima di scrivere in un `.svelte` delle aree IW, TR, AF, BK, IM,
> DV o T, avvisare il coordinatore; backend, test fuori da quelle cartelle e doc no.

> **W-B17 committato** (coordinatore, 10:49): `926a5c422` sul ramo, cherry-pick `4647c4af4` in `dev_release2` (treno 106),
> CHANGELOG con la riga proposta; il journal resta sul ramo con la 47. **Base aggiornata**: merge di `dev_release2` (`b82e7765f`,
> dentro il lotto `ui/data-editor` di T, `eb4040cd1`) senza conflitti → HEAD `8c930d5de` (verificato, worktree pulito). Via a
> W-B43: i test e la cura nei due spec, scrittura prima; lo slot E2E quando se ne libera uno. W-B46 resta nel backlog.

### W-B43 — tre debolezze in `asset-data-editor.spec.ts` e `fx-csv-import.spec.ts`: codice ⏳ (2026-10-16)

**Dopo il lotto di T** (codice di `8c930d5de`): `CsvEditor.svelte` dà `data-state="valid"` alla ✓ di ogni riga (~551),
`data-state="invalid"` alla ✗ (~557, ~560) e al distintivo d'errore della barra di stato (~510); `DataEditor.svelte` dà
`data-editor-stale-count` al contatore delle righe stantie (~641). T ha già portato i due spec sui nuovi selettori (`eb2adb37b`):
- test 21 (`asset-data-editor.spec.ts`, «stale toggle is visible in toolbar»): il contatore per `data-editor-stale-count`, ma
  tutto ancora dentro `if (await staleToggle.isVisible({timeout: 3000}).catch(() => false))`, su Apple (dato condiviso);
- «price CSV import: invalid rows show error indicators» (~279): `[data-state="invalid"].first()`, che può essere il
  distintivo e non una ✗ di riga;
- `assertNoErrors` (`fx-csv-import.spec.ts:51-58`): `[data-state="invalid"]:has-text("✗")` e `…:has-text("error")` (la parola).
Altri reperti dello stesso tipo: `fx-csv-import.spec.ts:233` asserisce il testo «Header currencies don't match» (il valore EN di
una chiave i18n); `{hasText: /Import \(3\)/}` in `asset-data-editor.spec.ts`. Nel prodotto, la barra di stato di `CsvEditor`
(«N valid rows», «• N errors», «• duplicate …s») è inglese scritta a mano → **W-B47** (file dell'area T dei colori: prima di
scriverci, avvisare il coordinatore).
**Da dove vengono le righe stantie** (verificato): `AssetDataEditorSection.svelte:144` (`staleDays` =
`backward_fill_info.days_back`); `price_query.py:62-104` (`_build_backward_filled_series`) emette una riga per giorno di
calendario in `[start, end]`, i giorni senza prezzo dopo il primo prezzo noto portati avanti con `days_back`, quelli prima
saltati: un asset con prezzi solo in D e D+3, aperto su `[D, D+3]`, ha due righe stantie.
**Disegno** (test-author, in corso 10:52, nessun E2E, nessun codice di prodotto): test 21 su un asset proprio coi prezzi in D e
D+3 → interruttore visibile, contatore 2, e la guardia negativa (intervallo senza righe stantie → interruttore assente); nel
test delle righe non valide, esattamente tre ✗ di riga (`[data-state="invalid"]` con ✗, glifo e non parola) più il
distintivo; in `fx-csv-import` un test nuovo con una riga valida e una non valida (una ✗, le ✓ contate, il distintivo), così le
verifiche negative di `assertNoErrors` hanno un controllo positivo che ne prova il selettore; `assertNoErrors` senza parole:
`[data-state="invalid"]` con conteggio 0; la riga 233 senza testo (visibile, nessuna `{`). **Nessun rosso di prodotto**: il
prodotto è giusto, i test erano vuoti; la prova della loro vacuità è statica (il ramo `if`, le sole verifiche negative), e i test
nuovi la superano con asserzioni positive (il conteggio 2 e l'assenza a zero, la ✗ contata).
Slot: `files/scripts/w_slot.py` nella cartella della sessione (regola delle 10:47: niente `/tmp`), `--step
ade=front-asset/asset-data-editor/420 --step fx=front-fx/fx-csv-import/240`, dry run pulito; il primo avvio ricostruisce la
build debug (la base è cambiata).
> **P4 decisa dal developer** (coordinatore, 11:11): `GET /brokers/{id}/access` **non si restringe** (W-B34): «gli utenti devono
> sapere che esistono altri broker, per capire perché un nome non si può riusare e a chi chiedere». Nessun lotto; scritta nel
> backlog come decisione, col motivo.
> Conseguenza della P4 (11:14): la docstring di `list_accesses` (`backend/app/services/brokers/access.py:96`, scritta in W-B35)
> diceva che `user_id`/`is_superuser` erano «kept for a check the route may add»; ora dice che non si leggono perché ogni utente
> autenticato può leggere l'elenco, con la decisione e il suo motivo. Nessuna pagina della doc prometteva una restrizione futura
> (grep). `black`/`ruff` puliti; file identico in `dev_release2`. Commit a sé, da proporre col prossimo handoff.
**Scritti** (11:12, test-author, nessun E2E): `frontend/e2e/assets/asset-events-owned.ts` (`createOwnedAsset(page, owned,
options = {})` con `label` e `closes` facoltativi, `OwnedClose`; i valori di serie sono quelli di prima: i due spec degli eventi
invariati), `asset-data-editor.spec.ts` (+95 −…: `owned` per describe, `afterEach(deleteOwned)`, aiuti `openOwnPricesEditor` e
`priceRowIds`; test 16 e 21 riscritti), `fx-csv-import.spec.ts` (`assertNoErrors(modal, validRows?)`, un test nuovo, il test 10).
Titoli invariati.
- Test 21: asset proprio («E2E stale rows», USD) con chiusure in D = oggi − 20 e D+3; su `[D, D+3]` le righe sono esattamente D,
  D+1, D+2, D+3, l'interruttore è visibile, il contatore legge `/^\D*2\D*$/`; la guardia su `[D+3, D+3]`: una riga sola, il
  pulsante d'import della barra (`fx-data-import-btn`, del `DataEditor` comune) visibile, poi l'interruttore assente. `prices/current`
  servito in locale. 60 s.
- Test 16 (Apple, non scrive): esattamente 3 ✗ di riga (`[data-state="invalid"]` con ✗), ciascuna visibile, e il distintivo
  (`[data-state="invalid"]` senza ✗) visibile.
- Nuovo test FX «an invalid data row is marked ✗ and the others ✓» (non scrive): una riga valida e una con `not-a-rate` → una ✓,
  una ✗, il distintivo.
- `assertNoErrors`: `[data-state="invalid"]` a 0, e per i chiamanti con righe di dati (test 7, 17, 20) prima 2 `[data-state="valid"]`.
- Test 10: il messaggio d'errore dell'intestazione visibile, non vuoto, senza `{`, al posto del testo inglese.
**Prove leggere**: `prettier` pulito; `front check` **0 errori, 0 avvisi** dopo un `api sync`.
> **⚠️ Fuori pista**: il primo `front check` (11:13) dava 1 errore in `frontend/src/lib/features/auth/RegisterCard.svelte:100`
> («`verification_required` does not exist on type `AuthRegisterResponse`»): codice del workstream E arrivato con la base, e il
> mio client generato (ignorato da git) era di prima. `api sync` (nessuna differenza tracciata) → `front check` 0/0. Non è un
> difetto del ramo: dopo ogni aggiornamento della base va rigenerato il client.
**Residui** → **W-B48** (altri selettori per testo e un altro `if` vuoto negli stessi due spec) e **W-B47** allargata (anche il
piede di `DataImportModal`, «• N error(s)» e «• duplicates», in inglese e senza `data-state`).

> **P5 e P6 decise dal developer** (coordinatore, 11:19), lotti separati dopo W-B43, rossi prima, `api sync` dove serve:
> - **P5 (W-B30)**: «se lo svuoto attivamente vuol dire che lo voglio cancellare»: un `cost_basis_override: null` esplicito in un
>   update toglie il costo manuale; un campo assente lo lascia; con `cost_basis_mode: 'auto'` il null si ignora; sui lati che il
>   costo lo richiedono, `costBasisRequired`;
> - **P6 (W-B36)**: la tabella dei tipi vale anche negli update, **solo quando cambia il campo interessato** (come N2); prima un
>   controllo dei dati esistenti, per sapere quante righe vecchie sono fuori regola.

### W-B30 (P5) — un costo manuale svuotato si toglie: analisi ✅ (2026-10-16)

Codice di `c25c3f8b4`, sola lettura:
- `_apply_update_values` (`backend/app/services/transactions/batch_edits.py:252-265`): `if item.cost_basis_override is not
  None:` → un `null` esplicito e un campo assente sono la stessa cosa: il costo resta, in silenzio. Pydantic v2 li distingue con
  `item.model_fields_set`.
- Il frontend il `null` lo manda già: il form (`txPayloadHelpers.ts:303`, `:322`: in modo manuale, campo vuoto → `null`) e il
  Bulk (`:355-359`); in modo auto manda `cost_basis_mode: 'auto'` col valore o `null` (`:268`, `:320-323`). La cura è solo nel
  backend.
- Il controllo N2 sugli update (`_check_update_cost_basis`, `batch_costs.py`) confronta già `cost_fields` con quelli salvati:
  togliere il costo su un lato che lo richiede dà `costBasisRequired` senza altro codice.
- La tabella oggi (`cost_basis_allowed`/`cost_basis_required`, verificati per ogni tipo e segno): un costo manuale è ammesso
  **solo** dove è richiesto (ADJUSTMENT e TRANSFER a quantità positiva). Quindi nella UI l'effetto è: svuotare un costo richiesto
  è rifiutato con un messaggio (prima restava in silenzio); il «si toglie» vale per righe vecchie con un costo dove non è ammesso
  (via API).
**Disegno**: in `_apply_update_values`, `elif "cost_basis_override" in item.model_fields_set and item.cost_basis_mode not in
("auto", "auto-detail")` → `cost_basis_override` e `cost_basis_currency` a `None` (decisione tecnica: «auto-detail» è un modo
auto come «auto»); la descrizione di `TXUpdateItem.cost_basis_override` (OpenAPI → `api sync`). Rossi (test-author,
`services transaction-cost-basis-rule`, accanto ai test di N2): `null` su un TRANSFER ricevuto con costo manuale →
`costBasisRequired`, niente cambia (oggi passa e il costo resta); `null` su una riga vecchia con un costo dove non è richiesto
(scritta con l'ORM) → costo tolto (oggi resta); guardie: campo assente → invariato; `null` con `auto` → il costo Auto.
Doc (docs-writer): form utente e regole degli update per sviluppatori. CHANGELOG 🐛.

### W-B36b (P6) — la tabella dei tipi anche negli update, quando il campo cambia: analisi ✅ (2026-10-16)

I quattro casi (sezione W-B36): 1 un TRANSFER con cassa ≠ 0, 2 un FX_CONVERSION con quantità ≠ 0, 3 un TRANSFER a quantità 0,
4 un FX_CONVERSION o CASH_TRANSFER a cassa 0 (raggiungibile anche con un promote di WITHDRAWAL e DEPOSIT a importo zero). La
creazione li rifiuta già (regole 2, 3, 3b); in `validate_transaction_business_rules` (comune a creazione e update) restano gli
insiemi d'eccezione `_P6_CASH_FORBIDDEN_UNCHECKED`, `_P6_QUANTITY_SIGN_UNCHECKED` e la regola 11 che non legge «nonzero».
**Disegno proposto**: un parametro della funzione con i campi che l'update cambia (`None` per la creazione, che resta com'è: le
sue regole 2, 3, 3b fanno già il lavoro, e così non si doppiano i messaggi); in un update i quattro punti valgono quando cambia il
loro campo (cassa per 1 e 4, quantità per 2 e 3) o il tipo; il promote, che cambia il tipo, applica la tabella intera alle righe
che produce (caso 4). Rossi prima (`schemas transactions` e `services transaction`). Le righe vecchie fuori regola restano
modificabili per le note, i tag e la descrizione (come N2).
**Il controllo dei dati, prima** (in sola lettura): `files/scripts/p6_legacy_rows.sql` nella cartella della sessione, quattro
conteggi più il totale, da far girare con `sqlite3 "file:<…>/app.db?mode=ro" < p6_legacy_rows.sql` su una copia a server fermo. Nel DB
della corsia dopo lo slot di W-B43 (il mock); sul DB del developer solo lui.
> **Disegni approvati** (coordinatore, 11:25): W-B30 con `model_fields_set`, W-B36b coi campi cambiati; non serve il numero
> vero per partire: rossi e avanti. Il developer autorizza **una copia del suo DB demo** per i controlli dei figli: il
> coordinatore la prepara con la procedura per farsene una copia; allora `p6_legacy_rows.sql` sulla mia copia e il risultato
> qui. Rossi in scrittura (11:26), nessuna prova fino allo slot: W-B30 (test-author, `test_transaction_cost_basis_rule.py`) e
> W-B36b (test-author, `test_transaction_service.py` e `test_transaction_schemas.py`; il codice nuovo `cashNonzero` per il caso
> 4). Ordine delle cure: W-B30 prima (committato), poi W-B36b: tutte e due toccano `batch_edits.py`.
**W-B30, rossi scritti** (11:38, test-author, non eseguiti): classe `TestDecisionP5AnExplicitNullEmptiesTheCost` in
`backend/test_scripts/test_services/test_transaction_cost_basis_rule.py`, dopo `TestEditsOfARowWithCost` di N2; la riga che chiede
un costo è la gamba ricevente di un TRANSFER (`_store(world, "transfer_in", cost=…)`), il cui costo Auto è quello che gli altri
test Auto del file si aspettano. Il test-author ha segnalato un caso fuori dal disegno: con la 47 la gamba che cede è un
ADJUSTMENT −q con un costo **scritto dal sistema**; un `null` via API lo cancellerebbe e per CP-16 le unità uscirebbero a prezzo
0 (numeri). **Decisione del coordinatore (B)** (11:42, da rivedere dal developer): il `null` toglie il costo solo dove il tipo e il
lato lo prendono (`cost_basis_allowed` sul tipo e la quantità finali della riga), altrove si ignora come oggi: è la lettera della
P5 («il costo **manuale**») e i costi di consegna della 47 restano. Con la tabella di oggi i lati ammessi sono anche obbligatori:
il `null` dà sempre `costBasisRequired`, non toglie mai niente; resta la differenza da oggi: il costo non è più tenuto in silenzio.
I rossi `[buy]` e `[adjustment_out]` diventano guardie (il costo resta); il rosso del lato obbligatorio resta. Cura aggiornata
(`files/scripts/wb30_cure.py`, dry run pulito): l'import di `cost_basis_allowed`, la condizione su `model_fields_set`, il modo e
`cost_basis_allowed`, la docstring di `_apply_update_values` e la descrizione di `TXUpdateItem.cost_basis_override`.

**W-B43, slot 2** ✅ (11:30–11:47, carico 68–147; `files/scripts/w_slot.py --no-load-gate`, slot dato col carico già alto):
`front-asset asset-data-editor` **26/26** (3,3 min, con la ricostruzione della build debug; i test 16 e 21 riscritti passano);
`front-fx fx-csv-import` **21/22**: rosso il test 19 «swap after less-than syntax rewrites header with greater-than» (non toccato),
tempo del test (30 s) scaduto nel setup, nella navigazione di `goToFxDetailPage` (`e2e/fx/fx-helpers.ts:64`), prima di ogni
asserzione. **Triage** (skill `test-triage`): §1 e §3 non si applicano (nessun dato asserito, niente stato spostato); §2 nessuna
attesa a orologio, condizioni giuste, gli altri 21 test con lo stesso setup passati; rilanciato da solo (11:49, carico 49) →
**passato in 3,1 s**. **Verdetto: ambiente** (macchina satura dalle prove delle altre sessioni); se si ripete a carico normale, il
rimedio è il tempo dello spec (come W-B45). Porta libera. FROZEN, handoff alle 11:59. > **⚠️ Fuori pista**: un errore del
servizio (~11:55) ha interrotto il mio turno e fatto cadere il test-author di W-B36b (DNS) dopo 417 righe in
`test_transaction_service.py`, non verificate: un test-author nuovo le rivede e aggiunge la puntina di `cashNonzero`.

**P6, il controllo dei dati** ✅ (12:01, carico 43; skill `real-data-copy`, `git show baa1b6e7e:…`): copia di lavoro
`/tmp/librefolio-r2-w-realdata` dalla copia di riferimento del coordinatore (demo del developer, Alembic 008, prezzi di oggi, solo
EUR, un utente), `umask 077`, nessun marcatore di produzione, `go-rwx`; `sqlite3 "file:…/app.db?mode=ro" < p6_legacy_rows.sql`
(sola lettura, nessun server). **Risultato: caso 1 = 0, caso 2 = 0, caso 3 = 0, caso 4 = 0** righe fuori regola. Copia
**cancellata** alle 12:01 (`lsof +D` vuoto, `rm -rf`, `ls`: «No such file or directory»); nessun file derivato tenuto.

**W-B43 committato** (coordinatore, 12:02): `d6a260c89` sul ramo (HEAD, verificato), cherry-pick `a59593570` in `dev_release2`
(treno 109); triage del test 19 accettato (ambiente).

**W-B30, rossi** ✅ (12:01, carico 49): `services transaction-cost-basis-rule TestDecisionP5AnExplicitNullEmptiesTheCost` →
**1 fallito, 5 passati**: rosso `test_emptying_the_manual_cost_of_a_received_transfer_is_refused` («emptying the manual cost of a
received TRANSFER is saved, and the receiving leg … holds 42.000000 EUR — that leg needs a cost basis…»); guardie verdi:
`test_a_null_where_no_cost_is_taken_is_ignored[buy|adjustment_out]` (decisione B), `test_notes_edit_without_the_cost_key_keeps_the_cost`,
`test_auto_update_sending_a_null_writes_the_auto_cost[auto|auto-detail]`. **Cura** ✅ (12:02, `files/scripts/wb30_cure.py
--apply`; `black` ha unito la condizione in una riga). **Verdi**: `services transaction-cost-basis-rule` **80/80**; `services
transaction` **67/67** (con `-k "not TestUpdateTypeTableRules"`: i rossi di W-B36b restano fuori); `black`/`ruff` puliti; `api
sync` senza differenze tracciate; `front check` **0/0**. Doc: docs-writer in corso.
> **⚠️ Fuori pista — cherry-pick**: la simulazione (`git merge-file`, base HEAD, nostra `dev_release2`, loro il worktree) dà
> `batch_edits.py` e `transactions.py` puliti, ma **3 conflitti** nel file dei test: le aggiunte di W-B30 stanno accanto a quelle
> della 47 (che `dev_release2` non ha) nella docstring del modulo, nella riga d'import e nelle costanti, e il test usava il nome
> `cost_basis_allowed` importato proprio dalla riga della 47. Il test-author (12:20) sposta le aggiunte (costanti accanto alla
> classe, il paragrafo P5 nella docstring della classe, `type_metadata.cost_basis_allowed` dall'alias che `dev` ha, `import …
> transactions as transaction_schemas` in ordine isort) perché W-B30 entri senza la 47; poi di nuovo simulazione e prove.

**W-B36b, rossi** ✅ (12:21, carico 33): il test-author caduto aveva lasciato 417 righe giuste e complete; quello nuovo ha corretto
due docstring, aggiunto la puntina TX-S-110 `test_cash_nonzero_message_on_an_update_changing_the_cash` e passato `black`/`ruff`.
`services transaction TestUpdateTypeTableRules` → **7 falliti, 22 passati**: rossi i cinque casi d'update (1 TRANSFER con
cassa, 2 FX_CONVERSION con quantità, 3 TRANSFER a quantità 0, 4 FX_CONVERSION e CASH_TRANSFER a cassa 0) e i due promote a
importo zero (CASH_TRANSFER, FX_CONVERSION), tutti «… was saved» (oggi passano); guardie verdi (note e tag su coppie fuori regola,
modifiche che lasciano il campo com'è salvato, valori rimandati identici). `schemas transactions <puntina>` → **1 fallito**
(`TypeError: … unexpected keyword argument 'changed_fields'`, rosso atteso per una parola chiave nuova). Il promote è
raggiungibile (WITHDRAWAL e DEPOSIT a 0 si salvano: la regola 11 giudica solo un importo non zero). La cura dopo il commit di
W-B30 (gli stessi due file di prodotto); la chiave i18n `cashNonzero` da aggiungere (4 lingue).

**W-B30, il file dei test senza la 47** ✅ (12:40, test-author): le aggiunte spostate lontano dalle righe della 47, comportamento
e nomi dei test invariati: `import backend.app.schemas.transactions.transactions as transaction_schemas` prima dell'alias
`type_metadata` (isort), `transaction_schemas.TXUpdateItem` e `type_metadata.cost_basis_allowed` (l'alias che `dev` ha già); le
costanti (`LEGACY_SHAPES`, `LEGACY_LABELS`, `AUTO_MODES`) sopra la classe; il paragrafo P5 dentro la docstring della classe;
nella docstring del modulo resta solo il punto «Not covered» riscritto (diventava falso). Due dipendenze dalla 47 trovate e
tolte: il nome nudo `cost_basis_allowed` e `select` (dalla riga d'import della 47, in `_stored_cost`: ora
`session.get(Transaction, id, populate_existing=True)`, che emette sempre la sua SELECT). **Simulazione del cherry-pick**
(`git merge-file`, base HEAD `d6a260c89`, nostra `dev_release2`, loro il worktree; file in `files/sim/`): **0 conflitti su tutti
i 9 file** del lotto; sui tre `.py` risultanti `ruff` e `black --check` puliti (`--stdin-filename` col percorso vero: nessun
nome indefinito, quindi nessuna dipendenza nascosta dalla 47), nessun marcatore della 47 nel file dei test risultante.
**Doc** ✅: docs-writer in inglese (`user/transactions/form.en.md:40`, la frase sulla modifica di una transazione salvata;
`developer/backend/transactions/wac.md`, il paragrafo «An explicit `null` in an update»; `service.md:66`, la riga 5 della
tabella degli stadi); IT/FR/ES a mano alla riga 39, dopo la frase del **Manuale**, coi termini della pagina (IT «costo di
carico», FR «prix de revient», ES «coste base»); **nessuno stamp**: la pagina ha già un debito di traduzione (il punto «Missing
event?» manca in IT/FR/ES). `mkdocs build` (strict) **exit 0** (12:30, carico 36).
> **⚠️ Fuori pista — le due osservazioni del docs-writer, verificate sul codice** → **W-B49**: (1) ogni modifica passa dalla
> Bulk (`handleEditRow` → `openBulk({action: 'edit'})`), che apre il modulo; il controllo dal vivo del modulo su una coppia
> (`collectDualUpdates` → `diffDualItem`) non manda il costo svuotato, perché la gamba ricevente di `buildDualCreatePayloads` non
> ha la chiave quando il campo è vuoto; il «Salva tutto» della Bulk (`buildUpdateDiff`) manda il `null` e W-B30 lo rifiuta:
> il costo non resta in silenzio, ma il rifiuto arriva tardi. La frase della guida utente («il salvataggio è rifiutato») resta
> vera. (2) Il tooltip `transactions.costBasisOverride.tooltip` e la riga «Normal transfer» di
> `financial-theory/…/adjustment.{en,it,fr}.md` dicono ancora «vuoto = calcolato in automatico». Fuori dal lotto: W-B49.

**W-B30 committato** (coordinatore, 12:47): `949da55f8` sul ramo (HEAD, verificato), cherry-pick `54880598b` in `dev_release2`
(treno 111) con la riga 🐛 del CHANGELOG; il cancello `services transaction-cost-basis-rule` e `services transaction` sul
risultato lo gira il coordinatore. Numerazione: **W-B50** alle quattro note di IW-8 (test del wizard di import), scritto nel
BACKLOG. Le note non mi erano arrivate: lette nella cronologia del coordinatore (10:22) e verificate sugli spec.

### W-B36b (P6) — la tabella dei tipi anche negli update, quando il campo cambia: cura ✅ (2026-10-16)

**Cura** ✅ (12:50; `files/scripts/wb36b_cure.py`, dry run pulito poi `--apply`, 18 modifiche in 6 file; `black` invariato,
`ruff` pulito):
- `backend/app/schemas/transactions/transactions.py`: `validate_transaction_business_rules(…, changed_fields=None)`; `None` è
  la chiamata di CREATE, che resta com'è (le sue regole 2, 3 e 3b); `cash_changed` e `quantity_changed`, un tipo cambiato
  vale per tutti i campi; regola 8 sul TRANSFER e regola 10 su FX_CONVERSION e TRANSFER solo col campo cambiato; regola 11
  col codice nuovo `cashNonzero` («{type} requires cash.amount != 0»); i set rinominati `_P6_CASH_FORBIDDEN_WHEN_CHANGED` e
  `_P6_QUANTITY_SIGN_WHEN_CHANGED` (il vecchio «UNCHECKED» diventava falso); commento del modulo e docstring;
- `transaction_batch_context.py`: `stored_rule_values`, `rule_values()` (tipo, quantità, importo, valuta) e
  `changed_rule_fields()`, che confronta per valore con la riga salvata prima del batch: un valore rimandato com'è salvato non
  è un cambiamento; senza fotografia, nessun cambiamento (come prima di P6);
- `transaction_batch_stages.py`: la fotografia in `_load_existing_transactions`, accanto a `stored_cost_fields` di N2;
- `batch_edits.py`: `apply_updates` passa `changed_rule_fields(…)` a `_validate_updated_final_state`;
- `batch_creates.py`: `_promoted_state_issues` passa `changed_fields=frozenset({"type"})` (un promote cambia il tipo);
- la docstring di `TestUpdateTypeTableRules`: tolti i nomi vecchi dei set («regole 8, 10 e 11»);
- i18n `transactions.errors.cashNonzero` nelle 4 lingue (`dev.py i18n add`, sorgente `i18n/transactions/<lang>.json`).
> **⚠️ Fuori pista — disegno**: il piano voleva una costante `PROMOTED_FIELDS` importata in `batch_creates.py`, ma quella riga
> d'import sta subito sopra la riga della 47 (`cost_basis_allowed`, riga 16 di HEAD): il cherry-pick avrebbe dato conflitto.
> Scelta: il promote passa `{"type"}`, e un tipo cambiato giudica ogni campo; `changed_rule_fields` riporta anche il tipo,
> come `cost_fields` di N2. Nessun update può cambiare un tipo verso o da TRANSFER, FX_CONVERSION o CASH_TRANSFER
> (`SWAP_GROUPS`), quindi per gli update di oggi non cambia nulla.

**Verdi** ✅ (12:52–12:55, carico 37–47): `services transaction TestUpdateTypeTableRules` **29/29** (i 7 rossi verdi, 22
guardie); puntina TX-S-110 **1/1**; `services transaction` **96/96**; `schemas transactions` **106/106**; `services
transaction-cost-basis-rule` **80/80**; `services broker` **76/76**; `services brim-create-transaction` **14/14** (la via di
CREATE); `i18n audit` exit 0, nessuna traduzione mancante (`transactions.errors` è un prefisso dinamico). Porta libera.
**Simulazione del cherry-pick** su `dev_release2` `34e1e8092`: **0 conflitti** sugli 11 file; sui `.py` risultanti `ruff` e
`black` puliti, i JSON validi; `_find_promote_rule_match`, usato dal test del promote, c'è in `dev`. Nessuna superficie
dell'API cambiata (niente `api sync`). Doc: docs-writer in corso (`developer/backend/transactions/service.md`, solo la sezione
«Per-type rules», lontano dalle righe della 47).

**W-B36b, doc** ✅ (13:05, docs-writer): `developer/backend/transactions/service.md`, sezione «Per-type rules»: `cashNonzero` nella
riga «10, 11» della tabella, e il paragrafo «Until the developer's pending decision P6…» sostituito dal comportamento deciso
(i quattro punti coi loro codici, solo sul campo cambiato, confronto per valore con `stored_rule_values`, il promote li
controlla tutti, CREATE con le sue regole 2, 3 e 3b; rimando a N2, `wac.md#persisted-cost-basis`). Due hunk, lontani dalle
righe della 47. Pagina solo inglese, niente stamp. `i18n check` (strict) exit 0, 4776 chiavi; `mkdocs build` (strict)
**exit 0** (13:08–13:11, carico 44); `check-links` **97 validi**.
> **⚠️ Fuori pista — testi dei test rimasti al prima**: il docs-writer ha segnalato, e ho verificato, che la cura rende falsi
> dei testi nei test: `_P6_PENDING` e `TestRules5To11P6Pending` (TX-S-104…107) dicono «P6 pending … flip this guard», e i
> rossi di W-B36b (e TX-S-110) dicono «RED until W-B36b… Today … is saved». Restano verdi (TX-S-104…107 chiamano la funzione
> senza `changed_fields`, cioè come CREATE), ma la convenzione del progetto è «red before W-B31, now its guard» (TX-S-092/093).
> Lo stesso difetto l'ho lasciato nel lotto W-B30, già committato: la classe P5 dice ancora «Today … / RED until the cure».
> Verificata la funzione su tutti i casi e tutte le combinazioni di `changed_fields` (None, cash, quantity, type): esatta.
> Test-author (13:06) per tre file: (A) `test_transaction_schemas.py`, il blocco P6 riallineato alla decisione (rinomine),
> `_run_rules` con `changed_fields`, e in TX-S-104…107 le metà della decisione a livello di funzione (il campo → il codice;
> l'altro campo → niente; `{"type"}` → il codice), TX-S-110 da rosso a guardia; (B) `test_transaction_service.py`, solo prosa
> nel blocco di W-B36b; (C) `test_transaction_cost_basis_rule.py`, solo prosa nella classe P5: **commit a parte**, seguito di
> W-B30, lontano dalle righe della 47.

**Test riallineati** ✅ (13:21, test-author; `black`/`ruff` puliti, nessun test girato): (A) `_P6_PENDING` → `_P6_ON_A_CHANGE`,
`TestRules5To11P6Pending` → `TestRules5To11P6OnAChange`, TX-S-104…107 rinominati («…refused_only_when_the_… changes»), ognuno
con la metà senza `changed_fields` (`[]`) e tre metà nuove (il campo → il codice; l'altro campo → `[]`; `{"type"}` → il
codice); `_run_rules` con `changed_fields`; TX-S-110 «red before W-B36b, now its guard». (B) e (C) **solo prosa**, verificato
confrontando gli AST senza docstring (B con la copia del worktree delle 12:57 in `files/sim/`, C con HEAD); gli hunk di C tutti
dentro la classe P5 (748–841).

**⏸️ PAUSA del developer** (~13:25): nessun comando né specialista in corso, nessun merge aperto, porta 6184 libera. HEAD
`949da55f8`. **Alla ripresa**: rileggere le metà nuove di TX-S-104…107 (lettura iniziata); poi, col carico sotto 50, `schemas
transactions`, `services transaction`, `services transaction-cost-basis-rule` (A ha asserzioni nuove, non ancora girate);
nuova simulazione del cherry-pick (A, B e C cambiati dopo quella delle 12:57; C contro `dev_release2` da solo); `git diff
--check`; handoff FROZEN con **due commit**: W-B36b (5 file backend, 4 JSON i18n, `service.md`, i due file di test) e il seguito
di W-B30 (solo `test_transaction_cost_basis_rule.py`, prosa); il journal resta sul ramo.

**▶️ Ripresa** (14:14, via del coordinatore). Rilette le metà nuove di TX-S-104…107: coincidono con i ritorni della funzione
verificati alle 13:05 (`[]` senza `changed_fields`; il codice sul campo del caso; `[]` sull'altro campo; il codice con
`{"type"}`). **Verdi sui test riallineati** ✅ (14:14–14:19, carico 43–46): `schemas transactions` **106/106**; `services
transaction` **96/96**; `services transaction-cost-basis-rule` **80/80**. Porta libera. **Simulazione del cherry-pick** su
`dev_release2` `04dcf3a37`: commit 1 (W-B36b, 12 file) **0 conflitti**, commit 2 (seguito di W-B30, 1 file) **0 conflitti**;
sui `.py` risultanti `ruff`/`black` puliti, JSON validi, nessuna riga della 47 nei file risultanti. `git diff --check` pulito.
**Handoff FROZEN** (14:2x): due commit, il journal resta sul ramo.

**W-B36b committato** (coordinatore, 14:30): `7ad5a8849` (fix) e `05c0f647b` (test come guardie) sul ramo (HEAD `05c0f647b`,
verificato), in `dev_release2` coi cherry-pick `277d26cd0` e `b51bb3663`; il cancello lo gira il coordinatore.

### C-97 — più cifre decimali per quantità e prezzi (issue #43): analisi ✅ (2026-10-16)

> Assegnata dal coordinatore (13:23); testo nel BACKLOG, sezione C (`b171c058e`). Già deciso: quantità **10** decimali, prezzi
> (`price_history`) **12**, importi **restano 6**; oltre il limite si **rifiuta** con un messaggio che dice il massimo, **mai
> arrotondare in silenzio**. Analisi in sola lettura (HEAD `05c0f647b`): inventario con due explore (backend, frontend), le
> affermazioni chiave verificate o misurate da me (SQLAlchemy 2.0.52, SQLite 3.54, Pydantic 2.13).

**Stato reale**
1. *Lettura*: `Numeric(18, 6)` in `backend/app/db/models.py` (`transactions.quantity` :880, `amount` :885,
   `cost_basis_override` :935; `price_history` open/high/low/close/adjusted_close :997–1002; `asset_events.value` :1043; i cambi
   `Numeric(24, 10)` :1095). Nessun adapter (`db/session.py` imposta solo i PRAGMA): il `Decimal` si scrive come float (REAL,
   misurato con `typeof`) e si rilegge con `'%.6f'`. Misurato: `0.12345678` → `0.123457`; `0.0000034573` → `0.000003`.
2. *I prezzi sono troncati anche in scrittura* (correzione al BACKLOG: «il valore intero resta nel file» vale per quantità,
   importi ed eventi, non per i prezzi): ogni upsert di `price_history`, manuale, CSV o provider, passa da
   `truncate_priceHistory` (`services/assets/price_store.py:179–182` → `db/precision.py:114–124`, `ROUND_DOWN` alla scala del
   modello). Le cifre oltre la sesta dei prezzi salvati sono perse; un refresh le riscrive solo per le date che il provider rimanda.
3. *Nessun limite di decimali in input*: `SafeDecimal` e `Currency` (`schemas/common.py`), `TXCreateItem`/`TXUpdateItem`, la
   promozione, `FAPricePoint`/`FAUpsert` (`schemas/prices.py:89, :169`), gli eventi (`schemas/assets/events.py`): nessun
   `decimal_places`, nessun codice d'errore. Oggi le cifre in più si accettano e poi si arrotondano (lettura) o troncano
   (scrittura), sempre in silenzio.
4. *Uscita JSON*: `SafeDecimal` serializza con `format(v, "f")`: tutte le cifre, mai notazione scientifica (un `Decimal` sotto
   `1e-6` ha `str` scientifico, `3.4573E-7`: verificato).
5. *Somme in SQL*: `services/transactions/balances.py:132–133, :169` (i saldi della convalida e le posizioni),
   `services/assets/crud.py:282`, `services/pac_allocator/source/loaders.py:21, :94`: somme di REAL rilette col tipo della
   colonna; il `'%.6f'` di oggi nasconde il rumore del double (misurato: `0.1 + 0.2 − 0.3` = `2.8e-17`).
6. *Frontend, input*: `ExactQuantityInput maxFractionDigits={6}` in `TxFormSingleSection.svelte:176, :224` e
   `TxFormPairSection.svelte:192` (TR). Il componente (`ui/input/ExactQuantityInput.svelte`, default 12) segna il valore non valido
   senza troncarlo, ma **nessuno mostra un messaggio** (nessun consumer di `digitsValid`, nessuna chiave i18n);
   `ExactDecimalInput.svelte:344` ha un `maxlength` che può tagliare un incolla. Senza limite e via `Number()`: l'editor dei dati
   e il CSV (`ui/data-editor/DataEditor.svelte:221–236`, `CsvEditor.svelte:83–103`, `ErasableNumberCell.svelte:65`, T; colonne
   dei prezzi a `step 0.01` in `AssetDataEditorSection.svelte:73–76`, AF), il passo di correzione dell'import
   (`FixFlaggedStep.svelte:770, :865`, IW), il Bulk (`TransactionBulkModal.svelte:187, :190, :2213`, il segno girato passando da
   `Number`, TR). L'evento creato al volo **arrotonda in silenzio a 8** (`EventCreateMiniModal.svelte:84–87`, `toFixed`, TR).
7. *Frontend, visualizzazione*: quantità tagliate a 6 (`components/transactions/shared/txDisplayHelpers.ts:21`,
   `utils/transactions/resolveValidationMessage.ts:198`, `features/brokers/lots/unifiedLotsTableHelpers.ts:64`,
   `lotGanttChartHelpers.ts:108, :119`, `features/dashboard/ExposureTable.svelte:155` DV) o a 8 (`LotWacPriceChart.svelte:493`,
   `LotCustodyModal.svelte:78` BK; `GapFixStep.svelte:72`, `FixFlaggedStep.svelte:426` IW). Prezzi a 2–4 decimali, un prezzo
   PEPE si legge `0,00` o `0,0000`: `AssetTable.svelte:221`, `AssetPriceSummary.svelte:99, :112`, `AssetCard.svelte:226, :233`,
   `ProviderAssignmentSection.svelte:379` (AF); `providerProbe.ts:124, :135`; `charts/candlestickChartHelpers.ts:94–97`,
   `priceChartHelpers.ts:605`; `PriceChartFull.svelte:814, :817, :882`, `LineChart.svelte:737–739, :819`,
   `MeasurePanel.svelte:300–301` (DV); `LotWacPriceChart.svelte:507, :516` (BK); `WacPreviewSection.svelte:559–568` (TR). Test
   che fissano i 6: `lotGanttChartHelpers.test.ts`, `unifiedLotsTableHelpers.test.ts`, `ExactQuantityInput.test.ts:36`,
   `ExactDecimalInput.test.ts:89, :142, :219`; nessuno spec E2E.
8. *BRIM*: i parser leggono esatto (`Decimal` da stringa; `_brim_io._coerce_number` passa da `str(float)`, esatto fino a 15
   cifre). I duplicati confrontano le quantità con `QUANTITY_TOLERANCE = 0.0001` (`services/brim/brim_provider.py:2156`): a
   quantità da satoshi due acquisti diversi coincidono sulla quantità (resta l'importo a 0,01).
9. *Matematica (J)*: `services/financial_math/yield_on_cost.py:37`, tolleranza `1e-6` sulle quantità dello split: una quantità
   sotto il milionesimo conta come zero.

**Il limite del REAL, misurato**: alzare solo la scala mostra il rumore del double: a scala 10 `12345678.9` torna
`12345678.9000000004`, a scala 12 `65000.123456` torna `65000.123456000001` (un prezzo BTC in euro con cifre false). Un double
garantisce 15 cifre significative: `1234567.123456789` (16) non torna uguale.

**Proposta**
1. *Un tipo di colonna* (`TypeDecorator` in `backend/app/db/`) per quantità e prezzi: scrive il float come oggi; **rilegge il REAL
   come il decimale più corto che lo rappresenta** (`repr`), portato a 15 cifre significative, al più alla scala della colonna,
   **mai sotto i 6 decimali** (la forma di oggi: `10.000000` resta `10.000000`; API, golden come
   `fixtures/native_cash_guard/eur_only_golden.json` con 48 quantità, e test non cambiano per i valori a ≤ 6 decimali).
   Prototipo misurato: `0.0000034573`, `12345678.9`, `65000.123456`, `99999.1234567891` tornano esatti; `0.1 + 0.2 − 0.3` torna 0;
   `func.sum` passa dal tipo; `db/precision.py` legge `precision`/`scale` dal tipo; DDL `NUMERIC(22, 10)`. Quantità
   (`transactions.quantity`) `(22, 10)`, prezzi (`price_history` open/high/low/close/adjusted_close) `(24, 12)`: le cifre intere
   restano 12. Importi (`amount`, `cost_basis_override`) e `asset_events.value` restano `Numeric(18, 6)`.
2. *Limiti in input, rifiuto col massimo*: quantità ≤ 10 decimali, prezzi ≤ 12, e ≤ 15 cifre significative in tutto (D1).
   Codici col parametro `{max}`: per le transazioni come issue del batch (codice, parametri, campo:
   `schemas/transactions/batch.py:150–151`), per i prezzi un 422 dello schema. Fonte unica: la scala del modello, già letta da
   `get_model_column_precision` (`db/precision.py`).
3. *Prezzi*: l'input dell'utente (upsert manuale, CSV) è rifiutato dallo schema prima di `price_store`; il
   `truncate_priceHistory` resta per i prezzi dei provider (float lunghi, non digitati), ora a 12.
4. *Migrazione: nessun DDL, nessun passo sui dati* (precedenti 002 e 004): su SQLite la dichiarazione non limita ciò che si salva
   e l'arrotondamento è del modello Python, che cambia col codice. Per le installazioni nuove (D3): (a) solo il modello, `001`
   dichiara ancora `NUMERIC(18, 6)`, innocuo su SQLite; (b) come 004 per `VARCHAR(14)` → `(32)`: `001_initial.py` dichiara il vero
   e la ragione va nel docstring della migrazione della release. La regola di `backend-db.instructions.md` vieta di toccare 001
   per tabelle già rilasciate; 004 l'ha fatto per una dichiarazione che SQLite ignora. Da aggiornare comunque la convenzione
   «`Numeric(18, 6)`» nelle istruzioni DB, nel docstring di `models.py:5` e in `test_db/db_schema_validate.py:10`.
5. *Per chi ha già dati*: quantità salvate con più cifre (1.1, import, API) tornano visibili fino a 10 decimali; i prezzi no
   (troncati in scrittura). I valori a ≤ 6 decimali restano identici, anche nella forma. Posizioni, costi e P&L di chi ha quantità
   con più cifre cambiano di poco: il FIFO/WAC (J) riceve le cifre vere.

**Decisioni**
- **D1** — oltre 15 cifre significative il valore non torna uguale: rifiutarlo (coerente con «mai in silenzio»)? Proposta: sì.
- **D2** — righe BRIM oltre il limite (una quantità a 12 decimali nel file): rifiutate alla conferma, col messaggio nel wizard?
  Proposta: sì (i broker ne mostrano 6–8).
- **D3** — migrazione (a) o (b). Proposta: (b), nota nel docstring della migrazione della 1.3 (la 009 di A se A è d'accordo,
  altrimenti una 010 di sola documentazione).
- **D4** — i `.svelte` sono in TR, IW, BK, AF, DV e T: servono i via dei colori, lotto per lotto.

**Lotti proposti** (ognuno coi rossi prima della cura)
- **C-97a, backend** (nessuna area): il tipo di colonna, i limiti in input coi codici e le chiavi i18n, `price_store`, la
  migrazione secondo D3, le istruzioni DB. Rossi: quantità a 8 e 10 decimali rilette uguali (create e update), il prezzo
  `0.0000034573` riletto uguale, i rifiuti a 11 e 13 decimali e a 16 cifre, la somma senza rumore, la forma `10.000000`
  invariata. `api sync` se l'OpenAPI cambia. Riga 🐛 del CHANGELOG e doc utente con questo lotto.
- **C-97b, input** (TR, T, IW, AF): `maxFractionDigits={10}` nei due `TxForm*`; il messaggio del massimo in
  `ExactQuantityInput`/`ExactDecimalInput` e il `maxlength`; editor dei dati e CSV dei prezzi come stringhe col limite; il passo
  di correzione dell'import; i `Number()` del Bulk; l'evento al volo limitato a 6 col messaggio.
- **C-97c, visualizzazione** (TR, BK, AF, DV): le quantità a 10 (prima i `.ts`, poi `ExposureTable`); un formatter dei prezzi a
  cifre significative (almeno 2 decimali; sotto 1, abbastanza per 4 cifre significative; al più 12) nei punti del punto 7.
- **Fuori lotto**: la tolleranza dei duplicati BRIM → W-B51 (mia); a J la tolleranza `1e-6` di `yield_on_cost.py:37` e il
  confronto `!= 0` su una somma di REAL in SQL (`assets/crud.py:282`, lotto G); importi oltre 6 decimali ancora arrotondati in
  lettura (fuori da C-97 per decisione).

**Rischi**: il tipo di colonna tocca ogni lettura di quantità e prezzi (posizioni, saldi, FIFO, export): «mai sotto i 6» tiene
fermi i valori di oggi, e `services`, `api` e `financial_math` lo provano. Un prezzo sopra 999 con 12 decimali supera le 15 cifre:
in input lo rifiuta D1; dai provider si legge a 15 cifre.

> **⚠️ Fuori pista — W-B30 ha rotto la build strict di `dev_release2`** (coordinatore, 14:31): il paragrafo «An explicit `null`
> in an update» di `developer/backend/transactions/wac.md` (docs-writer) linka `split_promote.md#transfer-giving-leg`, un'ancora
> che esiste solo sul mio ramo (decisione 47). La mia simulazione del cherry-pick controllava conflitti, lint e JSON, non la
> build della doc sul risultato. Il coordinatore ha corretto `dev` con `ed500643f` (il link senza l'ancora). **All'ingresso della
> 47: rimettere l'ancora** in `wac.md` (al merge le due versioni di quella riga si incontrano: tenere quella con l'ancora).
> **Procedura da ora**, prima di ogni handoff con cherry-pick: `files/scripts/sim_cherry_pick.sh <target> [--docs] <file>…`
> (cartella di sessione) esporta l'albero del target con `git archive`, ci scrive il merge a tre vie di ogni file del lotto (base
> HEAD, nostra il target, loro il worktree), passa `ruff`/`black` sui `.py` e `json.load` sui `.json`, e se il lotto ha un `.md`
> lancia `dev.py mkdocs build` (strict) e `check-links` **dentro l'albero simulato**, col carico sotto 50. Validata sul caso vero
> (14:33): su `ed500643f^` (= `04dcf3a37`, lo stesso target della simulazione di W-B36b) → **FAILED**, con l'avviso esatto
> dell'ancora mancante; build in circa 70 s; albero rimosso a fine prova.

### C-97a — quantità a 10 e prezzi a 12 decimali, backend: disegno ⏳ (2026-10-16)

> **Decisioni del developer** (coordinatore, 15:33): il disegno dell'analisi approvato. Salvataggio **REAL** (niente testo,
> niente ricostruzione di tabelle); la colonna rilegge il decimale esatto più corto, al più 15 cifre significative. **D1 sì**
> (oltre 15 cifre significative: rifiuto con messaggio chiaro); **D2 sì** (una riga BRIM oltre il limite: rifiutata alla
> conferma, col messaggio nel wizard); **D3**: `001_initial` dichiara il tipo vero, la ragione nel docstring della migrazione
> della 1.3, **nessuno script dopo l'avvio**; nota nella 009 di A se A è d'accordo, altrimenti una 010 di sola doc. Limiti:
> quantità 10, prezzi 12, importi 6; i prezzi dei provider troncati a 12. **Nessuna pulizia** dei dati salvati («quel che è
> fatto è fatto»). **Le somme in SQL passano in Python** (`Decimal`, esatte): miei `transactions/balances.py` e
> `assets/crud.py:282`; i loader del PAC li fa MF (lotto G1, dopo J-17). Da valutare nel lotto i 3 confronti a zero in SQL e i
> 2 filtri `func.abs(amount)`. D4 (aree dei colori) lo segue il coordinatore. Ordine: C-97a prima (rossi, CHANGELOG, doc),
> poi input e visualizzazione.
> **Accordo con MF** (15:4x): la casa delle somme esiste ed è pura, nessuna funzione nuova:
> `financial_math/ledger_totals.position_quantities(rows, as_of=None)` per le quantità,
> `financial_math/native_cash.native_balances` con `cash_movement_from_transaction` per la cassa; righe leggere (solo le
> colonne); i filtri restano nella query, la soglia di polvere al chiamante. Verificata l'unica differenza:
> `position_quantities` salta le righe a quantità 0 (i dividendi), dove la somma SQL dava una riga a 0; i tre lettori leggono
> una riga mancante come zero (`brokers/summary.py:89`, `brim/brim_gap_fix.py:76`, il replay `.get(…, 0)`).

**Contratto** (rossi e cura lo seguono alla lettera)
1. *Il tipo di colonna*: `backend/app/db/real_decimal.py`, `RealDecimal(precision, scale)` (`TypeDecorator` su `Numeric`,
   `cache_ok`). Scrive come oggi (il `Decimal` diventa float, REAL). Rilegge il REAL (o l'INTEGER, che SQLite tiene per un
   valore intero) come il decimale più corto che lo rappresenta (`repr` del double), portato a `REAL_SIGNIFICANT_DIGITS = 15`
   cifre significative, arrotondato alla scala se ne ha di più, **completato a 6 decimali se ne ha meno** (la forma di oggi:
   `10` torna `10.000000`). Colonne: `Transaction.quantity` → `RealDecimal(22, 10)`; `PriceHistory` open, high, low, close,
   adjusted_close → `RealDecimal(24, 12)`. Gli importi (`amount`, `cost_basis_override`), `asset_events.value`, `volume` e i
   cambi restano come sono.
2. *`db/precision.py`*: `get_model_column_precision` accetta il `TypeDecorator` (oggi `isinstance(…, Numeric)` lo rifiuta);
   `truncate_to_db_precision` su una colonna `RealDecimal`: alla scala e poi a 15 cifre significative, sempre `ROUND_DOWN`,
   così il valore scritto è quello che si rilegge (`refresh.py:423–424` confronta il nuovo col vecchio). Nuova
   `decimal_limit_issue(value, model, column) -> tuple[str, int] | None`: `("decimalPlacesExceeded", scala)` se i decimali,
   senza gli zeri finali, superano la scala della colonna; altrimenti `("significantDigitsExceeded", 15)` oltre 15 cifre
   significative; `None` se va bene. Una sola fonte: la scala del modello.
3. *Transazioni* (D2: alla conferma, non al parse del BRIM): una fase `check_decimal_limits(context)` subito dopo
   `parse_inputs` (`transaction_batch_stages.py`, chiamata da `execute_batch`), su create e update: `quantity` (campo
   `quantity`, scala 10), `cash.amount` (campo `cash.amount`, 6), `cost_basis_override.amount` (campo `cost_basis_override`,
   6). Un issue per campo: `code` `decimalPlacesExceeded` o `significantDigitsExceeded`, `params` `{"max": N}`, `field`,
   `ref_id` l'id dell'update, `error` in inglese col campo («Quantity: at most 10 decimal places»). La riga resta nel batch
   (la coppia non si rompe); il batch non si salva. I due codici entrano in `TXValidationCode`
   (`GET /transactions/types` → `validation_codes`).
4. *Prezzi*: `bulk_upsert_prices` con `source_plugin_key == "MANUAL"` (l'API) rifiuta prima di scrivere, come il cambio di
   valuta: `ValueError` → HTTP 400, con l'asset, i massimi (12 decimali, 15 cifre) e le date; i provider troncano (punto 2).
   `FAPricePoint` e `FAUpsert` non cambiano: li costruiscono anche i provider (`refresh.py:533`).
5. *Eventi*: `bulk_upsert_events` (solo l'API) rifiuta un valore oltre 6 decimali o 15 cifre come il cambio di valuta:
   `AssetSourceError("EVENT_TOO_MANY_DIGITS", …)`, 400 in `_REFUSAL_STATUS`, `params` coi massimi e gli eventi.
6. *Somme in Python*: `_get_balances_before_date` (e quindi `get_balances_at_end_of`) con una sola query di righe leggere
   per cassa e quantità; `get_asset_holdings`; `assets/crud.py` (`held_own`/`held_others`: `position_quantities`, poi
   `> QUANTITY_DUST_THRESHOLD`).
7. *Confronti in SQL, valutati*: `lots_analysis_service.py:557` (`amount != 0`), `portfolio_service.py:151–152`
   (`quantity != 0`), `transactions/queries.py:79, :81` (`func.abs(amount)` tra due limiti): tutti per riga, senza
   aritmetica, sul REAL salvato: un REAL che vale 0 è 0, e un limite passa per lo stesso float del valore. Nessun rumore,
   C-97 non li cambia: nessuna modifica.
8. *Messaggi*: `transactions.errors.decimalPlacesExceeded` «At most {max} decimal places» e
   `transactions.errors.significantDigitsExceeded` «At most {max} significant digits» (4 lingue); il risolutore
   (`frontend/src/lib/utils/transactions/resolveValidationMessage.ts`, file `.ts`, nessuna area) mette davanti
   l'etichetta del campo per questi due codici: «Quantity: At most 10 decimal places».
9. *Migrazione (D3)*: `001_initial.py` dichiara `NUMERIC(22, 10)` per la quantità e `NUMERIC(24, 12)` per i cinque prezzi; la
   ragione (la dichiarazione che SQLite ignora, come 002 e 004; la lettura del modello) nel docstring della migrazione 1.3.
10. *Istruzioni e doc*: `backend-db.instructions.md` («Decimal columns»), il docstring di `models.py`,
   `test_db/db_schema_validate.py:10`; doc developer `developer/architecture/database/` (index, assets_pricing,
   brokers_transactions); doc utente: il modulo delle transazioni e l'editor dei prezzi; riga 🐛 del CHANGELOG.

**Rossi** (test-author, prima della cura): il tipo su un motore in memoria (8 e 10 decimali, `0.0000034573`, `65000.123456`
a scala 12, `12345678.9` a scala 10, `10` → `10.000000`, un double a 17 cifre → 15); `get_model_column_precision` e
`truncate_priceHistory` a 12 e 15 cifre; `decimal_limit_issue`; create e update di quantità a 8 e 10 decimali rilette uguali;
i rifiuti (11 decimali, 16 cifre, importo e costo a 7 decimali) col codice, `{"max"}` e il campo; gli zeri finali non contano
(guardia); due acquisti di `99999.1234567891` danno esattamente `199998.2469135782` in `get_asset_holdings` e
`get_balances_at_end_of` (oggi `199998.246914`; con la sola colonna e la somma in SQL sarebbe `199998.2469135780`); il prezzo
manuale `0.0000034573` riletto uguale e 13 decimali rifiutati senza scrivere nulla; un prezzo del provider a 14 decimali
troncato a 12; un evento manuale a 7 decimali rifiutato; una riga BRIM a 12 decimali presente dopo il parse (guardia D2);
Vitest del risolutore.

**Prove e definizione di fatto**: rossi visti; verdi `db`, `utils`, `services transaction`, `services transaction-cost-basis-rule`,
`services broker`, `services financial-math`, `services portfolio-engine`, `services lots-analysis-pure`, `services brim-*`
toccati, le suite dei prezzi e degli eventi; `schemas transactions`; `api sync` (OpenAPI: forse solo le descrizioni); `front
check` e il Vitest; `i18n check`; sulla copia dei dati del developer (sola lettura, solo conteggi): quante quantità hanno più di
6 decimali (tornano visibili) e che ogni altra si rilegge identica a oggi; la simulazione del cherry-pick con
`files/scripts/sim_cherry_pick.sh` e la build strict sul risultato; due commit (lettura e somme; limiti e messaggi) se la
differenza lo consiglia.

**C-97a, rossi in scrittura** (15:50): due test-author in parallelo, file distinti: (1) colonna, `db/precision.py`, prezzi ed
eventi; (2) transazioni (rilettura, rifiuti con codice, `{"max"}` e campo, guardie), somme esatte, guardia BRIM D2, membri di
`TXValidationCode`, Vitest del risolutore. Regola data loro: un rosso cade al momento del test, mai alla raccolta (i nomi
nuovi raggiunti come attributi del modulo, o attraverso i modelli). **Cura pronta** (`files/scripts/c97a_cure.py`, dry run
pulito alle 15:52: 38 modifiche in 14 file e il modulo nuovo `backend/app/db/real_decimal.py`; non applicata prima dei rossi).
Verificato prima: `TypeDecorator.impl_instance` c'è (SQLAlchemy 2.0.52); `isinstance(…, Numeric)` è falso per il tipo nuovo,
quindi `get_model_column_precision` lo scarta; un valore intero SQLite lo salva come INTEGER; un confronto `!= 0` sulla colonna
nuova funziona; il `repr` di serie porta `asdecimal=False`, che l'autogenerate di Alembic copierebbe: il tipo ha il suo.

**C-97a, i dati del developer** ✅ (15:53, carico 38; skill `real-data-copy`; copia di lavoro dalla copia di riferimento,
Alembic 008, nessun marcatore di produzione, sola lettura, `files/scripts/c97_realdata_counts.py`; solo conteggi): con la
lettura di C-97 **tutte le 216 quantità e tutti i 52 658 prezzi** (477 open, high e low; 51 227 close) **si rileggono identici a
oggi**, forma compresa: nessuna quantità salvata ha più di 6 decimali, e i prezzi erano troncati in scrittura. Le **15
posizioni** e i **2 saldi di cassa** sommati in Python sono uguali alle somme SQL di oggi. Per questo utente C-97a non cambia
nessun numero. Copia cancellata (`lsof +D` vuoto, `rm -rf`, `ls`: «No such file or directory»).

> **D3 deciso** (coordinatore, 16:04): la nota va nella **009 di A**, nessuna 010. Paragrafo scritto e mandato ad A (16:0x),
> nello stile della nota `VARCHAR(14)` della 004: la dichiarazione che SQLite ignora, la lettura del modello, nessun DDL,
> nessuna riscrittura dei dati, l'effetto per chi ha già dati (e i dati del developer identici). La modifica di
> `001_initial.py` resta in C-97a; se C-97a entra prima della 009, la nota segue con la 009. **FE8b**: IW e TR sono in `dev`
> (`e9b4ac6b0`); aspetta l'ingresso di T (~16:45), lo dice il coordinatore.
> **A** (16:05): la nota è nella 009, parola per parola, come punto 2 («Quantities keep 10 decimal places and prices 12 (C-97,
> issue #43): no DDL, no data step.»), accanto al punto 1 di A (P18); la prima riga della 009 nomina C-97. Entra nel prossimo
> commit di A (con A-24); `ruff`, `black` e Alembic puliti, una testa.

**C-97a, rossi** ✅ (16:22–16:25, carico 35–40; i conteggi coincidono con quelli che i test-author avevano previsto leggendo il
codice):
- `utils real-decimal` (nuovo, `test_utilities/test_real_decimal.py`, isolamento `pure`) **48 falliti, 23 passati**;
- `utils decimal-precision` **6 falliti** (i test che fissavano `(18, 6)`, riallineati), 15 passati;
- `services asset-source test_price_column_precision test_truncate_price` **2 falliti** (riallineati);
- `services asset-digit-limits` (nuovo, `test_services/test_asset_digit_limits.py`) **19 falliti, 13 passati**;
- `services transaction-decimal-places` (nuovo, `test_services/test_transaction_decimal_places.py`) **31 falliti, 11 passati**;
- `front-utility core-unit` (nuovo `resolveValidationMessage.decimals.test.ts`) **18 falliti**, 6408 passati.
Tutti i rossi cadono su un `AssertionError` che dice cosa vede l'utente («a BTC buy of 0.12345678 reads back as 0.123457»,
«a PEPE close of 0.0000034573 EUR reads back as 0.000003 EUR»); nessun errore di raccolta o di setup; tutte le guardie verdi.
Registro dei test: solo aggiunte in `scripts/test_runner/_backend_services.py`, `_backend_utils.py`, `_frontend_utility.py`
(superfici condivise; verificato che la registrazione di `portfolio-engine`, toccata per un attimo, è intatta).
> **⚠️ Fuori pista — segnalazioni dei test-author**: (1) `test_db/test_numeric_truncation.py` scopre le colonne con
> `isinstance(…, Numeric)` e dopo la cura salterebbe in silenzio le sei colonne nuove: riparazione chiesta al test-author;
> (2) i rossi del caso «coppia con una gamba oltre il limite» sono rossi, non guardie: oggi la coppia si salva intera;
> (3) bug esistente, fuori lotto: −1 su `low` e `high` insieme fa scattare il controllo OHLC (→ backlog); (4) gli eventi dei
> provider restano arrotondati a 6 in lettura (importi: fuori da C-97 per decisione).

**C-97a, cura** ✅ (16:29, `files/scripts/c97a_cure.py --apply`: 38 modifiche in 14 file e `backend/app/db/real_decimal.py`;
`black` ha riformattato un file, `ruff` pulito; `prettier --check` pulito sul risolutore). Chiavi i18n con `dev.py i18n add`
(sorgente `i18n/transactions/<lang>.json`): `transactions.errors.decimalPlacesExceeded` («At most {max} decimal places» /
«Al massimo {max} decimali» / «Au maximum {max} décimales» / «Como máximo {max} decimales») e
`transactions.errors.significantDigitsExceeded` («At most {max} significant digits» / «Al massimo {max} cifre significative» /
«Au maximum {max} chiffres significatifs» / «Como máximo {max} cifras significativas»). Il test-author ha riparato
`test_db/test_numeric_truncation.py`: la scoperta delle colonne legge anche un `TypeDecorator` su `Numeric` (guardia su una
tabella sonda) e un valore a tutta larghezza esercita il taglio a 15 cifre.

**C-97a, verdi** ✅ (16:30–17:0x, carico 33–49, in corsia, uno alla volta): i cinque file dei rossi `utils real-decimal` **71/71**,
`utils decimal-precision` **21/21**, `services asset-source` **61/61**, `services asset-digit-limits` **32/32**, `services
transaction-decimal-places` **42/42**; `front-utility core-unit` **6426/6426**; `db all` **exit 0** (tutte le azioni; il nuovo
`numeric-truncation` vede le sei colonne `RealDecimal`, «Helper OK»; il contratto 3 `create_all` = migrazioni passa);
`schemas transactions` **106**, `schemas assets` **70**; services `transaction` **96**, `transaction-cost-basis-rule` **80**,
`broker` **76**, `financial-math` **405**, `portfolio-engine` **40**, `lots-analysis-pure` **129**, `roi-fifo-utils` **727**,
`brim-gap-fix` **99**, `brim-create-transaction` **14**, `brim-report-sets` **259**, `brim-provider-base` **39**,
`asset-event-store` **61**, `asset-source-refresh` **18**, `asset-sync-counts` **1**, `current-price-bootstrap` **8**,
`portfolio-allocation-source` **89**, `backup-archive` **141** (1 skip), `synthetic-yield` **16**, `asset-source-guards` **29**;
`utils gate-i18n-catalog` **176**. Tutti al primo giro. Porta libera. API: slot 2 del coordinatore (~17:10–17:40),
`files/scripts/c97a_api_slot.sh` (16 azioni, dry run pulito).

**C-97a, doc** ✅ (16:50, docs-writer; nessuna build, link verificati a mano): `developer/backend/transactions/service.md`
(riga 1 della tabella degli stadi, sezione nuova «🔢 Decimal limits» `#decimal-limits` dopo «Per-type rules», «⚖️ Balance
Queries»; righe 63–105 identiche a HEAD), `developer/architecture/database/index.md` (sezione nuova «🔢 Decimal Columns»),
`brokers_transactions.md`, `assets_pricing.md`, `developer/backend/assets/events.md` (`EVENT_TOO_MANY_DIGITS`),
`developer/backend/assets/architecture.md` (prezzi manuali e del provider), `developer/backend/transactions/balance_validation.md`
(il replay somma in Python); utente: `user/transactions/import/how-to.en.md`, una frase in «💾 Save in the bulk workspace»
(nessun debito di traduzione prima: da specchiare in IT/FR/ES).
> **⚠️ Fuori pista — due correzioni al contratto, chieste al coordinatore (17:0x)**: (1) **`cost_basis_override` è un prezzo per
> unità**, non un importo (`financial_math/average_cost.py:322` lo moltiplica per la quantità; il prezzo del lotto FIFO,
> `fifo/engine.py:229–234`; la descrizione del modello: «Frozen PER-UNIT cost basis»): a 6 decimali il costo di un PEPE
> ricevuto a `0.0000034573` resta `0.000003` (−13% sulla base di costo). **Proposta D5**: con i prezzi, `RealDecimal(24, 12)`,
> limiti 12 e 15. (2) **Gli import Intesa sarebbero rifiutati**: `broker_intesa/plugin.py:370` calcola il costo per unità come
> `cost / qty` (1000/3 ha 25 decimali): con C-97a com'è, rifiuto a «Salva tutto» (prima il database arrotondava in silenzio);
> anche a 12 decimali. Crédit Agricole (`price / 100` per le obbligazioni) sta nei 12; nessun altro plugin calcola costi o
> importi. **Proposta D6**: un valore **calcolato** dal plugin si arrotonda nel plugin alla colonna, esplicitamente, con un
> aiuto di `db/precision.py`; i valori letti dal file restano sotto D2. (3) Il docs-writer ha misurato che il rumore di una
> somma SQL non sopravvive alla lettura a 10 decimali in 2000 gruppi a somma zero nei limiti: la doc dice solo ciò che è
> verificato (la somma SQL somma i double; la lettura a 6 nascondeva l'errore; Python dà lo zero esatto).

> **D5 e D6 decisi** (coordinatore, 17:05, nella lista «da rivedere» del developer): **D5** `cost_basis_override` con i prezzi,
> `RealDecimal(24, 12)`, 12 decimali e 15 cifre, `001` dichiarato così; **D6** un valore **calcolato** dal plugin si arrotonda
> nel plugin, esplicitamente, con un solo aiuto in `db/precision.py` (12 decimali, 15 cifre, `ROUND_HALF_EVEN`), documentato
> nella guida dei plugin BRIM; i valori **letti dal file** restano sotto D2. Prima dello slot. Delta della cura
> `files/scripts/c97a_d5d6_cure.py` (dry run pulito alle 17:06: 14 modifiche in 8 file): il modello e `001`,
> `round_computed_value(value, model, column)` in `db/precision.py`, Intesa (`cost / qty`) e Crédit Agricole (`price / 100`
> per le obbligazioni) lo chiamano, docstring e istruzioni DB. In corso: i due test-author (aspettative della base di costo a
> 12; rosso PEPE per unità; l'aiuto e i due plugin; sette colonne `RealDecimal`) e il docs-writer (D5 nelle pagine scritte,
> sottosezione «Decimal places» nella guida BRIM). **A** (17:05): la frase su D5 nella 009, nel suo prossimo checkpoint (A-27,
> commit a parte: la 009 era già committata in `bbe6c35da` col testo precedente).

**C-97a, D5 e D6: rossi, cura, verdi** ✅ (17:10–17:16, nella finestra dello slot, senza il cancello del carico, 90–145): rossi
`services transaction-decimal-places` **6 falliti** (il costo per unità oltre il limite atteso `{"max": 12}`, oggi 6; il costo
PEPE `0.0000034573` rifiutato), `utils real-decimal` **16 falliti** (colonna, precisione, troncamento, `decimal_limit_issue`
sul costo; `round_computed_value` assente), `external brim-providers TestComputedValuesAreRounded` **2 falliti** (Intesa
1000/3 a 25 decimali; Crédit Agricole `95,123456789087 / 100`); la guardia D2 (un prezzo di fondo letto dal file passa com'è
letto) verde; `db numeric-truncation` 4/4 (segue il modello). Delta applicato (`files/scripts/c97a_d5d6_cure.py --apply`, 14
modifiche in 8 file; `black`/`ruff` puliti). **Verdi**: `utils real-decimal` **92**, `utils decimal-precision` **21**, `db
numeric-truncation` **4**, `external brim-providers TestComputedValuesAreRounded intesa` **18**, `services
transaction-decimal-places` **44**, `services transaction-cost-basis-rule` **80**, `services asset-digit-limits` **32**.
**Doc** (docs-writer, 2° giro): D5 nelle pagine del 1° giro; nuova sottosezione «🔢 Decimal places» `#decimal-places` nella
guida dei plugin `developer/architecture/patterns/brim_plugin_guide.md` (la pagina che la skill indica), e la ricetta
`quantize(Decimal("0.000001"))` dell'avviso «per unità» sostituita da `round_computed_value`. Frase utente specchiata a mano
in `user/transactions/import/how-to.{it,fr,es}.md` (IT «costo di carico», FR «prix de revient», ES «coste base»; etichette e
testi del messaggio come nel catalogo); nessun debito prima → **stamp** (`mkdocs translate-stamp --file
user/transactions/import/how-to.en.md`, MD5 6477f124→5b0c1e75). Skill `brim-plugin`, regola 7: il quoziente con
`round_computed_value` (D6) e i limiti con D2. **Slot API** avviato alle 17:17 (`files/scripts/c97a_api_slot.sh`, cut-off 17:45).

**C-97a, slot API** ✅ parziale (slot 2, 17:17–17:44, carico 35–170, `--no-load-gate`; la prima azione ha ricostruito la build
debug, ~10 min, con l'`api sync` dell'avvio): **11 azioni verdi, 229 test**: `api transactions-validate` **12**, `transactions`
**26**, `tx-balance-walk` **9**, `assets-price` **18**, `prices-currency-coherence` **5**, `assets-events` **45**, `assets-crud`
**35**, `brokers` **34**, `batch-split-promote` **36**, `transfer-promotion` **3**, `prices-sync-delta` **5**. Saltate al taglio:
`current-price-persistence`, `brim`, `backup-restore`, `portfolio`, `portfolio-wac` (chiesto un altro slot). Porta libera;
nessun file tracciato nuovo dall'`api sync`. **Fermo** sulle prove leggere fino al via del coordinatore (galleria dei colori,
carico 130–170): restano `utils gate-i18n-usage`, `front check`, `check-orphans` e la simulazione del cherry-pick con la build
strict sull'albero simulato.

> **FE8b libero** (coordinatore, 17:45): T è entrato (`4d8ae68c4`), il lavoro dei colori su `components/transactions/**` è
> tutto in `dev`. **Ordine (scelta di W)**: C-97a (handoff), poi **FE8b**, poi C-97b e C-97c: FE8b sposta e divide i moduli
> delle transazioni (moduli condivisi e `features/transactions/index.ts`) che C-97b tocca (`TxForm*Section.svelte`, gli
> input), così C-97b scrive sui file nella loro casa nuova. FE8b parte dall'analisi, sulla base aggiornata dopo C-97a.

**C-97a, secondo slot API** ✅ (17:53–18:12): `api current-price-persistence` **5**, `backup-restore` **114**, `portfolio`
**51**, `portfolio-wac` **12**; `api brim` al primo giro **6 falliti, 112 passati**, tutti sulla premessa «`e2e_test_admin` … signs
in: 401». **Triage** (skill `test-triage`, §4): nel DB della corsia 415 utenti creati dai test e nessuno dei due di fixture: un'azione
`api` da sola non esegue il setup della categoria (`_api_setup` → `db_populate(force=True)`), e le mie prove `services` avevano
ricreato il DB vuoto. **Verdetto: ambiente.** Rimedio: `dev.py test … db --force populate` sulla mia corsia (il passo del setup
della categoria; il populate senza `--force` rifiuta un DB esistente), **passato col codice di C-97a** (7096 record, controlli del
portafoglio puliti, «All TRANSFER/ADJUSTMENT(qty>0) have cost_basis_override set»): anche i dati mock stanno nei limiti nuovi.
`api brim` di nuovo: **118/118**. → **W-B54** (il runner, superficie di H). **Tutte le 16 azioni `api` verdi.**

**C-97a, prove leggere e simulazione** ✅ (18:13–18:19, carico 39–47): `utils gate-i18n-usage` **195**, `front check` **0 errori,
0 avvisi**, `check-orphans` (ogni file di test registrato). **Simulazione del cherry-pick** (`files/scripts/sim_cherry_pick.sh
dev_release2 --docs`, 46 file del lotto, il journal escluso): **0 conflitti**; `ruff`/`black` puliti sui `.py` risultanti tranne
`scripts/test_runner/_backend_utils.py`, il cui `black --check` fallisce già su HEAD e su `dev_release2` (una riga del banner
del Designer Lab, non mia; le mie righe sono solo l'aggiunta di `real-decimal`); JSON validi; **`mkdocs build` strict exit 0 e
`check-links` exit 0 sull'albero simulato**. `git diff --check` pulito; porta libera. **Handoff FROZEN** (18:2x): un commit.

**C-97a committato** (coordinatore, 18:29): `5c4426e75` (codice) e `d8c2a13c7` (journal) sul ramo (HEAD `d8c2a13c7`, verificato,
worktree pulito), cherry-pick **`bab52635d`** in `dev_release2` (treno 123), senza conflitti; il cancello su `dev` lo gira il
coordinatore; la riga 🐛 del CHANGELOG nei suoi record. **Il conteggio di D5** (18:29, carico 31, copia di lavoro, sola lettura):
nei dati del developer **nessuna riga ha `cost_basis_override`**: D5 non cambia nessun numero. Copia cancellata (`lsof +D` vuoto,
`rm -rf`, `ls`). Prossimi: W-B53, FE8b (analisi), C-97b, C-97c.

**C-97a, la forma dei valori calcolati (D6)** ✅ (2026-10-16, 19:4x–20:0x). **Trovato da MF**: il suo `all-backend` (su
`0452e592c`, con C-97a) ha 2 rossi in External, `TestCreditAgricoleCanonicalCharacterization::test_csv_freezes_entire_output[securities]`
e `test_xlsx_matches_entire_literal_csv_output[securities]` («complete parse output drifted»). Riprodotti nella mia corsia: **2 falliti**.
**Triage** (skill `test-triage`; §1 no: i valori ci sono tutti, cambia la forma): confronto campo per campo, cambia solo
`cost_basis_override.amount` (le 14 righe ADJUSTMENT del 2024-06-05; gli INTEREST nel messaggio di pytest sono l'inizio del dict
troncato). `round_computed_value` quantizzava **sempre**, quindi riempiva fino alla scala: `100.00 / 100` → `1.000000000000`,
`0.9369` → `0.936900000000`. Stesso valore, forma diversa: la caratterizzazione fissa la forma, e il wizard avrebbe mostrato gli zeri.
**Verdetto: difetto, mio (D6).**
> **⚠️ Fuori pista**: nei verdi di C-97a avevo girato di `external brim-providers` solo la classe nuova e Intesa, non i 737:
> errore di selettore mio. D'ora in poi, quando cambia un plugin o un helper che i plugin chiamano, **tutto** `external brim-providers`.

**Guardia rossa** (test-author `510e98ef`): `test_round_computed_value_keeps_the_form_of_a_value_that_fits` in
`test_utilities/test_real_decimal.py`, 4 casi (`1.00`, `0.9369`, `100.00/100` su `cost_basis_override`, `12.5` su `amount`),
confronto con `str()`, poi valore e `decimal_limit_issue`. **Rosso 4/4 per la ragione giusta** (`1.000000000000`,
`0.936900000000`, `12.500000`). **Cura** (`files/scripts/c97a_form_fix.py --apply`, poi una rifinitura a mano):
`round_computed_value` quantizza solo quando il valore ha **più decimali della scala**, o non è finito (lì il comportamento di
prima: `quantize` rifiuta l'infinito); il passo a 15 cifre significative lascia com'è un valore che ne ha meno. Docstring
aggiornata; le attese già scritte per D6 (1000/3, 100000/3, 2/3, 1/3 su importo e quantità, i due pareggi, il bond CA
0.951234567891) restano valide, verificate a mano prima della cura. **Verdi** (corsia 6184, slot 2): `utils real-decimal`
**96**; **tutto** `external brim-providers` **736 passati, 1 saltato** (il caso Degiro di `TestWindows1252Invariance`, già
saltato prima); `services transaction-decimal-places` **44**. `black`/`ruff` puliti, `git diff --check` pulito. **Simulazione
del cherry-pick** su `dev_release2` (`b9c549300`), i 2 file: **0 conflitti, pulito**. Doc invariate: descrivono la regola del
valore (half-even alla scala, poi 15 cifre), che resta vera. **Handoff** al coordinatore come checkpoint a sé, prima di W-B53:
`backend/app/db/precision.py` e `backend/test_scripts/test_utilities/test_real_decimal.py`.

### W-B53 — scaldare il pool BRIM all'avvio: analisi ⏳ (2026-10-16)

**Stato reale** (HEAD `d8c2a13c7`): `backend/app/services/brim/brim_parse_pool.py` crea il pool alla prima analisi (`_get_pool`,
`ProcessPoolExecutor` con contesto `forkserver`); il primo worker è un interprete nuovo che importa
`backend.app.services.brim.brim_provider` e tutto il registro dei plugin. Il test a tempo (`TIMEOUT = 30`,
`backend/test_scripts/test_api/test_brim_api.py`, `TestParseEndpoint`) arriva dopo i 9 test di `TestFileStorage`: il suo primo
`/parse` paga quel costo. **Misurato** (18:3x, carico ~31, `files/scripts/wb53_measure2.py`, `PYTHONPATH` alla radice come il
server): oggi il primo richiamo che importa il modulo BRIM costa **3,94 s** (sotto carico 100–170 diventa i 31–49 s di J), il
secondo 1 ms; con il **forkserver precaricato** (`set_forkserver_preload` + `forkserver.ensure_running()`) il primo richiamo
costa **1,07 s** se arriva subito, **0,03 s** con 3 s di vantaggio. Memoria: il forkserver passa da 21 a **~90 MB**; i worker
nascono da lui e ne condividono le pagine, quindi con più worker il totale è **minore** di oggi (oggi ognuno importa da sé).
> **⚠️ Fuori pista — misura**: la prima misura dava 0,1 s e 20 MB: il precaricamento non era avvenuto, perché
> `multiprocessing` inghiotte in silenzio l'`ImportError` del modulo da precaricare e il `sys.path` del mio script non aveva
> la radice. Il server ce l'ha; il test della cura deve controllare che il modulo sia davvero caricato nel worker.

**Disegno** (la prima proposta di J; nessuna interfaccia nuova):
1. `brim_parse_pool.py`: `_get_pool` precarica il modulo BRIM nel forkserver (`set_forkserver_preload`) prima di creare il pool;
   nuova `prewarm()`: con `forkserver` disponibile, precarica e avvia subito il forkserver (`multiprocessing.forkserver.ensure_running()`,
   ritorna in ~10 ms, l'import avviene nel processo del forkserver); qualunque errore si registra e non ferma nulla (il pool
   resta pigro, come oggi). Senza `forkserver` (solo `spawn`) non fa nulla. Il pool e i worker restano pigri: «un import non
   avvia mai processi» resta vero (il forkserver parte all'avvio dell'app, non a un import).
2. `services/platform/app_lifespan.py`: un passo `Step("brim-parse-pool", …)` dopo `market-holidays`, in background
   (`asyncio.to_thread(prewarm)` tenuto da `_keep_in_background`), come il calendario dei mercati.
3. Rossi (test-author): un worker del pool parte col modulo BRIM già caricato (osservato da una funzione d'aiuto in un modulo
   di test che non lo importa); `prewarm()` avvia il forkserver prima di ogni analisi (in un interprete a parte: il forkserver è
   unico per processo); il passo di avvio c'è, dopo `market-holidays`; guardie: `prewarm()` non solleva mai, l'analisi
   funziona dopo il riscaldamento. Selettori: `services brim-parse-pool`, i test del ciclo di vita dell'app, `api brim` (slot).
4. Doc: `developer/architecture/overview.md` (l'elenco dei passi di avvio), `developer/backend/brim/architecture.md` (la riga
   «Parse»).

**W-B53, rossi in scrittura** (18:4x, test-author): il worker nasce col modulo BRIM caricato (osservato in un interprete a parte,
con un modulo sonda che non lo importa), `prewarm()` avvia il forkserver lasciando pigro il pool, il passo `brim-parse-pool`
dopo `market-holidays`, guardie (nessuna eccezione da `prewarm`, analisi funzionante dopo). **Cura pronta**
(`files/scripts/wb53_cure.py`, dry run pulito: 8 modifiche in `brim_parse_pool.py` e `app_lifespan.py`), non applicata.
> **⚠️ Fuori pista — il contratto corretto dal test-author** (19:0x): precaricare `brim_provider` **non carica i 33 plugin**:
> il registro li scopre al primo `get_provider_instance`, dentro `parse_file`, quindi ogni worker li avrebbe importati alla
> prima analisi; la mia misura cronometrava solo l'import del modulo. Misurato (carico ~46): import 1,05 s + scoperta 0,35 s,
> 107 MB in tutto. **Contratto nuovo**: il forkserver precarica un modulo nuovo e minimo,
> `backend/app/services/brim/brim_parse_preload.py`, che importa `brim_provider` e il registro e lancia
> `BRIMProviderRegistry.auto_discover()` dentro `try/except Exception` (il forkserver sopravvive solo a un `ImportError` nel
> precaricamento; un errore di scoperta lo riporta il primo parse del worker, come oggi); `_PRELOAD` lo nomina per stringa (il
> modulo del pool non deve scoprire i plugin quando lo si importa); una nota sul precaricamento unico per processo (il pool
> BRIM è l'unico utente del forkserver). La scoperta gira sotto un lock e lascia `_discovery_done` vero: i worker lo ereditano.
> Il test-author: il rosso decisivo chiede anche un plugin caricato e la scoperta fatta; una guardia (il modulo di
> precaricamento non solleva quando la scoperta fallisce); `raising=False` nei due test che fanno girare tutto il lifespan
> (`test_market_calendar.py`, `test_post_migration.py`). Cura aggiornata (`files/scripts/wb53_cure.py`, dry run pulito: 8
> modifiche in 2 file e il modulo nuovo).

**W-B53, rossi** ✅ (19:13–19:19, carico 45–49): `services brim-parse-pool` **8 falliti, 9 passati** (rosso decisivo: «worker … started
without the BRIM module; a plugin module; the registry's discovery done»; rosso `prewarm`; le guardie che cadono solo per
`prewarm` o il modulo mancanti; verdi gli 8 test di prima e la guardia «importare il pool resta leggero»), `services
app-lifecycle` **2 falliti** (nessun passo `brim-parse-pool`), i due test del lifespan intero con lo stub `raising=False`
verdi. Il test-author ha aggiunto anche la guardia «il forkserver resta a un solo thread dopo il precaricamento» (nel test di
`prewarm`), che proposta da lui accolgo: forkare un processo con dei thread è ciò che il docstring del pool vieta. **Cura**
✅ (19:20, `files/scripts/wb53_cure.py --apply`: 8 modifiche e `brim_parse_preload.py`). > **⚠️ Fuori pista**: `ruff` S110
(`try`-`except`-`pass`) nel modulo di precaricamento, nessun precedente di `noqa: S110` nel codice: l'errore di scoperta ora si
registra nel forkserver (`structlog`), il che serve anche all'operatore. Controllo a mano: il modulo di precaricamento, in un
interprete nuovo con la radice nel `sys.path`, lascia la scoperta fatta, 33 plugin, 1 thread. **Verdi** ✅ (19:22–19:29, carico
33–49): `services brim-parse-pool` **17/17** (18,6 s invece di 150 s: i test a interprete nuovo usano il forkserver
precaricato), `app-lifecycle` **44**, `risk-all test_the_lifespan_prewarms` **1**, `db post-migration
test_the_server_runs_the_fixes` **1**, `brim-parse-race` **42**, `brim-provider-base` **39**, `brim-parse-error` **4**;
`black`/`ruff` puliti. Porta libera. Doc: docs-writer in corso; `api brim`: slot chiesto.

> **N56 (coordinatore, 19:30): il riscaldamento è opzionale.** +80 MB fissi e +1,4 s di CPU a ogni avvio per 3,9 s alla
> **prima** importazione: un cattivo affare per le macchine piccole del Cloud; i 30–48 s a freddo li vede solo la nostra
> macchina di test sovraccarica. **Disegno (approvato)**: `LIBREFOLIO_BRIM_PREWARM` letto da un modulo di sezione nuovo,
> `backend/app/config/brim.py` (proprietario W; lo schema di `sleep_wake.py`): non impostato o vuoto → **segue la modalità**
> (spento in produzione, acceso in modalità test, letta solo con `is_test_mode()`: nessun cambio al runner, che toglie la
> variabile e mette `LIBREFOLIO_TEST_MODE=1`); `1/true/yes/on` e `0/false/no/off` decidono; altro → `BrimConfigError` (un
> `ValueError` con `.variable`), il passo lo registra come avviso e non avvia nulla. Il passo resta in elenco; il
> precaricamento resta sulla via pigra (la prima analisi avvia il forkserver, che carica i plugin). Sezione «Broker Import»
> di `.env.example` mia. **Revisione di H** (sola lettura, OK sulla posizione nei 3 hunk di `app_lifespan.py`): il test della
> posizione con `assert_in_relative_order(app_lifespan.STARTUP_STEPS, ("market-holidays", "brim-parse-pool", "scheduler"),
> "STARTUP_STEPS")`; la modalità test solo con `is_test_mode()`; in `.env.example` la riga commentata
> `# LIBREFOLIO_BRIM_PREWARM=false   # test mode: true`, nella sezione «Broker Import» dopo «Risk Engines»; doc secondo C-99
> (la spiegazione intera sulla pagina della funzione, una riga in `configuration.md`); prove in più `shutdown-budget`,
> `shutdown-process`, `config-env-example`, `app-lifecycle`.

**W-B53/N56, rossi** ✅ (19:45–19:46, slot 2): test del test-author `5b49e819` (nessuna esecuzione sua). `services app-lifecycle`
**3 falliti, 46 passati**: `…_starts_nothing_when_the_warm_up_is_off[production-default]` e `[off-in-test-mode]`, `…_logs_an_invalid_setting_starts_nothing_and_the_startup_goes_on`,
tutti per «the step started {<Task pending … to_thread()>}» (il passo avviava comunque); `services config-brim` (file nuovo
`test_services/test_config_brim.py`, registrato `isolation="pure"`) **51 falliti**, tutti `ModuleNotFoundError:
backend.app.config.brim`, dentro i test e non alla raccolta. Il test della posizione è passato a `assert_in_relative_order`
(rinominato `…_prewarmed_after_the_market_holidays_and_before_the_scheduler`); ogni caso mette la modalità con monkeypatch e
ne verifica la premessa con `is_test_mode()`; l'avviso deve nominare la variabile; una barriera (lo stesso passo con `1` deve
chiamare la controfigura in un thread) prova che i casi «nulla» provano qualcosa.
> **⚠️ Fuori pista — la guardia di `.env.example` non vede una costante**: il rilevatore registra solo i nomi letterali, quindi
> `os.environ.get(BRIM_PREWARM_VARIABLE, …)` non avrebbe obbligato la riga. `brim.py` legge col nome letterale (la costante
> resta per i messaggi); verificato chiamando il rilevatore: lettura vista in `config/brim.py:44`, riga documentata.

**Cura N56** ✅ (19:46, `files/scripts/wb53_n56_cure.py --apply`: 4 modifiche in 3 file e `config/brim.py` nuovo): il passo
chiede `brim_prewarm_enabled()`; `BrimConfigError` → `logger.warning("BRIM parse pool prewarm off: invalid setting",
variable=…, error=…)`; docstring del pool; la sezione «Broker Import» di `.env.example`. `black`/`ruff` puliti sui 9 file.
**Verdi** ✅ (19:47–19:50, carico 46–58, slot 2; `files/scripts/n56_greens.sh`, uno alla volta): `services config-brim` **51**,
`app-lifecycle` **49**, `brim-parse-pool` **17**, `shutdown-budget` **188**, `shutdown-process` **7**, `config-env-example`
**38**, `risk-all test_the_lifespan_prewarms` **1**, `db post-migration test_the_server_runs_the_fixes` **1**. **Slot 2, `api
brim`** ✅ (19:51–19:56): prima `db populate --force` sulla mia corsia (W-B54: i `services` lasciano il DB vuoto; 7096
record), poi **118/118** in 2:20; nel log del server il forkserver parte all'avvio col precaricamento («BRIM parse pool
forkserver started», 19:54:07) e il pool alla prima analisi, 12 s dopo; `TestParseEndpoint` tutto verde (J-30). Porta libera.
> **⚠️ Fuori pista — «a ogni risveglio»**: il docs-writer ha notato che una macchina Fly *sospesa* riprende senza riavviare il
> server (`admin/sleep_wake`): lì il costo è solo la memoria; la CPU si paga a ogni avvio vero (deploy, riavvio, risveglio di
> una macchina *fermata*). La decisione non cambia (gli 80 MB bastano); corretti il docstring di `config/brim.py` e
> `.env.example` («at every server start»); detto al coordinatore.

**Doc N56** ✅ (docs-writer `c85c1769`, rivista e verificata sul codice): `developer/backend/brim/architecture.md`, la riga
«Parse» e la sottosezione nuova «🔥 Preload and warm-up» `#parse-pool-warm-up` (precaricamento sulla via pigra, attesa della
prima analisi, `prewarm()`, N56 con la tabella dei valori, il server di test che si scalda sempre, quattro regole, i
selettori); `developer/architecture/overview.md`, il passo 15 `brim-parse-pool` (`scheduler` e `idle-monitor` diventano 16 e
17); `developer/architecture/settings.md`, «Seven exist today» con `brim.py`; `admin/configuration.en.md`, **una riga** (C-99),
dove ho corretto «by developer decision N56» in «by decision N56» (è del coordinatore). **IT/FR/ES di `configuration` non
specchiate**: quelle pagine non hanno nessuna riga della 1.3 (EN 534 righe, IT 126), quindi la pagina intera va al giro di
Aphra; **niente stamp**. Seguito accolto: una regola nella guida dei plugin BRIM (un modulo di plugin non avvia thread,
processi o connessioni quando lo si importa: lo importa il forkserver, che deve restare a un thread).

**W-B53, prove leggere e simulazione** ✅ (20:00–20:17, carico 46–49): `black`/`ruff` puliti sugli 11 `.py`, `git diff --check`
pulito, `check-orphans` (360 file backend raggiungibili). **Simulazione del cherry-pick** su `dev_release2`: dev è andato avanti
(merge di A, `68355911f`, poi `9d9030a94` e `624fa5609`): **3 conflitti veri** più 2 del journal.
- `test_app_lifecycle.py`, la docstring del modulo: la frase di H-15 (`plugin-secrets-check`) nello stesso punto della mia →
  tenute tutte e due, prima quella di H-15.
- `overview.md`: il mio ramo ha ancora il passo `lone-transfer-legs` della decisione 47, che dev non ha, e dev ha
  `admin-bootstrap` e `plugin-secrets-check` → i passi 11–15 di dev, poi `16. brim-parse-pool`, `17. scheduler`,
  `18. idle-monitor`. > **⚠️ Fuori pista**: fuori dal blocco la fusione automatica avrebbe lasciato `16. scheduler` e `17.
  idle-monitor` (stesso cambio dai due lati): pulita per git, sbagliata nel senso. L'avviso dello strict su
  `#lone-transfer-legs` era un artefatto del blocco in conflitto.
- `settings.md`: dev ha riscritto la frase (`env_url()`) → la sua, con «Seven exist today» (dev ha gli stessi sei moduli).
- Il journal (plan 04, BACKLOG) resta sul mio ramo: il plan 04 di dev si ferma a 2817 righe, e la mia sezione del BACKLOG su
  dev è un'altra.
> **⚠️ Fuori pista — lo script di simulazione lintava file per file, dal worktree**: `ruff` decide «first-party» dai file
> presenti, quindi i moduli nuovi di dev (`bootstrap_admin_service`, `plugin_secrets_check`) e i miei (`config/brim.py`, scritto
> dopo `app_lifespan.py`) risultavano di terze parti: I001 falso. Corretto `files/scripts/sim_cherry_pick.sh`: prima tutte le
> fusioni, poi il lint **dentro l'albero simulato**; e `--resolved=DIR`, che mette al posto di una fusione in conflitto il file
> risolto (rifiutato se ha ancora i marcatori).

Risoluzioni in `files/wb53_resolved/` (3 file, contro `9d9030a94`; fra quello e `624fa5609` nessuno dei 17 file è cambiato).
Simulazione con le risoluzioni su `624fa5609`: **0 conflitti, lint pulito, `mkdocs build` strict exit 0, `check-links` exit 0**.
**Revisione combinata** (dev + W-B53, nell'albero simulato, corsia 6184): `services config-brim` **51**, `app-lifecycle` **51** (i
miei 49 e i 2 di H-15), `config-env-example` **38**, `brim-parse-pool` **17**. Porta libera. **Handoff FROZEN** (20:2x): due
commit, codice e journal; su dev solo il primo.

**W-B53 committato** (coordinatore, 20:18): `193412cdf` (codice) e `7fda52929` (journal) sul ramo (HEAD `7fda52929`, verificato,
worktree pulito); cherry-pick **`618d7208e`** in `dev_release2` (treno 133) con le mie 3 risoluzioni (`overview.md` controllato:
16 `brim-parse-pool`, 17 `scheduler`, 18 `idle-monitor`); il cancello su dev lo gira il coordinatore; la riga ✨ del CHANGELOG nei
suoi record. **MF** (MF-I2, `auto_cost.py`): risposto (a), cambia lui le 4 righe di `is_split_linked` sul suo ramo; il mio ramo
in quel file aggiunge solo `_handover_cost` (decisione 47), lontano dal blocco 70–95.

### FE8b — la cartella delle transazioni in `features/`: analisi ⏳ (2026-10-16)

**Stato reale** (HEAD `7fda52929`; `dev_release2` `618d7208e`: **stessa lista di file**, contenuti diversi, vedi sotto; strumenti
in sola lettura: `files/scripts/fe8b_inventory.py`, `files/scripts/fe8b_mapping.py`, uscite in `files/fe8b/`):
- **FE8a fatto** (15/10): i tagli delle tre modali in `form/`, `bulk/`, `wizard/`. I padri restano grandi (Wizard 5 053, Bulk
  3 389, Form 1 704 righe): il ridisegno dello stato in classi è fuori dalla 1.3 (disegno di FE8a). **FE8b è una sola rinomina.**
- **Da spostare**: `components/transactions/**` 66 file (29 264 righe), `utils/transactions/**` 49 (11 553), `utils/brim/**` 7
  (779), `stores/transactions/**` 3 (740); in più `ui/display/CompactCashCell` (+test) e 3 test in `utils/__tests__`.
- **Usati da fuori**: 17 moduli, 31 righe d'import in 24 file: le rotte `transactions`, `brokers/[id]`, `dashboard`;
  `features/files` (`FileSetBadges`, `FilesTable` → `importReportSets`); `components/assets/AssetDataEditorSection`
  (`eventTypes`, `eventSaveError`); `ui/display/CompactCashCell` (`transactionTypeStore`, `signHintColor`);
  `ui/select/ImportPluginSelect` e `features/settings/tabs/AboutTab` (`pluginText`); `utils/broker/brokerHelpers`
  (`pluginKind`); 3 test in `utils/__tests__`; l'harness `ReportSetCardInModalHarness`; lo spec `tx-fx-completeness`.
- **`vi.mock` su moduli che si spostano**: 7 (`ImportWizardModal.test.ts` 5, `TransactionFormModal.test.ts` 1,
  `txPayloadHelpers.test.ts` 1), tutti sul file che definisce: si aggiornano i percorsi, nessun barile in mezzo.
- **Barili**: `components/transactions/index.ts` (7 righe) e `shared/index.ts` (3), usati solo dalle 3 rotte.
- **Percorsi fuori dal codice**: runner `_frontend_transaction.py` 19 e `_frontend_utility.py` 27 (i Vitest elencati per
  percorso, che `check-orphans` confronta); gate con percorsi reali `htmlSink` 6, `htmlInterpolation` 4, `flagFont` 1,
  `moneyRenderSites` 3; baseline dei colori 37 righe di misura e 3 `~split` di FE8a; 4 spec E2E; 1 harness; doc per
  sviluppatori 11 pagine; **devWiki 99 pagine, 258 righe**; 3 docstring del backend (`schemas/transactions/type_metadata.py`,
  `test_brim_providers.py`, `test_brim_degiro.py`; `test_brim_providers.py:6202` **legge `utils/brim/pluginKind.ts` come
  testo**). I 3 test del Designer Lab usano `TX_TABLE` solo come chiave di una fixture in memoria: non leggono il file.
- **Il precedente di Y** (FE7 `6f7ac70ce`, FE3 `aec49a9cb`, FE6 `ce828e9c1`, FE2 `51aff4a12`, tutti del 16/10): sole
  rinomine (FE7: 101 file, 138 righe tolte e 138 messe), **nessun barile nuovo e D-P4 rinviato a FE9** («fra feature si
  importa dal file che definisce», D-Y5 e D-Y13 del piano 09), righe di misura della baseline rinominate con gli stessi conteggi,
  **dichiarazioni `~split` lasciate com'erano** (anche quella di `GrowthChart`), doc e devWiki nello stesso commit; un modulo
  usato da molti fuori (`BrokerIcon`, 17) è andato in `ui/display`; `utils/broker/` è rimasto dov'era.
- **La mia base è indietro di 343 commit**: fra questi i lotti dei colori sui file delle transazioni (12:08–15:44, `48ecea1e2`,
  `1a01ae733`, `9c79d5b35`, `70bae91b4`, `c4b8a4ae3`, `d39728347`), per cui 36 dei file da spostare differiscono da dev
  (+1 115/−882). I miei commit su quei file (W-B44, W-B39, C-34, C-97a) sono già in dev con altri id. → **prima di FE8b serve
  l'aggiornamento della base**, o la rinomina porterebbe contenuti vecchi.

**Già fatto o contraddetto**: il `features/transactions/index.ts` della riga FE8b del §7 è superato dal precedente di Y (D-P4 a
FE9); i tagli dei file grandi (P2.4) sono FE8a. P-14 (l'accento di «broker» in 46 chiavi di `es`) e U-B9 (broker mock senza
plugin predefinito), sulla stessa riga del §7, non sono spostamenti: lotti piccoli a parte.

**Disegno proposto** (la forma del piano 43; mappa in `files/fe8b/mapping.tsv`: **124 spostamenti e 2 barili tolti, nessuna
collisione, uguale su dev**):

| Cartella | File (test) | Cosa |
|---|---|---|
| `features/transactions/` | 24 (9) | `TransactionsTable`, `types.ts`, i due store, il nucleo che più parti usano (`txPayloadHelpers`, `txCommitApi`, `commitRefusal`, `resolveValidationMessage`, `useValidateScheduler`, `resolveBrimNotice`, `resolveFormItems`, `loadTransactionRows`, `txDisplayHelpers`, `TransactionTypeSearchSelect`), `TransactionActionModal` |
| `form/` | 13 (4) | `TransactionFormModal` e le sue sezioni, `txFormFields`, `signHintColor`, `CompactCashCell` |
| `bulk/` | 18 (6) | `TransactionBulkModal` e i suoi pezzi, `PromoteAllModal`, `PromoteMergeModal`, `TransactionPickerModal`, `TransactionResultBanner`, `bulkDisplay`, `bulkTodos`, `promoteHelpers`, `promoteSuggest` |
| `import/` | 56 (21) | `ImportWizardModal` e i passi (`wizard/` confluisce qui, come deciso in FE8a), l'`import/` di oggi, `ImportBrokerMismatchModal`, `ParseDetailModal`, `TransactionCompareModal`, i 14 moduli `import*`, `gapFixModel`, …, `defaultPluginCheck`, `isFakeAssetId` |
| `events/`, `cells/`, `wac/` | 8 (3), 3, 2 (1) | come oggi; `eventTypes` in `events/` |

**Decisioni** (proposte; le alternative sotto):
- **F1 · niente `index.ts`**: D-P4 a FE9, come Y. I due barili si tolgono; le 3 rotte importano dai file che definiscono.
  Alternativa: il barile spostato come file pubblico della feature (anticipa D-P4 per una sola feature, ed esporta
  `TransactionFormModal`, che un test prende con `vi.mock`).
- **F2 · `utils/brim/` diviso**: restano `pluginText` e `pluginKind` (+test), usati da broker, settings e `ui/select`, e letti
  come testo dal backend; vanno in `import/` `defaultPluginCheck` (+test) e `isFakeAssetId`, usati solo dall'import.
  Alternativa: tutta la cartella nella feature (tre import nuovi verso la feature, due dei quali inversioni: `ui/select` e
  `utils/broker`).
- **F3 · `CompactCashCell` in `form/`**: scritto come editor generico, ma lo usano solo le transazioni (sezioni del Form, Form,
  WAC) e importa tipi delle transazioni (`SignRule`, `computeSignHint`); lasciato in `ui/display`, diventerebbe un import
  `ui → feature`. Alternativa: resta, e FE9 lo rende generico.
- **F4 · le modali nella cartella della loro parte**; alternativa a pari costo: lo specchio di oggi (`modals/` e `shared/`
  restano), con `wizard/` in `import/` e i moduli di `utils` presso i loro utilizzatori.

**Conflitti previsti**:
- Nessun ramo con commit fuori da dev tocca i file che si spostano. E (+40) e B (+5) aggiungono righe a
  `_frontend_utility.py`; BK cambia una riga di misura della baseline, non delle transazioni (`--resolve`).
- Il lavoro non committato degli altri non lo vedo: chiedo il **congelamento dei percorsi** per la durata di FE8b, con un
  annuncio come per FE8a: `components/transactions/**`, `utils/transactions/**`, `utils/brim/{defaultPluginCheck,isFakeAssetId}*`,
  `stores/transactions/**`, `ui/display/CompactCashCell*`. Nei file condivisi (rotte, `AssetDataEditorSection`, `features/files`,
  runner, gate, baseline, doc, devWiki) cambio solo righe di percorso.
- C-97b e C-97c scrivono poi sui percorsi nuovi (il motivo dell'ordine). La decisione 47 (sul mio ramo, aspetta J-17) non
  tocca i file che si spostano; in doc e devWiki (`wac.md`, `overview.md`) FE8b cambia solo percorsi.

**Complessità e rischi**: alta per ampiezza (~250 file toccati: 124 rinomine, ~300 specificatori d'import, ~260 righe della
devWiki), nulla per logica. I rischi:
- un import relativo sbagliato: lo prendono svelte-check e la build;
- un `vi.mock` che non punta più al modulo (il test passerebbe senza mock): controllo esplicito dei 7;
- un gate che confronta percorsi reali;
- un test che legge un file per percorso (`pluginKind`, che resta);
- la somiglianza delle rinomine (≥ 95 %), misurata per file prima dell'handoff.

**Passi**:
0. Il coordinatore aggiorna la base (dev → W). Verifico HEAD; rifaccio inventario e mappa sulla base nuova.
1. `files/scripts/fe8b_move.py`, deterministico, dry run e poi `--apply`:
   - `mv`, non `git mv` (lo staging è del coordinatore);
   - ogni specificatore che risolve a un file spostato riscritto nel suo stile: `$lib` resta `$lib`, relativo resta relativo;
     i 4 relativi che escono dalla feature diventano `$lib`;
   - i barili espansi nelle 3 rotte;
   - i percorsi nei runner, nei gate, negli E2E, nell'harness, nelle docstring del backend, nella doc e nella devWiki;
   - le righe di misura della baseline rinominate (stessi conteggi); le `~split` lasciate.
2. Controlli statici: ogni specificatore risolve; i 7 `vi.mock` risolvono al file nuovo; i vecchi percorsi a zero fuori dalla
   storia (journal, `~split`, `LibreFolio_devWiki/log.md`); somiglianza per file.
3. Prove nella corsia 6184; E2E in uno slot.
4. Plan e BACKLOG; simulazione del cherry-pick su dev con lo strict build; handoff FROZEN: un commit di rinomina e il journal.

**Definizione di fatto**: vecchi percorsi a zero in `frontend/`, `scripts/`, `.github/`, `backend/`,
`mkdocs_src/docs/developer/` (eccezioni dichiarate: le `~split`, la storia); rinomine ≥ 95 %; nessun barile né shim nuovo;
svelte-check 0 errori e 0 avvisi; i Vitest delle categorie toccate verdi; `front build`; `theme-roles.mjs --check` pulito con gli
stessi totali; `check-orphans`; `check_source_paths.py` a 5 path mancanti come oggi; `mkdocs build` strict e `check-links`; `lint
--dead-code` senza reperti nuovi.

**Selettori proposti**: `front check`; `front-transaction tx-unit`; `front-utility core-unit`, `component-unit`; `front-broker
broker-unit`; `front-asset asset-unit`; `check-orphans`; `front build`; `theme-roles.mjs --check`; `lint --dead-code`; `mkdocs
build` e `check-links`; `check_source_paths.py`. In slot: `front-transaction all --workers 4`, `front-broker detail`,
`front-portfolio dashboard`, `front-utility files`, `front-asset asset-data-editor`, `front-utility onboarding-tour`.

**FE8b: via** (coordinatore, 20:41): F1–F4 come raccomandato (niente `index.ts`, `utils/brim/` diviso, `CompactCashCell` in
`form/`, ogni modale nella cartella della sua parte). **Passo 0, aggiornamento della base** ✅: la fusione di dev `e5c80ad7c`
aperta dal coordinatore nel mio worktree, **7 conflitti risolti per unione** (`files/scripts/merge_e5c80ad7c_resolve.py`):
`test_app_lifecycle.py` e `settings.md` col lato di dev, che contiene già il mio; `overview.md` nell'ordine del codice fuso
(11 `lone-transfer-legs`, poi i passi di dev 12–19); `wac.md` col link ancorato a `split_promote.md#transfer-giving-leg`
(l'àncora c'è con la 47); `devWiki/index.md` la mia riga V-3 più quella di J-17; **`price_resolver.md`**: J-17 («un
ADJUSTMENT non è mai un prezzo», decisione P2) risponde al punto aperto che il testo della 47 segnalava → il testo di dev, con
il caso della 47 nominato dentro il punto di J-17; `user/dashboard/charts.en.md` il punto di J-17 e l'ultima frase della 47.
Fusi da git: il risultato differisce da dev solo per i 3 commit della 47 e per il journal (conteggi per file uguali alla patch
della 47, salvo le mie 3 risoluzioni). > **⚠️ Fuori pista**: in `devWiki/log.md` l'entrata della 47 ha perso la riga «Graph: not
updated…» già all'aggiornamento di base delle 10:49 (due entrate aggiunte in fondo dai due lati, intercalate da git): cosmetico,
lasciato. Prove sul tree fuso: `app-lifecycle` 51, `lone-transfer-legs` 20, `orphan-transfer-numbers` 21, `broker` 79,
`transaction-cost-basis-rule` 80, `roi-fifo-utils` 833, `portfolio-engine` 40, `lots-analysis-pure` 163, `mkdocs build` strict
e `check-links` exit 0, `check_source_paths.py` a 5. Committata dal coordinatore: **`cec9c6ab1`**; poi dev `27994759a` (J-24,
MF C e MF-I2 su `auto_cost.py`, A-25, Z) fuso pulito: HEAD **`f33306e41`**. Lo strumento dello spostamento è pronto
(`files/scripts/fe8b_move.py`, dry run pulito: 0 import irrisolti, 0 nomi di cartelle vecchie, ogni file spostato ≥ 95 %
simile, 4 barili espansi, 6 `vi.mock`, 12 righe della baseline, 360 menzioni di percorso). **La 47 entra in dev prima di FE8b**
(coordinatore, 20:52), dopo la prova con J-24.

### Decisione 47 in dev: la prova con J-24 ✅ (2026-10-16)

**J-24** (`9d702ae8d`, regola P21 del developer, «ogni importo al cambio del suo giorno»): un ADJUSTMENT in uscita con un costo
lasciava il capitale al costo storico del pool e non realizzava nulla; ora esce a quantità × costo dichiarato al cambio del suo
giorno (D), e la differenza dal costo medio che il pool cede (C) è realizzata, come nei lotti (CP-7a); il flusso del giorno per
TWRR e MWRR segue. La 47 scrive proprio quelle righe: la gamba che cede, ADJUSTMENT-out al **costo Auto del suo broker**
(`_handover_cost` → `compute_wac_iterative` senza suggerimento di valuta: la valuta dell'**ultimo acquisto**, ogni acquisto
convertito al cambio del suo giorno).

**Prove su `f33306e41`** (20:54–20:59, corsia 6184, `files/scripts/j24_checks.sh`, una alla volta): `app-lifecycle` **51**,
`lone-transfer-legs` **20**, `orphan-transfer-numbers` **21**, `broker` **79**, `transaction-cost-basis-rule` **80**,
`roi-fifo-utils` **865** (con i test di J-24), `portfolio-engine` **41**, `lots-analysis-pure` **163**. Tutto verde.

**I numeri della 47 (V-3) non cambiano**: i test di W li fissano tutti in EUR, senza cambi (il libro S7 e lo specchio, «B
cancellato»: Dashboard 120 investiti e P&L 60; lotti realizzato 0, proventi 80). In una valuta il costo Auto sulla riga è il
costo medio, al cambio 1: D = C, J-24 realizza 0. Il libro CP-16 di J (`test_adjustment_out_with_cost_numbers.py`, lo stesso
S7 con la riga della 47) ne è la guardia, «uguale prima e dopo J-24». **Cambia la gamba in un'altra valuta** (costo Auto in USD,
rapporto in EUR, cambio mosso fra l'acquisto e la consegna): la Dashboard realizza D − C nel giorno della consegna, come già i
lotti. Il «foreign book» di J fissa esattamente questa forma: 10 X′ comprati per 1 000 USD a 1,25 (C = 800 EUR), consegnati a
100 USD l'uno a 1,60 (D = 625 EUR): investito 175, P&L e realizzato −175; prima di J-24 0, 0, 0, contro il −175 dei lotti.
Per la 47 vuol dire: cancellato il broker che ricevette un titolo in USD, il broker che lo mandò mostra quel giorno un
realizzato di cambio, e Dashboard e lotti dicono lo stesso numero. Il test di W «capitale e P&L non si muovono» riguarda le
gambe di cassa, che J-24 non tocca. Nessun test va da capo a fondo in valuta (la cancellazione scrive il costo Auto in USD, la
Dashboard lo legge): coperto in due metà, W scrive la riga (in EUR, più i casi di cambio mancante), J la legge (anche in USD)
→ **W-B55**.

**CHANGELOG** (proposta, 🐛 Fixed, dopo la riga di N1b sulla metà che riceve): vedi il messaggio al coordinatore delle 21:0x.
Prossimi: `all-backend` nello slot del coordinatore (~21:30–21:40), l'ingresso della 47 per fusione del mio ramo (47 e journal,
43 file senza conflitti, verificato dal coordinatore), poi FE8b.

**FE8b, inventario sulla base nuova** ✅ (21:0x, HEAD `6162dfc0f`, sola lettura): stessi 125 file (42 103 righe: −233 dai
lotti dei colori di dev), stessi 17 moduli e 31 righe d'import da fuori, stessi 7 `vi.mock`; mappa **identica** (124
spostamenti, 2 barili). Dry run di `files/scripts/fe8b_move.py`: 191 file riscritti, 575 riferimenti (356 menzioni di percorso),
0 import irrisolti, 0 nomi di cartelle vecchie, 0 relativi sconosciuti, ogni file spostato ≥ 95 % simile. Corretti nello
strumento prima di applicarlo: la baseline scritta come `formatBaseline` (intestazione al suo posto, righe in ordine di code
point, dichiarazioni com'erano), il controllo degli import sui file su disco (il client generato e il catalogo i18n contano;
segnalato solo ciò che risolveva prima e non dopo), il barile usato dentro la cartella (`ImportWizardModal`, un `import type`),
le menzioni di cartella senza barra e i percorsi `../` della devWiki, `frontend/design/REPORT.md` storia (un rapporto datato
24/07), e la frase di `transaction-form.md` che nomina la cartella del Form (→ `form/`). Restano 2 voci da leggere, percorsi
già morti in due pagine della devWiki (`CashTransactionModal`, `TransactionStagingModal`), che FE8b non tocca. Vitest sceglie
l'ambiente file per file (`// @vitest-environment`), non per percorso: lo spostamento non cambia ambiente a nessun test. Pronto
ad applicarlo dopo l'ingresso della 47.

**Decisione 47, `all-backend`** ✅ (slot 2, 21:19:54–21:52:38, 32 min 39 s, carico 50–119; HEAD `6162dfc0f`, la 47 con J-24;
`files/scripts/allb_47.sh`, `dev.py test --test-port 6184 --data-dir /tmp/librefolio-r13-w --workers 2 --log-dir … all-backend`):
**7/7 categorie verdi** (External, DB, Services, Utils, Schema, API, E2E), «ALL BACKEND TESTS PASSED», **0 falliti**. Passaggi
paralleli a 2 worker: 171 unità 12 584 passati e 5 saltati; 49 unità 3 091; 12 unità 1 833; 70 unità 1 914 passati e 2
saltati; unità da sole 2 255 passati e 25 saltati (28 sessioni pytest); DB 20/20 script. In tutto ~21 677 passati, 32 saltati.
Le righe «❌» del log sono i messaggi attesi dei test negativi dei fornitori FX (`MOCKFX_FAIL`, valuta non supportata).
Porta libera dopo; DB di test archiviato dal runner (`00_archive/test-db_20261016_215237.tar.xz`); log per unità in
`files/logs/allb_47_units_2119/`. Pronta per l'ingresso (fusione del mio ramo in dev, 47 e journal).

**La 47 entrata** (coordinatore, 21:5x): fusione `ea72346b7` (treno 142), CHANGELOG `bf2c22791`; il mio ramo portato avanti
veloce a `bf2c22791`, pulito. Dal team dei colori: i 3 test del Designer Lab liberi (aggiornarli); i lotti T e AF di stasera
non toccano le 12 righe della baseline; nessun ingresso durante il congelamento. **FE8b: via e congelamento annunciato.**

### FE8b — la cartella delle transazioni in `features/`: lo spostamento ⏳ (2026-10-16)

1. ✅ **Spostamento** (21:56, `files/scripts/fe8b_move.py --apply` su `bf2c22791`; prima il dry run sulla base nuova, identico:
   tre commit di dev toccavano solo altre righe di `_frontend_utility.py` e altre rotte): 124 file in `features/transactions/`
   (radice 24, `form/` 13, `bulk/` 18, `import/` 56, `events/` 8, `cells/` 3, `wac/` 2), i 2 barili tolti, `utils/brim/` con
   `pluginText` e `pluginKind`; 191 file riscritti, 575 riferimenti (4 barili espansi, 6 `vi.mock`, 12 righe della baseline, 356
   menzioni di percorso). Con `mv`, non `git mv`: lo staging è del coordinatore.
   > **⚠️ Fuori pista — `import.meta.glob`**: lo strumento non leggeva i glob di Vite. Tre pattern relativi erano rimasti
   > quelli della cartella vecchia: `GapFixStep.test.ts` (`../../../utils/transactions/gapFixModel.ts` → `./gapFixModel.ts`) e
   > `ReportSetCard.test.ts` (`../../table/DataTable.svelte`, `../../ui/feedback/Tooltip.svelte` → `../../../components/…`),
   > ognuno con la sua chiave di lettura: corretti a mano (4 righe). Trovati con il grep dei percorsi vecchi sui file nuovi (non
   > tracciati, quindi fuori da `git grep`). Nessun altro glob, `new URL(…, import.meta.url)` o `readFileSync` nei file spostati;
   > nessuno script che scandisce solo `lib/components`, `lib/utils` o `lib/stores` (`coverage_js.py` classifica già
   > `src/lib/features/` come HIGH, come per i lotti di Y).
2. ✅ **Controlli statici** (21:57–22:0x, carico 59–100): percorsi vecchi a zero in `frontend/`, `scripts/`, `backend/`,
   `.github/`, `mkdocs_src/docs/`, devWiki, salvo le eccezioni dichiarate (le 3 righe `~split`, storia; 2 pagine della devWiki che
   nominavano già file inesistenti; `frontend/design/REPORT.md`, rapporto datato); `git diff --check` pulito; `prettier --check`
   sui 140 file toccati pulito; `theme-roles.mjs --check` «Colour gates: clean»; `check_source_paths.py` a 5 come prima (4 103
   citati); `check-orphans` (504 unità e 138 spec registrati e raggiungibili); `black` pulito; `ruff`: i 4 PLC0415 di
   `_frontend_transaction.py` ci sono già su HEAD, righe non toccate.
3. ✅ **Prove del punto 1** (slot 1, 22:06–22:26, carico 55–102; `files/scripts/fe8b_point1.sh`):
   - `front check` al primo giro **27 errori in 7 file, tutti in `features/backup/`** (`RestoreStatus`, `control_totals`, …),
     che FE8b non tocca. > **⚠️ Fuori pista — ambiente**: il client generato (`src/lib/api/generated.ts` e `openapi.json`,
     ignorati da git) era delle 21:47, cioè dell'avvio del server di `all-backend`, prima dell'avanzamento veloce che ha portato
     l'API del ripristino di B (`1e2f6374a`). `dev.py api sync` (nessun file tracciato cambiato), poi di nuovo tutto il punto 1.
     Lezione: dopo un aggiornamento di base che porta API, `api sync` prima di svelte-check.
   - Secondo giro: `front check` **0 errori, 0 avvisi**; Vitest `front-transaction tx-unit` **907**, `front-utility core-unit`
     **7 270** (con i gate dell'HTML e dei colori), `component-unit` **4 246**, `front-broker broker-unit` **60**, `front-asset
     asset-unit` **881**; `front build` verde; `mkdocs build` strict (3 084 URL relativi risolti) e `check-links` verdi.
   - `lint --dead-code --scope frontend`: exit 1 come sempre su questo albero (decine di reperti altrui: tipi di `lib/types`,
     rischio, onboarding, dipendenze `@embedpdf` non elencate). Nella feature solo `txStoreGetFiltered` e `txStoreGetVersion`
     (`txStore.svelte.ts`): **già inutilizzati su HEAD** al percorso vecchio, e nessun barile li esportava. **Nessun reperto
     nuovo.**
   - Dev è avanzato durante il congelamento (`bf2c22791` → `4e233fe5b`: Z-18, J CP-7b, E-4): l'unico file in comune è la rotta
     della Dashboard (Z alle righe 109–650, FE8b alle righe d'import 78–79: nessun conflitto); nessun riferimento nuovo ai
     percorsi vecchi, nessun file nuovo nelle cartelle congelate.
   - **Commit pronto** (22:3x): 376 percorsi nel commit del codice (`files/fe8b/stage_code.txt`: 126 tolti, 124 nuovi, 126
     modificati), il journal a parte (`files/fe8b/stage_journal.txt`); nessun file ignorato o generato fra loro; `git diff
     --check` pulito; porta libera.
4. ✅ **Prove del punto 2, gli E2E** (slot 1, 22:28–23:24, carico 44–150; dopo il commit del coordinatore: **`74e390c98`**,
   252 file e le 124 rinomine riconosciute, più `bc8a58fba` del journal; `files/scripts/fe8b_point2.sh`):
   - `db populate --force`; `front-transaction all --workers 4`: 343 + 32 passati (32 saltati del progetto mobile), **6
     rossi, nessuno dello spostamento**:
     - **3 sono un difetto di C-97a, mio, in dev dalle 18:29**: `tx-commit-all-types` «TRANSFER (asset) … dual brokers», `tx-wac-bulk`
       WB4, `tx-wac-formmodal` FM6 — commit annullato con «Cost basis override: at most 12 decimal places». In `auto` e
       `auto-detail` il Form rimanda la media dell'anteprima (100 / 3 per intero) e il backend ne legge solo la valuta
       (`auto_cost.py`, `ccy_hint`) e ricalcola l'importo, ma `check_decimal_limits` lo controllava in ogni modo. Cura nel
       checkpoint seguente («C-97a, il costo Auto»), approvata dal coordinatore, prima di C-97b.
     - **3 sono attese sul backend sotto carico** (`tx-import-report-set` R1, step 2 non in 30 s dopo l'upload; R7, step 3
       ancora «parsing» dopo 30 s; `tx-import-duplicate-precedence` E1, fermo sui duplicati 20 s, e il teardown oltre 120 s),
       a carico 100–150. **Rigirati da soli** (23:21–23:24, carico 44–54, `files/scripts/fe8b_rerun.sh`): R1 e R7 **2 passati**
       (31,9 s), E1 **1 passato** (15,1 s). Verdetto (skill `test-triage`): **lentezza**, non FE8b.
   - `front-broker detail` **38**, `front-portfolio dashboard` **27**, `front-utility files` **29**, `front-asset
     asset-data-editor` **26**, `front-utility onboarding-tour` **10**. Porta libera.
   - **FE8b pronto per l'ingresso.** W-B56 (la media dell'anteprima senza arrotondamento, da decidere con MF) nel backlog.

**FE8b entrato** (coordinatore, 23:2x): **`31335fe26`** in `dev_release2`; congelamento finito. Prossimi: C-97a, il costo Auto;
poi C-97b e C-97c.

### C-97a — il costo Auto non passa dal controllo dei decimali ✅ (2026-10-16)

**Trovato dagli E2E di FE8b** (`tx-commit-all-types` «TRANSFER (asset) … dual brokers», `tx-wac-bulk` WB4, `tx-wac-formmodal`
FM6): il commit di un trasferimento col costo su Auto è annullato con «Cost basis override: at most 12 decimal places». **Difetto
mio (C-97a), in dev dalle 18:29.** In `cost_basis_mode` `auto` e `auto-detail` il Form rimanda la media dell'anteprima, che può
essere periodica (100 / 3 per intero); il backend di quel valore legge solo la valuta (`ccy_hint`, `auto_cost.py`) e ricalcola
l'importo (`_auto_cost` → `_write_auto_cost`), ma `check_decimal_limits` controllava l'importo in ogni modo. La docstring dello
stadio e la pagina «Decimal limits» dicevano già «manual cost basis»: il codice non lo faceva. Approvato dal coordinatore come
checkpoint a sé, subito dopo l'ingresso di FE8b, prima di C-97b.

1. ✅ **Rossi** (test-author `abfb74f8`): `TestAnAutoCostBasisIsNotChecked` in `test_services/test_transaction_decimal_places.py`,
   40 casi. Rossi 30: create (TRANSFER ricevuto e ADJUSTMENT +1) e update, `auto` e `auto-detail`, `/validate` e `/commit`, 100 / 3
   per intero (26 decimali) e 1000000 / 3 come lo stampa un float (16 cifre significative), accettati; e l'esito: la riga tiene
   il costo Auto calcolato (125 / 3 → `41.666666666667` EUR, scelto diverso da 100 / 3 per distinguerlo dall'importo mandato).
   Guardie 10: lo stesso importo in `manual` resta rifiutato (D2). Visti (23:25, carico 54): **30 falliti, 10 passati**, per la
   ragione giusta (un issue di decimali sulle righe Auto, commit non fatto).
2. ✅ **Cura** (`files/scripts/c97a_auto_cost_fix.py --apply`): `_decimal_limit_values` (`transaction_batch_stages.py`) salta
   `cost_basis_override` quando `cost_basis_mode` è `auto` o `auto-detail` (la tupla letterale, come nelle altre 4 occorrenze
   del codice), con la ragione in docstring. Una frase nella pagina `developer/backend/transactions/service.md`, «Decimal
   limits» (senza traduzioni). `black`/`ruff` puliti.
3. ✅ **Verdi** (23:27, carico 49): `services transaction-decimal-places` **84** (i 40 nuovi e i 44 di prima),
   `transaction-cost-basis-rule` **80**. **Simulazione del cherry-pick** su `dev_release2` (`778156983`), i 3 file: 0 conflitti,
   lint pulito, `mkdocs build` strict e `check-links` exit 0. Da girare in uno slot, come conferma: `api transactions-validate` e
   i 3 E2E che l'hanno trovato.
4. ✅ **Conferma prima dell'ingresso** (slot 1, 23:34–23:46, carico 42–92; dopo il commit del coordinatore `de901f228` e
   `11baeab0f`; `files/scripts/c97a_auto_confirm.sh`): `db populate --force`; `api transactions-validate` **12**;
   `front-transaction tx-commit-all-types` **19** (il TRANSFER fra due broker passa), `tx-wac-bulk` **11** (con WB4),
   `tx-wac-formmodal` **10** (con FM6). Porta libera. **Pronto per l'ingresso.**

**C-97a, il costo Auto, committato** (coordinatore, 23:3x): `de901f228` (codice) e `11baeab0f` (journal). Conferma prima
dell'ingresso nello slot 2 (`files/scripts/c97a_auto_confirm.sh`: `db populate --force`, `api transactions-validate`, i 3 E2E).

### C-97b — i decimali in input: analisi ⏳ (2026-10-16)

**Stato reale** (HEAD `11baeab0f`, percorsi dopo FE8b; sola lettura). Il backend (C-97a) accetta una quantità a 10 decimali, un
prezzo o un costo per unità a 12, un importo a 6, ogni valore a 15 cifre significative; un evento a 6 (`AssetEvent.value`
`Numeric(18, 6)`, `EVENT_TOO_MANY_DIGITS`). Oltre il limite rifiuta col massimo (D2). In input:
1. **Form, quantità a 6**: `ExactQuantityInput maxFractionDigits={6}` sul campo `draft.quantity` in `form/TxFormSingleSection.svelte:176,
   :224` e `form/TxFormPairSection.svelte:192` → **10**.
2. **I due input** (`components/ui/input/ExactQuantityInput.svelte`, `ExactDecimalInput.svelte`): oltre il massimo il valore è
   segnato non valido (`digitsValid` falso) ma **nessun messaggio** dice perché; `ExactDecimalInput.svelte:169` calcola un
   `maxlength` dalle cifre ammesse, quindi un incolla più lungo è **troncato in silenzio** dal browser. → un messaggio sotto il
   campo, con le chiavi che già traducono `decimalPlacesExceeded` e `significantDigitsExceeded` (stessa frase della conferma), e
   niente `maxlength` che tagli. Li usa anche il PAC (`features/tools/pac-allocator/planner/steps/RoutingStep.svelte:277`,
   `BrokerEditor.svelte:380`): il messaggio comparirebbe anche lì. Test che fissano i 6: `ExactQuantityInput.test.ts:36`,
   `ExactDecimalInput.test.ts:89, :142, :219`.
3. **Bulk, segno via `Number`** (`bulk/TransactionBulkModal.svelte:187, :190`, `fieldsFromTx`): `String(Math.abs(Number(x)))` scrive
   «1e-8» per un satoshi `-0.00000001`, nella cella e nel payload → un helper per stringa (`txPayloadHelpers.ts` ha già
   `applySign`, `:142`). Gli altri ~30 `Number()` del Bulk confrontano o leggono il segno: entro 15 cifre sono esatti, li lascio.
4. **Evento al volo** (`events/EventCreateMiniModal.svelte:84–87`): `parseFloat` e `toFixed(min(max(2, decimali), 8))` arrotonda
   **in silenzio** a 8, oltre i 6 del backend; il valore suggerito è arrotondato a 2 (`:97`, `toFixed(2)`). → stringa
   normalizzata, al più 6 decimali col messaggio, il suggerito com'è.
5. **Editor dei dati dei prezzi**: i valori sono numeri JS, esatti entro 15 cifre, e il backend li legge bene anche in notazione
   esponenziale; ma le colonne `close/open/high/low` e `amount` degli eventi hanno `step: 0.01`
   (`components/assets/AssetDataEditorSection.svelte:73–76, :99`): per il browser un prezzo PEPE è «fuori passo» → `step: 'any'`.
   La visualizzazione a 4 decimali (`ui/data-editor/DataEditor.svelte:212`) è di C-97c.
6. **Passo di correzione dell'import** (`import/FixFlaggedStep.svelte:760, :855`): campi di testo normalizzati come stringhe,
   nessun `Number` scritto; oltre il limite li rifiuta la conferma, col messaggio nel wizard (D2). → **niente** in C-97b.

**Proprietà e colori**: `features/transactions/**` (1, 3, 4) è mio dopo FE8b e i lotti dei colori sono entrati;
`components/ui/input/*` (2) è condiviso (anche il PAC) → serve il via; `components/assets/AssetDataEditorSection.svelte` (5) è
di X (righe concesse, come in E1b) e nell'area AF → serve il via.

**Prove proposte**: rossi Vitest per i due input (il messaggio oltre il massimo, l'incolla intero), per le tre sezioni del Form
(10 decimali validi, 11 col messaggio), per l'helper del segno (mai «1e-8»), per l'evento al volo (6 col messaggio, nessun
arrotondamento); l'editor con `step: 'any'` (un prezzo PEPE accettato). Poi `front check`, Vitest `tx-unit`, `core-unit`,
`component-unit`, `asset-unit`, e in uno slot `front-transaction` (la parte del Form e del Bulk) e `front-asset
asset-data-editor`. Doc utente: le pagine che dicono 6 decimali, da cercare; CHANGELOG: la riga di C-97.

**Peso**: medio (6 file di codice, ~6 file di test). Ordine: rossi (test-author), cura, prove, doc, handoff.

**C-97a, il costo Auto, entrato** (coordinatore, 23:5x): `c91bd41b2` in `dev_release2` (i 2 commit); il plan 04 entra con C-97b.
**C-97b: via pieno** (coordinatore, 23:5x): il team dei colori non ha nulla di aperto su `ExactQuantityInput`, `ExactDecimalInput`,
`AssetDataEditorSection`; per il messaggio `text-lf-danger`, bordo `border-lf-danger`, nessuna classe di palette. X avvisato per
O-8 su `AssetDataEditorSection` (solo le mie righe `step`; chi entra per secondo risolve).

**Disegno della cura** (dopo i rossi del test-author `d227471f`):
- **Gli input condivisi**: il messaggio è un elemento fratello dopo l'`<input>` (Svelte 5 ammette più radici: fuori dallo stato
  d'errore il DOM resta quello di oggi, e i 10 chiamanti — 8 nel PAC, in `div.relative` o righe `flex`, e i 2 `TxForm` — non
  cambiano layout), solo quando la **parte decimale** supera il budget: `data-testid="<testid>-digits-error"`,
  `data-max=<maxFractionDigits>`, `text-xs text-lf-danger`; il bordo c'è già (`aria-invalid:border-lf-danger`). Le cifre
  significative e la parte intera restano come oggi: segnate, e rifiutate alla conferma col messaggio del backend. Via il
  `maxlength`. Chiave nuova e generica `common.decimalPlacesExceeded` in `base` (4 lingue, la frase di
  `transactions.errors.decimalPlacesExceeded`, che è un prefisso dinamico protetto: doppione accettato come `assets.types.OTHER` e
  `common.other`), con `./dev.py i18n add`.
- **Form**: `maxFractionDigits={10}` sui 3 input della quantità.
- **Bulk**: `absDecimal` per stringa in `txPayloadHelpers.ts`, e `exactDecimalSign` per il segno, in `fieldsFromTx`.
- **Evento al volo**: niente `parseFloat`/`toFixed` per mostrare il valore: la stringa normalizzata, con almeno 2 decimali aggiunti
  come zeri; oltre 6 decimali il messaggio e niente invio; il suggerito com'è.
- **Il rifiuto dell'evento** (punto 6 in più): `EVENT_TOO_MANY_DIGITS` di C-97a non è tradotto (`eventSaveError.ts` non lo conosce,
  nessuna chiave): un messaggio col massimo e gli eventi, come gli altri codici del file.
- **Editor dei prezzi**: `step?: number | 'any'` in `ui/data-editor/DataEditorTypes.ts` (mio dall'inizio) e `step: 'any'` sulle 5
  colonne di `AssetDataEditorSection`.

**I rossi** (test-author `d227471f`, 16/10 sera): Vitest diretto sui 6 file, **21 falliti, 339 passati**, tutti per il motivo
atteso. Il punto 5 (lo `step` dell'editor dei prezzi) è **caduto**: le celle dell'editor sono campi di testo o
`ErasableNumberCell`, e `ColumnDef.step` è solo il passo delle frecce, la premessa era sbagliata. Il punto 3 è una guardia:
`applySign(value, 'positive')` fa già il valore assoluto per stringa. Aggiunto il punto 6 (la traduzione di
`EVENT_TOO_MANY_DIGITS`). File dei rossi: `ExactDecimalInput.test.ts`, `ExactQuantityInput.test.ts`, `TransactionFormModal.test.ts`,
`txPayloadHelpers.test.ts`, `eventSaveError.test.ts`, il nuovo `EventCreateMiniModal.test.ts` (registrato in `front_component_unit`
di `_frontend_utility.py`).

**⏸️ In pausa** (coordinatore, 17/10 00:0x): prima W-B58 e W-B59 della revisione R13-SEC2 di E (sezione qui sotto). La cura di
C-97b non è applicata; i rossi restano nel worktree, fuori dai checkpoint di W-B58/W-B59. Da ricordare alla ripresa: il rifiuto
dell'evento porterà anche `max_integer_digits` (W-B58), e la frase di `events.saveError.tooManyDigits` deve poterlo dire.

### W-B58 e W-B59 — la revisione R13-SEC2 di E: ✅ handoff FROZEN (2026-10-17)

**Fonte**: piano 08 di E, «R13-SEC2» (in dev da `6cadaf427`): reperto 1 (MEDIUM 8/10) e note 1, 2, 4, 5 → **W-B58**; nota 12
(disponibilità 9/10, provata) → **W-B59**. Priorità del coordinatore (17/10, 00:0x): prima di C-97b, da chiudere prima del rilascio;
rossi prima; `price_query.py` è di X: lo scrivo io, X lo rivede al checkpoint; niente riga 🔒 nel CHANGELOG (C-97a non è uscita).
HEAD `11baeab0f` (in dev); i file toccati sono identici fra HEAD e la punta di dev (`git diff HEAD dev_release2` vuoto su di loro).

**Stato reale verificato (W-B58)**:
- **Lettura** — `db/real_decimal.py:53-62`: un REAL ±inf solleva `TypeError` (l'esponente `'F'` confrontato con un intero); da
  1e54 in su `InvalidOperation` (il riempimento a 6 decimali in un contesto di 60 cifre). Le colonne `RealDecimal`: quantità
  `(22, 10)`, costo per unità `(24, 12)`, i cinque prezzi `(24, 12)`. `services/assets/crud.py:283-287` legge le quantità di
  tutti: una riga così dà 500 a ogni utente su `/assets/all` e `/assets/query`, e non si cancella dall'API (la cancellazione la
  carica).
- **Limite** — `db/precision.py:157-172`: `normalize(_WIDE_CONTEXT)` va in `decimal.Overflow` per `1E+1000000` (500), porta
  `1E-2000000` a 0 (passa), e nessuno limita la grandezza (`1E+60`: 1 cifra, 0 decimali, passa). `truncate_to_db_precision`
  (`:130`) va in `InvalidOperation` da `1E+48` (12 decimali in 60 cifre).
- **Scrittori**:
  - transazioni: `transaction_batch_stages.py:106-134` controlla creates e updates; la promozione scrive
    `resolved_fields.cost_basis_override` senza controllo (`batch_creates.py:255-299`: il REAL arrotonda, nessun limite);
  - prezzi manuali: `price_store.py:30-46` controlla open/high/low/close (decimali, cifre) prima di scrivere, **non** il volume né
    la grandezza;
  - prezzi dei provider: `price_store.py:165-255` tronca e scrive a blocchi di 1 000 date, ognuno col suo commit: un
    `InvalidOperation` nel blocco 2 lascia scritto il blocco 1;
  - prezzo corrente: `price_query.py:858-904` (di X) scrive `Decimal(str(item.value))` senza `truncate_priceHistory` né limite;
  - eventi manuali: `event_store.py:331-356` controlla decimali e cifre, non la grandezza; eventi dei provider
    (`_upsert_asset_events`, da `refresh.py:580`): nessun controllo.
- Le colonne `Numeric` (importo, valore dell'evento, volume, cambio) si leggono col `'%.Nf'` di SQLAlchemy: un inf diventa
  `Decimal('Infinity')` senza eccezione, e rompe dopo, nelle risposte.

**Disegno della cura (W-B58)**:
1. **La lettura non solleva mai** (`RealDecimal.process_result_value`): un double finito torna come il suo decimale esatto, con
   un contesto largo quanto il valore (niente tetto a 60 cifre); un double non finito (±inf; un NaN SQLite lo salva come NULL)
   torna `None`, con un avviso nel log una volta per processo. La riga si carica, l'elenco funziona, la riga si cancella. Un
   valore finito oltre le cifre intere della colonna **resta com'è**: una DB della 1.2 può avere una quantità oltre 12 cifre intere,
   mai controllata, e leggerla come `None` cancellerebbe una posizione.
2. **La scrittura**: `RealDecimal.process_bind_param` (nuovo) rifiuta con `ValueError` un valore che come double diventa ±inf:
   rete di sicurezza, chiunque scriva.
3. **Il limite** (`decimal_limit_issue`): calcolato dalle cifre, senza contesto (niente overflow, underflow né arrotondamento):
   decimali → cifre significative → **cifre intere ≤ precisione − scala** (codice nuovo `integerDigitsExceeded`, `{max}`); un
   valore non finito → `integerDigitsExceeded`. L'ordine tiene i risultati di C-97a (una quantità di 16 cifre dice ancora «cifre
   significative»). Due aiuti nuovi: `integer_digits_issue` (solo la grandezza, per il volume) e `storable_value` (un valore di
   provider troncato alla colonna, o `None` se nessun troncamento lo fa entrare).
4. **Transazioni**: il codice nuovo arriva da `decimal_limit_issue` (testo «digits before the decimal point»);
   `TXValidationCode.INTEGER_DIGITS_EXCEEDED`; e la **promozione**: `resolved_fields.cost_basis_override` controllato sulla colonna
   `cost_basis_override` (issue `operation="promote"`, campo `cost_basis_override`). Frontend: `FIELD_PREFIXED_CODES` e la chiave
   `transactions.errors.integerDigitsExceeded` (4 lingue, `dev.py i18n add`).
   **Il batch si ferma** (aggiunto 00:3x, dopo aver letto `execute_batch`): `check_decimal_limits` aggiunge l'issue ma il batch va
   avanti per tutti gli stadi (C-97a: «la riga resta nel batch»), che calcolano coi valori — prodotti, medie, il double del REAL. Un
   valore di un milione di cifre li manda in `Overflow` (500), e uno di 400 cifre tutte diverse prende per primo
   `significantDigitsExceeded`, va avanti, diventa inf al flush e torna come testo grezzo «Balance validation error». Quindi
   `check_decimal_limits` risponde se un valore supera le cifre intere della colonna, **qualunque codice abbia preso**, e
   `execute_batch` si ferma dopo il controllo degli accessi (lo stesso ritorno anticipato dell'accesso negato: `committed=False`,
   le issue, `results` vuoto). Gli altri codici di C-97a lasciano la riga nel batch come prima. Tre rossi in più chiesti al
   test-author: quantità `1E+1000000`, quantità di 400 cifre, importo `-1E+1000000`.
5. **Prezzi manuali**: `_reject_prices_over_the_limit` rifiuta anche le cifre intere, e un volume non finito o oltre 24 cifre intere
   (un volume con decimali resta accettato: è un conteggio, letto arrotondato come prima); il messaggio dice anche il limite
   intero. Prima di scrivere qualsiasi cosa.
6. **Prezzi dei provider** (`bulk_upsert_prices` non MANUAL): **prima dei blocchi**, una data con un valore non memorizzabile
   (un prezzo non finito o oltre 12 cifre intere, un volume oltre 24, una chiusura che il troncamento porta a 0) è scartata e
   riportata come un OHLC impossibile (`rejected …`), con un avviso; le altre si scrivono. Niente eccezione a metà. Un punto si
   scrive intero o si scarta (un volume sbagliato scarta la data: un dato del provider così non è affidabile). La regola dello zero
   vale solo per la chiusura (un minimo di `1E-13` diventa 0, ammesso). E i valori **già salvati** che la fusione F.4 riprende
   (open, high, low, volume di una riga esistente): uno scritto da una versione vecchia oltre le cifre della colonna (la 1.2
   salvava il prezzo corrente com'era) faceva sollevare il troncamento a metà dei blocchi → scritto come NULL (`_kept_price`,
   `_kept_volume`).
7. **Prezzo corrente** (`price_query.py`, di X): attraverso `storable_value` (`truncate_priceHistory` più i limiti); non
   memorizzabile → non salvato, con un avviso; valido → troncato come lo storico.
8. **Eventi**: i manuali (`_reject_too_many_digits`) rifiutano anche le cifre intere (`EVENT_TOO_MANY_DIGITS`, parametro in più
   `max_integer_digits`); quelli dei provider (`_upsert_asset_events`): un evento non memorizzabile è scartato, con un avviso,
   prima di scrivere.
9. **Non tocco**: `truncate_to_db_precision` (ogni chiamante ora controlla la grandezza prima, tranne il cambio, di X); `crud.py`
   (la lettura basta: `position_quantities` salta una quantità `None`).

**Fuori dal lotto** (al backlog, approvato dal coordinatore 00:5x): la nota 3 (il testo grezzo «Balance validation error»: con
l'arresto del batch non è più raggiungibile da un valore troppo grande, nessuna voce); **W-B60** (il rumore del double negli importi,
sopra); **W-B61** i cambi, manuali (`api/v1/fx/currencies.py:92` → `fx/storage.py:60`: nessun limite, `1E+400` salvato come inf e
il suo inverso `1E-400` come 0) e dei provider (`truncate_fx_rate` solleva da `1E+50`), di X — il coordinatore avvisa X; **W-B62**
la nota 6 (`/prices/current` scrive per intero un `1E+50000000` del provider nella **risposta**, `schemas/common.py:47`: la cura non
lo salva più, ma lo risponde); **W-B63** un inf **già salvato** in una colonna `Numeric` (importo, valore di evento, volume, cambio)
si rilegge `Decimal('Infinity')` e rompe le risposte: per importo e valore dell'evento lo chiude W-B60 (`RealDecimal` lo legge
`None`), volume e cambio restano.

**Prova a secco della cura** (00:41, carico 50): `files/scripts/wb58_wb59_cure.py` (sostituzioni esatte, 11 file) applicato a una
copia del backend in `/tmp/libreFolio_wb58_sim` (non nel worktree), con uno script di controllo degli aiuti: `1E+60`,
`1000000000000`, `-1E+13` (importo), `1E+48` (chiusura), `1E+1000000`, ±Infinity e NaN → `integerDigitsExceeded` (12; volume
`1E+25` → 24); `1234567890123.456` e 400 cifre → `significantDigitsExceeded` per primo, ma `integer_digits_issue` li segna (il
batch si ferma); `1E-2000000` e `1E-13` (chiusura) → `decimalPlacesExceeded`; `999999999999`, `1.50000000000000`, `-1`, `0` →
nessun limite. `storable_value`: `1E+400` → None, `123.4567890123456` → `123.456789012345`; `storable_price`: chiusura `1E-13` →
None, minimo `1E-13` → `0E-12`, `65432.1234567890999` → `65432.1234567890`. Lettura: ±inf e `'abc'` → None (un avviso), 1e54,
1e60, 1.79e308 → il decimale esatto, 10 → `10.000000`; scrittura di `1E+400` → `ValueError`, `1.5` e None passano.

**Domanda per il developer (D-W58-1)**: 12 cifre intere per quantità e importo (precisione − scala, la direzione di E)
rifiutano una quantità da 1 000 000 000 000 in su (meme coin: mille miliardi di PEPE ≈ 10 M$) e un importo da mille miliardi in
su (IDR, VND, IRR). **Predefinito**: 12, come dichiarato dalle colonne. Alternativa: la quantità a 15 (il limite delle cifre
significative). Lavoro col predefinito.

**Deciso — N63** (coordinatore, decisione notturna del 17/10, 00:5x; il developer la rivede al mattino): **15 cifre intere per
quantità e importo**, non 12. Ragioni: mille miliardi di VND ≈ 40 k$, di IDR ≈ 60 k$, importi realistici; la 1.2 non ha mai fatto
rispettare `Numeric(18,6)` su SQLite, quindi dati oltre 12 cifre intere possono già esistere e diventerebbero immodificabili; il
DoS si chiude con qualunque limite lontano da 1e54; 15 come le cifre significative di C-97a. Le altre colonne restano come
dichiarate: costo per unità (un prezzo, D5) 12, i cinque prezzi 12, il valore dell'evento (per unità) 12, il volume 24. Nella
cura: `max_integer_digits(model, column)` in `db/precision.py` (15 per `transactions.quantity` e `transactions.amount`, altrimenti
precisione − scala), letto da `decimal_limit_issue`, `integer_digits_issue` e dai messaggi dei prezzi e degli eventi. Il
test-author aggiornato (stessi rossi, i massimi nuovi). Prova a secco rifatta sulla copia: quantità `1E+15` e importo `-1E+15` →
15; `999999999999999` e importo `-1E+13` → nessun limite; costo `1E+13`, chiusura `1E+13`, valore evento `1E+13` → 12; volume
`1E+25` → 24; `1234567890123.456` → solo `significantDigitsExceeded` (13 cifre intere, entro 15: il batch non si ferma).

**Un limite di N63 da sapere (pre-esistente, non della cura)**: l'importo (e il valore dell'evento) è `Numeric(18, 6)`, che
SQLAlchemy rilegge col formato `'%.6f'`: da 11 cifre intere il rumore del double compare nei decimali —
`123456789012.345` torna `123456789012.345001` già oggi, e con 15 cifre intere `99999999999999.9` torna `99999999999999.906250`.
Gli importi interi (VND, IDR) tornano esatti. Cura proposta: `RealDecimal(18, 6)` (stesso DDL, nessuna migrazione), dopo aver
controllato le `SUM` in SQL su quelle colonne → **W-B60**, fuori da questo lotto.

**Stato reale verificato (W-B59)**: `services/brim/brim_parse_pool.py:86-88` imposta il precaricamento in `_get_pool()` qualunque
sia il prewarm. Su 3.13 il primo `run_in_executor` aspetta sul thread del loop il pid del worker, che il forkserver manda solo dopo
il precaricamento: il loop resta fermo per tutto l'import di BRIM e dei 33 plugin (~4 s a riposo, 30–50 s sotto carico; la prova
di E: stallo massimo 3,14 s col precaricamento, 0,18 s senza). Contro N56 («il default lascia invariato il self-hosted»). La
docstring di `config/brim.py` («the first parse starts the forkserver, which loads the plugins») e la doc
(`developer/backend/brim/architecture.md`, «Preload and warm-up») descrivono proprio questo.

**Disegno della cura (W-B59)**: `_get_pool()` imposta il precaricamento solo se `brim_prewarm_enabled()` (un `BrimConfigError`
vale spento). Spento: il forkserver pigro parte senza precaricamento e ogni worker importa BRIM da sé al primo parse, fuori dal
loop, come prima di W-B53. In modalità di test (prewarm acceso) non cambia nulla. Doc: le due docstring e la sezione della doc;
`.env.example` resta.

**Prove**:
- rossi (test-author): `utils real-decimal` (lettura di ±inf, 1e54, 1e60, 1.79e308 senza eccezione; la scrittura di un inf
  rifiutata; `decimal_limit_issue` con `1E+60`, 13 cifre intere, `1E+1000000`, `1E-2000000`, ±Infinity, e le guardie
  dell'ordine; `storable_value`); `services transaction-decimal-places` (BUY `1E+60` su un broker con scoperto e short, importo e
  costo oltre 12 cifre intere, la promozione, la lista degli asset con una riga REAL 1e60 e una inf); `services
  asset-digit-limits` (prezzi manuali e volume, provider a blocchi, prezzo corrente, eventi manuali e dei provider);
  `services brim-parse-pool` (worker senza precaricamento col prewarm spento; il test esistente esplicito col prewarm acceso);
  Vitest `resolveValidationMessage.decimals.test.ts`;
- dopo la cura: gli stessi più `db numeric-truncation`, `utils decimal-precision`, `services config-brim`, `api
  transactions-validate`, `api assets-events`, `front-transaction tx-unit`, `i18n check`, `lint`, `api sync`, `front check`; le prove
  API nello slot del coordinatore.

**Passo 1 — i rossi ✅ (01:0x)**, test-author `0746298a`, nessun codice di produzione toccato, nessun file nuovo (nessuna voce del
runner). Prove nella corsia, una alla volta, carico < 50:

| Azione | Rossi prima della cura |
|---|---|
| `utils real-decimal` | 94 falliti / 113 passati |
| `services transaction-decimal-places` | 33 / 88 (due giri) |
| `services asset-digit-limits` | 36 / 40 |
| `services brim-parse-pool` | 2 / 17 |
| Vitest `resolveValidationMessage.decimals.test.ts` | 11 / 21 |

Ogni rosso per l'assenza del contratto (asserzione o `pytest.fail` che nomina l'eccezione), nessun errore di raccolta né di
fixture. > **Note implementazione**: due scoperte del test-author, che correggono la mia analisi: la BUY di 400 cifre oggi non dà
il testo grezzo «Balance validation error» ma un **500** (`TypeError` in `validate_cost_basis`, che rilegge la riga inf); e le create
di `1E+60` (quantità o costo) sollevano `InvalidOperation` nello stesso punto. L'arresto del batch le chiude tutte. Il contratto
dell'arresto (`check_decimal_limits` → bool) e N63 (15 cifre intere per quantità e importo) sono arrivati al test-author durante la
scrittura (`write_agent`). Casi derivati marcati `derived-` (`sNaN`, `FxRate.rate` → 14, un evento di provider `1E+13`).
> **⚠️ Fuori pista**: `_assert_names_the_refusal` (helper condiviso di `test_asset_digit_limits.py`) ha un parametro `extra_limits`
(il 24 del volume) e toglie la notazione scientifica; `_run_as_the_endpoint` accetta `deletes` e `promotes`.

**Passo 2 — la cura ✅ (01:1x)**: `files/scripts/wb58_wb59_cure.py --apply` (11 file: `db/real_decimal.py`, `db/precision.py`,
`schemas/transactions/batch.py`, `transactions/transaction_batch_stages.py`, `transactions/transaction_service.py`,
`assets/price_store.py`, `assets/price_query.py`, `assets/event_store.py`, `brim/brim_parse_pool.py`, `config/brim.py`,
`frontend/…/resolveValidationMessage.ts`); chiave `transactions.errors.integerDigitsExceeded` con `dev.py i18n add` (4 lingue, nel
sottosistema `transactions`). > **Note implementazione**: `process_bind_param` e la lettura passano da `_as_double` (un `sNaN` o un
testo → NaN, mai un'eccezione: il messaggio dice sempre «finite»). Ruff B009 su `getattr(price, "volume")` → gli aiuti di
`price_store` tipizzati `FAPricePoint`, accesso diretto (a mano dopo lo script). `truncate_to_db_precision` non cambia: ogni
chiamante passa ora da un controllo della grandezza (`storable_value`, i rifiuti manuali), e i valori già salvati che la fusione
F.4 riprende passano da `_kept_price`/`_kept_volume`.

**Passo 3 — le prove leggere ✅ (01:1x–01:2x, carico 43–48)**: i cinque rossi verdi — `utils real-decimal` **207**, `services
transaction-decimal-places` **121**, `services asset-digit-limits` **76**, `services brim-parse-pool` **19**, Vitest dei due file del
risolutore **85**. I vicini (`/tmp/libreFolio_wb58_neighbours.sh`): `utils decimal-precision` 21, `db numeric-truncation` 4, `db
validate` 17, `services config-brim` 51, `services app-lifecycle` 51, `services current-price-bootstrap` 8, `services
transaction-cost-basis-rule` 80, `services asset-source` 61, `utils provider-core-cache` 46: tutti verdi. `ruff` e `black` puliti
sui 14 file toccati, `prettier` pulito, `dev.py i18n check` stretto (4 912 chiavi). > **⚠️ Fuori pista**: la prima prova (`utils
real-decimal`, 1,2 s) è partita col carico a 88, contro la regola del carico; dalle successive lo script aspetta < 50.
L'E2E `tx-fx-completeness.spec.ts:249` (importo di 12 cifre intere e 18 significative) legge solo il payload e resta fuori
dall'arresto (12 ≤ 15).

**Passo 4 — le prove senza porta e la doc ✅ (01:2x–01:5x)**: `external brim-providers` **736** passati, 1 saltato (carico 39);
`front check` **0 errori, 0 avvisi** (carico 40). Regola aggiornata in `.github/instructions/backend-db.instructions.md` (la lettura
che non solleva, la terza soglia con `max_integer_digits` e N63, `storable_value`/`storable_price`). Doc per sviluppatori dal
docs-writer `04364ca8` (sei pagine: `architecture/database/index.md` — una colonna «Digits before the point» nella tabella —,
`backend/transactions/service.md`, `backend/assets/architecture.md`, `backend/assets/events.md`,
`architecture/database/assets_pricing.md`, `backend/brim/architecture.md` «Preload and warm-up»), `mkdocs build` stretto e
`check-links` verdi; un secondo giro per i passi fuori sezione che ha segnalato (la riga Parse di «Concurrency & off-loading», ora
falsa col prewarm spento; l'arresto anticipato fra i confini degli errori; `brim_plugin_guide.md`; `brokers_transactions.md`).
> **⚠️ Fuori pista** (dal docs-writer, corregge il punto 9 del disegno): non **ogni** chiamante di `truncate_to_db_precision`
controlla la grandezza prima. `refresh.py:423` (`_count_actual_price_changes`, di X) tronca la chiusura del provider senza
controllo: un `1E+60` vi solleva `InvalidOperation`, che il suo `try/except` raccoglie (ripiego: tutte le date contate come
nuove, nessun 500); e le date poi scartate per grandezza restano nei conteggi `inserted`/`updated`/`changed_points`, come già
quelle con un OHLC impossibile. Gli eventi dei provider scartati sono solo nel log, non nel risultato della sincronizzazione.
Cosmetico (conteggi), nessuna voce nuova; lo dice la doc. La pagina utente `user/transactions/import/how-to.en.md` (~284) nomina solo i
decimali: lasciata così (un caso limite, il messaggio si spiega da sé, e cambiarla aprirebbe un debito di traduzione).

**Passo 5 — lo slot 2 ✅ (01:31–01:50)**, `files/scripts/wb58_slot.sh` (cancello a 70): `db populate --force` ok, `api
transactions-validate` **12**, `api batch-split-promote` **36**, `api assets-events` **45**, `api brim` **118**, `api
prices-currency-coherence` **5**, `api prices-sync-delta` **5**: tutto verde; porta 6184 libera (lsof: 0 in ascolto, 01:50).
In `api brim` il server di prova ha il prewarm acceso (modalità di test): il percorso caldo di W-B53 non cambia.

**Passo 6 — il secondo giro della doc e la simulazione ✅ (01:5x)**: il docs-writer ha corretto la riga Parse di «Concurrency &
off-loading» (falsa col prewarm spento), l'arresto anticipato fra i confini degli errori di `service.md`, la riga di `price_store.py`,
`brim_plugin_guide.md` (la terza soglia) e `brokers_transactions.md` (15, 15, 12 cifre intere); build stretta (carico 36) e
`check-links` (97 link) verdi. > **⚠️ Fuori pista**: provando il codice su SQLite in memoria ha trovato che `round_computed_value`
limita le cifre significative solo su una colonna `RealDecimal`: su un importo (`Numeric(18, 6)`) `1234567890.1234567` diventa
`1234567890.123457`, ancora 16 cifre significative → la docstring (già di C-97a: «always passes») corretta a mano in
`db/precision.py`, solo testo. Il `git fetch` che avevo messo in una riga di controllo l'ho fermato subito: nessun ref cambiato
(`FETCH_HEAD` del 16/10), e non lo rifaccio (git in sola lettura). Simulazione (`sim_cherry_pick.sh dev_release2 --docs`, 31 file
compresi piano e backlog) su dev **`3a5ff5194`** (dopo la fine del blocco dei segnali di J, `b36e3873f`): **0 conflitti**,
`price_query.py` fuso con l'import da `services/signals/`; ruff e black puliti sui `.py` fusi; `mkdocs build` stretto e `check-links`
verdi sull'albero simulato (carico 48). `git diff --check` pulito; porta 6184 libera.

**Handoff FROZEN (02:0x)** — tre commit proposti:
1. `fix(decimals): bound size, reads never raise` (W-B58, 26 file): `.github/instructions/backend-db.instructions.md`,
   `backend/app/db/{precision,real_decimal}.py`, `backend/app/schemas/transactions/batch.py`,
   `backend/app/services/assets/{event_store,price_query,price_store}.py`,
   `backend/app/services/transactions/{transaction_batch_stages,transaction_service}.py`,
   `backend/test_scripts/test_services/{test_asset_digit_limits,test_transaction_decimal_places}.py`,
   `backend/test_scripts/test_utilities/test_real_decimal.py`, `frontend/src/lib/features/transactions/resolveValidationMessage{,.decimals.test}.ts`,
   `frontend/src/lib/i18n/transactions/{en,it,fr,es}.json`, `mkdocs_src/docs/developer/architecture/database/{index,assets_pricing,brokers_transactions}.md`,
   `mkdocs_src/docs/developer/architecture/patterns/brim_plugin_guide.md`, `mkdocs_src/docs/developer/backend/assets/{architecture,events}.md`,
   `mkdocs_src/docs/developer/backend/transactions/service.md`;
2. `fix(brim): preload parse pool only on prewarm` (W-B59, 4 file): `backend/app/services/brim/brim_parse_pool.py`,
   `backend/app/config/brim.py`, `backend/test_scripts/test_services/test_brim_parse_pool.py`,
   `mkdocs_src/docs/developer/backend/brim/architecture.md`;
3. `docs(journal): W-B58, W-B59, N63` (2 file): questo piano e `BACKLOG_POST_1.2.md`.
**Fuori dal checkpoint** (C-97b, in pausa): `ExactDecimalInput.test.ts`, `ExactQuantityInput.test.ts`, `TransactionFormModal.test.ts`,
`txPayloadHelpers.test.ts`, `eventSaveError.test.ts`, il nuovo `EventCreateMiniModal.test.ts`, `scripts/test_runner/_frontend_utility.py`.
X rivede `price_query.py` (e, se vuole, `price_store.py` ed `event_store.py`, che toccano i suoi prezzi ed eventi). Nessuna riga 🔒 nel
CHANGELOG (C-97a e W-B53 non sono usciti). Dopo l'ingresso: C-97b riprende (la cura, poi la frase di `tooManyDigits` col
`max_integer_digits`).

### C-97b — i decimali in input: la cura ✅, handoff FROZEN, E2E ✅ (2026-10-17)

**Ripresa** (coordinatore, 02:0x): W-B58/W-B59 committati (`7a4fdf024`, `e69544f79`, journal `94fbd54fd`) ed entrati in dev
(`4e9d1815f`, revisione di X ok; le sue 2 note su `price_query.py` vanno a X come X-R40). HEAD `94fbd54fd` verificato; nel
worktree solo i file di C-97b. W-B57 (TC-17 dei colori) aggiunta alla mia sezione del backlog: entra con C-97b.

**Passo 1 — la cura ✅ (02:1x)**: `files/scripts/c97b_cure.py --apply` (6 file), poi `prettier` (nessuna modifica):
- `components/ui/input/ExactDecimalInput.svelte`: `fractionOverflow` (la parte decimale oltre `maxFractionDigits`, sul valore
  normalizzato) e, dopo l'`<input>`, `<p class="mt-1 text-xs text-lf-danger" data-testid="<testid>-digits-error"
  data-max=…>` con `common.decimalPlacesExceeded`; via `maxLength` e `maxlength`. Il bordo c'era (`aria-invalid:border-lf-danger`).
- `form/TxFormSingleSection.svelte` (×2) e `form/TxFormPairSection.svelte`: `maxFractionDigits` 6 → **10**.
- `bulk/TransactionBulkModal.svelte`: `quantityText()` (le cifre come scritte, senza zeri finali, mai notazione esponenziale, mai
  tagliate: `formatDecimalForDisplay` con `maxFrac` lungo quanto il valore) con `applySign(…, 'positive')` ed `exactDecimalSign` al
  posto di `String(Math.abs(Number(x)))` in `fieldsFromTx` e in `txCreateItemToPendingOp` (la stessa riga, due volte: un satoshi
  importato da BRIM diventava `1e-8` anche nel payload, che il backend rifiuta), e nella cella della quantità (vista doppia e
  singola), ora con `escapeHtml` (prima un valore non numerico entrava nell'HTML così com'era). La cassa resta col `Number`: un
  importo ha al più 6 decimali e 15 cifre, esatto in un double, e cambiarla toccherebbe la forma mostrata in edit (`100.1`).
- `events/EventCreateMiniModal.svelte`: `plainAmount` (decimale semplice senza segno, dopo `normalizeDecimalInput`),
  `withTwoDecimals` (almeno 2, quelli scritti tenuti), `amountDecimals` (gli zeri finali non contano, come nel backend),
  `EVENT_VALUE_DECIMALS = 6`; al blur niente `parseFloat`/`toFixed`; oltre 6 il messaggio
  (`event-create-amount-digits-error`, `data-max="6"`), `aria-invalid` sul campo e «Crea» disabilitato; il suggerito intero
  (`0.2345` resta); l'importo inviato come stringa (lo schema accetta `number | string`). Il toast resta a 2 decimali (C-97c).
- `events/eventSaveError.ts`: ramo `EVENT_TOO_MANY_DIGITS` → `events.saveError.tooManyDigits` con `date`, `type`, `more`, `max`
  (`max_decimal_places`), `significant`, `integer` (`max_integer_digits` di W-B58).
- i18n con `dev.py i18n add`: `common.decimalPlacesExceeded` in `base` (EN «At most {max} decimal places», la frase di
  `transactions.errors.decimalPlacesExceeded`, prefisso dinamico protetto: doppione accettato) ed `events.saveError.tooManyDigits`
  nel sottosistema `assets` (4 lingue, nello stile di `inUse`; il FR col ramo `many`). `i18n check` stretto: 4 914 chiavi.
> **Note implementazione**: lasciati `maxIntegerDigits={12}` sulle tre quantità del Form: con N63 il backend ne accetta 15, ma la
guardia del test-author (`1000000000000.1` invalido nel Form) e N63 da rivedere al mattino dicono di non muoverli qui → **W-B64**.

**Passo 2 — i rossi verdi ✅ (02:2x–02:4x)**: primo giro (carico 39) sui 6 file: **347 passati, 13 falliti**, tutti
`[svelte-i18n] Cannot format a message without first setting the initial locale` in `ExactDecimalInput.test.ts` ed
`ExactQuantityInput.test.ts`, che non inizializzano i18n (il messaggio ora è tradotto): i rossi di C-97b e due test vecchi che
digitano un overflow. > **⚠️ Fuori pista**: riparazione del test-author `d227471f` (`setupI18n` in un `beforeAll` a livello di
modulo, nei due file; nessuna asserzione cambiata) → i 6 file **360/360** (carico 33). Poi `front-transaction tx-unit` **914**
passati (23 file). > **⚠️ Fuori pista**: `front-utility component-unit` fermato prima di partire: era ancora nel cancello del carico
quando il coordinatore ha dichiarato il **blocco della galleria fino alle ~03:30** (carico 160–170: niente `api`, E2E,
`all-backend`, `--workers`; prove leggere solo a carico < 50); il mio ciclo d'attesa sarebbe partito comunque dopo 30 minuti, quindi
l'ho fermato e da qui il cancello non ricade mai in una prova.

**Passo 3 — la guardia E2E e la doc ✅ (02:2x–02:4x)**:
- **Guardia** (test-author `d227471f`), `tx-bulk-operations.spec.ts`, blocco «commit on owned rows»: «C-97b: an untouched
  one-satoshi SELL opens as original, shows 0.00000001, and closing writes nothing». Seme proprio su Interactive Brokers, marcato
  `E2E-satoshi-sell-<suffisso>`: deposito `0.02` USD, BUY `0.00000002` BTC (`BTC-USD`, letto solo) per `-0.02`, SELL `-0.00000001`
  per `0.01` (300–302 giorni fa; pulizia nell'`afterEach` del blocco). Asserisce `data-status="original"`, la cella `0.00000001`, la
  chiusura senza «scarta» e la riga riletta per id ancora `-0.00000001` con lo stesso `updated_at`. Verde per costruzione (la
  cura c'è già): nessun rosso possibile, lo dico nell'handoff. Tipi: `tsc -p tsconfig.e2e.json` pulito sullo spec (4 errori
  vecchi altrove: `e2e/fixtures/sync-overwrite.ts:89,125`, `e2e/onboarding-tour.spec.ts:863`, `src/lib/types/files.ts` senza
  l'alias `$lib`). > **⚠️ Fuori pista**: il test-author chiude il Form con «Annulla», non «Applica»: «Applica» senza modifiche su
  una SELL riprende i campi col segno (cella `-0.00000001`, chiusura che chiede di scartare), precedente a C-97b → **W-B65**. Il
  seme era 1 BTC intero: ridotto a un satoshi e pochi centesimi, perché il valore del portafoglio dell'utente E2E non si muova
  sotto i vicini.
- **Doc** (docs-writer `421124da`): `core-ui/atoms.md` (#exactdecimalinput: il messaggio, niente `maxlength`, il valore com'è;
  #exactquantityinput: il testid passato, 12 + 10 nel Form), `features/transaction-form.md` (la riga `quantity` a 10, il punto
  **Quantity**, una frase sull'importo di «+ New event» e su `events.saveError.tooManyDigits`); build stretta e `check-links`
  verdi. Il Bulk non è descritto da nessuna pagina: niente. > **⚠️ Fuori pista**: dalle sue verifiche sul codice — i campi
  priorità del PAC (`maxFractionDigits={0}`) avrebbero detto «At most 0 decimal places» → `common.decimalPlacesExceeded` ora è un
  plurale ICU (`=0` «Whole numbers only», `one` «At most 1 decimal place», il FR col ramo `many`; `dev.py i18n update`), non più
  un doppione di `transactions.errors.decimalPlacesExceeded`; `ExactDecimalInput` conta gli zeri finali (il backend no) → in
  **W-B64**; le frecce e il toast della mini-modale passano ancora dal `Number` (le frecce esatte per costruzione: `toFixed` sui
  decimali del passo; il toast a 2 decimali è di C-97c). Secondo giro chiesto: `data-editor.md` (il codice nuovo nell'elenco di
  `eventSaveErrorMessage()`) e la frase sul plurale in `atoms.md`.

**Passo 4 — le prove leggere ✅ (02:36–03:1x)** (`files/scripts/c97b_light.sh`, cancello < 50 che salta e non forza): i 6 file
più `catalogIcuLocale.test.ts` **377 passati** (carico 39), `front check` **0/0** (46), `utils gate-i18n-catalog` passato (42),
`utils gate-i18n-usage` **195** (36), `front-utility core-unit` **7 294** (46), `front-utility component-unit` **4 169 passati,
99 saltati**, uscita 1. > **⚠️ Fuori pista**: i 99 saltati sono 3 file di `features/backup` (`RestartOverlay`, `RestoreCard`,
`RestoreReportModal`): «Hook timed out in 60000ms» nel caricamento del componente, sotto il carico del blocco della galleria;
rilanciati da soli (carico 47) → **99/99** passati. Verdetto: lentezza, area non toccata. Il secondo giro della doc (docs-writer
`421124da`): `core-ui/data-editor.md` (`EVENT_TOO_MANY_DIGITS` nell'elenco di `eventSaveErrorMessage()`) e `atoms.md` (il testo
segue il budget: «Whole numbers only» a 0); build stretta e `check-links` verdi. Doc utente: nessuna pagina dice 6 decimali per la
quantità del Form (`user/transactions/import/how-to.en.md` ~284 dice già 10): niente.

**Passo 5 — la simulazione ✅ (03:0x)**: `sim_cherry_pick.sh dev_release2 --docs`, 27 file (codice, test, i18n, doc, runner,
journal) su dev **`2818924b7`**: **0 conflitti**, JSON validi, `mkdocs build` stretto e `check-links` verdi sull'albero simulato
(carico 42). `git diff --check` pulito.

**Handoff FROZEN (03:1x)**, chiesto dal coordinatore prima dello slot: lui committa, unisce dev, e lo slot prova la revisione
combinata. Due commit proposti: `feat(transactions): 10-decimal input, digit message` (codice, test, i18n, doc, runner: 25 file) e
`docs(journal): C-97b, W-B57, W-B64, W-B65` (piano e backlog). Slot di C-97b (~35 min) **dopo le 04:45** (nuovo blocco della
galleria 03:50–04:45, poi Y): prima, sulla HEAD nuova, `api sync` (il client generato è ignorato da git) e `front check` a carico
< 50; poi `files/scripts/c97b_slot.sh`. Riga del CHANGELOG da aggiungere alla voce C-97 (#43), all'ingresso, dal coordinatore.

**Prima dello slot ✅ (03:30–03:3x)**: C-97b committato (`24aa1d69b`, `527306638`), dev `2818924b7` unito → HEAD **`1f779d386`**;
sopra, `dev.py api sync` (carico 35, uscita 0; il client generato è ignorato da git: nessuna differenza tracciata) e `front check`
**0/0** (carico 40). E2E di R13-SEC5 (revisione di sicurezza di E su C-97b): niente sopra la soglia, e il lotto chiude un pozzo
`{@html}` nella cella del Bulk; tre note basse → **W-B66** (un `1e-8` incollato diventa `18`; un incolla enorme blocca la
scheda: `10n ** places` e una regex quadratica; il toast a 2 decimali, con C-97c).

**Passo 6 — gli E2E ✅ (slot 2, 04:48–05:13)**, `files/scripts/c97b_slot.sh` su HEAD **`1f779d386`** (la revisione combinata; nel
worktree solo i file di test di W-B60 e il journal, nessun file di `frontend/` né di `backend/app/`; `api sync` già fatto alle 03:30
sulla stessa HEAD): `db populate --force` ok, `tx-bulk-operations` **11** (la guardia del satoshi compresa), `tx-event-create-exists`
**8**, `tx-event-picker` **5**, `transactions-modals` **25**, `tx-commit-all-types` **19**, `tx-wac-bulk` **11**,
`tx-bulk-promote-cost-basis` **8**, `tx-bulk-import-handoff` **3** (partito a carico 41, finito a 158: verde lo stesso),
`tx-fx-completeness` **4**: **94 passati, 0 falliti**; porta 6184 libera dopo (lsof: 0 in ascolto). C-97b pronto per l'ingresso.

Lista originale dello slot: `db populate --force`, poi
`tx-bulk-operations` (con la guardia), `tx-event-create-exists`, `tx-event-picker`, `transactions-modals`, `tx-commit-all-types`,
`tx-wac-bulk`, `tx-bulk-promote-cost-basis`, `tx-bulk-import-handoff` (la conversione import → Bulk), `tx-fx-completeness`. Il PAC
non ha E2E che scrivano nei campi toccati (solo la fixture della galleria li nomina).
Restano, a carico < 50: `front check`, `front-utility component-unit` e `core-unit`, `utils gate-i18n-catalog` e
`gate-i18n-usage`; poi lo slot (dopo il blocco) per gli E2E: `tx-bulk-operations` (la guardia), `tx-event-create-exists`,
`tx-event-picker`, `transactions-modals`, `tx-commit-all-types`, `tx-wac-bulk`, `tx-bulk-promote-cost-basis`.

### W-B60 — importi e valori degli eventi senza il rumore del double: ✅ handoff FROZEN, `all-backend` dopo l'unione (2026-10-17)

**Ordine del coordinatore** (03:0x): C-97b committato (`24aa1d69b`, `527306638`), base aggiornata con dev `2818924b7` → HEAD
**`1f779d386`**, pulito. Nell'attesa dello slot di C-97b (dopo le 04:45): l'analisi di W-B60 e i rossi, **solo file di test**;
nessun codice di prodotto finché gli E2E di C-97b non sono verdi, perché lo slot provi esattamente questa revisione.

**Stato reale verificato** (HEAD `1f779d386`, sola lettura):
- `Transaction.amount` (`db/models.py:892`) e `AssetEvent.value` (`:1052`) sono `Numeric(18, 6)`: SQLAlchemy li rilegge col
  formato `'%.6f'` del double, quindi da ~11 cifre intere il rumore entra nei 6 decimali (`123456789012.345` →
  `123456789012.345001`, `12345678901.2345` → `12345678901.234501`; con le 15 cifre intere di N63, `99999999999999.9` →
  `99999999999999.906250`). Gli importi interi tornano esatti (un double è esatto fino a 2^53). Un REAL inf torna
  `Decimal('Infinity')` (W-B63), e niente impedisce di scriverlo (nessun `process_bind_param`).
- **SQL**: nessun aggregato su queste colonne (le `func.sum` del backend contano righe con `case`); l'unica espressione è il
  filtro `func.abs(Transaction.amount) >= …` di `transactions/queries.py:79-81`, che il tipo non tocca. Le somme sono già in
  Python (`native_balances`, `_LedgerAccumulator` di `ledger_totals.py`).
- **Arrotondamenti**: i plugin BRIM arrotondano solo il costo per unità (`credit_agricole:1078`, `intesa:372`), mai un importo;
  `truncate_to_db_precision`/`round_computed_value` su `amount` non hanno chiamanti nell'app. Da `RealDecimal` prenderebbero il
  taglio a 15 cifre significative (oggi il test `test_real_decimal.py:332` fissa il contrario: `1234567890123.456789`, «nessun
  taglio delle cifre significative» per un `Numeric`).
- **Totali del backup** (J-27/B-13): `compute_control_totals` legge dall'ORM, quindi i due lati seguono il tipo; un backup
  registrato **prima** e ripristinato **dopo** riporterebbe una differenza per un importo enorme con decimali (riportata, mai un
  rifiuto). I backup della 1.2 non hanno totali (J-27 è della 1.3): tocca solo i backup delle build di sviluppo. La docstring di
  `ledger_totals.py` (di J/MF) dice «amounts are Numeric(18, 6)» e il commento di `_EXACT` «Sums of Numeric(18, 6) amounts»:
  da allineare (solo testo).
- **Test che si adattano da soli**: `test_numeric_truncation.py` scopre le colonne e il loro `decorated` dal tipo
  (`numeric is not column.type`): con `RealDecimal` si aspetterà il taglio a 15 cifre. `db_schema_validate.py:10` lo dice in
  docstring.

**Disegno della cura** (dopo gli E2E di C-97b): `RealDecimal(18, 6)` per `Transaction.amount` e `AssetEvent.value` — stesso DDL,
**nessuna migrazione** (Alembic confronta l'`impl`: `NUMERIC(18, 6)` com'è); docstring di `models.py`; regola in
`.github/instructions/backend-db.instructions.md`; doc (`architecture/database/index.md` — tabella e «Read» —,
`brokers_transactions.md`, `backend/assets/events.md`); docstring di `ledger_totals.py` con l'ok di J/MF. Effetti: la lettura
esatta (15 cifre significative, sempre 6 decimali come oggi), un inf letto `None` e mai più scritto (la metà importo/evento di
W-B63), `truncate_to_db_precision`/`round_computed_value` su un importo con le 15 cifre. Costo: la lettura di un importo passa da
Python (repr + `Decimal`), come già la quantità: ~1–2 µs a riga.

**Prove** (rossi, test-author `0746298a`, che conosce i file di W-B58): `utils real-decimal` (il tipo delle due colonne; l'andata e
ritorno esatta di `123456789012.345`, `-99999999999999.9`, `12345678901.2345`; le guardie `-100` → `-100.000000`, `0.000001`,
`999999999999999`; un inf letto `None`; `1E+400` rifiutato in scrittura; il test di `:332` riscritto, 15 cifre ROUND_DOWN; un
`round_computed_value` su un importo a 15 cifre); `services transaction-decimal-places` (una BUY con importo `-123456789012.345`
riletta esatta dal servizio e nei totali di controllo della sua riga); `services asset-digit-limits` (un evento di valore
`12345678901.2345` riletto esatto). Dopo la cura: gli stessi, `db numeric-truncation`, `db validate`, `utils decimal-precision`,
le API delle transazioni e degli eventi nello slot.

**I rossi ✅ (03:1x–03:28, carico 38–42)**, test-author `0746298a`, solo file di test, nessun file nuovo:

| Azione | Rossi | Passati |
|---|---|---|
| `utils real-decimal` | 27 | 212 |
| `services transaction-decimal-places` | 2 | 122 |
| `services asset-digit-limits` | 1 | 77 |

Ogni rosso per l'assenza del contratto: il tipo delle due colonne (×2); la rilettura esatta di `123456789012.345`,
`-99999999999999.9`, `12345678901.2345` (×6, oggi il rumore); un inf letto `None` (×4); `1E+400` rifiutato in scrittura (×8 diretti, ×2
dal motore); `truncate_to_db_precision` su un importo a 15 cifre ROUND_DOWN (×3: il vecchio guard
`test_guard_an_amount_gets_no_significant_digit_cut` diventa un rosso, e `999999999999999.999999` → `999999999999999`, mai per
eccesso); `round_computed_value` su un importo (×2); la BUY di `-123456789012.345` riletta dall'ORM dopo `expire` e da `get_by_ids`, e
nei totali di controllo della sua sola riga (`TestACashAmountReadsBackExactly`); un dividendo di `12345678901.2345` riletto da
`query_events_bulk`. Guardie verdi: la dichiarazione e il DDL `NUMERIC(18, 6) NOT NULL` invariati; `-100`, `0.000001`,
`999999999999999`, `-1234.5`, `1.5` con la forma di oggi. > **Note implementazione**: `_UNCHANGED_COLUMNS` non elenca più le due
colonne; `_process_bind_param` gestisce un `Numeric` (senza il metodo) con un fallimento nominato; `db_schema_validate.py:10`, solo
docstring. `test_numeric_truncation.py` non chiede nulla (scopre il tipo da sé; verificato col suo aiuto e la regola di `(18, 6)`),
ma le sue docstring («seven columns», `:175`, `:257-258`) andranno a nove con la cura. > **⚠️ Fuori pista**: dopo la cura un valore di
evento inf si legge `None`, e `query_events_bulk` costruisce `Currency(amount=None)`, che fallisce: la query degli eventi resta rotta
su una riga così (oggi fallisce su `Infinity`: nulla peggiora) → in **W-B63**.

### W-B62 e W-B63 — i valori enormi nelle risposte e gli inf già salvati: analisi ✅, rossi di W-B62 ✅ (2026-10-17)

**Ordine del coordinatore** (03:3x): analisi in sola lettura con una proposta, nell'attesa dello slot di C-97b; niente codice
finché C-97b non è verde. (E le due righe di `ledger_totals.py`, di J, le scrivo io in W-B60, solo testo: aggiunte allo script
`files/scripts/wb60_cure.py`, da applicare con la cura.)

**W-B62 — stato reale** (HEAD `1f779d386`):
- `price_query.get_current_prices_bulk` (`services/assets/price_query.py:703`, di X): `cv = await core.call_provider(…)`, poi
  **`core._asset_current_cache.set(cache_key, cv)` prima di ogni controllo** (`:785`), poi `FACurrentPriceItem(value=cv.value)`.
  Un `1E+50000000` è un `Decimal` finito: pydantic lo accetta (rifiuta solo ±Infinity e NaN, che cadono nel `except` e vanno al
  ripiego del DB), `SafeDecimal` lo scrive con `format(v, "f")` (`schemas/common.py:47`): ~50 MB a risposta, e la cache lo
  riserve per 2 minuti a ogni utente (ramo del colpo in cache, `:767-776`). W-B58 lo tiene fuori dalla DB (`storable_price`,
  `:864`), non dalla risposta.
- **Lo stesso nel refresh**: `refresh._persist_refresh_item` costruisce `changed_items_delta` dai punti **in arrivo**
  (`_count_actual_price_changes`, o il ripiego `list(price_items)` quando quello solleva) e li risponde in
  `FARefreshResult.changed_points` (`refresh.py:643`, fino a `CHANGED_POINTS_PAYLOAD_CAP`): una data che `bulk_upsert_prices`
  scarta come non memorizzabile torna comunque nel delta col valore grezzo.
- Il serializzatore non è il posto: è condiviso da ogni `SafeDecimal`, e sollevare lì dà un 500 all'intera risposta.

**W-B62 — proposta** (codice di X, scritto da me con la sua revisione, come W-B58):
1. Al confine del provider in `get_current_prices_bulk`: `storable_price(cv.value)` subito dopo la chiamata; se `None` la quotazione
   è un fallimento del provider (avviso nel log), **non va in cache**, e l'elemento cade sul ripiego del DB come per un errore. Le
   valide si servono troncate come le salva la DB (12 decimali, 15 cifre: la risposta e la riga di oggi dicono lo stesso numero).
2. Il delta del refresh elenca solo i punti scritti: lo stesso predicato di `price_store._unstorable_provider_point` filtra
   `changed_items_delta` (va esposto come funzione pubblica del modulo).
3. Il ripiego del DB (`:815`, `Decimal(str(last_price.close))`) salta una riga con chiusura `None` (un inf letto dopo W-B58):
   oggi `Decimal('None')` solleva `InvalidOperation`, e il `gather` rompe tutta la richiesta.
Peso: piccolo (2 file di X + un aiuto pubblico in `price_store`); rossi: una quotazione `1E+50000000` mai servita né in cache, il
delta senza la data scartata, il ripiego con una chiusura `None`.

**W-B63 — stato reale**: dopo W-B58 e W-B60 le colonne lette da `RealDecimal` (quantità, importo, costo, i cinque prezzi, valore
dell'evento) rileggono un inf come `None` e non ne scrivono più; restano `Numeric`: `price_history.volume` (24, 0), `fx_rates.rate`
(24, 10) e `broker_user_access.share_percentage` (7, 6; limitata dallo schema, un inf non ci arriva). Lettori: il volume in 7 file
(segnali `obv`, `mfi`, `signals/base.py`, `price_query`, `price_store`, il plugin Borsa Italiana, l'export del backup), il cambio in 5
file della conversione FX (ovunque si converta). Un inf letto `Decimal('Infinity')` passa nei calcoli e il JSON lo scrive
`Infinity`, che lo Zod del frontend rifiuta: la risposta intera cade. Ma anche il `None` delle colonne `RealDecimal` ha lettori che
non lo reggono: il ripiego del prezzo corrente (sopra), `services/assets/crud.py:793` (`Decimal(str(ev.value))` nel confronto degli
eventi) e `query_events_bulk` (`Currency(amount=None)`, trovato dal test-author).
- **Come può esserci, oggi**: solo da una 1.2 (nessun limite di grandezza: un `1E+400` manuale diventava un REAL inf), da una
  scrittura a mano, o da un archivio preparato. SQLite salva NaN come NULL, quindi il caso è solo ±inf (`col IN (9e999, -9e999)`).

**W-B63 — proposta**: niente indurimento di N lettori; i dati si correggono una volta, all'avvio dopo l'aggiornamento.
1. **Una correzione post-migrazione** (`db/post_migration/`, il quadro che esiste per i dati che Alembic non deve toccare:
   connessione `sqlite3` diretta, controllo d'integrità, copia di backup, una transazione, verifica, `row_count_changes`), non una
   migrazione Alembic né `db validate` (lo strumento di sviluppo: un self-hosted non lo lancia). `NonFiniteDecimalsFix`: `detect`
   conta per colonna i valori `IN (9e999, -9e999)`; `apply`:
   - colonne annullabili (`price_history.open/high/low/adjusted_close/volume`, `transactions.cost_basis_override`): `NULL`;
   - righe ricavabili di nuovo: `price_history` con la chiusura inf e `fx_rates` col cambio inf **cancellate** (il refresh e la
     sincronizzazione FX le riprendono; un cambio manuale perso è nel rapporto con data e coppia);
   - dati dell'utente NOT NULL (`transactions.quantity/amount`, `asset_events.value`): **mai toccati**, solo riportati (id nel log e
     nel rapporto): dopo W-B58/W-B60 si leggono `None` e l'utente li corregge o cancella (la cancellazione è provata dai test di
     W-B58).
2. Le due guardie puntuali sui lettori del `None` che rompono una richiesta intera (il ripiego del prezzo corrente, sopra;
   `crud.py:793` e `query_events_bulk`: la riga saltata con un avviso).
3. Il cambio (W-B61, di X) chiude l'ultima scrittura senza limite.
Decisione per il developer (**D-W63-1**): cancellare all'avvio le righe di prezzo e di cambio con un inf (ricavabili, riportate),
o solo riportarle. **Predefinito**: cancellare e riportare. Peso: medio (una correzione con i suoi test di rilevamento, dry run e
verifica, più le due guardie); rossi prima.

**Ordine proposto**: W-B60 (dopo gli E2E di C-97b) → W-B62 (piccolo, sicurezza della risposta) → W-B63 (dopo D-W63-1 e, per i
cambi, W-B61 di X).

**Ordine approvato** (coordinatore, 03:38): W-B60 (dopo gli E2E di C-97b) → W-B62 (file di X, revisione di X) → W-B63 (dopo
D-W63-1, data al developer, e W-B61/X-R38 di X per i cambi). Nell'attesa dello slot: i rossi di W-B62, solo file di test.

**I rossi di W-B62 ✅ (03:46, carico 43)**, test-author `0746298a`, tutti in `test_asset_digit_limits.py`: `services
asset-digit-limits` **18 falliti, 80 passati** (i 17 di W-B62 più il rosso di W-B60 sul valore dell'evento). Rossi: mai servita
(`1E+50000000`, `1E+60`, `1E-13`, con e senza riga salvata; ×6); mai in cache (le tre, più `derived-float-inf`: la cache registra
ogni valore che riceve, e una seconda chiamata deve tornare al provider; ×4); la quotazione valida servita come la tiene la DB
(`65432.1234567890999` → `65432.123456789`, confronto per valore; ×1); il delta del refresh senza la data scartata (chiusura
`1E+60`, volume `1E+25`; ×2); il ripiego oltre una chiusura illeggibile e senza nessuna leggibile, senza provider o con un
provider che fallisce (oggi `InvalidOperation` da `Decimal(str(None))`; ×4). Guardie verdi: `101.5` servita e in cache come prima;
la riga più recente normale come ripiego. > **Note implementazione**: il provider finto conta le chiamate, solleva se la quotazione
è un'eccezione e serve uno storico; la fixture `assigned` divisa in `_assign_double`/`_drop_double`; la barriera di
`test_an_unstorable_current_quote_is_not_persisted` ora controlla che il provider sia stato chiamato (non che l'elemento venga da
lui), perché con la cura una quotazione non memorizzabile cade sul ripiego: i suoi 4 casi restano verdi. `1E+50000000` non costa
nulla (19,6 s tutta la prova: niente lo scrive per intero). > **⚠️ Fuori pista** (letto nel codice, non provato): l'elemento del
colpo in cache si costruisce fuori dal `try` del provider; oggi un float inf finisce in cache prima che lo schema lo rifiuti, e la
chiamata successiva entro 2 minuti solleva e rompe tutto il bulk. La cura (una quotazione non memorizzabile non va in cache) lo
chiude.

**W-B62 passa a X** (coordinatore, 03:4x), insieme alla sua X-R40 (la stessa quotazione rifiutata data come viva, nei file di X):
la mia analisi qui sopra è il riferimento. I rossi già scritti restano non committati nel mio worktree finché il coordinatore non
li passa a X, che mette i suoi casi in un file nuovo e cambia solo la riga della barriera in `test_asset_digit_limits.py`. Copie
fuori dal repo: `files/wb62_for_x/` (il file intero, il diff contro HEAD, il blocco 1132–1371). Prima del checkpoint di W-B60 tolgo
dal file le parti di W-B62 (il blocco, il paragrafo della docstring, gli import usati solo da lì, gli aiuti del provider finto e la
barriera), così il commit porta solo W-B60. Il mio ordine: slot di C-97b → W-B60 → W-B63 (dopo D-W63-1).

**Il file torna solo W-B60 ✅ (03:5x)**: il coordinatore ha passato le copie a X; per il checkpoint di W-B60, barriera e aiuti come
committati con W-B58 (li cambia X). Il test-author `0746298a` ha tolto da `test_asset_digit_limits.py` ogni parte di W-B62 (il
blocco, il paragrafo della docstring, gli import `contextlib`, `AsyncIterator`, `FARefreshItem`/`SyncDateRangeModel`, `core`) e
riportato `_Assigned`, `_QuoteDouble`, la fixture `assigned` e la barriera al testo di HEAD: il diff ha 3 hunk, tutti di W-B60 (il
paragrafo della docstring, gli import `FAEventQueryItem`/`DateRangeModel`, la sezione «W-B60: an event value reads back exactly»).
`ruff` e `black` puliti; `services asset-digit-limits` (03:54, carico 45): **1 fallito** (il rosso di W-B60), **77 passati**. Delta di
W-B60 nel worktree: 4 file di test (+350/−18) e il journal; nessun codice di prodotto.

**Coda aggiornata** (coordinatore, 03:56): slot di C-97b → W-B60 → **W-B67** (il costo Auto sulla riga sbagliata, da J nell'analisi
di V-4: `_find_created_tx_for_wac` ripiega sull'ultima riga con broker, asset, data e tipo uguali; prima del rilascio, rossi prima)
→ W-B63 (dopo D-W63-1). Dopo C-97b, J scrive un `case` in `features/transactions/events/eventSaveError.ts` (il 409 di P-10,
`EVENT_SPLIT_ADJUSTMENTS_WITHOUT_COST`): lo rivedo io.

**C-97b entrato** (coordinatore, 05:1x): dev `b2462042d`, la mia frase aggiunta alla voce C-97 del CHANGELOG in `b214c8200`. Il mio
ff fallisce per i file di W-B60 non committati: HEAD resta `1f779d386`, la punta arriva al checkpoint di W-B60 (col piano 04).

**W-B60 — la cura ✅ (05:1x)**: gli E2E di C-97b sono verdi, quindi il codice di prodotto è ammesso.
`files/scripts/wb60_cure.py --apply` (3 file): `backend/app/db/models.py` (`Transaction.amount` e `AssetEvent.value` →
`RealDecimal(18, 6)`, la docstring del modulo), `.github/instructions/backend-db.instructions.md` (la regola) e
`backend/app/services/financial_math/ledger_totals.py` (di J, assegnato dal coordinatore: le due righe che nominano il tipo degli
importi, solo testo). Docstring di `test_numeric_truncation.py` a mano: la scoperta trova ora **nove** colonne `RealDecimal` (le
sette di C-97a più importo e valore dell'evento) e tre `Numeric` (`share_percentage`, `rate`, `volume`).
> **Note implementazione**: il filtro `func.abs(Transaction.amount) >= …` (`transactions/queries.py:79-81`) non passa dal
`process_bind_param` del nuovo tipo: `func.abs` è senza tipo, il parametro prende `Numeric` dal valore, e un `1E+400` si lega
come oggi (`inf`, nessun risultato, nessun 500); `amount != 0` passa da `RealDecimal` con un letterale finito. Verificato con
SQLAlchemy dalla venv del progetto. Un importo della 1.2 con più di 15 cifre significative ora si rilegge arrotondato alla
quindicesima: al più 0,000005 di differenza con 10 cifre intere, circa dieci volte tanto per ogni cifra intera in più (misurato dal
docs-writer su 300 000 campioni per caso: 0,000055 con 11, 0,00055 con 12; la 1.2 non limitava le cifre degli importi); dopo C-97
un importo nuovo non ne ha più di 15.

**W-B60 — le prove leggere ✅ (05:16–05:28, carico 29–47)** (`files/scripts/wb60_light.sh`, cancello < 50 che salta e non forza):
i rossi verdi — `utils real-decimal` **239**, `services transaction-decimal-places` **124**, `services asset-digit-limits` **78**; i
vicini che leggono importi — `db numeric-truncation` **4** (rifatto dopo le docstring), `db validate` **17**, `db post-migration`
**41**, `utils decimal-precision` **21**, `services financial-math` **825**, `services backup-totals` **84**, `services
backup-archive` **155** (1 saltato), `services backup-staging` **145**, `services lots-analysis-pure` **177**, `services
transaction-cost-basis-rule` **80**. `ruff` e `black` puliti sui 7 file `.py` toccati. Doc per sviluppatori: docs-writer `9c1ef823` in
corso. Restano: lo slot pesante (`all-backend --workers 2`, ~33 min l'ultima volta: il tipo di ogni importo cambia) e la simulazione
sulla punta di dev.

**W-B60 — la doc ✅ (05:3x–05:4x)**, docs-writer `9c1ef823`: `architecture/database/index.md` (la riga della tabella a
`RealDecimal(18, 6)`, gli esempi del rumore, la frase su W-B60 senza migrazione, la nota sui dati della 1.2, le colonne senza le
guardie ridotte a `volume` e `rate`), `brokers_transactions.md:101` (la riga `amount`), `backend/transactions/service.md:184-186`
(«the amount is `Numeric`» → l'importo fra le colonne `RealDecimal`), `backend/financial_math.md:239`; `events.md` non nomina il
tipo: niente. Build stretta e `check-links` verdi (carico 30–32); secondo giro chiesto per `brim_plugin_guide.md:212-214` (15 cifre
intere anche per l'importo). > **⚠️ Fuori pista** (dalle verifiche del docs-writer): (1) la mia nota sui dati della 1.2 diceva «al più
0,000005»: vale solo con 10 cifre intere → corretta sopra e nella doc; (2) tre passi di `backend/app/db/precision.py` dicevano ancora
l'importo `Numeric` (la docstring del modulo, il commento di N63, l'esempio di `round_computed_value`, che ora usa un cambio:
`123456789.12345678912` → `123456789.1234567891`, verificato con la funzione) → corretti a mano, solo testo, `ruff` e `black` puliti;
(3) i valori degli eventi dei provider non sono troncati alla colonna come i prezzi dei provider (`_storable_events` controlla solo la
grandezza): con la lettura nuova un pareggio al settimo decimale arrotonda diversamente (`784.0774475`: prima `…447`, ora `…448`) e un
valore di 10+ cifre intere può superare le 15 significative → **W-B68**, basso.

**Il percorso del coordinatore** (05:29): lo slot 3 per `all-backend --workers 2`, ma sulla revisione combinata (HEAD `1f779d386` è
130 commit indietro rispetto a dev): doc finite → CHECKPOINT READY e FROZEN con le liste da mettere in stage → lui committa e unisce
dev nel mio ramo → `all-backend --workers 2` nella mia corsia (6184) quando il carico a 5 minuti è < 50. CHANGELOG: la mia riga come
riga 🐛 a sé, non dentro C-97.

**La simulazione e le risoluzioni ✅ (05:4x–05:5x)**: su dev `252835dce`, 3 conflitti in 2 file, tutti fra W-B60 e X-R38/X-R50
(i cambi di X, `80f5c65ff` e `243ab6150`, la parte FX di W-B58): in `test_real_decimal.py` due paragrafi della docstring e due sezioni
di test aggiunti nello stesso punto (×2); in `architecture/database/index.md` la tabella (la riga dell'importo mia, `RealDecimal(18,
6)`; quella del cambio di X, 14 cifre intere). Risolti per unione, prima X poi W-B60 (`files/scripts/wb60_resolve.py` →
`files/wb60_resolved/`). Rifatta su dev **`1c2bac918`** con `--resolved`: **0 conflitti**, lint pulito nell'albero simulato, `mkdocs
build` stretto e `check-links` verdi; i due file risolti non sono cambiati in dev fra le due punte (fuori di essi, solo altre sezioni
del backlog, che si fondono da sole). Prova semantica: `utils real-decimal` lanciato nell'albero simulato (il codice di dev più il mio)
→ **267 passati** (i 239 di W-B60 più i 28 di X-R38/X-R50).

**W-B60 — `all-backend` e ingresso (06:36–06:5x)**: `all-backend --workers 2` su `c5761ac55` (05:57–06:36, 38m44s; la build del
frontend 17 minuti): **6 categorie su 7 verdi**; nei servizi 6 486 passati, 5 saltati, **2 falliti**, entrambi in
`test_lone_transfer_legs.py` → **W-B69** (sotto). Non di W-B60: gli stessi 2 rossi su un'esportazione pura di dev `1c2bac918` (senza
W-B60) e da soli nel worktree (carico 23–25). W-B60 entrato: dev `484c71afb`, CHANGELOG 🐛 `0dc58c70b`; HEAD avanzata a `0dc58c70b`.
Revisione di X-R47 (`5f68a8db0`, sola lettura): OK, una nota bassa (il rapporto mostrato com'è, `-0.5`, in frasi IT/FR/ES che
scrivono «0,5»).

### W-B69 — il costo Auto calcolato ignorando una riga illeggibile (regressione di W-B58): analisi ✅ (2026-10-17)

**Stato reale**: la decisione 1 della 47 vuole che una gamba che cede, il cui costo non si calcola, resti un TRANSFER con una
ragione. I test lo provocano piantando nel suo insieme una riga di quantità `'n/a'` (testo): prima di W-B58 la lettura sollevava
(TypeError) e il calcolo con lei. Da W-B58 (`7a4fdf024`) `RealDecimal` legge `None`: `compute_wac_iterative` (facciata di MF,
`portfolio_service.py`) carica la riga (`quantity IS NOT NULL AND quantity != 0` vale per un testo) e
`cost_movement_from_transaction` (`financial_math/average_cost.py:294`) tratta `None` come 0 e la salta: la media esce **senza
quella riga** e la gamba diventa un ADJUSTMENT a quel costo, per sempre. Con W-B60 un importo illeggibile letto `None` fa peggio:
`abs(tx.amount) if tx.amount else 0` ne fa un acquisto gratuito. Gli stessi calcoli servono al costo Auto nel batch (create,
update, divisione di una coppia TRANSFER), alla cancellazione di un broker (`delete_by_broker`, «ogni costo prima di cambiare una
riga: un calcolo che fallisce lascia tutto com'era») e al passo delle gambe sole (`lone_transfer_legs.py`, per gamba `try/except` →
ragione).

**Disegno**: in `_auto_cost` (`auto_cost.py`, mio) una guardia prima del calcolo: le righe dell'insieme (stessi filtri della
facciata, senza gli esclusi) lette dall'ORM; una con quantità o importo `None` → `UnreadablePoolError` (gli id nel log, il conteggio
nel messaggio). Effetti: le gambe sole tornano alla decisione 1 (i 2 rossi diventano verdi); la cancellazione di un broker torna a
fallire intera, come progettato; nel batch un **issue** al posto di un 500 o di un costo sbagliato: codice nuovo
`autoCostUnreadable` sulla riga (`cost_basis_override`, `params {count}`, nessun id: l'insieme può essere di un broker partner),
chiave `transactions.errors.autoCostUnreadable` (4 lingue); il batch si ferma lì. Fuori: l'anteprima `POST /portfolio/wac` (facciata
di MF, nessuna scrittura) e gli altri lettori che saltano un `None` (la pulizia dei dati è W-B63). Rossi: i 2 esistenti, più il batch
(create Auto e divisione di una coppia) e la cancellazione di un broker con un insieme illeggibile, e il caso dell'importo.
**Peso**: medio (~2–3 ore con i18n, test e doc), non sotto l'ora → dopo SEC7-3, come da ordine del coordinatore.

### R13-SEC7-3 — `format(v, "f")` sull'input prima dei limiti, il giro dei giorni, le date: analisi ✅ (2026-10-17)

**Fonte**: piano 08 di E, «R13-SEC7», reperto 3 (MEDIUM 8/10, DoS da qualsiasi utente: OOM), più le due aggiunte del coordinatore
(06:3x): `balances.py:75` e la data controllata in scrittura (J). Priorità: prima di W-B69.

**Stato reale** (HEAD `0dc58c70b`):
- `services/brokers/broker_service.py:173`: i saldi iniziali di un broker nuovo diventano un dict grezzo con
  `format(currency_obj.amount, "f")` prima di `execute_batch`; `Currency.validate_amount` (`schemas/common.py`) fa solo
  `Decimal(str(v))`, e pydantic accetta `1E+999999999` (finito): `format` scrive un miliardo di cifre sul loop degli eventi.
- `services/transactions/promotion.py`: `format(-abs(qty), "f")` e `format(abs(qty), "f")` (`quantity: SafeDecimal` della richiesta,
  `:127`, `:136`): `abs()` va in `Overflow` oltre l'Emax del contesto (`1E+1000000`: un 500), e sotto scrive tutte le cifre;
  `format(req.cost_basis_override.amount, "f")` (`:141`) come il broker. Le due casse (`:151`, `:160`) vengono da righe salvate:
  limitate.
- Gli altri `format(v, "f")` dei servizi leggono valori interni o già limitati (ledger_totals, series_preparation, telemetry, PAC);
  quello del plugin Danske legge il file nel worker del pool (da guardare a parte: fuori dal reperto).
- `services/transactions/balances.py:75`: il giro di `_validate_broker_balances` va **giorno per giorno** da `from_date` (o dalla
  prima transazione) all'ultima transazione. Nessuna richiesta gli passa un intervallo: gli estremi sono le **date delle
  transazioni**, che però scrive l'utente senza limiti → una riga del `0001-01-01` (o del `9999-12-31`) fa girare ~740 000 (o ~2,9
  milioni) di giorni a ogni batch che tocca quel broker, sul loop degli eventi.
- **Date**: nessun limite (`TXCreateItem.date`, `TXUpdateItem.date`, `resolved_fields.date` della promozione); l'interfaccia vieta già
  il futuro (`SingleDatePicker`, `allowFuture` falso di default, i form non lo cambiano), l'API no.

**Disegno della cura**:
1. **I due dict grezzi**: `str(v)` al posto di `format(v, "f")` (la notazione corta: `1E+999999999` resta di 12 caratteri, e il batch
   la rifiuta con `integerDigitsExceeded` e si ferma, W-B58); il segno con `copy_abs()`/`copy_negate()`, senza contesto (niente
   `Overflow`).
2. **Al confine**, difesa in profondità: `Currency.validate_amount` rifiuta un importo con un esponente fuori da ±100
   (`adjusted()`), e la `quantity` della richiesta di promozione lo stesso: 422 prima di qualsiasi lavoro. Nessun valore legittimo vi si
   avvicina (al più 24 cifre intere, al più 12 decimali). `SafeDecimal` in generale e il serializzatore `_decimal_fixed_point` non li
   tocco: condivisi da 207 campi anche di risposta; il lato dei provider è W-B62 di X.
3. **Il giro dei giorni**: solo i giorni con transazioni (più `from_date`), non ogni giorno del calendario: fra due giorni con
   movimenti i saldi non cambiano, e il primo giorno negativo è sempre uno di loro (o `from_date`, coi saldi precedenti) →
   equivalente, e lineare nelle transazioni.
4. **Le date in scrittura (decisione notturna N74)**: `1900-01-01 ≤ data ≤ oggi + 1 anno`, controllate in uno stadio del batch accanto
   a `check_decimal_limits` (create, update, `resolved_fields.date` delle promozioni; l'import BRIM conferma dal batch); codice
   `dateOutOfRange` `{min, max}` sul campo `date`, chiave `transactions.errors.dateOutOfRange` (4 lingue); il batch si ferma come per
   le cifre intere. **N74, N = 1 anno**: l'interfaccia vieta già il futuro; un anno copre fusi orari e date di regolamento in avanti di
   un report; alternativa N = 10. Il batch risponde con le issue (200, `committed` falso), come per tutti i codici del batch.

**Prove** (rossi del test-author prima della cura): i dict grezzi del broker e della promozione senza cifre espanse (una spia su
`execute_batch`, con `1E+5000000`, senza rischiare un OOM nel test) e la promozione di `1E+1000000` senza 500; il 422 al confine; il
giro dei giorni (guardia d'equivalenza: la data dell'errore con anni di vuoto, e coi saldi precedenti già negativi); le date (create,
update, promozione, i bordi: 1900-01-01 e oggi + 1 anno accettati, il giorno prima e il giorno dopo rifiutati). Dopo: `services
transaction-*`, `api transactions-validate`, `api batch-split-promote`, `api brokers*`, e uno slot.

### R13-SEC7-3 — cura (2026-10-17, in corso)

**Disegno approvato** dal coordinatore (17/10): «design OK, in the order you gave»; `schemas/common.py` mio per questo lotto;
**N74 con N = 1 anno**; il batch risponde 200 con `committed` falso; `balances.py` sui soli giorni con transazioni.

**Decisione notturna N74** (da rivedere col developer): una transazione porta una data fra **1900-01-01** e **oggi + 1 anno**
(UTC; il 29 febbraio → 28 febbraio). Controllata in scrittura nello stadio `check_dates` del batch: create, update che cambia la
data, data risolta di una promozione; l'import BRIM conferma da lì. Fuori dai limiti `dateOutOfRange` sul campo `date`, `params
{min, max}` (ISO), il batch si ferma dopo il controllo d'accesso. Perché 1 anno: l'interfaccia vieta già il futuro
(`SingleDatePicker`, `allowFuture` falso), un anno copre i fusi orari e le date di regolamento in avanti di un report;
alternativa N = 10. Le righe già salvate fuori dai limiti restano (un update che non tocca la data passa): il giro dei saldi non
le paga più (passo 3 del disegno); altri giri per giorno su tutta la storia, se ce ne sono, sono di J.

1. ✅ **Rossi** (test-author `3f86d648`, 2026-10-17).
   > **⚠️ Fuori pista**: il limite al confine (`Currency.validate_amount`, ±100) cambia un caso già committato di W-B58:
   > `test_transaction_decimal_places.py`, `MILLION_DIGIT_REFUSALS`, `c-cash-amount--1E+1000000` non arriva più a
   > `check_decimal_limits` (`integerDigitsExceeded {max: 15}`): lo rifiuta il parse del batch (`value_error` su `cash.amount`,
   > «Invalid value»). Stesso scopo (niente 500, niente salvato), codice diverso; la quantità (non `Currency`) tiene
   > `integerDigitsExceeded` a ogni esponente. Scelto di tenere il disegno approvato e ri-fissare quel caso (test-author), non
   > di restringere il limite alle due richieste: il limite in `Currency` protegge ogni richiesta che porta un importo. I plugin
   > BRIM costruiscono `Currency` nel parse: un file con un esponente oltre ±100 non si legge più (prima lo rifiutava il batch);
   > nessun file vero ci si avvicina, e `abs()` di quei valori andava già in `Overflow`.
   > **Note implementazione**: rossi per la cifra espansa (broker `test_broker_service.py`, promozione `test_transaction_service.py`:
   > lo `str` breve sulla spia di `execute_batch`, con `model_construct`), il 422 al confine (`test_common_schemas.py`,
   > `test_broker_schemas.py`, `test_transaction_schemas.py`; `test_brokers_api.py`, `test_transfer_promotion.py`: oggi 200 e 500), il giro dei
   > giorni (`TestBalanceReplayDays`: tre guardie + il rosso dei 3 653 passi), le date (`TestTheDateIsCheckedAtWrite` e i codici elencati),
   > il risolutore (`resolveValidationMessage.decimals.test.ts`, 4 lingue dal catalogo vero). Tutti rossi per il contratto mancante.
   > **⚠️ Fuori pista**: la mia revisione della cura contro i rossi ha trovato un buco: nel batch, il costo risolto di una promozione che
   > `Currency` rifiuta (esponente oltre ±100, o nessun numero) sfuggiva al controllo e alzava in `_apply_promote_cost_basis` (un 500;
   > `abc` lo fa già oggi). Rosso in più, `TestAPromotedCostBasisCurrencyRefuses` (8 rossi, 11 verdi), e la cura lo copre.
   > **⚠️ Fuori pista**: il test-author, con un `UPDATE … WHERE status != 'done'` sulla tabella `todos` della sessione, ha chiuso 21
   > todo altrui; rimessi a posto a mano dal confronto col backlog (17 riaperti, 4 marcati «da verificare»).
2. ✅ **Cura** (2026-10-17): `files/scripts/sec73_cure.py --apply` (9 file) + `dev.py i18n add transactions.errors.dateOutOfRange` (EN
   «Between {min} and {max}», IT «Tra {min} e {max}», FR «Entre {min} et {max}», ES «Entre {min} y {max}»).
   > **Note implementazione**: `str()` e `copy_abs()/copy_negate()` nei due dict grezzi; `check_decimal_exponent` (±100,
   > `MAX_DECIMAL_EXPONENT`) in `schemas/common.py`, chiamato da `Currency.validate_amount` (anche il ramo `Decimal`) e dal validatore della
   > `quantity` di `TXTransferPromoteRequest`; il giro dei saldi sui giorni con transazioni più `from_date`; `check_dates` (N74) con
   > `transaction_date_bounds()`, `TXValidationCode.DATE_OUT_OF_RANGE`, lo stop in `execute_batch`, `dateOutOfRange` in
   > `FIELD_PREFIXED_CODES`. Lint: ruff pulito; black chiedeva una riga vuota in `common.py` (corretta, script allineato); prettier pulito.
   > Verificato prima: una lettura `RealDecimal` quantizza alla scala della colonna, quindi nessuna lettura dà a `Currency` un esponente
   > oltre 12; il suggerimento delle promozioni nega solo la riga salvata (`-tx_b.…`), mai l'input.
   > **⚠️ Fuori pista** (trovato a margine, fuori dal reperto): lo stesso suggerimento fa `inp.date ± timedelta(days=tolerance_days)`, e
   > una data `0001-01-01` o `9999-12-31` dà un `OverflowError`, un 500 di quella richiesta (non memoria né CPU) → **W-B71** nel backlog.
3. ⏳ **Verdi**. Leggeri (17/10 07:43–07:44, carico 33–39): `schemas common` 100, `schemas brokers` 38, `schemas transactions` 126,
   `services broker` 81, `services transaction` 104, `services transaction-decimal-places` 150: tutti verdi. Restano Vitest, i file `api`,
   `utils gate-i18n-catalog`, e dopo H-41 il giro intero.
4. ✅ **Doc** (2026-10-17): docs-writer `2e1c78ce`, 12 pagine EN (sviluppatore: `balance_validation.md`, `service.md` con
   «📅 Transaction dates», `database/index.md`, `brim_plugin_guide.md`, `split_promote.md` con `#promote-request-shape`, `brokers/forms.md`,
   `wac.md`, `brokers_transactions.md`; utente: `form`, `import/how-to`, `import/index`, `transactions/index`). Le frasi IT/FR/ES delle 4
   pagine utente le ho scritte io (`files/scripts/sec73_user_docs_i18n.py`, 12 file, le etichette dal catalogo); `translate-validate`
   pulito su `how-to`, `import/index`, `index`; timbrate solo `how-to` e `import/index` (la cache di Aphra combaciava con l'EN di HEAD).
   `mkdocs build` stretto ok (87 s, carico 35), `check-links` ok (docs-writer).
   > **⚠️ Fuori pista**: `form.en.md` ha un debito di traduzione precedente, mio (E1b, `0ffaa9127`): il punto «Missing event?» e il suo
   > link `events.md#new-event`, la cui sezione manca anche in `events.{it,fr,es}.md` → non timbrata (il timbro nasconderebbe il debito),
   > resta alla pipeline. `transactions/index.en.md` aveva già una deriva non timbrata (cache ≠ EN di HEAD) → non timbrata.
   > **⚠️ Fuori pista**: discordanze trovate dal docs-writer: (1) il giro giorno per giorno partiva da `from_date`, non dalla prima riga:
   > la riga che pesava su ogni batch era una lontana nel futuro (`9999-12-31`: ~2,9 milioni di giorni a ogni giro successivo, poi
   > l'overflow della data), una dell'anno 1 solo quando il giro partiva da lì → il commento in `balances.py` corretto; (2) «ogni lettura
   > fallisce» (H-41) non si riproduce: la colonna `Text` di SQLite salva un numero come testo (`'42'`) → tolto dalla docstring del modello
   > e dal piano; (3) il costo unito su entrambe le righe di una coppia di cassa → **W-B72**; (5) la pagina utente dice che l'unione sceglie
   > data e costo → **W-B73**; (6) la docstring di `execute_batch` senza `check_dates` → corretta.
5. ✅ **Simulazione sulla punta di dev** (2026-10-17 08:20): `sim_cherry_pick.sh 7f8e69be6 --docs` sui 51 file del lotto (SEC7-3 +
   H-41, giornale compreso; dev è 98 commit avanti): 0 conflitti, ruff/black e JSON puliti, `mkdocs build` stretto e `check-links` ok
   sull'albero simulato (carico 35). Dev ha toccato un solo file del lotto, `BACKLOG_POST_1.2.md` (altre sezioni).
   > **Note implementazione**: la metà dei rossi di W-B69 che resta a me (33 rossi, 24 guardie, `test_transaction_cost_basis_rule.py`)
   > è parcheggiata in `files/wb69_mine/` (copia e diff, sha256 `3f48c081db18…`) e il file riportato al contenuto di HEAD con
   > `git show HEAD:… >` (nessun comando git che scrive): fuori dal checkpoint e dal giro completo sulla revisione combinata. La metà di
   > MF (17 test, file a sé) gli è stata mandata direttamente (`files/wb69_for_mf/`), con la bozza di `auto_cost.py` e il cucito.
6. ✅ **Handoff** (2026-10-17 08:3x): CHECKPOINT READY, FROZEN. Committati dal coordinatore: `c0b67f4c8` (cura), `61acbc16b` (test),
   `4bd1d28f6` (doc), `6da4ae0ae` (giornale); base `eced298f8` (+ dev `eed325d99`), poi **`5ece98c29`** (+ dev `73443c6db`: W-B69 di MF,
   X-R53, B-31, Y-25; `wac.md`, `service.md`, `database/index.md` fusi da soli).
7. ⏳ **Giro completo** (`files/scripts/allb_sec73.sh`, slot 2, `5ece98c29`, 08:55–09:48, carico a 5 minuti 48,8 alla partenza):
   **rosso**. 5 categorie su 7 verdi (External, DB, Utils, Schema, E2E); Services: worker 0 21 falliti / 8239 passati, worker 1 2 / 7444
   (5 saltati); API: worker 1 7 / 1072 (2 saltati). Porta libera dopo.
   - **`services asset-digit-limits`, due casi `1E+400` (miei)**. (a) **Regressione vera**: `event_store._storable_events` analizzava
     l'evento del provider con `FAAssetEventPoint(**raw)` *prima* del controllo delle cifre intere di W-B58, e il limite d'esponente di
     SEC7-3 (in `Currency`) faceva alzare quell'analisi: un refresh perdeva **tutti** i suoi eventi invece di scartare quello. (b) Il
     caso dell'evento manuale: `FAEventUpsert` ora rifiuta `1E+400` al confine (il contratto di SEC7-3: un 422, niente scritto), e il
     test di W-B58 costruiva la richiesta aspettando l'`EVENT_TOO_MANY_DIGITS` del magazzino → da ri-fissare.
   - **`email-verification`** (21 services + 7 API, non miei): tutti `EmailRateLimitedError` con `retry_after` ≈ 899 s, il
     `SlidingWindowLimiter` in memoria di 15 minuti (`RESEND_BY_ADDRESS`/`FORGOT_BY_ADDRESS`) speso da test che dividono un processo
     sotto 2 worker. Da soli verdi (09:51–09:52, carico 27–30: services 127, API 60), e così nei cancelli F (`f4dab3db7`) e D del
     coordinatore: isolamento fra test, non SEC7-3; passato a E dal coordinatore.
   > **⚠️ Fuori pista**: la base è cambiata (`eced298f8` → `5ece98c29`) mentre il primo lancio aspettava ancora nel cancello del carico:
   > fermato senza che il giro fosse partito (nessuna riga «start», porta libera, nessun processo) e rilanciato sulla base nuova.
8. ✅ **Cura in avanti** (`files/scripts/sec73_fix_events.py --apply`, 2026-10-17 09:5x): in `_storable_events` l'analisi di ogni
   evento grezzo dentro un `try`; un `ValidationError` lo scarta con lo stesso avviso, col giorno e il tipo, **mai il valore** (può essere
   lungo a piacere). Ruff e black puliti. Il caso manuale lo ri-fissa il test-author `3f86d648` (un test proprio per `1E+400`: il rifiuto
   dello schema al confine, niente scritto; `1E+13` e `1E+60` restano al rifiuto del magazzino), più un evento del provider di 5 000
   cifre scartato. Poi `services asset-digit-limits` e le unità vicine.
   > **Note implementazione**: `services asset-digit-limits` **79 passati, 0 falliti** (test-author, carico 29,6: il rosso della
   > regressione verde, il nuovo test del rifiuto dello schema per l'evento manuale, il nuovo evento del provider di 5 000 cifre); le
   > vicine (09:56–09:58, carico 26): `services asset-event-store` 71, `services event-split-ratio` 78, `services asset-source-guards`
   > 29, `api assets-events` 45. Doc: `developer/backend/assets/events.md`, il paragrafo dello scarto dei provider (l'evento rifiutato
   > dallo schema, scartato uno alla volta, nel log solo data e tipo). Il controllo che l'avviso non porti il valore lungo non è nel
   > test (il file non cattura i log): lo garantisce il codice (`(refused by the schema)`).

#### Revisione del lotto di MF (W-B69, la sua metà) — ✅ (2026-10-17)

`1b4e4a27d` (in dev `c61a2db4d`), dopo il fatto, in sola lettura via git: `auto_cost.py` uguale alla mia bozza e al contratto
(`UnreadablePoolError(count)` senza id; `_unreadable_pool_rows` coi filtri della facciata, il costo salvato ma letto `None`; il cucito per
riga col rilancio senza lista); `lone_transfer_legs.py` solo commenti; i 17 test identici byte per byte a quelli consegnati (sha256
`1272a3d3c0b6…`), registrati come `services auto-cost-unreadable-pool` (classe `write-scoped` della categoria); doc accurata (il
paragrafo finale di `wac.md#unreadable-pool` lo riscrivo con la mia metà). Nota senza azione: in `delete_by_broker` un sopravvissuto
con la quantità illeggibile fallisce su `survivor.quantity < 0` (TypeError): la cancellazione fallisce intera, con un messaggio tecnico
(classe W-B74/W-B63). **Pavimento condiviso di N74**: MF definisce `EARLIEST_RANGE_START = date(1900, 1, 1)` in
`utils/datetime_utils.py` (MF-SEC8-2); io tolgo `TRANSACTION_DATE_MIN` e lo importo nel primo lotto dopo la sua entrata (più
`service.md:207`), così nessuno importa da un modulo di servizio (accordo con MF e coordinatore, 17/10 08:5x).

#### H-41 dentro SEC7-3 — i campi uniti di una promozione, tipati (2026-10-17)

**Fonte**: H, via il coordinatore (17/10 07:5x): «`TXPromoteBatchItem.resolved_fields: Dict[str, Any]` … applicato com'è; `description` nella
colonna `Text` senza controllo di tipo né di lunghezza: un numero (anche `Infinity`) lì fa fallire ogni lettura di quella transazione;
`cost_basis_override` o `date` sbagliati probabilmente un 500. Direzione: un modello tipato, un rosso prima per ogni campo».

**Stato reale**: `_apply_promote_resolved_fields` (`batch_creates.py`) scrive `description` com'è (la lettura, `TXReadItem.description:
Optional[str]`, fallirebbe su un numero; ma la colonna `Text` di SQLite lo salva come testo, `'42'`: non si riproduce), `tags_to_csv(123)` alza (TypeError), un dict di tag ne salva le chiavi,
`parse_ISO_date` alza su una data sbagliata o `null`, `Currency.model_validate` su un costo che non è un oggetto; una chiave sconosciuta è
ignorata. L'interfaccia (`PromoteMergeModal`) manda solo `description` e `tags`; `date` e `cost_basis_override` solo dall'API.

**Disegno**: `TXPromoteResolvedFields(StrictModel)` in `schemas/transactions/batch.py`, tipato come i campi di una create: `description`
(al più 500), `tags` (`validate_tags_list`), `date` (un `null` esplicito rifiutato), `cost_basis_override: Currency`; chiavi sconosciute
rifiutate. Si applica ciò che la richiesta nomina (`model_fields_set`): un `null` esplicito svuota descrizione, tag, costo. Il rifiuto è al
parse del batch, issue della promozione sul nome del campo stesso (`_loc_to_field` toglie `resolved_fields.`: l'etichetta è quella del
campo). Sostituisce la cattura dei rifiuti di `Currency` che avevo messo in `_promote_cost_amount` (passo 2): il parse li rifiuta già, con
lo stesso codice e lo stesso campo (`cost_basis_override.amount`). Script: `files/scripts/h41_cure.py` (dry run pulito su 3 file).
**Scelta (500 caratteri)**: la descrizione unita (`mergeStrings`: `a\nb`) di due descrizioni lunghe può superarli e allora è rifiutata;
è già così sul ramo misto e su quello nuovo+nuovo dell'unione, dove la create porta il testo unito (`TXCreateItem.description`
`max_length=500`): il limite allinea gli altri due rami (edit+edit, pagina Transazioni), invece di lasciare righe che una modifica non
salva più. Residuo di chiarezza (W-B70, sotto): l'unione non avvisa, e `string_too_long` non è tradotto (`PYDANTIC_BUILTIN_KEYS`).

1. ✅ **Rossi** (2026-10-17): `TestTheResolvedFieldsAreTyped` in `test_transaction_decimal_places.py` (44 test): 21 rossi, 23 verdi
   (carico 35,6), ognuno per il contratto mancante. Oltre ai 500 attesi, due difetti di oggi: dei tag mandati come testo (`"a, b"`) si
   salvano `'a,,, ,b'` (`tags_to_csv` unisce i caratteri), e una descrizione lista fallisce al flush (`ProgrammingError`, un 500). Il
   costo `"12"` e `{"amount": "1"}` erano già verdi con la cattura del passo 2 di SEC7-3; il `null` esplicito del costo su un TRANSFER dà
   `costBasisRequired` (fissato).
2. ✅ **Cura** (2026-10-17): `files/scripts/h41_cure.py --apply` (3 file).
   > **⚠️ Fuori pista**: un import circolare (`batch.py` → `transactions.py` → `type_metadata.py` → `batch.py`): `validate_tags_list` si
   > importa dentro il validatore, col `# noqa: PLC0415 — avoid circular import` come `schemas/provider.py:240`, senza spostare né
   > riesportare nulla; provati i tre ordini d'import e `backend.app.main`. Nessun comando era partito nella corsia.
   > `api sync` (17/10 08:0x): exit 0, nessun file tracciato cambiato; il client generato non tipizza i corpi del batch, quindi il
   > `Record<string, unknown>` del frontend non cambia.
3. ⏳ **Verdi**: `services transaction-decimal-places` 194 (150 + 44), `schemas transactions` 126 (08:04, carico 27); `front check`
   (08:2x): svelte-check 0 errori, 0 avvisi, prettier pulito. Resta il giro completo.
   > **⚠️ Fuori pista**: `front check` l'ho lanciato senza la porta del carico, ed è partito a 70,9 (il minuto; la regola vuole < 50 per i
   > controlli leggeri). Il risultato vale, la regola no: da qui ogni controllo passa da `sec73_light.sh` o da un `gate` esplicito.
   > **Riassegnazione** (coordinatore, 17/10 08:1x): il cuore di W-B69 (la guardia dell'insieme in `_auto_cost`, `UnreadablePoolError`,
   > `delete_by_broker`, le gambe sole) va a **MF**; a me resta la parte del batch (`autoCostUnreadable` negli stadi), dopo SEC7-3, e la
   > revisione del lotto di MF. Il cucito che ho chiesto: `_compute_wac_for_auto_items(..., unreadable=lista)` raccoglie per riga in
   > `auto_cost.py` (file di MF). Materiale a MF: `files/wb69_for_mf/` (la mia bozza, la metà dei rossi).

### W-B71, W-B72, W-B74 — analisi (2026-10-17, sola lettura, HEAD `eced298f8`)

Richiesta del coordinatore (17/10 08:36): analisi in sola lettura durante l'attesa dello slot; li faccio dopo il giro completo e
l'entrata, nell'ordine che scelgo.

#### W-B71 — 500 ai bordi del calendario (suggerimenti, gap-fix)

**Stato reale**: tre punti fanno `data ± timedelta` su una data della richiesta, senza limiti:
- `services/transactions/promotion.py:315-316`, `promote_suggest_bulk`: `inp.date ∓ timedelta(days=tolerance_days)` (0–30, 7 di
  default; `TXPromoteSuggestInput.date` qualsiasi);
- `services/transactions/event_suggestions.py:63-64`: `req.date ∓ timedelta(days=req.tolerance_days)` (0–7, 0 di default:
  con 0 nessun overflow);
- `services/transactions/balances.py:151`, `get_balances_at_end_of`: `as_of + timedelta(days=1)`, chiamato dal gap-fix BRIM
  (`services/brim/brim_gap_fix.py:74`, `as_of` dei punti di controllo della richiesta, `schemas/brim.py:794/806`).
Con `0001-01-01` o `9999-12-31` un `OverflowError`: un 500 per quella richiesta (niente memoria né CPU).

**Disegno**: un aiuto `shift_date(d, days)` in `utils/datetime_utils.py` che satura a `date.min`/`date.max` invece di alzare, nei
tre punti. Non un 422 sugli input: le due richieste di suggerimento sono a lotti (le bozze del Bulk), e una sola riga col giorno
sbagliato toglierebbe i suggerimenti a tutte; il salvataggio la rifiuta comunque (N74). Per il gap-fix, `date.max` come «fine del
giorno» prende tutte le righe: lo stesso significato. Rossi: le tre richieste ai due bordi (oggi 500), guardie dentro i bordi.
**Peso**: piccolo (~1 ora con i test).

#### W-B72 — il costo unito su entrambe le righe di una coppia di cassa

**Stato reale**: `_apply_promote_cost_basis` (`batch_creates.py`) mette il costo sulla gamba di quantità positiva, o su
**entrambe** quando nessuna l'ha (coppia di cassa: FX_CONVERSION, CASH_TRANSFER), dopo la pulizia di `cost_basis_allowed` e dopo
`_promoted_state_issues` (che controlla le regole senza i campi uniti): nessun controllo lo vede. Non sbaglia i numeri:
`cost_movement_from_transaction` (`financial_math/average_cost.py`) esce prima su una quantità 0, quindi il costo resta rumore
salvato (lista, export, backup). Solo da un client dell'API: l'interfaccia manda solo descrizione e tag. **Più largo del
reperto**: create e update non rifiutano un `cost_basis_override` su un tipo che non ne prende (la regola 12 guarda solo
`cost_basis_mode`); l'update lo scrive sempre (`batch_edits.py:270`), la create anche (`batch_creates.py:51`). I plugin BRIM lo
mettono solo su un ADJUSTMENT in entrata (Crédit Agricole `:1079`, Intesa `:389`), il frontend solo dove `cbAllowed`.

**Disegno** (decisione da prendere, D-W72-1): (a) solo la promozione: un costo unito non nullo quando nessuna gamba ne prende
(`cost_basis_allowed(target_type, quantity)`) → issue della promozione; oppure (b) **ogni scrittura** (consigliata): la regola 12
estesa a `cost_basis_override` (create, update che lo imposta, promozione), codice nuovo `costBasisNotAllowed` `{type, qty}` (4
lingue), nessun plugin né l'interfaccia toccati; le righe già salvate restano (un update che non tocca il costo passa). Rossi per
ciascuna via, guardie sui tipi che lo prendono. **Peso**: piccolo-medio (~1,5 ore con (b)).

#### W-B74 — una riga illeggibile e il giro dei saldi

**Stato reale**: due facce. (1) **Nella finestra del giro** (`_validate_broker_balances`, `balances.py`): una quantità o un importo
letto `None` (W-B58) entra in `tx.amount != 0` (vero) e poi in una somma: `TypeError`, che `validate_balances`
(`transaction_batch_stages.py`) rende «Balance validation error: …» senza codice, indice -1. (2) **Prima della finestra**, peggio:
`_get_balances_before_date` passa da `cash_movement_from_transaction` (`financial_math/native_cash.py:95`: un importo `None` →
nessun movimento) e `position_quantities` (`ledger_totals.py:100`: `not quantity` → saltata): la riga **sparisce in silenzio**, e il
saldo d'inizio è sbagliato (un prelievo illeggibile prima di `from_date` fa sembrare la cassa più alta: un batch che andava
rifiutato passa, o il contrario). Nemmeno la lista le mostra: `TXReadItem.quantity` è obbligatorio e `Currency(amount=None)` è
rifiutato (W-B63).

**Disegno**: all'inizio di `_validate_broker_balances`, il conteggio delle righe del broker (fino all'ultima data del giro) con un
importo (con valuta) o una quantità (con asset) letti `None` → `BalanceValidationError` con un codice nuovo `ledgerUnreadable`
`{brokerId, count}`, sulla riga del batch che ha portato al giro; messaggio in 4 lingue che non manda alla lista (che non le mostra)
ma all'amministratore. Lo stesso conteggio in `get_balances_at_end_of` (gap-fix: oggi le salta). Un solo aiuto di query, vicino a
quello di MF per W-B69 (`_unreadable_pool_rows`) se il suo lotto è entrato: da condividere, non da copiare. La via d'uscita per
l'utente resta W-B63 (D-W63-1, col developer). Rossi: una riga illeggibile prima e dentro la finestra (oggi: saldo sbagliato
accettato, e il codice mancante), guardie su un registro leggibile. **Peso**: medio (~2 ore con i18n e doc).

#### Ordine proposto

**W-B74** (dati: un saldo sbagliato in silenzio), poi **W-B71** (meccanico), poi **W-B72** dopo D-W72-1. W-B74 dopo l'entrata
del lotto di MF, per condividere l'aiuto di query.

**Decisione** (coordinatore, 17/10 08:39): **D-W72-1 → (b)**, la regola 12 estesa a `cost_basis_override` su ogni scrittura,
`costBasisNotAllowed {type, qty}`, le righe già salvate restano: **decisione notturna N78**, da rivedere col developer. Ordine
approvato: W-B74 (dopo l'entrata di W-B69 di MF, aiuto condiviso) → W-B71 → W-B72.

**Aggiunta a W-B72** (17/10 08:4x, sola lettura): dei 22 codici delle regole di business (`PydanticCustomError` in
`schemas/transactions/transactions.py`) uno solo non ha la chiave `transactions.errors.*` in nessuna lingua:
`costBasisModeIncompatible`, il codice della regola 12 che N78 estende (l'altro, `multipleBusinessRuleErrors`, è l'involucro che il
parse del batch apre, mai mostrato). Oggi l'utente lo legge in inglese grezzo. Nel lotto di W-B72: la sua chiave (4 lingue) accanto
a `costBasisNotAllowed`, e un cancello che dia a ogni codice delle regole una chiave, come quello di W-B69 per `TXValidationCode`.
Script di W-B71 pronto (`files/scripts/wb71_cure.py`, dry run pulito su 4 file).

### W-B71 — le finestre di date ai bordi del calendario: cura ✅ (2026-10-17) — 🧊 FROZEN

**Base**: HEAD `9b23bdbfe` (dev, avanzato dal coordinatore dopo l'entrata di SEC7-3: cura `550e462a5`, giornale `b46a49385`, dev
`e609082ab`, CHANGELOG `dbc2e7225`). Disegno: sezione «W-B71, W-B72, W-B74 — analisi» qui sopra.

**Ordine cambiato** (proposto al coordinatore, 17/10 10:0x): W-B71 ora; la metà del batch di W-B69 con `EARLIEST_RANGE_START` quando
entra MF-SEC8-2; poi W-B74, poi W-B72 (N78). Perché W-B74 dopo W-B69: il suo rifiuto è per broker (una riga illeggibile rende ignoti i
saldi del broker, e la lista nemmeno le mostra), quindi ogni scenario del batch di W-B69 (una riga illeggibile nell'insieme del broker
d'origine, che si rigioca) avrebbe un secondo issue `ledgerUnreadable`: con W-B69 prima, i rossi di W-B74 si scrivono sul batch com'è
allora, e quelli parcheggiati di W-B69 non si riscrivono due volte.

1. ✅ **Rossi** (test-author `83f7167c`): `shift_date` in `test_datetime_utils.py`; il suggerimento di promozione e quello degli eventi
   con un input al `0001-01-01` e al `9999-12-31` accanto a uno ordinario (che trova ancora il suo candidato, e non a un giorno in più);
   il gap-fix con un `as_of` al `9999-12-31`.
   > **Note implementazione**: primo giro (carico 38–47): `utils datetime` 26 rossi / 13 verdi (manca `shift_date`), `services
   > brim-gap-fix` 3 rossi / 102 verdi (`OverflowError`); i due file `api` (B3.12–B3.13 in `test_transactions_batch_split_promote.py`,
   > G.4.9–G.4.10 in `test_events_suggest.py`) scritti, da girare in uno slot (la prima azione ricostruisce frontend e MkDocs).
   > **⚠️ Fuori pista** (dai dubbi del test-author, presi): (1) con `shift_date` la fine del `9999-12-31` è `date.max`, e
   > `_get_balances_before_date` conta solo `date < date.max`: una riga datata proprio `9999-12-31` (di una versione vecchia) mancherebbe →
   > `get_balances_at_end_of` diventa una query inclusiva (`date <= as_of`, `through=True`), senza spostare il giorno; (2)
   > `brim_report_sets.py` ha cinque `± 1 giorno` su date del report caricato o di righe salvate (`:164`, `:243`, `:253`, `:437`,
   > `:440`): stesso 500 con un file costruito → dentro W-B71 con `shift_date` (miei file BRIM), rossi in `test_brim_report_sets.py`.
   > Script della cura riscritto (5 file, dry run pulito); il pezzo nuovo in `files/scripts/wb71_balances_sets_part.py.txt`.
2. ✅ **Cura**: `files/scripts/wb71_cure.py` (dry run pulito su 4 file anche su `9b23bdbfe`).
   > **Note implementazione**: ordine approvato dal coordinatore (10:0x). Avanzamento a dev `91f4de9cb` (MF-SEC8-2, `e119c71bc`) chiesto
   > e fatto **prima** della cura: `EARLIEST_RANGE_START` di MF e il mio `shift_date` stanno nello stesso punto di
   > `utils/datetime_utils.py`; MF l'ha messo prima di `latest_range_end()`, quindi l'ancora dello script regge (dry run di nuovo
   > pulito). MF-SEC8-2 non tocca i file dei test di W-B71.
   > **Note implementazione** (rossi, secondo giro, 10:42–10:57, slot del coordinatore): `services brim-report-sets` 9 rossi / 265
   > verdi (`TestCalendarEdges`: i cinque punti raggiunti dalle entrate che il file già usa, ognuno con la sua guardia un giorno dentro
   > il bordo), `services brim-gap-fix` 4 rossi / 102 (`TestCalendarsLastDay`, più la riga datata proprio `9999-12-31` che deve contare
   > alla fine di quel giorno: una cura che sposta solo la data non basta), `api batch-split-promote` 1 rosso (B3.13) / 37, `api
   > events-suggest` 1 rosso (G.4.10) / 10. Il primo giro `api` ha ricostruito frontend e MkDocs (6m42s).
   > **⚠️ Fuori pista**: nel primo giro B3.13 era rosso per la ragione giusta (`promotion.py:315`, `OverflowError` nel log del server) ma
   > col messaggio sbagliato: la sonda che seguiva usava la connessione che uvicorn chiude dopo un'eccezione non gestita
   > (`httpx.ReadError`). Il test-author manda ora ogni richiesta che può dare un 500 su un client suo; rigirato pulito, broker e asset
   > cancellati. Dubbi annotati, senza azione: una correzione datata `9999-12-31` (solo da dati vecchi: N74 la rifiuta)
   > farebbe H0 = `9999-12-31` (gli avvisi `before_history_segment` lo mostrano); `delete_owned` (aiuto esistente) ferma le
   > cancellazioni al primo errore di connessione.
   > **Cura applicata** (11:00): `shift_date` in `utils/datetime_utils.py` (dopo `latest_range_end()`, `EARLIEST_RANGE_START` di MF prima),
   > i due suggerimenti, i cinque punti di `brim_report_sets.py`; `get_balances_at_end_of` con `_get_balances_before_date(...,
   > through=True)` (query inclusiva). `timedelta` non serve più in `balances.py`, `promotion.py`, `event_suggestions.py`,
   > `brim_report_sets.py`. Ruff pulito; black ha riformattato la `select(...)` lunga di `balances.py` (script non riallineato: conta il
   > diff).
3. ✅ **Verdi** (11:00–11:10, slot, carico a 5 minuti 43–49): `utils datetime` 39, `services brim-gap-fix` 106, `services
   brim-report-sets` 274, `api batch-split-promote` 38, `api events-suggest` 11, `services transaction` 104; porta libera.
4. ✅ **Doc**: `developer/frontend/state/transaction-draft.md` (la finestra del suggerimento ai bordi), `developer/backend/transactions/
   service.md` (`get_balances_at_end_of`, query inclusiva), `developer/architecture/patterns/brim_plugin_guide.md` (i giorni attorno a H0
   e alla copertura, tenuti ai bordi). Nessuna pagina utente: il comportamento visibile è «nessun suggerimento» invece di un errore.
5. ⏳ **Simulazione e handoff**.

### W-B69 — la metà del batch (W) e il pavimento di N74 condiviso ✅ (2026-10-17) — 🧊 FROZEN

**Base**: HEAD `2dddaa95d` (dev con W-B71 dentro: `b801dc687` + `0955164a6` → `1431e20df`, CHANGELOG `2dddaa95d`). Il cuore di W-B69 è
di MF (`1b4e4a27d`, rivisto qui sopra); a me il batch, col pavimento condiviso `EARLIEST_RANGE_START` (MF-SEC8-2, già in dev).

1. ✅ **Rossi**: la mia metà ripresa da `files/wb69_mine/` (il file non era cambiato dalla base del parcheggio; diff identico): `services
   transaction-cost-basis-rule` **33 rossi**, 104 verdi (11:15, carico 24); ogni rosso ora fallisce su un `UnreadablePoolError` che esce
   dal batch (lo stato intermedio di MF: un 500), cioè per il rifiuto del batch che manca. Il rosso del pavimento (test-author
   `3f86d648`, `TestTheDateFloorIsTheReplayFloor`): «N74's floor is the replay floor, EARLIEST_RANGE_START (MF-SEC8-2), never a copy:
   transaction_batch_stages still defines its own TRANSACTION_DATE_MIN = 1900-01-01; transaction_batch_stages has no
   EARLIEST_RANGE_START» (carico 35).
2. ✅ **Cura**: `files/scripts/wb69_batch_cure.py --apply` (6 file) e `files/scripts/wb69_batch_i18n.sh`
   (`transactions.errors.autoCostUnreadable`, 4 lingue, plurale ICU su `{count}`, il FR col ramo `many`). `compute_wac_and_fx_issues`
   passa la lista al cucito di MF e fa di ogni elemento l'issue `autoCostUnreadable` sulla riga (`cost_basis_override`, `params
   {"count": N}`, nessun id); il `_handover_cost` della gamba che cede di una divisione lo prende per riga (operazione `split`, `ref_id`
   la gamba). `TXValidationCode.AUTO_COST_UNREADABLE`. `transaction_date_bounds()` rende `EARLIEST_RANGE_START`, `TRANSACTION_DATE_MIN`
   tolto (nessun test lo importava).
   > **⚠️ Fuori pista**: ruff C901 su `compute_wac_and_fx_issues` (11 > 10) con le due prese: il giro della divisione estratto in
   > `_cost_split_handovers()`, stesso comportamento, dentro lo stesso `if` (niente `noqa`).
3. ✅ **Verdi** (11:19–11:20, carico 23–25): `services transaction-cost-basis-rule` 137, `services transaction-decimal-places` 195,
   `services auto-cost-unreadable-pool` 17 (di MF), `services lone-transfer-legs` 20, `services transaction` 104; `i18n check` (5025
   chiavi), Vitest 107 (ICU per lingua e il risolutore). Non girati i file `api`: la sorgente i18n cambiata rende vecchia la build del
   frontend (ricostruzione); il batch lo esercitano i test dei servizi, in processo.
4. ✅ **Doc**: `wac.md#unreadable-pool` (il paragrafo finale: il batch ora rifiuta), `split_promote.md` (il rifiuto della divisione e la
   riga della tabella dei codici), `service.md` (il pavimento di N74 è `EARLIEST_RANGE_START`).
5. ⏳ **Simulazione e handoff**.

### W-B74 — una riga illeggibile e il giro dei saldi ✅ (2026-10-17) — 🧊 FROZEN

**Base**: HEAD `6eaf0774c` (dev con la metà del batch di W-B69: `18fc070c8` + `729d6edee` → `eee5dad17`; CHANGELOG `6eaf0774c`, la riga
di MF estesa). Disegno: sezione «W-B71, W-B72, W-B74 — analisi».

1. ✅ **Rossi** (test-author `6341ec42`, 11:2x–11:4x, carico 32–45): **17 nuovi** — `test_transaction_service.py`
   `TestWB74AnUnreadableRowInTheReplay` (a: un WITHDRAWAL illeggibile prima del batch, oggi il batch passa con 20 dove il saldo è −80;
   b: dentro la finestra, oggi l'errore senza codice «Balance validation error: unsupported operand…»; c: la quantità; d: il conteggio,
   una riga con due valori illeggibili conta 1; e: i codici), `test_brim_gap_fix.py` (`get_balances_at_end_of` ×3, `compute_gap_fix`
   ×2: oggi propone un WITHDRAWAL che duplica la riga che non legge); **8 guardie** verdi (broker con scoperto e allo scoperto: niente
   giro; un altro broker; il registro leggibile; righe dopo `as_of` o fra quelle da cancellare); **24 aggiornamenti di contratto** dei
   rossi di W-B69 (il batch che rigioca il broker d'origine porta anche `ledgerUnreadable`: esattamente due issue; la guardia
   `another-asset-create` diventa un test proprio, un solo `ledgerUnreadable`). I casi del costo salvato illeggibile restano a un issue:
   nessun saldo legge un costo, e così fanno anche da guardia (il conteggio del giro senza il costo).
   > **Note implementazione**: nessun altro test cambia (grep del test-author): il test della quantità infinita cancellata dal batch
   > resta verde perché `validate_balances` fa il flush prima del giro, e il conteggio non vede più la riga cancellata; quelli di MF non
   > passano dal giro. Dubbi annotati senza azione: `BrokerService.update_bulk` rigioca da capo quando si stringono i flag di un broker
   > e risponde `error=str(e)` (in inglese, come già il saldo negativo su quella via); una sola issue di saldo per batch (il primo
   > broker): come prima.
2. ✅ **Cura**: `files/scripts/wb74_cure.py --apply` (nuovo `backend/app/services/transactions/unreadable_rows.py` con
   `count_unreadable_rows()` e `UnreadableLedgerError`; `auto_cost._unreadable_pool_rows` di MF passa da lì, condiviso e non copiato;
   `balances.py`: il conteggio all'inizio di `_validate_broker_balances`, dopo i ritorni anticipati, → `BalanceValidationError`
   `ledgerUnreadable {brokerId, count}` all'indice −1, e in `get_balances_at_end_of` → `UnreadableLedgerError`; `brim_gap_fix._state_at`
   → `BRIMLedgerUnreadable` (409, `ledger_unreadable`, in `brim_report_sets.py` coi fratelli); `TXValidationCode.LEDGER_UNREADABLE`) e
   `files/scripts/wb74_i18n.sh` (`transactions.errors.ledgerUnreadable`, 4 lingue, `{brokerName}` dal risolutore, plurale su
   `{count}`, il FR col ramo `many`). Black ha rimesso su una riga il `raise` lungo di `brim_gap_fix.py`.
3. ✅ **Verdi** (11:51–12:00, carico 33–47): `services transaction` 120, `services brim-gap-fix` 115, `services
   transaction-cost-basis-rule` 137, `services auto-cost-unreadable-pool` 17, `services lone-transfer-legs` 20, `services
   transaction-decimal-places` 195, `services broker` 81, `services financial-math` 1145 (le frontiere dei livelli); `i18n check`
   (5026 chiavi), Vitest 70 (ICU per lingua, il risolutore).
4. ✅ **Doc**: `balance_validation.md` (il terzo codice prima del giro), `service.md` (il modulo nuovo nella tabella,
   `get_balances_at_end_of` che rifiuta), `wac.md` (il conteggio condiviso), `brim_plugin_guide.md` (il 409 `ledger_unreadable` del
   gap-fix).
5. ⏳ **Simulazione e handoff**.

#### Revisione di Z-28, la metà BRIM — ✅ (2026-10-17)

`3a3d5ab1c` (`fix(locks): refuse symlinked lock files`), dopo il fatto, in sola lettura: `brim_provider._acquire_file_lock` apre con
`os.open(…, O_RDWR | O_CREAT | O_NOFOLLOW, 0o600)` e chiude il descrittore se `flock` alza; `_release_file_lock` sblocca e chiude in
un `finally`. L'unico chiamante, `_broker_metadata_lock`, tratta il descrittore come opaco, e un'apertura rifiutata alza prima di
scrivere `held[key]` (nessuna profondità rimasta appesa); la chiave è `broker_<int>`, nessun input dell'utente. I test
(`test_brim_parse_race.py`) coprono il symlink pendente e quello a un file esistente, e il modo. Nota senza azione: `O_NOFOLLOW`
protegge l'ultimo componente; una cartella `.locks` simbolica verrebbe seguita, come per i lock del backup e dello scheduler.

### W-B72 — un costo dove il tipo non ne prende (N78): cura ✅ (2026-10-17) — 🧊 FROZEN

**Base**: HEAD `e908f0d4f` (dev con W-B74: `bd5deeb36` + `29f544846` → `80cee9c2d`). **Decisione notturna N78** (coordinatore, 08:39, da
rivedere col developer): la regola 12 estesa a `cost_basis_override` su ogni scrittura, codice `costBasisNotAllowed {type, qty}`, le
righe già salvate restano. Solo TRANSFER e ADJUSTMENT a quantità > 0 prendono un costo (`cost_basis_allowed`).

1. ✅ **Rossi, primo giro** (test-author `5fdd8bfa`): create BUY, ADJUSTMENT −5 e una gamba di FX_CONVERSION con un costo; update che lo
   mette su un BUY salvato; promozione di una coppia di cassa col costo unito; la chiave di `costBasisModeIncompatible` e il cancello su
   tutti i codici delle regole; guardie (ADJUSTMENT +5, TRANSFER in entrata, Auto con la valuta, un BUY vecchio col costo che cambia solo
   la descrizione, la coppia d'asset, il `null`). `services transaction-cost-basis-rule` 16 rossi / 147, `transaction-decimal-places`
   2 rossi / 199. Grep di test, popolamento, E2E e plugin: nessuno manda un costo dove non si prende (i plugin BRIM solo su un
   ADJUSTMENT in entrata, il form passa da `cbAllowed`).
   > **⚠️ Fuori pista**: il test-author ha trovato due problemi della N78 letterale.
   > - **(a) Conflitto con le decisioni 4 e 47.** `test_split_keeps_the_cost_an_update_of_the_same_batch_gives_the_giving_leg`
   >   dà alla gamba che cede di uno split (un ADJUSTMENT −4) un costo con un update senza modo: è il costo di consegna della
   >   decisione 47, che il motore FIFO legge su ADJUSTMENT_OUT (`fifo/engine.py:244`). La N78 letterale lo rifiuterebbe.
   > - **(b) Parametri persi.** Un errore di regola **da solo** arriva senza `params`: `_parse_lenient` li tiene solo per quelli
   >   impacchettati (`multipleBusinessRuleErrors`). Oggi `cashNonzero` & c. arrivano all'app col `{type}` vuoto.
   >
   > Chiesto al coordinatore.
2. ✅ **Decisione del coordinatore** (17/10): **(a), la N78 raffinata**. La regola 12b rifiuta un costo che la richiesta mette, senza
   modo, dove `cost_basis_allowed` è falso, **tranne su un ADJUSTMENT a quantità < 0** (il costo di consegna della 47, e l'update dello
   stesso batch della 4: decisioni del developer, che vincono sulla N78). Approvati anche:
   - un errore di regola **solo**, a livello di modello, con un contesto di dati semplici, tiene il contesto come `params`; gli errori di
     campo di pydantic e `value_error` (il contesto porta l'eccezione) restano `None`;
   - il vecchio `promote_transfer` rifiuta `cost_basis_override` su un FX_CONVERSION, invece di lasciarlo cadere in silenzio, con il
     suo rosso.
   La raffinatura è registrata sotto la N78.
3. ✅ **Rossi, secondo giro** (stesso test-author):
   - `adjustment-out` esce dai casi rifiutati e diventa una guardia (create, e update su un ADJUSTMENT −4 salvato);
   - il caso di regola 12 col modo fissa anche i `params` `{type: BUY, qty: 5}` (spostato nella classe
     `TestN78AModeLetsRule12SpeakAlone`; la vecchia classe delle guardie ora si chiama `TestN78GuardsStrayCostsAndNulls`);
   - in `test_transaction_service.py`: la classe `TestParseLenientParamsOfALoneError`, con un rosso sui `params` di un errore
     solo (`qtyPositive` → `{type: BUY}`) e tre guardie (`string_too_long`; `value_error` di uno split con `id_a == id_b` e di
     una promozione senza riferimento a B, `params` `None`); il rosso di `promote_transfer` su FX_CONVERSION con un costo
     (`TestTransferPromotion::test_promote_to_fx_conversion_with_a_cost_basis_is_refused`).

   Prove: `services transaction-cost-basis-rule` 17 rossi / 147 verdi, `services transaction` 2 / 123,
   `transaction-decimal-places` invariato (2 / 199). Ogni rosso fallisce per il motivo che dichiara: costo salvato, `params`
   `None`, coppia ricreata col costo perso. Le 10 + 3 guardie sono verdi oggi.
4. ✅ **Cura applicata** (17/10), `files/scripts/wb72_cure.py --apply` su 6 file (+67/−3), più `files/scripts/wb72_i18n.sh` (le due
   chiavi in `transactions/{en,it,fr,es}.json`, +3/−1 per lingua). `ruff check` e `black --check` puliti sui 6 file (prova
   aspettando il carico < 50). Prima di applicare, verificato che nessuna scrittura legittima manda un costo dove la 12b lo rifiuta:
   - i plugin BRIM: Credit Agricole solo su un ADJUSTMENT in entrata, azzerato a ogni riga; Intesa col modo `manual`; il gap-fix
     solo con `missing > 0`; Generic CSV non lo mappa;
   - il ripristino dei backup copia file, non passa dal batch;
   - il frontend: form, coppie, Bulk e import passano da `cbAllowed` (`txPayloadHelpers.ts`, `opToTxFields`);
   - i test: un esame dell'albero sintattico (`files/scripts/wb72_scan_payloads.py`) su 17 file Python, e una lettura dei 13
     E2E che mandano un costo. Nessun payload su un tipo che non ne prende, se non i rossi di W-B72.

   Il cancello dei codici: oggi mancava solo `costBasisModeIncompatible` (1 di 21 codici); con la cura entra
   `costBasisNotAllowed` (22). `validation_codes` di `GET /transactions/types` elenca solo `TXValidationCode` (codici del batch):
   nessuna aggiunta. Nessun test fissava `params` `None` su un errore solo (grep dei test di API, servizi, schemi, esterni).

   Parti della cura:
   - la regola 12b con `cost_basis_set` e l'eccezione ADJUSTMENT −q, documentata nella docstring della funzione;
   - la create e l'update che passano `cost_basis_set`;
   - `_resolved_cost_issues` per la promozione;
   - `_lone_error_params` in `_parse_lenient` (loc vuota, contesto di soli str/int/float/bool/None);
   - in `promote_transfer` il rifiuto su FX_CONVERSION, e un commento nello schema della richiesta.

   I18n, `files/scripts/wb72_i18n.sh`: le due chiavi nello stile di `costBasisRequired`, **senza `{qty}`** (una riga salvata
   lo stampa `3.0000000000`). Il lato è detto a parole; i `params` tengono `qty` per i client dell'API.
5. ✅ **Verdi** (17/10, 12:50–12:58, `files/scripts/wb72_light.sh`, una prova alla volta col carico < 50; log `files/logs/wb72_*.log`):

   | Prova | Esito |
   |---|---|
   | `services transaction-cost-basis-rule` | 164 verdi (i 17 rossi inclusi) |
   | `services transaction` | 125 verdi (i 2 rossi inclusi) |
   | `services transaction-decimal-places` | 201 verdi (i 2 rossi inclusi) |
   | `services brim-create-transaction` | 14 verdi |
   | `schemas transactions` | 126 verdi |
   | `services brim-gap-fix` | 115 verdi |
   | `external brim-providers` | 736 verdi, 1 saltato (DEGIRO Windows-1252, per costruzione) |
   | `utils gate-i18n-catalog` | 176 verdi |
   | `utils gate-i18n-usage` | 195 verdi |
   | `dev.py i18n check` | stretto, 5 033 chiavi |
   | Vitest `catalogIcuLocale.test.ts` + `resolveValidationMessage.test.ts` | 70 verdi |

   **Non eseguiti**: i test `api` (le sorgenti i18n cambiate rendono vecchia la build del frontend, che il server ricostruisce: serve
   uno slot) e gli E2E. Nessun E2E manda un costo dove la 12b lo rifiuta (vedi il passo 4). Il livello API serializza lo stesso
   `TXBatchResponse` dei test di servizio, e i `params` nuovi sono dati semplici. Li copre il prossimo `all-backend`.
6. ✅ **Doc** (docs-writer `a9c358d1`, 17/10; solo EN, pagine per sviluppatori senza traduzioni):
   - `service.md` «Per-type rules»: la riga 12b nella tabella; il paragrafo della 12b (chiamanti di `cost_basis_set`,
     l'eccezione, l'`elif`, il costo salvato mai giudicato, il `null`); i `params` di un errore solo (`_lone_error_params`);
     i due messaggi e il cancello;
   - `wac.md`: «Persisted Cost Basis» (la 12b e la sua eccezione) e «Promote boundary» (la coppia di cassa);
   - `split_promote.md`: la gamba che cede, il passo 3 (`_resolved_cost_issues`), la riga `cost_basis_override` della tabella
     di `resolved_fields`, la tabella dei codici, la vecchia promozione;
   - `brim_plugin_guide.md`: una frase alla fine dell'avviso «PER-UNIT»; un costo su un'altra riga rifiuta la riga.

   Prove: `mkdocs build` stretto con uscita 0 e nessun avviso; `check-links` con 97 collegamenti validi e 0 rotti. Rivisto da
   me contro il codice; i `params` degli update li verifico a `batch_edits.py:205`.
7. ✅ **Simulazione** (17/10, 13:05–13:09): `files/scripts/sim_cherry_pick.sh dev_release2 --docs` sui 19 file, dev `4e11fabec`
   (HEAD `e908f0d4f` antenato): 0 conflitti; ruff e black sui 9 `.py` uniti e `json.load` sui 4 cataloghi puliti; `mkdocs build`
   stretto e `check-links` con uscita 0 sull'albero simulato. Il `wac.md` di dev (J-12/N81, il paragrafo dei due wipe) si unisce da
   solo, venti righe sotto il nostro. `git diff --check` pulito; porta 6184 libera. Handoff FROZEN inviato al coordinatore.
8. ✅ **Dopo l'ingresso: un rosso di dev** (17/10, trovato da X; ingresso `e71b68d50` + `19c2f596e` → `7bc66c7ca`). `front-utility
   core-unit` → `src/htmlInterpolation.gate.test.ts`, «finds no markup in any translation outside the reviewed sanitized keys».
   Le due chiavi nuove portavano `<b>…</b>` in tutte e 4 le lingue, sul modello di `costBasisRequired`. Il cancello ammette markup
   solo nelle tre chiavi riviste di `SANITIZED_MARKUP_KEYS` (tutte `transactions.errors.*`, rese da `resolveIssueMessage` con
   `{@html sanitizeHtml(…)}`).
   - **Cura**: testo semplice, la scelta preferita dal coordinatore: le stesse parole senza `<b>`, nessuna eccezione nuova nel
     cancello. Script `files/scripts/wb72_plain_i18n.sh`, con `dev.py i18n update`.
   - **Prove** (carico < 50): il cancello da solo con Vitest, 26 verdi; `dev.py i18n check` stretto, 5 048 chiavi;
     `front-utility core-unit` 207 file, 8 378 verdi.

   > **⚠️ Fuori pista**: io non avevo fatto girare `core-unit`. Le mie prove i18n erano `gate-i18n-catalog`, `gate-i18n-usage`,
   > `i18n check` e il Vitest ICU, ma il cancello dell'HTML sta in `core-unit`. Regola per i lotti con chiavi i18n nuove: girare
   > anche il cancello dell'HTML (`src/htmlInterpolation.gate.test.ts`) o `core-unit`.

> **Nota, nuova voce W-B75** (fuori perimetro, non toccata): `BRIMProvider._create_transaction` mette in `params` il contesto di ogni
> errore solo così com'è. Quello di un `value_error` porta l'oggetto eccezione, e la risposta non si serializza (verificato:
> `PydanticSerializationError` su `BRIMValidationIssue.model_dump(mode="json")`). Oggi non è raggiungibile: i plugin passano istanze di
> `Currency` (non rivalidate) e liste di stringhe. È latente per un plugin nuovo. Cura: lo stesso filtro dei dati semplici.

### W-B67 — il costo Auto sulla riga sbagliata: analisi (2026-10-17, sola lettura, HEAD `f731d462e`)

**Base**: HEAD `f731d462e` = dev con W-B72 (`e71b68d50` + `19c2f596e` → `7bc66c7ca`, CHANGELOG `f731d462e`). Via del coordinatore:
«W-B67, reds first».

**Difetto 1, la riga** (la voce del backlog, confermato nel codice). `_compute_wac_for_auto_items` (`auto_cost.py:47`) trova la
riga di una create in Auto con `_find_created_tx_for_wac` (`:207-231`). Con un `link_uuid` la prende da `link_uuid_map` per indice
(giusto: le coppie TRANSFER non hanno il difetto). Senza, cerca **l'ultima riga** con lo stesso broker, asset, data e tipo
(`order_by(id.desc()).limit(1)`). Quindi:

- due ADJUSTMENT Auto non collegati, stessa chiave: il secondo riceve il costo due volte, il primo mai. Si salva senza costo, perché
  il controllo `costBasisRequired` salta le create in Auto (`batch_costs.py:182`);
- un Auto seguito da un Manuale con la stessa chiave: il costo Manuale è sovrascritto con la media, l'Auto resta senza;
- un Manuale seguito da un Auto: la riga trovata è quella giusta (id più alto), nessun difetto.

La creazione conosce già la riga di ogni indice (`apply_creates`, `batch_creates.py:41-62`), ma la tiene solo in `link_uuid_map`
per le righe collegate.

**Difetto 2, l'ordine e la diluizione** (trovato nell'analisi, non nel backlog). Il gruppo di una riga Auto è il suo broker fino
alla sua data, senza sé stessa (`_auto_cost_source`). Ci entrano le altre righe Auto **dello stesso batch non ancora costate**.
Un'acquisizione senza costo vi entra a zero (`ADD_UNKNOWN_COST`, `average_cost.py:463`; `portfolio_service.py`, «enters at
zero»), e la media si diluisce in base all'ordine degli indici.

Esempio: un BUY di 10 a 100 EUR il giorno D−1, poi due ADJUSTMENT +5 in Auto il giorno D.

| | A (indice 0) | B (indice 1) |
|---|---|---|
| oggi | nessun costo | 66,666667 |
| solo la mappa | 66,666667 (B a zero) | 88,888889 |
| P1 | 100 | 100 |

Due Auto in date diverse in ordine d'indice inverso (D+1 prima di D) danno, oggi e con la sola mappa, 66,666667 a quello di D+1.

**Proposta D-W67-1 (P1)**:
- (a) la mappa indice → riga dalla creazione (`context.created_by_index`), senza ricerca per campi; `_find_created_tx_for_wac` va via;
- (b) le righe Auto calcolate nell'ordine della data del loro gruppo (`as_of` di `_auto_cost_source`), poi nell'ordine originale;
- (c) le righe Auto del batch non ancora costate, salvo quelle legate a uno split (che restano movimenti di riscalatura), fuori dai
  gruppi delle altre.

Risultato: i costi che le righe avrebbero salvate una alla volta in ordine di data. Nell'esempio, 100 e 100. L'ordine di
`wac_results` nella risposta non cambia. Alternativa **P2**: solo (a); toglie il difetto 1 e lascia il 2 (66,67 / 88,89).

**Rossi proposti** (servizio, `execute_batch` come `POST /transactions/commit`; il `world` di
`test_transaction_cost_basis_rule.py` ha già 10 unità a 100 EUR):

1. due Auto +5 stesso giorno: entrambe salvate con 100 (oggi A senza costo, B 66,666667);
2. Auto e poi Manuale a 50, stesso giorno: il Manuale tiene 50, l'Auto 83,333333 (il Manuale è nel gruppo; lo stesso giorno conta,
   come documentato). Oggi il Manuale diventa 66,666667 e l'Auto resta senza. Non dipende dalla decisione;
3. (P1) due Auto in D e D+1, indici in ordine inverso: entrambe 100;
4. `wac_results` per indice col valore della propria riga.

Guardie: un Auto solo; Manuale e poi Auto; una coppia TRANSFER in Auto; un ADJUSTMENT legato a uno split in Auto e un Auto +q lo
stesso giorno (lo split resta nel gruppo).

**Superfici**: `auto_cost.py`, `batch_creates.py`, `transaction_batch_context.py`, `batch_costs.py`; doc `wac.md` («Inline WAC»),
`service.md` (contesto condiviso, se elenca i campi). Nessun i18n, nessuna API. **Ordine**: decisione → rossi → cura → verdi →
doc → handoff.

### W-B67 — cura ✅ (2026-10-17) — 🧊 FROZEN

1. ✅ **Decisione D-W67-1 → P1** (coordinatore, 17/10, registrata come **N84**): ogni create sulla propria riga; le righe Auto
   calcolate nell'ordine della data del loro gruppo, poi per indice; le righe Auto del batch non ancora costate (salvo quelle legate
   a uno split) fuori dai gruppi delle altre. La regola: lo stesso costo che avrebbero salvate una alla volta in ordine di data.
2. ✅ **Rossi** (test-author `181447ad`, solo `test_transaction_cost_basis_rule.py`, +315 righe). Le classi:
   - `TestWB67EachAutoCreateCostsItsOwnRow`, 3 rossi:
     - Auto e poi Manuale: il Manuale tiene 50, l'Auto 1250/15;
     - due Auto con la stessa chiave: 100 e 100;
     - Auto legato a uno split e Auto +q: `wac_results` per indice;
   - `TestWB67AutoRowsAreCostedInDateOrder`, 1 rosso: D+2 e D con indici inversi e un BUY in D+1, 175 e 100;
   - `TestWB67GuardsWhereTodaysSearchFindsTheRow`, 3 guardie:
     - un Auto solo;
     - Manuale e poi Auto;
     - **nuova**: la riga legata a uno split calcolata per ultima resta nel gruppo di una gamba TRANSFER Auto dello stesso giorno.
       Il rosso 3 da solo non fissava l'eccezione di (c).

   La guardia TRANSFER è citata, non duplicata (`TestAutoCost[transfer_in]`, `TestWB69Guards…`).

   Prove (carico < 50): `… transaction-cost-basis-rule WB67` 4 rossi / 3 verdi; l'azione intera 4 / 167. Oggi:

   | Rosso | Esito oggi |
   |---|---|
   | 1 | Auto senza costo, Manuale 66,666666666667 |
   | 2 | riga 0 senza costo, riga 1 66,666666666667 |
   | 3 | `wac_results` [0: 50, 1: 50] |
   | 4 | la riga di D+2 a 150, cioè «oggi» |

   > **⚠️ Fuori pista**: le note del test-author.
   > - (1) Il mio conto «solo la mappa» per il rosso 2 era sbagliato: è 1000/15 e 88,888888888889, non 1500/15.
   > - (3) Il pareggio fra una create e un update con la stessa data: la cura usa la posizione (le create per indice, poi gli
   >   update), ora scritto nella docstring.
   > - (4) Un update in Auto conta come non ancora costato (lettura di N84): il suo costo salvato è quello che sostituisce, e le
   >   righe dello stesso giorno arrivano alla media coerente con sé stessa (scritto nella docstring).
   > - (5) La cache: già vista, ogni riga calcola con esclusi diversi.
3. ✅ **Cura applicata** (17/10, prima dei verdi delle 13:36), `files/scripts/wb67_cure.py --apply` su 4 file (+56/−68), più la docstring sul pareggio e
   sugli update. `ruff check` e `black --check` puliti.
   - `transaction_batch_context.py`: il campo `created_by_index`;
   - `batch_creates.apply_creates`: lo riempie dopo il flush;
   - `batch_costs.compute_wac_and_fx_issues`: lo passa;
   - `auto_cost._compute_wac_for_auto_items`: la riga dalla mappa; `split_linked_ids` una volta per tutte; le fonti calcolate
     prima; l'ordine `(as_of, posizione)`; `pending` escluso dal gruppo (`excluded + others`) e tolto solo quando il costo è
     scritto, così una riga che fallisce (gruppo illeggibile, cambio mancante) resta fuori dai gruppi delle altre e non vi entra
     a zero; i risultati nell'ordine degli elementi. Via `_find_created_tx_for_wac`.

   La cache di `compute_wac_iterative` (chiave con gli id esclusi e l'impronta id + `updated_at`, cieca ai costi scritti nella
   sessione) non dà un risultato stantio: ogni riga Auto calcola con un insieme di esclusi diverso.
   Caso limite noto: una gamba TRANSFER ricevuta prima della sua partner è ordinata con la data della partner (la data del suo
   gruppo), come vuole N84.
4. ✅ **Verdi** (17/10, 13:36–13:42, `files/scripts/wb67_light.sh`, una prova alla volta col carico < 50; log
   `files/logs/wb67_*.log`):

   | Prova | Esito |
   |---|---|
   | `services transaction-cost-basis-rule` | 171 verdi (i 4 rossi inclusi) |
   | `services transaction` | 125 verdi |
   | `services transaction-decimal-places` | 201 verdi |
   | `services auto-cost-unreadable-pool` (di MF) | 17 verdi |
   | `services lone-transfer-legs` | 20 verdi |
   | `services orphan-transfer-numbers` | 21 verdi |
   | `services roi-fifo-utils` (con `test_wac_rounded_to_column.py`) | 1 312 verdi |
   | `services broker` | 81 verdi |

   **Slot del coordinatore prima dell'ingresso** (17/10, 13:50–14:00, `files/scripts/wb67_slot.sh`; il via con 5 minuti di carico
   < 50, ogni passo con il carico a 1 minuto < 70; log `files/logs/wb67_slot_*.log`):

   | Prova | Esito |
   |---|---|
   | `test db populate --force` | uscita 0 |
   | `api transactions-wac` (`test_wac_inline.py`, con la ricostruzione del frontend) | 20 verdi |
   | `api portfolio-wac` | 12 verdi |
   | `api batch-split-promote` | 38 verdi |
   | E2E `tx-wac-bulk` | 11 verdi |
   | E2E `tx-wac-formmodal` | 10 verdi |
   | E2E `tx-transfer-auto-cost` | 2 verdi |

   Esito: SLOT GREEN, nessun flaky, porta 6184 libera dopo.
5. ✅ **Doc** (docs-writer `ca763408`; solo EN, pagine per sviluppatori senza traduzioni):
   - `wac.md`: la riga «Batch auto modes» della tabella; «Inline Batch Auto Modes» con la riga di ogni elemento, l'ordine, la
     voce sugli esclusi, la regola N84 coi tre casi, `wac_results` e la cache, «prima di W-B67» con l'esempio e i test;
   - `service.md`: `created_by_index` nel contesto condiviso, e il passo 1 di «Linked Pairs».

   Più una frase mia in `developer/frontend/components/features/transaction-form.md`. La pagina dava la data della riga anche
   per la gamba TRANSFER ricevuta, che invece usa quella della partner; ora c'è anche l'esclusione di W-B67, con un collegamento.
   `mkdocs build` stretto con uscita 0, `check-links` con 97 validi.
   > **⚠️ Fuori pista**: la correzione del docs-writer al mio testo. Una create in Auto con il suggerimento di valuta del frontend
   > (`{code, amount: '0'}`) è salvata con quello 0 prima del passo WAC (`apply_creates`, e `_apply_update_values` per un update).
   > Prima di W-B67 entrava quindi nei gruppi delle altre righe come `ADD_ZERO_COST`, non `ADD_UNKNOWN_COST`. La cura copre
   > entrambi i casi: la riga resta fuori finché il suo costo non è scritto.
6. ✅ **Simulazione** (17/10, 13:46–13:49): `sim_cherry_pick.sh dev_release2 --docs` sui 10 file, dev `04955c498` (HEAD
   `f731d462e` antenato; dev ha portato SEC8-2a/2b, SEC9-1 e altro di MF, ma nulla sul percorso del WAC: solo
   `rows_before_floor` nei DTO di `portfolio_service`). 0 conflitti, ruff e black puliti, `mkdocs build` stretto e `check-links`
   con uscita 0 sull'albero unito. `git diff --check` pulito; porta 6184 libera. Handoff FROZEN.

### W-B66 — il campo decimale: un esponente incollato, un incolla enorme: analisi (2026-10-17, sola lettura, HEAD `f731d462e`)

Via del coordinatore (17/10 13:49): «W-B66 → W-B68», dopo l'ingresso di W-B67. Voce del backlog da E (R13-SEC5, revisione di
C-97b). Il punto (3), il toast di «+ New event», resta in C-97c.

**(1) Un esponente incollato cambia il numero.** `ExactDecimalInput.handleInput` (`components/ui/input/ExactDecimalInput.svelte:210-221`)
passa ogni input da `filterDecimalInput` (`utils/core/parseDecimalInput.ts:30-34`), che toglie tutto ciò che non è cifra, punto,
virgola o il meno iniziale. Un `1e-8` incollato diventa `18`, un `1,5E+3` diventa `1,53`, senza avviso. Digitando, la `e` non entra
mai: solo un incolla arriva intero.

**(2) Un incolla enorme blocca la scheda di chi incolla** (solo il proprio browser). Tre punti:
- **regex quadratiche** su un testo lungo che non combacia: `formatDecimalForDisplay` (`utils/core/formatDecimal.ts:41`,
  `^-?\d*\.?\d*$`), chiamata dalla cella del Bulk (`quantityText`, `TransactionBulkModal.svelte:187`) e da `ExactQuantityInput`. Lo
  stesso schema c'è in `CANONICAL` (`parseDecimalInput.ts:21`, `\d+\.?\d*`), che `normalizeDecimalInput` prova a **ogni** battuta,
  in tutti i campi decimali (form, Bulk, import, data editor, planner PAC, tabelle). Le forme lineari equivalenti sono
  `^-?\d*(?:\.\d*)?$` e `^-?(?:\d+(?:\.\d*)?|\.\d+)$`: stesso linguaggio, la seconda `\d*` raggiungibile solo dopo il punto;
- **`compareExact` coi limiti** `min`/`max` (`ExactDecimalInput.svelte:104-112`, `normalizedParts:154-155`): un `BigInt` delle cifre
  incollate per `10n ** places`. Con un milione di decimali, un numero di un milione di cifre a ogni battuta. Si calcola anche
  quando le cifre sono già oltre il budget (`digitsValid` falso), cioè quando il confronto non serve;
- **le frecce** (`stepValue` → `acceleratedArrowStep:250-288`): lo stesso `BigInt` sul valore enorme.

`ExactQuantityInput` avvolge `ExactDecimalInput`: una cura copre entrambi.

**Proposta di cura** (D-W66-1 per il punto 1):
- (a) un testo **interamente** in notazione scientifica (`-?` cifre con `.` o `,` decimale, `e`/`E`, esponente con segno) è
  espanso **esatto** in decimale semplice in `filterDecimalInput`, se `|esponente| ≤ 100`, il limite del backend (R13-SEC7-3).
  Il testo espanso passa poi dai controlli di sempre: le cifre oltre il budget danno il messaggio di C-97b. Oltre ±100 il testo
  resta com'è, il campo è rosso, e un messaggio sotto il campo dice che l'esponente è fuori portata (chiave nuova
  `common.decimalExponentOutOfRange`, 4 lingue, in `base`: serve l'ok come per D-W12). Alternativa: rifiutare ogni esponente
  col messaggio;
- (b) le due regex lineari; in `normalizedParts`, `compareExact` solo con `digitsValid`; in `stepValue`, niente passo su un
  valore oltre il budget.

**Superfici**: `utils/core/parseDecimalInput.ts` e `utils/core/formatDecimal.ts` (nucleo condiviso: serve l'assegnazione come
scrittore; i chiamanti non cambiano comportamento, salvo l'esponente che oggi è un numero sbagliato),
`components/ui/input/ExactDecimalInput.svelte` (mio, C-97b; il lotto colori T vi ha toccato le classi), i18n `base` per la chiave
nuova.

**Rossi** (Vitest):
- `parseDecimalInput.test.ts`: l'esponente letto esatto (`1e-8`, `1,5E+3`, `-2.5e2`); fuori portata lasciato com'è; testi senza
  esponente invariati;
- `formatDecimal.test.ts`: la regex lineare con lo stesso linguaggio (una tabella di casi), e un testo di 200 000 caratteri che
  finisce entro un tetto generoso, dove la forma quadratica impiega secondi;
- `ExactDecimalInput.test.ts`: l'incolla di `1e-8` dà `0.00000001`; quello di `1e-200` dà il campo rosso col messaggio; un
  incolla di 200 000 decimali con `min`/`max` resta reattivo, e `compareExact` non gira.

Nessun backend, nessuna API.

### W-B66 — cura ✅ (2026-10-17) — 🧊 FROZEN

**Base**: HEAD `f078b766c` = dev con W-B67 (`279b3d5bd` + `581757965` → `ac92e6fae`, CHANGELOG `f078b766c`). Poi, alle 14:14,
HEAD `5603a23a7` = dev con la cura del cancello dell'HTML (`21b8aa975` + `cc86dee84`): avanzamento veloce del coordinatore, a
worktree pulito. Il dry run della cura di W-B66 resta pulito.

1. ✅ **Decisioni del coordinatore** (17/10, 14:00):
   - **scrittore** di `utils/core/parseDecimalInput.ts` e `utils/core/formatDecimal.ts` (nessun worktree li ha aperti), oltre al
     mio `ExactDecimalInput.svelte`;
   - **D-W66-1 = (a)**: un esponente incollato è espanso esatto entro ±100; oltre, il testo resta, il campo è rosso e c'è il
     messaggio;
   - la chiave `common.decimalExponentOutOfRange` in `base`, 4 lingue: ok;
   - cancello in più prima del checkpoint: `front-utility core-unit` e `component-unit` nella corsia.

   Verificato in sola lettura: `canShowSignColor` di `ExactQuantityInput` chiede anche `digitsValid`, quindi il confronto saltato
   oltre il budget non cambia nulla per i genitori. I test esistono già e sono registrati:
   `src/lib/utils/__tests__/parseDecimalInput.test.ts` e `src/lib/utils/core/__tests__/formatDecimal.test.ts` (`core-unit`),
   `src/lib/components/ui/input/ExactDecimalInput.test.ts` (`component-unit`).
2. ✅ **Rossi** (test-author `539999df`, Vitest; due giri, sotto). La cura era pronta nel frattempo (`files/scripts/wb66_cure.py`,
   dry run pulito su 3 file), con l'i18n in `files/scripts/wb66_i18n.sh`: `{max}` semplice, niente plurale né formato
   numerico, spagnolo col tu come la maggior parte di `base`.

   > **⚠️ Fuori pista**, cose trovate mentre scrivevo la cura.
   > - **Una terza regex quadratica**: `formatDecimalForDisplay` toglie gli zeri finali con `frac.replace(/0+$/, '')`, quadratica su
   >   una lunga fila di zeri che non chiude il testo. La cella del Bulk passa `maxFrac: value.length`, quindi nulla la tronca prima.
   >   Misurato con node (V8), a 10 000 / 20 000 / 40 000 caratteri:
   >
   >   | Caso | 10 000 | 20 000 | 40 000 |
   >   |---|---|---|---|
   >   | `/0+$/` | 170 ms | 711 ms | 3 632 ms |
   >   | vecchia regex di visualizzazione | 164 ms | 692 ms | 3 332 ms |
   >   | vecchio `CANONICAL` | 179 ms | 730 ms | 2 684 ms |
   >
   >   Le forme lineari, e `SCIENTIFIC`, stanno a 0,1 ms. I rossi di tempo sono dimensionati a 40 000 caratteri: un'espressione
   >   regolare sincrona non si interrompe, e a 200 000 bloccherebbe Vitest per circa 90 s a test.
   > - **`normalizeDecimalInput` toglie la `e` allo stesso modo** (`1e-8` → `18`). Lo chiamano molti campi senza
   >   `filterDecimalInput`: data editor, tabelle, planner, import, mini-modale degli eventi, `CompactCashCell` all'uscita dal
   >   campo. La stessa espansione esatta vale anche lì; fuori portata il testo torna intatto. Dentro l'approvazione: cambiano solo
   >   i testi con un esponente.
   > - **Le frecce**: su un `1e-200` tenuto, `normalizeDecimalInput` leggeva 1200, e una freccia lo faceva 1201. Né un valore
   >   fuori budget né un esponente rifiutato si spostano con le frecce.
   > - `ExactDecimalInput` accetta un esponente in portata anche dal `value` del genitore (un `Number` che stampa `1e-8`).

   ✅ **Primo giro dei rossi** (test-author `539999df`, 17/10): 64 rossi e 138 verdi sui tre file. Ogni rosso mostra il
   risultato di oggi: `1e-8` → `18`, `3E+150` → `3150`, il prop `1e-8` invalido, 4 `BigInt` della lunghezza dell'incolla, le frecce
   a `1.1234567890133`. Tempi di oggi:

   | Caso | Tempo |
   |---|---|
   | regex di visualizzazione | 2,5–2,8 s |
   | `/0+$/` | 2,8–3,9 s |
   | componente | pochi ms, quindi i suoi rossi sono di comportamento |

   Il rosso di tempo di `normalizeDecimalInput` non può esistere: `CANONICAL` vede solo testi già filtrati e corti. Diventa una
   guardia, e il cambio di `CANONICAL` resta difensivo.

   > **⚠️ Fuori pista**: le note 3–6 del test-author mostrano un buco del mio contratto. «Il filtro di sempre appena il testo non
   > è più scientifico» rimetteva il difetto con un tasto: `1e-200` più un carattere dà `1e-200x`, cioè `1200`; un `1e5x` incollato
   > dava `15`, `1.234,5e2` dava `1234.52`; una freccia su un `1e-200` tenuto lo sostituiva con un numero. **Regola rifinita**
   > (dentro D-W66-1: un numero non cambia mai in silenzio):
   > - un **marcatore d'esponente** è una cifra, un segno decimale facoltativo, `e`/`E`, un segno facoltativo e una cifra
   >   (`/\d[.,]?[eE][+-]?\d/`, lineare);
   > - un testo con un marcatore che non si legge esatto (fuori portata, o non interamente un numero) resta com'è, rosso, col
   >   messaggio (`exponentNotReadable`, che prende il posto di `isScientificOutOfRange`);
   > - senza marcatore il filtro resta quello di sempre: una `e` digitata da sola sparisce, `EUR 12,34` dà `12,34`;
   > - il testo tenuto vince sulla regola del segno (`-1e-200` resta tale);
   > - le frecce non spostano un testo tenuto.
   >
   > Il messaggio ora copre i due casi: «Write the number out in full: scientific notation is read only on its own, with an
   > exponent up to ±{max}». Verificato con node (`--experimental-strip-types`) sulle funzioni curate in uno specchio: 24 casi
   > come da contratto; `1e100` dà 101 caratteri, `1e-100` 102.

   ✅ **Secondo giro dei rossi** (test-author `539999df`): 231 test, 88 rossi e 143 verdi, i conti previsti prima di girare.
   - Oggi: `1e5x` → `15`, `1e-200x` → `1200`, `1e5e3` → `153`, `1.234,5e2` → `1234.52`, `-1e-200` → `1200`, `.5e1` → `.51`;
     le frecce su un `1e-200` tenuto danno `1200.000000000001`.
   - Il test-author ha aggiunto anche: `-1e5x` tenuto col segno; `12EUR` → `12` (una cura che prendesse ogni `e` dopo una cifra
     come marcatore la romperebbe); una riga di 40 000 caratteri `…9e5x`, che coglie una cura quadratica (una regex lasca vi
     impiega 2,5 s).
3. ✅ **Cura applicata** (17/10, 14:30 circa): `files/scripts/wb66_cure.py --apply` su 3 file, e
   `files/scripts/wb66_i18n.sh` (la chiave in `base/{en,it,fr,es}.json`: «Write the number out in full: scientific notation is read
   only on its own, with an exponent up to ±{max}»).
4. ✅ **Verdi** (carico < 50; log `files/logs/wb66_*.log`):

   | Prova | Esito |
   |---|---|
   | Vitest, i tre file | 231 verdi |
   | `prettier --check` sui sorgenti e i cataloghi cambiati | pulito |
   | `dev.py i18n check` | stretto, 5 051 chiavi |
   | `front-utility core-unit` (cancello dell'HTML e test del planner inclusi) | 209 file, 8 589 verdi |
   | `front-utility component-unit` | 179 file, 4 821 verdi |
   | `dev.py front check` | svelte-check 0 errori, 0 avvisi |
5. ✅ **Doc**: `developer/frontend/components/core-ui/atoms.md` «ExactDecimalInput», tre aggiunte: l'esponente incollato e il
   messaggio, `min`/`max` solo nel budget, le frecce e la linearità. La pagina non ha traduzioni.
6. ✅ **Simulazione** (17/10, 14:46–14:50): `sim_cherry_pick.sh dev_release2 --docs` sui 13 file, dev `f8e1f6aed` (HEAD
   `5603a23a7` antenato; dev non ha toccato i miei file, solo altre sezioni del backlog). 0 conflitti, i 4 cataloghi si caricano,
   `mkdocs build` stretto e `check-links` con uscita 0 sull'albero unito. `git diff --check` pulito; porta 6184 libera (nessun
   server: solo Vitest e i runner `front-utility`). Handoff FROZEN.

### W-B68 — i valori degli eventi dei provider troncati alla colonna: analisi e cura ✅ (2026-10-17) — 🧊 FROZEN

**Base**: HEAD `731140500` = dev con W-B66 (`b8e180ff8` + `32282ffac` → `e820279e1`, CHANGELOG `731140500`). Via del coordinatore
(14:49): «W-B68: GO, failing tests first». W-B75 è passata a H (la rivedo al suo checkpoint).

**Stato verificato** (sola lettura):
- **Il difetto.** `EventStoreOperations._storable_events` (`backend/app/services/assets/event_store.py:97-127`) controlla di un
  evento del provider solo le cifre intere (`integer_digits_issue`): non lo **tronca** a ciò che la colonna tiene. I prezzi dei
  provider sì (`storable_price` → `truncate_to_db_precision`, `db/precision.py`).
- **L'effetto.** `AssetEvent.value` è `RealDecimal(18, 6)` (`db/models.py:1055`, W-B60). Un valore con più di 6 decimali, o più
  di 15 cifre significative, si scrive com'è e si rilegge arrotondato: letto ≠ scritto. `784.0774475` si rilegge `…448`, prima
  `…447`.
- **I percorsi.** Solo il refresh dei provider passa da `_storable_events` (`refresh.py:602` → `_upsert_asset_events`). Gli
  eventi manuali sono rifiutati prima da `_reject_too_many_digits` (C-97) e scritti direttamente con `_write_asset_events`
  (`:289-296`): la cura non li tocca.
- **Il piano d'investimento programmato** (`FAScheduledInvestmentSchedule.asset_events`, parametri dell'utente) è un provider:
  i suoi eventi passano di qui. Un valore con più di 6 decimali, oggi arrotondato in silenzio dalla lettura, sarà troncato in
  silenzio. Rifiutarlo all'ingresso dei parametri è del provider (X): residuo da segnalare, non mio.
- **Lo split.** Il controllo del rapporto (`is_valid_split_ratio`, X-R47) va fatto sul valore **troncato**: un rapporto `1E-7`
  passa oggi, si salva e si rilegge 0, cioè proprio lo split che X-R47 scarta.

**Cura** (prossima, dopo i rossi): in `_storable_events`, `storable_value(evt.value.amount, AssetEvent, "value")` al posto di
`integer_digits_issue`:
- None → scartato e registrato nel log come oggi;
- altrimenti l'evento prende il valore troncato (`model_copy` sul `Currency`), solo se cambia: un valore che già entra resta
  com'è, forma compresa (`1.5`, non `1.500000`);
- il rapporto dello split si controlla sul valore troncato.

Doc: dove `developer/` descrive la scrittura degli eventi dei provider (W-B58, W-B60).

**Test**: `services asset-digit-limits` (`test_asset_digit_limits.py`, accanto ai test sugli eventi dei provider), più
`asset-event-store`, `event-split-ratio` e la guardia degli upsert, come prove di non regressione.

**Passi:**
1. ✅ **Rossi** (test-author `c5b03fa0`, solo `test_asset_digit_limits.py`, test col marcatore `wb68`): 12 rossi e 8 guardie. Oggi:

   | Caso | Si rilegge oggi | Contratto |
   |---|---|---|
   | `784.0774475` | `784.077448` | `784.077447` |
   | `0.1234567` | `0.123457` (mezzo pari) | `0.123456` |
   | `123456789012.123999` | `…124000` | `123456789012.123` |
   | SPLIT `0.0000001` | salvato, si rilegge `0` | scartato, un avviso col nome dell'asset |
   | letto = scritto, 4 valori, riga nuova e aggiornata | sessione ≠ rilettura | uguali |

   Le guardie: i valori che entrano si rileggono uguali, e nella sessione tengono la forma (`1.5`, `0.123456`,
   `123456789012.123`, uno SPLIT di 2). Prove: `asset-digit-limits WB68` 12 rossi / 8 verdi (due volte); l'azione intera 12 / 87;
   `event-split-ratio` 78, `asset-event-store` 71.

   > **⚠️ Fuori pista**, le note del test-author:
   > - (1) «tiene la forma» non vale con `storable_value` da solo (`1.5` → `1.500000`). La mia cura assegna il valore troncato
   >   solo quando cambia il numero, quindi la guardia della forma passa.
   > - (2) `123456789012.123456` non è un rosso: la rilettura col mezzo pari cade già sul troncato. Usato `…123999`.
   > - (3) Il controllo «nomina l'asset» di X-R47 in `test_event_split_ratio.py` (file di X) è lasco: accetta qualunque numero,
   >   e con l'asset 1 basta il `count=1` dell'avviso. Lo segnalo al coordinatore, non lo tocco.
2. ✅ **Cura** (`files/scripts/wb68_cure.py --apply`): in `_storable_events`, `storable_value` al posto di `integer_digits_issue`
   (anche nell'import). Il valore troncato con `model_copy` solo quando cambia; il rapporto dello split giudicato sul valore
   troncato; docstring di `_upsert_asset_events` e `_storable_events`. `ruff` e `black` puliti.
3. ✅ **Verdi** (17/10, 15:07–15:08, `files/scripts/wb68_light.sh`, carico < 50):

   | Prova | Esito |
   |---|---|
   | `asset-digit-limits` | 99 verdi (i 12 rossi inclusi) |
   | `event-split-ratio` | 78 verdi |
   | `asset-event-store` | 71 verdi |
   | `asset-source-guards` | 29 verdi |
   | `asset-source-refresh` | 18 verdi |
   | `asset-source` | 61 verdi |
4. ✅ **Doc**, entrambe senza traduzioni:
   - `developer/backend/assets/events.md`: il paragrafo sugli eventi dei provider, con il troncamento, la forma, lo split
     giudicato troncato e l'esempio di prima;
   - `developer/architecture/database/index.md`: anche gli eventi dei provider sono troncati (`storable_value`).
5. ✅ **Simulazione** (17/10, 15:09–15:11): `sim_cherry_pick.sh dev_release2 --docs` sui 6 file, dev `79d4ca239` (HEAD
   `731140500` antenato; dev ha cambiato dei miei file solo il backlog, in altre sezioni). 0 conflitti; ruff e black puliti;
   `mkdocs build` stretto e `check-links` con uscita 0 sull'albero unito. `git diff --check` pulito; porta 6184 libera. Handoff FROZEN.

### C-97c — la visualizzazione di quantità e prezzi: analisi (2026-10-17, sola lettura, HEAD `cc2e9307c`)

**Base**: HEAD `cc2e9307c` = dev con W-B68 (`f3836e99b` → `06e9d2c20`, CHANGELOG `cc2e9307c`). Ordine del coordinatore (15:11):
le due revisioni in coda (W-B75 di H, il chunking BRIM di MF, ai loro checkpoint), poi **C-97c**, poi W-B70.

**Perimetro** (dal punto 7 dell'analisi di C-97, più due resti):
- quantità mostrate a 10 decimali, non 6 o 8;
- un formatter dei prezzi a cifre significative: almeno 2 decimali, abbastanza per 4 cifre significative, al più 12;
- dai resti: il toast di «+ New event» (W-B66 punto 3) e la vista a 4 decimali del data editor.

**Stato a HEAD** (riverificato; i file si sono spostati con FE8 e Y5/Y6; elenco completo in
`files/c97c_sites.txt`):

| Area | Sito | Oggi |
|---|---|---|
| TR | `features/transactions/txDisplayHelpers.ts:21` | quantità a 6 |
| TR | `resolveValidationMessage.ts:203-205` | saldo d'asset a 6 |
| TR | `wac/WacPreviewSection.svelte:545-575` | costo unitario e PMC a 2–4 (prezzi) |
| TR | `events/EventCreateMiniModal.svelte:197` | toast `formatFixed(parseFloat(…), 2)` |
| IW | `import/GapFixStep.svelte:72` | quantità a 8 |
| IW | `import/FixFlaggedStep.svelte:427` | a 2…`decimals` |
| T (mio) | `ui/data-editor/DataEditor.svelte:212` | `Number(val)…maximumFractionDigits: 4`: prezzi, cambi ed eventi |
| BK | `features/brokers/lots/unifiedLotsTableHelpers.ts:69` | 6 |
| BK | `lotGanttChartHelpers.ts:108, :119` | 6 |
| BK | `LotWacPriceChart.svelte:501, :1372` | 8 |
| BK | `LotCustodyModal.svelte:78, :145, :161, :192` | 8 |
| DV | `features/dashboard/ExposureTable.svelte:154` | 6 |
| AF | `components/assets/AssetTable.svelte:117` | prezzi a 2 |
| AF | `AssetPriceSummary.svelte:99, :112` | 2 |
| AF | `AssetCard.svelte:226, :233` | 2 |
| AF | `ProviderAssignmentSection.svelte:381` | 2 |
| AF | `providerProbe.ts:124, :135` | 2 |
| DV | `components/charts/candlestickChartHelpers.ts:94-97` | 2/4/6 |
| DV | `priceChartHelpers.ts:608` | 4 |
| DV | `PriceChartFull.svelte:820, :823, :888, :1051` | 4 |
| DV | `LineChart.svelte:744-746, :826, :837` | 2/4 |
| DV | `MeasurePanel.svelte:300-305, :534` | 4/6 |

Quel che c'è già:
- `formatExactDecimal` (`utils/core/formatFixed.ts:60`): decimale esatto, localizzato, `minFrac`/`maxFrac`. Le quantità sono
  quasi solo un cambio d'argomento.
- Nessun formatter dei prezzi a cifre significative fuori dal planner PAC, che tiene tutte le cifre di un prezzo
  (`planner/format.ts`): serve un aiuto nuovo in `utils/core`.
- Test da aggiornare: `lotGanttChartHelpers.test.ts`, `unifiedLotsTableHelpers.test.ts` (fissano i 6).

**Proposta**:
- **D-C97c-1, la regola del prezzo**: decimali = min(12, max(2, quanti servono per 4 cifre significative)), zeri finali tolti oltre
  i 2. Esempi: `0.0000034573` → `0,000003457`; `1.2345` → `1,235` (con l'arrotondamento di `Intl`); `123.45` → `123,45`;
  `65000.123` → `65.000,12`; `0.5` → `0,50`. Gli assi dei grafici restano compatti (`k`, `M`): la regola vale per i valori, non
  per le etichette degli assi.
- **Lotti**: C-97c-1 mio subito (l'aiuto `formatPrice` in `utils/core`, i siti TR, IW e il data editor); C-97c-2 i siti BK, e
  C-97c-3 AF e DV, ai loro proprietari o a me con l'assegnazione.

### C-97c-1 — l'aiuto dei prezzi e i siti TR, IW, data editor: cura ✅ (2026-10-17) — 🧊 FROZEN

1. ✅ **Decisioni del coordinatore** (17/10, 15:14):
   - **D-C97c-1**, la mia regola con un emendamento perché nulla mostri *meno* decimali di oggi:
     `formatPrice(value, {minDecimals = 2})`, decimali = min(12, max(minDecimals, quelli di 4 cifre significative)), zeri tolti
     oltre `minDecimals`; un sito a 4 decimali (cambi, data editor) passa `minDecimals: 4`; gli assi restano compatti; esempi
     fissati in Vitest con un caso di cambio a `minDecimals: 4`;
   - **i tre lotti sono miei**, col suo via sui `.svelte` di TR, IW, BK, AF e DV, solo la formattazione dei numeri (nessuna classe
     o markup oltre la chiamata);
   - C-97c-1 subito; C-97c-2 (BK) dopo, con la revisione di J; C-97c-3 (AF e DV) dopo l'ingresso di X-R59 A/B di Y, con le
     revisioni di X (AF) e di Y (DV).
2. ✅ **Dettaglio d'implementazione** (comunicato al coordinatore, 15:30 circa): un `floorDecimals` facoltativo (di default
   `minDecimals`), perché un sito che oggi mostra un *intervallo* di decimali tenga la sua forma.
   - Decimali = min(12, max(floorDecimals, quelli di 4 cifre)); zeri aggiunti solo fino a `minDecimals`.
   - Data editor `{0, 4}`: `1.5` resta `1,5`, non `1,5000`. PMC corrente `{2, 4}`. Cambi `{minDecimals: 4}`.
   - `formatPrice` restituisce `''` per un input che non è un numero e non lo ripete mai: resta un formatter puro di numeri, da
     mettere fra i `NUMERIC_FORMAT_CALLS` del cancello dell'HTML con C-97c-3 (i tooltip).
   - Il sito del data editor passa `Number(val)`, che il cancello già scarta: nessun cambio al cancello in C-97c-1.
   - `FixFlaggedStep.svelte:427` esce dal perimetro: è un importo di cassa che mostra i suoi decimali fino a 8, più dei 6 della
     colonna.
3. ✅ **Rossi** (test-author `f6656189`, Vitest): 54 rossi e 269 verdi in 7 file, tutti rossi di C-97c-1.

   | File | Rossi / verdi | Oggi |
   |---|---|---|
   | `formatFixed` | 43 / 57 | «non esportato» |
   | `txDisplayHelpers` (nuovo, in `core-unit`) | 2 / 7 | `+0.123457 📈`, `+123,456,789.123457 📈` |
   | `resolveValidationMessage` | 2 / 54 | `-0 📉` |
   | `WacPreviewSection` | 4 / 6 | `0.12345678`, `0.00 €`, `0.0000`, `= 0.0001 €` |
   | `EventCreateMiniModal` | 1 / 5 | `0.12 USD` |
   | `GapFixStep` | 1 / 28 | `0.12345678` (troncato, non arrotondato) |
   | `DataEditor` | 1 / 112 | `0` |

   Il test-author ha portato a 8 decimali le quantità di due test di lingua (M-18) in `WacPreviewSection` e `GapFixStep`, con
   l'attesa del taglio a 10: provano solo il locale e restano verdi prima e dopo.
   > **⚠️ Fuori pista**, i buchi del contratto che ha segnalato, già coperti dalla cura:
   > - `floorDecimals` sotto `minDecimals`, o `minDecimals` sopra 12: il massimo include `minDecimals` e il minimo è limitato al
   >   massimo, quindi nessun `RangeError` di Intl;
   > - la stringa `'-0'` passa dal ramo `number === 0` e dà `0.00`;
   > - il costo unitario della riga in un'altra valuta e quello senza valuta sono anche loro nella cura, senza un rosso proprio.
4. ✅ **Cura applicata** (17/10, 15:40 circa): `files/scripts/c97c1_cure.py --apply` su 8 file (7 di prodotto più il frammento del
   cancello del denaro), poi `prettier --write` su `WacPreviewSection.svelte` (solo le mie righe: la cella della PMC divisa). Doc:
   in `developer/frontend/i18n.md` la riga `formatPrice` / `priceFractionDigits` nella tabella dei formatter (pagina senza
   traduzioni).
5. ✅ **Verdi** (carico < 50; log `files/logs/c97c1_*.log`):

   | Prova | Esito |
   |---|---|
   | Vitest, i 7 file più il cancello del denaro e quello dell'HTML | 356 verdi |
   | `dev.py test check-orphans` | ogni test registrato raggiungibile |
   | `front-utility core-unit` | 210 file, 8 647 verdi |
   | `front-utility component-unit` | 179 file, 4 832 verdi |
   | `front-transaction tx-unit` | 23 file, 915 verdi |
   | `dev.py front check` | svelte-check 0/0 |

   > **⚠️ Fuori pista**: il primo `tx-unit` (carico 49) ha dato 3 file «Hook timed out in 60000ms»: `GapFixStep`,
   > `ParseDetailModal`, `ReportSetCard`, gli ultimi due non toccati. Nessun test fallito: 823 verdi, 92 saltati per il timeout.
   > Rilanciati da soli a carico 28: 92 verdi; poi l'azione intera a carico 27: 915 verdi. Carico, non un rosso.
6. ✅ **Simulazione** (17/10, 16:02–16:04): `sim_cherry_pick.sh dev_release2 --docs` sui 19 file (il test nuovo, non
   tracciato, compreso), dev `e9746b959` (HEAD `cc2e9307c` antenato; dev ha cambiato il backlog e una riga del runner
   `_frontend_utility.py`, che si unisce da sola con la registrazione del test nuovo). 0 conflitti; `mkdocs build` stretto e
   `check-links` con uscita 0 sull'albero unito. `git diff --check` pulito. Handoff FROZEN.

   La cura è pronta, `files/scripts/c97c1_cure.py`, dry run pulito su 8 file. `formatPrice` è verificato con node
   (`--experimental-strip-types`) su tutti gli esempi del contratto, `it` compreso, `-0` e i vuoti.
   > **⚠️ Fuori pista**: il **cancello del denaro** (`lib/utils/privacy/moneyRenderSites.test.ts`) registra per file e frammento
   > il toast di `EventCreateMiniModal` (`` `${formatFixed(amt, 2)} ${assetCurrency}` ``, `public`: un evento è dell'asset, non
   > dell'utente). La riscrittura deve aggiornare il frammento nello stesso cambio, come dice `developer/frontend/i18n.md` («Two
   > source gates»): è nella cura. Gli altri siti non cambiano forma di denaro: tengono `formatCurrencyAmountPlain`, o scrivono
   > senza valuta.

**Siti di C-97c-1**:

| Sito | Oggi | Dopo |
|---|---|---|
| `txDisplayHelpers.formatTxQuantity` | `toLocaleString` a 6 | `formatExactDecimal(…, {maxFrac: 10})` |
| `resolveValidationMessage.ts:203` (saldo d'asset) | 6 | 10, esatto |
| `WacPreviewSection`: quantità | `formatExactDecimal` di default, 8 | 10 |
| `WacPreviewSection`: costi unitari | 2 | `formatPrice` |
| `WacPreviewSection`: PMC corrente | 2–4 | `{2, 4}` |
| `WacPreviewSection`: cambio | `formatFixed(…, 4)` | `{minDecimals: 4}` |
| `EventCreateMiniModal`, toast | `formatFixed(parseFloat(…), 2)` | il valore esatto, 2–6 |
| `GapFixStep:72` | quantità a 8 | 10 |
| `DataEditor:212`, riga di sola lettura | `Number(val)…max 4` | `formatPrice(Number(val), {minDecimals: 0, floorDecimals: 4})` |

### C-97c-2 — quantità e prezzi dei lotti (BK): analisi e cura ✅ (2026-10-17) — entrato (`a8ec9d309` → `016fe7af9`)

**Base**: HEAD `a84020b09` = dev con C-97c-1 (`7b251606a` → `f1bfa1e31`, CHANGELOG `a84020b09`; `theme-roles --check` pulito sulla
punta). Via del coordinatore: «Go C-97c-2 (BK, lots); J reviews».

**Siti** (`frontend/src/lib/features/brokers/lots/`):

| Sito | Oggi | Dopo |
|---|---|---|
| `unifiedLotsTableHelpers.formatLotQuantity(value: number \| null)` | `toLocaleString` a 6 | 10 |
| `lotGanttChartHelpers.formatQuantity(value: number)` | 6 | 10 |
| `lotGanttChartHelpers.quantityPluralCount` | conta sulle stesse 6 cifre | 10 (il plurale segue le cifre mostrate) |
| `LotWacPriceChart.svelte` `formatQuantityValue(value: number)` | `formatExactDecimal(Math.abs(value), {maxFrac: 8})` | `formatLotQuantity` |
| `LotCustodyModal.svelte` `formatQuantity` | `formatExactDecimal(abs, {maxFrac: 8})` su un numero | `formatLotQuantity` |
| `LotAnalysisFailedNotice.svelte:37` (sito nuovo, di J-12) | `formatExactDecimal(raw, {maxFrac: 8})`, `raw` stringa del backend | `maxFrac: 10` |
| `LotWacPriceChart.formatMaybePrice` e `LotCustodyModal.formatUnitPrice` (prezzi per unità, pubblici) | 2 decimali fissi | `priceFractionDigits` |

**Restano**:
- i totali (`formatMaybeMoney`, `formatPrice` della modale, mascherati): sono denaro;
- i rapporti degli split (`:1372`; `:145`, `:161`, `:192` della modale) a 8: un rapporto è il valore di un evento, che tiene 6
  decimali;
- gli assi del grafico, compatti.

Il cancello del denaro non registra siti dei lotti.

> **Scoperta**: `formatExactDecimal` passato un **numero** lo scrive con `String()`, quindi una quantità sotto 1e-6 si legge `1e-7`
> (`formatDecimalForDisplay` restituisce com'è un testo che non è un decimale semplice). Un lotto da 10 satoshi
> (0,0000001 BTC) nel grafico e nella modale si legge `1e-7`, già oggi. Per questo i due siti passano a `formatLotQuantity`
> (Intl su un numero, mai in notazione scientifica, fino a 10 decimali): una sola implementazione per le quantità dei lotti.

**Test**:
- `unifiedLotsTableHelpers.test.ts` e `lotGanttChartHelpers.test.ts` fissano i 6: si aggiornano;
- rossi in `LotCustodyModal.test.ts` e `LotAnalysisFailedNotice.test.ts`;
- `LotWacPriceChart` non ha un test di componente: le quantità passano dall'aiuto condiviso, già provato; il prezzo per unità si
  prova nella modale.

**Passi**:
1. ✅ **Cura pronta** (17/10): `files/scripts/c97c2_cure.py`, dry run pulito sui 5 file. `QUANTITY_FRACTION_DIGITS = 10` in
   `lotGanttChartHelpers.ts`, dichiarata prima di `formatQuantity` e letta anche da `quantityPluralCount`: le cifre mostrate e quelle
   che decidono il plurale sono le stesse per costruzione. I due componenti importano `formatLotQuantity` da
   `./unifiedLotsTableHelpers` (la cartella condivide già aiuti fra file, `./lotChartShared`) e `priceFractionDigits` accanto a
   `formatExactDecimal`.
2. ✅ **Rossi** (17/10, test-author `c97c2-reds`, 4 file già nel runner, nessuna registrazione nuova): **11 rossi, 197 verdi**, uguali
   nella mia corsia (carico 24, `files/logs/c97c2/10_my_reds.log`), ognuno sul suo motivo:
   - `unifiedLotsTableHelpers.test.ts` (3): il tetto a dieci (oggi `0.123457`), `0.1234567891` (oggi `0.123457`), `0.0000001` (oggi `0`:
     il lotto si legge vuoto); guardie `2.5` e `it` esplicito;
   - `lotGanttChartHelpers.test.ts` (4): il tetto a dieci, `0.1234567891`, il conteggio di `1.0000001` (oggi 1, atteso 1,5) e la riga del
     tooltip («1.0000001 share» → «shares»); i due casi O-16 che fissavano il taglio a sei leggono ora `1.00000000001` (frazione oltre la
     decima: verde prima e dopo); guardia nuova: il conteggio segue le cifre che `formatQuantity` mostra, in `en` e `it`;
   - `LotCustodyModal.test.ts` (3): quantità `0.1234567891` (oggi `0.12345678`) e `0.0000001` (oggi **`1e-7`** nelle 4 celle: riepilogo,
     frammento, storia d'apertura e di partenza), prezzo per unità `0.000003457312` (oggi «Open price 0.00 EUR», «Close price 0.00 EUR»);
     guardie `2.5` e `123.45`;
   - `LotAnalysisFailedNotice.test.ts` (1): `0.1234567891` (oggi «Removes 0.12345678 more…»).
   Nei blocchi M-18 (italiano) i valori a nove decimali passano a sei (`0.123456`, `1.123456`): leggono solo la notazione, mai un taglio.
   > **Note del test-author** (da decidere, nessun rosso aggiunto): (1) il riepilogo della modale somma le fette in float e oggi taglia a
   > otto: 0,7 + 0,1 si legge `0.79999999`; con `formatLotQuantity` (Intl arrotonda alla decima) `0.8`: la cura lo corregge di passaggio;
   > (2) una quantità con più cifre di quante un float ne tenga (`123456789.1234567891`) si legge `123,456,789.12345679`, già oggi (la
   > modale legge in float); solo l'avviso resta esatto (stringa del backend); (3) l'avviso tiene `formatExactDecimal`, che scrive `1e-7`
   > se riceve un numero: oggi riceve una stringa; (4) la modale passa dal taglio all'arrotondamento all'ultima cifra: si vede solo su somme
   > in float oltre la decima; (5) le celle della quantità originale/aperta e del prezzo d'apertura del riepilogo non hanno testid.
3. ✅ **Cura applicata e verdi** (17/10, 16:3x–16:47):
   - `c97c2_cure.py --apply` sui 5 file; i 4 file di test **208 verdi** (carico 23). I due componenti usano ancora
     `formatExactDecimal` per i rapporti degli split: nessun import morto.
   - Poi `c97c2_cure_b.py --apply` (3 file): **una sola costante** `LOT_QUANTITY_FRACTION_DIGITS = 10` in `lotChartShared.ts`
     (il modulo leggero che il Gantt già importa; ne importa solo `uiLocale`), letta da `formatLotQuantity`, dal `formatQuantity` del
     Gantt e da `quantityPluralCount`, al posto di due `10` scritti a mano. Nessun test enumera gli export di `lotChartShared`.
   - Verdi dopo la parte b (`files/scripts/c97c2_light.sh`, una prova alla volta, carico < 50; log `files/logs/c97c2/light_*.log`,
     il primo giro, prima della parte b, in `round1/`, uguale):

     | Prova | Esito |
     |---|---|
     | `front-broker broker-unit` (modale, avviso e 5 altri) | 7 file, 76 verdi |
     | `front-utility core-unit` (gli aiuti dei lotti, `lotChartShared`, i cancelli del denaro e dell'HTML) | 211 file, 8 727 verdi |
     | `dev.py front check` | svelte-check 0/0 |
     | Prettier sui 10 file | pulito |
     | `git diff --check` | pulito |

   - Nessun E2E fissa le cifre dei lotti: `privacy-masking.spec.ts` confronta col testo letto in chiaro sulla stessa pagina;
     `lotDataQualityHelpers.test.ts` sostituisce il formatter con un `vi.fn`.
   - Le note del test-author: (1) `0.7 + 0.1` nel riepilogo ora si legge `0.8` (Intl arrotonda alla decima): corretto di passaggio;
     (2) **chiusa senza codice**: la quantità salvata ha al più 15 cifre significative (`storable_value`, il `REAL` di SQLite), che
     un float di JavaScript tiene e Intl riscrive uguali alla decima; un valore come `123456789.1234567891` (19 cifre) non si salva
     così neppure nel database; (3)–(5) nessuna azione.
4. ✅ **Doc** (17/10, modifica puntuale come in C-97c-1, pagina per sviluppatori senza traduzioni):
   `developer/frontend/components/features/lots-analysis.md`, la riga di `missing_quantity` («up to 8 decimals» → il testo decimale
   del backend, fino ai 10 della colonna) e una sezione nuova «Quantities and prices» sotto `LotCustodyModal`: la costante, chi
   scrive le quantità (tabella, grafico WAC, modale, Gantt, il plurale del tooltip, l'avviso), i prezzi per unità pubblici con
   `priceFractionDigits`, e ciò che non cambia (totali, rapporti degli split a 8, assi). Nessun'altra pagina fissa le cifre dei
   lotti (grep di `six|6|eight|8|ten|10` + `fraction|decimal|digit` e dei nomi delle funzioni); la lista dei formatter di
   `developer/frontend/i18n.md` nomina le funzioni senza le cifre.
5. ✅ **Simulazione** (17/10, 16:52–16:54): `sim_cherry_pick.sh dev_release2 --docs` sui 12 file, dev `2405097c7` (HEAD `a84020b09`
   antenato, 42 commit avanti, nessuno dei quali tocca i 12 file né la cartella dei lotti): 0 conflitti; `mkdocs build` stretto e
   `check-links` con uscita 0 sull'albero unito (log `files/logs/c97c2/20_sim.log`). `git diff --check` pulito. Handoff FROZEN;
   revisione di J.

### W-B70 — la descrizione unita oltre 500, gli errori di campo senza il loro contesto: analisi (2026-10-17, sola lettura, HEAD `a84020b09`)

**Stato reale**

1. **Backend, la regola in due copie.**
   - `_lone_error_params` esiste due volte: `transaction_batch_stages.py:48-60` e BRIM `brim_provider.py:545-557`.
   - Un errore di campo (`loc` non vuoto) ha sempre `params=None`.
   - Gli errori di campo con un contesto di dati semplici negli schemi delle transazioni:
     - `string_too_long`, `{max_length}`:
       - `description` 500 in create (`transactions.py:248`), update (`:529`) e nei campi uniti (`batch.py:196`);
       - `link_uuid_a/b` 36 (`batch.py:223-224`).
     - `greater_than`, `{gt}`:
       - `id_a`/`id_b` (`batch.py:175-176`, `:221-222`);
       - `from_tx_id`/`to_tx_id`, `asset_id`, `id` (`promotion.py:36-37`, `:43`, `:93`);
       - `id` del delete (`transactions.py:633`).
     - `greater_than_equal`, `{ge}`: `asset_event_id` dell'update (`transactions.py:551`).
2. **Il ramo impacchettato** (`multipleBusinessRuleErrors`) copia il `ctx` di ogni sotto-errore senza filtro, nelle due copie (nota di
   H, revisione di W-B75).
   - Oggi i sotto-errori vengono dai nostri validatori, quindi tengono dati semplici.
   - Un'eccezione o un oggetto messi lì renderebbero la risposta non serializzabile: un 400 «Unable to serialize» nel BRIM, un 500
     nel batch.
3. **Frontend** (`resolveValidationMessage.ts`):
   - **`string_too_long` non è tradotto.** `PYDANTIC_BUILTIN_KEYS` non lo ha, quindi l'utente legge «Descrizione: String should
     have at most 500 characters», in inglese, in ogni lingua.
   - **`greaterThan`, `greaterThanEqual`, `lessThan` e `lessThanEqual` leggono `{gt}`, `{ge}`, `{lt}`, `{le}`**, che non arrivano
     mai: svelte-i18n restituisce allora il messaggio grezzo, `{gt}` compreso (il rosso lo fisserà).
   - **Un'etichetta non escapata (scoperta).** Il ramo dei built-in (`:248-253`) mette davanti `fieldLabel` senza
     `escapeHtml`, gli altri due rami la escapano.
     - L'etichetta di ripiego è il nome grezzo del campo preso dal `loc`, quindi la chiave di un `extra_forbidden` arriva dal
       payload fino a `{@html}`.
     - Si raggiunge solo dal proprio payload API o dal codice di un plugin (l'interfaccia manda chiavi fisse): self-only, ma
       rompe la regola del modulo («every string that reaches it is escaped»).
     - Cura: `escapeHtml(fieldLabel)`, nessun effetto su un'etichetta tradotta.
   - Il risolutore serve il batch (Form, Bulk, banner, `commitRefusal`) e il BRIM (`ParseDetailModal`, `resolveBrimNotice`): una
     chiave copre entrambi.
4. **Modale d'unione** (`features/transactions/bulk/PromoteMergeModal.svelte`, area TR, classi di palette legacy):
   - la textarea (`promote-merge-desc-input`) non ha contatore né limite;
   - il precompilato `mergeStrings(a, b)` = `a\nb` arriva a 1 001 caratteri.
5. **«Promuovi tutto» del Bulk, strategia `merge`** (`TransactionBulkModal.svelte:3087-3090`): unisce senza la modale, quindi una
   coppia la cui descrizione unita supera 500 è rifiutata al salvataggio, sull'elemento della promozione.
6. **Il Form è già al sicuro.** `TxFormOptionalSection.svelte:71` ha `maxlength="500"`, contato in unità UTF-16, quindi mai oltre i
   punti di codice del backend. Nella cartella delle transazioni non c'è un altro `maxlength`: una create o un update del Bulk oltre
   500 è rifiutato col messaggio, che W-B70 traduce.
7. **Il conteggio.** Il `max_length` del backend è `len()` di Python, in punti di codice; il precedente nel frontend è
   `[...text].length` (`pluginSettingsForm.ts:223-224`, `passwordRules.ts:36`).

**Test che cambiano contratto** (i rossi li riscrivono):
- `test_brim_create_transaction.py:375-392` (`test_field_error_with_plain_context_carries_no_params`) e `:476`;
- `test_transaction_service.py:376-403`, la guardia di `string_too_long` con `params` nulli;
- da controllare `test_transaction_decimal_places.py:1347`, il caso H-41 della descrizione di 501 caratteri.

**Decisioni chieste al coordinatore**

- **D-W70-1.** Un errore di campo col contesto di dati semplici lo porta come `params`, nelle due copie.
  - `value_error` e ogni altro contesto non semplice restano `None`.
  - I sotto-errori del ramo impacchettato passano dallo stesso filtro, sotto-errore per sotto-errore, nelle due copie.
  - Contratto della risposta: `params` non è più nullo per gli errori di campo; l'unico lettore è il frontend.
- **D-W70-2.** Chiave nuova `transactions.pydantic.stringTooLong`, «At most {max_length} characters», 4 lingue, con
  `dev.py i18n add`.
  - Solo i codici raggiungibili: niente `string_too_short` né `too_long`.
  - Più l'escape di `fieldLabel`.
- **D-W70-3.** Modale d'unione: un contatore `n / 500`, in punti di codice, sotto la textarea.
  - Oltre 500: un ruolo d'errore, un messaggio, `aria-invalid` e Conferma disabilitata.
  - Il limite vive in una costante del frontend, documentata contro lo schema.
  - Serve l'OK di scrittura su `PromoteMergeModal.svelte` (TR); il markup nuovo usa solo ruoli.
- **D-W70-4.** «Promuovi tutto» con la strategia `merge`, quando la descrizione unita di una coppia supera 500:
  - **(a)**, proposta: la coppia resta non promossa, l'utente la unisce nella modale, e un avviso dice «N coppie lasciate a
    un'unione manuale»;
  - **(b)**: come oggi, rifiutata al salvataggio, ora tradotta.
  - Mai (c), tenere le note di un lato solo: perde testo.
  - (a) chiede l'OK di scrittura su `TransactionBulkModal.svelte` (TR, lotto FE8a) e una chiave nuova.
- **D-W70-5.** W-B77 dentro W-B70: una sola copia di `_loc_to_field` e della regola dei `params` in un modulo neutro
  (`backend/app/utils/pydantic_errors.py`; i due servizi lo importano senza cicli), con la riduzione di `resolved_fields.` (innocua
  per il BRIM, che non ha quel campo). Altrimenti due copie cambiate uguali e un test di parità, e W-B77 dopo con H.

**Decisioni del coordinatore** (17/10 16:5x; ordine: C-97c-3 prima, poi W-B70):
- **D-W70-1: OK.** Il cambio di contratto va bene prima del rilascio; i tre test che fissano `None` si riscrivono come rossi.
- **D-W70-2: OK**, e l'`escapeHtml` del ramo dei built-in nello stesso lotto, con un rosso.
- **D-W70-3: OK**; OK di scrittura su `PromoteMergeModal.svelte`, solo ruoli di colore.
- **D-W70-4: (a)**: la coppia resta non promossa, con l'avviso; OK di scrittura su `TransactionBulkModal.svelte`. Mai perdere testo.
- **D-W70-5: W-B77 dentro**, un modulo condiviso `utils/pydantic_errors.py`; rivede H (era co-proprietario). La SEC9g di MF tocca
  `brim_provider.py` in `search_asset_candidates_bulk`, un'altra funzione: in BRIM la mia modifica resta all'import e ai siti di chiamata.

### C-97c-3 — prezzi degli asset (AF) e dei grafici, quantità della dashboard (DV): analisi e cura ✅ (2026-10-17) — 🧊 FROZEN

**Base**: HEAD `6e503e0f6` = dev con C-97c-2 (`4e02e5fee` → `016fe7af9`, CHANGELOG `6e503e0f6`), con X-R59 di Y (`f317e3a9f`).
Via del coordinatore (17/10 16:5x): «C-97c-3 first (it closes C-97c), then W-B70». OK di scrittura sui `.svelte` di AF e DV dal
D-C97c-1, solo per la formattazione dei numeri. Revisori: X (AF), Y (DV).

**Siti** (riverificati sulla punta; X-R59 ha spostato le righe di 1–2):

| Area | Sito | Oggi | Dopo |
|---|---|---|---|
| AF | `components/assets/AssetTable.svelte:219`, colonna `lastPrice` | `formatCurrencyAmountHtml(price, …, {public})`: 2 fissi | `minFraction`/`maxFraction` da `priceFractionDigits(price)` |
| AF | `AssetPriceSummary.svelte:99`, prezzo | `formatFixed(lastPrice, 2)` | `formatPrice(lastPrice)` |
| AF | `AssetPriceSummary.svelte:112`, Δ assoluto | `formatFixed(deltaAbs, 2, {signed})` | `formatPrice(deltaAbs, {signed: true})` |
| AF | `AssetCard.svelte:226`, prezzo | `formatFixed(Number(livePrice), 2)` | `formatPrice(livePrice)` |
| AF | `AssetCard.svelte:233`, Δ assoluto | `formatFixed(Number(deltaAbs), 2, {signed})` | `formatPrice(deltaAbs, {signed: true})` |
| AF | `ProviderAssignmentSection.svelte:381`, prova: prezzo corrente | `formatFixed(Number(cpValue), 2)` | `formatPrice(Number(cpValue))` |
| AF | `providerProbe.ts:124`, `:135`, tooltip della prova: prezzo, chiusure | `formatFixed(Number(…), 2)` | `formatPrice(Number(…))` |
| DV | `features/dashboard/ExposureTable.svelte:154`, quantità | Intl a 6 | Intl a 10 |
| DV | `ExposureTable.svelte:396` prezzo, `:412` PMC | `formatCurrencyAmountPlain(…, {public})`: 2 fissi | `priceFractionDigits` |
| DV | `charts/candlestickChartHelpers.ts:94-97` `formatCandlePrice` (tooltip) | ≥100 → 2; ≥1 → 4; sotto 1 → fino a 6, almeno 1 | `formatPrice(v)`; `{minDecimals: 4}`; `{minDecimals: 1, floorDecimals: 6}` |
| DV | `charts/priceChartHelpers.ts:608`, Δ del tooltip | `formatFixed(deltaAbs, 4, {signed})` | `formatPrice(deltaAbs, {minDecimals: 4, signed: true})` |
| DV | `PriceChartFull.svelte:820`, `:823` (valore dell'evento, originale), `:888` (valore del secchio), `:1051` (valore della riga) | `formatFixed(…, 4)` | `formatPrice(…, {minDecimals: 4})` |
| DV | `LineChart.svelte:826` (valore), `:837` (banda superiore e inferiore) | `formatFixed(…, 4)` | `formatPrice(…, {minDecimals: 4})` |
| DV | `MeasurePanel.svelte:300-301` `fmtValue` | ≥1 → 4; sotto 1 → fino a 6 | `{minDecimals: 4}`; `{minDecimals: 0, floorDecimals: 6}` |
| DV | `MeasurePanel.svelte:305` `fmtDelta`, `:534` valore d'inizio in attesa | 4 (col segno il Δ) | `{minDecimals: 4[, signed: true]}` |

Ogni sostituzione tiene il minimo di oggi (`minDecimals`, `floorDecimals`): nessun valore mostra meno cifre, e sopra 0,001 le cifre
non cambiano, salvo i prezzi a 2 fra 1 e 10, che mostrano la terza quando c'è (`1.234`, D-C97c-1: 4 cifre significative).

**Restano**:
- gli assi (`LineChart:744-746`), i volumi (`formatVolume`), i giorni (`PriceChartFull:825`), i conteggi e i secondi
  (`ProviderAssignmentSection:402`, `:654`, `:686`), le percentuali;
- `AssetTable.formatDelta`: il ramo a 2 decimali è morto (le due chiamate passano `'%'`). Non si tocca.

**Scoperte**:
- **Tre prezzi per unità fuori dall'elenco**, negli stessi file autorizzati: la colonna `lastPrice` di `AssetTable` e prezzo e PMC di
  `ExposureTable`, scritti come valuta con 2 decimali fissi. Un PEPE si legge `0,00 €`. Stessa regola dei prezzi dei lotti (C-97c-2):
  entrano. Fuori da AF e DV nessun altro prezzo `public` (il planner PAC tiene tutte le cifre).
- **L'arrotondamento.** `formatFixed` arrotonda il valore binario (`toFixed`), `formatPrice` il decimale più corto (Intl): solo un
  caso esattamente a metà può cambiare l'ultima cifra (`1.005` → `1.00` oggi, `1.01` dopo). È la regola già accettata in C-97c-1.
- **Il `NaN`.** `formatFixed` scrive `NaN`, `formatPrice` niente: i siti escludono già `null`, e un prezzo non numerico non arriva.

**Cancelli**:
- HTML (`htmlInterpolation.gate.test.ts`): `LineChart:837` passa `upper[dataIdx]`, una lettura per chiave calcolata, che il cancello
  accetta solo come primo argomento di un formattatore numerico. `formatPrice` entra in `NUMERIC_FORMAT_CALLS`, con la ragione: scrive
  cifre, i segni della lingua e un segno; `''` per un valore non numerico, mai il suo input.
- Denaro (`moneyRenderSites.test.ts`): il frammento di `PriceChartFull:1051` è registrato `public` e cambia: si aggiorna nella stessa
  modifica. Nessun sito nuovo: le righe con `formatCurrencyAmount*` sono esenti, e nessun altro letterale cambiato unisce un `currency` a
  un numero.

**E2E**: nessuno fissa un prezzo che cambia (tutti sopra 10: `12.34`, `95`–`777`, `123.45`).

**Test** (test-author): rossi in `candlestickChartHelpers`, `priceChartHelpers`, `providerProbe` (core-unit), `ProviderAssignmentSection`,
`PriceChartFull`, `LineChart`, `MeasurePanel`, `AssetTable` (con `AssetCard`, già montato lì), `ExposureTable` (component-unit), e un
file nuovo `AssetPriceSummary.test.ts` (registrato in component-unit); nel cancello HTML un caso della regola per `formatPrice`.

**Passi**:
1. ✅ **Cura pronta** (17/10): `files/scripts/c97c3_cure.py`, dry run pulito su 13 file (11 di prodotto più i due cancelli).
2. ✅ **Rossi** (17/10, test-author `c97c3-reds`): **28 rossi, 447 verdi** in 11 file, uguali nella mia corsia (carico 31,
   `files/logs/c97c3/10_my_reds.log`); tutti nei blocchi C-97c-3, ognuno sul suo motivo (oggi `0.00`, `0.0000`, `1.23`, `0.000003`,
   `0.0`, `0.123457`, `0`; il cancello riporta le due letture).
   - core-unit: `candlestickChartHelpers` 3, `priceChartHelpers` 2 (`buildDeltaHtml`), `providerProbe` 3, il cancello HTML 1 (più una
     guardia: `formatPrice(row.display_name)` resta riportato dalla regola dei nomi, un'opzione calcolata dalla sua);
   - component-unit: `AssetPriceSummary` 4 (file nuovo, registrato dopo `AssetTable.test.ts` in `front_component_unit`), `AssetTable` 3
     (colonna `lastPrice`, prezzo e Δ di `AssetCard`), `ProviderAssignmentSection` 2, `PriceChartFull` 2, `LineChart` 1, `MeasurePanel` 3,
     `ExposureTable` 4.
   - Nessuna asserzione esistente fissava un comportamento che cambia; `providerProbe.test.ts` fissa ora il browser a en-US per tutto il
     file (Node segue la lingua dell'host); `ExposureTable.test.ts`: i due oracoli della quantità passano a 10, stessi valori.
   - Due letture senza testid (`AssetCard`, il prezzo vivo; `MeasurePanel`, la riga in attesa): lette dal contenitore, senza aggiungere
     testid (nessun markup oltre la chiamata, regola del D-C97c-1).
   > **Note del test-author**: (1) `formatPrice` scrive `''` per null, undefined, NaN, dove `formatFixed` scriveva `NaN`: un limite di
   > banda o un valore di secchio mancante mostra vuoto; (2) la prova col prezzo nullo resta `0.00` (`Number(null)`); (3) svelte-check dà 6
   > errori in file d'altri (`periodChanges.ts`, `assetDetailRangeChange.ts`, `assetDetailLive.svelte.ts`, `UsersTab.svelte`): il client
   > generato è vecchio dopo l'avanzamento, `api sync` prima di `front check`; (4) i commenti del cancello che nominano i due formattatori:
   > la riga 140 entra nella cura (quella a 57 dà esempi).
3. ✅ **Cura applicata e verdi** (17/10, 17:3x–17:57): `c97c3_cure.py --apply` sui 13 file, più la riga 140 del cancello HTML
   («`formatFixed`, `formatPercent` or `formatPrice`»). L'unico `formatPrice` locale, quello di `LotCustodyModal`, scrive un numero o `—`:
   la fiducia per nome del cancello resta giusta. Gli 11 file e il cancello del denaro: **482/482** (carico 38). Poi
   `files/scripts/c97c3_light.sh`, una prova alla volta, carico < 50 (log `files/logs/c97c3/light_*.log`):

   | Prova | Esito |
   |---|---|
   | `dev.py api sync` | uscita 0, nessun file tracciato cambiato |
   | `dev.py test check-orphans` | ogni test registrato raggiungibile (il file nuovo compreso) |
   | `front-utility core-unit` (i due cancelli, gli aiuti dei grafici, la prova) | 211 file, 8 795 verdi |
   | `front-utility component-unit` | 180 file, 4 866 verdi |
   | `front-portfolio chart-safety-unit` (l'escape dei tooltip) | 8 file, 91 verdi |
   | `dev.py front check` | svelte-check 0/0 (i 6 errori visti dal test-author erano il client vecchio) |
   | Prettier sui 24 file | pulito |

4. ✅ **Doc** (17/10, modifica puntuale, pagina per sviluppatori senza traduzioni): `developer/frontend/i18n.md`, la frase sui due cancelli:
   il cancello HTML si fida di `formatFixed`, `formatPercent` **o `formatPrice`** («only those three names»). Nessun'altra pagina fissa le
   cifre di questi siti (grep dei nomi delle funzioni e di `2|4|6 dp`, `decimals`). Backlog: **W-B78** (le 10 cifre delle quantità scritte
   a mano in 10 punti di 9 file; una costante in `utils/core`, dopo la 1.3).
5. ✅ **Simulazione** (17/10, 17:58–18:01): `sim_cherry_pick.sh dev_release2 --docs` sui 27 file (il test nuovo, non tracciato,
   compreso), dev `685d76dab` (HEAD `6e503e0f6` antenato, 42 commit avanti; tocca due miei file condivisi, il backlog e
   `_frontend_utility.py`, in altre righe): 0 conflitti; `mkdocs build` stretto e `check-links` con uscita 0 sull'albero unito (log
   `files/logs/c97c3/20_sim.log`). `git diff --check` pulito. Handoff FROZEN; revisori X (AF) e Y (DV). Chiude C-97c.

### W-B70 (+ W-B77) — i parametri degli errori di campo, la descrizione unita oltre 500: cura ✅ (2026-10-17) — 🧊 FROZEN

**Base**: HEAD `a5d615fd7` = dev con C-97c-3 (`164babac1` → `e19f7c7e6`, CHANGELOG `a5d615fd7`). Via e decisioni D-W70-1…5 del
coordinatore (sopra, «W-B70 — analisi»). OK di scrittura: `PromoteMergeModal.svelte`, `TransactionBulkModal.svelte`; in BRIM solo
l'import, i doppioni e i siti di chiamata (la SEC9g di MF è in `search_asset_candidates_bulk`).

**Contratto — backend**:
- **`backend/app/utils/pydantic_errors.py`** (nuovo, una sola copia, W-B77):
  - `PLAIN_PARAM_TYPES = (str, int, float, bool, NoneType)`;
  - `loc_to_field(loc)`: gli indici saltati, `resolved_fields.` tolto davanti a un campo (H-41; innocuo per il BRIM, che non ha quel
    campo), `None` per un `loc` vuoto;
  - `error_params(error)`: il `ctx` dell'errore copiato quando ogni valore è dato semplice, `None` se manca, è vuoto o ne tiene uno che
    non lo è (l'eccezione di un `value_error`). Non guarda più `loc`: un errore di campo porta il suo contesto (D-W70-1).
- **Batch** (`transaction_batch_stages._parse_lenient`) e **BRIM** (`BRIMProvider._create_transaction`): `error_params` per l'errore
  solo **e per ogni sotto-errore impacchettato** (`multipleBusinessRuleErrors`, la nota di H), `loc_to_field` per il campo. Via
  `_PLAIN_PARAM_TYPES`, `_loc_to_field` e `_lone_error_params` dai due moduli (BRIM: la riga 95 e i due metodi statici).
- **L'effetto**, misurato su `TXPromoteResolvedFields` (17/10): `string_too_long` → `{max_length: 500}`; `greater_than` → `{gt}`;
  `greater_than_equal` → `{ge}`; `date_from_datetime_parsing` → `{error: <testo di pydantic>}`; `model_type` → `{class_name}`;
  `value_error`, `missing`, `extra_forbidden`, `string_type` → `None`. I testi in più sono innocui: il risolutore escapa ogni
  parametro di testo e nessuna traduzione li legge.
- La docstring di `schemas/transactions/batch.py:191` nomina la funzione nuova.

**Contratto — frontend**:
- `resolveValidationMessage.ts`: `string_too_long` → `transactions.pydantic.stringTooLong` («At most {max_length} characters», 4
  lingue); nel ramo dei built-in l'etichetta del campo passa da `escapeHtml` come negli altri due rami.
- `bulk/promoteHelpers.ts`: `TX_DESCRIPTION_MAX_LENGTH = 500` (il `max_length` di `TXCreateItem`, `TXUpdateItem` e
  `TXPromoteResolvedFields.description`), `textLength(text)` in punti di codice (come `len()` di Python), e
  `resolvePromoteAllFields(strategy, left, right)`: `{}` se i due lati non divergono, i campi del lato o l'unione, `null` quando
  l'unione supererebbe il limite.
- `PromoteMergeModal.svelte`: sotto la textarea il contatore `promote-merge-desc-counter` («{n} / {max}», `data-state` `ok`|`over`,
  muto o rosso in un ternario); oltre il limite la textarea `aria-invalid` (`aria-invalid:border-lf-danger`), il messaggio
  `promote-merge-desc-too-long` (`text-xs text-lf-danger`, `data-max`, `transactions.promote.descriptionTooLong`) e Conferma
  disabilitato (`disabled:opacity-50 disabled:cursor-not-allowed`), come `EventCreateMiniModal`. Solo ruoli.
- `TransactionBulkModal.svelte`, `mergeAllSuggestions`: `resolvePromoteAllFields`; una coppia `null` resta non promossa e si conta;
  alla fine `notify({name: 'tx.bulk.promote-all.left-for-manual-merge', detail: {pairs}, toast: {variant: 'warning', …}})` con
  `transactions.promote.mergeAllLeftTooLong` (plurale ICU). Mai un testo perso.

**Test** (due test-author in parallelo, file distinti): backend (il modulo nuovo, `utils pydantic-errors`; i tre test che fissano
`None` riscritti come rossi; i sotto-errori impacchettati filtrati) e frontend (Vitest: risolutore, aiuti, modale d'unione; un E2E
di «promuovi tutto», scritto e girato nello slot).

**Passi**:
1. ✅ **Cura pronta** (17/10): `files/scripts/wb70_cure.py` (dry run pulito su 8 file, uno nuovo; più le tre descrizioni del runner
   `_backend_services.py` che nominavano `_loc_to_field`) e `files/scripts/wb70_i18n.sh` (le tre chiavi con `dev.py i18n add`, poi
   `i18n check`).
2. ✅ **Rossi** (17/10):
   - **backend** (test-author `wb70-backend-reds`, corsia 6184, log `files/logs/wb70/01`–`04`):

     | Selettore | Rossi | Verdi | Oggi |
     |---|---|---|---|
     | `utils pydantic-errors` (file nuovo `test_utilities/test_pydantic_errors.py`, registrato in `_backend_utils.py`) | 51 | 10 | 49 casi: il modulo non c'è; 2 `TestOneCopy`: le due copie esistono ancora e nessuno importa il modulo |
     | `services brim-create-transaction` | 2 | 16 | `params` nulli dove `{max_length: 500}`, `{max_length: 36}` (`link_uuid`) |
     | `services transaction` | 5 | 125 | nulli dove `{max_length: 500}`, `{gt: 0}` ×2 (split, promote), `{ge: 0}` (update); l'impacchettato copia `object()` e un `ValueError` (risposta non serializzabile) |
     | `services transaction-decimal-places` | 8 | 193 | H-41: 4 casi × validate/commit nulli dove il contesto semplice di pydantic (atteso calcolato dagli errori stessi, nessun testo fissato) |

     Una cura simulata in memoria (`files/wb70_harness/`) porta tutto al verde salvo `TestOneCopy`, che vuole i file veri. Il ramo
     impacchettato del BRIM con un contesto non semplice non si raggiunge senza toccare il modello (ogni regola di `TXCreateItem` impacchetta
     dati semplici): coperto dal contratto di `error_params` e da `TestOneCopy`. Nessun `test_api` fissava `None` su un errore di campo.
     > **⚠️ Fuori pista**: una chiamata `--run-status` del test-author (senza test) ha usato `.testLog` di default nella mia corsia e ha
     > archiviato un log precedente in `.testLog/00_archive/logs_20261017_183605.tar.xz` (file ignorati, recuperabili).
   - **frontend** (test-author `wb70-frontend-reds`; uguali nella mia corsia, carico 11, `files/logs/wb70/10_my_front_reds.log`):
     **34 rossi, 97 verdi** in 3 file — `resolveValidationMessage.test.ts` 7 (la traduzione di `string_too_long`, l'etichetta escapata da
     `field` e da `loc`, la chiave nei 4 cataloghi), `promoteHelpers.test.ts` 19 (i nomi nuovi; la logica di oggi come guardie),
     `PromoteMergeModal.test.ts` 8 (contatore, `aria-invalid`, messaggio, Conferma disabilitato, punti di codice). Più l'E2E **PC7** in
     `tx-bulk-promote-cost-basis.spec.ts` (scritto, non girato: rosso atteso «la coppia da 501 resta due righe: atteso 2, ricevuto 1»).
3. ✅ **Cura applicata e verdi** (17/10, 18:3x–18:5x): `wb70_cure.py --apply` (9 file, uno nuovo), `wb70_i18n.sh` (le tre chiavi nelle
   4 lingue, `i18n check` stretto: 5 063 chiavi). In BRIM solo i blocchi permessi: l'import (l. 84), la costante (l. 93-97), i due
   metodi statici (l. 539-559), la docstring e i due siti di `_create_transaction`. Poi `files/scripts/wb70_light.sh`, una prova alla
   volta, carico < 50 (log `files/logs/wb70/light_*.log`):

   | Prova | Esito |
   |---|---|
   | `ruff check`, `black --check` sui 10 file Python | puliti |
   | `utils pydantic-errors` | verde (51 rossi + 10 guardie) |
   | `services brim-create-transaction` | verde (18) |
   | `services transaction` | verde (130) |
   | `services transaction-decimal-places` | verde (201) |
   | Vitest dei 3 file | 131/131 |
   | `front-utility core-unit` | verde |
   | `front-transaction tx-unit` | verde |
   | `utils gate-i18n-catalog`, `utils gate-i18n-usage` | verdi |
   | `dev.py test check-orphans` | ogni test registrato raggiungibile |
   | `dev.py front check` | 0/0, dopo un secondo `api sync` |

   > **⚠️ Fuori pista**: il primo `front check` ha dato 2 errori in `features/changelog/whatsNewStore.svelte.ts` (C-54, entrato con
   > l'avanzamento): il client generato, ignorato da git, era quello di prima dell'avanzamento. `api sync` (uscita 0, nessun file
   > tracciato cambiato) e `front check` 0/0. Lezione: dopo ogni avanzamento della base, `api sync` prima del primo `front check`.
4. ✅ **Doc** (17/10, docs-writer `46ade847`, solo EN, `mkdocs build` stretto e `check-links` verdi): `developer/backend/transactions/
   service.md` (la regola e la sua casa), `split_promote.md` (i `params` del rifiuto, il limite nel frontend), `developer/frontend/state/
   transaction-draft.md` (contatore, «Merge all», i test), `developer/architecture/patterns/brim_plugin_guide.md:456` (più una mia
   correzione: il `field` solo per l'errore di un campo, un sotto-errore impacchettato non ne ha), `user/transactions/index.en.md` (l. 49:
   **W-B73** chiuso, la modale offre descrizione e tag; l. 62: «Combine» lascia la coppia troppo lunga). Nessun timbro: la pagina utente
   ha già un debito di traduzione.
   > **Scoperte del docs-writer**: (1) un limite `Decimal` resta senza `params` (`Decimal` non è dato semplice; nei modelli delle
   > transazioni ogni `gt`/`ge` è su un intero), scritto nella pagina; (2) **W-B79**: `onPromotePair` della pagina Transazioni apre la
   > modale d'unione anche quando differiscono solo data o costo, che la modale non offre più (il corpo dice solo «Confirm promotion»):
   > nel backlog, dopo la 1.3.
5. ✅ **Slot** (via del coordinatore 18:5x, carico a 5 minuti < 50; `files/scripts/wb70_slot.sh`, log `files/logs/wb70_slot_*.log`,
   18:58–19:15): `db populate --force` sulla mia cartella, poi uno alla volta:

   | Prova | Esito |
   |---|---|
   | `front-transaction tx-bulk-promote-cost-basis` (con **PC7**) | 9/9 |
   | `front-transaction tx-bulk-promote-exec` | 9/9 |
   | `api transactions-validate` | 12/12 |
   | `api batch-split-promote` | 38/38 |
   | `api brim` | 118/118 |

   Porta 6184 libera dopo. Il rosso di PC7 è ragionato dal codice (oggi la coppia da 501 si unisce in una riga), non visto: la cura era
   già applicata quando lo slot è arrivato.
6. ✅ **Simulazione** (17/10, 19:16–19:18): `sim_cherry_pick.sh dev_release2 --docs` sui 29 file (i due nuovi, non tracciati, compresi),
   dev `a6adb0066` (HEAD `a5d615fd7` antenato; dev tocca solo il backlog, in altre sezioni): 0 conflitti; `mkdocs build` stretto e
   `check-links` con uscita 0 (log `files/logs/wb70/31_sim.log`; la stessa a 18:56 su `d9e9a88b2`). `git diff --check` pulito.
   Handoff FROZEN; H rivede W-B77.

### Revisioni dopo l'ingresso: MF-SEC9g (di E) ed E-19a, la guardia del gap-fix ✅ (2026-10-17, sola lettura, HEAD `c9ebc1102`)

W-B70 entrato: dev `41335f1e1` (`07fcf4303`), CHANGELOG `c9ebc1102`. `theme-roles --check` pulito sulla HEAD (le condizioni del
coordinatore dei colori per C-97c: classi invariate, il cancello pulito a ogni checkpoint, un colore solo col suo via).
- **MF-SEC9g** (`316f9c0d3`): **OK, nessun reperto**. Semantica identica: gli indici ISIN e ticker tengono i valori salvati nell'ordine
  dell'universo e si leggono con `.upper()` come l'uguaglianza di prima; un matcher compilato per ago con la stessa regola del testo
  vuoto; gli stessi campi del nome, nello stesso ordine, e le stesse porte di priorità. Il thread legge solo le viste semplici, costruite
  sul loop dagli attributi già caricati; `_add_candidate` legge esattamente i quattro campi della vista. Osservazione: il confronto dei
  nomi generici resta O(estrazioni × universo) di CPU, ora fuori dal loop.
- **E-19a, la guardia del gap-fix** (`e4a4af4e2`, doc `180e7b20d`): **OK**. Le righe sono quelle che `get_balances_at_end_of` somma
  (broker, data fino ad `as_of`, le stesse esclusioni; `amount` NOT NULL); il controllo di W-B74 prima; una query DISTINCT per
  checkpoint o verifica; il messaggio è testo semplice in `GapFixStep` (`{group.error}`): i codici citati sono sicuri. Nota: il 409 arriva
  in inglese in ogni lingua, come quello di W-B74 → **W-B80** (dopo la 1.3).
- Backlog: chiusi con i loro commit W-B43, W-B58, W-B59, W-B60 (miei) e W-B61, W-B62 (di X), entrati senza la riga ✅.

### W-B48 — gli ultimi selettori per testo nei due spec del data editor: analisi e cura ✅ (2026-10-17) — 🧊 FROZEN

Ogni sito della voce c'è ancora, circa 15 righe più in basso. Sostituzioni senza codice di prodotto:
- `asset-data-editor.spec.ts`: `/Import \(N\)/` (308, 322, 345, 359, 385, 414, 478, 492) → `data-import-confirm` con `data-valid-rows`
  (e `data-error-count`); `button:has-text("Save")` (231, 260, 279, 368, 423) → `asset-editor-save-btn`; `toHaveText(/Save \(\d+\)/)`
  (372) → il `data-badge` della scheda dei prezzi (`asset-editor-prices-tab` → `tab-badge`), lo stesso conteggio delle righe modificate;
  `button:has-text("Cancel")` (235, 292) → `asset-editor-cancel-btn`; `span.rounded-full` (274) → `tab-badge` con `data-badge` (li
  pubblica `ui/tabs/TabBar.svelte:201`).
- `fx-csv-import.spec.ts`: `'Import (2)'`/`'Import (1)'` (178, 196, 223, 264, 397, 479, 490) → `data-import-confirm` con
  `data-valid-rows`; `text=Discard import` (280) → `data-import-discard-confirm`; `hasText: 'Cancel'` (291) → `data-import-cancel`; il
  test 14 (315–336) senza i due `if (count() > 0)`: il banner c'è e nomina i due codici, prima e dopo lo scambio.
- **Due glifi** restano, entrambi in file di X: il ✕ del pannello dell'editor (`routes/(app)/assets/[id]/+page.svelte:2650`) e il ⇄
  dell'import FX (`FxDataImportModal.svelte:199-206`). Un selettore per ruolo leggerebbe titoli tradotti: chiesto l'OK per un
  `data-testid` ciascuno (`asset-detail-editor-close`, `fx-import-swap`).
- Prove: `front-asset asset-data-editor` e `front-fx fx-csv-import`, nello slot (circa 10 min).

**Decisione** (coordinatore, 17/10 19:4x): **via, con i due `data-testid`** (`asset-detail-editor-close`, `fx-import-swap`), solo
l'attributo, nient'altro nei due file di X (J ha la pagina dell'asset aperta alle righe 57/916, lontano da 2650). Slot di circa 10 minuti
da chiedere quando pronto.

**Passi**:
1. ✅ **Selettori** (17/10, test-author `wb48-selectors`, scritti e non girati): le sostituzioni della lista, verificate sui componenti;
   oltre la lista, con la sua ragione: il badge della scheda `'2'` esatto (le due righe importate), i due «non N righe» come
   `data-valid-rows` `'0'` e disabilitato (aspettano invece di passare subito), e il test 14 con un `not.toHaveText(prima)` dopo lo
   scambio (un banner che non si aggiorna non passa).
2. ✅ **I due `data-testid`** (17/10): `asset-detail-editor-close` sul ✕ (`routes/(app)/assets/[id]/+page.svelte:2650`) e `fx-import-swap`
   sul ⇄ (`FxDataImportModal.svelte`), solo l'attributo; poi il ✕ dello spec e **tutti gli otto** ⇄ dello spec FX su quei testid (sette
   oltre la lista della voce, lo stesso glifo). Prettier pulito sui quattro file; `theme-roles --check` pulito; `front check` 0/0 dopo un
   `api sync` (il client generato era di nuovo quello di prima dell'avanzamento: 7 errori nei file di X).
3. ✅ **Slot** (via del coordinatore 19:4x, insieme a W-B51; `files/scripts/wb4851_slot.sh`, log `files/logs/wb4851_slot_*.log`):
   `front-asset asset-data-editor` **30/30**, `front-fx fx-csv-import` **22/22** (dopo `db populate --force` sulla mia cartella).
4. ✅ **Checkpoint** (17/10, 19:5x) — 🧊 FROZEN: simulazione su dev `2fbbf4c4c` con `--docs` pulita (0 conflitti, build stretta e
   `check-links`), `theme-roles --check` pulito, `git diff --check` pulito, porta 6184 libera.

### W-B51 — la tolleranza dei duplicati BRIM sulle quantità crypto: analisi e cura ✅ (2026-10-17) — 🧊 FROZEN

**Stato reale**: `detect_tx_duplicates` (`backend/app/services/brim/brim_provider.py:2166`) cerca, per riga del report, le righe del broker
dello stesso tipo e giorno (e dello stesso asset, se risolto), poi tiene quelle con `abs(existing.quantity - tx.quantity) <=
QUANTITY_TOLERANCE` (`Decimal("0.0001")`, `:2207`, `:2256`) e la cassa uguale a `AMOUNT_TOLERANCE` (0,01).
- **Il caso vero, più comune dell'esempio della voce**: due acquisti ricorrenti da 10 € di BTC lo stesso giorno, 0,00015123 e
  0,00015098 BTC: stessa cassa, quantità a 2,5e-7 l'una dall'altra, quindi doppione: «probabile» se anche la descrizione coincide
  (un piano d'accumulo la ripete), e allora la seconda riga parte **deselezionata**; «possibile» altrimenti, selezionata con un avviso
  (`importDedup.ts`; la correzione è del test-author). Con le quantità esatte a 10 decimali (C-97a), 0,0001 è grosso per ogni token sotto il centesimo di unità.
- **L'uguaglianza esatta** sistema il reimport dello stesso file (la quantità salvata torna com'era scritta), ma perde un report di
  un altro formato che arrotonda (0,0002 contro 0,00015123 salvato): la riga tornerebbe «nuova», e un doppio import vero è peggio di un
  doppione segnalato.

**Proposta D-W51-1**: uguali alla precisione del meno preciso dei due: `|a − b| ≤ ½ unità dell'ultima cifra` della scala minore, la scala
letta senza gli zeri finali (`normalize()`: la lettura della colonna aggiunge zeri, `10` torna `10.000000`). 0,00015123 contro 0,00015098:
diversi; 0,0002 (un report a 4 decimali) contro 0,00015123: uguali; gli interi come oggi. La cassa resta a 0,01 (valuta, 2 decimali).
Un aiuto puro (`_same_quantity`) accanto al rilevatore; rossi prima: i due acquisti ricorrenti (oggi doppioni), con guardie per il
reimport identico, il report arrotondato e le quantità intere.

**Decisione D-W51-1** (coordinatore, 17/10 19:4x): **approvata con una guardia**: due quantità coincidono quando, arrotondate (half-up)
alla scala della meno precisa, sono uguali **e** `|a − b| ≤ 0,0001` (il limite di oggi: mai più largo di prima; 10 e 10,4 restano
distinte); la scala misurata sui valori `normalize()`. Rossi prima: 0,00015 contro 0,00008 (oggi doppioni), un 0,00015 di un report
arrotondato contro uno 0,000153 salvato (resta un doppione), il caso degli interi.

**Passi**:
1. ✅ **Cura pronta** (17/10): `files/scripts/wb51_cure.py`, dry run pulito; l'aiuto provato a parte su tutti gli esempi della decisione
   (anche 25 cifre, `None`, inf).
2. ✅ **Rossi** (17/10, test-author `wb51-reds`; uguali nella mia corsia, carico 32, `files/logs/wb51/10_my_reds.log`): `db brim`
   **4 rossi, 35 verdi**, la classe nuova `TestWB51QuantityOfADuplicate` in `backend/test_scripts/test_db/test_brim_db.py`:
   - rossi: 0,00015 contro 0,00008 e 0,00015123 contro 0,00015098 (oggi doppioni «probabili»); una quantità salvata illeggibile, testo
     `'n/a'` o `9e999` (+inf), che si legge `None`: oggi `TypeError` a `brim_provider.py:2256` (la cassa guardava già `None`);
   - guardie: il report arrotondato (0,00015 contro 0,000153 salvato), 10 e 10, la reimportazione identica, il valore salvato riletto
     con gli zeri (0,00015 → `0.000150`) in entrambi i versi, il pareggio half-up (0,000145 contro 0,00015), 10 e 10,4 distinti.
   > **⚠️ Fuori pista**: il mio esempio «`0.000153000` riletto» non esiste: la colonna completa a 6 decimali, e `0.000153` torna com'è;
   > il test-author ha usato `0.00015` → `0.000150`.
3. ✅ **Cura applicata e verdi** (17/10): `wb51_cure.py --apply` (`QUANTITY_MATCH_BOUND`, `_decimal_places`, `_same_quantity` accanto a
   `detect_tx_duplicates`; la docstring del rilevatore); `ruff`, `black` puliti; `db brim` **39/39**; `utils gate-event-loop-io` 14/14.
4. ✅ **Doc**: `developer/backend/brim/architecture.md`, la tabella della deduplicazione (la regola della quantità e della cassa).
   > **Scoperta**: il wizard ha una **copia** della regola, sul float e a 0,0001, per i doppioni fra file e col pool in attesa
   > (`importDedup.ts:145-157`, l'identità del gruppo con `toFixed(4)`): **W-B81**, proposta subito dopo.
5. ✅ **Slot** (con W-B48): `api brim` **118/118**, `api brim-scalable` **2/2**. Checkpoint FROZEN con W-B48 (sopra).

### W-B81 — i doppioni del wizard con la regola di W-B51: analisi e cura (2026-10-17) ✅

**Base**: HEAD `c97001b80` = dev con W-B48 e W-B51 (`080f7ee7f`, `52573b4aa`, `5c2faced1` → `4bc6b2ab1`, CHANGELOG `c97001b80`). Via del
coordinatore (17/10 19:4x): «Vitest first; `importDedup.ts:145-157` applies exactly D-W51-1; fold the `toFixed(4)` group identity onto
the same rule, no float compare on decimals; name the shared cases so backend and frontend pin the same table».

**Stato reale** (`frontend/src/lib/features/transactions/import/importDedup.ts`, `importTypes.ts`):
- `DedupKey` tiene quantità, importo e costo per unità come `number`; `buildDedupKey` legge `Number(tx.quantity ?? 0)`;
  `dedupKeysMatch` confronta in float a 0,0001 (quantità e costo) e a 0,01 (importo); `describeDedupKey` scrive `toFixed(4)`/`toFixed(2)`
  (0,00015123 e 0,00015098 hanno la stessa identità `0.0002`). Il wizard usa le chiavi solo attraverso le funzioni (`ImportWizardModal`,
  il pool in attesa); l'identità del gruppo vive nella sessione (nessuna memoria).
- In più, dai rossi: un NaN (`'n/a'`) combaciava con tutto (`Math.abs(NaN) > 0.0001` è falso), il float sbagliava il limite
  (100 contro 100,0001; −100 contro −100,01) e confondeva due testi a 18 decimali (`wei-apart`).

**Contratto**: un lettore esatto dei testi decimali semplici (segno, cifre, punto facoltativo; mai un esponente: un report scrive
decimali semplici, `SafeDecimal`), `sameDedupQuantity(a, b)` con la regola di D-W51-1 (half-up alla scala del meno preciso, `normalize`
dei testi, e `|a − b| ≤ 0,0001`) per quantità e costo per unità; l'importo entro 0,01 calcolato esatto; `DedupKey` con i testi esatti, e
`describeDedupKey` con il testo esatto di ogni numero. Un testo che non è un decimale semplice non fa chiave; **uno vuoto si legge `0`**
(decisione mia, il default del payload: una riga di cassa con la quantità svuotata incontra ancora il suo gemello in attesa).
`getDedupCurrency` rende l'importo come testo esatto; **un importo vuoto si legge `0`** come uno mancante e come la quantità (oggi
`Number('')` è 0; domanda del test-author, decisione mia). **Un numero finito** (i default `?? 0` del codice, un valore messo a run
time: il tipo dice testo) si legge come lo scrive JavaScript, l'esponente espanso (`1.5e-7` → `0.00000015`); un testo resta stretto
(`'1.5e-7'` illeggibile). Il confronto resta stretto: il vuoto diventa `0` solo nei lettori dei campi (`buildDedupKey`, `getDedupCurrency`).
Fuori ambito: i gettoni del confronto a N colonne (`CmpSource`, `ImportWizardModal.svelte:1718`, `toFixed(2)`) evidenziano le celle a
schermo, non decidono un doppione: restano.

**Passi**:
1. ✅ **Rossi** (test-author `wb81-reds`, `importDedup.test.ts`, in `front-utility core-unit`): **47 rossi, 72 verdi** (119); la tabella
   condivisa coi nomi del backend (`apart-at-5-decimals`, `recurring-buys-at-8-decimals`, `report-rounded`, `integers-10`,
   `integers-10-and-10.4`, `identical-reimport`, i due «padded», `half-up-tie`, `unreadable[text]`, `unreadable[inf]`), più
   `integers-10-read-back`, `bound-inclusive`, `wei-apart`, `negative-half-up-tie`; i letterali di `DedupKey` passati a testi. Poi due
   aggiustamenti chiesti: il vuoto si legge `0` in `buildDedupKey`, le attese di `getDedupCurrency` come testi. Terzo giro: l'importo
   vuoto si legge `0`, un numero finito come lo scrive JavaScript (esponente espanso), le forme accettate (`+0.5`, `.5`, `5.`, `' 0.5 '`,
   `-.5`), l'esponente anche finito (`'1.5e-7'`) illeggibile. **Rossi confermati da me** (17/10, carico 15): `importDedup.test.ts` **135
   test, 67 rossi, 68 verdi**; `importDuplicateResolver.test.ts` 54/54 (solo il commento di `:298`). Log `files/logs/wb81/50_reds_confirm.log`.
2. ✅ **Cura pronta**: `files/scripts/wb81_cure.py` (dry run pulito sui 2 file), l'aritmetica provata in node su tutta la tabella nei due
   versi (`files/wb81_check.mjs`).
3. ✅ **Doc**: `developer/frontend/components/features/import-wizard.md`, la tabella della firma (quantità, importo, costo per unità).
4. ✅ **Cura applicata** (17/10, `wb81_cure.py --apply`): `importTypes.ts` (`DedupKey` a testi, le tolleranze come testi) e
   `importDedup.ts` (`readExactDecimal` / `readFieldDecimal`, `exactText`, `atScale`, `withinExact`, `sameDedupQuantity` esportata,
   `sameDedupAmount`, `getDedupCurrency` a testo, `buildDedupKey`, `dedupKeysMatch`, `describeDedupKey` senza `toFixed`).
   > **Note implementazione**: un lettore solo, `readExactDecimal`: un testo decimale semplice, o un numero finito com'è scritto da
   > JavaScript con l'esponente espanso (`exactDecimal`); `readFieldDecimal` legge il vuoto come `0` (i due lettori dei campi). Le cifre
   > in `bigint`, nessun `Number` sulle cifre. Aritmetica provata in node prima (`files/wb81_check.mjs`, 21 casi nei due versi e il limite
   > dell'importo; `files/wb81_check2.mjs`, 35 casi del lettore).
   > **⚠️ Fuori pista**: `ImportWizardModal.svelte:1718` scrive `src.cashAmount.toFixed(2)`, ma `src` è un `CmpSource` del confronto a N
   > colonne (gettoni per evidenziare le celle), non una `DedupKey`: fuori ambito, non toccato. Gli E2E leggono l'identità del gruppo
   > dal testid (`import-wizard-resolver-compare-{key}`, `tx-import-duplicate-precedence.spec.ts:858`), mai un formato scritto a mano;
   > l'identità resta unica (`DuplicatesStep.svelte:149`, `{#each … (group.key)}`): due chiavi dello stesso testo combaciano.
5. ✅ **Verdi** (17/10, `files/scripts/wb81_light.sh`, carico 13–41, una alla volta; log in `files/logs/wb81/`):
   - Vitest dei 7 file dell'import (`importDedup`, `importDuplicateResolver`, `importMerge`, `importPairs`, `importRowState`,
     `importResolutionHelpers`, `ImportWizardModal`): **347/347**;
   - Prettier dei 4 file: pulito; `theme-roles --check`: pulito;
   - `api sync`: nessuna differenza tracciata;
   - `front-utility core-unit`: **217 file, 9 212 test** verdi; `front-utility component-unit`: **185 file, 4 923** verdi;
   - `front check`: **0 errori, 0 avvisi**.
   - Non girato: nessun E2E. Proposto facoltativo: `front-transaction tx-import-duplicate-precedence` (6 test, i gruppi tra file sul
     percorso dei dati veri).
6. ✅ **Backlog**: W-B81 ✅.

> **W-B81 entrata** (17/10 20:4x): dev `5890d512c` (`f5536f856` + `e8b29cc0e`), CHANGELOG `05b6b834e` (la riga di W-B51 estesa). E2E di
> conferma dopo l'ingresso, sul tip, chiesto dal coordinatore: `front-transaction tx-import-duplicate-precedence`
> (`files/scripts/wb81_post_e2e.sh`, dietro il cancello di carico).
> ✅ 17/10 20:50, carico 20–49: `api sync`, `db populate`, **`tx-import-duplicate-precedence` 6/6** (37,6 s) sul tip `05b6b834e`; porta 6184
> libera dopo. Log `files/logs/wb81/post_*.log`.

### Revisione dopo l'ingresso — Z-33, `redate_provider_events` (2026-10-17) ✅ OK

`backend/app/services/assets/event_store.py:101` (commit `60170aae5`, dev `51b5c8db1`), chiamata da `_settle_exchange_timezone`
(`refresh.py:513-574`). Verificato:
- l'evento si sposta solo se la storia fresca ha il suo tipo su S+1 e non su S (`event_target`); il resto della refresh non scrive
  nulla senza la storia piena o il fuso (`Nothing written…`), quindi nessuna riga nuova esiste prima del controllo;
- dal più recente al più vecchio: uno spostamento in avanti di un giorno non incontra mai l'evento successivo ancora da spostare
  (la chiave vecchia esce da `by_key` prima che entri la nuova);
- il tipo confrontato con `str(...).strip().upper()` su `AssetEventType` (`StrEnum`: il valore), come `fresh_events` (`refresh.py:263`);
- l'unica FK verso `asset_events` è `transactions.asset_event_id` (RESTRICT, `models.py:964`): la fusione ripunta le transazioni
  prima del `delete`; nessun vincolo d'unicità sugli eventi (`models.py:1037`), quindi un evento manuale sullo stesso giorno convive;
- lo SPLIT porta con sé solo le sue ADJUSTMENT del giorno vecchio, con un `UPDATE` che salta il controllo dei saldi: il cammino
  controlla la fine di ogni giorno (`transactions/balances.py:96-130`), e spostare in avanti le righe dello split le allinea alle
  date del broker; il saldo di S scende sotto zero solo se gli scambi di S fossero in unità dopo lo split, cosa che un report non
  scrive. Il costo medio mette prima le aggiunte e poi le riduzioni dello stesso giorno (`financial_math/average_cost.py:24`),
  come per uno split datato giusto da sempre (New York);
- prove: 8 test di eventi e transazioni (`test_asset_source_refresh.py:1537-1740`): spostamento solo con la storia, SPLIT con la sua
  ADJUSTMENT, ADJUSTMENT già sul giorno giusto intatta, il dividendo che non sposta la sua transazione, nessun'altra transazione,
  la fusione col gemello, nessun doppione accanto allo spostato.
Esito: **OK**, nessun reperto.

### K3 — analisi in sola lettura (2026-10-17, base `05b6b834e`)

Via del coordinatore (17/10 20:4x): «Start K3 now: analysis first. Read B-47/B-48 first». W-B65 di B è in dev (`cde76dc54`):
`TransactionBulkModal.svelte` è libero.

**Stato reale, voce per voce**

1. **🔗 Eventi collegabili nel Bulk** (`TODO_FUTURI.md:56`, da P2-6). Backend pronto: `POST /transactions/events/suggest`
   (`api/v1/transactions.py:246`, `services/transactions/event_suggestions.py`), **12** test API (`test_events_suggest.py`; il TODO dice 8
   e un percorso vecchio). Nessun chiamante nel frontend. Lacune trovate:
   - **due fonti per una mappa**: `suggest_events_bulk` scrive a mano DIVIDEND→DIVIDEND, INTEREST→INTEREST, ADJUSTMENT→PRICE_ADJUSTMENT/SPLIT;
     `EVENT_TYPE_METADATA` (`schemas/transactions/type_metadata.py:479`) dà anche MATURITY_SETTLEMENT→INTEREST: il suggerimento non propone
     mai una scadenza a un INTEREST;
   - `tolerance_days ≤ 7` (`schemas/transactions/event_suggest.py:32`), contro lo slider del Bulk 0–14 (`TxBulkToolbar.svelte:71`) e il
     picker 1–30 (`AssetEventPicker.svelte:40`);
   - lista senza tetto, una SELECT per richiesta; a pari distanza l'ordine del DB; il candidato non porta `notes` (il picker le mostra);
   - `AssetEventPicker` (`features/transactions/events/`, 498 righe) legge `query_events_bulk` (`POST /assets/events/query`): **ogni tipo**
     nella finestra, quindi dalla UI un DIVIDEND si collega a uno SPLIT; la finestra calcolata nel browser (`new Date` + `toISOString`,
     `:105-112`) perde un giorno a un bordo quando attraversa un cambio d'ora;
   - **la regola 9 non guarda il tipo dell'evento**: `schemas/transactions/transactions.py:141` (tipo compatibile e asset),
     `_validate_asset_event_link` (`services/transactions/validation.py:25`: esiste e stesso asset). I calcoli leggono il legame per tipo
     dell'evento (`financial_math/splits.py:40` `load_split_links`: ogni transazione legata a uno SPLIT, «each caller decides»); dal lato
     dell'evento P-10 (decisione 27) già rifiuta il cambio di tipo di uno SPLIT collegato.
2. **B-47** confermata: `CompactCashCell.handleBlur` (`features/transactions/form/CompactCashCell.svelte:100-103`) emette sempre la forma
   mostrata (`0.01` per `0.010000`), `setCash` (`TransactionFormModal.svelte:1238`) la prende, `serializeOps` confronta il testo → «scartare?».
   Nello stesso giro: l'`$effect` di sincronia confronta con `Number` (`:74-86`); `txCreateItemToPendingOp` legge la cassa con `Number`
   (`TransactionBulkModal.svelte:2228-2234`; la quantità due righe sopra è già esatta); `isDraftReadyForValidation` legge `amount === '0'`
   (`transactionTypeStore.ts:273`: `0.00` è «pronto»); il ramo FX di `isFormComplete` `Number(...) !== 0` (`TransactionFormModal.svelte:733-736`).
3. **B-48** confermata: `ExactQuantityInput` (`components/ui/input/ExactQuantityInput.svelte:108`) conta intere (15) e decimali (10) a parte;
   il backend tiene 15 cifre significative in tutto (`db/precision.py:41`, `REAL_SIGNIFICANT_DIGITS`). Commento vecchio
   `e2e/transactions/tx-bulk-promote-cost-basis.spec.ts:117`. La cella della cassa non ha nessun tetto di cifre (stessa classe).
4. **K-2** confermata: percorso lento, il form o il wizard si aprono subito (`TransactionBulkModal.svelte:471-482`) e, a caricamento finito,
   `if (!formOpen) scheduleAutoOpen(...)` (`:500-502`) riapre quello che l'utente ha chiuso.
5. **K-3** confermata: `resetAll` (`:898-910`) senza `|| d.inaccessible` (c'è in `resetRow`, `:890`).
6. **K-4** confermata, **più grave del titolo**: `ensureCurrenciesLoaded($currentLanguage)` (`:487`) è letto in modo sincrono nell'`$effect`
   d'apertura; un cambio di lingua lo rilancia, e l'effetto ricostruisce `ops` dall'intento (`:441-449`) e azzera divisioni, promozioni e
   problemi: **le modifiche non salvate si perdono**. Cura: `untrack`.
7. **V-37b**: punto di partenza confermato, ⚡ `disabled={!isFormComplete}` (`TransactionFormModal.svelte:1583`); gli errori propri portano
   già al primo campo (`focusFirstLocalError` `:1109`, `validateNow` `:1122`). Stima di V: 1,5–2 giorni; 2–4 chiavi (mie), `form.en.md`,
   galleria, `tx-fx-completeness:262/:363/:389`. Il controllo delle cifre significative di B-48 entra nel passo del formato.
8. C-65a con X: fuori da K3 (dopo, come deciso).

**Sotto-lotti proposti** (un checkpoint ciascuno): **K3a** (K-4, B-47, K-2, K-3, B-48: sicurezza dei dati prima, ~mezza giornata);
**K3b** (🔗: un motore, banner del Bulk, picker sul motore, regola 9b, ~1,5–2 giorni); **K3c** (V-37b, ~1,5–2 giorni, se c'è tempo).

**Decisioni chieste**: D-K3-1 una mappa sola da `EVENT_TYPE_METADATA` (il suggerimento propone anche MATURITY_SETTLEMENT a INTEREST);
D-K3-2 regola 9b alla scrittura (un legame a un evento di tipo non compatibile → 400 con codice e parametri, tradotto; le righe vecchie
restano finché il legame non cambia); D-K3-3 il picker sul motore (solo tipi compatibili, finestra lato server fino a 30 giorni);
D-K3-4 il banner del Bulk (una riga per transazione col candidato più vicino e «Collega», scelta se più di uno, «Collega tutti» solo per
le righe con un candidato solo); D-K3-5 `tolerance_days ≤ 30`, tetto della lista, spareggio (distanza, data, id), `notes` nel candidato;
D-K3-6 il tetto delle 15 cifre significative anche sulla cassa; D-K3-7 V-37b nella 1.3 o dopo.

**Decisioni del coordinatore** (17/10 20:45, tutte approvate): D-K3-1 una mappa da `EVENT_TYPE_METADATA`; D-K3-2 regola 9b alla
scrittura (400 con codice, tradotto; le righe vecchie restano finché il legame non cambia); D-K3-3 il picker sul motore, finestra lato
server fino a 30 giorni; D-K3-4 il banner come proposto; D-K3-5 `tolerance_days ≤ 30`, tetto della lista, spareggio (distanza, data, id),
`notes` nel candidato, `api sync` ok; D-K3-6 le 15 cifre significative anche sulla cassa, prop additiva `maxSignificantDigits` su
`ExactQuantityInput` ok; **D-K3-7 V-37b nella 1.3, dopo K3b** (il developer, 13/10: «se è facile lo farei subito, altrimenti dopo la 1.2»).
Scrittura ok sui file di K3a e K3b (nessuno aperto altrove); markup nuovo solo ruoli; le classi di palette di `AssetEventPicker` restano.
Un checkpoint per sotto-lotto; K3a: prima i rossi, prima la sicurezza dei dati.

**Regole colore per K3** (coordinatore colori, 17/10 21:48; nessun lavoro di colore in sospeso sugli 8 file):
- le **categorie restano** (aspettano la designer): in `TransactionBulkModal` il viola/indaco della coppia (9 punti), in `TxBulkBanners` e
  `TxFormPairSection` la coppia e il chip del cambio (2 + 4), in `AssetEventPicker` la mappa dei tipi d'evento (righe 84–86, 12 punti);
- il banner di K3b **riusa `InfoBanner`** (già importato in `TxBulkBanners`) con il suo tono, come gli altri banner lì: nessuna tinta fatta
  a mano;
- in `AssetEventPicker` un tipo d'evento nel markup nuovo prende il colore dalla mappa esistente: nessuna classe di palette nuova;
- `theme-roles --check` pulito a ogni checkpoint.

### K3a — sicurezza dei dati del Bulk e del Form (2026-10-17, ⏸️ parcheggiato il 19/10)

**Contratto della cura** (i rossi lo fissano prima):
- **K-4**: `TransactionBulkModal.svelte:487`, la lingua letta con `untrack`: un cambio di lingua col Bulk aperto non rilancia l'effetto
  d'apertura, le righe e le modifiche restano. (Oggi `currentLanguage` cambia da `LanguageSelector`, Preferenze e `login`, `auth.ts:129`:
  percorso latente, il rosso imposta lo store.)
- **B-47**: `CompactCashCell` al blur emette solo se l'importo o la valuta cambiano per valore (`exactDecimalEqual` col valore ricevuto);
  la sincronia dall'alto confronta per valore esatto, non con `Number`. Un focus e un blur senza modifiche non cambiano la riga: niente
  «scartare?». `txCreateItemToPendingOp`: la cassa letta come testo esatto (segno tolto come per la quantità), con un aiuto puro in
  `txPayloadHelpers.ts`. `isDraftReadyForValidation`: una cassa zero in qualunque forma (`0.00`) non è pronta (`exactDecimalSign`).
  Il ramo FX di `isFormComplete` resta: l'input filtra i caratteri e `Number` è esatto sullo zero, nessun difetto osservabile.
- **K-2**: l'apertura automatica del percorso lento avviene una volta: chiuso dall'utente prima della fine del caricamento, il form o il
  wizard non si riapre.
- **K-3**: `resetAll` salta il segnaposto `inaccessible`, come `resetRow`.
- **B-48 + D-K3-6**: `decimalDigitCounts` (`utils/core/parseDecimalInput.ts`) conta anche le cifre significative, come il backend
  (`db/precision.py:168` `_digit_counts`: zeri iniziali e finali esclusi, lo zero ne ha 1); `ExactQuantityInput` prop additiva
  `maxSignificantDigits` (rosso: `aria-invalid`, `digitsValid` e `valid` falsi); `CompactCashCell` prop additiva `maxSignificantDigits`
  (`aria-invalid` e il bordo `--lf-danger` nel suo `<style>`); il form passa 15 alla quantità e a ogni cassa (singola, coppia, FX), il
  valore fuori tetto è un errore proprio del form (V-37: Apply bloccato, ⚡ porta al campo, nessuna richiesta) e sotto il campo compare
  `transactions.errors.significantDigitsExceeded` (`{max: 15}`, già nelle 4 lingue: nessuna chiave nuova). Il commento di
  `e2e/transactions/tx-bulk-promote-cost-basis.spec.ts:117` aggiornato.

**Passi**: 1. rossi (test-author); 2. cura; 3. verdi leggeri; 4. E2E nello slot; 5. doc; 6. backlog (K-2…K-4 in `38_postReleaseBacklog`;
B-47 e B-48 sono nella sezione di B: chiusura chiesta al coordinatore); 7. simulazione e checkpoint.

1. ⏳ **Rossi** (test-author `k3a-reds`, 17/10): primo giro **26 rossi Vitest + 1 E2E**. `bulk/TransactionBulkModal.test.ts` nuovo
   (montaggio del Bulk con Form e wizard finti, registrato in `component-unit`): K-4, K-2 (creazione e import), K-3; `CompactCashCell` (B-47 ×3,
   B-48), `TransactionFormModal` (B-47, B-48 ×3), `ExactQuantityInput`, `parseDecimalInput` (10), `transactionTypeStore` (zero ×3). E2E
   `tx-bulk-operations.spec.ts` «B-47: a focus and a blur on the cash of a saved DEPOSIT…» (la chiusura chiede di scartare).
   > **⚠️ Fuori pista** (dal test-author): (a) il tetto delle 15 cifre rende **PC5** (`tx-bulk-promote-cost-basis.spec.ts`, regressione di
   > C-46: la barra di selezione confrontava doppi) impossibile da digitare: sotto 15 cifre significative due decimali diversi sono due doppi
   > diversi (DBL_DIG). Decisione mia: il soggetto di C-46 passa al Vitest del Bulk con le righe iniettate come da un import (guardia, verde);
   > l'E2E PC5 diventa l'E2E di B-48 (il form rifiuta le 18 cifre). (b) Cinque casi del Form («exact quantity contract») e uno di
   > `tx-fx-completeness` digitano 18 cifre: stesso soggetto con valori nel dominio (≤ 15 significative; sotto 1e-6 dove il punto è «mai
   > `Number`», perché `String(Number(x))` scrive l'esponente). (c) **K-3b, trovata ora**: dopo un reset, se la metà leggibile è quella che
   > riceve, la coppia sparisce dalla griglia: il passo 1 di `collapsePairedOps` legge la cassa ignota del segnaposto come 0 e nasconde la
   > metà leggibile. Cura nello stesso lotto: il segnaposto è sempre il partner nascosto della metà leggibile, come nella prima costruzione.

> **⏸️ Parcheggiato il 19/10** (fermo del developer del 17/10 21:47; alla ripartenza K3 è fra gli ampliamenti che il developer sta leggendo,
> N91). Il secondo giro del test-author era finito ma **mai girato**: K-3b (la metà ricevente, col reset di riga e con «Reset all»), PC5 diviso
> (la guardia di C-46 nel Vitest del Bulk; l'E2E PC5 diventa quello di B-48), i sei casi portati nel dominio (5 del Form, uno di
> `tx-fx-completeness`). La cura non è mai stata applicata.
> - **Dove**: cartella di sessione di W (`e71e0e34-…`), `files/parked/`: `k3a-reds-20261019.patch` (10 file: i 9 tracciati e
>   `bulk/TransactionBulkModal.test.ts` nuovo; 1 858 righe), `k3a_cure.py` (la cura, dry run pulito su 8 file), `k3a_light.sh`, gli hash
>   (`k3a-parked-sha256.txt`) e lo stato (`k3a-parked-state.txt`). La patch ricostruisce byte per byte i file del 17/10 su `05b6b834e`
>   (provata su una copia di HEAD, `shasum -c`).
> - Worktree riportato a HEAD per quei file e il non tracciato tolto; `git apply --check` della patch sul worktree pulito: OK.
> - **Con la regola del 19/10 sono domande, non decisioni**: le scelte fatte da me in questa sezione (PC5 diviso, i valori nel dominio,
>   K-3b nello stesso lotto) tornano al coordinatore con le opzioni alla ripresa; D-K3-1…7 aspettano la lettura del developer (N91).

### Revisione dopo l'ingresso — J-57, sul percorso dell'import (2026-10-19) ✅ OK, due domande

Ripartenza del 19/10 (fase 2): base `3d5678283`. J-57 è `b7e2bb3bd` (dev `539371064`). Sola lettura, solo il percorso dell'import:
plugin BRIM → wizard → Bulk → validate/commit. La decisione del developer (19/10): J-57 resta, «Auto» senza niente da mediare è
rifiutato, lo 0 manuale (il regalo) è permesso nel form e nel wizard, e il messaggio suggerisce «Manuale e 0». J sta analizzando come
completarlo nel wizard: questa revisione serve a J e al coordinatore.

**Verificato, OK**
- Il salvataggio di un import passa da `execute_batch`. Il pool conta le righe del batch già scritte (flush). Il ricevente di un TRANSFER
  media il broker del partner fino alla data del partner, senza le due gambe (`auto_cost.py:266-279`), così un trasferimento intero
  tiene il suo costo. Le righe Auto non ancora costate restano fuori (N84), e una rifiutata resta fuori dalle successive: la cascata è
  voluta e fissata dal test R4 di J (`test_two_auto_adjustments_on_an_empty_broker_are_both_refused`).
- Un pool di unità gratuite (Manuale 0) dà una media 0 valida (test C2 di J), e la riga costata così esce da `pending`: `Currency`
  (`schemas/common.py:159`) non ha `__bool__`. Nessun rifiuto falso a valle.
- Nessun numero sbagliato a video: l'anteprima Auto del form viene dalla risposta della validazione (`WacPreviewSection` ←
  `wac_results`), e una riga rifiutata non ha risultato.
- I due codici hanno la chiave nelle 4 lingue, con il suggerimento «0 se sono arrivate gratis» per `autoCostEmptyPool`.
- Lo 0 manuale è raggiungibile nell'import: in Manuale `buildCreatePayload` manda `{amount: '0'}` (`txPayloadHelpers.ts:281`), il
  backend lo accetta (`test_manual_zero_cost_on_a_broker_that_never_held_the_asset_commits`), e `remainingTodos` lo conta come risposta
  a un todo del costo (`bulkTodos.ts:23-24`).

**Dove J-57 tocca l'import.** I plugin non mandano mai Auto: solo Crédit Agricole e Intesa mettono `manual`, e solo quando il report dà
il costo. Auto lo mette il frontend, in due punti:
1. il form apre in Auto una riga senza modalità (`TransactionFormModal.svelte:398`, `:472`, `:475`), e `applyFormPayload` deriva Auto
   per una riga con modalità `null` (`TransactionBulkModal.svelte:817-823`): aprire nel form una riga importata in entrata e premere
   Applica la mette in Auto;
2. un todo bloccante del costo si chiude con Auto (`bulkTodos.ts:22`): `gap_fix_cost` del gap-fix, `demerger` di Danske Bank,
   `corporate_action` del CSV generico.

Quelle righe sono posizioni che LibreFolio non ha. Con J-57 finiscono in `autoCostEmptyPool` alla validazione, dove prima diventavano
un acquisto gratuito in silenzio: giusto. Però il todo sparisce come «risposto», e al suo posto arriva un errore di validazione.

**Domande per J e il coordinatore**
- **Q-J57-1 · Auto risponde ancora a un todo bloccante del costo?**
  - (a) com'è oggi;
  - (b) un todo bloccante del costo si chiude solo con un valore, Manuale e 0 compreso: il plugin sa già che non c'è niente da mediare
    *(consiglio)*;
  - (c) come (b), e in più il form apre quella riga in Manuale vuoto invece che in Auto.
- **Q-J57-2 · Lo 0 di un plugin senza modalità.** Una riga importata con un costo 0 e senza modalità si apre nel form in Auto, e lo 0
  diventa il segnaposto della valuta (`TransactionFormModal.svelte:400-402`): il costo del plugin si perde. Oggi non succede (nessun
  plugin manda uno 0 senza modalità), ma è la stessa radice di W-B82 qui sotto, e la stessa cura la chiude.
- **Nota sulla cascata, per il wizard.** In un import con un ADJUSTMENT in entrata su A e poi un TRANSFER A→B, tutti e due sono
  rifiutati: il secondo con «nessuna unità detenuta», benché A le abbia (sono della prima riga, ancora senza costo). È la scelta di J
  (R4). Conviene che il wizard porti l'utente alla prima riga rifiutata: sistemata quella, le altre passano alla validazione dopo.

**Trovato fuori da J-57 (mio, latente): W-B82.** Un costo che il plugin o il gap-fix dà senza modalità si perde nel Bulk.
`txCreateItemToPendingOp` lascia la modalità a `null`, e `buildCreatePayload` manda un costo solo in Auto o in Manuale
(`txPayloadHelpers.ts:277-283`). Così la proposta del gap-fix con il costo per unità della banca (`brim_gap_fix.py:213`) arriverebbe
senza costo, rifiutata con `costBasisRequired`. Latente: oggi nessun plugin riempie `unit_cost` (solo Danske Bank costruisce posizioni,
e senza costo). Cura proposta, dopo il via: all'ingresso dell'import un costo senza modalità diventa Manuale, e il gap-fix scrive
`cost_basis_mode="manual"` come Crédit Agricole e Intesa; un rosso Vitest e uno pytest.

### Fase 2 della ripartenza — tre analisi in sola lettura (2026-10-19, base `3d5678283`)

Regola del 19/10: nessuna decisione di prodotto da W. Ogni scelta che cambia ciò che l'utente vede, i numeri o i dati è una
domanda al coordinatore, con le opzioni e il consiglio. Nessun codice: si implementa solo dopo il via. Le tre analisi leggono il
codice di `3d5678283`; l'inventario (B) unisce quattro passate in sola lettura e le mie verifiche delle voci di W.

#### A. N78-bis — il costo ammesso e obbligatorio, calcolato dal backend

Il developer, testuale: «la regola deve venire esposta dal backend nell'endpoint che lo espone».

**Oggi, il backend**
- `GET /transactions/types` pubblica per tipo `cost_basis_mode` e, per le coppie, `cost_basis_pair` [chi cede, chi riceve], coi
  valori `forbidden` / `optional` / `required_qty_pos` (`schemas/transactions/type_metadata.py:36-37`, `:127-136`). TRANSFER
  `["forbidden", "required_qty_pos"]` (`:314`), ADJUSTMENT `required_qty_pos` (`:359`), ogni altro tipo `forbidden`.
- Il validatore legge la tabella con tre funzioni: `_cost_basis_rule` (il lato viene dalla quantità: sopra zero riceve,
  altrimenti cede; `:403-415`), `cost_basis_required` (`:418-426`) e `cost_basis_allowed` (`:429-436`).
- Regola 12 (`schemas/transactions/transactions.py:177-185`): una modalità (`auto`, `auto-detail`, `manual`) solo dove
  `cost_basis_allowed`.
- Regola 12b (N78, W-B72, `:186-195`): un costo senza modalità solo dove `cost_basis_allowed`, **oppure su un ADJUSTMENT con
  quantità sotto zero**: il costo di consegna della decisione 47, scritto da `_handover_cost` quando un TRANSFER si divide o si
  cancella, e che un update può impostare.
- Quindi un ADJUSTMENT in uscita accetta un valore ma nessuna modalità, e l'eccezione non è nella tabella pubblicata.

**Oggi, il frontend.** La formula `cbRule !== 'forbidden' && !(cbRule === 'required_qty_pos' && quantità <= 0)` è ricopiata a
mano, e il Form decide per nome di tipo:

| Punto | Cosa fa | Sull'ADJUSTMENT in uscita |
|---|---|---|
| `txPayloadHelpers.ts:270-284` `buildCreatePayload` | manda Auto, o un valore Manuale, solo dove la formula ammette un costo | il costo di consegna digitato non parte |
| `txPayloadHelpers.ts:296-337` `buildUpdateDiff` | confronta e manda il costo con la stessa formula | la modifica del costo di consegna non parte |
| `txPayloadHelpers.ts:342-372` `diffDualItem` | idem per le coppie del Form | — |
| `txPayloadHelpers.ts:456-457` `buildDualCreatePayloads` | porta Auto al ricevente | — |
| `TransactionBulkModal.svelte:802-826` `applyFormPayload` | toglie modalità e costo dove la formula non lo ammette | il costo salvato sparisce dalla riga: la chiusura chiede di scartare, il salvataggio non lo manda |
| `TransactionBulkModal.svelte:203-213` `fieldsFromTx` | Manuale dove il tipo ammette un costo | — |
| `TransactionBulkModal.svelte:719-725`, passo 3 di `collapsePairedOps` | Auto al ricevente di una coppia nuova | — |
| `TransactionFormModal.svelte:744` `showCostBasisField` | `TRANSFER` o `ADJUSTMENT`, per nome | la sezione appare anche dove il valore non partirà |
| `TxFormSingleSection.svelte:294` | la sezione in linea dell'ADJUSTMENT | offre anche Auto, che la regola 12 rifiuta in uscita |

**L'effetto** (letto nel codice, non visto a schermo): su un ADJUSTMENT in uscita il Form mostra il costo e lascia cambiarlo, ma
il valore non parte mai. La modifica si perde in silenzio, e il costo di consegna è il costo a cui i lotti cedono le unità
(decisione 47): un numero.

**Proposta: il backend calcola, il frontend legge**
1. **Backend**: una funzione sola in `type_metadata.py`, `cost_basis_answer(tx_type, direction)`, con `direction` fra `in`
   (quantità sopra zero), `out` (sotto zero) e `zero`. Rende `{value, auto}`:
   - `value`: `required` (un valore, o Auto dove `auto` è vero), `optional` o `forbidden`;
   - `auto`: se si può scegliere Auto.
   Le regole 12 e 12b e `cost_basis_required` la chiamano, così il validatore e la risposta pubblicata non possono più
   divergere. Valori di oggi:

   | Tipo | `in` | `out` | `zero` |
   |---|---|---|---|
   | ADJUSTMENT | `required`, Auto | `optional`, senza Auto (l'eccezione) | `forbidden` |
   | TRANSFER | `required`, Auto | `forbidden` | `forbidden` |
   | ogni altro tipo | `forbidden` | `forbidden` | `forbidden` |
2. `GET /transactions/types` pubblica per tipo `cost_basis_rules: {in, out, zero}` già calcolati; `api sync`.
3. **Frontend**: `getCostBasisAnswer(type, quantitySign)` al posto di `getCostBasisRule` e della formula. I nove punti leggono
   `value` e `auto`; il Form mostra la sezione quando `value` non è `forbidden` per il segno della quantità, e offre Auto solo
   quando `auto`.
4. **Test**: un pytest «di contratto», per ogni tipo e direzione la risposta pubblicata coincide con ciò che le regole 12 e 12b
   accettano e rifiutano (una regola nuova non può dimenticare l'endpoint); Vitest sui nove punti; un E2E del Form sul costo di
   consegna.

Stima: backend circa mezza giornata, frontend circa una, doc un quarto.

**Domande**
- **Q-N78-1 · Il costo di consegna nel Form.** Con la risposta pubblicata, un ADJUSTMENT in uscita mostra un costo scritto a mano,
  senza Auto.
  - (a) modificabile *(consiglio: il backend lo accetta già, e il developer chiede che il frontend «la legga e basta»)*;
  - (b) solo in lettura: il valore scritto dal backend alla divisione;
  - (c) nascosto.

  E l'etichetta: «Costo di consegna», o la stessa «Costo per unità» dell'entrata?
- **Q-N78-2 · I campi vecchi dell'endpoint.**
  - (a) il campo nuovo accanto a `cost_basis_mode` e `cost_basis_pair`, che restano una release segnati deprecati *(consiglio:
    l'endpoint è pubblico)*;
  - (b) sostituirli subito.

#### B. Inventario degli endpoint che espongono regole

Il developer, testuale: «siccome abbiamo vari endpoint con le regole, verifica che anche loro siano aggiornati rispetto il sistema
ad ora». Le voci di W le ho verificate io; quelle degli altri workstream le ho solo lette.

| # | Endpoint o regola | Il frontend | Allineato oggi? | Deriva | Di chi | Cura proposta |
|---|---|---|---|---|---|---|
| 1 | `GET /transactions/types`: modi e segni di asset, cassa e quantità, `requires_link`, `event_compatible`, `pair_form_layout`, `promote_from`, `swap_group` | `transactionTypeStore.ts` (`getTypeRule`) | sì, per i campi letti | le coppie scritte a mano: la lista dei tipi di coppia (`TransactionBulkModal.svelte:1992`), il lato che cede per `type === 'TRANSFER'` (`:576`, `:954`, `:976`, `:1679`; `TransactionActionModal.svelte:76`), il controllo «opposto» (`:2572-2573`, `:2897-2898`, `:2922-2923`) invece di `promote_from.field_constraints`; le liste di tipi del wizard (`FixFlaggedStep.svelte:307-309`); pubblicati e mai letti: `split_into`, `pair_field_constraints`, `validation_codes` | W | W-B46 (le coppie dalla tabella); le liste del wizard dai segni pubblicati; i campi inutili letti o tolti |
| 2 | `GET /transactions/types`: il costo (`cost_basis_mode`, `cost_basis_pair`) | la formula ricopiata in nove punti | **no** | l'eccezione dell'ADJUSTMENT in uscita | W | N78-bis (A) |
| 3 | `GET /transactions/types`: `event_types[].compatible_tx_types` | mai letto | **no** | il validatore non guarda il tipo dell'evento (`services/transactions/validation.py:25-31`); i suggerimenti hanno una mappa loro senza MATURITY_SETTLEMENT→INTEREST (`event_suggestions.py:43-45`); il picker elenca ogni tipo (`AssetEventPicker.svelte:123`, `:233`) e ha le sue icone (`:83-92`) | W | K3b, già deciso (D-K3-1…3: una mappa da `EVENT_TYPE_METADATA`, regola 9b, il picker sul motore); le icone da `getEventTypeEmoji`, i colori della mappa restano |
| 4 | Le guardie dello SPLIT con ADJUSTMENT collegate senza costo, al cambio di tipo e alla cancellazione (P-10/27, X-R48/49: `services/assets/event_store.py`, `_reject_split_retype_without_costs`, `:572`, `:643`; `services/assets/split_guard.py:22`) | — | non pubblicate | la UI le scopre al salvataggio | X e W | Q-INV-3 |
| 5 | `GET /brokers/import/plugins`: `supported_extensions`, `report_roles[].extensions` | in parte: le estensioni scritte a mano in quattro punti (`ImportWizardModal.svelte:144`, `UploadStep.svelte:97`, `BrokerImportFilesModal.svelte:358`, `routes/(app)/files/+page.svelte:831`) | sì, per caso | coincide solo finché nessun plugin pubblica un'estensione nuova | W (i primi tre), H (la pagina File) | `accept` e il controllo dall'unione delle estensioni pubblicate |
| 6 | L'upload BRIM (`api/v1/brokers.py:600-660`) | — | — | accetta qualsiasi estensione: un file che nessun plugin legge è salvato | W | Q-INV-1 |
| 7 | La dimensione massima dell'upload (`max_upload_mb`, `brokers.py:631-643`) | il wizard e la modale dei report usano i 10 MB di default di `FileUploader.svelte:19`, la pagina File passa il setting (`files/+page.svelte:824`, `:831`) | **no** | con un limite cambiato dall'admin il wizard rifiuta a 10 MB, o lascia arrivare un 413 in inglese | W | passare il setting come la pagina File |
| 8 | `GET /assets/provider`: `params_schema` (`FAProviderParamField`, `schemas/provider.py:120-135`) | form dinamico (`components/assets/ProviderAssignmentSection.svelte`, `params_schema` a `:61`) | **può divergere** | lo schema è scritto a mano nel plugin, separato dal modello Pydantic che valida, e non sa dire min e max; lo Scheduled Investment non pubblica i limiti di N73 (`schemas/assets/scheduled_investment.py:35-38`) | X | lo schema generato dal modello, con min e max; i limiti di N73 pubblicati |
| 9 | `GET /fx/providers` | solo campi descrittivi | sì | — | — | — |
| 10 | I cataloghi dei segnali (`/signals/preview`, i cataloghi di FX e asset) | `schemaMapper.ts:98-125` legge min, max, default ed enum | sì | i segnali solo del browser (seno, lineare, composto) hanno limiti loro, ma non vanno al backend | Y | — |
| 11 | `GET /risk/catalog`: `parameters_schema` | il laboratorio non lo legge: 0,95, 1 e 30 scritti a mano (`riskAnalysisHelpers.ts:291`, `:328-351`) | sì, oggi | se un plugin cambia default o limiti, il frontend non segue | da assegnare | default e limiti dal catalogo |
| 12 | `GET /tools/catalog` (PAC): il contratto generato | in parte: `maxlength="120"` (`BrokerEditor.svelte:149`, `ManualAccountDialog.svelte:44`, `LiquidityStep.svelte:163`, `:209`) non è nel contratto (quale campo: da verificare), `max="100"` a mano (`TargetInputCell.svelte:16`, `RoutingStep.svelte:261`, `FxStep.svelte:339`) | da verificare | — | PAC, da assegnare | i limiti dal contratto generato |
| 13 | `GET /plugin-settings` | `PluginSettingsForm.svelte`, `pluginSettingsForm.ts` | sì | — | — | — |
| 14 | `GET /system/instance`: `password_rules`, la registrazione | letti; `passwordRules.ts:16` è solo un ripiego | sì | lo username (3–50, `schemas/auth.py:30`, `:60`) non è pubblicato | **A** | segnalato ad A |
| 15 | Limiti senza endpoint, copiati a mano: i tetti delle richieste in blocco e i 100 anni (`api/bulkBatches.ts:15-25` contro `utils/date_range_limits.py:20-30`), il pavimento 1900 (`utils/rangeChange.ts:16`), i 500 caratteri della descrizione (`promoteHelpers.ts:76`) | copie | sì, oggi | nessuna fonte unica | Z (bulkBatches), W (descrizione), da assegnare (rangeChange) | Q-INV-2 |
| 16 | `MAX_BULK_WRITE_ITEMS` (10 000, `date_range_limits.py:36`) | nessuna copia | **no** | un CSV di prezzi o cambi oltre 10 000 righe riceve un 422 | X | dividere le scritture, o avvisare prima |
| 17 | Le cifre decimali (nessun endpoint) | il Form: quantità 15 intere e 10 decimali (allineato), la cassa senza limiti (B-48, D-K3-6, in K3a parcheggiato); i default 12/12 di `ExactDecimalInput` e `ExactQuantityInput` sono la colonna dei prezzi | **no** per le cifre significative | nessun input applica le 15 cifre significative che il backend chiede a ogni colonna `RealDecimal` (`db/precision.py:128`): prezzi e cambi accettano 24 cifre | W (Form, K3a), X (editor di prezzi e cambi) | il `maxSignificantDigits` di K3a anche negli editor di X |
| 18 | L'anno fra 1900 e 2200 di ogni calendario (`CalendarMonth.svelte:221-222`) | scritto a mano | sì, oggi | vale per ogni data, non solo per i piani | UI condivisa, da assegnare | i limiti come prop, dai limiti del backend |
| 19 | Le date delle transazioni | `SingleDatePicker` porta a oggi del browser | sì | — | W | N74 (C) |

**Correzioni alle passate di lettura** (verificate da me): `TxFormSingleSection.svelte:223-224` (15/10) è il secondo campo della
quantità, non la cassa, che non ha limiti (riga 17); e i selettori di data delle transazioni hanno un massimo, oggi del browser
(`SingleDatePicker`, `allowFuture` falso).

**Domande**
- **Q-INV-1 · L'upload BRIM di un file che nessun plugin legge.** (a) com'è: salvato, nessun plugin compatibile; (b) 415 con le
  estensioni ammesse *(consiglio)*.
- **Q-INV-2 · I limiti copiati a mano (riga 15).** (a) pubblicarli in `GET /system/instance`, come le regole delle password
  *(consiglio)*; (b) un test per ognuno che confronta la copia col backend; (c) lasciarli.
- **Q-INV-3 · Le guardie dello SPLIT (riga 4).** (a) pubblicarle, perché la UI le mostri prima del salvataggio; (b) restano al
  salvataggio *(consiglio per la 1.3, se il rifiuto di oggi è già tradotto: da verificare con X)*.

#### C. N74 — il limite in avanti della data di una transazione

Decisione del developer (19/10): da «oggi + 1 anno» a «domani del server», codice `dateOutOfRange`; il client ha già il suo limite.

**Oggi**
- `transaction_batch_stages.py:167-179`: `TRANSACTION_DATE_YEARS_AHEAD = 1`, e `transaction_date_bounds()` prende oggi da
  `today_date()`, in UTC. `check_dates()` (`:188-221`) legge le create, gli update che cambiano la data e la data di una
  promozione.
- Ogni ingresso passa da `execute_batch`: l'import BRIM (la conferma del Bulk) e il gap-fix compresi.
- Il commento del codice spiega l'anno: «a year covers the time zones and the settlement dates a broker's report puts ahead». È
  proprio il caso che N74 chiude.

**Quale «oggi».** Ci sono due funzioni. `today_date()` è UTC (`utils/datetime_utils.py:87`). `latest_range_end()` è la data
locale del server più un giorno (`:108-120`), ed è già il tetto dei prezzi e dei cambi scritti a mano (N83, `stored_date_bounds()`,
`utils/date_range_limits.py:74`). Proposta: le transazioni usano lo stesso `stored_date_bounds()`, così un solo «domani del
server» vale per transazioni, prezzi e cambi.

**I plugin di import**

| Plugin | La data della riga | Futura? |
|---|---|---|
| Fineco | «Data valuta» per prima, poi «Operazione» (`broker_fineco/plugin.py:284-285`) | **sì**: un acquisto di oggi ha valuta T+2, fino a quattro giorni di calendario sul fine settimana |
| Disnat | la data dell'operazione; il regolamento solo se manca (`broker_disnat/plugin.py:194`) | di rado |
| Danske Bank | le righe di custodia regolate dopo la fine del file di cassa sono scartate come `not_yet_settled` (`broker_danske_bank/plugin.py:898-906`) | no |
| Scalable | le righe non eseguite sono saltate (`_scalable.py:339-342`) | no |
| CSV generico | la colonna che sceglie l'utente (`broker_generic_csv/plugin.py:552`) | se l'utente sceglie una data valuta |
| Intesa | «Data», la data contabile (`broker_intesa/plugin.py:194`) | no |
| gli altri | la data dell'operazione o un timestamp | al più un giorno avanti per il fuso: coperto da «domani» |
| gap-fix | `checkpoint.as_of`, la data di verità del report (`brim/brim_gap_fix.py:211`) | no |

**I report di esempio**: nessuna data di riga dopo il 20/10/2026. I CSV non ne hanno; negli XLSX, letti con openpyxl, le sole
date più avanti sono scadenze di BTP dentro le descrizioni («BTP OTHER 1/9/2030» in `credit_agricole-conti.xlsx`, «BTP 1/12/2026»
in `credit_agricole-export.xlsx`).

**Domanda**
- **Q-N74-1 · Le righe Fineco con la data valuta oltre domani.**
  - (a) il plugin le tiene da parte con un avviso («non ancora regolata: reimporta il report dopo il <data>»), come fa Danske Bank
    *(consiglio)*;
  - (b) arrivano al Bulk e la validazione le rifiuta con `dateOutOfRange`: l'utente le deve deselezionare a mano;
  - (c) Fineco data le righe con «Operazione». Le date cambierebbero rispetto agli import già fatti, e il controllo dei doppioni
    non riconoscerebbe più le righe salvate: sconsigliata.

**Test da cambiare**
- `backend/test_scripts/test_services/test_transaction_decimal_places.py`:
  - gli aiuti `_a_year_after` e `_resolve_day` (~:2081-2092) e gli id `today-plus-one-year-plus-one-day` /
    `today-plus-one-year-the-last-day` (~:2070-2077) diventano «domani» e «dopodomani»;
  - `_assert_refused_on_its_date` (`:2113`, i `params` `{min, max}`);
  - i test a `:2140`, `:2158`, `:2176` (rifiutati) e `:2199` (accettato fino al massimo);
  - le docstring `:67-73` e `:2129`;
  - `:2243`, il pavimento, non cambia.
- `frontend/src/lib/features/transactions/resolveValidationMessage.decimals.test.ts:284` (`max: '2027-10-17'`) e i commenti `:47`
  e `:280`: solo testo.
- Restano: `test_brim_db.py:436` (data fissa, 2025-01-15 più un giorno), `test_brim_gap_fix.py:1555-1562` (l'anno 9999),
  `test_asset_source_upsert_guards.py:956` (un commento).
- Nuovi: un rosso per «dopodomani rifiutato» e uno per «domani accettato», con l'orologio del server a ridosso della mezzanotte
  (un oggi iniettato); per Fineco, se Q-N74-1 è (a).

**Doc e CHANGELOG**: `developer/backend/transactions/service.md:255-285` (il limite, il perché, l'esempio «2027-10-17»);
`developer/architecture/patterns/brim_plugin_guide.md:1125` («today (UTC) one year on»); il commento di
`TXValidationCode.DATE_OUT_OF_RANGE` (`schemas/transactions/batch.py:129`); una riga 🔄 nel CHANGELOG.

**Il client**: `SingleDatePicker` (`components/ui/date/SingleDatePicker.svelte:67`, `:154`, `:284`) non offre date future e porta
una data digitata a oggi del browser: già dentro il limite nuovo.

Stima: backend circa un'ora più i test; Fineco circa mezza giornata se (a); doc circa un'ora.

#### C-bis. Q-N74-1 — le righe Fineco con la data valuta futura sono già complete? (2026-10-19, sola lettura)

Il developer, testuale: «ho bisogno che mi confermi che le righe "future" contengono già tutto, so per esperienza che altri broker,
ad esempio Intesa, per le righe future non ancora contabilizzate alcuni campi li lascia vuoti, con questa logica scarto le righe
future, perché negli export futuri cambieranno».

**I dati che abbiamo non bastano per rispondere.** Non esiste nel repository una riga Fineco con la data valuta futura rispetto al
suo export, né due export dello stesso periodo.
- I 4 report d'esempio (`brim_providers/sample_reports/fineco-export.csv`, `fineco_variant_a.csv`, `fineco_btp_market.csv`,
  `fineco_btp_placement.csv`) sono sintetici: aggiunti col plugin (`98c78f981`, 25/07/2026; `7778f7ba5`, 12/08/2026), con intestatari
  e dossier inventati e nessuna data di export nel file. Le righe sono del 2023–2024, e alcune date un export vero non le avrebbe: un
  rimborso di domenica 13/10/2024 con la valuta lo stesso giorno, un altro di domenica 01/09/2024 regolato martedì 03/09.
- L'unico fixture Fineco scritto nei test (`test_brim_providers.py:2529`) è un rimborso sopra la pari, senza date future.
- I `broker_reports` di una corsia popolata sono copie degli stessi esempi (`upload_broker_reports`,
  `test_db/populate_mock_data.py:3536-3563`), e Fineco non è nemmeno nella mappa: popolare non aggiunge nulla. (La mia corsia non
  esiste più: `/tmp` è stato svuotato; non l'ho ripopolata.)

**1 · I campi delle righe.** Negli esempi ogni riga di compravendita ha tutto pieno: quantità, divisa, prezzo, controvalore,
commissione. I campi vuoti dipendono solo dal tipo di riga: `Cambio` sulle righe in euro, le tre colonne delle commissioni dei fondi
sulle righe che non sono fondi, quantità e prezzo su dividendi e cedole. La valuta è a +2 giorni dall'operazione (+4 per un
venerdì), lo stesso giorno per gli aumenti di capitale. Ma sono righe vecchie e inventate: dicono come il plugin legge un export
completo, non come Fineco scrive una riga non ancora regolata.

**Che cosa farebbe oggi il plugin con una riga provvisoria a campi vuoti** (letto nel codice):
- quantità o controvalore vuoti diventano 0 (`broker_fineco/plugin.py:310-311`, `_parse_fineco_number(...) or Decimal("0")`);
- una divisa vuota diventa EUR (`:308`);
- una data valuta vuota ricade sulla data dell'operazione (`:285`).

Una compravendita col controvalore vuoto entra quindi a 0 €, senza avviso: è il rischio che il developer descrive, e vale qualunque
sia la scelta sulle date. → **W-B83** (archiviata).
> **⚠️ Corretto il 19/10**, nell'analisi del lotto qui sotto: una quantità vuota **non** entra a 0. La regola 10 rifiuta la riga già
> in lettura (`qtyPositive`, `qtyNegative`) e il wizard la mostra come riga in errore. Solo il controvalore vuoto entra in silenzio.

**2 · Lo stesso movimento in un export successivo.** Non verificabile: nessuna coppia di export dello stesso periodo. Le due BTP
hanno lo stesso dossier ma mesi diversi (maggio–giugno e settembre 2023), senza movimenti in comune. Se un campo cambiasse, il
controllo dei doppioni (`detect_tx_duplicates`) confronta giorno, tipo, asset, quantità (la regola di W-B51) e l'importo entro 0,01:
una riga reimportata con la data valuta spostata, o un controvalore corretto, non sarebbe riconosciuta, ed entrerebbe una seconda
volta.

**3 · Ordini non eseguiti o non contabilizzati.** Il formato non ha una colonna di stato: le colonne lette sono 0–14, e `can_parse`
chiede Operazione, Data valuta, Isin e Controvalore. Il plugin riconosce cinque descrizioni («Compravendita titoli», «Dividendo»,
«Stacco Cedole», «Rimborso», «Aumento capitale») e salta ogni altra con un avviso (`:299-303`). Il report è «Movimenti Dossier
Titoli», i movimenti del dossier: dal nome, movimenti registrati e non ordini, ma né il codice né gli esempi lo provano. La pagina
utente dice «Beta — tested with sample files», e che Fineco dà un Excel che l'utente salva in CSV.

**4 · Gli altri plugin**

| Plugin | La data della riga | Le righe non definitive |
|---|---|---|
| Danske Bank | la valuta (`Arvopäivä`), poi l'operazione (`broker_danske_bank/plugin.py:274-275`) | le operazioni regolate dopo la fine del file di cassa restano fuori con un avviso, «arriveranno al prossimo import» (`not_yet_settled`, `:903`, testo `:1246`); quelle non eseguite o non contabilizzate escluse con un avviso (`status`, `:488`, `:525`) |
| Disnat | l'operazione; il regolamento solo se manca (`broker_disnat/plugin.py:194`) | — |
| CSV generico | la prima colonna di data nell'ordine del file dell'utente, fra `date`, `data`, `settlement_date`, `value_date`, `trade_date`… (`_detect_columns`, `broker_generic_csv/plugin.py:488-511`) | — |
| Scalable | l'operazione | le righe non `executed`/`settled` non entrano, con un avviso (`_scalable.py:339-344`) |
| Bitvavo | l'operazione | le righe non «Completed» saltate con un avviso (`broker_bitvavo/plugin.py:174-175`) |
| Investimental | l'ultimo aggiornamento dell'ordine | gli ordini cancellati o rifiutati saltati, con un riepilogo (`:242-254`, `:334`) |
| Crédit Agricole, Directa, DEGIRO, Saxo, InvestEngine | l'operazione; il report ha anche la valuta, che il plugin non usa per la data | — |
| gli altri | l'operazione o un timestamp, senza colonna di stato (ricerca per parole, non ogni riga letta) | — |

Solo Danske Bank data con la valuta per prima scelta, come Fineco, e mette già da parte le operazioni non ancora regolate:
l'opzione (a) di Q-N74-1 è il suo comportamento.

**Che cosa servirebbe per rispondere a 1–3.** Due export veri del developer dello stesso dossier:
1. uno con un'operazione degli ultimi uno o due giorni lavorativi, la cui data valuta sia ancora futura al momento dell'export;
2. uno dello stesso periodo qualche giorno dopo, a regolamento avvenuto;
3. meglio ancora, con un ordine aperto non eseguito (un limite lontano dal prezzo).

Si confronta la stessa riga campo per campo nei due file, e si guarda se l'ordine aperto compare. I file restano fuori dal
repository (dati privati, skill `real-data-copy`); nel piano vanno solo gli esiti, senza valori. In alternativa basta che il
developer guardi in Fineco un'operazione di ieri: c'è già nei «Movimenti Dossier Titoli», con quantità, prezzo e controvalore pieni?

**Per la decisione.** L'opzione (a), tenere da parte le righe con la valuta oltre il «domani del server», non dipende dalle risposte
a 1–3: è la scelta prudente, ed è quella di Danske Bank. Da sola però non copre una riga provvisoria la cui valuta è già passata
quando si importa un file vecchio di qualche giorno: nel file la riga resta com'era all'export, e Fineco non scrive la data
dell'export. Per quel caso serve W-B83: una compravendita con quantità o controvalore vuoti non entra a 0.

### N74 · Fineco opzione (a), W-B83 e le righe sicure — analisi (2026-10-19, sola lettura, base `b82208bed`)

Il developer su Q-N74-1, testuale: «si si, fai come dice l'opzione a, ma non fare un avviso, solo una nota, o forse nulla, e
piuttosto scriviamo questo principio nella skill che spiega come fare i plugin, si devono importare solo le date sicure».

Il lotto del coordinatore:
1. Fineco, opzione (a): le righe con la valuta oltre domani restano fuori, senza avviso; una nota breve se esiste un canale
   informativo, altrimenti niente;
2. W-B83 nello stesso spirito;
3. il principio nella skill `brim-plugin` e, se ha le regole obbligatorie, nella guida dei plugin (docs-writer);
4. Danske: solo una segnalazione.

**Il canale della nota esiste.** È `BRIMNotice(severity="info")` (`schemas/brim.py:516`, «info = explanatory (blue)»).
- Il wizard mostra le note in blu, sotto «Note informative», separate da «Da verificare» in ambra (`ImportWizardModal.svelte:2432-2447`,
  `BrimNoticeList.svelte`).
- Scalable lo usa già per lo stesso caso: `scalable_not_executed`, «… were not executed … and were not imported. An order executed
  later comes with the next export» (`_scalable.py:103-107`).
- **Da sapere**: ogni nota, anche info, apre una finestra di conferma blu quando si lascia l'analisi: «Note dall'importazione —
  L'importazione ha lasciato N note … Leggila prima di continuare» (`ImportWizardModal.svelte:3116-3118`, `:4741-4743`).

→ Uso la **nota**: un codice, il conteggio e le righe d'origine come evidenza, il testo tradotto per codice
(`importWizard.brimNotice.<code>`). Se il developer non vuole la finestra, si passa a «niente» togliendo la nota.

**La correzione di W-B83.**
- Una **quantità vuota** non entra a 0: la regola 10 rifiuta già la riga in lettura (`qtyPositive`, `qtyNegative`,
  `schemas/transactions/transactions.py:158-161`). Il wizard la mostra come riga in errore.
- Un **controvalore vuoto** entra invece in silenzio a 0 €: la regola 7 chiede solo che la cassa ci sia, e la 11 salta il segno sullo
  zero (`:132-133`, `:169-173`). Succede per un BUY, per un rimborso (SELL a 0 €, cioè la perdita di tutto il costo), e anche per un
  dividendo o una cedola.

**La cura proposta**, un solo file di prodotto (`broker_fineco/plugin.py`):
1. **la data.** Se la data della riga (la valuta, o l'operazione se la valuta manca) viene dopo `latest_range_end()`
   (`utils/datetime_utils.py:108-120`), la riga resta fuori intera: niente transazione, niente FEE della variante B, niente
   INTEREST del rimborso sopra la pari. `latest_range_end()` è il domani del server, lo stesso dei prezzi e dei cambi (N83);
2. **i campi.** Una compravendita (BUY o SELL, il rimborso compreso) senza quantità o senza controvalore resta fuori intera, allo stesso
   modo;
3. **le note.** Una nota sola per motivo, `severity="info"`:
   - `fineco_not_yet_settled`: «N righe non ancora regolate (valuta dopo domani): non importate, arrivano col prossimo export»;
   - `fineco_incomplete_rows`: «N compravendite senza quantità o controvalore: non importate, arrivano col prossimo export».

   Ognuna porta `context.count` e le righe d'origine come evidenza, come Scalable. Il testo del plugin è nella lingua dell'export,
   l'italiano. Le chiavi `importWizard.brimNotice.fineco_*` vanno nelle 4 lingue, in `frontend/src/lib/i18n/importWizard/*.json`, via
   `dev.py i18n add`: un file condiviso;
4. **la versione.** `plugin_version` da 1.1.0 a 1.2.0: i file già analizzati diventano vecchi e si rianalizzano
   (`brim/brim_provider.py:908-911`), così la regola vale anche per i report caricati prima;
5. **la docstring** del modulo: le date e le note.

I report d'esempio non cambiano esito: le righe sono del 2023–2024, tutte complete.

**I rossi previsti** (test-author, in `backend/test_scripts/test_external/test_brim_providers.py`, accanto a
`test_fineco_bond_redeemed_above_par_splits_interest`). I CSV in `tmp_path`; il domani del plugin fissato con `monkeypatch`, per
non dipendere dall'orologio.

| Caso | Oggi | Dopo |
|---|---|---|
| valuta dopo domani | entra | fuori, nota `fineco_not_yet_settled` con `count` e la riga come evidenza |
| valuta domani, valuta oggi | entra | entra (guardia) |
| valuta vuota, operazione dopo domani | entra | fuori |
| un dividendo dopo domani | entra | fuori |
| una riga della variante B dopo domani | entra con la sua FEE | fuori, nessuna FEE |
| un rimborso sopra la pari dopo domani | SELL più INTEREST | fuori |
| un BUY senza controvalore | BUY a 0 € | fuori, nota `fineco_incomplete_rows` |
| un SELL senza quantità | errore `qtyNegative` | fuori, nessun errore, la nota |
| in ogni caso | — | nessuna nota `warning` nuova |
| i 4 report d'esempio | — | lo stesso esito (guardia) |

**I test da girare**, corsia 6184, leggeri, uno alla volta col carico sotto 50, nessuno slot pesante:
- `external brim-providers`, filtrato su Fineco, poi intero se il carico lo permette;
- `utils gate-plugin-i18n-ownership` e `dev.py i18n check`;
- ruff e black sul plugin;
- per la doc, `mkdocs build` stretto e `check-links` sull'albero simulato;
- nessun E2E: non c'è codice nuovo del frontend, e la lista delle note è già coperta.

**Doc**
- docs-writer, solo EN:
  - `user/transactions/import/fineco.en.md`, «Good to know»: le date e le righe lasciate fuori;
  - `developer/backend/brim/architecture.md#plugin-fineco`;
  - `developer/architecture/patterns/brim_plugin_guide.md`: un punto nuovo fra le regole obbligatorie («Import philosophy»,
    `:159-193`), e la riscrittura del paragrafo a `:1125`, che oggi dice il contrario: «Emit the date the report states, even one a
    few days ahead, such as a settlement date».
- io: la skill `brim-plugin`, con la regola obbligatoria 9, «solo righe sicure».
- CHANGELOG 🔄: la riga la propongo io.

**Danske (punto 4, solo una segnalazione).** `excluded_not_yet_settled` ed `excluded_status` (righe non eseguite o non contabilizzate)
escono come `severity="warning"` (`broker_danske_bank/plugin.py:1499-1501`). Sono in ambra, sotto «Da verificare», e fanno della
finestra di conferma «Avvisi rilevati … Alcune transazioni potrebbero essere state saltate».
- Per coerenza con Fineco e con Scalable (`scalable_not_executed`, che è una nota), queste due andrebbero abbassate a nota.
- Gli altri motivi di esclusione di Danske restano avvisi: righe senza controparte, ambigue, fuori dalla copertura della cassa, di
  tipo sconosciuto, invalide.

**Domande**
- **Q-N74-2 · Il perimetro di W-B83.** Il coordinatore dice «compravendita»: propongo BUY e SELL, il rimborso compreso perché è una
  SELL.
  - (a) solo questi;
  - (b) anche i dividendi e le cedole senza controvalore, e l'aumento di capitale senza quantità *(consiglio: è lo stesso
    principio; oggi un dividendo vuoto entra a 0 €, e un aumento di capitale vuoto è un errore di validazione)*.
- **Q-N74-3 · La soglia.** Come deciso, resta fuori solo una riga con la valuta dopo domani: una con la valuta di domani, non ancora
  regolata, entra. Se il developer vuole solo righe regolate, la soglia diventa «dopo oggi». *(Consiglio: dopo domani. È lo stesso
  limite del batch, dei prezzi e dei cambi; la riga ha già i suoi numeri dall'esecuzione, e W-B83 ferma quelle incomplete.)*
- **Q-N74-4 · Il limite del batch** (N74 vero e proprio, analisi C) nello stesso lotto? *(Consiglio: sì. È lo stesso domani,
  `stored_date_bounds()`; il paragrafo della guida cambia comunque; i test sono quelli elencati in C.)*
- Resta com'è: con la valuta vuota si usa la data dell'operazione, come dice la pagina utente.
