/**
 * Colour roles in the browser: every migrated element draws the colour of its role, as the browser itself resolves it,
 * in the light and in the dark theme — and, in dark, what is not migrated yet keeps today's look from the legacy remap
 * of src/app.css, proven on probes of the spec's own rather than on a component of a page (colour programme,
 * workstream T: step T-2, the login/registration pilot; step T-3, the app shell; step T-5, the login background; then
 * the designer's round 2 of the palette, «Pietra e Salvia» in light and «Ardesia e Salvia» in dark, approved whole by
 * the developer on 15/10 — decision D-T17, step T-8: the sidebar is green in both themes, drawn from a family of roles
 * of its own, --lf-bar-*, which supersedes D-T15, the neutral sidebar with a green logo block alone. D-T19 made the
 * header green too; after his review of the preview, D-T23 gave it back a neutral surface of its own, step T-8b).
 *
 * ## What this protects
 *
 * The sign-in cards (LoginCard, RegisterCard, PasswordInput, PasswordStrength) and the app shell ((app)/+layout.svelte,
 * Sidebar with its connection-security line, Header and the menus of the header) moved from palette classes to the
 * role utilities of src/lib/theme/tokens.css (bg-lf-card, border-lf-input…). The unit gates prove that the source is
 * written right (src/themeRoles.gate.test.ts) and that the roles are a whole, legible table
 * (src/themeTokens.gate.test.ts); only a browser can prove that the cascade delivers them. In dark it has a rival: the
 * legacy remap of src/app.css (P1) is unlayered, so it beats every Tailwind utility, and its structural rules exempt an
 * element only through `:where(:not([class*='-lf-']))`. Without that exemption a migrated field would keep the legacy
 * border, text and placeholder, and the card the legacy border, and nothing but a computed style would say so.
 *
 * Round 2, as approved and then corrected (D-T23), changed values, which this spec never writes, and these things it
 * reads: the app and the standalone pages share one background (--lf-surface-app is derived from --lf-surface-page);
 * the sidebar is green (D-T17) — its surface, --lf-surface-bar; its text, --lf-bar-text; no right border (D-T23 took
 * off the dark one); an active item on a fill of its own, marked by an indicator on its left; a keyboard focus ring of
 * its own, --lf-bar-focus, since the page's --lf-focus would hardly show on the green; the connection-security levels
 * in the bright statuses of the bar; and a logo block with no surface of its own, through which the bar shows. The
 * header is neutral (D-T23): a surface of its own, --lf-surface-header, a step off the page's, a --lf-border-subtle
 * bottom border, and its controls in the page's roles, the page's focus ring included. The cards of the sign-in page
 * and the menus are in relief, --lf-border-raised (N3); a field under the pointer draws --lf-border-input-hover
 * (D-T18); the forgot-password card shows its commands in a terminal box (Q6); and the password requirements sit on
 * the panel surface.
 *
 * The login background (ui/AnimatedBackground.svelte, fixed behind `/` and the error page) left its literals for roles
 * as well, and its dark rules (`:global(html.dark)`) with them: its surface is --lf-surface-page, its illustration the
 * roles --lf-art-*, whose alpha is the strength of each layer. Those have no utility: the component reads them with
 * var() in its <style>, where no class grammar looks. themeTokens.gate.test.ts proves them declared and resolvable in
 * both themes (C2); only a browser can prove that each layer draws its own.
 *
 * (a) Signed out, on `/`, in each theme:
 *   - `login-modal`: background --lf-surface-card, border --lf-border-raised (N3) — in light the colour of
 *     --lf-border-subtle; in dark a colour of its own, checked to differ first, and there the proof that
 *     `html.dark .rounded-2xl` leaves the card alone;
 *   - `login-username`: border --lf-border-input at rest and --lf-focus in focus, text --lf-text-primary, placeholder
 *     --lf-text-placeholder — in dark, the proof that `html.dark input` and its `::placeholder` leave it alone;
 *   - on the desktop project, both fields of the card, `login-username` and `login-password` (PasswordInput): border
 *     --lf-border-input at rest, --lf-border-input-hover under the pointer (D-T18), then --lf-focus once focused there
 *     — focus beats hover — the three roles resolved to three different colours first. Tailwind writes `hover:`
 *     inside `@media (hover: hover)`, which the mobile project, a touch device, does not match: the case skips there;
 *   - `login-submit`: background --lf-action;
 *   - the register card, once the password meets every rule: every `password-rule-*` passed; the
 *     `password-requirements` box on --lf-surface-panel with a --lf-border-subtle border; and in each passed rule its
 *     ✓ — the rule's one `<svg>` — in --lf-success, its text in --lf-text-secondary;
 *   - the forgot-password card, `forgot-modal`, opened by `goto-forgot`: border --lf-border-raised; its terminal box,
 *     `forgot-reset-commands` (Q6), background --lf-terminal-bg and border --lf-terminal-border; and its four lines,
 *     the `<code>` children of the box, by position in the component's fixed markup — a `#` comment, then its command,
 *     twice — each comment checked to start with `#`, the shell's comment mark, before it is read: the commands in
 *     --lf-terminal-prompt, the comments in --lf-terminal-comment, the two roles resolved to two different colours
 *     first.
 *
 * (b) Signed in as TEST_USER, on `/dashboard`, in each theme:
 *   - --lf-surface-app resolves to the colour of --lf-surface-page (round 2: one background);
 *   - `app-shell`: background --lf-surface-app;
 *   - the sidebar — the `<nav>` that holds `sidebar-collapse-toggle`, since it has no test id of its own: background
 *     --lf-surface-bar, text --lf-bar-text, and no right border: a border-right-width of 0 (D-T23);
 *   - its logo block, `sidebar-brand`, one with the bar (D-T17): no background of its own — transparent, the bar shows
 *     through — and text --lf-on-brand. Text colour is inherited, so the reading proves the block's own role only
 *     because --lf-on-brand and the sidebar's --lf-bar-text are two different colours, checked first in both themes;
 *   - its active item, `nav-dashboard` — the item whose href is the page on view, both read back first: background
 *     --lf-bar-active-bg, text --lf-bar-active-text, left border --lf-bar-indicator, the mark on its left; an inactive
 *     item, `nav-settings`, read at rest (no pointer over it, checked): text --lf-bar-text;
 *   - its connection-security line, `connection-security`, once the server has answered (`data-server-checked`, so the
 *     level is final): the icon — the `<svg>` of `connection-security-toggle` — in the bar's status role of the level
 *     the line reports in `data-level` (secure → --lf-bar-success, local → --lf-bar-warning, insecure →
 *     --lf-bar-danger; secure on the lane's localhost), the three resolved to three different colours first;
 *     `connection-security-label` in --lf-bar-text;
 *   - `app-header`, neutral (D-T23): background --lf-surface-header, resolved first to a colour of its own, neither
 *     --lf-surface-app nor --lf-surface-bar; bottom border --lf-border-subtle; and its controls in the page's roles:
 *     `theme-toggle` in --lf-text-secondary, `header-donate-link`, «Offrimi un caffè», in --lf-donate — both checked
 *     first to differ from the header's own text, --lf-text-primary, which they would inherit without a role of their
 *     own — and on the mobile project the icon of `mobile-menu-toggle` in --lf-text-primary, which the header's text
 *     shares: there the reading proves the colour, not the class that gives it;
 *   - keyboard focus, each surface with its ring, the two rings resolved to two different colours first: a Tab from
 *     `privacy-toggle` lands on `theme-toggle`, read back as focused and as `:focus-visible`, and draws a solid outline
 *     in the page's --lf-focus where the toggle at rest drew none — the focus pins the header (T-7), which is read where
 *     it stands; and a Tab from `nav-dashboard` lands on the next control of the sidebar, read back as inside the
 *     `<nav>` and `:focus-visible`, which draws a solid outline in --lf-bar-focus.
 *
 * (c) The other side of the line, in dark, where the remap acts. What is not migrated yet keeps today's look (D-T3),
 * but the waves migrate the page content area by area (D-T28) — DV's took the dashboard on 16/10, the cash card this
 * case used to read included — so no component of a page is legacy for sure any more: the remap is proven on probes of
 * the spec's own instead, appended to the page content, the shell's one `<main>`, and removed in the task that reads
 * them. A container with no role utility, `<div class="rounded-xl">`, takes the remap's border,
 * `var(--theme-border-primary)`, the legacy variable, and its twin with one escapes the remap through
 * `:where(:not([class*='-lf-']))`: `<div class="rounded-xl border-lf-subtle">` draws --lf-border-subtle — the legacy
 * variable checked first to differ from --lf-border-subtle and from --lf-border-raised, the borders a migrated
 * container takes. The rule probed is a structural one, `html.dark .rounded-xl`, not a class rule such as
 * `html.dark .bg-white`: C4 (themeTokens.gate.test.ts) retires a class rule in the change that removes the class's last
 * use, so a `bg-white` probe would go red inside someone else's wave again; a structural rule keys on an element or a
 * shape, which a migration keeps, and leaves app.css only with the clean-up (B6), which removes the remap and must
 * rewrite this half anyway. Meanwhile the language menu opened over the page, migrated, draws its own roles:
 * `language-selector-panel` on --lf-surface-card, with a --lf-border-raised border (N3), checked to differ from
 * --lf-border-subtle first. A remap that stopped repainting a legacy container, or caught a migrated one, shows here.
 *
 * (d) Signed out, on `/`, in each theme, the login background, `animated-background`:
 *   - its root: background --lf-surface-page;
 *   - its three waves, the `<div>` children of the root, which render once the component is mounted — waited for, never
 *     assumed: wave N, in DOM order, is a gradient with a stop in --lf-art-hill-N, at opacity 1 — the strength of a hill
 *     is the alpha of its role, and an opacity on top would dim it twice;
 *   - its three chart lines, the `<path>`s of its `<svg>`: stroke --lf-art-line;
 *   - in dark, none of those colours is one of the retired dark background, alpha aside: #11151c (its page), #00ff9a
 *     (its hills), #4ade80 (its chart lines).
 *
 * ## How it reads
 *
 * The test writes no colour it expects to see — the three of (d) are there to be proven gone. The theme is
 * `localStorage['librefolio-theme']`, written by an init script on every navigation, before app.html's theme script
 * reads it ahead of the first paint. Signing in applies the account's own preference instead (auth.ts calls
 * `applyTheme` with the user's settings), so the signed-in cases load `/dashboard` again once signed in: the init script
 * writes the theme back first, and nothing after the sign-in reads the server's preference again. The preference on the
 * server is never touched.
 *
 * The value a role must have is the one the browser computes for it: a probe element appended to <body> with
 * `<property>: var(--lf-…, transparent)`, read with getComputedStyle and removed in the same task, so the page never
 * paints it. The element and the probe go through the same cascade, so the two computed values serialize alike whatever
 * the role is made of — a hex, a color-mix; the legacy variable of (c) is read the same way. Every read of an element
 * polls until it settles: the fields carry `transition-all`, and so do the sidebar and its items, so a border read
 * straight after a focus would catch the transition halfway.
 *
 * A wave of (d) holds its colour as a stop of a gradient, which no colour property holds alone: each colour stop of its
 * computed `background-image` is read back through a probe's `color` — the property its role is read through — so the
 * two sides still serialize alike, whether the role is a hex (the dark hills) or a color-mix with an alpha (the light
 * ones), and even if the gradient kept a stop unresolved. A chart line is compared through `stroke` itself.
 *
 * The positive control runs first in every test: the probe resolves a role to a colour (it falls back to transparent
 * when no stylesheet declares the role, and that is refused); the two themes resolve --lf-surface-card to two different
 * values, read by probes inside a `.light` and a `.dark` subtree, which tokens.css declares every role on as well; and
 * the page's own value is the one of the theme the test set. So a dark test cannot pass on a page drawn in light — the
 * account's own preference included — and a probe that read one value everywhere fails there instead of passing below.
 * In (d) the three hill roles must also resolve to three different colours, or no wave could be told from another; in
 * (b), likewise, the three status roles of the connection-security levels, or the icon could not tell one from another.
 * Wherever a reading could also come from a neighbouring role — an inherited text colour, a border at rest, the other
 * surface's focus ring — the two roles are checked to differ before it is taken.
 *
 * ## What it cannot see
 *
 *   - pixels: a computed colour is what the cascade decided, not what reached the screen — an opacity (a wave's aside,
 *     held at 1 by (d)), a layer on top, an image behind, a clip; the states but four — the fields under the pointer
 *     (desktop only), a focused field, the keyboard focus on the theme toggle and on a sidebar control — and no pressed
 *     state; the colours of the icons but three, the ✓ of a passed rule, the connection-security icon and the mobile
 *     menu's. The gallery and the designer's review do;
 *   - legibility: the contrast of the pairs is themeTokens.gate.test.ts's (C3), on the declared values;
 *   - the placeholder through anything but getComputedStyle(el, '::placeholder'). A browser that ignored the
 *     pseudo-element would hand back the field's own colour, --lf-text-primary: a red, not a silent pass, and its
 *     message names the field's own colour so that it reads as what it is;
 *   - the sidebar as it slides: on mobile it waits off-canvas and is read there — a computed colour does not depend on
 *     where the drawer is, so it is not opened;
 *   - what is fleeting: the hover states (an inactive sidebar item's `hover:bg-lf-bar-hover`, which is why that item is
 *     read at rest; the header's controls; the logo block's close button, a button drawn on mobile only), the focus
 *     ring of every control but the theme toggle and the sidebar control after `nav-dashboard`, the collapsed
 *     sidebar's tooltips (shown on hover only), and the shell's waiting screens (`app-auth-checking`,
 *     `app-bootstrap-loading`, `onboarding-redirecting`) and `welcome-shell`, which a signed-in landing passes
 *     through, or never reaches, before anything could be read;
 *   - the connection-security levels the lane does not report: on its localhost the line is secure, so the other two
 *     tones — the insecure tint behind the toggle, --lf-bar-danger at 20 %, and the mobile menu's danger dot,
 *     --lf-danger on the header, with them — are resolved but never seen drawn here (connection-security.spec.ts
 *     reaches those levels under other host names, and reads no colour); nor the line's details and their admin
 *     warning, which stay closed;
 *   - the login background as it moves: the waves' transform and the lines' dash and fade are animated, their colours
 *     are not, so a computed colour holds at any frame — but the opacity of a line, animated from 0 to 1 and back, is
 *     not read, so its strength is checked only as the alpha of --lf-art-line; and a retired colour that came back in
 *     another form (a mix of it) would not be recognised as one;
 *   - the remap at work but on one rule: (c) reads, on probes, the border it gives a rounded container; what its class
 *     rules (`html.dark .bg-white` …) and its rules on a legacy field paint is not read in a browser;
 *   - any page but `/` and `/dashboard` — the error page included, which draws the same login background and a card in
 *     relief — and the content of `/dashboard` itself, where (c) reads probes of its own instead: the pages are the
 *     migration waves' own cases, and the gallery's.
 *
 * The test writes nothing server-side. The signed-out cases never sign in or register; the registration link needs
 * `registration_mode` 'open': open by default, read by the login card from GET /api/v1/system/instance, and changed by no
 * E2E spec (auth.spec.ts stubs that read on its own pages only). The signed-in cases sign in as TEST_USER — the server
 * counts the sign-in, as it does for every E2E login — and only read; TEST_USER is grandfathered completed on every
 * onboarding flow (populate_mock_data), which is read back before the dashboard is loaded, so no Welcome, tour or guide
 * stands in the way. The runner's desktop AND mobile projects run every case but the fields under the pointer, a desktop
 * case. Registered in scripts/test_runner/_frontend_utility.py, action `theme-roles` of front-utility.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {readOnboardingProgress} from '../fixtures/onboarding-accounts';
import {TEST_USER} from '../fixtures/test-users';

const THEMES = ['light', 'dark'] as const;
type Theme = (typeof THEMES)[number];

/** The colour properties this spec compares: a probe reads its role through the same one as the element. */
type ColourProperty = 'background-color' | 'border-top-color' | 'border-bottom-color' | 'border-left-color' | 'outline-color' | 'color' | 'stroke';

