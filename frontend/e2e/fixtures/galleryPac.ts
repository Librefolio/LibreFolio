/**
 * Gallery, Tools — the PAC allocator: one realistic draft per viewport, then the nine shots of its
 * page (mkdocs_src/docs/user/tools/pac-allocator/index.en.md, one placeholder per wizard step and
 * three for the result).
 *
 * ## The draft
 *
 * The planner keeps its draft in the open page only (PacPlannerTool.svelte: `new PlannerDraft(...)`
 * at mount; nothing is saved, a reload wipes it). A language or a theme switched from the header
 * does not touch it: the language store only sets the locale (stores/app/language.ts), the root
 * layout tears the app down for the first dictionary only (routes/+layout.svelte), and the Tool
 * Host remounts the renderer on a session change only (ToolHost.svelte, `{#key account.generation}`).
 * So {@link buildPacDraft} fills the draft once per test — once per viewport — and every
 * language and theme photographs the same draft. Leaving the page with a draft would ask to
 * confirm (`beforeNavigate`): the test never navigates away; the page closes with the test.
 *
 * What it holds ({@link PAC_SCENARIO}): valuation in EUR; liquidity copied from DEGIRO (EUR), a
 * new contribution in EUR and an external account in EUR; DEGIRO (one order mode, EUR, by amount,
 * a percentage fee with minimum and maximum, the Broker converting) and Interactive Brokers (by
 * units, a fixed fee, you converting); Apple (Auto price) and Microsoft (Manual price) taken from
 * «Your Assets» and a Manual Asset; DEGIRO may buy only the Manual Asset, with every limit of a
 * route filled; targets 30/30/40. The USD Assets can be bought on Interactive Brokers only, and
 * most of the money is in EUR: the plan has a currency exchange to make.
 *
 * The seed moved shares in USD on DEGIRO (populate_mock_data.py, the AAPL and MSFT transfers, amount
 * 0): a copy of DEGIRO brings a USD cash row at zero and a USD order mode. The draft removes both,
 * as a user who plans DEGIRO in EUR does — nothing in it assumes what the copy brings.
 *
 * ## Read-only, offline
 *
 * The copies and the Asset reads go through `POST /portfolio/allocation-source` (a read of the
 * database, no provider: planner/source.ts), the calculation through the Tools API (a local
 * solver, `plan_pac_allocation`); nothing is written. Nothing here reaches a route of the
 * gallery's offline guard (galleryReportSets.ts, `guardGalleryOffline`): no sync, no probe, no
 * live price.
 *
 * ## Framing
 *
 * A wizard step ends in a sticky footer (Back, Continue) that covers the bottom of the screen while
 * the step goes on below it; {@link framePacBlock} keeps it out of the block it frames. A short page
 * is shot from its top, header included: it cannot scroll far enough for the header to slide away.
 * Focus left in the header pins it there (Header.svelte, `focusPinned`): a language or a theme
 * picked from it leaves the focus on its button, so every frame first takes the focus off the header.
 *
 * ## A screen taller than the desktop's: `tools/pac-result-proof`
 *
 * Coordinator's decision, provisional: the simulation shot's rule (galleryRiskLab.ts, «Screens taller than the
 * desktop's») extended to Proof and solver. The page wants the whole section in one image — the outcome, proof and stop
 * badges, the exact value of each objective, the solver stages and the backend timings — and it is far taller than the
 * desktop's 720 px. On the desktop only, {@link fitScreenToPacProof} gives that shot a screen as tall as the section plus
 * the frame's margins, width and scale unchanged, and {@link restorePacScreen} puts the project's screen back right after
 * the shot, so the next language's result and plan are taken on 720 px again. The mobile project keeps its phone: the
 * section from its title.
 */

import type {APIResponse} from '@playwright/test';
import {expect, type Locator, type Page} from './playwright';
import {navigateTo} from './auth-helpers';
import {expectNoToast, waitForStillness} from './galleryReportSets';
import {fitViewportToBlock, frameFromTop, imagesSettled, parkPointer, scrollBackToHeader} from './galleryRiskLab';
import {optionsClosed} from './probe';

/** The planner's page (features/tools/registry.ts, `defineToolRenderer('pac_allocator', …)`). */
export const PAC_URL = '/tools/pac_allocator';

/** The seeded Brokers and Assets the draft copies, by name (populate_mock_data.py). */
const PAC_BROKER_NAMES = {ib: 'Interactive Brokers', degiro: 'DEGIRO'} as const;
const PAC_ASSET_NAMES = {apple: 'Apple Inc.', microsoft: 'Microsoft Corporation'} as const;

/** Apple and Microsoft are both 100% USA in the seed (populate_mock_data.py, `classification_params`). */
const SEEDED_COUNTRY = 'USA';

/**
 * Every value the draft is given, typed once: every language and theme shows the same figures. The
 * names are the user's own, so they stay as typed in every language; none is a real account. The
 * fee of DEGIRO is the documentation's own example (0.19%, minimum 1.50, maximum 18).
 */
export const PAC_SCENARIO = {
    valuationCurrency: 'EUR',
    copiedCash: {currency: 'EUR', toUse: '2000'},
    contribution: {label: 'PAC', amount: '500'},
    /**
     * In EUR, as every source: a foreign source makes the engine fail — in USD it lets the plan convert USD into EUR at the
     * inverse of the stored EUR/USD rate, an exact value that never terminates in base 10, which the engine then fails to publish
     * (WireNumberTooLargeError, planner_report.py `ratio_to_fixed_decimal(ledger.raw_rounding_delta)`); in CHF the calculation
     * fails on a negative value (ValueError, models.py `_require_nonnegative`). Both end in «Calculation failed». With EUR
     * sources only, the plan's one conversion is EUR into USD at Interactive Brokers. Back to a foreign currency once fixed.
     */
    externalAccount: {name: 'Northwind Bank', currency: 'EUR', declared: '3000', toUse: '1200'},
    ibUsdFixedFee: '1',
    degiroFee: {floor: '1.5', ratePercent: '0.19', cap: '18'},
    microsoftManualPrice: '410',
    manualAsset: {name: 'Global Bond ETF', price: '52.4'},
    /** DEGIRO's route to the Manual Asset: every limit filled, so the shot shows each one with a value. */
    bondOnDegiro: {minimum: '100', required: '300', cap: '2500', marginPercent: '0.5'},
    /** The same Asset on Interactive Brokers, less preferred: the plan buys it on DEGIRO. */
    bondOnIbPriority: '1',
    appleRequiredOnIb: '2',
    microsoftCapOnIb: '3',
    targets: {apple: '30', microsoft: '30', bond: '40'},
    /** The Review is shot with the target total at 90%: one field still to complete. */
    incompleteBondTarget: '30',
} as const;

/** Database ids of what the draft copies, found by name — never assumed from the populate order. */
export interface PacIds {
    brokers: {ib: number; degiro: number};
    assets: {apple: number; microsoft: number};
}

/** The draft's own keys (planner/copies.ts: `broker:<id>`, `cash:broker:<id>:<currency>`, `asset:<id>`); the Manual Asset's is generated. */
export interface PacDraft {
    ids: PacIds;
    keys: {ib: string; degiro: string; degiroCash: string; apple: string; microsoft: string; bond: string};
}

