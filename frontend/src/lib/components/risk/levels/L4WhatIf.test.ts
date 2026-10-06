// @vitest-environment jsdom
/**
 * L4WhatIf — component test (Vitest + jsdom), checkpoint k5b (D377): the tool selector.
 *
 * L4 holds three tools at increasing distance from observed data — the replay (observed), the
 * shock (assumed), the simulation (modelled) — always in that order. Until k5b every tool a page
 * supplied was drawn at once. D377 lets the reader choose which ones are open:
 *
 *   1. **Several tools supplied** (the Dashboard supplies all three). The open set is remembered
 *      per user in this browser, under `lf_{userId}_risk.l4.openTools` (`getUserStorage` /
 *      `setUserStorage`), as a JSON array of tool ids in the fixed order.
 *        - **First visit** (nothing remembered): no box at all, the hint `risk-l4-empty`, and one
 *          add button per supplied tool — `risk-l4-add-{tool}`, in the fixed order.
 *        - **Adding** a tool opens its box. The boxes keep the fixed order whatever the order of
 *          adding; an open tool's add button goes, and with every tool open none is left. Each add
 *          remembers the new set. Adding resets nothing.
 *        - **The hint** says that no tool is open, so it shows only then: one open tool — added or
 *          remembered — is enough to drop it, while the closed tools are still offered.
 *        - **Closing**: each open box has `risk-l4-{tool}-close`, named by
 *          `risk.levels.l4.tools.close` with the tool's title. Closing removes the box, remembers
 *          the set, and asks the controller to forget that tool's answer — exactly once, and only
 *          that one: replay → `'replay'`, shock → `'stress'`, simulation → `'simulation'`.
 *        - **A remembered set** opens exactly those tools, in the fixed order; ids that are
 *          unknown or not supplied are ignored, and a value that is not a JSON list of ids reads
 *          as a first visit. Mounting alone never writes.
 *   2. **One tool supplied** (Asset Global mounts the replay alone, with no controller): the box at
 *      once, with no add button, no close button and no hint, and storage is neither read nor
 *      written — what the Dashboard remembers is not this page's business.
 *
 * Unchanged, and pinned again because the boxes are now opened and closed: the box testids and
 * their `data-distance` (`observed`, `assumed`, `modelled`), and the simulation box's beta banner
 * (`scope="simulation"`) and model warning, inside it and nowhere else.
 *
 * **The snippets** are raw snippets (`createRawSnippet`), each a `probe-{tool}` element, so what
 * a box holds is visible without mounting the real rungs; a closed tool's snippet must not be on
 * screen at all. **The controller** is a fake with one `vi.fn()`: `resetAnalysis` is the whole of
 * what the selector may ask of it.
 *
 * **Storage.** On Node 26 the global `localStorage` is unavailable without `--localstorage-file`,
 * and `getUserStorage` then falls back to its default in silence — every "nothing remembered"
 * case would pass for the wrong reason. So the file owns a Map-backed stand-in that logs every
 * call, emptied before each case (the `AllocationPanel.test.ts` pattern), and the harness proves
 * the product's own helpers reach it. **The user** is a store this file controls: the
 * `currentUser` export of `$lib/stores/app/auth` is replaced, the rest of the module is real.
 *
 * **Handles.** `data-testid`, `data-distance`, `data-scope`, the order of elements in the document
 * — which is the contract here, the fixed order of the tools — and the close buttons' accessible
 * names, resolved from the shipped catalogue through the same `$_`. The harness case says the new
 * keys exist, so a key echoed back on both sides cannot pass for a name. No class, no prose.
 *
 * **Guards and reds.** The one-tool cases are green before k5b and must stay green; every
 * several-tools case is red until the selector lands.
 *
 * Left elsewhere: the rungs themselves (`l4/L4Replay.test.ts`), Asset Global's mount
 * (`AssetSetReplaySection.test.ts`), and the Dashboard end to end (`portfolio/risk-analysis.spec.ts`).
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {createRawSnippet, type Component, type Snippet} from 'svelte';
import {get, type Writable} from 'svelte/store';

// The signed-in user, which scopes the remembered set: a store this file sets per case. The rest
// of the auth module stays real, so whatever else imports it gets what it always got.
vi.mock('$lib/stores/app/auth', async (importOriginal) => {
    const {writable} = await import('svelte/store');
    return {...(await importOriginal<typeof import('$lib/stores/app/auth')>()), currentUser: writable<{id: number} | null>(null)};
});

/** The stand-in's contents, and every call made to it — `get`, `set` or `remove`, with the key. */
const storage = new Map<string, string>();
const storageLog: string[] = [];
vi.stubGlobal('localStorage', {
    getItem: (key: string) => {
        storageLog.push(`get ${key}`);
        return storage.get(key) ?? null;
    },
    setItem: (key: string, value: string) => {
        storageLog.push(`set ${key}`);
        storage.set(key, String(value));
    },
    removeItem: (key: string) => {
        storageLog.push(`remove ${key}`);
        storage.delete(key);
    },
    clear: () => {
        storageLog.push('clear');
        storage.clear();
    },
});

