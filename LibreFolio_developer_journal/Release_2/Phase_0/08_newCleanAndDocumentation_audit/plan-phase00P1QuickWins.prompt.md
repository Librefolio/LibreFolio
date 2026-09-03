# P1 — Quick win tecnici: piano di esecuzione (08_newCleanAndDocumentation_audit)

> **Creato**: 2026-09-02, giorno dell'audit. **Fonte**: [`99_task_riesumati.md`](99_task_riesumati.md) §P1 (18 voci) + i P0-5 secondari.
> **Metodo**: workstream paralleli per area di file (mai due sullo stesso file),
> **nessuna suite di test durante lo sviluppo parallelo** — run targeted solo se un
> workstream è solo; **una run full seriale alla fine** (`dev.py test all`, workers=1).
> **Chiusura**: a fine giro, aggiornare lo stato nei report d'area che citavano le voci
> (come fatto per i P0 il 02/09) + CHANGELOG + questo piano.

## Decisioni pendenti (bloccano i rispettivi task)

| # | Questione | Stato |
|---|---|---|
| D-1 (P1-2) | Soglia complessità | ✅ **Deciso 03/09 (utente)**: soglia BASSA (10) → i flat packer saltano fuori e vengono marcati uno a uno con `# noqa: C901 — flat mapping, no nested logic` (commento mirato, non per-file); sui residui si legge il valore reale e si decide il massimo sensato. ~157 funzioni da triaggiare: NON è una quick win — WS-B diventa M, esecuzione a lotti per modulo |
| D-2 (P1-16) | Prova migrazione su DB 1.0.1 | ✅ **Deciso 03/09 (utente)**: container dall'**immagine pubblicata vecchia** (è online) → DENTRO il container: db populate (mock) per un DB pieno 1.0.1 → marker SQL diretti per le due migrazioni dati — `002`: `identifier_other` scalare `'MIGRATION_MARKER'` + uno `''` + uno già array (atteso `["MIGRATION_MARKER"]` / NULL / invariato); `5b1333fa6b07`: `global_settings.scheduler_history_sync_times` con CSV noto (atteso riscrittura timezone) → stop → nuova immagine **locale** sullo stesso volume → log alembic + marker + boot + dashboard |
| D-3 (P1-11 coda) | Metadati componenti AI export drawdown (`version=1`/`WINDOWED` vs payload full-history) prima del tag V1. Nota: il bump `implementation_version` 1.1.0 del plugin è **già fatto** (02/09, la policy lo richiedeva e la semantica era appena cambiata) | ⏳ da decidere con P2 |

## Workstream paralleli

```
WS-A api contracts      P1-1  response_model ×6 (system.py, settings.py, uploads.py) + api sync
                              ✅ Lane A (03/09): 6 endpoint cablati, 13 schema creati;
                              uploads: 2 endpoint binari → response_class. api sync al closeout.
WS-B lint hygiene       P1-3  55 TRY400 → logger.exception ✅ Lane B2 (03/09): 55/55, 0 residui
                          P1-2  C901 gate @10 attivo in pyproject (03/09); 173 siti in triage
                              parallela (Lane E1–E4): flat packer → noqa giustificato,
                              logica annidata → noqa TODO(P2-refactor) + lista refactor
WS-C backend dead code  P1-4/P0-5b/P1-6 ✅ Lane B (03/09): orfani rimossi, N+1 fixati
                              (i siti fx erano in api/v1/fx.py, non services/fx.py),
                              mappatura fifo_utils documentata sotto (rimozione differita)
WS-D frontend dead/i18n P1-7/P1-8/P1-9 ✅ Lane C (03/09): 10 orfani, 25 chiavi ×4 lingue
                              (2523→2498), 22 re-export + tipi orfani. Delta audit: ~30
                              aiExport.dataset NON orfane (risoluzione dinamica backend-driven).
WS-E frontend stores    P1-10 ✅ (Lane C): rimossi cachedProvidersHash + invalidateCurrencyGraph,
                              docstring registra il perché (grafo statico per sessione)
WS-F test infra         P1-5/P1-13/P1-14 🔄 Lane D in corso
WS-G meta/docs          P1-12/P1-15/P1-17 🔄 Lane D in corso
WS-H release gate       P1-16 🔄 "before" fatto (03/09): immagine pubblicata 1.0.1 su volume
                              /tmp/lf_mig_proof, DB popolato (17 asset, 5435 record), marker SQL
                              inseriti (identifier_other scalare/''/già-array; scheduler times
                              '12:00' UTC → atteso '14:00' Europe/Rome a settembre, CEST=UTC+2).
                              Script di verifica pronto: /tmp/lf_mig_after_verify.sh
CHIUSURA                P1-18 ✅ (03/09): run full seriale 14/15 (rosso = solo la suite
                          AI Export con i 3 contract red preesistenti su HEAD); coverage
                          backend test **91%** (era 90,66% un mese fa; ora include
                          spawn_worker 87%, prima 0%), backend-da-E2E 29%, JS 72,3% stmt,
                          identifier_utils 80%. `ruff check backend/` tutto verde (a HEAD:
                          37 preesistenti). api sync + fix discriminatore SchedulerLog.
                          Commit unico proposto in /tmp/libreFolio_commit_final.txt
```

