/**
 * pluginSettingsForm — the plugin settings form without the DOM (workstream X, lot CP11b; plan 03 §4.4).
 *
 * `PluginSettingsForm.svelte` only draws what these functions decide, so the rules are pinned here, once:
 *   - `groupByFamily`: the entries by family, the price sources (`asset`) before the exchange-rate sources (`fx`) before
 *     the import sources (`brim`, W-BS) before the tools (`tool`, X5-4b) whatever the order of the answer, each family in the answer's order, a family
 *     without entries left out;
 *   - `FAMILY_ICONS`: one icon per family of `FAMILY_ORDER`, no more and no fewer, the one the family has on the
 *     documentation's home — lucide's `ChartColumn` for the price sources, `Coins` for the exchange-rate sources — and
 *     an icon of its own for the import sources and another for the tools, none of them the same as another;
 *   - the catalogues: the family's title key, `pluginSettings.families.tool` included, reads in the four languages;
 *   - the texts: `fieldLabel`, `fieldDescription` and `optionLabel` say the plugin's key when it is translated and the
 *     plugin's English text otherwise (a key answered with itself, or with nothing, is no translation), and never ask
 *     for a key the plugin did not declare; `displayValue` writes the value in force of a field the caller cannot
 *     change — an option by its label, a value the options do not hold as it is, no value as '—';
 *   - `readOnlyReason`: none for an editable field, `locked` when a server variable sets it, `adminOnly` otherwise;
 *     `secretState`: `invalidEnv` before `env` before `unreadable` before `set` before `unset`;
 *   - `FormState` and its four moves (`typed`, `chosen`, `cleared`, `restored`), none of which changes the form it is
 *     given; `shownText` and `shownChoice`: what was typed or chosen, else the default of a field to clear, else the
 *     value in force;
 *   - `draftOf`: the edits of the fields the caller may change, and only of those that change — a text or a choice
 *     equal to the value in force makes no edit (a number compared as a number), emptying a text whose saved value is
 *     in force deletes it (`clear`), an empty secret makes no edit, a field to clear is cleared;
 *   - `draftProblems`: `number`, `integer`, `below`/`above` with the bound, `tooShort`/`tooLong` with the length
 *     counted in code points as the server's `len()` counts it, `option`, and `required` for an empty secret;
 *   - `writeItems`: one item per edit, in the order the plugin declares its fields, each carrying exactly one of
 *     `value` (a number field's text parsed), `secret_value` and `clear: true`;
 *   - `refusalsByField` and `refusalKey`: the refused items by field; a code this interface does not know reads as an
 *     invalid value;
 *   - `own`: every lookup by field key reads what a map holds itself, never what every object inherits — a plugin may
 *     declare a field named `constructor` (the backend's key pattern allows it), and it is a field like any other.
 *
 * Node environment: nothing here renders. The translator is a fake each case hands in. Inputs are deep-frozen where a
 * function must leave what it is given as it was: a mutation throws instead of passing.
 */
import {describe, expect, it, vi} from 'vitest';
import {ChartColumn, Coins} from 'lucide-svelte';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import type {PluginSettingsEntry, PluginSettingWriteResult, SettingField, SettingOption} from './pluginSettingsApi';
import {
    chosen,
    cleared,
    displayValue,
    draftOf,
    draftProblems,
    EMPTY_FORM,
    FAMILY_ICONS,
    FAMILY_ORDER,
    FAMILY_TITLE_KEYS,
    fieldDescription,
    fieldLabel,
    groupByFamily,
    optionLabel,
    own,
    PROBLEM_KEYS,
    readOnlyReason,
    refusalKey,
    refusalsByField,
    restored,
    SCOPE_KEYS,
    secretState,
    shownChoice,
    shownText,
    typed,
    writeItems,
    type FieldEdit,
    type FormState,
    type InputProblem,
    type PluginDraft,
} from './pluginSettingsForm';

// --- Fixtures ------------------------------------------------------------------------------------------------------

/** A field as `fieldOf` hands it over, every key present: an editable user text field, nothing in force. */
function field(over: Partial<SettingField> & Pick<SettingField, 'key'>): SettingField {
    return {
        type: 'string',
        scope: 'user',
        secret: false,
        required: false,
        label: over.key,
        description: '',
        label_key: null,
        description_key: null,
        options: [],
        min_length: null,
        max_length: null,
        minimum: null,
        maximum: null,
        default: null,
        value: null,
        is_set: false,
        source: 'none',
        locked: false,
        env_variable: null,
        editable: true,
        problem: null,
        updated_at: null,
        ...over,
    };
}

function entry(fields: SettingField[], over: Partial<PluginSettingsEntry> = {}): PluginSettingsEntry {
    return {family: 'asset', plugin_code: 'mockprov', plugin_name: 'Mock provider', icon_url: null, configured: true, fields, ...over};
}

const REGION_OPTIONS: SettingOption[] = [
    {value: 'eu', label: 'Europe', label_key: null},
    {value: 'us', label: 'United States', label_key: 'pluginSettings.asset.mockprov.option.region.us'},
];

/** A saved user text, its default behind it. */
const NICKNAME = field({key: 'nickname', label: 'Nickname', value: 'mine', default: 'anon', is_set: true, source: 'db'});
/** An instance number at its default. */
const TOLERANCE = field({key: 'price_tolerance', type: 'number', scope: 'system', label: 'Price tolerance', minimum: 0, maximum: 10, default: 0.5, value: 0.5, source: 'default'});
/** A user integer at its default. */
const RETRIES = field({key: 'retries', type: 'integer', minimum: 1, maximum: 5, default: 3, value: 3, source: 'default'});
/** A saved user choice. */
const REGION = field({key: 'region', type: 'select', options: REGION_OPTIONS, default: 'eu', value: 'us', is_set: true, source: 'db'});
/** An instance switch at its default. */
const VERBOSE = field({key: 'verbose', type: 'boolean', scope: 'system', default: false, value: false, source: 'default'});
/** A user secret, not set: it has neither value nor default. */
const API_KEY = field({key: 'api_key', secret: true, required: true, min_length: 8});

