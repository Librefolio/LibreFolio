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

→ Step 4: [Copie dominio](plan-phase00Step4PacRebalancerDomainCopies.prompt.md)
