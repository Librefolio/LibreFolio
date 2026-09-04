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
            // Per estensione, non `src/**`: quel glob prendeva anche i file che
            // non sono codice — l'istanbul provider ha provato a strumentare un
            // `.DS_Store` e la corsa è morta con un SyntaxError su dati binari.
            include: ['src/**/*.{js,ts,svelte}'],
            exclude: ['src/**/*.test.ts', 'src/**/__tests__/**', 'src/**/__mocks__/**', 'src/app.d.ts'],
            // `istanbul` invece del provider V8, e la ragione è misurabile: su un
            // componente con un solo `{#if}` esercitato da entrambi i lati, V8
            // riporta un branch map **vuoto** mentre istanbul riporta i due rami.
            // Il compilatore Svelte trasforma il markup condizionale in closure che
            // V8 non riconosce come decisioni, quindi ogni `{#if}` dell'app era
            // fuori dal conto e solo i blocchi `<script>` venivano misurati.
            //
            // Vale anche per il denominatore condiviso con gli E2E: quelli girano su
            // un build strumentato dallo stesso istanbul (`COVERAGE_INSTRUMENT=1` in
            // vite.config.ts), quindi le due misure ora parlano delle stesse
            // posizioni invece di due compilazioni diverse dello stesso file.
            provider: 'istanbul',
            // Il formato di scambio con il livello E2E. Ogni invocazione di
            // vitest scrive in una cartella propria perché il runner lo lancia
            // otto volte, una per categoria: con una cartella condivisa
            // l'ultima corsa cancellerebbe le precedenti. `frontend/scripts/
            // unit-report.js` le riunisce poi in un report solo.
            reporter: ['json'],
            reportsDirectory: `coverage-js/unit/${Date.now().toString(36)}-${process.pid}`,
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