/** Freezes a value and everything it holds, so that a function changing its input throws instead of passing. */
function frozen<T>(value: T): T {
    if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
        for (const child of Object.values(value)) frozen(child);
        Object.freeze(value);
    }
    return value;
}

/** A translator knowing the keys of `catalogue`, answering any other key with the key itself, as svelte-i18n does. */
function translatorOf(catalogue: Record<string, string> = {}) {
    return vi.fn((key: string) => (Object.hasOwn(catalogue, key) ? catalogue[key] : key));
}

// --- Groups ----------------------------------------------------------------------------------------------------------

describe('groupByFamily — the groups of the Plugins tab', () => {
    const JUSTETF = entry([], {plugin_code: 'justetf'});
    const BORSA = entry([], {plugin_code: 'borsa_italiana'});
    const ECB = entry([], {family: 'fx', plugin_code: 'ecb'});
    const MOCKFX = entry([], {family: 'fx', plugin_code: 'mockfx'});

    it('puts the price sources before the exchange-rate sources whatever the order of the answer, each family in the answer’s order', () => {
        const answer = frozen([ECB, JUSTETF, MOCKFX, BORSA]);

        expect(groupByFamily(answer)).toStrictEqual([
            {family: 'asset', entries: [JUSTETF, BORSA]},
            {family: 'fx', entries: [ECB, MOCKFX]},
        ]);
    });

    it('leaves out a family without entries, and answers no group for no entry', () => {
        expect(groupByFamily([MOCKFX, ECB]), 'only exchange-rate sources: no empty asset group').toStrictEqual([{family: 'fx', entries: [MOCKFX, ECB]}]);
        expect(groupByFamily([BORSA]), 'only price sources: no empty fx group').toStrictEqual([{family: 'asset', entries: [BORSA]}]);
        expect(groupByFamily([])).toStrictEqual([]);
    });

    it('names the four families, asset first and the tools last, each with a whole key for its title', () => {
        expect(FAMILY_ORDER).toEqual(['asset', 'fx', 'brim', 'tool']);
        expect(FAMILY_TITLE_KEYS).toStrictEqual({
            asset: 'pluginSettings.families.asset',
            fx: 'pluginSettings.families.fx',
            brim: 'pluginSettings.families.brim',
            tool: 'pluginSettings.families.tool',
        });
    });

    it('puts the tools after the import sources, the exchange-rate sources and the price sources, whatever the order of the answer, each family in the answer’s order', () => {
        const IMPORTER = entry([], {family: 'brim', plugin_code: 'broker_x'});
        const TOOL = entry([], {family: 'tool', plugin_code: 'fx_converter'});
        const OTHER_TOOL = entry([], {family: 'tool', plugin_code: 'compound_growth'});

        expect(groupByFamily(frozen([TOOL, IMPORTER, OTHER_TOOL, ECB, JUSTETF]))).toStrictEqual([
            {family: 'asset', entries: [JUSTETF]},
            {family: 'fx', entries: [ECB]},
            {family: 'brim', entries: [IMPORTER]},
            {family: 'tool', entries: [TOOL, OTHER_TOOL]},
        ]);
        expect(groupByFamily([ECB, JUSTETF]), 'no tool: no tool group').toStrictEqual([
            {family: 'asset', entries: [JUSTETF]},
            {family: 'fx', entries: [ECB]},
        ]);
        expect(groupByFamily([TOOL]), 'tools only: the tool group alone, not read as another family').toStrictEqual([{family: 'tool', entries: [TOOL]}]);
    });

    it('lists, as groups, exactly the families that have entries: the family filter of the tab', () => {
        const IMPORTER = entry([], {family: 'brim', plugin_code: 'broker_x'});
        const TOOL = entry([], {family: 'tool', plugin_code: 'fx_converter'});

        expect(groupByFamily([TOOL, JUSTETF]).map((group) => group.family)).toEqual(['asset', 'tool']);
        expect(groupByFamily([IMPORTER, TOOL]).map((group) => group.family)).toEqual(['brim', 'tool']);
        expect(groupByFamily([TOOL, IMPORTER, ECB, JUSTETF]).map((group) => group.family)).toEqual([...FAMILY_ORDER]);
    });

    it('puts the import sources after the exchange-rate sources and the price sources, whatever the order of the answer', () => {
        const IMPORTER = entry([], {family: 'brim', plugin_code: 'broker_x'});
        const OTHER_IMPORTER = entry([], {family: 'brim', plugin_code: 'broker_y'});

        expect(groupByFamily(frozen([IMPORTER, ECB, OTHER_IMPORTER, JUSTETF]))).toStrictEqual([
            {family: 'asset', entries: [JUSTETF]},
            {family: 'fx', entries: [ECB]},
            {family: 'brim', entries: [IMPORTER, OTHER_IMPORTER]},
        ]);
        expect(groupByFamily([ECB, JUSTETF]), 'no import source: no brim group').toStrictEqual([
            {family: 'asset', entries: [JUSTETF]},
            {family: 'fx', entries: [ECB]},
        ]);
    });

    it('has one icon per family of FAMILY_ORDER, no more and no fewer: a new family adds its row', () => {
        expect(Object.keys(FAMILY_ICONS).sort(), 'a row for each family, and for nothing else').toEqual([...FAMILY_ORDER].sort());
        for (const family of FAMILY_ORDER) expect(FAMILY_ICONS[family], `${family}: a component, not an empty row`).toBeTypeOf('function');
    });

    it('gives the import sources an icon of their own: neither the price sources’ nor the exchange-rate sources’', () => {
        expect(FAMILY_ICONS.brim, 'a component, not an empty row').toBeTypeOf('function');
        expect(FAMILY_ICONS.brim).not.toBe(ChartColumn);
        expect(FAMILY_ICONS.brim).not.toBe(Coins);
    });

    it('gives the tools an icon of their own: neither the price sources’, the exchange-rate sources’ nor the import sources’', () => {
        expect(FAMILY_ICONS.tool, 'a component, not an empty row').toBeTypeOf('function');
        expect(FAMILY_ICONS.tool).not.toBe(ChartColumn);
        expect(FAMILY_ICONS.tool).not.toBe(Coins);
        expect(FAMILY_ICONS.tool).not.toBe(FAMILY_ICONS.brim);
    });

    it('gives each family the icon of the documentation’s home: lucide’s ChartColumn to the price sources, Coins to the exchange-rate sources', () => {
        // The premise: two different icons that exist, so that neither identity below can hold between two undefined.
        expect(ChartColumn, 'premise: lucide exports ChartColumn').toBeTypeOf('function');
        expect(Coins, 'premise: lucide exports Coins').toBeTypeOf('function');
        expect(ChartColumn).not.toBe(Coins);

        expect(FAMILY_ICONS.asset).toBe(ChartColumn);
        expect(FAMILY_ICONS.fx).toBe(Coins);
    });
});

