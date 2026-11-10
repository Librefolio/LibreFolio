/**
 * pdfViewerAssets — unit tests
 *
 * Where the PDF viewer (EmbedPDF) gets what it loads (developer's decision, release 2 batch 7: previewing a PDF asks
 * nothing of a third party). Pinned here:
 *
 * - with our engine answering, the viewer gets absolute URLs on the app's origin — the engine runs in a worker started
 *   from a blob, where a relative URL has nothing to resolve against — for the engine and for the fallback fonts we
 *   ship (Latin/Cyrillic/Greek/Vietnamese, Arabic, Hebrew), and for the CJK fonts the app's own route
 *   `/api/v1/files/pdf-fonts/<package>/<file>` (H-55 wave 4: the server fetches them once, checks their hash and serves
 *   them; no URL anywhere names a CDN);
 * - with our engine unreachable, the promise rejects with an Error: never `{}`, which would leave the viewer on its CDN
 *   defaults. The preview catches it and shows the browser's own viewer (FilePreviewModal);
 * - the probe (a HEAD) never throws, and only a 2xx counts;
 * - the options every preview gets: the app's own UI font, no Google Fonts stylesheet, no signature fonts, no stamps.
 *
 * The expectations are not written out by hand: they are read from what the module stands on. The library's own
 * fallback map (`createCdnFontConfig`, @embedpdf/engines) is the reference for the charsets, and the font packages'
 * `fonts` metadata for each file's name, weight and style. And the last block reads the installed packages from disk
 * (`node_modules/@embedpdf/*`): the module's pins — the engine of the snippet's own version, the font files it
 * imports — hold against what `npm install` actually put there. (That the server's hash list is the installed CJK
 * packages is `pdfFontHashes.test.ts`.)
 */
import {afterEach, describe, expect, it, vi} from 'vitest';
import {existsSync, readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createCdnFontConfig} from '@embedpdf/engines/pdfium';
import {FontCharset} from '@embedpdf/models';
import {fonts as arabicFonts} from '@embedpdf/fonts-arabic';
import {fonts as hebrewFonts} from '@embedpdf/fonts-hebrew';
import {fonts as japaneseFonts} from '@embedpdf/fonts-jp';
import {fonts as koreanFonts} from '@embedpdf/fonts-kr';
import {fonts as latinFonts} from '@embedpdf/fonts-latin';
import {fonts as simplifiedChineseFonts} from '@embedpdf/fonts-sc';
import {fonts as traditionalChineseFonts} from '@embedpdf/fonts-tc';

import {headProbe, LOCAL_FONT_FILES, LOCAL_PDF_ENGINE, localFontFallback, pdfViewerAssets, pdfViewerOfflineOptions} from './pdfViewerAssets';

/** A page the preview is opened from: the URLs must land on its origin, not under its path. */
const BASE = 'http://librefolio.test:6158/files?tab=static&filename=ebook.pdf';
const ORIGIN = new URL(BASE).origin;
const CDN_HOST = 'cdn.jsdelivr.net';
const EMBEDPDF_DIR = fileURLToPath(new URL('../../../../node_modules/@embedpdf/', import.meta.url));

/** The version `npm install` put in node_modules for `@embedpdf/<name>`. */
function installedVersion(name: string): string {
    return (JSON.parse(readFileSync(`${EMBEDPDF_DIR}${name}/package.json`, 'utf-8')) as {version: string}).version;
}

/** Every string in `value`, at any depth: the keys and the values of objects, the items of arrays. */
function strings(value: unknown): string[] {
    if (typeof value === 'string') return [value];
    if (Array.isArray(value)) return value.flatMap(strings);
    if (value && typeof value === 'object') return Object.entries(value).flatMap(([key, item]) => [key, ...strings(item)]);
    return [];
}

type FontFile = {file: string; weight?: number; italic?: boolean};
type FontEntry = {url: string; weight?: number; italic?: boolean};

/** The fonts the viewer gets for one charset. */
function fontsFor(charset: FontCharset): FontEntry[] {
    const fallback = localFontFallback(BASE) as {fonts: Record<number, FontEntry[]>};
    return fallback.fonts[charset];
}

/** What the module promises for a script we ship: the package's own entries for the files we ship, on our origin. */
function shipped(files: readonly FontFile[]): FontEntry[] {
    return files.filter((font) => font.file in LOCAL_FONT_FILES).map((font) => ({url: new URL(LOCAL_FONT_FILES[font.file], BASE).href, weight: font.weight, italic: font.italic}));
}

/** The name of the file an URL points at. */
function fileOf(url: string): string {
    return decodeURIComponent(new URL(url, BASE).pathname.split('/').pop() ?? '');
}

