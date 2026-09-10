import {type APIRequestContext, expect, type Page, type Request, test} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER, TEST_USER_2} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

/**
 * Broker Sharing E2E Tests
 *
 * Tests for the broker access-sharing feature (BrokerSharingPanel, the shared UI —
 * donut chart, add/edit/remove users, save — reused in two shells):
 * - BrokerSharingModal: wraps the panel with modal chrome, used from the broker list page
 * - Detail page "Info" tab: embeds the panel directly, no modal chrome
 *
 * Covers:
 * - Share button visibility (always visible; read-only unless OWNER)
 * - Modal open/close (list page only)
 * - Ownership chart, add/edit/remove users
 * - Save flow
 * - Role-based access checks
 * - Dark mode
 */

// Helper: Navigate to first broker detail page (OWNER)
async function goToFirstBrokerDetail(page: Page) {
    await navigateTo(page, '/brokers');
    // Wait for brokers page to load
    await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 10000});
    // Wait for broker cards to appear (API fetch)
    const brokerCards = page.locator('[data-testid^="broker-card-"]');
    await expect(brokerCards.first()).toBeVisible({timeout: 10000});

    // Click the first broker card to navigate to detail
    await brokerCards.first().click();
    await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 10000});
}

// Helper: Open sharing panel (assumes already on broker detail as OWNER).
// On the detail page this is an inline panel in the "Info" tab, NOT a modal —
// BrokerSharingModal only wraps BrokerSharingPanel on the broker list page.
async function openSharingModal(page: Page) {
    const shareBtn = page.getByTestId('broker-share-button');
    await expect(shareBtn).toBeVisible({timeout: 5000});
    await shareBtn.click();
    await expect(page.getByTestId('broker-sharing-panel')).toBeVisible({timeout: 5000});
}

// Helper: Open the real BrokerSharingModal from the broker list page (grid share icon).
async function openSharingModalFromList(page: Page) {
    await navigateTo(page, '/brokers');
    await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 10000});
    const shareBtn = page.locator('[data-testid^="broker-share-"]').first();
    await expect(shareBtn).toBeVisible({timeout: 10000});
    await shareBtn.click();
    await expect(page.getByTestId('broker-sharing-modal')).toBeVisible({timeout: 5000});
}

