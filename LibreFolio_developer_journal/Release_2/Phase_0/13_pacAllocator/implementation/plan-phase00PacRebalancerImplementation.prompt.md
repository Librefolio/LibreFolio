# PAC & Rebalancer — piano implementativo maestro

**Stato:** IN IMPLEMENTATION — G3/G5 OPEN.
**Baseline esecutiva:** `941834237696f32bbabfde62a08e070e4b23758e`.
**Branch di authoring:** `e-alfy-allocatore-pac`.
**Lane:** porta `6153`, data dir `/tmp/librefolio-r2-d`, venv condiviso
`LibreFolio-SAUMUTtc`.
**Autorizzazione prodotto:** ricevuta dal developer il 2026-09-16 dopo il
checkpoint planning `888f99a6c8641e063c979b4b315eb65367de7e4a`.
**Dependency checkpoint:** `941834237696f32bbabfde62a08e070e4b23758e`
(`build(deps): add PySCIPOpt solver`).

← Design: [PAC & Rebalancer target](../plan-phase00PacRebalancerTargetDesign.prompt.md)

Subpiani:

1. [Contratti e capacità](plan-phase00Step1PacRebalancerContractsCapacity.prompt.md)
   - [Round 1 — capacità piattaforma Tool](plan-phase00Step1Round1-ToolPlatformCapacity.prompt.md)
2. [Core esatto e oracle](plan-phase00Step2PacRebalancerExactCore.prompt.md)
3. [Solver e policy](plan-phase00Step3PacRebalancerSolverPolicies.prompt.md)
4. [Copie dominio](plan-phase00Step4PacRebalancerDomainCopies.prompt.md)
5. [Frontend e review umana](plan-phase00Step5PacRebalancerFrontendReview.prompt.md)
6. [Integrazione, test e docs](plan-phase00Step6PacRebalancerIntegrationTestsDocs.prompt.md)

---

## 0. Registro esecutivo e Fleet

### 0.1 Gate aperti

- G0 ✅ bundle planning checkpointato.
- G1 ✅ autorizzazione developer esplicita ricevuta.
- G4 ✅ dependency checkpoint verificato dal coordinator.
- G2 ✅ handshake C/D congelato. Diagnostics preserva il contratto piattaforma:
  utente attivo autenticato, payload strutturale/sanitizzato, nessuno scenario
  o valore personale; anonimo `401`.
- G3/G5 ⏳ contract, witness e capacity non ancora congelati.

> **Decisione developer capacity 2026-09-16**: ritirato il candidate
> 16 Asset/4 Broker/32 route/4 valute come cap prodotto. G5 deve produrre una
> curva di crescita sul compiler reale e un envelope anti-abuso alto,
> resource-bound. Target: massimo circa `1 GB RSS` per singolo job; due worker
> possono raggiungere circa `2 GB`; `30 s` riservati al solver per item, con
> overhead end-to-end addizionale. Nessun nuovo probe lungo né cardinalità
> pubblica finché Group C non definisce deadline/memory policy piattaforma.

> **Note implementazione 2026-09-16**: baseline `941834237696f32bbabfde62a08e070e4b23758e`
> verificata pulita; porta `6153` libera. Il dependency checkpoint contiene
> PySCIPOpt `6.2.1`, SCIP `10.0.2`, NumPy `2.5.3`, SciPy `1.18.1` e highspy
> `1.15.1`. Smoke developer MIQCP: `x=3`, epigrafo quadratico `z=0`, status
> `optimal`, un thread e seed fisso.

### 0.2 Ownership attiva prima dei writer Fleet

