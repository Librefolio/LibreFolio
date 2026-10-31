// @vitest-environment jsdom
/**
 * TransactionsTable — a row action is offered only when the page gave it a handler (FB-17).
 * Component test (Vitest + jsdom).
 *
 * The table is presentational: each row action (View, Edit, Clone, Split, Delete) calls a handler the page passes
 * (`onViewRow`, `onEditRow`, `onCloneRow`, `onSplitRow`, `onDeleteRow`). The Transactions page passes all five. The
 * broker page's Transactions tab wires Edit, Clone, Delete and View, and does not wire Split: an action with no
 * handler would be a button that does nothing, so the table does not draw it. The rule, per action:
 *
 *   visible  =  the handler is passed  AND  the row's access level allows it (the unchanged `rowAccessLevel` rule:
 *               Edit, Split and Delete need full access, Clone needs the broker — or both brokers of a pair — to be
 *               editable, View is for every row).
 *
 * What is covered, each against its opposite so a green is never "nothing was drawn":
 *   - every handler passed (the Transactions page): View, Edit, Clone, Delete on a standalone row, and Split besides
 *     on a linked pair — the page does not change;
 *   - the broker tab's set (no `onSplitRow`): the pair row offers the other four and no Split; the standalone row
 *     is the same as above;
 *   - one handler missing at a time: exactly that action is gone, the others stay;
 *   - a row on a broker the user only views: just View, handlers or not (the access rule is untouched);
 *   - the handlers receive the row they were opened from.
 *
 * Selection. The rows by `tbody tr[data-row-id="tx-<id>"]`, the row's kebab by `row-actions-tx-<id>`, the menu a
 * right-click on the row opens by `context-menu`, and each action by `context-menu-action-<id>`: the handles the table and the menu publish.
 * Nothing here reads translated text.
 *
 * Brokers. The access rule reads the broker store, which this file fills with `mergeBrokers` (a role per broker) and
 * empties after each test: without a role the table treats a broker as unreadable and every action but View is off.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';

// The requests this graph makes are the reference catalogues; every other method is inert (the brokers carry an
// icon source, so BrokerIcon never asks the API).
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (property === 'list_currencies_api_v1_utilities_currencies_get') {
                    return vi.fn(async () => ({items: [{code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []}]}));
                }
                if (property === 'list_assets_api_v1_assets_query_get') return vi.fn(async () => []);
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {fireEvent, render, screen, setupI18n} from '$test/component';
import {ensureCurrenciesLoaded} from '$lib/stores/reference/currencyStore';
import {mergeBrokers, resetBrokerStore} from '$lib/stores/reference/brokerStore';
import TransactionsTable from './TransactionsTable.svelte';
import type {TXReadItem} from './types';

/** Editable broker (OWNER) and a broker the user can only read (VIEWER). */
const OWNED = {id: 41, name: 'FB-17 owned broker', portal_url: 'https://owned.example.com', icon_url: null, default_import_plugin: null, user_role: 'OWNER'};
const READ_ONLY = {id: 42, name: 'FB-17 read-only broker', portal_url: 'https://readonly.example.com', icon_url: null, default_import_plugin: null, user_role: 'VIEWER'};

const base = {asset_id: null, quantity: '0', asset_event_id: null, tags: [], description: null};

/** A standalone deposit on the editable broker. */
const DEPOSIT: TXReadItem = {...base, id: 8201, broker_id: OWNED.id, type: 'DEPOSIT', date: '2026-03-10', cash: {code: 'EUR', amount: '25.00'}, related_transaction_id: null};
/** A linked FX conversion, both halves on the editable broker: the pair that can be split. */
const FX_GIVER: TXReadItem = {...base, id: 8202, broker_id: OWNED.id, type: 'FX_CONVERSION', date: '2026-03-12', cash: {code: 'EUR', amount: '-100.00'}, related_transaction_id: 8203};
const FX_RECEIVER: TXReadItem = {...base, id: 8203, broker_id: OWNED.id, type: 'FX_CONVERSION', date: '2026-03-12', cash: {code: 'EUR', amount: '109.00'}, related_transaction_id: 8202};
/** A standalone deposit on the read-only broker. */
const READ_ONLY_DEPOSIT: TXReadItem = {...base, id: 8204, broker_id: READ_ONLY.id, type: 'DEPOSIT', date: '2026-03-11', cash: {code: 'EUR', amount: '5.00'}, related_transaction_id: null};

type Handlers = {onViewRow: (row: TXReadItem) => void; onEditRow: (row: TXReadItem) => void; onCloneRow: (row: TXReadItem) => void; onSplitRow: (row: TXReadItem) => void; onDeleteRow: (row: TXReadItem) => void};
type HandlerName = keyof Handlers;

const ACTION_OF: Record<HandlerName, string> = {onViewRow: 'view', onEditRow: 'edit', onCloneRow: 'clone', onSplitRow: 'split', onDeleteRow: 'delete'};

function spies(): {[K in HandlerName]: Mock<Handlers[K]>} {
    return {onViewRow: vi.fn(), onEditRow: vi.fn(), onCloneRow: vi.fn(), onSplitRow: vi.fn(), onDeleteRow: vi.fn()};
}

/** Mount the table on `rows` with only the `passed` handlers. */
function mount(rows: TXReadItem[], passed: Partial<Handlers>): void {
    render(TransactionsTable, {
        mainRows: rows.map((r) => structuredClone(r)),
        partnerRows: [],
        brokers: [{...OWNED}, {...READ_ONLY}],
        eventTooltipMap: new Map(),
        ...passed,
    });
}

/** Barrier: the row is rendered. */
async function rowReady(txId: number): Promise<void> {
    await screen.findByTestId(`row-actions-tx-${txId}`);
    expect(document.querySelector(`tbody tr[data-row-id="tx-${txId}"]`), `row tx-${txId} is rendered`).not.toBeNull();
}

