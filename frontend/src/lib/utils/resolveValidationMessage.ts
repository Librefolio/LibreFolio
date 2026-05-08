/**
 * Resolve validation issue messages into translated, human-friendly text.
 *
 * The backend sends structured `code` + `params` (IDs only, no resolved names).
 * This module enriches params with display names from stores and produces
 * a translated message via the i18n `$t` function.
 *
 * Fallback chain:
 *   1. `transactions.errors.<code>` with enriched params → translated string
 *   2. `issue.error` or `issue.msg` → raw English fallback (debug-friendly)
 *
 * @module utils/resolveValidationMessage
 */

import {formatCurrencyAmountPlain, formatCurrencyCodeHtml} from './currencyFormat';

/**
 * Mapping of Pydantic built-in error types to i18n keys.
 * These are NOT our custom codes — they come from Pydantic's own validators
 * (e.g. Field(gt=0) produces type="greater_than", ctx={gt: 0}).
 * We translate them so users see localized messages instead of English.
 */
const PYDANTIC_BUILTIN_KEYS: Record<string, string> = {
    greater_than: 'transactions.pydantic.greaterThan',
    greater_than_equal: 'transactions.pydantic.greaterThanEqual',
    less_than: 'transactions.pydantic.lessThan',
    less_than_equal: 'transactions.pydantic.lessThanEqual',
    missing: 'transactions.pydantic.missing',
    string_type: 'transactions.pydantic.stringType',
    decimal_parsing: 'transactions.pydantic.decimalParsing',
    int_parsing: 'transactions.pydantic.intParsing',
    value_error: 'transactions.pydantic.valueError',
    extra_forbidden: 'transactions.pydantic.extraForbidden',
};

/**
 * Field-specific overrides for Pydantic built-in errors.
 * Key = `fieldName:errorType`, value = i18n key.
 * These provide human-friendly messages for common cases where the generic
 * Pydantic message + field prefix is confusing (e.g. "Broker: Value must
 * be greater than 0" → "Please select a broker").
 */
const FIELD_ERROR_OVERRIDES: Record<string, string> = {
    'broker_id:greater_than': 'transactions.fieldErrors.brokerRequired',
    'broker_id:missing': 'transactions.fieldErrors.brokerRequired',
    'asset_id:greater_than': 'transactions.fieldErrors.assetRequired',
    'asset_id:missing': 'transactions.fieldErrors.assetRequired',
    'quantity:decimal_parsing': 'transactions.fieldErrors.quantityInvalid',
    'cash:missing': 'transactions.fieldErrors.cashRequired',
    'id:greater_than': 'transactions.errors.idRequired',
    'id:missing': 'transactions.errors.idRequired',
};

/** Minimal broker shape needed for resolution. */
interface BrokerLike {
    id: number;
    name: string;
}

/** Minimal asset shape needed for resolution. */
interface AssetLike {
    id: number;
    display_name: string;
    icon_url?: string | null;
    asset_type?: string | null;
}

/** Context stores for resolving IDs → display names. */
export interface ResolverContext {
    brokers?: BrokerLike[];
    assets?: AssetLike[];
    /** Optional function to resolve broker icon URL by ID. */
    getBrokerIconUrl?: (brokerId: number) => string | null;
}

/** Shape of a validation issue (from TXValidationIssue or extractValidationIssues). */
export interface ResolvableIssue {
    code?: string | null;
    params?: Record<string, any> | null;
    error?: string;
    msg?: string;
    /** Dot-joined Pydantic loc path (e.g. "body.creates.0.broker_id"). */
    loc?: string;
    /** Explicit field name from TXValidationIssue (e.g. "asset_id"). */
    field?: string | null;
}

/**
 * Extract the leaf field name from a Pydantic `loc` path or issue `field`.
 * Examples:
 *   "body.creates.0.broker_id"  → "broker_id"
 *   "body.creates.0.cash.amount" → "cash.amount"
 *   "body.creates.0"            → null (row-level, no specific field)
 */
function extractFieldName(issue: ResolvableIssue): string | null {
    // Prefer explicit field if set
    if (issue.field) return issue.field;

    if (!issue.loc) return null;
    const parts = issue.loc.split('.').filter(Boolean);
    // Strip "body", operation ("creates"/"updates"/"deletes"), and the row index
    let tail = parts;
    if (tail[0] === 'body') tail = tail.slice(1);
    if (tail[0] === 'creates' || tail[0] === 'updates' || tail[0] === 'deletes') tail = tail.slice(1);
    // Skip the row index (digit)
    if (tail.length > 0 && /^\d+$/.test(tail[0])) tail = tail.slice(1);
    // What remains is the field path (may be multi-segment like "cash.amount")
    if (tail.length === 0) return null;
    return tail.join('.');
}

/**
 * Translate a schema field name into a user-friendly label.
 * Uses the i18n key `transactions.fields.<fieldName>`.
 * Falls back to a cleaned-up version of the raw name.
 */
