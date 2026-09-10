// @vitest-environment jsdom
/**
 * ChangelogModal — render, folding, search and bulk fold tests (Vitest + jsdom),
 * F12 round 4, extended in round 5.
 *
 * Round 4: a search box (`changelog-search`) that force-opens matching branches
 * while typing, expand-all/collapse-all controls, and individually foldable
 * `####` subsections (`changelog-subsection-toggle-{ci}-{si}-{ssi}`).
 *
 * Round 5 adds two subjects:
 *  - clickable search hits (`changelog-search-results` chips `changelog-hit-*`):
 *    a hit is offered when the needle matches a section/subsection TITLE **or
 *    its own body** (round-5 follow-up: a bullet deep inside a section is a
 *    "go there" target too); the label always stays the title. Clicking one
 *    unfolds the branch AND sets the manual fold state, which is why the tests
 *    below assert the branch is still open AFTER the query is cleared — while
 *    searching, force-open would mask a click that did nothing. The hit list
 *    is capped at 8; the fixture's v1.0.0 chapter carries ten `### Zed NN`
 *    sections so a single needle can exceed the cap.
 *  - the manual update check in the header (`changelog-check-update`): the same
 *    `checkForUpdates()` contract the login flow now uses, with the outcome
 *    reported only through the `app.update.checked` notification, with no
 *    persistent result/remote-version panel. Admin + newer delegates to
 *    `updateAvailable.show`; non-admin + newer shows the ask-admin modal with
 *    the admin list fetched from the users search.
 *
 * The feature module imports the repo-root CHANGELOG.md via vite's `?raw`,
 * which the jsdom pipeline refuses (fs strictness on a path outside
 * frontend/) — the pure-logic sibling spec (changelog.test.ts, node env)
 * already pins the real parse incl. splitSections. Here the modal's subject is
 * what it DOES with parsed chapters, so the module is stubbed with a known
 * fixture in the round-4 shape (`sections[].subsections[]`).
 *
 * Fold state is read from `aria-expanded` (the a11y contract) cross-checked
 * against DOM presence of the bodies. Translated copy is never asserted; the
 * admin usernames asserted in the modal are this test's own fixture data.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/features/changelog/changelog', () => {
    // Ten Zed sections on the oldest chapter: one needle ("zed") produces ten
    // hits, which is what the cap-at-8 test needs. "Quokka patch" is a ####
    // title no other string in the fixture contains.
    const zedSections = Array.from({length: 10}, (_, i) => ({
        title: `Zed ${String(i + 1).padStart(2, '0')}`,
        body: '- z\n',
        subsections: [],
    }));
    const zedBody = zedSections.map((s) => `### ${s.title}\n- z\n`).join('\n');
    return {
        changelogChapters: [
            {
                version: '1.2.0',
                date: '2026-08-07',
                body: 'Intro notes for 1.2.0.\n\n### Fixed\n- a bug\n\n#### Deep dive\nBug detail text.\n\n### Added\n- a thing\n',
                sections: [
                    {title: null, body: 'Intro notes for 1.2.0.\n', subsections: []},
                    {title: 'Fixed', body: '- a bug\n', subsections: [{title: 'Deep dive', body: 'Bug detail text.\n'}]},
                    {title: 'Added', body: '- a thing\n', subsections: []},
                ],
            },
            {
                version: '1.1.0',
                date: '2026-07-01',
                body: 'Intro for 1.1.0.\n\n#### Notes\nZebra subsection note.\n\n### Added\n- a feature\n',
                sections: [
                    {title: null, body: 'Intro for 1.1.0.\n', subsections: [{title: 'Notes', body: 'Zebra subsection note.\n'}]},
                    {title: 'Added', body: '- a feature\n', subsections: []},
                ],
            },
            {
                version: '1.0.0',
                date: '2026-06-01',
                body: `Intro for 1.0.0.\n\n### Security\n- hardened\n\n#### Quokka patch\nQuokka detail.\n\n${zedBody}`,
                sections: [{title: null, body: 'Intro for 1.0.0.\n', subsections: []}, {title: 'Security', body: '- hardened\n', subsections: [{title: 'Quokka patch', body: 'Quokka detail.\n'}]}, ...zedSections],
            },
        ],
        CHANGELOG_REMOTE_URL: 'https://github.com/Librefolio/LibreFolio/blob/main/CHANGELOG.md',
    };
});

// $lib/api: a Proxy minting a cached spy per method, so `api[SEARCH]` here and
// the call inside the component are the same fn (pattern from AssetModal.test.ts).
vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
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

// auth: a minimal controllable readable store — the update check's admin branch
// reads `$auth.user?.is_superuser`. Default `user: null` = the non-admin path.
const authStore = vi.hoisted(() => {
    type AuthState = {user: {id: number; username: string; is_superuser: boolean} | null};
    let value: AuthState = {user: null};
    const subs = new Set<(v: AuthState) => void>();
    return {
        subscribe(fn: (v: AuthState) => void) {
            subs.add(fn);
            fn(value);
            return () => subs.delete(fn);
        },
        set(v: AuthState) {
            value = v;
            for (const fn of subs) fn(value);
        },
    };
});
vi.mock('$lib/stores/app/auth', () => ({auth: authStore}));

// The update probe (round 5): the modal must use THE SAME checkForUpdates
// contract as the login flow — so it is mocked here, and every test programs
// its answer.
const checkForUpdatesMock = vi.hoisted(() => vi.fn());
vi.mock('$lib/features/update-check/updateCheck', () => ({
    checkForUpdates: checkForUpdatesMock,
}));

// The F14 modal takeover: admin + newer delegates to updateAvailable.show.
const updateAvailableMock = vi.hoisted(() => ({show: vi.fn(), close: vi.fn(), skipVersion: vi.fn()}));
vi.mock('$lib/features/update-check/updateCheckStore.svelte', () => ({updateAvailable: updateAvailableMock}));

const notifyMock = vi.hoisted(() => vi.fn());
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: notifyMock}));

// Keep the real i18n initialization, but expose keys/parameters as test-owned
// tokens. Toast assertions pin localization calls, not any language's prose.
const translateMock = vi.hoisted(() => vi.fn());
vi.mock('$lib/i18n', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/i18n')>();
    const {readable} = await import('svelte/store');
    return {...actual, _: readable(translateMock)};
});

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {tick} from 'svelte';
import ChangelogModal from './ChangelogModal.svelte';
import {CHANGELOG_REMOTE_URL} from '$lib/features/changelog/changelog';
import {zodiosApi} from '$lib/api';
import type {UpdateCheckResult} from '$lib/features/update-check/updateCheck';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const api = zodiosApi as any;
const SEARCH = 'search_users_endpoint_api_v1_users_search_get';
const GET_INFO = 'get_system_info_api_v1_system_info_get';

/** The release the probe reports when "newer" is the programmed answer. */
const RELEASE = {version: '1.2.4', tag: 'v1.2.4', url: 'https://example.com/release-1.2.4', name: 'Test release'};

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((resolvePromise, rejectPromise) => {
        resolve = resolvePromise;
        reject = rejectPromise;
    });
    return {promise, resolve, reject};
}

