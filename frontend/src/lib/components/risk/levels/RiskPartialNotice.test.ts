// @vitest-environment jsdom
/**
 * RiskPartialNotice — the one notice above the risk levels (Vitest + jsdom).
 *
 * Developer's decision of 24/09/2026: the partial-result disclosure leaves the
 * levels and becomes ONE notice at the top of the four-level panel. It names what
 * came back partial and lists every warning worth reading, each once. Under
 * L1–L3 only what did not come back at all stays.
 *
 * Developer's decision of 30/09/2026 — cause, then effect: the reasons come first,
 * because they are what the reader can act on; the measurements they cost follow,
 * one chip each, grouped under the question of the level that shows them — L1, L2,
 * L3, then the ones no level claims, in a group of their own and never dropped.
 *
 * What is pinned, without writing a translated sentence down: the notice renders
 * nothing when there is nothing to say; its title says *partial* when something
 * is — or names the cause, when every reason is a holding nothing has ever priced —
 * and *notes* when only warnings on whole results are left (a warning on an `ok`
 * result is still worth reading — nothing is filtered on `degrades_result`); each
 * measurement is named by its label when it has one, by its catalogue name
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
import {analyticNameKey} from './partialNotice';
import RiskPartialNotice from './RiskPartialNotice.svelte';

const PARTIAL_TITLE = 'risk.levels.notice.partialTitle';
const NOTES_TITLE = 'risk.levels.notice.notesTitle';
/** The title that names the cause: every reason is a holding nothing has ever priced. */
const NO_PRICE_SOURCE_TITLE = 'risk.levels.notice.noPriceSourceTitle';
/** The line that leads the measurements, after the causes. */
const AFFECTED = 'risk.levels.notice.affected';
/** What the panel names L3's own KPI by: in L3, its catalogue name ("historical") would be false. */
const L3_KPI_LABEL = 'risk.levels.l3.rows.kpi';
/** Each level's question, as its frame titles it on the page and the notice titles its group. */
const LEVEL_TITLES = {1: 'risk.levels.l1.title', 2: 'risk.levels.l2.title', 3: 'risk.levels.l3.title'} as const;
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

