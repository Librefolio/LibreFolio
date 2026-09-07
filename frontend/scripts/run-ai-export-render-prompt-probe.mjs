#!/usr/bin/env node

import {createInterface} from 'node:readline';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

import {createServer} from 'vite';

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
process.env.LIBREFOLIO_FRONTEND_ROOT = frontendRoot;

const svelteKitRuntimeStubs = {
    name: 'librefolio-ai-export-probe-sveltekit-runtime',
    resolveId(id) {
        if (id === '$app/environment' || id === '$app/navigation') return `\0${id}`;
    },
    load(id) {
        if (id === '\0$app/environment') return "export const browser = false; export const building = false; export const dev = false; export const version = 'probe';";
        if (id === '\0$app/navigation') return 'export async function goto() {}';
    },
};

const vite = await createServer({
    root: frontendRoot,
    configFile: false,
    appType: 'custom',
    logLevel: 'silent',
    plugins: [svelteKitRuntimeStubs],
    server: {middlewareMode: true},
    resolve: {
        alias: {
            $lib: resolve(frontendRoot, 'src', 'lib'),
        },
    },
});

const module = await vite.ssrLoadModule('/scripts/ai-export-render-prompt-probe.ts');
const input = createInterface({
    input: process.stdin,
    crlfDelay: Infinity,
});

try {
    for await (const line of input) {
        if (line.trim().length === 0) continue;
        let requestId = 'unknown';
        try {
            const message = JSON.parse(line);
            if (typeof message?.request_id === 'string') requestId = message.request_id;
            const result = await module.handleProbeMessage(message);
            process.stdout.write(`${JSON.stringify(result)}\n`);
        } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            process.stdout.write(`${JSON.stringify({request_id: requestId, ok: false, error: {name: error instanceof Error ? error.name : 'Error', message}})}\n`);
        }
    }
} finally {
    await vite.close();
}