function chapterExpanded(i: number): string | null {
    return screen.queryByTestId(`changelog-chapter-toggle-${i}`)?.getAttribute('aria-expanded') ?? null;
}

function sectionExpanded(ci: number, si: number): string | null {
    return screen.queryByTestId(`changelog-section-toggle-${ci}-${si}`)?.getAttribute('aria-expanded') ?? null;
}

function subsectionExpanded(ci: number, si: number, ssi: number): string | null {
    return screen.queryByTestId(`changelog-subsection-toggle-${ci}-${si}-${ssi}`)?.getAttribute('aria-expanded') ?? null;
}

/** Type into the search box; ends when the input carries the query. */
async function typeSearch(q: string) {
    const input = screen.getByTestId('changelog-search') as HTMLInputElement;
    await fireEvent.input(input, {target: {value: q}});
    await waitFor(() => expect(input).toHaveValue(q));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    api[GET_INFO].mockReset();
    api[GET_INFO].mockResolvedValue({app_version: '1.2.3'});
    api[SEARCH].mockReset();
    api[SEARCH].mockResolvedValue({items: []});
    checkForUpdatesMock.mockReset();
    updateAvailableMock.show.mockClear();
    notifyMock.mockClear();
    translateMock.mockReset();
    translateMock.mockImplementation((key: string, options?: {values?: {version?: string}}) => {
        const version = options?.values?.version;
        return version === undefined ? key : `${key}(${version})`;
    });
    authStore.set({user: null});
});

