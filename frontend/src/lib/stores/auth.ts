/**
 * Authentication Store
 *
 * Manages user authentication state and provides login/logout functions.
 * Uses session cookies for authentication (HttpOnly, managed by backend).
 */
import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import { goto } from '$app/navigation';
import { api, ApiError } from '$lib/api';

/**
 * User information returned from the server
 */
export interface AuthUser {
	id: number;
	username: string;
	email: string;
	is_active: boolean;
}

/**
 * Authentication state
 */
interface AuthState {
	user: AuthUser | null;
	isLoading: boolean;
	error: string | null;
	isInitialized: boolean;
}

const initialState: AuthState = {
	user: null,
	isLoading: false,
	error: null,
	isInitialized: false
};

/**
 * Create the authentication store
 */
function createAuthStore() {
	const { subscribe, set, update } = writable<AuthState>(initialState);

	return {
		subscribe,

		/**
		 * Login with username/email and password
		 */
		login: async (username: string, password: string): Promise<boolean> => {
			update(state => ({ ...state, isLoading: true, error: null }));

			try {
				const response = await api.post<{ user: AuthUser; message: string }>(
					'/auth/login',
					{ username, password }
				);

				update(state => ({
					...state,
					user: response.user,
					isLoading: false,
					error: null,
					isInitialized: true
				}));

				return true;
			} catch (error) {
				let errorMessage = 'Login failed';

				if (error instanceof ApiError) {
					if (error.status === 401) {
						errorMessage = 'Invalid username or password';
					} else if (error.status === 422) {
						errorMessage = 'Invalid input';
					} else {
						errorMessage = error.message;
					}
				}

				update(state => ({
					...state,
					user: null,
					isLoading: false,
					error: errorMessage,
					isInitialized: true
				}));

				return false;
			}
		},

		/**
		 * Logout current user
		 */
		logout: async (): Promise<void> => {
			update(state => ({ ...state, isLoading: true }));

			try {
				await api.post('/auth/logout');
			} catch (error) {
				// Ignore errors on logout - we'll clear state anyway
				console.warn('Logout error:', error);
			}

			set({
				user: null,
				isLoading: false,
				error: null,
				isInitialized: true
			});

			// Redirect to login
			if (browser) {
				goto('/login');
			}
		},

		/**
		 * Check if user is authenticated (verify session with server)
		 */
		checkAuth: async (): Promise<boolean> => {
			update(state => ({ ...state, isLoading: true }));

			try {
				const response = await api.get<{ user: AuthUser }>('/auth/me');

				update(state => ({
					...state,
					user: response.user,
					isLoading: false,
					error: null,
					isInitialized: true
				}));

				return true;
			} catch (error) {
				update(state => ({
					...state,
					user: null,
					isLoading: false,
					error: null,
					isInitialized: true
				}));

				return false;
			}
		},

		/**
		 * Clear any error message
		 */
		clearError: () => {
			update(state => ({ ...state, error: null }));
		},

		/**
		 * Reset store to initial state
		 */
		reset: () => {
			set(initialState);
		}
	};
}

// Create singleton store
export const auth = createAuthStore();

// Derived stores for convenience
export const currentUser = derived(auth, $auth => $auth.user);
export const isAuthenticated = derived(auth, $auth => $auth.user !== null);
export const isAuthLoading = derived(auth, $auth => $auth.isLoading);
export const authError = derived(auth, $auth => $auth.error);
export const isAuthInitialized = derived(auth, $auth => $auth.isInitialized);

/**
 * Helper to get current auth state synchronously
 */
export function getAuthState(): AuthState {
	return get(auth);
}

/**
 * Helper to check if user is authenticated synchronously
 */
export function isLoggedIn(): boolean {
	return get(isAuthenticated);
}

