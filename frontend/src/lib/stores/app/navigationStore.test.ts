/**
 * navigationStore — the explicit back stack behind every detail page's ← button, and the replace
 * expectation that asset prev/next adds to it (workstream K, step 16 item 2), pinned red-first.
 *
 * Decision (developer, 06/10): prev/next on the asset detail page REPLACE the current history
 * entry, so "Back" returns to the list however many steps the user took. The browser half is
 * `goto(url, {replaceState: true})`. This store is the other half: on its own it cannot tell a goto
 * that replaces from one that pushes, so `expectReplaceNavigation(url)` tells it — the NEXT tracked
 * navigation of type link/goto/form whose pathname (the part before `?`) equals `url`'s pathname
 * replaces the top entry instead of being pushed. The expectation is consumed by the next tracked
 * navigation of any type, match or not; popstate, enter and `resetNavDepth()` clear it too.
 *
 * The stack is private, so every assertion reads it the way the app does: through `goBack()` and
 * the `goto` it issues. `backTrail()` presses ← until the fallback, which spells out the whole stack
 * below the current page.
 *
 * The first block characterizes today's behaviour: it is green before the change and must stay
 * green after it. The second pins the expectation: red until `expectReplaceNavigation` exists.
 *
 * Every test starts from a fresh module (`vi.resetModules()` + dynamic import): the stack and the
 * expectation are module state, and a characterization must not lean on the new reset semantics.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const {goto} = vi.hoisted(() => ({goto: vi.fn()}));
vi.mock('$app/navigation', () => ({goto}));

type NavigationStore = typeof import('./navigationStore');

/** Never tracked by any test: reaching it can only mean "nothing below the current page". */
const FALLBACK = '/fallback-never-tracked';
const LIST = '/assets?x=1';
const DETAIL_3 = '/assets/3?s=1';
const DETAIL_5 = '/assets/5?s=1';
const DETAIL_7 = '/assets/7?s=1';
const FX = '/fx/EURUSD';

let nav: NavigationStore;

beforeEach(async () => {
    vi.resetModules();
    goto.mockReset();
    nav = await import('./navigationStore');
});

/** Where one press of ← goes. Like the app, it pops the current page off the stack. */
function back(): string | undefined {
    goto.mockClear();
    nav.goBack(FALLBACK);
    return goto.mock.calls.at(-1)?.[0];
}

/** Every page ← walks to, nearest first, until it falls back. The top entry is the current page: popped, never visited. */
function backTrail(): string[] {
    const trail: string[] = [];
    for (let step = 0; step < 20; step++) {
        const target = back();
        if (target === FALLBACK) return trail;
        if (target === undefined) throw new Error('goBack() issued no goto at all');
        trail.push(target);
    }
    throw new Error(`goBack() never reached the fallback in 20 steps: ${trail.join(' ← ')}`);
}

describe('navigationStore — the back stack as it is today (characterization)', () => {
    it('falls back when nothing was tracked', () => {
        expect(back()).toBe(FALLBACK);
    });

    it('falls back from the first page: one entry has nothing below it', () => {
        nav.trackNavigation('enter', LIST);
        expect(back()).toBe(FALLBACK);
    });

    it.each(['link', 'goto', 'form'] as const)('pushes a %s navigation to another page', (type) => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation(type, DETAIL_3);
        nav.trackNavigation(type, FX);
        expect(backTrail()).toEqual([DETAIL_3, LIST]);
    });

    it('updates the top entry in place when only the query changes', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('goto', '/assets?x=2'); // a filter synced to the URL
        nav.trackNavigation('link', DETAIL_3);
        // ← returns to the list as last seen, and the list was one entry, not two.
        expect(backTrail()).toEqual(['/assets?x=2']);
    });

    it('pops the top entry on popstate', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('link', DETAIL_3);
        nav.trackNavigation('link', FX);
        nav.trackNavigation('popstate', DETAIL_3); // the browser's own Back, from FX
        expect(backTrail()).toEqual([LIST]);
    });

    it('re-anchors on the page popstate lands on when the pop empties the stack', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('popstate', DETAIL_3);
        nav.trackNavigation('link', FX);
        expect(backTrail()).toEqual([DETAIL_3]);
    });

    it('starts over on enter (a reload, a direct link)', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('link', DETAIL_3);
        nav.trackNavigation('enter', FX);
        nav.trackNavigation('link', DETAIL_5);
        expect(backTrail()).toEqual([FX]);
    });

    it('forgets everything on resetNavDepth() (a sidebar section button)', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('link', DETAIL_3);
        nav.resetNavDepth();
        expect(back()).toBe(FALLBACK);
    });

    it('ignores a navigation with no URL', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('link', DETAIL_3);
        nav.trackNavigation('link', undefined);
        expect(backTrail()).toEqual([LIST]);
    });

    it('forgets everything when another user signs in', async () => {
        // Same fresh registry as `nav`, so this is the instance the store registered its reset with.
        const session = await import('$lib/stores/app/clientSession');
        session.transitionClientSession('nav-user-a'); // first identity: resolves, resets nothing
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('link', DETAIL_3);
        session.transitionClientSession('nav-user-a'); // the same account again is not a transition
        expect(back()).toBe(LIST);

        nav.trackNavigation('link', DETAIL_5);
        session.transitionClientSession('nav-user-b');
        expect(back()).toBe(FALLBACK);
    });
});

