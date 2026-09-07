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
 * On translations: `tr` is injected, so the tests pass the identity function.
 * The assertions are then about *which key* was chosen — which is stable across
 * the four languages — and never about the sentence it renders.
 *
 * `getCurrencyInfo` and `getCachedFxProviders` are left un-mocked on purpose:
 * both degrade to a documented default when their store is cold, so the real
 * provider-chain parsing stays under test instead of being replaced by a stub.
 */
import {describe, expect, it, vi} from 'vitest';
import {buildAssetSyncToast, buildFxSyncToast} from '../syncToastHelpers';
import {formatElapsed, formatTime} from '../syncHelpers';

/** Identity translator: assertions name the key, never its rendering. */
const tr = (key: string) => key;

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
    });

    it('reads absent counters as zero', () => {
        expect(buildFxSyncToast({status: 'ok'}, 'EUR-USD', tr).message).toContain('0↓ 0Δ');
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
