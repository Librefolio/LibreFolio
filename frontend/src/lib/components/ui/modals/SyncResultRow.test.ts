// @vitest-environment jsdom
/**
 * SyncResultRow — component test (Vitest + jsdom).
 *
 * One line of a sync result, for every sync modal. There used to be four copies
 * of it — AssetSyncModal, FxSyncModal and the two snippets inside PageSyncModal
 * — and they drifted, silently, because each copy was only ever read next to
 * itself: a `partial` explained itself in one and not in the others, an empty
 * `errors` array blanked the hover text in one, and the gesture that copies a
 * long error existed on one row out of four. That is what this file is for. The
 * row's behaviour now has one owner and one place to read it.
 *
 * The division of labour with the three modal specs, and it is worth keeping:
 *   - here: what the row does with a `SyncResult` — which statuses afford a
 *     retry, which carry counters, how the visible error and the copied one are
 *     derived, when the skipped note and the elapsed time appear;
 *   - there: what each modal *passes in* — the identity block, the provider
 *     badge and the registry behind it, the per-leg tooltip only FX has — plus
 *     the section building and the wire→SyncResult mapping, and one test each
 *     that the modal really renders this row.
 *
 * The snippets come from `$test/harness/SyncResultRowHarness.svelte`, which
 * draws deliberately plain markers: what a caller puts in the identity block is
 * that caller's test, not this one.
 *
 * Asserted on `data-testid`/`data-*`, on numbers injected here, and on relative
 * measurements. Never on translated text: the fallback error message comes from
 * the catalogue, so what is asserted about it is that it is *there*, not what it
 * says. Never on CSS classes either — the status colour is a colour, and the
 * skipped note is found by its testid rather than by the `italic` it happens to
 * be styled with.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {SyncResult, SyncStatus} from '$lib/utils/sync/syncHelpers';

// jsdom has neither a clipboard nor `execCommand`, and what the row promises is
// that the whole text leaves the row — not how it travels.
vi.mock('$lib/utils/clipboard', () => ({writeExportToClipboard: vi.fn()}));

import Harness from '$test/harness/SyncResultRowHarness.svelte';
import {writeExportToClipboard} from '$lib/utils/clipboard';

const copied = vi.mocked(writeExportToClipboard);

// =========================================================================
// Fixtures and readers
// =========================================================================

function res(id: string, status: SyncStatus | string, over: Partial<SyncResult> = {}): SyncResult {
    // Asserted into shape on purpose, twice over. `points_fetched` and
    // `points_changed` are required on the type but optional in practice — every
    // modal maps them with `?? 0` and the row reads them the same way, because a
    // body really can arrive without them — so padding them here would delete a
    // branch this file is meant to cover. And `status` is widened because a
    // value outside the four is exactly one of the cases under test.
    return {id, status, ...over} as SyncResult;
}

function mount(result: SyncResult, props: Record<string, unknown> = {}) {
    const onRetry = vi.fn();
    return {onRetry, ...render(Harness, {result, onRetry, ...props})};
}

/** Rows are addressed by the id they were given, never by position. */
function rowOf(id: string): HTMLElement {
    const el = document.querySelector<HTMLElement>(`[data-testid="sync-result-row"][data-row-id="${id}"]`);
    if (!el) throw new Error(`no row for ${id}; present: ${[...document.querySelectorAll('[data-testid="sync-result-row"]')].map((r) => r.getAttribute('data-row-id')).join(', ') || '(none)'}`);
    return el;
}

const retryOf = (id: string) => within(rowOf(id)).queryByTestId('sync-retry-row');
const errorOf = (id: string) => within(rowOf(id)).queryByTestId('sync-row-error');

/** How many `↓` counters the row shows: one group for points, one for events. */
function counterGroups(id: string): number {
    return (rowOf(id).textContent?.match(/↓/g) ?? []).length;
}

/**
 * The hover text of a row's error.
 *
 * It exists only while the trigger is hovered and it is portaled to
 * `document.body` to escape the modal's stacking context, so it is read
 * globally. `findBy` throws on a second match, which is what keeps "one open at
 * a time" honest.
 */
