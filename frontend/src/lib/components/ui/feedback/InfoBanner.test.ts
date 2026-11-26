// @vitest-environment jsdom
/**
 * InfoBanner — its ✕ is the standard CloseButton (85 BTN-2d).
 *
 * `info-banner-dismiss`, drawn only when the banner may be dismissed and somebody listens; on the tint of the banner's
 * own state (an error is danger); named `common.close` in the interface's language — until then «Dismiss», English
 * written in the component; a click tells the caller, and the banner itself stays until the caller drops it.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {buttonClasses} from '$lib/components/ui/button/buttonClasses';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import InfoBanner from './InfoBanner.svelte';

beforeAll(async () => {
    await setupI18n();
});

const TINTS = [
    ['warning', 'warning'],
    ['info', 'info'],
    ['error', 'danger'],
    ['success', 'success'],
] as const;

describe('InfoBanner — the ✕ (85 BTN-2d)', () => {
    it.each(TINTS)('a %s banner: the ✕ stands on the %s tint, and a click tells the caller', async (variant, tint) => {
        const ondismiss = vi.fn();
        render(InfoBanner, {props: {variant, message: 'probe message', dismissible: true, ondismiss}});
        const dismiss = within(screen.getByTestId(`info-banner-${variant}`)).getByTestId('info-banner-dismiss');
        expect(dismiss.className).toBe(buttonClasses({variant: 'ghost', size: 'xs', shape: 'icon', tint}));
        await fireEvent.click(dismiss);
        expect(ondismiss).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId(`info-banner-${variant}`), 'the caller drops it, not the ✕').toBeInTheDocument();
    });

    it('is named common.close in the interface’s language, never the English «Dismiss» of before', async () => {
        expect(itCatalogue.common.close, 'premise: the two languages differ').not.toBe(en.common.close);
        await setupI18n('it');
        try {
            render(InfoBanner, {props: {message: 'probe message', dismissible: true, ondismiss: vi.fn()}});
            const dismiss = screen.getByTestId('info-banner-dismiss');
            expect(dismiss).toHaveAttribute('aria-label', itCatalogue.common.close);
            expect(dismiss.hasAttribute('title')).toBe(false);
        } finally {
            cleanup();
            await setupI18n('en');
        }
    });

    it('is not drawn when the banner may not be dismissed, or nobody listens', () => {
        render(InfoBanner, {props: {message: 'probe message', ondismiss: vi.fn()}});
        expect(screen.getByTestId('info-banner-info'), 'barrier: the banner is drawn').toBeInTheDocument();
        expect(screen.queryByTestId('info-banner-dismiss')).toBeNull();
        cleanup();
        render(InfoBanner, {props: {message: 'probe message', dismissible: true}});
        expect(screen.getByTestId('info-banner-info')).toBeInTheDocument();
        expect(screen.queryByTestId('info-banner-dismiss')).toBeNull();
    });
});
