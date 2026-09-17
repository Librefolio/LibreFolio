# Step 1 — contratti pubblici, dipendenza SCIP e capacità

**Stato:** IN PROGRESS — G2/G4 COMPLETE, G3 W0 CHECKPOINT READY,
G5 OPEN.
**Dipende da:** planning checkpoint, autorizzazione prodotto, handshake gruppo C.
**Blocca:** core, shell frontend, solver e client generato.

← Master: [piano implementativo](plan-phase00PacRebalancerImplementation.prompt.md)
← Autorità: [target](../plan-phase00PacRebalancerTargetDesign.prompt.md) ·
[architettura](../plan-phase00PacRebalancerArchitecture.prompt.md)
→ Round 1 piattaforma:
[deadline, memoria e metriche Tool](plan-phase00Step1Round1-ToolPlatformCapacity.prompt.md)

## 1. Scopo

Congelare prima del codice downstream:

1. handshake con la piattaforma Tool;
2. schema pubblico strict e comprensibile anche da un agente MCP;
3. fixture canoniche;
4. limiti input/output misurati sul prodotto reale;
5. update PySCIPOpt developer-owned;
6. dominio di capacità supportato da SCIP entro il runtime Tool.

Non si usa il vecchio witness audit da circa 289 KB come autorità. Il contratto
nasce dalle tabelle e dagli stati UI approvati.

## 2. Ownership

| Tipo | Percorso/oggetto | Writer |
|---|---|---|
| esclusivo | nuovi DTO in `backend/app/schemas/pac_allocator.py` | contract owner |
| esclusivo | fixture JSON request/result PAC/Rebalancer | contract owner |
| esclusivo | diagnostics capacity PAC/Rebalancer | capacity owner |
| shared | plugin descriptor/service registration | integration owner |
| shared/generated | OpenAPI/JSON Schema/TypeScript client | integration owner |
| developer-only | `Pipfile`, `Pipfile.lock` | developer |

Il contract owner non modifica registry/router generici del gruppo C. I DTO
P1 importati da plugin/test restano additivi e compatibili fino al checkpoint
integrazione CP5; vengono rimossi insieme ai consumer legacy dal solo
integration owner, evitando errori di collection intermedi.

## 3. Handshake gruppo C

Decisioni congelate dal coordinator il 2026-09-16:

| Voce | Decisione |
|---|---|
| service IDs | `pac_allocator` e `portfolio_rebalancer`, distinti e stabili |
| operation | `plan`, non `analyze` |
| schema/service version | contract `2.0.0`; implementation pin iniziale `2.0.0`; nessuna compatibilità implicita col P1 |
| worker entry | supervisor `backend.app.services.tools.worker.execute_tool_job`; plugin `backend.app.services.tool_plugins.pac_allocator.PacAllocatorTool` |
| renderer key | `pac-allocator` e `portfolio-rebalancer`; UI contract `2.0.0` |
| compute | `POST /api/v1/tools/compute`, bulk autenticato; Tool ripetibili e correlation ID distinti |
| diagnostics | `GET /api/v1/tools/diagnostics` per utente attivo autenticato; anonimo `401`; risposta solo strutturale/sanitizzata, senza scenario, trace, credenziali o valori personali |
| issue codes | shared `allocation.*`; product-specific `pac_allocator.*` / `portfolio_rebalancer.*`; severity e path tipizzati |
| limits | parameter `131072 B`, result `262144 B`, soft `4 s`, hard `5 s` |
| cancellation | `context.checkpoint()` tra le fasi/tier; hard cleanup del worker posseduto dal supervisor |
| generated code | `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync`, solo integration owner |

Non aggiungere endpoint schema specifici o `/tools/prefill`.

> **Note implementazione**: il codice piattaforma conferma registry
> transazionale, schema Pydantic, worker spawn, compute bulk e limiti. Il
> coordinator ha respinto la nuova ipotesi admin-only: avrebbe rotto
> `ToolAboutPanel`, API, test e docs esistenti senza migliorare privacy.

Test futuri assegnati a `test-author`:

- anonimo → diagnostics `401`;
- utente ordinario autenticato → `200`;
- payload privo di scenario, trace, credenziali e valori personali;
- nessuna privilege escalation attraverso diagnostics.

## 4. Wire input

### 4.1 Principi

- root object, `extra="forbid"`;
- object union discriminata, mai tuple posizionali;
- decimal/quantity/rate come stringhe finite;
- ID stabili e reference esplicite;
- unità nel nome o nel type;
- tabelle piatte per Asset, holding, cash, Broker, route e FX;
- nesting solo per dati davvero inseparabili;
- scenario manuale senza ID database valido;
- nessun default economico nascosto;
- nessun campo derivato che il backend possa calcolare senza ambiguità.

### 4.2 Famiglie richieste

```text
PlannerRequest
├── operation = "plan"
├── valuation_currency
├── as_of / source metadata
├── assets[]
├── brokers[]
├── holdings[]
├── existing_cash[]
├── contributions[]
├── order_routes[]
├── fx_routes[]
├── target_weights[]
└── policy
```

Ogni riga deve dichiarare:

- ID canonico e foreign key;
- currency/unit;
- provenance quando copiata;
- valore esatto come stringa;
- constraint BUY/SELL separati;
- semantica minimo `required` oppure `if_active`;
- instruction `whole_quantity` oppure `monetary_amount`;
- step/quantum esplicito.

Le famiglie economiche interessate dichiarano inoltre i campi seguenti, senza
default impliciti:

- prezzo sorgente, currency, `quote_base_quantity`, source, as-of e staleness;
- margine esecuzione BUY e SELL per route, incluso zero esplicito;
- fee BUY e SELL per Broker con fixed/rate/floor/cap;
- PMC con valuta fiscale e `withholding_kind`;
- tax rate per Asset;
- fee, spread e buffer delle route FX.

