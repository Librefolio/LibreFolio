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

import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {get} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
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
    it('draws «How much can it hurt?», «How does it move?» and «What if…?» on one asset: no «Am I diversified?», no benchmark level', async () => {
        mountPanel({kind: 'asset', asset_id: 7} as RiskScope);

        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-scope', 'asset');
        for (const level of [1, 4]) expect(screen.getByTestId(`risk-level-${level}`), `level ${level} is missing on one asset`).toBeInTheDocument();
        expect(screen.queryByTestId('risk-level-2'), 'diversification drawn on one asset: there is nothing to diversify').toBeNull();
        // 81 U29 (developer, P-12): «Compared with a reference» — the picker and the table of one asset beside one reference — is gone.
        expect(screen.queryByTestId('risk-level-3'), 'the benchmark level is drawn on one asset').toBeNull();
        expect(screen.queryByTestId('risk-l3-benchmark'), 'the benchmark picker is drawn on one asset').toBeNull();
        expect(screen.queryByTestId('risk-l3'), 'the risk-adjusted table is drawn on one asset').toBeNull();
    });

    it('asks nothing for the benchmark level on one asset, and keeps asking it on a portfolio', async () => {
        const asked = () => JSON.stringify(queryRisk.mock.calls);
        const view = mountPanel({kind: 'asset', asset_id: 7} as RiskScope);
        await waitFor(() => expect(queryRisk).toHaveBeenCalled());
        expect(asked(), 'the asset asked for the risk/return scatter of a level it no longer draws').not.toContain('asset_risk_return');
        view.unmount();

        queryRisk.mockClear();
        mountPanel({kind: 'portfolio'} as RiskScope);
        await waitFor(() => expect(queryRisk).toHaveBeenCalled());
        expect(asked(), 'control: the portfolio still asks for the scatter, so the absence above is the asset rule').toContain('asset_risk_return');
    });

    // 81 U25: the rate is a condition of L1's semi-deviation too, so it stays on the asset, under the period line; on a
    // portfolio it sits in L3's row, beside «Compare with», and nowhere else on the page.
    it('puts the risk-free rate under the period line on one asset, and beside «Compare with» on a portfolio', async () => {
        const view = mountPanel({kind: 'asset', asset_id: 7} as RiskScope);
        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.getAllByTestId('risk-free-rate'), 'one field on the asset').toHaveLength(1);
        expect(screen.getByTestId('risk-period').parentElement?.contains(screen.getByTestId('risk-free-rate')), 'the asset’s field is not under the period line').toBe(true);
        view.unmount();

        mountPanel({kind: 'portfolio'} as RiskScope);
        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.getAllByTestId('risk-free-rate'), 'one field on the portfolio').toHaveLength(1);
        expect(screen.getByTestId('risk-l3-benchmark').contains(screen.getByTestId('risk-free-rate')), 'the portfolio’s field is not beside «Compare with»').toBe(true);
        expect(screen.getByTestId('risk-period').parentElement?.contains(screen.getByTestId('risk-free-rate')), 'the portfolio’s field is also under the period line').toBe(false);
    });

    it('keeps «Am I being paid?» on a portfolio, titled for a portfolio', async () => {
        const t = get(_);
        mountPanel({kind: 'portfolio'} as RiskScope);
        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.getByTestId('risk-level-3-title').textContent?.trim()).toBe(t('risk.levels.l3.title'));
    });

    it('draws no sync button of its own on one asset: the Asset Detail toolbar has the page’s one Refresh (Y11)', async () => {
        mountPanel({kind: 'asset', asset_id: 7} as RiskScope);

        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.queryByTestId('risk-sync-button')).toBeNull();
    });

    // RN-17 (c): the header's docs icon on one asset names the asset's questions and opens the Asset Detail's own page (no anchor, RN-13 B1),
    // not the Dashboard's «four questions of the Risk tab».
    it('points the docs icon at the Asset Detail’s page, in the asset’s words, and keeps the Dashboard’s on a portfolio', async () => {
        const t = get(_);
        const open = vi.spyOn(window, 'open').mockReturnValue(null);
        const view = mountPanel({kind: 'asset', asset_id: 7} as RiskScope);
        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        const icon = screen.getByTestId('risk-levels-docs');
        expect(icon).toHaveAttribute('aria-label', t('risk.docsHelp.headerAsset'));
        await fireEvent.click(icon);
        expect(open).toHaveBeenLastCalledWith('/mkdocs/user/assets/detail/', '_blank', 'noopener');
        view.unmount();

        mountPanel({kind: 'portfolio'} as RiskScope);
        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.getByTestId('risk-levels-docs')).toHaveAttribute('aria-label', t('risk.docsHelp.header'));
        open.mockRestore();
    });

    // RN-18 (Q22 a): «How does it move?» is one block on every surface, right after «How much can it hurt?».
    it('draws «How does it move?» right after «How much can it hurt?», on one asset and on a portfolio', async () => {
        for (const scope of [{kind: 'asset', asset_id: 7}, {kind: 'portfolio'}] as RiskScope[]) {
            const view = mountPanel(scope);
            await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
            const order = [...screen.getByTestId('risk-levels-panel').querySelectorAll('[data-level]')].map((section) => section.getAttribute('data-level'));
            expect(order.slice(0, 2), `${scope.kind}: the block is not second`).toEqual(['1', 'move']);
            expect(screen.getByTestId('risk-level-move')).toBeInTheDocument();
            view.unmount();
        }
    });

    it('keeps «Am I diversified?» on a portfolio: the Dashboard draws what it drew before', async () => {
        mountPanel({kind: 'portfolio'} as RiskScope);

        await waitFor(() => expect(screen.getByTestId('risk-levels-panel')).toHaveAttribute('data-catalog', 'ready'));
        expect(screen.getByTestId('risk-level-2')).toBeInTheDocument();
    });
});