describe('ChangelogModal (F12)', () => {
    it('renders header controls, index, one panel per chapter, and the remote link when open', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});

        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        expect(screen.getByTestId('changelog-search')).toBeInTheDocument();
        expect(screen.getByTestId('changelog-expand-all')).toBeInTheDocument();
        expect(screen.getByTestId('changelog-collapse-all')).toBeInTheDocument();
        expect(screen.getByTestId('changelog-index-0')).toBeInTheDocument();
        expect(screen.getByTestId('changelog-index-1')).toBeInTheDocument();

        const remote = screen.getByTestId('changelog-remote-link');
        expect(remote).toHaveAttribute('href', CHANGELOG_REMOTE_URL);
        expect(remote).toHaveAttribute('target', '_blank');
    });

    it('opens with only the newest release unfolded; sections and subsections start folded', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        expect(chapterExpanded(0)).toBe('true');
        expect(chapterExpanded(1)).toBe('false');
        expect(screen.getByTestId('changelog-intro-0')).toBeInTheDocument();
        expect(screen.queryByTestId('changelog-section-1-0')).not.toBeInTheDocument();

        // Inside the open chapter: both named sections folded (bodies absent), so
        // the subsection toggle (rendered only inside an open section) is absent too.
        expect(sectionExpanded(0, 1)).toBe('false');
        expect(screen.queryByTestId('changelog-section-body-0-1')).not.toBeInTheDocument();
        expect(screen.queryByTestId('changelog-subsection-toggle-0-1-0')).not.toBeInTheDocument();
    });

    it('a #### subsection folds individually inside its open section', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        // Open the Fixed section (0:1) — its subsection appears, still folded.
        await fireEvent.click(screen.getByTestId('changelog-section-toggle-0-1'));
        await waitFor(() => expect(sectionExpanded(0, 1)).toBe('true'));
        expect(subsectionExpanded(0, 1, 0)).toBe('false');
        expect(screen.queryByTestId('changelog-subsection-body-0-1-0')).not.toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('changelog-subsection-toggle-0-1-0'));

        await waitFor(() => expect(subsectionExpanded(0, 1, 0)).toBe('true'));
        expect(screen.getByTestId('changelog-subsection-body-0-1-0').innerHTML).toContain('Bug detail text.');
    });

    it('expand-all opens every chapter, section and subsection; collapse-all closes all', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(screen.getByTestId('changelog-expand-all'));

        await waitFor(() => {
            expect(chapterExpanded(0)).toBe('true');
            expect(chapterExpanded(1)).toBe('true');
            expect(chapterExpanded(2)).toBe('true');
        });
        // Deepest fold on each chapter: 0:1:0 (#### inside Fixed), 1:0:0
        // (#### attached to the intro of 1.1.0) and 2:1:0 (#### inside the
        // v1.0.0 Security section) all open, bodies rendered.
        expect(sectionExpanded(0, 1)).toBe('true');
        expect(subsectionExpanded(0, 1, 0)).toBe('true');
        expect(subsectionExpanded(1, 0, 0)).toBe('true');
        expect(sectionExpanded(2, 1)).toBe('true');
        expect(subsectionExpanded(2, 1, 0)).toBe('true');
        expect(screen.getByTestId('changelog-subsection-body-0-1-0')).toBeInTheDocument();
        expect(screen.getByTestId('changelog-subsection-body-1-0-0')).toBeInTheDocument();
        expect(screen.getByTestId('changelog-subsection-body-2-1-0')).toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('changelog-collapse-all'));

        await waitFor(() => {
            expect(chapterExpanded(0)).toBe('false');
            expect(chapterExpanded(1)).toBe('false');
            expect(chapterExpanded(2)).toBe('false');
        });
        // No chapter content remains in the DOM.
        expect(screen.queryByTestId('changelog-intro-0')).not.toBeInTheDocument();
        expect(screen.queryByTestId('changelog-subsection-body-1-0-0')).not.toBeInTheDocument();
        expect(screen.queryByTestId('changelog-subsection-body-2-1-0')).not.toBeInTheDocument();
    });

    it('search force-opens the folded chapter and section that match (lowercase needle)', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());
        expect(chapterExpanded(1)).toBe('false');

        // "feature" appears only in chapter 1.1.0's Added section.
        await typeSearch('feature');

        await waitFor(() => expect(chapterExpanded(1)).toBe('true'));
        await waitFor(() => expect(sectionExpanded(1, 1)).toBe('true'));
        // Round-5 highlighting: the needle is wrapped in <mark>, so assert the
        // visible text (textContent strips the highlight tags).
        expect(screen.getByTestId('changelog-section-body-1-1').textContent).toContain('a feature');
    });

    it('search descends to #### depth: a needle unique to a subsection force-opens the whole branch', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());
        expect(chapterExpanded(1)).toBe('false');

        // "zebra" appears only inside the Notes subsection of 1.1.0's intro.
        await typeSearch('zebra');

        await waitFor(() => expect(chapterExpanded(1)).toBe('true'));
        await waitFor(() => expect(subsectionExpanded(1, 0, 0)).toBe('true'));
        // Same round-5 note: highlight wraps the needle in <mark>; textContent
        // asserts the visible sentence regardless of the wrapping.
        expect(screen.getByTestId('changelog-subsection-body-1-0-0').textContent).toContain('Zebra subsection note.');
    });

    it('clearing the search restores the manual fold state', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await typeSearch('feature');
        await waitFor(() => expect(chapterExpanded(1)).toBe('true'));

        await typeSearch('');

        // The force-open lifts; chapter 1 returns to its (untouched) folded state.
        await waitFor(() => expect(chapterExpanded(1)).toBe('false'));
    });

    // Regression guard for the round-4 bug the test batch caught: haystacks were
    // lowercased but the needle (`query`) was not, so an uppercase search matched
    // nothing. The modal now normalizes the needle once (`query.trim().toLowerCase()`).
    it('search is case-insensitive — an uppercase needle matches lowercase content', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());
        expect(chapterExpanded(1)).toBe('false');

        await typeSearch('FEATURE');

        await waitFor(() => expect(chapterExpanded(1)).toBe('true'));
        await waitFor(() => expect(sectionExpanded(1, 1)).toBe('true'));
    });

    it('renders nothing when closed', () => {
        render(ChangelogModal, {open: false, onClose: vi.fn()});

        expect(screen.queryByTestId('changelog-modal')).not.toBeInTheDocument();
    });
});

// =========================================================================
// Round 5 — clickable search hits (`changelog-search-results`)
// =========================================================================
//
// While a query is active, matching branches are already force-open, so the
// click's contribution cannot be read from the fold state DURING the search.
// What jumpToHit adds is the *manual* fold state: the clicked branch must
// remain open after the query is cleared, while a branch that merely matched
// (and was never clicked) folds back. Every click test below therefore ends
// on the post-clear state — that is the only reading that proves the click.
// Scrolling is asserted through a spy on the jsdom stub ($test/component).

