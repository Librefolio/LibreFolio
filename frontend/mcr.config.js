/**
 * Monocart coverage — configurazione dei test unit (vitest).
 *
 * Caricata automaticamente da `vitest-monocart-coverage`.
 * La variante E2E vive in `mcr.e2e.config.js` e riusa gli stessi filtri.
 */
import {sharedFilters} from './mcr.shared.js';

/**
 * Ogni invocazione scrive in una cartella propria.
 *
 * Serve perché `vitest-monocart-coverage` chiama `generate()` al termine di
 * *ogni* processo vitest, e il runner lancia vitest 8 volte (una per categoria):
 * con una cartella condivisa l'ultima corsa cancellerebbe le precedenti.
 * Il report unico si ottiene poi con `mcr merge` su tutte queste cartelle.
 */
const runTag = `${Date.now().toString(36)}-${process.pid}`;

export default {
    name: 'LibreFolio — Unit Coverage (vitest)',
    outputDir: `coverage-js/unit/${runTag}`,

    // `raw` è il formato di scambio: è ciò che `mcr merge` legge per unire
    // unit ed E2E in un report unico (stesso ruolo dei .coverage.* del backend).
    reports: ['raw'],
    lcov: false,

    ...sharedFilters,
};
