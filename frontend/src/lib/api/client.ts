/**
 * API Client for LibreFolio
 *
 * Base wrapper for all API calls with:
 * - Session cookie authentication
 * - Language header sync
 * - Centralized error handling
 * - Timeout handling
 */
import { goto } from '$app/navigation';
import { browser } from '$app/environment';

// Get current language from localStorage or default to 'en'
function getCurrentLanguage(): string {
	if (!browser) return 'en';
	return localStorage.getItem('librefolio-locale') || 'en';
}

// Base URL - in production, API is served from same origin
const API_BASE = '/api/v1';

// Default timeout in milliseconds
const DEFAULT_TIMEOUT = 30000;

/**
 * Custom error class for API errors
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
}

/**
 * Options for API calls
 */
export interface ApiCallOptions extends Omit<RequestInit, 'body'> {
	timeout?: number;
	body?: unknown;
}

/**
 * Make an API call with automatic error handling and authentication
 */
export async function apiCall<T>(
	endpoint: string,
	options: ApiCallOptions = {}
): Promise<T> {
	const { timeout = DEFAULT_TIMEOUT, body, ...fetchOptions } = options;

	// Build URL
	const url = `${API_BASE}${endpoint}`;

	// Get current language for Accept-Language header
	const lang = getCurrentLanguage();

	// Setup abort controller for timeout
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), timeout);

	try {
		const response = await fetch(url, {
			...fetchOptions,
			signal: controller.signal,
			credentials: 'include', // Include session cookie
			headers: {
				'Content-Type': 'application/json',
				'Accept-Language': lang,
				...fetchOptions.headers
			},
			body: body ? JSON.stringify(body) : undefined
		});

		clearTimeout(timeoutId);

		// Handle common error cases
		if (!response.ok) {
			// Try to parse error response
			let errorData: unknown;
			try {
				errorData = await response.json();
			} catch {
				errorData = await response.text();
			}

			// Handle 401 Unauthorized - redirect to login
			if (response.status === 401) {
				if (browser) {
					goto('/login');
				}
				throw new ApiError(401, 'Unauthorized', errorData);
			}

			// Handle 403 Forbidden
			if (response.status === 403) {
				throw new ApiError(403, 'Forbidden', errorData);
			}

			// Handle 404 Not Found
			if (response.status === 404) {
				throw new ApiError(404, 'Not Found', errorData);
			}

			// Handle 422 Validation Error
			if (response.status === 422) {
				throw new ApiError(422, 'Validation Error', errorData);
			}

			// Handle other errors
			throw new ApiError(response.status, response.statusText, errorData);
		}

		// Parse successful response
		// Handle 204 No Content
		if (response.status === 204) {
			return undefined as T;
		}

		return await response.json();
	} catch (error) {
		clearTimeout(timeoutId);

		// Handle abort/timeout
		if (error instanceof Error && error.name === 'AbortError') {
			throw new ApiError(408, 'Request Timeout');
		}

		// Re-throw ApiError as-is
		if (error instanceof ApiError) {
			throw error;
		}

		// Wrap other errors
		throw new ApiError(0, 'Network Error', error);
	}
}

/**
 * Convenience methods for common HTTP verbs
 */
export const api = {
	get: <T>(endpoint: string, options?: Omit<ApiCallOptions, 'method' | 'body'>) =>
		apiCall<T>(endpoint, { ...options, method: 'GET' }),

	post: <T>(endpoint: string, body?: unknown, options?: Omit<ApiCallOptions, 'method' | 'body'>) =>
		apiCall<T>(endpoint, { ...options, method: 'POST', body }),

	put: <T>(endpoint: string, body?: unknown, options?: Omit<ApiCallOptions, 'method' | 'body'>) =>
		apiCall<T>(endpoint, { ...options, method: 'PUT', body }),

	patch: <T>(endpoint: string, body?: unknown, options?: Omit<ApiCallOptions, 'method' | 'body'>) =>
		apiCall<T>(endpoint, { ...options, method: 'PATCH', body }),

	delete: <T>(endpoint: string, options?: Omit<ApiCallOptions, 'method' | 'body'>) =>
		apiCall<T>(endpoint, { ...options, method: 'DELETE' })
};

export default api;
