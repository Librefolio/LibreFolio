/**
 * Anti-regression gate for the privacy masking channel (analysis §1.8).
 *
 * ## What this protects
 *
 * Global privacy (U2) works because every monetary amount is rendered through a
 * small set of formatters that consult the privacy store. The mechanical rule
 * used to classify a site — *"which formatter does it come out of?"* — is only
 * sound while that set is **known**. A new formatter written tomorrow is invisible
 * to the rule, gets classified structural by default, and leaks in silence.
 *
 * So this file does not test behaviour. It tests the **premise** of the rule: that
 * the set of places rendering money is the set we think it is.
 *
 * ## What it does, and what it deliberately does not
 *
 * It scans the source for two observable forms of money rendering and fails when
 * one appears that is **not in the registry below**. It does not judge whether a
 * new site is safe — a judging gate needs to be right about intent, and one that is
 * wrong in an annoying direction gets switched off, at which point it protects
 * nothing at all. Registering a site is a human decision recorded once.
 *
 * ## Why sites are keyed by content and not by line
 *
 * An unrelated edit above a site shifts its line number. A registry keyed by line
 * would go red for reasons that have nothing to do with money, which is the same
 * failure mode as a noisy gate: it trains people to update it without reading it.
 * Keyed by content, the gate stays quiet until the rendering itself changes.
 *
 * ## Completeness, stated honestly
 *
 * FORM_A is exact: `style: 'currency'` either appears or it does not.
 * FORM_B is a heuristic — a template literal interpolating a currency token
 * alongside a numeric-looking one. It cannot see money assembled across several
 * statements, nor an amount rendered with no currency marker at all (those are
 * registered below as judgement sites). The gate is deterministic about the forms
 * it knows; it is not a proof of completeness, and the note in
 * `.github/skills/devpy-tools/testing-frontend/SKILL.md` says so where someone
 * adding a rule will read it.
 */

import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync, statSync} from 'node:fs';
import {join, relative, resolve} from 'node:path';

type Status =
    /** Goes through the channel: masked at this site or at its function boundary. */
    | 'masked'
    /** Matches a form but renders no amount — registered so it stops being rediscovered. */
    | 'not-money'
    /** Real money outside the channel, deliberately not fixed yet. Named, not forgotten. */
    | 'residual'
    /** Real money outside the channel, found by this gate, not yet triaged. */
    | 'unmasked';

interface Site {
    file: string;
    /** Whitespace-collapsed matched text. The key, together with `file`. */
    snippet: string;
    status: Status;
    why: string;
}

const SRC = resolve(process.cwd(), 'src');

