// @vitest-environment jsdom
/**
 * KpiSection — component test (Vitest + jsdom).
 *
 * Subject: F5 — the parenthetical percentage next to the total P&L in the
 * Net Worth card (data-testid="kpi-total-pnl-delta") is the ABSOLUTE,
 * since-inception return (`total_gain_loss_percent`), not the period figure
 * (`simple_roi_percent`). Showing the period number next to the absolute
 * amount answers a question the user didn't ask; the two figures differ
 * precisely when the period is not the whole history, which is always.
 *
 * The test summary sets the two sources far apart (absolute +5%, period +50%)
 * so a mix-up cannot hide behind rounding. Asserted on the rendered DOM of the
 * delta element — the span is plain text, not tweened — and cross-checked on
 * Card 2, where the period ROI legitimately appears.
 *
 * No translated text is asserted; `kpi-total-pnl-delta` and `kpi-returns` are
 * the structural anchors.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
// Namespace import on purpose: the hydration context (page cache, phase 1) is read by name below, so
// the F5 and V2 cases keep running while `TweenedValue.svelte` does not export it yet.
import * as Tweened from '$lib/components/ui/TweenedValue.svelte';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import KpiSection from './KpiSection.svelte';

const EUR = (amount: string) => ({code: 'EUR', amount});

/** A summary where absolute (since-inception) and period returns DIFFER by 10×. */
function summary() {
    return {
        net_worth: EUR('10500'),
        market_value: EUR('10000'),
        period_market_value_start: EUR('9500'),
        open_cost_basis: EUR('10000'),
        period_book_value_start: EUR('9800'),
        cash_total: EUR('500'),
        net_deposited_capital: EUR('10000'),
        total_deposited: EUR('10000'),
        total_withdrawn: EUR('0'),
        period_pnl: EUR('500'),
        period_unrealized_gain_loss_delta: EUR('400'),
        period_realized_gain_loss: EUR('50'),
        period_income: EUR('60'),
        period_fees_taxes: EUR('10'),
        period_fees: EUR('6'),
        period_taxes: EUR('4'),
        total_gain_loss: EUR('500'),
        total_invested: EUR('10000'),
        total_gain_loss_percent: '0.05', // absolute, since inception → +5.00%
        simple_roi_percent: '0.50', // period → +50.00% (Card 2 only)
        twrr_percent: '0.40',
        mwrr_cumulative_percent: '0.45',
        mwrr_annualized_percent: '0.30',
    };
}

beforeAll(async () => {
    await setupI18n();
});

describe('KpiSection — absolute ROI next to total P&L (F5)', () => {
    it('shows total_gain_loss_percent in the Net Worth card parenthetical, not the period ROI', async () => {
        render(KpiSection, {summary: summary(), history: [], loading: false, displayCurrency: 'EUR'});

        await waitFor(() => expect(screen.getByTestId('kpi-total-pnl-delta')).toBeInTheDocument());

        const delta = screen.getByTestId('kpi-total-pnl-delta');
        // Absolute figure: 0.05 → "+5.00%".
        expect(delta.textContent).toContain('(+5.00%)');
        // The period figure must not leak here.
        expect(delta.textContent).not.toContain('50.00%');
    });

    it('keeps the period ROI on the Returns card (the two figures are not swapped)', async () => {
        render(KpiSection, {summary: summary(), history: [], loading: false, displayCurrency: 'EUR'});

        await waitFor(() => expect(screen.getByTestId('kpi-returns')).toBeInTheDocument());

        // Card 2 is the period-returns home: roiVal = simple_roi_percent × 100 → 50.00%.
        // (TweenedValue animates the metric bars, so poll the settled text.)
        const returnsCard = screen.getByTestId('kpi-returns');
        await waitFor(() => expect(returnsCard.textContent).toContain('50.00%'), {timeout: 3000});
        // …and the absolute figure does not take its place.
        expect(returnsCard.textContent).not.toContain('(+5.00%)');
    });

    it('omits the parenthetical when the absolute ROI is not parseable, keeping the amount', async () => {
        const broken = {...summary(), total_gain_loss_percent: 'not-a-number'};
        render(KpiSection, {summary: broken, history: [], loading: false, displayCurrency: 'EUR'});

        await waitFor(() => expect(screen.getByTestId('kpi-total-pnl-delta')).toBeInTheDocument());

        const delta = screen.getByTestId('kpi-total-pnl-delta');
        expect(delta.textContent).not.toContain('%');
        // The P&L amount itself still renders (no crash, no empty card).
        expect(delta.textContent?.trim().length).toBeGreaterThan(0);
    });
});

