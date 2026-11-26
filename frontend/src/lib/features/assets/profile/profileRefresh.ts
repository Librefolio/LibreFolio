/**
 * profileRefresh.ts — «Aggiorna» of the «Profilo» tab with its notice (plan 68, E6c, I13): read the asset's enrichers
 * again and save what changed; the prices stay with «Sincronizza». What it wrote is often invisible (nothing changed, or
 * a voice off screen), so a toast is always owed:
 * - voices written → success with their count; nothing written → info;
 * - a source that failed (`error`, a refusal for too many requests included; a «not found» is no failure) → warning;
 * - the call failing, or the asset unknown → error;
 * - no enricher read (`enrichers_read` 0: every one bound is turned off, not installed or not configured; E6c2, PROF
 *   19/11) → a warning that nothing was read, never «nothing changed».
 * «Riallinea i profili» (87, A5) does the same for many assets in one call, and says it with one toast: how many assets were
 * read, how many data changed, how many sources did not answer. Its call has no progress to show and may outlast the wait:
 * then the server goes on by itself, and the toast says so (`running`), never «failed».
 * Each outcome is also the structured event the tests read: `asset.profile.refreshed` or `asset.profile.refreshFailed`.
 */
import {notify} from '$lib/stores/app/notify.svelte';
import {refreshAssetProfile, refreshAssetProfiles, type ProfileRefreshResult} from './profileStore';

type Translate = (key: string, values?: Record<string, string | number>) => string;

export type ProfileRefreshOutcome = 'written' | 'unchanged' | 'partial' | 'none' | 'failed';

/** The sources of a refresh that failed, by code (a «not found» is no failure). */
export function failedSources(result: ProfileRefreshResult): string[] {
    return (result.outcomes ?? []).filter((outcome) => outcome.status === 'error').map((outcome) => outcome.code);
}

/** How the refresh of one asset went. */
export function refreshOutcome(result: ProfileRefreshResult): ProfileRefreshOutcome {
    if (result.error) return 'failed';
    if ((result.enrichers_read ?? 0) === 0) return 'none';
    if (failedSources(result).length) return 'partial';
    return (result.written ?? []).length ? 'written' : 'unchanged';
}

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
    const sourcesFailed = failedSources(result);
    const enrichersRead = result.enrichers_read ?? 0;
    const outcome = refreshOutcome(result);
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

/** How a refresh of many assets ended: one result per asset, or the server still at it, or the call refused. */
export type ProfilesRefresh = {kind: 'done'; results: ProfileRefreshResult[]} | {kind: 'running'} | {kind: 'failed'};

/** The wait ended before the answer (the browser's, or a proxy's): the server goes on reading and saving by itself. */
function stillRunning(error: unknown): boolean {
    const {code, response} = (error ?? {}) as {code?: unknown; response?: {status?: unknown}};
    return code === 'ECONNABORTED' || code === 'ETIMEDOUT' || response?.status === 502 || response?.status === 504;
}

/** «Riallinea i profili»: read the enrichers of those assets in one call; tell the user how it went. */
export async function refreshProfiles(assetIds: number[], translate: Translate): Promise<ProfilesRefresh> {
    let results: ProfileRefreshResult[];
    try {
        results = await refreshAssetProfiles(assetIds);
    } catch (error) {
        const running = stillRunning(error);
        notify({
            name: running ? 'asset.profiles.refreshRunning' : 'asset.profiles.refreshFailed',
            detail: {assets: assetIds.length},
            toast: running ? {variant: 'info', message: translate('assets.profile.bulk.stillRunning')} : {variant: 'error', message: translate('assets.profile.refresh.failed')},
        });
        return {kind: running ? 'running' : 'failed'};
    }
    const outcomes = results.map(refreshOutcome);
    const written = results.reduce((sum, result) => sum + (result.written ?? []).length, 0);
    const sourcesFailed = new Set(results.flatMap(failedSources)).size;
    const failed = outcomes.filter((outcome) => outcome === 'failed').length;
    const read = outcomes.filter((outcome) => outcome !== 'failed' && outcome !== 'none').length;
    const toast =
        read === 0 && failed === 0
            ? {variant: 'warning' as const, message: translate('assets.profile.bulk.noneActive')}
            : sourcesFailed || failed
              ? {variant: 'warning' as const, message: translate('assets.profile.bulk.partial', {read, written, sources: sourcesFailed, failed})}
              : {variant: 'success' as const, message: translate('assets.profile.bulk.done', {read, written})};
    notify({name: 'asset.profiles.refreshed', detail: {assets: assetIds.length, read, written, sources_failed: sourcesFailed, failed}, toast});
    return {kind: 'done', results};
}
