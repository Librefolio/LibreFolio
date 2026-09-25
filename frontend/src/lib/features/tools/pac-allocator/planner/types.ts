/**
 * Wire types of the PAC planner 2.0.0, derived from the generated contract.
 *
 * Nothing here is hand-written against the backend: every type is an
 * extraction of `ToolInput`/`ToolOutput`, so a contract change surfaces as a
 * type error instead of a silent mismatch.
 */
import type {ToolInput, ToolOutput} from '$lib/features/tools/contracts';

export type PacPlannerRequest = ToolInput<'pac_allocator', '2.0.0'>;
export type PacPlannerResult = ToolOutput<'pac_allocator', '2.0.0'>;
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
export type PacFxAction = PacSolution['fx_actions'][number];
export type PacOrderRow = PacSolution['order_rows'][number];
export type PacLedgerRow = PacSolution['ledger_rows'][number];
export type PacExposureRow = PacSolution['exposure_rows'][number];
export type PacAccounting = PacSolution['accounting'];
export type PacCosts = PacSolution['costs'];
export type PacObjectiveStage = PacSolution['objectives']['stages'][number];

export type PacExactNumber = PacAssetRow['target_weight'];
export type PacExactMoney = PacAssetRow['target_value'];
export type PacNumberAvailability = PacAssetRow['final_weight'];
export type PacExactPrice = PacOrderRow['mid_price'];
export type PacExactFxRate = PacFxAction['spot_rate'];
export type PacObjectiveUnit = PacObjectiveStage['unit'];

export type PacCatalogs = PacReadyResult['catalogs'];
export type PacScenarioBasis = PacReadyResult['scenario_basis'];
export type PacProof = PacReadyResult['proof'];
export type PacSolverEvidence = PacReadyResult['solver_evidence'];
export type PacSolverStage = Extract<PacSolverEvidence, {kind: 'reported_floating'}>['stages'][number];
export type PacDeployment = PacPlanResult['deployment'];

export type PacRequestAsset = PacPlannerRequest['assets'][number];
export type PacRequestBroker = PacPlannerRequest['brokers'][number];
export type PacRequestCapability = PacRequestBroker['capabilities'][number];
export type PacRequestFeeSchedule = PacRequestBroker['fee_schedules'][number];
export type PacRequestCash = PacPlannerRequest['existing_cash'][number];
export type PacRequestContribution = PacPlannerRequest['contributions'][number];
export type PacRequestFundingRoute = PacPlannerRequest['funding_routes'][number];
export type PacRequestOrderRoute = PacPlannerRequest['order_routes'][number];
export type PacRequestProvenance = PacPlannerRequest['provenance'][number];
export type PacRequestExposure = PacRequestAsset['exposures'][number];
export type PacRequestPolicy = PacPlannerRequest['policy'];

/** The wizard steps, in screen order (C0 delta §3). */
export const PLANNER_STEPS = ['scenario', 'liquidity', 'brokers', 'assets', 'routing', 'targets', 'fx', 'strategy', 'review'] as const;
export type PlannerStep = (typeof PLANNER_STEPS)[number];
