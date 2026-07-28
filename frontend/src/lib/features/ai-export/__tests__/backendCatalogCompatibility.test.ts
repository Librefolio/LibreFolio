import {describe, expect, it, vi} from 'vitest';

import compatibilityFixture from '../../../../../../backend/test_scripts/fixtures/ai_export/legacy_semantics/prompt_compatibility.v1.json';
import {schemas} from '$lib/api';
import {ASSET_AI_EXPORT_TASKS} from '../catalog/assetTasks';
import {BROKER_AI_EXPORT_TASKS} from '../catalog/brokerTasks';
import {
    AI_EXPORT_LOCAL_CHOICES,
    AI_EXPORT_TASK_CATALOG,
    AiExportCatalogHttpError,
    AiExportCatalogLoader,
    AiExportCatalogPresentationDriftError,
    fetchBackendAiExportCatalog,
    findBackendCatalogPresentationFields,
    reconcileAiExportCatalog,
    type AiExportCatalogCompatibilityResult,
    type AiExportCatalogFetcher,
} from '../catalog/compatibility';
import {FX_AI_EXPORT_TASKS} from '../catalog/fxTasks';
import {PORTFOLIO_AI_EXPORT_TASKS} from '../catalog/portfolioTasks';
import {
    AI_EXPORT_CATALOG_SCHEMA_VERSION,
    AI_EXPORT_DETAIL_LEVELS,
    AI_EXPORT_FRONTEND_RESPONSE_CONTRACT_VERSION,
    AI_EXPORT_PROFILE_VERSION,
    AI_EXPORT_RENDER_MODES,
    type AiExportBackendCatalogEntry,
    type AiExportBackendCatalogResponse,
    type AiExportDetailLevel,
    type AiExportDomain,
    type AiExportTask,
    type AiExportTaskDefinition,
} from '../catalog/shared';

function buildMatchingBackendCatalog(): AiExportBackendCatalogResponse {
    return {
        schema_version: AI_EXPORT_CATALOG_SCHEMA_VERSION,
        entries: AI_EXPORT_LOCAL_CHOICES.map((choice) => ({
            domain: choice.domain,
            task: choice.backendTask,
            detail_level: choice.detailLevel,
            profile_id: choice.profileId,
            profile_version: choice.profileVersion,
            frontend_response_contract_id: choice.frontendResponseContractId,
            frontend_response_contract_version: choice.frontendResponseContractVersion,
            applicability_code: 'test_applicable',
            supports_user_notes: choice.supportsUserNotes,
            supports_web_research: choice.supportsWebResearch,
        })),
    };
}

function updateBackendEntry(catalog: AiExportBackendCatalogResponse, domain: AiExportDomain, task: AiExportTask, detailLevel: AiExportDetailLevel, update: (entry: AiExportBackendCatalogEntry) => AiExportBackendCatalogEntry): AiExportBackendCatalogResponse {
    return {
        ...catalog,
        entries: (catalog.entries ?? []).map((entry) => (entry.domain === domain && entry.task === task && entry.detail_level === detailLevel ? update(entry) : entry)),
    };
}

function findChoice(result: AiExportCatalogCompatibilityResult, domain: AiExportDomain, task: AiExportTask, detailLevel: AiExportDetailLevel) {
    const choice = result.choices.find((candidate) => candidate.domain === domain && candidate.backendTask === task && candidate.detailLevel === detailLevel);
    if (!choice) throw new Error(`Missing local choice ${domain}.${task}.${detailLevel}`);
    return choice;
}

