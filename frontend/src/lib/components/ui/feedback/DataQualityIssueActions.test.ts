// @vitest-environment jsdom
/**
 * DataQualityIssueActions — every action of an issue is a chip Button (85 BTN-2d).
 *
 * `variant="chip"` at `xs`, in the row's tone: the `tone` it is given, else the one of the issue's severity (error →
 * danger, warning → warning, info → info). The one button of a category is busy while its action runs (`aria-busy`, the
 * click dropped) and only for its own code. An asset's chip cuts a long name and shows it whole; a pair's chip says the
 * action and the pair in its name, whatever its word draws. The component opens nothing: it tells `onaction`.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import {_} from '$lib/i18n';
import {buttonClasses, type ButtonTone} from '$lib/components/ui/button/buttonClasses';
import {formatPairSlugPlain} from '$lib/utils/currency/currencyFormat';
import type {DataQualityIssue} from './DataQualityBanner.svelte';
import DataQualityIssueActions from './DataQualityIssueActions.svelte';
import {ctaLabel} from './dataQualityCta';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

const SYNC: DataQualityIssue = {domain: 'portfolio', code: 'STALE_PRICE', severity: 'warning', message_i18n_key: 'dataQuality.stalePrice', cta_action: 'sync_asset_prices'};
const ASSETS: DataQualityIssue = {...SYNC, code: 'MISSING_PRICE', severity: 'error', cta_action: 'navigate_asset', affected_asset_ids: [301, 302], affected_asset_names: ['Delisted fund', 'Unlisted bond']};
const PAIRS: DataQualityIssue = {...SYNC, code: 'MISSING_FX', cta_action: 'add_fx_pair', affected_fx_pairs: ['EUR-USD']};

const chip = (tone: ButtonTone, extra: Record<string, unknown> = {}) => buttonClasses({variant: 'chip', tone, size: 'xs', ...extra});
const name = (action: string) => ctaLabel((key) => get(_)(key), action);

describe('DataQualityIssueActions — the chips (85 BTN-2d)', () => {
    it.each([
        ['error', 'danger'],
        ['warning', 'warning'],
        ['info', 'info'],
    ] as const)('severity %s draws the %s chip', (severity, tone) => {
        render(DataQualityIssueActions, {props: {issue: {...SYNC, severity}, placement: 'head'}});
        expect(screen.getByTestId('data-quality-cta-STALE_PRICE').className).toBe(chip(tone));
    });

    it('the tone it is given wins over the issue’s severity', () => {
        render(DataQualityIssueActions, {props: {issue: {...SYNC, severity: 'info'}, placement: 'head', tone: 'danger'}});
        expect(screen.getByTestId('data-quality-cta-STALE_PRICE').className).toBe(chip('danger'));
    });

    it('the button of a running action is busy and its click dropped; another code’s action leaves it live', async () => {
        const onaction = vi.fn();
        const view = render(DataQualityIssueActions, {props: {issue: SYNC, placement: 'head', onaction, busyCode: 'STALE_PRICE'}});
        const button = screen.getByTestId('data-quality-cta-STALE_PRICE');
        expect(button).toHaveAttribute('aria-busy', 'true');
        expect(button).toBeDisabled();
        expect(button.hasAttribute('disabled'), 'busy is never the native attribute').toBe(false);
        await fireEvent.click(button);
        expect(onaction).not.toHaveBeenCalled();

        await view.rerender({issue: SYNC, placement: 'head', onaction, busyCode: 'ANOTHER_CODE'});
        expect(button).not.toHaveAttribute('aria-busy');
        await fireEvent.click(button);
        expect(onaction).toHaveBeenCalledTimes(1);
        expect(onaction.mock.calls[0][0]).toBe('sync_asset_prices');
        expect(onaction.mock.calls[0][2]).toMatchObject({code: 'STALE_PRICE'});
    });

    it('an asset’s chip carries the asset’s name, cuts, and goes to its own asset', async () => {
        const onaction = vi.fn();
        render(DataQualityIssueActions, {props: {issue: ASSETS, placement: 'items', onaction}});
        const asset = screen.getByTestId('data-quality-nav-asset-302');
        expect(asset).toHaveTextContent('Unlisted bond');
        expect(asset.className).toBe(`${chip('danger', {truncate: true})} max-w-[16rem]`);
        expect(asset.querySelector('[data-lf-word]')?.classList.contains('truncate')).toBe(true);
        expect(asset.hasAttribute('title')).toBe(false);
        await fireEvent.click(asset);
        expect(onaction).toHaveBeenCalledTimes(1);
        expect(onaction.mock.calls[0].slice(0, 2)).toEqual(['navigate_asset', '302']);
    });

    it('a pair’s chip says the action and the pair in its name, and acts on its pair', async () => {
        const onaction = vi.fn();
        render(DataQualityIssueActions, {props: {issue: PAIRS, placement: 'items', onaction}});
        const pair = screen.getByTestId('data-quality-fx-pair-EUR-USD');
        expect(pair).toHaveAttribute('aria-label', `${name('add_fx_pair')}: ${formatPairSlugPlain('EUR-USD')}`);
        expect(pair.hasAttribute('title')).toBe(false);
        await fireEvent.click(pair);
        expect(onaction).toHaveBeenCalledTimes(1);
        expect(onaction.mock.calls[0].slice(0, 2)).toEqual(['add_fx_pair', 'EUR-USD']);
    });

    it('each half draws only its own shape', () => {
        render(DataQualityIssueActions, {props: {issue: SYNC, placement: 'items'}});
        expect(screen.queryByTestId('data-quality-cta-STALE_PRICE')).toBeNull();
        cleanup();
        render(DataQualityIssueActions, {props: {issue: ASSETS, placement: 'head'}});
        expect(screen.queryByTestId('data-quality-nav-assets-MISSING_PRICE')).toBeNull();
        expect(screen.queryByTestId('data-quality-cta-MISSING_PRICE')).toBeNull();
    });
});
