// @vitest-environment jsdom
/**
 * ChartSignalsSection — component test (Vitest + jsdom) for the E1 UX fix.
 *
 * While a backend signal request is in flight, every per-card summary is
 * necessarily stale/empty — and `pointCount: 0` reads as "no data". Showing
 * the red issue icon in that window was a false alarm between "requested" and
 * "answered" (the user-visible flash this fix removes): `signalsLoading=true`
 * must swap the issue icon for a spinner, and the issue must come back the
 * moment the request settles.
 *
 * Asserted on `data-testid` / `data-severity` only — the spinner and the issue
 * icon are the two published states; never a translated label, never a CSS
 * class.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {render, screen, setupI18n} from '$test/component';

// The section's currency labels come from this store, which talks to the API —
// jsdom has no server. The card under test never renders a currency, so an
// empty table is the honest stub.
vi.mock('$lib/stores/reference/currencyStore', () => ({
    currencyStoreVersion: {subscribe: vi.fn(() => () => {})},
    ensureCurrenciesLoaded: vi.fn(async () => undefined),
    getCurrencyInfo: vi.fn(() => undefined),
}));

import ChartSignalsSection, {type SignalDataSummary} from './ChartSignalsSection.svelte';
import type {SignalConfig} from '$lib/charts/signals';

/** A configured signal whose summary says "no data" (pointCount 0 → severity error). */
const SIGNAL: SignalConfig = {
    id: 'sig-1',
    signalType: 'sma',
    params: {window: 20},
    style: {color: '#3b82f6', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null},
};

const EMPTY_SUMMARY: SignalDataSummary = {pointCount: 0, eventCounts: {}, firstDate: null};

function mount(signalsLoading: boolean) {
    const props = {
        signals: [SIGNAL],
        definitions: [],
        signalSummaries: new Map([[SIGNAL.id, EMPTY_SUMMARY]]),
        signalsLoading,
    };
    return {props, ...render(ChartSignalsSection, props)};
}

describe('ChartSignalsSection — signalsLoading suppresses the transient issue icon (E1 UX)', () => {
    beforeEach(async () => {
        await setupI18n();
    });

    it('signalsLoading=true → spinner shown, no error icon', async () => {
        mount(true);

        // Presence barrier first (rule: an absence assertion needs one): the
        // signal card itself must be on screen before "no error icon" means
        // anything.
        await screen.findByText('sma');

        expect(screen.getByTestId('signal-loading')).toBeInTheDocument();
        expect(screen.queryByTestId('signal-issue')).toBeNull();
    });

    it('signalsLoading=false → the issue icon comes back (severity error)', async () => {
        const {rerender, props} = mount(true);
        await screen.findByTestId('signal-loading');

        // The request settled: the very same summary now produces the issue.
        await rerender({...props, signalsLoading: false});

        const issue = await screen.findByTestId('signal-issue');
        expect(issue).toHaveAttribute('data-severity', 'error');
        expect(screen.queryByTestId('signal-loading')).toBeNull();
    });

    it('signalsLoading=false from the start → issue visible immediately (default path unchanged)', async () => {
        mount(false);

        await screen.findByText('sma');
        const issue = await screen.findByTestId('signal-issue');
        expect(issue).toHaveAttribute('data-severity', 'error');
        expect(screen.queryByTestId('signal-loading')).toBeNull();
    });
});
