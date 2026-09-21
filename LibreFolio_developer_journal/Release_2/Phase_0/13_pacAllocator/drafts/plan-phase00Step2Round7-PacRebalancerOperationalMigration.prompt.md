# Round 7 — PAC/Rebalancer operational migration

> **ARCHIVIO:** piano implementativo precedente, sospeso prima del codice e
> superato dal consolidamento target. L'entrypoint della suite corrente è
> [`../plan-phase00PacRebalancerTargetDesign.prompt.md`](../plan-phase00PacRebalancerTargetDesign.prompt.md).
> Ogni riferimento sotto a un piano “corrente” conserva soltanto il contesto
> storico del round in cui fu scritto.

**Status:** GATE P1 AUTHORIZED / STEP 0 REOPENED — FIXED-L2 MATHEMATICS
READY; IMPLEMENTATION FROZEN ON PRODUCT-SHAPED PAYLOAD AND SCIP
MIQP/MIQCP CAPACITY.
**Implementation:** the developer authorized implementation from clean baseline
`202e4056f2b915c055eeb8436eae765023201918`; the former PAC+Rebalancer
solver/capacity gate stopped all production/test work before Step 1. The developer
has now frozen one shared fixed-reference `L2_fixed` solver core for PAC and
Rebalancer and approved PySCIPOpt/SCIP as an additive candidate. The
mathematical contract is ready after independent review. No
production/test/dependency work resumes until the product-shaped result contract,
coordinated environment and solver capacity/probe gates close.
**Durable location:**
`LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/drafts/plan-phase00Step2Round7-PacRebalancerOperationalMigration.prompt.md`

← Previous:
[Round 6 — PAC/Rebalancer UI Blueprint](plan-phase00Step2Round6-PacRebalancerUiBlueprint.prompt.md)

**Normative product flow:**
[PAC/Rebalancer end-to-end design](pac-rebalancer-end-to-end-design.md).

**Approved UI source, ora promosso nella suite target:**
[PAC/Rebalancer UI completa](../plan-phase00PacRebalancerUiTarget.prompt.md).

Naming uses **Round 7**, not Round 6, because Round 6 is the approved UI Blueprint
phase and Round 7 is the backend/frontend migration. Gate P0 materializes this
contiguous chain:

```text
Round 5 operational design
  -> Round 6 approved UI Blueprint
  -> Round 7 operational migration
```

## 0. Problem and proposed approach

Current PAC and Portfolio Rebalancer are unreleased P1 analysis prototypes. They expose
the correct stable Tool identities, but not approved operational behavior:

- `operation="analyze"` instead of one atomic `operation="plan"`;
- theoretical PAC amounts and target gaps instead of feasible funding, FX, BUY/SELL
  instructions, costs and post-plan allocations;
- obsolete `report_currency`, `buy_grid`, `quantity_step` and `monetary_step`;
- long-form P1 editors instead of approved nine-step wizard;
- no independent Decimal evaluator, complete small-case oracle or operational solver;
- P1 docs/tests/i18n/codecs describe behavior explicitly rejected by developer.

Approach:

1. checkpoint approved design/planning state through coordinator;
2. freeze corrected v1 contract and update normative design;
3. replace P1 cleanly, preserving only stable Tool codes/component keys and reusable
   platform/UI infrastructure;
4. develop schemas, domain-copy APIs, shared frontend primitives and pure Decimal core
   in parallel after contract freeze;
5. develop solver after evaluator contract, PAC/Rebalancer views after shared shell;
6. integrate through one owner for plugin, codegen, registry, runner, i18n and
   CHANGELOG;
7. validate exact math, permissions, resource limits, desktop/mobile UX and manual
   review before integration.

## 1. Authority, baseline and hard gates

### 1.1 Source precedence

1. developer feedback and explicit UI approval in this session;
2. approved
   `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00PacRebalancerUiTarget.prompt.md`;
3. `pac-rebalancer-end-to-end-design.md`, reconciled during Gate P0;
4. this Round 7 plan;
5. current code for existing implementation truth;
6. Round 5 and earlier plans as history only.

`pac-rebalancer-operational-design.md` is a compatibility redirect to the normative
end-to-end artifact, not a second authority.

If approved Blueprint and older Round 5 text disagree, Blueprint wins for UX and
order-entry contract; math invariants remain authoritative unless Step 0 identifies a
real contradiction.

### 1.2 Recorded coordination state

| Item | Value |
|---|---|
| Worktree | `/Users/ea_enel/Documents/00_My/LibreFolio-worktrees/e-alfy-friendly-dollop` |
| Branch | `e-alfy-allocatore-pac` |
| Audited HEAD | `e38a521f068c2d1b8d743775e90711fec1326fb3` |
| Approved combined baseline | `e38a521f068c2d1b8d743775e90711fec1326fb3` |
| Target branch | `dev_release2` |
| Coordinator session | `c8328a01-f208-4ade-a352-0486d1f14de2` |
| Test port | `6153` |
| Test data dir | `/tmp/librefolio-r2-d` |
| Shared environment | `PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc` |

### 1.3 Two separate developer gates

> **Historical gate sequence:** Gate P0 and Gate P1 below were subsequently
> completed on checkpoint `202e4056f2b915c055eeb8436eae765023201918`.
> Current production freeze comes from reopened Step 0, not missing start
> authorization.

Approval of this plan authorizes **planning-state persistence only**. It does not
authorize product implementation.

Gate P0 sequence:

1. replace obsolete session SQL tasks with the Round 7 task/dependency graph;
2. materialize completed Round 6 UI plan and pending Round 7 plan in project;
3. materialize every missing approved design/decision artifact needed by that chain;
4. mark Blueprint Reviews B/C/D/final as approved; no UX change;
5. add Round 5 → Round 6 → Round 7 forward/back links;
6. update only additive planning indexes needed to expose Round 6/7 status;
7. validate planning files, enter `FROZEN`;
8. send coordinator immediate request containing developer authorization, exact
   intended planning paths and proposed checkpoint message;
9. coordinator persists planning/design state and returns commit SHA plus clean-state
   confirmation;
10. verify local planning baseline against coordinator-provided SHA;
11. ask developer explicitly whether implementation may start.

Gate P1 opens only when developer answers that second request affirmatively. No
production/test/docs implementation, test, server, DB action, API sync, staging or
history mutation occurs before Gate P1. Current coordinated workstream never commits or
stages ordinary files.

### 1.4 Runtime lane

All future runtime commands use:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
pipenv run python dev.py test \
  --test-port 6153 \
  --data-dir /tmp/librefolio-r2-d \
  <category> <action>
```

Rules:

- never ports `6040`/`6041`;
- never another workstream data dir;
- never two commands concurrently in this lane;
- file-disjoint implementation may run in parallel, but every test/build/server/DB
  command enters one serialized lane queue;
- never `server --force`;
- no dependency installation without manifest change or explicit dependency failure;
- no new solver dependency without new developer approval;
- stop exact PID for any owned server and prove port `6153` free at handoff.

## 2. Goal and non-goals

### 2.1 Goal

Deliver two operational, deterministic Tool services:

- `pac_allocator`: allocates selected funding across target Assets using
  one global discrete fixed-reference `L2_fixed` primary; `proportional` and
  `min_fragmentation` select different operational tier orders after the shared
  mathematical objective;
- `portfolio_rebalancer`: plans toward whole-portfolio targets using
  the same fixed-reference objective; `invest_only` and explicit
  `invest_and_sell` select different admissible action domains and constraints.

Both consume a complete immutable snapshot, compute without DB/provider/service
lookups, return a primary plus frozen-action BUY-only deployment plan, and
present approved desktop/mobile wizard and results. They share normalization,
constraint primitives, policy compiler, solver adapter, ledgers and Decimal
evaluator; they remain distinct products through input flow, enabled variables,
hard constraints, operational tiers, reports and UI.

### 2.2 Non-goals

- no broker order execution;
- no shorting, leverage or implicit debt;
- no hidden Broker routing;
- no automatic live-provider fetch in worker;
- no optimizer-history/Riskfolio reuse;
- no FIFO/WAC/tax-regime algorithm change;
- no tax-loss harvesting, carried-loss compensation or plusvalenza optimization;
- no multi-hop FX or rate-cycle arbitrage;
- no persistent planner profiles or Asset tax-rate column in v1;
- no proportional forced split across Brokers;
- no Broker closure/consolidation objective;
- no legacy P1 adapter, fallback, alias, dual version or compatibility route;
- no `/tools/prefill`;
- no frontend economic allocation, fee, tax, FX or order computation.

## 3. Current code truth

| Area | Current truth | Round 7 action |
|---|---|---|
| Tool platform | `ToolPlugin`, registry, catalog v2, worker/executor, diagnostics, authenticated bulk compute, fingerprints and compiled renderer checks already exist | reuse; generic-platform edit is stop condition unless proven gap |
| Public schemas | `backend/app/schemas/pac_allocator.py` exposes P1 `analyze`, reporting currency, buy grids and theoretical facts | replace root/nested types; keep no P1 union |
| Numerical service | `backend/app/services/pac_allocator/` has P1 normalize/evaluator/report only | preserve useful exact-decimal utilities only; replace P1 domain |
| Tool plugin | `backend/app/services/tool_plugins/pac_allocator.py` already publishes two services, stable codes and component keys at `1.0.0` | switch both to `plan`; keep public identities/version |
| Domain copy | `PortfolioAllocationSource*` and `build_portfolio_allocation_source` expose OWNER custody, quotes and native cash safely | extend with PMC/classifications/provenance/missing facts; no planner persistence |
| WAC/PMC | `compute_wac_iterative` already owns broker×Asset WAC computation | call from authorized domain assembly; do not duplicate/change math |
| Saved quotes | allocation source reads `PriceHistory` without provider fetch | extend read DTO; never use mutating `/assets/prices/current` |
| FX | existing FX domain owns saved rates/routes/conversion | use/extend read-only domain response with value, source and timestamp |
| Frontend P1 | `frontend/src/lib/features/tools/pac-allocator/` contains monolithic P1 wrappers/editors/results and hand-normalized source DTO | clean-break into shared planner shell + two thin Tool views |
| Client guards | current wrappers already use account generation, request sequence, abort and draft revision | preserve/generalize in shell |
| Generated client | `generated.ts`, `generated-tools.ts`, contract map and fingerprint validation already exist | regenerate once through official API sync |
| Shared inputs | `CompactCashCell`, `ExactDecimalInput`, selectors, entity modals, DataTable and ConfirmModal already mature | reuse; extract shared quantity input from TransactionFormModal |
| P1 tests | schema/service/API tests and PAC/Rebalancer E2E assert rejected analysis behavior | replace, do not retain compatibility expectations |
| P1 docs | two EN user guides explicitly describe “P1” and no-order behavior | rewrite after contract/UI stable |
| Runner | current actions include `schemas pac-analyze`, `services pac-analyze`, `api pac-tool`, `front-utility pac-tool`, `front-utility rebalancer-tool`, `front-utility component-unit` | rename only P1 schema/service actions; retain API/E2E action names |
| DB | no persisted operational Broker profile or Asset tax rate | no migration in v1 |

## 4. Approved product and UX contract

### 4.1 Two products, shared primitives

PAC and Rebalancer retain distinct service codes, routes, wrappers, labels, strategies
and result semantics. They share:

- immutable scenario model;
- numerical normalization/evaluation/ledger;
- funding/Broker/Asset/route/FX editors;
- wizard navigation and stale guards;
- operational result tables/charts;
- test helpers and docs concepts.

No public mode switch merges them into one Tool.

### 4.2 Nine-step input flow

1. **Scenario:** Tool-specific scope, as-of date, valuation currency.
2. **Liquidity and funding sources:** new cash, existing Broker/account cash,
   manual account; select exact amount, not necessarily full balance.
3. **Operational Brokers:** existing or manual Broker used for BUY/SELL.
4. **Assets/current holdings:** canonical Assets or manual Assets; Rebalancer custody
   per Broker remains exact.
5. **Asset×Broker eligibility and constraints:** BUY/SELL eligibility, priority,
   min-if-operated, required minimum and typed caps.
6. **Target:** PAC contribution target or Rebalancer final whole-portfolio target.
7. **Potential FX:** explicit single-hop pairs, spot provenance/age, spread, safety
   margin and fee.
8. **Strategy:** PAC policy or Rebalancer trade mode.
9. **Review snapshot:** complete immutable payload, then one Tool compute.

Back/forward navigation preserves draft. Compatible upstream edits mark dependent
steps `Da rivedere`. Structural edits that delete dependent configuration open
`ConfirmModal` listing exact data to remove. No silent reset.

### 4.3 Approved order-entry enum

Round 5 D08 is superseded. Input per Broker/currency is:

```text
order_instruction_kind =
  "whole_quantity"
| "monetary_amount"
```

- `whole_quantity`: Broker expects integer share count; implicit unit is `1`; no
  quantity step.
- `monetary_amount`: Broker expects monetary notional in debit/trade currency;
  `order_amount_step` is required and means minimum increment accepted by Broker UI.
- no `fractional_orders_allowed`;
- no `quantity_step`;
- no separate fractional BUY/SELL booleans;
- existing fractional inventory remains exact and is never rounded to new-order mode.

Output mirrors same discriminant:

```text
WholeQuantityInstruction {
  kind="whole_quantity",
  quantity
}