/** The first paint of `/`: it asks GET /auth/me before it shows the login (the budget auth.spec.ts gives the same step). */
const FIRST_PAINT_MS = 20_000;
/** A full load of a signed-in page: GET /auth/me, then the bootstrap's reads, before the shell renders (login()'s arrival budget). */
const SHELL_MS = 30_000;
/** A computed colour settles within one transition (150 ms); the budget is the expect default's, stated. */
const SETTLE_MS = 3_000;

/** Meets every rule of PasswordStrength: length, upper case, lower case, a digit, a special character. Never submitted. */
const EVERY_RULE = 'Glacier!Quill7-Marmot-Sundial';
/** The rules the checklist lists (PasswordStrength.svelte), each `password-rule-<key>`. */
const RULE_KEYS = ['minLength', 'hasUppercase', 'hasLowercase', 'hasNumber', 'hasSpecial'] as const;

/** The login background (AnimatedBackground.svelte): its waves, the `<div>` children of its root, wave N on --lf-art-hill-N. */
const WAVES = 3;
/** …and its chart lines, the `<path>`s of its `<svg>`, all three on --lf-art-line. */
const LINES = 3;
/** The colours of the dark login background before T-5, literals all three: its page, its hills, its chart lines. */
const RETIRED_DARK = ['#11151c', '#00ff9a', '#4ade80'] as const;

