/**
 * FX — the destructive routes, on both the pair list and the pair detail page.
 *
 * These are the handlers that *write* to the shared, user-less FX tables and were
 * deliberately left uncovered until they could be exercised safely:
 *
 *   - list page: `confirmDelete` (single pair), `confirmBulkDelete` (bulk pairs),
 *     `handleBulkRefreshFx` (re-fetches rates for the selection);
 *   - detail page: the manual rate editor's delete-a-rate + save (`handleSave`
 *     delete branch), and `handleSwapDirection`'s confirm-while-editing gate.
 *
 * `fx-bulk.spec.ts` says in its own header that it stops short of exactly these
 * (bulk refresh, confirmed delete) "because they mutate shared FX data … that
 * other specs read". This file is that missing half, done the safe way.
 *
 * Strategy: disposable pairs, never mock pairs. Every pair here uses a currency
 * that is not in the mock and not touched by any sibling fx spec (NZD, SGD, MXN,
 * ZAR, HKD, SEK, NOK, PLN — all EUR-first so `base < quote` holds), priced by the
 * deterministic MOCKFX provider. Each test deletes only its own pair; the mock
 * baseline is never touched, so nothing needs resurrecting and the database is
 * left exactly as found. The `afterAll` repopulate is a net, not the plan — see
 * `fixtures/mock-restore.ts`.
 */
import {expect, test, type APIRequestContext} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {goToFxPage, goToFxDetailPage} from './fx-helpers';
import {daysAgoIso} from '../fixtures/dates';
import {apiLogin, REPOPULATE_ALLOWED, repopulateMockData} from '../fixtures/mock-restore';

// ─────────────────────────────────────────────────────────────────────────────
// Serial, and here is what is shared — the frontend twin of the backend's
// `exclusive_because`. This file creates disposable FX pairs (routes + rates) in
// the global, user-less `fx_conversion_routes` / `fx_rates` tables, then walks
// the delete and bulk-refresh routes on them. It hands those rows down the
// sequence: a pair created in `beforeAll` is read by one test and destroyed by
// another. The file owns those rows start to finish; a sibling test toggling the
// shared list selection mid-assertion, or the `afterAll` net firing while another
// worker is mid-test, would corrupt the run. That is the whole reason it opts out
// of `fullyParallel`.
// ─────────────────────────────────────────────────────────────────────────────
test.describe.configure({mode: 'serial'});

const API = '/api/v1';

/** All disposable pairs — created once in `beforeAll`, swept in `afterAll`. */
const P_DETAIL = {base: 'EUR', quote: 'NZD'}; // non-destructive detail interactions
const P_EDIT_DEL = {base: 'EUR', quote: 'SGD'}; // editor: delete one rate + save
const P_SWAP_EDIT = {base: 'EUR', quote: 'MXN'}; // swap-while-editing confirm gate
const P_BULK_REFRESH = [
    {base: 'EUR', quote: 'ZAR'},
    {base: 'EUR', quote: 'HKD'},
];
const P_SINGLE_DEL = {base: 'EUR', quote: 'SEK'}; // confirmed single delete
const P_BULK_DEL = [
    {base: 'EUR', quote: 'NOK'},
    {base: 'EUR', quote: 'PLN'},
];
const ALL_DISPOSABLE = [P_DETAIL, P_EDIT_DEL, P_SWAP_EDIT, ...P_BULK_REFRESH, P_SINGLE_DEL, ...P_BULK_DEL];

/** Five stored rates per pair, spread across the last three weeks (well inside
 *  the detail page's default 3-month range, so every one renders in the editor). */
const RATE_DATES = [daysAgoIso(3), daysAgoIso(6), daysAgoIso(9), daysAgoIso(12), daysAgoIso(15)];

/** A mock route present before any test — the net's baseline (EUR-USD is seeded). */
let mockRouteBaseline = false;

/**
 * Create (idempotently) a disposable pair: a MOCKFX route + a handful of manual
 * rates. The route upserts on `(base, quote, priority)` and the rates upsert on
 * `(date, base, quote)`, so calling this twice is a no-op update, never an error.
 */
async function createPair(req: APIRequestContext, base: string, quote: string, dates: string[] = RATE_DATES): Promise<void> {
    const rr = await req.post(`${API}/fx/providers/routes`, {
        data: [{base, quote, priority: 1, chain_steps: [{from: base, to: quote, provider: 'MOCKFX'}]}],
    });
    expect(rr.ok(), `create route ${base}-${quote}: ${rr.status()} ${await rr.text()}`).toBeTruthy();
    if (dates.length > 0) {
        const rt = await req.post(`${API}/fx/currencies/rate`, {
            data: dates.map((date, i) => ({date, base, quote, rate: 1.1 + i * 0.01, source: 'MANUAL'})),
        });
        expect(rt.ok(), `upsert rates ${base}-${quote}: ${rt.status()} ${await rt.text()}`).toBeTruthy();
    }
}