### Fuori pista della chiusura (03/09)

- **Bootstrap del server di test morto** scoperto alla prima run full: il sitecustomize
  di Lane D (P1-13) oscurava quello di Homebrew Python → `pipenv` non importabile → la
  build frontend abortiva sul check JS-cache strict (I1). Fix: chain-exec dello
  sitecustomize shadowato + import coverage guardato. Senza I1 sarebbe rimasto un
  warning silenzioso — le due modifiche si sono coperte a vicenda.
- Container `lf-mig-proof` (porta 6049) lasciato attivo per ispezione utente; cleanup:
  `docker rm -f lf-mig-proof && rm -rf /tmp/lf_mig_proof && git worktree remove /tmp/lf-101`.

> **⚠️ Fuori pista (03/09)**: l'audit citava i siti N+1 fx come `services/fx.py:965/:1014` —
> in realtà sono in `api/v1/fx.py`. Inoltre `scripts/coverage_analysis.py:152` elencava ancora
> `get_session_ttl_sync` (rimosso da Lane B) — esclusione aggiornata.
> **⚠️ Fuori pista (03/09)**: leftover segnalato da Lane C — `BaseDropdown.svelte` e
> `TransactionTypeBadge.svelte` sono file completamente orfani (zero importatori);
> `design-system.html` documenta ancora BaseDropdown come usato. Decisione utente richiesta.
> **⚠️ Fuori pista (03/09)**: Lane A aveva introdotto `SchedulerLogResponse` (union
> discriminata su `job`) ma svelte-check falliva sul client rigenerato. Causa doppia:
> (a) il generatore TS ignora `const` di Pydantic — serve `Field(json_schema_extra={"enum": [...]})`
> sul `Literal` (pattern già usato da `ai_export_runtime.py`); (b) il post-processor
> `frontend/scripts/fix-openapi-discriminators.mjs` ha una **lista hardcoded** di membri di
> union discriminate a cui togliere l'annotazione `: z.ZodType<T>` — i due nuovi entry
> SchedulerLog* sono stati aggiunti. Regola: **ogni nuovo membro di union discriminata va
> registrato in quel file** (e il campo discriminatore vuole `json_schema_extra enum`).

## Note di soluzione concordate

### P1-10 — grafo valute mezzo cablato (`stores/currencyGraphStore.ts`)
**Risoluzione 03/09 (ipotesi utente confermata sul codice): RIMOZIONE, non
completamento.** Il grafo si costruisce SOLO dalle capability dei provider
(`base_currencies × target_currencies`, `currencyGraph.ts:73-110` — il sentinella
MANUAL è esplicitamente saltato). I provider sono registrati all'avvio del backend
e non esiste endpoint per abilitarli/disabilitarli a runtime; le route configurate
dall'utente (`POST/DELETE /fx/providers/routes`) e i rate NON sono input del grafo.
Quindi il grafo non può cambiare entro una sessione — e un riavvio backend forza il
reload della pagina comunque. `cachedProvidersHash` (mai letto) e
`invalidateCurrencyGraph()` (zero chiamanti) sono macchinari morti per un caso
impossibile: cancellare entrambi + docstring che registra il perché. ~~(Proposta
iniziale "completare il cablaggio" — ritirata: le mutazioni coppie non alimentano
il grafo.)~~

### P1-13 — coverage dei worker spawn
`.coveragerc` ha già `concurrency = multiprocessing,thread,gevent` (necessario ma non
sufficiente per `spawn`): manca l'avvio di coverage **dentro** il figlio. Ricetta standard
coverage.py: (1) un `sitecustomize.py` con `coverage.process_startup()`; (2) runner con
`--coverage` imposta `COVERAGE_PROCESS_START=<repo>/.coveragerc` e prepend al PYTHONPATH la
cartella col sitecustomize; (3) i figli spawn ereditano l'env → scrivono
`.coverage.<host>.<pid>.<rand>` → il combine li raccoglie. Verifica: una riga di
`spawn_worker.py` toccata da un test risk appare coperta.

