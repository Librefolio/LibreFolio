// @vitest-environment jsdom
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import LineShapePicker from './LineShapePicker.svelte';

beforeAll(async () => {
    await setupI18n();
});

describe('LineShapePicker (Y2 FB-3)', () => {
    it('offers the three shapes and marks the one in force', () => {
        render(LineShapePicker, {value: 'steps', onchange: vi.fn()});
        expect(screen.getByTestId('line-shape')).toHaveAttribute('data-value', 'steps');
        expect(screen.getByTestId('line-shape-segments')).toHaveAttribute('aria-pressed', 'false');
        expect(screen.getByTestId('line-shape-steps')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('line-shape-spline')).toHaveAttribute('aria-pressed', 'false');
    });

    it('is controlled: a click calls onchange with the shape and does not move the mark itself', async () => {
        const onchange = vi.fn();
        render(LineShapePicker, {value: 'segments', onchange});
        await fireEvent.click(screen.getByTestId('line-shape-spline'));
        expect(onchange).toHaveBeenCalledExactlyOnceWith('spline');
        expect(screen.getByTestId('line-shape-segments')).toHaveAttribute('aria-pressed', 'true');
    });

    it('takes a test id prefix of the page that uses it', () => {
        render(LineShapePicker, {value: 'segments', onchange: vi.fn(), testIdPrefix: 'preference-line-shape-picker'});
        expect(screen.getByTestId('preference-line-shape-picker-steps')).toBeInTheDocument();
    });

    it('does not answer a click when disabled', async () => {
        const onchange = vi.fn();
        render(LineShapePicker, {value: 'segments', onchange, disabled: true});
        await fireEvent.click(screen.getByTestId('line-shape-steps'));
        expect(onchange).not.toHaveBeenCalled();
    });
});
