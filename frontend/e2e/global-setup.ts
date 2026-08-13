/**
 * Playwright Global Setup
 *
 * Ensures the test database is populated with mock data and test users
 * before any E2E test runs. This makes `npm run test:e2e` self-contained
 * — no need to manually run `./dev.py test db populate` first.
 *
 * Also initializes global settings via the API (they are seeded at server
 * startup, but `populate --force` wipes them — this step re-creates them).
 *
 * Runs once per Playwright invocation (before all projects/workers).
 *
 * ## LF_SETUP_DONE
 *
 * When `./dev.py test` launches Playwright it has *already* populated the
 * database and created the users — with a superset of what is done here (eight
 * users instead of three). Redoing it costs ~23 s per invocation and changes
 * nothing, so the runner sets `LF_SETUP_DONE=1` and steps 1 and 2 stand down.
 *
 * Step 3 always runs. Nothing on the Python side initialises the global
 * settings, and `populate --force` wipes them, so skipping it would leave the
 * suite running against a table the server only seeds at startup.
 *
 * Running `npx playwright test` by hand sets no such variable and therefore
 * takes the full path, exactly as before.
 */

import {execSync} from 'child_process';
import * as path from 'path';

const PROJECT_ROOT = path.resolve(import.meta.dirname, '..', '..');
const TEST_PORT = process.env.TEST_PORT || '6041';
const BASE_URL = `http://localhost:${TEST_PORT}`;
const SETUP_DONE = process.env.LF_SETUP_DONE === '1';
const SETUP_FETCH_TIMEOUT_MS = 20_000;

export default async function globalSetup() {
    if (SETUP_DONE) {
        console.log('\n🔧 [global-setup] DB and users already prepared by the runner — skipping to global settings');
    } else {
        console.log('\n🔧 [global-setup] Ensuring test DB is populated...');

        try {
            // 1. Populate test DB with mock data (--force recreates if needed).
            //    --with-reports seeds sample BRIM import files so broker import-history
            //    E2E tests (e.g. brokers-detail "import files modal") have data to show;
            //    without it the modal is empty and those tests fail on a clean checkout.
            execSync('pipenv run python -m backend.test_scripts.test_db.populate_mock_data --force --with-reports', {
                cwd: PROJECT_ROOT,
                stdio: 'pipe',
                timeout: 90_000,
            });
            console.log('   ✅ Test DB populated');
        } catch (e: unknown) {
            const err = e as {stderr?: Buffer; stdout?: Buffer};
            const stderr = err.stderr?.toString() || '';
            const stdout = err.stdout?.toString() || '';
            if (stderr.includes('already') || stdout.includes('already')) {
                console.log('   ✅ Test DB already populated');
            } else {
                console.error('   ⚠️  DB populate failed (tests may still work if DB was set up earlier)');
                console.error('   stderr:', stderr.slice(0, 300));
            }
        }

        try {
            // 2. Ensure E2E test users exist
            const users = [
                ['e2e_test_user', 'e2e@test.example.com', 'E2eTestPass123!'],
                ['e2e_test_admin', 'e2eadmin@test.example.com', 'E2eAdminPass123!'],
                ['e2e_test_user2', 'e2e2@test.example.com', 'E2eTestPass456!'],
            ];

            for (const [username, email, password] of users) {
                try {
                    execSync(`pipenv run python scripts/user_cli.py --test-db create-superuser ${username} ${email} ${password}`, {cwd: PROJECT_ROOT, stdio: 'pipe', timeout: 15_000});
                } catch {
                    // "already exists" is expected — ignore
                }
            }

            // Promote admin
            try {
                execSync('pipenv run python scripts/user_cli.py --test-db promote e2e_test_admin', {
                    cwd: PROJECT_ROOT,
                    stdio: 'pipe',
                    timeout: 15_000,
                });
            } catch {
                // Already promoted — ignore
            }

            console.log('   ✅ Test users ready');
        } catch {
            console.error('   ⚠️  User setup failed (tests may still work if users exist)');
        }
    }

    // 3. Initialize global settings via API
    await initGlobalSettings();

    console.log('');
}

/**
 * Re-create the global settings through the admin API.
 *
 * `populate --force` wipes the `global_settings` table, but the server only
 * seeds it at startup — so anything that repopulates mid-run has to put those
 * rows back. Exported because the transaction-hygiene fixture repopulates when
 * a spec file destroys shared rows, and it must not reinvent this.
 *
 * Both calls carry a deadline. A backend that accepts the connection but never
 * answers — the state uvicorn is left in when a run is aborted mid-flight, and
 * one `reuseExistingServer` happily reuses — would otherwise park fetch() here
 * forever, before the reporter has printed a single line. Twenty silent minutes
 * are a far worse failure than a warning.
 */
export async function initGlobalSettings(): Promise<void> {
    try {
        // Login as admin
        const loginRes = await fetch(`${BASE_URL}/api/v1/auth/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username: 'e2e_test_admin', password: 'E2eAdminPass123!'}),
            signal: AbortSignal.timeout(SETUP_FETCH_TIMEOUT_MS),
        });
        if (loginRes.ok) {
            const cookie = loginRes.headers.getSetCookie?.()?.join('; ') || '';
            // Call initialize endpoint
            const initRes = await fetch(`${BASE_URL}/api/v1/settings/global/initialize`, {
                method: 'POST',
                headers: {Cookie: cookie},
                signal: AbortSignal.timeout(SETUP_FETCH_TIMEOUT_MS),
            });
            if (initRes.ok) {
                const data = await initRes.json();
                console.log(`   ✅ Global settings initialized (${data.message})`);
            } else {
                console.error(`   ⚠️  Global settings init failed: ${initRes.status}`);
            }
        } else {
            console.error(`   ⚠️  Admin login failed: ${loginRes.status} (global settings may be missing)`);
        }
    } catch (e) {
        const timedOut = e instanceof Error && (e.name === 'TimeoutError' || e.name === 'AbortError');
        if (timedOut) {
            console.error(`   ⚠️  Global settings init timed out after ${SETUP_FETCH_TIMEOUT_MS / 1000}s.`);
            console.error(`   ⚠️  ${BASE_URL} accepts connections but does not answer — a stale test server`);
            console.error("   ⚠️  is probably still holding the port. Kill it and let this run start its own.");
        } else {
            console.error(`   ⚠️  Global settings init error: ${e}`);
        }
    }
}