/** The page on view in (b), and with it the sidebar's active item: the one whose href it is (Sidebar.svelte's `activeHref`). */
const DASHBOARD_URL = /^https?:\/\/[^/]+\/dashboard(?:[/?#]|$)/;
/** The bar's status role each level of the connection-security line draws its icon in (ConnectionSecurityIndicator.svelte, D-T17). */
const LEVEL_ROLES = {secure: '--lf-bar-success', local: '--lf-bar-warning', insecure: '--lf-bar-danger'} as const;
type ConnectionLevel = keyof typeof LEVEL_ROLES;
/** The line asks the server once it has mounted: one GET on a loaded lane (connection-security.spec.ts's budget). */
const VERDICT_MS = 15_000;
/** The four lines of the forgot-password card's terminal box, in the order of its fixed markup (ForgotPasswordCard.svelte). */
const TERMINAL_LINES = ['comment', 'command', 'comment', 'command'] as const;

// The first paint may take FIRST_PAINT_MS on a loaded lane; the comparisons after it take a few seconds. The signed-in
// cases sign in first and set a budget of their own.
test.setTimeout(45_000);

/**
 * What the browser computes for `expression` as `property`, on a probe appended to <body> — inside a subtree forced into
 * `theme` when one is given — read and removed within the same task.
 */
function probe(page: Page, expression: string, property: ColourProperty, theme: Theme | null = null): Promise<string> {
    return page.evaluate(
        ({expression, property, theme}) => {
            const host = document.createElement('div');
            if (theme) host.classList.add(theme);
            const element = host.appendChild(document.createElement('div'));
            element.style.setProperty(property, expression);
            document.body.appendChild(host);
            try {
                return getComputedStyle(element).getPropertyValue(property);
            } finally {
                host.remove();
            }
        },
        {expression, property, theme},
    );
}

/**
 * A role's colour as the page resolves it. The probe falls back to transparent when nothing declares the role, and that
 * is refused: every role this spec reads through it is a colour that shows — opaque, or translucent as the light hills of
 * the login background are, never fully transparent — so transparent can only mean a broken probe or a missing role.
 */
async function role(page: Page, name: string, property: ColourProperty, theme: Theme | null = null): Promise<string> {
    const value = await probe(page, `var(${name}, transparent)`, property, theme);
    const unresolved = await probe(page, 'transparent', property, theme);
    expect(value, `${name} must resolve to a colour${theme ? ` in a .${theme} subtree` : ''}: the probe fell back to transparent, so no stylesheet declares it there`).not.toBe(unresolved);
    return value;
}

/** An element's computed colour; with `pseudo`, the colour of that pseudo-element of it. */
function computed(target: Locator, property: ColourProperty, pseudo = ''): Promise<string> {
    return target.evaluate((element, {property, pseudo}) => getComputedStyle(element, pseudo || null).getPropertyValue(property), {property, pseudo});
}

/**
 * What the browser computes as `property` for a `<div>` with the classes `className`, appended to `container`, read and
 * removed within the same task, so the page never paints it. Unlike probe(), which states its colour in a style, it
 * takes the colour the page's own rules give those classes there — the remap of app.css included — as they would to a
 * container of the page. A new element has no transition to settle, so it is read once.
 */
function probeIn(container: Locator, className: string, property: ColourProperty): Promise<string> {
    return container.evaluate(
        (host, {className, property}) => {
            const element = document.createElement('div');
            element.className = className;
            host.appendChild(element);
            try {
                return getComputedStyle(element).getPropertyValue(property);
            } finally {
                element.remove();
            }
        },
        {className, property},
    );
}

/**
 * The colour of each stop of `wave`'s computed background-image, read back through a probe's `color` — the property
 * role() reads a hill role through, so the two sides serialize alike — with the image itself, for the message. One
 * task: the probe is appended to <body> and removed before the page could paint it.
 */
function stopColours(wave: Locator): Promise<{image: string; stops: string[]}> {
    return wave.evaluate((element) => {
        const image = getComputedStyle(element).getPropertyValue('background-image');
        // The arguments of the gradient, split at their top-level commas: a direction, then the stops — a colour and, when
        // it has them, its positions. What parses as a colour once its positions are stripped is a stop.
        const args = /^[\w-]+\((.*)\)$/.exec(image)?.[1] ?? '';
        const parts: string[] = [];
        let depth = 0;
        let part = '';
        for (const char of args) {
            if (char === ',' && depth === 0) {
                parts.push(part);
                part = '';
                continue;
            }
            if (char === '(') depth++;
            else if (char === ')') depth--;
            part += char;
        }
        if (args) parts.push(part);
        const probe = document.body.appendChild(document.createElement('div'));
        try {
            const stops = parts
                .map((candidate) => candidate.trim().replace(/(?:\s+[-+]?[\d.]+(?:%|[a-z]+)?)+$/i, ''))
                .filter((colour) => CSS.supports('color', colour))
                .map((colour) => {
                    probe.style.setProperty('color', colour);
                    return getComputedStyle(probe).getPropertyValue('color');
                });
            return {image, stops};
        } finally {
            probe.remove();
        }
    });
}

/** An `rgba()` as the `rgb()` of its channels: a retired colour stays retired at any strength. */
const withoutAlpha = (colour: string): string => colour.replace(/^rgba\((\d+), (\d+), (\d+), [\d.]+\)$/, 'rgb($1, $2, $3)');

/** `target` draws `property` in the colour of the role `name`, once any transition has settled. */
async function expectRole(page: Page, target: Locator, property: ColourProperty, name: string, what: string, pseudo = ''): Promise<void> {
    const expected = await role(page, name, property);
    await expect.poll(() => computed(target, property, pseudo), {message: `${what}: ${pseudo ? `${pseudo} ` : ''}${property} must be ${name}, ${expected}`, timeout: SETTLE_MS}).toBe(expected);
}

/**
 * The positive control: the page is drawn in `theme`, measured on a colour and not only on <html>'s class. The probe
 * resolves --lf-surface-card, the `.light` and `.dark` subtrees resolve it to two different values, and the page's own
 * value is the one of `theme`.
 */
async function expectDrawnIn(page: Page, theme: Theme): Promise<void> {
    await expect(page.locator('html'), `app.html's theme script must draw the page in ${theme}, the value the init script stored`).toHaveClass(new RegExp(`(?:^|\\s)${theme}(?:\\s|$)`));
    const card: Record<Theme | 'page', string> = {
        page: await role(page, '--lf-surface-card', 'background-color'),
        light: await role(page, '--lf-surface-card', 'background-color', 'light'),
        dark: await role(page, '--lf-surface-card', 'background-color', 'dark'),
    };
    expect(card.light, 'positive control: the two themes resolve --lf-surface-card to two different values, or no comparison below could tell them apart').not.toBe(card.dark);
    expect(card.page, `positive control: the page resolves --lf-surface-card to its ${theme} value`).toBe(card[theme]);
}

/** Signed out, on a fresh load of `/` drawn in `theme`: the init script stores `theme` before app.html's theme script reads it. */
async function openSignIn(page: Page, theme: Theme): Promise<void> {
    await page.addInitScript((look) => localStorage.setItem('librefolio-theme', look), theme);
    await page.goto('/');
    await expect(page.getByTestId('login-modal')).toBeVisible({timeout: FIRST_PAINT_MS});
    await expectDrawnIn(page, theme);
}

/** Precondition, read back rather than inferred: no onboarding flow is due, so no Welcome, tour or guide stands between the sign-in and the dashboard. */
async function expectNoOnboardingDue(page: Page): Promise<void> {
    const due = (await readOnboardingProgress(page)).filter((item) => item.status === 'pending' || item.version < item.current_version).map((item) => item.flow);
    expect(due, `${TEST_USER.username} must be grandfathered completed on every onboarding flow (populate_mock_data _grandfather_onboarding_for_test_users)`).toEqual([]);
}

/**
 * Signed in as TEST_USER, on a fresh load of `/dashboard` drawn in `theme`. The sign-in applies the account's own theme
 * preference; the full load after it lets the init script write `theme` back before app.html's theme script reads it.
 */
async function openDashboard(page: Page, theme: Theme): Promise<void> {
    await page.addInitScript((look) => localStorage.setItem('librefolio-theme', look), theme);
    await login(page, TEST_USER);
    await expectNoOnboardingDue(page);
    await page.goto('/dashboard');
    await expect(page.getByTestId('app-shell')).toBeVisible({timeout: SHELL_MS});
    await expectDrawnIn(page, theme);
}

test.describe('Colour roles on the sign-in page — every element draws its role, as the browser resolves it', () => {
    for (const theme of THEMES) {
        test.describe(`${theme} theme`, () => {
            test.beforeEach(async ({page}) => {
                await openSignIn(page, theme);
            });

            test('the login card: card in relief, field at rest and in focus, its placeholder, the primary action', async ({page}) => {
                const card = page.getByTestId('login-modal');
                await expectRole(page, card, 'background-color', '--lf-surface-card', 'login-modal');
                // N3: the card in relief. In light --lf-border-raised is the colour of --lf-border-subtle; in dark it is one
                // of its own, checked first, so that there the reading proves the card's own role.
                if (theme === 'dark') {
                    const subtle = await role(page, '--lf-border-subtle', 'border-top-color');
                    expect(await role(page, '--lf-border-raised', 'border-top-color'), `positive control: in dark --lf-border-raised is not --lf-border-subtle (${subtle}), so the card's border reads its own role`).not.toBe(subtle);
                }
                await expectRole(page, card, 'border-top-color', '--lf-border-raised', 'login-modal (in dark, html.dark .rounded-2xl must exempt it)');

                const username = page.getByTestId('login-username');
                // At rest: nothing focuses the field on load, and blur() makes sure of it.
                await username.blur();
                await expect(username).not.toBeFocused();
                await expectRole(page, username, 'border-top-color', '--lf-border-input', 'login-username at rest (in dark, html.dark input must exempt it)');
                await expectRole(page, username, 'color', '--lf-text-primary', 'login-username text (in dark, html.dark input must exempt it)');
                const own = await computed(username, 'color');
                await expectRole(page, username, 'color', '--lf-text-placeholder', `login-username placeholder (the field's own colour is ${own}: a reading equal to it means the browser resolved no ::placeholder style)`, '::placeholder');

                await username.focus();
                await expect(username).toBeFocused();
                await expectRole(page, username, 'border-top-color', '--lf-focus', 'login-username in focus');

                await expectRole(page, page.getByTestId('login-submit'), 'background-color', '--lf-action', 'login-submit');
            });

            test('the fields under the pointer: the hover border (D-T18), and the focus border over it once focused there', async ({page}, testInfo) => {
                test.skip(testInfo.project.name !== 'desktop', 'Desktop only: Tailwind writes hover: inside @media (hover: hover), which the mobile project, a touch device, does not match');
                // Positive control: the three borders of a field are three colours, or no reading below could tell a state
                // from another.
                const borders = [await role(page, '--lf-border-input', 'border-top-color'), await role(page, '--lf-border-input-hover', 'border-top-color'), await role(page, '--lf-focus', 'border-top-color')];
                expect(new Set(borders).size, `positive control: --lf-border-input, --lf-border-input-hover and --lf-focus resolve to three different colours (${borders.join(' | ')})`).toBe(3);

                // The username field, then the password field (PasswordInput, its hover a class: directive). The pointer and
                // the focus move from the first to the second, so the second starts at rest too — read back, not assumed.
                for (const testId of ['login-username', 'login-password']) {
                    const field = page.getByTestId(testId);
                    await expect(field).toBeVisible();
                    await field.blur();
                    await expect(field, `${testId} starts without the focus`).not.toBeFocused();
                    expect(await field.evaluate((element) => element.matches(':hover')), `${testId} starts at rest: no pointer is over it`).toBe(false);
                    await expectRole(page, field, 'border-top-color', '--lf-border-input', `${testId} at rest`);

                    await field.hover();
                    await expect.poll(() => field.evaluate((element) => element.matches(':hover')), {message: `the pointer is over ${testId}`, timeout: SETTLE_MS}).toBe(true);
                    await expectRole(page, field, 'border-top-color', '--lf-border-input-hover', `${testId} under the pointer (D-T18)`);

                    await field.focus();
                    await expect(field).toBeFocused();
                    expect(await field.evaluate((element) => element.matches(':hover')), `${testId} is still under the pointer: hovered and focused at once`).toBe(true);
                    await expectRole(page, field, 'border-top-color', '--lf-focus', `${testId} focused under the pointer: the focus border beats the hover one`);
                }
            });

            test('the register card: a password meeting every rule, the requirements box on the panel surface, each rule ticked in success', async ({page}) => {
                const gotoRegister = page.getByTestId('goto-register');
                await expect(gotoRegister, 'the login card must offer registration: registration_mode is open by default, read from GET /api/v1/system/instance, and no E2E spec changes it').toBeVisible();
                await gotoRegister.click();
                await expect(page.getByTestId('register-modal')).toBeVisible();

                const password = page.getByTestId('register-password');
                await password.fill(EVERY_RULE);
                await expect(password).toHaveValue(EVERY_RULE);

                const requirements = page.getByTestId('password-requirements');
                await expect(requirements).toBeVisible();
                for (const key of RULE_KEYS) await expect(requirements.getByTestId(`password-rule-${key}`), `the rule ${key}`).toHaveAttribute('data-passed', 'true');
                // Every rule the box lists, those this spec does not name included: none is left unmet.
                await expect(requirements.locator('[data-testid^="password-rule-"]:not([data-passed="true"])')).toHaveCount(0);

                // Round 2: the box is a neutral panel, and the ticks carry the success colour.
                await expectRole(page, requirements, 'background-color', '--lf-surface-panel', 'password-requirements');
                await expectRole(page, requirements, 'border-top-color', '--lf-border-subtle', 'password-requirements border');
                // A passed rule says so twice: its ✓, the rule's one icon, and its text. Read through the rule's own
                // `data-passed`, so a rule that flipped back would not resolve rather than lend its ✗ to the reading.
                for (const key of RULE_KEYS) {
                    const passed = requirements.locator(`[data-testid="password-rule-${key}"][data-passed="true"]`);
                    await expectRole(page, passed.locator('svg').first(), 'color', '--lf-success', `the ✓ of the passed rule ${key}`);
                    await expectRole(page, passed.locator('span').first(), 'color', '--lf-text-secondary', `the text of the passed rule ${key}`);
                }
            });

            test('the forgot-password card: in relief, and its commands in a terminal box, the commands and the comments apart (Q6)', async ({page}) => {
                const gotoForgot = page.getByTestId('goto-forgot');
                await expect(gotoForgot, 'the login card offers the password recovery').toBeVisible();
                await gotoForgot.click();
                const card = page.getByTestId('forgot-modal');
                await expect(card).toBeVisible();
                await expectRole(page, card, 'border-top-color', '--lf-border-raised', 'forgot-modal (N3)');

                const terminal = card.getByTestId('forgot-reset-commands');
                await expect(terminal).toBeVisible();
                await expectRole(page, terminal, 'background-color', '--lf-terminal-bg', 'forgot-reset-commands');
                await expectRole(page, terminal, 'border-top-color', '--lf-terminal-border', 'forgot-reset-commands border');

                // `color` is inherited: a comment line that lost its own role would draw the box's, the prompt colour. The
                // two differ, checked first, so that the readings below tell a comment from a command.
                const prompt = await role(page, '--lf-terminal-prompt', 'color');
                expect(await role(page, '--lf-terminal-comment', 'color'), `positive control: --lf-terminal-comment is not --lf-terminal-prompt (${prompt})`).not.toBe(prompt);
                // The lines carry no test id: they are the `<code>` children of the box, in the order of the component's fixed
                // markup (TERMINAL_LINES). An index names a line of that markup here, it does not guess at a row — and each
                // comment line is checked to be one before it is read: it starts with `#`, the shell's comment mark, which no
                // translation touches.
                const lines = terminal.locator(':scope > code');
                await expect(lines, 'the terminal box holds its four lines').toHaveCount(TERMINAL_LINES.length);
                for (const [index, kind] of TERMINAL_LINES.entries()) {
                    const line = lines.nth(index);
                    if (kind === 'comment') {
                        await expect(line, `line ${index + 1} of forgot-reset-commands is a shell comment`).toHaveText(/^\s*#/);
                        await expectRole(page, line, 'color', '--lf-terminal-comment', `line ${index + 1} of forgot-reset-commands, a comment`);
                    } else {
                        await expect(line, `line ${index + 1} of forgot-reset-commands is a command`).not.toHaveText(/^\s*#/);
                        await expectRole(page, line, 'color', '--lf-terminal-prompt', `line ${index + 1} of forgot-reset-commands, a command`);
                    }
                }
            });
        });
    }
});

test.describe('Colour roles in the app shell — signed in as TEST_USER, on /dashboard', () => {
    // A sign-in, then a full load of a signed-in page: login() alone may take 70 s on a loaded lane (auth.spec.ts).
    test.describe.configure({timeout: 120_000});

    for (const theme of THEMES) {
        test(`(b) ${theme} theme: the green sidebar from its own roles, the neutral header from the page's, each with its keyboard ring`, async ({page}, testInfo) => {
            await openDashboard(page, theme);

            // Round 2: the app and the standalone pages share one background, --lf-surface-app derived from --lf-surface-page.
            const pageSurface = await role(page, '--lf-surface-page', 'background-color');
            expect(await role(page, '--lf-surface-app', 'background-color'), `--lf-surface-app resolves to the colour of --lf-surface-page, ${pageSurface} (round 2: one background)`).toBe(pageSurface);
            await expectRole(page, page.getByTestId('app-shell'), 'background-color', '--lf-surface-app', 'app-shell');

            // The sidebar has no test id: it is the <nav> that holds its collapse toggle. On mobile it waits off-canvas
            // and is read there, since a computed colour does not depend on where the drawer is.
            const sidebar = page.locator('nav').filter({has: page.getByTestId('sidebar-collapse-toggle')});
            await expect(sidebar, 'one <nav> holds sidebar-collapse-toggle: the sidebar').toHaveCount(1);
            // D-T17: green in both themes, drawn from a family of roles of its own, --lf-bar-*.
            await expectRole(page, sidebar, 'background-color', '--lf-surface-bar', 'the sidebar');
            await expectRole(page, sidebar, 'color', '--lf-bar-text', 'the sidebar text');
            // D-T23: no right border, in either theme — read as a width, since a border that is not drawn has no colour.
            await expect(sidebar, 'the sidebar draws no right border (D-T23)').toHaveCSS('border-right-width', '0px');

            // The logo block is one with the bar (D-T17): no surface of its own, so the bar shows through — the transparent
            // keyword, read back through the same probe. Its text keeps the role of the login card header; `color` is
            // inherited, so the reading tells the block's role from the sidebar's only because the two differ, checked first.
            const brand = sidebar.getByTestId('sidebar-brand');
            await expect(brand, 'the sidebar holds its logo block, sidebar-brand').toHaveCount(1);
            const transparent = await probe(page, 'transparent', 'background-color');
            await expect.poll(() => computed(brand, 'background-color'), {message: `the logo block, sidebar-brand: no background of its own, ${transparent}, so that the bar shows through`, timeout: SETTLE_MS}).toBe(transparent);
            const barText = await role(page, '--lf-bar-text', 'color');
            expect(await role(page, '--lf-on-brand', 'color'), `positive control: --lf-on-brand is not the bar text, --lf-bar-text (${barText}), so the logo block's text reads its own role, not the one it would inherit from the sidebar`).not.toBe(barText);
            await expectRole(page, brand, 'color', '--lf-on-brand', 'the logo block text');

            // The active item is the one whose href is the page on view: both read back, never inferred from a class.
            await expect(page, 'the page on view is /dashboard').toHaveURL(DASHBOARD_URL);
            const active = sidebar.getByTestId('nav-dashboard');
            await expect(active, 'nav-dashboard links the page on view').toHaveAttribute('href', '/dashboard');
            await expectRole(page, active, 'background-color', '--lf-bar-active-bg', 'the active item, nav-dashboard on /dashboard');
            await expectRole(page, active, 'color', '--lf-bar-active-text', 'the active item text');
            await expectRole(page, active, 'border-left-color', '--lf-bar-indicator', 'the active item left border, its indicator');

            // An inactive item, read at rest: under the pointer it would draw hover:bg-lf-bar-hover.
            const inactive = sidebar.getByTestId('nav-settings');
            await expect(inactive, 'nav-settings links another page than the one on view').toHaveAttribute('href', '/settings');
            expect(await inactive.evaluate((element) => element.matches(':hover')), 'nav-settings is read at rest: no pointer is over it').toBe(false);
            await expectRole(page, inactive, 'color', '--lf-bar-text', 'an inactive item, nav-settings');

            // The connection-security line on the green bar: its icon in the bar's status role of the level it reports.
            const tones: string[] = [];
            for (const name of Object.values(LEVEL_ROLES)) tones.push(await role(page, name, 'color'));
            expect(new Set(tones).size, `positive control: the three level roles resolve to three different colours, or the icon could not tell a level from another (${tones.join(' | ')})`).toBe(tones.length);
            const line = sidebar.getByTestId('connection-security');
            // The browser's verdict comes first, the server's is folded in once it answers: read the level once it is final.
            await expect(line, 'the server answered the line (GET /api/v1/system/connection): its level is final').toHaveAttribute('data-server-checked', 'true', {timeout: VERDICT_MS});
            const level = await line.getAttribute('data-level');
            expect(Object.keys(LEVEL_ROLES), `connection-security reports a level the indicator draws (data-level=${level})`).toContain(level);
            const tone = LEVEL_ROLES[level as ConnectionLevel];
            await expectRole(page, line.getByTestId('connection-security-toggle').locator('svg').first(), 'color', tone, `the connection-security icon, level ${level}`);
            // The label shows on an expanded sidebar, and a fresh browser context stores no collapsed one.
            const label = line.getByTestId('connection-security-label');
            await expect(label, 'the sidebar is expanded, so the line shows its label').toBeAttached();
            await expectRole(page, label, 'color', '--lf-bar-text', 'connection-security-label');

            // The header, neutral since D-T23: a surface of its own, a step off the page's, and the page's roles for the rest.
            const header = page.getByTestId('app-header');
            const headerSurface = await role(page, '--lf-surface-header', 'background-color');
            for (const name of ['--lf-surface-app', '--lf-surface-bar']) {
                const neighbour = await role(page, name, 'background-color');
                expect(headerSurface, `positive control: --lf-surface-header is not ${name} (${neighbour}), so the reading below is the header's own surface`).not.toBe(neighbour);
            }
            await expectRole(page, header, 'background-color', '--lf-surface-header', 'app-header');
            await expectRole(page, header, 'border-bottom-color', '--lf-border-subtle', 'app-header bottom border');
            // Its controls in the page's roles. `color` is inherited: a control with no text role of its own would draw the
            // header's, --lf-text-primary, which differs from both readings below, checked first.
            const headerText = await role(page, '--lf-text-primary', 'color');
            for (const name of ['--lf-text-secondary', '--lf-donate']) {
                expect(await role(page, name, 'color'), `positive control: ${name} is not the header's text, --lf-text-primary (${headerText}), so the reading below is the control's own role`).not.toBe(headerText);
            }
            const themeToggle = header.getByTestId('theme-toggle');
            await expect(themeToggle).toBeVisible();
            await expectRole(page, themeToggle, 'color', '--lf-text-secondary', 'theme-toggle');
            const donate = header.getByTestId('header-donate-link');
            await expect(donate).toBeVisible();
            await expectRole(page, donate, 'color', '--lf-donate', 'header-donate-link');
            if (testInfo.project.name === 'mobile') {
                // On a phone the header holds the burger that opens the sidebar. Its icon draws --lf-text-primary, the header's
                // own text: here the reading proves the colour, not the class that gives it.
                const menuToggle = header.getByTestId('mobile-menu-toggle');
                await expect(menuToggle, 'the mobile header shows the burger').toBeVisible();
                await expectRole(page, menuToggle.locator('svg').first(), 'color', '--lf-text-primary', 'the icon of mobile-menu-toggle');
            }

            // Keyboard focus draws the ring of the surface it is on: the page's --lf-focus on the neutral header, the
            // sidebar's own --lf-bar-focus on the green, where --lf-focus would hardly show. The two differ, checked first, so
            // that each reading names its ring.
            const pageRing = await role(page, '--lf-focus', 'outline-color');
            const barRing = await role(page, '--lf-bar-focus', 'outline-color');
            expect(pageRing, `positive control: the page's ring, --lf-focus, is not the sidebar's, --lf-bar-focus (${barRing}), so each reading below tells one from the other`).not.toBe(barRing);

            // On the header. The last hop is a Tab, which Chrome always marks :focus-visible — a bare focus() would inherit
            // the kind of the page's last interaction — from privacy-toggle, the control just before theme-toggle in the
            // header on both projects (header-scroll.spec.ts takes the same hop). The focus pins the header (T-7): it is
            // read where it stands.
            await expect(themeToggle, 'theme-toggle at rest draws no outline: the one read below is its focus ring').toHaveCSS('outline-style', 'none');
            const privacy = header.getByTestId('privacy-toggle');
            await expect(privacy).toBeVisible();
            await privacy.focus();
            await page.keyboard.press('Tab');
            await expect(themeToggle, 'Tab from privacy-toggle lands on theme-toggle, the next control of the header').toBeFocused();
            expect(await themeToggle.evaluate((element) => element.matches(':focus-visible')), 'a focus that arrives by Tab is keyboard focus').toBe(true);
            await expect(themeToggle, 'the focus ring is drawn: focus-visible:outline-2, a solid outline').toHaveCSS('outline-style', 'solid');
            await expectRole(page, themeToggle, 'outline-color', '--lf-focus', 'the keyboard focus ring of theme-toggle on the header');

            // On the sidebar: a Tab from nav-dashboard lands on the next control of the <nav>, whichever it is — read back,
            // never assumed. On mobile the drawer waits off-canvas with its controls in the tab order, and a computed colour
            // does not depend on where the drawer is.
            await active.focus();
            await expect(active, 'nav-dashboard holds the focus before the Tab').toBeFocused();
            await page.keyboard.press('Tab');
            const landed = await sidebar.evaluate((nav) => {
                const element = document.activeElement;
                return {inside: element !== null && element !== nav && nav.contains(element), visible: element?.matches(':focus-visible') ?? false, testId: element?.getAttribute('data-testid') ?? ''};
            });
            expect(landed.inside, 'Tab from nav-dashboard lands on a control inside the sidebar <nav>').toBe(true);
            expect(landed.visible, 'a focus that arrives by Tab is keyboard focus').toBe(true);
            expect(landed.testId, 'the sidebar control the Tab landed on carries a test id, so it can be read').not.toBe('');
            const next = sidebar.getByTestId(landed.testId);
            await expect(next, `${landed.testId} holds the focus`).toBeFocused();
            await expect(next, 'the focus ring is drawn: focus-visible:outline-2, a solid outline').toHaveCSS('outline-style', 'solid');
            await expectRole(page, next, 'outline-color', '--lf-bar-focus', `the keyboard focus ring of ${landed.testId} on the sidebar`);
        });
    }

    test('(c) dark theme: in the page content a legacy container takes the remap and its twin with a role escapes it, and a migrated menu over the page draws its roles', async ({page}) => {
        await openDashboard(page, 'dark');

        // The page content, the shell's one <main>: the waves migrate it area by area (D-T28), so no component of it is
        // legacy for sure, and the remap is proven on two probes appended to it, twins but for a role utility.
        const content = page.getByTestId('app-shell').getByRole('main');
        await expect(content, 'the app shell holds one <main>, the page content').toHaveCount(1);
        // Positive control: the remap's border differs from the two a migrated container takes, or the probes below
        // could not tell legacy from migrated.
        const remapBorder = await role(page, '--theme-border-primary', 'border-top-color');
        for (const name of ['--lf-border-subtle', '--lf-border-raised']) {
            const migrated = await role(page, name, 'border-top-color');
            expect(remapBorder, `positive control: the remap's border, --theme-border-primary, is not ${name} (${migrated}), the border of a migrated container, so the probes below tell legacy from migrated`).not.toBe(migrated);
        }
        // A container with no role utility takes the remap's border — a structural rule, which only the clean-up (B6)
        // retires, where C4 retires a class rule such as html.dark .bg-white with the class's last use. Without the
        // remap, Tailwind's preflight would draw the border in currentColor, the probe's text colour.
        expect(await probeIn(content, 'rounded-xl', 'border-top-color'), `a legacy container in the page content, <div class="rounded-xl"> (html.dark .rounded-xl must repaint it): border-top-color must be --theme-border-primary, ${remapBorder}`).toBe(remapBorder);
        // Its twin with a role utility escapes the remap through :where(:not([class*='-lf-'])), and draws its role.
        const roleBorder = await role(page, '--lf-border-subtle', 'border-top-color');
        expect(await probeIn(content, 'rounded-xl border-lf-subtle', 'border-top-color'), `a migrated container in the page content, <div class="rounded-xl border-lf-subtle"> (html.dark .rounded-xl must exempt it): border-top-color must be --lf-border-subtle, ${roleBorder}`).toBe(roleBorder);

        // A migrated menu, opened over the page: on the card, in relief (N3).
        const languageButton = page.getByTestId('language-selector-button');
        await expect(languageButton, 'the language menu starts closed').toHaveAttribute('aria-expanded', 'false');
        await languageButton.click();
        await expect(languageButton).toHaveAttribute('aria-expanded', 'true');
        const panel = page.getByTestId('language-selector-panel');
        await expect(panel).toBeVisible();
        await expectRole(page, panel, 'background-color', '--lf-surface-card', 'language-selector-panel');
        const subtle = await role(page, '--lf-border-subtle', 'border-top-color');
        expect(await role(page, '--lf-border-raised', 'border-top-color'), `positive control: in dark --lf-border-raised is not --lf-border-subtle (${subtle}), so the menu's border reads its own role`).not.toBe(subtle);
        await expectRole(page, panel, 'border-top-color', '--lf-border-raised', 'language-selector-panel border');
    });
});

test.describe('Colour roles behind the sign-in page — the login background, signed out on /', () => {
    for (const theme of THEMES) {
        test(`(d) ${theme} theme: the login background draws the page surface, its three hills and its chart lines from the roles`, async ({page}) => {
            await openSignIn(page, theme);
            const background = page.getByTestId('animated-background');
            await expectRole(page, background, 'background-color', '--lf-surface-page', 'animated-background');

            const hills: string[] = [];
            for (let n = 1; n <= WAVES; n++) hills.push(await role(page, `--lf-art-hill-${n}`, 'color'));
            expect(new Set(hills).size, `positive control: the hill roles resolve to ${WAVES} different colours, or no wave could be told from another (${hills.join(' | ')})`).toBe(WAVES);

            // The waves render once the component is mounted: waited for, never assumed. Their DOM order is the subject —
            // wave N reads --lf-art-hill-N — so an index names a wave of the component here, it does not guess at a row.
            const waves = background.locator(':scope > div');
            await expect(waves, 'the waves of the login background, rendered once it is mounted').toHaveCount(WAVES);
            const drawn = [await computed(background, 'background-color')];
            for (const [index, hill] of hills.entries()) {
                const wave = waves.nth(index);
                const name = `--lf-art-hill-${index + 1}`;
                await expect.poll(() => stopColours(wave), {message: `wave ${index + 1}: its gradient must have a stop in ${name}, ${hill}`, timeout: SETTLE_MS}).toMatchObject({stops: expect.arrayContaining([hill])});
                await expect(wave, `wave ${index + 1}: no opacity on top — the strength of its hill is the alpha of ${name}`).toHaveCSS('opacity', '1');
                drawn.push(...(await stopColours(wave)).stops);
            }

            const lines = background.locator('svg path');
            await expect(lines, 'the chart lines of the login background').toHaveCount(LINES);
            for (let index = 0; index < LINES; index++) {
                const line = lines.nth(index);
                await expectRole(page, line, 'stroke', '--lf-art-line', `chart line ${index + 1}`);
                drawn.push(await computed(line, 'stroke'));
            }

            // Only the dark background had literals of its own (its `:global(html.dark)` rules). The negative half, its
            // barrier passed above: every colour in `drawn` was just proven to be its role's. The retired literals go
            // through the same probe, so they serialize as the drawn colours do; an alpha does not hide one.
            if (theme === 'dark') {
                const retired = await Promise.all(RETIRED_DARK.map((hex) => probe(page, hex, 'color')));
                const back = drawn.filter((colour) => retired.includes(withoutAlpha(colour)));
                expect(back, `none of the retired dark colours (${RETIRED_DARK.join(', ')}, read as ${retired.join(', ')}) is drawn again; drawn: ${drawn.join(' | ')}`).toEqual([]);
            }
        });
    }
});
