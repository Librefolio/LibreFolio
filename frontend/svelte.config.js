import adapter from '@sveltejs/adapter-static';
import {vitePreprocess} from '@sveltejs/vite-plugin-svelte';

console.log('[DEBUG] loaded svelte.config.js', import.meta.url);

/** @type {import('@sveltejs/kit').Config} */
const config = {
    // Consult https://svelte.dev/docs/kit/integrations
    // for more information about preprocessors
    preprocess: vitePreprocess({script: true}),

    kit: {
        // Use static adapter to generate static files that FastAPI can serve
        adapter: adapter({
            pages: 'build',
            assets: 'build',
            fallback: '200.html', // SPA fallback for dynamic routes
            precompress: false,
            strict: false, // Allow pages that cannot be prerendered
        }),
        alias: {
            // Test-only harness (see src/__tests__/component.ts). Declared here
            // rather than in tsconfig because SvelteKit regenerates
            // .svelte-kit/tsconfig.json from this map: adding it by hand there
            // would be overwritten on the next sync, and svelte-check would go
            // back to reporting "cannot find module '$test/component'".
            $test: 'src/__tests__',
        },
        paths: {
            // Empty base means use relative paths from current URL
            base: '',
        },
    },
};

export default config;
