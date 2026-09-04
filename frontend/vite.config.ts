import {sveltekit} from '@sveltejs/kit/vite';
import {defineConfig, createLogger} from 'vite';
import {execSync} from 'child_process';
import istanbul from 'vite-plugin-istanbul';

/**
 * Get git version from git describe.
 * Returns format like 'v1.2.3' or 'v1.2.3-5-gabcdef-dirty'.
 */
function getGitVersion(): string {
    try {
        return execSync('git describe --tags --always --dirty').toString().trim();
    } catch {
        return 'unknown';
    }
}

/**
 * Custom logger that suppresses Rollup @__PURE__ annotation warnings.
 *
 * These warnings fire when Rollup injects @__PURE__ annotations (for tree-shaking)
 * at positions that don't align with sourcemaps after TypeScript type erasure.
 * Rollup handles this automatically ("The comment will be removed to avoid issues")
 * so the warnings are purely noise. They cannot be silenced via rollupOptions.onwarn
 * because SvelteKit runs multiple Rollup environments (client + SSR).
 */
const suppressedWarnPatterns = ['annotation that Rollup cannot interpret', "Can't resolve original location of error"];

const logger = createLogger();
const origWarn = logger.warn.bind(logger);
logger.warn = (msg, opts) => {
    if (suppressedWarnPatterns.some((p) => msg.includes(p))) return;
    origWarn(msg, opts);
};

/**
 * Instrument the source for coverage when `COVERAGE_INSTRUMENT=1`.
 *
 * Why this exists, given that we already measure coverage: the V8 route we used
 * before reports *nothing* for a Svelte template's branches. Measured on a
 * component holding a single `{#if}` exercised from both sides, the branch map
 * came back empty — so every `{#if}`, `{:else}` and `{#each}` in the app was
 * invisible to the numbers, and only `<script>` blocks were ever counted.
 * Istanbul instruments the source before the compiler rewrites it, so those
 * branches survive.
 *
 * The second gain is subtler and matters more. Unit tests and E2E used to
 * measure two *different compilations* of the same file — vitest's for jsdom,
 * the production build for Playwright — and their statement positions did not
 * line up, so merging them inflated the denominator with the same code counted
 * twice. One shared instrumentation removes that by construction.
 *
 * Off by default: instrumented code is slower and must never ship. The E2E
 * coverage run turns it on, the production build never sees it.
 *
 * `forceBuildInstrument` and `checkProd` are not optional here, and their
 * absence fails *silently*. The plugin's own `apply()` returns
 * `env.command === 'serve'` unless forced, so during `vite build` it is not
 * merely inert — it is never installed, and `configResolved` would disable it a
 * second time because a production build sets `isProduction`. The result is a
 * run that announces "building instrumented", builds a perfectly ordinary
 * bundle, and then reports zero coverage without failing: a green that measures
 * nothing. The guard against that is `.coverage-instrumented`, written only
 * after a build that really carried the flag, plus the fixture's warning when
 * `window.__coverage__` turns out to be absent.
 */
const coverageInstrumentation =
    process.env.COVERAGE_INSTRUMENT === '1'
        ? [
              istanbul({
                  include: 'src/**/*',
                  extension: ['.js', '.ts', '.svelte'],
                  requireEnv: false,
                  forceBuildInstrument: true,
                  checkProd: false,
              }),
          ]
        : [];

export default defineConfig(({mode}) => ({
    plugins: [sveltekit(), ...coverageInstrumentation],
    customLogger: logger,
    // Inject version at build time
    define: {
        __APP_VERSION__: JSON.stringify(getGitVersion()),
    },
    build: {
        // Debug mode: sourcemaps + no minify for easy debugging
        // Instrumented builds keep their sourcemaps: without them the coverage
        // cannot be mapped back to the sources anyone reads.
        sourcemap: mode === 'development' || process.env.COVERAGE_INSTRUMENT === '1',
        minify: mode === 'development' ? false : 'esbuild',
        rollupOptions: {
            output: {
                manualChunks: (id) => {
                    // Split large dependencies into separate chunks
                    if (id.includes('node_modules')) {
                        // zxcvbn-ts (password strength) - very large (~1.7MB)
                        // Split into separate chunks for lazy loading
                        if (id.includes('@zxcvbn-ts/language-common')) {
                            return 'vendor-zxcvbn-dict-common';
                        }
                        if (id.includes('@zxcvbn-ts/language-en')) {
                            return 'vendor-zxcvbn-dict-en';
                        }
                        if (id.includes('@zxcvbn-ts/core')) {
                            return 'vendor-zxcvbn-core';
                        }
                        // Lucide icons
                        if (id.includes('lucide')) {
                            return 'vendor-icons';
                        }
                        // Date/time libraries
                        if (id.includes('date-fns') || id.includes('dayjs') || id.includes('moment')) {
                            return 'vendor-date';
                        }
                    }
                },
            },
        },
        // zxcvbn dictionaries are ~1.7MB - this is expected for password strength
        // The library uses frequency lists for common passwords/words
        chunkSizeWarningLimit: 2000,
    },
}));
