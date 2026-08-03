import {expect, test, type Page} from '@playwright/test';

import {login, logout, navigateTo, openMobileMenu, setLanguage} from '../fixtures/auth-helpers';
import {TEST_USER, TEST_USER_2} from '../fixtures/test-users';
import {configureCustomPeriod, expectCustomPeriod, exportCurrentSelection, gotoDashboard, gotoFirstAsset, gotoFirstBroker, gotoFx, openAiExportPanel, selectAiExportSelection, setupAiExportPage, waitForClipboard} from './helpers';

interface DraftExpectation {
    readonly kind: 'dataset' | 'analysis';
    readonly id: string;
    readonly label: string;
    readonly detail: 'compact' | 'standard' | 'full';
    readonly notes?: string;
    readonly period?: '3m' | '6m' | '1y';
    readonly customPeriod?: {
        readonly amount: number;
        readonly unit: 'days' | 'weeks' | 'months' | 'years';
    };
}

async function waitForStoredDraft(page: Page, draft: DraftExpectation): Promise<void> {
    await expect
        .poll(
            () =>
                page.evaluate((expected) => {
                    for (let index = 0; index < localStorage.length; index += 1) {
                        const key = localStorage.key(index);
                        if (!key?.includes('_ai_export_v2_')) continue;
                        const value = localStorage.getItem(key);
                        if (!value) continue;
                        try {
                            const stored = JSON.parse(value) as {
                                selectionKind?: string;
                                selectionId?: string;
                                detailLevel?: string;
                                notes?: string;
                                period?: {preset?: string; customAmount?: number; customUnit?: string};
                            };
                            if (stored.selectionKind !== expected.kind || stored.selectionId !== expected.id || stored.detailLevel !== expected.detail) continue;
                            if (expected.notes !== undefined && stored.notes !== expected.notes) continue;
                            if (expected.period !== undefined && stored.period?.preset !== expected.period) continue;
                            if (expected.customPeriod && (stored.period?.preset !== 'custom' || stored.period.customAmount !== expected.customPeriod.amount || stored.period.customUnit !== expected.customPeriod.unit)) continue;
                            return true;
                        } catch {
                            continue;
                        }
                    }
                    return false;
                }, draft),
            {timeout: 2_000, intervals: [50, 100, 250], message: `AI Export did not persist ${draft.id}`},
        )
        .toBe(true);
}

async function saveDraft(page: Page, draft: DraftExpectation): Promise<void> {
    const panel = await openAiExportPanel(page);
    await selectAiExportSelection(page, draft.kind, draft.id);
    await page.getByTestId(`ai-export-detail-${draft.detail}`).click();
    if (draft.customPeriod) await configureCustomPeriod(page, draft.customPeriod.amount, draft.customPeriod.unit);
    else if (draft.period) await page.getByTestId(`ai-export-period-${draft.period}`).click();
    if (draft.notes !== undefined) await page.getByTestId('ai-export-user-notes').fill(draft.notes);
    await waitForStoredDraft(page, draft);
    await page.keyboard.press('Escape');
    await expect(panel.menu).toBeHidden({timeout: 2_000});
}

async function expectDraft(page: Page, draft: DraftExpectation): Promise<void> {
    const panel = await openAiExportPanel(page);
    await expect(page.getByTestId('ai-export-selection-button')).toContainText(draft.label, {timeout: 2_000});
    await expect(page.getByTestId(`ai-export-detail-${draft.detail}`)).toHaveAttribute('aria-pressed', 'true', {timeout: 2_000});
    if (draft.customPeriod) await expectCustomPeriod(page, draft.customPeriod.amount, draft.customPeriod.unit);
    else if (draft.period) await expect(page.getByTestId(`ai-export-period-${draft.period}`)).toHaveAttribute('aria-pressed', 'true', {timeout: 2_000});
    if (draft.notes !== undefined) await expect(page.getByTestId('ai-export-user-notes')).toHaveValue(draft.notes, {timeout: 2_000});
    await page.keyboard.press('Escape');
    await expect(panel.menu).toBeHidden({timeout: 2_000});
}

async function switchUser(page: Page, user: typeof TEST_USER): Promise<void> {
    await openMobileMenu(page);
    await logout(page);
    await login(page, user);
    await setLanguage(page, 'en');
}

test.setTimeout(120_000);

