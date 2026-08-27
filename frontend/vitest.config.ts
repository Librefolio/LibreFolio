import {defineConfig} from 'vitest/config';
import {svelte} from '@sveltejs/vite-plugin-svelte';
import {svelteTesting} from '@testing-library/svelte/vite';
import path from 'path';

export default defineConfig({
    // I due plugin servono solo ai *component test*: senza di loro un `.svelte`
    // importato da un test è un file di testo. Sono innocui per i test puramente
    // TS — trasformano solo i `.svelte` — quindi non serve una seconda config.
    // `svelteTesting` aggiunge la condizione di risoluzione `browser` (Svelte 5
    // in Node risolverebbe la build server, che non produce DOM) e lo smontaggio
    // automatico dei componenti fra un test e l'altro.
    plugins: [svelte(), svelteTesting()],
    test: {
        include: ['src/**/*.test.ts'],
        // L'ambiente resta `node` per i ~190 test esistenti, che non toccano il DOM
        // e in jsdom pagherebbero l'avvio senza guadagnarci nulla. I component test
        // lo chiedono file per file con `// @vitest-environment jsdom` in testa.
        coverage: {
            // Acceso da ./dev.py test --coverage js|all, che esporta COVERAGE_JS=1.
            // I sottoprocessi lo ereditano, quindi non serve toccare le 8
            // invocazioni di vitest sparse nel runner.
            enabled: process.env.COVERAGE_JS === '1',
            include: ['src/**'],
            provider: 'custom',
            customProviderModule: 'vitest-monocart-coverage',
        },
    },
    resolve: {
        alias: {
            $lib: path.resolve(__dirname, 'src/lib'),
            $test: path.resolve(__dirname, 'src/__tests__'),
            '$app/navigation': path.resolve(__dirname, 'src/__mocks__/$app/navigation.ts'),
            '$app/environment': path.resolve(__dirname, 'src/__mocks__/$app/environment.ts'),
        },
    },
});
