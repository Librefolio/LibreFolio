/**
 * Turns the coverage that the Playwright fixture accumulated into a report.
 *
 * During an E2E run the fixture only calls `mcr.add()`, never `generate()`:
 * Playwright is launched once per spec, so each process contributes to a shared
 * monocart cache and the report has to be produced once, at the end — the same
 * shape as the backend's `.coverage.<pid>` files followed by `coverage combine`.
 *
 * There is no CLI equivalent for this step (`mcr merge` reads raw files, not the
 * cache), hence this helper. Invoked by `_finalize_js_coverage()`.
 */
import MCR from 'monocart-coverage-reports';
import coverageOptions from '../mcr.e2e.config.js';

const reports = (process.argv[2] || 'v8,raw,console-summary').split(',');

const mcr = MCR({...coverageOptions, reports});
const results = await mcr.generate();

if (!results) {
    console.error('[mcr-generate] no coverage data found in the cache');
    process.exit(1);
}
