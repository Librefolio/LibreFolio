/**
 * Gallery — the runtime twin of gate G3 (plan G-18): at every shot, the elements of the page whose class mixes a colour
 * role with a legacy colour class.
 *
 * G3 (`frontend/scripts/theme/theme-roles.mjs`) forbids an element carrying both a role utility (`bg-lf-card`) and a
 * legacy colour class (`text-gray-500`): app.css exempts from its legacy dark remap every element carrying a role, so a
 * half-migrated element keeps half of its old colours in the dark theme. The gate reads the sources, and sees a class
 * string only where one file writes it whole. A class composed at runtime escapes it: a `className` or `contentClass`
 * prop passed from another area, an imported constant, a concatenation. The rendered page holds them all, so this module
 * applies the gate's rule to every class attribute of the page — with the gate's own patterns, `ROLE_CLASS_RE` and
 * `LEGACY_CLASS_RE`, imported from theme-roles.mjs once per worker and never copied.
 *
 * ## Opt-in, and only a report
 *
 * It runs only when `LF_GALLERY_MIXED_DIR` names a directory, which `scripts/visual_review/gallery_snapshot.sh` sets: CI
 * and `dev.py mkdocs gallery` leave it unset, and there it does nothing. `gallery_tool mixed --collect` merges the
 * directory's files into `<snapshot>/mixed_elements.json`.
 *
 * `captureShot` (galleryShot.ts) calls it once the picture is taken, so it cannot change one, and the scan only reads the
 * page. It reports and never judges: no `expect`, no throw. A failure of its own — the gate not loaded, a scan that failed
 * or ran past {@link SCAN_TIMEOUT_MS}, a record not written — leaves a record or a log line (⚠️), and the test goes on.
 *
 * ## The record
 *
 * One JSON line per shot, appended to `worker-<pid>.jsonl` in that directory: one file per worker process, so no file has
 * two writers.
 *
 *     {"v":1,"shot":"desktop/en/dark/settings/preferences","t":"2026-10-16T09:12:03.456Z","ms":9,"elements":1830,"role":412,"legacy":977,"mixed":[…],"truncated":false}
 *
 * `shot` is `viewport/lang/theme/category/name`, its picture `<gallery>/<shot>.png`; `ms` the scan's duration; `elements`
 * counts the elements with a class, `role` and `legacy` those carrying a role utility and a legacy class. `mixed` has one
 * entry per distinct mixed element, at most {@link MAX_ENTRIES} of them — past those, `truncated` is true:
 *
 * - `tag`, and `testid`: its own test id, or null;
 * - `owner`: the test id of its nearest ancestor with one, or null. Where the element is, a hint of where its class comes
 *   from, no proof: a class prop arrives from the caller;
 * - `selector`: from its own test id, or from its owner's (`body` without one) down at most {@link MAX_STEPS} steps;
 * - `legacy` and `role`: the distinct matches of each pattern, in order;
 * - `classes`: the class attribute, its whitespace collapsed, cut at {@link MAX_CLASSES_CHARS} characters;
 * - `onScreen`: drawn, and meeting the viewport, by the test of `shotFingerprint` (galleryShot.ts);
 * - `count`: how many elements share its `tag`, `testid`, `owner` and `classes`. One of them on screen sets `onScreen`;
 *   `selector` is the first one's.
 *
 * A shot whose scan failed has `{"v":1,"shot":…,"t":…,"error":"…"}` instead. A shot with mixed elements says so in the
 * run's log (🎨): how many, and how many of them on screen.
 */

import type {Page} from '@playwright/test';
import {appendFileSync, mkdirSync} from 'node:fs';
import path from 'node:path';

/**
 * The gate's module. Its specifier is not a literal on purpose: given one, `tsc -p tsconfig.e2e.json`, which has no
 * `allowJs`, looks for the module's types and fails (TS7016).
 */
const GATE_MODULE = new URL('../../scripts/theme/theme-roles.mjs', import.meta.url).href;

/** How long the scan may take. */
const SCAN_TIMEOUT_MS = 10_000;

/** How many distinct mixed elements a record keeps. */
const MAX_ENTRIES = 200;

/** How much of a class attribute a record keeps. */
const MAX_CLASSES_CHARS = 300;

/** How many steps a selector goes down from its anchor: past them, it keeps the last ones under a descendant combinator. */
const MAX_STEPS = 4;

/** The two patterns of theme-roles.mjs that G3 applies. */
interface GatePatterns {
    ROLE_CLASS_RE: RegExp;
    LEGACY_CLASS_RE: RegExp;
}

/** Their sources: all of them that crosses into the page. */
interface PatternSources {
    role: string;
    legacy: string;
}