Cash esistente e nuovi contributi sono collezioni diverse. Il cash è
Broker×valuta o sorgente×valuta; non viene aggregato in una cassa convertita.

Ogni request include `currency_specs[]`. Ogni `CurrencySpec` contiene codice e
`minor_unit` quantum backend-derived, non editabile dall'utente. L'assembly di
dominio risolve il codice tramite utility valuta backend estesa con Babel CLDR
`get_currency_precision`; uno scenario manuale invia il codice ma non inventa
la precisione. Metadata irrisolvibile produce `needs_input`/`unsupported`.

Numeri input: stringhe fixed-point finite. Numeri derivati che possono essere
non terminanti usano una union oggetto nominata e discriminata:

```text
ExactNumber = FiniteDecimal | ExactRatio
```

`ExactRatio` porta numerator/denominator come stringhe intere bounded,
denominator positivo e proiezione display backend-authored esplicitamente non
autorevole. Vietati tuple, free-form object e schema ricorsivi.

**G3 Option B, decisione developer 2026-09-16:** il wire request valida la
forma canonica fixed-point, il tipo stringa, la finitezza e l'envelope lessicale
(`max_length=96`); rifiuta esponente, virgola, `+`, leading zero non canonici e
negative zero. Non applica `gt`/`ge`/`le`, regex positive/nonnegative o
validator relazionali ai valori economici request. Zero, negativi e valori
oltre il range economico restano quindi shape-valid e arrivano al normalizer,
che produce risultati typed `invalid`, `needs_input` o `unsupported` invece di
un transport `422`. Restano wire-invalid JSON malformato, tipi/discriminanti
errati, campi missing/extra, testo numerico non canonico e violazioni degli
envelope strutturali di ID/stringhe/interi JS-safe.

Non esistono campi pubblici `solver_budget` o count/cap configurabili
dall'utente. Il limite di cardinalità/resource supportato resta materia G5;
nessun array request viene troncato o ridimensionato silenziosamente.

La copia dominio minima del Broker espone `DomainBrokerIdentity.active` come
boolean obbligatorio senza default, insieme a `source_broker_id`, nome e
provenance. `ManualBrokerIdentity` non espone `active`. I flag sorgente
`allow_cash_overdraft`, `allow_asset_shorting`, `execution_profile_status` e
`opened_at` non fanno parte del request Planner. Una route inviata verso un
Broker dominio inattivo viene classificata dal normalizer con
`allocation.broker_inactive` a severità `error`; il wire strict accetta il
fatto e non abilita mai debito, short o capability implicite.

Precedente envelope usato per fixture/probe iniziali, **non più autorità per
un cap prodotto**:

| Famiglia | Max |
|---|---:|
| Asset | 32 |
| Broker | 8 |
| order route | 64 |
| valute | 8 |
| holding | 64 |
| cash | 32 |
| contributi | 16 |
| funding | 32 |
| capability | 32 |
| FX quote | 32 |
| FX route | 48 |
| issue | 128 |
| provenance | 256 |

Il developer ha ritirato il candidate runtime 16 Asset/4 Broker/32 route/4
valute come possibile cap pubblico. Nessuna cardinalità di questa tabella va
codificata nel contract finché G5 non misura il compiler di produzione.

Il contract manterrà comunque:

- envelope lessicali, ID, discriminator e interi strutturali bounded;
- preflight/runtime resource-bound con esito typed, mai truncation, da
  congelare in G5 senza trasformarlo in knob pubblico;
- distinzione fra request oltre envelope (`422`) e scenario strutturalmente
  valido ma oltre capacità supportata (`unsupported`/Tool limit);
- nessun default o ridimensionamento silenzioso.

Il nuovo target di misura è `1 GB RSS` massimo **per singolo job**; due worker
possono quindi avvicinarsi a `2 GB` complessivi. Il budget richiesto è `30 s`
riservato al solo solver; startup, build, replay Decimal, output e cleanup
richiedono margine addizionale. I limiti Tool correnti 4/5/20 s non possono
essere modificati da questo workstream: Group C deve progettare il nuovo
envelope piattaforma prima del prossimo probe.

### 4.3 Prodotti

- PAC: holding iniziali assenti o zero; SELL vietato.
- Rebalancer: holding iniziali obbligatorie e aggregate per identità Asset
  canonica; custodia Broker preservata.
- Un'unica request può mescolare route whole e monetary.
- La quota economica personale è separata dalla quantità custodita intera.

## 5. Wire output

```text
PlannerResult
├── availability
├── outcome / proof / stop_reason
├── scenario_basis
├── primary_solution
├── optional_deployment_solution
├── issues[]
└── provenance
```

Il risultato è product-shaped:

- Asset allocation completa;
- before/target/after e residui;
- esposizioni aggregate;
- funding actions;
- FX actions;
- Broker order rows;
- ledger Broker×valuta;
- cost/fee/tax/reserve totals;
- `F_ref`, `F_final`, `U`, `L2_fixed`;
- confronto e delta variante;
- proof e stop facts.

Entrambe le soluzioni espongono stato finale autorevole completo. È ammesso
condividere una base immutabile o riferimenti ID; il frontend non applica delta
per ricostruire denaro, quantità, ledger o obiettivi.

Issue:

- object tipizzato compatto;
- `code`, `severity`, `path`, `message_key`, `params`;
- nessuna stack trace o payload personale;
- ordine deterministico.

## 6. Status e proof

Congelare una union discriminata, non un record con opzionali arbitrari:

```text
PlannerResult =
    NeedsInputResult
  | InvalidResult
  | UnsupportedResult
  | ReadyNoOpResult
  | ReadyIncumbentResult
  | ReadyInfeasibleResult
  | ReadyNoIncumbentResult
```

