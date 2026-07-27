import {describe, expect, it} from 'vitest';

import compatibilityFixtureJson from '../../../../../../backend/test_scripts/fixtures/ai_export/legacy_semantics/prompt_compatibility.v1.json';
import {ASSET_AI_EXPORT_TASKS} from '../catalog/assetTasks';
import {BROKER_AI_EXPORT_TASKS} from '../catalog/brokerTasks';
import {FX_AI_EXPORT_TASKS} from '../catalog/fxTasks';
import {PORTFOLIO_AI_EXPORT_TASKS} from '../catalog/portfolioTasks';
import {AI_EXPORT_DETAIL_LEVELS, type AiExportDomain} from '../catalog/shared';

type Classification = 'migration-parity' | 'greenfield';
type RenderMode = 'data_only' | 'full_prompt';
type LegacyCatalogDomain = 'portfolio' | 'asset' | 'fx';

interface LegacyMapping {
    legacy_prompt_id: string;
    target_domain: AiExportDomain;
    target_task: string;
    render_mode: RenderMode;
    classification: Classification;
    scope?: string;
}

interface GreenfieldTask {
    target_task: string;
    render_modes: RenderMode[];
    classification: Classification;
}

interface DomainCompatibility {
    legacy_mappings: LegacyMapping[];
    greenfield_tasks: GreenfieldTask[];
    legacy_surface?: {
        catalog_source: string;
        scope: string;
        task_specific_behavior: boolean;
    };
}

interface CompatibilityFixture {
    fixture_schema_version: string;
    classifications: Classification[];
    domains: {
        portfolio: DomainCompatibility;
        asset: DomainCompatibility;
        fx: DomainCompatibility;
        broker: DomainCompatibility;
    };
    greenfield_capabilities: Array<{
        capability: string;
        values?: string[];
        target_task?: string;
        target_domain?: string;
        classification: Classification;
    }>;
}

const fixture = compatibilityFixtureJson as CompatibilityFixture;

const LEGACY_PROMPT_IDS = {
    portfolio: ['snapshot', 'pac_planning', 'rebalancing', 'market_trend', 'income_review', 'describe_portfolio'],
    asset: ['asset_snapshot', 'asset_classify'],
    fx: ['fx_snapshot', 'fx_trend'],
} as const;

const LEGACY_RENDER_MODES: Record<LegacyCatalogDomain, Readonly<Record<string, RenderMode>>> = {
    portfolio: {
        snapshot: 'data_only',
        pac_planning: 'full_prompt',
        rebalancing: 'full_prompt',
        market_trend: 'full_prompt',
        income_review: 'full_prompt',
        describe_portfolio: 'full_prompt',
    },
    asset: {
        asset_snapshot: 'data_only',
        asset_classify: 'full_prompt',
    },
    fx: {
        fx_snapshot: 'data_only',
        fx_trend: 'full_prompt',
    },
};

const V2_TASK_IDS: Record<AiExportDomain, ReadonlySet<string>> = {
    portfolio: new Set(PORTFOLIO_AI_EXPORT_TASKS.map((task) => task.backendTask)),
    asset: new Set(ASSET_AI_EXPORT_TASKS.map((task) => task.backendTask)),
    fx: new Set(FX_AI_EXPORT_TASKS.map((task) => task.backendTask)),
    broker: new Set(BROKER_AI_EXPORT_TASKS.map((task) => task.backendTask)),
};

function expectTargetTaskExists(mapping: LegacyMapping): void {
    expect(V2_TASK_IDS[mapping.target_domain].has(mapping.target_task)).toBe(true);
}

describe('legacy AI Export catalog compatibility oracle v1', () => {
    it('keeps frozen legacy IDs, classifications, render modes, and V2 targets aligned', () => {
        for (const domain of ['portfolio', 'asset', 'fx'] as const) {
            const compatibility = fixture.domains[domain];
            const mappings = compatibility.legacy_mappings;

            expect(mappings.map((mapping) => mapping.legacy_prompt_id)).toEqual(LEGACY_PROMPT_IDS[domain]);
            for (const mapping of mappings) {
                expect(mapping.classification).toBe('migration-parity');
                expect(mapping.target_domain).toBe(domain);
                expect(mapping.render_mode).toBe(LEGACY_RENDER_MODES[domain][mapping.legacy_prompt_id]);
                expectTargetTaskExists(mapping);
            }

            const representedTasks = new Set(mappings.map((mapping) => mapping.target_task));
            for (const task of compatibility.greenfield_tasks) {
                expect(task.classification).toBe('greenfield');
                expect(task.render_modes).toEqual(['data_only', 'full_prompt']);
                expect(V2_TASK_IDS[domain].has(task.target_task)).toBe(true);
                representedTasks.add(task.target_task);
            }
            expect([...representedTasks].sort()).toEqual([...V2_TASK_IDS[domain]].sort());
        }
    });

    it('records broker legacy as filtered portfolio output and broker tasks as greenfield', () => {
        const broker = fixture.domains.broker;

        expect(broker.legacy_surface).toEqual({
            catalog_source: 'portfolio',
            scope: 'single_broker_filter',
            task_specific_behavior: false,
        });
        expect(broker.legacy_mappings.map((mapping) => mapping.legacy_prompt_id)).toEqual(LEGACY_PROMPT_IDS.portfolio);
        for (const mapping of broker.legacy_mappings) {
            expect(mapping.target_domain).toBe('portfolio');
            expect(mapping.scope).toBe('single_broker_filter');
            expect(mapping.classification).toBe('migration-parity');
            expect(mapping.render_mode).toBe(LEGACY_RENDER_MODES.portfolio[mapping.legacy_prompt_id]);
            expectTargetTaskExists(mapping);
        }

        expect(broker.greenfield_tasks.map((task) => task.target_task)).toEqual(BROKER_AI_EXPORT_TASKS.map((task) => task.backendTask));
        for (const task of broker.greenfield_tasks) {
            expect(task.classification).toBe('greenfield');
            expect(task.render_modes).toEqual(['data_only', 'full_prompt']);
            expect(V2_TASK_IDS.broker.has(task.target_task)).toBe(true);
        }
    });

    it('classifies three-state detail levels as greenfield conformance', () => {
        const detailLevels = fixture.greenfield_capabilities.find((capability) => capability.capability === 'detail_levels');

        expect(detailLevels).toEqual({
            capability: 'detail_levels',
            values: AI_EXPORT_DETAIL_LEVELS,
            classification: 'greenfield',
        });
        expect(AI_EXPORT_DETAIL_LEVELS).toEqual(['compact', 'standard', 'full']);
        expect(fixture.classifications).toEqual(['migration-parity', 'greenfield']);
    });
});
