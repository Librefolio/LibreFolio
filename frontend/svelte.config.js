import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// Use static adapter to generate static files that FastAPI can serve
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: undefined,  // Disable fallback generation - FastAPI handles SPA routing
			precompress: false,
			strict: false  // Allow pages that cannot be prerendered
		})
	}
};

export default config;
