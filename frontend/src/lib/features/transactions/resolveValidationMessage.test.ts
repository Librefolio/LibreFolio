import {afterEach, describe, it, expect, vi} from 'vitest';

// M-18 CP2: the numbers of a message are written in the interface locale, the UI language regionalised by
// the browser. Node's `navigator.language` follows the host's ICU locale, so it is pinned to en-US before any
// import, as jsdom's always is: the English UI then writes en-US, today's text.
vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {getMessageFormatter, waitLocale} from 'svelte-i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {resolveIssueMessage, translateFieldName, type ResolvableIssue, type ResolverContext} from './resolveValidationMessage';

/**
 * A controllable stand-in for svelte-i18n's `$t`. The module's entire fallback
 * chain hinges on one convention — a *missing* key resolves to the key string
 * itself — so the fake echoes the key when it is unknown, and otherwise
 * interpolates `{placeholder}` tokens from `opts.values`. That lets a test both
 * choose which keys "exist" and prove that the enriched params reached the
 * template.
 */
function makeT(known: Record<string, string> = {}) {
    return (key: string, opts?: {values?: Record<string, any>}): string => {
        const tpl = known[key];
        if (tpl === undefined) return key; // missing → the key itself (the module's "not found" signal)
        const values = opts?.values ?? {};
        return tpl.replace(/\{(\w+)\}/g, (_m, k) => (values[k] !== undefined ? String(values[k]) : `{${k}}`));
    };
}

describe('translateFieldName', () => {
    it('returns the i18n label when the field key exists', () => {
        const t = makeT({'transactions.fields.broker_id': 'Broker'});
        expect(translateFieldName('broker_id', t)).toBe('Broker');
    });

    it('flattens a dotted field path into an underscore key', () => {
        const t = makeT({'transactions.fields.cash_amount': 'Cash amount'});
        expect(translateFieldName('cash.amount', t)).toBe('Cash amount');
    });

    it('falls back to a humanised name when no key exists', () => {
        const t = makeT();
        // underscores/dots → spaces, first letter capitalised
        expect(translateFieldName('asset_id', t)).toBe('Asset id');
        expect(translateFieldName('cash.amount', t)).toBe('Cash amount');
    });
});

describe('resolveIssueMessage — no code', () => {
    it('prefers error over msg', () => {
        const t = makeT();
        expect(resolveIssueMessage({error: 'boom', msg: 'ignored'}, t)).toBe('boom');
    });

    it('falls through to msg when error is absent', () => {
        const t = makeT();
        expect(resolveIssueMessage({msg: 'just msg'}, t)).toBe('just msg');
    });

    it('uses the constant last resort when neither is present', () => {
        const t = makeT();
        expect(resolveIssueMessage({}, t)).toBe('Unknown error');
    });
});

describe('resolveIssueMessage — custom error code (happy path)', () => {
    it('translates the custom code and interpolates raw params verbatim', () => {
        const t = makeT({'transactions.errors.CUSTOM': 'Custom failed for {name}'});
        const msg = resolveIssueMessage({code: 'CUSTOM', params: {name: 'foo'}}, t);
        expect(msg).toBe('Custom failed for foo');
    });

    it('tolerates a null params bag', () => {
        const t = makeT({'transactions.errors.CUSTOM': 'ok'});
        expect(resolveIssueMessage({code: 'CUSTOM', params: null}, t)).toBe('ok');
    });
});

describe('resolveIssueMessage — type enrichment', () => {
    it('replaces a translatable transaction type with its localized name', () => {
        const t = makeT({
            'transactions.errors.WRONG_TYPE': 'type={type} a={typeA} b={typeB}',
            'transactions.types.BUY': 'Acquisto',
            'transactions.types.SELL': 'Vendita',
        });
        const msg = resolveIssueMessage({code: 'WRONG_TYPE', params: {type: 'BUY', typeA: 'SELL', typeB: 'BUY'}}, t);
        expect(msg).toBe('type=Acquisto a=Vendita b=Acquisto');
    });

    it('leaves an untranslatable type string untouched', () => {
        const t = makeT({'transactions.errors.WRONG_TYPE': 'type={type}'});
        // transactions.types.MYSTERY is unknown → the raw value survives
        expect(resolveIssueMessage({code: 'WRONG_TYPE', params: {type: 'MYSTERY'}}, t)).toBe('type=MYSTERY');
    });

    it('ignores a non-string type param', () => {
        const t = makeT({'transactions.errors.WRONG_TYPE': 'type={type}'});
        expect(resolveIssueMessage({code: 'WRONG_TYPE', params: {type: 42}}, t)).toBe('type=42');
    });
});

