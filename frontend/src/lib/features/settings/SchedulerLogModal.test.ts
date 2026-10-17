// @vitest-environment jsdom
/**
 * SchedulerLogModal — component test (Vitest + jsdom).
 *
 * The scheduler's execution history: one row per run, three filters, and a
 * collapsible detail table whose shape depends on which job produced the entry.
 * Almost none of it is reachable from a real backend on demand — the rows it
 * renders are whatever the scheduler happened to write, and a suite cannot ask
 * for a run that failed on three assets, succeeded on two FX pairs, and took
 * two minutes. Here the log is a fixture, so every shape is one line of setup.
 *
 * The translator is mocked with the identity, so `$_('common.currentPrice')`
 * renders as that key. The strings this file *does* assert literally —
 * `3/3 ✓`, `1m5s`, `(+2)` — are assembled by the component itself out of
 * numbers and punctuation and pass through no translation table; they are the
 * summary format, which is the contract under test.
 *
 * The entry rows publish `data-job`, `data-status`, `data-expanded` and
 * `data-has-detail`, and the list publishes `data-busy`. Nothing below reads a
 * CSS class, and nothing waits on the clock: the two timed behaviours (the
 * `since` window and the 500 ms long-press) use fake timers.
 *
 * A failed item without an error message is still rendered as a failure, never
 * as a success tick.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {readable} from 'svelte/store';
import {waitLocale} from 'svelte-i18n';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

// Partial on purpose: `$lib/stores/app/language`, reached through `formatFixed` → `uiLocale`, reads the
// catalogue constants (`DEFAULT_LOCALE`, `SUPPORTED_LOCALES`, …) from this module. Only the translator is replaced.
vi.mock('$lib/i18n', async (importOriginal) => ({...(await importOriginal<typeof import('$lib/i18n')>()), _: readable((key: string) => key)}));
vi.mock('$lib/api', () => ({zodiosApi: {axios: {get: vi.fn()}}}));
vi.mock('$lib/utils/clipboard', () => ({writeExportToClipboard: vi.fn()}));
vi.mock('$lib/stores/reference/currencyStore', () => ({
    getCurrencyInfo: (code: string) => (code === 'USD' ? {flag_emoji: '🇺🇸'} : {}),
}));
vi.mock('$lib/utils/providerHelpers', () => ({
    ensureAssetProvidersCached: vi.fn().mockResolvedValue(undefined),
    getAssetProviderIconUrl: (p: string) => (p === 'yahoo' ? 'https://icons.test/yahoo.png' : null),
    getFxProviderIconUrl: (p: string) => (p === 'ecb' ? 'https://icons.test/ecb.png' : null),
    parseProviderChain: (p?: string) => (p ? p.split('>') : []),
    PROVIDER_COLORS: {} as Record<string, string>,
    DEFAULT_PROVIDER_COLOR: '#888888',
}));

import SchedulerLogModal from './SchedulerLogModal.svelte';
import {zodiosApi} from '$lib/api';
import {currentLanguage} from '$lib/stores/app/language';
import {writeExportToClipboard} from '$lib/utils/clipboard';

const httpGet = vi.mocked(zodiosApi.axios.get);
const copied = vi.mocked(writeExportToClipboard);

type Entry = Record<string, unknown>;

/** A current_price run: `summary.ok` / `summary.err`, items in `items`. */
function priceRun(over: Entry = {}): Entry {
    return {
        ts: '2026-01-15T08:00:00Z',
        job: 'current_price',
        duration_s: 1.25,
        status: 'ok',
        summary: {ok: 2, err: 0},
        items: [
            {asset_id: 1, name: 'Apple', ok: true},
            {asset_id: 2, name: 'Nvidia', ok: true},
        ],
        ...over,
    };
}

/** A history_sync run: assets and FX counted separately. */
function historyRun(over: Entry = {}): Entry {
    return {
        ts: '2026-01-15T09:00:00Z',
        job: 'history_sync',
        duration_s: 65,
        status: 'ok',
        summary: {assets_ok: 1, assets_err: 0, fx_ok: 1, fx_err: 0},
        assets: [{asset_id: 1, name: 'Apple', status: 'ok', provider: 'yahoo', prices_changed: 3}],
        fx: [{pair: 'EUR/USD', base: 'EUR', quote: 'USD', status: 'ok', provider: 'ecb', points_changed: 5}],
        ...over,
    };
}

function list(): HTMLElement {
    return screen.getByTestId('scheduler-log-entries');
}

function rows(): HTMLElement[] {
    return screen.queryAllByTestId('scheduler-log-entry');
}

/** The single row for a job, addressed by the attribute the product publishes. */
function row(job: string): HTMLElement {
    const found = rows().filter((r) => r.getAttribute('data-job') === job);
    expect(found).toHaveLength(1);
    return found[0];
}

/** Renders with `open: true` and waits for the fetch the effect kicks off. */
async function mountWith(entries: Entry[] = [], open = true): Promise<{container: HTMLElement}> {
    httpGet.mockResolvedValue({data: {entries}} as never);
    const result = render(SchedulerLogModal, {open});
    if (open) await waitFor(() => expect(list()).toHaveAttribute('data-busy', 'false'));
    return {container: result.container};
}

/** Picks an option out of one of the three `SimpleSelect` filters. */
async function chooseFilter(which: 'job' | 'status' | 'time', value: string): Promise<void> {
    await fireEvent.click(screen.getByTestId(`scheduler-log-filter-${which}-button`));
    await fireEvent.click(screen.getByTestId(`scheduler-log-filter-${which}-option-${value}`));
}

/** The query params of the most recent GET. */
function lastParams(): Record<string, string> {
    const call = httpGet.mock.calls.at(-1) as [string, {params: Record<string, string>}];
    expect(call[0]).toBe('/api/v1/settings/scheduler/log');
    return call[1].params;
}

beforeEach(() => {
    httpGet.mockReset();
    copied.mockReset();
    copied.mockResolvedValue(undefined as never);
    vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.restoreAllMocks();
});

