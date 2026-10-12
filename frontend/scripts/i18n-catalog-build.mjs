#!/usr/bin/env node
/**
 * Generate the translation catalogue the app loads, `src/lib/i18n/<lang>.json`, from its sources.
 *
 * The catalogue is built by `scripts/i18n_catalog.py` (see its docstring) from `src/lib/i18n/base/`, the subsystem
 * folders and the plugins' `i18n/`, and is not tracked by git. This wrapper runs it before `dev`, `build` and `check`
 * (npm pre-hooks) and before every Vitest run (`globalSetup` in `vitest.config.ts`); `dev.py` calls the Python script
 * directly. It rewrites only what changed, so a warm run costs one Python start. `PYTHON` picks the interpreter,
 * otherwise `python3`, then `python`.
 */
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const SCRIPT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'scripts', 'i18n_catalog.py');

export default function setup() {
    const interpreters = process.env.PYTHON ? [process.env.PYTHON] : ['python3', 'python'];
    for (const interpreter of interpreters) {
        try {
            execFileSync(interpreter, [SCRIPT, 'build', '--quiet'], {stdio: 'inherit'});
            return;
        } catch (error) {
            // Not installed under this name: try the next one. Any other failure is the build's, already printed.
            if (error.code === 'ENOENT') continue;
            throw new Error(`The translation catalogue could not be generated (${SCRIPT} build exited with ${error.status})`, {cause: error});
        }
    }
    throw new Error(`No Python interpreter found to run ${SCRIPT}: set PYTHON`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
    try {
        setup();
    } catch (error) {
        console.error(error.message);
        process.exit(1);
    }
}
