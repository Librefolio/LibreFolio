// @vitest-environment jsdom
/**
 * DataQualityBanner — the NON_ISO_CURRENCY issues of the portfolio report (lot E-19b2, workstream E).
 *
 * Before E-18 the lenient rule stored a currency as written (`978`, `EURO`, `eur`), and every conversion such a value
 * needs fails. The report asked for its FX pair (`978-EUR`, whose «Add FX pair» gets a 422); E-19b2 names the value
 * instead: one warning `NON_ISO_CURRENCY` per value, carrying `message_params.value` (the value, cut at 16 characters)
 * and, when there are, the `suggestion` or the `candidates`, with no CTA, no pair, and the group key
 * `non_iso_currency:<value>`, unique per value. The banner needs no change, but two such issues share their code, and its
 * `{#each}` is keyed by `code + group_key`: both must render.
 *
 * The contract under test:
 *   - DQN-01: the five keys of the issue are messages of the four `dataQuality` source catalogues
 *     (`src/lib/i18n/dataQuality/<lang>.json`) and of the four generated ones (`src/lib/i18n/<lang>.json`, built from the
 *     sources by Vitest's global setup, read as CNI-09 reads them), each naming exactly the parameters the backend sends —
 *     `nonIsoCurrencySuggestion` {value, suggestion}, `nonIsoCurrencyCandidates` {value, candidates},
 *     `nonIsoCurrencyUnknown` {value}, `nonIsoReportCurrency` {value, suggestion}, `nonIsoReportCurrencyUnknown` {value}
 *     —, the same in the four languages: a parameter the backend does not send makes the formatter throw, one left out
 *     hides what the user has to correct;
 *   - DQN-02 (grouped, the Dashboard's mode) and DQN-03 (flat): two NON_ISO_CURRENCY issues with different group keys,
 *     beside a MISSING_FX_MARKET issue: two `data-quality-issue-NON_ISO_CURRENCY` rows, none showing a raw key, each
 *     showing its own value and its suggestion (or candidates) and nothing of the other's value; no
 *     `data-quality-cta-NON_ISO_CURRENCY`, no asset button and nothing else to press in their rows, while the sibling's
 *     action is drawn in the same mount (the presence barrier of the absence): grouped, the chip of its pair
 *     `data-quality-fx-pair-EUR-USD`, since an `add_fx_pair` acts on one pair at a time (the layout of 19/10/2026,
 *     `DataQualityBanner.layout.test.ts`); flat, its `data-quality-cta-MISSING_FX_MARKET`;
 *   - DQN-04: the generated API client accepts the issue. zodios validates every response with it
 *     (`zodios-client.ts`, `validate: 'response'`): an IssueCode the client does not know rejects the whole report, and
 *     the Dashboard of a user with a stored `978` loses its data instead of showing the warning.
 *
 * The texts are never asserted on: only the parameters this file passes (`978`, `EUR`, `Bolívar Soberano`, `VED, VES`)
 * are looked for in what the rows show.
 *
 * Red today (marked `// red until E-19b2`): no catalogue holds the five keys — the rows show their raw keys —, and the
 * generated client's IssueCode has no NON_ISO_CURRENCY (`./dev.py api sync` regenerates it). The row count and the
 * absence of a CTA hold today already: the banner needs no change.
 */
