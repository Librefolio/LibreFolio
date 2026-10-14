// @vitest-environment jsdom
/**
 * AllocationPanel — component test (Vitest + jsdom), plan §4 row S4 (R21).
 *
 * Subject: the view (now/history) and the dimension tab are restored from user-scoped
 * storage when the panel mounts. A restored History view requests its data exactly as
 * the click does (`onMount`, AllocationPanel.svelte:85-88). A stored value this version
 * does not know falls back to the default instead of leaving the panel without a pressed
 * button (`readStoredView` / `readStoredTab`, :48-55).
 *
 * WHAT IS REPLACED, AND WHY
 * - `localStorage`: on Node 26 the global is `undefined` without `--localstorage-file`,
 *   and `getUserStorage` then falls back to the defaults in silence, so a stored-History
 *   case would pass or fail for the wrong reason. A Map-backed stand-in, as in
 *   ExposureTable.test.ts, emptied before every case: each mount starts from exactly what
 *   its case stored. Keys are built with the product's own `getUserStorageKey`.
 * - `echarts`: an `init` that returns a recorder, so no renderer can load if a path
 *   changes. With `summary: null` neither AllocationPieChart nor GeographyMap mounts, and
 *   with `allocationHistory: null` the history chart returns before `echarts.init`
 *   (AllocationHistoryChart.svelte:748-750).
 * - `$lib/api`: the history chart's `onMount` loads country and sector reference data
 *   through it. The stand-in answers with empty lists, so those loads settle without jsdom
 *   sending real requests to its default origin (localhost:3000). ExposureTable, KpiSection
 *   and ContributionTable do the same.
 *
 * Nothing translated is asserted. Buttons are found by `data-testid` and their state is
 * read from `aria-pressed`.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {Mock} from 'vitest';

vi.mock('echarts', () => ({
    init: (dom: HTMLElement) => {
        const setOptionCalls: unknown[] = [];
        let disposed = false;
        return {
            setOptionCalls,
            setOption: (option: unknown) => void setOptionCalls.push(option),
            getOption: () => ({}),
            getDom: () => dom,
            getWidth: () => 0,
            getHeight: () => 0,
            on: () => {},
            off: () => {},
            dispatchAction: () => {},
            resize: () => {},
            clear: () => {},
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
    },
}));

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => ({items: []}));
            },
        },
    ),
}));

const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => void storage.set(key, value),
    removeItem: (key: string) => void storage.delete(key),
});

import {tick} from 'svelte';
import {render, screen, setupI18n, waitFor, within} from '$test/component';
import {getUserStorageKey} from '$lib/utils/storage';
import AllocationPanel from './AllocationPanel.svelte';

type RequestHistory = (dimension: 'type' | 'sector' | 'geo', brokerIds: number[] | undefined) => Promise<void>;

/** Persist a selection under the panel's keys (AllocationPanel.svelte:43-44), scoped as the product scopes them. */
function storeSelection(selection: {view: string; tab: string}): void {
    storage.set(getUserStorageKey('dashboard-allocation-view'), selection.view);
    storage.set(getUserStorageKey('dashboard-allocation-tab'), selection.tab);
}

/** Mount the panel with no summary and no history loaded: only the restored selection is under test. */
function mountPanel(): Mock<RequestHistory> {
    const onRequestAllocationHistory = vi.fn<RequestHistory>(async () => {});
    render(AllocationPanel, {
        summary: null,
        loading: false,
        displayCurrency: 'EUR',
        brokerIds: [7, 9],
        currentLanguage: 'en',
        allocationHistory: null,
        onRequestAllocationHistory,
    });
    return onRequestAllocationHistory;
}

/**
 * Barrier: the mount has settled. Every request the panel made has resolved (the panel
 * awaits it), and Svelte has flushed whatever those continuations and effects scheduled.
 * A call count read before this point would miss a second request from another path.
 */
async function mountSettled(onRequest: Mock<RequestHistory>): Promise<void> {
    await Promise.allSettled(onRequest.mock.results.map((result) => result.value));
    await tick();
}