Ogni variante possiede un discriminante letterale e soltanto i campi validi
per quello stato. Invarianti:

```text
availability = needs_input | invalid | unsupported | ready
outcome      = no_op | incumbent_found | infeasible_proven | no_incumbent
proof        = optimal_proven | gap_bounded | not_proven | infeasibility_proven
proof_source = exhaustive_oracle | score_lattice_closure | deterministic_conflict
stop_reason  = completed | time_limit | node_limit
```

- `outcome` esiste solo per `ready`;
- ogni piano pubblicato ha `decimal_verified`;
- `completed` è stop reason, non prova;
- floating `optimal`/`infeasible` non viene promosso;
- i campi non applicabili sono esclusi dalla variante; nullable è ammesso solo
  per un fatto semanticamente nullable, verificato nel TypeScript generato;
- `SELL_IRREDUCIBILITY_UNRESOLVED` è un issue code stabile prima del freeze.

`SolverStageEvidence` è dichiaratamente `reported_floating`: stage ID, scope
global/incumbent-face, sense, unità, primal/dual/absolute/relative gap come
testo Decimal finito, tolleranze e engine/version/settings. Non usa
`ExactRatio`. `gap_bounded` richiede bound finito e ordinato per ogni tier
normativo incompleto; altrimenti `not_proven`.

HTTP disconnect, hard timeout piattaforma, memory/resource termination, crash,
invalid output e cleanup failure restano errori Tool senza risultato
finanziario. Un result espone soltanto completion pulita, time limit o node
limit osservati dal solver e seguiti da replay Decimal valido.

## 7. Esercizio MCP

Senza leggere codice o docs esterne, un reviewer riceve soltanto JSON Schema e
deve costruire:

1. PAC minimo manuale, una valuta, una route whole;
2. PAC misto whole + monetary, più Broker;
3. Rebalancer multi-custody con `invest_only`;
4. Rebalancer `invest_and_sell` con fee/tax;
5. scenario con contributo separato dal cash;
6. scenario FX;
7. input invalid, missing, unsupported.

Almeno una request usa margine BUY non zero e una fee con floor/cap; almeno una
SELL monetary dichiara step, minimo/cap, PMC, tax rate e withholding. L'importo
lordo scelto è output del solver, non input o autorizzazione dell'utente.

Acceptance:

- tutti gli input validi passano il vero TypeAdapter;
- gli invalidi producono codici/path leggibili;
- nessuna domanda richiede conoscenza del DB LibreFolio;
- nessun campo duplicato o ambiguo sopravvive per comodità interna;
- schema e TypeScript preservano discriminanti e precisione.
- nessun campo economico obbligatorio richiede un default implicito.

## 8. Payload witness

### 8.1 Misure

Per request e result:

- JSON UTF-8 compatto e pretty;
- schema export;
- totale per sezione top-level;
- conteggio righe e cardinalità;
- primary vs deployment;
- issues worst valid;
- provenienza;
- percentuale di headroom.

### 8.2 Gate

- input `<=131072 B`;
- ogni result `<=262144 B`;
- target ingegneristico: almeno 15% di headroom, salvo decisione developer
  esplicita su un witness product-shaped;
- nessuna compressione/base64;
- nessuna paginazione o secondo lookup;
- nessuna omissione di fatti finanziari obbligatori;
- nessun ricalcolo finanziario frontend;
- nessuna riduzione silenziosa del dominio.

Se il witness supera il target:

1. eliminare duplicazione non semantica;
2. condividere cataloghi immutabili e ID;
3. mantenere finali autorevoli completi;
4. quantificare ogni eventuale compromesso di cardinalità;
5. chiedere decisione developer.

## 9. Update PySCIPOpt developer-owned