### P1-2 — esito triage (03/09): 199 siti → 173 FLAT giustificati, 26 COMPLEX da refactor

Gate attivo: `C901` in select + `max-complexity = 10` in pyproject. Ogni sito ha ricevuto
`# noqa: C901 — <giustificazione>` dopo lettura integrale della funzione (5 lane parallele
E1–E5 + 2 siti fx_providers dal coordinatore). Verifica finale: `ruff check backend/` →
**zero errori** (era già rosso a HEAD con 37 preesistenti: 36 PLC0415 + 1 B905 in
test_scripts/settings.py — risolti nel corso, import hoisting + 2 noqa giustificati;
`dev.py lint` torna verde per la prima volta).

**Backlog refactor (26 COMPLEX, marcati `TODO(P2-refactor)` nel codice):**

| Funzione | C901 | Nota |
|---|---|---|
| `transaction_service.py:937 execute_batch` | 115 | pipeline batch 8 stadi, validazioni annidate per item |
| `portfolio_engine.py:555 build` | 97 | motore replay giornaliero monolitico |
| `portfolio_service.py:906 get_summary` | 73 | accumulazione broker/tx/asset annidata |
| `brim_providers/broker_credit_agricole.py:929 _parse_account_movements` | 71 | parse a due passi con 6 closure annidate |
| `portfolio_service.py:1670 get_positions_contribution` | 62 | accumulazione annidata + rami FX |
| `asset_source.py:2713 bulk_refresh_prices` | 62 | orchestratore 3 fasi, closure fetch/persist |
| `fx.py:778 sync_pairs_bulk` | 54 | sync concorrente 3 fasi, 4 closure |
| `asset_source.py:2161 get_prices_bulk` | 49 | pipeline 9 passi query/FX/segnali |
| `lots_analysis_service.py:169 get_lots_analysis` | 35 | orchestratore lungo |
| `portfolio_service.py:95 compute_wac_iterative` | 32 | pipeline WAC a stadi |
| `portfolio_service.py:347 compute_wac_iterative_multi_broker` | 32 | gemella multi-broker, condivide helper |
| `portfolio_engine.py:1902 calculate` | 26 | orchestratore pipeline |
| `asset_source.py:2880 _fetch_single` | 22 | cache gap-analysis annidata ~6 livelli |
| `portfolio_service.py:2111 get_report` | 21 | orchestrazione include-flag + retry MWRR |
| `brim_provider.py:1471 detect_tx_duplicates` | 21 | risoluzione asset + match qty/cash annidati |
| `scheduled_investment.py:233 _generate_schedule_values` | 19 | motore accrual giorno-per-giorno |
| `scheduled_investment.py:403 _compute_value_at` | 18 | quasi-duplicato del walker sopra |
| `roi_utils.py:343 calculate_mwrr_series` | 15 | retry chain solver warm-start |
| `risk/metrics.py:259 drawdown_episodes` | 15 | state machine episodi con recovery |
| `portfolio_engine.py:1250 _compute_in_transit` | 13 | valutazione per-intervallo annidata |
| `risk_plugins/stress.py:140 _normalize_bucket_shocks` | 13 | normalizzazione bucket per-dimensione |
| `signal_series_preparation.py:235 select_signal_computation_points` | 11 | segmentazione run contigui |
| `signal_annotations.py:199 _crossings` | 11 | crossing detection stateful |
| `signal_service.py` (1), `lots_analysis_service.py` (1°) | ~11 | vedi commenti in codice |
| `test_runner/_consolidate.py:297 run_consolidated` | 23 | verdict folding annidato |
| `test_runner/_coverage.py:155 _finalize_coverage` | 24 | matrice modi × pipeline combine |
| `test_runner/_inventory.py:107 _collecting` | 24 | patch/restore registry annidato |

Nota: i 3 del test_runner sono tooling interno — priorità inferiore rispetto ai 23 backend.
script `pre-commit`-style: nessuno; il gate ruff li preserva dal peggioramento.

