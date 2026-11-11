/**
 * Where the BRIM sample reports are (U-B4): each import plugin keeps its own in
 * `backend/app/services/brim_providers/<plugin>/sample_reports/`. The twin of
 * `backend/test_scripts/brim_samples.py`: a file name in, the path of that file out.
 */
import {existsSync, readdirSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const PROVIDERS_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../backend/app/services/brim_providers');
/** What belongs to no plugin: the README and the `malformed/` fixtures. */
const SHARED_DIR = path.join(PROVIDERS_DIR, 'sample_reports');

/** The path of the sample report called `name`, in the folder of the plugin that owns it. */
export function samplePath(name: string): string {
    for (const plugin of readdirSync(PROVIDERS_DIR, {withFileTypes: true})) {
        if (!plugin.isDirectory()) continue;
        const candidate = path.join(PROVIDERS_DIR, plugin.name, 'sample_reports', name);
        if (existsSync(candidate)) return candidate;
    }
    return path.join(SHARED_DIR, name);
}