Con tutte le lane ferme:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
pipenv install pyscipopt==<versione-approvata>
```

Il developer:

1. seleziona una versione compatibile Python 3.13/macOS/Linux/container;
2. aggiorna `Pipfile` e `Pipfile.lock`;
3. registra hash lock e versioni Python/PySCIPOpt/SCIP;
4. riapre le lane soltanto dopo verifica import.

Gli agenti non installano, non creano venv e non modificano lock.

**✅ Completato 2026-09-16.**

> **Note implementazione**: dependency checkpoint
> `941834237696f32bbabfde62a08e070e4b23758e` verificato dal coordinator.
> Versioni: PySCIPOpt `6.2.1`, SCIP `10.0.2`, NumPy `2.5.3`, SciPy `1.18.1`,
> highspy `1.15.1`. Smoke developer: import e MIQCP epigrafo convesso
> `x=3`, `z=0`, status `optimal`, un thread, seed fisso. Hash:
> `Pipfile=9ff612277af827364b3b777cc36ed34c8d22ac7c6df13470c38a266cb86a5f70`;
> `Pipfile.lock=67f0b3bee3da6c1c7fdf6e8ce4fa7d714e482d2e2f0722da54bdb6d3df3d40b1`.

> **⚠️ Fuori pista**: il resolver ha aggiornato NumPy `2.5.2 -> 2.5.3`.
> Cambio accettabile perché il manifest dichiara `numpy = "*"`, ma richiede
> regressione mirata dei percorsi numerici/portfolio prima del gate combinato.

> **Note implementazione — compatibilità NumPy 2026-09-16**: sulla lane
> `6153` / `/tmp/librefolio-r2-d` sono passati in sequenza gli existing
> selector `services portfolio-engine` (42), `services series-preparation`
> (7), `services risk-optimization` (10), `services quantlib-runtime` (2) e
> `schemas risk` (14): **75 passed**, nessun failure. Questa evidenza chiude
> il controllo mirato macOS sul bump patch; non sostituisce i gate combinati
> finali né le prove Linux/container.

## 10. Capacity probe

Corpus:

| Famiglia | Asset | Broker | Route | Valute | Scopo |
|---|---:|---:|---:|---:|---|
| oracle-xs | 1–4 | 1–2 | 1–8 | 1–2 | confronto esaustivo |
| small | 8 | 2 | 16 | 2 | tutte le policy |
| medium | 16 | 4 | 32 | 4 | fee/FX/activation |
| candidate-max | dal contract | dal contract | dal contract | dal contract | cap pubblico |
| sell-stress | cap SELL | cap Broker | cap route | multi | controfattuali |

Misurare:

- import cold/warm;
- build MIQP e MIQCP;
- tempo per tier;
- node count/gap;
- replay exact;
- oracle/closure;
- report serialize/revalidate;
- wall totale;
- peak RSS;
- cancel latency;
- cleanup thread/process/file;
- wheel e container.

Eseguire inoltre il bulk envelope reale:

- `max_batch_items=4`;
- `workers=2`;
- `queue_timeout_ms=5000`;
- `job_timeout_ms=5000`;
- quattro item candidate-max con service ID distinti/ripetuti;
- tempi di attesa, esecuzione, timeout e cleanup per ogni item.

Il dominio pubblico viene congelato soltanto se candidate-max rispetta soft
`4 s` e hard `5 s` con margine operativo. In caso contrario si torna al
developer con dati, non con fallback.

### 10.1 Probe macOS preliminare — 2026-09-16

Probe sintetico bounded, prima del contract/candidate-max definitivo:

- cold import child: `47.30 ms`; wall process `119.60 ms`; RSS `33,767,424 B`;
- modello fixed-L2 epigraph, 8 Asset/16 route: `optimal`, `399.43 ms`,
  853 nodi, 29 soluzioni;
- stesso dominio con vincolo quadratico addizionale: `optimal`, `752.88 ms`,
  1,363 nodi, 33 soluzioni;
- 16 Asset/32 route e 32 Asset/64 route: incumbent trovati, ma `timelimit`
  a 3 s e gap SCIP non informativo (`1e20`);
- bulk 4×(16 Asset/32 route), 2 processi: wall `6,597.01 ms`; ogni item
  `timelimit` a 3 s con 39–41 incumbent;
- warm import in-process: `0.004 ms`; import iniziale nello stesso probe
  `72.16 ms`;
- 16 Asset/32 route resta `timelimit` sia a 4 s sia a 5 s, con 48–55
  incumbent ma gap floating non informativo;
- sostituendo il singolo epigrafo globale con epigrafi quadratici separabili
  per Asset e warm-start deterministico, gli stessi domini sintetici chiudono
  floating `optimal`: 8/16 route `31.19 ms`, 16/32 route `55.31 ms`,
  32/64 route `51.94 ms`, tutti a un nodo e gap SCIP `0`;
- oracle indipendente esaustivo, 3 Asset: stesso optimum lessicografico del
  modello (`q=(8,2,1)`, `L2=7773`, `U=91`), `1.68 ms`;
- `interruptSolve()` da thread Python non ha preemptato `optimize()` prima
  del limite: non è una strategia di cancellation accettabile;
- terminazione del processo solver posseduto: `1.48 ms`, exit `SIGTERM`,
  processo non vivo e PID rilasciato.

> **Note implementazione**: il probe prova packaging, piccolo MIQCP, oracle
> feasibility e cleanup hard su macOS. Non chiude G5: il candidate-max dipende
> dal contract, 16+ Asset non hanno prova entro 3 s, il gap floating non è
> pubblicabile e cancellation cooperativa richiede time limit/event hook o
> resta affidata al supervisor di processo.

> **⚠️ Fuori pista**: il primo modello sintetico, con simmetria route e scala
> dei residui troppo aggressiva, non trovava incumbent entro 3 s. Dopo
> scaling coerente, route non equivalenti, at-most-one route e warm-start
> zero, 8 Asset chiudeva; gli epigrafi separabili hanno poi eliminato il
> collo di bottiglia anche a 32 Asset. Questo rende la formulazione un gate
> architetturale del compiler, non prova A: status/gap floating non vengono
> promossi senza replay Decimal e oracle/closure.

### 10.2 Determinism matrix preliminare — 2026-09-16

Eseguite 30 run per cella, 2 processi, seed fisso, un thread, budget solver
1/2/4 s; totale 270 solve multi-stage:

| Dominio | Esito stage | Azioni/score distinti | Exact tuple candidato | Baseline deterministica | Peak RSS |
|---|---|---:|---|---|---:|
| 8 Asset / 16 route | 4/4 stage floating `optimal` | 1 / 1 | `(L2=5940,U=46,rows=8,tie=953)` | `(72995,687,8,853)` | 69,959,680 B |
| 16 Asset / 32 route | L2 floating `optimal`; U `timelimit` | 1 / 1 | `(16892,40,16,3646)` | `(133189,1295,16,3416)` | 107,544,576 B |
| 32 Asset / 64 route | L2 floating `optimal`; U `timelimit` | 1 / 1 | `(35215,35,32,14415)` | `(249778,2504,32,13758)` | 72,564,736 B |

- ogni candidato batte lessicograficamente la costruzione feasible
  deterministica;
- hash azioni identico fra tutte le 30 run e fra budget 1/2/4 s per ogni
  dominio;
- 8/16 completa le quattro facce in `704–843 ms`;
- 16/32 e 32/64 consumano il budget sul secondo tier ma producono sempre lo
  stesso incumbent;
- questa matrice misura determinismo/performance, non proof A: anche 8/16
  richiede oracle o score-lattice closure esatta prima di
  `optimal_proven`; 16/32 e 32/64 restano candidati
  `incumbent_found/not_proven` dopo futuro replay Decimal.

### 10.3 Bulk separabile preliminare — 2026-09-16

Quattro item 16 Asset/32 route, due processi, budget solver 4 s:

- wall complessivo `8,327.342 ms`;
- item `4,052.749–4,076.372 ms`;
- tutti con action hash
  `a54406da615f7b2f7bc8cd9d3eae8c4c05c9fc0ec338553116e1ed77202adbc6`;
- tutti con exact candidate tuple `(16892,40,16,3646)`, migliore della
  baseline `(133189,1295,16,3416)`;
- tutti con stage `[L2=optimal floating, U=timelimit]`;
- peak RSS per processo `93,011,968–99,188,736 B`.

Il singolo item resta sotto hard 5 s, ma ~4.08 s non lascia il margine
operativo richiesto dal soft 4 s. Il wall bulk resta compatibile con due
worker, ma non rappresenta ancora coda/timeout/cleanup dell'executor Tool
reale. G5 resta aperto: serve ridurre il budget solver sotto 4 s per
riservare serialize/replay/report/cleanup, poi ripetere nel worker integrato.

Ripetizione con budget solver `3.5 s`:

- wall complessivo `7,288.051 ms`;
- item `3,552.666–3,556.702 ms`;
- stesso action hash, exact candidate tuple e stage state di 4 s;
- peak RSS `91,013,120–98,107,392 B`;
- riserva osservata rispetto a hard 5 s: almeno `1,443.298 ms` prima
  dell'overhead del worker integrato.

`3.5 s` è quindi candidato per il budget solver interno, non ancora default
pubblico: il gate finale deve includere build, replay Decimal,
serializzazione, queue e cleanup del processo Tool reale.

> **⚠️ Fuori pista**: il primo avvio dell'harness Tool reale da `/tmp`
> (`PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python
> /tmp/libreFolio_pac_real_tool_capacity.py`) si è fermato prima di
> collection/worker con `ModuleNotFoundError: No module named 'backend'`,
> perché Python ha usato `/tmp` come import root. Nessun DB, server o file
> applicativo toccato; corretto l'harness aggiungendo il cwd al `sys.path`
> prima degli import.

> **⚠️ Fuori pista**: il corpus bulk originale usava il modello monolitico
> ormai scartato e quindi sovrastimava il costo del primo tier. La ripetizione
> separabile dimostra incumbent stabile e consumo del budget sul tier U, ma
> non autorizza cap pubblico o proof A.

### 10.4 Gate executor Tool reale — 2026-09-16

Harness diagnostico fuori repository, registry isolato, stesso
`ToolExecutor`/`execute_tool_job`/spawn/validation/serialization/cleanup di
produzione. Budget SCIP interno `3.25 s`, riserva post-solve `0.35 s`;
operation soft `4 s`, hard `5 s`. Tutti i risultati dichiarano
`proof=not_proven`.

| Misura | 8 Asset / 16 route | 16 Asset / 32 route |
|---|---:|---:|
| single response wall | `1,112.544 ms` | `3,646.166 ms` |
| startup child | `256 ms` | `255 ms` |
| cold PySCIPOpt import | `70.355 ms` | `36.743 ms` |
| build | `6.774 ms` | `2.580 ms` |
| solve tiers | `728.772 ms` | `3,303.746 ms` |
| replay Decimal | `0.022 ms` | `0.038 ms` |
| report | `0.052 ms` | `0.057 ms` |
| cleanup | `43 ms` | `39 ms` |
| result bytes | `938 B` | `1,337 B` |
| peak RSS child | `87,851,008 B` | `113,475,584 B` |
| stage | 4× floating `optimal` | L2 `optimal`, U `timelimit` |

Bulk reale 4×16/32, due worker:

- response wall/server `7,338.101/7,338 ms`, sotto request deadline 20 s;
- prima wave queue `0 ms`, seconda wave `3,663 ms`, sotto queue timeout
  5 s;
- ordine e cardinalità preservati, quattro correlation ID e quattro
  execution ID distinti;
- response `7,399 B`; ogni result `1,337 B`;
- quattro action hash e exact tuple identici; tutti migliori della baseline;
- cleanup `47–60 ms`; nessun PID worker vivo dopo il proprio cleanup;
- snapshot dopo risposta: active/pending/queued/degraded `0/0/0/0`.

Determinism executor reale, 30 run per dominio:

- 8/16: `30/30` success, un hash, un exact score
  `(5940,46,8,953)`, tutte le quattro facce floating chiuse; max batch wall
  `2,226.371 ms`, peak RSS `88,915,968 B`;
- 16/32: `30/30` success, un hash, un exact score
  `(16892,40,16,3646)`, L2 floating chiuso/U timeout; max batch wall
  `7,403.163 ms`, peak RSS `114,376,704 B`;
- ogni candidato supera la baseline deterministica; ordine/cardinalità
  invariati; tutti gli executor snapshot idle; tutti i 60 PID worker
  terminati.

In totale l'harness ha completato `66/66` job Tool senza failure. Dopo
shutdown executor: active/pending/queued/degraded `0/0/0/0`. Il campione
pre-exit vedeva un solo helper `multiprocessing` del processo harness, non
un worker Tool; al termine del comando `ps -p 88025 ...` non restituiva
alcun processo. Tutti i PID Tool erano già provati morti prima dello
shutdown.

Conclusione limitata al vecchio envelope 4/5/20 s:

- 16 Asset/32 route è un punto misurato stabile, non un massimo prodotto;
- 8/16 supera performance/determinism nel corpus sintetico, ma
  `optimal_proven` resta subordinato a oracle/score-lattice esatto;
- 32/64 ha solo evidenza standalone, non integrata;
- nessuna di queste cardinalità autorizza un cap pubblico.

Artifact:
`/tmp/libreFolio_pac_real_tool_capacity.json`; log completo:
`/tmp/libreFolio_pac_real_tool_capacity.log`.

### 10.5 Reframe capacity developer — 2026-09-16

Scelta developer:

- evitare un limite basso per numero di Asset/route;
- analizzare la crescita reale di variabili, vincoli, nodi, wall e RSS;
- usare soglie resource-driven abbastanza alte da non colpire un uso
  ragionevole;
- massimo indicativo `1 GB RSS` per job;
- due worker ammessi, quindi circa `2 GB` Tool complessivi;
- `30 s` dedicati al solver per item, con overhead end-to-end separato.

G5 torna quindi aperto. Il prossimo gate, dopo design piattaforma C e compiler
PAC/Rebalancer rappresentativo, deve campionare separatamente:

1. Asset canonici;
2. route d'ordine per Asset e totali;
3. Broker;
4. valute/casse;
5. route FX;
6. modalità buy-only e invest-and-sell;
7. densità di fee, limiti e attivazioni.

Per ogni cella: dimensione modello, build, tier solve, incumbent/bound,
replay Decimal, bytes, RSS, cleanup e determinismo. L'andamento MIQCP può
essere esponenziale nel caso peggiore: “nessun limite” non è un contratto
sicuro. Il risultato atteso è un envelope anti-abuso alto più limite
tempo/memoria esplicito, non il precedente cap 16/4/32/4.

## 11. Sequenza esecutiva

- [x] 1. Verificare baseline, G1 e handshake C. ✅ 2026-09-16
- [x] 2. Inventariare P1 e rimuovere assunzioni wire obsolete dal design DTO.
      ✅ 2026-09-16
- [x] 3. Aggiungere input/output strict mantenendo import P1 collezionabili
      fino alla rimozione atomica a CP5. ✅ 2026-09-16
- [ ] 4. Generare JSON Schema e TypeScript; diff semantico.
- [ ] 5. Eseguire esercizio MCP.
- [x] 6. Costruire witness min/medium/max e breakdown deterministico.
      ✅ 2026-09-16
- [x] 7. Ottenere update dipendenza developer-owned. ✅ 2026-09-16
- [x] 8. Eseguire probe SCIP/capacity nella lane. ✅ 2026-09-16
- [ ] 9. Eseguire probe bulk 4-item/2-worker e congelare cardinalità,
      envelope, versioni, codici e fingerprint.
- [ ] 10. Ottenere review schema, auth e capacity.

Dopo ogni step aggiornare immediatamente questo file con data, nota,
evidenza e fuori-pista.

### 11.1 Handoff W0 G3 — 2026-09-16

> **Note implementazione:** il contract v2 è additivo dopo gli adapter P1 e
> dichiara root/adapters distinti PAC e Rebalancer `2.0.0`. Il recheck statico
> post-resume conferma che tutti i campi economici raggiungibili dalle request
> usano `PlannerFixedDecimal`, mentre gli alias positive/nonnegative rimasti
> sono raggiungibili soltanto dagli output autorevoli. Conferma inoltre
> `DomainBrokerIdentity.active` required/no-default, assenza del campo sul
> Broker manuale e assenza dei flag Broker sorgente dal wire Planner.

> **Note implementazione — fixture:** sei witness sintetici sono presenti in
> `backend/test_scripts/fixtures/pac_allocator/`: PAC min request/result,
> Rebalancer medium request/result e PAC candidate request/result. L'unico
> `domain_broker` delle fixture request porta `active=false`; i Broker manuali
> non portano il campo. I witness request includono intenzionalmente valori
> economici shape-valid ma semanticamente invalidi: minor unit/rate/step zero,
> prezzi/fee/cap/priorità/FX/buffer/target negativi e rate/share/weight oltre
> range.

> **Evidenza pre-freeze già acquisita:** roundtrip strict
> validate/dump/revalidate dei sei witness v2; roundtrip dei quattro root P1;
> profilo JSON Schema supportato (zero default/free-form/finance JSON-number,
> discriminanti e required preservati); regex frontend-compatible; Ruff,
> Black e `git diff --check` verdi. Misure compatte UTF-8:
> PAC min request/result `2,481/6,397 B`; Rebalancer medium request/result
> `13,781/19,516 B`; PAC candidate request/result `26,694/15,963 B`.
> Headroom rispettivamente `98.11/97.56%`, `89.49/92.56%`,
> `79.63/93.91%` rispetto ai limiti Tool request/result. Il resume corrente
> vietava test e comandi: questa evidenza non è stata rieseguita e resta da
> riconfermare sul checkpoint integrato.

> **⚠️ Fuori pista:** nessuno nel resume. Non sono stati avviati test,
> comandi, server, API sync o generazione; nessun file è stato staged.

> **Blocco esterno statico:** il test non posseduto
> `backend/test_scripts/test_schemas/test_pac_planner_schemas.py` costruisce
> ancora `PlannerBrokerIdentity` con `allow_cash_overdraft` e
> `allow_asset_shorting` nelle righe di supporto del probe Broker inattivo
> (occorrenze correnti alle linee 721–722 e 813–814), poi pretende un
> roundtrip strict. Questo contraddice il binding pubblico finale e deve
> fallire con `extra="forbid"`. Il test-author deve rimuovere i flag dai
> payload accettati e, se utile, trasformarli in probe espliciti di rejection.
> W0 non ha modificato il file test.

> **⚠️ Fuori pista — primo gate schema, 2026-09-16:** D-main ha eseguito
> `schemas pac-planner` sulla lane esclusiva `6153`: `165 passed, 12 failed`
> dopo collection/setup completi. Undici failure sono drift test-only: i
> payload helper inserivano erroneamente i flag sorgente
> `allow_cash_overdraft`/`allow_asset_shorting` nel public
> `DomainBrokerIdentity`, che correttamente li rifiuta come extra; fix
> restituito al test-author con obbligo di provare esplicitamente
> l'esclusione. Una failure è prodotto: `invest_and_sell` accettava route
> solo BUY nonostante il contratto richieda almeno una route SELL; validator
> stretto restituito al W0 owner. Nessun altro red, nessun DB/server residuo,
> nessun file staged.

> **Note implementazione — risoluzione W0 2026-09-16:** aggiunto al root
> `RebalancerInvestAndSellRequest` un validator strutturale post-parse che
> richiede almeno una `PlannerSellOrderRouteInput`. La regola non valida
> quantità o range economici e quindi non altera G3 Option B. Per divieto
> esplicito del resume W0, il selector non è stato rieseguito in questa lane;
> D-main deve riconfermare il caso mirato e il gate `schemas pac-planner`
> dopo la correzione test-author dei payload Broker.

> **⚠️ Fuori pista — review finale G3 2026-09-16:** dopo un focused verde
> `199/199`, il gate completo `schemas pac-planner` verde `392/392` e il
> preservato `schemas pac-analyze` verde `112/112`, la review read-only fresca
> ha individuato cinque stati impossibili non coperti: bound `gap_bounded`
> incoerente con l'incumbent Decimal, SELL pubblicabile con policy
> `invest_only`, pesi Asset indipendenti dai valori autorevoli, FX stale non
> accettato pubblicabile in un result ready e divergenza frontend/backend su
> negative zero. Ruff e `git diff --check` erano verdi; Black richiedeva una
> sola compattazione meccanica nel validator SELL.

> **Note implementazione — fix review G3 2026-09-16:** con autorizzazione
> coordinator sono stati aggiunti bound `min|max` sense-aware con identità
> completa stage/scope/unit, divieto SELL/evidence nei result `invest_only`
> primari e deployment, identità esatte peso×denominatore=valore per target,
> before e final, guardia output FX stale (`age_days >= 0`, `accepted=true`) e
> regex v2 portabili senza lookaround che rifiutano `-0`/`-0.000` senza
> modificare il regex P1. Black ha formattato soltanto
> `backend/app/schemas/pac_allocator.py`; Ruff sul file è verde. Regressioni
> test-author e rerun completi restano pendenti.

> **⚠️ Fuori pista — riconciliazione test 2026-09-16:** un primo focused
> post-catalogo ha prodotto `200 passed / 2 failed / 183 deselected`; entrambe
> le failure erano drift test-only perché Pydantic esporta i `Literal`
> singleton come `const` e quelli multipli come `enum`. Il test-author ha
> normalizzato le due rappresentazioni senza allargare i valori ammessi. Un
> probe metriche successivo è terminato prima degli import con
> `ModuleNotFoundError: backend` perché lo script temporaneo in `/tmp` non
> aveva il cwd in `sys.path`; nessun DB, file di prodotto o server è stato
> toccato. Corretto solo il bootstrap del probe, poi rimosso lo script.

> **Note implementazione — gate finali W0 G3 2026-09-16:** il focused dei
> cinque fix review è verde `36/36` (`392` deselected); il gate completo
> `schemas pac-planner` è verde `428/428`; il preservato
> `schemas pac-analyze` è verde `112/112`. Comandi:
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6153 --data-dir /tmp/librefolio-r2-d schemas pac-planner ...`,
> poi gli stessi argomenti per `schemas pac-planner` completo e
> `schemas pac-analyze`. Ruff sui tre path Python, Black `--check` e
> `git diff --check` sono verdi. La review read-only post-fix non ha trovato
> finding ad alta confidenza; capacity/runtime solver resta esplicitamente G5.

