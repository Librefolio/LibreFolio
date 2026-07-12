import {test} from '@playwright/test';
import {login, navigateTo} from './fixtures/auth-helpers';
import {TEST_USER} from './fixtures/test-users';

const PRESET_LABELS = new Set([
    '1W', '1M', '3M', '6M', '1Y', '2Y', '3Y', '5Y', '10Y',
    'WTD', 'MTD', 'QTD', 'YTD',
    'All', 'Tutti', 'Custom', 'Personalizzato',
]);

async function measure(page: import('@playwright/test').Page) {
    return await page.evaluate((labels) => {
        const bar = document.querySelector('[data-testid="dashboard-filter-bar"]');
        const allButtons = Array.from(bar?.querySelectorAll('button') ?? []) as HTMLButtonElement[];
        const visible = allButtons.filter((b) => {
            const text = b.textContent?.trim() ?? '';
            if (!labels.includes(text)) return false;
            let el: HTMLElement | null = b;
            while (el) {
                if (el.getAttribute('aria-hidden') === 'true' || el.classList.contains('invisible')) return false;
                el = el.parentElement;
            }
            return true;
        });
        const tops = visible.map((b) => Math.round(b.getBoundingClientRect().top));
        return {count: visible.length, uniqueTops: [...new Set(tops)], tops, labels: visible.map(b=>b.textContent?.trim())};
    }, [...PRESET_LABELS]);
}

test('reproduce exact test1 sequence then poll at 1129', async ({page}) => {
    await login(page, TEST_USER);
    await navigateTo(page, '/dashboard');
    await page.getByTestId('dashboard-filter-bar').waitFor({state: 'visible', timeout: 8_000});

    const widths = [1128, 1200, 1400, 1000, 950, 900, 850];
    for (const vw of widths) {
        await page.setViewportSize({width: vw, height: 900});
        await page.waitForTimeout(300);
    }
    console.log('--- now going to 1129, polling ---');
    await page.setViewportSize({width: 1129, height: 900});
    for (let i = 0; i < 10; i++) {
        await page.waitForTimeout(100);
        const r = await measure(page);
        console.log(`t=${(i+1)*100}ms -> count=${r.count} uniqueTops=${JSON.stringify(r.uniqueTops)} tops=${JSON.stringify(r.tops)} labels=${JSON.stringify(r.labels)}`);
    }
});
