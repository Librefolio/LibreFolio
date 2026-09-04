import {defineConfig, devices} from '@playwright/test';
import * as dotenv from 'dotenv';
import * as path from 'path';
import {fileURLToPath} from 'url';

// ES module compatibility for __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load .env from project root
dotenv.config({path: path.resolve(__dirname, '../.env')});

// Use TEST_PORT for E2E tests (server runs in test mode)
const TEST_PORT = process.env.TEST_PORT || '6041';
const BASE_URL = `http://localhost:${TEST_PORT}`;

// How many Playwright workers hit the backend at once. Still 1 by default:
// fullyParallel is off and the suite shares state, so raising it is a decision
// taken per-run (or by the test runner), not a silent default.
const E2E_WORKERS = Math.max(1, Number(process.env.E2E_WORKERS || '1') || 1);

// Backend size follows the parallelism actually pointed at it: one uvicorn
// worker per two browser workers, never fewer than one. A single hardcoded '1'
// meant that raising the browser workers just queued them all behind one
// process — the bottleneck would have looked like slow tests.
// Precedence: explicit override → gallery's own tuning (one per four, since
// browser workers there spend most of their time rendering) → derived.
const SERVER_WORKERS = Math.max(1, Number(process.env.LIBREFOLIO_SERVER_WORKERS || process.env.GALLERY_SERVER_WORKERS || Math.ceil(E2E_WORKERS / 2)) || 1);

// `E2E_FORCE_PARALLEL` used to mean `fullyParallel: true`, back when the default
// was `false`. The default is now `true`, so the flag has nothing left to force:
// the only thing still serialised is a block that says `mode: 'serial'`, and
// Playwright gives the config no way to override a describe-level mode.
//
// Re-testing one of those blocks is therefore a source edit, not an env var —
// comment the declaration out, run, and either delete it with the run as
// evidence or restore it with the reason updated. Kept as a warning so an old
// command line says so instead of silently doing nothing.
if (process.env.E2E_FORCE_PARALLEL) {
    console.warn("⚠️  E2E_FORCE_PARALLEL is obsolete: fullyParallel is the default now. To re-test a `mode: 'serial'` block, comment out its declaration.");
}

// Set by scripts/test_runner/_server.py when the runner has already started one
// backend for the whole run. Without this, a coverage run refuses to start at
// all — reuseExistingServer is false under coverage, and Playwright checks the
// health URL *before* launching its webServer, so it aborts with "port already
// used" and takes the whole frontend phase down with it. Measured: exit 1.
const SHARED_SERVER = !!process.env.LIBREFOLIO_TEST_SHARED_SERVER;

