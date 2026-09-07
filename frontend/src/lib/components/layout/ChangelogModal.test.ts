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
 *    `checkForNewerRelease()` the login flow uses, with the outcome rendered as
 *    `changelog-up-to-date` (none), delegated to `updateAvailable.show` (admin
 *    + newer) or shown as the `changelog-ask-admin` banner with the admin list
 *    fetched from the users search (non-admin + newer).
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
 * admin usernames asserted in the banner are this test's own fixture data.
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

// The update probe (round 5): the modal must use THE SAME checkForNewerRelease
// as the login flow — so it is mocked here, and every test programs its answer.
const checkForNewerReleaseMock = vi.hoisted(() => vi.fn());
vi.mock('$lib/features/update-check/updateCheck', () => ({
    checkForNewerRelease: checkForNewerReleaseMock,
}));

// The F14 modal takeover: admin + newer delegates to updateAvailable.show.
const updateAvailableMock = vi.hoisted(() => ({show: vi.fn(), close: vi.fn(), skipVersion: vi.fn()}));
vi.mock('$lib/features/update-check/updateCheckStore.svelte', () => ({updateAvailable: updateAvailableMock}));

// Round 6: "up to date" is a toast, not a banner — toasts is mocked so the
// toast content and the no-banner invariant are both observable.
const toastsMock = vi.hoisted(() => ({success: vi.fn(), error: vi.fn(), warning: vi.fn()}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({toasts: toastsMock}));

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import ChangelogModal from './ChangelogModal.svelte';
import {CHANGELOG_REMOTE_URL} from '$lib/features/changelog/changelog';
import {zodiosApi} from '$lib/api';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const api = zodiosApi as any;
const SEARCH = 'search_users_endpoint_api_v1_users_search_get';

/** The release the probe reports when "newer" is the programmed answer. */
const RELEASE = {version: '9.9.9', url: 'https://example.com/release-9.9.9', name: 'Test release'};

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
    api[SEARCH].mockReset();
    api[SEARCH].mockResolvedValue({items: []});
    checkForNewerReleaseMock.mockReset();
    updateAvailableMock.show.mockClear();
    toastsMock.success.mockClear();
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
// The button runs the same `checkForNewerRelease()` as the login flow (mocked
// here — jsdom never reaches GitHub) and renders one of three outcomes:
// `changelog-up-to-date`, a delegation to the F14 UpdateAvailableModal for
// admins (`updateAvailable.show`), or the `changelog-ask-admin` banner listing
// the administrators fetched from the users search. Every test ends on the
// state the click produced — never on a timer.

describe('ChangelogModal — manual update check (round 5)', () => {
    const checkBtn = () => screen.getByTestId('changelog-check-update') as HTMLButtonElement;

    it('the header offers the check, and clicking it probes with the running version', async () => {
        checkForNewerReleaseMock.mockResolvedValue(null);
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '1.2.3'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        expect(checkBtn()).toBeEnabled();
        await fireEvent.click(checkBtn());

        await waitFor(() => expect(checkForNewerReleaseMock).toHaveBeenCalledWith('1.2.3'));
        // The probe answered: the button is usable again (not stuck in 'checking').
        await waitFor(() => expect(checkBtn()).toBeEnabled());
    });

    it('no newer release → the up-to-date line, and nothing else is touched', async () => {
        checkForNewerReleaseMock.mockResolvedValue(null);
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '1.2.3'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        await waitFor(() => expect(toastsMock.success).toHaveBeenCalled());
        expect(screen.queryByTestId('changelog-ask-admin')).not.toBeInTheDocument();
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
        // Up-to-date is decided before any admin lookup — no users search fires.
        expect(api[SEARCH]).not.toHaveBeenCalled();
    });

    it('admin + newer release → delegates to updateAvailable.show, with no banner', async () => {
        authStore.set({user: {id: 1, username: 'root', is_superuser: true}});
        checkForNewerReleaseMock.mockResolvedValue(RELEASE);
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '1.2.3'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        // The F14 modal takes over: the release is handed over verbatim.
        await waitFor(() => expect(updateAvailableMock.show).toHaveBeenCalledWith(RELEASE));
        expect(screen.queryByTestId('changelog-ask-admin')).not.toBeInTheDocument();
        // An admin needs no admin list — the search endpoint is never hit.
        expect(api[SEARCH]).not.toHaveBeenCalled();
    });

    it('non-admin + newer release → the ask-admin modal lists the admins from the users search', async () => {
        authStore.set({user: {id: 5, username: 'carol', is_superuser: false}});
        checkForNewerReleaseMock.mockResolvedValue(RELEASE);
        api[SEARCH].mockResolvedValue({items: [{username: 'rooty'}, {username: 'boss'}]});
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '1.2.3'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        // Round 7: the ask-admin hint is its own modal, not a banner row.
        await waitFor(() => expect(screen.getByTestId('ask-admin-modal')).toBeInTheDocument());
        // The admin list comes from the dedicated query, not from a hardcode.
        expect(api[SEARCH]).toHaveBeenCalledWith({queries: {q: '', admins: true}});
        // One row per admin, in the search's order (this test's own data).
        const rows = screen.getAllByTestId('ask-admin-row').map((r) => r.textContent);
        expect(rows.join(' ')).toContain('rooty');
        expect(rows.join(' ')).toContain('boss');
        // The F14 modal is NOT triggered for non-admins.
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
        // The up-to-date toast is NOT shown on this path.
        expect(toastsMock.success).not.toHaveBeenCalled();
    });

    it('a second click while the probe is in flight is a no-op', async () => {
        let resolveProbe!: (v: null) => void;
        checkForNewerReleaseMock.mockImplementation(
            () =>
                new Promise<null>((res) => {
                    resolveProbe = res;
                }),
        );
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '1.2.3'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());
        // 'checking' is visible to the user as a disabled button.
        await waitFor(() => expect(checkBtn()).toBeDisabled());

        await fireEvent.click(checkBtn());
        expect(checkForNewerReleaseMock).toHaveBeenCalledTimes(1);

        // Settle the probe: the outcome renders and the button recovers.
        resolveProbe(null);
        await waitFor(() => expect(toastsMock.success).toHaveBeenCalled());
        await waitFor(() => expect(checkBtn()).toBeEnabled());
    });

    it('a failed probe returns to idle — nothing stuck, and the next click works', async () => {
        checkForNewerReleaseMock.mockRejectedValueOnce(new Error('NEEDLE-OFFLINE'));
        checkForNewerReleaseMock.mockResolvedValue(null);
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '1.2.3'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        // Back to idle: button usable again, no outcome bar, no delegation.
        await waitFor(() => expect(checkBtn()).toBeEnabled());
        expect(screen.queryByTestId('changelog-ask-admin')).not.toBeInTheDocument();
        expect(updateAvailableMock.show).not.toHaveBeenCalled();

        // Not stuck: a retry really probes again and can succeed.
        await fireEvent.click(checkBtn());
        await waitFor(() => expect(checkForNewerReleaseMock).toHaveBeenCalledTimes(2));
        await waitFor(() => expect(toastsMock.success).toHaveBeenCalled());
    });

    it('a failed admin search after a hit also returns to idle — the banner does not stay', async () => {
        authStore.set({user: {id: 5, username: 'carol', is_superuser: false}});
        checkForNewerReleaseMock.mockResolvedValue(RELEASE);
        api[SEARCH].mockRejectedValue(new Error('NEEDLE-SEARCH-DOWN'));
        render(ChangelogModal, {open: true, onClose: vi.fn(), currentVersion: '1.2.3'});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        // The ask-admin branch WAS entered (the search fired)...
        await waitFor(() => expect(api[SEARCH]).toHaveBeenCalledTimes(1));
        // ...and its failure drops the state back to idle: banner gone (the
        // enabled button is the positive barrier for this negative), no delegation.
        await waitFor(() => expect(checkBtn()).toBeEnabled());
        expect(screen.queryByTestId('changelog-ask-admin')).not.toBeInTheDocument();
        expect(updateAvailableMock.show).not.toHaveBeenCalled();
    });

    it('without a running version the probe is skipped and the answer is up-to-date', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});
        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        await fireEvent.click(checkBtn());

        await waitFor(() => expect(toastsMock.success).toHaveBeenCalled());
        expect(checkForNewerReleaseMock).not.toHaveBeenCalled();
    });
});
