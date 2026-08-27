/**
 * Filtri condivisi fra la coverage unit e quella E2E.
 *
 * Tenerli in un solo posto è ciò che rende confrontabili i due report e
 * sensato il loro merge: se i due livelli filtrassero in modo diverso, le
 * percentuali del report combinato non vorrebbero dire niente.
 */
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const FRONTEND_DIR = path.dirname(fileURLToPath(import.meta.url));
const SRC_DIR = path.join(FRONTEND_DIR, 'src');
const BUILD_DIR = path.join(FRONTEND_DIR, 'build');

/** Estensioni dei sorgenti che ci interessano. */
const SOURCE_RE = /\.(svelte|ts|js)$/;
const TEST_RE = /\.(test|spec)\.[tj]s$/;

/**
 * Sorgenti nostri per posizione, ma non nostri per scrittura.
 *
 * `api/generated.ts` è prodotto da `openapi-zod-client` a partire dallo schema
 * OpenAPI: 17k righe di validatori Zod che l'app attraversa a ogni chiamata e
 * che risultano quindi coperte al 100%. Contarle significa aggiungere 478
 * statement sempre verdi al denominatore, cioè spostare in su la percentuale
 * complessiva senza che nessuno abbia testato niente — e la percentuale serve
 * proprio a decidere dove scrivere i prossimi test.
 *
 * Non è codice da testare: se sbaglia, sbaglia il generatore, e il posto dove
 * accorgersene è `./dev.py api sync`, non la suite.
 */
const GENERATED_SOURCES = new Set(['src/lib/api/generated.ts']);

/**
 * Elenco dei file che esistono davvero in `frontend/src`.
 *
 * È questo l'unico criterio affidabile per distinguere il nostro codice da
 * quello di terzi. Le sourcemap dei pacchetti npm conservano i percorsi
 * *interni al pacchetto*, non quelli di installazione: il runtime di Svelte,
 * per dire, si presenta come `src/internal/client/dom/blocks/each.js` e quello
 * di SvelteKit come `src/runtime/client/...`. Filtrare per prefisso vorrebbe
 * dire rincorrere una lista di eccezioni libreria per libreria; chiedere
 * invece che il file sia sul nostro disco chiude la questione una volta sola.
 */
const ourSources = new Set();
(function collect(dir) {
    let entries;
    try {
        entries = fs.readdirSync(dir, {withFileTypes: true});
    } catch {
        return;
    }
    for (const e of entries) {
        const full = path.join(dir, e.name);
        if (e.isDirectory()) {
            if (e.name === '__mocks__' || e.name === '__tests__') continue;
            collect(full);
        } else if (SOURCE_RE.test(e.name) && !TEST_RE.test(e.name)) {
            ourSources.add(path.relative(FRONTEND_DIR, full).split(path.sep).join('/'));
        }
    }
})(SRC_DIR);

/** Tiene solo i sorgenti che appartengono a LibreFolio. */
function sourceFilter(sourcePath) {
    const p = sourcePath.replace(/\\/g, '/');
    if (GENERATED_SOURCES.has(p)) return false;
    return ourSources.has(p);
}

/**
 * Scarta i bundle che non possono contenere nostro codice.
 *
 * Oltre alle dipendenze, esclude i documenti HTML serviti dal server di test:
 * i loro script inline sono il bootstrap generato da SvelteKit, non hanno
 * sourcemap, e finirebbero nel report come un file di nome `localhost-6041`.
 * Il controllo vale solo per gli URL http(s): la coverage unit arriva con
 * percorsi `file://` che puntano direttamente ai sorgenti.
 */
function entryFilter(entry) {
    const url = entry.url || '';
    if (url.includes('/node_modules/')) return false;
    if (/^https?:/.test(url) && !SOURCE_RE.test(url.split(/[?#]/)[0])) return false;
    return true;
}

/** Normalizza i percorsi così che unit ed E2E indichino lo stesso file. */
function sourcePath(filePath) {
    return filePath.replace(/\\/g, '/').replace(/^.*?(src\/)/, '$1');
}

/**
 * Risolve le sourcemap dei bundle serviti dal server di test.
 *
 * SvelteKit emette sourcemap **esterne** (`chunk.js.map`), non incorporate:
 * nel bundle resta solo il commento `sourceMappingURL`. Senza questo resolver
 * monocart si ferma al livello del bundle e il report elenca i chunk
 * `_app/immutable/...` invece dei nostri `.svelte` e `.ts` — cioè esattamente
 * l'informazione che non serve a nessuno.
 *
 * Le mappe si leggono da disco anziché via HTTP di proposito: la risoluzione
 * avviene alla generazione del report, quando il server di test è già stato
 * spento da Playwright.
 */
async function sourceMapResolver(url, defaultResolver) {
    const appPath = url.match(/\/(_app\/.+?\.map)(?:[?#].*)?$/);
    if (appPath) {
        try {
            return await fsp.readFile(path.join(BUILD_DIR, appPath[1]), 'utf-8');
        } catch {
            // Bundle non più sul disco (rebuild nel frattempo): si prova la via normale.
        }
    }
    return defaultResolver(url);
}

export const sharedFilters = {entryFilter, sourceFilter, sourcePath, sourceMapResolver};
