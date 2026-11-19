/**
 * profileForget.ts — «Dimentica» of changes of the asset profile with its notice (plan 68, E6a/E6b), one way for the
 * «Ultime variazioni» panel and the «Storia del dato» window: the rows go (a success toast with the count), the server
 * refuses them (`newer`, `not_found`: a warning, the host reads again), or the call fails (an error). Each outcome is
 * also a structured event (`asset.profile.changes.*`), the half the tests read.
 */
import {notify} from '$lib/stores/app/notify.svelte';
import {forgetProfileRows} from './profileStore';

type Translate = (key: string, values?: Record<string, string | number>) => string;

/** Forget the rows `ids` of one asset, sending back `asOf` of the read that showed them; tell the user how it went. */
export async function forgetChanges(assetId: number, ids: number[], asOf: string, translate: Translate): Promise<void> {
    try {
        const outcome = await forgetProfileRows(assetId, ids, asOf);
        if (outcome.kind === 'forgotten') {
            notify({name: 'asset.profile.changes.forgotten', detail: {asset_id: assetId, deleted: outcome.deleted}, toast: {variant: 'success', message: translate('assets.profile.changes.forgotten', {count: outcome.deleted})}});
        } else {
            notify({name: 'asset.profile.changes.refused', detail: {asset_id: assetId, reason: outcome.kind, update_ids: outcome.updateIds}, toast: {variant: 'warning', message: translate(outcome.kind === 'newer' ? 'assets.profile.changes.newer' : 'assets.profile.changes.notFound')}});
        }
    } catch {
        notify({name: 'asset.profile.changes.forgetFailed', detail: {asset_id: assetId}, toast: {variant: 'error', message: translate('assets.profile.changes.forgetFailed')}});
    }
}
