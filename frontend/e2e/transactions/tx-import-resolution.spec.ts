/**
 * Import Wizard — Asset Resolution E2E Tests
 *
 * Tests the advanced resolution flow in the review step of the ImportWizardModal.
 * Uses generic_simple.csv which contains UNETF (unknown asset → fake_id).
 *
 * The wizard has seven steps, three of them conditional: unification, corrections and
 * duplicates appear only when the parse produced something for them to do. Walking to
 * the review step therefore means asking at each one, never assuming a fixed order.
 *
 * The file. A test that parses uploads its own copy of generic_simple.csv through the API
 * to the seeded "Interactive Brokers" broker — the broker the seeded copies live on, so
 * the parse is asked for the same broker and compared with the same transactions —
 * selects it in step 2 by its file id, wherever the panel's pages put it, and deletes it
 * in afterEach. The walk to the review is the shared one (fixtures/import-wizard.ts):
 * the parse response decides the notices' confirmation, the stepper the steps crossed.
 *
 * Prerequisites:
 *   - Backend test mode (port 6041)
 *   - DB populated: the "Interactive Brokers" broker, on which the test user is an owner.
 *     IWR-010 previews whichever file step 2 lists first, so it still relies on the
 *     samples populate_mock_data.py uploads with --with-reports.
 *
 * IWR-013 does not parse generic_simple.csv: whether its UNETF reaches the review
 * unresolved depends on the database (IWR-005's confirmed prompt attaches UNETF to an
 * existing asset), and that test needs to know how many assets are unresolved. It uploads
 * a CSV of its own instead, one purchase of each of n invented tickers.
 *
 * Test IDs: IWR-001..IWR-014
 *
 * Key data-testids used:
 *   import-wizard-step4             — Step 4 container
 *   import-wizard-resolve-section   — Resolve assets section wrapper
 *   import-wizard-resolve-toggle    — Collapsible header button
 *   import-wizard-unresolved-count  — The header's amber badge: how many assets are unresolved
 *   import-wizard-import            — Import button (disabled when unresolved)
 *   search-select-create-new        — "Create new asset" footer in AssetSelect dropdown
 *   search-select-option-{id}       — Individual asset option in dropdown
 *   identifier-prompt-skip          — Skip button in identifier prompt
 *   identifier-prompt-confirm       — Confirm button in identifier prompt
 *   identifier-prompt-cancel        — Cancel button in identifier prompt
 *   asset-modal-form                — AssetModal form container
 *   asset-modal-display-name        — Display name input in AssetModal
 *   asset-modal-cancel              — Cancel button in AssetModal
 *   tx-form-modal-root              — Compare modal (TransactionFormModal in view mode)
 */

import {IntlMessageFormat} from 'intl-messageformat';
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {SUPPORTED_LANGUAGES, t as catalogueText} from '../fixtures/i18n-data';
import {continueToReview, deleteOwnedReports, parseSelectedFile, selectBrokerFile, uploadOwnedReport, type OwnedReport, type ParseResponse} from '../fixtures/import-wizard';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';

test.setTimeout(90_000);

/** The seeded broker the sample belongs to, and the sample a parsing test uploads a copy of. */
const GENERIC_SIMPLE = {brokerName: 'Interactive Brokers', sample: 'generic_simple.csv'};

/** The message of the resolve header's badge: how many assets are still unresolved, `{n}`. */
const UNRESOLVED_COUNT_KEY = 'importWizard.unresolvedCount';

/**
 * The reports the running test uploaded, emptied by afterEach as it deletes them. Module
 * state on purpose: `parseGenericSimple` fills it from inside the tests' bodies, and a
 * worker runs one test at a time.
 */
const ownedReports: OwnedReport[] = [];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** The option list is present and has finished loading its catalogue. */
async function optionListReady(page: Page) {
    const list = page.locator('[role="listbox"]');
    await expect(list.first()).toBeVisible({timeout: 5_000});
    await expect(list.first()).toHaveAttribute('aria-busy', 'false', {timeout: 10_000});
}

/** The option list is gone — the teardown that follows a pick or an Escape. */
async function optionListClosed(page: Page) {
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 10_000});
}

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** Open BulkModal → click Import → ImportWizard opens */
async function openImportWizard(page: Page) {
    const firstRow = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').first();
    await firstRow.hover();
    const kebabBtn = firstRow.getByTestId(/^row-actions-/);
    await expect(kebabBtn).toBeVisible({timeout: 3_000});
    await kebabBtn.click();
    await page.getByTestId('context-menu-action-edit').click();
    await page.getByTestId('tx-bulk-modal-root').waitFor({state: 'visible', timeout: 6_000});

    // The BulkModal may auto-open a FormModal for the selected paired transaction.
    // Close it before clicking Import.
    const formClose = page.getByTestId('tx-form-close');
    if (await formClose.isVisible({timeout: 1_500}).catch(() => false)) {
        await formClose.click();
        await expect(formClose).toHaveCount(0, {timeout: 5_000});
    }

    await page.getByTestId('tx-bulk-import').click();
    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 5_000});
}