export type PacStep = 'scenario' | 'liquidity' | 'brokers' | 'assets' | 'routing' | 'targets' | 'fx' | 'strategy' | 'review';

/** The spec's `waitForMotionSettled`: nothing is animating in the scope (the Web Animations the frozen CSS cannot pause). */
export type MotionSettled = (scope: Locator, what: string) => Promise<void>;

/** Margin between a framed block and the edges of what is shown. */
const FRAME_MARGIN = 8;
/** Header.svelte, `HIDE_SCROLL_THRESHOLD`: the header slides away only past its own height plus this much scroll. */
const HEADER_HIDE_SLACK = 8;

/** Data reads of the planner: one `POST /portfolio/allocation-source` over the admin's Brokers, a database read that takes well under a second on a quiet lane. */
const READ_TIMEOUT = 20_000;
/**
 * The calculation: the copied facts read again, then `POST /tools/…` to the solver. The tool's own contract waits at most 65 s
 * (backend tool_plugins/pac_allocator.py, `client_timeout_ms`); past that the planner shows its own error, which the state
 * assertion then names. The engine needs milliseconds for a draft this size.
 */
const CALCULATION_TIMEOUT = 75_000;

// ---------------------------------------------------------------------------
// Ids and the page
// ---------------------------------------------------------------------------

async function jsonOk<T>(response: APIResponse, what: string): Promise<T> {
    expect(response.ok(), `${what} answered HTTP ${response.status()}`).toBe(true);
    return (await response.json()) as T;
}

function single(matches: Array<{id: number}>, what: string): number {
    if (matches.length !== 1) throw new Error(`${what} found ${matches.length} times, expected once. Check populate_mock_data.py seeding.`);
    return matches[0].id;
}

/** The ids of DEGIRO, Interactive Brokers, Apple and Microsoft, through the page's own session (`page.request` is not routed). */
export async function resolvePacIds(page: Page): Promise<PacIds> {
    const brokers = await jsonOk<{items?: Array<{id: number; name: string}>}>(await page.request.get('/api/v1/brokers'), 'GET /api/v1/brokers');
    const assets = await jsonOk<Array<{id: number; display_name: string}>>(await page.request.get('/api/v1/assets/query'), 'GET /api/v1/assets/query');
    const broker = (name: string) =>
        single(
            (brokers.items ?? []).filter((item) => item.name === name),
            `Broker "${name}" among the admin's Brokers`,
        );
    const asset = (name: string) =>
        single(
            assets.filter((item) => item.display_name === name),
            `Asset "${name}"`,
        );
    return {
        brokers: {ib: broker(PAC_BROKER_NAMES.ib), degiro: broker(PAC_BROKER_NAMES.degiro)},
        assets: {apple: asset(PAC_ASSET_NAMES.apple), microsoft: asset(PAC_ASSET_NAMES.microsoft)},
    };
}

/**
 * Open the PAC allocator and end on its first step: the Tools catalogue in and healthy (a degraded one would toast), the
 * renderer mounted, the planner on Scenario. The first open on a lane loads the catalogue and the renderer's chunk.
 */
export async function openPacPlanner(page: Page): Promise<Locator> {
    await navigateTo(page, PAC_URL);
    const host = page.getByTestId('tool-host');
    await expect(host, 'the PAC allocator did not load').toHaveAttribute('data-state', 'ready', {timeout: 30_000});
    await expect(host).toHaveAttribute('data-busy', 'false');
    await expect(host.getByTestId('tool-host-degraded'), 'the Tools catalogue came back degraded').toHaveCount(0);
    const planner = host.getByTestId('pac-planner');
    await expect(planner).toHaveAttribute('data-view', 'wizard', {timeout: 10_000});
    await expect(planner).toHaveAttribute('data-step', 'scenario');
    return planner;
}

/**
 * Go to a wizard step from the step list — the vertical list on a desktop, the «Steps» list on a phone (StepNav.svelte,
 * `data-variant`) — and end on the step shown with its title focused: the planner focuses it on every change, which also
 * scrolls it into view, so the change is over only then.
 */
export async function goToPacStep(page: Page, step: PacStep): Promise<Locator> {
    const planner = page.getByTestId('pac-planner');
    await expect(planner, 'the planner is not on its wizard').toHaveAttribute('data-view', 'wizard');
    const section = planner.getByTestId('pac-planner-step');
    if ((await planner.getAttribute('data-step')) !== step) {
        const nav = planner.getByTestId('pac-planner-nav');
        await expect(nav).toBeVisible();
        const compact = (await nav.getAttribute('data-variant')) === 'compact';
        const toggle = nav.getByTestId('pac-planner-nav-toggle');
        if (compact) {
            if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
            await expect(toggle).toHaveAttribute('aria-expanded', 'true');
        }
        await nav.locator(`[data-testid="pac-planner-nav-step"][data-step="${step}"]`).click();
        await expect(planner).toHaveAttribute('data-step', step);
        if (compact) await expect(toggle, 'the «Steps» list stays open').toHaveAttribute('aria-expanded', 'false');
        await expect.poll(() => section.evaluate((element) => element.contains(document.activeElement)), {message: `the ${step} step never took the focus`}).toBe(true);
    }
    await expect(section).toHaveAttribute('data-step', step);
    return section;
}

// ---------------------------------------------------------------------------
// Filling the draft
// ---------------------------------------------------------------------------

function cashCard(page: Page, cashKey: string): Locator {
    return page.locator(`[data-testid="pac-planner-cash"][data-cash-key="${cashKey}"]`);
}

function externalAccountCard(page: Page): Locator {
    return page.locator('[data-testid="pac-planner-cash"][data-origin="manual"]');
}

function brokerCard(page: Page, brokerKey: string): Locator {
    return page.locator(`[data-testid="pac-planner-broker"][data-broker-key="${brokerKey}"]`);
}

function assetCard(page: Page, assetKey: string): Locator {
    return page.locator(`[data-testid="pac-planner-asset"][data-asset-key="${assetKey}"]`);
}

function routeCard(page: Page, assetKey: string, brokerKey: string): Locator {
    return page.locator(`[data-testid="pac-planner-route"][data-asset-key="${assetKey}"][data-broker-key="${brokerKey}"]`);
}

function targetInput(page: Page, assetKey: string): Locator {
    return page.locator(`[data-testid="pac-planner-target"][data-asset-key="${assetKey}"]`).getByTestId('pac-planner-target-input');
}

/** Type a value into an exact-decimal field (ExactDecimalInput: canonical text, `.` as the separator in every language). */
async function typeValue(input: Locator, value: string): Promise<void> {
    await input.fill(value);
    await expect(input).toHaveValue(value);
}

/** Pick a currency in a CurrencySearchSelect: its inline search, then the option. Ends on the list closed, the code shown. */
async function chooseCurrency(scope: Locator, testId: string, code: string): Promise<void> {
    const select = scope.getByTestId(testId);
    const trigger = select.getByTestId(`${testId}-trigger`);
    await trigger.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');
    await select.getByTestId(`${testId}-search`).fill(code);
    // The currency catalogue is read once per language (currencyStore.ts): the first open of a session waits for it.
    const option = select.getByTestId(`search-select-option-${code}`);
    await expect(option, `${code} is not offered`).toBeVisible({timeout: 10_000});
    await option.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
    await optionsClosed(scope.page());
    // An ISO code, not a translation: the select shows the code it holds.
    await expect(trigger, `${testId} does not hold ${code}`).toContainText(code);
}

