/**
 * Transaction Type Store — Server-driven type rules + event type metadata.
 *
 * Replaces the 3 hardcoded files:
 * - `transactionTypeRules.ts`  (TypeRule, getTypeRule, isDraftReadyForValidation, …)
 * - `transactionTypes.ts`      (TX_TYPES, getTransactionTypeIconUrl, getTxTypeDocUrl, …)
 * - `eventTypes.ts`            (getEventTypeEmoji)
 *
 * Data is lazily fetched from `GET /transactions/types` on first use and
 * cached for the session. Types (FieldMode, SignRule) are derived from the
 * Zod-generated client — no manual duplication.
 *
 * @module stores/transactionTypeStore
 */

import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {writable} from 'svelte/store';
import type {z} from 'zod';

// =============================================================================
//  Types — derived from generated Zod schemas (single source of truth)
// =============================================================================

export const TX_TYPES = schemas.TransactionType.options;
export type TransactionTypeCode = (typeof TX_TYPES)[number];

/** Server-side transaction type metadata (full shape from the API). */
type ServerTXType = z.infer<typeof schemas.TXTypeMetadata>;

/** Server-side event type metadata. */
type ServerEventType = z.infer<typeof schemas.EventTypeMetadata>;

/** Combined response from GET /transactions/types. */
type ServerTypesResponse = z.infer<typeof schemas.TXTypesResponse>;

/** Field visibility/requirement mode — derived from backend FieldMode enum. */
export type FieldMode = ServerTXType['asset_mode'];

/** Sign constraint — derived from backend SignType enum. */
export type SignRule = ServerTXType['quantity_sign'];

/** Pair form layout — derived from backend PairFormLayout enum. */
export type PairFormLayout = NonNullable<ServerTXType['pair_form_layout']>;

// =============================================================================
//  TypeRule — frontend-friendly shape (renamed fields for readability)
// =============================================================================

export interface TypeRule {
	assetField: FieldMode;
	cashField: FieldMode;
	quantityMode: FieldMode;
	quantityRule: SignRule;
	cashSign: SignRule;
	eventLinkable: boolean;
	requiresPair: boolean;
	pairFormLayout: PairFormLayout | null;
}

export interface ValidatableDraft {
	type: string;
	broker_id: number;
	asset_id?: number | null;
	quantity?: string | null;
	cash?: {code: string; amount: string} | null;
}

// =============================================================================
//  Internal cache
// =============================================================================

let _cache: ServerTypesResponse | null = null;
let _loading: Promise<void> | null = null;
/** Derived TypeRule map — populated when _cache is set. */
let _ruleMap: Record<string, TypeRule> = {};

/** Reactive version counter — bumped when types are loaded, so $derived
 *  expressions that read `$typesVersion` re-evaluate. */
export const typesVersion = writable(0);

// =============================================================================
//  Server → TypeRule (no mapping — values are already lowercase)
// =============================================================================

function serverTypeToRule(s: ServerTXType): TypeRule {
	return {
		assetField: s.asset_mode,
		cashField: s.cash_mode,
		quantityMode: s.quantity_mode,
		quantityRule: s.quantity_sign,
		cashSign: s.cash_sign,
		eventLinkable: s.event_compatible,
		requiresPair: s.requires_link,
		pairFormLayout: s.pair_form_layout ?? null,
	};
}

function rebuildRuleMap(types: ServerTXType[]): Record<string, TypeRule> {
	const map: Record<string, TypeRule> = {};
	for (const t of types) {
		map[t.code] = serverTypeToRule(t);
	}
	return map;
}

// =============================================================================
//  Permissive fallback (used only for truly unknown type codes)
// =============================================================================

const FALLBACK_RULE: TypeRule = {
	assetField: 'optional',
	cashField: 'optional',
	quantityMode: 'optional',
	quantityRule: 'free',
	cashSign: 'free',
	eventLinkable: false,
	requiresPair: false,
	pairFormLayout: null,
};

// =============================================================================
//  Public API
// =============================================================================

/**
 * Ensure types are loaded from the server. Call this at modal open time.
 * Returns immediately if already loaded. Safe to call multiple times.
 */
export async function ensureTypesLoaded(): Promise<void> {
	if (_cache) return;
	if (_loading) return _loading;
	_loading = (async () => {
		try {
			const resp = (await zodiosApi.get_transaction_types_api_v1_transactions_types_get()) as unknown as ServerTypesResponse;
			_cache = resp;
			_ruleMap = rebuildRuleMap(resp.transaction_types);
			typesVersion.update((v) => v + 1);
		} catch (e) {
			console.error('[transactionTypeStore] Failed to fetch /transactions/types', e);
			throw e; // let caller handle — frontend cannot work without type rules
		} finally {
			_loading = null;
		}
	})();
	return _loading;
}

/** Whether the type cache has been populated. Use in $derived to defer rendering. */
export function isTypesLoaded(): boolean {
	return _cache != null;
}

/** Safe lookup — returns FALLBACK_RULE only for truly unknown codes. */
export function getTypeRule(type: string | null | undefined): TypeRule {
	const code = (type ?? '').toUpperCase();
	return _ruleMap[code] ?? FALLBACK_RULE;
}

/** Icon URL for a transaction type. */
export function getTypeIconUrl(type: string | null | undefined): string {
	const code = (type ?? '').toUpperCase();
	if (_cache) {
		const st = _cache.transaction_types.find((t) => t.code === code);
		if (st) return `/icons/transactions/${st.icon_slug}.png`;
	}
	// Derive slug from code (e.g. FX_CONVERSION → fx-conversion)
	const slug = code.toLowerCase().replace(/_/g, '-');
	return `/icons/transactions/${slug}.png`;
}

