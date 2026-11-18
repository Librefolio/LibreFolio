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

vi.mock('$lib/api', () => ({zodiosApi: {read_assets_bulk_api_v1_assets_get: readAssetsBulk}}));
vi.mock('$lib/stores/reference/countryStore', () => ({ensureCountriesLoaded: vi.fn(async () => undefined)}));

import {effectRoot} from '$test/runes.svelte';
import {createMatrixMetadata} from './matrixMetadata.svelte';

const ROWS = [{asset_id: 7, asset_type: 'ETF', classification_params: {sector_area: {distribution: {Technology: '1'}}, geographic_area: null}}];

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

        answer([...ROWS, {asset_id: 8, asset_type: 'STOCK', classification_params: null}]);
        await vi.waitFor(() => expect(metadata.status).toBe('ready'));
        expect(metadata.types.get(8)).toBe('STOCK');
    });
});
