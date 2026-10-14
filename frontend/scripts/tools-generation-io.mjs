import {randomUUID} from 'node:crypto';
import {lstat, open, readFile, rename, unlink} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {join, resolve} from 'node:path';
import ts from 'typescript';
import {invariant} from './tools-schema-document.mjs';

const require = createRequire(import.meta.url);
const outputNames = new Set([
    'tool-contracts.openapi.json', 'generated-tools.ts', 'tool-contract-map.generated.ts', 'generated.ts',
]);
const inputNames = new Set([...outputNames, 'openapi.json']);

export async function assertLockedToolchain() {
    for (const [name, version] of [['openapi-zod-client', '1.18.3'], ['zod', '3.24.1']]) {
        const metadata = JSON.parse(await readFile(require.resolve(`${name}/package.json`), 'utf8'));
        invariant(metadata.version === version,
            `expected locked ${name}@${version}, found ${metadata.version}; review the adapter before upgrading`);
    }
}

export function validateGeneratedTypes(files) {
    const options = {
        strict: true, noEmit: true, skipLibCheck: true, types: [],
        target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
        moduleResolution: ts.ModuleResolutionKind.Bundler, esModuleInterop: true,
    };
    const sources = new Map([...files].map(([path, source]) => [resolve(path), source]));
    const host = ts.createCompilerHost(options, true);
    const originalGetSourceFile = host.getSourceFile.bind(host);
    const originalReadFile = host.readFile.bind(host);
    const originalFileExists = host.fileExists.bind(host);
    host.readFile = (path) => sources.get(resolve(path)) ?? originalReadFile(path);
    host.fileExists = (path) => sources.has(resolve(path)) || originalFileExists(path);
    host.getSourceFile = (path, languageVersion, onError, shouldCreateNewSourceFile) => {
        const source = sources.get(resolve(path));
        return source === undefined
            ? originalGetSourceFile(path, languageVersion, onError, shouldCreateNewSourceFile)
            : ts.createSourceFile(path, source, languageVersion, true, ts.ScriptKind.TS);
    };
    const program = ts.createProgram([...sources.keys()], options, host);
    const diagnostics = ts.getPreEmitDiagnostics(program);
    invariant(diagnostics.length === 0, `generated codec/map type validation failed:\n${ts.formatDiagnostics(
        diagnostics, {
            getCanonicalFileName: (path) => path,
            getCurrentDirectory: () => process.cwd(),
            getNewLine: () => '\n',
        })}`);
}

async function readOwnedFile(path) {
    try {
        const status = await lstat(path);
        invariant(status.isFile() && !status.isSymbolicLink(), `refusing non-file output ${path}`);
        return await readFile(path);
    } catch (error) {
        if (error.code === 'ENOENT') return null;
        throw error;
    }
}

async function removeNamedFile(path) {
    try {
        await unlink(path);
    } catch (error) {
        if (error.code !== 'ENOENT') throw error;
    }
}

async function releaseCreatedLock(path, handle, identity, ownership) {
    const assertIdentity = (status) => {
        invariant(status.isFile() && status.dev === identity.dev && status.ino === identity.ino,
            `lock path was replaced; refusing to remove it: ${path}`);
    };
    assertIdentity(await lstat(path, {bigint: true}));
    if (ownership !== null) {
        const status = await handle.stat({bigint: true});
        invariant(status.size === BigInt(ownership.length), `lock ownership changed: ${path}`);
        const current = Buffer.alloc(ownership.length);
        let offset = 0;
        while (offset < current.length) {
            const {bytesRead} = await handle.read(current, offset, current.length - offset, offset);
            if (bytesRead === 0) break;
            offset += bytesRead;
        }
        invariant(offset === ownership.length && current.equals(ownership), `lock ownership changed: ${path}`);
    }
    // Keep the original handle open so an unlinked lock's inode cannot be reused.
    assertIdentity(await lstat(path, {bigint: true}));
    await unlink(path);
}

