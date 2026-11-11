// @vitest-environment jsdom
/**
 * CellDateRange — component test (Vitest + jsdom).
 *
 * The cell has two faces. The normal one embeds a DateRangePicker and is already
 * exercised through ScheduledInvestmentEditor. The other — reached only when
 * `isLateInterest` is true — is a bespoke grace-period popover with its own
 * calendar arithmetic, and it was almost entirely unreached: opening it needs a
 * row that is a late-interest period, which is a narrow slice of seeded data.
 *
 * As a component it is trivial to reach: `isLateInterest` is a prop. What is worth
 * testing is the arithmetic, because it is deliberately *non-calendar*. Grace is
 * stored as a single day count but shown as Y/M/D over a fixed 365-day year and
 * 30-day month, so 400 days is "1y 1m 5d" and 730 days is "2y", and the two input
 * groups have to stay each other's inverse. `onGraceDaysChange(days)` is the whole
 * contract — the number that leaves is what these tests assert.
 *
 * Deliberately NOT tested here:
 *   - the popover's on-screen position. `openGracePopover` reads
 *     `getBoundingClientRect`, which jsdom reports as zeros; asserting the computed
 *     `top`/`left` would be measuring the absence of a layout engine, not the code.
 *   - the DateRangePicker inside the normal branch — it lives in `ui/`, is another
 *     team's component, and is already covered where it is actually driven (SIE).
 *   - any label text: the popover's captions ("Late", "Close", "days") are literals
 *     here, but the number that matters travels through `data-*` and the callback.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import CellDateRange from './CellDateRange.svelte';

beforeAll(async () => {
    // The non-late branch mounts a DateRangePicker that reads the catalogue.
    await setupI18n();
});

function mountLate(props: Record<string, unknown> = {}) {
    const onGraceDaysChange = vi.fn();
    const onchange = vi.fn();
    const utils = render(CellDateRange, {start: '2024-01-01', end: '2024-12-31', isLateInterest: true, graceDays: 0, onGraceDaysChange, onchange, ...props});
    return {onGraceDaysChange, onchange, ...utils};
}

async function openPopover() {
    await fireEvent.click(screen.getByTestId('celldr-late-trigger'));
    return screen.getByTestId('celldr-grace-popover');
}

/** Value of a number input, as the DOM reports it (a string). */
function val(testid: string): string {
    return (screen.getByTestId(testid) as HTMLInputElement).value;
}

/** Last day-count handed to the parent. */
function lastGrace(spy: ReturnType<typeof vi.fn>): number | undefined {
    return spy.mock.calls.at(-1)?.[0];
}

describe('CellDateRange — late-interest trigger', () => {
    it('renders the late trigger and reflects graceDays without opening the popover', () => {
        mountLate({graceDays: 30});
        expect(screen.getByTestId('celldr-late-trigger')).toHaveAttribute('data-grace-days', '30');
        // Closed until clicked.
        expect(screen.queryByTestId('celldr-grace-popover')).toBeNull();
    });

    it('opens the popover on click', async () => {
        mountLate({graceDays: 30});
        expect(await openPopover()).toBeInTheDocument();
    });

    it('does not open when disabled', async () => {
        mountLate({graceDays: 30, disabled: true});
        await fireEvent.click(screen.getByTestId('celldr-late-trigger'));
        expect(screen.queryByTestId('celldr-grace-popover')).toBeNull();
    });
});

describe('CellDateRange — grace arithmetic (365-day year, 30-day month)', () => {
    it('splits a compound total into Y / M / D on open', async () => {
        mountLate({graceDays: 400}); // 400 = 1*365 + 1*30 + 5
        await openPopover();
        expect(val('celldr-grace-y')).toBe('1');
        expect(val('celldr-grace-m')).toBe('1');
        expect(val('celldr-grace-d')).toBe('5');
        expect(val('celldr-grace-total')).toBe('400');
    });

    it('recomputes the total from Y / M / D and emits the day count', async () => {
        const {onGraceDaysChange} = mountLate({graceDays: 0});
        await openPopover();

        await fireEvent.input(screen.getByTestId('celldr-grace-y'), {target: {value: '2'}});
        // 2y = 730 days; the total field mirrors it, and the parent hears the number.
        expect(lastGrace(onGraceDaysChange)).toBe(730);
        expect(val('celldr-grace-total')).toBe('730');
    });

    it('recomputes Y / M / D from an edited total and emits the same number back', async () => {
        const {onGraceDaysChange} = mountLate({graceDays: 0});
        await openPopover();

        await fireEvent.input(screen.getByTestId('celldr-grace-total'), {target: {value: '365'}});
        expect(lastGrace(onGraceDaysChange)).toBe(365);
        expect(val('celldr-grace-y')).toBe('1');
        expect(val('celldr-grace-m')).toBe('0');
        expect(val('celldr-grace-d')).toBe('0');
    });

    it('rounds a fractional total to a whole day', async () => {
        const {onGraceDaysChange} = mountLate({graceDays: 0});
        await openPopover();

        await fireEvent.input(screen.getByTestId('celldr-grace-total'), {target: {value: '10.6'}});
        expect(lastGrace(onGraceDaysChange)).toBe(11);
    });

    it('clamps a negative total to zero', async () => {
        const {onGraceDaysChange} = mountLate({graceDays: 0});
        await openPopover();

        await fireEvent.input(screen.getByTestId('celldr-grace-total'), {target: {value: '-5'}});
        expect(lastGrace(onGraceDaysChange)).toBe(0);
        expect(val('celldr-grace-total')).toBe('0');
    });

    it('clamps a negative Y / M / D field to zero', async () => {
        const {onGraceDaysChange} = mountLate({graceDays: 60});
        await openPopover();

        await fireEvent.input(screen.getByTestId('celldr-grace-m'), {target: {value: '-3'}});
        // m clamps to 0; with the seeded 60 days (0y 2m 0d) that leaves 0.
        expect(lastGrace(onGraceDaysChange)).toBe(0);
        expect(val('celldr-grace-m')).toBe('0');
    });
});

describe('CellDateRange — closing the popover', () => {
    it('closes on Escape', async () => {
        mountLate({graceDays: 30});
        await openPopover();
        await fireEvent.keyDown(window, {key: 'Escape'});
        expect(screen.queryByTestId('celldr-grace-popover')).toBeNull();
    });

    it('closes on a backdrop click', async () => {
        mountLate({graceDays: 30});
        await openPopover();
        await fireEvent.click(screen.getByTestId('celldr-grace-backdrop'));
        expect(screen.queryByTestId('celldr-grace-popover')).toBeNull();
    });

    it('closes on the Close button', async () => {
        mountLate({graceDays: 30});
        await openPopover();
        await fireEvent.click(screen.getByTestId('celldr-grace-close'));
        expect(screen.queryByTestId('celldr-grace-popover')).toBeNull();
    });
});

describe('CellDateRange — normal branch', () => {
    it('renders the inline picker and no late trigger when isLateInterest is false', () => {
        render(CellDateRange, {start: '2024-01-01', end: '2024-06-30', isLateInterest: false, onchange: vi.fn(), onGraceDaysChange: vi.fn()});
        expect(screen.getByTestId('celldr-inline')).toBeInTheDocument();
        expect(screen.queryByTestId('celldr-late-trigger')).toBeNull();
    });
});
