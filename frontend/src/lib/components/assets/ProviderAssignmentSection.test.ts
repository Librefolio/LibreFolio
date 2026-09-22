// @vitest-environment jsdom
/**
 * ProviderAssignmentSection — component test (Vitest + jsdom).
 *
 * The reusable provider config block inside the asset modal: pick a provider,
 * type an identifier, fill dynamic params, run a "Test Configuration" probe, and
 * read the URLs back. It is worth a component test rather than E2E because every
 * interesting branch is a *state* the parent rarely reaches — a provider that
 * accepts exactly one identifier type, a params schema with a currency field, a
 * probe that returns a soft failure — and each one is a prop or a mocked API
 * response here instead of a seeded provider and a live network round-trip.
 *
 * What these tests assert is the `onchange` payload (the contract to the parent)
 * and the `data-testid` / `data-status` the component publishes. Never a
 * translated label, never a CSS class, never geometry (jsdom has no layout).
 *
 * The pure probe classifiers/formatters (`isSoftProbeFailure`,
 * `summarizeProbeError`, `buildProbeTooltipHtml`, …) are covered exhaustively in
 * `providerProbe.test.ts`; here we only prove the component wires them up.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {writable} from 'svelte/store';
import type {z} from 'zod';
import type {schemas} from '$lib/api/generated';
import type {ProviderConfiguration} from './providerProbeState.svelte';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import ProviderProbeLifecycleHarness from '$test/ProviderProbeLifecycleHarness.svelte';

type LifecycleProvider = z.infer<typeof schemas.FAProviderInfo>;
type LifecycleProbeRequest = z.infer<typeof schemas.FAProviderProbeRequest>;
type LifecycleProbeResponse = z.infer<typeof schemas.FAProviderProbeResponse>;

// The added lifecycle cases opt into explicit routes; the older cases keep
// their existing mock behaviour unchanged.
const lifecycleApi = vi.hoisted(() => ({
    enabled: false,
    unexpected: [] as string[],
    list: vi.fn<() => Promise<LifecycleProvider[]>>(),
    probe: vi.fn<(request: LifecycleProbeRequest) => Promise<LifecycleProbeResponse>>(),
}));

// --- Mocks --------------------------------------------------------------
// zodiosApi: a Proxy minting a cached spy per method, so `vi.mocked(zodiosApi.foo)`
// programs the same fn (same pattern as AssetModal.test.ts).
vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (lifecycleApi.enabled) {
                    if (prop === 'list_providers_api_v1_assets_provider_get') return lifecycleApi.list;
                    if (prop === 'probe_provider_config_api_v1_assets_provider_probe_post') return lifecycleApi.probe;
                    lifecycleApi.unexpected.push(prop);
                    throw new Error(`Unexpected provider lifecycle API method: ${prop}`);
                }
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});
vi.mock('$lib/stores/reference/currencyStore', () => ({
    currencyStoreVersion: writable(0),
    ensureCurrenciesLoaded: vi.fn(async () => undefined),
    getCurrencyInfo: vi.fn((code: string) => {
        const table: Record<string, {symbol: string; flag_emoji: string}> = {
            USD: {symbol: '$', flag_emoji: '🇺🇸'},
            EUR: {symbol: '€', flag_emoji: '🇪🇺'},
        };
        return table[code] ?? {code, name: code, symbol: code, flag_emoji: '🏳️', country_codes: [], country_names: []};
    }),
}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));

import ProviderAssignmentSection from './ProviderAssignmentSection.svelte';
import {zodiosApi} from '$lib/api';

// --- Provider fixtures --------------------------------------------------
// mockprov must be filtered out of the options; yahoo has an icon + help url +
// two accepted types; justetf accepts exactly one type (auto-set); paramprov has
// one of every generic field type; schedprov carries the scheduled_investment UI.
const PROVIDERS = [
    {code: 'yahoo', name: 'Yahoo', supports_search: true, params_schema: [], icon_url: 'http://x/yahoo.png', accepted_identifier_types: ['TICKER', 'ISIN'], provider_help_url: 'https://help.yahoo'},
    {code: 'justetf', name: 'JustETF', supports_search: false, params_schema: [], icon_url: null, accepted_identifier_types: ['ISIN']},
    {code: 'mockprov', name: 'Mock', supports_search: false, params_schema: []},
    {
        code: 'paramprov',
        name: 'ParamProv',
        supports_search: false,
        params_schema: [
            {key: 'note', type: 'text', required: true, description: 'Note', placeholder: 'a note'},
            {key: 'count', type: 'number', required: false, description: 'Count', default: 5},
            {key: 'lang', type: 'select', required: false, description: 'Language', options: ['en', 'it'], option_labels: {en: '🇬🇧 English'}},
            {key: 'base_currency', type: 'select', required: false, description: 'BaseCcy', options: ['USD', 'EUR']},
            {key: 'ccy', type: 'currency', required: false, description: 'Currency'},
        ],
    },
    {code: 'schedprov', name: 'Scheduled', supports_search: false, params_schema: [{key: '_ui_component', type: 'ui_component', required: false, description: '', default: 'scheduled_investment'}]},
];

const listFn = () => vi.mocked(zodiosApi.list_providers_api_v1_assets_provider_get as never) as ReturnType<typeof vi.fn>;
const probeFn = () => vi.mocked(zodiosApi.probe_provider_config_api_v1_assets_provider_probe_post as never) as ReturnType<typeof vi.fn>;

function mount(props: Record<string, unknown> = {}) {
    const onchange = vi.fn();
    return {onchange, ...render(ProviderAssignmentSection, {onchange, ...props})};
}

/** Wait until the async provider list has loaded (the selected label appears). */
async function waitLoaded(name: string) {
    await waitFor(() => expect(screen.getByText(name)).toBeInTheDocument());
}

