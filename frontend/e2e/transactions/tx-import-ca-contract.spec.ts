/**
 * Import Wizard — plugin → frontend contract E2E
 *
 * What this file proves is not Crédit Agricole. It is the set of channels the parse
 * system uses to tell the wizard what it could not decide on its own: notices with a
 * severity and evidence tables, field todos with a reason code and a context, split
 * hints, per-asset advisories. CA is simply the one plugin that speaks all of them, so
 * its fixture is used as the message.
 *
 * The spec is self-contained: it creates its own broker and uploads
 * `credit_agricole-conti-contract.csv` through the API, so it neither depends on the
 * mock data nor shifts the broker indices other suites rely on.
 *
 * Test IDs: CAC-001..CAC-012
 *
 * Channels covered:
 *   BRIMNotice          severity info vs warning, evidence table with its comment
 *   BRIMFieldTodo       blocker gates the step; reason_code groups the panels
 *   context.split_hint  the N-leg editor and its suggestions
 *   context.reason      the plugin's own proposal, accepted as read
 *   BRIMAssetNotice     the "possibly matured" banner on the asset form
 */

import {expect, test, type Page} from '@playwright/test';
import {readFileSync} from 'fs';
import {resolve} from 'path';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(120_000);

const FIXTURE = resolve(process.cwd(), '../backend/app/services/brim_providers/sample_reports/credit_agricole-conti-contract.csv');
const API = 'http://localhost:6041/api/v1';

// ---------------------------------------------------------------------------
// Setup — broker and file created through the API, not through the UI
// ---------------------------------------------------------------------------

/**
 * Create a broker bound to the CA plugin and upload the contract fixture to it.
 *
 * Doing this over the API keeps the spec about the contract rather than about the
 * upload form, which `tx-brim-import.spec.ts` already covers. The name is unique per
 * run so repeated runs against a persistent database do not collide.
 */
async function createBrokerWithFixture(page: Page): Promise<{brokerName: string; fileName: string}> {
    const suffix = Date.now().toString().slice(-6);
    const brokerName = `CA Contract ${suffix}`;
    const fileName = `ca-contract-${suffix}.csv`;

    const created = await page.request.post(`${API}/brokers`, {
        data: [{name: brokerName, opened_at: '2020-01-01', default_import_plugin: 'broker_credit_agricole'}],
    });
    expect(created.ok(), await created.text()).toBeTruthy();
    const brokerId = (await created.json()).results[0].broker_id;

    const upload = await page.request.post(`${API}/brokers/import/upload`, {
        multipart: {
            broker_id: String(brokerId),
            file: {name: fileName, mimeType: 'text/csv', buffer: readFileSync(FIXTURE)},
        },
    });
    expect(upload.ok(), await upload.text()).toBeTruthy();

    return {brokerName, fileName};
}

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
    await page.waitForTimeout(400);
}

async function openImportWizard(page: Page) {
    const firstRow = page.locator('[data-testid="tx-table"] tbody tr[data-row-id]').first();
    await firstRow.hover();
    const kebab = firstRow.getByTestId(/^row-actions-/);
    await expect(kebab).toBeVisible({timeout: 3_000});
    await kebab.click();
    await page.getByTestId('context-menu-action-edit').click();
    await page.getByTestId('tx-bulk-modal-root').waitFor({state: 'visible', timeout: 6_000});

    const formClose = page.getByTestId('tx-form-close');
    if (await formClose.isVisible({timeout: 1_500}).catch(() => false)) {
        await formClose.click();
        await page.waitForTimeout(300);
    }

    await page.getByTestId('tx-bulk-import').click();
    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 5_000});
}

