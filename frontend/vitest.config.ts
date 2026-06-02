import {defineConfig} from 'vitest/config';
import path from 'path';

export default defineConfig({
    test: {
        include: ['src/**/*.test.ts'],
    },
    resolve: {
        alias: {
            '$lib': path.resolve(__dirname, 'src/lib'),
            '$app/navigation': path.resolve(__dirname, 'src/__mocks__/$app/navigation.ts'),
            '$app/environment': path.resolve(__dirname, 'src/__mocks__/$app/environment.ts'),
        },
    },
});

