/**
 * Backend issues and platform errors → what the user reads (C3, C8, N17).
 *
 * The backend publishes a code, a path and typed params; the UI translates
 * the code, routes the path to a wizard step and names the entity. Money
 * params go through the personal formatter, so privacy masks them.
 */
import type {ToolClientError} from '../../contracts';
import {formatPlannerMoneyPlain, formatPlannerPlainDecimal} from './format';
import {type PlannerDraft} from './draft.svelte';
import type {RequestIdMap} from './request';
import type {PlannerSource, SourceIssue} from './source';
import type {PlannerIssue, PlannerStep} from './types';

export const TOOL_ERROR_KEY_PREFIX = 'tools.pacAllocator.planner.toolErrors';

export interface PresentedIssue {
    id: string;
    code: string;
    severity: 'info' | 'warning' | 'error';
    kind: string;
    /** `null` = no step owns it (proof, result): no "Go to" button. */
    step: PlannerStep | null;
    entity: string | null;
    field: string | null;
    messageKey: string;
    fallback: string;
    values: Record<string, string>;
}

type AnyIssue = PlannerIssue | SourceIssue;
type AnyPath = AnyIssue['path'];

const SECTION_STEPS: Record<string, PlannerStep | null> = {
    input: 'scenario',
    // The user's positions are edited in the Assets step (F3a of project 67).
    holdings: 'assets',
    assets: 'assets',
    brokers: 'brokers',
    cash: 'liquidity',
    contributions: 'liquidity',
    liquidity: 'liquidity',
    funding: 'brokers',
    routing: 'routing',
    fx: 'fx',
    targets: 'targets',
    policy: 'strategy',
    // Source sections (allocation-source copy issues)
    prices: 'assets',
    classifications: 'assets',
    fx_quotes: 'fx',
    cash_balances: 'liquidity',
    current_distribution: 'targets',
    wac_contexts: null,
    proof: null,
    result: null,
};

function pathSection(path: AnyPath): string | null {
    return 'section' in path ? path.section : null;
}

function pathField(path: AnyPath): string | null {
    return 'field' in path ? path.field : null;
}

function pathEntity(path: AnyPath): {kind: string; id: string} | null {
    return 'entity_kind' in path ? {kind: path.entity_kind, id: path.entity_id} : null;
}

export function issueStep(path: AnyPath): PlannerStep | null {
    const field = pathField(path);
    if (field === 'fx_spread_rate') return 'fx';
    const section = pathSection(path);
    if (section === null) return null;
    return section in SECTION_STEPS ? SECTION_STEPS[section] : 'review';
}

/** The entity a path names, as the user knows it (a name, never an amount). */
export function entityLabel(draft: PlannerDraft, entity: {kind: string; id: string} | null, ids?: RequestIdMap): string | null {
    if (!entity) return null;
    switch (entity.kind) {
        case 'asset':
            return draft.asset(entity.id)?.name ?? entity.id;
        case 'broker':
            return draft.broker(entity.id)?.name ?? entity.id;
        case 'cash': {
            const cash = draft.cashRow(entity.id);
            if (cash) return `${draft.broker(cash.brokerKey)?.name ?? cash.brokerKey} · ${cash.currency}`;
            // A target entry for a cash cell is named «<broker id>:CURRENCY» (contract 2.0.0); the broker id has its own
            // colon (`broker:1`), so the currency is what follows the last one.
            const cut = entity.id.lastIndexOf(':');
            const broker = cut > 0 ? draft.broker(entity.id.slice(0, cut)) : undefined;
            return broker ? `${broker.name} · ${entity.id.slice(cut + 1)}` : entity.id;
        }
        case 'holding': {
            // A position of the Rebalancer (F3a of project 67): its Broker need not be among the scenario's Brokers.
            const position = draft.data.positions.find((item) => item.key === entity.id);
            if (!position) return entity.id;
            return `${draft.asset(position.assetKey)?.name ?? position.assetKey} · ${draft.broker(position.brokerKey)?.name ?? position.brokerName}`;
        }
        case 'contribution':
            return draft.contribution(entity.id)?.label || entity.id;
        case 'funding_route': {
            const ref = ids?.funding.get(entity.id);
            return ref ? (draft.broker(ref.brokerKey)?.name ?? ref.brokerKey) : entity.id;
        }
        case 'order_route': {
            const ref = ids?.routes.get(entity.id);
            if (!ref) return entity.id;
            return `${draft.asset(ref.assetKey)?.name ?? ref.assetKey} · ${draft.broker(ref.brokerKey)?.name ?? ref.brokerKey}`;
        }
        case 'fx_rate':
        case 'currency':
            return entity.id;
        case 'scenario':
        case 'solution':
        case 'order':
            return null;
        default:
            return entity.id;
    }
}

