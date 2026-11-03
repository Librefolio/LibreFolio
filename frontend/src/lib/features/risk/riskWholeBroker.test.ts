// @vitest-environment jsdom
/**
 * wholeBroker — the broker page's risk counts every broker whole (MF6-3, developer's decision D4; Vitest + jsdom).
 *
 * A portfolio scope says `apply_ownership_share`, true by default: an owner counts its share of each broker. The broker page shows
 * the broker's amounts whole, as an editor sees them, so the risk opened from that page asks for `false`, and its stress impacts and
 * scope value then match the page's. The panels take `wholeBroker` (default `false`) and put that field in the scope they query with:
 *
 * - `withWholeBroker(scope, true)` on a portfolio scope adds `apply_ownership_share: false` and keeps every other field;
 * - on any other kind of scope, or with `wholeBroker` false, the scope is handed back as it came: the Dashboard asks what it asked;
 * - `RiskLevelsPanel`, mounted with `wholeBroker`, sends that scope in every request of its waves, and without the prop sends what
 *   it always sent: the share applied, the generated schema's default (`true`).
 *
 * The data of the answers is not the subject: every question is answered with an empty list.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const fetchRiskCatalog = vi.hoisted(() => vi.fn());
const fetchRiskScenarioCatalog = vi.hoisted(() => vi.fn());
const queryRisk = vi.hoisted(() => vi.fn());
const invalidateRisk = vi.hoisted(() => vi.fn());

vi.mock('$lib/features/risk/riskStore.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/risk/riskStore.svelte')>();
    return {...actual, fetchRiskCatalog, fetchRiskScenarioCatalog, queryRisk, invalidateRisk, hasRiskCapability: () => true};
});

vi.mock('echarts', () => ({
    init: (dom: unknown) => ({
        setOption: () => {},
        getDom: () => dom,
        on: () => {},
        off: () => {},
        dispatchAction: () => {},
        clear: () => {},
        resize: () => {},
        isDisposed: () => false,
        dispose: () => {},
    }),
}));

import {cleanup, render, setupI18n, waitFor} from '$test/component';
import type {RiskQueryRequest, RiskScope} from '$lib/features/risk/riskRequest';
import {withWholeBroker} from '$lib/features/risk/riskRequest';
import RiskLevelsPanel from './levels/RiskLevelsPanel.svelte';

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    fetchRiskCatalog.mockReset().mockResolvedValue({items: []});
    fetchRiskScenarioCatalog.mockReset().mockResolvedValue({items: []});
    invalidateRisk.mockReset();
    queryRisk.mockReset().mockResolvedValue({items: []});
});

afterEach(() => {
    cleanup();
});

const BROKER_SCOPE = {kind: 'portfolio', broker_ids: [7]} as RiskScope;

describe('withWholeBroker', () => {
    it('asks a portfolio scope not to apply the ownership share, and keeps every other field', () => {
        expect(withWholeBroker(BROKER_SCOPE, true)).toEqual({kind: 'portfolio', broker_ids: [7], apply_ownership_share: false});
    });

    it('hands the scope back as it came without the prop', () => {
        expect(withWholeBroker(BROKER_SCOPE, false)).toBe(BROKER_SCOPE);
    });

    it('leaves a scope that is not a portfolio alone, whatever the prop says', () => {
        const asset = {kind: 'asset', asset_id: 4} as RiskScope;
        expect(withWholeBroker(asset, true)).toBe(asset);
    });
});

/** Every scope the panel put in a request, serialised once each. */
const scopesAsked = () => [...new Set(queryRisk.mock.calls.map(([request]) => JSON.stringify((request as RiskQueryRequest).scope)))];

function mountPanel(extra: Record<string, unknown> = {}) {
    return render(RiskLevelsPanel, {props: {scope: BROKER_SCOPE, dateStart: '2025-01-01', dateEnd: '2025-12-31', targetCurrency: 'EUR', ...extra}});
}

describe('RiskLevelsPanel — wholeBroker', () => {
    it('queries with apply_ownership_share false in every request when the prop is on', async () => {
        mountPanel({wholeBroker: true});

        await waitFor(() => expect(queryRisk).toHaveBeenCalled());
        expect(scopesAsked(), 'a request went out with the share applied: the broker page would show amounts that are not the page’s').toEqual([JSON.stringify({kind: 'portfolio', broker_ids: [7], apply_ownership_share: false})]);
    });

    it('keeps the share applied without the prop: the Dashboard asks what it asked before', async () => {
        mountPanel();

        await waitFor(() => expect(queryRisk).toHaveBeenCalled());
        expect(scopesAsked()).toEqual([JSON.stringify({kind: 'portfolio', broker_ids: [7], apply_ownership_share: true})]);
    });
});
