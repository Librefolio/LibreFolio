/**
 * E2E Tests for Select Components
 *
 * Tests the unified Select component family:
 * - SimpleSelect (LanguageSelector, SettingSelect)
 * - SearchSelect (CurrencySelect, ImportPluginSelect)
 * - BrokerSearchSelect (Files upload modal)
 *
 * Focus areas:
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 * - Click outside to close
 * - Search filtering
 * - Option selection
 * - Accessibility
 */
import {expect, test} from '@playwright/test';
import {login} from './fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from './fixtures/test-users';

test.describe('Select Components', () => {

    test.describe('LanguageSelector (SimpleSelect style)', () => {

        test('opens dropdown on click', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});

            await page.getByTestId('language-selector-button').click();

            // All language options should be visible
            await expect(page.getByRole('menuitem', {name: /English/})).toBeVisible();
            await expect(page.getByRole('menuitem', {name: /Italiano/})).toBeVisible();
            await expect(page.getByRole('menuitem', {name: /Français/})).toBeVisible();
            await expect(page.getByRole('menuitem', {name: /Español/})).toBeVisible();
        });

        test('closes dropdown on click outside', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});

            await page.getByTestId('language-selector-button').click();
            await expect(page.getByRole('menuitem', {name: /English/})).toBeVisible();

            // Click outside the dropdown
            await page.locator('body').click({position: {x: 10, y: 10}});

            // Dropdown should close
            await expect(page.getByRole('menuitem', {name: /English/})).not.toBeVisible();
        });

        test('closes dropdown on Escape key', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});

            await page.getByTestId('language-selector-button').click();
            await expect(page.getByRole('menuitem', {name: /English/})).toBeVisible();

            await page.keyboard.press('Escape');

            await expect(page.getByRole('menuitem', {name: /English/})).not.toBeVisible();
        });

        test('selects language and updates UI', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});

            // Switch to Italian
            await page.getByTestId('language-selector-button').click();
            await page.getByRole('menuitem', {name: /Italiano/}).click();

            // Login button should now be in Italian
            await expect(page.getByTestId('login-submit')).toContainText('Accedi');

            // Switch back to English
            await page.getByTestId('language-selector-button').click();
            await page.getByRole('menuitem', {name: /English/}).click();

            await expect(page.getByTestId('login-submit')).toContainText('Login');
        });
    });

    test.describe('SearchSelect (Currency Selector in Settings)', () => {

        test.beforeEach(async ({page}) => {
            await login(page, TEST_USER);
            await page.goto('/settings');
            // Navigate to Preferences tab
            const prefsTab = page.getByRole('tab').filter({hasText: /Preferences|Preferenze/i});
            await prefsTab.click();
            await page.waitForTimeout(500);
        });

        test('currency select opens with search field', async ({page}) => {
            // Find currency select container and click the combobox trigger
            const currencySelect = page.getByTestId('preference-currency');
            await expect(currencySelect).toBeVisible({timeout: 5000});

            // Click the combobox trigger (div with role="combobox")
            await currencySelect.locator('[role="combobox"]').click();

            // Search input should be visible
            const searchInput = page.locator('input[type="text"]');
            await expect(searchInput.first()).toBeVisible({timeout: 3000});
        });

        test('currency select shows options in listbox', async ({page}) => {
            const currencySelect = page.getByTestId('preference-currency');
            await currencySelect.locator('[role="combobox"]').click();

            // Should show listbox with options
            await expect(page.locator('[role="listbox"]')).toBeVisible({timeout: 3000});
        });

        test('currency select can close with Escape', async ({page}) => {
            const currencySelect = page.getByTestId('preference-currency');
            await currencySelect.locator('[role="combobox"]').click();

            // Listbox should be visible
            await expect(page.locator('[role="listbox"]')).toBeVisible({timeout: 3000});

            // Press Escape to close
            await page.keyboard.press('Escape');

            // Listbox should be hidden
            await expect(page.locator('[role="listbox"]')).not.toBeVisible({timeout: 2000});
        });
    });

    test.describe('ImportPluginSelect (Broker Form)', () => {

        test.beforeEach(async ({page}) => {
            await login(page, TEST_USER);
            await page.goto('/brokers');
            // Open create broker modal
            await page.getByTestId('add-broker-button').click();
            await expect(page.getByTestId('broker-modal')).toBeVisible({timeout: 5000});
        });

        test('plugin select is visible in broker form', async ({page}) => {
            // Find plugin select
            const pluginSelect = page.getByTestId('import-plugin-select');
            await expect(pluginSelect).toBeVisible({timeout: 3000});
        });

        test('plugin select opens dropdown with listbox', async ({page}) => {
            const pluginSelect = page.getByTestId('import-plugin-select');
            await pluginSelect.locator('[role="combobox"]').click();

            // Should show listbox
            await expect(page.locator('[role="listbox"]')).toBeVisible({timeout: 3000});
        });

        test('plugin select shows search input when opened', async ({page}) => {
            const pluginSelect = page.getByTestId('import-plugin-select');
            await pluginSelect.locator('[role="combobox"]').click();

            // Should show search input (inline search mode)
            const searchInput = pluginSelect.locator('input[type="text"]');
            await expect(searchInput).toBeVisible({timeout: 3000});
        });

        test('plugin select can be closed with Escape', async ({page}) => {
            const pluginSelect = page.getByTestId('import-plugin-select');
            await pluginSelect.locator('[role="combobox"]').click();

            // Listbox should be visible
            await expect(page.locator('[role="listbox"]')).toBeVisible({timeout: 3000});

            // Press Escape
            await page.keyboard.press('Escape');

            // Listbox should be hidden
            await expect(page.locator('[role="listbox"]')).not.toBeVisible({timeout: 2000});
        });
    });

    test.describe('Global Settings Selects (Admin)', () => {

        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
            await page.goto('/settings');
            // Navigate to Global Settings tab (admin only) - look for Shield icon or text
            const globalTab = page.getByRole('tab').filter({hasText: /Global|Globali|Admin/i});
            await expect(globalTab).toBeVisible({timeout: 5000});
            await globalTab.click();
            await page.waitForTimeout(500);
        });

        test('global settings tab loads for admin', async ({page}) => {
            // Verify the global settings tab content is visible
            await expect(page.getByTestId('global-settings-tab')).toBeVisible({timeout: 5000});
        });

        test('global settings has interactive elements', async ({page}) => {
            const globalTab = page.getByTestId('global-settings-tab');
            await expect(globalTab).toBeVisible({timeout: 5000});

            // Should have some interactive elements (buttons, inputs, selects)
            const interactiveElements = globalTab.locator('button, input, select, [role="combobox"]');
            const count = await interactiveElements.count();

            // Should have at least some interactive elements
            expect(count).toBeGreaterThan(0);
        });
    });

    test.describe('BrokerSearchSelect (Files Page)', () => {

        test.beforeEach(async ({page}) => {
            await login(page, TEST_USER);
            await page.goto('/files');
        });

        test('files page loads with tab navigation', async ({page}) => {
            // Verify BRIM tab exists
            const brimTab = page.getByRole('tab', {name: /Broker|BRIM/i});
            await expect(brimTab).toBeVisible();

            // Can switch to BRIM tab
            await brimTab.click();
            await expect(brimTab).toHaveAttribute('aria-selected', 'true');
        });
    });

    test.describe('Accessibility', () => {

        test('language selector has proper menu role', async ({page}) => {
            await page.goto('/');
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 3000});

            const button = page.getByTestId('language-selector-button');
            await expect(button).toBeVisible();

            // When opened, dropdown should have role="menu"
            await button.click();
            await expect(page.locator('[role="menu"]')).toBeVisible();
        });

        test('search select has listbox role when open', async ({page}) => {
            await login(page, TEST_USER);
            await page.goto('/settings');
            const prefsTab = page.getByRole('tab').filter({hasText: /Preferences|Preferenze/i});
            await prefsTab.click();
            await page.waitForTimeout(500);

            const currencySelect = page.getByTestId('preference-currency');
            await currencySelect.locator('[role="combobox"]').click();

            // Should have listbox role
            await expect(page.locator('[role="listbox"]')).toBeVisible({timeout: 3000});
        });
    });
});
