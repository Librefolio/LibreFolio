// @vitest-environment jsdom
/**
 * FileEditModal — the file size in the UI language, in a legacy component (M-18 CP1).
 *
 * Numbers follow the UI language (the developer's rule of 2026-10-12). The modal shows the size of the
 * file it renames through `formatBytes`, which printed `toFixed(1)` — `1.5 KB` for an Italian reader, who
 * writes `1,5 KB` — and now writes its number through `formatFixed`, with a `locale` defaulting to
 * `uiLocale()`, and its unit through `translate`, defaulting to `get(_)`.
 *
 * The trap this file guards (wiki: problems/legacy-component-language-untracked). FileEditModal is a
 * legacy component (`export let`, `$:`, `createEventDispatcher`), and a legacy template compiles a call
 * inside an expression to `$.untrack(() => formatBytes(file.size))`, tracking only what the expression
 * names. Whatever `formatBytes` reads by itself is read when the expression last ran, and the size keeps
 * the language it was drawn in. So the template names both sources in the expression —
 * `formatBytes(file.size, $_, $uiLocaleStore)` — and only an in-place switch can tell: a mount in the new
 * language passes either way.
 *
 * Why both. `$uiLocaleStore` moves the moment the language does, so naming it re-runs the expression and
 * the number follows. The unit comes from the catalogue, which the app loads on the first switch to a
 * language: when the expression re-runs for the new language, the catalogue may not have arrived yet,
 * and only an expression that also names `$_` runs again when it does. Measured on a prototype before
 * writing this file: without `$_`, the size ends the first switch to French as `1,5 KB` — French number,
 * English unit — and with `$_` as `1,5 Ko`.
 *
 * Steps. English at mount, today's exact text. Italian at mount, and English → Italian in place: the number
 * follows (Italian keeps the `KB` of English, so these steps are about the number alone). The first switch
 * to French, whose catalogue is not loaded yet: the number and the unit both follow once it arrives. That
 * test runs last and checks its own precondition — no other test of this file loads French.
 *
 * Expectations. The number comes from `Intl.NumberFormat` in this runtime, never typed; the unit is read
 * from the shipped catalogue of the step's language — `common.kilobytes`, a plain message `$_` returns as
 * it is — so no translation is written here. The controls check that the Italian number and the French
 * unit differ from English: otherwise a step would compare equal strings and prove nothing.
 *
 * Selection. The dialog by its role, the modal by its `data-testid`; the size is the one leaf of the
 * dialog whose whole text is a number and a unit, as the modal publishes no handle of its own for it.
 * jsdom's browser is en-US, so the English UI keeps en-US notation.
 *
 * The scope of the upload (decision 36), first block. The modal takes an optional `scope` and hands it to
 * `uploadFile` as its third argument; without it, nothing — the server decides. `uploadFile` is therefore
 * a spy, while `formatBytes`, this file's other subject, stays the real one from the same module. That
 * block runs first and loads no language, so the French test still finds its catalogue unloaded.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';
import {dictionary, locale, waitLocale} from 'svelte-i18n';

// Nothing here reaches the network: `uploadFile` is a spy (the scope block asserts what it is called with), and
// `formatBytes`, from the same module, stays real; the API client stays out of the graph.
vi.mock('$lib/api', () => ({axiosInstance: {post: vi.fn()}}));
const uploads = vi.hoisted(() => ({uploadFile: vi.fn()}));
vi.mock('$lib/utils/files/upload', async (importOriginal) => ({...(await importOriginal<typeof import('$lib/utils/files/upload')>()), uploadFile: uploads.uploadFile}));

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import enCatalogue from '$lib/i18n/en.json';
import frCatalogue from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import {currentLanguage} from '$lib/stores/app/language';
import FileEditModal from './FileEditModal.svelte';

type UiLanguage = 'en' | 'it' | 'fr';

/** The shipped catalogues the unit is read from, as the component's `$_` reads it. */
const CATALOGUES = {en: enCatalogue, it: itCatalogue, fr: frCatalogue};

/** 1.5 KB exactly: one decimal in every notation, no rounding involved. */
const SIZE_BYTES = 1536;
const SIZE_KB = 1.5;

/** Today's English text: the number exactly as `toFixed(1)` printed it, the unit as the English catalogue has it. */
const ENGLISH = `1.5 ${CATALOGUES.en.common.kilobytes}`;

/** The kilobyte unit of `lang`'s shipped catalogue: what `$_('common.kilobytes')` returns in that language. */
function unitIn(lang: UiLanguage): string {
    return CATALOGUES[lang].common.kilobytes;
}

/** The size as `formatBytes` must write it in `lang`: the number from Intl, the unit from the catalogue of `lang`. */
function expectedSize(lang: UiLanguage): string {
    const number = new Intl.NumberFormat(lang, {minimumFractionDigits: 1, maximumFractionDigits: 1}).format(SIZE_KB);
    return `${number} ${unitIn(lang)}`;
}

