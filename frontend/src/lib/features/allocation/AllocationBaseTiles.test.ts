// @vitest-environment jsdom
/**
 * AllocationBaseTiles — the three boxes (Vitest + jsdom): every number is the backend's, amounts are masked under privacy
 * (and shown again when it is turned off), percentages never are.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it} from 'vitest';
import {cleanup, render, screen, setupI18n, within} from '$test/component';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import AllocationBaseTiles from './AllocationBaseTiles.svelte';
import {makeView} from './allocation.fixture';

beforeAll(async () => {
    await setupI18n();
});
beforeEach(() => setPrivacyEnabled(false));
afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

const text = (id: string) => screen.getByTestId(id).textContent ?? '';

describe('the base box', () => {
    it('shows the base, its share of the portfolio and the bar', () => {
        render(AllocationBaseTiles, {view: makeView(), testId: 't'});
        expect(text('t-base-amount')).toContain('36');
        expect(text('t-base-share')).toContain('46');
        expect(text('t-base-share'), 'the net worth, as the backend gave it').toContain('80');
        expect(screen.getByTestId('t-base-bar')).toHaveAttribute('data-share', '46.10');
    });

    it('a missing share (base at or below zero) draws an empty bar and no percentage', () => {
        render(AllocationBaseTiles, {view: makeView({base_share_of_portfolio: null}), testId: 't'});
        expect(screen.getByTestId('t-base-bar')).toHaveAttribute('data-share', '');
        expect(text('t-base-share')).not.toContain('%');
        expect(screen.getByTestId('t-base-bar').firstElementChild).toHaveStyle({width: '0%'});
    });
});

describe('the outside and excluded boxes', () => {
    it('lists every class left outside, none summed into an «others»', () => {
        render(AllocationBaseTiles, {view: makeView(), testId: 't'});
        const classes = screen.getAllByTestId('t-outside-class').map((el) => el.getAttribute('data-class'));
        expect(classes).toEqual(['BOND', 'FUND', 'Liquidity', 'CRYPTO', 'COMMODITY']);
    });

    it('says «nothing» when the filter leaves nothing out', () => {
        render(AllocationBaseTiles, {view: makeView({outside: {amount: '0.00', by_class: []}}), testId: 't'});
        expect(screen.queryAllByTestId('t-outside-class')).toHaveLength(0);
    });

    it('lists the excluded buckets and assets by name, and a fixed row only with an amount', () => {
        const view = makeView({
            excluded: {
                amount: '9000.00',
                by_bucket: [{key: 'Unknown', amount: '4120.00'}],
                by_asset: [{asset_id: 2, amount: '4000.00'}],
                unattributable: [
                    {reason: 'in_transit', amount: '0.00'},
                    {reason: 'no_country', amount: '880.00'},
                ],
            },
        });
        render(AllocationBaseTiles, {view, testId: 't'});
        expect(screen.getByTestId('t-excluded-bucket')).toHaveAttribute('data-key', 'Unknown');
        expect(within(screen.getByTestId('t-excluded-asset')).getByText(/Apple Inc\./)).toBeInTheDocument();
        const fixed = screen.getAllByTestId('t-excluded-unattributable').map((el) => el.getAttribute('data-reason'));
        expect(fixed, 'a zero row is not drawn').toEqual(['no_country']);
    });
});

describe('privacy', () => {
    it('masks every amount and keeps the percentages, in both directions, in place', async () => {
        render(AllocationBaseTiles, {view: makeView(), testId: 't'});
        const everyAmount = () => ['t-base-amount', 't-outside-amount', 't-excluded-amount'].map(text);
        for (const shown of everyAmount()) expect(shown).not.toContain(PRIVACY_PLACEHOLDER);

        setPrivacyEnabled(true);
        await Promise.resolve();
        for (const shown of everyAmount()) expect(shown).toContain(PRIVACY_PLACEHOLDER);
        expect(text('t-base-amount')).not.toContain('36');
        expect(text('t-base-share'), 'the percentage stays').toContain('46');
        expect(text('t-base-share'), 'the net worth in the line is an amount: masked').toContain(PRIVACY_PLACEHOLDER);
        expect(screen.getAllByTestId('t-outside-class')[0].textContent).toContain(PRIVACY_PLACEHOLDER);

        setPrivacyEnabled(false);
        await Promise.resolve();
        for (const shown of everyAmount()) expect(shown).not.toContain(PRIVACY_PLACEHOLDER);
        expect(text('t-base-amount')).toContain('36');
    });
});