const testBtn = () => screen.getByTestId('provider-test-config') as HTMLButtonElement;
const idInput = () => screen.getByTestId('provider-identifier') as HTMLInputElement;

beforeEach(async () => {
    await setupI18n();
    vi.clearAllMocks();
    listFn().mockResolvedValue(PROVIDERS as never);
});

// =========================================================================
describe('ProviderAssignmentSection — noProvider gate', () => {
    it('renders nothing of the config body when noProvider=true', async () => {
        mount({noProvider: true, providerCode: 'yahoo'});
        // The whole {#if !noProvider} block is skipped.
        expect(screen.queryByTestId('provider-code-select')).toBeNull();
        expect(screen.queryByTestId('provider-identifier')).toBeNull();
    });

    it('renders the provider select when noProvider=false', async () => {
        mount({providerCode: 'yahoo'});
        await waitLoaded('Yahoo');
        expect(screen.getByTestId('provider-code-select')).toBeInTheDocument();
    });
});

// =========================================================================
describe('ProviderAssignmentSection — provider options & selection', () => {
    it('excludes mockprov, renders both icon and no-icon options, and reports selection via onchange', async () => {
        const {onchange} = mount({providerCode: 'yahoo'});
        await waitLoaded('Yahoo');

        await fireEvent.click(screen.getByTestId('provider-code-select-button'));
        // yahoo has an icon, justetf has none — both option snippets render.
        expect(await screen.findByTestId('provider-option-yahoo')).toBeInTheDocument();
        expect(screen.getByTestId('provider-option-justetf')).toBeInTheDocument();
        // mockprov is filtered out of the dropdown entirely.
        expect(screen.queryByTestId('provider-option-mockprov')).toBeNull();

        await fireEvent.click(screen.getByTestId('provider-option-paramprov'));
        // handleProviderChange resets identifier + testStatus and emits.
        await waitFor(() => {
            const last = onchange.mock.calls.at(-1)?.[0];
            expect(last).toMatchObject({providerCode: 'paramprov', identifier: '', testStatus: 'not_tested'});
        });
    });

    it('shows the provider help link only when the selected provider has one', async () => {
        mount({providerCode: 'yahoo'});
        await waitLoaded('Yahoo');
        // yahoo has provider_help_url → a documentation anchor is rendered.
        expect(document.querySelector('a[href="https://help.yahoo"]')).not.toBeNull();
    });

    it('omits the help link for a provider without a help url', async () => {
        mount({providerCode: 'justetf'});
        await waitLoaded('JustETF');
        expect(document.querySelector('a[href^="https://help"]')).toBeNull();
    });
});

