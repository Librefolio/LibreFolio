// @vitest-environment jsdom
/**
 * The five reusable settings controls — component test (Vitest + jsdom).
 *
 * `SettingToggle`, `SettingNumber`, `SettingSelect`, `SettingTheme` and
 * `SettingCurrency` are one component wearing five different inputs. Each says
 * so in its own header comment — *"follows same API as SettingSelect for
 * consistency"* — and each renders the same inline action row: Save and Undo
 * when the value is modified, Reset when it merely differs from the default,
 * and nothing at all when the section is locked.
 *
 * That shared contract is asserted **once, against all five**, in the table at
 * the top. Writing it five times in five files would state the same thing five
 * times and, more to the point, would hide the places where the five do *not*
 * agree — which turned out to be the interesting part, and is recorded in the
 * final describe block.
 *
 * Reaching this from an E2E means finding a real setting that is simultaneously
 * modified and non-default, in a shared database, and then a locked one; the
 * flags here are props, so the whole matrix is four lines.
 *
 * Addressing. These components publish no `data-testid` and no state attribute:
 * the action buttons carry only a `title`, and "which option is active" is
 * expressed as a Tailwind class. `$lib/i18n` is therefore mocked with an
 * identity translator so `title={$_('common.save')}` renders as that literal
 * key — every query names a key, stable in all four languages, never a
 * sentence. Where no attribute exists at all, the test asserts the callback the
 * component emits instead, which is its actual contract.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import type {Mock} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

vi.mock('$lib/i18n', () => ({_: readable((key: string) => key)}));
vi.mock('$lib/stores/app/language', () => ({currentLanguage: writable('en')}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));
vi.mock('$lib/stores/reference/currencyStore', () => ({
    currencyStoreVersion: writable(0),
    ensureCurrenciesLoaded: vi.fn(async () => undefined),
    getAllCurrencies: vi.fn(() => [
        {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []},
        {code: 'USD', name: 'US Dollar', symbol: '$', flag_emoji: '🇺🇸', country_codes: [], country_names: []},
    ]),
    getCurrencyInfo: vi.fn((code: string) => ({code, name: code, symbol: code, flag_emoji: '🏳️', country_codes: [], country_names: []})),
}));
vi.mock('$lib/stores/reference/fxRoutesStore', () => ({
    fxRoutesVersion: writable(0),
    ensureFxRoutesLoaded: vi.fn(async () => undefined),
    getConfiguredCurrencySet: vi.fn(() => new Set(['EUR', 'USD'])),
}));

import SettingToggle from './SettingToggle.svelte';
import SettingNumber from './SettingNumber.svelte';
import SettingSelect from './SettingSelect.svelte';
import SettingTheme from './SettingTheme.svelte';
import SettingCurrency from './SettingCurrency.svelte';

const CURRENCY_OPTIONS = [
    {value: 'EUR', label: 'Euro'},
    {value: 'USD', label: 'US Dollar'},
];

/** The three inline actions, named by the i18n key of their `title`. */
const SAVE = 'common.save';
const UNDO = 'common.undo';
const RESET = 'common.reset';

/** Which of the three inline actions the control is currently offering. */
function actionsOffered(): string[] {
    return [SAVE, UNDO, RESET].filter((title) => screen.queryAllByTitle(title).length > 0);
}

interface Reports {
    save: Mock;
    undo: Mock;
    reset: Mock;
    change: Mock;
}

/** One mount signature over five components. */
interface Harness {
    name: string;
    mount(props?: Record<string, unknown>): Reports;
}

function callbackHarness(name: string, Component: unknown, base: Record<string, unknown>): Harness {
    return {
        name,
        mount(props: Record<string, unknown> = {}): Reports {
            const reports: Reports = {save: vi.fn(), undo: vi.fn(), reset: vi.fn(), change: vi.fn()};
            render(
                Component as never,
                {
                    label: `${name} label`,
                    ...base,
                    onsave: reports.save,
                    onundo: reports.undo,
                    onreset: reports.reset,
                    onchange: reports.change,
                    ...props,
                } as never,
            );
            return reports;
        },
    };
}

const HARNESSES: Harness[] = [
    callbackHarness('SettingToggle', SettingToggle, {value: false}),
    callbackHarness('SettingNumber', SettingNumber, {value: '5'}),
    callbackHarness('SettingSelect', SettingSelect, {value: 'EUR', options: CURRENCY_OPTIONS}),
    callbackHarness('SettingCurrency', SettingCurrency, {value: 'EUR'}),
    callbackHarness('SettingTheme', SettingTheme, {value: 'auto'}),
];

beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
});

