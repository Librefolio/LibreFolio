/**
 * The names of the Rebalancer's strategy and target fidelity (F3a of project 67, step 13), as the Review and the side
 * panel show them; the Strategy step (10b) shows the same. A name only: «Custom» never shows its euros or λ here (N1).
 * The translate function is the caller's `$t`, so the keys stay literal for the i18n audit.
 */
import type {DraftFidelity} from './draft.svelte';

type Translate = (key: string, options?: {default?: string; values?: Record<string, string | number>}) => string;

/** The Rebalancer's strategy by the draft's policy: «Invest only» (the only one before F3b). The PAC names its policies itself. */
export function rebalancerStrategyName(t: Translate, policy: string): string {
    return policy === 'invest_only' ? t('tools.portfolioRebalancer.planner.strategy.investOnly') : policy || '—';
}

/** The target fidelity's choice, by name. */
export function fidelityName(t: Translate, fidelity: DraftFidelity): string {
    if (fidelity.kind === 'custom') return t('tools.portfolioRebalancer.planner.strategy.fidelity.custom');
    if (fidelity.kind === 'target_first') return t('tools.portfolioRebalancer.planner.strategy.fidelity.targetFirst');
    switch (fidelity.level) {
        case 'cost_aware':
            return t('tools.portfolioRebalancer.planner.strategy.fidelity.costAware');
        case 'faithful':
            return t('tools.portfolioRebalancer.planner.strategy.fidelity.faithful');
        default:
            return t('tools.portfolioRebalancer.planner.strategy.fidelity.balanced');
    }
}
