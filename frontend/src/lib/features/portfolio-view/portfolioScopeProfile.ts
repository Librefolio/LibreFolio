/**
 * The profile of a portfolio view's scope (Y6-7, delivery 3).
 *
 * `PortfolioView` is one page with two users: the Dashboard (every broker the user owns, filterable) and a broker's page
 * (that one broker, whole). What they do NOT share is here, in one place: the `data-testid`s, the `pageBusy` keys, the guide
 * anchors, the toolbar thresholds and a few switches. Nothing is derived from a prefix: ~30 browser specs read these names and
 * they are not symmetrical (`broker-holdings` is the broker's positions tab; the refresh button is `sync-button` on one page and
 * `broker-refresh` on the other). `portfolioScopeProfile.test.ts` pins the table.
 *
 * Pure: no store, no network, no component state.
 */
import {ArrowRightLeft, Briefcase, Info, PieChart, Shield, TrendingUp} from 'lucide-svelte';
import type {ComponentType} from 'svelte';
import type {LayoutThresholds} from '$lib/utils/layout/responsiveLayout.svelte';

export type PortfolioViewScope = {kind: 'portfolio'} | {kind: 'broker'; brokerId: number};

export const PORTFOLIO_TAB_IDS = ['panoramica', 'posizioni', 'allocazione', 'rischio', 'transazioni', 'info'] as const;
export type PortfolioTabId = (typeof PORTFOLIO_TAB_IDS)[number];
export const DEFAULT_PORTFOLIO_TAB: PortfolioTabId = 'panoramica';

export interface PortfolioScopeTab {
    id: PortfolioTabId;
    icon: ComponentType;
    testId: string;
    guideAnchor?: string;
}

export interface PortfolioScopeTestIds {
    root: string;
    controls: string;
    filterRow: string;
    refresh: string;
    currency: string;
    overviewTab: string;
    positionsTab: string;
    allocationTab: string;
    riskTab: string;
    transactionsTab: string;
    cashBalances: string;
    cashBalance: string;
}

export interface PortfolioScopeProfile {
    kind: PortfolioViewScope['kind'];
    /** Prefix of the `pageBusy` keys (`<prefix>-first-load`, `-period`, `-currency`, `-refresh`, `-contribution`, …). */
    busyPrefix: 'dashboard' | 'broker';
    tabs: readonly PortfolioScopeTab[];
    testIds: PortfolioScopeTestIds;
    /** Guide anchor of the page root; the broker's is on its header, which the page owns. */
    rootGuideAnchor: string | null;
    rootSpacing: 'space-y-4' | 'space-y-6';
    toolbar: {thresholds: LayoutThresholds; debugName: string; pickerMaxWidthTwoRow: number | undefined};
    aiExport: {domain: 'portfolio' | 'broker'; memoryKey: string; defaultSelectionId: string};
    /** The toolbar's Refresh stands before the AI Export menu (the broker's order). */
    refreshBeforeAiExport: boolean;
    /** The toolbar has the broker multi-select. */
    hasBrokerFilter: boolean;
    /** The broker counts whole (`apply_ownership_share: false`, MF6-3, D4), not as the user's share of it. */
    fullShare: boolean;
    /** Nothing is asked before the owned brokers are known (F2): the Dashboard's scope IS those brokers. */
    waitsForOwnedBrokers: boolean;
}

const DASHBOARD_TESTIDS: PortfolioScopeTestIds = {
    root: 'dashboard-page',
    controls: 'dashboard-controls',
    filterRow: 'dashboard-filter-bar',
    refresh: 'sync-button',
    currency: 'dashboard-target-currency',
    overviewTab: 'dashboard-overview-tab',
    positionsTab: 'dashboard-positions-tab',
    allocationTab: 'dashboard-allocation-tab',
    riskTab: 'dashboard-risk-tab',
    transactionsTab: 'dashboard-transactions-tab',
    cashBalances: 'dashboard-cash-balances',
    cashBalance: 'dashboard-cash-balance',
};

const BROKER_TESTIDS: PortfolioScopeTestIds = {
    root: 'broker-detail-page',
    controls: 'broker-controls',
    filterRow: 'broker-overview-controls',
    refresh: 'broker-refresh',
    currency: 'broker-detail-target-currency',
    overviewTab: 'broker-overview-tab',
    positionsTab: 'broker-holdings',
    allocationTab: 'broker-allocation-tab',
    riskTab: 'broker-risk-tab',
    transactionsTab: 'broker-transactions-tab',
    cashBalances: 'broker-cash-balances',
    cashBalance: 'broker-cash-balance',
};

