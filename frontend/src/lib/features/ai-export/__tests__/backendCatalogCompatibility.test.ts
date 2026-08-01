import {describe, expect, it, vi} from 'vitest';

import {AiExportCatalogHttpError, AiExportCatalogLoader, fetchBackendAiExportCatalog} from '../catalog/compatibility';
import {backendCatalogFixture} from './runtimeFixtures';

describe('AI Export backend catalog loading', () => {
    it('parses and caches the typed catalog', async () => {
        const fetchCatalog = vi.fn(async () => backendCatalogFixture());
        const loader = new AiExportCatalogLoader(fetchCatalog);

        const first = await loader.load();
        const second = await loader.load();

        expect(first.status).toBe('compatible');
        expect(second).toBe(first);
        expect(fetchCatalog).toHaveBeenCalledTimes(1);
        loader.reset();
        await loader.load();
        expect(fetchCatalog).toHaveBeenCalledTimes(2);
    });

    it('maps non-success HTTP responses', async () => {
        const fetcher = vi.fn(async () => new Response('', {status: 503, statusText: 'Unavailable'}));

        await expect(fetchBackendAiExportCatalog(fetcher)).rejects.toBeInstanceOf(AiExportCatalogHttpError);
    });

    it('rejects untyped catalog payloads', async () => {
        const fetcher = vi.fn(async () => new Response(JSON.stringify({schema_version: 1}), {status: 200, headers: {'content-type': 'application/json'}}));

        await expect(fetchBackendAiExportCatalog(fetcher)).rejects.toThrow();
    });
});