async function hoverTooltip(trigger: HTMLElement): Promise<string> {
    // The listener sits on the Tooltip's own wrapper, the child's parent, and
    // mouseenter does not bubble — the event has to be aimed at the wrapper.
    await fireEvent.mouseEnter(trigger);
    const text = (await screen.findByTestId('tooltip-content')).textContent ?? '';
    await fireEvent.mouseLeave(trigger);
    await waitFor(() => expect(screen.queryByTestId('tooltip-content')).toBeNull());
    return text;
}

const wrapperOf = (el: HTMLElement) => el.parentElement as HTMLElement;

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    copied.mockClear();
});

// =========================================================================
// What each status affords
// =========================================================================

describe('SyncResultRow — what each status affords', () => {
    it('offers a retry, and a reason, on the two statuses that can be repaired and on no other', async () => {
        // One render per status, each with an id of its own, so nothing is read
        // by position and every row is addressed by what it is.
        for (const [status, repairable] of [
            ['ok', false],
            ['partial', true],
            ['failed', true],
            ['skipped', false],
        ] as const) {
            mount(res(status, status, {message: 'something to say', points_fetched: 1, points_changed: 1}));

            expect(rowOf(status)).toHaveAttribute('data-status', status);
            expect(retryOf(status) !== null).toBe(repairable);
            // The reason and the control to act on it appear together: a retry
            // button with nothing next to it is what the FX row used to be.
            expect(errorOf(status) !== null).toBe(repairable);
        }
    });

    it('renders a status it does not recognise, and offers nothing to do about it', async () => {
        mount(res('mystery', 'weird', {message: 'from a newer backend'}));
        // FX passes a `statusTooltip` on every row, so the unrecognised status
        // arrives in production wearing one; both shapes have to survive it.
        mount(res('tipped', 'weird', {message: 'from a newer backend'}), {statusTooltip: 'ecb → frankfurter'});

        for (const id of ['mystery', 'tipped']) {
            // The row is drawn — the icon and colour maps fall back rather than throw…
            expect(rowOf(id)).toHaveAttribute('data-status', 'weird');
            expect(rowOf(id)).toHaveTextContent(id);
            // …and nothing about it is actionable, because nothing here knows what it means.
            expect(retryOf(id)).toBeNull();
            expect(errorOf(id)).toBeNull();
        }

        const icon = rowOf('tipped').querySelector('svg') as SVGElement;
        expect(await hoverTooltip(icon.parentElement as HTMLElement)).toContain('ecb → frankfurter');
    });

    it('takes the retry away while a run is in flight and gives it back when it ends', async () => {
        const {rerender, onRetry} = mount(res('a1', 'failed', {message: 'try me'}));
        expect(retryOf('a1')).not.toBeNull();

        await rerender({syncing: true});
        expect(retryOf('a1')).toBeNull();
        // The reason stays: what went wrong is still true while the next attempt runs.
        expect(errorOf('a1')).not.toBeNull();

        await rerender({syncing: false});
        expect(retryOf('a1')).not.toBeNull();

        await fireEvent.click(retryOf('a1') as HTMLElement);
        expect(onRetry).toHaveBeenCalledWith('a1');
    });
});

// =========================================================================
// The counters
// =========================================================================

