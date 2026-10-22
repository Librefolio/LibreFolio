/**
 * assetFormState — pure derivations behind the AssetModal form.
 *
 * These are the boolean/derivation expressions that used to live inline in
 * `$derived(...)` inside `AssetModal.svelte`. Each is a function of its inputs, so
 * extracting them makes every branch (the quote-base validity ladder, the
 * has-provider gate, the create-vs-edit dirty rule, the notice grouping) testable
 * without mounting the modal. The `$derived` wrappers stay in the component and
 * just call these.
 *
 * @module components/assets/assetFormState
 */

/**
 * A quote base of zero or less is a division-by-zero waiting to happen in every
 * price conversion, and a fractional base is not a quotation unit. Invalid when the
 * value is non-finite, below 1, or not an integer.
 */
export function isQuoteBaseQuantityInvalid(q: number): boolean {
    return !Number.isFinite(q) || q < 1 || !Number.isInteger(q);
}

/**
 * The quote base an asset type starts from when no provider suggests one (Z-32 d): bonds are quoted per 100 nominal
 * (BTP/BOT and most MOT bonds), every other type per unit. One entry per exception.
 */
export const QUOTE_BASE_TYPE_DEFAULTS: Readonly<Record<string, number>> = Object.freeze({BOND: 100});

/** The quote base of an asset type without a provider's suggestion: `QUOTE_BASE_TYPE_DEFAULTS`, else 1. */
export function defaultQuoteBaseQuantity(assetType: string): number {
    return QUOTE_BASE_TYPE_DEFAULTS[(assetType ?? '').toUpperCase()] ?? 1;
}

/** A provider's quote base suggestion, as the API sends it (`FAQuoteBaseSuggestion`). */
export interface QuoteBaseSuggestion {
    quantity: number;
    quote_currency?: string | null;
}

/** Where a proposed quote base comes from: the provider's explicit suggestion, or the asset type's default. */
export type QuoteBaseSource = {kind: 'suggestion'; quantity: number; quoteCurrency: string | null} | {kind: 'typeDefault'; assetType: string; quantity: number};

/**
 * The quote base the form proposes (Z-32 d, the developer's ladder): the provider's explicit suggestion when it is a
 * whole number of at least 1, else the asset type's default. A search selection writes it like the name; "Ask the
 * provider" offers it as a comparison row when it differs from the field.
 */
export function proposeQuoteBase(suggestion: QuoteBaseSuggestion | null | undefined, assetType: string): QuoteBaseSource {
    const quantity = suggestion?.quantity;
    if (typeof quantity === 'number' && Number.isInteger(quantity) && quantity >= 1) {
        return {kind: 'suggestion', quantity, quoteCurrency: suggestion?.quote_currency ?? null};
    }
    return {kind: 'typeDefault', assetType, quantity: defaultQuoteBaseQuantity(assetType)};
}

/**
 * The note that says why a quote base is proposed: the provider's suggestion (with its quote currency when it gave
 * one), or the bond convention; none for another type's default of 1.
 */
export function quoteBaseNote(source: QuoteBaseSource, provider: string): {key: string; values: Record<string, string | number>} | null {
    if (source.kind === 'suggestion') {
        return source.quoteCurrency ? {key: 'assets.modal.quoteBaseSuggested', values: {provider, currency: source.quoteCurrency, quantity: source.quantity}} : {key: 'assets.modal.quoteBaseSuggestedPlain', values: {provider, quantity: source.quantity}};
    }
    return source.assetType.toUpperCase() === 'BOND' ? {key: 'assets.modal.bondQuoteBaseHint', values: {}} : null;
}

/**
 * The i18n key for the quote-base validation message: the "min" message when the
 * value is non-finite or below 1, otherwise the "integer" message (a finite,
 * ≥1 but non-integer value).
 */
export function quoteBaseQuantityErrorKey(q: number): string {
    return !Number.isFinite(q) || q < 1 ? 'assets.modal.quoteBaseMin' : 'assets.modal.quoteBaseInteger';
}

/**
 * A provider is "configured enough" to act on when it is not explicitly removed,
 * has a code, and either carries an identifier or is an AUTO_GENERATED type (which
 * needs none).
 */
export function computeHasProvider(providerNoProvider: boolean, providerCode: string, providerIdentifier: string, providerIdentifierType: string): boolean {
    return !providerNoProvider && providerCode !== '' && (providerIdentifier !== '' || providerIdentifierType === 'AUTO_GENERATED');
}

/** The four provider fields whose change makes the provider block dirty. */
export interface ProviderFields {
    code: string;
    identifier: string;
    identifierType: string;
    params: unknown;
}

/**
 * Whether the provider block differs from its load-time snapshot. In create mode
 * (no snapshot) any configured provider counts as dirty; in edit mode it is a
 * field-by-field comparison, with params compared as canonical JSON (an absent
 * initial snapshot reads as the string `'null'`).
 */
export function computeProviderDirty(editMode: boolean, hasProvider: boolean, current: ProviderFields, initialParamsJson: string, initial: Omit<ProviderFields, 'params'>): boolean {
    if (!editMode) return hasProvider;
    return current.code !== initial.code || current.identifier !== initial.identifier || current.identifierType !== initial.identifierType || JSON.stringify(current.params ?? null) !== (initialParamsJson || 'null');
}

/** One raw import advisory, as authored by a broker-import plugin. */
export interface ImportNotice {
    kind?: string | null;
    reason?: string | null;
}

/** Advisories grouped by category, ready to render as one banner per `kind`. */
export interface GroupedNotice {
    kind: string;
    reasons: string[];
}

/**
 * Group import advisories by category (`kind`, defaulting to `'generic'`),
 * deduping identical reasons within a category and dropping any notice that is
 * null or carries no reason. Insertion order of both categories and reasons is
 * preserved.
 */
export function groupImportNotices(notices: readonly (ImportNotice | null | undefined)[] | null | undefined): GroupedNotice[] {
    const groups = new Map<string, string[]>();
    for (const n of notices ?? []) {
        if (!n || !n.reason) continue;
        const kind = n.kind || 'generic';
        const bucket = groups.get(kind) ?? [];
        if (!bucket.includes(n.reason)) bucket.push(n.reason);
        groups.set(kind, bucket);
    }
    return [...groups.entries()].map(([kind, reasons]) => ({kind, reasons}));
}