// =========================================================================
describe('ProviderAssignmentSection — identifier type', () => {
    it('auto-sets and locks the identifier type when the provider accepts exactly one', async () => {
        const {onchange} = mount({providerCode: 'justetf', identifierType: 'TICKER'});
        await waitLoaded('JustETF');
        // The auto-set effect switches TICKER → ISIN and emits.
        await waitFor(() => {
            const last = onchange.mock.calls.at(-1)?.[0];
            expect(last?.identifierType).toBe('ISIN');
        });
        // Locked: shown as a readonly div (the value the test controls), not a select.
        expect(screen.getByTestId('provider-id-type-locked')).toBeInTheDocument();
        expect(screen.queryByTestId('provider-id-type-select-button')).toBeNull();
    });

    it('offers a type dropdown when the provider accepts several types', async () => {
        mount({providerCode: 'yahoo'});
        await waitLoaded('Yahoo');
        // Not auto-set → the interactive type select is present (its counterpart of
        // the locked div asserted above), and the identifier field is editable.
        expect(screen.getByTestId('provider-id-type-select-button')).toBeInTheDocument();
        expect(screen.queryByTestId('provider-id-type-locked')).toBeNull();
        expect(idInput()).toBeInTheDocument();
        expect(idInput()).not.toBeDisabled();
    });

    it('drives the identifier placeholder from the identifier type', async () => {
        const {rerender} = mount({providerCode: 'yahoo', identifierType: 'URL'});
        await waitLoaded('Yahoo');
        expect(idInput().placeholder).toBe('https://example.com/price');

        await rerender({providerCode: 'yahoo', identifierType: 'ISIN'});
        expect(idInput().placeholder).toBe('IE00B4L5Y983');
    });

    it('hides the identifier field entirely for an AUTO_GENERATED type', async () => {
        mount({providerCode: 'yahoo', identifierType: 'AUTO_GENERATED'});
        await waitLoaded('Yahoo');
        // isAutoGenerated → id-type row, identifier input and provider-url section all hidden.
        expect(screen.queryByTestId('provider-identifier')).toBeNull();
        expect(document.querySelector('#provider-url-readonly')).toBeNull();
    });

    it('emits when the identifier is typed and marks the config not-tested', async () => {
        const {onchange} = mount({providerCode: 'yahoo'});
        await waitLoaded('Yahoo');
        await fireEvent.input(idInput(), {target: {value: 'AAPL'}});
        await waitFor(() => {
            const last = onchange.mock.calls.at(-1)?.[0];
            expect(last).toMatchObject({identifier: 'AAPL', testStatus: 'not_tested'});
        });
    });
});

// =========================================================================
describe('ProviderAssignmentSection — dynamic params', () => {
    it('renders one control per generic field and emits the changed param', async () => {
        const {onchange, container} = mount({providerCode: 'paramprov'});
        await waitLoaded('ParamProv');

        // text + number fields are present (currency + selects too, but those are
        // their own components with their own tests).
        const note = container.querySelector('#param-note') as HTMLInputElement;
        const count = container.querySelector('#param-count') as HTMLInputElement;
        expect(note).not.toBeNull();
        expect(count).not.toBeNull();

        await fireEvent.input(note, {target: {value: 'hello'}});
        await waitFor(() => {
            const last = onchange.mock.calls.at(-1)?.[0];
            // paramsSchema is non-empty → computedParams is the params object.
            expect(last?.providerParams).toMatchObject({note: 'hello'});
        });

        await fireEvent.input(count, {target: {value: '7'}});
        await waitFor(() => {
            const last = onchange.mock.calls.at(-1)?.[0];
            expect(last?.providerParams).toMatchObject({count: 7});
        });
    });

    it('seeds paramsValues from the providerParams prop', async () => {
        const {container} = mount({providerCode: 'paramprov', providerParams: {note: 'seeded'}});
        await waitLoaded('ParamProv');
        const note = container.querySelector('#param-note') as HTMLInputElement;
        await waitFor(() => expect(note.value).toBe('seeded'));
    });

    it('mounts the scheduled-investment editor when the params schema declares that UI', async () => {
        mount({providerCode: 'schedprov'});
        await waitLoaded('Scheduled');
        // uiComponent === 'scheduled_investment' → the child editor renders instead
        // of the generic field loop.
        expect(await screen.findByTestId('schedule-add-first-period')).toBeInTheDocument();
    });
});

