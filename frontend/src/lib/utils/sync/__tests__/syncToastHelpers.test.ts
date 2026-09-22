/**
 * syncToastHelpers — unit tests
 *
 * These two functions decide what the user is *told* after a sync: the toast
 * variant, and the HTML behind it. The variant is the part that carries meaning
 * — green means "it worked", amber means "look at this" — and it is the one
 * thing a spec may assert on without asserting on a translation.
 *
 * The interesting case is not success. `buildAssetSyncToast` deliberately
 * downgrades a *successful* response with zero changes to a warning, because a
 * provider that returns rows in the wrong currency has them silently dropped by
 * the backend and answers `ok` with nothing written. Green there would tell the
 * user the opposite of the truth. That rule, and its FX counterpart, are what
 * this file pins.
 *
 * On translations: `tr` supplies synthetic markers. Assertions name the key
 * chosen, never a phrase frozen from one of the four catalogues.
 *
 * Existing cold-store coverage uses the real metadata fallbacks. Presentation
 * tests supply isolated currency metadata; provider-chain parsing stays real.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {buildAssetSyncToast, buildFxSyncToast} from '../syncToastHelpers';
import {formatElapsed, formatTime} from '../syncHelpers';
import {fxPairHtml, parseProviderChain, type FxPairHtmlOptions} from '$lib/utils/providerHelpers';
import * as currencyStore from '$lib/stores/reference/currencyStore';

/** Deliberately unlike catalogue text, so a hardcoded prefix cannot pass. */
const tr = (key: string) => `[[translation:${key}]]`;

const pairFlags = {JPY: '🇯🇵', RON: '🇷🇴'};

function mockPairCurrencies(flags: Record<string, string> = pairFlags) {
    return vi.spyOn(currencyStore, 'getCurrencyInfo').mockImplementation((code) => ({
        code,
        name: code,
        symbol: code,
        flag_emoji: flags[code] ?? '🏳️',
        country_codes: [],
        country_names: [],
    }));
}

