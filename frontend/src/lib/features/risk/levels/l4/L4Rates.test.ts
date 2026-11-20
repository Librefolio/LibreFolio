// @vitest-environment jsdom
/**
 * L4Rates — the rates scenario of one asset (RN-25), in its «What if…?» (Vitest + jsdom).
 *
 * The consultant's decisions (18/11/2026), pinned here:
 *   1. It says which duration it used: read in the Profile, from which source, on which day, how many years.
 *   2. Rates up or down, by half a point, one point or two: the figure of the answer the backend computed for that move
 *      (−duration × move), never one the page works out; switching asks nothing.
 *   3. The money on the position when the page states one; percentages only otherwise.
 *   4. The first-order caveat, always.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {get} from 'svelte/store';

// The enrichers' list names the source (`durationSource.ts`): an enricher, never a price provider.
vi.mock('$lib/api', async (importOriginal) => {
    const original = (await importOriginal()) as {zodiosApi: Record<string, unknown>};
    return {...original, zodiosApi: {...original.zodiosApi, list_enrichers_api_v1_assets_enrichers_get: vi.fn(async () => ({enrichers: [{code: 'borsa_italiana', name: 'Borsa Italiana'}], default_order: {}}))}};
});

import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import type {RiskAnalyticResult} from '$lib/features/risk/riskStore.svelte';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import L4Rates from './L4Rates.svelte';
import {dayFormatter} from '../../eligibility';

const STEPS = [0.005, 0.01, 0.02, -0.005, -0.01, -0.02];

function answer(duration = 1.8, source = 'borsa_italiana'): RiskAnalyticResult {
    return {
        instance_id: 'base-current_composition-rate_shock',
        analytic_code: 'rate_shock',
        status: 'ok',
        output: {kind: 'rate_shock', modified_duration: duration, duration_read_on: '2026-11-08', duration_source: source, scenarios: STEPS.map((move) => ({yield_change: move, price_change: -duration * move}))},
        metadata: {scope: 'asset'},
    } as unknown as RiskAnalyticResult;
}

beforeAll(async () => {
    await setupI18n('en');
});

afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

const root = () => screen.getByTestId('risk-rates');
const text = (testId: string) => (screen.getByTestId(testId).textContent ?? '').replace(/\s+/g, ' ').trim();

describe('L4Rates', () => {
    it('says the duration it used: the source by its enricher’s name, the day, the years', async () => {
        render(L4Rates, {props: {result: answer(), currency: 'EUR', scopeValue: null}});
        expect(root()).toHaveAttribute('data-source', 'borsa_italiana');
        expect(root()).toHaveAttribute('data-duration', '1.8');
        await waitFor(() => expect(text('risk-rates-source')).toContain('Borsa Italiana'));
        const source = text('risk-rates-source');
        expect(source).not.toContain('borsa_italiana');
        expect(source).toContain('1.8');
        expect(source).toContain('2026');
    });

    it('names a duration the user wrote with the Profile’s own words', () => {
        render(L4Rates, {props: {result: answer(1.8, 'user'), currency: 'EUR', scopeValue: null}});
        expect(text('risk-rates-source')).toContain(get(_)('assets.profile.edit.sourceUser'));
    });

    it('opens on rates up by one point, and reads the figure of that move from the answer', () => {
        render(L4Rates, {props: {result: answer(), currency: 'EUR', scopeValue: null}});
        expect(root()).toHaveAttribute('data-direction', 'up');
        expect(root()).toHaveAttribute('data-step', '0.01');
        expect(screen.getByTestId('risk-rates-result')).toHaveAttribute('data-price-change', String(-1.8 * 0.01));
        expect(text('risk-rates-result')).toBe(
            get(_)('risk.levels.l4.ratesFall', {values: {percent: '−1.8%', amount: ''}})
                .replace(/\s+/g, ' ')
                .trim(),
        );
    });

    it('rates down give the opposite figure, in the rising sentence', async () => {
        render(L4Rates, {props: {result: answer(), currency: 'EUR', scopeValue: null}});
        await fireEvent.click(screen.getByTestId('risk-rates-down'));
        expect(root()).toHaveAttribute('data-direction', 'down');
        expect(screen.getByTestId('risk-rates-result')).toHaveAttribute('data-price-change', String(-1.8 * -0.01));
        expect(text('risk-rates-result')).toContain('+1.8%');
    });

    it('switches the step among half a point, one and two', async () => {
        render(L4Rates, {props: {result: answer(), currency: 'EUR', scopeValue: null}});
        await fireEvent.click(screen.getByTestId('risk-rates-step-0.02'));
        expect(root()).toHaveAttribute('data-step', '0.02');
        expect(screen.getByTestId('risk-rates-result')).toHaveAttribute('data-price-change', String(-1.8 * 0.02));
        await fireEvent.click(screen.getByTestId('risk-rates-step-0.005'));
        expect(screen.getByTestId('risk-rates-result')).toHaveAttribute('data-price-change', String(-1.8 * 0.005));
    });

    it('adds the money on the position when the page states one', () => {
        render(L4Rates, {props: {result: answer(), currency: 'EUR', scopeValue: 8000}});
        expect(screen.getByTestId('risk-rates-amount')).toBeInTheDocument();
        cleanup();
        render(L4Rates, {props: {result: answer(), currency: 'EUR', scopeValue: null}});
        expect(screen.queryByTestId('risk-rates-amount')).toBeNull();
    });

    it('masks the money with privacy, and shows it again when it is turned off, without remounting', () => {
        render(L4Rates, {props: {result: answer(), currency: 'EUR', scopeValue: 10_000}});
        expect(text('risk-rates-amount')).toBe('· −€180.00');
        setPrivacyEnabled(true);
        flushSync();
        expect(text('risk-rates-amount')).toBe(`· −€${PRIVACY_PLACEHOLDER}`);
        setPrivacyEnabled(false);
        flushSync();
        expect(text('risk-rates-amount')).toBe('· −€180.00');
    });

    it('always carries the first-order caveat', () => {
        render(L4Rates, {props: {result: answer(), currency: 'EUR', scopeValue: null}});
        expect(text('risk-rates-caveat')).toBe(get(_)('risk.levels.l4.ratesCaveat'));
    });

    // D1c (plan 68 D1d): a «now» duration the source has not confirmed for more than 30 days is said not up to date, with
    // the day of its last confirmation, as the Profile says it; a fresh one, or one held by an older reading, says nothing.
    it('says the duration is not up to date when the profile marks it stale, with the day it was last confirmed', () => {
        const stale = answer();
        Object.assign(stale.output as Record<string, unknown>, {duration_confirmed_on: '2026-09-01', duration_stale: true});
        render(L4Rates, {props: {result: stale, currency: 'EUR', scopeValue: null}});
        expect(root()).toHaveAttribute('data-stale', 'true');
        expect(text('risk-rates-stale')).toBe(get(_)('risk.levels.l4.ratesStale', {values: {date: dayFormatter()('2026-09-01')}}));
    });

    it('says nothing of freshness when the duration is up to date or held by an older reading', () => {
        const fresh = answer();
        Object.assign(fresh.output as Record<string, unknown>, {duration_confirmed_on: '2026-11-10', duration_stale: false});
        render(L4Rates, {props: {result: fresh, currency: 'EUR', scopeValue: null}});
        expect(root()).toHaveAttribute('data-stale', 'false');
        expect(screen.queryByTestId('risk-rates-stale')).toBeNull();
        cleanup();
        // An older reading holds the analysis day: no confirmation day, never stale (the backend's rule).
        render(L4Rates, {props: {result: answer(), currency: 'EUR', scopeValue: null}});
        expect(root()).toHaveAttribute('data-stale', 'false');
        expect(screen.queryByTestId('risk-rates-stale')).toBeNull();
    });
});
