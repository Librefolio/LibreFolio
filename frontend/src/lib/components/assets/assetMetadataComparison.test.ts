/**
 * assetMetadataComparison — pure unit tests for the decision half of AssetModal's "Ask Provider".
 *
 * `compareMetadata` turns the provider's `patch_data` and a snapshot of the form into the ordered writes the modal
 * applies (actions), the rows of the comparison dialog (differences) and the distributions the provider does not
 * report (missingFields). Every branch is driven here with a fixed snapshot, fixed labels and a `manuallyChanged`
 * built from the set of fields the user edited while the request was in flight.
 */
import {describe, expect, it} from 'vitest';
import {IDENTIFIER_TYPES} from '$lib/utils/assetTypes';
import {compareMetadata, type ComparisonLabels, type ComparisonScope, type ComparisonSnapshot, type MetadataComparison} from './assetMetadataComparison';
import type {Distribution} from './assetPayload';

/** The caller's labels. `description` is not 'Description' on purpose: the row once showed that English literal in every language (X-R11). */
const LABELS: ComparisonLabels = {name: 'Name', type: 'Type', currency: 'Currency', description: 'Desc', sector: 'Sector', geographic: 'Geo'};

/** `manuallyChanged` for a request during which the user edited exactly `fields`. */
const editedDuring = (fields: string[]) => (field: string) => fields.includes(field);

/** An empty form, currency not picked by the user; each test sets only what it reads. */
function snapshot(overrides: Partial<ComparisonSnapshot> = {}): ComparisonSnapshot {
    return {
        identifiers: {},
        displayName: '',
        assetType: '',
        currency: '',
        currencyUserSet: false,
        shortDescription: '',
        descriptionFromPrefill: false,
        sectorDistribution: {},
        geographicDistribution: {},
        ...overrides,
    };
}

interface CompareOptions {
    /** The form when the comparison started (empty by default). */
    form?: Partial<ComparisonSnapshot>;
    scope?: ComparisonScope;
    /** The fields the user edited while the request was in flight (none by default). */
    touched?: string[];
}

function compare(patchData: Record<string, any>, {form = {}, scope = 'all', touched = []}: CompareOptions = {}): MetadataComparison {
    return compareMetadata(patchData, snapshot(form), scope, editedDuring(touched), LABELS);
}

/** The actions and dialog rows a comparison produced for one field. */
function forField(result: MetadataComparison, field: string) {
    return {actions: result.actions.filter((a) => a.field === field), differences: result.differences.filter((d) => d.field === field)};
}

const NOTHING = {actions: [], differences: []};

/** Freezes `value` and everything inside it, so an in-place write throws (ES modules run in strict mode). */
function deepFreeze<T>(value: T): T {
    if (value !== null && typeof value === 'object') {
        for (const nested of Object.values(value as Record<string, unknown>)) deepFreeze(nested);
        Object.freeze(value);
    }
    return value;
}

/** A provider answer with something for every field the comparison knows. */
const FULL_PATCH = {
    identifier_isin: 'IT0005557006',
    identifier_other: ['BTP-VALORE'],
    display_name: 'BTP Valore 2028',
    asset_type: 'BOND',
    currency: 'EUR',
    classification_params: {
        short_description: 'Italian government bond',
        sector_area: {distribution: {Government: 1}},
        geographic_area: {distribution: {ITA: 1}},
    },
};

describe('compareMetadata — scope', () => {
    it.each<[ComparisonScope, string[]]>([
        ['all', ['identifier_isin', 'identifier_other', 'display_name', 'asset_type', 'currency', 'short_description', 'sector_area', 'geographic_area']],
        ['identifiers', ['identifier_isin', 'identifier_other']],
        ['sector', ['sector_area']],
        ['geographic', ['geographic_area']],
    ])('scope %s compares only its own fields', (scope, fields) => {
        const result = compare(FULL_PATCH, {scope});
        expect(result.actions.map((a) => a.field)).toEqual(fields);
        expect(result.differences).toEqual([]);
        expect(result.missingFields).toEqual([]);
    });

    it.each<[ComparisonScope, string[]]>([
        ['all', ['Sector', 'Geo']],
        ['identifiers', []],
        ['sector', ['Sector']],
        ['geographic', ['Geo']],
    ])('scope %s reports as missing only its own distributions', (scope, missing) => {
        expect(compare({display_name: 'BTP Valore 2028'}, {scope}).missingFields).toEqual(missing);
    });
});

