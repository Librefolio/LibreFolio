/**
 * Monocart coverage — configurazione degli E2E (Playwright).
 *
 * Importata esplicitamente dalla fixture in `e2e/fixtures/playwright.ts`.
 * Non viene caricata automaticamente: l'auto-caricamento di monocart cerca
 * `mcr.config.js`, che è la configurazione degli unit.
 */
import {sharedFilters} from './mcr.shared.js';

export default {
    name: 'LibreFolio — E2E Coverage (Playwright)',
    outputDir: 'coverage-js/e2e',

    reports: ['raw'],
    lcov: false,

    // La fixture gira una volta per test e Playwright viene invocato una volta
    // per spec: i dati devono accumularsi, non sostituirsi.
    cleanCache: false,

    ...sharedFilters,
};
