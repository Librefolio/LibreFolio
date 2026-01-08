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
			fallback: 'index.html',  // SPA fallback for client-side routing
			precompress: false,
			strict: true
		})
	}
};

export default config;
