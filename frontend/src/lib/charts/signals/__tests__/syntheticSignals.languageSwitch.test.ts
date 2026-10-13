// @vitest-environment jsdom
/**
 * Synthetic benchmark labels follow the interface language when it changes in place (T-EN2).
 *
 * A page reads its benchmarks' labels inside reactive code: the asset detail's overlay series are a
 * `$derived` over `renderMulti`, which calls `getLabel()`. The language selector changes the language
 * without reloading the page, so that read must run again. The contract reads the catalogue through a
 * TRACKED translator — `fromStore(_)`, the model of `uiLocale()` — beside formatters whose default locale,
 * `uiLocale()`, is tracked too.
 *
 * How: `recordReads` (`$test/runes.svelte`) records every value an effect reads. The language is switched as
 * the selector does it (`currentLanguage.set`), its catalogue awaited, the effects flushed, and the LAST label
 * recorded must be the new language's. Each case switches to a language whose catalogue is not loaded yet —
 * checked, not assumed — because that is where a translator read once would show: the language store moves
 * at once and the catalogue lands later, so only a tracked translator words the label again when it lands
 * (an untracked one would leave English words beside figures already in the new notation).
 *
 * Expected labels are the catalogue's own text (`$_`) around figures Intl writes in the interface locale,
 * never typed. On jsdom's en-US browser that locale is `en-US` for English and the bare language otherwise.
 *
 * Red today: a label reads nothing reactive, so the effect runs once and its last value is the English label.
 *
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`) next to
 * `syntheticSignals.test.ts`, which pins the labels themselves; the jsdom environment is per file, and
 * `recordReads` needs it.
 */
import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {flushSync} from 'svelte';
import {get} from 'svelte/store';
import {dictionary, waitLocale} from 'svelte-i18n';

import {setupI18n} from '$test/component';
import {assertEffectsRun, recordReads} from '$test/runes.svelte';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import type {SignalStyle} from '../ChartSignal';
import {CompoundSignal} from '../CompoundSignal';
import {LinearSignal} from '../LinearSignal';
import {SineSignal} from '../SineSignal';

type UiLanguage = 'en' | 'it' | 'fr';

const style: SignalStyle = {
    color: '#3b82f6',
    lineWidth: 1,
    lineType: 'dashed',
    markerStart: null,
    markerEnd: null,
};

/** A catalogue message with its values, as the interface language words it. */
function catalogue(key: string, values: Record<string, string>): string {
    return get(_)(key, {values});
}

/** `value` percent as Intl writes it in `locale`: up to two decimals, none trailing; `signed` puts a `+` before a positive one. */
function percent(value: number, locale: string, {signed = false} = {}): string {
    const text = new Intl.NumberFormat(locale, {style: 'percent', minimumFractionDigits: 0, maximumFractionDigits: 2}).format(value / 100);
    return signed && value > 0 ? `+${text}` : text;
}

/** `value` as Intl writes it in `locale`: up to two decimals, none trailing. */
function decimal(value: number, locale: string): string {
    return new Intl.NumberFormat(locale, {minimumFractionDigits: 0, maximumFractionDigits: 2}).format(value);
}

/** The labels of the signals below as the catalogue and Intl write them in `locale`. */
function expectedLabels(locale: string): {linear: string; compound: string; sine: string} {
    return {
        linear: `${catalogue('chartSettings.signals.linearLabel', {rate: percent(2.5, locale)})} ${percent(0.5, locale, {signed: true})}`,
        compound: `${catalogue('chartSettings.signals.compoundLabel', {rate: percent(7.25, locale)})} ${percent(-1.5, locale, {signed: true})}`,
        sine: catalogue('chartSettings.signals.sineLabel', {amplitude: percent(12.5, locale), period: decimal(45.5, locale)}),
    };
}

/** Each label with its no-break spaces spelled out, so a failure tells U+00A0 and U+202F from a space. */
function spelled(labels: Record<string, string>): Record<string, string> {
    return Object.fromEntries(Object.entries(labels).map(([name, label]) => [name, label.replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`)]));
}

/** Whether svelte-i18n holds `lang`'s catalogue yet: it registers each language empty and fills it on first use. */
function catalogueLoaded(lang: UiLanguage): boolean {
    return Object.keys(get(dictionary)[lang] ?? {}).length > 0;
}

/** Switch the interface language in place, as the language selector does; wait for its catalogue, then flush the effects. */
async function switchTo(lang: UiLanguage): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
    flushSync();
}

/** The last value an effect recorded, which must be a set of labels and not the error a read threw. */
function lastLabels(values: Array<Record<string, string> | Error>): Record<string, string> {
    const last = values.at(-1);
    if (last === undefined) throw new Error('the effect recorded nothing');
    if (last instanceof Error) throw last;
    return last;
}

beforeAll(async () => {
    await setupI18n('en');
    assertEffectsRun();
});

afterEach(async () => {
    // The language is module-level state shared by every case of the file.
    await switchTo('en');
});

describe('Synthetic benchmark labels follow an in-place language switch (T-EN2)', () => {
    it('Linear and Compound, read inside an effect, are read again in Italian when the interface switches from English in place', async () => {
        const linear = new LinearSignal('linear', style, {annualRate: 2.5, offset: 0.5});
        const compound = new CompoundSignal('compound', style, {annualRate: 7.25, offset: -1.5});
        expect(catalogueLoaded('it'), 'precondition: the Italian catalogue is not loaded yet, so the switch waits for it as a first switch does in the app').toBe(false);

        const reads = recordReads(() => ({linear: linear.getLabel(), compound: compound.getLabel()}));
        try {
            const english = expectedLabels(uiLocale());
            expect(spelled(lastLabels(reads.values)), 'control: the effect read the English labels').toEqual(spelled({linear: english.linear, compound: english.compound}));

            await switchTo('it');
            expect(uiLocale(), 'control: an Italian interface on jsdom’s en-US browser writes bare Italian').toBe('it');
            const italian = expectedLabels('it');

            expect(spelled(lastLabels(reads.values)), 'the labels are not read again in Italian: the effect that read them did not run again, or ran before the catalogue landed and never after').toEqual(spelled({linear: italian.linear, compound: italian.compound}));
        } finally {
            reads.stop();
        }
    });

    it('Sine, read inside an effect, is read again in French when the interface switches from English in place', async () => {
        const sine = new SineSignal('sine', style, {amplitude: 12.5, period: 45.5, offset: 0});
        expect(catalogueLoaded('fr'), 'precondition: the French catalogue is not loaded yet, so the switch waits for it as a first switch does in the app').toBe(false);

        const reads = recordReads(() => ({sine: sine.getLabel()}));
        try {
            expect(spelled(lastLabels(reads.values)), 'control: the effect read the English label').toEqual(spelled({sine: expectedLabels(uiLocale()).sine}));

            await switchTo('fr');
            expect(uiLocale(), 'control: a French interface on jsdom’s en-US browser writes bare French').toBe('fr');

            expect(spelled(lastLabels(reads.values)), 'the label is not read again in French: the effect that read it did not run again, or ran before the catalogue landed and never after').toEqual(spelled({sine: expectedLabels('fr').sine}));
        } finally {
            reads.stop();
        }
    });
});
