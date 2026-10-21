/**
 * The changelog files bundled with the build (F12, lot CL): the repository's English CHANGELOG.md, which Vite's `?raw`
 * import inlines into the bundle, and one lazy chunk per translation `CHANGELOG.<xx>.md`. `changelog.ts` parses and
 * merges them.
 *
 * They live apart so that a jsdom test can replace them (A-CL1): there Vite refuses a `?raw` import from outside
 * `frontend/`, mocked or not, and with it every module that holds one. Mocking this module lets a test load the real
 * `changelog.ts`.
 */
import changelogRaw from '../../../../../CHANGELOG.md?raw';

/** The English CHANGELOG.md, as written. */
export const englishChangelog: string = changelogRaw;

/** The translations beside it, `CHANGELOG.<xx>.md`: one lazy loader per file, keyed by its path. */
export const translationModules = import.meta.glob<string>('../../../../../CHANGELOG.[a-z][a-z].md', {query: '?raw', import: 'default'});