const DASHBOARD_TABS: readonly PortfolioScopeTab[] = [
    {id: 'panoramica', icon: Briefcase, testId: 'dashboard-tab-panoramica'},
    {id: 'posizioni', icon: TrendingUp, testId: 'dashboard-tab-posizioni'},
    {id: 'allocazione', icon: PieChart, testId: 'dashboard-tab-allocazione'},
    {id: 'rischio', icon: Shield, testId: 'dashboard-tab-risk'},
    {id: 'transazioni', icon: ArrowRightLeft, testId: 'dashboard-tab-transazioni'},
];

const BROKER_TABS: readonly PortfolioScopeTab[] = [
    {id: 'panoramica', icon: Briefcase, testId: 'broker-tab-panoramica', guideAnchor: 'broker.detail.overview'},
    {id: 'posizioni', icon: TrendingUp, testId: 'broker-tab-posizioni', guideAnchor: 'broker.detail.positions'},
    {id: 'allocazione', icon: PieChart, testId: 'broker-tab-allocazione', guideAnchor: 'broker.detail.allocation'},
    {id: 'rischio', icon: Shield, testId: 'broker-tab-risk'},
    {id: 'transazioni', icon: ArrowRightLeft, testId: 'broker-tab-transazioni', guideAnchor: 'broker.detail.transactions'},
    {id: 'info', icon: Info, testId: 'broker-tab-info', guideAnchor: 'broker.detail.info'},
];

export function portfolioScopeProfile(scope: PortfolioViewScope): PortfolioScopeProfile {
    if (scope.kind === 'broker') {
        return {
            kind: 'broker',
            busyPrefix: 'broker',
            tabs: BROKER_TABS,
            testIds: BROKER_TESTIDS,
            rootGuideAnchor: null,
            rootSpacing: 'space-y-6',
            toolbar: {
                // `labelHideTabs`: six tabs at 75 % take 690 px in Spanish, the widest (see the dashboard's note below).
                thresholds: {oneRow: 1000, denseRow: 840, stackFilters: 530, oneColumn: 430, labelHideActions: 270, labelHideTabs: 710},
                debugName: 'brokerDetail',
                pickerMaxWidthTwoRow: 470,
            },
            aiExport: {domain: 'broker', memoryKey: `broker:${scope.brokerId}`, defaultSelectionId: 'broker.review'},
            refreshBeforeAiExport: true,
            hasBrokerFilter: false,
            fullShare: true,
            waitsForOwnedBrokers: false,
        };
    }
    return {
        kind: 'portfolio',
        busyPrefix: 'dashboard',
        tabs: DASHBOARD_TABS,
        testIds: DASHBOARD_TESTIDS,
        rootGuideAnchor: 'page.dashboard',
        rootSpacing: 'space-y-4',
        toolbar: {
            // `labelHideTabs`: below it the tabs show their icons alone. A row of tabs shrinks its words to 75 % first, so the
            // threshold sits above the bar that holds them at that size in the widest language, Spanish: 596 px (it was 570,
            // and from 579 the last tab stood 17 px past the bar). Measured by toolbar-width-sweep in four languages, 25/11/2026.
            thresholds: {oneRow: 1000, denseRow: 990, stackFilters: 510, oneColumn: 390, noExtraLabel: 410, labelHideActions: 210, labelHideTabs: 610},
            debugName: 'dashboard',
            pickerMaxWidthTwoRow: undefined,
        },
        aiExport: {domain: 'portfolio', memoryKey: 'portfolio', defaultSelectionId: 'portfolio.pac_planning'},
        refreshBeforeAiExport: false,
        hasBrokerFilter: true,
        fullShare: false,
        waitsForOwnedBrokers: true,
    };
}

/** `dashboard-first-load` / `broker-first-load`: the key a `pageBusy` call of the view is tracked under. */
export function busyKey(profile: PortfolioScopeProfile, name: string): string {
    return `${profile.busyPrefix}-${name}`;
}

/** The tab bar's items of a profile, labelled by the caller (the labels are translated text). */
export function tabsForProfile(profile: PortfolioScopeProfile, label: (id: PortfolioTabId) => string) {
    return profile.tabs.map((tab) => ({id: tab.id, label: label(tab.id), icon: tab.icon, testId: tab.testId, ...(tab.guideAnchor ? {guideAnchor: tab.guideAnchor} : {})}));
}