describe('navigationStore — expectReplaceNavigation (asset prev/next)', () => {
    it('lets the expected navigation replace the current page, so ← returns to the list', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('goto', DETAIL_3);
        nav.expectReplaceNavigation(DETAIL_5);
        nav.trackNavigation('goto', DETAIL_5);
        // The list, not /assets/3: the asset the user stepped away from was replaced, not stacked.
        expect(backTrail()).toEqual([LIST]);
    });

    it('keeps ← on the list after several prev/next steps', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('goto', DETAIL_3);
        for (const step of [DETAIL_5, DETAIL_7, DETAIL_3]) {
            nav.expectReplaceNavigation(step);
            nav.trackNavigation('goto', step);
        }
        expect(backTrail()).toEqual([LIST]);
    });

    it.each(['link', 'goto', 'form'] as const)('is honoured by a %s navigation', (type) => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('link', DETAIL_3);
        nav.expectReplaceNavigation(DETAIL_5);
        nav.trackNavigation(type, DETAIL_5);
        expect(backTrail()).toEqual([LIST]);
    });

    it('matches on the pathname, and the entry keeps the URL actually visited', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('goto', DETAIL_3);
        nav.expectReplaceNavigation(DETAIL_5);
        nav.trackNavigation('goto', '/assets/5?s=2&tab=prices');
        nav.trackNavigation('link', FX);
        expect(backTrail()).toEqual(['/assets/5?s=2&tab=prices', LIST]);
    });

    it('lets a navigation elsewhere push as today, and is consumed by it', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('goto', DETAIL_3);
        nav.expectReplaceNavigation(DETAIL_5);
        nav.trackNavigation('link', FX); // not the expected page: pushed, and the expectation is gone
        nav.trackNavigation('goto', DETAIL_5); // so this one is pushed too
        expect(backTrail()).toEqual([FX, DETAIL_3, LIST]);
    });

    it('is consumed by the navigation it matched: a later visit to that page is pushed', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('goto', DETAIL_3);
        nav.expectReplaceNavigation(DETAIL_5);
        nav.trackNavigation('goto', DETAIL_5); // replaces DETAIL_3
        nav.trackNavigation('link', FX);
        nav.trackNavigation('link', DETAIL_5); // an ordinary visit
        expect(backTrail()).toEqual([FX, DETAIL_5, LIST]);
    });

    it('is cleared by popstate', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('goto', DETAIL_3);
        nav.expectReplaceNavigation(DETAIL_5);
        nav.trackNavigation('popstate', LIST); // the browser's Back wins: DETAIL_3 is popped
        nav.trackNavigation('goto', DETAIL_5); // an ordinary visit from the list: pushed
        expect(backTrail()).toEqual([LIST]);
    });

    it('is cleared by enter', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('goto', DETAIL_3);
        nav.expectReplaceNavigation(DETAIL_5);
        nav.trackNavigation('enter', DETAIL_3); // a reload
        nav.trackNavigation('goto', DETAIL_5);
        expect(backTrail()).toEqual([DETAIL_3]);
    });

    it('is cleared by resetNavDepth(): the next page is the floor of the new stack', () => {
        nav.trackNavigation('enter', LIST);
        nav.trackNavigation('goto', DETAIL_3);
        nav.expectReplaceNavigation(DETAIL_5);
        nav.resetNavDepth();
        nav.trackNavigation('goto', DETAIL_5);
        nav.trackNavigation('link', FX);
        expect(backTrail()).toEqual([DETAIL_5]);
    });
});
