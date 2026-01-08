/**
 * Server Hooks
 *
 * Handles server-side request processing:
 * - Session validation
 * - Route protection (redirect to login if not authenticated)
 */
import type { Handle } from '@sveltejs/kit';
import { redirect } from '@sveltejs/kit';

/**
 * Routes that don't require authentication
 */
const PUBLIC_ROUTES = [
	'/login',
	'/register',
	'/forgot-password',
	'/reset-password',
	'/api'  // API routes handle their own auth
];

/**
 * Check if a path is a public route
 */
function isPublicRoute(path: string): boolean {
	return PUBLIC_ROUTES.some(route => path.startsWith(route) || path === '/');
}

/**
 * Main request handler
 */
export const handle: Handle = async ({ event, resolve }) => {
	const { url, cookies } = event;
	const path = url.pathname;

	// Skip auth check for public routes
	if (isPublicRoute(path)) {
		return resolve(event);
	}

	// Check for session cookie
	// Note: The actual session validation is done by the backend API
	// Here we just check if the cookie exists as a quick client-side check
	const sessionCookie = cookies.get('session');

	if (!sessionCookie) {
		// No session - redirect to login
		throw redirect(303, `/login?redirect=${encodeURIComponent(path)}`);
	}

	// Session exists - let the request proceed
	// The backend will validate the session on API calls
	return resolve(event);
};

