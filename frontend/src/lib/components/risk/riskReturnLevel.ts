/**
 * riskReturnLevel — the decisions behind `RiskReturnLevel.svelte`, the one table, chart
 * and set of notes that answer "what did each pay for its risk?" on every page that asks.
 *
 * Two pages ask it: the portfolio's L3 (Dashboard and a broker's page) and Asset Global's
 * L3°. They were two components until the developer's review of 05/10/2026 asked for one,
 * "così che nel tempo se aggiorniamo uno aggiorniamo entrambi". What still differs is what
 * each payload carries, and that is said here, as capabilities, rather than as a page name.
 *
 * ⚠️ A CAPABILITY IS DECLARED, NEVER INFERRED FROM THE VALUES. "Some row has a beta" is not
 * "this page measures beta": with a benchmark chosen and every beta undefined, the lab still
 * shows the column, with its dashes, because a dash that explains itself is an answer and a
 * missing column is not. So each column, and each note that depends on one, is switched by
 * a flag the caller states (agreed with the lab's owner, 06/10/2026).
 */
import type {AssetSetTableRow} from './assetSetTable';

/**
 * One asset of the table. The lab's `AssetSetPaidRow` is one as it stands, so the lab
 * hands its rows over unchanged; the portfolio adds the weight and leaves the ratios out.
 */
export interface RiskReturnRow extends AssetSetTableRow {
    /** Annualised volatility, as a fraction. */
    volatility: number | null;
    /** The period's average return, scaled to a year, as a fraction. */
    expectedReturn: number | null;
    /** Share of the portfolio, `0..1`. Only a portfolio has one. */
    weight?: number | null;
    /**
     * The ratios. A figure reads three ways: a number; `null`, measured and not measurable —
     * the lab's dash with its blank note; `undefined`, not calculated here (yet) — a dash that
     * says so, rather than claim a measurement failed that was never attempted.
     */
    sharpe?: number | null;
    sortino?: number | null;
    /** Against the shared benchmark; only where one applies. */
    beta?: number | null;
    correlation?: number | null;
    /**
     * This asset is the benchmark itself (the lab's D371): its beta and correlation are
     * then not blanks but inapplicable, and their dash says so.
     */
    isReference?: boolean;
    /**
     * A reference the table opens with, tinted like its dot: the portfolio itself, or the
     * benchmark (developer's review of 06/10/2026). Absent on an ordinary asset row. Reference
     * rows open the table but sort with the others when the reader sorts (his choice).
     */
    role?: 'portfolio' | 'benchmark';
    /**
     * The row was added for the reference rather than being one of the page's assets: the
     * portfolio always, a benchmark nobody holds or selected. An added row takes a `ref-` id and
     * `-ref-` cells and stays out of the asset count, so every per-asset count stays one per
     * asset (agreed with the lab's owner, 06/10/2026). A reference that is one of the assets —
     * the lab's D371, a benchmark the reader holds — is not added: it keeps its id and its cells,
     * and only moves up and takes the tint.
     */
    added?: boolean;
}

/** The table's id for a row: an asset's id, or `ref-portfolio` / `ref-<assetId>` for an added reference. */
export function rowIdOf(row: RiskReturnRow): string {
    if (!row.added) return String(row.assetId);
    return row.role === 'portfolio' ? 'ref-portfolio' : `ref-${row.assetId}`;
}

/**
 * The chart's id for the dot a row stands for: `portfolio`, `benchmark` for an added benchmark
 * (a reference nobody holds has a dot of its own), and `asset-<id>` for every asset — the
 * benchmark among them when it is one.
 */
export function pointIdOf(row: RiskReturnRow): string {
    if (row.role === 'portfolio') return 'portfolio';
    if (row.added) return 'benchmark';
    return `asset-${row.assetId}`;
}

/** The row a dot stands for, or `null` when it has none. */
export function rowIdForPoint(pointId: string, rows: readonly RiskReturnRow[]): string | null {
    const row = rows.find((candidate) => pointIdOf(candidate) === pointId);
    return row ? rowIdOf(row) : null;
}

/** The order the table opens in: the portfolio, then the benchmark, then the rest as the page gave them. */
export function referenceRowsFirst<T extends RiskReturnRow>(rows: readonly T[]): T[] {
    const rank = (row: T): number => (row.role === 'portfolio' ? 0 : row.role === 'benchmark' ? 1 : 2);
    return rows
        .map((row, index) => ({row, index}))
        .sort((left, right) => rank(left.row) - rank(right.row) || left.index - right.index)
        .map(({row}) => row);
}

