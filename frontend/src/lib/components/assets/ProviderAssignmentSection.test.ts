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
 * and the `data-testid` / `data-status` / `data-operation` the component
 * publishes. Never a translated label, never a CSS class, never geometry (jsdom
 * has no layout).
 *
 * Each `provider-test-result` row publishes the operation it reports in
 * `data-operation`: the backend's own operation names, `current_price` and
 * `history` — the strings the request sends in `operations` — or `probe` on the
 * one row that reports the probe call itself failing. That is the hook a caller
 * identifies a row by (`AssetModal.providerLifecycle.test.ts`); the probe cases
 * pin it.
 *
 * The probe's figures (M-18 CP3b) are read where the component writes them: the
 * current price and the history count that open their results' details, each
 * result's time and the total, all in the interface locale (`uiLocale()`, through
 * `formatFixed`). A row publishes its operation and its status and nothing
 * finer, so the figures and days inside it are found by structure — inside the
 * row, and in the list that holds the rows — and in those cases the labels that
 * tell the rows apart are compared through the catalogue (`$_`), never as
 * literals. Every expected figure is written by `Intl` itself. Its days (T-ISO) —
 * the current price's day and the history's range as the backend writes it — are
 * written in the house notation of a tooltip day, every expected day written by
 * `Intl` too.
 *
 * The probe's scope note (C-90): the manual probe reads only the last few days of
 * history, while creating the asset downloads all of it. Once a manual probe has
 * settled with a `history` row — a success or a warning — the section ends on one
 * `provider-test-scope-note` under the total time, in the catalogue's words
 * (`assets.probe.scopeNote`); none before a test, none while one runs, none when
 * the probe failed as a whole or answered without a history, none after an
 * automatic probe.
 *
 * The pure probe classifiers/formatters (`isSoftProbeFailure`,
 * `summarizeProbeError`, `buildProbeTooltipHtml`, …) are covered exhaustively in
 * `providerProbe.test.ts`; here we only prove the component wires them up.
 *
 * The provider's plugin settings (workstream X, lot CP11b) are the last block:
 * on a provider change the panel reads that provider's settings
 * (`GET /settings/plugins`, `family=asset`, `plugin_code`), ignoring an answer
 * overtaken by a newer change and a read that fails; with an entry it shows
 * `provider-settings-status` (`data-configured="false"`) only while the
 * provider still needs settings, and `provider-configure` (`data-configured`,
 * hidden when `readonly`, disabled with the panel), which opens
 * `PluginSettingsModal`; a save there refreshes the badge, and the dialog keeps
 * its form: it does not read the plugin again (PAS-S8). A case that does not
 * program the read gets the Proxy's `undefined`: the read fails on it, and the
 * panel takes a failed read as «no settings». The lifecycle cases route it
 * explicitly, answering no settings.
 *
 * The probe refused for too many probes (workstream X, X-R66) — red until
 * X-R66. Past `LIBREFOLIO_PROBE_RATE_LIMIT` probes a minute the endpoint
 * answers 429: `detail.error_code` PROBE_RATE_LIMITED with its `retry_after`
 * and the server's English, and `Retry-After`. Today the manual probe's one
 * `probe` row shows that English, as its one line and as its detail. Once
 * `probeRateLimitMessage` answers, both are its sentence: the catalogue's
 * PROBE_RATE_LIMITED with the time the pause ends — read through `$_`, the
 * clock pinned (Date only), never as a literal; the detail is read where the
 * row hands it over, its copy button (PAS-RL1). Any other failure of the probe
 * call keeps today's one line and detail (PAS-RL2, green before and after).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {get, writable} from 'svelte/store';
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
    // The panel reads the selected provider's plugin settings (workstream X, CP11): a planned request of its own,
    // answered «no settings» so that these cases keep proving the probe's lifecycle and nothing else.
    settings: vi.fn<(request: {queries: Record<string, string>}) => Promise<{plugins: unknown[]}>>(),
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
                    if (prop === 'get_plugin_settings_api_v1_settings_plugins_get') return lifecycleApi.settings;
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
import {_} from '$lib/i18n';
import {toasts} from '$lib/stores/app/toastStore.svelte';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatAxisDate} from '$lib/utils/core/formatAxisDate';
import {formatResumeTime, resumesToday} from './resolveProviderError';

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

/**
 * The result rows as `<operation>:<status>`, sorted: what each `provider-test-result` publishes in `data-operation`
 * — the backend's own operation names (`current_price`, `history`), or `probe` for the probe call's own failure —
 * and `data-status`. The hook a caller identifies a row by, whatever the order and the interface language.
 */
function operationStatuses(rows: HTMLElement[]): string[] {
    return rows.map((row) => `${row.getAttribute('data-operation')}:${row.getAttribute('data-status')}`).sort();
}

beforeEach(async () => {
    await setupI18n();
    vi.clearAllMocks();
    listFn().mockResolvedValue(PROVIDERS as never);
});

/**
 * The clipboard surface, stubbed per test and put back after it. jsdom has none of
 * `navigator.clipboard`, `window.isSecureContext`, `document.execCommand`: each stub
 * is an own property, and `restoreStubs()` (in `afterEach`) deletes it again — or
 * restores what was there — newest first.
 */
const stubbed: {target: object; key: string; before: PropertyDescriptor | undefined}[] = [];

function stubProperty(target: object, key: string, value: unknown) {
    stubbed.push({target, key, before: Object.getOwnPropertyDescriptor(target, key)});
    Object.defineProperty(target, key, {value, configurable: true, writable: true});
}

function restoreStubs() {
    for (const {target, key, before} of stubbed.splice(0).reverse()) {
        if (before) Object.defineProperty(target, key, before);
        else Reflect.deleteProperty(target, key);
    }
}

/**
 * Plain HTTP as Chromium presents it: not a secure context, and no
 * `navigator.clipboard` at all. The legacy `execCommand('copy')` succeeds and
 * records what the hidden textarea held at that moment.
 */
function onPlainHttp() {
    const captured: (string | undefined)[] = [];
    const execCommand = vi.fn((_command: string) => {
        captured.push(document.querySelector('textarea')?.value);
        return true;
    });
    stubProperty(window, 'isSecureContext', false);
    stubProperty(navigator, 'clipboard', undefined);
    stubProperty(document, 'execCommand', execCommand);
    return {execCommand, captured};
}

