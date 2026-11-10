// @vitest-environment jsdom
/**
 * PortfolioToolbar — the Refresh button while the live prices are paused (F-4; Vitest + jsdom).
 *
 * While the live prices wait for the user (`liveState === 'paused-idle'`, FB-28) the toolbar draws no extra pill and its label does not change:
 * the Refresh button keeps its shape, its width and its word, and only its icon and its tone change, with a tooltip that says the updates are
 * paused. It is one and the same element (same test id), and a click does what Refresh does. The picker, the currency select, the broker filter and the AI Export menu are
 * replaced by no-op components: they have their own specs.
 *
 * Nothing translated is asserted: the label is checked as «not empty, not a raw key».
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';

const mocks = vi.hoisted(() => ({noop: () => {}}));
vi.mock('$lib/components/ui/date/DateRangePicker.svelte', () => ({default: mocks.noop}));
vi.mock('$lib/components/ui/select/CurrencySearchSelect.svelte', () => ({default: mocks.noop}));
vi.mock('$lib/features/ai-export/AiExportMenu.svelte', () => ({default: mocks.noop}));
vi.mock('./BrokerFilterSelect.svelte', () => ({default: mocks.noop}));

import PortfolioToolbar from './PortfolioToolbar.svelte';
import {portfolioScopeProfile} from './portfolioScopeProfile';
import type {ActivePollingState} from '$lib/features/live-updates/activePolling';

beforeAll(async () => {
    await setupI18n();
});

function props(liveState: ActivePollingState, kind: 'portfolio' | 'broker' = 'portfolio', onrefresh: () => void = () => {}) {
    const profile = portfolioScopeProfile(kind === 'broker' ? {kind: 'broker', brokerId: 1} : {kind: 'portfolio'});
    return {
        profile,
        tabs: [],
        activeTab: 'panoramica',
        ontabchange: () => {},
        dateRangeCtl: {activePreset: null, displayStart: '2026-01-01', end: '2026-10-28', onDateRangeChange: () => {}},
        targetCurrency: 'EUR',
        baseCurrency: 'EUR',
        oncurrencychange: () => {},
        oncreateforex: () => {},
        brokers: [],
        selectedBrokerIds: [],
        brokerFilterActive: false,
        onselectbrokers: () => {},
        liveState,
        aiExport: {domain: profile.aiExport.domain, memoryKey: profile.aiExport.memoryKey, defaultSelectionId: profile.aiExport.defaultSelectionId, disabled: false, context: () => ({}) as never},
        onrefresh,
    };
}

describe('PortfolioToolbar — Refresh while the updates are paused (F-4)', () => {
    const iconOf = (button: HTMLElement) => button.querySelector('svg')?.getAttribute('class') ?? '';

    it.each(['running', 'stopped', 'paused-hidden'] as const)('draws the plain Refresh button while %s', (state) => {
        render(PortfolioToolbar, props(state) as never);
        const button = screen.getByTestId('sync-button');
        expect(button).toHaveAttribute('data-live-state', state);
        expect(screen.queryByTestId('sync-button-paused-icon')).toBeNull();
        expect(button.className).toContain('bg-lf-card');
    });

    it('draws no separate pill: the old «Updates paused» element is gone', () => {
        render(PortfolioToolbar, props('paused-idle') as never);
        expect(screen.queryByTestId('live-updates-status')).toBeNull();
    });

    it('while paused for inactivity the same button changes only its icon and its tone: same element, same word, same shape', async () => {
        const {rerender} = render(PortfolioToolbar, props('running') as never);
        const before = screen.getByTestId('sync-button');
        const word = before.textContent?.trim();
        const shape = before.className.split(/\s+/).filter((name) => /^(px|py|gap|rounded|border|flex|items|justify|text-xs|font)/.test(name) || name === 'whitespace-nowrap');
        expect(word, 'precondition: the button has its word').not.toBe('');
        const plainIcon = iconOf(before);

        await rerender(props('paused-idle') as never);

        const button = screen.getByTestId('sync-button');
        expect(button, 'the same element: nothing is swapped, nothing shifts').toBe(before);
        expect(button).toHaveAttribute('data-live-state', 'paused-idle');
        expect(button.textContent?.trim(), 'the word stays, so the width does not change').toBe(word);
        for (const name of shape) expect(button.className, `the shape class ${name} stays`).toContain(name);
        expect(screen.getByTestId('sync-button-paused-icon'), 'the pause icon').toBeInTheDocument();
        expect(iconOf(button)).not.toBe(plainIcon);
        expect(button.className, 'the tone of the old pill').not.toContain('bg-lf-card');
        expect(button.className).toContain('bg-lf-neutral');
    });

    it('its tooltip says the updates are paused and what the click does; no raw key', async () => {
        const {rerender} = render(PortfolioToolbar, props('running') as never);
        const plain = screen.getByTestId('sync-button').getAttribute('title');
        await rerender(props('paused-idle') as never);
        const hint = screen.getByTestId('sync-button').getAttribute('title') ?? '';
        expect(hint).not.toBe('');
        expect(hint).not.toContain('liveUpdates.');
        expect(hint, 'another tooltip than the plain one').not.toBe(plain);
    });

    it('goes back to the plain button when the prices resume', async () => {
        const {rerender} = render(PortfolioToolbar, props('paused-idle') as never);
        await rerender(props('running') as never);
        const button = screen.getByTestId('sync-button');
        expect(screen.queryByTestId('sync-button-paused-icon')).toBeNull();
        expect(button.className).toContain('bg-lf-card');
    });

    it.each(['running', 'paused-idle'] as const)('a click calls the page’s refresh, paused or not (%s)', async (state) => {
        const onrefresh = vi.fn();
        render(PortfolioToolbar, props(state, 'portfolio', onrefresh) as never);
        await fireEvent.click(screen.getByTestId('sync-button'));
        expect(onrefresh).toHaveBeenCalledTimes(1);
    });

    it('the broker’s page has the same button under its own test id', () => {
        render(PortfolioToolbar, props('paused-idle', 'broker') as never);
        const button = screen.getByTestId('broker-refresh');
        expect(button).toHaveAttribute('data-live-state', 'paused-idle');
        expect(screen.getByTestId('broker-refresh-paused-icon')).toBeInTheDocument();
    });
});
