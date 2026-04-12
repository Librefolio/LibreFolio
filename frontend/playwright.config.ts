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
const TEST_PORT = process.env.TEST_PORT || '8001';
const BASE_URL = `http://localhost:${TEST_PORT}`;

export default defineConfig({
    testDir: './e2e',
    fullyParallel: false,           // Test sequenziali (stato condiviso)
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: 1,
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
    // GALLERY_SERVER_WORKERS env var controls uvicorn worker count (set by dev.py mkdocs gallery)
    // COVERAGE_BACKEND=1 enables backend code coverage tracking during E2E tests
    webServer: {
        command: `cd .. && ./dev.py server --test --force --workers ${process.env.GALLERY_SERVER_WORKERS || '1'}${process.env.COVERAGE_BACKEND ? ' --coverage' : ''}`,
        url: `${BASE_URL}/api/v1/system/health`,
        reuseExistingServer: !process.env.CI,
        timeout: 120 * 1000,
    },
});
