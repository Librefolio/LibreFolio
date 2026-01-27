/**
 * Transaction Types
 *
 * Types for financial transactions.
 * Derived from Zod schemas in generated.ts.
 */

import { z } from 'zod';
import { schemas } from '$lib/api/generated';

// =============================================================================
// TYPES DERIVED FROM ZOD SCHEMAS
// =============================================================================

/**
 * Transaction as returned from GET /transactions.
 */
export type Transaction = z.infer<typeof schemas.TXReadItem>;

/**
 * Request body for creating transactions (input format).
 */
export type TransactionCreateItem = z.infer<typeof schemas.TXCreateItem_Input>;

/**
 * Transaction as returned from parsing (output format with possible fake IDs).
 */
export type TransactionParsed = z.infer<typeof schemas.TXCreateItem_Output>;

/**
 * Request body for updating a transaction.
 */
export type TransactionUpdateItem = z.infer<typeof schemas.TXUpdateItem>;

/**
 * Metadata about a transaction type (for UI display).
 */
export type TransactionTypeMetadata = z.infer<typeof schemas.TXTypeMetadata>;

// =============================================================================
// FRONTEND-ONLY TYPES
// =============================================================================

/**
 * Simplified transaction for display in lists.
 */
export interface TransactionSummary {
	id: number;
	type: string;
	date: string;
	currency: string;
	total_amount: number;
	asset_name?: string;
}