/**
 * Tick one owned Broker in a copy dialog (BrokerScopeCopyDialog.svelte) and copy it. The dialog reads the snapshot of every
 * Broker the admin owns first; the row must be selectable — owned — and, for liquidity, list `currency` among its cash.
 */
async function copyFromBroker(page: Page, kind: 'liquidity' | 'broker', brokerId: number, currency?: string): Promise<void> {
    const testid = kind === 'liquidity' ? 'pac-planner-liquidity-copy' : 'pac-planner-broker-copy';
    await page.getByTestId(`${testid}-open`).click();
    const dialog = page.getByTestId(testid);
    const body = dialog.getByTestId(`${testid}-body`);
    await expect(body, 'the Brokers the admin owns were not read').toHaveAttribute('data-state', 'ready', {timeout: READ_TIMEOUT});
    const row = body.locator(`[data-testid="${testid}-broker"][data-broker-id="${brokerId}"]`);
    await expect(row, `Broker ${brokerId} is not offered as one the admin owns: check populate_mock_data.py`).toHaveAttribute('data-selectable', 'true');
    if (currency) {
        // A cash row is a direct child of the list and carries its currency; the currency label inside the row carries the same
        // attribute (CurrencyCode), so only the list's own children are rows. A currency may hold more than one row: at least one.
        const cashRows = row.getByTestId(`${testid}-cash`).locator(`:scope > [data-currency="${currency}"]`);
        await expect(cashRows, `Broker ${brokerId} holds no ${currency} cash: check populate_mock_data.py`).not.toHaveCount(0);
    }
    await row.getByTestId(`${testid}-check`).check();
    await expect(row).toHaveAttribute('data-selected', 'true');
    await dialog.getByTestId(`${testid}-apply`).click();
    await expect(dialog).toHaveCount(0);
}

/** Remove a cash row from the Liquidity step through its confirmation (RemovalConfirm: ConfirmModal), and end on it gone. */
async function removeCash(page: Page, cashKey: string): Promise<void> {
    const card = cashCard(page, cashKey);
    await card.getByTestId('pac-planner-cash-remove').click();
    // The confirmation's test id sits on its header; its buttons are the header's siblings.
    const confirm = page.getByTestId('pac-planner-liquidity-removal');
    await expect(confirm).toBeVisible();
    await confirm.locator('..').getByTestId('confirm-modal-confirm').click();
    await expect(confirm).toHaveCount(0);
    await expect(card).toHaveCount(0);
}

/** Open a Broker's editor (BrokerEditor.svelte), let `configure` set its values, apply them to the draft. */
async function editBroker(page: Page, brokerKey: string, configure: (editor: Locator) => Promise<void>): Promise<void> {
    await brokerCard(page, brokerKey).getByTestId('pac-planner-broker-edit').click();
    const editor = page.getByTestId('pac-planner-broker-editor');
    await expect(editor.getByTestId('pac-planner-broker-editor-panel')).toBeVisible();
    await configure(editor);
    await editor.getByTestId('pac-planner-broker-editor-apply').click();
    await expect(editor).toHaveCount(0);
}

/**
 * Build the draft, step by step, the way a user does (see the module notes for what it holds), and end on the Review with
 * nothing left to complete. Every step is visited, so the step list marks them all; the FX step reads its rate (Auto).
 */
