/**
 * Broker Types
 *
 * Types for broker entities and related data.
 * Derived from Zod schemas in generated.ts.
 */

import { z } from 'zod';
import { schemas } from '$lib/api/generated';

// =============================================================================
// TYPES DERIVED FROM ZOD SCHEMAS
// =============================================================================

/**
 * Basic broker information (from GET /brokers list).
 */
export type Broker = z.infer<typeof schemas.BRReadItem>;

/**
 * Broker with summary data including cash balances and holdings.
 * Retrieved from GET /brokers/:id/summary
 */
export type BrokerSummary = z.infer<typeof schemas.BRSummary>;

/**
 * Request body for creating a new broker.
 */
export type BrokerCreateItem = z.infer<typeof schemas.BRCreateItem>;

/**
 * Request body for updating a broker.
 */
export type BrokerUpdateItem = z.infer<typeof schemas.BRUpdateItem>;

/**
 * Asset holding within a broker (part of BrokerSummary).
 */
export type BrokerAssetHolding = z.infer<typeof schemas.BRAssetHolding>;

/**
 * Broker access entry (for multi-user access control).
 */
export type BrokerAccessItem = z.infer<typeof schemas.BRAccessItem>;

/**
 * Response from GET /brokers/:id/access
 */
export type BrokerAccessListResponse = z.infer<typeof schemas.BRAccessListResponse>;

// =============================================================================
// FRONTEND-ONLY TYPES
// =============================================================================

/**
 * Simplified broker info for dropdowns and references.
 */
export interface BrokerInfo {
	id: number;
	name: string;
}

/**
 * Broker with UI state for interactive components.
 */
export interface BrokerWithUIState extends Broker {
	/** Whether this broker is selected in a list */
	isSelected?: boolean;
	/** Whether an operation is in progress for this broker */
	isLoading?: boolean;
}
