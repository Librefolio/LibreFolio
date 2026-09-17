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
import {get} from 'svelte/store';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {_ as t} from '$lib/i18n';

// The section's currency labels come from this store, which talks to the API —
// jsdom has no server. The diagnostic cases only need the flag field rendered
// beside the configured asset currency.
vi.mock('$lib/stores/reference/currencyStore', () => ({
    currencyStoreVersion: {subscribe: vi.fn(() => () => {})},
    ensureCurrenciesLoaded: vi.fn(async () => undefined),
    getCurrencyInfo: vi.fn(() => ({flag_emoji: ''})),
}));

import ChartSignalsSection, {type SignalDataSummary} from './ChartSignalsSection.svelte';
import ChartAestheticsSection from './ChartAestheticsSection.svelte';
import type {SignalConfig, SignalDefinition, SignalProblem} from '$lib/charts/signals';

/** A configured signal whose summary says "no data" (pointCount 0 → severity error). */
const SIGNAL: SignalConfig = {
    id: 'sig-1',
    signalType: 'sma',
    params: {window: 20},
    style: {color: '#3b82f6', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null},
};

const CONVERSION_ERROR = 'synthetic-price-conversion-failure';
const FAILED_COMPARISON_SIGNAL: SignalConfig = {
    id: 'failed-comparison',
    signalType: 'asset-comparison',
    params: {
        assetId: '42',
        _conversionFailed: true,
        _conversionError: CONVERSION_ERROR,
    },
    style: {color: '#f59e0b', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null},
};
const ASSET_COMPARISON_DEFINITION: SignalDefinition = {
    type: 'asset-comparison',
    displayName: 'Asset',
    icon: '📊',
    category: 'comparison',
    paramDescriptors: [
        {
            key: 'assetId',
            label: 'Asset',
            type: 'select',
            default: '',
            dynamicOptionsKey: 'configuredAssets',
        },
    ],
    source: 'local',
};

const EMPTY_SUMMARY: SignalDataSummary = {pointCount: 0, eventCounts: {}, firstDate: null};
const READY_COMPARISON_SUMMARY: SignalDataSummary = {
    pointCount: 2,
    eventCounts: {},
    firstDate: '2026-08-01',
};
const INSUFFICIENT_HISTORY_PROBLEM: SignalProblem = {
    code: 'insufficient_history',
    status: 'unavailable',
    missingPriceFields: [],
    missingEventTypes: [],
    fieldCoverage: {close: 1},
    availablePoints: 0,
    requestedPoints: 365,
    minimumPoints: 365,
    warmupUsedPoints: 0,
    warmupRequiredPoints: 365,
    missingPoints: 365,
    maxConsecutiveMissingPoints: 365,
    coverageRatio: 0,
    coveragePercent: 0,
    selectedStartDate: null,
    selectedEndDate: null,
    excludedPoints: null,
    message: null,
};

const HIDDEN_SIGNAL: SignalConfig = {
    id: 'hidden-sma',
    signalType: 'sma',
    params: {window: 37, untouched: {marker: 'hidden-config'}},
    style: {color: '#ec4899', lineWidth: 3, lineType: 'dashed', markerStart: 'circle', markerEnd: 'diamond'},
    componentStyles: {
        average: {color: '#8b5cf6', lineWidth: 1, lineType: 'dotted', markerStart: null, markerEnd: null},
    },
};
const HIDDEN_SIGNAL_BYTES = JSON.stringify(HIDDEN_SIGNAL);

function expectHiddenSignalUnchanged(signals: SignalConfig[]) {
    const hidden = signals.find((signal) => signal.id === HIDDEN_SIGNAL.id);
    expect(hidden).toBeDefined();
    expect(JSON.stringify(hidden)).toBe(HIDDEN_SIGNAL_BYTES);
}

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

describe('ChartSignalsSection — typed problem rendering', () => {
    beforeEach(async () => {
        await setupI18n();
    });

    it('prefers the typed problem over conversion, zero-point, and missing-before fallbacks', async () => {
        render(ChartSignalsSection, {
            signals: [FAILED_COMPARISON_SIGNAL],
            definitions: [],
            signalSummaries: new Map([
                [
                    FAILED_COMPARISON_SIGNAL.id,
                    {
                        pointCount: 0,
                        eventCounts: {},
                        firstDate: '2026-09-14',
                        problem: INSUFFICIENT_HISTORY_PROBLEM,
                    },
                ],
            ]),
            signalsLoading: false,
            dateStart: '2025-09-14',
        });

        const card = await screen.findByTestId(`signal-card-${FAILED_COMPARISON_SIGNAL.id}`);
        const issue = within(card).getByTestId('signal-issue');
        expect(issue).toHaveAttribute('data-problem-code', 'insufficient_history');
        expect(issue).toHaveAttribute('data-severity', 'error');
    });
});

