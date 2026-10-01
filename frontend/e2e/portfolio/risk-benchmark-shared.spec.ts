/**
 * Asset page, Risk tab — the comparison measures against the SHARED benchmark.
 *
 * Owner: the Risk workstream. Developer decision, 01/10/2026: wherever a page measures
 * against a benchmark there is a picker; on load it shows the current benchmark, and it
 * is empty only when nothing is set. The asset page's Risk tab uses that shared choice —
 * it opens on it, and changing it there changes it everywhere. Holding an asset does not
 * disqualify it as a benchmark; being the asset the page measures does.
 *
 * Four cases, each read off the state the picker publishes on its root —
 * `risk-comparison-asset-select-control`, with `data-benchmark-id` (the resolved value, ''
 * when there is none) and `data-measured` — and off what reaches the wire; never off an
 * icon or a label:
 *   1. a stored benchmark opens the tab with the picker on it, and Run sends a
 *      `comparison` whose `comparison_asset_id` is that id;
 *   2. a stored benchmark that IS this asset is still the current one — never dropped —
 *      published as measured, with its ⚠ visible, and nothing is compared: the backend
 *      would refuse a yardstick that is also the subject;
 *   3. choosing another asset here writes the reader's shared key;
 *   4. nothing stored: no benchmark published, and Run disabled until a choice is made.
 *
 * Registered as `front-portfolio risk-benchmark-shared` (the `-unit` action next to it is
 * the store's).
 *
 * `risk-asset-detail.spec.ts` is the ownerless net for this page and stays as it is: this
 * file shares nothing with it but `risk-mocks.ts`, which is additive.
 *
 * Nothing to restore: the risk endpoints are mocked, the choice lives in this context's
 * `localStorage` (which dies with the context), and no database row is written — so every
 * test runs beside its neighbours.
 */
import {expect, test, type Page} from '../fixtures/playwright';

import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {installRiskMocks, waitForRiskCatalog, type RiskRequest} from './risk-mocks';

/** The picker's test id on the asset page: `-trigger`, `-search` and `-measured` hang off it. */
const PICKER = 'risk-comparison-asset-select';
/** Its root, the id `SignalAssetParamControl` already gives it today: where the page reads its state. */
const CONTROL = `${PICKER}-control`;

interface CatalogueAsset {
    id: number;
    display_name: string;
    is_benchmark?: boolean;
    held_by_me?: boolean;
}

interface Cast {
    /** The asset whose page is opened. */
    subject: CatalogueAsset;
    /** A flagged benchmark, to be stored as the shared choice. */
    benchmark: CatalogueAsset;
    /** An asset the reader holds: a legitimate benchmark since 01/10/2026. */
    held: CatalogueAsset;
}

/**
 * Three distinct assets, each picked for the property its case needs rather than for its
 * place on a page. Within a property the lowest id is taken: `populate_mock_data.py`
 * creates those before any spec runs, so a neighbour's freshly created asset — which may
 * be deleted under us — is never the one picked.
 */
async function castAssets(page: Page): Promise<Cast> {
    const response = await page.request.get('/api/v1/assets/query');
    expect(response.ok(), 'the asset list must answer: it is exactly what the picker offers').toBe(true);
    const all = ((await response.json()) as CatalogueAsset[]).sort((left, right) => left.id - right.id);

    const benchmark = all.find((asset) => asset.is_benchmark === true);
    if (!benchmark) throw new Error('No asset is flagged is_benchmark. populate_mock_data.py flags its INDEX assets as benchmarks.');
    const held = all.find((asset) => asset.held_by_me === true && asset.id !== benchmark.id);
    if (!held) throw new Error(`${TEST_USER.username} holds no asset besides the benchmark. Check populate_mock_data.py seeding.`);
    const subject = all.find((asset) => asset.is_benchmark !== true && asset.id !== held.id);
    if (!subject) throw new Error('No third asset whose page could be opened. Check populate_mock_data.py seeding.');
    return {subject, benchmark, held};
}

/** The user id the benchmark store scopes its key with, asked of the endpoint the app asks. */
async function currentUserId(page: Page): Promise<number> {
    const response = await page.request.get('/api/v1/auth/me');
    expect(response.ok(), 'the shared benchmark lives under a user-scoped key, so the test needs the id the app resolves').toBe(true);
    const body = (await response.json()) as {user?: {id?: number}};
    const id = body.user?.id;
    expect(Number.isInteger(id), `auth/me must publish an integer user id, read ${JSON.stringify(body.user)}`).toBe(true);
    return id as number;
}

