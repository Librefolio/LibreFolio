/**
 * assetActions — the two actions every asset row and chart of the Positions tab offers (86, A11): one list, one order,
 * «Analyse lots» first, then «View asset».
 */
import {describe, expect, it, vi} from 'vitest';

const {goto} = vi.hoisted(() => ({goto: vi.fn(async () => undefined)}));
vi.mock('$app/navigation', () => ({goto}));

import {assetMenuItems, assetRowActions, runAssetAction} from './assetActions';

const t = (key: string) => `t:${key}`;

describe('assetMenuItems', () => {
    it('lists the analysis before the asset page, each with its icon and its translated label', () => {
        const items = assetMenuItems(t);
        expect(items.map((item) => item.id)).toEqual(['analyze-lots', 'view-asset']);
        expect(items.map((item) => item.label)).toEqual(['t:brokers.lots.analyze', 't:brokers.lots.viewAsset']);
        expect(items.every((item) => item.icon)).toBe(true);
    });
});

describe('runAssetAction', () => {
    it('runs the analysis, or goes to the asset page', () => {
        const onAnalyze = vi.fn();
        runAssetAction('analyze-lots', 7, onAnalyze);
        expect(onAnalyze).toHaveBeenCalledExactlyOnceWith(7);
        expect(goto).not.toHaveBeenCalled();
        runAssetAction('view-asset', 7, onAnalyze);
        expect(goto).toHaveBeenCalledExactlyOnceWith('/assets/7');
        expect(onAnalyze).toHaveBeenCalledTimes(1);
    });

    it('does nothing for a row without an asset, for an unknown action, or without an analysis handler', () => {
        goto.mockClear();
        const onAnalyze = vi.fn();
        runAssetAction('analyze-lots', null, onAnalyze);
        runAssetAction('view-asset', null, onAnalyze);
        runAssetAction('other', 7, onAnalyze);
        runAssetAction('analyze-lots', 7, undefined);
        expect(onAnalyze).not.toHaveBeenCalled();
        expect(goto).not.toHaveBeenCalled();
    });
});

describe('assetRowActions', () => {
    it('is the same list as rows actions, on the asset of the row, with the handler read when the action runs', () => {
        goto.mockClear();
        let handler: ((assetId: number) => void) | undefined;
        const actions = assetRowActions<{assetId: number | null}>({t, assetIdOf: (row) => row.assetId, onAnalyze: () => handler});
        expect(actions.map((action) => action.id)).toEqual(['analyze-lots', 'view-asset']);
        expect(actions.map((action) => (action.label as () => string)())).toEqual(['t:brokers.lots.analyze', 't:brokers.lots.viewAsset']);
        const late = vi.fn();
        handler = late;
        void actions[0].onClick({assetId: 9});
        expect(late).toHaveBeenCalledExactlyOnceWith(9);
        void actions[1].onClick({assetId: 9});
        expect(goto).toHaveBeenCalledExactlyOnceWith('/assets/9');
        void actions[0].onClick({assetId: null});
        expect(late).toHaveBeenCalledTimes(1);
    });
});
