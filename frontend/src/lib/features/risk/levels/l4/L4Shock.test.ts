// @vitest-environment jsdom
//
// The docblock above is load-bearing (L4Replay.test.ts tells the long story): `render()` needs a
// `document`, and under the default `node` environment a `.svelte.ts` compiles but `$effect` never
// fires, so the controller below would hand the block a frozen snapshot and an absence would pass on
// a page that never rendered. `assertEffectsRun()` in the harness turns that into a message.
/**
 * L4Shock — component test (Vitest + jsdom), T-SHK: D5 of the 02's README («Difetti noti»), 13/10/2026.
 *
 * The hypothetical shock of L4 answers in the scenario table (`TornadoChart`). Until T-SHK the table
 * spoke the engine's vocabulary: every row a raw bucket id (`ETF_MONETARY`, `Financials`, `ITA`), under
 * a first column headed «Asset», and a row at 0.0% for every bucket of the preset the portfolio does not
 * hold — fifteen of the eighteen of «Global risk-off». The detail editor wrote the same ids as its text,
 * its `title` and its fields' accessible names. What is pinned here:
 *
 *   1. **The rows are named as the legacy panel names them** (`stressBucketLabel`,
 *      `RiskAnalysisPanel.svelte:357-365`): `Other` → common.other; `european_union` →
 *      risk.stress.europeanUnion; an asset class → assets.types.<ID>; a sector → its emoji and
 *      sectors.<key> (`sectorI18nKey`); a country → its flag and its name, from the country cache. The
 *      dimension is the answer's (`output.dimension`): the sector and geography answers are put on
 *      screen with no preset chosen, while the block's own editor dimension is still `asset_class`.
 *   2. **A code nobody knows is shown as written** — neither the catalogue nor the reference data has
 *      it — never as a catalogue key, and never behind a white flag. Each case sets one beside a known
 *      code, which is what makes it red today rather than green by accident.
 *   3. **The first column is headed by the dimension**: risk.stress.dimensions.<dimension>, read off
 *      the header of the column that holds the rows' names.
 *   4. **A bucket nobody holds is not a row**, and a portfolio that holds none of them shows no table,
 *      while its total stays. The rule itself (a share of exactly 0, weights known) is pinned by
 *      `scenarioHelpers.test.ts`; here, that the block draws what the helper keeps.
 *   5. **The detail editor** names the chosen scenario's buckets by the scenario's dimension — the words
 *      beside each field, their `title` and the field's `aria-label` — and keeps the id in
 *      `data-bucket-id`.
 *   6. **A language switch in place** rewrites the rows, the header and the editor, and a country's name
 *      is read again in the new language.
 *
 * **How a label is asserted without pinning one.** Every expected label is computed when it is
 * asserted, in the language the app is in (Italian; French after the switch): its words from the shipped
 * catalogue through the same `$_` the block uses, a country's flag and name from the reference data this
 * file feeds the country cache with, a sector's emoji from the answer this file feeds the sector cache
 * with. `expectedLabel` restates the contract once, and the harness proves the restatement can fail:
 * every label differs from its id, every dimension from «Asset», and the switch's subjects from one
 * language to the other.
 *
 * **The reference caches are the real ones**, fed through the two utility endpoints of `$lib/api` (a
 * partial mock: the rest of the module is the real one). Before each case the country cache holds
 * English names, a language no case runs in, so an Italian or French name on screen can only come from
 * the block loading the names of its own language — as the legacy panel does (`ensureCountriesLoaded`
 * per language, then a counter that redraws the labels). The sectors endpoint answers real emoji, the
 * backend's own, and the sector cache has none until it loads them (since DV no emoji is written in the
 * frontend): a sector row matches its label only once the block has loaded the sectors and redrawn.
 * Nothing else in this file loads them.
 *
 * **Today** every case below is red except the harness. The switch cases fail first on their Italian
 * barrier, for want of any label at all; their own subject — the redraw — is exercised once labels exist.
 *
 * Left elsewhere: which rows a payload yields and in which order (`scenarioHelpers.test.ts`), the table
 * and its default first header, «Asset», which the replay keeps (`TornadoChart.test.ts`), and the shock
 * end to end (`portfolio/risk-analysis.spec.ts`).
 *
 * Registered in `scripts/test_runner/_frontend_portfolio.py`, in the Vitest list of
 * `front_portfolio_risk_levels_component` (action `risk-levels-component`), next to `L4Replay.test.ts`.
 *
 * ⚠️ Every weight, figure and holding below is invented; the shapes are the backend's
 * (`risk_plugins/stress/plugin.py::_hypothetical`, `_resolve_bucket`). `WARRANT`, `Quantum Computing`
 * and `XKX` are codes invented to be unknown to the catalogue and to the reference data.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {get} from 'svelte/store';
import {waitLocale} from 'svelte-i18n';

const fetchRiskCatalog = vi.hoisted(() => vi.fn());
const fetchRiskScenarioCatalog = vi.hoisted(() => vi.fn());
const queryRisk = vi.hoisted(() => vi.fn());
const invalidateRisk = vi.hoisted(() => vi.fn());

vi.mock('$lib/features/risk/riskStore.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/risk/riskStore.svelte')>();
    return {
        ...actual,
        fetchRiskCatalog,
        fetchRiskScenarioCatalog,
        queryRisk,
        invalidateRisk,
        // Capability gating belongs to the panel, not to this block: stubbing it keeps the subject
        // singular. `queryRisk` is scripted per question below, so no backend is ever reached.
        hasRiskCapability: () => true,
    };
});

/**
 * The reference data the labels read: the two utility endpoints the country and sector caches load
 * from, answered by this file. The rest of `$lib/api` is the real one, and so are the two caches.
 */
const reference = vi.hoisted(() => ({countries: vi.fn(), sectors: vi.fn()}));

vi.mock('$lib/api', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/api')>();
    return {
        ...actual,
        zodiosApi: {
            ...actual.zodiosApi,
            list_countries_api_v1_utilities_countries_get: reference.countries,
            list_sectors_api_v1_utilities_sectors_get: reference.sectors,
        },
    };
});

