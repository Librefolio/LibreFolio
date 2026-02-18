/**
 * Application Version
 *
 * Version is injected at build time from git describe via Vite.
 */

// Declared by Vite at build time (see vite.config.ts)
declare const __APP_VERSION__: string;

/**
 * Application version from git tags.
 * Format: 'v1.2.3' (on tag) or 'v1.2.3-5-gabcdef' (commits after tag)
 */
export const APP_VERSION: string = typeof __APP_VERSION__ !== 'undefined'
    ? __APP_VERSION__
    : 'unknown';

/**
 * Check if this is a release version (exactly on a tag)
 */
export function isReleaseVersion(): boolean {
    const clean = APP_VERSION.replace('-dirty', '');
    return !clean.includes('-');
}

/**
 * Check if there are uncommitted changes
 */
export function isDirtyVersion(): boolean {
    return APP_VERSION.endsWith('-dirty');
}