/**
 * V2 — the daily change and its percentage, on Card 1 (P&L) and Card 2 (Returns).
 *
 * Reported as «+91,31 € (+-16.36%)»: the `+` followed the amount while the number carried its
 * own sign, and against a negative base the quotient came out with the opposite sign to the
 * change. The rule, the developer's, the same on both cards:
 *   percentage = day change / |previous value| × 100;
 *   sign and colour follow the direction (up → `+`, down → `-`), never «+-»;
 *   hidden ONLY when the previous value is exactly 0.
 * Card 1's base is yesterday's total P&L, Card 2's is yesterday's NAV. The change is the
 * difference between the total P&L of the last two history points on both cards.
 *
 * Anchors: `kpi-pnl-delta-day-pct` carries exactly the formatted percentage (formatPercent: `+`
 * only above zero, two decimals); `data-direction` carries the direction, which is what drives
 * the colour — a CSS class is not a contract.
 */
describe('KpiSection — daily change percentage (V2)', () => {
    /** A history point with every field the cards read; only P&L and NAV vary between cases. */
    function point(date: string, totalPnl: string, navValue: string) {
        return {
            date,
            cash_value: EUR('500'),
            market_value: EUR('10000'),
            nav_value: EUR(navValue),
            capital_baseline: EUR('10000'),
            book_asset_like: EUR('10000'),
            cash_from_contributed_capital: EUR('400'),
            cash_from_generated_returns: EUR('100'),
            total_pnl: EUR(totalPnl),
        };
    }

    /** Yesterday then today, as the dashboard's history ends. */
    function renderDay(prev: {totalPnl: string; nav?: string}, last: {totalPnl: string; nav?: string}) {
        const history = [point('2026-10-05', prev.totalPnl, prev.nav ?? '10000'), point('2026-10-06', last.totalPnl, last.nav ?? '10000')];
        return render(KpiSection, {summary: summary(), history, loading: false, displayCurrency: 'EUR'});
    }

    async function dayLine() {
        await waitFor(() => expect(screen.getByTestId('kpi-pnl-delta-day')).toBeInTheDocument());
        return screen.getByTestId('kpi-pnl-delta-day');
    }

    describe('Card 1 — share of yesterday’s total P&L', () => {
        it('a loss that shrinks is a rise: + and up, never «+-»', async () => {
            renderDay({totalPnl: '-558.10'}, {totalPnl: '-466.79'});
            const line = await dayLine();

            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('+16.36%');
            expect(line).toHaveAttribute('data-direction', 'up');
            expect(line.textContent).not.toContain('+-');
        });

        it('a loss that grows is a fall: - and down', async () => {
            renderDay({totalPnl: '-558.10'}, {totalPnl: '-649.41'});
            const line = await dayLine();

            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('-16.36%');
            expect(line).toHaveAttribute('data-direction', 'down');
            expect(line.textContent).not.toContain('+-');
        });

        it('keeps the positive-base reading unchanged', async () => {
            renderDay({totalPnl: '2950.00'}, {totalPnl: '3041.45'});
            const line = await dayLine();

            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('+3.10%');
            expect(line).toHaveAttribute('data-direction', 'up');
        });

        it('a day without change is flat, with an unsigned zero', async () => {
            renderDay({totalPnl: '-558.10'}, {totalPnl: '-558.10'});
            const line = await dayLine();

            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('0.00%');
            expect(line).toHaveAttribute('data-direction', 'flat');
        });

        it('hides the percentage when yesterday’s total P&L is exactly zero, keeping the amount', async () => {
            renderDay({totalPnl: '0'}, {totalPnl: '50'});
            const line = await dayLine();

            // Positive barrier: the line is rendered under the new contract (it has a direction)…
            expect(line).toHaveAttribute('data-direction', 'up');
            // …and only the share of a zero base is missing.
            expect(screen.queryByTestId('kpi-pnl-delta-day-pct')).toBeNull();
            expect(line.textContent?.trim().length).toBeGreaterThan(0);
        });

        it('shows the percentage for a tiny base that is not zero', async () => {
            renderDay({totalPnl: '0.005'}, {totalPnl: '1.005'});
            await dayLine();

            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('+20000.00%');
        });
    });

    describe('Card 2 — share of yesterday’s NAV', () => {
        async function returnsPct() {
            await waitFor(() => expect(screen.getByTestId('kpi-returns')).toBeInTheDocument());
            return screen.queryByTestId('kpi-returns-delta-pct');
        }

        it('shows a rise against a negative NAV as +, never «+-»', async () => {
            renderDay({totalPnl: '-500', nav: '-1000'}, {totalPnl: '-450'});
            const pct = await returnsPct();

            expect(pct).not.toBeNull();
            expect(pct!.textContent?.trim()).toBe('+5.00%');
            expect(pct).toHaveAttribute('data-direction', 'up');
        });

        it('shows a fall against a positive NAV as - and down', async () => {
            renderDay({totalPnl: '1000', nav: '10000'}, {totalPnl: '900'});
            const pct = await returnsPct();

            expect(pct).not.toBeNull();
            expect(pct!.textContent?.trim()).toBe('-1.00%');
            expect(pct).toHaveAttribute('data-direction', 'down');
        });

        it('hides the percentage only when yesterday’s NAV is exactly zero', async () => {
            renderDay({totalPnl: '-558.10', nav: '0'}, {totalPnl: '-466.79'});
            const pct = await returnsPct();

            // Positive barrier in the same render: Card 1, whose base is not zero, shows its share.
            expect(screen.getByTestId('kpi-pnl-delta-day-pct').textContent?.trim()).toBe('+16.36%');
            expect(pct).toBeNull();
        });
    });
});

