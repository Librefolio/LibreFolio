# Round 7 — PAC/Rebalancer operational migration

**Status:** PLANNING PERSISTENCE APPROVED / IMPLEMENTATION FROZEN.
**Implementation:** separately forbidden until coordinator SHA is verified and
developer grants Gate P1 start authorization.
**Durable location:**
`LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/plan-phase00Step2Round7-PacRebalancerOperationalMigration.prompt.md`

← Previous:
[Round 6 — PAC/Rebalancer UI Blueprint](plan-phase00Step2Round6-PacRebalancerUiBlueprint.prompt.md)

**Normative product flow:**
[PAC/Rebalancer end-to-end design](pac-rebalancer-end-to-end-design.md).

**Approved UI source:**
[PAC/Rebalancer UI Blueprint](pac-rebalancer-ui-blueprint.md).

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
   `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/pac-rebalancer-ui-blueprint.md`;
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
  `proportional` or `min_fragmentation`;
- `portfolio_rebalancer`: plans toward whole-portfolio targets using
  `invest_only` or explicit `invest_and_sell`.

Both consume a complete immutable snapshot, compute without DB/provider/service
lookups, return base plus residual-optimized plans, and present approved
desktop/mobile wizard and results.

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

1. status/outcome/proof/stop/limits;
2. base versus residual-optimized plan;
3. Asset allocation comparison;
4. Type/Sector/Geography before-target-after;
5. Asset summary;
6. foldable operational plan:
   - funding/transfers;
   - FX conversions;
   - one Broker order panel per Broker;
7. exact ledgers, constraints, reasons and diagnostics.

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
| D15 | PAC policies: `proportional`, `min_fragmentation` | frozen |
| D16 | Rebalancer modes: `invest_only` default, `invest_and_sell` explicit | frozen |
| D17 | Residual optimization is orthogonal and always returned beside immutable base | frozen |
| D18 | Tax schedule: SELL fee → positive gain → rounded reserve → net reusable proceeds | frozen |
| D19 | `withholding_kind` derived from regime; carried losses informational in v1 | frozen |
| D20 | UI Blueprint A–D/final is approved; no aesthetic gate remains | frozen |
| D21 | Reuse/generalize existing UI primitives; migrate transaction quantity editor first | frozen |
| D22 | Use SciPy/HiGHS only if oracle, benchmark, cancellation and resource gates pass | developer selected |
| D23 | If SciPy/HiGHS gate fails, stop and request approval before any new solver dependency | hard stop |
| D24 | Keep current API/E2E runner action names; replace only obsolete P1 schema/service actions | frozen |
| D25 | One shared writer owns generated client, registry, runner, i18n and CHANGELOG | frozen |
| D26 | Default objective remains exact `max deviation → sum squared deviation`; inability to encode tier 2 is a solver-gate failure, not permission to weaken objective | hard stop |
| D27 | Atomic payload/result must fit fixed Tool ceilings: 131,072 input bytes, 262,144 result bytes, 4 s soft and 5 s hard execution | hard stop |
| D28 | Parallel workstreams share one runtime lane; implementation may overlap, validation is serialized | frozen |
| D29 | Runner owner registers final test paths before each workstream's first selector run; Step 10 audits rather than first wiring them | frozen |

**Open product decisions:** none. Any later change to units, order enum, fee/FX/tax
schedule, objectives or approved visuals reopens Step 0 and math/UI review.

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
```

Invariants:

- source available/selected currencies match;
- `0 <= selected <= available` when maximum is known;
- new funding has no fake pre-existing balance;
- same source is posted once even when it is also an operational Broker;
- `funding_routes` names only selected destination Brokers/currencies;
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
- no inferred route to unselected Broker.

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
  fx_safety_margin_rate,
  fixed_fee?
}
```

`fx_safety_margin_rate` is reserved source cash, not fee or investment. Result exposes
`fx_safety_margin_amount`.

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
  outcome = "no_op" | "infeasible_proven" | "incumbent_found" | "no_incumbent",
  proof = "optimal_proven" | "gap_bounded" | "not_proven",
  stop_reason = "completed" | "time_limit" | "node_limit" | "cancelled",
  limits,
  objective_values,
  base_solution?,
  residual_optimized_solution?,
  issues[],
  normalized_snapshot_digest
}
```

Rules:

- missing required fact → `needs_input`;
- supplied contradiction/malformed relationship → `invalid`;
- understood but outside supported domain → `unsupported`;
- hard explicit constraints can yield `infeasible_proven`;
- low cash/no useful route/min-if-operated not reached normally yields `no_op`;
- timeout with incumbent never says optimal;
- timeout without incumbent is `no_incumbent/not_proven`;
- crash, output validation, cleanup or platform timeout remains Tool error;
- base + optimized required for `no_op` and `incumbent_found`;
- optimized may equal base with exact zero delta.

Each solution includes:

- funding and transfer actions;
- coupled FX actions;
- Broker plans and orders;
- Asset-level target/actual/residual summaries;
- cash ledgers per Broker/currency;
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
  - fx_safety_margin
>= 0
```

