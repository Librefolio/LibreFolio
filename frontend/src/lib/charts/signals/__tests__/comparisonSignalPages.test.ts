// @vitest-environment node
/**
 * The pages that name a comparison asset leave its fallback name to the catalogue (T-FB; Vitest, node). 13/10/2026.
 *
 * Why. Before its display name is known, a comparison asset is named by its id: «Asset #7». The asset page writes
 * that name by hand in English — the comparison events' banner and labels, the calendar return's overlay, the
 * name it hands `AssetComparisonSignal` — and its not-found error is `Asset #7 not found`, whatever the interface
 * language. The FX page words the same name through its own key, `fxDetail.assetFallback`. One meaning, one key:
 * `chartSettings.signals.assetFallback`, the one `AssetComparisonSignal` reads (`comparisonSignals.test.ts`).
 *
 * The contract, after the cure:
 *   - neither page writes «Asset #…» by hand. The asset page leaves `_assetDisplayName` unset for an asset it does
 *     not know, so the signal names it; its other comparison labels read `$t('chartSettings.signals.assetFallback',
 *     …)`, and its not-found error is `error = catalogueError('assetDetail.notFound')`, a key every catalogue holds;
 *   - the FX page no longer reads `fxDetail.assetFallback`: it reads `chartSettings.signals.assetFallback`;
 *   - the asset page's two load failures fall back to the catalogue too, right after the error's own message, which
 *     stays: `error = e?.message || catalogueError('assetDetail.loadFailed')` and
 *     `… || catalogueError('assetDetail.pricesLoadFailed')`, and the English `Failed to load asset info` and
 *     `Failed to load prices` are gone from the page, in any quotes — the console logs, which end on a colon, are
 *     not these literals (added to the lot by the coordinator on 13/10);
 *   - every banner error of the asset page goes through its `catalogueError(key)`, which returns `_i18n:${key}`,
 *     the form its `errorMessage` translates: the key is written whole at each call because `dev.py i18n audit`
 *     reads a key only as one whole literal — written inside `'_i18n:<key>'`, it was listed as dead (repair of
 *     13/10, after the cure). A key assembled or prefixed by hand does not satisfy the forms.
 *
 * How. Mounting the two pages is impractical — each loads a dozen endpoints and stores before it draws — so this
 * spec reads their sources, the way `chartCoreHelpers.test.ts` reads chart sources. It enumerates, it does not
 * judge: every finding is listed as `:line  source`. The forms are a floor, not a proof: a quote or a backtick
 * directly followed by `Asset #` (a template or a literal opening the name), and a quoted
 * `fxDetail.assetFallback`. A name assembled across statements is not seen; the signal's own name is pinned by
 * `comparisonSignals.test.ts`, and what the pages show by their E2E.
 *
 * One site is allowed, keyed by its content and with its reason: the console label the asset page builds inside
 * `isDebugEnabled()` — a developer log, never shown to the user, left out of the lot by the coordinator's analysis.
 * An allowed site that no longer exists is refused: remove its entry.
 *
 * Positive controls: the sources read are the two pages (each holds its own noData banner error); the asset page's
 * `catalogueError` builds the `_i18n:` form its banner translates (the premise of every key check); the forms match
 * a violating line and pass a compliant one — the load failures' and the banner keys' too: the contract's call is
 * seen, the key alone, another key, the prefixed string, an assembled key or another variable are not — and the
 * shared key is in every catalogue.
 *
 * Red before the cure (13/10): the asset page wrote «Asset #…» on five user-facing lines and named no shared key,
 * and its two load failures fell back to English sentences; the FX page read `fxDetail.assetFallback` twice;
 * `assetDetail.notFound`, `loadFailed` and `pricesLoadFailed` were in no catalogue.
 *
 * The catalogues are read like `riskGlossary.test.ts` reads them: the four generated ones (`src/lib/i18n/<lang>.json`,
 * built from their sources by Vitest's global setup), typed on the app's locale list.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`), next to
 * `comparisonSignals.test.ts`.
 */
