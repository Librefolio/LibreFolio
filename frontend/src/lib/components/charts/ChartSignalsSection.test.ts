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
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {_ as t} from '$lib/i18n';
import {addMessages} from 'svelte-i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

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
import {OVERFLOW_MARQUEE_SELECTOR} from '$lib/actions/scrollOnOverflow';

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
    unavailablePoints: null,
    unavailableStart: null,
    unavailableEnd: null,
    resyncStart: null,
    resyncEnd: null,
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

describe('ChartSignalsSection — the units of a local benchmark’s parameters are worded by the catalogue (T-EN2)', () => {
    /*
     * The section draws the numeric controls of the local benchmarks (Linear, Compound, Sine) in a branch of
     * its own, and writes there each descriptor's `suffix` as it is: `%/yr` and `days` whatever the interface
     * language. The backend branch (`SignalParamControl`) already words its unit through
     * `signals.units.<suffix>`, keeping the raw suffix when the catalogue has no such key.
     *
     * The contract: the local branch words its unit the same way, and the descriptors carry tokens —
     * Linear's and Compound's `annualRate` the token `percentPerYear`, Sine's `period` the token `days`
     * (as today); `%` names no key and stays `%`. The descriptors are the registry's own: no definitions are
     * passed, so the section reads `getRegisteredSignalTypes()`. A unit is a word, not a figure, so the
     * catalogue alone decides it: the language is switched through svelte-i18n, as in the rest of this file.
     *
     * Handles: a control is `signal-param-<signal id>-<param key>`, and its unit is the element right after
     * its number input. The expected words are the catalogue's (`$_`), never typed.
     *
     * Red today: in Italian and in French the rate reads `%/yr` and the period `days`.
     */
    const LANGUAGES = ['it', 'fr'] as const;
    const benchmarkStyle: SignalConfig['style'] = {color: '#3b82f6', lineWidth: 1, lineType: 'dashed', markerStart: null, markerEnd: null};
    /** One card per local benchmark, each on its declared defaults. */
    const BENCHMARKS: SignalConfig[] = [
        {id: 'bench-linear', signalType: 'linear', params: {annualRate: 2, offset: 0}, style: benchmarkStyle},
        {id: 'bench-compound', signalType: 'compound', params: {annualRate: 8, offset: 0}, style: benchmarkStyle},
        {id: 'bench-sine', signalType: 'sine', params: {amplitude: 15, period: 45, offset: 0}, style: benchmarkStyle},
    ];

    afterEach(async () => {
        await setupI18n('en');
    });

    /** Mount the three benchmark cards in `lang`. */
    async function mountBenchmarks(lang: 'en' | (typeof LANGUAGES)[number]): Promise<void> {
        await setupI18n(lang);
        render(ChartSignalsSection, {signals: BENCHMARKS});
        for (const {id} of BENCHMARKS) expect(screen.getByTestId(`signal-card-${id}`), `barrier: the card ${id} is drawn`).toBeInTheDocument();
    }

    /** The unit written after the number input of the `key` control of the card `signalId`. */
    function unitOf(signalId: string, key: string): string | null {
        const control = screen.getByTestId(`signal-param-${signalId}-${key}`);
        const inputs = control.querySelectorAll('input[type="number"]');
        expect(inputs, `the ${key} control of ${signalId} holds one number input`).toHaveLength(1);
        return inputs[0].nextElementSibling?.textContent?.trim() ?? null;
    }

    /** A unit as the catalogue words it, after checking the catalogue has it: a missing key would read as the key itself. */
    function unitWord(key: string): string {
        const word = get(t)(key);
        expect(word, `premise: the catalogue has ${key}`).not.toBe(key);
        return word;
    }

    it.each(LANGUAGES)('%s interface: the annual rate of Linear and Compound reads signals.units.percentPerYear, the period of Sine signals.units.days', async (lang) => {
        await mountBenchmarks(lang);
        const perYear = unitWord('signals.units.percentPerYear');
        const days = unitWord('signals.units.days');

        expect({linearRate: unitOf('bench-linear', 'annualRate'), compoundRate: unitOf('bench-compound', 'annualRate'), sinePeriod: unitOf('bench-sine', 'period')}, `the units are not the ${lang} catalogue's: the local branch writes the descriptor's raw suffix`).toEqual({
            linearRate: perYear,
            compoundRate: perYear,
            sinePeriod: days,
        });
    });

    it.each(LANGUAGES)('%s interface: a percentage names no catalogue key and stays % (guard)', async (lang) => {
        await mountBenchmarks(lang);

        expect({
            linearOffset: unitOf('bench-linear', 'offset'),
            compoundOffset: unitOf('bench-compound', 'offset'),
            sineAmplitude: unitOf('bench-sine', 'amplitude'),
            sineOffset: unitOf('bench-sine', 'offset'),
        }).toEqual({linearOffset: '%', compoundOffset: '%', sineAmplitude: '%', sineOffset: '%'});
    });

    it('English interface: the rate and the period read as they do today, the English catalogue’s words (guard)', async () => {
        await mountBenchmarks('en');

        expect({linearRate: unitOf('bench-linear', 'annualRate'), compoundRate: unitOf('bench-compound', 'annualRate'), sinePeriod: unitOf('bench-sine', 'period')}).toEqual({
            linearRate: unitWord('signals.units.percentPerYear'),
            compoundRate: unitWord('signals.units.percentPerYear'),
            sinePeriod: unitWord('signals.units.days'),
        });
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

describe('ChartAestheticsSection — the y-axis scale is labelled from the catalogues (P, item 8)', () => {
    // Three labels of the y-axis scale are English written in the code: the auto mode prints 'Auto'
    // while its two neighbours already read `chartSettings.yAxisInclude0` and `common.custom`, and the
    // custom bounds are captioned 'Min' and 'Max' — in every language. The contract: the auto mode
    // reads `chartSettings.yAxisAuto`, a key the cure adds; the bounds read `common.min` and
    // `common.max`, which the four catalogues already have (Spanish writes them «Mín» and «Máx»).
    //
    // Observed without reading a language, in a marker locale: every key of the English catalogue,
    // and each key the cure adds, reads as a marker of itself (`⟦common.min⟧`), so a label the section
    // takes from the catalogue reads its marker and a literal written in it reads as itself. Whether
    // the four catalogues have the keys is asked of the JSON files, in the first case. Include 0 and
    // Custom are the control: they already come from the catalogue, and must read their markers.
    //
    // Red today: the auto mode reads 'Auto', the bounds 'Min' and 'Max'; no catalogue has
    // `chartSettings.yAxisAuto`.

    /** A private-use language (BCP 47 reserves qaa–qtz): Intl accepts it, and it is none of the app's catalogues. */
    const MARKER_LOCALE = 'qaa';
    const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

    /** How a label reads in the marker locale: `⟦key⟧`, or `⟦key n=3⟧` for a message given values. */
    const marked = (key: string, values: Record<string, string | number> = {}): string => `⟦${[key, ...Object.entries(values).map(([name, value]) => `${name}=${value}`)].join(' ')}⟧`;

    /** The value behind a dotted key of a catalogue, if any. */
    const leafOf = (catalogue: unknown, key: string): unknown => key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);

    /** Every dotted key of a catalogue that holds a string. */
    function stringKeysOf(node: unknown, prefix = ''): string[] {
        if (typeof node === 'string') return [prefix];
        if (node === null || typeof node !== 'object') return [];
        return Object.entries(node).flatMap(([part, child]) => stringKeysOf(child, prefix ? `${prefix}.${part}` : part));
    }

    /** Each of `keys` that some catalogue has no string for, with those catalogues: `{}` when all four have all of them. */
    function catalogueGaps(keys: readonly string[]): Record<string, string[]> {
        const gaps = keys.map((key) => [key, Object.entries(CATALOGUES).flatMap(([lang, catalogue]) => (typeof leafOf(catalogue, key) === 'string' ? [] : [lang]))] as const);
        return Object.fromEntries(gaps.filter(([, langs]) => langs.length > 0));
    }

    /** Switch svelte-i18n to the marker locale: every key of the English catalogue reads as its marker, and so does every key of `added` — a key the cure adds, with the names of its values. */
    async function useMarkerLocale(added: Record<string, readonly string[]>): Promise<void> {
        const messages: Record<string, string> = Object.fromEntries(stringKeysOf(en).map((key) => [key, marked(key)]));
        for (const [key, names] of Object.entries(added)) messages[key] = marked(key, Object.fromEntries(names.map((name) => [name, `{${name}}`])));
        addMessages(MARKER_LOCALE, messages);
        await setupI18n(MARKER_LOCALE);
    }

    beforeEach(async () => {
        await useMarkerLocale({'chartSettings.yAxisAuto': []});
    });

    afterEach(async () => {
        await setupI18n('en');
    });

    /** The section's custom y-axis row, mounted in the marker locale, after checking that the locale is live. */
    function mountMarkedBounds() {
        const bounds = mountCustomAestheticBounds();
        expect(screen.getByTestId('chart-axis-legacy-custom'), 'control: a mode the section already takes from the catalogue reads its marker').toHaveTextContent(marked('common.custom'));
        return bounds;
    }

    /** The texts around the two bound fields, in reading order: every text of the smallest element that holds both. */
    function boundCaptions(min: HTMLElement, max: HTMLElement): string[] {
        let frame = min.parentElement;
        while (frame && !frame.contains(max)) frame = frame.parentElement;
        if (!frame) throw new Error('the two bound fields share no element');
        const walker = document.createTreeWalker(frame, NodeFilter.SHOW_TEXT);
        const texts: string[] = [];
        for (let node = walker.nextNode(); node; node = walker.nextNode()) {
            const text = node.textContent?.trim();
            if (text) texts.push(text);
        }
        return texts;
    }

    it('the four catalogues have every label of the y-axis scale', () => {
        expect(catalogueGaps(['chartSettings.yAxisAuto', 'chartSettings.yAxisInclude0', 'common.custom', 'common.min', 'common.max']), 'key → the catalogues with no string for it').toEqual({});
    });

    it('names the auto mode chartSettings.yAxisAuto, as Include 0 and Custom beside it are named from the catalogue', () => {
        mountMarkedBounds();
        const modes = Object.fromEntries(['auto', 'include0', 'custom'].map((mode) => [mode, screen.getByTestId(`chart-axis-legacy-${mode}`).textContent?.trim()]));

        expect(modes).toEqual({auto: marked('chartSettings.yAxisAuto'), include0: marked('chartSettings.yAxisInclude0'), custom: marked('common.custom')});
    });

    it('captions the custom bounds common.min and common.max', () => {
        const {min, max} = mountMarkedBounds();

        expect(boundCaptions(min, max)).toEqual([marked('common.min'), marked('common.max')]);
    });
});

describe('ChartSignalsSection — the asset-comparison selector scrolls a long asset name with the project marquee (Y-38)', () => {
    /*
     * What it protects: the asset-comparison selector of the signals panel sits in a 192 px box, and both its closed
     * field and the rows of its list cut the asset's name with an ellipsis: a name is almost never readable whole
     * (developer's request, 20/10). Decision (a): the field AND the rows scroll, with the marquee the rest of the
     * project uses for asset names.
     *
     * The contract: in the closed field, and in each row of the open list, the option's label (the asset's display
     * name plus the suffix the section appends to it) sits in ONE element carrying the marquee's marker, as its text
     * and as its `title`. Nothing else changes: the closed field still shows the name, once.
     *
     * How it is read: the selector is `signal-param-<card id>-assetId-select`, its closed field `<selector>-trigger`,
     * read while closed (with the inline search, an open selector draws its search input there instead), and a row is
     * `search-select-option-<asset id>` inside the listbox. A marquee is found by `OVERFLOW_MARQUEE_SELECTOR`, the
     * marker the marquee itself is keyed on: a functional hook, not a style. jsdom has no layout, so nothing ever
     * overflows here: the contract is the element and its marker, not the motion.
     *
     * Red today: the field and the rows draw the label in a span that truncates it; no element carries the marker.
     */
    const LONG_NAME = 'Synthetic comparison asset with a deliberately long display name that never fits a 192 px field';
    /** The asset the card under test compares against: the long name, shown in its closed field. */
    const SELECTED = {id: 3801, display_name: LONG_NAME};
    /** The asset the panel's other comparison card holds: the list of the card under test marks it as used elsewhere. */
    const PINNED = {id: 3802, display_name: 'Synthetic peer asset already held by the other comparison card of the panel'};
    /** An asset no card holds: its label carries no suffix. */
    const FREE = {id: 3803, display_name: 'Synthetic free peer'};
    const ASSETS = [SELECTED, PINNED, FREE];
    /**
     * Each asset's label in the list of the card under test, as the section builds its `configuredAssets` options:
     * ' ✓' for the card's own asset, ' 📌' for an asset another comparison card holds, nothing for the rest. (' 👑',
     * the page's own asset, never reaches this list: the asset page leaves that asset out of `availableAssets`, and
     * no other page names an asset as its main one.)
     */
    const LABELS: Record<number, string> = {
        [SELECTED.id]: `${SELECTED.display_name} ✓`,
        [PINNED.id]: `${PINNED.display_name} 📌`,
        [FREE.id]: FREE.display_name,
    };
    const comparisonStyle: SignalConfig['style'] = {color: '#0ea5e9', lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null};
    /** The card under test. */
    const CARD: SignalConfig = {id: 'y38-comparison', signalType: 'asset-comparison', params: {assetId: String(SELECTED.id)}, style: comparisonStyle};
    /** The panel's other comparison card, holding PINNED. */
    const OTHER_CARD: SignalConfig = {id: 'y38-other-comparison', signalType: 'asset-comparison', params: {assetId: String(PINNED.id)}, style: comparisonStyle};
    const SELECT_ID = `signal-param-${CARD.id}-assetId-select`;

    beforeEach(async () => {
        await setupI18n();
    });

    function normalize(text: string | null | undefined): string {
        return (text ?? '').replace(/\s+/g, ' ').trim();
    }

    /** Every marquee inside `scope`, read as the text it shows and the title it carries. */
    function marqueeReadings(scope: HTMLElement): Array<{text: string; title: string | null}> {
        return [...scope.querySelectorAll<HTMLElement>(OVERFLOW_MARQUEE_SELECTOR)].map((marquee) => ({text: normalize(marquee.textContent), title: marquee.getAttribute('title')}));
    }

    /** Mount the panel with its two comparison cards: the selector of the card under test, and its closed field after checking it is closed. */
    function mountSelector(): {select: HTMLElement; field: HTMLElement} {
        render(ChartSignalsSection, {signals: [CARD, OTHER_CARD], definitions: [ASSET_COMPARISON_DEFINITION], availableAssets: ASSETS});
        const select = screen.getByTestId(SELECT_ID);
        const field = within(select).getByTestId(`${SELECT_ID}-trigger`);
        expect(field, 'barrier: the field is closed (an open selector draws its search input there instead)').toHaveAttribute('aria-expanded', 'false');
        return {select, field};
    }

    /** Open the list from the closed field: each asset's row, after checking it shows the asset's name. */
    async function openRows(select: HTMLElement, field: HTMLElement): Promise<Array<{id: number; row: HTMLElement}>> {
        await fireEvent.click(field);
        const listbox = await within(select).findByRole('listbox');
        return ASSETS.map(({id, display_name}) => {
            const row = within(listbox).getByTestId(`search-select-option-${id}`);
            expect(row, `barrier: the row of asset ${id} shows its name`).toHaveTextContent(display_name);
            return {id, row};
        });
    }

    it('the closed field holds the selected asset’s whole label in one marquee, as its text and its title', () => {
        // Today: the field draws the label in a span that truncates it, so the long name ends in an ellipsis; no
        // element of the field carries the marquee's marker.
        const {field} = mountSelector();
        expect(field, 'barrier: the closed field shows the selected asset').toHaveTextContent(LONG_NAME);

        expect(marqueeReadings(field), 'the closed field holds no marquee with the whole label: a long asset name is cut by an ellipsis instead of scrolling').toEqual([{text: LABELS[SELECTED.id], title: LABELS[SELECTED.id]}]);
    });

    it('each row of the open list holds its asset’s whole label in one marquee, as its text and its title', async () => {
        // Today: every row draws its label in a span that truncates it; no element of a row carries the marquee's
        // marker.
        const {select, field} = mountSelector();
        const rows = await openRows(select, field);

        const readings = Object.fromEntries(rows.map(({id, row}) => [id, marqueeReadings(row)]));
        expect(readings, 'a row of the list holds no marquee with its whole label: a long asset name is cut by an ellipsis instead of scrolling').toEqual(Object.fromEntries(ASSETS.map(({id}) => [id, [{text: LABELS[id], title: LABELS[id]}]])));
    });

    it('the closed field shows the selected asset’s whole name exactly once (guard)', () => {
        // Green today and after: the field's text holds the whole display name once. The marquee must neither drop it
        // (the name left to a title alone) nor duplicate it (a second copy for a seamless loop).
        const {field} = mountSelector();

        expect(normalize(field.textContent).split(LONG_NAME).length - 1, 'the closed field does not show the selected asset’s whole name exactly once: the marquee dropped or duplicated it').toBe(1);
    });
});
