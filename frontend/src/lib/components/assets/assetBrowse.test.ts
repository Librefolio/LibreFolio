/**
 * assetBrowse — the order the asset detail page's `‹ n/N ›` buttons follow (workstream K, step 16
 * item 2), pinned red-first. A pure module, in memory only.
 *
 * Decisions (developer, 06/10):
 *   - the buttons follow "the list I left": its filters, its view (grid or table) and, in the table,
 *     each panel's column sort and column filters;
 *   - with no list to follow (direct link, Dashboard, Transactions, reload, or an asset missing from
 *     the published list) they follow ALL assets in the list page's default order;
 *   - at the edges a button is disabled, there is no wrap-around; under 2 assets they are hidden.
 *
 * What this file pins:
 *   - the published list: `null` until the list page publishes and after a reset; grid = the panels'
 *     ids concatenated in the published panel order; table = per panel, the table's order restricted
 *     to the panel's current ids (a row a column filter hid is NOT added back), else the panel's ids;
 *     a panel with no ids contributes nothing; everything handed in or out is a copy;
 *   - `resetAssetBrowse()`, also run as a client-session reset when another account signs in;
 *   - `defaultAssetBrowseOrder`: the list page's unfiltered default view — actives (plus the
 *     inactives when the open asset is inactive), in `orderAssetsByLifecycle` order, grouped by the
 *     list page's `assetScope` (own → others → analysis);
 *   - `browseNeighbours`: position, total and neighbours, `null` for an id the order lacks;
 *   - the copy guard: the module keeps a private copy of the list page's `assetScope` (a `.svelte`
 *     page cannot be imported), and the copy must stay identical to the original.
 *
 * Tests share one module instance and `beforeEach` resets it through its own `resetAssetBrowse()`
 * (pinned below). The two that need a pristine instance, the initial state and the client-session
 * reset, load a fresh one with `vi.resetModules()` + dynamic import.
 */
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {ASSET_BROWSE_PANEL_ORDER, browseNeighbours, clearAssetTableOrder, defaultAssetBrowseOrder, getAssetListOrder, publishAssetListOrder, publishAssetTableOrder, resetAssetBrowse} from './assetBrowse';

beforeEach(() => {
    resetAssetBrowse();
});

// =============================================================================
// The copy guard
// =============================================================================

const LIST_PAGE = 'src/routes/(app)/assets/+page.svelte';
const BROWSE_MODULE = 'src/lib/components/assets/assetBrowse.ts';
const ALIGN = `align \`${BROWSE_MODULE}\` with \`assetScope\` in \`${LIST_PAGE}\`: the asset detail's prev/next default order groups assets with it`;

/**
 * The whole `function assetScope(…) {…}` declaration of a source file, every whitespace run
 * collapsed to one space; `''` when there is none. Paths are relative to `frontend/`, where the
 * runner and `vitest run` start (as `moneyRenderSites.test.ts` reads them).
 *
 * The body is the first `{` met outside the parameter list: the braces before it belong to the
 * parameter's type (`a: {held_by_me?: boolean; …}`), which sits inside the parentheses.
 */
function assetScopeDeclaration(file: string): string {
    const source = readFileSync(resolve(process.cwd(), file), 'utf8');
    const start = source.indexOf('function assetScope(');
    if (start < 0) return '';
    let parens = 0;
    let braces = 0;
    let inBody = false;
    for (let i = start; i < source.length; i++) {
        const char = source[i];
        if (char === '(') parens++;
        else if (char === ')') parens--;
        else if (char === '{') {
            if (parens === 0 && braces === 0) inBody = true;
            braces++;
        } else if (char === '}') {
            braces--;
            if (inBody && braces === 0) return source.slice(start, i + 1).replace(/\s+/g, ' ');
        }
    }
    return '';
}

describe('assetBrowse — the private copy of assetScope', () => {
    it('stays identical to the list page original', () => {
        const original = assetScopeDeclaration(LIST_PAGE);
        const copy = assetScopeDeclaration(BROWSE_MODULE);

        // Positive control: a guard that finds nothing on either side would compare '' with ''.
        expect(original, `no \`function assetScope(\` declaration found in \`${LIST_PAGE}\`: the guard is reading the wrong file`).toContain("return 'analysis'");
        expect(copy, `no \`function assetScope(\` declaration found in \`${BROWSE_MODULE}\`: ${ALIGN}`).not.toBe('');
        expect(copy, ALIGN).toBe(original);
    });
});

// =============================================================================
// The order the list page publishes
// =============================================================================