export async function buildPacDraft(page: Page, ids: PacIds): Promise<PacDraft> {
    const s = PAC_SCENARIO;
    const keys = {
        ib: `broker:${ids.brokers.ib}`,
        degiro: `broker:${ids.brokers.degiro}`,
        degiroCash: `cash:broker:${ids.brokers.degiro}:${s.copiedCash.currency}`,
        apple: `asset:${ids.assets.apple}`,
        microsoft: `asset:${ids.assets.microsoft}`,
        bond: '',
    };

    // Scenario: the valuation currency, chosen even when the admin's default is already EUR.
    await goToPacStep(page, 'scenario');
    await chooseCurrency(page.getByTestId('pac-planner-scenario'), 'pac-planner-scenario-currency', s.valuationCurrency);

    // Liquidity, in the order of the page's three sources: DEGIRO's cash, a new contribution, an external account.
    await goToPacStep(page, 'liquidity');
    await copyFromBroker(page, 'liquidity', ids.brokers.degiro, s.copiedCash.currency);
    const copied = cashCard(page, keys.degiroCash);
    await expect(copied).toHaveAttribute('data-origin', 'copied');
    await typeValue(copied.getByTestId('pac-planner-cash-selected'), s.copiedCash.toUse);
    await expect(copied.getByTestId('pac-planner-cash-exceeds'), `DEGIRO holds less than ${s.copiedCash.toUse} ${s.copiedCash.currency}: check populate_mock_data.py`).toHaveCount(0);
    // Every currency DEGIRO ever moved becomes a cash row (copies.ts, `applyLiquidityCopy`): the seed's share transfers in USD
    // leave it a USD row at zero. A user planning in EUR removes it; the copy is in the DOM whole, the dialog being closed.
    const copiedRows = page.locator('[data-testid="pac-planner-cash"][data-origin="copied"]');
    for (const key of await copiedRows.evaluateAll((rows) => rows.map((row) => row.getAttribute('data-cash-key') ?? ''))) {
        if (key !== keys.degiroCash) await removeCash(page, key);
    }
    await expect(copiedRows).toHaveCount(1);

    await page.getByTestId('pac-planner-contribution-add').click();
    const contribution = page.getByTestId('pac-planner-contribution');
    await expect(contribution).toHaveCount(1);
    // The default label is written in the language of the moment: a label of the user's own stays the same in every shot.
    await typeValue(contribution.getByTestId('pac-planner-contribution-label'), s.contribution.label);
    await typeValue(contribution.getByTestId('pac-planner-contribution-amount'), s.contribution.amount);
    await expect(contribution.getByTestId('pac-planner-contribution-currency-trigger')).toContainText(s.valuationCurrency);

    await page.getByTestId('pac-planner-manual-account-open').click();
    const account = page.getByTestId('pac-planner-manual-account');
    await typeValue(account.getByTestId('pac-planner-manual-account-name'), s.externalAccount.name);
    await chooseCurrency(account, 'pac-planner-manual-account-currency', s.externalAccount.currency);
    await typeValue(account.getByTestId('pac-planner-manual-account-available'), s.externalAccount.declared);
    await typeValue(account.getByTestId('pac-planner-manual-account-selected'), s.externalAccount.toUse);
    await account.getByTestId('pac-planner-manual-account-add').click();
    await expect(account).toHaveCount(0);
    await expect(externalAccountCard(page).getByTestId('pac-planner-cash-currency')).toHaveAttribute('data-currency', s.externalAccount.currency);

    // Brokers: DEGIRO came with its cash; Interactive Brokers is chosen as an existing Broker (identity only, no cash). A copied
    // Broker gets one order mode per currency it ever moved (copies.ts, `defaultModes(observed_currencies)`).
    await goToPacStep(page, 'brokers');
    await copyFromBroker(page, 'broker', ids.brokers.ib);
    for (const currency of ['USD', 'EUR']) {
        await expect(brokerCard(page, keys.ib).locator(`[data-testid="pac-planner-broker-mode"][data-currency="${currency}"]`), `Interactive Brokers has no ${currency} order mode (its cash currencies): check populate_mock_data.py`).toBeVisible();
    }
    await expect(brokerCard(page, keys.degiro).locator('[data-testid="pac-planner-broker-mode"][data-currency="EUR"]'), 'DEGIRO has no EUR order mode').toBeVisible();

    // Interactive Brokers: by units (the default), a fixed fee in USD; you convert before buying (the default).
    await editBroker(page, keys.ib, async (editor) => {
        const usd = editor.locator('[data-testid="pac-planner-mode"][data-currency="USD"]');
        await expect(usd).toHaveAttribute('data-kind', 'whole_quantity');
        await typeValue(usd.getByTestId('pac-planner-mode-fee-fixed'), s.ibUsdFixedFee);
    });

    // DEGIRO, the Broker of the shot: orders in EUR only — the seed's USD share transfers gave it a USD mode too, which goes —
    // by amount, the documentation's fee, the Broker converting when you buy.
    await editBroker(page, keys.degiro, async (editor) => {
        const modes = editor.getByTestId('pac-planner-mode');
        for (const currency of await modes.evaluateAll((items) => items.map((item) => item.getAttribute('data-currency') ?? ''))) {
            if (currency === 'EUR') continue;
            const other = editor.locator(`[data-testid="pac-planner-mode"][data-currency="${currency}"]`);
            await other.getByTestId('pac-planner-mode-remove').click();
            await expect(other).toHaveCount(0);
        }
        await expect(modes).toHaveCount(1);
        const eur = editor.locator('[data-testid="pac-planner-mode"][data-currency="EUR"]');
        await expect(eur, 'a new order mode is by number of units').toHaveAttribute('data-kind', 'whole_quantity');
        const kind = eur.getByTestId('pac-planner-mode-kind-button');
        await kind.click();
        await expect(kind).toHaveAttribute('aria-expanded', 'true');
        // Two order types and the current one marked: the other is «By amount». The block says which one it took.
        await eur.getByTestId('pac-planner-mode-kind-dropdown').locator('[role="option"][aria-selected="false"]').click();
        await expect(eur).toHaveAttribute('data-kind', 'monetary_amount');
        // By amount, the increment becomes the currency's smallest unit (BrokerEditor.svelte, `setKind`).
        await expect(eur.getByTestId('pac-planner-mode-step')).toHaveValue('0.01');
        await typeValue(eur.getByTestId('pac-planner-mode-fee-floor'), s.degiroFee.floor);
        await typeValue(eur.getByTestId('pac-planner-mode-fee-rate'), s.degiroFee.ratePercent);
        await typeValue(eur.getByTestId('pac-planner-mode-fee-cap'), s.degiroFee.cap);
        const automatic = editor.locator('[data-testid="pac-planner-conversion-mode"][data-mode="automatic"]');
        await automatic.click();
        await expect(automatic).toHaveAttribute('data-selected', 'true');
    });

    // Assets: Apple and Microsoft from «Your Assets» (every Asset held starts ticked), then a Manual Asset.
    await goToPacStep(page, 'assets');
    await page.getByTestId('pac-planner-owned-assets-open').click();
    const owned = page.getByTestId('pac-planner-owned-assets');
    const ownedBody = owned.getByTestId('pac-planner-owned-assets-body');
    await expect(ownedBody, 'the Assets the admin holds were not read').toHaveAttribute('data-state', 'ready', {timeout: READ_TIMEOUT});
    await ownedBody.getByTestId('pac-planner-owned-assets-none').click();
    const count = ownedBody.getByTestId('pac-planner-owned-assets-count');
    await expect(count).toHaveAttribute('data-selected', '0');
    for (const assetId of [ids.assets.apple, ids.assets.microsoft]) {
        const row = ownedBody.locator(`[data-testid="pac-planner-owned-assets-asset"][data-asset-id="${assetId}"]`);
        await expect(row, `Asset ${assetId} is not held in a Broker the admin owns: check populate_mock_data.py`).toBeVisible();
        await row.getByTestId('pac-planner-owned-assets-check').check();
        await expect(row).toHaveAttribute('data-selected', 'true');
    }
    await expect(count).toHaveAttribute('data-selected', '2');
    await owned.getByTestId('pac-planner-owned-assets-apply').click();
    await expect(owned).toHaveCount(0);
    // Their stored price and composition are read right after (AssetsStep.svelte, `readFacts`).
    await expect(page.getByTestId('pac-planner-assets'), 'the prices of the added Assets were not read').toHaveAttribute('data-busy', 'false', {timeout: READ_TIMEOUT});
    for (const key of [keys.apple, keys.microsoft]) {
        await expect(assetCard(page, key), `${key} has no stored price: check populate_mock_data.py`).toHaveAttribute('data-price', 'set');
        await expect(assetCard(page, key)).toHaveAttribute('data-price-mode', 'auto');
    }

    const microsoft = assetCard(page, keys.microsoft);
    await microsoft.getByTestId('pac-planner-asset-price-mode-manual').click();
    await expect(microsoft.getByTestId('pac-planner-asset-price-mode')).toHaveAttribute('data-mode', 'manual');
    await expect(microsoft).toHaveAttribute('data-price-mode', 'manual');
    await typeValue(microsoft.getByTestId('pac-planner-asset-price-input'), s.microsoftManualPrice);

    await page.getByTestId('pac-planner-asset-add').click();
    const assetEditor = page.getByTestId('pac-planner-asset-editor');
    await typeValue(assetEditor.getByTestId('pac-planner-asset-editor-name'), s.manualAsset.name);
    await typeValue(assetEditor.getByTestId('pac-planner-asset-editor-price'), s.manualAsset.price);
    await expect(assetEditor.getByTestId('pac-planner-asset-editor-price-currency-trigger')).toContainText(s.valuationCurrency);
    await assetEditor.getByTestId('pac-planner-asset-editor-apply').click();
    await expect(assetEditor).toHaveCount(0);
    const manual = page.locator('[data-testid="pac-planner-asset"][data-origin="manual"]');
    await expect(manual).toHaveCount(1);
    await expect(manual).toHaveAttribute('data-price-mode', 'manual-asset');
    const bondKey = await manual.getAttribute('data-asset-key');
    if (!bondKey) throw new Error('the Manual Asset carries no data-asset-key');
    keys.bond = bondKey;

    // Routing: a new route starts allowed. Apple and Microsoft are excluded on DEGIRO, one click each — DEGIRO has no USD mode
    // left, and an excluded route asks for none; every limit of DEGIRO's route to the Manual Asset is filled. The Asset may be
    // bought on both Brokers, so each route shows its Priority.
    await goToPacStep(page, 'routing');
    for (const key of [keys.apple, keys.microsoft]) {
        const route = routeCard(page, key, keys.degiro);
        if ((await route.getAttribute('data-enabled')) !== 'false') await route.getByTestId('pac-planner-route-enabled').click();
        await expect(route).toHaveAttribute('data-enabled', 'false');
    }
    const bondOnDegiro = routeCard(page, keys.bond, keys.degiro);
    await expect(bondOnDegiro).toHaveAttribute('data-enabled', 'true');
    await expect(bondOnDegiro).toHaveAttribute('data-ready', 'true');
    await typeValue(bondOnDegiro.getByTestId('pac-planner-route-minimum-if-active'), s.bondOnDegiro.minimum);
    await typeValue(bondOnDegiro.getByTestId('pac-planner-route-required-minimum'), s.bondOnDegiro.required);
    await typeValue(bondOnDegiro.getByTestId('pac-planner-route-cap'), s.bondOnDegiro.cap);
    await typeValue(bondOnDegiro.getByTestId('pac-planner-route-margin'), s.bondOnDegiro.marginPercent);
    await expect(bondOnDegiro.getByTestId('pac-planner-route-priority-field')).toBeVisible();
    await typeValue(routeCard(page, keys.bond, keys.ib).getByTestId('pac-planner-route-priority'), s.bondOnIbPriority);
    await typeValue(routeCard(page, keys.apple, keys.ib).getByTestId('pac-planner-route-required-minimum'), s.appleRequiredOnIb);
    await typeValue(routeCard(page, keys.microsoft, keys.ib).getByTestId('pac-planner-route-cap'), s.microsoftCapOnIb);

    // Targets: 30 / 30 / 40.
    await goToPacStep(page, 'targets');
    await typeValue(targetInput(page, keys.apple), s.targets.apple);
    await typeValue(targetInput(page, keys.microsoft), s.targets.microsoft);
    await typeValue(targetInput(page, keys.bond), s.targets.bond);
    await expect(page.getByTestId('pac-planner-targets-control')).toHaveAttribute('data-state', 'balanced');

    // FX: the one pair in play (EUR/USD), read from LibreFolio as the step opens (Auto); none may be missing.
    await goToPacStep(page, 'fx');
    const fx = page.getByTestId('pac-planner-fx');
    await expect(fx.locator('[data-testid="pac-planner-fx-pair"][data-pair="EUR/USD"]'), 'no EUR/USD rate stored: check populate_mock_data.py').toHaveAttribute('data-rate', 'set', {timeout: READ_TIMEOUT});
    await expect(fx).toHaveAttribute('data-busy', 'false');
    await expect(fx.locator('[data-testid="pac-planner-fx-pair"][data-rate="missing"]')).toHaveCount(0);

    await goToPacStep(page, 'strategy');
    const review = (await goToPacStep(page, 'review')).getByTestId('pac-planner-review');
    await expect(review.getByTestId('pac-planner-review-problems'), 'the draft is not complete').toHaveCount(0);
    await expect(review.getByTestId('pac-planner-calculate')).toBeEnabled();
    return {ids, keys};
}

