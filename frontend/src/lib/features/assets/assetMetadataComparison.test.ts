/**
 * assetMetadataComparison — pure unit tests for the decision half of AssetModal's "Ask Provider".
 *
 * `compareMetadata` turns the provider's `patch_data` and a snapshot of the form into the ordered writes the modal
 * applies (actions) and the rows of the comparison dialog (differences). Every branch is driven here with a fixed snapshot, fixed labels and a `manuallyChanged`
 * built from the set of fields the user edited while the request was in flight.
 *
 * The quote base (Z-32 d, the last blocks): on a full comparison only, right after the currency row, one row when the
 * form's quote base differs from the proposal — the plugin's suggestion for the line (the sixth argument), else the
 * default of the type the comparison reads (the provider's, unless it is the form's own or only its family). Never an
 * action, always checked, noted by the caller's label for its source: `LABELS.quoteBaseNote` is a fake that spells the
 * source out, so a case sees which note was asked for. The snapshot holds a quote base of 1 by default — the blank
 * form's — so an answer with no type and no suggestion changes nothing on an empty form. RED until the row exists.
 *
 * The description, the sectors and the countries are the profile's (plan 68, E9): a provider's `classification_params`
 * is not compared any more, and there is no «missing distribution» to report.
 */
import {describe, expect, it, vi} from 'vitest';
import {IDENTIFIER_TYPES} from '$lib/utils/assetTypes';
import {compareMetadata, type ComparisonLabels, type ComparisonScope, type ComparisonSnapshot, type MetadataComparison} from './assetMetadataComparison';
import type {QuoteBaseSource, QuoteBaseSuggestion} from './assetFormState';

/** The note the caller writes for a quote base proposal — a fake that spells its source out, so a case sees which note was asked for. */
function noteOf(source: QuoteBaseSource): string {
    return source.kind === 'suggestion' ? `note(suggestion ${source.quantity} ${source.quoteCurrency ?? '—'})` : `note(typeDefault ${source.assetType} ${source.quantity})`;
}

/** The caller's labels. */
const LABELS: ComparisonLabels = {name: 'Name', type: 'Type', currency: 'Currency', icon: 'Icon', quoteBase: 'QuoteBase', quoteBaseNote: noteOf};

/** `manuallyChanged` for a request during which the user edited exactly `fields`. */
const editedDuring = (fields: string[]) => (field: string) => fields.includes(field);

/** An empty form, currency not picked by the user, the blank form's quote base of 1; each test sets only what it reads. */
function snapshot(overrides: Partial<ComparisonSnapshot> = {}): ComparisonSnapshot {
    return {
        identifiers: {},
        displayName: '',
        assetType: '',
        currency: '',
        currencyUserSet: false,
        iconUrl: '',
        quoteBaseQuantity: 1,
        ...overrides,
    };
}

interface CompareOptions {
    /** The form when the comparison started (empty by default). */
    form?: Partial<ComparisonSnapshot>;
    scope?: ComparisonScope;
    /** The fields the user edited while the request was in flight (none by default). */
    touched?: string[];
    /** The plugin's quote base suggestion for the line (none by default). */
    suggestion?: QuoteBaseSuggestion | null;
}

function compare(patchData: Record<string, any>, {form = {}, scope = 'all', touched = [], suggestion = null}: CompareOptions = {}): MetadataComparison {
    return compareMetadata(patchData, snapshot(form), scope, editedDuring(touched), LABELS, suggestion);
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
        ['all', ['identifier_isin', 'identifier_other', 'display_name', 'asset_type', 'currency']],
        ['identifiers', ['identifier_isin', 'identifier_other']],
    ])('scope %s compares only its own fields', (scope, fields) => {
        // A BOND at 100: the full answer agrees on the quote base too, so no row is left to blur the scope (Z-32 d).
        const result = compare(FULL_PATCH, {scope, form: {quoteBaseQuantity: 100}});
        expect(result.actions.map((a) => a.field)).toEqual(fields);
        expect(result.differences).toEqual([]);
    });
});

