// @vitest-environment jsdom
/**
 * ProfileHistoryModal — «Storia del dato» of one voice (plan 68, E6b; the mock's shots 13 and 14): the big chart of the
 * voice from its first day (numbers only), and under it the same table as «Ultime variazioni» with every row of that
 * voice, without the «Dato» column, with the same «Dimentica».
 *
 * Pinned with the profile memory mocked and ECharts stubbed (jsdom has no canvas):
 *   - closed it reads nothing; open, it reads the voice's steps from its first day and the voice's changes;
 *   - a number voice has the chart, with a point per step; a text voice has none;
 *   - «Dimentica» sends the `as_of` of the changes read, tells the page (`onchanged`) and reads again.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const readAssetProfile = vi.fn();
const forgetProfileRows = vi.fn();
vi.mock('./profileStore', () => ({
    readAssetProfile: (...args: unknown[]) => readAssetProfile(...args),
    forgetProfileRows: (...args: unknown[]) => forgetProfileRows(...args),
    loadProfileCatalogue: vi.fn(async () => CATALOGUE),
    profileVoice: (key: string) => CATALOGUE.find((voice) => voice.key === key),
}));
vi.mock('./profileSources', async (original) => ({...((await original()) as object), loadProfileSources: vi.fn(async () => ({borsa_italiana: {name: 'Borsa Italiana', icon: null}}))}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));
vi.mock('$lib/stores/reference/countryStore', () => ({ensureCountriesLoaded: vi.fn(async () => undefined), getCountryInfo: (iso3: string) => ({name: iso3})}));
vi.mock('echarts', () => ({init: () => ({setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn(), on: vi.fn()})}));

const CATALOGUE = [
    {key: 'yield_gross', shape: 'percentage', groups: ['bond'], volatile: true},
    {key: 'description', shape: 'text', groups: ['identity'], volatile: false},
    {key: 'geography', shape: 'map', groups: ['classification'], volatile: false, map_keys: 'country'},
];

import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import ProfileHistoryModal from './ProfileHistoryModal.svelte';

function change(id: number, key: string) {
    return {
        id,
        key,
        value: '0.0361',
        previous: '0.034',
        has_previous: true,
        source: 'borsa_italiana',
        user_id: null,
        user_name: null,
        user_avatar_url: null,
        read_on: '2026-11-08',
        source_date: null,
        created_at: '2026-11-08T10:00:00Z',
        previous_source: 'user',
        previous_user_id: 3,
        previous_user_name: 'anna',
        previous_read_on: '2026-11-01',
        previous_source_date: null,
    };
}

const STEPS = [
    {date: '2026-10-11', through: '2026-10-31', value: '0.0352', source: 'borsa_italiana', update_id: 1},
    {date: '2026-11-01', through: '2026-11-07', value: '0.034', source: 'user', update_id: 2},
    {date: '2026-11-08', through: '2026-11-19', value: '0.0361', source: 'borsa_italiana', update_id: 3},
];

/** The two reads of the window: the voice's steps (keys: [key]) and its changes (keys: []). */
function answer(key: string, ids: number[], asOf = 'AS-OF-1') {
    return (_id: number, _range: unknown, options: {keys?: string[]}) =>
        Promise.resolve(
            options.keys && options.keys.length
                ? {kind: 'found', asOf, voices: {[key]: key === 'yield_gross' ? STEPS : [{date: '2026-10-01', through: '2026-11-19', value: 'A fund', source: 'user', update_id: 9}]}, changes: null}
                : {kind: 'found', asOf, voices: {}, changes: {items: ids.map((id) => change(id, key)), total: ids.length, page: 0, page_size: 20}},
        );
}

function mount(voiceKey: string, props: Record<string, unknown> = {}) {
    const onchanged = vi.fn();
    const onclose = vi.fn();
    render(ProfileHistoryModal, {props: {open: true, assetId: 7, assetName: 'BTP Valore', voiceKey, onchanged, onclose, ...props}});
    return {onchanged, onclose};
}

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    readAssetProfile.mockReset();
    forgetProfileRows.mockReset();
});

