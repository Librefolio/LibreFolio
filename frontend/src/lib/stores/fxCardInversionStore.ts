/**
 * FX Card Inversion Store — Module-level Map that persists card inversion state
 * across SPA navigations (survives component mount/unmount within the same session).
 *
 * Used by FxCard to remember which pairs the user has inverted.
 * Plain Map (non-reactive) — each card reads on mount and writes on toggle.
 */

const invertedCards = new Map<string, boolean>();

/** Check if a card is inverted (default: false) */
export function isCardInverted(slug: string): boolean {
    return invertedCards.get(slug) ?? false;
}

/** Set or clear the inversion state for a card */
export function setCardInverted(slug: string, inverted: boolean): void {
    if (inverted) {
        invertedCards.set(slug, true);
    } else {
        invertedCards.delete(slug);
    }
}