import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {schemas} from '$lib/api/generated';
import type {SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import enSource from '$lib/i18n/dataQuality/en.json';
import itSource from '$lib/i18n/dataQuality/it.json';
import frSource from '$lib/i18n/dataQuality/fr.json';
import esSource from '$lib/i18n/dataQuality/es.json';
import type {DataQualityIssue} from './DataQualityBanner.svelte';
import DataQualityBanner from './DataQualityBanner.svelte';

const NON_ISO = 'NON_ISO_CURRENCY';

// --- Fixtures: the issues as the backend serialises them -------------------------------------------------------------

/** `978`, stored by an older version: one ISO code stands behind it, EUR; one held asset is stored in it. */
const SUGGESTED: DataQualityIssue = {
    domain: 'portfolio',
    code: NON_ISO,
    severity: 'warning',
    message_i18n_key: 'dataQuality.nonIsoCurrencySuggestion',
    message_params: {value: '978', suggestion: 'EUR'},
    count: 1,
    affected_asset_ids: [41],
    affected_asset_names: ['Old ledger fund'],
    affected_fx_pairs: [],
    cta_action: null,
    cta_target: null,
    group_key: 'non_iso_currency:978',
};

/** `Bolívar Soberano`: the name ISO 4217 gives two currencies, VED and VES; a side of a missing pair, no asset. */
const AMBIGUOUS: DataQualityIssue = {
    domain: 'portfolio',
    code: NON_ISO,
    severity: 'warning',
    message_i18n_key: 'dataQuality.nonIsoCurrencyCandidates',
    message_params: {value: 'Bolívar Soberano', candidates: 'VED, VES'},
    count: null,
    affected_asset_ids: [],
    affected_asset_names: [],
    affected_fx_pairs: [],
    cta_action: null,
    cta_target: null,
    group_key: 'non_iso_currency:Bolívar Soberano',
};

/** A canonical pair missing beside them: its action (grouped, its pair's chip; flat, its CTA), drawn in the same mount, is the barrier of the absence of theirs. */
const SIBLING: DataQualityIssue = {
    domain: 'portfolio',
    code: 'MISSING_FX_MARKET',
    severity: 'warning',
    message_i18n_key: 'dataQuality.missingFx',
    message_params: {count: 1},
    count: 1,
    affected_asset_ids: [],
    affected_asset_names: [],
    affected_fx_pairs: ['EUR-USD'],
    cta_action: 'add_fx_pair',
    cta_target: null,
    group_key: 'missing_fx',
};

const ISSUES: DataQualityIssue[] = [SUGGESTED, AMBIGUOUS, SIBLING];

/** What each NON_ISO_CURRENCY row must show of its own parameters, and the other row's value it must not show. */
const ROWS: Array<{value: string; shows: string[]; notShows: string}> = [
    {value: '978', shows: ['978', 'EUR'], notShows: 'Bolívar Soberano'},
    {value: 'Bolívar Soberano', shows: ['Bolívar Soberano', 'VED, VES'], notShows: '978'},
];

// --- Helpers ----------------------------------------------------------------------------------------------------------

/** The text an element shows, each run of whitespace read as one space. */
function shown(element: HTMLElement): string {
    return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** The two NON_ISO_CURRENCY rows each show their own value and parameters, and none shows a raw key. */
function expectEachRowShowsItsOwnValue(rows: HTMLElement[]): void {
    expect(rows, 'one row per NON_ISO_CURRENCY issue: the two group keys keep them apart').toHaveLength(2);
    for (const row of rows) {
        expect(shown(row), 'a row shows a raw key: no catalogue holds its sentence').not.toContain('dataQuality.nonIso');
    }
    for (const {value, shows, notShows} of ROWS) {
        const carrying = rows.filter((row) => shown(row).includes(value));
        expect(carrying, `one row shows the value ${value}`).toHaveLength(1);
        const text = shown(carrying[0]);
        for (const part of shows) expect(text, `the row of ${value} shows ${part}`).toContain(part);
        expect(text, `the row of ${value} shows nothing of the other value`).not.toContain(notShows);
    }
}

/** No action of any kind for a NON_ISO_CURRENCY issue — no CTA, no asset button, no pair chip; asked once the sibling's action is proven drawn. */
function expectNoActionForNonIso(): void {
    expect(screen.queryByTestId(`data-quality-cta-${NON_ISO}`), 'no CTA: nothing to add, sync or open').toBeNull();
    expect(screen.queryByTestId(`data-quality-nav-assets-${NON_ISO}`), 'no asset button: the issue has no CTA').toBeNull();
    // Whatever shape an action takes (one button, a chip per asset, a chip per pair), it is a button inside the row.
    for (const row of screen.getAllByTestId(`data-quality-issue-${NON_ISO}`)) {
        const buttons = [...row.querySelectorAll('button')].map((button) => button.getAttribute('data-testid'));
        expect(buttons, 'nothing to press in a NON_ISO_CURRENCY row: no CTA, no asset button, no pair chip').toEqual([]);
    }
}

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
});

