/**
 * profileRefresh.ts — «Aggiorna» of the «Profilo» tab with its notice (plan 68, E6c, I13): read the asset's enrichers
 * again and save what changed; the prices stay with «Sincronizza». What it wrote is often invisible (nothing changed, or
 * a voice off screen), so a toast is always owed:
 * - voices written → success with their count; nothing written → info;
 * - a source that failed (`error`, a refusal for too many requests included; a «not found» is no failure) → warning;
 * - the call failing, or the asset unknown → error;
 * - no enricher read (`enrichers_read` 0: every one bound is turned off, not installed or not configured; E6c2, PROF
 *   19/11) → a warning that nothing was read, never «nothing changed».
 * Each outcome is also the structured event the tests read: `asset.profile.refreshed` or `asset.profile.refreshFailed`.
 */
import {notify} from '$lib/stores/app/notify.svelte';
import {refreshAssetProfile} from './profileStore';

type Translate = (key: string, values?: Record<string, string | number>) => string;

export type ProfileRefreshOutcome = 'written' | 'unchanged' | 'partial' | 'none' | 'failed';

/** «Aggiorna» one asset; tell the user how it went. The asset's profile reads are forgotten either way. */
export async function refreshProfile(assetId: number, translate: Translate): Promise<ProfileRefreshOutcome> {
    const failed = () => {
        notify({name: 'asset.profile.refreshFailed', detail: {asset_id: assetId}, toast: {variant: 'error', message: translate('assets.profile.refresh.failed')}});
        return 'failed' as const;
    };
    let result;
    try {
        result = await refreshAssetProfile(assetId);
    } catch {
        return failed();
    }
    if (result.error) return failed();
    const written = result.written ?? [];
    const sourcesFailed = (result.outcomes ?? []).filter((outcome) => outcome.status === 'error').map((outcome) => outcome.code);
    const enrichersRead = result.enrichers_read ?? 0;
    const outcome: ProfileRefreshOutcome = enrichersRead === 0 ? 'none' : sourcesFailed.length ? 'partial' : written.length ? 'written' : 'unchanged';
    const toast =
        outcome === 'none'
            ? {variant: 'warning' as const, message: translate('assets.profile.refresh.noneActive')}
            : outcome === 'partial'
              ? {variant: 'warning' as const, message: translate('assets.profile.refresh.partial', {count: sourcesFailed.length, written: written.length})}
              : outcome === 'written'
                ? {variant: 'success' as const, message: translate('assets.profile.refresh.written', {count: written.length})}
                : {variant: 'info' as const, message: translate('assets.profile.refresh.unchanged')};
    notify({name: 'asset.profile.refreshed', detail: {asset_id: assetId, written, failed: sourcesFailed, enrichers_read: enrichersRead}, toast});
    return outcome;
}
