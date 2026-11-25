/**
 * @vitest-environment node
 *
 * 78 L10b — a user who owns no broker: the refusal says why, and the prompt never suggests what the user cannot select.
 *
 * An export that names no broker reads the brokers the user owns (D13). A user who owns none has no position, exposure
 * or portfolio to read: the backend refuses those selections with 422 `selection_not_applicable`,
 * `reason_code: 'no_owned_brokers'`, and keeps the market-only ones. For a market-only analysis it lists the suggested
 * datasets the user cannot select (`unavailable_dataset_ids`): the «Additional LibreFolio Data» block leaves them out,
 * as it leaves out the datasets already included.
 *
 * Keys are asserted through a translate stub that returns them, never a translation; the catalogue case checks only that
 * the key is a sentence of its own, in each of the four catalogues.
 */
import {describe, expect, it} from 'vitest';

import {SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import {AiExportProblemError} from '../aiExportClient';
import type {AiExportCompatibleSelection, AiExportSnapshotResponse} from '../catalog/shared';
import {renderAiExportPromptDiagnostics} from '../templates/promptRenderer';
import {getAiExportErrorMessage, type AiExportTranslate} from '../ui';
import {compatibilityFixture, selectionFixture, snapshotFixture} from './runtimeFixtures';

const NO_OWNED_BROKERS_KEY = 'aiExport.noOwnedBrokers';
const NOT_APPLICABLE_KEY = 'aiExport.selectionNotApplicable';

/** A translate stub: every key comes back as itself, so the key chosen is what the case reads. */
const t: AiExportTranslate = (key) => key;

function notApplicable(reasonCode: string, domain: 'asset' | 'fx' | 'portfolio', selectionId: string): AiExportProblemError {
    return new AiExportProblemError(
        422,
        {
            code: 'selection_not_applicable',
            message: 'Not applicable',
            domain,
            selection_kind: 'dataset',
            selection_id: selectionId,
            detail_level: 'standard',
            applicability_code: 'always_applicable',
            reason_code: reasonCode,
        },
        null,
    );
}

describe('getAiExportErrorMessage — a user who owns no broker', () => {
    it.each([
        ['asset', 'asset.position_and_history'],
        ['fx', 'fx.market_and_exposure'],
        ['portfolio', 'portfolio.overview_and_history'],
    ] as const)('words no_owned_brokers with aiExport.noOwnedBrokers for %s %s', (domain, selectionId) => {
        expect(getAiExportErrorMessage(t, notApplicable('no_owned_brokers', domain, selectionId))).toBe(NO_OWNED_BROKERS_KEY);
    });

    // GUARD: the other reasons keep their own sentence.
    it('keeps the generic sentence for another reason, and its own for too many price days', () => {
        expect(getAiExportErrorMessage(t, notApplicable('no_position', 'asset', 'asset.position_and_history'))).toBe(NOT_APPLICABLE_KEY);
        expect(getAiExportErrorMessage(t, notApplicable('too_many_price_days', 'asset', 'asset.market_history'))).toBe('aiExport.tooManyPriceDays');
    });
});

describe('the catalogues word the refusal of a user who owns no broker', () => {
    const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

    function leaf(catalogue: unknown, key: string): unknown {
        return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    }

    it.each([...SUPPORTED_LOCALES])('%s.json has a sentence of its own for aiExport.noOwnedBrokers', (locale) => {
        const catalogue = CATALOGUES[locale];
        const generic = leaf(catalogue, NOT_APPLICABLE_KEY);
        expect(typeof generic, `${NOT_APPLICABLE_KEY} is not a sentence in ${locale}.json: this case reads the wrong place`).toBe('string');
        const sentence = leaf(catalogue, NO_OWNED_BROKERS_KEY);
        expect(typeof sentence === 'string' && sentence.trim() !== '', `${locale}.json has no ${NO_OWNED_BROKERS_KEY}`).toBe(true);
        expect(sentence).not.toBe(generic);
    });
});

describe('«Additional LibreFolio Data» leaves out the datasets the user cannot select', () => {
    /** The market-only analyses and the broker-reading dataset each one suggests. */
    const CASES: readonly [string, AiExportCompatibleSelection, string][] = [
        ['asset.market_analysis', selectionFixture('analysis', 'asset.market_analysis'), 'asset.position_and_history'],
        ['fx.pair_analysis', selectionFixture('analysis', 'fx.pair_analysis'), 'fx.market_and_exposure'],
    ];

    function additionalData(selection: AiExportCompatibleSelection, snapshot: AiExportSnapshotResponse): string {
        const diagnostics = renderAiExportPromptDiagnostics({selection, compatibility: compatibilityFixture(), snapshot, responseLanguage: 'English', translate: t});
        const sections = diagnostics.sections.filter((section) => section.id === 'additional_librefolio_data');
        expect(sections, 'exactly one additional_librefolio_data section').toHaveLength(1);
        return sections[0].content;
    }

    function labelOf(datasetId: string): string {
        const dataset = compatibilityFixture().catalog.datasets.find((entry) => entry.id === datasetId);
        if (!dataset) throw new Error(`Missing fixture dataset ${datasetId}`);
        return dataset.display_i18n_key;
    }

    it.each(CASES)('%s: an owner is told about %s; a user who owns no broker is not', (_analysis, selection, datasetId) => {
        const owner = snapshotFixture(selection);
        // Positive control: the suggestion is there for an owner, so its absence below is the filter, not the fixture.
        expect(additionalData(selection, owner)).toContain(`### ${labelOf(datasetId)}`);

        const withoutBrokers: AiExportSnapshotResponse = {...owner, unavailable_dataset_ids: [datasetId]};
        const content = additionalData(selection, withoutBrokers);
        expect(content).not.toContain(labelOf(datasetId));
        expect(content).not.toContain(datasetId);
    });
});
