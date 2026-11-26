/**
 * profileStore (plan 68, E1): the small memory of the asset profile the «Profilo» tab, its cards, the changes panel and
 * the profile windows share.
 *
 * Pinned:
 * - the catalogue is asked once per session; a failed load is not kept (the next call asks again); `profileVoice`
 *   answers a voice of the loaded catalogue, `undefined` before it or for an unknown key;
 * - a read of one asset is remembered per request (asset, range, voices, changes): the same request asks the server
 *   once, a different one asks again; `invalidateAssetProfile(id)` forgets that asset's reads only;
 *   `clearProfileMemory()` forgets everything; a failed read is not kept;
 * - a read answers the asset's item and the server's `as_of`; an item with `error` («Asset not found») is a typed
 *   `missing` result, distinct from an asset without rows (`voices: {}`);
 * - «Dimentica» sends `[{asset_id, update_ids, as_of}]` and forgets that asset's reads on success; a refusal 409
 *   `PROFILE_UPDATES_NEWER` or 404 `PROFILE_UPDATES_NOT_FOUND` is a typed result (with the ids), never a throw, and
 *   forgets the asset's reads too (the page reloads); any other error is thrown as it came;
 * - «Aggiorna» (E6c) sends `[asset_id]`, answers that asset's result and forgets its reads, whatever the server says;
 *   «Riallinea i profili» (87 A5) sends every id in one call, answers one result per id asked and forgets all their reads.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({
    api: {
        profile_catalogue_api_v1_assets_profile_catalogue_get: vi.fn(),
        query_profile_api_v1_assets_profile_query_post: vi.fn(),
        forget_profile_api_v1_assets_profile_delete: vi.fn(),
        refresh_profile_api_v1_assets_profile_refresh_post: vi.fn(),
    },
}));
vi.mock('$lib/api', () => ({zodiosApi: mocks.api}));

import {clearProfileMemory, forgetProfileRows, invalidateAssetProfile, loadProfileCatalogue, profileVoice, readAssetProfile, refreshAssetProfile, refreshAssetProfiles} from './profileStore';

const catalogueCall = mocks.api.profile_catalogue_api_v1_assets_profile_catalogue_get;
const queryCall = mocks.api.query_profile_api_v1_assets_profile_query_post;
const forgetCall = mocks.api.forget_profile_api_v1_assets_profile_delete;
const refreshCall = mocks.api.refresh_profile_api_v1_assets_profile_refresh_post;

const TER = {key: 'ter', shape: 'percentage', sign: 'non_negative', unit: null, groups: ['key_figures'], key_figure: true, charted: true, volatile: false, choices: [], map_keys: null};
const GEO = {key: 'geography', shape: 'map', sign: null, unit: null, groups: ['classification'], key_figure: false, charted: false, volatile: false, choices: [], map_keys: 'country'};
const AS_OF = '2026-11-17T08:00:00Z';
const RANGE = {start: '2026-01-01', end: '2026-11-17'};

function answer(assetId: number, voices: Record<string, unknown[]> = {}, extra: Record<string, unknown> = {}) {
    return {as_of: AS_OF, items: [{asset_id: assetId, voices, changes: null, error: null, ...extra}]};
}

function axiosRefusal(status: number, detail: unknown) {
    return Object.assign(new Error(`Request failed with status code ${status}`), {response: {status, data: {detail}}});
}

beforeEach(() => {
    clearProfileMemory();
    vi.clearAllMocks();
});

afterEach(() => clearProfileMemory());

describe('the catalogue', () => {
    it('is asked once and answers its voices by key', async () => {
        catalogueCall.mockResolvedValue({voices: [TER, GEO]});
        expect(profileVoice('ter'), 'nothing before the first load').toBeUndefined();

        const [first, second] = await Promise.all([loadProfileCatalogue(), loadProfileCatalogue()]);

        expect(first.map((voice) => voice.key)).toEqual(['ter', 'geography']);
        expect(second).toBe(first);
        expect(catalogueCall).toHaveBeenCalledTimes(1);
        expect(profileVoice('geography')?.shape).toBe('map');
        expect(profileVoice('nope')).toBeUndefined();
    });

    it('does not keep a failed load', async () => {
        catalogueCall.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({voices: [TER]});

        await expect(loadProfileCatalogue()).rejects.toThrow('offline');
        await expect(loadProfileCatalogue()).resolves.toHaveLength(1);
        expect(catalogueCall).toHaveBeenCalledTimes(2);
    });
});

describe('reading an asset', () => {
    it('asks the server once per request and answers the item with as_of', async () => {
        const steps = [{date: '2026-01-01', through: '2026-11-17', value: '0.0022', source: 'justetf', update_id: 5}];
        queryCall.mockResolvedValue(answer(7, {ter: steps}));

        const first = await readAssetProfile(7, RANGE, {keys: ['ter']});
        const again = await readAssetProfile(7, RANGE, {keys: ['ter']});

        expect(queryCall).toHaveBeenCalledTimes(1);
        expect(queryCall).toHaveBeenCalledWith([{asset_id: 7, date_range: RANGE, keys: ['ter']}]);
        expect(first).toEqual({kind: 'found', asOf: AS_OF, voices: {ter: steps}, changes: null});
        expect(again).toBe(first);
    });

    it('asks again for a different request: range, voices, changes', async () => {
        queryCall.mockResolvedValue(answer(7));

        await readAssetProfile(7, RANGE);
        await readAssetProfile(7, {start: 'min', end: '2026-11-17'});
        await readAssetProfile(7, RANGE, {keys: ['ter']});
        await readAssetProfile(7, RANGE, {changes: {key: null, page: 0}});
        await readAssetProfile(7, RANGE, {changes: {key: null, page: 1}});

        expect(queryCall).toHaveBeenCalledTimes(5);
        expect(queryCall).toHaveBeenNthCalledWith(4, [{asset_id: 7, date_range: RANGE, changes: {key: null, page: 0}}]);
    });

    it('tells a missing asset from an asset without rows', async () => {
        queryCall.mockResolvedValueOnce(answer(7, {}, {error: 'Asset not found'})).mockResolvedValueOnce(answer(8));

        await expect(readAssetProfile(7, RANGE)).resolves.toEqual({kind: 'missing', asOf: AS_OF});
        await expect(readAssetProfile(8, RANGE)).resolves.toEqual({kind: 'found', asOf: AS_OF, voices: {}, changes: null});
    });

    it('forgets one asset, or everything, and never keeps a failed read', async () => {
        queryCall.mockResolvedValue(answer(7));
        await readAssetProfile(7, RANGE);
        await readAssetProfile(8, RANGE);

        invalidateAssetProfile(7);
        await readAssetProfile(7, RANGE);
        await readAssetProfile(8, RANGE);
        expect(queryCall).toHaveBeenCalledTimes(3);

        clearProfileMemory();
        await readAssetProfile(8, RANGE);
        expect(queryCall).toHaveBeenCalledTimes(4);

        queryCall.mockRejectedValueOnce(new Error('boom'));
        clearProfileMemory();
        await expect(readAssetProfile(9, RANGE)).rejects.toThrow('boom');
        await readAssetProfile(9, RANGE);
        expect(queryCall).toHaveBeenCalledTimes(6);
    });
});

describe('«Dimentica»', () => {
    it('sends the rows with as_of and forgets the asset’s reads on success', async () => {
        queryCall.mockResolvedValue(answer(7));
        forgetCall.mockResolvedValue({results: [{asset_id: 7, success: true, deleted_count: 2}], success_count: 1, total_deleted: 2, errors: []});
        await readAssetProfile(7, RANGE);

        const outcome = await forgetProfileRows(7, [11, 12], AS_OF);

        expect(forgetCall).toHaveBeenCalledWith([{asset_id: 7, update_ids: [11, 12], as_of: AS_OF}]);
        expect(outcome).toEqual({kind: 'forgotten', deleted: 2});
        await readAssetProfile(7, RANGE);
        expect(queryCall, 'the read after a forget asks the server again').toHaveBeenCalledTimes(2);
    });

    it.each([
        [409, 'PROFILE_UPDATES_NEWER', 'newer'],
        [404, 'PROFILE_UPDATES_NOT_FOUND', 'not_found'],
    ])('a %i %s refusal is a typed result with the ids, and the reads are forgotten', async (status, code, kind) => {
        queryCall.mockResolvedValue(answer(7));
        forgetCall.mockRejectedValue(axiosRefusal(status, {error_code: code, message: 'refused', asset_id: 7, update_ids: [12]}));
        await readAssetProfile(7, RANGE);

        await expect(forgetProfileRows(7, [11, 12], AS_OF)).resolves.toEqual({kind, updateIds: [12]});
        await readAssetProfile(7, RANGE);
        expect(queryCall).toHaveBeenCalledTimes(2);
    });

    it('throws any other error as it came', async () => {
        const failure = axiosRefusal(500, {request_id: 'r1'});
        forgetCall.mockRejectedValue(failure);

        await expect(forgetProfileRows(7, [11], AS_OF)).rejects.toBe(failure);
    });
});

describe('«Aggiorna» (E6c)', () => {
    it('sends the asset, answers its result and forgets its reads', async () => {
        queryCall.mockResolvedValue(answer(7));
        const result = {asset_id: 7, written: ['ter'], outcomes: [{code: 'mockenrich', identifier_type: 'ISIN', identifier: 'X', status: 'ok', voices: ['ter'], error_code: null, retry_after: null, from_cache: false}], error: null};
        refreshCall.mockResolvedValue({results: [result]});
        await readAssetProfile(7, RANGE);

        await expect(refreshAssetProfile(7)).resolves.toEqual(result);
        expect(refreshCall).toHaveBeenCalledWith([7]);
        await readAssetProfile(7, RANGE);
        expect(queryCall, 'the read after «Aggiorna» asks the server again').toHaveBeenCalledTimes(2);
    });

    it('forgets the reads when the call fails too, and throws', async () => {
        queryCall.mockResolvedValue(answer(7));
        const failure = axiosRefusal(500, {request_id: 'r1'});
        refreshCall.mockRejectedValue(failure);
        await readAssetProfile(7, RANGE);

        await expect(refreshAssetProfile(7)).rejects.toBe(failure);
        await readAssetProfile(7, RANGE);
        expect(queryCall).toHaveBeenCalledTimes(2);
    });
});

describe('«Riallinea i profili» (87 A5)', () => {
    it('asks every asset in one call and answers one result per asset, in the order asked', async () => {
        queryCall.mockImplementation(async (items: Array<{asset_id: number}>) => answer(items[0].asset_id));
        refreshCall.mockResolvedValue({results: [{asset_id: 8, written: ['ter'], outcomes: [], error: null, enrichers_read: 1}]});
        await readAssetProfile(7, RANGE);
        await readAssetProfile(8, RANGE);

        const results = await refreshAssetProfiles([7, 8]);
        expect(refreshCall).toHaveBeenCalledTimes(1);
        expect(refreshCall.mock.calls[0][0]).toEqual([7, 8]);
        expect(results.map((result) => [result.asset_id, result.error])).toEqual([
            [7, 'missing'],
            [8, null],
        ]);
        await readAssetProfile(7, RANGE);
        await readAssetProfile(8, RANGE);
        expect(queryCall, 'both assets are read again').toHaveBeenCalledTimes(4);
    });

    it('forgets the reads when the wait ends first too: the server goes on writing', async () => {
        queryCall.mockResolvedValue(answer(7));
        refreshCall.mockRejectedValue(Object.assign(new Error('timeout'), {code: 'ECONNABORTED'}));
        await readAssetProfile(7, RANGE);

        await expect(refreshAssetProfiles([7])).rejects.toMatchObject({code: 'ECONNABORTED'});
        await readAssetProfile(7, RANGE);
        expect(queryCall).toHaveBeenCalledTimes(2);
    });
});
