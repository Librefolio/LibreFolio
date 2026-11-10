/**
 * Scheduler Settings E2E Tests
 *
 * Tests the scheduler configuration modal, log modal, and status row
 * in the Global Settings (Admin) tab. Also includes regression test
 * for fetch_interval removal from provider assignment forms.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py db populate --test)
 *
 * Test IDs: FSCH-001..FSCH-010
 */

import {type APIRequestContext, expect, type Page, test} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {openSettingsTab} from '../fixtures/settings-tabs';
import {TEST_ADMIN} from '../fixtures/test-users';
import {API_BASE, goToAssetDetailPage, openEditAssetModal} from '../assets/assets-helpers';
import {eventSeq, waitForEvent} from '../fixtures/app-events';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Navigate to Settings → Admin tab → Global Settings with sync category visible.
 * Waits for the scheduler rows to be present.
 */
async function goToSchedulerSettings(page: import('@playwright/test').Page) {
    await login(page, TEST_ADMIN);
    await navigateTo(page, '/settings');
    await openSettingsTab(page, 'admin');
    await expect(page.getByTestId('global-settings-tab')).toBeVisible({timeout: 10_000});

    // Click the "Scheduler & Upload" category so the scheduler rows are visible.
    // By id, not by its label: the label is translated (EN/IT/FR/ES) and a test that
    // reads it only passes in the language the suite happens to run in.
    await page.getByTestId('global-settings-category-sync').click();

    // Wait for scheduler rows
    await expect(page.getByTestId('scheduler-status-row')).toBeVisible({timeout: 10_000});
}

// ---------------------------------------------------------------------------
// FSCH-001: Scheduler status row visible for admin
// ---------------------------------------------------------------------------

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers. The one exception
// is the pair of Config Modal tests that save: they run in sequence (see there).
test.describe.configure({mode: 'parallel'});