/** `data-testid` of every dimension tab currently pressed. Throws when no tab is rendered at all. */
function pressedTabs(): string[] {
    return within(screen.getByTestId('allocation-panel'))
        .getAllByTestId(/^allocation-tab-/)
        .filter((tab) => tab.getAttribute('aria-pressed') === 'true')
        .map((tab) => tab.dataset.testid ?? '');
}

/**
 * The elements between the history chart and the panel root that carry `invisible`, the
 * class the panel uses to hide the History view (AllocationPanel.svelte:142). Both ends
 * are excluded.
 *
 * Why a class and not `toBeVisible()`: jsdom loads no Tailwind, so `invisible` has no
 * computed style here and `toBeVisible()` would report a hidden chart as visible. The
 * class is the product's visibility switch, and the only observable of it. The chart
 * element carries its own `invisible` while it has no data
 * (AllocationHistoryChart.svelte:826), which says nothing about the panel's choice.
 */
function layersHidingHistory(): HTMLElement[] {
    const panel = screen.getByTestId('allocation-panel');
    const chart = within(panel).getByTestId('allocation-history-chart');
    const hiding: HTMLElement[] = [];
    let el = chart.parentElement;
    while (el !== panel) {
        if (!el) throw new Error('allocation-history-chart is not inside allocation-panel');
        if (el.classList.contains('invisible')) hiding.push(el);
        el = el.parentElement;
    }
    return hiding;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    storage.clear();
});

describe('AllocationPanel — view and tab restored from storage (S4, R21)', () => {
    it('restores a stored History view and requests its data once, for the stored tab', async () => {
        // WHY: History data is fetched on request (Broker detail reloads its overview). A
        // restored History view that does not ask, as the click does, shows the History
        // button pressed over data nobody requested. Catches a dropped mount request, a
        // request for another tab or other brokers, and a second request from another path
        // (an effect, a duplicated onMount): the count is read after the mount has settled.
        storeSelection({view: 'history', tab: 'sector'});

        const onRequest = mountPanel();

        await waitFor(() => expect(onRequest).toHaveBeenCalled());
        await mountSettled(onRequest);

        expect(screen.getByTestId('allocation-view-history')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('allocation-view-now')).toHaveAttribute('aria-pressed', 'false');
        expect(pressedTabs()).toEqual(['allocation-tab-sector']);
        expect(layersHidingHistory()).toEqual([]);
        expect(onRequest).toHaveBeenCalledTimes(1);
        expect(onRequest).toHaveBeenCalledWith('sector', [7, 9]);
    });

    it('falls back to Now when the stored view is not one this version knows', async () => {
        // WHY: `readStoredView` (:48-50) maps anything but 'history' to 'now'. A stored value
        // passed through unvalidated leaves neither view button pressed. The stored tab is a
        // valid non-default one on purpose: seeing it pressed proves storage was read, so
        // 'now' comes from the fallback and not from a storage that answered nothing.
        storeSelection({view: 'garbage', tab: 'sector'});

        const onRequest = mountPanel();

        // Presence barrier: the panel is mounted and its selection restored.
        await waitFor(() => expect(screen.getByTestId('allocation-view-now')).toHaveAttribute('aria-pressed', 'true'));
        expect(pressedTabs()).toEqual(['allocation-tab-sector']);
        await mountSettled(onRequest);

        expect(screen.getByTestId('allocation-view-history')).toHaveAttribute('aria-pressed', 'false');
        expect(layersHidingHistory()).not.toEqual([]);
        expect(onRequest).not.toHaveBeenCalled();
    });

    it('falls back to the Type tab when the stored tab is not one this version knows', async () => {
        // WHY: same fallback rule for the tab (`readStoredTab`, :52-55). A stored value passed
        // through unvalidated leaves no tab pressed, and a restored History view would hand it
        // to the parent as the dimension to load. The stored History view is the proof that
        // storage was read.
        storeSelection({view: 'history', tab: 'garbage'});

        const onRequest = mountPanel();

        await waitFor(() => expect(onRequest).toHaveBeenCalled());
        await mountSettled(onRequest);

        expect(screen.getByTestId('allocation-view-history')).toHaveAttribute('aria-pressed', 'true');
        expect(pressedTabs()).toEqual(['allocation-tab-type']);
        expect(onRequest).toHaveBeenCalledTimes(1);
        expect(onRequest).toHaveBeenCalledWith('type', [7, 9]);
    });
});