describe('ChartSignalsSection — asset comparison mode diagnostics', () => {
    beforeEach(async () => {
        await setupI18n();
    });

    it('authoritative Calendar summary bypasses stale price conversion flags', async () => {
        const props = {
            signals: [FAILED_COMPARISON_SIGNAL],
            definitions: [ASSET_COMPARISON_DEFINITION],
            signalSummaries: new Map([
                [
                    FAILED_COMPARISON_SIGNAL.id,
                    {
                        ...READY_COMPARISON_SUMMARY,
                        comparisonStatusAuthoritative: true,
                    },
                ],
            ]),
            signalsLoading: false,
            availableAssets: [{id: 42, display_name: 'Synthetic comparison asset', currency: 'USD'}],
            displayCurrency: 'EUR',
            configuredFxSlugs: ['EUR-USD'],
            oncreatefxpair: vi.fn(),
            onsyncfxpair: vi.fn(),
        };
        const view = render(ChartSignalsSection, props);

        const card = await screen.findByTestId(`signal-card-${FAILED_COMPARISON_SIGNAL.id}`);
        expect(within(card).getByTestId(`signal-param-${FAILED_COMPARISON_SIGNAL.id}-assetId`)).toBeInTheDocument();
        expect(within(card).queryByTestId('signal-issue')).toBeNull();
        expect(within(card).queryByTestId(`signal-fx-sync-${FAILED_COMPARISON_SIGNAL.id}`)).toBeNull();
        expect(within(card).queryByTestId(`signal-fx-create-${FAILED_COMPARISON_SIGNAL.id}`)).toBeNull();

        await view.rerender({...props, configuredFxSlugs: []});

        const nonconfiguredCard = screen.getByTestId(`signal-card-${FAILED_COMPARISON_SIGNAL.id}`);
        expect(within(nonconfiguredCard).getByTestId(`signal-param-${FAILED_COMPARISON_SIGNAL.id}-assetId`)).toBeInTheDocument();
        expect(within(nonconfiguredCard).queryByTestId('signal-issue')).toBeNull();
        expect(within(nonconfiguredCard).queryByTestId(`signal-fx-create-${FAILED_COMPARISON_SIGNAL.id}`)).toBeNull();
        expect(within(nonconfiguredCard).queryByTestId(`signal-fx-sync-${FAILED_COMPARISON_SIGNAL.id}`)).toBeNull();
    });

    it('normal Price summary keeps the conversion failure diagnostic', async () => {
        const props = {
            signals: [FAILED_COMPARISON_SIGNAL],
            definitions: [ASSET_COMPARISON_DEFINITION],
            signalSummaries: new Map([[FAILED_COMPARISON_SIGNAL.id, READY_COMPARISON_SUMMARY]]),
            signalsLoading: false,
            availableAssets: [{id: 42, display_name: 'Synthetic comparison asset', currency: 'USD'}],
            displayCurrency: 'EUR',
            configuredFxSlugs: ['EUR-USD'],
            oncreatefxpair: vi.fn(),
            onsyncfxpair: vi.fn(),
        };
        const view = render(ChartSignalsSection, props);

        const card = await screen.findByTestId(`signal-card-${FAILED_COMPARISON_SIGNAL.id}`);
        expect(within(card).getByTestId(`signal-param-${FAILED_COMPARISON_SIGNAL.id}-assetId`)).toBeInTheDocument();
        const issue = within(card).getByTestId('signal-issue');
        expect(issue).toHaveAttribute('data-severity', 'error');
        expect(issue).not.toHaveAttribute('data-problem-code');
        const syncButton = within(card).getByTestId(`signal-fx-sync-${FAILED_COMPARISON_SIGNAL.id}`);
        const syncAriaLabel = `${get(t)('common.sync')}: EUR/USD`;
        expect(syncButton).toBeInTheDocument();
        expect(syncButton).toHaveAccessibleName(syncAriaLabel);
        expect(syncButton).toHaveAttribute('aria-label', syncAriaLabel);
        expect(within(card).queryByTestId(`signal-fx-create-${FAILED_COMPARISON_SIGNAL.id}`)).toBeNull();
        await fireEvent.click(issue);
        expect(await screen.findByTestId('tooltip-content')).toHaveTextContent(CONVERSION_ERROR);

        await view.rerender({...props, configuredFxSlugs: []});

        const nonconfiguredCard = screen.getByTestId(`signal-card-${FAILED_COMPARISON_SIGNAL.id}`);
        expect(within(nonconfiguredCard).getByTestId(`signal-param-${FAILED_COMPARISON_SIGNAL.id}-assetId`)).toBeInTheDocument();
        const nonconfiguredIssue = within(nonconfiguredCard).getByTestId('signal-issue');
        expect(nonconfiguredIssue).toHaveAttribute('data-severity', 'error');
        expect(nonconfiguredIssue).not.toHaveAttribute('data-problem-code');
        const createButton = within(nonconfiguredCard).getByTestId(`signal-fx-create-${FAILED_COMPARISON_SIGNAL.id}`);
        const createAriaLabel = `${get(t)('common.create')}: ${get(t)('assetDetail.fxPairMissing', {values: {base: 'EUR', quote: 'USD'}})}`;
        expect(createButton).toBeInTheDocument();
        expect(createButton).toHaveAccessibleName(createAriaLabel);
        expect(createButton).toHaveAttribute('aria-label', createAriaLabel);
        expect(within(nonconfiguredCard).queryByTestId(`signal-fx-sync-${FAILED_COMPARISON_SIGNAL.id}`)).toBeNull();
    });

    it('keeps page-owned asset sync progress across a true remount', () => {
        const syncingAssetIds = new Set([42]);
        const props = {
            signals: [FAILED_COMPARISON_SIGNAL],
            definitions: [ASSET_COMPARISON_DEFINITION],
            availableAssets: [{id: 42, display_name: 'Synthetic comparison asset'}],
            syncingAssetIds,
            onsyncasset: vi.fn(),
        };
        const view = render(ChartSignalsSection, props);
        const syncTestId = `signal-sync-asset-${FAILED_COMPARISON_SIGNAL.id}`;

        const syncAction = screen.getByTestId(syncTestId);
        expect(syncAction).toBeDisabled();
        expect(syncAction.querySelector('svg')).toHaveClass('animate-spin');

        view.unmount();
        render(ChartSignalsSection, props);

        const remountedSyncAction = screen.getByTestId(syncTestId);
        expect(remountedSyncAction).toBeDisabled();
        expect(remountedSyncAction.querySelector('svg')).toHaveClass('animate-spin');
    });

    it('clears only target runtime params when Asset SearchSelect replaces the peer asset', async () => {
        const style: SignalConfig['style'] = {
            color: '#2563eb',
            lineWidth: 3,
            lineType: 'dashed',
            markerStart: 'circle',
            markerEnd: 'diamond',
        };
        const durableParam = {lookbackDays: 90};
        const runtimeParams = {
            _resolvedData: [{date: '2026-09-01', value: 101}],
            _conversionFailed: true,
            _conversionError: 'stale conversion failure',
            _assetCurrency: 'USD',
            _targetCurrency: 'EUR',
            _assetIconUrl: '/icons/old-peer.svg',
            _assetType: 'ETF',
            _assetDisplayName: 'Old peer asset',
        };
        const peerSignal: SignalConfig = {
            id: 'peer-asset-replacement',
            signalType: 'asset-comparison',
            params: {
                assetId: '101',
                mode: 'percentage',
                durableParam,
                ...runtimeParams,
            },
            style,
        };
        let emittedSignals: SignalConfig[] | undefined;
        const onchange = vi.fn((next: SignalConfig[]) => {
            emittedSignals = next;
        });
        render(ChartSignalsSection, {
            signals: [peerSignal],
            definitions: [ASSET_COMPARISON_DEFINITION],
            availableAssets: [
                {id: 101, display_name: 'Old peer asset'},
                {id: 202, display_name: 'Replacement peer asset'},
            ],
            onchange,
        });

        const assetSelectId = `signal-param-${peerSignal.id}-assetId-select`;
        const assetSelect = screen.getByTestId(assetSelectId);
        await fireEvent.click(within(assetSelect).getByTestId(`${assetSelectId}-trigger`));
        const listbox = await within(assetSelect).findByRole('listbox');
        await fireEvent.click(within(listbox).getByTestId('search-select-option-202'));

        await waitFor(() => expect(onchange).toHaveBeenCalledTimes(1));
        if (!emittedSignals) throw new Error('Asset replacement did not emit a signal configuration');
        const replacement = emittedSignals.find((signal) => signal.id === peerSignal.id);
        if (!replacement) throw new Error(`Replacement for signal ${peerSignal.id} was not emitted`);

        expect(replacement.params).toEqual({
            assetId: '202',
            mode: 'percentage',
            durableParam,
        });
        for (const runtimeKey of Object.keys(runtimeParams)) {
            expect(replacement.params).not.toHaveProperty(runtimeKey);
        }
        expect(replacement.style).toEqual(style);
    });
});

