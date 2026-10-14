/**
 * Colour roles on the sign-in page: every migrated element draws the colour of its role, as the browser itself resolves
 * it, in the light and in the dark theme (colour programme, workstream T, step T-2 — the login/registration pilot).
 *
 * ## What this protects
 *
 * LoginCard, RegisterCard, PasswordInput and PasswordStrength moved from palette classes to the role utilities of
 * src/lib/theme/tokens.css (bg-lf-card, border-lf-input…). The unit gates prove that the source is written right
 * (src/themeRoles.gate.test.ts) and that the roles are a whole, legible table (src/themeTokens.gate.test.ts); only a
 * browser can prove that the cascade delivers them. In dark it has a rival: the legacy remap of src/app.css (P1) is
 * unlayered, so it beats every Tailwind utility, and its structural rules exempt an element only through
 * `:where(:not([class*='-lf-']))`. Without that exemption a migrated field would keep the legacy border, text and
 * placeholder, and the card the legacy border, and nothing but a computed style would say so. In each theme:
 *
 *   - `login-modal`: background --lf-surface-card, border --lf-border-subtle — in dark, the proof that
 *     `html.dark .rounded-2xl` leaves it alone;
 *   - `login-username`: border --lf-border-input at rest and --lf-focus in focus, text --lf-text-primary, placeholder
 *     --lf-text-placeholder — in dark, the proof that `html.dark input` and its `::placeholder` leave it alone;
 *   - `login-submit`: background --lf-action;
 *   - the register card, once the password meets every rule: every `password-rule-*` passed, and the
 *     `password-requirements` box on --lf-success-soft (in dark, the designer's own value rather than the recipe).
 *
 * ## How it reads
 *
 * The test writes no colour. The theme is `localStorage['librefolio-theme']`, set by an init script before the first
 * navigation, which app.html's theme script reads before the first paint. The value a role must have is the one the
 * browser computes for it: a probe element appended to <body> with `<property>: var(--lf-…, transparent)`, read with
 * getComputedStyle and removed in the same task, so the page never paints it. The element and the probe go through the
 * same cascade, so the two computed values serialize alike whatever the role is made of — a hex, a color-mix. Every
 * read of an element polls until it settles: the fields carry `transition-all`, so a border read straight after a focus
 * would catch the transition halfway.
 *
 * The positive control runs first, before every test: the probe resolves a role to a colour (it falls back to
 * transparent when no stylesheet declares the role, and that is refused); the two themes resolve --lf-surface-card to
 * two different values, read by probes inside a `.light` and a `.dark` subtree, which tokens.css declares every role on
 * as well; and the page's own value is the one of the theme the test set. So a dark test cannot pass on a page drawn in
 * light, and a probe that read one value everywhere fails there instead of passing below.
 *
 * ## What it cannot see
 *
 *   - pixels: a computed colour is what the cascade decided, not what reached the screen — an opacity, a layer on top,
 *     an image behind; hover and pressed states; the colours of the icons. The gallery and the designer's review do;
 *   - legibility: the contrast of the pairs is themeTokens.gate.test.ts's (C3), on the declared values;
 *   - the placeholder through anything but getComputedStyle(el, '::placeholder'). A browser that ignored the
 *     pseudo-element would hand back the field's own colour, --lf-text-primary: a red, not a silent pass, and its
 *     message names the field's own colour so that it reads as what it is;
 *   - any page but `/`, and a signed-in session: the shell's pilot (T-3) brings its own cases.
 *
 * Nothing is written server-side: the visitor never signs in and never registers. The registration link needs
 * `enable_registration`, true by default and closed by no E2E spec (auth.spec.ts stubs it on its own pages only). The
 * runner's desktop AND mobile projects run every case. Registered in scripts/test_runner/_frontend_utility.py, action
 * `theme-roles` of front-utility.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';

const THEMES = ['light', 'dark'] as const;
type Theme = (typeof THEMES)[number];

/** The colour properties this spec compares: a probe reads its role through the same one as the element. */
type ColourProperty = 'background-color' | 'border-top-color' | 'color';

/** The first paint of `/`: it asks GET /auth/me before it shows the login (the budget auth.spec.ts gives the same step). */
const FIRST_PAINT_MS = 20_000;
/** A computed colour settles within one transition (150 ms); the budget is the expect default's, stated. */
const SETTLE_MS = 3_000;

/** Meets every rule of PasswordStrength: length, upper case, lower case, a digit, a special character. Never submitted. */
const EVERY_RULE = 'Glacier!Quill7-Marmot-Sundial';
/** The rules the checklist lists (PasswordStrength.svelte), each `password-rule-<key>`. */
const RULE_KEYS = ['minLength', 'hasUppercase', 'hasLowercase', 'hasNumber', 'hasSpecial'] as const;

// The first paint may take FIRST_PAINT_MS on a loaded lane; the comparisons after it take a few seconds.
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
 * is refused: every role this spec reads is opaque, so transparent can only mean a broken probe or a missing role.
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

test.describe('Colour roles on the sign-in page — every element draws its role, as the browser resolves it', () => {
    for (const theme of THEMES) {
        test.describe(`${theme} theme`, () => {
            test.beforeEach(async ({page}) => {
                await page.addInitScript((look) => localStorage.setItem('librefolio-theme', look), theme);
                await page.goto('/');
                await expect(page.getByTestId('login-modal')).toBeVisible({timeout: FIRST_PAINT_MS});
                await expectDrawnIn(page, theme);
            });

            test('the login card: card, field at rest and in focus, its placeholder, the primary action', async ({page}) => {
                const card = page.getByTestId('login-modal');
                await expectRole(page, card, 'background-color', '--lf-surface-card', 'login-modal');
                await expectRole(page, card, 'border-top-color', '--lf-border-subtle', 'login-modal (in dark, html.dark .rounded-2xl must exempt it)');

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

            test('the register card: a password meeting every rule, the requirements box on success-soft', async ({page}) => {
                const gotoRegister = page.getByTestId('goto-register');
                await expect(gotoRegister, 'the login card must offer registration: enable_registration is true by default and no E2E spec closes it').toBeVisible();
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

                await expectRole(page, requirements, 'background-color', '--lf-success-soft', 'password-requirements');
            });
        });
    }
});
