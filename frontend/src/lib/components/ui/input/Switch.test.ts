// @vitest-environment jsdom
/**
 * Switch — component test (Vitest + jsdom).
 *
 * The one on/off lever of the app: controlled (`checked` in, `onchange(next, event)` out), two sizes, and two ways of
 * telling assistive technology what it is (`role="switch"` + `aria-checked`, or `aria-pressed` on a plain button).
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '$test/component';
import Switch from './Switch.svelte';

afterEach(cleanup);

const lever = () => screen.getByTestId('sw');

describe('Switch', () => {
    it('is a role="switch" with aria-checked by default, and carries its test id and name', () => {
        render(Switch, {checked: false, testId: 'sw', label: 'Active'});

        expect(lever()).toHaveAttribute('role', 'switch');
        expect(lever()).toHaveAttribute('aria-checked', 'false');
        expect(lever()).not.toHaveAttribute('aria-pressed');
        expect(lever()).toHaveAttribute('type', 'button');
        expect(lever()).toHaveAccessibleName('Active');
    });

    it('draws the track and the knob with the roles of the switch, never a palette class', () => {
        const {unmount} = render(Switch, {checked: false, testId: 'sw'});
        expect(lever()).toHaveClass('bg-lf-switch-off');
        expect(lever().firstElementChild).toHaveClass('bg-lf-switch-knob-off', 'border-lf-input');
        unmount();

        render(Switch, {checked: true, testId: 'sw'});
        expect(lever()).toHaveClass('bg-lf-checked');
        expect(lever().firstElementChild).toHaveClass('bg-lf-switch-knob-on');
        expect(lever()).toHaveAttribute('aria-checked', 'true');
    });

    it.each(['sm', 'md'] as const)('%s: never shrinks beside a long label (86, A2)', (size) => {
        render(Switch, {checked: true, testId: 'sw', size});
        expect(lever()).toHaveClass('shrink-0');
    });

    it('has two sizes, and the knob sits at the other end when on', () => {
        const md = render(Switch, {checked: false, testId: 'sw'});
        expect(lever()).toHaveClass('h-6', 'w-11');
        expect(lever().firstElementChild).toHaveClass('translate-x-1');
        md.unmount();

        const mdOn = render(Switch, {checked: true, testId: 'sw'});
        expect(lever().firstElementChild).toHaveClass('translate-x-6');
        mdOn.unmount();

        const sm = render(Switch, {checked: false, testId: 'sw', size: 'sm'});
        expect(lever()).toHaveClass('h-5', 'w-9');
        expect(lever().firstElementChild).toHaveClass('translate-x-[3px]');
        sm.unmount();

        render(Switch, {checked: true, testId: 'sw', size: 'sm'});
        expect(lever().firstElementChild).toHaveClass('translate-x-[18px]');
    });

    it('semantics="pressed" keeps a plain toggle button: aria-pressed, no role, no aria-checked', () => {
        render(Switch, {checked: true, testId: 'sw', semantics: 'pressed', label: 'Toggle'});

        expect(lever()).toHaveAttribute('aria-pressed', 'true');
        expect(lever()).not.toHaveAttribute('role');
        expect(lever()).not.toHaveAttribute('aria-checked');
    });

    it('asks for the opposite state on a click, and does not change by itself', async () => {
        const onchange = vi.fn();
        render(Switch, {checked: false, testId: 'sw', onchange});

        await fireEvent.click(lever());

        expect(onchange).toHaveBeenCalledTimes(1);
        expect(onchange.mock.calls[0][0]).toBe(true);
        expect(onchange.mock.calls[0][1]).toBeInstanceOf(MouseEvent);
        expect(lever(), 'controlled: the caller decides').toHaveAttribute('aria-checked', 'false');
    });

    it('a disabled switch ignores the click and says so', async () => {
        const onchange = vi.fn();
        render(Switch, {checked: false, testId: 'sw', onchange, disabled: true});

        await fireEvent.click(lever());

        expect(lever()).toBeDisabled();
        expect(onchange).not.toHaveBeenCalled();
    });

    it('dims a disabled switch, unless the caller asks not to; it is clickable-looking only when enabled', () => {
        const dimmed = render(Switch, {checked: false, testId: 'sw', disabled: true});
        expect(lever()).toHaveClass('opacity-50', 'cursor-not-allowed');
        dimmed.unmount();

        const plain = render(Switch, {checked: false, testId: 'sw', disabled: true, dim: false});
        expect(lever()).not.toHaveClass('opacity-50');
        expect(lever()).toHaveClass('cursor-not-allowed');
        plain.unmount();

        render(Switch, {checked: false, testId: 'sw'});
        expect(lever()).toHaveClass('cursor-pointer');
        expect(lever()).not.toHaveClass('opacity-50');
    });

    it('hands the click event to the caller (to stop it) and passes the other attributes to the button', async () => {
        let seen: MouseEvent | undefined;
        const onchange = vi.fn((_next: boolean, event: MouseEvent) => {
            seen = event;
            event.stopPropagation();
        });
        render(Switch, {checked: false, testId: 'sw', onchange, 'data-key': 'k1', title: 'Keep'} as never);

        await fireEvent.click(lever());

        expect(onchange).toHaveBeenCalledTimes(1);
        expect(seen?.type).toBe('click');
        expect(lever()).toHaveAttribute('data-key', 'k1');
        expect(lever()).toHaveAttribute('title', 'Keep');
    });

    it('is named by a visible label through labelledby', () => {
        render(Switch, {checked: false, testId: 'sw', labelledby: 'lbl'});
        expect(lever()).toHaveAttribute('aria-labelledby', 'lbl');
    });
});