describe('fetching', () => {
    it('asks for the log as soon as it is opened', async () => {
        await mountWith([priceRun()]);

        expect(httpGet).toHaveBeenCalledOnce();
        expect(rows()).toHaveLength(1);
    });

    it('asks for nothing while it is closed', async () => {
        await mountWith([priceRun()], false);

        expect(httpGet).not.toHaveBeenCalled();
    });

    it('publishes that it is busy, then that it is not', async () => {
        let release!: (v: unknown) => void;
        httpGet.mockReturnValue(new Promise((res) => (release = res)) as never);
        render(SchedulerLogModal, {open: true});

        await waitFor(() => expect(list()).toHaveAttribute('data-busy', 'true'));

        release({data: {entries: []}});
        await waitFor(() => expect(list()).toHaveAttribute('data-busy', 'false'));
    });

    it('shows a placeholder only while the first load is still empty-handed', async () => {
        let release!: (v: unknown) => void;
        httpGet.mockReturnValue(new Promise((res) => (release = res)) as never);
        render(SchedulerLogModal, {open: true});

        await waitFor(() => expect(list()).toHaveAttribute('data-busy', 'true'));
        expect(screen.queryByTestId('scheduler-log-empty')).toBeNull();
        expect(rows()).toHaveLength(0);

        release({data: {entries: []}});
        await waitFor(() => expect(screen.getByTestId('scheduler-log-empty')).toBeInTheDocument());
    });

    it('keeps the rows on screen while it reloads, instead of blanking', async () => {
        // `loading && entries.length === 0` — the second half of that guard is
        // what stops a filter change from flashing the list away.
        await mountWith([priceRun()]);
        let release!: (v: unknown) => void;
        httpGet.mockReturnValue(new Promise((res) => (release = res)) as never);

        await chooseFilter('time', '7d');
        await waitFor(() => expect(list()).toHaveAttribute('data-busy', 'true'));
        expect(rows()).toHaveLength(1);

        release({data: {entries: []}});
        await waitFor(() => expect(list()).toHaveAttribute('data-busy', 'false'));
    });

    it('survives a response with no entries key at all', async () => {
        httpGet.mockResolvedValue({data: {}} as never);
        render(SchedulerLogModal, {open: true});

        await waitFor(() => expect(screen.getByTestId('scheduler-log-empty')).toBeInTheDocument());
    });

    it('stops being busy even when the request fails', async () => {
        httpGet.mockRejectedValue(new Error('Network Error'));
        render(SchedulerLogModal, {open: true});

        await waitFor(() => expect(list()).toHaveAttribute('data-busy', 'false'));
        expect(screen.getByTestId('scheduler-log-empty')).toBeInTheDocument();
    });

    it('refetches when the time window changes', async () => {
        await mountWith([priceRun()]);

        await chooseFilter('time', '7d');
        await waitFor(() => expect(httpGet).toHaveBeenCalledTimes(2));
    });

    it('does not refetch when a client-side filter changes', async () => {
        await mountWith([priceRun(), historyRun()]);

        await chooseFilter('job', 'history_sync');

        expect(httpGet).toHaveBeenCalledOnce();
    });

    it('collapses everything again when the window changes', async () => {
        await mountWith([priceRun()]);
        await fireEvent.click(within(row('current_price')).getByRole('button'));
        expect(row('current_price')).toHaveAttribute('data-expanded', 'true');

        await chooseFilter('time', '6h');
        await waitFor(() => expect(httpGet).toHaveBeenCalledTimes(2));

        expect(row('current_price')).toHaveAttribute('data-expanded', 'false');
    });
});

describe('the time window it asks the backend for', () => {
    const NOW = new Date('2026-01-15T12:00:00.000Z');
    const cases: [string, string][] = [
        ['1h', '2026-01-15T11:00:00.000Z'],
        ['6h', '2026-01-15T06:00:00.000Z'],
        ['24h', '2026-01-14T12:00:00.000Z'],
        ['7d', '2026-01-08T12:00:00.000Z'],
        ['30d', '2025-12-16T12:00:00.000Z'],
    ];

    it.each(cases)('%s becomes since=%s', async (filter, expected) => {
        vi.useFakeTimers();
        vi.setSystemTime(NOW);
        httpGet.mockResolvedValue({data: {entries: []}} as never);

        render(SchedulerLogModal, {open: true});
        await vi.advanceTimersByTimeAsync(0);

        if (filter !== '24h') {
            await chooseFilter('time', filter);
            await vi.advanceTimersByTimeAsync(0);
        }

        expect(lastParams().since).toBe(expected);
    });

    it('sends no window at all for "all time"', async () => {
        await mountWith([]);

        await chooseFilter('time', 'all');
        await waitFor(() => expect(httpGet).toHaveBeenCalledTimes(2));

        expect(lastParams()).toEqual({});
    });

    it('defaults to the last 24 hours', async () => {
        await mountWith([]);

        expect(lastParams()).toHaveProperty('since');
    });
});

describe('filtering what came back', () => {
    const mixed = () => [priceRun(), historyRun(), priceRun({ts: '2026-01-15T10:00:00Z', status: 'error', summary: {ok: 0, err: 1}, items: [{asset_id: 3, name: 'Broken', ok: false, error: 'boom'}]})];

    it('shows everything by default', async () => {
        await mountWith(mixed());

        expect(rows()).toHaveLength(3);
    });

    it('narrows to one job', async () => {
        await mountWith(mixed());

        await chooseFilter('job', 'history_sync');

        expect(rows()).toHaveLength(1);
        expect(rows()[0]).toHaveAttribute('data-job', 'history_sync');
    });

    it('narrows to one status', async () => {
        await mountWith(mixed());

        await chooseFilter('status', 'error');

        expect(rows()).toHaveLength(1);
        expect(rows()[0]).toHaveAttribute('data-status', 'error');
    });

    it('applies both filters at once', async () => {
        await mountWith(mixed());

        await chooseFilter('job', 'current_price');
        await chooseFilter('status', 'ok');

        expect(rows()).toHaveLength(1);
    });

    it('says so when the filters exclude everything', async () => {
        await mountWith(mixed());

        await chooseFilter('job', 'history_sync');
        await chooseFilter('status', 'error');

        expect(rows()).toHaveLength(0);
        expect(screen.getByTestId('scheduler-log-empty')).toBeInTheDocument();
    });

    it('goes back to everything when the filters are cleared', async () => {
        await mountWith(mixed());
        await chooseFilter('job', 'history_sync');

        await chooseFilter('job', 'all');

        expect(rows()).toHaveLength(3);
    });
});