describe('compareMetadata — order', () => {
    it('emits the actions in field order: identifiers (enum order), OTHER, name, type, currency, description, sector, geographic', () => {
        const result = compareMetadata(
            {
                // Listed backwards on purpose: the order is the comparison's, not the payload's.
                classification_params: {geographic_area: {distribution: {ITA: 1}}, sector_area: {Government: '1'}, short_description: 'Italian government bond'},
                currency: 'USD',
                asset_type: 'ETF',
                display_name: 'BTP Valore',
                identifier_other: ['BTP-VALORE'],
                identifier_uuid: 'uuid-1',
                identifier_figi: 'BBG000000001',
                identifier_sedol: 'B0YBKJ7',
                identifier_cusip: '037833100',
                identifier_ticker: 'BTPV',
                identifier_isin: 'IT0005557006',
            },
            snapshot({
                identifiers: {ISIN: 'IT0005557006', TICKER: 'btpv'},
                displayName: 'btp valore',
                assetType: 'ETF_BOND',
                currency: 'EUR',
                currencyUserSet: false,
                shortDescription: 'BTP VALORE 2028',
                descriptionFromPrefill: true,
                sectorDistribution: {},
                geographicDistribution: {ITA: 1},
            }),
            'all',
            editedDuring([]),
            LABELS,
        );
        expect(result.actions).toEqual([
            {kind: 'agree', field: 'identifier_isin'},
            {kind: 'fill', field: 'identifier_ticker', value: 'BTPV'},
            {kind: 'fill', field: 'identifier_cusip', value: '037833100'},
            {kind: 'fill', field: 'identifier_sedol', value: 'B0YBKJ7'},
            {kind: 'fill', field: 'identifier_figi', value: 'BBG000000001'},
            {kind: 'fill', field: 'identifier_uuid', value: 'uuid-1'},
            {kind: 'mergeOther', field: 'identifier_other', values: ['BTP-VALORE']},
            {kind: 'fill', field: 'display_name', value: 'BTP Valore'},
            {kind: 'agree', field: 'asset_type'},
            {kind: 'fill', field: 'currency', value: 'USD'},
            {kind: 'mergeDescription', field: 'short_description', value: 'Italian government bond\n\nBTP VALORE 2028'},
            {kind: 'fillDistribution', field: 'sector_area', value: {Government: 1}},
            {kind: 'agree', field: 'geographic_area'},
        ]);
        expect(result.differences).toEqual([]);
        expect(result.missingFields).toEqual([]);
    });

    it('lists the dialog rows in the same field order, each with its label', () => {
        const result = compareMetadata(
            {
                classification_params: {geographic_area: {distribution: {USA: 1}}, sector_area: {distribution: {Technology: 1}}, short_description: 'Apple designs consumer electronics.'},
                currency: 'USD',
                asset_type: 'STOCK',
                display_name: 'Apple Inc.',
                identifier_other: ['APC.DE'],
                identifier_uuid: 'uuid-new',
                identifier_figi: 'BBG-new',
                identifier_sedol: 'SEDOL-new',
                identifier_cusip: 'CUSIP-new',
                identifier_ticker: 'AAPL',
                identifier_isin: 'US0378331005',
            },
            snapshot({
                identifiers: {ISIN: 'US-old', TICKER: 'AAPL.MI', CUSIP: 'CUSIP-old', SEDOL: 'SEDOL-old', FIGI: 'BBG-old', UUID: 'uuid-old'},
                displayName: 'Apple',
                assetType: 'ETF',
                currency: 'EUR',
                currencyUserSet: true,
                shortDescription: 'My own notes',
                descriptionFromPrefill: false,
                sectorDistribution: {Health: 1},
                geographicDistribution: {ITA: 1},
            }),
            'all',
            editedDuring([]),
            LABELS,
        );
        const stringRow = (field: string, label: string, currentValue: string, providerValue: string) => ({field, label, type: 'string', currentValue, providerValue, selected: true});
        expect(result.differences).toEqual([
            stringRow('identifier_isin', 'ISIN', 'US-old', 'US0378331005'),
            stringRow('identifier_ticker', 'TICKER', 'AAPL.MI', 'AAPL'),
            stringRow('identifier_cusip', 'CUSIP', 'CUSIP-old', 'CUSIP-new'),
            stringRow('identifier_sedol', 'SEDOL', 'SEDOL-old', 'SEDOL-new'),
            stringRow('identifier_figi', 'FIGI', 'BBG-old', 'BBG-new'),
            stringRow('identifier_uuid', 'UUID', 'uuid-old', 'uuid-new'),
            stringRow('display_name', 'Name', 'Apple', 'Apple Inc.'),
            stringRow('asset_type', 'Type', 'ETF', 'STOCK'),
            stringRow('currency', 'Currency', 'EUR', 'USD'),
            stringRow('short_description', LABELS.description, 'My own notes', 'Apple designs consumer electronics.'),
            {field: 'sector_area', label: 'Sector', type: 'distribution', currentValue: {Health: 1}, providerValue: {Technology: 1}, selected: true},
            {field: 'geographic_area', label: 'Geo', type: 'distribution', currentValue: {ITA: 1}, providerValue: {USA: 1}, selected: true},
        ]);
        // OTHER never makes a dialog row: it is merged.
        expect(result.actions).toEqual([{kind: 'mergeOther', field: 'identifier_other', values: ['APC.DE']}]);
        expect(result.missingFields).toEqual([]);
    });
});