import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import {_, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import {currentUser} from '$lib/stores/app/auth';
import type {OnDemandAnalysis} from '$lib/stores/risk/riskPanelController.svelte';
import {getUserStorage, getUserStorageKey, setUserStorage} from '$lib/utils/storage';
import L4WhatIf from './L4WhatIf.svelte';

type Tool = 'replay' | 'shock' | 'simulation';

/** The tools, in their fixed order: observed, assumed, modelled. */
const TOOLS: readonly Tool[] = ['replay', 'shock', 'simulation'];

/** The analysis each tool's answer lives under in the controller. */
const ANALYSIS: Readonly<Record<Tool, OnDemandAnalysis>> = {replay: 'replay', shock: 'stress', simulation: 'simulation'};

const DISTANCE: Readonly<Record<Tool, string>> = {replay: 'observed', shock: 'assumed', simulation: 'modelled'};

/** Each tool's title, as its box is headed. */
const TITLE_KEYS: Readonly<Record<Tool, string>> = {replay: 'risk.levels.l4.replay', shock: 'risk.levels.l4.shock', simulation: 'risk.levels.l4.simulation'};

/** The selector's own sentences (k5b). */
const SELECTOR_KEYS = {empty: 'risk.levels.l4.tools.empty', add: 'risk.levels.l4.tools.add', close: 'risk.levels.l4.tools.close'} as const;

const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

/** Whose L4 is on screen, and another user of the same browser. */
const USER = 42;
const OTHER_USER = 7;

/** The base key the open set is remembered under; the product scopes it with the user. */
const OPEN_TOOLS = 'risk.l4.openTools';

/** What the selector may ask of the controller, and nothing more. */
interface ToolController {
    resetAnalysis: (analysis: OnDemandAnalysis) => void;
}

/**
 * The props this spec mounts with — declared here, so it compiles on either side of the arrival
 * of `controller`, whatever the type the product gives it.
 */
interface WhatIfProps {
    replay?: Snippet;
    shock?: Snippet;
    simulation?: Snippet;
    controller?: ToolController;
}

const WhatIf = L4WhatIf as unknown as Component<WhatIfProps>;

const signedIn = currentUser as unknown as Writable<{id: number} | null>;

const BOX = (tool: Tool) => `risk-l4-${tool}`;
const ADD = (tool: Tool) => `risk-l4-add-${tool}`;
const CLOSE = (tool: Tool) => `risk-l4-${tool}-close`;
const PROBE = (tool: Tool) => `probe-${tool}`;
const EMPTY = 'risk-l4-empty';

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** A catalogue sentence as the component words it: `$_`, with the same values. Never a literal. */
function t(key: string, values?: Record<string, string>): string {
    return normalize(get(_)(key, values === undefined ? undefined : {values}));
}

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** The simple `{name}` arguments of an ICU message — whatever the product calls the tool's title in it. */
function placeholders(message: unknown): string[] {
    return typeof message === 'string' ? [...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*\}/g)].map((match) => match[1]) : [];
}