describe('SyncResultRow — the counters', () => {
    it('shows the point counters on the two statuses that have them and on no other', async () => {
        for (const [status, counted] of [
            ['ok', true],
            ['partial', true],
            ['failed', false],
            ['skipped', false],
        ] as const) {
            mount(res(status, status, {points_fetched: 7, points_changed: 3}));

            expect(counterGroups(status)).toBe(counted ? 1 : 0);
            if (counted) expect(rowOf(status)).toHaveTextContent('7↓ 3Δ');
        }
    });

    it('reads absent counters as zero rather than as nothing', async () => {
        // The wire shape makes both optional, and an `ok` with no numbers is what
        // a provider that had nothing new to say produces.
        mount(res('a1', 'ok'));

        expect(rowOf('a1')).toHaveTextContent('0↓ 0Δ');
    });

    it('shows the corporate-events pair only when something was fetched, and defaults its delta', async () => {
        mount(res('with', 'ok', {points_fetched: 2, points_changed: 2, events_fetched: 4}));
        mount(res('without', 'ok', {points_fetched: 2, points_changed: 2, events_fetched: 0}));

        expect(counterGroups('with')).toBe(2);
        expect(rowOf('with')).toHaveTextContent('4↓ 0Δ'); // events_changed absent → 0
        expect(counterGroups('without')).toBe(1);
    });

    it('leaves out the glyph in front of the counters when the caller asks for none', async () => {
        // FX rows count rates, not prices, and have always shown bare numbers.
        // Measured as a difference between two rows rather than by naming an icon:
        // which glyph it is belongs to the caller, that there is one belongs here.
        mount(res('withIcon', 'ok', {points_fetched: 1, points_changed: 1}));
        mount(res('bare', 'ok', {points_fetched: 1, points_changed: 1}), {countIcon: null});

        const withIcon = rowOf('withIcon').querySelectorAll('svg').length;
        const bare = rowOf('bare').querySelectorAll('svg').length;
        expect(withIcon - bare).toBe(1);
        expect(rowOf('bare')).toHaveTextContent('1↓ 1Δ');
    });
});

// =========================================================================
// What it says went wrong
// =========================================================================

describe('SyncResultRow — what it says went wrong', () => {
    it('shows the first error on screen and copies every one of them on a double click', async () => {
        mount(res('a1', 'failed', {errors: ['symbol not found', 'and the fallback failed too']}));
        const error = errorOf('a1') as HTMLElement;

        // The row is one line in a narrow flex box: it shows the first error and
        // truncates. Everything else is reachable only by copying, which is why
        // the gesture exists.
        expect(error).toHaveTextContent('symbol not found');
        expect(error).not.toHaveTextContent('and the fallback failed too');
        expect(await hoverTooltip(wrapperOf(error))).toContain('and the fallback failed too');

        await fireEvent.dblClick(error);
        expect(copied).toHaveBeenCalledWith('symbol not found; and the fallback failed too', expect.anything(), expect.anything());
    });

    it('falls back to the message when the error list is empty', async () => {
        // The defect this file exists for. The FX row read its hover text as
        // `errors?.join('; ') ?? message`, and `[].join('; ')` is `''`, which
        // `??` does not catch. An empty `errors` is not exotic: every modal maps
        // `errors: r.errors ?? []`, so a body carrying only a `message` — the
        // ordinary shape — blanked the tooltip exactly when there was something
        // to say.
        mount(res('a1', 'failed', {message: 'upstream refused the range', errors: []}));
        const error = errorOf('a1') as HTMLElement;

        expect(error).toHaveTextContent('upstream refused the range');
        expect(await hoverTooltip(wrapperOf(error))).toContain('upstream refused the range');

        await fireEvent.dblClick(error);
        expect(copied).toHaveBeenCalledWith('upstream refused the range', expect.anything(), expect.anything());
    });

    it('still says something when there is neither an error nor a message', async () => {
        mount(res('a1', 'failed'));

        // The last resort comes from the catalogue and is translated, so what is
        // asserted is that the user is not left with an empty red space.
        expect((errorOf('a1')?.textContent ?? '').trim().length).toBeGreaterThan(0);
    });

    it('copies on a long press, and not on a press that ends early', async () => {
        mount(res('a1', 'failed', {errors: ['held down long enough']}));
        const error = errorOf('a1') as HTMLElement;

        vi.useFakeTimers();
        try {
            await fireEvent.touchStart(error);
            await vi.advanceTimersByTimeAsync(400);
            await fireEvent.touchEnd(error);
            await vi.advanceTimersByTimeAsync(1_000);
            expect(copied).not.toHaveBeenCalled();

            await fireEvent.touchStart(error);
            await vi.advanceTimersByTimeAsync(500);
            expect(copied).toHaveBeenCalledWith('held down long enough', expect.anything(), expect.anything());
        } finally {
            vi.useRealTimers();
        }
    });
});

