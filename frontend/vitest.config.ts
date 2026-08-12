import {defineConfig} from 'vitest/config';
import path from 'path';

export default defineConfig({
    test: {
        include: ['src/**/*.test.ts'],
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
            '$lib': path.resolve(__dirname, 'src/lib'),
            '$app/navigation': path.resolve(__dirname, 'src/__mocks__/$app/navigation.ts'),
            '$app/environment': path.resolve(__dirname, 'src/__mocks__/$app/environment.ts'),
        },
    },
});

