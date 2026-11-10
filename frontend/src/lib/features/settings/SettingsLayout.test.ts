// @vitest-environment jsdom
/**
 * SettingsLayout — component test (Vitest + jsdom).
 *
 * The frame every settings page sits in: a category list on the left (a
 * dropdown instead, on a phone), a title row on the right, and up to four action
 * buttons — save-all, undo-all, reset-all, lock — whose presence is decided by a
 * five-flag truth table. It owns no data and talks to no API: `categories`,
 * `selectedCategory`, `hasChanges`, `hasNonDefaults`, `isLocked` and `showLock`
 * come in as props, and `onsaveAll` / `onundoAll` / `onresetAll` /
 * `ontoggleLock` go out as callback props.
 *
 * That truth table is the subject. `settings.spec.ts` drives the real settings
 * page, where the flags are whatever the stored settings happen to make them —
 * in practice "unlocked, nothing modified" plus a brief "modified" while a spec
 * edits a field. The locked combinations, and the one that matters most (locked
 * *with* unsaved changes, where the save button is withdrawn), are not reachable
 * from there without an admin flipping a global lock in a shared database.
 *
 * Two notes on how things are addressed:
 *
 *   - **What it publishes.** Every category button carries a `data-testid` and
 *     its selected state as `aria-pressed` — "true" on the selected one, "false"
 *     on every other: `settings-category-all` and `settings-category-{id}` in the
 *     sidebar; `settings-mobile-category-all` and `settings-mobile-category-{id}`
 *     in the phone dropdown, rendered only while it is open, behind
 *     `settings-mobile-category-trigger`. The selection is therefore asserted
 *     directly. The tests that read it off the phone trigger's label stay: that
 *     label is a behaviour of its own — derived from the selection, falling back
 *     to All, carrying the category's icon — and nothing else covers it.
 *     The root is `settings-layout`, with `data-busy`, and the save-all /
 *     undo-all / reset-all buttons come from `SettingBulkActions` with ids of
 *     their own; the lock button has none. So the table of actions still names
 *     every button by its `title`: `$lib/i18n` is mocked with an identity
 *     translator, `title={$_('common.saveAll')}` renders as the literal key, and
 *     every query names a *key*, stable in all four languages, never a sentence.
 *
 *   - **Both layouts are in the DOM at once.** `sm:hidden` and `hidden sm:block`
 *     are Tailwind, and jsdom has no stylesheet, so the phone dropdown and the
 *     desktop sidebar both render and every category label appears at least
 *     twice. Every query is therefore scoped — to `<nav>` for the sidebar, to
 *     the block owning the `settings.category` label for the dropdown — or goes
 *     through a test id, which belongs to one layout by construction, rather
 *     than reaching for a global `getByText` that would resolve ambiguously.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {readable} from 'svelte/store';
import {Globe, Lock as LockIcon, User} from 'lucide-svelte';
import {cleanup, fireEvent, render, screen, within} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));

import SettingsLayout from './SettingsLayout.svelte';

const CATEGORIES = [
    {id: 'profile', icon: User, labelKey: 'settings.categoryProfile'},
    {id: 'global', icon: Globe, labelKey: 'settings.categoryGlobal'},
    {id: 'security', icon: LockIcon, labelKey: 'settings.categorySecurity'},
];

interface Mounted {
    container: HTMLElement;
    saveAll: ReturnType<typeof vi.fn>;
    undoAll: ReturnType<typeof vi.fn>;
    resetAll: ReturnType<typeof vi.fn>;
    toggleLock: ReturnType<typeof vi.fn>;
}

function mount(props: Record<string, unknown> = {}): Mounted {
    const saveAll = vi.fn();
    const undoAll = vi.fn();
    const resetAll = vi.fn();
    const toggleLock = vi.fn();
    const {container} = render(SettingsLayout, {
        categories: CATEGORIES,
        selectedCategory: '',
        title: 'Settings under test',
        onsaveAll: saveAll,
        onundoAll: undoAll,
        onresetAll: resetAll,
        ontoggleLock: toggleLock,
        ...props,
    } as never);
    return {container, saveAll, undoAll, resetAll, toggleLock};
}

/** The desktop sidebar — the only `<nav>` in the component. */
function sidebar(container: HTMLElement): HTMLElement {
    const nav = container.querySelector('nav');
    if (!nav) throw new Error('no sidebar rendered');
    return nav;
}

/** The phone block, found through the label it owns rather than its class. */
function mobileBlock(): HTMLElement {
    const el = screen.getByText('settings.category').closest('div');
    if (!el) throw new Error('no mobile block rendered');
    return el;
}

/** The dropdown trigger, by its test id: it is rendered open or closed. */
function mobileTrigger(): HTMLElement {
    return screen.getByTestId('settings-mobile-category-trigger');
}

