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
const SERVER_WORKERS = Math.max(
    1,
    Number(
        process.env.LIBREFOLIO_SERVER_WORKERS ||
        process.env.GALLERY_SERVER_WORKERS ||
        Math.ceil(E2E_WORKERS / 2)
    ) || 1
);

// Set by scripts/test_runner/_server.py when the runner has already started one
// backend for the whole run. Without this, a coverage run refuses to start at
// all — reuseExistingServer is false under coverage, and Playwright checks the
// health URL *before* launching its webServer, so it aborts with "port already
// used" and takes the whole frontend phase down with it. Measured: exit 1.
const SHARED_SERVER = !!process.env.LIBREFOLIO_TEST_SHARED_SERVER;

export default defineConfig({
    globalSetup: './e2e/global-setup.ts',
    testDir: './e2e',
    fullyParallel: false,           // Test sequenziali (stato condiviso)
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: E2E_WORKERS,
    reporter: [
        ['html', {outputFolder: 'playwright-report', open: 'never'}],
        ['list']
    ],

    timeout: 30000,  // Test timeout (30s for full test including setup)
    expect: {timeout: 3000},  // 3s for localhost assertions

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
        command: `cd .. && exec ./dev.py server --test --force --workers ${SERVER_WORKERS}${process.env.COVERAGE_BACKEND ? ' --coverage' : ''}`,
        url: `${BASE_URL}/api/v1/system/health`,
        // In coverage mode, always start a fresh server (don't reuse a
        // non-coverage server that may already be running on the port) —
        // unless the runner started the shared one, which already has coverage
        // enabled because both follow the same flag.
        reuseExistingServer: SHARED_SERVER ? true : (process.env.COVERAGE_BACKEND ? false : !process.env.CI),
        timeout: 120 * 1000,
        // Send SIGTERM instead of SIGKILL so coverage run can flush .coverage.<pid>.
        // In coverage mode the flush itself takes time (writing the coverage data file), and a
        // SIGKILL there silently discards the whole run's backend coverage — so the grace
        // window is widened. Outside coverage there is nothing to flush: 5s stays.
        gracefulShutdown: {signal: 'SIGTERM', timeout: process.env.COVERAGE_BACKEND ? 30000 : 5000},
    },
});
