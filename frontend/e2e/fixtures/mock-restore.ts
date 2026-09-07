/**
 * The safety net for specs that walk the *destructive* routes.
 *
 * The two `*-destructive` specs delete files, FX pairs and FX rates — rows that
 * live in global, user-less-ish tables (or, for files, the shared uploads dir)
 * that every other spec reads. Their primary restore is precise: each test
 * deletes only the disposable rows it created, identified by a unique marker, so
 * the mock baseline is never touched and the database is left exactly as found.
 *
 * This module is the *net* underneath that, not the strategy. It mirrors the
 * `restore()` half of the tx-hygiene fixture in `playwright.ts`:
 *
 *   1. a spec snapshots the mock baseline in `beforeAll` (a set of ids/slugs it
 *      must never destroy);
 *   2. in `afterAll`, after the precise cleanup, it asks whether every baseline
 *      member is still there. If one vanished, a mock row was destroyed and no
 *      API call can bring it back with its original id — so the only faithful
 *      repair is a full `populate_mock_data --force`.
 *
 * ### Why it disables itself under `--workers > 1`
 *
 * `populate_mock_data --force` unlinks the whole SQLite file and rebuilds it.
 * Run inside a parallel category it would wipe the database while sibling specs
 * on the other three workers are mid-assertion — the exact catastrophe the
 * tx-hygiene fixture avoids by switching off above one worker. The DoD run is
 * `--workers 4`, so the net is *suppressed there by construction*; the precise
 * cleanup is what keeps that run green, and the second `--workers 4` pass on the
 * database the first one left is the proof it did.
 *
 * At `--workers 1` (a single-spec debug run, or the runner's own probes) the net
 * is live and the baseline check is accurate, because nobody else is writing.
 */
import {request as playwrightRequest, type APIRequestContext} from '@playwright/test';
import {TEST_USER} from './test-users';

/** Same base URL Playwright's config computes (`playwright.config.ts`). */
export const E2E_BASE_URL = `http://localhost:${process.env.TEST_PORT || '6041'}`;

/** The worker count the runner decided, surfaced exactly as `playwright.ts` reads it. */
export const E2E_WORKERS = Math.max(1, Number(process.env.E2E_WORKERS || '1') || 1);

/** True only when it is safe to run a destructive full repopulate — i.e. no sibling worker. */
export const REPOPULATE_ALLOWED = E2E_WORKERS <= 1;

/**
 * A fresh API context, logged in as the default E2E user.
 *
 * Used from `afterAll`, where the per-test `page` (and its authenticated
 * `page.request`) no longer exists. `page.request` shares the browser cookie
 * jar; here we mint a standalone context and authenticate it the same way the
 * tx-hygiene net does. Returns `null` on any failure — cleanup must never turn a
 * green run red.
 */
export async function apiLogin(): Promise<APIRequestContext | null> {
    try {
        const ctx = await playwrightRequest.newContext({baseURL: E2E_BASE_URL});
        const res = await ctx.post('/api/v1/auth/login', {
            data: {username: TEST_USER.username, password: TEST_USER.password},
        });
        if (!res.ok()) {
            await ctx.dispose();
            return null;
        }
        return ctx;
    } catch {
        return null;
    }
}

/**
 * Full mock repopulate — the faithful repair for a destroyed baseline.
 *
 * Identical to `repopulate()` in `playwright.ts`: run the seeder with `--force`,
 * then replay `initGlobalSettings()` (the one part of `globalSetup` the seeder
 * does not recreate). Never call this without checking {@link REPOPULATE_ALLOWED}
 * first.
 */
export async function repopulateMockData(): Promise<boolean> {
    try {
        const {execSync} = await import('node:child_process');
        const path = await import('node:path');
        // e2e/fixtures → e2e → frontend → repo root
        const root = path.resolve(import.meta.dirname, '..', '..', '..');
        execSync('pipenv run python -m backend.test_scripts.test_db.populate_mock_data --force --with-reports', {
            cwd: root,
            stdio: 'pipe',
            timeout: 120_000,
        });
        const {initGlobalSettings} = await import('../global-setup');
        await initGlobalSettings();
        return true;
    } catch (e) {
        console.warn('[mock-restore] repopulate failed, leaving the database as it is:', e);
        return false;
    }
}