/** All, then every category, by the id their test ids end with. */
const CATEGORY_KEYS = ['all', ...CATEGORIES.map((category) => category.id)];

/** `aria-pressed` of All and of every category, in the sidebar or in the open dropdown. */
function pressed(layout: 'settings-category' | 'settings-mobile-category'): Record<string, string | null> {
    return Object.fromEntries(CATEGORY_KEYS.map((key) => [key, screen.getByTestId(`${layout}-${key}`).getAttribute('aria-pressed')]));
}

/** What `pressed()` reads when `selected` — `all`, or a category id — is the selection: "true" there, "false" everywhere else. */
function onlyPressed(selected: string): Record<string, string> {
    return Object.fromEntries(CATEGORY_KEYS.map((key) => [key, key === selected ? 'true' : 'false']));
}

/** Every action button currently offered, by the i18n key of its title. */
function actionTitles(): string[] {
    return [...document.querySelectorAll<HTMLElement>('[title]')].map((el) => el.getAttribute('title') ?? '');
}

afterEach(cleanup);

describe('SettingsLayout — the category list', () => {
    it('offers All plus every category it was given, in the sidebar', () => {
        const {container} = mount();

        const nav = sidebar(container);
        expect(within(nav).getByRole('button', {name: 'settings.all'})).toBeInTheDocument();
        for (const category of CATEGORIES) {
            expect(within(nav).getByRole('button', {name: category.labelKey})).toBeInTheDocument();
        }
    });

    it('names the selected category on the phone trigger', () => {
        mount({selectedCategory: 'global'});

        expect(mobileTrigger()).toHaveTextContent('settings.categoryGlobal');
    });

    it('names All on the phone trigger when nothing is filtered', () => {
        mount({selectedCategory: ''});

        expect(mobileTrigger()).toHaveTextContent('settings.all');
    });

    it('falls back to All when the selected id is not in the list', () => {
        // The parent can hand down an id that no longer exists — a category
        // removed by a role change, or a stale value restored from the URL. The
        // trigger must still say something rather than render "undefined".
        mount({selectedCategory: 'category-that-was-removed'});

        expect(mobileTrigger()).toHaveTextContent('settings.all');
    });

    it('shows the category icon on the trigger only once one is selected', () => {
        // The icon has no accessible name and no attribute of its own, so it is
        // counted structurally: the trigger always carries the chevron, and a
        // selected category adds exactly one more glyph in front of the label.
        const {container} = mount({selectedCategory: ''});
        expect(mobileTrigger().querySelectorAll('svg')).toHaveLength(1);

        cleanup();
        mount({selectedCategory: 'profile'});
        expect(mobileTrigger().querySelectorAll('svg')).toHaveLength(2);
        void container;
    });

    it('shows no icon for an id that matches no category', () => {
        mount({selectedCategory: 'category-that-was-removed'});

        expect(mobileTrigger().querySelectorAll('svg')).toHaveLength(1);
    });

    it('switches category when the sidebar is used', async () => {
        // The selection is a bound prop; besides its `aria-pressed` (the
        // describe below), the label the phone trigger derives from it must
        // follow a change made in the sidebar.
        const {container} = mount({selectedCategory: ''});

        await fireEvent.click(within(sidebar(container)).getByRole('button', {name: 'settings.categorySecurity'}));

        expect(mobileTrigger()).toHaveTextContent('settings.categorySecurity');
    });

    it('goes back to All from the sidebar', async () => {
        const {container} = mount({selectedCategory: 'security'});

        await fireEvent.click(within(sidebar(container)).getByRole('button', {name: 'settings.all'}));

        expect(mobileTrigger()).toHaveTextContent('settings.all');
    });
});