/** The close button's name: the close sentence, with the tool's title in each of its arguments. */
function closeLabel(tool: Tool): string {
    const title = t(TITLE_KEYS[tool]);
    return t(SELECTOR_KEYS.close, Object.fromEntries(placeholders(at(en, SELECTOR_KEYS.close)).map((name) => [name, title])));
}

/** The key the open set lives under for a user, as the contract writes it. */
function keyFor(userId: number): string {
    return `lf_${userId}_${OPEN_TOOLS}`;
}

/** Put a value where the selector reads the open set, as a previous visit would have left it. Not logged. */
function remember(value: string, userId = USER): void {
    storage.set(keyFor(userId), value);
}

/** The open set remembered for a user, parsed; `undefined` when nothing is. */
function remembered(userId = USER): unknown {
    const raw = storage.get(keyFor(userId));
    return raw === undefined ? undefined : JSON.parse(raw);
}

/** The calls that changed storage, from the log. */
function writes(): string[] {
    return storageLog.filter((entry) => !entry.startsWith('get '));
}

/** A rung's stand-in: a raw snippet whose element says which tool it is. */
function probe(tool: Tool): Snippet {
    return createRawSnippet(() => ({render: () => `<div data-testid="${PROBE(tool)}">${tool} probe</div>`}));
}

function fakeController() {
    return {resetAnalysis: vi.fn<(analysis: OnDemandAnalysis) => void>()};
}

/** L4 with the given tools supplied, in the props, and the controller if any. */
function mount(tools: readonly Tool[], controller?: ToolController) {
    const props: WhatIfProps = {controller};
    for (const tool of tools) props[tool] = probe(tool);
    return render(WhatIf, {props});
}

/** The tools whose element under `testId` is on screen, in document order — the order the reader meets them. */
function inDocumentOrder(testId: (tool: Tool) => string): Tool[] {
    return TOOLS.flatMap((tool) => screen.queryAllByTestId(testId(tool)).map((node) => ({tool, node})))
        .sort((left, right) => (left.node === right.node ? 0 : left.node.compareDocumentPosition(right.node) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1))
        .map(({tool}) => tool);
}

/** The open boxes, and the add buttons, as the reader meets them. */
function selectorState(): {open: Tool[]; add: Tool[]} {
    return {open: inDocumentOrder(BOX), add: inDocumentOrder(ADD)};
}

async function add(tool: Tool): Promise<void> {
    const button = screen.queryByTestId(ADD(tool));
    if (!button) throw new Error(`there is no ${ADD(tool)} button to open the ${tool} with (D377); the add buttons on screen are ${JSON.stringify(inDocumentOrder(ADD))}`);
    await fireEvent.click(button);
}

async function close(tool: Tool): Promise<void> {
    const button = screen.queryByTestId(CLOSE(tool));
    if (!button) throw new Error(`there is no ${CLOSE(tool)} button to close the ${tool} with (D377); the close buttons on screen are ${JSON.stringify(inDocumentOrder(CLOSE))}`);
    await fireEvent.click(button);
}