describe('resolveIssueMessage — broker enrichment', () => {
    const t = makeT({'transactions.errors.E': 'broker={brokerName}'});

    it('resolves a known broker id to its name', () => {
        const ctx: ResolverContext = {brokers: [{id: 7, name: 'Fineco'}]};
        expect(resolveIssueMessage({code: 'E', params: {brokerId: 7}}, t, ctx)).toBe('broker=Fineco');
    });

    it('prefers the chained icon HTML when the resolver provides one', () => {
        const ctx: ResolverContext = {brokers: [{id: 7, name: 'Fineco'}], getBrokerIconHtml: () => '<i>ICON</i>'};
        expect(resolveIssueMessage({code: 'E', params: {brokerId: 7}}, t, ctx)).toBe('broker=<i>ICON</i>Fineco');
    });

    it('falls back to an <img> tag from the icon URL when there is no chained HTML', () => {
        const ctx: ResolverContext = {brokers: [{id: 7, name: 'Fineco'}], getBrokerIconUrl: () => '/logos/fineco.png'};
        const msg = resolveIssueMessage({code: 'E', params: {brokerId: 7}}, t, ctx);
        expect(msg).toContain('<img src="/logos/fineco.png"');
        expect(msg).toContain('Fineco');
    });

    it('emits no icon when neither resolver yields one', () => {
        const ctx: ResolverContext = {brokers: [{id: 7, name: 'Fineco'}], getBrokerIconUrl: () => null};
        expect(resolveIssueMessage({code: 'E', params: {brokerId: 7}}, t, ctx)).toBe('broker=Fineco');
    });

    it('shows a "#id" placeholder when the broker is absent from a provided list', () => {
        const ctx: ResolverContext = {brokers: [{id: 1, name: 'Other'}]};
        expect(resolveIssueMessage({code: 'E', params: {brokerId: 7}}, t, ctx)).toBe('broker=Broker #7');
    });

    it('shows a "#id" placeholder when no broker list is provided at all', () => {
        expect(resolveIssueMessage({code: 'E', params: {brokerId: 7}}, t)).toBe('broker=Broker #7');
    });
});

describe('resolveIssueMessage — asset enrichment', () => {
    const t = makeT({'transactions.errors.E': 'asset={assetName}'});

    it('resolves a known asset id and uses its explicit icon_url', () => {
        const ctx: ResolverContext = {assets: [{id: 3, display_name: 'Apple', icon_url: '/apple.png'}]};
        const msg = resolveIssueMessage({code: 'E', params: {assetId: 3}}, t, ctx);
        expect(msg).toContain('<img src="/apple.png"');
        expect(msg).toContain('Apple');
    });

    it('derives a type icon when the asset has no explicit icon_url', () => {
        const ctx: ResolverContext = {assets: [{id: 3, display_name: 'Apple', asset_type: 'STOCK'}]};
        const msg = resolveIssueMessage({code: 'E', params: {assetId: 3}}, t, ctx);
        // getAssetTypeIconUrl maps unknown/known types under /icons/asset-types/
        expect(msg).toContain('<img src="/icons/asset-types/');
        expect(msg).toContain('Apple');
    });

    it('shows a "#id" placeholder when the asset is absent from a provided list', () => {
        const ctx: ResolverContext = {assets: [{id: 1, display_name: 'Other'}]};
        expect(resolveIssueMessage({code: 'E', params: {assetId: 3}}, t, ctx)).toBe('asset=Asset #3');
    });

    it('shows a "#id" placeholder when no asset list is provided at all', () => {
        expect(resolveIssueMessage({code: 'E', params: {assetId: 3}}, t)).toBe('asset=Asset #3');
    });
});

