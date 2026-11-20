// @vitest-environment jsdom
/**
 * LimitProblems (F2 of project 67, coordinator's answer F2-Q2): the «Check the limits» box under the targets table.
 *
 * A minimum above the maximum names both limits, as the mockup does: «the minimum (2,000.00 €) is above the maximum
 * (1,000.00 €)». The amounts are wealth, so they are formatted here, where the line is drawn, through the planner's personal
 * formatter: privacy masks them, and the line follows the privacy switch both ways. A share is a percentage, public. The
 * other limit problems keep their own sentence. Read through test ids and data attributes; an amount is compared with the
 * formatter's own output, never with a sentence.
 */
import {flushSync, tick} from 'svelte';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

// source.ts, the tool client and the currency catalogue import the API client. Nothing here talks to a server.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, render, screen, setupI18n} from '$test/component';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import {PlannerDraft, type DraftAsset} from '../draft.svelte';
import {formatPlannerMoneyPlain, formatPlannerPercentUnits} from '../format';
import LimitProblems from './LimitProblems.svelte';

beforeAll(async () => {
    await setupI18n();
    setPrivacyEnabled(false);
});

afterEach(() => {
    setPrivacyEnabled(false);
    cleanup();
});

function asset(draft: PlannerDraft, name: string): DraftAsset {
    return {
        key: draft.nextId('manual-asset'),
        origin: 'manual',
        sourceAssetId: null,
        name,
        ticker: '',
        assetClass: 'etf',
        iconUrl: null,
        active: true,
        price: {amount: '10', currency: 'EUR', quoteBaseQuantity: '1', referenceDate: '2026-09-16'},
        priceManual: false,
        copiedPrice: null,
        priceStamp: null,
        priceSource: null,
        exposures: [],
        copiedExposures: null,
        exposureStamp: null,
        enteredAt: '2026-09-16T12:00:00Z',
    };
}

function draftWith(limits: {minimum: string; maximum: string}[]): {draft: PlannerDraft; keys: string[]} {
    const draft = new PlannerDraft('EUR', 'proportional');
    const keys = limits.map((pair, index) => {
        const item = asset(draft, `Probe ${index + 1}`);
        draft.addAsset(item);
        draft.setLimit(item.key, 'minimum', pair.minimum);
        draft.setLimit(item.key, 'maximum', pair.maximum);
        return item.key;
    });
    return {draft, keys};
}

async function mount(draft: PlannerDraft): Promise<void> {
    render(LimitProblems, {draft});
    flushSync();
    await tick();
}

const row = (key: string) => screen.getByTestId('pac-planner-targets-limits-problems').querySelector<HTMLElement>(`[data-key="${key}"]`) as HTMLElement;

describe('LimitProblems', () => {
    it('a minimum above the maximum names both amounts, formatted as personal money', async () => {
        const {draft, keys} = draftWith([{minimum: '2000', maximum: '1000'}]);
        await mount(draft);

        const line = row('limitMinAboveMax');
        expect(line.getAttribute('data-asset-key')).toBe(keys[0]);
        expect(line.querySelector('[data-side="minimum"]')?.textContent).toBe(formatPlannerMoneyPlain('2000', 'EUR'));
        expect(line.querySelector('[data-side="maximum"]')?.textContent).toBe(formatPlannerMoneyPlain('1000', 'EUR'));
    });

    it('privacy masks the amounts, and the line follows the switch both ways', async () => {
        const {draft} = draftWith([{minimum: '2000', maximum: '1000'}]);
        await mount(draft);
        const shown = row('limitMinAboveMax').querySelector('[data-side="minimum"]')?.textContent;

        setPrivacyEnabled(true);
        flushSync();
        await tick();
        expect(row('limitMinAboveMax').querySelector('[data-side="minimum"]')?.textContent).toContain(PRIVACY_PLACEHOLDER);
        expect(row('limitMinAboveMax').querySelector('[data-side="maximum"]')?.textContent).toContain(PRIVACY_PLACEHOLDER);
        expect(row('limitMinAboveMax').textContent).not.toContain('2,000');

        setPrivacyEnabled(false);
        flushSync();
        await tick();
        expect(row('limitMinAboveMax').querySelector('[data-side="minimum"]')?.textContent).toBe(shown);
    });

    it('two shares stay visible with privacy on: a percentage is public', async () => {
        const {draft} = draftWith([{minimum: '60%', maximum: '40%'}]);
        await mount(draft);
        setPrivacyEnabled(true);
        flushSync();
        await tick();

        expect(row('limitMinAboveMax').querySelector('[data-side="minimum"]')?.textContent).toBe(formatPlannerPercentUnits('60'));
        expect(row('limitMinAboveMax').textContent).not.toContain(PRIVACY_PLACEHOLDER);
    });

    it('the other limit problems keep their own line, and no problem renders no box', async () => {
        const {draft, keys} = draftWith([{minimum: 'abc', maximum: ''}]);
        await mount(draft);
        expect(row('limitInvalid').getAttribute('data-asset-key')).toBe(keys[0]);
        expect(row('limitInvalid').querySelector('[data-side]')).toBeNull();

        draft.setLimit(keys[0], 'minimum', '');
        flushSync();
        await tick();
        expect(screen.queryByTestId('pac-planner-targets-limits-problems')).toBeNull();
    });
});
