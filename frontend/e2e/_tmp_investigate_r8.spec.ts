import {test, expect} from '@playwright/test';
import {login, navigateTo} from './fixtures/auth-helpers';
import {TEST_USER} from './fixtures/test-users';

test.setTimeout(30_000);

const PRESET_LABELS = new Set([
    '1W', '1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '10Y',
    'WTD', 'MTD', 'QTD', 'YTD',
    'All', 'Tutti', 'Custom', 'Personalizzato',
]);

async function measureWrap(page: import('@playwright/test').Page) {
    return await page.evaluate((labels) => {
        const dashboard = (window as any).__lfLayouts?.dashboard;
        const pickerConfig = dashboard?.pickerConfig;
        const bar = document.querySelector('[data-testid="dashboard-filter-bar"]');
        const allButtons = Array.from(bar?.querySelectorAll('button') ?? []) as HTMLButtonElement[];
        const visiblePresetButtons = allButtons.filter((b) => {
            const text = b.textContent?.trim() ?? '';
            if (!labels.includes(text)) return false;
            let el: HTMLElement | null = b;
            while (el) {
                if (el.getAttribute('aria-hidden') === 'true' || el.classList.contains('invisible')) return false;
                el = el.parentElement;
            }
            return true;
        });
        const tops = visiblePresetButtons.map((b) => Math.round(b.getBoundingClientRect().top));
        const uniqueTops = [...new Set(tops)].sort((a, b) => a - b);
        return {
            badgeCount: visiblePresetButtons.length,
            uniqueRows: uniqueTops.length,
            tops,
            labels: visiblePresetButtons.map((b) => b.textContent?.trim()),
            maxWidth: pickerConfig?.maxWidth,
            layoutMode: dashboard?.layoutMode,
        };
    }, [...PRESET_LABELS]);
}

test.describe('Round 8 diagnostic - wrap fix + dynamic maxWidth', () => {
    test('1128px container should never show wrapped badges (verify+shed)', async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/dashboard');
        await page.getByTestId('dashboard-filter-bar').waitFor({state: 'visible', timeout: 8_000});

        const widths = [1128, 1200, 1400, 1000, 950, 900, 850, 1129, 1127];
        for (const vw of widths) {
            await page.setViewportSize({width: vw, height: 900});
            await page.waitForTimeout(600);
            const result = await measureWrap(page);
            console.log(
                `viewport=${vw}px -> badges=${result.badgeCount} rows=${result.uniqueRows} tops=${JSON.stringify(result.tops)} layoutMode=${result.layoutMode} labels=${JSON.stringify(result.labels)}`
            );
            // Each row-group must be internally consistent (all same top). More than 2 distinct
            // tops would mean a badge stranded alone on a broken 3rd row - the exact bug reported.
            expect(result.uniqueRows, `at ${vw}px badges wrapped unexpectedly: tops=${JSON.stringify(result.tops)}`).toBeLessThanOrEqual(2);
        }
    });

    test('resize sequence should not get stuck in a wrong wrapped state', async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/dashboard');
        await page.getByTestId('dashboard-filter-bar').waitFor({state: 'visible', timeout: 8_000});

        await page.setViewportSize({width: 500, height: 900});
        await page.waitForTimeout(600);
        let result = await measureWrap(page);
        console.log(`after narrow(500) -> rows=${result.uniqueRows} badges=${result.badgeCount}`);

        await page.setViewportSize({width: 1128, height: 900});
        await page.waitForTimeout(600);
        result = await measureWrap(page);
        console.log(`after resize to 1128 -> rows=${result.uniqueRows} badges=${result.badgeCount} tops=${JSON.stringify(result.tops)}`);
        expect(result.uniqueRows, `stuck wrapped state after resize: tops=${JSON.stringify(result.tops)}`).toBeLessThanOrEqual(2);

        await page.setViewportSize({width: 1129, height: 900});
        await page.waitForTimeout(600);
        result = await measureWrap(page);
        console.log(`after resize to 1129 -> rows=${result.uniqueRows} badges=${result.badgeCount}`);
        expect(result.uniqueRows).toBeLessThanOrEqual(2);

        // Sequence of small back-and-forth resizes around the same boundary (the exact
        // "stuck stable wrong fixed point" scenario reported by the user)
        for (const vw of [1130, 1126, 1128, 1125, 1128]) {
            await page.setViewportSize({width: vw, height: 900});
            await page.waitForTimeout(600);
            result = await measureWrap(page);
            console.log(`oscillate to ${vw} -> rows=${result.uniqueRows} badges=${result.badgeCount}`);
            expect(result.uniqueRows).toBeLessThanOrEqual(2);
        }
    });

    test('live console maxWidth tuning works end-to-end without a resize', async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/dashboard');
        await page.getByTestId('dashboard-filter-bar').waitFor({state: 'visible', timeout: 8_000});
        await page.setViewportSize({width: 1400, height: 900});
        await page.waitForTimeout(600);

        const before = await page.evaluate(() => {
            const el = document.querySelector('[data-testid="dashboard-filter-bar"] .drp-trigger')
                ?.parentElement as HTMLElement | null;
            return el ? getComputedStyle(el).maxWidth : null;
        });
        console.log(`before tuning: computed max-width = ${before}`);

        await page.evaluate(() => {
            (window as any).__lfLayouts.dashboard.pickerConfig.maxWidth = 900;
        });
        await page.waitForTimeout(600);

        const after = await page.evaluate(() => {
            const el = document.querySelector('[data-testid="dashboard-filter-bar"] .drp-trigger')
                ?.parentElement as HTMLElement | null;
            return el ? getComputedStyle(el).maxWidth : null;
        });
        console.log(`after tuning to 900: computed max-width = ${after}`);
        expect(after).toBe('900px');
        expect(after).not.toBe(before);

        const result = await measureWrap(page);
        console.log(`after tuning, badge check -> rows=${result.uniqueRows} badges=${result.badgeCount}`);
        expect(result.uniqueRows).toBeLessThanOrEqual(2);

        // tune back down small to confirm badges shrink back down (shed) without reload
        await page.evaluate(() => {
            (window as any).__lfLayouts.dashboard.pickerConfig.maxWidth = 400;
        });
        await page.waitForTimeout(600);
        const afterSmall = await page.evaluate(() => {
            const el = document.querySelector('[data-testid="dashboard-filter-bar"] .drp-trigger')
                ?.parentElement as HTMLElement | null;
            return el ? getComputedStyle(el).maxWidth : null;
        });
        expect(afterSmall).toBe('400px');
        const resultSmall = await measureWrap(page);
        console.log(`after tuning to 400 -> rows=${resultSmall.uniqueRows} badges=${resultSmall.badgeCount}`);
        expect(resultSmall.uniqueRows).toBeLessThanOrEqual(2);
    });
});
