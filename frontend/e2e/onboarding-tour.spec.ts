/**
 * Onboarding Round 5 — per-step progress and contextual polish.
 *
 * Every case owns a disposable account because pending onboarding is persisted
 * per user. Bulk cases also create one uniquely identified broker/transaction,
 * discard every draft, and remove the whole account in finally.
 */

import {expect, test, type APIRequestContext, type Locator, type Page, type Request} from './fixtures/playwright';
import {login, navigateTo} from './fixtures/auth-helpers';
import {waitForParseVerdict, waitForSettled} from './fixtures/app-events';
import {uniqueSuffix} from './fixtures/unique';

test.setTimeout(120_000);

type DisposableUser = {id: number; username: string; email: string; password: string};
type PointerMode = 'none' | 'cursor';
type HighlightMode = 'none' | 'pulse';
type Box = {x: number; y: number; width: number; height: number};
type AtomicGuideTarget = {testId: string; describedBy: string | null; rect: Box};
type BrokerScrollByCall = {top: number; left: number; behavior: string};
type BrokerScrollState = {scrollByCalls: BrokerScrollByCall[]; scrollIntoViewTargets: string[]};
type BrokerGeometrySample = BrokerScrollState & {scrollY: number; viewportHeight: number; header: Box; views: Box; add: Box};
type BrokerScrollHarness = {
    state: BrokerScrollState;
    originalScrollBy: typeof window.scrollBy;
    originalScrollIntoView: typeof Element.prototype.scrollIntoView;
};
type OwnedTransaction = {brokerId: number; brokerName: string; transactionId: number; rowId: string; marker: string};
type ImportScrollState = {
    initialWindowY: number;
    initialWizardScrollTop: number | null;
    windowEvents: number[];
    wizardScrollEvents: number[];
    scrollIntoViewTargets: string[];
};
type ImportScrollHarness = {
    state: ImportScrollState;
    originalScrollIntoView: typeof Element.prototype.scrollIntoView;
    onWindowScroll: () => void;
    onElementScroll: (event: Event) => void;
    observer: MutationObserver;
};
type Round5Window = Window & {
    __lfRound5BrokerScroll?: BrokerScrollHarness;
    __lfRound5ImportScroll?: ImportScrollHarness;
};

const DESCRIPTION_ID = 'onboarding-coachmark-description';
const CORE_ORDER = ['intro.scene', 'intro.navigation', 'intro.dashboard', 'intro.transactions_nav', 'intro.brokers_nav', 'intro.fx_nav', 'intro.assets_nav', 'intro.tools_nav', 'intro.settings_nav'] as const;
const BULK_STEPS = ['transaction.bulk.workspace', 'transaction.bulk.validation', 'transaction.bulk.selection', 'transaction.bulk.save'] as const;
const BULK_ACCOUNT_SETUP_SKIPS = ['transactions_page_guide', 'transaction_create_guide'] as const;
const TRANSACTION_FORM_GUIDE_STEPS = [
    {stepId: 'transaction.create.basics', targetId: 'tx-form-type-wrap', pointer: 'none', highlight: 'pulse'},
    {stepId: 'transaction.create.amounts', targetId: 'tx-form-required', pointer: 'none', highlight: 'pulse', allowTargetOverlap: true},
    {stepId: 'transaction.create.details', targetId: 'tx-form-optional-toggle', pointer: 'none', highlight: 'pulse'},
    {stepId: 'transaction.create.save', targetId: 'tx-form-save', pointer: 'cursor', highlight: 'none'},
] as const;

async function registerDisposableUser(request: APIRequestContext, tag: string): Promise<DisposableUser> {
    const suffix = uniqueSuffix();
    const user = {
        username: `tour_${tag}_${suffix}`,
        email: `tour_${tag}_${suffix}@example.com`,
        password: `Tour9!_${suffix}`,
    };
    const response = await request.post('/api/v1/auth/register', {data: user});
    expect(response.status(), 'Disposable-account registration must be enabled; this spec never rewrites global settings').toBe(201);
    const created = (await response.json()) as {user: {id: number}};
    return {...user, id: created.user.id};
}

