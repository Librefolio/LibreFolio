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
    /**
     * Real money shown in the clear *by rule*: market prices, asset-level events, FX rates,
     * WAC. The rule is the product owner's criterion of 2026-09-22 — a number is personal
     * when it lets you infer what the user owns, and these do not. Mirrors
     * `AmountSensitivity = 'public'` in `frontend/src/lib/utils/privacy/maskable.ts`.
     */
    | 'public'
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

/**
 * Already routed through the masking channel: not a false negative by construction.
 *
 * An entry here is a promise that whatever leaves the named function is masked, so
 * membership has a price: the function must be a module export pinned by a unit test
 * that would break if the masking were removed. A local closure cannot be pinned, so
 * adding one would be a promise nobody can break loudly — the gate would go quiet on
 * that channel forever, including the day someone unmasks it.
 *
 * Names are anchored with `\b` because a bare prefix absolves every longer name that
 * starts the same way: `formatCurrencyAmount` without it would also cover
 * `formatCurrencyAmountPlain` and `…Html`, which are listed here on their own merits.
 * The redundancy would be worse than noise — deleting one of those entries to expose
 * it to the gate again would then have no effect at all.
 */
const SAFE_CALL = /formatCurrencyAmountPlain|formatCurrencyAmountHtml|formatCurrencyCodeHtml|formatCurrencyCode\b|formatScopedCurrencyAmount\b|formatCurrencyAmount\b|maskable\(|maskFormattedNumber\(/;
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

/**
 * The hits of one source line, in the order `scan` reports them.
 *
 * A function of its own so that a synthetic line goes through exactly the code a real
 * file goes through: a regression test of the gate that ran on a copy of this logic
 * would test the copy.
 */
function scanLine(file: string, line: string, index: number): Hit[] {
    const hits: Hit[] = [];
    if (FORM_A.test(line)) {
        hits.push({file, line: index + 1, snippet: collapse(line), form: 'A'});
    }
    if (SAFE_CALL.test(line)) return hits;
    for (const literal of line.match(TEMPLATE_LITERAL) ?? []) {
        const tokens = [...literal.matchAll(INTERPOLATION)].map((m) => m[1].trim());
        if (!tokens.some((t) => CURRENCY_TOKEN.test(t))) continue;
        const others = tokens.filter((t) => !CURRENCY_TOKEN.test(t) && !I18N_CALL.test(t));
        if (!others.some((t) => NUMERIC_TOKEN.test(t))) continue;
        hits.push({file, line: index + 1, snippet: collapse(literal), form: 'B'});
    }
    return hits;
}

function scan(): Hit[] {
    const hits: Hit[] = [];
    for (const full of sourceFiles(SRC)) {
        const file = relative(SRC, full).replaceAll('\\', '/');
        readFileSync(full, 'utf8')
            .split('\n')
            .forEach((line, index) => {
                hits.push(...scanLine(file, line, index));
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
        snippet: "return maskCurrencyParts(new Intl.NumberFormat(locale, {style: 'currency', currency, maximumFractionDigits: 2}).formatToParts(amount));",
        status: 'masked',
        why: 'The fifth currency formatter. Masked in the same expression by maskCurrencyParts, which hides the digits and keeps the currency and the sign; the two em-dash absence checks run before it.',
    },
    {
        file: 'lib/components/brokers/lots/lotComparisonChartHelpers.ts',
        snippet: "style: 'currency',",
        status: 'masked',
        why: 'formatAxisCurrency, the absolute-return axis of the lot comparison chart, extracted from the component. Its Intl exit goes through maskCurrencyParts; its fallback exit masks with maskFormattedNumber( and so is not a hit at all.',
    },
    {
        file: 'lib/features/ai-export/templates/snapshotDataRenderer.ts',
        snippet: "return 10 ** -(new Intl.NumberFormat('en', {style: 'currency', currency: currencyCode}).resolvedOptions().maximumFractionDigits ?? 2);",
        status: 'not-money',
        why: 'Reads resolvedOptions().maximumFractionDigits and renders nothing. The known false positive of form A, kept registered so the next reader does not re-derive it.',
    },
    {
        file: 'lib/components/dashboard/GrowthChart.svelte',
        snippet: '`<div style="display:flex;justify-content:space-between;gap:16px;color:${pnlColor}"><span><b>${$_(\'dashboard.totalPnl\')}</b></span><b>${fmtCurrency(totalPnlVal, true)}</b></div>`',
        status: 'masked',
        why: "The P&L-total row of the Abs tooltip, a consumer of fmtCurrency that §1.8 did not list. fmtCurrency is masked at its definition in the same function, through maskFormattedNumber, which keeps the locale's sign outside the mask and masks the digits only (D8, D23b); the gate cannot follow a call into a local closure, so this row still matches through its totalPnlVal/pnlColor tokens. Unmasking the definition would bring the definition line back as an unregistered hit: the boundary is guarded by this gate, as for LotComparisonChart.formatAxisCurrency. The masking of this row is pinned behaviourally by GrowthChart.test.ts «masks every tooltip amount in the Abs, P&L-total and candle rows, keeping the currency and the sign readable».",
    },
    {
        file: 'lib/components/transactions/events/EventCreateMiniModal.svelte',
        snippet: '`${amt.toFixed(2)} ${assetCurrency}`',
        status: 'public',
        why: "The success toast for a created asset event. Asset events are asset-level, not the user's (backend/app/db/models.py, class AssetEvent: «Events are NOT transactions — they describe what happens to the asset globally, not what happens in a user's portfolio»), so the amount is public under the 2026-09-22 rule. It was registered as unmasked until that rule existed.",
    },
    {
        file: 'lib/components/transactions/events/AssetEventPicker.svelte',
        snippet: "`${diff >= 0 ? '+' : ''}${diff.toFixed(2)}${crossCurrency ? ' ≠' : ''}`",
        status: 'not-money',
        why: 'A cash delta rendered with no currency marker, used to rank candidate matches. Judgement site in the class of MeasurePanel: catching it would mean chasing toFixed over arbitrary numbers, and a gate that fires on arbitrary numbers is a gate someone switches off.',
    },
    {
        file: 'lib/features/tools/pac-allocator/planner/format.ts',
        snippet: "return new Intl.NumberFormat('en', {style: 'currency', currency: currencyCode}).resolvedOptions().maximumFractionDigits ?? 2;",
        status: 'not-money',
        why: 'cldrCurrencyDigits: reads resolvedOptions().maximumFractionDigits for the arrow step of PAC planner money inputs and renders nothing — the same form-A false positive as snapshotDataRenderer. Every planner amount leaves through formatCurrencyAmountPlain/Html in the same file.',
    },
    {
        file: 'lib/components/charts/PriceChartFull.svelte',
        snippet: '`${currencyHtml}: ${Number(value).toFixed(4)}${valueSuffix}${axisNoteHtml}`',
        status: 'public',
        why: "The value part of a price-chart tooltip row (asset and FX detail): the price, or the percentage return, of an asset, an FX pair or an overlay signal at the hovered date — market data, never the user's holdings, so public by the rule that keeps prices, rates and percentages readable. It matches only since K step 16 (06/10) moved the currency badge out of the label and next to the value, so that a phone can shrink the label and keep both whole; before that the same value rendered as `${labelHtml}: ${Number(value).toFixed(4)}…` with no currency token beside it.",
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
                      'If it renders money that is public by rule (a market price, an asset-level event, a rate), register it as "public" with the reason.',
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
        expect(listOf('residual')).toEqual([
            // one element per line: parallel removals must not touch the same line
        ]);
        expect(listOf('unmasked')).toEqual([
            // one element per line: parallel removals must not touch the same line
        ]);
        // Sites in the clear by rule are asserted by content too, so that reclassifying
        // one is a visible decision rather than a quiet edit to the registry.
        expect(listOf('public')).toEqual([
            // one element per line: parallel removals must not touch the same line
            'lib/components/charts/PriceChartFull.svelte',
            'lib/components/transactions/events/EventCreateMiniModal.svelte',
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
        // The fixture reproduces `PerformanceChart.shortMoney` as of `f1047f766`, so the
        // test no longer depends on a file owned by another workstream: masking that site
        // with `maskable(` puts the real line under SAFE_CALL, out of the scanner's reach,
        // and a positive control whose subject can disappear is not a control. The fixture
        // goes through the same `scanLine` as every real file, which is what makes this a
        // test of the gate and not of a copy of it.
        //
        // Narrowing CURRENCY_TOKEN back must fail here rather than go quiet.
        const shortMoneyLine = 'return symbol ? `${sign}${symbol}${compact}` : `${sign}${compact} ${currency}`;';
        const branches = scanLine('fixture', shortMoneyLine, 0)
            .filter((h) => h.form === 'B')
            .map((h) => h.snippet);

        expect(branches).toEqual(['`${sign}${symbol}${compact}`', '`${sign}${compact} ${currency}`']);
    });

    it('gives every registered site a reason', () => {
        const unexplained = REGISTRY.filter((s) => s.why.trim().length < 20).map((s) => s.file);
        expect(unexplained).toEqual([]);
    });
});