// --- Texts -----------------------------------------------------------------------------------------------------------

describe('fieldLabel, fieldDescription, optionLabel — the plugin’s key when translated, its English text otherwise', () => {
    const LABELLED = field({key: 'region', label: 'Region', label_key: 'pluginSettings.asset.mockprov.label.region', description: 'Where to look', description_key: 'pluginSettings.asset.mockprov.description.region'});
    const OPTION: SettingOption = {value: 'us', label: 'United States', label_key: 'pluginSettings.asset.mockprov.option.region.us'};

    it('says the translation of the key the plugin declared', () => {
        const t = translatorOf({
            'pluginSettings.asset.mockprov.label.region': 'Regione',
            'pluginSettings.asset.mockprov.description.region': 'Dove cercare',
            'pluginSettings.asset.mockprov.option.region.us': 'Stati Uniti',
        });

        expect(fieldLabel(LABELLED, t)).toBe('Regione');
        expect(fieldDescription(LABELLED, t)).toBe('Dove cercare');
        expect(optionLabel(OPTION, t)).toBe('Stati Uniti');
    });

    it.each([
        ['a key the catalogue does not hold (answered with itself)', translatorOf()],
        ['a key translated as nothing', vi.fn(() => '')],
    ])('falls back to the plugin’s English text for %s', (_label, t) => {
        expect(fieldLabel(LABELLED, t)).toBe('Region');
        expect(fieldDescription(LABELLED, t)).toBe('Where to look');
        expect(optionLabel(OPTION, t)).toBe('United States');
    });

    it('says the English text of a plugin that declared no key, without asking the translator anything', () => {
        const t = translatorOf({Region: 'never asked'});

        expect(fieldLabel(field({key: 'region', label: 'Region'}), t)).toBe('Region');
        expect(fieldDescription(field({key: 'region', description: 'Where to look'}), t)).toBe('Where to look');
        expect(fieldDescription(field({key: 'region'}), t), 'no description: nothing').toBe('');
        expect(optionLabel({value: 'eu', label: 'Europe', label_key: null}, t)).toBe('Europe');
        expect(t, 'the interface never builds a key of its own').not.toHaveBeenCalled();
    });
});

describe('displayValue — the value in force of a field the caller cannot change', () => {
    const t = translatorOf({'pluginSettings.asset.mockprov.option.region.us': 'Stati Uniti'});

    it.each<[string, SettingField, string]>([
        ['no value', field({key: 'endpoint', value: null}), '—'],
        ['no value, on a select too', field({key: 'region', type: 'select', options: REGION_OPTIONS, value: null}), '—'],
        ['a choice: its option’s label', field({key: 'region', type: 'select', options: REGION_OPTIONS, value: 'eu'}), 'Europe'],
        ['a choice whose option is translated', field({key: 'region', type: 'select', options: REGION_OPTIONS, value: 'us'}), 'Stati Uniti'],
        ['a choice the options do not hold: as it is', field({key: 'region', type: 'select', options: REGION_OPTIONS, value: 'jp'}), 'jp'],
        ['a text', field({key: 'endpoint', value: 'https://api.example'}), 'https://api.example'],
        ['a number', field({key: 'price_tolerance', type: 'number', value: 0.5}), '0.5'],
        ['a zero, which is a value', field({key: 'retries', type: 'integer', value: 0}), '0'],
        ['a switch on', field({key: 'verbose', type: 'boolean', value: true}), 'true'],
        ['a switch off', field({key: 'verbose', type: 'boolean', value: false}), 'false'],
    ])('%s', (_label, given, shown) => {
        expect(displayValue(given, t)).toBe(shown);
    });

    it('has a whole key for each scope', () => {
        expect(SCOPE_KEYS).toStrictEqual({user: 'pluginSettings.scope.user', system: 'pluginSettings.scope.system'});
    });
});

// --- Read-only fields and secrets ------------------------------------------------------------------------------------