test.describe('AI Export contextual memory', () => {
    test.beforeEach(async ({context, page}) => {
        await context.grantPermissions(['clipboard-read', 'clipboard-write']);
        await setupAiExportPage(page);
    });

    test('isolates Portfolio, Broker, and Asset drafts with detail, period, and notes', async ({page}) => {
        const portfolioDraft: DraftExpectation = {
            kind: 'analysis',
            id: 'portfolio.rebalancing',
            label: 'Portfolio Rebalancing',
            detail: 'full',
            notes: 'Portfolio-only allocation constraints.',
            customPeriod: {amount: 8, unit: 'weeks'},
        };
        const brokerDraft: DraftExpectation = {
            kind: 'analysis',
            id: 'broker.cost_efficiency',
            label: 'Broker Cost Efficiency',
            detail: 'compact',
            notes: 'Broker-only fee review.',
            period: '6m',
        };
        const assetDraft: DraftExpectation = {
            kind: 'analysis',
            id: 'asset.position_review',
            label: 'Position Review',
            detail: 'full',
            notes: 'Asset-only position context.',
            period: '1y',
        };

        await gotoDashboard(page);
        await saveDraft(page, portfolioDraft);
        const brokerPath = await gotoFirstBroker(page);
        await saveDraft(page, brokerDraft);
        const assetPath = await gotoFirstAsset(page);
        await saveDraft(page, assetDraft);

        await gotoDashboard(page);
        await expectDraft(page, portfolioDraft);
        await navigateTo(page, brokerPath);
        await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 8_000});
        await expectDraft(page, brokerDraft);
        await navigateTo(page, assetPath);
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 8_000});
        await expectDraft(page, assetDraft);
    });

    test('namespaces Portfolio memory by authenticated user', async ({page}) => {
        const userOneDraft: DraftExpectation = {
            kind: 'analysis',
            id: 'portfolio.rebalancing',
            label: 'Portfolio Rebalancing',
            detail: 'full',
            notes: 'USER_ONE_AI_EXPORT_MEMORY',
            period: '1y',
        };
        const userTwoDraft: DraftExpectation = {
            kind: 'analysis',
            id: 'portfolio.description',
            label: 'Portfolio Description',
            detail: 'compact',
            notes: 'USER_TWO_AI_EXPORT_MEMORY',
            period: '6m',
        };

        await gotoDashboard(page);
        await saveDraft(page, userOneDraft);

        await switchUser(page, TEST_USER_2);
        await gotoDashboard(page);
        const userTwoDefault = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-selection-button')).toContainText('Recurring Investment Plan', {timeout: 2_000});
        await expect(page.getByTestId('ai-export-user-notes')).toHaveValue('');
        await page.keyboard.press('Escape');
        await expect(userTwoDefault.menu).toBeHidden({timeout: 2_000});
        await saveDraft(page, userTwoDraft);

        await switchUser(page, TEST_USER);
        await gotoDashboard(page);
        await expectDraft(page, userOneDraft);
    });

    test('shares memory across canonical FX routes but not other FX pairs', async ({page}) => {
        const canonicalDraft: DraftExpectation = {
            kind: 'analysis',
            id: 'fx.conversion_timing',
            label: 'FX Conversion Timing',
            detail: 'full',
            notes: 'EUR-USD canonical draft.',
            customPeriod: {amount: 9, unit: 'weeks'},
        };

        await gotoFx(page, 'EUR-USD');
        await saveDraft(page, canonicalDraft);

        await gotoFx(page, 'EUR-GBP');
        const otherPair = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-selection-button')).toContainText('FX Trend Review', {timeout: 2_000});
        await expect(page.getByTestId('ai-export-user-notes')).toHaveValue('');
        await page.keyboard.press('Escape');
        await expect(otherPair.menu).toBeHidden({timeout: 2_000});

        await gotoFx(page, 'USD-EUR');
        await expectDraft(page, canonicalDraft);
    });

    test('retains Analysis notes while Dataset export never copies them', async ({page}) => {
        await gotoDashboard(page);
        const hiddenNote = 'ANALYSIS_ONLY_NOTE_5E31';
        await openAiExportPanel(page);
        await selectAiExportSelection(page, 'analysis', 'portfolio.rebalancing');
        await page.getByTestId('ai-export-user-notes').fill(hiddenNote);
        await waitForStoredDraft(page, {
            kind: 'analysis',
            id: 'portfolio.rebalancing',
            label: 'Portfolio Rebalancing',
            detail: 'standard',
            notes: hiddenNote,
            period: '3m',
        });

        await selectAiExportSelection(page, 'dataset', 'portfolio.overview');
        await expect(page.getByTestId('ai-export-user-notes')).toHaveCount(0);
        await page.getByTestId('ai-export-detail-compact').click();
        await exportCurrentSelection(page);

        const clipboard = await waitForClipboard(page, ['Snapshot Metadata and Dataset Manifest', 'Snapshot Data'], 'Dataset clipboard was not populated');
        expect(clipboard).not.toContain(hiddenNote);
        expect(clipboard).not.toContain('Analysis Objective');
        expect(clipboard).not.toContain('Response Contract');
        expect(clipboard).not.toContain('User Notes');

        const reopened = await openAiExportPanel(page);
        await selectAiExportSelection(page, 'analysis', 'portfolio.rebalancing');
        await expect(page.getByTestId('ai-export-user-notes')).toHaveValue(hiddenNote, {timeout: 2_000});
        await page.keyboard.press('Escape');
        await expect(reopened.menu).toBeHidden({timeout: 2_000});
    });
});
