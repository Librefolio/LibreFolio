import {expect, type Locator, type Page, type Request, type Response} from '../fixtures/playwright';

import {login, navigateTo, setLanguage} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

export const UI_TIMEOUT = 8_000;
export const API_TIMEOUT = 30_000;

export type AiExportSelectionKind = 'dataset' | 'analysis';
export type AiExportDetailLevel = 'compact' | 'standard' | 'full';
export type AiExportPeriodUnit = 'days' | 'weeks' | 'months' | 'years';

export interface AiExportPanel {
    readonly trigger: Locator;
    readonly menu: Locator;
    readonly options: Locator;
}

export interface AiExportResult {
    readonly request: Request;
    readonly response: Response;
    readonly payload: Record<string, unknown>;
}

export async function setupAiExportPage(page: Page): Promise<void> {
    await login(page, TEST_USER);
    await setLanguage(page, 'en');
}

export function isSnapshotPost(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/ai-export/snapshot';
}

export async function openAiExportPanel(page: Page): Promise<AiExportPanel> {
    const trigger = page.getByTestId('ai-export-button');
    await expect(trigger).toBeVisible({timeout: UI_TIMEOUT});
    await expect(trigger).toBeEnabled({timeout: UI_TIMEOUT});
    await trigger.click();

    const menu = page.getByTestId('ai-export-menu-panel');
    const options = page.getByTestId('ai-export-options-panel');
    await expect(menu).toBeVisible({timeout: 3_000});
    await expect(options).toBeVisible({timeout: 3_000});
    return {trigger, menu, options};
}