/**
 * Page cache, phase 1 (R2 / N, decision E1 of 06/10): a figure already known does not count up from 0.
 *
 * `TweenedValue` starts every value from `tweened(0)`, so returning to the Dashboard with the report
 * in cache still shows each KPI counting from zero for ~1 s — on screen it looks like a recompute.
 * The page that hydrates from the cache says so through a Svelte context, `TWEEN_HYDRATION_CONTEXT`
 * (set by `setTweenHydration(isHydrated)`, both exported by `TweenedValue.svelte`'s module script):
 * while `isHydrated()` is true, a tweened value appears at its final value on the first frame, and a
 * later change still tweens from the old value to the new one. Without the context nothing changes:
 * the first load counts from zero, as today.
 *
 * The subject is Card 1's hero (`kpi-period-pnl` → `kpi-value`), formatted by the same formatter the
 * card uses, so the comparison carries no translated text and no locale assumption.
 */
describe('KpiSection — hydration from the cache (page cache, phase 1)', () => {
    const hydration = Tweened as unknown as {TWEEN_HYDRATION_CONTEXT?: unknown; setTweenHydration?: (isHydrated: () => boolean) => void};
    const hero = () => within(screen.getByTestId('kpi-period-pnl')).getByTestId('kpi-value');
    /** Card 1's hero exactly as KpiSection formats it. */
    const heroText = (amount: number) => formatCurrencyAmountPlain(amount, 'EUR', {showSign: true});
    const props = (periodPnl = '500') => ({summary: {...summary(), period_pnl: EUR(periodPnl)}, history: [], loading: false, displayCurrency: 'EUR'});

    function hydratedContext(): Map<unknown, () => boolean> {
        expect(hydration.TWEEN_HYDRATION_CONTEXT, 'TweenedValue.svelte exports no TWEEN_HYDRATION_CONTEXT: a page hydrated from the cache cannot tell its figures to start from their value').toBeDefined();
        return new Map([[hydration.TWEEN_HYDRATION_CONTEXT, () => true]]);
    }

    it('exports the context key and its setter from TweenedValue’s module script', () => {
        expect(hydration.TWEEN_HYDRATION_CONTEXT, 'TweenedValue.svelte exports no TWEEN_HYDRATION_CONTEXT').toBeDefined();
        expect(typeof hydration.setTweenHydration, 'TweenedValue.svelte exports no setTweenHydration(isHydrated)').toBe('function');
    });

    it('without the context, counts up: the first frame is the formatted zero, then the final value (the first load, unchanged)', async () => {
        render(KpiSection, props());

        // Read synchronously after render: before any animation frame.
        expect(hero().textContent?.trim()).toBe(heroText(0));
        await waitFor(() => expect(hero().textContent?.trim()).toBe(heroText(500)), {timeout: 3000});
    });

    it('with the context, shows the final value on the first frame, before any animation frame', () => {
        render(KpiSection, {props: props(), context: hydratedContext()});

        expect(hero().textContent?.trim(), 'a figure served from the cache still counts up from zero').toBe(heroText(500));
    });

    it('with the context, still moves to a new value when the summary changes', async () => {
        const {rerender} = render(KpiSection, {props: props('500'), context: hydratedContext()});
        expect(hero().textContent?.trim(), 'precondition: the cached figure is on screen at once').toBe(heroText(500));

        await rerender(props('800'));

        await waitFor(() => expect(hero().textContent?.trim(), 'the refreshed figure never replaced the cached one').toBe(heroText(800)), {timeout: 3000});
    });
});