MonetaryAmountInstruction {
  kind="monetary_amount",
  amount,
  estimated_quantity
}
```

### 4.4 Results contract

Shared result hierarchy:

1. availability plan-level e outcome/proof/stop/metrics per soluzione;
2. base versus residual-optimized plan;
3. Asset allocation comparison;
4. Type/Sector/Geography before-target-after;
5. Asset summary;
6. foldable operational plan:
   - funding/transfers;
   - FX conversions;
   - one Broker order panel per Broker;
7. exact ledgers, constraints, reasons and diagnostics, including PAC
   `base_processing_rank`, route tie reason and one-time fee/FX attribution.

Visuals approved:

- Asset matrix mini-bars;
- Type/Sector aligned tapered ribbons:
  - PAC `Target → Dopo`;
  - Rebalancer `Prima → Target → Dopo`;
- paired synchronized Geography maps plus optional diverging `Dopo - Target`;
- standard Sankey only for real Funding→Broker→FX→order flows;
- `DataTable` + `ColumnVisibilityToggle` for desktop detail;
- same data projected as cards/accordions on mobile;
- Asset/Broker icons;
- default label `Valore investito`; `Valore mid` only optional audit column.

## 5. Pre-implementation decisions

| ID | Decision | Status / gate |
|---|---|---|
| D01 | PAC/Rebalancer remain distinct public services and UIs; core shared | frozen |
| D02 | One complete snapshot, one compute, one result; no solver preview | frozen |
| D03 | Worker is synchronous/pure and performs no DB/provider/domain lookup | frozen |
| D04 | P1 is unreleased: remove obsolete code/tests/docs/i18n, no compatibility | frozen |
| D05 | Public Tool contract stays `1.0.0`; implementation/UI versions stay valid SemVer | frozen |
| D06 | Canonical Asset identity aggregates Brokers; names never establish identity | frozen |
| D07 | Cash remains source/Broker/currency native; only selected amount enters plan | frozen |
| D08 | New contributions remain separate funding sources; no double posting | frozen |
| D09 | Funding source and operational Broker are separate roles; output lists transfers | frozen |
| D10 | Existing/manual sources and Brokers both supported; manual is scenario-only | frozen |
| D11 | Broker settings are per-run; no DB migration/profile endpoint in v1 | frozen |
| D12 | `order_instruction_kind` enum replaces all fractional booleans/quantity step | frozen by approved UI |
| D13 | BUY/SELL fee profiles are independent: fixed + rate + min/max percent component | frozen |
| D14 | FX is declared single-hop, coupled debit/credit; spread, fee, safety margin explicit | frozen |
| D15 | PAC primary is a global discrete fixed-reference `L2_fixed` solve; no continuous-QP+floor and no deterministic floor authority | supersedes prior D15; frozen 2026-09-16 |
| D16 | Rebalancer modes: `invest_only` imposes SELL=0; `invest_and_sell` explicitly enables constrained SELL. They define admissible actions, not objective weights | corrected/frozen 2026-09-15 |
| D17 | Deployment result freezes every primary action and adds BUY only; it minimizes `U` then resulting `L2_fixed`, may worsen score visibly, and promotes any candidate that dominates an unproven primary incumbent | supersedes prior D17; frozen 2026-09-16 |
| D18 | Tax schedule: SELL fee → positive gain → rounded reserve → net reusable proceeds | frozen |
| D19 | `withholding_kind` derived from regime; carried losses informational in v1 | frozen |
| D20 | UI Blueprint A–D/final is approved; no aesthetic gate remains | frozen |
| D21 | Reuse/generalize existing UI primitives; migrate transaction quantity editor first | frozen |
| D22 | PySCIPOpt/SCIP is the approved additive candidate for shared PAC/Rebalancer fixed-L2 MIQP plus convex-MIQCP lexicographic tiers; Riskfolio and SciPy remain unchanged | frozen 2026-09-16 |
| D23 | No solver probe, install or manifest/lock change starts until every coordinated lane is frozen and the developer performs or explicitly authorizes the shared-environment update | hard stop |
| D24 | Keep current API/E2E runner action names; replace only obsolete P1 schema/service actions | frozen |
| D25 | One shared writer owns generated client, registry, runner, i18n and CHANGELOG | frozen |
| D26 | PAC primary: `L2_fixed → U → policy tiers → tie`; proportional orders route/cost/rows, min-fragmentation orders split/rows before route/cost. Deployment: `U → L2_fixed → incremental cost/rows → tie` | supersedes prior D26; frozen 2026-09-16 |
| D27 | Atomic payload/result must fit fixed Tool ceilings: 131,072 input bytes, 262,144 result bytes, 4 s soft and 5 s hard execution | hard stop |
| D28 | Parallel workstreams share one runtime lane; implementation may overlap, validation is serialized | frozen |
| D29 | Runner owner registers final test paths before each workstream's first selector run; Step 10 audits rather than first wiring them | frozen |
| D30 | Solver/Decimal money deltas within one currency minor unit are canonicalized; physical cash, inventory, min/max and step constraints remain exact after normalization | corrected/frozen 2026-09-15 |
| D31 | Route priority is an operational tier after `L2_fixed/U`, never a greedy Asset envelope or hidden target; activation costs are charged once and attribution is reported | supersedes prior D31; frozen 2026-09-16 |
| D32 | Availability is plan-level; outcome/proof/stop/metrics are per search result. Both PAC results use the strict search union and exact Decimal incumbent validation | supersedes prior D32; frozen 2026-09-16 |
| D33 | Required PAC minima are global hard constraints; only a complete Decimal conflict witness or exhaustive oracle permits `infeasible_proven` | supersedes prior D33; frozen 2026-09-16 |
| D34 | Both Tools use `L2_fixed=Σ_a(V_a_final-w_aF_ref)²` in valuation-currency squared units. Actual-final percentages, D∞ and D1 are diagnostics only | supersedes prior D34; frozen 2026-09-16 |
| D35 | `F_ref = current invested value + selected route-reachable funding` fixes target and accounting; SELL proceeds are internal. `U = F_ref - F_final` reconciles free cash, physical reserves, economic loss and signed bounded rounding | supersedes prior D35; frozen 2026-09-16 |
| D36 | `invest_and_sell` freezes invest-only; every SELL is fixed-target-overweight, funding-only and locally quantum-irriducible for its fixed incremental BUY plan. The restricted phase reuses `L2_fixed → U → turnover → cost → rows/splits → tie`; local/global SELL minimality remain distinct | updated/frozen 2026-09-16 |
| D37 | Rebalancer deployment freezes every primary action including SELL, adds BUY only, then orders `U → L2_fixed → incremental cost/rows → total tie` | supersedes prior D37; frozen 2026-09-16 |
| D38 | Constraint primitives are shared. PAC policies reorder operational tiers; Rebalancer cards define action domains. Primary and deployment results are automatic | updated/frozen 2026-09-16 |
| D39 | Every published incumbent is Decimal-feasible with an exact evaluated objective tuple. Floating solver `optimal/infeasible` is never promoted: public proof is at most `gap_bounded/not_proven`; exact optimality needs exhaustive oracle or coefficient-safe score-lattice closure, and exact infeasibility needs deterministic conflict witness or exhaustive oracle | frozen 2026-09-15 |
| D40 | Every final Asset×Broker quantity and aggregate Asset value is nonnegative; Rebalancer additionally requires `F_final>0` | frozen 2026-09-16 |
| D41 | PolicyCompiler emits declarative variables/constraints/objective stages for solver-backed policies; a deterministic dispatcher remains only for genuinely closed-form policies; both share normalized scenario and Decimal evaluator | frozen 2026-09-16 |
| D42 | The first fixed-L2 tier is convex MIQP. After exact L2 proof, its convex sublevel equals the optimum face and later tiers are convex MIQCP/MISOCP. Without exact proof it is only a non-worsening incumbent ceiling: any lower-L2 candidate restarts the cascade, and conditional tiers cannot prove the global tuple. Nonconvex equality-freezing is not used | corrected/frozen 2026-09-16 |
| D43 | One scenario may mix whole-quantity and monetary-amount routes. Monetary orders remain integer counts of native `order_amount_step` (possibly the currency minor unit); fractional Asset quantity is derived. Continuous relaxation is bound/warm-start only, never authoritative rounding | frozen 2026-09-16 |
| D44 | `U=F_ref-F_final` is exact and may be slightly negative only through bounded favorable posting rounding; require `U≥-|A_round|max`. Cash-free/reserve/loss terms remain nonnegative and the signed rounding term reconciles the difference | corrected/frozen 2026-09-16 |

**Open product decisions/gates:** codegen-compatible result shape below
`262,144` bytes; coordinated PySCIPOpt dependency update; convex MIQP/MIQCP
capacity, packaging, cancellation and exact-oracle benchmark. SCIP adoption as candidate
does not itself authorize install or probe. Any later change to units, objective
tiers, proof semantics, order enum, fee/FX/tax schedule or approved visuals
reopens Step 0 and math/UI review.

## 6. Public and internal contracts

### 6.1 Exact wire rules

- all financial numbers are finite fixed-point Decimal strings;
- UI accepts locale comma/dot, serializes canonical dot;
- money = Decimal string + ISO 4217 currency;
- quantity = Decimal Asset units;
- raw price = money per positive integer `quote_base_quantity`;
- target/fee/spread/safety/tax rate = ratio, not 0–100 percentage;
- timestamps = timezone-aware ISO 8601;
- as-of dates = ISO date;
- nested objects reject extras;
- exclusive alternatives use discriminated unions;
- no JSON float enters normalized/evaluator domain.

#### 6.1.1 Capacity budget

Step 0 must prove a worst-case compact-JSON witness within platform ceilings before
public schema implementation. Minimum supported-domain target:

| Dimension | Minimum v1 cap |
|---|---:|
| Assets/targets | 32 |
| operational Brokers | 8 |
| funding sources | 16 |
| Asset×Broker routes | 64 |
| distinct currencies | 8 |
| explicit FX facts | 24 |
| orders per solution | 64 |
| typed issues | 256 |

Step 0 may raise these caps after measurement. It may not lower them or omit output
fields to fit bytes without developer approval. Required witnesses:

- maximum valid input serializes to `<= 131_072` UTF-8 bytes;
- maximum result with both solutions serializes to `<= 262_144` UTF-8 bytes;
- schema export itself remains within supported Tool profile;
- solver wall budget leaves time for cold import, normalization, Decimal evaluation,
  report serialization and output revalidation inside 4 s soft / 5 s hard limits.

Initial execution budget to prove: solver native calls total `<= 2.5 s`, non-solver
worker phases total `<= 1.0 s`, leaving at least `0.5 s` before soft timeout. A miss
reopens supported-domain/platform scope; no silent cap reduction or platform edit.

### 6.2 Public inputs

```text
PacPlanInput
├── operation = "plan"            # required, no default
├── scenario: PlanningScenario
└── pac_policy = "proportional" | "min_fragmentation"

RebalancePlanInput
├── operation = "plan"            # required, no default
├── scenario: PlanningScenario
└── trade_mode = "invest_only" | "invest_and_sell"
```

```text
PlanningScenario
├── scenario_id
├── as_of_date
├── valuation_currency
├── funding_sources[]
├── funding_routes[]
├── trading_brokers[]
├── assets[]
├── fx_facts[]
└── targets[]
```

Funding unions:

```text
NewExternalFunding {
  source_kind="new_external",
  source_id, label, selected_money
}

ExistingAccountFunding {
  source_kind="existing_account",
  source_id, broker_id?, available_money, selected_money, provenance
}

ManualAccountFunding {
  source_kind="manual_account",
  source_id, label, declared_available_money, selected_money
}

FundingRoute {
  source_id,
  destination_broker_id,
  currency,
  priority
}
```

Invariants:

- source available/selected currencies match;
- `0 <= selected <= available` when maximum is known;
- new funding has no fake pre-existing balance;
- same source is posted once even when it is also an operational Broker;
- `funding_routes` names only selected destination Brokers/currencies;
- funding priority is explicit; cash already on the destination Broker precedes
  transfers, then priority and stable IDs break ties;
- unselected cash never enters objective/ledger.

Trading Broker union:

```text
ExistingTradingBroker {
  broker_kind="existing_broker",
  broker_id, domain_snapshot, run_configuration
}

ManualTradingBroker {
  broker_kind="manual_broker",
  scenario_broker_id, label, run_configuration
}
```

`BrokerRunConfiguration` contains:

- currencies and debit/credit currency;
- `fx_mode = native_currency_required | auto_convert_on_buy`;
- `order_instruction_kind`;
- `order_amount_step` only for `monetary_amount`;
- BUY and SELL fee profile per side/currency;
- `tax_regime = administered | declarative_free`;
- carried-loss amount/currency/as-of, default zero and informational;
- allowed funding links.

Fee profile:

```text
FeeProfile {
  currency,
  fixed_amount,
  rate,
  rate_minimum_amount?,
  rate_maximum_amount?
}
```

Asset snapshot:

```text
PlanningAsset
├── asset_key
├── asset_id?
├── display facts/icon
├── quote {raw_price, currency, quote_base_quantity, source, observed_at}
├── classifications {type[], sector[], geography[]}
├── capital_gains_tax_rate
├── holdings_by_broker[]
└── broker_routes[]
```

Holding:

- Broker;
- exact custody quantity;
- PMC per unit, currency, as-of and provenance;
- existing fractional quantity preserved;
- no second tax field.

Route:

- Asset/Broker identity;
- BUY eligibility and SELL eligibility;
- priority integer;
- side/debit currency;
- side-specific min-if-operated;
- optional required hard minimum;
- cap discriminant: none, quantity or notional;
- monetary amount step is a positive integer multiple of currency minor unit;
- no inferred route to unselected Broker.

Target invariants:

- one Decimal weight per canonical Asset, `w_a >= 0`;
- exact Decimal `sum(w_a) = 1`, otherwise `invalid`;
- `T_a = w_a * F_ref` is not rounded internally; for PAC,
  `F_ref = K_reachable` because `V_current_invested = 0`;
- positive target requires a usable quote; missing/non-finite price is
  `needs_input`, never silent omission;
- `K_reachable` includes only selected cash with a declared structural path to
  a BUY route of an Asset with positive weight and usable quote.

FX fact:

```text
FxFact {
  broker_id,
  from_currency,
  to_currency,
  mid_rate,
  source,
  observed_at,
  spread_rate,
  fx_buffer_rate,
  fixed_fee?
}
```

`fx_buffer_rate` is reserved source cash, not fee or investment. Result exposes
`fx_buffer_amount`.

### 6.3 Public output

Use a strict availability-discriminated union so impossible states cannot be built:

```text
PlanningInputFailure {
  availability = "needs_input" | "invalid" | "unsupported",
  issues[],
  normalized_snapshot_digest?
}

PlanningReadyResult {
  availability = "ready",
  base_result: SearchResult,
  variant_result?: SearchResult,
  issues[],
  normalized_snapshot_digest
}

SearchResult =
  SearchExactOptimalPlan
  | SearchBoundedPlan
  | SearchUnprovenPlan
  | SearchNoIncumbent
  | SearchDeterministicInfeasible
  | SearchOracleInfeasible

SearchPlanCore {
  method,
  stop_reason = "completed" | "time_limit" | "node_limit" | "cancelled",
  incumbent_validation = "decimal_verified",
  limits,
  objective_values,
  target_deviation,
  cash_deficit,
  rebalancer_accounting?,
  sell_minimality?,
  solution
}

SearchExactOptimalPlan = SearchPlanCore & {
  outcome = "no_op" | "incumbent_found",
  proof = "optimal_proven",
  stop_reason = "completed",
  proof_source = "exhaustive_oracle" | "score_lattice_closure",
  exact_proof_evidence,
  solver_evidence?
}

SearchBoundedPlan = SearchPlanCore & {
  outcome = "incumbent_found",
  proof = "gap_bounded",
  solver_evidence,
  objective_bounds,
  gap
}

SearchUnprovenPlan = SearchPlanCore & {
  outcome = "incumbent_found",
  proof = "not_proven",
  solver_evidence?,
  objective_bounds?,
  gap?
}

SearchNoIncumbent {
  method,
  outcome = "no_incumbent",
  proof = "not_proven",
  stop_reason = "completed" | "time_limit" | "node_limit" | "cancelled",
  solver_evidence,
  limits,
  issues[]
}

SearchDeterministicInfeasible {
  method,
  outcome = "infeasible_proven",
  proof = "infeasibility_proven",
  stop_reason = "completed",
  proof_source = "deterministic_conflict",
  conflict_witness,
  limits
}

SearchOracleInfeasible {
  method,
  outcome = "infeasible_proven",
  proof = "infeasibility_proven",
  stop_reason = "completed",
  proof_source = "exhaustive_oracle",
  oracle_evidence,
  limits
}

