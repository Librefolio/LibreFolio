import {sveltekit} from '@sveltejs/kit/vite';
import {defineConfig} from 'vite';

export default defineConfig({
    plugins: [sveltekit()],
    build: {
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
});
