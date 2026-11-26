/**
 * The two actions of an asset in the Positions tab — its rows (Exposure, Contribution) and its charts (treemap, period
 * P&L): the analysis of its lots first, then its page. One list, so the four menus cannot disagree.
 *
 * @module features/dashboard/assetActions
 */
import {ExternalLink, Layers} from 'lucide-svelte';
import {goto} from '$app/navigation';
import type {ContextMenuItem} from '$lib/components/ui/ContextMenu.svelte';
import type {RowAction} from '$lib/components/table/types';

type Translate = (key: string) => string;
type OnAnalyze = ((assetId: number) => void) | undefined;

const ASSET_ACTIONS = [
    {id: 'analyze-lots', icon: Layers, label: (t: Translate) => t('brokers.lots.analyze') || 'Analyze Lots'},
    {id: 'view-asset', icon: ExternalLink, label: (t: Translate) => t('brokers.lots.viewAsset') || 'View Asset'},
] as const;

/** Runs an action of the list on `assetId`; nothing for a row without an asset or an action the list does not have. */
export function runAssetAction(actionId: string, assetId: number | null, onAnalyze: OnAnalyze): void {
    if (assetId == null) return;
    if (actionId === 'analyze-lots') onAnalyze?.(assetId);
    else if (actionId === 'view-asset') void goto(`/assets/${assetId}`);
}

/** The list as the items of a chart's `ContextMenu`. */
export function assetMenuItems(t: Translate): ContextMenuItem[] {
    return ASSET_ACTIONS.map(({id, icon, label}) => ({id, label: label(t), icon: icon as unknown as ContextMenuItem['icon']}));
}

/** The list as the row actions of a table; `onAnalyze` is read when the action runs. */
export function assetRowActions<T>(deps: {t: Translate; assetIdOf: (row: T) => number | null; onAnalyze: () => OnAnalyze}): RowAction<T>[] {
    return ASSET_ACTIONS.map(({id, icon, label}) => ({
        id,
        icon,
        label: () => label(deps.t),
        onClick: (row: T) => runAssetAction(id, deps.assetIdOf(row), deps.onAnalyze()),
    }));
}
