// @vitest-environment jsdom
/**
 * ProfileChangesTable — the one table of the changes of the asset profile (plan 68, E6a; round 38: «un componente
 * solo, fatto con DataTable, che riceve righe diverse»), shown by the «Ultime variazioni» panel and by the «Storia del
 * dato» window.
 *
 * Pinned here, on stable handles (`data-kind`, `data-source`, `data-*` of the pager), never on a translated text:
 *   - a row per change, its «Cosa è cambiato» kind; the «Dato» column only where the host asks for it (the panel);
 *   - «Chi»: the author of a value written by hand by username, a source by its name;
 *   - «Dimentica» of one row and of the rows chosen asks first, and hands the host the ids only on confirm;
 *   - the pager: the host owns the page (the server pages by twenty), the table asks for the next one.
 *   - 77 SEL-D: the table draws its selection panel — the bar at the top with the hint, «Dimentica» with the number of
 *     rows it takes — and the pager is the table's balloon (`DataTablePagination`, the server's total), the second row
 *     of the dock under the actions when they come down (the designer's (b), 20/11).
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {_} from '$lib/i18n';
// The countries' names are not the table's to test: no network for them.
vi.mock('$lib/stores/reference/countryStore', () => ({ensureCountriesLoaded: vi.fn(async () => undefined), getCountryInfo: (iso3: string) => ({name: iso3})}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {ProfileVoice} from './profileStore';
import type {ProfileChange} from './profileChanges';
import ProfileChangesTable from './ProfileChangesTable.svelte';

const TER = {key: 'ter', shape: 'percentage', groups: ['costs'], volatile: false} as unknown as ProfileVoice;
const VOICES: Record<string, ProfileVoice> = {ter: TER};

function change(id: number, fields: Partial<ProfileChange> = {}): ProfileChange {
    return {
        id,
        key: 'ter',
        value: '0.0014',
        previous: '0.0012',
        has_previous: true,
        source: 'justetf',
        user_id: null,
        user_name: null,
        user_avatar_url: null,
        read_on: '2026-11-08',
        source_date: null,
        created_at: '2026-11-08T10:00:00Z',
        previous_source: 'justetf',
        previous_user_id: null,
        previous_user_name: null,
        previous_read_on: '2026-11-01',
        previous_source_date: null,
        ...fields,
    } as ProfileChange;
}

const ROWS = [change(11, {previous_source: 'user', previous_user_name: 'anna'}), change(10, {source: 'user', user_id: 3, user_name: 'anna', value: '0.0012', previous: '0.0014'}), change(9, {has_previous: false, previous: null, previous_source: null})];

function mount(props: Record<string, unknown> = {}) {
    const onforget = vi.fn(async () => undefined);
    const onpage = vi.fn();
    render(ProfileChangesTable, {props: {rows: ROWS, voices: VOICES, total: ROWS.length, page: 0, sourceNames: {justetf: 'justETF'}, showVoice: true, onforget, onpage, storageKey: 'test-profile-changes', ...props}});
    return {onforget, onpage};
}

/** The row's menu, by its right-click: the ⋮ button opens the same menu, positioned by a frame jsdom never draws
 *  (`DataEditor.test.ts` says why). */
async function openRowMenu(rowId: string) {
    const row = screen.getByTestId('profile-changes-table').querySelector<HTMLElement>(`tr[data-row-id="${rowId}"]`);
    if (!row) throw new Error(`no row ${rowId}`);
    await fireEvent.contextMenu(row, {clientX: 10, clientY: 10});
}

beforeAll(async () => {
    await setupI18n('en');
});

afterEach(() => {
    cleanup();
});

