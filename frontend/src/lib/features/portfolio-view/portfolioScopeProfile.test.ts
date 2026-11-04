/**
 * The profile of a portfolio view's scope (Y6-7, delivery 3): the names and numbers the Dashboard and a broker's page do
 * NOT share, in one place.
 *
 * The two pages kept their own `data-testid`s, `pageBusy` keys, guide anchors and toolbar thresholds, and ~30 browser specs
 * read them: a prefix replaced by a rule would rename some of them (`broker-holdings` is the broker's positions tab, not
 * `broker-positions-tab`; the refresh button is `sync-button` on one page and `broker-refresh` on the other). So every
 * name is spelled out here and pinned by this spec: it is the table those specs read.
 */
import {describe, expect, it} from 'vitest';
import {PORTFOLIO_TAB_IDS, busyKey, portfolioScopeProfile, tabsForProfile, type PortfolioTabId} from './portfolioScopeProfile';

const portfolio = portfolioScopeProfile({kind: 'portfolio'});
const broker = portfolioScopeProfile({kind: 'broker', brokerId: 7});

describe('portfolioScopeProfile · the Dashboard', () => {
    it('keeps the names the Dashboard has always had', () => {
        expect(portfolio.testIds).toEqual({
            root: 'dashboard-page',
            controls: 'dashboard-controls',
            filterRow: 'dashboard-filter-bar',
            refresh: 'sync-button',
            currency: 'dashboard-target-currency',
            overviewTab: 'dashboard-overview-tab',
            positionsTab: 'dashboard-positions-tab',
            riskTab: 'dashboard-risk-tab',
            transactionsTab: 'dashboard-transactions-tab',
            cashBalances: 'dashboard-cash-balances',
            cashBalance: 'dashboard-cash-balance',
        });
        expect(portfolio.tabs.map((tab) => [tab.id, tab.testId])).toEqual([
            ['panoramica', 'dashboard-tab-panoramica'],
            ['posizioni', 'dashboard-tab-posizioni'],
            ['rischio', 'dashboard-tab-risk'],
            ['transazioni', 'dashboard-tab-transazioni'],
        ]);
        expect(busyKey(portfolio, 'first-load')).toBe('dashboard-first-load');
        expect(busyKey(portfolio, 'contribution')).toBe('dashboard-contribution');
    });

    it('has no Info tab, a broker filter, a banner, and the period on its transactions', () => {
        expect(portfolio.tabs.some((tab) => tab.id === 'info')).toBe(false);
        expect(portfolio.hasBrokerFilter).toBe(true);
        expect(portfolio.showsBanners).toBe(true);
        expect(portfolio.transactionsFollowPeriod).toBe(true);
        expect(portfolio.aiExport).toEqual({domain: 'portfolio', memoryKey: 'portfolio', defaultSelectionId: 'portfolio.pac_planning'});
        expect(portfolio.rootGuideAnchor).toBe('page.dashboard');
        expect(portfolio.refreshBeforeAiExport).toBe(false);
    });

    it('keeps its toolbar thresholds', () => {
        expect(portfolio.toolbar).toEqual({
            thresholds: {oneRow: 1000, denseRow: 990, stackFilters: 510, oneColumn: 390, noExtraLabel: 410, labelHideActions: 210, labelHideTabs: 460},
            debugName: 'dashboard',
            pickerMaxWidthTwoRow: undefined,
        });
    });
});

describe('portfolioScopeProfile · a broker', () => {
    it('keeps the names the broker page has always had', () => {
        expect(broker.testIds).toEqual({
            root: 'broker-detail-page',
            controls: 'broker-controls',
            filterRow: 'broker-overview-controls',
            refresh: 'broker-refresh',
            currency: 'broker-detail-target-currency',
            overviewTab: 'broker-overview-tab',
            positionsTab: 'broker-holdings',
            riskTab: 'broker-risk-tab',
            transactionsTab: 'broker-transactions-tab',
            cashBalances: 'broker-cash-balances',
            cashBalance: 'broker-cash-balance',
        });
        expect(broker.tabs.map((tab) => [tab.id, tab.testId, tab.guideAnchor ?? null])).toEqual([
            ['panoramica', 'broker-tab-panoramica', 'broker.detail.overview'],
            ['posizioni', 'broker-tab-posizioni', 'broker.detail.positions'],
            ['rischio', 'broker-tab-risk', null],
            ['transazioni', 'broker-tab-transazioni', 'broker.detail.transactions'],
            ['info', 'broker-tab-info', 'broker.detail.info'],
        ]);
        expect(busyKey(broker, 'first-load')).toBe('broker-first-load');
        expect(busyKey(broker, 'refresh')).toBe('broker-refresh');
        expect(busyKey(broker, 'pnl-candles')).toBe('broker-pnl-candles');
    });

    it('has the Info tab, no broker filter, and its own AI export', () => {
        expect(broker.hasBrokerFilter).toBe(false);
        expect(broker.aiExport).toEqual({domain: 'broker', memoryKey: 'broker:7', defaultSelectionId: 'broker.review'});
        expect(broker.rootGuideAnchor).toBeNull();
        expect(broker.refreshBeforeAiExport).toBe(true);
        expect(broker.rootSpacing).toBe('space-y-6');
        expect(portfolio.rootSpacing).toBe('space-y-4');
    });

    it('counts the broker whole and asks as soon as the page opens, not when the owned brokers are known', () => {
        expect(broker.fullShare).toBe(true);
        expect(portfolio.fullShare).toBe(false);
        expect(broker.waitsForOwnedBrokers).toBe(false);
        expect(portfolio.waitsForOwnedBrokers).toBe(true);
    });

    it('keeps its toolbar thresholds and the wider period picker', () => {
        expect(broker.toolbar).toEqual({
            thresholds: {oneRow: 1000, denseRow: 840, stackFilters: 530, oneColumn: 430, labelHideActions: 270, labelHideTabs: 660},
            debugName: 'brokerDetail',
            pickerMaxWidthTwoRow: 470,
        });
    });

    it('stays on the whole history of its transactions until «Transactions in the period» (delivery 4)', () => {
        expect(broker.transactionsFollowPeriod).toBe(false);
        expect(broker.showsBanners).toBe(false);
    });
});

describe('tabsForProfile', () => {
    const label = (id: PortfolioTabId) => `label:${id}`;

    it('lists the tabs of the profile in order, with the label of each', () => {
        expect(tabsForProfile(portfolio, label).map((tab) => [tab.id, tab.label])).toEqual([
            ['panoramica', 'label:panoramica'],
            ['posizioni', 'label:posizioni'],
            ['rischio', 'label:rischio'],
            ['transazioni', 'label:transazioni'],
        ]);
        expect(tabsForProfile(broker, label).map((tab) => tab.id)).toEqual(['panoramica', 'posizioni', 'rischio', 'transazioni', 'info']);
    });

    it('knows every tab id, and the broker profile has them all', () => {
        expect([...PORTFOLIO_TAB_IDS]).toEqual(['panoramica', 'posizioni', 'rischio', 'transazioni', 'info']);
        expect(broker.tabs.map((tab) => tab.id)).toEqual([...PORTFOLIO_TAB_IDS]);
    });
});
