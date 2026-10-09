/**
 * Where the PDF viewer (EmbedPDF) gets what it loads, so that previewing a PDF asks nothing of a third party.
 *
 * Out of the box the viewer fetches its PDFium engine and the fonts a PDF does not embed from a CDN (jsDelivr), its
 * interface font from Google Fonts, and a stamp library from jsDelivr again — on every preview, and nothing works
 * without the internet. LibreFolio ships the engine and the fallback fonts most PDFs need as build assets, and turns
 * off what a read-only preview never uses:
 *
 * - the engine (`pdfium.wasm`), the snippet's own pinned dependency, so the version always matches the snippet;
 * - the fallback fonts for Cyrillic, Greek and Vietnamese text (Noto Sans, regular and bold, upright and italic),
 *   Arabic (Noto Naskh Arabic) and Hebrew (Noto Sans Hebrew);
 * - Chinese, Japanese and Korean stay on the CDN, fetched only for a PDF that needs them: tens of megabytes each,
 *   too heavy to ship in the image;
 * - the interface font is the app's own, the signature fonts and the stamp library are not loaded at all: the preview
 *   cannot sign or stamp.
 *
 * Our copies come first; when they cannot be reached, the viewer falls back on its CDN defaults, so a broken
 * deployment still previews PDFs.
 */

import type {PDFViewerConfig} from '@embedpdf/snippet';
import {FontCharset} from '@embedpdf/models';
import {fonts as arabicFonts} from '@embedpdf/fonts-arabic';
import {fonts as hebrewFonts} from '@embedpdf/fonts-hebrew';
import {fonts as japaneseFonts} from '@embedpdf/fonts-jp';
import {fonts as koreanFonts} from '@embedpdf/fonts-kr';
import {fonts as latinFonts} from '@embedpdf/fonts-latin';
import {fonts as simplifiedChineseFonts} from '@embedpdf/fonts-sc';
import {fonts as traditionalChineseFonts} from '@embedpdf/fonts-tc';
import pdfiumWasm from '@embedpdf/pdfium/pdfium.wasm?url';
// The font packages export no file paths, so the files are taken from the installed packages by path.
import notoSansRegular from '../../../../node_modules/@embedpdf/fonts-latin/fonts/NotoSans-Regular.ttf?url';
import notoSansItalic from '../../../../node_modules/@embedpdf/fonts-latin/fonts/NotoSans-Italic.ttf?url';
import notoSansBold from '../../../../node_modules/@embedpdf/fonts-latin/fonts/NotoSans-Bold.ttf?url';
import notoSansBoldItalic from '../../../../node_modules/@embedpdf/fonts-latin/fonts/NotoSans-BoldItalic.ttf?url';
import notoNaskhArabicRegular from '../../../../node_modules/@embedpdf/fonts-arabic/fonts/NotoNaskhArabic-Regular.ttf?url';
import notoNaskhArabicBold from '../../../../node_modules/@embedpdf/fonts-arabic/fonts/NotoNaskhArabic-Bold.ttf?url';
import notoSansHebrewRegular from '../../../../node_modules/@embedpdf/fonts-hebrew/fonts/NotoSansHebrew-Regular.ttf?url';
import notoSansHebrewBold from '../../../../node_modules/@embedpdf/fonts-hebrew/fonts/NotoSansHebrew-Bold.ttf?url';

type FontFallback = NonNullable<PDFViewerConfig['fontFallback']>;
type FontFile = {file: string; weight?: number; italic?: boolean};

/** The engine as a build asset: `/_app/immutable/assets/pdfium.<hash>.wasm` once built. */
export const LOCAL_PDF_ENGINE = pdfiumWasm;

