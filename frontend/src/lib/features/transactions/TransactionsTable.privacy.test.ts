// @vitest-environment jsdom
/**
 * TransactionsTable — the linked asset event's value under the global privacy toggle.
 * Component test (Vitest + jsdom), workstream J (privacy), checkpoint C6.
 *
 * The rule, developer decision D5′-c: a UNIT value is `public`, a TOTAL is `personal`. An asset
 * EVENT describes the asset, not the portfolio — backend/app/db/models.py, class AssetEvent:
 * «Events are NOT transactions — they describe what happens to the asset globally, not what
 * happens in a user's portfolio». Its value (a dividend per share, a price adjustment) is the
 * same for every holder, so it is public, as EventCreateMiniModal's success toast already is.
 * A transaction linked to an event shows that value in its Links column, in two places, both
 * built by `eventTooltipText`: the `aria-label` of the event dot and the tooltip the dot opens
 * (TxLinksCell's `eventTooltip` prop). Both must keep their digits with privacy on.
 *
 * Positive control, in the same mount and through the same toggle: the transaction's own cash
 * amount is a TOTAL — money the user moved — so it must be masked with privacy on and clear
 * with privacy off. Without it, "the event value stays visible" would be just as true of a table
 * that never re-rendered on the toggle. A second personal control sits in the same Links
 * column: the tooltip of a linked FX conversion names the two cash amounts of the pair
 * (`fmtCash`), which stay masked — a fix that made the whole column public is caught there.
 *
 * How the two tests tell a regression apart:
 *   - an event value left `personal` fails the first test at its first toggle (off → on) and the
 *     second at mount;
 *   - a table that stops re-rendering on the toggle fails the positive control, never the
 *     subject — so a red on the subject with green controls is the classification and nothing
 *     else.
 * Every step checks, in this order, the flag, a fresh call to the formatter the label uses, the
 * two personal controls, then the subject, so a red names the layer that failed.
 *
 * Selection. Rows by `tr[data-row-id="tx-<id>"]` (DataTable's row handle) and cells by the
 * handles the table itself publishes: `tx-cash-cell-<id>`, `tx-event-dot-<id>`,
 * `tx-link-icon-<id>`. The tooltip is opened through the keyboard (Enter on its trigger), which
 * opens it at once — a click on the dot is swallowed by the table's capture-phase handler by
 * design, and a hover opens only after a delay. Its trigger is a toggle, so it is pressed only
 * while no tooltip is open. The Tooltip portals its body to `document.body`, so the body is
 * found as the one open tooltip of the document: nothing else here opens one, and the event
 * date it must carry proves it is the event's.
 *
 * Nothing here reads translated text. The event label's first line is "<emoji> <translated type
 * name> · <date>": only the date is asserted there, as a control that the label is the event's
 * own and not the "linked event" fallback. The amount is read from the line that names the
 * event's currency. The FX tooltip's sentence is translated too, so only the amount pair it
 * carries is asserted.
 *
 * Expectations. Unmasked strings come from the formatters themselves with privacy off —
 * `toLocaleString(undefined, …)` follows the host locale, so a frozen literal would turn a de-DE
 * runner red — and each is checked once against the digits put in. Masked strings are literals:
 * a placeholder has no locale.
 *
 * Storage. The shared `$app/environment` mock reports `browser: false`, so the privacy store
 * keeps the flag in memory and never touches `localStorage`; DataTable's layout preferences
 * are try/catch-guarded and fall back to the default layout, every column visible.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';

// The requests this graph makes are the reference catalogues. The currency one is answered so
// every amount carries a real symbol and flag, as on the page; the asset list is empty, so the
// asset cell falls back to `#<id>`. Every other method is inert — the broker icon never asks,
// because the broker below carries a portal URL.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (property === 'list_currencies_api_v1_utilities_currencies_get') {
                    return vi.fn(async () => ({
                        items: [
                            {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []},
                            {code: 'USD', name: 'US Dollar', symbol: '$', flag_emoji: '🇺🇸', country_codes: ['US'], country_names: ['United States']},
                        ],
                    }));
                }
                if (property === 'list_assets_api_v1_assets_query_get') {
                    return vi.fn(async () => []);
                }
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {fireEvent, render, screen, setupI18n} from '$test/component';
import {isPrivacyEnabled, setPrivacyEnabled, togglePrivacy} from '$lib/stores/app/privacyStore.svelte';
import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {formatCurrencyAmountHtml, formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import TransactionsTable from './TransactionsTable.svelte';
import type {AssetEvent, TXReadItem} from './types';

const P = PRIVACY_PLACEHOLDER;

const BROKER = {
    id: 31,
    name: 'C6 probe broker',
    // Any icon field keeps BrokerIcon off the network: it does not hydrate the broker from the API.
    portal_url: 'https://broker.example.com',
    icon_url: null,
    default_import_plugin: null,
};

/** The asset event: a dividend of 1.25 USD per share, the same for every holder of asset 41. */
const EVENT: AssetEvent = {id: 9101, asset_id: 41, type: 'DIVIDEND', date: '2026-03-06', value: '1.25', currency: 'USD', is_auto: false, notes: null};