/**
 * P9 — Card 1's «Unrealized change» bar explains itself (issue #32, D11).
 *
 * The backend splits `period_unrealized_gain_loss_delta` by asset currency into
 * `summary.period_unrealized_breakdown`: `asset` rows (what the assets did in their own currency),
 * `fx` rows (what the exchange rate did to their cost), `unsplit` rows (positions that could not be
 * split). The rows add up to the bar's figure exactly, in an order the backend owns. Contract:
 *
 *   - rows present → the bar's tooltip is HTML, with one
 *     `<tr data-testid="kpi-unrealized-breakdown-{kind}-{asset_currency}">` per row, in the order
 *     received: the frontend never adds a row (no `fx` row for the report currency) nor drops one;
 *   - each row's value cell — its last cell, as in every tooltip table of this card — is the row's
 *     `period_delta` formatted like the cash tooltip: signed money through `formatCurrencyAmountPlain`,
 *     so masked by the privacy toggle exactly as every personal amount is;
 *   - no rows (empty or absent) → today's plain text tooltip, and no breakdown row.
 *
 * The bar is found by structure, not by its label: Card 1's metric bars follow its hero figure
 * (`kpi-value`), and each one's tooltip trigger is the `[role="button"]` wrapper Tooltip renders
 * (the header's DocsLink comes before the hero and is a native `<button>`), so the first trigger
 * after the hero is the «Unrealized change» bar. It is opened with Enter — the keyboard path opens
 * the same tooltip as a hover, without the hover delay. Labels are never asserted: their i18n keys
 * have not landed yet.
 */