describe('readOnlyReason and secretState', () => {
    it.each<[string, Partial<SettingField>, ReturnType<typeof readOnlyReason>]>([
        ['an editable field is never read-only', {editable: true}, null],
        ['not even one marked locked', {editable: true, locked: true}, null],
        ['a field a server variable sets', {editable: false, locked: true, source: 'env'}, 'locked'],
        ['an instance field, for a user who is not an administrator', {editable: false, locked: false, scope: 'system'}, 'adminOnly'],
    ])('readOnlyReason: %s', (_label, over, reason) => {
        expect(readOnlyReason(field({key: 'k', ...over}))).toBe(reason);
    });

    it.each<[string, Partial<SettingField>, ReturnType<typeof secretState>]>([
        ['an invalid server variable, whatever else holds', {problem: 'invalid_env', locked: true, source: 'env', is_set: true}, 'invalidEnv'],
        ['a server variable sets it (locked)', {locked: true, source: 'env', is_set: true}, 'env'],
        ['a server variable sets it (its source)', {source: 'env', is_set: true}, 'env'],
        ['a server variable, before a saved value this key cannot read', {locked: true, source: 'env', is_set: true, problem: 'unreadable'}, 'env'],
        ['a saved value this instance’s key cannot read', {source: 'db', is_set: true, problem: 'unreadable'}, 'unreadable'],
        ['a saved value', {source: 'db', is_set: true}, 'set'],
        ['nothing', {source: 'none', is_set: false}, 'unset'],
    ])('secretState: %s', (_label, over, state) => {
        expect(secretState(field({key: 'api_key', secret: true, ...over}))).toBe(state);
    });
});

// --- What the user did -----------------------------------------------------------------------------------------------

describe('FormState — what the user did, never changed in place', () => {
    /** Typed in `a`, chosen in `c` and `d`, `e` to clear. */
    const START: FormState = frozen({texts: {a: 'x'}, choices: {c: 'eu', d: true}, clears: ['e']});

    it('EMPTY_FORM holds nothing', () => {
        expect(EMPTY_FORM).toStrictEqual({texts: {}, choices: {}, clears: []});
    });

    it('typed: keeps the text — an empty one too —, and the field is no longer to clear', () => {
        expect(typed(START, 'b', 'y')).toStrictEqual({texts: {a: 'x', b: 'y'}, choices: {c: 'eu', d: true}, clears: ['e']});
        expect(typed(START, 'a', '')).toStrictEqual({texts: {a: ''}, choices: {c: 'eu', d: true}, clears: ['e']});
        expect(typed(START, 'e', 'z')).toStrictEqual({texts: {a: 'x', e: 'z'}, choices: {c: 'eu', d: true}, clears: []});
    });

    it('chosen: keeps the choice — false too —, and the field is no longer to clear', () => {
        expect(chosen(START, 'c', 'us')).toStrictEqual({texts: {a: 'x'}, choices: {c: 'us', d: true}, clears: ['e']});
        expect(chosen(START, 'e', false)).toStrictEqual({texts: {a: 'x'}, choices: {c: 'eu', d: true, e: false}, clears: []});
    });

    it('cleared: drops what was typed or chosen there, and lists the field once', () => {
        expect(cleared(START, 'a')).toStrictEqual({texts: {}, choices: {c: 'eu', d: true}, clears: ['e', 'a']});
        expect(cleared(START, 'c')).toStrictEqual({texts: {a: 'x'}, choices: {d: true}, clears: ['e', 'c']});
        expect(cleared(START, 'e'), 'already to clear: listed once').toStrictEqual({texts: {a: 'x'}, choices: {c: 'eu', d: true}, clears: ['e']});
    });

    it('restored: nothing done to the field any more, the others as they were', () => {
        expect(restored(START, 'a')).toStrictEqual({texts: {}, choices: {c: 'eu', d: true}, clears: ['e']});
        expect(restored(START, 'd')).toStrictEqual({texts: {a: 'x'}, choices: {c: 'eu'}, clears: ['e']});
        expect(restored(START, 'e')).toStrictEqual({texts: {a: 'x'}, choices: {c: 'eu', d: true}, clears: []});
        expect(restored(START, 'untouched')).toStrictEqual(START);
    });

    it('answers a new form each time: the one it was given stays as it was (it is frozen here)', () => {
        for (const next of [typed(START, 'a', 'y'), chosen(START, 'c', 'us'), cleared(START, 'a'), restored(START, 'e')]) {
            expect(next).not.toBe(START);
        }
        expect(START).toStrictEqual({texts: {a: 'x'}, choices: {c: 'eu', d: true}, clears: ['e']});
    });
});

describe('shownText and shownChoice — what a control shows', () => {
    it('a text field: what was typed (even nothing), else the default when its saved value is to go, else the value in force', () => {
        expect(shownText(NICKNAME, EMPTY_FORM)).toBe('mine');
        expect(shownText(NICKNAME, typed(EMPTY_FORM, 'nickname', 'someone'))).toBe('someone');
        expect(shownText(NICKNAME, typed(EMPTY_FORM, 'nickname', '')), 'what the user emptied stays empty').toBe('');
        expect(shownText(NICKNAME, cleared(EMPTY_FORM, 'nickname'))).toBe('anon');
        expect(shownText(NICKNAME, typed(EMPTY_FORM, 'other', 'someone')), 'another field’s text is not this one’s').toBe('mine');
    });

    it('a field without a value or a default shows nothing; a number shows as written', () => {
        expect(shownText(field({key: 'endpoint'}), EMPTY_FORM)).toBe('');
        expect(shownText(field({key: 'endpoint', value: 'x', is_set: true, source: 'db'}), cleared(EMPTY_FORM, 'endpoint')), 'to clear, no default: nothing').toBe('');
        expect(shownText(TOLERANCE, EMPTY_FORM)).toBe('0.5');
        expect(shownText(field({key: 'retries', type: 'integer', value: 0}), EMPTY_FORM)).toBe('0');
    });

    it('a choice: what was chosen (false included), else the default when its saved value is to go, else the value in force', () => {
        expect(shownChoice(REGION, EMPTY_FORM)).toBe('us');
        expect(shownChoice(REGION, chosen(EMPTY_FORM, 'region', 'eu'))).toBe('eu');
        expect(shownChoice(REGION, cleared(EMPTY_FORM, 'region'))).toBe('eu');
        expect(shownChoice(field({...VERBOSE, value: true}), chosen(EMPTY_FORM, 'verbose', false))).toBe(false);
        expect(shownChoice(field({key: 'region', type: 'select', options: REGION_OPTIONS}), EMPTY_FORM)).toBeNull();
    });
});