export default defineConfig({
    globalSetup: './e2e/global-setup.ts',
    testDir: './e2e',
    // On by default, and earned: every non-gallery category was run under
    // E2E_FORCE_PARALLEL at four workers until it was green, and the reds that
    // surfaced were fixed rather than declared away — 216/216 transactions,
    // 298/298 assets+fx+utility, 98/98 ai-export+brokers+portfolio+settings.
    //
    // The unit of parallelism is the *test*, not the file. That matters: with
    // file-level scheduling the workers idle at the tail of a run waiting for
    // the last long file (measured 3.4 min vs 2.5 min on the same category).
    //
    // Blocks that genuinely share state opt *out* with
    // `test.describe.configure({mode: 'serial'})` and a written reason — the
    // exception catalogue, the twin of `exclusive_because` on the backend.
    // Currently: brokers/multi-user, asset-event-delete, tx-brim-import.
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: E2E_WORKERS,
    reporter: [['html', {outputFolder: 'playwright-report', open: 'never'}], ['list']],

    timeout: 30000, // Test timeout (30s for full test including setup)
    expect: {timeout: 3000}, // 3s for localhost assertions

    use: {
        baseURL: BASE_URL,
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
        video: 'on-first-retry',
        launchOptions: {
            slowMo: process.env.SLOWMO ? parseInt(process.env.SLOWMO) : 0,
        },
    },

    projects: [
        {
            name: 'desktop',
            use: {
                ...devices['Desktop Chrome'],
                viewport: {width: 1280, height: 720},
            },
        },
        {
            name: 'mobile',
            use: {
                ...devices['iPhone 14 Pro Max'],
                // Force Chromium for mobile emulation — WebKit on Linux has
                // stability issues (click actions hang, touch events stall).
                // The device descriptor still provides viewport, isMobile,
                // hasTouch, and deviceScaleFactor for proper mobile rendering.
                browserName: 'chromium',
                // viewport: { width: 430, height: 932 }  // già incluso nel device
            },
        },
    ],

    // Server avviato automaticamente in test mode (--force kills stale servers)
    // Worker count: LIBREFOLIO_SERVER_WORKERS / GALLERY_SERVER_WORKERS, else derived
    // from E2E_WORKERS (see SERVER_WORKERS above).
    // COVERAGE_BACKEND=1 enables backend code coverage tracking during E2E tests
    //
    // SIGTERM chain for coverage (all 3 levels use exec/execvpe):
    //   Playwright gracefulShutdown SIGTERM → /bin/sh 'exec' → dev.py os.execvpe()
    //   → pipenv os.execvpe() → coverage run receives SIGTERM → writes .coverage.*
    //
    // Without gracefulShutdown, Playwright sends SIGKILL (uncatchable) — no coverage data.
    webServer: {
        // `--no-reload`: the reloader watches the repository root, so any file
        // written during a run — a source edit, a generated artefact — restarts
        // the backend under the tests and drops every in-flight session. The
        // symptom is a burst of login timeouts that looks like flakiness. An
        // ephemeral test server has nothing to hot-reload; the runner's own
        // shared-backend path already passes this flag.
        //
        // `--no-scheduler`: the runner's shared-backend path has always passed it,
        // with the reason written out in `_server.py` — `populate_mock_data` writes
        // `last_run_at=yesterday`, so every job is due the moment a test server
        // boots. Five seconds in, the daemon starts refreshing current prices for
        // *every active asset* against live providers, and the OHLC write-back
        // documented on `get_current_prices_bulk` means those refreshes **create
        // and extend price rows underneath the tests**. This path did not pass it,
        // so a frontend category run on its own — `./dev.py test front-asset all`,
        // which starts its own server rather than attaching to a shared one — was
        // running against a backend that mutates prices on a 10-minute timer and
        // drags the network into the suite. Measured on the shared path when it
        // was still missing: ±700-1300 lines of backend coverage between two
        // identical runs, and one run where the Bank of England answered HTML.
        command: `cd .. && exec ./dev.py server --test --force --no-reload --no-scheduler --workers ${SERVER_WORKERS}${process.env.COVERAGE_BACKEND ? ' --coverage' : ''}`,
        // The server auto-rebuilds the frontend when it thinks the sources moved,
        // and that rebuild does not know what kind of build the runner just made.
        // Without this it produced a *plain* bundle on top of the instrumented
        // one, deleting the instrumentation between the build and the tests —
        // and the run then reported "no JS coverage collected" while every test
        // passed. Passing the flags down means a rebuild, if one still happens,
        // reproduces the same kind and has the heap to finish it.
        env: process.env.COVERAGE_JS === '1' ? {COVERAGE_INSTRUMENT: '1', NODE_OPTIONS: '--max-old-space-size=8192'} : {},
        url: `${BASE_URL}/api/v1/system/health`,
        // In coverage mode, always start a fresh server (don't reuse a
        // non-coverage server that may already be running on the port) —
        // unless the runner started the shared one, which already has coverage
        // enabled because both follow the same flag.
        reuseExistingServer: SHARED_SERVER ? true : process.env.COVERAGE_BACKEND ? false : !process.env.CI,
        timeout: 120 * 1000,
        // Send SIGTERM instead of SIGKILL so coverage run can flush .coverage.<pid>.
        // In coverage mode the flush itself takes time (writing the coverage data file), and a
        // SIGKILL there silently discards the whole run's backend coverage — so the grace
        // window is widened. Outside coverage there is nothing to flush: 5s stays.
        gracefulShutdown: {signal: 'SIGTERM', timeout: process.env.COVERAGE_BACKEND ? 30000 : 5000},
    },
});