describe('compareMetadata — a string field', () => {
    it.each<[string, unknown]>([
        ['empty', ''],
        ['null', null],
        ['undefined', undefined],
    ])('is left alone when the provider value is %s', (_label, providerValue) => {
        expect(forField(compare({display_name: providerValue}), 'display_name')).toEqual(NOTHING);
        expect(forField(compare({display_name: providerValue}, {form: {displayName: 'Apple'}}), 'display_name')).toEqual(NOTHING);
    });

    it('fills an empty field the user has not touched', () => {
        expect(forField(compare({display_name: 'Apple Inc.'}), 'display_name')).toEqual({actions: [{kind: 'fill', field: 'display_name', value: 'Apple Inc.'}], differences: []});
    });

    it('asks about an empty field the user touched (they may have cleared it on purpose)', () => {
        expect(forField(compare({display_name: 'Apple Inc.'}, {touched: ['display_name']}), 'display_name')).toEqual({
            actions: [],
            differences: [{field: 'display_name', label: 'Name', type: 'string', currentValue: '', providerValue: 'Apple Inc.', selected: true}],
        });
    });

    it('agrees when the values are equal and the field is untouched', () => {
        expect(forField(compare({display_name: 'Apple Inc.'}, {form: {displayName: 'Apple Inc.'}}), 'display_name')).toEqual({actions: [{kind: 'agree', field: 'display_name'}], differences: []});
    });

    it('says nothing when the values are equal and the field was touched', () => {
        expect(forField(compare({display_name: 'Apple Inc.'}, {form: {displayName: 'Apple Inc.'}, touched: ['display_name']}), 'display_name')).toEqual(NOTHING);
    });

    it('fills over a difference of case and surrounding blanks only (title noise) when untouched', () => {
        expect(forField(compare({display_name: 'T-Bond 2030'}, {form: {displayName: '  t-bond 2030 '}}), 'display_name')).toEqual({actions: [{kind: 'fill', field: 'display_name', value: 'T-Bond 2030'}], differences: []});
    });

    it('asks about a case-only difference the user touched', () => {
        expect(forField(compare({display_name: 'T-Bond 2030'}, {form: {displayName: 't-bond 2030'}, touched: ['display_name']}), 'display_name')).toEqual({
            actions: [],
            differences: [{field: 'display_name', label: 'Name', type: 'string', currentValue: 't-bond 2030', providerValue: 'T-Bond 2030', selected: true}],
        });
    });

    it('asks about a real difference, with the field label (the currency exception does not apply to other fields)', () => {
        // The default snapshot has currencyUserSet: false, which would fill a currency; here it must change nothing.
        expect(forField(compare({display_name: 'Apple Inc.'}, {form: {displayName: 'Apple'}}), 'display_name')).toEqual({
            actions: [],
            differences: [{field: 'display_name', label: 'Name', type: 'string', currentValue: 'Apple', providerValue: 'Apple Inc.', selected: true}],
        });
    });
});

