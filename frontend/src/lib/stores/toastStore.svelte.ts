/**
 * Toast Notification Store (Svelte 5 Runes)
 *
 * Lightweight toast system for transient user notifications.
 * Uses $state for reactivity. Auto-dismisses after configurable duration.
 *
 * Usage:
 *   import { toasts } from '$lib/stores/toastStore.svelte';
 *   toasts.success('Operation completed');
 *   toasts.error('Something went wrong', 10000);
 *   toasts.warning('Partial data');
 *   toasts.info('Note: ...');
 */

import {generateUUID} from '$lib/utils/uuid';
import {debug} from '$lib/debug';

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
    id: string;
    variant: ToastVariant;
    message: string;
    /** Total duration in ms (for countdown bar) */
    duration: number;
    /** Timestamp when toast was created (for countdown bar) */
    createdAt: number;
    /** Auto-dismiss timeout handle (for cleanup) */
    _timeout?: ReturnType<typeof setTimeout>;
}

const DEFAULT_DURATION: Record<ToastVariant, number> = {
    success: 8000,
    error: 15000,
    warning: 10000,
    info: 8000,
};

let items = $state<Toast[]>([]);

/**
 * Strip HTML/SVG markup from a toast message so the console log stays
 * readable. Toast messages often embed inline icons (<svg>…</svg>),
 * coloured badges (<span class="…">…</span>) and <img> flags that are
 * meaningful in the UI but pure noise in DevTools.
 *
 * Strategy:
 *   1. Drop entire <svg>…</svg> and <img …/> nodes (no useful text inside).
 *   2. Remove any remaining tags, keeping their text content.
 *   3. Decode the handful of HTML entities we actually emit.
 *   4. Collapse runs of whitespace into a single space.
 *
 * Pure string-based — no DOM access — so it is safe in SSR and cheap.
 */
function stripHtmlForLog(message: string): string {
    if (!message || message.indexOf('<') === -1) return message;
    return message
        .replace(/<svg\b[^>]*>[\s\S]*?<\/svg>/gi, '')
        .replace(/<img\b[^>]*\/?>(?:<\/img>)?/gi, '')
        .replace(/<\/?[a-z][^>]*>/gi, '')
        .replace(/&nbsp;/g, ' ')
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/\s+/g, ' ')
        .trim();
}

// #R4-5: console-log gate via the shared ``$lib/debug`` helper. Active when:
//   - VITE_DEBUG=true (``./dev.py server --debug`` / ``npm run build:debug``)
//   - OR the app runs under ``vite dev`` (``import.meta.env.DEV``).
// In production builds the whole branch is tree-shaken away. This is the
// *single* centralised place where every toast is mirrored to the browser
// console — so developers can scroll back the full history even after toasts
// auto-dismiss.

function show(variant: ToastVariant, message: string, duration?: number): string {
    const id = generateUUID();
    const ms = duration ?? DEFAULT_DURATION[variant];

    // Mirror every toast to the browser console at the matching console level
    // (error/warn/info/log) so DevTools filtering works as expected.
    // The toast ``message`` often contains inline HTML (flags, badges, lucide
    // <svg> icons) which is meaningful in the UI but pure noise in the console.
    // Strip tags and collapse whitespace for a clean, readable log line.
    const variantMethod = variant === 'error' ? 'error' : variant === 'warning' ? 'warn' : variant === 'info' ? 'info' : 'log';
    debug[variantMethod]('Toast', `[${variant}]`, stripHtmlForLog(message));

    const toast: Toast = {id, variant, message, duration: ms, createdAt: Date.now()};

    if (ms > 0) {
        toast._timeout = setTimeout(() => dismiss(id), ms);
    }

    items = [...items, toast];
    return id;
}

function dismiss(id: string) {
    const toast = items.find((t) => t.id === id);
    if (toast?._timeout) clearTimeout(toast._timeout);
    items = items.filter((t) => t.id !== id);
}

function clear() {
    for (const t of items) {
        if (t._timeout) clearTimeout(t._timeout);
    }
    items = [];
}

export const toasts = {
    get items() {
        return items;
    },

    show,
    dismiss,
    clear,

    success: (message: string, duration?: number) => show('success', message, duration),
    error: (message: string, duration?: number) => show('error', message, duration),
    warning: (message: string, duration?: number) => show('warning', message, duration),
    info: (message: string, duration?: number) => show('info', message, duration),
};
