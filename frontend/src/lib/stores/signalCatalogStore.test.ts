import {describe, expect, it, vi} from 'vitest';

import {SignalCatalogStore, type SignalCatalogLoader} from './signalCatalogStore.svelte';
import type {BackendSignalCatalogDefinition, BackendSignalCatalogResponse} from '$lib/charts/signals';

function makeCatalogItem(index: number, domain: 'asset' | 'fx'): BackendSignalCatalogDefinition {
    return {
        signal_code: `SIGNAL_${index}`,
        implementation_version: '1.0.0',
        category: 'trend',
        display_name_key: `signals.${index}`,
        description_key: `signals.${index}.description`,
        icon: 'chart-spline',
        params_schema: {type: 'object', properties: {}},
        default_params: {},
        input_requirements: {
            price_fields: ['close'],
            data_policy: 'strict_contiguous',
            minimum_coverage: 1,
        },
        output_specs: [
            {
                key: 'value',
                label_key: 'signals.value',
                unit: 'price',
                axis: {key: 'price', role: 'price'},
                kind: 'line',
            },
        ],
        compatible_domains: [domain],
    };
}

function responseWithCount(count: number, domain: 'asset' | 'fx'): BackendSignalCatalogResponse {
    return {
        items: Array.from({length: count}, (_, index) => makeCatalogItem(index, domain)),
    };
}

describe('SignalCatalogStore', () => {
    it('loads the expected Asset 17 and FX 9 backend definitions once', async () => {
        const loader = vi.fn<SignalCatalogLoader>((domain) => Promise.resolve(responseWithCount(domain === 'asset' ? 17 : 9, domain)));
        const store = new SignalCatalogStore(loader);

        const [asset, fx] = await Promise.all([store.load('asset'), store.load('fx')]);

        expect(asset.filter((definition) => definition.source === 'backend')).toHaveLength(17);
        expect(fx.filter((definition) => definition.source === 'backend')).toHaveLength(9);
        expect(loader).toHaveBeenCalledTimes(2);
        await store.load('asset');
        expect(loader).toHaveBeenCalledTimes(2);
    });

    it('deduplicates concurrent loads for the same domain', async () => {
        let resolveResponse: (response: BackendSignalCatalogResponse) => void = () => undefined;
        const loader = vi.fn<SignalCatalogLoader>(
            () =>
                new Promise((resolve) => {
                    resolveResponse = resolve;
                }),
        );
        const store = new SignalCatalogStore(loader);

        const first = store.load('asset');
        const second = store.load('asset');
        resolveResponse(responseWithCount(17, 'asset'));

        await Promise.all([first, second]);
        expect(loader).toHaveBeenCalledTimes(1);
    });

    it('surfaces fetch errors and supports explicit retry', async () => {
        const loader = vi.fn<SignalCatalogLoader>().mockRejectedValueOnce(new Error('catalog offline')).mockResolvedValueOnce(responseWithCount(9, 'fx'));
        const store = new SignalCatalogStore(loader);

        await expect(store.load('fx')).rejects.toThrow('catalog offline');
        expect(store.error('fx')).toBe('catalog offline');

        const definitions = await store.load('fx', true);
        expect(definitions.filter((definition) => definition.source === 'backend')).toHaveLength(9);
        expect(store.error('fx')).toBeNull();
    });
});
