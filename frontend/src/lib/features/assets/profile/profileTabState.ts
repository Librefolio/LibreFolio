/**
 * profileTabState — the logic of the «Profilo» tab of the asset page (plan 68, E3+E4), as pure functions: the tab keeps
 * the DOM and the network (`profileStore`), this module decides what each part shows.
 *
 * - **The period** is the one chosen at the top of the asset page (I16): two days, or `start: 'min'` for «Tutti», up to
 *   the page's last day. The backend clips every voice's steps to it.
 * - **A voice's value** is its last step in the period: `value`, `emptied` on purpose (a null value), or `unavailable`
 *   (no step).
 * - **Where a voice goes** comes from the catalogue, never from a list here: `key_figure` makes a card, `charted` gives
 *   it a chart of its steps, `groups` place it in the details (the fund, the company, the identity, the bond). A voice
 *   with no group has no cell (the issuer's LEI, the voices other lanes read).
 * - **The classification** shows the composition of one day: «dati al» lists the days a composition changed in the
 *   period, newest first.
 * - **The company's sector** is the sector map of a share: one sector at 100 %. A map of several sectors is a fund's,
 *   shown by the classification only.
 *
 * No financial quantity is computed here: values are found and written. A percentage, stored as a fraction, is shifted
 * to percent on its decimal text (`fractionToPercent`) before it is drawn or written.
 *
 * @module features/assets/profile/profileTabState
 */
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import {compareDecimal, fractionToPercent} from '$lib/utils/core/exactDecimal';
import {formatPercent} from '$lib/utils/core/formatPercent';
import {sectorI18nKey} from '$lib/utils/assetTypes';
import {valueAt} from '$lib/utils/stepSeries';
import {panelWeights} from './profileEditState';
import type {ProfileDateRange, ProfileStep, ProfileVoice, ProfileVoices} from './profileStore';

// =============================================================================
// The period
// =============================================================================

/** The period of the asset page: its two days, and whether it is «Tutti». */
export interface PagePeriod {
    start: string;
    end: string;
    all: boolean;
}

/** The range the tab reads: the page's two days, or `start: 'min'` for «Tutti». */
export function profileReadRange(period: PagePeriod): ProfileDateRange {
    return period.all ? {start: 'min', end: period.end} : {start: period.start, end: period.end};
}

// =============================================================================
// A voice's value
// =============================================================================

/** What a cell shows: a value, a value emptied on purpose, or nothing in the period. */
export type ProfileCellState = 'value' | 'emptied' | 'unavailable';

/** One voice as a cell shows it: its last step in the period. */
export interface ProfileCell {
    key: string;
    voice: ProfileVoice;
    state: ProfileCellState;
    step: ProfileStep | null;
}

/** The cell of a voice: its last step in the period. */
export function profileCell(voice: ProfileVoice, steps: readonly ProfileStep[] | undefined): ProfileCell {
    const last = steps && steps.length ? steps[steps.length - 1] : null;
    const state: ProfileCellState = last === null ? 'unavailable' : last.value === null || last.value === undefined ? 'emptied' : 'value';
    return {key: voice.key, voice, state, step: last};
}

// =============================================================================
// Key figures
// =============================================================================

/** One point of a card's chart, as `PriceChartCompact` draws it; `missing` breaks the line. */
export interface ProfileChartPoint {
    date: string;
    value: number;
    missing?: boolean;
}

/** A key figure card: its cell, and the points of its chart (null: no chart). */
export interface KeyFigureCard extends ProfileCell {
    chart: ProfileChartPoint[] | null;
}

/** The number a chart draws for one stored value: a percentage in percent, an amount by its number; null otherwise. */
function chartNumber(voice: ProfileVoice, value: unknown): number | null {
    if (value === null || value === undefined) return null;
    let text: string | null = null;
    if (voice.shape === 'percentage') text = fractionToPercent(String(value));
    else if (voice.shape === 'number') text = String(value);
    else if (voice.shape === 'amount') text = String((value as {amount?: unknown}).amount ?? '');
    if (text === null || text === '') return null;
    const number = Number(text);
    return Number.isFinite(number) ? number : null;
}

/**
 * The points of a charted voice: one at the start of each step, and one closing the line on the last day. A step with
 * no number (emptied) breaks the line. Null when nothing in the period can be drawn.
 */
export function chartPoints(voice: ProfileVoice, steps: readonly ProfileStep[] | undefined): ProfileChartPoint[] | null {
    if (!steps || !steps.length) return null;
    const points: ProfileChartPoint[] = steps.map((point) => {
        const number = chartNumber(voice, point.value);
        return number === null ? {date: point.date, value: 0, missing: true} : {date: point.date, value: number};
    });
    if (points.every((point) => point.missing)) return null;
    const last = steps[steps.length - 1];
    const closing = points[points.length - 1];
    if (last.through !== last.date) points.push(closing.missing ? {date: last.through, value: 0, missing: true} : {date: last.through, value: closing.value});
    return points;
}

/** The key figure cards: every key figure of the catalogue, in its order, with a chart when the voice is charted. */
export function keyFigureCards(catalogue: readonly ProfileVoice[], voices: ProfileVoices): KeyFigureCard[] {
    return catalogue
        .filter((voice) => voice.key_figure)
        .map((voice) => {
            const steps = voices[voice.key];
            return {...profileCell(voice, steps), chart: voice.charted ? chartPoints(voice, steps) : null};
        });
}

// =============================================================================
// Details
// =============================================================================

