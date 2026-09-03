/**
 * Transaction Types
 *
 * Types for financial transactions.
 * Derived from Zod schemas in generated.ts.
 */

import {z} from 'zod';
import {schemas} from '$lib/api/generated';

// =============================================================================
// TYPES DERIVED FROM ZOD SCHEMAS
// =============================================================================

/**
 * Transaction as returned from GET /transactions.
 */
export type Transaction = z.infer<typeof schemas.TXReadItem>;

/**
 * Request body for creating transactions.
 *
 * Uses the `_Output` variant: the generator splits `TXCreateItem` in two because the
 * schema appears both as a request body and in responses, and the output shape is the
 * narrow one (`quantity: string` rather than `string | number | array`). That is what
 * the app actually builds and reads, and an `_Output` value is accepted wherever an
 * `_Input` is expected.
 */
export type TransactionCreateItem = z.infer<typeof schemas.TXCreateItem_Output>;
