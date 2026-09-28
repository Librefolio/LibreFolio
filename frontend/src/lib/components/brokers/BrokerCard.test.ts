// @vitest-environment jsdom
/**
 * BrokerCard under the global privacy toggle — component test (Vitest + jsdom).
 *
 * R20, product owner review of 2026-09-22: on the Brokers list page, which renders one
 * BrokerCard per broker, the amounts hid under the global privacy toggle but did not come back
 * when it was switched off. The mechanism, measured on 2026-09-24 by this spec and by the
 * compiled component: BrokerCard is a legacy-mode component (`export let`,
 * `createEventDispatcher`, no runes), and a legacy template compiles a function call inside an
 * expression to `$.untrack(() => …)`, tracking only the values the expression names
 * (`summary`, `targetCurrency`, `balance`). Its three `{@html formatCurrencyAmountHtml(...)}`
 * sites therefore never saw `isPrivacyEnabled()`, the `$state` rune the formatter reads through
 * `maskable`, and every amount kept the state it had at mount: turned on in place, privacy left
 * them in the clear; mounted masked, they stayed masked after privacy was turned off. All three
 * tests below were red on that code, each at its first toggle.
 *
 * The fix routes the three sites — NAV, gain/loss, one per cash balance — through
 * `CurrencyAmount`, a runes child whose `{@html}` is tracked through the call. The card itself
 * stays legacy, and the assertions below are the ones that measured the defect.
 *
 * How the steps tell a regression apart:
 *   - a template that does not re-render on the toggle fails the first test at its first step
 *     (off → on) and the second at its only step (on → off);
 *   - a re-render in one direction only passes off → on and fails on → off;
 *   - a subscription that fires once and then goes deaf fails the third test, which repeats
 *     the round trip twice.
 *
 * Every step checks three controls before it looks at the card, so a red names the layer
 * that failed instead of just "privacy is broken":
 *   1. `isPrivacyEnabled()` — the flag really moved;
 *   2. a fresh `formatCurrencyAmountHtml` call — the formatter follows the flag;
 *   3. a reactive consumer of our own (`toStore` over the same formatter call) — a consumer
 *      that *tracks* the call sees the toggle.
 * With all three green, a card still showing the previous state is the card's own re-render
 * and nothing else.
 *
 * Selection. The card by `data-testid`; the amounts by the markup the formatter itself emits
 * (`.currency-amount` beside its `.currency-code`). The card publishes no per-amount handle,
 * and that markup is the contract every masked amount in the app shares. The card's money is
 * read as a sorted multiset of `"<amount> <code>"`, never by position: masked, the NAV and the
 * EUR balance are indistinguishable by design.
 *
 * Expectations. Unmasked strings come from the formatter itself with privacy off —
 * `toLocaleString(undefined, …)` follows the host locale, so a frozen `12,345.67` would turn a
 * de-DE runner red — and the NAV one is checked once against the digits put in. Masked strings
 * are literals: a placeholder has no locale. Nothing here reads translated text.
 *
 * Storage. The shared `$app/environment` mock reports `browser: false`, so `setPrivacyEnabled`
 * moves the in-memory rune and never touches `localStorage`; persistence is
 * privacyStore.test.ts's subject, not this one's.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {toStore} from 'svelte/store';

// The only request this graph makes is the currency catalogue, answered here so the rendered
// suffix carries a real symbol and flag, as on the Brokers page. Every other method is inert.
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
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {render, screen, setupI18n} from '$test/component';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {formatCurrencyAmountHtml, type CurrencyAmountFormatOptions} from '$lib/utils/currency/currencyFormat';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import BrokerCard from './BrokerCard.svelte';

const P = PRIVACY_PLACEHOLDER;
const TARGET_CURRENCY = 'EUR';

// Four amounts with four distinct magnitudes, so the unmasked multiset has no ties.
const NAV = 12345.67;
const GAIN_LOSS = -987.65;
const EUR_CASH = 2500.5;
const USD_CASH = 1200.25;

/** A row of `GET /brokers`, as the Brokers page passes it. */
const BROKER = {
    id: 42,
    name: 'R20 probe broker',
    description: null,
    // A portal URL is what most real brokers carry, and it keeps BrokerIcon off the network:
    // with any icon field set it does not hydrate the broker from the API.
    portal_url: 'https://broker.example.com',
    icon_url: null,
    default_import_plugin: null,
    allow_cash_overdraft: false,
    allow_asset_shorting: false,
    is_active: true,
    user_role: 'OWNER',
    user_share_percentage: '100',
};

