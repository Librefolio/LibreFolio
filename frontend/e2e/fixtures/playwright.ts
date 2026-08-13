/**
 * Barrel Playwright con raccolta di coverage JS.
 *
 * Gli spec importano da qui invece che da '@playwright/test'. Il modulo
 * ri-esporta gli stessi simboli, quindi per gli spec cambia solo il percorso.
 *
 * La raccolta è attiva solo con COVERAGE_JS=1 (impostato da
 * `./dev.py test --coverage js|all`): a flag spento la fixture esce subito e
 * la corsa normale non paga nulla.
 *
 * Nota sull'architettura: qui si chiama solo `mcr.add()`, mai `generate()`.
 * Playwright viene invocato una volta per spec, quindi i dati devono
 * accumularsi nella cache di monocart e il report va prodotto una sola volta
 * a fine corsa — è lo stesso schema con cui il backend accumula i
 * `.coverage.<pid>` e poi li unisce con `coverage combine`.
 */
import {test as testBase, expect, request as playwrightRequest} from '@playwright/test';
import type {APIRequestContext, Browser, BrowserContext, Locator, Page, Request, Response, TestInfo} from '@playwright/test';
import {TEST_USER} from './test-users';

const COVERAGE_ON = process.env.COVERAGE_JS === '1';

/**
 * Transaction hygiene — active only when specs share one invocation.
 *
 * `Transaction` is a global table with no `user_id`, so a spec that commits and
 * walks away leaves its rows in every later spec's table. That used to be
 * harmless: one Playwright process per action meant `globalSetup` re-populated
 * before each one, and the leftovers were wiped before anyone tripped over them.
 *
 * Consolidation removes that accident, and the damage is not what one might
 * expect. It is rarely a duplicate key — it is **row inflation**: a spec that
 * scans "the first 20 rows", or reads page one, stops finding the fixture it
 * needs because a hundred rows from earlier specs now sort ahead of it. The
 * failure then names the innocent spec.
 *
 * ### The granularity is per spec file, not per test — and that is the whole point
 *
 * Cleaning after every *test* looks tidier and is wrong. Specs are written
 * sequentially: `tx-commit-all-types` commits a BUY and then sells part of it,
 * `tx-delete` creates a pair in one test and deletes it in the next. Wiping
 * between tests breaks those chains, and measurably did: it turned three reds
 * into five.
 *
 * What consolidation actually removed was the *inter-file* reset — before it,
 * every spec file ran in its own process against a freshly populated database.
 * So that is exactly what this restores: state accumulates freely inside a file,
 * and is rolled back when the file changes and once more at the end of the
 * worker.
 *
 * ### The rollback has to work in both directions
 *
 * Deleting the rows a file added is the cheap half. A file that *destroys* mock
 * rows — `tx-delete` does, by design — cannot be repaired that way, because no
 * API call brings back a row with its original id and its original half of a
 * linked pair. When the baseline ids are no longer all there, the database is
 * repopulated instead. It costs about ten seconds and, measured over the whole
 * `transactions/` directory, happens once.
 *
 * Runs only under `LF_TX_HYGIENE=1`, set by the consolidated pass, so a
 * single-spec run behaves exactly as before.
 */
const HYGIENE_ON = process.env.LF_TX_HYGIENE === '1';
const TX_ENDPOINT = '/api/v1/transactions';
/** Extra time granted to the test that happens to pay for a repopulate. */
const REPOPULATE_BUDGET_MS = 25_000;