/** Already routed through the masking channel: not a false negative by construction. */
const SAFE_CALL = /formatCurrencyAmountPlain|formatCurrencyAmountHtml|formatCurrencyCodeHtml|formatCurrencyCode\b|riskHelpers\.formatCurrencyAmount|maskable\(/;
const FORM_A = /style\s*:\s*['"]currency['"]/;
const TEMPLATE_LITERAL = /`[^`]*`/g;
const INTERPOLATION = /\$\{([^}]*)\}/g;
const I18N_CALL = /\$_\(|\$t\(|label\(/;
/**
 * What makes a number *money* rather than a percentage or a quantity.
 *
 * `symbol` is here because a rendered currency **symbol** is not a currency
 * **token**: `` `${sign}${symbol}${compact}` `` renders dollars while containing
 * no identifier this regex would otherwise match. That shape was found in the
 * primary branch of `PerformanceChart.shortMoney`, which the gate had caught only
 * through the fallback branch that happened to share its line — so its coverage of
 * that site depended on where the source wrapped.
 *
 * `sign` is deliberately **not** here: it appears in 29 further template literals,
 * almost all percentages (`formatSignedPercent`) and CSS class names
 * (`signedToneClass`). A gate that fires on a class name is a gate someone
 * switches off.
 */
const CURRENCY_TOKEN = /currency|symbol/i;
const NUMERIC_TOKEN = /toFixed|toLocaleString|NumberFormat|format|amount|price|balance|pnl|\bnet\b|total|compact|\bsum\b|\bvalue\b/i;

const collapse = (s: string): string => s.trim().replace(/\s+/g, ' ');

function sourceFiles(dir: string, acc: string[] = []): string[] {
    for (const entry of readdirSync(dir)) {
        const full = join(dir, entry);
        if (statSync(full).isDirectory()) {
            if (entry === 'node_modules' || entry === '__mocks__' || entry === '__tests__') continue;
            sourceFiles(full, acc);
        } else if (/\.(ts|svelte)$/.test(entry) && !/\.test\.ts$/.test(entry)) {
            acc.push(full);
        }
    }
    return acc;
}

interface Hit {
    file: string;
    line: number;
    snippet: string;
    form: 'A' | 'B';
}

function scan(): Hit[] {
    const hits: Hit[] = [];
    for (const full of sourceFiles(SRC)) {
        const file = relative(SRC, full).replaceAll('\\', '/');
        readFileSync(full, 'utf8')
            .split('\n')
            .forEach((line, index) => {
                if (FORM_A.test(line)) {
                    hits.push({file, line: index + 1, snippet: collapse(line), form: 'A'});
                }
                if (SAFE_CALL.test(line)) return;
                for (const literal of line.match(TEMPLATE_LITERAL) ?? []) {
                    const tokens = [...literal.matchAll(INTERPOLATION)].map((m) => m[1].trim());
                    if (!tokens.some((t) => CURRENCY_TOKEN.test(t))) continue;
                    const others = tokens.filter((t) => !CURRENCY_TOKEN.test(t) && !I18N_CALL.test(t));
                    if (!others.some((t) => NUMERIC_TOKEN.test(t))) continue;
                    hits.push({file, line: index + 1, snippet: collapse(literal), form: 'B'});
                }
            });
    }
    return hits;
}

/**
 * The registered set. Adding an entry here is the act of deciding; the gate only
 * notices that a decision is missing.
 */
const REGISTRY: Site[] = [
    {
        file: 'lib/components/risk/riskAnalysisHelpers.ts',
        snippet: "return new Intl.NumberFormat(locale, {style: 'currency', currency, maximumFractionDigits: 2}).format(amount);",
        status: 'masked',
        why: 'The fifth currency formatter. Masked one line above, after the two em-dash absence checks.',
    },
    {
        file: 'lib/components/brokers/lots/LotComparisonChart.svelte',
        snippet: "style: 'currency',",
        status: 'masked',
        why: 'formatAxisCurrency: masked at the function boundary, which covers this exit and the catch fallback below.',
    },
    {
        file: 'lib/components/brokers/lots/LotComparisonChart.svelte',
        snippet: '`${formatAxisNumber(normalized)} ${currency}`',
        status: 'masked',
        why: 'The catch fallback of formatAxisCurrency — the second money-rendering exit of the same function, covered by the same boundary check.',
    },
    {
        file: 'lib/features/ai-export/templates/snapshotDataRenderer.ts',
        snippet: "return 10 ** -(new Intl.NumberFormat('en', {style: 'currency', currency: currencyCode}).resolvedOptions().maximumFractionDigits ?? 2);",
        status: 'not-money',
        why: 'Reads resolvedOptions().maximumFractionDigits and renders nothing. The known false positive of form A, kept registered so the next reader does not re-derive it.',
    },
    {
        file: 'lib/components/dashboard/GrowthChart.svelte',
        snippet: '`${baseCurrency} ${v.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`',
        status: 'residual',
        why: 'fmtCurrency, analysis §1.8 #3. Out of scope while workstream I rewrites this file; one line to mask once it returns.',
    },
    {
        file: 'lib/components/dashboard/GrowthChart.svelte',
        snippet: "`<div style=\"display:flex;justify-content:space-between;gap:16px;color:${pnlColor}\"><span><b>${$_('dashboard.totalPnl')}</b></span><b>${totalPnlVal >= 0 ? '+' : '−'}${fmtCurrency(Math.abs(totalPnlVal))}</b></div>`",
        status: 'residual',
        why: 'A consumer of fmtCurrency in the same file, which §1.8 did not list. Covered by masking fmtCurrency; registered so the residual is one decision and not two.',
    },
    {
        file: 'lib/components/dashboard/PerformanceChart.svelte',
        snippet: '`${sign}${compact} ${currency}`',
        status: 'unmasked',
        why: 'shortMoney: a money formatter that never calls Intl with style currency, so §1.8 — which anchored on that API — did not see it. Compact notation, so it discloses the magnitude it is meant to hide. This is the fallback branch, used when no symbol is known.',
    },
    {
        file: 'lib/components/dashboard/PerformanceChart.svelte',
        snippet: '`${sign}${symbol}${compact}`',
        status: 'unmasked',
        why: 'shortMoney again, the primary branch — the one that renders for every currency with a known symbol. It carries no currency identifier, only a rendered symbol, so the gate saw this site at first only through the fallback branch sharing its line: coverage of the more important path was an accident of where the source wrapped. CURRENCY_TOKEN was widened to close it.',
    },
    {
        file: 'lib/components/transactions/events/EventCreateMiniModal.svelte',
        snippet: '`${amt.toFixed(2)} ${assetCurrency}`',
        status: 'unmasked',
        why: 'The success toast for a created event. §1.8 listed line 73 of this file as an input value (excluded by D7) and stopped there; this is a different line in the same file, and it renders.',
    },
    {
        file: 'lib/features/tools/pac-allocator/PacResultPanel.svelte',
        snippet: '`${formatDecimalForDisplay(fact.value.amount, {maxFrac: 12})} ${fact.value.currency}`',
        status: 'unmasked',
        why: 'moneyText, the ideal allocation column. Owned by the Tool/PAC workstream; registered here, to be masked by whoever owns the file.',
    },
    {
        file: 'lib/features/tools/pac-allocator/RebalancerResultPanel.svelte',
        snippet: '`${formatDecimalForDisplay(fact.value.amount, {maxFrac: 12})} ${fact.value.currency}`',
        status: 'unmasked',
        why: 'The rebalancer twin of the site above, same shape and same owner.',
    },
    {
        file: 'lib/components/transactions/events/AssetEventPicker.svelte',
        snippet: "`${diff >= 0 ? '+' : ''}${diff.toFixed(2)}${crossCurrency ? ' ≠' : ''}`",
        status: 'not-money',
        why: 'A cash delta rendered with no currency marker, used to rank candidate matches. Judgement site in the class of MeasurePanel: catching it would mean chasing toFixed over arbitrary numbers, and a gate that fires on arbitrary numbers is a gate someone switches off.',
    },
];