describe('compareMetadata — the asset type', () => {
    it('agrees when the provider names only the family of the stored subtype, untouched', () => {
        expect(forField(compare({asset_type: 'ETF'}, {form: {assetType: 'ETF_STOCK'}}), 'asset_type')).toEqual({actions: [{kind: 'agree', field: 'asset_type'}], differences: []});
    });

    it('says nothing about a family-only proposal on a touched type', () => {
        expect(forField(compare({asset_type: 'ETF'}, {form: {assetType: 'ETF_STOCK'}, touched: ['asset_type']}), 'asset_type')).toEqual(NOTHING);
    });

    it('still offers a refinement of the family (ETF → ETF_STOCK)', () => {
        expect(forField(compare({asset_type: 'ETF_STOCK'}, {form: {assetType: 'ETF'}}), 'asset_type')).toEqual({
            actions: [],
            differences: [{field: 'asset_type', label: 'Type', type: 'string', currentValue: 'ETF', providerValue: 'ETF_STOCK', selected: true}],
        });
    });

    it('asks about a different type', () => {
        expect(forField(compare({asset_type: 'BOND'}, {form: {assetType: 'STOCK'}}), 'asset_type').differences).toEqual([{field: 'asset_type', label: 'Type', type: 'string', currentValue: 'STOCK', providerValue: 'BOND', selected: true}]);
    });

    it('applies the family rule to the asset type only', () => {
        expect(forField(compare({display_name: 'ETF'}, {form: {displayName: 'ETF_STOCK'}}), 'display_name').differences).toEqual([{field: 'display_name', label: 'Name', type: 'string', currentValue: 'ETF_STOCK', providerValue: 'ETF', selected: true}]);
    });
});

describe('compareMetadata — the currency', () => {
    it('fills over a default the user never picked', () => {
        expect(forField(compare({currency: 'USD'}, {form: {currency: 'EUR', currencyUserSet: false}}), 'currency')).toEqual({actions: [{kind: 'fill', field: 'currency', value: 'USD'}], differences: []});
    });

    it('asks when the user picked the currency', () => {
        expect(forField(compare({currency: 'USD'}, {form: {currency: 'EUR', currencyUserSet: true}}), 'currency')).toEqual({
            actions: [],
            differences: [{field: 'currency', label: 'Currency', type: 'string', currentValue: 'EUR', providerValue: 'USD', selected: true}],
        });
    });

    it('asks when the user touched it during the request, picked or not', () => {
        expect(forField(compare({currency: 'USD'}, {form: {currency: 'EUR', currencyUserSet: false}, touched: ['currency']}), 'currency').differences).toEqual([{field: 'currency', label: 'Currency', type: 'string', currentValue: 'EUR', providerValue: 'USD', selected: true}]);
    });
});