/** One `summary.by_broker` entry of the report, amounts serialised as Decimal strings. */
const SUMMARY = {
    broker_id: BROKER.id,
    net_worth: {code: 'EUR', amount: '12345.67'},
    gain_loss: {code: 'EUR', amount: '-987.65'},
    gain_loss_percent: '-0.0741',
    cash_balances: [
        {code: 'EUR', amount: '2500.50'},
        {code: 'USD', amount: '1200.25'},
    ],
};

/** NAV and gain/loss in the target currency, one amount per balance: the card's four. */
const MASKED_MONEY = [`${P} EUR`, `-${P} EUR`, `${P} EUR`, `${P} USD`].sort();
const CURRENCY_CODES = ['EUR', 'EUR', 'EUR', 'USD'];

/** Filled in `beforeAll`, once the currency cache is loaded, with privacy off. */
let navClear = '';
let clearMoney: string[] = [];

/** Unsubscribers of the reactive consumers created by the running test. */
const teardowns: Array<() => void> = [];

/**
 * Every amount under `root` as `"<amount> <code>"`, sorted — a multiset, never a position.
 *
 * The formatter emits an amount and its code as siblings of one fragment, and each amount site
 * in the card — a `CurrencyAmount`, which adds no element of its own — has a parent of its own,
 * so the code is looked up beside the amount. Anything else is a markup change this helper
 * must not paper over.
 */
function moneyIn(root: Element): string[] {
    return [...root.querySelectorAll('.currency-amount')]
        .map((amount) => {
            const [code, ...extra] = amount.parentElement ? [...amount.parentElement.querySelectorAll('.currency-code')] : [];
            if (!code || extra.length > 0) throw new Error(`amount "${amount.textContent}" does not sit beside exactly one .currency-code`);
            return `${amount.textContent} ${code.textContent}`;
        })
        .sort();
}

/** What the formatter renders for one amount right now, read through the same helper as the card. */
function formatted(amount: number, code: string, opts?: CurrencyAmountFormatOptions): string {
    const host = document.createElement('span');
    host.innerHTML = formatCurrencyAmountHtml(amount, code, opts);
    const [money, ...extra] = moneyIn(host);
    if (!money || extra.length > 0) throw new Error('the formatter did not emit exactly one amount');
    return money;
}

/**
 * Control 3: a reactive consumer of our own, reading the same call as the card's NAV.
 *
 * `toStore` runs its getter inside a render effect, so every rune the getter reads is tracked.
 * If this consumer sees a toggle and the card does not, the card's rendering is what does not
 * track the formatter — the R20 mechanism.
 */
function trackedNav(): () => string {
    let current = '';
    teardowns.push(
        toStore(() => formatted(NAV, 'EUR')).subscribe((value) => {
            current = value;
        }),
    );
    return () => current;
}

/** Set the flag, then flush: synchronously, and once more through the microtask the app itself waits on. */
async function setPrivacy(value: boolean): Promise<void> {
    setPrivacyEnabled(value);
    flushSync();
    await tick();
}

function mountCard(): void {
    render(BrokerCard, {broker: {...BROKER}, summary: structuredClone(SUMMARY), assetCount: 3, targetCurrency: TARGET_CURRENCY});
}