/** A distinct mixed element of the shot (the module's header). */
interface MixedEntry {
    tag: string;
    testid: string | null;
    owner: string | null;
    selector: string;
    legacy: string[];
    role: string[];
    classes: string;
    onScreen: boolean;
    count: number;
}

/** What the scan of the page counts and finds. */
interface PageScan {
    elements: number;
    role: number;
    legacy: number;
    mixed: MixedEntry[];
    truncated: boolean;
}

/** A shot's line: its scan, or the error that stopped it. */
type ShotRecord = ({v: 1; shot: string; t: string; ms: number} & PageScan) | {v: 1; shot: string; t: string; error: string};

/** The gate's patterns, imported by the first shot that records and kept for the worker's life — a failure as well. */
let gateSources: Promise<PatternSources> | undefined;

/** A failure every shot of a worker would repeat is logged once: the gate not loaded, a record not written. */
let gateFailureLogged = false;
let writeFailureLogged = false;

/** The directory this worker made. */
let madeDir: string | undefined;

/** The gate's patterns, as their sources. */
async function importGate(): Promise<PatternSources> {
    const gate = (await import(GATE_MODULE)) as GatePatterns;
    if (!(gate.ROLE_CLASS_RE instanceof RegExp) || !(gate.LEGACY_CLASS_RE instanceof RegExp)) throw new Error('theme-roles.mjs exports no ROLE_CLASS_RE or no LEGACY_CLASS_RE pattern');
    return {role: gate.ROLE_CLASS_RE.source, legacy: gate.LEGACY_CLASS_RE.source};
}

/** The first line of an error's message: a record and a log line stay on one line. */
function messageOf(error: unknown): string {
    const message = error instanceof Error ? error.message : String(error);
    return (
        message
            .split('\n')
            .map((line) => line.trim())
            .find((line) => line !== '') ?? 'unknown error'
    );
}

/** `work`, or a rejection once `ms` have passed; the timer never outlives the race. */
async function withTimeout<T>(work: Promise<T>, ms: number): Promise<T> {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const timeout = new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error(`the scan took more than ${ms / 1000} s`)), ms);
    });
    try {
        return await Promise.race([work, timeout]);
    } finally {
        clearTimeout(timer);
    }
}

/** Read every class attribute of the page with the gate's patterns: one evaluate, which writes nothing, scrolls nothing and focuses nothing. */
function scanPage(page: Page, sources: PatternSources): Promise<PageScan> {
    return page.evaluate(
        ({role, legacy, maxEntries, maxClassesChars, maxSteps}) => {
            // As G3 tests a class string (theme-roles.mjs, hasRoleClass): a copy without `g`, which carries no lastIndex from
            // one element to the next. The global copies serve matchAll alone.
            const roleTest = new RegExp(role);
            const legacyTest = new RegExp(legacy);
            const roleAll = new RegExp(role, 'g');
            const legacyAll = new RegExp(legacy, 'g');
            const matches = (pattern: RegExp, value: string): string[] => [...new Set(Array.from(value.matchAll(pattern), (match) => match[0]))];
            // The test of shotFingerprint (galleryShot.ts).
            const onScreen = (element: Element): boolean => {
                if (element.getClientRects().length === 0 || getComputedStyle(element).visibility !== 'visible') return false;
                const box = element.getBoundingClientRect();
                return box.width > 0 && box.height > 0 && box.bottom > 0 && box.right > 0 && box.top < window.innerHeight && box.left < window.innerWidth;
            };
            const byTestId = (id: string): string => `[data-testid="${id.replace(/["\\]/g, '\\$&')}"]`;
            // The local name, not the tag name: an SVG element keeps its case (`foreignObject`), and a selector matches it only so.
            const step = (element: Element): string => {
                const parent = element.parentElement;
                const sameTag = parent ? Array.from(parent.children).filter((sibling) => sibling.localName === element.localName) : [];
                return sameTag.length > 1 ? `${element.localName}:nth-of-type(${sameTag.indexOf(element) + 1})` : element.localName;
            };
            const selectorOf = (element: Element, testid: string | null, ownerElement: Element | null): string => {
                if (testid !== null) return byTestId(testid);
                const anchor = ownerElement ?? document.body;
                const steps: string[] = [];
                let node: Element | null = element;
                let depth = 0;
                while (node && node !== anchor) {
                    if (depth < maxSteps) steps.unshift(step(node));
                    node = node.parentElement;
                    depth += 1;
                }
                // Outside the body (the root, the head): the steps from the root.
                if (!node) return steps.join(' > ');
                const from = ownerElement ? byTestId(ownerElement.getAttribute('data-testid') ?? '') : 'body';
                if (steps.length === 0) return from;
                return `${from}${depth > maxSteps ? ' ' : ' > '}${steps.join(' > ')}`;
            };

            let elements = 0;
            let roleCount = 0;
            let legacyCount = 0;
            let truncated = false;
            const entries = new Map<string, MixedEntry>();
            for (const element of document.querySelectorAll('[class]')) {
                // The attribute, not className: an SVG element's className is an SVGAnimatedString.
                const value = element.getAttribute('class') ?? '';
                if (value.trim() === '') continue;
                elements += 1;
                const hasRole = roleTest.test(value);
                const hasLegacy = legacyTest.test(value);
                if (hasRole) roleCount += 1;
                if (hasLegacy) legacyCount += 1;
                if (!hasRole || !hasLegacy) continue;
                const tag = element.localName.toLowerCase();
                const testid = element.getAttribute('data-testid');
                const ownerElement = element.parentElement?.closest('[data-testid]') ?? null;
                const owner = ownerElement?.getAttribute('data-testid') ?? null;
                const classes = value.replace(/\s+/g, ' ').trim().slice(0, maxClassesChars);
                const key = JSON.stringify([tag, testid, owner, classes]);
                const seen = entries.get(key);
                if (seen) {
                    seen.count += 1;
                    if (!seen.onScreen) seen.onScreen = onScreen(element);
                } else if (entries.size < maxEntries) {
                    entries.set(key, {tag, testid, owner, selector: selectorOf(element, testid, ownerElement), legacy: matches(legacyAll, value), role: matches(roleAll, value), classes, onScreen: onScreen(element), count: 1});
                } else {
                    truncated = true;
                }
            }
            return {elements, role: roleCount, legacy: legacyCount, mixed: [...entries.values()], truncated};
        },
        {role: sources.role, legacy: sources.legacy, maxEntries: MAX_ENTRIES, maxClassesChars: MAX_CLASSES_CHARS, maxSteps: MAX_STEPS},
    );
}

