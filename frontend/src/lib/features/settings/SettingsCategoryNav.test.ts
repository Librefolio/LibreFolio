// @vitest-environment jsdom
/**
 * SettingsCategoryNav — component test (Vitest + jsdom), project 76, lot S1a.
 *
 * The category menu every settings page shares (Global settings, Preferences, and from S1b Plugins), extracted from
 * the two copies those pages had. The pages' own tests (`SettingsLayout.test.ts`, `GlobalSettingsTab.test.ts`) stay
 * as they were and prove that nothing they had is lost; this file pins the component's own contract:
 *
 *   - **sidebar**: one button per entry, «All» first, each with `{prefix}-category-{key}` and `aria-pressed`; a click
 *     reports the entry's id; an entry's icon is drawn, «All» has none;
 *   - **phone**: the «Category» label and a trigger with the page's label and icon; the list opens and closes on the
 *     trigger, a choice reports its id and closes it, a click outside closes it, a click inside does not; the listener
 *     goes with the block;
 *   - **keys**: an entry's test id ends with its `testKey` when it has one (Preferences' «All», whose id is '').
 *
 * `$lib/i18n` is mocked with an identity translator: the label reads `settings.category`.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {Globe, User} from 'lucide-svelte';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
// The scroll itself is the helper's (headerOffset.test.ts) and a real browser's (settings-filter-menu.spec.ts); here it is
// only asked for, with the right element.
vi.mock('$lib/utils/layout/headerOffset', async (importOriginal) => ({...(await importOriginal<typeof import('$lib/utils/layout/headerOffset')>()), scrollStartIntoView: vi.fn()}));

import SettingsCategoryNav from './SettingsCategoryNav.svelte';
import {clearHeaderOffset, HEADER_OFFSET_EVENT, publishHeaderOffset, scrollStartIntoView} from '$lib/utils/layout/headerOffset';

const ENTRIES = [
    {id: '', testKey: 'all', label: 'All'},
    {id: 'profile', icon: User, label: 'Profile'},
    {id: 'global', icon: Globe, label: 'Global'},
];

function mount(props: Record<string, unknown> = {}) {
    const onselect = vi.fn();
    const result = render(SettingsCategoryNav, {mode: 'sidebar', entries: ENTRIES, selected: '', onselect, testIdPrefix: 'nav', ...props} as never);
    return {...result, onselect};
}

beforeEach(() => {
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
        callback(0);
        return 1;
    });
});
afterEach(() => {
    cleanup();
    clearHeaderOffset();
    vi.mocked(scrollStartIntoView).mockClear();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe('SettingsCategoryNav — the sidebar', () => {
    it('draws one button per entry, in order, each with its test id', () => {
        const {container} = mount();
        const nav = container.querySelector('nav');
        expect(nav).not.toBeNull();
        expect(
            within(nav as HTMLElement)
                .getAllByRole('button')
                .map((button) => button.getAttribute('data-testid')),
        ).toEqual(['nav-category-all', 'nav-category-profile', 'nav-category-global']);
    });

    it('presses the selected entry alone', () => {
        mount({selected: 'global'});
        expect(['all', 'profile', 'global'].map((key) => screen.getByTestId(`nav-category-${key}`).getAttribute('aria-pressed'))).toEqual(['false', 'false', 'true']);
    });

    it('reports the id of the entry clicked, «All» included', async () => {
        const {onselect} = mount({selected: 'profile'});
        await fireEvent.click(screen.getByTestId('nav-category-global'));
        await fireEvent.click(screen.getByTestId('nav-category-all'));
        expect(onselect.mock.calls).toEqual([['global'], ['']]);
    });

    it('draws an icon for a category and none for «All»; the selected one adds its chevron', () => {
        mount({selected: 'global'});
        expect(screen.getByTestId('nav-category-all').querySelectorAll('svg')).toHaveLength(0);
        expect(screen.getByTestId('nav-category-profile').querySelectorAll('svg')).toHaveLength(1);
        expect(screen.getByTestId('nav-category-global').querySelectorAll('svg')).toHaveLength(2);
    });

    it('adds no document listener', () => {
        const add = vi.spyOn(document, 'addEventListener');
        mount();
        expect(add).not.toHaveBeenCalledWith('click', expect.any(Function));
        add.mockRestore();
    });
});

describe('SettingsCategoryNav — the phone dropdown', () => {
    const phone = (props: Record<string, unknown> = {}) => mount({mode: 'phone', triggerLabel: 'Global', triggerIcon: Globe, selected: 'global', ...props});
    const block = () => screen.getByTestId('nav-mobile-category-box');

    it("shows the label, and a trigger with the page's text and icon", () => {
        phone();
        expect(screen.getByTestId('nav-mobile-category-trigger')).toHaveTextContent('Global');
        // The chevron, plus the page's icon
        expect(screen.getByTestId('nav-mobile-category-trigger').querySelectorAll('svg')).toHaveLength(2);
        expect(within(block()).getAllByRole('button')).toHaveLength(1);
    });

    it('opens on the trigger, listing every entry with its test id, the selected one pressed', async () => {
        phone();
        await fireEvent.click(screen.getByTestId('nav-mobile-category-trigger'));
        const menu = screen.getByTestId('nav-mobile-category-menu');
        expect(
            within(menu)
                .getAllByRole('button')
                .map((button) => [button.getAttribute('data-testid'), button.getAttribute('aria-pressed')]),
        ).toEqual([
            ['nav-mobile-category-all', 'false'],
            ['nav-mobile-category-profile', 'false'],
            ['nav-mobile-category-global', 'true'],
        ]);
    });

    it('reports a choice and closes in one press', async () => {
        const {onselect} = phone();
        await fireEvent.click(screen.getByTestId('nav-mobile-category-trigger'));
        await fireEvent.click(screen.getByTestId('nav-mobile-category-profile'));
        expect(onselect).toHaveBeenCalledWith('profile');
        expect(screen.queryByTestId('nav-mobile-category-menu')).toBeNull();
    });

    it('closes on a second press of the trigger and on a click outside, not on one inside', async () => {
        phone();
        const trigger = screen.getByTestId('nav-mobile-category-trigger');
        await fireEvent.click(trigger);
        await fireEvent.click(trigger);
        expect(screen.queryByTestId('nav-mobile-category-menu')).toBeNull();

        await fireEvent.click(trigger);
        await fireEvent.click(screen.getByText('settings.category'));
        expect(screen.getByTestId('nav-mobile-category-menu')).toBeInTheDocument();

        await fireEvent.click(document.body);
        expect(screen.queryByTestId('nav-mobile-category-menu')).toBeNull();
    });

    it('removes its document listener when it goes', () => {
        const remove = vi.spyOn(document, 'removeEventListener');
        phone();
        cleanup();
        expect(remove).toHaveBeenCalledWith('click', expect.any(Function));
        remove.mockRestore();
    });
});

describe('SettingsCategoryNav — counts and dots (76 S1b, the Plugins menu)', () => {
    const COUNTED = [
        {id: 'all', label: 'All', count: 3},
        {id: 'asset', icon: User, label: 'Prices', count: 2, dot: true},
        {id: 'fx', icon: Globe, label: 'FX rates', count: 0},
    ];

    it('shows each count, publishes it as data-count, and the dot with its label for screen readers', () => {
        mount({entries: COUNTED, selected: 'all', dotLabel: 'Has plugins to configure'});
        expect(['all', 'asset', 'fx'].map((key) => [screen.getByTestId(`nav-category-${key}`).getAttribute('data-count'), screen.getByTestId(`nav-category-${key}`).textContent?.replace(/\s+/g, ' ').trim()])).toEqual([
            ['3', 'All 3'],
            ['2', 'Prices Has plugins to configure 2'],
            ['0', 'FX rates 0'],
        ]);
        expect(within(screen.getByTestId('nav-category-asset')).getByTestId('nav-category-dot')).toBeInTheDocument();
        expect(within(screen.getByTestId('nav-category-fx')).queryByTestId('nav-category-dot')).toBeNull();
    });

    it('draws the same counts and dot in the phone dropdown', async () => {
        mount({mode: 'phone', entries: COUNTED, selected: 'all', triggerLabel: 'All', dotLabel: 'Has plugins to configure'});
        await fireEvent.click(screen.getByTestId('nav-mobile-category-trigger'));
        expect(screen.getByTestId('nav-mobile-category-asset')).toHaveAttribute('data-count', '2');
        expect(within(screen.getByTestId('nav-mobile-category-asset')).getByTestId('nav-mobile-category-dot')).toBeInTheDocument();
    });

    it('draws no count and no data-count for an entry without one (Global settings, Preferences)', () => {
        mount();
        expect(screen.getByTestId('nav-category-profile')).not.toHaveAttribute('data-count');
        expect(screen.getByTestId('nav-category-profile').textContent?.trim()).toBe('Profile');
    });
});

/**
 * It follows the window (81 U38). Which element a choice brings back under the header is decided here; how far it scrolls
 * is `headerOffset`'s; what sticks where is a real browser's (`e2e/settings/settings-filter-menu.spec.ts`).
 */
