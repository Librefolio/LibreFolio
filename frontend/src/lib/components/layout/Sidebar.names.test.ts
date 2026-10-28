// @vitest-environment jsdom
/**
 * Sidebar — the accessible names of its own controls come from the catalogue (workstream H, checkpoint 1, lot TC-5).
 *
 * The sidebar's close overlay (`aria-label`), its collapse toggle (`title`) and its mobile close button (no name at all)
 * were English text written in the markup, or nothing, so an Italian, French or Spanish user, and a screen reader, got
 * English or a nameless button. The cure takes them from the catalogue: `nav.closeSidebar` for the overlay and the
 * mobile close button, `nav.collapseSidebar` / `nav.expandSidebar` for the collapse toggle (collapsed → expand).
 *
 * The contract under test, with `$lib/i18n` answering `⟦<key>⟧` so a name is read as the key the component asked for
 * (never an English sentence): the label of a control is its `aria-label`, else its `title`;
 *   - open, expanded: the overlay (`role="button"`, outside the `<nav>`) and the mobile close button (inside
 *     `sidebar-brand`, next to the collapse toggle) are labelled `⟦nav.closeSidebar⟧`, and no other control is;
 *   - closed, expanded: only the mobile close button;
 *   - collapsed: no mobile close button (the sidebar shows icons only), and the toggle says `⟦nav.expandSidebar⟧`;
 *     expanded, the toggle says `⟦nav.collapseSidebar⟧`.
 * The catalogue keys themselves are pinned in `src/lib/i18n/frameKeys.test.ts`.
 *
 * Set up as `Sidebar.legal.test.ts` does (read it for what is replaced and why): the changelog modal and the connection
 * indicator are no-op components, `$app/stores` and `$app/environment` are the aliases of `vitest.config.ts`, and the
 * generated alias of `GET /system/instance` is spied and refuses. The sidebar is imported once in a `beforeAll`.
 *
 * Written red-first, before the cure.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, render, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';

const i18n = vi.hoisted(() => ({mark: (key: string): string => `⟦${key}⟧`}));

vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const translator = readable(i18n.mark);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: translator, t: translator};
});
vi.mock('$lib/components/layout/ChangelogModal.svelte', () => ({default: () => {}}));
vi.mock('$lib/components/layout/ConnectionSecurityIndicator.svelte', () => ({default: () => {}}));

import {zodiosApi} from '$lib/api';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

let Sidebar: typeof import('./Sidebar.svelte').default;

const INSTANCE_ALIAS = 'get_instance_config_api_v1_system_instance_get';
const instanceEndpoint = zodiosApi as unknown as Record<typeof INSTANCE_ALIAS, () => Promise<InstanceConfig>>;

/** A control's label: its `aria-label`, else its `title`. `null` when it has neither. */
function labelOf(element: Element): string | null {
    return element.getAttribute('aria-label') ?? element.getAttribute('title');
}

function mountSidebar(props: {collapsed: boolean; isOpen: boolean}): HTMLElement {
    return render(Sidebar, {props}).container;
}

/** Every button-like control of the document: a `<button>` or an element with `role="button"`, the overlay included. */
function controls(root: HTMLElement): HTMLElement[] {
    return Array.from(root.querySelectorAll<HTMLElement>('button, [role="button"]'));
}

/** The controls labelled `label`. */
function labelled(root: HTMLElement, label: string): HTMLElement[] {
    return controls(root).filter((element) => labelOf(element) === label);
}

beforeAll(async () => {
    assertEffectsRun();
    Sidebar = (await import('./Sidebar.svelte')).default;
}, 180_000);

beforeEach(() => {
    vi.spyOn(instanceEndpoint, INSTANCE_ALIAS).mockRejectedValue(new Error('no network in this test'));
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

describe('Sidebar — control names come from the catalogue (TC-5)', () => {
    it('TC5-01: open and expanded, the overlay and the mobile close button are both named nav.closeSidebar, and nothing else is', () => {
        const sidebar = mountSidebar({collapsed: false, isOpen: true});
        // Presence barrier: the overlay is drawn (it is the only `role="button"` outside the <nav>), and the brand row holds its toggle and its close button.
        const nav = sidebar.querySelector('nav') as HTMLElement;
        const overlay = controls(sidebar).filter((element) => !nav.contains(element));
        const brand = within(sidebar).getByTestId('sidebar-brand');
        const brandButtons = Array.from(brand.querySelectorAll<HTMLElement>('button'));
        expect(overlay, 'barrier: the open sidebar draws its overlay').toHaveLength(1);
        expect(brandButtons, 'barrier: the brand row holds the collapse toggle and the mobile close button').toHaveLength(2);

        const named = labelled(sidebar, i18n.mark('nav.closeSidebar'));

        expect(named, 'the overlay and the mobile close button carry nav.closeSidebar').toHaveLength(2);
        expect(named).toContain(overlay[0]);
        expect(
            named.filter((element) => brand.contains(element)),
            'one of them is the mobile close button of the brand row',
        ).toHaveLength(1);
        expect(
            named.some((element) => element.getAttribute('data-testid') === 'sidebar-collapse-toggle'),
            'the collapse toggle is not the close button',
        ).toBe(false);
    });

    it('TC5-02: closed and expanded, only the mobile close button is named nav.closeSidebar', () => {
        const sidebar = mountSidebar({collapsed: false, isOpen: false});
        const brand = within(sidebar).getByTestId('sidebar-brand');
        expect(Array.from(brand.querySelectorAll('button')), 'barrier: the brand row holds the toggle and the close button').toHaveLength(2);

        const named = labelled(sidebar, i18n.mark('nav.closeSidebar'));

        expect(named, 'no overlay while closed; the mobile close button is named').toHaveLength(1);
        expect(brand.contains(named[0])).toBe(true);
    });

    it('TC5-03: expanded, the collapse toggle says nav.collapseSidebar', () => {
        const sidebar = mountSidebar({collapsed: false, isOpen: false});

        const toggle = within(sidebar).getByTestId('sidebar-collapse-toggle');

        expect(labelOf(toggle), 'expanded → the toggle collapses').toBe(i18n.mark('nav.collapseSidebar'));
    });

    it('TC5-04: collapsed, the toggle says nav.expandSidebar and there is no mobile close button', () => {
        const sidebar = mountSidebar({collapsed: true, isOpen: false});
        const toggle = within(sidebar).getByTestId('sidebar-collapse-toggle');

        expect(labelOf(toggle), 'collapsed → the toggle expands').toBe(i18n.mark('nav.expandSidebar'));
        expect(labelled(sidebar, i18n.mark('nav.closeSidebar')), 'collapsed, no close button and no overlay').toHaveLength(0);
        expect(within(sidebar).getByTestId('sidebar-brand').querySelectorAll('button'), 'barrier: the brand row holds the toggle alone').toHaveLength(1);
    });
});
