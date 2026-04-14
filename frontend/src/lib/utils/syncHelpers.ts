/**
 * Shared sync helpers — used by SyncModalBase, FxSyncModal, AssetSyncModal, PageSyncAllModal.
 *
 * Centralises:
 *  - SyncResult interface (common fields for FX and Asset sync results)
 *  - SyncSection interface (multi-section sync modal support)
 *  - SyncStatus type
 *  - Status icons and colors
 *  - Time formatting utilities
 */

import type {Component, Snippet} from 'svelte';
import {AlertCircle, AlertTriangle, Check, SkipForward} from 'lucide-svelte';
import type {LegDetail} from '$lib/utils/providerHelpers';

// =========================================================================
// Sync status type and result interface
// =========================================================================

export type SyncStatus = 'ok' | 'partial' | 'failed' | 'skipped';

export interface SyncResult {
    id: string;               // pair slug for FX, asset_id.toString() for Asset
    status: SyncStatus;
    points_fetched: number;
    points_changed: number;
    provider_used?: string | null;
    message?: string | null;
    errors?: string[];
    elapsed_ms?: number;
    // FX-specific (multi-provider chains):
    detail?: LegDetail[];
    // FA-specific (OHLCV granularity):
    inserted_count?: number;
    updated_count?: number;
    // Corporate events:
    events_fetched?: number;
    events_changed?: number;
}

// =========================================================================
// Sync section — multi-section sync modal support
// =========================================================================

/**
 * A sync section defines one group of items to sync in SyncModalBase.
 * SyncModalBase renders one titled section per SyncSection and runs
 * all sections in parallel with a unified countdown.
 */
export interface SyncSection {
    /** Section identifier (e.g. 'assets', 'fx') */
    id: string;
    /** Section title displayed as header (e.g. '📊 Assets') */
    title: string;
    /** Callback to perform the actual sync — returns results */
    doSyncFn: (targetIds: string[]) => Promise<SyncResult[]>;
    /** All target IDs to sync in this section */
    targetIds: string[];
    /** Snippet for rendering each result row (specialization-specific) */
    resultRow: Snippet<[SyncResult, boolean]>;
    /** Count label for summary footer (e.g. 'assets', 'pairs') */
    countLabel: string;
}

// =========================================================================
// Status icons and colors
// =========================================================================

export const STATUS_ICONS: Record<SyncStatus, Component> = {
    ok: Check as unknown as Component,
    partial: AlertTriangle as unknown as Component,
    failed: AlertCircle as unknown as Component,
    skipped: SkipForward as unknown as Component,
};

export const STATUS_COLORS: Record<SyncStatus, string> = {
    ok: 'text-emerald-500',
    partial: 'text-amber-500',
    failed: 'text-red-500',
    skipped: 'text-gray-400',
};

// =========================================================================
// Time formatting utilities
// =========================================================================

/** Format elapsed milliseconds to human-readable string. */
export function formatElapsed(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
}

/** Format seconds to mm:ss or Ns. */
export function formatTime(sec: number): string {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return m > 0 ? `${m}:${s.toString().padStart(2, '0')}` : `${s}s`;
}