Physical closing cash is a separate identity:

```text
physical_final =
  spendable_final
  + fx_safety_margin
  + self_reserved_tax
```

`broker_withheld_tax` has left the account and is not added back. Evaluator reconciles
both relations separately; reserved cash is never counted as both outflow and final
physical cash in one equality.

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

PAC proportional:

1. minimize maximum target deviation;
2. minimize exact sum of squared deviations;
3. apply policy cost/priority tie-breaks;
4. stable deterministic ID tie-break.

PAC min-fragmentation:

1. never worsen proportional objective tuple;
2. never invest less than base;
3. minimize split Assets;
4. minimize order rows;
5. apply Broker priority;
6. minimize fees;
7. stable tie-break.

Residual optimization:

- starts from immutable base;
- may add BUY only;
- cannot move/remove base orders or introduce SELL;
- cannot worsen base objective;
- maximizes additional mid investment then minimizes incremental fee/rows.

Rebalancer:

- `invest_only` is default;
- `K*` is displayed only as continuous, fee-free lower bound;
- `invest_and_sell` freezes best invest-only candidate, then permits SELL only when
  residual gap improves;
- new liquidity is used first;
- SELL only overweight;
- then minimize turnover, costs, rows and stable tie-break.

The squared-deviation tier is normative. Returning `not_proven` because the selected
solver cannot represent that objective is not acceptable default behavior. Before
schema/code freeze, Step 0 must prove an exact finite linear formulation for the
declared supported domain—for example exact integer scaling plus a proven
linearization/refinement of the tier-1-optimal face—or trigger D23. An approximation,
piecewise heuristic or replacement with absolute deviation is a product change.

### 7.6 SciPy/HiGHS gate

Approved dependency policy:

1. use existing SciPy/HiGHS only;
2. represent decision ticks with finite bounds derived from cash/inventory;
3. keep Decimal evaluator authoritative;
4. allow solver-side numeric encoding only when every coefficient/tick stays inside a
   documented exact/safe domain;
5. prove an exact encoding/search closure for squared-deviation tier before
   implementation proceeds;
6. compare solver against complete exhaustive oracle on all small cases;
7. test medium supported-domain families where exhaustive oracle is unavailable and
   require a meaningful certified bound;
8. benchmark cold start, solve time, memory observation, time/node limits and worker
   cleanup;
9. bound each native solver call below platform soft timeout and checkpoint between
   lexicographic calls;
10. treat client abort as “stop waiting”, not a false cancellation acknowledgement;
    platform worker termination/cleanup remains authoritative;
11. never claim secondary-objective proof unless valid bound/search closure proves it;
12. if formulation, correctness, capacity or supported-domain gates fail, stop before
    manifest change and ask developer whether to add a dedicated solver dependency.

No arbitrary Big-M. Every bound derives from selected cash, instruction step, price,
fees or inventory.

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
5. Freeze evaluator/solver objective order and proof rules.
6. Prove exact linear/search formulation for squared-deviation objective in the
   minimum supported domain; trigger D23 if impossible with SciPy/HiGHS.
7. Build maximum-input and maximum-two-solution-result JSON witnesses; prove
   131,072/262,144-byte ceilings.
8. Allocate 4 s soft / 5 s hard execution budget across cold start, solver, Decimal
   evaluation, serialization and output validation.
9. Freeze final test file paths and runner actions for early WR lease.
10. Add sanitized numeric witnesses for fee, FX, tax, low cash and no-op.
11. Run independent math/logic review; fix blockers before code.

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

**DoD:** no contradictory active contract, no open product question, no obsolete
fractional flag/quantity step, exact tier-2 formulation accepted, minimum supported
domain fits fixed Tool envelopes, reviewer finds no blocker.

**Stop:** any change to approved behavior, unresolved formula, payload/result overflow,
execution-budget miss or objective not exactly representable.

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
7. Add regression tests for transaction create/edit/paired layouts.
8. Ask WR owner to add new tests to explicit `front-utility component-unit` path list
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
3. Implement minor-unit `ROUND_HALF_UP`.
4. Implement native Broker/currency ledger.
5. Implement coupled single-hop FX and safety margin.
6. Implement whole-quantity/monetary-amount BUY/SELL instructions.
7. Implement SELL gross/fee/tax/net schedule and withholding semantics.
8. Implement PAC/Rebalancer objective evaluation.
9. Implement status classification independent of solver.
10. Expose candidate evaluator used by tests/oracle/solver/report.
11. Ask WR owner to register `services pac-planner-core` before first selector
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
2. Build complete exhaustive oracle for small instances.
3. Build SciPy/HiGHS adapter for feasibility and lexicographic stages.
4. Implement PAC proportional/min-fragmentation.
5. Implement Rebalancer invest-only then sequential invest-and-sell.
6. Implement immutable residual-addition pass.
7. Re-evaluate every incumbent with Decimal evaluator.
8. Propagate best bound/gap/stop reason without false optimality.
9. Enforce exact squared-deviation formulation accepted in Step 0.
10. Test medium-domain families for certified bounds, not only oracle-sized cases.
11. Apply native time/node limits below platform soft limit; checkpoint between
    lexicographic calls.
