import {expect, test, type Locator, type Page, type Request} from '@playwright/test';
import {login, navigateTo, setLanguage} from './fixtures/auth-helpers';
import {TEST_USER} from './fixtures/test-users';

type AiExportDomain = 'portfolio' | 'asset' | 'fx' | 'broker';

interface ExportExpectation {
    domain: AiExportDomain;
    task: string;
    assetId?: number;
    brokerId?: number;
    omitBrokerIds?: boolean;
}

interface SnapshotRequestPayload {
    domain: AiExportDomain;
    task: string;
    detail_level: string;
    broker_ids?: number[];
    asset_id?: number;
    broker_id?: number;
    base_currency?: string;
    quote_currency?: string;
}

const UI_TIMEOUT = 8_000;
const RESPONSE_TIMEOUT = 20_000;
const SNAPSHOT_DESCRIPTION = 'Copy factual data only, without analysis instructions or a response contract.';

test.setTimeout(120_000);

function isSnapshotPost(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/ai-export/snapshot';
}

async function requireSeededEntry(page: Page, candidates: readonly Locator[], errorMessage: string): Promise<Locator> {
    const deadline = Date.now() + UI_TIMEOUT;

    while (Date.now() < deadline) {
        for (const candidate of candidates) {
            if (await candidate.isVisible()) return candidate;
        }
        await page.waitForTimeout(100);
    }

    throw new Error(`${errorMessage} Check populate_mock_data.py seeding.`);
}

function numericScopeId(page: Page, domain: 'assets' | 'brokers'): number {
    const match = new URL(page.url()).pathname.match(new RegExp(`^/${domain}/(\\d+)$`));
    if (!match) throw new Error(`Cannot derive ${domain} scope ID from URL: ${page.url()}`);
    return Number(match[1]);
}

function expectUppercaseCurrency(value: string | undefined, field: string): void {
    if (value === undefined) throw new Error(`${field} must be a string`);
    expect(value.length, `${field} must not be empty`).toBeGreaterThan(0);
    expect(value, `${field} must be uppercase`).toBe(value.toUpperCase());
    expect(value, `${field} must contain uppercase letters only`).toMatch(/^[A-Z]+$/);
}

async function readClipboard(page: Page): Promise<string> {
    return page.evaluate(async () => {
        try {
            return await navigator.clipboard.readText();
        } catch {
            return '';
        }
    });
}

async function waitForClipboard(page: Page, requiredFragments: readonly string[], message: string): Promise<string> {
    await expect
        .poll(
            async () => {
                const clipboardText = await readClipboard(page);
                return requiredFragments.every((fragment) => clipboardText.includes(fragment));
            },
            {
                timeout: 5_000,
                intervals: [100, 200, 500],
                message,
            },
        )
        .toBe(true);

    return readClipboard(page);
}

async function openAiExportPanel(page: Page): Promise<{trigger: Locator; menu: Locator}> {
    const trigger = page.getByTestId('ai-export-v2-button');
    await expect(trigger).toBeVisible({timeout: UI_TIMEOUT});
    await expect(trigger).toBeEnabled({timeout: UI_TIMEOUT});
    await trigger.click();

    const menu = page.getByTestId('ai-export-v2-menu-panel');
    await expect(menu).toBeVisible({timeout: 3_000});
    expect(await menu.evaluate((panel) => panel.parentElement === document.body)).toBe(true);
    return {trigger, menu};
}

async function selectAnalysis(page: Page, analysis: string): Promise<void> {
    await page.getByTestId('ai-export-v2-task-select-button').click();
    await page.getByTestId(`ai-export-v2-task-option-${analysis}`).click();
}

async function assertAnalysisOptionVisibility(page: Page, visibleAnalyses: readonly string[], hiddenAnalyses: readonly string[]): Promise<void> {
    await page.getByTestId('ai-export-v2-task-select-button').click();
    for (const analysis of visibleAnalyses) {
        await expect(page.getByTestId(`ai-export-v2-task-option-${analysis}`)).toBeVisible({timeout: 2_000});
    }
    for (const analysis of hiddenAnalyses) {
        await expect(page.getByTestId(`ai-export-v2-task-option-${analysis}`)).toHaveCount(0);
    }
    await page.keyboard.press('Escape');
    await expect(page.getByRole('listbox', {name: 'Analysis task'})).toBeHidden({timeout: 2_000});
}

