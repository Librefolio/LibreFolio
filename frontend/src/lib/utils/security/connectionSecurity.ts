/**
 * Connection security: how safely this browser talks to LibreFolio. Pure rules, no I/O.
 *
 * The browser knows its own protocol and the host it was pointed at; the server
 * (`GET /api/v1/system/connection`) adds the class of the address it sees. The server can confirm
 * the browser's verdict or make it uncertain, never make it secure.
 */

export type HostClass = 'loopback' | 'vpn' | 'lan' | 'public';
export type ServerClientClass = HostClass | 'unknown';
export type ConnectionLevel = 'secure' | 'local' | 'insecure';
export type ConnectionReason = 'https' | 'localhost' | 'vpn' | 'lan' | 'uncertain' | 'internet';

/** What the server answered about this request. */
export interface ServerView {
    clientClass: ServerClientClass;
    cookieSecure: boolean;
}

export interface ConnectionAssessment {
    level: ConnectionLevel;
    reason: ConnectionReason;
    /** HTTPS in the browser, but the server does not mark the session cookie Secure. */
    cookieWarning: boolean;
}

export interface ConnectionInput {
    /** `location.protocol`, such as `https:`. */
    protocol: string;
    /** `location.hostname`: an IPv6 literal may keep its brackets. */
    hostname: string;
    /** `null` until the server answers, or when it cannot. */
    server: ServerView | null;
}

/** The user page that explains the indicator, linked at its root (no anchor). */
export const CONNECTION_SECURITY_DOCS_PATH = 'user/connection-security/';

/** Names that never leave the local network: mDNS, the conventional home suffixes, the reserved `.internal`. */
const LAN_SUFFIXES = ['.local', '.lan', '.home.arpa', '.internal'];

/** Lower-cased, without the brackets of an IPv6 literal or the trailing dot of a fully qualified name. */
function normaliseHost(hostname: string): string {
    let host = hostname.trim().toLowerCase();
    if (host.startsWith('[') && host.endsWith(']')) host = host.slice(1, -1);
    if (host.endsWith('.')) host = host.slice(0, -1);
    return host;
}

/** The four octets of a dotted IPv4 literal, or null. */
function parseIPv4(host: string): number[] | null {
    const parts = host.split('.');
    if (parts.length !== 4 || !parts.every((part) => /^\d{1,3}$/.test(part))) return null;
    const octets = parts.map(Number);
    return octets.every((octet) => octet <= 255) ? octets : null;
}

/** The eight 16-bit groups of an IPv6 literal (`::`, an embedded IPv4 tail and a zone id allowed), or null. */
function parseIPv6(host: string): number[] | null {
    let text = host.split('%')[0];
    if (!text.includes(':')) return null;
    const lastColon = text.lastIndexOf(':');
    const last = text.slice(lastColon + 1);
    if (last.includes('.')) {
        const v4 = parseIPv4(last);
        if (!v4) return null;
        text = `${text.slice(0, lastColon + 1)}${((v4[0] << 8) | v4[1]).toString(16)}:${((v4[2] << 8) | v4[3]).toString(16)}`;
    }
    const halves = text.split('::');
    if (halves.length > 2) return null;
    const groups = (part: string): number[] | null => {
        if (part === '') return [];
        const values = part.split(':').map((group) => (/^[0-9a-f]{1,4}$/.test(group) ? parseInt(group, 16) : Number.NaN));
        return values.some(Number.isNaN) ? null : values;
    };
    const head = groups(halves[0]);
    const tail = halves.length === 2 ? groups(halves[1]) : [];
    if (head === null || tail === null) return null;
    const missing = 8 - head.length - tail.length;
    if (halves.length === 2 ? missing < 1 : missing !== 0) return null;
    return [...head, ...new Array<number>(missing).fill(0), ...tail];
}

function classifyIPv4([a, b]: number[]): HostClass {
    if (a === 127) return 'loopback';
    if (a === 100 && b >= 64 && b <= 127) return 'vpn'; // CGNAT 100.64/10: Tailscale, Headscale
    if (a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 169 && b === 254)) return 'lan';
    return 'public';
}

function classifyIPv6(groups: number[]): HostClass {
    if (groups.slice(0, 7).every((group) => group === 0) && groups[7] === 1) return 'loopback';
    if (groups.slice(0, 5).every((group) => group === 0) && groups[5] === 0xffff) {
        return classifyIPv4([groups[6] >> 8, groups[6] & 0xff, groups[7] >> 8, groups[7] & 0xff]);
    }
    if (groups[0] === 0xfd7a && groups[1] === 0x115c && groups[2] === 0xa1e0) return 'vpn'; // Tailscale's fd7a:115c:a1e0::/48
    if ((groups[0] & 0xffc0) === 0xfe80 || (groups[0] & 0xfe00) === 0xfc00) return 'lan'; // link-local, unique-local
    return 'public';
}

/** Class of the host the browser was pointed at. */
export function classifyHost(hostname: string): HostClass {
    const host = normaliseHost(hostname);
    const v4 = parseIPv4(host);
    if (v4) return classifyIPv4(v4);
    const v6 = parseIPv6(host);
    if (v6) return classifyIPv6(v6);
    if (host === 'localhost' || host.endsWith('.localhost')) return 'loopback';
    if (host.endsWith('.ts.net')) return 'vpn';
    if (!host.includes('.') || LAN_SUFFIXES.some((suffix) => host.endsWith(suffix))) return 'lan';
    return 'public';
}

/**
 * The level and its reason, from the browser's view and, once it answers, the server's.
 *
 * HTTPS and the loopback are the browser's call alone. Otherwise the server's view of the source
 * can only confirm the browser's verdict or turn it uncertain: a public source behind a local or
 * VPN name, a local source behind a public name. It never makes a connection secure.
 */
export function assessConnection({protocol, hostname, server}: ConnectionInput): ConnectionAssessment {
    const cookieWarning = protocol === 'https:' && server !== null && !server.cookieSecure;
    if (protocol === 'https:') return {level: 'secure', reason: 'https', cookieWarning};
    const seen = server?.clientClass ?? null;
    switch (classifyHost(hostname)) {
        case 'loopback':
            return {level: 'secure', reason: 'localhost', cookieWarning};
        case 'vpn':
            return seen === 'public' ? {level: 'local', reason: 'uncertain', cookieWarning} : {level: 'secure', reason: 'vpn', cookieWarning};
        case 'lan':
            return {level: 'local', reason: seen === 'public' ? 'uncertain' : 'lan', cookieWarning};
        case 'public':
            return seen === 'loopback' || seen === 'vpn' || seen === 'lan' ? {level: 'local', reason: 'uncertain', cookieWarning} : {level: 'insecure', reason: 'internet', cookieWarning};
    }
}

/** The connection-security page, in the user's documentation language. */
export function connectionSecurityDocsUrl(lang: string): string {
    const prefix = lang && lang !== 'en' ? `${lang}/` : '';
    return `/mkdocs/${prefix}${CONNECTION_SECURITY_DOCS_PATH}`;
}