afterEach(() => {
    restoreStubs();
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
        // Each row names its operation: the hook a caller (AssetModal's lifecycle spec) identifies it by.
        expect(operationStatuses(rows), 'the rows do not publish their operations: one current_price and one history, each a success').toEqual(['current_price:success', 'history:success']);
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
        expect(screen.getByTestId('provider-test-result-copy')).toBeInTheDocument();
    });

    it('copies the error detail on plain HTTP through the legacy path, and confirms it once', async () => {
        probeFn().mockResolvedValue({
            current_price: {success: false, error: 'HTTP 500 upstream', error_code: 'HTTP_ERROR', execution_time_ms: 40},
        } as never);
        // HTTP_ERROR has no catalogue entry, so the row's detail is the backend's own error text.
        expect(get(_)('providerErrors.HTTP_ERROR')).toBe('providerErrors.HTTP_ERROR');
        mount({providerCode: 'yahoo', identifier: 'AAPL'});
        await waitLoaded('Yahoo');
        await fireEvent.click(testBtn());
        await waitFor(() => expect(testBtn()).toHaveAttribute('data-status', 'failed'));
        // No textarea on the page before the click: the one the stub reads can only be the copy's.
        expect(document.querySelector('textarea')).toBeNull();
        // And no toast yet: whatever is counted below, the copy click produced it.
        expect(toasts.info).not.toHaveBeenCalled();
        const http = onPlainHttp();

        await fireEvent.click(screen.getByTestId('provider-test-result-copy'));

        await waitFor(() => expect(http.execCommand).toHaveBeenCalledTimes(1));
        expect(http.execCommand).toHaveBeenCalledWith('copy');
        expect(http.captured).toEqual(['HTTP 500 upstream']);
        await waitFor(() => expect(toasts.info).toHaveBeenCalledTimes(1));
        expect(toasts.error).not.toHaveBeenCalled();
        expect(document.querySelector('textarea')).toBeNull();
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
        // A soft failure keeps its operation's row: the same two operations, each a warning.
        expect(operationStatuses(rows), 'the soft-failure rows do not publish their operations: one current_price and one history, each a warning').toEqual(['current_price:warning', 'history:warning']);
    });

    it('marks the probe failed when the probe call itself throws', async () => {
        probeFn().mockRejectedValue(new Error('network down') as never);
        const {onchange} = mount({providerCode: 'yahoo', identifier: 'AAPL'});
        await waitLoaded('Yahoo');

        await fireEvent.click(testBtn());
        await waitFor(() => expect(testBtn()).toHaveAttribute('data-status', 'failed'));
        expect(onchange.mock.calls.at(-1)?.[0]).toMatchObject({testStatus: 'failed'});
        // No operation answered: the one row reports the probe call itself, as `probe`, an error.
        expect(operationStatuses(screen.getAllByTestId('provider-test-result')), 'the probe call’s own failure is not exactly one row publishing probe, an error').toEqual(['probe:error']);
    });
});