describe('compareMetadata — identifiers', () => {
    const TYPED = IDENTIFIER_TYPES.filter((type) => type !== 'OTHER');

    it('walks the identifier types in enum order, whatever the payload order', () => {
        const patchData = Object.fromEntries([...TYPED].reverse().map((type) => [`identifier_${type.toLowerCase()}`, `${type}-value`]));
        const result = compare(patchData, {scope: 'identifiers', touched: ['identifier_other']});
        expect(result.actions).toEqual(TYPED.map((type) => ({kind: 'fill', field: `identifier_${type.toLowerCase()}`, value: `${type}-value`})));
    });

    it('skips OTHER and every identifier the provider leaves empty', () => {
        const result = compare({identifier_isin: '', identifier_ticker: null, identifier_cusip: undefined, identifier_figi: 'BBG000B9XRY4', identifier_other: 'APC.DE'}, {scope: 'identifiers'});
        expect(result.actions).toEqual([
            {kind: 'fill', field: 'identifier_figi', value: 'BBG000B9XRY4'},
            {kind: 'mergeOther', field: 'identifier_other', values: 'APC.DE'},
        ]);
        expect(result.differences).toEqual([]);
    });

    it('reads the current value from the snapshot and labels the row with the type', () => {
        expect(compare({identifier_isin: 'US0378331005'}, {scope: 'identifiers', form: {identifiers: {ISIN: 'US-old'}}}).differences).toEqual([{field: 'identifier_isin', label: 'ISIN', type: 'string', currentValue: 'US-old', providerValue: 'US0378331005', selected: true}]);
    });

    it('reads a type missing from the snapshot as empty', () => {
        const result = compare({identifier_isin: 'US0378331005'}, {scope: 'identifiers', form: {identifiers: {TICKER: 'AAPL'}}, touched: ['identifier_isin']});
        expect(forField(result, 'identifier_isin')).toEqual({
            actions: [],
            differences: [{field: 'identifier_isin', label: 'ISIN', type: 'string', currentValue: '', providerValue: 'US0378331005', selected: true}],
        });
    });

    it('agrees with an identifier the form already has, and fills one with a case-only difference', () => {
        const result = compare({identifier_isin: 'US0378331005', identifier_ticker: 'AAPL'}, {scope: 'identifiers', form: {identifiers: {ISIN: 'US0378331005', TICKER: 'aapl'}}, touched: ['identifier_other']});
        expect(result.actions).toEqual([
            {kind: 'agree', field: 'identifier_isin'},
            {kind: 'fill', field: 'identifier_ticker', value: 'AAPL'},
        ]);
    });
});

describe('compareMetadata — OTHER identifiers', () => {
    it('merges them when the user has not edited them, handing over the payload value as is', () => {
        const others = ['APC.DE', 'AAPL.MI'];
        const actions = compare({identifier_other: others}, {scope: 'identifiers'}).actions;
        expect(actions).toEqual([{kind: 'mergeOther', field: 'identifier_other', values: others}]);
        const [merge] = actions;
        expect(merge.kind === 'mergeOther' && merge.values).toBe(others);
    });

    it('still emits the merge when the provider sends none (the modal then finds nothing to add)', () => {
        expect(compare({}, {scope: 'identifiers'}).actions).toStrictEqual([{kind: 'mergeOther', field: 'identifier_other', values: undefined}]);
    });

    it('never merges into OTHER identifiers the user edited', () => {
        expect(compare({identifier_other: ['APC.DE']}, {scope: 'identifiers', touched: ['identifier_other']})).toEqual({actions: [], differences: [], missingFields: []});
    });
});

