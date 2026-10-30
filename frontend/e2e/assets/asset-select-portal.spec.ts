/**
 * SimpleSelect list above the DataTable's sticky header — E2E (lot H6-1)
 *
 * The Type cell of the asset Events editor is a `SimpleSelect` inside a `DataTable` row. The row
 * is `position: relative; z-index: 1` (`z-index: 10` while it has the focus) and the table's
 * header cells are `position: sticky; z-index: 15`. The list of a select is `position: fixed`,
 * but a fixed element is still painted in the stacking context of its ancestors, so when the list
 * opens upward — it does when the cell is low on the screen — and reaches the header, the header
 * is painted OVER the options. jsdom has no paint order; only a real browser can say what the user
 * sees. The fix moves the list to `<body>` (`use:portal`); `SimpleSelect.portal.test.ts` pins the
 * structure, this spec pins the effect.
 *
 * What is proved, on an asset and an event this test creates itself:
 * - the open list overlaps the table header (a premise, not an assumption: it is measured), and
 * - at the centre of every option the list shows, the topmost element is inside the list, and
 * - a real click on an option that was under the header chooses it (the editor becomes dirty).
 *
 * Data. One USD asset with its two closes and one manual DIVIDEND, both created through the API and
 * deleted afterwards (`deleteOwned`); nothing shared is read or written. The viewport is shortened
 * after the row is on screen so the cell sits near the bottom of it and the select opens upward.
 */
import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedAsset, deleteOwned, eventRow, openEventsEditor, seedEvents, type Owned} from './asset-events-owned';

/** What the browser says about one option of the open list. */
type OptionProbe = {id: string; selected: boolean; top: number; centerInList: boolean; overHeader: boolean; hitInList: boolean};

test.describe('SimpleSelect list above the DataTable header', () => {
    let owned: Owned = {assetIds: [], brokerIds: []};

    test.beforeEach(async ({page}) => {
        owned = {assetIds: [], brokerIds: []};
        await login(page, TEST_USER);
    });

    test.afterEach(async ({page}) => {
        await deleteOwned(page, owned);
    });

    test('the options of an open Type select are on top of the sticky header, and a click on one chooses it', async ({page}, testInfo) => {
        test.skip(testInfo.project.name !== 'desktop', 'Desktop only: the viewport is sized by the test to put the cell low on the screen');

        const asset = await createOwnedAsset(page, owned, {label: 'E2E select portal'});
        const [eventId] = await seedEvents(page, asset.id, [{date: daysAgoIso(20), type: 'DIVIDEND', amount: '0.50', notes: `e2e-select-portal-${uniqueSuffix()}`}]);
        const panel = await openEventsEditor(page, asset);
        const row = eventRow(panel, eventId);
        await expect(row, 'the event this test created must be listed').toBeVisible({timeout: 15_000});
        const typeSelect = row.getByRole('combobox');
        await expect(typeSelect).toBeVisible();

        // Put the cell low on the screen: scroll it to the middle, then cut the viewport 70 px under it.
        // `SimpleSelect` opens upward when less than 200 px is left below the trigger and there is more above.
        await typeSelect.scrollIntoViewIfNeeded();
        const placed = await typeSelect.boundingBox();
        if (!placed) throw new Error('The Type select of the event row has no box');
        await page.evaluate((dy) => window.scrollBy(0, dy), placed.y - 320);
        await expect.poll(async () => (await typeSelect.boundingBox())?.y ?? -1, {message: 'the cell did not settle'}).toBeGreaterThan(150);
        const settled = await typeSelect.boundingBox();
        if (!settled) throw new Error('The Type select of the event row has no box');
        await page.setViewportSize({width: 1280, height: Math.ceil(settled.y + settled.height + 70)});
        await expect(typeSelect, 'the cell must stay on screen after the viewport is cut').toBeInViewport();

        await typeSelect.click();
        await expect(typeSelect).toHaveAttribute('aria-expanded', 'true');
        const listboxId = await typeSelect.getAttribute('aria-controls');
        expect(listboxId, 'the type select names its listbox').toBeTruthy();
        const listbox = page.locator(`[id="${listboxId}"]`);
        await expect(listbox).toBeVisible();

        // What the browser paints: for each option, is the topmost element at its centre inside the list?
        const probes = await typeSelect.evaluate((trigger, id): OptionProbe[] => {
            const list = document.getElementById(id as string);
            if (!list) return [];
            const listRect = list.getBoundingClientRect();
            const header = trigger.closest('table')?.querySelector('thead');
            const headerCells = header ? [...header.querySelectorAll('th')].map((cell) => cell.getBoundingClientRect()) : [];
            return [...list.querySelectorAll<HTMLElement>('[role="option"]')].map((option) => {
                const rect = option.getBoundingClientRect();
                const cx = rect.left + rect.width / 2;
                const cy = rect.top + rect.height / 2;
                const hit = document.elementFromPoint(cx, cy);
                return {
                    id: option.id,
                    selected: option.getAttribute('aria-selected') === 'true',
                    top: rect.top,
                    centerInList: cx >= listRect.left && cx <= listRect.right && cy >= listRect.top && cy <= listRect.bottom,
                    overHeader: headerCells.some((cell) => cx >= cell.left && cx <= cell.right && cy >= cell.top && cy <= cell.bottom),
                    hitInList: !!hit && list.contains(hit),
                };
            });
        }, listboxId);

        const shown = probes.filter((probe) => probe.centerInList);
        expect(shown.length, 'the list shows its options').toBeGreaterThan(1);
        // Premise: the list really reaches the header. If it does not, a green below would prove nothing.
        const underHeader = shown.filter((probe) => probe.overHeader);
        expect(underHeader.length, 'premise: at least one option of the open list lies over the table header').toBeGreaterThan(0);
        const covered = shown.filter((probe) => !probe.hitInList).map((probe) => probe.id);
        expect(covered, 'options whose centre is painted under another element (the table header)').toEqual([]);

        // A real click on an option that lies over the header: Playwright refuses a target another element intercepts.
        const target = underHeader.filter((probe) => !probe.selected).sort((a, b) => a.top - b.top)[0];
        if (!target) throw new Error('Every option over the header is the selected one: nothing to choose');
        await page.locator(`[id="${target.id}"]`).click({timeout: 5_000});
        await expect(listbox).toBeHidden();
        await expect(typeSelect).toHaveAttribute('aria-expanded', 'false');
        // The choice reached the editor: its row is dirty, so Save is enabled.
        await expect(panel.getByTestId('asset-editor-save-btn')).toBeEnabled();
    });
});
