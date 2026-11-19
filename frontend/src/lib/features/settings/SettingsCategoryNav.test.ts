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
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {Globe, User} from 'lucide-svelte';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));

import SettingsCategoryNav from './SettingsCategoryNav.svelte';

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

afterEach(cleanup);

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
    const block = () => screen.getByText('settings.category').closest('div') as HTMLElement;

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
