/**
 * The «Calls» boxes of a plugin's card never write one word over another (81 U47, testlist of 23/11/2026).
 *
 * Each plugin card of Settings › Plugins has five boxes (minute, hour, day, week, month); a box draws its window's label
 * and its count («0», «0 / 1 000», «0 no limit»). At 1440 and 768 px the label of the week collided with the count in
 * Italian («Settiman0»), and at 390 px the count and its «no limit» broke over three lines. The cause is one: a box is
 * a fixed grid, and a label and a count that do not fit its width have nowhere to go.
 *
 * The criterion, as the developer asked: the rectangle of the label's text and the rectangle of the count's text of a
 * box do not intersect, at 1440, 768 and 390 px. Two companions that the same defect breaks: each of the two is on one
 * line, and neither ends past its own box. The rectangles are those of the TEXT (a `Range` over the element's contents),
 * not of the element: an element squeezed narrower than its word still reports its narrow box while the word spills
 * over its neighbour. All four languages (the labels are «Week / Settimana / Semaine / Semana»), both kinds of reader:
 * a member (count and «no limit» as text) and an administrator (the count and an input to type the limit in).
 *
 * The geometry is read in one `evaluate` per box set; nothing is written (the language is the browser context's
 * localStorage only). A presence control makes a box whose label and count are hung on the same spot come back as an
 * overlap, or the zeros mean nothing.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo, setLanguage} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';

const WIDTHS = [1440, 768, 390] as const;
const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;

interface BoxReport {
    window: string;
    labelLines: number;
    countLines: number;
    overlap: number;
    labelPastBox: number;
    countPastBox: number;
}

/** What each box of the page does with its two texts. */
async function measureBoxes(page: Page): Promise<BoxReport[]> {
    return page.evaluate(() => {
        const rectsOf = (el: Element): DOMRect[] => {
            const range = document.createRange();
            range.selectNodeContents(el);
            return [...range.getClientRects()].filter((r) => r.width > 0 && r.height > 0);
        };
        const union = (rects: DOMRect[]) => ({
            left: Math.min(...rects.map((r) => r.left)),
            right: Math.max(...rects.map((r) => r.right)),
            top: Math.min(...rects.map((r) => r.top)),
            bottom: Math.max(...rects.map((r) => r.bottom)),
        });
        /** Lines: rectangles whose vertical middles are further apart than a quarter of a line are on different ones. */
        const lines = (rects: DOMRect[]): number => {
            const middles = rects.map((r) => (r.top + r.bottom) / 2).sort((a, b) => a - b);
            let count = 0;
            let last = -Infinity;
            for (const middle of middles) {
                if (middle - last > 4) count += 1;
                last = middle;
            }
            return count;
        };
        return [...document.querySelectorAll('[data-testid="plugin-settings-calls-window"]')].map((box) => {
            const label = box.firstElementChild as Element;
            const count = box.querySelector('[data-testid="plugin-settings-calls-count"]') as Element;
            const l = rectsOf(label);
            const c = rectsOf(count);
            const boxRect = box.getBoundingClientRect();
            const ul = union(l);
            const uc = union(c);
            const across = Math.min(ul.right, uc.right) - Math.max(ul.left, uc.left);
            const down = Math.min(ul.bottom, uc.bottom) - Math.max(ul.top, uc.top);
            return {
                window: box.getAttribute('data-window') ?? '',
                labelLines: lines(l),
                countLines: lines(c),
                overlap: across > 0.5 && down > 0.5 ? Math.round(across * 10) / 10 : 0,
                labelPastBox: Math.max(0, Math.round((ul.right - boxRect.right) * 10) / 10),
                countPastBox: Math.max(0, Math.round((uc.right - boxRect.right) * 10) / 10),
            };
        });
    });
}

function expectFit(reports: BoxReport[], what: string): void {
    expect(reports.length, `${what}: premise — the page has Calls boxes to measure`).toBeGreaterThan(0);
    const bad = reports.filter((r) => r.overlap > 0 || r.labelLines > 1 || r.countLines > 1 || r.labelPastBox > 0.5 || r.countPastBox > 0.5);
    expect(bad, `${what}: ${bad.length} of ${reports.length} boxes write one text over another, break a text over lines, or end past their box`).toEqual([]);
}

async function openPlugins(page: Page): Promise<void> {
    await navigateTo(page, '/settings?tab=plugins');
    await expect(page.getByTestId('settings-tab-plugins')).toHaveAttribute('aria-selected', 'true', {timeout: 10_000});
    await waitForSettled(page.getByTestId('plugin-settings-tab'), 25_000);
    await expect(page.getByTestId('plugin-settings-calls-window').last()).toBeVisible({timeout: 15_000});
}

test.beforeEach(async ({}, testInfo) => {
    test.skip(testInfo.project.name !== 'desktop', 'the file sets the widths it needs: one project is enough');
});

test('the detector sees a label and a count hung on the same spot (presence control)', async ({page}) => {
    await login(page, TEST_USER);
    await openPlugins(page);
    await page.evaluate(() => {
        const box = document.querySelector('[data-testid="plugin-settings-calls-window"]') as HTMLElement;
        for (const child of [box.firstElementChild, box.querySelector('[data-testid="plugin-settings-calls-count"]')] as HTMLElement[]) {
            child.style.cssText = 'position:absolute;left:20px;top:20px;white-space:nowrap';
        }
    });
    const reports = await measureBoxes(page);
    expect(reports[0].overlap, 'two texts on the same spot went unseen').toBeGreaterThan(0);
});

for (const [who, user] of [
    ['a member', TEST_USER],
    ['an administrator', TEST_ADMIN],
] as const) {
    for (const width of WIDTHS) {
        test(`${who} at ${width} px: label and count never overlap, in the four languages`, async ({page}) => {
            test.setTimeout(120_000);
            await page.setViewportSize({width, height: 900});
            await login(page, user);
            await openPlugins(page);
            try {
                for (const language of LANGUAGES) {
                    await setLanguage(page, language);
                    await waitForSettled(page.getByTestId('plugin-settings-tab'), 15_000);
                    expectFit(await measureBoxes(page), `${who}, ${language}, ${width} px`);
                }
            } finally {
                // The selector writes this browser context's localStorage only: hygiene, not isolation.
                await setLanguage(page, 'en');
            }
        });
    }
}
