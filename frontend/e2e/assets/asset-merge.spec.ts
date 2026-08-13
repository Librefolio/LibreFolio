/**
 * Asset merge E2E — folding a duplicate back into the asset that should have held it
 *
 * Duplicates are not a hypothesis: two imports of the same bond under its placement and
 * its market ISIN produce two assets, each holding half the history. The merge is how
 * that is repaired, and it is irreversible — so the flow is deliberately two-step, and
 * the second step is a dry run the backend computes rather than a promise the UI makes.
 *
 * What this file proves:
 *   · the counts shown before confirming come from the server, not from the client;
 *   · confirming actually moves the transactions and retires the source;
 *   · the surviving asset keeps *both* codes — an ISIN the files knew must never be
 *     dropped just because it lost the election for the leading one.
 *
 * Test IDs: AM-001..AM-003
 */

import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

test.setTimeout(120_000);

const API = 'http://localhost:6041/api/v1';

interface Pair {
    sourceId: number;
    sourceName: string;
    sourceIsin: string;
    targetId: number;
    targetName: string;
    targetIsin: string;
}

/**
 * Create the two halves of one security, and give the doomed one a transaction so the
 * dry run has something to count.
 */
async function createDuplicatePair(page: Page): Promise<Pair> {
    const suffix = Date.now().toString().slice(-6);
    const sourceName = `BTP Merge CUM ${suffix}`;
    const targetName = `BTP Merge MKT ${suffix}`;
    // An ISIN is exactly 12 characters — the schema enforces it, so the fixture must too.
    const sourceIsin = `IT0${suffix}AAA`;
    const targetIsin = `IT0${suffix}BBB`;

    const created = await page.request.post(`${API}/assets`, {
        data: [
            {display_name: sourceName, currency: 'EUR', asset_type: 'BOND', identifier_isin: sourceIsin},
            {display_name: targetName, currency: 'EUR', asset_type: 'BOND', identifier_isin: targetIsin},
        ],
    });
    expect(created.ok(), await created.text()).toBeTruthy();
    const body = await created.json();
    const ids: number[] = body.results.map((r: {asset_id: number}) => r.asset_id);
    expect(ids.length).toBe(2);

    const brokers = await page.request.get(`${API}/brokers`);
    expect(brokers.ok()).toBeTruthy();
    const brokerId = (await brokers.json()).items[0].id;

    const tx = await page.request.post(`${API}/transactions/commit`, {
        data: {
            creates: [
                // The buy needs funded cash, or the batch is refused for a negative balance.
                {date: '2024-01-02', type: 'DEPOSIT', broker_id: brokerId, cash: {code: 'EUR', amount: '5000.00'}},
                {date: '2024-03-01', type: 'BUY', asset_id: ids[0], broker_id: brokerId, quantity: '1000', cash: {code: 'EUR', amount: '-1000.00'}, description: `merge-fixture-${suffix}`},
            ],
        },
    });
    expect(tx.ok(), await tx.text()).toBeTruthy();
    // A 200 here is not proof: the endpoint reports refusals in `issues` and leaves `committed` false.
    const committed = await tx.json();
    expect(committed.committed, JSON.stringify(committed.issues ?? [])).toBe(true);

    return {sourceId: ids[0], sourceName, sourceIsin, targetId: ids[1], targetName, targetIsin};
}

/** There is no `GET /assets/{id}`: existence is read from the bulk endpoint. */
async function assetExists(page: Page, assetId: number): Promise<boolean> {
    const res = await page.request.get(`${API}/assets?asset_ids=${assetId}`);
    expect(res.ok(), await res.text()).toBeTruthy();
    return ((await res.json()) as unknown[]).length > 0;
}

async function openMergeModal(page: Page, pair: Pair) {
    await navigateTo(page, '/assets');
    await page.waitForSelector('[data-testid="assets-page"]', {timeout: 15_000});
    await page.waitForTimeout(800);

    const search = page.getByTestId('assets-search-input');
    await search.fill(pair.sourceName);
    await page.waitForTimeout(800);

    const card = page.locator(`[data-testid="asset-card-${pair.sourceId}"]`).first();
    if (await card.isVisible({timeout: 3_000}).catch(() => false)) {
        await card.hover();
        await card.getByTestId('asset-card-merge').click();
    } else {
        // Table view: the same verb lives in the row's context menu.
        const row = page.locator(`[data-testid="asset-row-${pair.sourceId}"]`).first();
        await expect(row).toBeVisible({timeout: 5_000});
        await row.click({button: 'right'});
        await page.getByTestId('context-menu-action-merge').click();
    }

    await page.getByTestId('asset-merge-modal').waitFor({state: 'visible', timeout: 6_000});
    await expect(page.getByTestId('asset-merge-source')).toContainText(pair.sourceName);
}