// ---------------------------------------------------------------------------
// Framing
// ---------------------------------------------------------------------------

/** Take the focus off the app header, where a language or theme just picked leaves it and pins the header (Header.svelte, `focusPinned`). */
async function releaseHeaderFocus(page: Page): Promise<void> {
    await page.evaluate(() => {
        const header = document.querySelector('[data-testid="app-header"]');
        const active = document.activeElement;
        if (header && active instanceof HTMLElement && header.contains(active)) active.blur();
    });
    await expect(page.getByTestId('app-header'), 'the app header stays pinned: a menu or a dialog is still open').not.toHaveAttribute('data-scroll-state', 'pinned');
}

/** The part of the screen the wizard's sticky footer covers while its step goes on below the fold; none in the result. */
async function footerReserve(page: Page): Promise<number> {
    if ((await page.getByTestId('pac-planner').getAttribute('data-view')) !== 'wizard') return 0;
    const footer = page.getByTestId('pac-planner-footer');
    await expect(footer).toBeVisible();
    const box = await footer.boundingBox();
    return box ? Math.ceil(box.height) : 0;
}

/**
 * Frame a block, from `first` to `last`, as a measured layout decides — every language and theme of a viewport alike:
 * - a page that cannot scroll past its header's height keeps its header (it slides away only beyond that): the shot is taken
 *   from the top when the block is all there above the footer, from the end of the page otherwise;
 * - any other page brings the block down from the top of the screen, the header gone (galleryRiskLab.ts, `frameFromTop`):
 *   from `first` when the block fits above the footer, from `fallback` when it does not; with `keep: 'bottom'` the page then
 *   goes on down until `last` clears the footer, at the cost of the block's top.
 */
async function framePacBlock(page: Page, block: {first: Locator; last: Locator; fallback?: Locator; keep?: 'top' | 'bottom'}): Promise<void> {
    const viewport = page.viewportSize();
    if (!viewport) throw new Error('the page has no viewport');
    await releaseHeaderFocus(page);
    await scrollBackToHeader(page);
    await expect(block.first).toBeVisible();
    await expect(block.last).toBeVisible();
    const room = viewport.height - (await footerReserve(page)) - FRAME_MARGIN;

    const {maxScroll, headerHeight} = await page.evaluate(() => ({
        maxScroll: document.documentElement.scrollHeight - window.innerHeight,
        headerHeight: document.querySelector('[data-testid="app-header"]')?.getBoundingClientRect().height ?? 0,
    }));
    if (maxScroll <= headerHeight + HEADER_HIDE_SLACK) {
        if ((await block.last.evaluate((element) => element.getBoundingClientRect().bottom)) <= room) return;
        await page.evaluate((top) => window.scrollTo({top, behavior: 'instant'}), maxScroll);
        await waitForStillness(block.last, 'the framed block');
        return;
    }

    const top = await block.first.evaluate((element) => element.getBoundingClientRect().top + window.scrollY);
    const bottom = await block.last.evaluate((element) => element.getBoundingClientRect().bottom + window.scrollY);
    const fits = bottom - top + FRAME_MARGIN <= room;
    await frameFromTop(page, fits || !block.fallback ? block.first : block.fallback, FRAME_MARGIN);
    if (block.keep !== 'bottom') return;
    const overflow = await block.last.evaluate((element, limit) => Math.ceil(element.getBoundingClientRect().bottom - limit), room);
    if (overflow <= 0) return;
    await page.evaluate((by) => window.scrollBy({top: by, behavior: 'instant'}), overflow);
    await waitForStillness(block.last, 'the framed block');
}

/**
 * Scroll the body of a dialog — the scroll box around `first` — so that the block from `first` to `last` is shown with as much
 * of the dialog above it as fits; a block taller than the box is shown from `first`. Only that box scrolls. Says whether the whole
 * block is on show.
 */
async function revealInDialog(dialog: Locator, first: string, last: string): Promise<boolean> {
    const whole = await dialog.evaluate(
        (root, selectors) => {
            const start = root.querySelector(selectors.first);
            const end = root.querySelector(selectors.last);
            if (!(start instanceof HTMLElement) || !(end instanceof HTMLElement)) throw new Error(`${selectors.first} or ${selectors.last} is not in the dialog`);
            let node: HTMLElement | null = start.parentElement;
            let box: HTMLElement | null = null;
            while (node) {
                const overflow = getComputedStyle(node).overflowY;
                if ((overflow === 'auto' || overflow === 'scroll') && node.scrollHeight > node.clientHeight) {
                    box = node;
                    break;
                }
                if (node === root) break;
                node = node.parentElement;
            }
            if (!box) return true;
            const frame = box.getBoundingClientRect();
            const from = start.getBoundingClientRect().top - frame.top + box.scrollTop - 8;
            const to = end.getBoundingClientRect().bottom - frame.top + box.scrollTop + 8;
            const fromTop = Math.max(0, to - box.clientHeight);
            box.scrollTop = fromTop <= from ? fromTop : from;
            return fromTop <= from;
        },
        {first, last},
    );
    await waitForStillness(dialog.locator(last), 'the dialog body');
    return whole;
}