> **Note implementazione — wire evidence finale:** i sei fixture validano
> strict, dumpano e rivalidano. Byte `source/emitted/headroom-emitted`:
> PAC request min `3859/2481/128591`, PAC result min
> `10122/6404/255740`, PAC request candidate
> `29737/26694/104378`, PAC result candidate
> `18363/15970/246174`, Rebalancer request medium
> `21759/13781/117291`, Rebalancer result medium
> `33404/19499/242645`. I candidate restano specimen strutturali, non prova
> di capacità. JSON Schema compatti:
> PAC input/output `27397/70628 B`, Rebalancer input/output
> `38344/78959 B`. Fingerprint finali:
> PAC `e1a42a87d702aee0cd333a7a9570f2564c8cd6a607ed370ad3c9985ad2665fe5`;
> Rebalancer
> `56e80e456c11a99b6a2d9ecad3f16ef66912d27852028ea443f656546b63573d`.
> Nessun API sync, client generato, plugin, registry o runtime solver è stato
> avviato. Porta `6153` verificata libera; staged/unmerged `0/0`.

### 11.2 Correzione stretta route SELL/step whole — 2026-09-16

> **⚠️ Fuori pista:** la review coordinator successiva al checkpoint G3 ha
> rilevato due autorità spurie nel request v2. `gross_amount_requested`
> trasformava una decisione monetaria del solver in input/autorizzazione
> utente; `WholeQuantityCapability.quantity_step` accettava inoltre frazioni
> fixed-point incompatibili con una capability whole. Nessun percorso di
> compatibilità viene mantenuto perché il v2 non è ancora rilasciato.