describe('resolveIssueMessage — balance and currency formatting', () => {
    it('formats a cash balance with its currency when both are present', () => {
        const t = makeT({'transactions.errors.E': 'bal={formattedBalance}'});
        const msg = resolveIssueMessage({code: 'E', params: {balance: '1234.5', currency: 'USD'}}, t);
        // formatCurrencyAmountPlain forces 2 decimals and a sign; exact symbol/flag
        // depend on the currency store, which is empty in unit → code fallback.
        expect(msg).toContain('bal=');
        expect(msg).toContain('1,234.50');
        expect(msg).toContain('USD');
    });

    it('formats a positive asset balance with an up emoji when there is no currency', () => {
        const t = makeT({'transactions.errors.E': 'bal={balance}'});
        const msg = resolveIssueMessage({code: 'E', params: {balance: '5'}}, t);
        expect(msg).toBe('bal=5 📈');
    });

    it('formats a negative asset balance with a down emoji', () => {
        const t = makeT({'transactions.errors.E': 'bal={balance}'});
        const msg = resolveIssueMessage({code: 'E', params: {balance: '-2.5'}}, t);
        expect(msg).toContain('📉');
        expect(msg).not.toContain('📈');
    });

    it('rewrites a bare currency code into rich HTML', () => {
        const t = makeT({'transactions.errors.E': 'cur={currency}'});
        const msg = resolveIssueMessage({code: 'E', params: {currency: 'EUR'}}, t);
        expect(msg).toContain('currency-code');
        expect(msg).toContain('EUR');
    });

    it('ignores a non-string currency', () => {
        const t = makeT({'transactions.errors.E': 'cur={currency}'});
        // A numeric currency neither triggers formatCurrencyCodeHtml nor the balance+currency branch
        expect(resolveIssueMessage({code: 'E', params: {currency: 5}}, t)).toBe('cur=5');
    });
});

/**
 * M-18 CP2 — the numbers of a message in the interface language.
 *
 * Every figure follows the UI language (the developer's rule of 2026-10-12). An asset balance with no
 * currency was written with `toLocaleString(undefined, …)` — the browser's notation — into a sentence the
 * translator writes in the UI language: `12,345.678 📈` inside an Italian message. The cure writes it in
 * `uiLocale()` with the same digits (no forced decimals, up to six); a cash balance goes through
 * `formatCurrencyAmountPlain`, whose number follows the same source. Expectations are Intl's output with
 * the module's own options, never typed, but for today's English text. The currency store is empty in a
 * unit run, so a cash balance carries its code alone.
 */