/**
 * The last steps before a shot, as the risk lab takes them: the pointer parked where nothing reacts to it and no tooltip left,
 * every image of the region loaded, nothing in it animating or moving, no toast over the page. `motionSettled` is the spec's
 * `waitForMotionSettled`.
 */
export async function settlePacShot(page: Page, region: Locator, what: string, motionSettled: MotionSettled): Promise<void> {
    await parkPointer(page);
    await imagesSettled(region);
    await motionSettled(region, what);
    await waitForStillness(region, what);
    await expectNoToast(page);
}

// ---------------------------------------------------------------------------
// The wizard shots, before any calculation
// ---------------------------------------------------------------------------

/** `tools/pac-step-liquidity`: DEGIRO's cash, the contribution and the external account, from the first card. */
export async function framePacLiquidity(page: Page, draft: PacDraft): Promise<Locator> {
    const step = await goToPacStep(page, 'liquidity');
    const copied = cashCard(page, draft.keys.degiroCash);
    await expect(copied).toHaveAttribute('data-origin', 'copied');
    await expect(step.getByTestId('pac-planner-contribution')).toHaveCount(1);
    await expect(externalAccountCard(page)).toHaveCount(1);
    // A remounted step shows no copy notice (CopyFlow is the step's own): the cards follow the three sources directly.
    await framePacBlock(page, {first: step, last: externalAccountCard(page), fallback: copied});
    return step;
}

/**
 * `tools/pac-step-brokers`: DEGIRO's editor, open over the Brokers step at the top of the page — its order mode by amount, the
 * increment, the fee and the Broker converting — with its body scrolled so the conversion choice is on show under the mode.
 * The editor edits a copy: {@link closePacBrokerEditor} cancels it.
 */
export async function framePacBrokerEditor(page: Page, draft: PacDraft, motionSettled: MotionSettled): Promise<Locator> {
    await goToPacStep(page, 'brokers');
    await releaseHeaderFocus(page);
    await scrollBackToHeader(page);
    await brokerCard(page, draft.keys.degiro).getByTestId('pac-planner-broker-edit').click();
    const dialog = page.getByTestId('pac-planner-broker-editor');
    const panel = dialog.getByTestId('pac-planner-broker-editor-panel');
    await expect(panel).toBeVisible();
    const s = PAC_SCENARIO;
    await expect(panel.getByTestId('pac-planner-mode'), 'DEGIRO orders in EUR only').toHaveCount(1);
    const eur = panel.locator('[data-testid="pac-planner-mode"][data-currency="EUR"]');
    await expect(eur).toHaveAttribute('data-kind', 'monetary_amount');
    await expect(eur.getByTestId('pac-planner-mode-step')).toHaveValue('0.01');
    await expect(eur.getByTestId('pac-planner-mode-fee-rate')).toHaveValue(s.degiroFee.ratePercent);
    await expect(eur.getByTestId('pac-planner-mode-fee-floor')).toHaveValue(s.degiroFee.floor);
    await expect(eur.getByTestId('pac-planner-mode-fee-cap')).toHaveValue(s.degiroFee.cap);
    await expect(panel.locator('[data-testid="pac-planner-conversion-mode"][data-mode="automatic"]')).toHaveAttribute('data-selected', 'true');
    await motionSettled(dialog, 'the Broker editor');
    // A measured layout decides, the same for every language and theme of a viewport: on a desktop the mode and the conversion
    // choice fit the dialog's body together; on a phone the mode alone fills it, and the shot shows the mode — order type,
    // increment, purchase fee — with the conversion choice below the fold.
    const whole = await revealInDialog(panel, '[data-testid="pac-planner-mode"][data-currency="EUR"]', '[data-testid="pac-planner-conversion-modes"]');
    await expect(eur.getByTestId('pac-planner-mode-kind-button'), 'the order type is out of the shot').toBeInViewport();
    if (whole) await expect(panel.getByTestId('pac-planner-conversion-modes'), 'the conversion choice is out of the shot').toBeInViewport();
    return dialog;
}

/** Close the Broker editor without applying (its working copy is dropped) and end on it gone. */
export async function closePacBrokerEditor(page: Page): Promise<void> {
    const dialog = page.getByTestId('pac-planner-broker-editor');
    await dialog.getByTestId('pac-planner-broker-editor-cancel').click();
    await expect(dialog).toHaveCount(0);
}

/**
 * `tools/pac-step-assets`: Apple (Auto), Microsoft (Manual) and the Manual Asset. The country names of the compositions are
 * read once per language (countryStore.ts) and, until then, the previous language's stay on screen: the shot waits for the name
 * the backend gives for the current language.
 */
export async function framePacAssets(page: Page, draft: PacDraft): Promise<Locator> {
    const step = await goToPacStep(page, 'assets');
    await expect(page.getByTestId('pac-planner-assets')).toHaveAttribute('data-busy', 'false', {timeout: READ_TIMEOUT});
    await expect(assetCard(page, draft.keys.apple)).toHaveAttribute('data-price-mode', 'auto');
    await expect(assetCard(page, draft.keys.microsoft)).toHaveAttribute('data-price-mode', 'manual');
    await expect(assetCard(page, draft.keys.bond)).toHaveAttribute('data-price-mode', 'manual-asset');
    for (const key of [draft.keys.apple, draft.keys.microsoft, draft.keys.bond]) await expect(assetCard(page, key), `${key} shows no price`).toHaveAttribute('data-price', 'set');
    const country = await countryName(page, SEEDED_COUNTRY);
    for (const key of [draft.keys.apple, draft.keys.microsoft]) {
        await expect(assetCard(page, key).locator('[data-testid="pac-planner-asset-dimension"][data-dimension="geography"]'), `${key}: the country is not named in the page's language`).toContainText(country, {timeout: READ_TIMEOUT});
    }
    await framePacBlock(page, {first: step, last: assetCard(page, draft.keys.bond), fallback: assetCard(page, draft.keys.apple)});
    return step;
}

/** A country's name in the page's current language, as the backend gives it to the country store. */
async function countryName(page: Page, iso3: string): Promise<string> {
    const language = await page.locator('html').getAttribute('lang');
    const body = await jsonOk<{items?: Array<{iso3?: string; name?: string}>}>(await page.request.get('/api/v1/utilities/countries', {params: {language: language ?? 'en'}}), 'GET /api/v1/utilities/countries');
    const name = (body.items ?? []).find((item) => item.iso3 === iso3)?.name;
    if (!name) throw new Error(`the country list has no ${iso3}`);
    return name;
}

/**
 * `tools/pac-step-routing`: the first Broker of the step, DEGIRO — Apple and Microsoft excluded, the Manual Asset allowed with
 * Minimum, Required and Maximum purchase, Price margin and Priority filled — from the step's title when the card fits under it.
 */
