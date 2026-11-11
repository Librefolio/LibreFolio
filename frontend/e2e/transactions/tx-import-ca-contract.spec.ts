/**
 * Import Wizard — plugin → frontend contract E2E
 *
 * What this file proves is not Crédit Agricole. It is the set of channels the parse
 * system uses to tell the wizard what it could not decide on its own: notices with a
 * severity and evidence tables, field todos with a reason code and a context, split
 * hints, per-asset advisories. CA is simply the one plugin that speaks all of them, so
 * its fixture is used as the message.
 *
 * Since 2.0.0 Crédit Agricole is a REPORT-SET plugin: an export is no longer imported
 * alone, the securities movements (role `securities`) and the account movements (role
 * `account`) are uploaded together, in one batch, and the wizard shows them as ONE set
 * (`report-set-card`) that is combined (`POST /sets/combine`) and then parsed as a single
 * row. The channels below are the plugin's, not the set's, so they are proved on a set
 * whose two members are:
 *
 *   account     `credit_agricole-conti-contract.csv`: the rows that raise every channel.
 *               The account arm books a row on its own exactly as it did alone, so each
 *               notice, todo, split hint and asset advisory the fixture raises is still
 *               raised (the backend twin is test_brim_providers.py, TestPluginFrontendContract,
 *               set `credit_agricole-account-only`).
 *   securities  `credit_agricole-securities-contract.csv`: one transfer from another dossier
 *               (a cashless ADJUSTMENT and an info notice). It is there because a set needs
 *               both exports, and it is chosen to meet nothing: it pairs with no account row
 *               and no securities row with cash exists that could be left out, so nothing
 *               the account rows raise changes or disappears.
 *
 * The spec is self-contained: it creates its own broker and uploads the two members through
 * the API in one batch (`batch_id` in the form, as the wizard sends it), so it neither
 * depends on the mock data nor shifts the broker indices other suites rely on. Every broker
 * a test creates is deleted in afterEach (force), and its files with it, the set's combined
 * file included: a file left behind would be inherited by the next broker that reuses the id.
 *
 * The corridor is the shared one (fixtures/import-wizard.ts): the set's card is selected in
 * step 2 by its key and ticked whole; whether the notices' confirmation must be read past is
 * decided by the parse response of the combined file; the conditional steps are crossed when
 * the stepper lands on them. The rows the wizard shows are those of the COMBINED file, in date
 * order: no test here names a row by its position in a source export.
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

import {expect, test, type Page} from '../fixtures/playwright';
import {randomUUID} from 'crypto';
import {readFileSync} from 'fs';
import {resolve} from 'path';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {appears, optionsClosed} from '../fixtures/probe';
import {continueToReview, continueToStep, parseSelectedSet, selectReportSet, type ParseResponse} from '../fixtures/import-wizard';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {samplePath} from '../fixtures/brimSamples';

test.setTimeout(120_000);

const ACCOUNT_FIXTURE = samplePath('credit_agricole-conti-contract.csv');
const SECURITIES_FIXTURE = samplePath('credit_agricole-securities-contract.csv');
const CA = 'broker_credit_agricole';
const API = `http://localhost:${process.env.TEST_PORT || '6041'}/api/v1`;

// ---------------------------------------------------------------------------
// Setup — broker and set created through the API, not through the UI
// ---------------------------------------------------------------------------

/** A broker this test created and the report set (one upload batch, two exports) uploaded to it. */
interface CaFixture {
    brokerId: number;
    brokerName: string;
    batchId: string;
    securitiesFileId: string;
    accountFileId: string;
}

/** What afterEach deletes: each broker this test created, and the files it must take with it. */
interface OwnedBroker {
    brokerId: number;
    brokerName: string;
    fileIds: string[];
}

/**
 * Create a broker bound to the CA plugin and upload the contract set to it: the two members in one batch.
 *
 * Doing this over the API keeps the spec about the contract rather than about the
 * upload form, which `tx-brim-import.spec.ts` already covers. The name is unique per
 * run so repeated runs against a persistent database do not collide.
 *
 * The broker is recorded in `owned` as soon as it exists, each file as soon as its
 * upload answers: whatever fails afterwards, afterEach still deletes them.
 */
