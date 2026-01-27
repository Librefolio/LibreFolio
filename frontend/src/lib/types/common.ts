/**
 * Common/Shared Types
 *
 * Utility types used across multiple domains.
 * Types are derived from Zod schemas in generated.ts to stay in sync with backend.
 */

import { z } from 'zod';
import { schemas } from '$lib/api/generated';

// =============================================================================
// TYPES DERIVED FROM ZOD SCHEMAS
// =============================================================================

/**
 * Currency amount with ISO 4217 code.
 * Used for cash balances, transaction amounts, prices, etc.
 *
 * @example
 * { code: "EUR", amount: "1000.50" }
 * { code: "USD", amount: "-250.00" }  // negative for withdrawals
 */
export type Currency = z.infer<typeof schemas.Currency_Output>;

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
