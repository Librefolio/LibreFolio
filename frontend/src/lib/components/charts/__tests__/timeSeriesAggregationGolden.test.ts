/**
 * Golden identity net for the four `groupPointsByBucket` consumers.
 *
 * WHAT THIS TEST IS FOR
 * ---------------------
 * `groupPointsByBucket` (private, `timeSeriesAggregation.ts:59`) is about to have
 * its parameter generalised. This file replays a fixed catalogue of inputs
 * through the four functions that call it and compares the result, field for
 * field, against `fixtures/timeSeriesAggregation.golden.v1.json` — a record
 * captured from the implementation BEFORE that refactor.
 *
 * WHY IT IS NOT JUST MORE ASSERTIONS
 * ----------------------------------
 * `timeSeriesAggregation.test.ts` next door encodes what someone believed these
 * functions should do. That has its own value, but it is not a refactor net: it
 * only covers the cases somebody thought of. These goldens encode what the code
 * ACTUALLY did, including at edges nobody designed for — see
 * `revisited-bucket-non-monotonic` and `fully-unsorted-descending`, which pin
 * the fact that grouping compares against the previous group only, so a
 * Map-keyed rewrite would quietly change the output.
 *
 * WHY THE EXPECTATIONS LIVE IN A SEPARATE COMMITTED FILE
 * -----------------------------------------------------
 * If the expected values were re-derived from the code at run time, this test
 * would compare the implementation against itself and stay green through any
 * change at all — worse than no test, because it manufactures confidence. The
 * JSON is the frozen half of the comparison and must be read as a pre-refactor
 * artefact, not as something regenerated alongside the code it checks.
 *
 * HOW A REAL BEHAVIOUR CHANGE IS SUPPOSED TO BE ACCEPTED
 * -----------------------------------------------------
 * `node src/lib/components/charts/__tests__/fixtures/regenerateTimeSeriesAggregationGolden.ts`
 * reports the drift and writes nothing. With `--accept` it rewrites the fixture,
 * and this file STAYS RED, because `GOLDEN_DIGEST` below is a literal the script
 * deliberately never touches. Accepting new behaviour therefore costs a second
 * manual edit in a second file, with the printed diff in front of you. There is
 * no `vitest -u` shortcut: this test uses no snapshot mechanism at all.
 */
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';

import {describe, expect, it} from 'vitest';

import {GOLDEN_CASES, GOLDEN_FORMAT_VERSION, GOLDEN_FUNCTIONS, GOLDEN_RESOLUTIONS, canonicalStringify, captureGoldenCorpus, expectedGoldenKeys, goldenDigest, type EncodedValue, type GoldenEntries, type GoldenEntry} from './fixtures/timeSeriesAggregationGoldenCases.ts';

/**
 * Digest of the recorded entries, as captured from commit eba37ba41 — i.e. from
 * the pre-refactor implementation.
 *
 * DO NOT update this because the test went red. A mismatch means the recorded
 * behaviour and the current behaviour disagree, which is the single thing this
 * file exists to detect. Only change it together with a reviewed regeneration.
 */
const GOLDEN_DIGEST = 'sha256:046dce7cee5eb24c9511b99835b5d649d0b6b0c0165954b479527e2e06aa097c';

/** Literals, not derived: a regeneration that quietly drops cases has to fail here. */
const EXPECTED_CASE_COUNT = 23;
const EXPECTED_ENTRY_COUNT = 276; // 4 functions x 23 cases x 3 resolutions

interface GoldenFile {
    meta: Record<string, string>;
    formatVersion: number;
    entries: GoldenEntries;
}

const goldenPath = new URL('./fixtures/timeSeriesAggregation.golden.v1.json', import.meta.url);
const golden = JSON.parse(readFileSync(goldenPath, 'utf8')) as GoldenFile;

const captured = captureGoldenCorpus();

function entryText(entry: GoldenEntry): string {
    return canonicalStringify(entry as unknown as EncodedValue);
}