/** `riskBenchmarkStore`'s key for one reader — `storageKey()` there, reproduced rather than guessed. */
function benchmarkKey(userId: number): string {
    return `lf_${userId}_risk_benchmark_asset`;
}

async function readKey(page: Page, key: string): Promise<string | null> {
    return page.evaluate((storageKey) => window.localStorage.getItem(storageKey), key);
}

/**
 * Put the reader's shared choice in storage, or take it out, and return its key.
 *
 * Written on the app's origin and read by a runtime that starts afterwards: the store
 * keeps its value at module scope and reads storage once per account, so only the full
 * document load in `openAssetRisk` is sure to see the seed. Only the user-scoped spelling
 * is seeded, on purpose: the page renders after `/auth/me` has resolved, so that is the
 * key the app must read — a picker that opened on any other would be the defect.
 */
async function storeBenchmark(page: Page, assetId: number | null): Promise<string> {
    const key = benchmarkKey(await currentUserId(page));
    const value = assetId === null ? null : String(assetId);
    await page.evaluate(
        ([storageKey, stored]) => {
            if (stored === null) window.localStorage.removeItem(storageKey);
            else window.localStorage.setItem(storageKey, stored);
        },
        [key, value] as const,
    );
    expect(await readKey(page, key), 'the seed did not land in storage').toBe(value);
    return key;
}

/** The asset's page, Risk tab, by a full document load; returns once the comparison controls are up. */
async function openAssetRisk(page: Page, assetId: number): Promise<void> {
    await navigateTo(page, `/assets/${assetId}?tab=risk`);
    await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 15_000});
    // Every section is gated on the capability catalog: wait for the gate, then for what is behind it.
    await waitForRiskCatalog(page);
    await expect(page.getByTestId('risk-comparison-controls')).toBeVisible();
}

/**
 * Open the picker and end with it open.
 *
 * `SearchSelect.openDropdown()` ignores a click landing within 200 ms of its last close (a
 * guard against touch double-fire), and nothing on the page says the guard is armed: a
 * click right after an Escape is swallowed and the list simply stays shut. So this asks for
 * the end state and clicks only while it is not there, retrying until the list is open —
 * never a blind second click, which on an open list would close it again.
 */
async function openPicker(page: Page): Promise<void> {
    const trigger = page.getByTestId(`${PICKER}-trigger`);
    await expect(async () => {
        if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
        await expect(trigger).toHaveAttribute('aria-expanded', 'true', {timeout: 1_000});
    }, 'the picker never opened').toPass({timeout: 8_000});
}

/** Choose `asset` the way a reader does — open, type its name, click it — and end with the list closed. */
async function chooseInPicker(page: Page, asset: CatalogueAsset): Promise<void> {
    const trigger = page.getByTestId(`${PICKER}-trigger`);
    await openPicker(page);
    await page.getByTestId(`${PICKER}-search`).fill(asset.display_name);
    // Scoped to this picker: `search-select-option-*` is shared by every select on the page.
    const option = page.getByTestId(PICKER).getByTestId(`search-select-option-${asset.id}`);
    await expect(option, `${asset.display_name} (#${asset.id}) is not on offer on this page`).toBeVisible({timeout: 8_000});
    await option.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
}

/** The `comparison_asset_id` of every comparison the panel asked about this asset, in order. */
function comparisonIdsFor(requests: RiskRequest[], assetId: number): number[] {
    return requests
        .filter((request) => request.scope.kind === 'asset' && request.scope.asset_id === assetId)
        .flatMap((request) => request.analytics)
        .filter((analytic) => analytic.analytic_code === 'comparison')
        .map((analytic) => Number(analytic.parameters?.comparison_asset_id));
}

function askedAbout(requests: RiskRequest[], assetId: number): boolean {
    return requests.some((request) => request.scope.kind === 'asset' && request.scope.asset_id === assetId);
}

