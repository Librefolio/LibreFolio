// @vitest-environment jsdom
/**
 * AssetTable — the Last Price column stays public under the privacy toggle (Vitest + jsdom).
 *
 * Subject. The Last Price cell renders
 * `formatCurrencyAmountHtml(price, row.currency, {sensitivity: 'public'})`. A market quote is
 * public by rule — the criterion recorded in `utils/privacy/moneyRenderSites.test.ts`: a number
 * is personal when it lets you infer what the user owns, and a quote is the same figure for
 * every user — so its digits must stay visible with privacy on and off. Nothing else protects
 * that marking. The money-render-sites gate enumerates formatter channels and never re-examines
 * a `public` argument, and the formatter's own tests cannot know which call sites are entitled
 * to it. Dropping the argument would hide every quote of the assets list behind the placeholder
 * while every other test stays green.
 *
 * Why a negative control instead of a positive one. The table renders no personal amount —
 * name, usage count, type, currency, quote, percentage deltas, provider — so no cell of the same
 * mount can prove by masking that the toggle reached the table. The proof that these assertions
 * can fail was taken on a scratch copy of AssetTable.svelte with `{sensitivity: 'public'}`
 * removed, aliased over `./AssetTable.svelte` by a throwaway vitest config outside the tracked
 * tree: both tests went red, each at its first privacy-on step — the second one in place, so the
 * table does re-render this cell on the toggle, and a green here means the marking held. To take
 * it again, repeat that swap; never edit the real component for it.
 *
 * Controls. Every step checks the flag and a fresh *personal* call of the same formatter before
 * the cell, so a red names its layer: a flag that did not move, a masking channel that is dead
 * (which would make the public cell clear for the wrong reason), or the cell itself.
 *
 * Selection. The row by `data-row-id`; the cell by its column — the index of
 * `dt-header-lastPrice` among the data headers, matched against the row's `td-data` cells, the
 * structural hook DataTable.test.ts and ExposureTable.test.ts also use. Inside the cell, the
 * parts come from the markup the formatter emits (`.currency-amount`, `.currency-symbol`,
 * `.emoji-flag`, `.currency-code`): the table publishes no per-amount handle, and that markup is
 * the contract every formatted amount in the app shares.
 *
 * Expectations. The clear parts are the formatter's own output with privacy off — the host
 * locale decides the separators — checked once against the digits put in; the currency parts
 * are the values the mocked catalogue below supplies. Nothing here reads translated text.
 *
 * Storage. The shared `$app/environment` mock reports `browser: false`, so `setPrivacyEnabled`
 * moves the in-memory rune and never touches `localStorage`.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';

// The currency catalogue is answered so the cell carries a real symbol and flag, as on the
// assets page. The only other request of this graph, the provider list, resolves to nothing,
// which its loader tolerates (the row is a manual asset and renders no provider icon).
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (property === 'list_currencies_api_v1_utilities_currencies_get') {
                    return vi.fn(async () => ({
                        items: [{code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []}],
                    }));
                }
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {render, screen, setupI18n} from '$test/component';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import {ensureAssetProvidersCached} from '$lib/utils/providerHelpers';
import AssetTable, {type AssetRow} from './AssetTable.svelte';

const CODE = 'EUR';
/** Six distinct digits, and a group separator in most locales. */
const PRICE = 1234.56;

/** One manual asset with a quote and no live update: the cell renders `row.lastPrice`. */
const ROW: AssetRow = {
    id: 7,
    display_name: 'Public quote probe',
    currency: CODE,
    asset_type: 'STOCK',
    provider_code: null,
    active: true,
    lastPrice: PRICE,
};

/** One formatted amount, split into the parts the formatter emits. */
interface MoneyParts {
    amount: string;
    symbol: string | null;
    flag: string | null;
    code: string | null;
}

/** Filled in `beforeAll`, with privacy off: what the cell must show in every state. */
let clear: MoneyParts;

/** The single formatted amount under `root`; anything but exactly one is a markup change to report, not to guess around. */
function partsIn(root: ParentNode, where: string): MoneyParts {
    const amounts = root.querySelectorAll('.currency-amount');
    if (amounts.length !== 1) throw new Error(`${where}: ${amounts.length} .currency-amount elements, expected exactly 1`);
    const text = (selector: string) => root.querySelector(selector)?.textContent?.trim() ?? null;
    return {amount: amounts[0].textContent?.trim() ?? '', symbol: text('.currency-symbol'), flag: text('.emoji-flag'), code: text('.currency-code')};
}