describe('compareMetadata — the classification is the profile’s (plan 68, E9)', () => {
    it('never reads a provider’s description, sectors or countries, and reports nothing missing', () => {
        // FULL_PATCH carries all three; a form holding other values must not get a row for them either
        const result = compare(FULL_PATCH, {form: {quoteBaseQuantity: 100}});
        const classification = ['short_description', 'sector_area', 'geographic_area'];
        expect(result.actions.filter((a) => classification.includes(a.field))).toEqual([]);
        expect(result.differences.filter((d) => classification.includes(d.field))).toEqual([]);
        expect(Object.keys(result).sort()).toEqual(['actions', 'differences']);
    });
});

describe('compareMetadata — order', () => {
    it('emits the actions in field order: identifiers (enum order), OTHER, name, type, currency', () => {
        const result = compareMetadata(
            {
                // Listed backwards on purpose: the order is the comparison's, not the payload's.
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
        ]);
        expect(result.differences).toEqual([]);
    });

    it('lists the dialog rows in the same field order, each with its label', () => {
        const result = compareMetadata(
            {
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
        ]);
        // OTHER never makes a dialog row: it is merged.
        expect(result.actions).toEqual([{kind: 'mergeOther', field: 'identifier_other', values: ['APC.DE']}]);
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

// Project 76, P3 (the consultant's answer): the provider's logo is a field like the others, for every provider. An empty
// icon is filled; a different one is a choice, never overwritten in silence — not even when only the case differs, since
// a URL's path is case-sensitive.
describe('compareMetadata — the icon', () => {
    const LOGO = 'https://coin-images.coingecko.com/coins/images/1/large/bitcoin.png';

    it('fills an empty icon', () => {
        expect(forField(compare({icon_url: LOGO}), 'icon_url')).toEqual({actions: [{kind: 'fill', field: 'icon_url', value: LOGO}], differences: []});
    });

    it('agrees with the same icon', () => {
        expect(forField(compare({icon_url: LOGO}, {form: {iconUrl: LOGO}}), 'icon_url')).toEqual({actions: [{kind: 'agree', field: 'icon_url'}], differences: []});
    });

    it.each<[string, string]>([
        ['another icon', 'https://example.org/my-icon.png'],
        ['the same address in another case', LOGO.toUpperCase()],
    ])('asks about %s, with its label', (_label, current) => {
        expect(forField(compare({icon_url: LOGO}, {form: {iconUrl: current}}), 'icon_url')).toEqual({
            actions: [],
            differences: [{field: 'icon_url', label: 'Icon', type: 'string', currentValue: current, providerValue: LOGO, selected: true}],
        });
    });

    it('is compared in the scope «all» only', () => {
        expect(forField(compare({icon_url: LOGO}, {scope: 'identifiers'}), 'icon_url')).toEqual(NOTHING);
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
        expect(compare({identifier_other: ['APC.DE']}, {scope: 'identifiers', touched: ['identifier_other']})).toEqual({actions: [], differences: []});
    });
});

describe('compareMetadata — purity', () => {
    it('never writes into the payload, the snapshot or the quote base suggestion', () => {
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
        const buildForm = () => snapshot({identifiers: {ISIN: 'IT0005556990'}, displayName: 'btp valore 2028'});
        // The third input since Z-32 d: the plugin's suggestion for the line. The form holds the blank 1, so it makes a row.
        const buildSuggestion = () => ({quantity: 100, quote_currency: 'EUR'});
        const patchData = deepFreeze(buildPatch());
        const form = deepFreeze(buildForm());
        const suggestion = deepFreeze(buildSuggestion());

        const result = compareMetadata(patchData, form, 'all', editedDuring([]), LABELS, suggestion);

        // Writes of every kind were decided, plus two dialog rows — none of them into the inputs.
        expect(result.actions.map((a) => a.kind)).toEqual(['fill', 'mergeOther', 'fill', 'fill', 'fill']);
        expect(result.differences.map((d) => d.field)).toEqual(['identifier_isin', 'quote_base_quantity']);
        expect(patchData).toEqual(buildPatch());
        expect(form).toEqual(buildForm());
        expect(suggestion).toEqual(buildSuggestion());
    });
});

// =========================================================================
// The quote base (Z-32 d) — see the header. RED: today no comparison proposes a quote base at all.
// =========================================================================

/** A proposal from the plugin's suggestion, as `proposeQuoteBase` builds it. */
const suggested = (quantity: number, quoteCurrency: string | null = null): QuoteBaseSource => ({kind: 'suggestion', quantity, quoteCurrency});
/** A proposal from the default of `assetType`, as `proposeQuoteBase` builds it. */
const typeDefault = (assetType: string, quantity: number): QuoteBaseSource => ({kind: 'typeDefault', assetType, quantity});

/** The quote base row of a proposal: both values as text, always checked, the caller's note for its source, and the source itself. */
function quoteBaseRow(current: number, source: QuoteBaseSource) {
    return {field: 'quote_base_quantity', label: LABELS.quoteBase, type: 'string', currentValue: String(current), providerValue: String(source.quantity), selected: true, note: LABELS.quoteBaseNote(source), quoteBaseSource: source};
}

/** A line quoted in pence: the plugin suggests one price per 100 shares, in GBp (Yahoo's VOD.L). */
const PENCE: QuoteBaseSuggestion = {quantity: 100, quote_currency: 'GBp'};

describe('compareMetadata — the quote base (Z-32 d)', () => {
    it.each<{label: string; form: Partial<ComparisonSnapshot>; suggestion: QuoteBaseSuggestion | null}>([
        {label: 'the suggestion', form: {assetType: 'STOCK', quoteBaseQuantity: 100}, suggestion: PENCE},
        {label: 'a STOCK’s default, 1', form: {assetType: 'STOCK', quoteBaseQuantity: 1}, suggestion: null},
        {label: 'a BOND’s default, 100', form: {assetType: 'BOND', quoteBaseQuantity: 100}, suggestion: null},
    ])('says nothing when the form already holds $label: no action, no row (guard)', ({form, suggestion}) => {
        expect(forField(compare({}, {form, suggestion}), 'quote_base_quantity')).toEqual(NOTHING);
    });

    it('proposes the plugin’s suggestion as a checked row, noted as a suggestion', () => {
        expect(forField(compare({}, {form: {assetType: 'STOCK', quoteBaseQuantity: 1}, suggestion: PENCE}), 'quote_base_quantity')).toEqual({actions: [], differences: [quoteBaseRow(1, suggested(100, 'GBp'))]});
    });

    it('reads a suggestion without its quote currency as quoteCurrency null', () => {
        expect(compare({}, {form: {assetType: 'STOCK', quoteBaseQuantity: 1}, suggestion: {quantity: 10}}).differences).toEqual([quoteBaseRow(1, suggested(10))]);
    });

    it('lets a suggestion win over the type: 1 for a BOND stored at 100', () => {
        expect(compare({}, {form: {assetType: 'BOND', quoteBaseQuantity: 100}, suggestion: {quantity: 1}}).differences).toEqual([quoteBaseRow(100, suggested(1))]);
    });

    it('without a suggestion, proposes the type’s default: 100 for a BOND, with the note of a BOND’s default', () => {
        expect(compare({}, {form: {assetType: 'BOND', quoteBaseQuantity: 1}}).differences).toEqual([quoteBaseRow(1, typeDefault('BOND', 100))]);
    });

    it('without a suggestion, proposes 1 for any other type — a row from the default alone starts checked too (Q-Q5 a)', () => {
        // An answer with no type and no suggestion at all: the form's own type is read.
        expect(compare({}, {form: {assetType: 'STOCK', quoteBaseQuantity: 100}}).differences).toEqual([quoteBaseRow(100, typeDefault('STOCK', 1))]);
    });

    it('counts an invalid suggestion as none: the type’s default (the ladder of proposeQuoteBase)', () => {
        expect(compare({}, {form: {assetType: 'STOCK', quoteBaseQuantity: 100}, suggestion: {quantity: 0}}).differences).toEqual([quoteBaseRow(100, typeDefault('STOCK', 1))]);
    });

    it.each<{label: string; form: Partial<ComparisonSnapshot> & {quoteBaseQuantity: number}; patch: Record<string, any>; source: QuoteBaseSource}>([
        {label: 'a BOND for a STOCK', form: {assetType: 'STOCK', quoteBaseQuantity: 1}, patch: {asset_type: 'BOND'}, source: typeDefault('BOND', 100)},
        {label: 'a BOND for an empty type, which it fills', form: {assetType: '', quoteBaseQuantity: 1}, patch: {asset_type: 'BOND'}, source: typeDefault('BOND', 100)},
        {label: 'an ETF for a BOND', form: {assetType: 'BOND', quoteBaseQuantity: 100}, patch: {asset_type: 'ETF'}, source: typeDefault('ETF', 1)},
    ])('reads the default of the type the provider proposes — $label', ({form, patch, source}) => {
        expect(forField(compare(patch, {form}), 'quote_base_quantity')).toEqual({actions: [], differences: [quoteBaseRow(form.quoteBaseQuantity, source)]});
    });

    it('keeps the form’s type when the provider names only its family: the source names ETF_STOCK, not ETF', () => {
        // Both default to 1: only the source tells which type the ladder read.
        expect(forField(compare({asset_type: 'ETF'}, {form: {assetType: 'ETF_STOCK', quoteBaseQuantity: 100}}), 'quote_base_quantity').differences).toEqual([quoteBaseRow(100, typeDefault('ETF_STOCK', 1))]);
    });

    it('lets a suggestion win over the type the provider proposes too (guard)', () => {
        // A BOND proposed for a STOCK at 1, but the plugin says 1: nothing to ask about the quote base.
        expect(forField(compare({asset_type: 'BOND'}, {form: {assetType: 'STOCK', quoteBaseQuantity: 1}, suggestion: {quantity: 1}}), 'quote_base_quantity')).toEqual(NOTHING);
    });

    it('is never an action, and an edit of the field during the request changes nothing', () => {
        const untouched = compare({}, {form: {assetType: 'STOCK', quoteBaseQuantity: 1}, suggestion: PENCE});
        const touched = compare({}, {form: {assetType: 'STOCK', quoteBaseQuantity: 1}, suggestion: PENCE, touched: ['quote_base_quantity']});
        expect(forField(touched, 'quote_base_quantity')).toEqual({actions: [], differences: [quoteBaseRow(1, suggested(100, 'GBp'))]});
        expect(touched).toEqual(untouched);
    });

    it.each<[ComparisonScope, number]>([
        ['all', 1],
        ['identifiers', 0],
    ])('scope %s: %i quote base row — only a full comparison proposes one', (scope, rows) => {
        expect(forField(compare({}, {scope, form: {assetType: 'STOCK', quoteBaseQuantity: 1}, suggestion: PENCE}), 'quote_base_quantity').differences).toHaveLength(rows);
    });

    it('lists the quote base row right after the currency row, the last one', () => {
        const result = compare({display_name: 'Apple Inc.', asset_type: 'STOCK', currency: 'USD'}, {form: {displayName: 'Apple', assetType: 'ETF', currency: 'EUR', currencyUserSet: true, quoteBaseQuantity: 100}});
        expect(result.differences.map((d) => d.field)).toEqual(['display_name', 'asset_type', 'currency', 'quote_base_quantity']);
    });

    it('notes the row with what the caller’s label says for its source — nothing included', () => {
        const quoteBaseNote = vi.fn((_source: QuoteBaseSource): string | undefined => undefined);
        const result = compareMetadata({}, snapshot({assetType: 'STOCK', quoteBaseQuantity: 100}), 'all', editedDuring([]), {...LABELS, quoteBaseNote}, null);
        expect(quoteBaseNote).toHaveBeenCalledWith(typeDefault('STOCK', 1));
        const [row] = forField(result, 'quote_base_quantity').differences;
        expect(row).toEqual({...quoteBaseRow(100, typeDefault('STOCK', 1)), note: undefined});
        expect(row?.note).toBeUndefined();
    });
});