import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {assertEffectsRun, effectRoot} from '$test/runes.svelte';
import {schemas} from '$lib/api';
import {_, locale, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import type {RiskQueryRequest, RiskScenarioDimension} from '$lib/features/risk/riskRequest';
import type {RiskResultMetadata, RiskStressOutput} from '$lib/features/risk/riskTypes';
import {currentLanguage} from '$lib/stores/app/language';
import {ensureCountriesLoaded, getCountryInfo} from '$lib/stores/reference/countryStore';
import {createRiskPanelController, type RiskControllerInputs, type RiskPanelController} from '$lib/features/risk/riskPanelController.svelte';
import type {RiskAnalyticResult} from '$lib/features/risk/riskStore.svelte';
import {sectorI18nKey} from '$lib/utils/assetTypes';
import L4Shock from './L4Shock.svelte';

type Dimension = RiskScenarioDimension;
type ShockImpact = NonNullable<RiskStressOutput['impacts']>[number];
type ShockSlice = NonNullable<ShockImpact['bucket_audit']>[number];
type Shocks = Readonly<Record<string, number>>;

const DIMENSIONS: readonly Dimension[] = ['asset_class', 'sector', 'geography'];

/** The language the app is in for every case; the one the switch goes to; the one the country cache holds before each case. */
const UI: SupportedLocale = 'it';
const SWITCH_TO: SupportedLocale = 'fr';
const PRIMED: SupportedLocale = 'en';

const TORNADO = 'risk-shock-tornado';
const WINDOW = {start: '2026-01-02', end: '2026-10-09'};
/** A notional portfolio value: the amounts a weighted answer carries, which no bucket row reads. */
const SCOPE_VALUE = 50_000;

const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

// ---------------------------------------------------------------------------
// Reference data
// ---------------------------------------------------------------------------

/**
 * The countries endpoint's answer, per language: Babel's names on the server, invented here. `XKX` is
 * deliberately absent — a code the reference data does not know.
 */
const COUNTRIES: Readonly<Record<string, {iso2: string; flag: string; names: Readonly<Record<SupportedLocale, string>>}>> = {
    ITA: {iso2: 'IT', flag: '🇮🇹', names: {en: 'Italy', it: 'Italia', fr: 'Italie', es: 'Italia'}},
    DEU: {iso2: 'DE', flag: '🇩🇪', names: {en: 'Germany', it: 'Germania', fr: 'Allemagne', es: 'Alemania'}},
    USA: {iso2: 'US', flag: '🇺🇸', names: {en: 'United States', it: 'Stati Uniti', fr: 'États-Unis', es: 'Estados Unidos'}},
};

/**
 * The sectors endpoint's answer, as the backend writes it (`SectorListResponse`): the sectors it lists with their
 * emoji — the backend's own glyphs (`SECTOR_EMOJI`, `backend/app/utils/asset/sector.py`) — the two allocation buckets,
 * and the glyph of a key it lists nowhere. A fresh copy per call: the cache keeps what it is handed.
 */
function sectorsAnswer() {
    return {
        items: [
            {key: 'Financials', emoji: '🏦'},
            {key: 'Health Care', emoji: '🏥'},
            {key: 'Technology', emoji: '💻'},
            {key: 'Energy', emoji: '⚡'},
            {key: 'Other', emoji: '📦'},
        ],
        buckets: [
            {key: 'Liquidity', emoji: '💰'},
            {key: 'Unknown', emoji: '❓'},
        ],
        fallback_emoji: '❓',
    };
}

/** The emoji the sector cache answers for a key once it holds `sectorsAnswer()`: a listed one, or the fallback. */
function answeredSectorEmoji(key: string): string {
    const answer = sectorsAnswer();
    return [...answer.items, ...answer.buckets].find((entry) => entry.key === key)?.emoji ?? answer.fallback_emoji;
}

// ---------------------------------------------------------------------------
// Answers, written the way `risk_plugins/stress/plugin.py::_hypothetical` writes them
// ---------------------------------------------------------------------------

/** One line of a holding's `bucket_audit`; its contribution is the product `schemas/risk.py` validates. */
function slice(exposure_bucket_id: string, exposure: number, candidate_bucket_ids: string[], applied_bucket_id: string | null, bucket_shock: number, rule: ShockSlice['rule']): ShockSlice {
    return {exposure_bucket_id, exposure, candidate_bucket_ids, applied_bucket_id, bucket_shock, shock_contribution: exposure * bucket_shock, rule};
}

/** A holding of a weighted (portfolio) scope: its shock the sum of its slices', its contribution its weight times that. */
function holding(asset_id: number, weight: number, dimension: Dimension, bucket_audit: ShockSlice[]): ShockImpact {
    const shock_return = bucket_audit.reduce((sum, line) => sum + line.shock_contribution, 0);
    return {
        asset_id,
        weight,
        shock_return,
        contribution_return: weight * shock_return,
        impact_amount: (weight * SCOPE_VALUE * shock_return).toFixed(2),
        dimension,
        metadata_fallback: false,
        bucket_audit,
    };
}

/** A holding wholly in one asset class: applied directly when the class is a configured bucket, else to none (`unconfigured_zero`). */
function classHolding(asset_id: number, weight: number, assetClass: string, shocks: Shocks): ShockImpact {
    const line = assetClass in shocks ? slice(assetClass, 1, [assetClass], assetClass, shocks[assetClass], 'direct') : slice(assetClass, 1, [], null, 0, 'unconfigured_zero');
    return holding(asset_id, weight, 'asset_class', [line]);
}

/** The output around those holdings: one configured bucket per shock, ordered by id, with Σ wᵢ·eᵢ_b·shock_b as its contribution. */
function shockOutput(dimension: Dimension, shocks: Shocks, impacts: ShockImpact[]): RiskStressOutput {
    const configured_buckets = Object.keys(shocks)
        .sort()
        .map((bucket_id) => {
            const applied = impacts.flatMap((impact) => (impact.bucket_audit ?? []).filter((line) => line.applied_bucket_id === bucket_id).map((line) => ({impact, line})));
            return {
                bucket_id,
                shock: shocks[bucket_id],
                applied_asset_count: new Set(applied.map(({impact}) => impact.asset_id)).size,
                asset_exposure_total: applied.reduce((sum, {line}) => sum + line.exposure, 0),
                contribution_return: applied.reduce((sum, {impact, line}) => sum + Number(impact.weight) * line.shock_contribution, 0),
            };
        });
    const portfolio_return = impacts.reduce((sum, impact) => sum + Number(impact.contribution_return), 0);
    return {kind: 'stress', method: 'hypothetical', dimension, portfolio_return, impact_amount: (SCOPE_VALUE * portfolio_return).toFixed(2), classification_coverage: 1, impacts, configured_buckets};
}

function metadata(): RiskResultMetadata {
    return {
        analyzed_range: {start: WINDOW.start, end: WINDOW.end},
        frequency: 'daily',
        n_observations: 1,
        calendar_days: 0,
        coverage: 1,
        currency: 'EUR',
        scope: 'portfolio',
        mode: 'current_composition',
        return_basis: 'current_composition_backtest',
        algorithm_version: 'test-l4-shock',
        computed_at: '2026-10-13T01:00:00+00:00',
    };
}

function shockResult(output: RiskStressOutput): RiskAnalyticResult {
    return {instance_id: 'single-stress', analytic_code: 'stress', status: 'ok', output, metadata: metadata(), warnings: []};
}

/** «Global risk-off» as `scenario_catalog/built_in/hypothetical/global_risk_off.yml` ships it: eighteen asset classes. */
const GLOBAL_RISK_OFF: Shocks = {
    STOCK: -0.2,
    ETF: -0.15,
    BOND: -0.05,
    CRYPTO: -0.3,
    FUND: -0.15,
    CROWDFUND: -0.1,
    HOLD: -0.05,
    COMMODITY: -0.12,
    REAL_ESTATE: -0.15,
    INDEX: -0.2,
    OTHER: 0,
    ETF_STOCK: -0.2,
    ETF_BOND: -0.05,
    ETF_COMMODITY: -0.12,
    ETF_REAL_ESTATE: -0.15,
    ETF_CRYPTO: -0.3,
    ETF_MONETARY: 0,
    CROWDFUND_REAL_ESTATE: -0.1,
};

/** «Banking crisis» as `banking_crisis.yml` ships it. */
const BANKING_CRISIS: Shocks = {Financials: -0.4, Other: 0};

/** A geography shock a host scenario could name: one country, the built-in group, and the Other every geography shock carries. */
const ITALY_AND_EU: Shocks = {ITA: -0.25, european_union: -0.2, Other: 0};

/**
 * «Global risk-off» over a portfolio holding three of its classes — a stock, a money-market ETF (shocked
 * by 0, so a held bucket with a 0 contribution) and real-estate crowdfunding — and 20% cash.
 */
const RISK_OFF_ANSWER = shockOutput('asset_class', GLOBAL_RISK_OFF, [classHolding(101, 0.4, 'STOCK', GLOBAL_RISK_OFF), classHolding(102, 0.15, 'ETF_MONETARY', GLOBAL_RISK_OFF), classHolding(103, 0.25, 'CROWDFUND_REAL_ESTATE', GLOBAL_RISK_OFF)]);
/** Its rows, worst first: −8%, −2.5%, and the held ETF at 0. */
const RISK_OFF_ROWS = ['bucket:STOCK', 'bucket:CROWDFUND_REAL_ESTATE', 'bucket:ETF_MONETARY'];

/** «Banking crisis» over a bank and a fund split between Financials and Technology, which the scenario leaves to Other. */
const BANKING_ANSWER = shockOutput('sector', BANKING_CRISIS, [
    holding(201, 0.3, 'sector', [slice('Financials', 1, ['Financials', 'Other'], 'Financials', -0.4, 'direct')]),
    holding(202, 0.5, 'sector', [slice('Financials', 0.2, ['Financials', 'Other'], 'Financials', -0.4, 'direct'), slice('Technology', 0.8, ['Other'], 'Other', 0, 'other')]),
]);
const BANKING_ROWS = ['bucket:Financials', 'bucket:Other'];

/** The geography shock over an Italian stock and a fund half German, half American: a country, the group, and Other. */
const ITALY_EU_ANSWER = shockOutput('geography', ITALY_AND_EU, [
    holding(301, 0.3, 'geography', [slice('ITA', 1, ['ITA', 'european_union', 'Other'], 'ITA', -0.25, 'country')]),
    holding(302, 0.4, 'geography', [slice('DEU', 0.5, ['european_union', 'Other'], 'european_union', -0.2, 'geography_group'), slice('USA', 0.5, ['Other'], 'Other', 0, 'other')]),
]);
const ITALY_EU_ROWS = ['bucket:ITA', 'bucket:european_union', 'bucket:Other'];

/** A portfolio of bonds under two equity classes: nobody holds either bucket. */
const NOTHING_HELD: Shocks = {ETF: -0.25, STOCK: -0.35};
const NOTHING_HELD_ANSWER = shockOutput('asset_class', NOTHING_HELD, [classHolding(501, 0.6, 'BOND', NOTHING_HELD), classHolding(502, 0.3, 'BOND', NOTHING_HELD)]);

interface UnknownCase {
    dimension: Dimension;
    known: string;
    unknown: string;
    output: RiskStressOutput;
    rows: string[];
}

/** One answer per dimension with a code nobody knows, beside a known one. Every bucket is held. */
const UNKNOWN_CASES: readonly UnknownCase[] = [
    {
        dimension: 'asset_class',
        known: 'STOCK',
        unknown: 'WARRANT',
        output: shockOutput('asset_class', {STOCK: -0.2, WARRANT: -0.4}, [classHolding(401, 0.5, 'STOCK', {STOCK: -0.2, WARRANT: -0.4}), classHolding(402, 0.1, 'WARRANT', {STOCK: -0.2, WARRANT: -0.4})]),
        rows: ['bucket:STOCK', 'bucket:WARRANT'],
    },
    {
        // Two words: the catalogue key is `sectorI18nKey`'s, sectors.HealthCare.
        dimension: 'sector',
        known: 'Health Care',
        unknown: 'Quantum Computing',
        output: shockOutput('sector', {'Health Care': -0.1, 'Quantum Computing': -0.5, Other: 0}, [
            holding(411, 0.4, 'sector', [slice('Health Care', 1, ['Health Care', 'Other'], 'Health Care', -0.1, 'direct')]),
            holding(412, 0.1, 'sector', [slice('Quantum Computing', 1, ['Quantum Computing', 'Other'], 'Quantum Computing', -0.5, 'direct')]),
            holding(413, 0.2, 'sector', [slice('Energy', 1, ['Other'], 'Other', 0, 'other')]),
        ]),
        rows: ['bucket:Health Care', 'bucket:Quantum Computing', 'bucket:Other'],
    },
    {
        dimension: 'geography',
        known: 'ITA',
        unknown: 'XKX',
        output: shockOutput('geography', {ITA: -0.25, XKX: -0.3, Other: 0}, [
            holding(421, 0.3, 'geography', [slice('ITA', 1, ['ITA', 'Other'], 'ITA', -0.25, 'country')]),
            holding(422, 0.05, 'geography', [slice('XKX', 1, ['XKX', 'Other'], 'XKX', -0.3, 'country')]),
            holding(423, 0.2, 'geography', [slice('USA', 1, ['Other'], 'Other', 0, 'other')]),
        ]),
        rows: ['bucket:ITA', 'bucket:XKX', 'bucket:Other'],
    },
];

// ---------------------------------------------------------------------------
// The scenario catalogue, shaped on the built-in YAML so the strict generated Zod accepts it
// ---------------------------------------------------------------------------

type PresetId = 'global_risk_off' | 'banking_crisis' | 'host_italy_eu';

interface Preset {
    source: 'built_in' | 'host';
    /** This test's own data, not a catalogue sentence: the presets are picked by id. */
    name: string;
    dimension: Dimension;
    shocks: Shocks;
    answer: RiskStressOutput;
}

const PRESETS: Readonly<Record<PresetId, Preset>> = {
    global_risk_off: {source: 'built_in', name: 'Global risk-off', dimension: 'asset_class', shocks: GLOBAL_RISK_OFF, answer: RISK_OFF_ANSWER},
    banking_crisis: {source: 'built_in', name: 'Banking crisis', dimension: 'sector', shocks: BANKING_CRISIS, answer: BANKING_ANSWER},
    host_italy_eu: {source: 'host', name: 'Synthetic Italy and EU shock (invented)', dimension: 'geography', shocks: ITALY_AND_EU, answer: ITALY_EU_ANSWER},
};

function hypotheticalEntry(id: PresetId) {
    const preset = PRESETS[id];
    return {
        source: preset.source,
        source_file: `hypothetical/${id}.yml`,
        scenario: {
            schema_version: 1,
            id,
            kind: 'hypothetical_shock',
            tags: [preset.dimension],
            name: {en: preset.name},
            description: {en: `${preset.name}: a description.`},
            allowed_dimensions: [preset.dimension],
            defaults: {dimension: preset.dimension, bucket_shocks: {...preset.shocks}},
            editable: {dimension: false, bucket_shocks: true, manual_overrides: true},
            limits: {minimum_shock: -1, maximum_shock: 1, maximum_buckets: 100},
        },
    };
}

const SCENARIO_CATALOG = {
    items: (Object.keys(PRESETS) as PresetId[]).map(hypotheticalEntry),
    // As `built_in/geography/european_union.yml` ships it, members abridged.
    geography_groups: [{schema_version: 1, id: 'european_union', name: {en: 'European Union', it: 'Unione Europea', fr: 'Union européenne', es: 'Unión Europea'}, members: ['DEU', 'FRA', 'ITA']}],
};

// ---------------------------------------------------------------------------
// Reading the catalogue, and the contract restated
// ---------------------------------------------------------------------------

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** A catalogue sentence as the block words it: `$_`, in the language the app is in. Never a literal. */
function t(key: string): string {
    return normalize(get(_)(key));
}

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** The language the app is in. The harness proves the catalogue speaks it too. */
function lang(): SupportedLocale {
    return get(currentLanguage);
}

/** The sentence a key resolves to, or `null` when no catalogue the runtime reads — the language or its fallback — holds it. */
function shipped(key: string): string | null {
    return typeof at(CATALOGUES[lang()], key) === 'string' || typeof at(CATALOGUES.en, key) === 'string' ? t(key) : null;
}

/**
 * The name a bucket must read in the language the app is in — the contract, restated once: the legacy
 * panel's `stressBucketLabel`, plus the rule that a code nobody knows is shown as written. A sector with
 * no emoji reads its name alone, no leading space (DV-6); the emoji here are the answer's, which lists
 * one for every sector, so each expected sector label is the one drawn once the sectors have loaded.
 */
function expectedLabel(bucket: string, dimension: Dimension): string {
    if (bucket === 'Other') return t('common.other');
    if (bucket === 'european_union') return t('risk.stress.europeanUnion');
    if (dimension === 'asset_class') return shipped(`assets.types.${bucket}`) ?? bucket;
    if (dimension === 'sector') {
        const name = shipped(`sectors.${sectorI18nKey(bucket)}`);
        if (name === null) return bucket;
        const emoji = answeredSectorEmoji(bucket);
        return emoji ? `${emoji} ${name}` : name;
    }
    const country = COUNTRIES[bucket];
    return country ? `${country.flag} ${country.names[lang()]}` : bucket;
}

function bucketOf(key: string): string {
    return key.startsWith('bucket:') ? key.slice('bucket:'.length) : key;
}

/** What each of these rows must read, by key. */
function expectedRows(dimension: Dimension, keys: readonly string[]): Record<string, string> {
    return Object.fromEntries(keys.map((key) => [key, expectedLabel(bucketOf(key), dimension)]));
}

interface EditorEntry {
    /** The words beside the field: the text of the elements, other than the field, that carry a `title`. */
    text: string;
    /** The distinct titles the entry carries. */
    title: string;
    ariaLabel: string;
}

/** What the detail editor must show for a scenario, by bucket id: its name, three times. */
function expectedEditor(dimension: Dimension, shocks: Shocks): Record<string, EditorEntry> {
    return Object.fromEntries(
        Object.keys(shocks).map((bucket) => {
            const label = expectedLabel(bucket, dimension);
            return [bucket, {text: label, title: label, ariaLabel: label}];
        }),
    );
}

// ---------------------------------------------------------------------------
// Reading the block
// ---------------------------------------------------------------------------

/** The rows' keys, in the order on screen. */
function rowKeys(): string[] {
    return screen.queryAllByTestId(`${TORNADO}-row`).map((row) => row.getAttribute('data-row-key') ?? '');
}

/** A row's own element, which must be exactly one. */
function rowMarker(key: string): HTMLElement {
    const markers = screen.queryAllByTestId(`${TORNADO}-row`).filter((row) => row.getAttribute('data-row-key') === key);
    if (markers.length !== 1) throw new Error(`row ${key} is drawn by ${markers.length} elements; the table draws ${JSON.stringify(rowKeys())}`);
    return markers[0];
}

/** The name each of these rows shows, by key. */
function rowLabels(keys: readonly string[]): Record<string, string> {
    return Object.fromEntries(keys.map((key) => [key, normalize(rowMarker(key).textContent)]));
}

/**
 * The header of the column that holds the rows' names, found through the position of a row's cell in
 * its row — never a fixed index, never the column id — after checking that column is the first.
 */
function nameColumnHeader(key: string): string {
    const root = screen.getByTestId(TORNADO);
    const cell = rowMarker(key).closest('td');
    const headerRow = root.querySelector('th[data-testid^="dt-header-"]')?.parentElement;
    if (!cell?.parentElement || !headerRow) throw new Error(`row ${key} is not drawn in a headed table`);
    const header = headerRow.children[[...cell.parentElement.children].indexOf(cell)];
    if (!header) throw new Error(`the column of row ${key} has no header`);
    if (header !== headerRow.querySelector('th[data-testid^="dt-header-"]')) throw new Error(`the rows' names are not in the first column: they sit under ${header.getAttribute('data-testid')}`);
    return normalize(header.textContent);
}

/** The part of the editor that belongs to one field: its widest ancestor holding no other field. */
function entryOf(editor: HTMLElement, field: HTMLElement): HTMLElement {
    let entry: HTMLElement = field;
    while (entry.parentElement && entry.parentElement !== editor && entry.parentElement.querySelectorAll('[data-testid="risk-shock-bucket"]').length === 1) entry = entry.parentElement;
    return entry;
}

/** Every bucket the detail editor lists, by its `data-bucket-id`: the words beside its field, their title and the field's accessible name. */
function editorEntries(): Record<string, EditorEntry> {
    const editor = screen.getByTestId('risk-shock-buckets');
    return Object.fromEntries(
        within(editor)
            .getAllByTestId('risk-shock-bucket')
            .map((field) => {
                const entry = entryOf(editor, field);
                const titled = [...entry.querySelectorAll('[title]')];
                return [
                    field.getAttribute('data-bucket-id') ?? '',
                    {
                        text: titled
                            .filter((node) => node !== field)
                            .map((node) => normalize(node.textContent))
                            .join(' | '),
                        title: [...new Set(titled.map((node) => normalize(node.getAttribute('title'))))].join(' | '),
                        ariaLabel: normalize(field.getAttribute('aria-label')),
                    },
                ];
            }),
    );
}

// ---------------------------------------------------------------------------
// Mounting and driving
// ---------------------------------------------------------------------------

function controllerInputs(): RiskControllerInputs {
    return {scope: {kind: 'portfolio'}, dateStart: WINDOW.start, dateEnd: WINDOW.end, targetCurrency: 'EUR', appliedRiskFreePercent: 0, refreshVersion: 0};
}

const stops: (() => void)[] = [];

/**
 * A real controller, optionally carrying one shock answer, and the block on top. The `flushSync()` lets
 * the controller's first effect apply the base signature — which discards every on-demand answer —
 * before the answer is seeded.
 */
function mount(result: RiskAnalyticResult | null = null): RiskPanelController {
    const {value: controller, stop} = effectRoot(() => createRiskPanelController(() => controllerInputs()));
    stops.push(stop);
    flushSync();
    if (result) controller.setResult('stress', result);
    render(L4Shock, {props: {controller, assetNames: {}, currency: 'EUR'}});
    return controller;
}

/** Every shock question put to `queryRisk`, as asked; and the answer the next one gets. */
const stress = {
    asked: [] as Record<string, unknown>[],
    next: null as RiskStressOutput | null,
};

/** Choose a preset as a reader does — one click — and end on its answer being on screen. */
async function choosePreset(controller: RiskPanelController, id: PresetId): Promise<void> {
    const preset = PRESETS[id];
    stress.next = preset.answer;
    await controller.loadScenarioCatalog();
    flushSync();
    const button = within(screen.getByTestId('risk-shock-presets'))
        .queryAllByTestId('risk-shock-preset')
        .find((node) => node.getAttribute('data-preset-id') === id);
    if (!button) throw new Error(`the block offers no preset ${id}: the scenario catalogue did not reach it`);
    await fireEvent.click(button);
    await waitFor(() => expect(controller.stressResult, `the answer to ${id} never reached the block`).not.toBeNull());
    expect(stress.asked[stress.asked.length - 1], `premise: choosing ${id} did not ask its own question`).toEqual({method: 'hypothetical', dimension: preset.dimension, bucket_shocks: {...preset.shocks}});
    flushSync();
}

/** Open the detail editor, clicking only when it is closed, and end on it being open. */
async function openEditor(): Promise<void> {
    const toggle = screen.getByTestId('risk-shock-detail-toggle');
    if (toggle.getAttribute('aria-expanded') !== 'true') await fireEvent.click(toggle);
    expect(toggle, 'the detail toggle did not open the editor').toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByTestId('risk-shock-buckets')).toBeInTheDocument();
}