| Owner | Workstream | Lease esclusiva | Dipende da | Runtime |
|---|---|---|---|---|
| `D-main/integration` | G2, capacity, integrazione | piani; `backend/app/services/tool_plugins/pac_allocator.py`; package export; generated client/API; Tool renderer registry; runner/catalogue; i18n; MkDocs nav/onboarding; `CHANGELOG.md` | coordinator per shared platform | unico owner lane `6153` quando concessa |
| `fleet-contract` | W0 contract/wire/witness | `backend/app/schemas/pac_allocator.py`; fixture wire PAC/Rebalancer dedicate | G2 decisions | nessun server |
| `fleet-exact-core` | W1 primitive/evaluator/oracle | `backend/app/services/pac_allocator/models.py`, `numeric.py`, `normalize.py`, `ledger.py`, `evaluator.py`, `oracle.py`, `issues.py` | contract interno congelato; solver non richiesto per prima slice | nessun runtime senza lease |
| `fleet-domain-copy` | W2 source copy | `backend/app/services/portfolio_allocation_source.py`; `backend/app/schemas/portfolio.py`; `backend/app/api/v1/portfolio_api.py` | G2 + audit auth/source + symbol alignment G3 | nessun runtime senza lease |
| `fleet-exact-input` | W3 exact input | `frontend/src/lib/utils/transactions/txPayloadHelpers.ts`; `frontend/src/lib/components/ui/input/ExactDecimalInput.svelte`; nuovo `ExactQuantityInput.svelte`; `frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte` | G1 + audit componenti | nessun runtime senza lease |
| `fleet-shell` | W4 shell fixture-driven | `frontend/src/lib/features/tools/pac-allocator/planner/**` | G3 + W3 | non avviato |
| `test-author` | test nuovi/riparati | file test assegnati, mai file produzione o runner | contract/impl disponibili | lane serializzata su grant |
| `docs-writer` | MkDocs EN | pagine MkDocs PAC/Rebalancer assegnate | G9 | nessun `mkdocs serve` |

Un owner non modifica lease altrui. `D-main/integration` è l'unico writer delle
superfici shared/generated per tutta l'esecuzione.

### 0.3 Checkpoint e ordine integrazione

1. `CP1`: contract/fixture/witness + dependency/capacity evidence; nessun
   generated/shared edit fuori da `D-main/integration`.
2. `CP2`: exact core/evaluator/oracle, dopo contract freeze.
3. `CP3`: domain copy + exact input + shell fixture-driven; domain e frontend
   restano merge semanticamente indipendenti.
4. `CP4`: solver/policy/proof, dopo CP2 + capacity freeze.
5. `CP5`: reporter/plugin/generated client, integrati dal writer unico.
6. `CP6`: PAC UI e Rebalancer UI; poi review umana, non E2E completi.

Ogni subagent parte con analisi e file map, poi riceve autorizzazione writer
soltanto sulla lease registrata. I comandi runtime non vengono parallelizzati.

> **⚠️ Fuori pista 2026-09-16**: il developer ha anticipato G4 prima della
> chiusura G2/G3. Il lock ha aggiornato NumPy `2.5.2 -> 2.5.3`; il piano lo
> accetta perché `numpy = "*"` e non richiede un lock delta minimale. Rischio
> condiviso basso ma non nullo: prima dei gate estesi eseguire selector numerici
> e portfolio esistenti.

> **Decisione coordinator G2 2026-09-16**: la precedente ipotesi diagnostics
> admin-only era stale. Il contratto storico e corrente di catalog/compute/
> diagnostics è authenticated-user; `ToolAboutPanel` usa il diagnostics
> sanitizzato. Nessuna modifica auth di produzione è richiesta.

> **Note implementazione Slice A 2026-09-16**: il numeric kernel additivo è
> completo e la review matematica indipendente non ha trovato blocker.
> Registrato `services pac-planner-core`: `83/83` test nuovi verdi; regressione
> P1 `services pac-analyze`: `97/97` verdi, lane `6153` serializzata.
> Chiarimenti documentation-only, format e rerun completati; checkpoint
> selettivo verificato dal coordinator:
> `22cb18d1d60c8b1197627e6e8eff9cb55f001d3e`. Nessun export package
> anticipato.

> **Note implementazione exact input 2026-09-16**: la slice production
> quattro-file è presente e FROZEN; test-author/component/E2E/format-check
> restano obbligatori prima del checkpoint. Precisione transazioni `12+6`,
> planner configurabile `12+12`; nessuna conversione quantità via `Number`.

## 1. Obiettivo

Sostituire il prototipo P1 analysis-only con due Tool operativi distinti:

- PAC Allocator;
- Portfolio Rebalancer.

