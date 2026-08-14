/**
 * Import Wizard — asset identity E2E
 *
 * The question this file asks is the one that opened P3: *how many securities are really
 * in these files?* The wizard allocates a placeholder id per instrument **per file**, so
 * the same BTP read from two reports arrives as two unrelated assets — and an Italian
 * retail bond legitimately carries two ISINs, the placement (CUM) code it was issued
 * with and the market code it is quoted under. Getting this wrong does not fail loudly:
 * it produces two plausible assets, half the transactions on each.
 *
 * The fixtures are two Fineco reports of the same portfolio, built to raise all three
 * states the step can show:
 *   proposed  — `BTP 20-25 1.40% CUM` vs `BTP 20-25 1.40%`, two ISINs, names apart by one
 *               short token: the engine sees the resemblance and refuses to act alone;
 *   confirmed — `ISHARES MSCI WORLD ACC` under the same ISIN in both files;
 *   single    — `ETF COVERED BOND ISH`, named once and by itself.
 *
 * Test IDs: AID-001..AID-007
 */

import {expect, test, type Page} from '../fixtures/playwright';
import {readFileSync} from 'fs';
import {resolve} from 'path';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(120_000);

const SAMPLES = resolve(process.cwd(), '../backend/app/services/brim_providers/sample_reports');
const FIXTURES = [
    {path: `${SAMPLES}/fineco_btp_placement.csv`, label: 'placement'},
    {path: `${SAMPLES}/fineco_btp_market.csv`, label: 'market'},
];
const API = 'http://localhost:6041/api/v1';

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

/** Create a Fineco-bound broker and upload both reports to it, over the API. */
async function createBrokerWithFixtures(page: Page): Promise<{brokerName: string; fileNames: string[]}> {
    const suffix = Date.now().toString().slice(-6);
    const brokerName = `Identity ${suffix}`;

    const created = await page.request.post(`${API}/brokers`, {
        data: [{name: brokerName, opened_at: '2020-01-01', default_import_plugin: 'broker_fineco'}],
    });
    expect(created.ok(), await created.text()).toBeTruthy();
    const brokerId = (await created.json()).results[0].broker_id;

    const fileNames: string[] = [];
    for (const fixture of FIXTURES) {
        const fileName = `identity-${fixture.label}-${suffix}.csv`;
        const upload = await page.request.post(`${API}/brokers/import/upload`, {
            multipart: {
                broker_id: String(brokerId),
                file: {name: fileName, mimeType: 'text/csv', buffer: readFileSync(fixture.path)},
            },
        });
        expect(upload.ok(), await upload.text()).toBeTruthy();
        fileNames.push(fileName);
    }

    return {brokerName, fileNames};
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

/** Select every file of our broker and parse them together — one import, two reports. */
async function parseBothFiles(page: Page, target: {brokerName: string; fileNames: string[]}) {
    await page.getByTestId('import-wizard-next').click();
    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 5_000});
    await page.waitForTimeout(800);

    const step2 = page.getByTestId('import-wizard-step2');
    const rowFor = (fileName: string) => step2.locator('tr[data-row-id]').filter({hasText: fileName}).first();

    if (
        !(await rowFor(target.fileNames[0])
            .isVisible({timeout: 2_000})
            .catch(() => false))
    ) {
        // A brand-new broker's panel may start folded.
        const headers = step2.locator('div.rounded-lg > button').filter({hasText: target.brokerName});
        for (let i = 0; i < (await headers.count()); i++) {
            await headers.nth(i).click();
            await page.waitForTimeout(400);
            if (
                await rowFor(target.fileNames[0])
                    .isVisible({timeout: 800})
                    .catch(() => false)
            )
                break;
        }
    }

    for (const fileName of target.fileNames) {
        const row = rowFor(fileName);
        await expect(row).toBeVisible({timeout: 5_000});
        const checkbox = row.locator('td.td-select button.checkbox-btn');
        await checkbox.scrollIntoViewIfNeeded();
        await checkbox.click();
        await page.waitForTimeout(250);
    }

    await expect(page.getByTestId('import-wizard-parse')).toBeEnabled({timeout: 4_000});
    await page.getByTestId('import-wizard-parse').click();
    await page.getByTestId('import-wizard-step3').waitFor({state: 'visible', timeout: 20_000});
    await expect(page.getByTestId('import-wizard-continue')).toBeEnabled({timeout: 30_000});
}

