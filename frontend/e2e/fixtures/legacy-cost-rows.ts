/**
 * Acquisitions without a cost, written the way an older version stored them (release checklist item 22).
 *
 * The app refuses to save a TRANSFER pair or an ADJUSTMENT-in without a cost basis any more (`COST_BASIS_REQUIRED`, and
 * P-10 closed the retype path), so such rows exist only in data an older version left behind. The API cannot create them:
 * `backend/test_scripts/test_db/legacy_cost_rows.py` writes them straight into the lane's test database. This fixture runs
 * it, the way global-setup.ts runs Python: from the repo root, with this process's environment — TEST_PORT and
 * LIBREFOLIO_TEST_DATA_DIR, exported by playwright.config.ts — so the helper resolves this lane's database and nothing
 * else, and refuses brokers the account does not own.
 *
 * Used by `portfolio/data-quality-legacy.spec.ts` and Y2 of `portfolio/yield-on-cost-real.spec.ts`.
 */

import {execFileSync} from 'child_process';
import * as path from 'path';
import {fileURLToPath} from 'url';
import {expect} from '@playwright/test';

/** The repo root: the helper is a module of it, and runs from there. */
const PROJECT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const HELPER_MODULE = 'backend.test_scripts.test_db.legacy_cost_rows';

/** The ids of the three rows the helper writes: a TRANSFER pair, and an ADJUSTMENT-in of another asset, all without a cost. */
export type LegacyRows = {transfer_out: number; transfer_in: number; adjustment_in: number};

/** What to write: the two owned brokers and assets, the day, the quantities and the marker every description carries. */
export type LegacyRequest = {userId: number; sourceBroker: number; destBroker: number; transferAsset: number; adjustmentAsset: number; date: string; transferQty: number; adjustmentQty: number; marker: string};

/**
 * Write the legacy rows. When the runner's `pipenv run` has already activated the environment (VIRTUAL_ENV), its interpreter is
 * called directly — no `pipenv`, which could create an environment of its own; otherwise `pipenv run python`, as global-setup.ts
 * does. Arguments travel as an argv array, never through a shell. A non-zero exit fails with the helper's own explanation.
 */
export function writeLegacyRows(legacy: LegacyRequest): LegacyRows {
    const helperArgs = [
        '-m',
        HELPER_MODULE,
        '--user-id',
        String(legacy.userId),
        '--source-broker',
        String(legacy.sourceBroker),
        '--dest-broker',
        String(legacy.destBroker),
        '--transfer-asset',
        String(legacy.transferAsset),
        '--adjustment-asset',
        String(legacy.adjustmentAsset),
        '--date',
        legacy.date,
        '--transfer-qty',
        String(legacy.transferQty),
        '--adjustment-qty',
        String(legacy.adjustmentQty),
        '--marker',
        legacy.marker,
    ];
    const venv = process.env.VIRTUAL_ENV;
    const command = venv ? path.join(venv, 'bin', 'python') : 'pipenv';
    const argv = venv ? helperArgs : ['run', 'python', ...helperArgs];
    let stdout: string;
    try {
        stdout = execFileSync(command, argv, {cwd: PROJECT_ROOT, env: process.env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 90_000});
    } catch (error) {
        const failed = error as {status?: number | null; signal?: string | null; stdout?: string; stderr?: string; message?: string};
        throw new Error(`legacy_cost_rows (${command}) exited with ${failed.status ?? failed.signal ?? 'no status'}:\n${failed.stderr || failed.message || ''}\n${failed.stdout ?? ''}`);
    }
    // The helper's contract is one line of JSON on stdout; anything else is a failure worth reading.
    const lines = stdout.split('\n').filter((line) => line.trim() !== '');
    expect(lines, `legacy_cost_rows prints one line of JSON; it printed:\n${stdout}`).toHaveLength(1);
    const rows = JSON.parse(lines[0]) as LegacyRows;
    expect(rows, `legacy_cost_rows printed ${lines[0]}`).toEqual({transfer_out: expect.any(Number), transfer_in: expect.any(Number), adjustment_in: expect.any(Number)});
    // For the run log: which interpreter wrote the rows, and their ids.
    console.log(`legacy_cost_rows ran with ${venv ? `VIRTUAL_ENV ${command}` : 'the pipenv fallback (pipenv run python)'}: ${lines[0]}`);
    return rows;
}