/** Switch the language in place, as the header's selector does: the store and the catalogue together. */
function switchLanguage(language: SupportedLocale): void {
    currentLanguage.set(language);
    flushSync();
    expect(get(locale), `premise: the catalogue did not follow the switch to ${language}`).toBe(language);
}

/**
 * Put the country cache in the primed language. A load the previous case started may still be in
 * flight, and the cache hands it back instead of loading: asking again once it has landed loads the
 * primed names. Bounded, and it says so when it cannot.
 */
async function primeCountries(): Promise<void> {
    for (let attempt = 0; attempt < 3; attempt += 1) {
        await ensureCountriesLoaded(PRIMED);
        if (getCountryInfo('ITA').name === COUNTRIES.ITA.names[PRIMED]) return;
    }
    throw new Error(`the country cache could not be put back in ${PRIMED}: it answers ${JSON.stringify(getCountryInfo('ITA'))}`);
}

beforeAll(async () => {
    await setupI18n(UI);
    // The switch goes to French in place: its catalogue is loaded here, so the switch is synchronous,
    // as it is in the app for a language already visited.
    await waitLocale(SWITCH_TO);
});

beforeEach(async () => {
    // Set before anything is mounted, so no block reacts to it.
    currentLanguage.set(UI);
    stress.asked = [];
    stress.next = null;
    fetchRiskCatalog.mockReset().mockResolvedValue({items: []});
    fetchRiskScenarioCatalog.mockReset().mockResolvedValue(SCENARIO_CATALOG);
    invalidateRisk.mockReset();
    queryRisk.mockReset().mockImplementation(async (request: RiskQueryRequest) => {
        const analytic = request.analytics.find((candidate) => candidate.analytic_code === 'stress');
        // The base wave the controller fires on mount is answered empty and never counted.
        if (!analytic) return {items: []};
        stress.asked.push((analytic.parameters ?? {}) as Record<string, unknown>);
        if (!stress.next) throw new Error('the shock was asked, and this test scripted no answer for it');
        return {items: [shockResult(stress.next)]};
    });
    reference.countries.mockReset().mockImplementation(async (config?: {queries?: {language?: string}}) => {
        const language = (config?.queries?.language ?? 'en') as SupportedLocale;
        return {
            language,
            items: Object.entries(COUNTRIES).map(([iso3, country]) => ({iso3, iso2: country.iso2, name: country.names[language] ?? country.names.en, flag_emoji: country.flag})),
        };
    });
    reference.sectors.mockReset().mockImplementation(async () => sectorsAnswer());
    await primeCountries();
});