// --- The edits -------------------------------------------------------------------------------------------------------

describe('draftOf — the edits a form makes: on the fields the caller may change, and only where something changes', () => {
    const PLUGIN = entry([REGION, TOLERANCE, RETRIES, VERBOSE, NICKNAME, API_KEY]);

    it('makes no edit for a form nobody touched', () => {
        expect(draftOf(PLUGIN, EMPTY_FORM)).toStrictEqual({});
    });

    it('a text: an edit when it differs from the value in force, none when it says the same', () => {
        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'nickname', 'someone'))).toStrictEqual({nickname: {kind: 'text', text: 'someone'}});
        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'nickname', 'mine'))).toStrictEqual({});
    });

    it.each(['0.5', ' 0.5 ', '0.50', '.5'])('a number is compared as a number: %j says the same as 0.5', (text) => {
        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'price_tolerance', text))).toStrictEqual({});
    });

    it('a number that differs is an edit, kept as typed until it is written; an integer the same way', () => {
        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'price_tolerance', '0.75'))).toStrictEqual({price_tolerance: {kind: 'text', text: '0.75'}});
        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'retries', '3'))).toStrictEqual({});
        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'retries', '4'))).toStrictEqual({retries: {kind: 'text', text: '4'}});
        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'price_tolerance', 'abc')), 'what is no number is an edit: its problem says why').toStrictEqual({price_tolerance: {kind: 'text', text: 'abc'}});
    });

    it('emptying a text whose saved value is in force deletes it; emptying one that is not saved does nothing', () => {
        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'nickname', ''))).toStrictEqual({nickname: {kind: 'clear'}});
        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'nickname', '   ')), 'blanks are empty').toStrictEqual({nickname: {kind: 'clear'}});
        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'price_tolerance', '')), 'the default is in force: nothing to delete').toStrictEqual({});
        const savedNumber = entry([field({...TOLERANCE, value: 2, is_set: true, source: 'db'})]);
        expect(draftOf(savedNumber, typed(EMPTY_FORM, 'price_tolerance', '')), 'a saved number emptied is deleted too').toStrictEqual({price_tolerance: {kind: 'clear'}});
    });

    it('a choice: an edit when it differs from the value in force — false included —, none when it is the same', () => {
        expect(draftOf(PLUGIN, chosen(EMPTY_FORM, 'region', 'eu'))).toStrictEqual({region: {kind: 'value', value: 'eu'}});
        expect(draftOf(PLUGIN, chosen(EMPTY_FORM, 'region', 'us'))).toStrictEqual({});
        expect(draftOf(PLUGIN, chosen(EMPTY_FORM, 'verbose', true))).toStrictEqual({verbose: {kind: 'value', value: true}});
        expect(draftOf(PLUGIN, chosen(EMPTY_FORM, 'verbose', false))).toStrictEqual({});
        const switchedOn = entry([field({...VERBOSE, value: true, is_set: true, source: 'db'})]);
        expect(draftOf(switchedOn, chosen(EMPTY_FORM, 'verbose', false))).toStrictEqual({verbose: {kind: 'value', value: false}});
    });

    it('a secret: what was typed is an edit; an empty input is none — it never deletes a saved secret', () => {
        const savedKey = entry([field({...API_KEY, is_set: true, source: 'db'})]);

        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'api_key', 'sk-live-0001'))).toStrictEqual({api_key: {kind: 'secret', text: 'sk-live-0001'}});
        expect(draftOf(PLUGIN, typed(EMPTY_FORM, 'api_key', ''))).toStrictEqual({});
        expect(draftOf(savedKey, typed(EMPTY_FORM, 'api_key', ''))).toStrictEqual({});
    });

    it('a field to clear is cleared, whatever its kind, and what was typed there before no longer counts', () => {
        let form = typed(EMPTY_FORM, 'nickname', 'someone');
        for (const key of ['nickname', 'region', 'api_key', 'verbose']) form = cleared(form, key);

        expect(draftOf(PLUGIN, form)).toStrictEqual({region: {kind: 'clear'}, verbose: {kind: 'clear'}, nickname: {kind: 'clear'}, api_key: {kind: 'clear'}});
    });

    it('ignores whatever was done to a field the caller may not change', () => {
        const readOnly = entry([field({...NICKNAME, editable: false, locked: true, source: 'env'}), field({...REGION, editable: false}), field({...API_KEY, editable: false, scope: 'system'})]);
        let form = typed(EMPTY_FORM, 'nickname', 'someone');
        form = chosen(form, 'region', 'eu');
        form = typed(form, 'api_key', 'sk-live-0001');

        expect(draftOf(readOnly, form)).toStrictEqual({});
        expect(draftOf(readOnly, cleared(EMPTY_FORM, 'nickname'))).toStrictEqual({});
    });

    it('lists only the fields that change, each by its key', () => {
        let form = typed(EMPTY_FORM, 'nickname', 'someone');
        form = typed(form, 'price_tolerance', '0.5');
        form = chosen(form, 'region', 'eu');
        form = chosen(form, 'verbose', false);

        expect(draftOf(PLUGIN, form)).toStrictEqual({region: {kind: 'value', value: 'eu'}, nickname: {kind: 'text', text: 'someone'}});
    });
});

// --- Problems before the server's ------------------------------------------------------------------------------------