/** Reach the unification step, reading past the notice modal if the parse raised one. */
async function goToAssetStep(page: Page, target: {brokerName: string; fileNames: string[]}) {
    await openImportWizard(page);
    await parseBothFiles(page, target);
    await page.getByTestId('import-wizard-continue').click();

    const confirm = page.getByTestId('import-wizard-warning-confirm');
    if (await confirm.isVisible({timeout: 2_500}).catch(() => false)) {
        await confirm.click();
    }
    await page.getByTestId('asset-group-step').waitFor({state: 'visible', timeout: 10_000});
    await page.waitForTimeout(400);
}

/** The card holding the two BTPs — the only one the engine leaves undecided. */
function proposedCard(page: Page) {
    return page.locator('[data-testid^="asset-group-grp-"][data-state="proposed"]').first();
}

async function groupIdOf(card: ReturnType<typeof proposedCard>): Promise<string> {
    const testid = await card.getAttribute('data-testid');
    return (testid ?? '').replace('asset-group-', '');
}

// ---------------------------------------------------------------------------

test.describe('Import Wizard — asset identity', () => {
    let broker: {brokerName: string; fileNames: string[]};

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        broker = await createBrokerWithFixtures(page);
        await goToTransactions(page);
    });

    // -----------------------------------------------------------------------
    // AID-001 — the three states, and what each one means
    // -----------------------------------------------------------------------
    test('AID-001: the unification step separates certain, proposed and lone instruments', async ({page}) => {
        await goToAssetStep(page, broker);

        // Same ISIN in both files: nothing to ask.
        await expect(page.locator('[data-testid^="asset-group-grp-"][data-state="confirmed"]').first()).toBeVisible();
        // Two ISINs, names apart by one short token: asked, never assumed.
        await expect(proposedCard(page)).toBeVisible();
        // Named once: alone, and not to be confused with an undecided group.
        await expect(page.locator('[data-testid^="asset-group-grp-"][data-state="single"]').first()).toBeVisible();

        // The proposal must show its reasoning: a dashed box with no stated reason is an
        // instruction to guess.
        const card = proposedCard(page);
        await expect(card.locator('[data-testid^="asset-group-links-"]')).toBeVisible();
        await expect(card.getByText(/BTP 20-25/i).first()).toBeVisible();
    });

    // -----------------------------------------------------------------------
    // AID-002 — confirming a proposal settles it
    // -----------------------------------------------------------------------
    test('AID-002: confirming a proposed group turns it into a certainty', async ({page}) => {
        await goToAssetStep(page, broker);

        const card = proposedCard(page);
        const groupId = await groupIdOf(card);
        await page.getByTestId(`asset-group-confirm-${groupId}`).click();

        await expect(page.getByTestId(`asset-group-${groupId}`)).toHaveAttribute('data-state', 'confirmed');
        // A settled group has nothing left to confirm.
        await expect(page.getByTestId(`asset-group-confirm-${groupId}`)).toHaveCount(0);
    });

    // -----------------------------------------------------------------------
    // AID-003 — splitting a group, and taking it all back
    // -----------------------------------------------------------------------
    test('AID-003: a group can be broken apart and the whole step reset', async ({page}) => {
        await goToAssetStep(page, broker);

        const cardsBefore = await page.locator('[data-testid^="asset-group-grp-"]').count();
        const groupId = await groupIdOf(proposedCard(page));

        await page.getByTestId(`asset-group-split-${groupId}`).click();
        await page.waitForTimeout(500);
        expect(await page.locator('[data-testid^="asset-group-grp-"]').count()).toBe(cardsBefore + 1);

        // Reset is the way back from any decision taken here, not just from this one.
        await page.getByTestId('asset-group-reset').click();
        await page.waitForTimeout(600);
        expect(await page.locator('[data-testid^="asset-group-grp-"]').count()).toBe(cardsBefore);
        await expect(proposedCard(page)).toBeVisible();
    });

    // -----------------------------------------------------------------------
    // AID-004 — electing the code the asset will be quoted under
    // -----------------------------------------------------------------------
    test('AID-004: the market ISIN can be elected over the placement one', async ({page}) => {
        await goToAssetStep(page, broker);

        const card = proposedCard(page);
        const groupId = await groupIdOf(card);

        // Both codes are on the card: nothing the files knew is thrown away.
        const placement = page.getByTestId(`asset-group-badge-${groupId}-IT0005410912`);
        const market = page.getByTestId(`asset-group-badge-${groupId}-IT0005416570`);
        await expect(placement).toBeVisible();
        await expect(market).toBeVisible();

        // Electing the quoted code is the whole point: a CUM code has no price feed
        // behind it, so leading with it means an asset that never updates.
        await market.click();
        await expect(market).toHaveAttribute('data-primary', 'true');
        await expect(placement).toHaveAttribute('data-primary', 'false');
    });

    // -----------------------------------------------------------------------
    // AID-005 — the group's name is the user's to set
    // -----------------------------------------------------------------------
    test('AID-005: an unbound group can be renamed', async ({page}) => {
        await goToAssetStep(page, broker);

        const groupId = await groupIdOf(proposedCard(page));
        await page.getByTestId(`asset-group-rename-${groupId}`).click();

        const input = page.getByTestId(`asset-group-rename-input-${groupId}`);
        await expect(input).toBeVisible({timeout: 3_000});
        await input.fill('BTP 2025 unificato');
        await input.press('Enter');

        await expect(page.getByTestId(`asset-group-name-${groupId}`)).toHaveText('BTP 2025 unificato');
    });

    // -----------------------------------------------------------------------
    // AID-006 — merging two lone instruments by hand, and extracting one back
    // -----------------------------------------------------------------------
    test('AID-006: two instruments can be merged from the menu and pulled apart again', async ({page}) => {
        await goToAssetStep(page, broker);

        const before = await page.locator('[data-testid^="asset-group-grp-"]').count();
        const single = page.locator('[data-testid^="asset-group-grp-"][data-state="single"]').first();
        await single.locator('[data-testid^="asset-group-single-menu-"]').first().click();
        await page.getByTestId('asset-group-menu-merge').click();
        await page.waitForTimeout(300);

        // Destinations are listed in a second phase — a flat menu on a thirty-instrument
        // import would be unreadable.
        const target = page.locator('[data-testid^="asset-group-merge-target-"]').first();
        await expect(target).toBeVisible({timeout: 3_000});
        await target.click();
        await page.waitForTimeout(600);
        expect(await page.locator('[data-testid^="asset-group-grp-"]').count()).toBe(before - 1);

        // A merge made by hand must be undoable by hand.
        await page.getByTestId('asset-group-reset').click();
        await page.waitForTimeout(600);
        expect(await page.locator('[data-testid^="asset-group-grp-"]').count()).toBe(before);
    });

    // -----------------------------------------------------------------------
    // AID-007 — a decision here outlives the rest of the wizard
    // -----------------------------------------------------------------------
    test('AID-007: a confirmed unification survives leaving and re-entering the step', async ({page}) => {
        await goToAssetStep(page, broker);

        const groupId = await groupIdOf(proposedCard(page));
        await page.getByTestId(`asset-group-confirm-${groupId}`).click();
        await expect(page.getByTestId(`asset-group-${groupId}`)).toHaveAttribute('data-state', 'confirmed');

        // Forward, then back: the step is rebuilt from the parse, so an override that is
        // not stored quietly evaporates and the user is asked the same question twice.
        await page.getByTestId('import-wizard-assets-continue').click();
        // Wait until the step is actually gone before going back. Playwright waits
        // for the back button to be clickable, not for the wizard to have finished
        // changing step — so clicking straight away can hit the button still
        // mounted on this step and land one step further back than intended.
        await page.getByTestId('asset-group-step').waitFor({state: 'hidden', timeout: 8_000});
        await page.getByTestId('import-wizard-back').click();

        await page.getByTestId('asset-group-step').waitFor({state: 'visible', timeout: 8_000});
        await expect(page.getByTestId(`asset-group-${groupId}`)).toHaveAttribute('data-state', 'confirmed');
    });
});