describe('the one-line summary', () => {
    it('counts a clean price run', async () => {
        await mountWith([priceRun({summary: {ok: 3, err: 0}})]);

        expect(row('current_price')).toHaveTextContent('3/3 ✓');
    });

    it('adds the failures when there are any', async () => {
        await mountWith([priceRun({summary: {ok: 2, err: 1}})]);

        expect(row('current_price')).toHaveTextContent('2/3 ✓ · 1 ✗');
    });

    it('treats a summary with nothing in it as zero, not as blank', async () => {
        await mountWith([priceRun({summary: {}})]);

        expect(row('current_price')).toHaveTextContent('0/0 ✓');
    });

    it('mentions only assets when only assets ran', async () => {
        await mountWith([historyRun({summary: {assets_ok: 2, assets_err: 0}, fx: []})]);

        const text = row('history_sync').textContent ?? '';
        expect(text).toContain('2/2 assets');
        expect(text).not.toContain('FX');
    });

    it('mentions only FX when only FX ran', async () => {
        await mountWith([historyRun({summary: {fx_ok: 4, fx_err: 0}, assets: []})]);

        const text = row('history_sync').textContent ?? '';
        expect(text).toContain('4/4 FX');
        expect(text).not.toContain('assets');
    });

    it('joins both halves when both ran', async () => {
        await mountWith([historyRun({summary: {assets_ok: 1, assets_err: 1, fx_ok: 2, fx_err: 0}})]);

        expect(row('history_sync')).toHaveTextContent('1/2 assets · 2/2 FX · 1 ✗');
    });

    it('adds the two error counts together', async () => {
        await mountWith([historyRun({summary: {assets_ok: 0, assets_err: 2, fx_ok: 0, fx_err: 3}})]);

        expect(row('history_sync')).toHaveTextContent('0/2 assets · 0/3 FX · 5 ✗');
    });

    it('says nothing rather than "0/0" for a history run that did nothing', async () => {
        await mountWith([historyRun({summary: {}, assets: [], fx: []})]);

        const text = row('history_sync').textContent ?? '';
        expect(text).not.toContain('assets');
        expect(text).not.toContain('✗');
    });
});

describe('how long it took', () => {
    const cases: [string, unknown, string][] = [
        ['a fraction of a minute', 1.25, '1.3s'],
        ['exactly nothing', 0, '0.0s'],
        ['just under a minute', 59.9, '59.9s'],
        ['a minute and a bit', 65, '1m5s'],
        ['a round two minutes', 120, '2m0s'],
        ['a duration the log did not record', undefined, '—'],
        ['a null duration', null, '—'],
    ];

    it.each(cases)('%s reads as %s', async (_name, duration, expected) => {
        await mountWith([priceRun({duration_s: duration})]);

        expect(row('current_price')).toHaveTextContent(expected);
    });
});

describe('the preview of what was touched', () => {
    it('lists them all while they are few', async () => {
        await mountWith([
            priceRun({
                items: [
                    {asset_id: 1, name: 'Apple', ok: true},
                    {asset_id: 2, name: 'Nvidia', ok: true},
                ],
            }),
        ]);

        expect(row('current_price')).toHaveTextContent('Apple, Nvidia');
    });

    it('counts the rest once there are too many', async () => {
        await mountWith([priceRun({items: ['Apple', 'Nvidia', 'Tesla', 'Meta', 'Amazon'].map((name, i) => ({asset_id: i, name, ok: true}))})]);

        expect(row('current_price')).toHaveTextContent('Apple, Nvidia, Tesla (+2)');
    });

    it('draws assets and FX pairs from the same list', async () => {
        await mountWith([
            historyRun({
                assets: [{asset_id: 1, name: 'Apple', status: 'ok'}],
                fx: [{pair: 'EUR/USD', status: 'ok'}],
            }),
        ]);

        expect(row('history_sync')).toHaveTextContent('Apple, EUR/USD');
    });

    it('stands in for a nameless asset and a nameless pair', async () => {
        await mountWith([
            historyRun({
                assets: [{asset_id: 1, status: 'ok'}],
                fx: [{status: 'ok'}],
            }),
        ]);

        expect(row('history_sync')).toHaveTextContent('?, ?');
    });
});

describe('the row header', () => {
    it('names a job it knows', async () => {
        await mountWith([priceRun(), historyRun()]);

        expect(row('current_price')).toHaveTextContent('common.currentPrice');
        expect(row('history_sync')).toHaveTextContent('settings.global.scheduler.log.historySync');
    });

    it('falls back to the raw name for a job it does not know', async () => {
        await mountWith([priceRun({job: 'cleanup_orphans'})]);

        expect(row('cleanup_orphans')).toHaveTextContent('cleanup_orphans');
    });

    it('prints a timestamp it cannot parse rather than "Invalid Date"', async () => {
        await mountWith([priceRun({ts: 'not-a-timestamp'})]);

        expect(row('current_price')).toHaveTextContent('not-a-timestamp');
    });

    it('carries the status it was given', async () => {
        await mountWith([priceRun({status: 'partial'})]);

        expect(row('current_price')).toHaveAttribute('data-status', 'partial');
    });
});

/**
 * M-18 CP2 — when a run happened, in the interface language.
 *
 * Every figure follows the UI language (the developer's rule of 2026-10-12). The row header writes the
 * run's time through `new Intl.DateTimeFormat(undefined, {month: 'short', day: 'numeric', hour: '2-digit',
 * minute: '2-digit'})` — the browser's locale — so an Italian UI on an English browser read
 * `Jan 15, 09:00 AM`. The cure: the interface locale, `uiLocale()`; a timestamp that cannot be parsed is
 * still printed as it came (the row header's own test).
 *
 * The time publishes no handle: it is the one leaf of the row whose text carries a wall-clock time
 * (`hh:mm`) — the duration reads `1.3s`, the summary `2/2 ✓`. Expectations are Intl's output in this
 * runtime with the component's options, never typed; jsdom's browser is en-US, so the English UI keeps
 * en-US. The language is switched as LanguageSelector does (`currentLanguage.set`) and put back after each
 * test; this file's translator stays the identity, which no figure reads. SchedulerLogModal is a runes
 * component: the in-place test proves the time is read reactively, in both shapes of a row header — the
 * clickable one of a run with a detail and the static one of a run without.
 */