/** Read only text from the helper-owned markup, without introducing a DOM. */
function markupText(html: string): string {
    return html
        .replace(/<svg\b[^>]*>[\s\S]*?<\/svg>/g, '')
        .replace(/<[^>]*>/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

afterEach(() => vi.restoreAllMocks());

describe('buildAssetSyncToast', () => {
    it('reports an error when there is no result at all', () => {
        const toast = buildAssetSyncToast(null, 'ACME', tr);
        expect(toast.variant).toBe('error');
        expect(toast.message).toContain('prices.sync.noResponse');
    });

    it('is a success when something actually changed', () => {
        const toast = buildAssetSyncToast({status: 'ok', points_fetched: 10, points_changed: 3}, 'ACME', tr);
        expect(toast.variant).toBe('success');
        expect(toast.message).toContain('10↓ 3Δ');
        expect(toast.message).not.toContain('prices.sync.noChanges');
    });

    it('warns on a successful response that changed nothing', () => {
        // The point of the rule: the provider answered "ok" and wrote nothing.
        const toast = buildAssetSyncToast({status: 'ok', points_fetched: 40, points_changed: 0}, 'ACME', tr);
        expect(toast.variant).toBe('warning');
        expect(toast.message).toContain('prices.sync.noChanges');
    });

    it('stays a success when only the events changed', () => {
        const toast = buildAssetSyncToast({status: 'ok', points_changed: 0, events_fetched: 2, events_changed: 1}, 'ACME', tr);
        expect(toast.variant).toBe('success');
        expect(toast.message).toContain('2↓ 1Δ');
    });

    it('omits the event line when no events were fetched', () => {
        const withEvents = buildAssetSyncToast({status: 'ok', points_changed: 1, events_fetched: 3, events_changed: 2}, 'A', tr).message;
        const without = buildAssetSyncToast({status: 'ok', points_changed: 1, events_fetched: 0}, 'A', tr).message;
        expect(withEvents.split('\n').length).toBeGreaterThan(without.split('\n').length);
    });

    it('reads absent counters as zero rather than undefined', () => {
        const toast = buildAssetSyncToast({status: 'partial'}, 'ACME', tr);
        expect(toast.message).toContain('0↓ 0Δ');
        expect(toast.message).not.toContain('undefined');
    });

    describe('partial', () => {
        it('warns, and names the partial suffix', () => {
            const toast = buildAssetSyncToast({status: 'partial', points_fetched: 5, points_changed: 5}, 'ACME', tr);
            expect(toast.variant).toBe('warning');
            expect(toast.message).toContain('prices.sync.partialSuffix');
        });

        it('appends the provider explanation when there is one', () => {
            const detail = 'Current value only, history unavailable';
            const toast = buildAssetSyncToast({status: 'partial', message: detail}, 'ACME', tr);
            expect(toast.message).toContain(detail);
        });

        it('says nothing extra when the provider gave no explanation', () => {
            const toast = buildAssetSyncToast({status: 'partial', message: null}, 'ACME', tr);
            expect(toast.message.endsWith('Δ')).toBe(true);
        });
    });

    it('is informational when the asset was skipped', () => {
        const toast = buildAssetSyncToast({status: 'skipped'}, 'ACME', tr);
        expect(toast.variant).toBe('info');
        expect(toast.message).toContain('prices.sync.skippedSuffix');
    });

    describe('failure', () => {
        it('prefers the provider message when there is one', () => {
            const toast = buildAssetSyncToast({status: 'failed', message: 'HTTP 503'}, 'ACME', tr);
            expect(toast.variant).toBe('error');
            expect(toast.message).toContain('HTTP 503');
            expect(toast.message).not.toContain('prices.sync.failedDefault');
        });

        it('falls back to the generic wording when it does not', () => {
            const toast = buildAssetSyncToast({status: 'failed'}, 'ACME', tr);
            expect(toast.variant).toBe('error');
            expect(toast.message).toContain('prices.sync.failedDefault');
        });

        it('treats an unrecognised status as a failure', () => {
            // Anything the four known branches do not claim is not a success.
            expect(buildAssetSyncToast({status: 'something-new'}, 'ACME', tr).variant).toBe('error');
        });
    });
});

describe('buildFxSyncToast', () => {
    it('reports an error when there is no result at all', () => {
        const toast = buildFxSyncToast(null, 'EUR-USD', tr);
        expect(toast.variant).toBe('error');
    });

    it('is a success with the fetched/changed counts', () => {
        const toast = buildFxSyncToast({status: 'ok', points_fetched: 7, points_changed: 7}, 'EUR-USD', tr);
        expect(toast.variant).toBe('success');
        expect(toast.message).toContain('7↓ 7Δ');
        expect(toast.message.startsWith(`${tr('fx.sync.synced')}:\n`)).toBe(true);
    });

    it('reads absent counters as zero', () => {
        expect(buildFxSyncToast({status: 'ok'}, 'EUR-USD', tr).message).toContain('0↓ 0Δ');
    });

    it('keeps the default unlinked layout as heading, pair row, then counts/providers row', () => {
        mockPairCurrencies();
        const toast = buildFxSyncToast({status: 'ok', points_fetched: 9, points_changed: 4, provider_used: 'CHAIN:ECB+FED'}, 'JPY-RON', tr);

        expect(toast.message.split('\n').map(markupText)).toEqual([`${tr('fx.sync.synced')}:`, `${pairFlags.JPY} JPY ${pairFlags.RON} RON`, '9↓ 4Δ ECB → FED']);
    });

    describe('the provider chain', () => {
        it('renders a single provider', () => {
            const toast = buildFxSyncToast({status: 'ok', provider_used: 'MOCKFX'}, 'EUR-USD', tr);
            expect(toast.message).toContain('MOCKFX');
        });

        it('renders every leg of a CHAIN, joined by an arrow', () => {
            const toast = buildFxSyncToast({status: 'ok', provider_used: 'CHAIN:ECB+FED'}, 'EUR-CHF', tr);
            expect(toast.message).toContain('ECB');
            expect(toast.message).toContain('FED');
            expect(toast.message).toContain('→');
        });

        it('preserves repeated provider nodes and their order in a multi-hop chain', () => {
            const toast = buildFxSyncToast({status: 'ok', provider_used: 'CHAIN:MOCKFX+MOCKFX_FAIL+MOCKFX'}, 'JPY-RON', tr, undefined, undefined, {outerFlags: true, linkToDetail: true});
            expect(parseProviderChain('CHAIN:MOCKFX+MOCKFX_FAIL+MOCKFX')).toEqual(['MOCKFX', 'MOCKFX_FAIL', 'MOCKFX']);
            expect(markupText(toast.message)).toContain('MOCKFX → MOCKFX_FAIL → MOCKFX');
        });

        it('renders nothing at all when no provider was recorded', () => {
            const toast = buildFxSyncToast({status: 'ok', provider_used: null}, 'EUR-USD', tr);
            expect(toast.message).not.toContain('→');
            expect(toast.message).not.toContain('undefined');
        });
    });

    describe('partial', () => {
        it('warns and names the partial suffix', () => {
            const toast = buildFxSyncToast({status: 'partial', points_fetched: 2, points_changed: 1}, 'EUR-USD', tr);
            expect(toast.variant).toBe('warning');
            expect(toast.message).toContain('prices.sync.partialSuffix');
        });

        it('still shows which provider answered', () => {
            const toast = buildFxSyncToast({status: 'partial', points_fetched: 2, provider_used: 'CHAIN:ECB+SNB'}, 'EUR-CHF', tr);
            expect(toast.message).toContain('ECB');
            expect(toast.message).toContain('SNB');
        });

        it('appends whatever the detail formatter returns, and passes it the translator', () => {
            const formatDetail = vi.fn(() => '\nleg 1 failed');
            const result = {status: 'partial', points_fetched: 2, points_changed: 1};
            const toast = buildFxSyncToast(result, 'EUR-USD', tr, undefined, formatDetail);
            expect(toast.message).toContain('leg 1 failed');
            expect(formatDetail).toHaveBeenCalledWith(result, tr);
        });

        it('omits the detail when no formatter was supplied', () => {
            expect(buildFxSyncToast({status: 'partial'}, 'EUR-USD', tr).message).not.toContain('leg');
        });
    });

    it('is informational when the pair is manual-only', () => {
        const toast = buildFxSyncToast({status: 'skipped'}, 'EUR-USD', tr);
        expect(toast.variant).toBe('info');
        expect(toast.message).toContain('prices.sync.manualOnly');
    });

    describe('failure', () => {
        it('appends the provider message when there is one', () => {
            const toast = buildFxSyncToast({status: 'failed', message: 'rate limit'}, 'EUR-USD', tr);
            expect(toast.variant).toBe('error');
            expect(toast.message).toContain('rate limit');
        });

        it('says only the generic wording when there is not', () => {
            const toast = buildFxSyncToast({status: 'failed'}, 'EUR-USD', tr);
            expect(toast.variant).toBe('error');
            expect(toast.message).toContain('prices.sync.failedDefault');
        });

        it('treats an unrecognised status as a failure', () => {
            expect(buildFxSyncToast({status: 'weird'}, 'EUR-USD', tr).variant).toBe('error');
        });
    });

    it('renders a slug with no quote currency without inventing one', () => {
        // `fxPairHtml` splits on '-'; a malformed slug must not produce "undefined".
        expect(buildFxSyncToast({status: 'ok'}, 'EUR', tr).message).not.toContain('undefined');
    });

    describe('opt-in pair presentation', () => {
        beforeEach(() => {
            mockPairCurrencies();
        });

        it('uses the translated success prefix and one linked JPY / RON label between its flags', () => {
            const translate = vi.fn(tr);
            const toast = buildFxSyncToast({status: 'ok', points_fetched: 9, points_changed: 4, provider_used: 'CHAIN:MOCKFX+MOCKFX_FAIL+MOCKFX'}, 'JPY-RON', translate, undefined, undefined, {outerFlags: true, linkToDetail: true});

            expect(translate).toHaveBeenCalledWith('fx.sync.synced');
            expect(toast.variant).toBe('success');
            expect(toast.message.split('\n').map(markupText)).toEqual([`${tr('fx.sync.synced')}:`, `${pairFlags.JPY} JPY / RON ${pairFlags.RON} 9↓ 4Δ MOCKFX → MOCKFX_FAIL → MOCKFX`]);
            expect(toast.message).toContain('href="/fx/JPY-RON"');
            expect(toast.message).toContain('data-testid="toast-fx-link"');
            expect(toast.message.match(/<a\b/g)).toHaveLength(1);
        });

        it.each([
            {status: 'ok', variant: 'success', detail: '8↓ 3Δ'},
            {status: 'partial', variant: 'warning', detail: '[[leg-detail:unavailable]]'},
            {status: 'skipped', variant: 'info', detail: tr('prices.sync.manualOnly')},
            {status: 'failed', variant: 'error', detail: '[[provider-error]]'},
            {status: 'unknown-status', variant: 'error', detail: '[[provider-error]]'},
        ])('retains the $status variant and detail when only the pair label is linked', ({status, variant, detail}) => {
            const result = {status, points_fetched: 8, points_changed: 3, provider_used: 'CHAIN:MOCKFX+MOCKFX', message: '[[provider-error]]'};
            const formatDetail = vi.fn(() => '\n[[leg-detail:unavailable]]');
            const deprecatedFormatProvider = vi.fn(() => '[[deprecated-provider-formatter]]');
            const options = {outerFlags: true, linkToDetail: true};
            const plain = buildFxSyncToast(result, 'JPY-RON', tr, deprecatedFormatProvider, formatDetail);
            formatDetail.mockClear();
            const linked = buildFxSyncToast(result, 'JPY-RON', tr, deprecatedFormatProvider, formatDetail, options);

            expect(plain.variant).toBe(variant);
            expect(linked.variant).toBe(variant);

            const plainPair = fxPairHtml('JPY-RON');
            const linkedPair = fxPairHtml('JPY-RON', options);
            const isSharedFormatterStatus = status === 'ok' || status === 'partial';
            const expectedMessage = isSharedFormatterStatus ? plain.message.replace(`${plainPair}\n`, `${linkedPair} `) : plain.message.replace(plainPair, linkedPair);
            expect(linked.message).toBe(expectedMessage);
            expect(linked.message).toContain(detail);
            expect(linked.message).toContain('href="/fx/JPY-RON"');
            expect(linked.message.match(/<a\b/g)).toHaveLength(1);
            expect(deprecatedFormatProvider).not.toHaveBeenCalled();
            if (status === 'partial') {
                expect(formatDetail).toHaveBeenCalledTimes(1);
                expect(formatDetail).toHaveBeenCalledWith(result, tr);
            } else {
                expect(formatDetail).not.toHaveBeenCalled();
            }

            if (isSharedFormatterStatus) {
                expect(linked.message.split('\n').map(markupText)).toEqual([`${status === 'ok' ? tr('fx.sync.synced') : tr('prices.sync.partialSuffix')}:`, `${pairFlags.JPY} JPY / RON ${pairFlags.RON} 8↓ 3Δ MOCKFX → MOCKFX`, ...(status === 'partial' ? ['[[leg-detail:unavailable]]'] : [])]);
            } else if (status === 'skipped') {
                expect(linked.message.split('\n').map(markupText)).toEqual([`${tr('prices.sync.skippedSuffix')}:`, `${pairFlags.JPY} JPY / RON ${pairFlags.RON}`, tr('prices.sync.manualOnly')]);
            }
        });

        it('retains the missing-response error rather than manufacturing a linked success', () => {
            const plain = buildFxSyncToast(null, 'JPY-RON', tr);
            const linked = buildFxSyncToast(null, 'JPY-RON', tr, undefined, undefined, {outerFlags: true, linkToDetail: true});

            expect(linked).toEqual(plain);
            expect(linked.variant).toBe('error');
            expect(linked.message).not.toContain('<a');
        });
    });
});

describe('fxPairHtml — shared default and creation opt-ins', () => {
    beforeEach(() => {
        mockPairCurrencies();
    });

    it.each([undefined, {}, {outerFlags: false, linkToDetail: false}] satisfies Array<FxPairHtmlOptions | undefined>)('keeps the legacy arrow and quote-before-currency flag order with options %j', (options) => {
        const html = fxPairHtml('JPY-RON', options);

        expect(markupText(html)).toBe(`${pairFlags.JPY} JPY ${pairFlags.RON} RON`);
        expect(html).toContain('<svg');
        expect(html).not.toContain('<a');
        expect(currencyStore.getCurrencyInfo).toHaveBeenCalledWith('JPY');
        expect(currencyStore.getCurrencyInfo).toHaveBeenCalledWith('RON');
    });

    it('places outer flags around one unlinked JPY / RON label', () => {
        const html = fxPairHtml('JPY-RON', {outerFlags: true});

        expect(markupText(html)).toBe(`${pairFlags.JPY} JPY / RON ${pairFlags.RON}`);
        expect(html).not.toContain('<a');
        expect(html).not.toContain('<svg');
    });

    it.each([{linkToDetail: true}, {outerFlags: true, linkToDetail: true}])('links only the currency label and keeps each flag outside with options %j', (options) => {
        const html = fxPairHtml('JPY-RON', options);

        expect(markupText(html)).toBe(`${pairFlags.JPY} JPY / RON ${pairFlags.RON}`);
        expect(html).toContain('href="/fx/JPY-RON"');
        expect(html).toContain('data-testid="toast-fx-link"');
        expect(html).toMatch(/>JPY \/ RON<\/a>/);
        expect(html.indexOf(pairFlags.JPY)).toBeLessThan(html.indexOf('<a'));
        expect(html.indexOf(pairFlags.RON)).toBeGreaterThan(html.indexOf('</a>'));
        expect(html.match(/<a\b/g)).toHaveLength(1);
        expect(html).not.toContain('<svg');
    });

    it('takes both flags from currency metadata instead of a hardcoded pair table', () => {
        vi.mocked(currencyStore.getCurrencyInfo).mockImplementation((code) => ({
            code,
            name: code,
            symbol: code,
            flag_emoji: code === 'JPY' ? '[[base-flag]]' : '[[quote-flag]]',
            country_codes: [],
            country_names: [],
        }));

        expect(markupText(fxPairHtml('JPY-RON', {outerFlags: true}))).toBe('[[base-flag]] JPY / RON [[quote-flag]]');
        expect(currencyStore.getCurrencyInfo).toHaveBeenCalledTimes(2);
        expect(currencyStore.getCurrencyInfo).toHaveBeenCalledWith('JPY');
        expect(currencyStore.getCurrencyInfo).toHaveBeenCalledWith('RON');
    });

    it.each([{}, {outerFlags: true}])('escapes currency tokens without opting malformed input into navigation: %j', (options) => {
        const html = fxPairHtml('<img>&-"RON\'', options);

        expect(html).toContain('&lt;img&gt;&amp;');
        expect(html).toContain('&quot;RON&#39;');
        expect(html).not.toContain('<img>');
        expect(html).not.toContain('<a');
    });

    it('escapes the single-currency fallback without inventing a quote or link', () => {
        const html = fxPairHtml('<script>&');

        expect(html).toContain('&lt;script&gt;&amp;');
        expect(html).not.toContain('<script>');
        expect(html).not.toContain('undefined');
        expect(html).not.toContain('<a');
        expect(currencyStore.getCurrencyInfo).toHaveBeenCalledTimes(1);
        expect(currencyStore.getCurrencyInfo).toHaveBeenCalledWith('<script>&');
    });

    it('rejects malformed pair navigation instead of constructing an arbitrary href', () => {
        expect(() => fxPairHtml('JPY-RON" onclick="bad()', {linkToDetail: true})).toThrow('FX detail links require an AAA-BBB pair slug');
    });
});

describe('formatElapsed', () => {
    it('stays in milliseconds below a second', () => {
        expect(formatElapsed(0)).toBe('0ms');
        expect(formatElapsed(999)).toBe('999ms');
    });

    it('switches to seconds with one decimal at a second', () => {
        expect(formatElapsed(1000)).toBe('1.0s');
        expect(formatElapsed(1500)).toBe('1.5s');
        expect(formatElapsed(12340)).toBe('12.3s');
    });

    it('rounds to the tenth, and inherits toFixed for the halves', () => {
        // 1.45 has no exact binary form, so `toFixed(1)` rounds it *down*. Worth
        // pinning rather than discovering: a test written against "round half up"
        // fails here and looks like a bug in the formatter.
        expect(formatElapsed(1450)).toBe('1.4s');
        expect(formatElapsed(1451)).toBe('1.5s');
    });
});

describe('formatTime', () => {
    it('shows bare seconds below a minute', () => {
        expect(formatTime(0)).toBe('0s');
        expect(formatTime(59)).toBe('59s');
    });

    it('shows m:ss from a minute up, padding the seconds', () => {
        expect(formatTime(60)).toBe('1:00');
        expect(formatTime(65)).toBe('1:05');
        expect(formatTime(600)).toBe('10:00');
    });
});
