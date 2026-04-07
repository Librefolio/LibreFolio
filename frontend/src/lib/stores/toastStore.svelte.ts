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

import { generateUUID } from '$lib/utils/uuid';

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

function show(variant: ToastVariant, message: string, duration?: number): string {
    const id = generateUUID();
    const ms = duration ?? DEFAULT_DURATION[variant];

    const toast: Toast = {id, variant, message, duration: ms, createdAt: Date.now()};

    if (ms > 0) {
        toast._timeout = setTimeout(() => dismiss(id), ms);
    }

    items = [...items, toast];
    return id;
}

function dismiss(id: string) {
    const toast = items.find(t => t.id === id);
    if (toast?._timeout) clearTimeout(toast._timeout);
    items = items.filter(t => t.id !== id);
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

