/**
 * «Calcolalo in LibreFolio» (plan 78, L4a): the PAC prompt sends the user to the PAC allocator, step by step.
 *
 * The backend declares only the tool's code (`suggested_tools`); the renderer writes the block in the interface
 * language, and every label of the tool is the tool's own i18n key, so a label that changes in the tool changes in the
 * prompt too. Pins structure only: where the block goes, that it is there only when a tool is suggested, that the tool's
 * labels come from the tool's keys, and that an unknown tool closes the catalog. Never a wording.
 */
import {describe, expect, it} from 'vitest';

import {SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import {reconcileAiExportCatalog} from '../catalog/compatibility';
import type {AiExportCompatibleSelection} from '../catalog/shared';
import {renderAiExportPromptDiagnostics, type AiExportPromptTranslate} from '../templates/promptRenderer';
import {AI_EXPORT_TOOL_GUIDES, AI_EXPORT_TOOLS_NAV_KEY} from '../templates/toolGuides';
import {backendCatalogFixture, compatibilityFixture, selectionFixture, snapshotFixture} from './runtimeFixtures';

const PAC = selectionFixture('analysis', 'portfolio.pac_planning');
const GUIDE = AI_EXPORT_TOOL_GUIDES.pac_allocator;

/** Every key comes back as itself; a message's values follow it, so the case can see which labels filled it. */
const keys: AiExportPromptTranslate = (key, values) => (values ? `${key} ${Object.values(values).join(' ')}` : key);

function render(selection: AiExportCompatibleSelection, translate: AiExportPromptTranslate = keys) {
    return renderAiExportPromptDiagnostics({selection, compatibility: compatibilityFixture(), snapshot: snapshotFixture(selection), responseLanguage: 'English', translate});
}

function toolSection(selection: AiExportCompatibleSelection, translate: AiExportPromptTranslate = keys): string {
    const sections = render(selection, translate).sections.filter((section) => section.id === 'librefolio_tool');
    expect(sections, 'exactly one librefolio_tool section').toHaveLength(1);
    return sections[0].content;
}

describe('the PAC prompt', () => {
    it('is in the new shape, with the tool block right after Additional LibreFolio Data', () => {
        const ids = render(PAC).sections.map((section) => section.id);
        expect(ids[0]).toBe('task');
        expect(ids.indexOf('librefolio_tool')).toBe(ids.indexOf('additional_librefolio_data') + 1);
        expect(ids.indexOf('librefolio_tool')).toBeLessThan(ids.indexOf('domain_notes'));
    });

    it("writes the tool's path and every step from the tool's own keys, quoted", () => {
        const content = toolSection(PAC);
        expect(content).toContain(`"${AI_EXPORT_TOOLS_NAV_KEY}"`);
        expect(content).toContain(`### ${GUIDE.nameKey}`);
        for (const step of GUIDE.steps) {
            expect(content).toContain(`"${step.labelKey}": ${step.explanationKey}`);
            for (const valueKey of Object.values(step.values ?? {})) expect(content).toContain(`"${valueKey}"`);
        }
    });

    it("follows a label changed in the tool: the prompt is the tool's own word", () => {
        const renamed = 'Targets, renamed in the tool';
        const translate: AiExportPromptTranslate = (key, values) => (key === 'tools.pacAllocator.planner.steps.targets' ? renamed : keys(key, values));
        expect(toolSection(PAC, translate)).toContain(`"${renamed}":`);
    });
});

describe('only an analysis that suggests a tool has the block', () => {
    const analyses = compatibilityFixture().selections.filter((selection) => selection.kind === 'analysis' && selection.id !== 'portfolio.pac_planning');

    it.each(analyses.map((selection) => [selection.id, selection] as const))('%s has no tool block', (_id, selection) => {
        expect(render(selection).sections.map((section) => section.id)).not.toContain('librefolio_tool');
    });
});

describe('a tool the frontend cannot write closes the catalog', () => {
    it('an unknown suggested tool is a tool_suggestion_mismatch', () => {
        const catalog = backendCatalogFixture();
        const analyses = catalog.analyses.map((entry) => (entry.id === 'portfolio.pac_planning' ? {...entry, suggested_tools: [{tool_code: 'a_tool_added_later'}]} : entry));
        const result = reconcileAiExportCatalog({...catalog, analyses});
        expect(result.status).toBe('disabled');
        expect(result.reasonCodes).toContain('tool_suggestion_mismatch');
        // Positive control: the same catalog with the known tool is compatible
        expect(reconcileAiExportCatalog(catalog).status).toBe('compatible');
    });
});

describe('every key of the block is in the four catalogues', () => {
    const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};
    const FIXED = ['aiExport.tool.heading', 'aiExport.tool.intro', 'aiExport.tool.when', 'aiExport.tool.path', 'aiExport.tool.inputs', 'aiExport.tool.returns', 'aiExport.tool.steps.sidebar', 'aiExport.tool.steps.card', 'aiExport.additionalData.steps.openLibreFolio'];
    const ALL = [...FIXED, AI_EXPORT_TOOLS_NAV_KEY, GUIDE.nameKey, GUIDE.whenKey, GUIDE.returnsKey, ...GUIDE.steps.flatMap((step) => [step.labelKey, step.explanationKey, ...Object.values(step.values ?? {})])];

    function leaf(catalogue: unknown, key: string): unknown {
        return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    }

    it.each([...SUPPORTED_LOCALES])('%s.json has every key, and each explanation names its placeholders', (locale) => {
        const catalogue = CATALOGUES[locale];
        const missing = ALL.filter((key) => typeof leaf(catalogue, key) !== 'string');
        expect(missing, `${locale}.json lacks keys of the tool block`).toEqual([]);
        for (const step of GUIDE.steps) {
            const sentence = leaf(catalogue, step.explanationKey) as string;
            for (const placeholder of Object.keys(step.values ?? {})) expect(sentence, `${locale} ${step.explanationKey}`).toContain(`{${placeholder}}`);
        }
    });
});