function translateFieldName(fieldName: string, t: (key: string, opts?: any) => string): string {
    // Flatten dots for the i18n key: "cash.amount" → "cash_amount"
    const keyPart = fieldName.replace(/\./g, '_');
    const key = `transactions.fields.${keyPart}`;
    const translated = t(key);
    if (translated !== key) return translated;
    // Fallback: replace underscores/dots with spaces, capitalize first letter
    const cleaned = fieldName.replace(/[_.]/g, ' ');
    return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

/**
 * Resolve a single validation issue into a user-facing translated message.
 *
 * @param issue  The issue object (from backend `/validate` response or Pydantic 422 extraction)
 * @param t      The i18n translation function (`$t` from svelte-i18n)
 * @param ctx    Optional stores for resolving brokerId/assetId into display names
 */
export function resolveIssueMessage(
    issue: ResolvableIssue,
    t: (key: string, opts?: {values?: Record<string, any>}) => string,
    ctx?: ResolverContext,
): string {
    const code = issue.code;
    if (!code) {
        return issue.error || issue.msg || 'Unknown error';
    }

    const rawParams = issue.params ?? {};
    const enriched: Record<string, any> = {...rawParams};

    // Resolve type code → translated type name (e.g. "BUY" → "Acquisto")
    for (const typeParam of ['type', 'typeA', 'typeB']) {
        if (rawParams[typeParam] && typeof rawParams[typeParam] === 'string') {
            const typeKey = `transactions.types.${rawParams[typeParam]}`;
            const translatedType = t(typeKey);
            if (translatedType !== typeKey) {
                enriched[typeParam] = translatedType;
            }
        }
    }

    // Resolve brokerId → brokerName (with icon)
    if (rawParams.brokerId != null && ctx?.brokers) {
        const broker = ctx.brokers.find((b) => b.id === rawParams.brokerId);
        const iconUrl = ctx.getBrokerIconUrl?.(rawParams.brokerId);
        const brokerIcon = iconUrl
            ? `<img src="${iconUrl}" alt="" width="16" height="16" style="display:inline;vertical-align:middle;margin-right:2px" onerror="this.style.display='none'">`
            : '';
        enriched.brokerName = broker ? `${brokerIcon}${broker.name}` : `Broker #${rawParams.brokerId}`;
    } else if (rawParams.brokerId != null) {
        enriched.brokerName = `Broker #${rawParams.brokerId}`;
    }

    // Resolve assetId → assetName (with icon)
    if (rawParams.assetId != null && ctx?.assets) {
        const asset = ctx.assets.find((a) => a.id === rawParams.assetId);
        if (asset) {
            const iconSrc = asset.icon_url ?? (asset.asset_type ? `/icons/asset-types/${asset.asset_type.toLowerCase()}.png` : '/icons/asset-types/other.png');
            const assetIcon = `<img src="${iconSrc}" alt="" width="16" height="16" style="display:inline;vertical-align:middle;margin-right:2px" onerror="this.style.display='none'">`;
            enriched.assetName = `${assetIcon}${asset.display_name}`;
        } else {
            enriched.assetName = `Asset #${rawParams.assetId}`;
        }
    } else if (rawParams.assetId != null) {
        enriched.assetName = `Asset #${rawParams.assetId}`;
    }

    // Format balance with currency if both present
    if (rawParams.balance != null && rawParams.currency) {
        enriched.formattedBalance = formatCurrencyAmountPlain(
            parseFloat(rawParams.balance),
            rawParams.currency,
            {showSign: true, minFraction: 2, maxFraction: 2},
        );
    } else if (rawParams.balance != null) {
        const num = parseFloat(rawParams.balance);
        // Asset balances: no forced decimals (show "5" not "5.00"), emoji 📈/📉 after number
        const emoji = num >= 0 ? '📈' : '📉';
        const formatted = num.toLocaleString(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 6,
        });
        enriched.balance = `${formatted} ${emoji}`;
    }

    // Resolve currency code → rich HTML with symbol + flag (e.g. "$ 🇺🇸 USD")
    if (rawParams.currency && typeof rawParams.currency === 'string') {
        enriched.currency = formatCurrencyCodeHtml(rawParams.currency);
    }

    // Extract and translate field name for prefixing
    const fieldName = extractFieldName(issue);
    const fieldLabel = fieldName ? translateFieldName(fieldName, t) : null;

    // Try translating with our custom error code first
    const key = `transactions.errors.${code}`;
    const translated = t(key, {values: enriched});

    // If our custom key exists, use it (already field-specific in wording)
    if (translated !== key) {
        return translated;
    }

    // Try field-specific override (e.g. broker_id:greater_than → "Please select a broker")
    if (fieldName && code) {
        const overrideKey = FIELD_ERROR_OVERRIDES[`${fieldName}:${code}`];
        if (overrideKey) {
            const overrideTranslated = t(overrideKey, {values: enriched});
            if (overrideTranslated !== overrideKey) return overrideTranslated;
        }
    }

    // Try Pydantic built-in error type mapping — these are generic,
    // so we PREFIX with the translated field name for context.
    const builtinKey = PYDANTIC_BUILTIN_KEYS[code];
    if (builtinKey) {
        const builtinTranslated = t(builtinKey, {values: enriched});
        if (builtinTranslated !== builtinKey) {
            return fieldLabel ? `${fieldLabel}: ${builtinTranslated}` : builtinTranslated;
        }
    }

    // Fallback to raw error/msg string, still prefixed with field if available
    const rawMsg = issue.error || issue.msg || code;
    return fieldLabel ? `${fieldLabel}: ${rawMsg}` : rawMsg;
}