/** Each open box: its distance, its own snippet inside, and the beta notices only in the simulation's. */
function expectBoxes(open: readonly Tool[]): void {
    for (const tool of open) {
        const box = screen.getByTestId(BOX(tool));
        expect(box, `the ${tool} box lost its distance from observed data`).toHaveAttribute('data-distance', DISTANCE[tool]);
        expect(within(box).queryByTestId(PROBE(tool)), `the ${tool} box does not hold the ${tool} snippet`).not.toBeNull();
        if (tool === 'simulation') {
            expect(within(box).getByTestId('risk-beta-banner'), 'the simulation box lost its beta banner, or the banner its scope').toHaveAttribute('data-scope', 'simulation');
            expect(within(box).queryByTestId('risk-l4-model-warning'), 'the simulation box lost its model warning').not.toBeNull();
        } else {
            expect(within(box).queryByTestId('risk-beta-banner'), `the ${tool} box carries the simulation's beta banner`).toBeNull();
            expect(within(box).queryByTestId('risk-l4-model-warning'), `the ${tool} box carries the simulation's model warning`).toBeNull();
        }
    }
    const closed = TOOLS.filter((tool) => !open.includes(tool));
    expect(
        closed.filter((tool) => screen.queryAllByTestId(PROBE(tool)).length > 0),
        'a closed tool’s snippet is on screen: a closed tool is not mounted at all, not merely hidden',
    ).toEqual([]);
    if (!open.includes('simulation')) {
        expect(screen.queryAllByTestId('risk-beta-banner'), 'the beta banner is on screen with the simulation closed: it belongs to the simulation box').toEqual([]);
        expect(screen.queryAllByTestId('risk-l4-model-warning'), 'the model warning is on screen with the simulation closed').toEqual([]);
    }
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    storage.clear();
    storageLog.length = 0;
    signedIn.set({id: USER});
});

describe('L4WhatIf — the harness itself', () => {
    it('reaches the storage stand-in and the signed-in user through the product’s own helpers', () => {
        // Every "nothing remembered" and "nothing written" below stands on this: were the helpers
        // to miss the stand-in, the selector would read its default and write nowhere, in silence.
        expect(getUserStorageKey(OPEN_TOOLS), 'the open set’s key is not scoped with the signed-in user').toBe(keyFor(USER));
        setUserStorage('probe.key', 'probe value');
        expect(storage.get(`lf_${USER}_probe.key`), 'setUserStorage does not reach the stand-in').toBe('probe value');
        expect(getUserStorage('probe.key', ''), 'getUserStorage does not read the stand-in').toBe('probe value');
        expect(storageLog, 'the stand-in does not log the calls the cases below count').toEqual([`set lf_${USER}_probe.key`, `get lf_${USER}_probe.key`]);
    });

    it('has the selector’s three sentences in every catalogue, the close one naming the tool it closes', () => {
        // One line per key and locale, so a red names every sentence that is missing.
        const missing = SUPPORTED_LOCALES.flatMap((code) =>
            Object.values(SELECTOR_KEYS)
                .filter((key) => typeof at(CATALOGUES[code], key) !== 'string')
                .map((key) => `${code}: ${key}`),
        );
        expect(missing, 'the selector’s sentences are missing from these catalogues (k5b adds risk.levels.l4.tools.*)').toEqual([]);
        // svelte-i18n echoes the id back on a miss, and so would the component.
        for (const key of Object.values(SELECTOR_KEYS)) expect(t(key), `${key} does not resolve: the catalogue is not loaded`).not.toBe(key);

        // The premise of three distinct close buttons: three distinct titles.
        const titles = TOOLS.map((tool) => t(TITLE_KEYS[tool]));
        expect(new Set(titles).size, 'premise: two tools share a title').toBe(TOOLS.length);
        // The close sentence takes the title: each close button then says which tool it closes.
        expect(placeholders(at(en, SELECTOR_KEYS.close)), `${SELECTOR_KEYS.close} has no argument to put the tool’s title in: three close buttons would read alike`).not.toEqual([]);
        for (const tool of TOOLS) expect(closeLabel(tool), `the close sentence does not name the ${tool} by its title`).toContain(t(TITLE_KEYS[tool]));
        expect(new Set(TOOLS.map(closeLabel)).size, 'two close buttons read alike').toBe(TOOLS.length);
    });
});