/** An issue's typed params as the sentence's values: money through the personal formatter, so privacy masks it. */
export function issueParamValues(issue: Pick<AnyIssue, 'params'>): Record<string, string> {
    const values: Record<string, string> = {};
    for (const param of issue.params as readonly Record<string, unknown>[]) {
        const name = String(param.name);
        switch (param.kind) {
            case 'money': {
                // planner: {value: {amount, currency}}; copy: {amount, currency}
                const money = (param.value ?? param) as {amount?: unknown; currency?: unknown};
                // At the currency's minor unit, `≈` when that rounds it (R14): the sum of the minimums and its base may carry
                // more digits (TL-4 of project 67), and then read as the preview's total does.
                values[name] = formatPlannerMoneyPlain(String(money.amount ?? ''), String(money.currency ?? ''), {minorUnit: true});
                break;
            }
            case 'decimal':
                values[name] = formatPlannerPlainDecimal(String(param.value));
                break;
            case 'entity_ref':
                values[name] = String(param.entity_id);
                break;
            default:
                values[name] = String(param.value);
        }
    }
    return values;
}

/**
 * The codes whose sentence names a figure of the Tool's own (TL-4 of project 67): the Rebalancer says them with its words,
 * from its own catalogue. «The cash the plan can invest» is the PAC's base; the Rebalancer's is «the total that enters the
 * plan».
 */
const REBALANCER_OWN_SENTENCES: ReadonlySet<string> = new Set(['allocation.bounds_min_sum_exceeds_reference']);

export function issueMessageKey(code: string, text: 'pac' | 'rebalancer' = 'pac'): string {
    if (text === 'rebalancer' && REBALANCER_OWN_SENTENCES.has(code)) return `tools.portfolioRebalancer.planner.issues.${code}`;
    return `tools.pacAllocator.planner.issues.${code}`;
}

export function presentIssue(issue: AnyIssue, draft: PlannerDraft, ids?: RequestIdMap, text: 'pac' | 'rebalancer' = 'pac'): PresentedIssue {
    const entity = pathEntity(issue.path);
    const values = issueParamValues(issue);
    values.code = issue.code;
    return {
        id: `${issue.code}|${JSON.stringify(issue.path)}|${JSON.stringify(issue.params)}`,
        code: issue.code,
        severity: issue.severity,
        kind: issue.kind,
        step: issueStep(issue.path),
        entity: entityLabel(draft, entity, ids),
        field: pathField(issue.path),
        messageKey: issueMessageKey(issue.code, text),
        fallback: 'The backend reported an issue ({code}).',
        values,
    };
}

export function presentIssues(issues: readonly PlannerIssue[], draft: PlannerDraft, ids?: RequestIdMap, text: 'pac' | 'rebalancer' = 'pac'): PresentedIssue[] {
    return dedupe(issues.map((issue) => presentIssue(issue, draft, ids, text)));
}

/**
 * Copy issues name snapshot rows (`asset:N`, `broker:N`, `price:asset:N:…`,
 * `cash:broker:N:CUR`, `fx:PAIR:…`); the row may not be in the draft yet, so
 * the name comes from the snapshot when the draft does not have it.
 */
