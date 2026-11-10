/**
 * The server's list of CJK PDF fonts — unit tests (H-55 wave 4, decision (c)).
 *
 * The server fetches a Japanese, Korean or Chinese fallback font once from jsDelivr and keeps it only if its sha256 is the
 * one in `backend/app/services/files/pdf_font_hashes.json` (`pdf_fonts.py`). That list is not written by hand: it is
 * generated from the copies the lock installed in `node_modules/@embedpdf/fonts-{jp,kr,sc,tc}`
 * (`scripts/pdf-font-hashes.mjs`), and this test is the guard that keeps it so. It reads the committed file and the
 * installed packages and says:
 *
 * - the committed list is, byte for byte, what the script would write for the packages installed now: a package updated
 *   without regenerating the list (`node scripts/pdf-font-hashes.mjs`) turns this red, instead of the server refusing
 *   every font in production with a hash mismatch;
 * - it holds the 26 files of the four packages, each one of them, and no other package;
 * - its version is the version of each package's `package.json`, which is the version the server's source URL pins.
 *
 * Green as soon as the list exists: it is a guard, not a new behaviour.
 */
import {describe, expect, it} from 'vitest';
import {existsSync, readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {fontHashList, fontHashText, OUTPUT, PACKAGES} from '../../../../scripts/pdf-font-hashes.mjs';

const EMBEDPDF = fileURLToPath(new URL('../../../../node_modules/@embedpdf/', import.meta.url));

interface HashEntry {
    package: string;
    file: string;
    size: number;
    sha256: string;
}
interface HashList {
    version: string;
    files: HashEntry[];
}

/** The committed list, parsed. */
function committed(): HashList {
    return JSON.parse(readFileSync(OUTPUT, 'utf8')) as HashList;
}

describe('pdf_font_hashes.json — the server list of CJK fonts', () => {
    it('is exactly what the installed packages give: the file the script would write, byte for byte', () => {
        expect(existsSync(OUTPUT), `${OUTPUT} is missing: run node scripts/pdf-font-hashes.mjs`).toBe(true);

        expect(readFileSync(OUTPUT, 'utf8')).toBe(fontHashText(fontHashList()));
    });

    it('lists the four CJK packages and nothing else', () => {
        expect(PACKAGES).toEqual(['fonts-jp', 'fonts-kr', 'fonts-sc', 'fonts-tc']);
        expect([...new Set(committed().files.map((entry) => entry.package))].sort()).toEqual([...PACKAGES].sort());
    });

    it('holds 26 files over the four packages, each one named once', () => {
        const {files} = committed();

        expect(files).toHaveLength(26);
        const names = files.map((entry) => `${entry.package}/${entry.file}`);
        expect(new Set(names).size, `a font is listed twice: ${names.join(', ')}`).toBe(26);
        for (const entry of files) {
            expect(entry.sha256, `${entry.package}/${entry.file}`).toMatch(/^[0-9a-f]{64}$/);
            expect(entry.size, `${entry.package}/${entry.file}`).toBeGreaterThan(0);
        }
    });

    it.each(PACKAGES)('has the version of the installed @embedpdf/%s', (name) => {
        const installed = (JSON.parse(readFileSync(`${EMBEDPDF}${name}/package.json`, 'utf8')) as {version: string}).version;

        expect(committed().version, `@embedpdf/${name} was updated: run node scripts/pdf-font-hashes.mjs`).toBe(installed);
    });
});