/** The user's dividend transaction, linked to that event: 43.21 EUR credited to the broker. */
const DIVIDEND_TX: TXReadItem = {
    id: 8101,
    broker_id: BROKER.id,
    asset_id: EVENT.asset_id,
    type: 'DIVIDEND',
    date: '2026-03-10',
    quantity: '0',
    cash: {code: 'EUR', amount: '43.21'},
    related_transaction_id: null,
    asset_event_id: EVENT.id,
    tags: [],
    description: null,
};

/** A linked FX conversion on the same broker: 100.00 EUR given, 109.00 USD received. */
const FX_GIVER: TXReadItem = {
    id: 8102,
    broker_id: BROKER.id,
    asset_id: null,
    type: 'FX_CONVERSION',
    date: '2026-03-12',
    quantity: '0',
    cash: {code: 'EUR', amount: '-100.00'},
    related_transaction_id: 8103,
    asset_event_id: null,
    tags: [],
    description: null,
};
const FX_RECEIVER: TXReadItem = {...FX_GIVER, id: 8103, cash: {code: 'USD', amount: '109.00'}, related_transaction_id: FX_GIVER.id};

/** Filled in `beforeAll`, once the currency cache is loaded, with privacy off. */
let eventValueClear = '';
let cashClear = '';
let fxPairClear = '';
const CASH_MASKED = `+${P} € 🇪🇺 EUR`;
const EVENT_VALUE_MASKED = `${P} $ 🇺🇸 USD`;
const FX_PAIR_MASKED = `${P} € 🇪🇺 EUR → ${P} $ 🇺🇸 USD`;