describe('SettingsCategoryNav — a choice brings the start of the list back', () => {
    const asked = () => vi.mocked(scrollStartIntoView).mock.calls.map(([anchor]) => anchor);

    it('sidebar: the row that holds the menu and the content, after the choice has been reported', async () => {
        const {onselect, container} = mount();
        await fireEvent.click(screen.getByTestId('nav-category-global'));
        expect(onselect).toHaveBeenCalledWith('global');
        await vi.waitFor(() => expect(asked()).toHaveLength(1));
        expect(asked()[0]).toBe(screen.getByTestId('nav-category-nav').parentElement);
        expect(container.contains(asked()[0] as Element)).toBe(true);
    });

    it('sidebar: the entry already selected asks as well (the person is lost in the page, not in the filter)', async () => {
        mount({selected: 'global'});
        await fireEvent.click(screen.getByTestId('nav-category-global'));
        await vi.waitFor(() => expect(asked()).toHaveLength(1));
    });

    it("phone: the menu's own top (its label), once, and the list closes", async () => {
        const {onselect} = mount({mode: 'phone', triggerLabel: 'Global', selected: 'global'});
        await fireEvent.click(screen.getByTestId('nav-mobile-category-trigger'));
        await fireEvent.click(screen.getByTestId('nav-mobile-category-profile'));
        expect(onselect).toHaveBeenCalledWith('profile');
        await vi.waitFor(() => expect(asked()).toHaveLength(1));
        expect(asked()[0]).toBe(screen.getByTestId('nav-mobile-category-label'));
        expect(screen.queryByTestId('nav-mobile-category-menu')).toBeNull();
    });

    it('asks for nothing before a choice', () => {
        mount();
        mount({mode: 'phone'});
        expect(asked()).toHaveLength(0);
    });
});

