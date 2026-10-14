// @vitest-environment jsdom
/**
 * Uploader column contract: real FilesTable, DataTable and enum popover.
 * Only transport, notification delivery and preference persistence are boundaries.
 * Synthetic text files deliberately have no preview images: the uploader image
 * can be addressed through its identified row/column without a made-up cell hook.
 * Parent URL serialization and list/grid composition belong to a page-level E2E.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {BrimFile, FileData, UploadedFile} from '$lib/types';
import type {FilterValue} from '$lib/components/table/types';
import {clientSessionUserId, getClientSessionUserId, transitionClientSession} from '$lib/stores/app/clientSession';
import FilesTable from './FilesTable.svelte';

const boundary = vi.hoisted(() => ({
    searchUsers: vi.fn(),
    notify: vi.fn(),
}));

vi.mock('$lib/api', () => ({
    zodiosApi: {search_users_endpoint_api_v1_users_search_get: boundary.searchUsers},
    axiosInstance: {},
}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: boundary.notify}));
vi.mock('$lib/utils/storage', () => ({getUserStorageKey: (key: string) => `review-uploader-${key}`}));

type TableType = 'static' | 'brim';
const UPLOADED_AT = '2024-03-15T12:00:00Z';
const USER_IDS = {zephyr: 7, atlas10: 41, atlas2: 91, unknown: 8080};
const USERS = [
    {id: USER_IDS.zephyr, username: 'Review Zephyr', avatar_url: '/review/zephyr.svg'},
    // The generated client permits array-valued nullable fields.
    {id: USER_IDS.atlas10, username: 'Review Atlas 10', avatar_url: ['/review/atlas.svg?owned=yes']},
    {id: USER_IDS.atlas2, username: 'Review Atlas 2', avatar_url: null},
    {id: 9999, username: 'Review No Files', avatar_url: null},
];

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((yes, no) => {
        resolve = yes;
        reject = no;
    });
    return {promise, resolve, reject};
}

function filesFor(type: TableType): FileData[] {
    const owners: Array<{id: string; uploader: number | null}> = [
        {id: 'zephyr', uploader: USER_IDS.zephyr},
        {id: 'atlas10', uploader: USER_IDS.atlas10},
        {id: 'atlas2', uploader: USER_IDS.atlas2},
        {id: 'unknown', uploader: USER_IDS.unknown},
    ];
    // Null is a valid BRIM wire value. UploadFileInfo requires a numeric owner;
    // do not fabricate a schema-valid static response by casting null to number.
    if (type === 'brim') owners.push({id: 'none', uploader: null});
    return owners.map(({id, uploader}) => {
        const common = {size_bytes: 128, uploaded_at: UPLOADED_AT};
        if (type === 'brim') {
            return {
                ...common,
                file_id: id,
                filename: `review-${id}.txt`,
                status: 'uploaded',
                uploaded_by_user_id: uploader,
                target_broker_id: null,
            } satisfies BrimFile;
        }
        if (uploader === null) throw new Error('Static fixture requires an uploader');
        return {
            ...common,
            id,
            original_name: `review-${id}.txt`,
            mime_type: 'text/plain',
            uploaded_by_user_id: uploader,
            url: `/review/files/${id}`,
        } satisfies UploadedFile;
    });
}

function root(type: TableType): HTMLElement {
    return screen.getByTestId(`files-table-${type}`);
}

function ids(table: HTMLElement): string[] {
    return [...table.querySelectorAll('tbody tr[data-row-id]')].map((row) => row.getAttribute('data-row-id')!);
}

function uploaderCell(table: HTMLElement, id: string): HTMLTableCellElement {
    const header = within(table).getByTestId('dt-header-uploader') as HTMLTableCellElement;
    const row = table.querySelector<HTMLTableRowElement>(`tbody tr[data-row-id="${id}"]`);
    if (!row) throw new Error(`Owned row ${id} not on the single fixture page: ${ids(table).join(', ')}`);
    // This is not a positional data lookup: the column comes from its identity,
    // including any selection/broker columns the real table inserts.
    const cell = row.cells.item(header.cellIndex);
    if (!cell) throw new Error(`Uploader cell absent for owned row ${id}`);
    return cell;
}

function imageIn(element: HTMLElement): HTMLImageElement {
    const images = element.querySelectorAll('img');
    expect(images).toHaveLength(1);
    const image = element.querySelector('img');
    if (!image) throw new Error('Expected the identified uploader image');
    return image;
}

async function openUploaderFilter(table: HTMLElement): Promise<HTMLElement> {
    await fireEvent.click(within(table).getByTestId('col-filter-trigger-uploader'));
    const popover = await within(table).findByTestId('column-filter');
    expect(popover).toHaveAttribute('data-filter-type', 'enum');
    return popover;
}

async function settled(type: TableType) {
    await waitFor(() => expect(root(type)).toHaveAttribute('data-users-state', 'ready'));
    expect(root(type)).toHaveAttribute('data-busy', 'false');
    return root(type);
}

function mount(type: TableType, initialFilters?: Record<string, FilterValue>) {
    const onFiltersChange = vi.fn();
    const result = render(FilesTable, {type, files: filesFor(type), onDelete: vi.fn(), initialFilters, onFiltersChange});
    return {...result, onFiltersChange};
}

let previousUser: string | null;
beforeAll(async () => {
    await setupI18n();
});
beforeEach(() => {
    boundary.searchUsers.mockReset().mockResolvedValue({items: USERS});
    boundary.notify.mockReset();
    // Isolate the real table's hard-coded storageKey without clearing anyone
    // else's storage or importing the authentication/network tree.
    vi.stubGlobal('localStorage', {getItem: () => null, setItem: vi.fn(), removeItem: vi.fn()});
    previousUser = getClientSessionUserId();
    transitionClientSession('review-uploader-session');
});
afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    transitionClientSession(previousUser);
    vi.unstubAllGlobals();
});

describe.each(['static', 'brim'] as const)('FilesTable %s uploaders', (type) => {
    it('loads all active users once, retaining rows while the lookup is pending', async () => {
        const request = deferred<{items: typeof USERS}>();
        boundary.searchUsers.mockReturnValueOnce(request.promise);
        mount(type);
        const table = root(type);
        expect(table).toHaveAttribute('data-users-state', 'loading');
        expect(table).toHaveAttribute('data-busy', 'true');
        expect(table).toHaveAttribute('aria-busy', 'true');
        const before = ids(table);
        expect(before).toContain('atlas2');
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('#91');
        expect(boundary.searchUsers).toHaveBeenCalledExactlyOnceWith({queries: {q: ''}});

        request.resolve({items: USERS});
        await settled(type);
        expect(ids(table)).toEqual(before);
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('Review Atlas 2');
        expect(table).toHaveAttribute('aria-busy', 'false');
        expect(boundary.notify).not.toHaveBeenCalled();
    });

    it('renders normalized avatar URLs and hides a failed native image without losing the username', async () => {
        mount(type);
        const table = await settled(type);
        const cell = uploaderCell(table, 'atlas10');
        const image = imageIn(cell);
        expect(image).toHaveAttribute('src', '/review/atlas.svg?owned=yes&img_preview=32x32');
        expect(image).toHaveAttribute('alt', '');
        expect(image).toHaveAttribute('width', '20');
        expect(image).toHaveAttribute('height', '20');
        const plain = imageIn(uploaderCell(table, 'zephyr'));
        expect(plain).toHaveAttribute('src', '/review/zephyr.svg?img_preview=32x32');
        expect(imageIn(uploaderCell(table, 'atlas2')).getAttribute('src')).toMatch(/^data:image\/svg\+xml,/);
        const fallbackIcon = image.nextElementSibling?.querySelector('svg');
        expect(fallbackIcon).toBeInTheDocument();
        expect(image).toBeVisible();

        await fireEvent.error(image);
        expect(image).not.toBeVisible();
        // Assert retained fallback markup, not a pretend Tailwind visibility
        // transition in jsdom. Circular clipping / CSS reveal need a browser.
        expect(fallbackIcon).toBeInTheDocument();
        expect(cell).toHaveTextContent('Review Atlas 10');
        expect(plain).toBeVisible();
    });

    it('searches by username and numeric ID, retaining multi-selection and unused options', async () => {
        const {onFiltersChange} = mount(type);
        const table = await settled(type);
        const unfilteredIds = ids(table);
        const popover = await openUploaderFilter(table);
        const controls = within(popover);
        expect(controls.queryByTestId('filter-enum-option-9999')).toBeNull();
        expect(controls.getByTestId('filter-enum-option-8080')).toBeInTheDocument();
        const knownOptionIds = new Set(['filter-enum-option-7', 'filter-enum-option-41', 'filter-enum-option-91']);
        const knownOptionOrder = [...popover.querySelectorAll('[data-testid^="filter-enum-option-"]')].map((option) => option.getAttribute('data-testid')).filter((id): id is string => id !== null && knownOptionIds.has(id));
        expect(knownOptionOrder).toEqual(['filter-enum-option-91', 'filter-enum-option-41', 'filter-enum-option-7']);

        await fireEvent.input(controls.getByTestId('filter-enum-search'), {target: {value: '  aTLAs 2  '}});
        expect(controls.getByTestId('filter-enum-option-91')).toHaveTextContent('Review Atlas 2');
        expect(controls.queryByTestId('filter-enum-option-41')).toBeNull();
        await fireEvent.click(controls.getByTestId('filter-enum-option-91'));
        await waitFor(() => expect(ids(table)).toEqual(['atlas2']));
        expect(controls.getByTestId('filter-enum-option-91')).toHaveAttribute('data-checked', 'true');

        await fireEvent.input(controls.getByTestId('filter-enum-search'), {target: {value: '8080'}});
        await fireEvent.click(controls.getByTestId('filter-enum-option-8080'));
        await waitFor(() => expect(new Set(ids(table))).toEqual(new Set(['atlas2', 'unknown'])));
        expect(onFiltersChange).toHaveBeenLastCalledWith({uploader: {type: 'enum', selected: ['91', '8080']}});

        await fireEvent.click(controls.getByTestId('filter-enum-search-clear'));
        expect(controls.getByTestId('filter-enum-option-91')).toHaveAttribute('data-checked', 'true');
        expect(controls.getByTestId('filter-enum-option-8080')).toHaveAttribute('data-checked', 'true');
        expect(controls.getByTestId('filter-enum-option-41')).toHaveAttribute('data-checked', 'false');
        // Filtering rows never removes an option whose rows are now off-screen.
        expect(controls.getByTestId('filter-enum-option-7')).toBeInTheDocument();
        await fireEvent.click(controls.getByTestId('column-filter-reset'));
        await waitFor(() => expect(ids(table)).toEqual(unfilteredIds));
        expect(onFiltersChange).toHaveBeenLastCalledWith({});
    });

    it('deduplicates uploader options without collapsing files belonging to the same uploader', async () => {
        const files = filesFor(type);
        const original = files.find((file) => file.uploaded_by_user_id === USER_IDS.atlas2);
        if (!original) throw new Error('Owned Atlas fixture is missing');
        const duplicate: FileData = type === 'static' ? {...(original as UploadedFile), id: 'atlas2-copy', original_name: 'review-atlas2-copy.txt'} : {...(original as BrimFile), file_id: 'atlas2-copy', filename: 'review-atlas2-copy.txt'};
        render(FilesTable, {type, files: [...files, duplicate], onDelete: vi.fn()});
        const table = await settled(type);
        expect(ids(table)).toEqual(expect.arrayContaining(['atlas2', 'atlas2-copy']));
        const popover = await openUploaderFilter(table);
        const controls = within(popover);
        expect(controls.getAllByTestId('filter-enum-option-91')).toHaveLength(1);
        await fireEvent.click(controls.getByTestId('filter-enum-option-91'));
        expect(ids(table)).toEqual(['atlas2', 'atlas2-copy']);
    });

    it('uses the enum icon candidate chain when an avatar fails', async () => {
        mount(type);
        const popover = await openUploaderFilter(await settled(type));
        const option = within(popover).getByTestId('filter-enum-option-41');
        const image = imageIn(option);
        expect(image).toHaveAttribute('src', '/review/atlas.svg?owned=yes&img_preview=32x32');
        expect(image).toHaveAttribute('referrerpolicy', 'no-referrer');
        await fireEvent.error(image);
        expect(image.getAttribute('src')).toMatch(/^data:image\/svg\+xml,/);
        expect(option).toHaveTextContent('Review Atlas 10');
        expect(option).toHaveAttribute('data-checked', 'false');
    });

    it('sorts known uploaders by natural username order, not their IDs or filenames', async () => {
        mount(type);
        const table = await settled(type);
        const sort = within(table).getByTestId('dt-sort-uploader');
        const knownIds = new Set(['zephyr', 'atlas10', 'atlas2']);
        const knownOrder = () => ids(table).filter((id) => knownIds.has(id));
        await fireEvent.click(sort);
        expect(knownOrder()).toEqual(['atlas2', 'atlas10', 'zephyr']);
        await fireEvent.click(sort);
        expect(knownOrder()).toEqual(['zephyr', 'atlas10', 'atlas2']);
        await fireEvent.click(sort);
        expect(knownOrder()).toEqual(['zephyr', 'atlas10', 'atlas2']);
    });

    it('accepts the uploader URL-key contract before and after lookup completion', async () => {
        const request = deferred<{items: typeof USERS}>();
        boundary.searchUsers.mockReturnValueOnce(request.promise);
        const {onFiltersChange} = mount(type, {uploader: {type: 'enum', selected: ['41', '8080']}});
        const table = root(type);
        await waitFor(() => expect(ids(table)).toEqual(['atlas10', 'unknown']));
        request.resolve({items: USERS});
        await settled(type);
        expect(ids(table)).toEqual(['atlas10', 'unknown']);
        expect(onFiltersChange).toHaveBeenLastCalledWith({uploader: {type: 'enum', selected: ['41', '8080']}});
        const popover = await openUploaderFilter(table);
        expect(within(popover).getByTestId('filter-enum-option-41')).toHaveAttribute('data-checked', 'true');
        expect(within(popover).getByTestId('filter-enum-option-8080')).toHaveAttribute('data-checked', 'true');
    });

    it('publishes a warning on lookup failure and preserves every owned file', async () => {
        const request = deferred<{items: typeof USERS}>();
        boundary.searchUsers.mockReturnValueOnce(request.promise);
        mount(type);
        const table = root(type);
        const before = ids(table);
        expect(before).toContain('zephyr');
        request.reject(new Error('review-lookup-failed'));
        await waitFor(() => expect(table).toHaveAttribute('data-users-state', 'error'));
        expect(table).toHaveAttribute('data-busy', 'false');
        expect(ids(table)).toEqual(before);
        expect(boundary.notify).toHaveBeenCalledExactlyOnceWith(
            expect.objectContaining({
                name: 'files.uploaders.failed',
                detail: {reason: 'review-lookup-failed'},
                toast: expect.objectContaining({variant: 'warning'}),
            }),
        );
        const popover = await openUploaderFilter(table);
        await fireEvent.click(within(popover).getByTestId('filter-enum-option-8080'));
        expect(ids(table)).toEqual(['unknown']);
    });
});

describe('FilesTable absent and stale uploader identities', () => {
    it('keeps null BRIM owners distinct from unknown numeric IDs and known accounts', async () => {
        mount('brim');
        const table = await settled('brim');
        const popover = await openUploaderFilter(table);
        const controls = within(popover);
        expect(controls.getByTestId('filter-enum-option-__none__')).toBeInTheDocument();
        expect(controls.getByTestId('filter-enum-option-8080')).toBeInTheDocument();
        await fireEvent.click(controls.getByTestId('filter-enum-option-__none__'));
        expect(ids(table)).toEqual(['none']);
        await fireEvent.click(controls.getByTestId('filter-enum-option-8080'));
        expect(new Set(ids(table))).toEqual(new Set(['none', 'unknown']));
        expect(controls.getByTestId('filter-enum-option-91')).toHaveAttribute('data-checked', 'false');
    });

    it('treats an empty successful lookup as ready, with numeric fallback identities still usable', async () => {
        boundary.searchUsers.mockResolvedValueOnce({items: []});
        mount('static');
        const table = await settled('static');
        expect(uploaderCell(table, 'zephyr')).toHaveTextContent('#7');
        const popover = await openUploaderFilter(table);
        await fireEvent.click(within(popover).getByTestId('filter-enum-option-7'));
        expect(ids(table)).toEqual(['zephyr']);
        expect(boundary.notify).not.toHaveBeenCalled();
    });

    it('stays idle without an identity, then loads names when an account arrives', async () => {
        transitionClientSession(null);
        mount('static');
        const table = root('static');
        await tick();
        expect(table).toHaveAttribute('data-users-state', 'idle');
        expect(table).toHaveAttribute('data-busy', 'false');
        expect(table).toHaveAttribute('aria-busy', 'false');
        expect(boundary.searchUsers).not.toHaveBeenCalled();
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('#91');

        transitionClientSession('review-new-login');
        await settled('static');
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('Review Atlas 2');
        expect(boundary.searchUsers).toHaveBeenCalledExactlyOnceWith({queries: {q: ''}});
    });

    it('clears resolved names on account replacement and refetches for that identity only once', async () => {
        mount('static');
        const table = await settled('static');
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('Review Atlas 2');
        const replacement = deferred<{items: typeof USERS}>();
        boundary.searchUsers.mockReturnValueOnce(replacement.promise);

        transitionClientSession('review-replacement');
        await tick();
        expect(table).toHaveAttribute('data-users-state', 'loading');
        expect(table).toHaveAttribute('data-busy', 'true');
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('#91');
        expect(uploaderCell(table, 'atlas2')).not.toHaveTextContent('Review Atlas 2');
        expect(boundary.searchUsers).toHaveBeenCalledTimes(2);
        expect(boundary.searchUsers).toHaveBeenLastCalledWith({queries: {q: ''}});
        transitionClientSession('review-replacement');
        await tick();
        expect(boundary.searchUsers).toHaveBeenCalledTimes(2);

        replacement.resolve({items: [{id: 91, username: 'Review Replacement', avatar_url: null}]});
        await settled('static');
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('Review Replacement');
        expect(boundary.notify).not.toHaveBeenCalled();
    });

    it.each(['resolve', 'reject'] as const)('keeps replacement names ready when the previous account lookup later %ss', async (outcome) => {
        const oldRequest = deferred<{items: typeof USERS}>();
        const replacement = deferred<{items: typeof USERS}>();
        boundary.searchUsers.mockReturnValueOnce(oldRequest.promise).mockReturnValueOnce(replacement.promise);
        mount('static');
        const table = root('static');
        expect(table).toHaveAttribute('data-users-state', 'loading');
        transitionClientSession('review-replacement');
        await tick();
        expect(boundary.searchUsers).toHaveBeenCalledTimes(2);
        replacement.resolve({items: [{id: 91, username: 'Review Replacement', avatar_url: null}]});
        await settled('static');
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('Review Replacement');

        if (outcome === 'resolve') oldRequest.resolve({items: USERS});
        else oldRequest.reject(new Error('obsolete-account-request'));
        // Consume the precise response before asserting its lack of side effects.
        await oldRequest.promise.catch(() => undefined);
        await tick();
        expect(table).toHaveAttribute('data-users-state', 'ready');
        expect(table).toHaveAttribute('data-busy', 'false');
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('Review Replacement');
        expect(uploaderCell(table, 'atlas2')).not.toHaveTextContent('Review Atlas 2');
        expect(boundary.notify).not.toHaveBeenCalled();
        expect(boundary.searchUsers).toHaveBeenCalledTimes(2);
    });

    it('clears resolved names on logout and settles idle without fetching', async () => {
        mount('static');
        const table = await settled('static');
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('Review Atlas 2');
        transitionClientSession(null);
        await tick();
        expect(table).toHaveAttribute('data-users-state', 'idle');
        expect(table).toHaveAttribute('data-busy', 'false');
        expect(table).toHaveAttribute('aria-busy', 'false');
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('#91');
        expect(uploaderCell(table, 'atlas2')).not.toHaveTextContent('Review Atlas 2');
        expect(boundary.searchUsers).toHaveBeenCalledTimes(1);
        expect(boundary.notify).not.toHaveBeenCalled();
    });

    it.each(['resolve', 'reject'] as const)('stays idle after logout when an outstanding lookup later %ss', async (outcome) => {
        const request = deferred<{items: typeof USERS}>();
        boundary.searchUsers.mockReturnValueOnce(request.promise);
        mount('static');
        const table = root('static');
        expect(table).toHaveAttribute('data-users-state', 'loading');
        transitionClientSession(null);
        await tick();
        expect(table).toHaveAttribute('data-users-state', 'idle');
        expect(table).toHaveAttribute('data-busy', 'false');
        expect(table).toHaveAttribute('aria-busy', 'false');
        expect(boundary.searchUsers).toHaveBeenCalledTimes(1);

        if (outcome === 'resolve') request.resolve({items: USERS});
        else request.reject(new Error('obsolete-request'));
        await request.promise.catch(() => undefined);
        await tick();
        expect(table).toHaveAttribute('data-users-state', 'idle');
        expect(table).toHaveAttribute('data-busy', 'false');
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('#91');
        expect(uploaderCell(table, 'atlas2')).not.toHaveTextContent('Review Atlas 2');
        expect(boundary.searchUsers).toHaveBeenCalledTimes(1);
        expect(boundary.notify).not.toHaveBeenCalled();
    });

    it('unsubscribes on unmount so later identities cannot start a lookup', async () => {
        const subscribe = clientSessionUserId.subscribe;
        const unsubscribe = vi.fn();
        vi.spyOn(clientSessionUserId, 'subscribe').mockImplementation((run, invalidate) => {
            const stop = subscribe(run, invalidate);
            return () => {
                unsubscribe();
                stop();
            };
        });
        const mounted = mount('static');
        await settled('static');
        expect(unsubscribe).not.toHaveBeenCalled();
        expect(boundary.searchUsers).toHaveBeenCalledTimes(1);

        mounted.unmount();
        expect(screen.queryByTestId('files-table-static')).toBeNull();
        expect(unsubscribe).toHaveBeenCalledTimes(1);
        transitionClientSession('review-after-unmount');
        await tick();
        expect(boundary.searchUsers).toHaveBeenCalledTimes(1);
        expect(boundary.notify).not.toHaveBeenCalled();
    });

    it.each(['resolve', 'reject'] as const)('ignores an unmounted lookup that later %ss beside a new table', async (outcome) => {
        const oldRequest = deferred<{items: typeof USERS}>();
        const readStaleUsername = vi.fn(() => 'Review Stale');
        const staleUsers = [
            {
                id: 91,
                get username() {
                    return readStaleUsername();
                },
                avatar_url: null,
            },
        ];
        boundary.searchUsers.mockReturnValueOnce(oldRequest.promise);
        const old = mount('static');
        expect(root('static')).toHaveAttribute('data-users-state', 'loading');
        old.unmount();
        boundary.searchUsers.mockResolvedValueOnce({items: [{id: 91, username: 'Review Current', avatar_url: null}]});
        mount('static');
        const table = await settled('static');
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('Review Current');
        if (outcome === 'resolve') oldRequest.resolve({items: staleUsers});
        else oldRequest.reject(new Error('unmounted-request'));
        await oldRequest.promise.catch(() => undefined);
        await tick();
        // An unmounted component cannot repaint anyway: DOM absence alone
        // would pass even if it consumed and normalized the stale response.
        expect(readStaleUsername).not.toHaveBeenCalled();
        expect(uploaderCell(table, 'atlas2')).toHaveTextContent('Review Current');
        expect(uploaderCell(table, 'atlas2')).not.toHaveTextContent('Review Stale');
        expect(boundary.notify).not.toHaveBeenCalled();
    });
});