async function loggedInApi(baseURL: string | undefined): Promise<APIRequestContext | null> {    if (!baseURL) return null;
    try {
        const ctx = await playwrightRequest.newContext({baseURL});
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

async function txIds(api: APIRequestContext): Promise<Set<number>> {
    const res = await api.get(TX_ENDPOINT);
    if (!res.ok()) return new Set();
    const rows = (await res.json()) as Array<{id: number}>;
    return new Set(rows.map((r) => r.id));
}

/** Delete every transaction created since `before`, including rows created
 *  indirectly — the other half of a pair, a promoted transfer. Working by id
 *  difference rather than by "the ids I made" is what catches those. */
async function dropSince(api: APIRequestContext, before: Set<number>): Promise<void> {
    try {
        const after = await txIds(api);
        const created = [...after].filter((id) => !before.has(id));
        if (created.length > 0) {
            await api.post(`${TX_ENDPOINT}/commit`, {
                data: {creates: [], updates: [], deletes: created, splits: [], promotes: []},
            });
        }
    } catch {
        // Cleanup must never turn a passing test red: a failure here shows up as
        // the next spec's problem, which is bad, but inventing a red in the
        // innocent test that happened to run first is worse.
    }
}

/**
 * Restore the mock data wholesale.
 *
 * Deleting what a file added is only half the invariant. `tx-delete` *destroys*
 * mock rows and never puts them back, and no API call can resurrect a row with
 * its original id and its original half of a linked pair. Measured: after that
 * file, `tx-picker-pagination` picks two rows that turn out to be one pair, the
 * BulkModal auto-opens a FormModal for the single entity, and four tests then
 * time out clicking a button behind the modal's backdrop — 5/5 green on a fresh
 * database, 4 red on the one the suite leaves behind.
 *
 * So a file that removed shared rows gets the only faithful repair there is.
 * `populate_mock_data` recreates the E2E users itself; the global settings it
 * wipes are put back through the same helper `globalSetup` uses.
 */
async function repopulate(): Promise<boolean> {
    try {
        const {execSync} = await import('node:child_process');
        const path = await import('node:path');
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
        console.warn('[tx-hygiene] repopulate failed, continuing with the database as it is:', e);
        return false;
    }
}

/** Roll the database back to what the spec file found. Returns true if it had
 *  to repopulate, which the caller pays for out of the test's time budget. */
async function restore(api: APIRequestContext, baseline: Set<number>): Promise<boolean> {
    let destroyed = false;
    try {
        const now = await txIds(api);
        destroyed = [...baseline].some((id) => !now.has(id));
    } catch {
        // Unreadable state: treat it as intact rather than repopulating blindly.
    }
    if (!destroyed) {
        await dropSince(api, baseline);
        return false;
    }
    return await repopulate();
}

type HygieneState = {api: APIRequestContext | null; file: string | null; baseline: Set<number>; baseURL: string};

type McrInstance = {add: (entries: unknown[]) => Promise<unknown>; fileCache?: Map<string, unknown>} | null;

const test = testBase.extend<{jsCoverage: void; txHygiene: void}, {hygieneApi: HygieneState; mcr: McrInstance}>({
    /**
     * One monocart instance per worker, not one per test.
     *
     * `MCR(options)` is a constructor: it builds a `CoverageReport` with its own
     * `fileCache` and, on the first `add()`, resolves the sourcemaps of the whole
     * build. Calling it per test was affordable while Playwright started a fresh
     * process for every spec file — a dozen instances, then the heap went away
     * with the process. Consolidation removed that reset: one worker now runs the
     * 25 spec files of `transactions/` in a row, so it became several hundred
     * instances each re-parsing the same sourcemaps.
     *
     * Reusing one instance keeps that cache warm instead of rebuilding it. It is
     * worker-scoped rather than global because Playwright workers are separate
     * processes anyway.
     *
     * Reuse alone is **not** enough — see the `fileCache.clear()` below. The two
     * changes fix different halves of the same symptom: `FATAL ERROR: Ineffective
     * mark-compacts near heap limit`, which Playwright reports as `worker process
     * exited unexpectedly (SIGABRT)` against whichever test happened to be running
     * when the heap ran out.
     */
    mcr: [
        async ({}, use) => {
            if (!COVERAGE_ON) {
                await use(null);
                return;
            }
            let instance: McrInstance = null;
            try {
                const {default: MCR} = await import('monocart-coverage-reports');
                const {default: coverageOptions} = await import('../../mcr.e2e.config.js');
                instance = MCR(coverageOptions);
            } catch (e) {
                console.warn('[coverage-js] monocart non disponibile:', e);
            }
            await use(instance);
        },
        {scope: 'worker'},
    ],

    hygieneApi: [
        async ({}, use) => {
            // Built from TEST_PORT rather than the project's baseURL: `use.baseURL`
            // is set at config top level, not per project, so it is not visible here.
            const baseURL = `http://localhost:${process.env.TEST_PORT || '6041'}`;
            const state: HygieneState = {
                api: HYGIENE_ON ? await loggedInApi(baseURL) : null,
                file: null,
                baseline: new Set(),
                baseURL,
            };
            await use(state);
            // The last file of the worker has no successor to trigger its cleanup.
            if (state.api && state.file) await restore(state.api, state.baseline);
            await state.api?.dispose();
        },
        {scope: 'worker'},
    ],

    txHygiene: [
        async ({hygieneApi}, use, testInfo) => {
            const state = hygieneApi;
            if (!state.api) {
                await use();
                return;
            }
            if (state.file !== testInfo.file) {
                if (state.file) {
                    const repopulated = await restore(state.api, state.baseline);
                    if (repopulated) {
                        // Paid for out of this test's budget, so give it back. Only
                        // when the cost was actually incurred: a blanket increase
                        // would hide the very slowness these timeouts exist to catch.
                        testInfo.setTimeout(testInfo.timeout + REPOPULATE_BUDGET_MS);
                        // The users are recreated with fresh ids, so the worker's
                        // session cookie no longer refers to anything.
                        await state.api.dispose();
                        state.api = await loggedInApi(state.baseURL);
                        if (!state.api) {
                            await use();
                            return;
                        }
                    }
                }
                state.file = testInfo.file;
                state.baseline = await txIds(state.api);
            }
            await use();
        },
        {scope: 'test', auto: true},
    ],

    jsCoverage: [
        async ({context, mcr}, use) => {
            if (!COVERAGE_ON) {
                await use();
                return;
            }

            const startOn = async (page: Page) => {
                try {
                    await page.coverage.startJSCoverage({resetOnNavigation: false});
                } catch {
                    // Pagina già chiusa, oppure browser non Chromium: non è un errore
                    // del test, e non deve farlo fallire.
                }
            };

            // Copre sia le pagine già aperte sia quelle create dopo (popup, tab).
            context.on('page', startOn);
            await Promise.all(context.pages().map(startOn));

            await use();

            context.off('page', startOn);

            const collected = await Promise.all(
                context.pages().map(async (page) => {
                    try {
                        return await page.coverage.stopJSCoverage();
                    } catch {
                        return [];
                    }
                }),
            );

            const entries = collected.flat();
            if (entries.length === 0 || !mcr) return;

            try {
                await mcr.add(entries);
                // `add()` writes the payload to the cache directory and *then* keeps a
                // copy in `fileCache`, keyed by a fresh id every call. That map is a
                // pure optimisation for the case where `add()` and `generate()` run in
                // the same process — monocart's own `generate.js` falls back to reading
                // the very same file from disk when the key is missing.
                //
                // Here they never share a process: the fixture only adds, and the report
                // is produced afterwards by `scripts/mcr-generate.js`. So every entry
                // retained is a full V8 payload — sources and sourcemaps included — held
                // for a reader that will never look at it. Over one spec file that was
                // invisible; over the 25 files of a consolidated category it reached
                // 8 GB and killed the worker.
                mcr.fileCache?.clear();
            } catch (e) {
                // Il pacchetto potrebbe non essere installato: meglio un avviso
                // che far fallire l'intera suite per un problema di strumentazione.
                console.warn('[coverage-js] raccolta non riuscita:', e);
            }
        },
        {scope: 'test', auto: true},
    ],
});

export {test, expect};
export type {APIRequestContext, Browser, BrowserContext, Locator, Page, Request, Response, TestInfo};
