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
 * Test IDs: AID-001..AID-009
 */

import {expect, test, type APIRequestContext, type Page} from '../fixtures/playwright';
import {readFileSync} from 'fs';
import {resolve} from 'path';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {appears} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';

test.setTimeout(120_000);

const SAMPLES = resolve(process.cwd(), '../backend/app/services/brim_providers/sample_reports');
const FIXTURES = [
    {path: `${SAMPLES}/fineco_btp_placement.csv`, label: 'placement'},
    {path: `${SAMPLES}/fineco_btp_market.csv`, label: 'market'},
];
const API = `http://localhost:${process.env.TEST_PORT || '6041'}/api/v1`;

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

type OwnedImportFixture = {
    brokerId: number;
    brokerName: string;
    fileIds: string[];
    fileNames: string[];
};
type DisposableUser = {id: number; username: string; email: string; password: string};

async function registerDisposableUser(request: APIRequestContext): Promise<DisposableUser> {
    const suffix = uniqueSuffix();
    const user = {
        username: `asset_identity_${suffix}`,
        email: `asset_identity_${suffix}@example.com`,
        password: `Identity9!_${suffix}`,
    };
    const response = await request.post(`${API}/auth/register`, {data: user});
    expect(response.status(), 'Disposable-account registration must remain enabled').toBe(201);
    const created = (await response.json()) as {user: {id: number}};
    return {...user, id: created.user.id};
}

async function prepareDisposableImportUser(page: Page): Promise<void> {
    const response = await page.request.get(`${API}/settings/onboarding`);
    expect(response.ok(), `Onboarding setup failed (HTTP ${response.status()})`).toBe(true);
    const progress = (await response.json()) as {
        flows: Array<{flow: string; current_version: number}>;
    };
    for (const flow of progress.flows) {
        if (flow.flow === 'import_guide') continue;
        const skipped = await page.request.post(`${API}/settings/onboarding/${flow.flow}/skip`, {
            data: {expected_version: flow.current_version},
        });
        expect(skipped.ok(), `Could not skip owned flow ${flow.flow} (HTTP ${skipped.status()})`).toBe(true);
    }
}

/** Create a Fineco-bound broker and upload both reports to it, over the API. */
async function createBrokerWithFixtures(page: Page): Promise<OwnedImportFixture> {
    const suffix = uniqueSuffix();
    const brokerName = `Identity ${suffix}`;

    const created = await page.request.post(`${API}/brokers`, {
        data: [{name: brokerName, opened_at: '2020-01-01', default_import_plugin: 'broker_fineco'}],
    });
    expect(created.ok(), await created.text()).toBeTruthy();
    const brokerBody = (await created.json()) as {
        results: Array<{name: string; success: boolean; broker_id: number | null}>;
    };
    const broker = brokerBody.results.find((candidate) => candidate.name === brokerName);
    if (!broker?.success || typeof broker.broker_id !== 'number') {
        throw new Error(`Owned broker setup returned no id for ${brokerName}`);
    }
    const brokerId = broker.broker_id;

    const fileNames: string[] = [];
    const fileIds: string[] = [];
    for (const fixture of FIXTURES) {
        const fileName = `identity-${fixture.label}-${suffix}.csv`;
        const upload = await page.request.post(`${API}/brokers/import/upload`, {
            multipart: {
                broker_id: String(brokerId),
                file: {name: fileName, mimeType: 'text/csv', buffer: readFileSync(fixture.path)},
            },
        });
        expect(upload.ok(), await upload.text()).toBeTruthy();
        const uploaded = (await upload.json()) as {file_id?: string};
        if (!uploaded.file_id) throw new Error(`Owned upload ${fileName} returned no file_id`);
        fileIds.push(uploaded.file_id);
        fileNames.push(fileName);
    }

    return {brokerId, brokerName, fileIds, fileNames};
}

