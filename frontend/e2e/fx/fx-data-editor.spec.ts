/**
 * FX Data Editor — E2E Tests
 *
 * Tests the data editor section in the FX detail page, and what it says when the server
 * refuses a save, whole or in part (X-R46): the server's facts, never Axios's sentence.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated with EUR-USD data
 */

import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, setLanguage} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {t} from '../fixtures/i18n-data';
import {daysAgoIso} from '../fixtures/dates';
import {goToFxDetailPage} from './fx-helpers';

test.describe('FX Data Editor', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Open editor via edit button
    // ========================================================================
    test('can open data editor', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-edit-btn').click();
        await expect(page.getByTestId('fx-detail-editor-panel')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Data table has rows
    // ========================================================================
    test('data editor table has rows', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-edit-btn').click();
        const editorPanel = page.getByTestId('fx-detail-editor-panel');
        await expect(editorPanel).toBeVisible();

        // Look for table rows within the editor
        const rows = editorPanel.locator('table tbody tr, [data-testid*="editor-row"]');
        const count = await rows.count();
        expect(count).toBeGreaterThan(0);
    });

    // ========================================================================
    // Test 7: Close editor (cancel) resets state
    // ========================================================================
    test('closing editor hides the panel', async ({page}) => {
        await goToFxDetailPage(page, 'EUR-USD');
        await page.getByTestId('fx-detail-edit-btn').click();
        await expect(page.getByTestId('fx-detail-editor-panel')).toBeVisible();

        // Click the edit button again to close (toggle)
        await page.getByTestId('fx-detail-edit-btn').click();
        await expect(page.getByTestId('fx-detail-editor-panel')).not.toBeVisible();
    });

    // ========================================================================
    // Test 8: The editor's own buttons and the CSV import title, in Italian
    // ========================================================================
    /**
     * The save/cancel bar under the rate editor is written in English straight
     * into FxDataEditorSection, while the shared data editor already carries its
     * sentences (`dataEditor.save` with the count, `dataEditor.saving`) and
     * `common.cancel` exists. Every expected label is read from it.json, never
     * typed here; the positive control is a label of the same editor that is
     * already the catalogue's, so an English label next to it is a hard-coded one.
     *
     * "Saving" lives only while a save is in flight, so the save is held at the
     * network edge and then refused: the label can be read for as long as the test
     * needs, and the deletion it carries never reaches the shared EUR-USD rates.
     */
    test('words the save/cancel bar and the CSV import title from the active catalogue', async ({page}) => {
        await setLanguage(page, 'it');
        await goToFxDetailPage(page, 'EUR-USD');

        await page.getByTestId('fx-detail-edit-btn').click();
        const panel = page.getByTestId('fx-detail-editor-panel');
        await expect(panel).toBeVisible();

        // Positive control: this editor already takes its toolbar label from it.json.
        const importButton = page.getByTestId('fx-data-import-btn');
        await expect(importButton).toHaveText(t('it', 'dataEditor.importCsv'));

        const save = page.getByTestId('fx-editor-save-btn');
        const cancel = page.getByTestId('fx-editor-cancel-btn');
        const saveLabel = (n: number) => t('it', 'dataEditor.save').replace('{n}', String(n));
        // A label renders with its button and nothing loads in between, so a short
        // wait is honest — and keeps four soft reds inside the test's budget.
        await expect.soft(save, 'save, nothing to save').toHaveText(saveLabel(0), {timeout: 2_000});
        await expect.soft(cancel, 'cancel').toHaveText(t('it', 'common.cancel'), {timeout: 2_000});

        // The CSV import modal opened from the same editor names itself from the catalogue.
        await importButton.click();
        const importModal = page.getByTestId('data-import-modal');
        await expect(importModal).toBeVisible();
        await expect.soft(importModal.getByTestId('data-import-modal-header').getByRole('heading', {level: 2}), 'CSV import title').toHaveText(t('it', 'csvImport.title'), {timeout: 2_000});
        await page.keyboard.press('Escape');
        await expect(importModal).toBeHidden();

        // One row marked for deletion makes the count 1. Any row serves: the mark is
        // local until saved, and the save below never reaches the server.
        const kebab = panel.locator('[data-testid^="row-actions-"]').first();
        await expect(kebab, 'EUR-USD shows no rate in the editor: check populate_mock_data.py').toBeVisible();
        await kebab.click();
        await expect(page.getByTestId('context-menu')).toBeVisible();
        await page.getByTestId('context-menu-action-delete').click();
        await expect(save).toBeEnabled();
        await expect.soft(save, 'save, one change').toHaveText(saveLabel(1), {timeout: 2_000});

        // Hold the save at the network edge, read the in-flight label, then refuse it.
        let release!: () => void;
        const held = new Promise<void>((resolve) => (release = resolve));
        let arrived!: () => void;
        const reached = new Promise<void>((resolve) => (arrived = resolve));
        const rates = '**/api/v1/fx/currencies/rate';
        await page.route(rates, async (route) => {
            if (route.request().method() !== 'DELETE') return route.fallback();
            arrived();
            await held;
            await route.abort();
        });
        try {
            await save.click();
            await reached;
            await expect.soft(save, 'save, in flight').toHaveText(t('it', 'dataEditor.saving'), {timeout: 2_000});
        } finally {
            release();
        }
        // Refused: the save is over and the mark still pending. Nothing to restore —
        // the deletion only ever lived in this page, which the test discards.
        await expect(save).toBeEnabled();
        await page.unroute(rates);
    });

    // ========================================================================
    // What a refused save says (X-R46)
    // ========================================================================
    /**
     * X-R46. The editor mishandled the server's refusals of a save:
     * - refused whole (a 400 or a 422), its banner and its toast showed Axios's generic
     *   `e.message` — «Request failed with status code 422» — instead of what the server
     *   answered: which rate it refused, and why;
     * - taken in part (a 200 with refusals), every rate sent was counted as saved, and the
     *   save was announced as a success.
     *
     * Each test imports its own lines into the editor of the seeded EUR-USD, which it only
     * reads, and answers the rate save (POST) at the network edge with what the server answers
     * to those rates: nothing is written, so nothing needs restoring. The answers have the
     * shapes of the server's coded refusals, and carry the refused day only where the editor
     * must read it (`items`, `rejected`): a day in the editor's words can come from there alone.
     *
     * Read without words: a toast by its variant (`toast-error`, `toast-warning`), the banner by
     * `fx-editor-error`, and their text only for ISO days and for the absence of Axios's
     * sentence, which is English whatever the interface language. FxDataEditorSection does not
     * publish `fx-editor-error` yet: until X-R46 adds it, the banner is red as not found too.
     */
    test.describe('server refusals (X-R46)', () => {
        // A red lists every missing fact at once (soft assertions, two seconds each, behind a
        // barrier): the budget is for that report — green, a test takes a fraction of it.
        test.describe.configure({timeout: 60_000});

        const RATES_URL = '**/api/v1/fx/currencies/rate';
        const RATES_PATH = '/api/v1/fx/currencies/rate';
        /** Axios's own sentence for any answer outside 2xx: English, and none of the server's facts in it. */
        const AXIOS_GENERIC = 'Request failed with status code';
        /** The first day a rate may carry (`stored_date_bounds()`); the last, in the answers below, is tomorrow. */
        const MIN_DATE = '1900-01-01';

        /** One rate as the editor sends it. */
        type SentRate = {base: string; quote: string; date: string; rate: number | string};

        /** The editor of EUR-USD, with `lines` (`[day, rate]`, written EUR>USD) imported through its CSV modal. */
        async function editorWithImported(page: Page, lines: Array<[string, string]>): Promise<Locator> {
            await goToFxDetailPage(page, 'EUR-USD');
            await page.getByTestId('fx-detail-edit-btn').click();
            const panel = page.getByTestId('fx-detail-editor-panel');
            await expect(panel).toBeVisible();
            await panel.getByTestId('fx-data-import-btn').click();
            const modal = page.getByTestId('data-import-modal');
            await expect(modal).toBeVisible();
            // The header names the page's own direction: the rates go in as written, never inverted.
            const csv = ['date;EUR>USD', ...lines.map(([day, rate]) => `${day};${rate}`)].join('\n');
            const input = modal.getByTestId('csv-editor-input');
            await input.fill(csv);
            await expect(input).toHaveValue(csv);
            const confirm = modal.getByTestId('data-import-confirm');
            await expect(confirm, 'every line is a valid rate').toHaveAttribute('data-valid-rows', String(lines.length));
            await confirm.click();
            await expect(modal).toBeHidden();
            return panel;
        }

        /**
         * Answer every rate save (POST) of the page with `answer(sent)` — the server's answer to the
         * rates sent — and keep what each save sent. No save reaches the server; any other method does.
         */
        async function answerSaves(page: Page, answer: (sent: SentRate[]) => {status: number; json: unknown}): Promise<SentRate[][]> {
            const saves: SentRate[][] = [];
            await page.route(RATES_URL, async (route) => {
                if (route.request().method() !== 'POST') {
                    await route.fallback();
                    return;
                }
                const sent = route.request().postDataJSON() as SentRate[];
                saves.push(sent);
                await route.fulfill(answer(sent));
            });
            return saves;
        }

        /** The days each save sent, sorted. */
        function sentDays(saves: SentRate[][]): string[][] {
            return saves.map((sent) => sent.map((rate) => rate.date).sort());
        }

        /** Where `day` sits in what was sent: the `index` by which the server names a rate. */
        function indexOf(sent: SentRate[], day: string): number {
            return sent.findIndex((rate) => rate.date === day);
        }

        /** Click Save, and return the status of the answer once the save has been answered. */
        async function save(page: Page, panel: Locator): Promise<number> {
            const saveButton = panel.getByTestId('fx-editor-save-btn');
            await expect(saveButton).toBeEnabled();
            const answered = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === RATES_PATH, {timeout: 15_000});
            await saveButton.click();
            return (await answered).status();
        }

        /**
         * `told` — a toast, or the banner — is shown, holds every one of `facts` and not Axios's
         * sentence. Soft, so a red lists every missing fact; the wait is short, the text being
         * final once `told` is shown.
         */
        async function expectTold(told: Locator, what: string, facts: string[]): Promise<void> {
            await expect(told, `${what} is shown`).toBeVisible();
            for (const fact of facts) await expect.soft(told, `${what} holds ${fact}`).toContainText(fact, {timeout: 2_000});
            await expect.soft(told, `${what} says what the server said, not Axios's sentence`).not.toContainText(AXIOS_GENERIC, {timeout: 2_000});
        }

        test("a rate dated after the last storable day is told refused with that day and the bounds, not with Axios's sentence", async ({page}) => {
            // Pins: a 422 `date_out_of_range` is told, by the error toast and by the banner, with
            // the day refused and the bounds the server gave, in ISO; the editor stays open on the
            // rate, ready to be corrected.
            // Red on HEAD: the toast reads «… Request failed with status code 422», and the banner,
            // which holds the same sentence, publishes no `fx-editor-error`.
            const refused = daysAgoIso(-30);
            const max = daysAgoIso(-1);
            const panel = await editorWithImported(page, [[refused, '1.0823']]);
            // The server's answer to a day after tomorrow (X-R65): the whole save refused. Its
            // message says the bounds, never the day — that is in `items`.
            const saves = await answerSaves(page, (sent) => ({
                status: 422,
                json: {detail: {code: 'date_out_of_range', message: `Dates must lie between ${MIN_DATE} and ${max}: 1 does not`, params: {min: MIN_DATE, max}, items: [{index: indexOf(sent, refused), date: refused}], count: 1}},
            }));

            expect(await save(page, panel), 'the save reached the refusal').toBe(422);
            expect(sentDays(saves), 'one save, of the imported rate alone').toEqual([[refused]]);

            await expectTold(page.getByTestId('toast-error'), 'the error toast', [refused, MIN_DATE]);
            // Nothing is lost: the editor stays open on the imported rate, ready to save again.
            await expect(panel).toBeVisible();
            await expect(panel.getByTestId('fx-editor-save-btn')).toBeEnabled();
            await expectTold(panel.getByTestId('fx-editor-error'), 'the banner', [refused, MIN_DATE, max]);
        });

        test('a save the server takes in part is told as a warning naming the refused day, not as a success', async ({page}) => {
            // Pins: a 200 whose `rejected` lists a rate is no full success. The editor counts as
            // saved only the `results`, and its toast is a warning naming the day refused, in ISO.
            // Red on HEAD: the answer's refusals are ignored, both rates are counted as saved and
            // the toast is a success.
            // Two days of the page's three-month range, so the save widens nothing. The second rate
            // cannot be stored — 1E-11 is 0 at the column's ten decimal places (X-R38) — and the
            // server keeps the first alone.
            const [kept, refused] = [daysAgoIso(12), daysAgoIso(11)];
            const panel = await editorWithImported(page, [
                [kept, '1.2345'],
                [refused, '0.00000000001'],
            ]);
            // `errors` stays empty: the refusal is told in `rejected` alone.
            const saves = await answerSaves(page, (sent) => ({
                status: 200,
                json: {
                    results: [{success: true, action: 'updated', rate: '1.2345000000', date: kept, base: 'EUR', quote: 'USD'}],
                    success_count: 1,
                    errors: [],
                    rejected: [{index: indexOf(sent, refused), date: refused, reason: 'rate_not_storable'}],
                },
            }));

            expect(await save(page, panel), 'the save was answered').toBe(200);
            expect(sentDays(saves), 'one save, of the two imported rates').toEqual([[kept, refused].sort()]);

            // The save is told by one toast: a warning, one of its two rates being refused, that
            // names the day refused.
            const toast = page.getByTestId(/^toast-(success|warning|error|info)$/);
            await expect(toast, 'the save is told').toBeVisible();
            await expect.soft(toast, 'as a warning, not as a success: one of the two rates was refused').toHaveAttribute('data-testid', 'toast-warning', {timeout: 2_000});
            await expect.soft(toast, `naming the day refused, ${refused}`).toContainText(refused, {timeout: 2_000});
        });

        test("a save the server refuses whole is told with the refused day, not with Axios's sentence", async ({page}) => {
            // Pins: a 400 `fx_rates_refused` — no rate of the save could be stored — is told
            // without Axios's sentence, and the banner names the day of the rate refused, in ISO.
            // Red on HEAD: the toast and the banner read «… Request failed with status code 400»,
            // and the banner publishes no `fx-editor-error`.
            const refused = daysAgoIso(13);
            const panel = await editorWithImported(page, [[refused, '0.00000000001']]);
            // The server's message names the day too (`fx_rate_refusal`); this one stops short of
            // it, or a banner echoing the message would pass for one built from `rejected`.
            const saves = await answerSaves(page, (sent) => ({
                status: 400,
                json: {detail: {code: 'fx_rates_refused', message: 'All rates failed: Rate 0: Validation error: the rate cannot be stored', rejected: [{index: indexOf(sent, refused), date: refused, reason: 'rate_not_storable'}]}},
            }));

            expect(await save(page, panel), 'the save reached the refusal').toBe(400);
            expect(sentDays(saves), 'one save, of the imported rate alone').toEqual([[refused]]);

            await expectTold(page.getByTestId('toast-error'), 'the error toast', []);
            // Nothing is lost: the editor stays open on the imported rate.
            await expect(panel).toBeVisible();
            await expectTold(panel.getByTestId('fx-editor-error'), 'the banner', [refused]);
        });
    });
});