// =========================================================================
describe('ProviderAssignmentSection — Test Configuration probe', () => {
    it('disables the test button until an identifier is present', async () => {
        mount({providerCode: 'yahoo'});
        await waitLoaded('Yahoo');
        expect(testBtn()).toBeDisabled();
    });

    it('marks the probe passed and propagates the provider URL on full success', async () => {
        probeFn().mockResolvedValue({
            current_price: {success: true, value: 100.5, currency: 'USD', as_of_date: '2024-01-02', execution_time_ms: 120},
            history: {success: true, points_count: 250, date_range: '2020..2024', execution_time_ms: 300, sample_prices: [{date: '2024-01-01', close: 99}]},
            total_execution_time_ms: 420,
            provider_url: 'https://prov/url',
        } as never);
        const {onchange, container} = mount({providerCode: 'yahoo', identifier: 'AAPL'});
        await waitLoaded('Yahoo');

        await fireEvent.click(testBtn());
        await waitFor(() => expect(testBtn()).toHaveAttribute('data-status', 'passed'));
        // Both operations rendered a result row, each flagged success (the {#each}
        // and the success-icon branch actually ran, not merely the button status).
        const rows = screen.getAllByTestId('provider-test-result');
        expect(rows).toHaveLength(2);
        expect(rows.every((r) => r.getAttribute('data-status') === 'success')).toBe(true);
        // provider_url from the response flowed into the readonly URL field…
        const urlField = container.querySelector('#provider-url-readonly') as HTMLInputElement;
        expect(urlField.value).toBe('https://prov/url');
        // …and the final emit carried the passed status.
        expect(onchange.mock.calls.at(-1)?.[0]).toMatchObject({testStatus: 'passed'});
    });

    it('marks the probe failed on a real error and offers a copy button', async () => {
        probeFn().mockResolvedValue({
            current_price: {success: false, error: 'HTTP 500 upstream', error_code: 'HTTP_ERROR', execution_time_ms: 40},
        } as never);
        mount({providerCode: 'yahoo', identifier: 'AAPL'});
        await waitLoaded('Yahoo');

        await fireEvent.click(testBtn());
        await waitFor(() => expect(testBtn()).toHaveAttribute('data-status', 'failed'));
        // A real error row exposes the copy-to-clipboard control.
        expect(document.querySelector('button[title="Copy error detail"]')).not.toBeNull();
    });

    it('keeps the probe passed when every failure is a soft (warning) failure', async () => {
        probeFn().mockResolvedValue({
            current_price: {success: false, error: 'no data today', error_code: 'NO_DATA', execution_time_ms: 30},
            history: {success: false, error: 'not implemented', error_code: 'NOT_IMPLEMENTED', execution_time_ms: 20},
        } as never);
        mount({providerCode: 'yahoo', identifier: 'AAPL'});
        await waitLoaded('Yahoo');

        await fireEvent.click(testBtn());
        // hasRealError is false → passed even though both operations failed softly.
        await waitFor(() => expect(testBtn()).toHaveAttribute('data-status', 'passed'));
        // Both rows rendered as warnings (the {:else if warning} icon branch ran).
        const rows = screen.getAllByTestId('provider-test-result');
        expect(rows).toHaveLength(2);
        expect(rows.every((r) => r.getAttribute('data-status') === 'warning')).toBe(true);
    });

    it('marks the probe failed when the probe call itself throws', async () => {
        probeFn().mockRejectedValue(new Error('network down') as never);
        const {onchange} = mount({providerCode: 'yahoo', identifier: 'AAPL'});
        await waitLoaded('Yahoo');

        await fireEvent.click(testBtn());
        await waitFor(() => expect(testBtn()).toHaveAttribute('data-status', 'failed'));
        expect(onchange.mock.calls.at(-1)?.[0]).toMatchObject({testStatus: 'failed'});
    });
});

