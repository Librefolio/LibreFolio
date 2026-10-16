/**
 * Whether the host a browser uses to reach this instance is local (decision §10.4: «the host of the request other than
 * localhost and the local network»). The open-registration warning (A7b) is for an instance reachable from outside.
 *
 * Local:
 * - `localhost`, and every name under `.localhost`;
 * - IPv4 127.0.0.0/8, 10/8, 172.16/12, 192.168/16 and 100.64/10 (carrier-grade NAT, the Tailscale addresses);
 * - IPv6 `::1`, `fc00::/7` and `fe80::/10`, and an IPv4-mapped address (`::ffff:a.b.c.d`) by its IPv4 — browsers write
 *   it in hexadecimal, `[::ffff:7f00:1]`, and both forms are read;
 * - a name of a single label (`nas`), and the names under `.local`, `.lan`, `.home.arpa` and `.internal`.
 *
 * Everything else is external, the names under `.ts.net` included: Tailscale Funnel publishes them. The host may come
 * as `location.hostname` gives it: in any case, with the brackets of an IPv6 address, with a trailing dot.
 */

const LOCAL_SUFFIXES = ['.localhost', '.local', '.lan', '.home.arpa', '.internal'];

function ipv4Octets(host: string): number[] | null {
    const parts = host.split('.');
    if (parts.length !== 4 || !parts.every((part) => /^\d{1,3}$/.test(part))) return null;
    const octets = parts.map(Number);
    return octets.every((octet) => octet <= 255) ? octets : null;
}

function isLocalIpv4([first, second]: number[]): boolean {
    return first === 127 || first === 10 || (first === 172 && second >= 16 && second <= 31) || (first === 192 && second === 168) || (first === 100 && second >= 64 && second <= 127);
}

/** The IPv4 of an IPv4-mapped IPv6 address, dotted (`::ffff:127.0.0.1`) or as browsers write it (`::ffff:7f00:1`). */
function mappedIpv4(host: string): number[] | null {
    const dotted = /^::ffff:(\d{1,3}(?:\.\d{1,3}){3})$/.exec(host);
    if (dotted) return ipv4Octets(dotted[1]);
    const hex = /^::ffff:([0-9a-f]{1,4}):([0-9a-f]{1,4})$/.exec(host);
    if (!hex) return null;
    const high = parseInt(hex[1], 16);
    const low = parseInt(hex[2], 16);
    return [high >> 8, high & 0xff, low >> 8, low & 0xff];
}

function isLocalIpv6(host: string): boolean {
    if (host === '::1') return true;
    const mapped = mappedIpv4(host);
    if (mapped) return isLocalIpv4(mapped);
    const first = host.split(':')[0];
    if (!/^[0-9a-f]{1,4}$/.test(first)) return false;
    const group = parseInt(first, 16);
    // fc00::/7 (unique local) and fe80::/10 (link-local)
    return (group & 0xfe00) === 0xfc00 || (group & 0xffc0) === 0xfe80;
}

export function isLocalHost(hostname: string): boolean {
    let host = hostname.trim().toLowerCase();
    if (host.startsWith('[') && host.endsWith(']')) host = host.slice(1, -1);
    if (host.endsWith('.')) host = host.slice(0, -1);
    if (host === '') return true;
    if (host.includes(':')) return isLocalIpv6(host);
    const octets = ipv4Octets(host);
    if (octets) return isLocalIpv4(octets);
    if (host === 'localhost' || !host.includes('.')) return true;
    return LOCAL_SUFFIXES.some((suffix) => host.endsWith(suffix));
}
