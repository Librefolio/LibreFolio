import {sveltekit} from '@sveltejs/kit/vite';
import {defineConfig} from 'vite';
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

export default defineConfig(({mode}) => ({
    plugins: [sveltekit()],
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
