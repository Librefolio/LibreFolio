/**
 * API Module Exports
 *
 * This module provides:
 * - api: Base API client with auth/language headers
 * - ApiError: Custom error class for API errors
 * - schemas: Zod schemas for deriving TypeScript types
 *
 * Architecture:
 * - Authentication is handled by backend via HTTP-only session cookies
 * - Browser automatically sends cookies with credentials: 'include'
 * - This wrapper handles 401 redirects and adds Accept-Language header
 */

// Base client (temporary - will be replaced by Zodios wrapper)
export { api, apiCall, ApiError } from './client';
export type { ApiCallOptions } from './client';

// Re-export Zod schemas for deriving types in /lib/types/
// Usage: import { schemas } from '$lib/api'; then z.infer<typeof schemas.X>
export { schemas } from './generated';
