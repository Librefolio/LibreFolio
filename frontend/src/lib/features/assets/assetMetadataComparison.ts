/**
 * assetMetadataComparison — the decision half of AssetModal's "Ask Provider": what the provider's metadata does to
 * the form, as a pure function.
 *
 * Each field is compared against the value it had when the comparison started: a field is written only by its own
 * step, so deciding everything on that snapshot gives the same outcome as writing step by step. The modal keeps the
 * network, the request tickets, the toasts and the comparison dialog, and applies the actions in order.
 *
 * The description, the sectors and the countries are not compared (plan 68, E9): they are the profile's, which the
 * enrichers fill and the profile window compares. A provider's `classification_params` is not read.
 *
 * Per field, three outcomes:
 * - the form is empty and the user has not typed in it → fill it with the provider's value;
 * - the values agree (or differ only by case, or the currency is the untouched default) → nothing to ask;
 * - they differ → a row of the comparison dialog.
 *
 * The quote base (Z-32 d) is never filled, the field being never empty: the provider's suggestion, else the default of
 * the type the provider proposes (or the form's), is a row when it differs from the field.
 *
 * @module features/assets/assetMetadataComparison
 */
import {IDENTIFIER_TYPES, isFamilyOnlyProposal} from '$lib/utils/assetTypes';
import type {DiffItem} from './ProviderComparisonModal.svelte';
import {proposeQuoteBase, type QuoteBaseSource, type QuoteBaseSuggestion} from './assetFormState';

/** Which fields a comparison covers: `all`, or the identifiers' own "Ask Provider". */
export type ComparisonScope = 'all' | 'identifiers';

/** The form values a comparison reads, taken before it starts. */
export interface ComparisonSnapshot {
    /** Current value per single-valued identifier type (`ISIN` → `IT0005…`), `''` when the row is absent. */
    identifiers: Record<string, string>;
    displayName: string;
    assetType: string;
    currency: string;
    /** The user picked the currency (otherwise the form shows a default the provider may correct silently). */
    currencyUserSet: boolean;
    /** The asset's icon URL, `''` for none (project 76, P3: a provider's logo is compared like the other fields). */
    iconUrl: string;
    /** The form's quote base ("Units per single price"). */
    quoteBaseQuantity: number;
}

/** The localized labels of the comparison rows (identifier rows are labelled by their type). */
export interface ComparisonLabels {
    name: string;
    type: string;
    currency: string;
    icon: string;
    quoteBase: string;
    /** The note under the quote base row, from where its proposal comes; undefined for none. */
    quoteBaseNote: (source: QuoteBaseSource) => string | undefined;
}

/** A write into the form, in the order the modal applies it. Every action also marks its `field` auto-filled. */
export type ComparisonAction =
    /** Fill a string field (`display_name`, `asset_type`, `currency`, `icon_url`, `identifier_<type>`). */
    | {kind: 'fill'; field: string; value: string}
    /** The form already agrees with the provider on this field. */
    | {kind: 'agree'; field: string}
    /** Merge the provider's OTHER identifiers (marked auto-filled only when some are new). */
    | {kind: 'mergeOther'; field: 'identifier_other'; values: unknown};

export interface MetadataComparison {
    actions: ComparisonAction[];
    /** The rows of the comparison dialog, in field order. */
    differences: DiffItem[];
}

/**
 * Compare a provider's metadata (`patch_data` of the probe) with the form.
 *
 * @param patchData the provider's metadata
 * @param snapshot the form values when the comparison started
 * @param scope the fields to compare
 * @param manuallyChanged whether the user edited a field since the request was sent
 * @param labels the localized labels of the rows
 * @param quoteBaseSuggestion the provider's quote base suggestion for this line (Z-32 d), if any
 */