describe('ChartSignalsSection — signal style popover', () => {
    beforeEach(async () => {
        await setupI18n();
    });

    it('closes the signal style popover when Escape reaches the window listener', async () => {
        mount(false);

        const styleSection = screen.getByTestId(`signal-style-${SIGNAL.id}`);
        await fireEvent.click(within(styleSection).getByRole('button'));

        expect(screen.getByTestId('signal-style-popover')).toBeVisible();
        expect(screen.getByTestId('signal-style-backdrop')).toBeInTheDocument();

        await fireEvent.keyDown(window, {key: 'Escape'});

        expect(screen.queryByTestId('signal-style-popover')).toBeNull();
        expect(screen.queryByTestId('signal-style-backdrop')).toBeNull();
    });
});

describe('ChartSignalsSection — allowed signal types', () => {
    beforeEach(async () => {
        await setupI18n();
    });

    it('offers only Asset comparison and preserves hidden configs when adding and unfiltering', async () => {
        const onchange = vi.fn();
        const props = {
            signals: [HIDDEN_SIGNAL],
            allowedSignalTypes: ['asset-comparison'],
            signalsLoading: true,
            availableAssets: [
                {id: 101, display_name: 'Synthetic comparison one'},
                {id: 202, display_name: 'Synthetic comparison two'},
            ],
            onchange,
        };
        const view = render(ChartSignalsSection, props);

        expect(screen.getByTestId('signals-comparison-select-button')).toBeInTheDocument();
        expect(screen.queryByTestId('signals-indicator-select-button')).toBeNull();
        expect(screen.queryByTestId('signals-benchmark-select-button')).toBeNull();

        await fireEvent.click(screen.getByTestId('signals-comparison-select-button'));
        expect(screen.getByTestId('signal-tree-option-asset-comparison')).toBeInTheDocument();
        expect(screen.queryByTestId('signal-tree-option-fx-pair')).toBeNull();

        await fireEvent.click(screen.getByTestId('signal-tree-option-asset-comparison'));
        await waitFor(() => expect(onchange).toHaveBeenCalledTimes(1));

        const emitted = onchange.mock.calls[0][0] as SignalConfig[];
        expect(emitted.find((signal) => signal.id === HIDDEN_SIGNAL.id)).toEqual(HIDDEN_SIGNAL);
        expectHiddenSignalUnchanged(emitted);
        expect(emitted.find((signal) => signal.signalType === 'asset-comparison')).toBeDefined();
        expect(screen.getAllByTestId('signal-loading')).toHaveLength(1);

        await view.rerender({
            ...props,
            signals: emitted,
            allowedSignalTypes: undefined,
        });

        expect(screen.getByTestId('signals-benchmark-select-button')).toBeInTheDocument();
        expect(screen.getAllByTestId('signal-loading')).toHaveLength(2);

        const comparison = emitted.find((signal) => signal.signalType === 'asset-comparison');
        if (!comparison) throw new Error('Asset comparison config was not emitted');

        await view.rerender({...props, signals: emitted});
        expect(screen.getByTestId(`signal-card-${comparison.id}`)).toHaveAttribute('data-signal-type', 'asset-comparison');
        expect(screen.getByTestId(`signal-param-${comparison.id}-assetId`)).toBeInTheDocument();

        const assetSelectId = `signal-param-${comparison.id}-assetId-select`;
        const assetSelect = screen.getByTestId(assetSelectId);
        await fireEvent.click(within(assetSelect).getByTestId(`${assetSelectId}-trigger`));
        await fireEvent.click(screen.getByTestId('search-select-option-202'));
        await waitFor(() => expect(onchange).toHaveBeenCalledTimes(2));

        const parameterUpdate = onchange.mock.calls[1][0] as SignalConfig[];
        expectHiddenSignalUnchanged(parameterUpdate);
        expect(parameterUpdate.find((signal) => signal.id === comparison.id)?.params.assetId).toBe('202');
        await view.rerender({...props, signals: parameterUpdate});

        const styleSection = screen.getByTestId(`signal-style-${comparison.id}`);
        await fireEvent.click(within(styleSection).getByRole('button'));
        await fireEvent.click(within(styleSection).getByRole('button', {name: 'dashed'}));
        await waitFor(() => expect(onchange).toHaveBeenCalledTimes(3));

        const styleUpdate = onchange.mock.calls[2][0] as SignalConfig[];
        expectHiddenSignalUnchanged(styleUpdate);
        expect(styleUpdate.find((signal) => signal.id === comparison.id)?.style.lineType).toBe('dashed');
        await view.rerender({...props, signals: styleUpdate});

        await fireEvent.click(screen.getByTestId(`signal-remove-${comparison.id}`));
        await waitFor(() => expect(onchange).toHaveBeenCalledTimes(4));

        const removal = onchange.mock.calls[3][0] as SignalConfig[];
        expectHiddenSignalUnchanged(removal);
        expect(removal.find((signal) => signal.id === comparison.id)).toBeUndefined();
        await view.rerender({...props, signals: removal});
        expect(screen.queryByTestId(`signal-card-${comparison.id}`)).toBeNull();
        expect(screen.queryByTestId(`signal-card-${HIDDEN_SIGNAL.id}`)).toBeNull();

        await view.rerender({...props, signals: removal, allowedSignalTypes: undefined});
        expect(screen.getByTestId(`signal-card-${HIDDEN_SIGNAL.id}`)).toHaveAttribute('data-signal-type', HIDDEN_SIGNAL.signalType);
        expect(screen.queryByTestId(`signal-card-${comparison.id}`)).toBeNull();
    });
});