async function assertRemovedControlsAbsent(page: Page): Promise<void> {
    await expect(page.getByTestId('ai-export-v2-response-language')).toHaveCount(0);
    await expect(page.getByTestId('ai-export-v2-response-language-button')).toHaveCount(0);
    await expect(page.getByTestId('ai-export-v2-compatibility-status')).toHaveCount(0);
    await expect(page.getByTestId('ai-export-v2-render-data_only')).toHaveCount(0);
    await expect(page.getByTestId('ai-export-v2-render-full_prompt')).toHaveCount(0);
    await expect(page.getByTestId('ai-export-v2-web-research')).toHaveCount(0);
}

async function assertDocsPopup(page: Page, expectedPath: string, activation: 'click' | 'Enter' = 'click'): Promise<void> {
    const docsLink = page.getByTestId('ai-export-v2-docs-link');
    const popupPromise = page.waitForEvent('popup');
    if (activation === 'Enter') {
        await docsLink.focus();
        await expect(docsLink).toBeFocused();
        await docsLink.press('Enter');
    } else {
        await docsLink.click();
    }
    const popup = await popupPromise;
    await expect.poll(() => new URL(popup.url()).pathname, {timeout: UI_TIMEOUT}).toBe(expectedPath);
    await popup.close();
    await page.mouse.move(0, 0);
}

async function assertPanelAboveChartControls(menu: Locator, overlayButton: Locator): Promise<void> {
    await expect(overlayButton).toBeVisible({timeout: UI_TIMEOUT});
    const overlayTestId = await overlayButton.getAttribute('data-testid');
    if (!overlayTestId) throw new Error('Chart overlay button requires data-testid');
    const layers = await menu.evaluate((panel, overlayTestId) => {
        const overlay = document.querySelector<HTMLElement>(`[data-testid="${overlayTestId}"]`);
        if (!overlay) throw new Error(`Missing overlay ${overlayTestId}`);

        let overlayZ = 0;
        let current: HTMLElement | null = overlay;
        while (current && current !== document.body) {
            const parsed = Number.parseInt(getComputedStyle(current).zIndex, 10);
            if (Number.isFinite(parsed)) overlayZ = Math.max(overlayZ, parsed);
            current = current.parentElement;
        }

        return {
            bodyLevel: panel.parentElement === document.body,
            panelZ: Number.parseInt(getComputedStyle(panel).zIndex, 10),
            overlayZ,
        };
    }, overlayTestId);

    expect(layers.bodyLevel).toBe(true);
    expect(layers.panelZ).toBe(9000);
    expect(layers.panelZ).toBeGreaterThan(layers.overlayZ);
}

async function exportSnapshotAndAssert(page: Page, expected: ExportExpectation): Promise<void> {
    const {trigger, menu} = await openAiExportPanel(page);
    await selectAnalysis(page, 'snapshot');
    await expect(page.getByTestId('ai-export-v2-task-selected-name')).toHaveText('Data Snapshot');
    await expect(page.getByTestId('ai-export-v2-user-notes')).toHaveCount(0);
    await assertRemovedControlsAbsent(page);

    const compact = page.getByTestId('ai-export-v2-detail-compact');
    await compact.click();
    await expect(compact).toHaveAttribute('aria-pressed', 'true', {timeout: 2_000});

    const exportButton = page.getByTestId('ai-export-v2-export-button');
    await expect(exportButton).toBeEnabled({timeout: 3_000});

    const requestPromise = page.waitForRequest(isSnapshotPost, {timeout: UI_TIMEOUT});
    const responsePromise = page.waitForResponse((response) => isSnapshotPost(response.request()), {timeout: RESPONSE_TIMEOUT});

    await exportButton.click();
    await expect(menu).toBeHidden({timeout: 3_000});
    await expect(trigger).toBeFocused({timeout: 3_000});

    const [request, response] = await Promise.all([requestPromise, responsePromise]);
    const failureBody = response.status() === 200 ? '' : await response.text();
    expect(response.status(), failureBody).toBe(200);

    const payload: SnapshotRequestPayload = request.postDataJSON();
    expect(payload).toMatchObject({
        domain: expected.domain,
        task: expected.task,
        detail_level: 'compact',
    });

    if (expected.omitBrokerIds) expect(payload).not.toHaveProperty('broker_ids');
    if (expected.assetId !== undefined) expect(payload.asset_id).toBe(expected.assetId);
    if (expected.brokerId !== undefined) expect(payload.broker_id).toBe(expected.brokerId);
    if (expected.domain === 'fx') {
        expectUppercaseCurrency(payload.base_currency, 'base_currency');
        expectUppercaseCurrency(payload.quote_currency, 'quote_currency');
    }

    const clipboardText = await waitForClipboard(page, ['Snapshot Data', `domain: ${expected.domain}`, `task: ${expected.task}`], `Clipboard did not receive ${expected.domain}.${expected.task} Snapshot data`);
    expect(clipboardText).not.toContain('Task Instructions');
    expect(clipboardText).not.toContain('Optional User Notes');
}

