/**
 * Wire types of the planner 2.0.0, derived from the generated contract: generic roots on the Tool, and the PAC's
 * names (`Pac…`) derived from them.
 *
 * Nothing here is hand-written against the backend: every type is an
 * extraction of `ToolInput`/`ToolOutput`, so a contract change surfaces as a
 * type error instead of a silent mismatch.
 *
 * The request exists in two forms (plan-phase00PacContractCompaction §1):
 * - `PlannerRequest` is the compact body that is sent: a field holding its
 *   schema default may be left out;
 * - `PlannerResolvedRequest` is the same body as the codec parses it, every
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

export type PlannerRequest = PlannerToolRequest<'pac_allocator'>;
export type PlannerResolvedRequest = PlannerToolResolvedRequest<'pac_allocator'>;
export type PlannerResult = PlannerToolResult<'pac_allocator'>;
export type PlannerResultState = PlannerResult['result_state'];

export type PlannerFailureResult = Extract<PlannerResult, {result_state: 'needs_input' | 'invalid' | 'unsupported'}>;
export type PlannerReadyResult = Exclude<PlannerResult, PlannerFailureResult>;
export type PlannerPlanResult = Extract<PlannerResult, {result_state: 'ready_no_op' | 'ready_incumbent'}>;
export type PlannerInfeasibleResult = Extract<PlannerResult, {result_state: 'ready_infeasible'}>;
export type PlannerNoIncumbentResult = Extract<PlannerResult, {result_state: 'ready_no_incumbent'}>;

export type PlannerIssue = PlannerResult['issues'][number];
export type PlannerIssuePath = PlannerIssue['path'];
export type PlannerIssueSection = PlannerIssuePath['section'];
export type PlannerIssueParam = PlannerIssue['params'][number];

export type PlannerSolution = PlannerPlanResult['primary_solution'];
export type PlannerAssetRow = PlannerSolution['asset_rows'][number];
export type PlannerFundingAction = PlannerSolution['funding_actions'][number];
export type PlannerConversion = PlannerSolution['conversions'][number];
export type PlannerOrderRow = PlannerSolution['order_rows'][number];
export type PlannerLedgerRow = PlannerSolution['ledger_rows'][number];
export type PlannerRoundingTopUp = PlannerSolution['rounding_top_ups'][number];
export type PlannerExposureRow = PlannerSolution['exposure_rows'][number];
export type PlannerAccounting = PlannerSolution['accounting'];
export type PlannerCosts = PlannerSolution['costs'];
export type PlannerObjectiveStage = PlannerSolution['objectives']['stages'][number];

export type PlannerExactNumber = PlannerAssetRow['target_weight'];
export type PlannerExactMoney = PlannerAssetRow['target_value'];
export type PlannerNumberAvailability = PlannerAssetRow['final_weight'];
export type PlannerExactPrice = PlannerOrderRow['mid_price'];
export type PlannerExactFxRate = PlannerConversion['spot_rate'];
export type PlannerObjectiveUnit = PlannerObjectiveStage['unit'];

export type PlannerCatalogs = PlannerReadyResult['catalogs'];
export type PlannerScenarioBasis = PlannerReadyResult['scenario_basis'];
export type PlannerProof = PlannerReadyResult['proof'];
export type PlannerSolverEvidence = PlannerReadyResult['solver_evidence'];
export type PlannerSolverStage = PlannerSolverEvidence['stages'][number];
export type PlannerDeployment = PlannerPlanResult['deployment'];

export type PlannerRequestAsset = PlannerRequest['assets'][number];
export type PlannerRequestBroker = PlannerRequest['brokers'][number];
export type PlannerRequestCapability = NonNullable<PlannerRequestBroker['capabilities']>[number];
export type PlannerRequestFeeSchedule = NonNullable<PlannerRequestBroker['fee_schedules']>[number];
export type PlannerRequestCash = NonNullable<PlannerRequest['existing_cash']>[number];
export type PlannerRequestContribution = NonNullable<PlannerRequest['contributions']>[number];
export type PlannerRequestFundingRoute = NonNullable<PlannerRequest['funding_routes']>[number];
export type PlannerRequestOrderRoute = PlannerRequest['order_routes'][number];
export type PlannerRequestProvenance = PlannerRequest['provenance'][number];
export type PlannerRequestExposure = NonNullable<PlannerRequestAsset['exposures']>[number];
export type PlannerRequestPolicy = PlannerRequest['policy'];

export type PlannerResolvedAsset = PlannerResolvedRequest['assets'][number];
export type PlannerResolvedFundingRoute = PlannerResolvedRequest['funding_routes'][number];
export type PlannerResolvedOrderRoute = PlannerResolvedRequest['order_routes'][number];

/** The wizard steps, in screen order (C0 delta §3). */
export const PLANNER_STEPS = ['scenario', 'liquidity', 'brokers', 'assets', 'routing', 'targets', 'fx', 'strategy', 'review'] as const;
export type PlannerStep = (typeof PLANNER_STEPS)[number];