SolverEvidence {
  solver_name,
  solver_version,
  reported_status,
  settings,
  tolerances,
  tier_bounds[] {
    tier,
    scope = "global" | "incumbent_face",
    conditioned_on?,
    primal_bound?,
    dual_bound?,
    absolute_gap?,
    relative_gap?,
    units
  }
}
```

Rules:

- missing required fact → `needs_input`;
- supplied contradiction/malformed relationship → `invalid`;
- understood but outside supported domain → `unsupported`;
- hard explicit constraints can yield `infeasible_proven` only with a complete
  Decimal conflict witness or exhaustive exact oracle; greedy or floating-solver
  failure is never proof;
- low cash/no useful route/min-if-operated not reached normally yields `no_op`;
- every published search plan, including an empty incumbent, has
  `incumbent_validation=decimal_verified`; this certifies money, constraints,
  accounting and exact objective tuple, not global optimality;
- search `no_op` requires `optimal_proven` from `exhaustive_oracle` or
  `score_lattice_closure`; an unproved empty incumbent is
  `incumbent_found/gap_bounded|not_proven` with `operational_change=false`;
- floating solver `optimal` maps at most to `gap_bounded` with raw bounds,
  tolerances, version/settings, or to `not_proven`;
- floating solver `infeasible` without exact closure maps to
  `no_incumbent/not_proven/completed`, never `infeasible_proven`;
- timeout with incumbent never says `optimal_proven`;
- timeout without incumbent is `no_incumbent/not_proven`;
- `gap_bounded` requires `solver_evidence` with tier units, raw primal/dual
  bounds, gaps, tolerances, version and settings; absent/incomparable evidence
  degrades to `not_proven`;
- `optimal_proven` requires exhaustive exact enumeration or a documented
  coefficient-safe reachable-score closure for every normative tier and is the
  only SearchPlan state carrying `proof_source`;
- `infeasible_proven` requires `deterministic_conflict` or `exhaustive_oracle`;
  the former carries exactly `conflict_witness`, the latter exactly
  `oracle_evidence`;
- `completed` is a stop reason, never proof by itself;
- crash, output validation, cleanup or platform timeout remains Tool error;
- `base_result` is always present when `availability=ready` and represents the
  primary;
- `variant_result` runs after a primary incumbent, including an exact empty
  incumbent; no deployment runs after primary `infeasible_proven` or
  `no_incumbent`;
- deployment may equal primary with exact zero delta;
- both results have independent outcome/proof/stop/bounds;
- if deployment has lower `L2_fixed` than an unproven primary incumbent, promote
  it and recompute the pair rather than publish it as a degrading variant;
  repeat over the finite domain while budget remains; after a promotion without
  time to rebuild a coherent pair, publish the best primary as `not_proven`,
  omit `variant_result` and emit an explicit issue;
- Rebalancer accounting reports `F_ref`, `F_final`, `U`, free cash, physical
  reserves, economic loss and signed rounding adjustment;
- Rebalancer SELL claims report row quantum/counterfactual plus local/global
  minimality separately:
  `sell_minimality.local=irreducible|not_applicable` and
  `sell_minimality.global=proven|gap_bounded|not_proven|not_applicable`;
  local irreducibility never maps to global proof, and floating solver status
  never maps global SELL minimality to `proven`.

Each solution includes:

- funding and transfer actions;
- coupled FX actions;
- Broker plans and orders;
- Asset-level target/mid-investment summaries split into attributed cost,
  reserved buffer, physical free cash/reasons and signed rounding adjustment;
- fixed target, residual and `L2_fixed`; actual-final percentage, D∞/D1
  diagnostics; route/tie reason and one-time activation attribution;
- cash ledgers per Broker/currency;
- Rebalancer actual final percentages, D∞pct/D1pct diagnostics, `F_ref/U`
  reconciliation and frozen-action delta between primary/deployment profiles;
- before/target/after Asset and classification exposures;
- fees, spread cost, tax reserve and FX safety margin;
- active constraints and explanations.

## 7. Mathematical model and solver gate

### 7.1 Authoritative layers

1. **Normalizer:** parses/validates wire strings into frozen dataclasses.
2. **Independent Decimal evaluator:** evaluates any complete candidate and owns all
   monetary truth/status checks.
3. **Solver adapter:** proposes candidates and bounds; never self-certifies.
4. **Reporter:** serializes evaluator-approved facts.

Evaluator imports no solver module. Solver candidate is always re-evaluated from raw
decision variables before publication.

#### 7.1.1 Notation and units

This is the local implementation notation. Public field names remain those in
§6; the end-to-end design contains the full derivations.

| Symbol | Meaning | Unit/domain |
|---|---|---|
| `A`, `a` | target Asset set and one canonical Asset | finite ID set |
| `B`, `b` | authorized Broker set and one Broker | finite ID set |
| `C`, `c,d` | native currencies and source/destination currency | ISO currency |
| `S`, `s` | selected funding sources | finite ID set |
| `R`, `r` | executable order routes; each route fixes Asset, Broker, side, currency and instruction kind | finite ID set |
| `J`, `j` | explicitly authorized directed FX legs | finite acyclic edge set |
| `v` | valuation currency used by all cross-Asset scores | one currency in `C` |
| `μ_c` | minor unit of currency `c` | native currency, e.g. `0.01 EUR` |
| `ρ_{c→d}` | approved FX conversion rate | destination currency / source currency |
| `w_a` | target weight of Asset `a`; `Σ_a w_a = 1` exactly | dimensionless Decimal |
| `h^0_{ab}` | initial economic quantity of Asset `a` at Broker `b` | Asset quantity |
| `p^{mid}_{r}` | route price used for economic valuation | route currency / Asset quantity |
| `Δq_r`, `Δm_r` | quantity step or monetary step of route `r` | Asset quantity or route currency |
| `C^0_{bc}` | selected initial spendable cash at Broker `b`, currency `c` | native currency |
| `K^{cap}_{sbc}` | selectable funding cap from source `s` to Broker `b`, currency `c` | native currency |
| `fee_r(·)`, `tax_r(·)` | approved piecewise fee and SELL-tax-reserve policies | route currency |

Every monetary parameter crossing currencies is converted once into `v` using
the immutable input snapshot. Money in a native ledger remains in its native
currency. Quantity, money and dimensionless ratios are never added to one
another. `L2_fixed` is therefore measured in `v²`, not `%²`.

The authoritative financial actions are discrete quantum counts:

| Variable | Meaning | Domain |
|---|---|---|
| `t_{sbc}` | funding transferred from source `s` to Broker `b` in `c` | nonnegative integer multiples of `μ_c` within source/route caps |
| `f_j` | source-currency debit of FX leg `j` | nonnegative integer multiples of source `μ_c` |
| `x_r^{BUY}`, `x_r^{SELL}` | instruction quanta on route `r` | nonnegative integer |
| `y_r^{BUY}`, `y_r^{SELL}` | route/side activation for fixed fee, minimum and row counting | binary |

For `whole_quantity`, `x_r Δq_r` is quantity. For `monetary_amount`,
`x_r Δm_r` is the submitted native-currency amount and the evaluator derives the
economic quantity from that amount, price and provider rule without rounding the
pre-existing inventory. Fractional SELL likewise uses its explicit quantity
step. There is no authoritative unconstrained floating financial action.
SCIP may represent coefficients and relaxations in binary floating point, but
the normalized inputs and replayed action quanta remain exact Decimal values.

Derived, never independently editable, values include:

| Symbol | Definition |
|---|---|
| `h^{final}_{ab}` | initial quantity plus evaluated BUY quantity minus evaluated SELL quantity |
| `V^0_a`, `V^{final}_a` | initial/final economic mid value of Asset `a` in `v` |
| `F_ref` | fixed accounting reference defined in §7.5 |
| `T_a` | fixed monetary target `w_a F_ref` |
| `r_a` | signed target residual `V^{final}_a - T_a` |
| `F_final` | `Σ_a V^{final}_a` |
| `U` | accounting shortfall `F_ref - F_final` |
| `C^{final}_{bc}` | final physical cash in one Broker×native-currency ledger |
| `L2_fixed` | `Σ_a r_a²` |

#### 7.1.2 Mathematical syntax

- A subscript selects an entity: `V_a` is one Asset value and `C_{bc}` one
  Broker×currency ledger. A superscript such as `0`, `final`, `BUY` or `SELL`
  selects time or side.
- `Σ_{a∈A}` means “sum once over every canonical target Asset”.
- `∀a∈A` means the following hard constraint must hold for every Asset.
- `x≥0` means zero is admitted and negative holdings, cash or action quantities
  are not.
- `f(x)²` is a square; its unit is the square of `f`'s unit.
- `→` in an objective is lexicographic priority, never arithmetic addition and
  never an implicit weight.

Normative objective notation is:

```math
x^* = \operatorname*{argmin}_{\mathrm{lex},\,x\in X}
      \left(f_1(x),f_2(x),\ldots,f_k(x)\right)
```

`X` is the hard-feasible action domain compiled from one normalized scenario.
The executor performs separate solver stages:

1. minimize `f₁`;
2. Decimal-replay the incumbent and retain the exact value `f̄₁`;
3. constrain `f₁≤f̄₁` and minimize `f₂`;
4. repeat for every tier.

If `f̄_i` is exactly proved optimal, `f_i≤f̄_i` identifies the exact prior
optimum face without a nonconvex equality. If it is only an incumbent,
`f_i≤f̄_i` is an incumbent ceiling: subsequent bounds and results are explicitly
conditioned on that ceiling. Any later candidate with a lower earlier-tier value
is promoted, Decimal-replayed and restarts the cascade. No weighted sum may
replace these stages, because a hidden coefficient would change the product
policy. Maximizing invested capital is represented by minimizing `U`.

### 7.2 Native-ledger conservation

For each Broker/currency, evaluator derives spendable closing cash:

```text
spendable_final =
    selected_initial_cash
  + inbound_transfers
  + coupled_fx_credits
  + gross_sell_proceeds
  - outbound_transfers
  - coupled_fx_debits
  - buy_notional
  - buy_fees
  - sell_fees
  - broker_withheld_tax
  - self_reserved_tax
  - fx_fees
  - fx_buffer_amount
>= 0
```

Physical closing cash is a separate identity:

```text
physical_final =
  spendable_final
  + fx_buffer_amount
  + self_reserved_tax
```

`broker_withheld_tax` has left the account and is not added back. Evaluator reconciles
both relations separately; reserved cash is never counted as both outflow and final
physical cash in one equality.

Funding, transfers and FX source debits are native-minor-unit decision amounts.
For a required canonical destination amount, the FX source debit is the native
ceiling of the continuous rate quotient; the coupled destination credit is rounded
once with `ROUND_HALF_UP`. Order debits/credits, fees, FX credit/fee/buffer and tax
reserve form the closed rounded-posting set. Spendable final may therefore include
unspent selected cash or net SELL proceeds; origin does not change the `U` identity.

For an authorized leg `j:c→d`, with spread `s_j`, the executable rate and
coupled postings are:

```math
\rho^{eff}_{c\to d}=\rho_{c\to d}(1-s_j),\qquad 0\le s_j<1
```

```math
f_j\in\mu_c\mathbb{Z}_{\ge0},\qquad
\operatorname{credit}_j=
\operatorname{round}_{\mu_d,\mathrm{HALF\_UP}}
\left(f_j\rho^{eff}_{c\to d}\right)
```

To satisfy a required destination amount, `f_j` is at least the source-minor-unit
ceiling of the inverse-rate quotient. Any posted excess stays visible as
destination cash. `fx_buffer_amount` is rounded once in source currency,
remains physical source cash and is never fee, investment or double debit.

Hard invariants:

- no cash/contribution double count;
- no FX credit without coupled debit;
- no active conversion cycle;
- no fee/tax/spread counted as investment;
- no negative spendable balance;
- no SELL beyond exact Broker inventory;
- no global same-Asset BUY and SELL;
- no short/leverage/implicit transfer;
- order min/max/required units match declared quantity/notional unit.

### 7.3 Price semantics

- source quote retains original currency and `quote_base_quantity`;
- evaluator derives unit mid once;
- investment/exposure uses mid value;
- BUY ledger uses charge price after FX spread;
- SELL ledger uses credit price after FX spread;
- execution-currency prices and every FX assumption are present in submitted snapshot;
- frontend never silently computes authoritative conversion.

### 7.4 Fees and SELL tax

For non-zero order notional `N`:

```text
fee(N) = fixed + clamp(rate * N, rate_minimum, rate_maximum)
```

Min/max apply only to percentage component. BUY and SELL profiles are independent.
For non-zero orders, `rate=0` with a positive `rate_minimum` applies that minimum;
a free profile requires fixed/rate/minimum all zero.

SELL schedule:

```text
gross proceeds
- SELL fee
- PMC cost basis of sold quantity
= gain before tax