/** The fallback fonts shipped with LibreFolio, by file name as the font packages list them. */
export const LOCAL_FONT_FILES: Readonly<Record<string, string>> = {
    'NotoSans-Regular.ttf': notoSansRegular,
    'NotoSans-Italic.ttf': notoSansItalic,
    'NotoSans-Bold.ttf': notoSansBold,
    'NotoSans-BoldItalic.ttf': notoSansBoldItalic,
    'NotoNaskhArabic-Regular.ttf': notoNaskhArabicRegular,
    'NotoNaskhArabic-Bold.ttf': notoNaskhArabicBold,
    'NotoSansHebrew-Regular.ttf': notoSansHebrewRegular,
    'NotoSansHebrew-Bold.ttf': notoSansHebrewBold,
};

/**
 * The version of the CJK font packages the CDN URLs point at: the one installed, so the file names they list exist
 * there (the viewer's own default asks for `@latest`). A unit test keeps it equal to the installed packages.
 */
export const CDN_FONTS_VERSION = '1.0.0';
const CDN_FONTS_BASE = 'https://cdn.jsdelivr.net/npm/@embedpdf';

/** Whether `url` can be fetched. Never throws. */
export type AssetProbe = (url: string) => Promise<boolean>;

/** A HEAD request answered with a 2xx: the asset is there, and checking costs no body. */
export const headProbe: AssetProbe = async (url) => {
    try {
        return (await fetch(url, {method: 'HEAD'})).ok;
    } catch {
        return false;
    }
};

/** What changes with where the assets come from: absent keys leave the viewer on its CDN defaults. */
export interface PdfViewerAssets {
    wasmUrl?: string;
    fontFallback?: FontFallback;
}

/**
 * Our engine and fonts when our copy of the engine answers, the viewer's CDN defaults otherwise. URLs are absolute:
 * the engine runs in a worker started from a blob, where a relative URL has nothing to resolve against.
 */
export async function pdfViewerAssets(base: string, probe: AssetProbe = headProbe): Promise<PdfViewerAssets> {
    const wasmUrl = new URL(LOCAL_PDF_ENGINE, base).href;
    if (!(await probe(wasmUrl))) return {};
    return {wasmUrl, fontFallback: localFontFallback(base)};
}

/**
 * The viewer's own fallback map (charset → fonts), with the scripts we ship pointing at our copies and the CJK ones at
 * the CDN. Only the variants we ship are listed: the engine picks the closest one for a weight it is not given.
 */
export function localFontFallback(base: string): FontFallback {
    const local = (files: readonly FontFile[]) => files.filter((font) => font.file in LOCAL_FONT_FILES).map((font) => ({url: new URL(LOCAL_FONT_FILES[font.file], base).href, weight: font.weight, italic: font.italic}));
    const cdn = (pkg: string, files: readonly FontFile[]) => files.map((font) => ({url: `${CDN_FONTS_BASE}/${pkg}@${CDN_FONTS_VERSION}/fonts/${font.file}`, weight: font.weight, italic: font.italic}));
    const latin = local(latinFonts);
    return {
        fonts: {
            [FontCharset.CYRILLIC]: latin,
            [FontCharset.GREEK]: latin,
            [FontCharset.VIETNAMESE]: latin,
            [FontCharset.ARABIC]: local(arabicFonts),
            [FontCharset.HEBREW]: local(hebrewFonts),
            [FontCharset.SHIFTJIS]: cdn('fonts-jp', japaneseFonts),
            [FontCharset.HANGEUL]: cdn('fonts-kr', koreanFonts),
            [FontCharset.GB2312]: cdn('fonts-sc', simplifiedChineseFonts),
            [FontCharset.CHINESEBIG5]: cdn('fonts-tc', traditionalChineseFonts),
        },
    };
}

/**
 * What a read-only preview turns off, wherever the assets come from: the interface in the app's own font (no Google
 * Fonts stylesheet), no signature fonts and no stamp library (the preview cannot sign or stamp).
 */
export function pdfViewerOfflineOptions(uiFontFamily: string): Pick<PDFViewerConfig, 'fonts' | 'stamp'> {
    return {
        fonts: {ui: {family: uiFontFamily, stylesheetUrl: null}, signature: null},
        stamp: {manifests: []},
    };
}