afterEach(() => cleanup());

describe('ProfileHistoryModal', () => {
    it('closed, it reads nothing', () => {
        readAssetProfile.mockImplementation(answer('yield_gross', [3]));
        mount('yield_gross', {open: false});
        expect(readAssetProfile).not.toHaveBeenCalled();
    });

    it('reads the voice from its first day and its changes; a number voice has the chart, the table has no «Dato» column', async () => {
        readAssetProfile.mockImplementation(answer('yield_gross', [3, 2, 1]));
        mount('yield_gross');
        const modal = await screen.findByTestId('profile-history');
        await waitFor(() => expect(modal).toHaveAttribute('data-status', 'ready'));
        expect(modal).toHaveAttribute('data-voice', 'yield_gross');

        const calls = readAssetProfile.mock.calls.map((call) => ({range: call[1] as {start: string}, options: call[2] as {keys: string[]; changes?: {key: string; page: number}}}));
        expect(calls.find((call) => call.options.keys.length === 1)).toMatchObject({range: {start: 'min'}, options: {keys: ['yield_gross']}});
        expect(calls.find((call) => call.options.keys.length === 0)?.options.changes).toEqual({key: 'yield_gross', page: 0});

        const chart = screen.getByTestId('profile-history-chart');
        expect(chart).toHaveAttribute('data-point-count', '3');
        expect(chart).toHaveAttribute('data-hand-count', '1');
        // E12: the chart says when it has drawn (chartReady.ts), like every chart of the app: the gallery waits for it
        await waitFor(() => expect(chart).toHaveAttribute('data-chart-ready', 'false'));
        expect(screen.getByTestId('profile-change-what-3')).toBeInTheDocument();
        expect(screen.queryByTestId('dt-header-voice')).toBeNull();
    });

    it.each(['description', 'geography'])('draws no chart for %s, a voice that is not a number: only its table (E6b2)', async (key) => {
        readAssetProfile.mockImplementation(answer(key, [9]));
        mount(key);
        await waitFor(() => expect(screen.getByTestId('profile-history')).toHaveAttribute('data-status', 'ready'));
        expect(screen.queryByTestId('profile-history-chart')).toBeNull();
        expect(screen.getByTestId('profile-change-what-9')).toBeInTheDocument();
    });

    it('forgets with the as_of of the changes read, tells the page and reads again', async () => {
        readAssetProfile.mockImplementation(answer('yield_gross', [3, 2, 1], 'AS-OF-CHANGES'));
        forgetProfileRows.mockResolvedValue({kind: 'forgotten', deleted: 1});
        const {onchanged} = mount('yield_gross');
        await waitFor(() => expect(screen.getByTestId('profile-history')).toHaveAttribute('data-status', 'ready'));
        const before = readAssetProfile.mock.calls.length;

        const row = screen.getByTestId('profile-changes-table').querySelector<HTMLElement>('tr[data-row-id="3"]');
        if (!row) throw new Error('no row 3');
        await fireEvent.contextMenu(row, {clientX: 10, clientY: 10});
        await fireEvent.click(await screen.findByTestId('profile-change-forget-3'));
        await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));

        await waitFor(() => expect(forgetProfileRows).toHaveBeenCalledWith(7, [3], 'AS-OF-CHANGES'));
        await waitFor(() => expect(onchanged).toHaveBeenCalledTimes(1));
        await waitFor(() => expect(readAssetProfile.mock.calls.length).toBeGreaterThan(before));
    });

    it('closes from its button', async () => {
        readAssetProfile.mockImplementation(answer('yield_gross', [3]));
        const {onclose} = mount('yield_gross');
        await fireEvent.click(await screen.findByTestId('profile-history-close'));
        expect(onclose).toHaveBeenCalledTimes(1);
    });
});