/** Delete a disposable pair's route and all its rates. Idempotent — a pair a test
 *  already removed answers with zero deletions, which is fine. */
async function deletePair(req: APIRequestContext, base: string, quote: string): Promise<void> {
    await req.delete(`${API}/fx/providers/routes`, {data: [{base, quote}]}).catch(() => {});
    await req.delete(`${API}/fx/currencies/rate`, {data: [{from: base, to: quote, delete_all: true}]}).catch(() => {});
}

/** The stored rate dates for a pair, read straight from the backup stream. */
async function ratesDates(req: APIRequestContext, base: string, quote: string): Promise<string[]> {
    const res = await req.get(`${API}/backup/fx/${base}/${quote}/rates?format=json`);
    if (!res.ok()) return [];
    const body = (await res.json()) as {rows: Array<{date: string}>};
    return body.rows.map((r) => r.date);
}

/** Switch the list page into table view and wait for a specific disposable row to
 *  render — the FxTable + its checkboxes only exist in list view. */
async function openListViewWithRow(page: import('@playwright/test').Page, slug: string): Promise<void> {
    await goToFxPage(page);
    await page.getByTestId('view-mode-list').click();
    await expect(page.locator(`[data-row-id="${slug}"]`)).toBeVisible({timeout: 8_000});
}

test.beforeEach(async ({page}) => {
    await login(page, TEST_USER);
});

test.beforeAll(async () => {
    const api = await apiLogin();
    if (!api) throw new Error('fx-destructive: could not log in an API context for setup');
    try {
        // Baseline for the net: a seeded mock route we must never destroy.
        const res = await api.get(`${API}/fx/providers/routes`);
        if (res.ok()) {
            const items = ((await res.json()) as {items?: Array<{base: string; quote: string}>}).items ?? [];
            mockRouteBaseline = items.some((r) => r.base === 'EUR' && r.quote === 'USD');
        }
        // Clean slate, then create every disposable pair up front.
        for (const p of ALL_DISPOSABLE) await deletePair(api, p.base, p.quote);
        for (const p of ALL_DISPOSABLE) await createPair(api, p.base, p.quote);
    } finally {
        await api.dispose();
    }
});

// ── Detail page ──────────────────────────────────────────────────────────────

test('detail: swap direction navigates to the reversed slug', async ({page}) => {
    await goToFxDetailPage(page, `${P_DETAIL.base}-${P_DETAIL.quote}`);

    // Not editing → `handleSwapDirection` goes straight to `doSwap`, which
    // replaceState-navigates to the display-reversed slug (EUR-NZD → NZD-EUR).
    await page.getByTestId('fx-detail-swap-btn').click();
    await page.waitForURL(new RegExp(`/fx/${P_DETAIL.quote}-${P_DETAIL.base}`), {timeout: 8_000});
    await expect(page.getByTestId('fx-detail-page')).toBeVisible();
});

test('detail: signals / aesthetics / measures panels toggle', async ({page}) => {
    await goToFxDetailPage(page, `${P_DETAIL.base}-${P_DETAIL.quote}`);

    // Signals: the toggle owns an aria-expanded contract — assert the flip, no
    // assumption about the initial state.
    const signals = page.getByTestId('fx-detail-signals-toggle');
    const sigBefore = await signals.getAttribute('aria-expanded');
    await signals.click();
    await expect(signals).toHaveAttribute('aria-expanded', sigBefore === 'true' ? 'false' : 'true');

    // Aesthetics: no aria-expanded, so assert the panel it gates appears then goes.
    const aesthetics = page.getByTestId('fx-detail-aesthetics-toggle');
    await aesthetics.click();
    await expect(page.getByTestId('fx-detail-aesthetics-panel')).toBeVisible();
    await aesthetics.click();
    await expect(page.getByTestId('fx-detail-aesthetics-panel')).toBeHidden();

    // Measures: the panel is always in the DOM but `hidden` when off, so visibility
    // is the honest signal.
    const measures = page.getByTestId('fx-detail-measures-toggle');
    await measures.click();
    await expect(page.getByTestId('fx-detail-measures-panel')).toBeVisible();
});

test('detail: refresh reloads the chart without error', async ({page}) => {
    await goToFxDetailPage(page, `${P_DETAIL.base}-${P_DETAIL.quote}`);

    await page.getByTestId('fx-detail-refresh-btn').click();
    // `handleRefresh` raises then lowers the page's data-busy; settle on it.
    await waitForSettled(page.getByTestId('fx-detail-page'));
    await expect(page.getByTestId('fx-detail-page')).toBeVisible();
});