export async function selectAiExportSelection(page: Page, kind: AiExportSelectionKind, id: string): Promise<void> {
    const category = page.getByTestId(`ai-export-category-${kind}`);
    await category.click();
    await expect(category).toHaveAttribute('aria-pressed', 'true', {timeout: 2_000});

    const selectionButton = page.getByTestId('ai-export-selection-button');
    await selectionButton.click();
    const option = page.getByTestId(`ai-export-selection-option-${id}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await expect(selectionButton).toHaveAttribute('aria-expanded', 'false', {timeout: 2_000});
}

export async function readVisibleSelectionIds(page: Page): Promise<string[]> {
    const selectionButton = page.getByTestId('ai-export-selection-button');
    await selectionButton.click();
    await expect(selectionButton).toHaveAttribute('aria-expanded', 'true', {timeout: 2_000});

    const ids = await page.getByTestId(/^ai-export-selection-option-/).evaluateAll((elements) =>
        elements
            .map((element) => element.getAttribute('data-testid') ?? '')
            .filter((testId) => testId && !testId.endsWith('-icon') && !testId.endsWith('-description'))
            .map((testId) => testId.replace('ai-export-selection-option-', '')),
    );

    await selectionButton.click();
    await expect(selectionButton).toHaveAttribute('aria-expanded', 'false', {timeout: 2_000});
    return ids;
}

export async function configureCustomPeriod(page: Page, amount: number, unit: AiExportPeriodUnit): Promise<void> {
    await page.getByTestId('ai-export-period-custom').click();
    const amountInput = page.getByTestId('ai-export-period-custom-amount');
    await expect(amountInput).toBeVisible({timeout: 2_000});
    await amountInput.fill(String(amount));

    const unitButton = page.getByTestId('ai-export-period-custom-unit-button');
    await unitButton.click();
    await unitButton.press('Home');
    const unitIndex: Record<AiExportPeriodUnit, number> = {
        days: 0,
        weeks: 1,
        months: 2,
        years: 3,
    };
    for (let index = 0; index < unitIndex[unit]; index += 1) await unitButton.press('ArrowDown');
    await unitButton.press('Enter');
}

export async function expectCustomPeriod(page: Page, amount: number, unit: AiExportPeriodUnit): Promise<void> {
    await expect(page.getByTestId('ai-export-period-custom-amount')).toHaveValue(String(amount), {timeout: 2_000});
    const shortLabel: Record<AiExportPeriodUnit, string> = {
        days: 'D',
        weeks: 'W',
        months: 'M',
        years: 'Y',
    };
    await expect(page.getByTestId('ai-export-period-custom-unit-button')).toContainText(shortLabel[unit], {timeout: 2_000});
}

export async function isVisibleWithin(locator: Locator, timeout = 1_000): Promise<boolean> {
    return locator
        .waitFor({state: 'visible', timeout})
        .then(() => true)
        .catch(() => false);
}

export async function exportCurrentSelection(page: Page): Promise<AiExportResult> {
    await page.evaluate(async () => {
        try {
            await navigator.clipboard.writeText('');
        } catch {
            // Clipboard assertions report any actual permission failure.
        }
    });

    const requestPromise = page.waitForRequest(isSnapshotPost, {timeout: UI_TIMEOUT});
    const responsePromise = page.waitForResponse((response) => isSnapshotPost(response.request()), {timeout: API_TIMEOUT});
    await page.getByTestId('ai-export-copy-button').click();

    const [request, response] = await Promise.all([requestPromise, responsePromise]);
    const failureBody = response.status() === 200 ? '' : await response.text();
    expect(response.status(), failureBody).toBe(200);

    const copyAnyway = page.getByTestId('ai-export-copy-anyway');
    if (await isVisibleWithin(copyAnyway)) await copyAnyway.click();

    await expect(page.getByTestId('ai-export-menu-panel')).toBeHidden({timeout: 3_000});
    return {
        request,
        response,
        payload: request.postDataJSON() as Record<string, unknown>,
    };
}

export async function readClipboard(page: Page): Promise<string> {
    return page.evaluate(async () => {
        try {
            return await navigator.clipboard.readText();
        } catch {
            return '';
        }
    });
}

export async function waitForClipboard(page: Page, requiredFragments: readonly string[], message: string): Promise<string> {
    await expect
        .poll(
            async () => {
                const clipboardText = await readClipboard(page);
                return requiredFragments.every((fragment) => clipboardText.includes(fragment));
            },
            {
                timeout: 5_000,
                intervals: [100, 200, 500],
                message,
            },
        )
        .toBe(true);

    return readClipboard(page);
}

async function requireSeededEntry(candidates: readonly Locator[], errorMessage: string): Promise<Locator> {
    // "First of N that shows up" is `.or()`, not a hand-rolled poll: the union
    // retries on Playwright's own clock, so the loop's 100 ms sleep — the last
    // mechanical wait in the suite — has nothing left to cover.
    const union = candidates.reduce((acc, candidate) => acc.or(candidate));
    try {
        await expect(union.first()).toBeVisible({timeout: UI_TIMEOUT});
    } catch {
        throw new Error(`${errorMessage} Check populate_mock_data.py seeding.`);
    }
    for (const candidate of candidates) {
        if (await candidate.isVisible()) return candidate;
    }
    throw new Error(`${errorMessage} Check populate_mock_data.py seeding.`);
}

export async function gotoDashboard(page: Page): Promise<void> {
    await navigateTo(page, '/dashboard');
    await expect(page.getByTestId('dashboard-page')).toBeVisible({timeout: UI_TIMEOUT});
}

export async function gotoFirstAsset(page: Page): Promise<string> {
    await navigateTo(page, '/assets');
    await expect(page.getByTestId('assets-page')).toBeVisible({timeout: UI_TIMEOUT});
    const entry = await requireSeededEntry([page.getByTestId(/^asset-card-/).first(), page.getByTestId(/^asset-row-/).first()], 'No seeded asset card or row found on /assets.');
    await entry.click();
    await expect(page).toHaveURL(/\/assets\/\d+(?:[?#].*)?$/, {timeout: UI_TIMEOUT});
    await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
    return new URL(page.url()).pathname;
}

export async function gotoSeededAsset(page: Page, fixture: {readonly displayName: string; readonly ticker: string}): Promise<string> {
    const response = await page.request.get('/api/v1/assets/query', {
        params: {ticker: fixture.ticker},
    });
    if (!response.ok()) {
        throw new Error(`Seeded asset lookup failed with HTTP ${response.status()}: ${await response.text()}`);
    }

    const body: unknown = await response.json();
    const matches = Array.isArray(body)
        ? body.filter(
              (entry): entry is {id: number; display_name: string; identifier_ticker: string; active: boolean} =>
                  typeof entry === 'object' &&
                  entry !== null &&
                  Number.isInteger((entry as {id?: unknown}).id) &&
                  (entry as {display_name?: unknown}).display_name === fixture.displayName &&
                  (entry as {identifier_ticker?: unknown}).identifier_ticker === fixture.ticker &&
                  (entry as {active?: unknown}).active === true,
          )
        : [];
    if (matches.length !== 1) {
        throw new Error(`Expected one active seeded asset ${fixture.displayName} (${fixture.ticker}), found ${matches.length}. Check populate_mock_data.py seeding.`);
    }

    await navigateTo(page, `/assets/${matches[0].id}`);
    await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
    return new URL(page.url()).pathname;
}

export async function gotoFirstBroker(page: Page): Promise<string> {
    await navigateTo(page, '/brokers');
    await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: UI_TIMEOUT});
    const entry = await requireSeededEntry([page.getByTestId(/^broker-card-/).first()], 'No seeded broker card found on /brokers.');
    await entry.click();
    await expect(page).toHaveURL(/\/brokers\/\d+(?:[?#].*)?$/, {timeout: UI_TIMEOUT});
    await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
    return new URL(page.url()).pathname;
}

export async function gotoFx(page: Page, pair: string): Promise<void> {
    await navigateTo(page, `/fx/${pair}`);
    await expect(page.getByTestId('fx-detail-page')).toBeVisible({timeout: UI_TIMEOUT});
}

export function numericScopeId(page: Page, domain: 'assets' | 'brokers'): number {
    const match = new URL(page.url()).pathname.match(new RegExp(`^/${domain}/(\\d+)$`));
    if (!match) throw new Error(`Cannot derive ${domain} scope ID from URL: ${page.url()}`);
    return Number(match[1]);
}

export async function assertPanelWithinViewport(page: Page, panel: Locator): Promise<void> {
    const viewport = page.viewportSize();
    const box = await panel.boundingBox();
    if (!viewport || !box) throw new Error('AI Export panel requires viewport and layout boxes');

    expect(box.x).toBeGreaterThanOrEqual(7);
    expect(box.y).toBeGreaterThanOrEqual(7);
    expect(box.x + box.width).toBeLessThanOrEqual(viewport.width - 7);
    expect(box.y + box.height).toBeLessThanOrEqual(viewport.height - 7);
}

export async function assertPanelAboveOverlay(panel: Locator, overlay: Locator): Promise<void> {
    await expect(overlay).toBeVisible({timeout: UI_TIMEOUT});
    const overlayTestId = await overlay.getAttribute('data-testid');
    if (!overlayTestId) throw new Error('Chart overlay requires a data-testid');

    const layers = await panel.evaluate((panelElement, testId) => {
        const overlayElement = document.querySelector<HTMLElement>(`[data-testid="${testId}"]`);
        if (!overlayElement) throw new Error(`Missing overlay ${testId}`);

        let overlayZ = 0;
        let current: HTMLElement | null = overlayElement;
        while (current && current !== document.body) {
            const parsed = Number.parseInt(getComputedStyle(current).zIndex, 10);
            if (Number.isFinite(parsed)) overlayZ = Math.max(overlayZ, parsed);
            current = current.parentElement;
        }

        return {
            bodyLevel: panelElement.parentElement === document.body,
            panelZ: Number.parseInt(getComputedStyle(panelElement).zIndex, 10),
            overlayZ,
        };
    }, overlayTestId);

    expect(layers.bodyLevel).toBe(true);
    expect(layers.panelZ).toBe(9000);
    expect(layers.panelZ).toBeGreaterThan(layers.overlayZ);
}
