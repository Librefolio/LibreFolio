/**
 * pluginText — a BRIM import plugin's name and description in the UI language.
 *
 * A plugin runs backend-side and writes its `name` and `description` in English. The four catalogues
 * carry `brimPlugins.<code>.name` and `brimPlugins.<code>.description` (test_brim_providers.py keeps
 * the English ones equal to the plugins' own and the other three filled in), and the plugin select,
 * the import wizard and the About page read them through these two lookups, built on `translateOr`:
 *
 *   - hit    → the catalogue's text, at the plugin's own key;
 *   - miss   → svelte-i18n hands the key back: the plugin's own text, never the raw key;
 *   - empty  → a translation written as "" is no translation: the plugin's own text again;
 *   - and when the plugin's own text is missing too, the name falls back to the code (something has
 *     to name the plugin) and the description to '' (nothing to describe is better than a code).
 *
 * The fake catalogues below are written by this file: their values are test data, not the app's
 * translations, which this file never reads.
 */

import {describe, expect, it, vi} from 'vitest';
import {brimPluginDescription, brimPluginName, type BrimPluginText} from './pluginText';

const DEPOSIT = 'broker_scalable_deposit';
const NAME_KEY = `brimPlugins.${DEPOSIT}.name`;
const DESCRIPTION_KEY = `brimPlugins.${DEPOSIT}.description`;

/** The plugin as `GET /brokers/import/plugins` lists it: its own English name and description. */
const PLUGIN: BrimPluginText = {
    code: DEPOSIT,
    name: 'Scalable Capital overnight account',
    description: 'Import the Scalable Capital overnight account from the LibreFolio exporter file.',
};

/** Fake `$t`: a known key answers its catalogue text (even ""); an unknown key comes back as itself, as svelte-i18n answers a missing key. */
function makeT(known: Record<string, string> = {}) {
    return vi.fn((key: string): string => (Object.hasOwn(known, key) ? known[key] : key));
}

describe('brimPluginName', () => {
    it('is the catalogue name, looked up at brimPlugins.<code>.name', () => {
        const t = makeT({[NAME_KEY]: 'Overnight account, in the UI language'});
        expect(brimPluginName(PLUGIN, t)).toBe('Overnight account, in the UI language');
        expect(t, 'one lookup, at the name key of the plugin’s own code').toHaveBeenCalledExactlyOnceWith(NAME_KEY);
    });

    it('keeps the plugin’s own name when the catalogue does not know the plugin — never the raw key', () => {
        const t = makeT({'brimPlugins.broker_scalable.name': 'another plugin’s name'});
        expect(brimPluginName(PLUGIN, t)).toBe(PLUGIN.name);
    });

    it('keeps the plugin’s own name when the catalogue’s translation is empty', () => {
        const t = makeT({[NAME_KEY]: ''});
        expect(brimPluginName(PLUGIN, t)).toBe(PLUGIN.name);
    });

    it('reads only the name key: a catalogue that has the description alone leaves the plugin’s name', () => {
        const t = makeT({[DESCRIPTION_KEY]: 'a description is not a name'});
        expect(brimPluginName(PLUGIN, t)).toBe(PLUGIN.name);
    });

    it.each([
        ['null', null],
        ['empty', ''],
        ['left out', undefined],
    ])('falls back to the code when the plugin’s name is %s and the catalogue has none', (_label, name) => {
        const plugin: BrimPluginText = name === undefined ? {code: DEPOSIT} : {code: DEPOSIT, name};
        expect(brimPluginName(plugin, makeT())).toBe(DEPOSIT);
        expect(brimPluginName(plugin, makeT({[NAME_KEY]: ''})), 'an empty translation is no translation').toBe(DEPOSIT);
    });

    it('names a plugin known only by its code — a refusal’s context — from the catalogue', () => {
        expect(brimPluginName({code: DEPOSIT}, makeT({[NAME_KEY]: 'Overnight account, in the UI language'}))).toBe('Overnight account, in the UI language');
    });
});

describe('brimPluginDescription', () => {
    it('is the catalogue description, looked up at brimPlugins.<code>.description', () => {
        const t = makeT({[DESCRIPTION_KEY]: 'What the plugin reads, in the UI language'});
        expect(brimPluginDescription(PLUGIN, t)).toBe('What the plugin reads, in the UI language');
        expect(t, 'one lookup, at the description key of the plugin’s own code').toHaveBeenCalledExactlyOnceWith(DESCRIPTION_KEY);
    });

    it('keeps the plugin’s own description when the catalogue does not know the plugin — never the raw key', () => {
        expect(brimPluginDescription(PLUGIN, makeT())).toBe(PLUGIN.description);
    });

    it('keeps the plugin’s own description when the catalogue’s translation is empty', () => {
        expect(brimPluginDescription(PLUGIN, makeT({[DESCRIPTION_KEY]: ''}))).toBe(PLUGIN.description);
    });

    it('reads only the description key: a catalogue that has the name alone leaves the plugin’s description', () => {
        expect(brimPluginDescription(PLUGIN, makeT({[NAME_KEY]: 'a name is not a description'}))).toBe(PLUGIN.description);
    });

    it.each([
        ['null', null],
        ['left out', undefined],
    ])('is empty when the plugin’s description is %s and the catalogue has none — not the code, not the name', (_label, description) => {
        const plugin: BrimPluginText = description === undefined ? {code: DEPOSIT, name: PLUGIN.name} : {code: DEPOSIT, name: PLUGIN.name, description};
        expect(brimPluginDescription(plugin, makeT())).toBe('');
        expect(brimPluginDescription(plugin, makeT({[DESCRIPTION_KEY]: ''})), 'an empty translation is no translation').toBe('');
    });

    it('stays empty for a plugin that describes itself with an empty string', () => {
        expect(brimPluginDescription({code: DEPOSIT, name: PLUGIN.name, description: ''}, makeT())).toBe('');
    });
});