async function createBrokerWithFixture(page: Page, owned: OwnedBroker[], options: {label: string; filePrefix: string; openedAt: string}): Promise<CaFixture> {
    const suffix = uniqueSuffix();
    const brokerName = `${options.label} ${suffix}`;

    const created = await page.request.post(`${API}/brokers`, {
        data: [{name: brokerName, opened_at: options.openedAt, default_import_plugin: 'broker_credit_agricole'}],
    });
    expect(created.ok(), await created.text()).toBeTruthy();
    const results = ((await created.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null}>}).results;
    const result = results.find((item) => item.name === brokerName);
    if (!result?.success || typeof result.broker_id !== 'number') throw new Error(`Broker "${brokerName}" was not created: ${JSON.stringify(results)}`);
    const brokerId = result.broker_id;
    const record: OwnedBroker = {brokerId, brokerName, fileIds: []};
    owned.push(record);

    // The files of one batch are one report set: the wizard's step 1 gives the exports of a session the same batch_id.
    const batchId = randomUUID();
    const uploadMember = async (fixture: string, role: 'securities' | 'account'): Promise<string> => {
        const fileName = `${options.filePrefix}-${role}-${suffix}.csv`;
        const upload = await page.request.post(`${API}/brokers/import/upload`, {
            multipart: {
                broker_id: String(brokerId),
                batch_id: batchId,
                file: {name: fileName, mimeType: 'text/csv', buffer: readFileSync(fixture)},
            },
        });
        const body = await upload.text();
        expect(upload.ok(), body).toBeTruthy();
        const info = JSON.parse(body) as {file_id: string; filename: string; target_broker_id: number | null; batch_id?: string | null};
        record.fileIds.push(info.file_id);
        expect(info, `the ${role} export lands on "${brokerName}", in the batch of its set`).toMatchObject({filename: fileName, target_broker_id: brokerId, batch_id: batchId});
        return info.file_id;
    };
    const securitiesFileId = await uploadMember(SECURITIES_FIXTURE, 'securities');
    const accountFileId = await uploadMember(ACCOUNT_FIXTURE, 'account');

    return {brokerId, brokerName, batchId, securitiesFileId, accountFileId};
}

/**
 * Delete every broker in `owned` with force — the server deletes the broker's BRIM files
 * with it — and empty the list. Asserts each delete, and that the files went too: a file
 * that outlives its broker is inherited by the next broker that reuses the id. The files
 * checked are the two uploads and every other file the broker holds when it is deleted: a
 * set's combined file is written by the analysis, so only the broker's list knows its id.
 */
async function deleteOwnedBrokers(page: Page, owned: OwnedBroker[]): Promise<void> {
    const failures: string[] = [];
    for (const broker of owned.splice(0)) {
        try {
            const listed = await page.request.get(`${API}/brokers/import/files?broker_ids=${broker.brokerId}`);
            if (listed.ok()) {
                const files = (await listed.json()) as Array<{file_id: string; target_broker_id: number | null}>;
                for (const file of files) if (file.target_broker_id === broker.brokerId && !broker.fileIds.includes(file.file_id)) broker.fileIds.push(file.file_id);
            } else {
                failures.push(`list the files of broker "${broker.brokerName}" (${broker.brokerId}): HTTP ${listed.status()}`);
            }
            const response = await page.request.delete(`${API}/brokers?ids=${broker.brokerId}&force=true`);
            const body = (await response.json().catch(() => null)) as {results?: Array<{id: number; success: boolean}>} | null;
            if (!response.ok() || body?.results?.find((item) => item.id === broker.brokerId)?.success !== true) {
                failures.push(`broker "${broker.brokerName}" (${broker.brokerId}): HTTP ${response.status()} ${JSON.stringify(body)}`);
                continue;
            }
            const after = await page.request.get(`${API}/brokers/import/files`);
            if (after.ok()) {
                const remaining = new Set(((await after.json()) as Array<{file_id: string}>).map((file) => file.file_id));
                for (const fileId of broker.fileIds) if (remaining.has(fileId)) failures.push(`file ${fileId} outlived broker "${broker.brokerName}" (${broker.brokerId})`);
            } else {
                failures.push(`list the files after deleting broker "${broker.brokerName}" (${broker.brokerId}): HTTP ${after.status()}`);
            }
        } catch (error) {
            failures.push(`broker "${broker.brokerName}" (${broker.brokerId}): ${String(error)}`);
        }
    }
    expect(failures, 'cleanup deletes every broker this test created, and its files with it').toEqual([]);
}

