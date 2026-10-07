// @vitest-environment jsdom
/**
 * dashboardViewStore — the Dashboard's currency and broker filter last the session (page cache,
 * phase 1, decision E3), like the period already does in `dateRangeStore`.
 *
 * Today `targetCurrency` restarts from the base currency and `selectedBrokerIds` from "all" every
 * time the Dashboard mounts, so a return (the ‹ arrow, the sidebar) asks a report under another key
 * and the cache cannot serve it. The store holds the two choices:
 *
 *   - `readDashboardView()` → `{targetCurrency, brokerIds}`; `{targetCurrency: null, brokerIds: []}`
 *     when nothing was chosen;
 *   - `writeDashboardView(patch)` merges the patch and persists it in sessionStorage, per user — a
 *     reload in the same tab finds it again, another account never reads it;
 *   - a client-session reset (logout) clears it, in memory and in sessionStorage;
 *   - no sessionStorage (SSR) answers the defaults and never throws; a value stored malformed reads
 *     as the defaults.
 *
 * Every case starts from a fresh page: the module registry is reset, so the client session has not
 * resolved an identity yet — exactly what a reload does — and the first `transition()` runs no
 * resetter. sessionStorage, like the browser's, survives the reset; `beforeEach` empties it.
 *
 * jsdom for a real sessionStorage, and `browser: true`: the shared `$app/environment` mock answers
 * `browser: false`, which would turn any storage path guarded by it into a no-op.
 *
 * Red first: `dashboardViewStore.ts` does not exist yet. It is loaded by a computed specifier, so its
 * absence fails each case with the contract in the message rather than the whole file at import.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const BROWSER_ENVIRONMENT = vi.hoisted(() => ({browser: true, dev: true, building: false, version: 'test'}));
vi.mock('$app/environment', () => BROWSER_ENVIRONMENT);

const VIEW_MODULE = './dashboardViewStore';
const DEFAULTS = {targetCurrency: null, brokerIds: []};

interface DashboardView {
    targetCurrency: string | null;
    brokerIds: number[];
}

interface FreshPage {
    readDashboardView: () => DashboardView;
    writeDashboardView: (patch: Partial<DashboardView>) => void;
    /** The client session of this page: the first call resolves the identity and runs no resetter. */
    transition: (userId: number | string | null) => boolean;
}

/** A page load: fresh modules, the same sessionStorage. */
async function freshPage(): Promise<FreshPage> {
    vi.resetModules();
    const {transitionClientSession} = await import('$lib/stores/app/clientSession');
    let module: Record<string, unknown>;
    try {
        module = (await import(/* @vite-ignore */ VIEW_MODULE)) as Record<string, unknown>;
    } catch (error) {
        throw new Error(`src/lib/stores/portfolio/dashboardViewStore.ts does not exist yet: the Dashboard's currency and broker filter restart from the defaults on every return (${String(error)})`);
    }
    for (const name of ['readDashboardView', 'writeDashboardView']) {
        expect(typeof module[name], `dashboardViewStore exports no ${name}()`).toBe('function');
    }
    return {
        readDashboardView: module.readDashboardView as FreshPage['readDashboardView'],
        writeDashboardView: module.writeDashboardView as FreshPage['writeDashboardView'],
        transition: transitionClientSession,
    };
}

function storedKeys(): string[] {
    return Array.from({length: sessionStorage.length}, (_, index) => sessionStorage.key(index)).filter((key): key is string => key !== null);
}

beforeEach(() => {
    sessionStorage.clear();
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('dashboardViewStore (page cache, phase 1)', () => {
    it('reads the defaults when nothing was chosen', async () => {
        const page = await freshPage();
        page.transition(901);

        expect(page.readDashboardView()).toEqual(DEFAULTS);
    });

    it('merges what it writes', async () => {
        const page = await freshPage();
        page.transition(902);

        page.writeDashboardView({targetCurrency: 'USD'});
        page.writeDashboardView({brokerIds: [1, 5]});
        expect(page.readDashboardView(), 'a write replaced the view instead of merging into it').toEqual({targetCurrency: 'USD', brokerIds: [1, 5]});

        page.writeDashboardView({targetCurrency: 'CHF'});
        expect(page.readDashboardView()).toEqual({targetCurrency: 'CHF', brokerIds: [1, 5]});
    });

    it('keeps the view in sessionStorage: a reload in the same tab finds it again', async () => {
        const before = await freshPage();
        before.transition(903);
        before.writeDashboardView({targetCurrency: 'USD', brokerIds: [5]});
        expect(storedKeys().length, 'nothing was written to sessionStorage').toBeGreaterThan(0);

        const reloaded = await freshPage();
        reloaded.transition(903);

        expect(reloaded.readDashboardView(), 'the view lived in memory only: a reload lost it').toEqual({targetCurrency: 'USD', brokerIds: [5]});
    });

    it('keys the view by user: another account reads the defaults, also after a reload that ran no reset', async () => {
        const mine = await freshPage();
        mine.transition(904);
        mine.writeDashboardView({targetCurrency: 'USD', brokerIds: [5]});

        // A reload that resolves to another account: the first resolution runs no resetter, so only
        // the key can keep the view apart.
        const theirs = await freshPage();
        theirs.transition(905);
        expect(theirs.readDashboardView(), 'another account read this view: the sessionStorage key is not per user').toEqual(DEFAULTS);

        // …and the view is still there for its owner.
        const mineAgain = await freshPage();
        mineAgain.transition(904);
        expect(mineAgain.readDashboardView()).toEqual({targetCurrency: 'USD', brokerIds: [5]});
    });

    it('clears the view on a logout, in memory and in sessionStorage', async () => {
        const page = await freshPage();
        page.transition(906);
        page.writeDashboardView({targetCurrency: 'USD', brokerIds: [5]});

        page.transition(null);
        page.transition(906);
        expect(page.readDashboardView(), 'a logout kept the view').toEqual(DEFAULTS);

        const reloaded = await freshPage();
        reloaded.transition(906);
        expect(reloaded.readDashboardView(), 'a logout left the view in sessionStorage').toEqual(DEFAULTS);
    });

    it('reads a malformed stored value as the defaults', async () => {
        const page = await freshPage();
        page.transition(907);
        const before = new Set(storedKeys());
        page.writeDashboardView({targetCurrency: 'USD', brokerIds: [5]});
        const written = storedKeys().filter((key) => !before.has(key));
        expect(written.length, 'precondition: the view was persisted to sessionStorage').toBeGreaterThan(0);
        for (const key of written) sessionStorage.setItem(key, '{"targetCurrency": "USD", "brokerIds": [5');

        const reloaded = await freshPage();
        reloaded.transition(907);

        expect(() => reloaded.readDashboardView(), 'a malformed stored value broke the Dashboard').not.toThrow();
        expect(reloaded.readDashboardView()).toEqual(DEFAULTS);
    });

    it('answers the defaults and never throws without sessionStorage (SSR)', async () => {
        vi.doMock('$app/environment', () => ({...BROWSER_ENVIRONMENT, browser: false}));
        try {
            vi.stubGlobal('sessionStorage', undefined);
            const page = await freshPage();
            page.transition(908);

            expect(page.readDashboardView()).toEqual(DEFAULTS);
            expect(() => page.writeDashboardView({targetCurrency: 'USD', brokerIds: [5]}), 'a write without sessionStorage threw').not.toThrow();
        } finally {
            vi.doMock('$app/environment', () => BROWSER_ENVIRONMENT);
        }
    });
});