export function compareMetadata(patchData: Record<string, any>, snapshot: ComparisonSnapshot, scope: ComparisonScope, manuallyChanged: (field: string) => boolean, labels: ComparisonLabels, quoteBaseSuggestion?: QuoteBaseSuggestion | null): MetadataComparison {
    const actions: ComparisonAction[] = [];
    const differences: DiffItem[] = [];

    function compareStringField(field: string, label: string, currentVal: string, providerVal: string | null | undefined) {
        if (!providerVal) return;
        const touched = manuallyChanged(field);
        if (!currentVal && !touched) {
            actions.push({kind: 'fill', field, value: providerVal});
        } else if (currentVal === providerVal || (field === 'asset_type' && isFamilyOnlyProposal(currentVal, providerVal))) {
            // A provider that only knows the family of the stored subtype (ETF for an
            // ETF_STOCK) agrees with it: no row, the subtype stays (K step 17, item 17).
            if (!touched) actions.push({kind: 'agree', field});
        } else {
            // Name/casing noise: the on-site search title and the metadata page title
            // differ only in case (e.g. "T-bond" vs "T-Bond") — same instrument, not a
            // real difference. Skip instead of showing a false diff.
            // Not for an icon: a URL's path is case-sensitive, so another case is another image (project 76, P3).
            const isCaseOnly = field !== 'icon_url' && currentVal.trim().toLowerCase() === providerVal.trim().toLowerCase();
            // Currency not explicitly chosen: on a fresh asset the search may leave the
            // currency unset, so the form still shows the base-currency default (e.g. EUR)
            // while the provider knows the real one (e.g. a USD-denominated EuroTLX bond).
            // The user never picked that value — auto-fill it rather than flag a fake diff.
            const isUnsetCurrencyDefault = field === 'currency' && !snapshot.currencyUserSet;
            if (!touched && (isCaseOnly || isUnsetCurrencyDefault)) {
                actions.push({kind: 'fill', field, value: providerVal});
            } else {
                differences.push({field, label, type: 'string', currentValue: currentVal, providerValue: providerVal, selected: true});
            }
        }
    }

    function compareQuoteBase() {
        // The ladder reads the type the provider proposes, when it proposes another one
        const providerType = typeof patchData.asset_type === 'string' ? patchData.asset_type : '';
        const typeChanges = providerType !== '' && providerType !== snapshot.assetType && !isFamilyOnlyProposal(snapshot.assetType, providerType);
        const source = proposeQuoteBase(quoteBaseSuggestion, typeChanges ? providerType : snapshot.assetType);
        if (source.quantity === snapshot.quoteBaseQuantity) return;
        differences.push({field: 'quote_base_quantity', label: labels.quoteBase, type: 'string', currentValue: String(snapshot.quoteBaseQuantity), providerValue: String(source.quantity), selected: true, note: labels.quoteBaseNote(source), quoteBaseSource: source});
    }

    // --- IDENTIFIERS (scope 'all' or 'identifiers') ---
    if (scope === 'all' || scope === 'identifiers') {
        for (const idType of IDENTIFIER_TYPES) {
            // OTHER is a JSON list of soft identifiers, not a scalar string — handled below.
            if (idType === 'OTHER') continue;
            const dbKey = `identifier_${idType.toLowerCase()}`;
            const provVal = patchData[dbKey];
            if (provVal) compareStringField(dbKey, idType, snapshot.identifiers[idType] ?? '', provVal);
        }
        // OTHER: merge each list element as its own row (additive, deduped) instead of
        // routing the array through the string compare path.
        if (!manuallyChanged('identifier_other')) actions.push({kind: 'mergeOther', field: 'identifier_other', values: patchData.identifier_other});
    }

    // --- ASSET DETAILS (scope 'all' only) ---
    if (scope === 'all') {
        compareStringField('display_name', labels.name, snapshot.displayName, patchData.display_name);
        compareStringField('asset_type', labels.type, snapshot.assetType, patchData.asset_type);
        compareStringField('currency', labels.currency, snapshot.currency, patchData.currency);
        // The provider's logo: filled when the asset has none, a choice when it has another (project 76, P3)
        compareStringField('icon_url', labels.icon, snapshot.iconUrl, patchData.icon_url);
        compareQuoteBase();
    }

    return {actions, differences};
}
