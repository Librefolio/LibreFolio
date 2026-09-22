# Step 3 — compiler dichiarativo, SCIP, policy e proof

**Stato:** ANALISI CONSEGNATA 2026-09-18 (nessun codice) — exact core (Step 1
contratto/Step 2 evaluator) risulta soddisfatto; resta bloccante solo G5
capacity/runtime. Vedi §16.
**Dipende da:** Step 1 capacity freeze, Step 2 evaluator.

← Master: [piano implementativo](plan-phase00PacRebalancerImplementation.prompt.md)
← Precedente: [core esatto e oracle](plan-phase00Step2PacRebalancerExactCore.prompt.md)
← Autorità: [policy](../plan-phase00PacRebalancerPolicies.prompt.md) ·
[nucleo matematico](../plan-phase00PacRebalancerMathematicalCore.prompt.md)

## 1. Scopo

Implementare una sola famiglia solver-backed fixed-reference/fixed-L2 per PAC
e Rebalancer, con policy distinte compilate da dati dichiarativi.

Il solver cerca. L'evaluator esatto valida e ordina. Il reporter spiega.

## 2. Ownership

Nuovi moduli previsti:

```text
backend/app/services/pac_allocator/constraints.py
backend/app/services/pac_allocator/objectives.py
backend/app/services/pac_allocator/compiler.py
backend/app/services/pac_allocator/solver.py
backend/app/services/pac_allocator/proof.py
backend/app/services/pac_allocator/sell_verifier.py
```

Test previsti:

```text
backend/test_scripts/test_services/test_pac_planner_policies.py
backend/test_scripts/test_services/test_pac_planner_solver.py
backend/test_scripts/test_services/test_pac_planner_sell.py
```

Il solver owner non modifica plugin, route, generated client o frontend.

## 3. Programma dichiarativo

```text
PolicyProgram
├── enabled_variables
├── finite_bounds
├── hard_constraints[]
├── primary_stages[]
├── deployment_stages[]
├── canonical_tie
└── proof_eligibility
```

Primitive riusabili:

- funding balance/cap;
- FX pair/debit-credit/activation;
- BUY/SELL quantum e activation;
- route min/cap;
- holding conservation;
- Broker×currency ledger;
- Asset nonnegativity;
- no BUY+SELL Asset;
- fee/tax/buffer;
- fixed primary actions;
- added BUY only;
- turnover;
- rows/splits;
- stable ID tie.

Ogni `ConstraintSpec` ha:

- ID e issue code;
- coefficienti/unità;
- builder SCIP;
- verifier evaluator;
- explanation key.

## 4. Variabili e bound

```text
t[source, broker, currency]  integer minor-unit funding
f[fx_route]                  integer source minor-unit debit
x_buy[order_route]           integer quantum
x_sell[order_route]          integer quantum
y_buy/y_sell                 binary activation
```

Bound derivati soltanto da:

- saldo/cap funding;
- inventario;
- prezzo e quote basis;
- step ordine;
- cap/minimo;
- route/permission;
- FX balance.

Nessun Big-M arbitrario. Un envelope non rappresentabile in modo sicuro è
`unsupported`.

## 5. Stage lessicografici

`argmin_lex` significa solve sequenziale:

1. ottimizzare stage;
2. estrarre incumbent;
3. replay evaluator exact;
4. registrare best exact e bound solver;
5. aggiungere bound non peggiorativo;
6. passare allo stage seguente.

Mai:

- weighted scalar;
- epsilon economico nascosto;
- confronto su valore formattato;
- uguaglianza quadratica non convessa.

Il primo stage:

```text
minimize sum_a (V_final[a] - target[a])^2
```

è MIQP convesso. Il sublevel `L2 <= ceiling` per i tier successivi è MIQCP
convesso. Se il ceiling deriva da incumbent non provato, non rappresenta una
faccia ottima provata.

## 6. Matrice policy

| Policy | Variabili | Constraint specifici | Primario |
|---|---|---|---|
| PAC `proportional` | funding/FX/BUY | SELL off | `L2 -> U -> route priority -> cost -> rows -> tie` |
| PAC `min_fragmentation` | funding/FX/BUY | SELL off | `L2 -> U -> split Assets -> rows -> route priority -> cost -> tie` |
| Rebalancer `invest_only` | funding/FX/BUY | SELL off; `V0 > 0`; `F_final > 0` | `L2 -> U -> turnover -> cost -> rows/splits -> tie` |
| Rebalancer `invest_and_sell` | baseline frozen + restricted SELL + incremental BUY | anti-liquidation; `V0 > 0`; `F_final > 0` | `L2 -> U -> turnover -> cost -> rows/splits -> tie` |

Le policy condividono compiler e primitive; non diventano un unico prodotto.

## 7. Rebalancer `invest_and_sell`

1. risolvere `invest_only`;
2. congelare funding, FX e BUY baseline;
3. abilitare SELL soltanto su Asset baseline-overweight;
4. vietare SELL su Asset con BUY congelato;
5. il netto SELL finanzia soltanto BUY incrementali;
6. vietare sale-to-idle-cash;
7. imporre holding/value finali non negativi;
8. verificare ogni SELL pubblicato.

`SellIrreducibilityVerifier`:

- rimuove un quantum;
- rimuove l'intera riga;
- ricalcola fee, tax, ledger, FX e fonti alternative;
- mantiene identico il vettore BUY incrementale;
- massimo due controfattuali per riga SELL.

Se la verifica non si chiude esattamente, non pubblicare il candidato SELL:
restituire l'ultimo incumbent verificato, almeno `invest_only`, con proof
onesta e issue `SELL_IRREDUCIBILITY_UNRESOLVED`. Non chiamare la proprietà
locale “minimalità globale”.

## 8. Variante margine

Congelare:

- funding;
- trasferimenti;
- FX;
- SELL;
- BUY primari;
- quantità e attivazioni delle righe primarie.

Abilitare soltanto BUY addizionali finanziabili dai saldi risultanti. Le righe
primarie restano attive e immutate; sono ammesse nuove attivazioni BUY su route
già dichiarate, mai nuove fonti, FX o SELL.

Pipeline:

```text
min U
then min resulting L2_fixed
then min incremental cost
then min incremental rows
then canonical tie
```

Il delta `L2_fixed` è visibile. Lo stage L2 dopo deployment sceglie il minor
danno target sulla faccia di massimo investimento.

Se la variante domina il `L2_fixed` di un primario non provato:

- promuovere a nuova incumbent primaria e riavviare la cascata; oppure
- omettere la variante se il budget non consente una coppia coerente.

Mai etichettarla semplicemente variante di una base dominata.

## 9. Proof semantics A

Pipeline candidatura:

```text
SCIP candidate
  -> exact Decimal/ExactRatio replay
      -> invalid: discard
      -> valid: publishable incumbent
```

`optimal_proven` soltanto con:

- exhaustive oracle; oppure
- `score_lattice_closure` coefficient-safe per tutti i tier.

`infeasible_proven` soltanto con:

- deterministic exact conflict; oppure
- oracle completo.

SCIP floating:

- `optimal` → al massimo `gap_bounded`/`not_proven`;
- `infeasible` → `no_incumbent/not_proven`;
- time/node limit con incumbent → `incumbent_found`;
- time/node limit senza incumbent → `no_incumbent`.

Proof, outcome e stop reason restano assi distinti.

## 10. `score_lattice_closure`

Per ogni stage:

1. derivare lattice esatto dai coefficienti razionali e domini interi;
2. trasformare bound floating in intervallo conservativo;
3. dimostrare che nessun valore lattice migliore entra nell'intervallo;
4. congelare soltanto se la dimostrazione copre quello stage;
5. ripetere per tutti i tier.

Non derivare closure dalla sola feasibility tolerance MIQP. Se scaling,
overflow o coefficiente rendono la prova incerta, proof resta `not_proven`.

## 11. Adapter SCIP

Responsabilità:

- lifecycle modello per request;
- coefficient scaling sicuro;
- objective replacement per stage;
- bound/gap/node/time capture;
- deterministic seed/thread policy;
- checkpoint tra build/stage/replay/counterfactual;
- cancellation cooperativa;
- cleanup in success/error/timeout/cancel;
- nessun global mutable model;
- nessun fallback SciPy/HiGHS.

Il budget interno riserva tempo per:

- replay;
- variante;
- SELL counterfactual;
- report serialization/revalidation.

## 12. Test e oracle

Confrontare solver vs oracle su tutto il corpus piccolo:

- stessa feasibility;
- stessa tupla lessicografica;
- stesso tie-break;
- stessa variante;
- stesse policy a input normalizzati equivalenti.

Test ulteriori:

- permutation invariance;
- whole/monetary misti;
- fee activation;
- FX coupled;
- tax reserve;
- no-op;
- infeasible exact;
- limit con/senza incumbent;
- promotion/restart;
- SELL quantum/whole-row;
- cancel a ogni checkpoint;
- cleanup ripetuto.

Selector:

```text
services pac-planner-solver
services pac-planner-capacity
```

## 13. Sequenza

- [ ] 1. Definire `ConstraintSpec` e `ObjectiveStage`.
- [ ] 2. Compilare variabili/bound comuni.
- [ ] 3. Implementare MIQP `L2_fixed`.
- [ ] 4. Implementare cascade MIQCP e tie.
- [ ] 5. Implementare PAC `proportional`.
- [ ] 6. Implementare PAC `min_fragmentation`.
- [ ] 7. Implementare Rebalancer `invest_only`.
- [ ] 8. Implementare estensione `invest_and_sell`.
- [ ] 9. Implementare variante BUY-only e promotion.
- [ ] 10. Implementare proof mapping e lattice closure.
- [ ] 11. Implementare SELL verifier.
- [ ] 12. Implementare cancel/cleanup.
- [ ] 13. Confrontare oracle e benchmark capacity.
      **Due numeri di produzione dipendono da questo lavoro e vanno rimisurati qui**
      (aggiunti il 2026-09-21, con il budget engine propagato):
      - `_POST_ENGINE_RESERVE_MS = 2_000` in `tool_plugins/pac_allocator.py` — la
        riserva post-solver per replay esatto e report. Misurata **~1 ms** sugli
        scenari di test attuali, ma cresce col dominio mentre la quota del solver
        no: il valore è dimensionato per uno scenario più grande di quanto oggi
        si sappia costruire, cioè è una stima in attesa di questo benchmark.
      - `limits/nodes` — **mai passato in produzione**. È la sola manopola di
        troncamento deterministica (`limits/dettime` non esiste in SCIP 10.0,
        sondato), quindi il valore va scelto qui e non prima. Finché resta
        assente, `stop_reason: "node_limit"` (`schemas/pac_allocator.py:2406,2469`,
        prodotto da `planner_report.py:848`) è un valore di contratto dichiarato e
        **non producibile**.
      > Sono elencati qui, e non solo nei rispettivi commenti, perché un commento
      > esatto invecchia senza farsi notare: `DEFAULT_SOLVER_TIME_BUDGET_SECONDS`
      > ha documentato fedelmente per cinque giorni una probe tarata su un
      > envelope che non esisteva più. Chi eseguirà questo punto deve trovare la
      > lista, non ricostruirla.
- [ ] 14. Review matematica e resource lifecycle.

## 14. Stop conditions

- solver richiesto ma dependency/capacity gate non chiuso;
- coefficiente non scalabile in sicurezza;
- bound infinito;
- stage successivo peggiora il precedente exact;
- candidate non rigiocabile;
- status pubblico dipende solo dallo status SCIP;
- controfattuale SELL supera budget senza fallback sicuro;
- candidate-max viola runtime o memoria.

## 15. Definition of Done

- compiler dichiara tutte le differenze di policy;
- fixed-L2/variant corrispondono ai design;
- solver e evaluator separati;
- oracle equality sul dominio piccolo;
- proof semantics A rispettata;
- SELL verifier chiude o degrada onestamente;
- cancellation e cleanup verificati;
- capacity gate verde;
- CP4 pronto e porta libera.

## 16. Analisi di readiness (coordinatore, 2026-09-18) — solo analisi, nessun codice

