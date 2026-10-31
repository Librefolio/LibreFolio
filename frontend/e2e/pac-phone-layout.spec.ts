/**
 * PAC allocator on a phone — the Targets and Review steps fit the screen (Y-9).
 *
 * The tables of the planner declared widths that added up to more than a phone is wide (the Targets table asked for ~600 px,
 * the Review ones for more), so on a 375 px screen each of them scrolled sideways inside its card. On a phone the columns are
 * fluid down to a floor of their own (`minWidth`): the tables fit the card and nothing scrolls sideways, neither the table nor
 * the page. Measured, not looked at: `scrollWidth` against `clientWidth` of every table wrapper in the step, and of the page.
 *
 * The draft is the gallery's own (`galleryPac.ts`), built on the populated test database; a screenshot of each step is attached
 * to the test for the eye.
 */
import {expect, test, type Page} from './fixtures/playwright';
import {login} from './fixtures/auth-helpers';
import {TEST_ADMIN} from './fixtures/test-users';
import {buildPacDraft, goToPacStep, openPacPlanner, resolvePacIds, type PacStep} from './fixtures/galleryPac';

const PHONE = {width: 375, height: 812};

/** How much each DataTable wrapper of the step, and the page, overflow their box sideways (pixels, 0 = fits). */
async function sidewaysOverflow(page: Page): Promise<{page: number; tables: number[]}> {
    return page.evaluate(() => ({
        page: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
        tables: [...document.querySelectorAll<HTMLElement>('[data-testid="pac-planner-step"] .table-wrapper')].map((wrapper) => Math.max(0, wrapper.scrollWidth - wrapper.clientWidth)),
    }));
}

/** What the failure message shows to size the columns: the box of each table and the width each of its columns takes. */
async function tableBoxes(page: Page): Promise<string> {
    return page.evaluate(() =>
        JSON.stringify(
            [...document.querySelectorAll<HTMLElement>('[data-testid="pac-planner-step"] .table-wrapper')].map((wrapper) => ({
                box: wrapper.clientWidth,
                content: wrapper.scrollWidth,
                columns: [...wrapper.querySelectorAll<HTMLElement>('thead th')].map((th) => `${th.dataset.testid ?? th.className.split(' ')[0]}:${Math.round(th.getBoundingClientRect().width)}`),
            })),
        ),
    );
}

test.describe('PAC allocator on a phone (Y-9)', () => {
    test.setTimeout(240_000);

    for (const step of ['targets', 'review'] as const satisfies readonly PacStep[]) {
        test(`the ${step} step: no table and no page scrolls sideways at ${PHONE.width} px`, async ({page}, testInfo) => {
            await page.setViewportSize(PHONE);
            await login(page, TEST_ADMIN);
            const ids = await resolvePacIds(page);
            await openPacPlanner(page);
            await buildPacDraft(page, ids);
            await goToPacStep(page, step);

            const overflow = await sidewaysOverflow(page);
            await testInfo.attach(`pac-${step}-phone`, {body: await page.screenshot({fullPage: true}), contentType: 'image/png'});
            expect(overflow.tables.length, `the ${step} step shows at least one table`).toBeGreaterThan(0);
            expect(overflow, `sideways overflow in pixels: the page, then each table of the ${step} step; boxes ${await tableBoxes(page)}`).toEqual({page: 0, tables: overflow.tables.map(() => 0)});
        });
    }
});
