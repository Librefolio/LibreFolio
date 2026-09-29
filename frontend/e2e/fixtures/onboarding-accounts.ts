/**
 * Disposable onboarding accounts for guide specs.
 *
 * Onboarding progress is persisted per user, and walking a guide *moves* that
 * progress. The canonical E2E users are grandfathered `completed` on every flow
 * on purpose (populate_mock_data `_grandfather_onboarding_for_test_users`), so a
 * guide spec can neither run on them nor write to them: every guide test
 * registers its own account, takes it through the real welcome hand-off, skips
 * over the API every flow it is not about — so no other guide competes for the
 * overlay — and deletes the account, with everything it owns, in `finally`.
 *
 * Adapted from the helpers of `onboarding-tour.spec.ts`, which keeps its own
 * copies; this module owns nothing that spec relies on.
 */

import {expect, type APIRequestContext, type Page} from './playwright';
import {login} from './auth-helpers';
import {uniqueSuffix} from './unique';

export type DisposableUser = {id: number; username: string; email: string; password: string};
export type OnboardingFlowStatus = 'pending' | 'completed' | 'skipped';
export type OnboardingFlowProgress = {
    flow: string;
    status: OnboardingFlowStatus;
    version: number;
    current_version: number;
    update_available: boolean;
};
export type OwnedBroker = {id: number; name: string};

/** Mirrors `isOnboardingProgressDue` (`$lib/types/onboarding`): what the app would still offer. */
function isDue(item: OnboardingFlowProgress): boolean {
    return item.status === 'pending' || item.version < item.current_version;
}

/** Register a fresh account. `tag` must stay short: usernames are capped at 50 characters. */
export async function registerDisposableUser(request: APIRequestContext, tag: string): Promise<DisposableUser> {
    const suffix = uniqueSuffix();
    const username = `guides_${tag}_${suffix}`;
    const user = {username, email: `${username}@example.com`, password: `Guide9!_${suffix}`};
    const response = await request.post('/api/v1/auth/register', {data: user});
    expect(response.status(), 'Disposable-account registration must be enabled; guide specs never rewrite global settings').toBe(201);
    const created = (await response.json()) as {user: {id: number}};
    return {...user, id: created.user.id};
}

/**
 * Delete the brokers this test created, then the account itself.
 *
 * Authenticates `request` as the account it is about to delete and checks the id,
 * so a cleanup can never act on anybody else's session.
 */
export async function deleteDisposableUser(request: APIRequestContext, user: DisposableUser, ownedBrokerIds: readonly number[] = []): Promise<void> {
    const loggedIn = await request.post('/api/v1/auth/login', {
        data: {username: user.username, password: user.password},
    });
    expect(loggedIn.ok(), 'Cleanup must authenticate as the account it owns').toBe(true);
    const body = (await loggedIn.json()) as {user: {id: number}};
    expect(body.user.id, 'Cleanup must remain scoped to this test user').toBe(user.id);
    const failures: string[] = [];
    try {
        for (const brokerId of ownedBrokerIds) {
            const deleted = await request.delete(`/api/v1/brokers?ids=${brokerId}&force=true`);
            if (!deleted.ok()) {
                failures.push(`broker ${brokerId}: HTTP ${deleted.status()} ${await deleted.text()}`);
                continue;
            }
            const result = ((await deleted.json()) as {results: Array<{id: number; success: boolean}>}).results.find((candidate) => candidate.id === brokerId);
            if (result?.success !== true) failures.push(`broker ${brokerId}: ${JSON.stringify(result)}`);
        }
    } finally {
        const removed = await request.delete('/api/v1/auth/users/me');
        expect(removed.ok(), 'Cleanup must delete the disposable onboarding account').toBe(true);
    }
    expect(failures, 'Cleanup must delete every broker owned by this test').toEqual([]);
}

