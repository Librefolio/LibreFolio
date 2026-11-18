/**
 * Asset page, Risk tab — L3 measures against the SHARED benchmark.
 *
 * Owner: the Risk workstream. Developer decision, 01/10/2026: wherever a page measures
 * against a benchmark there is a picker; on load it shows the current benchmark, and it
 * is empty only when nothing is set. The asset page's Risk tab uses that shared choice —
 * it opens on it, and changing it there changes it everywhere. Holding an asset does not
 * disqualify it as a benchmark; being the asset the page measures does.
 *
 * Since RN-17 the tab mounts the levels panel on the asset, so the picker is L3's — the
 * Dashboard's own, `risk-l3-benchmark-select` — and L3 compares by itself once the choice
 * is confirmed (`set`): there is no «Run» button any more. Four cases, each read off the
 * state the picker publishes on its root — `risk-l3-benchmark-select-control`, with
 * `data-benchmark-id` (the resolved value, '' when there is none) and
 * `data-benchmark-state` — and off what reaches the wire; never off an icon or a label:
 *   1. a stored benchmark opens the tab with the picker on it, and L3 sends a
 *      `comparison` whose `comparison_asset_id` is that id;
 *   2. a stored benchmark that IS this asset is still the current one — never dropped from
 *      the picker nor from storage — L3 says why (`risk-l3-benchmark-is-subject`), and
 *      nothing is compared: the backend would refuse a yardstick that is also the subject;
 *   3. choosing another asset here writes the reader's shared key;
 *   4. nothing stored: no benchmark published and nothing compared, until a choice is made.
 *
 * Registered as `front-portfolio risk-benchmark-shared` (the `-unit` action next to it is
 * the store's).
 *
 * The eligibility engine is answered here, every asked asset admitted (`answerEligibility`):
 * the lane's engine judges the seed's prices against today's date, and its verdicts would
 * decide whether a stored choice is `set` or `blocked` — D378's subject, pinned in
 * `risk-asset-detail.spec.ts`, not this file's.
 *
 * Nothing to restore: the risk endpoints are mocked, the choice lives in this context's
 * `localStorage` (which dies with the context), and no database row is written — the page's
 * live-price poll included, held for the whole test (`holdLivePricePoll`) — so every
 * test runs beside its neighbours.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';

import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {schemas} from '../../src/lib/api/generated';
import {installRiskMocks, waitForRiskCatalog, type RiskRequest} from './risk-mocks';

/** L3's picker on the asset page: `-trigger`, `-search` and `-control` hang off it. */
const PICKER = 'risk-l3-benchmark-select';
/** Its root, where the page publishes the choice and how far it got confirming it. */
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

/**
 * Answer `POST /risk/eligibility` with every asked asset admitted: a copy, reduced to that one
 * verdict, of `answerEligibility` in `risk-lab.spec.ts` (a spec may not import another). The body
 * goes through the generated schema, because the client validates every response.
 */
async function answerEligibility(page: Page): Promise<void> {
    await page.route('**/api/v1/risk/eligibility', async (route) => {
        const sent = (route.request().postDataJSON() ?? {}) as {asset_ids?: number[]; date_range?: {start?: string; end?: string | null}};
        const start = sent.date_range?.start ?? '';
        const lastDay = sent.date_range?.end ?? start;
        const body = schemas.RiskEligibilityResponse.parse({
            items: [...new Set(sent.asset_ids ?? [])].map((assetId) => ({asset_id: assetId, level: 'eligible', reasons: [], first_quote: start, last_quote: lastDay, quotes_in_period: 60})),
            min_quotes: 20,
            stale_days: 7,
        });
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)}).catch(() => undefined);
    });
}

/**
 * The asset's page, Risk tab, by a full document load; returns the levels panel once its
 * capability catalogue is in and L3's picker is up.
 */