test.describe('Runes parity', () => {
    test.setTimeout(60_000);

    type OwnedUser = {id: number; username: string; email: string; password: string};
    type Grant = {user_id: number; role: 'OWNER' | 'EDITOR' | 'VIEWER'; share_percentage: number | string};
    type OwnedSharing = {owner: OwnedUser; viewer: OwnedUser; brokerId: number};

    async function authenticateOwned(request: APIRequestContext, user: OwnedUser) {
        const response = await request.post('/api/v1/auth/login', {data: {username: user.username, password: user.password}});
        expect(response.ok()).toBe(true);
        expect((await response.json()).user.id).toBe(user.id);
    }

    // Each test owns two disposable accounts, their complete ACL, and one empty
    // broker. Cleanup addresses only returned IDs, never a shared-row snapshot.
    async function withOwnedSharing(request: APIRequestContext, run: (owned: OwnedSharing) => Promise<void>) {
        const users: OwnedUser[] = [];
        let owner: OwnedUser | undefined;
        let brokerId: number | undefined;
        async function register(role: string): Promise<OwnedUser> {
            const suffix = uniqueSuffix();
            const credentials = {username: `runes_${role}_${suffix}`, email: `runes_${role}_${suffix}@example.com`, password: `Runes9!_${suffix}`};
            const response = await request.post('/api/v1/auth/register', {data: credentials});
            expect(response.status(), 'Disposable-account registration must be enabled; do not repair global state').toBe(201);
            const {user} = (await response.json()) as {user: {id: number; is_superuser: boolean}};
            const owned = {...credentials, id: user.id};
            users.push(owned);
            expect(user.is_superuser, 'These cases require ordinary disposable members').toBe(false);
            return owned;
        }
        try {
            owner = await register('owner');
            const viewer = await register('viewer');
            await authenticateOwned(request, owner);
            const name = `Runes sharing ${uniqueSuffix()}`;
            const created = await request.post('/api/v1/brokers', {data: [{name}]});
            expect(created.ok()).toBe(true);
            const {results} = (await created.json()) as {results: {name: string; success: boolean; broker_id: number | null}[]};
            const ownedBroker = results.find((result) => result.name === name);
            if (ownedBroker?.broker_id != null) brokerId = ownedBroker.broker_id;
            expect(ownedBroker).toMatchObject({name, success: true});
            if (brokerId === undefined) throw new Error(`No created broker ID returned for ${name}`);
            const seeded = await request.put(`/api/v1/brokers/${brokerId}/access`, {
                data: [
                    {user_id: owner.id, role: 'OWNER', share_percentage: 1},
                    {user_id: viewer.id, role: 'VIEWER', share_percentage: 0},
                ],
            });
            expect(seeded.ok()).toBe(true);
            await expectAcl(request, brokerId, owner.id, viewer.id, 'VIEWER');
            await run({owner, viewer, brokerId});
        } finally {
            // Continue cleaning the other owned resources even if one cleanup
            // fails, but never hide that failure or expand cleanup beyond IDs.
            const failures: unknown[] = [];
            if (owner && brokerId !== undefined) {
                try {
                    await authenticateOwned(request, owner);
                    const deleted = await request.delete('/api/v1/brokers', {params: {ids: brokerId}});
                    expect(deleted.ok()).toBe(true);
                    const {results} = (await deleted.json()) as {results: {id: number; success: boolean}[]};
                    expect(results.find((result) => result.id === brokerId)).toMatchObject({id: brokerId, success: true});
                } catch (error) {
                    failures.push(error);
                }
            }
            for (const user of users) {
                try {
                    await authenticateOwned(request, user);
                    const deleted = await request.delete('/api/v1/auth/users/me');
                    expect(deleted.ok()).toBe(true);
                } catch (error) {
                    failures.push(error);
                }
            }
            if (failures.length) throw new AggregateError(failures, 'Runes parity could not clean all owned resources');
        }
    }

    function aclProjection(grants: Grant[]) {
        return grants.map((grant) => ({user_id: grant.user_id, role: grant.role, share_percentage: Number(grant.share_percentage)})).sort((a, b) => a.user_id - b.user_id);
    }

    async function expectAcl(request: APIRequestContext, brokerId: number, ownerId: number, viewerId: number, role: 'EDITOR' | 'VIEWER') {
        const response = await request.get(`/api/v1/brokers/${brokerId}/access`);
        expect(response.ok()).toBe(true);
        const {items} = (await response.json()) as {items: Grant[]};
        // Cardinality is intentional: the test owns the broker's complete ACL.
        expect(aclProjection(items)).toEqual(
            aclProjection([
                {user_id: ownerId, role: 'OWNER', share_percentage: 1},
                {user_id: viewerId, role, share_percentage: 0},
            ]),
        );
    }

    async function openOwnedModal(page: Page, brokerId: number, ownerId: number) {
        await navigateTo(page, '/brokers');
        await expect(page.getByTestId('brokers-page')).toHaveAttribute('data-busy', 'false', {timeout: 15_000});
        // The grid is not paginated. The exact ID remains safe even when the
        // discovery section lists brokers owned by neighbouring workers.
        await page.getByTestId(`broker-share-${brokerId}`).click();
        await expect(page.getByTestId('broker-sharing-modal')).toBeVisible();
        await expect(page.getByTestId('broker-sharing-panel')).toHaveAttribute('data-access-state', 'ready', {timeout: 10_000});
        await expect(page.getByTestId('sharing-owners-column').getByTestId(`access-entry-${ownerId}`)).toBeVisible();
    }

    async function editOwnedRole(page: Page, userId: number, role: 'EDITOR' | 'VIEWER') {
        await page.getByTestId(`access-entry-${userId}`).click();
        const editor = page.getByTestId('sharing-edit-user-modal');
        await expect(editor).toBeVisible();
        await editor.getByTestId('sharing-edit-role-trigger').click();
        await editor.getByTestId(`sharing-edit-role-option-${role}`).click();
        await editor.getByTestId('sharing-confirm-edit').click();
        await expect(editor).toBeHidden();
        const column = role === 'EDITOR' ? 'sharing-editors-column' : 'sharing-viewers-column';
        await expect(page.getByTestId(column).getByTestId(`access-entry-${userId}`)).toBeVisible();
        await expect(page.getByTestId('sharing-save-btn')).toBeEnabled();
    }

    test('owned modal resets and discards drafts, then saves the complete ACL and reopens clean', async ({page, request}) => {
        await withOwnedSharing(request, async ({owner, viewer, brokerId}) => {
            await login(page, owner);
            const path = `/api/v1/brokers/${brokerId}/access`;
            const puts: Grant[][] = [];
            const recordPut = (req: Request) => {
                if (req.method() === 'PUT' && new URL(req.url()).pathname === path) puts.push(req.postDataJSON() as Grant[]);
            };
            page.on('request', recordPut);
            try {
                await openOwnedModal(page, brokerId, owner.id);
                const modal = page.getByTestId('broker-sharing-modal');
                const viewerEntry = page.getByTestId('sharing-viewers-column').getByTestId(`access-entry-${viewer.id}`);
                await expect(viewerEntry).toBeVisible();
                await expect(page.getByTestId('sharing-save-btn')).toBeDisabled();

                await editOwnedRole(page, viewer.id, 'EDITOR');
                await page.getByTestId('sharing-reset-btn').click();
                await expect(viewerEntry).toBeVisible();
                await expect(page.getByTestId('sharing-save-btn')).toBeDisabled();
                await expectAcl(request, brokerId, owner.id, viewer.id, 'VIEWER');
                expect(puts).toEqual([]);

                await editOwnedRole(page, viewer.id, 'EDITOR');
                await modal.press('Escape');
                await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible();
                await page.getByTestId('confirm-modal-cancel').click();
                await expect(page.getByTestId('confirm-modal-confirm')).toBeHidden();
                await expect(modal).toBeVisible();
                await expect(page.getByTestId('sharing-editors-column').getByTestId(`access-entry-${viewer.id}`)).toBeVisible();
                await expect(page.getByTestId('sharing-save-btn')).toBeEnabled();

                await modal.press('Escape');
                await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible();
                await page.getByTestId('confirm-modal-confirm').click();
                await expect(modal).toBeHidden();
                await expect(page.getByTestId('confirm-modal-confirm')).toBeHidden();
                await openOwnedModal(page, brokerId, owner.id);
                await expect(viewerEntry).toBeVisible();
                await expect(page.getByTestId('sharing-save-btn')).toBeDisabled();
                await expectAcl(request, brokerId, owner.id, viewer.id, 'VIEWER');
                expect(puts).toEqual([]);

                await editOwnedRole(page, viewer.id, 'EDITOR');
                const response = page.waitForResponse((res) => res.request().method() === 'PUT' && new URL(res.url()).pathname === path);
                await page.getByTestId('sharing-save-btn').click();
                const saved = await response;
                expect(saved.ok()).toBe(true);
                const expectedAcl: Grant[] = [
                    {user_id: owner.id, role: 'OWNER', share_percentage: 1},
                    {user_id: viewer.id, role: 'EDITOR', share_percentage: 0},
                ];
                expect(aclProjection(saved.request().postDataJSON() as Grant[])).toEqual(aclProjection(expectedAcl));
                // F3 through the actual legacy modal host: Save must close it,
                // not open a second discard prompt while dirty clears later.
                await expect(modal).toBeHidden({timeout: 10_000});
                await expect(page.getByTestId('brokers-page')).toHaveAttribute('data-busy', 'false', {timeout: 15_000});
                await expect(page.getByTestId('confirm-modal-confirm')).toBeHidden();
                await expectAcl(request, brokerId, owner.id, viewer.id, 'EDITOR');

                await openOwnedModal(page, brokerId, owner.id);
                await expect(page.getByTestId('sharing-editors-column').getByTestId(`access-entry-${viewer.id}`)).toBeVisible();
                await expect(page.getByTestId('sharing-save-btn')).toBeDisabled();
                await modal.press('Escape');
                await expect(modal).toBeHidden();
                expect(puts.map(aclProjection)).toEqual([aclProjection(expectedAcl)]);
            } finally {
                page.off('request', recordPut);
            }
        });
    });

    test('owned viewer reloads the Info panel read-only while self-service stays reachable', async ({page, request}) => {
        await withOwnedSharing(request, async ({owner, viewer, brokerId}) => {
            await login(page, viewer);
            const writes: string[] = [];
            const recordWrite = (req: Request) => {
                if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method()) && new URL(req.url()).pathname.startsWith(`/api/v1/brokers/${brokerId}/access`)) writes.push(req.url());
            };
            page.on('request', recordWrite);
            try {
                // Two real document loads exercise the unchanged legacy Info
                // host and remount, rather than inspecting only a modal shell.
                for (const visit of ['initial', 'reload']) {
                    await test.step(visit, async () => {
                        await navigateTo(page, `/brokers/${brokerId}`);
                        await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 15_000});
                        await page.getByTestId('broker-share-button').click();
                        const panel = page.getByTestId('broker-sharing-panel');
                        await expect(panel).toHaveAttribute('data-access-state', 'ready', {timeout: 10_000});
                        const entry = panel.getByTestId('sharing-viewers-column').getByTestId(`access-entry-${viewer.id}`);
                        await expect(entry).toBeVisible();
                        await expect(entry).toBeDisabled();
                        await expect(panel.getByTestId(`access-entry-${owner.id}`)).toBeDisabled();
                        await expect(panel.getByTestId('sharing-self-leave-btn')).toBeEnabled();
                        // Presence/ready barriers above give these negatives teeth.
                        await expect(panel.getByTestId('sharing-add-user-btn')).toBeHidden();
                        await expect(panel.getByTestId('sharing-save-btn')).toBeHidden();
                        await expect(panel.getByTestId('sharing-reset-btn')).toBeHidden();
                        await expect(panel.getByTestId('sharing-self-demote-btn')).toBeHidden();
                    });
                }
                await expectAcl(request, brokerId, owner.id, viewer.id, 'VIEWER');
                expect(writes).toEqual([]);
            } finally {
                page.off('request', recordWrite);
            }
        });
    });
});
async function expectOwnershipChartCanvas(page: Page) {
    const section = page.getByTestId('ownership-chart-section');
    await expect(section).toBeVisible({timeout: 5000});

    const canvas = section.locator('canvas').first();
    await expect(canvas).toBeVisible({timeout: 5000});
    await expect
        .poll(
            async () => {
                const box = await canvas.boundingBox();
                if (!box || box.width <= 0 || box.height <= 0) return 'zero-css-size';

                return canvas.evaluate((node) => {
                    const htmlCanvas = node as HTMLCanvasElement;
                    return htmlCanvas.width > 0 && htmlCanvas.height > 0 ? 'non-zero' : 'zero-bitmap-size';
                });
            },
            {timeout: 5000},
        )
        .toBe('non-zero');
}

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('Broker Sharing', () => {
    test.describe('Share Button Visibility', () => {
        test('S1: share button visible for OWNER on broker detail', async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await expect(page.getByTestId('broker-share-button')).toBeVisible();
        });

        test('S2: share button visible read-only for VIEWER', async ({page}) => {
            // TEST_USER_2 is VIEWER on Interactive Brokers (from populate)
            await login(page, TEST_USER_2);
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 10000});
            // TEST_USER_2 only has VIEWER access, so find any broker card
            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            await expect(brokerCards.first()).toBeVisible({timeout: 10000});
            await brokerCards.first().click();
            await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 10000});
            // Share button IS now always visible (design: everyone can see who has access)
            const shareBtn = page.getByTestId('broker-share-button');
            await expect(shareBtn).toBeVisible({timeout: 5000});
            // Edit button should still NOT be visible for VIEWER (unchanged)
            await expect(page.getByTestId('broker-edit-button')).not.toBeVisible({timeout: 2000});
            // Opening it must be read-only: no "add user" control for a non-OWNER
            await shareBtn.click();
            await expect(page.getByTestId('broker-sharing-panel')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('sharing-add-user-btn')).not.toBeVisible({timeout: 2000});
        });

        test('S3: share button opens the sharing panel (Info tab)', async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);
            // Panel is visible (openSharingModal asserts this)
        });
    });

    // BrokerSharingModal (the actual modal, with close/Escape/confirm-discard chrome) is
    // only used from the broker list page's share icon — the detail page's "Info" tab
    // embeds BrokerSharingPanel inline, without modal chrome (see openSharingModal above).
    test.describe('BrokerSharingModal (List Page)', () => {
        test('S9: close modal with Escape key', async ({page}) => {
            await login(page, TEST_ADMIN);
            await openSharingModalFromList(page);
            await expectOwnershipChartCanvas(page);
            await page.getByTestId('broker-sharing-modal').press('Escape');
            await expect(page.getByTestId('broker-sharing-modal')).not.toBeVisible({timeout: 3000});
        });
    });

    test.describe('BrokerSharingPanel Content', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);
        });

        test('S4: panel shows ownership chart section', async ({page}) => {
            await expectOwnershipChartCanvas(page);
        });

        test('S5: panel shows at least the current OWNER in badge list', async ({page}) => {
            // Should see at least one access-entry badge (the OWNER)
            const entries = page.locator('[data-testid^="access-entry-"]');
            await expect(entries.first()).toBeVisible({timeout: 5000});
        });

        test('S6: add user button is visible', async ({page}) => {
            await expect(page.getByTestId('sharing-add-user-btn')).toBeVisible();
        });

        test('S7: clicking add user opens add-user modal', async ({page}) => {
            await page.getByTestId('sharing-add-user-btn').click();
            await expect(page.getByTestId('sharing-add-form')).toBeVisible({timeout: 3000});
        });

        test('S8: save button is disabled when no changes', async ({page}) => {
            const saveBtn = page.getByTestId('sharing-save-btn');
            await expect(saveBtn).toBeVisible();
            await expect(saveBtn).toBeDisabled();
        });

        test('S10: three role columns are visible (Owners, Editors, Viewers)', async ({page}) => {
            await expect(page.getByTestId('sharing-owners-column')).toBeVisible({timeout: 3000});
            await expect(page.getByTestId('sharing-editors-column')).toBeVisible({timeout: 3000});
            await expect(page.getByTestId('sharing-viewers-column')).toBeVisible({timeout: 3000});
        });
    });

    test.describe('BrokerSharingPanel - Add User Flow', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);
        });

        test('S11: add user form has a user picker', async ({page}) => {
            await page.getByTestId('sharing-add-user-btn').click();
            await expect(page.getByTestId('sharing-add-form')).toBeVisible();
            await expect(page.getByTestId('sharing-user-select-trigger')).toBeVisible();
        });

        test('S12: user picker lists users up-front and narrows down while typing', async ({page}) => {
            await page.getByTestId('sharing-add-user-btn').click();
            await expect(page.getByTestId('sharing-add-form')).toBeVisible({timeout: 3000});

            // Opening the picker must already show the candidate list — no typing required
            await page.getByTestId('sharing-user-select-trigger').click();
            const options = page.locator('[data-testid^="search-select-option-"]');
            await expect(options.first()).toBeVisible({timeout: 5000});

            // Typing narrows the list client-side ('frank' is a free user on no broker)
            const searchInput = page.getByTestId('sharing-user-select-search');
            await expect(searchInput).toBeVisible();
            await searchInput.pressSequentially('frank', {delay: 50});

            await expect(options.first()).toBeVisible({timeout: 5000});
            const remaining = await options.count();
            for (let i = 0; i < remaining; i++) {
                await expect(options.nth(i)).toContainText(/frank/i);
            }
        });
    });

    test.describe('BrokerSharingPanel - Edit User', () => {
        test('S13: clicking edit on a badge opens edit modal', async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);

            // Find first access entry edit button
            const editBtn = page.locator('[data-testid^="access-entry-"] button[title]').first();
            if (await editBtn.isVisible({timeout: 2000})) {
                await editBtn.click();
                // Edit modal/form should appear
                await expect(page.locator('[role="dialog"], [data-testid$="-modal"]').first()).toBeVisible({timeout: 10_000});
            }
        });
    });

    test.describe('Role-Based Access', () => {
        test('S14: EDITOR sees share button read-only on broker they edit', async ({page}) => {
            // TEST_USER is EDITOR on Directa SIM (from populate)
            await login(page, TEST_USER);
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 10000});
            // Find Directa SIM card specifically (where user is EDITOR)
            const directaCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: 'Directa'});
            if (await directaCard.isVisible({timeout: 5000})) {
                await directaCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 10000});
                // Share button IS now always visible (design: everyone can see who has access)
                const shareBtn = page.getByTestId('broker-share-button');
                await expect(shareBtn).toBeVisible({timeout: 2000});
                // But edit button should be visible too (EDITOR can edit the broker itself)
                await expect(page.getByTestId('broker-edit-button')).toBeVisible({timeout: 2000});
                // Opening it must be read-only: no "add user" control for a non-OWNER
                await shareBtn.click();
                await expect(page.getByTestId('broker-sharing-panel')).toBeVisible({timeout: 5000});
                await expect(page.getByTestId('sharing-add-user-btn')).not.toBeVisible({timeout: 2000});
            }
        });
    });

    test.describe('Dark Mode', () => {
        test('S15: sharing panel renders in dark mode', async ({page}) => {
            await login(page, TEST_ADMIN);

            // Enable dark mode via settings
            await navigateTo(page, '/settings');
            await expect(page.getByTestId('settings-page')).toBeVisible({timeout: 10000});
            const themeToggle = page.getByTestId('theme-toggle');
            if (await themeToggle.isVisible({timeout: 3000})) {
                await themeToggle.click();
            }

            // Navigate to broker detail and open the sharing panel (Info tab)
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);

            // Verify panel content is visible in dark mode
            await expectOwnershipChartCanvas(page);
            // Verify dark class on html
            const isDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));
            expect(isDark).toBe(true);
        });
    });
});
