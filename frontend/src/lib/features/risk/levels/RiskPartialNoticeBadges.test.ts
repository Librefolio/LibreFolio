// @vitest-environment jsdom
/**
 * RiskPartialNotice — the excluded assets as badges, with one short sentence for the cause (B6, V1 of A; Vitest + jsdom).
 *
 * Developer's decision of 29/09/2026, asked again on 31/10/2026 (D-B6b): a reason that excludes assets says its cause once, in a
 * short sentence that keeps the count («2 assets excluded: …»), and the assets themselves are badges — an `AssetChip` in its
 * `excluded` variant, icon and struck-through name — not a list of names inside the sentence.
 *
 * Pinned, on test ids and data attributes; the sentences are resolved from the shipped catalogue through the same `$_`:
 *
 * - an exclusion reason the notice knows, with the assets the warning named, reads its short sentence with the count of
 *   those assets and shows one excluded badge per asset, in the warning's order;
 * - the backend's long sentence is not shown beside them (it would name the assets twice);
 * - a reason without assets (merged warnings that disagreed and lost them), a cause the notice has no short sentence for, and
 *   a warning that is not an exclusion all keep the backend's own sentence, whole, and no badge: nothing is ever dropped;
 * - an asset the cache does not know is a badge named by its id, never an empty pill;
 * - each short sentence ships in the four catalogues.
 */
import {beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';

import {render, screen, setupI18n, within} from '$test/component';
import {_} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';

import type {ResultReason} from './levelHelpers';
import RiskPartialNotice from './RiskPartialNotice.svelte';

const CATALOGUES = {en, it: itCatalogue, fr, es};
const SHORT_REASONS = ['missing_price', 'missing_fx', 'invalid_currency', 'insufficient_history', 'no_price_source'] as const;
const shortKey = (reason: string) => `risk.levels.notice.excluded.${reason}`;

const LONG = 'Synthetic backend sentence: 2 assets excluded from the calculation, no market prices — Invented A, Invented B.';
const EXCLUSION: ResultReason = {key: `assets_excluded:${LONG}`, message: LONG, occurrences: 1, reason: 'missing_price', assetIds: [41, 42]};

beforeAll(async () => {
    await setupI18n('en');
});

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

function leaf(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

function mountNotice(reasons: ResultReason[]) {
    return render(RiskPartialNotice, {props: {partial: [], reasons}});
}

const badges = () => screen.queryAllByTestId('risk-partial-reason-asset');

describe('RiskPartialNotice — excluded assets as badges (B6)', () => {
    it('reads the short sentence with the count, and one excluded badge per asset in the warning order', () => {
        mountNotice([EXCLUSION]);

        const [line] = screen.getAllByTestId('risk-partial-reason');
        expect(normalize(line.textContent)).toContain(normalize(get(_)(shortKey('missing_price'), {values: {count: 2}})));
        expect(badges().map((badge) => badge.getAttribute('data-asset-id'))).toEqual(['41', '42']);
        for (const badge of badges()) expect(badge.getAttribute('data-variant')).toBe('excluded');
    });

    it("does not repeat the backend's long sentence, which names the assets a second time", () => {
        mountNotice([EXCLUSION]);

        expect(normalize(screen.getByTestId('risk-partial-reasons').textContent)).not.toContain(LONG);
    });

    it('names an asset the cache does not know by its id, never an empty pill', () => {
        mountNotice([EXCLUSION]);

        expect(normalize(within(badges()[0]).getByText(/./).textContent)).toBe('#41');
    });

    it.each([
        ['merged warnings that lost their assets', {...EXCLUSION, assetIds: undefined}],
        ['no asset named', {...EXCLUSION, assetIds: []}],
        ['a cause the notice has no short sentence for', {...EXCLUSION, reason: 'a_cause_nobody_wrote'}],
        ['no stated cause', {...EXCLUSION, reason: undefined}],
        ['a warning that is not an exclusion', {...EXCLUSION, key: `historical_replay_excluded_no_prices:${LONG}`}],
    ] as Array<[string, ResultReason]>)('keeps the backend sentence whole and shows no badge: %s', (_name, reason) => {
        mountNotice([reason]);

        expect(normalize(screen.getByTestId('risk-partial-reason').textContent)).toContain(LONG);
        expect(badges()).toHaveLength(0);
    });

    it.each(SHORT_REASONS)('ships the short sentence of %s in all four catalogues, with its count', (reason) => {
        for (const [language, catalogue] of Object.entries(CATALOGUES)) {
            const sentence = leaf(catalogue, shortKey(reason));
            expect(typeof sentence, `${shortKey(reason)} is missing in ${language}`).toBe('string');
            expect(sentence as string, `${shortKey(reason)} in ${language} does not carry the count`).toContain('{count');
        }
    });
});
