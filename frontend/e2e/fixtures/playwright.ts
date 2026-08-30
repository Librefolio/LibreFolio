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
 * Nota sull'architettura: qui si scrive un JSON per test e basta; il report si
 * produce a fine corsa da `scripts/js-coverage-report.js`. È lo stesso schema
 * con cui il backend accumula i `.coverage.<pid>` e poi li unisce con
 * `coverage combine` — e per la stessa ragione: accumulare in memoria dentro il
 * worker è ciò che, sui 25 spec di una categoria consolidata, arrivava a 8 GB.
 */
import {test as testBase, expect, request as playwrightRequest} from '@playwright/test';
import type {APIRequestContext, Browser, BrowserContext, Locator, Page, Request, Response, TestInfo} from '@playwright/test';
import {existsSync} from 'node:fs';
import {mkdir, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {TEST_USER} from './test-users';

const COVERAGE_ON = process.env.COVERAGE_JS === '1';

/**
 * Is the build under test instrumented by `vite-plugin-istanbul`?
 *
 * The sentinel is written by `_ensure_frontend_build()`; timestamps cannot tell
 * the two *kinds* of build apart. When it is there, `window.__coverage__` will
 * carry richer data than V8 for every file, so V8 is not started at all — it is
 * not merely redundant, it is expensive: its payloads carry sources and
 * sourcemaps, and accumulating them across a consolidated category is what
 * reached 8 GB and killed the worker.
 */
const INSTRUMENTED_BUILD = (() => {
    if (!COVERAGE_ON) return false;
    try {
        return existsSync(new URL('../../build/.coverage-instrumented', import.meta.url));
    } catch {
        return false;
    }
})();

/** Where each test drops its slice of `window.__coverage__`. */
const E2E_COVERAGE_DIR = fileURLToPath(new URL('../../coverage-js/e2e-raw', import.meta.url));

let coverageSeq = 0;
let warnedUninstrumented = false;

/**
 * Say once, per worker, that the measurement is silently empty.
 *
 * Without instrumentation there is nothing to read and the run would produce a
 * report of zero without failing — the exact shape of a green that means
 * nothing. `_ensure_frontend_build()` normally prevents this; the warning is
 * for when someone runs Playwright directly against a plain build.
 */
function warnUninstrumentedOnce(): void {
    if (warnedUninstrumented) return;
    warnedUninstrumented = true;
    console.warn('[coverage-js] the build under test is not instrumented — no coverage will be collected. Rebuild with COVERAGE_INSTRUMENT=1.');
}

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
 *
 * ### Why it switches itself off under parallelism
 *
 * The whole mechanism rests on one assumption: **a worker runs a spec file from
 * start to finish, alone.** That is what makes "delete every transaction id that
 * appeared since I opened this file" a correct description of *my* leftovers.
 *
 * With `fullyParallel: true` the unit of scheduling is the test, not the file:
 * four workers interleave tests from four different files against one database.
 * "Since I opened this file" then also covers the rows the other three workers
 * created for tests that are still running — and `restore()` would delete them
 * out from under them. The repopulate path is worse still: it runs
 * `populate_mock_data --force`, wiping the database while three tests are
 * mid-assertion.
 *
 * So hygiene and cross-file interleaving are mutually exclusive by construction,
 * and hygiene is the half that is no longer needed: it exists to protect tests
 * that read data they did not create, and those are exactly the tests this
 * migration rewrote. Measured without it at four workers: transactions 216/216,
 * assets+fx+utility 298/298.
 */
const HYGIENE_REQUESTED = process.env.LF_TX_HYGIENE === '1';
const HYGIENE_ON = HYGIENE_REQUESTED && Math.max(1, Number(process.env.E2E_WORKERS || '1') || 1) <= 1;
const TX_ENDPOINT = '/api/v1/transactions';
/** Extra time granted to the test that happens to pay for a repopulate. */
const REPOPULATE_BUDGET_MS = 25_000;

async function loggedInApi(baseURL: string | undefined): Promise<APIRequestContext | null> {
    if (!baseURL) return null;
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

const test = testBase.extend<{jsCoverage: void; txHygiene: void}, {hygieneApi: HygieneState}>({
    hygieneApi: [
        async ({}, use) => {
            if (HYGIENE_REQUESTED && !HYGIENE_ON) {
                console.warn('[tx-hygiene] disabled: tests interleave across files at E2E_WORKERS>1, so "created since I opened this file" would include other workers\' rows.');
            }
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
        async ({context}, use) => {
            if (!COVERAGE_ON) {
                await use();
                return;
            }

            await use();

            // The build carries its own istanbul counters, so collecting is a
            // read of `window.__coverage__` — already in source coordinates,
            // with a branch map for every `{#if}` of every template. Nothing
            // has to be mapped back through the bundle, which is why there is
            // no monocart here any more: resolving V8 ranges to sources was its
            // entire job, and instrumenting the build removed the job.
            const entries = (
                await Promise.all(
                    context.pages().map(async (page) => {
                        try {
                            return await page.evaluate(() => (window as unknown as {__coverage__?: unknown}).__coverage__ ?? null);
                        } catch {
                            // Page already closed: not an error of the test.
                            return null;
                        }
                    }),
                )
            ).filter(Boolean);

            if (entries.length === 0) {
                if (!INSTRUMENTED_BUILD) warnUninstrumentedOnce();
                return;
            }

            // One file per test rather than an in-process accumulator. The
            // accumulator is what used to die: it retained every payload —
            // sources and sourcemaps included — and over the 25 spec files a
            // consolidated category now runs in a single worker it reached 8 GB
            // and took the worker with it, reported against whichever test
            // happened to be running. Writing and forgetting is O(1) in memory,
            // and the merge is somebody else's problem: `js-coverage-report.js`.
            try {
                await mkdir(E2E_COVERAGE_DIR, {recursive: true});
                const name = `${Date.now().toString(36)}-${process.pid}-${coverageSeq++}.json`;
                await writeFile(join(E2E_COVERAGE_DIR, name), JSON.stringify(Object.assign({}, ...entries)));
            } catch (e) {
                console.warn('[coverage-js] raccolta non riuscita:', e);
            }
        },
        {scope: 'test', auto: true},
    ],
});

export {test, expect};
export type {APIRequestContext, Browser, BrowserContext, Locator, Page, Request, Response, TestInfo};
