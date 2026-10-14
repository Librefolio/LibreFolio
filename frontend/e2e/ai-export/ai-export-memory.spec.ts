import {expect, test, type Page} from '../fixtures/playwright';

import {waitForSettled} from '../fixtures/app-events';
import {login, logout, navigateTo, openMobileMenu, setLanguage} from '../fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER, TEST_USER_2} from '../fixtures/test-users';
import {API_TIMEOUT, configureCustomPeriod, expectCustomPeriod, exportCurrentSelection, gotoDashboard, gotoFirstAsset, gotoFirstBroker, gotoFx, openAiExportPanel, selectAiExportSelection, setupAiExportPage, waitForClipboard} from './helpers';

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

async function saveDraft(page: Page, draft: DraftExpectation): Promise<void> {
    const panel = await openAiExportPanel(page);
    await selectAiExportSelection(page, draft.kind, draft.id);
    await page.getByTestId(`ai-export-detail-${draft.detail}`).click();
    if (draft.customPeriod) await configureCustomPeriod(page, draft.customPeriod.amount, draft.customPeriod.unit);
    else if (draft.period) await page.getByTestId(`ai-export-period-${draft.period}`).click();
    if (draft.notes !== undefined) await page.getByTestId('ai-export-user-notes').fill(draft.notes);
    await expect(page.getByTestId('ai-export-selection-button')).toContainText(draft.label, {timeout: 2_000});
    await expect(page.getByTestId(`ai-export-detail-${draft.detail}`)).toHaveAttribute('aria-pressed', 'true', {timeout: 2_000});
    if (draft.notes !== undefined) await expect(page.getByTestId('ai-export-user-notes')).toHaveValue(draft.notes, {timeout: 2_000});
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

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

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
            id: 'broker.fiscal_lots',
            label: 'Capital-Loss Offset Strategies',
            detail: 'compact',
            notes: 'Broker-only tax-loss constraints.',
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

    test('resets Portfolio memory on every new login session', async ({page}) => {
        const userOneDraft: DraftExpectation = {
            kind: 'analysis',
            id: 'portfolio.rebalancing',
            label: 'Portfolio Rebalancing',
            detail: 'full',
            notes: 'USER_ONE_AI_EXPORT_MEMORY',
            period: '1y',
        };
        const adminDraft: DraftExpectation = {
            kind: 'analysis',
            id: 'portfolio.performance_market_drivers',
            label: 'Portfolio Performance & Market Drivers',
            detail: 'compact',
            notes: 'ADMIN_AI_EXPORT_MEMORY',
            period: '6m',
        };
        // The brokers the Dashboard aggregates, for whoever is logged in on the page (`page.request` carries its
        // cookies): OWNER with a share unset or above zero, as `getOwnedBrokers()` keeps them (brokerStore.ts).
        const ownedBrokerIds = async (): Promise<number[]> => {
            const listed = await page.request.get('/api/v1/brokers');
            expect(listed.ok(), `GET /api/v1/brokers → HTTP ${listed.status()}`).toBe(true);
            const {items} = (await listed.json()) as {items?: {id: number; user_role?: string | null; user_share_percentage?: string | number | null}[]};
            return (items ?? []).filter((broker) => broker.user_role === 'OWNER' && (broker.user_share_percentage == null || Number.parseFloat(String(broker.user_share_percentage)) > 0)).map((broker) => broker.id);
        };

        await gotoDashboard(page);
        await saveDraft(page, userOneDraft);

        // F2: the Dashboard's AI Export opens only on the brokers the user owns — a portfolio export without them is
        // widened by the backend to every broker the user can see. TEST_USER_2 owns none, so once the page has settled
        // its trigger must still be disabled. Settled means both things the trigger waits for are in: the broker list
        // (`data-busy="false"`) and the AI-export catalogue, which a cold load always asks for. Nothing on the page
        // publishes "catalogue applied": the catalogue response having finished is the nearest signal there is. The
        // login left a live Dashboard behind; it is unloaded first, so its own catalogue request cannot pass for the
        // new document's.
        await switchUser(page, TEST_USER_2);
        const ownedByUserTwo = await ownedBrokerIds();
        if (ownedByUserTwo.length > 0) throw new Error(`${TEST_USER_2.username} owns broker(s) [${ownedByUserTwo.join(', ')}] with a share above zero, but this step needs a user who owns none (seeded VIEWER at 0%). Check populate_mock_data.py seeding.`);
        await page.goto('about:blank');
        const catalogAnswered = page.waitForResponse((response) => response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/v1/ai-export/catalog', {timeout: API_TIMEOUT});
        // Awaited below; the empty catch only keeps a failure in between from also surfacing as an unhandled rejection.
        void catalogAnswered.catch(() => undefined);
        await gotoDashboard(page);
        const catalog = await catalogAnswered;
        expect(catalog.status(), catalog.status() === 200 ? '' : await catalog.text()).toBe(200);
        expect(await catalog.finished(), 'the AI-export catalogue never finished loading').toBeNull();
        await waitForSettled(page.getByTestId('dashboard-page'));
        await expect(page.getByTestId('sync-button')).toBeEnabled();
        const trigger = page.getByTestId('ai-export-button');
        await expect(trigger).toBeVisible();
        await expect(trigger, `AI Export is enabled for ${TEST_USER_2.username}, who owns no broker: its export would leave without broker_ids, and the backend would widen it to every broker the user can see (F2)`).toBeDisabled();

        // The second session needs a user who can export: TEST_ADMIN owns every seeded broker. After login an admin's
        // browser asks GitHub for a newer release (updateCheck.ts) and, when there is one, opens a modal over the
        // page: the third party stays out of the test, and the probe fails closed, in silence.
        await page.route('https://api.github.com/**', (route) => route.abort());
        await switchUser(page, TEST_ADMIN);
        if ((await ownedBrokerIds()).length === 0) throw new Error(`${TEST_ADMIN.username} owns no broker with a share above zero, so its Dashboard cannot export. Check populate_mock_data.py seeding.`);
        await gotoDashboard(page);
        const adminDefault = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-selection-button')).toContainText('Recurring Investment Plan', {timeout: 2_000});
        await expect(page.getByTestId('ai-export-user-notes')).toHaveValue('');
        await page.keyboard.press('Escape');
        await expect(adminDefault.menu).toBeHidden({timeout: 2_000});
        await saveDraft(page, adminDraft);

        await switchUser(page, TEST_USER);
        await gotoDashboard(page);
        const userOneDefault = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-selection-button')).toContainText('Recurring Investment Plan', {timeout: 2_000});
        await expect(page.getByTestId('ai-export-detail-standard')).toHaveAttribute('aria-pressed', 'true', {timeout: 2_000});
        await expect(page.getByTestId('ai-export-period-3m')).toHaveAttribute('aria-pressed', 'true', {timeout: 2_000});
        await expect(page.getByTestId('ai-export-user-notes')).toHaveValue('');
        await page.keyboard.press('Escape');
        await expect(userOneDefault.menu).toBeHidden({timeout: 2_000});
    });

    test('shares memory across canonical FX routes but not other FX pairs', async ({page}) => {
        const canonicalDraft: DraftExpectation = {
            kind: 'analysis',
            id: 'fx.exposure_impact',
            label: 'FX Exposure Impact',
            detail: 'full',
            notes: 'EUR-USD canonical draft.',
            customPeriod: {amount: 9, unit: 'weeks'},
        };

        await gotoFx(page, 'EUR-USD');
        await saveDraft(page, canonicalDraft);

        await gotoFx(page, 'EUR-GBP');
        const otherPair = await openAiExportPanel(page);
        await expect(page.getByTestId('ai-export-selection-button')).toContainText('FX Pair Analysis', {timeout: 2_000});
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
        await expect(page.getByTestId('ai-export-user-notes')).toHaveValue(hiddenNote, {timeout: 2_000});

        await selectAiExportSelection(page, 'dataset', 'portfolio.overview_and_history');
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