function card(): HTMLElement {
    return screen.getByTestId(`broker-card-${BROKER.id}`);
}

/** The card shows every amount in the clear. Controls first, so a red names its layer. */
function expectClear(step: string, nav: () => string): void {
    expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(false);
    expect(formatted(NAV, 'EUR'), `${step} — control: a fresh formatter call`).toBe(navClear);
    expect(nav(), `${step} — control: a consumer tracking the same call`).toBe(navClear);

    // The subject, exact: the NAV's own text (navClear) is one of the four.
    expect(moneyIn(card()), `${step} — the card's amounts are back in the clear`).toEqual(clearMoney);
}

/** The card masks every amount and keeps every currency. Controls first, as above. */
function expectMasked(step: string, nav: () => string): void {
    expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(true);
    expect(formatted(NAV, 'EUR'), `${step} — control: a fresh formatter call`).toBe(`${P} EUR`);
    expect(nav(), `${step} — control: a consumer tracking the same call`).toBe(`${P} EUR`);

    const amounts = [...card().querySelectorAll('.currency-amount')].map((amount) => amount.textContent ?? '');
    expect(amounts, `${step} — the card rendered its four amounts`).toHaveLength(4);
    expect(
        amounts.filter((text) => /\d/.test(text) || !text.includes(P)),
        `${step} — amounts still showing a digit, or missing the placeholder`,
    ).toEqual([]);
    expect([...card().querySelectorAll('.currency-code')].map((code) => code.textContent).sort(), `${step} — the currency codes stay`).toEqual(CURRENCY_CODES);
    expect(moneyIn(card()), `${step} — the card's amounts, exactly`).toEqual(MASKED_MONEY);
}

beforeAll(async () => {
    await setupI18n();
    await ensureCurrenciesLoaded('en');
    // Control: the cache is really populated, so the suffix carries the symbol and flag the
    // Brokers page shows instead of the bare-code fallback.
    expect(getCurrencyInfo('USD').symbol).toBe('$');

    setPrivacyEnabled(false);
    navClear = formatted(NAV, 'EUR');
    clearMoney = [navClear, formatted(GAIN_LOSS, TARGET_CURRENCY, {showSign: true}), formatted(EUR_CASH, 'EUR'), formatted(USD_CASH, 'USD')].sort();
    // The clear expectation is the formatter's own output, so check once that it carries the
    // digits put in: a formatter masking unconditionally would otherwise make "back in the
    // clear" compare the placeholder with itself.
    expect(navClear.replace(/\D/g, '')).toBe('1234567');
});

afterEach(() => {
    for (const stop of teardowns.splice(0)) stop();
    // The flag is module-level state shared by every test in this file: a leftover `true`
    // would mount the next card masked.
    setPrivacyEnabled(false);
});

describe('BrokerCard — amounts follow the global privacy toggle (R20)', () => {
    it('mounted in the clear: masks every amount when privacy turns on, then shows the digits again when it turns off', async () => {
        const nav = trackedNav();
        mountCard();
        expectClear('mount, privacy off', nav);

        await setPrivacy(true);
        expectMasked('off → on', nav);

        await setPrivacy(false);
        expectClear('on → off', nav);
    });

    it('mounted with privacy already on: shows the digits again when privacy turns off', async () => {
        const nav = trackedNav();
        await setPrivacy(true);
        mountCard();
        expectMasked('mount, privacy on', nav);

        await setPrivacy(false);
        expectClear('on → off', nav);
    });

    it('follows the flag on every toggle of two more round trips (on/off/on/off), not only the first', async () => {
        const nav = trackedNav();
        mountCard();
        expectClear('mount, privacy off', nav);

        for (const round of [1, 2]) {
            await setPrivacy(true);
            expectMasked(`round ${round}: off → on`, nav);
            await setPrivacy(false);
            expectClear(`round ${round}: on → off`, nav);
        }
    });
});
