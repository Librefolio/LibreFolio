/**
 * Debug logging utility for LibreFolio frontend.
 *
 * Uses compile-time environment variable substitution.
 * When VITE_DEBUG is not set or false, the minifier will eliminate
 * all debug code as dead code (tree shaking).
 *
 * Usage:
 *   import { debug } from '$lib/debug';
 *   debug.log('MyComponent', 'message', data);
 *   debug.warn('MyComponent', 'warning');
 *   debug.error('MyComponent', 'error', error);
 *
 * Enable debug mode:
 *   VITE_DEBUG=true npm run build
 *   or in .env.local: VITE_DEBUG=true
 */

// This constant is replaced at compile time by Vite
// When false, the entire debug object becomes a no-op and gets tree-shaken
const DEBUG_ENABLED = import.meta.env.VITE_DEBUG === 'true';

type LogLevel = 'log' | 'warn' | 'error' | 'info';

interface DebugLogger {
    log: (component: string, ...args: unknown[]) => void;
    warn: (component: string, ...args: unknown[]) => void;
    error: (component: string, ...args: unknown[]) => void;
    info: (component: string, ...args: unknown[]) => void;
    group: (component: string, label: string) => void;
    groupEnd: () => void;
    time: (label: string) => void;
    timeEnd: (label: string) => void;
}

function createLogger(level: LogLevel): (component: string, ...args: unknown[]) => void {
    if (!DEBUG_ENABLED) {
        // Return no-op function - will be eliminated by minifier
        return () => {
        };
    }

    return (component: string, ...args: unknown[]) => {
        const prefix = `[${component}]`;
        console[level](prefix, ...args);
    };
}

/**
 * Debug logger object.
 * All methods are no-ops when VITE_DEBUG is not enabled,
 * and the minifier will eliminate the dead code.
 */
export const debug: DebugLogger = {
    log: createLogger('log'),
    warn: createLogger('warn'),
    error: createLogger('error'),
    info: createLogger('info'),

    group: DEBUG_ENABLED
        ? (component: string, label: string) => console.group(`[${component}] ${label}`)
        : () => {
        },

    groupEnd: DEBUG_ENABLED
        ? () => console.groupEnd()
        : () => {
        },

    time: DEBUG_ENABLED
        ? (label: string) => console.time(label)
        : () => {
        },

    timeEnd: DEBUG_ENABLED
        ? (label: string) => console.timeEnd(label)
        : () => {
        },
};

/**
 * Check if debug mode is enabled.
 * Useful for conditional rendering of debug UI elements.
 */
export const isDebugEnabled = (): boolean => DEBUG_ENABLED;

/**
 * Assert a condition in debug mode.
 * Throws in debug mode, no-op in production.
 */
export function debugAssert(condition: boolean, message: string): void {
    if (DEBUG_ENABLED && !condition) {
        throw new Error(`Assertion failed: ${message}`);
    }
}