test.describe('Scheduler — Visibility', () => {
    test('FSCH-001: scheduler status row is visible for admin', async ({page}) => {
        await goToSchedulerSettings(page);
        await expect(page.getByTestId('scheduler-status-row')).toBeVisible();
    });

    test('FSCH-002: scheduler config row is visible for admin', async ({page}) => {
        await goToSchedulerSettings(page);
        await expect(page.getByTestId('scheduler-config-row')).toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// FSCH-003..004: Log modal open / close
// ---------------------------------------------------------------------------

test.describe('Scheduler — Log Modal', () => {
    test.beforeEach(async ({page}) => {
        await goToSchedulerSettings(page);
    });

    test('FSCH-003: click status row opens log modal', async ({page}) => {
        await page.getByTestId('scheduler-status-row').click();
        await expect(page.getByTestId('scheduler-log-entries')).toBeVisible({timeout: 5_000});
    });

    test('FSCH-004: log modal closes on close button', async ({page}) => {
        await page.getByTestId('scheduler-status-row').click();
        await expect(page.getByTestId('scheduler-log-entries')).toBeVisible({timeout: 5_000});

        await page.getByTestId('scheduler-log-close').click();
        await expect(page.getByTestId('scheduler-log-entries')).not.toBeVisible({timeout: 3_000});
    });

    test('FSCH-004b: log modal closes on Escape key', async ({page}) => {
        await page.getByTestId('scheduler-status-row').click();
        await expect(page.getByTestId('scheduler-log-entries')).toBeVisible({timeout: 5_000});

        await page.keyboard.press('Escape');
        await expect(page.getByTestId('scheduler-log-entries')).not.toBeVisible({timeout: 3_000});
    });
});

// ---------------------------------------------------------------------------
// FSCH-011..015: what is actually INSIDE the log modal
//
// The three tests above open the modal and close it again; nothing looks in.
// That left the filters, the per-entry status and the collapsible detail —
// most of the component — unexercised.
//
// Two things had to be published first, because both were readable only from
// Tailwind classes, and asserting on those tests the palette rather than the
// behaviour: each entry now carries `data-job`, `data-status`, `data-expanded`
// and `data-has-detail`, and the three filter selects hand their options a
// testid so a filter can be driven without clicking translated text.
// ---------------------------------------------------------------------------

const LOG_ENTRY = '[data-testid="scheduler-log-entry"]';

async function openLogModal(page: import('@playwright/test').Page) {
    await page.getByTestId('scheduler-status-row').click();
    const entries = page.getByTestId('scheduler-log-entries');
    await expect(entries).toBeVisible({timeout: 5_000});
    // Visible is not loaded: the container publishes data-busy for exactly this.
    await expect(entries).toHaveAttribute('data-busy', 'false', {timeout: 10_000});
    // The time filter defaults to "last 24 hours" and the seeded runs are dated
    // *yesterday*, so how many of them are on screen depends on what time of day the
    // suite runs — at 21:40 exactly one of the five survives. Widening to "all" is the
    // precondition these tests need, and stating it is cheaper than a test that passes
    // in the morning and fails in the evening.
    await setLogFilter(page, 'time', 'all');
    return entries;
}

/** Pick a value in one of the modal's three filter selects. */
async function setLogFilter(page: import('@playwright/test').Page, filter: 'job' | 'status' | 'time', value: string) {
    await page.getByTestId(`scheduler-log-filter-${filter}-button`).click();
    const option = page.getByTestId(`scheduler-log-filter-${filter}-option-${value}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    // The dropdown closing is the post-condition this helper promises: leaving it
    // open makes the next filter's options overlap it in the DOM.
    await expect(page.getByTestId(`scheduler-log-filter-${filter}-dropdown`)).toBeHidden({timeout: 3_000});
}

test.describe('Scheduler — Log Modal contents', () => {
    test.beforeEach(async ({page}) => {
        await goToSchedulerSettings(page);
    });

    test('FSCH-011: entries publish a job and a status, and the mock supplies all three statuses', async ({page}) => {
        await openLogModal(page);

        // populate_mock_data seeds current_price runs that are ok, partial and error,
        // plus history_sync runs. Asserting that each of the three is *present* says
        // the status made it from the joblog to the DOM; it is not a count of how many
        // there are, which a neighbour could change.
        for (const status of ['ok', 'partial', 'error']) {
            await expect(page.locator(`${LOG_ENTRY}[data-status="${status}"]`).first(), `the log should contain at least one ${status} run — check the joblog seeding in populate_mock_data.py`).toBeVisible({timeout: 5_000});
        }
        await expect(page.locator(`${LOG_ENTRY}[data-job="current_price"]`).first()).toBeVisible();
        await expect(page.locator(`${LOG_ENTRY}[data-job="history_sync"]`).first()).toBeVisible();
    });

    test('FSCH-012: the status filter leaves only entries of that status', async ({page}) => {
        await openLogModal(page);
        await expect(page.locator(`${LOG_ENTRY}[data-status="ok"]`).first()).toBeVisible({timeout: 5_000});

        await setLogFilter(page, 'status', 'error');

        // The assertion is a *relation*, not a number: whatever survives the filter must
        // carry the status asked for. That holds no matter how many runs the joblog has,
        // which is the only form of this assertion that survives a shared database.
        const shown = page.locator(LOG_ENTRY);
        await expect(shown.first()).toBeVisible({timeout: 5_000});
        const total = await shown.count();
        expect(total, 'filtering to error must leave the error runs on screen').toBeGreaterThan(0);
        expect(await page.locator(`${LOG_ENTRY}[data-status="error"]`).count()).toBe(total);
    });

    test('FSCH-013: the job filter leaves only entries of that job', async ({page}) => {
        await openLogModal(page);
        await expect(page.locator(`${LOG_ENTRY}[data-job="current_price"]`).first()).toBeVisible({timeout: 5_000});

        await setLogFilter(page, 'job', 'history_sync');

        const shown = page.locator(LOG_ENTRY);
        await expect(shown.first()).toBeVisible({timeout: 5_000});
        const total = await shown.count();
        expect(total).toBeGreaterThan(0);
        expect(await page.locator(`${LOG_ENTRY}[data-job="history_sync"]`).count()).toBe(total);
    });

    test('FSCH-014: an entry with detail expands and collapses, and shows its items', async ({page}) => {
        await openLogModal(page);

        // Only entries that have something to show are clickable — the component renders
        // the others as a plain div. So this asks for one that can actually expand rather
        // than assuming the first entry qualifies.
        const expandable = page.locator(`${LOG_ENTRY}[data-has-detail="true"]`).first();
        await expect(expandable, 'the seeded joblog should contain at least one run with per-item detail').toBeVisible({timeout: 5_000});
        await expect(expandable).toHaveAttribute('data-expanded', 'false');

        await expandable.getByRole('button').first().click();
        await expect(expandable).toHaveAttribute('data-expanded', 'true');
        await expect(expandable.getByTestId('scheduler-log-entry-detail')).toBeVisible();

        await expandable.getByRole('button').first().click();
        await expect(expandable).toHaveAttribute('data-expanded', 'false');
        await expect(expandable.getByTestId('scheduler-log-entry-detail')).toHaveCount(0);
    });

    test('FSCH-015: a filter that matches nothing says so instead of showing a blank list', async ({page}) => {
        await openLogModal(page);
        await expect(page.locator(LOG_ENTRY).first()).toBeVisible({timeout: 5_000});

        // The mock seeds current_price runs in all three statuses but history_sync only
        // as ok and partial, so "history_sync that failed outright" is a combination the
        // joblog cannot satisfy. An empty list and an unloaded list look identical
        // without help: the component publishes an explicit "no entries" node, and this
        // is what asks for it.
        await setLogFilter(page, 'job', 'history_sync');
        await setLogFilter(page, 'status', 'error');

        await expect(page.getByTestId('scheduler-log-empty')).toBeVisible({timeout: 5_000});
        await expect(page.locator(LOG_ENTRY)).toHaveCount(0);
    });
});

// ---------------------------------------------------------------------------
// FSCH-005..009: Config modal
// ---------------------------------------------------------------------------

/**
 * What the modal's Save writes: all five of these *global* settings, every time, in one
 * PATCH /settings/global/bulk (SchedulerConfigModal.handleSave). A test that changes only
 * the frequency still rewrites the other four, for every user of the instance, so a
 * writer snapshots all five and puts all five back.
 */
const SCHEDULER_KEYS = ['scheduler_current_price_frequency_minutes', 'scheduler_history_sync_times', 'scheduler_history_sync_days', 'scheduler_history_sync_horizon_days', 'scheduler_timezone'] as const;
type SchedulerSettings = Record<(typeof SCHEDULER_KEYS)[number], string>;
const BULK_PATH = `${API_BASE}/settings/global/bulk`;

/**
 * Sign the test's own API context in as the admin: the POST /auth/login the restore makes, and like it independent of
 * the browser. Once, before the first read: the context keeps the session cookie for every request after it.
 */
async function signInAsAdmin(request: APIRequestContext): Promise<void> {
    const signedIn = await request.post(`${API_BASE}/auth/login`, {data: {username: TEST_ADMIN.username, password: TEST_ADMIN.password}});
    expect(signedIn.ok(), `The test's API context could not sign in as ${TEST_ADMIN.username} (HTTP ${signedIn.status()})`).toBe(true);
}

/**
 * The scheduler's global settings as stored: a signed-in read since decision 36 (A6d), so `request` must be signed in
 * first (`signInAsAdmin`, or the restore's own sign-in).
 */
async function readSchedulerSettings(request: APIRequestContext): Promise<SchedulerSettings> {
    const response = await request.get(`${API_BASE}/settings/global`);
    expect(response.ok(), `GET ${API_BASE}/settings/global returned ${response.status()}`).toBe(true);
    const {items} = (await response.json()) as {items: Array<{key: string; value: string}>};
    const stored = {} as SchedulerSettings;
    for (const key of SCHEDULER_KEYS) {
        const item = items.find((candidate) => candidate.key === key);
        if (!item) throw new Error(`Global setting ${key} is missing: check initGlobalSettings in e2e/global-setup.ts`);
        stored[key] = item.value;
    }
    return stored;
}

/**
 * Put back exactly what `before` held, through the endpoint the modal writes with, and
 * read it back. `request` is the test's own API context, signed in here as the admin, so
 * the restore does not depend on the browser surviving whatever failed. Only the values
 * come back: the rows keep this write's updated_at / updated_by.
 */
async function restoreSchedulerSettings(request: APIRequestContext, before: SchedulerSettings): Promise<void> {
    const signedIn = await request.post(`${API_BASE}/auth/login`, {data: {username: TEST_ADMIN.username, password: TEST_ADMIN.password}});
    expect(signedIn.ok(), `The restore could not sign in as ${TEST_ADMIN.username} (HTTP ${signedIn.status()})`).toBe(true);
    const restored = await request.patch(BULK_PATH, {data: {items: SCHEDULER_KEYS.map((key) => ({key, value: before[key]}))}});
    expect(restored.ok(), `Restoring the scheduler settings failed (HTTP ${restored.status()}): ${await restored.text()}`).toBe(true);
    expect(await readSchedulerSettings(request), 'the scheduler settings are back to what the test found').toEqual(before);
}

/** A frequency other than the stored one, so the save is a real change. */
function otherFrequency(before: SchedulerSettings, preferred: number): string {
    return String(before.scheduler_current_price_frequency_minutes === String(preferred) ? preferred + 1 : preferred);
}

/**
 * Unlock the Admin tab. It opens locked, and the lock is exactly what disables Configure,
 * so that button's own state is both the precondition and the proof the unlock took: no
 * translated title, and no probe deciding whether to click a toggle.
 */
async function unlockSchedulerConfig(page: Page) {
    const configure = page.getByTestId('scheduler-config-btn');
    await expect(configure, 'precondition: a freshly loaded Admin tab is locked').toBeDisabled();
    await page.getByTestId('global-settings-tab').getByTestId('settings-lock-toggle').click();
    await expect(configure).toBeEnabled();
    return configure;
}

/** Unlock, open the config modal, and wait for its form. */
async function openSchedulerConfig(page: Page) {
    await (await unlockSchedulerConfig(page)).click();
    await expect(page.getByTestId('scheduler-config-frequency')).toBeVisible({timeout: 5_000});
}

/** Save, and wait for the server's answer: a later failure then never races the write its restore undoes. */
async function saveSchedulerConfig(page: Page) {
    const patched = page.waitForResponse((res) => res.request().method() === 'PATCH' && new URL(res.url()).pathname === BULK_PATH, {timeout: 5_000});
    await page.getByTestId('scheduler-config-save').click();
    const response = await patched;
    expect(response.ok(), `PATCH ${BULK_PATH} returned ${response.status()}`).toBe(true);
    return response;
}

test.describe('Scheduler — Config Modal', () => {
    test.beforeEach(async ({page}) => {
        await goToSchedulerSettings(page);
    });

    test('FSCH-005: click Configure opens config modal', async ({page}) => {
        const configure = await unlockSchedulerConfig(page);
        await configure.click();
        await expect(page.getByTestId('scheduler-config-frequency')).toBeVisible({timeout: 5_000});
    });

    // The file's only writers. Save rewrites five instance-wide settings, so each of
    // them snapshots those before acting and restores them in `finally`.
    test.describe('Saving', () => {
        // Why serial: a snapshot is the baseline only while no other writer sits between it
        // and its restore. Side by side, FSCH-006b could snapshot the value FSCH-006 has
        // just saved and "restore" that, leaving it on the instance for everyone. In
        // sequence each one starts from the value the other has already put back.
        test.describe.configure({mode: 'serial'});

        test('FSCH-006: config modal saves frequency change via PATCH /global/bulk', async ({page, request}) => {
            await signInAsAdmin(request);
            const before = await readSchedulerSettings(request);
            const frequency = otherFrequency(before, 15);
            try {
                await openSchedulerConfig(page);
                const freqInput = page.getByTestId('scheduler-config-frequency').locator('input');
                // Precondition, read back: the modal starts from the stored value.
                await expect(freqInput).toHaveValue(before.scheduler_current_price_frequency_minutes);
                await freqInput.fill(frequency);

                const since = await eventSeq(page);
                const response = await saveSchedulerConfig(page);

                // Verify the PATCH payload contains the frequency key with new value
                const items: Array<{key: string; value: string}> = response.request().postDataJSON()?.items ?? [];
                const freqItem = items.find((i) => i.key === 'scheduler_current_price_frequency_minutes');
                expect(freqItem).toBeDefined();
                expect(freqItem?.value).toBe(frequency);

                // The modal closes on success and the schedule is shown nowhere else, so the toast
                // is the only thing separating "saved" from "dismissed".
                await expect(page.getByTestId('toast-success')).toBeVisible({timeout: 5_000});
                const saved = await waitForEvent(page, 'settings.scheduler.saved', {since});
                expect(saved.detail?.frequencyMinutes).toBe(Number(frequency));
                // And the server holds it: the write the restore below has to undo.
                expect((await readSchedulerSettings(request)).scheduler_current_price_frequency_minutes).toBe(frequency);
            } finally {
                await restoreSchedulerSettings(request, before);
            }
        });

        test('FSCH-006b: a toast can be dismissed by swiping it away', async ({page, request}) => {
            // Riding on the one operation that already writes: no extra mutation, and the toast
            // it raises is a real one rather than a fabricated fixture. Its write is undone in
            // `finally`, like FSCH-006's.
            await signInAsAdmin(request);
            const before = await readSchedulerSettings(request);
            try {
                await openSchedulerConfig(page);
                const freqInput = page.getByTestId('scheduler-config-frequency').locator('input');
                await expect(freqInput).toHaveValue(before.scheduler_current_price_frequency_minutes);
                await freqInput.fill(otherFrequency(before, 20));
                await saveSchedulerConfig(page);

                const toast = page.getByTestId('toast-success');
                await expect(toast).toBeVisible({timeout: 5_000});

                const box = await toast.boundingBox();
                expect(box, 'toast must have a box to drag').toBeTruthy();
                const y = box!.y + box!.height / 2;
                // Start left of centre so the drag cannot begin on the ✕ in the top-right corner.
                await page.mouse.move(box!.x + 20, y);
                await page.mouse.down();
                await page.mouse.move(box!.x + 20 + 140, y, {steps: 12});
                await page.mouse.up();

                await expect(toast).toBeHidden({timeout: 3_000});
            } finally {
                await restoreSchedulerSettings(request, before);
            }
        });
    });

    test('FSCH-007: Cancel discards changes without PATCH request', async ({page}) => {
        await openSchedulerConfig(page);

        // Change frequency value
        await page.getByTestId('scheduler-config-frequency').locator('input').fill('99');

        // Track whether PATCH was called
        let patchCalled = false;
        page.on('request', (req) => {
            if (req.method() === 'PATCH' && req.url().includes('/settings/global/bulk')) {
                patchCalled = true;
            }
        });

        // Cancel
        await page.getByTestId('scheduler-config-cancel').click();
        // Assert the close first: "no PATCH was sent" is only meaningful once
        // the modal has actually finished doing whatever it was going to do.
        await expect(page.getByTestId('scheduler-config-frequency')).not.toBeVisible({timeout: 10_000});
        expect(patchCalled).toBe(false);
    });

    test('FSCH-008: add time slot appears in the list', async ({page}) => {
        await openSchedulerConfig(page);
        await expect(page.getByTestId('scheduler-config-times')).toBeVisible({timeout: 5_000});

        // Time slots are rendered as <span class="rounded-full"> badge elements (not <li>)
        const timesSection = page.getByTestId('scheduler-config-times');
        const initialSlots = await timesSection.locator('span.rounded-full').count();

        // Add a new time slot
        await page.getByTestId('scheduler-config-time-input').fill('12:00');
        await page.getByTestId('scheduler-config-time-add').click();

        // Slot count should have increased
        await expect.poll(() => timesSection.locator('span.rounded-full').count(), {timeout: 10_000}).toBeGreaterThan(initialSlots);
    });

    test('FSCH-009: delete time slot removes it from list', async ({page}) => {
        await openSchedulerConfig(page);
        await expect(page.getByTestId('scheduler-config-times')).toBeVisible({timeout: 5_000});

        const timesSection = page.getByTestId('scheduler-config-times');

        // Time slots are <span class="rounded-full"> (not <li>)
        let initialCount = await timesSection.locator('span.rounded-full').count();

        if (initialCount < 2) {
            // Need at least 2 to delete one — add a slot first
            await page.getByTestId('scheduler-config-time-input').fill('14:00');
            await page.getByTestId('scheduler-config-time-add').click();
            await expect.poll(() => timesSection.locator('span.rounded-full').count(), {timeout: 10_000}).toBeGreaterThan(initialCount);
            initialCount = await timesSection.locator('span.rounded-full').count();
        }

        // Delete first slot via its remove button (the <button> inside the span badge)
        const firstSlotDeleteBtn = timesSection.locator('span.rounded-full button').first();
        await firstSlotDeleteBtn.click();

        await expect.poll(() => timesSection.locator('span.rounded-full').count(), {timeout: 10_000}).toBeLessThan(initialCount);
    });
});

// ---------------------------------------------------------------------------
// FSCH-010: Regression — no fetch_interval field in provider assignment forms
// ---------------------------------------------------------------------------

test.describe('Scheduler — Regression (fetch_interval removed)', () => {
    test('FSCH-010: provider assignment form has no fetch_interval field', async ({page}) => {
        await login(page, TEST_ADMIN);

        // Ask the API for an asset instead of hunting the list. The list has two
        // interchangeable views (table/cards, persisted in localStorage), so probing
        // for one and falling back to the other used to end in `test.skip()` whenever
        // both probes timed out under load — the regression silently unguarded.
        const response = await page.request.get(`${API_BASE}/assets/query?active=true`);
        expect(response.ok(), `GET ${API_BASE}/assets/query returned ${response.status()}`).toBe(true);
        const assets = (await response.json()) as Array<{id: number}>;
        const assetId = assets[0]?.id;
        expect(assetId, 'the seeded database must contain at least one active asset').toBeDefined();

        await goToAssetDetailPage(page, String(assetId));
        await openEditAssetModal(page);

        // There must be no input with name/id/placeholder related to fetch_interval
        const fetchIntervalInput = page.locator('input[name="fetch_interval"], input[id*="fetch_interval"], input[placeholder*="fetch interval" i]');
        await expect(fetchIntervalInput).toHaveCount(0);
    });
});
