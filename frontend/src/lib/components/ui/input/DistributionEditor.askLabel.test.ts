// @vitest-environment jsdom
/**
 * DistributionEditor — the label of its «ask» button (plan 68, E10c3).
 *
 * The editor asks a price provider in the asset window («Chiedi al Provider»); in the profile window it asks the
 * enrichers, which are not price providers. A caller may name the button (`askLabel`): it is the button's text and its
 * title. Without one, the editor keeps «Chiedi al Provider».
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {cleanup, render, screen, setupI18n} from '$test/component';
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
        expect(button).toHaveAttribute('title', 'Ask the source');
        expect(button).toHaveTextContent(/^Ask the source$/);
    });

    it('keeps «ask the provider» without a name', () => {
        render(DistributionEditor, {kind: 'geographic', value: {}, hasProvider: true, onAskProvider: vi.fn()});
        expect(screen.getByTestId('distribution-ask-provider-geographic')).toHaveAttribute('title', get(_)('assets.identifiers.askProvider'));
    });
});
