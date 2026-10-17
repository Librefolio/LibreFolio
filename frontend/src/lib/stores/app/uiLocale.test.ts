/**
 * uiLocale — the locale every number is written in (M-18 CP1, CP2).
 *
 * The rule, the developer's (2026-10-12): numbers follow the language of the UI, not the machine. The
 * browser only chooses the region, and only when it speaks the same language:
 *
 *   - UI language L, browser primary tag B (`navigator.language`): when B's language is L and B names a
 *     region, B itself, canonical — `it-CH` writes `4788.01`, `fr-CA` has dates of its own, and a numeric
 *     region is a region too: `es-419`, Latin America;
 *   - otherwise L's default: `en-GB` for English, the bare language for the others. That includes a B in
 *     L that names no region (CP2, "English without a region falls back to en-GB"): a bare `en`, or an
 *     `en-Latn` with only a script, has no region to lend — and kept as it is, a bare `en` is written by
 *     Intl as American, `10/12/2026` and `2:05 PM`;
 *   - only the primary tag counts. Chrome lists `en-US` second on almost every install, so scanning the
 *     list would send an Italian reading the English UI to American conventions; equally, an English
 *     browser does not lend the `it-CH` it lists second to the Italian UI.
 *
 * Three faces, each pinned here: `resolveUiLocale` (pure), `uiLocaleStore` (a readable for legacy
 * templates, `$uiLocaleStore`) and `uiLocale()` (the same value as a getter, the default locale of every
 * number formatter).
 *
 * The browser. Node's `navigator.language` follows the host's ICU locale — `LANG=it_CH.UTF-8` gives
 * `it-CH`, an empty `LANG` gives `und` — so every test installs the tag it means with `vi.stubGlobal` and
 * takes a freshly imported graph: `vi.resetModules()`, then `import()` of this module, the language store
 * it derives from and the Svelte runtime the test reads it through, all from one registry. Whether the
 * module reads the tag at import, on subscription or on every change is its own business: all three see
 * the tag of the test.
 *
 * The reactive face. A getter that answers correctly when polled can still be invisible to a runes
 * template: `get(store)` returns the right value and re-runs nothing, so every formatter defaulting to it
 * would keep the language of the first render. `toStore` runs its getter inside a render effect, so a
 * consumer built on `uiLocale()` sees a language change only if `uiLocale()` is tracked. Measured in this
 * environment before writing the test: `toStore(() => get(s))` stays on its first value,
 * `toStore(() => fromStore(s).current)` follows.
 *
 * Language. `currentLanguage.set`, as LanguageSelector does. Each graph starts from the app's default,
 * English, and is put back to English after its test.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

type UiLocaleModule = typeof import('./uiLocale');
type CurrentLanguage = (typeof import('./language'))['currentLanguage'];

interface Graph {
    ui: UiLocaleModule;
    currentLanguage: CurrentLanguage;
    store: typeof import('svelte/store');
    flushSync: (typeof import('svelte'))['flushSync'];
}

/** Language stores of the graphs booted by the running test, put back to English after it. */
const booted: CurrentLanguage[] = [];

/**
 * A fresh graph under a browser whose primary tag is `language` and whose list is `languages`.
 * `language: null` is a runtime with no `navigator` at all, as on the server.
 */
async function boot(language: string | null = 'en-US', languages: readonly string[] = language ? [language] : []): Promise<Graph> {
    vi.stubGlobal('navigator', language === null ? undefined : {language, languages: [...languages]});
    vi.resetModules();
    const ui = await import('./uiLocale');
    const {currentLanguage} = await import('./language');
    const store = await import('svelte/store');
    const {flushSync} = await import('svelte');
    booted.push(currentLanguage);
    return {ui, currentLanguage, store, flushSync};
}

/** The store's value and the getter's, read together: the two faces must never disagree. */
function bothFaces({ui, store}: Graph): {store: string; getter: string} {
    return {store: store.get(ui.uiLocaleStore), getter: ui.uiLocale()};
}

const as = (locale: string) => ({store: locale, getter: locale});

afterEach(() => {
    for (const currentLanguage of booted.splice(0)) currentLanguage.set('en');
    vi.unstubAllGlobals();
});

