/**
 * Authentication Store
 *
 * Manages user authentication state and provides login/logout functions.
 * Uses session cookies for authentication (HttpOnly, managed by backend).
 *
 * Now uses Zodios client for type-safe API calls with Zod validation.
 */
import {derived, get, writable} from 'svelte/store';
import {browser} from '$app/environment';
import {goto} from '$app/navigation';
import {zodiosApi} from '$lib/api';
import {debug} from '$lib/debug';
import type {AuthState, AuthUser} from '$lib/types';
import {isAxiosError} from 'axios';
import {currentLanguage} from '$lib/stores/language';
import {userSettings} from '$lib/stores/settings';

// Re-export types for backward compatibility
export type {AuthUser, AuthState} from '$lib/types';

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
    const {subscribe, set, update} = writable<AuthState>(initialState);

    return {
        subscribe,

        /**
         * Login with username/email and password
         */
        login: async (username: string, password: string): Promise<boolean> => {
            update(state => ({...state, isLoading: true, error: null}));

            try {
                debug.log('AuthStore', 'Attempting login for:', username);
                const response = await zodiosApi.login_api_v1_auth_login_post({
                    username,
                    password
                });
                debug.log('AuthStore', 'Login response:', response);

                update(state => ({
                    ...state,
                    user: response.user,
                    isLoading: false,
                    error: null,
                    isInitialized: true
                }));

                // Apply user settings from login response (Bug 1 fix)
                // Handle potential array type from openapi-zod-client
                const settings = Array.isArray(response.user_settings)
                    ? response.user_settings[0]
                    : response.user_settings;

                if (settings && browser) {
                    debug.log('AuthStore', 'Applying user settings:', settings);

                    // Apply language preference
                    if (settings.language) {
                        currentLanguage.set(settings.language as 'en' | 'it' | 'fr' | 'es');
                    }

                    // Apply theme preference
                    if (settings.theme) {
                        const theme = settings.theme;
                        if (theme === 'dark') {
                            document.documentElement.classList.add('dark');
                            localStorage.setItem('theme', 'dark');
                        } else if (theme === 'light') {
                            document.documentElement.classList.remove('dark');
                            localStorage.setItem('theme', 'light');
                        } else {
                            // auto mode - match system preference
                            localStorage.setItem('theme', 'auto');
                            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                            if (prefersDark) {
                                document.documentElement.classList.add('dark');
                            } else {
                                document.documentElement.classList.remove('dark');
                            }
                        }
                    }

                    // Cache settings to localStorage for userSettings store
                    // Bug 2 fix: Also update the store directly so it's available immediately
                    userSettings.setDirect(settings);
                }

                return true;
            } catch (error) {
                debug.log('AuthStore', 'Login error:', error);
                let errorMessage = 'Login failed';

                if (isAxiosError(error)) {
                    debug.log('AuthStore', 'Axios error status:', error.response?.status);
                    debug.log('AuthStore', 'Axios error data:', error.response?.data);
                    if (error.response?.status === 401) {
                        errorMessage = 'Invalid username or password';
                    } else if (error.response?.status === 422) {
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
            update(state => ({...state, isLoading: true}));

            try {
                await zodiosApi.logout_api_v1_auth_logout_post(undefined);
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
                goto('/');
            }
        },

        /**
         * Check if user is authenticated (verify session with server)
         */
        checkAuth: async (): Promise<boolean> => {
            debug.log('AuthStore', 'checkAuth started');
            update(state => ({...state, isLoading: true}));

            try {
                const response = await zodiosApi.get_me_api_v1_auth_me_get();

                debug.log('AuthStore', 'checkAuth success', response.user?.username);
                update(state => ({
                    ...state,
                    user: response.user,
                    isLoading: false,
                    error: null,
                    isInitialized: true
                }));

                return true;
            } catch (error) {
                debug.log('AuthStore', 'checkAuth failed', error);
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
            update(state => ({...state, error: null}));
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