describe('compareMetadata — the description', () => {
    const provider = (shortDescription: unknown) => ({classification_params: {short_description: shortDescription}});

    it('is compared only on a full comparison carrying a provider description', () => {
        expect(forField(compare(provider('Apple designs consumer electronics.'), {scope: 'sector'}), 'short_description')).toEqual(NOTHING);
        expect(forField(compare(provider('Apple designs consumer electronics.'), {scope: 'identifiers'}), 'short_description')).toEqual(NOTHING);
        expect(forField(compare(provider('')), 'short_description')).toEqual(NOTHING);
        expect(forField(compare({classification_params: {}}), 'short_description')).toEqual(NOTHING);
        expect(forField(compare({classification_params: null}), 'short_description')).toEqual(NOTHING);
        expect(forField(compare({}), 'short_description')).toEqual(NOTHING);
    });

    it('merges the provider description over a broker-import prefill: provider first, then the trimmed prefill', () => {
        const result = compare(provider('Apple designs consumer electronics.'), {form: {shortDescription: '  APPLE INC / AAPL  ', descriptionFromPrefill: true}});
        expect(forField(result, 'short_description')).toEqual({
            actions: [{kind: 'mergeDescription', field: 'short_description', value: 'Apple designs consumer electronics.\n\nAPPLE INC / AAPL'}],
            differences: [],
        });
    });

    it('keeps the provider description alone when it already contains the prefill', () => {
        const result = compare(provider('Apple Inc. (AAPL) designs consumer electronics.'), {form: {shortDescription: ' Apple Inc. (AAPL) ', descriptionFromPrefill: true}});
        expect(forField(result, 'short_description').actions).toEqual([{kind: 'mergeDescription', field: 'short_description', value: 'Apple Inc. (AAPL) designs consumer electronics.'}]);
    });

    it('agrees with a prefill equal to the provider description (no merge)', () => {
        const result = compare(provider('Apple designs consumer electronics.'), {form: {shortDescription: 'Apple designs consumer electronics.', descriptionFromPrefill: true}});
        expect(forField(result, 'short_description')).toEqual({actions: [{kind: 'agree', field: 'short_description'}], differences: []});
    });

    it('fills, without merging, a prefill that differs from the provider only by surrounding blanks', () => {
        const result = compare(provider('Apple designs consumer electronics.'), {form: {shortDescription: '  Apple designs consumer electronics.  ', descriptionFromPrefill: true}});
        expect(forField(result, 'short_description')).toEqual({actions: [{kind: 'fill', field: 'short_description', value: 'Apple designs consumer electronics.'}], differences: []});
    });

    it('fills an empty prefilled description through the plain compare', () => {
        const result = compare(provider('Apple designs consumer electronics.'), {form: {shortDescription: '', descriptionFromPrefill: true}});
        expect(forField(result, 'short_description')).toEqual({actions: [{kind: 'fill', field: 'short_description', value: 'Apple designs consumer electronics.'}], differences: []});
    });

    it("asks about a prefill the user touched, under the caller's label like every other row (X-R11)", () => {
        const result = compare(provider('Apple designs consumer electronics.'), {form: {shortDescription: 'APPLE INC / AAPL', descriptionFromPrefill: true}, touched: ['short_description']});
        expect(forField(result, 'short_description')).toEqual({
            actions: [],
            differences: [{field: 'short_description', label: LABELS.description, type: 'string', currentValue: 'APPLE INC / AAPL', providerValue: 'Apple designs consumer electronics.', selected: true}],
        });
    });

    it('compares a description the user typed (no prefill) like any other field', () => {
        const typed = (shortDescription: string) => forField(compare(provider('Apple designs consumer electronics.'), {form: {shortDescription, descriptionFromPrefill: false}}), 'short_description');
        expect(typed('My own notes')).toEqual({
            actions: [],
            differences: [{field: 'short_description', label: LABELS.description, type: 'string', currentValue: 'My own notes', providerValue: 'Apple designs consumer electronics.', selected: true}],
        });
        expect(typed('')).toEqual({actions: [{kind: 'fill', field: 'short_description', value: 'Apple designs consumer electronics.'}], differences: []});
        expect(typed('Apple designs consumer electronics.')).toEqual({actions: [{kind: 'agree', field: 'short_description'}], differences: []});
    });
});