/**
 * Budget for the transactions page to land and finish its first load: the 20 s the sibling import specs give
 * `waitForSettled(transactions-page)` (tx-import-flow, tx-import-degiro, …) and tx-wac-bulk its busy gate.
 */
const NAVIGATION_TIMEOUT_MS = 20_000;

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    // The page publishes its first load through `data-busy` and renders the table only once that load has ended
    // without an error: wait for the gate with the navigation budget, then check the table. A fixed 10 s on the
    // table itself lost by a hair under load (R, 12/10: the table was already on screen in the failure snapshot).
    await waitForSettled(page.getByTestId('transactions-page'), NAVIGATION_TIMEOUT_MS);
    await expect(page.getByTestId('tx-table')).toBeVisible({timeout: NAVIGATION_TIMEOUT_MS});
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
    }

    await page.getByTestId('tx-bulk-import').click();
    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 5_000});
}

/**
 * Select the uploaded set in step 2 — its card, by the batch it was uploaded in, ticked whole — and
 * parse it, stopping on the analysis step. The set is combined first and the combined file parsed:
 * the response returned is that parse's, and it says whether leaving the analysis asks to confirm notices.
 */
async function parseFixture(page: Page, target: CaFixture): Promise<ParseResponse> {
    await page.getByTestId('import-wizard-next').click();
    await selectReportSet(page, {brokerId: target.brokerId, pluginCode: CA, batchId: target.batchId});
    return parseSelectedSet(page);
}

/** Walk from the analysis step to the corrections step, past the notices and the unification step if the stepper lands on it. */
async function goToFixStep(page: Page, target: CaFixture) {
    await openImportWizard(page);
    const parsed = await parseFixture(page, target);
    await continueToStep(page, parsed, 'fix');
}

// ---------------------------------------------------------------------------