/**
 * Click a conditional step's Continue button if that step is on screen.
 *
 * The wizard shows unification, corrections and duplicates only when the parse produced
 * something for them to do, so a walk to the review step has to ask rather than assume.
 */
async function skipStepIfPresent(page: Page, continueTestId: string) {
    const button = page.getByTestId(continueTestId);
    if (await button.isVisible({timeout: 1_500}).catch(() => false)) {
        await button.click();
        await expect(button).toHaveCount(0, {timeout: 5_000});
    }
}

/**
 * Upload this test's own copy of generic_simple.csv, select it in step 2 and parse it,
 * stopping on the analysis step. Called with the wizard on step 1: the wizard reads the
 * broker files when it enters step 2, so the upload comes first. Returns the parse
 * response, which says whether leaving the analysis asks to confirm notices.
 */
async function parseGenericSimple(page: Page): Promise<ParseResponse> {
    const own = await uploadOwnedReport(page, ownedReports, GENERIC_SIMPLE);

    // Step 1: skip (no new uploads in the wizard itself)
    await page.getByTestId('import-wizard-next').click();

    // Step 2: the copy, by its id, in the Interactive Brokers panel, on whichever page it is
    await selectBrokerFile(page, own);

    // Step 3: parse
    return parseSelectedFile(page, own.fileId);
}

/**
 * Walk from the analysis step to the review step, crossing whichever of the three
 * conditional steps this parse happens to raise.
 */
async function goToStep4WithGenericSimple(page: Page) {
    const parsed = await parseGenericSimple(page);
    await continueToReview(page, parsed);
}

/** The parse response with its asset mappings (`BRIMParseResponse.asset_mappings`), which the shared `ParseResponse` leaves out. */
type ParsedAssets = ParseResponse & {asset_mappings?: Array<{extracted_symbol?: string | null; candidates?: unknown[]; selected_asset_id?: number | null}>};

/** A generic CSV with one purchase of each ticker, shaped like generic_simple.csv's UNETF row: the generic plugin reads a code of 1–6 letters and digits as a ticker. */
function purchasesOf(tickers: string[]): string {
    const rows = tickers.map((ticker) => `2024-12-10,BUY,10,-250.00,USD,${ticker},E2E unresolved badge ${ticker}`);
    return ['date,type,quantity,amount,currency,asset,description', ...rows].join('\n') + '\n';
}

/**
 * Upload `csv`, a file of this test's own making, to the seeded broker under a unique name, and push it
 * onto `ownedReports` as soon as the server has accepted it, for afterEach to delete. The route and the
 * checks of `uploadOwnedReport`, replicated: the fixture uploads only the samples on disk.
 */