// =========================================================================
describe('ProviderAssignmentSection — readonly & disabled', () => {
    it('hides the test button and disables inputs when readonly', async () => {
        mount({providerCode: 'yahoo', identifier: 'AAPL', readonly: true});
        await waitLoaded('Yahoo');
        expect(screen.queryByTestId('provider-test-config')).toBeNull();
        expect(idInput()).toBeDisabled();
    });

    it('disables the identifier input when disabled', async () => {
        mount({providerCode: 'yahoo', identifier: 'AAPL', disabled: true});
        await waitLoaded('Yahoo');
        expect(idInput()).toBeDisabled();
    });
});

// =========================================================================
describe('ProviderAssignmentSection — probe ownership lifecycle', () => {
    const providers: LifecycleProvider[] = [
        {
            code: 'lifecycle-a',
            name: 'Lifecycle A',
            description: 'Synthetic provider with an editable parameter',
            supports_search: false,
            params_schema: [{key: 'note', type: 'text', required: true, description: ''}],
            accepted_identifier_types: ['TICKER', 'ISIN'],
            supports_meaningful_volume: false,
        },
        {
            code: 'lifecycle-b',
            name: 'Lifecycle B',
            description: 'Synthetic alternative provider without parameters',
            supports_search: false,
            params_schema: [],
            accepted_identifier_types: ['TICKER', 'ISIN'],
            supports_meaningful_volume: false,
        },
    ];
    const pending: Array<() => Promise<void>> = [];

    function configuration(): ProviderConfiguration {
        return {
            providerCode: 'lifecycle-a',
            identifier: 'OWNED.PROBE',
            identifierType: 'TICKER',
            providerParams: {note: 'owned note'},
            noProvider: false,
        };
    }

    function expectedRequest(): LifecycleProbeRequest {
        // Independent of the bound props, and frozen so a later UI edit cannot
        // change the oracle alongside the request reference retained by the spy.
        const request: LifecycleProbeRequest = {
            provider_code: 'lifecycle-a',
            identifier: 'OWNED.PROBE',
            identifier_type: 'TICKER',
            provider_params: {note: 'owned note'},
            operations: ['current_price', 'history'],
        };
        Object.freeze(request.provider_params);
        Object.freeze(request.operations);
        return Object.freeze(request);
    }

    function probeResponse(): LifecycleProbeResponse {
        return {
            provider_code: 'lifecycle-a',
            identifier: 'OWNED.PROBE',
            provider_url: 'https://provider.invalid/owned-probe',
            total_execution_time_ms: 9,
            current_price: {
                success: true,
                value: '123.45',
                currency: 'USD',
                as_of_date: '2024-01-02',
                execution_time_ms: 4,
            },
            history: {
                success: true,
                points_count: 1,
                date_range: '2024-01-01..2024-01-01',
                sample_prices: [{date: '2024-01-01', close: '123.40'}],
                execution_time_ms: 5,
            },
        };
    }

    function deferred<T>(fallback: T) {
        let resolve!: (value: T) => void;
        const promise = new Promise<T>((complete) => {
            resolve = complete;
        });
        async function finish(value: T = fallback) {
            resolve(value);
            // This is the promise actually returned to the component/controller,
            // followed by Svelte's update boundary, never clock-based polling.
            await promise;
            await tick();
            flushSync();
        }
        pending.push(() => finish());
        return {promise, finish};
    }

    function unexpected(operation: string): never {
        lifecycleApi.unexpected.push(operation);
        throw new Error(`Unplanned provider lifecycle request: ${operation}`);
    }

    function queueCatalogue() {
        const reply = deferred(providers);
        lifecycleApi.list.mockImplementationOnce(() => reply.promise);
        return reply;
    }

    function queueProbe() {
        const reply = deferred(probeResponse());
        lifecycleApi.probe.mockImplementationOnce((request) => {
            if (request.operations.join(',') !== 'current_price,history') {
                return unexpected(`probe operations: ${request.operations.join(',')}`);
            }
            return reply.promise;
        });
        return reply;
    }

    function expectManualResults(container: HTMLElement) {
        // getAllByTestId is the positive barrier: an empty result set throws.
        // Every row here belongs to this mount and this synthetic response.
        for (const row of within(container).getAllByTestId('provider-test-result')) {
            expect(row).toBeVisible();
            expect(row).toHaveAttribute('data-status', 'success');
        }
    }

    beforeEach(() => {
        lifecycleApi.enabled = true;
        lifecycleApi.unexpected.length = 0;
        pending.length = 0;
        lifecycleApi.list.mockReset().mockImplementation(() => unexpected('provider catalogue'));
        lifecycleApi.probe.mockReset().mockImplementation(() => unexpected('provider probe'));
    });

    afterEach(async () => {
        try {
            // Dispose every owner before releasing even an unused/failed-case
            // deferred. These cases do not change globals or client identity.
            await cleanup();
            for (const finish of pending) await finish();
            expect(lifecycleApi.unexpected).toEqual([]);
        } finally {
            lifecycleApi.enabled = false;
            lifecycleApi.list.mockReset();
            lifecycleApi.probe.mockReset();
            pending.length = 0;
        }
    });

    it('keeps shared manual work across collapse/remount and clears it on a provider switch', async () => {
        const catalogue = queueCatalogue();
        const firstRemount = queueCatalogue();
        const secondRemount = queueCatalogue();
        const manual = queueProbe();
        const request = expectedRequest();
        const onchange = vi.fn();
        const {container} = render(ProviderProbeLifecycleHarness, {...configuration(), onchange});
        await catalogue.finish();

        expect(testBtn()).toBeVisible();
        expect(testBtn()).toHaveAttribute('data-status', 'not_tested');
        expect(testBtn()).toBeEnabled();
        expect(idInput()).toHaveValue('OWNED.PROBE');
        expect(screen.getByTestId('param-note')).toHaveValue('owned note');

        await fireEvent.click(testBtn());
        expect(testBtn()).toHaveAttribute('data-status', 'testing');
        expect(testBtn()).toBeDisabled();
        expect(lifecycleApi.probe.mock.calls).toStrictEqual([[request]]);

        // The child disappears while its manual request is still in flight.
        // Only the parent-owned controller can accept the response now.
        await fireEvent.click(screen.getByTestId('provider-probe-collapse'));
        expect(screen.getByTestId('provider-probe-expand')).toBeEnabled();
        expect(screen.queryByTestId('provider-test-config')).toBeNull();
        await manual.finish();

        await fireEvent.click(screen.getByTestId('provider-probe-expand'));
        await firstRemount.finish();
        expect(testBtn()).toHaveAttribute('data-status', 'passed');
        expect(testBtn()).toBeEnabled();
        expectManualResults(container);
        expect(idInput()).toHaveValue('OWNED.PROBE');
        expect(screen.getByTestId('param-note')).toHaveValue('owned note');

        // A second collapse starts with visible results, proving that completed
        // manual details survive as well as the in-flight work above.
        await fireEvent.click(screen.getByTestId('provider-probe-collapse'));
        expect(screen.getByTestId('provider-probe-expand')).toBeEnabled();
        expect(screen.queryByTestId('provider-test-result')).toBeNull();
        await fireEvent.click(screen.getByTestId('provider-probe-expand'));
        await secondRemount.finish();
        expect(testBtn()).toHaveAttribute('data-status', 'passed');
        expectManualResults(container);

        await fireEvent.click(screen.getByTestId('provider-code-select-button'));
        expect(screen.getByTestId('provider-option-lifecycle-b')).toBeVisible();
        await fireEvent.click(screen.getByTestId('provider-option-lifecycle-b'));

        expect(idInput()).toBeVisible();
        expect(idInput()).toHaveValue('');
        expect(testBtn()).toHaveAttribute('data-status', 'not_tested');
        expect(testBtn()).toBeDisabled();
        expect(screen.queryByTestId('provider-test-result')).toBeNull();
        expect(screen.queryByTestId('param-note')).toBeNull();
        expect(onchange).toHaveBeenLastCalledWith({
            providerCode: 'lifecycle-b',
            identifier: '',
            identifierType: 'TICKER',
            providerParams: null,
            noProvider: false,
            testStatus: 'not_tested',
        });
        // The actual argument reference is still the original configuration;
        // neither remount nor the switch silently issued another probe.
        expect(lifecycleApi.probe.mock.calls).toStrictEqual([[request]]);
        expect(lifecycleApi.list.mock.calls).toStrictEqual([[], [], []]);
    });

    it('discards a standalone response after unmount before a fresh instance uses the same configuration', async () => {
        const oldCatalogue = queueCatalogue();
        const lateResponse = queueProbe();
        const request = expectedRequest();
        const oldOnchange = vi.fn();
        const oldMount = render(ProviderAssignmentSection, {...configuration(), onchange: oldOnchange});
        await oldCatalogue.finish();

        const oldButton = testBtn();
        expect(oldButton).toBeVisible();
        expect(oldButton).toBeEnabled();
        await fireEvent.click(oldButton);
        expect(oldButton).toHaveAttribute('data-status', 'testing');
        expect(oldButton).toBeDisabled();
        expect(lifecycleApi.probe.mock.calls).toStrictEqual([[request]]);
        expect(oldOnchange).not.toHaveBeenCalled();

        await oldMount.unmount();
        expect(oldButton).not.toBeInTheDocument();
        await lateResponse.finish();
        // A fresh mount alone would not catch the old destroyed child's late
        // emitChange: this callback proves its owner rejected the response.
        expect(oldOnchange).not.toHaveBeenCalled();

        const newCatalogue = queueCatalogue();
        const currentResponse = queueProbe();
        const newOnchange = vi.fn();
        const {container} = render(ProviderAssignmentSection, {...configuration(), onchange: newOnchange});
        await newCatalogue.finish();

        expect(testBtn()).toBeVisible();
        expect(testBtn()).toBeEnabled();
        expect(testBtn()).toHaveAttribute('data-status', 'not_tested');
        expect(idInput()).toHaveValue('OWNED.PROBE');
        expect(screen.getByTestId('param-note')).toHaveValue('owned note');
        expect(screen.queryByTestId('provider-test-result')).toBeNull();

        await fireEvent.click(testBtn());
        expect(testBtn()).toHaveAttribute('data-status', 'testing');
        expect(testBtn()).toBeDisabled();
        await currentResponse.finish();
        expect(testBtn()).toHaveAttribute('data-status', 'passed');
        expect(testBtn()).toBeEnabled();
        expectManualResults(container);
        expect(newOnchange).toHaveBeenLastCalledWith({...configuration(), testStatus: 'passed'});
        expect(oldOnchange).not.toHaveBeenCalled();
        expect(lifecycleApi.probe.mock.calls).toStrictEqual([[request], [request]]);
        expect(lifecycleApi.list.mock.calls).toStrictEqual([[], []]);
    });

    it('clears mounted parameter controls and verification when the parent resets params to null', async () => {
        const catalogue = queueCatalogue();
        const firstProbe = queueProbe();
        const originalRequest = expectedRequest();
        const onchange = vi.fn();
        const {container, rerender} = render(ProviderAssignmentSection, {...configuration(), onchange});
        await catalogue.finish();
        expect(idInput()).toHaveValue('OWNED.PROBE');
        expect(screen.getByTestId('param-note')).toHaveValue('owned note');
        expect(testBtn()).toBeEnabled();

        await fireEvent.click(testBtn());
        expect(testBtn()).toHaveAttribute('data-status', 'testing');
        await firstProbe.finish();
        expect(testBtn()).toHaveAttribute('data-status', 'passed');
        expectManualResults(container);

        // The schema remains mounted: disappearing controls on a provider switch
        // would not detect a stale local params object after this parent reset.
        await rerender({providerParams: null});
        await tick();
        flushSync();
        expect(screen.getByTestId('param-note')).toBeVisible();
        expect(screen.getByTestId('param-note')).toHaveValue('');
        expect(idInput()).toHaveValue('OWNED.PROBE');
        expect(testBtn()).toHaveAttribute('data-status', 'not_tested');
        expect(testBtn()).toBeEnabled();
        expect(screen.queryByTestId('provider-test-result')).toBeNull();

        const resetProbe = queueProbe();
        await fireEvent.click(testBtn());
        expect(testBtn()).toHaveAttribute('data-status', 'testing');
        expect(lifecycleApi.probe.mock.calls).toStrictEqual([[originalRequest], [{...originalRequest, provider_params: null}]]);
        await resetProbe.finish();
        expect(testBtn()).toHaveAttribute('data-status', 'passed');
        expectManualResults(container);
        expect(onchange).toHaveBeenLastCalledWith({...configuration(), providerParams: null, testStatus: 'passed'});
        expect(lifecycleApi.probe.mock.calls).toStrictEqual([[originalRequest], [{...originalRequest, provider_params: null}]]);
        expect(lifecycleApi.list.mock.calls).toStrictEqual([[]]);
    });

    it('preserves a standalone URL binding seed and probes with full params before the catalog resolves', async () => {
        const catalogue = queueCatalogue();
        const manual = queueProbe();
        const request = expectedRequest();
        const seedUrl = 'https://provider.invalid/stored-seed';
        const onchange = vi.fn();
        const {container, rerender} = render(ProviderProbeLifecycleHarness, {...configuration(), providerUrl: seedUrl, shared: false, onchange});
        await tick();
        flushSync();

        const boundUrl = screen.getByTestId('provider-probe-bound-url');
        expect(boundUrl).toHaveTextContent(seedUrl);
        expect(idInput()).toHaveValue('OWNED.PROBE');
        expect(testBtn()).toHaveAttribute('data-status', 'not_tested');
        expect(testBtn()).toBeEnabled();
        expect(lifecycleApi.list.mock.calls).toStrictEqual([[]]);

        // The catalogue is still pending. Provider params belong to the draft,
        // not to whichever schema the panel has managed to load so far.
        await fireEvent.click(testBtn());
        expect(testBtn()).toHaveAttribute('data-status', 'testing');
        expect(lifecycleApi.probe.mock.calls).toStrictEqual([[request]]);
        expect(boundUrl).toHaveTextContent(seedUrl);
        await manual.finish();
        expect(testBtn()).toHaveAttribute('data-status', 'passed');
        expect(boundUrl).toHaveTextContent('https://provider.invalid/owned-probe');
        expectManualResults(container);
        expect(onchange).toHaveBeenLastCalledWith({...configuration(), testStatus: 'passed'});

        await catalogue.finish();
        expect(screen.getByTestId('param-note')).toHaveValue('owned note');
        expect(testBtn()).toHaveAttribute('data-status', 'passed');
        expect(boundUrl).toHaveTextContent('https://provider.invalid/owned-probe');
        expect(lifecycleApi.probe.mock.calls).toStrictEqual([[request]]);

        await rerender({providerParams: null});
        await tick();
        flushSync();
        expect(screen.getByTestId('param-note')).toBeVisible();
        expect(screen.getByTestId('param-note')).toHaveValue('');
        expect(testBtn()).toHaveAttribute('data-status', 'not_tested');
        expect(boundUrl.textContent).toBe('');
        expect(screen.queryByTestId('provider-test-result')).toBeNull();
        expect(lifecycleApi.probe.mock.calls).toStrictEqual([[request]]);
    });

    it('shows an automatic result only as status until the section runs a manual probe', async () => {
        const catalogue = queueCatalogue();
        const automatic = queueProbe();
        const manual = queueProbe();
        const request = expectedRequest();
        const {container} = render(ProviderProbeLifecycleHarness, configuration());
        await catalogue.finish();

        expect(testBtn()).toBeVisible();
        expect(testBtn()).toHaveAttribute('data-status', 'not_tested');
        await fireEvent.click(screen.getByTestId('provider-probe-auto'));
        expect(testBtn()).toHaveAttribute('data-status', 'testing');
        expect(testBtn()).toBeDisabled();
        expect(lifecycleApi.probe.mock.calls).toStrictEqual([[request]]);
        await automatic.finish();

        // The completed status is the positive barrier before checking that
        // automatic work did not render manual-only detail rows.
        expect(testBtn()).toHaveAttribute('data-status', 'passed');
        expect(testBtn()).toBeEnabled();
        expect(screen.queryByTestId('provider-test-result')).toBeNull();

        await fireEvent.click(testBtn());
        expect(testBtn()).toHaveAttribute('data-status', 'testing');
        expect(testBtn()).toBeDisabled();
        await manual.finish();
        expect(testBtn()).toHaveAttribute('data-status', 'passed');
        expect(testBtn()).toBeEnabled();
        expectManualResults(container);
        expect(lifecycleApi.probe.mock.calls).toStrictEqual([[request], [request]]);
        expect(lifecycleApi.list.mock.calls).toStrictEqual([[]]);
    });
});
