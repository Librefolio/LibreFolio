/**
 * Shared classes for single-line text that should auto-scroll (not hard-clip, no fade, no
 * manual/hover interaction) when it overflows its container — used for asset/broker names
 * across cards, tables, and the asset detail title.
 *
 * `overflow-x-hidden` (not `-auto`): this is a fully automatic marquee (see
 * `actions/scrollOnOverflow.ts`), not a user-driven scroll area — hiding overflow entirely
 * means no scrollbar and no manual drag/swipe to fight with the animation, which drives the
 * same element's `scrollLeft` programmatically (works regardless of the `overflow` value).
 *
 * `overflow-scroll-marquee` is a plain marker class (no styling) — `scrollOnOverflow`
 * (Svelte template usages) and `attachOverflowMarqueeToDescendants` (raw-HTML table-cell
 * usages, e.g. ExposureTable/ContributionTable/AssetTable/TransactionsTable) both use it to
 * find/attach to the right elements.
 */
export const overflowScrollTextClass = 'block min-w-0 overflow-x-hidden overflow-y-hidden whitespace-nowrap overflow-scroll-marquee';