/** `text` with its no-break spaces spelled out, so a message tells U+00A0 and U+202F from a space. */
function spelled(text: string): string {
    return text.replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`);
}

function mountModal(): void {
    const file = new File([new Uint8Array(SIZE_BYTES)], 'statement.pdf', {type: 'application/pdf'});
    expect(file.size, 'control: the file has the size put in').toBe(SIZE_BYTES);
    render(FileEditModal, {props: {open: true, file}});
}

/** The size the modal shows: within its dialog, the one leaf whose whole text is a number and a unit. */
function shownSize(): string {
    const dialog = screen.getByRole('dialog');
    within(dialog).getByTestId('file-edit-modal');
    const sizes = [...dialog.querySelectorAll('*')]
        .filter((element) => element.children.length === 0)
        .map((element) => (element.textContent ?? '').trim())
        .filter((text) => /^\d[\d.,\u00a0\u202f]*\s\S+$/.test(text));
    if (sizes.length !== 1) throw new Error(`expected one size in the dialog, found ${JSON.stringify(sizes)}`);
    return sizes[0];
}

/** Flush synchronously, then once more through the microtask the app itself waits on. */
async function settle(): Promise<void> {
    flushSync();
    await tick();
}

/** Change the UI language as LanguageSelector does, then flush. The controls name the layer if the language did not move. */
async function switchLanguage(lang: UiLanguage): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
    await settle();
    expect(get(currentLanguage), `control: the app language is ${lang}`).toBe(lang);
    expect(get(locale), `control: the svelte-i18n locale is ${lang}`).toBe(lang);
}

beforeAll(async () => {
    await setupI18n();
    // Italian joins English up front, so a switch to it never waits on a loader. French is left to the
    // test that switches to it: the arrival of its catalogue is that test's subject.
    await waitLocale('it');
    // Controls: today's English is what the formatter writes in English, this runtime has Italian ICU
    // data, and the French unit differs from the English one.
    expect(expectedSize('en'), 'English, from Intl and the catalogue').toBe(ENGLISH);
    expect(expectedSize('it'), 'Italian differs from English').not.toBe(ENGLISH);
    expect(unitIn('fr'), 'the French kilobyte unit differs from the English one').not.toBe(unitIn('en'));
});

afterEach(async () => {
    // The language is module-level state shared by every test of the file.
    await switchLanguage('en');
});

describe('FileEditModal — the scope it uploads with (decision 36)', () => {
    beforeEach(() => {
        uploads.uploadFile.mockReset().mockResolvedValue('/uploads/statement.pdf');
    });

    /** Mount on a PDF, confirm, and answer the arguments `uploadFile` got; the modal completes with its url. */
    async function confirmUpload(props: Record<string, unknown>): Promise<unknown[]> {
        const complete = vi.fn();
        const file = new File(['%PDF-1.4'], 'statement.pdf', {type: 'application/pdf'});
        render(FileEditModal, {props: {open: true, file, ...props}, events: {complete: (event: CustomEvent) => complete(event)}});

        await fireEvent.click(screen.getByTestId('file-edit-confirm'));

        await waitFor(() => expect(uploads.uploadFile).toHaveBeenCalledTimes(1));
        await waitFor(() => expect(complete).toHaveBeenCalledTimes(1));
        expect(complete.mock.calls[0][0].detail.url).toBe('/uploads/statement.pdf');
        const args = uploads.uploadFile.mock.calls[0];
        expect((args[0] as File).name, 'the file it renames').toBe('statement.pdf');
        return args;
    }

    it.each(['personal', 'common'] as const)('hands scope %s to uploadFile as its third argument', async (scope) => {
        const [, , passed] = await confirmUpload({scope});

        expect(passed).toBe(scope);
    });

    it('passes no scope when it is given none: the server decides (control: today’s call)', async () => {
        const [, , passed] = await confirmUpload({});

        expect(passed).toBeUndefined();
    });
});

describe('FileEditModal — the file size in the UI language, in a legacy component (M-18)', () => {
    it('English UI (control): 1.5 and the English unit, today’s exact text', () => {
        mountModal();

        expect(shownSize()).toBe(ENGLISH);
    });

    it('mounted with the UI in Italian: the size in Italian notation', async () => {
        await switchLanguage('it');
        mountModal();

        const expected = expectedSize('it');
        expect(shownSize(), spelled(expected)).toBe(expected);
    });

    it('follows an in-place switch of the UI language, en → it → en: the number', async () => {
        mountModal();
        expect(shownSize(), 'en, mount — today’s text').toBe(ENGLISH);

        await switchLanguage('it');
        expect(shownSize(), `en → it in place — Italian notation, ${spelled(expectedSize('it'))}`).toBe(expectedSize('it'));

        await switchLanguage('en');
        expect(shownSize(), 'it → en in place — today’s text again').toBe(ENGLISH);
    });

    it('follows the first in-place switch to French, whose catalogue arrives after the language: the number and the unit', async () => {
        expect(Object.keys(get(dictionary).fr ?? {}), 'precondition: the French catalogue is not loaded yet — another test of this file loaded it first').toHaveLength(0);
        mountModal();
        expect(shownSize(), 'en, mount — today’s text').toBe(ENGLISH);

        // As LanguageSelector does: the language moves at once, the catalogue follows when it has loaded.
        currentLanguage.set('fr');
        await settle();
        await waitLocale('fr');
        await settle();
        expect(get(locale), 'control: the svelte-i18n locale is fr').toBe('fr');

        expect(shownSize(), `en → fr in place — French notation and unit, ${spelled(expectedSize('fr'))}`).toBe(expectedSize('fr'));
    });
});
