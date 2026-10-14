// @vitest-environment jsdom
/**
 * BrokerBadge — U4 (C3): a badge for a broker without icon fields asks `GET /brokers/{id}` once.
 *
 * The defect, as a component: `BrokerBadge` derives a *new* `resolvedBroker` object at every
 * `brokerStoreVersion` bump, and `BrokerIcon` reads its props from it, so the icon's effect re-runs
 * at every bump and calls `ensureBrokerIconFieldsLoaded` again. For a broker that has none of
 * `icon_url`, `portal_url`, `default_import_plugin` the answer carries no icon field either, the
 * merge bumps the version, and the next GET follows — a loop paced only by the network. On the
 * Transactions page that was ~60 requests a second for one broker.
 *
 * The badge is mounted with the real store and the real icon; only the HTTP client is bounded. The
 * GET is a counted `vi.fn()` that answers a broker without icon fields, and any other endpoint is
 * recorded as a stray and fails the test.
 *
 * Why rounds and not a wait: the loop lives entirely in microtasks (the mocked GET resolves at
 * once, Svelte flushes through `queueMicrotask`), so there is no moment at which "it has settled"
 * could be awaited. A fixed number of rounds — flush, then let the microtask queue advance several
 * steps — gives a looping implementation many chances to ask again, and a correct one none. The
 * count after each round is kept, so a red shows how the requests grow.
 *
 * The component is unmounted inside each test, in `finally`: while the loop runs the microtask
 * queue never empties, and only destroying the badge's effects ends it.
 *
 * Nothing here reads a translated word, and the badge has no i18n to boot: the name is the one the
 * test passes in, and the elements are found by test id.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {render, screen} from '$test/component';

const api = vi.hoisted(() => ({
    getBroker: vi.fn(),
    /** Endpoints the badge reached that this file does not own. Must stay empty. */
    stray: [] as string[],
}));

// vi.mock is hoisted — the factory runs before the imports below.
vi.mock('$lib/api', () => {
    const endpoints: Record<string, unknown> = {
        get_broker_api_v1_brokers__broker_id__get: api.getBroker,
    };
    return {
        zodiosApi: new Proxy(endpoints, {
            get(target, key) {
                if (typeof key !== 'string') return undefined;
                if (key in target) return target[key];
                api.stray.push(key);
                return () => Promise.reject(new Error(`unexpected request in BrokerBadge tests: ${key}`));
            },
        }),
    };
});

import {mergeBrokers, resetBrokerStore} from '$lib/stores/reference/brokerStore';
import BrokerBadge from './BrokerBadge.svelte';

/** Rounds of re-rendering a looping badge gets to ask again. Fixed: the count, not a clock, decides. */
const ROUNDS = 10;
/** Microtask hops per round: each `tick()` is one hop followed by a synchronous flush. */
const HOPS_PER_ROUND = 5;

/** One round: flush pending effects, then let the microtask queue advance a few steps. */
async function round(): Promise<void> {
    flushSync();
    for (let hop = 0; hop < HOPS_PER_ROUND; hop++) await tick();
}

/** Run every round and return the GET count observed after each one. */
async function countsAfterEachRound(): Promise<number[]> {
    const counts: number[] = [];
    for (let index = 0; index < ROUNDS; index++) {
        await round();
        counts.push(api.getBroker.mock.calls.length);
    }
    return counts;
}

beforeEach(() => {
    resetBrokerStore();
    api.getBroker.mockReset();
    api.stray.length = 0;
});

afterEach(() => {
    expect(api.stray, 'the badge reached an endpoint these tests do not own').toEqual([]);
});

describe('BrokerBadge — broker icon hydration (C3)', () => {
    it('U4 · a badge for a broker without icon fields asks GET /brokers/{id} once, however many re-renders follow', async () => {
        mergeBrokers([{id: 1, name: 'No icons'}]);
        api.getBroker.mockResolvedValue({id: 1, name: 'No icons', icon_url: null, portal_url: null, default_import_plugin: null});

        const {unmount} = render(BrokerBadge, {broker: {id: 1, name: 'No icons'}});
        let counts: number[] = [];
        try {
            expect(screen.getByTestId('broker-badge-1'), 'precondition: the badge is mounted').toBeInTheDocument();
            counts = await countsAfterEachRound();
        } finally {
            unmount();
        }

        expect(api.getBroker, 'the badge asks about its own broker').toHaveBeenCalledWith(expect.objectContaining({params: {broker_id: 1}}));
        expect(api.getBroker, `GET /brokers/1 count after each of ${ROUNDS} rounds: [${counts.join(', ')}]`).toHaveBeenCalledTimes(1);
    });

    it('U4 control · a badge whose cached broker has a portal_url never asks, over the same rounds', async () => {
        mergeBrokers([{id: 2, name: 'With portal', portal_url: 'https://example.invalid'}]);
        api.getBroker.mockResolvedValue({id: 2, name: 'With portal', icon_url: null, portal_url: 'https://example.invalid', default_import_plugin: null});

        const {unmount} = render(BrokerBadge, {broker: {id: 2, name: 'With portal'}});
        let counts: number[] = [];
        try {
            counts = await countsAfterEachRound();
            // Presence barrier for the negative below: the cached portal reached BrokerIcon — the
            // very prop its effect reads — because the favicon it derives is on screen.
            const badge = screen.getByTestId('broker-badge-2');
            expect(badge.querySelector('img')?.getAttribute('src'), 'the cached portal_url drives the icon').toBe('https://example.invalid/favicon.ico');
        } finally {
            unmount();
        }

        expect(api.getBroker, `GET /brokers/2 count after each of ${ROUNDS} rounds: [${counts.join(', ')}]`).not.toHaveBeenCalled();
    });
});
