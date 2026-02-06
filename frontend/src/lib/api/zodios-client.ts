/**
 * Zodios API Client for LibreFolio
 *
 * Type-safe API client built on Zodios (which uses Axios internally).
 *
 * Features:
 * - Session cookie authentication (withCredentials: true)
 * - Language header sync (Accept-Language via interceptor)
 * - Centralized error handling
 * - Timeout handling
 * - Zod validation of responses
 *
 * @see https://github.com/ecyrbe/zodios
 */
import axios, {type AxiosError, type InternalAxiosRequestConfig} from 'axios';
import {createApiClient} from './generated';
import {goto} from '$app/navigation';
import {browser} from '$app/environment';
import {debug} from '$lib/debug';

// =============================================================================
// CONFIGURATION
// =============================================================================

// Base URL - use '/' because endpoints in generated.ts already include full path
// (e.g., "/api/v1/auth/login"). Zodios requires a non-empty baseUrl.
const API_BASE = '/';

// Default timeout in milliseconds
const DEFAULT_TIMEOUT = 30000;

// Get current language from localStorage or default to 'en'
function getCurrentLanguage(): string {
    if (!browser) return 'en';
    return localStorage.getItem('librefolio-locale') || 'en';
}

// =============================================================================
// CUSTOM AXIOS INSTANCE
// =============================================================================

/**
 * Custom params serializer that serializes arrays as repeated query params.
 * Example: { broker_ids: [1, 2] } → "broker_ids=1&broker_ids=2"
 * Instead of default Axios behavior: "broker_ids[]=1&broker_ids[]=2"
 *
 * This matches FastAPI's expected format for List[int] query parameters.
 */
function serializeParams(params: Record<string, unknown>): string {
    const searchParams = new URLSearchParams();

    for (const [key, value] of Object.entries(params)) {
        if (value === undefined || value === null) {
            continue;
        }

        if (Array.isArray(value)) {
            // Serialize arrays as repeated params: key=1&key=2
            for (const item of value) {
                if (item !== undefined && item !== null) {
                    searchParams.append(key, String(item));
                }
            }
        } else {
            searchParams.append(key, String(value));
        }
    }

    return searchParams.toString();
}

/**
 * Custom Axios instance with LibreFolio configuration.
 * This is passed to Zodios to use instead of creating its own.
 *
 * Note: No baseURL needed because endpoints already include full path (e.g., /api/v1/auth/login)
 * Note: Content-Type is NOT set globally - Axios auto-detects it based on body type:
 *       - JSON body → application/json
 *       - FormData → multipart/form-data with correct boundary
 */
const axiosInstance = axios.create({
    timeout: DEFAULT_TIMEOUT,
    withCredentials: true, // Include session cookies in requests
    paramsSerializer: {
        serialize: serializeParams
    }
});

// =============================================================================
// REQUEST INTERCEPTOR
// =============================================================================

/**
 * Add Accept-Language header to every request based on user's locale preference.
 */
axiosInstance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const lang = getCurrentLanguage();
        config.headers.set('Accept-Language', lang);

        // Debug logging
        debug.log('API', `${config.method?.toUpperCase() || 'GET'} ${config.url}`);

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// =============================================================================
// RESPONSE INTERCEPTOR
// =============================================================================

/**
 * Handle common error responses:
 * - 401 Unauthorized → redirect to login
 * - Other errors → wrap in ApiError
 */
axiosInstance.interceptors.response.use(
    (response) => {
        // Successful response - return as-is
        return response;
    },
    (error: AxiosError) => {
        // Handle 401 Unauthorized - redirect to login
        if (error.response?.status === 401) {
            if (browser) {
                debug.log('API', '401 Unauthorized - redirecting to login');
                goto('/');
            }
        }

        // Let the error propagate - Zodios will handle it
        return Promise.reject(error);
    }
);

// =============================================================================
// ZODIOS CLIENT
// =============================================================================

/**
 * Type-safe API client using Zodios.
 *
 * All endpoints are auto-generated from OpenAPI schema with full TypeScript support.
 * Responses are validated at runtime using Zod schemas.
 *
 * @example
 * ```typescript
 * // List all brokers
 * const brokers = await zodiosApi.list_brokers_api_v1_brokers_get();
 *
 * // Get a specific broker
 * const broker = await zodiosApi.get_broker_api_v1_brokers__broker_id__get({
 *   params: { broker_id: 1 }
 * });
 *
 * // Create a broker
 * const newBroker = await zodiosApi.create_broker_api_v1_brokers_post({
 *   name: "My Broker",
 *   allow_cash_overdraft: false,
 *   allow_asset_shorting: false
 * });
 * ```
 */
export const zodiosApi = createApiClient(API_BASE, {
    axiosInstance,
    validate: 'response' // Validate responses with Zod, trust request params
});

// =============================================================================
// ERROR CLASSES (for backward compatibility)
// =============================================================================

/**
 * Custom error class for API errors.
 * Maintained for backward compatibility during migration.
 */
export class ApiError extends Error {
    status: number;
    statusText: string;
    data?: unknown;

    constructor(status: number, statusText: string, data?: unknown) {
        super(`API Error: ${status} ${statusText}`);
        this.name = 'ApiError';
        this.status = status;
        this.statusText = statusText;
        this.data = data;
    }

    /**
     * Create ApiError from Axios error
     */
    static fromAxiosError(error: AxiosError): ApiError {
        const status = error.response?.status || 0;
        const statusText = error.response?.statusText || error.message || 'Network Error';
        const data = error.response?.data;
        return new ApiError(status, statusText, data);
    }
}

// =============================================================================
// EXPORTS
// =============================================================================

export {axiosInstance};
export default zodiosApi;