tax reserve = ROUND_HALF_UP(max(gain before tax, 0) * Asset tax rate)
reusable proceeds = gross proceeds - SELL fee - tax reserve
```

`withholding_kind`:

- `broker_withheld` for administered regime;
- `self_reserved` for declarative/free regime.

Both reserves are unavailable to subsequent BUY. Only self-reserved tax remains in
physical cash. No loss netting or carried-loss compensation in v1.

### 7.5 Objectives

Shared fixed-reference definitions:

```text
F_ref = V_current_invested + K_selected_route_reachable
T_a = w_a * F_ref
r_a = V_a_final - T_a
L2_fixed = Σ_a r_a²
F_final = Σ_a V_a_final
U = F_ref - F_final
```

For PAC, `V_current_invested=0`; for Rebalancer it is the current mid value of
the invested Assets. `K_selected` includes selected existing cash and selected
new contributions as distinct native-ledger rows. `K_selected_route_reachable`
includes only value having at least one permitted source→Broker×currency→BUY
path to a positive-weight Asset with usable price, ignoring only
amount-dependent minima. Cash that is merely below a minimum stays reachable
and reappears in `U`; cash with no structural path is `K_trapped`, excluded from
`F_ref`. Fee, spread, tax and buffer are candidate-dependent and are not
pre-netted from the reference. SELL proceeds are internal transfers and never
increase `F_ref`.

`w_a` is dimensionless; `F_ref`, `T_a`, `r_a`, `F_final` and `U` are in
valuation currency; `L2_fixed` is in valuation-currency squared. It is evaluated
exactly from unformatted Decimal values. `L2_fixed/F_ref²`,
actual-final percentages, D∞ and D1 are diagnostics only and do not control
orders.

The exact identities are:

```math
\sum_a r_a=-U,\qquad
L2_{fixed}\ge\frac{U^2}{|A|}
```

so shrinking investment cannot shrink the target denominator or avoid a
quadratic penalty. The authoritative accounting decomposition is:

```math
U=C_{free}+R_{physical}+L_{economic}+A_{round}
```

`C_free` is reachable spendable closing cash; `R_physical` is FX buffer plus
self-reserved tax; `L_economic` is once-only value loss from charge/sell spread,
fees, FX spread and broker-withheld tax; `A_round` is the signed sum of
minor-unit posting adjustments. It must satisfy:

```math
|A_{round}|
\le
\frac12\sum_j\mu_{c_j}\rho_{c_j\to v},
\qquad
U\ge-|A_{round}|_{max}
```

The index `j` in this bound covers each rounded debit/credit posting once.
Positive `A_round` consumed value; a small negative value is favorable posting,
not leverage. A broken identity or bound makes the candidate invalid.

Every final Broker×Asset quantity and aggregate Asset value is nonnegative:

```math
h^{final}_{ab}\ge0\quad\forall(a,b),\qquad
V^{final}_a\ge0\quad\forall a
```

Rebalancer additionally requires `V_current_invested>0` before solve and
`F_final>0` for every candidate. PAC may publish an exact no-op at zero or
unusable budget.

PAC primary:

- `proportional`:
  `L2_fixed → U → route priority → cost → rows → total tie`;
- `min_fragmentation`:
  `L2_fixed → U → split Assets → rows → route priority → cost → total tie`.

Rebalancer primary:

- `invest_only` imposes SELL=0;
- `invest_and_sell` freezes the invest-only baseline, permits SELL only from
  fixed-target-overweight Assets with no frozen BUY and only to fund incremental
  BUY;
- both use:
  `L2_fixed → U → turnover → cost → rows/splits → total tie`;
- every active SELL remains one-quantum/whole-row necessary after fee/tax/FX and
  alternative-funding recomputation; local irreducibility is not global proof.

Both deployment results freeze the complete primary action vector, including
funding, FX, orders and SELL, then permit BUY additions only:

```text
U → resulting L2_fixed → incremental cost/rows → total tie
```

They report additional investment, residual cash, incremental cost and
before/after `L2_fixed` plus diagnostics. `ΔL2_fixed` may be positive. If a
deployment candidate has lower `L2_fixed` than an unproven primary incumbent,
it dominates and must be promoted/re-ranked before publication.

#### 7.5.1 Policy compiler matrix

The policy string selects a declarative program; it does not select a hidden
coefficient or a second accounting implementation.

| Product/mode | Enabled actions and domain | Additional hard constraints | Primary lexicographic tiers | Deployment tiers |
|---|---|---|---|---|
| PAC `proportional` | selected funding, transfers, permitted acyclic FX, discrete BUY and activations | `SELL=0`; route permissions, minima/caps/quanta and native ledgers | `L2_fixed → U → route priority → cost → rows → total tie` | freeze all primary funding/transfer/FX/BUY actions; add BUY only: `U → L2_fixed → incremental cost → incremental rows → total tie` |
| PAC `min_fragmentation` | same PAC action domain | same PAC hard constraints | `L2_fixed → U → split Assets → rows → route priority → cost → total tie` | same frozen-action BUY-only domain and tiers |
| Rebalancer `invest_only` | selected funding, transfers, permitted acyclic FX, discrete BUY and activations over immutable initial holdings | `SELL=0`; `V_current_invested>0`; `F_final>0`; all PAC ledger/route constraints | `L2_fixed → U → turnover → cost → rows/splits → total tie` | freeze complete primary action vector; add BUY only with same deployment tiers |
| Rebalancer `invest_and_sell`, phase 1 | exact `invest_only` program | exact `invest_only` constraints | compute and freeze the `invest_only` primary | not yet run |
| Rebalancer `invest_and_sell`, phase 2 | frozen phase-1 funding/FX/BUY plus SELL and incremental BUY | SELL only from baseline-overweight Assets having no frozen BUY; no BUY+SELL per Asset; SELL≤inventory; positive net proceeds; every SELL funds incremental BUY; local quantum/riga irreducibility; no sale-to-idle-cash | `L2_fixed → U → turnover → cost → rows/splits → total tie` on the restricted extension domain | after phase-2 primary, freeze its complete vector including SELL and add BUY only with the deployment tiers |

All rows inherit nonnegative final quantity/value, native-ledger conservation,
once-only fee/FX/tax/rounding accounting and finite derived bounds. In
`invest_and_sell`, local SELL irreducibility is a mandatory feasibility property,
not proof that the globally best SELL vector was found.

Proof eligibility is identical across rows:

- a Decimal-valid incumbent may be `not_proven` or `gap_bounded`;
- `optimal_proven` requires complete exact oracle or coefficient-safe
  score-lattice closure for every normative tier;
- `infeasible_proven` requires a complete deterministic Decimal conflict witness
  or exhaustive exact oracle;
- a floating solver status never upgrades these states.

The v1 table is entirely solver-backed. A deterministic dispatcher remains an
architectural extension point only for a future genuinely closed-form policy;
it consumes the same `NormalizedScenario` and Decimal evaluator but may not be
used to relabel the current global PAC solve as deterministic.

### 7.6 Shared SCIP MIQP/MIQCP solver gate

Frozen solver-boundary policy:

1. do not install/probe PySCIPOpt until every runtime lane is frozen and the
   developer performs or explicitly authorizes the shared Pipfile/lock update;
2. compile PAC and Rebalancer objectives into one SCIP adapter: convex MIQP for
   the first tier and convex MIQCP/MISOCP for the fixed-L2 sublevel;
3. represent decision ticks and activations with finite bounds derived from
   cash, instruction step, route cap and inventory;
4. keep Decimal evaluator authoritative;
5. scale Decimal values and weights rationally and reject unsafe
   coefficient/activity/dynamic-range envelopes;
6. impose hard nonnegativity; require Rebalancer `V₀>0` before solve and
   `F_final>0` without epsilon;
7. solve each lexicographic tier separately and do not emulate priorities with
   hidden weights. A proven L2 optimum makes the convex sublevel an exact face;
   otherwise it is only an incumbent ceiling, a lower-L2 result restarts the
   cascade, and later evidence remains explicitly conditional;
8. derive any exact `L2_fixed` score lattice from reachable scaled monetary
   residuals and squared terms; SCIP's floating MIQP gap alone is never closure;
9. apply D39: Decimal-verify every incumbent, retain raw floating solver
    evidence, and never promote it to an exact public proof;
10. compare solver against a complete exhaustive oracle on all small cases;
11. test medium supported-domain families where exhaustive oracle is unavailable
    and require a meaningful certified bound;
12. re-evaluate every integer incumbent and native ledger with Decimal; a bounded
    posting-rounding delta is reportable, a hard violation is not;
13. benchmark wheel/import, MIQP and convex-MIQCP tiers, cold start, warm solves,
    RSS, packaging, cancellation, time/node limits and
    worker cleanup;
14. bound each native call below platform soft timeout and checkpoint between
    lexicographic calls;
15. treat client abort as “stop waiting”, not a false cancellation acknowledgement;
    platform worker termination/cleanup remains authoritative;
16. use `optimal_proven` only when exhaustive exact oracle or a
    coefficient-safe reachable-score bound closes every relevant tier; use
    `infeasible_proven` only for deterministic conflict witness or exhaustive
    exact closure;
17. if SCIP fails formulation, packaging, correctness, capacity or
    supported-domain gates, stop for a new developer decision.

No arbitrary Big-M. Every bound derives from selected cash, instruction step, price,
fees or inventory.

### 7.7 Component responsibilities

| Component | Owns | Must not do |
|---|---|---|
| Normalizer | parse wire strings; validate units, IDs, uniqueness and cross-references; build immutable exact `NormalizedScenario`; classify `needs_input/invalid/unsupported` | choose routes, optimize, query DB/provider/service, silently default missing financial facts |
| `PolicyCompiler` | map the matrix in §7.5.1 to variables, finite domains, hard `ConstraintSpec`s, ordered `ObjectiveStage`s and canonical tie vector | perform financial I/O, hide weights/tolerances, change ledger equations by mode |
| SCIP adapter | encode compiled integer/binary actions and convex quadratic objective/sublevels; enforce time/node/cancel checkpoints; return raw candidates, bounds, settings and statuses | declare financial truth, round money for publication, promote floating status to exact proof |
| Decimal evaluator | replay every native posting once; verify constraints, holdings, cash, FX, fees, tax, rounding bound and complete exact objective tuple; create deterministic conflict witnesses where available | import solver modules, repair a materially infeasible candidate, infer missing facts |
| Exhaustive oracle | enumerate the complete bounded action domain for declared small cases and rank candidates with the same independent evaluator | copy the production solver search or add-only heuristic, claim coverage outside its declared bounds |
| Reporter | map normalized input plus evaluator/proof evidence into the discriminated result union in §6.3 | recompute money, percentages, objectives or proof |
| Frontend renderer | display backend-authored rows, ledgers, deltas, diagnostics and explanations | reconstruct hidden financial facts or recompute authoritative results |

`ObjectiveStage` carries name, direction, unit, exact Decimal evaluator function
and solver expression builder. `ConstraintSpec` carries stable code, scope,
finite bound/source and both solver and Decimal predicates. This common
intermediate representation is the extension seam: a future policy is
declarative only if existing facts, constraints, result and proof contract can
express it; otherwise it requires an explicit contract/version decision.

### 7.8 Public status mapping under proof semantics A

| Evaluated condition | Public representation |
|---|---|
| required fact absent | `PlanningInputFailure(availability="needs_input")` |
| supplied fact or relationship contradictory/malformed | `PlanningInputFailure(availability="invalid")` |
| understood scenario outside the frozen supported domain | `PlanningInputFailure(availability="unsupported")` |
| Decimal-feasible best candidate plus exhaustive oracle or safe score-lattice closure of every tier | `SearchExactOptimalPlan`; `outcome=no_op|incumbent_found`, `proof=optimal_proven`, exact `proof_source` |
| Decimal-feasible candidate plus comparable raw solver bounds in declared units | `SearchBoundedPlan`; `outcome=incumbent_found`, `proof=gap_bounded` |
| Decimal-feasible candidate without conclusive/comparable bounds | `SearchUnprovenPlan`; `outcome=incumbent_found`, `proof=not_proven` |
| no candidate plus complete Decimal static conflict | `SearchDeterministicInfeasible`; `outcome=infeasible_proven`, `proof_source=deterministic_conflict` |
| no candidate plus exhaustive exact oracle closure | `SearchOracleInfeasible`; `outcome=infeasible_proven`, `proof_source=exhaustive_oracle` |
| no valid incumbent and no exact infeasibility proof, including floating `infeasible` | `SearchNoIncumbent`; `outcome=no_incumbent`, `proof=not_proven` |
| timeout/node limit/cancel with Decimal-feasible incumbent | bounded or unproven plan with the real `stop_reason`; never exact by stop reason alone |
| crash, failed cleanup, failed serialization or output-contract validation | Tool error, never a success-shaped planning result |

Every published plan carries `incumbent_validation=decimal_verified`.
This proves the displayed candidate's accounting, constraints and exact tuple,
not global optimality. A floating `optimal` can map only to `gap_bounded` when
its raw bounds are comparable and complete, otherwise `not_proven`. A floating
`infeasible` without exact closure maps to `no_incumbent/not_proven`.
`base_result` and `variant_result`, when present, retain independent
outcome/proof/stop/evidence. An empty incumbent is public `no_op` only when its
optimality is exactly proved.

### 7.9 Model-build order and stop conditions

Normative implementation pseudocode:

```text
plan(request):
  normalized = normalize_exact(request)
  if normalized is input_failure:
      return input_failure

  static_conflict = decimal_precheck(normalized)
  if static_conflict is complete:
      return deterministic_infeasible(static_conflict)

  program = policy_compiler.compile(normalized.product, normalized.mode_or_policy)
  require_finite_bounds_and_safe_coefficient_envelope(program)

  if program is rebalancer.invest_and_sell:
      invest_only = solve_lex(program.invest_only, primary_tiers)
      stop_or_publish_if_no_decimal_incumbent(invest_only)
      program = compile_restricted_sell_extension(program, freeze(invest_only.actions))

  primary = solve_lex(program, primary_tiers)
  stop_or_publish_if_no_decimal_incumbent(primary)

  deployment_program = compile_deployment(
      freeze(primary.funding, transfers, fx, buy, sell),
      enable_additional_buy_only=True,
  )
  deployment = solve_lex(deployment_program, deployment_tiers)

  if deployment has Decimal L2_fixed lower than unproven primary:
      primary = promote(deployment)
      restart primary/deployment cascade while budget permits

  return reporter.render(primary, coherent_optional_deployment, exact_evidence)
```

`solve_lex` executes this order for every stage:

1. build the solver expression from the compiled stage;
2. call SCIP only within the remaining soft budget;
3. extract raw integer/binary actions and raw solver evidence;
4. Decimal-replay every candidate from those actions;
5. discard materially infeasible candidates without repair;
6. rank valid candidates by the full exact prefix;
7. add the exact incumbent ceiling for the completed prefix;
8. checkpoint cancellation/time and continue, stop or restart on earlier-tier
   improvement.

Stop before a solver call when required facts, finite action bounds,
coefficient/activity envelope, supported route graph or required solver
capability is missing. Stop with exact infeasibility only on a complete conflict
witness/oracle. Stop with `no_incumbent/not_proven` when limits or floating
infeasibility leave no Decimal-valid candidate. If deployment promotion leaves
insufficient time to rebuild a coherent pair, publish the promoted primary as
`not_proven`, omit the variant and emit a typed issue. Never install/fallback to
another solver, relax a hard constraint, invent an epsilon, reduce cardinality
or omit mandatory facts at runtime.

## 8. Persistence and domain-copy architecture

### 8.1 DB decision

No planner DB model or Alembic migration in v1.

- operational Broker settings remain per-run;
- manual account/Broker/Asset remain local scenario data;
- Asset tax rate is prefilled `0.26`, editable in snapshot;
- carried losses are per-run facts;
- persistent profiles/tax metadata remain `TODO_FUTURI.md`.

If implementation appears to require persisted planner settings, stop and reopen
scope. Do not create partial schema “for later”.

### 8.2 Domain-copy responsibilities

Extend domain-owned APIs, not Tool compute:

- Portfolio: canonical Asset candidates, complete OWNER custody by Asset×Broker,
  native Broker cash, PMC and provenance;
- Broker: authorized identity/display facts only;
- Asset: quote, `quote_base_quantity`, Type/Sector/Geography exposure facts and
  explicit missing values;
- FX: saved read-only rate, source timestamp and staleness.

Requirements:

- current price copy must not call mutating `/assets/prices/current`;
- use existing `compute_wac_iterative` for PMC; no WAC/FIFO change;
- OWNER 0% still receives full custody facts with personal share separate;
- selected unauthorized Broker set fails closed; no silent intersection;
- missing price/FX/classification remains explicit, never omitted;
- all sync I/O inside async handlers uses `asyncio.to_thread`;
- no personal values in logs/diagnostics/examples.

### 8.3 Worker boundary

`compute()` receives only validated snapshot and `ToolExecutionContext`.

Allowed:

- synchronous pure normalization/evaluation/solver;
- `context.checkpoint` for cancellation;
- owned child process/thread only if executor cleanup domain guarantees termination.

Forbidden:

- `AsyncSession`, principal, request/cookie;
- Asset/Portfolio/Broker/FX service calls;
- DB query;
- provider/live network call;
- financial write;
- hidden preference/global-state lookup.

## 9. Frontend architecture and component reuse

### 9.1 Proposed module layout

```text
frontend/src/lib/features/tools/pac-allocator/
├── PacAllocatorTool.svelte
├── PortfolioRebalancerTool.svelte
├── planner/
│   ├── OperationalPlannerShell.svelte
│   ├── PlanningStepRail.svelte
│   ├── PlanningSummaryRail.svelte
│   ├── PlanningMobileSummary.svelte
│   ├── FundingSourcesStep.svelte
│   ├── TradingBrokersStep.svelte
│   ├── PlanningAssetsStep.svelte
│   ├── AssetBrokerRoutesStep.svelte
│   ├── PlanningTargetsStep.svelte
│   ├── PlanningFxStep.svelte
│   ├── PlanningStrategyStep.svelte
│   ├── PlanningReviewStep.svelte
│   ├── PlanningResultShell.svelte
│   ├── PlanningAssetMatrix.svelte
│   ├── PlanningExposureRibbons.svelte
│   ├── PlanningGeographyComparison.svelte
│   ├── PlanningOperationalPlan.svelte
│   ├── PlanningAssetTable.svelte
│   ├── PlanningBrokerOrdersTable.svelte
│   ├── planningDraft.svelte.ts
│   ├── planningDependencies.ts
│   ├── planningSourceCopies.ts
│   ├── planningResultSelectors.ts
│   └── planningContracts.ts
├── pac/
│   └── PAC-only strategy/result components
└── rebalancer/
    └── Rebalancer-only holding/strategy/result components