async function openAssetRisk(page: Page, assetId: number): Promise<Locator> {
    await navigateTo(page, `/assets/${assetId}?tab=risk`);
    await expect(page.getByTestId('asset-detail-risk-panel')).toBeVisible({timeout: 15_000});
    // Every section is gated on the capability catalog: wait for the gate, then for what is behind it.
    const panel = await waitForRiskCatalog(page);
    await expect(panel.getByTestId('risk-l3-benchmark')).toBeVisible();
    return panel;
}

/**
 * The barrier every «nothing compared» below is read after: the panel's base wave has landed
 * and it talked to the risk endpoint about this asset, so it had every chance to ask.
 */
async function expectBaseWave(panel: Locator, requests: RiskRequest[], assetId: number): Promise<void> {
    await expect(panel).toHaveAttribute('data-busy', 'false', {timeout: 15_000});
    await expect.poll(() => askedAbout(requests, assetId), {timeout: 10_000, message: 'the panel never asked the risk endpoint about this asset, so "no comparison" would prove nothing'}).toBe(true);
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

/**
 * Hold the asset page's live-price poll, unanswered, for the whole test.
 *
 * A copy of `holdLivePricePoll` in `risk-lab.spec.ts`, with exactly its behaviour — the same
 * pattern, the same empty handler — because Playwright refuses to let one test file import
 * another: a change to one is a change to both.
 *
 * Every test here opens `/assets/{id}`, which polls `POST /assets/prices/current` for its asset
 * on load and every 30 s, and from a second timer 5 s in and every minute after. Once the US
 * market is open, an answered poll asks the live provider and writes today's price into the
 * lane's database — measured on 05/10/2026 at 14:53Z, one run of this file without the hold:
 * Yahoo's `current_value for MSFT` and four «Intra-day price extend» writes on that asset; with
 * the hold, none. And `zodios-client` turns every answered poll into a portfolio mutation, which
 * drops the risk cache and discards whatever comparison is in flight: a background actor racing
 * the very requests these tests read.
 *
 * Held, never answered, because nothing else is inert: a stubbed answer still passes through that
 * interceptor and still invalidates. An unanswered call does nothing at all: each poller awaits it
 * and, after axios's 30 s timeout, gives up without a word. The handler calls no route method, so
 * nothing can throw when the context closes. Installed first in `beforeEach`, before any page is
 * open. No test here opens the sync modal, so no FX provider catalogue is asked for and none is held.
 *
 * ⚠️ This isolates the tests; it repairs nothing. Outside this file the poll still reaches the
 * providers and writes on every visit.
 */
async function holdLivePricePoll(page: Page): Promise<void> {
    await page.route(/\/api\/v1\/assets\/prices\/current(?:\?|$)/, () => {
        // Deliberately neither fulfilled nor continued: see above.
    });
}

test.describe('Asset page Risk tab — L3 opens on the shared benchmark', () => {
    test.beforeEach(async ({page}) => {
        await holdLivePricePoll(page);
        await login(page, TEST_USER);
    });

    test('opens on the benchmark the reader chose elsewhere, and L3 compares against it', async ({page}) => {
        const requests = await installRiskMocks(page);
        await answerEligibility(page);
        const {subject, benchmark} = await castAssets(page);
        await storeBenchmark(page, benchmark.id);

        const panel = await openAssetRisk(page, subject.id);

        const control = panel.getByTestId(CONTROL);
        await expect(control, 'the picker did not open on the stored benchmark').toHaveAttribute('data-benchmark-id', String(benchmark.id), {timeout: 8_000});
        await expect(control, 'the stored benchmark was never confirmed').toHaveAttribute('data-benchmark-state', 'set', {timeout: 10_000});
        // Not this asset, so nothing to say about it — an absence asserted behind the presence above.
        await expect(panel.getByTestId('risk-l3-benchmark-is-subject')).toHaveCount(0);

        await expect.poll(() => comparisonIdsFor(requests, subject.id), {timeout: 10_000, message: 'L3 sent no comparison against the stored benchmark'}).toContain(benchmark.id);
        expect(new Set(comparisonIdsFor(requests, subject.id)), 'a comparison went out against something other than the stored benchmark').toEqual(new Set([benchmark.id]));
    });

    test('when the stored benchmark is this very asset, keeps it as the choice, says why and compares nothing', async ({page}) => {
        const requests = await installRiskMocks(page);
        await answerEligibility(page);
        const {subject} = await castAssets(page);
        const key = await storeBenchmark(page, subject.id);

        const panel = await openAssetRisk(page, subject.id);

        const control = panel.getByTestId(CONTROL);
        await expect(control, 'the asset itself must stay the current benchmark, not be dropped').toHaveAttribute('data-benchmark-id', String(subject.id), {timeout: 8_000});
        // `set` first: a choice still `pending` compares nothing either, and the absence below would be about that.
        await expect(control).toHaveAttribute('data-benchmark-state', 'set', {timeout: 10_000});
        await expect(panel.getByTestId('risk-l3-benchmark-is-subject')).toBeVisible();

        // Presence barrier for the absence below: the panel has finished its own load, and
        // has talked to the risk endpoint about this asset — so it had every chance to ask.
        await expectBaseWave(panel, requests, subject.id);
        expect(comparisonIdsFor(requests, subject.id), 'a comparison went out although the benchmark is the asset itself').toEqual([]);
        expect(await readKey(page, key), 'the shared choice was dropped because this page measures it').toBe(String(subject.id));
    });

    test('choosing another asset here makes it the shared choice', async ({page}) => {
        await installRiskMocks(page);
        await answerEligibility(page);
        const {subject, benchmark, held} = await castAssets(page);
        const key = await storeBenchmark(page, benchmark.id);

        const panel = await openAssetRisk(page, subject.id);
        const control = panel.getByTestId(CONTROL);
        // Barrier: the stored choice was read, so what follows is a change, not a first choice.
        await expect(control).toHaveAttribute('data-benchmark-id', String(benchmark.id), {timeout: 8_000});

        // A held asset, on purpose: holding it does not disqualify it as a benchmark.
        await chooseInPicker(page, held);

        await expect(control).toHaveAttribute('data-benchmark-id', String(held.id));
        await expect.poll(() => readKey(page, key), {message: 'the choice made on the asset page did not reach the shared key'}).toBe(String(held.id));
    });

    test('with nothing stored, no benchmark is published and nothing is compared until a choice is made', async ({page}) => {
        const requests = await installRiskMocks(page);
        await answerEligibility(page);
        const {subject, held} = await castAssets(page);
        await storeBenchmark(page, null);

        const panel = await openAssetRisk(page, subject.id);
        const control = panel.getByTestId(CONTROL);
        const trigger = page.getByTestId(`${PICKER}-trigger`);

        // Barrier: the picker's asset list has arrived, so a default invented from it would
        // already be published when the root is read below.
        await openPicker(page);
        await expect(page.getByTestId(PICKER).getByTestId(`search-select-option-${held.id}`)).toBeVisible({timeout: 8_000});
        await page.getByTestId(`${PICKER}-search`).press('Escape');
        await expect(trigger).toHaveAttribute('aria-expanded', 'false');

        await expect(control, 'with nothing stored the root must publish an empty data-benchmark-id').toHaveAttribute('data-benchmark-id', '');
        await expect(control).toHaveAttribute('data-benchmark-state', 'none');
        await expectBaseWave(panel, requests, subject.id);
        expect(comparisonIdsFor(requests, subject.id), 'a comparison went out with no benchmark chosen').toEqual([]);

        await chooseInPicker(page, held);

        await expect(control).toHaveAttribute('data-benchmark-id', String(held.id));
        await expect(control).toHaveAttribute('data-benchmark-state', 'set', {timeout: 10_000});
        await expect.poll(() => comparisonIdsFor(requests, subject.id), {timeout: 10_000, message: 'the choice was not compared'}).toEqual([held.id]);
    });
});
