# Step 3 — compiler dichiarativo, SCIP, policy e proof

**Stato:** PENDING EXACT CORE AND SCIP CAPACITY.
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

→ Step 4: [Copie dominio](plan-phase00Step4PacRebalancerDomainCopies.prompt.md)
