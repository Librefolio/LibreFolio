/**
 * isLocalHost — is the host the admin reached the instance through a local one? (accounts lot A7b, C4)
 *
 * The open-registration warning is for an instance reached through a host "other than localhost and the local network"
 * (decision §10.4); the list is §4.7's, with the IPv6 ranges the coordinator approved (16/10, 20:30). The contract under
 * test:
 *   - local: `localhost` and every name under `.localhost`; the IPv4 ranges 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12,
 *     192.168.0.0/16 and 100.64.0.0/10 (CGNAT, where Tailscale numbers its nodes); the IPv6 loopback `::1`, the unique
 *     local fc00::/7 (`fc…`, `fd…`) and the link local fe80::/10; an IPv4-mapped IPv6 address, `::ffff:a.b.c.d`,
 *     classified as the IPv4 it carries; a single-label name (`nas`); a name ending in `.local`, `.lan`, `.home.arpa`
 *     or `.internal`;
 *   - external: every other address — a documentation range too (203.0.113.0/24, 2001:db8::/32): not local is not
 *     local —, every name under `.ts.net` (Tailscale Funnel can publish it to the internet), every other name;
 *   - neither case nor a trailing dot counts, and an IPv6 literal counts with or without the brackets
 *     `location.hostname` keeps around it (`[::1]`);
 *   - a suffix counts as whole labels (`nas.mylan` is not under `.lan`), an IPv6 group as a number (`fd::1` is
 *     `00fd::1`, outside fc00::/7), and a name that starts like an address is a name (`10.0.0.1.example.com`).
 *
 * Every range is read on both sides of both its boundaries: its first and last address, and the address just before
 * and just after it.
 *
 * `location.hostname` is the WHATWG URL parser's serialisation: names lower-cased, the trailing dot of an IPv4 literal
 * dropped, an IPv6 literal compressed, lower-cased and in brackets — and an IPv4-mapped address written in hex, never
 * dotted: the page `http://[::ffff:127.0.0.1]/` has the hostname `[::ffff:7f00:1]`. The dotted form is the contract's
 * wording; the hex form is the only one a browser hands over, so it has a case of its own, which reads it from the URL
 * parser itself (Node's follows the same standard as the browsers' and jsdom's).
 *
 * A neighbour already parses these hosts: `classifyHost()` in `utils/security/connectionSecurity.ts` (plan 36). It is
 * not this rule: it calls a `*.ts.net` name a VPN one, which is external here, and it counts 169.254.0.0/16 as LAN,
 * which §4.7 does not list.
 *
 * Not pinned, either way: 169.254.0.0/16, `0.0.0.0` and `::`, the deprecated IPv4-compatible `::a.b.c.d`, an IPv6 zone
 * id, a spelling of an IPv6 address the URL parser never produces (`0:0:0:0:0:0:0:1`), the bare `home.arpa`, and the
 * empty string.
 *
 * Pure: the node environment. Red until A7b: `frontend/src/lib/features/auth/localHost.ts` does not exist yet, the
 * import fails and the whole file is red.
 */
import {describe, expect, it} from 'vitest';
import {isLocalHost} from './localHost';

/** A host, and why it is what the case says. */
type Row = [host: string, why: string];
/** A host, whether it is local, and why. */
type JudgedRow = [host: string, local: boolean, why: string];

/** Every IPv6 row twice: as written, and in the brackets `location.hostname` keeps around it. */
function withAndWithoutBrackets(rows: Row[]): Row[] {
    return rows.flatMap(([host, why]): Row[] => [
        [host, why],
        [`[${host}]`, `${why}, in brackets`],
    ]);
}

const LOCAL_NAMES: Row[] = [
    ['localhost', 'the loopback name'],
    ['app.localhost', 'a name under .localhost'],
    ['api.app.localhost', 'a deeper name under .localhost'],
    ['nas', 'a single-label name'],
    ['librefolio', 'a single-label name'],
    ['home-server', 'a single-label name with a hyphen'],
    ['nas.local', 'an mDNS name'],
    ['printer.office.local', 'a deeper mDNS name'],
    ['nas.lan', 'the conventional home suffix'],
    ['nas.home.arpa', 'the home network domain'],
    ['librefolio.internal', 'the suffix reserved for private use'],
];