```

Names may be tightened during implementation, but ownership boundaries and shared
versus Tool-specific split are fixed.

### 9.2 Required reuse/generalization

| Existing surface | Action |
|---|---|
| `CompactCashCell.svelte` | reuse for money+currency; extend only through generic props |
| `ExactDecimalInput.svelte` | reuse for rates/percentages/non-money Decimal |
| inline quantity editor in `TransactionFormModal.svelte` | extract `ExactQuantityInput.svelte`; migrate transaction modal first |
| `AssetSelect.svelte` / `BrokerSearchSelect.svelte` | reuse for row-level choice |
| `AssetModal.svelte` / `BrokerModal.svelte` | reuse for persistent authorized creation |
| Asset/Broker galleries | reuse for multi-select/discovery |
| `AssetIcon.svelte` / `BrokerIcon.svelte` | reuse in cards/charts/tables |
| `CurrencySearchSelect.svelte` | reuse |
| `SingleDatePicker.svelte` | reuse |
| `ConfirmModal.svelte` | reuse for exact dependency deletion |
| `DataTable.svelte` / `ColumnVisibilityToggle.svelte` | reuse for desktop operational tables |
| `GeographyMap.svelte` | reuse/extend for synchronized before/after maps |
| existing ECharts dashboard components | reuse lifecycle, theme, resize, touch patterns |
| `KpiCard.svelte` | reuse for result KPIs |

`ExactQuantityInput` regression contract:

- locale-safe raw input;
- comma/dot;
- trailing zeros preserved while editing;
- arrow stepping;
- blur formatting;
- configurable sign/range/disabled/testid;
- exact string remains authoritative for mutation/serialization;
- `Number`/`parseFloat` may drive non-authoritative visual sign hints only;
- current auto-negate behavior is reimplemented by exact string sign manipulation,
  never by float round-trip;
- no observable TransactionFormModal UX regression; high-precision quantity handling
  intentionally improves.

### 9.3 State ownership

Shared shell owns:

- nine-step state machine;
- completed/review-required/invalid state;
- destructive dependency graph and modal;
- account generation, request sequence, component identity and draft revision;
- copy/compute AbortControllers;
- busy/cancel/error/result-stale;
- immutable review snapshot/digest.

Step components mutate only local draft. Result components are read-only. Source copy:

1. fetches explicit domain response;
2. displays provenance/date/age;
3. applies only on explicit action;
4. rejects late account/request/revision responses;
5. never binds live or overwrites silently.

### 9.4 Frontend math boundary

Frontend may:

- parse local display strings without loss;
- validate required shape/range for immediate UX;
- total target ratios exactly for form guidance;
- derive chart coordinates and display formatting from backend output.

Frontend may not:

- allocate cash;
- choose orders/routes/FX;
- compute fees/taxes/SELL proceeds;
- produce authoritative before/after portfolio economics;
- reinterpret missing backend facts as zero.

## 10. Parallel execution graph

```text
Developer planning-state approval
        |
        v
SQL task reset + Round 6/7/artifact materialization
        |
        v
Coordinator checkpoint commit + SHA
        |
        v
Developer implementation-start approval (Gate P1)
        |
        v
W0 Contract/docs freeze -------------------------+
        |                                        |
        +--> W1 Schema/internal models ----------+----+
        |                                        |    |
        +--> W2 Domain-copy API -----------------+    |
        |                                             |
        +--> W3 Shared numeric UI primitive ----------+
                                                      |
W1 --> W4 Decimal normalizer/evaluator/ledger --------+
W1 + W3 --> W6 Shared wizard/result shell ------------+
W4 --> W5 Oracle/solver/benchmark --------------------+
W2 + W6 --> source-copy integration                   |
W5 --> W7 Plugin/report/API sync/client --------------+
W6 + W7 --> W8 PAC UI ---------+                      |
W6 + W7 --> W9 Rebalancer UI --+----------------------+
                                |
                                v
W10 Tests/runner + W11 Docs/i18n/CHANGELOG
                                |
                                v
W12 Combined gates/reviews/manual runbook
```

### 10.1 Workstream ownership

| WS | Exclusive write scope | Hard dependencies | Specialist |
|---|---|---|---|
| W0 | PAC normative design/contract reconciliation | Gate P1 | high-reasoning planner + rubber-duck |
| WR | runner registrations and explicit Vitest path lists | W0 + final test paths from active WS | one integration owner |
| W1 | `backend/app/schemas/pac_allocator.py`, internal `models.py` | W0 | backend schema owner; test-author |
| W2 | Portfolio/Asset/Broker/FX copy schemas/services/API | W0 | backend domain owner; test-author |
| W3 | generic numeric inputs + TransactionFormModal migration | Gate P1 | frontend owner; test-author |
| W4 | normalize/evaluator/numeric/ledger/fee/FX modules | W1 | high-reasoning math owner; test-author |
| W5 | solver/oracle/objectives/limits/benchmark | W4 | high-reasoning math owner; test-author |
| W6 | shared planner shell/draft/steps/result primitives | W1, W3; fixtures first | frontend shared owner; test-author |
| W7 | report/plugin/export/codegen/client/registry | W1, W4, W5 | single integration owner; test-author |
| W8 | PAC wrapper/strategy/results | W6, W7 | frontend PAC owner; test-author |
| W9 | Rebalancer wrapper/holdings/strategy/results | W6, W7 | frontend Rebalancer owner; test-author |
| W10 | final test matrix + runner reachability audit | W1–W9, WR | test-author; runner owner |
| W11 | EN docs, i18n, CHANGELOG | stable contract/UI | docs-writer + one shared writer |
| W12 | combined revision, reviews, runbook | all | integrator + independent reviewers |

Shared leases:

- Tool schema export/API sync/client generation;
- `frontend/src/lib/features/tools/registry.ts`;
- runner modules;
- four i18n catalogues;
- MkDocs nav;
- `CHANGELOG.md`;
- onboarding/layout;
- any generic Tool platform file.

One integration owner writes them. Other workstreams provide requested snippets/keys,
never concurrent edits.

Parallel arrows above mean **file-disjoint implementation only**. All validation
commands, including pure component/unit selectors, queue serially through lane 6153.
PAC and Rebalancer code work may overlap; their Playwright runs may not.

Runner catalogue is an early shared lease, not deferred wiring:

1. each test-author workstream freezes its final test path before first validation;
2. runner owner batches registrations/path-list updates;
3. workstream waits until its action reaches that path;
4. only then runs its `dev.py test` selector;
5. Step 10 audits reachability, aggregate inclusion and obsolete P1 removal.

## 11. Detailed implementation steps

After every completed step, immediately update durable Round 7 plan:

```text
- [x] Step N — title — YYYY-MM-DD
  > **Nota implementazione**: exact files/symbols and delivered behavior.
  > **Evidenza**: exact command, selector, pass count and artifact/hash.
  > **⚠️ Fuori pista**: error/detour, DB/files/server impact, recovery and
  > evidence validity. Omit only when no detour occurred.
```

### Gate P0 — Persist approved planning state

> **Completed historical gate.** “Pending Round 7” below describes its state at
> Gate P0, before the checkpoint and later Gate P1.

**Owned surfaces**

- session SQL `todos` / `todo_deps`;
- completed Round 6 UI plan;
- pending Round 7 plan;
- approved end-to-end design, decision chronicle and UI Blueprint artifacts;
- Round 5/Round 6/Round 7 cross-links;
- Blueprint approval status;
- additive local planning index entries.

**Dependency:** developer approval of planning-state persistence through native plan
approval. This approval is not implementation authorization.

**Actions**

1. Reset SQL tasks/dependencies to exact Round 7 graph before repo changes.
2. Inventory stable project artifacts against session/source bundle.
3. Materialize all missing plans/artifacts and approval status without changing product
   code.
4. Validate links, hashes and diff.
5. Send coordinator checkpoint request.
6. Wait for commit SHA/clean state.
7. Verify local planning baseline.

**Specialist:** coordinated workstream + release coordinator.

**Validation**

```text
git diff --check
```

Plus scoped relative-link/path validator over `13_pacAllocator`.

**Artifacts:** refreshed SQL task graph; complete stable Round 5→6→7 planning bundle;
coordinator commit SHA; verified baseline; clean/authorized delta report.

**DoD:** planning state persisted; SHA returned; no partial files; implementation still
not started; developer has not yet been asked to start.

**Stop:** no SHA or baseline mismatch.

### Gate P1 — Obtain explicit implementation-start authorization

**Owned surfaces:** session communication and SQL status only; no repository write.

**Dependency:** Gate P0 DoD including coordinator SHA and verified clean planning
baseline.

**Actions**

1. Report exact coordinator SHA, persistent planning files and any residual delta.
2. Ask developer explicitly whether product implementation may start.
3. If approved, mark SQL implementation gate done and begin Step 0.
4. If not approved or no answer, remain `FROZEN`.

**Validation:** re-read `HEAD` and `git status --short`; no test/build/server.

**Artifacts:** verbatim developer authorization and verified start SHA.

**DoD:** explicit implementation authorization exists after checkpoint, never inferred
from plan approval.

**Stop:** missing authorization, changed baseline or dirty delta not explained by
approved planning files.

### Step 0 — Reconcile and freeze normative contract

**Owned surfaces**

- `pac-rebalancer-end-to-end-design.md`;
- `pac-rebalancer-operational-design.md` redirect integrity;
- `pac-allocator-contract.md`;
- `pac-allocator-ux.md`;
- Round 7 plan progress.

**Dependency:** Gate P1.

**Actions**

1. Verify Gate P0 planning artifacts already use approved order enum and no
   contradictory active fractional boolean.
2. Freeze `invalid` availability branch and conditional output union.
3. Verify all Blueprint review blocks/final aesthetic decisions remain approved.
4. Freeze exact fields, units, cardinality limits and issue/status matrix.
5. Freeze shared `F_ref`, monetary targets, `L2_fixed`, hard nonnegativity and
   exact Decimal units/scaling.
6. Freeze PAC/Rebalancer primary and deployment tier orders plus policy compiler
   boundaries.
7. Prove `U` conservation, anti-shrink, deployment monotonicity and funding-only
   quantum-minimal SELL; encode the accepted conservative exact-public
   proof/status semantics and MIQP/MIQCP boundary.
8. Build maximum-input and maximum-two-solution-result JSON witnesses; prove
   131,072/262,144-byte ceilings.
9. Allocate 4 s soft / 5 s hard execution budget across cold start, solver, Decimal
   evaluation, serialization and output validation.
10. Freeze final test file paths and runner actions for early WR lease.
11. Add sanitized numeric witnesses for fee, FX, tax, low cash and no-op.
12. Run independent math/logic review; fix blockers before code.

**Specialist:** high-reasoning math owner; read-only rubber-duck.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc \
pipenv run python /tmp/libreFolio_pac_contract_capacity.py

git diff --check
```

Temporary pure probe serializes worst-case pseudocode fixtures and records byte
counts; it performs no server, DB, provider or production-file write. Also run scoped
documentation link/path check.

**Artifacts:** contract delta matrix; schema pseudocode; duplicate-design redirect;
objective-formulation proof; capacity/time budget; reviewed witnesses.

**DoD:** no contradictory active contract, no obsolete fractional flag/quantity
step, shared fixed-reference objective and both result orders accepted,
Rebalancer SELL/proof semantics accepted, minimum supported domain fits fixed
Tool envelopes, reviewer finds no blocker.

**Stop:** accepted proof combinations not representable, payload/result overflow,
execution-budget miss or accepted objective not safely representable.

**Progress — 2026-09-15**

