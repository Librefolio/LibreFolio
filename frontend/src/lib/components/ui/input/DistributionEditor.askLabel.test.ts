// @vitest-environment jsdom
/**
 * DistributionEditor — the label of its «ask» button (plan 68, E10c3).
 *
 * The editor asks a price provider in the asset window («Chiedi al Provider»); in the profile window it asks the
 * enrichers, which are not price providers. A caller may name the button (`askLabel`): it is the button's word and its
 * name. Without one, the editor keeps «Chiedi al Provider». Since 85 BTN-2d it is a standard Button: no native title,
 * and with no source to ask it is off with its reason (D5), reachable, its click dropped.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import DistributionEditor from './DistributionEditor.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

describe('DistributionEditor — the ask button', () => {
    it('says what the caller names it', () => {
        render(DistributionEditor, {kind: 'sector', value: {}, hasProvider: true, onAskProvider: vi.fn(), askLabel: 'Ask the source'});
        const button = screen.getByTestId('distribution-ask-provider-sector');
        expect(button).toHaveAttribute('aria-label', 'Ask the source');
        expect(button.hasAttribute('title')).toBe(false);
        expect(button).toHaveTextContent(/^Ask the source$/);
    });

    it('keeps «ask the provider» without a name', () => {
        render(DistributionEditor, {kind: 'geographic', value: {}, hasProvider: true, onAskProvider: vi.fn()});
        expect(screen.getByTestId('distribution-ask-provider-geographic')).toHaveAttribute('aria-label', get(_)('assets.identifiers.askProvider'));
    });

    it('with no source to ask it is off with its reason: reachable, its click dropped, the reason shown', async () => {
        const onAskProvider = vi.fn();
        render(DistributionEditor, {kind: 'sector', value: {}, hasProvider: false, onAskProvider});
        const button = screen.getByTestId('distribution-ask-provider-sector');
        expect(button).toHaveAttribute('aria-disabled', 'true');
        expect(button).toHaveAttribute('data-disabled-reason', 'no-source');
        expect(button.hasAttribute('disabled')).toBe(false);
        await fireEvent.click(button);
        expect(onAskProvider).not.toHaveBeenCalled();
        const reason = get(_)('assets.distribution.askNoSource');
        expect(reason, 'the reason is in the catalogue').not.toBe('assets.distribution.askNoSource');
        expect(screen.getByRole('tooltip')).toHaveTextContent(reason);
    });

    it('with a source it asks on a click, and is busy while asking', async () => {
        const onAskProvider = vi.fn();
        const view = render(DistributionEditor, {kind: 'sector', value: {}, hasProvider: true, onAskProvider});
        await fireEvent.click(screen.getByTestId('distribution-ask-provider-sector'));
        expect(onAskProvider).toHaveBeenCalledTimes(1);
        await view.rerender({kind: 'sector', value: {}, hasProvider: true, onAskProvider, askingProvider: true});
        expect(screen.getByTestId('distribution-ask-provider-sector')).toHaveAttribute('aria-busy', 'true');
        await fireEvent.click(screen.getByTestId('distribution-ask-provider-sector'));
        expect(onAskProvider, 'nothing starts twice').toHaveBeenCalledTimes(1);
    });
});