test('detail: provider modal opens and closes', async ({page}) => {
    await goToFxDetailPage(page, `${P_DETAIL.base}-${P_DETAIL.quote}`);

    await page.getByTestId('fx-detail-provider-btn').click();
    await expect(page.getByTestId('fx-add-pair-modal')).toBeVisible({timeout: 5_000});

    // Escape routes through ModalBase → onRequestClose → showProviderModal = false.
    await page.keyboard.press('Escape');
    await expect(page.getByTestId('fx-add-pair-modal')).toBeHidden();
});

test('detail: sync modal opens and closes (MOCKFX route enables sync)', async ({page}) => {
    await goToFxDetailPage(page, `${P_DETAIL.base}-${P_DETAIL.quote}`);

    // The MOCKFX route means providers.length > 0 → isManualOnly false → button
    // enabled. Opening + closing the modal covers `handleSync` without a provider
    // round-trip.
    const syncBtn = page.getByTestId('fx-detail-sync-btn');
    await expect(syncBtn).toBeEnabled();
    await syncBtn.click();

    await expect(page.getByTestId('page-sync-modal')).toBeVisible({timeout: 5_000});
    await expect(page.getByTestId('sync-modal-body')).toBeVisible();
    await page.getByTestId('sync-modal-close').click();
    await expect(page.getByTestId('page-sync-modal')).toBeHidden();
});

test('detail: rate editor deletes a single rate and persists it', async ({page}) => {
    const {base, quote} = P_EDIT_DEL;
    const victim = RATE_DATES[2]; // a middle date, safely inside the range

    // Precondition, verified not inferred: the rate we are about to delete exists.
    expect(await ratesDates(page.request, base, quote)).toContain(victim);

    await goToFxDetailPage(page, `${base}-${quote}`);

    // Open the manual editor and delete exactly the victim row.
    await page.getByTestId('fx-detail-edit-btn').click();
    await expect(page.getByTestId('fx-detail-editor-panel')).toBeVisible({timeout: 5_000});
    await expect(page.getByTestId('data-editor-root')).toBeVisible();

    const kebab = page.getByTestId(`row-actions-${victim}`);
    await expect(kebab).toBeVisible({timeout: 5_000});
    await kebab.click();
    await expect(page.getByTestId('context-menu')).toBeVisible();
    await page.getByTestId('context-menu-action-delete').click();

    // The row is now marked deleted → editor dirty → Save enabled.
    const save = page.getByTestId('fx-editor-save-btn');
    await expect(save).toBeEnabled();
    await save.click();

    // `handleSave` toasts on success, then `onsave` closes the panel. Assert the
    // variant (never the translated text) and the panel's disappearance.
    await expect(page.getByTestId('toast-success')).toBeVisible({timeout: 8_000});
    await expect(page.getByTestId('fx-detail-editor-panel')).toHaveCount(0);

    // The real proof: the backend no longer has that date, and the others survive.
    const after = await ratesDates(page.request, base, quote);
    expect(after).not.toContain(victim);
    expect(after).toContain(RATE_DATES[0]);
});

test('detail: swap while editing asks to confirm — cancel keeps editing, confirm swaps', async ({page}) => {
    const {base, quote} = P_SWAP_EDIT;
    await goToFxDetailPage(page, `${base}-${quote}`);

    // Make the editor dirty (delete a row, do NOT save) so a swap must ask first.
    await page.getByTestId('fx-detail-edit-btn').click();
    await expect(page.getByTestId('fx-detail-editor-panel')).toBeVisible({timeout: 5_000});
    await page.getByTestId(`row-actions-${RATE_DATES[1]}`).click();
    await expect(page.getByTestId('context-menu')).toBeVisible();
    await page.getByTestId('context-menu-action-delete').click();
    await expect(page.getByTestId('fx-editor-save-btn')).toBeEnabled();

    // Cancel branch: the confirm appears, we decline, nothing navigates, still editing.
    await page.getByTestId('fx-detail-swap-btn').click();
    await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: 5_000});
    await page.getByTestId('confirm-modal-cancel').click();
    await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);
    await expect(page).toHaveURL(new RegExp(`/fx/${base}-${quote}`));
    await expect(page.getByTestId('fx-detail-editor-panel')).toBeVisible();

    // Confirm branch: still dirty, so a second swap re-asks; this time we accept
    // and `doSwap` navigates to the reversed slug (the unsaved edit is discarded).
    await page.getByTestId('fx-detail-swap-btn').click();
    await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: 5_000});
    await page.getByTestId('confirm-modal-confirm').click();
    await page.waitForURL(new RegExp(`/fx/${quote}-${base}`), {timeout: 8_000});
});