async function addSecondProposedPair(page: Page, fixture: OwnedImportFixture): Promise<void> {
    const suffix = uniqueSuffix();
    const variants = [
        {
            source: FIXTURES.find(({label}) => label === 'placement')?.path,
            label: 'placement-second-proposal',
            nameFrom: 'BTP 20-25 1.40% CUM',
            nameTo: 'BTP 30-35 2.50% CUM',
            isinFrom: 'IT0005410912',
            isinTo: 'IT0000000101',
        },
        {
            source: FIXTURES.find(({label}) => label === 'market')?.path,
            label: 'market-second-proposal',
            nameFrom: 'BTP 20-25 1.40%',
            nameTo: 'BTP 30-35 2.50%',
            isinFrom: 'IT0005416570',
            isinTo: 'IT0000000102',
        },
    ];

    for (const variant of variants) {
        if (!variant.source) throw new Error(`Missing source fixture for ${variant.label}`);
        const body = readFileSync(variant.source, 'utf8').replace(variant.nameFrom, variant.nameTo).replace(variant.isinFrom, variant.isinTo);
        expect(body).toContain(variant.nameTo);
        expect(body).toContain(variant.isinTo);
        const fileName = `identity-${variant.label}-${suffix}.csv`;
        const upload = await page.request.post(`${API}/brokers/import/upload`, {
            multipart: {
                broker_id: String(fixture.brokerId),
                file: {name: fileName, mimeType: 'text/csv', buffer: Buffer.from(body, 'utf8')},
            },
        });
        expect(upload.ok(), await upload.text()).toBeTruthy();
        const uploaded = (await upload.json()) as {file_id?: string};
        if (!uploaded.file_id) throw new Error(`Owned upload ${fileName} returned no file_id`);
        fixture.fileIds.push(uploaded.file_id);
        fixture.fileNames.push(fileName);
    }
}

async function deleteOwnedImportFixture(page: Page, fixture: OwnedImportFixture | undefined, user: DisposableUser): Promise<void> {
    await page.goto('about:blank');
    const loggedIn = await page.request.post(`${API}/auth/login`, {
        data: {username: user.username, password: user.password},
    });
    expect(loggedIn.ok(), 'Cleanup must authenticate as its disposable account').toBe(true);
    const failures: string[] = [];
    try {
        if (fixture) {
            for (const fileId of fixture.fileIds) {
                const deleted = await page.request.delete(`${API}/brokers/import/files/${fileId}`);
                if (!deleted.ok()) {
                    failures.push(`file ${fileId}: HTTP ${deleted.status()} ${await deleted.text()}`);
                }
            }
            const brokerDeleted = await page.request.delete(`${API}/brokers?ids=${fixture.brokerId}&force=true`);
            if (!brokerDeleted.ok()) {
                failures.push(`broker ${fixture.brokerId}: HTTP ${brokerDeleted.status()} ${await brokerDeleted.text()}`);
            } else {
                const body = (await brokerDeleted.json()) as {results: Array<{id: number; success: boolean}>};
                const result = body.results.find((candidate) => candidate.id === fixture.brokerId);
                if (result?.success !== true) failures.push(`broker ${fixture.brokerId}: ${JSON.stringify(body)}`);
            }
        }
    } finally {
        const me = await page.request.get(`${API}/auth/me`);
        expect(me.ok(), 'Cleanup must remain authenticated as its disposable account').toBe(true);
        const identity = (await me.json()) as {user: {id: number}};
        expect(identity.user.id).toBe(user.id);
        const removed = await page.request.delete(`${API}/auth/users/me`);
        expect(removed.ok(), 'Cleanup must delete the disposable import account').toBe(true);
    }
    expect(failures, 'Cleanup must remove only this test’s uploaded files and broker').toEqual([]);
}

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
    // The table being VISIBLE is not the table being LOADED: it renders empty
    // and fills in. The page publishes data-busy, so wait on that instead.
    await waitForSettled(page.getByTestId('transactions-page'));
}

async function openImportWizard(page: Page) {
    await expect(page.getByTestId('tx-import-button')).toBeEnabled();
    await page.getByTestId('tx-import-button').click();
    await page.getByTestId('import-wizard-stepper').waitFor({state: 'visible', timeout: 5_000});
}

/** Select every file of our broker and parse them together — one import, two reports. */
async function parseBothFiles(page: Page, target: {brokerName: string; fileNames: string[]}) {
    await page.getByTestId('import-wizard-next').click();
    await page.getByTestId('import-wizard-step2').waitFor({state: 'visible', timeout: 5_000});

    const step2 = page.getByTestId('import-wizard-step2');
    const rowFor = (fileName: string) => step2.locator('tr[data-row-id]').filter({hasText: fileName}).first();

    if (!(await appears(rowFor(target.fileNames[0]), 5_000))) {
        // A brand-new broker's panel may start folded.
        const headers = step2.locator('div.rounded-lg > button').filter({hasText: target.brokerName});
        for (let i = 0; i < (await headers.count()); i++) {
            await headers.nth(i).click();
            if (await appears(rowFor(target.fileNames[0]), 1_500)) break;
        }
    }

    for (const fileName of target.fileNames) {
        const row = rowFor(fileName);
        await expect(row).toBeVisible({timeout: 5_000});
        const checkbox = row.locator('td.td-select button.checkbox-btn');
        await checkbox.scrollIntoViewIfNeeded();
        await checkbox.click();
    }

    await expect(page.getByTestId('import-wizard-parse')).toBeEnabled({timeout: 4_000});
    await page.getByTestId('import-wizard-parse').click();
    await page.getByTestId('import-wizard-step3').waitFor({state: 'visible', timeout: 20_000});
    await waitForParseVerdict(page);
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
    // The step is only meaningful once it has decided what to show: either groups or
    // the explicit empty state. Both are real; "neither yet" is what the sleep hid.
    await expect(page.getByTestId('asset-group-empty').or(page.getByTestId('asset-group-reset')).first()).toBeVisible({timeout: 10_000});
}