describe('KpiSection — unrealized change breakdown tooltip (P9)', () => {
    type BreakdownKind = 'asset' | 'fx' | 'unsplit';
    const row = (kind: BreakdownKind, assetCurrency: string, amount: string) => ({kind, asset_currency: assetCurrency, period_delta: EUR(amount)});

    /** Four rows adding up to the fixture's `period_unrealized_gain_loss_delta` (400), in the backend's order. */
    const ROWS = [row('asset', 'EUR', '250.50'), row('asset', 'USD', '120'), row('fx', 'USD', '-30.25'), row('unsplit', 'ISK', '59.75')];

    const norm = (text: string | null | undefined): string => (text ?? '').replace(/\s+/g, ' ').trim();
    const testIdOf = (r: {kind: string; asset_currency: string}) => `kpi-unrealized-breakdown-${r.kind}-${r.asset_currency}`;
    /** What the value cell must read: the cash tooltip's formatter, signed, in the amount's own currency. */
    const signedMoney = (r: {period_delta: {code: string; amount: string}}) => norm(formatCurrencyAmountPlain(parseFloat(r.period_delta.amount), r.period_delta.code, {showSign: true}));

    function renderWith(extra: Record<string, unknown>) {
        return render(KpiSection, {summary: {...summary(), ...extra}, history: [], loading: false, displayCurrency: 'EUR'});
    }

    /** Card 1's first metric bar trigger: the first Tooltip wrapper after the hero figure. */
    function unrealizedBarTrigger(): HTMLElement {
        const card = screen.getByTestId('kpi-period-pnl');
        const hero = within(card).getByTestId('kpi-value');
        const trigger = Array.from(card.querySelectorAll<HTMLElement>('[role="button"]')).find((element) => element.tagName !== 'BUTTON' && Boolean(hero.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING));
        if (!trigger) throw new Error('Card 1 renders no tooltip trigger after its hero figure: the metric bars are gone');
        return trigger;
    }

    async function openUnrealizedTooltip(): Promise<HTMLElement> {
        await fireEvent.keyDown(unrealizedBarTrigger(), {key: 'Enter'});
        return screen.findByTestId('tooltip-content');
    }

    function breakdownRowIds(tooltip: HTMLElement): string[] {
        return Array.from(tooltip.querySelectorAll<HTMLElement>('[data-testid^="kpi-unrealized-breakdown-"]')).map((element) => element.getAttribute('data-testid') ?? '');
    }

    function valueCell(tooltip: HTMLElement, r: {kind: string; asset_currency: string}): string {
        const tableRow = within(tooltip).getByTestId(testIdOf(r));
        expect(tableRow.tagName, `${testIdOf(r)} is a table row`).toBe('TR');
        const cells = tableRow.querySelectorAll('td');
        return norm(cells[cells.length - 1]?.textContent);
    }

    afterEach(() => {
        // Module-level flag shared by every test of the file: a leftover `true` would mount the next card masked.
        setPrivacyEnabled(false);
    });

    it('lists one row per breakdown row, in the order received, each with its signed amount', async () => {
        renderWith({period_unrealized_breakdown: ROWS});

        const tooltip = await openUnrealizedTooltip();

        expect(breakdownRowIds(tooltip)).toEqual(ROWS.map(testIdOf));
        for (const r of ROWS) expect(valueCell(tooltip, r), testIdOf(r)).toBe(signedMoney(r));
    });

    it('keeps the order it receives even when it is not the one it would choose: the backend owns it', async () => {
        const scrambled = [ROWS[2], ROWS[3], ROWS[1], ROWS[0]];
        renderWith({period_unrealized_breakdown: scrambled});

        const tooltip = await openUnrealizedTooltip();

        expect(breakdownRowIds(tooltip)).toEqual(scrambled.map(testIdOf));
    });

    it('shows exactly the rows it receives: a single-currency portfolio has one asset row, no fx row of its own making', async () => {
        const single = [row('asset', 'EUR', '400')];
        renderWith({period_unrealized_breakdown: single});

        const tooltip = await openUnrealizedTooltip();

        expect(breakdownRowIds(tooltip)).toEqual(['kpi-unrealized-breakdown-asset-EUR']);
        expect(valueCell(tooltip, single[0])).toBe(signedMoney(single[0]));
    });

    it('masks every amount with privacy on, as the formatter masks any personal amount', async () => {
        setPrivacyEnabled(true);
        // Control: the expected values really are masked — equality below is not digits against digits.
        for (const r of ROWS) expect(signedMoney(r), `control: ${testIdOf(r)} masked by the formatter`).not.toMatch(/\d/);
        renderWith({period_unrealized_breakdown: ROWS});

        const tooltip = await openUnrealizedTooltip();

        expect(breakdownRowIds(tooltip)).toEqual(ROWS.map(testIdOf));
        for (const r of ROWS) expect(valueCell(tooltip, r), testIdOf(r)).toBe(signedMoney(r));
    });

    it.each([
        ['empty', {period_unrealized_breakdown: []}],
        ['absent', {}],
    ])('keeps today’s plain text tooltip when the breakdown is %s', async (_label, extra) => {
        renderWith(extra);

        const tooltip = await openUnrealizedTooltip();

        expect(breakdownRowIds(tooltip)).toEqual([]);
        expect(tooltip.querySelector('table'), 'a plain text tooltip has no table').toBeNull();
        expect(norm(tooltip.textContent).length).toBeGreaterThan(0);
    });
});

