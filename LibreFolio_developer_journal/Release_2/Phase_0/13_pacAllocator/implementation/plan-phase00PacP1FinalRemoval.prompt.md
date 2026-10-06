# Piano D — Rimozione finale del P1, poi R7

**Stato:** 🔄 iniziato il 2026-10-06 alle 19:39. Il via è del coordinator alle 19:25 («Via alla riga 13»),
dopo la validazione di `7ba60a62f`.
**Baseline:** `7ba60a62f` su `e-alfy-allocatore-pac`: merge `--no-ff` di `a8ad1a500` (slice di
robustezza) con `6addaba05` (`dev_release2`), albero `59873db3e`. Verificata alle 19:39: albero
pulito, stage vuoto, porte 6151 e 6161 libere.
**Posizione:** `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacP1FinalRemoval.prompt.md`
← Precedente: [`plan-phase00PacSolverRobustness.prompt.md`](plan-phase00PacSolverRobustness.prompt.md) (riga 12 del README).
→ Seguente: analisi del Rebalancer (riga 14), piano da definire. Parte solo dopo il checkpoint di
questa riga e il via del coordinator.
**Corsia:** suite `6151` + `/tmp/librefolio-r2-d`, un comando per volta. Nessun server di review.
Il riavvio della macchina delle 19:21 ha svuotato `/tmp`: la data-dir si ricrea al primo uso. Accanto
a ogni tempo annoto il carico della macchina.

Le righe citate sono misurate alla baseline. Se il codice cambia, prevale il codice.

---

## 0. Perché

Il developer, il 2026-10-05, sull'analisi che proponeva questo lavoro:

> «si approvo il piano»
>
> «Prima la correzione del solver, poi la pulizia P1 (Consigliato)»
>
> «Sì, tutte come raccomanda D (Consigliato)»

Quindi la pulizia del P1 viene dopo la slice del solver (riga 12, ora integrata), **con l'estensione
(b)** e con tutte le 28 chiavi `tools.portfolioRebalancer.*`. Le 104 chiavi del planner che nessuno
usa vanno nel backlog, non qui.

Il coordinator, il 2026-10-05:
- **R7** entra in questo lavoro, come ultimo commit separato `fix(pac): …`, con le chiavi tramite
  `dev.py i18n`. Nel passaggio di consegne propongo la riga 🐛 del CHANGELOG; il CHANGELOG lo
  scrive il coordinator.
- **`developer/architecture/patterns/tool_plugins.en.md:287`** si corregge qui, con il
  docs-writer, solo in inglese.

Il coordinator, il 2026-10-06 alle 19:25:
1. questo piano, con dentro le due correzioni di journal e la validazione di `7ba60a62f`;
2. **prima del codice**, l'elenco esatto dei file e le zone di `portfolio_service.py`. Dentro
   l'elenco concesso procedo; per ciò che ne esce aspetto il suo ok;
3. prima i test rossi, poi codice e `api sync`; gate sulla 6151; checkpoint con la previsione sui
   file della famiglia Risk.

