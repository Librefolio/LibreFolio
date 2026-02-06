/**
 * User & Authentication Types
 *
 * Types for user authentication and profile management.
 * Derived from Zod schemas in generated.ts.
 */

import {z} from 'zod';
import {schemas} from '$lib/api/generated';

// =============================================================================
// TYPES DERIVED FROM ZOD SCHEMAS
// =============================================================================

/**
 * User information returned from authentication endpoints.
 * Used in login response, /auth/me, register response, etc.
 */
export type AuthUser = z.infer<typeof schemas.AuthUserResponse>;

/**
 * Response from POST /auth/login
 */
export type AuthLoginResponse = z.infer<typeof schemas.AuthLoginResponse>;

/**
 * Response from GET /auth/me
 */
export type AuthMeResponse = z.infer<typeof schemas.AuthMeResponse>;

/**
 * Response from POST /auth/register
 */
export type AuthRegisterResponse = z.infer<typeof schemas.AuthRegisterResponse>;

/**
 * Request body for POST /auth/login
 */
export type AuthLoginRequest = z.infer<typeof schemas.AuthLoginRequest>;

/**
 * Request body for POST /auth/register
 */
export type AuthRegisterRequest = z.infer<typeof schemas.AuthRegisterRequest>;

/**
 * Request body for PUT /auth/profile
 */
export type UpdateProfileRequest = z.infer<typeof schemas.UpdateProfileRequest>;

/**
 * Response from PUT /auth/profile
 */
export type UpdateProfileResponse = z.infer<typeof schemas.UpdateProfileResponse>;

// =============================================================================
// FRONTEND-ONLY TYPES
// =============================================================================

/**
 * Authentication state for the auth store.
 */
export interface AuthState {
    /** Currently authenticated user, or null if not logged in */
    user: AuthUser | null;
    /** Whether an auth operation is in progress */
    isLoading: boolean;
    /** Error message from last failed operation */
    error: string | null;
    /** Whether initial auth check has completed */
    isInitialized: boolean;
}
