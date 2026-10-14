/**
 * FX Data Editor — E2E Tests
 *
 * Tests the data editor section in the FX detail page.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated with EUR-USD data
 */

import {expect, test} from '../fixtures/playwright';
import {login, setLanguage} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {t} from '../fixtures/i18n-data';
import {goToFxDetailPage} from './fx-helpers';

test.describe('FX Data Editor', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Open editor via edit button
    // ========================================================================
    test('can open data editor', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-edit-btn').click();
        await expect(page.getByTestId('fx-detail-editor-panel')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Data table has rows
    // ========================================================================
    test('data editor table has rows', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-edit-btn').click();
        const editorPanel = page.getByTestId('fx-detail-editor-panel');
        await expect(editorPanel).toBeVisible();

        // Look for table rows within the editor
        const rows = editorPanel.locator('table tbody tr, [data-testid*="editor-row"]');
        const count = await rows.count();
        expect(count).toBeGreaterThan(0);
    });

    // ========================================================================
    // Test 7: Close editor (cancel) resets state
    // ========================================================================
    test('closing editor hides the panel', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-edit-btn').click();
        await expect(page.getByTestId('fx-detail-editor-panel')).toBeVisible();

        // Click the edit button again to close (toggle)
        await page.getByTestId('fx-detail-edit-btn').click();
        await expect(page.getByTestId('fx-detail-editor-panel')).not.toBeVisible();
    });

    // ========================================================================
    // Test 8: The editor's own buttons and the CSV import title, in Italian
    // ========================================================================
    /**
     * The save/cancel bar under the rate editor is written in English straight
     * into FxDataEditorSection, while the shared data editor already carries its
     * sentences (`dataEditor.save` with the count, `dataEditor.saving`) and
     * `common.cancel` exists. Every expected label is read from it.json, never
     * typed here; the positive control is a label of the same editor that is
     * already the catalogue's, so an English label next to it is a hard-coded one.
     *
     * "Saving" lives only while a save is in flight, so the save is held at the
     * network edge and then refused: the label can be read for as long as the test
     * needs, and the deletion it carries never reaches the shared EUR-USD rates.
     */
    test('words the save/cancel bar and the CSV import title from the active catalogue', async ({page}) => {
        await setLanguage(page, 'it');
        await goToFxDetailPage(page, 'EUR-USD');

        await page.getByTestId('fx-detail-edit-btn').click();
        const panel = page.getByTestId('fx-detail-editor-panel');
        await expect(panel).toBeVisible();

        // Positive control: this editor already takes its toolbar label from it.json.
        const importButton = page.getByTestId('fx-data-import-btn');
        await expect(importButton).toHaveText(t('it', 'dataEditor.importCsv'));

        const save = page.getByTestId('fx-editor-save-btn');
        const cancel = page.getByTestId('fx-editor-cancel-btn');
        const saveLabel = (n: number) => t('it', 'dataEditor.save').replace('{n}', String(n));
        // A label renders with its button and nothing loads in between, so a short
        // wait is honest — and keeps four soft reds inside the test's budget.
        await expect.soft(save, 'save, nothing to save').toHaveText(saveLabel(0), {timeout: 2_000});
        await expect.soft(cancel, 'cancel').toHaveText(t('it', 'common.cancel'), {timeout: 2_000});

        // The CSV import modal opened from the same editor names itself from the catalogue.
        await importButton.click();
        const importModal = page.getByTestId('data-import-modal');
        await expect(importModal).toBeVisible();
        await expect.soft(importModal.getByTestId('data-import-modal-header').getByRole('heading', {level: 2}), 'CSV import title').toHaveText(t('it', 'csvImport.title'), {timeout: 2_000});
        await page.keyboard.press('Escape');
        await expect(importModal).toBeHidden();

        // One row marked for deletion makes the count 1. Any row serves: the mark is
        // local until saved, and the save below never reaches the server.
        const kebab = panel.locator('[data-testid^="row-actions-"]').first();
        await expect(kebab, 'EUR-USD shows no rate in the editor: check populate_mock_data.py').toBeVisible();
        await kebab.click();
        await expect(page.getByTestId('context-menu')).toBeVisible();
        await page.getByTestId('context-menu-action-delete').click();
        await expect(save).toBeEnabled();
        await expect.soft(save, 'save, one change').toHaveText(saveLabel(1), {timeout: 2_000});

        // Hold the save at the network edge, read the in-flight label, then refuse it.
        let release!: () => void;
        const held = new Promise<void>((resolve) => (release = resolve));
        let arrived!: () => void;
        const reached = new Promise<void>((resolve) => (arrived = resolve));
        const rates = '**/api/v1/fx/currencies/rate';
        await page.route(rates, async (route) => {
            if (route.request().method() !== 'DELETE') return route.fallback();
            arrived();
            await held;
            await route.abort();
        });
        try {
            await save.click();
            await reached;
            await expect.soft(save, 'save, in flight').toHaveText(t('it', 'dataEditor.saving'), {timeout: 2_000});
        } finally {
            release();
        }
        // Refused: the save is over and the mark still pending. Nothing to restore —
        // the deletion only ever lived in this page, which the test discards.
        await expect(save).toBeEnabled();
        await page.unroute(rates);
    });
});
