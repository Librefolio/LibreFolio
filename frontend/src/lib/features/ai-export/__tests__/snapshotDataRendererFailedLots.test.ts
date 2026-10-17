import {describe, expect, it} from 'vitest';

import {renderSnapshotDataText} from '../templates/snapshotDataRenderer';

/**
 * J-12 (decision N81, option A): an asset whose FIFO lot reconstruction FAILED is declared, never shown with wrong
 * figures. The backend moves the lot components with it (at most +1 over the released v1.2.1): `portfolio.fifo_lots` /
 * `broker.fifo_lots` 2 → 3 and `asset.lot_detail` 3 → 4, while both `*.fifo_summary` stay at 3 (already moved in this
 * cycle by J-17) and take the same fields:
 *
 * - the multi-asset components carry `failed_reconstruction_asset_count` and `failed_lot_reconstructions`, one row per
 *   FAILED asset with its identity and `failure_codes` only; the FAILED asset has no lot row and no asset row, and the
 *   summary's scope totals are null;
 * - `asset.lot_detail` carries `lot_reconstruction_status` and `failure_codes`; FAILED: no lot.
 *
 * A bumped version this renderer does not list in `COMPACT_COMPONENT_VERSIONS` silently falls back to YAML, so the map
 * moves in the same change (`ai-export-version-bump-once-per-release`). These tests pin the structure the generic
 * compact renderer gives the new fields — the failed asset by its prompt ref (A#), never its database id; its codes; the
 * status — and no prompt wording: texts are placeholders, cells are read by column header, rows found by what they hold.
 *
 * Today (base `2f4ef68e6`) `COMPACT_COMPONENT_VERSIONS` lists the FIFO lots {1, 2} and the lot detail {1, 2, 3}: a v3
 * FIFO lots section and a v4 lot detail section render as `PAYLOAD YAML FALLBACK`. The FIFO summary v3 is compact
 * already, so its case is a guard.
 */
