# Rapporto R — run finale con coverage (albero candidato al tag)

> Sessione **R**, sera del 13/10/2026. Solo misura e classificazione: nessun file di codice, test o configurazione
> toccato. Corsia esclusiva `--test-port 6176 --data-dir /tmp/librefolio-r2-r-cov`. Rapporto della run precedente
> (12/10, base `a5653f9ef`): `rapporto-R-run-completa-coverage.md`, nella stessa cartella.

## 0. In breve

| | |
|---|---|
| **Base** | `10e646f799777028386a24057aab22e68a0e423d` (`dev_release2`: treno 97 + CHANGELOG), verificata da `libreFolio_R_final_prep.sh` (HEAD, albero pulito, lock JS invariato, corsia libera) |
| **Comando** | `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc LIBREFOLIO_TEST_STARTUP_TIMEOUT=900 pipenv run python dev.py test --coverage --fresh-run --cov-clean-backend --cov-clean-backend-e2e --workers 2 --test-port 6176 --data-dir /tmp/librefolio-r2-r-cov all`, **un'invocazione sola** |
| **Preparazione** | `front build --debug` + `mkdocs build` prima della run (21:35 → 21:37, 2 min): il backend condiviso è partito in pochi secondi |
| **Durata** | 21:37:55 → 00:21:54 = **2 h 44 min** (il 12/10: 4 h 21 min) |
| **Esito** | **rc = 0 · 15/15 categorie verdi · «ALL TESTS PASSED»** |
| **Test** | pytest **12 936 ✓ / 0 ✗** (28 skip voluti) · vitest **11 515 ✓ / 0 ✗** · Playwright **1 221 ✓ / 0 ✗** (32 skip voluti), nessun flaky (retries 0) |
| **Rossi** | **0**: nessun rilancio necessario, nessun difetto di prodotto da segnalare |
| **DB al seed** | dopo **ogni** categoria frontend, salvo la differenza tollerata da V (372 tassi MOCKFX dopo `front-fx`) e due scritture di prezzi correnti (§3) |
| **Coverage** | backend da test **91,54 %** (righe+archi; righe 93,57 %, rami 84,84 %) · backend da E2E 29,32 % · JS/Svelte **71,17 % statement**, 62,83 % rami — **le cifre E2E del JS sono limiti inferiori (C-69, I1)** |

**Rossi per classe**: (a) carico 0 · (b) ambiente 0 · (c) interferenza 0 · (d) test 0 · (e) prodotto 0.

**Rispetto al 12/10** (29 rossi, tutti E2E): le cure hanno chiuso tutto, e i gruppi che allora erano rossi qui sono
verdi uno per uno (§1.3). Il carico però è stato molto più basso (media 8,9 contro 37,9): la run dimostra che le
cure reggono a carico normale, non che reggono a carico 100.

---

## 1. Esecuzione

### 1.1 Ambiente

- Worktree portata in fast-forward dal coordinatore a `10e646f79`. `node_modules` è quello del 12/10: il lock JS è
  invariato da `a5653f9ef` (in `package.json` sono cambiati solo gli script `pre*` del catalogo i18n), quindi niente
  nuovo `npm ci`.
- Venv `LibreFolio-SAUMUTtc` con `uvicorn[standard]` 0.52.4: uvloop 0.23.0 e httptools 0.9.0 importabili.
- Data-dir della corsia azzerata prima della run. Mai `./dev.py` nudo, mai `npx`, una sola invocazione nella corsia.

### 1.2 Carico

Campioni ogni 30 s (326, 21:37 → 00:21), load 1-min:

| | |
|---|---|
| media | **8,9** (il 12/10: 37,9) |
| minimo | 3,5 |
| massimo | **29,5** alle 21:38:57 (avvio, passata parallela backend) |
| altri picchi | 25,6 alle 22:19:46 (front-asset → front-broker); 24,2 alle 22:20; 24,4 alle 22:44:58 (front-fx → front-portfolio); 22,7 alle 22:44:27 |

