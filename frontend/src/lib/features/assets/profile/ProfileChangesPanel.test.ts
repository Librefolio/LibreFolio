// @vitest-environment jsdom
/**
 * ProfileChangesPanel — «Ultime variazioni» on the «Profilo» tab (plan 68, E6a; round 40: folded and closed).
 *
 * Pinned here, with the profile memory mocked (the table's own behaviour is `ProfileChangesTable.test.ts`):
 *   - closed at first, it reads nothing; opened, it reads the changes only (`keys: []`, `changes: {page: 0}`) and
 *     publishes its state (`data-status`, `data-busy`);
 *   - «Dimentica» sends the `as_of` of the read that showed the rows, then tells the tab (`onchanged`) and reads again;
 *   - a refusal (`newer`, `not_found`) reads again too, and says so; nothing is lost silently;
 *   - a page emptied by a forget falls back to the one before.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const readAssetProfile = vi.fn();
const forgetProfileRows = vi.fn();
const notify = vi.fn();
vi.mock('./profileStore', () => ({readAssetProfile: (...args: unknown[]) => readAssetProfile(...args), forgetProfileRows: (...args: unknown[]) => forgetProfileRows(...args)}));
vi.mock('./profileSources', async (original) => ({...((await original()) as object), loadProfileSources: vi.fn(async () => ({justetf: {name: 'justETF', icon: null}}))}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: (...args: unknown[]) => notify(...args)}));
vi.mock('$lib/stores/reference/countryStore', () => ({ensureCountriesLoaded: vi.fn(async () => undefined), getCountryInfo: (iso3: string) => ({name: iso3})}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {ProfileVoice} from './profileStore';
import ProfileChangesPanel from './ProfileChangesPanel.svelte';

const VOICES: Record<string, ProfileVoice> = {ter: {key: 'ter', shape: 'percentage', groups: ['costs'], volatile: false} as unknown as ProfileVoice};

function change(id: number) {
    return {
        id,
        key: 'ter',
        value: '0.0014',
        previous: null,
        has_previous: false,
        source: 'justetf',
        user_id: null,
        user_name: null,
        user_avatar_url: null,
        read_on: '2026-11-08',
        source_date: null,
        created_at: '2026-11-08T10:00:00Z',
        previous_source: null,
        previous_user_id: null,
        previous_user_name: null,
        previous_read_on: null,
        previous_source_date: null,
    };
}

function page(ids: number[], total = ids.length, number = 0, asOf = 'AS-OF-1') {
    return {kind: 'found', asOf, voices: {}, changes: {items: ids.map(change), total, page: number, page_size: 20}};
}

function mount(props: Record<string, unknown> = {}) {
    const onchanged = vi.fn();
    render(ProfileChangesPanel, {props: {assetId: 7, voices: VOICES, onchanged, ...props}});
    return {onchanged};
}

async function open() {
    await fireEvent.click(screen.getByTestId('profile-changes-toggle'));
    await waitFor(() => expect(screen.getByTestId('profile-changes-panel')).toHaveAttribute('data-status', 'ready'));
}

async function forgetRow(rowId: string) {
    const row = screen.getByTestId('profile-changes-table').querySelector<HTMLElement>(`tr[data-row-id="${rowId}"]`);
    if (!row) throw new Error(`no row ${rowId}`);
    await fireEvent.contextMenu(row, {clientX: 10, clientY: 10});
    await fireEvent.click(await screen.findByTestId(`profile-change-forget-${rowId}`));
    await fireEvent.click(await screen.findByTestId('confirm-modal-confirm'));
}

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    readAssetProfile.mockReset();
    forgetProfileRows.mockReset();
    notify.mockReset();
});

afterEach(() => cleanup());

describe('ProfileChangesPanel', () => {
    it('is closed at first and reads nothing; opened, it reads the changes only', async () => {
        readAssetProfile.mockResolvedValue(page([2, 1]));
        mount();
        expect(screen.getByTestId('profile-changes-panel')).toHaveAttribute('data-open', 'false');
        expect(readAssetProfile).not.toHaveBeenCalled();

        await open();

        expect(readAssetProfile).toHaveBeenCalledTimes(1);
        const [assetId, , options] = readAssetProfile.mock.calls[0] as [number, unknown, {keys: string[]; changes: {page: number}}];
        expect(assetId).toBe(7);
        expect(options).toEqual({keys: [], changes: {page: 0}});
        expect(screen.getByTestId('profile-change-what-2')).toBeInTheDocument();
    });

    it('forgets with the as_of of the read that showed the row, tells the tab, and reads again', async () => {
        readAssetProfile.mockResolvedValueOnce(page([2, 1], 2, 0, 'AS-OF-SHOWN')).mockResolvedValue(page([1], 1, 0, 'AS-OF-2'));
        forgetProfileRows.mockResolvedValue({kind: 'forgotten', deleted: 1});
        const {onchanged} = mount();
        await open();

        await forgetRow('2');

        await waitFor(() => expect(forgetProfileRows).toHaveBeenCalledWith(7, [2], 'AS-OF-SHOWN'));
        await waitFor(() => expect(onchanged).toHaveBeenCalledTimes(1));
        await waitFor(() => expect(readAssetProfile).toHaveBeenCalledTimes(2));
        await waitFor(() => expect(screen.queryByTestId('profile-change-what-2')).toBeNull());
        expect(notify.mock.calls.at(-1)?.[0]).toMatchObject({name: 'asset.profile.changes.forgotten', detail: {asset_id: 7, deleted: 1}});
    });

    it('reads again and says so when the server refuses the forget', async () => {
        readAssetProfile.mockResolvedValue(page([2, 1]));
        forgetProfileRows.mockResolvedValue({kind: 'newer', updateIds: [2]});
        const {onchanged} = mount();
        await open();

        await forgetRow('2');

        await waitFor(() => expect(readAssetProfile).toHaveBeenCalledTimes(2));
        expect(notify.mock.calls.at(-1)?.[0]).toMatchObject({name: 'asset.profile.changes.refused', detail: {asset_id: 7, reason: 'newer'}});
        expect(onchanged).toHaveBeenCalledTimes(1);
    });

    it('falls back to the page before when a forget empties the last one', async () => {
        readAssetProfile
            .mockResolvedValueOnce(page([5], 21, 0))
            .mockResolvedValueOnce(page([1], 21, 1))
            .mockResolvedValueOnce(page([], 20, 1))
            .mockResolvedValue(page([5], 20, 0));
        forgetProfileRows.mockResolvedValue({kind: 'forgotten', deleted: 1});
        mount();
        await open();
        await fireEvent.click(within(screen.getByTestId('profile-changes-pager')).getByTestId('pagination-next'));
        await waitFor(() => expect(screen.getByTestId('profile-change-what-1')).toBeInTheDocument());

        await forgetRow('1');

        await waitFor(() => expect(screen.getByTestId('profile-changes-pager')).toHaveAttribute('data-page', '0'));
        const pages = readAssetProfile.mock.calls.map((call) => (call[2] as {changes: {page: number}}).changes.page);
        expect(pages).toEqual([0, 1, 1, 0]);
    });
});