describe('assetBrowse — the published list order', () => {
    it('is null before the list page publishes, even when a table already reported', async () => {
        vi.resetModules();
        const fresh = await import('./assetBrowse');
        expect(fresh.getAssetListOrder()).toBeNull();

        fresh.publishAssetTableOrder('own', [2, 1]);
        expect(fresh.getAssetListOrder()).toBeNull();
    });

    it('is null again after resetAssetBrowse(), and the table orders went with it', () => {
        publishAssetTableOrder('own', [2, 1]);
        publishAssetListOrder('list', [{id: 'own', ids: [1, 2]}]);
        expect(getAssetListOrder()).toEqual([2, 1]);

        resetAssetBrowse();
        expect(getAssetListOrder()).toBeNull();
        // The same panel published again comes back in its own order: no stale table order left.
        publishAssetListOrder('list', [{id: 'own', ids: [1, 2]}]);
        expect(getAssetListOrder()).toEqual([1, 2]);
    });

    it('names the panels in the list page order: own, others, analysis', () => {
        expect(ASSET_BROWSE_PANEL_ORDER).toEqual(['own', 'others', 'analysis']);
    });

    describe('grid view', () => {
        it('concatenates the panels in the order they were published', () => {
            publishAssetListOrder('grid', [
                {id: 'own', ids: [3, 1]},
                {id: 'others', ids: [7]},
                {id: 'analysis', ids: [5, 2]},
            ]);
            expect(getAssetListOrder()).toEqual([3, 1, 7, 5, 2]);

            // The published order, not a canonical one; and a new publication replaces the old.
            publishAssetListOrder('grid', [
                {id: 'analysis', ids: [5]},
                {id: 'own', ids: [3]},
            ]);
            expect(getAssetListOrder()).toEqual([5, 3]);
        });

        it('ignores the table orders, and table view uses them again', () => {
            publishAssetTableOrder('own', [1, 3]);
            const panels = [
                {id: 'own' as const, ids: [3, 1]},
                {id: 'others' as const, ids: [7]},
            ];

            publishAssetListOrder('grid', panels);
            expect(getAssetListOrder()).toEqual([3, 1, 7]);

            publishAssetListOrder('list', panels);
            expect(getAssetListOrder()).toEqual([1, 3, 7]);
        });
    });

    describe('table view', () => {
        it("follows each panel's table order, panel by panel", () => {
            publishAssetTableOrder('own', [3, 1, 2]);
            publishAssetTableOrder('analysis', [9, 8]);
            publishAssetListOrder('list', [
                {id: 'own', ids: [1, 2, 3]},
                {id: 'others', ids: [7, 6]},
                {id: 'analysis', ids: [8, 9]},
            ]);
            // own and analysis: their tables' order; others has no table order, so its panel order.
            expect(getAssetListOrder()).toEqual([3, 1, 2, 7, 6, 9, 8]);
        });

        it('does not add back a row a column filter hid, and drops an id the panel no longer holds', () => {
            // The own table shows 3 and 1 (a column filter hides 2), and still lists 99, gone from the panel.
            publishAssetTableOrder('own', [3, 99, 1]);
            publishAssetListOrder('list', [
                {id: 'own', ids: [1, 2, 3]},
                {id: 'others', ids: [7]},
            ]);
            expect(getAssetListOrder()).toEqual([3, 1, 7]);
        });

        it('uses a table order published after the list, the latest one winning', () => {
            publishAssetListOrder('list', [{id: 'own', ids: [1, 2, 3]}]);
            expect(getAssetListOrder()).toEqual([1, 2, 3]);

            publishAssetTableOrder('own', [2, 3, 1]); // the table reports after the page published
            expect(getAssetListOrder()).toEqual([2, 3, 1]);

            publishAssetTableOrder('own', [1, 3, 2]); // the user sorts by another column
            expect(getAssetListOrder()).toEqual([1, 3, 2]);
        });

        it('falls back to the panel order once its table order is cleared', () => {
            publishAssetTableOrder('own', [2, 1]);
            publishAssetListOrder('list', [
                {id: 'own', ids: [1, 2]},
                {id: 'others', ids: [7, 6]},
            ]);
            expect(getAssetListOrder()).toEqual([2, 1, 7, 6]);

            clearAssetTableOrder('own');
            expect(getAssetListOrder()).toEqual([1, 2, 7, 6]);
        });

        it('takes nothing from a panel with no ids, or not published at all, whatever its table said', () => {
            publishAssetTableOrder('others', [7, 6]);
            publishAssetTableOrder('analysis', [9]);
            publishAssetListOrder('list', [
                {id: 'own', ids: [1, 2]},
                {id: 'others', ids: []},
            ]);
            expect(getAssetListOrder()).toEqual([1, 2]);
        });
    });

    describe('copies', () => {
        it('is not affected by later changes to what it was handed', () => {
            const panels: {id: 'own' | 'others'; ids: number[]}[] = [{id: 'own', ids: [1, 2]}];
            const tableOrder = [2, 1];
            publishAssetTableOrder('own', tableOrder);
            publishAssetListOrder('list', panels);

            panels[0].ids.push(3);
            panels[0].ids.reverse();
            panels.push({id: 'others', ids: [7]});
            tableOrder.splice(0, tableOrder.length, 1, 2);
            expect(getAssetListOrder()).toEqual([2, 1]);

            panels[0].ids = [9];
            expect(getAssetListOrder()).toEqual([2, 1]);
        });

        it('hands out a fresh array each time', () => {
            publishAssetListOrder('grid', [{id: 'own', ids: [1, 2, 3]}]);
            const first = getAssetListOrder() ?? [];
            expect(first).toEqual([1, 2, 3]);

            first.reverse();
            first.push(99);
            const second = getAssetListOrder();
            expect(second).toEqual([1, 2, 3]);
            expect(second).not.toBe(first);
        });
    });

    it('is emptied when the account changes: it is a client-session reset', async () => {
        vi.resetModules();
        const browse = await import('./assetBrowse');
        // Same fresh registry: the session instance this fresh module registered its reset with.
        const session = await import('$lib/stores/app/clientSession');

        session.transitionClientSession('browse-user-a'); // first identity: resolves, resets nothing
        browse.publishAssetTableOrder('own', [2, 1]);
        browse.publishAssetListOrder('list', [{id: 'own', ids: [1, 2]}]);
        session.transitionClientSession('browse-user-a'); // the same account again is not a transition
        expect(browse.getAssetListOrder()).toEqual([2, 1]);

        session.transitionClientSession('browse-user-b');
        expect(browse.getAssetListOrder()).toBeNull();
        browse.publishAssetListOrder('list', [{id: 'own', ids: [1, 2]}]);
        expect(browse.getAssetListOrder(), 'the table orders must be emptied with the list').toEqual([1, 2]);

        session.transitionClientSession(null); // logout
        expect(browse.getAssetListOrder()).toBeNull();
    });
});