describe('SettingsLayout — the phone dropdown', () => {
    it('starts closed', () => {
        mount();

        // Closed, the block holds exactly one button: the trigger itself.
        expect(within(mobileBlock()).getAllByRole('button')).toHaveLength(1);
    });

    it('opens on the trigger and lists All plus every category', async () => {
        mount();

        await fireEvent.click(mobileTrigger());

        const block = mobileBlock();
        expect(within(block).getByRole('button', {name: 'settings.categoryProfile'})).toBeInTheDocument();
        // Trigger + All + three categories.
        expect(within(block).getAllByRole('button')).toHaveLength(5);
    });

    it('closes again when the trigger is pressed a second time', async () => {
        mount();
        const trigger = mobileTrigger();
        await fireEvent.click(trigger);
        expect(within(mobileBlock()).getAllByRole('button')).toHaveLength(5);

        await fireEvent.click(trigger);

        expect(within(mobileBlock()).getAllByRole('button')).toHaveLength(1);
    });

    it('selects a category and closes in one press', async () => {
        mount({selectedCategory: ''});
        const trigger = mobileTrigger();
        await fireEvent.click(trigger);

        await fireEvent.click(within(mobileBlock()).getByRole('button', {name: 'settings.categoryGlobal'}));

        expect(trigger).toHaveTextContent('settings.categoryGlobal');
        expect(within(mobileBlock()).getAllByRole('button')).toHaveLength(1);
    });

    it('selects All from the dropdown and closes', async () => {
        mount({selectedCategory: 'global'});
        const trigger = mobileTrigger();
        await fireEvent.click(trigger);

        await fireEvent.click(within(mobileBlock()).getByRole('button', {name: 'settings.all'}));

        expect(trigger).toHaveTextContent('settings.all');
        expect(within(mobileBlock()).getAllByRole('button')).toHaveLength(1);
    });

    it('closes when the user clicks anywhere else on the page', async () => {
        const {container} = mount();
        await fireEvent.click(mobileTrigger());
        expect(within(mobileBlock()).getAllByRole('button')).toHaveLength(5);

        await fireEvent.click(document.body);

        expect(within(mobileBlock()).getAllByRole('button')).toHaveLength(1);
        void container;
    });

    it('stays open when the click lands inside its own block', async () => {
        mount();
        await fireEvent.click(mobileTrigger());

        // The label the block owns — inside the surface, so not an outside click.
        await fireEvent.click(screen.getByText('settings.category'));

        expect(within(mobileBlock()).getAllByRole('button')).toHaveLength(5);
    });

    it('stops listening for outside clicks once it is gone', async () => {
        // `onDestroy` removes the document listener. Without it every mounted-then-
        // discarded settings page would leave a handler behind, and the leak is
        // silent until something else throws inside it.
        const remove = vi.spyOn(document, 'removeEventListener');
        mount();

        cleanup();

        expect(remove).toHaveBeenCalledWith('click', expect.any(Function));
        remove.mockRestore();
    });
});

describe('SettingsLayout — the selected category, as each button publishes it', () => {
    it('gives All and every category a test id in the sidebar, each on its own button', () => {
        const {container} = mount();

        const nav = sidebar(container);
        expect(within(nav).getByTestId('settings-category-all')).toHaveTextContent('settings.all');
        for (const category of CATEGORIES) {
            expect(within(nav).getByTestId(`settings-category-${category.id}`)).toHaveTextContent(category.labelKey);
        }
    });

    it('gives the phone trigger a test id, and All and every category one once the dropdown is open', async () => {
        mount();

        // Closed, the block's only button is the one carrying the trigger's id, and no option is rendered.
        const block = mobileBlock();
        expect(within(block).getAllByRole('button')).toEqual([within(block).getByTestId('settings-mobile-category-trigger')]);
        expect(screen.queryByTestId('settings-mobile-category-all')).toBeNull();

        await fireEvent.click(mobileTrigger());

        expect(within(block).getByTestId('settings-mobile-category-all')).toHaveTextContent('settings.all');
        for (const category of CATEGORIES) {
            expect(within(block).getByTestId(`settings-mobile-category-${category.id}`)).toHaveTextContent(category.labelKey);
        }
    });

    it('presses All alone when nothing is filtered, in the sidebar and in the dropdown', async () => {
        mount({selectedCategory: ''});

        expect(pressed('settings-category')).toEqual(onlyPressed('all'));
        await fireEvent.click(mobileTrigger());
        expect(pressed('settings-mobile-category')).toEqual(onlyPressed('all'));
    });

    it('presses the selected category alone, in the sidebar and in the dropdown', async () => {
        mount({selectedCategory: 'global'});

        expect(pressed('settings-category')).toEqual(onlyPressed('global'));
        await fireEvent.click(mobileTrigger());
        expect(pressed('settings-mobile-category')).toEqual(onlyPressed('global'));
    });

    it('moves the pressed state with a choice made in the sidebar, in both layouts', async () => {
        mount({selectedCategory: ''});

        await fireEvent.click(screen.getByTestId('settings-category-security'));

        expect(pressed('settings-category')).toEqual(onlyPressed('security'));
        await fireEvent.click(mobileTrigger());
        expect(pressed('settings-mobile-category')).toEqual(onlyPressed('security'));

        await fireEvent.click(screen.getByTestId('settings-category-all'));

        expect(pressed('settings-category')).toEqual(onlyPressed('all'));
    });

    it('moves the pressed state with a choice made in the dropdown, in both layouts', async () => {
        mount({selectedCategory: 'global'});
        await fireEvent.click(mobileTrigger());

        await fireEvent.click(screen.getByTestId('settings-mobile-category-profile'));

        // The choice closes the dropdown; reopened, it presses the new category alone.
        expect(screen.queryByTestId('settings-mobile-category-profile')).toBeNull();
        expect(pressed('settings-category')).toEqual(onlyPressed('profile'));
        await fireEvent.click(mobileTrigger());
        expect(pressed('settings-mobile-category')).toEqual(onlyPressed('profile'));

        await fireEvent.click(screen.getByTestId('settings-mobile-category-all'));

        expect(pressed('settings-category')).toEqual(onlyPressed('all'));
        await fireEvent.click(mobileTrigger());
        expect(pressed('settings-mobile-category')).toEqual(onlyPressed('all'));
    });
});