/**
 * Card 2 «Returns» — a return the backend did not compute reads «—», never 0.
 *
 * `twrr_percent`, `mwrr_cumulative_percent` and `mwrr_annualized_percent` are optional and nullable
 * in the schema: TWRR is None when it cannot be calculated, MWRR when its solver does not converge.
 * A figure nobody computed is not a zero return. The defect pinned here parsed each missing one as 0:
 * its bar read «0.00%», and Timing effect subtracted that invented zero — a missing MWRR cumulative
 * came out as «-40.00 pp», labelled unfavourable. Contract:
 *
 *   - a missing TWRR / MWRR cumulative / MWRR annualized reads «—» (U+2014) as its bar value: no digits;
 *   - Timing effect is `mwrr_cumulative − twrr` in percentage points, signed, two decimals; when either
 *     input is missing it reads «—», and its label claims nothing — neither favourable, neutral nor
 *     unfavourable;
 *   - MWRR annualized is not an input of Timing effect: its absence leaves Timing effect untouched;
 *   - `null` and an absent key are the same «missing»: every case runs with both.
 *
 * Read through `kpi-return-{roi,twrr-cum,mwrr-cum,mwrr-ann}-value`, `kpi-timing-effect-value` and
 * `kpi-timing-effect-label`, inside `kpi-returns`. The bars tween for 700 ms, so every assertion also
 * requires ROI — required by the schema, never missing here — at its settled «50.00%»: a «—» counts
 * only once the card has stopped moving. The anchors are compared together, so a red lists every one
 * that disagrees. Timing effect is locale-formatted with a translated unit, so only its sign and
 * digits are matched; the label is translated, so it is only read as empty or not.
 */