> **Note implementazione:** dal public `PlannerSellOrderRouteInput` è stato
> rimosso `gross_amount_requested`. La SELL monetaria sceglie il lordo come
> quanta interi di `order_amount_step`, entro minimo, cap notional e inventario;
> `MonetaryAmountInstruction` nel result conserva l'importo scelto. Il
> `quantity_step` request whole usa ora il dedicated
> `PlannerWholeQuantityStep`: stringa intera canonica signed, massimo 96
> caratteri. Zero e negativi restano shape-valid per G3 Option B e sono
> classificati dal normalizer con
> `allocation.nonpositive_quantity_step`; frazioni come `1.5` sono
> transport-invalid. Gli alias output positive-whole e tutti i tipi/regex P1
> restano invariati.

> **Note implementazione — evidenza correzione:** baseline verificata
> `509929ab3e151e796fe5807cb6db77b8fb4480fb`, staged/unmerged `0/0`. I sei
> fixture passano import, strict validate/dump/revalidate; il request medium
> corretto misura `21625/13690/117382 B`
> (`source/emitted/headroom-emitted`). Gli altri cinque file fixture non sono
> cambiati. Il probe puro accetta step `"1"`, `"0"`, `"-1"` e gli estremi
> canonici da 96 caratteri; rifiuta `"1.5"`, `"+1"`, `"01"`, `"-0"`, 97
> caratteri e JSON number. Il medesimo probe conferma
> `extra_forbidden` se ricompare `gross_amount_requested`.

