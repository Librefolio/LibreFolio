// @vitest-environment jsdom
/**
 * PortfolioRiskTab — the Risk tab moved out of the portfolio view (Y6-7, delivery 2; Vitest + jsdom).
 *
 * Three states, told apart by the owned brokers: known and some (the panel is mounted), known and none (a plain line), not
 * known yet (a spinner, not an empty tab). The panel never mounts before the owned brokers are known: asked without
 * `broker_ids` the backend would widen the scope to every broker the user can see. The panel itself has its own specs.
 *
 * A broker filter narrows the risk as it narrows every other tab (RSK-F, the developer, 24/11/2026): the panel asks over the
 * brokers of the summary on screen (`brokerIds`), so its money and its percentages answer one question.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {render, screen, setupI18n} from '$test/component';

const mocks = vi.hoisted(() => ({panel: vi.fn()}));
vi.mock('$lib/features/risk/levels/RiskLevelsPanel.svelte', () => ({default: mocks.panel}));

import PortfolioRiskTab from './PortfolioRiskTab.svelte';

beforeAll(async () => {
    await setupI18n();
});

const props = (overrides: Record<string, unknown> = {}) => ({
    testId: 'dashboard-risk-tab',
    canAsk: false,
    brokersReady: false,
    ownedBrokerIds: [] as number[],
    brokerIds: null as number[] | null,
    dateStart: '2026-01-01',
    dateEnd: '2026-06-30',
    targetCurrency: 'EUR',
    summary: null,
    refreshVersion: 0,
    onsynced: () => {},
    ...overrides,
});

describe('PortfolioRiskTab', () => {
    it('mounts the panel on the owned brokers once they are known', () => {
        mocks.panel.mockClear();
        const summary = {net_worth: {amount: '900'}, holdings: [{asset_id: 5}]};
        render(PortfolioRiskTab, props({canAsk: true, brokersReady: true, ownedBrokerIds: [3, 4], brokerIds: [4, 3], summary}));
        expect(mocks.panel).toHaveBeenCalledTimes(1);
        expect(screen.queryByTestId('dashboard-risk-no-owned')).toBeNull();
        expect(screen.queryByTestId('dashboard-risk-loading')).toBeNull();
        const panelProps = mocks.panel.mock.calls[0][1] as Record<string, unknown>;
        expect(panelProps.scope).toEqual({kind: 'portfolio', broker_ids: [4, 3]});
        expect(panelProps.internalSubset).toBe(false);
        expect(panelProps.wholeBroker).toBeFalsy();
        expect(panelProps.scopeValue).toBe(900);
    });

    it("with a broker filter, asks over the filtered brokers at the owner's share and says it reads a subset", () => {
        mocks.panel.mockClear();
        const summary = {net_worth: {amount: '250.5'}, holdings: [{asset_id: 8}]};
        render(PortfolioRiskTab, props({canAsk: true, brokersReady: true, ownedBrokerIds: [3, 4, 9], brokerIds: [4], summary}));
        const panelProps = mocks.panel.mock.calls[0][1] as Record<string, unknown>;
        expect(panelProps.scope).toEqual({kind: 'portfolio', broker_ids: [4]});
        expect(panelProps.internalSubset).toBe(true);
        expect(panelProps.wholeBroker).toBeFalsy();
        // The summary is the filtered report's: its net worth is the value of this very scope.
        expect(panelProps.scopeValue).toBe(250.5);
        expect(panelProps.assetIds).toEqual([8]);
    });

    it('never asks with no brokers: an empty set falls back to the owned ones', () => {
        mocks.panel.mockClear();
        render(PortfolioRiskTab, props({canAsk: true, brokersReady: true, ownedBrokerIds: [3, 4], brokerIds: []}));
        const panelProps = mocks.panel.mock.calls[0][1] as Record<string, unknown>;
        expect(panelProps.scope).toEqual({kind: 'portfolio', broker_ids: [3, 4]});
        expect(panelProps.internalSubset).toBe(false);
        expect(panelProps.scopeValue).toBeNull();
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

    it('asks the risk of one broker, whole, on a broker page — even before any owned broker is known', () => {
        mocks.panel.mockClear();
        const summary = {net_worth: {amount: '1234.5'}, holdings: [{asset_id: 5}, {asset_id: 5}, {asset_id: 6}]};
        render(PortfolioRiskTab, props({testId: 'broker-risk-tab', broker: {id: 7}, summary}));
        expect(screen.getByTestId('broker-risk-tab')).toBeInTheDocument();
        expect(screen.queryByTestId('dashboard-risk-loading')).toBeNull();
        expect(mocks.panel).toHaveBeenCalledTimes(1);
        const panelProps = mocks.panel.mock.calls[0][1] as Record<string, unknown>;
        expect(panelProps.scope).toEqual({kind: 'portfolio', broker_ids: [7]});
        expect(panelProps.wholeBroker).toBe(true);
        expect(panelProps.internalSubset).toBe(true);
        expect(panelProps.scopeValue).toBe(1234.5);
        expect(panelProps.assetIds).toEqual([5, 6]);
    });
});