describe('SettingsLayout — which actions are offered', () => {
    it('offers none of them when there is nothing to do and no lock', () => {
        mount({hasChanges: false, hasNonDefaults: false, showLock: false});

        expect(actionTitles()).toEqual([]);
    });

    it('offers save and undo, but not reset, for unsaved changes on default values', () => {
        mount({hasChanges: true, hasNonDefaults: false});

        expect(actionTitles()).toEqual(['common.saveAll', 'common.undoAll']);
    });

    it('offers reset alone when the stored values differ from the defaults', () => {
        mount({hasChanges: false, hasNonDefaults: true});

        expect(actionTitles()).toEqual(['common.resetAll']);
    });

    it('offers all three when there are both unsaved changes and non-defaults', () => {
        mount({hasChanges: true, hasNonDefaults: true});

        expect(actionTitles()).toEqual(['common.saveAll', 'common.undoAll', 'common.resetAll']);
    });

    it('withdraws save, undo and reset while the section is locked', () => {
        // The one combination that matters and that an E2E cannot easily reach:
        // a lock applied while edits are pending. Everything that could write is
        // taken away and only the lock toggle remains — so the pending changes
        // are unreachable until the lock comes off, rather than silently saved.
        mount({hasChanges: true, hasNonDefaults: true, isLocked: true, showLock: true});

        expect(actionTitles()).toEqual(['settings.unlock']);
    });

    it('shows nothing at all when locked without the lock button', () => {
        // `showLock: false` with `isLocked: true` is a parent bug rather than a
        // user state, but the layout must not render an empty action bar for it.
        mount({hasChanges: true, hasNonDefaults: true, isLocked: true, showLock: false});

        expect(actionTitles()).toEqual([]);
    });

    it('names the action, not the state: unlocked offers Lock', () => {
        mount({showLock: true, isLocked: false});

        expect(actionTitles()).toEqual(['settings.lock']);
    });

    it('names the action, not the state: locked offers Unlock', () => {
        mount({showLock: true, isLocked: true});

        expect(actionTitles()).toEqual(['settings.unlock']);
    });

    it('keeps the lock button beside the others when unlocked', () => {
        mount({hasChanges: true, hasNonDefaults: true, showLock: true, isLocked: false});

        expect(actionTitles()).toEqual(['common.saveAll', 'common.undoAll', 'common.resetAll', 'settings.lock']);
    });

    it('disables save all while a write is running', () => {
        mount({hasChanges: true, isSaving: true});

        expect(screen.getByTitle('common.saveAll')).toBeDisabled();
    });
});

describe('SettingsLayout — what the actions report', () => {
    it.each([
        ['common.saveAll', 'saveAll'],
        ['common.undoAll', 'undoAll'],
        ['common.resetAll', 'resetAll'],
    ])('reports %s', async (title, event) => {
        const mounted = mount({hasChanges: true, hasNonDefaults: true});

        await fireEvent.click(screen.getByTitle(title));

        expect(mounted[event as 'saveAll' | 'undoAll' | 'resetAll']).toHaveBeenCalledTimes(1);
    });

    it('reports a request to lock', async () => {
        const {toggleLock} = mount({showLock: true, isLocked: false});

        await fireEvent.click(screen.getByTitle('settings.lock'));

        expect(toggleLock).toHaveBeenCalledTimes(1);
    });

    it('reports a request to unlock', async () => {
        const {toggleLock} = mount({showLock: true, isLocked: true});

        await fireEvent.click(screen.getByTitle('settings.unlock'));

        expect(toggleLock).toHaveBeenCalledTimes(1);
    });
});

describe('SettingsLayout — the header', () => {
    it('shows the title it was given', () => {
        // A caller-supplied string, not a catalogue entry: the test passed it in.
        mount({title: 'Global settings'});

        expect(screen.getByRole('heading', {name: 'Global settings'})).toBeInTheDocument();
    });

    it('shows a description when there is one', () => {
        mount({description: 'What these settings do'});

        expect(screen.getByText('What these settings do')).toBeInTheDocument();
    });

    it('renders no description paragraph when there is none', () => {
        const {container} = mount({description: ''});

        expect(container.querySelectorAll('p')).toHaveLength(0);
    });
});
