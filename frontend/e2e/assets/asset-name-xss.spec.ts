/**
 * Asset name XSS — a stored asset name stays text in every view of the asset list
 * (workstream K, step 13, item 0).
 *
 * The Name column of the asset table built its cell as HTML with `${row.display_name}` interpolated
 * raw, and `DataTable` renders `html` cells with `{@html}`. The backend stores any string as a name
 * and assets are global, so a name written by one user ran as script in the browser of every user who
 * opened the asset list. The same cell draws the icon as `<img src="${icon_url}">`, where a quote in
 * the stored URL closes the attribute and opens one of its own.
 *
 * What this file proves, for each view, in a real browser:
 *   · the payload is shown as the characters it is made of — the text contains `<img src=x`;
 *   · it did not become markup: no `img[src="x"]`, no element carrying the payloads' `onerror`;
 *   · nothing ran: the counters the payloads would bump are still undefined once every image of
 *     the row or card has settled — loaded, or failed with its `error` event dispatched, which is
 *     the moment an injected `onerror` runs. That is the barrier, not a duration.
 *
 * The card view renders the name as Svelte text and binds the icon's `src` as a property: it is the
 * control, green before the fix and after it. Each view gets its own page, so a payload that fires
 * in the table cannot be counted against the cards.
 *
 * The data is this spec's own: two assets whose names carry a token unique to the test, created
 * through the API as the E2E user and deleted in `afterEach` whatever the outcome — a stored XSS left
 * behind would fire in every later test that opens the asset table in this lane.
 *
 * Companion: `src/htmlInterpolation.gate.test.ts`, the source gate for the same rule.
 *
 * Test IDs: AX-001..AX-002
 */

import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {API_BASE, goToAssetsPage} from './assets-helpers';

test.setTimeout(60_000);

/** Closes `src="…"` and opens an `onerror` of its own, if the URL is pasted into markup unescaped. */
const ICON_BREAKOUT = 'x" onerror="window.__k13XssIcon=1';

/** What the payloads write when their handler runs: undefined means nothing ran. */
type XssCounters = {__k13Xss?: number; __k13XssIcon?: number};

interface XssAssets {
    token: string;
    nameId: number;
    iconId: number;
}

/** The ids the current test created, recorded before any assertion can throw, so cleanup always has them. */
let created: number[] = [];

/**
 * Create the two hostile assets and prove the backend kept them verbatim: if it ever normalised the
 * name or refused the quote in the URL, the page could only show harmless values and every
 * assertion below would be green for a reason that has nothing to do with escaping.
 */
async function createXssAssets(page: Page): Promise<XssAssets> {
    const token = `k13xss-${uniqueSuffix()}`;
    const hostileName = `K13 XSS <img src=x onerror="window.__k13Xss=(window.__k13Xss||0)+1"> ${token}`;
    const iconName = `K13 XSS icon ${token}`;

    const res = await page.request.post(`${API_BASE}/assets`, {
        data: [
            {display_name: hostileName, currency: 'EUR', asset_type: 'STOCK'},
            {display_name: iconName, currency: 'EUR', asset_type: 'STOCK', icon_url: ICON_BREAKOUT},
        ],
    });
    const body = (await res.json().catch(() => null)) as {results?: Array<{asset_id: number | null; success: boolean; display_name: string; message: string}>} | null;
    const results = body?.results ?? [];
    created = results.filter((r) => r.success && r.asset_id != null).map((r) => r.asset_id as number);
    expect(res.status(), `asset create must answer 201: ${JSON.stringify(body)}`).toBe(201);

    const idOf = (name: string): number => {
        const result = results.find((r) => r.display_name === name);
        expect(result?.success, `asset "${name}" must be created: ${result?.message}`).toBe(true);
        return result?.asset_id as number;
    };
    const assets = {token, nameId: idOf(hostileName), iconId: idOf(iconName)};

    const read = await page.request.get(`${API_BASE}/assets?asset_ids=${assets.nameId}&asset_ids=${assets.iconId}`);
    expect(read.ok(), await read.text()).toBeTruthy();
    const stored = (await read.json()) as Array<{asset_id: number; display_name: string; icon_url?: string | null}>;
    expect(stored.find((a) => a.asset_id === assets.nameId)?.display_name, 'the backend must store the hostile name verbatim').toBe(hostileName);
    expect(stored.find((a) => a.asset_id === assets.iconId)?.icon_url, 'the backend must store the breakout icon URL verbatim').toBe(ICON_BREAKOUT);
    return assets;
}

/** Open the asset list filtered to this test's two assets, in the grid view that renders them safely. */
async function openFilteredList(page: Page, assets: XssAssets): Promise<void> {
    await goToAssetsPage(page);
    // Grid first: until the search is applied, the view shows every asset in the lane, and the grid
    // is the view that renders a hostile name as text whoever created it.
    await page.getByTestId('view-mode-grid').click();

    const search = page.getByTestId('assets-search-input');
    await search.fill(assets.token);
    await expect(search).toHaveValue(assets.token);

    await expect(page.getByTestId(`asset-card-${assets.nameId}`)).toBeVisible({timeout: 15_000});
    await expect(page.getByTestId(`asset-card-${assets.iconId}`)).toBeVisible({timeout: 15_000});
    // The token is unique to this test, so the filtered set is exactly the two assets it created:
    // once it holds nothing else, the search is applied, and so is every view built from it.
    await expect(page.locator('[data-testid^="asset-card-"][data-lifecycle]')).toHaveCount(2, {timeout: 15_000});
}