export function sourceEntityLabel(draft: PlannerDraft, source: PlannerSource | null, entity: {kind: string; id: string} | null): string | null {
    if (!entity) return null;
    const assetKey = /(?:^|:)(asset:\d+)(?::|$)/.exec(entity.id)?.[1];
    const brokerKey = /(?:^|:)(broker:\d+)(?::|$)/.exec(entity.id)?.[1];
    const assetName = assetKey ? (draft.asset(assetKey)?.name ?? source?.assets.find((row) => row.asset_id === assetKey)?.name ?? assetKey) : null;
    const brokerName = brokerKey ? (draft.broker(brokerKey)?.name ?? source?.brokers.find((row) => row.broker_id === brokerKey)?.name ?? brokerKey) : null;
    if (entity.kind === 'cash_balance' && brokerName) return `${brokerName} · ${entity.id.split(':').at(-1)}`;
    if (entity.kind === 'fx_quote') return entity.id.split(':')[1] ?? entity.id;
    const parts = [assetName, brokerName].filter((part): part is string => part !== null);
    return parts.length > 0 ? parts.join(' · ') : entity.id;
}

export function presentSourceIssue(issue: SourceIssue, draft: PlannerDraft, source: PlannerSource | null): PresentedIssue {
    const presented = presentIssue(issue, draft);
    return {...presented, entity: sourceEntityLabel(draft, source, pathEntity(issue.path))};
}

export function presentSourceIssues(issues: readonly SourceIssue[], draft: PlannerDraft, source: PlannerSource | null): PresentedIssue[] {
    return dedupe(issues.map((issue) => presentSourceIssue(issue, draft, source)));
}

function dedupe(issues: PresentedIssue[]): PresentedIssue[] {
    const seen = new Set<string>();
    return issues.filter((issue) => {
        if (seen.has(issue.id)) return false;
        seen.add(issue.id);
        return true;
    });
}

// -- Platform errors (16 ToolError codes, N17) -----------------------------------

export const TOOL_ERROR_FALLBACKS: Record<string, string> = {
    unknown_tool: 'The backend does not know this tool.',
    tool_unavailable: 'The tool is unavailable on the backend right now.',
    version_mismatch: 'The tool version changed on the backend. Reload the page to get the new interface.',
    invalid_parameters: 'The backend rejected the request structure. No calculation was run.',
    input_limit_exceeded: 'The scenario is larger than the tool accepts. Remove Assets, routes or rows.',
    queue_full: 'Too many calculations are waiting. Try again in a moment.',
    queue_timeout: 'The calculation waited too long in the queue and was not started.',
    execution_limit: 'The calculation hit a resource limit of the tool platform.',
    execution_timeout: 'The calculation exceeded the execution time limit.',
    worker_crashed: 'The calculation process stopped unexpectedly.',
    execution_failed: 'An internal error of the tool stopped the calculation, and no plan was published.',
    invalid_output: 'The tool produced an output that does not match its contract. It was discarded.',
    output_limit_exceeded: 'The result is larger than the platform accepts.',
    memory_limit: 'The calculation exceeded the memory limit.',
    cleanup_failed: 'The calculation finished, but the platform could not clean up after it.',
    service_unavailable: 'The tool service is unavailable.',
};

export interface PresentedToolError {
    code: string;
    messageKey: string;
    fallback: string;
    retryable: boolean;
    issueCount: number;
}

export function presentToolError(error: {code: string; retryable: boolean; issue_count: number}): PresentedToolError {
    return {
        code: error.code,
        messageKey: `${TOOL_ERROR_KEY_PREFIX}.${error.code}`,
        fallback: TOOL_ERROR_FALLBACKS[error.code] ?? 'The tool platform reported an error ({code}).',
        retryable: error.retryable,
        issueCount: error.issue_count,
    };
}

/** Client-side failures keep the platform wording (`presentation.ts`); only the retry rule is PAC-local. */
export function clientErrorRetryable(error: ToolClientError): boolean {
    return error.kind === 'network' || error.kind === 'timeout';
}
