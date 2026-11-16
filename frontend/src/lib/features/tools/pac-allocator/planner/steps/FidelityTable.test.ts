// @vitest-environment jsdom
/**
 * The table «Maximum acceptable cost» (F3a of project 67, step 10a; M30–M33, N1).
 *
 * The figures are the backend preview's, as it gives them: no figure is computed here. Four rows of money in the wrong
 * place, the reference row marked; one column per level; the «Custom» column only while that choice is active and the
 * answer carries it (M32); «Target first» has no column, a line under the table says so (M33). While the preview waits
 * the figures stay, muted; after a failure the table goes and a line says why. Every figure is the user's money (derived
 * from the total): masked in privacy mode. Nothing reads translated text: figures are compared with the planner's own
 * formatter.
 */
import {flushSync, tick} from 'svelte';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, render, screen, setupI18n} from '$test/component';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import type {DraftFidelity} from '../draft.svelte';
import {formatExactMoneyCompact, formatExactMoneyPlain} from '../format';
import {PlannerPreview, type PreviewReady} from '../preview.svelte';
import {REBALANCER_PLANNER_PROFILE} from '../profile';
import FidelityTable from './FidelityTable.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

const money = (value: string) => ({value: {kind: 'finite_decimal' as const, value}, currency: 'EUR'});
const number = (value: string) => ({kind: 'finite_decimal' as const, value});
/** The table shows two significant digits and the symbol alone (G6-1), as the mockup («up to 4 €», «2,4 €»). */
const whole = (value: string) => formatExactMoneyCompact(money(value));

/** The mockup's table on 20 000 €, with the custom column at 60 € on the reference row. */
function ready(custom: boolean): PreviewReady {
    const row = (misplaced: string, reference: boolean, costs: [string, string, string], customCost: string) => ({
        misplaced: money(misplaced),
        reference,
        cost_aware: money(costs[0]),
        balanced: money(costs[1]),
        faithful: money(costs[2]),
        custom: custom ? money(customCost) : null,
    });
    return {
        operation: 'preview',
        result_state: 'preview_ready',
        availability: 'ready',
        valuation_currency: 'EUR',
        total: money('20000'),
        issues: [],
        limit_problems: [],
        items: [],
        table: {
            level_weights: {cost_aware: number('0.25'), balanced: number('1'), faithful: number('4')},
            rows: [row('200', false, ['1', '4', '16'], '2.4'), row('500', false, ['6.25', '25', '100'], '15'), row('1000', true, ['25', '100', '400'], '60'), row('2000', false, ['100', '400', '1600'], '240')],
        },
        custom: custom ? {distance_weight: number('0.6'), reference_amount: money('60')} : null,
    };
}

function previewWith(state: PlannerPreview['state'], numbers: PreviewReady | null, reason: string | null = null): PlannerPreview {
    const preview = new PlannerPreview({call: vi.fn(), blocked: () => false});
    preview.state = state;
    preview.numbers = numbers;
    preview.reason = reason;
    return preview;
}

const BALANCED: DraftFidelity = {kind: 'level', level: 'balanced'};

function mount(preview: PlannerPreview | null, fidelity: DraftFidelity = BALANCED): void {
    render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: FidelityTable, childProps: {preview, fidelity}}});
    flushSync();
}

function cells(level: string): string[] {
    return screen
        .getAllByTestId('rebalancer-planner-fidelity-cell')
        .filter((cell) => cell.getAttribute('data-level') === level)
        .map((cell) => cell.textContent?.trim() ?? '');
}

describe('the table «Maximum acceptable cost»', () => {
    it('shows the preview rows as they come, the reference row marked; no «Custom» column for a level', () => {
        mount(previewWith('ready', ready(false)));
        expect(cells('misplaced').map((text, index) => text.includes(whole(['200', '500', '1000', '2000'][index])))).toEqual([true, true, true, true]);
        expect(cells('balanced').map((text, index) => text.includes(whole(['4', '25', '100', '400'][index])))).toEqual([true, true, true, true]);
        expect(cells('faithful')[3]).toContain(whole('1600'));
        expect(cells('cost_aware')[1]).toContain(whole('6.25'));
        const reference = screen.getAllByTestId('rebalancer-planner-fidelity-cell').filter((cell) => cell.getAttribute('data-reference') === 'true' && cell.getAttribute('data-level') === 'misplaced');
        expect(reference.map((cell) => cell.textContent)).toHaveLength(1);
        expect(reference[0].textContent).toContain(whole('1000'));
        expect(cells('custom')).toEqual([]);
        expect(screen.getByTestId('rebalancer-planner-fidelity-target-first')).toBeTruthy();
        expect(screen.getByTestId('rebalancer-planner-fidelity-total').textContent).toContain(formatExactMoneyPlain(money('20000')));
    });

    it('the «Custom» column is there while that choice is active and the answer carries it', () => {
        mount(previewWith('ready', ready(true)), {kind: 'custom', lambda: '0.6'});
        expect(cells('custom').map((text, index) => text.includes(whole(['2.4', '15', '60', '240'][index])))).toEqual([true, true, true, true]);
        // G6-2: the «Custom» column stands out; the levels do not.
        const highlighted = (level: string) =>
            screen
                .getAllByTestId('rebalancer-planner-fidelity-cell')
                .filter((cell) => cell.getAttribute('data-level') === level)
                .map((cell) => cell.getAttribute('data-highlight'));
        expect(highlighted('custom')).toEqual(['true', 'true', 'true', 'true']);
        expect(highlighted('balanced')).toEqual(['false', 'false', 'false', 'false']);
        cleanup();

        // Another choice: the column goes, even if the answer still carries it.
        mount(previewWith('ready', ready(true)), BALANCED);
        expect(cells('custom')).toEqual([]);
    });

    it('stale figures stay, marked; a failed preview removes the table and says why', () => {
        mount(previewWith('waiting', ready(false)));
        expect(screen.getByTestId('rebalancer-planner-fidelity').getAttribute('data-stale')).toBe('true');
        expect(cells('balanced')).toHaveLength(4);
        cleanup();

        mount(previewWith('error', null, 'allocation.price_missing'));
        expect(screen.queryAllByTestId('rebalancer-planner-fidelity-cell')).toHaveLength(0);
        expect(screen.getByTestId('rebalancer-planner-fidelity-reason').getAttribute('data-reason')).toBe('allocation.price_missing');
    });

    it('every figure is masked in privacy mode, both ways', async () => {
        mount(previewWith('ready', ready(false)));
        const shown = whole('400');

        setPrivacyEnabled(true);
        flushSync();
        await tick();
        expect(cells('balanced').every((text) => text.includes(PRIVACY_PLACEHOLDER))).toBe(true);
        expect(cells('misplaced').every((text) => text.includes(PRIVACY_PLACEHOLDER))).toBe(true);
        expect(screen.getByTestId('rebalancer-planner-fidelity-total').textContent).toContain(PRIVACY_PLACEHOLDER);

        setPrivacyEnabled(false);
        flushSync();
        await tick();
        expect(cells('balanced')[3]).toContain(shown);
    });
});