I Tool condividono scenario normalizzato, primitive contabili, compiler,
adapter SCIP, evaluator esatto e report model. Restano distinti per input,
modalità, vincoli, azioni e presentazione.

L'implementazione deve:

1. funzionare anche con scenario interamente manuale;
2. offrire copie esplicite e indipendenti dai domini esistenti;
3. supportare nello stesso piano ordini `whole_quantity` e
   `monetary_amount`;
4. produrre primario fixed-L2 e variante BUY-only deployment-first;
5. pubblicare soltanto incumbent rigiocati esattamente;
6. rispettare limiti Tool, permessi, privacy e lifecycle;
7. ottenere approvazione umana UI prima degli E2E completi.

## 2. Non scope

- nessuna modifica FIFO/WAC o regime fiscale globale;
- nessuna modifica all'optimizer storico Riskfolio/SciPy;
- nessun routing automatico fra broker;
- nessuna persistenza di draft o piani;
- nessuna esecuzione ordini;
- nessuna API `/tools/prefill`;
- nessun calcolo finanziario nel frontend;
- nessun silent truncation, fallback solver o riduzione cardinalità;
- nessun uso di dati personali in fixture, log, screenshot o benchmark.

## 3. Stato reale di partenza

La baseline contiene:

- piattaforma Tool del gruppo C: base, registry, schema export, executor,
  route compute e diagnostics;
- schemi P1 in `backend/app/schemas/pac_allocator.py`;
- package P1 in `backend/app/services/pac_allocator/`;
- plugin P1 in `backend/app/services/tool_plugins/pac_allocator.py`;
- source copy in `backend/app/services/portfolio_allocation_source.py`;
- frontend P1 in `frontend/src/lib/features/tools/pac-allocator/`;
- renderer compilato in `frontend/src/lib/features/tools/registry.ts`;
- test/runner/docs P1;
- nessuna dipendenza PySCIPOpt nel `Pipfile`.

Il prototipo P1 non è un ramo legacy da mantenere. Le parti utili vengono
riusate o migrate; semantiche analysis-only e test che le congelano vengono
eliminate.

## 4. Invarianti matematici

```text
F_ref = V0 + K_reachable
T_a = w_a * F_ref
r_a = V_final_a - T_a
L2_fixed = sum_a r_a^2
F_final = sum_a V_final_a
U = F_ref - F_final
```

Pipeline normative:

| Prodotto | Primario |
|---|---|
| PAC `proportional` | `L2_fixed -> U -> route priority -> cost -> rows -> tie` |
| PAC `min_fragmentation` | `L2_fixed -> U -> split Assets -> rows -> route priority -> cost -> tie` |
| Rebalancer | `L2_fixed -> U -> turnover -> cost -> rows/splits -> tie` |

Variante per entrambi:

```text
freeze complete primary funding/transfers/FX/BUY/SELL
allow additional BUY only
U -> resulting L2_fixed -> incremental cost/rows -> tie
```

`ExactRatio` governa ranking/freeze/proof; `ROUND_HALF_UP` governa soltanto
posting monetari. Uno status floating SCIP non diventa automaticamente
`optimal_proven` o `infeasible_proven`.

## 5. Gate sequenziali

| Gate | Evidenza richiesta | Blocca |
|---|---|---|
| G0 Planning checkpoint | bundle linkato, diff-check, checksum, SHA pulito | ogni codice prodotto |
| G1 Product authorization | frase developer esplicita | tutti i workstream |
| G2 Tool handshake | versioni, codici, renderer, worker, limits, writer | schema/plugin/client |
| G3 Contract freeze | DTO, fixture, schema/codegen, MCP review, payload witness | core/shell/solver |
| G4 Dependency update | `Pipfile` + lock developer-owned | import/probe SCIP |
| G5 Capacity freeze | packaging, MIQP/MIQCP, scaling multi-asse, `1 GB/job`, `30 s solver`, RSS enforcement, cancel, dominio alto e finito | solver integration |
| G6 Exact-core checkpoint | evaluator/oracle indipendenti verdi | policy integration |
| G7 Solver checkpoint | fixed-L2/policy/proof/SELL verdi | Tool report |
| G8 Domain-copy checkpoint | auth/provenance/missing facts verdi | copy UI |
| G9 UI review | `APPROVED` separato PAC/Rebalancer | E2E completi |
| G10 Combined revision | test/lint/build/docs/capacity/review su una SHA | final handoff |

