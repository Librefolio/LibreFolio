/**
 * Wire types of the planner 2.0.0, derived from the generated contract: generic roots on the Tool, and the PAC's
 * names (`Pac…`) derived from them.
 *
 * Nothing here is hand-written against the backend: every type is an
 * extraction of `ToolInput`/`ToolOutput`, so a contract change surfaces as a
 * type error instead of a silent mismatch.
 *
 * The request exists in two forms (plan-phase00PacContractCompaction §1):
 * - `PacPlannerRequest` is the compact body that is sent: a field holding its
 *   schema default may be left out;
 * - `PacResolvedRequest` is the same body as the codec parses it, every
 *   default filled in. The result views read this one.
 */
import type {z} from 'zod';
import type {ToolContractMap, ToolInput, ToolOutput, ToolVersion} from '$lib/features/tools/contracts';

/** The Tools that share the planner (F1 of project 67), and the contract version they answer. */
export type PlannerToolCode = 'pac_allocator' | 'portfolio_rebalancer';
export type PlannerContractVersion = '2.0.0';

/** The planner's version of Tool `C`: `2.0.0`, written so that TypeScript can check it for a generic `C`. */
type PlannerVersionOf<C extends PlannerToolCode> = PlannerContractVersion & ToolVersion<C>;

/** The root types, generic on the Tool; the PAC when none is named. */
export type PlannerToolRequest<C extends PlannerToolCode = 'pac_allocator'> = ToolInput<C, PlannerVersionOf<C>>;
export type PlannerToolResolvedRequest<C extends PlannerToolCode = 'pac_allocator'> = z.output<ToolContractMap[C][PlannerContractVersion]['input']>;
// The services answer two operations (B4 of project 67); the planner sends ``plan`` and its views read the plan's results.
export type PlannerToolResult<C extends PlannerToolCode = 'pac_allocator'> = Extract<ToolOutput<C, PlannerVersionOf<C>>, {operation: 'plan'}>;

export type PacPlannerRequest = PlannerToolRequest<'pac_allocator'>;
export type PacResolvedRequest = PlannerToolResolvedRequest<'pac_allocator'>;
export type PacPlannerResult = PlannerToolResult<'pac_allocator'>;
export type PacResultState = PacPlannerResult['result_state'];

export type PacFailureResult = Extract<PacPlannerResult, {result_state: 'needs_input' | 'invalid' | 'unsupported'}>;
export type PacReadyResult = Exclude<PacPlannerResult, PacFailureResult>;
export type PacPlanResult = Extract<PacPlannerResult, {result_state: 'ready_no_op' | 'ready_incumbent'}>;
export type PacInfeasibleResult = Extract<PacPlannerResult, {result_state: 'ready_infeasible'}>;
export type PacNoIncumbentResult = Extract<PacPlannerResult, {result_state: 'ready_no_incumbent'}>;

export type PacIssue = PacPlannerResult['issues'][number];
export type PacIssuePath = PacIssue['path'];
export type PacIssueSection = PacIssuePath['section'];
export type PacIssueParam = PacIssue['params'][number];

export type PacSolution = PacPlanResult['primary_solution'];
export type PacAssetRow = PacSolution['asset_rows'][number];
export type PacFundingAction = PacSolution['funding_actions'][number];
export type PacConversion = PacSolution['conversions'][number];
export type PacOrderRow = PacSolution['order_rows'][number];
export type PacLedgerRow = PacSolution['ledger_rows'][number];
export type PacRoundingTopUp = PacSolution['rounding_top_ups'][number];
export type PacExposureRow = PacSolution['exposure_rows'][number];
export type PacAccounting = PacSolution['accounting'];
export type PacCosts = PacSolution['costs'];
export type PacObjectiveStage = PacSolution['objectives']['stages'][number];

export type PacExactNumber = PacAssetRow['target_weight'];
export type PacExactMoney = PacAssetRow['target_value'];
export type PacNumberAvailability = PacAssetRow['final_weight'];
export type PacExactPrice = PacOrderRow['mid_price'];
export type PacExactFxRate = PacConversion['spot_rate'];
export type PacObjectiveUnit = PacObjectiveStage['unit'];

export type PacCatalogs = PacReadyResult['catalogs'];
export type PacScenarioBasis = PacReadyResult['scenario_basis'];
export type PacProof = PacReadyResult['proof'];
export type PacSolverEvidence = PacReadyResult['solver_evidence'];
export type PacSolverStage = PacSolverEvidence['stages'][number];
export type PacDeployment = PacPlanResult['deployment'];

export type PacRequestAsset = PacPlannerRequest['assets'][number];
export type PacRequestBroker = PacPlannerRequest['brokers'][number];
export type PacRequestCapability = NonNullable<PacRequestBroker['capabilities']>[number];
export type PacRequestFeeSchedule = NonNullable<PacRequestBroker['fee_schedules']>[number];
export type PacRequestCash = NonNullable<PacPlannerRequest['existing_cash']>[number];
export type PacRequestContribution = NonNullable<PacPlannerRequest['contributions']>[number];
export type PacRequestFundingRoute = NonNullable<PacPlannerRequest['funding_routes']>[number];
export type PacRequestOrderRoute = PacPlannerRequest['order_routes'][number];
export type PacRequestProvenance = PacPlannerRequest['provenance'][number];
export type PacRequestExposure = NonNullable<PacRequestAsset['exposures']>[number];
export type PacRequestPolicy = PacPlannerRequest['policy'];

export type PacResolvedAsset = PacResolvedRequest['assets'][number];
export type PacResolvedFundingRoute = PacResolvedRequest['funding_routes'][number];
export type PacResolvedOrderRoute = PacResolvedRequest['order_routes'][number];

/** The wizard steps, in screen order (C0 delta §3). */
export const PLANNER_STEPS = ['scenario', 'liquidity', 'brokers', 'assets', 'routing', 'targets', 'fx', 'strategy', 'review'] as const;
export type PlannerStep = (typeof PLANNER_STEPS)[number];