// =============================================================================
// The default order: no list to follow
// =============================================================================

/**
 * API-shaped assets, in API order. Their panel on the list page is `assetScope`, which reads what is
 * held now: own when `held_by_me`, else others when `held_by_others`, else analysis; a missing flag
 * reads as false.
 */
const ASSETS = [
    {id: 1, active: true, held_by_me: false, held_by_others: false}, // analysis
    {id: 2, active: false, held_by_me: true, held_by_others: false}, // own, inactive
    {id: 3, active: true, held_by_me: true, held_by_others: true}, // own, held by others too
    {id: 4, active: true, held_by_others: true}, // others: no held_by_me flag
    {id: 5, active: true}, // analysis: no flags at all
    {id: 6, active: false, held_by_me: false, held_by_others: true}, // others, inactive
    {id: 7, active: false}, // analysis, inactive
];

describe('assetBrowse — defaultAssetBrowseOrder (the list page unfiltered)', () => {
    it('follows the active assets only, by panel: own, others, analysis', () => {
        expect(defaultAssetBrowseOrder(ASSETS, 4)).toEqual([3, 4, 1, 5]);
    });

    it('adds the inactive assets when the open one is inactive, actives first within each panel', () => {
        // As with the list's "inactive" toggle on: 3 comes before 2 although the API lists 2 first.
        expect(defaultAssetBrowseOrder(ASSETS, 2)).toEqual([3, 2, 4, 6, 1, 5, 7]);
        expect(defaultAssetBrowseOrder(ASSETS, 7)).toEqual([3, 2, 4, 6, 1, 5, 7]);
    });

    it('follows the active assets only when the open asset is not among them', () => {
        expect(defaultAssetBrowseOrder(ASSETS, 99)).toEqual([3, 4, 1, 5]);
        expect(defaultAssetBrowseOrder([], 99)).toEqual([]);
    });

    it('groups by the list page assetScope: held by me wins over held by others, a missing flag reads as false', () => {
        const assets = [
            {id: 13, active: true, held_by_others: false}, // analysis, with no held_by_me at all
            {id: 12, active: true, held_by_me: false, held_by_others: true}, // others
            {id: 11, active: true, held_by_me: true}, // own, with no held_by_others at all
            {id: 14, active: true}, // analysis
            {id: 15, active: true, held_by_me: true, held_by_others: true}, // own: held by me wins
            {id: 16, active: true, held_by_me: false, held_by_others: false, tx_count_own: 2, tx_count: 5}, // analysis despite its trade counts: a position sold years ago is no longer yours, the panels read what is held now (decision of 24/09)
        ];
        // Within a panel, the input order is kept.
        expect(defaultAssetBrowseOrder(assets, 12)).toEqual([11, 15, 12, 13, 14, 16]);
    });
});

// =============================================================================
// Neighbours
// =============================================================================

describe('assetBrowse — browseNeighbours', () => {
    it('places an id with its neighbours', () => {
        expect(browseNeighbours([10, 20, 30], 20)).toEqual({index: 1, total: 3, previous: 10, next: 30});
    });

    it('has no previous at the first and no next at the last: no wrap-around', () => {
        expect(browseNeighbours([10, 20, 30], 10)).toEqual({index: 0, total: 3, previous: null, next: 20});
        expect(browseNeighbours([10, 20, 30], 30)).toEqual({index: 2, total: 3, previous: 20, next: null});
    });

    it('places a lone id with no neighbours at all', () => {
        expect(browseNeighbours([10], 10)).toEqual({index: 0, total: 1, previous: null, next: null});
    });

    it('is null for an id the order does not hold', () => {
        expect(browseNeighbours([10, 20, 30], 40)).toBeNull();
        expect(browseNeighbours([], 10)).toBeNull();
    });
});
