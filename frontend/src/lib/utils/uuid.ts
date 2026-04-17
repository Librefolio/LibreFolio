/**
 * UUID v4 generator with fallback for non-secure contexts.
 *
 * `crypto.randomUUID()` is only available in "secure contexts" (HTTPS or localhost).
 * When serving over plain HTTP on a remote server, it throws:
 *   "TypeError: crypto.randomUUID is not a function"
 *
 * This module provides a drop-in replacement that:
 * 1. Uses `crypto.randomUUID()` when available (fast, native)
 * 2. Falls back to `crypto.getRandomValues()` based UUID v4 (works everywhere)
 *
 * @module utils/uuid
 */

/**
 * Generate a UUID v4 string.
 *
 * @returns A random UUID like "550e8400-e29b-41d4-a716-446655440000"
 */
export function generateUUID(): string {
    // Prefer native API when available (secure context: HTTPS or localhost)
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        return crypto.randomUUID();
    }

    // Fallback: build UUID v4 from crypto.getRandomValues (works on HTTP too)
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);

    // Set version 4 (0100) in byte 6
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    // Set variant 10xx in byte 8
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
