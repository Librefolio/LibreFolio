// @vitest-environment jsdom
/**
 * RiskLevelSection — the frame around one risk level (Vitest + jsdom).
 *
 * What is pinned: how the frame names a measurement that did not come back whole,
 * in `{testId}-health`. The caller hands over identifiers and the frame words
 * them, from one of two sources: the entry's own `label` — an i18n key, used
 * where the analytic's name would be ambiguous, since L1 asks `historical_var`
 * once for a day and once for a month — else the analytic's catalogue name, keyed
 * by `analyticNameKey`, the camelCase rule the notice above the levels shares.
 *
 * A snake_case code is the case the rule exists for: `historical_var` lives at
 * `risk.analytics.historicalVar.name`. A frame that built the key from the raw
 * code would find nothing and print `historical_var` through its `{default: code}`
 * fallback — and `partialNotice.test.ts` could not see it, because it tests the
 * rule, not whether this frame uses it.
 *
 * Expected text is resolved from the shipped catalogue through the same `$_` the
 * component uses; no sentence is written down here. The harness case guards the
 * ways that could go vacuous: a key missing from the catalogue (svelte-i18n
 * echoes the id back), a name that reads like the raw code (then the fallback
 * would pass for it), an uncamelled key that happens to exist (then a frame
 * without the rule would pass too), and a label that reads like the analytic's
 * name (then which branch rendered has no answer).
 *
 * Mounted alone, with props only: no controller, no store, no mock.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {createRawSnippet, type ComponentProps, type Snippet} from 'svelte';
import {get} from 'svelte/store';

import {fireEvent, render, screen, setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import DocsLink from '$lib/components/ui/DocsLink.svelte';

import type {ResultHealth} from './levelHelpers';
import RiskLevelSection from './RiskLevelSection.svelte';

const TEST_ID = 'risk-level-under-test';
/** A multi-word analytic code: the one shape the camelCase rule changes. */
const CODE = 'historical_var';
const NAME_KEY = 'risk.analytics.historicalVar.name';
/** The key a frame would build from the raw code, without the camelCase rule. */
const UNCAMELLED_KEY = `risk.analytics.${CODE}.name`;
const FAILED_KEY = 'risk.states.failed';
const UNAVAILABLE_KEY = 'risk.states.unavailable';
/** The label L1 gives its one-day VaR, the instance the analytic's name alone cannot tell from the month. */
const DAY_LABEL = 'risk.levels.l1.rows.day';

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** A catalogue sentence as the component formats it: `$_`, no values. */
function resolve(key: string): string {
    return normalize(get(_)(key));
}

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** The frame, open (it is not collapsible), holding `health` and nothing else; its health line. */
function healthLine(health: ResultHealth[]): HTMLElement {
    render(RiskLevelSection, {props: {title: 'Synthetic level title', level: 1, testId: TEST_ID, health}});
    const line = screen.getByTestId(`${TEST_ID}-health`);
    // Barrier: one entry per measurement given, so the text below is about these and nothing else.
    expect(line, 'the health line does not hold one entry per measurement').toHaveAttribute('data-count', String(health.length));
    return line;
}

beforeAll(async () => {
    await setupI18n('en');
});

describe('RiskLevelSection — the harness itself', () => {
    it('resolves every key it compares against, and none of them reads like another outcome', () => {
        for (const key of [NAME_KEY, FAILED_KEY, UNAVAILABLE_KEY, DAY_LABEL]) {
            expect(typeof at(en, key), `${key} is missing from en.json`).toBe('string');
            expect(resolve(key), `${key} does not resolve: the catalogue is not loaded`).not.toBe(key);
        }
        const name = resolve(NAME_KEY);
        // A missed key prints the raw code (`{default: code}`): were the name the code, a miss would pass.
        expect(name, `${NAME_KEY} reads like the raw code: a missed key could not be told from a found one`).not.toBe(CODE);
        // The key a frame without the rule would build must miss, or that frame would find a name too.
        expect(get(_)(UNCAMELLED_KEY), `${UNCAMELLED_KEY} exists after all: a frame that skipped the camelCase rule would still be named`).toBe(UNCAMELLED_KEY);
        expect(resolve(DAY_LABEL), 'the label reads like the analytic name: which of the two rendered could not be told').not.toBe(name);
    });
});