// =========================================================================
describe('ProviderAssignmentSection — the probe figures in the interface language (M-18)', () => {
    /*
     * Four figures, each written through `formatFixed` in the interface locale, `uiLocale()`: the current
     * price that opens its result's detail (two decimals), the history's point count that opens its own
     * (no decimals, grouped the interface's way), each result's time and the total (seconds, two decimals).
     * On jsdom's en-US browser the interface locale is `en-US` for the English UI and bare `it` for the
     * Italian one: an en-US browser lends Italian no region.
     *
     * The word after the count (T-EN1): the count and its word are one catalogue message,
     * `assets.probe.points`, a plural on `count` with the figure as `n` — `12.345 punti`, `1 point` — before
     * the currency in brackets and the date range, which do not move. The last cases read it; the M-18 cases
     * read only the figure.
     *
     * The days (T-ISO). The current price's day, in brackets at the end of its detail, is written in the house
     * notation of a tooltip day — the lot charts' `formatAxisDate(uiLocale(), day, true)`: `2 gen 2024`,
     * `2 janv. 2024` — and so is the history's range when it is what the backend always writes,
     * `f"{min(dates)} → {max(dates)}"` (`provider_management.py`): a string that is exactly
     * `YYYY-MM-DD → YYYY-MM-DD` becomes `<start> → <end>`, each day in the house notation. Any other range is
     * shown as it came (the fixtures' `2020-01-01..2024-01-01` and `2020..2024` among them). Expected days come
     * from Intl (`houseDay`); red today in Italian and French, where both days are ISO.
     *
     * Handles. The rows are `provider-test-result`, each publishing its operation (`data-operation`) and its
     * status and nothing finer, so the rest is structure: a row is its label, its detail and its time — three
     * spans, in that order — and the total is the one line of the rows' list that holds no row. Here the labels
     * prove which row is which, read through the catalogue.
     */
    type ProbeResponse = z.infer<typeof schemas.FAProviderProbeResponse>;

    /** What the synthetic probe answers: the price as the backend sends it (a decimal string), the history's point count, each operation's time and the total; the current price's day and the history's range when a case names them. */
    interface ProbeInput {
        price: string;
        count: number;
        resultMs: number;
        totalMs: number;
        asOfDate?: string;
        dateRange?: string;
    }

    /** The probe's figures, as read off the section or as the expectation writes them. */
    interface Figures {
        /** The current price, as its result's detail opens. */
        price: string;
        /** The history's point count, as its result's detail opens. */
        count: string;
        /** Each result's time as written beside it: the current price's, then the history's. */
        times: string[];
        /** The total line, its label included. */
        total: string;
    }

    function figuresResponse({price, count, resultMs, totalMs, asOfDate = '2024-01-02', dateRange = '2020-01-01..2024-01-01'}: ProbeInput): ProbeResponse {
        return {
            provider_code: 'yahoo',
            identifier: 'AAPL',
            total_execution_time_ms: totalMs,
            current_price: {success: true, value: price, currency: 'USD', as_of_date: asOfDate, execution_time_ms: resultMs},
            history: {success: true, points_count: count, date_range: dateRange, execution_time_ms: resultMs},
        };
    }

    /** `value` with exactly `digits` decimals, as `Intl` writes it in `locale`: the oracle, never a literal. */
    function fixed(value: number, digits: number, locale: string): string {
        return new Intl.NumberFormat(locale, {minimumFractionDigits: digits, maximumFractionDigits: digits}).format(value);
    }

    function normalize(text: string | null | undefined): string {
        return (text ?? '').replace(/\s+/g, ' ').trim();
    }

    /** A catalogue word as the section words it: `$_`, in whatever language the catalogue speaks. */
    function word(key: string): string {
        return normalize(get(_)(key));
    }

    /** The figures as they must read in `locale`. */
    function expected({price, count, resultMs, totalMs}: ProbeInput, locale: string): Figures {
        const time = `(${fixed(resultMs / 1000, 2, locale)}s)`;
        return {
            price: fixed(Number(price), 2, locale),
            count: fixed(count, 0, locale),
            times: [time, time],
            total: `${word('assets.probe.totalTime')}: ${fixed(totalMs / 1000, 2, locale)}s`,
        };
    }

    /** A result row's parts, by structure: its label, its detail and its time — the row's three spans, in that order. */
    function partsOf(row: HTMLElement): {label: string; detail: string; time: string} {
        const spans = [...row.children].filter((child) => child.tagName === 'SPAN');
        expect(spans, 'a result row is its label, its detail and its time: three spans').toHaveLength(3);
        const [label, detail, time] = spans.map((span) => normalize(span.textContent));
        return {label, detail, time};
    }

    /** The figure a detail opens with: everything before its first space. */
    function opening(detail: string): string {
        return detail.split(' ')[0];
    }

    /** The list of results: the rows' nearest common ancestor. */
    function resultListOf(rows: HTMLElement[]): HTMLElement {
        for (let node = rows[0].parentElement; node; node = node.parentElement) {
            const candidate = node;
            if (rows.every((row) => candidate.contains(row))) return candidate;
        }
        throw new Error('the result rows share no list');
    }

    /** The total line, by structure: the one child of the results list that holds no result (the in-flight line is gone once the probe has settled). */
    function totalLineOf(rows: HTMLElement[]): string {
        const lines = [...resultListOf(rows).children].filter((child) => !rows.some((row) => child.contains(row)));
        expect(lines, 'besides its results, the list holds one line: the total').toHaveLength(1);
        return normalize(lines[0].textContent);
    }

    /** The figures as the section wrote them. */
    function figures(): Figures {
        const rows = screen.getAllByTestId('provider-test-result');
        expect(rows, 'barrier: one result per operation the synthetic response carries, two').toHaveLength(2);
        const [price, history] = rows.map((row) => partsOf(row));
        expect([price.label, history.label], 'the results are not the current price then the history (labels read through the catalogue)').toEqual([`${word('common.currentPrice')}:`, `${word('assets.probe.history')}:`]);
        return {price: opening(price.detail), count: opening(history.detail), times: [price.time, history.time], total: totalLineOf(rows)};
    }

    /** Mounts the section, runs the manual probe `input` answers, and waits until it has settled. */
    async function probeWith(input: ProbeInput): Promise<void> {
        probeFn().mockResolvedValue(figuresResponse(input));
        mount({providerCode: 'yahoo', identifier: 'AAPL'});
        await waitLoaded('Yahoo');
        await fireEvent.click(testBtn());
        await waitFor(() => expect(testBtn()).toHaveAttribute('data-status', 'passed'));
    }

    /** The interface language switched in place, as the language selector does, then Svelte's update boundary. */
    async function switchTo(language: 'en' | 'it'): Promise<void> {
        currentLanguage.set(language);
        await tick();
        flushSync();
    }

    afterEach(async () => {
        currentLanguage.set('en');
        await setupI18n('en');
    });

    it.each([{price: '1234.5'}, {price: '12345.5'}])('Italian UI: the current price $price, a history of 12345 points, each result’s 1234 ms and the 2468 ms total, all in Italian notation', async ({price}) => {
        const input: ProbeInput = {price, count: 12345, resultMs: 1234, totalMs: 2468};
        // An Italian UI is the catalogue and the language store together, as the language selector moves
        // them; the store is a plain writable in this file, so the catalogue is switched beside it.
        await setupI18n('it');
        currentLanguage.set('it');
        expect(uiLocale(), 'control: an Italian UI on jsdom’s en-US browser writes bare Italian').toBe('it');

        await probeWith(input);

        expect(figures(), 'the probe’s figures are not in Italian notation: the section still writes them with toFixed, a point in every language').toEqual(expected(input, 'it'));
    });

    it('follows an in-place switch while mounted: English (en-US, the count grouped from 1,000 on — the new contract) → Italian → English; the results recompute and every figure follows', async () => {
        // A price below 1,000, so its English form is the one it always had; the count from 1,000 on is
        // grouped in English too — the new contract, pinned by the English case below.
        const input: ProbeInput = {price: '123.456', count: 12345, resultMs: 1234, totalMs: 2468};
        await probeWith(input);
        const english = figures();

        // Only the language store moves; the catalogue stays English. A catalogue switch re-runs every
        // `$t` read — `buildTestResults` among them — and would refresh the figures even through a locale
        // read the section does not track: here the interface locale is the only road to them.
        await switchTo('it');
        expect(uiLocale(), 'control: the switch reached the interface locale').toBe('it');
        const italian = figures();

        await switchTo('en');
        expect(uiLocale(), 'control: and back, en-US on this browser').toBe('en-US');
        const englishAgain = figures();

        expect({english, italian, englishAgain}, 'the figures do not follow the interface language in place: the derived results and the times must be rewritten at each switch').toEqual({
            english: expected(input, 'en-US'),
            italian: expected(input, 'it'),
            englishAgain: expected(input, 'en-US'),
        });
    });

    it('English UI on an en-US browser: below 1,000 the figures read as before (123.46, 1.23s, 2.47s); a history count from 1,000 on is now grouped (12,345 points) — the new contract', async () => {
        const input: ProbeInput = {price: '123.456', count: 12345, resultMs: 1234, totalMs: 2468};
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser writes en-US').toBe('en-US');
        const english = expected(input, 'en-US');
        // Premises. Below 1,000, en-US writes exactly what toFixed wrote: those figures are guards the cure
        // must not move. From 1,000 on en-US groups, so the count is where the English contract changes.
        const toFixedTime = `(${(input.resultMs / 1000).toFixed(2)}s)`;
        expect({price: english.price, times: english.times, total: english.total}, 'premise: below 1,000, en-US writes what toFixed wrote').toEqual({
            price: Number(input.price).toFixed(2),
            times: [toFixedTime, toFixedTime],
            total: `${word('assets.probe.totalTime')}: ${(input.totalMs / 1000).toFixed(2)}s`,
        });
        expect(english.count, 'premise: en-US groups a count from 1,000 on, which the bare number does not').not.toBe(String(input.count));

        await probeWith(input);
        const written = figures();

        expect({price: written.price, times: written.times, total: written.total}, 'guard: below 1,000 the English figures read as they always did').toEqual({price: english.price, times: english.times, total: english.total});
        expect(written.count, 'new contract: the history count is grouped the interface’s way, 12,345 points in en-US').toBe(english.count);
    });

    /** The history result's detail as the section wrote it, its row found by its label (read through the catalogue). */
    function historyDetail(): string {
        const history = screen
            .getAllByTestId('provider-test-result')
            .map((row) => partsOf(row))
            .find((parts) => parts.label === `${word('assets.probe.history')}:`);
        if (!history) throw new Error('No result row is labelled as the history');
        expect(history.detail, 'barrier: the history succeeded, and its detail still ends on its date range').toMatch(/ — 2020-01-01\.\.2024-01-01$/);
        return history.detail;
    }

    /** What a history detail says before the currency in brackets: the count and the word that names it. */
    function countPhrase(detail: string): string {
        const currency = detail.indexOf(' (');
        return currency < 0 ? detail : detail.slice(0, currency);
    }

    /** The count and its word as the catalogue words them in the interface language — `assets.probe.points`, the figure as Intl writes it in `locale`. */
    function pointsPhrase(count: number, locale: string): string {
        return normalize(get(_)('assets.probe.points', {values: {count, n: fixed(count, 0, locale)}}));
    }

    it('Italian UI: a history of 12345 points is counted in the catalogue’s words — assets.probe.points, its plural, the figure in Italian notation (T-EN1)', async () => {
        await setupI18n('it');
        currentLanguage.set('it');
        expect(uiLocale(), 'control: an Italian UI on jsdom’s en-US browser writes bare Italian').toBe('it');

        await probeWith({price: '123.456', count: 12345, resultMs: 1234, totalMs: 2468});

        expect(countPhrase(historyDetail()), 'the history count is not worded by the catalogue: the section writes «points» in English after the figure').toBe(pointsPhrase(12345, 'it'));
    });

    it('English UI: a history of one point is counted in the singular — the catalogue’s «one» branch of assets.probe.points (T-EN1)', async () => {
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser writes en-US').toBe('en-US');

        await probeWith({price: '123.456', count: 1, resultMs: 1234, totalMs: 2468});

        expect(countPhrase(historyDetail()), 'one point is counted in the plural: the section writes «points» whatever the count').toBe(pointsPhrase(1, 'en-US'));
    });

    it('French UI: a history of one point is counted in the singular too (T-EN1)', async () => {
        await setupI18n('fr');
        currentLanguage.set('fr');
        expect(uiLocale(), 'control: a French UI on jsdom’s en-US browser writes bare French').toBe('fr');

        await probeWith({price: '123.456', count: 1, resultMs: 1234, totalMs: 2468});

        expect(countPhrase(historyDetail()), 'one point is not counted in the French catalogue’s words: the section writes «points» in English whatever the count').toBe(pointsPhrase(1, 'fr'));
    });

    it('English UI: a history of 12345 points reads as it does today — the English catalogue’s plural around the en-US figure (guard, T-EN1)', async () => {
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser writes en-US').toBe('en-US');

        await probeWith({price: '123.456', count: 12345, resultMs: 1234, totalMs: 2468});

        expect(countPhrase(historyDetail()), 'the English plural moved').toBe(pointsPhrase(12345, 'en-US'));
    });

    /** The calendar day `iso` in the house notation of a tooltip day, as Intl writes it in `locale`: numeric year, short month, numeric day. */
    function houseDay(iso: string, locale: string): string {
        const [year, month, day] = iso.split('-').map(Number);
        return new Intl.DateTimeFormat(locale, {year: 'numeric', month: 'short', day: 'numeric'}).format(new Date(year, month - 1, day));
    }

    /** The detail of the result labelled `labelKey` (read through the catalogue), as the section wrote it. */
    function detailOf(labelKey: string): string {
        const parts = screen
            .getAllByTestId('provider-test-result')
            .map((row) => partsOf(row))
            .find((candidate) => candidate.label === `${word(labelKey)}:`);
        if (!parts) throw new Error(`No result row is labelled ${labelKey}`);
        return parts.detail;
    }

    /** The current price's day: what its detail says in the brackets closing it. */
    function priceDay(): string | undefined {
        return /\(([^()]*)\)$/.exec(detailOf('common.currentPrice'))?.[1];
    }

    /** The history's range: what its detail says after its last dash. */
    function historyRange(): string {
        const detail = detailOf('assets.probe.history');
        const dash = detail.lastIndexOf(' — ');
        expect(dash, 'barrier: the history succeeded, and its detail ends on its date range after a dash').toBeGreaterThan(0);
        return detail.slice(dash + ' — '.length);
    }

    /** An Italian or a French UI: the catalogue and the language store together, as the language selector moves them. */
    async function speakAs(lang: 'it' | 'fr'): Promise<string> {
        await setupI18n(lang);
        currentLanguage.set(lang);
        const locale = uiLocale();
        expect(locale, `control: a ${lang} UI on jsdom’s en-US browser writes bare ${lang}`).toBe(lang);
        return locale;
    }

    it.each(['it', 'fr'] as const)('%s UI: the current price’s day, in the brackets closing its detail, is written in the house notation (T-ISO)', async (lang) => {
        const locale = await speakAs(lang);
        expect(houseDay('2024-01-02', locale), 'control: the oracle is the lot charts’ tooltip day').toBe(formatAxisDate(locale, '2024-01-02', true));

        await probeWith({price: '123.456', count: 12, resultMs: 1234, totalMs: 2468, asOfDate: '2024-01-02'});

        expect(priceDay(), `the current price’s day is not in the ${lang} interface’s notation: the section writes the ISO day`).toBe(houseDay('2024-01-02', locale));
    });

    it.each(['it', 'fr'] as const)('%s UI: the history’s range as the backend writes it, «2024-01-01 → 2024-01-08», is written day by day in the house notation (T-ISO)', async (lang) => {
        const locale = await speakAs(lang);

        await probeWith({price: '123.456', count: 6, resultMs: 1234, totalMs: 2468, dateRange: '2024-01-01 → 2024-01-08'});

        expect(historyRange(), `the history’s range is not in the ${lang} interface’s notation: the section writes the backend’s ISO days`).toBe(`${houseDay('2024-01-01', locale)} → ${houseDay('2024-01-08', locale)}`);
    });

    it.each(['2020-01-01..2024-01-01', '2020..2024'])('Italian UI: a range that is not exactly «YYYY-MM-DD → YYYY-MM-DD» — %s — is shown as it came (guard, T-ISO)', async (range) => {
        await speakAs('it');

        await probeWith({price: '123.456', count: 6, resultMs: 1234, totalMs: 2468, dateRange: range});

        expect(historyRange(), 'a range the backend does not write was rewritten').toBe(range);
    });
});