describe('the time of a run, in the interface language (M-18 CP2)', () => {
    const TS = '2026-01-15T08:00:00Z';
    const STAMP: Intl.DateTimeFormatOptions = {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'};
    /** The run's time as Intl writes it in `locale`. */
    const stampIn = (locale: string): string => new Intl.DateTimeFormat(locale, STAMP).format(new Date(TS));

    /** The one leaf of a run's row whose text carries a wall-clock time. */
    function shownStamp(job: string): string {
        const stamps = [...row(job).querySelectorAll('*')]
            .filter((element) => element.children.length === 0)
            .map((element) => (element.textContent ?? '').trim())
            .filter((text) => /\d{1,2}:\d{2}/.test(text));
        if (stamps.length !== 1) throw new Error(`expected one time in the ${job} row, found ${JSON.stringify(stamps)}`);
        return stamps[0];
    }

    /** Change the UI language as LanguageSelector does, then flush. */
    async function switchLanguage(lang: 'en' | 'it'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        flushSync();
        await tick();
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await switchLanguage('en');
    });

    it('English UI on an en-US browser (control): the time as today', async () => {
        await mountWith([priceRun({ts: TS})]);

        expect(shownStamp('current_price')).toBe(stampIn('en-US'));
    });

    it('mounted with the UI in Italian: the Italian time', async () => {
        await switchLanguage('it');
        const expected = stampIn('it');
        expect(expected, 'control: the Italian time differs from the English one').not.toBe(stampIn('en-US'));

        await mountWith([priceRun({ts: TS})]);

        expect(shownStamp('current_price')).toBe(expected);
    });

    it('follows an in-place switch of the UI language, en → it → en, in both shapes of a row header', async () => {
        await mountWith([priceRun({ts: TS}), historyRun({ts: TS, assets: [], fx: []})]);
        expect(row('current_price'), 'premise: the price run has a detail, so a clickable header').toHaveAttribute('data-has-detail', 'true');
        expect(row('history_sync'), 'premise: the history run has none, so a static header').toHaveAttribute('data-has-detail', 'false');
        const read = () => ({clickable: shownStamp('current_price'), static: shownStamp('history_sync')});
        const both = (locale: string) => ({clickable: stampIn(locale), static: stampIn(locale)});
        expect(read(), 'en, mount — today’s text').toEqual(both('en-US'));

        await switchLanguage('it');
        expect(read(), 'en → it in place — the Italian time').toEqual(both('it'));

        await switchLanguage('en');
        expect(read(), 'it → en in place — today’s text again').toEqual(both('en-US'));
    });
});

describe('opening a row', () => {
    it('is not clickable when there is nothing to show', async () => {
        await mountWith([priceRun({items: []})]);

        const r = row('current_price');
        expect(r).toHaveAttribute('data-has-detail', 'false');
        expect(within(r).queryByRole('button')).toBeNull();
    });

    it('treats empty assets and FX lists as nothing to show either', async () => {
        await mountWith([historyRun({assets: [], fx: []})]);

        expect(row('history_sync')).toHaveAttribute('data-has-detail', 'false');
    });

    it('opens and closes on click', async () => {
        await mountWith([priceRun()]);
        const r = row('current_price');
        expect(screen.queryByTestId('scheduler-log-entry-detail')).toBeNull();

        await fireEvent.click(within(r).getByRole('button'));
        expect(row('current_price')).toHaveAttribute('data-expanded', 'true');
        expect(screen.getByTestId('scheduler-log-entry-detail')).toBeInTheDocument();

        await fireEvent.click(within(row('current_price')).getByRole('button'));
        expect(row('current_price')).toHaveAttribute('data-expanded', 'false');
        expect(screen.queryByTestId('scheduler-log-entry-detail')).toBeNull();
    });

    it('opens one row without opening its neighbour', async () => {
        await mountWith([priceRun(), historyRun()]);

        await fireEvent.click(within(row('current_price')).getByRole('button'));

        expect(row('current_price')).toHaveAttribute('data-expanded', 'true');
        expect(row('history_sync')).toHaveAttribute('data-expanded', 'false');
    });

    it('keeps two rows apart even when they share a timestamp', async () => {
        // The key is `ts_job`, so two jobs logged in the same second are still
        // two rows with two independent expansion states.
        await mountWith([priceRun({ts: '2026-01-15T08:00:00Z'}), historyRun({ts: '2026-01-15T08:00:00Z'})]);

        await fireEvent.click(within(row('history_sync')).getByRole('button'));

        expect(row('history_sync')).toHaveAttribute('data-expanded', 'true');
        expect(row('current_price')).toHaveAttribute('data-expanded', 'false');
    });
});

describe('the price-run detail table', () => {
    async function openPriceDetail(items: Entry[]): Promise<HTMLElement> {
        await mountWith([priceRun({items})]);
        await fireEvent.click(within(row('current_price')).getByRole('button'));
        return screen.getByTestId('scheduler-log-entry-detail');
    }

    it('lists every item by name', async () => {
        const detail = await openPriceDetail([
            {asset_id: 1, name: 'Apple', ok: true},
            {asset_id: 2, name: 'Nvidia', ok: false, error: 'quote unavailable'},
        ]);

        expect(detail).toHaveTextContent('Apple');
        expect(detail).toHaveTextContent('Nvidia');
    });

    it('shows the reason a fetch failed', async () => {
        const detail = await openPriceDetail([{asset_id: 2, name: 'Nvidia', ok: false, error: 'quote unavailable'}]);

        expect(detail).toHaveTextContent('— quote unavailable');
    });

    it('does not tick a failed item just because it has no error message', async () => {
        const detail = await openPriceDetail([{asset_id: 2, name: 'Nvidia', ok: false}]);

        expect(detail).toHaveTextContent('—');
        expect(detail).not.toHaveTextContent('✓');
    });

    it('copies the message on a double click', async () => {
        const detail = await openPriceDetail([{asset_id: 2, name: 'Nvidia', ok: false, error: 'quote unavailable'}]);

        await fireEvent.dblClick(within(detail).getByText(/quote unavailable/));

        expect(copied).toHaveBeenCalledOnce();
        expect(copied.mock.calls[0][0]).toBe('quote unavailable');
    });

    it('copies after a long press on a touch screen', async () => {
        const detail = await openPriceDetail([{asset_id: 2, name: 'Nvidia', ok: false, error: 'quote unavailable'}]);
        const cell = within(detail).getByText(/quote unavailable/);
        vi.useFakeTimers();

        await fireEvent.touchStart(cell);
        await vi.advanceTimersByTimeAsync(499);
        expect(copied).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(2);
        expect(copied).toHaveBeenCalledOnce();
    });

    it('cancels the long press when the finger leaves early', async () => {
        const detail = await openPriceDetail([{asset_id: 2, name: 'Nvidia', ok: false, error: 'quote unavailable'}]);
        const cell = within(detail).getByText(/quote unavailable/);
        vi.useFakeTimers();

        await fireEvent.touchStart(cell);
        await vi.advanceTimersByTimeAsync(200);
        await fireEvent.touchEnd(cell);
        await vi.advanceTimersByTimeAsync(1000);

        expect(copied).not.toHaveBeenCalled();
    });
});