/** DataTable's column title (its `th`): 12 px semibold, upper-case, 0.025em apart. */
export const HEADER_FONT = '600 12px';
const HEADER_LETTER_SPACING_PX = 0.3;
/** What DataTable draws around a title: its padding (8 + 8), the gap (4) and the sort icon (14), plus 2 so rounding never clips a letter. */
const HEADER_CHROME_PX = 36;

/**
 * The width a column needs to show its title on one line, in px. DataTable writes its titles
 * upper-case and never wraps them, so a column narrower than its title spills it over the next
 * one. Measured in the reader's language (`measure` gets the upper-case text in `HEADER_FONT`),
 * so a short title opens a narrow column (developer's review of 06/10/2026: «peso è troppo
 * larga»).
 */
export function headerWidth(title: string, measure: (text: string) => number): number {
    const text = title.toLocaleUpperCase();
    return Math.ceil(measure(text) + HEADER_LETTER_SPACING_PX * text.length) + HEADER_CHROME_PX;
}

/** What the page's payload carries, as the columns and notes that depend on it. */
export interface RiskReturnCapabilities {
    /** Each row has a weight in a portfolio: a weight column, and the dots are sized by it. */
    weight?: boolean;
    /** Sortino and Sharpe were measured per asset. */
    ratios?: boolean;
    /** A benchmark applies: beta and correlation per asset. */
    benchmark?: boolean;
}

/** What the chart leaves out, as shares of the whole. Only a portfolio has a whole. */
export interface RiskReturnOutside {
    cash: number | null;
    unpriced: number | null;
}

/** One line of the notes under the chart. */
export type RiskReturnNote = 'outside' | 'above' | 'return' | 'priceOnly' | 'line' | 'size';

export interface RiskReturnNotesInput {
    /** Which dot the line runs through (`capitalMarketLineAnchor`), or `null` when none is drawn. */
    lineAnchor: 'benchmark' | 'portfolio' | null;
    capabilities: RiskReturnCapabilities;
    outside?: RiskReturnOutside | null;
}

/** A share counts as present only when it is a real, strictly positive number. */
function present(share: number | null | undefined): boolean {
    return typeof share === 'number' && Number.isFinite(share) && share > 0;
}

/** Whether the "not plotted" line has anything to say, and what. */
export function outsideParts(outside: RiskReturnOutside | null | undefined): {cash: boolean; unpriced: boolean} {
    return {cash: present(outside?.cash), unpriced: present(outside?.unpriced)};
}

/**
 * The notes under the chart, in the order they are read (developer's reviews of 05/10/2026):
 *
 * 1. `outside` — what the chart does not plot, right under it, only when there is any;
 * 2. `above` — what being above the line means, only where a line is drawn;
 * 3. `return` — which return the dots use, and its warning in bold: always;
 * 4. `priceOnly` — that the return comes from prices alone: always, until the backend
 *    adds income (Risk, 05/10/2026);
 * 5. `line` — where the line comes from, only where it is drawn;
 * 6. `size` — what a dot's size means, only where the dots are sized by a weight.
 *
 * The two lines about the line can never appear on a chart without one, which is how
 * a chart with no line — the lab before a benchmark is placed — never describes one.
 */
export function riskReturnNotes({lineAnchor, capabilities, outside}: RiskReturnNotesInput): RiskReturnNote[] {
    const parts = outsideParts(outside);
    const notes: RiskReturnNote[] = [];
    if (parts.cash || parts.unpriced) notes.push('outside');
    if (lineAnchor !== null) notes.push('above');
    // TODO(total-return): the returns are price-only today — coupons and dividends received are not in
    // them (developer's review of 06/10/2026: «mettiamolo nei todo futuri e anche in un todo nel codice
    // per non dimenticarlo»). Risk owns the backend change, a total return built from the recorded
    // income with price as the fallback, declared per asset. When it lands: drop `priceOnly` here and
    // `risk.levels.l3.scatter.notes.priceOnly`, and update the «Prices only, for now» warning of
    // `benchmark-selection.en.md#the-risk-return-line`.
    notes.push('return', 'priceOnly');
    if (lineAnchor !== null) notes.push('line');
    if (capabilities.weight) notes.push('size');
    return notes;
}