/** The server's onboarding progress for the account signed in on `page`'s browser context. */
export async function readOnboardingProgress(page: Page): Promise<OnboardingFlowProgress[]> {
    const response = await page.request.get('/api/v1/settings/onboarding');
    expect(response.ok(), `Onboarding progress read failed (HTTP ${response.status()})`).toBe(true);
    return ((await response.json()) as {flows: OnboardingFlowProgress[]}).flows;
}

export async function readFlowProgress(page: Page, flow: string): Promise<OnboardingFlowProgress> {
    const item = (await readOnboardingProgress(page)).find((candidate) => candidate.flow === flow);
    if (!item) throw new Error(`The account has no onboarding progress for ${flow}`);
    return item;
}

/** A brand-new account lands on /welcome; the default choices hand it to the intro scene. */
export async function completeWelcome(page: Page): Promise<void> {
    await expect(page).toHaveURL(/\/welcome(?:[/?#]|$)/, {timeout: 15_000});
    await expect(page.getByTestId('welcome-form')).toBeVisible({timeout: 10_000});
    await expect(page.getByTestId('welcome-continue')).toBeEnabled({timeout: 10_000});
    await page.getByTestId('welcome-continue').click();
    await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/, {timeout: 15_000});
    await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
    await expect(page.getByTestId('onboarding-intro-scene')).toHaveAttribute('data-state', 'intro-scene', {timeout: 10_000});
}

/**
 * Skip, over the API, every flow still due except `keepDue`, then verify that
 * exactly `keepDue` is left — the precondition is read back, not inferred.
 *
 * Step-managed flows (Import, Bulk) are skipped at flow level, which the service
 * cascades to every registered step.
 */
export async function skipDueFlowsExcept(page: Page, keepDue: readonly string[]): Promise<void> {
    const before = await readOnboardingProgress(page);
    for (const flow of keepDue) {
        const item = before.find((candidate) => candidate.flow === flow);
        if (!item) throw new Error(`The account has no onboarding progress for ${flow}`);
        expect(item.status, `${flow} must start pending on a fresh account`).toBe('pending');
    }
    for (const item of before) {
        if (!isDue(item) || keepDue.includes(item.flow)) continue;
        const skipped = await page.request.post(`/api/v1/settings/onboarding/${item.flow}/skip`, {
            data: {expected_version: item.current_version},
        });
        expect(skipped.ok(), `The account could not skip ${item.flow} (HTTP ${skipped.status()})`).toBe(true);
    }
    const due = (await readOnboardingProgress(page))
        .filter(isDue)
        .map((item) => item.flow)
        .sort();
    expect(due, 'Only the flows under test may still be due, so no other guide competes for the overlay').toEqual([...keepDue].sort());
}

/**
 * Sign in, finish welcome with its defaults, close the intro scene through its
 * own control, and leave only `keepDue` pending. The page is left on /dashboard
 * with stale in-memory progress: callers reach their trigger with a full load.
 */
export async function prepareOnboardingAccount(page: Page, user: DisposableUser, keepDue: readonly string[]): Promise<void> {
    await login(page, user);
    await completeWelcome(page);
    await page.getByTestId('onboarding-intro-close').click();
    await expect(page.getByTestId('onboarding-intro-scene')).toHaveCount(0, {timeout: 10_000});
    await skipDueFlowsExcept(page, keepDue);
}

/** A broker owned by the account signed in on `page`; its id is recorded for cleanup before it is returned. */
export async function createOwnedBroker(page: Page, tag: string, ownedBrokerIds: number[]): Promise<OwnedBroker> {
    const name = `guides-${tag}-broker-${uniqueSuffix()}`;
    const response = await page.request.post('/api/v1/brokers', {data: [{name, opened_at: '2025-01-01'}]});
    expect(response.ok(), `Owned broker setup failed (HTTP ${response.status()})`).toBe(true);
    const body = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>};
    const created = body.results.find((candidate) => candidate.name === name);
    if (!created?.success || typeof created.broker_id !== 'number') {
        throw new Error(`Owned broker setup returned no id for ${name}: ${created?.message ?? 'missing result'}`);
    }
    ownedBrokerIds.push(created.broker_id);
    return {id: created.broker_id, name};
}