describe('draftProblems — what the declared rules refuse before the server does', () => {
    const text = (value: string): FieldEdit => ({kind: 'text', text: value});
    const secret = (value: string): FieldEdit => ({kind: 'secret', text: value});
    const choice = (value: string | boolean): FieldEdit => ({kind: 'value', value});
    const NUMBER = field({key: 'n', type: 'number', minimum: 0, maximum: 10});
    const INTEGER = field({key: 'n', type: 'integer', minimum: 1, maximum: 5});
    const TEXT = field({key: 'n', min_length: 3, max_length: 5});
    const SECRET = field({key: 'n', secret: true, min_length: 8, max_length: 12});
    const SELECT = field({key: 'n', type: 'select', options: REGION_OPTIONS});
    const SWITCH = field({key: 'n', type: 'boolean'});

    function problemOf(given: SettingField, edit: FieldEdit): InputProblem | undefined {
        return draftProblems(entry([given]), {n: edit})['n'];
    }

    it.each<[string, SettingField, FieldEdit, InputProblem]>([
        ['a number that is no number', NUMBER, text('abc'), {code: 'number'}],
        ['a number with a decimal comma', NUMBER, text('1,5'), {code: 'number'}],
        ['a number that is not finite', NUMBER, text('Infinity'), {code: 'number'}],
        ['a number below the minimum', NUMBER, text('-0.5'), {code: 'below', limit: 0}],
        ['a number above the maximum', NUMBER, text('10.01'), {code: 'above', limit: 10}],
        ['an integer with a fraction', INTEGER, text('2.5'), {code: 'integer'}],
        ['an integer with a fraction below the minimum: not an integer first', INTEGER, text('0.5'), {code: 'integer'}],
        ['an integer below the minimum', INTEGER, text('0'), {code: 'below', limit: 1}],
        ['an integer above the maximum', INTEGER, text('6'), {code: 'above', limit: 5}],
        ['a text shorter than min_length', TEXT, text('ab'), {code: 'tooShort', limit: 3}],
        ['a text longer than max_length', TEXT, text('abcdef'), {code: 'tooLong', limit: 5}],
        ['a secret shorter than min_length', SECRET, secret('sk-1'), {code: 'tooShort', limit: 8}],
        ['a secret longer than max_length', SECRET, secret('sk-live-0001-extra'), {code: 'tooLong', limit: 12}],
        ['an empty secret', SECRET, secret(''), {code: 'required'}],
        ['a choice the select does not offer', SELECT, choice('jp'), {code: 'option'}],
    ])('%s', (_label, given, edit, problem) => {
        expect(problemOf(given, edit)).toStrictEqual(problem);
    });

    it.each<[string, SettingField, FieldEdit]>([
        ['a number at the minimum', NUMBER, text('0')],
        ['a number at the maximum', NUMBER, text('10')],
        ['a number written with blanks around it', NUMBER, text(' 7 ')],
        ['a number without bounds, negative', field({key: 'n', type: 'number'}), text('-2.5')],
        ['an integer written with a zero fraction', INTEGER, text('3.0')],
        ['a text at min_length', TEXT, text('abc')],
        ['a text at max_length', TEXT, text('abcde')],
        ['a text without bounds', field({key: 'n'}), text('anything at all, however long it is')],
        ['a secret within its bounds', SECRET, secret('sk-live-01')],
        ['a choice the select offers', SELECT, choice('us')],
        ['a switch', SWITCH, choice(false)],
        ['a clear, whatever the rules', NUMBER, {kind: 'clear'}],
        ['a secret to clear', SECRET, {kind: 'clear'}],
    ])('no problem for %s', (_label, given, edit) => {
        expect(problemOf(given, edit)).toBeUndefined();
    });

    it('counts a length in code points, as the server’s len() does: 👑 is one character, not two', () => {
        const crowned = '👑ab';
        expect(crowned.length, 'premise: JavaScript counts four UTF-16 units').toBe(4);

        expect(problemOf(field({key: 'n', max_length: 3}), text(crowned)), 'three code points fit in 3').toBeUndefined();
        expect(problemOf(field({key: 'n', min_length: 4}), text(crowned)), 'three code points are short of 4').toStrictEqual({code: 'tooShort', limit: 4});
        expect(problemOf(field({key: 'n', secret: true, max_length: 3}), secret(crowned)), 'a secret is counted the same way').toBeUndefined();
    });

    it('keys the problems by field, leaving out the fields without one and the edits of fields the plugin does not declare', () => {
        const plugin = entry([TOLERANCE, NICKNAME, RETRIES]);
        const draft: PluginDraft = {price_tolerance: text('11'), nickname: text('someone'), retries: text('2.5'), ghost: text('abc')};

        expect(draftProblems(plugin, draft)).toStrictEqual({price_tolerance: {code: 'above', limit: 10}, retries: {code: 'integer'}});
        expect(draftProblems(plugin, {})).toStrictEqual({});
    });

    it('has a whole key per problem code', () => {
        expect(PROBLEM_KEYS).toStrictEqual({
            required: 'pluginSettings.problems.required',
            number: 'pluginSettings.problems.number',
            integer: 'pluginSettings.problems.integer',
            below: 'pluginSettings.problems.below',
            above: 'pluginSettings.problems.above',
            tooShort: 'pluginSettings.problems.tooShort',
            tooLong: 'pluginSettings.problems.tooLong',
            option: 'pluginSettings.problems.option',
        });
    });
});

// --- The write -------------------------------------------------------------------------------------------------------