// The PAC's former names (F1 of project 67, step 9): aliases until step 10 removes them.
export type PacPlannerRequest = PlannerRequest;
export type PacResolvedRequest = PlannerResolvedRequest;
export type PacPlannerResult = PlannerResult;
export type PacResultState = PlannerResultState;
export type PacFailureResult = PlannerFailureResult;
export type PacReadyResult = PlannerReadyResult;
export type PacPlanResult = PlannerPlanResult;
export type PacInfeasibleResult = PlannerInfeasibleResult;
export type PacNoIncumbentResult = PlannerNoIncumbentResult;
export type PacIssue = PlannerIssue;
export type PacIssuePath = PlannerIssuePath;
export type PacIssueSection = PlannerIssueSection;
export type PacIssueParam = PlannerIssueParam;
export type PacSolution = PlannerSolution;
export type PacAssetRow = PlannerAssetRow;
export type PacFundingAction = PlannerFundingAction;
export type PacConversion = PlannerConversion;
export type PacOrderRow = PlannerOrderRow;
export type PacLedgerRow = PlannerLedgerRow;
export type PacRoundingTopUp = PlannerRoundingTopUp;
export type PacExposureRow = PlannerExposureRow;
export type PacAccounting = PlannerAccounting;
export type PacCosts = PlannerCosts;
export type PacObjectiveStage = PlannerObjectiveStage;
export type PacExactNumber = PlannerExactNumber;
export type PacExactMoney = PlannerExactMoney;
export type PacNumberAvailability = PlannerNumberAvailability;
export type PacExactPrice = PlannerExactPrice;
export type PacExactFxRate = PlannerExactFxRate;
export type PacObjectiveUnit = PlannerObjectiveUnit;
export type PacCatalogs = PlannerCatalogs;
export type PacScenarioBasis = PlannerScenarioBasis;
export type PacProof = PlannerProof;
export type PacSolverEvidence = PlannerSolverEvidence;
export type PacSolverStage = PlannerSolverStage;
export type PacDeployment = PlannerDeployment;
export type PacRequestAsset = PlannerRequestAsset;
export type PacRequestBroker = PlannerRequestBroker;
export type PacRequestCapability = PlannerRequestCapability;
export type PacRequestFeeSchedule = PlannerRequestFeeSchedule;
export type PacRequestCash = PlannerRequestCash;
export type PacRequestContribution = PlannerRequestContribution;
export type PacRequestFundingRoute = PlannerRequestFundingRoute;
export type PacRequestOrderRoute = PlannerRequestOrderRoute;
export type PacRequestProvenance = PlannerRequestProvenance;
export type PacRequestExposure = PlannerRequestExposure;
export type PacRequestPolicy = PlannerRequestPolicy;
export type PacResolvedAsset = PlannerResolvedAsset;
export type PacResolvedFundingRoute = PlannerResolvedFundingRoute;
export type PacResolvedOrderRoute = PlannerResolvedOrderRoute;
