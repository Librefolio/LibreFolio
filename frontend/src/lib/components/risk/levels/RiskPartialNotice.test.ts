// @vitest-environment jsdom
/**
 * RiskPartialNotice — the one notice above the risk levels (Vitest + jsdom).
 *
 * Developer's decision of 24/09/2026: the partial-result disclosure leaves the
 * levels and becomes ONE notice at the top of the four-level panel. It names what
 * came back partial and lists every warning worth reading, each once. Under
 * L1–L3 only what did not come back at all stays.
 *
 * What is pinned, without writing a translated sentence down: the notice renders
 * nothing when there is nothing to say; its title says *partial* when something
 * is, and *notes* when only warnings on whole results are left (a warning on an
 * `ok` result is still worth reading — nothing is filtered on `degrades_result`);
 * each measurement is named by its label when it has one, by its catalogue name
 * otherwise, and by its raw code when the catalogue has no name — never by a key.
 * Expected text is resolved from the shipped catalogue through the same `$_`.
 */
import {beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';

import {render, screen, setupI18n, within} from '$test/component';
import {_} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';

import {MONTHLY_VAR_INSTANCE} from '../riskAnalysisHelpers';
import type {ResultHealth, ResultReason} from './levelHelpers';
import RiskPartialNotice from './RiskPartialNotice.svelte';

const PARTIAL_TITLE = 'risk.levels.notice.partialTitle';
const NOTES_TITLE = 'risk.levels.notice.notesTitle';
const CATALOGUES = {en, it: itCatalogue, fr, es};

const MONTH_LABEL = 'risk.levels.l1.rows.month';
const CORRELATION_NAME = 'risk.analytics.correlation.name';
/** A measurement the catalogue has no name for: it must be shown as its code, never as a key. */
const UNNAMED_CODE = 'synthetic_measure_without_a_name';

const LABELLED: ResultHealth = {instanceId: MONTHLY_VAR_INSTANCE, code: 'historical_var', status: 'partial', label: MONTH_LABEL};
const UNLABELLED: ResultHealth = {instanceId: 'base-historical-correlation', code: 'correlation', status: 'partial'};
const UNNAMED: ResultHealth = {instanceId: 'base-historical-synthetic', code: UNNAMED_CODE, status: 'partial'};

const CARRIED_TWICE: ResultReason = {key: 'sparse_history:Synthetic sentence carried by two measurements.', message: 'Synthetic sentence carried by two measurements.', occurrences: 2};
const CARRIED_ONCE: ResultReason = {key: 'low_pair_coverage:Synthetic sentence carried by one measurement.', message: 'Synthetic sentence carried by one measurement.', occurrences: 1};

/** Whitespace between template nodes comes from the markup, not from the sentences. */
function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** A catalogue sentence formatted as the component formats it. */
function resolve(key: string): string {
    return normalize(get(_)(key));
}

/** The leaf behind a dotted key in one catalogue, read from the file on disk. */
function leaf(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

function mountNotice(partial: ResultHealth[], reasons: ResultReason[]) {
    return render(RiskPartialNotice, {props: {partial, reasons}});
}

beforeAll(async () => {
    await setupI18n();
});

describe('RiskPartialNotice — the catalogue it words its titles with', () => {
    it.each(Object.keys(CATALOGUES) as (keyof typeof CATALOGUES)[])('ships both titles in %s.json, as two different sentences without arguments', (locale) => {
        const catalogue = CATALOGUES[locale];
        // Positive control: a sibling key this reader must find, so a red below is a
        // missing key and not a guard reading the wrong place.
        expect(typeof leaf(catalogue, 'risk.levels.backtestNotice'), `risk.levels.backtestNotice is not a sentence in ${locale}.json: this guard reads the wrong place`).toBe('string');

        const partial = leaf(catalogue, PARTIAL_TITLE);
        const notes = leaf(catalogue, NOTES_TITLE);
        expect(typeof partial, `${PARTIAL_TITLE} is missing from ${locale}.json: the notice would print its key`).toBe('string');
        expect(typeof notes, `${NOTES_TITLE} is missing from ${locale}.json: the notice would print its key`).toBe('string');
        expect(String(partial).trim(), `${PARTIAL_TITLE} is empty in ${locale}.json`).not.toBe('');
        expect(String(notes).trim(), `${NOTES_TITLE} is empty in ${locale}.json`).not.toBe('');
        expect(partial, `the two titles read alike in ${locale}.json: the reader could not tell a partial answer from notes on a whole one`).not.toBe(notes);
        expect(`${String(partial)} ${String(notes)}`, `a title takes ICU arguments in ${locale}.json, but the notice words it without values`).not.toMatch(/[{}]/);
    });

    // The titles below are compared for equality with these resolutions, so a key that
    // resolved to itself would let a notice printing that key pass: this closes that door.
    it('resolves the two titles to two different sentences, not to their keys', () => {
        const partialTitle = resolve(PARTIAL_TITLE);
        const notesTitle = resolve(NOTES_TITLE);
        expect(partialTitle, `${PARTIAL_TITLE} did not resolve`).not.toBe(PARTIAL_TITLE);
        expect(notesTitle, `${NOTES_TITLE} did not resolve`).not.toBe(NOTES_TITLE);
        expect(partialTitle, 'the two titles resolve alike: "which title rendered" below would have no answer').not.toBe(notesTitle);
    });
});

describe('RiskPartialNotice', () => {
    it('renders nothing when there is nothing to disclose', () => {
        const {container} = mountNotice([], []);

        expect(screen.queryByTestId('risk-partial-notice'), 'an empty notice was rendered: a frame with nothing in it reads as a fault').toBeNull();
        expect(normalize(container.textContent)).toBe('');
    });

    it('titles a partial answer as partial and names each measurement: by label, by catalogue name, by code', () => {
        mountNotice([LABELLED, UNLABELLED, UNNAMED], []);

        const notice = screen.getByTestId('risk-partial-notice');
        expect(notice).toBeVisible();
        expect(notice).toHaveAttribute('data-partial-count', '3');
        expect(normalize(within(notice).getByTestId('risk-partial-title').textContent), 'a notice naming partial measurements is not titled as partial').toBe(resolve(PARTIAL_TITLE));

        const measurements = screen.getByTestId('risk-partial-measurements');
        expect(measurements).toHaveAttribute('data-count', '3');
        expect(normalize(measurements.textContent), 'the measurements are not named by label, then by catalogue name, then by code, joined by " · "').toBe([resolve(MONTH_LABEL), resolve(CORRELATION_NAME), UNNAMED_CODE].join(' · '));
        expect(screen.queryByTestId('risk-partial-reasons'), 'a reasons list was drawn with no reason in it').toBeNull();
    });

    it('titles warnings on a whole answer as notes, names no measurement, and still shows every sentence', () => {
        mountNotice([], [CARRIED_ONCE]);

        const notice = screen.getByTestId('risk-partial-notice');
        expect(notice, 'a warning on a whole result was withheld: nothing is filtered on degrades_result').toBeVisible();
        expect(notice).toHaveAttribute('data-partial-count', '0');
        expect(normalize(within(notice).getByTestId('risk-partial-title').textContent), 'a notice carrying only warnings on whole results is not titled as notes').toBe(resolve(NOTES_TITLE));
        expect(screen.queryByTestId('risk-partial-measurements'), 'a list of partial measurements was drawn with none in it').toBeNull();
        expect(screen.getByTestId('risk-partial-reasons')).toHaveAttribute('data-count', '1');
    });

    it('lists each reason once, with the number of measurements that carried it', () => {
        mountNotice([UNLABELLED], [CARRIED_TWICE, CARRIED_ONCE]);

        expect(screen.getByTestId('risk-partial-reasons')).toHaveAttribute('data-count', '2');
        const entries = screen.getAllByTestId('risk-partial-reason');
        expect(
            entries.map((entry) => [normalize(entry.textContent), entry.getAttribute('data-occurrences')]),
            'the reasons are not the given sentences, once each, in order, with their arity',
        ).toEqual([
            [CARRIED_TWICE.message, '2'],
            [CARRIED_ONCE.message, '1'],
        ]);
    });

    it('never puts a key on screen', () => {
        mountNotice([LABELLED, UNLABELLED, UNNAMED], [CARRIED_TWICE]);

        // Barrier: everything this notice can word is on screen before the absence is read.
        const notice = screen.getByTestId('risk-partial-notice');
        expect(screen.getByTestId('risk-partial-measurements')).toHaveAttribute('data-count', '3');
        expect(screen.getByTestId('risk-partial-reasons')).toHaveAttribute('data-count', '1');
        expect(normalize(notice.textContent), 'a catalogue key reached the screen').not.toMatch(/\brisk\.[a-zA-Z]+\./);
    });
});