const riskLevelsPanelSource = readFileSync(resolve(process.cwd(), 'src/lib/features/risk/levels/RiskLevelsPanel.svelte'), 'utf8');
const assetRiskTabSource = readFileSync(resolve(process.cwd(), 'src/lib/features/risk/AssetRiskTab.svelte'), 'utf8');

// The sync's completion travels unchanged from the modal to the page (the Asset Detail drops its comparison overlays only
// on an accepted sync): the header hands it to `controller.handleSynced` (`RiskPanelHeader.test.ts`), the controller to
// its `onsynced` (`riskPanelController.test.ts`); these two pin the last links, the panel and the Asset Detail's tab
// (RN-17 c; they replace the contracts of the legacy `RiskAnalysisPanel` → `AssetRiskScenariosView` chain, now gone).
describe('RiskLevelsPanel — the sync completion source contracts', () => {
    it('forwards the controller’s sync completion through RiskLevelsPanel unchanged', () => {
        expect(riskLevelsPanelSource).toMatch(/\bonsynced\?\s*:\s*\(\s*detail\s*:\s*RiskSyncCompletion\s*\)\s*=>\s*void\s*\|\s*Promise<void>\s*;/);
        expect(riskLevelsPanelSource, 'the controller option drops the detail').toMatch(/\bonsynced\s*:\s*\(\s*detail\s*\)\s*=>\s*onsynced\?\.\(\s*detail\s*\)\s*,/);
        expect(riskLevelsPanelSource).not.toMatch(/\bonsynced\s*:\s*\(\s*\)\s*=>/);
    });

    it('types and forwards the Asset Detail tab’s completion callback unchanged', () => {
        expect(assetRiskTabSource).toMatch(/\bonsynced\?\s*:\s*\(\s*detail\s*:\s*RiskSyncCompletion\s*\)\s*=>\s*void\s*\|\s*Promise<void>\s*;/);
        const propsBinding = assetRiskTabSource.match(/let\s*\{([\s\S]*?)\}\s*:\s*Props\s*=\s*\$props\(\)\s*;/)?.at(1) ?? '';
        expect(propsBinding).toMatch(/(?:^|,)\s*onsynced\s*(?:,|$)/);
        const panelTag = assetRiskTabSource.match(/<RiskLevelsPanel\b[\s\S]*?\/>/)?.at(0) ?? '';
        expect(panelTag).not.toBe('');
        expect(panelTag).toContain('{onsynced}');
        expect(panelTag).not.toMatch(/\bonsynced\s*=/);
    });
});