La galleria di M sulla 6158 (fino alle ~22:15, poi 9 gruppi per ~20 min) si vede nei picchi brevi tra le 22:19 e le
22:45 (1-min fino a 24–26, 5-min mai oltre 15,7). Nessun rosso cade in quelle finestre: non ce ne sono.

### 1.3 Andamento

| fase | durata | esito |
|---|---|---|
| parallelo backend, 2 worker (4 lotti) | 21:38 → 21:58 | **11 062 ✓**, 3 skip, 0 ✗ |
| consolidato backend | | services 185 ✓ · api 68 ✓ · e2e 7 ✓ |
| front-ai-export | 21:58 → 22:01 | E2E **18/18** (il 12/10: 4 ✗) · vitest 513 ✓ |
| front-asset | → 22:17 | E2E **126 + 19** (il 12/10: 2 ✗) · vitest 1 001 ✓ |
| front-broker | → 22:23 | E2E 2 + 51 ✓ · vitest 57 ✓ |
| front-fx | → 22:34 | E2E **76 + 27** (il 12/10: 11 ✗) · vitest 138 ✓ |
| front-portfolio | → 22:55 | E2E 18 + 66 + 98 ✓ · vitest 1 268 ✓ |
| front-transaction | → 23:27 | E2E 34 (+32 skip voluti) + 78 + 82 + 47 + 57 + 55 + 16 = **369** (il 12/10: 5 ✗) · vitest 887 ✓ |
| front-user | → 23:29 | E2E 20 ✓ · vitest 57 ✓ |
| front-utility | → 00:03 | E2E 92 + 110 + 129 = **331** (il 12/10: 7 ✗) · vitest 7 594 ✓ |
| seriale: external, db | → 00:21 | tutto verde; db 13/13 azioni |

Riscontri puntuali sui rossi del 12/10:

- `layout/toolbar-width-sweep`: **20/20**, compresi `assetDetail › es` e `dashboard › es` (14,4 s e 11,2 s). Il
  difetto (e) del 12/10 è chiuso (V-19, lotto 48 di I).
- `auth.spec.ts`: **29/29**.
- `fx-add-pair`, `fx-bulk`, `fx-chart-settings`, `fx-csv-import`, `asset-data-editor`, `tx-commit-all-types`,
  `tx-import-ca-contract`, le 4 spec AI Export: tutte verdi.
- La firma «Tearing down "jsCoverage" exceeded the test timeout of 30000ms» **non compare più** (V-28), e nemmeno
  «Fixture "jsCoverage" timeout of 120000ms exceeded».

### 1.4 Avvisi del runner (non rossi)

- 2 × «1 empty coverage part(s) removed — their writer was stopped while saving» (parti `p1.w0` e `p4.w0` della
  passata parallela): regola «opzione A» decisa l'08/10, causa nel backlog (N-4). Il combine è verde, nessun
  «Couldn't combine».
- Nessun «Shared backend ignored SIGTERM… killing its process group».
- Le righe `❌ Provider metadata test failed…`, `❌ API error: MOCKFX_FAIL: simulated provider failure…` della passata
  external sono **stampe di test verdi** che verificano i percorsi d'errore dei provider.

---

## 2. Rossi e rilanci

Nessun rosso, quindi nessun rilancio. Il metodo previsto, skill `test-triage` (artefatti salvati ogni 20 s, rilancio
da solo a 1 worker con la stessa coverage, load annotato), era pronto e non è servito: `test-results/` è rimasto
vuoto per tutta la run.

---

## 3. DB al seed, categoria per categoria

