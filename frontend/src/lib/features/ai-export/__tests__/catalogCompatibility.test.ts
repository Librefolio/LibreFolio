import {describe, expect, it} from 'vitest';

import {findCompatibleAiExportSelection, reconcileAiExportCatalog, selectionsForDomain} from '../catalog/compatibility';
import {AI_EXPORT_CATALOG_VERSION, AI_EXPORT_SCHEMA_VERSION, AI_EXPORT_SELECTION_VERSION} from '../catalog/shared';
import {backendCatalogFixture} from './runtimeFixtures';

describe('AI Export catalog compatibility', () => {
    it('accepts the exact 8 Dataset / 11 Analysis V1 catalog', () => {
        const compatibility = reconcileAiExportCatalog(backendCatalogFixture());

        expect(compatibility.status).toBe('compatible');
        expect(compatibility.selections).toHaveLength(19);
        expect(selectionsForDomain(compatibility, 'portfolio', 'dataset')).toHaveLength(2);
        expect(selectionsForDomain(compatibility, 'broker', 'analysis')).toHaveLength(3);
        expect(selectionsForDomain(compatibility, 'asset')).toHaveLength(4);
        expect(selectionsForDomain(compatibility, 'fx')).toHaveLength(4);
        expect(findCompatibleAiExportSelection(compatibility, 'analysis', 'asset.market_analysis')).toBeDefined();
    });

    it('fails closed on catalog count or contract identity drift', () => {
        const missingDataset = backendCatalogFixture();
        missingDataset.datasets = missingDataset.datasets.slice(1);
        expect(reconcileAiExportCatalog(missingDataset).reasonCodes).toContain('dataset_catalog_mismatch');

        const contractDrift = backendCatalogFixture();
        contractDrift.analyses[0].response_contract_version = AI_EXPORT_SELECTION_VERSION + 1;
        const compatibility = reconcileAiExportCatalog(contractDrift);
        expect(compatibility.status).toBe('disabled');
        expect(compatibility.reasonCodes).toContain('response_contract_mismatch');
        expect(compatibility.byKey.has(`analysis:${contractDrift.analyses[0].id}`)).toBe(false);
    });

    it('fails closed on group, domain, i18n key, or icon drift', () => {
        const catalog = backendCatalogFixture();
        catalog.datasets[0].icon = 'database';

        const compatibility = reconcileAiExportCatalog(catalog);

        expect(compatibility.status).toBe('disabled');
        expect(compatibility.reasonCodes).toContain('selection_metadata_mismatch');
        expect(compatibility.byKey.has(`dataset:${catalog.datasets[0].id}`)).toBe(false);
    });

    it('fails closed on schema and catalog version drift', () => {
        const catalog = backendCatalogFixture();
        catalog.schema_version = AI_EXPORT_SCHEMA_VERSION + 1;
        catalog.catalog_version = AI_EXPORT_CATALOG_VERSION + 1;

        expect(reconcileAiExportCatalog(catalog).reasonCodes).toEqual(expect.arrayContaining(['schema_version_mismatch', 'catalog_version_mismatch']));
    });
});
