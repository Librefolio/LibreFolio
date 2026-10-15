import {themed} from '$lib/theme/themePair';
import {LOT_STATE_COLORS} from '$lib/theme/chartTheme';

/**
 * Shared visual encoding for a FIFO lot's open/closed state, used by BOTH the per-lot
 * performance bubbles' center dot (LotWacPriceChart) and the "Aperti | Chiusi" filter buttons
 * (LotGanttChart) so the two stay in colour sync. A lot is:
 *  - OPEN     → still fully open (open == original quantity)
 *  - PARTIAL  → partially closed (0 < open < original)
 *  - CLOSED   → fully closed (open <= 0)
 */
export type LotDisplayState = 'OPEN' | 'PARTIAL' | 'CLOSED';

/** Derive the display state from the open vs original quantity. */
export function lotDisplayState(openQuantity: number, originalQuantity: number): LotDisplayState {
    if (!(openQuantity > 0)) return 'CLOSED';
    if (originalQuantity > 0 && openQuantity < originalQuantity) return 'PARTIAL';
    return 'OPEN';
}

/** Theme-aware fill colour for a lot state (also the Gantt filter button colours). */
export function lotStateColor(state: LotDisplayState, dark: boolean): string {
    switch (state) {
        case 'OPEN':
            return themed(LOT_STATE_COLORS.open, dark); // sky
        case 'PARTIAL':
            return themed(LOT_STATE_COLORS.partial, dark); // amber
        case 'CLOSED':
            return themed(LOT_STATE_COLORS.closed, dark); // slate
    }
}

/** ECharts scatter symbol that encodes the lot state by shape (color-blind safe). */
export function lotStateSymbol(state: LotDisplayState): 'circle' | 'diamond' | 'rect' {
    switch (state) {
        case 'OPEN':
            return 'circle';
        case 'PARTIAL':
            return 'diamond';
        case 'CLOSED':
            return 'rect';
    }
}

/** The two filter buckets a lot falls into for the Gantt "Aperti | Chiusi" toggle. */
export function lotIsOpenBucket(state: LotDisplayState): boolean {
    return state !== 'CLOSED';
}