const EXTERNAL_NAMES: Row[] = [
    ['example.com', 'a public name'],
    ['librefolio.app', 'a public name'],
    ['my.nas.example.com', 'a public name, whatever its labels sound like'],
    ['nas.tailnet-1234.ts.net', 'a Tailscale name: Funnel can publish it'],
    ['librefolio.example.ts.net', 'a Tailscale name'],
    ['localhost.example.com', 'localhost as the first label of a public name'],
    ['nas.local.example.com', 'a local suffix in the middle of a public name'],
    ['lan.example.com', 'a local suffix as the first label of a public name'],
    ['nas.notlocalhost', 'a suffix counts as whole labels: not under .localhost'],
    ['nas.mylocal', 'not under .local'],
    ['nas.mylan', 'not under .lan'],
    ['nas.myhome.arpa', 'not under .home.arpa'],
    ['nas.arpa', '.arpa alone is not .home.arpa'],
    ['nas.notinternal', 'not under .internal'],
    ['10.0.0.1.example.com', 'a name that starts like a private address is a name'],
];

const IPV4_LOCAL: Row[] = [
    ['127.0.0.0', 'the first address of 127.0.0.0/8'],
    ['127.0.0.1', 'the loopback'],
    ['127.1.2.3', 'inside 127.0.0.0/8'],
    ['127.255.255.255', 'the last address of 127.0.0.0/8'],
    ['10.0.0.0', 'the first address of 10.0.0.0/8'],
    ['10.0.0.1', 'inside 10.0.0.0/8'],
    ['10.255.255.255', 'the last address of 10.0.0.0/8'],
    ['172.16.0.0', 'the first address of 172.16.0.0/12'],
    ['172.20.10.1', 'inside 172.16.0.0/12'],
    ['172.31.255.255', 'the last address of 172.16.0.0/12'],
    ['192.168.0.0', 'the first address of 192.168.0.0/16'],
    ['192.168.1.10', 'a home network address'],
    ['192.168.255.255', 'the last address of 192.168.0.0/16'],
    ['100.64.0.0', 'the first address of 100.64.0.0/10 (CGNAT, Tailscale)'],
    ['100.100.100.100', 'the Tailscale resolver'],
    ['100.127.255.255', 'the last address of 100.64.0.0/10'],
];

const IPV4_EXTERNAL: Row[] = [
    ['126.255.255.255', 'just before 127.0.0.0/8'],
    ['128.0.0.0', 'just after 127.0.0.0/8'],
    ['9.255.255.255', 'just before 10.0.0.0/8'],
    ['11.0.0.0', 'just after 10.0.0.0/8'],
    ['172.15.255.255', 'just before 172.16.0.0/12'],
    ['172.32.0.0', 'just after 172.16.0.0/12'],
    ['172.32.0.1', 'after 172.16.0.0/12'],
    ['192.167.255.255', 'just before 192.168.0.0/16'],
    ['192.169.0.0', 'just after 192.168.0.0/16'],
    ['192.169.0.1', 'after 192.168.0.0/16'],
    ['100.63.255.255', 'just before 100.64.0.0/10'],
    ['100.128.0.0', 'just after 100.64.0.0/10'],
    ['100.128.0.1', 'after 100.64.0.0/10'],
    ['8.8.8.8', 'a public resolver'],
    ['203.0.113.7', 'a documentation address: not local is not local'],
];

const IPV6_LOCAL: Row[] = [
    ['::1', 'the loopback'],
    ['fc00::', 'the first address of fc00::/7 (unique local)'],
    ['fc00::1', 'a unique-local address under fc'],
    ['fd12:3456:789a::1', 'a unique-local address under fd'],
    ['fd7a:115c:a1e0::1', 'a Tailscale node'],
    ['fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff', 'the last address of fc00::/7'],
    ['fe80::', 'the first address of fe80::/10 (link local)'],
    ['fe80::1', 'a link-local address'],
    ['febf:ffff:ffff:ffff:ffff:ffff:ffff:ffff', 'the last address of fe80::/10'],
];

const IPV6_EXTERNAL: Row[] = [
    ['::2', 'the address just after the loopback'],
    ['fbff:ffff:ffff:ffff:ffff:ffff:ffff:ffff', 'just before fc00::/7'],
    ['fe00::', 'just after fc00::/7'],
    ['fe7f:ffff:ffff:ffff:ffff:ffff:ffff:ffff', 'just before fe80::/10'],
    ['fec0::', 'just after fe80::/10: the old site-local range is not in the list'],
    ['fd::1', 'its first group is 00fd: a number, not the prefix fd'],
    ['fc::1', 'its first group is 00fc'],
    ['fe8::1', 'its first group is 0fe8'],
    ['2001:db8::1', 'a documentation address, which ends in ::1 without being the loopback'],
    ['2606:4700:4700::1111', 'a public resolver'],
];

/** The IPv4 address an IPv4-mapped IPv6 address carries, whether that IPv4 is local, and why. */
const MAPPED: JudgedRow[] = [
    ['127.0.0.1', true, 'the loopback'],
    ['10.1.2.3', true, 'inside 10.0.0.0/8'],
    ['172.16.0.1', true, 'inside 172.16.0.0/12'],
    ['192.168.1.1', true, 'inside 192.168.0.0/16'],
    ['100.64.0.1', true, 'inside 100.64.0.0/10'],
    ['8.8.8.8', false, 'a public address'],
    ['172.32.0.1', false, 'after 172.16.0.0/12'],
    ['192.169.0.1', false, 'after 192.168.0.0/16'],
    ['100.128.0.1', false, 'after 100.64.0.0/10'],
];