/** The card holding the two BTPs — the only one the engine leaves undecided. */
function proposedCard(page: Page) {
    return page.locator('[data-testid^="asset-group-grp-"][data-state="proposed"]').first();
}

async function groupIdOf(card: ReturnType<typeof proposedCard>): Promise<string> {
    const testid = await card.getAttribute('data-testid');
    return (testid ?? '').replace('asset-group-', '');
}

type AssetGroupSnapshot = {
    testId: string;
    state: string;
    members: string[];
    primaries: string[];
};

async function readAssetGroupSnapshot(page: Page): Promise<AssetGroupSnapshot[]> {
    return page.getByTestId('asset-group-step').evaluate((root) =>
        Array.from(root.querySelectorAll<HTMLElement>('[data-testid^="asset-group-grp-"]')).map((card) => ({
            testId: card.dataset.testid ?? '',
            state: card.dataset.state ?? '',
            members: Array.from(card.querySelectorAll<HTMLElement>('[role="listitem"][data-testid]'))
                .map((member) => member.dataset.testid ?? '')
                .sort(),
            primaries: Array.from(card.querySelectorAll<HTMLElement>('[data-testid^="asset-group-badge-"][data-primary="true"]'))
                .map((badge) => badge.dataset.testid ?? '')
                .sort(),
        })),
    );
}

// ---------------------------------------------------------------------------