export async function withToolGenerationLock(directory, action) {
    const path = join(directory, '.tools-codegen.lock');
    const ownership = Buffer.from(JSON.stringify({pid: process.pid, token: randomUUID()}));
    let handle;
    try {
        handle = await open(path, 'wx+', 0o600);
    } catch (error) {
        if (error.code === 'EEXIST') {
            throw new Error(`Tool codegen is locked: ${path}. Verify its owner before removing a stale lock.`);
        }
        throw error;
    }
    let identity;
    let initialized = false;
    let result;
    const failures = [];
    try {
        identity = await handle.stat({bigint: true});
        await handle.writeFile(ownership);
        initialized = true;
        result = await action();
    } catch (error) {
        failures.push(error);
    }
    try {
        identity ??= await handle.stat({bigint: true});
        await releaseCreatedLock(path, handle, identity, initialized ? ownership : null);
    } catch (error) {
        failures.push(error);
    }
    try {
        await handle.close();
    } catch (error) {
        failures.push(error);
    }
    if (failures.length === 1) throw failures[0];
    if (failures.length > 1) throw new AggregateError(failures, `Tool generation and lock cleanup failed: ${path}`);
    return result;
}

export async function publishGenerationSet(directory, contents, expected = new Map()) {
    const entries = [];
    const token = `${process.pid}.${randomUUID()}`;
    for (const [name, value] of contents) {
        invariant(outputNames.has(name), `unexpected generated output ${name}`);
        const path = join(directory, name);
        entries.push({
            path, bytes: Buffer.from(value), previous: await readOwnedFile(path),
            pending: `${path}.${token}.pending`, backup: `${path}.${token}.previous`,
            pendingCreated: false, backedUp: false, published: false,
        });
    }
    const failures = [];
    try {
        for (const entry of entries) {
            const handle = await open(entry.pending, 'wx', 0o644);
            entry.pendingCreated = true;
            try {
                await handle.writeFile(entry.bytes);
                await handle.sync();
            } finally {
                await handle.close();
            }
            invariant(await readOwnedFile(entry.backup) === null, `backup path already exists: ${entry.backup}`);
        }
        for (const [name, bytes] of expected) {
            invariant(inputNames.has(name), `unexpected generation input ${name}`);
            const current = await readOwnedFile(join(directory, name));
            invariant(current !== null && current.equals(Buffer.from(bytes)),
                `${name} changed during generation; refusing a stale publication`);
        }
        for (const entry of entries) {
            const current = await readOwnedFile(entry.path);
            invariant(entry.previous === null ? current === null : current?.equals(entry.previous),
                `${entry.path} changed before publication`);
            if (entry.previous !== null) {
                await rename(entry.path, entry.backup);
                entry.backedUp = true;
            }
            await rename(entry.pending, entry.path);
            entry.published = true;
        }
    } catch (error) {
        failures.push(error);
        for (const entry of [...entries].reverse()) {
            try {
                if (entry.published) {
                    const current = await readOwnedFile(entry.path);
                    invariant(current?.equals(entry.bytes), `concurrent output edit; backup retained: ${entry.backup}`);
                }
                if (entry.backedUp) {
                    await rename(entry.backup, entry.path);
                    entry.backedUp = false;
                } else if (entry.published) {
                    await removeNamedFile(entry.path);
                }
            } catch (restoreError) {
                failures.push(restoreError);
            }
        }
    } finally {
        for (const entry of entries) {
            try {
                if (entry.pendingCreated) await removeNamedFile(entry.pending);
                if (failures.length === 0 && entry.backedUp) await removeNamedFile(entry.backup);
            } catch (cleanupError) {
                failures.push(cleanupError);
            }
        }
    }
    if (failures.length) throw new AggregateError(failures, 'Tool generation failed; do not use an incomplete output set');
}
