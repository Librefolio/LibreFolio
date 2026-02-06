import {exec} from 'child_process';
import {promisify} from 'util';

const execAsync = promisify(exec);

/**
 * Reset test database to clean state with populate data
 */
export async function resetDatabase(): Promise<void> {
    console.log('[E2E] Resetting test database...');
    await execAsync('cd .. && ./dev.py db create-clean --test');
    await execAsync('cd .. && ./dev.py test db populate --force');
    console.log('[E2E] Database reset complete');
}

/**
 * Just run db populate (without full reset)
 */
export async function populateDatabase(): Promise<void> {
    console.log('[E2E] Populating test database...');
    await execAsync('cd .. && ./dev.py test db populate');
    console.log('[E2E] Database populated');
}