/**
 * Every image in `scope` has settled: its `load` or `error` event has been dispatched. The capture
 * listeners installed by `addInitScript` see the event before the element's own handlers, and this
 * poll reads their record in a later task, so once it holds an injected `onerror` has run — or never
 * will. Only then does "the counter is undefined" mean "nothing ran" rather than "not yet".
 */
async function imagesSettled(scope: Locator): Promise<void> {
    await expect
        .poll(
            () =>
                scope.evaluate((root) => {
                    const seen = (window as unknown as {__k13ImagesSettled?: WeakSet<Element>}).__k13ImagesSettled;
                    return !!seen && [...root.querySelectorAll('img')].every((img) => seen.has(img));
                }),
            {timeout: 10_000, message: 'every image of the row/card must load or fail before the counters are read'},
        )
        .toBe(true);
}

async function counters(page: Page): Promise<XssCounters> {
    return page.evaluate(() => {
        const w = window as unknown as XssCounters;
        return {__k13Xss: w.__k13Xss, __k13XssIcon: w.__k13XssIcon};
    });
}

test.describe('Asset list — a stored asset name stays text (K step 13, item 0)', () => {
    let assets: XssAssets;

    test.beforeEach(async ({page}) => {
        created = [];
        await page.addInitScript(() => {
            const seen = new WeakSet<Element>();
            (window as unknown as {__k13ImagesSettled: WeakSet<Element>}).__k13ImagesSettled = seen;
            const record = (event: Event) => {
                if (event.target instanceof HTMLImageElement) seen.add(event.target);
            };
            // `load` and `error` do not bubble, but every event crosses the document in the capture phase.
            document.addEventListener('load', record, true);
            document.addEventListener('error', record, true);
        });
        await login(page, TEST_USER);
        assets = await createXssAssets(page);
    });

    test.afterEach(async ({page}) => {
        const ids = created;
        created = [];
        if (ids.length === 0) return;
        const res = await page.request.delete(`${API_BASE}/assets?${ids.map((id) => `asset_ids=${id}`).join('&')}`);
        const body = (await res.json().catch(() => null)) as {success_count?: number} | null;
        // Loud on purpose: a hostile name left in the lane fires in every later asset-table test.
        expect(res.ok() && body?.success_count === ids.length, `cleanup must delete assets ${ids.join(', ')}: ${JSON.stringify(body)}`).toBe(true);
    });

    // -----------------------------------------------------------------------
    // AX-001 — the table: the view that rendered the name with {@html}
    // -----------------------------------------------------------------------
    test('AX-001: in the table view the name and the icon URL stay text and run nothing', async ({page}) => {
        await openFilteredList(page, assets);
        await page.getByTestId('view-mode-list').click();

        const tables = page.locator('[data-testid^="assets-table-panel-"]');
        const nameRow = tables.locator(`tr[data-row-id="${assets.nameId}"]`);
        const iconRow = tables.locator(`tr[data-row-id="${assets.iconId}"]`);
        // Presence barrier: the token sits in the same cell as both payloads, so once it is shown
        // the cell has been rendered and everything below is a statement about the rendered cell.
        await expect(nameRow).toContainText(assets.token, {timeout: 15_000});
        await expect(iconRow).toContainText(assets.token, {timeout: 15_000});

        await expect.soft(nameRow, 'the table must show the markup of the name as text').toContainText('<img src=x');
        await expect.soft(nameRow.locator('img[src="x"]'), 'the name must not become an <img> in the table').toHaveCount(0);
        await expect.soft(iconRow.locator('img[src="x"]'), 'the icon URL must not break out of src="…" in the table').toHaveCount(0);
        await expect.soft(page.getByTestId('assets-page').locator('[onerror*="__k13Xss"]'), 'no element may carry a handler written by the payloads').toHaveCount(0);

        await imagesSettled(nameRow);
        await imagesSettled(iconRow);
        const fired = await counters(page);
        expect.soft(fired.__k13Xss, 'the name payload ran as script in the table').toBeUndefined();
        expect.soft(fired.__k13XssIcon, 'the icon URL payload ran as script in the table').toBeUndefined();
    });

    // -----------------------------------------------------------------------
    // AX-002 — the cards: the control, rendered through Svelte text and bound attributes
    // -----------------------------------------------------------------------
    test('AX-002: in the card view the name and the icon URL stay text and run nothing', async ({page}) => {
        await openFilteredList(page, assets);

        const nameCard = page.getByTestId(`asset-card-${assets.nameId}`);
        const iconCard = page.getByTestId(`asset-card-${assets.iconId}`);
        await expect(nameCard).toContainText(assets.token);
        await expect(iconCard).toContainText(assets.token);

        await expect.soft(nameCard, 'the card must show the markup of the name as text').toContainText('<img src=x');
        await expect.soft(nameCard.locator('img[src="x"]'), 'the name must not become an <img> in the card').toHaveCount(0);
        await expect.soft(iconCard.locator('img[src="x"]'), 'the icon URL must not break out of src in the card').toHaveCount(0);
        await expect.soft(page.getByTestId('assets-page').locator('[onerror*="__k13Xss"]'), 'no element may carry a handler written by the payloads').toHaveCount(0);

        await imagesSettled(nameCard);
        await imagesSettled(iconCard);
        const fired = await counters(page);
        expect.soft(fired.__k13Xss, 'the name payload ran as script in the cards').toBeUndefined();
        expect.soft(fired.__k13XssIcon, 'the icon URL payload ran as script in the cards').toBeUndefined();
    });
});
