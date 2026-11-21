// @vitest-environment jsdom
/**
 * LimitInputCell (F2 of project 67, M1 and M8): the two fields of the «Limits» column, minimum and maximum of an Asset's
 * final value, typed as an amount («500») or a percentage («35%»). Empty field = no limit.
 *
 * What the cell owns: writing each field into the draft as typed, and marking both fields red when the minimum is above
 * the maximum in the same form. «Continue» is stopped by the same check, through `localProblems` (the shell's `next()`
 * stops on any problem of the step). An empty field and a full one carry the same classes, so they are equally tall.
 * Read through test ids and ARIA states, never through the translated text.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';

// source.ts and the tool client import the API client. Nothing here talks to a server.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {PlannerDraft, type DraftAsset} from '../draft.svelte';
import {localProblems} from '../request';
import LimitInputCell from './LimitInputCell.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(cleanup);

function draftWithAsset(): {draft: PlannerDraft; assetKey: string} {
    const draft = new PlannerDraft('EUR', 'proportional');
    const asset: DraftAsset = {
        key: draft.nextId('manual-asset'),
        origin: 'manual',
        sourceAssetId: null,
        name: 'Cell probe',
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
    draft.addAsset(asset);
    draft.data.targets[asset.key] = '100';
    return {draft, assetKey: asset.key};
}

const minimum = () => screen.getByTestId('pac-planner-limit-minimum') as HTMLInputElement;
const maximum = () => screen.getByTestId('pac-planner-limit-maximum') as HTMLInputElement;

describe('LimitInputCell', () => {
    it('writes each field into the draft as typed, and an emptied entry leaves no trace', async () => {
        const {draft, assetKey} = draftWithAsset();
        render(LimitInputCell, {draft, assetKey, label: 'Cell probe'});

        await fireEvent.input(minimum(), {target: {value: '500'}});
        await fireEvent.input(maximum(), {target: {value: '35%'}});
        expect(draft.data.limits[assetKey]).toStrictEqual({minimum: '500', maximum: '35%'});

        await fireEvent.input(minimum(), {target: {value: ''}});
        await fireEvent.input(maximum(), {target: {value: ''}});
        expect(draft.data.limits).toStrictEqual({});
    });

    it('limit cell marks both fields and blocks Continue when min is above max', async () => {
        const {draft, assetKey} = draftWithAsset();
        render(LimitInputCell, {draft, assetKey, label: 'Cell probe'});
        expect(minimum().getAttribute('aria-invalid')).toBe('false');
        expect(maximum().getAttribute('aria-invalid')).toBe('false');

        await fireEvent.input(minimum(), {target: {value: '2000'}});
        await fireEvent.input(maximum(), {target: {value: '1000'}});

        expect(screen.getByTestId('pac-planner-limit').getAttribute('data-conflict')).toBe('true');
        expect(minimum().getAttribute('aria-invalid')).toBe('true');
        expect(maximum().getAttribute('aria-invalid')).toBe('true');
        expect(
            localProblems(draft)
                .filter((item) => item.step === 'targets')
                .map((item) => item.key),
        ).toEqual(['limitMinAboveMax']);

        // Different forms: the cell does not compare them, the backend does.
        await fireEvent.input(maximum(), {target: {value: '10%'}});
        expect(screen.getByTestId('pac-planner-limit').getAttribute('data-conflict')).toBe('false');
        expect(minimum().getAttribute('aria-invalid')).toBe('false');
    });

    it('marks only the field that is not a limit', async () => {
        const {draft} = draftWithAsset();
        render(LimitInputCell, {draft, assetKey: draft.data.assets[0].key, label: 'Cell probe'});

        await fireEvent.input(maximum(), {target: {value: '120%'}});

        expect(maximum().getAttribute('aria-invalid')).toBe('true');
        expect(minimum().getAttribute('aria-invalid')).toBe('false');
    });

    it('an empty field has the same classes, hence the same height, as a full one (M8)', async () => {
        const {draft, assetKey} = draftWithAsset();
        render(LimitInputCell, {draft, assetKey, label: 'Cell probe'});
        const emptyClass = minimum().className;
        expect(maximum().className).toBe(emptyClass);

        await fireEvent.input(minimum(), {target: {value: '500'}});

        expect(minimum().value).toBe('500');
        expect(minimum().className).toBe(emptyClass);
        expect(maximum().className).toBe(emptyClass);
    });
});
