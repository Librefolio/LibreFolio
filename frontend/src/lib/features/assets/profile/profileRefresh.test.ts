/**
 * profileRefresh — «Aggiorna» of the «Profilo» tab with its notice (plan 68, E6c). What the refresh wrote is often
 * invisible (nothing changed, or a voice off screen), so a toast is always owed:
 * - voices written → success with their count; nothing written → info;
 * - a source that failed (`error`, a refusal for too many requests included) → warning: the read is partial;
 * - the call failing, or the asset unknown → error;
 * - E6c2 (PROF 19/11): no enricher read (`enrichers_read` 0: every one bound is off, not installed or not configured) →
 *   a warning that nothing was read, never «nothing changed».
 * 87 A5, «Riallinea i profili»: one call for many assets, one toast for all of them; a wait that ends before the answer is
 * «the server goes on», never «failed».
 * Each outcome is also the event the tests read: `asset.profile.refreshed` (with the voices written and the sources that
 * failed) or `asset.profile.refreshFailed`.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import type {NotifyOptions} from '$lib/stores/app/notify.svelte';

const mocks = vi.hoisted(() => ({refreshAssetProfile: vi.fn(), refreshAssetProfiles: vi.fn()}));
vi.mock('./profileStore', () => ({refreshAssetProfile: mocks.refreshAssetProfile, refreshAssetProfiles: mocks.refreshAssetProfiles}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));

import {notify} from '$lib/stores/app/notify.svelte';
import {refreshProfile, refreshProfiles} from './profileRefresh';

const translate = (key: string, values?: Record<string, string | number>) => (values ? `${key} ${JSON.stringify(values)}` : key);

function outcome(code: string, status: string, errorCode: string | null = null) {
    return {code, identifier_type: 'ISIN', identifier: 'X', status, voices: [], error_code: errorCode, retry_after: null, from_cache: false};
}

function events(): NotifyOptions[] {
    return vi.mocked(notify).mock.calls.map(([event]) => event);
}

beforeEach(() => vi.clearAllMocks());

describe('refreshProfile', () => {
    it('tells how many voices it wrote', async () => {
        mocks.refreshAssetProfile.mockResolvedValue({asset_id: 7, written: ['ter', 'fund_size'], outcomes: [outcome('justetf', 'ok')], error: null, enrichers_read: 1});

        await expect(refreshProfile(7, translate)).resolves.toBe('written');
        expect(mocks.refreshAssetProfile).toHaveBeenCalledWith(7);
        const [event] = events();
        expect(event.name).toBe('asset.profile.refreshed');
        expect(event.detail).toEqual({asset_id: 7, written: ['ter', 'fund_size'], failed: [], enrichers_read: 1});
        expect(event.toast).toEqual({variant: 'success', message: 'assets.profile.refresh.written {"count":2}'});
    });

    it('says so when nothing changed: a source that does not know the asset is no failure', async () => {
        mocks.refreshAssetProfile.mockResolvedValue({asset_id: 7, written: [], outcomes: [outcome('justetf', 'ok'), outcome('yahoo', 'not_found')], error: null, enrichers_read: 1});

        await expect(refreshProfile(7, translate)).resolves.toBe('unchanged');
        expect(events()[0].toast?.variant).toBe('info');
    });

    it('warns when a source failed, the voices written still counted', async () => {
        mocks.refreshAssetProfile.mockResolvedValue({asset_id: 7, written: ['ter'], outcomes: [outcome('justetf', 'ok'), outcome('yahoo', 'error', 'RATE_LIMITED')], error: null, enrichers_read: 1});

        await expect(refreshProfile(7, translate)).resolves.toBe('partial');
        const [event] = events();
        expect(event.detail).toEqual({asset_id: 7, written: ['ter'], failed: ['yahoo'], enrichers_read: 1});
        expect(event.toast?.variant).toBe('warning');
    });

    it('says nothing was read when no enricher bound could be read (E6c2)', async () => {
        mocks.refreshAssetProfile.mockResolvedValue({asset_id: 7, written: [], outcomes: [], error: null, enrichers_read: 0});

        await expect(refreshProfile(7, translate)).resolves.toBe('none');
        const [event] = events();
        expect(event.name).toBe('asset.profile.refreshed');
        expect(event.detail).toEqual({asset_id: 7, written: [], failed: [], enrichers_read: 0});
        expect(event.toast).toEqual({variant: 'warning', message: 'assets.profile.refresh.noneActive'});
    });

    it.each([
        ['the call fails', () => mocks.refreshAssetProfile.mockRejectedValue(new Error('boom'))],
        ['the asset is unknown', () => mocks.refreshAssetProfile.mockResolvedValue({asset_id: 7, written: [], outcomes: [], error: 'Asset not found'})],
    ])('reports an error when %s', async (_case, arrange) => {
        arrange();

        await expect(refreshProfile(7, translate)).resolves.toBe('failed');
        const [event] = events();
        expect(event.name).toBe('asset.profile.refreshFailed');
        expect(event.toast?.variant).toBe('error');
    });
});

describe('refreshProfiles (87 A5)', () => {
    const asset = (id: number, fields: Record<string, unknown> = {}) => ({asset_id: id, written: [], outcomes: [outcome('justetf', 'ok')], error: null, enrichers_read: 1, ...fields});

    it('asks every asset in one call and says with one toast what came of it', async () => {
        const results = [asset(1, {written: ['ter', 'fund_size']}), asset(2)];
        mocks.refreshAssetProfiles.mockResolvedValue(results);

        await expect(refreshProfiles([1, 2], translate)).resolves.toEqual({kind: 'done', results});
        expect(mocks.refreshAssetProfiles).toHaveBeenCalledTimes(1);
        expect(mocks.refreshAssetProfiles).toHaveBeenCalledWith([1, 2]);
        expect(events()).toEqual([{name: 'asset.profiles.refreshed', detail: {assets: 2, read: 2, written: 2, sources_failed: 0, failed: 0}, toast: {variant: 'success', message: 'assets.profile.bulk.done {"read":2,"written":2}'}}]);
    });

    it('warns once for a source that failed on many assets, and for an asset not read', async () => {
        const down = [outcome('yahoo', 'error', 'RATE_LIMITED')];
        mocks.refreshAssetProfiles.mockResolvedValue([asset(1, {outcomes: down}), asset(2, {outcomes: down}), asset(3, {error: 'Asset not found', enrichers_read: 0, outcomes: []})]);

        await refreshProfiles([1, 2, 3], translate);
        const [event] = events();
        expect(event.detail).toEqual({assets: 3, read: 2, written: 0, sources_failed: 1, failed: 1});
        expect(event.toast?.variant).toBe('warning');
    });

    it('never says «nothing changed» when no enricher could be read', async () => {
        mocks.refreshAssetProfiles.mockResolvedValue([asset(1, {outcomes: [], enrichers_read: 0})]);

        await refreshProfiles([1], translate);
        expect(events()[0].toast).toEqual({variant: 'warning', message: 'assets.profile.bulk.noneActive'});
    });

    it.each([
        ['the browser stops waiting', {code: 'ECONNABORTED'}],
        ['a proxy stops waiting', {code: 'ERR_BAD_RESPONSE', response: {status: 504}}],
    ])('says the server goes on when %s', async (_case, error) => {
        mocks.refreshAssetProfiles.mockRejectedValue(error);

        await expect(refreshProfiles([1], translate)).resolves.toEqual({kind: 'running'});
        const [event] = events();
        expect(event.name).toBe('asset.profiles.refreshRunning');
        expect(event.toast).toEqual({variant: 'info', message: 'assets.profile.bulk.stillRunning'});
    });

    it('reports an error when the call is refused', async () => {
        mocks.refreshAssetProfiles.mockRejectedValue({code: 'ERR_BAD_RESPONSE', response: {status: 500}});

        await expect(refreshProfiles([1], translate)).resolves.toEqual({kind: 'failed'});
        expect(events()[0]).toMatchObject({name: 'asset.profiles.refreshFailed', toast: {variant: 'error'}});
    });
});