Valgono le due richieste del developer: **nomi veri** degli agenti (test-author, docs-writer,
agente `general-purpose`; nessun modello fissato, vale quello predefinito dell'harness) e **parole
semplici**, prima il fatto concreto e poi, se serve, il nome tecnico.

## 1. Il problema, detto semplice

Il **P1** è il primo prototipo dell'allocatore. Per avere il catalogo degli Asset e la cassa dei
Broker chiedeva al report del portafoglio (`POST /portfolio/report`) una sezione in più,
`allocation_source`.

Il planner v2 non la usa: ha un endpoint suo, `POST /portfolio/allocation-source`, senza cache, con
la fonte e la data di ogni dato. La riga 8 ha già tolto la pagina del P1. Qui resta il suo lato dati:
- nel backend, un ramo di `get_report` con un'impronta di cache tutta sua
  (`portfolio_service.py:2267-2353`), un'uscita anticipata (`:2434-2450`) e un errore 403 dedicato
  (`portfolio_api.py:241-250`);
- 7 schemi in `schemas/portfolio.py`;
- il client `allocationSource.ts`, che nessuna pagina importa;
- 285 chiavi di testo che nessuna pagina mostra, e il codice delle copie che la UI non apre più
  (estensione (b)).

**Per chi usa l'app non cambia niente.** Il report risponde con le stesse sezioni di prima, meno
`allocation_source`: le sezioni passano da 13 a 12. Una richiesta che manda ancora il campo
`allocation_source` riceve 422, perché il body (`PortfolioReportQuery`, uno `StrictModel`) rifiuta
i campi che non conosce. Nel repo, tolto `allocationSource.ts`, nessun client lo manda più.

## 2. Step 0 — correzioni del journal e validazione di `7ba60a62f` ✅ 2026-10-06

Le due correzioni approvate dal coordinator il 2026-10-06 entrano nel commit di journal di questa
riga:
1. `plan-phase00PacSolverRobustness.prompt.md:1477`: l'oggetto del terzo commit diventa «docs(journal):
   close the solver robustness slice» (48 caratteri), come l'ha accorciato il coordinator al
   checkpoint. A `:7` il piano seguente è ora un link.
2. `README.md`, riga 12: gli SHA dei tre commit e del merge. Riga 13: il link a questo piano, lo stato
   🔄 e il metodo giusto del report, `POST` (prima c'era scritto `GET`).

**Validazione di `7ba60a62f`** (2026-10-06, dalle 17:31 alle 17:42, corsia 6151). Il merge non porta
dipendenze né migrazioni.

| Gate | Esito |
|---|---|
| `api sync` | ok; hash dei contratti dei tool `f636854e…`, uguale a S6; PAC `4f061103…58bb`, 1.0.0 |
| `front build --debug` | ok (carico 42-45) |
| `mkdocs build` (strict) | ok |
| 11 suite backend | 177 core, 159 evaluator, 21 oracle, 40 policies, 40 solver, 30 proof, 39 wire-numbers, 39 report, 44 service, 543 schemas pac-planner, 7 api pac-planner-tool: 1 139 test, gli stessi di S6 |
| `core-unit` | 104 file, 2 956 test |
| `component-unit` | 99 file, 2 241 test (carico 58-62); un file più di S6, `SearchSelect.reopen.test.ts`, arrivato col merge |
| `front check` | 0 errori, 0 warning |
| `check-orphans` | backend 231, frontend unit 288, e2e 96 |
| `i18n audit` | 4 505 chiavi × 4, 0 incomplete, 0 mancanti nel backend, 521 non usate |
| `mkdocs check-links` | rosso solo per D28 (`#rolling-return` in it/fr/es), già accettato; 81 link validi |
| `dev.py lint` | verde |

Alla fine le porte 6151 e 6161 erano libere (17:42:48).

> **Note implementazione**: correzioni applicate alle 19:40, insieme alla creazione di questo piano.
> Nessun altro file toccato.

## 3. File e zone

### 3.1 Dentro l'elenco concesso dal coordinator

| File | Cosa cambia |
|---|---|
| `backend/app/services/portfolio_allocation_source.py` | via il P1: import `:22-27`; `PortfolioAllocationSourceAccessError` `:51-56`; `build_portfolio_allocation_source` `:59-98`; `_load_owner_accesses` `:101-123`; `_ensure_cash_brokers_accessible` `:126-133`; `_load_candidate_assets` `:163-177`; `_load_usage_counts` `:217-244`; `_build_contexts_by_asset` `:247-269`; `_build_source_assets` `:272-312`; `_build_cash_sources` `:346-366`; `_build_selected_cash_balances` `:369-378`. Resta il v2: `:136-160`, `:180-214`, `:315-343` e tutto da `:381`. Gli import rimasti senza uso li segnala `ruff` (F401). |
| `backend/app/schemas/portfolio.py` | via le 7 classi `:1109-1197`, il campo della richiesta `:1691` e quello della risposta `:1713`. Resta `PlannerSourceSection` (`:1205`). |
| `backend/app/services/portfolio_service.py` | solo le parti `allocation_source` di `get_report` e dei suoi import (§3.2) |
| `backend/app/api/v1/portfolio_api.py` | `PortfolioAllocationSourceAccessError` (`:37`) esce dal blocco di import `:36-41`; gli altri nomi restano. In `get_portfolio_report` il `try/except` `:241-250`, con il codice `allocation_source_cash_broker_forbidden` a `:247`, diventa `return await service.get_report(...)`. La route v2 `:188-219` resta. |
| `frontend/src/lib/features/tools/pac-allocator/allocationSource.ts` e `.test.ts` | cancellati: sono gli unici consumatori di `allocation_source` nel frontend |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | le 285 chiavi della lista, solo con `dev.py i18n remove <chiave> -f`, **solo dopo lo SHA di riallineamento del coordinator** (§5, S6) |
| `backend/test_scripts/test_services/test_portfolio_allocation_source.py` | test-author: via `:2026-2027` e `:2082` (`usage_probe`, che chiama il loader P1 `_load_usage_counts`) |
| `backend/test_scripts/test_api/test_portfolio_api.py` | test-author (§5, S2) |
| il journal | questo piano, `README.md`, `plan-phase00PacSolverRobustness.prompt.md` (§2) |

### 3.2 Le zone di `portfolio_service.py` (2 706 righe)

Tutte dentro `get_report` o nei suoi import:

| Righe | Cosa |
|---|---|
| `:66` | `PortfolioAllocationSource,` nell'import degli schemi |
| `:79` | `from backend.app.services.portfolio_allocation_source import build_portfolio_allocation_source` |
| `:2231-2232` | le variabili `allocation_source_date` e `allocation_cash_broker_ids` |
| `:2234` | `price_fingerprint_date`: via; a `:2264` torna `effective_date_to` |
| `:2241-2244` | 3 righe di commento e la condizione; resta `if broker_ids_for_scope:` |
| `:2262` | `allocation_metadata_fp = None` |
| `:2267-2363` | l'impronta di cache dei metadati del P1 (97 righe; la stima iniziale `:2267-2353` era corta, vedi S3) |
| `:2398-2399`, `:2402` | i membri P1 della chiave di cache `l2_key` |
| `:2412-2450` | la chiamata al builder P1, il commento `:2421`, `needs_engine` `:2422-2433` (lo usa solo l'uscita anticipata: resterebbe una variabile morta, F841) e l'uscita anticipata `:2434-2450` |
| `:2467-2468` | `included.append("allocation_source")` |
| `:2698` | `allocation_source=allocation_source,` nella risposta |

`UserRole`, `Broker`, `Asset`, `PriceHistory` e `func` restano usati altrove nel file: i loro import
non cambiano.

### 3.3 Fuori dall'elenco: concessi dal coordinator il 2026-10-06

Il coordinator ha concesso tutte e cinque le voci. Nessun altro ramo le tocca, tranne il runner.

| File | Cosa cambia | Nota |
|---|---|---|
| `backend/test_scripts/test_services/test_financial/test_portfolio_service.py` | test-author: via la classe `TestPortfolioAllocationSource` (da `:3450` alla fine del file, riga 4 832, 12 test) e gli import `:40`, `:44` e `:46` | la classe è mia (P1), il file è condiviso. Dopo il codice backend il file non si importa più senza questa modifica. L'import `:44` (`AssetSourceManager`) lo usa solo la classe tolta. Il cache-bust F2 resta coperto da `TestAccessFingerprintCacheBust` (`:607`). |
| `scripts/test_runner/_frontend_utility.py:116` (`:120` dopo il treno `a7d0b37ec`) | via la riga di `allocationSource.test.ts` | file condiviso del runner; tolgo solo questa riga, **solo dopo lo SHA di riallineamento** (S1, Fuori pista 2) |
| `frontend/e2e/tools/allocation-tool-fixtures.ts` | cancellato | fixture del prototipo del Round 4 (`d66f8e58e`), senza importatori; usa il report con `allocation_source` |
| estensione (b): `planner/steps/SourceCopyDialog.svelte` (cancellato); `planner/copies.ts`: le varianti `price`, `exposures` e `fx` di `CopyConflict` (`:15-17`), `applyPriceCopy` (`:306-359`), `applyClassificationCopy` (`:491-536`), `applyFxCopy` (`:560-~628`), i rami di `resolveConflicts` (`:798-815`; la funzione resta per la cassa, `copyFlow.svelte.ts:5`), `restoreCopiedRate` (`:822-827`); `planner/draft.svelte.ts`: `fxPairs` (`:703`), `removeFx` (`:713-715`); `planner/shared/ConflictDialog.svelte`: `:32-38`, `:59-80` | codice v2 senza utenti | approvata dal developer il 2026-10-05, ma i file sono fuori dall'elenco. `sourceAssetKeys` (`:298`) e `clonePrice` (`:302`) li tolgo solo se restano senza utenti. Il tipo `CopyKind` non cambia. |
| `mkdocs_src/docs/developer/architecture/patterns/tool_plugins.en.md:287` | docs-writer, solo EN | la frase «The current compiled registry binds no components at all … `renderer_missing`» è vecchia: il registry lega `pac_allocator` 1.0.0 a `PacPlannerTool.svelte` (`frontend/src/lib/features/tools/registry.ts:241-244`). La pagina non ha traduzioni: nessuno stamp. |

R7 (§6) è un commit a sé, dopo il checkpoint del P1. Anche i suoi file sono fuori dall'elenco: il
coordinator li riverifica in quel momento.

### 3.4 File generati

`openapi.json`, `generated.ts` e `tool-contract-map.generated.ts` sono ignorati da Git
(`frontend/.gitignore:12-13`, `frontend/src/lib/api/.gitignore:3`): `api sync` non lascia diff
tracciati.

### 3.5 Cosa resta del v2

- `POST /portfolio/allocation-source` (`portfolio_api.py:188-219`, `_get_allocation_source_user`
  `:49`);
- `PlannerSourceSection` (`schemas/portfolio.py:1205`);
- il selettore del runner `services portfolio-allocation-source` (`_backend_services.py:587-597`,
  `:1064-1065`): il suo file copre il v2;
- il commento a `portfolio_allocation_source.py:1234` sull'import pigro: riguarda il WAC del v2.

## 4. Previsione sui file della famiglia Risk

Rami confrontati in sola lettura: `e-alfy-risk-asset-global-lab` `28559e829`,
`e-alfy-risk-asset-global-levels` `1041c38fa` (punta avanzata durante la verifica, ricontrollata: stessi
hunk, stesso esito i18n), `e-alfy-risk-management-replan` `9ce2efaed`. Base comune con la mia HEAD:
`9b5291c25`.

- **`portfolio_service.py`.** I loro hunk: un import inserito dopo quello di `schemas.wac` (sul target
  `:78`), poi `:440-441` e `:697`. Fra il loro import e la mia riga `:79` c'è la riga
  `from backend.app.services.fx import convert_bulk`, che nessuno dei due tocca. Le mie altre zone
  partono da `:2231`. **Nessun conflitto testuale previsto.**
- **i18n.** Loro aggiungono 151 chiavi, ne tolgono 20 e ne cambiano 16, in `assetPicker.*`,
  `chartSettings.tooltips`, `dashboard.allocationGeneric`, `risk.*`, `sharedResource.syncSelection`,
  `signals.units` e `assets.panels`. **Nessuna chiave in comune** con le mie 285. La vicinanza nel
  testo dei JSON si controlla al merge.
- **`_frontend_utility.py`.** Loro aggiungono righe alla base `:72`, `:77-78`, `:81-82`, `:179`,
  `:224-229` e cambiano le descrizioni a `:511` e `:520`; io tolgo solo `:116`. Nessun conflitto
  previsto.
- **Non toccano** `schemas/portfolio.py`, `portfolio_api.py`, i tre file di test, il frontend del PAC
  e `tool_plugins.en.md`.

N tocca `FxStep.svelte:197-200` e `:354-363` e la chiave `planner.fx.pairAbsentHelp`: niente di
questo è nelle mie liste.

> Questa previsione è di S1. In S9 l'ho rifatta sulle punte della sera, con un merge simulato: vedi S9.

## 5. Passi

### S0 — journal ✅ 2026-10-06

Vedi §2.

### S1 — elenco al coordinator ✅ 2026-10-06

Messaggio con §3 e §4, la domanda su L2 (§6.3) e l'ordine: prima il P1, poi R7.

> **Note implementazione**: inviato alle 19:46 (`needs_input`). Parto con S2, che è dentro l'elenco
> concesso. S3 aspetta l'ok sul file `test_portfolio_service.py` (§3.3, voce A).
>
> **⚠️ Fuori pista**: la punta del ramo Risk dei livelli si chiama `e-alfy-risk-asset-global-levels`
> ed era avanzata a `1041c38fa`. L'ho ricontrollata prima dell'invio: stessi hunk in
> `portfolio_service.py` e nel runner, nessuna chiave i18n in comune.
>
> **Risposta del coordinator** (2026-10-06):
> - le voci A–E di §3.3 sono concesse;
> - L2 (§6.3): opzione (a), chiusa senza codice;
> - R7 dopo il checkpoint del P1; il coordinator riverifica allora i suoi file;
> - le 285 chiavi i18n si tolgono **per ultime**, solo dopo lo SHA di riallineamento. Il treno porta
>   `dev_release2` in ff fino a N' e poi riallinea i rami; modifiche non committate ai cataloghi
>   bloccherebbero il mio ff;
> - nel checkpoint va l'elenco esatto delle chiavi tolte: dopo l'integrazione segue un audit i18n
>   generale;
> - la riga 14 aspetta il via del coordinator (triage di fine sprint).
>
> **⚠️ Fuori pista 2**: ho controllato in sola lettura i quattro rami del treno
> (script `/tmp/libreFolio_d_r13/train_overlap.sh`):
>
> | Ramo | Punta | Contiene D (`7ba60a62f`) | File in comune con la mia lista |
> |---|---|---|---|
> | K `e-alfy-k-tassonomia-e-select` | `998ce67d4` | sì | i 4 cataloghi, `_frontend_utility.py` |
> | L `e-alfy-l-danske-bank` | `eba9e8bf1` | sì | i 4 cataloghi, `_frontend_utility.py` |
> | M `e-alfy-cloud-resource-sizing` | `d0018a5a1` | sì | i 4 cataloghi, `_frontend_utility.py` |
> | N `e-alfy-fx-dashboard-sync` | `1ae2a53c9` | sì | i 4 cataloghi, `_frontend_utility.py` (più `FxStep.svelte`, che non tocco) |
>
> Git rifiuta un ff o un merge se un file che arriva col treno ha modifiche non committate, anche se le
> righe sono lontane. Quindi anche la riga `_frontend_utility.py:116` aspetta lo SHA, insieme alle
> chiavi. Il resto della mia lista (backend, test, frontend del PAC, fixture, docs, journal) il treno
> non lo tocca.

### S2 — test rossi (test-author)

Dentro l'elenco concesso, quindi parte senza aspettare l'ok.

> **Base di `black`**: `test_portfolio_api.py` non passa già oggi `black --check`: 8 blocchi da
> riformattare (`:1830-2469`), tutti nati con `0088748a8` (2026-09-18, «feat(pac): redesign FX/funding
> to canonical rate map»). Uno sta dentro il test legacy che tolgo. `dev.py format` applica black a
> tutto il backend, ma nessun gate lo controlla (`dev.py lint` usa solo ruff). Non riformatto i blocchi
> rimasti: il controllo è «nessun blocco nuovo rispetto alla base», e nel checkpoint propongo la
> riformattazione come commit `style(pac)` a parte. Gli altri due file di test passano.

`test_portfolio_api.py`:
- **rosso 1**: un report con i flag predefiniti ha esattamente le 12 sezioni. Oggi è rosso: la
  risposta contiene anche `allocation_source`;
- **rosso 2**: una richiesta con `allocation_source` riceve 422, con l'errore su quel campo. Oggi è
  rosso: risponde 200;
- **conversione** di `:1474-1562` in `test_report_one_chart_flag_includes_exactly_that_section`:
  senza `allocation_source`, ogni flag di grafico da solo dà `included_features == [section]` e la
  sezione piena. È l'unico test di `include_broker_pnl_history`: va convertito, non tolto;
- via i test P1 `:593-1144` (compreso il pin a 13 chiavi `:767-780`), `_legacy_report_response`
  (`:2334-2410`) e il test legacy che lo usa (`:2411` e seguenti). Via gli import `:23-28`,
  `MagicMock`, `AS_OF`, `PortfolioReportMetadata` e `PortfolioReportResponse`, se restano senza uso.

`test_portfolio_allocation_source.py`: via `:2026-2027` e `:2082`.

`test_portfolio_service.py` (concesso): via la classe `TestPortfolioAllocationSource` e gli import
`:40`, `:44`, `:46`.

Corse, una per volta:
1. `api portfolio`: rossi esattamente i due test nuovi, verde tutto il resto;
2. `services portfolio-allocation-source`: verde;
3. `services roi-fifo-utils` (contiene `test_financial/test_portfolio_service.py`,
   `_backend_services.py:583`): verde.

> **Note implementazione** (S2 ✅ 2026-10-06 20:04): il test-author ha scritto i tre file senza correre
> test.
> - `test_portfolio_api.py` (2 697 → 2 039 righe): tolti i 4 test P1 (vecchie `:593-1144`),
>   `_legacy_report_response` e il test legacy (vecchie `:2334-2477`), gli import P1, `MagicMock` e
>   `AS_OF`. Nuovi in testa a `TestPortfolioReportEndpoint`:
>   `test_report_response_has_exactly_twelve_sections` (`:584`) e
>   `test_report_rejects_allocation_source_field` (`:620`). Convertito
>   `test_report_one_chart_flag_includes_exactly_that_section` (`:981`), con
>   `included_features == [section]`.
> - `test_portfolio_allocation_source.py` (2 633 → 2 630): tolte le 3 righe di `usage_probe`.
> - `test_portfolio_service.py` (4 832 → 3 444): tolta `TestPortfolioAllocationSource` (vecchie
>   `:3448-4832`) e gli import `:40`, `:44`, `:46`; nessun altro import è rimasto senza uso.
> - `ruff`: tutto passa. `black --check`: i file 2 e 3 passano; nel file 1 restano solo i 7 blocchi
>   vecchi, identici e spostati di 514 righe; quello dentro il test legacy è sparito con il test.
>
> Corse sulla 6151:
>
> | Corsa | Esito | Durata | Carico (1/5/15 min), inizio → fine |
> |---|---|---|---|
> | `api portfolio` | **2 rossi attesi**, 47 verdi | 20,6 s | 7,45/12,28/22,78 → 6,05/11,48/22,12 |
> | `services portfolio-allocation-source` | 89 verdi | 1,0 s | 5,43 → 5,95 |
> | `services roi-fifo-utils` | 506 verdi, di cui 87 di `test_portfolio_service.py` | 4,3 s | 5,96 → 5,95 |
>
> I due rossi sono quelli giusti. Rosso 1: «unexpected sections: ['allocation_source']». Rosso 2:
> risposta 200 invece di 422. La cartella dati della corsia era sparita col riavvio; il server la
> ricrea all'avvio (`backend/app/main.py:98`, `ensure_database_exists`). Log in
> `/tmp/libreFolio_d_r13/s2_*.log`.

### S3 — codice backend ✅ 2026-10-06 20:12

§3.1 e §3.2. Poi `ruff check` sui file toccati, per gli import rimasti senza uso.

> **Note implementazione**: un solo script con un'asserzione per ogni ancora
> (`/tmp/libreFolio_d_r13/s3_remove_p1.py`): ogni sostituzione deve trovare esattamente un punto, e le
> funzioni e le classi le trova `ast` per nome. Prima l'ho corso a vuoto, scrivendo il risultato in
> `/tmp/libreFolio_d_r13/s3_preview/`, e ho letto il diff; poi l'ho applicato.
> - `schemas/portfolio.py`: 1 713 → 1 620 righe. Via le 7 classi e i 2 campi.
> - `portfolio_allocation_source.py`: 1 860 → 1 619 righe. Via le 10 funzioni e classi del P1 e i
>   6 import di schema. Restano i 3 loader del v2. La docstring del modulo ora descrive il v2.
> - `portfolio_service.py`: 2 706 → 2 554 righe. `get_report` torna alla forma di prima del P1, con
>   le aggiunte venute dopo (FX, rendimento sul costo, i nuovi flag). Con tutti i flag a `false` la
>   richiesta passa dal motore, come prima del P1. L'impronta dei prezzi usa `effective_date_to`,
>   cioè `date_to or today`, come prima.
> - `portfolio_api.py`: 293 → 283 righe. Il `try/except` diventa un `return` diretto.
> - `ruff check` e `black --check` puliti sui 4 file, l'import del modulo funziona, e `rg` non trova
>   più simboli P1 in `backend/app`, `scripts` e `dev.py`. Nei test resta solo il corpo del rosso 2,
>   che manda apposta `allocation_source` e si aspetta 422.
> - **Tenuto apposta**: nella chiave di cache resta
>   `tuple(sorted(broker_ids_for_scope)) if broker_ids_for_scope else None`. L'ha aggiunto il P1
>   (`8273335ff`), ma rende la chiave solo più precisa, mai sbagliata, e non era nella tabella §3.2.
>   I test leggono la chiave solo dalla fine (`[-2]` FX, `[-1]` rendimento sul costo,
>   `test_portfolio_service.py:2597-2610`), quindi togliere i membri in mezzo non sposta nulla.

> **⚠️ Fuori pista 1**: il blocco dell'impronta dei metadati P1 era di 97 righe (`:2267-2363`), non
> `:2267-2353` come stimato in §3.2. La prova a vuoto l'ha mostrato prima di scrivere; §3.2 è
> corretto.

> **⚠️ Fuori pista 2**: durante S3 è arrivato il riallineamento del coordinator: `dev_release2` e il
> mio ramo sono a `a7d0b37ec` (treno D, K, L, M, N), con il lavoro in corso intatto. Il treno tocca,
> della mia lista, solo i 4 cataloghi e `_frontend_utility.py`: la riga di
> `allocationSource.test.ts` è passata da `:116` a `:120`. Tocca anche `FxStep.svelte` (di N) e due
> spec della Dashboard, senza riferimenti al P1. Lo S6 è sbloccato.

> **⚠️ Fuori pista 3** (trovato in S8, controllando i simboli rimasti): il commento a
> `portfolio_allocation_source.py:993` diceva che l'import dentro la funzione evita un ciclo fra moduli
> (`portfolio_service` → questo modulo). Dopo S3 il ciclo non c'è più: `portfolio_service.py` non
> importa più questo modulo, che ora importa solo `portfolio_api.py:36`. L'import però deve restare
> dentro la funzione, perché due test (`test_portfolio_allocation_source.py:1365` e `:1750`) sostituiscono
> `portfolio_service.compute_wac_iterative` e funzionano solo se il nome si legge al momento della
> chiamata. Portarlo in cima vorrebbe dire cambiare quei test, fuori da questo checkpoint. Ho cambiato
> solo il commento, con il motivo vero; il codice e il `# noqa: PLC0415` restano.

| Comando (corsia 6151, uno per volta) | Esito | pytest | Muro | Carico prima → dopo |
|---|---|---|---|---|
| `test api portfolio` | 49 passed: i 2 rossi ora verdi | 19,93 s | 129 s | 4,29 → 13,98 |
| `test services portfolio-allocation-source` | 89 passed | 0,98 s | 5 s | 13,58 → 12,90 |
| `test services roi-fifo-utils` | 506 passed | 4,06 s | 7 s | 12,66 → 11,97 |

> Porta 6151 libera alla fine. Log in `/tmp/libreFolio_d_r13/s3_*.log`.

### S4 — frontend core ✅ 2026-10-06

Cancello `allocationSource.ts`, `allocationSource.test.ts` e la fixture e2e
`allocation-tool-fixtures.ts`. La riga del runner va in S6, dopo lo SHA di riallineamento.

> **Note implementazione**: prima di cancellare ho ricontrollato i riferimenti su `a7d0b37ec`
> (`frontend/src`, `frontend/e2e`, `scripts`, `dev.py`). `allocationSource.ts` lo importava solo il suo
> test (`allocationSource.test.ts:4`); `allocation-tool-fixtures.ts` non lo importava nessuno. Gli
> altri riferimenti sono al v2 (`planner/source.ts:197`, `:313`) e al selettore del runner
> `services portfolio-allocation-source`: restano. Cancellati i 3 file (971 righe) e tolta la riga
> `_frontend_utility.py:120`. La cartella `frontend/e2e/tools/` era rimasta vuota e l'ho tolta:
> nessuna configurazione la nomina (`playwright.config.ts`, `vitest.config.ts`, `vite.config.ts`,
> `package.json`, `scripts`).

> **⚠️ Fuori pista**: la riga del runner l'ho tolta qui e non in S6, perché il riallineamento era già
> arrivato (S3, Fuori pista 2): S6 resta solo per le chiavi i18n.

### S5 — estensione (b) (concessa) ✅ 2026-10-06

I file e le righe di §3.3.

> **Note implementazione**: le righe di §3.3 erano ancora giuste su `a7d0b37ec` (`copies.ts` è fermo a
> `6f29ec1cf`); solo la fine di `applyFxCopy` è `:608`, non `~628`. Prima ho controllato gli utenti:
> `SourceCopyDialog.svelte` non lo importava nessuno; `ConflictDialog.svelte` resta, perché lo usa
> `CopyFlowView.svelte:4` per i conflitti della cassa; nessuno spec e2e o unitario nomina i `testid`
> tolti (`pac-planner-{prices,classifications,fx}-copy`, le righe price/exposures/fx del conflitto); i
> `.fxPairs` rimasti nel planner sono di `plan`, `query` e `built.counts`, non della bozza. Poi uno
> script con un'asserzione per ancora (`/tmp/libreFolio_d_r13/s5_extension_b.py`), prima a vuoto con
> il diff, poi applicato:
> - `copies.ts` 889 → 714 righe: `CopyConflict` ha solo la variante `cash`; via `applyPriceCopy`,
>   `applyClassificationCopy`, `applyFxCopy`, `restoreCopiedRate` e i tre rami di `resolveConflicts`,
>   che ora aggiorna solo la cassa. Via l'import `sameExposures`, rimasto senza uso in questo file
>   (lo usano ancora `request.ts` e `draft.svelte.ts`). `sourceAssetKeys`, `clonePrice` e
>   `cloneExposures` hanno ancora utenti e restano.
> - `draft.svelte.ts` 786 → 779: via `fxPairs` e `removeFx`.
> - `ConflictDialog.svelte` 97 → 60: via `priceText` e i rami price/exposures/fx; resta il ramo della
>   cassa, senza `{#if}`, con `data-kind`. Via gli import rimasti senza uso (`DraftPrice`, 5 formatter,
>   `DIMENSION_FALLBACKS`).
> - `steps/SourceCopyDialog.svelte` cancellato (134 righe).
> - `prettier --check` pulito sui 3 file modificati; nessun import senza uso
>   (`/tmp/libreFolio_d_r13/s5_import_use.py`). Il controllo dei tipi è in S8 (`front check`).

### S6 — runner e i18n, solo dopo lo SHA di riallineamento ✅ 2026-10-06 20:32

0. Aspetto lo SHA del coordinator e controllo che il mio ramo sia stato portato in avanti: i file del
   treno sono puliti nel mio albero, quindi non blocco il ff. Poi tolgo la riga
   `_frontend_utility.py:116`.
1. Una scansione nuova dei riferimenti (`frontend/src`, `backend/app`, `scripts`; i test non contano
   come consumatori). I miei script in `/tmp` sono andati persi col riavvio: questa volta salvo una
   copia anche nei file della sessione.
2. Solo le chiavi ancora senza riferimenti: `dev.py i18n remove <chiave> -f`, una per chiamata, da
   uno script in `/tmp`. Le righe con `#` della lista (le 104 del backlog) non si toccano.
3. Parità fra le 4 lingue: da 4 505 a circa 4 220 chiavi ciascuna (il conteggio va rifatto sulla
   nuova base, perché il treno aggiunge chiavi); `git diff --stat` limitato ai 4 file.
4. L'elenco esatto delle chiavi tolte va nel checkpoint e in un'appendice di questo piano.

> **Note implementazione**:
> - **La scansione nuova** (`/tmp/libreFolio_d_r13/s6_refs_scan.py`; script, log e tabelle anche nei
>   file della sessione, `files/r13/`) legge `frontend/src`, `backend/app` e `scripts`; i test non
>   contano. Trova le chiavi scritte per intero, quelle costruite da una costante (`${KEY}.title`, anche
>   con più costanti in fila) e quelle con una parte variabile. Una parte variabile vale «qualunque
>   nome», e la chiave conta come usata se quel nome compare nel codice come stringa o come chiave di
>   un oggetto. Una prova con chiavi sicuramente usate (`s6_control_keys.txt`) le trova tutte.
> - **Sulla base `a7d0b37ec` con il mio lavoro**: 4 508 chiavi per lingua. Le 285 chiavi della lista
>   sono tutte testi semplici (non gruppi) in tutte e 4 le lingue, e nessuna è più usata: G1 65, G2 28,
>   G3 168, G4 14, G5 10.
> - **Il mio lavoro non lascia altre chiavi orfane**: ho scansionato tutte le chiavi due volte,
>   sull'albero di HEAD e sul worktree. Diventano inutilizzate esattamente 24 chiavi, tutte nella lista
>   (G4 e G5, i testi dei dialoghi tolti in S5).
> - **La rimozione**: `dev.py i18n remove <chiave> -f`, una chiamata per chiave, dallo script
>   `/tmp/libreFolio_d_r13/s6_remove.sh`. Lo script si ferma al primo errore e vuole «✓ removed» in
>   tutte e 4 le lingue. Esito: 285 chiavi su 285, nessun errore, 386 s, carico 18,68 alla partenza
>   (`s6_remove.log`).
> - **La verifica** (`/tmp/libreFolio_d_r13/s6_verify.py`): confronta, lingua per lingua, i cataloghi di
>   HEAD con quelli del worktree:
>   - da 4 508 a 4 223 chiavi in ognuna delle 4 lingue, con le stesse chiavi in tutte;
>   - mancano esattamente le 285 della lista: nessuna chiave aggiunta, nessun testo cambiato;
>   - il file riscritto è identico a una nuova scrittura dello stesso JSON;
>   - `tools.allocation` e `tools.portfolioRebalancer` non esistono più. Di `tools.pacAllocator` fuori
>     dal planner restano solo `name` e `description`; in tutto `tools.pacAllocator` passa da 1 125 a 933
>     chiavi;
>   - restano le chiavi da tenere: `planner.fx.pairAbsentHelp` (di N), `planner.strategy.tieBreak`, i
>     testi della cassa del dialogo dei conflitti e `dashboard.allocation`, che serve a R7.
>
>   `git diff --stat`: i 4 cataloghi, 345 righe tolte ciascuno, nessuna aggiunta: le 285 chiavi più
>   l'apertura e la chiusura dei 30 gruppi rimasti vuoti. Log `/tmp/libreFolio_d_r13/s6_verify.log`.
> - L'elenco esatto delle chiavi è nell'appendice A.

> **⚠️ Fuori pista**:
> - la scansione della p12 era andata persa col riavvio: l'ho rifatta da zero, e questa volta script,
>   log e tabelle sono anche nei file della sessione;
> - la base contava 4 508 chiavi per lingua, non 4 505: il treno ne ha portate 3 in più;
> - delle 104 chiavi del backlog (le righe con `#`), una adesso è usata:
>   `tools.pacAllocator.planner.result.proof.floatingFinished`, letta da `result/model.ts:113` dopo il Q6
>   della slice del solver. Non l'ho toccata; le chiavi del backlog scendono a 103;
> - **nomi di chiave senza catalogo, già a HEAD** (da mettere nel backlog, non li tocco):
>   - `pac_allocator/evaluator.py:968` scrive `explanation_key = "tools.allocation.constraints.<codice>"`
>     in un modello interno (`ConstraintRef`, `models.py:664`) che nessun codice legge;
>   - `test_pac_planner_schemas.py:537` e la fixture `rebalancer_plan_result.medium.v2.json` usano
>     `tools.allocation.explanations.*` e `tools.portfolioRebalancer.explanations.*` come esempi per
>     `explanation_keys`, che il report manda sempre vuoto (`planner_report.py:628`) e il frontend non
>     legge.
>
>   Nessuna di queste chiavi esisteva nei cataloghi, quindi la rimozione non cambia nulla; ma dopo
>   la riga 13 i due gruppi `tools.allocation` e `tools.portfolioRebalancer` non esistono proprio.

### S7 — docs (concessa) ✅ 2026-10-06

docs-writer, `tool_plugins.en.md:287`, solo EN.

> **Note implementazione**: il docs-writer ha cambiato una sola riga, la `:287`. Prima diceva che il
> registro compilato non lega nessun componente e che `pac_allocator` risulta non disponibile con
> `renderer_missing`. Adesso dice il vero, verificato su `registry.ts:240-247`: c'è una sola
> registrazione, `pac_allocator` contratto `1.0.0`, chiave `pac-allocator`, UI `1.0.0`, import lazy di
> `PacPlannerTool.svelte`. `renderer_missing` vale per un descrittore compatibile senza
> registrazione: un descrittore incompatibile esce prima con un altro motivo (`contracts.ts:274-293`).
> Le altre due frasi del paragrafo sono rimaste. Nessuna data da aggiornare (il front matter ha solo
> `title` e `description`); la pagina esiste solo in inglese, quindi niente `translate-stamp` e
> nessun debito di traduzione. `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py
> mkdocs build` → exit 0, 0 WARNING, 0 ERROR (`/tmp/libreFolio_d_r13/s7_mkdocs_build.log`).
> `check-links` resta in S8.

### S8 — `api sync` e gate ✅ 2026-10-06 20:45

I gate del backend (punti 2–4 e 10) posso già correrli prima dello SHA. La serie completa la corro dopo
S6, sulla nuova base.

Un comando per volta sulla 6151, con il carico accanto ai tempi:
1. `front build --debug`, poi `mkdocs build`, prima di tutto ciò che avvia il backend (lezione
   R14.8);
2. `api sync`;
3. `api portfolio`;
4. `services portfolio-allocation-source`, poi `services roi-fifo-utils` (`test_financial/`, copre
   `get_report`);
5. `check-orphans`;
6. `i18n audit`;
7. `front check`, a 0/0;
8. `front build`;
9. `core-unit` e `component-unit`;
10. `ruff check` e `black --check` sui soli file Python toccati (per `test_portfolio_api.py`: nessun
    blocco nuovo rispetto alla base, vedi S2);
11. `mkdocs check-links`: accettato solo il rosso D28.

Più il controllo con `rg` che nel sorgente non resti nessun simbolo P1.

> **Note implementazione**: tutti i gate sono verdi, e sono girati sull'albero finale. L'ultima modifica
> a un file è delle 20:34:41 (il commento di `portfolio_allocation_source.py:993`, Fuori pista 3 di
> S3); il primo gate è partito alle 20:35:02. Un comando per volta sulla 6151, con
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py …` e, per i test,
> `test --test-port 6151 --data-dir /tmp/librefolio-r2-d …`. Ogni comando passa da
> `/tmp/libreFolio_d_r13/s8_run.sh`, che scrive il log `s8_<nome>.log` e una riga in
> `s8_summary.log`; le copie sono in `files/r13/` della sessione. Il carico è la media di un minuto
> di `uptime`, letta prima e dopo.
>
> | # | Comando | Esito | Ora | Durata | Carico prima → dopo |
> |---|---|---|---|---|---|
> | 1 | `api sync` | rc 0; hash del contratto dei tool `f636854e…e33a`, uguale alla validazione di `7ba60a62f` | 20:35:02 | 19 s | 18,68 → 18,90 |
> | 2 | `front build --debug` | rc 0; svelte-check 0 errori, 0 avvisi | 20:35:39 | 89 s | 17,09 → 11,27 |
> | 3 | `test … api portfolio` | 49 passati | 20:37:26 | 28 s | 14,33 → 17,17 |
> | 4 | `test … services portfolio-allocation-source` | 89 passati | 20:37:57 | 6 s | 18,20 → 18,34 |
> | 5 | `test … services roi-fifo-utils` | 506 passati | 20:38:06 | 9 s | 19,27 → 18,49 |
> | 6 | `test … check-orphans` | verde: ogni file di test è registrato nel runner e raggiungibile da un'azione `all` (293 file unit frontend, 97 spec e2e, 231 file backend) | 20:38:19 | 1 s | 18,49 → 17,89 |
> | 7 | `i18n audit` | rc 0; 4 223 chiavi in ognuna delle 4 lingue, nessuna traduzione mancante | 20:38:42 | 4 s | 16,00 → 15,28 |
> | 8 | `front check` | 0 errori, 0 avvisi | 20:39:32 | 30 s | 11,88 → 10,66 |
> | 9 | `front build` | rc 0 | 20:40:08 | 80 s | 10,21 → 9,73 |
> | 10 | `test … front-utility core-unit` | 107 file, 3 014 test passati; la lista del runner passa da 108 a 107 voci, quella in meno è `allocationSource.test.ts` | 20:41:35 | 25 s | 10,77 → 15,93 |
> | 11 | `test … front-utility component-unit` | 101 file, 2 284 test passati | 20:42:23 | 72 s | 14,33 → 34,39 |
> | 12 | `mkdocs check-links` | rc 1 solo per il rosso accettato D28 (`#rolling-return` in it/fr/es); 81 link validi, `user/tools/pac-allocator` ok; uguale alla validazione di `7ba60a62f` | 20:43:41 | 2 s | 34,44 → 34,44 |
> | 13 | `lint` | «All checks passed!» | 20:43:50 | 2 s | 35,21 → 35,21 |
> | 14 | `ruff check` sugli 8 file Python toccati | «All checks passed!» | 20:44 | — | — |
> | 15 | `black --check` sugli stessi 8 | solo `test_portfolio_api.py`: 7 blocchi, tutti già alla base, nessuno nuovo (vedi sotto) | 20:44 | — | — |
> | 16 | `mkdocs build` | rc 0; 0 WARNING, 0 ERROR | 20:45:15 | 25 s | 13,96 → 16,73 |
> | 17 | `git diff --check` | pulito | 20:44 | — | — |
> | 18 | `lsof -nP -iTCP:6151 -sTCP:LISTEN` | rc 1: porta libera, anche dopo il punto 16 | 20:45 | — | — |
>
> - **Simboli P1**, cercati in `backend/app`, `backend/test_scripts`, `frontend/src`, `frontend/e2e`,
>   `scripts`, `mkdocs_src/docs` e `dev.py`: `PortfolioAllocationSource`,
>   `build_portfolio_allocation_source`, `allocationSource`, `include_allocation_source`,
>   `SourceCopyDialog`, `allocation-tool-fixtures` → nessun risultato. `allocation_source` non compare
>   più né in `schemas/portfolio.py` né in `portfolio_service.py`. Restano solo la route v2
>   (`portfolio_api.py:36`, `:48`, `:188-197`), il suo client (`planner/source.ts:4`, `:197`, `:313`),
>   i suoi test e il test del 422 (`test_portfolio_api.py:620-639`), che manda apposta un campo
>   `allocation_source` al report.
> - **black.** Alla base `test_portfolio_api.py` ha 8 blocchi che black riformatterebbe, nel worktree
>   7. Quello in meno (`@@ -2455`, `legacy_asset = next(...)`) stava dentro il test P1 tolto. Il
>   confronto l'ho fatto su una copia di HEAD in `/tmp/libreFolio_d_r13/s8_black_base/`. `dev.py lint`
>   usa solo ruff, e in S2 si era deciso di non riformattare quei blocchi.
> - **Stato del worktree**: 23 voci dopo tutti i gate, le stesse di prima (18 modificati, 4 cancellati,
>   1 nuovo); stage vuoto. I file generati (`openapi.json`, `generated.ts`,
>   `tool-contract-map.generated.ts`), `frontend/build/`, il sito MkDocs e `.testLog/` sono ignorati.
>
> **⚠️ Fuori pista**:
> - **l'ordine dei punti 1 e 2.** La lista diceva `front build --debug` e poi `api sync`; ho fatto il
>   contrario, perché la build mette dentro il client generato da `api sync`: nell'ordine della lista
>   avrebbe controllato un client vecchio. La lezione R14.8 resta rispettata, perché `api sync`
>   importa l'app nel processo e non avvia nessun server;
> - **`mkdocs build`.** All'inizio volevo riusare la build di S7 (20:21:04, dopo l'ultima modifica a
>   un `.md`, 20:20:28). Però i cataloghi i18n sono cambiati dopo (20:32), e non ero sicuro che la
>   build dei docs non li leggesse; quindi l'ho rifatta sull'albero finale (punto 16);
> - **`check-orphans` scrive un'istantanea del DB** in
>   `.testLog/00_archive/test-db_20261006_203820.tar.xz`. È ignorata (`.gitignore:119`), quindi
>   resta fuori dal checkpoint;
> - **`i18n audit`: 260 chiavi «probabilmente inutilizzate» e 93 «non verificate».** Alla validazione
>   di `7ba60a62f` le inutilizzate erano 521. La differenza è 261, cioè le chiavi dei gruppi G1, G2 e
>   G3 (65 + 28 + 168), che erano già senza riferimenti. Le altre 24 tolte (G4 e G5) l'audit non le
>   contava, perché fino a S5 le leggeva il codice del P1. Le 260 di adesso si dividono così:
>   - 103 sono nel backlog. La lista del backlog ne aveva 104: l'unica che l'audit non segna è
>     `floatingFinished`, che è usata davvero (`result/model.ts:113`);
>   - 28 sono altre chiavi `tools.*`, fuori dal backlog (sotto);
>   - 129 sono fuori da `tools.*`: non riguardano questa riga, e non le ho toccate.
>
>   Nessuna delle 285 chiavi tolte compare ancora nell'audit. Le 28 chiavi `tools.*` le ho
>   controllate una per una con la mia scansione, a HEAD e nel worktree: lo stato è uguale nei due
>   alberi, quindi questa riga non le ha toccate.
>     - 3 senza riferimenti nemmeno per la scansione: `tools.contractVersion`,
>       `tools.implementationVersion`, `tools.open`. Erano senza riferimenti già a HEAD e non fanno
>       parte del P1: per il backlog;
>     - 6 usate davvero, perché la scansione trova la riga che le legge:
>       `planner.brokers.{feeMax,feeMin,feeZero,fundingChipHelp,stepUnits}` (`modeText.ts:28-65`) e
>       `planner.units.shares` (`modeText.ts:21`). L'audit non le riconosce;
>     - 19 usate anche loro, da `planner/result/KpiCards.svelte`, che compone la chiave da
>       `KEY = 'tools.pacAllocator.planner.result.kpi'` (`:25`) e da un nome scritto per esteso:
>       `text('compute.budget', …)` a `:215`, `text('parts.trapped', …)` a `:75`, e i 5 `help.*` con
>       `` text(`help.${key}`, …) `` a `:96`, coi nomi a `:98-110`. La scansione le segna «possibili»
>       proprio per la composizione; l'audit non le riconosce.
>
>   Quindi delle 28 solo le 3 senza riferimenti vanno nel backlog; le altre 25 sono usate, e l'audit
>   le segna per un suo limite.

### S9 — checkpoint ✅ 2026-10-06 20:55

CHECKPOINT READY con il delta, i conteggi, l'elenco esatto delle chiavi tolte, la previsione sui file
della famiglia Risk e del treno, e i messaggi proposti; porta 6151 libera. Poi FROZEN. La riga 14
parte solo col via del coordinator.

Commit proposti:
1. `refactor(pac): remove P1 allocation source`: backend, test, frontend, i18n, runner, fixture,
   estensione (b) e la riga della pagina developer;
2. `docs(journal): …`: questo piano, il README e la correzione del piano della riga 12.

> **Note implementazione**: previsione rifatta sulle punte di stasera, in sola lettura. Gli script sono
> in `/tmp/libreFolio_d_r13/s9_*`; le copie dei log sono in `files/r13/s9/` della sessione.
> - **K, L, M e N** sono a `a7d0b37ec`, cioè al target e alla mia HEAD: non hanno commit da
>   confrontare. Il loro lavoro non committato non lo vedo.
> - **Famiglia Risk.** La punta è `e-alfy-risk-asset-global-levels` `22ef9d091`. Contiene
>   `e-alfy-risk-management-replan` `09b35ca98` e `e-alfy-risk-asset-global-lab` `1041c38fa`, e ha già
>   fuso il target: la base comune con la mia HEAD è `a7d0b37ec`. I file in comune sono
>   `portfolio_service.py`, `_frontend_utility.py` e i 4 cataloghi.
> - **Merge a tre vie simulato** con `git merge-file -p` su copie in `/tmp`: **0 conflitti in tutti e 6
>   i file.**
> - **`portfolio_service.py`** è il punto più vicino. Loro inseriscono un import dopo la riga `:77`
>   della base (`schemas.wac`); io tolgo la `:79` (`build_portfolio_allocation_source`). In mezzo resta
>   la `:78` (`services.fx`), che nessuno dei due tocca. Le loro altre zone sono `:439` e `:694-696`;
>   le mie sono `:66` e da `:2231` a `:2698`. Il file fuso passa ruff (vedi il Fuori pista).
> - **i18n fusa.** JSON valido, 4 355 chiavi per lingua (4 508 + 152 − 20 − 285), stesse chiavi
>   nelle 4 lingue. Le loro 152 aggiunte, 20 rimozioni e 16 cambi ci sono tutti; nessuna delle mie
>   285 chiavi torna; nessun loro cambio tocca le mie chiavi (`s9_i18n_check.py`).
> - **`_frontend_utility.py` fuso.** Si legge (AST) e passa ruff. Passa da 603 a 602 righe: manca
>   solo la mia riga di `allocationSource.test.ts`.
> - **CHANGELOG.** Il P1 non è mai uscito in una versione. Al tag `v1.1.0` nessun file di `backend` o
>   di `frontend/src` contiene `allocation_source`, `AllocationSource` o `allocationSource`. Il modulo è
>   nato con `8273335ff` (2026-09-11), e nessun tag lo contiene. La voce PAC di `[Unreleased]`
>   (`CHANGELOG.md:18`) parla delle copie del v2, che restano: cassa (`copies.ts:230`), prezzi (`:350`),
>   cambi (`:440`), aggiornamento al **Calcola** (`:552`) e distribuzione (`:677`). Proposta al
>   coordinator: nessuna riga.
> - CHECKPOINT READY inviato al coordinator subito dopo questa nota. Poi FROZEN.
>
> **⚠️ Fuori pista**: lanciato da `/tmp`, ruff dava 2 × I001 sul file fuso. Rilanciato col percorso
> del repo (`--stdin-filename`), dava gli stessi 2 × I001 anche sulla loro copia non fusa, e niente
> sulla mia. La causa è `data_quality_thresholds.py`, che esiste solo sul loro ramo. Senza quel file
> sul disco, ruff prende il loro import per una libreria esterna e chiede di spostarlo. Ho rifatto la
> prova con un albero finto in `/tmp`, con i loro moduli come file vuoti: ruff passa su tutte e tre le
> copie (la loro, la mia e la fusa). Non è un errore loro né del merge.

## 6. R7 — `fix(pac)`, dopo il checkpoint del P1

**Perché dopo.** R7 cambia dei valori nei 4 file i18n, gli stessi da cui il P1 toglie 285 chiavi. Se
i due lavori stanno nello stesso albero, il developer non può dividerli in due commit per percorso.
Quindi prima il commit del P1, poi R7 sul nuovo HEAD, con i suoi gate.

### 6.1 «La pagina Allocazione», che non esiste

`distribution.source` (il suggerimento a `DistributionDialog.svelte:204`) e `distribution.differs`
(`:66`) rimandano ai «valori della pagina Allocazione» e ai pesi che «differiscono dalla pagina», in
tutte e 4 le lingue. Quella pagina non esiste: i valori sono quelli del pannello della Dashboard
`dashboard.allocation` («Asset Allocation», «Allocazione Patrimoniale», «Allocation Patrimoniale»,
«Asignación Patrimonial»). Correzione: i valori ×4 con `dev.py i18n update`, più i fallback EN nel
componente, con il nome del pannello della Dashboard.

### 6.2 «1 units»

Con una quantità di 1 il risultato scrive «buy 1 units». Le chiavi senza plurale sono sette:

| Dove | Chiave | Valore |
|---|---|---|
| `result/text.ts:21` | `result.text.buyUnits` | quantità dell'ordine, personale |
| `result/text.ts:29` | `result.text.stepUnits` | passo dell'ordine, pubblico; mancava nella lista originale |
| `result/text.ts:39` | `result.text.pricePer` | base del prezzo, pubblica; si vede solo quando è diversa da 1 |
| `result/text.ts:48` e `:54` | `result.text.units` | minimo e tetto della route, personali |
| `result/OrderDetail.svelte:57` e `:58` | `result.detail.quantityExact`, `.quantityEstimated` | quantità economica, personale; trovate rileggendo per questo piano |

Correzione: il plurale ICU, `{count, plural, one {…} other {…}}`, con un `count` numerico accanto alla
quantità già formattata, come fa già `brokers.stepUnits` (`modeText.ts:28-31`). La libreria usa
`Intl.PluralRules`, quindi la forma giusta la sceglie la lingua (per esempio in francese 1,5 è
singolare).

**Privacy.** Quando la quantità è mascherata, il `count` è sempre quello del plurale. Il singolare
rivelerebbe che la quantità è 1. La funzione che sceglie il `count` va in `planner/format.ts`,
l'unico adattatore privacy del planner.

### 6.3 La distanza L2 e la lingua — chiusa con (a) il 2026-10-06

> **Decisione del coordinator**: opzione (a), chiusa senza cambiare codice.

`formatPlannerL2` (`format.ts:206`) scrive la distanza con `toLocaleString(undefined, …)`, cioè nella
lingua del browser. Lo fa anche il formatter del denaro di tutta l'app
(`utils/currency/currencyFormat.ts:39`, `:61`), mentre quantità e tassi usano `formatDecimalForDisplay`
(punto decimale, senza separatore delle migliaia). La nota originale di R7
(`plan-phase00PacRound5PostMerge.prompt.md:992`) confrontava L2 con quantità e tassi; ma L2 è un
importo in valuta, e segue la regola del denaro.

- **(a), consigliata:** chiudere senza cambiare codice. L2 è denaro e segue la regola del denaro di
  tutta l'app.
- **(b):** scriverla come le quantità, col punto e senza separatore.

Una lingua dei numeri uguale a quella dell'app, per tutto, è un lavoro più largo: backlog.

### 6.4 File di R7

`planner/steps/DistributionDialog.svelte`, `planner/result/text.ts`, `planner/result/OrderDetail.svelte`,
`planner/format.ts`; i valori ×4 con `dev.py i18n update`; i test con il test-author
(`planner/format.test.ts`, già nel runner; un eventuale `result/text.test.ts` chiede una riga in più
in `_frontend_utility.py`).

Commit: `fix(pac): …`, con la riga 🐛 del CHANGELOG proposta al coordinator.

## 7. Definition of done

- Nel sorgente nessun simbolo P1, verificato con `rg`: `allocation_source` nel report,
  `PortfolioAllocationSource*`, `build_portfolio_allocation_source`, `allocationSource.ts`.
- Le 12 sezioni del report fissate da un test; una richiesta con `allocation_source` riceve 422.
- `include_broker_pnl_history` ancora coperto.
- Tutti i gate di S8 verdi, con il carico annotato.
- Parità i18n fra le 4 lingue e diff i18n limitato alle chiavi della lista.
- Porta 6151 libera alla consegna.
- Questo piano aggiornato dopo ogni passo.
- R7: le sette chiavi col plurale, la privacy rispettata, il testo della Dashboard ×4, L2 come deciso.

## 8. Avanzamento

| Passo | Stato | Data |
|---|---|---|
| S0 journal | ✅ | 2026-10-06 |
| S1 elenco al coordinator | ✅ | 2026-10-06 19:46; risposta ricevuta lo stesso giorno |
| S2 rossi | ✅ | 2026-10-06 20:04 |
| S3 backend | ✅ | 2026-10-06 20:12 |
| S4 frontend core | ✅ con la riga del runner | 2026-10-06 |
| S5 estensione (b) | ✅ | 2026-10-06 |
| S6 runner e i18n | ✅ 285 chiavi tolte ×4, da 4 508 a 4 223 per lingua (appendice A) | 2026-10-06 20:32 |
| S7 docs | ✅ docs-writer, una riga | 2026-10-06 |
| S8 gate | ✅ 18 controlli, tutti verdi (check-links rosso solo per D28, accettato) | 2026-10-06 20:45 |
| S9 checkpoint | ✅ previsione rifatta: 0 conflitti con la famiglia Risk; CHECKPOINT READY, poi FROZEN | 2026-10-06 20:55 |
| R7 | ⏳ | |

## Appendice A — le 285 chiavi tolte in S6

Tolte con `dev.py i18n remove <chiave> -f`, una per chiamata, in tutte e 4 le lingue. Fonte: la
lista del P1 (sessione, `files/p12-i18n-remove-keys.txt`), ricontrollata in S6 sulla base `a7d0b37ec`.

### G1 — `tools.allocation`, senza riferimenti (65)

```text
tools.allocation.asset.custodyCount
tools.allocation.asset.futureConstraints
tools.allocation.asset.futureConstraintsHint
tools.allocation.diagnostics.invalid
tools.allocation.diagnostics.needsInput
tools.allocation.diagnostics.noIssues
tools.allocation.diagnostics.ready
tools.allocation.diagnostics.technical
tools.allocation.diagnostics.unsupported
tools.allocation.fundingSummary.afterAnalysis
tools.allocation.fundingSummary.available
tools.allocation.fundingSummary.contributions
tools.allocation.fundingSummary.empty
tools.allocation.fundingSummary.existing
tools.allocation.fundingSummary.hint
tools.allocation.fundingSummary.title
tools.allocation.fundingSummary.updating
tools.allocation.issues.assetsRequired
tools.allocation.issues.cashRequired
tools.allocation.issues.contributionStep
tools.allocation.issues.currencyDomain
tools.allocation.issues.duplicateCurrency
tools.allocation.issues.duplicateInstrument
tools.allocation.issues.duplicateRow
tools.allocation.issues.duplicateTarget
tools.allocation.issues.fieldRequired
tools.allocation.issues.generic
tools.allocation.issues.holdingsRequired
tools.allocation.issues.identityRate
tools.allocation.issues.identityRateRedundant
tools.allocation.issues.incompleteDecimal
tools.allocation.issues.initialDebt
tools.allocation.issues.invalidCurrency
tools.allocation.issues.invalidDate
tools.allocation.issues.invalidDecimal
tools.allocation.issues.invalidQuoteBasis
tools.allocation.issues.inventoryOffGrid
tools.allocation.issues.negativeContribution
tools.allocation.issues.nonintegerWholeStep
tools.allocation.issues.nonpositiveFxRate
tools.allocation.issues.nonpositiveMonetaryStep
tools.allocation.issues.nonpositivePrice
tools.allocation.issues.nonpositiveQuantityStep
tools.allocation.issues.numericDomain
tools.allocation.issues.quoteRequired
tools.allocation.issues.referenceAfterAsOf
tools.allocation.issues.referenceDateUnspecified
tools.allocation.issues.shortInventory
tools.allocation.issues.targetOutOfRange
tools.allocation.issues.targetRequired
tools.allocation.issues.targetTotal
tools.allocation.issues.targetsRequired
tools.allocation.issues.unselectedTarget
tools.allocation.issues.unusedValuation
tools.allocation.issues.valuationRateRequired
tools.allocation.path.cash
tools.allocation.path.contributions
tools.allocation.path.holdings
tools.allocation.path.targets
tools.allocation.path.valuationRates
tools.allocation.results.stale
tools.allocation.target.remaining
tools.allocation.target.selectAssetsFirst
tools.allocation.target.total
tools.allocation.target.visual
```

### G2 — `tools.portfolioRebalancer`, i testi del P1, senza riferimenti (28)

```text
tools.portfolioRebalancer.analyze
tools.portfolioRebalancer.custodyContext
tools.portfolioRebalancer.customizedRemovalMessage
tools.portfolioRebalancer.customizedRemovalTitle
tools.portfolioRebalancer.description
tools.portfolioRebalancer.funding.hint
tools.portfolioRebalancer.funding.title
tools.portfolioRebalancer.holdings.hint
tools.portfolioRebalancer.holdings.title
tools.portfolioRebalancer.name
tools.portfolioRebalancer.p1.description
tools.portfolioRebalancer.p1.title
tools.portfolioRebalancer.results.availableCash
tools.portfolioRebalancer.results.boundary
tools.portfolioRebalancer.results.currentValue
tools.portfolioRebalancer.results.currentWeight
tools.portfolioRebalancer.results.custodyContexts
tools.portfolioRebalancer.results.empty
tools.portfolioRebalancer.results.hint
tools.portfolioRebalancer.results.investedTotal
tools.portfolioRebalancer.results.targetValue
tools.portfolioRebalancer.results.title
tools.portfolioRebalancer.results.valueGap
tools.portfolioRebalancer.results.zeroInvested
tools.portfolioRebalancer.targetEditor.copyCurrent
tools.portfolioRebalancer.targetEditor.hint
tools.portfolioRebalancer.targetEditor.title
tools.portfolioRebalancer.uncustodied
```

### G3 — `tools.pacAllocator` fuori dal planner, senza riferimenti (`name` e `description` restano) (168)

```text
tools.pacAllocator.addManualAsset
tools.pacAllocator.analyze
tools.pacAllocator.analyzing
tools.pacAllocator.asOfDate
tools.pacAllocator.assets.hint
tools.pacAllocator.assets.title
tools.pacAllocator.brokerCustody
tools.pacAllocator.cash.addContribution
tools.pacAllocator.cash.addCurrency
tools.pacAllocator.cash.amount
tools.pacAllocator.cash.backToBrokers
tools.pacAllocator.cash.backendAggregate
tools.pacAllocator.cash.contributions
tools.pacAllocator.cash.contributionsHint
tools.pacAllocator.cash.enterAmounts
tools.pacAllocator.cash.existing
tools.pacAllocator.cash.existingHint
tools.pacAllocator.cash.fromBrokers
tools.pacAllocator.cash.fullNativeReserve
tools.pacAllocator.cash.loadingBrokerCash
tools.pacAllocator.cash.markNoneContributions
tools.pacAllocator.cash.markNoneExisting
tools.pacAllocator.cash.markNotSupplied
tools.pacAllocator.cash.monetaryStep
tools.pacAllocator.cash.monetaryStepHint
tools.pacAllocator.cash.noNativeBalances
tools.pacAllocator.cash.noOwnerBrokers
tools.pacAllocator.cash.noSelectedBalances
tools.pacAllocator.cash.noneContributions
tools.pacAllocator.cash.noneExisting
tools.pacAllocator.cash.notSupplied
tools.pacAllocator.cash.refreshingSelection
tools.pacAllocator.cash.selectedReserves
tools.pacAllocator.cash.sourceStale
tools.pacAllocator.cashPools
tools.pacAllocator.cashPoolsHint
tools.pacAllocator.confirmDeselectMessage
tools.pacAllocator.confirmDeselectTitle
tools.pacAllocator.custodyContext
tools.pacAllocator.custodyContexts
tools.pacAllocator.customizedRemovalItems
tools.pacAllocator.customizedRemovalMessage
tools.pacAllocator.customizedRemovalTitle
tools.pacAllocator.denominatorHint
tools.pacAllocator.draftPreserved
tools.pacAllocator.duplicate
tools.pacAllocator.economicShare
tools.pacAllocator.economicShareHint
tools.pacAllocator.emptyRowsHint
tools.pacAllocator.exactView
tools.pacAllocator.formattedView
tools.pacAllocator.fullCustody
tools.pacAllocator.fundsHint
tools.pacAllocator.fundsTitle
tools.pacAllocator.gallery.empty
tools.pacAllocator.gallery.hint
tools.pacAllocator.gallery.inactive
tools.pacAllocator.gallery.observed
tools.pacAllocator.gallery.otherUsers
tools.pacAllocator.gallery.owned
tools.pacAllocator.gallery.search
tools.pacAllocator.gallery.title
tools.pacAllocator.gallery.zeroPosition
tools.pacAllocator.gridModeHint
tools.pacAllocator.identityAndCustody
tools.pacAllocator.importedSnapshot
tools.pacAllocator.initialState
tools.pacAllocator.instrumentId
tools.pacAllocator.issues
tools.pacAllocator.loadingOwnedAssets
tools.pacAllocator.manual
tools.pacAllocator.manualCopy
tools.pacAllocator.missingPrice
tools.pacAllocator.modified
tools.pacAllocator.nativePrice
tools.pacAllocator.newManualAsset
tools.pacAllocator.noAssetMatches
tools.pacAllocator.noCurrentCustody
tools.pacAllocator.noOrders
tools.pacAllocator.noOwnedAssetsHint
tools.pacAllocator.normalizedInput
tools.pacAllocator.p1.description
tools.pacAllocator.p1.title
tools.pacAllocator.personalShare
tools.pacAllocator.pilotNotice
tools.pacAllocator.platformError
tools.pacAllocator.platformErrorTitle
tools.pacAllocator.priceAt
tools.pacAllocator.quantityStepHint
tools.pacAllocator.quoteBasisHint
tools.pacAllocator.rates.add
tools.pacAllocator.rates.copySaved
tools.pacAllocator.rates.copyUnavailable
tools.pacAllocator.rates.date
tools.pacAllocator.rates.description
tools.pacAllocator.rates.enterManually
tools.pacAllocator.rates.equationHint
tools.pacAllocator.rates.nativeCurrency
tools.pacAllocator.rates.noCashConversion
tools.pacAllocator.rates.reason
tools.pacAllocator.rates.reasonAssets
tools.pacAllocator.rates.reasonCash
tools.pacAllocator.rates.reasonContribution
tools.pacAllocator.rates.title
tools.pacAllocator.rates.titleNumbered
tools.pacAllocator.rates.value
tools.pacAllocator.readOnlyFacts
tools.pacAllocator.reportCurrency
tools.pacAllocator.result.gap
tools.pacAllocator.result.row
tools.pacAllocator.result.target
tools.pacAllocator.result.value
tools.pacAllocator.result.weight
tools.pacAllocator.resultMeaning
tools.pacAllocator.results.boundary
tools.pacAllocator.results.budget
tools.pacAllocator.results.contributions
tools.pacAllocator.results.empty
tools.pacAllocator.results.existingCash
tools.pacAllocator.results.hint
tools.pacAllocator.results.idealAllocation
tools.pacAllocator.results.title
tools.pacAllocator.revision
tools.pacAllocator.rowLimitHint
tools.pacAllocator.rowLimitWarning
tools.pacAllocator.rows.addAsset
tools.pacAllocator.rows.description
tools.pacAllocator.rows.empty
tools.pacAllocator.rows.fractional
tools.pacAllocator.rows.gridMode
tools.pacAllocator.rows.identity
tools.pacAllocator.rows.initialQuantity
tools.pacAllocator.rows.price
tools.pacAllocator.rows.quantityStep
tools.pacAllocator.rows.quoteBasis
tools.pacAllocator.rows.quoteDate
tools.pacAllocator.rows.rowNumber
tools.pacAllocator.rows.sameAsset
tools.pacAllocator.rows.target
tools.pacAllocator.rows.title
tools.pacAllocator.rows.whole
tools.pacAllocator.scenario
tools.pacAllocator.selectedContextCount
tools.pacAllocator.selectedContexts
tools.pacAllocator.selectedContextsHint
tools.pacAllocator.snapshotAt
tools.pacAllocator.stale.ignored
tools.pacAllocator.stale.pending
tools.pacAllocator.stale.result
tools.pacAllocator.staleLabel
tools.pacAllocator.state.invalid
tools.pacAllocator.state.needsInput
tools.pacAllocator.state.ready
tools.pacAllocator.state.unsupported
tools.pacAllocator.stopWaiting
tools.pacAllocator.target
tools.pacAllocator.targetEditor.hint
tools.pacAllocator.targetEditor.title
tools.pacAllocator.totals.combinedCash
tools.pacAllocator.totals.contributions
tools.pacAllocator.totals.existingCash
tools.pacAllocator.totals.invested
tools.pacAllocator.totals.maxGap
tools.pacAllocator.totals.squaredGap
tools.pacAllocator.units
tools.pacAllocator.valuationSettings
tools.pacAllocator.valuationSettingsHint
tools.pacAllocator.valuationSettingsInfo
```

### G4 — `tools.pacAllocator.planner`, usate solo da `SourceCopyDialog.svelte`, cancellato in S5 (14)

```text
tools.pacAllocator.planner.assetCopy.empty
tools.pacAllocator.planner.assetCopy.manual
tools.pacAllocator.planner.classificationsCopy.source
tools.pacAllocator.planner.classificationsCopy.title
tools.pacAllocator.planner.copy.apply
tools.pacAllocator.planner.copy.ownerScope
tools.pacAllocator.planner.copy.reading
tools.pacAllocator.planner.copy.rule
tools.pacAllocator.planner.copy.stop
tools.pacAllocator.planner.fxCopy.empty
tools.pacAllocator.planner.fxCopy.source
tools.pacAllocator.planner.fxCopy.title
tools.pacAllocator.planner.pricesCopy.source
tools.pacAllocator.planner.pricesCopy.title
```

### G5 — `tools.pacAllocator.planner`, usate solo dai rami prezzo, esposizioni e FX di `ConflictDialog.svelte`, tolti in S5 (10)

```text
tools.pacAllocator.planner.conflict.priceLine
tools.pacAllocator.planner.conflict.pricePrevious
tools.pacAllocator.planner.conflict.priceIncoming
tools.pacAllocator.planner.conflict.priceCurrent
tools.pacAllocator.planner.conflict.exposuresPrevious
tools.pacAllocator.planner.conflict.exposuresYours
tools.pacAllocator.planner.conflict.exposuresIncoming
tools.pacAllocator.planner.conflict.fxPrevious
tools.pacAllocator.planner.conflict.fxIncoming
tools.pacAllocator.planner.conflict.fxCurrent
```