export async function framePacRouting(page: Page, draft: PacDraft): Promise<Locator> {
    const step = await goToPacStep(page, 'routing');
    const degiro = page.locator(`[data-testid="pac-planner-routing-broker"][data-broker-key="${draft.keys.degiro}"]`);
    await expect(degiro.getByTestId('pac-planner-routing-count')).toHaveAttribute('data-allowed', '1');
    await expect(degiro.getByTestId('pac-planner-routing-count')).toHaveAttribute('data-total', '3');
    const bond = routeCard(page, draft.keys.bond, draft.keys.degiro);
    await expect(bond.getByTestId('pac-planner-route-fields')).toBeVisible();
    await expect(bond.getByTestId('pac-planner-route-priority-field')).toBeVisible();
    await expect(bond.getByTestId('pac-planner-route-required-minimum')).toHaveValue(PAC_SCENARIO.bondOnDegiro.required);
    await framePacBlock(page, {first: step, last: degiro, fallback: degiro});
    return step;
}

/** Bring the target total to 90%, so the Review has one field still to complete; {@link framePacTargets} puts it back. */
export async function leavePacTargetsIncomplete(page: Page, draft: PacDraft): Promise<void> {
    await goToPacStep(page, 'targets');
    await typeValue(targetInput(page, draft.keys.bond), PAC_SCENARIO.incompleteBondTarget);
    await expect(page.getByTestId('pac-planner-targets-control')).toHaveAttribute('data-state', 'missing');
}

/**
 * `tools/pac-step-review`: the step summary, the one problem left — the target total — and «Calculate plan», disabled until it
 * is fixed. No calculation has run yet, so the Review offers no «See the last result». The «Calculation data» table stays
 * folded: open, it pushes the button out of a desktop screen. The block is framed from its foot, so the button is on show.
 */
export async function framePacReview(page: Page): Promise<Locator> {
    const step = await goToPacStep(page, 'review');
    const review = step.getByTestId('pac-planner-review');
    const problems = review.getByTestId('pac-planner-review-problems');
    await expect(problems).toBeVisible();
    const items = problems.getByTestId('pac-planner-review-problem-item');
    await expect(items, 'the draft holds another problem than the target total').toHaveCount(1);
    await expect(items).toHaveAttribute('data-step', 'targets');
    const calculate = review.getByTestId('pac-planner-calculate');
    await expect(calculate).toBeDisabled();
    await expect(review.getByTestId('pac-planner-show-result')).toHaveCount(0);
    await expect(review.getByTestId('pac-planner-review-facts-toggle')).toHaveAttribute('aria-expanded', 'false');
    await framePacBlock(page, {first: step, last: calculate, keep: 'bottom'});
    return step;
}

/** `tools/pac-step-targets`: the field completed again — 30 / 30 / 40, the total at 100% — with «Balance all» and «Copy current distribution». */
export async function framePacTargets(page: Page, draft: PacDraft): Promise<Locator> {
    const step = await goToPacStep(page, 'targets');
    await typeValue(targetInput(page, draft.keys.bond), PAC_SCENARIO.targets.bond);
    const control = page.getByTestId('pac-planner-targets-control');
    await expect(control).toHaveAttribute('data-state', 'balanced');
    await expect(step.getByTestId('pac-planner-targets-balance-all')).toBeVisible();
    await expect(step.getByTestId('pac-planner-distribution-open')).toBeEnabled();
    await framePacBlock(page, {first: step, last: control, fallback: step});
    return step;
}

// ---------------------------------------------------------------------------
// The calculation and the result shots
// ---------------------------------------------------------------------------

/**
 * Calculate the complete draft from its Review and end on a plan: the copied facts read again and nothing missing from them,
 * the result current (not stale), state `ready_incumbent`. A no-op, an infeasible draft or a tool error fails here, named.
 */
export async function calculatePacPlan(page: Page): Promise<Locator> {
    const review = (await goToPacStep(page, 'review')).getByTestId('pac-planner-review');
    await expect(review.getByTestId('pac-planner-review-problems')).toHaveCount(0);
    const calculate = review.getByTestId('pac-planner-calculate');
    await expect(calculate).toBeEnabled();
    await calculate.click();
    const planner = page.getByTestId('pac-planner');
    await expect(planner).toHaveAttribute('data-view', 'result');
    await expect(planner, 'the calculation is still running').toHaveAttribute('data-busy', 'false', {timeout: CALCULATION_TIMEOUT});
    await expect(planner, 'the calculation did not end on a plan').toHaveAttribute('data-state', 'ready_incumbent');
    const result = planner.getByTestId('pac-planner-result');
    await expect(result).toHaveAttribute('data-state', 'ready_incumbent');
    await expect(result).toHaveAttribute('data-stale', 'false');
    await expect(planner.getByTestId('pac-planner-refresh-notice'), 'a copied fact was no longer found in LibreFolio').toHaveAttribute('data-missing', '0');
    return result;
}

function resultSection(page: Page, id: 'allocation' | 'plan' | 'exposures' | 'ledger' | 'proof'): Locator {
    return page.getByTestId('pac-planner-result').locator(`[data-testid="pac-planner-result-section"][data-section="${id}"]`);
}

/**
 * `tools/pac-result`: the outcome badges — a plan, verified in Decimal, proven optimal, the search completed — the Key figures
 * and the Allocation per Asset table, from the top of the outcome. An unproven plan would document a degraded state: it fails.
 */
export async function framePacResult(page: Page): Promise<Locator> {
    const result = page.getByTestId('pac-planner-result');
    await expect(result).toHaveAttribute('data-stale', 'false');
    const outcome = result.getByTestId('pac-planner-outcome');
    await expect(outcome).toHaveAttribute('data-state', 'ready_incumbent');
    const badges = outcome.getByTestId('pac-planner-outcome-badges');
    for (const [badge, tone] of [
        ['availability', 'success'],
        ['validation', 'info'],
        ['proof', 'success'],
        ['stop', 'neutral'],
    ] as const) {
        await expect(badges.locator(`[data-testid="pac-planner-outcome-badge"][data-badge="${badge}"]`), `the ${badge} badge is not ${tone}`).toHaveAttribute('data-tone', tone);
    }
    const kpi = result.getByTestId('pac-planner-kpi');
    for (const id of ['fixed_reference', 'final_invested', 'shortfall', 'selected_funding', 'explicit_cost', 'orders']) await expect(kpi.locator(`[data-testid="pac-planner-kpi-item"][data-kpi="${id}"]`)).toBeVisible();
    await expect(kpi.getByTestId('pac-planner-kpi-compute')).toBeVisible();
    const allocation = resultSection(page, 'allocation');
    await expect(allocation).toHaveAttribute('data-open', 'true');
    // One row per Asset of the draft: three, all this test's own.
    await expect(allocation.getByTestId('pac-planner-assets-table').locator('tbody tr[data-row-id]')).toHaveCount(3);
    await framePacBlock(page, {first: outcome, last: allocation, fallback: outcome});
    return result;
}

/**
 * `tools/pac-result-plan`: the Operational plan from its title — numbered cash steps, the currency exchange made on Interactive
 * Brokers (it converts before buying), then the orders. Interactive Brokers always has orders: Apple and Microsoft are bought
 * there only.
 */