describe('resolveIssueMessage — the numbers in the interface language (M-18 CP2)', () => {
    const t = makeT({'transactions.errors.E': 'bal={balance}', 'transactions.errors.C': 'cash={formattedBalance}'});
    /** An asset balance as the module writes it: no forced decimals, up to six. */
    const balanceIn = (locale: string, value: number): string => new Intl.NumberFormat(locale, {minimumFractionDigits: 0, maximumFractionDigits: 6}).format(value);
    /** A cash balance's number: two decimals. */
    const cashIn = (locale: string, value: number): string => new Intl.NumberFormat(locale, {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(value);

    /** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
    async function uiLanguage(lang: 'en' | 'it'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
    }

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await uiLanguage('en');
    });

    it('English UI on an en-US browser (control): today’s text', async () => {
        await uiLanguage('en');

        expect(resolveIssueMessage({code: 'E', params: {balance: '12345.678'}}, t)).toBe('bal=12,345.678 📈');
        expect(resolveIssueMessage({code: 'E', params: {balance: '-2.5'}}, t)).toBe('bal=-2.5 📉');
        expect(resolveIssueMessage({code: 'C', params: {balance: '12345.5', currency: 'USD'}}, t)).toBe('cash=+12,345.50 USD');
    });

    it('Italian UI: an asset balance in Italian notation, without passing a locale', async () => {
        await uiLanguage('it');
        const up = balanceIn('it', 12345.678);
        expect(up, 'control: the Italian notation differs from the English one').not.toBe(balanceIn('en-US', 12345.678));

        expect(resolveIssueMessage({code: 'E', params: {balance: '12345.678'}}, t)).toBe(`bal=${up} 📈`);
        expect(resolveIssueMessage({code: 'E', params: {balance: '-2.5'}}, t)).toBe(`bal=${balanceIn('it', -2.5)} 📉`);
    });

    it('Italian UI: a cash balance in Italian notation too, through the currency formatter', async () => {
        await uiLanguage('it');
        expect(cashIn('it', 12345.5), 'control: the Italian notation differs from the English one').not.toBe(cashIn('en-US', 12345.5));

        expect(resolveIssueMessage({code: 'C', params: {balance: '12345.5', currency: 'USD'}}, t)).toBe(`cash=+${cashIn('it', 12345.5)} USD`);
    });
});

/**
 * C-97c-1 (decision D-C97c-1 of the coordinator, 17/10) — an asset balance loses no digit the database keeps.
 *
 * A balance with no `currency` is a quantity of an asset, and a quantity keeps ten decimals. The module writes it with
 * `parseFloat` and `maximumFractionDigits: 6`, so a balance of -0.0000000123 reads `-0 📉`. The contract: up to ten
 * decimals, exact — the decimal string as it is, never through a float — with the emoji by sign as today, 📈 from zero
 * up, 📉 below. Red: a balance past the sixth decimal, and one past what a float holds. Guard: `5` stays `5 📈`. English
 * on the en-US browser pinned at the top of the file, set through the store; the expectations are typed.
 */
describe('resolveIssueMessage — an asset balance keeps every decimal, up to ten, exact (C-97c-1)', () => {
    const t = makeT({'transactions.errors.E': 'bal={balance}'});

    /** The English UI, set as LanguageSelector sets it: on the en-US browser it is written en-US. */
    async function english(): Promise<void> {
        currentLanguage.set('en');
        await waitLocale('en');
        expect(uiLocale(), 'control: an English UI on the en-US browser is written en-US').toBe('en-US');
    }

    it('-0.0000000123 reads -0.0000000123 📉 — its ten decimals, not six', async () => {
        await english();

        expect(resolveIssueMessage({code: 'E', params: {balance: '-0.0000000123'}}, t)).toBe('bal=-0.0000000123 📉');
    });

    it('123456789.1234567891 reads 123,456,789.1234567891 📈 — the decimal string as it is, never through a float', async () => {
        await english();
        expect(String(Number('123456789.1234567891')), 'control: a float does not hold every digit').not.toBe('123456789.1234567891');

        expect(resolveIssueMessage({code: 'E', params: {balance: '123456789.1234567891'}}, t)).toBe('bal=123,456,789.1234567891 📈');
    });

    it('guard: 5 reads 5 📈 — no forced decimals', async () => {
        await english();

        expect(resolveIssueMessage({code: 'E', params: {balance: '5'}}, t)).toBe('bal=5 📈');
    });
});

describe('resolveIssueMessage — pairs formatting (WAC FX)', () => {
    it('renders each base/quote pair as flag HTML joined by commas', () => {
        const t = makeT({'transactions.errors.E': 'pairs={pairs}'});
        const msg = resolveIssueMessage({code: 'E', params: {pairs: ['USD/EUR', 'GBP/JPY']}}, t);
        expect(msg).toContain('USD');
        expect(msg).toContain('EUR');
        expect(msg).toContain('GBP');
        expect(msg).toContain('JPY');
        expect(msg).toContain(', '); // two pairs joined
    });

    it('tolerates a malformed pair missing its quote half', () => {
        const t = makeT({'transactions.errors.E': 'pairs={pairs}'});
        // "USD" splits to [USD, undefined] → quote branch is skipped, no throw
        const msg = resolveIssueMessage({code: 'E', params: {pairs: ['USD']}}, t);
        expect(msg).toContain('USD');
    });
});

describe('resolveIssueMessage — fallback chain when the custom key is missing', () => {
    it('applies a field-specific override before the generic pydantic message', () => {
        // broker_id:missing is overridden to a friendly "select a broker" key
        const t = makeT({'transactions.fieldErrors.brokerRequired': 'Please select a broker'});
        const msg = resolveIssueMessage({code: 'missing', loc: 'body.creates.0.broker_id'}, t);
        expect(msg).toBe('Please select a broker');
    });

    it('prefixes a generic pydantic message with the translated field label', () => {
        const t = makeT({
            'transactions.fields.quantity': 'Quantity',
            'transactions.pydantic.greaterThan': 'must be greater than {gt}',
        });
        const msg = resolveIssueMessage({code: 'greater_than', field: 'quantity', params: {gt: 0}}, t);
        expect(msg).toBe('Quantity: must be greater than 0');
    });

    it('returns a pydantic message unprefixed when the field is unknown', () => {
        const t = makeT({'transactions.pydantic.missing': 'is required'});
        // No loc, no field → no label to prefix with
        expect(resolveIssueMessage({code: 'missing'}, t)).toBe('is required');
    });

    it('falls back to the raw error string, field-prefixed, when nothing else matches', () => {
        const t = makeT({'transactions.fields.asset_id': 'Asset'});
        const msg = resolveIssueMessage({code: 'weird_code', field: 'asset_id', error: 'raw backend text'}, t);
        expect(msg).toBe('Asset: raw backend text');
    });

    it('falls back to the code itself when there is no error, msg, or field', () => {
        const t = makeT();
        expect(resolveIssueMessage({code: 'weird_code'}, t)).toBe('weird_code');
    });

    it('skips an override whose key is itself missing and continues down the chain', () => {
        // broker_id:missing has an override key, but that key is NOT in the dict,
        // so it must fall through to the pydantic message (which IS present).
        const t = makeT({
            'transactions.fields.broker_id': 'Broker',
            'transactions.pydantic.missing': 'is required',
        });
        const msg = resolveIssueMessage({code: 'missing', field: 'broker_id'}, t);
        expect(msg).toBe('Broker: is required');
    });
});

describe('resolveIssueMessage — field extraction from loc', () => {
    it('strips body / operation / row-index to reach the leaf field', () => {
        const t = makeT({'transactions.fields.broker_id': 'Broker', 'transactions.pydantic.missing': 'is required'});
        expect(resolveIssueMessage({code: 'missing', loc: 'body.updates.12.broker_id'}, t)).toBe('Broker: is required');
    });

    it('keeps a multi-segment field path (cash.amount)', () => {
        const t = makeT({'transactions.fields.cash_amount': 'Cash', 'transactions.pydantic.missing': 'is required'});
        expect(resolveIssueMessage({code: 'missing', loc: 'body.creates.0.cash.amount'}, t)).toBe('Cash: is required');
    });

    it('treats a row-level loc (no leaf field) as having no field', () => {
        const t = makeT({'transactions.pydantic.missing': 'is required'});
        // body.creates.0 → nothing left after stripping → no prefix
        expect(resolveIssueMessage({code: 'missing', loc: 'body.creates.0'}, t)).toBe('is required');
    });

    it('prefers an explicit field over the loc path', () => {
        const t = makeT({'transactions.fields.asset_id': 'Asset', 'transactions.pydantic.missing': 'is required'});
        expect(resolveIssueMessage({code: 'missing', field: 'asset_id', loc: 'body.creates.0.broker_id'}, t)).toBe('Asset: is required');
    });

    it('handles a loc that does not start with "body" or an operation', () => {
        const t = makeT({'transactions.pydantic.missing': 'is required'});
        // No body/creates/updates/deletes prefix and no leading digit: the whole path is the field.
        expect(resolveIssueMessage({code: 'missing', loc: 'foo.bar'}, t)).toBe('Foo bar: is required');
    });

    it('reaches the leaf field through a "deletes" operation', () => {
        // The id:missing override maps to transactions.errors.idRequired, which is deliberately
        // absent from this fake, so resolution falls through to the generic pydantic message.
        const t = makeT({'transactions.fields.id': 'Id', 'transactions.pydantic.missing': 'is required'});
        expect(resolveIssueMessage({code: 'missing', loc: 'body.deletes.3.id'}, t)).toBe('Id: is required');
    });
});

describe('resolveIssueMessage — residual defensive branches', () => {
    it('renders a pair whose base half is empty', () => {
        const t = makeT({'transactions.errors.E': 'pairs={pairs}'});
        // "/EUR" splits to ['', 'EUR'] → the base branch takes its falsy path, no throw
        const msg = resolveIssueMessage({code: 'E', params: {pairs: ['/EUR']}}, t);
        expect(msg).toContain('EUR');
    });

    it('falls to the raw string when a pydantic code exists but its message key does not', () => {
        // "greater_than" is a known pydantic code, but the pydantic i18n key is absent
        // from this fake, so its translation equals the key → chain continues to raw.
        const t = makeT({'transactions.fields.quantity': 'Quantity'});
        const msg = resolveIssueMessage({code: 'greater_than', field: 'quantity', error: 'raw'}, t);
        expect(msg).toBe('Quantity: raw');
    });
});

/**
 * K step 13, item 0 — every caller renders the result with `{@html}` (TransactionFormModal,
 * TransactionBulkModal, ParseDetailModal), so what a user or a backend wrote must come out as text.
 * Assertions are on the string, the way the sink receives it: `&lt;` where a tag would open, `&quot;`
 * where an attribute would close — and never the attribute a payload tries to write.
 */
describe('resolveIssueMessage — user and backend text reaches {@html} escaped', () => {
    const HOSTILE = '<img src=x onerror="window.__k13=1">';
    const BREAKOUT_URL = 'x" onerror="window.__k13=1';
    /** An attribute written by a payload: it can only appear when a quote was left unescaped. */
    const INJECTED_ATTRIBUTE = 'onerror="window.__k13';

    it('escapes a broker name', () => {
        const t = makeT({'transactions.errors.E': 'broker={brokerName}'});
        const ctx: ResolverContext = {brokers: [{id: 7, name: `${HOSTILE} Fineco`}]};
        const msg = resolveIssueMessage({code: 'E', params: {brokerId: 7}}, t, ctx);
        expect(msg).toContain('&lt;img');
        expect(msg).not.toContain('<img src=x');
        expect(msg).not.toContain(INJECTED_ATTRIBUTE);
        expect(msg).toContain('Fineco');
    });

    it('keeps a broker icon URL inside its src attribute', () => {
        const t = makeT({'transactions.errors.E': 'broker={brokerName}'});
        const ctx: ResolverContext = {brokers: [{id: 7, name: 'Fineco'}], getBrokerIconUrl: () => BREAKOUT_URL};
        const msg = resolveIssueMessage({code: 'E', params: {brokerId: 7}}, t, ctx);
        expect(msg).toContain('&quot;');
        expect(msg).not.toContain(INJECTED_ATTRIBUTE);
        expect(msg).toContain('Fineco');
    });

    it('escapes an asset name, and keeps its icon_url inside its src attribute', () => {
        const t = makeT({'transactions.errors.E': 'asset={assetName}'});
        const ctx: ResolverContext = {assets: [{id: 3, display_name: `${HOSTILE} Apple`, icon_url: BREAKOUT_URL}]};
        const msg = resolveIssueMessage({code: 'E', params: {assetId: 3}}, t, ctx);
        expect(msg).toContain('&lt;img');
        expect(msg).toContain('&quot;');
        expect(msg).not.toContain('<img src=x');
        expect(msg).not.toContain(INJECTED_ATTRIBUTE);
        expect(msg).toContain('Apple');
    });

    it('escapes a raw backend message returned when the issue has no code', () => {
        const msg = resolveIssueMessage({error: `Duplicate of ${HOSTILE}`}, makeT());
        expect(msg).toContain('&lt;img');
        expect(msg).not.toContain('<img');
        expect(msg).toContain('Duplicate of');
    });

    it('escapes a raw backend message used as the last fallback, and keeps its field prefix', () => {
        const t = makeT({'transactions.fields.description': 'Description'});
        const msg = resolveIssueMessage({code: 'UNMAPPED_CODE', msg: HOSTILE, field: 'description'}, t);
        expect(msg.startsWith('Description: ')).toBe(true);
        expect(msg).toContain('&lt;img');
        expect(msg).not.toContain('<img');
    });
});

/**
 * W-B39 — on a split, a missing exchange rate has words of its own.
 *
 * Splitting a TRANSFER pair values the units that leave at their average cost (decision 47). When that average
 * needs a rate the database lacks, the commit refuses the split with `wacFxUnavailable` on `operation: 'split'`;
 * the generic text of the code only says that the calculation failed — no rate, no way out — and the Transactions
 * page now shows the refusal in a toast. A split's issue therefore reads `transactions.errors.wacFxUnavailableSplit`
 * first, its `{pairs}` filled in, and the generic key when the catalogue has no split text; the same code on any
 * other operation keeps the generic text.
 *
 * The issues are variables, never literals handed to the call: the file compiles whether or not `ResolvableIssue`
 * declares `operation` yet. The markup of a pair belongs to `formatCurrencyCodeHtml`, so only its codes are asserted.
 */
describe('resolveIssueMessage — a missing exchange rate on a split (W-B39)', () => {
    const SPLIT_KEY = 'transactions.errors.wacFxUnavailableSplit';
    const GENERIC_KEY = 'transactions.errors.wacFxUnavailable';
    /** A distinctive opening, then the pairs: the opening tells the split text apart, the pairs prove it was filled. */
    const SPLIT_TEXT = 'Average cost of the units that leave needs the {pairs} rate';
    const GENERIC_TEXT = 'WAC calculation failed.';
    /** The issue `batch_costs._wac_fx_unavailable` writes, without its operation. */
    const missingRate = {
        index: 0,
        ref_id: 41,
        error: 'WAC calculation failed: missing FX pairs USD/EUR',
        code: 'wacFxUnavailable',
        params: {pairs: ['USD/EUR'], pair_details: [{pair: 'USD/EUR', dates: ['2026-10-01']}]},
        field: 'cost_basis_override',
    };

    it('a split reads its own text, the missing pairs filled in', () => {
        const t = makeT({[SPLIT_KEY]: SPLIT_TEXT, [GENERIC_KEY]: GENERIC_TEXT});
        const issue = {...missingRate, operation: 'split'};
        const msg = resolveIssueMessage(issue, t);
        expect(msg).toContain('Average cost of the units that leave needs the');
        expect(msg).toContain('USD');
        expect(msg).toContain('EUR');
        expect(msg).not.toContain('{pairs}');
        expect(msg).not.toContain(GENERIC_TEXT);
    });

    it('control: the same code on another operation keeps the generic text', () => {
        const t = makeT({[SPLIT_KEY]: SPLIT_TEXT, [GENERIC_KEY]: GENERIC_TEXT});
        const issue = {...missingRate, operation: 'create', ref_id: null};
        expect(resolveIssueMessage(issue, t)).toBe(GENERIC_TEXT);
    });

    it('control: a split falls back to the generic text when the catalogue has no split text', () => {
        const t = makeT({[GENERIC_KEY]: GENERIC_TEXT});
        const issue = {...missingRate, operation: 'split'};
        expect(resolveIssueMessage(issue, t)).toBe(GENERIC_TEXT);
    });
});

/**
 * W-B70 (decision D-W70-2 of the coordinator, 17/10) — notes too long have words of their own, and the built-in branch
 * escapes its field label.
 *
 * A transaction's notes hold 500 characters at most (`max_length=500`: a create, an update, a promote's
 * `resolved_fields`). Past it pydantic answers `string_too_long`, and the backend now hands the error's context over as
 * params (D-W70-1: `{max_length: 500}`). `PYDANTIC_BUILTIN_KEYS` maps pydantic's own codes to `transactions.pydantic.*`
 * and has no entry for this one, so the message falls through to the raw English of `issue.error` («String should have
 * at most 500 characters»), in whatever language the editor speaks. The contract: `string_too_long` maps to
 * `transactions.pydantic.stringTooLong` («At most {max_length} characters», added by the cure), its `{max_length}`
 * the param as sent, after the field label like every built-in message.
 *
 * The label. All three callers render the result with `{@html}`, and two of the module's three branches escape the
 * field label; the built-in branch does not. With no translation the label is the field name itself (cleaned of `_`
 * and `.`, first letter up) — for `extra_forbidden` any key of the request body — so a name carrying markup reaches the
 * HTML as markup. The contract: escaped there too, and only the label: the text after it is the catalogue's own. A
 * translated label is plain text, which escaping leaves as it is.
 *
 * Reds: `string_too_long` through its key with `max_length: 500`; a hostile field name, from `field` and from `loc`.
 * Guards, green before and after: `greater_than` hands `{gt: 0}` to its key as the number it is (the frontend already
 * passes the params on, D-W70-1 is what fills them); a translated label comes out unchanged, and the catalogue's text
 * after it keeps its markup. The translator is `makeT`, wrapped in a spy where the values handed to a key are the
 * subject.
 */
describe('resolveIssueMessage — notes too long, and the built-in branch escapes its label (W-B70, D-W70-2)', () => {
    const STRING_TOO_LONG_KEY = 'transactions.pydantic.stringTooLong';
    /** The issue the backend writes for a promote whose combined notes pass the limit, `params` filled (D-W70-1). */
    const notesTooLong: ResolvableIssue = {code: 'string_too_long', field: 'description', params: {max_length: 500}, error: 'String should have at most 500 characters', operation: 'promote'};
    /** Field names that are markup. Neither holds a `_` or a `.`, so the label's fallback keeps them as they are. */
    const HOSTILE_FIELD = '<img src=x onerror=alert(1)>';
    const BREAKOUT_FIELD = '"><img src=x onerror=alert(1)>';
    /** The catalogue knows the code's text and no label for these names. */
    const unexpectedField = makeT({'transactions.pydantic.extraForbidden': 'Unexpected field'});

    it('string_too_long resolves through transactions.pydantic.stringTooLong, its max_length the number sent, after the field label', () => {
        const t = vi.fn(makeT({'transactions.fields.description': 'Description', [STRING_TOO_LONG_KEY]: 'At most {max_length} characters'}));

        const msg = resolveIssueMessage(notesTooLong, t);

        expect(msg, 'the translated text after the field label, never the raw English of issue.error').toBe('Description: At most 500 characters');
        expect(t, 'the key is asked with the limit as sent: the number 500').toHaveBeenCalledWith(STRING_TOO_LONG_KEY, {values: expect.objectContaining({max_length: 500})});
    });

    it('guard: greater_than hands {gt: 0} to transactions.pydantic.greaterThan as the number 0', () => {
        const t = vi.fn(makeT({'transactions.fields.quantity': 'Quantity', 'transactions.pydantic.greaterThan': 'Value must be greater than {gt}'}));

        const msg = resolveIssueMessage({code: 'greater_than', field: 'quantity', params: {gt: 0}, error: 'Input should be greater than 0'}, t);

        expect(msg).toBe('Quantity: Value must be greater than 0');
        expect(t).toHaveBeenCalledWith('transactions.pydantic.greaterThan', {values: expect.objectContaining({gt: 0})});
    });

    it('escapes a label that falls back to a hostile field name (extra_forbidden, the name in field)', () => {
        expect(translateFieldName(HOSTILE_FIELD, unexpectedField), 'control: no translation, so the label is the name itself').toBe(HOSTILE_FIELD);

        const msg = resolveIssueMessage({code: 'extra_forbidden', field: HOSTILE_FIELD, error: 'Extra inputs are not permitted'}, unexpectedField);

        expect(msg).toBe('&lt;img src=x onerror=alert(1)&gt;: Unexpected field');
        expect(msg).not.toContain('<img');
    });

    it('escapes it when the name comes from loc, a closing quote included', () => {
        const msg = resolveIssueMessage({code: 'extra_forbidden', loc: `body.creates.0.${BREAKOUT_FIELD}`, error: 'Extra inputs are not permitted'}, unexpectedField);

        expect(msg).toBe('&quot;&gt;&lt;img src=x onerror=alert(1)&gt;: Unexpected field');
        expect(msg).not.toContain('<img');
        expect(msg).not.toContain('"');
    });

    it('guard: a translated label is plain text, unchanged, and the catalogue’s text after it keeps its markup', () => {
        const t = makeT({'transactions.fields.quantity': 'Quantità', 'transactions.pydantic.extraForbidden': 'Campo <em>inatteso</em>'});

        expect(resolveIssueMessage({code: 'extra_forbidden', field: 'quantity'}, t)).toBe('Quantità: Campo <em>inatteso</em>');
    });
});

/**
 * W-B70, D-W70-2 — the key is in the four catalogues, naming the param the backend fills.
 *
 * The cases above hand the module a translator of their own. These read the catalogues the app ships
 * (`$lib/i18n/<lang>.json`, generated from the sources before every Vitest run): `transactions.pydantic.stringTooLong`
 * must be a message in each, naming the one placeholder the backend fills, `max_length`. Where it is missing, svelte-i18n
 * answers with the key itself and the module falls back to the raw English; a placeholder named otherwise would not be
 * filled. The wording is the translators': only the presence, the placeholder and that the message formats with the
 * limit written are read. Red today in the four languages: the key is in no catalogue.
 */
describe('transactions.pydantic.stringTooLong — in the four catalogues, with {max_length} (W-B70, D-W70-2)', () => {
    const KEY = 'transactions.pydantic.stringTooLong';
    const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};

    /** The value at a dotted key of a catalogue, or undefined. */
    function messageAt(catalogue: unknown, key: string): unknown {
        return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    }

    /** The placeholders a message names, `{name}` or `{name, …}`, each once. */
    function placeholdersOf(message: string): string[] {
        return [...new Set([...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1]))].sort();
    }

    for (const lang of Object.keys(CATALOGUES)) {
        it(`${lang}: a message naming {max_length} and nothing else, which writes the limit it is given`, () => {
            const message = messageAt(CATALOGUES[lang], KEY);
            expect(typeof message, `${lang}: ${KEY} is a message of the catalogue`).toBe('string');
            expect(placeholdersOf(message as string), `${lang}: the placeholder the backend fills`).toEqual(['max_length']);
            expect(String(getMessageFormatter(message as string, lang).format({max_length: 500})), `${lang}: the limit, written`).toMatch(/(?<![\d.,])500(?![.,]?\d)/);
        });
    }
});