/** Pick the surviving asset in the modal's search select. */
async function chooseTarget(page: Page, pair: Pair) {
    const select = page.getByTestId('asset-merge-target-select');
    await select.click();
    await page.waitForTimeout(300);

    const input = select.locator('input[type="text"]').first();
    await input.fill(pair.targetName);

    await page.getByTestId(`search-select-option-${pair.targetId}`).click();
    await expect(page.getByTestId('asset-merge-target')).toContainText(pair.targetName);
}

// ---------------------------------------------------------------------------

test.describe('Assets — merge', () => {
    let pair: Pair;

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        pair = await createDuplicatePair(page);
    });

    // -----------------------------------------------------------------------
    // AM-001 — the preview is a dry run, and it says what will actually move
    // -----------------------------------------------------------------------
    test('AM-001: the second step previews what the merge would move', async ({page}) => {
        await openMergeModal(page, pair);
        await chooseTarget(page, pair);

        // Step one only asks where things should go; nothing is written yet.
        await page.getByTestId('asset-merge-next').click();
        await expect(page.getByTestId('asset-merge-preview')).toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('asset-merge-preview-transactions')).toContainText('1');

        // Backing out of the preview must leave the archive exactly as it was.
        await page.getByTestId('asset-merge-back').click();
        await page.getByTestId('asset-merge-cancel').click();
        await page.waitForTimeout(500);

        expect(await assetExists(page, pair.sourceId)).toBe(true);
    });

    // -----------------------------------------------------------------------
    // AM-002 — confirming moves the history and retires the duplicate
    // -----------------------------------------------------------------------
    test('AM-002: confirming the merge moves the transactions and removes the source', async ({page}) => {
        await openMergeModal(page, pair);
        await chooseTarget(page, pair);
        await page.getByTestId('asset-merge-next').click();
        await expect(page.getByTestId('asset-merge-preview')).toBeVisible({timeout: 8_000});

        await page.getByTestId('asset-merge-confirm').click();
        await expect(page.getByTestId('asset-merge-modal')).toBeHidden({timeout: 15_000});

        expect(await assetExists(page, pair.sourceId)).toBe(false);

        const moved = await page.request.get(`${API}/transactions?asset_id=${pair.targetId}`);
        expect(moved.ok()).toBeTruthy();
        const items = await moved.json();
        expect(items.length).toBeGreaterThan(0);
    });

    // -----------------------------------------------------------------------
    // AM-003 — the survivor inherits the codes it did not have
    // -----------------------------------------------------------------------
    test('AM-003: the surviving asset keeps both ISINs', async ({page}) => {
        await openMergeModal(page, pair);
        await chooseTarget(page, pair);
        await page.getByTestId('asset-merge-next').click();
        await expect(page.getByTestId('asset-merge-preview')).toBeVisible({timeout: 8_000});

        // Two ISINs on one bond is the normal case, not a conflict to resolve by
        // discarding one: the modal states what it is about to inherit.
        await expect(page.getByTestId('asset-merge-identifiers-added')).toBeVisible();

        await page.getByTestId('asset-merge-confirm').click();
        await expect(page.getByTestId('asset-merge-modal')).toBeHidden({timeout: 15_000});

        // Only `/assets/all` carries the identifier block; the bulk read is metadata only.
        const survivor = await page.request.get(`${API}/assets/all`);
        expect(survivor.ok(), await survivor.text()).toBeTruthy();
        const asset = ((await survivor.json()) as {id: number}[]).find((a) => a.id === pair.targetId) as {identifier_isin?: string; identifier_other?: string[]} | undefined;
        expect(asset, 'the surviving asset must still be readable').toBeTruthy();
        const codes = [asset?.identifier_isin, ...(asset?.identifier_other ?? [])].filter(Boolean).join(' ');
        expect(codes).toContain(pair.sourceIsin);
        expect(codes).toContain(pair.targetIsin);
    });
});