/** Mounted with no `levelOf` at all unless one is given, so the prop's own default is what is exercised. */
function mountNotice(partial: ResultHealth[], reasons: ResultReason[], levelOf?: Readonly<Record<string, 1 | 2 | 3>>) {
    return render(RiskPartialNotice, {props: {partial, reasons, ...(levelOf ? {levelOf} : {})}});
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

    // Cause → effect (30/09/2026) put three more sentences on the notice: the title naming the
    // cause, the line leading the measurements, and the label L3's own KPI is named by.
    it.each(Object.keys(CATALOGUES) as (keyof typeof CATALOGUES)[])('ships the cause title, the lead line and the L3 KPI label in %s.json, and three different titles', (locale) => {
        const catalogue = CATALOGUES[locale];
        // Positive control, as above: a red below is a missing key, not a guard reading the wrong place.
        expect(typeof leaf(catalogue, 'risk.levels.backtestNotice'), `risk.levels.backtestNotice is not a sentence in ${locale}.json: this guard reads the wrong place`).toBe('string');

        for (const key of [NO_PRICE_SOURCE_TITLE, AFFECTED, L3_KPI_LABEL]) {
            const value = leaf(catalogue, key);
            expect(typeof value, `${key} is missing from ${locale}.json: the notice would print its key`).toBe('string');
            expect(String(value).trim(), `${key} is empty in ${locale}.json`).not.toBe('');
            expect(String(value), `${key} takes ICU arguments in ${locale}.json, but the notice words it without values`).not.toMatch(/[{}]/);
        }

        // Pairwise different: the title is the one place the notice says which case it is in.
        const titles = [PARTIAL_TITLE, NOTES_TITLE, NO_PRICE_SOURCE_TITLE].map((key) => leaf(catalogue, key));
        expect(new Set(titles).size, `two of the notice's three titles read alike in ${locale}.json: the reader could not tell a cause from a partial answer, or either from notes`).toBe(3);
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

        // One chip per measurement, read chip by chip and in order, so each naming rule is
        // covered by a measurement of its own: a label, a catalogue name found through the
        // camelCase rule, and the raw code of an analytic the catalogue has no name for.
        // A query, not a `getAll`: a notice without chips must fail this assertion, not error.
        const measurements = screen.getByTestId('risk-partial-measurements');
        const chips = within(measurements).queryAllByTestId('risk-partial-measurement');
        expect(
            chips.map((chip) => [chip.getAttribute('data-instance'), normalize(chip.textContent)]),
            'the measurements are not named one chip each, in order: by label, then by catalogue name, then by code',
        ).toEqual([
            [LABELLED.instanceId, resolve(MONTH_LABEL)],
            [UNLABELLED.instanceId, resolve(CORRELATION_NAME)],
            [UNNAMED.instanceId, UNNAMED_CODE],
        ]);
        expect(measurements, 'data-count does not count the chips on screen').toHaveAttribute('data-count', String(chips.length));

        // Never a key, said explicitly: none in the shape of one, and none equal to the key it
        // was resolved from — svelte-i18n echoes a missing id back, so a chip printing its own
        // key would otherwise pass for a name that happened to resolve to it.
        const resolvedFrom = [MONTH_LABEL, CORRELATION_NAME, analyticNameKey(UNNAMED_CODE)];
        chips.forEach((chip, index) => {
            const text = normalize(chip.textContent);
            expect(text, `chip ${index + 1} prints a catalogue key`).not.toMatch(/\brisk\.[a-zA-Z]+\./);
            expect(text, `chip ${index + 1} prints the key it was resolved from`).not.toBe(resolvedFrom[index]);
        });
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

/*
 * The tone of the notice (developer's decision; this test list approved on 30/09/2026).
 *
 * Amber says "something went wrong, and may come right": worth a look, worth a retry. That is
 * the wrong word for a holding nothing has ever priced — no price source assigned, no price
 * ever recorded — because that exclusion will read the same tomorrow: it is a standing fact
 * about the portfolio, not a fault of today's answer. So the root publishes its tone in
 * `data-tone`: `info` if and only if there is at least one reason and every reason states that
 * permanent cause (`reason === 'no_price_source'`), `warning` for anything else.
 *
 * One door per case: `every`, not `some` — one occasional cause among permanent ones warns; a
 * reason that states no cause is never taken for a permanent one, beside one or alone; an empty
 * list of reasons does not make `every` true by vacuity — partial measurements with no reason
 * given warn, since nothing says why; and the partial measurements never decide the tone on
 * their own, in either direction.
 */

/** The permanent cause, in two sentences: two measurements excluding different holdings word it apart. */
const NO_SOURCE_ONE: ResultReason = {key: 'assets_excluded:Synthetic sentence about one holding nothing has ever priced.', message: 'Synthetic sentence about one holding nothing has ever priced.', occurrences: 2, reason: 'no_price_source'};
const NO_SOURCE_OTHER: ResultReason = {key: 'assets_excluded:Synthetic sentence about another holding nothing has ever priced.', message: 'Synthetic sentence about another holding nothing has ever priced.', occurrences: 1, reason: 'no_price_source'};
/** An occasional cause: a price that is missing, and may yet arrive. */
const MISSING_PRICE: ResultReason = {key: 'assets_excluded:Synthetic sentence about a holding missing a price.', message: 'Synthetic sentence about a holding missing a price.', occurrences: 1, reason: 'missing_price'};
/** A note that states no cause at all, as a data-quality warning words it. */
const NO_CAUSE: ResultReason = {key: 'data_quality_degraded:Synthetic data-quality sentence stating no cause.', message: 'Synthetic data-quality sentence stating no cause.', occurrences: 1};

describe('RiskPartialNotice — its tone: informative only when every cause is permanent', () => {
    /** The notice for these inputs, once it is seen to hold every reason and measurement it was given. */
    function noticeFor(partial: ResultHealth[], reasons: ResultReason[]): HTMLElement {
        mountNotice(partial, reasons);
        const notice = screen.getByTestId('risk-partial-notice');
        // Barrier: the tone below is about exactly these inputs, not about a notice that dropped some.
        expect(within(notice).queryAllByTestId('risk-partial-reason'), 'the notice does not hold one entry per reason given').toHaveLength(reasons.length);
        expect(notice, 'the notice does not count the partial measurements it was given').toHaveAttribute('data-partial-count', String(partial.length));
        return notice;
    }

    it('is informative when every reason is a holding nothing has ever priced, on a partial answer', () => {
        const notice = noticeFor([UNLABELLED], [NO_SOURCE_ONE, NO_SOURCE_OTHER]);
        expect(notice, 'every reason is a holding with no price source — a standing fact, not a fault — yet the notice is not informative').toHaveAttribute('data-tone', 'info');
    });

    it('is informative when every reason is a holding nothing has ever priced, and nothing came back partial', () => {
        const notice = noticeFor([], [NO_SOURCE_ONE, NO_SOURCE_OTHER]);
        expect(notice, 'notes whose every cause is a missing price source are not informative when no measurement is partial').toHaveAttribute('data-tone', 'info');
    });

    it('warns when one reason has an occasional cause beside a permanent one', () => {
        const notice = noticeFor([UNLABELLED], [NO_SOURCE_ONE, MISSING_PRICE]);
        expect(notice, 'a missing price may come right and deserves a warning, yet one permanent cause beside it made the whole notice informative').toHaveAttribute('data-tone', 'warning');
    });

    it('warns when one reason states no cause, beside a permanent one', () => {
        const notice = noticeFor([UNLABELLED], [NO_SOURCE_ONE, NO_CAUSE]);
        expect(notice, 'a note that states no cause sits beside a permanent one, yet the notice is informative: a cause nobody stated was taken for a permanent one').toHaveAttribute('data-tone', 'warning');
    });

    it('warns when measurements came back partial and no reason is given', () => {
        const notice = noticeFor([LABELLED, UNLABELLED], []);
        expect(notice, 'measurements came back partial with no reason given, yet the notice does not warn: nothing says the cause is permanent').toHaveAttribute('data-tone', 'warning');
    });

    it('warns when no reason states a cause', () => {
        const notice = noticeFor([], [CARRIED_TWICE, CARRIED_ONCE]);
        expect(notice, 'reasons that state no cause read as a permanent one: an absent cause must never soften the notice').toHaveAttribute('data-tone', 'warning');
    });
});

/*
 * Cause, then effect (developer's decision of 30/09/2026; this test list approved the same day).
 *
 * The reasons are what the reader can act on, so they come first; the measurements they cost
 * follow, grouped under the question of the level that shows them, so the reader knows where on
 * the page to read with care. The panel says which level shows which measurement (`levelOf`, by
 * instance id, first claim wins); the notice keeps L1, L2, L3 in page order whatever order the
 * measurements arrive in, and gives the ones no level claims a group of their own, last and
 * untitled — dropped, a partial measurement would read as whole.
 */

/** L3's two measurements, as the panel names them: the scatter by its catalogue name, L3's own KPI by its label. */
const RISK_RETURN: ResultHealth = {instanceId: 'base-current_composition-asset_risk_return', code: 'asset_risk_return', status: 'partial'};
const L3_KPI: ResultHealth = {instanceId: 'base-current_composition-historical_kpi', code: 'historical_kpi', status: 'partial', label: L3_KPI_LABEL};

/** Out of page order on purpose — an L3 entry first, an unplaced one in the middle, a second L3 entry last — so the grouping cannot be the order the entries came in. */
const OUT_OF_ORDER: ResultHealth[] = [RISK_RETURN, LABELLED, UNNAMED, UNLABELLED, L3_KPI];
/** Every entry above placed but `UNNAMED`, which no level claims. */
const LEVEL_OF: Readonly<Record<string, 1 | 2 | 3>> = {[RISK_RETURN.instanceId]: 3, [LABELLED.instanceId]: 1, [UNLABELLED.instanceId]: 2, [L3_KPI.instanceId]: 3};

/** An element the test cannot go on without, as an assertion failure rather than a null dereference. */
function present(element: HTMLElement | null, what: string): HTMLElement {
    expect(element, `${what} is missing`).not.toBeNull();
    return element as HTMLElement;
}

/** The instance of each chip in one group, in document order. */
function instancesIn(group: HTMLElement): (string | null)[] {
    return within(group)
        .queryAllByTestId('risk-partial-measurement')
        .map((chip) => chip.getAttribute('data-instance'));
}

/** What a group says besides its chips: the question of its level, or nothing. */
function textBesideChips(group: HTMLElement): string {
    const copy = group.cloneNode(true) as HTMLElement;
    copy.querySelectorAll('[data-testid="risk-partial-measurement"]').forEach((chip) => chip.remove());
    return normalize(copy.textContent);
}

describe('RiskPartialNotice — the cause first, then what it cost, under the level that shows it', () => {
    it('lists the causes before the measurements they cost', () => {
        mountNotice([UNLABELLED], [CARRIED_ONCE], {[UNLABELLED.instanceId]: 2});

        const notice = screen.getByTestId('risk-partial-notice');
        // Barrier: both halves are on screen, so the order below compares two things that exist.
        const reasons = present(within(notice).queryByTestId('risk-partial-reasons'), 'the list of causes');
        const measurements = present(within(notice).queryByTestId('risk-partial-measurements'), 'the list of measurements');
        // Neither inside the other: a nested half would also read as FOLLOWING, and order nothing.
        expect(reasons.contains(measurements) || measurements.contains(reasons), 'one half is nested in the other').toBe(false);
        expect(Boolean(reasons.compareDocumentPosition(measurements) & Node.DOCUMENT_POSITION_FOLLOWING), 'the measurements come before their causes: the reader meets the effect before what can be acted on').toBe(true);
    });

    it('groups the measurements under their level in page order, the unplaced ones last and untitled', () => {
        mountNotice(OUT_OF_ORDER, [], LEVEL_OF);

        const measurements = screen.getByTestId('risk-partial-measurements');
        const groups = within(measurements).queryAllByTestId('risk-partial-level');
        expect(
            groups.map((group) => group.getAttribute('data-level')),
            'the groups are not L1, L2, L3, then the unplaced ones, each once',
        ).toEqual(['1', '2', '3', 'none']);

        // Each group holds exactly its own measurements, in the order they were given.
        expect(groups.map(instancesIn), 'a measurement sits under the wrong level, or out of the order it was given in').toEqual([[LABELLED.instanceId], [UNLABELLED.instanceId], [RISK_RETURN.instanceId, L3_KPI.instanceId], [UNNAMED.instanceId]]);

        // A level's group opens on its question, worded as its frame words it; the group of the
        // unplaced ones says nothing but its chip's name.
        ([1, 2, 3] as const).forEach((level, index) => {
            const title = resolve(LEVEL_TITLES[level]);
            expect(title, `${LEVEL_TITLES[level]} did not resolve`).not.toBe(LEVEL_TITLES[level]);
            expect(textBesideChips(groups[index]), `the level ${level} group is not titled by its question alone`).toBe(title);
            expect(normalize(groups[index].textContent).startsWith(title), `the level ${level} group does not open on its question`).toBe(true);
        });
        expect(normalize(groups[3].textContent), 'the group of unplaced measurements says more than its chip').toBe(UNNAMED_CODE);

        // One chip per partial measurement, counted by the list itself.
        expect(within(measurements).queryAllByTestId('risk-partial-measurement'), 'not one chip per partial measurement').toHaveLength(OUT_OF_ORDER.length);
        expect(measurements, 'data-count does not count the partial measurements').toHaveAttribute('data-count', String(OUT_OF_ORDER.length));
    });

    it('puts every measurement in the one untitled group when no level is known', () => {
        mountNotice(OUT_OF_ORDER, []);

        const measurements = screen.getByTestId('risk-partial-measurements');
        const groups = within(measurements).queryAllByTestId('risk-partial-level');
        expect(
            groups.map((group) => group.getAttribute('data-level')),
            'a measurement with no level was placed under one, or dropped',
        ).toEqual(['none']);
        expect(instancesIn(groups[0]), 'the unplaced measurements are not all named, in the order given').toEqual(OUT_OF_ORDER.map((entry) => entry.instanceId));
        expect(textBesideChips(groups[0]), 'the group of unplaced measurements carries a title').toBe('');
        expect(measurements, 'data-count does not count the partial measurements').toHaveAttribute('data-count', String(OUT_OF_ORDER.length));
    });
});

/*
 * The title names the cause when there is one to name (developer's decision of 30/09/2026).
 *
 * It follows the tone pinned above: a partial answer whose every reason is a holding nothing has
 * ever priced is titled by that cause; notes on a whole answer stay notes, whatever their cause;
 * and one occasional cause beside a permanent one makes the whole answer partial again — `every`,
 * never `some`, as for the tone.
 */
describe('RiskPartialNotice — its title names the cause', () => {
    // The titles below are compared for equality with these resolutions: three sentences that
    // resolved alike, or to their keys, would leave "which title rendered" without an answer.
    it('resolves the three titles to three different sentences, not to their keys', () => {
        const titles = [PARTIAL_TITLE, NOTES_TITLE, NO_PRICE_SOURCE_TITLE].map((key) => [key, resolve(key)] as const);
        for (const [key, title] of titles) expect(title, `${key} did not resolve`).not.toBe(key);
        expect(new Set(titles.map(([, title]) => title)).size, 'two of the three titles resolve alike').toBe(3);
    });

    it('names the missing price source when every reason is one, on a partial answer', () => {
        mountNotice([UNLABELLED], [NO_SOURCE_ONE, NO_SOURCE_OTHER]);

        const notice = screen.getByTestId('risk-partial-notice');
        // Barrier: the case under test is the informative one.
        expect(notice).toHaveAttribute('data-tone', 'info');
        expect(normalize(within(notice).getByTestId('risk-partial-title').textContent), 'a partial answer whose every cause is a holding nothing has ever priced is not titled by that cause').toBe(resolve(NO_PRICE_SOURCE_TITLE));
    });

    it('stays notes when every reason is a missing price source and nothing came back partial', () => {
        mountNotice([], [NO_SOURCE_ONE]);

        const notice = screen.getByTestId('risk-partial-notice');
        expect(notice).toHaveAttribute('data-tone', 'info');
        expect(normalize(within(notice).getByTestId('risk-partial-title').textContent), 'notes on a whole answer are not titled as notes').toBe(resolve(NOTES_TITLE));
    });

    it('says partial when one reason is occasional beside a permanent one', () => {
        mountNotice([UNLABELLED], [NO_SOURCE_ONE, MISSING_PRICE]);

        const notice = screen.getByTestId('risk-partial-notice');
        expect(notice).toHaveAttribute('data-tone', 'warning');
        expect(normalize(within(notice).getByTestId('risk-partial-title').textContent), 'one permanent cause among others made the title name it').toBe(resolve(PARTIAL_TITLE));
    });
});