### P1-2 — complessità (risposta alla domanda dell'utente)
Sì: McCabe/C901 conta **ogni** punto decisionale — inclusi ternari e operatori booleani —
quindi un flat packer "spacchetta e ripacchetta" con 12 ternari segna 13 pur essendo
lineare. La metrica "onesta" per quel caso sarebbe la cognitive complexity (penalizza il
nesting, non il flat data-shuffling), **ma ruff non la supporta**. Con la toolbox ruff:
C901@25 ora (19 violazioni, triage con fix o `# noqa: C901 — flat mapping` motivato) +
PLR0915 (troppi statement, default 50) come rete per i muri di statement, e cricchetto
verso 15/10 in una tornata successiva. Soglia 10 subito = ~157 funzioni da toccare: non è
una quick win, è un progetto.

## Regole
- Test nuovi/riparati via test-author; mai due suite in parallelo (DB condiviso).
- `./dev.py api sync` dopo WS-A (schemi). `./dev.py i18n` per WS-D (mai edit a mano dei JSON).
- Nessun `git commit` — proposta di messaggio a fine giro.
- A fine giro: stato nei report d'area + 99_task_riesumati.md + questo piano + CHANGELOG.

## WS-H log (P1-16) — ✅ PROVA SUPERATA (03/09)

**Before**: immagine pubblicata `ghcr.io/librefolio/librefolio:1.0.1` (amd64, emulata) su
volume `/tmp/lf_mig_proof`, DB popolato (17 asset, 11 utenti, 5435 record, alembic
`001_initial`), marker SQL: asset1 `identifier_other='MIGRATION_MARKER'`, asset2 `''`,
asset3 `'["ALREADY_ARRAY"]'`; `scheduler_history_sync_times='12:00'` con
`scheduler_timezone='Europe/Rome'`.

**After**: build `librefolio:latest-light` dal working tree (arm64 nativa — rimosso il flag
`--platform` usato per la 1.0.1), stesso volume, container `lf-mig-proof` su :6049.
Risultati (log: `/tmp/libreFolio_ws_h_after.log`):
- alembic: `001_initial` → `5b1333fa6b07` applicata in boot (002 + 5b1333fa6b07);
- 002: scalare → `["MIGRATION_MARKER"]` ✓, `''` → NULL ✓, array esistente invariato ✓;
- 5b: `12:00` → `14:00` = atteso esatto (Europe/Rome CEST = UTC+2 a settembre) ✓;
- boot pulito (zero traceback), dashboard `GET /` → 200.
Container lasciato attivo su :6049 per ispezione utente
(cleanup: `docker rm -f lf-mig-proof && rm -rf /tmp/lf_mig_proof /tmp/lf-101`).

## WS-H log (P1-16) — fase "before" pronta (03/09)

