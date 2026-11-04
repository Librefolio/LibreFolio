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
import {zodValidationPlugin} from '@zodios/core';
import {createApiClient} from './generated';
import {reportApiFailure, requestPath} from './apiErrorConsole';
import {goto} from '$app/navigation';
import {browser} from '$app/environment';
import {debug} from '$lib/debug';
import {loginUrl} from '$lib/utils/internalPath';
import {notifyPortfolioMutation} from '$lib/stores/portfolio/portfolioMutation';
import {priceRefresh} from '$lib/features/price-refresh/priceRefresh';
import {instanceBlockState, isInstanceAwaitingRestoreError, isInstanceBlockedError, isInstanceRestoreInterruptedError} from '$lib/features/instance/instanceBlockState';
import {isUserLimitError, userLimitState} from '$lib/features/instance/userLimitState';

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
        serialize: serializeParams,
    },
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
        // The path only: a query string can carry a token (H-60)
        debug.log('API', `${config.method?.toUpperCase() || 'GET'} ${requestPath(config.url)}`);

        return config;
    },
    (error) => {
        return Promise.reject(error);
    },
);

// =============================================================================
// RESPONSE INTERCEPTOR
// =============================================================================

/**
 * The anonymous pages of a link — an invitation, the initial administrator's setup, a password reset, an email
 * verification — have no session to lose: a 401 there is the instance's block (P16), which the page receives.
 * The same pages as `_TOKEN_PATHS` in `backend/app/services/accounts/token_service.py`, the pages a link opens:
 * `test_account_tokens.py` checks that the two lists agree.
 */
const LINK_PAGES = new Set(['/setup', '/invite', '/reset-password', '/verify-email', '/confirm-email-change']);

function isLinkPage(pathname: string): boolean {
    return LINK_PAGES.has(pathname.length > 1 && pathname.endsWith('/') ? pathname.slice(0, -1) : pathname);
}

/**
 * Handle common error responses:
 * - 401 Unauthorized → redirect to login (not from `/` nor from the anonymous pages of a link)
 * - Other errors → wrap in ApiError
 */
axiosInstance.interceptors.response.use(
    (response) => {
        notifyPortfolioMutation(response.config.method, response.config.url, response.data);
        // While the server catches up on prices it says so on every response: «Updating prices…» (Z5).
        priceRefresh.observe(response.headers);
        return response;
    },
    (error: AxiosError) => {
        // One console line for an unexpected failure, without a word of its data (H-60): apiErrorConsole.ts
        reportApiFailure(error);

        // A 401 means the session is gone: go to the login, carrying the page to come back to.
        // On the root the login is already there, and a failed sign-in answers 401 too; a link page has no session.
        if (error.response?.status === 401) {
            if (browser && window.location.pathname !== '/' && !isLinkPage(window.location.pathname)) {
                debug.log('API', '401 Unauthorized - redirecting to login');
                goto(loginUrl(window.location.pathname + window.location.search));
            }
        }

        // A 423 `instance_blocked`: the hosting provider blocked this instance, and the layout shows the block page.
        if (isInstanceBlockedError(error.response?.status, error.response?.data)) {
            instanceBlockState.markBlocked();
        }

        // A 423 `user_limit_exceeded` (A5-7): the active accounts outnumber the plan, and the layout shows the choice (an
        // administrator) or the wait (anyone else).
        if (isUserLimitError(error.response?.status, error.response?.data)) {
            userLimitState.markExceeded();
        }

        // A 423 `instance_awaiting_restore` (H-62: the hosting panel is restoring this instance) or
        // `instance_restore_interrupted` (B-33: the state of the restore cannot be read). Read the instance's
        // configuration again, so the root layout's gate shows its page even when it was read before the state began. A dynamic import: the configuration is a runes module that imports this client.
        if (isInstanceAwaitingRestoreError(error.response?.status, error.response?.data) || isInstanceRestoreInterruptedError(error.response?.status, error.response?.data)) {
            void import('$lib/features/instance/instanceConfig.svelte').then(({instanceConfig}) => instanceConfig.load({force: true}));
        }

        // Let the error propagate - Zodios will handle it
        return Promise.reject(error);
    },
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
    validate: 'response', // Validate responses with Zod, trust request params
});

// Zodios's own response check, replaced under its name so that it keeps its place in the plugin chain (H-60): an answer
// that breaks its schema is written to the console (apiErrorConsole.ts), then rejected as before.
const responseValidation = zodValidationPlugin({validate: 'response', transform: true, sendDefaults: false});
const validateResponse = responseValidation.response;
zodiosApi.use({
    name: 'zod-validation',
    request: responseValidation.request,
    response: validateResponse
        ? async (api, config, response) => {
              try {
                  return await validateResponse(api, config, response);
              } catch (error) {
                  reportApiFailure(error);
                  throw error;
              }
          }
        : undefined,
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