describe('resolveUiLocale — the UI language, with the browser’s region only when the two agree', () => {
    it.each([
        // The browser speaks the UI language and names a region: its own tag, region included.
        ['en', 'en-US', 'en-US'],
        ['en', 'en-GB', 'en-GB'],
        ['it', 'it-CH', 'it-CH'],
        ['fr', 'fr-CA', 'fr-CA'],
        ['es', 'es-MX', 'es-MX'],
        // …a numeric region is a region: es-419, Latin America (UN M.49), is kept just as es-MX is.
        ['es', 'es-419', 'es-419'],
        // …compared without regard to case, and returned canonical.
        ['IT', 'it-ch', 'it-CH'],
        // The browser speaks the UI language but names no region: nothing to lend, the UI language's default.
        // English is where it shows: a bare en kept as it is would be written American (10/12/2026, 2:05 PM).
        ['en', 'en', 'en-GB'],
        // …and a script is not a region.
        ['en', 'en-Latn', 'en-GB'],
        // …for the others the default is the bare language, the very tag the browser gave.
        ['it', 'it', 'it'],
        ['fr', 'fr', 'fr'],
        // Another language: the UI language's default — en-GB for English, the bare language otherwise.
        ['en', 'it-IT', 'en-GB'],
        ['it', 'en-US', 'it'],
        ['fr', 'en-US', 'fr'],
        ['es', 'it-IT', 'es'],
        // No tag at all.
        ['en', undefined, 'en-GB'],
        ['en', null, 'en-GB'],
        ['it', undefined, 'it'],
        // A tag that is not BCP 47: the default, never a throw.
        ['en', '', 'en-GB'],
        ['fr', 'not a tag!', 'fr'],
    ] as const)('(%s, %s) → %s', async (language, browserTag, expected) => {
        const {ui} = await boot();

        const resolved = ui.resolveUiLocale(language, browserTag);

        expect(resolved).toBe(expected);
        // Whatever it answers, Intl takes it as it is: a canonical tag, ready for Intl.NumberFormat.
        expect(Intl.getCanonicalLocales(resolved)).toEqual([resolved]);
    });
});

describe('uiLocaleStore and uiLocale() — the UI language as a locale, following every change', () => {
    it('English UI on an en-US browser, the test default: en-US through both faces', async () => {
        const graph = await boot('en-US');

        expect(graph.store.get(graph.currentLanguage), 'control: the UI starts in English').toBe('en');
        expect(bothFaces(graph)).toEqual(as('en-US'));
    });

    it.each([
        ['fr', 'fr'],
        ['it', 'it'],
        ['es', 'es'],
    ] as const)('UI switched to %s on an en-US browser: the bare language, %s', async (language, expected) => {
        const graph = await boot('en-US');

        graph.currentLanguage.set(language);

        expect(bothFaces(graph)).toEqual(as(expected));
    });

    it('a subscriber of the store hears every change, in order, and English again at the end', async () => {
        const {ui, currentLanguage} = await boot('en-US');
        const heard: string[] = [];
        const stop = ui.uiLocaleStore.subscribe((value: string) => void heard.push(value));
        try {
            currentLanguage.set('fr');
            currentLanguage.set('it');
            currentLanguage.set('en');
        } finally {
            stop();
        }

        expect(heard).toEqual(['en-US', 'fr', 'it', 'en-US']);
    });

    it('uiLocale() is tracked by an effect: a consumer reading it follows the language instead of keeping the first one', async () => {
        const {ui, currentLanguage, store, flushSync} = await boot('en-US');
        const seen: string[] = [];
        const stop = store.toStore(() => ui.uiLocale()).subscribe((value: string) => void seen.push(value));
        try {
            currentLanguage.set('fr');
            flushSync();
            currentLanguage.set('en');
            flushSync();
        } finally {
            stop();
        }

        expect(seen, 'a getter read once, like get(store), keeps ["en-US"]: no runes template would follow the language').toEqual(['en-US', 'fr', 'en-US']);
    });
});

describe('uiLocaleStore and uiLocale() — the browser’s own tag', () => {
    it('a Canadian French browser regionalises the French UI only: fr-CA, then en-GB for English, it for Italian', async () => {
        const graph = await boot('fr-CA', ['fr-CA', 'en-US']);

        graph.currentLanguage.set('fr');
        expect(bothFaces(graph), 'French UI').toEqual(as('fr-CA'));

        graph.currentLanguage.set('en');
        expect(bothFaces(graph), 'English UI').toEqual(as('en-GB'));

        graph.currentLanguage.set('it');
        expect(bothFaces(graph), 'Italian UI').toEqual(as('it'));
    });

    it('a Swiss Italian browser keeps its region for the Italian UI: it-CH', async () => {
        const graph = await boot('it-CH', ['it-CH']);

        graph.currentLanguage.set('it');

        expect(bothFaces(graph)).toEqual(as('it-CH'));
    });

    it('English UI on a bare en browser, which names no region: en-GB through both faces', async () => {
        const graph = await boot('en');

        expect(graph.store.get(graph.currentLanguage), 'control: the UI starts in English').toBe('en');
        expect(bothFaces(graph), 'kept as it is, a bare en is written American by Intl: 10/12/2026, 2:05 PM').toEqual(as('en-GB'));
    });

    it('only the primary tag counts: an en-US browser listing it-CH second leaves the Italian UI on it', async () => {
        const graph = await boot('en-US', ['en-US', 'it-CH']);

        graph.currentLanguage.set('it');

        expect(bothFaces(graph)).toEqual(as('it'));
    });

    it('without a navigator, as on the server: the UI language’s default, and no throw', async () => {
        const graph = await boot(null);

        expect(bothFaces(graph), 'English UI').toEqual(as('en-GB'));
        graph.currentLanguage.set('fr');
        expect(bothFaces(graph), 'French UI').toEqual(as('fr'));
    });
});