afterEach(() => {
    // Unmount first: a language reset with the block still mounted would start a load the next case inherits.
    cleanup();
    while (stops.length > 0) stops.pop()?.();
});

// ---------------------------------------------------------------------------
// The harness
// ---------------------------------------------------------------------------

describe('L4Shock — the harness itself', () => {
    it('runs effects, and the app and the catalogue speak the same language', () => {
        expect(() => assertEffectsRun()).not.toThrow();
        expect(lang(), 'premise: the cases run in Italian').toBe(UI);
        expect(get(locale), 'the app language and the catalogue locale disagree: a label could be worded in one and expected in the other').toBe(lang());
    });

    it('has every word the labels and the headers are made of, in every catalogue, and none for the codes invented to be unknown', () => {
        const words = [
            'common.other',
            'risk.stress.europeanUnion',
            'risk.levels.l4.table.asset',
            ...DIMENSIONS.map((dimension) => `risk.stress.dimensions.${dimension}`),
            ...Object.keys(GLOBAL_RISK_OFF).map((id) => `assets.types.${id}`),
            ...['Financials', 'Health Care'].map((sector) => `sectors.${sectorI18nKey(sector)}`),
        ];
        // One line per key and locale, so a red names every sentence that is missing.
        const missing = SUPPORTED_LOCALES.flatMap((code) => words.filter((key) => typeof at(CATALOGUES[code], key) !== 'string').map((key) => `${code}: ${key}`));
        expect(missing, 'a word the labels or the headers are made of is missing from a catalogue').toEqual([]);
        // svelte-i18n echoes the id back on a miss, and so would the block: both sides would "agree".
        for (const key of words) expect(t(key), `${key} does not resolve: the catalogue is not loaded`).not.toBe(key);

        const unknownWords = ['assets.types.WARRANT', `sectors.${sectorI18nKey('Quantum Computing')}`];
        const present = SUPPORTED_LOCALES.flatMap((code) => unknownWords.filter((key) => at(CATALOGUES[code], key) !== undefined).map((key) => `${code}: ${key}`));
        expect(present, 'a code invented to be unknown has a translation: the cases about unknown codes would prove nothing').toEqual([]);
        expect(Object.keys(COUNTRIES), 'XKX is meant to be unknown to the reference data').not.toContain('XKX');
    });

    it('passes every answer and the metadata through the generated contract, which the block parses them with', () => {
        // `riskOutput` parses with Zod and answers null on a miss: a fixture that failed it would render
        // an empty block, in which every absence below would be trivially true.
        const outputs = {RISK_OFF_ANSWER, BANKING_ANSWER, ITALY_EU_ANSWER, NOTHING_HELD_ANSWER, ...Object.fromEntries(UNKNOWN_CASES.map((unknownCase) => [unknownCase.unknown, unknownCase.output]))};
        const failing = Object.entries(outputs)
            .filter(([, output]) => !schemas.RiskStressOutput.safeParse(output).success)
            .map(([name]) => name);
        expect(failing, 'these answers fail the generated RiskStressOutput').toEqual([]);
        expect(schemas.RiskResultMetadata.safeParse(metadata()).success, 'the metadata fails the generated RiskResultMetadata').toBe(true);
        expect(
            (Object.keys(PRESETS) as PresetId[]).filter((id) => !schemas.RiskHypotheticalShockScenario.safeParse(hypotheticalEntry(id).scenario).success),
            'these presets fail the generated RiskHypotheticalShockScenario: the block would never offer them',
        ).toEqual([]);
    });

    it('feeds the real country cache from the countries endpoint, per language: the names a country label reads', async () => {
        for (const language of [UI, SWITCH_TO, PRIMED]) {
            await ensureCountriesLoaded(language);
            expect(getCountryInfo('ITA'), `the country cache does not answer what the endpoint said in ${language}`).toEqual({iso3: 'ITA', iso2: 'IT', name: COUNTRIES.ITA.names[language], flag_emoji: COUNTRIES.ITA.flag});
        }
        // What the cache answers for a code it does not know: no alpha-2, a white flag, the code as its name.
        expect(getCountryInfo('XKX'), 'premise: XKX is unknown to the reference data').toEqual(expect.objectContaining({iso2: '', name: 'XKX'}));
        // A country name on screen proves a load of its language only if the primed one names it otherwise.
        const names = COUNTRIES.ITA.names;
        expect(new Set([names[PRIMED], names[UI], names[SWITCH_TO]]).size, 'premise: the primed, the UI and the switch language name ITA alike').toBe(3);
    });

    it('answers the sectors endpoint as the backend does, the generated contract accepting it, with an emoji for every sector a case names', () => {
        // The cases only ever see the sector cache through the block, so the answer is checked here, not through the cache:
        // loading the cache from this harness would let a block that never loads the sectors pass.
        expect(schemas.SectorListResponse.safeParse(sectorsAnswer()).success, 'the sectors answer fails the generated SectorListResponse: the cache would read it otherwise than the app').toBe(true);
        // Until the block loads the sectors a row has no emoji: every expected sector label carries one, so such a row cannot match.
        const named = ['Financials', 'Health Care'];
        expect(
            named.filter((sector) => !sectorsAnswer().items.some((item) => item.key === sector && item.emoji.trim() !== '')),
            'a sector the cases name is not listed with an emoji of its own',
        ).toEqual([]);
        expect(new Set(named.map(answeredSectorEmoji)).size, 'the sectors the cases name carry two different emoji: a label cannot borrow another sector’s').toBe(named.length);
    });

    it('tells every label from its id, every dimension from «Asset», and the switch’s subjects from one language to the other', () => {
        const subjects: readonly (readonly [string, Dimension])[] = [
            ['STOCK', 'asset_class'],
            ['CROWDFUND_REAL_ESTATE', 'asset_class'],
            ['ETF_MONETARY', 'asset_class'],
            ['Financials', 'sector'],
            ['Health Care', 'sector'],
            ['Other', 'sector'],
            ['european_union', 'geography'],
            ['ITA', 'geography'],
            ['Other', 'geography'],
        ];
        const read = () => ({
            labels: subjects.map(([bucket, dimension]) => expectedLabel(bucket, dimension)),
            headers: DIMENSIONS.map((dimension) => t(`risk.stress.dimensions.${dimension}`)),
            asset: t('risk.levels.l4.table.asset'),
        });
        const check = (view: ReturnType<typeof read>, language: SupportedLocale) => {
            expect(
                subjects.filter((_subject, index) => view.labels[index] === subjects[index][0]).map(([bucket]) => bucket),
                `in ${language} these labels read as their ids: «the label, not the id» could not be told`,
            ).toEqual([]);
            expect(
                DIMENSIONS.filter((_dimension, index) => view.headers[index] === view.asset),
                `in ${language} a dimension is worded as «Asset»: which header was drawn could not be told`,
            ).toEqual([]);
        };
        const before = read();
        check(before, UI);
        switchLanguage(SWITCH_TO);
        try {
            const after = read();
            check(after, SWITCH_TO);
            // The switch cases read these: each must change, or a block that never redraws would pass.
            const unchanged = subjects.filter(([bucket], index) => ['STOCK', 'CROWDFUND_REAL_ESTATE', 'ETF_MONETARY', 'european_union', 'ITA', 'Other'].includes(bucket) && before.labels[index] === after.labels[index]).map(([bucket]) => bucket);
            expect(unchanged, `these labels read alike in ${UI} and ${SWITCH_TO}`).toEqual([]);
            expect(after.headers[0], `risk.stress.dimensions.asset_class reads alike in ${UI} and ${SWITCH_TO}`).not.toBe(before.headers[0]);
        } finally {
            switchLanguage(UI);
        }
    });
});