test.describe('Import Wizard — plugin contract', () => {
    let fixture: CaFixture;
    /** Every broker the running test created — the one below, CAC-012's late one: afterEach deletes them and empties the list. */
    const ownedBrokers: OwnedBroker[] = [];

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        // Broker and file first: the wizard reads the broker list when it opens.
        fixture = await createBrokerWithFixture(page, ownedBrokers, {label: 'CA Contract', filePrefix: 'ca-contract', openedAt: '2020-01-01'});
        await goToTransactions(page);
    });

    test.afterEach(async ({page}) => {
        await deleteOwnedBrokers(page, ownedBrokers);
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
        await expect.poll(() => first.getByTestId('fix-step-row').filter({visible: true}).count()).toBeLessThan(rowsBefore);
        await first.getByTestId('fix-step-group-toggle').click();
        await expect(first.getByTestId('fix-step-row').filter({visible: true})).toHaveCount(rowsBefore);

        // "Keep all" inside a panel settles that panel only: the whole point of grouping
        // is that a user can accept one class of finding and still examine another.
        await first.getByTestId('fix-step-group-accept-all').click();
        await expect(first.locator('[data-testid="fix-step-row"][data-decision="kept"]')).toHaveCount(rowsBefore);
        expect(await page.locator('[data-testid="fix-step-row"][data-decision="pending"]').count()).toBeGreaterThan(0);

        // And the panel can be put back exactly as it was.
        await first.getByTestId('fix-step-group-reset-all').click();
        await expect(first.locator('[data-testid="fix-step-row"][data-decision="pending"]')).toHaveCount(rowsBefore);
    });

    // -----------------------------------------------------------------------
    // CAC-004 — the global actions settle everything, and the step opens
    // -----------------------------------------------------------------------
    test('CAC-004: keep-all settles every row and opens the way forward', async ({page}) => {
        await goToFixStep(page, fixture);

        await page.getByTestId('fix-step-accept-all').click();

        await expect(page.locator('[data-testid="fix-step-row"][data-decision="pending"]')).toHaveCount(0, {timeout: 10_000});
        await expect(page.getByTestId('import-wizard-fix-continue')).toBeEnabled({timeout: 5_000});

        // Reset puts every row back to pending, and the gate closes again.
        await page.getByTestId('fix-step-reset-all').click();
        await expect.poll(() => page.locator('[data-testid="fix-step-row"][data-decision="pending"]').count()).toBeGreaterThan(0);
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
        // The barrier is the settling itself: `rows.count()` is the invariant under test
        // and would hold trivially if read before the action landed.
        await expect(page.locator('[data-testid="fix-step-row"][data-decision="pending"]')).toHaveCount(0, {timeout: 10_000});
        expect(await rows.count()).toBe(before);

        // Settling retires the row's todos; withdrawing the decision has to give them
        // back, or the row matches neither half of the membership test and disappears
        // from under the user — the defect this asserts is gone. The withdrawal lives
        // inside the row, so the row has to be opened first.
        await rows.first().getByTestId('fix-step-row-toggle').click();
        await rows.first().getByTestId('fix-step-reset').click();
        await expect(rows.first()).toHaveAttribute('data-decision', 'pending', {timeout: 5_000});
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
        }
        expect(splitRow, 'the fixture must offer at least one splittable row').not.toBeNull();

        // The plugin's own reading of the file, offered as a starting point.
        await expect(splitRow!.getByTestId('fix-step-split-hints')).toBeVisible();

        // One leg to begin with; typing an amount computes the trade leg as the rest.
        await splitRow!.getByTestId('fix-step-split-amount').first().fill('40');
        await expect(splitRow!.getByTestId('fix-step-split-preview')).toBeVisible();
        await expect(splitRow!.getByTestId('fix-step-split-main')).toBeVisible();

        // A second leg can be added, and its nature chosen from the custom select.
        await splitRow!.getByTestId('fix-step-split-add').click();
        await expect(splitRow!.getByTestId('fix-step-split-line')).toHaveCount(2);
        await splitRow!.getByTestId('fix-step-split-amount').nth(1).fill('12');

        // A charge larger than the trade itself would leave nothing bought.
        await splitRow!.getByTestId('fix-step-split-amount').first().fill('999999');
        await expect(splitRow!.getByTestId('fix-step-split-error')).toBeVisible({timeout: 3_000});

        // Back to a sane value, and the correction can be applied.
        await splitRow!.getByTestId('fix-step-split-amount').first().fill('40');
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
        }
        expect(splitRow).not.toBeNull();

        await splitRow!.getByTestId('fix-step-split-add').click();
        await expect(splitRow!.getByTestId('fix-step-split-line')).toHaveCount(2);

        // Open the second line's select: the first line's nature must be gone from it —
        // two "commissioni" legs on one row would be two transactions saying the same thing.
        const secondKind = splitRow!.getByTestId('fix-step-split-kind').nth(1);
        await secondKind.click();

        const options = page.locator('[data-testid^="search-select-option-"]');
        await expect(options.first()).toBeVisible({timeout: 5_000});
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

        await row.getByTestId('fix-step-accept').click();

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
        await page.getByTestId('import-wizard-fix-continue').click();
        // Deliberate: this proves an error banner *never* appears. A retrying assertion
        // would pass instantly on the empty page, before the re-check has even answered.
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
        await page.getByTestId('import-wizard-fix-continue').click();
        // Deliberate, same reason as CAC-009: absence is only meaningful after the
        // re-check has had a window in which it could have complained.
        await page.waitForTimeout(2_000);

        await expect(page.getByText(/ADJUSTMENT requires asset_id/i)).toHaveCount(0);
    });

    // -----------------------------------------------------------------------
    // CAC-011 — BRIMAssetNotice: the "possibly matured" advisory
    // -----------------------------------------------------------------------
    test('CAC-011: a suspected maturity is announced on the asset form', async ({page}) => {
        await openImportWizard(page);
        const parsed = await parseFixture(page, fixture);
        await continueToReview(page, parsed);

        const step4 = page.getByTestId('import-wizard-step4');

        // Open the creation form for an unresolved instrument: the advisory rides on the
        // extracted asset, so it must be on screen exactly where the decision is made.
        const resolveSection = step4.getByTestId('import-wizard-resolve-section');
        if (!(await resolveSection.isVisible({timeout: 3_000}).catch(() => false))) {
            await step4.getByTestId('import-wizard-resolve-toggle').click();
        }
        await expect(resolveSection, 'the section of the instruments to resolve is open').toBeVisible({timeout: 5_000});
        await resolveSection.scrollIntoViewIfNeeded();

        // The advisory rides on ONE of the set's extracted assets (the bond whose maturity the account states with
        // no coupon to identify it), and which select that is depends on the order the combined file lists the
        // assets in: the transfer from another dossier that the securities member brings is another asset, with no
        // advisory. So the forms are opened one after the other until the banner is found; that it IS found is the
        // assertion, not a condition.
        const selects = resolveSection.locator('[data-testid="asset-select"]');
        await expect(selects.first(), 'the review lists the instruments to resolve').toBeVisible({timeout: 5_000});
        const total = await selects.count();
        const createNew = page.getByTestId('search-select-create-new');
        const notice = page.getByTestId('asset-import-notice');
        let advisories = 0;
        for (let index = 0; index < total && advisories === 0; index++) {
            await selects.nth(index).click();
            if (!(await appears(createNew, 3_000))) {
                // This instrument is already bound to an asset: nothing to create, so no advisory to read here.
                await page.keyboard.press('Escape');
                await optionsClosed(page);
                continue;
            }
            await createNew.click();
            await page.getByTestId('asset-modal-form').waitFor({state: 'visible', timeout: 6_000});
            if (await appears(notice.first(), 2_000)) {
                advisories += 1;
                // When it is there it must name what it saw.
                await expect(page.getByTestId('asset-import-notices')).toBeVisible();
                expect((await notice.first().textContent())?.trim().length).toBeGreaterThan(0);
            }
            await page.getByTestId('asset-modal-cancel').click();
            await expect(page.getByTestId('asset-modal-form')).toBeHidden({timeout: 5_000});
            await optionsClosed(page);
        }
        expect(advisories, `one of the ${total} instrument(s) of the set carries the "possibly matured" advisory on its creation form`).toBe(1);
    });

    // -----------------------------------------------------------------------
    // CAC-012 — broker opening date: reported, fixable, re-checkable
    // -----------------------------------------------------------------------
    test('CAC-012: transactions predating the broker are reported and can be fixed', async ({page}) => {
        // The set's earliest movement is from 2025; a broker opened after it makes
        // every earlier row unimportable until the date is moved back.
        const late = await createBrokerWithFixture(page, ownedBrokers, {label: 'CA Late', filePrefix: 'ca-late', openedAt: '2026-08-01'});

        await page.reload();
        // A full reload is a navigation: same gate, same budget as goToTransactions.
        await waitForSettled(page.getByTestId('transactions-page'), NAVIGATION_TIMEOUT_MS);
        await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: NAVIGATION_TIMEOUT_MS});
        await openImportWizard(page);
        const parsed = await parseFixture(page, late);
        await continueToReview(page, parsed);

        const step4 = page.getByTestId('import-wizard-step4');
        const issues = page.getByTestId('import-wizard-broker-opening-issues');
        await expect(issues).toBeVisible({timeout: 8_000});

        // The fix is offered where the problem is stated, and the verdict is recomputed
        // rather than assumed: the user must see the rows come back.
        const autofix = page.locator('[data-testid^="broker-opening-autofix"]').first();
        if (await autofix.isVisible({timeout: 3_000}).catch(() => false)) {
            await autofix.click();
            // The auto-fix re-checks by itself once the PATCH lands, so its own busy
            // flag is the barrier: reading the toolbar before it clears catches the
            // re-check button mid-life and Playwright loses it to the re-render.
            await waitForSettled(step4);
            const recheck = page.getByTestId('import-wizard-recheck-openings');
            if (await recheck.isVisible({timeout: 2_000}).catch(() => false)) {
                await recheck.click();
                await waitForSettled(step4);
            }
            await expect(issues).toHaveCount(0, {timeout: 8_000});
        }
    });
});