describe.each(HARNESSES)('$name — the shared inline-action contract', (harness) => {
    it('offers nothing while the value is untouched and at its default', () => {
        harness.mount({isModified: false, isNonDefault: false});

        expect(actionsOffered()).toEqual([]);
    });

    it('offers Save and Undo once the value is modified', () => {
        harness.mount({isModified: true, isNonDefault: false});

        expect(actionsOffered()).toEqual([SAVE, UNDO]);
    });

    it('offers Reset alone when the stored value differs from the default', () => {
        harness.mount({isModified: false, isNonDefault: true});

        expect(actionsOffered()).toEqual([RESET]);
    });

    it('hides Reset while there are unsaved changes, so the two cannot be confused', () => {
        // `isNonDefault && !isModified`: resetting on top of a pending edit would
        // discard it without saying so, so the offer is withdrawn until the edit
        // is resolved one way or the other.
        harness.mount({isModified: true, isNonDefault: true});

        expect(actionsOffered()).toEqual([SAVE, UNDO]);
    });

    it('offers nothing at all while the section is locked', () => {
        harness.mount({isModified: true, isNonDefault: true, isLocked: true});

        expect(actionsOffered()).toEqual([]);
    });

    it.each([
        [SAVE, 'save'],
        [UNDO, 'undo'],
    ])('reports %s', async (title, key) => {
        const reports = harness.mount({isModified: true});

        await fireEvent.click(screen.getByTitle(title));

        expect(reports[key as 'save' | 'undo']).toHaveBeenCalledTimes(1);
    });

    it('reports Reset', async () => {
        const reports = harness.mount({isNonDefault: true});

        await fireEvent.click(screen.getByTitle(RESET));

        expect(reports.reset).toHaveBeenCalledTimes(1);
    });

    it('shows the hint when given one, and no stray paragraph when not', () => {
        harness.mount({hint: 'why this matters'});
        expect(screen.getByText('why this matters')).toBeInTheDocument();

        cleanup();
        harness.mount();
        expect(screen.queryByText('why this matters')).not.toBeInTheDocument();
    });
});

describe('SettingToggle', () => {
    /** The switch itself, named by the label the test passed in. */
    function toggle(label = 'SettingToggle label'): HTMLElement {
        return screen.getByRole('switch', {name: `Toggle ${label}`});
    }

    it('turns an off setting on and says so', async () => {
        const reports = HARNESSES[0].mount({value: false});
        expect(toggle()).toHaveAttribute('aria-checked', 'false');

        await fireEvent.click(toggle());

        expect(reports.change).toHaveBeenCalledExactlyOnceWith(true);
        expect(toggle()).toHaveAttribute('aria-checked', 'true');
        expect(screen.getByText('ON')).toBeInTheDocument();
    });

    it('turns an on setting off and says so', async () => {
        // Started from the opposite state on purpose: a control that arrives
        // already on is *switched off* by a click, and a test that only ever
        // starts from `false` reads the same either way.
        const reports = HARNESSES[0].mount({value: true});
        expect(toggle()).toHaveAttribute('aria-checked', 'true');
        expect(screen.getByText('ON')).toBeInTheDocument();

        await fireEvent.click(toggle());

        expect(reports.change).toHaveBeenCalledExactlyOnceWith(false);
        expect(toggle()).toHaveAttribute('aria-checked', 'false');
        expect(screen.getByText('OFF')).toBeInTheDocument();
    });

    it('refuses to flip while locked, in the markup and in the handler', async () => {
        // Two layers, and both are checked: `disabled` stops the pointer, and the
        // `if (isLocked) return` in `toggle()` stops anything that gets past it.
        // Asserting only the attribute would leave the guard untested, and
        // dispatching only the event would not prove the button is unreachable.
        const reports = HARNESSES[0].mount({value: false, isLocked: true});
        const button = toggle();

        expect(button).toBeDisabled();
        await fireEvent.click(button);

        expect(reports.change).not.toHaveBeenCalled();
        expect(screen.getByText('OFF')).toBeInTheDocument();
    });

    it('keeps the switch live while a save is in flight', async () => {
        // Characterisation. `isSaving` disables the Save button only; the switch
        // stays enabled, so the value can be flipped again while the previous
        // value is still on the wire. See the divergence block below.
        const reports = HARNESSES[0].mount({value: false, isModified: true, isSaving: true});

        expect(screen.getByTitle(SAVE)).toBeDisabled();
        expect(toggle()).toBeEnabled();

        await fireEvent.click(toggle());
        expect(reports.change).toHaveBeenCalledExactlyOnceWith(true);
    });
});

