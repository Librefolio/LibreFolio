import {expect, test} from '../fixtures/playwright';

import {API_TIMEOUT, assertPanelAboveOverlay, assertPanelWithinViewport, gotoDashboard, gotoFirstAsset, isSnapshotPost, isVisibleWithin, openAiExportPanel, readClipboard, selectAiExportSelection, setupAiExportPage} from './helpers';

test.setTimeout(120_000);

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('AI Export panel', () => {
    test.beforeEach(async ({context, page}) => {
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        await setupAiExportPage(page);
        await gotoDashboard(page);
    });

    test('uses current selectors and preserves focus, portal, viewport layout, and close behavior', async ({page}, testInfo) => {
        const trigger = page.getByTestId('ai-export-button');
        const syncButton = page.getByTestId('sync-button');

        if (testInfo.project.name === 'desktop') {
            const [triggerBox, syncBox] = await Promise.all([trigger.boundingBox(), syncButton.boundingBox()]);
            if (!triggerBox || !syncBox) throw new Error('Dashboard action buttons require layout boxes');
            expect(Math.abs(triggerBox.y - syncBox.y)).toBeLessThan(2);
            expect(Math.min(triggerBox.y + triggerBox.height, syncBox.y + syncBox.height)).toBeGreaterThan(Math.max(triggerBox.y, syncBox.y));
        }

        const firstOpen = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-selection-button')).toBeFocused({timeout: 2_000});
        await expect(firstOpen.menu).toHaveAttribute('role', 'dialog');
        expect(await firstOpen.menu.evaluate((panel) => panel.parentElement === document.body)).toBe(true);
        await assertPanelWithinViewport(page, firstOpen.menu);

        await page.keyboard.press('Escape');
        await expect(firstOpen.menu).toBeHidden({timeout: 2_000});
        await expect(firstOpen.trigger).toBeFocused({timeout: 2_000});

        const outsideClose = await openAiExportPanel(page);
        await page.mouse.click(2, 2);
        await expect(outsideClose.menu).toBeHidden({timeout: 2_000});
    });

    test('keeps outer trigger label stable while preparing', async ({page}) => {
        const panel = await openAiExportPanel(page);
        await selectAiExportSelection(page, 'dataset', 'portfolio.overview_and_history');
        await page.getByTestId('ai-export-detail-compact').click();

        const stableLabel = await panel.trigger.getAttribute('aria-label');
        expect(stableLabel).toBeTruthy();

        let releaseRequest!: () => void;
        let signalStarted!: () => void;
        const requestGate = new Promise<void>((resolve) => {
            releaseRequest = resolve;
        });
        const requestStarted = new Promise<void>((resolve) => {
            signalStarted = resolve;
        });

        await page.route('**/api/v1/ai-export/snapshot', async (route) => {
            signalStarted();
            await requestGate;
            await route.continue();
        });

        const responsePromise = page.waitForResponse((response) => isSnapshotPost(response.request()), {timeout: API_TIMEOUT});
        try {
            await page.getByTestId('ai-export-copy-button').click();
            await requestStarted;
            await expect(panel.trigger).toHaveAttribute('aria-label', stableLabel!);
            await expect(panel.trigger).toHaveAttribute('aria-busy', 'true', {timeout: 2_000});
            await expect(panel.trigger).toBeDisabled({timeout: 2_000});
            await expect(page.getByTestId('ai-export-copy-button')).toContainText('Preparing export…', {timeout: 2_000});
        } finally {
            releaseRequest();
        }

        const response = await responsePromise;
        const failureBody = response.status() === 200 ? '' : await response.text();
        expect(response.status(), failureBody).toBe(200);
        if (await isVisibleWithin(page.getByTestId('ai-export-copy-anyway'))) await page.getByTestId('ai-export-copy-anyway').click();
        await expect(panel.menu).toBeHidden({timeout: 3_000});
        await expect(panel.trigger).toHaveAttribute('aria-label', stableLabel!);
        await page.unroute('**/api/v1/ai-export/snapshot');
    });

    test('drops an in-flight export after its panel context closes', async ({page}) => {
        const panel = await openAiExportPanel(page);
        await selectAiExportSelection(page, 'dataset', 'portfolio.overview_and_history');
        await page.getByTestId('ai-export-detail-compact').click();
        await page.evaluate(() => navigator.clipboard.writeText(''));

        let releaseRequest!: () => void;
        let signalStarted!: () => void;
        const requestGate = new Promise<void>((resolve) => {
            releaseRequest = resolve;
        });
        const requestStarted = new Promise<void>((resolve) => {
            signalStarted = resolve;
        });

        await page.route('**/api/v1/ai-export/snapshot', async (route) => {
            signalStarted();
            await requestGate;
            await route.continue();
        });

        const responsePromise = page.waitForResponse((response) => isSnapshotPost(response.request()), {timeout: API_TIMEOUT});
        try {
            await page.getByTestId('ai-export-copy-button').click();
            await requestStarted;
            await page.keyboard.press('Escape');
            await expect(panel.menu).toBeHidden({timeout: 2_000});
            await expect(panel.trigger).toBeEnabled({timeout: 2_000});
        } finally {
            releaseRequest();
        }

        const response = await responsePromise;
        expect(response.status(), response.status() === 200 ? '' : await response.text()).toBe(200);
        await expect.poll(() => readClipboard(page), {timeout: 2_000, intervals: [100, 250, 500]}).toBe('');
        await page.unroute('**/api/v1/ai-export/snapshot');
    });

    test('shows current inline help and catalog guidance', async ({page}) => {
        await openAiExportPanel(page);
        await page.getByTestId('ai-export-category-dataset').click();
        await expect(page.getByTestId('ai-export-category-help')).toContainText('Copies only the selected LibreFolio facts', {timeout: 2_000});

        const compactHelp = page.getByTestId('ai-export-detail-help-compact');
        await compactHelp.click();
        await expect(page.getByTestId('tooltip-content')).toContainText('Same data universe, with temporal buckets up to 30 days.', {timeout: 2_000});
        await compactHelp.click();
        await expect(page.getByTestId('tooltip-content')).toBeHidden({timeout: 2_000});

        const periodHelp = page.getByTestId('ai-export-period-help');
        await periodHelp.click();
        await expect(page.getByTestId('tooltip-content')).toContainText('Independent export period ending on the snapshot date.', {timeout: 2_000});
        await periodHelp.click();
        await expect(page.getByTestId('tooltip-content')).toBeHidden({timeout: 2_000});

        await page.getByTestId('ai-export-category-analysis').click();
        await expect(page.getByTestId('ai-export-category-help')).toContainText('Copies the required facts plus a focused question', {timeout: 2_000});
        const selectionButton = page.getByTestId('ai-export-selection-button');
        await selectionButton.click();
        const selectionDropdown = page.getByTestId('ai-export-selection-dropdown');
        const [buttonBox, dropdownBox] = await Promise.all([selectionButton.boundingBox(), selectionDropdown.boundingBox()]);
        if (!buttonBox || !dropdownBox) throw new Error('AI Export selection requires trigger and dropdown layout boxes');
        expect(Math.abs(buttonBox.width - dropdownBox.width)).toBeLessThan(1);
        const option = page.getByTestId('ai-export-selection-option-portfolio.performance_market_drivers');
        await expect(option).toContainText('Portfolio Performance & Market Drivers', {timeout: 2_000});
        await expect(option).toContainText('Explain portfolio performance and research dated market drivers for every held Asset.', {timeout: 2_000});
        const optionDescription = page.getByTestId('ai-export-selection-option-portfolio.performance_market_drivers-description');
        await expect(optionDescription).toHaveCSS('white-space', 'normal', {timeout: 2_000});
        expect(
            await optionDescription.evaluate((element) => {
                const lineHeight = Number.parseFloat(getComputedStyle(element).lineHeight);
                return element.scrollHeight > lineHeight * 1.5;
            }),
        ).toBe(true);
        await option.click();
    });

    test('shows deterministic size warning and Copy Anyway flow', async ({page}) => {
        const panel = await openAiExportPanel(page);
        await selectAiExportSelection(page, 'analysis', 'portfolio.performance_market_drivers');
        await page.getByTestId('ai-export-detail-full').click();

        const oversizedNotes = `E2E_SIZE_WARNING_${'x'.repeat(90_000)}`;
        const notes = page.getByTestId('ai-export-user-notes');
        await notes.evaluate((element, value) => {
            const textarea = element as HTMLTextAreaElement;
            const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
            setter?.call(textarea, value);
            textarea.dispatchEvent(new Event('input', {bubbles: true}));
        }, oversizedNotes);
        await expect.poll(() => notes.inputValue().then((value) => value.length), {timeout: 2_000}).toBe(oversizedNotes.length);

        const responsePromise = page.waitForResponse((response) => isSnapshotPost(response.request()), {timeout: API_TIMEOUT});
        await page.getByTestId('ai-export-copy-button').click();
        const response = await responsePromise;
        const failureBody = response.status() === 200 ? '' : await response.text();
        expect(response.status(), failureBody).toBe(200);

        await expect(page.getByTestId('ai-export-payload-stats')).toBeVisible({timeout: 3_000});
        await expect(page.getByTestId('ai-export-payload-stats')).toContainText('Final prompt size', {timeout: 2_000});
        await expect(page.getByTestId('ai-export-payload-stats')).toContainText('text that will actually be copied', {timeout: 2_000});
        await expect(page.getByTestId('ai-export-backend-size')).toHaveCount(0);
        await expect(page.getByTestId('ai-export-final-size')).toContainText('💾', {timeout: 2_000});
        await expect(page.getByTestId('ai-export-token-severity')).toBeVisible({timeout: 3_000});
        await expect(page.getByTestId('ai-export-use-compact')).toBeVisible({timeout: 3_000});
        await expect(page.getByTestId('ai-export-copy-anyway')).toBeVisible({timeout: 3_000});

        await page.getByTestId('ai-export-copy-anyway').click();
        await expect(panel.menu).toBeHidden({timeout: 3_000});
    });

    test('portals above Asset chart controls on desktop and mobile', async ({page}) => {
        await gotoFirstAsset(page);
        const panel = await openAiExportPanel(page);
        await assertPanelWithinViewport(page, panel.menu);
        await assertPanelAboveOverlay(panel.menu, page.getByTestId('asset-detail-measure-btn'));
    });
});