> JSON Schema compatti correnti: PAC input/output `27329/70628 B`;
> Rebalancer input/output `38069/78959 B`. Fingerprint correnti, che
> sostituiscono come autorità wire i valori storici §11.1: PAC
> `b76cc7114d6344bc54c844c2f85ccc45a39dbc0ddec4ad93d5a58aa4f8bc2ba1`;
> Rebalancer
> `df50a98897414b522e2bd498df20bb03387dedfd85e14174bee9d8a229fe2a0c`.
> Comandi puri eseguiti:
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python -m ruff
> check backend/app/schemas/pac_allocator.py`; stesso ambiente con
> `python -m black --check backend/app/schemas/pac_allocator.py`; stesso
> ambiente con `python -c` per import schema, sei roundtrip strict, probe
> lessicale/extra field, misura UTF-8 e fingerprint
> `backend.app.services.tools.schema`. Nessuna suite runtime, API sync,
> generazione client, plugin, registry o server è stata avviata.

> **Note implementazione — gate correzione D-main 2026-09-17:** D-main ha
> eseguito
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6153 --data-dir /tmp/librefolio-r2-d schemas pac-planner <six
> correction test names>`. Collection completa: `453`; deselected `428`;
> selected `25`. Esito `25/25 passed`, tempo pytest `0.73 s`, exit code `0`.
> Le sei declaration selezionate coprono: matrice di accettazione whole step;
> split schema request/output; rinvio al normalizer dei valori Option B
> `<= 0`; SELL medium senza gross field; obsolete gross
> `extra_forbidden`; deployment distinti senza proof annidato. Nessuna
> mutazione server/DB di prodotto; il runner ha archiviato soltanto log e
> snapshot test.

