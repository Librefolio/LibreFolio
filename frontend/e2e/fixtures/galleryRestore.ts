/**
 * Gallery, Settings › Backup (`settings/restore-rolled-back`, `settings/restore-last-result`): a restore that was rolled back.
 *
 * Nothing is restored, uploaded, confirmed or restarted for real: the lane's server is never stopped and holds no archive.
 * The page is shown a restore waiting for the next start (the status read, answered here), restarts it (the restart, answered
 * here with a one-time ticket, never sent on), finds the server gone (its readiness probes refused) and back (answered), and
 * reads the outcome (`rolled_back`, `first_start_failed`, answered here). Then «back to the tab» reads the status again, which
 * now tells the rolled-back result: the card's last-result notice. The routes are the ones of `settings/backup.spec.ts`
 * (FBKP-103), played in the same order, with the same bodies — each typed with the generated client's Zod schema, so a contract
 * that moved fails the test with Zod's own message. The success is never photographed (decision P8: it says nothing).
 *
 * Registered before the first navigation, the routes stay with the page for the whole test; the gallery's outer afterEach
 * drops them once the page has left (`leaveGalleryPage`). Every other method or path falls back to the routes before them.
 */
import {schemas} from '../../src/lib/api/generated';
import {expect, type Page} from './playwright';

const RESTORE_API = '/api/v1/backup/restore';
const RESTORE_STATUS = `${RESTORE_API}/status`;
const RESTORE_RESTART = `${RESTORE_API}/restart`;
const RESTORE_OUTCOME = `${RESTORE_API}/outcome`;
const SERVER_READY = '/api/v1/system/ready';

/** The staged check the faked restore refers to: fixed, 32 lowercase hex digits. */
const GALLERY_RESTORE_STAGE_ID = '5e2b7c9d1f3a48e6b0c4d2a19e7f3b86';
/** The one-time ticket of the faked restart: fixed, so that a shot is the same on every run. */
const GALLERY_RESTORE_TICKET = 'gallery-restore-ticket-0000000000000000000000';

type RestoreStatus = ReturnType<typeof schemas.RestoreStatus.parse>;

/** What the faked server answers right now; one per page. */
type Played = {serverUp: boolean; probesDown: number; probesUp: number; status: unknown};
const played = new WeakMap<Page, Played>();

function restoreStatus(fields: Partial<RestoreStatus> = {}): RestoreStatus {
    return schemas.RestoreStatus.parse({
        state: 'pending',
        stage_id: GALLERY_RESTORE_STAGE_ID,
        confirmed_at: '2026-10-15T09:45:03Z',
        confirmed_by: 'gallery_admin',
        backup_created_at: '2026-10-15T09:41:12Z',
        backup_app_version: '1.3.0',
        action: 'same',
        finished_at: null,
        reason: null,
        waiting: null,
        upload_limit_mb: 0,
        ...fields,
    });
}

/** Play the server's part for the restore on `page` (see the file header). Call inside the test, before the first navigation. */
export async function serveGalleryRestore(page: Page): Promise<void> {
    const state: Played = {serverUp: false, probesDown: 0, probesUp: 0, status: null};
    played.set(page, state);
    const outcome = schemas.RestoreOutcome.parse({state: 'rolled_back', reason: 'first_start_failed'});
    const ready = schemas.ReadinessResponse.parse({status: 'ready', checks: {database: 'ok', migrations: 'ok'}, app_version: 'v1.3.0'});
    await page.route(
        (url) => url.pathname === RESTORE_STATUS,
        async (route) => {
            if (state.status === null || route.request().method() !== 'GET') return route.fallback();
            await route.fulfill({json: state.status});
        },
    );
    await page.route(
        (url) => url.pathname.replace(/\/+$/, '') === RESTORE_RESTART,
        async (route) => {
            // Never sent on: the real one stops the lane's server.
            await route.fulfill({status: 202, json: schemas.RestoreRestartAccepted.parse({...(state.status as RestoreStatus), outcome_ticket: GALLERY_RESTORE_TICKET})});
        },
    );
    await page.route(
        (url) => url.pathname === SERVER_READY,
        async (route) => {
            if (!state.serverUp) {
                state.probesDown += 1;
                return route.abort('connectionrefused');
            }
            state.probesUp += 1;
            await route.fulfill({json: ready});
        },
    );
    await page.route(
        (url) => url.pathname === RESTORE_OUTCOME,
        async (route) => {
            if (!state.serverUp) return route.abort('connectionrefused');
            await route.fulfill({json: outcome});
        },
    );
}

/**
 * From the Backup tab (`open` loads it, after the status is faked): the restore card finds a restore waiting, the administrator restarts it, the
 * server goes down and comes back, and the overlay says the restore was rolled back because the first start failed. Resolves
 * with the overlay standing on that outcome.
 */
export async function rollBackRestoreOverlay(page: Page, open: () => Promise<void>): Promise<void> {
    const state = played.get(page);
    if (!state) throw new Error('the gallery restore is not served on this page (serveGalleryRestore)');
    state.serverUp = false;
    state.probesDown = 0;
    state.probesUp = 0;
    state.status = restoreStatus();
    // Opened after the faked status is set: the card reads it on load.
    await open();
    const card = page.getByTestId('restore-card');
    await expect(card).toBeVisible({timeout: 15_000});
    await expect(card, 'the faked status shows a restore waiting').toHaveAttribute('data-state', 'pending', {timeout: 15_000});
    await page.getByTestId('restore-restart').click();
    const overlay = page.getByTestId('restart-overlay');
    await expect(overlay).toHaveAttribute('data-outcome', 'waiting', {timeout: 15_000});
    await expect.poll(() => state.probesDown, {message: 'the page probes the restarting server, refused while it is down', timeout: 15_000}).toBeGreaterThan(0);
    state.serverUp = true;
    await expect(overlay).toHaveAttribute('data-outcome', 'rolled_back', {timeout: 15_000});
    await expect(overlay).toHaveAttribute('data-reason', 'first_start_failed');
    await expect(page.getByTestId('restart-detail')).toBeVisible();
    await expect(page.getByTestId('restart-back')).toBeVisible();
}

/** «Back to the tab» from the overlay: the status read again tells the rolled-back result, and the card shows it as its last result. */
export async function backToRestoreCard(page: Page): Promise<void> {
    const state = played.get(page);
    if (!state) throw new Error('the gallery restore is not served on this page (serveGalleryRestore)');
    state.status = restoreStatus({state: 'rolled_back', reason: 'first_start_failed', finished_at: '2026-10-15T09:46:40Z'});
    await page.getByTestId('restart-back').click();
    await expect(page.getByTestId('restart-overlay')).toBeHidden();
    const card = page.getByTestId('restore-card');
    await expect(card).toHaveAttribute('data-state', 'idle', {timeout: 15_000});
    const last = page.getByTestId('restore-last-result');
    await expect(last).toHaveAttribute('data-result', 'rolled_back');
    await expect(last).toHaveAttribute('data-reason', 'first_start_failed');
}