Autorizzata dal coordinatore come analisi pura (5 punti richiesti). Nessun
file di servizio toccato in questo round; unico file scritto è questo piano.
Fonti primarie: `models.py` (letto integrale, 1629 righe), `numeric.py`
(integrale, 398 righe), `evaluator.py`/`normalize.py` (mappa strutturale
completa + lettura mirata dei punti di ingresso), `schemas/pac_allocator.py`
(sezioni richieste/risultato/proof/witness/solver-evidence lette integrali),
`tools/base.py` e `tool_plugins/pac_allocator.py` (integrali), Mathematical
Core §1-4/17-22, Policies §5 (matrice), Step1 §10.1-10.5 (probe capacity
reali già eseguiti — dati sperimentali, non ipotesi).

### 16.1 Stato reale — cosa manca esattamente

- `normalize.py:1919,1926` (`normalize_pac_plan`/`normalize_rebalancer_plan`)
  producono solo `PlannerV2NormalizationResult{availability, issues,
  normalized: ExactPlannerScenario | None}` — nessuna nozione di policy o
  spazio-decisione qui.
- `evaluator.py:3368` (`build_exact_policy_view`) trasforma
  scenario+policy+purpose in `ExactPolicyView`: decisioni/vincoli/obiettivi/
  tie-break/SELL-gate/proof-requirement sono già **riferimenti normalizzati**
  (code/phase/scope/entity_refs/unit/enforcement/bound_source/
  explanation_key), non ancora coefficienti SCIP.
  `evaluator.py:3719` (`evaluate_exact_candidate`) trasforma un
  `CandidateActionVector` (solo `decision_id -> quanta`, `models.py`
  righe ~1041-1104) in `ExactEvaluation` completo (ledger/conflitti/
  obiettivi Decimal). Questi due estremi esistono e sono committati.
- **Manca interamente l'anello centrale**: zero file fra
  `constraints.py/objectives.py/compiler.py/solver.py/proof.py/
  sell_verifier.py`; zero classi `Oracle`/funzioni `oracle` in tutto
  `pac_allocator/` (grep negativo). `tool_plugins/pac_allocator.py:27-111`
  registra **solo** `operation="analyze"` (`_ANALYZE_POLICY` a riga 27,
  classe `PacAllocatorTool` a riga 43, `job_timeout_ms=5000`);
  `operation="plan"` non è mai stato dichiarato come
  `ToolService` — gap già segnalato dal coordinatore nel round W3 (api sync,
  handshake C).
- Il **contratto di uscita per `operation="plan"` è già completamente
  congelato** in `schemas/pac_allocator.py` (W0, non toccare): richieste
  (`_PlannerRequestBase`/`PacPlannerRequest`/`RebalancerInvestOnlyRequest`/
  `RebalancerInvestAndSellRequest`, righe 1088-1132), risultati `ready_*`
  (`_PacReadyResultBase`/`_RebalancerReadyResultBase`, righe 2760-2882;
  4 combinazioni `result_state`/`outcome`: `ready_no_op`/`no_op`,
  `ready_incumbent`/`incumbent_found`, `ready_infeasible`/
  `infeasible_proven`, `ready_no_incumbent`/`no_incumbent`), soluzioni
  (`PacPlanSolution`/`RebalancerPlanSolution` e sottoclassi `NoOp`/
  `Incumbent`/`Deployment`, righe 2111-2260), prove (`OptimalProvenProof`/
  `GapBoundedProof`/`NotProvenProof`/`InfeasibilityProvenProof`, righe
  1578-1659), witness (`ExhaustiveOracleWitness`/`ScoreLatticeClosureWitness`/
  `DeterministicConflictWitness`, righe 1461-1577) e solver evidence
  (`SolverNotRunEvidence`/`ReportedFloatingSolverEvidence`/
  `SolverStageEvidence`, righe 1447-1577). **Step3 non progetta un nuovo
  contratto: lo popola.**
- 6 fixture v2 esistono (`pac_plan_request/result.min.v2.json`,
  `...candidate-max.v2.json`, `rebalancer_plan_request/result.medium.v2.json`)
  ma sono fixture di validazione schema scritte a mano (W0), non fixture
  solver-verificate. Zero `test_pac_planner_solver*.py`/`*_policies*.py`/
  `*_sell*.py`/`*_oracle*.py` esistono (confermato via `find`).
- G4 (dipendenze SCIP) chiuso — PySCIPOpt 6.2.1/SCIP 10.2.2, smoke MIQCP
  optimal (nota `plan-phase00PacRebalancerImplementation.prompt.md`,
  2026-09-16). **G5 (capacity/runtime) resta esplicitamente aperto** — §16.4.

### 16.2 Mapping esatto verso SCIP (con riuso `numeric.py`)

Pipeline end-to-end (i tratti `[...]` sono il gap Step3; il resto esiste già
ed è committato):

```text
wire PacPlannerRequest/RebalancerXRequest (schemas, congelato)
  -> normalize_pac_plan / normalize_rebalancer_plan   (normalize.py:1919,1926)
  -> ExactPlannerScenario                              (models.py)
  -> build_exact_policy_view(scenario, policy, purpose) (evaluator.py:3368)
  -> ExactPolicyView (decisions/constraints/objectives/tie_breaks/
     sell_gates/proof_requirements — metadata, non coefficienti)
  [-> compiler.py: ExactPolicyView + ExactPlannerScenario -> modello SCIP]
  [-> solver.py: argmin_lex per stage, SCIP timelimit/nodelimit nativi]
  -> CandidateActionVector (decision_id -> quanta, intero)
  -> evaluate_exact_candidate(scenario, view, candidate, checkpoint)
     (evaluator.py:3719) -> ExactEvaluation (Decimal/ExactRatio, mai float)
  [-> proof.py: solver stage evidence + oracle/lattice -> ReadyPlanProof /
     InfeasibilityProvenProof]
  [-> sell_verifier.py: solo invest_and_sell -> SellIrreducibilityEvidence]
  -> PacPlanSolution/RebalancerPlanSolution + Ready*Result (schemas, congelato)
  [-> tool_plugins/pac_allocator.py: nuovo ToolService operation="plan"]
```

Mapping `DecisionAccess` (`models.py`) -> variabile SCIP: `family`
(`t/f/x_buy/x_sell/y_buy/y_sell`) determina il tipo (continua/intera/
binaria); `lower_quanta`/`upper_quanta` sono già bound pronti all'uso;
`mode` (`disabled/frozen_exact/additive_only/...`) determina se la
variabile va fissata (`lb=ub=frozen_quanta`), esclusa (`disabled`) o
lasciata libera nei bound — **non serve ri-derivare i bound da zero**, sono
già normalizzati in W1.

Mapping `ConstraintRef`/`ObjectiveRef` -> vincolo/obiettivo SCIP: sono
**solo metadata** (code/scope/entity_refs/unit/enforcement/bound_source).
Il compiler deve ricostruire i coefficienti reali a partire dai dati grezzi
di `ExactPlannerScenario`, seguendo **la stessa tassonomia già stabilita**
dalle funzioni dichiarative gemelle già in `evaluator.py`:
`_funding_constraint_refs` (1159), `_fx_constraint_refs` (1253),
`_order_constraint_refs` (1328), `_position_constraint_refs` (1438),
`_global_constraint_refs` (1532) — queste enumerano già QUALI vincoli
esistono e in che ordine; il compiler deve produrre l'espressione SCIP
1:1 corrispondente, così che ciò che il solver ottimizza e ciò che
l'evaluator poi rivalida non possano divergere per costruzione.

Catalogo `ObjectiveCode` (schema, riga ~1409) —
`fixed_l2/shortfall/turnover/explicit_cost/incremental_cost/
split_asset_count/active_order_rows/incremental_order_rows/route_priority`
— combacia 1:1 con la matrice lessicografica già pubblicata in Policies §5:
`L2_fixed=fixed_l2`, `U=shortfall`, `route priority=route_priority`,
`cost=explicit_cost` (`incremental_cost` in fase 2 `invest_and_sell`),
`rows=active_order_rows` (`incremental_order_rows` in fase 2), `split
Assets=split_asset_count`, `turnover=turnover`, tie-break canonico già
implementato (`_canonical_tie_decision_ids`/`_canonical_tie_breaks`,
evaluator.py 3194/3267).

**Formulazione raccomandata (non naive)**: il probe capacity già eseguito
(Step1 §10.1, 2026-09-16) mostra che un **singolo epigrafo quadratico
globale** stalla in `timelimit` a 16 Asset/32 route sia a 4s sia a 5s,
mentre **epigrafi quadratici separabili per Asset + warm-start
deterministico + route non simmetriche + at-most-one-route** chiudono
floating `optimal` a un nodo, gap `0`: 8/16 route `31.19ms`, 16/32
`55.31ms`, 32/64 `51.94ms`. Il compiler deve partire direttamente da questa
seconda formulazione, non dalla prima (già misurata inadeguata).

Confine solver/evaluator (Mathematical Core §3-4, invariato): il solver
propone quanta interi; solo un replay `evaluate_exact_candidate` in
Decimal/`ExactRatio` può promuovere un candidato a incumbent pubblicabile.
Questo confine non è nuovo — va solo rispettato meccanicamente in
`solver.py`/`proof.py`.

### 16.3 Dove si innesta proof/oracle (e dove resta separato)

- Le 3 dimensioni indipendenti restano quelle di Proof Semantics A:
  validazione incumbent (`decimal_verified`), evidenza solver (status/bound/
  gap floating, mai promossa da sola), prova (conclusione matematica sul
  dominio discreto).
- `SolverNotRunEvidence(reason=allocation.solver_not_required)` copre i casi
  **degeneri rilevabili prima di invocare SCIP**: `evaluator.py` ha già i
  rilevatori (`_require_feasible_invest_only_baseline`,
  `_validate_policy_purpose`, righe 3031-3355) per scenari senza funding
  selezionato o senza route raggiungibile — questi possono risolversi in
  `ready_no_op` senza mai costruire un modello SCIP.
- `oracle.py` (non esiste) serve `optimal_proven`/`infeasible_proven` via
  `exhaustive_oracle` su domini piccoli dichiarati (Mathematical Core §20,
  15 casi minimi). È **indipendente da `solver.py`**: stesso evaluator
  Decimal, enumerazione brute-force, non riusa la ricerca di produzione.
  Va costruito per primo o in parallelo — è più semplice di `solver.py` e
  dà da subito la prova più forte su fixture piccole.
- `score_lattice_closure` (Mathematical Core §22, algoritmo a 7 passi) è la
  tecnica più difficile — va costruita per ultima, dopo che `solver.py` e
  `oracle.py` sono entrambi solidi e incrociati sul corpus piccolo.
- Vincolo strutturale non negoziabile: lo status floating SCIP
  (`optimal`/`infeasible`) **non è mai promosso da solo** a `*_proven`; solo
  un witness oracle o lattice-closure lo fa. Questo va imposto in
  `proof.py`, non lasciato alla disciplina del chiamante.

### 16.4 Superfici file, ownership, test, dipendenze, rischi

