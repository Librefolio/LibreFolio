// @vitest-environment jsdom
/**
 * UserRow and the account's avatar (lot N69-4: N69 point 4, decision D8 (a)).
 *
 * `GET /users` and the answer of `PATCH /users/{id}` carry `avatar_url` for every account — the avatar of its user
 * settings, an image uploaded to the app (`/api/v1/uploads/file/<id>`) or an address, null when it has none; pinned in
 * `test_users_admin_api.py`, UADM-AV-01 to UADM-AV-04 —, and `AdminAccount` (`./types.ts`) gains it, optional: an older
 * server sends nothing. The row draws it in its toggle (`users-row-toggle`), right after the chevron and before the
 * name, through `UserAvatar` (`$lib/components/ui/media/UserAvatar.svelte`, a 24 px circle), whose root carries
 * `data-testid="users-row-avatar"` and `data-avatar="image"` or `data-avatar="initial"`.
 *
 * The contract under test:
 *   - an account with an avatar: one `users-row-avatar`, in the toggle, after the chevron and before the username,
 *     `data-avatar="image"`; its image is named by the username (`alt`); an image uploaded to the app is asked for as its
 *     48×48 preview — `?img_preview=48x48`, or `&img_preview=48x48` after the query it already has —, an address
 *     elsewhere as it is;
 *   - an account without one — `avatar_url` null, or absent —: `data-avatar="initial"`, the username's first character
 *     upper-cased, in the same place, and no image asked for;
 *   - the guard, green today and after: the toggle still shows the username, and still opens and closes the panel.
 *
 * How «the image it asks for» is read, with the real `LazyImage` and no stand-in for it. `LazyImage` asks in one of two
 * ways: the address of a preview of an uploaded file (`/api/v1/uploads/file/<hex id>?img_preview=WxH`, which `abc` is)
 * is fetched as a blob, for its cache of previews, its `<img>` waiting meanwhile with an empty `src`; any other address
 * goes to the `<img>`'s `src` as it is. So `fetch` is a spy that never answers — no blob, no cache entry, nothing that
 * outlives the case; it rejects once aborted, as a browser's does, when the row unmounts —, and the images asked for are
 * the addresses it received plus the `src` of the avatar's `<img>` elements, the drawn placeholder (`data:`) and an
 * empty `src` aside. Whichever way the avatar draws its image, `LazyImage` or not, the address lands in one of the two.
 *
 * The chevron has no test id: it is the toggle's icon, an `<svg>` (lucide), its only one outside the avatar. Never a
 * class or a colour: the avatar's colours are roles, which the colour gates watch.
 *
 * Mocks, as `UserRow.verification.test.ts`: the identity translator (a message renders as its key) and `formatDateTime`
 * (the row's date is not the subject); and `fetch`, as above. What runs for real: the row, and whatever draws its
 * avatar.
 *
 * Red until N69-4, every case marked so: the row draws no avatar today, no `users-row-avatar`. The fixtures carry
 * `avatar_url`, which `AdminAccount` gains in N69-4: until then this file is red at the type check too.
 */
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import {readable} from 'svelte/store';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/utils/core/formatDateTime', () => ({formatDateTime: () => '2026-10-19'}));

import UserRow from './UserRow.svelte';
import type {AdminAccount} from './types';

// --- Fixtures -------------------------------------------------------------

/** A username starting lower-case: its initial is upper-cased. */
const USERNAME = 'zoe';
const INITIAL = 'Z';
/** An avatar at an address outside the app, with a query of its own. */
const ADDRESS = 'https://example.org/a.png?size=2';
/** An image uploaded to the app. */
const UPLOADED_FILE = '/api/v1/uploads/file/abc';

/** An account as `GET /users` lists it. `avatar_url` only when given: without it, the answer of an older server. */
function makeAccount(flags: Partial<AdminAccount> = {}): AdminAccount {
    return {id: 41, username: USERNAME, email: `${USERNAME}@example.com`, is_active: true, is_superuser: false, created_at: '2026-10-19T00:00:00Z', protected: false, ...flags};
}