const key = (s: {file: string; snippet: string}): string => `${s.file}\u0000${s.snippet}`;
const listOf = (status: Status): string[] =>
    REGISTRY.filter((s) => s.status === status)
        .map((s) => s.file)
        .sort();

describe('money rendered outside the masking channel (analysis §1.8 gate)', () => {
    const hits = scan();

    it('finds the sites it is supposed to find', () => {
        // The positive control for every assertion below. "No unregistered site"
        // is also true when the scanner reads the wrong directory or the regexes
        // match nothing, and that is the failure this gate could not otherwise see.
        expect(hits.length).toBeGreaterThanOrEqual(REGISTRY.length);
        expect(hits.filter((h) => h.form === 'A').length).toBeGreaterThan(0);
        expect(hits.filter((h) => h.form === 'B').length).toBeGreaterThan(0);
        expect(hits.map((h) => h.file)).toContain('lib/components/risk/riskAnalysisHelpers.ts');
    });

    it('registers every site that renders money outside the channel', () => {
        const registered = new Set(REGISTRY.map(key));
        const unregistered = hits.filter((h) => !registered.has(key(h))).map((h) => `${h.file}:${h.line} (form ${h.form})\n    ${h.snippet}`);

        expect(
            unregistered,
            unregistered.length === 0
                ? ''
                : [
                      '',
                      'A site renders a monetary amount outside the privacy masking channel,',
                      'and it is not in the registry in this file.',
                      '',
                      'Route it through `maskable()` (see utils/privacy/maskable.ts), then add it',
                      'here with status "masked". If it renders no amount, add it as "not-money"',
                      'with the reason — an unexplained entry is indistinguishable from an oversight.',
                      '',
                      unregistered.join('\n  '),
                      '',
                  ].join('\n  '),
        ).toEqual([]);
    });

    it('keeps the registry from rotting', () => {
        const found = new Set(hits.map(key));
        const stale = REGISTRY.filter((s) => !found.has(key(s))).map((s) => `${s.file}\n    ${s.snippet}`);

        // A registry that keeps entries for code that no longer exists grows into a
        // list nobody trusts, and an untrusted list is worse than none: it makes the
        // next real entry look like more of the same.
        expect(stale, stale.length === 0 ? '' : `\n  Registered sites no longer present in the source — delete them:\n  ${stale.join('\n  ')}\n`).toEqual([]);
    });

    it('states which sites still render money in the clear', () => {
        // Asserted by exact content rather than by count: masking one of these must
        // fail here and force the list to be updated, so the round's partial
        // conformance cannot quietly become complete.
        expect(listOf('residual')).toEqual(['lib/components/dashboard/GrowthChart.svelte', 'lib/components/dashboard/GrowthChart.svelte']);
        expect(listOf('unmasked')).toEqual([
            'lib/components/dashboard/PerformanceChart.svelte',
            'lib/components/dashboard/PerformanceChart.svelte',
            'lib/components/transactions/events/EventCreateMiniModal.svelte',
            'lib/features/tools/pac-allocator/PacResultPanel.svelte',
            'lib/features/tools/pac-allocator/RebalancerResultPanel.svelte',
        ]);
    });

    it('sees both branches of a two-branch money line', () => {
        // A regression test for the gate itself, not for the product.
        //
        // `shortMoney` returns one of two template literals from a single line.
        // Only the fallback carries a `currency` identifier; the primary one
        // carries a rendered `symbol`. While CURRENCY_TOKEN required `currency`,
        // the primary branch was never matched — the site looked covered only
        // because both branches sat on the same line, so the gate's coverage of
        // its most important site would have been lost to a line wrap, in silence.
        //
        // Narrowing CURRENCY_TOKEN back must fail here rather than go quiet.
        const branches = hits.filter((h) => h.file === 'lib/components/dashboard/PerformanceChart.svelte' && h.form === 'B').map((h) => h.snippet);

        expect(branches).toContain('`${sign}${symbol}${compact}`');
        expect(branches).toContain('`${sign}${compact} ${currency}`');
    });

    it('gives every registered site a reason', () => {
        const unexplained = REGISTRY.filter((s) => s.why.trim().length < 20).map((s) => s.file);
        expect(unexplained).toEqual([]);
    });
});