function mountCustomAestheticBounds() {
    const onchange = vi.fn();
    render(ChartAestheticsSection, {
        yAxisMode: 'custom',
        yAxisMin: 10,
        yAxisMax: 20,
        onchange,
    });

    return {
        onchange,
        min: screen.getByTestId('chart-axis-legacy-min') as HTMLInputElement,
        max: screen.getByTestId('chart-axis-legacy-max') as HTMLInputElement,
    };
}

describe('ChartAestheticsSection — custom numeric bounds', () => {
    beforeEach(async () => {
        await setupI18n();
    });

    it('uses the shared compact-number typography contract for both inputs', () => {
        const {min, max} = mountCustomAestheticBounds();

        expect(min).toHaveClass('lf-compact-number-input');
        expect(max).toHaveClass('lf-compact-number-input');
    });

    it('keeps typed minimum and maximum values numeric in the legacy callback', async () => {
        const {onchange, min, max} = mountCustomAestheticBounds();

        await fireEvent.input(min, {target: {value: '12.5'}});
        expect(onchange).toHaveBeenLastCalledWith({
            colorByBaseline: true,
            areaFill: true,
            gridLines: true,
            staleGradient: true,
            yAxisMode: 'custom',
            yAxisMin: 12.5,
            yAxisMax: 20,
        });

        await fireEvent.input(max, {target: {value: '42.75'}});
        expect(onchange).toHaveBeenCalledTimes(2);
        expect(onchange).toHaveBeenLastCalledWith({
            colorByBaseline: true,
            areaFill: true,
            gridLines: true,
            staleGradient: true,
            yAxisMode: 'custom',
            yAxisMin: 12.5,
            yAxisMax: 42.75,
        });
    });

    it('keeps shared ArrowUp and ArrowDown stepping active on both inputs', async () => {
        const {onchange, min, max} = mountCustomAestheticBounds();

        await fireEvent.keyDown(min, {key: 'ArrowUp'});
        await fireEvent.keyUp(min, {key: 'ArrowUp'});
        expect(min).toHaveValue(11);
        expect(onchange).toHaveBeenLastCalledWith(expect.objectContaining({yAxisMin: 11, yAxisMax: 20}));

        await fireEvent.keyDown(max, {key: 'ArrowDown'});
        await fireEvent.keyUp(max, {key: 'ArrowDown'});
        expect(max).toHaveValue(19);
        expect(onchange).toHaveBeenCalledTimes(2);
        expect(onchange).toHaveBeenLastCalledWith(expect.objectContaining({yAxisMin: 11, yAxisMax: 19}));
    });
});