describe('the history-run detail table', () => {
    async function openHistoryDetail(over: Entry): Promise<HTMLElement> {
        await mountWith([historyRun(over)]);
        await fireEvent.click(within(row('history_sync')).getByRole('button'));
        return screen.getByTestId('scheduler-log-entry-detail');
    }

    it('shows how many prices and how many events changed', async () => {
        const detail = await openHistoryDetail({
            assets: [{asset_id: 1, name: 'Apple', status: 'ok', prices_changed: 4, events_changed: 2}],
            fx: [],
        });

        expect(detail).toHaveTextContent('+4');
        expect(detail).toHaveTextContent('+2');
    });

    it('falls back to the raw point count when neither prices nor events moved', async () => {
        const detail = await openHistoryDetail({
            assets: [{asset_id: 1, name: 'Apple', status: 'ok', prices_changed: 0, events_changed: 0, points_changed: 7}],
            fx: [],
        });

        expect(detail).toHaveTextContent('+7Δ');
    });

    it('says nothing about deltas when the point count is absent too', async () => {
        const detail = await openHistoryDetail({
            assets: [{asset_id: 1, name: 'Apple', status: 'ok'}],
            fx: [],
        });

        expect(detail).not.toHaveTextContent('Δ');
        expect(detail).toHaveTextContent('Apple');
    });

    it('shows no delta at all for an asset that failed', async () => {
        const detail = await openHistoryDetail({
            assets: [{asset_id: 1, name: 'Apple', status: 'error', points_changed: 9, errors: ['rate limited']}],
            fx: [],
        });

        expect(detail).not.toHaveTextContent('+9');
        expect(detail).toHaveTextContent('— rate limited');
    });

    it('shows only the first of several errors on the row', async () => {
        const detail = await openHistoryDetail({
            assets: [{asset_id: 1, name: 'Apple', status: 'error', errors: ['rate limited', 'and then it gave up']}],
            fx: [],
        });

        expect(detail).toHaveTextContent('— rate limited');
        expect(detail).not.toHaveTextContent('and then it gave up');
    });

    it('copies every error, not just the visible one', async () => {
        const detail = await openHistoryDetail({
            assets: [{asset_id: 1, name: 'Apple', status: 'error', errors: ['rate limited', 'and then it gave up']}],
            fx: [],
        });

        await fireEvent.dblClick(within(detail).getByText(/rate limited/));

        expect(copied.mock.calls[0][0]).toBe('rate limited; and then it gave up');
    });

    it('shows the provider that served the asset, with and without an icon', async () => {
        const detail = await openHistoryDetail({
            assets: [
                {asset_id: 1, name: 'Apple', status: 'ok', provider: 'yahoo'},
                {asset_id: 2, name: 'Bond', status: 'ok', provider: 'borsa'},
            ],
            fx: [],
        });

        // The asset table's icons are decorative (`alt=""`), so they are
        // addressed by `src` — an attribute of the product, not a style.
        expect(detail.querySelector('img[src="https://icons.test/yahoo.png"]')).not.toBeNull();
        expect(detail).toHaveTextContent('borsa');
        expect(detail.querySelectorAll('img')).toHaveLength(1);
    });

    it('shows the asset icon when the log carried one', async () => {
        const detail = await openHistoryDetail({
            assets: [{asset_id: 1, name: 'Apple', status: 'ok', icon_url: 'https://icons.test/apple.png'}],
            fx: [],
        });

        expect(detail.querySelector('img[src="https://icons.test/apple.png"]')).not.toBeNull();
    });

    it('shows a whole FX provider chain', async () => {
        const detail = await openHistoryDetail({
            assets: [],
            fx: [{pair: 'EUR/USD', base: 'EUR', quote: 'USD', status: 'ok', provider: 'ecb>yahoo', points_changed: 5}],
        });

        expect(within(detail).getByAltText('ecb')).toHaveAttribute('src', 'https://icons.test/ecb.png');
        expect(detail).toHaveTextContent('yahoo');
        expect(detail).toHaveTextContent('+5');
    });

    it('copes with an FX row that names no provider', async () => {
        const detail = await openHistoryDetail({
            assets: [],
            fx: [{pair: 'EUR/GBP', base: 'EUR', quote: 'GBP', status: 'ok'}],
        });

        expect(detail).toHaveTextContent('EUR');
        expect(within(detail).queryByAltText('ecb')).toBeNull();
    });

    it('flags the currencies it knows and skips the ones it does not', async () => {
        const detail = await openHistoryDetail({
            assets: [],
            fx: [{pair: 'EUR/USD', base: 'EUR', quote: 'USD', status: 'ok'}],
        });

        expect(detail).toHaveTextContent('🇺🇸');
    });

    it('shows the failure instead of a delta for a broken pair', async () => {
        const detail = await openHistoryDetail({
            assets: [],
            fx: [{pair: 'EUR/JPY', status: 'error', points_changed: 3, errors: ['no route']}],
        });

        expect(detail).toHaveTextContent('— no route');
        expect(detail).not.toHaveTextContent('+3');
    });

    it('copies an FX failure the same way as an asset one', async () => {
        const detail = await openHistoryDetail({
            assets: [],
            fx: [{pair: 'EUR/JPY', status: 'error', errors: ['no route', 'and no fallback']}],
        });

        await fireEvent.dblClick(within(detail).getByText(/no route/));

        expect(copied.mock.calls[0][0]).toBe('no route; and no fallback');
    });

    it('copies an FX failure on a long press too', async () => {
        const detail = await openHistoryDetail({
            assets: [],
            fx: [{pair: 'EUR/JPY', status: 'error', errors: ['no route']}],
        });
        const cell = within(detail).getByText(/no route/);
        vi.useFakeTimers();

        await fireEvent.touchStart(cell);
        await vi.advanceTimersByTimeAsync(501);

        expect(copied).toHaveBeenCalledOnce();
        expect(copied.mock.calls[0][0]).toBe('no route');
    });

    it('shows both tables when a run touched assets and FX', async () => {
        const detail = await openHistoryDetail({});

        expect(within(detail).getAllByRole('table')).toHaveLength(2);
    });

    it('shows one table when a run touched only one of them', async () => {
        const detail = await openHistoryDetail({fx: []});

        expect(within(detail).getAllByRole('table')).toHaveLength(1);
    });
});

