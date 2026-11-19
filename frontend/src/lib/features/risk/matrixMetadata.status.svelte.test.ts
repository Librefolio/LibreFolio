// @vitest-environment jsdom
/**
 * createMatrixMetadata — the state of its read (RN-20, Q12).
 *
 * The matrix offers its five orderings always; an ordering it cannot use says why, and the why must be true. «No sector
 * known for these assets» is true only once the read answered; while it is in flight the reason is that the assets'
 * details are still being read, and after a failed read that they could not be read. The three used to look the same
 * — three empty maps — and the orderings simply vanished: the page with two orderings the developer saw. So the factory
 * publishes its `status` beside the maps.
 *
 * The API and the country store are stood in for: this file is about the factory's state, not the read's parsing (that
 * is `matrixMetadata.test.ts`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';

const readAssetsBulk = vi.hoisted(() => vi.fn());
const queryProfile = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', () => ({zodiosApi: {read_assets_bulk_api_v1_assets_get: readAssetsBulk, query_profile_api_v1_assets_profile_query_post: queryProfile}}));
vi.mock('$lib/stores/reference/countryStore', () => ({ensureCountriesLoaded: vi.fn(async () => undefined)}));

import {effectRoot} from '$test/runes.svelte';
import {createMatrixMetadata} from './matrixMetadata.svelte';
import {todayIso} from '$lib/utils/dateOnly';

const ROWS = [{asset_id: 7, asset_type: 'ETF'}];
const PROFILE = {as_of: '2026-11-17T10:00:00Z', items: [{asset_id: 7, voices: {sector: [{date: '2026-11-17', through: '2026-11-17', value: {Technology: '1'}, source: 'justetf', update_id: 1, opened_on: '2026-11-01'}]}}]};

const stops: (() => void)[] = [];

function mount(assetIds: number[]) {
    const inputs = $state({assetIds});
    const {value, stop} = effectRoot(() => createMatrixMetadata(() => ({assetIds: inputs.assetIds, language: 'en'})));
    stops.push(stop);
    flushSync();
    return {metadata: value, inputs};
}

beforeEach(() => {
    readAssetsBulk.mockReset();
    queryProfile.mockReset().mockResolvedValue(PROFILE);
});

afterEach(() => {
    while (stops.length > 0) stops.pop()?.();
});

describe('createMatrixMetadata — the state of the read', () => {
    it('is ready, with three empty maps, when there are no assets to read', () => {
        const {metadata} = mount([]);

        expect(metadata.status).toBe('ready');
        expect(readAssetsBulk).not.toHaveBeenCalled();
    });

    it('is loading while the read is in flight, then ready with the maps the read answered', async () => {
        let answer: (rows: typeof ROWS) => void = () => undefined;
        readAssetsBulk.mockImplementation(() => new Promise((resolve) => (answer = resolve)));
        const {metadata} = mount([7]);

        await vi.waitFor(() => expect(readAssetsBulk).toHaveBeenCalledTimes(1));
        expect(metadata.status).toBe('loading');
        expect(metadata.types.size).toBe(0);

        answer(ROWS);
        await vi.waitFor(() => expect(metadata.status).toBe('ready'));
        expect(metadata.types.get(7)).toBe('ETF');
        expect(metadata.sectors.get(7)).toEqual({Technology: 1});
    });

    it('reads the sectors and countries from the profile, today, the two maps only, one item per asset (plan 68, E5)', async () => {
        readAssetsBulk.mockResolvedValue([...ROWS, {asset_id: 9, asset_type: 'STOCK'}]);
        const {metadata} = mount([9, 7]);
        await vi.waitFor(() => expect(metadata.status).toBe('ready'));
        expect(queryProfile).toHaveBeenCalledTimes(1);
        const items = queryProfile.mock.calls[0][0] as Array<{asset_id: number; date_range: {start: string; end?: string}; keys: string[]}>;
        expect(items.map((item) => item.asset_id)).toEqual([7, 9]);
        expect(items.every((item) => item.date_range.start === todayIso() && item.date_range.end === undefined)).toBe(true);
        expect(items.every((item) => JSON.stringify(item.keys) === JSON.stringify(['geography', 'sector']))).toBe(true);
    });

    it('is failed when the profile read fails', async () => {
        readAssetsBulk.mockResolvedValue(ROWS);
        queryProfile.mockRejectedValue(new Error('invented: the profile read failed'));
        const {metadata} = mount([7]);
        await vi.waitFor(() => expect(metadata.status).toBe('failed'));
    });

    it('is failed, with three empty maps, when the read fails', async () => {
        readAssetsBulk.mockRejectedValue(new Error('invented: the read failed'));
        const {metadata} = mount([7]);

        await vi.waitFor(() => expect(metadata.status).toBe('failed'));
        expect([metadata.types.size, metadata.sectors.size, metadata.regions.size]).toEqual([0, 0, 0]);
    });

    it('is loading again when the assets change, and ready once the new read answers', async () => {
        readAssetsBulk.mockResolvedValueOnce(ROWS);
        const {metadata, inputs} = mount([7]);
        await vi.waitFor(() => expect(metadata.status).toBe('ready'));

        let answer: (rows: unknown[]) => void = () => undefined;
        readAssetsBulk.mockImplementationOnce(() => new Promise((resolve) => (answer = resolve)));
        inputs.assetIds = [7, 8];
        flushSync();
        await vi.waitFor(() => expect(readAssetsBulk).toHaveBeenCalledTimes(2));
        expect(metadata.status).toBe('loading');

        answer([...ROWS, {asset_id: 8, asset_type: 'STOCK'}]);
        await vi.waitFor(() => expect(metadata.status).toBe('ready'));
        expect(metadata.types.get(8)).toBe('STOCK');
    });
});