- [!] Step 0 — **REOPENED FOR DOCUMENT CORRECTION / RUNTIME BLOCKED**
  > **Evidenza storica D23**: Gate P1 was recorded verbatim against clean baseline
  > `202e4056f2b915c055eeb8436eae765023201918`. Read-only analysis derived the only
  > finite exact MILP square construction available to linear SciPy/HiGHS: common
  > integer lattice, absolute-gap bits and binary-product rows after the tier-1 face
  > is frozen. It cannot satisfy the approved numeric domain and `2.5 s` solver
  > budget: current Decimal magnitudes can create objective-lattice gaps around
  > `10^24–10^36`, while exact binary64-safe aggregation requires
  > `32 * D*^2 < 2^53` (`D* <= 16,777,215`). Even the safe 32-Asset envelope adds
  > about `9,600` square binaries and `26,496` AND rows before routes, fee pieces,
  > FX, tax, transfers, sequential SELL and repeated lexicographic solves.
  >
  > **Evidenza**: the independent read-only audit observed SciPy `1.18.1`, HiGHS
  > `1.15.1`, and the native rejection `Cannot solve MIQP problems with HiGHS`.
  > The conservative object-only, reference-indexed compact-JSON stress dossier at
  > `/tmp/libreFolio_pac_contract_capacity_v4.py` measured input `114,198 /
  > 131,072` bytes (SHA-256
  > `08fb24a64319eccc4590c32b5d1b87b9c0a6ada4cb1e47e74b796cac77c58f7e`)
  > and result `289,436 / 262,144` bytes (SHA-256
  > `da08ef033868bcfef4f0028288d1e6ac08715d99cd98da5767aa044712db3049`).
  > A tuple-row witness fit (`84,590` / `207,116` bytes), but the existing Tool
  > registry deliberately quarantines tuple schemas as frontend-codegen
  > incompatible, so it is not acceptance evidence.
  >
  > **⚠️ Fuori pista**: the solver gate remains red. Exact tier-2 is not
  > representable safely/credibly within the existing linear solver and budget;
  > the stress dossier also exceeds the fixed result ceiling by `27,292` bytes.
  > It maximizes every audit cardinality simultaneously and duplicates two full
  > 64-order solutions, 128 cash-ledger rows, 48 FX-action rows, 224 exposure
  > rows and 256 issues with maximum-length values. The developer rejected it as
  > authority for the intended product output: it remains negative evidence
  > against naively duplicating full audit state, not evidence that the approved
  > result UI cannot fit. A new product-shaped witness must derive from the
  > approved Asset/Broker/order/funding/FX/summary views. No cardinality, platform
  > cap or payload-schema decision follows from this artifact. Rebalancer
  > deviation denominator/units, non-terminating
  > FX/price division rounding and exact `gap_bounded` units also require an explicit
  > numeric policy. Per D23, no schema, engine, API, frontend, test, generated client,
  > runner, i18n, docs or CHANGELOG implementation starts until the developer chooses
  > a solver/algorithm direction and approves a product-shaped result contract.
  >
  > **Chiarimento sviluppatore — 2026-09-15**: Riskfolio-Lib and SciPy remain in
  > their current roles; SCIP, if approved, is an additive planner solver rather
  > than a replacement or reason to reimplement existing quantitative libraries.
  > Floating-point solving followed by authoritative Decimal accounting and
  > currency rounding is acceptable. Order quantities and monetary ticks still
  > remain discrete solver decisions: this does not authorize a continuous QP
  > followed by flooring. Remaining gates are the Rebalancer score reference,
  > proof/status semantics for tolerance-based MIQCP, explicit PySCIPOpt/SCIP
  > dependency authorization and a codegen-compatible object result below the
  > existing `262,144`-byte platform ceiling.
  >
  > **Correzione algoritmica — 2026-09-15**: il developer ha confermato la
  > metodologia originale PAC: `target = budget × peso`, floor per quantità
  > intera/step monetario, residuo esplicito; soltanto la seconda soluzione
  > ottimizza incrementi BUY. Può peggiorare D∞/D1 per massimizzare investimento
  > mid aggiuntivo e deve mostrare il delta. Il precedente fallimento D23 non
  > blocca più la base PAC né impone SCIP: è riaperto e limitato al Rebalancer
  > dopo la scelta del relativo riferimento/obiettivo. Il gate payload resta rosso.
  > Fino alla nuova decisione e al nuovo witness restano vietati codice, test,
  > dependency update e probe.
  >
  > **Review matematica read-only — 2026-09-15**: primo verdetto `BLOCKED`
  > con due blocker documentali: hard minimum non riservati prima del greedy e
  > status/proof unici per due soluzioni diverse. Questa revisione li corregge
  > con pre-pass Decimal completo + conflict witness e result envelope
  > discriminati per soluzione. Corregge inoltre ranking route calcolato una
  > volta, somma target esatta, step monetario multiplo della minor unit,
  > ledger completo nel post-step, identità envelope
  > investimento/costi/buffer/cash/rounding, `d_budget` distinto da `r_target` e
  > tie-break vettoriale totale. Nessuna review ha autorizzato codice o solver.
  >
  > **Stato intermedio dopo correzione PAC**: i blocker PAC rilevati sono
  > risolti nel contratto documentale. Step 0 restava aperto per obiettivo/proof
  > Rebalancer e risultato object-only oltre `262144` byte.
  >
  > **Decisione obiettivo Rebalancer — 2026-09-15**: il developer ha congelato
  > percentuali investite finali effettive con `F_final>0`. La base target-first
  > ordina `D∞pct → D1pct → U → turnover → costi → righe/split → tie`;
  > `F_ref` è soltanto riferimento contabile e `U=F_ref-F_final`. La modalità
  > `invest_and_sell` congela invest-only e ammette solo SELL funding-only,
  > quantum-minimal. La variante deployment-first congela tutte le azioni base,
  > incluso SELL, aggiunge BUY e ordina
  > `U → D∞pct → D1pct → costi/righe → tie`. D² non è un tier.
  >
  > **Decisione policy — 2026-09-15**: vincoli e ledger restano comuni.
  > `proportional` ordina D∞/D1 prima di route/costi/righe;
  > `min_fragmentation` ordina split/righe prima di D∞/D1 e route/costi, sempre
  > dopo il massimo investimento. `invest_only`/`invest_and_sell` sono modalità
  > operative, non coefficienti della funzione obiettivo.
  >
  > **Formalizzazione documentale**: `U` è riconciliato in cash libero, riserve
  > fisiche, perdite economiche e rounding firmato bounded; il SELL distingue
  > irriducibilità locale da minimalità globale; D∞/D1 actual-percentage diventano
  > feasibility MILP monotone a soglia razionale, con `F_min`, separazione score,
  > scaling/GCD, envelope coefficienti e rivalutazione Decimal espliciti. La
  > separazione prova finitezza, ma una bisezione generica può superare
  > l’envelope coefficienti prima della chiusura: serve una ricerca su soglie
  > score-lattice sicure. Ciò prova rappresentabilità matematica condizionata,
  > non capacità o proof closure.
  >
  > **Review matematica Rebalancer**: il primo pass indipendente ha restituito
  > `BLOCKED` con 13 rilievi; il follow-up li ha verificati tutti chiusi e ha
  > individuato tre difetti nelle correzioni. La verifica stretta successiva ha
  > restituito `READY` su bound per-posting, cash SELL residuo e debito FX
  > nativo; l’ultima ambiguità `C_free/K_trapped` è stata corretta con la clausola
  > richiesta. Nessun blocker matematico documentale riportato resta aperto.
  >
  > **Stato intermedio precedente**: runtime FROZEN. Restavano separati la decisione
  > sulla rotta solver/capacità entro 4 s/5 s e il risultato object-only oltre
  > `262144` byte. Nessun codice, test, dependency o probe è autorizzato.
  >
  > **Decisione proof/status — 2026-09-15**: il developer ha scelto la semantica
  > pubblica conservativa. L’evaluator Decimal certifica fattibilità finanziaria,
  > accounting e tupla obiettivo esatta dell’incumbent, non l’assenza di un piano
  > migliore. Qualunque status floating `optimal/infeasible` resta al massimo
  > `gap_bounded` con bound/tolleranze/versione/settings grezzi o `not_proven`.
  > `optimal_proven` richiede oracle esaustivo esatto oppure chiusura
  > score-lattice coefficient-safe per tutti i tier;
  > `infeasible_proven` richiede conflict witness Decimal deterministico oppure
  > oracle esaustivo. La decisione non sceglie né autorizza solver, dependency o
  > probe.
  >
  > **Decisione fixed-L2 condivisa — 2026-09-16**: il developer ha superato sia
  > la base PAC deterministica sia l'obiettivo Rebalancer actual-percentage.
  > Entrambi i Tool usano
  > `L2_fixed=Σ_a(V_a_final-w_aF_ref)²`, poi `U` e tier operativi distinti.
  > Percentuali, D∞ e D1 sono diagnostici. Il risultato deployment congela tutte
  > le azioni primarie, aggiunge BUY e ordina
  > `U → L2_fixed → costi/righe incrementali → tie`; un candidato con L2
  > migliore di un primario non provato viene promosso, non mostrato come
  > degrado. `h_ab_final≥0` e `V_a_final≥0` sono hard constraint.
  >
  > **⚠️ Fuori pista — 2026-09-16**: il pivot rende storiche la costruzione PAC
  > target→route→floor, la ricerca parametrica D∞/D1 e la rotta HiGHS. Il nucleo
  > corrente richiede MIQP e tier lessicografici convex-MIQCP.
  > PySCIPOpt/SCIP è approvato come candidato additivo, ma
  > installazione/lock/probe restano bloccati fino al freeze globale e
  > all'azione o autorizzazione esplicita del developer. Riskfolio/SciPy non
  > cambiano. Il gate payload `289436 > 262144` resta indipendente e rosso.
  >
  > **Note implementazione — 2026-09-16**: riconciliazione documentale in corso
  > sui 13 path già modificati; nessun file production/test/dependency toccato.
  > La prima review matematica fixed-L2 read-only ha restituito `BLOCKED`: cinque
  > blocker e sei rilievi di contratto/esempio. Sono stati corretti target PAC
  > `w_aF_ref`, `U` firmato entro il bound di posting, distinzione MIQP/sublevel
  > convex-MIQCP, precondizione Rebalancer `V₀>0`, dominio deployment fungibile,
  > promozione degli incumbent, envelope coefficienti, definizione corrente di
  > `K_reachable`, naming FX e tutti i witness numerici UI. Il raccordo successivo
  > ha inoltre vietato funding/FX addizionali nel deployment, congelandoli come
  > richiesto, e ha chiarito che il sublevel coincide con la faccia L2 solo dopo
  > prova esatta; altrimenti un miglioramento riavvia la cascata e la prova resta
  > condizionata. I successivi follow-up review, refresh hash/checksum e
  > validazioni link/diff sono registrati nei blocchi conclusivi sotto.
  >
  > **⚠️ Fuori pista — 2026-09-16**: il witness PAC ha reso visibile la
  > distinzione tra `U=3,725` e cash fisico `3,72`: il posting BUY da `464,585`
  > a `464,59` genera `A_round=+0,005`. La UI ora mostra entrambi invece di
  > trattare cash e shortfall contabile come sinonimi.
  >
  > **Follow-up fixed-L2 — 2026-09-16**: la seconda review indipendente ha
  > verificato chiusi tutti gli undici finding iniziali, ma ha restituito ancora
  > `BLOCKED` sul witness Rebalancer: il primario dichiarava `C_free=0` e la
  > variante BUY-only spendeva `48,00`. La decomposizione è stata corretta a
  > `C_free=48`, riserve fisiche `8`, perdite `4`, rounding `0`; la variante
  > consuma esattamente quei `48` e termina con `U=12` senza saldo negativo.
  > Sono stati riallineati anche il piano operativo PAC (`3.655,28`/`3,72`) e
  > la disclosure tra celle renderizzate, totale Decimal, cash e `A_round`.
  > La verifica stretta successiva ha confermato questi fix, ma ha trovato che
  > la tabella Asset chiamava ancora `cash libero` il gap pre-posting `U`.
  > La colonna ora espone `C_free=3,720`, separato da
  > `A_round=+0,005` e `U=3,725`. Il dettaglio SELL è stato riallineato allo
  > stesso witness Rebalancer: lordo `1.106,33`, fee/perdita `4`, riserva
  > `self_reserved 8`, spendibile `1.094,33`. Questa separazione era l'ultimo
  > punto aperto del passaggio; il verdetto finale sotto l'ha chiusa.
  >
  > **⚠️ Fuori pista — target PAC 2026-09-16**: l'ultimo controllo ha provato
  > che il mock riusava target monetari storici incompatibili con i pesi
  > `70/12/13/5`. Il witness corrente usa ora un'unica base Decimal che somma
  > esattamente a `100%`: `70,05/12,71/12,24/5,00`; i target sono
  > `2.563,1295/465,0589/447,8616/182,9500`. Residui, percentuali, L2 primario
  > `3,92421202`, variante `8,06421202`, delta `4,14000000`, route budget e
  > viste mobile sono stati rigenerati dalla stessa base.
  >
  > **Follow-up UX numerico — 2026-09-16**: la review dell'intero witness ha
  > confermato quella catena ma trovato altri raccordi stale. HEAL ora passa
  > da un primario whole di `20` quote a una nuova riga monetaria `+3,00`;
  > il piano operativo PAC è all-EUR e coerente (`1` funding da `3.655,28`,
  > `0` FX, `4` BUY primari), header/label mobile usano il
  > primario canonico, e input holding/PMC/fee/tax SELL coincidono col witness
  > Rebalancer.
  >
  > **⚠️ Fuori pista — dominio variante 2026-09-16**: una route monetaria sullo
  > stesso Broker×valuta del primario avrebbe violato l'enum esclusivo o
  > dominato l'incumbent. Il PAC lascia ora `3,72` già locali su un secondo
  > Broker; una route HEAL-only con minimo=cap `3,00` apre la quinta riga solo
  > nella variante, senza nuovo funding/FX. Nel Rebalancer i `48` di `C_free`
  > sono sul Broker margine e una route HEAL-only ha minimo=cap `48`; importi
  > minori non appartengono al dominio. `FX=0`. Il verdetto conclusivo sotto ha
  > poi confermato il witness intero.
  >
  > **Review matematica fixed-L2 finale — READY, 2026-09-16**: il follow-up
  > conclusivo ha chiuso anche la sequenza Rebalancer. `invest_only` consuma
  > `1.252,00` su due route all-or-nothing (minimo=cap HEAL `1.164,50`, XDWI
  > `87,50`); Directa riceve solo il netto SELL `1.094,33` e lo investe su
  > XDWF; i `48` preesistenti restano sul Broker margine. Il PMC `53,5780`
  > produce plus lorda `34,77`, imponibile post-fee `30,77`, riserva `8` e
  > netto `1.094,33`. Il primario chiude a `L2=2.038,3538`, `U=60`; la
  > variante a `L2=2.182,3538`, `U=12`, delta `144`. PAC, signed `U`,
  > proof union e MIQP/MIQCP condizionale sono stati ricontrollati senza
  > blocker correnti. Step 0 resta comunque aperto sui gate payload e
  > dependency/probe, non sulla matematica.

### Step 1 — Replace public schemas and internal models

**Owned surfaces**

- `backend/app/schemas/pac_allocator.py`;
- `backend/app/services/pac_allocator/models.py`;
- new internal contract modules under same package;
- schema tests written by test-author.

**Dependency:** Step 0.

**Actions**

1. Implement strict discriminated unions from §6.
2. Define exact bounds for rows, strings, result bytes and numeric scales.
3. Serialize maximum valid input/output witnesses against fixed Tool ceilings.
4. Replace P1 input/output roots with `PacPlan*` and `RebalancePlan*`.
5. Remove `analyze`, `report_currency`, `buy_grid`, `quantity_step`,
   `monetary_step` and all P1 output models.
6. Define immutable normalized models distinct from wire draft models.
7. Make conditional status/result shapes unrepresentable when invalid.
8. Replace P1 schema tests; retain no compatibility assertions.
9. Ask WR owner to register `schemas pac-planner` before first selector run.

**Specialist:** backend schema owner; **test-author required**.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  schemas pac-planner
```

`schemas pac-planner` replaces current `schemas pac-analyze`.

**Artifacts:** schema export diff; actual max-input/max-result byte report;
valid/invalid witness table.

**DoD:** strict round-trip, nonfinite rejection, no P1 root import, all exclusive
states discriminated, actual maximum Pydantic instances fit Tool limits.

**Stop:** schema cannot express approved contract without free-form records.

### Step 2 — Extend permission-safe domain copies

**Owned surfaces**

- `backend/app/schemas/portfolio.py`;
- `backend/app/services/portfolio_allocation_source.py`;
- `backend/app/services/portfolio_service.py` only at existing orchestration seam;
- Asset/Broker/FX schema/service/API files only when a fact is genuinely missing;
- dedicated service/API tests by test-author.

**Dependency:** Step 0; implementation may run parallel with Steps 1 and 3, but
validation is serialized through lane 6153.

**Actions**

1. Add PMC amount/currency/as-of/provenance per Asset×Broker using existing WAC.
2. Add Type/Sector/Geography exposure facts with explicit `Unknown`.
3. Preserve quote source/date/staleness and missing price.
4. Expose saved read-only FX rate/source/time/age; no provider refresh.
5. Keep Broker identity/access facts separate from per-run capabilities.
6. Return full native cash per Broker/currency; selected amount remains frontend
   scenario choice.
7. Fail requested unauthorized Broker scope atomically.
8. Prove no planner persistence or DB migration.
9. Ask WR owner to register `services portfolio-allocation-source` before first
   selector run.

**Specialist:** backend domain owner; **test-author required**.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  services portfolio-allocation-source

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  api portfolio
```

First action is proposed and must be registered once by runner owner if absent; second
uses actual catalogue action after test-author verifies it.

**Artifacts:** sanitized source payloads; auth matrix; no-migration proof.

**DoD:** manual flow needs no DB Asset/Broker; copies are complete, provenance-aware,
OWNER-safe and non-mutating; missing facts explicit.

**Stop:** WAC/FIFO behavior change, silent scope filtering or mutating prefill.

### Step 3 — Generalize shared numeric frontend primitives

**Owned surfaces**

- new `frontend/src/lib/components/ui/input/ExactQuantityInput.svelte`;
- `TransactionFormModal.svelte` quantity-field migration;
- generic input component tests via test-author;
- no planner-specific file.

**Dependency:** Gate P1; implementation may run parallel with Steps 0–2 if ownership
stays isolated; validation remains queued after Step 0 contract freeze.

**Actions**