describe('ChangelogModal — search hits (round 5)', () => {
    it('a needle matching a ### section title offers that section as a hit chip', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());
        // No query, no hits — the modal is provably up, so the row's absence is meaningful.
        expect(screen.queryByTestId('changelog-search-results')).not.toBeInTheDocument();

        // "security" matches ONLY the ### Security title of v1.0.0 — no body,
        // no subsection title, no other section title contains it.
        await typeSearch('security');

        await waitFor(() => expect(screen.getByTestId('changelog-search-results')).toBeInTheDocument());
        const chip = screen.getByTestId('changelog-hit-s-2-1');
        // The label is this fixture's own data: "Title — vX.Y.Z".
        expect(chip.textContent).toContain('Security');
        expect(chip.textContent).toContain('v1.0.0');
        // Exactly one title matched, so exactly one chip exists (the collection
        // is owned by this fixture; the cap is not what is under test here).
        expect(within(screen.getByTestId('changelog-search-results')).getAllByRole('button')).toHaveLength(1);
        expect(screen.queryByTestId('changelog-hit-sub-2-1-0')).not.toBeInTheDocument();
    });

    it('clicking a section hit unfolds that branch — and it stays open after the query is cleared', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());
        expect(chapterExpanded(1)).toBe('false');

        // "added" matches TWO ### titles: v1.2.0's (s-0-2) and v1.1.0's (s-1-1).
        await typeSearch('added');
        await waitFor(() => expect(screen.getByTestId('changelog-hit-s-1-1')).toBeInTheDocument());
        expect(screen.getByTestId('changelog-hit-s-0-2')).toBeInTheDocument();

        const scrollSpy = vi.spyOn(Element.prototype, 'scrollIntoView');
        await fireEvent.click(screen.getByTestId('changelog-hit-s-1-1'));

        // The click requested a scroll to the section toggle.
        await waitFor(() => expect(scrollSpy).toHaveBeenCalled());
        scrollSpy.mockRestore();

        // Clearing lifts the search force-open. The CLICKED branch (v1.1.0's
        // Added) survives on manual state; the matched-but-unclicked sibling
        // (v1.2.0's Added) folds back — that contrast is the proof.
        await typeSearch('');
        await waitFor(() => expect(chapterExpanded(1)).toBe('true'));
        expect(sectionExpanded(1, 1)).toBe('true');
        expect(sectionExpanded(0, 2)).toBe('false');
    });

    it('a needle matching only a #### subsection title opens all three levels on click', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());
        expect(chapterExpanded(2)).toBe('false');

        // "quokka" appears in one #### title (Quokka patch, v1.0.0 Security).
        // Bodies mention it too, but hits are built from TITLES only → 1 chip.
        await typeSearch('quokka');
        await waitFor(() => expect(screen.getByTestId('changelog-hit-sub-2-1-0')).toBeInTheDocument());
        expect(within(screen.getByTestId('changelog-search-results')).getAllByRole('button')).toHaveLength(1);

        const scrollSpy = vi.spyOn(Element.prototype, 'scrollIntoView');
        await fireEvent.click(screen.getByTestId('changelog-hit-sub-2-1-0'));
        await waitFor(() => expect(scrollSpy).toHaveBeenCalled());
        scrollSpy.mockRestore();

        await typeSearch('');

        // Chapter → section → subsection all held open by the click's manual state.
        await waitFor(() => expect(chapterExpanded(2)).toBe('true'));
        expect(sectionExpanded(2, 1)).toBe('true');
        expect(subsectionExpanded(2, 1, 0)).toBe('true');
        expect(screen.getByTestId('changelog-subsection-body-2-1-0').innerHTML).toContain('Quokka detail.');
    });

    it('a needle unique to a body (every title clean) still yields the chip, labeled with the title', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        // Section-body arm: "hardened" lives only in the Security bullet body —
        // no title contains it. The chip is still offered, labeled by the TITLE.
        await typeSearch('hardened');
        await waitFor(() => expect(screen.getByTestId('changelog-hit-s-2-1')).toBeInTheDocument());
        const chip = screen.getByTestId('changelog-hit-s-2-1');
        expect(chip.textContent).toContain('Security');
        expect(chip.textContent).toContain('v1.0.0');
        // One body matched, one chip: body hits do not multiply or leak upwards.
        expect(within(screen.getByTestId('changelog-search-results')).getAllByRole('button')).toHaveLength(1);

        // Subsection-body arm: "zebra" lives only in the Notes subsection body
        // (the title "Notes" does not contain it) — the sub chip appears.
        await typeSearch('zebra');
        await waitFor(() => expect(screen.getByTestId('changelog-hit-sub-1-0-0')).toBeInTheDocument());
        const subChip = screen.getByTestId('changelog-hit-sub-1-0-0');
        expect(subChip.textContent).toContain('Notes');
        expect(subChip.textContent).toContain('v1.1.0');
        // Exactly one chip again: a subsection body hit does not create a
        // section chip for the parent (section hits need the section's OWN
        // title or body to match).
        expect(within(screen.getByTestId('changelog-search-results')).getAllByRole('button')).toHaveLength(1);
    });

    it('the hit list disappears when the query is cleared', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await typeSearch('security');
        await waitFor(() => expect(screen.getByTestId('changelog-search-results')).toBeInTheDocument());

        await typeSearch('');

        // Presence barrier above; now the whole results row must be gone.
        await waitFor(() => expect(screen.queryByTestId('changelog-search-results')).not.toBeInTheDocument());
    });

    it('caps the hit list at 8 chips, in fixture order', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        // "zed" matches the ten Zed NN section titles of v1.0.0 and nothing
        // else — the count IS the subject here, and the fixture is this test's.
        await typeSearch('zed');

        await waitFor(() => expect(screen.getByTestId('changelog-search-results')).toBeInTheDocument());
        expect(within(screen.getByTestId('changelog-search-results')).getAllByRole('button')).toHaveLength(8);
        // The first eight matches (s-2-2 … s-2-9) are offered; the ninth never renders.
        expect(screen.getByTestId('changelog-hit-s-2-2')).toBeInTheDocument();
        expect(screen.getByTestId('changelog-hit-s-2-9')).toBeInTheDocument();
        expect(screen.queryByTestId('changelog-hit-s-2-10')).not.toBeInTheDocument();
    });
});