I gate non vengono compressi in un'unica approvazione.

## 6. DAG esecutivo

```text
G0 -> G1 -> G2

G2 -> contract freeze -> MCP review + payload witness
G2 -> domain-copy audit -> domain-copy implementation
G2 -> developer dependency update -> SCIP probe
G1 -> ExactQuantityInput extraction

MCP review + payload witness
  -> exact core -> exhaustive oracle
  -> shared planner shell

exact core + SCIP probe
  -> solver/policy engine

exact core + oracle + solver + payload witness
  -> reporter/plugin/generated client

domain copy + shared shell + generated client
  -> PAC UI
  -> Rebalancer UI

PAC UI + Rebalancer UI
  -> human review
      -> E2E via test-author
      -> docs/i18n/changelog
          -> combined gates -> independent reviews -> final handoff
```

## 7. Workstream e parallelismo

| Workstream | Parte dopo | Consegna | Modello agente |
|---|---|---|---|
| W0 contract/capacity | G2 | wire, witness, dependency/probe report | Astra per schema/capacity |
| W1 exact core | G3 | normalizer/evaluator/oracle | Astra per matematica |
| W2 domain copies | G2 | API/service auth-safe | agente backend delimitato |
| W3 exact input | G1 | componente condiviso + regressione | agente frontend delimitato |
| W4 shell UI | G3 + W3 | wizard/lifecycle/result primitives | agente frontend |
| W5 solver/policy | W1 + G5 | compiler/SCIP/proof/SELL | Astra |
| W6 integration | W1 + W5 | reporter/plugin/client/registry | singolo writer |
| W7 PAC UI | W2 + W4 + W6 | superficie PAC | agente frontend |
| W8 Rebalancer UI | W2 + W4 + W6 | superficie Rebalancer | agente frontend |
| W9 tests/docs | G9 | E2E, docs, i18n, changelog | test-author/docs-writer |

W1, W2, W3 e la shell fixture-driven possono procedere in parallelo dopo i
rispettivi gate. PAC e Rebalancer UI possono procedere in parallelo dopo W6.
I comandi runtime restano serializzati.

## 8. Ownership

### 8.1 File esclusivi per workstream

| Area | Percorsi previsti |
|---|---|
| Contract | `backend/app/schemas/pac_allocator.py`, fixture wire dedicate |
| Exact core | `backend/app/services/pac_allocator/models.py`, `numeric.py`, `normalize.py`, `evaluator.py`, nuovi `ledger.py`, `oracle.py` |
| Solver | nuovi `constraints.py`, `objectives.py`, `compiler.py`, `solver.py`, `proof.py`, `sell_verifier.py` |
| Domain copy | `backend/app/services/portfolio_allocation_source.py` e sole API dominio assegnate |
| Exact input | estensione `ExactDecimalInput` oppure nuovo `ExactQuantityInput` solo dopo audit; migrazione `TransactionFormModal` |
| Shell | `frontend/src/lib/features/tools/pac-allocator/planner/**` |
| PAC wrapper | `PacAllocatorTool.svelte` e directory `pac/**` |
| Rebalancer wrapper | `PortfolioRebalancerTool.svelte` e directory `rebalancer/**` |
| Tests | nuovi file assegnati per categoria; nessun doppio writer |

### 8.2 Superfici shared/generated: un solo writer

- `Pipfile`, `Pipfile.lock`;
- `backend/app/services/tool_plugins/pac_allocator.py`;
- export package `__init__.py`;
- API/schema/client generati;
- `frontend/src/lib/features/tools/registry.ts`;
- cataloghi i18n;
- test runner/catalogue;
- MkDocs nav;
- `CHANGELOG.md`.

Il writer integra contributi semantici altrui; non sostituisce il file con la
propria versione.

L'integration owner è anche l'unico runner-catalogue writer da CP1 in avanti,
anche se la restante integrazione W6 parte più tardi. I workstream chiedono la
registrazione dei propri path: non modificano direttamente il catalogue.

## 9. Runtime e dipendenze

