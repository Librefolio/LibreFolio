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

/**
 * Reset database for gallery: force recreate + clean files + upload static resources + upload reports.
 * Ensures a fully deterministic filesystem state for reproducible screenshots.
 */
export async function resetDatabaseForGallery(): Promise<void> {
    console.log('[E2E] Resetting database for gallery (force + clean + static + reports)...');
    await execAsync('cd .. && ./dev.py test db populate --force --clean --with-static --with-reports');
    console.log('[E2E] Gallery database reset complete');
}

