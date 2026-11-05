/**
 * Broker Types
 *
 * Types for broker entities and related data.
 * Derived from Zod schemas in generated.ts.
 */

import {z} from 'zod';
import {schemas} from '$lib/api/generated';

// =============================================================================
// TYPES DERIVED FROM ZOD SCHEMAS
// =============================================================================

/**
 * Basic broker information (from GET /brokers list).
 */
export type Broker = z.infer<typeof schemas.BRReadItem>;

// =============================================================================
// FRONTEND-ONLY TYPES
// =============================================================================

/**
 * Simplified broker info for dropdowns and references.
 * Compatible with BrokerSelect component.
 */
export interface BrokerInfo {
    id: number;
    name: string;
    /** Optional icon URL for display in dropdowns */
    icon_url?: string | null;
    /** Optional portal URL for favicon fallback */
    portal_url?: string | null;
    /** Plugin code for resolving the plugin icon (step 3 of fallback chain) */
    default_import_plugin?: string | null;
}