describe('L4WhatIf — one tool supplied: the tool, and no selector', () => {
    it.each(TOOLS)('%s alone: its box at once, its snippet in it, and no add button, no close button, no hint (guard)', (tool) => {
        mount([tool]);

        expect(selectorState(), `with the ${tool} alone there is nothing to choose: its box is open from the start, and nothing is offered`).toEqual({open: [tool], add: []});
        expectBoxes([tool]);
        expect(inDocumentOrder(CLOSE), 'a tool supplied alone can be closed: the page would be left with no tool and no way back').toEqual([]);
        expect(screen.queryByTestId(EMPTY), 'the hint of an empty L4 is shown beside an open tool').toBeNull();
    });

    it('the replay alone — Asset Global — neither reads nor writes storage, whatever the Dashboard remembers (guard)', () => {
        // What the Dashboard remembers is not this page's business: an empty set, or one without
        // the replay, must not close Asset Global's only tool — and is not even read.
        for (const value of ['[]', '["shock"]', '["simulation"]']) {
            remember(value);
            storageLog.length = 0;
            const view = mount(['replay']);

            expect(selectorState(), `with ${value} remembered, the replay supplied alone is not open at once`).toEqual({open: ['replay'], add: []});
            expect(storageLog, `with ${value} remembered, the replay supplied alone touched storage: there is no selector to remember anything for`).toEqual([]);
            view.unmount();
        }
    });
});

describe('L4WhatIf — several tools: the first visit (D377)', () => {
    it('opens no box, says so, and offers one add button per tool, in the fixed order — writing nothing, resetting nothing', () => {
        const controller = fakeController();
        mount(TOOLS, controller);

        expect(selectorState(), 'a first visit must open no tool and offer each, in the fixed order: replay, shock, simulation').toEqual({open: [], add: TOOLS});
        expect(screen.queryByTestId(EMPTY), 'an L4 with no tool open does not say so').not.toBeNull();
        expectBoxes([]);
        expect(writes(), 'mounting wrote to storage: only the reader’s gestures change the open set').toEqual([]);
        expect(controller.resetAnalysis, 'mounting reset an analysis').not.toHaveBeenCalled();
    });

    it('offers only the tools supplied', () => {
        mount(['replay', 'simulation'], fakeController());

        expect(selectorState(), 'a page that supplies two tools offers those two, in the fixed order, and no other').toEqual({open: [], add: ['replay', 'simulation']});
        expect(screen.queryByTestId(EMPTY), 'an L4 with no tool open does not say so').not.toBeNull();
    });
});

describe('L4WhatIf — the hint that no tool is open', () => {
    it('shows only while no tool is open: one open tool — added from a first visit, or remembered — drops it, with the others still offered', async () => {
        // The positive control: on a first visit the hint is there, beside the three add buttons, so
        // each absence below is about an open tool and not about a hint that never renders.
        const firstVisit = mount(TOOLS, fakeController());
        expect(selectorState(), 'premise: a first visit opens no tool and offers each').toEqual({open: [], add: TOOLS});
        expect(screen.queryByTestId(EMPTY), 'premise: a first visit says that no tool is open').not.toBeNull();

        // One tool added from that first visit. With every tool open the hint goes with the add
        // buttons, so only this state — a tool open, others still offered — tells a hint bound to
        // "no tool is open" from one bound to "something is left to add".
        await add('shock');
        expect(selectorState(), 'barrier: the shock is open and the two others are still offered').toEqual({open: ['shock'], add: ['replay', 'simulation']});
        expect(screen.queryByTestId(EMPTY), 'the hint that no tool is open stayed on screen once the shock was added').toBeNull();
        firstVisit.unmount();

        // One tool remembered: the same state, from the mount on.
        remember('["replay"]');
        mount(TOOLS, fakeController());
        expect(selectorState(), 'barrier: the remembered replay is open and the two others are still offered').toEqual({open: ['replay'], add: ['shock', 'simulation']});
        expect(screen.queryByTestId(EMPTY), 'the hint that no tool is open is on screen beside the remembered replay').toBeNull();
    });
});