**Metodo.** In una run `all` la passata frontend popola il DB **una volta sola**, all'inizio
(`scripts/test_runner/_consolidate.py:315`): lo stato passa quindi da una categoria all'altra, e il §3 di V («perdita
confinata nella categoria») qui non vale. Lo ha confermato anche il coordinatore. Ho salvato il DB della corsia in sola
lettura (backup SQLite, sorgente `mode=ro`):
- dopo ogni populate;
- appena finito l'E2E di ogni categoria, cioè quando parte il suo vitest.

Poi ho confrontato ogni istantanea col seed di V e con la precedente (`/tmp/libreFolio_R_final_dbcmp.py`, esito in
`/tmp/libreFolio_R_final_dbcmp.txt`).

**Esito**: dopo **tutte e 8** le categorie frontend il DB è al seed:
- `users` 11, `brokers` 8 (id 1–8), `broker_user_access` 30, `transactions` 76 (**id 1–76 tutti presenti**, max 76),
  `assets` 17, `asset_events` 11 (stessi id: il rischio V-32 non si è manifestato), `fx_conversion_routes` 24 (stesse
  tuple), `user_settings` 10;
- `e2e_test_user` (en, light, EUR);
- scheduler (true, 10 min, `06:00,23:00`, mon–sat, 14, UTC);
- EUR/PLN ed EUR/SEK sempre a 276.

`sqlite_sequence` delle transazioni sale da 76 a 439 (righe create e tolte: normale).

| istantanea | Δ rispetto alla precedente |
|---|---|
| 01 populate (setup `api`, 21:48) | = seed. `global_settings` 0: lo crea il `globalSetup` di Playwright, non il populate |
| 02 populate (passata frontend, 21:58) | `custom-uploads` 61 → 103 e `broker_reports` 1 → 81: scritti dai test **backend** (api ed e2e), fuori dal perimetro del §3 |
| 03 dopo front-ai-export | `global_settings` creati (13, valori del seed); **`price_history` +7** (vedi sotto) |
| 04 dopo front-asset | nessuna |
| 05 dopo front-broker | nessuna |
| 06 dopo front-fx | **+372 tassi MOCKFX**, EUR/ILS, EUR/MYR, EUR/PHP ed EUR/TWD, 93 ciascuno: **la sola differenza tollerata da V**, identica |
| 07 dopo front-portfolio | nessuna |
| 08 dopo front-transaction | nessuna nel DB; file: vedi sotto |
| 09 dopo front-user | nessuna |
| 10 dopo front-utility | **`price_history` +3** (vedi sotto) |
| 11 populate (categoria `db`, 00:11) | ripopolato; i tassi ECB passano da 276 a 277 per coppia dopo mezzanotte (la finestra segue il calendario, come scrive V) |

**Le due scritture di `price_history`**, osservazione da non trattare come perdita:
- **+7 alle 22:01:15**, durante front-ai-export: una riga con la data del 13/10 per ciascuno dei 7 asset quotati,
  tutte nello stesso istante, con le fonti reali (justetf ×3, css_scraper ×2, yfinance, scheduled_investment). È il
  prezzo corrente salvato come barra del giorno quando una pagina lo chiede.
- **+3 alle 00:03:11**, durante front-utility, subito dopo mezzanotte: la barra del 14/10 di BTP Italia 2028, BTP Più
  e Gold Spot.
- La tabella non è tra quelle del seed di V e non tocca righe esistenti. Le righe sono quelle di oggi, e con la rete
  dipendono dal giorno: lo segnalo perché una spec che contasse le barre di un asset vedrebbe +1.

**I file della corsia**:
- `custom-uploads` resta **fermo a 103** per tutta la passata frontend.
- `broker_reports` cresce solo di file vuoti:
  - **front-transaction +89**: 89 lock `.locks/broker_N.lock` e ~107 cartelle vuote `uploaded/broker_N/`, una per
    ogni broker temporaneo creato e poi cancellato dalle spec di import (id fino a 200, mentre il seed ne ha 8);
  - **front-user +1**;
  - **front-utility +6**, non attribuibili: la categoria `db` ha poi ripulito la cartella.

  Nessun file di report resta orfano: i 16 file in `uploaded/` sono quelli del populate (`--with-reports`). È
  pulizia del file system alla cancellazione di un broker (BRIM/import, fuori dai workstream attivi): osservazione,
  non rosso.

