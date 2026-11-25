/**
 * @vitest-environment node
 *
 * «Calcolalo in LibreFolio» (plan 78, L4a): the panel and the probe write the tool block byte for byte alike.
 *
 * The block is the first place where the two fill placeholders with different code: the panel through svelte-i18n
 * (`$_(key, {values})`, ICU message format), the probe through `probeTranslation`'s plain `{name}` replacement. A
 * sentence ICU cannot parse (an ASCII apostrophe next to a brace, a stray brace) would break the PAC copy in that
 * language while the probe still renders it. For every language and every key of the guide, the real formatter must
 * not throw, must leave no placeholder behind, and must give exactly what the probe gives.
 */
import {get} from 'svelte/store';
import {_, init, locale, waitLocale} from 'svelte-i18n';
import {beforeAll, describe, expect, it} from 'vitest';

import {SUPPORTED_LOCALES} from '$lib/i18n';
import {probeTranslation} from '../../../../../scripts/ai-export-render-prompt-probe';
import {AI_EXPORT_TOOL_GUIDES, AI_EXPORT_TOOLS_NAV_KEY} from '../templates/toolGuides';

const GUIDE = AI_EXPORT_TOOL_GUIDES.pac_allocator;
const FIXED = ['aiExport.tool.heading', 'aiExport.tool.intro', 'aiExport.tool.when', 'aiExport.tool.path', 'aiExport.tool.inputs', 'aiExport.tool.returns', 'aiExport.tool.steps.sidebar', 'aiExport.tool.steps.card', AI_EXPORT_TOOLS_NAV_KEY, GUIDE.nameKey, GUIDE.whenKey, GUIDE.returnsKey];

beforeAll(async () => {
    // The app's own options (`initI18n`): no custom formats
    init({fallbackLocale: 'en', initialLocale: 'en'});
    await waitLocale('en');
});

describe.each([...SUPPORTED_LOCALES])('%s: svelte-i18n and the probe write the tool block alike', (lang) => {
    async function formatters() {
        locale.set(lang);
        await waitLocale(lang);
        return {panel: get(_), probe: probeTranslation(lang)};
    }

    it('every fixed sentence and label', async () => {
        const {panel, probe} = await formatters();
        // Positive control: the catalogue is loaded, so equal outputs are sentences, not two keys echoed back
        expect(panel('aiExport.tool.heading')).not.toBe('aiExport.tool.heading');
        for (const key of FIXED) expect(panel(key), key).toBe(probe(key));
    });

    it('every step, its label and its sentence with the quoted tool labels', async () => {
        const {panel, probe} = await formatters();
        for (const step of GUIDE.steps) {
            expect(panel(step.labelKey), step.labelKey).toBe(probe(step.labelKey));
            // The renderer's values: each tool label, translated and quoted
            const values = Object.fromEntries(Object.entries(step.values ?? {}).map(([name, key]) => [name, `"${probe(key)}"`]));
            const formatted = panel(step.explanationKey, {values});
            expect(formatted, step.explanationKey).not.toMatch(/\{\w+\}/);
            expect(formatted, step.explanationKey).toBe(probe(step.explanationKey, values));
        }
    });
});
