// Enable prerendering for static build
// This allows FastAPI to serve the SPA as static files

export const prerender = true;
export const ssr = false;  // Disable SSR since FastAPI serves static files