---

## 4. Coverage

### 4.1 Backend (Python, `branch = true`)

Categorie misurate: **tutte** (`all`: external, db, services, utils, schemas, api, e2e + backend toccato dai lotti
Playwright).

| base dati | statement | mancanti | rami | parziali | % coverage.py (righe+archi) | % righe | % rami |
|---|---:|---:|---:|---:|---:|---:|---:|
| backend da test | 53 883 | 3 467 | 16 248 | 2 291 | **91,54 %** | 93,57 % | 84,84 % |
| backend da E2E | 53 883 | 33 912 | 16 248 | 379 | 29,32 % | 37,06 % | 3,63 % |
| combinata (`.coverage`) | 53 883 | 3 466 | 16 248 | 2 290 | **91,55 %** | 93,57 % | 84,85 % |

- Sentinella dei figli `spawn`: `services/risk/quant/spawn_worker.py` all'**87,64 %**: cablaggio integro.
- **Confronto col 12/10** (stessa formula, stesse categorie): 91,51 → **91,55 %** (+0,04 pp); righe 93,53 → 93,57;
  rami 84,78 → 84,85; denominatore 53 896 → 53 883. E2E→backend 29,32 → 29,32, identico.
- Moduli più scoperti: invariati rispetto al 12/10. `schemas/pac_allocator.py` 97 mancanti, `pac_allocator/models.py`
  95, `schemas/risk.py` 88, `api/v1/assets.py` 73 (75,00 %), `brim_provider.py` 54. Percentuali più basse:
  `scheduler/scheduler.py` 60,18 %, `broker_cryptocom` 69,86 %, `broker_cointracking` 74,45 %, `api/v1/assets.py`
  75,00 %, `fx_providers/fed` 75,18 % (era 70,80: risente della rete). Per pacchetto: `brim_providers` 88,4 % righe /
  79,7 % rami (906 righe mancanti), `api/v1` 89,6 % / 83,7 %, `fx_providers` 89,7 % / 75,4 %.

### 4.2 Frontend (JS/Svelte, istanbul, build strumentata)

> ⚠️ **Le cifre E2E sono limiti inferiori (C-69, I1).** La fixture `jsCoverage` perde i contatori quando una pagina
> va su `about:blank`. Il numero E2E e la sua parte nella combinata possono solo essere più alti di quanto scritto.
> Non ho provato a correggerlo.

| livello | file | statement | rami | funzioni | righe |
|---|---:|---:|---:|---:|---:|
| unit (vitest) | 642 | 58,46 % (34 724 / 59 396) | 51,06 % | 60,70 % | 60,35 % |
| E2E (990 file di coverage raccolti) — **limite inferiore** | 610 | ≥ 62,09 % (35 192 / 56 682) | ≥ 48,81 % | ≥ 61,38 % | ≥ 64,89 % |
| **combinata** — limite inferiore per la parte E2E | 642 | **71,17 %** (47 698 / 67 020) | **62,83 %** (27 282 / 43 424) | 72,85 % | 78,30 % |

- **Senza `src/lib/features/tools`**: 78,34 % statement, 67,65 % rami.
- **Planner del PAC**: 7 008 statement al 14,21 %; 47 dei 55 file allo 0 % sono suoi. Nessuna spec E2E della suite lo
  esercita: è la lacuna di test già segnalata il 12/10 (proprietario probabile V).
