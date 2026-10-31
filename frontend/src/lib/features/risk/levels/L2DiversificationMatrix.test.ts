// @vitest-environment jsdom
/**
 * L2Diversification — the matrix's orderings by type, sector and area (B7, Vitest + jsdom).
 *
 * The matrix (`CorrelationHeatmap`) offers the orderings by type, by sector and by area only when it is
 * handed the three maps of `createMatrixMetadata`. The Asset Global laboratory hands them; L2 on the
 * Dashboard and on a broker mounted the matrix with the names alone, so a reader there could sort by
 * similarity and by name and nothing else (V4 of A and of F, never done).
 *
 * Pinned, with the metadata read stood in for (no request leaves the test):
 *
 * - L2 asks for the metadata of the assets of the matrix, the ids of the answer, not any other list;
 * - with the three maps served, the matrix offers the three orderings beside the two it always had;
 * - with the read failed (empty maps) it offers only those two, and the matrix itself still draws.
 *
 * ECharts is a stand-in that records nothing: the matrix is not the subject, its buttons are.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const metadataStandIn = vi.hoisted(() => ({
    inputs: [] as Array<() => {assetIds: readonly number[]; language: string}>,
    maps: null as null | {
        types: ReadonlyMap<number, string | null>;
        sectors: ReadonlyMap<number, Readonly<Record<string, number>> | null>;
        regions: ReadonlyMap<number, Readonly<Record<string, number>> | null>;
    },
}));

vi.mock('$lib/features/risk/matrixMetadata.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/risk/matrixMetadata.svelte')>();
    return {
        ...actual,
        createMatrixMetadata: (inputs: () => {assetIds: readonly number[]; language: string}) => {
            metadataStandIn.inputs.push(inputs);
            return metadataStandIn.maps ?? actual.EMPTY_MATRIX_METADATA;
        },
    };
});

const echartsModule = vi.hoisted(() => ({
    init: (dom: unknown) => ({
        setOption: () => {},
        getDom: () => dom,
        on: () => {},
        off: () => {},
        dispatchAction: () => {},
        clear: () => {},
        resize: () => {},
        isDisposed: () => false,
        dispose: () => {},
    }),
}));
vi.mock('echarts', () => echartsModule);

vi.mock('$lib/api', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/api')>();
    return {
        ...actual,
        zodiosApi: new Proxy(
            {},
            {
                get: () => vi.fn(async () => ({items: [], buckets: [], fallback_emoji: ''})),
            },
        ),
    };
});

import {render, screen, setupI18n, waitFor} from '$test/component';
import type {RiskAnalyticResult} from '$lib/features/risk/riskStore.svelte';

import L2Diversification from './L2Diversification.svelte';

const [ALPHA, BETA, GAMMA] = [11, 12, 13];
const ASSET_NAMES = {[ALPHA]: 'Invented fund Alpha', [BETA]: 'Invented fund Beta', [GAMMA]: 'Invented fund Gamma'};

function cell(row: number, column: number, value: number) {
    return {row_asset_id: row, column_asset_id: column, value, observations: 250, coverage: 1, status: 'ok' as const};
}

/** A correlation shaped like the API's: three assets, the three pairs below the diagonal. */
const CORRELATION: RiskAnalyticResult = {
    instance_id: 'base-historical-correlation',
    analytic_code: 'correlation',
    status: 'ok',
    output: {kind: 'matrix', asset_ids: [ALPHA, BETA, GAMMA], cells: [cell(BETA, ALPHA, 0.8), cell(GAMMA, ALPHA, 0.1), cell(GAMMA, BETA, -0.2)]},
    metadata: null,
    warnings: [],
} as unknown as RiskAnalyticResult;

const SERVED = {
    types: new Map<number, string | null>([
        [ALPHA, 'ETF'],
        [BETA, 'STOCK'],
        [GAMMA, 'STOCK'],
    ]),
    sectors: new Map<number, Readonly<Record<string, number>> | null>([
        [ALPHA, {Technology: 1}],
        [BETA, {Technology: 1}],
        [GAMMA, {'Health Care': 1}],
    ]),
    regions: new Map<number, Readonly<Record<string, number>> | null>([
        [ALPHA, {USA: 1}],
        [BETA, {USA: 1}],
        [GAMMA, {ITA: 1}],
    ]),
};

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    metadataStandIn.inputs = [];
    metadataStandIn.maps = null;
});

function mount(): void {
    render(L2Diversification, {props: {contributionResult: null, correlationResult: CORRELATION, assetNames: ASSET_NAMES}});
}

const ORDERING = (mode: string) => `risk-correlation-ordering-${mode}`;

describe('L2Diversification — the matrix orders by type, sector and area (B7)', () => {
    it('asks for the metadata of the assets of the matrix, and of no other', async () => {
        mount();
        await waitFor(() => expect(screen.getByTestId(ORDERING('similarity'))).toBeTruthy());

        expect(metadataStandIn.inputs.length, 'L2 never asked for the matrix metadata: the orderings cannot appear').toBeGreaterThan(0);
        const asked = metadataStandIn.inputs[0]();
        expect(asked.assetIds).toEqual([ALPHA, BETA, GAMMA]);
    });

    it('offers all five orderings when the three maps are served', async () => {
        metadataStandIn.maps = SERVED;
        mount();
        await waitFor(() => expect(screen.getByTestId(ORDERING('similarity'))).toBeTruthy());

        for (const mode of ['similarity', 'type', 'sector', 'region', 'name']) {
            expect(screen.queryByTestId(ORDERING(mode)), `the matrix of L2 does not offer the ordering "${mode}"`).not.toBeNull();
        }
    });

    it('offers only similarity and name when the metadata read gave nothing, and still draws the matrix', async () => {
        mount();
        await waitFor(() => expect(screen.getByTestId(ORDERING('similarity'))).toBeTruthy());

        expect(screen.queryByTestId(ORDERING('name'))).not.toBeNull();
        for (const mode of ['type', 'sector', 'region']) {
            expect(screen.queryByTestId(ORDERING(mode)), `"${mode}" is offered with no data to order by`).toBeNull();
        }
        expect(screen.queryByTestId('risk-l2-correlation')).not.toBeNull();
    });
});