Elenco moduli §2 confermato **con un'eccezione da chiarire**: §2 dichiara
"il solver owner non modifica plugin, route, generated client o frontend",
ma *qualcuno* deve registrare `operation="plan"` come `ToolService` in
`tool_plugins/pac_allocator.py`. Proposta (rispecchia esattamente lo split
P1 già esistente fra `analyze_pac_budget`/`analyze_rebalancing`
(importati in `tool_plugins/pac_allocator.py:17`) e il loro dispacciamento
nel `compute()` del plugin (`tool_plugins/pac_allocator.py:92-111`, chiamate
alle righe 99/107): il solver owner consegna solo due
nuove funzioni di servizio (`plan_pac_allocation`/`plan_rebalancing`,
stessa forma di `analyze_pac_budget(parameters, checkpoint=...)`);
D-main/integration (lease Fleet esistente sul Tool plugin) cabla la
`ToolService`/`ToolOperationPolicy` — nessuna modifica al confine di
ownership, solo conferma che si applica invariato anche qui.

Test (test-author, come da §2 + un'aggiunta):
`test_pac_planner_policies.py`/`test_pac_planner_solver.py`/
`test_pac_planner_sell.py` (già previsti) **più**
`test_pac_planner_oracle.py` (non elencato in §2 — `oracle.py` è un modulo
nuovo senza file di test dedicato nell'elenco originale).

Dipendenze: nessuna nuova — PySCIPOpt/SCIP già vendorizzate e smoke-testate
(G4 chiuso).

Rischi, tutti ancorati a dati di probe reali già raccolti (Step1 §10.1-10.5,
2026-09-16), non a ipotesi:

1. **Cancellation**: il probe ha trovato che `interruptSolve()` chiamato da
   un thread Python **non ha preemptato** `optimize()` prima del limite —
   il pattern cooperativo `Checkpoint = Callable[[], None]` (`check_budget`,
   usato ovunque nel resto del codice) non è sufficiente per SCIP stesso.
   Il guardiano primario deve essere il `timelimit`/`nodelimit` nativo di
   SCIP; il vero cancel duro resta il confine di processo posseduto dal
   Tool executor (SIGTERM, già misurato `1.48ms` per rilascio PID). Questo
   va progettato esplicitamente in `solver.py` (§11 adapter), non assunto
   funzionante via `check_budget()`.
2. **Margine tempo**: un item a budget solver 4s produce un wall reale di
   `~4.05-4.08s` — troppo stretto contro un hard deadline 5s una volta
   aggiunti serialize/replay/report/cleanup; a 3.5s il margine osservato
   sale a `~1.44s`. Questo vincola direttamente la futura
   `ToolOperationPolicy` di `operation="plan"`: serve un envelope
   `engine_timeout_ms`/`soft_timeout_ms`/`job_timeout_ms` sensibilmente più
   ampio dei 4000/4000/5000 attuali di `_ANALYZE_POLICY`, rispettando pur
   sempre il validator `ordered_deadlines` (`schemas/tools.py:136-146`).
3. **G5 resta esplicitamente aperto** e, per la scelta developer del
   2026-09-16 (Step1 §10.5), la sua chiusura richiede di campionare un
   compiler **rappresentativo** su 7 assi (Asset canonici, route/Asset e
   totali, Broker, valute/casse, route FX, buy-only vs invest-and-sell,
   densità fee/limiti/attivazioni) — cioè **G5 non può chiudersi prima che
   un compiler reale esista da campionare**. Non è un blocco all'avvio di
   Step3: la campagna di campionamento G5 è essa stessa parte del
   deliverable Step3 (il primo compiler rappresentativo È il soggetto di
   misura). La fetta minima (§16.5) va perciò tenuta deliberatamente
   piccola (Asset/Broker/valute a una cifra) per restare dentro qualunque
   envelope plausibile, mentre la campagna di campionamento vera e propria
   segue a ridosso.
4. `NotProvenReasonCode` (schema, riga 696) ha oggi solo 2 valori
   (`allocation.exact_proof_not_established` generico +
   `portfolio_rebalancer.sell_irreducibility_unresolved`). Fase 1 può
   riusare il codice generico per ogni esito non provato (time_limit/
   node_limit/dominio troppo grande per l'oracle collassano sullo stesso
   codice wire) senza toccare lo schema (lease `fleet-contract`); si
   raccomanda di rimandare una granularità più fine finché la telemetria
   solver non mostra un bisogno reale — non un blocco, solo segnalato
   perché tocca un file non di mia proprietà.

### 16.5 Fetta minima end-to-end (fase 1 onesta)

Perimetro proposto: PAC `proportional` **soltanto** (niente SELL, niente
cascata baseline, niente variante margine), scenari a una cifra di
Asset/Broker/route, valuta singola o multi-valuta con `fx_rates` espliciti.

Ordine di costruzione dentro la fase 1:

1. `oracle.py` — enumeratore esaustivo, riusa `evaluate_exact_candidate`
   così com'è, **zero dipendenza SCIP**. Dà da subito `optimal_proven`/
   `infeasible_proven` onesti su fixture giocattolo, prima ancora che il
   solver esista.
2. `constraints.py`/`objectives.py`/`compiler.py` — a partire
   **direttamente** dalla formulazione a epigrafi separabili già validata
   dal probe (non quella singola globale, già misurata inadeguata).
3. `solver.py` — adapter per lo stage `fixed_l2` e la cascata
   `L2 -> U -> route_priority -> cost -> rows -> tie` della sola policy
   `proportional`; guardiano primario = `timelimit`/`nodelimit` nativi
   SCIP (non `check_budget()` da solo, vedi rischio 1).
4. `proof.py` — non promuove mai lo status floating da solo: sotto la
   soglia dominio-piccolo incrocia con `oracle.py`
   (`optimal_proven`/`infeasible_proven`); altrimenti riporta onestamente
   `incumbent_found`/`not_proven`, o `gap_bounded` solo se un bound duale
   sicuro è derivabile.
5. Una singola funzione di orchestrazione nuova
   (`plan_pac_allocation(request, checkpoint)`, stessa forma di
   `analyze_pac_budget`) che lega normalize -> `build_exact_policy_view`
   -> oracle-o-solver -> replay `evaluate_exact_candidate` -> `proof.py`
   -> tipo wire `Ready*Result`.

Esplicitamente **fuori** dalla fase 1: `min_fragmentation`, `invest_only`,
`invest_and_sell` (+ SELL verifier), variante margine,
`score_lattice_closure`, cablaggio Tool (lease D-main/integration), la
campagna G5 sulle altre 6 dimensioni oltre alla scala giocattolo.

DoD di fase 1 (più stretto della DoD generale §15): il compiler produce un
modello SCIP valido per uno scenario PAC `proportional`; il solver produce
un candidato; il replay `evaluate_exact_candidate` è **sempre** invocato
(mai fidarsi dell'output floating direttamente); il risultato è sempre uno
fra `{ready_incumbent/incumbent_found+not_proven,
ready_incumbent/incumbent_found+optimal_proven (solo se l'oracle lo
conferma), ready_no_op/no_op, ready_infeasible/infeasible_proven (solo via
oracle o deterministic_conflict), ready_no_incumbent/no_incumbent}`; mai
`gap_bounded`/`optimal_proven` senza un witness genuino; cancellation via
limiti nativi SCIP + confine di processo Tool esistente; nuovi file di
test (almeno `test_pac_planner_oracle.py`) verdi sotto test-author.

### 16.6 Proposta di sequenza raffinata (integra §13, non la sostituisce)

| Passo §13 | Raffinamento fase 1 |
|---|---|
| 1-2 | invariati |
| 3 | solo `fixed_l2` per `proportional`, formulazione a epigrafi separabili |
| *nuovo 2.5* | `oracle.py` prima del compiler (indipendente, riusa evaluator) |
| 4 | cascata MIQCP solo per la pipeline `proportional` |
| 5 | come da §13 |
| 6-9 | rimandati esplicitamente a fase 2+ |
| 10 | split: solo la metà "oracle-witness/not-proven" in fase 1; `score_lattice_closure` rimandata |
| 11 | guardiano primario = limiti nativi SCIP, non `check_budget()` da solo |
| 12-14 | invariati, applicati al perimetro fase 1 |

### 16.7 Domande aperte per il coordinatore (motivate, non decisioni nuove)

1. Conferma ownership registrazione Tool (§16.4): solver owner consegna solo
   `plan_pac_allocation`/`plan_rebalancing`; D-main/integration cabla
   `ToolService`/`ToolOperationPolicy`, come già per P1. Confermare o
   redirigere.
2. Granularità `NotProvenReasonCode` (§16.4 punto 4): riuso del codice
   generico per tutta la fase 1, nessuna modifica schema. Confermare o
   redirigere.
3. Il limite dominio-piccolo dell'oracle deve restare una costante interna
   di sicurezza (mai esposta), o serve un issue code dedicato quando uno
   scenario è troppo grande per l'oracle ma il solver gira comunque?
   Raccomandazione: costante interna, nessun issue code dedicato in fase 1
   (l'esito resta semplicemente `not_proven`) — segnalato perché è un
   comportamento nuovo osservabile, non solo tecnico.

### 16.8 Stage 1 — `oracle.py` ✅ completato 2026-09-18

> **Note implementazione**: creato `backend/app/services/pac_allocator/oracle.py`
> (nuovo, ~200 righe, zero dipendenza SCIP) esattamente per §16.5 punto 1:
> enumeratore esaustivo su `view.decisions` (range pieno per
> `mutable`/`additive_only`, punto singolo fisso per `disabled`/
> `frozen_exact`), replay obbligato via `evaluate_exact_candidate` (mai
> ri-derivazione), selezione lessicografica per stage di `view.objectives`
> ordinati per `ordinal` ascendente + `canonical_tie_quanta` come tie-break
> finale. API pubblica: `MAX_EXHAUSTIVE_ORACLE_CANDIDATES` (200_000, costante
> interna di sicurezza per la domanda aperta §16.7.3), `OracleDomainTooLargeError`,
> `OracleResult`, `estimate_oracle_domain_size()`, `run_exhaustive_oracle()`.
> Test-author ha creato `backend/test_scripts/test_services/test_pac_planner_oracle.py`
> (20 test) + registrazione `pac-planner-oracle` in
> `scripts/test_runner/_backend_services.py` (mirror esatto di
> `pac-planner-evaluator`). Copertura: equivalenza esaustiva via scansione
> lessicografica indipendente (non circolare, non riusa `_lexicographic_key`),
> ordine `objective_codes` per view generica + cascata `proportional` hardcoded
> come contratto di prodotto, composizione multi-decisione
> (funding_transfer+fx_debit+buy_quantum) con quantum grossolano deliberato,
> confine dominio-troppo-grande (rifiuto rapido, boundary esatto),
> no-op, caso infeasible-esaustivo reale (non fabbricato — vedi fuori pista),
> threading/cancellazione checkpoint, `frozen_exact` (un solo valore, non il
> range teorico). Verificato indipendentemente da me (non solo dal report
> dell'agente): `py_compile`/`ruff`/`black` puliti su entrambi i file
> toccati, 20/20 pytest diretto, 140/140 suite gemella `test_pac_planner_evaluator.py`
> invariata, selettore runner `services pac-planner-oracle` verde via
> `dev.py test --test-port 6153 --data-dir /tmp/librefolio-r2-d`, `git diff --check`
> pulito, `git status --porcelain` mostra solo i path attesi, HEAD invariato
> a `75309672edac4c91f3cc85bddfe9f8344bea406d`.
>
> **⚠️ Fuori pista**: (1) research empirica confermata — una view PAC
> `proportional` `primary` **può** essere esaustivamente infeasible: un
> `required_minimum` di route buy superiore al cap raggiungibile rende
> `ORDER_REQUIRED_MIN` violato per ogni candidato incluso lo zero (a
> differenza del lato sell su `primary`/`invest_only_baseline`, dove il
> floor si rilassa a zero); coperto da un test reale con
> `_pac_scenario(required=..., route_cap=...)`, non fabbricato. (2)
> trovato codice morto difensivo in `_decision_value_range` (branch
> `frozen_exact` con `frozen_quanta is None`) — irraggiungibile da
> costruzione valida di `DecisionAccess` (bloccato da `__post_init__`),
> raggiungibile solo via bypass `object.__new__`; non è un bug, bloccato
> con un test di regressione invece di lasciarlo non verificato, non
> toccato in `oracle.py` (frozen per questo stage). (3) preesistente,
> non collegato: `scripts/test_runner/_backend_services.py` fallisce già
> `black --check` all'HEAD `75309672e` sulla entry `tools-lifecycle`
> (stringa multi-riga concatenata implicitamente, ~150 righe di distanza
> dalla registrazione `pac-planner-oracle`) — confermato riproducendo
> `black --check` sulla revisione HEAD isolata prima di qualunque modifica
> di questa sessione; non toccato, fuori scope per file-lease.

### 16.9 Stage 2 — `constraints.py` / `objectives.py` / `compiler.py` ✅ completato 2026-09-18

> **Note implementazione**: creati tre file nuovi in
> `backend/app/services/pac_allocator/` per §16.5 punto 2 (traduzione del
> modello contabile esatto in modello SCIP, **nessuna risoluzione**):
> `constraints.py` (~418 righe) — `ScenarioFacts` + `build_scenario_facts()`
> (fatti derivati una volta sola: mappe route, prezzi d'esecuzione con
> margine, tassi FX diretti/inversi, valute dei pool di acquisto) e i
> costruttori di vincoli duri `add_funding_pool_constraints`,
> `add_ledger_balance_constraints`, `add_order_required_minimum_constraints`,
> `add_order_activation_constraints`, `add_funding_activation_constraints`,
> `add_fee_epigraph_constraints`; `objectives.py` (~246 righe) — costruttori
> di espressione per i 5 stage della cascata `proportional` nell'ordine
> `ordinal` della view, con **formulazione epigrafica separabile per Asset**
> (probe §10.1: 8/16=31ms, 16/32=55ms, 32/64=52ms, tutti ottimi gap-0),
> mai l'epigrafo globale unico che stallava; `compiler.py` (~162 righe) —
> `CompiledProgram`, `PolicyProgramScopeError`, `PolicyProgramContractError`,
> `compile_policy_program(scenario, view) -> CompiledProgram`, che crea le
> variabili intere con box bounds `[lower_quanta, upper_quanta]` (uniformi
> per tutti i `DecisionMode`, nessun branch per modo), applica i vincoli e
> costruisce le espressioni obiettivo, **senza mai chiamare `optimize()`**.
> Scope guard `_require_supported_scope` che rifiuta esplicitamente tutto
> ciò che non è PAC `proportional` `primary` (niente fallback silenzioso).
> Test-author ha creato
> `backend/test_scripts/test_services/test_pac_planner_policies.py`
> (29 test) + registrazione `pac-planner-policies` in
> `scripts/test_runner/_backend_services.py` (mirror esatto di
> `pac-planner-oracle`, 32 inserzioni 0 cancellazioni). Copertura: fatti
> scenario multi-broker/multi-valuta, direzione coppia FX diretta/inversa,
> margine d'esecuzione, nozionale quantità-intera vs importo-monetario,
> confine di **ogni** vincolo duro (funding pool, ledger balance, minimo
> obbligatorio, attivazione ordine in entrambe le direzioni della
> disgiunzione, attivazione funding, epigrafo fee), valori dei 5 stage
> obiettivo confrontati contro `evaluate_exact_candidate` su 2 scenari × 3
> candidati, ordine della cascata, 4 scope guard, box bounds delle variabili
> compilate. Verificato indipendentemente da me (non solo dal report
> dell'agente): `py_compile` OK, `ruff check` pulito su tutti e 5 i file,
> `black --check` pulito sui 4 file nuovi, 29/29 pytest diretto, 324/324
> eseguendo insieme le 5 suite PAC (`policies` + `oracle` 20 + `evaluator`
> 140 + `exact`/`normalize` 135), selettore runner `services
> pac-planner-policies` verde via `dev.py test --test-port 6153 --data-dir
> /tmp/librefolio-r2-d`, `dev.py test check-orphans` verde (213 test backend
> registrati e raggiungibili), `git diff --check` pulito, HEAD invariato a
> `75309672edac4c91f3cc85bddfe9f8344bea406d`, 0 staged.
>
> **⚠️ Fuori pista**: (1) **bug reale trovato e corretto** in `compiler.py`:
> avevo copiato dai file fratelli l'import `pyscipopt` sotto `TYPE_CHECKING`
> — corretto lì (`constraints.py`/`objectives.py` ricevono `Model`/`Variable`
> come parametri e non istanziano mai), **sbagliato** in `compiler.py` che
> chiama `Model(...)` a runtime → `NameError` al primo smoke test. Non
> intercettato da `ruff`/`black`/`py_compile` (tutti verdi col bug
> presente): è la giustificazione empirica del perché lo smoke dinamico
> precede la fiducia nei gate statici. (2) **ridisegno del probe candidate**:
> `_probe_objective_inputs` serve un `CandidateActionVector` solo per
> estrarre `fixed_reference`/`target_value` da `evaluate_exact_candidate`;
> il piano iniziale era un vettore tutto-zero, ma leggendo
> `_decision_access_conflicts` (evaluator.py:3585) e `_validate_decision_mode`
> (models.py:838) ho verificato che quanta=0 **non** è sempre valido a
> contratto (fallisce per `frozen_exact` con `frozen_quanta` non nullo, o
> per bound con `lower_quanta > 0`). Scelta finale:
> `frozen_quanta` se `mode == "frozen_exact"`, altrimenti `baseline_quanta`
> — garantito valido per **qualunque** view ben formata, e semanticamente
> inerte perché `fixed_reference`/`target_value` non dipendono dai quanta
> sondati (verificato leggendo il corpo completo di `evaluate_exact_candidate`).
> (3) **limitazione documentata, da sorvegliare**: `add_fee_epigraph_constraints`
> omette deliberatamente il cap (`maximum_fee`) dalla stima di upper bound
> interna a SCIP (`fee_upper = rate * notional_upper`). Confermato
> empiricamente con un modello SCIP reale (fee 10%, cap €2, nozionale €100):
> `buy_fee` interno a SCIP = €10 cap-oblivious, mentre `exact_fee` di
> `evaluate_exact_candidate` = €2 correttamente cappato. **Non** causa mai
> falsa infeasibility e **non** corrompe mai la fee riportata/replayata
> (quella viene sempre dall'evaluator esatto): è una limitazione ristretta
> di *qualità di ricerca*, bloccata da
> `test_fee_epigraph_cap_oblivious_regression`. (4) `DecisionAccess.upper_quanta`
> è **già** stretto dalla cassa dal builder della view (route con cap grezzo
> 10 ma €50 di cassa a €10/unità → `upper_quanta=5`, verificato
> empiricamente): il vincolo di ledger balance fa quindi lavoro
> indipendente e non ridondante solo negli scenari a pool condiviso /
> multi-route; per testarlo isolatamente serve allargare deliberatamente il
> bound con `model.chgVarUb(...)` prima di fissare il candidato (gotcha
> passato a test-author). (5) gotcha `pyscipopt` riconfermato: mai
> richiamare `optimize()` due volte sullo stesso `Model` senza
> `freeTransform()`; pattern sicuro adottato ovunque = ricompilare un
> `Model` fresco per ogni check. È una preoccupazione di Stage 3
> (`solver.py`), rinviata consapevolmente. (6) `black --check` su
> `scripts/test_runner/_backend_services.py` continua a fallire sulla entry
> `tools-lifecycle` — stesso drift preesistente già registrato in §16.8.3,
> confermato di nuovo con `black --diff` (unico hunk, ~170 righe dalle
> nostre registrazioni), non toccato.

### 16.10 Stage 3 — diagnosi iniziale `solver.py` (2026-09-18, superata da §16.11-16.12)

> **Note implementazione**: scritto `backend/app/services/pac_allocator/solver.py`
> (nuovo, ~330 righe) per §16.5 punto 3: `solve_policy_program(program, *,
> time_budget_seconds, node_limit, checkpoint)` esegue la cascata
> lessicografica vera — risolve lo stage *k*, congela il suo ottimo come
> vincolo duro, risolve lo stage *k+1* su quella faccia — nell'ordine che
> `build_objective_cascade` ha prodotto dagli `ordinal` della view, mai
> riordinato qui. API: `SolverRunResult`, `SolverStageReport`,
> `SolverSetting`, `SolverTolerances`, `ENGINE_NAME`,
> `DEFAULT_SOLVER_TIME_BUDGET_SECONDS` (3.5s, da §16.4 rischio 2),
> `STAGE_PIN_RELATIVE_SLACK`. Il modulo **non decide nulla sulla prova**:
> il vocabolario di `outcome` è deliberatamente floating
> (`incumbent`/`reported_infeasible`/`no_incumbent`) e il campo
> `exact_replay_required` è `Literal[True]` per rendere strutturalmente
> impossibile dimenticare il replay. Guardia primaria = `limits/time`
> nativo SCIP riarmato col budget residuo prima di ogni stage; il
> `checkpoint` cooperativo è pollato **solo fra gli stage** ed è
> documentato come insufficiente da solo, non silenziosamente creduto.
> Regola di onestà strutturale: solo lo stage 0 (ancora globale) può
> produrre `reported_infeasible`; un'infeasibility a stage successivo è
> un'anomalia di pin registrata in `anomaly`, **mai** un verdetto sullo
> scenario. Pin esatto (`round(value)`) per gli stage provabilmente
> integrali (`route_priority`, `active_order_rows`, ogni `tie:*` — le
> priority sono `int`, models.py:618/679), slack relativo solo per i tre
> stage continui. Gate statici verdi (`py_compile`/`ruff`/`black`).
> Aggiunto inoltre a `compiler.py` il paragrafo richiesto dal
> coordinatore (condizione 2a): la limitazione cap-oblivious della fee
> ora è nel docstring del modulo, non solo nel piano e nel test.
>
> **⚠️ Fuori pista (bloccante)**: tre trappole PySCIPOpt confermate
> empiricamente (pyscipopt 6.2.1 / SCIP 10.0, non prese dalla doc) e
> codificate nel docstring di `solver.py`: (a) `getVal(var)` dopo
> `freeTransform()` restituisce **silenziosamente** il valore dello stage
> precedente invece di sollevare — quindi ogni osservazione è letta subito
> dopo il proprio `optimize()`; (b) `getObjVal()` può restituire un numero
> finito ma **privo di significato** quando uno stage si ferma su un limite
> con zero soluzioni (osservato `134.0` con `status='timelimit'`,
> `getNSols()==0`) — l'unico gate usato è `getNSols() > 0`; (c) i bound
> mancanti arrivano come `±1e+20`, non `None`/`inf`.
>
> **⚠️ Fuori pista (il blocco vero)**: lo smoke solver-vs-oracle ha trovato
> un **difetto di modellazione reale in `constraints.py`** (file accettato
> e congelato allo Stage 2). Su `_coarse_funding_fx_scenario` l'oracolo
> esaustivo trova `(buy2, funding8, fx8)` con `explicit_cost = 2/25`,
> il solver restituisce `(buy2, funding9, fx9)` con `9/100`: entrambi
> feasible al replay, identici sugli stage 1/2/3/5, divergenti su
> `explicit_cost` — cioè un **errore di ranking lessicografico vero**, non
> rumore float. Causa: fissando nel modello SCIP il punto dell'oracolo,
> SCIP lo dichiara **infeasible** mentre `evaluate_exact_candidate` lo
> dichiara feasible. La riga FX esatta lo spiega:
> `exact_destination_credit = 1188/125 = 9.504` ma
> `posted_destination_credit = 10`, perché il ledger posta **HALF_UP al
> quantum di valuta** (`ledger.py:114-139` → `numeric.post_half_up`,
> `numeric.py:235-253`). `ledger.py:44-54` elenca le famiglie arrotondate
> (`fx_credit`, `buy_debit`, `buy_fee`, + le SELL-only); solo
> `initial_selected`/`funding_in`/`funding_out`/`fx_debit` sono esatte
> (`ledger.py:35-41`). `add_ledger_balance_constraints` usa le espressioni
> **non arrotondate** per tutte e tre le famiglie arrotondate che PAC
> proportional tocca, vede 9.504 dove il ledger posta 10, e pota l'ottimo
> vero. `objectives.py` invece è **corretto** e non va toccato: verificato
> che `_evaluate_costs` (`evaluator.py:2295-2340`) somma `order.exact_fee`
> e `action.spread_loss`, entrambi costruiti su valori esatti, non postati.
> I 29 test dello Stage 2 non potevano vederlo: la fixture del test ledger
> usa `8×EUR10 + 1×EUR20 = EUR100`, tutti multipli esatti del quantum e
> senza gamba FX, quindi HALF_UP è un no-op lì — lacuna di *forma* della
> fixture, non test difettoso. Fix prototipato **senza toccare il file
> congelato** (monkeypatch in uno script usa-e-getta): modellare ogni
> famiglia arrotondata come variabile intera di unità-quantum `u` legata
> all'espressione esatta dalla relazione HALF_UP
> `q*u - q/2 <= E <= q*u + q/2 - q*delta` (il lato destro stretto fa
> arrotondare **su** i pareggi esatti, come
> `2*remainder >= scaled_denominator`). Con il prototipo entrambi gli
> scenari tornano a coincidere **esattamente** con l'oracolo
> (`(3,3)` e `(2,8,8)`), tutti gli stage `optimal`, nessuna anomalia.
> Segnalato al coordinatore invece di assorbirlo (sua condizione 2b:
> una divergenza che cambia il ranking non è un gap tollerabile);
> in attesa di autorizzazione su (1) fix in `constraints.py`, (2)
> fixture di regressione mancante via test-author, (3) conferma del
> design della cascata. **Envelope wall-clock misurato finora, solo scala
> giocattolo**: `two-asset` 0.007-0.008s, `coarse funding+FX` 0.003s su
> 7-8 stage, ogni stage `optimal` a 0-1 nodi — tre ordini di grandezza
> sotto il budget 3.5s, ma deliberatamente **non** proposto come numero
> di policy: quello è la campagna G5, che per §16.4 rischio 3 richiede un
> compiler rappresentativo (e prima di tutto corretto) da campionare.

### 16.11 Difetto Stage 2 trovato durante Stage 3 — ledger HALF_UP ✅ risolto 2026-09-18

> **Classificazione**: difetto di `constraints.py` (file **accettato** al
> confine Stage 2), scoperto e validato dal lavoro Stage 3. Registrato qui
> come difetto arrivato oltre un confine accettato, non come dettaglio
> implementativo di Stage 3 — su richiesta esplicita del coordinatore.
>
> **Causa radice**: `add_ledger_balance_constraints` sommava gli importi
> **esatti**, ma `ledger.py` posta alcune famiglie **arrotondate HALF_UP al
> quantum di valuta** (`ledger.rounded_money_posting` →
> `numeric.post_half_up`, ties away from zero). Famiglie arrotondate
> `ledger.py:44-54`: `fx_credit`, `buy_debit`, `buy_fee` (+ 4 SELL/tax fuori
> scope); famiglie esatte `ledger.py:35-41`:
> `initial_selected`/`funding_in`/`funding_out`/`fx_debit`. Su
> `_coarse_funding_fx_scenario` un credito FX di `1188/125 = 9.504` USD
> **posta 10**: il modello vedeva 9.504 contro un debito di 10, dichiarava
> infeasible un punto realmente feasible, e restituiva `(2,9,9)` con
> `explicit_cost 9/100` invece dell'ottimo `(2,8,8)` con `2/25` — **errore
> di ranking lessicografico vero**, non rumore float. `objectives.py`
> **non** è stato toccato: verificato che `_evaluate_costs`
> (`evaluator.py:2295-2340`) somma `order.exact_fee` e
> `action.spread_loss`, entrambi esatti, non postati.
>
> **Perché i 29 test Stage 2 non potevano vederlo**: la fixture del test
> ledger usa `8×EUR10 + 1×EUR20 = EUR100` — importi tutti multipli esatti
> del quantum, e nessuna gamba FX. HALF_UP è un **no-op** su quella forma.
> Lacuna di **forma della fixture**, non qualità del test: test-author non
> aveva alcun segnale per sospettare l'arrotondamento di posting.
>
> **Note implementazione (condizioni A-D del coordinatore)**:
> **(A) segno provato e imposto, non ereditato** — `floor(x+1/2)` è ties
> verso +∞ mentre `post_half_up` è ties away from zero: coincidono solo per
> `x >= 0`. Le tre famiglie in scope sono magnitudini non negative per
> costruzione (nozionale su misura non negativa, variabile fee con `lb=0`,
> credito FX su debito non negativo) e `_posted_units_term` aggiunge una
> riga `:nonneg` che **impone** la precondizione invece di assumerla.
> **(B) fail-closed sulle famiglie non modellate** — `_ROUNDED_FAMILY_DETECTORS`
> ha un detector per **ogni** famiglia di `ledger._ROUNDED_FAMILIES`
> (importata come unica fonte di verità); `_require_modelled_rounded_families`
> solleva `LedgerPostingScopeError` sia se `ledger.py` cresce una famiglia
> senza detector, sia se lo scenario posta davvero una famiglia non
> modellata. Il difetto vero non era "abbiamo scordato l'arrotondamento" ma
> "una famiglia arrotondata non modellata è degradata in silenzio alla sua
> espressione esatta e nessuno ha protestato": ora quel degrado è un errore.
> **(C) delta eliminato, non calibrato** — la formulazione proposta usava
> `E <= q*u + q/2 - q*delta` con `delta = 1e-9`. **Misurato: era sbagliato**
> — `q*delta = 1e-9` sta *sotto* `numerics/feastol = 1e-6`, quindi SCIP lo
> avrebbe assorbito e i pareggi avrebbero arrotondato dalla parte sbagliata;
> funzionava solo perché nessun pareggio è raggiungibile in queste fixture.
> Soluzione adottata: **coppia epigrafica non stretta**
> `q*u - q/2 <= E <= q*u + q/2`, soddisfacibile per **ogni** `E` reale,
> quindi **non può mai potare** — nessuna costante da calibrare, nessuna
> interazione con feastol. L'unica laschezza è sui pareggi esatti, e lì vale
> un'asimmetria dimostrata: per un **debito** scegliere l'unità bassa è
> permissivo (ammette punti che il replay esatto rifiuta — sicuro), per un
> **credito** è restrittivo (può potare l'ottimo — non sicuro). Quindi solo
> i crediti devono essere provabilmente tie-free:
> `_half_up_tie_reachable` lo decide **esattamente in O(1)** — con
> `coefficient/quantum = a/b` ai minimi termini un pareggio richiede
> `2an + b ≡ 0 (mod 2b)`, risolubile **solo se `b` è pari**, e allora per
> `n ≡ -a⁻¹·(b/2) (mod b)`. Validato contro forza bruta su 4000 razionali
> casuali, 0 discordanze; sulla fixture reale il primo pareggio è a `n=125`
> (`E = 297/2 = 148.5`), fuori dal range `[0,14]` — ecco perché il
> prototipo "funzionava". Un pareggio raggiungibile su un credito solleva
> `LedgerPostingScopeError` invece di rischiare una potatura silenziosa.
> **(D) gate oracolo permanente** — l'armamentario solver-vs-oracolo non
> vive più in `/tmp`: `test_pac_planner_solver.py` contiene
> `test_solver_incumbent_equals_exhaustive_oracle_optimum`, parametrizzato
> su `_ORACLE_AGREEMENT_FIXTURES` (aggiungere una fixture estende il gate
> automaticamente), che replaya il candidato del solver con
> `evaluate_exact_candidate` e confronta **quanta identici + chiave
> lessicografica completa identica** con l'ottimo esaustivo. La chiave è
> re-implementata in modo indipendente, non importata da `oracle.py`: il
> gate non è circolare. Da qui in poi "solver verde" significa
> "oracle-agreement verde".
>
> **Verifica**: fix validato sul percorso reale — entrambe le fixture
> tornano a coincidere **esattamente** con l'oracolo (`(3,3)` e `(2,8,8)`,
> `explicit_cost 0.08`), tutti gli stage `optimal`, nessuna anomalia.
> **Mutation test**: reintrodotto il vecchio comportamento a somma esatta
> con un monkeypatch usa-e-getta → `test_solver_incumbent_equals_exhaustive_oracle_optimum[coarse_funding_fx]`
> va **rosso**, file ripristinato e verificato identico. Un test di
> regressione che non può fallire non è un test di regressione.
>
> **⚠️ Fuori pista**: il primo tentativo del guard `_require_modelled_rounded_families`
> citava `scenario.scenario_id`, campo inesistente su `ExactPlannerScenario`
> → la riga di `raise` sollevava `AttributeError` invece di
> `LedgerPostingScopeError`. Trovato solo perché ho smoke-testato il
> **percorso di errore** e non solo quello felice; `ruff`/`black`/`py_compile`
> erano verdi col bug presente. Terza volta in tre stage che un gate statico
> pulito nasconde un difetto che solo l'esecuzione dinamica vede.

### 16.12 Stage 3 — `solver.py` ✅ completato 2026-09-18

> **Note implementazione**: `solver.py` (~330 righe) implementa la cascata
> lessicografica reale: risolve lo stage *k*, congela il suo ottimo come
> vincolo duro, risolve *k+1* su quella faccia, nell'ordine prodotto dagli
> `ordinal` della view (mai riordinato). Pin **esatto** (`round(value)`) per
> gli stage provabilmente integrali (`route_priority`, `active_order_rows`,
> ogni `tie:*`: le priority sono `int`, models.py:618/679), quindi per quella
> parte della cascata il contratto lessicografico è esatto e non tollerante;
> `STAGE_PIN_RELATIVE_SLACK` (1e-12, derivato dall'errore di
> rappresentazione float64, non una soglia economica) solo per i 3 stage
> continui. Guardia primaria = `limits/time` nativo SCIP riarmato col budget
> residuo prima di ogni stage; `checkpoint` pollato solo fra gli stage e
> documentato come insufficiente. Onestà **strutturale**: `outcome` usa
> vocabolario floating (`incumbent`/`reported_infeasible`/`no_incumbent`),
> `exact_replay_required: Literal[True]` rende impossibile dimenticare il
> replay, e solo lo stage 0 globale può produrre `reported_infeasible` —
> un'infeasibility a stage successivo popola `anomaly` e conserva il
> candidato precedente, mai un verdetto sullo scenario.
> Test-author ha creato `test_pac_planner_solver.py` (12 test) + esteso
> `test_pac_planner_policies.py` (+5, 29→34) + registrato
> `pac-planner-solver` in `_backend_services.py` (additivo).
> Verificato indipendentemente da me: `py_compile`/`ruff` puliti su tutti i
> file, `black --check` pulito su 13 file di `pac_allocator/` e sui 2 file
> di test, 12/12 solver, 34/34 policies, **341/341** sulle 6 suite PAC
> insieme (324 baseline + 5 + 12, nessuna regressione), entrambi i selettori
> runner verdi in lane 6153, `check-orphans` verde (214 file backend
> registrati e raggiungibili), `git diff --check` pulito, HEAD invariato a
> `75309672edac4c91f3cc85bddfe9f8344bea406d`, 0 staged.
>
> **⚠️ Fuori pista**: tre trappole PySCIPOpt confermate empiricamente
> (pyscipopt 6.2.1 / SCIP 10.0, non prese dalla doc) e codificate nel
> docstring: (a) `getVal(var)` dopo `freeTransform()` restituisce
> **silenziosamente** il valore dello stage precedente invece di sollevare;
> (b) `getObjVal()` può restituire un numero finito ma privo di significato
> quando uno stage si ferma su un limite con zero soluzioni (osservato
> `134.0` con `status='timelimit'`, `getNSols()==0`) — l'unico gate usato è
> `getNSols() > 0`; (c) i bound mancanti arrivano come `±1e+20`, non
> `None`/`inf`. Scelta di test-author condivisa: le fixture con **fee cap
> vincolante** sono deliberatamente **escluse** dal gate oracolo, perché
> l'epigrafo fee è documentato cap-oblivious e può legittimamente cambiare
> quale candidato il solver *preferisce* — è la limitazione nota §16.9,
> non una discordanza che quel gate debba sorvegliare.
> **Envelope wall-clock: ancora solo scala giocattolo** — 0.003-0.008s su
> 7-8 stage a 0-1 nodi, tre ordini di grandezza sotto il budget 3.5s.
> Deliberatamente **non** convertito in un numero di policy: la
> `ToolOperationPolicy` resta lease del coordinatore e resta non impostata
> finché la campagna G5 non gira su un compiler rappresentativo (§16.4
> rischio 3). Risposta onesta a oggi: *non misurato a scala rappresentativa*.

### 16.13 Stage 4 — `proof.py` ✅ completato 2026-09-18

> **Note implementazione**: creato
> `backend/app/services/pac_allocator/proof.py` (nuovo, ~250 righe) per
> §16.5 punto 4 — la terza delle tre dimensioni indipendenti di Proof
> Semantics A (§16.3): la validazione dell'incumbent è di `evaluator.py`,
> l'evidenza floating del solver è di `solver.py`, la **conclusione
> matematica sul dominio discreto** è di questo modulo e solo di questo.
>
> Requisito del coordinatore, testuale: la transizione non sicura dev'essere
> **irrappresentabile, non semplicemente non scritta** — "se ti trovi a
> scrivere un commento che dice «non passare mai proven qui», il design è
> sbagliato; rendi l'argomento impossibile". Implementato con **tre
> meccanismi indipendenti**, di natura diversa per non cadere insieme:
>
> 1. **Assenza.** `conclude_without_proof(solver: SolverRunResult) ->
>    UnprovenConclusion` è l'**unica** funzione che consuma evidenza solver,
>    e il suo tipo di ritorno non ammette altro. **Non esiste** in tutto il
>    modulo una funzione che mappi un `SolverRunResult` su un tipo proven:
>    non c'è una guardia da aggirare, non c'è nulla da chiamare. Verificato
>    in sorgente, non a occhio: `SolverRunResult` compare esattamente 3
>    volte (docstring, import, quell'unica firma).
> 2. **Impossibilità di tipo.** `UnprovenConclusion` è un dataclass frozen
>    i cui unici campi sono `reason_code` e `kind`, con `kind` un
>    `Literal["not_proven"]` a valore singolo. Non c'è niente da impostare
>    male e niente da dimenticare di impostare.
> 3. **Costruttore sigillato.** Entrambi i tipi witness richiedono il
>    sentinella privato di modulo `_WITNESS_SEAL`, che non esce mai dal
>    modulo; costruirne uno senza solleva `ProofForgeryError`. Anche codice
>    che scavalca l'API pubblica non può fabbricare la chiave che sblocca
>    una conclusione provata.
>
> Superficie: `ProofForgeryError`, `ExhaustiveOracleWitnessFacts`,
> `DeterministicConflictWitnessFacts`, `OptimalProvenConclusion`,
> `InfeasibilityProvenConclusion`, `UnprovenConclusion`, alias
> `ProvenConclusion`/`PlanConclusion`, `conclude_without_proof`,
> `conclude_with_oracle`, `conclude_infeasible_from_conflicts`,
> `describe_conclusion`, costante `NOT_PROVEN_REASON`
> (`allocation.exact_proof_not_established`, codice generico di fase 1 per
> §16.7 Q2: time limit, node limit e dominio oracle troppo grande collassano
> tutti su quello invece di inventare codici wire prima che la telemetria
> lo giustifichi).
>
> **Punto semantico sottile, esplicitato perché era il posto dove sbagliare
> senza accorgersene**: l'oracolo dimostra un enunciato sul **proprio**
> ottimo, non su qualunque candidato il chiamante pubblichi. Se `published`
> differisce dal `best_candidate` dell'oracolo — per esempio un incumbent
> del solver che non concorda — la conclusione viene **degradata a
> `not_proven`**, mai trasferita. Degradare è sempre corretto; trasferire
> attaccherebbe silenziosamente una prova a un oggetto di cui non parlava.
>
> **`gap_bounded` deliberatamente NON implementato**: richiede un bound
> duale valido, e ricavarlo dal duale floating di SCIP sarebbe esattamente
> la promozione che questo file esiste per impedire. Spedirlo
> "temporaneamente" avrebbe svuotato la garanzia al primo punto di comodo.
> `score_lattice_closure` idem, rinviato. **Entrambe le assenze sono
> asserite da un test**, quindi non possono ricomparire per sbaglio: è la
> parte che rende il rinvio sicuro invece che solo posticipato.
>
> **Test**: test-author ha creato
> `backend/test_scripts/test_services/test_pac_planner_proof.py`
> (33 test). Verificato indipendentemente da me, non sul suo report:
> `py_compile`/`ruff`/`black` puliti su entrambi i file nuovi, **33/33**
> sulla suite proof, **374/374** sulle 7 suite PAC insieme (341 invariati +
> 33 nuovi, zero regressioni). Prima ancora dei test avevo eseguito un
> harness di smoke mio: **37/37**, che copre ogni percorso pubblico **e ogni
> percorso di raise**.
>
> **Regola permanente del coordinatore applicata alla lettera**: ogni
> percorso di `raise` è stato provato per il tipo di eccezione che
> *dichiara*, non solo per il fatto che solleva — 14 percorsi distinti di
> `ProofForgeryError`, ciascuno con `pytest.raises(ProofForgeryError)`, mai
> `Exception` nudo. La regola nasce dall'incidente `scenario.scenario_id`
> (§16.11): una guardia che solleva il tipo sbagliato è peggio di nessuna
> guardia, perché sconfigge la gestione del chiamante sembrando
> deliberata.
>
> **Mutation test della garanzia**, perché un'affermazione di
> irrappresentabilità che non può fallire è decorazione. Rotta in tre modi
> indipendenti, tutti rilevati: (1) `conclude_without_proof` che promuove un
> incumbent a `optimal_proven` → 2 rossi; (2) controllo del sigillo
> disattivato → 2 rossi; (3) ottimo dell'oracolo trasferito a qualunque
> candidato pubblicato → 1 rosso. `proof.py` ripristinato **byte-identico**
> dopo ognuna, 33/33 di nuovo verdi.
>
> **⚠️ Fuori pista**: nessun bug trovato in `proof.py` da test-author, e
> nessuno trovato da me nello smoke — la prima volta in quattro stage. Va
> però letta bene: `proof.py` è l'unico dei cinque moduli che **non
> istanzia nulla a runtime e non parla con SCIP**, quindi è anche l'unico
> dove i gate statici hanno davvero il potere che sembrano avere. Non è una
> smentita della regola "smoke prima di fidarsi", è la sua conferma per
> contrasto.
>
> **⚠️ Fuori pista (registrazione differita, transitoria e voluta)**:
> `test_pac_planner_proof.py` esiste, è verde, ma **non è registrato** nel
> runner, perché registrarlo significa modificare
> `scripts/test_runner/_backend_services.py`, uno dei 10 path staged sotto
> freeze. Conseguenza dichiarata apertamente invece che ammorbidita:
> `dev.py test check-orphans` è **ROSSO** nel worktree, con
> `test_services/ (1 orphan) • test_pac_planner_proof.py`.
> Decisione del coordinatore: **opzione (b)**, lasciarlo così. Il
> ragionamento va conservato perché non è ovvio a lettura veloce: il rosso è
> una proprietà del **worktree in volo**, non di un commit. Il commit Stage
> 3 cattura l'indice staged, che `test_pac_planner_proof.py` non contiene
> affatto; su quella revisione `check-orphans` è verde e lo resterà. Quindi
> l'opzione (a) — registrare subito — non comprerebbe nulla di durevole
> (la storia è verde comunque) e costerebbe l'unica cosa che un checkpoint
> serve a dare: uno SHA che significa esattamente ciò che è stato
> rivisto. Alla revoca del freeze: registrare, riportare `check-orphans` a
> verde, e far viaggiare il tutto nel commit Stage 4 insieme a `proof.py` e
> alla sua suite. **Non è una svista**: è una condizione gestita e
> temporanea.

### 16.14 Stage 5 — `wire_numbers.py` / `planner_report.py` / `planner.py` ✅ completato 2026-09-18

> Questa sezione era stata scritta in due file separati
> (`plan-phase00Step3Stage4ProofSemantics.prompt.md`,
> `plan-phase00Step3Stage5ReportProjection.prompt.md`) perché questo piano era
> fra i 10 path staged sotto freeze e non poteva essere modificato. Col commit
> `9229085e9` il freeze è caduto e i due file sono stati ripiegati qui e
> cancellati: un documento, una cronologia. **Nessun errore è stato
> ripulito nella fusione** — le conclusioni sbagliate restano scritte accanto
> a quelle giuste, altrimenti averle annotate non serviva a niente.


#### Decisioni di contratto ricevute dal coordinatore (2026-09-18)

| Domanda | Risposta | Motivazione conservata |
|---|---|---|
| **Q1** `deployment` in fase 1 | `DeploymentUnavailable(reason_code="allocation.deployment_omitted")` | Dice "non l'abbiamo calcolato", che è vero. `primary_is_deployment` asserirebbe un'equivalenza mai stabilita: sarebbe un'affermazione, non un report. |
| **Q2** `exposure_rows` | **Derivarle** (opzione i), fail-closed | `[]` è valido a schema ma semanticamente una bugia: il consumatore non distingue "nessuna esposizione" da "non calcolate" — la stessa degradazione silenziosa eliminata tre volte in questo workstream (ledger non arrotondato, `missing_fx_pairs`, famiglie arrotondate non modellate). Aggregare `ExactAsset.exposures` pesate per target e per valore finale è **aritmetica su quantità già decise**, stessa classe del sommare le righe ordine in un costo totale: nessuna nuova decisione economica, nessuna policy nuova, non può cambiare quale candidato vince → è una proiezione, sta in 5a. |
| **Q3** `plan_rebalancing` | **Non spedirlo** | La risposta Q1 originale ("spedisci entrambe") riguardava il *confine di ownership*, non lo scope. Una funzione che esiste ma fallisce sempre è peggio di una assente, perché invita al cablaggio: qualcuno la importerà leggendo il nome e non il corpo. Assente → ImportError nel punto esatto in cui il lavoro mancante è ovvio. Arriva col lavoro SELL. |

Condizione non opzionale su Q2: coperture parziali **mai normalizzate** per
nascondere un ammanco; `target_weight` e `final_weight` sono proiezioni
separate di quantità decise separatamente, mai derivate l'una dall'altra per
comodità.

#### Mappature verificate in sorgente (non assunte)

Trappole trovate leggendo gli invarianti, prima di scrivere codice:

1. **`PlannerAccountingSummary.rounding_delta` ← `ExactAccountingEvaluation.rounding_adjustment`**,
   **non** `raw_rounding_delta`, nonostante la description del campo dica
   "Raw posted-exact aggregate rounding delta". Deciso dall'identità, non
   dal nome: `evaluator.py:2472` calcola
   `identity_delta = shortfall - (free_cash + physical_reserves +
   economic_losses + rounding_adjustment)` e lo schema
   (`pac_allocator.py:2369`) richiede
   `shortfall == free_cash + physical_reserves + economic_losses +
   rounding_delta` **con `identity_delta == 0`**. Solo
   `rounding_adjustment` chiude l'identità. Mappare il campo "raw"
   avrebbe rotto il validator — ed è il tipo di errore che il nome del
   campo attivamente suggerisce.
2. **`PlannerLedgerRow.rounding_delta` ← `ExactBrokerLedgerEvaluation.raw_rounding_delta`**
   (qui sì il grezzo): il validator di riga
   (`pac_allocator.py:1962-1996`) **non include** alcun termine di
   arrotondamento nella sua identità — `initial_selected + funding_in +
   fx_credit + gross_sell_credit - funding_out - fx_debit - buy_debit -
   buy_fees - sell_fees - tasse == final_spendable` — quindi lì
   `rounding_delta` è informativo, non identitario. Due campi omonimi su
   due modelli diversi con due sorgenti diverse: la coincidenza di nome è
   una trappola, non un indizio.
3. **L'identità di riga ledger gira sugli importi POSTATI.** Verificato sul
   caso reale: cella destinazione/USD con `fx_credit = 10` (postato) e
   `buy_debit = 10` → `final_spendable = 0` ✓. Se il wire pubblicasse
   l'esatto `9.504` l'identità non chiuderebbe. È **conferma indipendente**
   che il fix HALF_UP di §16.11 stava modellando la realtà del ledger e non
   inventando una convenzione: il modello SCIP, il replay esatto e il
   contratto wire ora concordano tutti sugli stessi importi postati.

   Corollario che vale la pena fissare, perché è la corroborazione più forte
   che abbiamo e impedisce a un lettore futuro di chiedersi se il fix fosse
   over-engineering: **`PlannerLedgerRow` mappa uno-a-uno su
   `ExactBrokerLedgerEvaluation`, `rounding_delta` incluso, e il contratto
   wire era congelato molto prima che il difetto venisse trovato.** Il wire
   portava già un campo per il residuo di arrotondamento. Quindi la
   distinzione esatto/postato era reale nel dominio da sempre, e il modello
   compilato era semplicemente l'unico posto che se l'era dimenticata — non
   una complicazione aggiunta per far tornare i conti al solver.

#### Q2 — correzione: il validator è la specifica, la union di tipi è solo il suo alfabeto

La risposta Q2 iniziale (due bullet: "copertura parziale → `final_weight`
unavailable" **e** "ammanco visibile, mai riscalare") si contraddiceva nel
caso che conta: un asset con valore ma nessuna esposizione dichiarata in una
dimensione. Ho argomentato — correttamente sui dati che avevo — che il
vocabolario delle `reason` (`zero_current_invested`, `zero_final_invested`,
`not_applicable`, `dependency_unavailable`: due guardie di denominatore zero,
due di assenza genuina, **nessuna** `partial_coverage`) mostra che la forma
unavailable è per i **calcoli indefiniti**, non per gli **input incompleti**.
Quella lettura dell'enum era giusta. La conclusione era comunque sbagliata.

Il coordinatore è andato a leggere il **validator**, e il contratto aveva già
deciso in un modo che nessuno dei due aveva proposto. Verificato riga per riga
da me prima di agire:

- `_validate_weight_availability` (`schemas/pac_allocator.py:1251-1267`) è
  **totale**, ammette esattamente due mondi:
  - `total == 0` (`:1258-1263`): **ogni** peso della dimensione dev'essere
    unavailable con reason esattamente `zero_final_invested`; un solo valore
    disponibile solleva. Disponibilità mista: impossibile.
  - `total != 0` (`:1264-1267`): **ogni** peso dev'essere disponibile, in
    `[0,1]`, **e la dimensione deve sommare esattamente a 1** ("must form a
    complete unit vector"). `value is None` solleva a `:1264`.
- `_validate_exposure_projection` (`:2456-2460`) impone la stessa chiusura a
  `target_weight`, **incondizionatamente**.

Conseguenza: **entrambe le uscite sono chiuse.** Il bullet 1 è inemettibile
appena `final_invested != 0` (`:1264` lo rifiuta); il bullet 2 è inemettibile
(`:1266` sul finale, `:2460` sul target); il mio esempio (Tech a 0.5, dimensione
che somma a 0.5) solleva `ValueError: sector final exposure weights must form a
complete unit vector`.

> **Lezione, stretta e da conservare**: quando un contratto wire ha un
> validator, **il validator è la specifica e la union di tipi è soltanto il suo
> alfabeto**. L'enum mi ha detto correttamente che `unavailable` non è per la
> copertura parziale; non poteva dirmi che neanche il ramo numerico lo è.
> Ragionare su cosa una tabella *dovrebbe* dire invece di leggere cosa il
> validator permette di dire ha prodotto una risposta sbagliata che sembrava
> ben argomentata.

### Forma scelta: riga categoria residua (opzione 3)

Le sole tre forme valide a schema erano: (1) omettere la dimensione, (2)
`exposure_rows = []`, (3) rappresentare il residuo non categorizzato come una
**propria riga categoria**, così che entrambi i vettori chiudano a 1 per
costruzione. Scelta (3): (1) e (2) sono il fallimento "tabella vuota" con un
altro cappello — il consumatore non distingue "non calcolato" da "nessuna
esposizione" — e (1) per giunta **distrugge** l'affermazione corretta che Tech
è davvero metà del portafoglio. (3) conserva quel `0.5` e trasforma la metà
mancante da assenza in **fatto nominato**: non più un buco che la UI deve
dedurre da una somma che non chiude, ma una fetta con un'etichetta.

Derivazione, per dimensione, su tutti gli asset:
`peso_categoria = Σ_asset w_asset × exposure_weight(asset, dim, categoria)`,
`peso_residuo = Σ_asset w_asset × (1 − Σ_categorie exposure_weight(asset, dim))`,
con `w_asset` = peso target per il vettore target, quota di valore finale per
quello finale. La chiusura è quindi un'**identità**
(`Σ_asset w_asset × 1 = 1`), **non** una normalizzazione — da asserire in
aritmetica esatta, mai raggiunta riscalando, e il residuo non va mai fuso in
una categoria reale.

Vincoli tenuti: regola **uniforme** senza casi speciali (se nessun asset
dichiara nulla, si emette il solo residuo a peso 1 — sopprimere la dimensione
proprio quando il dato è al suo peggio invertirebbe il segnale); le
dichiarazioni **parziali per asset** sono input reale, non solo gli asset del
tutto non dichiarati (`normalize.py:1093-1109` valida intervallo e unicità
`(dimension, category)` ma **non** richiede che una dimensione chiuda per
asset, quindi un asset al 60% Tech contribuisce `0.4·w_asset` al residuo);
`total == 0` va comunque nel mondo unavailable per **tutte** le righe residuo
incluso, con reason `zero_final_invested`, mentre `target_weight` deve
comunque chiudere a 1 perché i target non dipendono dal denominatore.

### Provenance del residuo — risolta, non fabbricata

`PacExposurePlanRow.provenance_ids` è `min_length=1` (`:2007`) e il residuo
nasce proprio dove **non** esiste una dichiarazione di esposizione, quindi
nessun `ExactExposure.provenance_id`. Punto di stop esplicito del
coordinatore: derivarla se è possibile farlo in modo veritiero, altrimenti
fermarsi invece di inventarla.

È possibile, e senza sintetizzare nulla. Evidenza raccolta prima di decidere:

1. Nel dominio **ogni record di input** porta il proprio `provenance_id`:
   `ExactProvenance`, `ExactExposure`, `ExactAssetQuote`, `ExactBroker`,
   `ExactHolding`, `ExactExistingCash`, `ExactContribution`,
   `ExactFundingRoute`, `ExactOrderRoute`, `ExactCostBasis`, `ExactAssetTax`,
   `ExactWithholding`.
2. Lo schema tratta `provenance_ids` **uniformemente** su righe funding, fx,
   ordine ed esposizione (`:2530-2534`): l'unione dev'essere inclusa nella
   lista provenance pubblicata di primo livello, e gli id devono essere unici
   per riga.

Quindi la semantica del campo è "**i record di input da cui questa riga è
stata derivata**", non "chi ha asserito questa classificazione". Sotto quella
lettura il residuo ha una provenance veritiera: l'unione dei
`quote.provenance_id` degli asset che vi contribuiscono, più i
`exposure.provenance_id` delle dichiarazioni parziali che lo generano. Sono
**id reali di record reali**, già pubblicati — nessuna sintesi, nessun
"sembra tracciato e non lo è". Non afferma che qualcuno abbia classificato il
residuo: dice da dove vengono i numeri che lo compongono.

#### Regole generali ricavate in 5a (valgono oltre questo step)

**Containment — rendere la regola incondizionata, non testare il ramo cattivo.**
`_validate_ready_solution` (`:2531`) chiede che l'unione delle provenance
citate dalle righe sia contenuta nella lista provenance pubblicata. Quella
regola è **condizionale a una nostra scelta a monte**: se pubblicassimo solo
le provenance "usate", il fallimento comparirebbe unicamente sugli scenari con
asset non categorizzati, cioè una suite verde non proverebbe niente senza una
fixture che azzecchi il ramo. Invece di aggiungere quella fixture,
`build_planner_provenance` pubblica **l'intera** lista provenance dello
scenario — fedele alla description del campo ("root provenance records
referenced by every copied or manually supplied fact") e, soprattutto, la
regola diventa **totale per costruzione**: nessuna riga può citare un id
assente. Generalizzando:

> Quando la regola di un validator è condizionale a una nostra scelta a monte,
> **preferire rendere la regola inviolabile invece di aggiungere una fixture
> che per caso esercita il ramo cattivo.** Le fixture decadono; una regola che
> non può essere violata no.

**Ogni turno con un risultato rilevante per il coordinatore finisce con
`send_session_message`.** Riassumere solo all'utente ha un danno concreto, non
procedurale: il coordinatore costruisce le direttive di ripresa da ciò che
osserva dall'esterno (mtime, `py_compile`, `git diff`), e quella vista **non
può vedere il lavoro completato**. Risultato: una lista di "remaining" stantia
e mezzo turno speso a correggerla. Se un turno sta per finire senza quel
messaggio, è già il segnale che qualcosa è andato storto.

**Uno stub che solleva non può attraversare un confine di turno.** Durante la
costruzione ho appeso un `raise NotImplementedError` e l'ho sostituito nello
stesso turno. Non ha mai raggiunto un gate, ma se il turno fosse finito male
sarebbe sopravvissuto — e `ruff`, `black` e `py_compile` sono **tutti
contenti** di un `raise NotImplementedError` pulito. Sarebbe stato il quinto
difetto invisibile all'analisi statica in sei stage, stessa famiglia
dell'import sotto `TYPE_CHECKING` (§16.9) e di `scenario.scenario_id`
inesistente (§16.11).

#### 5b — due difetti veri, trovati da test-author, corretti (autorizzazione: Opzione 1)

**Correzione che va contro di me, e il tempismo è la parte interessante.** Avevo
riportato al coordinatore che far girare il solver anche quando decide
l'oracolo era **"forzato dal contratto"**, perché
`ReportedFloatingSolverEvidence.stages` è `min_length=1`. **Conclusione
sbagliata.** `PlannerSolverEvidence` è una *union*
(`SolverNotRunEvidence | ReportedFloatingSolverEvidence`, `:1519-1522`) e
`_validate_stop_evidence` (`:2683-2688`) pretende evidenza floating **solo**
quando `stop_reason != "completed"`; la regola finished/unfinished vale
**solo dentro** il ramo floating. Quindi `completed` + `not_run` è
perfettamente legale. Di più: `SolverNotRunReasonCode` (`:700`) ha **un solo
valore**, `allocation.solver_not_required` — nessuno scrive un enum a valore
singolo per un percorso che non si aspetta venga mai preso.

> Ho letto il vincolo di un **campo** e mi sono fermato lì, invece di leggere
> il **validator che governa la sua union**. È esattamente R1 — *il validator
> è la specifica, la union di tipi è solo il suo alfabeto* — la regola che
> avevo appena applicato al codice altrui e non al mio. Il coordinatore ha
> commesso lo stesso errore lo stesso giorno, **a meno di un'ora** da quando
> aveva scritto R1, sullo stesso file. Questo dice che razza di regola è R1:
> non una lacuna di conoscenza che si chiude una volta, ma un **fallimento di
> attenzione ricorrente che sopravvive al fatto di conoscerlo**. La
> conclusione sbagliata resta scritta qui accanto a quella giusta: un registro
> del debito che cancella i propri errori è un registro non verificabile.

### Difetto A — `plan_pac_allocation` sollevava su un input legittimo

Fixture + `required_minimum = 1 unità` (€5 di cassa contro €10 di prezzo
unitario) faceva **sollevare** `ValidationError: Completed stops require
finished stages`, violando la docstring stessa della funzione ("Never raises
on a planning outcome"). Meccanismo: uno stage SCIP infeasible è
necessariamente `unfinished` (uno `finished` deve portare un primal finito,
che una risoluzione infeasible non ha), mentre
`PacPlannerReadyInfeasibleResult` pinna `stop_reason="completed"` e il
validator impone `completed ⇔ nessuno stage unfinished`. Contraddizione →
**`ready_infeasible` era irraggiungibile ogni volta che il solver girava**,
cioè sempre, a causa dell'errore qui sopra. Non è un caso esotico: è un utente
con un minimo d'ordine che non riesce a coprire a inizio mese.

**Fix (sottrattivo)**: l'oracolo si prova per primo; quando risolve, il solver
**non gira** e il risultato porta
`SolverNotRunEvidence(reason="allocation.solver_not_required")` con
`stop_reason="completed"`. Sistema il crash **e** elimina la corsa ridondante
del solver invece di scusarla.

> **Costo onesto del fix, da non leggere come indebolimento**: la produzione
> perde un *cross-check diagnostico* — un risultato deciso dall'oracolo non ha
> più un incumbent del solver che potrebbe dissentire. Non è una perdita di
> garanzia: l'oracolo è esaustivo, quindi la sua risposta **è** la risposta, e
> un solver in disaccordo avrebbe segnalato un bug di modellazione, non un
> risultato pubblicato sbagliato. Quel cross-check continua a vivere nel gate
> oracle-agreement di `test_pac_planner_solver.py`, che è dove ha preso il
> difetto HALF_UP. **Verificato prima di toccare qualunque cosa** che il gate
> non passa dal service entry: chiama `compile_policy_program` +
> `solve_policy_program` direttamente (`:73-74`) e `run_exhaustive_oracle`
> (`:159`), zero riferimenti a `plan_pac_allocation`, su tutte e 5 le fixture
> parametrizzate. Se fosse passato di lì, il gate sarebbe diventato **vacuo in
> silenzio** — passando per sempre confrontando l'oracolo con niente.

### Difetto B — vocabolario sbagliato, ed è un errore di Stage 4, non di 5b

`_wire_infeasibility` passava `evaluation.conflict_codes` (codici di vincolo
del dominio esatto, es. `ORDER_REQUIRED_MIN`) dentro
`DeterministicConflictWitness.issue_codes`, tipato `list[PlannerIssueCode]`.
Verificato: `"ORDER_REQUIRED_MIN" in PlannerIssueCode` → **False**; l'universo
wire è `allocation.*` ed è **congelato a 80 valori** con guardia
`RuntimeError` (`issues.py:48-50`). L'errore nasce in Stage 4:
`proof.conclude_infeasible_from_conflicts(evaluation)` prendeva l'input dal
dominio sbagliato; 5b è solo dove è stato eseguito per la prima volta.

**Fix**: fase 1 **non emette** `deterministic_conflict`. L'infeasibilità
provata viene dal solo oracolo; tutto il resto è onestamente `not_proven`.

> Ragionamento da conservare, perché qualcuno lo ri-proporrà: **una
> affermazione fatta al tempo della normalizzazione su input dichiarati e una
> fatta al tempo della valutazione su un candidato non sono la stessa
> affermazione.** Una tabella che mappasse `ORDER_REQUIRED_MIN` su
> `allocation.order_minimum_exceeds_cap` fabbricherebbe un'equivalenza fra due
> asserzioni diverse e la pubblicherebbe come **witness** — esattamente la
> classe di cosa che `proof.py` esiste per rendere irrappresentabile.
> Estendere l'enum non è disponibile: congelato, guardato, e non di nostra
> competenza.

### Limitazione di contratto trovata durante la verifica (segnalata, non corretta)

Sul percorso over-cap **infeasible** (oracolo escluso, solver attivo) il
risultato degrada onestamente a `ready_no_incumbent`/`not_proven`, ma
`build_stop_reason` mappa a **`stop_reason == "time_limit"`** anche se la
risoluzione non è stata fermata da un orologio: è infeasible. Non c'è una
risposta onesta disponibile — l'enum ammette solo
`completed | time_limit | node_limit`, `completed` è vietato perché gli stage
sono `unfinished`, e nessuno dei due limiti rimasti è vero. È una **limitazione
del contratto congelato**, non un difetto nostro. test-author ha
correttamente asserito l'invariante robusto (`stop_reason != "completed"` in
presenza di stage unfinished) invece di pinnare `"time_limit"`.

#### 5b — decisioni che vanno lette, non dedotte

**`plan_pac_allocation` NON è ri-esportata dal `__init__` del package, ed è
deliberato.** L'istruzione iniziale del coordinatore diceva "esportata da
`__init__.py`"; era **sbagliata** e la correzione è sua. La ragione è
concreta, non stilistica: la catena di import è
`planner → compiler:54 → pyscipopt` (`compiler.py` importa `Model` a livello
di modulo perché, a differenza di `constraints`/`objectives`, ne istanzia uno
davvero). Ri-esportare farebbe trascinare **SCIP a import-time a ogni
consumatore delle analisi P1 leggere** (`analyze_pac_budget`,
`analyze_rebalancing`) per un solver che non chiamano mai, e falsificherebbe
in silenzio la docstring del package — *"Pure P1 allocation analyses. No
solver, order, lookup, or persistence."* — cioè esattamente la promessa su cui
un lettore si basa per decidere se importare il package costa poco.

Verificato, non asserito: importare `backend.app.services.pac_allocator`
lascia `pyscipopt` **assente** da `sys.modules`; importare `planner` ce lo
mette.

> Un export **assente e non spiegato** è indistinguibile da una svista: il
> prossimo contributore che nota che `plan_pac_allocation` non è importabile
> dal package lo aggiungerà volentieri, senza accorgersi che così il package
> importa SCIP. Perciò la decisione è (a) scritta nella docstring di
> `planner.py` dove verrà letta, e (b) **resa una proprietà**: un test in
> **subprocess** asserisce `"pyscipopt" not in sys.modules` dopo l'import del
> package. Subprocess perché in-process il modulo è già caricato dalle suite
> sorelle e l'asserzione sarebbe vacua — la solita forma "passa perché non ha
> mai valutato niente". È la regola R2 (rendere la regola inviolabile invece
> di documentarla) applicata a un grafo di import invece che a un validator.

**~~Il solver gira anche quando decide l'oracolo — forzato dal contratto, non
scelto.~~ ⛔ RITIRATO — vedi §16.14 «due difetti veri» (Difetto A).** Quanto
segue è la conclusione **sbagliata** che avevo tratto il 2026-09-18 alle
18:39, lasciata scritta apposta perché il registro sia verificabile:

> `ReportedFloatingSolverEvidence.stages` è `min_length=1`
> (`schemas/pac_allocator.py:1505`), e ogni risultato ready lo richiede: senza
> almeno uno stage di evidenza il risultato non è emettibile. Registrato come
> **costo noto, non difetto**, con la mitigazione che lo rende limitato: il
> percorso oracolo si prende solo quando
> `estimate_oracle_domain_size(view) <= MAX_EXHAUSTIVE_ORACLE_CANDIDATES`, cioè
> esattamente sui domini piccoli dove una corsa ridondante del solver costa
> poco. Il costo **non può crescere con la scala**, perché a scala l'oracolo non
> viene consultato affatto.

**Perché era sbagliata**: `min_length=1` vincola quella *variante* di
evidenza, ma `PlannerSolverEvidence` è una **union**, e
`_validate_stop_evidence` pretende evidenza floating solo quando
`stop_reason != "completed"`. `completed` + `SolverNotRunEvidence` è legale, e
`SolverNotRunReasonCode` ha un **solo** valore — `allocation.solver_not_required`
— cioè il contratto prevedeva esplicitamente questo percorso. Il solver non era
affatto obbligatorio: era una mia scelta implementativa, e sbagliata, che
rendeva `ready_infeasible` inemettibile e faceva **sollevare** il planner su un
input legittimo.

**Fixture con ottimo degenere: requisito permanente, non aneddoto.** Il bug
del no-op (costruivo `PacIncumbentSolution`, che pretende ≥1 riga ordine,
*prima* di verificare il no-op) è stato preso dalla prima esecuzione
end-to-end perché la fixture dello schema ha un **ottimo degenere**: €5
contro un prezzo unitario di €10, quindi non fare nulla è corretto. Se avessi
esercitato solo uno scenario con un acquisto fattibile, il difetto sarebbe
arrivato in produzione e avrebbe fallito **la prima volta che un utente è a
corto di cassa** — che per uno strumento PAC non è un caso raro ma il più
comune a inizio mese. Perciò la suite permanente **deve** mantenere una
fixture il cui ottimo è no-op, e il test deve asserire `ready_no_op` **con**
`optimal_proven`, non semplicemente "nessuna eccezione".

**Quando si devia da uno scope concordato perché lo scope era sbagliato, va
detto esplicitamente.** Avevo riportato `__all__ == ["plan_pac_allocation"]`
senza nominare il file, mentre lo scope diceva "esportata da `__init__.py`":
letti insieme suggerivano che la superficie del *package* esportasse ormai
solo il planner, cioè che gli export P1 fossero stati persi. Sono serviti tre
comandi al coordinatore per stabilire che la verità era migliore di entrambe
le letture. **La deviazione è la parte interessante del report**, non un
dettaglio da far dedurre da un path da ricostruire.

#### Debito registrato (non rimosso, non ammorbidito)
| Item | Stato | Trigger |
|---|---|---|
| `stop_reason`: i rami `time_limit`/`node_limit` sono esercitati su uno stage **truccato** (`dataclasses.replace` su un `SolverRunResult` reale), non su una terminazione per limite genuina | Accettato per 5a | **Filato contro G5.** `build_stop_reason` è funzione pura degli stati di stage, quindi la *mappatura* è coperta fedelmente; ciò che manca è una terminazione reale. Forzare SCIP a un limite su uno scenario giocattolo non è deterministico e un test costruito ad arte sarebbe fragile. Una campagna a scala rappresentativa (G5) rende disponibile una terminazione vera **gratis** invece che manufatta. Trasforma un asterisco permanente in un task con un innesco. |
| Ordine ascendente **per sezione** provato in modo non vacuo solo sulla sezione BUY (2 righe); l'unicità globale è provata su tutte e tre le sezioni | Accettato per 5a | La proprietà protegge da un refactor futuro che rinumeri per sezione, e una sezione a una riga non può rilevarlo. **Quando le fixture di 5b avranno una sezione funding o FX multi-riga, estendere lì l'asserzione** invece di aggiungere una fixture solo per questo. |
| Path a scala ridotta della display projection coperto solo via il suo raise, non via una proiezione riuscita a scala più grossolana | Accettato così | Nessun follow-up. |

> Un checkpoint che elenca ciò che **non** ha dimostrato vale più di uno che
> lascia intendere di aver dimostrato tutto.

#### Rami irraggiungibili: documentare, non rimuovere

`terminating_decimal_text` contiene due rami (`rstrip("0")` e il fallback a
frazione vuota) **irraggiungibili** per un `ExactRatio` canonico. Decisione:
documentarli in-code con **l'argomento di raggiungibilità per esteso**, non
con la parola "unreachable".

Motivazione generalizzabile: un ramo irraggiungibile **non documentato** è
instabile in un modo preciso — comparirà in ogni coverage report da qui in
avanti, e **entrambe** le azioni disponibili sono cattive. Cancellarlo fa
sparire una difesa reale sulla forza di un numero di copertura. Coprirlo
obbliga a costruire un `ExactRatio` non normalizzato, cioè a scrivere un test
che **asserisce comportamento per un input che il tipo vieta**, fissando un
contratto che nessuno ha progettato e facendo sembrare una regressione un
futuro irrigidimento dell'invariante. Documentarlo chiude la questione una
volta sola. L'argomento va scritto perché, se `ExactRatio` smettesse di
normalizzare in costruzione, il ramo diventerebbe vivo e il commento è
l'avviso che qualcosa si è mosso sotto.

> **Regola promossa al piano master**: una mutazione sopravvissuta è evidenza
> di una lacuna nei test **solo se la mutazione cambia davvero il
> comportamento**. Corollario altrettanto importante: *verificare che la
> propria mutazione sia una mutazione vera prima di trarre qualunque
> conclusione dalla sua sopravvivenza*, perché una mutazione rotta è
> indistinguibile da una robusta al livello di "la suite è diventata rossa?".
> Ordine corretto: dimostrare per argomento, **poi** confermare
> empiricamente — il solo controllo empirico sarebbe compatibile con "nessun
> campione ha colpito il ramo".

> **Tecnica da nominare** (test-author, Mutation A): disabilitare la guardia
> di produzione così che il rosso venga dalla **ri-derivazione indipendente**
> dell'invariante da parte del test. *Un test che ri-deriva l'invariante è un
> test; un test che si limita a osservare che l'asserzione di produzione non
> scatta è un'eco.* La regola del mutation-test esiste perché il secondo tipo
> passa anche quando l'asserzione viene saltata in silenzio.

#### Vincoli forzati dallo schema (non scelte)

- **Gli stage `tie:<decision_id>` vanno filtrati da `solver_evidence`**: il
  `ObjectiveCode` wire non ha un membro `tie:*`, quindi non esiste
  alternativa. Va commentato nel codice al punto del filtro, perché
  altrimenti è silenzioso: un lettore che vede meno stage di evidenza di
  quanti il solver ne ha eseguiti sospetterebbe perdita di dati.
- **`stop_reason` è determinato, non scelto**: `_validate_stop_evidence`
  (`pac_allocator.py:2680-2688`) impone `completed` ⇔ nessuno stage
  `unfinished`, che combacia esattamente con
  `SolverRunResult.finished_stage_count`. Da commentare dove vive la
  mappatura, così il prossimo lettore non la ri-deriva.

→ Step 4: [Copie dominio](plan-phase00Step4PacRebalancerDomainCopies.prompt.md)