describe('SettingsCategoryNav — the phone box is stuck when the header has been passed', () => {
    /** The sentinel is the only aria-hidden div the phone mode draws: it stands where the box would be if it were not stuck. */
    function placeSentinel(top: () => number): void {
        vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
            const t = this.getAttribute('aria-hidden') === 'true' ? top() : 0;
            return {top: t, bottom: t, left: 0, right: 0, width: 0, height: 0, x: 0, y: t, toJSON: () => ({})};
        });
    }
    const box = () => screen.getByTestId('nav-mobile-category-box');

    it('not stuck while the box is below the header, stuck once its place has passed it', async () => {
        publishHeaderOffset(64, false);
        let top = 300;
        placeSentinel(() => top);
        mount({mode: 'phone'});
        expect(box()).toHaveAttribute('data-stuck', 'false');
        top = 10;
        window.dispatchEvent(new Event('scroll'));
        await vi.waitFor(() => expect(box()).toHaveAttribute('data-stuck', 'true'));
        top = 200;
        window.dispatchEvent(new Event('scroll'));
        await vi.waitFor(() => expect(box()).toHaveAttribute('data-stuck', 'false'));
    });

    it('is judged against the offset the header publishes: the same place is stuck under a shown header and free under a hidden one', async () => {
        publishHeaderOffset(64, true);
        placeSentinel(() => 30);
        mount({mode: 'phone'});
        expect(box()).toHaveAttribute('data-stuck', 'false');
        publishHeaderOffset(64, false);
        await vi.waitFor(() => expect(box()).toHaveAttribute('data-stuck', 'true'));
        publishHeaderOffset(64, true);
        await vi.waitFor(() => expect(box()).toHaveAttribute('data-stuck', 'false'));
    });

    it('draws the border and the shadow only while stuck, and keeps the label outside the box', async () => {
        publishHeaderOffset(64, false);
        placeSentinel(() => 0);
        mount({mode: 'phone'});
        await vi.waitFor(() => expect(box()).toHaveAttribute('data-stuck', 'true'));
        expect(box().className).toContain('shadow-lf-shadow');
        expect(box().className).toContain('border-lf-subtle');
        expect(box().contains(screen.getByTestId('nav-mobile-category-label'))).toBe(false);
    });

    it('listens to the window only while it lives', () => {
        const add = vi.spyOn(window, 'addEventListener');
        const remove = vi.spyOn(window, 'removeEventListener');
        const {unmount} = mount({mode: 'phone'});
        for (const type of ['scroll', 'resize', HEADER_OFFSET_EVENT]) {
            const registration = add.mock.calls.find(([eventType]) => eventType === type);
            expect(registration, `no ${type} listener`).toBeDefined();
        }
        unmount();
        for (const type of ['scroll', 'resize', HEADER_OFFSET_EVENT]) {
            const registration = add.mock.calls.find(([eventType]) => eventType === type);
            expect(remove).toHaveBeenCalledWith(type, registration?.[1]);
        }
    });
});