describe('writeItems — one item per edit, in the order the plugin declares its fields', () => {
    const PLUGIN = entry([REGION, TOLERANCE, RETRIES, VERBOSE, NICKNAME, API_KEY]);
    const subject = {family: 'asset', plugin_code: 'mockprov'} as const;

    it('follows the declaration order, not the order the draft lists its edits in', () => {
        const draft: PluginDraft = frozen({
            api_key: {kind: 'secret', text: 'sk-live-0001'},
            nickname: {kind: 'text', text: 'someone'},
            verbose: {kind: 'value', value: true},
            region: {kind: 'clear'},
        });

        expect(writeItems(PLUGIN, draft).map((item) => item.field_key)).toEqual(['region', 'verbose', 'nickname', 'api_key']);
    });

    it.each<[string, PluginDraft, Record<string, unknown>]>([
        ['a clear carries clear: true, and no value', {nickname: {kind: 'clear'}}, {...subject, field_key: 'nickname', scope: 'user', clear: true}],
        ['a secret carries secret_value, and no value', {api_key: {kind: 'secret', text: 'sk-live-0001'}}, {...subject, field_key: 'api_key', scope: 'user', secret_value: 'sk-live-0001'}],
        ['a choice carries its value', {region: {kind: 'value', value: 'eu'}}, {...subject, field_key: 'region', scope: 'user', value: 'eu'}],
        ['a switch turned off carries false', {verbose: {kind: 'value', value: false}}, {...subject, field_key: 'verbose', scope: 'system', value: false}],
        ['a text carries what was typed, as typed', {nickname: {kind: 'text', text: 'two  words '}}, {...subject, field_key: 'nickname', scope: 'user', value: 'two  words '}],
        ['a number carries the number', {price_tolerance: {kind: 'text', text: '0.75'}}, {...subject, field_key: 'price_tolerance', scope: 'system', value: 0.75}],
        ['a number written with blanks and a zero fraction', {price_tolerance: {kind: 'text', text: ' 5.0 '}}, {...subject, field_key: 'price_tolerance', scope: 'system', value: 5}],
        ['an integer carries the integer', {retries: {kind: 'text', text: '4'}}, {...subject, field_key: 'retries', scope: 'user', value: 4}],
        ['a number it cannot parse is sent as typed: the server refuses it', {price_tolerance: {kind: 'text', text: 'abc'}}, {...subject, field_key: 'price_tolerance', scope: 'system', value: 'abc'}],
    ])('%s', (_label, draft, item) => {
        expect(writeItems(PLUGIN, draft)).toStrictEqual([item]);
    });

    it('names the plugin and each field’s own scope', () => {
        const fxEntry = entry([field({key: 'base', scope: 'system'}), field({key: 'mine'})], {family: 'fx', plugin_code: 'mockfx'});

        expect(writeItems(fxEntry, {base: {kind: 'text', text: 'EUR'}, mine: {kind: 'clear'}})).toStrictEqual([
            {family: 'fx', plugin_code: 'mockfx', field_key: 'base', scope: 'system', value: 'EUR'},
            {family: 'fx', plugin_code: 'mockfx', field_key: 'mine', scope: 'user', clear: true},
        ]);
    });

    it('names the family of a tool plugin as it is, and a tool’s fields are never secrets: user and system, each its own scope (X5-4b)', () => {
        const toolEntry = entry([field({key: 'workers', type: 'integer', scope: 'system', value: 2, default: 2, source: 'default'}), field({key: 'precision', type: 'integer', value: 2, default: 2, source: 'default'})], {
            family: 'tool',
            plugin_code: 'fx_converter',
        });

        expect(writeItems(toolEntry, {workers: {kind: 'text', text: '4'}, precision: {kind: 'text', text: '6'}})).toStrictEqual([
            {family: 'tool', plugin_code: 'fx_converter', field_key: 'workers', scope: 'system', value: 4},
            {family: 'tool', plugin_code: 'fx_converter', field_key: 'precision', scope: 'user', value: 6},
        ]);
    });

    it('a tool’s user field is editable by a non-admin, a system one is read-only for them: draftOf edits only the first (X5-4b)', () => {
        const toolEntry = entry([field({key: 'precision', type: 'integer', scope: 'user', value: 2, default: 2, source: 'default', editable: true}), field({key: 'workers', type: 'integer', scope: 'system', value: 2, default: 2, source: 'default', editable: false})], {
            family: 'tool',
            plugin_code: 'fx_converter',
        });
        const form = typed(typed(EMPTY_FORM, 'precision', '6'), 'workers', '8');

        expect(readOnlyReason(toolEntry.fields[0]!), 'a user field: nothing prevents the caller').toBeNull();
        expect(readOnlyReason(toolEntry.fields[1]!), 'a system field, the caller is not an administrator').toBe('adminOnly');
        expect(draftOf(toolEntry, form)).toStrictEqual({precision: {kind: 'text', text: '6'}});
    });

    it('writes nothing for a field without an edit, nor for an edit of a field the plugin does not declare', () => {
        expect(writeItems(PLUGIN, {})).toStrictEqual([]);
        expect(writeItems(PLUGIN, {ghost: {kind: 'clear'}})).toStrictEqual([]);
    });
});

// --- The answer ------------------------------------------------------------------------------------------------------

describe('refusalsByField and refusalKey — what a refused write says, field by field', () => {
    it('keeps the refused items that carry a code, by field', () => {
        const results: PluginSettingWriteResult[] = [
            {field_key: 'region', success: false, error_code: 'LOCKED_BY_ENV'},
            {field_key: 'nickname', success: true, error_code: null},
            {field_key: 'api_key', success: false, error_code: 'INVALID_VALUE'},
            {field_key: 'verbose', success: false, error_code: null},
            {field_key: 'retries', success: true, error_code: 'INVALID_VALUE'},
        ];

        expect(refusalsByField(frozen(results))).toStrictEqual({region: 'LOCKED_BY_ENV', api_key: 'INVALID_VALUE'});
        expect(refusalsByField([])).toStrictEqual({});
    });

    it.each([
        ['UNKNOWN_FIELD', 'pluginSettings.refusals.UNKNOWN_FIELD'],
        ['FORBIDDEN_SCOPE', 'pluginSettings.refusals.FORBIDDEN_SCOPE'],
        ['LOCKED_BY_ENV', 'pluginSettings.refusals.LOCKED_BY_ENV'],
        ['INVALID_VALUE', 'pluginSettings.refusals.INVALID_VALUE'],
    ])('%s reads as its own key', (code, key) => {
        expect(refusalKey(code)).toBe(key);
    });

    it.each(['A_CODE_FROM_A_NEWER_SERVER', 'invalid_value', ''])('a code this interface does not know (%j) reads as an invalid value', (code) => {
        expect(refusalKey(code)).toBe('pluginSettings.refusals.INVALID_VALUE');
    });

    it.each(['constructor', 'toString', 'hasOwnProperty', '__proto__'])('a code named like a property every object inherits (%j) reads as an invalid value too, never as what it inherits', (code) => {
        expect(refusalKey(code)).toBe('pluginSettings.refusals.INVALID_VALUE');
    });
});