test.describe('Import Wizard — asset identity', () => {
    let broker: OwnedImportFixture | undefined;
    let user: DisposableUser | undefined;

    function ownedBroker(): OwnedImportFixture {
        if (!broker) throw new Error('Owned import fixture was not created');
        return broker;
    }

    test.beforeEach(async ({page, request}) => {
        broker = undefined;
        user = undefined;
        user = await registerDisposableUser(request);
        await login(page, user);
        await prepareDisposableImportUser(page);
        broker = await createBrokerWithFixtures(page);
        await goToTransactions(page);
    });

    test.afterEach(async ({page}) => {
        if (!user) return;
        await deleteOwnedImportFixture(page, broker, user);
    });

    // -----------------------------------------------------------------------
    // AID-001 — the three states, and what each one means
    // -----------------------------------------------------------------------
    test('AID-001: the unification step separates certain, proposed and lone instruments', async ({page}) => {
        await goToAssetStep(page, ownedBroker());

        // Same ISIN in both files: nothing to ask.
        await expect(page.locator('[data-testid^="asset-group-grp-"][data-state="confirmed"]').first()).toBeVisible();
        // Two ISINs, names apart by one short token: asked, never assumed.
        await expect(proposedCard(page)).toBeVisible();
        await expect(page.getByTestId('import-wizard-assets-continue'), 'An unresolved asset-group proposal must block Continue').toBeDisabled();
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
        await goToAssetStep(page, ownedBroker());

        const card = proposedCard(page);
        const groupId = await groupIdOf(card);
        await page.getByTestId(`asset-group-confirm-${groupId}`).click();

        await expect(page.getByTestId(`asset-group-${groupId}`)).toHaveAttribute('data-state', 'confirmed');
        // A settled group has nothing left to confirm.
        await expect(page.getByTestId(`asset-group-confirm-${groupId}`)).toHaveCount(0);
        await expect(page.getByTestId('import-wizard-assets-continue'), 'Continue must enable only after every proposal is terminal').toBeEnabled();
    });

    test('AID-009: Confirm All settles only the open proposals and preserves every partition and primary', async ({page}) => {
        const fixture = ownedBroker();
        await addSecondProposedPair(page, fixture);
        await goToAssetStep(page, fixture);

        const before = await readAssetGroupSnapshot(page);
        const proposedBefore = before.filter(({state}) => state === 'proposed');
        expect(proposedBefore, 'The four owned reports must produce exactly two independent open proposals').toHaveLength(2);
        expect(
            before.some(({state}) => state === 'confirmed'),
            'The same reports must retain at least one already-confirmed group',
        ).toBe(true);

        const content = page.getByTestId('import-wizard-content');
        await expect(content).toHaveAttribute('data-busy', 'false');
        const confirmAll = page.getByTestId('asset-group-confirm-all');
        await expect(confirmAll).toBeVisible();
        await confirmAll.click();

        await expect(confirmAll).toHaveCount(0);
        await expect(content).toHaveAttribute('data-busy', 'false');
        await expect(page.getByTestId('import-wizard-assets-continue')).toBeEnabled();

        const after = await readAssetGroupSnapshot(page);
        expect(after).toHaveLength(before.length);
        for (const previous of before) {
            const current = after.find(({testId}) => testId === previous.testId);
            if (!current) throw new Error(`Confirm All removed asset partition ${previous.testId}`);
            expect(current.members, `Confirm All must not repartition ${previous.testId}`).toEqual(previous.members);
            expect(current.primaries, `Confirm All must not change primaries for ${previous.testId}`).toEqual(previous.primaries);
            expect(current.state, `Confirm All changed an ineligible state for ${previous.testId}`).toBe(previous.state === 'proposed' ? 'confirmed' : previous.state);
        }
    });

    test('AID-008: clicking the real Assets Continue target advances the active import step', async ({page}) => {
        await goToAssetStep(page, ownedBroker());

        const card = proposedCard(page);
        const groupId = await groupIdOf(card);
        await page.getByTestId(`asset-group-confirm-${groupId}`).click();

        const continueButton = page.getByTestId('import-wizard-assets-continue');
        await expect(continueButton).toBeEnabled();
        const coachmark = page.getByTestId('onboarding-coachmark');
        await expect(coachmark).toHaveAttribute('data-step-id', 'import.assets', {timeout: 10_000});
        await expect(continueButton).toHaveAttribute('aria-describedby', 'onboarding-coachmark-description');

        await continueButton.click();
        await expect(page.getByTestId('asset-group-step')).toBeHidden({timeout: 8_000});
        await expect(coachmark).toBeVisible({timeout: 10_000});
        await expect(coachmark).toHaveAttribute('data-step-id', /^import\.(fix|duplicates|review)$/);
    });

    // -----------------------------------------------------------------------
    // AID-003 — splitting a group, and taking it all back
    // -----------------------------------------------------------------------
    test('AID-003: a group can be broken apart and the whole step reset', async ({page}) => {
        await goToAssetStep(page, ownedBroker());

        const cardsBefore = await page.locator('[data-testid^="asset-group-grp-"]').count();
        const groupId = await groupIdOf(proposedCard(page));

        await page.getByTestId(`asset-group-split-${groupId}`).click();
        await expect(page.locator('[data-testid^="asset-group-grp-"]')).toHaveCount(cardsBefore + 1);

        // Reset is the way back from any decision taken here, not just from this one.
        await page.getByTestId('asset-group-reset').click();
        await expect(page.locator('[data-testid^="asset-group-grp-"]')).toHaveCount(cardsBefore);
        await expect(proposedCard(page)).toBeVisible();
    });

    // -----------------------------------------------------------------------
    // AID-004 — electing the code the asset will be quoted under
    // -----------------------------------------------------------------------
    test('AID-004: the market ISIN can be elected over the placement one', async ({page}) => {
        await goToAssetStep(page, ownedBroker());

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
        await goToAssetStep(page, ownedBroker());

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
        await goToAssetStep(page, ownedBroker());

        const before = await page.locator('[data-testid^="asset-group-grp-"]').count();
        const single = page.locator('[data-testid^="asset-group-grp-"][data-state="single"]').first();
        await single.locator('[data-testid^="asset-group-single-menu-"]').first().click();
        await page.getByTestId('asset-group-menu-merge').click();

        // Destinations are listed in a second phase — a flat menu on a thirty-instrument
        // import would be unreadable.
        const target = page.locator('[data-testid^="asset-group-merge-target-"]').first();
        await expect(target).toBeVisible({timeout: 3_000});
        await target.click();
        await expect(page.locator('[data-testid^="asset-group-grp-"]')).toHaveCount(before - 1);

        // A merge made by hand must be undoable by hand.
        await page.getByTestId('asset-group-reset').click();
        await expect(page.locator('[data-testid^="asset-group-grp-"]')).toHaveCount(before);
    });

    // -----------------------------------------------------------------------
    // AID-007 — a decision here outlives the rest of the wizard
    // -----------------------------------------------------------------------
    test('AID-007: a confirmed unification survives leaving and re-entering the step', async ({page}) => {
        await goToAssetStep(page, ownedBroker());

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