/** Every mapped address twice, in the dotted form of the contract: as written, and in brackets. */
const MAPPED_DOTTED: JudgedRow[] = MAPPED.flatMap(([ipv4, local, why]): JudgedRow[] => [
    [`::ffff:${ipv4}`, local, why],
    [`[::ffff:${ipv4}]`, local, `${why}, in brackets`],
]);

const SPELLINGS: JudgedRow[] = [
    ['LOCALHOST', true, 'capitals'],
    ['App.LocalHost', true, 'mixed case under .localhost'],
    ['NAS', true, 'a single label in capitals'],
    ['NAS.Local', true, 'mixed case under .local'],
    ['printer.LAN', true, 'a suffix in capitals'],
    ['nas.HOME.ARPA', true, 'a two-label suffix in capitals'],
    ['Vault.Internal', true, 'mixed case under .internal'],
    ['localhost.', true, 'a fully qualified name'],
    ['nas.', true, 'a single label, fully qualified: its dot does not make it two labels'],
    ['nas.local.', true, 'fully qualified, under .local'],
    ['NAS.Home.Arpa.', true, 'capitals and a trailing dot'],
    ['10.1.2.3.', true, 'an IPv4 literal with a trailing dot'],
    ['EXAMPLE.COM', false, 'a public name in capitals'],
    ['example.com.', false, 'a public name, fully qualified'],
    ['Nas.Tailnet-1234.TS.NET', false, 'a Tailscale name in capitals'],
    ['nas.tailnet-1234.ts.net.', false, 'a Tailscale name, fully qualified'],
    ['FE80::1', true, 'IPv6 hex digits in capitals'],
    ['[FD12:3456:789A::1]', true, 'IPv6 capitals in brackets'],
    ['::FFFF:192.168.1.1', true, 'an IPv4-mapped prefix in capitals'],
    ['[2001:DB8::1]', false, 'a public IPv6 address in capitals'],
];

describe('isLocalHost — names', () => {
    // red until A7b
    it.each(LOCAL_NAMES)('%s is local: %s', (host) => {
        expect(isLocalHost(host)).toBe(true);
    });

    // red until A7b
    it.each(EXTERNAL_NAMES)('%s is external: %s', (host) => {
        expect(isLocalHost(host)).toBe(false);
    });
});

describe('isLocalHost — IPv4, on both sides of every boundary', () => {
    // red until A7b
    it.each(IPV4_LOCAL)('%s is local: %s', (host) => {
        expect(isLocalHost(host)).toBe(true);
    });

    // red until A7b
    it.each(IPV4_EXTERNAL)('%s is external: %s', (host) => {
        expect(isLocalHost(host)).toBe(false);
    });
});

describe('isLocalHost — IPv6, bare or in brackets, on both sides of every boundary', () => {
    // red until A7b
    it.each(withAndWithoutBrackets(IPV6_LOCAL))('%s is local: %s', (host) => {
        expect(isLocalHost(host)).toBe(true);
    });

    // red until A7b
    it.each(withAndWithoutBrackets(IPV6_EXTERNAL))('%s is external: %s', (host) => {
        expect(isLocalHost(host)).toBe(false);
    });
});

describe('isLocalHost — an IPv4-mapped IPv6 address is classified as the IPv4 it carries', () => {
    // red until A7b
    it.each(MAPPED_DOTTED)('%s → local %s: %s', (host, local) => {
        expect(isLocalHost(host)).toBe(local);
    });

    // red until A7b
    it.each(MAPPED)('the page http://[::ffff:%s]/ → local %s (%s), read in the hex form its location.hostname holds', (ipv4, local) => {
        const hostname = new URL(`http://[::ffff:${ipv4}]/`).hostname;
        expect(hostname, 'premise: the URL parser writes an IPv4-mapped address in hex, in brackets, never dotted').toMatch(/^\[::ffff:[0-9a-f]{1,4}:[0-9a-f]{1,4}\]$/);

        expect(isLocalHost(hostname), `location.hostname ${hostname}`).toBe(local);
        expect(isLocalHost(hostname.slice(1, -1)), `${hostname.slice(1, -1)}, without its brackets`).toBe(local);
    });
});

describe('isLocalHost — neither case nor a trailing dot counts', () => {
    // red until A7b
    it.each(SPELLINGS)('%s → local %s: %s', (host, local) => {
        expect(isLocalHost(host)).toBe(local);
    });
});