// =========================================================================
describe('ProviderAssignmentSection — the probe’s scope note (C-90)', () => {
    /*
     * The manual probe reads only the last few days of history, while creating the asset downloads all of it, and the
     * probe's few points were taken for what the asset would get. So a manual probe that has settled with a `history`
     * row — a success, or a warning — ends on one note under the total time, `provider-test-scope-note`, in the
     * catalogue's words (`assets.probe.scopeNote`). The note goes with the history row, not with the verdict: a probe
     * that failed on its current price has still read the history. No note before a test, none while one runs, none
     * when the probe failed as a whole (its one `probe` row) or answered without a history, and none after an
     * automatic probe, which draws no results.
     *
     * Every absence is asserted after a positive barrier — the button's status, and the rows the answer drew — so that
     * «no note» never means «not drawn yet». The note's words are compared through the catalogue, never as a literal,
     * and the catalogue must know them: a missing key renders as itself, and would match itself.
     */
    type ProbeResponse = z.infer<typeof schemas.FAProviderProbeResponse>;
    type Operations = Pick<ProbeResponse, 'current_price' | 'history'>;
    type Settled = 'passed' | 'failed';

    const NOTE = 'provider-test-scope-note';
    const PRICE_OK = {success: true, value: '100.50', currency: 'USD', as_of_date: '2024-01-05', execution_time_ms: 120};
    const PRICE_FAILED = {success: false, error: 'HTTP 500 upstream', error_code: 'HTTP_ERROR', execution_time_ms: 40};
    const HISTORY_OK = {success: true, points_count: 5, date_range: '2024-01-01 → 2024-01-05', sample_prices: [{date: '2024-01-05', close: '100.50'}], execution_time_ms: 300};
    const HISTORY_SOFT = {success: false, error: 'no prices in the days read', error_code: 'NO_DATA', execution_time_ms: 20};

    /** The probe's answer: the operations a case names, in 0.42 s. */
    function answer(operations: Operations): ProbeResponse {
        return {provider_code: 'yahoo', identifier: 'AAPL', total_execution_time_ms: 420, ...operations};
    }

    function normalize(text: string | null | undefined): string {
        return (text ?? '').replace(/\s+/g, ' ').trim();
    }

    /** A catalogue text as the section words it: `$_`, in whatever language the catalogue speaks. */
    function word(key: string): string {
        return normalize(get(_)(key));
    }

    /** Mounts the section, runs a manual probe, and waits until it has settled on `status`. */
    async function probeManually(status: Settled): Promise<void> {
        mount({providerCode: 'yahoo', identifier: 'AAPL'});
        await waitLoaded('Yahoo');
        await fireEvent.click(testBtn());
        await waitFor(() => expect(testBtn()).toHaveAttribute('data-status', status));
    }

    /** The list of results: the rows' nearest common ancestor, as the M-18 cases find it. */
    function resultListOf(rows: HTMLElement[]): HTMLElement {
        for (let node = rows[0].parentElement; node; node = node.parentElement) {
            const candidate = node;
            if (rows.every((row) => candidate.contains(row))) return candidate;
        }
        throw new Error('the result rows share no list');
    }

    /** The total line, by structure: the one line of the results list that holds no result, and is not, nor holds, the note. */
    function totalLineOf(rows: HTMLElement[], note: HTMLElement): HTMLElement {
        const lines = [...resultListOf(rows).children].filter((child): child is HTMLElement => child instanceof HTMLElement && !rows.some((row) => child.contains(row)) && !child.contains(note));
        expect(lines, 'besides its results and the note, the results list holds one line, the total: the note is a line of its own, not part of the total').toHaveLength(1);
        expect(normalize(lines[0].textContent).startsWith(`${word('assets.probe.totalTime')}:`), 'control: the line found is the total time, its label read through the catalogue').toBe(true);
        return lines[0];
    }

    interface Shown {
        /** What the history did, for the title. */
        history: string;
        operations: Operations;
        status: Settled;
        rows: string[];
    }

    const SHOWN: Shown[] = [
        {history: 'succeeded', operations: {current_price: PRICE_OK, history: HISTORY_OK}, status: 'passed', rows: ['current_price:success', 'history:success']},
        {history: 'failed softly, a warning (no prices in the days it read)', operations: {current_price: PRICE_OK, history: HISTORY_SOFT}, status: 'passed', rows: ['current_price:success', 'history:warning']},
        {history: 'succeeded while the current price failed for real', operations: {current_price: PRICE_FAILED, history: HISTORY_OK}, status: 'failed', rows: ['current_price:error', 'history:success']},
    ];

    it.each(SHOWN)('a manual probe whose history $history ends on one scope note, under the total time, in the catalogue’s words', async ({operations, status, rows}) => {
        probeFn().mockResolvedValue(answer(operations));

        await probeManually(status);

        const results = screen.getAllByTestId('provider-test-result');
        expect(operationStatuses(results), 'barrier: the rows the answer drew, a history among them').toEqual(rows);
        const notes = screen.queryAllByTestId(NOTE);
        expect(notes, 'no scope note under the result: nothing says the test read only the last few days, while creating the asset downloads its whole history').toHaveLength(1);
        const [note] = notes;
        expect(note).toBeVisible();
        const total = totalLineOf(results, note);
        expect(total.compareDocumentPosition(note) & Node.DOCUMENT_POSITION_FOLLOWING, 'the note is not under the total time').toBeTruthy();
        const words = word('assets.probe.scopeNote');
        expect(words, 'the shipped catalogue does not word the note: assets.probe.scopeNote is missing').not.toBe('assets.probe.scopeNote');
        expect(normalize(note.textContent), 'the note is not in the catalogue’s words, assets.probe.scopeNote').toBe(words);
    });

    it('says nothing before a test: no scope note while the configuration is untested', async () => {
        mount({providerCode: 'yahoo', identifier: 'AAPL'});
        await waitLoaded('Yahoo');

        // Barrier: the section is drawn and ready to test, and has not been tested.
        expect(testBtn()).toHaveAttribute('data-status', 'not_tested');
        expect(testBtn()).toBeEnabled();
        expect(screen.queryByTestId(NOTE), 'a scope note before any test').toBeNull();
    });

    it('says nothing while a test runs — not even when the result before it held a history', async () => {
        let settle!: (response: ProbeResponse) => void;
        probeFn()
            .mockResolvedValueOnce(answer({current_price: PRICE_OK, history: HISTORY_OK}))
            .mockImplementationOnce(
                () =>
                    new Promise<ProbeResponse>((resolve) => {
                        settle = resolve;
                    }),
            );
        await probeManually('passed');
        expect(operationStatuses(screen.getAllByTestId('provider-test-result')), 'barrier: the first test settled, a history among its rows').toEqual(['current_price:success', 'history:success']);

        await fireEvent.click(testBtn());

        // Barrier: the second test is in flight.
        expect(testBtn()).toHaveAttribute('data-status', 'testing');
        expect(testBtn()).toBeDisabled();
        expect(screen.queryByTestId(NOTE), 'a scope note while the test runs').toBeNull();

        settle(answer({current_price: PRICE_OK, history: HISTORY_OK}));
        await waitFor(() => expect(testBtn()).toHaveAttribute('data-status', 'passed'));
    });

    interface Silent {
        when: string;
        program: () => void;
        status: Settled;
        rows: string[];
    }

    const SILENT: Silent[] = [
        {when: 'the probe failed as a whole', program: () => probeFn().mockRejectedValue(new Error('network down')), status: 'failed', rows: ['probe:error']},
        {when: 'the answer holds no history', program: () => probeFn().mockResolvedValue(answer({current_price: PRICE_OK})), status: 'passed', rows: ['current_price:success']},
    ];

    it.each(SILENT)('says nothing when $when: no history row, no scope note', async ({when, program, status, rows}) => {
        program();

        await probeManually(status);

        expect(operationStatuses(screen.getAllByTestId('provider-test-result')), 'barrier: the rows the probe drew, none of them a history').toEqual(rows);
        expect(screen.queryByTestId(NOTE), `a scope note when ${when}`).toBeNull();
    });

    it('says nothing after an automatic probe, which draws no results', async () => {
        probeFn().mockResolvedValue(answer({current_price: PRICE_OK, history: HISTORY_OK}));
        render(ProviderProbeLifecycleHarness, {providerCode: 'yahoo', identifier: 'AAPL'});
        await waitLoaded('Yahoo');

        await fireEvent.click(screen.getByTestId('provider-probe-auto'));

        // Barrier: the automatic answer, a history among it, has landed: its verdict is drawn.
        await waitFor(() => expect(testBtn()).toHaveAttribute('data-status', 'passed'));
        expect(probeFn()).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId(NOTE), 'a scope note after an automatic probe').toBeNull();
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
        lifecycleApi.settings.mockReset().mockResolvedValue({plugins: []});
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
            lifecycleApi.settings.mockReset();
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

// =========================================================================
describe('ProviderAssignmentSection — the provider’s plugin settings (workstream X, CP11b)', () => {
    const settingsFn = () => vi.mocked(zodiosApi.get_plugin_settings_api_v1_settings_plugins_get as never) as ReturnType<typeof vi.fn>;
    const writeFn = () => vi.mocked(zodiosApi.update_plugin_settings_api_v1_settings_plugins_bulk_patch as never) as ReturnType<typeof vi.fn>;

    /** A provider's entry as `GET /settings/plugins` answers it: one user API key, saved once the provider is configured. */
    function pluginEntry(code: string, configured: boolean) {
        return {
            family: 'asset',
            plugin_code: code,
            plugin_name: code,
            configured,
            fields: [
                {
                    key: 'api_key',
                    type: 'string',
                    scope: 'user',
                    secret: true,
                    required: true,
                    label: 'API key',
                    description: '',
                    options: [],
                    is_set: configured,
                    source: configured ? 'db' : 'none',
                    locked: false,
                    editable: true,
                    problem: null,
                    updated_at: null,
                },
            ],
        };
    }

    const answer = (...plugins: unknown[]) => ({plugins});
    /** The read of one provider's settings, as the panel asks for it. */
    const readOf = (code: string) => ({queries: {family: 'asset', plugin_code: code}});

    /**
     * Lets every answer already given reach the panel — one real macrotask, so every pending microtask runs first —
     * then flushes Svelte. Waits for no time to pass: used only before asserting that something did not appear, after
     * a positive barrier.
     */
    async function drain(): Promise<void> {
        await new Promise<void>((resolve) => setTimeout(resolve, 0));
        await tick();
        flushSync();
    }

    /**
     * Starts recording the values `data-busy` takes on `element`, from the DOM's own record of its changes, and returns
     * the reader: the values in order, the current one last, repeats folded (as in `EmailSettingsTab.test.ts`). Nothing
     * is sampled, so a flash is not missed.
     */
    function recordBusy(element: HTMLElement): () => Array<string | null> {
        const records: MutationRecord[] = [];
        const observer = new MutationObserver((batch) => {
            records.push(...batch);
        });
        observer.observe(element, {attributes: true, attributeFilter: ['data-busy'], attributeOldValue: true});
        return () => {
            records.push(...observer.takeRecords());
            observer.disconnect();
            const values = [...records.map((record) => record.oldValue), element.getAttribute('data-busy')];
            return values.filter((value, index) => index === 0 || value !== values[index - 1]);
        };
    }

    afterEach(() => {
        settingsFn().mockReset();
        writeFn().mockReset();
    });

    it('PAS-S1: reads the selected provider’s settings; a provider still to configure shows the badge and «Configure»', async () => {
        settingsFn().mockResolvedValue(answer(pluginEntry('yahoo', false)));

        mount({providerCode: 'yahoo'});

        expect(await screen.findByTestId('provider-settings-status')).toHaveAttribute('data-configured', 'false');
        const configure = screen.getByTestId('provider-configure');
        expect(configure).toHaveAttribute('data-configured', 'false');
        expect(configure).toBeEnabled();
        expect(settingsFn()).toHaveBeenCalledTimes(1);
        expect(settingsFn()).toHaveBeenCalledWith(readOf('yahoo'));
        expect(screen.queryByTestId('plugin-settings-modal'), 'the dialog opens on a click, not before').toBeNull();
    });

    it('PAS-S2: a configured provider shows «Configure» and no badge', async () => {
        settingsFn().mockResolvedValue(answer(pluginEntry('yahoo', true)));

        mount({providerCode: 'yahoo'});

        expect(await screen.findByTestId('provider-configure')).toHaveAttribute('data-configured', 'true');
        expect(screen.queryByTestId('provider-settings-status'), 'drawn with the button, from the same answer').toBeNull();
    });

    it.each([
        ['declares none', () => Promise.resolve(answer())],
        ['come back without its entry', () => Promise.resolve(answer(pluginEntry('justetf', false)))],
        ['cannot be read', () => Promise.reject(new Error('settings unavailable'))],
    ])('PAS-S3: a provider whose settings %s gets no badge and no «Configure», and the panel works as before', async (_label, reply) => {
        settingsFn().mockImplementation(reply);

        mount({providerCode: 'yahoo'});

        await waitLoaded('Yahoo');
        await waitFor(() => expect(settingsFn()).toHaveBeenCalledWith(readOf('yahoo')));
        await drain();
        expect(screen.queryByTestId('provider-settings-status')).toBeNull();
        expect(screen.queryByTestId('provider-configure')).toBeNull();
        expect(screen.getByTestId('provider-code-select')).toBeInTheDocument();
        expect(idInput()).toBeEnabled();
    });

    it('PAS-S4: a read-only panel shows the badge, and offers no «Configure»', async () => {
        settingsFn().mockResolvedValue(answer(pluginEntry('yahoo', false)));

        mount({providerCode: 'yahoo', readonly: true});

        expect(await screen.findByTestId('provider-settings-status')).toHaveAttribute('data-configured', 'false');
        expect(screen.queryByTestId('provider-configure')).toBeNull();
    });

    it('PAS-S5: a disabled panel disables «Configure»', async () => {
        settingsFn().mockResolvedValue(answer(pluginEntry('yahoo', true)));

        mount({providerCode: 'yahoo', disabled: true});

        expect(await screen.findByTestId('provider-configure')).toBeDisabled();
    });

    it('PAS-S6: «No provider» reads no settings at all', async () => {
        settingsFn().mockResolvedValue(answer(pluginEntry('yahoo', false)));

        mount({providerCode: 'yahoo', noProvider: true});

        // The catalogue is read with or without a provider, by an effect declared after the settings one.
        await waitFor(() => expect(listFn()).toHaveBeenCalled());
        await drain();
        expect(settingsFn()).not.toHaveBeenCalled();
        expect(screen.queryByTestId('provider-settings-status')).toBeNull();
        expect(screen.queryByTestId('provider-configure')).toBeNull();
    });

    it('PAS-S7: on a provider change, an answer about the previous provider that lands last changes nothing', async () => {
        let answerYahoo!: (value: unknown) => void;
        settingsFn().mockImplementation(({queries}: {queries: {plugin_code: string}}) =>
            queries.plugin_code === 'yahoo'
                ? new Promise((resolve) => {
                      answerYahoo = resolve;
                  })
                : Promise.resolve(answer(pluginEntry(queries.plugin_code, true))),
        );
        mount({providerCode: 'yahoo'});
        await waitLoaded('Yahoo');
        await waitFor(() => expect(settingsFn()).toHaveBeenCalledWith(readOf('yahoo')));

        await fireEvent.click(screen.getByTestId('provider-code-select-button'));
        await fireEvent.click(await screen.findByTestId('provider-option-justetf'));

        expect(await screen.findByTestId('provider-configure')).toHaveAttribute('data-configured', 'true');
        expect(settingsFn()).toHaveBeenLastCalledWith(readOf('justetf'));

        answerYahoo(answer(pluginEntry('yahoo', false)));
        await drain();

        expect(screen.queryByTestId('provider-settings-status'), 'yahoo needed settings, but yahoo is no longer the provider').toBeNull();
        expect(screen.getByTestId('provider-configure')).toHaveAttribute('data-configured', 'true');
    });

    it('PAS-S8: «Configure» opens the dialog on that provider; a save there refreshes the badge, and the dialog keeps its form — no read of its own again, no flash back to «loading»', async () => {
        let saved = false;
        settingsFn().mockImplementation(async ({queries}: {queries: {plugin_code: string}}) => answer(pluginEntry(queries.plugin_code, saved)));
        writeFn().mockImplementation(async () => {
            saved = true;
            return {results: [{family: 'asset', plugin_code: 'yahoo', field_key: 'api_key', scope: 'user', success: true, error_code: null, message: null}], success_count: 1};
        });
        mount({providerCode: 'yahoo'});
        expect(await screen.findByTestId('provider-settings-status'), 'premise: yahoo needs settings').toHaveAttribute('data-configured', 'false');
        expect(settingsFn().mock.calls, 'the panel’s read').toStrictEqual([[readOf('yahoo')]]);

        await fireEvent.click(screen.getByTestId('provider-configure'));

        const dialog = await screen.findByTestId('plugin-settings-modal');
        const form = await within(dialog).findByTestId('plugin-settings-form-yahoo');
        expect(form).toHaveAttribute('data-configured', 'false');
        expect(settingsFn().mock.calls, 'and the dialog’s, on opening').toStrictEqual([[readOf('yahoo')], [readOf('yahoo')]]);
        const content = dialog.querySelector<HTMLElement>('[data-plugin="yahoo"]');
        expect(content, 'the dialog’s content, about yahoo').not.toBeNull();
        expect(content).toHaveAttribute('data-busy', 'false');
        const dialogBusy = recordBusy(content as HTMLElement);

        await fireEvent.input(within(form).getByTestId('plugin-setting-secret-input'), {target: {value: 'sk-yahoo-00000001'}});
        await fireEvent.click(within(form).getByTestId('plugin-settings-save'));

        await waitFor(() => expect(screen.getByTestId('provider-configure')).toHaveAttribute('data-configured', 'true'));
        expect(screen.queryByTestId('provider-settings-status'), 'configured now: the badge goes').toBeNull();
        const currentForm = () => within(screen.getByTestId('plugin-settings-modal')).getByTestId('plugin-settings-form-yahoo');
        await waitFor(() => expect(currentForm(), 'the save, and the read after it, are over').toHaveAttribute('data-busy', 'false'));
        await drain();
        expect(currentForm(), 'the form the save was made in, refreshed in place: the dialog did not load again').toBe(form);
        expect(form).toHaveAttribute('data-configured', 'true');
        expect(dialogBusy(), 'the dialog never went back to «loading»').toEqual(['false']);
        expect(settingsFn().mock.calls, 'the panel’s read, the dialog’s on opening and the form’s after its save: no third read of the dialog’s own').toStrictEqual([[readOf('yahoo')], [readOf('yahoo')], [readOf('yahoo')]]);
        expect(writeFn().mock.calls).toStrictEqual([[{items: [{family: 'asset', plugin_code: 'yahoo', field_key: 'api_key', scope: 'user', secret_value: 'sk-yahoo-00000001'}]}]]);

        await fireEvent.click(within(screen.getByTestId('plugin-settings-modal')).getByTestId('plugin-settings-modal-close'));

        await waitFor(() => expect(screen.queryByTestId('plugin-settings-modal')).toBeNull());
        expect(screen.getByTestId('provider-configure'), '«Configure» stays, for the next change').toHaveAttribute('data-configured', 'true');
    });

    it('PAS-S9: a provider change closes «Configure», and the next provider’s state comes in with the dialog closed', async () => {
        settingsFn().mockImplementation(async ({queries}: {queries: {plugin_code: string}}) => answer(pluginEntry(queries.plugin_code, false)));
        const {rerender} = mount({providerCode: 'yahoo'});
        await fireEvent.click(await screen.findByTestId('provider-configure'));
        expect(await screen.findByTestId('plugin-settings-modal'), 'premise: the dialog is open on yahoo').toBeVisible();

        await rerender({providerCode: 'justetf'});

        await waitFor(() => expect(screen.queryByTestId('plugin-settings-modal')).toBeNull());
        await waitFor(() => expect(settingsFn()).toHaveBeenCalledWith(readOf('justetf')));
        expect(await screen.findByTestId('provider-settings-status'), 'justetf’s own state').toHaveAttribute('data-configured', 'false');
        expect(screen.queryByTestId('plugin-settings-modal'), 'and the dialog stays closed').toBeNull();
    });
});

// =========================================================================
describe('ProviderAssignmentSection — the probe refused for too many probes (workstream X, X-R66)', () => {
    /** «Now» when the refusal lands: 10 June 2026, 14:30:20 local time — a month with no daylight-saving change. */
    const NOW = new Date(2026, 5, 10, 14, 30, 20);
    /** The refusal's wait, in whole seconds as the server counts them: the pause ends at 14:31:02, written 14:32. */
    const WAIT = 42;
    const KEY = 'providerErrors.PROBE_RATE_LIMITED';
    /** The server's own English for the refusal (`backend/app/api/v1/assets/providers.py`): what the row shows today. */
    const SERVER_MESSAGE = 'Too many provider probes: try again later';

    /** A failed request as a zodios (axios) call rejects with it: the answer's status, its `detail` as sent, its headers. */
    function httpFailure(status: number, detail: unknown, headers: Record<string, string> = {}) {
        return Object.assign(new Error(`Request failed with status code ${status}`), {response: {status, data: {detail}, headers}});
    }

    /** The probe's refusal: 429, its code with the wait and the server's English, and `Retry-After` with the same seconds. */
    function probeRateLimited() {
        return httpFailure(429, {error_code: 'PROBE_RATE_LIMITED', retry_after: WAIT, message: SERVER_MESSAGE}, {'retry-after': String(WAIT)});
    }

    /** Whitespace as one space: Intl writes some times with a narrow no-break space, and the DOM is read as text. */
    function squash(text: string | null | undefined): string {
        return (text ?? '').replace(/\s+/g, ' ').trim();
    }

    /** Runs the manual probe `failure` refuses; ends on the one row of the probe call's own failure, the probe settled. */
    async function refusedProbeRow(failure: unknown): Promise<HTMLElement> {
        probeFn().mockRejectedValue(failure as never);
        mount({providerCode: 'yahoo', identifier: 'AAPL'});
        await waitLoaded('Yahoo');
        await fireEvent.click(testBtn());
        await waitFor(() => expect(testBtn()).toHaveAttribute('data-status', 'failed'));
        const rows = screen.getAllByTestId('provider-test-result');
        expect(operationStatuses(rows), 'barrier: one row, the probe call’s own failure — probe, an error, as today').toEqual(['probe:error']);
        return rows[0];
    }

    /** The row's one line, after its label: its summary. The row is its label, that line and its time — three spans, in that order. */
    function oneLineOf(row: HTMLElement): string {
        const spans = [...row.children].filter((child) => child.tagName === 'SPAN');
        expect(spans, 'a result row is its label, its one line and its time: three spans').toHaveLength(3);
        return squash(spans[1].textContent);
    }

    /** The row's detail, where the row hands it over: its copy button, on plain HTTP — the text of the legacy copy. */
    async function copiedDetail(row: HTMLElement): Promise<string | undefined> {
        const http = onPlainHttp();
        await fireEvent.click(within(row).getByTestId('provider-test-result-copy'));
        await waitFor(() => expect(http.execCommand).toHaveBeenCalledTimes(1));
        expect(http.captured, 'one copy, of the row’s detail').toHaveLength(1);
        return http.captured[0];
    }

    beforeEach(() => {
        // Only the clock: the moment the pause ends is computed from «now», by the section and by the expectation alike.
        vi.useFakeTimers({toFake: ['Date']});
        vi.setSystemTime(NOW);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('PAS-RL1: a manual probe refused with 429 PROBE_RATE_LIMITED — its row’s one line and its detail are the catalogue’s PROBE_RATE_LIMITED with the time the pause ends, not the server’s English', async () => {
        const row = await refusedProbeRow(probeRateLimited());
        expect(resumesToday(WAIT, NOW), 'premise: the pause ends today').toBe(true);
        const time = formatResumeTime(WAIT, NOW);
        const sentence = get(_)(KEY, {values: {time}});

        const oneLine = oneLineOf(row);
        expect(oneLine, 'the one line is no longer the server’s English').not.toBe(SERVER_MESSAGE);
        expect(oneLine, 'the one line is the catalogue’s PROBE_RATE_LIMITED, with the time the pause ends').toBe(squash(sentence));
        expect(oneLine, 'the time the pause ends, rounded up to the minute').toContain(squash(time));
        expect(await copiedDetail(row), 'the detail is the same sentence').toBe(sentence);
        expect(get(_)(KEY), `premise: the catalogue has ${KEY}`).not.toBe(KEY);
    });

    it.each<{when: string; failure: () => unknown; shown: string}>([
        {when: 'a 429 the probe’s limiter did not send, another code', failure: () => httpFailure(429, {error_code: 'SYNTHETIC_OTHER_LIMIT', retry_after: WAIT, message: 'Synthetic limit of another kind'}, {'retry-after': String(WAIT)}), shown: 'Synthetic limit of another kind'},
        {when: 'a request that got no answer', failure: () => new Error('Synthetic connection dropped'), shown: 'Synthetic connection dropped'},
    ])('PAS-RL2: guard — $when: as today, the row’s one line and its detail are the failure’s own message', async ({failure, shown}) => {
        const row = await refusedProbeRow(failure());

        expect(oneLineOf(row), 'the one line, as today').toBe(shown);
        expect(await copiedDetail(row), 'the detail, as today').toBe(shown);
    });
});