test.describe('Asset page Risk tab — the comparison opens on the shared benchmark', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('opens on the benchmark the reader chose elsewhere, and Run compares against it', async ({page}) => {
        const requests = await installRiskMocks(page);
        const {subject, benchmark} = await castAssets(page);
        await storeBenchmark(page, benchmark.id);

        await openAssetRisk(page, subject.id);

        const control = page.getByTestId(CONTROL);
        await expect(control, 'the picker did not open on the stored benchmark').toHaveAttribute('data-benchmark-id', String(benchmark.id), {timeout: 8_000});
        await expect(control).toHaveAttribute('data-measured', 'false');
        // Not this asset, so nothing to warn about — an absence asserted behind the presence above.
        await expect(page.getByTestId(`${PICKER}-measured`)).toHaveCount(0);

        const run = page.getByTestId('risk-comparison-run');
        await expect(run).toBeEnabled();
        await run.click();

        await expect.poll(() => comparisonIdsFor(requests, subject.id), {timeout: 10_000, message: 'Run sent no comparison against the stored benchmark'}).toContain(benchmark.id);
        expect(new Set(comparisonIdsFor(requests, subject.id)), 'a comparison went out against something other than the stored benchmark').toEqual(new Set([benchmark.id]));
    });

    test('when the stored benchmark is this very asset, keeps it flagged as measured and compares nothing', async ({page}) => {
        const requests = await installRiskMocks(page);
        const {subject} = await castAssets(page);
        await storeBenchmark(page, subject.id);

        await openAssetRisk(page, subject.id);

        const control = page.getByTestId(CONTROL);
        await expect(control, 'a measured benchmark must stay the current one, not be dropped').toHaveAttribute('data-benchmark-id', String(subject.id), {timeout: 8_000});
        await expect(control).toHaveAttribute('data-measured', 'true');
        await expect(page.getByTestId(`${PICKER}-measured`)).toBeVisible();
        await expect(page.getByTestId('risk-comparison-run')).toBeDisabled();

        // Presence barrier for the absence below: the panel has finished its own load, and
        // has talked to the risk endpoint about this asset — so it had every chance to ask.
        await expect(page.getByTestId('asset-detail-risk-panel').getByTestId('risk-analysis-panel')).toHaveAttribute('data-busy', 'false', {timeout: 15_000});
        await expect.poll(() => askedAbout(requests, subject.id), {timeout: 10_000, message: 'the panel never asked the risk endpoint about this asset, so "no comparison" would prove nothing'}).toBe(true);
        expect(comparisonIdsFor(requests, subject.id), 'a comparison went out although the only benchmark on offer is the asset itself').toEqual([]);
    });

    test('choosing another asset here makes it the shared choice', async ({page}) => {
        await installRiskMocks(page);
        const {subject, benchmark, held} = await castAssets(page);
        const key = await storeBenchmark(page, benchmark.id);

        await openAssetRisk(page, subject.id);
        const control = page.getByTestId(CONTROL);
        // Barrier: the stored choice was read, so what follows is a change, not a first choice.
        await expect(control).toHaveAttribute('data-benchmark-id', String(benchmark.id), {timeout: 8_000});

        // A held asset, on purpose: holding it does not disqualify it as a benchmark.
        await chooseInPicker(page, held);

        await expect(control).toHaveAttribute('data-benchmark-id', String(held.id));
        await expect.poll(() => readKey(page, key), {message: 'the choice made on the asset page did not reach the shared key'}).toBe(String(held.id));
    });

    test('with nothing stored, no benchmark is published and Run waits for a choice', async ({page}) => {
        await installRiskMocks(page);
        const {subject, held} = await castAssets(page);
        await storeBenchmark(page, null);

        await openAssetRisk(page, subject.id);
        const control = page.getByTestId(CONTROL);
        const trigger = page.getByTestId(`${PICKER}-trigger`);

        // Barrier: the picker's asset list has arrived, so a default invented from it would
        // already be published when the root is read below.
        await openPicker(page);
        await expect(page.getByTestId(PICKER).getByTestId(`search-select-option-${held.id}`)).toBeVisible({timeout: 8_000});
        await page.getByTestId(`${PICKER}-search`).press('Escape');
        await expect(trigger).toHaveAttribute('aria-expanded', 'false');

        await expect(control, 'with nothing stored the root must publish an empty data-benchmark-id').toHaveAttribute('data-benchmark-id', '');
        await expect(control).toHaveAttribute('data-measured', 'false');
        await expect(page.getByTestId(`${PICKER}-measured`)).toHaveCount(0);
        await expect(page.getByTestId('risk-comparison-run')).toBeDisabled();

        await chooseInPicker(page, held);

        await expect(control).toHaveAttribute('data-benchmark-id', String(held.id));
        await expect(page.getByTestId('risk-comparison-run')).toBeEnabled();
    });
});