// ---------------------------------------------------------------------------
// The rows
// ---------------------------------------------------------------------------

describe('L4Shock — the rows are named, not coded (T-SHK, D5)', () => {
    it('names an asset-class answer’s rows from assets.types.* — «Global risk-off» over three held classes', async () => {
        mount(shockResult(RISK_OFF_ANSWER));
        expect(rowKeys(), 'barrier: the answer parsed and its held buckets are drawn').toEqual(expect.arrayContaining(RISK_OFF_ROWS));

        await waitFor(() => expect(rowLabels(RISK_OFF_ROWS), 'an asset-class row is not named by assets.types.<ID>: the table writes the bucket id').toEqual(expectedRows('asset_class', RISK_OFF_ROWS)));
    });

    it('names a sector answer’s rows by the answer’s dimension: the sector’s emoji and name, and Other as common.other', async () => {
        mount(shockResult(BANKING_ANSWER));
        expect(rowKeys(), 'barrier: the answer parsed and its buckets are drawn').toEqual(expect.arrayContaining(BANKING_ROWS));
        // No preset was chosen: the block's own dimension is still asset_class, so a sector name can only
        // come from the answer's.
        expect(screen.queryByTestId('risk-shock-detail-toggle'), 'premise: no scenario is chosen').toBeNull();

        await waitFor(() => expect(rowLabels(BANKING_ROWS), 'a sector row is not named by its emoji and sectors.<key>, or Other by common.other: the table writes the bucket id, or reads another dimension than the answer’s').toEqual(expectedRows('sector', BANKING_ROWS)));
    });

    it('names a geography answer’s rows by the answer’s dimension: a country by its flag and name, european_union and Other from the catalogue', async () => {
        mount(shockResult(ITALY_EU_ANSWER));
        expect(rowKeys(), 'barrier: the answer parsed and its buckets are drawn').toEqual(expect.arrayContaining(ITALY_EU_ROWS));
        expect(screen.queryByTestId('risk-shock-detail-toggle'), 'premise: no scenario is chosen').toBeNull();

        await waitFor(() => expect(rowLabels(ITALY_EU_ROWS), 'a geography row is not named — a country by the flag and name the country cache holds in the UI language, european_union by risk.stress.europeanUnion, Other by common.other').toEqual(expectedRows('geography', ITALY_EU_ROWS)));
    });
});