describe('RiskLevelSection — how a measurement that did not come back whole is named', () => {
    it('names a failed snake_case measurement by its catalogue name, found through the camelCase rule', () => {
        const line = healthLine([{instanceId: 'synthetic-var', code: CODE, status: 'failed'}]);
        expect(normalize(line.textContent), `${CODE} is not named by ${NAME_KEY}: the frame built its key without analyticNameKey`).toBe(`${resolve(NAME_KEY)}: ${resolve(FAILED_KEY)}`);
    });

    it('names a labelled measurement by its label, not by the analytic behind it', () => {
        const line = healthLine([{instanceId: 'synthetic-day-var', code: CODE, status: 'unavailable', label: DAY_LABEL}]);
        expect(normalize(line.textContent), `the entry is not named by its label ${DAY_LABEL}`).toBe(`${resolve(DAY_LABEL)}: ${resolve(UNAVAILABLE_KEY)}`);
    });
});

// ─── The actions slot ───────────────────────────────────────────────────────────────────────
/*
 * `actions` — a caller's own controls for its level, drawn in the frame's header just before
 * the manual's icon, on the icon's row. L1° of Asset Global is the first caller: it puts its
 * loss table's column toggle there. Three things are pinned, in both branches of the header:
 *
 *   - **Absent, nothing new.** A frame given no actions draws the header it drew before the slot
 *     existed: the same elements, nested the same way, the manual's icon still a direct child of
 *     its row. These cases are *guards* — green before the slot and required to stay green after
 *     it — because a wrapper added for the slot's sake would restyle every level on every page,
 *     including the many that will never pass an action.
 *   - **Present, beside the icon.** After the title in a fixed level, after the toggle in a
 *     collapsible one; in that row, before the icon; never inside the `<h3>` (a control inside a
 *     heading) nor inside the toggle (a button nested in a button, whose every click would also
 *     fold the level). Drawn exactly once, and drawn with no manual page too.
 *   - **A click on an action is not a click on the level.** It neither opens nor closes a
 *     collapsible level, and it does not fire `onfirstopen`, which is a request for data.
 *
 * The action is a raw snippet — a real `<button>` whose clicks are counted — so no wrapper
 * component is needed. The harness cases prove that it renders and counts where the frame is
 * known to render a snippet (its body, as `children`), so an action missing from the header is
 * the frame's doing and not the probe's; and that the header's shape can see a wrapper at all.
 */

/** The manual page of every "with a manual page" case. Any path does: the frame only forwards it. */
const DOCS_PATH = 'financial-theory/technical-analysis/risk-metrics/';
/** The probe action's testid. */
const ACTION = 'probe-action';
/** What must never sit inside the title or the toggle. */
const INTERACTIVE = 'a[href], button, input, select, textarea, [tabindex], [role="button"]';

/** The two branches of the header, and the element an action follows in each. */
const BRANCHES = [
    {name: 'fixed', collapsible: false, leader: 'title'},
    {name: 'collapsible', collapsible: true, leader: 'toggle'},
] as const;

/**
 * The frame's props with `actions`, the slot under test — declared here, so the spec states the
 * contract it expects and compiles on either side of the prop's arrival.
 */
type FrameProps = ComponentProps<typeof RiskLevelSection> & {actions?: Snippet};

/** A header action as a caller writes one: a real button, its clicks counted. */
function probeAction(onclick: () => void = () => {}): Snippet {
    return createRawSnippet(() => ({
        render: () => `<button type="button" data-testid="${ACTION}">probe</button>`,
        setup: (element) => {
            element.addEventListener('click', onclick);
            return () => element.removeEventListener('click', onclick);
        },
    }));
}

/** A frame with a title and a lead, plus whatever the case adds; the section it renders. */
function mountFrame(props: Partial<FrameProps> = {}): HTMLElement {
    const all: FrameProps = {title: 'Synthetic level title', lead: 'Synthetic lead sentence', level: 2, testId: TEST_ID, ...props};
    render(RiskLevelSection, {props: all});
    return screen.getByTestId(TEST_ID);
}

/** The probe action, which must be drawn exactly once. */
function theAction(): HTMLElement {
    const drawn = screen.queryAllByTestId(ACTION);
    expect(drawn, 'the action is not drawn exactly once — none: the frame ignores `actions`; two: it is drawn inside the header snippet and beside it').toHaveLength(1);
    return drawn[0];
}

/**
 * Where an action belongs in a branch: the element it must follow and never enter — the title
 * in a fixed level, the toggle in a collapsible one — and the row that element heads.
 */
