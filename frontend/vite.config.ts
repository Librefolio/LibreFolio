import {sveltekit} from '@sveltejs/kit/vite';
import {defineConfig, createLogger} from 'vite';
import {execSync} from 'child_process';

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
const suppressedWarnPatterns = [
    'annotation that Rollup cannot interpret',
    "Can't resolve original location of error",
];

const logger = createLogger();
const origWarn = logger.warn.bind(logger);
logger.warn = (msg, opts) => {
    if (suppressedWarnPatterns.some((p) => msg.includes(p))) return;
    origWarn(msg, opts);
};

export default defineConfig(({mode}) => ({
    plugins: [sveltekit()],
    customLogger: logger,
    // Inject version at build time
    define: {
        __APP_VERSION__: JSON.stringify(getGitVersion()),
    },
    build: {
        // Debug mode: sourcemaps + no minify for easy debugging
        sourcemap: mode === 'development' ? true : false,
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
                }
            }
        },
        // zxcvbn dictionaries are ~1.7MB - this is expected for password strength
        // The library uses frequency lists for common passwords/words
        chunkSizeWarningLimit: 2000
    }
}));