describe('L4Shock — a code nobody knows is shown as written (T-SHK)', () => {
    it.each(UNKNOWN_CASES)('$dimension: $unknown as written, beside $known named', async ({dimension, output, rows}) => {
        mount(shockResult(output));
        expect(rowKeys(), 'barrier: the answer parsed and its buckets are drawn').toEqual(expect.arrayContaining(rows));

        await waitFor(() => expect(rowLabels(rows), 'the known code is not named, or the unknown one is not shown as written: never a catalogue key, never a white flag').toEqual(expectedRows(dimension, rows)));
    });
});

describe('L4Shock — the first column is headed by the dimension (T-SHK)', () => {
    it.each([
        {dimension: 'asset_class', output: RISK_OFF_ANSWER, key: 'bucket:STOCK'},
        {dimension: 'sector', output: BANKING_ANSWER, key: 'bucket:Financials'},
        {dimension: 'geography', output: ITALY_EU_ANSWER, key: 'bucket:ITA'},
    ] as const)('heads a $dimension answer with risk.stress.dimensions.$dimension', async ({dimension, output, key}) => {
        mount(shockResult(output));

        await waitFor(() => expect(nameColumnHeader(key), `the column of the rows' names is not headed by risk.stress.dimensions.${dimension}`).toBe(t(`risk.stress.dimensions.${dimension}`)));
    });
});