// =====================================================================================================================
describe('DataQualityBanner — two NON_ISO_CURRENCY issues', () => {
    // red until E-19b2
    it('DQN-02: grouped (the Dashboard): both rows are drawn once unfolded, each with its own value, and neither offers a CTA', async () => {
        render(DataQualityBanner, {issues: ISSUES, mode: 'grouped'});
        const toggle = screen.getByTestId('data-quality-toggle');
        expect(toggle, 'mounted folded').toHaveAttribute('aria-expanded', 'false');
        await fireEvent.click(toggle);
        expect(toggle, 'unfolded').toHaveAttribute('aria-expanded', 'true');

        // The presence barrier of the absences below: in this very mount, an issue with an action draws it. Grouped, an
        // add_fx_pair acts on one pair at a time (the layout of 19/10/2026): its action is the chip of its pair.
        expect(within(screen.getByTestId('data-quality-issue-MISSING_FX_MARKET')).getByTestId('data-quality-fx-pair-EUR-USD')).toBeVisible();
        expectEachRowShowsItsOwnValue(screen.getAllByTestId(`data-quality-issue-${NON_ISO}`));
        expectNoActionForNonIso();
    });

    // red until E-19b2
    it('DQN-03: flat: one banner per issue, each with its own value, and neither offers a CTA', () => {
        render(DataQualityBanner, {issues: ISSUES, mode: 'flat'});

        // The presence barrier of the absences below: in this very mount, an issue with a CTA draws it.
        expect(screen.getByTestId('data-quality-cta-MISSING_FX_MARKET')).toBeVisible();
        expectEachRowShowsItsOwnValue(screen.getAllByTestId(`data-quality-issue-${NON_ISO}`));
        expectNoActionForNonIso();
    });
});

// =====================================================================================================================
/** The node at a dotted path of a catalogue, or undefined. */
function messageOf(catalogue: unknown, key: string): unknown {
    let node = catalogue;
    for (const part of key.split('.')) node = node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined;
    return node;
}

/** The ICU arguments a message names, sorted: `['suggestion', 'value']` for «{value}: did you mean {suggestion}?». */
function placeholdersOf(message: string): string[] {
    return [...new Set([...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1]))].sort();
}

/** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
const CATALOGUES: Record<string, Record<SupportedLocale, unknown>> = {
    'dataQuality source': {en: enSource, it: itSource, fr: frSource, es: esSource},
    'generated catalogue': {en, it: itCatalogue, fr, es},
};

/** Each key of the issue, and exactly the parameters the backend sends with it. */
const MESSAGES: Array<[string, string[]]> = [
    ['dataQuality.nonIsoCurrencySuggestion', ['suggestion', 'value']],
    ['dataQuality.nonIsoCurrencyCandidates', ['candidates', 'value']],
    ['dataQuality.nonIsoCurrencyUnknown', ['value']],
    ['dataQuality.nonIsoReportCurrency', ['suggestion', 'value']],
    ['dataQuality.nonIsoReportCurrencyUnknown', ['value']],
];

describe('the sentences of the NON_ISO_CURRENCY issue', () => {
    // red until E-19b2
    it.each(MESSAGES)('DQN-01: %s is a message of the four dataQuality sources and of the four generated catalogues, naming exactly %j', (key, params) => {
        for (const [where, catalogues] of Object.entries(CATALOGUES)) {
            for (const [language, catalogue] of Object.entries(catalogues)) {
                const message = messageOf(catalogue, key);
                expect(typeof message, `${where} ${language}: ${key} is not a message`).toBe('string');
                expect(placeholdersOf(message as string), `${where} ${language}: ${key} must name exactly ${params.join(', ')}`).toEqual(params);
            }
        }
    });
});

// =====================================================================================================================
describe('the API client', () => {
    // red until E-19b2 (./dev.py api sync)
    it('DQN-04: the generated client accepts a NON_ISO_CURRENCY issue, which zodios checks on every report', () => {
        expect(schemas.DataQualityIssue.safeParse({...SUGGESTED, code: 'MISSING_PRICE'}).success, 'control: the same issue under a code the client knows parses').toBe(true);

        expect(schemas.IssueCode.safeParse(NON_ISO).success, 'the generated IssueCode has no NON_ISO_CURRENCY: zodios rejects every report holding one').toBe(true);
        for (const issue of [SUGGESTED, AMBIGUOUS]) {
            expect(schemas.DataQualityIssue.safeParse(issue).success, `${issue.group_key} parses`).toBe(true);
        }
    });
});