/**
 * uiLocaleRule — the rule on its own, for the E2E spec that imports it directly (Y-31).
 *
 * `resolveUiLocale` lives in `./uiLocaleRule`, a module that imports nothing, and `./uiLocale` re-exports it. The reason
 * is outside this file: brokers-detail.spec.ts computes the locale the lots panel writes a day in with the app's own
 * rule (`dayAsThePanelWritesIt`), importing the module directly, and Playwright resolves neither `$app` nor `$lib` — the
 * aliases `./uiLocale` reaches through `./language`. One import would break that spec at load, before any of its tests,
 * and nothing here would notice: Vite resolves those aliases for Vitest.
 *
 * So the first test reads the module's source and lists everything it would load: an `import` of any kind, type-only
 * included; an `export … from`; an `import … = require()`; an `import()` call or an `import('…')` type; a `require()`.
 * The source is parsed by TypeScript, not matched by a pattern, so a comment or a string that names an import is not
 * one. Its positive control is the same scan run on `./uiLocale`, which must find the import of `./language` — the one
 * that keeps `./uiLocale` out of Playwright's reach.
 *
 * The second pins the move as a move: `./uiLocale` exports the very same function object, so every test above, which
 * reaches the rule through `./uiLocale`, still tests the rule the spec imports.
 *
 * Both import `./uiLocaleRule` dynamically: while the module is missing they fail on their own, and the file still
 * collects.
 */
describe('uiLocaleRule — the rule alone, which an E2E spec imports directly (Y-31)', () => {
    interface ModuleReference {
        kind: string;
        specifier: string;
    }

    /** Everything the module `file`, a sibling of this test, would load, in source order; and whether it parsed. */
    async function moduleReferences(file: string): Promise<{references: ModuleReference[]; parseErrors: string[]}> {
        const {readFileSync} = await import('node:fs');
        const ts = (await import('typescript')).default;
        const sf = ts.createSourceFile(file, readFileSync(new URL(file, import.meta.url), 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
        const named = (node: import('typescript').Node | undefined): string => (node === undefined ? '<none>' : ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node) ? node.text : `<${node.getText(sf)}>`);
        const references: ModuleReference[] = [];
        const visit = (node: import('typescript').Node): void => {
            if (ts.isImportDeclaration(node)) references.push({kind: 'import', specifier: named(node.moduleSpecifier)});
            else if (ts.isExportDeclaration(node) && node.moduleSpecifier) references.push({kind: 'export … from', specifier: named(node.moduleSpecifier)});
            else if (ts.isImportEqualsDeclaration(node) && ts.isExternalModuleReference(node.moduleReference)) references.push({kind: 'import = require()', specifier: named(node.moduleReference.expression)});
            else if (ts.isImportTypeNode(node)) references.push({kind: "import('…') type", specifier: ts.isLiteralTypeNode(node.argument) ? named(node.argument.literal) : named(node.argument)});
            else if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) references.push({kind: 'import()', specifier: named(node.arguments[0])});
            else if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === 'require') references.push({kind: 'require()', specifier: named(node.arguments[0])});
            ts.forEachChild(node, visit);
        };
        visit(sf);
        // Parsed with errors, the tree may stop short of a reference: the scan would not have read the whole module.
        const diagnostics = (sf as unknown as {parseDiagnostics?: readonly import('typescript').Diagnostic[]}).parseDiagnostics ?? [];
        return {references, parseErrors: diagnostics.map((diagnostic) => ts.flattenDiagnosticMessageText(diagnostic.messageText, ' '))};
    }

    it('./uiLocaleRule imports nothing — no import, no export … from, no import(), no require() — so Playwright loads it as it is', async () => {
        const rule = await import('./uiLocaleRule');
        expect(typeof rule.resolveUiLocale, 'barrier: the module exists and exports the rule').toBe('function');

        const control = await moduleReferences('./uiLocale.ts');
        expect(control.parseErrors, 'positive control: ./uiLocale parses').toEqual([]);
        expect(control.references, 'positive control: the scan finds the import of ./language, which keeps ./uiLocale out of Playwright’s reach').toContainEqual({kind: 'import', specifier: './language'});

        const scanned = await moduleReferences('./uiLocaleRule.ts');
        expect(scanned.parseErrors, './uiLocaleRule parses: the scan read all of it').toEqual([]);
        expect(scanned.references, 'what ./uiLocaleRule would load, for an E2E spec that resolves neither $app nor $lib: nothing').toEqual([]);
    });

    it('./uiLocale re-exports the very function ./uiLocaleRule declares: the tests above test the rule the spec imports', async () => {
        const {ui} = await boot();
        const rule = await import('./uiLocaleRule');

        expect(typeof rule.resolveUiLocale, 'control: the rule module exports resolveUiLocale').toBe('function');
        expect(ui.resolveUiLocale, 'one function object, re-exported — not a copy that could drift').toBe(rule.resolveUiLocale);
    });
});
