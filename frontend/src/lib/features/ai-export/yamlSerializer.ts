/**
 * Shared minimal YAML serializer for the AI export renderers — no external
 * dependency. Used by both the instruction-bearing prompt renderer and the
 * data-only renderer so the two stay byte-for-byte consistent in formatting.
 */

export function toYaml(obj: unknown, indent = 0): string {
    const pad = '  '.repeat(indent);

    if (obj === null || obj === undefined) return `${pad}null`;
    if (typeof obj === 'boolean') return `${pad}${obj}`;
    if (typeof obj === 'number') return `${pad}${fmt(obj)}`;
    if (typeof obj === 'string') {
        if (obj.includes('\n') || obj.includes(':') || obj.includes('#') || obj.startsWith('"')) {
            return `${pad}"${obj.replace(/"/g, '\\"')}"`;
        }
        return `${pad}${obj}`;
    }

    if (Array.isArray(obj)) {
        if (obj.length === 0) return `${pad}[]`;
        // Primitive arrays inline
        if (obj.every((v) => typeof v === 'string' || typeof v === 'number')) {
            return `${pad}[${obj.map((v) => (typeof v === 'string' ? `"${v}"` : fmt(v as number))).join(', ')}]`;
        }
        return obj.map((item) => `${pad}- ${toYaml(item, indent + 1).trimStart()}`).join('\n');
    }

    if (typeof obj === 'object') {
        const entries = Object.entries(obj).filter(([, v]) => v !== undefined && v !== null);
        if (entries.length === 0) return `${pad}{}`;
        return entries
            .map(([k, v]) => {
                const valStr = toYaml(v, indent + 1);
                if (typeof v === 'object' && !Array.isArray(v)) {
                    return `${pad}${k}:\n${valStr}`;
                }
                if (Array.isArray(v) && v.length > 0 && typeof v[0] === 'object') {
                    return `${pad}${k}:\n${valStr}`;
                }
                return `${pad}${k}: ${valStr.trimStart()}`;
            })
            .join('\n');
    }

    return `${pad}${String(obj)}`;
}

export function fmt(n: number): string {
    return Number.isInteger(n) ? String(n) : n.toFixed(2);
}
