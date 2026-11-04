/**
 * upload.ts — formatBytes, a file size in the UI language (M-18 CP1); and the scope of an upload (decision 36).
 *
 * Numbers follow the UI language (the developer's rule of 2026-10-12). `formatBytes` printed the number
 * with `toFixed(1)` — `1.5 KB` for an Italian reader, who writes `1,5 KB` — and now writes it through
 * `formatFixed(…, 1, {locale})`, with `locale` defaulting to `uiLocale()`:
 *
 *     formatBytes(bytes, translate = get(_), locale = uiLocale())
 *
 * The unit labels do not change: they still come from `translate`. Bytes below a kilobyte stay an
 * integer, written as they are.
 *
 * Expectations. Numbers come from `Intl.NumberFormat` in this runtime, never typed; English is typed
 * where it is today's exact text — the browser here is en-US, so English changes only by grouping
 * thousands. `translate` is a stub that echoes its key in brackets, so the unit asserted is the key the
 * function asked for, never a phrase from a catalogue.
 *
 * The browser. The default locale is the UI language regionalised by `navigator.language` when the two
 * agree (uiLocale.test.ts). Node's follows the host's ICU locale, so it is pinned to en-US before any
 * import, as jsdom's always is.
 *
 * The scope of an uploaded file (decision 36, CP-U2) lives in this module too, and is observed at the API
 * boundary, the one thing stubbed here: `uploadFile(file, description?, scope?)` puts `scope` in the form
 * only when it is given — without it the server decides (images common, the rest personal) — and
 * `setUploadScope(fileId, scope)` is the PATCH that changes it, answering the updated file.
 */
import {afterEach, beforeEach, describe, expect, expectTypeOf, it, vi} from 'vitest';

vi.hoisted(() => {
    vi.stubGlobal('navigator', {language: 'en-US', languages: ['en-US']});
});

const api = vi.hoisted(() => ({post: vi.fn(), patch: vi.fn()}));
vi.mock('$lib/api', () => ({
    axiosInstance: {post: api.post},
    zodiosApi: {update_file_api_v1_uploads__file_id__patch: api.patch},
}));