describe('dismissing', () => {
    it('closes on the footer button', async () => {
        await mountWith([priceRun()]);

        await fireEvent.click(screen.getByTestId('scheduler-log-close'));

        expect(screen.queryByTestId('scheduler-log-modal')).toBeNull();
    });

    it('closes on the header cross', async () => {
        const {container} = await mountWith([priceRun()]);
        const header = container.querySelector('[data-testid="scheduler-log-modal"] .border-b') as HTMLElement;

        await fireEvent.click(within(header).getAllByRole('button').at(-1) as HTMLElement);

        expect(screen.queryByTestId('scheduler-log-modal')).toBeNull();
    });

    it('renders nothing while closed', async () => {
        await mountWith([priceRun()], false);

        expect(screen.queryByTestId('scheduler-log-modal')).toBeNull();
    });
});

/**
 * Lot Z7c-2 — what lot Z7b added to the log: the items a provider's pause deferred, and when they are retried.
 *
 * Z7b defers an item a provider refused with HTTP 429: the item is neither ok nor failed. Its entry marks it
 * `deferred: true` (with `retry_after`, in seconds, when known), counts it apart in the summary (`deferred`, or
 * `assets_deferred` and `fx_deferred`) and carries the `retry_at` of the retry. The fixtures below have the shape the log
 * route answers once it passes these keys through (backend SAPI-012..014): every item carries `deferred` and
 * `retry_after`, every summary its deferred counters, every entry its `retry_at` — at their defaults when nothing was
 * deferred. An entry with none of these keys (an older backend) renders exactly as before.
 *
 * The handles are the product's: the `<tr>` of each item of the three detail tables is `scheduler-log-item`, with
 * `data-deferred="true|false"`; a deferred item's status cell holds `scheduler-log-item-deferred` instead of the ok or
 * failed mark — those two are bare icons without a handle, so they are asserted only through the deferred mark, present
 * or absent; the header holds `scheduler-log-retry-at` when the entry has a `retry_at`; the summary is
 * `scheduler-log-summary`, read for its `⏸` and its count — numbers and punctuation the component assembles, like
 * `2/3 ✓`, never translated. An item's row is told apart by the item's name or pair: data, not a translation.
 */
const RETRY_AT = '2026-01-15T08:02:00+00:00';

/** An item as the log route answers it once it passes lot Z7b's keys through: not deferred unless the fields say so. */
const answered = (fields: Entry): Entry => ({deferred: false, retry_after: null, ...fields});

/** A price run that deferred two items — Nvidia paused for 120 s, Meta with no Retry-After —, one ok and one failed beside them. */
function deferredPriceRun(over: Entry = {}): Entry {
    return priceRun({
        status: 'partial',
        summary: {ok: 1, err: 1, deferred: 2},
        retry_at: RETRY_AT,
        items: [
            answered({asset_id: 1, name: 'Apple', ok: true}),
            answered({asset_id: 2, name: 'Nvidia', ok: false, deferred: true, retry_after: 120, error: 'too many requests'}),
            answered({asset_id: 3, name: 'Meta', ok: false, deferred: true, error: 'too many requests'}),
            answered({asset_id: 4, name: 'Tesla', ok: false, error: 'quote unavailable'}),
        ],
        ...over,
    });
}

/** A history run that deferred two assets — Bond failed, Amazon partly saved (status ok): Z7b defers whatever the status — and one pair. */
function deferredHistoryRun(over: Entry = {}): Entry {
    return historyRun({
        status: 'partial',
        summary: {assets_ok: 1, assets_err: 0, assets_deferred: 2, fx_ok: 1, fx_err: 0, fx_deferred: 1},
        retry_at: RETRY_AT,
        assets: [
            answered({asset_id: 1, name: 'Microsoft', status: 'ok', provider: 'yahoo', prices_changed: 3, events_changed: 0}),
            answered({asset_id: 2, name: 'Bond', status: 'failed', deferred: true, retry_after: 300, errors: ['too many requests'], prices_changed: 0, events_changed: 0}),
            answered({asset_id: 3, name: 'Amazon', status: 'ok', deferred: true, provider: 'yahoo', errors: ['too many requests'], prices_changed: 2, events_changed: 0}),
        ],
        fx: [answered({pair: 'EUR/USD', base: 'EUR', quote: 'USD', status: 'ok', provider: 'ecb', points_changed: 4}), answered({pair: 'GBP/USD', base: 'GBP', quote: 'USD', status: 'failed', deferred: true, retry_after: 45, errors: ['too many requests'], points_changed: 0})],
        ...over,
    });
}

/** The single row of a job in a status, addressed by the attributes the product publishes. */
function rowWith(job: string, status: string): HTMLElement {
    const found = rows().filter((r) => r.getAttribute('data-job') === job && r.getAttribute('data-status') === status);
    expect(found).toHaveLength(1);
    return found[0];
}

