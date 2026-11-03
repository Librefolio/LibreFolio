// @vitest-environment jsdom
/**
 * PortfolioRiskTab — the Risk tab moved out of the portfolio view (Y6-7, delivery 2; Vitest + jsdom).
 *
 * Three states, told apart by the owned brokers: known and some (the panel is mounted), known and none (a plain line), not
 * known yet (a spinner, not an empty tab). The panel never mounts before the owned brokers are known: asked without
 * `broker_ids` the backend would widen the scope to every broker the user can see. The panel itself has its own specs.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {render, screen, setupI18n} from '$test/component';

const mocks = vi.hoisted(() => ({panel: vi.fn()}));
vi.mock('$lib/features/risk/levels/RiskLevelsPanel.svelte', () => ({default: mocks.panel}));

import PortfolioRiskTab from './PortfolioRiskTab.svelte';

beforeAll(async () => {
    await setupI18n();
});

const props = (overrides: Record<string, unknown> = {}) => ({canAsk: false, brokersReady: false, ownedBrokerIds: [] as number[], dateStart: '2026-01-01', dateEnd: '2026-06-30', targetCurrency: 'EUR', summary: null, brokerFilterActive: false, refreshVersion: 0, onsynced: () => {}, ...overrides});

describe('PortfolioRiskTab', () => {
    it('mounts the panel on the owned brokers once they are known', () => {
        mocks.panel.mockClear();
        render(PortfolioRiskTab, props({canAsk: true, brokersReady: true, ownedBrokerIds: [3, 4]}));
        expect(mocks.panel).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('dashboard-risk-no-owned')).toBeNull();
        expect(screen.queryByTestId('dashboard-risk-loading')).toBeNull();
    });

    it('says there is nothing when the brokers are known and the user owns none', () => {
        mocks.panel.mockClear();
        render(PortfolioRiskTab, props({brokersReady: true}));
        expect(screen.getByTestId('dashboard-risk-no-owned')).toBeInTheDocument();
        expect(mocks.panel).not.toHaveBeenCalled();
    });

    it('shows the spinner, and does not mount the panel, while the owned brokers are loading', () => {
        mocks.panel.mockClear();
        render(PortfolioRiskTab, props());
        expect(screen.getByTestId('dashboard-risk-loading')).toBeInTheDocument();
        expect(mocks.panel).not.toHaveBeenCalled();
    });
});