import {waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import type {UploadedFile, UploadScope} from '$lib/types/files';
import {formatBytes, setUploadScope, uploadFile} from './upload';

type UiLanguage = 'en' | 'it' | 'fr' | 'es';

const KIB = 1024;
const MIB = 1024 * KIB;
const GIB = 1024 * MIB;

/** Echoes the key it is asked for: the unit in the output names the key, never a translation. */
const translate = (key: string): string => `[[${key}]]`;

/** What Intl writes for `value` in `locale` with the one decimal of a size. */
function oneDecimal(locale: string, value: number): string {
    return new Intl.NumberFormat(locale, {minimumFractionDigits: 1, maximumFractionDigits: 1}).format(value);
}

/** `text` with its no-break spaces spelled out, so a message tells U+00A0 and U+202F from a space. */
function spelled(text: string): string {
    return text.replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`);
}

/** Change the UI language as LanguageSelector does; svelte-i18n settles before the next step. */
async function uiLanguage(lang: UiLanguage): Promise<void> {
    currentLanguage.set(lang);
    await waitLocale(lang);
}

/** One size per unit, each with one exact decimal in that unit: no rounding is involved. */
const SIZES = [
    {bytes: 1536, unit: 'common.kilobytes', value: 1.5},
    {bytes: 5.5 * MIB, unit: 'common.megabytes', value: 5.5},
    {bytes: 2.5 * GIB, unit: 'common.gigabytes', value: 2.5},
];

afterEach(async () => {
    // The language is module-level state shared by every test of the file.
    await uiLanguage('en');
});

describe('formatBytes — the number in the UI language, the unit from translate', () => {
    it('English UI (control): today’s exact text — one decimal, the unit asked of translate', async () => {
        await uiLanguage('en');

        expect(formatBytes(1536, translate)).toBe('1.5 [[common.kilobytes]]');
        expect(formatBytes(5.5 * MIB, translate)).toBe('5.5 [[common.megabytes]]');
        expect(formatBytes(2.5 * GIB, translate)).toBe('2.5 [[common.gigabytes]]');
        expect(formatBytes(512, translate)).toBe('512 [[common.bytes]]');
        expect(formatBytes(0, translate)).toBe('0 [[common.bytes]]');
    });

    it.each(['it', 'fr'] as const)('%s UI: the number in that language’s notation, without passing a locale', async (lang) => {
        await uiLanguage(lang);

        for (const {bytes, unit, value} of SIZES) {
            const expected = `${oneDecimal(lang, value)} [[${unit}]]`;
            // Control: the notation really differs from English in this runtime.
            expect(expected).not.toBe(`${oneDecimal('en', value)} [[${unit}]]`);
            expect(formatBytes(bytes, translate), `${bytes} bytes: ${spelled(expected)}`).toBe(expected);
        }
        // Below a kilobyte the size is an integer, written as it is in any language.
        expect(formatBytes(512, translate)).toBe('512 [[common.bytes]]');
    });

    it('English UI on an en-US browser: thousands are grouped — 2048 gigabytes', async () => {
        await uiLanguage('en');

        expect(formatBytes(2048 * GIB, translate)).toBe(`${oneDecimal('en-US', 2048)} [[common.gigabytes]]`);
        expect(formatBytes(2048 * GIB, translate)).toBe('2,048.0 [[common.gigabytes]]');
    });

    it('an explicit locale wins over the UI language', async () => {
        await uiLanguage('it');

        expect(formatBytes(1536, translate, 'fr')).toBe(`${oneDecimal('fr', 1.5)} [[common.kilobytes]]`);
        expect(formatBytes(2048 * GIB, translate, 'fr')).toBe(`${oneDecimal('fr', 2048)} [[common.gigabytes]]`);
        expect(formatBytes(1536, translate, 'en')).toBe('1.5 [[common.kilobytes]]');
    });

    it('follows the UI language from one call to the next: it → fr → en', async () => {
        const written: Record<string, string> = {};
        for (const lang of ['it', 'fr', 'en'] as const) {
            await uiLanguage(lang);
            written[lang] = formatBytes(1536, translate);
        }

        expect(written).toEqual({
            it: `${oneDecimal('it', 1.5)} [[common.kilobytes]]`,
            fr: `${oneDecimal('fr', 1.5)} [[common.kilobytes]]`,
            en: '1.5 [[common.kilobytes]]',
        });
    });
});

/** What the upload endpoint answers: the stored file, whose url `uploadFile` hands back. */
function uploaded(url: string) {
    return {data: {success: true, file: {url}}};
}

/** The form `uploadFile` posted, with the path it posted it to. */
function postedForm(): {path: string; form: FormData} {
    expect(api.post, 'uploadFile posts once').toHaveBeenCalledTimes(1);
    const [path, form] = api.post.mock.calls[0] as [string, unknown];
    expect(form, 'the body is a multipart form').toBeInstanceOf(FormData);
    return {path, form: form as FormData};
}

describe('uploadFile — the scope travels in the form only when it is given (decision 36)', () => {
    beforeEach(() => {
        api.post.mockReset();
    });

    it('without a scope the form carries no scope field: the server decides (control: today’s form)', async () => {
        api.post.mockResolvedValueOnce(uploaded('/api/v1/uploads/u-none'));
        const file = new File(['plain text'], 'notes.txt', {type: 'text/plain'});

        await expect(uploadFile(file, 'a note')).resolves.toBe('/api/v1/uploads/u-none');

        const {path, form} = postedForm();
        expect(path).toBe('/api/v1/uploads');
        expect((form.get('file') as File).name).toBe('notes.txt');
        expect(form.get('description')).toBe('a note');
        expect(form.has('scope'), 'no scope field at all, not an empty one').toBe(false);
    });

    it.each(['common', 'personal'] as const)('with scope %s the form carries exactly that scope, beside the file', async (scope) => {
        api.post.mockResolvedValueOnce(uploaded(`/api/v1/uploads/u-${scope}`));
        const file = new File(['png bytes'], 'logo.png', {type: 'image/png'});

        await expect(uploadFile(file, undefined, scope)).resolves.toBe(`/api/v1/uploads/u-${scope}`);

        const {path, form} = postedForm();
        expect(path).toBe('/api/v1/uploads');
        expect((form.get('file') as File).name).toBe('logo.png');
        expect(form.getAll('scope'), `scope=${scope}, once`).toEqual([scope]);
        expect(form.has('description'), 'no description was given').toBe(false);
    });
});

describe('setUploadScope — the PATCH that changes who sees an uploaded file (decision 36)', () => {
    beforeEach(() => {
        api.patch.mockReset();
    });

    it('is exported, with the signature (fileId, scope) → the updated file', () => {
        // Type-level (svelte-check): the scope type lives beside UploadedFile, and is its `scope`.
        expectTypeOf<UploadScope>().toEqualTypeOf<UploadedFile['scope']>();
        expectTypeOf(setUploadScope).toEqualTypeOf<(fileId: string, scope: UploadScope) => Promise<UploadedFile>>();
        // Runtime: the module exports it.
        expect(setUploadScope, 'upload.ts exports setUploadScope').toBeTypeOf('function');
    });

    it.each(['common', 'personal'] as const)('asks the PATCH alias for scope %s on that file, and answers what it answers', async (scope) => {
        const updated: UploadedFile = {
            id: 'file-1',
            original_name: 'logo.png',
            mime_type: 'image/png',
            size_bytes: 1536,
            uploaded_at: '2026-10-15T12:00:00Z',
            uploaded_by_user_id: 7,
            scope,
            can_delete: true,
            url: '/api/v1/uploads/file-1',
        };
        api.patch.mockResolvedValueOnce(updated);

        await expect(setUploadScope('file-1', scope)).resolves.toBe(updated);

        expect(api.patch).toHaveBeenCalledExactlyOnceWith({scope}, {params: {file_id: 'file-1'}});
    });

    it('rejects with the error of the PATCH, so its caller can tell the user', async () => {
        const refused = new Error('403 Cannot change files uploaded by other users');
        api.patch.mockRejectedValueOnce(refused);

        await expect(setUploadScope('file-2', 'common')).rejects.toBe(refused);
        expect(api.patch).toHaveBeenCalledExactlyOnceWith({scope: 'common'}, {params: {file_id: 'file-2'}});
    });
});