describe('backend AI Export catalog compatibility', () => {
    it('freezes 7/5/3/4 tasks and 57 exact detail choices in approved order', () => {
        expect(PORTFOLIO_AI_EXPORT_TASKS).toHaveLength(7);
        expect(ASSET_AI_EXPORT_TASKS).toHaveLength(5);
        expect(FX_AI_EXPORT_TASKS).toHaveLength(3);
        expect(BROKER_AI_EXPORT_TASKS).toHaveLength(4);
        expect(AI_EXPORT_TASK_CATALOG).toHaveLength(19);
        expect(AI_EXPORT_LOCAL_CHOICES).toHaveLength(57);
        expect(AI_EXPORT_TASK_CATALOG.map((task) => `${task.domain}.${task.backendTask}`)).toEqual([
            'portfolio.pac_planning',
            'portfolio.rebalancing',
            'portfolio.performance_attribution',
            'portfolio.income_review',
            'portfolio.portfolio_fifo_lot_review',
            'portfolio.technical_breadth',
            'portfolio.portfolio_description',
            'asset.asset_snapshot',
            'asset.asset_trend_analysis',
            'asset.position_review',
            'asset.asset_pac_timing_context',
            'asset.drawdown_recovery',
            'fx.fx_trend_review',
            'fx.fx_exposure_impact',
            'fx.fx_conversion_timing_context',
            'broker.broker_review',
            'broker.broker_cost_efficiency',
            'broker.broker_concentration_context',
            'broker.broker_fifo_lot_review',
        ]);

        for (const task of AI_EXPORT_TASK_CATALOG) {
            const taskPath = `${task.domain}.${task.backendTask}`;
            expect(task.id).toBe(task.backendTask);
            expect(task.labelKey).toBe(`aiExport.catalog.${taskPath}.label`);
            expect(task.descriptionKey).toBe(`aiExport.catalog.${taskPath}.description`);
            expect(task.supportedDetailLevels).toEqual(AI_EXPORT_DETAIL_LEVELS);
            expect(task.defaultDetailLevel).toBe('standard');
            expect(task.renderModes).toEqual(AI_EXPORT_RENDER_MODES);
            expect(task.frontendResponseContract).toEqual({
                id: taskPath,
                version: AI_EXPORT_FRONTEND_RESPONSE_CONTRACT_VERSION,
            });
            expect(task.instructionTemplateId).toBe(`aiExport.instructions.${taskPath}.v1`);
            expect(task.responseContractTemplateId).toBe(`aiExport.responseContracts.${taskPath}.v1`);

            for (const detailLevel of AI_EXPORT_DETAIL_LEVELS) {
                expect(task.expectedProfiles[detailLevel]).toEqual({
                    profileId: `${taskPath}.${detailLevel}`,
                    profileVersion: AI_EXPORT_PROFILE_VERSION,
                });
            }
        }
    });

    it('reconciles an exact backend fixture to 57 compatible selectable choices', () => {
        const result = reconcileAiExportCatalog(buildMatchingBackendCatalog());

        expect(result.status).toBe('compatible');
        expect(result.choices).toHaveLength(57);
        expect(result.selectableChoices).toHaveLength(57);
        expect(result.backendOnlyEntries).toEqual([]);
        expect(result.reasonCodes).toEqual([]);
        expect(result.choices.every((choice) => choice.status === 'compatible' && choice.reasonCode === null)).toBe(true);
    });

    it('fails closed when a backend profile is missing', () => {
        const catalog = buildMatchingBackendCatalog();
        const result = reconcileAiExportCatalog({
            ...catalog,
            entries: (catalog.entries ?? []).slice(1),
        });

        expect(result.status).toBe('disabled');
        expect(result.selectableChoices).toHaveLength(56);
        expect(findChoice(result, 'portfolio', 'pac_planning', 'compact')).toMatchObject({
            status: 'disabled',
            reasonCode: 'backend_entry_missing',
        });
    });

    it('keeps backend-only profiles non-selectable and reports missing local definition', () => {
        const catalog = buildMatchingBackendCatalog();
        const backendOnlyEntry: AiExportBackendCatalogEntry = {
            domain: 'asset',
            task: 'pac_planning',
            detail_level: 'compact',
            profile_id: 'asset.pac_planning.compact',
            profile_version: 1,
            frontend_response_contract_id: 'asset.pac_planning',
            frontend_response_contract_version: 1,
            applicability_code: 'test_applicable',
            supports_user_notes: true,
            supports_web_research: true,
        };
        const result = reconcileAiExportCatalog({
            ...catalog,
            entries: [...(catalog.entries ?? []), backendOnlyEntry],
        });

        expect(result.status).toBe('disabled');
        expect(result.selectableChoices).toHaveLength(57);
        expect(result.backendOnlyEntries).toEqual([
            {
                key: 'asset:pac_planning:compact',
                status: 'disabled',
                reasonCode: 'local_definition_missing',
                entry: backendOnlyEntry,
            },
        ]);
        expect(result.selectableChoices.some((choice) => choice.key === 'asset:pac_planning:compact')).toBe(false);
    });

    it('fails closed on profile identity or version mismatch', () => {
        const catalog = buildMatchingBackendCatalog();
        const idMismatch = reconcileAiExportCatalog(
            updateBackendEntry(catalog, 'portfolio', 'pac_planning', 'compact', (entry) => ({
                ...entry,
                profile_id: 'portfolio.pac_planning.compact.v2',
            })),
        );
        const versionMismatch = reconcileAiExportCatalog(
            updateBackendEntry(catalog, 'portfolio', 'pac_planning', 'compact', (entry) => ({
                ...entry,
                profile_version: entry.profile_version + 1,
            })),
        );

        expect(findChoice(idMismatch, 'portfolio', 'pac_planning', 'compact').reasonCode).toBe('profile_id_mismatch');
        expect(findChoice(versionMismatch, 'portfolio', 'pac_planning', 'compact').reasonCode).toBe('profile_version_mismatch');
        expect(idMismatch.selectableChoices).toHaveLength(56);
        expect(versionMismatch.selectableChoices).toHaveLength(56);
    });

    it('fails closed on frontend response contract ID or version mismatch', () => {
        const catalog = buildMatchingBackendCatalog();
        const idMismatch = reconcileAiExportCatalog(
            updateBackendEntry(catalog, 'portfolio', 'rebalancing', 'standard', (entry) => ({
                ...entry,
                frontend_response_contract_id: 'portfolio.rebalancing.v2',
            })),
        );
        const versionMismatch = reconcileAiExportCatalog(
            updateBackendEntry(catalog, 'portfolio', 'rebalancing', 'standard', (entry) => ({
                ...entry,
                frontend_response_contract_version: entry.frontend_response_contract_version + 1,
            })),
        );

        expect(findChoice(idMismatch, 'portfolio', 'rebalancing', 'standard').reasonCode).toBe('response_contract_id_mismatch');
        expect(findChoice(versionMismatch, 'portfolio', 'rebalancing', 'standard').reasonCode).toBe('response_contract_version_mismatch');
    });

    it('fails closed on user-note or web-research flag mismatch', () => {
        const catalog = buildMatchingBackendCatalog();
        const userNotesMismatch = reconcileAiExportCatalog(
            updateBackendEntry(catalog, 'portfolio', 'technical_breadth', 'full', (entry) => ({
                ...entry,
                supports_user_notes: !entry.supports_user_notes,
            })),
        );
        const webResearchMismatch = reconcileAiExportCatalog(
            updateBackendEntry(catalog, 'asset', 'position_review', 'full', (entry) => ({
                ...entry,
                supports_web_research: !entry.supports_web_research,
            })),
        );

        expect(findChoice(userNotesMismatch, 'portfolio', 'technical_breadth', 'full').reasonCode).toBe('supports_user_notes_mismatch');
        expect(findChoice(webResearchMismatch, 'asset', 'position_review', 'full').reasonCode).toBe('supports_web_research_mismatch');
    });

    it('fails the whole local catalog closed on backend schema mismatch', () => {
        const catalog = buildMatchingBackendCatalog();
        const result = reconcileAiExportCatalog({
            ...catalog,
            schema_version: catalog.schema_version + 1,
        });

        expect(result.status).toBe('disabled');
        expect(result.selectableChoices).toHaveLength(0);
        expect(result.reasonCodes).toEqual(['backend_catalog_schema_version_mismatch']);
        expect(result.choices.every((choice) => choice.reasonCode === 'backend_catalog_schema_version_mismatch')).toBe(true);
    });

    it('rejects duplicate backend tuples instead of selecting one', () => {
        const catalog = buildMatchingBackendCatalog();
        const duplicate = (catalog.entries ?? [])[0];
        if (!duplicate) throw new Error('Matching catalog fixture must contain entries');
        const result = reconcileAiExportCatalog({
            ...catalog,
            entries: [...(catalog.entries ?? []), duplicate],
        });

        expect(findChoice(result, duplicate.domain, duplicate.task, duplicate.detail_level).reasonCode).toBe('duplicate_backend_entry');
        expect(result.selectableChoices).toHaveLength(56);
    });

    it('preserves deterministic local order regardless of backend order', () => {
        const catalog = buildMatchingBackendCatalog();
        const forward = reconcileAiExportCatalog(catalog);
        const reversed = reconcileAiExportCatalog({
            ...catalog,
            entries: [...(catalog.entries ?? [])].reverse(),
        });
        const expectedOrder = AI_EXPORT_LOCAL_CHOICES.map((choice) => choice.key);

        expect(forward.choices.map((choice) => choice.key)).toEqual(expectedOrder);
        expect(reversed.choices.map((choice) => choice.key)).toEqual(expectedOrder);
        expect(reversed.selectableChoices.map((choice) => choice.key)).toEqual(expectedOrder);
    });

    it('deduplicates concurrent catalog GETs, caches success, and resets cleanly', async () => {
        const catalog = buildMatchingBackendCatalog();
        let fetchCount = 0;
        let resolvePending: (value: AiExportBackendCatalogResponse) => void = () => {
            throw new Error('Pending resolver was not initialized');
        };
        const pending = new Promise<AiExportBackendCatalogResponse>((resolve) => {
            resolvePending = resolve;
        });
        const fetchCatalog: AiExportCatalogFetcher = () => {
            fetchCount += 1;
            return fetchCount === 1 ? pending : Promise.resolve(catalog);
        };
        const loader = new AiExportCatalogLoader(fetchCatalog);

        const first = loader.load();
        const second = loader.load();
        expect(first).toBe(second);
        expect(fetchCount).toBe(1);

        resolvePending(catalog);
        const loaded = await first;
        expect(loaded.status).toBe('compatible');
        expect(loader.peek()).toBe(loaded);
        expect(await loader.load()).toBe(loaded);
        expect(fetchCount).toBe(1);

        loader.reset();
        expect(loader.peek()).toBeUndefined();
        const reloaded = await loader.load();
        expect(reloaded.status).toBe('compatible');
        expect(fetchCount).toBe(2);
        expect(reloaded).not.toBe(loaded);
    });

    it('rejects raw backend presentation fields before generated-schema parsing', async () => {
        const catalog = buildMatchingBackendCatalog();
        const rawCatalog = {
            ...catalog,
            entries: (catalog.entries ?? []).map((entry, index) => (index === 0 ? {...entry, prompt_text: 'Backend-owned prompt'} : entry)),
        };
        const json = vi.fn().mockResolvedValue(rawCatalog);
        const fetcher = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            statusText: 'OK',
            json,
        }) as unknown as typeof fetch;
        const loader = new AiExportCatalogLoader(() => fetchBackendAiExportCatalog(fetcher));

        let thrown: unknown;
        try {
            await loader.load();
        } catch (error) {
            thrown = error;
        }

        expect(thrown).toBeInstanceOf(AiExportCatalogPresentationDriftError);
        expect(thrown).toMatchObject({
            kind: 'presentation_drift',
            fields: ['prompt_text'],
        });
        expect(fetcher).toHaveBeenCalledOnce();
        expect(fetcher).toHaveBeenCalledWith('/api/v1/ai-export/catalog', {
            credentials: 'same-origin',
            headers: {Accept: 'application/json'},
        });
        expect(json).toHaveBeenCalledOnce();
        expect(loader.peek()).toBeUndefined();
    });

    it('rejects catalog HTTP errors before reading a response body', async () => {
        const json = vi.fn();
        const fetcher = vi.fn().mockResolvedValue({
            ok: false,
            status: 503,
            statusText: 'Service Unavailable',
            json,
        }) as unknown as typeof fetch;
        const loader = new AiExportCatalogLoader(() => fetchBackendAiExportCatalog(fetcher));

        let thrown: unknown;
        try {
            await loader.load();
        } catch (error) {
            thrown = error;
        }

        expect(thrown).toBeInstanceOf(AiExportCatalogHttpError);
        expect(thrown).toMatchObject({
            kind: 'http',
            status: 503,
            statusText: 'Service Unavailable',
        });
        expect(fetcher).toHaveBeenCalledOnce();
        expect(json).not.toHaveBeenCalled();
        expect(loader.peek()).toBeUndefined();
    });

    it('exposes a metadata-only backend catalog with no prompt, label, or instruction text', () => {
        const catalog = schemas.AiExportCatalogResponse.parse(buildMatchingBackendCatalog());
        const firstEntry = (catalog.entries ?? [])[0];
        if (!firstEntry) throw new Error('Matching catalog fixture must contain entries');

        expect(findBackendCatalogPresentationFields(catalog)).toEqual([]);
        expect(Object.keys(firstEntry).sort()).toEqual(['domain', 'task', 'detail_level', 'profile_id', 'profile_version', 'frontend_response_contract_id', 'frontend_response_contract_version', 'applicability_code', 'supports_user_notes', 'supports_web_research'].sort());
        expect(JSON.stringify(catalog)).not.toMatch(/prompt|label|instruction/i);
    });

    it('matches A2 migrated task IDs while keeping greenfield tasks non-parity', () => {
        const localByBackendTask = new Map<string, AiExportTaskDefinition>();
        for (const task of AI_EXPORT_TASK_CATALOG) localByBackendTask.set(task.backendTask, task);

        const classifications = new Map<string, Set<string>>();
        const greenfieldKeys = new Set<string>();
        const fixtureDomains = [
            ['portfolio', compatibilityFixture.domains.portfolio],
            ['asset', compatibilityFixture.domains.asset],
            ['fx', compatibilityFixture.domains.fx],
            ['broker', compatibilityFixture.domains.broker],
        ] as const;

        const addClassification = (domain: string, task: string, classification: string) => {
            const key = `${domain}.${task}`;
            const values = classifications.get(key);
            if (values) values.add(classification);
            else classifications.set(key, new Set([classification]));
        };

        for (const [, fixtureDomain] of fixtureDomains) {
            for (const mapping of fixtureDomain.legacy_mappings) {
                const localTask = localByBackendTask.get(mapping.target_task);
                expect(localTask).toBeDefined();
                expect(localTask?.domain).toBe(mapping.target_domain);
                expect(localTask?.renderModes).toContain(mapping.render_mode);
                expect(mapping.classification).toBe('migration-parity');
                addClassification(mapping.target_domain, mapping.target_task, mapping.classification);
            }
        }

        for (const [domain, fixtureDomain] of fixtureDomains) {
            for (const greenfieldTask of fixtureDomain.greenfield_tasks) {
                const localTask = localByBackendTask.get(greenfieldTask.target_task);
                expect(localTask).toBeDefined();
                expect(localTask?.domain).toBe(domain);
                expect(localTask?.renderModes).toEqual(greenfieldTask.render_modes);
                expect(greenfieldTask.classification).toBe('greenfield');
                const key = `${domain}.${greenfieldTask.target_task}`;
                greenfieldKeys.add(key);
                addClassification(domain, greenfieldTask.target_task, greenfieldTask.classification);
            }
        }

        expect(greenfieldKeys).toHaveLength(11);
        expect(classifications).toHaveLength(19);
        for (const task of AI_EXPORT_TASK_CATALOG) {
            const key = `${task.domain}.${task.backendTask}`;
            const expectedClassification = greenfieldKeys.has(key) ? 'greenfield' : 'migration-parity';
            expect(classifications.get(key)).toEqual(new Set([expectedClassification]));
        }
    });
});
