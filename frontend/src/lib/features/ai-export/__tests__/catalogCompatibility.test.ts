import {describe, expect, it} from 'vitest';

import {findCompatibleAiExportSelection, reconcileAiExportCatalog, selectionsForDomain} from '../catalog/compatibility';
import {backendCatalogFixture} from './runtimeFixtures';

describe('AI Export catalog compatibility', () => {
    it('accepts the exact 32 dataset / 16 analysis V2 catalog', () => {
        const compatibility = reconcileAiExportCatalog(backendCatalogFixture());

        expect(compatibility.status).toBe('compatible');
        expect(compatibility.selections).toHaveLength(48);
        expect(selectionsForDomain(compatibility, 'portfolio', 'dataset')).toHaveLength(10);
        expect(selectionsForDomain(compatibility, 'broker', 'analysis')).toHaveLength(4);
        expect(selectionsForDomain(compatibility, 'asset')).toHaveLength(8);
        expect(selectionsForDomain(compatibility, 'fx')).toHaveLength(9);
        expect(findCompatibleAiExportSelection(compatibility, 'analysis', 'asset.trend_analysis')).toBeDefined();
    });

    it('fails closed on catalog count or contract identity drift', () => {
        const missingDataset = backendCatalogFixture();
        missingDataset.datasets = missingDataset.datasets.slice(1);
        expect(reconcileAiExportCatalog(missingDataset).reasonCodes).toContain('dataset_catalog_mismatch');

        const contractDrift = backendCatalogFixture();
        contractDrift.analyses[0].response_contract_version = 1;
        const compatibility = reconcileAiExportCatalog(contractDrift);
        expect(compatibility.status).toBe('disabled');
        expect(compatibility.reasonCodes).toContain('response_contract_mismatch');
        expect(compatibility.byKey.has(`analysis:${contractDrift.analyses[0].id}`)).toBe(false);
    });

    it('fails closed on schema and catalog version drift', () => {
        const catalog = backendCatalogFixture();
        catalog.schema_version = 1;
        catalog.catalog_version = 1;

        expect(reconcileAiExportCatalog(catalog).reasonCodes).toEqual(expect.arrayContaining(['schema_version_mismatch', 'catalog_version_mismatch']));
    });
});