/** The groups of the details, in the order the tab shows them. */
export const DETAIL_GROUPS = ['fund', 'company', 'identity', 'bond'] as const;
export type DetailGroupId = (typeof DETAIL_GROUPS)[number];

export interface DetailGroup {
    group: DetailGroupId;
    cells: ProfileCell[];
}

/** A map in the details (the company's sector): shown only when it is one key at 100 %. */
function oneKeyMapCell(cell: ProfileCell): ProfileCell {
    if (cell.state !== 'value') return cell;
    const keys = Object.keys((cell.step?.value ?? {}) as Record<string, unknown>);
    return keys.length === 1 ? cell : {...cell, state: 'unavailable'};
}

/** The detail groups: each with the voices the catalogue places in it, in catalogue order. */
export function detailGroups(catalogue: readonly ProfileVoice[], voices: ProfileVoices): DetailGroup[] {
    return DETAIL_GROUPS.map((group) => ({
        group,
        cells: catalogue
            .filter((voice) => (voice.groups as readonly string[]).includes(group))
            .map((voice) => {
                const cell = profileCell(voice, voices[voice.key]);
                return voice.shape === 'map' ? oneKeyMapCell(cell) : cell;
            }),
    }));
}

// =============================================================================
// Classification
// =============================================================================

const COMPOSITION_KEYS = ['geography', 'sector'] as const;

/**
 * The days a composition (countries, sectors) changed in the period, newest first. An emptying is a change too: the
 * newest day is always the state at the end of the period, so the default never shows a composition emptied since.
 */
export function compositionDays(voices: ProfileVoices): string[] {
    const days = new Set<string>();
    for (const key of COMPOSITION_KEYS) {
        for (const point of voices[key] ?? []) days.add(point.date);
    }
    return [...days].sort().reverse();
}

/** The countries and the sectors of one day, as fractions; null where the day has none. */
export function compositionAt(voices: ProfileVoices, day: string): {geography: Record<string, number> | null; sector: Record<string, number> | null} {
    const at = (key: (typeof COMPOSITION_KEYS)[number]) => panelWeights(valueAt(voices[key] ?? [], day)?.value ?? null);
    return {geography: at('geography'), sector: at('sector')};
}

// =============================================================================
// Writing a value
// =============================================================================

/** What writing a value needs from outside: the labels, the locale, the countries' names. */
export interface ProfileFormatContext {
    translate: (key: string) => string;
    locale: string;
    countryName: (iso3: string) => string;
}

/** A calendar day (`YYYY-MM-DD`) in the locale, read at local midnight: no time-zone shift. */
export function formatProfileDay(iso: string, locale: string): string {
    const day = new Date(`${iso}T00:00:00`);
    return Number.isNaN(day.getTime()) ? iso : day.toLocaleDateString(locale, {year: 'numeric', month: '2-digit', day: '2-digit'});
}

function formatNumber(text: string, locale: string): string {
    const number = Number(text);
    return Number.isFinite(number) ? new Intl.NumberFormat(locale, {maximumFractionDigits: 6}).format(number) : text;
}

/** A stored value as the tab writes it; '' for a missing value. Amounts are public figures of the asset, never masked. */
export function formatProfileValue(voice: ProfileVoice, value: unknown, context: ProfileFormatContext): string {
    if (value === null || value === undefined || value === '') return '';
    const {translate, locale} = context;
    switch (voice.shape) {
        case 'percentage': {
            const percent = fractionToPercent(String(value));
            return percent === null ? String(value) : formatPercent(Number(percent), {signed: false, digits: 4, trim: true, locale});
        }
        case 'number': {
            const number = formatNumber(String(value), locale);
            return voice.unit ? `${number} ${translate(`assets.profile.units.${voice.unit}`)}` : number;
        }
        case 'amount': {
            const amount = value as {amount?: unknown; currency?: unknown};
            const number = Number(amount.amount);
            const currency = String(amount.currency ?? '');
            return Number.isFinite(number) ? formatCurrencyAmountPlain(number, currency, {sensitivity: 'public', minFraction: 0, maxFraction: 0, locale}) : `${String(amount.amount ?? '')} ${currency}`.trim();
        }
        case 'date':
            return formatProfileDay(String(value), locale);
        case 'choice':
            return translate(`assets.profile.choices.${voice.key}.${String(value)}`);
        case 'country':
            return context.countryName(String(value));
        case 'map': {
            // One key (a share's sector): its label. Several: the three largest, each with its weight in percent.
            const label = (key: string) => (voice.map_keys === 'country' ? context.countryName(key) : translate(`sectors.${sectorI18nKey(key)}`));
            const entries = Object.entries(value as Record<string, unknown>).map(([key, weight]) => [key, String(weight)] as const);
            if (entries.length === 1) return label(entries[0][0]);
            return [...entries]
                .sort((left, right) => compareDecimal(right[1], left[1]) ?? 0)
                .slice(0, 3)
                .map(([key, weight]) => `${label(key)} ${formatPercent(Number(fractionToPercent(weight) ?? weight), {signed: false, digits: 2, trim: true, locale})}`)
                .join(', ');
        }
        case 'table': {
            const schedule = value as Array<{from?: string; to?: string}>;
            return schedule.length ? `${formatProfileDay(schedule[0].from ?? '', locale)} → ${formatProfileDay(schedule[schedule.length - 1].to ?? '', locale)}` : '';
        }
        default:
            return String(value);
    }
}
