/**
 * Barrel Playwright con raccolta di coverage JS.
 *
 * Gli spec importano da qui invece che da '@playwright/test'. Il modulo
 * ri-esporta gli stessi simboli, quindi per gli spec cambia solo il percorso.
 *
 * La raccolta è attiva solo con COVERAGE_JS=1 (impostato da
 * `./dev.py test --coverage js|all`): a flag spento la fixture esce subito e
 * la corsa normale non paga nulla.
 *
 * Nota sull'architettura: qui si chiama solo `mcr.add()`, mai `generate()`.
 * Playwright viene invocato una volta per spec, quindi i dati devono
 * accumularsi nella cache di monocart e il report va prodotto una sola volta
 * a fine corsa — è lo stesso schema con cui il backend accumula i
 * `.coverage.<pid>` e poi li unisce con `coverage combine`.
 */
import {test as testBase, expect} from '@playwright/test';
import type {Browser, BrowserContext, Locator, Page, Request, Response, TestInfo} from '@playwright/test';

const COVERAGE_ON = process.env.COVERAGE_JS === '1';

const test = testBase.extend<{jsCoverage: void}>({
    jsCoverage: [
        async ({context}, use) => {
            if (!COVERAGE_ON) {
                await use();
                return;
            }

            const startOn = async (page: Page) => {
                try {
                    await page.coverage.startJSCoverage({resetOnNavigation: false});
                } catch {
                    // Pagina già chiusa, oppure browser non Chromium: non è un errore
                    // del test, e non deve farlo fallire.
                }
            };

            // Copre sia le pagine già aperte sia quelle create dopo (popup, tab).
            context.on('page', startOn);
            await Promise.all(context.pages().map(startOn));

            await use();

            context.off('page', startOn);

            const collected = await Promise.all(
                context.pages().map(async (page) => {
                    try {
                        return await page.coverage.stopJSCoverage();
                    } catch {
                        return [];
                    }
                }),
            );

            const entries = collected.flat();
            if (entries.length === 0) return;

            try {
                const {default: MCR} = await import('monocart-coverage-reports');
                const {default: coverageOptions} = await import('../../mcr.e2e.config.js');
                await MCR(coverageOptions).add(entries);
            } catch (e) {
                // Il pacchetto potrebbe non essere installato: meglio un avviso
                // che far fallire l'intera suite per un problema di strumentazione.
                console.warn('[coverage-js] raccolta non riuscita:', e);
            }
        },
        {scope: 'test', auto: true},
    ],
});

export {test, expect};
export type {Browser, BrowserContext, Locator, Page, Request, Response, TestInfo};