describe('failed lot reconstruction (J-12)', () => {
    // Database ids no rendered cell may carry: distinctive, so a leak cannot hide among the figures.
    const COMPLETE_ASSET_ID = 4471;
    const FAILED_ASSET_ID = 4472;
    const BROKER_ID = 4473;
    const directory = {
        assets: [
            {asset_id: COMPLETE_ASSET_ID, display_name: 'Complete Asset'},
            {asset_id: FAILED_ASSET_ID, display_name: 'Failed Asset'},
        ],
        brokers: [{broker_id: BROKER_ID, display_name: 'Named Broker'}],
        fx_pairs: [],
    };
    // A target-currency amount, keys in the order the backend `Currency` serializes them.
    const eur = (amount: string) => ({code: 'EUR', amount});
    const FAILURE_CODE = 'FIFO_SOURCE_QUANTITY_MISSING';
    // The row of a FAILED asset: identity and codes, nothing else (the backend pins this exact key set).
    const FAILED_ROW = {asset_id: FAILED_ASSET_ID, asset_name: 'Failed Asset', asset_ticker: null, failure_codes: [FAILURE_CODE]};

    const COMPLETE_FIFO_LOT = {
        lot_ref: 'L1',
        asset_id: COMPLETE_ASSET_ID,
        asset_name: 'Complete Asset',
        asset_ticker: null,
        opening_broker_id: BROKER_ID,
        direction: 'LONG',
        status: 'OPEN',
        opening_date: '2025-02-03',
        closing_date: null,
        opening_unit_price: eur('100.00'),
        original_quantity: '10',
        open_quantity: '10',
        realized_quantity: '0',
        original_cost: eur('1000.00'),
        residual_cost_basis: eur('1000.00'),
        cumulative_proceeds: eur('0.00'),
        open_value: eur('1120.00'),
        realized_pnl: eur('0.00'),
        unrealized_pnl: eur('120.00'),
        total_pnl: eur('120.00'),
        net_total_pnl: eur('120.00'),
        income: eur('0.00'),
        fees: eur('0.00'),
        taxes: eur('0.00'),
        value_source: 'MARKET_PRICE',
        net_metrics_status: 'AVAILABLE',
        states: ['OPEN'],
        current_custody: [{broker_id: BROKER_ID, custody_type: 'BROKER', quantity: '10'}],
    };
    const COMPLETE_ASSET_ROW = {
        asset_id: COMPLETE_ASSET_ID,
        asset_name: 'Complete Asset',
        asset_ticker: null,
        open_lot_count: 1,
        partial_lot_count: 0,
        closed_lot_count: 0,
        has_open_position: true,
        original_quantity: '10',
        open_quantity: '10',
        realized_quantity: '0',
        original_cost: eur('1000.00'),
        residual_cost_basis: eur('1000.00'),
        cumulative_proceeds: eur('0.00'),
        realized_pnl: eur('0.00'),
        open_value: eur('1120.00'),
        unrealized_pnl: eur('120.00'),
        potential_gain: eur('120.00'),
        potential_loss: eur('0.00'),
        total_pnl: eur('120.00'),
        net_total_pnl: eur('120.00'),
        income: eur('0.00'),
        fees: eur('0.00'),
        taxes: eur('0.00'),
        valued_open_lot_count: 1,
        unavailable_open_lot_count: 0,
        value_coverage_status: 'complete',
        net_metrics_status: 'AVAILABLE',
        broker_ids: [BROKER_ID],
        custody_types: ['BROKER'],
        states: ['OPEN'],
        has_in_transit_custody: false,
    };
    const COMPLETE_LOT_DETAIL = {
        lot_ref: 'L1',
        opening_broker_id: BROKER_ID,
        opening_date: '2025-02-03',
        opening_unit_price: '100.00',
        original_quantity: '10',
        original_cost: '1000.00',
        open_quantity: '10',
        realized_quantity: '0',
        cumulative_proceeds: '0.00',
        realized_pnl: '0.00',
        open_value: '1120.00',
        unrealized_pnl: '120.00',
        total_pnl: '120.00',
        net_total_pnl: '120.00',
        income: '0.00',
        allocated_fees: '0.00',
        allocated_taxes: '0.00',
        value_source: 'MARKET_PRICE',
        net_metrics_status: 'AVAILABLE',
        states: ['OPEN'],
        closing_date: null,
        current_custody: [{broker_id: BROKER_ID, custody_type: 'BROKER', quantity: '10'}],
    };

    type FifoLotsId = 'portfolio.fifo_lots' | 'broker.fifo_lots';
    type FifoSummaryId = 'portfolio.fifo_summary' | 'broker.fifo_summary';

    function scopeFields(componentId: string) {
        return {period_start: '2025-02-01', period_end: '2025-02-14', ...(componentId.startsWith('broker.') ? {broker_id: BROKER_ID} : {})};
    }

    function fifoLotsSection(componentId: FifoLotsId, componentVersion: number) {
        return {
            component_id: componentId,
            component_version: componentVersion,
            schema_id: componentId,
            schema_version: 1,
            payload: {
                ...scopeFields(componentId),
                target_currency: 'EUR',
                cost_allocation_semantics: 'cost allocation semantics placeholder',
                lot_count: 1,
                unavailable_amount_lot_count: 0,
                failed_reconstruction_asset_count: 1,
                failed_lot_reconstructions: [FAILED_ROW],
                lots: [COMPLETE_FIFO_LOT],
            },
        };
    }

    function fifoSummarySection(componentId: FifoSummaryId, componentVersion: number) {
        return {
            component_id: componentId,
            component_version: componentVersion,
            schema_id: componentId,
            schema_version: 1,
            payload: {
                ...scopeFields(componentId),
                target_currency: 'EUR',
                cost_allocation_semantics: 'cost allocation semantics placeholder',
                asset_count: 1,
                // A failed asset's part is unknown: the scope totals are null, never a partial sum.
                total_open_lots: null,
                total_partial_lots: null,
                total_closed_lots: null,
                total_residual_cost_basis: null,
                failed_reconstruction_asset_count: 1,
                failed_lot_reconstructions: [FAILED_ROW],
                assets: [COMPLETE_ASSET_ROW],
            },
        };
    }

    function lotDetailSection(componentVersion: number, assetId: number, status: string, failureCodes: readonly string[], lots: readonly Record<string, unknown>[]) {
        return {
            component_id: 'asset.lot_detail',
            component_version: componentVersion,
            schema_id: 'asset.lot_detail',
            schema_version: 1,
            payload: {
                asset_id: assetId,
                period: {start: '2025-02-01', end: '2025-02-14'},
                target_currency: 'EUR',
                cost_allocation_semantics: 'cost allocation semantics placeholder',
                lot_reconstruction_status: status,
                failure_codes: failureCodes,
                lots,
                omitted_degraded_lot_count: 0,
                unavailable_amount_lot_count: 0,
            },
        };
    }

    function targetOf(componentId: string) {
        return componentId.startsWith('broker.') ? {kind: 'broker', broker_id: BROKER_ID} : {kind: 'portfolio'};
    }

    /** The pipe table on the lines right after `marker`: its header, and one header-keyed map per data row. */
    function pipeTableAfter(content: string, marker: string): {readonly header: readonly string[]; readonly rows: Map<string, string>[]} {
        const lines = content.split('\n');
        const start = lines.indexOf(marker);
        expect(start, `a "${marker}" line`).toBeGreaterThanOrEqual(0);
        const table: string[][] = [];
        for (const line of lines.slice(start + 1)) {
            if (!line.startsWith('|')) break;
            table.push(line.slice(1, -1).split(/(?<!\\)\|/));
        }
        const [header = [], ...rows] = table;
        return {header, rows: rows.map((cells) => new Map(header.map((column, index): [string, string] => [column, cells[index]])))};
    }

    /** The one row whose `column` reads `value`: rows are found by what they hold, never by position. */
    function rowWhere(rows: readonly Map<string, string>[], column: string, value: string): Map<string, string> {
        const matches = rows.filter((row) => row.get(column) === value);
        expect(matches, `rows whose ${column} is ${value}`).toHaveLength(1);
        return matches[0];
    }

    /** The value cell of the SUMMARY row for `field`, the row found by its field name. */
    function summaryValue(content: string, field: string): string | undefined {
        return rowWhere(pipeTableAfter(content, 'SUMMARY').rows, 'field', field).get('value');
    }

    /** An asset's prompt ref, resolved through the ENTITY DIRECTORY as a reader of the prompt would. */
    function assetRef(entityDirectory: string, displayName: string): string {
        const ref = rowWhere(pipeTableAfter(entityDirectory, 'ASSETS').rows, 'display_name', displayName).get('ref');
        if (ref === undefined) throw new Error(`the ENTITY DIRECTORY has no ref for ${displayName}`);
        return ref;
    }

    /** The rendered block of `componentId`: where a leaked database id would show. */
    function blockOf(rendered: ReturnType<typeof renderSnapshotDataText>, componentId: string): string {
        const block = rendered.blocks.find((candidate) => candidate.id === componentId);
        if (block === undefined) throw new Error(`no block for ${componentId}`);
        return block.content;
    }

    /** The failed asset's row: declared by its prompt ref with its codes, and nothing else — no id, no figure. */
    function expectFailedAssetDeclared(content: string, entityDirectory: string): void {
        expect(summaryValue(content, 'failed_reconstruction_asset_count')).toBe('1');
        const failedRef = assetRef(entityDirectory, 'Failed Asset');
        expect(failedRef).toMatch(/^A\d+$/);
        const {header, rows} = pipeTableAfter(content, 'TABLE failed_lot_reconstructions');
        expect(header).toEqual(['row', 'asset_ref', 'failure_codes']);
        expect(rows).toHaveLength(1);
        expect(rowWhere(rows, 'asset_ref', failedRef).get('failure_codes')).toContain(FAILURE_CODE);
    }

    it.each(['portfolio.fifo_lots', 'broker.fifo_lots'] as const)('renders %s v3 compactly: the failed asset declared by ref with its codes, and no lot row of it', (componentId) => {
        const rendered = renderSnapshotDataText([fifoLotsSection(componentId, 3)], targetOf(componentId), directory);
        const block = blockOf(rendered, componentId);

        expect(block).toContain(`COMPONENT ${componentId}`);
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expectFailedAssetDeclared(block, rendered.entityDirectory);
        // The lots exported are the complete asset's only; the counts stay counts of the exported rows.
        const lotRows = pipeTableAfter(block, 'TABLE lots').rows;
        expect(lotRows.map((row) => row.get('asset_ref'))).toEqual([assetRef(rendered.entityDirectory, 'Complete Asset')]);
        expect(summaryValue(block, 'lot_count')).toBe('1');
        expect(summaryValue(block, 'unavailable_amount_lot_count')).toBe('0');
        expect(block).not.toContain(String(FAILED_ASSET_ID));
    });

    it('renders asset.lot_detail v4 of a FAILED reconstruction compactly: its status and codes, no lot', () => {
        const section = lotDetailSection(4, FAILED_ASSET_ID, 'FAILED', [FAILURE_CODE], []);
        const rendered = renderSnapshotDataText([section], {kind: 'asset', asset_id: FAILED_ASSET_ID}, directory);
        const block = blockOf(rendered, 'asset.lot_detail');

        expect(block).toContain('COMPONENT asset.lot_detail');
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(summaryValue(block, 'lot_reconstruction_status')).toBe('FAILED');
        expect(pipeTableAfter(block, 'TABLE failure_codes').rows.map((row) => row.get('value'))).toEqual([FAILURE_CODE]);
        expect(block).not.toContain('TABLE lots');
        expect(summaryValue(block, 'omitted_degraded_lot_count')).toBe('0');
        expect(summaryValue(block, 'unavailable_amount_lot_count')).toBe('0');
        // The asset is its prompt ref, never its database id.
        expect(summaryValue(block, 'asset_ref')).toBe(assetRef(rendered.entityDirectory, 'Failed Asset'));
        expect(block).not.toContain(String(FAILED_ASSET_ID));
    });

    it('renders asset.lot_detail v4 of a COMPLETE reconstruction compactly: its status and its lots', () => {
        const section = lotDetailSection(4, COMPLETE_ASSET_ID, 'COMPLETE', [], [COMPLETE_LOT_DETAIL]);
        const rendered = renderSnapshotDataText([section], {kind: 'asset', asset_id: COMPLETE_ASSET_ID}, directory);
        const block = blockOf(rendered, 'asset.lot_detail');

        expect(block).toContain('COMPONENT asset.lot_detail');
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expect(summaryValue(block, 'lot_reconstruction_status')).toBe('COMPLETE');
        expect(pipeTableAfter(block, 'TABLE lots').rows.map((row) => row.get('lot_ref'))).toEqual(['L1']);
    });

    it.each(['portfolio.fifo_summary', 'broker.fifo_summary'] as const)('GUARD: renders %s v3 compactly with the failed asset declared and the scope totals null', (componentId) => {
        // Green today and after: the FIFO summaries are v3 already, and the generic renderer prints the new fields.
        const rendered = renderSnapshotDataText([fifoSummarySection(componentId, 3)], targetOf(componentId), directory);
        const block = blockOf(rendered, componentId);

        expect(block).toContain(`COMPONENT ${componentId}`);
        expect(block).not.toContain('PAYLOAD YAML FALLBACK');
        expectFailedAssetDeclared(block, rendered.entityDirectory);
        for (const total of ['total_open_lots', 'total_partial_lots', 'total_closed_lots', 'total_residual_cost_basis']) {
            expect(summaryValue(block, total), total).toBe('null');
        }
        const assetRows = pipeTableAfter(block, 'TABLE assets').rows;
        expect(assetRows.map((row) => row.get('asset_ref'))).toEqual([assetRef(rendered.entityDirectory, 'Complete Asset')]);
        expect(block).not.toContain(String(FAILED_ASSET_ID));
    });
});