describe('KpiSection — Returns card: a missing return reads «—», never 0 (Card 2)', () => {
    const EM_DASH = '\u2014';
    /** ±5.00 pp: the decimal separator is the locale's and the unit is translated, so only sign and digits are matched. */
    const PLUS_5_PP = expect.stringMatching(/^\+5[.,]00(?!\d)/);
    const MINUS_5_PP = expect.stringMatching(/^-5[.,]00(?!\d)/);
    /** A label that claims a reading (favourable, neutral or unfavourable): its wording is translated, so only its presence is read. */
    const A_CLAIM = expect.stringMatching(/\S/);

    const ANCHORS = {
        roi: 'kpi-return-roi-value',
        twrrCum: 'kpi-return-twrr-cum-value',
        mwrrCum: 'kpi-return-mwrr-cum-value',
        mwrrAnn: 'kpi-return-mwrr-ann-value',
        timing: 'kpi-timing-effect-value',
        timingLabel: 'kpi-timing-effect-label',
    } as const;
    type Anchor = keyof typeof ANCHORS;

    type ReturnField = 'twrr_percent' | 'mwrr_cumulative_percent' | 'mwrr_annualized_percent';
    type Missing = 'null' | 'absent';
    /** The fixture as the schema types it: the three returns are optional and nullable. */
    type ReturnsSummary = Omit<ReturnType<typeof summary>, ReturnField> & Partial<Record<ReturnField, string | null>>;

    const norm = (text: string | null | undefined): string => (text ?? '').replace(/\s+/g, ' ').trim();

    /** The fixture with `fields` missing: set to null, or with their keys removed. */
    function summaryMissing(fields: readonly ReturnField[], how: Missing): ReturnsSummary {
        const s: ReturnsSummary = summary();
        for (const field of fields) {
            if (how === 'null') s[field] = null;
            else delete s[field];
        }
        return s;
    }

    function renderReturns(s: ReturnsSummary): void {
        render(KpiSection, {summary: s, history: [], loading: false, displayCurrency: 'EUR'});
    }

    /** What the Returns card shows at each anchor. Every value must be on screen; a label that is not rendered claims nothing either, so it reads as empty. */
    function readReturns(anchors: readonly Anchor[]): Record<string, string> {
        const card = within(screen.getByTestId('kpi-returns'));
        const read = (anchor: Anchor): string => norm((anchor === 'timingLabel' ? card.queryByTestId(ANCHORS[anchor]) : card.getByTestId(ANCHORS[anchor]))?.textContent);
        return Object.fromEntries(anchors.map((anchor) => [anchor, read(anchor)]));
    }

    /** Polls until the card reads `expected` at its anchors, with ROI settled at «50.00%» as the barrier. On timeout the diff is the whole reading, not only its first mismatch. */
    async function expectReturnsCard(expected: Partial<Record<Anchor, unknown>>): Promise<void> {
        const want: Partial<Record<Anchor, unknown>> = {roi: '50.00%', ...expected};
        await waitFor(() => expect(readReturns(Object.keys(want) as Anchor[])).toEqual(want), {timeout: 3000, onTimeout: (error) => error});
    }

    it.each([
        {reading: 'favourable', twrr: '0.40', mwrrCum: '0.45', twrrBar: '40.00%', mwrrCumBar: '45.00%', timing: PLUS_5_PP},
        {reading: 'unfavourable', twrr: '0.45', mwrrCum: '0.40', twrrBar: '45.00%', mwrrCumBar: '40.00%', timing: MINUS_5_PP},
    ])('control, every return present ($reading): each bar reads its value; Timing effect is mwrr_cum − twrr in pp, signed, with a claim', async ({twrr, mwrrCum, twrrBar, mwrrCumBar, timing}) => {
        renderReturns({...summary(), twrr_percent: twrr, mwrr_cumulative_percent: mwrrCum});

        await expectReturnsCard({twrrCum: twrrBar, mwrrCum: mwrrCumBar, mwrrAnn: '30.00%', timing, timingLabel: A_CLAIM});
    });

    describe.each<Missing>(['null', 'absent'])('a return missing as %s', (how) => {
        it('mwrr_cumulative_percent: its bar reads «—»; Timing effect reads «—» and claims nothing', async () => {
            renderReturns(summaryMissing(['mwrr_cumulative_percent'], how));

            await expectReturnsCard({twrrCum: '40.00%', mwrrCum: EM_DASH, mwrrAnn: '30.00%', timing: EM_DASH, timingLabel: ''});
        });

        it('twrr_percent: its bar reads «—»; Timing effect reads «—» and claims nothing', async () => {
            renderReturns(summaryMissing(['twrr_percent'], how));

            await expectReturnsCard({twrrCum: EM_DASH, mwrrCum: '45.00%', mwrrAnn: '30.00%', timing: EM_DASH, timingLabel: ''});
        });

        it('mwrr_annualized_percent: its bar reads «—», the other bars keep their values', async () => {
            renderReturns(summaryMissing(['mwrr_annualized_percent'], how));

            await expectReturnsCard({twrrCum: '40.00%', mwrrCum: '45.00%', mwrrAnn: EM_DASH});
        });

        it('mwrr_annualized_percent: Timing effect does not read it, still +5.00 pp with its claim', async () => {
            renderReturns(summaryMissing(['mwrr_annualized_percent'], how));

            await expectReturnsCard({timing: PLUS_5_PP, timingLabel: A_CLAIM});
        });

        it('twrr_percent and mwrr_cumulative_percent: both bars read «—»; Timing effect reads «—» and claims nothing', async () => {
            renderReturns(summaryMissing(['twrr_percent', 'mwrr_cumulative_percent'], how));

            await expectReturnsCard({twrrCum: EM_DASH, mwrrCum: EM_DASH, mwrrAnn: '30.00%', timing: EM_DASH, timingLabel: ''});
        });
    });
});