// ── List page ────────────────────────────────────────────────────────────────

test('list: bulk refresh clears the selection toolbar', async ({page}) => {
    const slugs = P_BULK_REFRESH.map((p) => `${p.base}-${p.quote}`);
    await openListViewWithRow(page, slugs[0]);

    for (const slug of slugs) {
        await expect(page.locator(`[data-row-id="${slug}"]`)).toBeVisible();
        await page.getByTestId(`dt-row-checkbox-${slug}`).click();
    }

    const toolbar = page.getByTestId('selection-toolbar');
    await expect(toolbar).toHaveAttribute('data-selected-count', String(slugs.length));

    // `handleBulkRefreshFx` re-fetches each selected pair then clears the selection,
    // so the toolbar disappears — the observable end state, no clock wait.
    await page.getByTestId('toolbar-action-refresh').click();
    await expect(toolbar).toHaveCount(0);

    // Non-destructive: both rows still exist afterward.
    for (const slug of slugs) await expect(page.locator(`[data-row-id="${slug}"]`)).toBeVisible();
});

test('list: single pair delete — confirmed removes exactly that row', async ({page}) => {
    const {base, quote} = P_SINGLE_DEL;
    const slug = `${base}-${quote}`;
    await openListViewWithRow(page, slug);

    const row = page.locator(`[data-row-id="${slug}"]`);
    await expect(row).toHaveCount(1);

    // row kebab → delete → the page's ConfirmModal (FxTable delete has no confirm
    // of its own; the page owns it).
    await page.getByTestId(`row-actions-${slug}`).click();
    await expect(page.getByTestId('context-menu')).toBeVisible();
    await page.getByTestId('context-menu-action-delete').click();

    const confirm = page.getByTestId('confirm-modal-confirm');
    await expect(confirm).toBeVisible({timeout: 5_000});
    await confirm.click();

    // `confirmDelete` deletes routes + rates, toasts, and filters the row out.
    await expect(page.getByTestId('toast-success')).toBeVisible({timeout: 8_000});
    await expect(row).toHaveCount(0);

    // Proof the shared tables really lost it — no route, no rates.
    expect(await ratesDates(page.request, base, quote)).toHaveLength(0);
});

test('list: bulk pair delete — confirmed shows results and removes the rows', async ({page}) => {
    const slugs = P_BULK_DEL.map((p) => `${p.base}-${p.quote}`);
    await openListViewWithRow(page, slugs[0]);

    for (const slug of slugs) {
        await expect(page.locator(`[data-row-id="${slug}"]`)).toBeVisible();
        await page.getByTestId(`dt-row-checkbox-${slug}`).click();
    }
    await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', String(slugs.length));

    await page.getByTestId('toolbar-action-delete').click();
    const confirm = page.getByTestId('confirm-modal-confirm');
    await expect(confirm).toBeVisible({timeout: 5_000});
    await confirm.click();

    // `confirmBulkDelete` keeps the modal open in *results* mode (a per-pair ✅/❌
    // list) — the footer becomes a single Close. Its presence is the success signal.
    const close = page.getByTestId('confirm-modal-close');
    await expect(close).toBeVisible({timeout: 8_000});
    await close.click();

    for (const slug of slugs) await expect(page.locator(`[data-row-id="${slug}"]`)).toHaveCount(0);
    // A mock pair the test never selected is still present — deletion was scoped.
    await expect(page.locator('[data-row-id="EUR-USD"]')).toBeVisible();
});

test.afterAll(async () => {
    const api = await apiLogin();
    if (!api) return;
    try {
        // 1. Precise cleanup: delete only the disposable pairs this file created.
        for (const p of ALL_DISPOSABLE) await deletePair(api, p.base, p.quote);

        // 2. The net. Only if a *mock* route vanished (it never should — we only
        //    ever touch disposables) and only when no sibling worker could be
        //    mid-test, because `--force` unlinks the whole database.
        if (REPOPULATE_ALLOWED && mockRouteBaseline) {
            const res = await api.get(`${API}/fx/providers/routes`);
            if (res.ok()) {
                const items = ((await res.json()) as {items?: Array<{base: string; quote: string}>}).items ?? [];
                const stillThere = items.some((r) => r.base === 'EUR' && r.quote === 'USD');
                if (!stillThere) {
                    await api.dispose();
                    await repopulateMockData();
                    return;
                }
            }
        }
    } finally {
        await api.dispose().catch(() => {});
    }
});