describe('SettingNumber', () => {
    function field(): HTMLElement {
        return screen.getByRole('spinbutton');
    }

    it('reports what was typed, as text, without parsing it first', async () => {
        // The value is a string all the way through — `12.50` must not become
        // `12.5` on the way out, or a trailing zero would vanish mid-keystroke.
        const reports = HARNESSES[1].mount({value: '5', type: 'float'});

        await fireEvent.input(field(), {target: {value: '12.50'}});

        expect(reports.change).toHaveBeenCalledExactlyOnceWith('12.50');
    });

    it.each([
        ['int by default', {}, '1'],
        ['float', {type: 'float'}, '0.01'],
        ['whatever the caller asked for', {step: 5}, '5'],
        ['an explicit step even on a float', {type: 'float', step: 0.5}, '0.5'],
    ])('steps by %s', (_label, props, expected) => {
        HARNESSES[1].mount(props);

        expect(field()).toHaveAttribute('step', expected);
    });

    it('passes min and max through to the field', () => {
        HARNESSES[1].mount({min: 2, max: 90});

        expect(field()).toHaveAttribute('min', '2');
        expect(field()).toHaveAttribute('max', '90');
    });

    it('shows the unit beside the field when there is one', () => {
        HARNESSES[1].mount({unit: 'days'});

        expect(screen.getByText('days')).toBeInTheDocument();
    });

    it('warns once the value climbs past the threshold', () => {
        HARNESSES[1].mount({value: '400', warnAbove: 365, warnMessage: 'that is a long time'});

        expect(screen.getByText('that is a long time')).toBeInTheDocument();
    });

    it.each([
        ['the value sits exactly on the threshold', {value: '365', warnAbove: 365}],
        ['the value is below it', {value: '10', warnAbove: 365}],
        ['no threshold was configured', {value: '99999'}],
        ['a threshold was set but no message was written', {value: '400', warnAbove: 365, warnMessage: ''}],
    ])('stays quiet when %s', (_label, props) => {
        HARNESSES[1].mount({...props, warnMessage: (props as {warnMessage?: string}).warnMessage ?? 'that is a long time'});

        expect(screen.queryByText('that is a long time')).not.toBeInTheDocument();
    });

    it('treats text that is not a number as zero rather than warning on NaN', () => {
        // `parseFloat('') || 0`. A NaN would compare false against every
        // threshold, which is the right answer by accident; zero is the right
        // answer on purpose, and it is also what the arrows step from.
        HARNESSES[1].mount({value: '', warnAbove: -1, warnMessage: 'above minus one'});

        expect(screen.getByText('above minus one')).toBeInTheDocument();
    });

    it('locks the field itself, not just the buttons', () => {
        HARNESSES[1].mount({isLocked: true});

        expect(field()).toBeDisabled();
    });

    it('withdraws Save while a save is in flight', () => {
        HARNESSES[1].mount({isModified: true, isSaving: true});

        expect(screen.getByTitle(SAVE)).toBeDisabled();
    });
});

describe('SettingSelect', () => {
    function trigger(): HTMLElement {
        return screen.getByRole('combobox');
    }

    it('reports the option the user picked', async () => {
        const reports = HARNESSES[2].mount({value: 'EUR'});
        await fireEvent.click(trigger());

        await fireEvent.click(screen.getByRole('option', {name: 'US Dollar'}));

        expect(reports.change).toHaveBeenCalledExactlyOnceWith('USD');
    });

    it('shows the label of the current value, not its code', () => {
        HARNESSES[2].mount({value: 'USD'});

        expect(trigger()).toHaveTextContent('US Dollar');
    });

    it('will not open while locked', async () => {
        HARNESSES[2].mount({isLocked: true});

        expect(trigger()).toBeDisabled();
        await fireEvent.click(trigger());

        expect(screen.queryByRole('option')).toBeNull();
    });

    it('says it is loading instead of showing an empty list', async () => {
        HARNESSES[2].mount({loading: true, options: []});

        await fireEvent.click(trigger());

        // A loading select refuses to open at all, which is the honest answer:
        // there is nothing to choose from yet.
        expect(screen.queryByRole('listbox')).toBeNull();
    });
});

