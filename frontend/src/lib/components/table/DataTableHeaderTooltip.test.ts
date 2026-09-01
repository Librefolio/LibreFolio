// @vitest-environment jsdom
/**
 * DataTable — header tooltip position (F10).
 *
 * Column-header tooltips must open UPWARD (`position="top"`; the Tooltip
 * auto-flips when there is no space above): a table header usually sits at the
 * top edge of its container, and a bottom-opening tooltip there covered the
 * first rows (beta feedback F10).
 *
 * The requested side is asserted, not the computed geometry: jsdom has no
 * layout engine, so Tooltip's own flip arithmetic cannot run here. The real
 * Tooltip is replaced by `$test/harness/TooltipProbe.svelte`, which publishes
 * the `position` prop it receives as `data-position`. This file is kept apart
 * from DataTable.test.ts because the mock is module-wide per spec file, and
 * the main suite exercises the real Tooltip.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/components/ui/feedback/Tooltip.svelte', async () => ({
    default: (await import('$test/harness/TooltipProbe.svelte')).default,
}));

import {render, setupI18n, waitFor} from '$test/component';
import DataTable from './DataTable.svelte';
import type {ColumnDef} from './types';

interface Row {
    id: string;
    name: string;
}

beforeAll(async () => {
    await setupI18n();
});

describe('DataTable — header tooltip opens upward (F10)', () => {
    it('wraps the sort button of a tooltip column in a top-positioned Tooltip', async () => {
        const columns: ColumnDef<Row>[] = [{id: 'name', header: 'Name', type: 'text', cell: (r) => r.name, getValue: (r) => r.name, headerTooltip: 'Sorts by name'}];
        render(DataTable, {
            data: [{id: 'r1', name: 'Alpha'}],
            columns: columns as ColumnDef<unknown>[],
            getRowId: ((r: Row) => r.id) as (row: unknown) => string,
            storageKey: 'f10-sort-tooltip',
        });

        await waitFor(() => expect(document.querySelector('tbody tr[data-row-id="r1"]')).not.toBeNull());

        const probes = [...document.querySelectorAll<HTMLElement>('thead [data-testid="tooltip-probe"]')];
        expect(probes.length).toBeGreaterThan(0);
        for (const probe of probes) {
            expect(probe.getAttribute('data-position')).toBe('top');
        }
        // The probe must wrap the column's sort control, not float loose.
        expect(probes.some((p) => p.querySelector('[data-testid="dt-sort-name"]') !== null)).toBe(true);
    });

    it('wraps the header info-link (tooltip + URL) in a top-positioned Tooltip', async () => {
        const columns: ColumnDef<Row>[] = [
            {
                id: 'name',
                header: 'Name',
                type: 'text',
                cell: (r) => r.name,
                getValue: (r) => r.name,
                headerTooltip: 'Docs for this column',
                headerTooltipUrl: 'https://example.com/docs',
            },
        ];
        render(DataTable, {
            data: [{id: 'r1', name: 'Alpha'}],
            columns: columns as ColumnDef<unknown>[],
            getRowId: ((r: Row) => r.id) as (row: unknown) => string,
            storageKey: 'f10-link-tooltip',
        });

        await waitFor(() => expect(document.querySelector('tbody tr[data-row-id="r1"]')).not.toBeNull());

        const link = document.querySelector<HTMLElement>('thead a.header-tooltip-link');
        expect(link, 'header tooltip link not rendered').not.toBeNull();
        const probe = link!.closest('[data-testid="tooltip-probe"]');
        expect(probe, 'header tooltip link is not inside a Tooltip').not.toBeNull();
        expect(probe!.getAttribute('data-position')).toBe('top');
    });

    it('a column without headerTooltip renders no header probe at all', async () => {
        const columns: ColumnDef<Row>[] = [{id: 'name', header: 'Name', type: 'text', cell: (r) => r.name, getValue: (r) => r.name}];
        render(DataTable, {
            data: [{id: 'r1', name: 'Alpha'}],
            columns: columns as ColumnDef<unknown>[],
            getRowId: ((r: Row) => r.id) as (row: unknown) => string,
            storageKey: 'f10-no-tooltip',
        });

        await waitFor(() => expect(document.querySelector('tbody tr[data-row-id="r1"]')).not.toBeNull());

        expect(document.querySelector('thead [data-testid="tooltip-probe"]')).toBeNull();
    });
});