async function deleteDisposableUser(request: APIRequestContext, user: DisposableUser, brokerIds: readonly number[] = [], fileIds: readonly string[] = []): Promise<void> {
    const loggedIn = await request.post('/api/v1/auth/login', {
        data: {username: user.username, password: user.password},
    });
    expect(loggedIn.ok(), 'Cleanup must authenticate as the account it owns').toBe(true);
    const body = (await loggedIn.json()) as {user: {id: number}};
    expect(body.user.id, 'Cleanup must remain scoped to this test user').toBe(user.id);
    const failures: string[] = [];
    try {
        for (const fileId of fileIds) {
            const deleted = await request.delete(`/api/v1/brokers/import/files/${fileId}`);
            if (!deleted.ok()) {
                failures.push(`file ${fileId}: HTTP ${deleted.status()} ${await deleted.text()}`);
                continue;
            }
            const result = (await deleted.json()) as {success?: boolean; file_id?: string};
            if (result.success !== true || result.file_id !== fileId) {
                failures.push(`file ${fileId}: ${JSON.stringify(result)}`);
            }
        }
        for (const brokerId of brokerIds) {
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
    expect(failures, 'Cleanup must delete every file and broker owned by this test').toEqual([]);
}

async function skipOwnedFlows(page: Page, flows: readonly string[]): Promise<void> {
    const response = await page.request.get('/api/v1/settings/onboarding');
    expect(response.ok(), `Owned onboarding progress setup failed (HTTP ${response.status()})`).toBe(true);
    const progress = (await response.json()) as {
        flows: Array<{flow: string; status: string; current_version: number}>;
    };
    for (const flow of flows) {
        const item = progress.flows.find((candidate) => candidate.flow === flow);
        if (!item) throw new Error(`Disposable account has no onboarding progress for ${flow}`);
        expect(item.status, `${flow} must still be pending before this test skips it`).toBe('pending');
        const skipped = await page.request.post(`/api/v1/settings/onboarding/${flow}/skip`, {
            data: {expected_version: item.current_version},
        });
        expect(skipped.ok(), `Disposable account could not skip ${flow} (HTTP ${skipped.status()})`).toBe(true);
    }
}

async function skipOwnedSteps(page: Page, flow: string, stepIds: readonly string[]): Promise<void> {
    const response = await page.request.get('/api/v1/settings/onboarding');
    expect(response.ok(), `Owned onboarding step setup failed (HTTP ${response.status()})`).toBe(true);
    const progress = (await response.json()) as {
        flows: Array<{
            flow: string;
            current_version: number;
            steps?: Array<{step_id: string; status: string}>;
        }>;
    };
    const item = progress.flows.find((candidate) => candidate.flow === flow);
    if (!item) throw new Error(`Disposable account has no onboarding progress for ${flow}`);
    for (const stepId of stepIds) {
        const step = item.steps?.find((candidate) => candidate.step_id === stepId);
        if (!step) throw new Error(`Disposable account has no onboarding step ${flow}:${stepId}`);
        expect(step.status, `${flow}:${stepId} must still be pending before this test skips it`).toBe('pending');
        const skipped = await page.request.post(`/api/v1/settings/onboarding/${flow}/steps/${stepId}/skip`, {
            data: {expected_version: item.current_version},
        });
        expect(skipped.ok(), `Disposable account could not skip ${flow}:${stepId} (HTTP ${skipped.status()})`).toBe(true);
    }
}

async function prepareDisposableBulkAccount(page: Page, extraSkips: readonly string[] = []): Promise<void> {
    await completeWelcome(page);
    await page.getByTestId('onboarding-intro-close').click();
    await expect(page.getByTestId('onboarding-intro-scene')).toHaveCount(0, {timeout: 10_000});
    await skipOwnedFlows(page, [...BULK_ACCOUNT_SETUP_SKIPS, ...extraSkips]);
    await page.reload();
    await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
    await expect(page.getByTestId('onboarding-intro-scene')).toHaveCount(0);
    await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);
}

async function createOwnedTransaction(page: Page, tag: string, brokerIds: number[]): Promise<OwnedTransaction> {
    const suffix = uniqueSuffix();
    const brokerName = `tour-${tag}-broker-${suffix}`;
    const brokerResponse = await page.request.post('/api/v1/brokers', {
        data: [{name: brokerName, opened_at: '2025-01-01'}],
    });
    expect(brokerResponse.ok(), `Owned broker setup failed (HTTP ${brokerResponse.status()})`).toBe(true);
    const brokerBody = (await brokerResponse.json()) as {
        results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>;
    };
    const broker = brokerBody.results.find((candidate) => candidate.name === brokerName);
    if (!broker?.success || typeof broker.broker_id !== 'number') {
        throw new Error(`Owned broker setup returned no id for ${brokerName}: ${broker?.message ?? 'missing result'}`);
    }
    brokerIds.push(broker.broker_id);

    const marker = `tour-${tag}-transaction-${suffix}`;
    const transactionResponse = await page.request.post('/api/v1/transactions/commit', {
        data: {
            creates: [
                {
                    broker_id: broker.broker_id,
                    type: 'DEPOSIT',
                    date: '2025-01-17',
                    cash: {code: 'EUR', amount: '10'},
                    description: marker,
                },
            ],
        },
    });
    expect(transactionResponse.ok(), `Owned transaction setup failed (HTTP ${transactionResponse.status()})`).toBe(true);
    const transactionBody = (await transactionResponse.json()) as {
        committed?: boolean;
        issues?: unknown[];
        results?: Array<{ids?: number[]}>;
    };
    expect(transactionBody.committed, `Owned transaction setup rolled back: ${JSON.stringify(transactionBody.issues ?? [])}`).toBe(true);
    const ids = (transactionBody.results ?? []).flatMap((result) => result.ids ?? []);
    expect(ids, 'Owned setup must create exactly its requested transaction').toHaveLength(1);
    const transactionId = ids.find((id) => Number.isInteger(id) && id > 0);
    if (transactionId == null) throw new Error('Owned transaction setup returned no positive transaction id');
    return {brokerId: broker.broker_id, brokerName, transactionId, rowId: `tx-${transactionId}`, marker};
}

async function completeWelcome(page: Page): Promise<void> {
    await expect(page).toHaveURL(/\/welcome(?:[/?#]|$)/, {timeout: 15_000});
    const form = page.getByTestId('welcome-form');
    await expect(form).toBeVisible({timeout: 10_000});
    await expect(page.getByTestId('welcome-continue')).toBeEnabled({timeout: 10_000});
    await page.getByTestId('welcome-continue').click();
    await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/, {timeout: 15_000});
    await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
    await expect(page.getByTestId('onboarding-intro-scene')).toHaveAttribute('data-state', 'intro-scene', {timeout: 10_000});
}

async function stableGuideBoxes(page: Page): Promise<{target: Box; panel: Box}> {
    let previous = '';
    let result: {target: Box; panel: Box} | null = null;
    await expect
        .poll(
            async () => {
                const sample = await page.evaluate((descriptionId) => {
                    const target = document.querySelector<HTMLElement>(`[aria-describedby="${descriptionId}"]:not([data-testid="onboarding-coachmark-panel"])`);
                    const panel = document.querySelector<HTMLElement>('[data-testid="onboarding-coachmark-panel"]');
                    if (!target || !panel) return null;
                    const targetRect = target.getBoundingClientRect();
                    const panelRect = panel.getBoundingClientRect();
                    return {
                        target: {x: targetRect.x, y: targetRect.y, width: targetRect.width, height: targetRect.height},
                        panel: {x: panelRect.x, y: panelRect.y, width: panelRect.width, height: panelRect.height},
                    };
                }, DESCRIPTION_ID);
                if (!sample) return 'missing';
                const signature = [sample.target.x, sample.target.y, sample.target.width, sample.target.height, sample.panel.x, sample.panel.y, sample.panel.width, sample.panel.height].map((value) => value.toFixed(2)).join(':');
                const stable = signature === previous;
                previous = signature;
                if (stable) result = sample;
                return stable ? 'stable' : signature;
            },
            {timeout: 10_000, message: 'Onboarding target/panel never reached two identical atomic geometry samples'},
        )
        .toBe('stable');
    if (!result) throw new Error('Onboarding target/panel has no measurable bounding box');
    return result;
}

async function sampleTransactionFormTargets(form: Locator): Promise<AtomicGuideTarget[]> {
    return form.evaluate(
        (root, targetIds) =>
            targetIds.map((testId) => {
                const target = root.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
                if (!target) throw new Error(`Transaction form guide target ${testId} is not rendered`);
                const rect = target.getBoundingClientRect();
                return {
                    testId,
                    describedBy: target.getAttribute('aria-describedby'),
                    rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
                };
            }),
        TRANSACTION_FORM_GUIDE_STEPS.map(({targetId}) => targetId),
    );
}

async function sampleBrokerGeometry(page: Page): Promise<BrokerGeometrySample> {
    return page.evaluate(() => {
        const harness = (window as Round5Window).__lfRound5BrokerScroll;
        const box = (testId: string): Box => {
            const element = document.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
            if (!element) throw new Error(`Broker guide geometry target ${testId} is not rendered`);
            const rect = element.getBoundingClientRect();
            return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
        };
        return {
            scrollY: window.scrollY,
            viewportHeight: window.innerHeight,
            header: box('app-header'),
            views: box('broker-page-views'),
            add: box('add-broker-button'),
            scrollByCalls: harness?.state.scrollByCalls.map((call) => ({...call})) ?? [],
            scrollIntoViewTargets: [...(harness?.state.scrollIntoViewTargets ?? [])],
        };
    });
}

async function placeBrokerAddUnderHeader(page: Page): Promise<BrokerGeometrySample> {
    await page.evaluate(() => {
        const root = document.querySelector<HTMLElement>('[data-testid="brokers-page"]');
        const header = document.querySelector<HTMLElement>('[data-testid="app-header"]');
        const add = document.querySelector<HTMLElement>('[data-testid="add-broker-button"]');
        if (!root || !header || !add) throw new Error('Broker guide layout is not mounted');

        // The disposable account's empty Broker page can be shorter than the
        // viewport. Give this document enough real scroll range, then position
        // Add so the sticky header hides only its top edge.
        root.style.minHeight = `${window.innerHeight * 2}px`;
        const headerRect = header.getBoundingClientRect();
        const addRect = add.getBoundingClientRect();
        const desiredTop = headerRect.bottom - Math.min(8, addRect.height / 2);
        window.scrollTo({top: window.scrollY + addRect.top - desiredTop, behavior: 'auto'});
    });

    await expect(page.getByTestId('app-header')).toHaveAttribute('data-scroll-state', 'pinned', {timeout: 5_000});
    await expect(page.getByTestId('onboarding-coachmark')).toHaveAttribute('data-geometry-state', 'stable', {timeout: 10_000});

    let sample: BrokerGeometrySample | null = null;
    await expect
        .poll(
            async () => {
                sample = await sampleBrokerGeometry(page);
                const headerBottom = sample.header.y + sample.header.height;
                return sample.add.y < headerBottom && sample.add.y + sample.add.height > headerBottom;
            },
            {timeout: 5_000, message: 'Broker Add never reached the intentionally header-obscured precondition'},
        )
        .toBe(true);
    if (!sample) throw new Error('Broker Add has no atomic geometry sample after positioning');
    return sample;
}

async function installBrokerScrollObservation(page: Page): Promise<void> {
    await page.evaluate(() => {
        const host = window as Round5Window;
        if (host.__lfRound5BrokerScroll) throw new Error('Round 5 Broker scroll observation is already installed');

        const state: BrokerScrollState = {scrollByCalls: [], scrollIntoViewTargets: []};
        const originalScrollBy = window.scrollBy;
        const originalScrollIntoView = Element.prototype.scrollIntoView;
        window.scrollBy = ((...args: unknown[]) => {
            const first = args[0];
            if (typeof first === 'number') {
                state.scrollByCalls.push({
                    left: first,
                    top: typeof args[1] === 'number' ? args[1] : 0,
                    behavior: 'auto',
                });
            } else {
                const options = (first ?? {}) as ScrollToOptions;
                state.scrollByCalls.push({
                    left: options.left ?? 0,
                    top: options.top ?? 0,
                    behavior: options.behavior ?? 'auto',
                });
            }
            Reflect.apply(originalScrollBy, window, args);
        }) as typeof window.scrollBy;
        Element.prototype.scrollIntoView = function (this: Element, arg?: boolean | ScrollIntoViewOptions): void {
            const element = this as HTMLElement;
            state.scrollIntoViewTargets.push(element.dataset.testid ?? element.id ?? element.tagName.toLowerCase());
            Reflect.apply(originalScrollIntoView, this, arg === undefined ? [] : [arg]);
        };
        host.__lfRound5BrokerScroll = {state, originalScrollBy, originalScrollIntoView};
    });
}

async function restoreBrokerScrollObservation(page: Page): Promise<void> {
    await page.evaluate(() => {
        const host = window as Round5Window;
        const harness = host.__lfRound5BrokerScroll;
        if (!harness) return;
        window.scrollBy = harness.originalScrollBy;
        Element.prototype.scrollIntoView = harness.originalScrollIntoView;
        delete host.__lfRound5BrokerScroll;
    });
}

function overlapArea(first: {x: number; y: number; width: number; height: number}, second: {x: number; y: number; width: number; height: number}): number {
    const width = Math.max(0, Math.min(first.x + first.width, second.x + second.width) - Math.max(first.x, second.x));
    const height = Math.max(0, Math.min(first.y + first.height, second.y + second.height) - Math.max(first.y, second.y));
    return width * height;
}

async function expectGuideGeometry(page: Page, pointer: PointerMode, allowTargetOverlap = false): Promise<void> {
    const coachmark = page.getByTestId('onboarding-coachmark');
    await expect(coachmark).toHaveAttribute('data-target-stable', 'true', {timeout: 10_000});
    const {target: targetBox, panel: panelBox} = await stableGuideBoxes(page);
    const viewport = page.viewportSize();
    if (!viewport) throw new Error('The Playwright project did not publish a viewport');

    expect(panelBox.x).toBeGreaterThanOrEqual(0);
    expect(panelBox.y).toBeGreaterThanOrEqual(0);
    expect(panelBox.x + panelBox.width).toBeLessThanOrEqual(viewport.width);
    expect(panelBox.y + panelBox.height).toBeLessThanOrEqual(viewport.height);
    if (!allowTargetOverlap) expect(overlapArea(panelBox, targetBox)).toBe(0);

    const geometry = await coachmark.evaluate((element) => {
        const data = (element as HTMLElement).dataset;
        return {
            centerX: Number(data.targetCenterX),
            centerY: Number(data.targetCenterY),
            hotspotX: data.pointerHotspotX === '' ? null : Number(data.pointerHotspotX),
            hotspotY: data.pointerHotspotY === '' ? null : Number(data.pointerHotspotY),
        };
    });
    expect(Math.abs(geometry.centerX - (targetBox.x + targetBox.width / 2))).toBeLessThanOrEqual(2);
    expect(Math.abs(geometry.centerY - (targetBox.y + targetBox.height / 2))).toBeLessThanOrEqual(2);

    if (pointer === 'cursor') {
        expect(geometry.hotspotX).not.toBeNull();
        expect(geometry.hotspotY).not.toBeNull();
        expect(geometry.hotspotX as number).toBeGreaterThanOrEqual(targetBox.x - 2);
        expect(geometry.hotspotX as number).toBeLessThanOrEqual(targetBox.x + targetBox.width + 2);
        expect(geometry.hotspotY as number).toBeGreaterThanOrEqual(targetBox.y - 2);
        expect(geometry.hotspotY as number).toBeLessThanOrEqual(targetBox.y + targetBox.height + 2);
    } else {
        expect(geometry.hotspotX).toBeNull();
        expect(geometry.hotspotY).toBeNull();
    }
}

async function activeGuideTarget(page: Page): Promise<Locator> {
    const target = page.locator(`[aria-describedby="${DESCRIPTION_ID}"]:not([data-testid="onboarding-coachmark-panel"])`);
    await expect(target).toHaveCount(1, {timeout: 10_000});
    await expect(target).toBeVisible();
    return target;
}

async function expectGuideStep(
    page: Page,
    options: {
        stepId: string;
        target?: Locator;
        pointer: PointerMode;
        highlight: HighlightMode;
        backdrop: boolean;
        placement?: 'top' | 'bottom' | 'left' | 'right' | 'center';
        allowTargetOverlap?: boolean;
    },
): Promise<{coachmark: Locator; target: Locator}> {
    const coachmark = page.getByTestId('onboarding-coachmark');
    await expect(coachmark).toHaveAttribute('data-step-id', options.stepId, {timeout: 15_000});
    await expect(coachmark).toHaveAttribute('data-guide-state', 'anchored', {timeout: 15_000});
    await expect(coachmark).toHaveAttribute('data-geometry-state', 'stable', {timeout: 15_000});
    await expect(coachmark).toHaveAttribute('data-pointer', options.pointer);
    await expect(coachmark).toHaveAttribute('data-highlight', options.highlight);
    await expect(coachmark).toHaveAttribute('data-panel-placement', options.placement ?? /^(top|bottom|left|right|center)$/);
    const target = options.target ?? (await activeGuideTarget(page));
    await expect(target).toHaveAttribute('aria-describedby', DESCRIPTION_ID);
    await expectGuideGeometry(page, options.pointer, options.allowTargetOverlap);

    if (options.pointer === 'cursor') {
        const pointer = page.getByTestId('onboarding-coachmark-pointer');
        await expect(pointer).toBeVisible();
        await expect(pointer.locator('svg')).toHaveCount(1);
        const colors = await pointer.evaluate((element) => {
            const style = getComputedStyle(element);
            return {background: style.backgroundColor, foreground: style.color};
        });
        expect(colors.background, 'Cursor background must be translucent immediately').toMatch(/(?:0\.7|70%)/);
        expect(colors.foreground, 'Cursor glyph must be translucent immediately').toMatch(/(?:0\.8|80%)/);
    } else {
        await expect(page.getByTestId('onboarding-coachmark-pointer')).toHaveCount(0);
    }
    await expect(coachmark.locator('[data-testid="onboarding-coachmark-pointer-line"]')).toHaveCount(0);

    if (options.highlight === 'pulse') {
        await expect(page.getByTestId('onboarding-coachmark-highlight')).toBeVisible();
    } else {
        await expect(page.getByTestId('onboarding-coachmark-highlight')).toHaveCount(0);
    }
    if (options.backdrop) {
        await expect(page.getByTestId('onboarding-spotlight-top')).toHaveCount(1);
    } else {
        await expect(page.getByTestId('onboarding-spotlight-top')).toHaveCount(0);
        await expect(page.getByTestId('onboarding-coachmark-backdrop')).toHaveCount(0);
    }

    return {coachmark, target};
}

async function expectPulseContainsTarget(page: Page, target: Locator): Promise<void> {
    const [highlight, targetBox] = await Promise.all([page.getByTestId('onboarding-coachmark-highlight').boundingBox(), target.boundingBox()]);
    if (!highlight || !targetBox) throw new Error('Transactions overview pulse or target has no bounding box');
    expect(highlight.x).toBeLessThanOrEqual(targetBox.x + 2);
    expect(highlight.y).toBeLessThanOrEqual(targetBox.y + 2);
    expect(highlight.x + highlight.width).toBeGreaterThanOrEqual(targetBox.x + targetBox.width - 2);
    expect(highlight.y + highlight.height).toBeGreaterThanOrEqual(targetBox.y + targetBox.height - 2);
}

async function goToOwnedTransaction(page: Page, owned: OwnedTransaction): Promise<Locator> {
    await navigateTo(page, `/transactions?page_size=25&id_min=${owned.transactionId}&id_max=${owned.transactionId}`);
    const pageRoot = page.getByTestId('transactions-page');
    await expect(pageRoot).toBeVisible({timeout: 15_000});
    await waitForSettled(pageRoot, 20_000);
    const table = page.getByTestId('tx-table');
    await expect(table).toBeVisible({timeout: 10_000});
    const row = table.locator(`tbody tr[data-row-id="${owned.rowId}"]`).filter({hasText: owned.marker});
    await expect(row, `Owned transaction ${owned.transactionId} must be the only id-filtered row`).toHaveCount(1, {timeout: 10_000});
    await expect(row).toBeVisible();
    return row;
}

async function openBulkOnOwnedTransaction(page: Page, owned: OwnedTransaction): Promise<{bulk: Locator; form: Locator}> {
    const row = await goToOwnedTransaction(page, owned);
    const checkbox = row.getByTestId(`dt-row-checkbox-${owned.rowId}`);
    await expect(checkbox).toBeEnabled();
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    await expect(page.getByTestId('toolbar-action-edit')).toBeEnabled({timeout: 5_000});
    await page.getByTestId('toolbar-action-edit').click();

    const bulk = page.getByTestId('tx-bulk-modal-root');
    const form = page.getByTestId('tx-form-modal');
    await expect(bulk).toBeVisible({timeout: 10_000});
    await expect(form).toBeVisible({timeout: 10_000});
    return {bulk, form};
}

async function stageDescriptionEdit(form: Locator): Promise<void> {
    const description = form.getByTestId('tx-form-description');
    await expect(description).toBeHidden();
    await form.getByTestId('tx-form-optional-toggle').click();
    await expect(description).toBeVisible();
    const marker = `onboarding-draft-${uniqueSuffix()}`;
    await description.fill(marker);
    await expect(description).toHaveValue(marker);
    await expect(form.getByTestId('tx-form-save')).toBeEnabled({timeout: 5_000});
    await form.getByTestId('tx-form-save').click();
    await expect(form).toBeHidden({timeout: 10_000});
}

async function installImportScrollObservation(page: Page): Promise<void> {
    await page.evaluate(() => {
        const host = window as Round5Window;
        if (host.__lfRound5ImportScroll) throw new Error('Round 5 Import scroll observation is already installed');

        const state: ImportScrollState = {
            initialWindowY: window.scrollY,
            initialWizardScrollTop: null,
            windowEvents: [],
            wizardScrollEvents: [],
            scrollIntoViewTargets: [],
        };
        const captureInitialWizardScroll = () => {
            if (state.initialWizardScrollTop !== null) return;
            const content = document.querySelector<HTMLElement>('[data-testid="import-wizard-content"]');
            if (content) state.initialWizardScrollTop = content.scrollTop;
        };
        const onWindowScroll = () => state.windowEvents.push(window.scrollY);
        const onElementScroll = (event: Event) => {
            const target = event.target;
            if (target instanceof HTMLElement && target.dataset.testid === 'import-wizard-content') {
                state.wizardScrollEvents.push(target.scrollTop);
            }
        };
        const observer = new MutationObserver(captureInitialWizardScroll);
        captureInitialWizardScroll();
        observer.observe(document.documentElement, {childList: true, subtree: true});
        const originalScrollIntoView = Element.prototype.scrollIntoView;
        Element.prototype.scrollIntoView = function (this: Element, arg?: boolean | ScrollIntoViewOptions): void {
            const element = this as HTMLElement;
            state.scrollIntoViewTargets.push(element.dataset.testid ?? element.id ?? element.tagName.toLowerCase());
            Reflect.apply(originalScrollIntoView, this, arg === undefined ? [] : [arg]);
        };
        window.addEventListener('scroll', onWindowScroll, {passive: true});
        document.addEventListener('scroll', onElementScroll, true);
        host.__lfRound5ImportScroll = {
            state,
            originalScrollIntoView,
            onWindowScroll,
            onElementScroll,
            observer,
        };
    });
}

async function readImportScrollObservation(page: Page): Promise<ImportScrollState & {currentWindowY: number; currentWizardScrollTop: number | null}> {
    return page.evaluate(() => {
        const harness = (window as Round5Window).__lfRound5ImportScroll;
        if (!harness) throw new Error('Round 5 Import scroll observation was not installed');
        const content = document.querySelector<HTMLElement>('[data-testid="import-wizard-content"]');
        return {
            initialWindowY: harness.state.initialWindowY,
            initialWizardScrollTop: harness.state.initialWizardScrollTop,
            windowEvents: [...harness.state.windowEvents],
            wizardScrollEvents: [...harness.state.wizardScrollEvents],
            scrollIntoViewTargets: [...harness.state.scrollIntoViewTargets],
            currentWindowY: window.scrollY,
            currentWizardScrollTop: content?.scrollTop ?? null,
        };
    });
}

async function resetImportScrollObservation(page: Page): Promise<void> {
    await page.evaluate(() => {
        const harness = (window as Round5Window).__lfRound5ImportScroll;
        if (!harness) throw new Error('Round 5 Import scroll observation was not installed');
        const content = document.querySelector<HTMLElement>('[data-testid="import-wizard-content"]');
        if (!content) throw new Error('Import wizard content was not mounted before the observation reset');
        harness.state.initialWindowY = window.scrollY;
        harness.state.initialWizardScrollTop = content.scrollTop;
        harness.state.windowEvents = [];
        harness.state.wizardScrollEvents = [];
        harness.state.scrollIntoViewTargets = [];
    });
}

async function restoreImportScrollObservation(page: Page): Promise<void> {
    await page.evaluate(() => {
        const host = window as Round5Window;
        const harness = host.__lfRound5ImportScroll;
        if (!harness) return;
        Element.prototype.scrollIntoView = harness.originalScrollIntoView;
        window.removeEventListener('scroll', harness.onWindowScroll);
        document.removeEventListener('scroll', harness.onElementScroll, true);
        harness.observer.disconnect();
        delete host.__lfRound5ImportScroll;
    });
}

function importCsv(marker: string): {name: string; mimeType: string; buffer: Buffer} {
    const body = 'date,type,quantity,amount,currency,asset,description\n' + `2025-03-01,DEPOSIT,0,100.00,EUR,,Round 5 ${marker}\n`;
    return {
        name: `onboarding-${marker}.csv`,
        mimeType: 'text/csv',
        buffer: Buffer.from(body),
    };
}

async function reachImportAnalyze(page: Page, brokerName: string, ownedFileIds: string[]): Promise<void> {
    const file = importCsv(uniqueSuffix());
    const step1 = page.getByTestId('import-wizard-step1');
    const input = step1.getByTestId('file-input');
    await input.setInputFiles(file);
    const pendingRow = step1.locator('tbody tr[data-row-id]');
    await expect(pendingRow, 'The fresh wizard must contain exactly the one file this test selected').toHaveCount(1);
    await expect(pendingRow.locator('input'), `Owned upload ${file.name} must be the pending filename`).toHaveValue(file.name);

    const brokerWrapper = page.getByTestId('import-wizard-step1-broker-select');
    const brokerSelect = brokerWrapper.getByRole('combobox');
    await brokerSelect.focus();
    await expect(brokerSelect).toBeFocused();
    await brokerSelect.press('Enter');
    const brokerSearch = brokerWrapper.getByRole('textbox');
    await expect(brokerSearch).toBeFocused();
    await brokerSearch.fill(brokerName);
    const brokerOption = page.locator('[data-testid^="search-select-option-"]').filter({hasText: brokerName});
    await expect(brokerOption, `Owned broker ${brokerName} must be the unique matching option`).toHaveCount(1, {
        timeout: 8_000,
    });
    await expect(brokerOption).toHaveAttribute('data-highlighted', 'true');
    await brokerSearch.press('Enter');
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 8_000});

    const uploadResponsePromise = page.waitForResponse((response) => {
        const request = response.request();
        return request.method() === 'POST' && new URL(response.url()).pathname === '/api/v1/brokers/import/upload';
    });
    await expect(page.getByTestId('import-wizard-next')).toBeEnabled({timeout: 5_000});
    await page.getByTestId('import-wizard-next').click();
    const uploadResponse = await uploadResponsePromise;
    expect(uploadResponse.ok(), `Owned upload ${file.name} failed with HTTP ${uploadResponse.status()}`).toBe(true);
    const uploaded = (await uploadResponse.json()) as {file_id?: string};
    if (!uploaded.file_id) throw new Error(`Owned upload ${file.name} returned no file_id`);
    ownedFileIds.push(uploaded.file_id);

    const step2 = page.getByTestId('import-wizard-step2');
    await expect(step2).toBeVisible({timeout: 10_000});
    await waitForSettled(step2, 20_000);
    const fileRow = step2.locator('tr[data-row-id]').filter({hasText: file.name});
    await expect(fileRow, `Owned upload ${file.name} must appear exactly once`).toHaveCount(1);
    const checkbox = fileRow.locator('button[data-state]');
    await expect(checkbox, `Owned upload ${file.name} must expose one selection control`).toHaveCount(1);
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    await expect(page.getByTestId('import-wizard-parse')).toBeEnabled({timeout: 5_000});

    await resetImportScrollObservation(page);
    await page.getByTestId('import-wizard-parse').click();
    await expect(page.getByTestId('import-wizard-step3')).toBeVisible({timeout: 10_000});
    await waitForParseVerdict(page);
}

test.describe('Onboarding Round 5', () => {
    test('Global Asset Abs/% propagates to every rendered card on desktop/mobile', async ({page}) => {
        await page.route('**/api/v1/assets/query*', async (route) => {
            await route.fulfill({
                json: [
                    {
                        id: 910_001,
                        display_name: 'Synthetic propagation asset A',
                        currency: 'EUR',
                        asset_type: 'STOCK',
                        active: true,
                        has_metadata: false,
                        provider_code: null,
                        tx_count: 1,
                        tx_count_own: 1,
                    },
                    {
                        id: 910_002,
                        display_name: 'Synthetic propagation asset B',
                        currency: 'EUR',
                        asset_type: 'STOCK',
                        active: true,
                        has_metadata: false,
                        provider_code: null,
                        tx_count: 0,
                        tx_count_own: 0,
                    },
                ],
            });
        });
        await page.route('**/api/v1/assets/prices/query', async (route) => {
            const requested = (route.request().postDataJSON() as Array<{asset_id: number}> | null) ?? [];
            await route.fulfill({
                json: {
                    items: requested.map(({asset_id}) => ({
                        asset_id,
                        prices: [],
                        events: [],
                        errors: [],
                        signals: [],
                    })),
                },
            });
        });
        await page.route('**/api/v1/assets/prices/current', async (route) => {
            await route.fulfill({json: {results: [], success_count: 0, errors: []}});
        });

        await login(page);
        await navigateTo(page, '/assets');

        const absoluteToggle = page.getByTestId('assets-global-view-absolute');
        const percentageToggle = page.getByTestId('assets-global-view-percentage');
        await expect(absoluteToggle).toBeVisible({timeout: 15_000});
        await expect(percentageToggle).toBeVisible({timeout: 15_000});

        const cards = page.getByTestId(/^asset-card-\d+$/);
        const everyRenderedCardUses = (mode: 'absolute' | 'percentage') => cards.evaluateAll((nodes, expected) => nodes.length > 0 && nodes.every((node) => (node as HTMLElement).dataset.viewMode === expected), mode);

        await expect.poll(() => everyRenderedCardUses('percentage'), {timeout: 10_000}).toBe(true);
        await absoluteToggle.click();
        await expect.poll(() => everyRenderedCardUses('absolute'), {timeout: 5_000}).toBe(true);
        await percentageToggle.click();
        await expect.poll(() => everyRenderedCardUses('percentage'), {timeout: 5_000}).toBe(true);
    });

    test('Core order and Transactions overview preserve geometry on desktop/mobile', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, `core_${testInfo.project.name}`);
        const financialWrites: string[] = [];
        const completionRequests: Array<Record<string, unknown>> = [];
        const recordWrites = (requestEvent: Request) => {
            if (requestEvent.method() !== 'POST') return;
            const path = new URL(requestEvent.url()).pathname;
            if (['/api/v1/brokers', '/api/v1/assets', '/api/v1/fx/providers/routes', '/api/v1/transactions/commit'].includes(path)) {
                financialWrites.push(path);
            }
            if (path === '/api/v1/settings/onboarding/intro_tour/complete') {
                completionRequests.push(requestEvent.postDataJSON());
            }
        };
        page.on('request', recordWrites);

        try {
            await login(page, user);
            await completeWelcome(page);

            const progressResponse = await page.request.get('/api/v1/settings/onboarding');
            expect(progressResponse.ok()).toBe(true);
            const progress = (await progressResponse.json()) as {
                flows: Array<{flow: string; steps?: Array<{step_id: string}>}>;
            };
            expect(progress.flows).toHaveLength(15);
            expect(progress.flows.find((flow) => flow.flow === 'import_guide')?.steps?.map((step) => step.step_id)).toEqual(['import.upload', 'import.select', 'import.analyze', 'import.assets', 'import.fix', 'import.duplicates', 'import.review', 'import.bulk']);
            expect(progress.flows.find((flow) => flow.flow === 'transaction_bulk_guide')?.steps?.map((step) => step.step_id)).toEqual(BULK_STEPS);
            await expect(page.getByTestId('dashboard-page')).toBeVisible();

            const observed: string[] = ['intro.scene'];
            await expect(page.getByTestId('onboarding-coachmark-pointer')).toHaveCount(0);
            await page.getByTestId('onboarding-intro-start').click();

            const mobile = testInfo.project.name === 'mobile';
            const steps = [
                {stepId: 'intro.navigation', targetId: mobile ? 'mobile-menu-toggle' : 'sidebar-collapse-toggle'},
                {stepId: 'intro.dashboard', targetId: 'nav-dashboard'},
                {stepId: 'intro.transactions_nav', targetId: 'nav-transactions'},
                {stepId: 'intro.brokers_nav', targetId: 'nav-brokers'},
                {stepId: 'intro.fx_nav', targetId: 'nav-fx'},
                {stepId: 'intro.assets_nav', targetId: 'nav-assets'},
                {stepId: 'intro.tools_nav', targetId: 'nav-tools'},
                {stepId: 'intro.settings_nav', targetId: 'nav-settings'},
            ] as const;

            for (const [index, step] of steps.entries()) {
                if (index > 0) await page.getByTestId('onboarding-coachmark-next').click();
                await expect(page).toHaveURL(/\/dashboard(?:[/?#]|$)/);
                if (mobile && index > 0) {
                    await expect(page.getByTestId('app-header')).toHaveAttribute('data-sidebar-open', 'true', {timeout: 10_000});
                }
                const target = page.getByTestId(step.targetId);
                const expectedPlacement = !mobile ? 'right' : step.stepId === 'intro.fx_nav' ? 'bottom' : step.stepId === 'intro.settings_nav' ? 'top' : undefined;
                await expectGuideStep(page, {
                    stepId: step.stepId,
                    target,
                    pointer: 'cursor',
                    highlight: 'pulse',
                    backdrop: true,
                    placement: expectedPlacement,
                });
                await expect(page.getByTestId('onboarding-coachmark-action-hint')).toHaveCount(0);
                await expect(page.getByTestId('app-shell')).toHaveAttribute('data-guide-inert', 'true');
                if (step.stepId === 'intro.dashboard') {
                    await expect(page.getByTestId('sync-button')).not.toHaveAttribute('aria-describedby', DESCRIPTION_ID);
                }
                observed.push(step.stepId);
            }

            expect(observed).toEqual(CORE_ORDER);
            await page.getByTestId('onboarding-coachmark-next').click();
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0, {timeout: 10_000});
            await expect(page.getByTestId('app-shell')).toHaveAttribute('data-guide-inert', 'false');
            expect(completionRequests).toHaveLength(1);
            expect(Object.keys(completionRequests.at(0) ?? {}).sort()).toEqual(['expected_version']);

            if (mobile) {
                await page.getByTestId('mobile-menu-toggle').click();
                await expect(page.getByTestId('app-header')).toHaveAttribute('data-sidebar-open', 'true');
            }
            await page.getByTestId('nav-transactions').click();
            await expect(page).toHaveURL(/\/transactions(?:[/?#]|$)/, {timeout: 15_000});
            const transactionsPage = page.getByTestId('transactions-page');
            await expect(transactionsPage).toBeVisible({timeout: 15_000});
            await waitForSettled(transactionsPage, 20_000);

            const overviewTarget = page.getByTestId('transactions-page-overview-guide-target');
            await expectGuideStep(page, {
                stepId: 'transactions.page.overview',
                target: overviewTarget,
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
                placement: 'bottom',
            });
            await expectPulseContainsTarget(page, overviewTarget);
            await expect(page.getByTestId('app-shell')).toHaveAttribute('data-guide-inert', 'false');
            await expect(page.getByTestId('tx-add-button')).toBeEnabled();

            await page.getByTestId('onboarding-coachmark-next').click();
            const addTarget = page.getByTestId('tx-add-button');
            await expectGuideStep(page, {
                stepId: 'transactions.page.add',
                target: addTarget,
                pointer: 'cursor',
                highlight: 'none',
                backdrop: false,
            });
            await expect(page.getByTestId('onboarding-coachmark-action-hint')).toBeVisible();

            await addTarget.click();

            const bulk = page.getByTestId('tx-bulk-modal-root');
            const form = page.getByTestId('tx-form-modal');
            await expect(bulk).toBeVisible({timeout: 10_000});
            await expect(form).toBeVisible({timeout: 10_000});
            for (const [index, guideStep] of TRANSACTION_FORM_GUIDE_STEPS.entries()) {
                if (index > 0) await page.getByTestId('onboarding-coachmark-next').click();
                const target = form.getByTestId(guideStep.targetId);
                const {coachmark} = await expectGuideStep(page, {
                    stepId: guideStep.stepId,
                    target,
                    pointer: guideStep.pointer,
                    highlight: guideStep.highlight,
                    placement: 'placement' in guideStep ? guideStep.placement : undefined,
                    allowTargetOverlap: 'allowTargetOverlap' in guideStep ? guideStep.allowTargetOverlap : undefined,
                });
                await expect(coachmark).toHaveAttribute('aria-hidden', 'false');
                await expect(coachmark).toBeVisible();
                await expect(addTarget).not.toHaveAttribute('aria-describedby', DESCRIPTION_ID);

                const sample = await sampleTransactionFormTargets(form);
                for (const candidate of sample) {
                    expect(candidate.describedBy, `${guideStep.stepId} must describe only ${guideStep.targetId}`).toBe(candidate.testId === guideStep.targetId ? DESCRIPTION_ID : null);
                }
                if (index === 0) {
                    const signatures = new Set(sample.map(({rect}) => [rect.x, rect.y, rect.width, rect.height].map((value) => value.toFixed(2)).join(':')));
                    expect(signatures.size, 'The four semantic form anchors must expose distinct rectangles').toBe(4);
                    const basics = sample.find(({testId}) => testId === 'tx-form-type-wrap');
                    const amounts = sample.find(({testId}) => testId === 'tx-form-required');
                    if (!basics || !amounts) throw new Error('The atomic form geometry sample omitted basics or amounts');
                    expect(basics.rect.x).toBeGreaterThanOrEqual(amounts.rect.x);
                    expect(basics.rect.y).toBeGreaterThanOrEqual(amounts.rect.y);
                    expect(basics.rect.x + basics.rect.width).toBeLessThanOrEqual(amounts.rect.x + amounts.rect.width);
                    expect(basics.rect.y + basics.rect.height).toBeLessThanOrEqual(amounts.rect.y + amounts.rect.height);
                }
            }
            await page.getByTestId('onboarding-coachmark-next').click();
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0, {timeout: 10_000});

            await form.getByTestId('tx-form-close').click();
            await expect(form).toBeHidden({timeout: 10_000});
            const {coachmark: bulkCoachmark} = await expectGuideStep(page, {
                stepId: 'transaction.bulk.workspace',
                target: bulk.getByTestId('tx-bulk-title'),
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            });
            await expect(bulkCoachmark).toHaveAttribute('aria-hidden', 'false');
            await expect(bulkCoachmark).toBeVisible();
            await expect(page.getByTestId('onboarding-coachmark-progress')).toHaveCount(0);
            await expect(page.getByTestId('onboarding-coachmark-back')).toHaveCount(0);
            await expect(page.getByTestId('onboarding-coachmark-next').locator('svg')).toHaveCount(0);

            await page.getByTestId('onboarding-coachmark-close').click();
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0, {timeout: 10_000});
            expect(financialWrites, 'Onboarding may persist only its own progress, never financial data').toEqual([]);
        } finally {
            page.off('request', recordWrites);
            await deleteDisposableUser(request, user);
        }
    });

    test('Broker views preserves scroll and header-obscured Add receives only its precise clearance scroll on desktop/mobile', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, `broker_scroll_${testInfo.project.name}`);
        let brokerScrollObservationInstalled = false;
        try {
            await page.emulateMedia({reducedMotion: 'reduce'});
            await login(page, user);
            await completeWelcome(page);
            await page.getByTestId('onboarding-intro-close').click();
            await expect(page.getByTestId('onboarding-intro-scene')).toHaveCount(0, {timeout: 10_000});

            await navigateTo(page, '/brokers');
            const brokersPage = page.getByTestId('brokers-page');
            await expect(brokersPage).toBeVisible({timeout: 15_000});
            await waitForSettled(brokersPage, 20_000);

            await expectGuideStep(page, {
                stepId: 'broker.page.overview',
                target: page.getByTestId('broker-page-overview-guide-target'),
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            });
            const reducedMotionPanel = await page.getByTestId('onboarding-coachmark-panel').evaluate((element) => {
                const style = getComputedStyle(element);
                return {transitionProperty: style.transitionProperty, subdued: element.dataset.subdued};
            });
            expect(reducedMotionPanel.transitionProperty, 'Reduced motion must remove only the panel transition').toBe('none');
            expect(reducedMotionPanel.subdued, 'Reduced motion must leave the fresh/subdued state machine active').toBe('false');
            await page.getByTestId('onboarding-coachmark-next').click();
            await expectGuideStep(page, {
                stepId: 'broker.page.currency',
                target: page.getByTestId('broker-page-currency'),
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            });

            const beforeViews = await sampleBrokerGeometry(page);
            await page.getByTestId('onboarding-coachmark-next').click();
            await expectGuideStep(page, {
                stepId: 'broker.page.views',
                target: page.getByTestId('broker-page-views'),
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
                allowTargetOverlap: true,
            });
            const atViews = await sampleBrokerGeometry(page);
            expect(atViews.scrollY, 'Activating Broker step 3 must not change window.scrollY').toBe(beforeViews.scrollY);

            const beforeAdd = await placeBrokerAddUnderHeader(page);
            const beforeAddHeaderBottom = beforeAdd.header.y + beforeAdd.header.height;
            expect(beforeAdd.add.y, 'Broker Add must start partially obscured by the sticky header').toBeLessThan(beforeAddHeaderBottom);
            expect(beforeAdd.add.y + beforeAdd.add.height, 'Broker Add must remain partially visible below the sticky header').toBeGreaterThan(beforeAddHeaderBottom);
            await installBrokerScrollObservation(page);
            brokerScrollObservationInstalled = true;

            await page.getByTestId('onboarding-coachmark-next').click();
            await expect
                .poll(async () => (await sampleBrokerGeometry(page)).scrollByCalls.length, {
                    timeout: 10_000,
                    message: 'Broker Add activation never requested sticky-header clearance',
                })
                .toBe(1);
            await expectGuideStep(page, {
                stepId: 'broker.page.add',
                target: page.getByTestId('add-broker-button'),
                pointer: 'cursor',
                highlight: 'none',
                backdrop: false,
            });
            const atAdd = await sampleBrokerGeometry(page);
            const safeHeaderBottom = beforeAddHeaderBottom + 8;
            const expectedScrollTop = beforeAdd.add.y - safeHeaderBottom;
            expect(expectedScrollTop, 'The forced Broker Add precondition must require an upward clearance scroll').toBeLessThan(0);
            expect(atAdd.scrollByCalls).toHaveLength(1);
            expect(atAdd.scrollByCalls[0].top).toBeCloseTo(expectedScrollTop, 5);
            expect(atAdd.scrollByCalls[0].left).toBe(0);
            expect(atAdd.scrollByCalls[0].behavior).toBe('auto');
            expect(atAdd.scrollIntoViewTargets, 'A partially visible header-obscured Add must not use scrollIntoView').toEqual([]);
            expect(atAdd.scrollY).toBeCloseTo(beforeAdd.scrollY + expectedScrollTop, 0);
            expect(atAdd.add.y, 'Add must receive exactly the sticky-header clearance plus its 8px safety gap').toBeCloseTo(atAdd.header.y + atAdd.header.height + 8, 0);
            expect(atAdd.add.y + atAdd.add.height, 'Add must remain fully inside the viewport').toBeLessThanOrEqual(atAdd.viewportHeight);

            await restoreBrokerScrollObservation(page);
            brokerScrollObservationInstalled = false;
            await page.getByTestId('onboarding-coachmark-close').click();
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0, {timeout: 10_000});
        } finally {
            if (brokerScrollObservationInstalled) await restoreBrokerScrollObservation(page);
            await deleteDisposableUser(request, user);
        }
    });

    test('Import preempts real Bulk milestones and resumes overview → validation → selection → save', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, `bulk_${testInfo.project.name}`);
        const ownedBrokerIds: number[] = [];
        const ownedFileIds: string[] = [];
        const commitRequests: string[] = [];
        const bulkStepCompletions: string[] = [];
        const observedMilestones: string[] = [];
        const recordWrites = (requestEvent: Request) => {
            if (requestEvent.method() !== 'POST') return;
            const path = new URL(requestEvent.url()).pathname;
            if (path === '/api/v1/transactions/commit') commitRequests.push(path);
            const bulkStep = path.match(/^\/api\/v1\/settings\/onboarding\/transaction_bulk_guide\/steps\/([^/]+)\/complete$/);
            if (bulkStep) bulkStepCompletions.push(decodeURIComponent(bulkStep[1]));
        };
        const validationRoute = '**/api/v1/transactions/validate';
        let heldValidationRequest = false;
        let releasingValidationForCleanup = false;
        let releaseValidationRequest!: () => void;
        const validationGate = new Promise<void>((resolve) => {
            releaseValidationRequest = resolve;
        });
        let validationReleased = false;
        const releaseValidation = () => {
            if (validationReleased) return;
            validationReleased = true;
            releaseValidationRequest();
        };
        const holdValidation = async (route: {continue(): Promise<void>}) => {
            if (heldValidationRequest) {
                await route.continue();
                return;
            }
            heldValidationRequest = true;
            await validationGate;
            try {
                await route.continue();
            } catch (error) {
                if (releasingValidationForCleanup && error instanceof Error && error.message.includes('Route is already handled')) return;
                throw error;
            }
        };
        let validationRouteInstalled = false;
        let scrollObservationInstalled = false;

        try {
            await login(page, user);
            await prepareDisposableBulkAccount(page);
            const owned = await createOwnedTransaction(page, testInfo.project.name, ownedBrokerIds);

            page.on('request', recordWrites);
            await page.route(validationRoute, holdValidation);
            validationRouteInstalled = true;

            const {bulk, form} = await openBulkOnOwnedTransaction(page, owned);
            const commit = bulk.getByTestId('tx-bulk-commit');
            const validateRunsBefore = Number((await bulk.getAttribute('data-validate-runs')) ?? '0');
            expect(validateRunsBefore, 'A newly opened owned Bulk workspace must sample before its first validate run').toBe(0);

            // The selected-row edit opens a real nested TransactionFormModal.
            // Bulk owns the pending overview, but cannot present it until it is
            // the topmost modal.
            await expect(form).toBeVisible();
            await expect(commit).toBeDisabled();
            const suspendedCoachmark = page.getByTestId('onboarding-coachmark');
            await expect(suspendedCoachmark).toHaveCount(1);
            await expect(suspendedCoachmark).toHaveAttribute('data-step-id', 'transaction.bulk.workspace');
            await expect(suspendedCoachmark).toHaveAttribute('aria-hidden', 'true');
            await expect(suspendedCoachmark).toBeHidden();
            await expect(bulk).toHaveAttribute('data-busy', 'true', {timeout: 10_000});
            await expect(bulk).toHaveAttribute('data-validate-runs', String(validateRunsBefore));

            await form.getByTestId('tx-form-cancel').click();
            await expect(form).toBeHidden({timeout: 10_000});

            await expectGuideStep(page, {
                stepId: 'transaction.bulk.workspace',
                target: bulk.getByTestId('tx-bulk-title'),
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            });
            observedMilestones.push('transaction.bulk.workspace');

            const importButton = bulk.getByTestId('tx-bulk-import');
            await expect(importButton).toBeEnabled();
            await importButton.focus();
            await expect(importButton).toBeFocused();
            await installImportScrollObservation(page);
            scrollObservationInstalled = true;
            await importButton.press('Enter');
            await expect(page.getByTestId('import-wizard-step1')).toBeVisible({timeout: 10_000});
            await expectGuideStep(page, {
                stepId: 'import.upload',
                target: page.getByTestId('import-wizard-next'),
                pointer: 'cursor',
                highlight: 'none',
                backdrop: false,
                placement: 'top',
            });
            const scrollObservation = await readImportScrollObservation(page);
            expect(scrollObservation.scrollIntoViewTargets, 'First-mount Import activation must not call scrollIntoView').toEqual([]);
            expect(scrollObservation.windowEvents, 'First-mount Import activation must not emit a window scroll').toEqual([]);
            expect(scrollObservation.currentWindowY, 'First-mount Import activation must preserve window.scrollY').toBe(scrollObservation.initialWindowY);
            expect(scrollObservation.initialWizardScrollTop, 'Import content must mount at its unscrolled origin').toBe(0);
            expect(scrollObservation.wizardScrollEvents, 'First-mount Import activation must not scroll its content root').toEqual([]);
            expect(scrollObservation.currentWizardScrollTop, 'First-mount Import activation must preserve the content scrollTop').toBe(scrollObservation.initialWizardScrollTop);
            await expect(page.getByTestId('import-wizard-back')).toHaveCount(0);

            await reachImportAnalyze(page, owned.brokerName, ownedFileIds);
            await expectGuideStep(page, {
                stepId: 'import.analyze',
                target: page.getByTestId('import-wizard-continue'),
                pointer: 'cursor',
                highlight: 'none',
                backdrop: false,
                placement: 'top',
            });
            const analyzeScrollObservation = await readImportScrollObservation(page);
            expect(analyzeScrollObservation.scrollIntoViewTargets, 'Analyze activation must not call scrollIntoView').toEqual([]);
            expect(analyzeScrollObservation.windowEvents, 'Analyze activation must not emit a window scroll').toEqual([]);
            expect(analyzeScrollObservation.currentWindowY, 'Analyze activation must preserve window.scrollY').toBe(analyzeScrollObservation.initialWindowY);
            expect(analyzeScrollObservation.wizardScrollEvents, 'Analyze activation must not scroll its content root').toEqual([]);
            expect(analyzeScrollObservation.currentWizardScrollTop, 'Analyze activation must preserve the content scrollTop').toBe(analyzeScrollObservation.initialWizardScrollTop);
            const scrollSnapshot = await page.getByTestId('import-wizard-content').evaluate((element) => {
                element.dispatchEvent(new Event('scroll'));
                const coachmark = document.querySelector<HTMLElement>('[data-testid="onboarding-coachmark"]');
                return {
                    guideState: coachmark?.dataset.guideState,
                    geometryState: coachmark?.dataset.geometryState,
                    targetStable: coachmark?.dataset.targetStable,
                };
            });
            expect(scrollSnapshot.guideState).toBe('anchored');
            expect(scrollSnapshot.targetStable).toBe('true');
            expect(scrollSnapshot.geometryState).toMatch(/^(revalidating|stable)$/);
            await expect(page.getByTestId('onboarding-coachmark')).toHaveAttribute('data-geometry-state', 'stable');
            await restoreImportScrollObservation(page);
            scrollObservationInstalled = false;

            await page.getByTestId('import-wizard-close').click();
            await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: 5_000});
            await page.getByTestId('confirm-modal-confirm').click();
            await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 10_000});
            await expectGuideStep(page, {
                stepId: 'transaction.bulk.workspace',
                target: bulk.getByTestId('tx-bulk-title'),
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            });

            // The overview completes while the first real Bulk validation call
            // is deliberately still in flight. Neither "request started" nor
            // a stale counter may unlock the validation milestone.
            await page.getByTestId('onboarding-coachmark-next').click();
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0, {timeout: 10_000});
            await expect(bulk).toHaveAttribute('data-busy', 'true');
            await expect(bulk).toHaveAttribute('data-validate-runs', String(validateRunsBefore));

            releaseValidation();
            await expect.poll(async () => Number((await bulk.getAttribute('data-validate-runs')) ?? '0'), {timeout: 20_000}).toBeGreaterThan(validateRunsBefore);
            await expect(bulk).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            const {target: validationTarget} = await expectGuideStep(page, {
                stepId: 'transaction.bulk.validation',
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            });
            await expect(validationTarget.getByTestId('tx-bulk-validate-now')).toBeVisible();
            observedMilestones.push('transaction.bulk.validation');

            await page.getByTestId('onboarding-coachmark-next').click();
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0, {timeout: 10_000});

            const selectAll = bulk.getByTestId('dt-select-all');
            await expect(selectAll).toHaveAttribute('data-state', 'unchecked');
            // The mobile coachmark can cover the header coordinates. Use the
            // checkbox's keyboard contract instead of bypassing actionability.
            await selectAll.focus();
            await expect(selectAll).toBeFocused();
            await selectAll.press('Space');
            await expect(selectAll).toHaveAttribute('data-state', 'checked');
            const {target: selectionTarget} = await expectGuideStep(page, {
                stepId: 'transaction.bulk.selection',
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            });
            observedMilestones.push('transaction.bulk.selection');

            // Emptying the first real selection removes both its conditional
            // toolbar and the milestone anchored to that toolbar.
            await selectAll.press('Space');
            await expect(selectAll).toHaveAttribute('data-state', 'unchecked');
            await expect(selectionTarget).toHaveCount(0, {timeout: 10_000});
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);

            // Re-enter the same verified state and complete the milestone so
            // save can be observed after it in the approved priority order.
            await selectAll.press('Space');
            await expect(selectAll).toHaveAttribute('data-state', 'checked');
            await expectGuideStep(page, {
                stepId: 'transaction.bulk.selection',
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            });
            await page.getByTestId('onboarding-coachmark-next').click();
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0, {timeout: 10_000});
            await selectAll.press('Space');
            await expect(selectAll).toHaveAttribute('data-state', 'unchecked');

            const ownedDraftRow = bulk.locator('tbody tr[data-row-id]').filter({hasText: owned.marker});
            await expect(ownedDraftRow, 'Bulk must contain exactly the transaction owned by this disposable account').toHaveCount(1);
            await ownedDraftRow.dblclick();
            await expect(form).toBeVisible({timeout: 10_000});
            await expect(form.getByTestId('tx-form-save')).toBeEnabled({timeout: 5_000});
            await form.getByTestId('tx-form-save').click();
            await expect(form).toBeHidden({timeout: 10_000});
            await expect(commit, 'An unchanged draft is not commit-ready').toBeDisabled({timeout: 10_000});
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);
            await ownedDraftRow.dblclick();
            await expect(form).toBeVisible({timeout: 10_000});
            await stageDescriptionEdit(form);
            await expect(commit, 'The edited owned draft must become commit-ready').toBeEnabled({timeout: 10_000});
            await expectGuideStep(page, {
                stepId: 'transaction.bulk.save',
                target: commit,
                pointer: 'cursor',
                highlight: 'none',
                backdrop: false,
                placement: 'top',
            });
            observedMilestones.push('transaction.bulk.save');
            await page.getByTestId('onboarding-coachmark-next').click();
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0, {timeout: 10_000});
            expect(observedMilestones).toEqual(['transaction.bulk.workspace', 'transaction.bulk.validation', 'transaction.bulk.selection', 'transaction.bulk.save']);
            expect(bulkStepCompletions).toEqual(BULK_STEPS);

            await bulk.getByTestId('tx-bulk-close').click();
            await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: 5_000});
            await page.getByTestId('confirm-modal-confirm').click();
            await expect(bulk).toHaveCount(0, {timeout: 10_000});
            expect(commitRequests, 'The entire Bulk milestone walk must discard its draft without committing').toEqual([]);
        } finally {
            releasingValidationForCleanup = true;
            releaseValidation();
            if (scrollObservationInstalled) await restoreImportScrollObservation(page);
            if (validationRouteInstalled) await page.unroute(validationRoute, holdValidation);
            page.off('request', recordWrites);
            await deleteDisposableUser(request, user, ownedBrokerIds, ownedFileIds);
        }
    });

    test('Bulk selection stays due across host cleanup, then X skips only that current step', async ({page, request}, testInfo) => {
        const user = await registerDisposableUser(request, `selection_${testInfo.project.name}`);
        const ownedBrokerIds: number[] = [];
        try {
            await login(page, user);
            await prepareDisposableBulkAccount(page, ['import_guide']);
            await skipOwnedSteps(
                page,
                'transaction_bulk_guide',
                BULK_STEPS.filter((stepId) => stepId !== 'transaction.bulk.selection'),
            );
            await page.reload();
            await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: 15_000});
            const owned = await createOwnedTransaction(page, `selection-${testInfo.project.name}`, ownedBrokerIds);
            const firstOpen = await openBulkOnOwnedTransaction(page, owned);

            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);
            await firstOpen.form.getByTestId('tx-form-cancel').click();
            await expect(firstOpen.form).toBeHidden({timeout: 10_000});
            const selectAll = firstOpen.bulk.getByTestId('dt-select-all');
            await expect(selectAll).toHaveAttribute('data-state', 'unchecked');
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);

            await selectAll.focus();
            await expect(selectAll).toBeFocused();
            await selectAll.press('Space');
            await expect(selectAll).toHaveAttribute('data-state', 'checked');
            const {target: selectionTarget} = await expectGuideStep(page, {
                stepId: 'transaction.bulk.selection',
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            });

            await selectAll.press('Space');
            await expect(selectAll).toHaveAttribute('data-state', 'unchecked');
            await expect(selectionTarget).toHaveCount(0, {timeout: 10_000});
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);

            await firstOpen.bulk.getByTestId('tx-bulk-close').click();
            await expect(firstOpen.bulk).toHaveCount(0, {timeout: 10_000});

            const secondOpen = await openBulkOnOwnedTransaction(page, owned);
            await secondOpen.form.getByTestId('tx-form-cancel').click();
            await expect(secondOpen.form).toBeHidden({timeout: 10_000});
            const reopenedSelectAll = secondOpen.bulk.getByTestId('dt-select-all');
            await expect(reopenedSelectAll).toHaveAttribute('data-state', 'unchecked');
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);

            await reopenedSelectAll.focus();
            await expect(reopenedSelectAll).toBeFocused();
            await reopenedSelectAll.press('Space');
            await expect(reopenedSelectAll).toHaveAttribute('data-state', 'checked');
            await expectGuideStep(page, {
                stepId: 'transaction.bulk.selection',
                pointer: 'none',
                highlight: 'pulse',
                backdrop: false,
            });
            const skippedStepResponse = page.waitForResponse((response) => {
                const path = new URL(response.url()).pathname;
                return response.request().method() === 'POST' && path === '/api/v1/settings/onboarding/transaction_bulk_guide/steps/transaction.bulk.selection/skip';
            });
            await page.getByTestId('onboarding-coachmark-close').click();
            const skippedStep = await skippedStepResponse;
            expect(skippedStep.ok()).toBe(true);
            const aggregate = (await skippedStep.json()) as {
                status: string;
                steps: Array<{step_id: string; status: string}>;
            };
            expect(aggregate.status).toBe('skipped');
            expect(aggregate.steps.find((step) => step.step_id === 'transaction.bulk.selection')?.status).toBe('skipped');
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0, {timeout: 10_000});

            await reopenedSelectAll.press('Space');
            await expect(reopenedSelectAll).toHaveAttribute('data-state', 'unchecked');
            await reopenedSelectAll.press('Space');
            await expect(reopenedSelectAll).toHaveAttribute('data-state', 'checked');
            await expect(page.getByTestId('onboarding-coachmark')).toHaveCount(0);

            await secondOpen.bulk.getByTestId('tx-bulk-close').click();
            await expect(secondOpen.bulk).toHaveCount(0, {timeout: 10_000});
        } finally {
            await deleteDisposableUser(request, user, ownedBrokerIds);
        }
    });
});