export async function framePacPlan(page: Page, draft: PacDraft): Promise<Locator> {
    const plan = resultSection(page, 'plan');
    await expect(plan).toHaveAttribute('data-open', 'true');
    await expect(plan.locator('[data-testid="pac-planner-plan-step"][data-kind="funding"]'), 'the plan moves no cash').not.toHaveCount(0);
    await expect(plan.locator('[data-testid="pac-planner-plan-step"][data-kind="conversion"]'), 'the plan makes no currency exchange').not.toHaveCount(0);
    const ibOrders = plan.locator(`[data-testid="pac-planner-plan-orders"][data-broker="${draft.keys.ib}"]`);
    await expect(ibOrders, 'Interactive Brokers has no orders').toBeVisible();
    // From the section's title whatever fits: the numbered steps come first, the orders follow them.
    await framePacBlock(page, {first: plan, last: ibOrders, fallback: plan});
    return plan;
}

/**
 * `tools/pac-result-proof`: Proof and solver from its title — the outcome, proof and stop badges, the exact value of each objective
 * of the Proportional cascade, the solver stages and the backend timings. Opened once, through «Proof and timings» (it scrolls
 * there smoothly: the frame waits for the section to arrive); it stays open for the next languages and themes. On the desktop the
 * shot then gets a screen as tall as the section: {@link fitScreenToPacProof}.
 */
export async function framePacProof(page: Page): Promise<Locator> {
    const result = page.getByTestId('pac-planner-result');
    const proof = resultSection(page, 'proof');
    if ((await proof.getAttribute('data-open')) !== 'true') {
        await result.getByTestId('pac-planner-goto-proof').click();
        await expect(proof).toHaveAttribute('data-open', 'true');
        await expect(proof).toBeInViewport();
        await waitForStillness(proof, 'the Proof and solver section');
    }
    const panel = proof.getByTestId('pac-planner-proof');
    await expect(panel).toHaveAttribute('data-proof', 'optimal_proven');
    await expect(panel.getByTestId('pac-planner-proof-stop')).toBeVisible();
    // policies.ts, POLICY_OBJECTIVES.proportional: the cascade the result publishes, one exact value each.
    for (const objective of ['fixed_l2', 'shortfall', 'route_priority', 'explicit_cost', 'active_order_rows']) {
        await expect(panel.locator(`[data-testid="pac-planner-objective"][data-objective="${objective}"]`).getByTestId('pac-planner-objective-value')).toBeVisible();
    }
    await expect(panel.getByTestId('pac-planner-solver-stages')).toBeVisible();
    // The platform's «Backend timings» box, then the planner's own bar of where the time went.
    const timings = panel.getByTestId('tool-execution-metrics');
    await expect(timings).toBeVisible();
    await framePacBlock(page, {first: proof, last: timings, fallback: proof});
    return proof;
}

// ---------------------------------------------------------------------------
// A screen taller than the desktop's (coordinator's decision, provisional)
// ---------------------------------------------------------------------------

/** The screen a page had before {@link fitScreenToPacProof} grew it: what {@link restorePacScreen} puts back. */
const screensBeforeProof = new WeakMap<Page, {width: number; height: number}>();

/**
 * DESKTOP ONLY — the simulation shot's rule (galleryRiskLab.ts, «Screens taller than the desktop's»), coordinator's decision,
 * provisional. Called on the section {@link framePacProof} framed: the screen becomes as tall as the whole section plus the frame's
 * margins, never shorter than the project's, width and scale unchanged (`fitViewportToBlock`) — measured every combination, the
 * section's sentences wrap differently in each language — and the size is logged (📐) under `shot`. The section is framed again
 * with its top at the margin, settled again (a resize may redraw a chart) and asserted whole in the shot. {@link restorePacScreen},
 * right after the shot, puts the project's screen back. Reverting the decision is deleting the one call in the spec.
 */
export async function fitScreenToPacProof(page: Page, proof: Locator, shot: string, motionSettled: MotionSettled): Promise<void> {
    const screen = page.viewportSize();
    if (!screen) throw new Error('the page has no viewport');
    const own = screensBeforeProof.get(page) ?? screen;
    screensBeforeProof.set(page, own);
    await expect(proof, 'Proof and solver is closed').toHaveAttribute('data-open', 'true');
    await armResizeBarrier(page);
    const fit = await fitViewportToBlock(page, proof, FRAME_MARGIN, own.height);
    if (fit.viewportHeight !== screen.height) await resizeHandled(page, fit.viewportHeight);
    console.log(`  📐 ${shot}: block ${fit.blockHeight} px → screen ${own.width}×${fit.viewportHeight}`);
    await releaseHeaderFocus(page);
    // The resize showed the header where the page stands (Header.svelte, `syncScrollContext`), so the frame's way back to the top
    // would pass at once and its scroll down land in the same frame as that way up: the header would see no movement and stay.
    // The page goes to the top first and renders it — two frames: the scroll event, then the header's own frame after it.
    await page.evaluate(() => window.scrollTo({top: 0, behavior: 'instant'}));
    await renderedFrames(page);
    await frameFromTop(page, proof, FRAME_MARGIN);
    await settlePacShot(page, proof, 'the Proof and solver section', motionSettled);
    await expect(proof, 'the Proof and solver section is not whole in the shot').toBeInViewport({ratio: 1});
}

/**
 * Put back the screen the page had before {@link fitScreenToPacProof} and end on the page laid out for it; a no-op when nothing grew
 * it (the mobile project, or the decision reverted). Called right after the tall shot, inside the same combination: the next one's
 * result and plan are 720 px shots.
 */
export async function restorePacScreen(page: Page): Promise<void> {
    const own = screensBeforeProof.get(page);
    if (!own) return;
    screensBeforeProof.delete(page);
    const screen = page.viewportSize();
    if (screen?.width === own.width && screen.height === own.height) return;
    await armResizeBarrier(page);
    await page.setViewportSize(own);
    await resizeHandled(page, own.height);
}

/** Arm a one-shot `resize` listener in the page, for {@link resizeHandled}. */
async function armResizeBarrier(page: Page): Promise<void> {
    await page.evaluate(() => {
        const flag = window as unknown as {__pacGalleryResized?: boolean};
        flag.__pacGalleryResized = false;
        window.addEventListener(
            'resize',
            () => {
                flag.__pacGalleryResized = true;
            },
            {once: true},
        );
    });
}

/**
 * End once the page has dispatched its `resize` and lays out at `height`. The header resets itself on that event (Header.svelte,
 * `syncScrollContext`: back to visible, its scroll baseline where the page stands): an event arriving after the next frame was
 * scrolled would put the header back over the shot. The page's own listener ran first: it was added at mount.
 */
async function resizeHandled(page: Page, height: number): Promise<void> {
    await expect.poll(() => page.evaluate(() => ((window as unknown as {__pacGalleryResized?: boolean}).__pacGalleryResized === true ? window.innerHeight : -1)), {message: 'the page never handled the screen resize'}).toBe(height);
}

/** Two animation frames rendered in the page: a scroll made before is dispatched, and every frame callback it scheduled has run. */
async function renderedFrames(page: Page): Promise<void> {
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
}