// =========================================================================
// The skipped note, and the parts the caller supplies
// =========================================================================

describe('SyncResultRow — the skipped note', () => {
    it('explains a skip when the backend gave a reason, and stays silent when it did not', async () => {
        mount(res('spoken', 'skipped', {message: 'rates already complete'}));
        mount(res('silent', 'skipped'));

        // The note hangs off the message, not off the status: a reasonless skip
        // is a row with a name and nothing else to read.
        expect(within(rowOf('spoken')).getByTestId('sync-row-skipped')).toHaveTextContent('rates already complete');
        expect(within(rowOf('silent')).queryByTestId('sync-row-skipped')).toBeNull();
        expect(rowOf('silent')).toHaveTextContent('silent');
    });
});

describe('SyncResultRow — the parts the caller supplies', () => {
    it('renders the identity block it was given', async () => {
        mount(res('a1', 'ok'));

        expect(within(rowOf('a1')).getByTestId('row-identity')).toHaveAttribute('data-identity-for', 'a1');
    });

    it('draws the provider badge only with both a provider and a snippet to draw it with', async () => {
        mount(res('both', 'ok', {provider_used: 'stooq'}));
        mount(res('noSnippet', 'ok', {provider_used: 'stooq'}), {withProvider: false});
        mount(res('noProvider', 'ok'));
        // `skipped` carries no counters, and the badge lives inside that block.
        mount(res('noCounters', 'skipped', {provider_used: 'stooq'}));

        expect(within(rowOf('both')).getByTestId('row-provider')).toHaveAttribute('data-provider', 'stooq');
        expect(within(rowOf('noSnippet')).queryByTestId('row-provider')).toBeNull();
        expect(within(rowOf('noProvider')).queryByTestId('row-provider')).toBeNull();
        expect(within(rowOf('noCounters')).queryByTestId('row-provider')).toBeNull();
    });

    it('wraps the status in a tooltip when the caller has something to add, and in nothing when it has not', async () => {
        // FX passes the per-leg breakdown of a chain here; an asset has no
        // equivalent, so the row must work with and without.
        mount(res('told', 'ok'), {statusTooltip: 'ecb → frankfurter'});
        mount(res('untold', 'ok'));

        const icon = rowOf('told').querySelector('svg') as SVGElement;
        expect(await hoverTooltip(icon.parentElement as HTMLElement)).toContain('ecb → frankfurter');

        // The presence above is what gives this absence its meaning: the same
        // gesture on a row whose caller said nothing opens nothing.
        const bare = rowOf('untold').querySelector('svg') as SVGElement;
        await fireEvent.mouseEnter(bare.parentElement as HTMLElement);
        expect(screen.queryByTestId('tooltip-content')).toBeNull();
    });

    it('offers the tooltip on the retry button too, which is what a failed row shows instead of an icon', async () => {
        mount(res('a1', 'failed', {message: 'down'}), {statusTooltip: 'tried ecb, then frankfurter'});

        const retry = retryOf('a1') as HTMLElement;
        expect(await hoverTooltip(wrapperOf(retry))).toContain('tried ecb, then frankfurter');
    });

    it('shows the elapsed time only when the result carries one', async () => {
        mount(res('slow', 'ok', {elapsed_ms: 2500}));
        mount(res('fast', 'ok', {elapsed_ms: 800}));
        mount(res('untimed', 'ok'));

        // `formatElapsed` has its own unit test; what matters here is which rows
        // get one at all.
        expect(rowOf('slow')).toHaveTextContent('2.5s');
        expect(rowOf('fast')).toHaveTextContent('800ms');
        expect(rowOf('untimed').textContent).not.toMatch(/\dm?s/);
    });
});
