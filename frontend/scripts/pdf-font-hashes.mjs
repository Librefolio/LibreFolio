#!/usr/bin/env node
/**
 * The list of the PDF viewer's CJK fonts the server may fetch, with the hash each one must have (lot H-55, decision (c)).
 *
 * The viewer asks for a Japanese, Korean or Chinese font only when a PDF needs it; the server fetches that file once from
 * jsDelivr (`backend/app/services/files/pdf_fonts.py`), keeps it only if its sha256 is the one written here, and serves
 * it from its own origin, so the Content-Security-Policy keeps `connect-src 'self'`. The list is read from the copies the
 * lock installed in `node_modules/@embedpdf/fonts-{jp,kr,sc,tc}`: the same files, byte for byte, at the same version.
 *
 *   node scripts/pdf-font-hashes.mjs          writes backend/app/services/files/pdf_font_hashes.json
 *   node scripts/pdf-font-hashes.mjs --check  exits 1 when the file differs from what it would write
 *
 * `src/lib/utils/files/pdfFontHashes.test.ts` keeps the file equal to the installed packages.
 */
import {createHash} from 'node:crypto';
import {readdirSync, readFileSync, writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const FRONTEND = join(dirname(fileURLToPath(import.meta.url)), '..');
export const PACKAGES = ['fonts-jp', 'fonts-kr', 'fonts-sc', 'fonts-tc'];
export const OUTPUT = join(FRONTEND, '..', 'backend', 'app', 'services', 'files', 'pdf_font_hashes.json');

/** @typedef {{package: string, file: string, size: number, sha256: string}} FontHash */
/** @typedef {{version: string, files: FontHash[]}} FontHashList */

/**
 * The list as the installed packages give it: one version for all of them, every font file with its size and sha256.
 * @param {string} [frontendDir]
 * @returns {FontHashList}
 */
export function fontHashList(frontendDir = FRONTEND) {
    /** @type {Set<string>} */
    const versions = new Set();
    /** @type {FontHash[]} */
    const files = [];
    for (const pkg of PACKAGES) {
        const root = join(frontendDir, 'node_modules', '@embedpdf', pkg);
        versions.add(JSON.parse(readFileSync(join(root, 'package.json'), 'utf8')).version);
        for (const file of readdirSync(join(root, 'fonts')).sort()) {
            const bytes = readFileSync(join(root, 'fonts', file));
            files.push({package: pkg, file, size: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex')});
        }
    }
    if (versions.size !== 1) throw new Error(`the CJK font packages are at different versions: ${[...versions].join(', ')}`);
    return {version: [...versions][0], files};
}

/**
 * The file's text: two-space JSON, one trailing newline.
 * @param {FontHashList} list
 * @returns {string}
 */
export function fontHashText(list) {
    return `${JSON.stringify(list, null, 2)}\n`;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
    const text = fontHashText(fontHashList());
    if (process.argv.includes('--check')) {
        let current = '';
        try {
            current = readFileSync(OUTPUT, 'utf8');
        } catch {
            current = '';
        }
        if (current !== text) {
            console.error(`${OUTPUT} differs from the installed CJK font packages: run node scripts/pdf-font-hashes.mjs`);
            process.exit(1);
        }
    } else {
        writeFileSync(OUTPUT, text);
        console.log(`wrote ${OUTPUT}`);
    }
}
