/**
 * Common/Shared Types
 *
 * Utility types used across multiple domains.
 * Types are derived from Zod schemas in generated.ts to stay in sync with backend.
 */

import {z} from 'zod';
import {schemas} from '$lib/api/generated';

// =============================================================================
// TYPES DERIVED FROM ZOD SCHEMAS
// =============================================================================

/**
 * Currency amount with ISO 4217 code.
 * Amount is kept as string to preserve decimal precision (no floating point errors).
 *
 * For calculations, use Decimal.js library.
 * For display, use formatCurrency() which handles string amounts.
 *
 * @example
 * { code: "EUR", amount: "1000.50" }
 * { code: "USD", amount: "-250.00" }  // negative for withdrawals
 */
export type Currency = z.infer<typeof schemas.Currency_Output>;

/**
 * Parse currency amount string to number for display formatting.
 * ⚠️ Use only for display! For calculations, use Decimal.js.
 */
export function parseCurrencyAmount(amount: string | undefined | null): number {
    if (!amount) return 0;
    return parseFloat(amount) || 0;
}

// =============================================================================
// UTILITY HELPERS FOR GENERATED TYPE ISSUES
// =============================================================================
// Note: openapi-zod-client sometimes generates incorrect union types like
// `string | (string | null)[]` instead of `string | null`. These helpers
// safely extract the correct value.

/**
 * Safely extract string value from potentially malformed union type.
 * Handles: string | null | undefined | (string | null)[]
 */
export function safeString(value: unknown): string | null {
    if (value === null || value === undefined) return null;
    if (typeof value === 'string') return value;
    if (Array.isArray(value) && value.length > 0) {
        const first = value[0];
        return typeof first === 'string' ? first : null;
    }
    return null;
}

/**
 * Safely extract number value from potentially malformed union type.
 * Handles: number | null | undefined | (number | null)[]
 */
export function safeNumber(value: unknown): number | null {
    if (value === null || value === undefined) return null;
    if (typeof value === 'number') return value;
    if (Array.isArray(value) && value.length > 0) {
        const first = value[0];
        return typeof first === 'number' ? first : null;
    }
    return null;
}

/**
 * Safely extract Currency value from potentially malformed union type.
 * Returns a proper Currency object with string amount.
 */
export function safeCurrency(value: unknown): Currency | null {
    if (value === null || value === undefined) return null;
    if (Array.isArray(value)) {
        // Take first non-null element
        const first = value.find((v) => v !== null);
        if (!first) return null;
        value = first;
    }
    const v = value as Record<string, unknown>;
    if (typeof v.code !== 'string') return null;
    const amount = typeof v.amount === 'string' ? v.amount : typeof v.amount === 'number' ? String(v.amount) : '0';
    return {code: v.code, amount};
}

/**
 * User role for broker access control.
 * - OWNER: Full access (CRUD broker, manage access, delete broker)
 * - EDITOR: Modify broker and transactions, can only remove self
 * - VIEWER: Read-only access
 */
export type UserRole = z.infer<typeof schemas.UserRole>;

/**
 * Transaction types supported by the system.
 */
export type TransactionType = z.infer<typeof schemas.TransactionType>;

/**
 * Asset types supported by the system.
 */
export type AssetType = z.infer<typeof schemas.AssetType>;

/**
 * Identifier types for assets.
 */
export type IdentifierType = z.infer<typeof schemas.IdentifierType>;

// =============================================================================
// FRONTEND-ONLY UTILITY TYPES
// =============================================================================

/**
 * Date range for filtering queries.
 */
export interface DateRange {
    /** Start date (inclusive), ISO 8601 format */
    start?: string;
    /** End date (inclusive), ISO 8601 format */
    end?: string;
}

/**
 * Pagination parameters for list endpoints.
 */
export interface PaginationParams {
    /** Number of items to skip */
    offset?: number;
    /** Maximum number of items to return */
    limit?: number;
}

/**
 * Standard paginated response wrapper.
 */
export interface PaginatedResponse<T> {
    /** Array of items */
    items: T[];
    /** Total count of items (before pagination) */
    total: number;
    /** Current offset */
    offset: number;
    /** Current limit */
    limit: number;
}

/**
 * Generic API error response.
 */
export interface ApiErrorResponse {
    /** Error message */
    detail: string;
    /** Optional error code */
    code?: string;
    /** Optional field-level errors */
    errors?: Record<string, string[]>;
}