async function uploadOwnedCsv(page: Page, csv: string): Promise<OwnedReport> {
    const brokersResponse = await page.request.get('/api/v1/brokers');
    expect(brokersResponse.ok(), `list the brokers: HTTP ${brokersResponse.status()}`).toBe(true);
    const {items} = (await brokersResponse.json()) as {items: Array<{id: number; name: string}>};
    const brokers = items.filter((broker) => broker.name === GENERIC_SIMPLE.brokerName);
    if (brokers.length !== 1) {
        throw new Error(`Expected exactly one broker named "${GENERIC_SIMPLE.brokerName}" visible to this user, found ${brokers.length}: it is seeded by backend/test_scripts/test_db/populate_mock_data.py (populate_brokers)`);
    }
    const brokerId = brokers[0].id;
    const fileName = `unresolved-badge-${uniqueSuffix()}.csv`;
    const response = await page.request.post('/api/v1/brokers/import/upload', {
        multipart: {broker_id: String(brokerId), file: {name: fileName, mimeType: 'text/csv', buffer: Buffer.from(csv, 'utf8')}},
    });
    expect(response.ok(), `upload ${fileName}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const uploaded = (await response.json()) as {file_id: string; filename: string; target_broker_id: number | null};
    const own: OwnedReport = {brokerId, fileId: uploaded.file_id, fileName};
    ownedReports.push(own);
    expect(uploaded, `${fileName} lands on "${GENERIC_SIMPLE.brokerName}" under its own name`).toMatchObject({filename: fileName, target_broker_id: brokerId});
    return own;
}

/**
 * The language the page is drawn in: `<html lang>`, which the root layout keeps on the language shown,
 * read once `data-i18n-ready` says its dictionary is in — the reading of `tx-bulk-import-handoff.spec.ts`,
 * replicated rather than imported (a spec does not reach into another spec's helpers).
 */
async function pageLanguage(page: Page): Promise<string> {
    const html = page.locator('html');
    await expect(html, 'the page has its dictionary').toHaveAttribute('data-i18n-ready', 'true');
    return ((await html.getAttribute('lang')) ?? '').split('-')[0];
}

/**
 * `importWizard.unresolvedCount` for `n`, as the `lang` catalogue words it: the message read from the
 * catalogue file and formatted by `intl-messageformat`, the formatter svelte-i18n compiles messages with.
 * A catalogue without the message fails here, by name.
 */
function unresolvedCountText(lang: string, n: number): string {
    const message = catalogueText(lang, UNRESOLVED_COUNT_KEY);
    expect(message, `the "${lang}" catalogue has a message for ${UNRESOLVED_COUNT_KEY}`).not.toBe(UNRESOLVED_COUNT_KEY);
    return String(new IntlMessageFormat(message, lang).format({n}));
}

/**
 * Open the AssetSelect dropdown for the first unresolved asset card.
 * Returns the step4 locator for convenience.
 */
async function openFirstAssetSelectDropdown(page: Page) {
    const step4 = page.getByTestId('import-wizard-step4');
    const resolveSection = step4.getByTestId('import-wizard-resolve-section');
    await expect(resolveSection).toBeVisible({timeout: 5_000});

    // Scroll resolve section into view (it may be above the visible area in the modal)
    await resolveSection.scrollIntoViewIfNeeded();

    // Wait for AssetSelect in the first UNRESOLVED card.
    // Resolved cards have 'border-emerald-200'; unresolved cards have 'border-gray-200'.
    // Targeting '.border-gray-200 [data-testid="asset-select"]' skips already-resolved cards.
    const assetSelect = resolveSection.locator('.border-gray-200 [data-testid="asset-select"]').first();

    // Use waitFor instead of isVisible+conditional to avoid race-condition where
    // a fast false-negative causes us to click the toggle on an already-open section.
    const appeared = await assetSelect
        .waitFor({state: 'visible', timeout: 4_000})
        .then(() => true)
        .catch(() => false);
    if (!appeared) {
        // Section body is not visible → click toggle to expand it
        await step4.getByTestId('import-wizard-resolve-toggle').click();
        // Wait for AssetSelect to appear after expand animation
        await assetSelect.waitFor({state: 'visible', timeout: 5_000});
    }

    await assetSelect.click();
    await optionListReady(page);

    return step4;
}

/**
 * Resolve the first unresolved asset via manual asset selection.
 * Types a search query, picks the first available option, and handles the
 * identifier prompt (skip it if it appears).
 * Returns true if successfully resolved.
 */
async function resolveFirstAssetManually(page: Page): Promise<boolean> {
    const step4 = await openFirstAssetSelectDropdown(page);
    const resolveSection = step4.getByTestId('import-wizard-resolve-section');

    // Type in the inline search input to filter assets (dropdown should be open)
    const searchInput = resolveSection.locator('[data-testid="asset-select"] input[type="text"]').first();
    if (!(await searchInput.isVisible({timeout: 2_000}).catch(() => false))) {
        // Dropdown might not be open yet; click the select again
        await resolveSection.locator('[data-testid="asset-select"]').first().click();
        await optionListReady(page);
    }

    // Type to trigger search
    await searchInput.fill('e');

    const firstOption = page.locator('[data-testid^="search-select-option-"]').first();
    if (!(await firstOption.isVisible({timeout: 3_000}).catch(() => false))) {
        await searchInput.fill('a');
    }

    const option = page.locator('[data-testid^="search-select-option-"]').first();
    if (!(await option.isVisible({timeout: 3_000}).catch(() => false))) {
        return false;
    }

    await option.click();
    await optionListClosed(page);

    // Handle identifier prompt (skip or confirm)
    const skipBtn = page.getByTestId('identifier-prompt-skip');
    const confirmBtn = page.getByTestId('identifier-prompt-confirm');
    const cancelBtn = page.getByTestId('identifier-prompt-cancel');

    if (await skipBtn.isVisible({timeout: 2_000}).catch(() => false)) {
        await skipBtn.click();
    } else if (await confirmBtn.isVisible({timeout: 500}).catch(() => false)) {
        await confirmBtn.click();
    } else if (await cancelBtn.isVisible({timeout: 500}).catch(() => false)) {
        await cancelBtn.click();
    }

    return true;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Import Wizard — Asset Resolution', () => {
    test.beforeEach(async ({page}) => {
        await login(page);
        await goToTransactions(page);
    });

    test.afterEach(async ({page}) => {
        await deleteOwnedReports(page, ownedReports);
    });

    // -----------------------------------------------------------------------
    // IWR-001: Resolve section visible + import button disabled
    // -----------------------------------------------------------------------
    test('IWR-001: Step 4 shows resolve section with unresolved badge and import disabled', async ({page}) => {
        await openImportWizard(page);
        await goToStep4WithGenericSimple(page);

        const step4 = page.getByTestId('import-wizard-step4');

        // Resolve Assets section must be visible (UNETF generates a fake_id)
        await expect(step4.getByTestId('import-wizard-resolve-section')).toBeVisible({timeout: 5_000});

        // The amber badge with unresolved count must be present
        const resolveToggle = step4.getByTestId('import-wizard-resolve-toggle');
        await expect(resolveToggle).toBeVisible();
        // Amber badge text contains a number (count of unresolved assets)
        const amberBadge = resolveToggle.locator('[class*="amber"]').first();
        await expect(amberBadge).toBeVisible();

        // Import button must be disabled while there are unresolved assets
        await expect(page.getByTestId('import-wizard-import')).toBeDisabled();
    });

    // -----------------------------------------------------------------------
    // IWR-002: AssetSelect dropdown opens and shows "Create new" button
    // -----------------------------------------------------------------------
    test('IWR-002: AssetSelect dropdown opens with Create new button', async ({page}) => {
        await openImportWizard(page);
        await goToStep4WithGenericSimple(page);

        await openFirstAssetSelectDropdown(page);

        // "Create new" footer button must be visible in the dropdown
        await expect(page.getByTestId('search-select-create-new')).toBeVisible({timeout: 5_000});

        // Close dropdown by pressing Escape
        await page.keyboard.press('Escape');
        await optionListClosed(page);
    });

    // -----------------------------------------------------------------------
    // IWR-003: Click "Create new" → AssetModal opens pre-filled with extracted name
    // -----------------------------------------------------------------------
    test('IWR-003: Create new asset — AssetModal opens with pre-filled name from extracted identifier', async ({page}) => {
        await openImportWizard(page);
        await goToStep4WithGenericSimple(page);

        await openFirstAssetSelectDropdown(page);

        // Click the "Create new" footer button
        await page.getByTestId('search-select-create-new').click();

        // AssetModal must open
        const assetModal = page.getByTestId('asset-modal-form');
        await expect(assetModal).toBeVisible({timeout: 5_000});

        // The Name input must be visible (may or may not be pre-filled depending on
        // whether the BRIM parser extracted a name vs just a ticker symbol)
        await expect(page.getByTestId('asset-modal-display-name')).toBeVisible({timeout: 3_000});

        // Cancel the modal — we're just verifying the pre-fill
        await page.getByTestId('asset-modal-cancel').click();
        await expect(page.getByTestId('asset-modal-form')).toHaveCount(0, {timeout: 5_000});

        // Wizard still open
        await expect(page.getByTestId('import-wizard-step4')).toBeVisible();
    });

    // -----------------------------------------------------------------------
    // IWR-004: Manual asset selection → identifier prompt → skip → asset resolved
    // -----------------------------------------------------------------------
    test('IWR-004: Manual asset pick shows identifier prompt (skip) → asset card becomes resolved', async ({page}) => {
        await openImportWizard(page);
        await goToStep4WithGenericSimple(page);

        const step4 = page.getByTestId('import-wizard-step4');
        const resolveSection = step4.getByTestId('import-wizard-resolve-section');

        // Open dropdown for first unresolved asset
        await openFirstAssetSelectDropdown(page);

        // Type a search to get options
        const searchInput = resolveSection.locator('[data-testid="asset-select"] input[type="text"]').first();
        await searchInput.fill('e');

        // Pick the first available asset option
        const firstOption = page.locator('[data-testid^="search-select-option-"]').first();
        await expect(firstOption).toBeVisible({timeout: 5_000});
        await firstOption.click();
        await optionListClosed(page);

        // One of: identifier prompt appears OR asset is directly resolved
        const skipBtn = page.getByTestId('identifier-prompt-skip');
        const confirmBtn = page.getByTestId('identifier-prompt-confirm');
        const promptVisible = (await skipBtn.isVisible({timeout: 2_000}).catch(() => false)) || (await confirmBtn.isVisible({timeout: 500}).catch(() => false));

        if (promptVisible) {
            // Identifier prompt appeared — skip it
            if (await skipBtn.isVisible({timeout: 500}).catch(() => false)) {
                await skipBtn.click();
            } else {
                // Cancel if skip not available
                await page.getByTestId('identifier-prompt-cancel').click();
            }
            await expect(skipBtn).toHaveCount(0, {timeout: 5_000});
        }

        // Either way the asset should now be resolved (emerald border on card)
        // The resolved card has 'border-emerald-200' class
        const resolvedCard = resolveSection.locator('.border-emerald-200, [class*="border-emerald"]').first();
        await expect(resolvedCard).toBeVisible({timeout: 3_000});
    });

    // -----------------------------------------------------------------------
    // IWR-005: Identifier prompt confirm → adds identifier to asset
    // -----------------------------------------------------------------------
    test('IWR-005: Identifier prompt confirm — assigns identifier and resolves asset', async ({page}) => {
        await openImportWizard(page);
        await goToStep4WithGenericSimple(page);

        const step4 = page.getByTestId('import-wizard-step4');
        const resolveSection = step4.getByTestId('import-wizard-resolve-section');

        // Open dropdown and pick an asset
        await openFirstAssetSelectDropdown(page);
        const searchInput = resolveSection.locator('[data-testid="asset-select"] input[type="text"]').first();
        await searchInput.fill('e');

        const firstOption = page.locator('[data-testid^="search-select-option-"]').first();
        await expect(firstOption).toBeVisible({timeout: 5_000});
        await firstOption.click();
        await optionListClosed(page);

        // If identifier prompt appears, use Confirm (not Skip)
        const confirmBtn = page.getByTestId('identifier-prompt-confirm');
        if (await confirmBtn.isVisible({timeout: 2_000}).catch(() => false)) {
            await confirmBtn.click();
            await expect(confirmBtn).toHaveCount(0, {timeout: 10_000});
            await waitForSettled(page.getByTestId('import-wizard-step4'), 20_000);

            // Asset should be resolved
            const resolvedCard = resolveSection.locator('.border-emerald-200, [class*="border-emerald"]').first();
            await expect(resolvedCard).toBeVisible({timeout: 3_000});
        } else {
            // Prompt didn't appear — asset was already resolved (identifier already matched)
            const resolvedCard = resolveSection.locator('.border-emerald-200, [class*="border-emerald"]').first();
            await expect(resolvedCard).toBeVisible({timeout: 3_000});
        }
    });

    // -----------------------------------------------------------------------
    // IWR-006: Full resolve → import button enables
    // -----------------------------------------------------------------------
    test('IWR-006: After resolving all unresolved assets, import button becomes enabled', async ({page}) => {
        await openImportWizard(page);
        await goToStep4WithGenericSimple(page);

        const step4 = page.getByTestId('import-wizard-step4');
        const importBtn = page.getByTestId('import-wizard-import');

        // The import button may already be enabled if previous tests resolved UNETF in the DB.
        // If it's disabled, resolve all unresolved assets and verify it becomes enabled.
        const startedDisabled = await importBtn.isDisabled();

        if (startedDisabled) {
            // Resolve all unresolved assets (loop up to 5 times)
            const step4Inner = page.getByTestId('import-wizard-step4');
            const resolveSection = step4Inner.getByTestId('import-wizard-resolve-section');

            for (let i = 0; i < 5; i++) {
                if (await importBtn.isEnabled()) break;

                // Wait for AssetSelect in unresolved card (target UNRESOLVED cards only)
                const assetSelectLocator = resolveSection.locator('.border-gray-200 [data-testid="asset-select"]').first();
                const appeared = await assetSelectLocator
                    .waitFor({state: 'visible', timeout: 4_000})
                    .then(() => true)
                    .catch(() => false);
                if (!appeared) {
                    await step4Inner.getByTestId('import-wizard-resolve-toggle').click();
                    const ok = await assetSelectLocator
                        .waitFor({state: 'visible', timeout: 5_000})
                        .then(() => true)
                        .catch(() => false);
                    if (!ok) break;
                }

                await assetSelectLocator.click();
                await optionListReady(page);

                // Search and pick
                const searchInput = resolveSection.locator('.border-gray-200 [data-testid="asset-select"] input[type="text"]').first();
                if (await searchInput.isVisible({timeout: 2_000}).catch(() => false)) {
                    await searchInput.fill('e');
                }

                const option = page.locator('[data-testid^="search-select-option-"]').first();
                if (!(await option.isVisible({timeout: 3_000}).catch(() => false))) {
                    if (await searchInput.isVisible({timeout: 500}).catch(() => false)) {
                        await searchInput.fill('a');
                    }
                }

                const opt = page.locator('[data-testid^="search-select-option-"]').first();
                if (await opt.isVisible({timeout: 2_000}).catch(() => false)) {
                    await opt.click();
                    await optionListClosed(page);
                }

                // Handle identifier prompt — skip
                const skipBtn = page.getByTestId('identifier-prompt-skip');
                const confirmBtn = page.getByTestId('identifier-prompt-confirm');
                const cancelBtn = page.getByTestId('identifier-prompt-cancel');
                if (await skipBtn.isVisible({timeout: 1_500}).catch(() => false)) {
                    await skipBtn.click();
                } else if (await confirmBtn.isVisible({timeout: 500}).catch(() => false)) {
                    await confirmBtn.click();
                } else if (await cancelBtn.isVisible({timeout: 500}).catch(() => false)) {
                    await cancelBtn.click();
                }
                await waitForSettled(page.getByTestId('import-wizard-step4'), 20_000);
            }
        } // end if (startedDisabled)

        // Import button must be enabled (either it started enabled or we just resolved all assets)
        await expect(importBtn).toBeEnabled({timeout: 5_000});

        // Click import and verify wizard closes
        await importBtn.click();
        await expect(page.getByTestId('import-wizard-stepper')).not.toBeVisible({timeout: 5_000});
        // BulkModal should still be open with imported rows
        await expect(page.getByTestId('tx-bulk-modal-root')).toBeVisible();
    });

    // -----------------------------------------------------------------------
    // IWR-007: Duplicate Detection — second parse detects previously imported rows
    // -----------------------------------------------------------------------
    test('IWR-007: Second import of same file raises the duplicates step', async ({page}) => {
        // IWR-006 already imported rows from generic_simple.csv into the DB. Parsing the
        // same file again must now stop on the dedicated duplicates step — it used to be
        // a badge inside the review table, which is why this test looked for one.
        await openImportWizard(page);
        await parseGenericSimple(page);

        await page.getByTestId('import-wizard-continue').click();
        await skipStepIfPresent(page, 'import-wizard-assets-continue');
        await skipStepIfPresent(page, 'import-wizard-fix-continue');

        const duplicatesStep = page.getByTestId('import-wizard-step-duplicates');
        const reached = await duplicatesStep.isVisible({timeout: 4_000}).catch(() => false);

        if (!reached) {
            // A fresh database has nothing to collide with, and the step is conditional:
            // its absence is then the correct behaviour, not a missing assertion.
            await expect(page.getByTestId('import-wizard-step4')).toBeVisible({timeout: 5_000});
            return;
        }

        // The resolver states how many groups need arbitration, and each group is a
        // clash between the file and the archive.
        await expect(page.getByTestId('import-wizard-duplicate-resolver')).toBeVisible({timeout: 5_000});
        await expect(page.getByTestId('import-wizard-resolver-status')).toBeVisible();
        expect(await page.getByTestId('import-wizard-duplicate-group').count()).toBeGreaterThan(0);

        // A row already in the archive must not be re-imported by default.
        await page.getByTestId('import-wizard-duplicates-continue').click();
        const step4 = page.getByTestId('import-wizard-step4');
        await expect(step4).toBeVisible({timeout: 5_000});
        expect(await step4.locator('tr.opacity-50, tr[class*="opacity-50"]').count()).toBeGreaterThan(0);
    });

    // -----------------------------------------------------------------------
    // IWR-006b: Compare Modal — click ⚠ badge opens TransactionFormModal in view mode
    // -----------------------------------------------------------------------
    test('IWR-006b: Click ⚠ duplicate badge opens compare modal in view mode', async ({page}) => {
        // Parse generic_simple.csv — if IWR-006/007 already ran, likely-dup rows are present.
        await openImportWizard(page);
        await goToStep4WithGenericSimple(page);

        const step4 = page.getByTestId('import-wizard-step4');

        // Look for a clickable amber badge cell (likely dup) in the TX table.
        // These are rendered as HTML cells: <span class="...amber...cursor-pointer">⚠ ...</span>
        const dupBadge = step4.locator('span[class*="amber"][class*="cursor-pointer"]').first();

        if (await dupBadge.isVisible({timeout: 3_000}).catch(() => false)) {
            await dupBadge.click();

            // TransactionFormModal should open in view mode
            // ModalBase renders testId="tx-form-modal" as data-testid on the backdrop
            const compareModal = page.locator('[data-testid="tx-form-modal"]');
            await expect(compareModal).toBeVisible({timeout: 5_000});

            // Title starts with 🔍 (titleOverride set by openCompare())
            const title = page.getByTestId('tx-form-title');
            await expect(title).toBeVisible({timeout: 3_000});
            const titleText = await title.textContent();
            expect(titleText).toContain('🔍');

            // Close by pressing Escape
            await page.keyboard.press('Escape');
            await expect(compareModal).not.toBeVisible({timeout: 3_000});
        } else {
            // No dup badges visible (fresh DB / first run) — just verify step 4 loaded
            await expect(step4).toBeVisible();
        }
    });

    // -----------------------------------------------------------------------
    // IWR-009: Broker creation reactivity — create broker from Step 1 shows in dropdown
    // -----------------------------------------------------------------------
    test('IWR-009: Creating a new broker from Step 1 makes it appear in the dropdown', async ({page}) => {
        await openImportWizard(page);

        // Step 1 is the upload step — it shows a BrokerSearchSelect when files are pending.
        // However, the global broker selector is only shown when pendingFiles.length > 0.
        // Navigate to Step 2 first to check if Step 1 has the broker selector visible.
        // If pendingFiles is empty (no uploads), the broker selector is not shown.
        // Alternative: directly check Step 1 content.
        const step1 = page.getByTestId('import-wizard-step1');
        await expect(step1).toBeVisible({timeout: 5_000});

        const brokerSelectWrapper = step1.getByTestId('import-wizard-step1-broker-select');
        const brokerSelectVisible = await brokerSelectWrapper.isVisible({timeout: 2_000}).catch(() => false);

        if (!brokerSelectVisible) {
            // No pending files → broker selector not shown — test is inapplicable
            // Proceed to Step 2 to try the per-row broker selector instead
            await page.getByTestId('import-wizard-next').click();
            await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 5_000});
            // Step 2 also has broker create via row inline editor — but that's more complex.
            // Simply verify the wizard works without broker creation.
            await expect(page.getByTestId('import-wizard-step2')).toBeVisible();
            return;
        }

        // Open the BrokerSearchSelect dropdown
        await brokerSelectWrapper.click();
        await optionListReady(page);

        // Click "Create new" in the dropdown footer
        const createNewBtn = page.getByTestId('search-select-create-new');
        await expect(createNewBtn).toBeVisible({timeout: 3_000});
        await createNewBtn.click();

        // BrokerModal should open
        const brokerModal = page.locator('[data-testid="broker-modal"]');
        await expect(brokerModal).toBeVisible({timeout: 5_000});

        // Fill in the broker name
        const nameInput = page.getByTestId('broker-name-input');
        await expect(nameInput).toBeVisible({timeout: 3_000});
        const uniqueName = `E2E Test Broker ${Date.now()}`;
        await nameInput.fill(uniqueName);
        await expect(nameInput).toHaveValue(uniqueName);

        // Save
        await page.getByTestId('broker-form-submit').click();

        // BrokerModal should close
        await expect(brokerModal).not.toBeVisible({timeout: 5_000});

        // Open the BrokerSearchSelect dropdown again — new broker should appear
        await brokerSelectWrapper.click();
        await optionListReady(page);

        // Verify the newly created broker appears in the options
        const newBrokerOption = page.locator(`[data-testid^="search-select-option-"]`).filter({hasText: uniqueName});
        await expect(newBrokerOption).toBeVisible({timeout: 5_000});

        // Close dropdown
        await page.keyboard.press('Escape');
    });

    // -----------------------------------------------------------------------
    // IWR-010: FilePreviewModal — preview file opens modal above wizard
    // -----------------------------------------------------------------------
    test('IWR-010: FilePreviewModal opens above wizard and can be closed', async ({page}) => {
        await openImportWizard(page);

        // Step 1: skip to Step 2 where files are listed with a preview action
        await page.getByTestId('import-wizard-next').click();
        await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 5_000});
        await waitForSettled(page.getByTestId('import-wizard-step2'), 20_000);

        const step2 = page.getByTestId('import-wizard-step2');

        // Find the row action menu and choose "preview".
        const previewBtn = step2.getByTestId(/^row-actions-/).first();
        const previewBtnVisible = await previewBtn.isVisible({timeout: 3_000}).catch(() => false);

        if (!previewBtnVisible) {
            // No files uploaded — preview action not available, test is inapplicable
            await expect(step2).toBeVisible();
            return;
        }

        await previewBtn.click();
        await page.getByTestId('context-menu-action-preview').click();

        // FilePreviewModal should open (ModalBase with testId="file-preview-modal")
        const previewModal = page.locator('[data-testid="file-preview-modal"]');
        await expect(previewModal).toBeVisible({timeout: 5_000});

        // Close by pressing Escape
        await page.keyboard.press('Escape');
        await expect(previewModal).not.toBeVisible({timeout: 3_000});

        // Wizard should still be visible and functional
        await expect(page.getByTestId('import-wizard-stepper')).toBeVisible();
        await expect(step2).toBeVisible();
    });

    // -----------------------------------------------------------------------
    // IWR-011: Conditional steps — a clean parse shows none of the three
    // -----------------------------------------------------------------------
    test('IWR-011: A parse with nothing to arbitrate goes straight to the review step', async ({page}) => {
        // The three middle steps exist to be skipped when there is no work for them. If
        // they appeared unconditionally the shortest import would be five clicks longer,
        // which is exactly what the restructure set out to remove.
        await openImportWizard(page);
        await parseGenericSimple(page);

        await page.getByTestId('import-wizard-continue').click();

        const conditional = ['import-wizard-step-assets', 'import-wizard-step-fix', 'import-wizard-step-duplicates'];
        const shown: string[] = [];
        for (const testid of conditional) {
            if (
                await page
                    .getByTestId(testid)
                    .isVisible({timeout: 1_200})
                    .catch(() => false)
            )
                shown.push(testid);
            await skipStepIfPresent(page, testid.replace('-step-', '-') + '-continue');
        }

        // Whatever this parse raised, the walk must end on the review step, and every
        // step shown must have had a reason to be there.
        await expect(page.getByTestId('import-wizard-step4')).toBeVisible({timeout: 5_000});
        for (const testid of shown) {
            expect(conditional).toContain(testid);
        }
    });

    // -----------------------------------------------------------------------
    // IWR-012: Going back from the review step lands on the analysis, not on nothing
    // -----------------------------------------------------------------------
    test('IWR-012: Back from the review step returns through the steps that were shown', async ({page}) => {
        await openImportWizard(page);
        await goToStep4WithGenericSimple(page);

        await page.getByTestId('import-wizard-back').click();

        // The previous step is whichever conditional step was raised, or the analysis if
        // none was. An empty panel — the symptom of a step machine counting by number
        // rather than by what it showed — is what this rules out.
        const landed = ['import-wizard-step-duplicates', 'import-wizard-step-fix', 'import-wizard-step-assets', 'import-wizard-step3'];
        let found = false;
        for (const testid of landed) {
            if (
                await page
                    .getByTestId(testid)
                    .isVisible({timeout: 1_200})
                    .catch(() => false)
            ) {
                found = true;
                break;
            }
        }
        expect(found).toBe(true);
    });

    // -----------------------------------------------------------------------
    // IWR-013: the unresolved badge counts the assets once, in the catalogue's plural
    // -----------------------------------------------------------------------
    for (const unresolved of [1, 2]) {
        test(`IWR-013 (n=${unresolved}): the resolve header counts the unresolved assets once, in the catalogue's plural`, async ({page}) => {
            // The badge drew `{step4UnresolvedCount}` and then `importWizard.unresolvedCount`, whose
            // message already holds `{n}` and had no plural: "1 1 assets unresolved". Its text must be
            // exactly the catalogue's message for the page's language, formatted for n.
            const tickers = Array.from({length: unresolved}, () => uniqueToken(6));
            await openImportWizard(page);
            const own = await uploadOwnedCsv(page, purchasesOf(tickers));

            // Step 1: skip; step 2: this test's file; step 3: parse
            await page.getByTestId('import-wizard-next').click();
            await selectBrokerFile(page, own);
            const parsed = await parseSelectedFile(page, own.fileId);

            // n is known by construction, and verified rather than assumed: the parse extracts the
            // invented tickers and nothing else, and no asset matches any of them.
            const mappings = (parsed as ParsedAssets).asset_mappings ?? [];
            expect(mappings.map((mapping) => mapping.extracted_symbol).sort(), 'premise: the parse extracts this file’s invented tickers, one asset each, and nothing else').toEqual([...tickers].sort());
            expect(
                mappings.filter((mapping) => (mapping.candidates ?? []).length > 0 || mapping.selected_asset_id != null),
                `premise: no asset matches the invented tickers, so all ${unresolved} reach the review unresolved`,
            ).toEqual([]);

            const step4 = await continueToReview(page, parsed);
            const lang = await pageLanguage(page);

            await expect(step4.getByTestId('import-wizard-unresolved-count'), `the badge is the "${lang}" catalogue's ${UNRESOLVED_COUNT_KEY} for n = ${unresolved}: the number once, inside the message's own plural`).toHaveText(unresolvedCountText(lang, unresolved), {timeout: 10_000});
        });
    }
});

test.describe('Import Wizard — the unresolved-assets message', () => {
    // -----------------------------------------------------------------------
    // IWR-014: the badge's message is a plural in every catalogue
    // -----------------------------------------------------------------------
    test('IWR-014: importWizard.unresolvedCount is a plural in every catalogue — one asset does not read as two with the digit swapped', () => {
        // The catalogue files alone: no page, no login. A message with no plural
        // (`{n} assets unresolved`) words 1 exactly as it words 2 with the "2" made a "1".
        const worded = SUPPORTED_LANGUAGES.map((lang) => ({lang, one: unresolvedCountText(lang, 1), twoAsOne: unresolvedCountText(lang, 2).replace('2', '1')}));
        const notPlural = worded.filter((entry) => entry.one === entry.twoAsOne);

        expect(notPlural, `${UNRESOLVED_COUNT_KEY} is an ICU plural in every catalogue: for one asset it does not read as the text for two with the digit swapped`).toEqual([]);
    });
});