/** Images uploaded to the app, and the query their preview is asked for with: the one they had, kept, and img_preview added once. */
const UPLOADED = [
    {label: 'an uploaded image', avatarUrl: UPLOADED_FILE, query: [['img_preview', '48x48']]},
    {
        label: 'an uploaded image whose address has a query',
        avatarUrl: `${UPLOADED_FILE}?v=2`,
        query: [
            ['v', '2'],
            ['img_preview', '48x48'],
        ],
    },
];

/** Accounts without an avatar: null, or absent (an older server). */
const WITHOUT: {label: string; flags: Partial<AdminAccount>}[] = [
    {label: 'avatar_url null', flags: {avatar_url: null}},
    {label: 'avatar_url absent (an older server)', flags: {}},
];

// --- The fetch of the case ------------------------------------------------

/** The `fetch` of the case: it never answers, and rejects once its signal aborts, as a browser's does. */
let fetchSpy: Mock<typeof fetch>;

beforeEach(() => {
    fetchSpy = vi.fn<typeof fetch>(
        (_input: RequestInfo | URL, init?: RequestInit) =>
            new Promise<Response>((_resolve, reject) => {
                const signal = init?.signal;
                const abort = () => reject(signal?.reason ?? new DOMException('The operation was aborted.', 'AbortError'));
                if (signal?.aborted) {
                    abort();
                } else {
                    signal?.addEventListener('abort', abort, {once: true});
                }
            }),
    );
    vi.stubGlobal('fetch', fetchSpy);
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

// --- DOM helpers ----------------------------------------------------------

interface Mounted {
    row: HTMLElement;
    toggle: HTMLElement;
}

/** Mount one row, another account's, on an instance with room left: the avatar depends on neither. */
function mount(account: AdminAccount): Mounted {
    render(UserRow, {props: {account, isSelf: false, isOnlyActiveAdmin: false, full: false, onAction: vi.fn()}});
    const row = screen.getByTestId('users-row');
    return {row, toggle: within(row).getByTestId('users-row-toggle')};
}

/** The row's avatar: exactly one, and in its toggle. */
function avatarOf({row, toggle}: Mounted): HTMLElement {
    const avatars = within(row).queryAllByTestId('users-row-avatar');
    expect(avatars, 'the users-row-avatar of the row').toHaveLength(1);
    expect(toggle.contains(avatars[0]), 'the avatar sits in users-row-toggle').toBe(true);
    return avatars[0];
}

/** `later` comes after `earlier` in the document, and is not inside it. */
function comesAfter(earlier: Node, later: Node): boolean {
    return !earlier.contains(later) && (earlier.compareDocumentPosition(later) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

/** The toggle draws its chevron, then the avatar, then the username. */
function expectAfterTheChevronBeforeTheName({toggle}: Mounted, avatar: HTMLElement): void {
    const chevron = [...toggle.querySelectorAll('svg')].find((icon) => !avatar.contains(icon));
    if (chevron === undefined) throw new Error('users-row-toggle draws no chevron: no <svg> outside the avatar');
    const names = within(toggle)
        .getAllByText(USERNAME)
        .filter((element) => !avatar.contains(element));
    expect(names, 'the username, outside the avatar').toHaveLength(1);
    expect(comesAfter(chevron, avatar), 'the avatar comes after the chevron').toBe(true);
    expect(comesAfter(avatar, names[0]), 'the username comes after the avatar').toBe(true);
}

/** The address a `fetch` call asked for, whatever form it was given in. */
function addressOf(input: RequestInfo | URL): string {
    if (typeof input === 'string') return input;
    return input instanceof URL ? input.href : input.url;
}

/** The images the avatar asks for, each once: the addresses `fetch` received, and the `src` of its `<img>` elements, the drawn placeholder (`data:`) and an empty `src` aside. */
function imagesAskedFor(avatar: HTMLElement): string[] {
    const fetched = fetchSpy.mock.calls.map(([input]) => addressOf(input));
    const drawn = [...avatar.querySelectorAll('img')].map((image) => image.getAttribute('src') ?? '').filter((src) => src !== '' && !src.startsWith('data:'));
    return [...new Set([...fetched, ...drawn])];
}

/** The names of the avatar's images, each once: the `alt` of its `<img>` elements. */
function namesOfImages(avatar: HTMLElement): (string | null)[] {
    return [...new Set([...avatar.querySelectorAll('img')].map((image) => image.getAttribute('alt')))];
}

// =========================================================================
describe('UserRow — the account’s avatar, between the chevron and the name (N69-4)', () => {
    // red until N69-4
    it.each(UPLOADED)('URA-01: $label — one users-row-avatar in the toggle, data-avatar="image", between the chevron and the username; its 48×48 preview asked for, named by the username', ({avatarUrl, query}) => {
        const mounted = mount(makeAccount({avatar_url: avatarUrl}));
        const avatar = avatarOf(mounted);

        expect(avatar).toHaveAttribute('data-avatar', 'image');
        expectAfterTheChevronBeforeTheName(mounted, avatar);
        const asked = imagesAskedFor(avatar);
        expect(asked, 'the images the avatar asks for').toHaveLength(1);
        const preview = new URL(asked[0], window.location.href);
        expect({origin: preview.origin, path: preview.pathname, query: [...preview.searchParams]}, `the preview asked for, read from ${asked[0]}`).toEqual({origin: window.location.origin, path: UPLOADED_FILE, query});
        expect(namesOfImages(avatar), 'the alt of its images').toEqual([USERNAME]);
    });

    // red until N69-4
    it('URA-02: an address outside the app — data-avatar="image", the address asked for as it is, named by the username', () => {
        const avatar = avatarOf(mount(makeAccount({avatar_url: ADDRESS})));

        expect(avatar).toHaveAttribute('data-avatar', 'image');
        expect(imagesAskedFor(avatar), 'the images the avatar asks for').toEqual([ADDRESS]);
        expect(namesOfImages(avatar), 'the alt of its images').toEqual([USERNAME]);
    });

    // red until N69-4
    it.each(WITHOUT)('URA-03: $label — data-avatar="initial", the username’s first character upper-cased, between the chevron and the username, and no image asked for', ({flags}) => {
        const mounted = mount(makeAccount(flags));
        const avatar = avatarOf(mounted);

        expect(avatar).toHaveAttribute('data-avatar', 'initial');
        expect(avatar.textContent?.trim(), 'the initial').toBe(INITIAL);
        expectAfterTheChevronBeforeTheName(mounted, avatar);
        // The barriers of the two absences: the avatar is drawn, as the initial. No image beside it, none fetched.
        expect(mounted.toggle.querySelectorAll('img'), 'an image in the toggle').toHaveLength(0);
        expect(fetchSpy, 'an image fetched').not.toHaveBeenCalled();
    });
});

// =========================================================================
describe('UserRow — the rest of its toggle, as before N69-4', () => {
    const SCENES: {label: string; flags: Partial<AdminAccount>}[] = [
        {label: 'with an uploaded avatar', flags: {avatar_url: UPLOADED_FILE}},
        {label: 'without an avatar', flags: {avatar_url: null}},
    ];

    // guard
    it.each(SCENES)('URA-04: $label — the toggle still shows the username, and still opens and closes the panel', async ({flags}) => {
        const {toggle} = mount(makeAccount(flags));

        expect(within(toggle).getAllByText(USERNAME).length, 'the username in the toggle').toBeGreaterThan(0);
        expect(toggle).toHaveAttribute('aria-expanded', 'false');
        const panelId = toggle.getAttribute('aria-controls');
        expect(panelId, 'the panel the toggle controls').not.toBeNull();

        await fireEvent.click(toggle);
        expect(toggle).toHaveAttribute('aria-expanded', 'true');
        expect(document.getElementById(panelId ?? ''), 'the panel, opened').not.toBeNull();

        await fireEvent.click(toggle);
        expect(toggle).toHaveAttribute('aria-expanded', 'false');
        expect(document.getElementById(panelId ?? ''), 'the panel, closed').toBeNull();
    });
});