// --- Keys every object inherits ----------------------------------------------------------------------------------------

describe('own — a lookup by field key reads what the map holds itself', () => {
    it('answers what the map holds, even a falsy value', () => {
        expect(own({region: 'eu'}, 'region')).toBe('eu');
        expect(own({verbose: false}, 'verbose')).toBe(false);
        expect(own({nickname: ''}, 'nickname')).toBe('');
        expect(own({region: 'eu'}, 'nickname')).toBeUndefined();
    });

    it.each(['constructor', 'toString', 'hasOwnProperty', 'valueOf', '__proto__'])('answers nothing for %j on a map that does not hold it, whatever every object inherits', (key) => {
        expect(own({}, key)).toBeUndefined();
        expect(own({region: 'eu'}, key)).toBeUndefined();
    });

    it('answers the map’s own value for a key every object also inherits', () => {
        expect(own({constructor: 'mine'}, 'constructor')).toBe('mine');
    });
});

describe('a field named constructor — a name every object inherits — is a field like any other', () => {
    const CONSTRUCTOR = field({key: 'constructor', label: 'Constructor', max_length: 5});
    const PLUGIN = entry([CONSTRUCTOR]);

    it('until the user types, it shows nothing and makes no edit, no problem and no item', () => {
        const draft = draftOf(PLUGIN, EMPTY_FORM);

        expect(shownText(CONSTRUCTOR, EMPTY_FORM)).toBe('');
        expect(shownChoice(CONSTRUCTOR, EMPTY_FORM)).toBeNull();
        expect(draft).toStrictEqual({});
        expect(draftProblems(PLUGIN, draft)).toStrictEqual({});
        expect(draftProblems(PLUGIN, {}), 'an empty draft').toStrictEqual({});
        expect(writeItems(PLUGIN, draft)).toStrictEqual([]);
        expect(writeItems(PLUGIN, {}), 'an empty draft').toStrictEqual([]);
    });

    // An object holding an own `constructor` is compared through its entries: `toStrictEqual` compares the two objects'
    // `constructor`, which here is a value of each, not their type.
    it('once typed, it makes a normal text edit, checked and written as any other', () => {
        const form = typed(EMPTY_FORM, 'constructor', 'abc');
        const draft = draftOf(PLUGIN, form);

        expect(shownText(CONSTRUCTOR, form)).toBe('abc');
        expect(Object.entries(draft)).toStrictEqual([['constructor', {kind: 'text', text: 'abc'}]]);
        expect(draftProblems(PLUGIN, draft), 'within its 5 characters').toStrictEqual({});
        expect(writeItems(PLUGIN, draft)).toStrictEqual([{family: 'asset', plugin_code: 'mockprov', field_key: 'constructor', scope: 'user', value: 'abc'}]);
        expect(Object.entries(draftProblems(PLUGIN, draftOf(PLUGIN, typed(EMPTY_FORM, 'constructor', 'abcdef')))), 'its declared rules apply').toStrictEqual([['constructor', {code: 'tooLong', limit: 5}]]);
    });

    it('a saved value of its own is cleared like any other', () => {
        const saved = entry([field({...CONSTRUCTOR, value: 'abc', default: 'xyz', is_set: true, source: 'db'})]);
        const form = cleared(EMPTY_FORM, 'constructor');

        expect(shownText(saved.fields[0], form), 'the default shows').toBe('xyz');
        expect(Object.entries(draftOf(saved, form))).toStrictEqual([['constructor', {kind: 'clear'}]]);
        expect(writeItems(saved, draftOf(saved, form))).toStrictEqual([{family: 'asset', plugin_code: 'mockprov', field_key: 'constructor', scope: 'user', clear: true}]);
        expect(draftOf(saved, restored(form, 'constructor')), 'restored: nothing to write').toStrictEqual({});
    });
});

// --- The catalogues --------------------------------------------------------------------------------------------------

describe('the family titles read in the four languages (X5-4b: tool joins asset, fx and brim)', () => {
    const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

    /** `catalogue.pluginSettings.families.<family>`, or undefined when any step is missing. */
    function familyTitle(catalogue: unknown, family: string): unknown {
        const families = ((catalogue as {pluginSettings?: {families?: Record<string, unknown>}}).pluginSettings ?? {}).families ?? {};
        return Object.hasOwn(families, family) ? families[family] : undefined;
    }

    it.each(Object.keys(CATALOGUES))('%s: every family of FAMILY_ORDER has a title, written under the key FAMILY_TITLE_KEYS names', (lang) => {
        for (const family of FAMILY_ORDER) {
            expect(FAMILY_TITLE_KEYS[family]).toBe(`pluginSettings.families.${family}`);
            const title = familyTitle(CATALOGUES[lang], family);
            expect(title, `${lang}: pluginSettings.families.${family}`).toBeTypeOf('string');
            expect((title as string).trim(), `${lang}: ${family} is not empty`).not.toBe('');
        }
    });

    it.each(Object.keys(CATALOGUES))('%s: the literal key pluginSettings.families.tool exists (the i18n audit reads whole literals)', (lang) => {
        const title = familyTitle(CATALOGUES[lang], 'tool');
        expect(title, `${lang}: pluginSettings.families.tool`).toBeTypeOf('string');
        expect((title as string).trim()).not.toBe('');
    });
});
