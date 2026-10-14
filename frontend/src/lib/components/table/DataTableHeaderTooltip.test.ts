// @vitest-environment jsdom
/**
 * DataTable — header tooltip position and documentation gestures.
 *
 * Header tooltips open upward. Documentation URLs remain ordinary anchors by
 * default, while a column may opt into the YOC guide gesture: click/tap pins
 * the tooltip, desktop double-click and a 500 ms mobile long press open the
 * guide, and the synthetic click emitted after a long press is consumed.
 *
 * The real Tooltip is used because visibility is part of the gesture contract.
 * The positioning case supplies deterministic rectangles: jsdom has no layout
 * engine, so its all-zero defaults would force Tooltip's viewport fallback.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import DataTable from './DataTable.svelte';
import type {ColumnDef} from './types';

interface Row {
    id: string;
    name: string;
}

const DOC_URL = 'https://example.com/yoc-guide';
const TOOLTIP_TEXT = 'Controlled YOC summary';
const storage = new Map<string, string>();
let fakeTimersActive = false;

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    storage.clear();
    vi.stubGlobal('localStorage', {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => void storage.set(key, value),
        removeItem: (key: string) => void storage.delete(key),
    });
});

afterEach(() => {
    cleanup();
    if (fakeTimersActive) {
        vi.clearAllTimers();
        vi.useRealTimers();
        fakeTimersActive = false;
    }
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

function column(linkMode?: 'direct' | 'gesture'): ColumnDef<Row> {
    return {
        id: 'name',
        header: 'Name',
        type: 'text',
        cell: (row) => row.name,
        getValue: (row) => row.name,
        headerTooltip: TOOLTIP_TEXT,
        headerTooltipUrl: DOC_URL,
        ...(linkMode ? {headerTooltipLinkMode: linkMode} : {}),
        filterable: false,
        resizable: false,
    };
}

async function mountTable(linkMode?: 'direct' | 'gesture') {
    render(DataTable, {
        data: [{id: 'r1', name: 'Alpha'}],
        columns: [column(linkMode)] as ColumnDef<unknown>[],
        getRowId: ((row: Row) => row.id) as (row: unknown) => string,
        storageKey: `header-tooltip-${linkMode ?? 'default'}`,
        enableSelection: false,
        enableActions: false,
        enableColumnFilters: false,
        enableColumnResize: false,
    });

    await waitFor(() => expect(document.querySelector('tbody tr[data-row-id="r1"]')).not.toBeNull());
}

function guideTrigger(): HTMLElement {
    return screen.getByTestId('dt-header-tooltip-name');
}

function rect(top: number, left: number, width: number, height: number): DOMRect {
    return {
        x: left,
        y: top,
        top,
        left,
        right: left + width,
        bottom: top + height,
        width,
        height,
        toJSON: () => ({}),
    } as DOMRect;
}

function openSpy() {
    return vi.spyOn(window, 'open').mockImplementation(() => null);
}

function useFakeTimers() {
    vi.useFakeTimers();
    fakeTimersActive = true;
}

describe('DataTable — header tooltips', () => {
    it('positions both the sortable label tooltip and the guide tooltip above their triggers', async () => {
        const frames = new Map<number, FrameRequestCallback>();
        let nextFrame = 0;
        vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
            const id = ++nextFrame;
            frames.set(id, callback);
            return id;
        });
        vi.stubGlobal('cancelAnimationFrame', (id: number) => {
            frames.delete(id);
        });

        const originalRect = HTMLElement.prototype.getBoundingClientRect;
        vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
            if (this.getAttribute('role') === 'tooltip') return rect(0, 0, 80, 20);
            if (this.querySelector('[data-testid="dt-sort-name"], [data-testid="dt-header-tooltip-name"]')) return rect(100, 100, 40, 20);
            return originalRect.call(this);
        });

        await mountTable('gesture');

        for (const testId of ['dt-sort-name', 'dt-header-tooltip-name']) {
            const trigger = screen.getByTestId(testId);
            await fireEvent.click(trigger);
            const tooltip = await screen.findByRole('tooltip');

            const pendingFrames = [...frames.values()];
            frames.clear();
            pendingFrames.forEach((callback) => callback(0));

            await waitFor(() => expect(tooltip).toHaveStyle({top: '72px'}));
            await waitFor(() => expect(tooltip).toHaveAttribute('data-dismissable', 'true'));
            await fireEvent.click(document.body);
            await waitFor(() => expect(screen.queryByRole('tooltip')).toBeNull());
        }
    });

    it('uses a normal click to show the opt-in tooltip without opening documentation', async () => {
        const open = openSpy();
        await mountTable('gesture');

        const trigger = guideTrigger();
        expect(trigger).toHaveAttribute('type', 'button');
        expect(trigger).toHaveAccessibleName(TOOLTIP_TEXT);
        expect(trigger).not.toHaveAttribute('href');
        expect(trigger).not.toHaveAttribute('title');
        expect(trigger).toHaveAttribute('aria-keyshortcuts', 'Shift+Enter');

        await fireEvent.click(trigger);

        expect(screen.getByRole('tooltip')).toHaveTextContent(TOOLTIP_TEXT);
        expect(open).not.toHaveBeenCalled();
    });

    it('keeps plain Enter as native tooltip activation without opening documentation', async () => {
        const open = openSpy();
        await mountTable('gesture');

        const trigger = guideTrigger();
        const keydown = new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true});
        await fireEvent(trigger, keydown);

        expect(keydown.defaultPrevented).toBe(false);
        expect(open).not.toHaveBeenCalled();

        // jsdom does not synthesize a button's native click after Enter.
        await fireEvent.click(trigger);

        expect(screen.getByRole('tooltip')).toHaveTextContent(TOOLTIP_TEXT);
        expect(open).not.toHaveBeenCalled();
    });

    it('opens documentation on Shift+Enter with the exact new-window contract', async () => {
        const open = openSpy();
        await mountTable('gesture');

        const keydown = new KeyboardEvent('keydown', {key: 'Enter', shiftKey: true, bubbles: true, cancelable: true});
        await fireEvent(guideTrigger(), keydown);

        expect(keydown.defaultPrevented).toBe(true);
        expect(open).toHaveBeenCalledTimes(1);
        expect(open).toHaveBeenCalledWith(DOC_URL, '_blank', 'noopener,noreferrer');
    });

    it('uses a normal tap to show the opt-in tooltip without opening documentation', async () => {
        const open = openSpy();
        await mountTable('gesture');
        useFakeTimers();

        const trigger = guideTrigger();
        await fireEvent.touchStart(trigger);
        await fireEvent.touchEnd(trigger);

        expect(screen.getByRole('tooltip')).toHaveTextContent(TOOLTIP_TEXT);
        expect(open).not.toHaveBeenCalled();
    });

    it('opens documentation on a desktop double-click', async () => {
        const open = openSpy();
        await mountTable('gesture');

        const event = new MouseEvent('dblclick', {bubbles: true, cancelable: true});
        await fireEvent(guideTrigger(), event);

        expect(event.defaultPrevented).toBe(true);
        expect(open).toHaveBeenCalledTimes(1);
        expect(open).toHaveBeenCalledWith(DOC_URL, '_blank', 'noopener,noreferrer');
    });

    it('opens documentation only after the 500 ms long-press threshold', async () => {
        const open = openSpy();
        await mountTable('gesture');
        useFakeTimers();

        const trigger = guideTrigger();
        await fireEvent.touchStart(trigger);
        await vi.advanceTimersByTimeAsync(499);
        expect(open).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(1);
        expect(open).toHaveBeenCalledTimes(1);
        expect(open).toHaveBeenCalledWith(DOC_URL, '_blank', 'noopener,noreferrer');
        await fireEvent.touchEnd(trigger);
    });

    it.each(['touchmove', 'touchend'] as const)('cancels a pending long press on %s', async (cancellation) => {
        const open = openSpy();
        await mountTable('gesture');
        useFakeTimers();

        const trigger = guideTrigger();
        await fireEvent.touchStart(trigger);
        await vi.advanceTimersByTimeAsync(250);
        if (cancellation === 'touchmove') await fireEvent.touchMove(trigger);
        else await fireEvent.touchEnd(trigger);
        await vi.advanceTimersByTimeAsync(500);

        expect(open).not.toHaveBeenCalled();
    });

    it('suppresses the synthetic click emitted after a completed long press', async () => {
        const open = openSpy();
        await mountTable('gesture');
        useFakeTimers();

        const trigger = guideTrigger();
        await fireEvent.touchStart(trigger);
        await vi.advanceTimersByTimeAsync(500);
        await fireEvent.touchEnd(trigger);

        const syntheticClick = new MouseEvent('click', {bubbles: true, cancelable: true});
        await fireEvent(trigger, syntheticClick);

        expect(syntheticClick.defaultPrevented).toBe(true);
        expect(open).toHaveBeenCalledTimes(1);
        expect(screen.getByRole('tooltip')).toHaveTextContent(TOOLTIP_TEXT);
    });

    it('keeps non-opt-in documentation triggers as direct links', async () => {
        await mountTable();

        const link = guideTrigger();
        expect(link.tagName).toBe('A');
        expect(link).toHaveAttribute('href', DOC_URL);
        expect(link).toHaveAttribute('target', '_blank');
        expect(link).toHaveAttribute('rel', 'noopener noreferrer');
        expect(link).not.toHaveAttribute('title');
    });

    it('renders no header tooltip trigger when the column has no tooltip', async () => {
        const columns: ColumnDef<Row>[] = [{id: 'name', header: 'Name', type: 'text', cell: (row) => row.name, getValue: (row) => row.name}];
        render(DataTable, {
            data: [{id: 'r1', name: 'Alpha'}],
            columns: columns as ColumnDef<unknown>[],
            getRowId: ((row: Row) => row.id) as (row: unknown) => string,
            storageKey: 'header-no-tooltip',
            enableSelection: false,
            enableActions: false,
        });

        await waitFor(() => expect(document.querySelector('tbody tr[data-row-id="r1"]')).not.toBeNull());

        expect(screen.queryByTestId('dt-header-tooltip-name')).toBeNull();
        expect(screen.queryByRole('tooltip')).toBeNull();
    });
});