// =========================================================================
// Round 5 — manual update check in the modal header (`changelog-check-update`)
// =========================================================================
//
// The button runs the same `checkForUpdates()` contract as the login flow
// (mocked here — jsdom never reaches GitHub) and reports the result through
// notify. There is no persistent result panel. A newer release still opens the
// F14 UpdateAvailableModal for admins (`updateAvailable.show`) or the
// `ask-admin-modal` listing administrators fetched from the users search.
// Every test ends on the state the click produced — never on a timer.

describe('ChangelogModal — manual update check (round 5)', () => {
    const checkBtn = () => screen.getByTestId('changelog-check-update') as HTMLButtonElement;

    function expectNoResultPanel() {
        // A missing modal must not satisfy the negative result assertions.
        expect(screen.getByTestId('changelog-modal')).toBeInTheDocument();
        expect(screen.getByTestId('changelog-search')).toBeInTheDocument();
        expect(screen.queryByTestId('changelog-update-result')).not.toBeInTheDocument();
        expect(screen.queryByTestId('changelog-remote-version')).not.toBeInTheDocument();
    }

    function expectChecked(result: UpdateCheckResult, toast?: {variant: 'success' | 'warning' | 'error'; message: string}, currentVersion = '1.2.3') {
        expect(notifyMock).toHaveBeenCalledWith({
            name: 'app.update.checked',
            detail: {
                status: result.status,
                source: result.source,
                checkedAt: result.checkedAt,
                currentVersion,
                reportedVersion: '9.9.9',
                remoteVersion: result.latest?.version ?? null,
                remoteTag: result.latest?.tag ?? null,
                reason: result.reason,
            },
            toast,
        });
    }

    it('probes with the backend app version and reports the metadata without a result panel or toast', async () => {
        authStore.set({user: {id: 1, username: 'root', is_superuser: true}});
        const result: UpdateCheckResult = {
            status: 'update-available',
            latest: RELEASE,
            source: 'network',
            checkedAt: 1_700_000_000_000,
        };
        checkForUpdatesMock.mockResolvedValue(result);
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());
        expectNoResultPanel();

        await fireEvent.click(checkBtn());

        await waitFor(() => expect(updateAvailableMock.show).toHaveBeenCalledWith(RELEASE));
        expect(api[GET_INFO]).toHaveBeenCalledTimes(1);
        expect(checkForUpdatesMock).toHaveBeenCalledTimes(1);
        expect(checkForUpdatesMock).toHaveBeenCalledWith('1.2.3', {force: true, ignoreDismissed: true});
        expect(notifyMock).toHaveBeenCalledTimes(1);
        expectChecked(result);
        expectNoResultPanel();
    });

    it.each([
        {tag: 'v1.2.3', source: 'network'},
        {tag: 'V1.2.3', source: 'network'},
        {tag: undefined, source: 'cache'},
    ] as const)('reports up-to-date as a two-line success toast, preserving tag $tag from $source', async ({tag, source}) => {
        const result: UpdateCheckResult = {
            status: 'up-to-date',
            latest: {version: '1.2.3', ...(tag === undefined ? {} : {tag}), url: 'https://example.com/release-1.2.3', name: 'Current release'},
            source,
            checkedAt: 1_700_000_000_001,
        };
        checkForUpdatesMock.mockResolvedValue(result);
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        await waitFor(() => expect(notifyMock).toHaveBeenCalledTimes(1));
        expectChecked(result, {
            variant: 'success',
            message: `changelog.upToDate\nchangelog.detectedRemoteVersion(${tag ?? '1.2.3'})`,
        });
        expect(translateMock).toHaveBeenCalledWith('changelog.upToDate');
        expect(translateMock).toHaveBeenCalledWith('changelog.detectedRemoteVersion', {values: {version: tag ?? '1.2.3'}});
        expect(checkForUpdatesMock).toHaveBeenCalledTimes(1);
        expect(checkForUpdatesMock).toHaveBeenCalledWith('1.2.3', {force: true, ignoreDismissed: true});
        expect(checkBtn()).toBeEnabled();
        expectNoResultPanel();
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
        expect(api[SEARCH]).not.toHaveBeenCalled();
        expect(screen.queryByTestId('ask-admin-modal')).not.toBeInTheDocument();
    });

    it('escapes both localized toast lines once while retaining raw remote metadata in the event', async () => {
        // Synthetic formatter output, not catalogue prose. Both lines contain
        // HTML-sensitive characters so escaping only the remote tag cannot pass.
        translateMock.mockImplementation((key: string, options?: {values?: {version?: string}}) => {
            if (key === 'changelog.upToDate') return `${key}<&>"'`;
            if (key === 'changelog.detectedRemoteVersion') return `${key}<&>"'(${options?.values?.version})`;
            return key;
        });
        const tag = `v1.2.3<&>"'`;
        const result: UpdateCheckResult = {
            status: 'up-to-date',
            latest: {version: '1.2.3', tag, url: RELEASE.url, name: RELEASE.name},
            source: 'network',
            checkedAt: 1_700_000_000_001,
        };
        checkForUpdatesMock.mockResolvedValue(result);
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        await waitFor(() => expect(notifyMock).toHaveBeenCalledTimes(1));
        expectChecked(result, {
            variant: 'success',
            message: 'changelog.upToDate&lt;&amp;&gt;&quot;&#39;\nchangelog.detectedRemoteVersion&lt;&amp;&gt;&quot;&#39;(v1.2.3&lt;&amp;&gt;&quot;&#39;)',
        });
        expect(translateMock).toHaveBeenCalledWith('changelog.detectedRemoteVersion', {values: {version: tag}});
        expectNoResultPanel();
    });

    it.each(['null', 'missing'] as const)('does not invent a remote version when latest is %s', async (latestShape) => {
        const result: UpdateCheckResult = {
            status: 'up-to-date',
            latest: null,
            source: 'none',
            checkedAt: null,
        };
        // A missing latest is outside the typed producer contract, but the
        // notification boundary must still not substitute either local version.
        const withoutLatest = {status: result.status, source: result.source, checkedAt: result.checkedAt};
        checkForUpdatesMock.mockResolvedValue(latestShape === 'null' ? result : withoutLatest);
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        await waitFor(() => expect(notifyMock).toHaveBeenCalledTimes(1));
        expectChecked(result, {variant: 'success', message: 'changelog.upToDate'});
        expect(translateMock).not.toHaveBeenCalledWith('changelog.detectedRemoteVersion', expect.anything());
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
        expect(api[SEARCH]).not.toHaveBeenCalled();
        expectNoResultPanel();
    });

    it('admin + newer release delegates to updateAvailable.show, with no banner and the backend version', async () => {
        authStore.set({user: {id: 1, username: 'root', is_superuser: true}});
        checkForUpdatesMock.mockResolvedValue({
            status: 'update-available',
            latest: RELEASE,
            source: 'network',
            checkedAt: 1_700_000_000_002,
        });
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        await waitFor(() => expect(updateAvailableMock.show).toHaveBeenCalledWith(RELEASE));
        expect(notifyMock).toHaveBeenCalledWith(
            expect.objectContaining({
                name: 'app.update.checked',
                detail: expect.objectContaining({
                    status: 'update-available',
                    currentVersion: '1.2.3',
                    reportedVersion: '9.9.9',
                }),
            }),
        );
        expect(notifyMock).toHaveBeenCalledTimes(1);
        expect(notifyMock).toHaveBeenCalledWith(expect.objectContaining({toast: undefined}));
        expect(updateAvailableMock.show).toHaveBeenCalledTimes(1);
        expectNoResultPanel();
        expect(screen.queryByTestId('ask-admin-modal')).not.toBeInTheDocument();
        expect(api[SEARCH]).not.toHaveBeenCalled();
    });

    it('non-admin + newer release → the ask-admin modal lists the admins from the users search', async () => {
        authStore.set({user: {id: 5, username: 'carol', is_superuser: false}});
        const result: UpdateCheckResult = {
            status: 'update-available',
            latest: RELEASE,
            source: 'network',
            checkedAt: 1_700_000_000_003,
        };
        checkForUpdatesMock.mockResolvedValue(result);
        api[SEARCH].mockResolvedValue({items: [{username: 'rooty'}, {username: 'boss'}]});
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        await waitFor(() => expect(screen.getByTestId('ask-admin-modal')).toBeInTheDocument());
        expect(api[SEARCH]).toHaveBeenCalledWith({queries: {q: '', admins: true}});
        const rows = screen.getAllByTestId('ask-admin-row').map((r) => r.textContent);
        expect(rows.join(' ')).toContain('rooty');
        expect(rows.join(' ')).toContain('boss');
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
        expect(notifyMock).toHaveBeenCalledTimes(1);
        expectChecked(result);
        expectNoResultPanel();
    });

    it.each([
        {status: 'image-pending', latest: RELEASE, reason: undefined, variant: 'warning', key: 'changelog.imagePending'},
        {status: 'no-release', latest: null, reason: undefined, variant: 'warning', key: 'changelog.noStableRelease'},
        {status: 'error', latest: null, reason: 'release-request-failed', variant: 'error', key: 'changelog.checkFailed'},
        {status: 'error', latest: null, reason: 'invalid-release', variant: 'error', key: 'changelog.checkFailed'},
        {status: 'error', latest: RELEASE, reason: 'image-auth-request-failed', variant: 'error', key: 'changelog.imageCheckFailed'},
        {status: 'error', latest: RELEASE, reason: 'image-request-failed', variant: 'error', key: 'changelog.imageCheckFailed'},
    ] as const)('reports $status / $reason through a $variant toast without offering an update', async ({status, latest, reason, variant, key}) => {
        authStore.set({user: {id: 1, username: 'root', is_superuser: true}});
        const result: UpdateCheckResult = {
            status,
            latest,
            reason,
            source: 'network',
            checkedAt: 1_700_000_000_004,
        };
        checkForUpdatesMock.mockResolvedValue(result);
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        await waitFor(() => expect(notifyMock).toHaveBeenCalledTimes(1));
        expectChecked(result, {variant, message: key});
        expect(translateMock).toHaveBeenCalledWith(key);
        expect(translateMock).not.toHaveBeenCalledWith('changelog.detectedRemoteVersion', expect.anything());
        expect(checkBtn()).toBeEnabled();
        expectNoResultPanel();
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
        expect(api[SEARCH]).not.toHaveBeenCalled();
        expect(screen.queryByTestId('ask-admin-modal')).not.toBeInTheDocument();
    });

    it.each(['system-info', 'probe'] as const)('reports a rejected %s as an error without fabricating remote metadata', async (stage) => {
        if (stage === 'system-info') api[GET_INFO].mockRejectedValue(new Error('system-info fixture failure'));
        else checkForUpdatesMock.mockRejectedValue(new Error('probe fixture failure'));
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        await waitFor(() => expect(notifyMock).toHaveBeenCalledTimes(1));
        expectChecked({status: 'error', latest: null, source: 'none', checkedAt: null, reason: 'check-failed'}, {variant: 'error', message: 'changelog.checkFailed'}, stage === 'system-info' ? '' : '1.2.3');
        if (stage === 'system-info') {
            expect(checkForUpdatesMock).not.toHaveBeenCalled();
        } else {
            expect(checkForUpdatesMock).toHaveBeenCalledTimes(1);
            expect(checkForUpdatesMock).toHaveBeenCalledWith('1.2.3', {force: true, ignoreDismissed: true});
        }
        expect(checkBtn()).toBeEnabled();
        expectNoResultPanel();
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
        expect(api[SEARCH]).not.toHaveBeenCalled();
    });

    it('reports admin lookup failure separately without rewriting the successful update check', async () => {
        authStore.set({user: {id: 5, username: 'carol', is_superuser: false}});
        const result: UpdateCheckResult = {
            status: 'update-available',
            latest: RELEASE,
            source: 'network',
            checkedAt: 1_700_000_000_005,
        };
        checkForUpdatesMock.mockResolvedValue(result);
        api[SEARCH].mockRejectedValue(new Error('admin lookup fixture failure'));
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        await waitFor(() => expect(notifyMock).toHaveBeenCalledTimes(2));
        expectChecked(result);
        expect(notifyMock).toHaveBeenLastCalledWith({
            name: 'app.update.admin-lookup-failed',
            toast: {variant: 'error', message: 'changelog.adminLookupFailed'},
        });
        expect(api[SEARCH]).toHaveBeenCalledWith({queries: {q: '', admins: true}});
        expect(checkBtn()).toBeEnabled();
        expectNoResultPanel();
        expect(screen.queryByTestId('ask-admin-modal')).not.toBeInTheDocument();
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
    });

    it('blocks duplicate in-flight checks and rereads the backend version on every forced retry', async () => {
        const pending = deferred<UpdateCheckResult>();
        const first: UpdateCheckResult = {
            status: 'up-to-date',
            latest: {version: '1.2.3', tag: 'v1.2.3', url: RELEASE.url, name: RELEASE.name},
            source: 'network',
            checkedAt: 1_700_000_000_006,
        };
        const second: UpdateCheckResult = {...first, latest: RELEASE, checkedAt: 1_700_000_000_007};
        api[GET_INFO].mockResolvedValueOnce({app_version: '1.2.3'}).mockResolvedValueOnce({app_version: '1.2.4'});
        checkForUpdatesMock.mockReturnValueOnce(pending.promise).mockResolvedValueOnce(second);
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());
        await waitFor(() => expect(checkForUpdatesMock).toHaveBeenCalledTimes(1));
        expect(checkBtn()).toBeDisabled();
        expect(notifyMock).not.toHaveBeenCalled();
        expectNoResultPanel();
        await fireEvent.click(checkBtn());
        expect(api[GET_INFO]).toHaveBeenCalledTimes(1);
        expect(checkForUpdatesMock).toHaveBeenCalledTimes(1);

        pending.resolve(first);
        await waitFor(() => expect(checkBtn()).toBeEnabled());
        expectChecked(first, {variant: 'success', message: 'changelog.upToDate\nchangelog.detectedRemoteVersion(v1.2.3)'});
        await fireEvent.click(checkBtn());

        await waitFor(() => expect(notifyMock).toHaveBeenCalledTimes(2));
        expect(api[GET_INFO]).toHaveBeenCalledTimes(2);
        expect(checkForUpdatesMock).toHaveBeenNthCalledWith(1, '1.2.3', {force: true, ignoreDismissed: true});
        expect(checkForUpdatesMock).toHaveBeenNthCalledWith(2, '1.2.4', {force: true, ignoreDismissed: true});
        expectChecked(second, {variant: 'success', message: 'changelog.upToDate\nchangelog.detectedRemoteVersion(v1.2.4)'}, '1.2.4');
        expect(checkBtn()).toBeEnabled();
        expectNoResultPanel();
    });

    it('a late response is ignored after the modal closes and reopens', async () => {
        authStore.set({user: {id: 1, username: 'root', is_superuser: true}});
        const pending = deferred<UpdateCheckResult>();
        checkForUpdatesMock.mockReturnValue(pending.promise);

        const view = render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());
        await waitFor(() => expect(checkForUpdatesMock).toHaveBeenCalledTimes(1));

        await view.rerender({open: false, onClose: vi.fn(), currentVersion: '9.9.9'});
        pending.resolve({
            status: 'update-available',
            latest: RELEASE,
            source: 'network',
            checkedAt: 1_700_000_000_004,
        });
        await pending.promise;
        await tick();
        await view.rerender({open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        expect(updateAvailableMock.show).not.toHaveBeenCalled();
        expect(notifyMock).not.toHaveBeenCalled();
        expect(api[SEARCH]).not.toHaveBeenCalled();
        expectNoResultPanel();
        expect(checkBtn()).toBeEnabled();
    });

    it.each(['resolve', 'reject'] as const)('ignores an old probe that settles via %s after a reopened modal completes a fresh check', async (settlement) => {
        authStore.set({user: {id: 1, username: 'root', is_superuser: true}});
        const stale = deferred<UpdateCheckResult>();
        const fresh: UpdateCheckResult = {status: 'no-release', latest: null, source: 'network', checkedAt: 1_700_000_000_009};
        checkForUpdatesMock.mockReturnValueOnce(stale.promise).mockResolvedValueOnce(fresh);
        const view = render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());
        await waitFor(() => expect(checkForUpdatesMock).toHaveBeenCalledTimes(1));
        await view.rerender({open: false, onClose: vi.fn(), currentVersion: '9.9.9'});
        await view.rerender({open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(checkBtn()).toBeEnabled());
        await fireEvent.click(checkBtn());
        await waitFor(() => expect(notifyMock).toHaveBeenCalledTimes(1));
        expectChecked(fresh, {variant: 'warning', message: 'changelog.noStableRelease'});

        // open is true again: only the generation guard can reject this result.
        if (settlement === 'resolve') stale.resolve({status: 'update-available', latest: RELEASE, source: 'network', checkedAt: 1_700_000_000_008});
        else stale.reject(new Error('stale probe fixture failure'));
        await stale.promise.catch(() => undefined);
        await tick();

        expect(notifyMock).toHaveBeenCalledTimes(1);
        expectChecked(fresh, {variant: 'warning', message: 'changelog.noStableRelease'});
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
        expect(api[SEARCH]).not.toHaveBeenCalled();
        expect(checkBtn()).toBeEnabled();
        expectNoResultPanel();
    });

    it('does not start a probe when an obsolete backend-version lookup completes after reopening', async () => {
        const pending = deferred<{app_version: string}>();
        api[GET_INFO].mockReturnValueOnce(pending.promise);
        const view = render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());
        await waitFor(() => expect(api[GET_INFO]).toHaveBeenCalledTimes(1));
        expect(checkBtn()).toBeDisabled();
        await view.rerender({open: false, onClose: vi.fn(), currentVersion: '9.9.9'});
        await view.rerender({open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        pending.resolve({app_version: '1.2.3'});
        await pending.promise;
        await tick();

        expect(checkForUpdatesMock).not.toHaveBeenCalled();
        expect(notifyMock).not.toHaveBeenCalled();
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
        expect(checkBtn()).toBeEnabled();
        expectNoResultPanel();
    });

    it('does not reopen the ask-admin modal when an obsolete admin lookup completes', async () => {
        authStore.set({user: {id: 5, username: 'carol', is_superuser: false}});
        const pending = deferred<{items: Array<{username: string}>}>();
        const result: UpdateCheckResult = {status: 'update-available', latest: RELEASE, source: 'network', checkedAt: 1_700_000_000_010};
        checkForUpdatesMock.mockResolvedValue(result);
        api[SEARCH].mockReturnValueOnce(pending.promise);
        const view = render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());
        await waitFor(() => expect(api[SEARCH]).toHaveBeenCalledWith({queries: {q: '', admins: true}}));
        expectChecked(result);
        await view.rerender({open: false, onClose: vi.fn(), currentVersion: '9.9.9'});
        await view.rerender({open: true, onClose: vi.fn(), currentVersion: '9.9.9'});
        pending.resolve({items: [{username: 'late-admin'}]});
        await pending.promise;
        await tick();

        expect(notifyMock).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('ask-admin-modal')).not.toBeInTheDocument();
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
        expect(checkBtn()).toBeEnabled();
        expectNoResultPanel();
    });
});
