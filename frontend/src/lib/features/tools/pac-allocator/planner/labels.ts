/** i18n keys and English defaults shared by the planner screens. */
import type {LocalProblem} from './request';
import type {PresentedIssue} from './issues';
import type {PlannerStep} from './types';

// Every planner module declares its own quoted namespace constant: `dev.py i18n audit`
// (scripts/i18n_usage.py) resolves only same-file string literals, and dotted backend
// codes need a literal template head. An imported prefix makes every key look dead.
const PLANNER_KEY = 'tools.pacAllocator.planner';

export const STEP_FALLBACKS: Readonly<Record<PlannerStep, string>> = {
    scenario: 'Scenario',
    liquidity: 'Liquidity',
    brokers: 'Brokers',
    assets: 'Assets',
    routing: 'Routing',
    targets: 'Targets',
    fx: 'FX',
    strategy: 'Strategy',
    review: 'Review',
};

export function stepKey(step: PlannerStep): string {
    return `${PLANNER_KEY}.steps.${step}`;
}

/** One row of an issue list: a local problem (D8) or a backend/copy issue (D9–D10). */
export interface ListedIssue {
    id: string;
    step: PlannerStep | null;
    entity: string | null;
    key: string;
    fallback: string;
    values: Record<string, string>;
    code: string | null;
    severity: 'info' | 'warning' | 'error';
}

export function listLocalProblem(problem: LocalProblem): ListedIssue {
    return {id: problem.id, step: problem.step, entity: problem.entity, key: `tools.pacAllocator.planner.problems.${problem.key}`, fallback: problem.fallback, values: problem.values, code: null, severity: 'error'};
}

export function listIssue(issue: PresentedIssue): ListedIssue {
    return {id: issue.id, step: issue.step, entity: issue.entity, key: issue.messageKey, fallback: issue.fallback, values: issue.values, code: issue.code, severity: issue.severity};
}

export const ORIGIN_FALLBACKS = {copied: 'Copied', manual: 'Manual', modified: 'Modified'} as const;

export const MODE_KIND_FALLBACKS = {whole_quantity: 'By number of units', monetary_amount: 'By amount'} as const;

export const DIMENSION_FALLBACKS = {asset_type: 'Asset type', geography: 'Geography', sector: 'Sector'} as const;
