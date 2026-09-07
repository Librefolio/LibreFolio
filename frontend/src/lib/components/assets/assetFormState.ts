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
 * Whether to seed the bond per-100 quotation default: only for a BOND still at the
 * initial 1 that the user has not manually touched. A market convention (BTP/BOT and
 * most MOT bonds quote per 100 nominal), so it is a suggestion, never an override.
 */
export function shouldSeedBondQuoteBase(assetType: string, quoteBaseQuantity: number, touched: boolean): boolean {
    return assetType === 'BOND' && quoteBaseQuantity === 1 && !touched;
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