/** Opens a run's detail through its header, and returns it. */
async function openDetail(job: string): Promise<HTMLElement> {
    await fireEvent.click(within(row(job)).getByRole('button'));
    return within(row(job)).getByTestId('scheduler-log-entry-detail');
}

/** Every item row of an opened detail: the `<tr>` of each price item, asset and FX pair. */
function itemRows(detail: HTMLElement): HTMLElement[] {
    return within(detail).queryAllByTestId('scheduler-log-item');
}

/** The one item row naming `name`. */
function itemRow(detail: HTMLElement, name: string): HTMLElement {
    const found = itemRows(detail).filter((r) => (r.textContent ?? '').includes(name));
    expect(found, `one item row names ${name}`).toHaveLength(1);
    return found[0];
}

/** The deferred marks inside `element`. */
function deferredMarks(element: HTMLElement): HTMLElement[] {
    return within(element).queryAllByTestId('scheduler-log-item-deferred');
}

/** The summary of a run's row, its whitespace collapsed. */
function summaryOf(entryRow: HTMLElement): string {
    return (within(entryRow).getByTestId('scheduler-log-summary').textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** Whether `text` holds `count` as a number of its own, not inside a larger one. */
function holdsCount(text: string, count: number): boolean {
    return new RegExp(`(^|\\D)${count}(\\D|$)`).test(text);
}

describe('Z7c-2 — a deferred price item', () => {
    it('gives every row of the price table its handle, and says which items were deferred', async () => {
        await mountWith([deferredPriceRun()]);

        const detail = await openDetail('current_price');

        expect(itemRows(detail), 'one row per item').toHaveLength(4);
        expect(Object.fromEntries(['Apple', 'Nvidia', 'Meta', 'Tesla'].map((name) => [name, itemRow(detail, name).getAttribute('data-deferred')]))).toEqual({Apple: 'false', Nvidia: 'true', Meta: 'true', Tesla: 'false'});
    });

    it('marks the status of a deferred item as deferred, with or without a retry_after, and of no other item', async () => {
        await mountWith([deferredPriceRun()]);

        const detail = await openDetail('current_price');

        expect(deferredMarks(itemRow(detail, 'Nvidia')), 'deferred, retry_after 120').toHaveLength(1);
        expect(deferredMarks(itemRow(detail, 'Meta')), 'deferred, no retry_after').toHaveLength(1);
        expect(deferredMarks(itemRow(detail, 'Apple')), 'an ok item keeps its own mark').toHaveLength(0);
        expect(deferredMarks(itemRow(detail, 'Tesla')), 'a failed item keeps its own mark').toHaveLength(0);
        expect(deferredMarks(detail), 'two deferred items, two marks').toHaveLength(2);
    });
});

describe('Z7c-2 — deferred history items', () => {
    it('gives every asset and FX row its handle, and says which were deferred', async () => {
        await mountWith([deferredHistoryRun()]);

        const detail = await openDetail('history_sync');

        expect(itemRows(detail), 'three assets and two pairs').toHaveLength(5);
        expect(Object.fromEntries(['Microsoft', 'Bond', 'Amazon', 'EUR/USD', 'GBP/USD'].map((name) => [name, itemRow(detail, name).getAttribute('data-deferred')]))).toEqual({
            Microsoft: 'false',
            Bond: 'true',
            Amazon: 'true',
            'EUR/USD': 'false',
            'GBP/USD': 'true',
        });
    });

    it('marks the status of a deferred asset or pair as deferred, whatever its status, and of no other', async () => {
        await mountWith([deferredHistoryRun()]);

        const detail = await openDetail('history_sync');

        for (const name of ['Bond', 'Amazon', 'GBP/USD']) expect(deferredMarks(itemRow(detail, name)), `${name} was deferred`).toHaveLength(1);
        for (const name of ['Microsoft', 'EUR/USD']) expect(deferredMarks(itemRow(detail, name)), `${name} was not`).toHaveLength(0);
    });
});

describe('Z7c-2 — when the deferred items are retried', () => {
    const shapes: [string, Entry, string][] = [
        ['a price run (clickable header)', deferredPriceRun(), 'true'],
        ['a history run (clickable header)', deferredHistoryRun(), 'true'],
        ['a run without detail (static header)', priceRun({retry_at: RETRY_AT, items: []}), 'false'],
    ];

    it.each(shapes)('shows the retry time in the header of %s, the detail closed', async (_shape, entry, hasDetail) => {
        await mountWith([entry]);

        const r = row(entry.job as string);
        expect(r, 'premise: the shape of the header').toHaveAttribute('data-has-detail', hasDetail);
        expect(within(r).queryByTestId('scheduler-log-entry-detail'), 'premise: only the header is drawn').toBeNull();
        expect(within(r).getAllByTestId('scheduler-log-retry-at')).toHaveLength(1);
    });

    it('shows none in a run without a retry_at — null or absent —, beside a run that has one', async () => {
        await mountWith([deferredPriceRun(), priceRun({ts: '2026-01-15T07:00:00Z', retry_at: null}), historyRun()]);

        expect(within(rowWith('current_price', 'partial')).getAllByTestId('scheduler-log-retry-at'), 'control: the run with a retry_at shows it').toHaveLength(1);
        expect(within(rowWith('current_price', 'ok')).queryByTestId('scheduler-log-retry-at'), 'retry_at null').toBeNull();
        expect(within(row('history_sync')).queryByTestId('scheduler-log-retry-at'), 'no retry_at key').toBeNull();
        expect(screen.getAllByTestId('scheduler-log-retry-at'), 'one retry time on screen, the control’s').toHaveLength(1);
    });
});

describe('Z7c-2 — the summary counts the deferred items apart', () => {
    it('a price run: ⏸ and how many were deferred', async () => {
        // ok 3, err 2, deferred 4: the other numbers the summary could print — 3, 2, 5, and with the deferred 6, 7, 9 — are never a 4.
        const items = [
            ...['Apple', 'Nvidia', 'Intel'].map((name, i) => answered({asset_id: i + 1, name, ok: true})),
            ...['Tesla', 'Oracle'].map((name, i) => answered({asset_id: i + 10, name, ok: false, error: 'quote unavailable'})),
            ...['Meta', 'Amazon', 'Adobe', 'Cisco'].map((name, i) => answered({asset_id: i + 20, name, ok: false, deferred: true, retry_after: 120, error: 'too many requests'})),
        ];
        await mountWith([priceRun({status: 'partial', summary: {ok: 3, err: 2, deferred: 4}, retry_at: RETRY_AT, items})]);

        const text = summaryOf(row('current_price'));

        expect(text).toContain('⏸');
        expect(holdsCount(text, 4), `the deferred count in «${text}»`).toBe(true);
    });

    it('a history run that deferred assets: ⏸ and how many', async () => {
        // assets 1 ok, 1 failed, 5 deferred; FX 2 ok: every sum of the other counts is at most 4, so a 5 is the deferred count.
        const assets = [
            answered({asset_id: 1, name: 'Microsoft', status: 'ok'}),
            answered({asset_id: 2, name: 'Tesla', status: 'failed', errors: ['no data']}),
            ...['Bond', 'Amazon', 'Cisco', 'Adobe', 'Intel'].map((name, i) => answered({asset_id: i + 10, name, status: 'failed', deferred: true, errors: ['too many requests']})),
        ];
        const fx = ['EUR/USD', 'EUR/GBP'].map((pair) => answered({pair, status: 'ok'}));
        await mountWith([historyRun({status: 'partial', summary: {assets_ok: 1, assets_err: 1, assets_deferred: 5, fx_ok: 2, fx_err: 0, fx_deferred: 0}, retry_at: RETRY_AT, assets, fx})]);

        const text = summaryOf(row('history_sync'));

        expect(text).toContain('⏸');
        expect(holdsCount(text, 5), `the deferred count in «${text}»`).toBe(true);
    });

    it('a history run that deferred FX pairs: ⏸ and how many', async () => {
        // assets 2 ok; FX 1 ok, 1 failed, 5 deferred: every sum of the other counts is at most 4, so a 5 is the deferred count.
        const assets = ['Microsoft', 'Apple'].map((name, i) => answered({asset_id: i + 1, name, status: 'ok'}));
        const fx = [
            answered({pair: 'EUR/USD', status: 'ok'}),
            answered({pair: 'EUR/JPY', status: 'failed', errors: ['no route']}),
            ...['GBP/USD', 'CHF/USD', 'SEK/USD', 'NOK/USD', 'DKK/USD'].map((pair) => answered({pair, status: 'failed', deferred: true, retry_after: 45, errors: ['too many requests']})),
        ];
        await mountWith([historyRun({status: 'partial', summary: {assets_ok: 2, assets_err: 0, assets_deferred: 0, fx_ok: 1, fx_err: 1, fx_deferred: 5}, retry_at: RETRY_AT, assets, fx})]);

        const text = summaryOf(row('history_sync'));

        expect(text).toContain('⏸');
        expect(holdsCount(text, 5), `the deferred count in «${text}»`).toBe(true);
    });
});

describe('Z7c-2 — a run with nothing deferred renders as before', () => {
    const priceItems = [
        {asset_id: 1, name: 'Apple', ok: true},
        {asset_id: 2, name: 'Nvidia', ok: true},
        {asset_id: 3, name: 'Tesla', ok: false, error: 'quote unavailable'},
    ];
    const assets = [
        {asset_id: 1, name: 'Microsoft', status: 'ok', provider: 'yahoo', prices_changed: 3},
        {asset_id: 2, name: 'Bond', status: 'error', errors: ['no data']},
    ];
    const fx = [
        {pair: 'EUR/USD', base: 'EUR', quote: 'USD', status: 'ok', provider: 'ecb', points_changed: 5},
        {pair: 'EUR/GBP', base: 'EUR', quote: 'GBP', status: 'ok', provider: 'ecb', points_changed: 2},
    ];

    const priceRuns: [string, Entry][] = [
        ['written before Z7b, without its keys', priceRun({status: 'partial', summary: {ok: 2, err: 1}, items: priceItems})],
        ['answered with its keys at their defaults', priceRun({status: 'partial', summary: {ok: 2, err: 1, deferred: 0}, retry_at: null, items: priceItems.map(answered)})],
    ];
    const historyRuns: [string, Entry][] = [
        ['written before Z7b, without its keys', historyRun({status: 'partial', summary: {assets_ok: 1, assets_err: 1, fx_ok: 2, fx_err: 0}, assets, fx})],
        ['answered with its keys at their defaults', historyRun({status: 'partial', summary: {assets_ok: 1, assets_err: 1, assets_deferred: 0, fx_ok: 2, fx_err: 0, fx_deferred: 0}, retry_at: null, assets: assets.map(answered), fx: fx.map(answered)})],
    ];

    it.each(priceRuns)('a price run %s: the summary of before, no retry time, no deferred mark', async (_name, entry) => {
        await mountWith([entry]);

        expect(summaryOf(row('current_price'))).toBe('2/3 ✓ · 1 ✗');
        expect(within(row('current_price')).queryByTestId('scheduler-log-retry-at')).toBeNull();
        const detail = await openDetail('current_price');
        expect(itemRows(detail).map((r) => r.getAttribute('data-deferred'))).toEqual(['false', 'false', 'false']);
        expect(deferredMarks(detail)).toHaveLength(0);
    });

    it.each(historyRuns)('a history run %s: the summary of before, no retry time, no deferred mark', async (_name, entry) => {
        await mountWith([entry]);

        expect(summaryOf(row('history_sync'))).toBe('1/2 assets · 2/2 FX · 1 ✗');
        expect(within(row('history_sync')).queryByTestId('scheduler-log-retry-at')).toBeNull();
        const detail = await openDetail('history_sync');
        expect(itemRows(detail).map((r) => r.getAttribute('data-deferred'))).toEqual(['false', 'false', 'false', 'false']);
        expect(deferredMarks(detail)).toHaveLength(0);
    });

    it('a run without detail (static header): its summary through the same handle, as before', async () => {
        await mountWith([priceRun({summary: {ok: 0, err: 0}, items: []})]);

        expect(row('current_price'), 'premise: a static header').toHaveAttribute('data-has-detail', 'false');
        expect(summaryOf(row('current_price'))).toBe('0/0 ✓');
        expect(within(row('current_price')).queryByTestId('scheduler-log-retry-at')).toBeNull();
    });
});