describe('L4Shock — a bucket nobody holds is not a row (T-SHK, D5)', () => {
    it('draws the three classes the portfolio holds out of the eighteen of «Global risk-off», worst first — the held one shocked by 0 included', () => {
        mount(shockResult(RISK_OFF_ANSWER));
        expect(screen.getByTestId('risk-shock-total'), 'barrier: the answer parsed and its total is stated').toBeInTheDocument();

        expect(rowKeys(), 'the table draws a row for a bucket nobody holds (a 0.0% line), or lost a held one, or reordered them').toEqual(RISK_OFF_ROWS);
    });

    it('draws no table when the portfolio holds none of the shocked classes, and still states the total', () => {
        mount(shockResult(NOTHING_HELD_ANSWER));
        // The barrier for the absence below: the answer parsed, and the block speaks about it.
        expect(screen.getByTestId('risk-shock-total'), 'the total went with the table: the answer is still an answer').toBeInTheDocument();

        expect(screen.queryByTestId(TORNADO), 'a table of 0.0% rows is drawn for buckets nobody holds').toBeNull();
    });
});

// ---------------------------------------------------------------------------
// The detail editor
// ---------------------------------------------------------------------------

describe('L4Shock — the detail editor names the chosen scenario’s buckets (T-SHK)', () => {
    it.each([
        {preset: 'global_risk_off', dimension: 'asset_class'},
        {preset: 'banking_crisis', dimension: 'sector'},
        {preset: 'host_italy_eu', dimension: 'geography'},
    ] as const)('$preset ($dimension): the words beside each field, their title and its aria-label, the id kept in data-bucket-id', async ({preset}) => {
        const controller = mount();
        await choosePreset(controller, preset);
        await openEditor();
        const {dimension, shocks} = PRESETS[preset];

        await waitFor(() =>
            expect(editorEntries(), `the editor does not name the buckets of ${preset} by its dimension (${dimension}) — in the words beside each field, their title and the field's aria-label — or does not key them by their id in data-bucket-id`).toEqual(expectedEditor(dimension, shocks)),
        );
    });
});