describe('timeSeriesAggregation golden corpus (pre-refactor capture)', () => {
    it('is the same record this test was written against', () => {
        // Tamper evidence. Computed over the canonical form, so prettier
        // reformatting the fixture is invisible here while a single changed
        // number is not.
        expect(goldenDigest(golden.entries), 'fixtures/timeSeriesAggregation.golden.v1.json no longer matches GOLDEN_DIGEST. Either the fixture was regenerated (accept it deliberately, after reading the drift the regenerate script prints) or it was hand-edited (do not).').toBe(GOLDEN_DIGEST);

        expect(golden.formatVersion).toBe(GOLDEN_FORMAT_VERSION);
    });

    it('covers exactly the declared matrix of functions, cases and resolutions', () => {
        expect(GOLDEN_CASES.length).toBe(EXPECTED_CASE_COUNT);
        expect(GOLDEN_FUNCTIONS.length).toBe(4);
        expect(GOLDEN_RESOLUTIONS).toEqual(['daily', 'weekly', 'monthly']);

        const expectedKeys = expectedGoldenKeys();
        expect(expectedKeys.length).toBe(EXPECTED_ENTRY_COUNT);
        expect(new Set(expectedKeys).size).toBe(EXPECTED_ENTRY_COUNT);

        // Exact set equality both ways: a missing entry must fail rather than
        // silently reduce the corpus to whatever the fixture happens to hold.
        expect([...Object.keys(golden.entries)].sort()).toEqual([...expectedKeys].sort());

        for (const fn of GOLDEN_FUNCTIONS) {
            const perFunction = Object.keys(golden.entries).filter((key) => key.startsWith(`${fn}|`));
            expect(perFunction.length, `${fn} should have one entry per case per resolution`).toBe(EXPECTED_CASE_COUNT * GOLDEN_RESOLUTIONS.length);

            for (const resolution of GOLDEN_RESOLUTIONS) {
                expect(perFunction.filter((key) => key.endsWith(`|${resolution}`)).length, `${fn} at ${resolution}`).toBe(EXPECTED_CASE_COUNT);
            }
        }

        // Case ids must be unique, or two cases would collide on one key.
        expect(new Set(GOLDEN_CASES.map((goldenCase) => goldenCase.id)).size).toBe(EXPECTED_CASE_COUNT);
    });

    it.each([...GOLDEN_FUNCTIONS])('%s still behaves exactly as recorded before the refactor', (fn) => {
        const keys = expectedGoldenKeys().filter((key) => key.startsWith(`${fn}|`));
        expect(keys.length).toBeGreaterThan(0);

        for (const key of keys) {
            const recorded = golden.entries[key];
            const live = captured.entries[key];

            // Whole-entry structural comparison first: it gives the readable
            // diff. The text comparison after it is what makes the assertion
            // total — it also catches an extra key that toStrictEqual would
            // report identically but which would change the digest.
            expect(live, key).toStrictEqual(recorded);
            expect(entryText(live), key).toBe(entryText(recorded));
        }
    });

    it('still guards every groupPointsByBucket consumer, and only those', () => {
        // The corpus is only a net for the functions it covers. If the refactor
        // (or anything after it) adds a fifth consumer, that consumer would be
        // unprotected and nothing would say so — hence this check, re-derived
        // from the source on every run rather than trusted from a comment.
        const source = readFileSync(new URL('../timeSeriesAggregation.ts', import.meta.url), 'utf8');

        const declaration = /^(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)/;
        const consumers = new Set<string>();
        let enclosing: string | null = null;

        for (const line of source.split('\n')) {
            const declared = declaration.exec(line);
            if (declared) {
                // Skips the helper's own declaration line, which of course
                // contains its name.
                enclosing = declared[1];
                continue;
            }
            if (enclosing && enclosing !== 'groupPointsByBucket' && /\bgroupPointsByBucket\s*\(/.test(line)) consumers.add(enclosing);
        }

        expect([...consumers].sort(), 'The set of functions calling groupPointsByBucket changed. If a consumer was added, capture goldens for it before refactoring; if the helper was renamed or inlined, this guard needs rewriting against the new shape — do not just delete it.').toEqual(
            [...GOLDEN_FUNCTIONS].sort(),
        );
    });

    it('records aggregateEnvelope because it consumes groupPointsByBucket, not because it is independent', () => {
        // Stated as an assertion rather than a comment because the opposite
        // belief ("envelope groups on its own") would make its goldens look like
        // dead weight to a later cleanup, and would remove the net from a
        // function squarely in the refactor's blast radius.
        const source = readFileSync(new URL('../timeSeriesAggregation.ts', import.meta.url), 'utf8');
        const body = source.slice(source.indexOf('export function aggregateEnvelope'));
        const envelope = body.slice(0, body.indexOf('\ninterface RenderBucket'));

        expect(envelope).toContain('groupPointsByBucket(middleData, resolution)');
        // And indirectly a second time, through the middle band.
        expect(envelope).toContain('aggregateLineSeries(middleData, resolution)');
    });
});

describe('golden corpus self-checks', () => {
    it('keeps every envelope band aligned with its middle series', () => {
        // aggregateEnvelope indexes `upper`/`lower` by the middle series' own
        // indexes, so a ragged fixture would read `undefined` and record a NaN
        // that says nothing about grouping.
        for (const goldenCase of GOLDEN_CASES) {
            expect(goldenCase.bands.upper.length, `${goldenCase.id} upper`).toBe(goldenCase.points.length);
            expect(goldenCase.bands.lower.length, `${goldenCase.id} lower`).toBe(goldenCase.points.length);
        }
    });

    it('is deterministic: capturing twice in the same process gives byte-identical results', () => {
        // No clock, no locale, no iteration-order dependence. If this ever fails,
        // every other assertion in this file is worthless.
        const first = canonicalStringify(captureGoldenCorpus().entries as unknown as EncodedValue);
        const second = canonicalStringify(captureGoldenCorpus().entries as unknown as EncodedValue);
        expect(first).toBe(second);
        expect(`sha256:${createHash('sha256').update(first).digest('hex')}`).toBe(GOLDEN_DIGEST);
    });
});