- **Confronto col 12/10**:

  | | 12/10 | 13/10 | Δ |
  |---|---:|---:|---:|
  | combinata, statement | 71,24 % | 71,17 % | −0,07 pp (+176 coperti, +309 di denominatore) |
  | combinata, rami | 62,82 % | 62,83 % | = |
  | unit | 57,15 % | 58,46 % | +1,3 pp |
  | E2E | 63,10 % | ≥ 62,09 % | −1,0 pp |

  - Il calo E2E si concentra in `ImportWizardModal.svelte`, che nella combinata scende dal 54,9 % al 50,1 % (1 374
    statement scoperti), e in `components/transactions`, dal 66,4 % al 63,4 %. Non lo attribuisco: con C-69 non si
    distingue un percorso non più eseguito da contatori persi.
  - I file di coverage E2E sono 990 per 1 221 test verdi; il 12/10 erano 1 005 per 1 192 eseguiti. Le spec delle
    transazioni toccate da V-33 e C-69 sono i primi indiziati.
  - Salgono `components/dashboard` (79,5 % → 83,3 %) e `components/files` (62,6 % → 64,9 %).
- File con più statement scoperti: `ImportWizardModal.svelte` 1 374, `routes/(app)/assets/[id]/+page.svelte` 553,
  `TransactionBulkModal.svelte` 423, `planner/steps/BrokerEditor.svelte` 421 (0 %), `planner/copies.ts` 353,
  `TransactionFormModal.svelte` 338, `routes/(app)/assets/+page.svelte` 300, `RiskAnalysisPanel.svelte` 279
  (rami 40,1 %).

---

## 5. Prove, stato finale, pulizia

| cosa | dove |
|---|---|
| log completo | `/tmp/libreFolio_R_final_run.log` (preparazione: `/tmp/libreFolio_R_final_prep.log`) |
| log per unità | `.testLog/` della worktree; DB finale archiviato dal runner in `.testLog/00_archive/test-db_20261014_002153.tar.xz` |
| load e disco ogni 30 s | `/tmp/libreFolio_R_final_load.log`; diario del watcher `/tmp/libreFolio_R_final_watch.log` |
| istantanee del DB per categoria e confronto | `/tmp/libreFolio_R_final_db/` (11 istantanee + metadati), `/tmp/libreFolio_R_final_dbcmp.txt` |
| coverage congelata (dati Python + report JS) | `/tmp/libreFolio_R_final_cov/`; JSON `/tmp/libreFolio_R_final_cov_{backend,e2e,combined}.json`; sintesi `/tmp/libreFolio_R_final_covsum_py.txt`, `/tmp/libreFolio_R_final_covsum_js.txt` |
| script | `/tmp/libreFolio_R_final_prep.sh`, `/tmp/libreFolio_R_final_run.sh`, `/tmp/libreFolio_R_final_watch.py`, `/tmp/libreFolio_R_final_dbcmp.py` |

**Stato finale** (14/10, 00:27):

- run conclusa con rc = 0, watcher terminato da solo con il runner; **nessun server acceso, porta 6176 libera**,
  nessun processo della corsia;
- worktree su `10e646f79`, **nessun file tracciato modificato** (`git status` vuoto);
- **raw JS cancellato** come concordato: `frontend/coverage-js/e2e-raw`, 18 GiB, dopo aver verificato che la copia
  congelata del `coverage-final.json` combinato fosse identica (`cmp`). Il volume dati è tornato a **31 GiB liberi**.
  Restano i report (`combined`, `e2e`, `unit`, `unit-combined`: 215 MB), `.coverage`, `.coverage_data`, `htmlcov*`:
  `./dev.py test coverage show combined` e `show js` mostrano le cifre di questo rapporto;
- build del frontend: **debug, non strumentata** (0 chunk con `__coverage__`). È stata ricostruita alle 00:10, al
  riavvio del backend condiviso durante la categoria `db`: è il comportamento descritto al §3.6 del rapporto del
  12/10;
- la data-dir della corsia (`/tmp/librefolio-r2-r-cov`) resta con il DB ripopolato dalla categoria `db`.
