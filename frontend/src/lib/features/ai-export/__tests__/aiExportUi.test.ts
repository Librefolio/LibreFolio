/**
 * AI Export UI helpers — menu labels, error messages and the "copied" message (Vitest, node).
 *
 * The figures of the copied message (M-18 CP2). Every figure is written in the interface language
 * (the developer's rule of 2026-10-12), through one source: `uiLocale()`. The copied message puts the
 * final prompt's token count and byte size inside a sentence of the interface language, so the two
 * figures take its notation. The response language is the language the AI is asked to answer in: it
 * shapes the prompt, never the message. Until now it also chose the notation of the two figures — an
 * English UI asking for an Italian answer read `11,93 k token (💾 47,68 KB)` inside an English
 * sentence. The rendered prompt is not this file's subject and does not change.
 *
 * Expectations. A localized figure comes from `Intl.NumberFormat` in this runtime, with the two fraction
 * digits the formatter writes; English is typed where it is the exact text. The browser is pinned to
 * en-US before any import (Node's follows the host's ICU locale): an English UI is then written en-US,
 * an Italian one bare `it` — an en-US browser lends no region to Italian (uiLocale.test.ts).
 *
 * Language. Switched as LanguageSelector does (`currentLanguage.set`), and put back to English after
 * every test: the store is module level.
 */
import {afterAll, afterEach, describe, expect, it, vi} from 'vitest';

vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

import {waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {AiExportProblemError} from '../aiExportClient';
import type {AiExportOptionsSelection} from '../aiExportOptions';
import {AI_EXPORT_RESPONSE_LANGUAGE_DISPLAY_NAMES, type AiExportPromptStats, type AiExportResponseLanguageDisplayName} from '../templates/promptRenderer';
import {buildAiExportMenuLabels, getAiExportErrorMessage, getAiExportSuccessMessages, type AiExportTranslate} from '../ui';
import {compatibilityFixture} from './runtimeFixtures';

const t = (key: string) => key;

/** A planning analysis copied in Standard detail, answered in `responseLanguage`. */
function copiedOptions(responseLanguage: AiExportResponseLanguageDisplayName): AiExportOptionsSelection {
    return {
        selectionKind: 'analysis',
        selectionId: 'portfolio.pac_planning',
        detailLevel: 'standard',
        period: {preset: '3m', customAmount: 3, customUnit: 'months'},
        responseLanguage,
    };
}

/** The final prompt: 11 925 tokens, 48 828 bytes — 11.925 thousand tokens, 47.68… KB. */
const COPIED_STATS: AiExportPromptStats = {
    finalPrompt: {
        characterCountUtf16CodeUnits: 47_700,
        byteCountUtf8: 48_828,
        estimatedTokens: 11_925,
        estimationMethod: 'ceil_utf16_code_units_div_4_v1',
    },
    snapshotBackendStats: {
        dataset_count: 1,
        section_count: 1,
        serialized_characters: 129_704,
        serialized_bytes: 131_072,
        estimated_tokens: 32_426,
        token_estimation_method: 'chars_div_4_v1',
    },
};

/** The copied message's two figures as `locale` writes them: two fraction digits, thousands of tokens and kilobytes (1 024 bytes). */
function figuresIn(locale: string): string {
    const twoDigits = new Intl.NumberFormat(locale, {minimumFractionDigits: 2, maximumFractionDigits: 2});
    return `${twoDigits.format(COPIED_STATS.finalPrompt.estimatedTokens / 1_000)} k token (💾 ${twoDigits.format(COPIED_STATS.finalPrompt.byteCountUtf8 / 1_024)} KB)`;
}

/** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
async function uiLanguage(lang: 'en' | 'it'): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
}

afterEach(async () => {
    // The language is module-level state shared by every test of the file.
    await uiLanguage('en');
});

afterAll(() => {
    vi.unstubAllGlobals();
});

describe('AI Export UI helpers', () => {
    it('builds labels for every real catalog selection', () => {
        const labels = buildAiExportMenuLabels(t, compatibilityFixture(), 'AI Export');

        expect(Object.keys(labels.options.selectionLabels)).toHaveLength(19);
        expect(labels.options.categoryLabels).toEqual({dataset: 'aiExport.exportData', analysis: 'aiExport.requestAnalysis'});
        expect(labels.options.categoryHelp).toEqual({dataset: 'aiExport.exportDataHelp', analysis: 'aiExport.requestAnalysisHelp'});
        expect(labels.options.payloadStatsHelp).toBe('aiExport.payloadStatsHelp');
        expect(labels.options.tokenUnitLabel).toBe('aiExport.tokenUnit');
    });

    it('includes the final token and byte sizes in the copied message, in the interface language: an Italian UI writes Italian digits', async () => {
        // M-18 CP2 rewrite. This case used to leave the UI in English and get Italian digits from the
        // response language; the interface language decides them now, so the Italian sentence below
        // comes with an Italian UI.
        await uiLanguage('it');
        expect(uiLocale(), 'control: an Italian UI on an en-US browser is written bare it').toBe('it');
        const translate = (key: string, translationOptions?: {values?: Record<string, string | number | boolean | null | undefined>}) => {
            if (key === 'aiExport.details.standard') return 'Standard';
            if (key === 'aiExport.tokenUnit') return 'token';
            if (key === 'aiExport.copied') return `AI Export copiato:\n• ${translationOptions?.values?.tokens} (💾 ${translationOptions?.values?.bytes})\n• dettaglio: ${translationOptions?.values?.detail}`;
            return key;
        };

        expect(getAiExportSuccessMessages(translate, {options: copiedOptions('Italian'), stats: COPIED_STATS}).copied).toBe(`AI Export copiato:\n• ${figuresIn('it')}\n• dettaglio: Standard`);
    });

    it('maps new typed problem codes', () => {
        const error = new AiExportProblemError(
            422,
            {
                code: 'selection_not_applicable',
                message: 'Not applicable',
                domain: 'asset',
                selection_kind: 'analysis',
                selection_id: 'asset.position_review',
                detail_level: 'standard',
                applicability_code: 'requires_position',
                reason_code: 'no_position',
            },
            null,
        );
        expect(getAiExportErrorMessage(t, error)).toBe('aiExport.selectionNotApplicable');
    });
});

describe('AI Export UI helpers — the copied message writes its figures in the interface language, never in the response language (M-18)', () => {
    // Today's English text, exactly: what an English UI on an en-US browser reads.
    const ENGLISH = '11.93 k token (💾 47.68 KB)';

    /** A `t` that words the copied message as its two figures and nothing else: no sentence is read. */
    const figuresT: AiExportTranslate = (key, options) => {
        if (key === 'aiExport.tokenUnit') return 'token';
        if (key === 'aiExport.copied') return `${options?.values?.tokens} (💾 ${options?.values?.bytes})`;
        return key;
    };

    /** The figures of the copied message for an answer asked in `responseLanguage`, in the current UI. */
    function copiedFigures(responseLanguage: AiExportResponseLanguageDisplayName): string {
        return getAiExportSuccessMessages(figuresT, {options: copiedOptions(responseLanguage), stats: COPIED_STATS}).copied;
    }

    it('an English UI on an en-US browser writes 11.93 k token (💾 47.68 KB), though the answer is asked in Italian', () => {
        expect(uiLocale(), 'control: an English UI on an en-US browser is written en-US').toBe('en-US');
        expect(figuresIn('en-US'), 'control: the typed English text is what en-US writes').toBe(ENGLISH);
        expect(figuresIn('it'), 'control: Italian writes these figures otherwise').not.toBe(ENGLISH);

        expect(copiedFigures('Italian'), 'the response language chose the notation of the figures').toBe(ENGLISH);
    });

    it('each UI writes the same figures, its own, for every response language: en-US for English, Italian for Italian', async () => {
        const read = (): Record<string, string> => Object.fromEntries(AI_EXPORT_RESPONSE_LANGUAGE_DISPLAY_NAMES.map((language) => [language, copiedFigures(language)]));
        const all = (figures: string): Record<string, string> => Object.fromEntries(AI_EXPORT_RESPONSE_LANGUAGE_DISPLAY_NAMES.map((language) => [language, figures]));

        expect(uiLocale(), 'control: an English UI on an en-US browser is written en-US').toBe('en-US');
        const written = {en: read(), it: {} as Record<string, string>};
        await uiLanguage('it');
        expect(uiLocale(), 'control: an Italian UI on an en-US browser is written bare it').toBe('it');
        written.it = read();

        expect(written, 'by response language, under each UI: the response language moved the figures').toEqual({en: all(ENGLISH), it: all(figuresIn('it'))});
    });
});

