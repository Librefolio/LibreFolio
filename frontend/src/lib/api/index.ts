/**
 * API Module Exports
 *
 * This module provides:
 * - api: Legacy API client (fetch-based) - DEPRECATED, use zodiosApi instead
 * - zodiosApi: Type-safe API client with Zod validation (Axios-based)
 * - ApiError: Custom error class for API errors
 * - schemas: Zod schemas for deriving TypeScript types
 *
 * Architecture:
 * - Authentication is handled by backend via HTTP-only session cookies
 * - Axios sends cookies with withCredentials: true
 * - Interceptors handle 401 redirects and add Accept-Language header
 *
 * Migration Guide:
 * - Old: api.get<Broker[]>('/brokers')
 * - New: zodiosApi.list_brokers_api_v1_brokers_get()
 *
 * The Zodios client provides:
 * - Full TypeScript autocomplete for endpoints
 * - Runtime validation of responses via Zod
 * - Type-safe request parameters
 */

// =============================================================================
// ZODIOS CLIENT (RECOMMENDED)
// =============================================================================
export { zodiosApi, ApiError, axiosInstance } from './zodios-client';

// =============================================================================
// LEGACY CLIENT (DEPRECATED - for backward compatibility during migration)
// =============================================================================
export { api, apiCall } from './client';
export type { ApiCallOptions } from './client';

// =============================================================================
// ZOD SCHEMAS (for deriving types in /lib/types/)
// =============================================================================
// Usage: import { schemas } from '$lib/api'; then z.infer<typeof schemas.X>
export { schemas } from './generated';
