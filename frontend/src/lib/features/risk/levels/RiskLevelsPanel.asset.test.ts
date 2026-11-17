// @vitest-environment jsdom
/**
 * RiskLevelsPanel on one asset (RN-17, Q1, Q3, Q16): the Asset Detail's risk tab becomes the levels panel mounted on
 * the asset — an x-ray of that asset, with the levels that have meaning on one asset only.
 *
 * «Am I as diversified as I think?» (L2) has no data on one asset — correlation and risk contribution do not declare the
 * `asset` scope — so it is not drawn there, while the Dashboard keeps it. The catalogue is answered as fully capable
 * (`hasRiskCapability: () => true`), so the absence is the panel's own rule, not a capability filter.
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

import {get} from 'svelte/store';
import {cleanup, render, screen, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import type {RiskScope} from '$lib/features/risk/riskRequest';
import RiskLevelsPanel from './RiskLevelsPanel.svelte';

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

function mountPanel(scope: RiskScope) {
    return render(RiskLevelsPanel, {props: {scope, dateStart: '2025-01-01', dateEnd: '2025-12-31', targetCurrency: 'EUR'}});
}

describe('RiskLevelsPanel — on one asset, the levels that have meaning on one asset', () => {
    it('draws «How much can it hurt?», the benchmark level and «What if…?», and no «Am I diversified?»', async () => {
        mountPanel({kind: 'asset', asset_id: 7} as RiskScope);

        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-scope', 'asset');
        for (const level of [1, 3, 4]) expect(screen.getByTestId(`risk-level-${level}`), `level ${level} is missing on one asset`).toBeInTheDocument();
        expect(screen.queryByTestId('risk-level-2'), 'diversification drawn on one asset: there is nothing to diversify').toBeNull();
    });

    it('titles the benchmark level «Compared with a reference» on one asset, and keeps «Am I being paid?» on a portfolio', async () => {
        const t = get(_);
        const view = mountPanel({kind: 'asset', asset_id: 7} as RiskScope);
        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.getByTestId('risk-level-3-title').textContent?.trim()).toBe(t('risk.levels.l3.titleAsset'));
        view.unmount();

        mountPanel({kind: 'portfolio'} as RiskScope);
        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.getByTestId('risk-level-3-title').textContent?.trim()).toBe(t('risk.levels.l3.title'));
    });

    it('draws no sync button of its own on one asset: the Asset Detail toolbar has the page’s one Refresh (Y11)', async () => {
        mountPanel({kind: 'asset', asset_id: 7} as RiskScope);

        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.queryByTestId('risk-sync-button')).toBeNull();
    });

    it('keeps «Am I diversified?» on a portfolio: the Dashboard draws what it drew before', async () => {
        mountPanel({kind: 'portfolio'} as RiskScope);

        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.getByTestId('risk-level-2')).toBeInTheDocument();
    });
});