const LOCAL_CHARSETS = [FontCharset.CYRILLIC, FontCharset.GREEK, FontCharset.VIETNAMESE, FontCharset.ARABIC, FontCharset.HEBREW];
const CJK_CHARSETS = [FontCharset.SHIFTJIS, FontCharset.HANGEUL, FontCharset.GB2312, FontCharset.CHINESEBIG5];

describe('pdfViewerAssets — our engine answers', () => {
    it('gives the viewer our engine as an absolute URL on the origin of the page it is opened from', async () => {
        const assets = await pdfViewerAssets(BASE, async () => true);

        expect(assets.wasmUrl).toBe(new URL(LOCAL_PDF_ENGINE, BASE).href);
        expect(new URL(assets.wasmUrl ?? '').origin, 'the engine is not served by the app').toBe(ORIGIN);
        expect(fileOf(assets.wasmUrl ?? ''), "the engine URL does not name pdfium's WASM").toMatch(/^pdfium(\.[\w-]+)?\.wasm$/);
    });

    it('gives the viewer our fallback fonts: the map localFontFallback builds, on the same origin', async () => {
        const assets = await pdfViewerAssets(BASE, async () => true);

        expect(assets.fontFallback).toEqual(localFontFallback(BASE));
    });

    it('gives the viewer exactly an engine and a fallback map, and no URL anywhere names the CDN (deep scan)', async () => {
        const assets = await pdfViewerAssets(BASE, async () => true);

        expect(Object.keys(assets).sort()).toEqual(['fontFallback', 'wasmUrl']);
        const found = strings(assets).filter((text) => text.includes(CDN_HOST));
        expect(found, `the assets name ${CDN_HOST}`).toEqual([]);
    });

    it('asks the probe about our engine, at its absolute URL', async () => {
        const probe = vi.fn(async () => true);
        await pdfViewerAssets(BASE, probe);

        expect(probe).toHaveBeenCalledTimes(1);
        expect(probe).toHaveBeenCalledWith(new URL(LOCAL_PDF_ENGINE, BASE).href);
    });
});

describe('pdfViewerAssets — our engine does not answer', () => {
    it('rejects with an Error, so the preview shows the browser viewer: it never resolves, to {} or to anything else', async () => {
        const probe = vi.fn(async () => false);

        await expect(pdfViewerAssets(BASE, probe)).rejects.toBeInstanceOf(Error);
        expect(probe).toHaveBeenCalledWith(new URL(LOCAL_PDF_ENGINE, BASE).href);
    });
});

describe('localFontFallback — the charsets and their fonts', () => {
    it("covers exactly the charsets of the library's own fallback map", () => {
        const ours = Object.keys((localFontFallback(BASE) as {fonts: object}).fonts).sort();
        const library = Object.keys(createCdnFontConfig(installedVersion('fonts-jp')).fonts).sort();

        expect(ours).toEqual(library);
        expect(ours.map(Number).sort()).toEqual([...LOCAL_CHARSETS, ...CJK_CHARSETS].sort());
    });

    it('serves Cyrillic, Greek and Vietnamese from our four Noto Sans files, with their weight and style from the package', () => {
        const expected = shipped(latinFonts);
        expect(expected.map((font) => fileOf(font.url))).toEqual(expect.arrayContaining(['NotoSans-Regular.ttf', 'NotoSans-Italic.ttf', 'NotoSans-Bold.ttf', 'NotoSans-BoldItalic.ttf']));
        expect(expected).toHaveLength(4);
        for (const charset of [FontCharset.CYRILLIC, FontCharset.GREEK, FontCharset.VIETNAMESE]) {
            expect(fontsFor(charset), `charset ${FontCharset[charset]}`).toEqual(expected);
        }
        // Spelled out once, so a package that changed them shows here as well.
        expect(expected.map((font) => [fileOf(font.url), font.weight, font.italic ?? false])).toEqual(
            expect.arrayContaining([
                ['NotoSans-Regular.ttf', 400, false],
                ['NotoSans-Italic.ttf', 400, true],
                ['NotoSans-Bold.ttf', 700, false],
                ['NotoSans-BoldItalic.ttf', 700, true],
            ]),
        );
    });

    it('serves Arabic and Hebrew from our two files each, regular and bold', () => {
        expect(fontsFor(FontCharset.ARABIC)).toEqual(shipped(arabicFonts));
        expect(fontsFor(FontCharset.ARABIC)).toHaveLength(2);
        expect(fontsFor(FontCharset.HEBREW)).toEqual(shipped(hebrewFonts));
        expect(fontsFor(FontCharset.HEBREW)).toHaveLength(2);
    });

    it('serves every local font as an absolute URL on the origin of the page', () => {
        for (const charset of LOCAL_CHARSETS) {
            for (const font of fontsFor(charset)) {
                expect(new URL(font.url).origin, `${FontCharset[charset]}: ${font.url}`).toBe(ORIGIN);
                expect(font.url, `${FontCharset[charset]}: a relative URL`).toBe(new URL(font.url).href);
            }
        }
    });

    it("serves Japanese, Korean and Chinese from the app's own font route, one entry per file of the package, with its weight and style", () => {
        const packages: Record<number, [string, readonly FontFile[]]> = {
            [FontCharset.SHIFTJIS]: ['fonts-jp', japaneseFonts],
            [FontCharset.HANGEUL]: ['fonts-kr', koreanFonts],
            [FontCharset.GB2312]: ['fonts-sc', simplifiedChineseFonts],
            [FontCharset.CHINESEBIG5]: ['fonts-tc', traditionalChineseFonts],
        };
        for (const charset of CJK_CHARSETS) {
            const [pkg, files] = packages[charset];
            expect(files.length, `@embedpdf/${pkg} lists no font`).toBeGreaterThan(0);
            expect(fontsFor(charset), FontCharset[charset]).toEqual(files.map((font) => ({url: new URL(`/api/v1/files/pdf-fonts/${pkg}/${font.file}`, BASE).href, weight: font.weight, italic: font.italic})));
        }
    });

    it('names the CDN nowhere in the whole map: not in a URL of any charset, local or CJK', () => {
        const found = strings(localFontFallback(BASE)).filter((text) => text.includes(CDN_HOST));
        expect(found, `the fallback map names ${CDN_HOST}`).toEqual([]);
    });
});