describe('L4WhatIf — adding a tool', () => {
    it('opens its box, in the fixed order whatever the order of adding, and its add button goes', async () => {
        mount(TOOLS, fakeController());

        await add('shock');
        expect(selectorState(), 'adding the shock does not open its box, or keeps offering it').toEqual({open: ['shock'], add: ['replay', 'simulation']});
        await add('replay');
        expect(selectorState(), 'the replay added after the shock is not drawn first: the boxes keep the fixed order, not the order of adding').toEqual({open: ['replay', 'shock'], add: ['simulation']});
        expectBoxes(['replay', 'shock']);
    });

    it('remembers the open set after each add, as a JSON list in the fixed order, and resets no analysis', async () => {
        const controller = fakeController();
        mount(TOOLS, controller);

        await add('shock');
        expect(remembered(), `adding the shock did not remember ["shock"] under ${keyFor(USER)}`).toEqual(['shock']);
        await add('replay');
        expect(remembered(), 'the open set is not remembered in the fixed order').toEqual(['replay', 'shock']);
        expect(controller.resetAnalysis, 'adding a tool reset an analysis: opening a tool is not a change of question').not.toHaveBeenCalled();
    });

    it('with every tool open, offers nothing more and drops the hint — the three boxes as they always were', async () => {
        const controller = fakeController();
        mount(TOOLS, controller);

        for (const tool of ['simulation', 'replay', 'shock'] as const) await add(tool);

        expect(selectorState(), 'with every tool open, the boxes are not in the fixed order, or an add button is left').toEqual({open: TOOLS, add: []});
        expect(screen.queryByTestId(EMPTY), 'the hint of an empty L4 is shown with every tool open').toBeNull();
        expectBoxes(TOOLS);
        expect(remembered(), 'the full set is not remembered in the fixed order').toEqual(TOOLS);
        expect(controller.resetAnalysis, 'adding a tool reset an analysis').not.toHaveBeenCalled();
    });
});

describe('L4WhatIf — closing a tool', () => {
    it.each(TOOLS)('closing the %s: its box goes, its add button comes back, the set is remembered without it, and its answer alone is forgotten', async (tool) => {
        remember(JSON.stringify(TOOLS));
        const controller = fakeController();
        mount(TOOLS, controller);
        expect(selectorState(), 'barrier: the remembered set opens every tool').toEqual({open: TOOLS, add: []});

        await close(tool);

        const rest = TOOLS.filter((other) => other !== tool);
        expect(selectorState(), `closing the ${tool} does not remove its box, or does not offer it again`).toEqual({open: rest, add: [tool]});
        expectBoxes(rest);
        expect(remembered(), `closing the ${tool} is not remembered`).toEqual(rest);
        expect(controller.resetAnalysis.mock.calls, `closing the ${tool} must forget its own answer (${ANALYSIS[tool]}) once, and no other tool's`).toEqual([[ANALYSIS[tool]]]);
    });

    it('puts each close button in its own box, named by the close sentence with the tool’s title', () => {
        remember(JSON.stringify(TOOLS));
        mount(TOOLS, fakeController());
        expect(selectorState(), 'barrier: the remembered set opens every tool').toEqual({open: TOOLS, add: []});

        for (const tool of TOOLS) {
            const button = screen.queryByTestId(CLOSE(tool));
            if (!button) throw new Error(`the ${tool} box has no ${CLOSE(tool)} button (D377)`);
            expect(screen.getByTestId(BOX(tool)).contains(button), `the ${tool} close button is not in the ${tool} box`).toBe(true);
            expect(button.tagName, `the ${tool} close control is not a button`).toBe('BUTTON');
            expect(button, `the ${tool} close button is not named by ${SELECTOR_KEYS.close} with the tool’s title`).toHaveAccessibleName(closeLabel(tool));
        }
    });

    it('closing the last open tool comes back to the empty L4: the hint, and every add button', async () => {
        remember('["shock"]');
        const controller = fakeController();
        mount(TOOLS, controller);
        expect(selectorState(), 'barrier: the remembered set opens the shock alone').toEqual({open: ['shock'], add: ['replay', 'simulation']});

        await close('shock');

        expect(selectorState(), 'with the last tool closed, L4 does not offer every tool again').toEqual({open: [], add: TOOLS});
        expect(screen.queryByTestId(EMPTY), 'an L4 with no tool open does not say so').not.toBeNull();
        expect(remembered(), 'closing the last tool is not remembered as an empty set').toEqual([]);
        expect(controller.resetAnalysis.mock.calls, 'closing the shock must forget the stress answer, once').toEqual([['stress']]);
    });
});

