import {describe, it, expect} from 'vitest';
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