describe('headProbe', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    /** `fetch`, answering every request with `status` (or throwing when `status` is an Error). */
    function stubFetch(status: number | Error) {
        const fetch = vi.fn(async () => {
            if (status instanceof Error) throw status;
            return new Response(null, {status});
        });
        vi.stubGlobal('fetch', fetch);
        return fetch;
    }

    it('asks with a HEAD, at the URL it is given', async () => {
        const fetch = stubFetch(200);
        await headProbe('http://librefolio.test/_app/immutable/assets/pdfium.abc.wasm');

        expect(fetch).toHaveBeenCalledWith('http://librefolio.test/_app/immutable/assets/pdfium.abc.wasm', {method: 'HEAD'});
    });

    it.each([200, 204])('is true on a %i', async (status) => {
        stubFetch(status);
        expect(await headProbe('http://librefolio.test/engine.wasm')).toBe(true);
    });

    it.each([301, 404, 500, 503])('is false on a %i', async (status) => {
        stubFetch(status);
        expect(await headProbe('http://librefolio.test/engine.wasm')).toBe(false);
    });

    it('is false, and does not throw, when the request fails', async () => {
        stubFetch(new TypeError('Failed to fetch'));
        await expect(headProbe('http://librefolio.test/engine.wasm')).resolves.toBe(false);
    });
});

describe('pdfViewerOfflineOptions', () => {
    it("keeps the interface in the app's own font, with no stylesheet to fetch, and turns signature fonts and stamps off", () => {
        expect(pdfViewerOfflineOptions('Inter, system-ui, sans-serif')).toEqual({
            fonts: {ui: {family: 'Inter, system-ui, sans-serif', stylesheetUrl: null}, signature: null},
            stamp: {manifests: []},
        });
    });
});

describe('pdfViewerAssets — the pins hold against the installed packages', () => {
    const EMBEDPDF = EMBEDPDF_DIR;

    it("ships the engine of the snippet's own version: the one its code was built against", () => {
        expect(installedVersion('pdfium')).toBe(installedVersion('snippet'));
        expect(existsSync(`${EMBEDPDF}pdfium/dist/pdfium.wasm`), 'node_modules/@embedpdf/pdfium/dist/pdfium.wasm is missing').toBe(true);
    });

    it('ships only fonts its packages list, each one on disk, each one imported under its own name', () => {
        const packages: Array<[string, readonly FontFile[]]> = [
            ['fonts-latin', latinFonts],
            ['fonts-arabic', arabicFonts],
            ['fonts-hebrew', hebrewFonts],
        ];
        expect(Object.keys(LOCAL_FONT_FILES)).toHaveLength(8);
        for (const [file, url] of Object.entries(LOCAL_FONT_FILES)) {
            const owners = packages.filter(([, fonts]) => fonts.some((font) => font.file === file));
            expect(
                owners.map(([name]) => name),
                `${file} is listed by no font package (or by several)`,
            ).toHaveLength(1);
            const [name] = owners[0];
            expect(existsSync(`${EMBEDPDF}${name}/fonts/${file}`), `node_modules/@embedpdf/${name}/fonts/${file} is missing`).toBe(true);
            // The build may add a hash to the name; it never swaps the file.
            const stem = file.replace(/\.ttf$/, '');
            expect(fileOf(url), `LOCAL_FONT_FILES['${file}'] points at another file`).toMatch(new RegExp(`^${stem}(\\.[\\w-]+)?\\.ttf$`));
        }
    });
});