12. Test client-abort semantics and worker cleanup without claiming native
    cooperative cancellation.
13. Ask WR owner to register `services pac-planner-solver` and
    `services pac-planner-benchmark` before first selector run.
14. Run benchmark; compare all complete oracle cases.
15. Stop for developer decision if SciPy/HiGHS gate fails.

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

**Artifacts:** oracle comparison matrix; exact objective-formulation evidence;
medium-domain bound report; supported-domain/resource report.

**DoD:** exact equality to oracle on full small domain; deterministic ties; valid
limits; medium-domain certified bounds; honest proof/status; accepted 4 s/5 s
capacity benchmark; no dependency change.

**Stop:** oracle mismatch, inability to represent exact squared objective, unsafe
coefficient domain, unbounded variable, payload/time overflow, cleanup failure or
unacceptable benchmark.

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
| Schema | required operation, strict extras, discriminants, bounds, nonfinite, Unicode, conditional output |
| Funding | new/existing/manual, partial selection, source=Broker, transfers, no double posting |
| Broker | existing/manual, currencies, both order kinds, fee BUY 0/SELL nonzero, regime/minus |
| Asset | canonical identity, same Asset multi-Broker, manual Asset, quote basis, missing price, classifications |
| Route | eligibility, priorities, conditional min, hard min, quantity/notional cap, excluded Broker |
| PAC | zero initial, proportional, min-fragmentation, trapped cash, low budget/no-op |
| Rebalancer | invest-only, zero new cash, invest+sell sequence, overweight zero target |
| Inventory | fractional existing quantity, whole SELL floor, monetary SELL residual, no oversell |
| Fee | fixed, percentage, min, max, zero, side-specific |
| FX | none, native, single-hop, spread witness, safety margin, fee, stale, missing, no cycle |
| Tax | gain/loss, rounding, broker-withheld/self-reserved, no carried-loss compensation |
| Objective | base immutable, residual monotone, deterministic ties, no fee as investment |
| Solver | exhaustive oracle equality, finite derived bounds, cancellation, incumbent/gap/no-incumbent |
| Status | needs_input, invalid, unsupported, no-op, infeasible proven, limit states, platform error |
| Auth | OWNER, OWNER 0%, unauthorized Broker fail-closed, no scenario diagnostics leak |
| Client | generated roots, fingerprint, exact version/component key, stale/account/request guards |
| UI | all nine steps, destructive modal, manual/copy, desktop/mobile, keyboard/aria/privacy |
| Result | Asset matrix, ribbons/maps, base/optimized, operational foldouts, hidden columns |

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
9. Inspect base/optimized, Asset matrix, exposures, funding/FX/Broker orders.
10. Trigger structural upstream edit; verify exact destructive warning.
11. Repeat low-budget no-op and hard-min infeasible.
12. Repeat mobile and keyboard-only.

### Rebalancer review

1. Copy holdings/PMC/current distribution.
2. Verify canonical same-Asset multi-Broker aggregation without custody loss.
3. Run invest-only; inspect K* lower-bound label.
4. Run invest-and-sell; verify use-new-cash-first.
5. Inspect gross SELL, fee, gain, tax reserve, withholding and net cash.
6. Verify no oversell/same-Asset BUY+SELL.
7. Inspect Before→Target→After, paired maps and Broker plans.
8. Trigger stale source/late response/account change.
9. Trigger limit with incumbent and limit without incumbent.
10. Repeat mobile and keyboard-only.

### Expected

- no real order or write;
- no hidden lookup;
- no omitted missing fact;
- every table reconciles backend ledger;
- no “optimal” without proof;
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
9. Complete small-case oracle matches solver.
10. Exact squared-deviation objective is represented/proven, not weakened.
11. SciPy/HiGHS passes medium-domain bound, capacity, resource and cleanup gates.
12. Worst-case input/result fit 131,072/262,144 bytes and worker fits 4 s/5 s
    envelope.
13. Outcome/proof/stop never overclaim.
14. Domain copy is permission-safe, read-only, complete and provenance-aware.
15. No planner DB migration or new dependency.
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
| SciPy/HiGHS cannot silently weaken squared objective | exact-formulation Step 0 gate + medium-domain bound gate + D23 stop |
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

No blocker remains at planning level. Step 0 intentionally remains a hard empirical
gate: inability to prove exact squared objective or platform capacity stops
implementation before public schema/code migration.