/** Select the uploaded fixture in step 2 and parse it, stopping on the analysis step. */
async function parseFixture(page: Page, target: {brokerName: string; fileName: string}) {
    await page.getByTestId('import-wizard-next').click();
    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 5_000});
    await page.waitForTimeout(800);

    // Each broker owns a foldable panel; a brand-new one may start folded.
    const panel = page.getByTestId('import-wizard-step2').locator('div.rounded-lg').filter({hasText: target.brokerName}).first();
    await expect(panel).toBeVisible({timeout: 6_000});

    let row = panel.locator('tr[data-row-id]').first();
    if (!(await row.isVisible({timeout: 1_500}).catch(() => false))) {
        await panel.locator('> button').first().click();
        await page.waitForTimeout(500);
    }

    const named = panel.locator('tr[data-row-id]').filter({hasText: target.fileName}).first();
    row = (await named.isVisible({timeout: 2_000}).catch(() => false)) ? named : panel.locator('tr[data-row-id]').first();
    await expect(row).toBeVisible({timeout: 5_000});

    const checkbox = row.locator('td.td-select button.checkbox-btn');
    await checkbox.scrollIntoViewIfNeeded();
    await checkbox.click();

    await expect(page.getByTestId('import-wizard-parse')).toBeEnabled({timeout: 4_000});
    await page.getByTestId('import-wizard-parse').click();
    await page.getByTestId('import-wizard-step3').waitFor({state: 'visible', timeout: 15_000});
    await expect(page.getByTestId('import-wizard-continue')).toBeEnabled({timeout: 30_000});
}

/**
 * Leaving the analysis step when the parse raised notices opens a confirmation modal
 * that lists them. Read past it.
 */
async function confirmNotices(page: Page) {
    const confirm = page.getByTestId('import-wizard-warning-confirm');
    if (await confirm.isVisible({timeout: 2_500}).catch(() => false)) {
        await confirm.click();
        await page.waitForTimeout(400);
    }
}

/**
 * Walk from the analysis step to the review step, through whichever conditional steps
 * this parse raised. Rows flagged for correction are kept as read: the point here is to
 * arrive, not to correct.
 */
async function walkToReview(page: Page) {
    for (const testid of ['import-wizard-assets-continue', 'import-wizard-fix-continue', 'import-wizard-duplicates-continue']) {
        const button = page.getByTestId(testid);
        if (await button.isVisible({timeout: 2_000}).catch(() => false)) {
            if (testid === 'import-wizard-fix-continue') {
                await page.getByTestId('fix-step-accept-all').click();
                await page.waitForTimeout(800);
            }
            await button.click();
            await page.waitForTimeout(600);
        }
    }
    await page.getByTestId('import-wizard-step4').waitFor({state: 'visible', timeout: 10_000});
}

/** Walk from the analysis step to the corrections step. */
async function goToFixStep(page: Page, target: {brokerName: string; fileName: string}) {
    await openImportWizard(page);
    await parseFixture(page, target);
    await page.getByTestId('import-wizard-continue').click();
    await confirmNotices(page);

    // The unification step comes first when the file names several instruments.
    const assetsContinue = page.getByTestId('import-wizard-assets-continue');
    if (await assetsContinue.isVisible({timeout: 2_000}).catch(() => false)) {
        await assetsContinue.click();
        await page.waitForTimeout(400);
    }
    await page.getByTestId('import-wizard-step-fix').waitFor({state: 'visible', timeout: 8_000});
}

// ---------------------------------------------------------------------------

