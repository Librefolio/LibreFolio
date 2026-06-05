/**
 * Shared helpers for broker role icons, colors, labels, and access checks.
 *
 * Extracted from BrokerSharingModal (Step 1, Plan B — Phase 07).
 * Consumed by BrokerBadge, BrokerSearchSelect, TransactionsTable, BulkModal.
 */
import {Crown, Pencil, Eye, Lock} from 'lucide-svelte';

// =========================================================================
// Role icon / color / label
// =========================================================================

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function getRoleIcon(role: string | null | undefined): any {
    switch (role) {
        case 'OWNER':
            return Crown;
        case 'EDITOR':
            return Pencil;
        case 'VIEWER':
            return Eye;
        default:
            return Lock;
    }
}

export function getRoleIconColor(role: string | null | undefined): string {
    switch (role) {
        case 'OWNER':
            return 'text-amber-500';
        case 'EDITOR':
            return 'text-blue-500';
        case 'VIEWER':
            return 'text-gray-400';
        default:
            return 'text-red-400';
    }
}

export function getRoleShortLabel(role: string | null | undefined, t: (key: string) => string): string {
    switch (role) {
        case 'OWNER':
            return t('brokers.sharing.roleOwnerShort');
        case 'EDITOR':
            return t('brokers.sharing.roleEditorShort');
        case 'VIEWER':
            return t('brokers.sharing.roleViewerShort');
        default:
            return '—';
    }
}

// =========================================================================
// Access predicates
// =========================================================================

/** True if user can mutate (edit/delete) transactions on this broker. */
export function canEditWithRole(role: string | null | undefined): boolean {
    return role === 'OWNER' || role === 'EDITOR';
}

// =========================================================================
// Paired access level
// =========================================================================

export type PairedAccessLevel = 'full' | 'viewer' | 'none';

const ROLE_RANK: Record<string, number> = {OWNER: 3, EDITOR: 2, VIEWER: 1};

export function getRoleRank(role: string | null | undefined): number {
    return role ? (ROLE_RANK[role] ?? 0) : 0;
}

/**
 * SVG path data for inline HTML rendering (BulkModal cells etc.).
 * Mirrors the lucide icons Crown/Pencil/Eye/Lock at 16×16.
 */
export const ROLE_SVG: Record<string, string> = {
    OWNER: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z"/><path d="M5.21 16.5h13.58"/></svg>',
    EDITOR: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/></svg>',
    VIEWER: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/></svg>',
    LOCKED: '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
};

/** Get inline SVG HTML for a role (for use in HTML string cells). */
export function getRoleSvgHtml(role: string | null | undefined): string {
    const color = getRoleIconColor(role);
    const svg = ROLE_SVG[role ?? ''] ?? ROLE_SVG.LOCKED;
    return `<span class="${color} inline-flex align-middle ml-0.5">${svg}</span>`;
}
