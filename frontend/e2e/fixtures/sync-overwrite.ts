/**
 * The sync dialogs' overwrite warning (C-66, F-094), as the page specs read it.
 *
 * A sync writes every date the data provider returns over its period and replaces what is stored there, manual edits
 * included. `SyncModalBase` says so before Start: for each active section whose targets already hold a stored row in
 * the period, one `{dialog testId}-overwrite-warning`, publishing `data-section`, `data-existing` (the targets holding
 * a stored row) and `data-total` (the section's targets). Its sentence is the catalogue's `fx.sync.overwriteWarning`.
 *
 * The pages decide what holds a stored row from what they show: a point filled backward from an earlier date is not
 * one. A spec therefore chooses its period by data, through the endpoints the pages read, rather than assuming what
 * the seed holds on a given day:
 *
 *   · `storedAssetPrices` — every asset with a provider (what «Sync all» on the Assets list syncs), and what
 *     `POST /assets/prices/query` answers for it over the period;
 *   · `storedFxRates` — every pair «Sync all» on the FX list syncs (any route but a lone MANUAL one), and what
 *     `POST /fx/currencies/convert` answers for it over the period;
 *   · `isStoredPoint` — the pages' rule, restated on the wire shape both endpoints share.
 *
 * And it reads the dialog without pinning a translation or starting a sync:
 *
 *   · `overwriteWarningSentence` — the catalogue's message for the page's language, formatted by
 *     `intl-messageformat`, the formatter svelte-i18n compiles messages with;
 *   · `overwriteCounts` — the three published values, as numbers;
 *   · `recordSyncRequests` — every sync request the page sends: a spec that opens a dialog and never starts it proves
 *     that no provider was called.
 */
import {IntlMessageFormat} from 'intl-messageformat';
import {schemas} from '../../src/lib/api/generated';
import {expect, type Locator, type Page} from './playwright';
import {t as catalogueText} from './i18n-data';

const API = '/api/v1';

/** The catalogue key of the warning's sentence. */
export const OVERWRITE_WARNING_KEY = 'fx.sync.overwriteWarning';

/** The two sync endpoints a sync dialog calls when it is started. */
const SYNC_PATHS: readonly string[] = [`${API}/assets/prices/sync`, `${API}/fx/currencies/sync`];

/** A period as the pages take it from their URL (`?start=&end=`), both bounds included. A type, not an interface, so it
 * can be handed as the URL query (`goToAssetsPage(page, period)`, `goToFxPage(page, period)`). */
export type SyncPeriod = {
    start: string;
    end: string;
};

/** What a page will show of one sync target over a period. */
export interface ShownInPeriod {
    /** Asset id, or pair slug (`BASE-QUOTE`, sorted as the dialogs name pairs). */
    id: string;
    /** Display name for an asset, the slug for a pair: what a failure message names. */
    name: string;
    /** The points the endpoint answers inside the period: stored rows and days filled backward. */
    shown: number;
    /** Of those, the stored rows: what a sync of the period replaces. */
    stored: number;
}

/**
 * Whether a point answered by `POST /assets/prices/query` or `POST /fx/currencies/convert` is a stored row: not
 * filled backward from an earlier date, i.e. no `backward_fill_info`, or one with `days_back` 0 (a stored price
 * converted with an older FX rate).
 *
 * The generated client types `backward_fill_info` wider than the wire (which sends an object or null): its TypeScript
 * union also holds a list. Read as the pages read it (`extractDaysBack`): only an object's numeric `days_back` counts,
 * anything else is 0.
 */
export function isStoredPoint(point: {backward_fill_info?: unknown}): boolean {
    const info = point.backward_fill_info;
    const daysBack = info !== null && typeof info === 'object' && 'days_back' in info ? info.days_back : 0;
    return (typeof daysBack === 'number' ? daysBack : 0) === 0;
}

function inPeriod(date: string, period: SyncPeriod): boolean {
    return date >= period.start && date <= period.end;
}

/**
 * Every asset with a provider — the targets of «Sync all» on the Assets list — with what the page will show of it
 * over `period`, read from the endpoint the page reads its prices from.
 */
export async function storedAssetPrices(page: Page, period: SyncPeriod): Promise<ShownInPeriod[]> {
    const listed = await page.request.get(`${API}/assets/query`);
    expect(listed.ok(), `GET ${API}/assets/query: HTTP ${listed.status()}`).toBe(true);
    const assets = ((await listed.json()) as Array<{id: number; display_name: string; provider_code?: string | null}>).filter((asset) => !!asset.provider_code);
    if (assets.length === 0) return [];

    const items = assets.map((asset) => schemas.FAPriceQueryItem.parse({asset_id: asset.id, date_range: period}));
    const queried = await page.request.post(`${API}/assets/prices/query`, {data: items});
    expect(queried.ok(), `POST ${API}/assets/prices/query over ${period.start} → ${period.end}: HTTP ${queried.status()} ${await queried.text()}`).toBe(true);
    const answer = schemas.FAPriceQueryResponse.parse(await queried.json());

    return assets.map((asset) => {
        const points = ((answer.items ?? []).find((item) => item.asset_id === asset.id)?.prices ?? []).filter((point) => inPeriod(point.date, period));
        return {id: String(asset.id), name: asset.display_name, shown: points.length, stored: points.filter(isStoredPoint).length};
    });
}

