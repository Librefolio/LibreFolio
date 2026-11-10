/**
 * Z-37: neutralize what breaks a template literal in the descriptions of the exported OpenAPI document.
 *
 * `openapi-zod-client --with-description` writes the description of a model that a required field refers to between
 * backticks (`Inner.describe(\`…\`)`). A backtick in a docstring ends that literal and `${` starts an expression, so
 * `generated.ts` stops being TypeScript and `api sync` fails. Run before the generator (`npm run generate-api`),
 * on `src/lib/api/openapi.json`, which is generated and ignored by git.
 *
 * The backtick becomes an apostrophe, `${` becomes `$ {`: the text stays readable. Only the string values of the keys
 * named `description` are changed; a property that is itself called `description` is a schema, not a text.
 */
import {readFile, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

/** @param {string} text */
export function neutralizeDescription(text) {
    return text.replaceAll('`', "'").replaceAll('${', '$ {');
}

/**
 * Rewrites `document` in place; returns how many descriptions changed.
 * @param {unknown} document
 * @returns {number}
 */
export function neutralizeOpenApiDescriptions(document) {
    let changed = 0;
    /** @param {any} node */
    const visit = (node) => {
        if (Array.isArray(node)) {
            node.forEach(visit);
            return;
        }
        if (node === null || typeof node !== 'object') return;
        for (const [key, value] of Object.entries(node)) {
            if (key === 'description' && typeof value === 'string') {
                const clean = neutralizeDescription(value);
                if (clean !== value) {
                    node[key] = clean;
                    changed += 1;
                }
            } else {
                visit(value);
            }
        }
    };
    visit(document);
    return changed;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
    const file = process.argv[2] ?? fileURLToPath(new URL('../src/lib/api/openapi.json', import.meta.url));
    const document = JSON.parse(await readFile(file, 'utf8'));
    const changed = neutralizeOpenApiDescriptions(document);
    await writeFile(file, JSON.stringify(document, null, 2));
    console.log(`openapi descriptions: ${changed} neutralized in ${file}`);
}
