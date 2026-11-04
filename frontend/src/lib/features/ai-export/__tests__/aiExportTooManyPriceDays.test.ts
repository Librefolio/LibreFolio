/**
 * @vitest-environment node
 *
 * J-50 — an AI Export refused because its prices would build too many per-day points says so, with a sentence of its own.
 *
 * Z-25 (N77) caps how many per-day price points one bulk request may build (`MAX_BULK_ITEM_DAYS`). An AI Export whose
 * selection needs a price load over that budget — the market snapshot of its period, or a technical load with its
 * signals' warm-up — is answered by the backend (J-50) 422 `selection_not_applicable`, `reason_code: 'too_many_price_days'`.
 * Until J-50 it was a 503 `snapshot_source_failure`, worded «a source is unavailable, try again later», for a request that
 * fails the same way every time.
 *
 * `getAiExportErrorMessage` (`../ui.ts`, `problemMessage`) words that refusal with `aiExport.tooManyPriceDays`, whatever
 * the selection's applicability code; any other reason keeps the generic `aiExport.selectionNotApplicable` (GUARD, green
 * today and after). Keys are asserted through a translate stub that returns them, never a translation; the catalogue case
 * checks only that the key is a sentence of its own, in each of the four catalogues.
 */
import {describe, expect, it} from 'vitest';

import {SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import {AiExportProblemError} from '../aiExportClient';
import {getAiExportErrorMessage, type AiExportTranslate} from '../ui';

const TOO_MANY_PRICE_DAYS_KEY = 'aiExport.tooManyPriceDays';
const NOT_APPLICABLE_KEY = 'aiExport.selectionNotApplicable';

/** A translate stub: every key comes back as itself, so the key chosen is what the case reads. */
const t: AiExportTranslate = (key) => key;

/** The 422 `selection_not_applicable` of an asset selection, as the client raises it. */
function notApplicable(reasonCode: string, selection: {kind: 'dataset' | 'analysis'; id: string; applicabilityCode: string}): AiExportProblemError {
    return new AiExportProblemError(
        422,
        {
            code: 'selection_not_applicable',
            message: 'Not applicable',
            domain: 'asset',
            selection_kind: selection.kind,
            selection_id: selection.id,
            detail_level: 'standard',
            applicability_code: selection.applicabilityCode,
            reason_code: reasonCode,
        },
        null,
    );
}

const MARKET_HISTORY = {kind: 'dataset', id: 'asset.market_history', applicabilityCode: 'always_applicable'} as const;
const POSITION_REVIEW = {kind: 'analysis', id: 'asset.position_review', applicabilityCode: 'requires_position'} as const;

describe('getAiExportErrorMessage — a selection refused for too many price days', () => {
    it.each([MARKET_HISTORY, POSITION_REVIEW])('words too_many_price_days with aiExport.tooManyPriceDays for the $kind $id', (selection) => {
        expect(getAiExportErrorMessage(t, notApplicable('too_many_price_days', selection))).toBe(TOO_MANY_PRICE_DAYS_KEY);
    });

    // GUARD: the reasons the backend gave before J-50, and one it may add later, keep the generic sentence.
    it.each(['no_position', 'no_direct_exposure', 'insufficient_price_history', 'unsupported_detail_level', 'a_reason_added_later'])('keeps aiExport.selectionNotApplicable for the reason %s', (reasonCode) => {
        expect(getAiExportErrorMessage(t, notApplicable(reasonCode, POSITION_REVIEW))).toBe(NOT_APPLICABLE_KEY);
    });
});

describe('the catalogues word a refusal for too many price days', () => {
    /** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
    const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

    /** The leaf behind a dotted key in one catalogue. */
    function leaf(catalogue: unknown, key: string): unknown {
        return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    }

    it.each([...SUPPORTED_LOCALES])('%s.json has a sentence of its own for aiExport.tooManyPriceDays, not the generic one', (locale) => {
        const catalogue = CATALOGUES[locale];
        const generic = leaf(catalogue, NOT_APPLICABLE_KEY);
        // Positive control: the generic sentence lives beside it, so a red below is a missing sentence, not a wrong place.
        expect(typeof generic, `${NOT_APPLICABLE_KEY} is not a sentence in ${locale}.json: this case reads the wrong place`).toBe('string');
        const sentence = leaf(catalogue, TOO_MANY_PRICE_DAYS_KEY);
        expect(typeof sentence === 'string' && sentence.trim() !== '', `${locale}.json has no ${TOO_MANY_PRICE_DAYS_KEY}`).toBe(true);
        expect(sentence, `${TOO_MANY_PRICE_DAYS_KEY} reads like ${NOT_APPLICABLE_KEY} in ${locale}.json: the user is still not told what to change`).not.toBe(generic);
    });
});
