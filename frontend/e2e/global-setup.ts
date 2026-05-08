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
 */

import {execSync} from 'child_process';
import * as path from 'path';

const PROJECT_ROOT = path.resolve(import.meta.dirname, '..', '..');
const TEST_PORT = process.env.TEST_PORT || '8001';
const BASE_URL = `http://localhost:${TEST_PORT}`;

export default async function globalSetup() {
	console.log('\n🔧 [global-setup] Ensuring test DB is populated...');

	try {
		// 1. Populate test DB with mock data (--force recreates if needed)
		execSync('pipenv run python -m backend.test_scripts.test_db.populate_mock_data --force', {
			cwd: PROJECT_ROOT,
			stdio: 'pipe',
			timeout: 60_000,
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
				execSync(
					`pipenv run python scripts/user_cli.py --test-db create-superuser ${username} ${email} ${password}`,
					{cwd: PROJECT_ROOT, stdio: 'pipe', timeout: 15_000}
				);
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

	// 3. Initialize global settings via API
	//    populate --force wipes the global_settings table, but the server
	//    only seeds them once at startup. Re-initialize via admin endpoint.
	try {
		// Login as admin
		const loginRes = await fetch(`${BASE_URL}/api/v1/auth/login`, {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({username: 'e2e_test_admin', password: 'E2eAdminPass123!'}),
		});
		if (loginRes.ok) {
			const cookie = loginRes.headers.getSetCookie?.()?.join('; ') || '';
			// Call initialize endpoint
			const initRes = await fetch(`${BASE_URL}/api/v1/settings/global/initialize`, {
				method: 'POST',
				headers: {Cookie: cookie},
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
		console.error(`   ⚠️  Global settings init error: ${e}`);
	}

	console.log('');
}