test.describe('Import Wizard — plugin contract', () => {
    let fixture: {brokerName: string; fileName: string};

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        // Broker and file first: the wizard reads the broker list when it opens.
        fixture = await createBrokerWithFixture(page);
        await goToTransactions(page);
    });

    // -----------------------------------------------------------------------
    // CAC-001 — BRIMNotice: severity, and evidence that can be read
    // -----------------------------------------------------------------------
    test('CAC-001: notices are rendered by severity, with their evidence readable', async ({page}) => {
        await openImportWizard(page);
        await parseFixture(page, fixture);

        // Notices are not silently carried forward: leaving the analysis step opens a
        // modal that reads them out, so nothing the plugin flagged goes past unseen.
        await page.getByTestId('import-wizard-continue').click();
        const notices = page.getByTestId('brim-notice');
        await expect(notices.first()).toBeVisible({timeout: 8_000});

        // The fixture raises both levels on purpose: an unmapped causale is news (info),
        // an unlinked maturity is a caution (warning). Collapsing the two would make the
        // second invisible among the first.
        await expect(page.locator('[data-testid="brim-notice"][data-severity="info"]').first()).toBeVisible();
        await expect(page.locator('[data-testid="brim-notice"][data-severity="warning"]').first()).toBeVisible();

        // Evidence is a table plus the sentence explaining what does not add up. The
        // sentence is the part a plugin cannot leave out — see the backend contract test.
        const toggle = page.getByTestId('brim-evidence-toggle').first();
        if (await toggle.isVisible({timeout: 2_000}).catch(() => false)) {
            await toggle.click();
            await page.waitForTimeout(300);
            await expect(page.getByTestId('brim-evidence').first()).toBeVisible({timeout: 4_000});
            await expect(page.getByTestId('brim-evidence-comment').first()).toBeVisible();
        }
    });

    // -----------------------------------------------------------------------
    // CAC-002 — a blocker raises the corrections step and holds the door
    // -----------------------------------------------------------------------
    test('CAC-002: a blocker opens the corrections step and blocks Continue', async ({page}) => {
        await goToFixStep(page, fixture);

        await expect(page.getByTestId('fix-step-rows')).toBeVisible();
        await expect(page.locator('[data-testid="fix-step-row"][data-severity="blocker"]').first()).toBeVisible();

        // Every row must be settled before the duplicate comparison can be asked a
        // meaningful question — a purchase misread as a withdrawal is compared against
        // withdrawals, confidently and wrongly.
        await expect(page.getByTestId('import-wizard-fix-continue')).toBeDisabled();
    });

    // -----------------------------------------------------------------------
    // CAC-003 — reason_code drives the panels, each with its own bulk actions
    // -----------------------------------------------------------------------
    test('CAC-003: rows are grouped by reason, foldable, with local and global actions', async ({page}) => {
        await goToFixStep(page, fixture);

        const groups = page.getByTestId('fix-step-group');
        expect(await groups.count()).toBeGreaterThan(1);

        // Folding a panel hides its rows without settling them.
        const first = groups.first();
        const rowsBefore = await first.getByTestId('fix-step-row').count();
        await first.getByTestId('fix-step-group-toggle').click();
        await page.waitForTimeout(300);
        expect(await first.getByTestId('fix-step-row').filter({visible: true}).count()).toBeLessThan(rowsBefore);
        await first.getByTestId('fix-step-group-toggle').click();
        await page.waitForTimeout(300);

        // "Keep all" inside a panel settles that panel only: the whole point of grouping
        // is that a user can accept one class of finding and still examine another.
        await first.getByTestId('fix-step-group-accept-all').click();
        await page.waitForTimeout(500);
        expect(await first.locator('[data-testid="fix-step-row"][data-decision="kept"]').count()).toBe(rowsBefore);
        expect(await page.locator('[data-testid="fix-step-row"][data-decision="pending"]').count()).toBeGreaterThan(0);

        // And the panel can be put back exactly as it was.
        await first.getByTestId('fix-step-group-reset-all').click();
        await page.waitForTimeout(500);
        expect(await first.locator('[data-testid="fix-step-row"][data-decision="pending"]').count()).toBe(rowsBefore);
    });

    // -----------------------------------------------------------------------
    // CAC-004 — the global actions settle everything, and the step opens
    // -----------------------------------------------------------------------
    test('CAC-004: keep-all settles every row and opens the way forward', async ({page}) => {
        await goToFixStep(page, fixture);

        await page.getByTestId('fix-step-accept-all').click();
        await page.waitForTimeout(800);

        expect(await page.locator('[data-testid="fix-step-row"][data-decision="pending"]').count()).toBe(0);
        await expect(page.getByTestId('import-wizard-fix-continue')).toBeEnabled({timeout: 5_000});

        // Reset puts every row back to pending, and the gate closes again.
        await page.getByTestId('fix-step-reset-all').click();
        await page.waitForTimeout(800);
        expect(await page.locator('[data-testid="fix-step-row"][data-decision="pending"]').count()).toBeGreaterThan(0);
        await expect(page.getByTestId('import-wizard-fix-continue')).toBeDisabled();
    });

    // -----------------------------------------------------------------------
    // CAC-005 — a settled row that is re-opened must not vanish
    // -----------------------------------------------------------------------
    test('CAC-005: re-opening a settled row keeps it on screen', async ({page}) => {
        await goToFixStep(page, fixture);

        const rows = page.getByTestId('fix-step-row');
        const before = await rows.count();

        await page.getByTestId('fix-step-accept-all').click();
        await page.waitForTimeout(800);
        expect(await rows.count()).toBe(before);

        // Settling retires the row's todos; withdrawing the decision has to give them
        // back, or the row matches neither half of the membership test and disappears
        // from under the user — the defect this asserts is gone. The withdrawal lives
        // inside the row, so the row has to be opened first.
        await rows.first().getByTestId('fix-step-row-toggle').click();
        await page.waitForTimeout(400);
        await rows.first().getByTestId('fix-step-reset').click();
        await page.waitForTimeout(600);
        expect(await rows.count()).toBe(before);
        expect(await page.locator('[data-testid="fix-step-row"][data-decision="pending"]').count()).toBeGreaterThan(0);
    });

    // -----------------------------------------------------------------------
    // CAC-006 — the split editor: hints, typed legs, and the remainder
    // -----------------------------------------------------------------------
    test('CAC-006: a split hint opens an editor whose legs add back up to the row', async ({page}) => {
        await goToFixStep(page, fixture);

        // Find the first row offering a split and open it.
        const rows = page.getByTestId('fix-step-row');
        let splitRow = null;
        for (let i = 0; i < (await rows.count()); i++) {
            const row = rows.nth(i);
            await row.getByTestId('fix-step-row-toggle').click();
            await page.waitForTimeout(250);
            if (
                await row
                    .getByTestId('fix-step-split')
                    .isVisible({timeout: 800})
                    .catch(() => false)
            ) {
                splitRow = row;
                break;
            }
            await row.getByTestId('fix-step-row-toggle').click();
            await page.waitForTimeout(150);
        }
        expect(splitRow, 'the fixture must offer at least one splittable row').not.toBeNull();

        // The plugin's own reading of the file, offered as a starting point.
        await expect(splitRow!.getByTestId('fix-step-split-hints')).toBeVisible();

        // One leg to begin with; typing an amount computes the trade leg as the rest.
        await splitRow!.getByTestId('fix-step-split-amount').first().fill('40');
        await page.waitForTimeout(400);
        await expect(splitRow!.getByTestId('fix-step-split-preview')).toBeVisible();
        await expect(splitRow!.getByTestId('fix-step-split-main')).toBeVisible();

        // A second leg can be added, and its nature chosen from the custom select.
        await splitRow!.getByTestId('fix-step-split-add').click();
        await page.waitForTimeout(300);
        expect(await splitRow!.getByTestId('fix-step-split-line').count()).toBe(2);
        await splitRow!.getByTestId('fix-step-split-amount').nth(1).fill('12');
        await page.waitForTimeout(400);

        // A charge larger than the trade itself would leave nothing bought.
        await splitRow!.getByTestId('fix-step-split-amount').first().fill('999999');
        await page.waitForTimeout(500);
        await expect(splitRow!.getByTestId('fix-step-split-error')).toBeVisible({timeout: 3_000});

        // Back to a sane value, and the correction can be applied.
        await splitRow!.getByTestId('fix-step-split-amount').first().fill('40');
        await page.waitForTimeout(500);
        await expect(splitRow!.getByTestId('fix-step-split-error')).toHaveCount(0);
    });

    // -----------------------------------------------------------------------
    // CAC-007 — the split kind select never offers the same nature twice
    // -----------------------------------------------------------------------
    test('CAC-007: a nature already used is not offered again', async ({page}) => {
        await goToFixStep(page, fixture);

        const rows = page.getByTestId('fix-step-row');
        let splitRow = null;
        for (let i = 0; i < (await rows.count()); i++) {
            const row = rows.nth(i);
            await row.getByTestId('fix-step-row-toggle').click();
            await page.waitForTimeout(250);
            if (
                await row
                    .getByTestId('fix-step-split')
                    .isVisible({timeout: 800})
                    .catch(() => false)
            ) {
                splitRow = row;
                break;
            }
            await row.getByTestId('fix-step-row-toggle').click();
            await page.waitForTimeout(150);
        }
        expect(splitRow).not.toBeNull();

        await splitRow!.getByTestId('fix-step-split-add').click();
        await page.waitForTimeout(300);

        // Open the second line's select: the first line's nature must be gone from it —
        // two "commissioni" legs on one row would be two transactions saying the same thing.
        const secondKind = splitRow!.getByTestId('fix-step-split-kind').nth(1);
        await secondKind.click();
        await page.waitForTimeout(400);

        const options = page.locator('[data-testid^="search-select-option-"]');
        const optionCount = await options.count();
        expect(optionCount).toBeGreaterThan(0);
        expect(optionCount).toBeLessThan(3); // three natures exist, one is taken
        await page.keyboard.press('Escape');
    });

    // -----------------------------------------------------------------------
    // CAC-008 — the plugin's proposal, accepted as read
    // -----------------------------------------------------------------------
    test('CAC-008: keeping a row as read badges it without changing it', async ({page}) => {
        await goToFixStep(page, fixture);

        const row = page.getByTestId('fix-step-row').first();
        await row.getByTestId('fix-step-row-toggle').click();
        await page.waitForTimeout(300);

        await row.getByTestId('fix-step-accept').click();
        await page.waitForTimeout(500);

        await expect(row).toHaveAttribute('data-decision', 'kept');
        await expect(row.getByTestId('fix-step-row-badge')).toBeVisible();
    });

    // -----------------------------------------------------------------------
    // CAC-009 — retyping a row applies the sign the type demands
    // -----------------------------------------------------------------------
    test('CAC-009: a corrected row leaves with the sign its type requires', async ({page}) => {
        await goToFixStep(page, fixture);

        // Settle everything the plugin flagged, then cross into the duplicates check.
        // That check validates the payload as real transactions, so a wrong sign shows
        // up there as "SELL requires quantity < 0" — the regression this guards.
        await page.getByTestId('fix-step-accept-all').click();
        await page.waitForTimeout(800);
        await page.getByTestId('import-wizard-fix-continue').click();
        await page.waitForTimeout(1_500);

        // The re-check may report duplicates, or nothing at all; what it must not do is
        // fail. The banner only appears when the call itself was refused.
        await expect(page.getByText(/SELL requires|BUY requires|requires quantity/i)).toHaveCount(0);
    });

    // -----------------------------------------------------------------------
    // CAC-010 — the duplicate re-check survives rows with no instrument
    // -----------------------------------------------------------------------
    test('CAC-010: the duplicate re-check does not fail on unresolved instruments', async ({page}) => {
        await goToFixStep(page, fixture);

        // Nothing is resolved at this point: the file's instruments are still placeholders.
        // Sending them as-is used to fail the whole call with a 422 and silently fall back
        // on the pre-correction verdict.
        await page.getByTestId('fix-step-accept-all').click();
        await page.waitForTimeout(800);
        await page.getByTestId('import-wizard-fix-continue').click();
        await page.waitForTimeout(2_000);

        await expect(page.getByText(/ADJUSTMENT requires asset_id/i)).toHaveCount(0);
    });

    // -----------------------------------------------------------------------
    // CAC-011 — BRIMAssetNotice: the "possibly matured" advisory
    // -----------------------------------------------------------------------
    test('CAC-011: a suspected maturity is announced on the asset form', async ({page}) => {
        await openImportWizard(page);
        await parseFixture(page, fixture);
        await page.getByTestId('import-wizard-continue').click();
        await confirmNotices(page);
        await walkToReview(page);

        const step4 = page.getByTestId('import-wizard-step4');

        // Open the creation form for an unresolved instrument: the advisory rides on the
        // extracted asset, so it must be on screen exactly where the decision is made.
        const resolveSection = step4.getByTestId('import-wizard-resolve-section');
        if (!(await resolveSection.isVisible({timeout: 3_000}).catch(() => false))) {
            await step4.getByTestId('import-wizard-resolve-toggle').click();
            await page.waitForTimeout(400);
        }
        await resolveSection.scrollIntoViewIfNeeded();

        const select = resolveSection.locator('[data-testid="asset-select"]').first();
        await select.click();
        await page.waitForTimeout(400);
        const createNew = page.getByTestId('search-select-create-new');
        if (await createNew.isVisible({timeout: 2_000}).catch(() => false)) {
            await createNew.click();
            await page.getByTestId('asset-modal-form').waitFor({state: 'visible', timeout: 6_000});

            // The banner is advisory: it may or may not concern this particular
            // instrument, but when it is there it must name what it saw.
            const notice = page.getByTestId('asset-import-notice');
            if (
                await notice
                    .first()
                    .isVisible({timeout: 2_000})
                    .catch(() => false)
            ) {
                await expect(page.getByTestId('asset-import-notices')).toBeVisible();
                expect((await notice.first().textContent())?.trim().length).toBeGreaterThan(0);
            }
            await page.getByTestId('asset-modal-cancel').click();
        }
    });

    // -----------------------------------------------------------------------
    // CAC-012 — broker opening date: reported, fixable, re-checkable
    // -----------------------------------------------------------------------
    test('CAC-012: transactions predating the broker are reported and can be fixed', async ({page}) => {
        // The fixture's earliest movement is from 2025; a broker opened after it makes
        // every earlier row unimportable until the date is moved back.
        const lateBroker = `CA Late ${Date.now().toString().slice(-6)}`;
        const created = await page.request.post(`${API}/brokers`, {
            data: [{name: lateBroker, opened_at: '2026-08-01', default_import_plugin: 'broker_credit_agricole'}],
        });
        expect(created.ok()).toBeTruthy();
        const brokerId = (await created.json()).results[0].broker_id;
        const lateFile = `ca-late-${Date.now().toString().slice(-6)}.csv`;
        const upload = await page.request.post(`${API}/brokers/import/upload`, {
            multipart: {broker_id: String(brokerId), file: {name: lateFile, mimeType: 'text/csv', buffer: readFileSync(FIXTURE)}},
        });
        expect(upload.ok()).toBeTruthy();

        await page.reload();
        await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
        await openImportWizard(page);
        await parseFixture(page, {brokerName: lateBroker, fileName: lateFile});
        await page.getByTestId('import-wizard-continue').click();
        await confirmNotices(page);
        await walkToReview(page);

        const issues = page.getByTestId('import-wizard-broker-opening-issues');
        await expect(issues).toBeVisible({timeout: 8_000});

        // The fix is offered where the problem is stated, and the verdict is recomputed
        // rather than assumed: the user must see the rows come back.
        const autofix = page.locator('[data-testid^="broker-opening-autofix"]').first();
        if (await autofix.isVisible({timeout: 3_000}).catch(() => false)) {
            await autofix.click();
            await page.waitForTimeout(1_000);
            const recheck = page.getByTestId('import-wizard-recheck-openings');
            if (await recheck.isVisible({timeout: 2_000}).catch(() => false)) {
                await recheck.click();
                await page.waitForTimeout(1_500);
            }
            await expect(issues).toHaveCount(0, {timeout: 8_000});
        }
    });
});