- Immagine pubblicata `ghcr.io/librefolio/librefolio:1.0.1` (tag senza `v`; solo amd64 → `--platform linux/amd64` su Mac ARM).
- Container `lf-mig-proof` su :6049, volume bind `/tmp/lf_mig_proof` → `/app/backend/data/prod-docker`; boot ok, DB creato a `001_initial` (1.0.1 contiene SOLO `001_initial`: sia 002 sia 5b1333fa6b07 vengono applicate all'upgrade).
- Il populate NON è nell'immagine (test_scripts esclusi dal dockerignore): eseguito da worktree `git worktree add /tmp/lf-101 v1.0.1` con il venv principale (`cwd=worktree`, venv bin su PATH per alembic) → 17 asset / 11 utenti / 5435 record, poi copiato sul volume a container fermo (e rimossi -wal/-shm stale).
- Marker SQL inseriti: asset 1 `identifier_other='MIGRATION_MARKER'` (atteso `["MIGRATION_MARKER"]`), asset 2 `''` (atteso NULL), asset 3 `'["ALREADY_ARRAY"]'` (atteso invariato); `scheduler_timezone='Europe/Rome'` + `scheduler_history_sync_times='12:00'` (atteso `'14:00'` con CEST di settembre — calcolare l'offset a runtime, non hardcodare).
- RESTA (fase "after", a corsie terminate): `./dev.py docker build` (immagine corrente) → `docker stop lf-mig-proof` → riavvio STESSO volume con la nuova immagine → verificare log alembic (002+5b applicate), marker come sopra, boot pulito, dashboard risponde su :6049.

## P1-6 mapping (Lane B, 03/09)

Mappatura dei casi limite di `backend/app/utils/financial/fifo_utils.py` (148 righe, legacy) su
`FifoLotEngine` (`backend/app/services/fifo_lot_engine.py`), prima di qualunque rimozione futura.
Nessuna cancellazione in questo giro — solo mapping.

### Equivalenze strutturali (dominio BUY/SELL puro, singolo broker)

- **Ordinamento**: fifo_utils ordina per `(date, id)`; engine per `(date, phase, transaction_id, pair_id)`
  (`_event_sort_key` :547) — per BUY/SELL same-day la phase è 3 per entrambi → tie-break su
  `transaction_id`: **equivalente**.
- **Consumo FIFO**: fifo_utils usa una deque; engine `_consume_broker_fragments` (:828) itera
  `_broker_fragments` ordinati per `(lot.opening_date, lot_id, fragment.start_date, fragment_id)`
  (:996-999): **equivalente** per un singolo broker (l'engine aggiunge lo scoping per-broker).
- **P&L realizzato**: `(sell - buy) * qty` identico (`_close_position_piece` :869 per LONG).
- **Prezzo unitario**: fifo_utils prende `price` dato; engine deriva `_unit_price(amount, quantity)`
  (:1515) — stessa grandezza, origine diversa (attenzione a fee incluse in `amount`).
- **Tipi non BUY/SELL ignorati**: fifo_utils filtra in ingresso; engine `classify_events` (:443) non
  emette eventi per tipi ignoti (DIVIDEND & co. vanno allo stadio income, non ai lotti): esito uguale.

### Le 11 testa a testa (`test_fifo_utils.py` → `test_fifo_lot_engine.py`)

| # | Test legacy | Cosa fissa | Equivalente engine |
|---|---|---|---|
| 1 | `test_single_buy_no_sell` | 1 open lot, pnl=0, unrealized=qty | `TestBasicLongShort::test_single_buy_opens_one_long_lot` (:202) ✅ |
| 2 | `test_buy_then_full_sell` | chiusura piena, pnl=(60-50)*100 | `test_buy_then_full_sell_closes_lot_with_pnl` (:212) ✅ |
| 3 | `test_buy_then_partial_sell` | parziale 30/70 | `test_buy_then_partial_sell_keeps_fragment_identity` (:227) ✅ |
| 4 | `test_two_buys_one_sell_fifo_order` | lotto più vecchio consumato prima | ordinamento `_broker_fragments` (:996) + `test_multi_lot_aggregation` (:528) ✅ (sostanza) |
| 5 | `test_sell_spans_multiple_lots` | sell 70 → 50+20 su due lotti | loop `_consume_broker_fragments` (:841-854) + `TestEconomicConservation` (:992,:1020) ✅ (sostanza) |
| 6 | `test_realized_pnl_calculation` | formula pnl | come #2 ✅ |
| 7 | `test_negative_pnl_on_loss` | segno negativo in perdita | formula identica (:869) ma **nessun test engine dedicato al segno perdita** — ⚠️ gap da coprire prima di rimuovere |
| 8 | `test_oversell_raises_error` | ValueError su oversell | **cambio deliberato**: engine apre SHORT se broker lo consente (`test_crossing_zero_sell_closes_long_then_opens_short` :247) altrimenti issue `FIFO_SOURCE_QUANTITY_MISSING` senza raise (`test_sell_exceeding_long_without_shorting_emits_issue` :282, `_apply_sell` :600-606) ✅ diversa semantica, pinnata |
| 9 | `test_no_transactions` | input vuoto → risultato vuoto | **cambio deliberato**: engine solleva `ValueError("requires at least one transaction")` (:390) — i caller filtrano a monte ⚠️ contratto diverso |
| 10 | `test_non_buy_sell_transactions_ignored` | DIVIDEND ignorato | `classify_events` non emette evento (vedi sopra) ✅ |
| 11 | `test_complex_scenario` (5B+3S) | matching multi-lotto concatenato | nessuno scenario 1:1; coperto per proprietà da `TestEconomicConservation` ✅ (sostanza) |

### Cosa l'engine copre in più (fuori scope legacy)

Scoping per-broker, TRANSFER con transito, SPLIT (incl. in-transit e rounding non-divisore),
ADJUSTMENT ± con cost_basis_override, SHORT, allocazione income/fee/tax, `analysis_status`.

### Prima di una futura rimozione di fifo_utils.py restano da fare

1. Aggiungere al suite engine un test esplicito di **P&L negativo** (gap #7).
2. Verificare che **nessun caller** di `calculate_fifo_lots` esista in produzione (grep 03/09: solo
   `test_fifo_utils.py` + registration runner `services_roi_fifo_utils` — già ok).
3. Aggiornare la registration `services_roi_fifo_utils` in `scripts/test_runner/_backend_services.py`
   (stringhe già corrette in questo giro; la unit resta perché copre l'intera cartella `test_financial/`).