describe.each<[string, 'sector_area' | 'geographic_area', 'sector' | 'geographic', string]>([
    ['sector', 'sector_area', 'sector', 'Sector'],
    ['geographic', 'geographic_area', 'geographic', 'Geo'],
])('compareMetadata — the %s distribution', (_name, field, scope, label) => {
    const provider = (area: unknown) => ({classification_params: {[field]: area}});
    const form = (distribution: Distribution): Partial<ComparisonSnapshot> => (field === 'sector_area' ? {sectorDistribution: distribution} : {geographicDistribution: distribution});

    it('fills an empty, untouched distribution with the normalized provider weights', () => {
        expect(compare(provider({distribution: {A: '0.25', B: 0.75}}), {scope})).toEqual({actions: [{kind: 'fillDistribution', field, value: {A: 0.25, B: 0.75}}], differences: [], missingFields: []});
    });

    it('reads a bare weight map as well as a {distribution} wrapper', () => {
        expect(compare(provider({A: '0.5', B: '0.5'}), {scope}).actions).toEqual([{kind: 'fillDistribution', field, value: {A: 0.5, B: 0.5}}]);
    });

    it('asks when the form holds a different distribution', () => {
        expect(compare(provider({distribution: {A: 1}}), {scope, form: form({B: 1})})).toEqual({
            actions: [],
            differences: [{field, label, type: 'distribution', currentValue: {B: 1}, providerValue: {A: 1}, selected: true}],
            missingFields: [],
        });
    });

    it('asks when the user emptied the distribution during the request', () => {
        expect(compare(provider({distribution: {A: 1}}), {scope, touched: [field]}).differences).toEqual([{field, label, type: 'distribution', currentValue: {}, providerValue: {A: 1}, selected: true}]);
    });

    it('agrees with the same weights, in any key order and given as strings', () => {
        expect(compare(provider({distribution: {B: '0.6', A: 0.4}}), {scope, form: form({A: 0.4, B: 0.6})})).toEqual({actions: [{kind: 'agree', field}], differences: [], missingFields: []});
    });

    it('says nothing about the same weights on a touched distribution', () => {
        expect(compare(provider({distribution: {A: 1}}), {scope, form: form({A: 1}), touched: [field]})).toEqual({actions: [], differences: [], missingFields: []});
    });

    it('reports the distribution as missing when the provider has none', () => {
        const answers = [{}, {classification_params: null}, {classification_params: {}}, provider(null)];
        expect(answers.map((patchData) => compare(patchData, {scope}))).toEqual(answers.map(() => ({actions: [], differences: [], missingFields: [label]})));
    });

    it('throws on a weight that is not a number', () => {
        expect(() => compare(provider({distribution: {A: 'abc'}}), {scope})).toThrow('Invalid distribution weight.');
    });
});

describe('compareMetadata — purity', () => {
    it('never writes into the payload or the snapshot, and fills with a copy of the provider weights', () => {
        // Built fresh on each call, so the frozen copy shares nothing with the one it is compared against.
        const buildPatch = () => ({
            identifier_isin: 'IT0005557006',
            identifier_ticker: 'BTPV',
            identifier_other: ['BTP-VALORE'],
            display_name: 'BTP Valore 2028',
            asset_type: 'BOND',
            currency: 'EUR',
            classification_params: {
                short_description: 'Italian government bond',
                sector_area: {distribution: {Government: 1}},
                geographic_area: {distribution: {ITA: 1}},
            },
        });
        const buildForm = () => snapshot({identifiers: {ISIN: 'IT0005556990'}, displayName: 'btp valore 2028', shortDescription: 'BTP VALORE', descriptionFromPrefill: true, geographicDistribution: {ITA: 0.5, FRA: 0.5}});
        const patchData = deepFreeze(buildPatch());
        const form = deepFreeze(buildForm());

        const result = compareMetadata(patchData, form, 'all', editedDuring([]), LABELS);

        // Writes of every kind were decided, plus two dialog rows — none of them into the inputs.
        expect(result.actions.map((a) => a.kind)).toEqual(['fill', 'mergeOther', 'fill', 'fill', 'fill', 'mergeDescription', 'fillDistribution']);
        expect(result.differences.map((d) => d.field)).toEqual(['identifier_isin', 'geographic_area']);
        expect(patchData).toEqual(buildPatch());
        expect(form).toEqual(buildForm());
        // The filled distribution is a new object: the form never aliases the provider's answer.
        const fill = result.actions.find((a) => a.kind === 'fillDistribution');
        expect(fill).toEqual({kind: 'fillDistribution', field: 'sector_area', value: {Government: 1}});
        expect(fill?.kind === 'fillDistribution' && fill.value).not.toBe(patchData.classification_params.sector_area.distribution);
    });
});
