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

/** Catalogue keys of the sign-in failures the login card translates. */
export type AuthErrorKey = 'auth.invalidCredentials' | 'auth.invalidInput' | 'auth.loginFailed';

/**
 * Why the last sign-in failed: a catalogue key, translated where it is drawn so it follows
 * the language, or the transport's own message, shown as it came.
 */
export type AuthError = {key: AuthErrorKey} | {message: string};

/**
 * Authentication state for the auth store.
 */
export interface AuthState {
    /** Currently authenticated user, or null if not logged in */
    user: AuthUser | null;
    /** Whether an auth operation is in progress */
    isLoading: boolean;
    /** Why the last sign-in failed, or null */
    error: AuthError | null;
    /** Whether initial auth check has completed */
    isInitialized: boolean;
}