1. Extract current locale-safe quantity editor behavior.
2. Remove three duplicated inline quantity inputs from transaction modal.
3. Preserve raw buffer, commas/dots, trailing zeros, arrows, blur, sign/range,
   disabled and test IDs.
4. Reuse existing parsing/format helpers; no new numeric parser.
5. Keep authoritative quantity as exact string and reimplement auto-negate without
   float conversion; numeric parsing is visual-only for sign hints.
6. Add generic props needed by planner without planner knowledge.
7. Keep objective construction, route selection, money conversion and ledger
   arithmetic out of the component and frontend.
8. Add regression tests for transaction create/edit/paired layouts.
9. Ask WR owner to add new tests to explicit `front-utility component-unit` path list
   before first selector run.

**Specialist:** frontend shared-component owner; **test-author required**.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  front-utility component-unit

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check
```

**Artifacts:** component API table; transaction regression evidence.

**DoD:** one shared quantity input; transaction UX unchanged, high precision no longer
float-round-trips; planner can consume component without fork.

**Stop:** any transaction behavior regression.

### Step 4 — Build Decimal normalizer/evaluator/ledger

**Owned surfaces**

- `backend/app/services/pac_allocator/normalize.py`;
- `evaluator.py`;
- `numeric.py`;
- new `ledger.py`, `fees.py`, `fx.py`, `objectives.py`;
- pure service tests via test-author.

**Dependency:** Step 1.

**Actions**

1. Normalize strict wire data into frozen dataclasses.
2. Validate targets, order enum, route units, fees, FX, inventory, PMC and tax.
3. Implement one-time minor-unit `ROUND_HALF_UP` for the closed posting set:
   BUY debit, SELL gross credit, order fee, FX credit/fee/buffer and tax reserve;
   derive signed per-posting reconciliation.
4. Implement native Broker/currency ledger.
5. Implement coupled single-hop FX and safety margin.
6. Implement whole-quantity/monetary-amount BUY/SELL instructions.
7. Implement SELL mid value removed separately from gross rounded credit,
   price/spread loss, fee/tax/net schedule and withholding semantics.
8. Implement shared `F_ref`, fixed Asset targets, residuals, exact
   valuation-currency-squared `L2_fixed`, diagnostic actual percentages/D∞/D1,
   signed `U` decomposition/rounding bound, anti-shrink identities and hard final
   nonnegativity.
9. Implement the evaluator side of typed `ConstraintSpec` and `ObjectiveStage`,
   including units and exact canonical tie values, without solver imports.
10. Implement exact required-min validation and deterministic conflict witness;
   floating solver failure alone remains non-proof.
11. Reconcile each candidate into final mid values, attributed cost, reserved
    buffer, physical free cash/reasons and signed posting-rounding adjustment.
12. Implement per-solution status classification independent of solver according
    to §7.8.
13. Expose candidate evaluator used by tests/oracle/solver/report.
14. Ask WR owner to register `services pac-planner-core` before first selector
    run.

**Specialist:** high-reasoning math owner; **test-author required**.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  services pac-planner-core
```

**Artifacts:** ledger truth tables; fee/FX/tax/rounding witnesses.

**DoD:** evaluator imports no solver; every ledger reconciles; no float; no
double-post; exact status semantics; all invariants green.

**Stop:** any candidate can pass with negative cash, oversell, duplicate posting or
non-reconciling output.

### Step 5 — Implement complete oracle, solver adapter and resource limits

**Owned surfaces**

- new `solver.py`, `oracle.py`, `limits.py`;
- solver-specific objective/formulation module if needed;
- diagnostic benchmark under `backend/test_scripts/diagnostics/`;
- tests via test-author.

**Dependency:** Step 4.

**Actions**

1. Declare supported v1 domain and finite derived bounds.
2. Build complete exhaustive oracle for small PAC and Rebalancer domains,
   including every discrete order/funding/FX combination.
3. Build the approved PySCIPOpt/SCIP adapter after the separate environment gate.
4. Implement a declarative `PolicyCompiler` that emits finite domains, hard
   `ConstraintSpec`s and sequential `ObjectiveStage`s exactly from §7.5.1; keep
   deterministic execution only for genuinely closed-form future policies.
5. Implement PAC proportional and min-fragmentation primary tuples from D26 and
   re-evaluate full native ledgers.
6. Implement Rebalancer invest-only primary
   `L2_fixed → U → turnover → cost → rows/splits → total tie`.
7. Implement sequential invest-and-sell with funding-only quantum-minimal SELL;
   require both one-quantum and whole-row counterfactuals, reuse the primary
   fixed-L2 tiers and distinguish local irreducibility from globally bounded/proven
   minimality.
8. Implement the frozen BUY-only deployment variant over immutable primary
   actions: `U → resulting L2_fixed → incremental cost/rows → total tie`.
9. Re-evaluate every incumbent, `U` component and native ledger with the Decimal
   evaluator; a deterministically corrected vector is a new candidate and inherits
   no proof/bound/frozen face.
10. Follow the stage/restart/build order in §7.9; each previous-tier constraint
    is an exact face only after exact proof and otherwise an explicitly
    conditioned incumbent ceiling.
11. Propagate score brackets, SELL-minimality bound, stop reason and the exact
    §7.8 status mapping without false optimality.
12. Enforce rational scaling, final nonnegativity, `F_final>0`, reachable
    fixed-L2 score separation and coefficient-safety envelopes plus the proof
    semantics accepted in Step 0.
13. Test medium-domain families for certified bounds, not only oracle-sized cases.
14. Apply native time/node limits below platform soft limit; checkpoint between
    lexicographic calls.
15. Test client-abort semantics and worker cleanup without claiming native
    cooperative cancellation.
16. Ask WR owner to register `services pac-planner-solver` and
    `services pac-planner-benchmark` before first selector run.
17. Run benchmark; compare all complete oracle cases.
18. Stop for developer decision if SCIP formulation, packaging or capacity fails.

**Specialist:** high-reasoning math owner; **test-author required**; independent
rubber-duck math review.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  services pac-planner-solver

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  services pac-planner-benchmark
```

**Artifacts:** PAC/Rebalancer oracle comparison matrix; fixed-L2 objective evidence;
medium-domain bound report;
supported-domain/resource report.

**DoD:** solver equals oracle on full small PAC/Rebalancer domain; deterministic
ties; valid limits; medium-domain certified
bounds; honest proof/status; accepted 4 s/5 s capacity benchmark; no unapproved
dependency change.

**Stop:** oracle mismatch, inability to represent the accepted fixed-L2 objective,
unsafe coefficient domain, unbounded variable,
payload/time overflow, cleanup failure or unacceptable benchmark.

### Step 6 — Build report/plugin and synchronize public client

**Owned surfaces**

- `backend/app/services/pac_allocator/report.py`;
- `backend/app/services/pac_allocator/__init__.py`;
- `backend/app/services/tool_plugins/pac_allocator.py`;
- Tool-specific export roots;
- generated API/Tool clients;
- Tool renderer registry;
- API/codec tests via test-author.

**Dependency:** Steps 1, 4, 5; Step 2 stable before final API sync.

**Actions**

1. Build complete strict public result from evaluator-approved candidate.
2. Keep plugin thin: validate → normalize → solve → evaluate → report.
3. Publish only operation `plan` for both existing service codes.
4. Preserve component keys `pac-allocator` and `portfolio-rebalancer`.
5. Forward `context.checkpoint`; import no domain service.
6. Replace P1 API tests with catalog/compute/diagnostic operational witnesses.
7. Run official API sync.
8. Verify generated roots, literal/discriminants, fingerprints and renderer pins.
9. Run sync twice; second diff must be empty.

**Specialist:** single Tool/codegen integration owner; **test-author required**.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  api pac-tool

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync
```

**Artifacts:** sanitized catalog/compute payloads; fingerprint table; deterministic
codegen proof.

**DoD:** two stable services, one plugin, atomic worker, no lookup, exact client
compatibility, unknown renderer fail-closed, no P1 codec.

**Stop:** generic Tool platform change required or codegen loses strict semantics.

### Step 7 — Build shared wizard, draft and result primitives

**Owned surfaces**

- `frontend/src/lib/features/tools/pac-allocator/planner/**`;
- P1 shared planner components replaced/deleted only by this owner;
- shared component tests via test-author.

**Dependency:** Step 1 fixture, Step 3; integrate Step 2/6 later.

**Actions**

1. Implement Svelte 5 nine-step shell and responsive navigation.
2. Implement draft dependency graph and exact destructive-change modal.
3. Implement funding source and operational Broker as separate steps.
4. Reuse generic inputs/selectors/modals/galleries.
5. Implement explicit source-copy apply and stale guards.
6. Implement immutable review snapshot.
7. Implement shared result status shell.
8. Implement Asset matrix, tapered ribbon, Geography and operational-table
   primitives from backend fixtures.
9. Implement DataTable desktop and card/accordion mobile projection.
10. Add accessibility, privacy, no-data and theme handling.
11. Ask WR owner to add planner unit paths to explicit
    `front-utility component-unit` list and repoint obsolete source-copy coverage in
    `front-utility core-unit` before first selector run.

**Specialist:** frontend shared owner; **test-author required**.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  front-utility component-unit

PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check
```

**Artifacts:** fixture gallery; component map; desktop/mobile synthetic snapshots.

**DoD:** approved shell/visuals represented; draft survives navigation; destructive
edits explicit; no frontend economics; mobile parity/accessibility.

**Stop:** chart/table requires recomputing backend economic facts.

### Step 8 — Implement PAC-specific UI

**Owned surfaces**

- `PacAllocatorTool.svelte`;
- `pac/**`;
- PAC-specific E2E/unit files via test-author.

**Dependency:** Steps 6 and 7.

**Actions**

1. Wire PAC source/manual paths into shared draft.
2. Expose `proportional`/`min_fragmentation`.
3. Submit exact `PacPlanInput`.
4. Render base/optimized comparison.
5. Render Target→After ribbons, Asset matrix, exposures and operational plan.
6. Cover no cash, low cash, trapped cash, no-op, hard infeasible, limit, stale and
   platform-error states.
7. Delete obsolete PAC P1 editor/result code and keys after replacements are live.

**Specialist:** frontend PAC owner; **test-author required**.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  front-utility pac-tool
```

**Artifacts:** desktop/mobile synthetic screenshots; payload/result witness.

**DoD:** complete manual/copy PAC flow, exact result tables/charts, no P1 analyzer,
no implicit order execution.

**Stop:** PAC wrapper duplicates shared shell or solver logic.

### Step 9 — Implement Rebalancer-specific UI

**Owned surfaces**

- `PortfolioRebalancerTool.svelte`;
- `rebalancer/**`;
- Rebalancer-specific E2E/unit files via test-author.

**Dependency:** Steps 6 and 7; implementation can run parallel with Step 8, but both
Playwright validations run serially in lane 6153.

**Actions**

1. Wire holdings/PMC/current distribution into shared draft.
2. Preserve canonical Asset aggregation and Broker custody rows.
3. Expose invest-only default and explicit invest-and-sell.
4. Display K* as lower bound only.
5. Render Before→Target→After ribbons, paired maps, Asset summary and operational
   SELL/BUY plan.
6. Show gross proceeds, fee, tax reserve, withholding, net reusable cash and
   remaining inventory.
7. Cover zero contribution, no-op, oversell rejection, hard infeasible, limit, stale
   and platform error.
8. Delete obsolete Rebalancer P1 editor/result code and keys.

**Specialist:** frontend Rebalancer owner; **test-author required**.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  front-utility rebalancer-tool
```

**Artifacts:** desktop/mobile synthetic screenshots; SELL ledger witness.

**DoD:** invest-only and invest-and-sell match backend semantics; no oversell or
same-Asset BUY+SELL; UI does not promise exact target when not proven.

**Stop:** custody is rounded/merged by name or tax reserve funds BUY.

### Step 10 — Complete tests and audit runner catalogue

**Owned surfaces**

- new/replaced backend tests;
- component/Vitest and Playwright specs;
- `scripts/test_runner` through one writer;
- no product changes except separately authorized fixes.

**Dependency:** Steps 1–9.

**Actions**

1. Confirm early WR lease replaced `schemas pac-analyze` with
   `schemas pac-planner`.
2. Confirm early WR lease replaced `services pac-analyze` with:
   - `services pac-planner-core`;
   - `services pac-planner-solver`;
   - `services pac-planner-benchmark`;
   - `services portfolio-allocation-source`.
3. Retain and repoint:
   - `api pac-tool`;
   - `front-utility pac-tool`;
   - `front-utility rebalancer-tool`;
   - `front-utility component-unit`;
   - `front-utility core-unit`.
4. Verify explicit Vitest file lists include `ExactQuantityInput` and planner tests;
   remove/repoint obsolete `allocationSource.test.ts`.
5. Ensure aggregate categories reach every new file.
6. Cover schema, normalizer, evaluator, oracle, solver, resources, catalog/API,
   permissions, component and E2E matrices.
7. Remove obsolete P1 tests instead of preserving old behavior.

**Specialist:** **test-author required**; one runner catalogue writer.

**Validation:** run all selectors above serially in lane 6153, then:

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py test \
  --test-port 6153 --data-dir /tmp/librefolio-r2-d \
  check-orphans
```

**Artifacts:** runner inventory diff; pass counts; oracle/property matrix.

**DoD:** no orphan tests, no translated-text/CSS selectors, no sleeps/fixed
positions/global counts, created data owned/cleaned, desktop/mobile both exercised.

**Stop:** any red requires `test-triage` before “flaky” label.

### Step 11 — Rewrite docs, i18n and CHANGELOG

**Owned surfaces**

- PAC/Rebalancer EN user guides;
- developer Tool-plugin guide where atomic snapshot boundary needs clarification;
- MkDocs nav through shared lease;
- four frontend i18n catalogues through one writer;
- `CHANGELOG.md` through one writer.

**Dependency:** stable contract/UI after Steps 8–10.

**Actions**

1. `docs-writer` rewrites EN PAC/Rebalancer guides for operational flow.
2. Document strategies, units, fees, FX, tax reserve, results/proof/limits/privacy.
3. Update developer guide with snapshot-only worker and domain-copy boundary.
4. Remove obsolete P1 labels/keys and add final UI keys through i18n CLI.
5. Do not translate docs unless developer explicitly requests translation.
6. Record translation debt/validation.
7. Add user-facing changelog entry.

**Specialist:** **docs-writer required** for EN; integration owner for i18n/CHANGELOG.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs build
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs check-links
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py mkdocs translate-validate
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py i18n audit
```

**Artifacts:** docs link report; translation-debt report; key audit.

**DoD:** active docs describe only operational v1; no P1 behavior; no unauthorized
translation; changelog user-facing.

**Stop:** docs require behavior not represented by tested contract.

### Step 12 — Combined gates, independent review and developer runbook

**Owned surfaces:** combined revision; no new feature.

**Dependency:** Steps 1–11.

**Actions**

1. Run formatter/lint/type/build gates.
2. Re-run API sync and require no diff.
3. Run targeted categories then integrated relevant suites serially.
4. Audit no DB migration/planner persistence/new dependency.
5. Run independent math/oracle review.
6. Run auth/privacy/resource/cleanup review.
7. Run code review for high-confidence regressions.
8. Verify generated/private/runtime artifacts excluded.
9. Prove port `6153` free.
10. Execute developer manual review only after green combined revision.

**Specialist:** integration owner; rubber-duck; code-review; high-reasoning
math/auth reviewer.

**Validation**

```text
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py lint
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front format --check
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front check
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py front build
PIPENV_CUSTOM_VENV_NAME=LibreFolio-SAUMUTtc pipenv run python dev.py api sync
git diff --check
lsof -nP -iTCP:6153 -sTCP:LISTEN
```

**Artifacts:** combined gate manifest; review findings/fixes; clean generated-file
audit; manual-review build/SHA.

**DoD:** zero blocking finding, all targeted evidence belongs to same revision, no
server/runtime residue, no private data.

**Stop:** any gate red, stale evidence, unowned shared edit or unresolved reviewer
finding.

## 12. Test acceptance matrix

| Family | Mandatory witnesses |
|---|---|
| Schema | required operation, strict extras, discriminants, exact target sum, monetary-step/minor-unit compatibility, bounds, nonfinite, Unicode, per-solution conditional output |
| Funding | new/existing/manual, partial selection, source=Broker, transfers, no double posting |
| Broker | existing/manual, currencies, both order kinds, fee BUY 0/SELL nonzero, regime/minus |
| Asset | canonical identity, same Asset multi-Broker, manual Asset, quote basis, missing price, classifications |
| Route | eligibility, priorities, conditional min, exact hard-min reservation/conflict witness, quantity/notional cap, excluded Broker |
| PAC | fixed `F_ref/T_a`, global discrete `L2_fixed`, whole/monetary decisions, canonical ties, competing native cash, one-time row/FX activation attribution, unavailable target, both policy tier orders, deployment BUY monotonicity, trapped cash, low budget/no-op |
| Rebalancer | fixed target, hard `F_final>0`, primary/deployment, invest-only, zero new cash, frozen invest+sell sequence, overweight zero target, no sale-to-idle-cash |
| Inventory | fractional existing quantity, whole SELL floor, monetary SELL residual, no oversell |
| Fee | fixed, percentage, min, max, zero, side-specific |
| FX | none, native, single-hop, spread witness, safety margin, fee, stale, missing, no cycle |
| Tax | gain/loss, rounding, broker-withheld/self-reserved, no carried-loss compensation |
| Objective | exact `L2_fixed` units/scaling, fixed `F_ref/T_a`, bounded signed rounding surplus `U≥-|A_round|max`, hard `h_ab_final/V_a_final≥0`, both PAC policy orders, Rebalancer tier order, exact `U` decomposition, deployment action monotonicity, visible `ΔL2`, promotion of dominating candidate, total-vector ties, no fee as investment |
| SELL proof | whole/monetary one-quantum decrement and whole-row removal, fixed-fee deactivation, tax/FX recompute, alternative declared funding, frozen-BUY exclusion, local irreducibility vs global minimality, multiple currencies |
| Solver | exhaustive oracle equality, mixed whole/monetary routes, MIQP+convex-MIQCP coefficient envelope, finite fixed-L2 score separation, safe score-lattice closure, Decimal replay/no inherited proof after correction, raw primal/dual bounds + tolerances/version/settings, cancellation, incumbent/gap/no-incumbent |
| Status | plan availability; primary/deployment no-op/incumbent/no-incumbent/infeasible; Decimal-feasible incumbent distinct from optimality; floating optimal→gap/not-proven; floating infeasible→no-incumbent/not-proven; exact oracle/score-lattice optimal proof; deterministic/oracle infeasibility proof; per-search stop/metrics; platform error |
| Auth | OWNER, OWNER 0%, unauthorized Broker fail-closed, no scenario diagnostics leak |
| Client | generated roots, fingerprint, exact version/component key, stale/account/request guards |
| UI | all nine steps, destructive modal, manual/copy, desktop/mobile, keyboard/aria/privacy |
| Result | Asset matrix, ribbons/maps, PAC/Rebalancer primary/deployment, `L2_fixed/U`/SELL proof, operational foldouts, hidden columns |

Examples `3484.14`/`3493.24` remain arithmetic witnesses under original assumptions,
not golden optima for new objective.

## 13. Manual developer review runbook

### Environment

- combined revision SHA shown in UI/handoff;
- lane `6153`, data dir `/tmp/librefolio-r2-d`;
- synthetic OWNER user and fixture only;
- no personal portfolio/export;
- backend/frontend started through `pipenv run python dev.py`;
- port verified free before/after.

### PAC review

1. Sidebar → Tools → PAC Allocator.
2. Walk all nine steps, back/forward, verify no data loss.
3. Create new funding plus partial existing Broker cash.
4. Add existing and manual operational Broker.
5. Configure `whole_quantity` and `monetary_amount`.
6. Configure BUY-free/SELL-paid fees and one FX pair.
7. Select/create Assets through existing selectors/modals.
8. Set routes/targets, review immutable snapshot and submit.
9. Inspect primary/deployment, fixed targets, `L2_fixed/U`, exposures and orders.
10. Trigger structural upstream edit; verify exact destructive warning.
11. Repeat low-budget no-op and hard-min infeasible.
12. Repeat mobile and keyboard-only.

### Rebalancer review

1. Copy holdings/PMC/current distribution.
2. Verify canonical same-Asset multi-Broker aggregation without custody loss.
3. Run invest-only; inspect K* lower-bound label plus fixed-L2
   primary/deployment comparison and actual-percentage diagnostics.
4. Verify `F_ref`, positive `F_final`, `U` and every free/reserve/loss/rounding
   component reconcile.
5. Run invest-and-sell; verify frozen invest-only actions and no sale-to-idle-cash.
6. Inspect gross SELL, fee, gain, tax reserve, withholding and net cash.
7. Verify no oversell/same-Asset BUY+SELL and inspect one-quantum
   local/global-minimality evidence.
8. Inspect Before→Target→After, paired maps and Broker plans.
9. Trigger stale source/late response/account change.
10. Trigger limit with incumbent and limit without incumbent; verify honest
    score brackets and conditional later tiers.
11. Repeat mobile and keyboard-only.

### Expected

- no real order or write;
- no hidden lookup;
- no omitted missing fact;
- every table reconciles backend ledger;
- no `optimal_proven` without exact `proof_source`; floating status remains
  bound evidence only;
- UI graphics match exact backend output;
- developer approves PAC and Rebalancer separately.

## 14. Rollback and recovery

- Each checkpoint is reviewable and independently tested.
- P1 is not retained as fallback. Failed migration remains unintegrated/unavailable.
- Schema/codegen failure: fix source schema and regenerate; never hand-edit generated
  financial types.
- Solver gate failure: stop before dependency change; preserve evaluator/oracle
  evidence and request decision.
- Domain-copy auth failure: block integration; never reduce requested scope silently.
- Shared-file conflict: freeze workstream, coordinate semantic resolution, rerun
  combined gates.
- Runtime failure: record exact command, phase, DB/files/server impact; stop exact PID;
  invalidate dependent evidence.
- Unexpected DB migration or persistent planner model: remove from scope before
  proceeding.

## 15. Deferred / `TODO_FUTURI.md`

Already registered and excluded from v1:

| Deferred extension | v1 boundary |
|---|---|
| proportional BUY split across Brokers | route priority/min-fragmentation only |
| proportional SELL split across custody | current policy/tie-break only |
| Broker closure/consolidation | no closure target |
| tax-aware/loss-compensation strategies | tax reserve only |
| persistent Broker operational profile | per-run scenario |
| persistent Asset tax rate | 26% prefill + per-run override |
| market-specific/intraday/degressive fees | fixed + rate + min/max by side/currency |
| transfer fee/limit/settlement | declared free/immediate v1 transfer |
| multi-hop/global FX routing | declared single-hop only |
| volatility-derived safety margin | explicit user input only |
| persistent manual scenarios | local draft only |

Do not duplicate TODO entries. New deferred item requires explicit developer decision.

## 16. Final Definition of Done

1. Coordinator checkpoint gate completed before any implementation.
2. Round 5/6/7 chain and normative docs are consistent.
3. P1 contract/code/tests/docs/i18n are removed, not hidden behind compatibility.
4. Public service codes/component keys remain stable at contract `1.0.0`.
5. PAC/Rebalancer accept complete immutable `plan` snapshots.
6. Worker performs no DB/provider/service lookup.
7. Native ledgers reconcile funding, transfers, FX, BUY/SELL, fee, tax and reserves.
8. Independent Decimal evaluator validates every candidate.
9. Complete small-case oracle matches the solver for mixed whole/monetary PAC
   and Rebalancer instances, including hard minima and activation costs.
10. Shared fixed-reference `L2_fixed`, distinct PAC operational tiers and frozen
    Rebalancer primary/deployment domains are represented without hidden weights
    or silent weakening.
11. Accepted SCIP adapter passes medium-domain bound, capacity, resource and
    cleanup gates.
12. Worst-case input/result fit 131,072/262,144 bytes and worker fits 4 s/5 s
    envelope.
13. Plan availability and per-solution outcome/proof/stop/metrics never
    overclaim or conflate primary with deployment.
14. Domain copy is permission-safe, read-only, complete and provenance-aware.
15. No planner DB migration; PySCIPOpt is added only through the separately
    authorized shared-environment dependency update.
16. Shared quantity/money/select/table/modal primitives are reused and transaction UX
    does not regress.
17. Approved nine-step desktop/mobile UI is delivered for both Tools.
18. Approved matrix/ribbons/maps/operational tables reflect backend facts only.
19. Manual scenarios work without DB Asset/Broker.
20. Generated client/fingerprint/renderer compatibility is deterministic/fail-closed.
21. All tests are authored through test-author and registered/reachable.
22. EN docs are authored through docs-writer; translation policy respected.
23. Combined lint/type/build/test/review gates pass on same revision.
24. Developer manual review approves PAC and Rebalancer separately.
25. Port `6153` is free; no private/runtime/generated artifact is improperly staged.

## 17. Read-only plan review record

Independent rubber-duck/math review found and this revision fixes:

| Finding | Correction |
|---|---|
| cash equation double-counted reserves | split spendable inequality from physical-cash identity |
| PAC base was over-modeled as minimax+D² and duplicated residual optimization | historical deterministic correction recorded; latest authority uses one global fixed-L2 primary plus frozen-action deployment variant |
| atomic snapshot may exceed fixed Tool bytes/time | explicit minimum domain, worst-case serialization and 4 s/5 s capacity gate |
| nonexistent `diagnostics` runner category | benchmark moved to `services pac-planner-benchmark` |
| parallel test commands conflicted on one lane | file edits may parallelize; all runtime validation serialized |
| new selectors were registered too late | early WR lease before each first selector run |
| `component-unit` explicit path list could omit new tests | mandatory list update plus `core-unit` repoint |
| two normative design files were byte-identical | one normative end-to-end file; duplicate becomes pointer |
| quantity precision conflicted with “unchanged behavior” | exact-string mutation, visual-only numeric parse, UX regression gate |
| solver-level memory stop reason was not observable | removed; memory exhaustion remains platform failure |
| stale old-workstream wording | replaced with current coordinated workstream |
| plan approval was conflated with implementation start | split Gate P0 persistence/checkpoint from later explicit Gate P1 developer authorization; reset SQL graph accordingly |

Fresh deterministic-PAC review initially returned `BLOCKED`; this revision fixes:

| Finding | Correction |
|---|---|
| greedy could starve required hard minima or overclaim infeasibility | exact Decimal reservation pre-pass + complete conflict witness |
| one status/proof envelope described two different solutions | plan availability separated from discriminated per-solution result |
| objective and display ratios were both called deviation | `d_budget` for D∞/D1; signed `r_target` display-only |
| residual scalar cash omitted additive FX/buffer | full native-ledger law on immutable-plus-additive actions |
| equal-priority rank could change per tick | rank once on first admissible quantum; no-quantum route last |
| target sum/reachability were under-specified | exact Decimal sum, unrounded target, positive-weight usable-price route |
| target shortfall conflated cost/buffer/free cash | exact Asset envelope decomposition and reason partition |
| money step could be unrepresentable | positive integer multiple of native minor unit |
| fragmentation indicator ignored base rows | `y` means final Asset×Broker row |
| stable tie was not total | lexicographic decision vector over canonical Asset/Broker order |
| guide still advertised drift-first residual | historical banners plus investment-first §8 algorithm |

Fresh Rebalancer review initially returned `BLOCKED`; this revision incorporates
all contract defects before follow-up:

| Finding | Correction |
|---|---|
| SELL mid value used but undefined | define `I_sell` at mid; book sell-vs-mid loss once and gross-credit rounding separately |
| PAC envelope omitted posting rounding | add signed per-Asset `A_round` to the exact identity and UI audit |
| rounded posting set was undecidable | close the seven posting families, debit/credit sign and one-time canonicalization |
| score separation was mistaken for a feasible generic-bisection proof | mark denominator/coefficient barrier; require safe achievable-score thresholds |
| SELL-funded phase had no tier order | reuse target-first tiers on the restricted frozen-baseline domain |
| overweight eligibility could conflict with frozen BUY | require baseline-overweight plus zero frozen BUY; global exclusion wins |
| one-quantum test could admit a cash-destroying row | require positive net proceeds and whole-row necessity too |
| cost tier could double-count FX spread | define it as `L_economic + T_self_reserved` |
| corrected incumbent could inherit proof | corrected vector is new and inherits no bound/face/proof |
| SELL step name drifted | use frozen `order_amount_step` |
| one `U_a` denoted two bounds | split `U_a^buy` and `U_a^sell` |
| fee formula dropped positive minimum at zero rate | apply `fixed + clamp(rate*N,min,max)` for every non-zero row |
| SELL local/global claims were one ambiguous enum | expose structured independent `local` and `global` fields |

The first follow-up verified all thirteen rows closed, then found three defects in
the fixes themselves: the rounding bound counted posting families instead of
instances, `C_free` omitted residual SELL cash, and FX source debit was not on the
native lattice. The design now indexes every debit/credit posting, includes net
SELL residual in reachable final cash, and makes FX source debit a native-ceiling
decision with one rounded destination credit.

A narrower second follow-up returned `READY` for those three corrections and
confirmed `U/A_round` signs plus `A_posted≥A_required`. It also found one remaining
wording ambiguity that could put `K_trapped` inside `C_free`; the exact requested
clause was applied, so `C_free` includes only route-reachable selected cash plus
net SELL residual and `K_trapped` appears solely in the extended identity. No
reviewer-reported math blocker remains.

Fresh Rebalancer-math review coverage:

| Required proof surface | Acceptance |
|---|---|
| `U=F_ref-F_final` | exact free/reserve/loss/signed-rounding decomposition plus extended trapped-cash identity |
| funding-only SELL | no sale-to-idle-cash; one-quantum local counterfactual recomputes fixed fees, tax, FX and alternative funding |
| SELL minimality | local irreducibility never overclaims global minimality |
| actual-percentage D∞/D1 | rational monotone MILP thresholds, hard `F_final>0`, finite-score separation |
| numeric safety | GCD/scaling/coefficient/activity/dynamic-range envelope and exact Decimal incumbent replay |
| proof honesty | mathematical finite termination distinguished from demonstrated production runtime/proof closure |

The PAC/Rebalancer objective and proof/status decisions are resolved at planning
level. Step 0 remains blocked on solver/capacity evidence and the object-result
capacity witness. Failure of either gate stops implementation before public
schema/code migration.