/** The parts of a formatter call's output, parsed off-document. */
function partsOf(html: string): MoneyParts {
    const template = document.createElement('template');
    template.innerHTML = html;
    return partsIn(template.content, 'formatter output');
}

/** The Last Price cell of ROW, located through its column header. */
function priceCell(): HTMLElement {
    const row = document.querySelector<HTMLElement>(`tbody tr[data-row-id="${ROW.id}"]`);
    if (!row) throw new Error(`row ${ROW.id} not rendered`);
    const headers = [...document.querySelectorAll<HTMLElement>('thead th[data-testid^="dt-header-"]')];
    const index = headers.findIndex((header) => header.dataset.testid === 'dt-header-lastPrice');
    if (index < 0) throw new Error('Last Price column not rendered');
    const cells = [...row.querySelectorAll<HTMLElement>('td.td-data')];
    if (cells.length !== headers.length) throw new Error(`${cells.length} data cells for ${headers.length} data headers`);
    return cells[index];
}

/** Mount the table; with both reference caches preloaded, the row is there once effects flush. */
async function mount(): Promise<void> {
    render(AssetTable, {data: [ROW]});
    flushSync();
    await tick();
    expect(screen.getByTestId('dt-header-lastPrice'), 'barrier: the Last Price column is rendered').toBeInTheDocument();
    expect(document.querySelector(`tbody tr[data-row-id="${ROW.id}"]`), `barrier: row ${ROW.id} is rendered`).not.toBeNull();
}

/** Move the flag through the real store, then flush: synchronously, and once more through the microtask the app waits on. */
async function setPrivacy(value: boolean): Promise<void> {
    setPrivacyEnabled(value);
    flushSync();
    await tick();
}

/** The subject, after two controls that name the failing layer. */
function expectPublicQuote(step: string, privacyOn: boolean): void {
    expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(privacyOn);
    expect(partsOf(formatCurrencyAmountHtml(PRICE, CODE)).amount, `${step} — control: a personal amount through the same formatter follows the flag`).toBe(privacyOn ? PRIVACY_PLACEHOLDER : clear.amount);

    const cell = partsIn(priceCell(), `${step} — Last Price cell`);
    expect(cell.amount, `${step} — the quote shows its digits`).toBe(clear.amount);
    expect(cell.amount, `${step} — the quote is not the placeholder`).not.toContain(PRIVACY_PLACEHOLDER);
    expect(cell, `${step} — digits and currency marker (symbol, flag, code)`).toEqual(clear);
}

beforeAll(async () => {
    await setupI18n();
    // Preloaded so the mount makes no request: AssetTable's own calls return at once, and no late
    // cache resolution re-renders the table in the middle of a step.
    await ensureCurrenciesLoaded('en');
    await ensureAssetProvidersCached();
    // Control: the catalogue is loaded, so the cell carries the real symbol and flag.
    expect(getCurrencyInfo(CODE).symbol).toBe('€');

    setPrivacyEnabled(false);
    clear = partsOf(formatCurrencyAmountHtml(PRICE, CODE, {sensitivity: 'public'}));
    // The clear expectation is the formatter's own output: check once that it carries the digits
    // put in and the full currency marker, or "shows its digits" would compare like with like.
    expect(clear.amount.replace(/\D/g, '')).toBe('123456');
    expect(clear).toEqual({amount: clear.amount, symbol: '€', flag: '🇪🇺', code: CODE});
});

afterEach(() => {
    // Module-level flag: a leftover `true` would mount the next table masked.
    setPrivacyEnabled(false);
});

describe('AssetTable — Last Price is public under privacy', () => {
    it('mounted with privacy on, then off and on again in place: the quote keeps its digits and currency', async () => {
        await setPrivacy(true);
        await mount();
        expectPublicQuote('mount, privacy on', true);

        await setPrivacy(false);
        expectPublicQuote('on → off', false);

        await setPrivacy(true);
        expectPublicQuote('off → on', true);
    });

    it('mounted with privacy off, then on and off again in place: the quote never masks', async () => {
        await mount();
        expectPublicQuote('mount, privacy off', false);

        await setPrivacy(true);
        expectPublicQuote('off → on', true);

        await setPrivacy(false);
        expectPublicQuote('on → off', false);
    });
});
