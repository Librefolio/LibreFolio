// @vitest-environment jsdom
/**
 * AssetModalProfileRow (plan 68, E8b): the «Dati del profilo» row of the asset window, which opens the profile window
 * over it.
 *
 * Pinned (the mock «finestra-asset-profilo»):
 * - the row publishes how many changes wait (`data-count`) and shows the badge only when one does;
 * - it names the voices waiting, in the order it is given;
 * - a click, and Enter or Space on the focused row, open the profile window; with `disabled` (the tour's preview) it
 *   opens nothing.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {fireEvent, render, screen, setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import AssetModalProfileRow from './AssetModalProfileRow.svelte';

describe('AssetModalProfileRow', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    it('says how many changes wait and names their voices, in order', () => {
        render(AssetModalProfileRow, {props: {summary: {count: 2, keys: ['ter', 'fund_domicile']}, onopen: vi.fn()}});
        const row = screen.getByTestId('asset-modal-profile-row');
        expect(row).toHaveAttribute('data-count', '2');
        expect(screen.getByTestId('asset-modal-profile-pending')).toBeInTheDocument();
        const names = screen.getByTestId('asset-modal-profile-voices').textContent ?? '';
        const ter = get(_)('assets.profile.voices.ter');
        const domicile = get(_)('assets.profile.voices.fund_domicile');
        expect(names.indexOf(ter)).toBeGreaterThanOrEqual(0);
        expect(names.indexOf(ter)).toBeLessThan(names.indexOf(domicile));
    });

    it('has no badge and no names when nothing waits', () => {
        render(AssetModalProfileRow, {props: {summary: {count: 0, keys: []}, onopen: vi.fn()}});
        expect(screen.getByTestId('asset-modal-profile-row')).toHaveAttribute('data-count', '0');
        expect(screen.queryByTestId('asset-modal-profile-pending')).toBeNull();
        expect(screen.queryByTestId('asset-modal-profile-voices')).toBeNull();
    });

    it('opens the profile window on a click, on Enter and on Space', async () => {
        const onopen = vi.fn();
        render(AssetModalProfileRow, {props: {summary: {count: 0, keys: []}, onopen}});
        const row = screen.getByTestId('asset-modal-profile-row');
        await fireEvent.click(row);
        await fireEvent.keyDown(row, {key: 'Enter'});
        await fireEvent.keyDown(row, {key: ' '});
        expect(onopen).toHaveBeenCalledTimes(3);
    });

    it('opens nothing when disabled', async () => {
        const onopen = vi.fn();
        render(AssetModalProfileRow, {props: {summary: {count: 1, keys: ['ter']}, onopen, disabled: true}});
        const row = screen.getByTestId('asset-modal-profile-row');
        expect(row).toHaveAttribute('aria-disabled', 'true');
        await fireEvent.click(row);
        expect(onopen).not.toHaveBeenCalled();
    });
});
