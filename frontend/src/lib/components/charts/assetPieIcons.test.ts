/**
 * assetPieIcons — which icon a slice of the asset pie wears (F-10, B8): the asset's own once it is known to load, else its type's; the cash's
 * the Liquidity one. The probe asks each URL once, and only a success changes anything.
 */
import {describe, expect, it, vi} from 'vitest';
import {assetSliceIconUrl, createIconProbe} from './assetPieIcons';
import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';

describe('assetSliceIconUrl', () => {
    const none: ReadonlySet<string> = new Set();

    it('the cash slice (no id) wears the Liquidity icon, whatever else it carries', () => {
        expect(assetSliceIconUrl({assetId: null, iconUrl: '/x.png', assetType: 'ETF'}, new Set(['/x.png']))).toBe(getAssetTypeIconUrl('LIQUIDITY'));
    });

    it('an own icon is used only once it is known to load; before that, and when it never does, the type’s', () => {
        const slice = {assetId: 7, iconUrl: 'https://example.test/logo.png', assetType: 'STOCK'};
        expect(assetSliceIconUrl(slice, none)).toBe(getAssetTypeIconUrl('STOCK'));
        expect(assetSliceIconUrl(slice, new Set(['https://example.test/logo.png']))).toBe('https://example.test/logo.png');
    });

    it('no own icon, an empty one, or a blank one: the type’s; no type either: the generic one', () => {
        expect(assetSliceIconUrl({assetId: 7, iconUrl: null, assetType: 'BOND'}, none)).toBe(getAssetTypeIconUrl('BOND'));
        expect(assetSliceIconUrl({assetId: 7, iconUrl: '  ', assetType: 'BOND'}, new Set(['  ']))).toBe(getAssetTypeIconUrl('BOND'));
        expect(assetSliceIconUrl({assetId: 7}, none)).toBe(getAssetTypeIconUrl(undefined));
    });
});

describe('createIconProbe', () => {
    const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

    it('asks each URL once, and tells the page after each icon that loads', async () => {
        const load = vi.fn(async (url: string) => url.endsWith('ok.png'));
        const onchange = vi.fn();
        const probe = createIconProbe(load, onchange);
        const slices = [
            {assetId: 1, iconUrl: '/a/ok.png'},
            {assetId: 2, iconUrl: '/b/dead.png'},
            {assetId: 3, iconUrl: '/a/ok.png'},
        ];
        probe.ask(slices);
        probe.ask(slices);
        await flush();
        expect(load).toHaveBeenCalledTimes(2);
        expect([...probe.loaded]).toEqual(['/a/ok.png']);
        expect(onchange, 'a failure changes nothing: the type’s icon is already drawn').toHaveBeenCalledTimes(1);
    });

    it('a loader that throws is a failed icon; slices with no id or no icon are not asked', async () => {
        const load = vi.fn(async () => {
            throw new Error('network');
        });
        const probe = createIconProbe(load, vi.fn());
        probe.ask([
            {assetId: 1, iconUrl: '/boom.png'},
            {assetId: null, iconUrl: '/cash.png'},
            {assetId: 2, iconUrl: ''},
            {assetId: 3},
        ]);
        await flush();
        expect(load).toHaveBeenCalledTimes(1);
        expect(probe.loaded.size).toBe(0);
    });

    it('after dispose a late answer changes nothing', async () => {
        let resolve: (ok: boolean) => void = () => {};
        const onchange = vi.fn();
        const probe = createIconProbe(() => new Promise<boolean>((done) => (resolve = done)), onchange);
        probe.ask([{assetId: 1, iconUrl: '/late.png'}]);
        probe.dispose();
        resolve(true);
        await flush();
        expect(onchange).not.toHaveBeenCalled();
    });
});