test.describe('AI Export V2 panel and hard cutover', () => {
    test.beforeEach(async ({context, page}) => {
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        await login(page, TEST_USER);
        await setLanguage(page, 'en');
    });

    test('keeps Dashboard toolbar layout, focus-visible styling, docs, and draft memory', async ({page}) => {
        await navigateTo(page, '/dashboard');
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: UI_TIMEOUT});

        const trigger = page.getByTestId('ai-export-v2-button');
        const syncButton = page.getByTestId('sync-button');
        if ((page.viewportSize()?.width ?? 0) >= 1_000) {
            const [triggerBox, syncBox] = await Promise.all([trigger.boundingBox(), syncButton.boundingBox()]);
            if (!triggerBox || !syncBox) throw new Error('Dashboard action buttons must have layout boxes');
            expect(Math.abs(triggerBox.y - syncBox.y)).toBeLessThan(2);
            expect(Math.min(triggerBox.y + triggerBox.height, syncBox.y + syncBox.height)).toBeGreaterThan(Math.max(triggerBox.y, syncBox.y));
        }

        const triggerClass = (await trigger.getAttribute('class')) ?? '';
        expect(triggerClass).toContain('focus-visible:ring-2');
        expect(triggerClass).not.toMatch(/(?:^|\s)focus:ring-/);

        const {menu} = await openAiExportPanel(page);
        await assertRemovedControlsAbsent(page);

        const taskSelect = page.getByTestId('ai-export-v2-task-select-button');
        await expect(taskSelect).toBeFocused();
        await expect(menu).not.toHaveAttribute('aria-modal', 'true');
        await expect(taskSelect).toHaveAttribute('role', 'combobox');
        await expect(taskSelect).toHaveAttribute('aria-haspopup', 'listbox');
        await assertDocsPopup(page, '/mkdocs/user/ai-export/portfolio/', 'Enter');

        const taskListboxId = await taskSelect.getAttribute('aria-controls');
        expect(taskListboxId).toBeTruthy();
        await taskSelect.click();
        const taskListbox = page.getByRole('listbox', {name: 'Analysis task'});
        await expect(taskListbox).toBeVisible();
        await expect(taskListbox).toHaveAttribute('id', taskListboxId!);
        const snapshotOption = page.getByTestId('ai-export-v2-task-option-snapshot');
        await expect(snapshotOption).toContainText('Data Snapshot');
        await expect(snapshotOption).toContainText(SNAPSHOT_DESCRIPTION);
        await expect(page.getByTestId('ai-export-v2-task-option-portfolio_fifo_lot_review')).toContainText('Portfolio FIFO Lot Review');
        await page.keyboard.press('Escape');
        await expect(taskListbox).toBeHidden({timeout: 2_000});
        await expect(menu).toBeVisible();
        await expect(taskSelect).toHaveAttribute('aria-expanded', 'false');
        await page.keyboard.press('Escape');
        await expect(menu).toBeHidden({timeout: 2_000});
        await expect(trigger).toBeFocused();
        await openAiExportPanel(page);

        const draftNotes = 'Preserve this Dashboard draft.';
        await selectAnalysis(page, 'rebalancing');
        await page.getByTestId('ai-export-v2-detail-full').click();
        await page.getByTestId('ai-export-v2-user-notes').fill(draftNotes);

        const detailHelpExpectations = {
            compact: 'no time series',
            standard: '8 preceding weekly points',
            full: 'full technical window',
        } as const;
        const hoverHelpButton = page.getByTestId('ai-export-v2-detail-help-compact');
        await hoverHelpButton.hover();
        await expect(page.getByTestId('tooltip-content')).toContainText(detailHelpExpectations.compact);
        await page.evaluate(() => window.dispatchEvent(new Event('scroll')));
        await page.waitForTimeout(250);
        await expect(page.getByTestId('tooltip-content')).toBeVisible();
        await page.mouse.move(0, 0);
        await expect(page.getByTestId('tooltip-content')).toBeHidden({timeout: 2_000});

        for (const [detailLevel, expectedText] of Object.entries(detailHelpExpectations)) {
            const helpButton = page.getByTestId(`ai-export-v2-detail-help-${detailLevel}`);
            await expect(helpButton).toBeVisible();
            await helpButton.click();
            await expect(page.getByTestId('tooltip-content')).toContainText(expectedText);
            await helpButton.click();
            await expect(page.getByTestId('tooltip-content')).toBeHidden({timeout: 2_000});
        }

        await trigger.click();
        await expect(menu).toBeHidden({timeout: 2_000});
        await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);

        const reopened = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-v2-task-selected-name')).toHaveText('Portfolio Rebalancing');
        await expect(page.getByTestId('ai-export-v2-detail-full')).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('ai-export-v2-user-notes')).toHaveValue(draftNotes);

        await page.keyboard.press('Escape');
        await expect(reopened.menu).toBeHidden({timeout: 2_000});
        await expect(reopened.trigger).toBeFocused();

        const technicalWindowPanel = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-v2-technical-window-3m')).toHaveAttribute('aria-pressed', 'true');
        await page.getByTestId('ai-export-v2-technical-window-custom').click();
        await page.getByTestId('ai-export-v2-technical-window-custom-amount').fill('8');
        await page.getByTestId('ai-export-v2-technical-window-custom-unit-button').click();
        await page.getByTestId('ai-export-v2-technical-window-custom-unit-option-weeks').click();
        await technicalWindowPanel.trigger.click();
        const restoredTechnicalWindowPanel = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-v2-technical-window-custom-amount')).toBeVisible();
        await expect(page.getByTestId('ai-export-v2-technical-window-custom-amount')).toHaveValue('8');
        await expect(page.getByTestId('ai-export-v2-technical-window-custom-unit-button')).toContainText('W');
        await restoredTechnicalWindowPanel.trigger.click();

        const outsideClose = await openAiExportPanel(page);
        await page.mouse.click(4, 4);
        await expect(outsideClose.menu).toBeHidden({timeout: 2_000});
        await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);
    });

    test('keeps hidden analysis notes out of Snapshot clipboard and restores the draft', async ({page}) => {
        await navigateTo(page, '/dashboard');
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: UI_TIMEOUT});

        const hiddenNote = 'SNAPSHOT_SECRET_NOTE_7f19';
        const {trigger, menu} = await openAiExportPanel(page);
        await selectAnalysis(page, 'rebalancing');
        await page.getByTestId('ai-export-v2-user-notes').fill(hiddenNote);
        await selectAnalysis(page, 'snapshot');
        await expect(page.getByTestId('ai-export-v2-user-notes')).toHaveCount(0);

        const requestPromise = page.waitForRequest(isSnapshotPost, {timeout: UI_TIMEOUT});
        const responsePromise = page.waitForResponse((response) => isSnapshotPost(response.request()), {timeout: RESPONSE_TIMEOUT});
        await page.getByTestId('ai-export-v2-export-button').click();
        await expect(menu).toBeHidden({timeout: 3_000});
        await expect(trigger).toBeFocused({timeout: 3_000});

        const [request, response] = await Promise.all([requestPromise, responsePromise]);
        const failureBody = response.status() === 200 ? '' : await response.text();
        expect(response.status(), failureBody).toBe(200);
        expect(request.postDataJSON()).toMatchObject({
            domain: 'portfolio',
            task: 'portfolio_description',
            detail_level: 'standard',
        });

        const clipboardText = await waitForClipboard(page, ['Snapshot Data', 'domain: portfolio', 'task: portfolio_description'], 'Clipboard did not receive the Dashboard Snapshot');
        expect(clipboardText).not.toContain(hiddenNote);
        expect(clipboardText).not.toContain('Optional User Notes');

        const reopened = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-v2-task-selected-name')).toHaveText('Data Snapshot');
        await selectAnalysis(page, 'rebalancing');
        await expect(page.getByTestId('ai-export-v2-user-notes')).toHaveValue(hiddenNote);
        await reopened.trigger.click();
        await expect(reopened.menu).toBeHidden({timeout: 2_000});
    });

    test('isolates Asset and canonical FX drafts and portals panels above chart controls', async ({page}) => {
        await navigateTo(page, '/assets');
        await expect(page.getByTestId('assets-page')).toBeVisible({timeout: UI_TIMEOUT});
        const assetEntry = await requireSeededEntry(page, [page.getByTestId(/^asset-card-/).first(), page.getByTestId(/^asset-row-/).first()], 'No seeded asset card or row found on /assets.');
        await assetEntry.click();
        await expect(page).toHaveURL(/\/assets\/\d+(?:[?#].*)?$/, {timeout: UI_TIMEOUT});
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
        const assetPath = new URL(page.url()).pathname;

        const assetPanel = await openAiExportPanel(page);
        await assertPanelAboveChartControls(assetPanel.menu, page.getByTestId('asset-detail-measure-btn'));
        await assertRemovedControlsAbsent(page);
        await assertDocsPopup(page, '/mkdocs/user/ai-export/asset/');
        await assertAnalysisOptionVisibility(page, ['snapshot', 'asset_trend_analysis', 'position_review', 'drawdown_recovery'], ['asset_snapshot', 'asset_pac_timing_context']);
        await selectAnalysis(page, 'asset_trend_analysis');
        await page.getByTestId('ai-export-v2-detail-full').click();
        await page.getByTestId('ai-export-v2-user-notes').fill('Asset-only draft');
        await assetPanel.trigger.click();
        await expect(assetPanel.menu).toBeHidden({timeout: 2_000});

        await navigateTo(page, '/fx/EUR-USD');
        await expect(page.getByTestId('fx-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
        const fxPanel = await openAiExportPanel(page);
        await assertPanelAboveChartControls(fxPanel.menu, page.getByTestId('fx-detail-measure-btn'));
        await assertRemovedControlsAbsent(page);
        await assertDocsPopup(page, '/mkdocs/user/ai-export/fx/');
        await assertAnalysisOptionVisibility(page, ['snapshot', 'fx_trend_review', 'fx_conversion_timing_context'], ['fx_exposure_impact']);
        await expect(page.getByTestId('ai-export-v2-task-selected-name')).toHaveText('FX Trend Review');
        await expect(page.getByTestId('ai-export-v2-user-notes')).toHaveValue('');
        await selectAnalysis(page, 'fx_conversion_timing_context');
        await page.getByTestId('ai-export-v2-detail-full').click();
        await page.getByTestId('ai-export-v2-user-notes').fill('EUR-USD active-key draft');

        await navigateTo(page, '/fx/EUR-GBP');
        await expect(page.getByTestId('fx-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
        await expect(fxPanel.menu).toBeHidden({timeout: 2_000});
        const newFxPanel = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-v2-task-selected-name')).toHaveText('FX Trend Review');
        await expect(page.getByTestId('ai-export-v2-user-notes')).toHaveValue('');
        await selectAnalysis(page, 'snapshot');
        await page.getByTestId('ai-export-v2-detail-compact').click();
        await newFxPanel.trigger.click();
        await expect(newFxPanel.menu).toBeHidden({timeout: 2_000});

        await navigateTo(page, assetPath);
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
        const restoredAssetPanel = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-v2-task-selected-name')).toHaveText('Asset Trend Analysis');
        await expect(page.getByTestId('ai-export-v2-detail-full')).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('ai-export-v2-user-notes')).toHaveValue('Asset-only draft');
        await restoredAssetPanel.trigger.click();
        await expect(restoredAssetPanel.menu).toBeHidden({timeout: 2_000});

        await navigateTo(page, '/fx/USD-EUR');
        await expect(page.getByTestId('fx-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
        const restoredFxPanel = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-v2-task-selected-name')).toHaveText('FX Conversion Timing Context');
        await expect(page.getByTestId('ai-export-v2-detail-full')).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('ai-export-v2-user-notes')).toHaveValue('EUR-USD active-key draft');
        await restoredFxPanel.trigger.click();
        await expect(restoredFxPanel.menu).toBeHidden({timeout: 2_000});
    });

    test('exports data-only Snapshot choices across all supported surfaces', async ({page}) => {
        await test.step('Dashboard', async () => {
            await navigateTo(page, '/dashboard');
            await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: UI_TIMEOUT});
            await exportSnapshotAndAssert(page, {
                domain: 'portfolio',
                task: 'portfolio_description',
                omitBrokerIds: true,
            });
        });

        await test.step('Asset Detail', async () => {
            await navigateTo(page, '/assets');
            await expect(page.getByTestId('assets-page')).toBeVisible({timeout: UI_TIMEOUT});
            const assetEntry = await requireSeededEntry(page, [page.getByTestId(/^asset-card-/).first(), page.getByTestId(/^asset-row-/).first()], 'No seeded asset card or row found on /assets.');
            await assetEntry.click();
            await expect(page).toHaveURL(/\/assets\/\d+(?:[?#].*)?$/, {timeout: UI_TIMEOUT});
            await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
            await exportSnapshotAndAssert(page, {
                domain: 'asset',
                task: 'asset_snapshot',
                assetId: numericScopeId(page, 'assets'),
            });
        });

        await test.step('FX Detail', async () => {
            await navigateTo(page, '/fx/EUR-USD');
            await expect(page.getByTestId('fx-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
            await exportSnapshotAndAssert(page, {
                domain: 'fx',
                task: 'fx_trend_review',
            });
        });

        await test.step('Broker Detail', async () => {
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: UI_TIMEOUT});
            const brokerCard = await requireSeededEntry(page, [page.getByTestId(/^broker-card-/).first()], 'No seeded broker card found on /brokers.');
            await brokerCard.click();
            await expect(page).toHaveURL(/\/brokers\/\d+(?:[?#].*)?$/, {timeout: UI_TIMEOUT});
            await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
            await expect(page.getByTestId('broker-name')).toBeVisible({timeout: UI_TIMEOUT});
            const panel = await openAiExportPanel(page);
            await assertDocsPopup(page, '/mkdocs/user/ai-export/broker/');
            await panel.menu.getByTestId('ai-export-v2-task-select-button').click();
            await expect(page.getByTestId('ai-export-v2-task-option-broker_fifo_lot_review')).toContainText('FIFO Lot Review');
            await page.keyboard.press('Escape');
            await panel.trigger.click();
            await exportSnapshotAndAssert(page, {
                domain: 'broker',
                task: 'broker_review',
                brokerId: numericScopeId(page, 'brokers'),
            });
        });
    });

    test('exports a real Dashboard analysis with locale-derived language and notes', async ({page}) => {
        await navigateTo(page, '/dashboard');
        await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: UI_TIMEOUT});
        const {trigger, menu} = await openAiExportPanel(page);
        await selectAnalysis(page, 'pac_planning');
        await assertRemovedControlsAbsent(page);

        const notes = 'Compare recurring-investment options while keeping fees visible.';
        await page.getByTestId('ai-export-v2-user-notes').fill(notes);

        const requestPromise = page.waitForRequest(isSnapshotPost, {timeout: UI_TIMEOUT});
        const responsePromise = page.waitForResponse((response) => isSnapshotPost(response.request()), {timeout: RESPONSE_TIMEOUT});
        await page.getByTestId('ai-export-v2-export-button').click();
        await expect(menu).toBeHidden({timeout: 3_000});
        await expect(trigger).toBeFocused({timeout: 3_000});

        const [request, response] = await Promise.all([requestPromise, responsePromise]);
        const failureBody = response.status() === 200 ? '' : await response.text();
        expect(response.status(), failureBody).toBe(200);
        expect(request.postDataJSON()).toMatchObject({
            domain: 'portfolio',
            task: 'pac_planning',
            detail_level: 'standard',
        });
        const requestBody = request.postDataJSON();
        expect(requestBody.technical_window.end).toBe(requestBody.date_range.end);
        expect(requestBody.technical_window.start).toMatch(/^\d{4}-\d{2}-\d{2}$/);

        const clipboardText = await waitForClipboard(page, ['Task Instructions', 'Optional User Notes', notes, 'Please provide your answer in: English.'], 'Clipboard did not receive the full Dashboard analysis prompt');
        expect(clipboardText).toContain('Snapshot Data');
    });
});