/** Alias matching the old transactionTypes.ts export name. */
export const getTransactionTypeIconUrl = getTypeIconUrl;

/** Languages with a built mkdocs site (besides default `en`). */
const DOC_LANGS = new Set(['it', 'fr', 'es']);

/** Docs URL for a transaction type, language-aware. */
export function getTxTypeDocUrl(type: string | null | undefined, lang: string = 'en'): string {
	const code = (type ?? '').toUpperCase();
	let slug: string | null = null;

	if (_cache) {
		const st = _cache.transaction_types.find((t) => t.code === code);
		slug = (st?.doc_slug as string | null | undefined) ?? null;
	}

	const langPrefix = DOC_LANGS.has(lang) ? `/${lang}` : '';
	return slug ? `/mkdocs${langPrefix}/financial-theory/instruments/transaction-types/${slug}/` : `/mkdocs${langPrefix}/financial-theory/instruments/transaction-types/`;
}

/** Emoji for an event type. */
export function getEventTypeEmoji(type: string | null | undefined): string {
	const code = (type ?? '').toUpperCase();
	if (_cache) {
		const et = _cache.event_types.find((e) => e.code === code);
		if (et) return et.emoji;
	}
	return '📌';
}

/** Types NOT requiring the pair-wizard — selectable in bulk modal / form. */
export function getStandaloneTypes(): TransactionTypeCode[] {
	return TX_TYPES.filter((t) => !getTypeRule(t).requiresPair);
}

// =============================================================================
//  H6: Sign-flip swap groups
// =============================================================================

/** Swap groups for "sign flip" — types that share identical field structure
 *  and can be swapped freely. Paired types are locked (no swap). */
const SWAP_GROUPS: ReadonlyArray<ReadonlyArray<TransactionTypeCode>> = [
	['BUY', 'SELL'],
	['DEPOSIT', 'WITHDRAWAL'],
	['DIVIDEND', 'INTEREST'],
	['TAX', 'FEE'],
	// ADJUSTMENT is a singleton — no swap partner
	// Paired types (CASH_TRANSFER, TRANSFER, FX_CONVERSION) — locked
];

/** Given a type code, return the set of types it can be "flipped" to
 *  (including itself). Returns [type] for singletons/paired (no flip). */
export function getSwapGroup(type: TransactionTypeCode): TransactionTypeCode[] {
	for (const group of SWAP_GROUPS) {
		if (group.includes(type)) return [...group];
	}
	return [type]; // singleton or paired → only itself
}

/** Pair-only types — created via promote wizard. */
export function getPairTypes(): TransactionTypeCode[] {
	return TX_TYPES.filter((t) => getTypeRule(t).requiresPair);
}

/** Types that have a dual-transaction form layout. */
export function getDualFormTypes(): TransactionTypeCode[] {
	return TX_TYPES.filter((t) => getTypeRule(t).pairFormLayout != null);
}

/** Get the pair form layout for a type (null = standard single form). */
export function getPairFormLayout(type: string | null | undefined): PairFormLayout | null {
	return getTypeRule(type).pairFormLayout;
}

/** Types that may link to an AssetEvent. */
export function getEventLinkableTypes(): TransactionTypeCode[] {
	return TX_TYPES.filter((t) => getTypeRule(t).eventLinkable);
}

/**
 * True when required fields for the draft's type are populated.
 * Gates auto-validation triggers so the user doesn't see obvious errors on empty rows.
 */
export function isDraftReadyForValidation(d: ValidatableDraft): boolean {
	if (!d.broker_id || d.broker_id <= 0) return false;
	const r = getTypeRule(d.type);
	if (r.assetField === 'required' && d.asset_id == null) return false;
	if (r.cashField === 'required' && (!d.cash || !d.cash.amount || d.cash.amount.trim() === '' || d.cash.amount === '0')) return false;
	if (r.quantityMode !== 'forbidden') {
		const q = (d.quantity ?? '').trim();
		if (q === '' || Number(q) === 0) return false;
	}
	return true;
}

/**
 * Build SelectOption[] for transaction type dropdowns (with icons).
 */
export function buildTransactionTypeOptions(t: (key: string) => string): Array<{
	value: string;
	label: string;
	icon: string;
}> {
	return TX_TYPES.map((tt) => ({
		value: tt,
		label: t(`transactions.types.${tt}`) || tt,
		icon: getTypeIconUrl(tt),
	}));
}

// =============================================================================
//  Promote matching — B1-17: server-driven promote rules
// =============================================================================

export interface PromoteMatch {
	/** Target paired type code (e.g. CASH_TRANSFER, TRANSFER, FX_CONVERSION). */
	targetType: string;
	/** Translated name of the target type. */
	targetLabel: string;
}

/**
 * Given 2 selected transaction rows, check if any paired type's `promote_from` rules
 * match their types. Returns the first match or null.
 *
 * The matching considers both orderings (rowA is type_a + rowB is type_b, or vice versa).
 */
export function findPromoteMatch(
	typeA: string,
	typeB: string,
	t: (key: string) => string,
): PromoteMatch | null {
	if (!_cache) return null;
	for (const st of _cache.transaction_types) {
		const promoteRules = st.promote_from;
		if (!promoteRules || !Array.isArray(promoteRules)) continue;
		for (const rule of promoteRules) {
			if (!rule || typeof rule !== 'object' || Array.isArray(rule)) continue;
			const r = rule as {type_a: string; type_b: string};
			const matchForward = typeA === r.type_a && typeB === r.type_b;
			const matchReverse = typeA === r.type_b && typeB === r.type_a;
			if (matchForward || matchReverse) {
				return {
					targetType: st.code,
					targetLabel: t(`transactions.types.${st.code}`) || st.code,
				};
			}
		}
	}
	return null;
}