/** The record of a shot whose scan did not happen, or failed. */
function failed(shot: string, error: unknown): ShotRecord {
    return {v: 1, shot, t: new Date().toISOString(), error: messageOf(error)};
}

/** The shot's record — its scan, or the error that stopped it — and its line in the log. Never throws. */
async function recordOf(page: Page, shot: string): Promise<ShotRecord> {
    let sources: PatternSources;
    try {
        gateSources ??= importGate();
        sources = await gateSources;
    } catch (error) {
        if (!gateFailureLogged) console.log(`  ⚠️ ${shot}: theme-roles.mjs not loaded, no shot of this worker is scanned for mixed elements: ${messageOf(error)}`);
        gateFailureLogged = true;
        return failed(shot, error);
    }
    try {
        const started = Date.now();
        const scan = await withTimeout(scanPage(page, sources), SCAN_TIMEOUT_MS);
        const ms = Date.now() - started;
        const mixed = scan.mixed.reduce((sum, entry) => sum + entry.count, 0);
        const onScreen = scan.mixed.reduce((sum, entry) => sum + (entry.onScreen ? entry.count : 0), 0);
        if (mixed > 0) console.log(`  🎨 ${shot}: ${mixed} mixed (${onScreen} on screen)`);
        return {v: 1, shot, t: new Date().toISOString(), ms, elements: scan.elements, role: scan.role, legacy: scan.legacy, mixed: scan.mixed, truncated: scan.truncated};
    } catch (error) {
        console.log(`  ⚠️ ${shot}: the scan for mixed elements failed: ${messageOf(error)}`);
        return failed(shot, error);
    }
}

/** Append the shot's record to this worker's file. A failure is logged, once per worker, and never thrown. */
function writeRecord(dir: string, shot: string, record: ShotRecord): void {
    try {
        if (madeDir !== dir) {
            mkdirSync(dir, {recursive: true});
            madeDir = dir;
        }
        appendFileSync(path.join(dir, `worker-${process.pid}.jsonl`), `${JSON.stringify(record)}\n`);
    } catch (error) {
        if (!writeFailureLogged) console.log(`  ⚠️ ${shot}: a record of mixed elements could not be written (logged once per worker): ${messageOf(error)}`);
        writeFailureLogged = true;
    }
}

/**
 * Record the mixed elements of the page as the shot `shot` (`viewport/lang/theme/category/name`) pictured it, when
 * `LF_GALLERY_MIXED_DIR` asks for them; otherwise return at once. Never throws, and never fails the test.
 */
export async function recordMixedElements(page: Page, shot: string): Promise<void> {
    const dir = process.env.LF_GALLERY_MIXED_DIR;
    if (!dir) return;
    writeRecord(dir, shot, await recordOf(page, shot));
}