Comando canonico futuro:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
pipenv run python dev.py test \
  --test-port 6153 \
  --data-dir /tmp/librefolio-r2-d \
  <categoria> <azione>
```

Regole:

- mai porta `6040` o `6041`;
- mai due comandi contemporanei nella lane;
- mai bare `./dev.py` in questo worktree coordinato;
- nessun `--force`;
- nessuna installazione da agente;
- update PySCIPOpt soltanto dal developer, con tutte le lane ferme;
- server terminato e `lsof` vuoto a ogni checkpoint.

## 10. Checkpoint

| Checkpoint | Delta |
|---|---|
| CP0 | bundle implementativo planning-only |
| CP1 | contract, fixture, MCP/payload, dependency e capacity evidence |
| CP2 | exact core + oracle |
| CP3 | domain copy + ExactQuantityInput + shell fixture-driven |
| CP4 | solver/policy/proof |
| CP5 | reporter/plugin/generated client |
| CP6 | PAC + Rebalancer candidate UI |
| CP7 | human-review fixes + approval record |
| CP8 | E2E/docs/i18n/changelog |
| CP9 | combined revision + final reviews |

Ogni checkpoint riporta baseline/target, file, evidenza, esclusioni, conflitti,
porta libera, commit proposto e stato `FROZEN`. Il coordinator effettua
staging e commit.

## 11. Selector pianificati

Nuove action:

```text
schemas pac-planner
services pac-planner-core
services pac-planner-oracle
services pac-planner-solver
services pac-planner-capacity
services portfolio-allocation-source
```

Action esistenti da ripuntare:

```text
api pac-tool
front-utility component-unit
front-utility pac-tool
front-utility rebalancer-tool
```

Il runner owner registra ogni path prima del primo selector. Una slice esegue
solo il selector minimo; le categorie integrate vengono eseguite a CP9.

## 12. Strategia review

- `test-author` scrive test backend/frontend quando la rispettiva slice viene
  implementata.
- Per la UI, prima della review umana sono ammessi unit/component/type/build e
  smoke tecnico, non gli E2E completi.
- Il developer approva PAC e Rebalancer separatamente su desktop/mobile.
- Solo dopo doppio `APPROVED`, `test-author` formalizza gli E2E.
- Un fix E2E che cambia comportamento o visuale riapre una review umana
  mirata.
- Review finali indipendenti: matematica/oracle, auth/privacy,
  resource/cleanup e code review.

## 13. Stop conditions

Fermarsi e informare il coordinator se:

- il baseline non coincide;
- manca una dipendenza prevista dal gate;
- wire, matematica o UX contraddicono i design;
- il payload non entra nei limiti senza degradazione prodotto;
- PySCIPOpt/SCIP non è packagable nel target;
- il candidate-max non rispetta il budget runtime;
- il solver produce un incumbent non rigiocabile esattamente;
- la copia dominio non può fallire chiuso;
- due workstream richiedono lo stesso file non assegnato;
- un test fallisce prima della collection o per infrastruttura.

Nessun fallback o compromesso viene applicato in silenzio.

## 14. Definition of Done

1. CP0 checkpointato e G1 autorizzato separatamente.
2. Handshake C/D congelato.
3. Wire strict, MCP-friendly, codegen-compatible e sotto cap.
4. PySCIPOpt/SCIP installato dal developer e verificato nei target.
5. Dominio supportato misurato e dichiarato.
6. Core/evaluator/oracle esatti e indipendenti dal solver.
7. Solver conforme a fixed-L2, policy, variante e proof semantics A.
8. SELL pubblicato soltanto dopo verifica controfattuale; fallback onesto.
9. Copie dominio read-only, complete e auth-safe.
10. Frontend senza calcoli economici o binding live.
11. UI PAC/Rebalancer approvata prima degli E2E completi.
12. Test, docs, i18n e changelog coerenti.
13. Gate finali verdi sulla stessa revisione.
14. Nessun artifact privato/runtime e porta `6153` libera.
15. Handoff `FROZEN` con commit proposto, senza staging/history dal workstream.

→ Step 1: [Contratti e capacità](plan-phase00Step1PacRebalancerContractsCapacity.prompt.md)