/** Text as a reader sees it: whitespace runs collapsed, surrounding blanks trimmed. */
function norm(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** What an HTML-formatted amount reads as once rendered. */
function readHtml(html: string): string {
    const host = document.createElement('span');
    host.innerHTML = html;
    return norm(host.textContent);
}

/**
 * The line of an event label that names the event's currency — the amount line — normalised.
 * The first line (emoji, translated type name, date) never names it, and this event has no notes.
 */
function eventAmountLine(label: string): string {
    const lines = label.split('\n').filter((line) => line.includes(EVENT.currency));
    if (lines.length !== 1) throw new Error(`expected exactly one line naming ${EVENT.currency} in the event label, found ${lines.length}: ${JSON.stringify(label)}`);
    return norm(lines[0]);
}

function mount(): void {
    // The tooltip body lives in document.body, outside the component: prove no earlier test left one open.
    expect(openTooltips(), 'no tooltip left open before mounting').toHaveLength(0);
    render(TransactionsTable, {
        mainRows: [structuredClone(DIVIDEND_TX), structuredClone(FX_GIVER), structuredClone(FX_RECEIVER)],
        partnerRows: [],
        brokers: [{...BROKER}],
        eventTooltipMap: new Map([[EVENT.id, {...EVENT}]]),
    });
}

function rowEl(txId: number): HTMLElement {
    const el = document.querySelector<HTMLElement>(`tbody tr[data-row-id="tx-${txId}"]`);
    if (!el) throw new Error(`row tx-${txId} not rendered`);
    return el;
}

/** Barrier: the three rows are rendered, with the handles every step reads. */
async function mounted(): Promise<void> {
    await screen.findByTestId(`tx-event-dot-${DIVIDEND_TX.id}`);
    for (const tx of [DIVIDEND_TX, FX_GIVER, FX_RECEIVER]) rowEl(tx.id);
    screen.getByTestId(`tx-cash-cell-${DIVIDEND_TX.id}`);
    screen.getByTestId(`tx-link-icon-${FX_GIVER.id}`);
}

function eventDot(): HTMLElement {
    return screen.getByTestId(`tx-event-dot-${DIVIDEND_TX.id}`);
}

/**
 * The open tooltip bodies, wherever they render: the Tooltip portals its body to
 * `document.body` to escape the row's stacking context, so it is not inside the row.
 */
function openTooltips(): HTMLElement[] {
    return screen.queryAllByTestId('tooltip-content');
}

/**
 * The event dot's tooltip, opened if it is not open yet. Its trigger toggles, so it is pressed
 * only while no tooltip is open; Enter opens it at once (a hover would open it after a delay).
 * Nothing else in these tests opens a tooltip, so the one open body is the event's — and the
 * event-date control in `expectStep` checks that it is.
 */
async function openEventTooltip(): Promise<HTMLElement> {
    if (openTooltips().length === 0) {
        const trigger = eventDot().closest<HTMLElement>('[role="button"]');
        if (!trigger) throw new Error('the event dot sits in no tooltip trigger');
        await fireEvent.keyDown(trigger, {key: 'Enter'});
    }
    const bodies = openTooltips();
    if (bodies.length !== 1) throw new Error(`${bodies.length} tooltips open, expected exactly the event dot's`);
    return bodies[0];
}

/**
 * Flip the flag through the store's own toggle — the call the header's PrivacyToggle makes —
 * then flush: synchronously, and once more through the microtask the app itself waits on.
 */
async function togglePrivacyInPlace(): Promise<void> {
    togglePrivacy();
    flushSync();
    await tick();
}

/** One step: controls first, so a red names its layer; the subject last. */
async function expectStep(step: string, privacyOn: boolean): Promise<void> {
    // Layer controls: the flag moved, and the formatter the event label uses follows it for a personal amount.
    expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(privacyOn);
    expect(norm(formatCurrencyAmountPlain(Number(EVENT.value), EVENT.currency)), `${step} — control: a personal amount through the label's formatter`).toBe(privacyOn ? EVENT_VALUE_MASKED : eventValueClear);

    // Positive control in the table itself: the transaction's cash amount is a TOTAL, personal.
    const cash = norm(screen.getByTestId(`tx-cash-cell-${DIVIDEND_TX.id}`).textContent);
    expect(cash, `${step} — positive control: the cash amount of tx #${DIVIDEND_TX.id} (personal) ${privacyOn ? 'is masked' : 'is in the clear'}`).toBe(privacyOn ? CASH_MASKED : cashClear);
    if (privacyOn) expect(cash, `${step} — positive control: the masked cash shows no digit`).not.toMatch(/\d/);

    // Second personal control, same column: the FX pair tooltip's two cash amounts.
    const fxLabel = norm(screen.getByTestId(`tx-link-icon-${FX_GIVER.id}`).getAttribute('aria-label'));
    expect(fxLabel, `${step} — personal control: the linked FX pair's cash amounts ${privacyOn ? 'are masked' : 'are in the clear'}`).toContain(privacyOn ? FX_PAIR_MASKED : fxPairClear);
    if (privacyOn) expect(fxLabel, `${step} — personal control: the FX pair tooltip shows no digit`).not.toMatch(/\d/);

    // The subject: the event value is public, in the dot's aria-label and in the tooltip it opens.
    const ariaLabel = eventDot().getAttribute('aria-label') ?? '';
    const tooltipText = (await openEventTooltip()).textContent ?? '';
    expect(ariaLabel, `${step} — control: the dot's aria-label is the event's own (it carries the event date)`).toContain(EVENT.date);
    expect(tooltipText, `${step} — control: the tooltip is the event's own (it carries the event date)`).toContain(EVENT.date);
    expect({ariaLabel: eventAmountLine(ariaLabel), tooltip: eventAmountLine(tooltipText)}, `${step} — the linked asset event's value is public (asset events are not portfolio money): digits and currency as with privacy off`).toEqual({ariaLabel: eventValueClear, tooltip: eventValueClear});
    expect(ariaLabel, `${step} — no placeholder in the event dot's aria-label`).not.toContain(P);
    expect(tooltipText, `${step} — no placeholder in the event tooltip`).not.toContain(P);
}

beforeAll(async () => {
    await setupI18n();
    await ensureCurrenciesLoaded('en');
    // Control: the cache is really populated, so every amount carries the symbol and flag.
    expect(getCurrencyInfo('USD').symbol).toBe('$');

    setPrivacyEnabled(false);
    eventValueClear = norm(formatCurrencyAmountPlain(Number(EVENT.value), EVENT.currency, {sensitivity: 'public'}));
    cashClear = readHtml(formatCurrencyAmountHtml(Number(DIVIDEND_TX.cash!.amount), DIVIDEND_TX.cash!.code, {showSign: true}));
    fxPairClear = `${norm(formatCurrencyAmountPlain(100, 'EUR'))} → ${norm(formatCurrencyAmountPlain(109, 'USD'))}`;

    // The clear expectations are the formatters' own output, so check once that they carry the
    // digits and currencies put in: a formatter masking unconditionally would otherwise make
    // "as with privacy off" compare the placeholder with itself.
    const digits = (text: string): string => text.replace(/\D/g, '');
    expect(digits(eventValueClear)).toBe('125');
    expect(eventValueClear).toMatch(/USD$/);
    expect(digits(cashClear)).toBe('4321');
    expect(cashClear).toMatch(/^\+.*EUR$/);
    expect(digits(fxPairClear)).toBe('1000010900');
    for (const clear of [eventValueClear, cashClear, fxPairClear]) expect(clear).not.toContain(P);
});

afterEach(() => {
    // The flag is module-level state shared by every test in this file: a leftover `true`
    // would mount the next table masked.
    setPrivacyEnabled(false);
});

describe('TransactionsTable — the linked asset event value is public, the cash stays personal (D5′-c)', () => {
    it('mounted in the clear: keeps the event value in the dot label and tooltip when privacy turns on in place, while the cash amount masks, and both read as before once it turns off', async () => {
        mount();
        await mounted();
        await expectStep('mount, privacy off', false);

        await togglePrivacyInPlace();
        await expectStep('off → on', true);

        await togglePrivacyInPlace();
        await expectStep('on → off', false);
    });

    it('mounted with privacy already on: shows the event value from the first render while the cash amount is masked, then shows the cash again when privacy turns off', async () => {
        setPrivacyEnabled(true);
        flushSync();
        mount();
        await mounted();
        await expectStep('mount, privacy on', true);

        await togglePrivacyInPlace();
        await expectStep('on → off', false);
    });
});