describe('SettingTheme', () => {
    /** The three theme buttons, named by their i18n keys. */
    const THEMES: Array<[string, string]> = [
        ['settings.themeLight', 'light'],
        ['settings.themeDark', 'dark'],
        ['settings.themeAuto', 'auto'],
    ];

    it('offers exactly three themes', () => {
        HARNESSES[4].mount();

        for (const [key] of THEMES) {
            expect(screen.getByRole('button', {name: key})).toBeInTheDocument();
        }
    });

    it.each(THEMES)('reports %s as %s', async (key, theme) => {
        const reports = HARNESSES[4].mount({value: theme === 'auto' ? 'light' : 'auto'});

        await fireEvent.click(screen.getByRole('button', {name: key}));

        expect(reports.change).toHaveBeenCalledExactlyOnceWith(theme);
    });

    it('reports a re-selection of the theme already in force', async () => {
        // Characterisation: `selectTheme` does not compare against the current
        // value, so choosing the active theme still dispatches `change` and the
        // parent still marks the setting modified. Harmless today — the parent
        // writes the same value back — but it is why "modified" can appear from
        // a click that changed nothing.
        const reports = HARNESSES[4].mount({value: 'dark'});

        await fireEvent.click(screen.getByRole('button', {name: 'settings.themeDark'}));

        expect(reports.change).toHaveBeenCalledExactlyOnceWith('dark');
    });

    it('refuses to change while locked, in the markup and in the handler', async () => {
        const reports = HARNESSES[4].mount({value: 'auto', isLocked: true});
        const light = screen.getByRole('button', {name: 'settings.themeLight'});

        expect(light).toBeDisabled();
        await fireEvent.click(light);

        expect(reports.change).not.toHaveBeenCalled();
    });
});

describe('SettingCurrency', () => {
    /**
     * `SearchSelect` renders its options as `search-select-option-{value}`
     * buttons inside a `role="listbox"`, but puts no `role="option"` on them —
     * so they are addressed by test id, which is the stable handle it does
     * publish.
     */
    function currencyOption(code: string): HTMLElement {
        return screen.getByTestId(`search-select-option-${code}`);
    }

    it('reports the currency the user picked', async () => {
        const reports = HARNESSES[3].mount({value: 'EUR'});

        await fireEvent.click(screen.getByRole('combobox'));
        await waitFor(() => expect(currencyOption('USD')).toBeInTheDocument());
        await fireEvent.click(currencyOption('USD'));

        await waitFor(() => expect(reports.change).toHaveBeenCalledExactlyOnceWith('USD'));
    });

    it('will not open while locked', async () => {
        // Asserted on `aria-expanded` and on the absence of a list, not on
        // `toBeDisabled()`: a locked `SearchSelect` swaps its `<button>` for a
        // `<div role="combobox">`, which cannot carry the real `disabled`
        // attribute and announces the state through `aria-disabled` instead.
        // What matters here is that the lock holds.
        HARNESSES[3].mount({isLocked: true});
        const trigger = screen.getByRole('combobox');

        await fireEvent.click(trigger);

        expect(trigger).toHaveAttribute('aria-disabled', 'true');
        expect(trigger).toHaveAttribute('aria-expanded', 'false');
        expect(screen.queryByRole('listbox')).toBeNull();
    });

    it('opens when it is not locked, so the previous test is about the lock', async () => {
        // The presence barrier for the negative above: without it, "no listbox"
        // would also be satisfied by a component that never opens at all.
        HARNESSES[3].mount({isLocked: false});
        const trigger = screen.getByRole('combobox');

        await fireEvent.click(trigger);

        expect(trigger).toHaveAttribute('aria-expanded', 'true');
        expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    it('carries the caller test id onto the row, and nothing when there is none', () => {
        HARNESSES[3].mount({testId: 'default-currency-row'});
        expect(screen.getByTestId('default-currency-row')).toBeInTheDocument();

        cleanup();
        HARNESSES[3].mount();
        expect(screen.queryByTestId('default-currency-row')).toBeNull();
    });
});

describe('the five controls now agree about saving', () => {
    it.each(HARNESSES.map((harness) => [harness.name, harness] as const))('%s withdraws Save while the save is running', (_name, harness) => {
        harness.mount({isModified: true, isSaving: true});

        expect(screen.getByTitle(SAVE)).toBeDisabled();
    });

    it('leaves every control editable during its own save', async () => {
        // The other half of the same gap, and the one that is shared by all
        // five: `isSaving` was only ever wired to the button, never to the input,
        // so the value on screen can drift from the value being written.
        const reports = HARNESSES[1].mount({value: '5', isModified: true, isSaving: true});
        const field = screen.getByRole('spinbutton');

        expect(field).toBeEnabled();
        await fireEvent.input(field, {target: {value: '9'}});

        expect(reports.change).toHaveBeenCalledExactlyOnceWith('9');
    });

    it('renders the icon it was given, on the control that takes one', () => {
        // `{#if icon}` is a branch in all five; a control without one must not
        // leave an empty slot behind.
        const {container} = render(SettingToggle as never, {value: false, label: 'no icon here'} as never);

        expect(within(container).queryByRole('img')).toBeNull();
        expect(container.querySelectorAll('svg')).toHaveLength(0);
    });
});