// ---------------------------------------------------------------------------
// A language switch in place
// ---------------------------------------------------------------------------

describe('L4Shock — the labels follow a language switch in place (T-SHK)', () => {
    it('rewrites the rows, the header and the detail editor', async () => {
        const controller = mount();
        await choosePreset(controller, 'global_risk_off');
        await openEditor();
        const view = () => ({rows: rowLabels(RISK_OFF_ROWS), header: nameColumnHeader('bucket:STOCK'), editor: editorEntries()});
        const expected = () => ({rows: expectedRows('asset_class', RISK_OFF_ROWS), header: t('risk.stress.dimensions.asset_class'), editor: expectedEditor('asset_class', GLOBAL_RISK_OFF)});
        await waitFor(() => expect(view(), `barrier: before the switch the rows, the header and the editor do not speak ${UI}`).toEqual(expected()));

        switchLanguage(SWITCH_TO);

        await waitFor(() => expect(view(), `after a switch to ${SWITCH_TO} in place, the rows, the header or the editor still speak ${UI}`).toEqual(expected()));
    });

    it('reads a country’s name again in the new language', async () => {
        mount(shockResult(ITALY_EU_ANSWER));
        await waitFor(() => expect(rowLabels(ITALY_EU_ROWS), `barrier: before the switch the geography rows do not speak ${UI}`).toEqual(expectedRows('geography', ITALY_EU_ROWS)));

        switchLanguage(SWITCH_TO);

        await waitFor(() => expect(rowLabels(ITALY_EU_ROWS), `after a switch to ${SWITCH_TO} in place, a country keeps its ${UI} name — the country names were not loaded again in the new language — or the catalogue words did not follow`).toEqual(expectedRows('geography', ITALY_EU_ROWS)));
    });
});
