/**
 * The actions of a data-quality issue — its `cta_action` — as a banner offers them: how an action meets what it fixes,
 * its label and its icon. Shared by the Dashboard's banner (`DataQualityBanner.svelte`) and the lots panel's
 * (`LotDataQualityBanner.svelte`, project 69 L4) through `DataQualityIssueActions.svelte`, so both draw an action the
 * same way and neither keeps a copy.
 *
 * @module components/ui/feedback/dataQualityCta
 */
import {ArrowUpRight, Coins, RefreshCw} from 'lucide-svelte';
import type {DataQualityIssue} from './DataQualityBanner.svelte';

/** The actions that work on one pair at a time: the add dialog opens on one pair, the link goes to one pair. */
export const PER_PAIR_ACTIONS: ReadonlySet<string> = new Set(['add_fx_pair', 'navigate_fx']);

/**
 * How a category's action meets what it fixes. `all`: one button fixes the whole category, so it comes first and the
 * message and items hang under it. `each-asset` and `each-pair`: the action works on one item at a time, so each item is
 * its own chip, under the message. `none`: no action, the message alone.
 */
export type FixShape = 'all' | 'each-asset' | 'each-pair' | 'none';

export function fixShape(issue: DataQualityIssue): FixShape {
    if (!issue.cta_action) return 'none';
    if (issue.cta_action === 'navigate_asset' && (issue.affected_asset_ids?.length ?? 0) > 0) return 'each-asset';
    if (PER_PAIR_ACTIONS.has(issue.cta_action) && (issue.affected_fx_pairs?.length ?? 0) > 0) return 'each-pair';
    return 'all';
}

/** Per-asset navigation targets (id + display name), zipping the two aligned backend arrays. */
export function assetTargets(issue: DataQualityIssue): {id: number; name: string}[] {
    const ids = issue.affected_asset_ids ?? [];
    const names = issue.affected_asset_names ?? [];
    return ids.map((id, i) => ({id, name: names[i] ?? `#${id}`}));
}

/** The label of an action: its catalogue entry `dataQuality.cta.<action>`, else the action's name in words. */
export function ctaLabel(translate: (key: string) => string, action: string | null | undefined): string {
    if (!action) return '';
    const key = `dataQuality.cta.${action}`;
    const translated = translate(key);
    return translated !== key ? translated : action.replace(/_/g, ' ');
}

/** The icon of an action: coins to add a pair, the sync arrows to sync, an arrow out to open a page. */
export function ctaIcon(action: string | null | undefined) {
    if (action === 'add_fx_pair') return Coins;
    if (action === 'sync_fx_pair' || action === 'sync_stale_fx' || action === 'sync_asset_prices') return RefreshCw;
    return ArrowUpRight;
}