function head(collapsible: boolean): {leader: HTMLElement; row: HTMLElement} {
    const leader = screen.getByTestId(collapsible ? `${TEST_ID}-toggle` : `${TEST_ID}-title`);
    const row = leader.parentElement;
    if (row === null) throw new Error('the header has no row: the frame is not mounted');
    return {leader, row};
}

/** The manual's control as the frame places it: DocsLink's root, one level above its button. */
function docsControl(): HTMLElement {
    const control = screen.getByTestId(`${TEST_ID}-docs`).parentElement;
    if (control === null) throw new Error('the manual icon has no parent: the frame is not mounted');
    return control;
}

/** Whether `first` comes before `second` in document order, `second` not inside it. */
function precedes(first: Node, second: Node): boolean {
    return !first.contains(second) && (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

/**
 * The header as a shape: every element's tag and testid (short of the frame's prefix), nested,
 * and nothing else — no class, no text. Three leaves are opaque: the body (`div[body]`), which
 * is not header; the manual's control (`docs`), which is DocsLink's own and wraps its button in
 * its Tooltip; and the chevron (`svg`), which is lucide's.
 */
function headerShape(section: Element): string {
    const docs = section.querySelector(`[data-testid="${TEST_ID}-docs"]`)?.parentElement ?? null;
    const walk = (node: Element): string => {
        if (node === docs) return 'docs';
        const tag = node.tagName.toLowerCase();
        if (tag === 'svg') return tag;
        const testId = node.getAttribute('data-testid');
        const label = testId === null ? tag : `${tag}[${testId.startsWith(`${TEST_ID}-`) ? testId.slice(TEST_ID.length + 1) : testId}]`;
        if (testId === `${TEST_ID}-body`) return label;
        const children = [...node.children].map(walk);
        return children.length > 0 ? `${label}(${children.join(' ')})` : label;
    };
    return [...section.children].map(walk).join(' ');
}

/**
 * The header each branch drew before the slot existed, as `headerShape` writes it — read off the
 * component as it stood then. An intended change to the header updates this table, and says so.
 */
const HEADER_BEFORE_THE_SLOT = [
    {label: 'a fixed level with a manual page', collapsible: false, docsPath: DOCS_PATH, shape: 'div(div(div(h3[title] docs) p[lead])) div[body]'},
    {label: 'a fixed level without one', collapsible: false, docsPath: undefined, shape: 'div(div(div(h3[title]) p[lead])) div[body]'},
    {label: 'a collapsible level with a manual page', collapsible: true, docsPath: DOCS_PATH, shape: 'div(button[toggle](div(div(h3[title]) p[lead]) svg) docs)'},
    {label: 'a collapsible level without one', collapsible: true, docsPath: undefined, shape: 'div(button[toggle](div(div(h3[title]) p[lead]) svg))'},
];

describe('RiskLevelSection — the actions slot: the harness itself', () => {
    it('the probe is a working action where the frame is known to render a snippet: drawn once, a button, its clicks counted', async () => {
        const clicks = vi.fn();
        mountFrame({children: probeAction(clicks)});
        const action = theAction();
        expect(screen.getByTestId(`${TEST_ID}-body`).contains(action), 'the probe, passed as children, is not in the body').toBe(true);
        expect(action.tagName, 'the probe is not a button').toBe('BUTTON');

        await fireEvent.click(action);
        expect(clicks, 'a click on the probe is not counted').toHaveBeenCalledTimes(1);
    });

    it("DocsLink is one element around its button — the shape's `docs` leaf", () => {
        const {container} = render(DocsLink, {props: {path: DOCS_PATH, icon: 'book', testId: 'probe-docs'}});
        expect(container.children, 'DocsLink no longer renders one root: the `docs` leaf of the shape starts elsewhere').toHaveLength(1);
        expect(screen.getByTestId('probe-docs').parentElement, 'DocsLink no longer wraps its button in exactly one element').toBe(container.firstElementChild);
    });

    it('the shape sees a wrapper: one more element around the manual icon changes it', () => {
        const section = mountFrame({docsPath: DOCS_PATH});
        // On a detached copy: the frame's own DOM stays Svelte's.
        const copy = section.cloneNode(true) as HTMLElement;
        const control = copy.querySelector(`[data-testid="${TEST_ID}-docs"]`)?.parentElement;
        if (!control) throw new Error('the copy has no manual icon');
        const wrapper = document.createElement('div');
        control.before(wrapper);
        wrapper.append(control);
        expect(headerShape(copy), 'a wrapper around the manual icon leaves the shape unchanged: the guards below could not see one').not.toBe(headerShape(section));
    });
});

describe('RiskLevelSection — the actions slot: without actions, the header drawn before the slot', () => {
    for (const {label, collapsible, docsPath, shape} of HEADER_BEFORE_THE_SLOT) {
        it(`draws ${label} exactly as before`, () => {
            const section = mountFrame({collapsible, docsPath});
            expect(headerShape(section), 'the header drawn without actions is not the header drawn before the slot existed').toBe(shape);
        });
    }

    for (const {name, collapsible, leader: leaderName} of BRANCHES) {
        it(`keeps the manual icon a direct child of the ${leaderName} row in a ${name} level, with nothing added beside it`, () => {
            mountFrame({collapsible, docsPath: DOCS_PATH});
            const {leader, row} = head(collapsible);
            const control = docsControl();
            expect(
                [...row.children].map((child) => (child === leader ? leaderName : child === control ? 'docs' : child.tagName.toLowerCase())),
                `the ${leaderName} row no longer holds the ${leaderName} and the manual icon alone`,
            ).toEqual([leaderName, 'docs']);
        });
    }
});

describe('RiskLevelSection — the actions slot: present, beside the manual icon', () => {
    for (const {name, collapsible, leader: leaderName} of BRANCHES) {
        it(`in a ${name} level: in the ${leaderName} row, after the ${leaderName} and never inside it, and before the manual icon`, () => {
            mountFrame({collapsible, docsPath: DOCS_PATH, actions: probeAction()});
            const action = theAction();
            const docs = screen.getByTestId(`${TEST_ID}-docs`);
            const {leader, row} = head(collapsible);

            expect(leader.contains(action), `the action is inside the ${leaderName}`).toBe(false);
            expect(leader.querySelector(INTERACTIVE), `something interactive is nested in the ${leaderName}`).toBeNull();
            expect(row.contains(action), `the action is not in the ${leaderName} row`).toBe(true);
            expect(precedes(leader, action), `the action does not come after the ${leaderName}`).toBe(true);
            expect(precedes(action, docs), 'the action does not come before the manual icon').toBe(true);
            expect(row.contains(docs), `the manual icon left the ${leaderName} row`).toBe(true);
        });

        it(`in a ${name} level with no manual page: still drawn, in the ${leaderName} row, after the ${leaderName} and never inside it`, () => {
            mountFrame({collapsible, actions: probeAction()});
            expect(screen.queryByTestId(`${TEST_ID}-docs`), 'premise: no manual page, no manual icon').toBeNull();
            const action = theAction();
            const {leader, row} = head(collapsible);

            expect(leader.contains(action), `the action is inside the ${leaderName}`).toBe(false);
            expect(row.contains(action), `the action is not in the ${leaderName} row`).toBe(true);
            expect(precedes(leader, action), `the action does not come after the ${leaderName}`).toBe(true);
        });
    }
});

describe('RiskLevelSection — the actions slot: a click on an action is not a click on the level', () => {
    it('neither opens nor closes a collapsible level, and does not fire onfirstopen', async () => {
        const clicks = vi.fn();
        const onfirstopen = vi.fn();
        const section = mountFrame({collapsible: true, docsPath: DOCS_PATH, actions: probeAction(clicks), onfirstopen});
        const {leader: toggle} = head(true);
        const expectOpen = (open: boolean, why: string) => {
            expect(toggle, why).toHaveAttribute('aria-expanded', String(open));
            expect(section, why).toHaveAttribute('data-open', String(open));
        };
        expectOpen(false, 'premise: a collapsible level is born closed');

        await fireEvent.click(theAction());
        expect(clicks, 'the click never reached the action').toHaveBeenCalledTimes(1);
        expectOpen(false, 'a click on the action opened the level');
        expect(onfirstopen, "a click on the action asked for the level's data").not.toHaveBeenCalled();

        // The control: the toggle does open the level, and asks once — so the assertions
        // above were about live attributes and a live callback.
        await fireEvent.click(toggle);
        expectOpen(true, 'the toggle did not open the level');
        expect(onfirstopen, 'opening the level did not ask for its data').toHaveBeenCalledTimes(1);

        await fireEvent.click(theAction());
        expect(clicks, 'the second click never reached the action').toHaveBeenCalledTimes(2);
        expectOpen(true, 'a click on the action closed the level');
        expect(onfirstopen, 'a click on the action asked for the data again').toHaveBeenCalledTimes(1);
    });
});
