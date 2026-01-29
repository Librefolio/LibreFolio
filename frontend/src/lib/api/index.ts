/**
 * API Module Exports
 *
 * This module provides:
 * - zodiosApi: Type-safe API client with Zod validation (Axios-based)
 * - ApiError: Custom error class for API errors
 * - schemas: Zod schemas for deriving TypeScript types
 *
 * Architecture:
 * - Authentication is handled by backend via HTTP-only session cookies
 * - Axios sends cookies with withCredentials: true
 * - Interceptors handle 401 redirects and add Accept-Language header
 *
 * Usage:
 *   import { zodiosApi } from '$lib/api';
 *   const brokers = await zodiosApi.list_brokers_api_v1_brokers_get();
 *
 * Types:
 *   import { schemas } from '$lib/api';
 *   type Broker = z.infer<typeof schemas.BRReadItem>;
 */

// =============================================================================
// ZODIOS CLIENT
// =============================================================================
export { zodiosApi, ApiError, axiosInstance } from './zodios-client';

// =============================================================================
// ZOD SCHEMAS (for deriving types in /lib/types/)
// =============================================================================
// Usage: import { schemas } from '$lib/api'; then z.infer<typeof schemas.X>
export { schemas } from './generated';