/**
 * Every pair «Sync all» on the FX list syncs — a pair with a route, unless its one route is MANUAL, the rule of the
 * page's `handleSyncAll` — with what the page will show of it over `period`, read from the endpoint the page reads its
 * rates from.
 */
export async function storedFxRates(page: Page, period: SyncPeriod): Promise<ShownInPeriod[]> {
    const listed = await page.request.get(`${API}/fx/providers/routes`);
    expect(listed.ok(), `GET ${API}/fx/providers/routes: HTTP ${listed.status()}`).toBe(true);
    const providersBySlug = new Map<string, string[]>();
    for (const route of schemas.FXConversionRoutesResponse.parse(await listed.json()).items ?? []) {
        const slug = [route.base, route.quote].sort().join('-');
        const code = route.is_chain ? `CHAIN:${route.chain_steps.map((step) => step.provider).join('+')}` : route.chain_steps[0].provider;
        providersBySlug.set(slug, [...(providersBySlug.get(slug) ?? []), code]);
    }
    const slugs = [...providersBySlug]
        .filter(([, codes]) => !(codes.length === 1 && codes[0] === 'MANUAL'))
        .map(([slug]) => slug)
        .sort();
    if (slugs.length === 0) return [];

    const conversions = slugs.map((slug) => {
        const [base, quote] = slug.split('-');
        return {from_amount: {code: base, amount: '1'}, to: quote, date_range: period};
    });
    const converted = await page.request.post(`${API}/fx/currencies/convert`, {data: conversions});
    // 404 is the endpoint's answer when every conversion failed: no pair has a rate on or before any day of the period.
    if (converted.status() === 404) return slugs.map((slug) => ({id: slug, name: slug, shown: 0, stored: 0}));
    expect(converted.ok(), `POST ${API}/fx/currencies/convert over ${period.start} → ${period.end}: HTTP ${converted.status()} ${await converted.text()}`).toBe(true);
    const {results} = schemas.FXConvertResponse.parse(await converted.json());

    return slugs.map((slug) => {
        const points = results.filter((result) => [result.from_amount.code, result.to_amount.code].sort().join('-') === slug && inPeriod(result.conversion_date, period));
        return {id: slug, name: slug, shown: points.length, stored: points.filter(isStoredPoint).length};
    });
}

/** One line per target, for a failure message: what each one shows and stores in the period. */
export function describeShown(targets: readonly ShownInPeriod[]): string {
    return targets.map((target) => `${target.name}: ${target.stored} stored of ${target.shown} shown`).join('; ') || '(no target)';
}

/**
 * The language the page is drawn in: `<html lang>`, which the root layout keeps on the language shown, read once
 * `data-i18n-ready` says its dictionary is in (the reading of `tx-import-resolution.spec.ts`).
 */
export async function pageLanguage(page: Page): Promise<string> {
    const html = page.locator('html');
    await expect(html, 'the page has its dictionary').toHaveAttribute('data-i18n-ready', 'true');
    return ((await html.getAttribute('lang')) ?? '').split('-')[0];
}

/**
 * `fx.sync.overwriteWarning` for these counts, as the `lang` catalogue words it: the message read from the catalogue
 * file and formatted by `intl-messageformat`. A catalogue without the message fails here, by name — a key that
 * resolved to itself would let a dialog printing the key pass.
 */
export function overwriteWarningSentence(lang: string, existing: number, total: number): string {
    const message = catalogueText(lang, OVERWRITE_WARNING_KEY);
    expect(message, `the "${lang}" catalogue has a message for ${OVERWRITE_WARNING_KEY}`).not.toBe(OVERWRITE_WARNING_KEY);
    return String(new IntlMessageFormat(message, lang).format({existing, total}));
}

/** A warning's three published values, read once it is on screen; a missing or non-numeric count fails here. */
export async function overwriteCounts(warning: Locator): Promise<{section: string | null; existing: number; total: number}> {
    await expect(warning).toBeVisible();
    const section = await warning.getAttribute('data-section');
    const existing = Number(await warning.getAttribute('data-existing'));
    const total = Number(await warning.getAttribute('data-total'));
    expect(Number.isInteger(existing) && Number.isInteger(total), `data-existing and data-total are whole numbers (read ${existing} and ${total})`).toBe(true);
    return {section, existing, total};
}

/**
 * Every sync request the page sends from now on, by path. Armed before the page opens; a spec that opens a sync
 * dialog and never starts it expects it empty at the end.
 */
export function recordSyncRequests(page: Page): string[] {
    const sent: string[] = [];
    page.on('request', (request) => {
        const path = new URL(request.url()).pathname;
        if (request.method() === 'POST' && SYNC_PATHS.includes(path)) sent.push(path);
    });
    return sent;
}