describe('ProfileChangesTable', () => {
    it('draws one row per change with its kind, and the voice column only where the host asks', async () => {
        mount();
        expect(screen.getByTestId('profile-change-what-11')).toHaveAttribute('data-kind', 'backFromHand');
        expect(screen.getByTestId('profile-change-what-10')).toHaveAttribute('data-kind', 'byHand');
        expect(screen.getByTestId('profile-change-what-9')).toHaveAttribute('data-kind', 'first');
        expect(screen.getByTestId('dt-header-voice')).toBeInTheDocument();
        cleanup();
        mount({showVoice: false});
        expect(screen.queryByTestId('dt-header-voice')).toBeNull();
    });

    it('names the author of a value written by hand, and a source by its name', () => {
        mount();
        const byHand = screen.getByTestId('profile-change-who-10');
        expect(byHand).toHaveAttribute('data-source', 'user');
        expect(byHand).toHaveTextContent('anna');
        const bySource = screen.getByTestId('profile-change-who-11');
        expect(bySource).toHaveAttribute('data-source', 'justetf');
        expect(bySource).toHaveTextContent('justETF');
    });

    // 81 U26a: a value from before the profile existed is the system's: the avatar «S» and «System», as the Files page
    // names what the installation itself uploaded. Every other source keeps its two-letter box.
    it('names the value from before the profile «System», with an «S» avatar, and keeps the box for a source', () => {
        const t = get(_);
        mount({rows: [change(21, {source: 'legacy', previous: null, has_previous: false, previous_source: null}), change(22, {source: 'justetf'})], total: 2});
        const system = screen.getByTestId('profile-change-who-21');
        expect(system).toHaveAttribute('data-source', 'legacy');
        expect(system).toHaveTextContent(t('assets.profile.changes.who.system'));
        const avatar = system.querySelector('[data-avatar="initial"]');
        expect(avatar, 'no initial avatar for the system').not.toBeNull();
        expect(avatar?.textContent?.trim()).toBe(t('assets.profile.changes.who.system').charAt(0).toUpperCase());
        expect(screen.getByTestId('profile-change-who-22').querySelector('[data-avatar]'), 'a source drew an avatar').toBeNull();
    });

    it('forgets one row only after the confirmation, and nothing on cancel', async () => {
        const {onforget} = mount();
        await openRowMenu('10');
        await fireEvent.click(await screen.findByTestId('profile-change-forget-10'));
        await screen.findByTestId('profile-changes-confirm');
        expect(onforget).not.toHaveBeenCalled();
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        expect(onforget).not.toHaveBeenCalled();

        await openRowMenu('10');
        await fireEvent.click(await screen.findByTestId('profile-change-forget-10'));
        await screen.findByTestId('profile-changes-confirm');
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(onforget).toHaveBeenCalledWith([10]));
    });

    it('forgets the rows chosen together, after one confirmation', async () => {
        const {onforget} = mount();
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-11'));
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-9'));
        expect(screen.getByTestId('selection-toolbar')).toHaveAttribute('data-variant', 'top');
        expect(screen.getByTestId('toolbar-action-forget-count').textContent?.trim(), '«Dimentica» says how many rows it takes').toBe('2');
        await fireEvent.click(await screen.findByTestId('toolbar-action-forget'));
        await screen.findByTestId('profile-changes-confirm');
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(onforget).toHaveBeenCalledTimes(1));
        expect([...(onforget.mock.calls[0] as unknown as [number[]])[0]].sort((a, b) => a - b)).toEqual([9, 11]);
    });

    it('nothing chosen: the bar at the top of the table holds the hint', () => {
        mount();
        expect(screen.getByTestId('dt-selection-top')).toBeInTheDocument();
        expect(screen.getByTestId('selection-toolbar-hint')).toBeInTheDocument();
    });

    it('pages by the server, in the table’s balloon: the range, and the next page asked of the host', async () => {
        const {onpage} = mount({total: 45, page: 1});
        const pager = screen.getByTestId('profile-changes-pager');
        expect(pager).toHaveAttribute('data-from', '21');
        expect(pager).toHaveAttribute('data-to', '23');
        expect(pager).toHaveAttribute('data-total', '45');
        const balloon = within(pager).getByTestId('data-table-pagination');
        expect(screen.getByTestId('dt-dock')).toContainElement(balloon);
        expect(within(pager).getByTestId('pagination-prev')).not.toBeDisabled();
        await fireEvent.click(within(pager).getByTestId('pagination-next'));
        expect(onpage).toHaveBeenCalledWith(2);
        await fireEvent.click(within(pager).getByTestId('pagination-prev'));
        expect(onpage).toHaveBeenCalledWith(0);
    });

    it('drops the selection when another page comes: «Dimentica» never reaches rows no longer shown', async () => {
        const onforget = vi.fn(async () => undefined);
        const props = {rows: ROWS, voices: VOICES, total: 45, page: 0, sourceNames: {}, showVoice: true, onforget, onpage: vi.fn(), storageKey: 'test-profile-changes'};
        const {rerender} = render(ProfileChangesTable, {props});
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-11'));
        expect(await screen.findByTestId('toolbar-action-forget')).toBeInTheDocument();

        await rerender({...props, page: 1, rows: [change(31), change(30)]});

        await waitFor(() => expect(screen.queryByTestId('toolbar-action-forget')).toBeNull());
        await fireEvent.click(screen.getByTestId('dt-row-checkbox-30'));
        await fireEvent.click(await screen.findByTestId('toolbar-action-forget'));
        await screen.findByTestId('profile-changes-confirm');
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(onforget).toHaveBeenCalledWith([30]));
    });

    it('on a phone shows one column: the sentence over the day, the voice and who wrote it (shot 14)', async () => {
        const matchMedia = vi.fn((query: string) => ({matches: query.includes('max-width'), media: query, addEventListener: vi.fn(), removeEventListener: vi.fn()}));
        vi.stubGlobal('matchMedia', matchMedia);
        try {
            mount();
            await waitFor(() => expect(screen.queryByTestId('dt-header-when')).toBeNull());
            expect(screen.queryByTestId('dt-header-voice')).toBeNull();
            expect(screen.queryByTestId('dt-header-who')).toBeNull();
            expect(screen.getByTestId('dt-header-what')).toBeInTheDocument();
            const detail = screen.getByTestId('profile-change-detail-10');
            expect(detail).toContainElement(screen.getByTestId('profile-change-who-10'));
            expect(screen.getByTestId('profile-change-who-10')).toHaveTextContent('anna');
        } finally {
            vi.unstubAllGlobals();
        }
    });

    it('closes the pager at the ends', () => {
        mount({total: 3, page: 0});
        const pager = screen.getByTestId('profile-changes-pager');
        expect(within(pager).getByTestId('pagination-prev')).toBeDisabled();
        expect(within(pager).getByTestId('pagination-next')).toBeDisabled();
    });
});