describe('AI Export UI helpers — the count presets of the period are labelled from the catalogues (T, duration labels)', () => {
    // The 3m, 6m and 1y presets are written '3M', '6M' and '1Y' in the code: English unit letters in
    // every language, while `custom` beside them already reads `aiExport.periodCustom`. The contract is
    // the date picker's and the rolling window's: `datePicker.presets.months` with n=3 and n=6,
    // `datePicker.presets.years` with n=1 — the catalogues carry the reader's unit letter (1A in Italian).
    //
    // Observed without reading a language, through a marker `t`: a label taken from the catalogue reads
    // as a marker of its key and values (`⟦datePicker.presets.months n=3⟧`), a literal written in the
    // code reads as itself.
    //
    // Red today: the three presets read '3M', '6M' and '1Y'.

    type TranslationValues = Readonly<Record<string, string | number | boolean | null | undefined>>;

    /** How a label reads through the marker `t`: `⟦key⟧`, or `⟦key n=3⟧` for a message given values. */
    const marked = (key: string, values: TranslationValues = {}): string => `⟦${[key, ...Object.entries(values).map(([name, value]) => `${name}=${String(value)}`)].join(' ')}⟧`;

    /** A `t` that reads every key as its marker, with the values it is given. */
    const markerT = (key: string, options?: {values?: TranslationValues}): string => marked(key, options?.values);

    it('labels 3m and 6m datePicker.presets.months and 1y datePicker.presets.years, each with its count as n — custom unchanged', () => {
        const labels = buildAiExportMenuLabels(markerT, compatibilityFixture(), 'AI Export');
        expect(labels.options.periodPresetLabels.custom, 'control: a preset the helper already takes from the catalogue reads its marker').toBe(marked('aiExport.periodCustom'));

        expect(labels.options.periodPresetLabels).toEqual({
            '3m': marked('datePicker.presets.months', {n: 3}),
            '6m': marked('datePicker.presets.months', {n: 6}),
            '1y': marked('datePicker.presets.years', {n: 1}),
            custom: marked('aiExport.periodCustom'),
        });
    });
});