describe('L4WhatIf — the remembered set', () => {
    it('opens exactly the tools remembered, in the fixed order whatever the order stored, and writes nothing on mount', () => {
        remember('["simulation","replay"]');
        const controller = fakeController();
        mount(TOOLS, controller);

        expect(selectorState(), 'the remembered set is not what opened, or not in the fixed order').toEqual({open: ['replay', 'simulation'], add: ['shock']});
        expectBoxes(['replay', 'simulation']);
        expect(writes(), 'mounting wrote to storage').toEqual([]);
        expect(controller.resetAnalysis, 'mounting reset an analysis').not.toHaveBeenCalled();
    });

    it.each([
        {why: 'an id it does not know', stored: '["bogus","shock"]', supplied: TOOLS, open: ['shock'], add: ['replay', 'simulation']},
        {why: 'a tool this page does not supply', stored: '["simulation","shock"]', supplied: ['replay', 'shock'], open: ['shock'], add: ['replay']},
    ] as const)('ignores $why, and writes nothing over it', ({stored, supplied, open, add: offered}) => {
        remember(stored);
        mount(supplied, fakeController());

        expect(selectorState(), `${stored} remembered, with ${JSON.stringify(supplied)} supplied, did not open what it names that is known and supplied`).toEqual({open, add: offered});
        expect(writes(), 'mounting wrote to storage').toEqual([]);
        expect(storage.get(keyFor(USER)), 'mounting rewrote the remembered set').toBe(stored);
    });

    it.each([
        ['JSON cut short', '["replay",'],
        ['not JSON at all', 'replay'],
        ['JSON that is not a list', '{"replay":true}'],
    ])('reads %s as a first visit, and writes nothing over it', (_why, stored) => {
        remember(stored);
        mount(TOOLS, fakeController());

        expect(selectorState(), `${stored} remembered is not read as a first visit`).toEqual({open: [], add: TOOLS});
        expect(screen.queryByTestId(EMPTY), 'an L4 with no tool open does not say so').not.toBeNull();
        expect(writes(), 'mounting wrote to storage').toEqual([]);
        expect(storage.get(keyFor(USER)), 'mounting rewrote the remembered value').toBe(stored);
    });

    it('is remembered per user: what one user opened is not another’s', async () => {
        remember('["shock"]', USER);
        signedIn.set({id: OTHER_USER});
        const view = mount(TOOLS, fakeController());

        expect(selectorState(), `user ${OTHER_USER} inherits user ${USER}’s open set`).toEqual({open: [], add: TOOLS});
        await add('replay');
        expect(remembered(OTHER_USER), `user ${OTHER_USER}’s set is not remembered under ${keyFor(OTHER_USER)}`).toEqual(['replay']);
        expect(remembered(USER), `user ${OTHER_USER}’s gesture changed user ${USER}’s set`).toEqual(['shock']);
        view.unmount();

        signedIn.set({id: USER});
        mount(TOOLS, fakeController());
        expect(selectorState(), `user ${USER} does not find the set they left`).toEqual({open: ['shock'], add: ['replay', 'simulation']});
    });
});