/**
 * Open a row's actions menu and return the ids of the actions it offers. By right-click, the path jsdom can measure
 * (DataTable's own tests do the same): the kebab button opens the very same menu, from the same visible actions.
 */
async function actionsOf(txId: number): Promise<string[]> {
    await rowReady(txId);
    const tr = document.querySelector<HTMLElement>(`tbody tr[data-row-id="tx-${txId}"]`);
    if (!tr) throw new Error(`row tx-${txId} not rendered`);
    await fireEvent.contextMenu(tr);
    const menu = await screen.findByTestId('context-menu');
    return Array.from(menu.querySelectorAll<HTMLElement>('[data-testid^="context-menu-action-"]')).map((el) => (el.getAttribute('data-testid') ?? '').replace('context-menu-action-', ''));
}

beforeAll(async () => {
    await setupI18n();
    await ensureCurrenciesLoaded('en');
});

beforeEach(() => {
    mergeBrokers([OWNED, READ_ONLY]);
});

afterEach(() => {
    resetBrokerStore();
});

describe('TransactionsTable — every handler passed (the Transactions page): nothing changes', () => {
    it('a standalone row offers View, Edit, Clone and Delete, and no Split (it has no pair to split)', async () => {
        mount([DEPOSIT, FX_GIVER, FX_RECEIVER], spies());

        const actions = await actionsOf(DEPOSIT.id);

        expect(actions).toEqual(expect.arrayContaining(['view', 'edit', 'clone', 'delete']));
        expect(actions).not.toContain('split');
    });

    it('a linked pair row offers View, Edit, Clone, Split and Delete', async () => {
        mount([DEPOSIT, FX_GIVER, FX_RECEIVER], spies());

        const actions = await actionsOf(FX_GIVER.id);

        expect(actions).toEqual(expect.arrayContaining(['view', 'edit', 'clone', 'split', 'delete']));
    });
});

describe('TransactionsTable — the broker tab wires no Split', () => {
    const {onSplitRow: _omitted, ...withoutSplit} = spies();

    it('a linked pair row offers View, Edit, Clone and Delete and no Split', async () => {
        mount([DEPOSIT, FX_GIVER, FX_RECEIVER], withoutSplit);

        const actions = await actionsOf(FX_GIVER.id);

        // Presence first: the menu is the pair row's own and it is not empty, so the absence below means something.
        expect(actions).toEqual(expect.arrayContaining(['view', 'edit', 'clone', 'delete']));
        expect(actions).not.toContain('split');
    });

    it('with Split passed on the same pair the action is there: the rule is the handler, not the row', async () => {
        mount([DEPOSIT, FX_GIVER, FX_RECEIVER], {...withoutSplit, onSplitRow: vi.fn()});

        expect(await actionsOf(FX_GIVER.id)).toContain('split');
    });

    it('a standalone row offers the same four as on the Transactions page', async () => {
        mount([DEPOSIT, FX_GIVER, FX_RECEIVER], withoutSplit);

        const actions = await actionsOf(DEPOSIT.id);

        expect(actions).toEqual(expect.arrayContaining(['view', 'edit', 'clone', 'delete']));
        expect(actions).not.toContain('split');
    });
});

describe('TransactionsTable — an action without its handler is not drawn', () => {
    const names: HandlerName[] = ['onViewRow', 'onEditRow', 'onCloneRow', 'onDeleteRow', 'onSplitRow'];

    it.each(names)('without %s only that action is gone from a linked pair row', async (missing) => {
        const all = spies();
        const passed: Partial<Handlers> = {...all};
        delete passed[missing];
        mount([DEPOSIT, FX_GIVER, FX_RECEIVER], passed);

        const actions = await actionsOf(FX_GIVER.id);

        const expected = names.filter((n) => n !== missing).map((n) => ACTION_OF[n]);
        // Each of the others is there (presence), the missing one is not (absence).
        expect(actions).toEqual(expect.arrayContaining(expected));
        expect(actions).not.toContain(ACTION_OF[missing]);
    });

    it('with no handler at all the row offers nothing: no menu button on the row', async () => {
        mount([DEPOSIT], {});

        // The row is rendered (its selection checkbox is there); with no action to offer the table draws no kebab.
        await screen.findByTestId(`dt-row-checkbox-tx-${DEPOSIT.id}`);
        expect(screen.queryByTestId(`row-actions-tx-${DEPOSIT.id}`)).toBeNull();
    });
});

describe('TransactionsTable — the access rule is unchanged', () => {
    it('a row on a broker the user only reads offers just View, whatever handlers are passed', async () => {
        mount([DEPOSIT, READ_ONLY_DEPOSIT], spies());

        const actions = await actionsOf(READ_ONLY_DEPOSIT.id);

        expect(actions).toEqual(['view']);
    });
});

describe('TransactionsTable — the handlers receive the row they were opened from', () => {
    it.each([
        ['edit', 'onEditRow'],
        ['clone', 'onCloneRow'],
        ['delete', 'onDeleteRow'],
    ] as const)('%s calls %s once with that row', async (action, handler) => {
        const all = spies();
        mount([DEPOSIT, FX_GIVER, FX_RECEIVER], all);
        await actionsOf(DEPOSIT.id);

        await fireEvent.click(await screen.findByTestId(`context-menu-action-${action}`));

        expect(all[handler]).toHaveBeenCalledTimes(1);
        expect(all[handler].mock.calls[0][0]).toMatchObject({id: DEPOSIT.id});
        for (const other of Object.keys(all) as HandlerName[]) if (other !== handler) expect(all[other]).not.toHaveBeenCalled();
    });
});