> **Note implementazione — gate completo D-main 2026-09-17:** eseguito
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6153 --data-dir /tmp/librefolio-r2-d schemas pac-planner`:
> `453/453 passed`, tempo pytest `1.64 s`, exit code `0`.

> **Note implementazione — preservazione P1 D-main 2026-09-17:** eseguito
> `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test
> --test-port 6153 --data-dir /tmp/librefolio-r2-d schemas pac-analyze`:
> `112/112 passed`, tempo pytest `0.73 s`, exit code `0`.

> **Note implementazione — micro-gate finale D-main 2026-09-17:** Ruff
> scoped su schema e schema-test `PASS`; Black `--check`: `2 files unchanged`.
> Il probe indipendente strict validate/dump/revalidate dei sei fixture è
> interamente verde. Byte `source/emitted`: PAC min request `3859/2481`, PAC
> min result `10122/6404`, PAC candidate request `29737/26694`, PAC candidate
> result `18363/15970`, Rebalancer medium request `21625/13690`, Rebalancer
> medium result `33404/19499`; tutti sotto i ceiling request/result
> `131072/262144 B`. Il profilo schema generato passa.

> Fingerprint indipendenti: PAC
> `b76cc7114d6344bc54c844c2f85ccc45a39dbc0ddec4ad93d5a58aa4f8bc2ba1`;
> Rebalancer
> `df50a98897414b522e2bd498df20bb03387dedfd85e14174bee9d8a229fe2a0c`.
> `git diff --check` sull'intero worktree `PASS`; lane `6153` libera.

> **Micro-review fresca:** `CLEAN`. Il public SELL gross field è
> completamente rimosso e un extra omonimo è strict-rejected; il whole step
> request è integer-only signed, bounded a 96 caratteri, con `<= 0` rinviato
> al normalizer W1; l'output positive-whole è invariato. Una deployment
> solution non contiene proof annidato o ereditato e lo rifiuta come extra.
> Il diff schema scoped lascia P1 intatto; il profilo schema generato è verde.

> **Dipendenza esplicita:** normalizer, model ed evaluator W1 già presenti
> continuano intenzionalmente a referenziare la semantica gross obsoleta e
> devono essere riconciliati immediatamente dopo il commit di questo
> micro-contract. Il checkpoint stabilisce l'autorità wire; non dichiara
> readiness runtime W1 standalone.

> **Stato correzione:** `MICRO-GATE PASS — SELECTIVE CHECKPOINT READY`.

## 12. Definition of Done

- handshake C firmato;
- schema strict, semplice, generated-client compatible;
- fixture PAC/Rebalancer complete;
- collection P1 preservata fino alla rimozione atomica CP5;
- esercizio MCP superato;
- witness sotto limiti con headroom riportata;
- update lock developer-owned verificato;
- MIQP/MIQCP/bulk/cancel/cleanup/packaging misurati;
- dominio pubblico supportato dichiarato;
- nessun codice downstream usa DTO non congelati;
- checkpoint CP1 pronto e porta `6153` libera.

→ Step 2: [Core esatto e oracle](plan-phase00Step2PacRebalancerExactCore.prompt.md)