import {describe, expect, it} from 'vitest';
import {readFileSync} from 'node:fs';
import type {SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

/** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

type Page = 'asset' | 'fx';

const SOURCES: Record<Page, string> = {
    asset: readFileSync(new URL('../../../../routes/(app)/assets/[id]/+page.svelte', import.meta.url), 'utf8'),
    fx: readFileSync(new URL('../../../../routes/(app)/fx/[pair]/+page.svelte', import.meta.url), 'utf8'),
};

/** A name written by hand: a quote or a backtick directly followed by `Asset #`. */
const HAND_WRITTEN_NAME = /[`'"]Asset #/;
/** The FX page's own key for the same name. */
const FX_PAGE_KEY = /[`'"]fxDetail\.assetFallback[`'"]/;
/** The shared key, as a page names it. */
const SHARED_KEY = "'chartSettings.signals.assetFallback'";

/** The asset page's two load failures: the English sentence each fell back to before the cure, and its key after. */
const LOAD_FAILURES = [
    {english: 'Failed to load asset info', key: 'assetDetail.loadFailed'},
    {english: 'Failed to load prices', key: 'assetDetail.pricesLoadFailed'},
] as const;

/** The lines of `source` holding `english` as a whole literal, in any quotes: a console log that goes on (`'… info:'`) is another literal. */
function englishLiterals(source: string, english: string): string[] {
    return findings(source, new RegExp(`[\`'"]${english}[\`'"]`));
}

/**
 * The asset page's banner error for `key`, as the contract writes it: `catalogueError('<key>')`, the key one whole
 * literal — the form `dev.py i18n audit` reads; it does not read a key inside `'_i18n:<key>'`, nor one assembled.
 */
function catalogueErrorOf(key: string): string {
    return String.raw`catalogueError\(\s*(['"])${key.replace(/\./g, '\\.')}\1\s*\)`;
}

/** Whether `source` sets the banner error to the catalogue's `key`: `error = catalogueError('<key>')`. */
function setsCatalogueError(source: string, key: string): boolean {
    return new RegExp(String.raw`\berror\s*=\s*${catalogueErrorOf(key)}`).test(source);
}

/** Whether `source` falls back to the catalogue's `key` right after the error's own message: `error = e?.message || catalogueError('<key>')`. */
function fallsBackAfterMessage(source: string, key: string): boolean {
    return new RegExp(String.raw`\berror\s*=\s*e\?\.message\s*\|\|\s*${catalogueErrorOf(key)}`).test(source);
}

/** A banner key written by hand inside the `_i18n:` prefix — `'_i18n:assetDetail.noData'` — which the audit cannot see. */
const PREFIXED_KEY = /[`'"]_i18n:[A-Za-z]/;

/** The page's helper builds the `_i18n:` form its banner resolves: `catalogueError(key)` returns `` `_i18n:${key}` ``. */
const CATALOGUE_ERROR_HELPER = /function\s+catalogueError\s*\(\s*(\w+)\b[^)]*\)[^{]*\{\s*return\s*`_i18n:\$\{\1\}`;?\s*\}/;

interface AllowedSite {
    page: Page;
    /** The whitespace-collapsed source line: the key. */
    snippet: string;
    why: string;
}

/** Hand-written names allowed to stay, each with its reason. */
const ALLOWED: readonly AllowedSite[] = [
    {
        page: 'asset',
        snippet: 'const assetLabel = assetInfo?.display_name ?? `Asset #${data.assetId}`;',
        why: 'the console label of the signal diagnostics, built only inside isDebugEnabled(): a developer log, never shown to the user; out of the lot by the coordinator’s T-FB analysis (13/10)',
    },
];

function collapse(line: string): string {
    return line.replace(/\s+/g, ' ').trim();
}

/** Every line of `source` the form matches, as `:line  source`. */
function findings(source: string, form: RegExp): string[] {
    return source.split('\n').flatMap((line, index) => (form.test(line) ? [`:${index + 1}  ${collapse(line)}`] : []));
}

/** The hand-written names of `page` that no entry of `ALLOWED` covers. */
function handWrittenNames(page: Page, source: string = SOURCES[page]): string[] {
    const allowed = new Set(ALLOWED.filter((site) => site.page === page).map((site) => site.snippet));
    return findings(source, HAND_WRITTEN_NAME).filter((finding) => !allowed.has(finding.replace(/^:\d+ {2}/, '')));
}

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** The catalogues that lack `key`, or hold it as something other than a non-empty sentence. */
function missingFrom(key: string): string[] {
    return Object.entries(CATALOGUES)
        .filter(([, catalogue]) => {
            const sentence = at(catalogue, key);
            return typeof sentence !== 'string' || sentence.trim() === '';
        })
        .map(([code]) => code);
}

describe('the comparison asset’s fallback name on the pages — the gate’s own controls (T-FB)', () => {
    it('reads the two pages: each holds its own noData banner error', () => {
        expect({asset: setsCatalogueError(SOURCES.asset, 'assetDetail.noData'), fx: SOURCES.fx.includes("'_i18n:fxDetail.noData'")}, 'a source read is not the page it names').toEqual({asset: true, fx: true});
    });

    it('premise: the asset page’s catalogueError builds the _i18n:<key> form its banner resolves', () => {
        expect({helper: CATALOGUE_ERROR_HELPER.test(SOURCES.asset), resolves: SOURCES.asset.includes("error.startsWith('_i18n:')")}, 'catalogueError no longer builds the form the banner translates: the key checks below would prove nothing about what the user reads').toEqual({
            helper: true,
            resolves: true,
        });
    });

    it('sees a hand-written name — a template or a literal — and passes the catalogue’s; sees the FX page’s key', () => {
        expect(handWrittenNames('asset', 'const a = `Asset #${id}`;\nconst b = "Asset #" + id;\nconst c = $t(\'chartSettings.signals.assetFallback\', {values: {id: String(id)}});'), 'the form does not see a hand-written name, or sees one in the catalogue’s').toEqual([
            ':1  const a = `Asset #${id}`;',
            ':2  const b = "Asset #" + id;',
        ]);
        expect(findings("$t('fxDetail.assetFallback', {values: {id}})\n$t('chartSettings.signals.assetFallback', {values: {id}})", FX_PAGE_KEY), 'the form does not see the FX page’s key, or sees the shared one').toEqual([":1  $t('fxDetail.assetFallback', {values: {id}})"]);
    });

    it('refuses an allowed site that no longer exists, and holds the shared key in every catalogue', () => {
        expect(
            ALLOWED.filter((site) => !findings(SOURCES[site.page], HAND_WRITTEN_NAME).some((finding) => finding.endsWith(`  ${site.snippet}`))).map((site) => `${site.page}: ${site.snippet}`),
            'an allowed site is gone from its page: remove its entry',
        ).toEqual([]);
        expect(missingFrom('chartSettings.signals.assetFallback'), 'the shared key is missing from a catalogue').toEqual([]);
    });

    it('sees a load failure’s English sentence in any quotes — not a console log that goes on — and a banner key only whole, through catalogueError, where the contract puts it', () => {
        const sample = ["console.error('Failed to load asset info:', e);", "error = e?.message || 'Failed to load asset info';", 'error = e?.message || "Failed to load asset info";'].join('\n');
        expect(englishLiterals(sample, 'Failed to load asset info'), 'the form does not see the sentence, or sees the console log').toEqual([":2  error = e?.message || 'Failed to load asset info';", ':3  error = e?.message || "Failed to load asset info";']);
        expect(
            {
                afterMessage: fallsBackAfterMessage("error = e?.message || catalogueError('assetDetail.loadFailed');", 'assetDetail.loadFailed'),
                alone: fallsBackAfterMessage("error = catalogueError('assetDetail.loadFailed');", 'assetDetail.loadFailed'),
                anotherKey: fallsBackAfterMessage("error = e?.message || catalogueError('assetDetail.loadFailedLater');", 'assetDetail.loadFailed'),
                prefixedString: fallsBackAfterMessage("error = e?.message || '_i18n:assetDetail.loadFailed';", 'assetDetail.loadFailed'),
                assembled: fallsBackAfterMessage("error = e?.message || catalogueError('assetDetail.' + 'loadFailed');", 'assetDetail.loadFailed'),
                set: setsCatalogueError("error = catalogueError('assetDetail.notFound');", 'assetDetail.notFound'),
                setAsAString: setsCatalogueError("error = '_i18n:assetDetail.notFound';", 'assetDetail.notFound'),
                notTheError: setsCatalogueError("const shown = catalogueError('assetDetail.notFound');", 'assetDetail.notFound'),
            },
            'the forms do not tell the contract’s call from the key alone, another key, the prefixed string, an assembled key or another variable',
        ).toEqual({afterMessage: true, alone: false, anotherKey: false, prefixedString: false, assembled: false, set: true, setAsAString: false, notTheError: false});
        expect(
            findings(["error = '_i18n:assetDetail.noData';", 'return `_i18n:${key}`;', "return error.startsWith('_i18n:') ? $t(error.slice(6)) : error;"].join('\n'), PREFIXED_KEY),
            'the form does not see a key written inside the prefix, or sees the helper’s template or the banner’s test',
        ).toEqual([":1  error = '_i18n:assetDetail.noData';"]);
    });
});

describe('the comparison asset’s fallback name on the pages (T-FB)', () => {
    it('the asset page writes no «Asset #…» by hand, and names an unknown asset with the shared key, chartSettings.signals.assetFallback', () => {
        expect(
            {handWritten: handWrittenNames('asset'), namesTheSharedKey: SOURCES.asset.includes(SHARED_KEY)},
            'the asset page still writes «Asset #…» in English: leave the name to AssetComparisonSignal, or read chartSettings.signals.assetFallback; the not-found error is catalogueError(’assetDetail.notFound’)',
        ).toEqual({handWritten: [], namesTheSharedKey: true});
    });

    it('the FX page writes no «Asset #…» by hand either (guard)', () => {
        expect(handWrittenNames('fx'), 'the FX page writes «Asset #…» by hand').toEqual([]);
    });

    it('the FX page names a comparison asset with the shared key, chartSettings.signals.assetFallback, and no longer with fxDetail.assetFallback', () => {
        expect({oldKey: findings(SOURCES.fx, FX_PAGE_KEY), namesTheSharedKey: SOURCES.fx.includes(SHARED_KEY)}, 'the FX page still reads its own key for the comparison asset’s name').toEqual({oldKey: [], namesTheSharedKey: true});
    });

    it('the asset page’s not-found error is the catalogue’s: error = catalogueError(’assetDetail.notFound’), the key whole, a key every catalogue holds', () => {
        expect({error: setsCatalogueError(SOURCES.asset, 'assetDetail.notFound'), missingFrom: missingFrom('assetDetail.notFound')}, 'the not-found error is not catalogueError with its key whole — so the audit cannot see the key — or its key is missing from a catalogue').toEqual({
            error: true,
            missingFrom: [],
        });
    });

    it('the asset page’s two load failures fall back, right after the error’s own message, to the catalogue — e?.message || catalogueError(’assetDetail.loadFailed’ / ’assetDetail.pricesLoadFailed’), keys every catalogue holds — and their English sentences are gone', () => {
        const written = Object.fromEntries(
            LOAD_FAILURES.map(({english, key}) => [
                key,
                {
                    english: englishLiterals(SOURCES.asset, english),
                    fallsBackToTheKey: fallsBackAfterMessage(SOURCES.asset, key),
                    missingFrom: missingFrom(key),
                },
            ]),
        );

        expect(written, 'a load failure falls back to an English sentence written in the page — or not right after e?.message, or not through catalogueError with its key whole, or to a key missing from a catalogue').toEqual(
            Object.fromEntries(LOAD_FAILURES.map(({key}) => [key, {english: [], fallsBackToTheKey: true, missingFrom: []}])),
        );
    });

    it('the asset page writes no banner key inside the _i18n: prefix: every banner error goes through catalogueError, its key whole, so the audit sees it (guard)', () => {
        expect(findings(SOURCES.asset, PREFIXED_KEY), 'a banner key is written inside the _i18n: prefix, where the catalogue audit cannot see it: write catalogueError(’<key>’)').toEqual([]);
    });
});
