import {describe, expect, it} from 'vitest';

import {schemas} from '$lib/api';

import {buildHypotheticalShockParameters, STRESS_ASSET_CLASSES, uniformAssetClassShocks} from './riskRequest';

/**
 * An `asset_class` stress must name **every** `AssetType`, and nothing that is not one.
 *
 * Neither mistake comes back as an error. A type with no bucket is not rejected:
 * `_resolve_bucket` (`backend/app/services/risk_plugins/stress.py`) shocks that
 * exposure by `0.0`, tags it `UNCONFIGURED_ZERO` and carries on — a book of
 * commodity ETFs comes out untouched by a crash meant to hit everything, and the
 * number is simply wrong. A bucket that is not an `AssetType` is rejected, but
 * only as far as `_normalize_bucket_shocks`: `service.py` turns the
 * `ValidationError` into the stress analytic coming back `unavailable` inside a
 * 200, with no 422 for anyone to catch.
 *
 * `RiskAnalysisPanel.svelte` shipped the first mistake. Its uniform stress (the
 * one every weighted scope runs) and its bucket editor both drew on a hand-written
 * list of nine asset classes while the enum had seventeen, and the eight left out
 * were shocked by zero, silently. The fix derives the list from the enum:
 * `STRESS_ASSET_CLASSES` and `uniformAssetClassShocks` in `riskRequest.ts`.
 *
 * The backend guards its own scenario catalogue against this exact hazard:
 * `backend/test_scripts/test_services/test_risk_scenario_catalog.py` checks every
 * built-in `asset_class` scenario in both directions — no `AssetType` without a
 * bucket, no bucket without an `AssetType`. That gate reads the YAML the backend
 * ships; it does not reach a list written in the frontend. This file is its
 * frontend counterpart, and asks the same two questions of both places the panel
 * takes asset-class buckets from.
 *
 * Two choices keep it from proving nothing:
 *
 * - The oracle is `schemas.AssetType.options`, imported here on its own — never
 *   `STRESS_ASSET_CLASSES`. The fix derives that constant from the same enum, so
 *   checking the function against it would measure the code with its own ruler,
 *   and would stay green through a return to a hand-written list: the function
 *   and the constant would regress together.
 * - The old nine-value list is kept below as a fixture and put through the same
 *   check, which must fail, with a gap that includes the eight types it missed. A
 *   coverage check that has stopped seeing anything (an enum read as empty, a
 *   filter that never matches) is green exactly like one that works; the
 *   known-answer failure is what tells the two apart. The stray half gets the
 *   same treatment: the enum plus one bogus bucket must come back with exactly
 *   that bucket named.
 */

/** The oracle: the generated client's copy of the backend enum, read independently of the code under test. */
const ASSET_TYPES: readonly string[] = schemas.AssetType.options;

/** The list `RiskAnalysisPanel.svelte` hand-wrote before the fix, verbatim — a fixture that exists to be rejected. */
const HAND_WRITTEN_LIST = ['STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND', 'CROWDFUND', 'HOLD', 'INDEX', 'OTHER'] as const;

/**
 * The eight types that list was missing when the fix landed. The control treats them
 * as a floor, not as the whole gap, so `AssetType` can grow without touching this file.
 */
const MISSED_BY_THE_HAND_WRITTEN_LIST = ['COMMODITY', 'REAL_ESTATE', 'ETF_STOCK', 'ETF_BOND', 'ETF_COMMODITY', 'ETF_REAL_ESTATE', 'ETF_CRYPTO', 'ETF_MONETARY'];

interface BucketCoverage {
    /** `AssetType` values no bucket names: shocked by 0.0 and tagged `UNCONFIGURED_ZERO`, without an error. */
    missing: string[];
    /** Bucket names that are not `AssetType` values: the backend refuses the whole stress analytic. */
    strays: string[];
}

/** The check, in both directions. Sorted, because coverage has no order and a sorted diff reads at a glance. */
function bucketCoverage(buckets: Iterable<string>): BucketCoverage {
    const named = new Set(buckets);
    const known = new Set(ASSET_TYPES);
    return {
        missing: ASSET_TYPES.filter((assetType) => !named.has(assetType)).sort(),
        strays: [...named].filter((bucket) => !known.has(bucket)).sort(),
    };
}

const FULL_COVERAGE: BucketCoverage = {missing: [], strays: []};

describe('asset_class stress buckets — every AssetType, nothing else', () => {
    it('uniformAssetClassShocks shocks every AssetType by the chosen fraction, and names no other bucket', () => {
        const shocks = uniformAssetClassShocks(-0.2);

        expect(bucketCoverage(Object.keys(shocks))).toEqual(FULL_COVERAGE);
        for (const assetType of ASSET_TYPES) {
            expect(shocks[assetType], assetType).toBe(-0.2);
        }
    });

    it('positive control: the same check fails on the old hand-written list, missing at least the eight types it forgot', () => {
        // Built the way the panel used to build it, then judged by the same check as above:
        // `missing` is `schemas.AssetType.options` minus the hand list.
        const legacyShocks: Record<string, number> = Object.fromEntries(HAND_WRITTEN_LIST.map((assetType) => [assetType, -0.2]));
        const {missing, strays} = bucketCoverage(Object.keys(legacyShocks));

        expect(missing.length, 'the check must see a gap in the old list').toBeGreaterThan(0);
        // A superset, not an equality: a new AssetType must not turn this control red.
        expect(missing).toEqual(expect.arrayContaining(MISSED_BY_THE_HAND_WRITTEN_LIST));
        expect(strays, 'the old list named only real types').toEqual([]);
    });

    it('positive control: the stray check names a bucket that is not an AssetType', () => {
        // Every other test asserts `strays: []`; this is what proves that half of the check can say no.
        // `CROWDFUND_LOAN` is a plausible post-rename leftover: the enum carried it before it became
        // `CROWDFUND`. Built from the enum itself, so a new AssetType changes nothing here.
        expect(ASSET_TYPES, 'CROWDFUND_LOAN is a real AssetType again: pick another bogus bucket').not.toContain('CROWDFUND_LOAN');
        const {missing, strays} = bucketCoverage([...ASSET_TYPES, 'CROWDFUND_LOAN']);

        expect(strays).toEqual(['CROWDFUND_LOAN']);
        expect(missing).toEqual([]);
    });

    it('buildHypotheticalShockParameters carries every AssetType onto the wire on the weighted-scope path', () => {
        // The call the panel makes for every weighted scope (portfolio, asset set).
        const params = buildHypotheticalShockParameters({dimension: 'asset_class', bucketShocks: uniformAssetClassShocks(-0.2)});
        expect(params).toMatchObject({method: 'hypothetical', dimension: 'asset_class'});

        // Judged after serialisation, because that is what `StressParams` receives.
        const bucketShocks = (JSON.parse(JSON.stringify(params)) as {bucket_shocks: Record<string, number>}).bucket_shocks;
        expect(bucketCoverage(Object.keys(bucketShocks))).toEqual(FULL_COVERAGE);
        for (const assetType of ASSET_TYPES) {
            expect(bucketShocks[assetType], assetType).toBe(-0.2);
        }
    });

    it('STRESS_ASSET_CLASSES offers every AssetType to the bucket editor, and nothing that is not one', () => {
        // With "show all buckets" on, the single-asset editor lists these for the
        // `asset_class` dimension. A type missing here cannot be offered a shock; a
        // stray can, and once edited it goes on the wire and costs the whole analytic.
        expect(bucketCoverage(STRESS_ASSET_CLASSES)).toEqual(FULL_COVERAGE);
    });
});
